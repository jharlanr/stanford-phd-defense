"""
Build a Greenland silhouette PNG in **Lambert Azimuthal Equal-Area**
(LAEA) projection, centered on Greenland (~71°N, -42°W). Equal-area is
the right family for the size-comparison card whose narrative job is
*Greenland is bigger than you think* — pairs with the USA basemap
(also rebuilt in equal-area: Albers Equal-Area Conic). Polar
stereographic (the prior choice) is conformal, not equal-area.

Output: website/public/greenland_silhouette.png + km-per-px metadata
printed to stdout so the website CSS can size against the same scale
as the USA basemap.

Run:
    cd cinematic
    source .venv/bin/activate
    python scene_01_intro/build_greenland_silhouette.py
"""

import os
import sys
from pathlib import Path

import certifi

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cartopy.crs as ccrs  # noqa: E402
import cartopy.io.shapereader as shapereader  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from shared import CINEMATIC_DIR  # noqa: E402

OUT = CINEMATIC_DIR.parent / "website" / "public" / "greenland_silhouette.png"


def main() -> None:
    print("Loading Greenland country polygon (Natural Earth)...")
    shp = shapereader.natural_earth(
        resolution="10m", category="cultural", name="admin_0_countries"
    )
    geom = None
    for rec in shapereader.Reader(shp).records():
        if rec.attributes.get("NAME") == "Greenland":
            geom = rec.geometry
            break
    if geom is None:
        raise RuntimeError("Greenland not found in admin_0_countries")

    # Lambert Azimuthal Equal-Area centered on Greenland's geographic
    # center. Equal-area projection — pairs cleanly with the Albers
    # Equal-Area CONUS basemap for an honest area comparison.
    proj = ccrs.LambertAzimuthalEqualArea(
        central_longitude=-42.0, central_latitude=71.0
    )

    # Pick a figure aspect that approximately matches the projected
    # bbox so pixels stay square. Bbox is ~3582 km × 2882 km (W×H);
    # 2.4 km/px target → ~1500×1200 figure pixels. set_aspect('equal')
    # below also enforces this, so the figsize is mostly a hint.
    FIGSIZE = (12, 10)
    DPI = 200
    fig = plt.figure(figsize=FIGSIZE, facecolor="black")
    ax = fig.add_axes([0, 0, 1, 1], projection=proj)
    ax.set_extent([-75, -10, 59, 84], crs=ccrs.PlateCarree())
    ax.set_aspect("equal")  # square pixels — required for honest area comparison.
    ax.set_facecolor("black")
    ax.set_axis_off()
    ax.add_geometries(
        [geom], crs=ccrs.PlateCarree(), facecolor="white", edgecolor="none"
    )

    # Capture km/px BEFORE saving so we know the rendered scale.
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    fig_w_px = FIGSIZE[0] * DPI
    fig_h_px = FIGSIZE[1] * DPI
    # Bbox extents may differ from figure aspect when set_aspect('equal')
    # adds matplotlib-side padding; report both for sanity.
    bbox_w_km = (x1 - x0) / 1000.0
    bbox_h_km = (y1 - y0) / 1000.0
    km_per_px_x = bbox_w_km / fig_w_px
    km_per_px_y = bbox_h_km / fig_h_px
    print(f"  projected bbox: {bbox_w_km:.0f} × {bbox_h_km:.0f} km (W × H)")
    print(f"  km per pixel: x={km_per_px_x:.3f}, y={km_per_px_y:.3f}")
    print(f"  uncropped pixel size: {fig_w_px}×{fig_h_px}")

    tmp = OUT.parent / "_silhouette_tmp.png"
    fig.savefig(tmp, dpi=DPI, facecolor="black", bbox_inches=None, pad_inches=0)
    plt.close(fig)

    # Convert to white-on-transparent silhouette, crop to tight bbox.
    img = Image.open(tmp).convert("RGBA")
    arr = np.array(img)
    # Black background → transparent; white Greenland → opaque white.
    luminance = arr[:, :, :3].mean(axis=2)
    alpha = (luminance > 32).astype(np.uint8) * 255
    rows = np.where(alpha.any(axis=1))[0]
    cols = np.where(alpha.any(axis=0))[0]
    r_min, r_max = rows[0], rows[-1]
    c_min, c_max = cols[0], cols[-1]
    print(f"  cropped: {c_max - c_min + 1} × {r_max - r_min + 1} px")

    h = r_max - r_min + 1
    w = c_max - c_min + 1
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[:, :, 0] = 255
    out[:, :, 1] = 255
    out[:, :, 2] = 255
    out[:, :, 3] = alpha[r_min : r_max + 1, c_min : c_max + 1]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(out, mode="RGBA").save(OUT, optimize=True)
    tmp.unlink()
    print(f"Wrote {OUT} ({OUT.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
