#!/usr/bin/env python
"""The Dask-tutorial card's ticking thumbnail (a card the director asked for).

"Parallelized Cloud Computing with Dask for Geoscientists" (Abrahams &
Rines, book.cryointhecloud.com/dask-for-geoscientists/) ends by compiling
Sentinel-2 tiles over the Oakland port terminals with sat-tile-stack and
plotting 25 August-2019 days — five of which carry imagery (the 5-day
revisit), the rest NaN. This re-runs THAT query (same centroid, bands,
pixel size, tile size, time range, mask — copied from the notebook's
"MAIN RUN BLOCK") and writes one square frame per day that has imagery:
the tutorial's stretched true-colour tile, its terminal mask outlined in
red, the date and the scene's cloud cover stamped in the corner.

Inputs (project copies, fetched by cinematic/scene_addl/fetch_sources.sh):
  cinematic/source_data/cryocloud/oakland_port_terminals.geojson
Network: Microsoft Planetary Computer STAC (anonymous, signed in place).

Outputs: cinematic/scene_addl/output_addl_cards/dask_oak_NN.jpg (720²)
  then  rsync -a --include='dask_oak_*.jpg' --exclude='*' cinematic/scene_addl/output_addl_cards/ website/.r2-cache/addl/cards/
        rclone copy website/.r2-cache/addl/cards r2:<bucket>/addl/cards --include 'dask_oak_*.jpg' --header-upload 'Cache-Control: public, max-age=31536000, immutable'
  (COPY, never sync: the mirror lacks the bed_prism source PNGs.)
Run:  nice -n 15 python cinematic/scene_addl/build_dask_card.py   (a Python env with sat_tile_stack + geopandas)
The card reads DASK_DAYS frames (SectionAdditionalWork.vue) — match it to
the count this prints.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import planetary_computer
import pystac_client
from PIL import Image, ImageDraw, ImageFont
from rasterio.features import rasterize
from sat_tile_stack import sattile_stack
from scipy.ndimage import binary_dilation, binary_erosion

ROOT = Path(__file__).resolve().parents[2]
MASK = ROOT / 'cinematic' / 'source_data' / 'cryocloud' / 'oakland_port_terminals.geojson'
OUT = ROOT / 'cinematic' / 'scene_addl' / 'output_addl_cards'

# The notebook's MAIN RUN BLOCK, verbatim values.
CENTROID = (-122.33, 37.81)
TIME_RANGE = '2019-08-01/2019-08-30'
BANDS = ['B04', 'B03', 'B02']  # the tutorial also pulls B08/B11; RGB is all the frame needs
PIX_RES = 10
TILE = 256
SIZE = 720
FONT = '/System/Library/Fonts/Menlo.ttc'


def linear_stretch_rgb(rgb: np.ndarray, pmin: float = 0, pmax: float = 98) -> np.ndarray:
    """The notebook's stretch: per band, pmin→0, pmax→1, clipped."""
    out = np.empty_like(rgb)
    for i in range(3):
        band = rgb[..., i]
        lo, hi = np.nanpercentile(band, (pmin, pmax))
        out[..., i] = np.clip((band - lo) / (hi - lo), 0, 1)
    return out


