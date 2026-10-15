"""
Build animated velocity streamlines over Greenland from ITS_LIVE.

Pipeline (work in progress):
  1. Load ITS_LIVE NetCDF (subset — full file is 47 GB) ⟵ THIS STEP
  2. Downsample to a manageable grid
  3. Generate streamlines from (vx, vy)
  4. Reproject from EPSG:3413 (NSIDC polar stereographic) to lat/lon
  5. Save as JSON for the Three.js renderer
  6. Three.js loads streamlines and animates flowing dashes via shader

Run:
    cd cinematic
    source .venv/bin/activate
    python scene_01_intro/build_velocity_streamlines.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import xarray as xr  # noqa: E402

from shared import CINEMATIC_DIR  # noqa: E402

# The lab drive's ITS_LIVE mosaic (this early step predates the
# source_data copy rule). Set LAB_DRIVE in the environment.
ITS_LIVE_PATH = (
    os.environ.get("LAB_DRIVE", "/path/to/your/lab/drive")
    + "/Lab_files/pnas2025/repos/sgl-stress/2d/data/"
    "ITS_LIVE_velocity_120m_RGI05A_0000_V02.1.nc"
)

OUT_DIR = CINEMATIC_DIR / "data"
OUT_DIR.mkdir(exist_ok=True)
OUT_NC = OUT_DIR / "its_live_greenland_subset.nc"

# Downsample factor — 120 m × 30 = 3.6 km grid (fine enough for streamlines,
# small enough to load comfortably).
STRIDE = 30


def main() -> None:
    print(f"opening {ITS_LIVE_PATH}")
    ds = xr.open_dataset(ITS_LIVE_PATH, chunks={"x": 2000, "y": 2000})

    print(f"  full shape: y={len(ds.y)} x={len(ds.x)}")
    print(f"  x range: {float(ds.x.min()):.0f} .. {float(ds.x.max()):.0f} m")
    print(f"  y range: {float(ds.y.min()):.0f} .. {float(ds.y.max()):.0f} m")

    # Pull just the velocity components we need; drop everything else.
    sub = ds[["vx", "vy", "v", "landice"]]
    sub = sub.isel(x=slice(None, None, STRIDE), y=slice(None, None, STRIDE))
    print(f"  subset shape: y={len(sub.y)} x={len(sub.x)}")

    # Realize into memory (small enough now).
    sub = sub.load()

    # Save for next session — the streamline + reprojection step picks up here.
    sub.to_netcdf(OUT_NC)
    print(f"wrote {OUT_NC} ({OUT_NC.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
