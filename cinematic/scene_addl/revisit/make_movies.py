"""Per-lake season movies for the "revisiting lake drainage papers" page.

Four tracks per lake, every one 153 daily frames (1 May → 30 Sep) at 512 px
over the same 5.12 km tile, so any two play side by side frame for frame:

  2010 / modis   MODIS Terra·Aqua, 250 m — what the paper's lake record saw
  2010 / hires   Landsat 7 ETM+ (pan-sharpened to 15 m, scan-line gaps left
                 in) and ASTER (15 m) on the days they exist
  2019 / modis   MODIS again, for the same comparison nine years on
  2019 / hires   Sentinel-2, 10 m (fetch_s2_2019.py)

A day with NO image is a BLACK frame — on purpose, at the director's
request: the gaps are the point here, unlike the site's other lake movies.

Colour: reflectance 0…1 → 0…255, linear, the same for every sensor.
ASTER has no blue band; its blue is green + 0.6 (green − red), said so in
the sidecar.

  cinematic/.venv/bin/python make_movies.py [--force] [ids…]
     → movies/…mp4, thumbs/…jpg and meta/…json under source_data/revisit/
"""
from __future__ import annotations

import json
import subprocess
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image

from common import MOVIE_DIR, SEASONS, STACK_DIR, TILE_M, WORK, season_days

FPS = 2
SIZE = 512
META_DIR = WORK / 'meta'
NDWI_MIN = 0.3
WATER_R_M = 1250.0
ASTER_ESUN = (1848.0, 1549.0, 1114.0)      # green, red, near-infrared (W m⁻² µm⁻¹)


def near_mask(n: int) -> np.ndarray:
    res = TILE_M / n
    yy, xx = np.mgrid[0:n, 0:n]
    return np.hypot((xx + 0.5) * res - TILE_M / 2, (yy + 0.5) * res - TILE_M / 2) <= WATER_R_M


def water_km2(blue: np.ndarray, red: np.ndarray, valid: np.ndarray, min_valid: float) -> float | None:
    """Water (blue–red NDWI > 0.3) within 1.25 km of the tile centre, km²;
    scaled up for the invalid part, None when too little is visible."""
    n = blue.shape[0]
    near = near_mask(n)
    vf = float(valid[near].mean())
    if vf < min_valid:
        return None
    with np.errstate(invalid='ignore', divide='ignore'):
        ndwi = (blue - red) / (blue + red)
    wet = valid & near & np.isfinite(ndwi) & (ndwi > NDWI_MIN)
    px = (TILE_M / n) ** 2 / 1e6
    return round(float(wet.sum()) * px / vf, 3)


def to8(rgb: np.ndarray, valid: np.ndarray) -> np.ndarray:
    out = (np.clip(np.nan_to_num(rgb), 0, 1) * 255).astype(np.uint8)
    out[~valid] = 0
    return out


def resize(frame: np.ndarray, valid: np.ndarray | None = None) -> np.ndarray:
    if frame.shape[0] == SIZE:
        return frame
    out = np.asarray(Image.fromarray(frame).resize((SIZE, SIZE), Image.BICUBIC))
    if valid is not None:   # keep the no-data cuts sharp and black
        v = np.asarray(Image.fromarray(valid.astype(np.uint8) * 255).resize((SIZE, SIZE), Image.NEAREST)) > 0
        out = out.copy(); out[~v] = 0
    return out


def encode(frames: np.ndarray, out_mp4) -> None:
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.Popen([
        'ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{SIZE}x{SIZE}',
        '-framerate', str(FPS), '-i', '-', '-c:v', 'libx264', '-crf', '20', '-g', '4', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', '-r', str(FPS), str(out_mp4),
    ], stdin=subprocess.PIPE)
    p.stdin.write(np.ascontiguousarray(frames).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f'ffmpeg failed: {out_mp4}')


# ─── the four tracks ───────────────────────────────────────────────────
def track_modis(lake: dict, year: int):
    z = np.load(STACK_DIR / f'modis_{year}' / f"{lake['id']}.npz")
    small = z['frames']                                   # (153, 41, 41, 3)
    n = small.shape[1]
    idx = np.minimum((np.arange(SIZE) * n / SIZE).astype(int), n - 1)    # nearest: the 250 m pixels stay blocks
    frames = small[:, idx][:, :, idx]
    sat = [str(s) for s in z['sat']]
    meta = {
        'label': 'MODIS · 250 m',
        'has': ''.join('1' if s else '0' for s in sat),
        'sensor': ''.join(s or '.' for s in sat),          # T = Terra, Q = Aqua
        'cloud': [None if c < 0 else int(c) for c in z['cloud']],
        'water_km2': [None if not np.isfinite(w) else float(w) for w in z['water']],
    }
    return frames, meta


def _saturated(band: np.ndarray) -> np.ndarray:
    """ETM+'s 8-bit visible bands clip over bright snow, each at its own
    ceiling (green lowest) — a flat top in the scene."""
    v = band[band > 0]
    if v.size == 0:
        return np.zeros(band.shape, bool)
    at = band >= int(v.max()) - 1
    return at if at.sum() > 0.003 * v.size else np.zeros(band.shape, bool)


