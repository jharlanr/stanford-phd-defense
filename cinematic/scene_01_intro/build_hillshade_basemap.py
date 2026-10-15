"""
Build a hillshaded ice-surface PNG from BedMachine v6.

Same projection + extent as greenland_basemap.png so the same
SphereGeometry segment can swap textures. Click 3 cross-fades the
satellite snow → this hillshade so the audience reads contour /
slope structure on the elevated ice mound during the dimensions
narration. Click 4 then cross-fades hillshade → velocity colormap.

Pipeline:
  1. Load BedMachine v6 surface, stride-downsample
  2. matplotlib LightSource hillshade (NW sun, vert_exag for slope visibility)
  3. Reproject EPSG:3413 → PlateCarree via cartopy
  4. Mask + feather to Greenland coastline
  5. Save 8-bit greyscale (Three.js material tints to icy white)

Run:
    cd cinematic
    source .venv/bin/activate
    python scene_01_intro/build_hillshade_basemap.py

Outputs:
    data/greenland_hillshade.png
    website/public/greenland_hillshade.png
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
from matplotlib.colors import LightSource  # noqa: E402
from PIL import Image, ImageFilter  # noqa: E402

from shared import BEDMACHINE_PATH, CINEMATIC_DIR  # noqa: E402

DATA_DIR = CINEMATIC_DIR / "data"
OUT = DATA_DIR / "greenland_hillshade.png"
PUBLIC_OUT = CINEMATIC_DIR.parent / "website" / "public" / "greenland_hillshade.png"

LON_W, LON_E = -75.0, -10.0
LAT_S, LAT_N = 59.0, 84.0
FIGSIZE = (26, 10)
DPI = 300

# 1.2 km grid — finer detail invisible at viewing scale.
STRIDE = 8

# Hillshade tuning: NW sun (315° azimuth) at 30° altitude is a tradeoff
# between cartography-standard noon (45°) and grazing sunset (15°).
# vert_exag = 80 lifts Greenland's gentle ice-sheet slopes (<0.5°) out
# of the [0.45, 0.55] near-uniform band that would wash out against
# saturated-white satellite snow, without splaying the surface into
# the harsh cracks-and-ridges look that pure raking light produces.
SUN_AZIMUTH_DEG = 315.0
SUN_ALTITUDE_DEG = 30.0
HILLSHADE_VERT_EXAG = 80.0


def find_greenland_geometry():
    shp = shapereader.natural_earth(
        resolution="10m", category="cultural", name="admin_0_countries"
    )
    for record in shapereader.Reader(shp).records():
        if record.attributes.get("NAME") == "Greenland":
            return record.geometry
    raise RuntimeError("Greenland not found in Natural Earth countries shapefile")


def render_hillshade(out_path) -> None:
    print(f"opening {BEDMACHINE_PATH}")
    ds = xr.open_dataset(BEDMACHINE_PATH, chunks={"x": 2000, "y": 2000})
    surf = ds["surface"].isel(
        x=slice(None, None, STRIDE), y=slice(None, None, STRIDE)
    ).load()
    print(f"  shape: y={len(surf.y)} x={len(surf.x)}")

    elev = np.nan_to_num(surf.values.astype(np.float32), nan=0.0)
    x = surf.x.values
    y = surf.y.values

    # Cell size in metres — needed by LightSource.hillshade for slope.
    dx = float(abs(x[1] - x[0]))
    dy = float(abs(y[1] - y[0]))

    ls = LightSource(azdeg=SUN_AZIMUTH_DEG, altdeg=SUN_ALTITUDE_DEG)
    hs = ls.hillshade(elev, vert_exag=HILLSHADE_VERT_EXAG, dx=dx, dy=dy)

    src = ccrs.NorthPolarStereo(central_longitude=-45.0, true_scale_latitude=70.0)
    proj = ccrs.PlateCarree()

    fig = plt.figure(figsize=FIGSIZE, facecolor="black")
    ax = fig.add_axes([0, 0, 1, 1], projection=proj)
    ax.set_extent([LON_W, LON_E, LAT_S, LAT_N], crs=proj)
    ax.set_facecolor("black")
    ax.set_axis_off()

    ax.pcolormesh(
        x, y, hs,
        transform=src,
        cmap="gray",
        vmin=0.0, vmax=1.0,
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
        [geom], crs=ccrs.PlateCarree(), facecolor="white", edgecolor="none"
    )
    fig.savefig(out_path, dpi=DPI, facecolor="black", bbox_inches=None, pad_inches=0)
    plt.close(fig)


def main() -> None:
    from scipy.ndimage import binary_dilation  # noqa: PLC0415

    hs_tmp = DATA_DIR / "_hillshade.png"
    mask_tmp = DATA_DIR / "_mask_hs.png"

    print("rendering hillshade...")
    render_hillshade(hs_tmp)

    print("rendering mask...")
    geom = find_greenland_geometry()
    render_mask(mask_tmp, geom)

    hs = Image.open(hs_tmp).convert("RGBA")
    mask = Image.open(mask_tmp).convert("L")
    mask_arr = np.array(mask)
    binary = mask_arr > 128
    binary = binary_dilation(binary, iterations=15)
    mask_arr = (binary.astype(np.float32) * 255).astype(np.uint8)
    mask = Image.fromarray(mask_arr, mode="L").filter(ImageFilter.GaussianBlur(radius=8))

    img_arr = np.array(hs)
    mask_arr = np.array(mask).astype(np.float32) / 255.0
    img_arr[..., 3] = (img_arr[..., 3].astype(np.float32) * mask_arr).astype(np.uint8)
    Image.fromarray(img_arr).save(OUT)

    hs_tmp.unlink()
    mask_tmp.unlink()
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")

    PUBLIC_OUT.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_OUT.write_bytes(OUT.read_bytes())
    print(f"wrote {PUBLIC_OUT}")


if __name__ == "__main__":
    main()
