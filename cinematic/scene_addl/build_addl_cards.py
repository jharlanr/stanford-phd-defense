#!/usr/bin/env python
"""Bake the SQUARE card thumbnails for /additional-work (the director asked
for square thumbs on every card, the Cape Smith stack for the C&G paper, and
the translucent sim block ticking through the ten beds for the glaciology
application).

Inputs — project copies only, originals never touched:
  cinematic/source_data/cg_paper/figA1_prospectivity.png   C&G Fig. A.1 (copied by
      cinematic/scene_addl/fetch_sources.sh); panel (a) = stacked MGSIM
      realizations on the Cape Smith Belt
  cinematic/source_data/tbs/aiexplained_Spuza-KwTJ4_0205-0235.mp4   the AI Explained
      clip; the "One Greenland lake across a 153-day season" panel at 2:22
  cinematic/source_data/essd/figs/fig7_architecture.png    ESSD Fig. 7 (the JSTARS card)
  cinematic/source_data/cop27/unfccc_cop27_lossanddamage_kiaraworth-35.jpg
      the C-PREE article's headline image (fetched by the same fetch_sources.sh)
  cinematic/scene_addl/output_addl_cards/bed_prism_NN.png  raw square crops of the
      glassy block, one per bed, from website/tools/render_bed_thumbs.mjs

Outputs: cinematic/scene_addl/output_addl_cards/  →  R2 addl/cards/
  cg_capesmith_sq.webp  1200×1200, TRANSPARENT (the stack floats on the card's dark ground;
                        the '(a) MGSIM Realizations' panel label is erased)
  tbs_lakes_sq.jpg      900×900
  jstars_arch_sq.jpg    900×900
  cop27_sideevent_sq.jpg  900×900 (a plain CENTRE crop of the headline image, as the director asked)
  bed_prism_NN.jpg      720×720 ×10 (only if the raw PNG frames exist)

Run:  ./cinematic/.venv/bin/python cinematic/scene_addl/build_addl_cards.py
then  rsync -a --include='*.jpg' --include='*.webp' --exclude='*' cinematic/scene_addl/output_addl_cards/ website/.r2-cache/addl/cards/
      rclone copy cinematic/scene_addl/output_addl_cards/ r2:<bucket>/addl/cards/ --include '*.jpg' --include '*.webp' --checksum --header-upload 'Cache-Control: public, max-age=31536000, immutable'
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'cinematic' / 'source_data'
OUT = ROOT / 'cinematic' / 'scene_addl' / 'output_addl_cards'
FIGA1 = SRC / 'cg_paper' / 'figA1_prospectivity.png'
CLIP = SRC / 'tbs' / 'aiexplained_Spuza-KwTJ4_0205-0235.mp4'
ARCH = SRC / 'essd' / 'figs' / 'fig7_architecture.png'
COP27 = SRC / 'cop27' / 'unfccc_cop27_lossanddamage_kiaraworth-35.jpg'


def ffmpeg(*args: str) -> None:
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', *args], check=True)


def size(f: Path) -> str:
    return subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                           '-of', 'csv=p=0', str(f)], capture_output=True, text=True, check=True).stdout.strip()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for f in (FIGA1, CLIP, ARCH, COP27):
        assert f.is_file(), f'missing {f} — run the fetch scripts'

    # C&G Fig. A.1 panel (a): the stacked realizations, without the colorbar.
    # Source is 3957×4271; the stack sits at x≈250–1700, y≈40–930. Crop, pad to
    # a transparent square, erase the label, scale to 1200 (PIL; the PNG has alpha).
    from PIL import Image
    fig = Image.open(FIGA1).convert('RGBA')
    crop = fig.crop((250, 40, 250 + 1450, 40 + 890))
    # '(a) MGSIM Realizations' sits in the top-left of the crop, above the
    # stack's first outline (which starts ~y 90): clear that rectangle.
    crop.paste((0, 0, 0, 0), (0, 0, 780, 80))
    # The panel's own background is OPAQUE white (alpha is 0 only outside the
    # axes): key near-white to transparent, ramping from grey 200 to white so
    # the anti-aliased outline edges keep their coverage.
    px = crop.load()
    for y in range(crop.height):
        for x in range(crop.width):
            r, g, b, a = px[x, y]
            m = min(r, g, b)
            if a and m > 200:
                px[x, y] = (r, g, b, min(a, int(255 - (m - 200) * 255 / 55)))
    sq = Image.new('RGBA', (1450, 1450), (0, 0, 0, 0))
    sq.paste(crop, (0, 280))
    sq.resize((1200, 1200), Image.LANCZOS).save(OUT / 'cg_capesmith_sq.webp', 'WEBP', quality=90, method=6)
    (OUT / 'cg_capesmith_sq.jpg').unlink(missing_ok=True)

    # AI Explained frame at 2:22: the dark "153-day season" panel (x 745–1845,
    # y 80–820 in the 1920×1080 frame) — a 740² window on its left side keeps
    # the panel title and three columns of lake frames.
    ffmpeg('-ss', '17', '-i', str(CLIP), '-frames:v', '1', '-vf', 'crop=740:740:745:80,scale=900:900',
           '-q:v', '2', str(OUT / 'tbs_lakes_sq.jpg'))

    # ESSD Fig. 7: the imagery stream (FrontCNN → ConvLSTM → pool) as a square.
    w, h = (int(v) for v in size(ARCH).split(','))
    side = int(h * 0.80)   # drop the figure title band and the bottom margin
    x0 = int(w * 0.19)     # the imagery stream: FrontCNN → ConvLSTM → pool
    y0 = int(h * 0.14)
    # The PNG is transparent: composite the crop onto white before the JPEG.
    ffmpeg('-i', str(ARCH), '-filter_complex',
           f'color=c=white:s={side}x{side}[bg];[0]crop={side}:{side}:{x0}:{y0}[fg];[bg][fg]overlay=0:0,format=rgb24,scale=900:900',
           '-frames:v', '1', '-q:v', '3', str(OUT / 'jstars_arch_sq.jpg'))

    # The COP27 card's thumbnail: the C-PREE article's headline image,
    # centre-cropped square (the centre crop is the version the director
    # asked for). The original is 2048×1365, so the crop is the full height and
    # a 1365-wide window centred on it: podium, the "United Nations Climate
    # Change" wall, and the side-event audience all survive it. No colour or
    # tonal edit — it is someone else's photograph (UNFCCC Flickr / Kiara Worth).
    cw, ch = (int(v) for v in size(COP27).split(','))
    ffmpeg('-i', str(COP27), '-vf', f'crop={ch}:{ch}:{(cw - ch) // 2}:0,scale=900:900',
           '-frames:v', '1', '-q:v', '3', str(OUT / 'cop27_sideevent_sq.jpg'))

    frames = sorted(OUT.glob('bed_prism_??.png'))
    if frames:
        for f in frames:
            ffmpeg('-i', str(f), '-vf', 'scale=720:720', '-q:v', '4', str(f.with_suffix('.jpg')))
    else:
        print('WARN: no bed_prism_NN.png yet — run website/tools/render_bed_thumbs.mjs first')

    for f in sorted(OUT.glob('*.jpg')):
        print(f'{f.name:22s} {size(f):>10s}  {f.stat().st_size / 1024:6.0f} KB')


if __name__ == '__main__':
    main()
