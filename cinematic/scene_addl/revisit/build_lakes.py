"""From the digitised discs (digitise_c18.py) to ONE list of lakes with a
history: which lakes Christoffersen et al. 2018 had on 5 June 2010, and which
they drained to the bed on 6 June, 7 June and by 10 June.

Per observation day the two Fig. 3 panels are matched by distance (they
agree to ~0.1 km), Fig. 4's panel adds any drained disc Fig. 3 hides, and the
result is snapped to the model's 1 km grid (the lakes ARE on it: the
fractional parts of the digitised positions concentrate to ±0.05 km).
Lakes are then tracked across the four days: same cell first, then the
nearest unclaimed cell within 1.5 km.

Registration: model km → UTM 22N km = (523.25 + x, 7404.0 + y). Checked
against the real lakes in MODIS of 5–6 June 2010 (Terra and Aqua): the
best shift is within one 125 m sample of zero.

  cinematic/.venv/bin/python build_lakes.py    → revisit/c18_lakes.json
"""
from __future__ import annotations

import json

import numpy as np
from pyproj import Transformer

from common import C18_UTM0, DIGI_DIR, EPSG, WORK
from digitise_c18 import DAYS, circ_offset

UTM2LL = Transformer.from_crs(EPSG, 4326, always_xy=True)
# Legend of Fig. 3: marker AREA ∝ volume, 9.4e6 m³ = the largest disc. (The
# smallest digitised disc / the largest = 0.08 in radius; √(0.1/9.4) = 0.10.)
V_MAX = 9.4e6


def corrected(raw: dict, panel: str) -> list[dict]:
    good = [d for d in raw[panel] if d['support'] >= 0.5]
    ox = circ_offset(np.array([d['x_km'] for d in good]))
    oy = circ_offset(np.array([d['y_km'] for d in good]))
    return [{**d, 'xc': d['x_km'] - ox, 'yc': d['y_km'] - oy, 'panel': panel} for d in raw[panel]]


def greedy(a: list[dict], b: list[dict], tol: float) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    if not a or not b:
        return [], list(range(len(a))), list(range(len(b)))
    D = np.hypot(np.array([d['xc'] for d in a])[:, None] - np.array([d['xc'] for d in b])[None, :],
                 np.array([d['yc'] for d in a])[:, None] - np.array([d['yc'] for d in b])[None, :])
    pairs, ua, ub = [], set(range(len(a))), set(range(len(b)))
    for flat in np.argsort(D, axis=None):
        i, j = divmod(int(flat), len(b))
        if D[i, j] > tol:
            break
        if i in ua and j in ub:
            pairs.append((i, j)); ua.discard(i); ub.discard(j)
    return pairs, sorted(ua), sorted(ub)


def day_table(raw: dict, day: str) -> list[dict]:
    spec = DAYS[day]
    p3 = [p for p in spec['panels'] if p.startswith('3')]
    p4 = [p for p in spec['panels'] if p.startswith('4')]
    rows: list[dict] = []
    for kind in ('present', 'drained', 'unchanged'):
        A = [d for d in corrected(raw, p3[0]) if d['kind'] == kind]
        B = [d for d in corrected(raw, p3[1]) if d['kind'] == kind]
        pairs, ua, ub = greedy(A, B, 0.6)
        merged = [{'xc': (A[i]['xc'] + B[j]['xc']) / 2, 'yc': (A[i]['yc'] + B[j]['yc']) / 2,
                   'r_pt': (A[i]['r_pt'] + B[j]['r_pt']) / 2, 'panels': [p3[0], p3[1]]} for i, j in pairs]
        merged += [{'xc': A[i]['xc'], 'yc': A[i]['yc'], 'r_pt': A[i]['r_pt'], 'panels': [p3[0]]} for i in ua]
        merged += [{'xc': B[j]['xc'], 'yc': B[j]['yc'], 'r_pt': B[j]['r_pt'], 'panels': [p3[1]]} for j in ub]
        if kind == 'drained' and p4:
            C = [d for d in corrected(raw, p4[0]) if d['kind'] == 'drained']
            pairs, _, uc = greedy(merged, C, 0.8)
            for i, j in pairs:
                merged[i]['panels'].append(p4[0])
                merged[i]['r_pt_fig4'] = C[j]['r_pt']
            for j in uc:   # a disc Fig. 3 hides entirely
                if C[j]['support'] >= 0.3:
                    merged.append({'xc': C[j]['xc'], 'yc': C[j]['yc'], 'r_pt': None, 'r_pt_fig4': C[j]['r_pt'], 'panels': [p4[0]]})
        seen: dict[tuple[int, int], dict] = {}
        for m in merged:
            cell = (int(round(m['xc'])), int(round(m['yc'])))
            if cell in seen:   # two fits of one disc
                seen[cell]['panels'] = sorted(set(seen[cell]['panels']) | set(m['panels']))
                continue
            seen[cell] = {'i': cell[0], 'j': cell[1], 'kind': kind, 'panels': m['panels'],
                          'r_pt': m.get('r_pt'), 'r_pt_fig4': m.get('r_pt_fig4')}
        rows += list(seen.values())
    return rows


