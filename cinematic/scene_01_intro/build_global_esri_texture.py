"""
Build a global ESRI World Imagery texture for the live Three.js globe.
Equirectangular (PlateCarree) projection, the standard for a Three.js
SphereGeometry texture.

Run once:
    cd cinematic
    source .venv/bin/activate
    python scene_01_intro/build_global_esri_texture.py

Output: website/public/earth_esri.jpg.
"""

import os
import sys
from pathlib import Path

import certifi  # noqa: E402

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cartopy.crs as ccrs  # noqa: E402
import cartopy.io.img_tiles as cimgt  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from shared import CINEMATIC_DIR  # noqa: E402

OUT = CINEMATIC_DIR.parent / "website" / "public" / "earth_esri.jpg"

ESRI_URL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}.jpg"
)
ZOOM = 7  # zoom 7 → 16× more tiles than zoom 5, ~32k×16k raw. Three.js
          # downsamples to GPU max (8192-16384 depending on hardware);
          # higher source means whatever survives is sharper. Builds in
          # ~10-15 minutes — run in background.
# White background so the un-tiled polar regions (above ~85° lat) blend
# with the surrounding ESRI snow/ice imagery instead of looking like
# a black void on the sphere.
BG = "white"


def main() -> None:
    # Large figure for zoom 7 — figsize × dpi sets the output JPEG
    # dimensions. 160×80 inches at 100 dpi → 16000×8000 px, right at
    # the typical GPU max texture cap.
    fig = plt.figure(figsize=(160, 80), facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1], projection=ccrs.PlateCarree())
    ax.set_global()
    ax.set_axis_off()
    ax.set_facecolor(BG)

    tiles = cimgt.GoogleTiles(url=ESRI_URL)
    ax.add_image(tiles, ZOOM)

    fig.savefig(OUT, dpi=100, facecolor=BG, bbox_inches=None, pad_inches=0)
    plt.close(fig)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
