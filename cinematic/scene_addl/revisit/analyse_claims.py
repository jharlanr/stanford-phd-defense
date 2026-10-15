"""A FIRST PASS at the question, by numbers only — to be checked by eye on
the page, not quoted: for each lake the paper drains, how much water does
Landsat 7 see near it before the cascade (clear frames up to 5 June 2010),
on 9 June (three days after the first drainages) and on 16 June (six days
after the last)?

Water = blue–red NDWI > 0.3 within 1.25 km of the lake's grid cell (so a
neighbour inside the radius counts, and it is an AREA, not a volume); cloudy
frames (1.65 µm test) are left out; ASTER frames carry no estimate.

  cinematic/.venv/bin/python analyse_claims.py   → revisit/claims_first_pass.csv
"""
from __future__ import annotations

import csv
import json

from common import WORK, season_days
from make_movies import META_DIR

PRE = ('2010-05-15', '2010-06-05')
MIN_LAKE = 0.05     # km² — below this there is no lake to speak of


def main() -> None:
    lakes = json.loads((WORK / 'c18_lakes.json').read_text())['lakes']
    days = season_days(2010)
    rows = []
    for lk in lakes:
        m = json.loads((META_DIR / f"2010_hires_{lk['id']}.json").read_text())
        w = dict(zip(days, m['water_km2']))
        pre = [(v, d) for d, v in w.items() if PRE[0] <= d <= PRE[1] and v is not None]
        pre_max, pre_day = max(pre) if pre else (None, None)
        claim = ''.join(
            {'full': 'F', 'partial': 'P', 'unknown': 'D'}[lk['history'][d].get('extent', 'unknown')]
            if lk['history'].get(d, {}).get('state') == 'drained'
            else ('u' if lk['history'].get(d, {}).get('state') == 'unchanged' else '.')
            for d in ('2010-06-06', '2010-06-07', '2010-06-10'))
        w9, w16 = w['2010-06-09'], w['2010-06-16']
        verdict = ''
        if lk['n_drainages']:
            later = max(v for v in (w9, w16) if v is not None) if (w9 is not None or w16 is not None) else None
            if w16 is None:
                verdict = 'no clear 16 June view'
            elif (pre_max or 0) < MIN_LAKE and (later or 0) < MIN_LAKE:
                verdict = 'no lake seen'
            elif (pre_max or 0) < MIN_LAKE:
                verdict = 'lake FORMS during the cascade' if w16 >= MIN_LAKE else 'forms, gone by 16 June'
            elif w16 >= 0.5 * pre_max:
                verdict = 'still there on 16 June'
            elif w16 < 0.2 * pre_max:
                verdict = 'gone by 16 June'
            else:
                verdict = 'smaller on 16 June'
        rows.append({'id': lk['id'], 'lat': lk['lat'], 'lon': lk['lon'],
                     'paper_6_7_10_June': claim, 'pre_km2': pre_max, 'pre_day': pre_day,
                     'jun07_km2': w['2010-06-07'], 'jun09_km2': w9, 'jun16_km2': w16, 'jul02_km2': w['2010-07-02'],
                     'first_pass': verdict})
    out = WORK / 'claims_first_pass.csv'
    with open(out, 'w', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader(); wr.writerows(rows)
    drained = [r for r in rows if r['first_pass']]
    print(f'{len(drained)} lakes the paper drains (F = fully, P = partially, D = by 10 June, u = unchanged, . = not on the map):')
    for v in sorted({r['first_pass'] for r in drained}):
        ids = [r['id'][4:] for r in drained if r['first_pass'] == v]
        print(f'  {v:32s} {len(ids):3d}   {" ".join(ids)}')
    full = [r for r in rows if r['paper_6_7_10_June'][:2] in ('F.', 'PF', 'uF', '.F')]
    seen9 = [r for r in full if r['jun09_km2'] is not None]
    still9 = [r for r in seen9 if r['jun09_km2'] >= MIN_LAKE]
    print(f'{len(full)} lakes read as FULLY drained on 6 or 7 June; Landsat sees {len(seen9)} of them clearly on 9 June;',
          f'{len(still9)} still hold ≥ {MIN_LAKE} km² of water then:', ' '.join(r['id'][4:] for r in still9))
    print('wrote', out)


if __name__ == '__main__':
    main()