def l7_frame(a: np.ndarray):
    """(4, 342, 342) blue, green, red (30 m) + pan (15 m), TOA × 1e4 →
    pan-sharpened RGB, validity, and the 30 m blue / red for the water test.
    Where a visible band is clipped the pixel is drawn neutral at its
    brightest band (clipping would tint the snow purple or yellow)."""
    b, g, r, pan = (a[k].astype(np.float32) / 1e4 for k in range(4))
    ms_valid = (a[0] > 0) & (a[1] > 0) & (a[2] > 0)
    pan_valid = a[3] > 0
    n = a.shape[1] // 2
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        p30 = np.nanmean(np.where(pan_valid, pan, np.nan).reshape(n, 2, n, 2), axis=(1, 3))
    p30u = np.repeat(np.repeat(p30, 2, 0), 2, 1)
    ratio = np.where(pan_valid & np.isfinite(p30u) & (p30u > 0.02), pan / np.maximum(p30u, 0.02), 1.0)
    rgb = np.stack([r, g, b], -1)
    sat = _saturated(a[0]) | _saturated(a[1]) | _saturated(a[2])
    rgb[sat] = rgb[sat].max(axis=-1, keepdims=True)
    rgb = rgb * np.clip(ratio, 0.5, 2.0)[..., None]
    return to8(rgb, ms_valid), ms_valid, b, r


def aster_frame(a: np.ndarray, gain: list[float], sun_elev: float, day: str):
    import datetime as dt
    doy = dt.date.fromisoformat(day).timetuple().tm_yday
    d = 1 - 0.01672 * np.cos(2 * np.pi * (doy - 4) / 365.25)
    valid = a[0] > 0
    rho = [np.pi * np.maximum(a[k].astype(np.float32) - 1, 0) * gain[k] * d * d / (ASTER_ESUN[k] * np.sin(np.radians(sun_elev))) for k in range(3)]
    green, red = rho[0], rho[1]
    blue = green + 0.6 * (green - red)
    return to8(np.stack([red, green, blue], -1), valid), valid


def track_hires_2010(lake: dict):
    f = STACK_DIR / 'hires_2010' / f"{lake['id']}.npz"
    if not f.exists():
        return None
    z = np.load(f)
    days = season_days(2010)
    frames = np.zeros((len(days), SIZE, SIZE, 3), np.uint8)
    sensor = ['.'] * len(days)
    water: list = [None] * len(days)
    valid_pct: list = [None] * len(days)
    ameta = json.loads(str(z['aster_meta'])) if 'aster_meta' in z else {}
    b5f = STACK_DIR / 'hires_2010_b5' / f"{lake['id']}.npz"
    b5 = dict(zip((str(d) for d in np.load(b5f)['days']), np.load(b5f)['b5'])) if b5f.exists() else {}
    cloud: list = [None] * len(days)
    cands: dict[int, list] = {}
    for k, day in enumerate(str(d) for d in z['l7_days']):
        if day in days:
            fr, v, b, r = l7_frame(z['l7'][k])
            w = water_km2(b, r, v, 0.6)
            cl = None
            if day in b5:      # cloud over ice: bright at 1.65 µm (ice ~0.02, fresh snow ~0.12 and even, cloud 0.1–0.45 and patchy)
                s5 = b5[day].astype(np.float32) / 1e4
                ok = s5 > 0
                if ok.mean() > 0.1:
                    p10, p50, p90 = np.percentile(s5[ok], [10, 50, 90])
                    cl = round(float((s5[ok] > 0.16).mean()) * 100)
                    if p90 > 0.16 or (p50 > 0.05 and p90 - p10 > 0.05):
                        w = None          # the lake cannot be measured through it
                        cl = max(cl, 50)
            cands.setdefault(days.index(day), []).append((float(v.mean()), 'L', fr, v, w, cl))
    for k, day in enumerate(str(d) for d in z['aster_days']):
        m = ameta.get(day)
        if day in days and m and (m['sun_elev'] or 0) > 20:      # the midnight-sun passes are too dark to read
            fr, v = aster_frame(z['aster'][k], m['gain'], m['sun_elev'], day)
            cands.setdefault(days.index(day), []).append((float(v.mean()), 'A', fr, v, None, None))
    for di, lst in cands.items():
        vf, s, fr, v, w, cl = max(lst, key=lambda t: t[0])
        if vf < 0.15:
            continue
        frames[di] = resize(fr, v)
        sensor[di] = s
        water[di] = w
        cloud[di] = cl
        valid_pct[di] = round(vf * 100)
    meta = {
        'label': 'Landsat 7 · ASTER · 15 m',
        'has': ''.join('0' if s == '.' else '1' for s in sensor),
        'sensor': ''.join(sensor),                          # L = Landsat 7 ETM+ (pan-sharpened), A = ASTER
        'valid_pct': valid_pct,
        'cloud': cloud,                                    # Landsat 7 only (1.65 µm test); ≥ 50 = the lake cannot be measured
        'water_km2': water,
        'note': 'Landsat 7: 30 m colour sharpened by the 15 m panchromatic band; black stripes are the scan-line-corrector gaps. '
                'ASTER: 15 m green/red, blue synthesised (no blue band).',
    }
    return frames, meta


