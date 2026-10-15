"""Landsat 7 band 5 (1.65 µm, 30 m) for the scenes fetch_hires_2010.py
already holds — the cloud test over ice: wet snow and ice are nearly black
at 1.65 µm, cloud is bright. Without it a lake under cloud reads as "no
water" (7 June 2010 is mostly cloud here).

  DEFENSE_SOURCE_DATA=… python fetch_l7_swir.py      # a Python env with earthengine-api
     → stacks/hires_2010_b5/<id>.npz: days, b5 (day, 171, 171) TOA × 1e4
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor

import ee
import numpy as np

from common import STACK_DIR, WORK
from fetch_hires_2010 import L7, lake_grid, pixels

OUT = STACK_DIR / 'hires_2010_b5'


def one(lake: dict) -> str:
    out = OUT / f"{lake['id']}.npz"
    if out.exists():
        return f"{lake['id']} have"
    z = np.load(STACK_DIR / 'hires_2010' / f"{lake['id']}.npz")
    days = [str(d) for d in z['l7_days']]
    g = lake_grid(lake['utm_e'], lake['utm_n'])
    g['dimensions'] = {'width': 171, 'height': 171}
    g['affineTransform']['scaleX'] = 30.0
    g['affineTransform']['scaleY'] = -30.0
    pt = ee.Geometry.Point([lake['lon'], lake['lat']]).buffer(2600).bounds()
    ic = ee.ImageCollection(L7[0]).merge(ee.ImageCollection(L7[1])).filterBounds(pt).filterDate('2010-05-01', '2010-10-01')
    cat = ee.Image.cat([
        ic.filter(ee.Filter.eq('DATE_ACQUIRED', d)).mosaic().select('B5').multiply(1e4).unmask(0).toInt16().rename(f"d{d.replace('-', '')}")
        for d in days
    ])
    arr = pixels(cat, g)
    np.savez_compressed(out, days=np.array(days), b5=np.stack([arr[f"d{d.replace('-', '')}"] for d in days]).astype(np.int16))
    return f"{lake['id']}: {len(days)} days"


def main() -> None:
    ee.Initialize()
    OUT.mkdir(parents=True, exist_ok=True)
    lakes = json.loads((WORK / 'c18_lakes.json').read_text())['lakes']
    t = time.time()
    with ThreadPoolExecutor(4) as ex:
        for msg in ex.map(one, lakes):
            print(msg, f'({time.time() - t:.0f} s)', flush=True)


if __name__ == '__main__':
    main()
