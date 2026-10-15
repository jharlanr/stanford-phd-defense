"""
Build a velocity-colored basemap PNG for Greenland from ITS_LIVE.

Same lat/lon extent + projection as data/greenland_basemap.png so the
two textures can be cross-faded on identical sphere geometry. The
satellite basemap shows during clicks 1-2 (Greenland as snow); this
velocity basemap shows during click 3 (Greenland coloured by ice speed,
NASA-SVS aesthetic).

Pipeline:
  1. Load the ITS_LIVE Greenland subset NetCDF (data/its_live_greenland_subset.nc).
  2. pcolormesh in EPSG:3413 with cartopy reprojecting to PlateCarree.
  3. Apply LogNorm(1, 3000) + the same colormap used by compute_streamlines.py
     for the QA preview. Keep these aligned so the static preview reads
     the same as the live render.
  4. Mask to Greenland's coastline (Natural Earth polygon, dilated +
     feathered identically to build_greenland_basemap.py so the patch
     covers the same buffer beyond the coast).

Run:
    cd cinematic
    source .venv/bin/activate
    python scene_01_intro/build_velocity_colormap.py

Outputs:
    data/greenland_velocity.png            (cinematic-side QA copy)
    website/public/greenland_velocity.png  (Three.js loads this)
"""

import os
import sys
from pathlib import Path

import certifi  # noqa: E402

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cartopy.crs as ccrs  # noqa: E402
import cartopy.io.shapereader as shapereader  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import xarray as xr  # noqa: E402
from matplotlib.colors import LogNorm  # noqa: E402
from PIL import Image, ImageFilter  # noqa: E402

from shared import CINEMATIC_DIR  # noqa: E402

DATA_DIR = CINEMATIC_DIR / "data"
SUBSET_NC = DATA_DIR / "its_live_greenland_subset.nc"
OUT = DATA_DIR / "greenland_velocity.png"
PUBLIC_OUT = CINEMATIC_DIR.parent / "website" / "public" / "greenland_velocity.png"

# Must match build_greenland_basemap.py exactly so the velocity texture
# can be swapped onto the same SphereGeometry segment.
LON_W, LON_E = -75.0, -10.0
LAT_S, LAT_N = 59.0, 84.0
FIGSIZE = (26, 10)
DPI = 400

# Velocity colormap. Aligns with compute_streamlines.py preview so the
# static and live renders use the same colorbar.
CMAP = "turbo"
SPEED_MIN = 1.0      # m/yr — anything below renders at the cmap's low end
SPEED_MAX = 3000.0   # m/yr — saturates at fastest tongues like Jakobshavn


def find_greenland_geometry():
    shp = shapereader.natural_earth(
        resolution="10m", category="cultural", name="admin_0_countries"
    )
    for record in shapereader.Reader(shp).records():
        if record.attributes.get("NAME") == "Greenland":
            return record.geometry
    raise RuntimeError("Greenland not found in Natural Earth countries shapefile")


def render_velocity(out_path) -> None:
    ds = xr.open_dataset(SUBSET_NC)
    speed = ds["v"].values
    x = ds["x"].values
    y = ds["y"].values

    # ITS_LIVE is on EPSG:3413 (NSIDC sea-ice polar stereographic north).
    # cartopy reprojects pcolormesh from this onto PlateCarree.
    src = ccrs.NorthPolarStereo(central_longitude=-45.0, true_scale_latitude=70.0)
    proj = ccrs.PlateCarree()

    fig = plt.figure(figsize=FIGSIZE, facecolor="black")
    ax = fig.add_axes([0, 0, 1, 1], projection=proj)
    ax.set_extent([LON_W, LON_E, LAT_S, LAT_N], crs=proj)
    ax.set_facecolor("black")
    ax.set_axis_off()

    ax.pcolormesh(
        x,
        y,
        speed,
        transform=src,
        cmap=CMAP,
        norm=LogNorm(vmin=SPEED_MIN, vmax=SPEED_MAX),
        shading="auto",
        rasterized=True,
    )

    fig.savefig(out_path, dpi=DPI, facecolor="black", bbox_inches=None, pad_inches=0)
    plt.close(fig)


def render_mask(out_path, geom) -> None:
    proj = ccrs.PlateCarree()
    fig = plt.figure(figsize=FIGSIZE, facecolor="black")
    ax = fig.add_axes([0, 0, 1, 1], projection=proj)
    ax.set_extent([LON_W, LON_E, LAT_S, LAT_N], crs=ccrs.PlateCarree())
    ax.set_facecolor("black")
    ax.set_axis_off()
    ax.add_geometries(
        [geom],
        crs=ccrs.PlateCarree(),
        facecolor="white",
        edgecolor="none",
    )
    fig.savefig(out_path, dpi=DPI, facecolor="black", bbox_inches=None, pad_inches=0)
    plt.close(fig)


def main() -> None:
    from scipy.ndimage import binary_dilation  # noqa: PLC0415

    velocity_tmp = DATA_DIR / "_velocity.png"
    mask_tmp = DATA_DIR / "_mask_velocity.png"

    print("rendering velocity field...")
    render_velocity(velocity_tmp)

    print("rendering greenland mask...")
    geom = find_greenland_geometry()
    render_mask(mask_tmp, geom)

    velocity = Image.open(velocity_tmp).convert("RGBA")
    mask = Image.open(mask_tmp).convert("L")
    mask_arr = np.array(mask)

    # Same dilation + feather as build_greenland_basemap.py so the patch
    # has identical alpha falloff at the coastline.
    binary = mask_arr > 128
    binary = binary_dilation(binary, iterations=25)
    mask_arr = (binary.astype(np.float32) * 255).astype(np.uint8)
    mask = Image.fromarray(mask_arr, mode="L")
    mask = mask.filter(ImageFilter.GaussianBlur(radius=12))

    img_arr = np.array(velocity)
    mask_arr = np.array(mask).astype(np.float32) / 255.0
    img_arr[..., 3] = (img_arr[..., 3].astype(np.float32) * mask_arr).astype(np.uint8)
    Image.fromarray(img_arr).save(OUT)

    velocity_tmp.unlink()
    mask_tmp.unlink()
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")

    PUBLIC_OUT.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_OUT.write_bytes(OUT.read_bytes())
    print(f"wrote {PUBLIC_OUT}")


if __name__ == "__main__":
    main()
