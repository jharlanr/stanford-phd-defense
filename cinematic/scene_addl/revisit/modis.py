"""Read the daily MODIS AOI arrays written by fetch_modis_aoi.py and turn a
day into a true-colour picture at 250 m.

Bands 1 (red, 250 m), 4 (green, 500 m), 3 (blue, 500 m); green and blue are
sharpened by the 250 m / 500 m red ratio (the standard MODIS 250 m true
colour). Reflectance 0…1 maps linearly to 0…255, the same rule as the site's
Sentinel-2 lake movies — no per-frame stretch.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from common import AOI_DIR

FILL_GQ = -28672


@lru_cache(maxsize=8)
def _load(sat: str, prod: str, year: int):
    z = np.load(AOI_DIR / f'modis_{sat}_{prod}_{year}.npz')
    return {'days': [str(d) for d in z['days']], 'data': z['data'], 'x0': float(z['x0']), 'y1': float(z['y1']), 'res': float(z['res'])}


def days(sat: str, year: int) -> list[str]:
    return _load(sat, 'gq', year)['days']


def day_arrays(sat: str, year: int, day: str):
    """(red250, green, blue, cloud, valid) on the 125 m grid, reflectance
    0…1 (NaN where the product has no observation); cloud = the MOD09
    state flag (cloudy or mixed), valid = has a 250 m observation."""
    gq = _load(sat, 'gq', year)
    ga = _load(sat, 'ga', year)
    if day not in gq['days'] or day not in ga['days']:
        return None
    q = gq['data'][gq['days'].index(day)].astype(np.float32)        # (2, H, W) at 125 m
    a = ga['data'][ga['days'].index(day)]                           # (4, h, w) at 250 m
    up = lambda v: np.repeat(np.repeat(v, 2, axis=0), 2, axis=1)    # noqa: E731 — 250 → 125 m, blocks kept
    red = np.where(q[0] <= -100, np.nan, q[0] * 1e-4)
    r5 = up(a[0].astype(np.float32)); g5 = up(a[2].astype(np.float32)); b5 = up(a[1].astype(np.float32))
    bad5 = (r5 <= -100) | (g5 <= -100) | (b5 <= -100)
    r5, g5, b5 = r5 * 1e-4, g5 * 1e-4, b5 * 1e-4
    ratio = np.where(r5 > 0.02, red / np.maximum(r5, 0.02), 1.0)
    green = np.where(bad5, np.nan, g5 * ratio)
    blue = np.where(bad5, np.nan, b5 * ratio)
    state = up(a[3].astype(np.int64))
    state = np.where(state < 0, 0, state)
    cloud = ((state & 0b11) == 1) | ((state & 0b11) == 2)
    valid = np.isfinite(red)
    return red, green, blue, cloud, valid


def rgb(sat: str, year: int, day: str) -> np.ndarray | None:
    """uint8 (H, W, 3) true colour; black where there is no observation."""
    arr = day_arrays(sat, year, day)
    if arr is None:
        return None
    red, green, blue, _, valid = arr
    out = np.stack([red, green, blue], axis=-1)
    out = np.where(valid[..., None] & np.isfinite(out), out, 0.0)
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


def grid(sat: str = 'terra', year: int = 2010):
    g = _load(sat, 'gq', year)
    return g['x0'], g['y1'], g['res']
