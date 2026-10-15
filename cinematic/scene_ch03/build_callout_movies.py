"""Chapter 3 beat 0's callout movies: each featured lake's season with the
days that have NO acquisition dropped (the director asked for the black
tiles to go while the imagery stays in sync — the panels wait for each
other — at 2 fps; the valid-frame rule).

Validity is the stack's OWN `pct_nans` (percent of the tile with no
reflectance), never a brightness guess: a frame is kept when
pct_nans < 1, i.e. the whole tile was imaged. That drops the no-pass
days (pct_nans = 100) and the swath-edge days (a partial black wedge;
only CW2019_2330 has them). Cloudy frames are KEPT — they are data the
labelers saw; no extra cloud cut is applied here.

The site builds ONE season clock from these five sidecars (the union of
the kept dates): all five panels always show the clock's date, and a lake
with no new frame on a clock date HOLDS its last kept frame.

Outputs (cinematic/scene_ch03/output_callouts/ → R2 ch03/lakes_valid/):
  <id>.mp4   kept frames only, 1 fps, a keyframe every GOP frames and no
             B-frames, so a seek decodes at most GOP frames
  <id>.json  {lake_id, t0, days, fps, frame_count, frames:[{day, date_iso,
             p_water}], p_water_daily:[153 values | null]}

The label demo reads these valid-frame movies too (ch03/lakes_valid/);
the full 153-frame ch03/lakes/ set is retired.

Run (from the defense checkout root, a Python env with cinematic/requirements.txt installed):
  nice -n 15 python -u \
      cinematic/scene_ch03/build_callout_movies.py
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import xarray as xr
from PIL import Image

sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared import SOURCE_DATA, require_source  # noqa: E402

STACK_DIR = SOURCE_DATA / 'stacks' / 'CW_2019'
OUT_DIR = Path('cinematic/scene_ch03/output_callouts')
FRAMES_DIR = OUT_DIR / '_frames'

T0 = '2019-05-01'
T1 = '2019-09-30'
S2_QUANT = 10000.0
MAX_PCT_NANS = 1.0  # percent

# Same five lakes + class colours as build_featured_lakes.py (Fig. 4).
LAKES = [
    ('CW2019_1889', '#4caf50'),  # HF
    ('CW2019_1848', '#42a5f5'),  # MD
    ('CW2019_1907', '#ff9800'),  # LD
    ('CW2019_2330', '#ab47bc'),  # CD
    ('CW2019_1597', '#e8524a'),  # ND
]


def hex_to_rgb(h: str) -> tuple:
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lake_outline_mask(lake_boundary: np.ndarray, thickness: int = 2) -> np.ndarray:
    """The outline burned into the movie — build_featured_lakes.py's recipe."""
    m = (lake_boundary > 0).astype(np.uint8)
    pad = np.pad(m, 1, mode='edge')
    nb_min = np.minimum.reduce([
        pad[0:-2, 0:-2], pad[0:-2, 1:-1], pad[0:-2, 2:],
        pad[1:-1, 0:-2],                  pad[1:-1, 2:],
        pad[2:,   0:-2], pad[2:,   1:-1], pad[2:,   2:],
    ])
    outline = (m == 1) & (nb_min == 0)
    for _ in range(thickness - 1):
        pad = np.pad(outline.astype(np.uint8), 1, mode='edge')
        nb_max = np.maximum.reduce([
            pad[0:-2, 1:-1], pad[1:-1, 0:-2], pad[1:-1, 2:], pad[2:, 1:-1],
        ])
        outline = nb_max > 0
    return outline


CRF = '23'
GOP = '6'


def encode(lake_id: str) -> Path:
    out_mp4 = OUT_DIR / f'{lake_id}.mp4'
    subprocess.run([
        'ffmpeg', '-y', '-loglevel', 'error',
        '-framerate', '1', '-i', str(FRAMES_DIR / lake_id / 'f%04d.png'),
        '-c:v', 'libx264', '-crf', CRF, '-preset', 'slow', '-pix_fmt', 'yuv420p',
        '-g', GOP, '-bf', '0',
        '-movflags', '+faststart', '-r', '1', str(out_mp4),
    ], check=True)
    return out_mp4


