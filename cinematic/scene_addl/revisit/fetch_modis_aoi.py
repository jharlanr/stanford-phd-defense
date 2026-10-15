"""Daily MODIS surface reflectance over the Christoffersen 2018 area, one
array per day, straight from the gridded daily products (the record the
paper's lake volumes were mapped from is MODIS — Fitzpatrick et al. 2014).

  MOD09GQ / MYD09GQ  250 m  band 1 (red), band 2 (NIR)      → 125 m UTM grid
  MOD09GA / MYD09GA  500 m  bands 1, 3, 4 (red, blue, green) → 250 m UTM grid
                     1 km   state_1km (cloud flags)          → 250 m UTM grid

Nearest-neighbour onto UTM 22N at HALF the native pixel, so the product's
own pixels survive as blocks. Nothing is composited, filled or filtered.

Runs in a Python env with earthengine-api (Planetary Computer carries
only the 8-day MODIS composites). Resumable: a finished file is skipped.

  DEFENSE_SOURCE_DATA=… python fetch_modis_aoi.py 2010 terra
"""
from __future__ import annotations

import io
import sys
import time

import ee
import numpy as np

from common import AOI_DIR, AOI_X0, AOI_X1, AOI_Y0, AOI_Y1, EPSG, season_days

SAT = {'terra': ('MODIS/061/MOD09GQ', 'MODIS/061/MOD09GA'), 'aqua': ('MODIS/061/MYD09GQ', 'MODIS/061/MYD09GA')}
GQ_BANDS = ['sur_refl_b01', 'sur_refl_b02']
GA_BANDS = ['sur_refl_b01', 'sur_refl_b03', 'sur_refl_b04', 'state_1km']
CHUNK_DAYS = {'gq': 5, 'ga': 10}   # computePixels caps a request at 48 MB


def grid(res: float) -> dict:
    w = int(round((AOI_X1 - AOI_X0) / res))
    h = int(round((AOI_Y1 - AOI_Y0) / res))
    return {
        'dimensions': {'width': w, 'height': h},
        'affineTransform': {'scaleX': res, 'shearX': 0, 'translateX': AOI_X0, 'shearY': 0, 'scaleY': -res, 'translateY': AOI_Y1},
        'crsCode': f'EPSG:{EPSG}',
    }


def fetch(coll: str, bands: list[str], days: list[str], res: float) -> dict[str, np.ndarray]:
    """{day: (band, y, x) int32} for the days that have an image."""
    import datetime as dt
    d0 = days[0]
    d1 = (dt.date.fromisoformat(days[-1]) + dt.timedelta(days=1)).isoformat()
    ic = ee.ImageCollection(coll).filterDate(d0, d1).select(bands)
    img = ic.toBands().unmask(-32768, False).toInt32()
    for attempt in range(5):
        try:
            raw = ee.data.computePixels({'expression': img, 'fileFormat': 'NPY', 'grid': grid(res)})
            break
        except Exception as e:  # noqa: BLE001 — transient EE errors
            print('   retry', attempt, str(e)[:120], flush=True)
            time.sleep(10 * (attempt + 1))
    else:
        raise RuntimeError(f'{coll} {d0}')
    arr = np.load(io.BytesIO(raw))
    out: dict[str, list] = {}
    for name in arr.dtype.names or []:
        # '2010_06_06_sur_refl_b01' → day, band
        day = name[:10].replace('_', '-')
        out.setdefault(day, {})[name[11:]] = arr[name]
    return {d: np.stack([v[b] for b in bands]) for d, v in out.items() if all(b in v for b in bands)}


def main() -> None:
    year = int(sys.argv[1])
    sat = sys.argv[2]
    ee.Initialize()
    gq, ga = SAT[sat]
    days = season_days(year)
    AOI_DIR.mkdir(parents=True, exist_ok=True)
    for prod, coll, bands, res in (('gq', gq, GQ_BANDS, 125.0), ('ga', ga, GA_BANDS, 250.0)):
        out = AOI_DIR / f'modis_{sat}_{prod}_{year}.npz'
        if out.exists():
            print('have', out.name)
            continue
        got: dict[str, np.ndarray] = {}
        step = CHUNK_DAYS[prod]
        for i in range(0, len(days), step):
            chunk = days[i:i + step]
            t = time.time()
            got.update(fetch(coll, bands, chunk, res))
            print(f'  {sat} {prod} {chunk[0]}…{chunk[-1]}: {len(got)} days so far ({time.time() - t:.1f} s)', flush=True)
        ds = sorted(got)
        data = np.stack([got[d] for d in ds])
        dtype = np.int16 if prod == 'gq' else np.int32
        np.savez_compressed(
            out, days=np.array(ds), bands=np.array(bands), data=data.astype(dtype),
            x0=AOI_X0, y1=AOI_Y1, res=res, epsg=EPSG,
        )
        print('wrote', out.name, data.shape, f'{out.stat().st_size / 1e6:.0f} MB')


if __name__ == '__main__':
    main()
