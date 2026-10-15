"""
Bake the hillshade into the satellite basemap PNG.

The satellite imagery (greenland_basemap.png) already gives Greenland
its photographic snow look. Multiplying by the BedMachine-derived
hillshade adds slope contour visibility — interior ridges and valleys
become readable as the audience sees the elevated DEM in click 3+,
without losing the satellite aesthetic the director wanted kept.

Run after build_greenland_basemap.py and build_hillshade_basemap.py
(both must produce their PNGs first):

    cd cinematic
    source .venv/bin/activate
    python scene_01_intro/combine_basemap_hillshade.py

Outputs (overwrites):
    data/greenland_basemap.png            (hillshaded satellite)
    website/public/greenland_basemap.png
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from shared import CINEMATIC_DIR  # noqa: E402

DATA_DIR = CINEMATIC_DIR / "data"
BASEMAP_PNG = DATA_DIR / "greenland_basemap.png"
HILLSHADE_PNG = DATA_DIR / "greenland_hillshade.png"
PUBLIC_BASEMAP = CINEMATIC_DIR.parent / "website" / "public" / "greenland_basemap.png"

# Amplification factor for the hillshade signal around its 0.5 midpoint.
# Greenland's gentle ice-sheet slopes give matplotlib LightSource a
# narrow [~0.4, 0.55] hillshade range; multiplying the (hs-0.5) delta
# by AMPLIFY widens the visible variation. We clip the *upper* end at
# 1.0 (asymmetric shading) — saturated white snow can't go any brighter,
# so the only useful direction is darkening shadowed slopes.
HILLSHADE_AMPLIFY = 5.0


def main() -> None:
    imagery = Image.open(BASEMAP_PNG).convert("RGBA")
    hillshade = Image.open(HILLSHADE_PNG).convert("RGBA")

    if hillshade.size != imagery.size:
        hillshade = hillshade.resize(imagery.size, Image.LANCZOS)

    img_arr = np.array(imagery).astype(np.float32)
    hs_arr = np.array(hillshade).astype(np.float32) / 255.0

    # The hillshade was saved with a 'gray' cmap so all RGB channels are
    # equal — pull luminance from R. Mask alpha from the hillshade tells
    # us which pixels are inside Greenland's coastline; outside, fall
    # back to neutral 0.5 (no shading) so the satellite ocean and small
    # off-Greenland landmasses (Iceland, Canadian Arctic) aren't darkened.
    hs_lum = hs_arr[..., 0]
    hs_alpha = hs_arr[..., 3]
    hs_lum = np.where(hs_alpha > 0.05, hs_lum, 0.5)

    # Asymmetric multiplicative factor: amplify the hillshade delta
    # around 0.5, then cap *above* at 1.0 (no brightening). Shadows
    # darken visibly on saturated-white snow; flat / lit areas stay
    # at the satellite imagery's natural brightness.
    factor = 1.0 + (hs_lum - 0.5) * HILLSHADE_AMPLIFY
    factor = np.clip(factor, 0.2, 1.0)

    for c in range(3):
        img_arr[..., c] = np.clip(img_arr[..., c] * factor, 0, 255)

    out = Image.fromarray(img_arr.astype(np.uint8), mode="RGBA")
    out.save(BASEMAP_PNG)
    print(f"wrote {BASEMAP_PNG}")

    PUBLIC_BASEMAP.write_bytes(BASEMAP_PNG.read_bytes())
    print(f"wrote {PUBLIC_BASEMAP}")


if __name__ == "__main__":
    main()
