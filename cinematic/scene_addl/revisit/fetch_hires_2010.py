"""The 2010 imagery that is FINER than MODIS, per lake: every Landsat 7 ETM+
scene (30 m colour + the 15 m panchromatic band; scan-line-corrector gaps
left as they are) and every ASTER scene (15 m green / red / near-infrared)
of the 2010 season that touches the lake's 5.1 km tile.

Sentinel-2 did not exist in 2010 (launched 2015); Landsat 5 has no scenes
here that summer. Planetary Computer holds no Landsat panchromatic band and
no ASTER over this area, so this one comes from Earth Engine (a Python env with earthengine-api);
the 2019 Sentinel-2 stacks are sat-tile-stack's.

One .npz per lake in stacks/hires_2010/, on a 15 m UTM 22N grid whose origin
is a multiple of 30 m (so a Landsat 30 m pixel is exactly 2 × 2 cells):
  l7_days, l7 (day, [B1 blue, B2 green, B3 red, B8 pan], y, x) TOA reflectance × 1e4, 0 = no data
  aster_days, aster (day, [B01 green, B02 red, B3N nir], y, x) DN, + the gains and sun elevation

  DEFENSE_SOURCE_DATA=… python fetch_hires_2010.py      # a Python env with earthengine-api
"""
from __future__ import annotations

import io
import json
import time
from concurrent.futures import ThreadPoolExecutor

import ee
import numpy as np

from common import EPSG, SEASONS, STACK_DIR, WORK

RES = 15.0
N = 342                      # 5130 m
OUT = STACK_DIR / 'hires_2010'
L7 = ['LANDSAT/LE07/C02/T1_TOA', 'LANDSAT/LE07/C02/T2_TOA']
L7_BANDS = ['B1', 'B2', 'B3', 'B8']
AST_BANDS = ['B01', 'B02', 'B3N']


def lake_grid(e: float, n: float) -> dict:
    x0 = round((e - N * RES / 2) / 30.0) * 30.0
    y1 = round((n + N * RES / 2) / 30.0) * 30.0
    return {
        'dimensions': {'width': N, 'height': N},
        'affineTransform': {'scaleX': RES, 'shearX': 0, 'translateX': x0, 'shearY': 0, 'scaleY': -RES, 'translateY': y1},
        'crsCode': f'EPSG:{EPSG}',
    }


def pixels(img: ee.Image, grid: dict) -> np.ndarray:
    for attempt in range(6):
        try:
            raw = ee.data.computePixels({'expression': img, 'fileFormat': 'NPY', 'grid': grid})
            return np.load(io.BytesIO(raw))
        except Exception as e:  # noqa: BLE001
            if attempt == 5:
                raise
            time.sleep(4 * (attempt + 1))
            print('   retry', str(e)[:100], flush=True)
    raise RuntimeError


def one(lake: dict) -> str:
    out = OUT / f"{lake['id']}.npz"
    if out.exists():
        return f"{lake['id']} have"
    pt = ee.Geometry.Point([lake['lon'], lake['lat']]).buffer(2600).bounds()
    d0, d1 = SEASONS[2010]
    d1x = '2010-10-01'
    grid = lake_grid(lake['utm_e'], lake['utm_n'])
    save: dict = {'x0': grid['affineTransform']['translateX'], 'y1': grid['affineTransform']['translateY'], 'res': RES, 'epsg': EPSG}

    # ── Landsat 7 ──
    ic = ee.ImageCollection(L7[0]).merge(ee.ImageCollection(L7[1])).filterBounds(pt).filterDate(d0, d1x)
    dates = sorted(set(ic.aggregate_array('DATE_ACQUIRED').getInfo()))
    l7_days, l7 = [], []
    if dates:
        cat = ee.Image.cat([
            ic.filter(ee.Filter.eq('DATE_ACQUIRED', d)).mosaic().select(L7_BANDS).multiply(1e4).unmask(0).toInt16()
              .rename([f"d{d.replace('-', '')}_{b}" for b in L7_BANDS])
            for d in dates
        ])
        arr = pixels(cat, grid)
        for d in dates:
            a = np.stack([arr[f"d{d.replace('-', '')}_{b}"] for b in L7_BANDS])
            if (a[3] > 0).mean() > 0.02 or (a[2] > 0).mean() > 0.02:      # the scene really covers the tile
                l7_days.append(d); l7.append(a)
    save['l7_days'] = np.array(l7_days)
    save['l7'] = np.stack(l7).astype(np.int16) if l7 else np.zeros((0, 4, N, N), np.int16)

    # ── ASTER ──
    ac = ee.ImageCollection('ASTER/AST_L1T_003').filterBounds(pt).filterDate(d0, d1x)
    info = ac.select([]).getInfo()['features'] if ac.size().getInfo() else []
    meta = {}
    for f in info:
        p = f['properties']
        if 'GAIN_COEFFICIENT_B01' not in p or 'GAIN_COEFFICIENT_B3N' not in p:
            continue     # a scene without the visible / near-infrared telescope
        day = time.strftime('%Y-%m-%d', time.gmtime(p['system:time_start'] / 1000))
        meta.setdefault(day, {'ids': [], 'gain': [p['GAIN_COEFFICIENT_B01'], p['GAIN_COEFFICIENT_B02'], p['GAIN_COEFFICIENT_B3N']],
                              'sun_elev': p.get('SOLAR_ELEVATION')})['ids'].append(f['id'])
    a_days, a_arr = [], []
    if meta:
        cat = ee.Image.cat([
            ee.ImageCollection([ee.Image(i).select(AST_BANDS) for i in m['ids']]).mosaic().unmask(0).toInt16()
              .rename([f"d{d.replace('-', '')}_{b}" for b in AST_BANDS])
            for d, m in sorted(meta.items())
        ])
        arr = pixels(cat, grid)
        for d in sorted(meta):
            a = np.stack([arr[f"d{d.replace('-', '')}_{b}"] for b in AST_BANDS])
            if (a[0] > 0).mean() > 0.02:
                a_days.append(d); a_arr.append(a)
    save['aster_days'] = np.array(a_days)
    save['aster'] = np.stack(a_arr).astype(np.uint8) if a_arr else np.zeros((0, 3, N, N), np.uint8)
    save['aster_meta'] = json.dumps({d: {'gain': meta[d]['gain'], 'sun_elev': meta[d]['sun_elev']} for d in a_days})
    np.savez_compressed(out, **save)
    return f"{lake['id']}: Landsat 7 on {len(l7_days)} days, ASTER on {len(a_days)} days"


def main() -> None:
    ee.Initialize()
    OUT.mkdir(parents=True, exist_ok=True)
    lakes = json.loads((WORK / 'c18_lakes.json').read_text())['lakes']
    t = time.time()
    with ThreadPoolExecutor(5) as ex:
        for msg in ex.map(one, lakes):
            print(msg, f'({time.time() - t:.0f} s)', flush=True)


if __name__ == '__main__':
    main()
