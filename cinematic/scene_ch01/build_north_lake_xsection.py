"""
Build a flow-aligned cross-section profile through North Lake from BedMachine
+ ITS_LIVE.

Used by the Ch.1 (JOG) website beat: "knife-slide to a cross-section along
flow at North Lake" — that real-world cross-section is what motivates the
2D simulation, which in turn motivates the 1D analytical work.

Inputs (on the lab drive, $LAB_DRIVE; ~6.8 GB combined):
  - BedMachine v6 (.nc): bed, surface, ice thickness, ice mask
  - ITS_LIVE 120 m velocity (.nc): vx, vy on the same polar-stereo grid

Method:
  1. Read both NetCDFs (lazy via xarray).
  2. Convert North Lake (lon, lat) → EPSG:3413 polar-stereo (x, y).
  3. Sample velocity at the lake centre → unit flow direction.
  4. Build a straight along-flow profile through the lake centre, ±L_HALF
     metres, sampled every PROFILE_DX_M metres.
  5. Bilinearly sample bed and surface along the profile.
  6. Write a small JSON the website can render directly.

Output:
  cinematic/scene_ch01/data/north_lake_xsection.json
    {
      "lake": {"lon", "lat", "x_m", "y_m", "elev_m"},
      "flow":  {"vx", "vy", "speed_m_yr", "heading_deg"},
      "profile": {
        "x_m":        [along-profile distance, lake at 0],
        "surface_m":  [...],
        "bed_m":      [...],
        "thickness_m":[...],
        "lon":        [...],   # geographic, for downstream context maps
        "lat":        [...],
      },
      "meta": {"l_half_m", "dx_m", "n_points", ...}
    }

Run:
    cd cinematic
    source .venv/bin/activate
    python scene_ch01/build_north_lake_xsection.py

Optional CLI overrides (kwargs by name):
    python scene_ch01/build_north_lake_xsection.py --lake_lon=-49.5 \
        --lake_lat=68.7 --l_half_km=15 --dx_m=50
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import xarray as xr
from pyproj import Transformer

# --- Defaults ---------------------------------------------------------------

# North Lake (CW2019_1889 in 2d/data/labels_2019_volumes.csv; same physical
# lake as CW2018_1366 in the ESSD catalog)
NL_LON = -49.49574
NL_LAT = 68.72493

# Profile geometry
L_HALF_M = 20_000.0   # half-length of the cross-section, metres along flow
DX_M     = 100.0      # sample spacing along profile

# Data paths (the lab drive; set LAB_DRIVE to your own copy)
LAB = os.environ.get(
    "LAB_DRIVE", "/path/to/your/lab/drive"
)
BEDMACHINE = f"{LAB}/pnas2025/repos/sgl-stress/2d/data/BedMachineGreenland-v6.nc"
ITSLIVE    = f"{LAB}/pnas2025/repos/sgl-stress/2d/data/ITS_LIVE_velocity_120m_RGI05A_0000_V02.1.nc"

# Output
HERE   = Path(__file__).resolve().parent
OUTDIR = HERE / "data"
OUTPUT = OUTDIR / "north_lake_xsection.json"


# --- Helpers ---------------------------------------------------------------

def bilinear_sample(da: xr.DataArray, x_pts: np.ndarray, y_pts: np.ndarray) -> np.ndarray:
    """Bilinearly sample a 2D DataArray with 1D x/y coords at arbitrary
    (x_pts, y_pts) projected coordinates. Returns NaN where out of bounds."""
    return da.interp(x=("pt", x_pts), y=("pt", y_pts)).values


def ll_to_ps(lon, lat):
    """Lon/lat (deg) → EPSG:3413 polar-stereo (m)."""
    t = Transformer.from_crs(4326, 3413, always_xy=True)
    return t.transform(lon, lat)


def ps_to_ll(x, y):
    """EPSG:3413 (m) → lon/lat (deg)."""
    t = Transformer.from_crs(3413, 4326, always_xy=True)
    return t.transform(x, y)


# --- Main -------------------------------------------------------------------

def main(lake_lon, lake_lat, l_half_m, dx_m):
    OUTDIR.mkdir(parents=True, exist_ok=True)

    print(f"  North Lake at lon={lake_lon}, lat={lake_lat}")
    lake_x, lake_y = ll_to_ps(lake_lon, lake_lat)
    print(f"  → EPSG:3413 (x, y) = ({lake_x:.1f}, {lake_y:.1f}) m")

    print(f"  opening BedMachine ({BEDMACHINE})")
    bm = xr.open_dataset(BEDMACHINE)
    print(f"    vars: {list(bm.data_vars)}")
    print(f"    x range: {float(bm.x.min()):.0f} .. {float(bm.x.max()):.0f} m")
    print(f"    y range: {float(bm.y.min()):.0f} .. {float(bm.y.max()):.0f} m")

    print(f"  opening ITS_LIVE ({ITSLIVE})")
    vel = xr.open_dataset(ITSLIVE)
    print(f"    vars: {list(vel.data_vars)[:8]}")
    # ITS_LIVE typical layout: x, y in EPSG:3413; v, vx, vy m/yr
    print(f"    x range: {float(vel.x.min()):.0f} .. {float(vel.x.max()):.0f} m")
    print(f"    y range: {float(vel.y.min()):.0f} .. {float(vel.y.max()):.0f} m")

    # Sample velocity at the lake centre (one-point .interp)
    print("  sampling velocity at lake centre")
    vx0 = float(vel["vx"].interp(x=lake_x, y=lake_y).values)
    vy0 = float(vel["vy"].interp(x=lake_x, y=lake_y).values)
    speed = float(np.hypot(vx0, vy0))
    if not np.isfinite(speed) or speed < 1.0:
        raise SystemExit(f"  ! velocity at lake centre is {speed} m/yr — "
                         "off-grid or stagnant; check coordinates")
    heading = float(np.degrees(np.arctan2(vy0, vx0)))
    print(f"    vx={vx0:.2f}, vy={vy0:.2f} m/yr, speed={speed:.2f} m/yr, "
          f"heading={heading:.1f}° (0°=+x_polar, 90°=+y_polar)")

    # Unit flow vector in polar-stereo
    ux, uy = vx0 / speed, vy0 / speed

    # Build profile sample points
    n_half = int(round(l_half_m / dx_m))
    n_pts  = 2 * n_half + 1
    s = np.linspace(-l_half_m, l_half_m, n_pts)             # along-flow distance, m
    px = lake_x + s * ux
    py = lake_y + s * uy
    print(f"  profile: {n_pts} points, spacing {dx_m:.1f} m, "
          f"half-length {l_half_m/1000:.1f} km")

    # Sample bed + surface (BedMachine convention: surface is ice surface,
    # bed is bedrock; thickness = surface - bed where ice-covered)
    print("  sampling BedMachine along profile")
    surface_m = bilinear_sample(bm["surface"], px, py)
    bed_m     = bilinear_sample(bm["bed"],     px, py)
    thick_m   = bilinear_sample(bm["thickness"], px, py)

    # Profile geographic coordinates (for follow-on context maps)
    plon, plat = ps_to_ll(px, py)

    out = {
        "lake": {
            "lon": float(lake_lon),
            "lat": float(lake_lat),
            "x_m": float(lake_x),
            "y_m": float(lake_y),
            "surface_m": float(np.interp(0.0, s, surface_m)),
            "bed_m":     float(np.interp(0.0, s, bed_m)),
        },
        "flow": {
            "vx_m_yr": vx0,
            "vy_m_yr": vy0,
            "speed_m_yr": speed,
            "heading_deg": heading,
            "unit_x": ux,
            "unit_y": uy,
        },
        "profile": {
            "x_m":         [float(v) for v in s],
            "surface_m":   [float(v) for v in surface_m],
            "bed_m":       [float(v) for v in bed_m],
            "thickness_m": [float(v) for v in thick_m],
            "lon":         [float(v) for v in plon],
            "lat":         [float(v) for v in plat],
        },
        "meta": {
            "n_points": n_pts,
            "dx_m": dx_m,
            "l_half_m": l_half_m,
            "epsg": 3413,
            "bedmachine_path": BEDMACHINE,
            "itslive_path": ITSLIVE,
            "comment": (
                "Cross-section profile through North Lake along the local "
                "ice-flow direction. Along-profile distance s=0 is at the "
                "lake centre; positive s is downflow."
            ),
        },
    }

    OUTPUT.write_text(json.dumps(out, indent=2))
    size_kb = OUTPUT.stat().st_size / 1024
    print(f"  wrote {OUTPUT} ({size_kb:.1f} KB)")

    bm.close()
    vel.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--lake_lon", type=float, default=NL_LON)
    p.add_argument("--lake_lat", type=float, default=NL_LAT)
    p.add_argument("--l_half_km", type=float, default=L_HALF_M / 1000)
    p.add_argument("--dx_m",      type=float, default=DX_M)
    args = p.parse_args()
    main(args.lake_lon, args.lake_lat, args.l_half_km * 1000, args.dx_m)
