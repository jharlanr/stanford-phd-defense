"""
Chapter 2's CENTRE-LAKES INSET (the director asked for a small zoom-in
map covering the seven centre lakes, so the one being looked at can be
highlighted) — the stage only: BedMachine v6's ice
margin, ice-free land and sea around the seven PNAS centre lakes, in a
local azimuthal-equidistant frame (km, north up), plus each lake's
position in that frame. The page (Ch2CenterLakesMap.vue) draws the
markers; nothing here is a picture.

The BedMachine layers are the Conclusion's (build_conclusion_visual.
bedmachine_layers, imported, not copied) on a window sized to the seven
lakes; surface contours are dropped (the inset is ~240 px).

Inputs:
  website/.r2-cache/ch02/sim/sim_domains.json   (the seven centre lakes)
  cinematic/source_data/data/BedMachineGreenland-v6.nc

Run (a Python env with pyproj, shapely, contourpy, scipy, xarray — cinematic/requirements.txt):
  nice -n 15 python -u \
      cinematic/scene_ch02/build_center_lakes_inset.py
Then (new bytes = new name):
  rclone copy cinematic/data/ch02_inset r2:<bucket>/ch02/inset \
      --header-upload 'Cache-Control: public, max-age=31536000, immutable'
  mkdir -p website/.r2-cache/ch02/inset && cp cinematic/data/ch02_inset/* website/.r2-cache/ch02/inset/
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scene_conclusion"))
import build_conclusion_visual as bcv  # noqa: E402

REPO = HERE.parents[1]
DOMAINS = REPO / "website" / ".r2-cache" / "ch02" / "sim" / "sim_domains.json"
OUT = REPO / "cinematic" / "data" / "ch02_inset" / "centerlakes_v1.json"

PAD_KM = 26.0  # room around the outermost lakes (and their glyphs)


def main() -> None:
    lakes = json.loads(DOMAINS.read_text())["lakes"]
    lon = np.array([lk["lon"] for lk in lakes])
    lat = np.array([lk["lat"] for lk in lakes])
    lon0, lat0 = float(lon.mean()), float(lat.mean())
    tr = bcv.local_transformer(lon0, lat0)
    x, y = tr.transform(lon, lat)
    half_x = float(np.abs(x).max()) + PAD_KM
    half_y = float(np.abs(y).max()) + PAD_KM
    # a window at least 3:4 so the coast reads beside the column of lakes
    half_x = max(half_x, 0.75 * half_y)
    bcv.HALF_X, bcv.HALF_Y = half_x, half_y
    layers = bcv.bedmachine_layers(tr, lon0, lat0)
    out = {
        "about": "Ch.2 centre-lakes inset · BedMachine v6 margin/land/sea · build_center_lakes_inset.py",
        "frame": {"proj": "aeqd", "lon0": lon0, "lat0": lat0, "units": "km", "q": bcv.Q,
                  "half_x": round(half_x, 2), "half_y": round(half_y, 2)},
        "lakes": [{"id": lk["id"], "num": int(lk["id"].split("_")[1]),
                   "x": round(float(xi), 2), "y": round(float(yi), 2)}
                  for lk, xi, yi in zip(lakes, x, y)],
        "margin": layers["margin"],
        "land": layers["land"],
        "sea": layers["sea"],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.1f} kB): window ±{half_x:.0f} × ±{half_y:.0f} km, "
          f"{len(out['margin'])} margin lines, {len(out['land'])} land / {len(out['sea'])} sea polygons")
    for lk in out["lakes"]:
        print(f"  {lk['num']}  x {lk['x']:7.2f}  y {lk['y']:7.2f}")


if __name__ == "__main__":
    main()
