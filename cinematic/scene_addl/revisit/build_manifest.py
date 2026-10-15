"""The files the website reads (→ R2 `addl/revisit/`):

  c18_lakes.json     the manifest: every lake, what the paper says happened
                     to it on each observation day, and which movies exist
  lakes/<id>.json    one sidecar per lake: the per-day detail of its four
                     tracks (image or blank, sensor, cloud, water)

R2 objects are cached for a year (`immutable`), so the whole folder is
uploaded under a versioned prefix — `addl/revisit_v<N>/` — and a rebuild
goes to the next N (the site's one constant: config/revisit.ts).

  cinematic/.venv/bin/python build_manifest.py
"""
from __future__ import annotations

import json

from common import AOI_X0, AOI_X1, AOI_Y0, AOI_Y1, C18_DOMAIN_KM, C18_UTM0, MOVIE_DIR, SEASONS, TILE_M, WORK
from digitise_c18 import DAYS
from make_movies import FPS, META_DIR, WATER_R_M

TRACKS = ((2010, 'modis'), (2010, 'hires'), (2019, 'modis'), (2019, 'hires'))
OBS_NOTE = {
    '2010-06-05': 'the day before the cascade',
    '2010-06-06': '15 fully, 28 partially (paper text)',
    '2010-06-07': '9 fully, 21 partially (paper text)',
    '2010-06-10': 'the 8–10 June drainages: clouds hid the lakes on 8 and 9 June; 48 completely',
}


def main() -> None:
    from pyproj import Transformer
    src = json.loads((WORK / 'c18_lakes.json').read_text())
    to_ll = Transformer.from_crs(32622, 4326, always_xy=True)
    lakes_out = []
    (MOVIE_DIR / 'lakes').mkdir(parents=True, exist_ok=True)
    n_tracks = {t: 0 for t in TRACKS}
    for lk in src['lakes']:
        tracks: dict = {}
        side_tracks: dict = {}
        for year, track in TRACKS:
            m = META_DIR / f"{year}_{track}_{lk['id']}.json"
            if not m.exists():
                tracks.setdefault(str(year), {})[track] = None
                continue
            meta = json.loads(m.read_text())
            n_tracks[(year, track)] += 1
            tracks.setdefault(str(year), {})[track] = meta['n_images']
            side_tracks.setdefault(str(year), {})[track] = meta
        thumbs = {str(y): (MOVIE_DIR / 'thumbs' / str(y) / f"{lk['id']}.jpg").exists() for y in SEASONS}
        states = {d: h['state'] for d, h in lk['history'].items()}
        lakes_out.append({
            'id': lk['id'], 'lat': lk['lat'], 'lon': lk['lon'], 'cell': [lk['i'], lk['j']],
            'states': states,
            'extent': {d: h['extent'] for d, h in lk['history'].items() if 'extent' in h},
            'volume_m3': {d: h['volume_m3'] for d, h in lk['history'].items() if 'volume_m3' in h},
            'drained_days': lk['drained_days'],
            'tracks': tracks, 'thumbs': thumbs,
        })
        (MOVIE_DIR / 'lakes' / f"{lk['id']}.json").write_text(json.dumps({
            'id': lk['id'], 'lat': lk['lat'], 'lon': lk['lon'],
            'fps': FPS, 'frame_count': 153, 'tile_km': TILE_M / 1e3, 'water_radius_km': WATER_R_M / 1e3,
            'history': lk['history'],
            'tracks': side_tracks,
        }))
    corners = [(C18_UTM0[0] * 1e3, C18_UTM0[1] * 1e3), ((C18_UTM0[0] + C18_DOMAIN_KM[0]) * 1e3, (C18_UTM0[1] + C18_DOMAIN_KM[1]) * 1e3)]
    lons = [lk['lon'] for lk in lakes_out]; lats = [lk['lat'] for lk in lakes_out]
    manifest = {
        'paper': {'cite': 'Christoffersen et al. 2018, Nature Communications 9:1064', 'doi': 'https://doi.org/10.1038/s41467-018-03420-8'},
        'provenance': 'Lake positions and drainage days DIGITISED from the paper\'s Figs. 3 and 4 (it publishes no lake table). '
                      'Positions are the centres of the model\'s 1 km grid cells; checked against the real lakes in MODIS of 5–6 June 2010.',
        'counts': {
            'lakes': len(lakes_out),
            'drained_lakes': sum(1 for lk in lakes_out if lk['drained_days']),
            'events_digitised': sum(len(lk['drained_days']) for lk in lakes_out),
            'events_paper': 124,
        },
        'obs_days': [{'date': d, 'caption': {k: v for k, v in s.items() if k != 'panels'}, 'note': OBS_NOTE[d]} for d, s in DAYS.items()],
        'cloud_days': ['2010-06-08', '2010-06-09'],
        'lake_bbox': {'south': min(lats), 'north': max(lats), 'west': min(lons), 'east': max(lons)},
        'seasons': {
            '2010': {'start': SEASONS[2010][0], 'end': SEASONS[2010][1], 'modis': 'MODIS · 250 m', 'hires': 'Landsat 7 · ASTER · 15 m'},
            '2019': {'start': SEASONS[2019][0], 'end': SEASONS[2019][1], 'modis': 'MODIS · 250 m', 'hires': 'Sentinel-2 · 10 m'},
        },
        'fps': FPS, 'frame_count': 153, 'tile_km': TILE_M / 1e3,
        'sidecar': 'lakes/<id>.json',
        'lakes': lakes_out,
    }
    out = MOVIE_DIR / 'c18_lakes.json'
    out.write_text(json.dumps(manifest))
    print('wrote', out.name, f'{out.stat().st_size / 1e3:.0f} kB;', {f'{y}/{t}': n for (y, t), n in n_tracks.items()}, 'of', len(lakes_out))
    _ = (AOI_X0, AOI_X1, AOI_Y0, AOI_Y1, corners, to_ll)


if __name__ == '__main__':
    main()
