# Revisiting lake drainage papers — Christoffersen et al. 2018

The pipeline behind `/additional-work/revisit`: every lake Christoffersen et
al. 2018 (Nat. Commun. 9:1064) drained to the bed in the 6–10 June 2010
cascade, with its season of imagery in 2010 (MODIS; Landsat 7 + ASTER) and in
2019 (MODIS; Sentinel-2).

The director's question: did the paper drain too many lakes to the bed —
drainages that are aliased in the MODIS record and were not hydrofracture
events — so that its tensile shock is partly an artefact and its overlap with
the drainages a correlation?

## Where the lakes come from

The paper publishes no lake table. Its inputs are "available on request";
Fitzpatrick et al. 2014 (the MODIS record it uses: 156 lakes, 663 drainage
events in 2010) has no data supplement; no repository deposit was found
(checked at the time of writing: the TC page, the Nature Communications page via PMC,
PANGAEA / Zenodo / Apollo searches). So the lakes are **digitised from the
paper's Figs. 3 and 4** (`digitise_c18.py`, `build_lakes.py`):

- every map panel is a 300-ppi raster in the PDF; each lake is a disc with a
  white rim. A disc is recovered as a circle fitted to its visible rim, with
  the constraint that the visible part lies inside it (so a half-hidden disc
  still gets its true centre);
- each day's drained lakes are drawn in THREE panels (Fig. 3 twice, Fig. 4
  once). The two Fig. 3 panels agree to 0.07 km (median) and 0.2 km (max);
- the positions sit on the **model's 1 km grid** (fractional parts
  concentrate to ±0.05 km), so each lake is a grid cell: the true lake centre
  is within ~0.5 km;
- registration: model (x, y) km → UTM 22N (523.25 + x, 7404.0 + y) km, the
  ice-margin fit from `scene_01_intro/build_coupling_length.py`. Checked
  against the real lakes in MODIS of 5 and 6 June 2010 (Terra and Aqua): the
  best shift is within one 125 m sample of zero.

Counts against the captions: 6 June 43 / 43, 7 June 29 / 30, 8–10 June
51 / 51 drained; 55 / 59 present on 5 June; unchanged 15 / 16, 15 / 16, 9 / 10.
The one 7 June drainage that could not be read is hidden under another disc
in all three of its panels (candidates: C18_058, C18_060, C18_064, C18_079 —
lakes drained on 6 June that sit under a 7 June disc). Tracking the cells
across the four days gives **82 lakes, 73 drained at least once, 123 drainage
events** (the paper's own arithmetic gives 85 lakes).

## Imagery

| season | track | source | how |
| --- | --- | --- | --- |
| 2010 | `modis` | MOD09GQ/GA + MYD09GQ/GA daily, 250 m | Earth Engine, `fetch_modis_aoi.py` → `tiles_modis.py` |
| 2010 | `hires` | Landsat 7 ETM+ (30 m + 15 m pan; SLC-off stripes) and ASTER (15 m) | Earth Engine, `fetch_hires_2010.py`, `fetch_l7_swir.py` |
| 2019 | `modis` | as 2010 | as 2010 |
| 2019 | `hires` | Sentinel-2 L2A, 10 m | Earth Engine, `fetch_s2_2019.py` |

Sentinel-2 did not exist in 2010 (launched 2015) and Landsat 5 has no scenes
here that summer. Planetary Computer has no daily MODIS, no Landsat
panchromatic band and no ASTER over the area, hence Earth Engine (a Python
env with earthengine-api, your own credentials). sat-tile-stack built `C18_001` for 2019
(`stacks/s2_2019/C18_001.nc`) and the Earth Engine tiles reproduce it to the
8-bit step (correlation 0.995–0.9998 after a one-pixel row offset); the full
7-band, 16-bit stacks cost > 1 GB of download per lake on the director's connection
(~7 h for the 82), so the page's movies use the display-grade tiles. To get
real sat-tile-stack stacks (labeler / classifier input):

    python engine/stacking/build_stacks.py --csv <source_data>/revisit/c18_lakes.csv \
        --output_dir <source_data>/revisit/stacks/s2_2019 --id_col lake_id \
        --time_range 2019-05-01/2019-09-30 --workers 6

Every movie is 153 daily frames (1 May → 30 Sep), 512 px over the same
5.12 km tile; a day with no image is a **black frame, on purpose**.
Reflectance 0…1 → 0…255, linear, for every sensor. Landsat 7's visible bands
clip over bright snow (drawn neutral there); ASTER has no blue band (blue is
synthesised from green and red, said in the sidecar).

`water_km2` in the sidecars is blue–red NDWI > 0.3 within 1.25 km of the tile
centre — a first-pass number, NOT a lake outline: neighbouring lakes inside
the radius count, Landsat's stripes are scaled for, cloudy Landsat frames
(1.65 µm test) and all ASTER frames carry none.

## Run order

    export DEFENSE_SOURCE_DATA=<main checkout>/cinematic/source_data   # from a worktree
    V=<main checkout>/cinematic/.venv/bin/python ; G=python   # G = a Python env with earthengine-api
    $V digitise_c18.py        # figure rasters → discs (+ QC PNGs in revisit/digitise/)
    $V build_lakes.py         # → revisit/c18_lakes.json (+ .csv)
    $G fetch_modis_aoi.py 2010 terra   (and aqua; 2019 terra, aqua)
    $V tiles_modis.py
    $G fetch_hires_2010.py ; $G fetch_l7_swir.py ; $G fetch_s2_2019.py
    $V make_movies.py         # → revisit/movies/{movies,thumbs}
    $V build_manifest.py      # → revisit/movies/c18_lakes.json + lakes/<id>.json
    rclone copy <source_data>/revisit/movies r2:<bucket>/addl/revisit_v<N> \
        --header-upload "Cache-Control: public, max-age=31536000, immutable"

R2 objects are immutable for a year: a rebuild goes to the next `_v<N>` and
`website/src/config/revisit.ts` is bumped.
