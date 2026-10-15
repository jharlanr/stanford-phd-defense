"""
Bake the monthly Greenland ice-speed time series for the Introduction's
"the seasons" steps: the ice speeds up every summer. Phase 1 baked turbo
colour frames; phase 2 (this file) bakes DATA textures the globe colours
itself, so a month is a drop-in for the "Greenland flows" speed drape
(greenland_speed_nasa_v1.webp).

DATA
    NASA MEaSUREs Greenland Monthly Ice Sheet Velocity Mosaics from SAR and
    Landsat, NSIDC-0731 v5 (Joughin 2023), fetched by
    fetch_velocity_series.py as 800 m speed overviews (whole sheet) and a
    400 m central-west window. Dec 2014 - Nov 2024, 120 months.
        Joughin, I. (2023). MEaSUREs Greenland Monthly Ice Sheet Velocity
        Mosaics from SAR and Landsat. (NSIDC-0731, Version 5). NASA NSIDC
        DAAC. https://doi.org/10.5067/EGKZX6FXXM4P
        Joughin, I., Smith, B. E., & Howat, I. (2018). Greenland Ice
        Mapping Project: ice flow velocity variation at sub-monthly to
        decadal timescales. The Cryosphere, 12, 2211-2227.
        https://doi.org/10.5194/tc-12-2211-2018
    Licence: NASA EOSDIS open data, no restriction on use; cite the dataset.
    Ice mask: BedMachine Greenland v6 (Morlighem et al.), `mask` (GIMP).
    Static speed (the drape's): ITS_LIVE v2.1 120 m 0000 composite, the
    480 m block mean build_flow_trails.py caches (data/flow/its_live_480m.npz).
    Slow-ice blend weight + last-resort gap fill: the 3.6 km ITS_LIVE subset
    (data/its_live_greenland_subset.nc).

WHAT THE GLOBE SHOWS (why data textures, not colour frames)
    The speed drape is 8192 x 3152, coloured from ITS_LIVE at 480 m. The
    monthly mosaics are 800 m data, here on a 1200 x 1400 grid (~2 km both
    ways at 70 N). Swapping colour
    frames for the drape would soften every outlet the moment the month
    appears and shift colours by the two products' bias. Instead the
    shader draws

        t_month = t_static + DELTA / log10(vmax / vmin)
        colour  = NASA palette (config/velocityPalette.json) at t_month

    where t_static is the drape's own log-speed fraction (speed_t_v1.webp,
    the SAME field, the SAME geometry as build_flow_trails.build_drape) and

        DELTA = w * (log10 v_month - log10 v_median)          [decades]

    v_month = this month's NSIDC-0731 speed (gap-filled, GAP POLICY),
    v_median = the pixel's 2014-2024 median of OBSERVED months (>= 12),
    w = the slow-ice blend weight (0 at v_static <= 20 m/yr, 1 at >= 60 m/yr,
    log-linear; the monthly errors of ~5-20 m/yr swamp slower ice). So the
    globe shows the ITS_LIVE composite's spatial detail multiplied by
    NSIDC-0731's monthly change relative to its own median: a month at its
    median speed IS the drape, pixel for pixel. Only LAND ICE (BedMachine
    mask >= 50 % of the pixel) moves; DELTA = 0 elsewhere.

    The anomaly view colours pct = 100 * (v_month / ref - 1), ref = the
    pixel's centred 12-month running median (seasonal anomaly: the
    interannual trend removed), RdBu_r at +/-ANOM_LIM %, neutral grey where
    the month is climatology/static-filled (codes 3-4) and fading to grey as
    v_static goes 40 -> 15 m/yr (noise), exactly as phase 1 did.

OUTPUTS -> cinematic/data/intro/seasons/ (R2 prefix intro/seasons/)
    speed_t_v1.webp             8192 x 3152 greyscale, byte = round(255 t_static)
    frames/m_YYYYMM.webp        1200 x 1400 RGB, LOSSLESS, one per month
                                (Jan 2015 - Nov 2024), same lon/lat extent:
        R = 128 + 256 * DELTA, in steps of 2  (DELTA clipped to +/-0.496 dec)
        G = 128 + 127 * pct / ANOM_LIM, in steps of 4 (1..255; 128 = invalid)
        B = 255 where the anomaly is valid (observed or interpolated, and
            v_static above the fade), else 0
    manifest.json               what the page reads: frames + coverage, the
                                encodings, the anomaly colour stops, three
                                region curves with their boxes in lat/lon
    qa/                         difference images vs the drape, emulated
                                contact sheets, region curves (not for R2)
    cache: source_data/velocity_series/nsidc0731_v5/_derived/stack_*.npy
    (1.2 GB reprojected stack; deleted at the end unless --keep-cache)

GAP POLICY (per ice pixel, per month; coverage fractions in the manifest)
    1 observed
    2 linear interpolation between the observed month before AND after
    3 median of that calendar month over all years with an observation
      (needs >= 2 years)
    4 static ITS_LIVE composite (DELTA = 0)
    0 nothing

Run (~10 min):
    cd cinematic
    nice -n 15 python \
        scene_01_intro/bake_velocity_series.py
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from PIL import Image  # noqa: E402
from rasterio.transform import from_bounds  # noqa: E402
from rasterio.warp import Resampling, reproject  # noqa: E402

HERE = Path(__file__).resolve().parent
CINEMATIC_DIR = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(CINEMATIC_DIR))
SRC = CINEMATIC_DIR / "source_data" / "velocity_series" / "nsidc0731_v5"
STATIC_NC = CINEMATIC_DIR / "data" / "its_live_greenland_subset.nc"
BEDMACHINE = CINEMATIC_DIR / "source_data" / "data" / "BedMachineGreenland-v6.nc"
DRAPE_SHIPPED = CINEMATIC_DIR.parent / "website" / ".r2-cache" / "shared" / "greenland_speed_nasa_v1.webp"
SPEED_BLEND = (20.0, 60.0)     # m/yr: 0 % monthly at <= 20, 100 % at >= 60
ANOM_FADE = (15.0, 40.0)       # m/yr: grey at <= 15, full colour at >= 40
ANOM_GREY = 0.55               # neutral grey (sRGB fraction): light enough that a swath edge
                               # (observed-and-usual white | no-signal grey) does not shout
OUT = CINEMATIC_DIR / "data" / "intro" / "seasons"
CACHE = SRC / "_derived"

LON_W, LON_E, LAT_S, LAT_N = -75.0, -10.0, 59.0, 84.0
ANOM_CMAP = "RdBu_r"
DELTA_SCALE = 256.0            # R byte per decade
DELTA_MAX = 127.0 / DELTA_SCALE
MEDIAN_MIN_OBS = 12
ANOM_STEP = 4                  # G quantum, bytes (1.6 % of anomaly)
DELTA_STEP = 2                 # R quantum, bytes (1.8 % of speed)

# Named regions: boxes in EPSG:3413 km (xmin, xmax, ymin, ymax). Chosen on
# the 2016 median speed map (phase 1, qa/regions_locator.png).
REGIONS = {
    "sermeq_kujalleq": dict(
        name="Sermeq Kujalleq (Jakobshavn Isbrae), trunk 10-20 km above the 2016 front",
        label="Jakobshavn", box=(-178, -168, -2282, -2274), kind="marine"),
    "russell_isunnguata": dict(
        name="Russell / Isunnguata Sermia sector, land-terminating ablation zone 10-50 km inland",
        label="Russell / Isunnguata Sermia", box=(-215, -175, -2520, -2480), kind="land"),
    "cw_interior": dict(
        name="Central-west, ~150 km inland (upper ablation / lower accumulation zone)",
        label="Central-west interior", box=(-80, -40, -2520, -2480), kind="interior"),
    "helheim": dict(name="Helheim Glacier trunk", label="Helheim",
                    box=(282, 292, -2582, -2575), kind="marine"),
    "kangerlussuaq_glacier": dict(
        name="Kangerlussuaq Glacier (SE) trunk", label="Kangerlussuaq Glacier",
        box=(474, 484, -2286, -2278), kind="marine"),
    "petermann": dict(name="Petermann Glacier near the grounding zone", label="Petermann",
                      box=(-276, -266, -985, -975), kind="marine"),
    "nioghalvfjerdsfjorden": dict(name="79N Glacier (Nioghalvfjerdsfjorden)", label="79N Glacier",
                                  box=(468, 478, -1036, -1026), kind="marine"),
}
# The curves the page draws (the rest stay in qa/).
SITE_REGIONS = ("russell_isunnguata", "sermeq_kujalleq", "petermann")


# --------------------------------------------------------------------------
def month_list() -> list[str]:
    return sorted(Path(f).stem[3:] for f in glob.glob(str(SRC / "gl_800m" / "vv_*.tif")))


def dst_transform(w: int, h: int):
    return from_bounds(LON_W, LAT_S, LON_E, LAT_N, w, h)


def reproject_to_drape(arr, src_transform, w, h, resampling=Resampling.average):
    dst = np.full((h, w), np.nan, dtype=np.float32)
    reproject(arr.astype(np.float32), dst, src_transform=src_transform, src_crs="EPSG:3413",
              src_nodata=np.nan, dst_transform=dst_transform(w, h), dst_crs="EPSG:4326",
              dst_nodata=np.nan, resampling=resampling)
    return dst


def load_stack(months, w, h) -> np.ndarray:
    """(T, H, W) speed on the drape grid, NaN = not observed. Cached."""
    CACHE.mkdir(exist_ok=True)
    cache = CACHE / f"stack_{w}x{h}_{months[0]}_{months[-1]}.npy"
    if cache.exists():
        return np.load(cache, mmap_mode="r")
    stack = np.full((len(months), h, w), np.nan, dtype=np.float32)
    for i, ym in enumerate(months):
        with rasterio.open(SRC / "gl_800m" / f"vv_{ym}.tif") as s:
            a = s.read(1).astype(np.float32)
            a[a <= 0] = np.nan
            stack[i] = reproject_to_drape(a, s.transform, w, h)
        print(f"  reprojected {ym}", end="\r", flush=True)
    print()
    np.save(cache, stack)
    return stack


def load_static(w, h) -> np.ndarray:
    import xarray as xr
    ds = xr.open_dataset(STATIC_NC)
    v = ds["v"].values.astype(np.float32)
    v[~np.isfinite(v) | (v <= 0)] = np.nan
    x, y = ds["x"].values, ds["y"].values
    dx, dy = float(x[1] - x[0]), float(y[1] - y[0])        # dy < 0 (north first)
    tr = rasterio.transform.from_origin(x[0] - dx / 2, y[0] - dy / 2, dx, -dy)
    return reproject_to_drape(v, tr, w, h, Resampling.bilinear)


def ice_fraction(w, h) -> np.ndarray:
    """Fraction of each drape pixel that is land ice (BedMachine v6 mask 2|3,
    i.e. GIMP ice mask incl. peripheral glaciers), from the 150 m grid."""
    import xarray as xr
    ds = xr.open_dataset(BEDMACHINE)
    m = ds["mask"].values
    ice = ((m == 2) | (m == 3)).astype(np.float32)
    x0, y0 = float(ds["x"][0]), float(ds["y"][0])
    tr = rasterio.transform.from_origin(x0 - 75, y0 + 75, 150, 150)
    return reproject_to_drape(ice, tr, w, h, Resampling.average)


# --------------------------------------------------------------------------
def fill_stack(obs: np.ndarray, static: np.ndarray, months):
    """Return filled (T,H,W) float32 and code (T,H,W) uint8 per GAP POLICY."""
    T = obs.shape[0]
    filled = np.array(obs, dtype=np.float32)
    code = np.where(np.isfinite(filled), 1, 0).astype(np.uint8)
    # 2: single-month gap between two observed months
    for t in range(1, T - 1):
        m = (code[t] == 0) & np.isfinite(obs[t - 1]) & np.isfinite(obs[t + 1])
        filled[t][m] = 0.5 * (obs[t - 1][m] + obs[t + 1][m])
        code[t][m] = 2
    # 3: calendar-month median over years (observed only, >= 2 years)
    cal = np.array([int(ym[4:]) for ym in months])
    for mo in range(1, 13):
        idx = np.where(cal == mo)[0]
        sub = obs[idx]
        n = np.isfinite(sub).sum(0)
        with np.errstate(all="ignore"):
            med = np.nanmedian(sub, axis=0)
        med[n < 2] = np.nan
        for t in idx:
            m = (code[t] == 0) & np.isfinite(med)
            filled[t][m] = med[m]
            code[t][m] = 3
    # 4: static composite
    for t in range(T):
        m = (code[t] == 0) & np.isfinite(static)
        filled[t][m] = static[m]
        code[t][m] = 4
    return filled, code


def running_median(filled: np.ndarray, code: np.ndarray, half=6) -> np.ndarray:
    """Centred 12-month running median of OBSERVED+interpolated values
    (codes 1-2) per pixel; windows clamp at the series ends."""
    T = filled.shape[0]
    base = np.where(code <= 2, filled, np.nan).astype(np.float32)
    base[code == 0] = np.nan
    ref = np.full_like(base, np.nan)
    for t in range(T):
        lo = max(0, t - half)
        hi = min(T, lo + 2 * half)
        lo = max(0, hi - 2 * half)
        win = base[lo:hi]
        n = np.isfinite(win).sum(0)
        with np.errstate(all="ignore"):
            r = np.nanmedian(win, axis=0)
        r[n < 6] = np.nan
        ref[t] = r
    return ref


def log_ramp(v: np.ndarray, lo_hi) -> np.ndarray:
    """0 at v <= lo, 1 at v >= hi, linear in log10(v) between; NaN -> 0."""
    lo, hi = lo_hi
    with np.errstate(all="ignore"):
        r = (np.log10(v) - np.log10(lo)) / (np.log10(hi) - np.log10(lo))
    return np.clip(np.nan_to_num(r, nan=0.0), 0, 1).astype(np.float32)

def region_series(months) -> dict:
    """Median speed in each REGIONS box from the native 800 m grids."""
    with rasterio.open(SRC / "gl_800m" / f"vv_{months[0]}.tif") as s:
        T = s.transform
    sl = {}
    for k, r in REGIONS.items():
        x0, x1, y0, y1 = (v * 1e3 for v in r["box"])
        c0, r0 = ~T * (x0, y1)
        c1, r1 = ~T * (x1, y0)
        sl[k] = (slice(int(r0), int(r1)), slice(int(c0), int(c1)))
    out = {k: dict(speed_obs=[], coverage=[]) for k in REGIONS}
    for ym in months:
        with rasterio.open(SRC / "gl_800m" / f"vv_{ym}.tif") as s:
            a = s.read(1)
        for k in REGIONS:
            sub = a[sl[k]]
            v = sub[sub > 0]
            c = v.size / sub.size
            out[k]["coverage"].append(round(float(c), 3))
            out[k]["speed_obs"].append(round(float(np.median(v)), 1) if c >= 0.5 else None)
    for k in REGIONS:
        y = np.array([np.nan if v is None else v for v in out[k]["speed_obs"]], float)
        ok = np.isfinite(y)
        yi = np.interp(np.arange(len(y)), np.where(ok)[0], y[ok]) if ok.sum() > 1 else y
        out[k]["speed"] = [round(float(v), 1) for v in yi]
        out[k]["interpolated"] = [bool(not o) for o in ok]
        # seasonal anomaly: vs centred 12-month running median of the curve
        ref = np.array([np.nanmedian(y[max(0, min(len(y) - 12, t - 6)):max(0, min(len(y) - 12, t - 6)) + 12])
                        for t in range(len(y))])
        out[k]["anomaly_pct"] = [None if not np.isfinite(a) else round(float(a), 1)
                                 for a in 100 * (y / ref - 1)]
        # per glaciological year: summer peak (max May-Sep, observed) vs the
        # median of the preceding Jan-Apr (observed)
        yrs = {}
        for yr in sorted({int(m[:4]) for m in months}):
            win = [y[i] for i, m in enumerate(months) if m[:4] == str(yr) and 1 <= int(m[4:]) <= 4]
            summ = [(y[i], m) for i, m in enumerate(months)
                    if m[:4] == str(yr) and 5 <= int(m[4:]) <= 9 and np.isfinite(y[i])]
            win = [v for v in win if np.isfinite(v)]
            if len(win) >= 2 and summ:
                pk, pm = max(summ)
                yrs[str(yr)] = dict(winter_median=round(float(np.median(win)), 1),
                                    summer_peak=round(float(pk), 1), peak_month=pm[4:],
                                    peak_pct=round(float(100 * (pk / np.median(win) - 1)), 1))
        out[k]["summer_peak_vs_winter"] = yrs
        out[k].update(name=REGIONS[k]["name"], box_epsg3413_km=REGIONS[k]["box"],
                      kind=REGIONS[k]["kind"])
    return out



# --------------------------------------------------------------------------
# The drape's own log-speed fraction (build_flow_trails.build_drape, minus
# the colour step).
def static_t_hi() -> tuple[np.ndarray, np.ndarray, int, int]:
    """(t, ice_alpha) on the drape's 8192 x 3152 grid: t in [0, 1] exactly as
    build_drape computes it before the palette lookup."""
    import build_flow_trails as bft
    from pyproj import Transformer
    from scipy import ndimage
    d = bft.load_coarse(False)
    vmin, vmax = bft.palette_lut()[1:]
    v = d["v"].astype(np.float32)
    ice = np.nan_to_num(d["ice"].astype(np.float32))
    valid = np.isfinite(v) & (v > 0)
    logv = np.log10(np.clip(np.where(valid, v, 1.0), 1e-3, None))
    logv = bft.fill_nearest(logv, valid)
    x, y = d["x"], d["y"]
    dx, dy = x[1] - x[0], y[1] - y[0]
    W, H = bft.DRAPE_W, bft.DRAPE_H
    lon = LON_W + (np.arange(W) + 0.5) / W * (LON_E - LON_W)
    lat = LAT_N - (np.arange(H) + 0.5) / H * (LAT_N - LAT_S)
    tr = Transformer.from_crs("EPSG:4326", "EPSG:3413", always_xy=True)
    t = np.zeros((H, W), np.float32)
    a = np.zeros((H, W), np.float32)
    for r0 in range(0, H, 394):
        r1 = min(H, r0 + 394)
        LON, LAT = np.meshgrid(lon, lat[r0:r1])
        X, Y = tr.transform(LON, LAT)
        coords = np.stack([((Y - y[0]) / dy).ravel(), ((X - x[0]) / dx).ravel()])
        lv = ndimage.map_coordinates(logv, coords, order=1, mode="nearest").reshape(X.shape)
        m = ndimage.map_coordinates(ice, coords, order=1, mode="constant", cval=0).reshape(X.shape)
        t[r0:r1] = np.clip((lv - np.log10(vmin)) / (np.log10(vmax) - np.log10(vmin)), 0, 1)
        a[r0:r1] = np.clip((m - 0.35) / 0.3, 0, 1)
    return t, a, W, H


def speed_lut() -> tuple[np.ndarray, float, float]:
    import build_flow_trails as bft
    return bft.palette_lut()


def anom_stops(n: int = 21) -> list[list]:
    """RdBu_r sampled at n stops: [fraction, '#rrggbb'] (fraction 0 = -lim)."""
    cmap = plt.get_cmap(ANOM_CMAP)
    out = []
    for f in np.linspace(0, 1, n):
        r, g, b, _ = cmap(f)
        out.append([round(float(f), 4), "#%02x%02x%02x" % tuple(int(round(c * 255)) for c in (r, g, b))])
    return out


def stops_lut(stops, n=1024) -> np.ndarray:
    fr = np.array([s[0] for s in stops])
    rgb = np.array([[int(s[1][i:i + 2], 16) for i in (1, 3, 5)] for s in stops], float)
    tt = np.linspace(0, 1, n)
    return np.stack([np.interp(tt, fr, rgb[:, c]) for c in range(3)], 1)


# The shader, in numpy (QA only: what the globe will paint, minus relief).
# The speed view here is palette(t + DELTA); the Globe paints
# drape + palette(t + DELTA) - palette(t), which equals this up to the
# drape's own WebP coding and is the drape exactly at DELTA = 0.
def emulate(t_static: np.ndarray, frame: np.ndarray | None, view: str, lim: float,
            lut_s: np.ndarray, lut_a: np.ndarray) -> np.ndarray:
    vmin, vmax = 1.0, 3000.0
    dec = np.log10(vmax / vmin)
    if view == "speed":
        tt = t_static if frame is None else t_static + (frame[..., 0].astype(np.float32) - 128) / DELTA_SCALE / dec
        idx = np.clip(np.round(np.clip(tt, 0, 1) * (len(lut_s) - 1)), 0, len(lut_s) - 1).astype(int)
        return lut_s[idx].astype(np.float32)
    pct = (frame[..., 1].astype(np.float32) - 128) / 127 * lim
    valid = frame[..., 2].astype(np.float32) / 255
    vst = vmin * (vmax / vmin) ** t_static
    fade = log_ramp(vst, ANOM_FADE)
    idx = np.clip(np.round((pct / lim + 1) / 2 * (len(lut_a) - 1)), 0, len(lut_a) - 1).astype(int)
    w = (fade * valid)[..., None]
    return w * lut_a[idx] + (1 - w) * ANOM_GREY * 255


# --------------------------------------------------------------------------
def contact_sheet(tiles, labels, out, cols=12):
    from PIL import ImageDraw
    th, tw = tiles[0].shape[:2]
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + 16)), (30, 30, 30))
    d = ImageDraw.Draw(sheet)
    for i, (im, lab) in enumerate(zip(tiles, labels)):
        r, c = divmod(i, cols)
        sheet.paste(Image.fromarray(im), (c * tw, r * (th + 16) + 16))
        d.text((c * tw + 4, r * (th + 16) + 2), lab, fill=(230, 230, 230))
    sheet.save(out)


def ll_to_px(lon, lat, w, h):
    return int((lon - LON_W) / (LON_E - LON_W) * w), int((LAT_N - lat) / (LAT_N - LAT_S) * h)


def make_qa(manifest, t_hi, a_hi, t_lo, a_lo, lim, w, h) -> None:
    qa = OUT / "qa"
    qa.mkdir(exist_ok=True)
    lut_s = speed_lut()[0].astype(np.float32)
    lut_a = stops_lut(manifest["anomaly_colour"]["stops"])
    frames = manifest["frames"]

    def comp(rgb, alpha):
        a = alpha[..., None]
        return (rgb * a + 18 * (1 - a)).clip(0, 255).astype(np.uint8)

    # --- 1. difference image: the shipped drape vs the shader at DELTA = 0
    #        and at the month that matches best -----------------------------
    drape = np.asarray(Image.open(DRAPE_SHIPPED).convert("RGBA")).astype(np.float32)
    t8 = np.asarray(Image.open(OUT / "speed_t_v1.webp").convert("L")).astype(np.float32) / 255
    rec0 = emulate(t8, None, "speed", lim, lut_s, lut_a)
    ice = drape[..., 3] > 127
    d0 = np.abs(rec0 - drape[..., :3]).max(-1)
    stats = dict(delta0=dict(mean=float(d0[ice].mean()), p99=float(np.percentile(d0[ice], 99)),
                             max=float(d0[ice].max())))
    # best month: smallest mean |DELTA| over ice
    best, best_v = None, 1e9
    for f in frames:
        fr = np.asarray(Image.open(OUT / f["file"]))
        v = np.abs(fr[..., 0].astype(np.float32) - 128)[a_lo > 0.5].mean()
        if v < best_v:
            best, best_v = f, v
    jan = next(f for f in frames if f["ym"] == "2016-01")
    diffs = {}
    for f in (best, jan):
        fr = np.asarray(Image.open(OUT / f["file"]).resize(drape.shape[1::-1], Image.BILINEAR))
        rec = emulate(t8, fr, "speed", lim, lut_s, lut_a)
        dd = np.abs(rec - drape[..., :3]).max(-1)
        diffs[f["ym"]] = dd
        stats[f["ym"]] = dict(mean=float(dd[ice].mean()), p99=float(np.percentile(dd[ice], 99)),
                              max=float(dd[ice].max()))
    (qa / "drape_diff_stats.json").write_text(json.dumps(dict(best_month=best["ym"], **stats), indent=1))
    Wd, Hd = drape.shape[1], drape.shape[0]
    x0, y0 = ll_to_px(-52, 70.5, Wd, Hd)
    x1, y1 = ll_to_px(-46, 66.5, Wd, Hd)
    fig, axs = plt.subplots(2, 3, figsize=(24, 12), facecolor="k")
    crop = (slice(y0, y1), slice(x0, x1))
    panels = [
        (comp(drape[..., :3], drape[..., 3] / 255)[crop], "shipped drape greenland_speed_nasa_v1.webp (CW 66.5-70.5N)"),
        (comp(rec0, drape[..., 3] / 255)[crop], "shader at DELTA = 0 (speed_t_v1.webp + palette)"),
        (np.where(ice, d0, 0)[crop], f"|drape - shader(DELTA=0)| max over RGB, bytes (mean {stats['delta0']['mean']:.1f}, p99 {stats['delta0']['p99']:.0f})"),
    ]
    fr_best = np.asarray(Image.open(OUT / jan["file"]).resize((Wd, Hd), Image.BILINEAR))
    rec_j = emulate(t8, fr_best, "speed", lim, lut_s, lut_a)
    panels += [
        (comp(rec_j, drape[..., 3] / 255)[crop], "shader at 2016-01"),
        (np.where(ice, diffs["2016-01"], 0)[crop], f"|drape - shader(2016-01)| (mean {stats['2016-01']['mean']:.1f}, p99 {stats['2016-01']['p99']:.0f})"),
        (np.where(ice, diffs[best["ym"]], 0)[crop], f"|drape - shader({best['ym']}, best month)| (mean {stats[best['ym']]['mean']:.1f}, p99 {stats[best['ym']]['p99']:.0f})"),
    ]
    for ax, (im, title) in zip(axs.flat, panels):
        if im.ndim == 2:
            ax.imshow(im, cmap="magma", vmin=0, vmax=40, aspect="auto")
        else:
            ax.imshow(im, aspect="auto")
        ax.set_title(title, color="w", fontsize=10)
        ax.set_axis_off()
    plt.tight_layout()
    plt.savefig(qa / "drape_diff.png", dpi=60, facecolor="k")
    plt.close(fig)
    # whole-sheet difference at 1/4
    fig, axs = plt.subplots(1, 2, figsize=(22, 9), facecolor="k")
    axs[0].imshow(np.where(ice, d0, 0)[::4, ::4], cmap="magma", vmin=0, vmax=40, aspect="auto")
    axs[0].set_title("|drape - shader(DELTA=0)|, whole sheet (0..40 bytes)", color="w")
    axs[1].imshow(np.where(ice, diffs["2016-01"], 0)[::4, ::4], cmap="magma", vmin=0, vmax=40, aspect="auto")
    axs[1].set_title("|drape - shader(2016-01)|", color="w")
    for ax in axs:
        ax.set_axis_off()
    plt.tight_layout()
    plt.savefig(qa / "drape_diff_sheet.png", dpi=60, facecolor="k")
    plt.close(fig)
    del drape, rec0, d0, diffs, rec_j, fr_best, t8

    # --- 2. emulated contact sheets (1/10 scale) ---------------------------
    s = 10
    tl = t_lo[::s, ::s]
    al = a_lo[::s, ::s]
    for view in ("speed", "anom"):
        tiles = []
        for f in frames:
            fr = np.asarray(Image.open(OUT / f["file"]))[::s, ::s]
            tiles.append(comp(emulate(tl, fr, view, lim, lut_s, lut_a), al))
        contact_sheet(tiles, [f"{f['ym']} obs {f['observed']:.2f}" for f in frames],
                      qa / f"contact_{view}.png")

    # --- 3. central-west strip, 2019 --------------------------------------
    x0, y0 = ll_to_px(-56, 72.5, w, h)
    x1, y1 = ll_to_px(-44, 65.5, w, h)
    fig, axs = plt.subplots(2, 12, figsize=(30, 8.5), facecolor="k")
    for j in range(12):
        f = next(ff for ff in frames if ff["ym"] == f"2019-{j + 1:02d}")
        fr = np.asarray(Image.open(OUT / f["file"]))[y0:y1, x0:x1]
        for r, view in enumerate(("speed", "anom")):
            im = comp(emulate(t_lo[y0:y1, x0:x1], fr, view, lim, lut_s, lut_a), a_lo[y0:y1, x0:x1])
            axs[r, j].imshow(im, aspect="auto")
            axs[r, j].set_axis_off()
            axs[r, j].set_title(f"{view} {f['ym']}", color="w", fontsize=9)
    plt.suptitle("central-west 65.5-72.5N 56-44W, 2019, as the shader paints it (no relief)", color="w")
    plt.tight_layout()
    plt.savefig(qa / "cw_strip_2019.png", dpi=60, facecolor="k")
    plt.close(fig)

    # --- 4. region curves --------------------------------------------------
    R = manifest["regions"]
    mo = manifest["region_months"]
    tt = np.array([int(m[:4]) + (int(m[5:]) - 0.5) / 12 for m in mo])
    fig, axs = plt.subplots(len(R), 1, figsize=(14, 2.6 * len(R)), sharex=True)
    for ax, (k, r) in zip(axs, R.items()):
        y = np.array([np.nan if v is None else v for v in r["speed_obs"]], float)
        ax.plot(tt, r["speed"], "-", color="0.6", lw=1)
        ax.plot(tt, y, "o", ms=3, color="C0")
        for yr in range(2015, 2025):
            ax.axvspan(yr + 5 / 12, yr + 8 / 12, color="orange", alpha=0.18, lw=0)
        ax.set_title(r["name"], fontsize=10, loc="left")
        ax.set_ylabel("m/yr")
    plt.tight_layout()
    plt.savefig(qa / "region_curves.png", dpi=70)
    plt.close(fig)


# --------------------------------------------------------------------------
def box_latlon(box_km):
    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:3413", "EPSG:4326", always_xy=True)
    x0, x1, y0, y1 = box_km
    corners = [tr.transform(x * 1e3, y * 1e3) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    c = tr.transform((x0 + x1) / 2 * 1e3, (y0 + y1) / 2 * 1e3)
    return ([round(c[1], 4), round(c[0], 4)],
            [[round(la, 4), round(lo, 4)] for lo, la in corners])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--height", type=int, default=1400)
    ap.add_argument("--anom-lim", type=float, default=50.0)
    ap.add_argument("--first", default="2015-01", help="first month shipped as a frame")
    ap.add_argument("--start-at", default="2016-01", help="the month the page opens on")
    ap.add_argument("--keep-cache", action="store_true")
    ap.add_argument("--only", type=int, default=0, help="bake only N frames (size test)")
    ap.add_argument("--qa-only", action="store_true")
    args = ap.parse_args()
    w, h = args.width, args.height
    lim = args.anom_lim
    (OUT / "frames").mkdir(parents=True, exist_ok=True)

    months = month_list()                         # Dec 2014 .. Nov 2024 (fills + medians use all)
    first = args.first.replace("-", "")
    ship = [i for i, m in enumerate(months) if m >= first]
    print(f"{len(months)} months {months[0]}..{months[-1]}, shipping {len(ship)}, grid {w}x{h}")

    # --- the drape's own t_static (8192 x 3152) ---------------------------
    print("static t (drape geometry)...", flush=True)
    t_hi, a_hi, W, H = static_t_hi()
    Image.fromarray(np.round(t_hi * 255).astype(np.uint8), "L").save(
        OUT / "speed_t_v1.webp", "WEBP", lossless=True, quality=100, method=6)
    print(f"  speed_t_v1.webp {(OUT / 'speed_t_v1.webp').stat().st_size / 1e6:.2f} MB", flush=True)
    t_lo = np.asarray(Image.fromarray((t_hi * 255).astype(np.uint8), "L").resize((w, h), Image.BOX),
                      np.float32) / 255
    a_lo = np.asarray(Image.fromarray((a_hi * 255).astype(np.uint8), "L").resize((w, h), Image.BOX),
                      np.float32) / 255
    del t_hi

    manifest_path = OUT / "manifest.json"
    if args.qa_only:
        make_qa(json.loads(manifest_path.read_text()), None, a_hi, t_lo, a_lo, lim, w, h)
        return

    obs_full = load_stack(months, w, h)
    static = load_static(w, h)
    ice = ice_fraction(w, h) >= 0.5
    print(f"  ice pixels {ice.sum()}", flush=True)
    obs = np.asarray(obs_full[:, ice])            # (T, N)
    del obs_full
    st = static[ice]
    filled, code = fill_stack(obs, st, months)
    ref = running_median(filled, code)
    with np.errstate(all="ignore"):
        nobs = np.isfinite(obs).sum(0)
        vmed = np.nanmedian(obs, axis=0)
    vmed[nobs < MEDIAN_MIN_OBS] = np.nan
    del obs
    wv = log_ramp(st, SPEED_BLEND)
    wv[~np.isfinite(st)] = 1.0
    # Where the shader greys the anomaly out anyway (v_static below the fade,
    # measured on the drape's own t like the shader does, with a margin),
    # store the neutral value: the interior's monthly noise was 2/3 of the
    # bytes and is never shown.
    v_st_drape = 10 ** (t_lo[ice] * np.log10(3000.0))
    anom_shown = v_st_drape >= ANOM_FADE[0] * 0.85

    frames = []
    todo = ship[: args.only] if args.only else ship
    for i in todo:
        ym = months[i]
        c = code[i]
        with np.errstate(all="ignore"):
            delta = wv * (np.log10(filled[i]) - np.log10(vmed))
        delta[(c == 0) | (c == 4) | ~np.isfinite(delta)] = 0.0
        delta = np.clip(delta, -DELTA_MAX, DELTA_MAX)
        with np.errstate(all="ignore"):
            pct = 100.0 * (filled[i] / ref[i] - 1.0)
        valid = (c <= 2) & (c >= 1) & np.isfinite(pct) & anom_shown
        R = np.full((h, w), 128, np.uint8)
        G = np.full((h, w), 128, np.uint8)
        B = np.zeros((h, w), np.uint8)
        # R in steps of DELTA_STEP bytes (1.8 % of speed: < 1 palette step).
        R[ice] = np.clip(128 + DELTA_STEP * np.round(DELTA_SCALE * delta / DELTA_STEP), 1, 255).astype(np.uint8)
        # G in steps of ANOM_STEP bytes (1.6 %): finer than the eye reads on
        # a +/-50 % ramp, and the noise costs fewer bits.
        g = 128 + ANOM_STEP * np.round(np.clip(127 * np.nan_to_num(pct) / lim, -127, 127) / ANOM_STEP)
        g = np.where(valid, np.clip(g, 1, 255), 128)
        G[ice] = g.astype(np.uint8)
        B[ice] = np.where(valid, 255, 0).astype(np.uint8)
        fn = f"frames/m_{ym}.webp"
        Image.fromarray(np.dstack([R, G, B]), "RGB").save(OUT / fn, "WEBP", lossless=True,
                                                         quality=100, method=6)
        cov = {f"code{k}": round(float(np.mean(c == k)), 4) for k in range(5)}
        frames.append(dict(ym=f"{ym[:4]}-{ym[4:]}", file=fn,
                           observed=round(float(np.mean(c[wv > 0.5] == 1)), 3),
                           bytes=(OUT / fn).stat().st_size, coverage=cov))
        print(f"  {ym}  observed {frames[-1]['observed']:.2f}  {frames[-1]['bytes'] / 1e3:.0f} kB",
              flush=True)
    if args.only:
        return
    del filled, ref, code

    reg_all = region_series(months)
    regions = {}
    for k in SITE_REGIONS + tuple(kk for kk in REGIONS if kk not in SITE_REGIONS):
        r = reg_all[k]
        centre, corners = box_latlon(REGIONS[k]["box"])
        regions[k] = dict(
            name=r["name"], label=REGIONS[k]["label"], kind=r["kind"], site=k in SITE_REGIONS,
            box_epsg3413_km=REGIONS[k]["box"], centre_latlon=centre, corners_latlon=corners,
            speed=[r["speed"][i] for i in ship], speed_obs=[r["speed_obs"][i] for i in ship],
            interpolated=[r["interpolated"][i] for i in ship],
            anomaly_pct=[r["anomaly_pct"][i] for i in ship],
            summer_peak_vs_winter=r["summer_peak_vs_winter"])

    manifest = dict(
        product="NASA MEaSUREs Greenland Monthly Ice Sheet Velocity Mosaics from SAR and "
                "Landsat, NSIDC-0731 Version 5 (speed 'vv', 800 m overview of the 200 m COG)",
        citation=[
            "Joughin, I. (2023). MEaSUREs Greenland Monthly Ice Sheet Velocity Mosaics from SAR "
            "and Landsat. (NSIDC-0731, Version 5). NASA NSIDC DAAC. https://doi.org/10.5067/EGKZX6FXXM4P",
            "Joughin, I., Smith, B. E., & Howat, I. (2018). Greenland Ice Mapping Project: ice "
            "flow velocity variation at sub-monthly to decadal timescales. The Cryosphere, 12, "
            "2211-2227. https://doi.org/10.5194/tc-12-2211-2018",
        ],
        grid=dict(lon_w=LON_W, lon_e=LON_E, lat_s=LAT_S, lat_n=LAT_N, frame_width=w, frame_height=h,
                  static_width=W, static_height=H, north_up=True,
                  same_extent_as="shared/greenland_speed_nasa_v1.webp"),
        static=dict(file="speed_t_v1.webp",
                    encoding="byte = round(255 * t), t = clip(log10(v/vmin)/log10(vmax/vmin), 0, 1); "
                             "v = the ITS_LIVE 480 m field the drape was coloured from"),
        speed_colour=dict(palette="website/src/config/velocityPalette.json", vmin=1.0, vmax=3000.0,
                          function="t = t_static + DELTA/log10(vmax/vmin); rgb = palette(t)"),
        delta=dict(encoding=f"R = 128 + {DELTA_SCALE:g} * DELTA in steps of {DELTA_STEP}, DELTA in decades",
                   scale=DELTA_SCALE, blend_mps=list(SPEED_BLEND), definition="w * (log10 v_month - log10 v_median); v_median = "
                   f"the pixel's median of observed months (>= {MEDIAN_MIN_OBS}); w = 0 at v_static <= "
                   f"{SPEED_BLEND[0]:g}, 1 at >= {SPEED_BLEND[1]:g} m/yr (log-linear); 0 off land ice "
                   "and on static-filled months"),
        anomaly_colour=dict(cmap=ANOM_CMAP, lim=lim, stops=anom_stops(),
                            encoding=f"G = 128 + 127 * pct / lim in steps of {ANOM_STEP}; B = 255 where valid",
                            definition="pct = 100 * (v / ref - 1); ref = the pixel's centred 12-month "
                                       "running median of observed + interpolated months",
                            neutral_grey=ANOM_GREY, fade_mps=list(ANOM_FADE),
                            fade="grey where invalid (month filled from climatology/static, or no "
                                 f"data); log-linear fade to grey as v_static goes {ANOM_FADE[1]:g} -> "
                                 f"{ANOM_FADE[0]:g} m/yr"),
        gap_policy={"1": "observed", "2": "mean of the observed month before and after",
                    "3": "median of this calendar month over all observed years (>= 2)",
                    "4": "static ITS_LIVE composite", "0": "no data"},
        coverage_note="observed = the fraction of the land-ice pixels whose blend weight w > 0.5 "
                      "(where the globe shows the month) that were observed that month; codeK = "
                      "fraction of all land-ice pixels with fill code K",
        start_at=args.start_at,
        frame_count=len(frames), date_range=[frames[0]["ym"], frames[-1]["ym"]],
        frames=frames,
        region_months=[f["ym"] for f in frames],
        region_note="native 800 m grid, box median over observed pixels; null when < 50 % of the "
                    "box observed; 'speed' fills nulls by linear interpolation in time",
        regions=regions,
    )
    manifest_path.write_text(json.dumps(manifest, indent=1))
    tot = sum(f["bytes"] for f in frames)
    print(f"wrote {manifest_path}; frames {tot / 1e6:.1f} MB", flush=True)
    make_qa(manifest, None, a_hi, t_lo, a_lo, lim, w, h)
    if not args.keep_cache:
        for p in CACHE.glob("stack_*.npy"):
            p.unlink()


if __name__ == "__main__":
    main()
