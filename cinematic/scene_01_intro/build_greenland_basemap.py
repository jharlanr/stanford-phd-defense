"""
Build a clean Greenland basemap PNG using ESRI World Imagery tiles.

Same data source as ESSD figure 1 panel (a), but without annotations,
gridlines, or markers. Saved with a transparent background outside
the polar-stereographic disc that fits Greenland.

Run once:
    cd cinematic
    source .venv/bin/activate
    python scene_01_intro/build_greenland_basemap.py

Output: data/greenland_basemap.png (used as a texture by Beat B / C).
"""

import os
import sys
from pathlib import Path

# Fix macOS Python-installer SSL cert issue before any network code runs.
import certifi  # noqa: E402

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cartopy.crs as ccrs  # noqa: E402
import cartopy.io.img_tiles as cimgt  # noqa: E402
import cartopy.io.shapereader as shapereader  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageFilter  # noqa: E402

from shared import CINEMATIC_DIR  # noqa: E402

OUT_DIR = CINEMATIC_DIR / "data"
OUT_DIR.mkdir(exist_ok=True)
# Hi-res variant. The original 10400 × 4000 / zoom-7 basemap (~3 MB)
# stays at `greenland_basemap.png`; the hires version goes to its own
# filename so we can switch over in Globe.vue without breaking main.
HIRES = True
OUT = OUT_DIR / ("greenland_basemap_hires.png" if HIRES else "greenland_basemap.png")

# Tight bounding box around Greenland only. Iceland and Canadian Arctic
# excluded — they cause heavy PlateCarree longitude distortion at high
# latitudes and aren't needed for the defense narrative.
LON_W, LON_E = -75.0, -10.0
LAT_S, LAT_N = 59.0, 84.0

# ESRI World Imagery — same source as ESSD figure 1.
ESRI_URL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}.jpg"
)
# Zoom 11 puts a tile at ~125 m/pixel ground resolution over Greenland
# — fine enough to RESOLVE supraglacial lakes (~1 km² = 8 pixels) as
# natural cyan patches in the imagery, removing the need for the
# synthetic flat-disc lake overlay. Verified by spot-checking a tile
# near North Lake (lakes clearly visible). ~25k–50k tile fetches; takes
# 5–10 minutes against ESRI's tile service but cartopy caches them.
# Zoom 7 (legacy) was ~125 tiles at ~5 km/pixel — too coarse to show
# any sub-km surface feature.
ZOOM = 11 if HIRES else 7

# Output dimensions:
#   Legacy:  10400 × 4000  (FIGSIZE 26×10 @ DPI 400)
#   Hi-res:  16380 × 6300  (FIGSIZE 26×10 @ DPI 630)
# 16384 is the WebGL max texture size on most desktop GPUs; we keep
# under that ceiling while saturating it. Aspect 2.6:1 matches the
# 65° lon × 25° lat extent at PlateCarree projection.
FIGSIZE = (26, 10)
DPI = 630 if HIRES else 400


def find_greenland_geometry():
    """Locate Greenland's polygon in Natural Earth's countries shapefile."""
    shp = shapereader.natural_earth(
        resolution="10m", category="cultural", name="admin_0_countries"
    )
    for record in shapereader.Reader(shp).records():
        if record.attributes.get("NAME") == "Greenland":
            return record.geometry
    raise RuntimeError("Greenland not found in Natural Earth countries shapefile")


def render_imagery(out_path) -> None:
    # PlateCarree (equirectangular) — maps cleanly onto a SphereGeometry
    # segment so the patch sits exactly on the globe's surface.
    proj = ccrs.PlateCarree()
    fig = plt.figure(figsize=FIGSIZE)
    fig.patch.set_alpha(0.0)
    ax = fig.add_axes([0, 0, 1, 1], projection=proj)
    ax.set_extent([LON_W, LON_E, LAT_S, LAT_N], crs=ccrs.PlateCarree())
    ax.patch.set_alpha(0.0)
    ax.set_axis_off()
    tiles = cimgt.GoogleTiles(url=ESRI_URL)
    ax.add_image(tiles, ZOOM)
    fig.savefig(out_path, dpi=DPI, transparent=True, bbox_inches=None, pad_inches=0)
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

    imagery_tmp = OUT_DIR / "_imagery.png"
    mask_tmp = OUT_DIR / "_mask.png"

    geom = find_greenland_geometry()
    render_imagery(imagery_tmp)
    render_mask(mask_tmp, geom)

    imagery = Image.open(imagery_tmp).convert("RGBA")
    mask = Image.open(mask_tmp).convert("L")
    mask_arr = np.array(mask)

    # Dilate Greenland's mask outward so the patch covers a small buffer
    # beyond the coastline. This hides the underlying globe's pixelated
    # "halo" where bilinear-filtered low-res texels spill past the coast.
    binary = mask_arr > 128
    binary = binary_dilation(binary, iterations=25)
    mask_arr = (binary.astype(np.float32) * 255).astype(np.uint8)
    mask = Image.fromarray(mask_arr, mode="L")

    # Feather the dilated edge so the buffer transitions smoothly to
    # transparency instead of showing a hard rectangular cutoff.
    mask = mask.filter(ImageFilter.GaussianBlur(radius=12))

    img_arr = np.array(imagery)
    mask_arr = np.array(mask).astype(np.float32) / 255.0
    img_arr[..., 3] = (img_arr[..., 3].astype(np.float32) * mask_arr).astype(np.uint8)
    Image.fromarray(img_arr).save(OUT, optimize=True)

    imagery_tmp.unlink()
    mask_tmp.unlink()
    print(f"wrote {OUT}")
    print(f"  dimensions: {img_arr.shape[1]} × {img_arr.shape[0]}")
    print(f"  size:       {OUT.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
