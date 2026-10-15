"""Digitise the lakes of Christoffersen et al. 2018's 6–10 June 2010 cascade.

The paper publishes no lake coordinates (inputs "on request"; Fitzpatrick
et al. 2014 has no data supplement — checked when this was written), so the lakes are
read off its own figures. Every map panel is a 300-ppi raster inside the
PDF; each lake is a filled disc with a white rim:

  Fig. 3 (page 5)  a/b  5 June   59 lakes (black)
                   d/e  6 June   43 drained (magenta) + 16 unchanged (black)
                   g/h  7 June   30 drained            + 16 unchanged
                   j/k  10 June  51 drained (8–10 June, clouds on 8–9) + 10 unchanged
  Fig. 4 (page 6)  a / d / g     the same 43 / 30 / 51 drained lakes, on black,
                                 disc size = volume drained

Each drained set therefore exists in THREE panels with different disc sizes
(so different overlaps). A disc is recovered as a circle fitted to its
visible rim under the constraint that the visible part lies inside it
(an occluded disc shows a crescent; its distance-transform maximum is not
its centre). The panels are then cross-matched in model km.

Calibration (PyMuPDF `get_image_info` boxes + the tick labels' text boxes)
is written out below. Model km → UTM 22N is the
translation fitted in scene_01_intro/build_coupling_length.py.

  cinematic/.venv/bin/python digitise_c18.py     → digitise/c18_dots.json + QC PNGs
"""
from __future__ import annotations

import json
import subprocess

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

from common import C18_PDF, DIGI_DIR

# ─── calibration ───────────────────────────────────────────────────────
# panel → (pdfimages file, image bbox in PDF pt (x0, y0, x1, y1), x at 0 km, pt/km x, y at 0 km, pt/km y)
P5_XL = (74.90, 1.6711)     # left column: ticks 20…100 at 108.32 … 242.00 pt
P5_XR = (250.545, 1.6741)   # right column: 284.025 … 417.95 pt
P5_Y = {1: (277.41, 1.6743), 2: (395.19, 1.6760), 3: (512.70, 1.6733), 4: (630.07, 1.6733)}
PANELS = {
    '3a': ('p5-000', (86.17, 161.24, 249.17, 254.03), P5_XL, P5_Y[1]),
    '3b': ('p5-001', (262.12, 161.24, 425.36, 254.03), P5_XR, P5_Y[1]),
    '3d': ('p5-002', (86.20, 278.90, 249.44, 371.70), P5_XL, P5_Y[2]),
    '3e': ('p5-003', (262.09, 278.96, 425.09, 371.64), P5_XR, P5_Y[2]),
    '3g': ('p5-004', (85.96, 396.41, 249.20, 489.20), P5_XL, P5_Y[3]),
    '3h': ('p5-005', (261.97, 396.47, 425.21, 489.27), P5_XR, P5_Y[3]),
    '3j': ('p5-006', (86.14, 514.07, 249.14, 606.86), P5_XL, P5_Y[4]),
    '3k': ('p5-007', (262.12, 514.10, 425.12, 606.78), P5_XR, P5_Y[4]),
    # Fig. 4 (constants from build_coupling_length.py: 0.9768 / 0.9785 pt per km)
    '4a': ('p6-000', (113.65, 381.08, 232.73, 435.36), (106.93, 0.9768), (448.9, 0.9785)),
    '4d': ('p6-001', (113.68, 457.28, 232.76, 511.67), (106.93, 0.9768), (505.57 + 20 * 0.9785, 0.9785)),
    '4g': ('p6-002', (113.71, 533.60, 233.03, 588.47), (106.93, 0.9768), (601.6, 0.9785)),
}
# What each observation day's panels are, and how many discs the captions give.
DAYS = {
    '2010-06-05': {'panels': ['3a', '3b'], 'present': 59},
    '2010-06-06': {'panels': ['3d', '3e', '4a'], 'drained': 43, 'unchanged': 16},
    '2010-06-07': {'panels': ['3g', '3h', '4d'], 'drained': 30, 'unchanged': 16},
    '2010-06-10': {'panels': ['3j', '3k', '4g'], 'drained': 51, 'unchanged': 10},
}
# Legend boxes drawn inside a raster (px, x0 y0 x1 y1) — never lakes.
LEGENDS = {
    '3a': [(520, 0, 680, 52), (0, 305, 236, 387)],
    '3d': [(480, 0, 680, 78)],
    '4a': [(330, 0, 496, 40)],
    '4d': [], '4g': [],
}


