"""
Build a normalized Greenland bed-elevation heightmap from BedMachine v6,
in the same lat/lon extent as greenland_basemap.png.

Three.js samples this texture in the cross-section slab fragment shader
to compute bedrock vs ice vs sky at the moving cut longitude.

Encoding:
  Pixel value (0..255) → bed elevation in metres via:
      bed_m = pixel * (BED_MAX_M - BED_MIN_M) / 255 + BED_MIN_M
  with BED_MIN_M = -3000, BED_MAX_M = 2500 (covers BedMachine v6 range
  with a little headroom).

Run:
    cd cinematic
    source .venv/bin/activate
    python scene_01_intro/build_bed_texture.py

Outputs:
    data/greenland_bed.png            (cinematic-side QA copy)
    website/public/greenland_bed.png  (Three.js loads as bed map)
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
from PIL import Image, ImageFilter  # noqa: E402

from shared import BEDMACHINE_PATH, CINEMATIC_DIR  # noqa: E402

DATA_DIR = CINEMATIC_DIR / "data"
OUT = DATA_DIR / "greenland_bed.png"
PUBLIC_OUT = CINEMATIC_DIR.parent / "website" / "public" / "greenland_bed.png"

LON_W, LON_E = -75.0, -10.0
LAT_S, LAT_N = 59.0, 84.0
FIGSIZE = (26, 10)
DPI = 200

BED_MIN_M = -3000.0   # deepest below sea level (BedMachine min ≈ -2700)
BED_MAX_M = 2500.0    # highest bed peak (BedMachine max ≈ 2400)
STRIDE = 8


def find_greenland_geometry():
    shp = shapereader.natural_earth(
        resolution="10m", category="cultural", name="admin_0_countries"
    )
    for record in shapereader.Reader(shp).records():
        if record.attributes.get("NAME") == "Greenland":
            return record.geometry
    raise RuntimeError("Greenland not found in Natural Earth countries shapefile")


def render_bed(out_path) -> None:
    print(f"opening {BEDMACHINE_PATH}")
    ds = xr.open_dataset(BEDMACHINE_PATH, chunks={"x": 2000, "y": 2000})
    bed = ds["bed"].isel(
        x=slice(None, None, STRIDE), y=slice(None, None, STRIDE)
    ).load()
    print(f"  subset shape: y={len(bed.y)} x={len(bed.x)}")
    print(f"  bed range: {float(bed.min()):.0f} to {float(bed.max()):.0f} m")

    x = bed.x.values
    y = bed.y.values
    z = np.nan_to_num(bed.values.astype(np.float32), nan=0.0)
    z_norm = np.clip((z - BED_MIN_M) / (BED_MAX_M - BED_MIN_M), 0.0, 1.0)

    src = ccrs.NorthPolarStereo(central_longitude=-45.0, true_scale_latitude=70.0)
    proj = ccrs.PlateCarree()

    fig = plt.figure(figsize=FIGSIZE, facecolor="black")
    ax = fig.add_axes([0, 0, 1, 1], projection=proj)
    ax.set_extent([LON_W, LON_E, LAT_S, LAT_N], crs=proj)
    ax.set_facecolor("black")
    ax.set_axis_off()

    ax.pcolormesh(
        x, y, z_norm,
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

    bed_tmp = DATA_DIR / "_bed.png"
    mask_tmp = DATA_DIR / "_mask_bed.png"

    print("rendering bed elevation...")
    render_bed(bed_tmp)

    print("rendering greenland mask...")
    geom = find_greenland_geometry()
    render_mask(mask_tmp, geom)

    bed = Image.open(bed_tmp).convert("L")
    mask = Image.open(mask_tmp).convert("L")

    # Mild blur on the bed itself to tame fjord-scale detail at the
    # cross-section's relatively coarse vertical resolution.
    bed = bed.filter(ImageFilter.GaussianBlur(radius=3))

    mask_arr = np.array(mask)
    binary = mask_arr > 128
    binary = binary_dilation(binary, iterations=2)
    mask_arr = (binary.astype(np.float32) * 255).astype(np.uint8)
    mask = Image.fromarray(mask_arr, mode="L").filter(
        ImageFilter.GaussianBlur(radius=3)
    )

    bed_arr = np.array(bed).astype(np.float32)
    mask_arr = np.array(mask).astype(np.float32) / 255.0
    # Outside the Greenland mask: encode "no data" as a pixel value
    # corresponding to BED_MIN_M (so the shader naturally treats it as
    # "very deep, all water above"). Easier than carrying a separate
    # mask channel.
    final = (bed_arr * mask_arr).astype(np.uint8)

    Image.fromarray(final, mode="L").save(OUT)

    bed_tmp.unlink()
    mask_tmp.unlink()
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")

    PUBLIC_OUT.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_OUT.write_bytes(OUT.read_bytes())
    print(f"wrote {PUBLIC_OUT}")
    print()
    print(f"  pixel→m: bed_m = pixel/255 * {BED_MAX_M - BED_MIN_M} + ({BED_MIN_M})")


if __name__ == "__main__":
    main()
