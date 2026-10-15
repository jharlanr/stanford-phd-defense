"""
The Introduction's "Greenland flows" step: the surface-
speed drape + the comet-trail streamlines, in the grammar of NASA SVS 3848
(Rignot et al., "Antarctic ice flow"): a log-scaled speed colour map on the
ice, thousands of thin dark streaks advected along the flow field.

Reads ONLY the ITS_LIVE 120 m Greenland mosaic copy in cinematic/source_data
(ITS_LIVE_velocity_120m_RGI05A_0000_V02.1.nc, EPSG:3413).

Outputs (cinematic/data/flow/, new names — never overwrite a shipped key):
  greenland_speed_nasa_v1.webp   the drape. PlateCarree lon −75..−10,
                                 lat 59..84 (the frame every Greenland patch
                                 in Globe.vue uses), RGBA, alpha = ITS_LIVE
                                 land/floating-ice mask (tundra and rock show
                                 the satellite basemap underneath).
  greenland_flow_trails_v1.bin   the streamlines, binary "FLW1" (below).
  flow_preview.png               QA: every streamline over the drape.

Colours come from website/src/config/velocityPalette.json — the SAME file
the colorbar component reads, so the bar and the map cannot drift apart.

Streamlines — evenly spaced (Jobard & Lefer 1997), integrated by arc length
in EPSG:3413 on a 480 m block-mean of the 120 m field (lightly smoothed so
the slow interior's direction is not noise):
  * seeds are visited FAST-FIRST, so each outlet's trunk is laid down first
    and runs as one long line from the divide to the calving front;
  * separation d_sep(v) shrinks with speed (7.5 km in the interior → 2 km
    on the outlets), so the interior is not empty and the outlets are
    several distinct lines, not a solid mass; a line stops when it comes
    within 0.55·d_sep of an accepted line (a 500 m distance raster);
  * lines stop off the ice, below 0.5 m/yr, on a direction reversal or a
    > 60° kink between steps (stagnation noise), or at 2,500 km.
Per vertex the file stores the ANIMATION TIME tau (s): the head of a comet
travels along the line at a display speed f(v) = F10 · (v / 10 m/yr)^EXP
km/s — a compressed power of the true speed, so the interior visibly creeps
while Jakobshavn-class outlets move briskly (the 1 → 10,000 m/yr range
becomes ~ 7.2 → 55 km/s, 7.6x instead of 10,000x). The shader draws comets at
t − tau (no per-frame geometry work, no loop seam).

FLW1 layout (little-endian):
  0   char[4]  'FLW1'
  4   uint32   nLines
  8   uint32   nPoints
  12  float32  lonW, lonE, latS, latN   (quantisation frame, degrees)
  28  float32  F10, EXP                 (display-speed law used for tau)
  36  uint32   reserved (0)
  40  uint32   lineStart[nLines + 1]    (point offsets)
  ..  float32  tau[nPoints]             (s from the line's upstream end)
  ..  uint16   lonQ[nPoints]            (lonW + q/65535 · (lonE − lonW))
  ..  uint16   latQ[nPoints]
  ..  uint8    speedQ[nPoints]          (log10 v · 64, v in m/yr, clamp 0..255)

Run (a Python env with xarray/pyproj/scipy/PIL):
  nice -n 15 python \
      cinematic/scene_01_intro/build_flow_trails.py [--rebuild-cache]
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from pathlib import Path

import numpy as np
import xarray as xr
from PIL import Image
from pyproj import Transformer
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared import CINEMATIC_DIR, SOURCE_DATA, require_source  # noqa: E402

SRC = SOURCE_DATA / "data" / "ITS_LIVE_velocity_120m_RGI05A_0000_V02.1.nc"
OUT_DIR = CINEMATIC_DIR / "data" / "flow"
CACHE = OUT_DIR / "its_live_480m.npz"
PALETTE_JSON = CINEMATIC_DIR.parent / "website" / "src" / "config" / "velocityPalette.json"

DRAPE_OUT = OUT_DIR / "greenland_speed_nasa_v1.webp"
TRAILS_OUT = OUT_DIR / "greenland_flow_trails_v1.bin"
PREVIEW_OUT = OUT_DIR / "flow_preview.png"

# The Greenland patch frame (must match Globe.vue BASEMAP_* / makeGreenlandPatch).
LON_W, LON_E = -75.0, -10.0
LAT_S, LAT_N = 59.0, 84.0
DRAPE_W, DRAPE_H = 8192, 3152

COARSEN = 4                 # 120 m → 480 m
SMOOTH_SIGMA_CELLS = 1.2    # direction-field smoothing (cells of 480 m)

# Streamline knobs.
STEP_M = 1000.0             # integration step (arc length)
KEEP_EVERY = 3              # store every 3rd step → 3 km vertices (~1.5 device px at the full view)
V_STOP = 0.5                # m/yr
MAX_LEN_M = 2_500_000.0
MIN_LEN_M = 20_000.0
DSEP_SLOW_M, DSEP_FAST_M = 7_500.0, 2_000.0
DSEP_V0, DSEP_V1 = 10.0, 1500.0   # d_sep ramps (in log v) between these
D_TEST_FRAC = 0.55
SEED_SPACING_M = 2_000.0
DIST_RES_M = 500.0

# Display-speed law (km/s of ground at 1x animation rate).
F10 = 12.0
EXP = 0.22


# ───────────────────────── data ─────────────────────────

def block_nanmean(a: np.ndarray, k: int) -> np.ndarray:
    h, w = a.shape
    a = a[: h - h % k, : w - w % k].reshape(h // k, k, w // k, k)
    with np.errstate(invalid="ignore"):
        return np.nanmean(a, axis=(1, 3))


def load_coarse(rebuild: bool):
    if CACHE.exists() and not rebuild:
        z = np.load(CACHE)
        return {k: z[k] for k in z.files}
    require_source(SRC)
    t0 = time.time()
    ds = xr.open_dataset(SRC, decode_timedelta=False)
    ny, nx = ds.sizes["y"], ds.sizes["x"]
    ny4, nx4 = ny - ny % COARSEN, nx - nx % COARSEN
    out = {k: np.empty((ny4 // COARSEN, nx4 // COARSEN), np.float32)
           for k in ("vx", "vy", "v", "ice")}
    STRIP = 1500 - 1500 % COARSEN
    for r0 in range(0, ny4, STRIP):
        r1 = min(ny4, r0 + STRIP)
        sl = dict(y=slice(r0, r1), x=slice(0, nx4))
        for k in ("vx", "vy", "v"):
            a = ds[k].isel(**sl).values.astype(np.float32)
            out[k][r0 // COARSEN: r1 // COARSEN] = block_nanmean(a, COARSEN)
        li = ds["landice"].isel(**sl).values.astype(np.float32)
        fl = ds["floatingice"].isel(**sl).values.astype(np.float32)
        ice = np.clip(np.nan_to_num(li) + np.nan_to_num(fl), 0, 1)
        out["ice"][r0 // COARSEN: r1 // COARSEN] = block_nanmean(ice, COARSEN)
        print(f"  rows {r0}-{r1} / {ny4}  ({time.time() - t0:.0f} s)", flush=True)
    x = ds["x"].values[:nx4].reshape(-1, COARSEN).mean(1)
    y = ds["y"].values[:ny4].reshape(-1, COARSEN).mean(1)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    np.savez(CACHE, x=x, y=y, **{k: v.astype(np.float16) for k, v in out.items()})
    out.update(x=x, y=y)
    return out


def palette_lut(n: int = 1024) -> tuple[np.ndarray, float, float]:
    p = json.loads(PALETTE_JSON.read_text())
    stops = p["stops"]
    fr = np.array([s[0] for s in stops])
    rgb = np.array([[int(s[1][i: i + 2], 16) for i in (1, 3, 5)] for s in stops], float)
    t = np.linspace(0, 1, n)
    lut = np.stack([np.interp(t, fr, rgb[:, c]) for c in range(3)], 1)
    return lut.round().astype(np.uint8), float(p["vmin"]), float(p["vmax"])


# ───────────────────────── drape ─────────────────────────

def fill_nearest(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    idx = ndimage.distance_transform_edt(~valid, return_distances=False, return_indices=True)
    return a[tuple(idx)]


def build_drape(d) -> np.ndarray:
    lut, vmin, vmax = palette_lut()
    v = d["v"].astype(np.float32)
    ice = d["ice"].astype(np.float32)
    ice = np.nan_to_num(ice)
    valid = np.isfinite(v) & (v > 0)
    logv = np.log10(np.clip(np.where(valid, v, 1.0), 1e-3, None))
    logv = fill_nearest(logv, valid)
    x, y = d["x"], d["y"]
    dx, dy = x[1] - x[0], y[1] - y[0]

    lon = LON_W + (np.arange(DRAPE_W) + 0.5) / DRAPE_W * (LON_E - LON_W)
    lat = LAT_N - (np.arange(DRAPE_H) + 0.5) / DRAPE_H * (LAT_N - LAT_S)
    tr = Transformer.from_crs("EPSG:4326", "EPSG:3413", always_xy=True)
    rgba = np.zeros((DRAPE_H, DRAPE_W, 4), np.uint8)
    ROWS = 394
    for r0 in range(0, DRAPE_H, ROWS):
        r1 = min(DRAPE_H, r0 + ROWS)
        LON, LAT = np.meshgrid(lon, lat[r0:r1])
        X, Y = tr.transform(LON, LAT)
        fi = (Y - y[0]) / dy
        fj = (X - x[0]) / dx
        coords = np.stack([fi.ravel(), fj.ravel()])
        lv = ndimage.map_coordinates(logv, coords, order=1, mode="nearest").reshape(fi.shape)
        m = ndimage.map_coordinates(ice, coords, order=1, mode="constant", cval=0).reshape(fi.shape)
        f = np.clip((lv - np.log10(vmin)) / (np.log10(vmax) - np.log10(vmin)), 0, 1)
        col = lut[(f * (len(lut) - 1)).round().astype(int)]
        a = np.clip((m - 0.35) / 0.3, 0, 1)
        rgba[r0:r1, :, :3] = col
        rgba[r0:r1, :, 3] = (a * 255).round().astype(np.uint8)
    return rgba


# ─────────────────────── streamlines ───────────────────────

class Field:
    def __init__(self, d):
        self.x0, self.y0 = float(d["x"][0]), float(d["y"][0])
        self.dx, self.dy = float(d["x"][1] - d["x"][0]), float(d["y"][1] - d["y"][0])
        vx = d["vx"].astype(np.float32)
        vy = d["vy"].astype(np.float32)
        v = d["v"].astype(np.float32)
        ok = np.isfinite(vx) & np.isfinite(vy) & np.isfinite(v)
        w = ndimage.gaussian_filter(ok.astype(np.float32), SMOOTH_SIGMA_CELLS)
        with np.errstate(invalid="ignore", divide="ignore"):
            self.vx = ndimage.gaussian_filter(np.where(ok, vx, 0), SMOOTH_SIGMA_CELLS) / w
            self.vy = ndimage.gaussian_filter(np.where(ok, vy, 0), SMOOTH_SIGMA_CELLS) / w
            self.v = ndimage.gaussian_filter(np.where(ok, v, 0), SMOOTH_SIGMA_CELLS) / w
        bad = (w < 0.5) | (np.nan_to_num(d["ice"].astype(np.float32)) < 0.5)
        self.vx[bad] = np.nan
        self.vy[bad] = np.nan
        self.v[bad] = np.nan
        self.ny, self.nx = self.v.shape

    def sample(self, px: float, py: float):
        fj = (px - self.x0) / self.dx
        fi = (py - self.y0) / self.dy
        j0, i0 = int(np.floor(fj)), int(np.floor(fi))
        if j0 < 0 or i0 < 0 or j0 >= self.nx - 1 or i0 >= self.ny - 1:
            return None
        tj, ti = fj - j0, fi - i0
        w00, w01 = (1 - ti) * (1 - tj), (1 - ti) * tj
        w10, w11 = ti * (1 - tj), ti * tj
        vx, vy, v = self.vx, self.vy, self.v
        ax = vx[i0, j0] * w00 + vx[i0, j0 + 1] * w01 + vx[i0 + 1, j0] * w10 + vx[i0 + 1, j0 + 1] * w11
        ay = vy[i0, j0] * w00 + vy[i0, j0 + 1] * w01 + vy[i0 + 1, j0] * w10 + vy[i0 + 1, j0 + 1] * w11
        sp = v[i0, j0] * w00 + v[i0, j0 + 1] * w01 + v[i0 + 1, j0] * w10 + v[i0 + 1, j0 + 1] * w11
        if not (np.isfinite(ax) and np.isfinite(ay) and np.isfinite(sp)):
            return None
        n = np.hypot(ax, ay)
        if n < 1e-6:
            return None
        return ax / n, ay / n, sp


def dsep(v: float) -> float:
    t = (np.log10(max(v, 1e-3)) - np.log10(DSEP_V0)) / (np.log10(DSEP_V1) - np.log10(DSEP_V0))
    t = min(1.0, max(0.0, t))
    return DSEP_SLOW_M + (DSEP_FAST_M - DSEP_SLOW_M) * t


class DistRaster:
    """Distance (m) to the nearest accepted streamline point, on a 500 m grid,
    stamped out to R_MAX around each point."""

    R_MAX = DSEP_SLOW_M * 1.05

    def __init__(self, f: Field):
        self.x0 = f.x0
        self.y1 = f.y0 + f.dy * (f.ny - 1)  # southernmost y (dy < 0)
        self.w = int((f.dx * (f.nx - 1)) / DIST_RES_M) + 2
        self.h = int((-f.dy * (f.ny - 1)) / DIST_RES_M) + 2
        self.d = np.full((self.h, self.w), np.inf, np.float32)
        r = int(np.ceil(self.R_MAX / DIST_RES_M))
        oy, ox = np.mgrid[-r: r + 1, -r: r + 1]
        self.off = (oy.ravel(), ox.ravel(), (np.hypot(oy, ox).ravel() * DIST_RES_M).astype(np.float32))
        self.r = r

    def idx(self, px, py):
        return int((py - self.y1) / DIST_RES_M), int((px - self.x0) / DIST_RES_M)

    def query(self, px, py) -> float:
        i, j = self.idx(px, py)
        if 0 <= i < self.h and 0 <= j < self.w:
            return float(self.d[i, j])
        return 0.0

    def stamp(self, pts: np.ndarray) -> None:
        oy, ox, od = self.off
        ii = ((pts[:, 1] - self.y1) / DIST_RES_M).astype(int)
        jj = ((pts[:, 0] - self.x0) / DIST_RES_M).astype(int)
        I = (ii[:, None] + oy[None]).ravel()
        J = (jj[:, None] + ox[None]).ravel()
        D = np.broadcast_to(od[None], (len(pts), len(od))).ravel()
        k = (I >= 0) & (I < self.h) & (J >= 0) & (J < self.w)
        np.minimum.at(self.d, (I[k], J[k]), D[k])


def integrate(f: Field, dr: DistRaster, sx: float, sy: float, sign: float):
    pts, spd = [], []
    px, py = sx, sy
    prev = None
    length = 0.0
    while length < MAX_LEN_M:
        s = f.sample(px, py)
        if s is None:
            break
        ux, uy, v = s
        if v < V_STOP:
            break
        if prev is not None and ux * prev[0] + uy * prev[1] < 0.2:
            break  # direction reversal
        if length > 2 * STEP_M and dr.query(px, py) < D_TEST_FRAC * dsep(v):
            break
        pts.append((px, py))
        spd.append(v)
        # midpoint (RK2) step along the unit direction
        mx, my = px + sign * ux * STEP_M * 0.5, py + sign * uy * STEP_M * 0.5
        s2 = f.sample(mx, my)
        # A midpoint that points back (a saddle / noisy stagnation) makes
        # the path ping-pong 1 km back and forth in place — stop there.
        if s2 is None or s2[0] * ux + s2[1] * uy < 0.2:
            break
        # A step that turns > 60° from the last one is noise (zig-zag
        # lines in near-stagnant ice), not flow.
        if prev is not None and s2[0] * prev[0] + s2[1] * prev[1] < 0.5:
            break
        prev = (s2[0], s2[1])
        px += sign * s2[0] * STEP_M
        py += sign * s2[1] * STEP_M
        length += STEP_M
    return pts, spd


def build_streamlines(d):
    f = Field(d)
    dr = DistRaster(f)
    # Seed lattice, fast-first with a random tiebreak.
    rng = np.random.default_rng(3848)
    xs = np.arange(f.x0, f.x0 + f.dx * (f.nx - 1), SEED_SPACING_M)
    ys = np.arange(f.y0 + f.dy * (f.ny - 1), f.y0, SEED_SPACING_M)
    X, Y = np.meshgrid(xs, ys)
    X = X.ravel() + rng.uniform(-0.4, 0.4, X.size) * SEED_SPACING_M
    Y = Y.ravel() + rng.uniform(-0.4, 0.4, Y.size) * SEED_SPACING_M
    fj = ((X - f.x0) / f.dx).round().astype(int).clip(0, f.nx - 1)
    fi = ((Y - f.y0) / f.dy).round().astype(int).clip(0, f.ny - 1)
    V = f.v[fi, fj]
    keep = np.isfinite(V) & (V > V_STOP * 2)
    X, Y, V = X[keep], Y[keep], V[keep]
    order = np.argsort(-(np.log10(V) + rng.uniform(0, 0.15, V.size)))
    print(f"  {len(order)} candidate seeds", flush=True)
    lines = []
    t0 = time.time()
    for n, k in enumerate(order):
        sx, sy, sv = X[k], Y[k], V[k]
        if dr.query(sx, sy) < dsep(sv):
            continue
        back, bsp = integrate(f, dr, sx, sy, -1.0)
        fwd, fsp = integrate(f, dr, sx, sy, +1.0)
        pts = back[::-1] + fwd[1:]
        sp = bsp[::-1] + fsp[1:]
        if len(pts) * STEP_M < MIN_LEN_M:
            continue
        P = np.array(pts)
        dr.stamp(P)
        lines.append((P, np.array(sp)))
        if len(lines) % 500 == 0:
            print(f"  {len(lines)} lines, seed {n}/{len(order)} ({time.time() - t0:.0f} s)", flush=True)
    return lines


def display_speed_kms(v: np.ndarray) -> np.ndarray:
    return F10 * (np.clip(v, 1.0, 10_000.0) / 10.0) ** EXP


def write_trails(lines, path: Path):
    tr = Transformer.from_crs("EPSG:3413", "EPSG:4326", always_xy=True)
    starts = [0]
    taus, lons, lats, spq = [], [], [], []
    for P, sp in lines:
        P = P[::KEEP_EVERY] if len(P) > 2 else P
        sp = sp[::KEEP_EVERY] if len(sp) > 2 else sp
        seg = np.hypot(*np.diff(P, axis=0).T) / 1000.0  # km
        fmid = display_speed_kms(0.5 * (sp[1:] + sp[:-1]))
        tau = np.concatenate([[0.0], np.cumsum(seg / fmid)])
        lon, lat = tr.transform(P[:, 0], P[:, 1])
        taus.append(tau.astype(np.float32))
        lons.append(lon)
        lats.append(lat)
        spq.append(np.clip(np.log10(np.clip(sp, 1, None)) * 64, 0, 255).round().astype(np.uint8))
        starts.append(starts[-1] + len(P))
    tau = np.concatenate(taus)
    lon = np.concatenate(lons)
    lat = np.concatenate(lats)
    q = lambda a, lo, hi: np.clip((a - lo) / (hi - lo) * 65535, 0, 65535).round().astype("<u2")  # noqa: E731
    with open(path, "wb") as fh:
        fh.write(b"FLW1")
        fh.write(struct.pack("<II", len(lines), len(tau)))
        fh.write(struct.pack("<4f", LON_W, LON_E, LAT_S, LAT_N))
        fh.write(struct.pack("<2fI", F10, EXP, 0))
        fh.write(np.array(starts, "<u4").tobytes())
        fh.write(tau.astype("<f4").tobytes())
        fh.write(q(lon, LON_W, LON_E).tobytes())
        fh.write(q(lat, LAT_S, LAT_N).tobytes())
        fh.write(np.concatenate(spq).tobytes())
    return lon, lat, starts, tau


def preview(rgba: np.ndarray, lon, lat, starts, path: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    # crop to Greenland-ish window in the PlateCarree frame, stretch lon by
    # cos(72°) so the preview is not a squashed PlateCarree strip.
    fig = plt.figure(figsize=(10, 14), facecolor="black")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("black")
    ax.imshow(rgba[::4, ::4], extent=[LON_W, LON_E, LAT_S, LAT_N], origin="upper")
    segs = [np.column_stack([lon[a:b], lat[a:b]]) for a, b in zip(starts[:-1], starts[1:])]
    ax.add_collection(LineCollection(segs, colors=(0.05, 0.08, 0.2, 0.7), linewidths=0.25))
    ax.set_xlim(-74, -11)
    ax.set_ylim(59.5, 83.8)
    ax.set_aspect(1 / np.cos(np.radians(72)))
    ax.set_axis_off()
    fig.savefig(path, dpi=150, facecolor="black")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild-cache", action="store_true")
    ap.add_argument("--skip-drape", action="store_true")
    ap.add_argument("--reuse-lines", action="store_true",
                    help="re-bake tau/format from the last traced lines (speed-law changes)")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("loading ITS_LIVE (480 m block means)...", flush=True)
    d = load_coarse(args.rebuild_cache)
    print(f"  grid {d['v'].shape}", flush=True)

    drape_png = OUT_DIR / "_drape_cache.png"
    if args.skip_drape and drape_png.exists():
        rgba = np.array(Image.open(drape_png))
    else:
        print("drape...", flush=True)
        rgba = build_drape(d)
        Image.fromarray(rgba).save(drape_png)
        Image.fromarray(rgba).save(DRAPE_OUT, "WEBP", quality=90, alpha_quality=90, method=6)
        print(f"wrote {DRAPE_OUT} ({DRAPE_OUT.stat().st_size / 1e6:.2f} MB)", flush=True)

    lines_cache = OUT_DIR / "_lines_cache.npz"
    if args.reuse_lines and lines_cache.exists():
        z = np.load(lines_cache)
        st = z["starts"]
        lines = [(z["P"][a:b], z["S"][a:b]) for a, b in zip(st[:-1], st[1:])]
        print(f"reused {len(lines)} traced lines", flush=True)
    else:
        print("streamlines...", flush=True)
        lines = build_streamlines(d)
        st = np.cumsum([0] + [len(P) for P, _ in lines])
        np.savez(lines_cache, starts=st, P=np.concatenate([P for P, _ in lines]),
                 S=np.concatenate([S for _, S in lines]))
    lon, lat, starts, tau = write_trails(lines, TRAILS_OUT)
    L = sum(len(P) for P, _ in lines) * STEP_M / 1000
    print(f"wrote {TRAILS_OUT} ({TRAILS_OUT.stat().st_size / 1e6:.2f} MB): "
          f"{len(lines)} lines, {len(tau)} vertices, {L:.0f} km of line, "
          f"max tau {tau.max():.0f} s", flush=True)
    preview(rgba, lon, lat, starts, PREVIEW_OUT)
    print(f"wrote {PREVIEW_OUT}")


if __name__ == "__main__":
    main()