def build(lake_id: str, color: str) -> dict:
    ds = xr.open_dataset(require_source(STACK_DIR / f'{lake_id}.nc'))
    t = ds['time'].values
    sel = (t >= np.datetime64(T0)) & (t <= np.datetime64(T1 + 'T23:59:59'))
    ds = ds.isel(time=sel)
    n = ds.sizes['time']
    times = ds['time'].values
    pct_nans = ds['pct_nans'].values
    p_water = ds['p_water'].values
    band_names = [str(x) for x in ds['common_name'].values]
    rgb_idx = [band_names.index(b) for b in ('red', 'green', 'blue')]
    outline = lake_outline_mask(ds['lake_boundary'].values, thickness=2)
    orgb = hex_to_rgb(color)

    day0 = np.datetime64(T0)
    fdir = FRAMES_DIR / lake_id
    fdir.mkdir(parents=True, exist_ok=True)
    for old in fdir.glob('*.png'):
        old.unlink()
    # One read of the RGB cube (a per-day isel re-inflates the netCDF's
    # chunks every time — minutes per lake).
    cube = ds['reflectance'].isel(band=rgb_idx).values

    kept = []
    for i in range(n):
        pn = pct_nans[i]
        if not np.isfinite(pn) or pn >= MAX_PCT_NANS:
            continue
        refl = cube[i]
        if np.isnan(refl).all():  # belt and braces: pct_nans said imaged
            continue
        r = np.clip(np.nan_to_num(refl) / S2_QUANT, 0.0, 1.0)
        frame = (np.transpose(r, (1, 2, 0)) * 255.0).clip(0, 255).astype(np.uint8)
        frame[outline] = orgb
        Image.fromarray(frame).save(fdir / f'f{len(kept):04d}.png', compress_level=1)
        day = int((times[i].astype('datetime64[D]') - day0) / np.timedelta64(1, 'D'))
        pw = p_water[i]
        kept.append({
            'day': day,
            'date_iso': str(times[i])[:10],
            'p_water': None if np.isnan(pw) else round(float(pw), 4),
        })

    out_mp4 = encode(lake_id)

    daily = [None if np.isnan(p) else round(float(p), 4) for p in p_water]
    sidecar = {
        'lake_id': lake_id,
        't0': T0,
        'days': n,
        'fps': 1.0,
        'frame_count': len(kept),
        'valid_rule': f'pct_nans < {MAX_PCT_NANS} (percent of the tile unimaged)',
        'frames': kept,
        'p_water_daily': daily,
        'source': 'Sentinel-2 L2A · Microsoft Planetary Computer',
    }
    (OUT_DIR / f'{lake_id}.json').write_text(json.dumps(sidecar, separators=(',', ':')))
    mb = out_mp4.stat().st_size / 1e6
    print(f'  {lake_id}: kept {len(kept)}/{n} · first {kept[0]["date_iso"]} · {mb:.2f} MB')
    return sidecar


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if '--encode-only' in sys.argv:  # re-encode the kept frames (_frames/<id>/)
        for lid, _ in LAKES:
            print(f'  {lid}: {encode(lid).stat().st_size / 1e6:.2f} MB')
        return
    cars = [build(lid, col) for lid, col in LAKES]
    clock = sorted({f['day'] for sc in cars for f in sc['frames']})
    print(f'season clock: {len(clock)} dates of {cars[0]["days"]} '
          f'({len(clock) / 2:.0f} s at 2 fps)')
    print('\nupload:\n  rclone copy cinematic/scene_ch03/output_callouts '
          'r2:<bucket>/ch03/lakes_valid/ --header-upload "Cache-Control: public, max-age=31536000, immutable"')


if __name__ == '__main__':
    main()
