#!/usr/bin/env python3
"""Menu-card thumbnail assets.

The Chapter 2 card renders the PNAS simulation domain of the main-text
lake (CW2019_2511) as a small 3-D block that turns through the pre- and
post-drainage Sentinel-2 faces and the elastic / viscous responses. The
chapter's own 1024² tiles are ~1.4 MB for the set; a menu thumbnail needs
a fraction of that, so this bakes thumb-sized copies:

  menu/ch02/dem_256.png    RG16 surface DEM, 1024 → 256 by averaging the
                           decoded 16-bit heights (never the bytes), then
                           re-encoded R = hi, G = lo, A = footprint
  menu/ch02/s2pre_512.jpg  Sentinel-2 truecolor, 18 Aug 2019 (lake full)
  menu/ch02/s2post_512.jpg Sentinel-2 truecolor, 23 Aug 2019 (drained)
  menu/ch02/e_512.png      elastic response, with patch (RGBA drape)
  menu/ch02/v_512.png      viscous response, with patch (RGBA drape)

Reads only the repo's R2 mirror (website/.r2-cache/ch02/sim — copies,
never the original source files) and writes into the mirror under menu/ch02/.
Upload:  rclone copy website/.r2-cache/menu/ch02 r2:<bucket>/menu/ch02 --header-upload 'Cache-Control: public, max-age=31536000, immutable'
New filenames, so no ASSET_VERSION bump.

The Chapter 1 card (the director asked that it show exactly what the
chapter shows later, at its curve-collapse moment) is a
miniature of TheoryPanel's collapse: `bake_ch01_collapse()` writes the
chapter's own run set (the δ ≤ 0.3 profile subset, 36 runs), its marker
vertices, its dimensional y-range and the master curve, thinned by
Douglas–Peucker at a third of a 2×-card pixel, to
menu/ch01/collapse_thumb.json (~41 kB). (The earlier card's
menu/ch01/ensemble_thumb.json — all 69 runs, every 6th sample — is
retired; it stays on R2 untouched.)
Upload:  rclone copy website/.r2-cache/menu/ch01/collapse_thumb.json r2:<bucket>/menu/ch01/ --header-upload 'Cache-Control: public, max-age=31536000, immutable'
"""
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'website' / '.r2-cache' / 'ch02' / 'sim'
OUT = ROOT / 'website' / '.r2-cache' / 'menu' / 'ch02'
LAKE = 'CW2019_2511'  # SectionCh2's DEFAULT_LAKE — the main-text Fig. 1 lake


def downsample_rg16(src: Path, dst: Path, factor: int) -> None:
    im = np.array(Image.open(src).convert('RGBA'))
    h, w = im.shape[:2]
    u16 = im[..., 0].astype(np.float64) * 256 + im[..., 1]
    a = im[..., 3].astype(np.float64)
    hh, ww = h // factor, w // factor
    u = u16[: hh * factor, : ww * factor].reshape(hh, factor, ww, factor).mean(axis=(1, 3))
    aa = a[: hh * factor, : ww * factor].reshape(hh, factor, ww, factor).mean(axis=(1, 3))
    u = np.clip(np.round(u), 0, 65535).astype(np.uint32)
    out = np.zeros((hh, ww, 4), np.uint8)
    out[..., 0] = u >> 8
    out[..., 1] = u & 255
    out[..., 3] = np.clip(np.round(aa), 0, 255).astype(np.uint8)
    Image.fromarray(out, 'RGBA').save(dst, optimize=True)
    print(f'  {dst.name}: {w}×{h} → {ww}×{hh}, heights {u.min()/65535*3500:.0f}–{u.max()/65535*3500:.0f} m, {dst.stat().st_size/1024:.0f} KB')


def resize(src: Path, dst: Path, size: int, **save) -> None:
    im = Image.open(src)
    im = im.resize((size, size), Image.LANCZOS)
    if dst.suffix == '.jpg':
        im = im.convert('RGB')
    im.save(dst, **save)
    print(f'  {dst.name}: {dst.stat().st_size/1024:.0f} KB')


def _rdp(pts: np.ndarray, eps: float) -> list[int]:
    """Ramer–Douglas–Peucker: indices of the vertices to keep."""
    keep = {0, len(pts) - 1}
    stack = [(0, len(pts) - 1)]
    while stack:
        i0, i1 = stack.pop()
        if i1 <= i0 + 1:
            continue
        a, b = pts[i0], pts[i1]
        ab = b - a
        L = np.hypot(*ab)
        seg = pts[i0 + 1:i1] - a
        if L < 1e-12:
            dist = np.hypot(seg[:, 0], seg[:, 1])
        else:
            dist = np.abs(ab[0] * seg[:, 1] - ab[1] * seg[:, 0]) / L
        k = int(np.argmax(dist))
        if dist[k] > eps:
            m = i0 + 1 + k
            keep.add(m)
            stack += [(i0, m), (m, i1)]
    return sorted(keep)