def rasters() -> None:
    DIGI_DIR.mkdir(parents=True, exist_ok=True)
    for page, stem in ((5, 'p5'), (6, 'p6'), (3, 'p3')):
        if not (DIGI_DIR / f'{stem}-000.png').exists():
            subprocess.run(['pdfimages', '-f', str(page), '-l', str(page), '-png', str(C18_PDF), str(DIGI_DIR / stem)], check=True)


def px_to_km(panel: str, x: np.ndarray, y: np.ndarray, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    _, (bx0, by0, bx1, by1), (x0, sx), (y0, sy) = PANELS[panel]
    h, w = shape
    xpt = bx0 + (np.asarray(x) + 0.5) / w * (bx1 - bx0)
    ypt = by0 + (np.asarray(y) + 0.5) / h * (by1 - by0)
    return (xpt - x0) / sx, (y0 - ypt) / sy


def km_per_px(panel: str, shape: tuple[int, int]) -> float:
    _, (bx0, _, bx1, _), (_, sx), _ = PANELS[panel]
    return (bx1 - bx0) / shape[1] / sx


# ─── circle fitting ────────────────────────────────────────────────────
def circle_from3(p: np.ndarray):
    (x1, y1), (x2, y2), (x3, y3) = p
    a = np.array([[x2 - x1, y2 - y1], [x3 - x1, y3 - y1]], float)
    b = 0.5 * np.array([x2 * x2 - x1 * x1 + y2 * y2 - y1 * y1, x3 * x3 - x1 * x1 + y3 * y3 - y1 * y1])
    det = a[0, 0] * a[1, 1] - a[0, 1] * a[1, 0]
    if abs(det) < 1e-6:
        return None
    cx, cy = np.linalg.solve(a, b)
    return cx, cy, float(np.hypot(x1 - cx, y1 - cy))


def circle_ls(pts: np.ndarray):
    x, y = pts[:, 0], pts[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones(len(x))]
    sol, *_ = np.linalg.lstsq(A, x * x + y * y, rcond=None)
    cx, cy, c = sol
    return cx, cy, float(np.sqrt(max(c + cx * cx + cy * cy, 0)))


def fit_disc(region: np.ndarray, rng: np.random.Generator):
    """The circle whose disc CONTAINS the visible region and whose rim
    explains most of the region's boundary. region: bool mask (cropped).
    Returns (cx, cy, r, support) in the crop's pixel coords; support = the
    fraction of the fitted circumference that is visible boundary."""
    ys, xs = np.nonzero(region)
    area = len(xs)
    edge = region & ~ndi.binary_erosion(region)
    ey, ex = np.nonzero(edge)
    bpts = np.c_[ex, ey].astype(float)
    rpts = np.c_[xs, ys].astype(float)
    if area < 14 or len(bpts) < 8:
        r = np.sqrt(area / np.pi)
        return float(xs.mean()), float(ys.mean()), float(r), 1.0
    best = None
    n = len(bpts)
    for _ in range(700):
        c = circle_from3(bpts[rng.choice(n, 3, replace=False)])
        if c is None:
            continue
        cx, cy, r = c
        if r < 1.5 or r > 45:
            continue
        # containment: the visible part must lie inside its own disc
        if (np.hypot(rpts[:, 0] - cx, rpts[:, 1] - cy) > r + 1.0).mean() > 0.01:
            continue
        inl = np.abs(np.hypot(bpts[:, 0] - cx, bpts[:, 1] - cy) - r) <= 0.8
        s = int(inl.sum())
        if best is None or s > best[0]:
            best = (s, inl)
    if best is None:
        r = np.sqrt(area / np.pi)
        return float(xs.mean()), float(ys.mean()), float(r), 0.0
    inl = best[1]
    for _ in range(3):  # least-squares refine on the inliers
        cx, cy, r = circle_ls(bpts[inl])
        inl2 = np.abs(np.hypot(bpts[:, 0] - cx, bpts[:, 1] - cy) - r) <= 0.8
        if inl2.sum() < 5:
            break
        inl = inl2
    support = float(inl.sum() / max(2 * np.pi * r, 1.0))
    return float(cx), float(cy), float(r), min(support, 1.0)


def find_discs(mask: np.ndarray, seed: int = 0) -> list[dict]:
    """Every disc of one colour in a panel: one circle per connected visible
    piece, then pieces of the same disc merged."""
    rng = np.random.default_rng(seed)
    lab, n = ndi.label(mask)  # 4-connected: a 1-px white rim separates overlapping discs
    out = []
    for i, sl in enumerate(ndi.find_objects(lab), start=1):
        reg = lab[sl] == i
        if reg.sum() < 5:
            continue
        pad = np.pad(reg, 2)
        cx, cy, r, sup = fit_disc(pad, rng)
        out.append({'x': cx - 2 + sl[1].start, 'y': cy - 2 + sl[0].start, 'r': r, 'support': sup, 'area': int(reg.sum())})
    # merge pieces that fitted the same circle (a disc cut in two by a disc on top of it)
    out.sort(key=lambda d: -d['area'])
    kept: list[dict] = []
    for d in out:
        for k in kept:
            if np.hypot(d['x'] - k['x'], d['y'] - k['y']) < 0.35 * max(d['r'], k['r']) + 1.0 and abs(d['r'] - k['r']) < 0.3 * max(d['r'], k['r']) + 1.0:
                k['area'] += d['area']
                break
        else:
            kept.append(d)
    return kept


def masks(im: np.ndarray, panel: str) -> tuple[np.ndarray, np.ndarray]:
    """(magenta fill, black fill) masks with the legends blanked."""
    r, g, b = (im[..., i].astype(int) for i in range(3))
    mag = (r > 185) & (g < 115) & (b > 185)
    blk = (r < 45) & (g < 45) & (b < 45)
    for x0, y0, x1, y1 in LEGENDS.get(panel, []):
        mag[y0:y1, x0:x1] = False
        blk[y0:y1, x0:x1] = False
    return mag, blk


def white_rim_fraction(im: np.ndarray, reg_mask: np.ndarray) -> float:
    """Fraction of the 2-px ring just outside a region that is white-ish
    (a lake disc is always rimmed white; a dark patch of the map is not)."""
    ring = ndi.binary_dilation(reg_mask, iterations=2) & ~reg_mask
    if not ring.any():
        return 0.0
    return float((im[ring].min(axis=1) > 150).mean())


def find_black(im: np.ndarray, blk: np.ndarray) -> list[dict]:
    lab, _ = ndi.label(blk)
    keep = np.zeros_like(blk)
    for i, sl in enumerate(ndi.find_objects(lab), start=1):
        reg = lab[sl] == i
        a = int(reg.sum())
        if a < 5 or a > 2600:
            continue
        y0, y1 = max(sl[0].start - 3, 0), min(sl[0].stop + 3, blk.shape[0])
        x0, x1 = max(sl[1].start - 3, 0), min(sl[1].stop + 3, blk.shape[1])
        sub = lab[y0:y1, x0:x1] == i
        if white_rim_fraction(im[y0:y1, x0:x1], sub) >= 0.72:
            keep[sl] |= reg
    return find_discs(keep, seed=1)


def circ_offset(v: np.ndarray) -> float:
    """Where the 1-km grid sits in a panel's axis (the circular mean of the
    fractional parts): the tick-label calibration is good to ~0.2 km."""
    return float(np.angle(np.exp(2j * np.pi * v).mean()) / (2 * np.pi))


def main() -> None:
    rasters()
    raw: dict[str, list[dict]] = {}
    for panel, (stem, *_rest) in PANELS.items():
        im = np.asarray(Image.open(DIGI_DIR / f'{stem}.png').convert('RGB'))
        mag, blk = masks(im, panel)
        s = km_per_px(panel, im.shape[:2])
        discs = []
        found = []
        if panel not in ('3a', '3b'):
            found += [('drained', d) for d in find_discs(mag)]
        if panel.startswith('3'):
            found += [('present' if panel in ('3a', '3b') else 'unchanged', d) for d in find_black(im, blk)]
        for kind, d in found:
            xk, yk = px_to_km(panel, d['x'], d['y'], im.shape[:2])
            discs.append({**d, 'kind': kind, 'x_km': float(xk), 'y_km': float(yk), 'r_km': d['r'] * s,
                          'r_pt': d['r'] / 300 * 72})
        # the panel's grid offset, from its well-fitted discs
        good = [d for d in discs if d['support'] >= 0.5]
        ox = circ_offset(np.array([d['x_km'] for d in good]))
        oy = circ_offset(np.array([d['y_km'] for d in good]))
        for d in discs:
            d['i'] = int(round(d['x_km'] - ox))
            d['j'] = int(round(d['y_km'] - oy))
            d['res_km'] = float(np.hypot(d['x_km'] - ox - d['i'], d['y_km'] - oy - d['j']))
        raw[panel] = discs
        # QC: the raster ×4 with every fitted circle
        z = 4
        qc = Image.fromarray(im).resize((im.shape[1] * z, im.shape[0] * z), Image.NEAREST)
        dr = ImageDraw.Draw(qc)
        for d in discs:
            cx, cy, r = (d['x'] + 0.5) * z, (d['y'] + 0.5) * z, d['r'] * z
            col = (0, 255, 255) if d['kind'] == 'drained' else (255, 160, 0)
            if d['support'] < 0.35:
                col = (255, 255, 0)
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=2)
            dr.line([cx - 5, cy, cx + 5, cy], fill=col, width=2)
            dr.line([cx, cy - 5, cx, cy + 5], fill=col, width=2)
        qc.save(DIGI_DIR / f'qc_{panel}.png')
        n = {k: sum(d['kind'] == k for d in discs) for k in ('present', 'drained', 'unchanged')}
        print(f"{panel}: {n}  grid offset ({ox:+.2f}, {oy:+.2f}) km, residual to grid median "
              f"{np.median([d['res_km'] for d in discs]):.2f} max {max(d['res_km'] for d in discs):.2f}")
    (DIGI_DIR / 'c18_dots_raw.json').write_text(json.dumps(raw, indent=1))

    # ─── one table per observation day: the union of its panels, on the grid ──
    days = {}
    for day, spec in DAYS.items():
        cells: dict[tuple[int, int, str], dict] = {}
        for panel in spec['panels']:
            for d in raw[panel]:
                key = (d['i'], d['j'], d['kind'])
                c = cells.setdefault(key, {'i': d['i'], 'j': d['j'], 'kind': d['kind'], 'panels': [], 'r_pt': {}, 'support': {}})
                if panel in c['panels']:
                    c.setdefault('dup', []).append(panel)   # two discs of one panel on one cell
                    continue
                c['panels'].append(panel)
                c['r_pt'][panel] = round(d['r_pt'], 3)
                c['support'][panel] = round(d['support'], 2)
        rows = sorted(cells.values(), key=lambda c: (c['kind'], c['i'], c['j']))
        days[day] = rows
        want = {k: v for k, v in spec.items() if k != 'panels'}
        got = {k: sum(c['kind'] == k for c in rows) for k in want}
        single = [(c['i'], c['j'], c['kind'], c['panels']) for c in rows if len(c['panels']) == 1]
        print(day, 'caption', want, '→ digitised', got)
        if single:
            print('   seen in ONE panel only:', single)
    (DIGI_DIR / 'c18_dots.json').write_text(json.dumps({
        'source': 'Christoffersen et al. 2018, Nat. Commun. 9:1064, Figs. 3 and 4 (digitised; lakes sit on the model 1 km grid)',
        'frame': 'i, j = model km (x east, y north); UTM 22N km = (523.25 + i, 7404.0 + j) before refinement',
        'days': days,
    }, indent=1))


if __name__ == '__main__':
    main()
