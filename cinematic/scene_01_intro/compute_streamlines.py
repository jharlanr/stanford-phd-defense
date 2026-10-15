"""
Compute Greenland surface velocity streamlines from the ITS_LIVE subset.

Pipeline:
  1. Load data/its_live_greenland_subset.nc (vx, vy in m/yr, EPSG:3413).
  2. Fill NaN with 0 so streamplot doesn't choke; mask low-flow regions.
  3. matplotlib streamplot → list of polylines in EPSG:3413 (x, y).
  4. Reproject each polyline to lat/lon (EPSG:4326) via pyproj.
  5. Save JSON: list of {lonlat: [[lon, lat], ...], speeds: [...]} for
     each streamline. Three.js renderer picks this up next.
  6. Render a static preview PNG (streamlines over greenland_basemap.png)
     so we can verify visually before integrating with the live globe.

Run:
    cd cinematic
    source .venv/bin/activate
    python scene_01_intro/compute_streamlines.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import xarray as xr  # noqa: E402
from PIL import Image  # noqa: E402
from pyproj import Transformer  # noqa: E402

from shared import CINEMATIC_DIR  # noqa: E402

DATA_DIR = CINEMATIC_DIR / "data"
SUBSET_NC = DATA_DIR / "its_live_greenland_subset.nc"
OUT_JSON = DATA_DIR / "greenland_streamlines.json"
OUT_PNG = DATA_DIR / "greenland_streamlines_preview.png"
BASEMAP_PNG = DATA_DIR / "greenland_basemap.png"

# Vite publishes anything in website/public/ as a static asset. The
# Three.js Globe component fetches the JSON via import.meta.env.BASE_URL.
PUBLIC_JSON = (
    CINEMATIC_DIR.parent / "website" / "public" / "greenland_streamlines.json"
)

# Drop every Nth polyline vertex to halve the JSON file size with no
# visible loss at viewing scale (streamplot output is over-sampled).
VERTEX_STRIDE = 2

# Basemap extent (must match build_greenland_basemap.py).
LON_W, LON_E = -75.0, -10.0
LAT_S, LAT_N = 59.0, 84.0

# Skip streamlines with peak speed below this (m/yr) — keeps the visual
# focused on the dynamic outlet glaciers and major flow tongues.
SPEED_FLOOR_MYR = 25.0

# matplotlib streamplot density. Higher = more lines, slower. 4–6 looks
# right for full-Greenland coverage at this grid resolution.
STREAM_DENSITY = 5.0


def load_velocity():
    ds = xr.open_dataset(SUBSET_NC)
    vx = ds["vx"].values
    vy = ds["vy"].values
    x = ds["x"].values
    y = ds["y"].values

    # streamplot wants strictly increasing y. Our y is descending
    # (north-to-south); flip both axis and arrays.
    if y[0] > y[-1]:
        y = y[::-1]
        vx = vx[::-1, :]
        vy = vy[::-1, :]

    # NaN → 0 so streamplot integrator doesn't blow up.
    vx = np.nan_to_num(vx, nan=0.0)
    vy = np.nan_to_num(vy, nan=0.0)
    return x, y, vx, vy


def streamline_polylines(x, y, vx, vy):
    """Run streamplot, harvest each integrated trajectory as an (N, 2) array."""
    fig = plt.figure()
    ax = fig.add_subplot(111)
    speed = np.hypot(vx, vy)
    sp = ax.streamplot(
        x,
        y,
        vx,
        vy,
        density=STREAM_DENSITY,
        linewidth=0.5,
        arrowsize=0,
        color=speed,
    )
    # streamplot returns a LineCollection where each segment is a 2-point
    # subline. To recover full polylines we group consecutive segments
    # whose endpoints match.
    segments = sp.lines.get_segments()
    plt.close(fig)

    polylines = []
    if not segments:
        return polylines

    current = [segments[0][0], segments[0][1]]
    EPS = 1e-6
    for seg in segments[1:]:
        a, b = seg
        if np.allclose(a, current[-1], atol=EPS):
            current.append(b)
        else:
            polylines.append(np.asarray(current))
            current = [a, b]
    polylines.append(np.asarray(current))
    return polylines


def filter_polylines(polylines, vx_grid, vy_grid, x_axis, y_axis):
    """Drop short or stagnant polylines; return list of (xy, speed) pairs."""
    kept = []
    speed_grid = np.hypot(vx_grid, vy_grid)
    dx = x_axis[1] - x_axis[0]
    dy = y_axis[1] - y_axis[0]
    for poly in polylines:
        if len(poly) < 6:
            continue
        # Sample speed at each polyline vertex via nearest-grid lookup.
        ix = np.clip(((poly[:, 0] - x_axis[0]) / dx).astype(int), 0, len(x_axis) - 1)
        iy = np.clip(((poly[:, 1] - y_axis[0]) / dy).astype(int), 0, len(y_axis) - 1)
        sp = speed_grid[iy, ix]
        if sp.max() < SPEED_FLOOR_MYR:
            continue
        kept.append((poly, sp))
    return kept


def reproject_polylines(polylines_with_speed):
    """EPSG:3413 (x, y in meters) → EPSG:4326 (lon, lat in degrees).

    Also computes per-line mean speed (drives shader scroll rate) and
    vertex-decimates each polyline by VERTEX_STRIDE (always keeping the
    final vertex so the line still terminates correctly).
    """
    transformer = Transformer.from_crs("EPSG:3413", "EPSG:4326", always_xy=True)
    out = []
    for xy, sp in polylines_with_speed:
        # Mean speed BEFORE decimation — uses every vertex so it's a
        # faithful average over the streamline integration.
        mean_speed = float(sp.mean())

        if VERTEX_STRIDE > 1:
            keep = np.arange(0, len(xy), VERTEX_STRIDE)
            if keep[-1] != len(xy) - 1:
                keep = np.append(keep, len(xy) - 1)
            xy = xy[keep]
            sp = sp[keep]
        lon, lat = transformer.transform(xy[:, 0], xy[:, 1])
        out.append(
            {
                "lonlat": np.column_stack([lon, lat]).round(4).tolist(),
                "speeds": sp.round(2).tolist(),
                "meanSpeed": round(mean_speed, 2),
            }
        )
    return out


VELOCITY_PNG = DATA_DIR / "greenland_velocity.png"


def render_preview(json_records, out_path):
    """Overlay dark streamlines on the velocity-colored basemap.

    Uses the same colormap (turbo) as build_velocity_colormap.py so the
    QA preview reads identically to the live Three.js render.
    """
    bg_path = VELOCITY_PNG if VELOCITY_PNG.exists() else BASEMAP_PNG
    if not bg_path.exists():
        print(f"  (no basemap — skipping preview)")
        return
    basemap = Image.open(bg_path).convert("RGBA")
    aspect = basemap.width / basemap.height

    fig = plt.figure(figsize=(13, 13 / aspect), facecolor="black")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(LON_W, LON_E)
    ax.set_ylim(LAT_S, LAT_N)
    ax.set_facecolor("black")
    ax.set_axis_off()
    ax.imshow(
        basemap,
        extent=[LON_W, LON_E, LAT_S, LAT_N],
        origin="upper",
        aspect="auto",
        zorder=1,
    )

    # Dark streamlines drape on top of the velocity colormap — NASA-SVS
    # aesthetic. Linewidth tapers slightly with speed so outlet glaciers
    # read as denser flow lines, but the dominant signal is the basemap.
    from matplotlib.collections import LineCollection  # noqa: PLC0415

    LOG_MIN, LOG_MAX = np.log10(10.0), np.log10(3000.0)
    all_segs = []
    all_widths = []
    for rec in json_records:
        ll = np.asarray(rec["lonlat"])
        sp = np.asarray(rec["speeds"])
        if len(ll) < 2:
            continue
        seg_speed = 0.5 * (sp[:-1] + sp[1:])
        log_sp = np.log10(np.clip(seg_speed, 1.0, 1e5))
        norm = np.clip((log_sp - LOG_MIN) / (LOG_MAX - LOG_MIN), 0, 1)
        for i in range(len(ll) - 1):
            all_segs.append([ll[i], ll[i + 1]])
            all_widths.append(0.25 + 0.6 * norm[i])
    lc = LineCollection(
        all_segs,
        colors=(0.0, 0.0, 0.0, 0.55),
        linewidths=all_widths,
        zorder=2,
    )
    ax.add_collection(lc)

    fig.savefig(out_path, dpi=200, facecolor="black")
    plt.close(fig)
    print(f"wrote {out_path}")


def main() -> None:
    print(f"loading {SUBSET_NC}")
    x, y, vx, vy = load_velocity()
    print(f"  grid: y={len(y)} x={len(x)}")
    print(f"  speed max: {np.hypot(vx, vy).max():.0f} m/yr")

    print("computing streamlines...")
    polylines = streamline_polylines(x, y, vx, vy)
    print(f"  raw polylines: {len(polylines)}")

    kept = filter_polylines(polylines, vx, vy, x, y)
    print(f"  kept (speed >= {SPEED_FLOOR_MYR} m/yr, len >= 6): {len(kept)}")

    print("reprojecting EPSG:3413 → EPSG:4326...")
    records = reproject_polylines(kept)

    payload = json.dumps(records)
    OUT_JSON.write_text(payload)
    size_kb = OUT_JSON.stat().st_size / 1024
    n_pts = sum(len(r["lonlat"]) for r in records)
    print(f"wrote {OUT_JSON} ({size_kb:.0f} KB, {n_pts} total vertices)")

    PUBLIC_JSON.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_JSON.write_text(payload)
    print(f"wrote {PUBLIC_JSON}")

    print("rendering static preview...")
    render_preview(records, OUT_PNG)


if __name__ == "__main__":
    main()
