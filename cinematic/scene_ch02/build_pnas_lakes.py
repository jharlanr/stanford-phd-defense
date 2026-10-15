"""Build the Ch.2 featured-lakes assets: the SEVEN simulated center
lakes of the PNAS paper (all englacially draining — hydrofracture/moulin
— so they all wear the HF green), each with

  1. a polygon entry in pnas_lakes.json (outer ring in lon/lat), and
  2. a Sentinel-2 true-colour movie + per-frame sidecar JSON for the
     LakeVideoPopup (same machinery as Ch.1 — imported from
     scene_ch01/build_featured_lakes.py).

Lake IDs are Dunmire-2025 new_ids; the sims use old numbers = id − 1523.
Windows bracket each lake's PNAS drainage date (imagery dates in the
paper) with ~4 weeks before and ~2 weeks after.

Inputs (local copies only — bash cinematic/fetch_sources.sh):
  cinematic/source_data/stacks/CW_2019/CW2019_{1910,1951,2394,2411,2416,2511,2520}.nc
  cinematic/source_data/data/labels_2019_volumes.csv

Outputs (cinematic/scene_ch02/output_lakes/):
  pnas_lakes.json        → R2 ch02/pnas_lakes.json
  lake_<id>.mp4 / .json  → R2 ch02/lakes/<id>.mp4 / <id>.json

--valid (the director found the imagery movies harsh with all the black
frames and asked for them to go): the SAME seven windows with
only the frames Sentinel-2 actually imaged — Chapter 3's rule
(scene_ch03/build_callout_movies.py): keep a day when the stack's own
pct_nans < 1 (percent of the tile unimaged), so the no-pass days and the
swath-edge wedges go; cloudy frames stay (they are data). 2 fps (the
valid-frame rule). The sidecar carries each kept frame's real `day` (days
since the window start `t0`) and the full daily p_water series, so the
popup's volume curve, date badge and marker stay on the calendar:

  cinematic/scene_ch02/output_lakes_valid/<id>.mp4 / .json
      → R2 ch02/lakes_valid/<id>.mp4 / <id>.json
  sidecar: {lake_id, lake_name, class, class_name, accent, date_range,
            t0, days, ticks, drain, fps, frame_count, duration_sec,
            valid_rule, frames:[{t_sec, day, date_iso, p_water,
            cloud_pct, nan_pct}], p_water_daily:[days values | null]}

Run (defense checkout root, a Python env with cinematic/requirements.txt installed):
  nice -n 15 python -u \
      cinematic/scene_ch02/build_pnas_lakes.py [--inspect | --valid]
"""

import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import xarray as xr
from PIL import Image

sys.stdout.reconfigure(line_buffering=True)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scene_ch01'))

from shared import SOURCE_DATA, require_source  # noqa: E402
import build_featured_lakes as bfl  # noqa: E402  (Ch.1 movie machinery)

OUT_DIR = Path('cinematic/scene_ch02/output_lakes')
# Point the shared movie builder at Ch.2's output tree.
bfl.OUT_DIR = OUT_DIR
bfl.FRAMES_DIR = OUT_DIR / '_frames'

HF_GREEN = '#4caf50'

# The seven PNAS center lakes. window brackets the paper's drainage
# imagery dates; drain dates from the PNAS main text/SI.
PNAS_LAKES = [
    dict(id='CW2019_1910', window=('2019-06-25', '2019-08-10')),  # drains ~Jul 22
    dict(id='CW2019_1951', window=('2019-06-05', '2019-07-25')),  # drains ~Jul 6
    dict(id='CW2019_2394', window=('2019-05-15', '2019-07-05')),  # drains Jun 14–16
    dict(id='CW2019_2411', window=('2019-07-01', '2019-08-20')),  # drains ~Aug 3
    dict(id='CW2019_2416', window=('2019-07-20', '2019-09-05')),  # drains Aug 21
    dict(id='CW2019_2511', window=('2019-07-20', '2019-09-05')),  # drains Aug 21
    dict(id='CW2019_2520', window=('2019-06-05', '2019-07-25')),  # drains ~Jul 6
]
for l in PNAS_LAKES:
    l.update(
        cls='HF',
        cls_name='Hydrofracture',
        name=f"Lake {l['id'].split('_')[1]}",
        color=HF_GREEN,
    )


