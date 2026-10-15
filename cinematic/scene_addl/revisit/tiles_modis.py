"""Cut each lake's 5.12 km tile out of the daily MODIS AOI arrays, for both
seasons. One frame per day; of Terra and Aqua the pass with less flagged
cloud over the tile is kept (Terra on a tie), and which one is recorded.

MODIS always has an observation at 67°N in summer, so these tiles are never
blank — a cloudy day shows the cloud.

  cinematic/.venv/bin/python tiles_modis.py     → stacks/modis_<year>/<id>.npz
"""
from __future__ import annotations

import json

import numpy as np

import modis
from common import SEASONS, STACK_DIR, TILE_M, WORK, season_days

WATER_R_M = 1250.0     # "water near the lake": within this of the tile centre
NDWI_MIN = 0.3


def main() -> None:
    lakes = json.loads((WORK / 'c18_lakes.json').read_text())['lakes']
    for year in SEASONS:
        out_dir = STACK_DIR / f'modis_{year}'
        out_dir.mkdir(parents=True, exist_ok=True)
        x0, y1, res = modis.grid('terra', year)
        days = season_days(year)
        n = int(round(TILE_M / res))          # 41 samples of 125 m
        frames = {lk['id']: np.zeros((len(days), n, n, 3), np.uint8) for lk in lakes}
        sat = {lk['id']: [''] * len(days) for lk in lakes}
        cloud = {lk['id']: [None] * len(days) for lk in lakes}
        water = {lk['id']: [None] * len(days) for lk in lakes}
        win = {}
        for lk in lakes:
            c0 = int(round((lk['utm_e'] - TILE_M / 2 - x0) / res))
            r0 = int(round((y1 - (lk['utm_n'] + TILE_M / 2)) / res))
            win[lk['id']] = (r0, c0)
        yy, xx = np.mgrid[0:n, 0:n]
        near = np.hypot((xx + 0.5) * res - TILE_M / 2, (yy + 0.5) * res - TILE_M / 2) <= WATER_R_M
        for di, day in enumerate(days):
            passes = {}
            for s in ('terra', 'aqua'):
                arr = modis.day_arrays(s, year, day)
                if arr is not None:
                    passes[s] = arr
            for lk in lakes:
                r0, c0 = win[lk['id']]
                sl = (slice(r0, r0 + n), slice(c0, c0 + n))
                best = None
                for s, (red, green, blue, cl, valid) in passes.items():
                    v = float(valid[sl].mean())
                    if v < 0.5:
                        continue
                    score = (float(cl[sl].mean()), 0 if s == 'terra' else 1)
                    if best is None or score < best[0]:
                        best = (score, s, red[sl], green[sl], blue[sl], valid[sl])
                if best is None:
                    continue
                (cf, _), s, r, g, b, v = best
                rgb = np.stack([r, g, b], axis=-1)
                rgb = np.where(v[..., None] & np.isfinite(rgb), rgb, 0.0)
                frames[lk['id']][di] = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
                sat[lk['id']][di] = 'T' if s == 'terra' else 'Q'
                cloud[lk['id']][di] = round(cf * 100)
                with np.errstate(invalid='ignore', divide='ignore'):
                    ndwi = (b - r) / (b + r)
                wet = np.isfinite(ndwi) & (ndwi > NDWI_MIN) & near
                water[lk['id']][di] = round(float(wet.sum()) * res * res / 1e6, 3)
            if di % 30 == 0:
                print(year, day, flush=True)
        for lk in lakes:
            i = lk['id']
            np.savez_compressed(out_dir / f'{i}.npz', frames=frames[i], sat=np.array(sat[i]), days=np.array(days),
                                cloud=np.array([-1 if c is None else c for c in cloud[i]]),
                                water=np.array([np.nan if w is None else w for w in water[i]]))
        print('wrote', len(lakes), 'MODIS tiles for', year)


if __name__ == '__main__':
    main()
