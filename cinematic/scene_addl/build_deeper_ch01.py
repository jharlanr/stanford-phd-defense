#!/usr/bin/env python
"""Bake the figures of the Additional-Work "deeper dive" page for Chapter 1
(/additional-work/deeper/chapter1 — the director's backup slides for the
committee: the n = 3 results and the paper's other figures the talk does
not cover).

Source = the JoG paper's OWN figure files, the accepted version
(JOG-2026-0047, "202607_final"), copied by cinematic/fetch_sources.sh into
  cinematic/source_data/manuscript_jog/final/figs/*.png
The originals on the lab Drive are never read here.

Every output is a figure of the paper, whole or cropped along its own
white gutters. Four are split so each piece fits one screen at a legible
scale (Figs 2, 4, 5, B1); where a piece loses the figure's shared key
(the h / α / γ legend strip at the bottom of Figs 4 and B1) that strip is
appended beneath it, unchanged. Fig. 2's two velocity-profile panels
(c, f; one above the other in the paper) are set side by side. Nothing is
redrawn, relabelled or recoloured. Crop boxes are pixel rows/columns of
the source PNGs, found as all-white gutters (see the box comments).

Outputs: cinematic/output/deeper/ch01/*.webp  (<= 2000 px wide, q 90)
  ->  R2 addl/deeper/ch01/<same name>

Run:  ./cinematic/.venv/bin/python cinematic/scene_addl/build_deeper_ch01.py
then  cp cinematic/output/deeper/ch01/*.webp website/.r2-cache/addl/deeper/ch01/
      rclone copy cinematic/output/deeper/ch01/ r2:<bucket>/addl/deeper/ch01/ --checksum --header-upload 'Cache-Control: public, max-age=31536000, immutable'
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'cinematic' / 'source_data' / 'manuscript_jog' / 'final' / 'figs'
OUT = ROOT / 'cinematic' / 'output' / 'deeper' / 'ch01'

MAX_W = 2000
QUALITY = 90
WHITE = 245  # a pixel brighter than this counts as paper
PAD = 0.012  # margin around the trimmed content, as a fraction of its width


def load(name: str) -> Image.Image:
    p = SRC / name
    if not p.exists():
        raise SystemExit(f'missing {p} — run cinematic/fetch_sources.sh (JOG FINAL block)')
    im = Image.open(p)
    # Flatten any alpha onto white paper.
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA')
        bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    return im.convert('RGB')


def trim(im: Image.Image) -> Image.Image:
    """Crop to the non-white content, then pad evenly with white."""
    a = np.asarray(im.convert('L'))
    ys, xs = np.where(a <= WHITE)
    box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    im = im.crop(box)
    pad = max(8, round(PAD * im.width))
    out = Image.new('RGB', (im.width + 2 * pad, im.height + 2 * pad), 'white')
    out.paste(im, (pad, pad))
    return out


def vstack(parts: list[Image.Image], gap: int = 0) -> Image.Image:
    w = max(p.width for p in parts)
    h = sum(p.height for p in parts) + gap * (len(parts) - 1)
    out = Image.new('RGB', (w, h), 'white')
    y = 0
    for p in parts:
        out.paste(p, ((w - p.width) // 2, y))
        y += p.height + gap
    return out


def hstack(parts: list[Image.Image], gap: int = 0) -> Image.Image:
    w = sum(p.width for p in parts) + gap * (len(parts) - 1)
    h = max(p.height for p in parts)
    out = Image.new('RGB', (w, h), 'white')
    x = 0
    for p in parts:
        out.paste(p, (x, (h - p.height) // 2))
        x += p.width + gap
    return out


def save(im: Image.Image, name: str) -> None:
    im = trim(im)
    if im.width > MAX_W:
        im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / f'{name}.webp'
    im.save(dst, 'WEBP', quality=QUALITY, method=6)
    print(f'{dst.name:34s} {im.width:5d} x {im.height:<5d} {dst.stat().st_size / 1024:7.0f} kB')


def main() -> None:
    # Fig. 1 — the schematic, whole.
    save(load('fig01_schematic.png'), 'fig01_schematic')

    # Fig. 2 (4621 x 2113). Columns a/b vs c: white gutter x 3298–3387.
    # Rows: suptitle y 32–106 (dropped — the caption carries h, α, ℓ, γ).
    # Column c/f split between c's x-label and f's title: white y 1151–1154.
    f2 = load('fig02_domain.png')
    save(f2.crop((0, 200, 3330, 2090)), 'fig02_fields')
    c = f2.crop((3340, 200, f2.width, 1152))
    f = f2.crop((3340, 1153, f2.width, 2090))
    save(hstack([trim(c), trim(f)], gap=60), 'fig02_sia_profiles')

    # Fig. 3 (4126 x 2341) — whole: fits one screen.
    save(load('fig03_surfstress.png'), 'fig03_surface_stress')

    # Fig. 4 (4116 x 3355). Suptitle ≤ 104; rows 1–2 end before the white
    # band y 1968–2183; the log-log row ends before y 3189–3240; the key
    # strip is y 3240–3327.
    f4 = load('fig04_dastress.png')
    key4 = f4.crop((0, 3236, f4.width, 3335))
    save(vstack([f4.crop((0, 150, f4.width, 1990)), key4], gap=40), 'fig04_profiles_collapse')
    save(vstack([f4.crop((0, 2150, f4.width, 3200)), key4], gap=20), 'fig04_loglog')

    # Fig. B1 (5555 x 4756). Suptitle ≤ 113; n = 1 block y 373–2220
    # (white y 2220–2516); n = 3 block y 2516–4363 (white 4363–4611); key
    # strip y 4611–4728.
    fb = load('figB1_velo.png')
    keyb = fb.crop((0, 4600, fb.width, 4740))
    save(vstack([fb.crop((0, 360, fb.width, 2225)), keyb], gap=60), 'figB1_velocity_n1')
    save(vstack([fb.crop((0, 2500, fb.width, 4370)), keyb], gap=60), 'figB1_velocity_n3')

    # Fig. 5 (4078 x 3254). Suptitle y 32–106 and the "Top: fixed ℓ |
    # Bottom: fixed α" line y 151–209 dropped (the titles say it); row 1
    # (a, b) y 216–1682, row 2 (c, d) y 1756–3222.
    f5 = load('fig05_phasespace.png')
    save(f5.crop((0, 212, f5.width, 1700)), 'fig05_acl_h_alpha')
    save(f5.crop((0, 1740, f5.width, 3240)), 'fig05_acl_h_ell')

    # Figs 6, 7, A1, C1 — whole.
    save(load('fig06_topopaint.png'), 'fig06_ice_sheet_profile')
    save(load('fig07_aclcomp.png'), 'fig07_acl_vs_n')
    save(load('figA1_combined.png'), 'figA1_greenland_n3')
    save(load('figC1_collapsedelta.png'), 'figC1_collapse_delta')


if __name__ == '__main__':
    main()