def main() -> None:
    raw = json.loads((DIGI_DIR / 'c18_dots_raw.json').read_text())
    tables = {day: day_table(raw, day) for day in DAYS}
    for day, rows in tables.items():
        want = {k: v for k, v in DAYS[day].items() if k != 'panels'}
        got = {k: sum(r['kind'] == k for r in rows) for k in want}
        print(day, 'caption', want, '→', got)

    # ─── track lakes across the four observation days ──────────────────
    lakes: list[dict] = []
    for day in DAYS:
        rows = tables[day]
        free = set(range(len(rows)))
        claimed: set[int] = set()
        for k, r in enumerate(rows):          # same cell
            for n, lk in enumerate(lakes):
                if n not in claimed and (r['i'], r['j']) in lk['cells']:
                    lk['history'][day] = r; claimed.add(n); free.discard(k); break
        cand = []
        for k in free:
            for n, lk in enumerate(lakes):
                if n in claimed:
                    continue
                d = min(np.hypot(rows[k]['i'] - a, rows[k]['j'] - b) for a, b in lk['cells'])
                if d <= 1.5:
                    cand.append((d, k, n))
        for d, k, n in sorted(cand):          # nearest unclaimed neighbour
            if k in free and n not in claimed:
                lakes[n]['history'][day] = rows[k]; lakes[n]['cells'].append((rows[k]['i'], rows[k]['j']))
                claimed.add(n); free.discard(k)
        for k in sorted(free):
            lakes.append({'cells': [(rows[k]['i'], rows[k]['j'])], 'history': {day: rows[k]}})

    r_max = max(r['r_pt'] for rows in tables.values() for r in rows if r['r_pt'])
    out = []
    order = sorted(lakes, key=lambda lk: (-lk['cells'][0][1], lk['cells'][0][0]))   # north → south, west → east
    for n, lk in enumerate(order, start=1):
        i, j = lk['cells'][0]
        e, nn = (C18_UTM0[0] + i) * 1e3, (C18_UTM0[1] + j) * 1e3
        lon, lat = UTM2LL.transform(e, nn)
        hist = {}
        days = list(DAYS)
        for d_i, day in enumerate(days):
            r = lk['history'].get(day)
            if r is None:
                continue
            h = {'state': r['kind'], 'cell': [r['i'], r['j']], 'panels': r['panels']}
            if r['r_pt']:
                h['volume_m3'] = round(V_MAX * (r['r_pt'] / r_max) ** 2, -4)
            if r['kind'] == 'drained':
                later = [lk['history'].get(x) for x in days[d_i + 1:]]
                nxt = days[d_i + 1] if d_i + 1 < len(days) else None
                if nxt is None:
                    h['extent'] = 'unknown'      # 10 June is the last map
                else:
                    h['extent'] = 'partial' if lk['history'].get(nxt) is not None else 'full'
            hist[day] = h
        drained_days = [d for d, h in hist.items() if h['state'] == 'drained']
        out.append({
            'id': f'C18_{n:03d}', 'i': i, 'j': j, 'utm_e': e, 'utm_n': nn,
            'lat': round(lat, 5), 'lon': round(lon, 5),
            'history': hist, 'drained_days': drained_days, 'n_drainages': len(drained_days),
        })
    n_dr = sum(1 for lk in out if lk['n_drainages'])
    print(f'{len(out)} lakes; {n_dr} drained at least once; {sum(lk["n_drainages"] for lk in out)} drainage events;',
          'drained more than once:', sum(1 for lk in out if lk['n_drainages'] > 1))
    for day in list(DAYS)[1:]:
        print('  ', day, {k: sum(1 for lk in out if lk['history'].get(day, {}).get('state') == 'drained' and lk['history'][day].get('extent') == k)
                          for k in ('full', 'partial', 'unknown')})
    (WORK / 'c18_lakes.json').write_text(json.dumps({
        'source': 'Christoffersen et al. 2018, Nat. Commun. 9:1064 — Figs. 3 and 4, digitised (the paper publishes no lake table)',
        'positions': 'centres of the model\'s 1 km grid cells (true lake centre within ~0.5 km); UTM 22N',
        'days': {d: {k: v for k, v in s.items() if k != 'panels'} for d, s in DAYS.items()},
        'volume_note': 'volume_m3 from the drawn disc area (Fig. 3 legend: 9.4e6 m³ = the largest disc) — approximate',
        'lakes': out,
    }, indent=1))


if __name__ == '__main__':
    main()
