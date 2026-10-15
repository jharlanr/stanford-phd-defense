"""Build the Ch.1 featured-lakes assets: the five ESSD fig-4
representative drainage-class lakes, each with

  1. a polygon entry in featured_lakes.json (outer ring in lon/lat +
     class + color) — drives the class-colored, hoverable, clickable
     lake overlay on the globe at Ch.1 Beat 0, and
  2. a Sentinel-2 true-colour movie (mp4) + per-frame sidecar JSON —
     drives the LakeVideoPopup, with the lake outline burned in the
     CLASS color and a normalized-lake-volume series for the chart.

Class palette is ESSD fig-4's CLASS_COLORS verbatim:
  ND #e8524a · HF #4caf50 · MD #42a5f5 · LD #ff9800 · CD #ab47bc

Inputs (local copies only — bash cinematic/fetch_sources.sh):
  cinematic/source_data/stacks/CW_2019/CW2019_{1597,1848,1889,1907,2330}.nc
  cinematic/source_data/data/labels_2019_volumes.csv   (WKT polygons)

Outputs (cinematic/scene_ch01/output_lakes/):
  featured_lakes.json          → R2 ch01/featured_lakes.json
  lake_<id>.mp4 / .json        → R2 ch01/lakes/<id>.mp4 / <id>.json

Per-lake time WINDOWS are chosen so each lake's characteristic
p_water story fits the frame (ND fills late July and never drains;
CD decays gradually into August; HF/North Lake keeps the director's
May 15 – June 30 spec). Verify with --inspect, which prints each
stack's p_water series instead of rendering.

Run (from defense checkout root, a Python env with cinematic/requirements.txt installed):
  python -u cinematic/scene_ch01/build_featured_lakes.py [--inspect]
"""

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import xarray as xr
from PIL import Image