def main() -> None:
    assert MASK.is_file(), f'missing {MASK} — run cinematic/scene_addl/fetch_sources.sh'
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = pystac_client.Client.open(
        'https://planetarycomputer.microsoft.com/api/stac/v1',
        modifier=planetary_computer.sign_inplace,
    )
    print('connected to Microsoft Planetary Computer')
    gdf = gpd.read_file(MASK)
    ts = sattile_stack(catalog, CENTROID, BANDS, pix_res=PIX_RES, tile_size=TILE,
                       time_range=TIME_RANGE, normalize=True, mask=gdf, pull_to_mem=True)
    print('tilestack', dict(ts.sizes))
    # Today's sat-tile-stack returns a Dataset (`reflectance`, raw DN — the
    # stretch below scales it) and no longer appends the mask as a band, so
    # the terminal outline is rasterized here onto the tile's own grid.
    da = ts['reflectance']
    # NOT da.attrs['transform']: that (and `spec`) describe the pre-crop
    # search window (287 px here), while the tile is the 256 px cut around
    # the centroid — using it put the outline ~15 px (150 m) off (the first
    # bake). The tile's own x/y coords are the truth: pixel
    # centres, so the edge sits half a pixel out.
    from rasterio.transform import from_origin
    xs = np.asarray(da.x.values, dtype=float)
    ys = np.asarray(da.y.values, dtype=float)
    dx = float(xs[1] - xs[0])
    dy = float(ys[0] - ys[1])
    transform = from_origin(xs[0] - dx / 2, ys[0] + dy / 2, dx, dy)
    crs = da.attrs['crs']
    print('tile transform', transform, '| attrs transform origin', da.attrs['transform'].c, da.attrs['transform'].f)
    geoms = [g for g in gdf.to_crs(crs).geometry]
    mask_native = rasterize(geoms, out_shape=(da.sizes['y'], da.sizes['x']), transform=transform, fill=0, default_value=1, dtype='uint8') > 0
    print(f'mask covers {mask_native.mean()*100:.1f} % of the tile')

    times = pd.to_datetime(ts.time.values)
    pct_nan = np.asarray(ts.coords['pct_nans'].values, dtype=float)
    cloud = np.asarray(ts['eo_cloud_cover'].values, dtype=float) if 'eo_cloud_cover' in ts.coords else np.full(len(times), np.nan)
    font = ImageFont.truetype(FONT, 30)
    font_small = ImageFont.truetype(FONT, 24)

    n = 0
    for k, t in enumerate(times):
        if not np.isfinite(pct_nan[k]) or pct_nan[k] > 50:
            continue
        rgb = np.moveaxis(da.isel(time=k).values.astype(np.float32), 0, -1)  # (y, x, rgb)
        if np.isnan(rgb).mean() > 0.5:
            continue
        rgb = linear_stretch_rgb(rgb)
        rgb = np.nan_to_num(rgb, nan=0.0)
        im = Image.fromarray((rgb * 255).round().astype(np.uint8), 'RGB').resize((SIZE, SIZE), Image.LANCZOS)
        # The terminal mask's outline, as the notebook's red 0.5 contour.
        m = mask_native
        m = np.array(Image.fromarray(m.astype(np.uint8) * 255).resize((SIZE, SIZE), Image.NEAREST)) > 127
        edge = binary_dilation(m, iterations=2) & ~binary_erosion(m, iterations=2)
        px = np.array(im)
        px[edge] = (255, 36, 36)
        im = Image.fromarray(px)
        # Date + scene cloud cover, bottom-left, on a dark backing.
        d = ImageDraw.Draw(im, 'RGBA')
        date = t.strftime('%-d %b %Y')
        cl = f'cloud {cloud[k]:.0f} %' if np.isfinite(cloud[k]) else ''
        w1 = d.textlength(date, font=font)
        w2 = d.textlength(cl, font=font_small) if cl else 0
        box_w = int(max(w1, w2)) + 28
        box_h = 30 + 24 + 26 if cl else 30 + 22
        d.rectangle((16, SIZE - 16 - box_h, 16 + box_w, SIZE - 16), fill=(0, 0, 0, 150))
        d.text((30, SIZE - 16 - box_h + 8), date, font=font, fill=(244, 207, 106, 255))
        if cl:
            d.text((30, SIZE - 16 - box_h + 46), cl, font=font_small, fill=(244, 207, 106, 220))
        out = OUT / f'dask_oak_{n:02d}.jpg'
        im.save(out, 'JPEG', quality=88, optimize=True)
        print(f'  {out.name}: {date} · NaN {pct_nan[k]:.0f} % · cloud {cloud[k]:.0f} % · {out.stat().st_size/1024:.0f} KB')
        n += 1
    print(f'{n} frames — set DASK_DAYS = {n} in SectionAdditionalWork.vue')


if __name__ == '__main__':
    main()
