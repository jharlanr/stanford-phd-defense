"""
Fetch a monthly time series of Greenland ice-surface SPEED for the
Introduction's "the ice speeds up every summer" beat.

SOURCE (primary)
    NASA MEaSUREs Greenland Monthly Ice Sheet Velocity Mosaics from SAR and
    Landsat, NSIDC-0731, Version 5 (Joughin, 2023). Monthly, 200 m native,
    whole ice sheet, 1 Dec 2014 - 30 Nov 2024, EPSG:3413.
    DOI 10.5067/EGKZX6FXXM4P
    Citation (dataset):
        Joughin, I. (2023). MEaSUREs Greenland Monthly Ice Sheet Velocity
        Mosaics from SAR and Landsat. (NSIDC-0731, Version 5). Boulder,
        Colorado USA. NASA National Snow and Ice Data Center Distributed
        Active Archive Center. https://doi.org/10.5067/EGKZX6FXXM4P
    Citation (method):
        Joughin, I., Smith, B. E., & Howat, I. (2018). Greenland Ice Mapping
        Project: ice flow velocity variation at sub-monthly to decadal
        timescales. The Cryosphere, 12, 2211-2227.
        https://doi.org/10.5194/tc-12-2211-2018
    Licence: NASA EOSDIS data -- no restrictions on use; cite the dataset
    (NSIDC "Use and Copyright": free, open, cite per the citation policy).
    Needs a (free) NASA Earthdata Login: read from ~/.netrc
    (machine urs.earthdata.nasa.gov). Nothing is printed from it.

HOW (cheap on disk)
    The `_vv_` (speed, m/yr) GeoTIFFs are Cloud-Optimized with internal
    overviews (200 m -> 400, 800, 1600 ... m). GDAL /vsicurl/ range-reads
    ONLY the requested overview, so a whole-ice-sheet month at 800 m costs
    a few MB instead of the ~200 MB full-res file. We also fetch a
    central-west (the thesis's study region) window at 400 m for the regional
    zoom and the curves.

    Granule URLs come from NASA CMR (no hard-coded end-of-month days).

OUTPUTS (gitignored; cinematic/source_data/velocity_series/)
    nsidc0731_v5/gl_800m/vv_YYYYMM.tif     whole sheet, 800 m, float32, nodata -1
    nsidc0731_v5/cw_400m/vv_YYYYMM.tif     central-west window, 400 m
    nsidc0731_v5/granules.json             CMR titles + URLs + time spans

Run (re-runnable; skips files already on disk):
    cd cinematic
    nice -n 15 python \
        scene_01_intro/fetch_velocity_series.py [--start 2014-12] [--end 2024-11]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CINEMATIC_DIR = HERE.parent
OUT_ROOT = CINEMATIC_DIR / "source_data" / "velocity_series" / "nsidc0731_v5"

COLLECTION = "NSIDC-0731"
VERSION = "5"
CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"

# Overview levels in the COGs: 0 -> 400 m, 1 -> 800 m (200 m native).
GL_OVERVIEW = 1          # whole sheet, 800 m
CW_OVERVIEW = 0          # central-west window, 400 m
# Central-west window in EPSG:3413 (m): ~66-72.5 N, coast to ~45 W: Jakobshavn to the
# Russell / Isunnguata Sermia land-terminating sector and ~200 km inland.
CW_BOUNDS = (-380_000.0, -2_620_000.0, 20_000.0, -1_900_000.0)   # xmin, ymin, xmax, ymax


def gdal_env() -> dict:
    cookie = str(OUT_ROOT / ".urs_cookies.txt")
    return dict(
        GDAL_HTTP_NETRC="YES",
        GDAL_HTTP_COOKIEFILE=cookie,
        GDAL_HTTP_COOKIEJAR=cookie,
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
        GDAL_HTTP_MAX_RETRY="4",
        GDAL_HTTP_RETRY_DELAY="3",
        VSI_CACHE="TRUE",
    )


def cmr_granules(start: str, end: str) -> list[dict]:
    """All '*_velocity_v05.0' granules between start and end (YYYY-MM)."""
    out, page = [], 1
    t0 = f"{start}-01T00:00:00Z"
    y, m = map(int, end.split("-"))
    t1 = f"{y + (m == 12)}-{(m % 12) + 1:02d}-01T00:00:00Z"
    while True:
        q = (f"{CMR}?short_name={COLLECTION}&version={VERSION}&page_size=200"
             f"&page_num={page}&temporal={t0},{t1}&sort_key=start_date")
        with urllib.request.urlopen(q, timeout=60) as r:
            entries = json.load(r)["feed"]["entry"]
        if not entries:
            break
        for e in entries:
            if not e["title"].endswith("_velocity_v05.0"):
                continue
            vv = [l["href"] for l in e["links"]
                  if l["href"].startswith("https") and l["href"].endswith("_vv_v05.0.tif")]
            if vv:
                out.append(dict(title=e["title"], start=e["time_start"],
                                end=e["time_end"], vv_url=vv[0]))
        page += 1
    # keep only granules that START inside [start, end] (CMR returns overlaps)
    out = [g for g in out if start <= g["start"][:7] <= end]
    return sorted(out, key=lambda g: g["start"])


def fetch_one(url: str, dst: Path, overview: int, bounds=None) -> dict:
    import numpy as np
    import rasterio
    from rasterio.windows import from_bounds

    with rasterio.open("/vsicurl/" + url, overview_level=overview) as src:
        if bounds is None:
            win = None
            transform = src.transform
            data = src.read(1)
        else:
            win = from_bounds(*bounds, transform=src.transform).round_offsets().round_lengths()
            data = src.read(1, window=win, boundless=True, fill_value=-1)
            transform = src.window_transform(win)
        profile = dict(driver="GTiff", height=data.shape[0], width=data.shape[1],
                       count=1, dtype="float32", crs=src.crs, transform=transform,
                       nodata=-1.0, compress="deflate", predictor=3, tiled=True,
                       blockxsize=256, blockysize=256)
    tmp = dst.with_suffix(".part.tif")
    with rasterio.open(tmp, "w", **profile) as d:
        d.write(data.astype("float32"), 1)
    tmp.rename(dst)
    valid = float(np.mean(data > 0))
    return dict(shape=list(data.shape), valid_frac=valid)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2014-12")
    ap.add_argument("--end", default="2024-11")
    ap.add_argument("--no-cw", action="store_true")
    args = ap.parse_args()

    os.environ.update(gdal_env())
    (OUT_ROOT / "gl_800m").mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "cw_400m").mkdir(parents=True, exist_ok=True)

    grans = cmr_granules(args.start, args.end)
    print(f"{len(grans)} monthly granules {args.start} .. {args.end}")
    (OUT_ROOT / "granules.json").write_text(json.dumps(grans, indent=1))

    for g in grans:
        ym = g["start"][:4] + g["start"][5:7]
        jobs = [(OUT_ROOT / "gl_800m" / f"vv_{ym}.tif", GL_OVERVIEW, None)]
        if not args.no_cw:
            jobs.append((OUT_ROOT / "cw_400m" / f"vv_{ym}.tif", CW_OVERVIEW, CW_BOUNDS))
        for dst, ov, bnds in jobs:
            if dst.exists():
                continue
            for attempt in range(3):
                try:
                    t = time.time()
                    info = fetch_one(g["vv_url"], dst, ov, bnds)
                    print(f"  {dst.parent.name}/{dst.name}  {info['shape']}  valid "
                          f"{info['valid_frac']:.3f}  {dst.stat().st_size / 1e6:.1f} MB  "
                          f"{time.time() - t:.0f}s", flush=True)
                    break
                except Exception as exc:  # noqa: BLE001
                    print(f"  retry {attempt + 1} {dst.name}: {exc}", file=sys.stderr)
                    time.sleep(5)


if __name__ == "__main__":
    main()
