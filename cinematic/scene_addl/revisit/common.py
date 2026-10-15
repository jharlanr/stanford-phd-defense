"""Shared constants for the "revisiting lake drainage papers" pipeline
(Christoffersen et al. 2018, Nat. Commun. 9:1064 — the 6–10 June 2010 cascade).

Everything is on ONE grid family: UTM 22N (EPSG:32622), the frame the paper's
model grid was registered to in scene_01_intro/build_coupling_length.py
(model (x, y) km → UTM (523.25 + x, 7404.0 + y) km, translation only).

Source data never lives in the repo: the gitignored cinematic/source_data/
of the MAIN checkout (set DEFENSE_SOURCE_DATA when running from a worktree).
"""
from __future__ import annotations

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
CINEMATIC = HERE.parents[1]
SOURCE_DATA = Path(os.environ.get('DEFENSE_SOURCE_DATA', CINEMATIC / 'source_data'))
WORK = SOURCE_DATA / 'revisit'          # everything this pipeline writes
AOI_DIR = WORK / 'aoi'                  # area-wide rasters (MODIS daily, Landsat scenes)
STACK_DIR = WORK / 'stacks'             # per-lake sat-tile-stack NetCDFs
MOVIE_DIR = WORK / 'movies'             # per-lake mp4 + sidecars + thumbs (→ R2)
DIGI_DIR = WORK / 'digitise'            # figure rasters + digitised dots
C18_PDF = SOURCE_DATA / 'coupling' / 'christoffersen2018.pdf'

EPSG = 32622
# Christoffersen's CISM domain, 120 × 75 km, in UTM 22N km.
C18_UTM0 = (523.25, 7404.0)
C18_DOMAIN_KM = (120.0, 75.0)
# The area every AOI raster covers: the domain + a 5 km margin (UTM 22N, m).
AOI_X0, AOI_X1 = 518_000.0, 648_000.0
AOI_Y0, AOI_Y1 = 7_399_000.0, 7_484_000.0

SEASONS = {2010: ('2010-05-01', '2010-09-30'), 2019: ('2019-05-01', '2019-09-30')}
TILE_M = 5120.0     # the ESSD stacks' footprint: 512 px at 10 m


def season_days(year: int) -> list[str]:
    import datetime as dt
    a, b = (dt.date.fromisoformat(s) for s in SEASONS[year])
    return [(a + dt.timedelta(days=i)).isoformat() for i in range((b - a).days + 1)]