VALID_DIR = Path('cinematic/scene_ch02/output_lakes_valid')
VALID_FPS = 2.0
MAX_PCT_NANS = 1.0  # percent of the tile unimaged (Ch.3's rule)


def build_valid_movie(lake: dict) -> dict:
    """Kept-frames-only movie + day-indexed sidecar (see --valid above)."""
    ds = xr.open_dataset(require_source(bfl.STACK_DIR / f"{lake['id']}.nc"))
    t = ds['time'].values
    lo = np.datetime64(lake['window'][0])
    hi = np.datetime64(lake['window'][1] + 'T23:59:59')
    dsw = ds.isel(time=(t >= lo) & (t <= hi))
    n = dsw.sizes['time']
    times = dsw['time'].values
    pct_nans = dsw['pct_nans'].values
    cloud = dsw['eo_cloud_cover'].values
    p_water = dsw['p_water'].values
    band_names = [str(x) for x in dsw['common_name'].values]
    rgb_idx = [band_names.index(b) for b in ('red', 'green', 'blue')]
    outline = bfl.lake_outline_mask(dsw['lake_boundary'].values, thickness=2)
    outline_rgb = bfl.hex_to_rgb(lake['color'])

    day0 = np.datetime64(lake['window'][0])
    days = int((np.datetime64(lake['window'][1]) - day0) / np.timedelta64(1, 'D')) + 1
    fdir = VALID_DIR / '_frames' / lake['id']
    fdir.mkdir(parents=True, exist_ok=True)
    for old in fdir.glob('*.png'):
        old.unlink()
    cube = dsw['reflectance'].isel(band=rgb_idx).values  # one read

    kept = []
    for i in range(n):
        pn = pct_nans[i]
        if not np.isfinite(pn) or pn >= MAX_PCT_NANS:
            continue
        refl = cube[i]
        if np.isnan(refl).all():
            continue
        r = np.clip(np.nan_to_num(refl, nan=0.0) / bfl.S2_QUANT, 0.0, 1.0)
        frame = (np.transpose(r, (1, 2, 0)) * 255.0).clip(0, 255).astype(np.uint8)
        frame[np.isnan(refl).any(axis=0)] = 40  # the <1 % stragglers
        frame[outline] = outline_rgb
        Image.fromarray(frame).save(fdir / f'f{len(kept):04d}.png', compress_level=1)
        day = int((times[i].astype('datetime64[D]') - day0) / np.timedelta64(1, 'D'))
        pw, cc = p_water[i], cloud[i]
        kept.append({
            't_sec': round(len(kept) / VALID_FPS, 3),
            'day': day,
            'date_iso': str(times[i])[:10],
            'p_water': None if np.isnan(pw) else round(float(pw), 4),
            'cloud_pct': None if np.isnan(cc) else round(float(cc), 1),
            'nan_pct': round(float(pn), 2),
        })

    out_mp4 = VALID_DIR / f"{lake['id']}.mp4"
    subprocess.run([
        'ffmpeg', '-y', '-loglevel', 'error',
        '-framerate', str(VALID_FPS), '-i', str(fdir / 'f%04d.png'),
        '-c:v', 'libx264', '-crf', '20', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', '-r', str(VALID_FPS), str(out_mp4),
    ], check=True)

    # The full daily p_water series (every day of the window, imaged or
    # not) — the curve and the drain marker are the same data as before.
    daily: list = [None] * days
    for i in range(n):
        d = int((times[i].astype('datetime64[D]') - day0) / np.timedelta64(1, 'D'))
        if 0 <= d < days and not np.isnan(p_water[i]):
            daily[d] = round(float(p_water[i]), 4)

    # Drain marker: build_featured_lakes' rule verbatim (largest drop
    # between consecutive REAL measurements ≤ 7 days apart, ≥ 0.3).
    drain = None
    valid = [(i, float(p_water[i])) for i in range(n) if not np.isnan(p_water[i])]
    best_drop, best_i = 0.0, None
    for (i0, p0), (i1, p1) in zip(valid, valid[1:]):
        gap_days = (times[i1] - times[i0]) / np.timedelta64(1, 'D')
        if gap_days <= 7 and p0 - p1 > best_drop:
            best_drop, best_i = p0 - p1, i1
    if best_i is not None and best_drop >= 0.3:
        iso = str(times[best_i])[:10]
        event = lake.get('event_label', 'drain')  # Ch.1's ND lake: 'freeze-up'
        drain = {'date_iso': iso, 'label': f'{bfl.date_label(iso)} · {event}'}

    ticks = bfl.make_ticks(day0, np.datetime64(lake['window'][1]))
    sidecar = {
        'lake_id': lake['id'],
        'lake_name': lake['name'],
        'class': lake['cls'],
        'class_name': lake['cls_name'],
        'accent': lake['color'],
        'date_range': list(lake['window']),
        't0': lake['window'][0],
        'days': days,
        'ticks': [{'date_iso': d, 'label': bfl.date_label(d)} for d in ticks],
        'drain': drain,
        'fps': VALID_FPS,
        'frame_count': len(kept),
        'duration_sec': round(len(kept) / VALID_FPS, 3),
        'valid_rule': f'pct_nans < {MAX_PCT_NANS} (percent of the tile unimaged)',
        'source': 'Sentinel-2 L2A · Microsoft Planetary Computer',
        'frames': kept,
        'p_water_daily': daily,
    }
    (VALID_DIR / f"{lake['id']}.json").write_text(json.dumps(sidecar, separators=(',', ':')))
    mb = out_mp4.stat().st_size / 1e6
    print(f"  {lake['id']}: kept {len(kept)}/{n} days · {kept[0]['date_iso']} → "
          f"{kept[-1]['date_iso']} · {mb:.2f} MB"
          + (f" · drain {drain['date_iso']}" if drain else ' · no drain marker'))
    return sidecar