def bake_ch01_collapse() -> None:
    """theory_n1.json → menu/ch01/collapse_thumb.json.

    The director asked that the card show exactly what the chapter shows
    later, at its curve-collapse moment. So the card takes the
    SAME run set TheoryPanel's stages 4–5 draw (the δ ≤ 0.3 profile
    subset, 36 runs), the same marker vertices (the panel's rule: every
    max(12, ⌊n/9⌋)-th sample), the same dimensional y-range
    (⌈1.08·max|τ|/100⌉·100 kPa) and the master curve. Each polyline is
    thinned by Douglas–Peucker in BOTH frames the thumb draws it in (the
    ±40 km / kPa frame and the composite x̂ / τ̂ frame), measured in
    device pixels of a 2× card (~1040 × 300), so the drawn curves are
    the chapter's to within a third of a pixel at any collapse phase.
    """
    import json
    src = ROOT / 'website' / '.r2-cache' / 'ch01' / 'theory_n1.json'
    dst = ROOT / 'website' / '.r2-cache' / 'menu' / 'ch01' / 'collapse_thumb.json'
    dst.parent.mkdir(parents=True, exist_ok=True)
    d = json.load(open(src))
    runs_src = [r for r in d['ensemble'] if r['delta'] <= 0.3]
    ymax = float(np.ceil(max(r['max_tau_kpa'] for r in runs_src) * 1.08 / 100) * 100)
    PX_W, PX_H, EPS = 1040.0, 300.0, 0.3  # 2× card plot box, device px
    ZUP, ZMID = 0.40, 0.24  # TheoryPanel's composite zones
    runs = []
    total = 0
    for r in runs_src:
        x = np.asarray(r['x_km'], float)
        t = np.asarray(r['tau_kpa'], float)
        n = len(x)
        half = r['ell_m'] / 2
        xm = x * 1e3
        up = xm < -half
        dn = xm > half
        u_nd = np.where(up, ZUP * (np.maximum(-7.5, (xm + half) / r['xscale_m']) + 6) / 6,
               np.where(dn, ZUP + ZMID + (1 - ZUP - ZMID) * np.minimum(7.5, (xm - half) / r['xscale_m']) / 6,
                        ZUP + ZMID * (xm + half) / r['ell_m']))
        v_nd = (t / r['tauscale_kpa']) / 1.35
        u_d = (x + 40) / 80
        v_d = t / ymax
        keep = set(_rdp(np.c_[u_d * PX_W, v_d * PX_H / 2], EPS))
        keep |= set(_rdp(np.c_[u_nd * PX_W, v_nd * PX_H / 2], EPS))
        step = max(12, n // 9)  # TheoryPanel.runMarkers
        marks = list(range(step, n - 2, step))
        keep |= set(marks)
        # the patch edges exactly (the composite axis breaks there)
        keep |= {i for i in range(n) if abs(abs(xm[i]) - half) < 1.0}
        keep = sorted(keep)
        pos = {k: j for j, k in enumerate(keep)}
        runs.append({
            'h': r['h'], 'a': r['alpha_deg'], 'g': r['gamma'], 'l': r['ell_m'],
            'xs': round(r['xscale_m'], 2), 'ts': round(r['tauscale_kpa'], 3),
            'x': [round(float(x[i]), 3) for i in keep],
            't': [round(float(t[i]), 3) for i in keep],
            'm': [pos[i] for i in marks],
        })
        total += len(keep)
    out = {'ymax_kpa': ymax, 'runs': runs,
           'master': {k: [round(v, 4) for v in d['master'][k]] for k in d['master']}}
    json.dump(out, open(dst, 'w'), separators=(',', ':'))
    print(f'  {dst.name}: {len(runs)} runs (δ ≤ 0.3), {total} pts, y ±{ymax:.0f} kPa, '
          f'{dst.stat().st_size / 1024:.0f} KB')


def main() -> None:
    bake_ch01_collapse()
    OUT.mkdir(parents=True, exist_ok=True)
    print(f'menu/ch02 from {LAKE}:')
    downsample_rg16(SRC / f'simdem_{LAKE}_rg16.png', OUT / 'dem_256.png', 4)
    resize(SRC / f'sims2pre_{LAKE}.jpg', OUT / 's2pre_512.jpg', 512, quality=86)
    resize(SRC / f'sims2post_{LAKE}.jpg', OUT / 's2post_512.jpg', 512, quality=86)
    resize(SRC / f'simstress_e_patch_{LAKE}.png', OUT / 'e_512.png', 512, optimize=True)
    resize(SRC / f'simstress_v_patch_{LAKE}.png', OUT / 'v_512.png', 512, optimize=True)


if __name__ == '__main__':
    main()
