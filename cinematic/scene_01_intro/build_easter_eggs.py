"""
Build alpha-mask textures for easter-egg hotspots on the spinning hub
globe. Each texture is a small PNG over the bounding box of a state /
region; the alpha channel is opaque inside the region's polygon and
transparent outside. Three.js uses these for hover detection (raycaster
hit + alpha sample) and for the colored glow + black outline shaders.

Currently:
  - New Jersey → click opens https://aos.princeton.edu/ (Princeton AOS)

Add new ones by editing the EGGS list below.

Run:
    cd cinematic
    source .venv/bin/activate
    python scene_01_intro/build_easter_eggs.py

Outputs (one PNG per egg):
    website/public/egg_<id>.png
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
from PIL import Image  # noqa: E402

from shared import CINEMATIC_DIR  # noqa: E402

PUBLIC_DIR = CINEMATIC_DIR.parent / "website" / "public"
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

# Each egg: id, state name (matches Natural Earth admin_1 'name' field),
# country, lat/lon bounding box.
EGGS = [
    {
        "id": "nj",
        "state_name": "New Jersey",
        "country": "United States of America",
        "lat_s": 38.8,
        "lat_n": 41.5,
        "lon_w": -75.7,
        "lon_e": -73.7,
    },
]

DPI = 200


def find_state_geometry(state_name: str, country: str):
    shp = shapereader.natural_earth(
        resolution="10m",
        category="cultural",
        name="admin_1_states_provinces",
    )
    for record in shapereader.Reader(shp).records():
        attrs = record.attributes
        if attrs.get("name") == state_name and attrs.get("admin") == country:
            return record.geometry
    raise RuntimeError(f"{state_name} not found in admin_1_states_provinces")


def build_egg(egg) -> None:
    geom = find_state_geometry(egg["state_name"], egg["country"])

    lon_w = egg["lon_w"]
    lon_e = egg["lon_e"]
    lat_s = egg["lat_s"]
    lat_n = egg["lat_n"]

    # Aspect of the bounding box on a PlateCarree map.
    aspect = (lon_e - lon_w) / (lat_n - lat_s)
    fig_w = 4
    fig_h = fig_w / aspect

    proj = ccrs.PlateCarree()
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="black")
    ax = fig.add_axes([0, 0, 1, 1], projection=proj)
    ax.set_extent([lon_w, lon_e, lat_s, lat_n], crs=proj)
    ax.set_facecolor("black")
    ax.set_axis_off()

    ax.add_geometries(
        [geom],
        crs=ccrs.PlateCarree(),
        facecolor="white",
        edgecolor="none",
    )

    tmp = PUBLIC_DIR / f"_egg_{egg['id']}_tmp.png"
    fig.savefig(tmp, dpi=DPI, facecolor="black", bbox_inches=None, pad_inches=0)
    plt.close(fig)

    # Convert to RGBA: alpha = white channel (state polygon = opaque).
    img = Image.open(tmp).convert("L")
    arr = np.array(img)
    rgba = np.zeros((*arr.shape, 4), dtype=np.uint8)
    rgba[..., 0:3] = 255
    rgba[..., 3] = arr
    out = PUBLIC_DIR / f"egg_{egg['id']}.png"
    Image.fromarray(rgba, mode="RGBA").save(out)
    tmp.unlink()
    print(f"wrote {out} ({out.stat().st_size / 1024:.1f} KB) — {egg['state_name']}")


def main() -> None:
    for egg in EGGS:
        build_egg(egg)


if __name__ == "__main__":
    main()