def main() -> None:
    inspect = '--inspect' in sys.argv
    if '--valid' in sys.argv:
        VALID_DIR.mkdir(parents=True, exist_ok=True)
        for lake in PNAS_LAKES:
            build_valid_movie(lake)
        print('\nupload:\n  rclone copy cinematic/scene_ch02/output_lakes_valid '
              'r2:<bucket>/ch02/lakes_valid/ --exclude "_frames/**" --header-upload "Cache-Control: public, max-age=31536000, immutable"')
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = {}
    with open(require_source(SOURCE_DATA / 'data' / 'labels_2019_volumes.csv'),
              encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if row['new_id'] in {l['id'] for l in PNAS_LAKES}:
                rows[row['new_id']] = row

    if inspect:
        for lake in PNAS_LAKES:
            ds = xr.open_dataset(require_source(bfl.STACK_DIR / f"{lake['id']}.nc"))
            pw = ds['p_water'].values
            t = ds['time'].values
            print(f"\n{lake['id']}:")
            for i in range(0, len(t), 3):
                v = pw[i]
                bar = '' if np.isnan(v) else '#' * int(round(v * 40))
                print(f"  {str(t[i])[:10]}  {'—' if np.isnan(v) else f'{v:4.2f}'} {bar}")
        return

    lakes_out = []
    for lake in PNAS_LAKES:
        row = rows[lake['id']]
        ring = bfl.parse_wkt_ring(row['geometry'])
        if len(ring) > 8:
            ring = ring[::bfl.DECIMATE_STRIDE]
        sidecar = bfl.build_movie(lake, row)
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

    (OUT_DIR / 'pnas_lakes.json').write_text(json.dumps({
        'lakes': lakes_out,
        'comment': 'The seven PNAS center lakes (all englacial/HF drainages; '
                   'sims use old ids = new_id − 1523). Ch.2 Beat 0 overlay + '
                   'popup registry.',
    }, separators=(',', ':')))
    print(f"\nwrote {OUT_DIR / 'pnas_lakes.json'}")
    print('\nupload:')
    print('  rclone copyto cinematic/scene_ch02/output_lakes/pnas_lakes.json r2:<bucket>/ch02/pnas_lakes.json --header-upload "Cache-Control: public, max-age=31536000, immutable"')
    for lake in PNAS_LAKES:
        print(f"  rclone copyto cinematic/scene_ch02/output_lakes/lake_{lake['id']}.mp4 r2:<bucket>/ch02/lakes/{lake['id']}.mp4 --header-upload 'Cache-Control: public, max-age=31536000, immutable'")
        print(f"  rclone copyto cinematic/scene_ch02/output_lakes/lake_{lake['id']}.json r2:<bucket>/ch02/lakes/{lake['id']}.json --header-upload 'Cache-Control: public, max-age=31536000, immutable'")


if __name__ == '__main__':
    main()
