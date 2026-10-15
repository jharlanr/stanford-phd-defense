"""Sentinel-2 L2A over each lake's tile for the 2019 season, display grade.

The same product sat-tile-stack reads (ESA L2A; Planetary Computer's
`sentinel-2-l2a` = Earth Engine's `COPERNICUS/S2_SR_HARMONIZED`), on the
same 512 × 512, 10 m, UTM 22N tile — but fetched as 8-bit reflectance
(DN / 40, so one step = 0.004) + the scene classification, one mosaic per
day. sat-tile-stack's full 7-band, 16-bit stacks cost > 1 GB of download per
lake on this connection (~7 h for the 82); this is ~90 MB per lake.
`C18_001` exists both ways and the two agree (the check is in the README).

One .npz per lake in stacks/s2_2019_gee/: days, rgb (day, [B4, B3, B2], y, x)
uint8, scl (day, y, x) uint8. A day absent from `days` has no acquisition.

  DEFENSE_SOURCE_DATA=… python fetch_s2_2019.py [ids…]      # a Python env with earthengine-api
"""
from __future__ import annotations

import io
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import ee
import numpy as np

from common import EPSG, STACK_DIR, TILE_M, WORK

RES = 10.0
N = 512
OUT = STACK_DIR / 's2_2019_gee'
BANDS = ['B4', 'B3', 'B2']
CHUNK = 20      # computePixels caps a request at 48 MB (it counts 2 bytes a pixel)


def pixels(img: ee.Image, grid: dict) -> np.ndarray:
    for attempt in range(6):
        try:
            return np.load(io.BytesIO(ee.data.computePixels({'expression': img, 'fileFormat': 'NPY', 'grid': grid})))
        except Exception as e:  # noqa: BLE001
            if attempt == 5:
                raise
            print('   retry', str(e)[:100], flush=True)
            time.sleep(4 * (attempt + 1))
    raise RuntimeError


def one(lake: dict) -> str:
    out = OUT / f"{lake['id']}.npz"
    if out.exists():
        return f"{lake['id']} have"
    x0, y1 = lake['utm_e'] - TILE_M / 2, lake['utm_n'] + TILE_M / 2
    grid = {
        'dimensions': {'width': N, 'height': N},
        'affineTransform': {'scaleX': RES, 'shearX': 0, 'translateX': x0, 'shearY': 0, 'scaleY': -RES, 'translateY': y1},
        'crsCode': f'EPSG:{EPSG}',
    }
    box = ee.Geometry.Rectangle([x0, y1 - TILE_M, x0 + TILE_M, y1], f'EPSG:{EPSG}', False)
    ic = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(box).filterDate('2019-05-01', '2019-10-01')
    stamps = ic.aggregate_array('system:time_start').getInfo()
    dates = sorted({time.strftime('%Y-%m-%d', time.gmtime(t / 1000)) for t in stamps})
    days, rgb, scl = [], [], []
    for k in range(0, len(dates), CHUNK):
        part = dates[k:k + CHUNK]
        imgs = []
        for d in part:
            nxt = time.strftime('%Y-%m-%d', time.gmtime(time.mktime(time.strptime(d, '%Y-%m-%d')) + 86400 + 43200))
            m = ic.filterDate(d, nxt).mosaic()
            tag = d.replace('-', '')
            imgs.append(m.select(BANDS).divide(40).round().clamp(0, 255).unmask(0).toUint8().rename([f'd{tag}_{b}' for b in BANDS]))
            imgs.append(m.select('SCL').unmask(0).toUint8().rename(f'd{tag}_SCL'))
        arr = pixels(ee.Image.cat(imgs), grid)
        for d in part:
            tag = d.replace('-', '')
            a = np.stack([arr[f'd{tag}_{b}'] for b in BANDS])
            if (a.max(axis=0) > 0).mean() < 0.02:
                continue      # the day's granules miss the tile
            days.append(d); rgb.append(a); scl.append(arr[f'd{tag}_SCL'])
    np.savez_compressed(out, days=np.array(days), rgb=np.stack(rgb) if rgb else np.zeros((0, 3, N, N), np.uint8),
                        scl=np.stack(scl) if scl else np.zeros((0, N, N), np.uint8), x0=x0, y1=y1, res=RES, epsg=EPSG)
    return f"{lake['id']}: Sentinel-2 on {len(days)} days ({len(dates)} dates searched)"


def main() -> None:
    ee.Initialize()
    OUT.mkdir(parents=True, exist_ok=True)
    lakes = json.loads((WORK / 'c18_lakes.json').read_text())['lakes']
    ids = sys.argv[1:]
    if ids:
        lakes = [lk for lk in lakes if lk['id'] in ids]
    t = time.time()
    with ThreadPoolExecutor(5) as ex:
        for msg in ex.map(one, lakes):
            print(msg, f'({time.time() - t:.0f} s)', flush=True)


if __name__ == '__main__':
    main()
