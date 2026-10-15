"""
Build a faint ESRI World Imagery basemap of the contiguous USA, used as
a "stack on top" geographic-context underlay beneath Greenland in the
Motivation scale comparator. Replaces the ad-hoc California polygons.

Output: website/public/usa_basemap.png
  **Albers Equal-Area Conic** (USA standard, parallels 29.5°N / 45.5°N).
  Equal-area is the right family for "compare areas honestly" — the
  card's narrative job is *Greenland is bigger than you think*, and the
  prior PlateCarree rendering exaggerated CONUS east-west by ~25% at
  37°N (cos(lat) ≈ 0.80), undermining the comparison. Albers preserves
  area; CONUS reads at its true ~1.55:1 W/N ratio.
  Faintness/desaturation is applied at render-time in the Three.js
  material, NOT here, so the source PNG stays a usable reference.

Run:
    cd cinematic
    source .venv/bin/activate
    python scene_01_intro/build_usa_basemap.py
"""

import os
import sys
from pathlib import Path

import certifi

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cartopy.crs as ccrs  # noqa: E402
import cartopy.io.img_tiles as cimgt  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from shared import CINEMATIC_DIR  # noqa: E402

OUT = CINEMATIC_DIR.parent / "website" / "public" / "usa_basemap.png"

# Whole contiguous USA so the audience reads "the United States" at a
# glance, not a regional crop they have to puzzle out.
LAT_S, LAT_N = 24.0, 50.0
LON_W, LON_E = -126.0, -66.0

ESRI_URL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}.jpg"
)
ZOOM = 5  # ~kilometre-scale resolution at this latitude. Plenty for a
          # faint underlay that's never the focus of attention.
# Figure aspect chosen to match CONUS Albers's natural bbox aspect
# (~1.85:1 width:height after projection, including the curve at the
# top of CONUS). Picking 18×10 gives matplotlib room to fit the
# projected geometry without big black side-margins.
FIGSIZE = (18, 10)
DPI = 200

# Albers Equal-Area Conic, USGS standard parallels for CONUS.
ALBERS = ccrs.AlbersEqualArea(
    central_longitude=-96.0,
    central_latitude=37.5,
    standard_parallels=(29.5, 45.5),
)


def main() -> None:
    import cartopy.io.shapereader as shapereader

    print("Fetching ESRI World Imagery tiles for CONUS…")
    tiler = cimgt.GoogleTiles(url=ESRI_URL)

    fig = plt.figure(figsize=FIGSIZE, facecolor="black")
    ax = fig.add_axes([0, 0, 1, 1], projection=ALBERS)
    ax.set_extent([LON_W, LON_E, LAT_S, LAT_N], crs=ccrs.PlateCarree())
    ax.set_facecolor("black")
    ax.set_axis_off()
    ax.add_image(tiler, ZOOM)

    # Overlay USA country outline + state boundaries in dark stroke so
    # the silhouette is recognisable even when desaturated/dimmed in
    # the website overlay.
    print("Overlaying USA outline + state boundaries…")
    countries_shp = shapereader.natural_earth(
        resolution="50m", category="cultural", name="admin_0_countries"
    )
    states_shp = shapereader.natural_earth(
        resolution="50m", category="cultural", name="admin_1_states_provinces_lines"
    )
    for record in shapereader.Reader(countries_shp).records():
        if record.attributes.get("NAME") == "United States of America":
            ax.add_geometries(
                [record.geometry], crs=ccrs.PlateCarree(),
                facecolor="none", edgecolor="black", linewidth=4.0,
            )
            break
    ax.add_geometries(
        list(shapereader.Reader(states_shp).geometries()),
        crs=ccrs.PlateCarree(),
        facecolor="none", edgecolor="black", linewidth=1.0, alpha=0.55,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.parent / "_usa_basemap_tmp.png"
    fig.savefig(tmp, dpi=DPI, facecolor="black", bbox_inches=None, pad_inches=0)
    plt.close(fig)

    # Albers-projected CONUS doesn't fill the rectangular figure (the
    # projection's curved top edge leaves a black margin top/bottom).
    # Crop tight to the non-black region so the website card has no gap
    # between the gold border and the imagery.
    import numpy as np
    from PIL import Image
    im = Image.open(tmp).convert("RGB")
    arr = np.array(im)
    luma = arr.mean(axis=2)
    nonblack_rows = np.where(luma.max(axis=1) > 8)[0]
    nonblack_cols = np.where(luma.max(axis=0) > 8)[0]
    r0, r1 = int(nonblack_rows[0]), int(nonblack_rows[-1])
    c0, c1 = int(nonblack_cols[0]), int(nonblack_cols[-1])
    cropped = arr[r0 : r1 + 1, c0 : c1 + 1]
    cropped_h, cropped_w = cropped.shape[:2]
    Image.fromarray(cropped).save(OUT, optimize=True)
    tmp.unlink()

    # Compute km/pixel of the CROPPED output so the website CSS can size
    # the Greenland silhouette overlay against the same display scale.
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    fig_w_px = FIGSIZE[0] * DPI
    fig_h_px = FIGSIZE[1] * DPI
    # Per-source-pixel km from the projection bbox.
    km_per_px_x_src = (x1 - x0) / 1000.0 / fig_w_px
    km_per_px_y_src = (y1 - y0) / 1000.0 / fig_h_px
    print(f"Wrote {OUT} ({OUT.stat().st_size/1024:.1f} KB)")
    print(f"  extent: lat {LAT_S}–{LAT_N}, lon {LON_W}–{LON_E}")
    print(f"  projected bbox: x={x0:.0f}–{x1:.0f} m, y={y0:.0f}–{y1:.0f} m")
    print(f"  uncropped pixel size: {fig_w_px}×{fig_h_px}")
    print(f"  cropped pixel size:   {cropped_w}×{cropped_h}  (removed {r0}px top, {fig_h_px - r1 - 1}px bottom)")
    print(f"  km per pixel (source / cropped): x={km_per_px_x_src:.3f}, y={km_per_px_y_src:.3f}")


if __name__ == "__main__":
    main()
