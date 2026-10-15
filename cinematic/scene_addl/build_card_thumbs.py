#!/usr/bin/env python
"""Three Additional-Work card thumbnails (the director asked for slick
thumbnails on the persistent-IDs, lake-label and deep-learning-classifier
cards).

Each card thumb is a square, faded until hovered; a ticking one is a short
run of frames that AddlCycleThumb.vue crossfades every 2 s. Pictures, not
captions: the only text is what IS the figure (a year, a lake's ID, a
panel's name).

  ids    Long-term meltwater tracking · persistent lake IDs.
         A 3.9 km square of one Sentinel-2 tile on the central-west margin
         (68.56 N, 49.37 W) in 2018 and in 2019, each year's Dunmire outlines drawn
         over its own full-lake day, the other year's outline ghosted, and
         the persistent-ID tags fixed in place while the year changes. The
         big lake is CW2018_1583 in 2018 and CW2019_1996 in 2019 — two
         per-year IDs, ONE lake — CW_0506 in the project's CW lookup (the centroid
         tracker, 500 m; never validated, so this is the idea, not a
         result). The small lake up-right is CW_0054 both years too.
         Frames: 2018, 2019, then both outlines together; each year keeps
         its own slot on the year mark so the crossfade never stacks digits.
         Inputs (copies): source_data/stacks/CW_2018/CW2018_1583.nc,
         source_data/stacks/CW_2019/CW2019_1996.nc,
         source_data/essd/dunmire/labels_{2018,2019}_volumes.geojson,
         source_data/essd/lookups/CW_lookup.csv (fetch_sources.sh).

  label  Label lakes yourself · the inter-rater 200.
         A miniature of the labeler stage: one CONTESTED lake of the 200,
         CW2019_1989 (an HF/MD split — one of the paper's two hard pairs:
         labeler 1 MD, 2 HF 0.75 / LD 0.25, 3 MD 0.75 / LD 0.25), its season frames
         with lakelabel's RED outline (the page's own movie, R2
         ch03/irr2/), eight kept days from snow to full to drained; under
         it the season scrubber and the five class sliders, which settle
         across the frames onto the three experts' mean soft label (HF 0.25,
         MD 0.58, LD 0.17) snapped to the labeler's quarters: HF 0.25, MD
         0.5, LD 0.25. The slider path is illustrative, nobody's record.
         Inputs: website/.r2-cache/ch03/irr2/CW2019_1989.{mp4,json}, deck.json.

  train  Lake drainage deep learning classifier optimization.
         The ESSD-revision baseline (y2019_5c_pw_noaug, best epoch 189):
         loss and macro-F1 drawing across the epochs (train white, val
         gold) above the validation confusion matrix ticking from "all LD"
         toward the diagonal, each cell in its TRUE class's colour, alpha =
         the row fraction. Eight frames: epochs 1, 10, 20, 40, 70, 110, 150
         and the best epoch (189, its own matrix).
         Input: website/.r2-cache/ch03/training/training_dynamics_v2.json
         (build_training_dynamics.py, from the Oak logs).

Outputs: cinematic/scene_addl/output_addl_cards/
  persist_ids_NN.jpg (3) · label_irr_NN.jpg (8) · clf_opt_NN.jpg (8)   800²
then
  rsync -a --include='persist_ids_*' --include='label_irr_*' --include='clf_opt_*' --exclude='*' \
      cinematic/scene_addl/output_addl_cards/ website/.r2-cache/addl/cards/
  rclone copy cinematic/scene_addl/output_addl_cards r2:<bucket>/addl/cards \
      --include 'persist_ids_*.jpg' --include 'label_irr_*.jpg' --include 'clf_opt_*.jpg' \
      --header-upload 'Cache-Control: public, max-age=31536000, immutable'
(COPY, never sync.) New bytes = new names; never bump ASSET_VERSION.

Run (from the checkout root, in a Python env with geopandas + xarray + PIL):
  nice -n 15 python cinematic/scene_addl/build_card_thumbs.py [ids|label|train ...]
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'cinematic' / 'source_data'
CACHE = ROOT / 'website' / '.r2-cache'
OUT = ROOT / 'cinematic' / 'scene_addl' / 'output_addl_cards'
FONTS = ROOT / 'cinematic' / 'fonts'
MONO = '/System/Library/Fonts/Menlo.ttc'

SIZE = 800          # the delivered square
SS = 2              # supersampling for the vector overlays
JPEG_Q = 84

BG = (10, 10, 20)               # #0a0a14
GOLD = (244, 207, 106)          # --gold-bright #f4cf6a
GOLD_DIM = (232, 185, 74)       # --gold #e8b94a
INK = (245, 240, 230)           # the site's warm white
ICE_BLUE = (127, 211, 255)      # 2018 — the site's cool accent family
CLASS_ORDER = ['ND', 'HF', 'MD', 'LD', 'CD']
CLASS_RGB = {
    'ND': (0xE8, 0x52, 0x4A),
    'HF': (0x4C, 0xAF, 0x50),
    'MD': (0x42, 0xA5, 0xF5),
    'LD': (0xFF, 0x98, 0x00),
    'CD': (0xAB, 0x47, 0xBC),
}


def font(name: str, px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name) if not name.startswith('/') else name, px)


def save(img: Image.Image, name: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    img.convert('RGB').save(p, quality=JPEG_Q, optimize=True, progressive=True)
    kb = p.stat().st_size / 1024
    print(f'  {name}  {kb:.0f} KB')
    if kb > 120:
        print(f'  WARNING {name} is over 120 KB')
    return p


def dashed_polyline(d: ImageDraw.ImageDraw, pts: list[tuple[float, float]], fill, width: int,
                    dash: float, gap: float) -> None:
    """A closed dashed outline (PIL has no dash style)."""
    pts = pts + [pts[0]]
    carry = 0.0  # distance into the current dash/gap cycle
    period = dash + gap
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        seg = float(np.hypot(x1 - x0, y1 - y0))
        if seg == 0:
            continue
        s = 0.0
        while s < seg:
            phase = (carry + s) % period
            if phase < dash:
                run = min(dash - phase, seg - s)
                a, b = s / seg, (s + run) / seg
                d.line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a),
                        (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)], fill=fill, width=width)
            else:
                run = min(period - phase, seg - s)
            s += run
        carry = (carry + seg) % period


# ══════════════════════════════════════════════════════════════════════════
# ids — the same lake, next year
# ══════════════════════════════════════════════════════════════════════════
IDS_STACKS = {
    2018: (SRC / 'stacks' / 'CW_2018' / 'CW2018_1583.nc', '2018-07-13'),  # p_water 0.999
    2019: (SRC / 'stacks' / 'CW_2019' / 'CW2019_1996.nc', '2019-06-16'),  # p_water 0.999
}
# The two stacks are the same tile within 20 m (y); this is their common
# window in pixel centres, EPSG:32622.
IDS_X = (563920.0, 569030.0)
IDS_Y = (7609240.0, 7604150.0)
# The thumb's square inside that window, in its 10 m pixels (col, row,
# side): the big lake and its small persistent neighbour, ~3.9 km across.
IDS_CROP = (70, 40, 390)
YEAR_RGB = {2018: ICE_BLUE, 2019: GOLD}


def ids_thumb() -> None:
    import geopandas as gpd
    import pandas as pd
    import xarray as xr
    from shapely.geometry import box

    print('ids:')
    rgbs = {}
    for year, (path, day) in IDS_STACKS.items():
        ds = xr.open_dataset(path)
        ds = ds.sel(x=slice(*IDS_X), y=slice(*IDS_Y))
        names = [str(v) for v in ds['common_name'].values]
        idx = [names.index(b) for b in ('red', 'green', 'blue')]
        t = ds.sel(time=day)
        refl = t['reflectance'].isel(band=idx).values  # (3, H, W)
        ds.close()
        rgbs[year] = np.clip(np.nan_to_num(refl) / 10000.0, 0, 1).transpose(1, 2, 0)
    H, W = rgbs[2018].shape[:2]
    assert rgbs[2019].shape[:2] == (H, W), (rgbs[2019].shape, H, W)
    c0, r0, n = IDS_CROP
    assert c0 + n <= W and r0 + n <= H
    xc0, yc0 = IDS_X[0] + 10.0 * c0, IDS_Y[0] - 10.0 * r0  # the crop's first pixel centre

    # the outlines, both years, with their persistent IDs
    lookup = pd.read_csv(SRC / 'essd' / 'lookups' / 'CW_lookup.csv')
    win = box(xc0 - 5, yc0 - 10 * n + 5, xc0 + 10 * n - 5, yc0 + 5)
    lakes: dict[int, gpd.GeoDataFrame] = {}
    for year in (2018, 2019):
        g = gpd.read_file(SRC / 'essd' / 'dunmire' / f'labels_{year}_volumes.geojson').to_crs(32622)
        g = g[g.intersects(win)]
        g = g.merge(lookup[lookup.year == year][['original_id', 'persistent_id']],
                    left_on='new_id', right_on='original_id', how='left')
        lakes[year] = g
        print(f'  {year}: ' + ', '.join(f'{r.new_id}={r.persistent_id}' for r in g.itertuples()))

    S = SIZE * SS
    scale = S / n

    def to_px(x: float, y: float) -> tuple[float, float]:
        return (((x - xc0) / 10.0 + 0.5) * scale, ((yc0 - y) / 10.0 + 0.5) * scale)

    def rings(geom) -> list[list[tuple[float, float]]]:
        polys = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
        return [[to_px(x, y) for x, y in p.exterior.coords] for p in polys]

    # persistent = an ID present in both years inside the window
    both = sorted(set(lakes[2018].persistent_id.dropna()) & set(lakes[2019].persistent_id.dropna()))
    print('  persistent in both years:', both)
    anchors = {}
    for pid in both:
        geoms = [lakes[y][lakes[y].persistent_id == pid].geometry.union_all() for y in (2018, 2019)]
        u = geoms[0].union(geoms[1])
        anchors[pid] = (u, to_px(u.centroid.x, u.centroid.y))

    def base(year: int | None) -> Image.Image:
        if year is None:
            # the "both" frame: the two years' imagery averaged and pushed
            # darker still, so the two outlines carry it
            rgb = 0.5 * (rgbs[2018] + rgbs[2019])
            rgb = rgb * 0.62
        else:
            rgb = rgbs[year] * 0.86
        im = Image.fromarray((rgb[r0:r0 + n, c0:c0 + n] * 255).clip(0, 255).astype(np.uint8))
        im = im.resize((S, S), Image.LANCZOS)
        # a soft vignette so the corners sink into the site's dark
        yy, xx = np.mgrid[0:S, 0:S] / (S - 1) - 0.5
        v = 1.0 - 0.55 * np.clip(np.hypot(xx, yy) / 0.72, 0, 1) ** 2.2
        a = np.asarray(im).astype(np.float32) * v[..., None]
        return Image.fromarray(a.clip(0, 255).astype(np.uint8))

    lw = 5 * SS
    tag_font = font(MONO, 30 * SS)
    year_font = font('EBGaramond-Medium.ttf', 56 * SS)

    def draw_outlines(d: ImageDraw.ImageDraw, year: int, solid: bool) -> None:
        col = YEAR_RGB[year]
        for geom in lakes[year].geometry:
            for ring in rings(geom):
                if solid:
                    d.line(ring + [ring[0]], fill=(0, 0, 0, 120), width=lw + 6 * SS, joint='curve')
                    d.line(ring + [ring[0]], fill=col + (255,), width=lw, joint='curve')
                else:
                    dashed_polyline(d, ring, fill=col + (170,), width=3 * SS, dash=12 * SS, gap=9 * SS)

    # tag placement, by hand for this window (800-px units from the lake's
    # union centroid): the big lake wears its tag in its middle; the small
    # one's sits on open ice to its left, joined by a leader
    TAG_OFFSET = {'CW_0506': (0, 0), 'CW_0054': (-175, -45)}

    def draw_tags(d: ImageDraw.ImageDraw) -> None:
        for pid, (_, (ax, ay)) in anchors.items():
            ox, oy = TAG_OFFSET.get(pid, (90, -90))
            tx, ty = ax + ox * SS, ay + oy * SS
            tw = d.textlength(pid, font=tag_font)
            padx, pady = 17 * SS, 10 * SS
            th = 30 * SS
            x0, y0 = tx - tw / 2 - padx, ty - th / 2 - pady
            x1, y1 = tx + tw / 2 + padx, ty + th / 2 + pady + 3 * SS
            if (ox, oy) != (0, 0):
                # leader: anchor dot → nearest pill edge
                ex = min(max(ax, x0), x1)
                ey = y1 if ay > y1 else (y0 if ay < y0 else ay)
                d.line([(ax, ay), (ex, ey)], fill=INK + (200,), width=2 * SS)
                d.ellipse([ax - 6 * SS, ay - 6 * SS, ax + 6 * SS, ay + 6 * SS],
                          fill=INK + (255,), outline=(0, 0, 0, 160), width=2 * SS)
            d.rounded_rectangle([x0, y0, x1, y1], radius=(y1 - y0) / 2,
                                fill=(10, 10, 20, 215), outline=INK + (150,), width=2 * SS)
            d.text((tx, (y0 + y1) / 2), pid, font=tag_font, fill=INK + (255,), anchor='mm')

    def year_mark(d: ImageDraw.ImageDraw, years: list[int]) -> None:
        # each year has a FIXED slot on a little timeline ("2018 · 2019"),
        # so the 2 s crossfade never overlays one year's digits on another's
        sep = '  ·  '
        y = S - 30 * SS
        xa = 34 * SS
        xs = xa + d.textlength('2018', font=year_font)
        xb = xs + d.textlength(sep, font=year_font)
        slot = {2018: xa, 2019: xb}
        for yr in years:
            d.text((slot[yr], y), str(yr), font=year_font, fill=YEAR_RGB[yr] + (255,), anchor='ls')
        if len(years) == 2:
            d.text((xs, y), sep, font=year_font, fill=INK + (150,), anchor='ls')

    frames = [(2018, [2018]), (2019, [2019]), (None, [2018, 2019])]
    for k, (year, marks) in enumerate(frames):
        im = base(year).convert('RGBA')
        ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        if year is None:
            draw_outlines(d, 2018, solid=True)
            draw_outlines(d, 2019, solid=True)
        else:
            other = 2019 if year == 2018 else 2018
            draw_outlines(d, other, solid=False)
            draw_outlines(d, year, solid=True)
        draw_tags(d)
        year_mark(d, marks)
        im = Image.alpha_composite(im, ov).resize((SIZE, SIZE), Image.LANCZOS)
        save(im, f'persist_ids_{k:02d}.jpg')


# ══════════════════════════════════════════════════════════════════════════
# label — the labeler stage in miniature
# ══════════════════════════════════════════════════════════════════════════
LABEL_LAKE = 'CW2019_1989'
# indices into the sidecar's kept frames (= the movie's frames): snow, the
# first water, filling ×3, full (24 Jun), drained (29 Jun), the remnant
LABEL_FRAMES = [0, 6, 11, 16, 23, 31, 34, 50]
# what the five sliders read on each of those frames: nothing while the
# season plays, then MD as it fills, HF once it is gone in five days, LD
# for the remnant — landing on the three experts' mean (HF 0.25, MD 0.58,
# LD 0.17) snapped to the labeler's quarters
LABEL_SLIDERS = [
    {}, {}, {}, {},
    {'MD': 0.25},
    {'MD': 0.5},
    {'MD': 0.5, 'HF': 0.25},
    {'MD': 0.5, 'HF': 0.25, 'LD': 0.25},
]
# the chip: a crop of the 512² movie frame around the lake (x, y, w, h)
LABEL_CROP = (0, 92, 512, 350)
LABEL_CHIP_H = 548


def movie_frames(mp4: Path, keep: list[int]) -> list[Image.Image]:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(mp4), '-vsync', '0',
                        f'{tmp}/f%04d.png'], check=True)
        return [Image.open(f'{tmp}/f{i + 1:04d}.png').convert('RGB').copy() for i in keep]


def label_thumb() -> None:
    print('label:')
    irr = CACHE / 'ch03' / 'irr2'
    side = json.loads((irr / f'{LABEL_LAKE}.json').read_text())
    deck = json.loads((irr / 'deck.json').read_text())
    lake = next(l for l in deck['lakes'] if l['id'] == LABEL_LAKE)
    assert lake['contested'], LABEL_LAKE
    mean = np.mean([e['p'] for e in lake['experts']], axis=0)
    print(f'  {LABEL_LAKE} split {lake["split"]}; expert mean',
          dict(zip(CLASS_ORDER, np.round(mean, 3))))
    chips = movie_frames(irr / f'{LABEL_LAKE}.mp4', LABEL_FRAMES)
    days = [side['frames'][i]['day'] for i in LABEL_FRAMES]
    ndays = side['days']
    print('  days', [side['frames'][i]['date_iso'] for i in LABEL_FRAMES])

    S = SIZE * SS
    cx, cy, cw, ch = LABEL_CROP
    chip_h = LABEL_CHIP_H * SS
    for k, (chip, day, vals) in enumerate(zip(chips, days, LABEL_SLIDERS)):
        im = Image.new('RGB', (S, S), BG)
        c = chip.crop((cx, cy, cx + cw, cy + ch)).resize((S, chip_h), Image.LANCZOS)
        a = np.asarray(c).astype(np.float32) * 0.92
        # the chip sinks into the panel at its foot
        fade = np.clip((np.arange(chip_h) - (chip_h - 36 * SS)) / (36 * SS), 0, 1)[:, None, None]
        a = a * (1 - 0.55 * fade) + np.array(BG, np.float32) * 0.55 * fade
        im.paste(Image.fromarray(a.clip(0, 255).astype(np.uint8)), (0, 0))
        d = ImageDraw.Draw(im, 'RGBA')  # an RGB canvas + 'RGBA' ink = alpha-blended marks
        d.line([(0, chip_h), (S, chip_h)], fill=GOLD_DIM + (110,), width=2 * SS)

        # the season scrubber: a gold run up to the day, a gold knob
        x0, x1 = 44 * SS, S - 44 * SS
        ys = chip_h + 42 * SS
        f = day / max(1, ndays - 1)
        xk = x0 + f * (x1 - x0)
        d.rounded_rectangle([x0, ys - 4 * SS, x1, ys + 4 * SS], radius=4 * SS, fill=(245, 199, 94, 62))
        d.rounded_rectangle([x0, ys - 4 * SS, max(x0 + 8 * SS, xk), ys + 4 * SS], radius=4 * SS,
                            fill=GOLD + (235,))
        r = 14 * SS
        d.ellipse([xk - r, ys - r, xk + r, ys + r], fill=GOLD + (255,), outline=BG + (255,), width=3 * SS)

        # the five class sliders
        # (no separate chip: at zero the five knobs ARE the class chips)
        top = chip_h + 92 * SS
        pitch = 30 * SS
        tx0, tx1 = 58 * SS, S - 44 * SS
        for i, code in enumerate(CLASS_ORDER):
            col = CLASS_RGB[code]
            y = top + i * pitch
            d.rounded_rectangle([tx0, y - 3 * SS, tx1, y + 3 * SS], radius=3 * SS, fill=(255, 255, 255, 30))
            for q in (0.25, 0.5, 0.75, 1.0):
                xq = tx0 + q * (tx1 - tx0)
                d.line([(xq, y - 8 * SS), (xq, y + 8 * SS)], fill=(255, 255, 255, 55), width=2 * SS)
            v = vals.get(code, 0.0)
            xv = tx0 + v * (tx1 - tx0)
            if v > 0:
                d.rounded_rectangle([tx0, y - 3 * SS, xv, y + 3 * SS], radius=3 * SS, fill=col + (215,))
            rk = 12 * SS
            d.ellipse([xv - rk, y - rk, xv + rk, y + rk], fill=col + (255,), outline=BG + (255,), width=3 * SS)
        im = im.resize((SIZE, SIZE), Image.LANCZOS)
        save(im, f'label_irr_{k:02d}.jpg')


# ══════════════════════════════════════════════════════════════════════════
# train — optimization: the curves, the matrix finding its diagonal
# ══════════════════════════════════════════════════════════════════════════
TRAIN_EPOCHS = [1, 10, 20, 40, 70, 110, 150]  # + the best epoch, its own matrix
TRAIN_XMAX = 200                               # the curves' epoch axis
LOSS_RANGE = (0.35, 1.7)


def train_thumb() -> None:
    print('train:')
    dyn = json.loads((CACHE / 'ch03' / 'training' / 'training_dynamics_v2.json').read_text())
    run = dyn['runs']['5c']
    assert run['classes'] == CLASS_ORDER, run['classes']
    best = run['best_epoch']
    cbe = run['confusion_by_epoch']
    steps = [(e, cbe['val'][cbe['epochs'].index(e)]) for e in TRAIN_EPOCHS]
    steps.append((best, run['best']['val']['cm']))
    print(f'  {run["run"]}: epochs {[e for e, _ in steps]} (best {best}, '
          f'val macro-F1 {run["best"]["val"]["macro_f1"]})')
    cur = run['curves']

    S = SIZE * SS
    title_font = font('EBGaramond-Medium.ttf', 40 * SS)
    panels = [
        # (title, x0, x1, train, val, (lo, hi))
        ('Loss', 40, 385, cur['train_loss'], cur['val_loss'], LOSS_RANGE),
        ('F1', 415, 760, cur['train_f1'], cur['val_f1'], (0.0, 1.0)),
    ]
    py0, py1 = 88, 290   # plot box, 800-px units

    for k, (ep, cm) in enumerate(steps):
        im = Image.new('RGB', (S, S), BG)
        d = ImageDraw.Draw(im, 'RGBA')  # an RGB canvas + 'RGBA' ink = alpha-blended marks
        for title, px0, px1, tr, va, (lo, hi) in panels:
            X0, X1, Y0, Y1 = px0 * SS, px1 * SS, py0 * SS, py1 * SS
            # the panel's title — F with a subscript 1, as on the site
            if title == 'F1':
                d.text((X0 + 6 * SS, Y0 - 14 * SS), 'F', font=title_font, fill=GOLD + (255,), anchor='ls')
                fw = d.textlength('F', font=title_font)
                d.text((X0 + 6 * SS + fw + 1 * SS, Y0 - 4 * SS), '1',
                       font=font('EBGaramond-Medium.ttf', 24 * SS), fill=GOLD + (255,), anchor='ls')
            else:
                d.text((X0 + 6 * SS, Y0 - 14 * SS), title, font=title_font, fill=GOLD + (255,), anchor='ls')
            # recessive axes
            d.line([(X0, Y0), (X0, Y1), (X1, Y1)], fill=(245, 240, 230, 80), width=2 * SS)

            def pt(e: int, v: float) -> tuple[float, float]:
                return (X0 + (e / TRAIN_XMAX) * (X1 - X0),
                        Y1 - (min(max(v, lo), hi) - lo) / (hi - lo) * (Y1 - Y0))
            if ep == best:
                bx = pt(best, lo)[0]
                for yy in range(int(Y0), int(Y1), 10 * SS):
                    d.line([(bx, yy), (bx, yy + 5 * SS)], fill=GOLD + (170,), width=2 * SS)
            for series, col, w in ((tr, INK + (200,), 5 * SS), (va, GOLD + (255,), 7 * SS)):
                pts = [pt(e + 1, series[e]) for e in range(ep)]
                if len(pts) > 1:
                    d.line(pts, fill=col, width=w, joint='curve')
                hx, hy = pts[-1]
                r = 10 * SS
                d.ellipse([hx - r, hy - r, hx + r, hy + r], fill=col[:3] + (255,), outline=BG + (255,), width=3 * SS)

        # the validation confusion matrix: rows = true class, cells in the
        # true class's colour, alpha = the row fraction
        m = np.asarray(cm, float)
        frac = m / np.maximum(m.sum(axis=1, keepdims=True), 1)
        cell, gap = 80 * SS, 7 * SS
        side = 5 * cell + 4 * gap
        mx0 = (S - side) // 2 + 14 * SS
        my0 = 326 * SS
        for i, tcode in enumerate(CLASS_ORDER):
            col = np.array(CLASS_RGB[tcode], float)
            # row chip (true) on the left, column chip (predicted) below
            cy = my0 + i * (cell + gap) + cell / 2
            d.rounded_rectangle([mx0 - 36 * SS, cy - 9 * SS, mx0 - 18 * SS, cy + 9 * SS],
                                radius=3 * SS, fill=tuple(col.astype(int)) + (255,))
            cxp = mx0 + i * (cell + gap) + cell / 2
            yb = my0 + side + 12 * SS
            d.rounded_rectangle([cxp - 9 * SS, yb, cxp + 9 * SS, yb + 18 * SS],
                                radius=3 * SS, fill=tuple(col.astype(int)) + (255,))
            for j in range(5):
                x = mx0 + j * (cell + gap)
                y = my0 + i * (cell + gap)
                a = frac[i, j]
                base = np.array([22, 22, 32], float)
                rgb = base + (col - base) * (0.0 if a <= 0 else 0.10 + 0.90 * a ** 0.8)
                d.rounded_rectangle([x, y, x + cell, y + cell], radius=8 * SS,
                                    fill=tuple(rgb.astype(int)) + (255,))
                if i == j:
                    d.rounded_rectangle([x, y, x + cell, y + cell], radius=8 * SS,
                                        outline=(245, 240, 230, 80), width=2 * SS)
        im = im.resize((SIZE, SIZE), Image.LANCZOS)
        save(im, f'clf_opt_{k:02d}.jpg')


if __name__ == '__main__':
    todo = sys.argv[1:] or ['ids', 'label', 'train']
    for name in todo:
        {'ids': ids_thumb, 'label': label_thumb, 'train': train_thumb}[name]()