SCL_CLOUD = (3, 8, 9, 10)      # sat-tile-stack's definition: shadow, cloud (medium, high), cirrus


def track_s2_2019(lake: dict):
    f = STACK_DIR / 's2_2019_gee' / f"{lake['id']}.npz"
    if not f.exists():
        return None
    z = np.load(f)
    days = season_days(2019)
    frames = np.zeros((len(days), SIZE, SIZE, 3), np.uint8)
    has = ['0'] * len(days)
    cloud: list = [None] * len(days)
    water: list = [None] * len(days)
    near = near_mask(SIZE)
    for k, day in enumerate(str(d) for d in z['days']):
        if day not in days:
            continue
        a = z['rgb'][k].astype(np.float32) * 0.004        # (3, y, x) red, green, blue reflectance
        valid = z['rgb'][k].max(axis=0) > 0
        if valid.mean() < 0.02:
            continue
        di = days.index(day)
        frames[di] = to8(np.transpose(a, (1, 2, 0)), valid)
        has[di] = '1'
        cl = np.isin(z['scl'][k], SCL_CLOUD)
        cloud[di] = round(float(cl[valid].mean()) * 100)
        if (near & valid).any() and float(cl[near & valid].mean()) <= 0.3:
            water[di] = water_km2(a[2], a[0], valid, 0.8)
    meta = {
        'label': 'Sentinel-2 · 10 m',
        'has': ''.join(has),
        'sensor': ''.join('S' if h == '1' else '.' for h in has),
        'cloud': cloud,
        'water_km2': water,
    }
    return frames, meta


TRACKS = (
    (2010, 'modis', lambda lk: track_modis(lk, 2010)),
    (2010, 'hires', track_hires_2010),
    (2019, 'modis', lambda lk: track_modis(lk, 2019)),
    (2019, 'hires', track_s2_2019),
)


def pick_thumb(frames: np.ndarray, meta: dict, days: list[str], before: str | None) -> np.ndarray | None:
    """The frame that shows the lake best: most water among the well-covered
    frames (before `before` when given), else the best-covered frame."""
    best, score = None, -1.0
    for i, h in enumerate(meta['has']):
        if h != '1' or (before and days[i] >= before):
            continue
        w = meta['water_km2'][i]
        cov = float((frames[i].max(axis=-1) > 0).mean())
        cl = (meta.get('cloud') or [None] * len(days))[i]
        s = (w or 0.0) + 0.05 * cov - (0.5 if (cl or 0) > 30 else 0.0)
        if cov >= 0.6 and s > score:
            best, score = i, s
    return None if best is None else frames[best]


def one(args: tuple[dict, bool]) -> str:
    lake, force = args
    msgs = []
    for year, track, fn in TRACKS:
        mp4 = MOVIE_DIR / 'movies' / str(year) / track / f"{lake['id']}.mp4"
        mfile = META_DIR / f"{year}_{track}_{lake['id']}.json"
        if mp4.exists() and mfile.exists() and not force:
            continue
        got = fn(lake)
        if got is None:
            msgs.append(f'{year}/{track}: no input yet')
            continue
        frames, meta = got
        encode(frames, mp4)
        days = season_days(year)
        meta.update({'src': f"movies/{year}/{track}/{lake['id']}.mp4", 'n_images': meta['has'].count('1'),
                     'bytes': mp4.stat().st_size})
        META_DIR.mkdir(parents=True, exist_ok=True)
        mfile.write_text(json.dumps(meta))
        if track == 'hires':
            th = pick_thumb(frames, meta, days, '2010-06-06' if year == 2010 else None)
            if th is None and year == 2010:
                th = pick_thumb(frames, meta, days, None)
            if th is not None:
                t = MOVIE_DIR / 'thumbs' / str(year) / f"{lake['id']}.jpg"
                t.parent.mkdir(parents=True, exist_ok=True)
                Image.fromarray(th).resize((256, 256), Image.LANCZOS).save(t, quality=86)
        msgs.append(f"{year}/{track}: {meta['n_images']} images, {mp4.stat().st_size / 1e6:.1f} MB")
    return f"{lake['id']}: " + ('; '.join(msgs) or 'up to date')


def main() -> None:
    force = '--force' in sys.argv
    ids = [a for a in sys.argv[1:] if not a.startswith('--')]
    lakes = json.loads((WORK / 'c18_lakes.json').read_text())['lakes']
    if ids:
        lakes = [lk for lk in lakes if lk['id'] in ids]
    with ProcessPoolExecutor(4) as ex:
        for msg in ex.map(one, [(lk, force) for lk in lakes]):
            print(msg, flush=True)


if __name__ == '__main__':
    assert SEASONS
    main()