sys.stdout.reconfigure(line_buffering=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared import SOURCE_DATA, require_source  # noqa: E402

STACK_DIR = SOURCE_DATA / 'stacks' / 'CW_2019'
LABELS_CSV = SOURCE_DATA / 'data' / 'labels_2019_volumes.csv'
OUT_DIR = Path('cinematic/scene_ch01/output_lakes')
FRAMES_DIR = OUT_DIR / '_frames'

# --season (for Chapter 3): the SAME five lakes over the FULL melt
# season, May 1 - Sep 30, one frame per day at 1 fps, written to
# cinematic/scene_ch03/output_lakes/ -> R2 ch03/lakes/<id>.{mp4,json}.
# Ch.3's callout panels and the label demo seek frame-by-frame on a
# shared season clock, so the movie must cover every day; Ch.1's popups
# keep the event-cut windows below.
SEASON = '--season' in sys.argv
if SEASON:
    OUT_DIR = Path('cinematic/scene_ch03/output_lakes')
    FRAMES_DIR = OUT_DIR / '_frames'
SEASON_WINDOW = ('2019-05-01', '2019-09-30')

# The five ESSD fig-4 representative lakes, in the figure's row order.
# window = the movie/chart span; picked from each lake's p_water story.
FEATURED = [
    dict(id='CW2019_1889', cls='HF', cls_name='Hydrofracture',
         name='North Lake', color='#4caf50',
         window=('2019-05-15', '2019-06-30')),
    dict(id='CW2019_1848', cls='MD', cls_name='Moulin drainage',
         name='Lake 1848', color='#42a5f5',
         window=('2019-05-01', '2019-06-30')),
    dict(id='CW2019_1907', cls='LD', cls_name='Lateral drainage',
         name='Lake 1907', color='#ff9800',
         window=('2019-05-01', '2019-06-15')),
    dict(id='CW2019_2330', cls='CD', cls_name='Crevasse drainage',
         name='Lake 2330', color='#ab47bc',
         window=('2019-05-15', '2019-08-15')),
    # ND's end-of-season p_water cliff is FREEZE-UP, not a drainage —
    # the marker must say so or the no-drainage class contradicts itself.
    dict(id='CW2019_1597', cls='ND', cls_name='No drainage',
         name='Lake 1597', color='#e8524a', event_label='freeze-up',
         window=('2019-07-01', '2019-09-30')),
]

S2_QUANT = 10000.0  # same true-colour recipe as the old NL-only build
TARGET_LOOP_SEC = 32.0  # fps scales with window length toward this
DECIMATE_STRIDE = 2     # polygon ring decimation for the overlay JSON

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def hex_to_rgb(h: str) -> tuple:
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def date_label(iso: str) -> str:
    _, m, d = iso.split('-')
    return f'{int(d)} {MONTHS[int(m) - 1]}'


def parse_wkt_ring(wkt: str) -> list:
    """Outer ring of a WKT POLYGON/MULTIPOLYGON as [[lon, lat], ...]."""
    m = re.search(r'\(\(+([^()]+)', wkt or '')
    if not m:
        return []
    coords = []
    for pair in m.group(1).split(','):
        parts = pair.strip().split()
        if len(parts) >= 2:
            coords.append([float(parts[0]), float(parts[1])])
    if len(coords) >= 2 and coords[0] == coords[-1]:
        coords.pop()
    return coords


def make_ticks(lo: np.datetime64, hi: np.datetime64) -> list:
    """Axis ticks: window endpoints + every 1st/15th in between, thinned
    to at most 5 so long windows don't crowd the axis. North Lake's
    window lands exactly on the director's spec: 15 May / 1 Jun / 15 Jun / 30 Jun."""
    cands = [lo]
    d = lo + np.timedelta64(1, 'D')
    while d < hi:
        day = int(str(d)[8:10])
        if day in (1, 15):
            cands.append(d)
        d += np.timedelta64(1, 'D')
    cands.append(hi)
    # Drop interior candidates that crowd an endpoint (< 7 days away).
    cands = [c for i, c in enumerate(cands)
             if i in (0, len(cands) - 1)
             or (c - lo > np.timedelta64(6, 'D') and hi - c > np.timedelta64(6, 'D'))]
    while len(cands) > 5:
        # Thin interior ticks (keep endpoints) by dropping every other.
        interior = cands[1:-1]
        cands = [cands[0]] + interior[1::2] + [cands[-1]]
    return [str(c)[:10] for c in cands]


def lake_outline_mask(lake_boundary: np.ndarray, thickness: int = 2) -> np.ndarray:
    m = (lake_boundary > 0).astype(np.uint8)
    pad = np.pad(m, 1, mode='edge')
    nb_min = np.minimum.reduce([
        pad[0:-2, 0:-2], pad[0:-2, 1:-1], pad[0:-2, 2:],
        pad[1:-1, 0:-2],                  pad[1:-1, 2:],
        pad[2:,   0:-2], pad[2:,   1:-1], pad[2:,   2:],
    ])
    outline = (m == 1) & (nb_min == 0)
    for _ in range(thickness - 1):
        pad = np.pad(outline.astype(np.uint8), 1, mode='edge')
        nb_max = np.maximum.reduce([
            pad[0:-2, 1:-1], pad[1:-1, 0:-2], pad[1:-1, 2:], pad[2:, 1:-1],
        ])
        outline = nb_max > 0
    return outline


def build_movie(lake: dict, meta_row: dict) -> dict:
    nc = require_source(STACK_DIR / f"{lake['id']}.nc")
    ds = xr.open_dataset(nc)
    t = ds['time'].values
    lo = np.datetime64(lake['window'][0])
    hi = np.datetime64(lake['window'][1] + 'T23:59:59')
    sel = (t >= lo) & (t <= hi)
    dsw = ds.isel(time=sel)
    n = dsw.sizes['time']

    band_names = [str(x) for x in dsw['common_name'].values]
    rgb_idx = [band_names.index(b) for b in ('red', 'green', 'blue')]
    refl = dsw['reflectance'].values
    pct_nans = dsw['pct_nans'].values
    cloud = dsw['eo_cloud_cover'].values
    p_water = dsw['p_water'].values
    times = dsw['time'].values

    outline = lake_outline_mask(dsw['lake_boundary'].values, thickness=2)
    outline_rgb = hex_to_rgb(lake['color'])

    fps = 1.0 if SEASON else round(min(3.0, max(1.2, n / TARGET_LOOP_SEC)), 2)

    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    for old in FRAMES_DIR.glob('*.png'):
        old.unlink()

    print(f"  {lake['id']} ({lake['cls']}): {n} frames @ {fps} fps, "
          f"{lake['window'][0]} → {lake['window'][1]}")
    for i in range(n):
        is_nan = bool(pct_nans[i] > 0.99 or np.isnan(pct_nans[i]))
        h, w = refl.shape[-2:]
        if is_nan:
            frame = np.full((h, w, 3), 40, dtype=np.uint8)
        else:
            r = np.clip(refl[i, rgb_idx] / S2_QUANT, 0.0, 1.0)
            frame = (np.transpose(r, (1, 2, 0)) * 255.0).clip(0, 255).astype(np.uint8)
            nan_mask = np.isnan(refl[i, rgb_idx]).any(axis=0)
            frame[nan_mask] = 40
        frame[outline] = outline_rgb
        Image.fromarray(frame).save(FRAMES_DIR / f'f{i:04d}.png', optimize=True)

    out_mp4 = OUT_DIR / f"lake_{lake['id']}.mp4"
    subprocess.run([
        'ffmpeg', '-y', '-loglevel', 'error',
        '-framerate', str(fps), '-i', str(FRAMES_DIR / 'f%04d.png'),
        '-c:v', 'libx264', '-crf', '20', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', '-r', str(fps), str(out_mp4),
    ], check=True)

    # Drain marker: date of the largest p_water drop between consecutive
    # REAL measurements — but only when the two measurements are ≤ 7 days
    # apart (a 0.5 drop across a 15-day cloud gap has no defensible drain
    # DATE — CD/MD decay under clouds and get no marker) and the drop is
    # ≥ 0.3 (ND never drains inside its window).
    drain = None
    valid = [(i, float(p_water[i])) for i in range(n) if not np.isnan(p_water[i])]
    best_drop, best_i = 0.0, None
    for (i0, p0), (i1, p1) in zip(valid, valid[1:]):
        gap_days = (times[i1] - times[i0]) / np.timedelta64(1, 'D')
        if gap_days <= 7 and p0 - p1 > best_drop:
            best_drop, best_i = p0 - p1, i1
    if best_i is not None and best_drop >= 0.3:
        drain_iso = str(times[best_i])[:10]
        event = lake.get('event_label', 'drain')
        drain = {'date_iso': drain_iso, 'label': f'{date_label(drain_iso)} · {event}'}

    frames_meta = []
    for i in range(n):
        pw, cc, nn = p_water[i], cloud[i], pct_nans[i]
        frames_meta.append({
            't_sec': round(i / fps, 3),
            'date_iso': str(times[i])[:10],
            'p_water': None if np.isnan(pw) else round(float(pw), 4),
            'cloud_pct': None if np.isnan(cc) else round(float(cc), 1),
            'nan_pct': None if np.isnan(nn) else round(float(nn), 1),
        })

    ticks = make_ticks(np.datetime64(lake['window'][0]), np.datetime64(lake['window'][1]))
    sidecar = {
        'lake_id': lake['id'],
        'lake_name': lake['name'],
        'class': lake['cls'],
        'class_name': lake['cls_name'],
        'accent': lake['color'],
        'date_range': list(lake['window']),
        'ticks': [{'date_iso': d, 'label': date_label(d)} for d in ticks],
        'drain': drain,
        'fps': fps,
        'frame_count': n,
        'duration_sec': round(n / fps, 3),
        'source': 'Sentinel-2 L2A · Microsoft Planetary Computer',
        'frames': frames_meta,
    }
    (OUT_DIR / f"lake_{lake['id']}.json").write_text(json.dumps(sidecar, indent=1))
    sz = out_mp4.stat().st_size / 1e6
    print(f"    wrote {out_mp4.name} ({sz:.2f} MB) + sidecar"
          + (f" · drain {drain['date_iso']} (Δ{best_drop:.2f})" if drain else ' · no drain marker'))
    return sidecar


def main() -> None:
    inspect = '--inspect' in sys.argv
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = {}
    with open(require_source(LABELS_CSV), encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if row['new_id'] in {l['id'] for l in FEATURED}:
                rows[row['new_id']] = row

    if inspect:
        for lake in FEATURED:
            ds = xr.open_dataset(require_source(STACK_DIR / f"{lake['id']}.nc"))
            pw = ds['p_water'].values
            t = ds['time'].values
            print(f"\n{lake['id']} ({lake['cls']}):")
            for i in range(0, len(t), 3):
                v = pw[i]
                bar = '' if np.isnan(v) else '#' * int(round(v * 40))
                print(f"  {str(t[i])[:10]}  {'—' if np.isnan(v) else f'{v:4.2f}'} {bar}")
        return

    if SEASON:
        for lake in FEATURED:
            lake['window'] = SEASON_WINDOW

    lakes_out = []
    for lake in FEATURED:
        row = rows[lake['id']]
        ring = parse_wkt_ring(row['geometry'])
        if len(ring) > 8:
            ring = ring[::DECIMATE_STRIDE]
        sidecar = build_movie(lake, row)
        lakes_out.append({
            'id': lake['id'],
            'name': lake['name'],
            'class': lake['cls'],
            'class_name': lake['cls_name'],
            'color': lake['color'],
            'lon': float(row['lon']),
            'lat': float(row['lat']),
            'area_m2': float(row['area']),
            'date_range': sidecar['date_range'],
            'ring': ring,
        })

    if SEASON:
        print('\nupload:\n  rclone copy cinematic/scene_ch03/output_lakes r2:<bucket>/ch03/lakes '
              '--include "lake_*.mp4" --include "lake_*.json" --header-upload "Cache-Control: public, max-age=31536000, immutable"  (rename lake_<id> -> <id>)')
        return

    (OUT_DIR / 'featured_lakes.json').write_text(json.dumps({
        'lakes': lakes_out,
        'comment': 'ESSD fig-4 representative drainage-class lakes; colors are '
                   'the manuscript CLASS_COLORS. Ch.1 Beat 0 overlay + popup registry.',
    }, separators=(',', ':')))
    print(f"\nwrote {OUT_DIR / 'featured_lakes.json'}")
    print('\nupload:')
    print('  rclone copyto cinematic/scene_ch01/output_lakes/featured_lakes.json r2:<bucket>/ch01/featured_lakes.json --header-upload "Cache-Control: public, max-age=31536000, immutable"')
    for lake in FEATURED:
        print(f"  rclone copyto cinematic/scene_ch01/output_lakes/lake_{lake['id']}.mp4 r2:<bucket>/ch01/lakes/{lake['id']}.mp4 --header-upload 'Cache-Control: public, max-age=31536000, immutable'")
        print(f"  rclone copyto cinematic/scene_ch01/output_lakes/lake_{lake['id']}.json r2:<bucket>/ch01/lakes/{lake['id']}.json --header-upload 'Cache-Control: public, max-age=31536000, immutable'")


if __name__ == '__main__':
    main()
