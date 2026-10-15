#!/usr/bin/env python
"""Bake the Additional-Work "deeper dive" page for Chapter 3
(/additional-work/deeper/chapter3 — the director asked that the Chapter 3
deeper dive carry every figure of the most recent ESSD revised
submission).

The paper: Rines et al., ESSD, essd-2026-406, MANUSCRIPT VERSION 3 (the
September 2026 revision — the one Chapter 3 of the site is built on). Its ten
figure files, whole: flattened onto white, trimmed to their own white
gutters, long side <= 2400 px, WebP. Names carry the version
(essd_v3_<file>.webp) so a later revision gets new R2 keys, never changed
bytes under an old one.

manifest.json records, per figure: the source file and its pixel size, the
baked size, and the caption — the version-3 PDF's (the authority: the
Sep-20 tex still carries "TO BE REGENERATED" placeholders for Appendix B)
with the tex caption beside it where the tex has a real one.

Inputs (a working copy — never the research tree itself; "copy, never
touch originals"):
  cinematic/source_data/manuscript_essd/revision_v3/figures/*.png
  cinematic/source_data/manuscript_essd/revision_v3/main_blue_20260920.tex
  cinematic/source_data/manuscript_essd/essd-2026-406-manuscript-version3.pdf
copied from ${SOURCE_ROOT}/lakes/2026/essd/paper/revision01_202609/
{figures,drafts}/ (the private research tree).

Outputs: cinematic/output/deeper/ch03/{figs/*.webp, manifest.json}
  -> R2 addl/deeper/ch03/

Run (any checkout root, the cinematic venv):
  python cinematic/scene_addl/build_deeper_ch03.py [--fig fig4_classes]
then
  rclone copy cinematic/output/deeper/ch03/ r2:<bucket>/addl/deeper/ch03/ --checksum --header-upload 'Cache-Control: public, max-age=31536000, immutable'
  (and the same into website/.r2-cache/addl/deeper/ch03/ for dev)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'cinematic'))
from shared import SOURCE_DATA, require_source  # noqa: E402

MS = SOURCE_DATA / 'manuscript_essd'
V3 = MS / 'revision_v3'
FIG_DIR = V3 / 'figures'
TEX = V3 / 'main_blue_20260920.tex'
PDF = MS / 'essd-2026-406-manuscript-version3.pdf'
OUT = ROOT / 'cinematic' / 'output' / 'deeper' / 'ch03'

PREFIX = 'essd_v3_'
WHITE = 245
MAX_SIDE = 2400

# source file stem -> the paper's figure number (PDF order).
FIGURES = {
    'fig1_study_area': '1',
    'fig2_datapipeline': '2',
    'fig3_masking': '3',
    'fig4_classes': '4',
    'fig5_gui': '5',
    'fig6_irr': '6',
    'fig7_architecture': '7',
    'figB1_map': 'B1',
    'figB2_training': 'B2',
    'figB3_confusion_matrices': 'B3',
}


def load_png(p: Path):
    from PIL import Image
    require_source(p)
    im = Image.open(p)
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA')
        bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    return im.convert('RGB')


def trim(im, pad_frac: float = 0.012):
    from PIL import Image
    a = np.asarray(im.convert('L'))
    ys, xs = np.where(a <= WHITE)
    im = im.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    pad = max(8, round(pad_frac * max(im.size)))
    out = Image.new('RGB', (im.width + 2 * pad, im.height + 2 * pad), 'white')
    out.paste(im, (pad, pad))
    return out


def save_fig(im, name: str) -> tuple[int, int]:
    from PIL import Image
    im = trim(im)
    s = MAX_SIDE / max(im.size)
    if s < 1:
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    d = OUT / 'figs'
    d.mkdir(parents=True, exist_ok=True)
    dst = d / f'{PREFIX}{name}.webp'
    im.save(dst, 'WEBP', quality=90, method=6)
    print(f'{dst.name:44s} {im.width:5d} x {im.height:<5d} {dst.stat().st_size / 1024:7.0f} kB')
    return im.size


def pdf_captions() -> dict[str, str]:
    """'Figure N. …' paragraphs of the version-3 PDF (text layer)."""
    require_source(PDF)
    txt = subprocess.run(['pdftotext', str(PDF), '-'], check=True, capture_output=True, text=True).stdout
    caps = {}
    for m in re.finditer(r'^\f?Figure (B?\d+)\. (.+?)(?:\n\s*\n|\Z)', txt, re.M | re.S):
        num = m.group(1)
        if num in caps:
            continue
        # A caption ends on a full stop at a line end; a following line that
        # starts lowercase is body text carried over a page break (Fig. B3
        # runs straight into the acknowledgements otherwise).
        lines = m.group(2).split('\n')
        for i in range(len(lines) - 1):
            if lines[i].rstrip().endswith('.') and lines[i + 1][:1].islower():
                lines = lines[:i + 1]
                break
        caps[num] = re.sub(r'\s+', ' ', ' '.join(lines)).strip()
    return caps


def tex_captions() -> dict[str, str]:
    """\\caption{…} of each \\includegraphics in the tex, by file stem
    (placeholders included — the PDF caption is the one the page uses)."""
    require_source(TEX)
    tex = TEX.read_text()
    caps = {}
    for m in re.finditer(r'^\\includegraphics[^{]*\{[^}]*/([^/}]+)\.png\}\s*\\caption\{', tex, re.M):
        i, depth = m.end(), 1
        while depth:
            depth += {'{': 1, '}': -1}.get(tex[i], 0)
            i += 1
        caps[m.group(1)] = re.sub(r'\s+', ' ', tex[m.end():i - 1]).strip()
    return caps


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--fig', choices=list(FIGURES))
    a = ap.parse_args()
    pcap, tcap = pdf_captions(), tex_captions()
    man_path = OUT / 'manifest.json'
    manifest = json.loads(man_path.read_text()) if man_path.exists() else {}
    for stem, num in FIGURES.items():
        if a.fig and a.fig != stem:
            continue
        src = FIG_DIR / f'{stem}.png'
        im = load_png(src)
        src_size = im.size
        size = save_fig(im, stem)
        manifest[f'figs/{PREFIX}{stem}.webp'] = {
            'figure': f'Fig. {num}',
            'source': str(src.relative_to(SOURCE_DATA)),
            'source_size': list(src_size),
            'size': list(size),
            'caption_pdf_v3': pcap.get(num),
            'caption_tex_20260920': tcap.get(stem),
        }
        if not pcap.get(num):
            print(f'  ! no PDF caption found for Fig. {num}')
    OUT.mkdir(parents=True, exist_ok=True)
    man_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({v['figure']: v['size'] for v in manifest.values()}))


if __name__ == '__main__':
    main()
