"""Build the Acknowledgements split-out faces.

The director asked for a split-out phase of the acknowledgements, stepped
through with the NEXT button, that shows each acknowledgements section
group by group with a publicly available professional headshot of each
person (found on the web).

headshots.json (next to this file) is the provenance record — for every
person or group on the public page: the official page that names them,
the image URL taken from that page, the day it was fetched, and the crop.
Only photos from a page that itself names the person with a matching
affiliation were used; anyone else is an initials tile ("initials").

This script:
  1. downloads each `image_url` (or reads `--raw <dir>/<slug>.<ext>` if a
     copy is already there), applies `crop` = [cx, cy, side] — the face
     centre as fractions of width/height and the square's side as a
     fraction of the shorter edge — and writes a 512 px JPEG (q 85) to
     <out>/<slug>.jpg (logos: the whole mark, padded square, PNG kept
     transparent → <slug>.png);
  2. writes website/src/config/ackHeadshots.gen.ts (slug → R2 key, kind,
     and the person's `url` — the director asked that a click on a name or face
     opens their site; no `url` in the manifest = unlinked);
  3. writes a contact sheet for review (--sheet), and a second sheet with
     every tile under the page's circular mask (--circles).

Upload (by hand, after the sheet has been reviewed; NEW names only — R2 objects
are cached immutable for a year):
  rclone copy <out> r2:<bucket>/acks/people_v2 \
    --header-upload "Cache-Control: public, max-age=31536000, immutable"

Run with the system python3 (Pillow only):
  python3 cinematic/scene_acks/build_headshots.py --raw <dir> --out <dir> --sheet <png> --circles <png>
  --only <slug,slug,…>  bake (and sheet) just those tiles; the .gen.ts is
                        still written for EVERYONE from the manifest, so the
                        already-uploaded tiles keep their keys untouched.

Manifest extras: `size` = output pixels (default 512; the
small bullet faces under the Princeton AOS card use 160); `mask: "circle"`
on a logo = the mark is a round badge on a white ground — cut the badge
out so it sits on the page's dark plate; `dark_filter` on a logo = a CSS
filter the page applies (Mineral-X: brightness(1.5)) so a mark drawn for
a white ground still reads on the dark plate — the stored PNG is untouched.
"""
from __future__ import annotations

import argparse
import io
import json
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
MANIFEST = HERE / 'headshots.json'
GEN_TS = REPO / 'website' / 'src' / 'config' / 'ackHeadshots.gen.ts'
PREFIX = 'acks/people_v2'  # v1 = the first cut; v2 = recentred for the circles
# A manifest entry's own `prefix` overrides PREFIX: faces added after v2 was
# uploaded go to a NEW prefix (e.g. Aleksandar Diamond-Stanic →
# acks/people_v3) so no v2 object is ever re-uploaded.
SIZE = 512
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'


def load_source(entry: dict, raw: Path | None) -> Image.Image:
    if raw is not None:
        hits = sorted(raw.glob(entry['slug'] + '.*'))
        if hits:
            return Image.open(hits[0])
    req = urllib.request.Request(entry['image_url'], headers={'User-Agent': UA, 'Accept': 'image/jpeg,image/png,*/*'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return Image.open(io.BytesIO(r.read()))


def crop_face(im: Image.Image, crop: list[float], pad: bool = False, size: int = SIZE) -> Image.Image:
    """Cut the square `crop` = [cx, cy, side] and scale it to SIZE.

    The tiles are shown as CIRCLES, so the face must sit centred with the
    whole head inside the circle (eyes ~44 % down, air above the hair).
    Where the source is framed too tight for that (the face fills it), the
    manifest sets `"pad": true` and the square may run past the photo's
    edge: the outside is the photo's border pixels stretched outward,
    blurred and feathered into the photo, so it reads as more of the same
    out-of-focus background rather than a hard border. Without `pad`
    the square is clamped inside the photo as before.
    """
    im = ImageOps.exif_transpose(im).convert('RGB')
    w, h = im.size
    cx, cy, side = crop
    s = side * min(w, h)
    x0, y0 = cx * w - s / 2, cy * h - s / 2
    if not pad:
        s = min(s, w, h)
        x0 = min(max(x0, 0), w - s)
        y0 = min(max(y0, 0), h - s)
        box = tuple(round(v) for v in (x0, y0, x0 + s, y0 + s))
        return im.crop(box).resize((size, size), Image.LANCZOS)
    return padded_square(im, x0, y0, s, size)


def padded_square(im: Image.Image, x0: float, y0: float, s: float, size: int = SIZE) -> Image.Image:
    w, h = im.size
    L, T = max(0, -round(x0)), max(0, -round(y0))
    R, B = max(0, round(x0 + s) - w), max(0, round(y0 + s) - h)
    W, H = w + L + R, h + T + B
    canvas = Image.new('RGB', (W, H))
    canvas.paste(im, (L, T))
    # Stretch the 1-px border rows/columns outward (and the corners). Not a
    # mirror: mirroring puts a ghost of the hair above the head.
    if T:
        canvas.paste(im.crop((0, 0, w, 1)).resize((w, T)), (L, 0))
    if B:
        canvas.paste(im.crop((0, h - 1, w, h)).resize((w, B)), (L, T + h))
    if L:
        canvas.paste(canvas.crop((L, 0, L + 1, H)).resize((L, H)), (0, 0))
    if R:
        canvas.paste(canvas.crop((L + w - 1, 0, L + w, H)).resize((R, H)), (L + w, 0))
    if L or T or R or B:
        r = max(3.0, 0.04 * s)
        blurred = canvas.filter(ImageFilter.GaussianBlur(r))
        mask = Image.new('L', (W, H), 255)
        ImageDraw.Draw(mask).rectangle((L, T, L + w - 1, T + h - 1), fill=0)
        mask = mask.filter(ImageFilter.GaussianBlur(max(1.5, 0.015 * s)))
        canvas = Image.composite(blurred, canvas, mask)
    bx, by = round(x0) + L, round(y0) + T
    return canvas.crop((bx, by, bx + round(s), by + round(s))).resize((size, size), Image.LANCZOS)


def circle_badge(im: Image.Image) -> Image.Image:
    """A round mark delivered on a white ground (the Princeton AOS badge):
    keep the disc, make the ground transparent. The disc is the bounding
    box of the non-white pixels; the mask is that ellipse, drawn at 4x and
    downsampled so the rim stays smooth, inset half a pixel so no white
    fringe survives."""
    im = im.convert('RGBA')
    w, h = im.size
    g = im.convert('L').point(lambda v: 255 if v < 235 else 0)
    bbox = g.getbbox()
    if not bbox:
        return im
    big = Image.new('L', (w * 4, h * 4), 0)
    x0, y0, x1, y1 = (v * 4 for v in bbox)
    ImageDraw.Draw(big).ellipse((x0 + 2, y0 + 2, x1 - 3, y1 - 3), fill=255)
    mask = big.resize((w, h), Image.LANCZOS)
    im.putalpha(mask)
    return im.crop(bbox)


def square_logo(im: Image.Image, mask: str | None = None) -> Image.Image:
    im = im.convert('RGBA')
    if mask == 'circle':
        im = circle_badge(im)
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    w, h = im.size
    k = SIZE / max(w, h)
    im = im.resize((max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS)
    out = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    out.paste(im, ((SIZE - im.width) // 2, (SIZE - im.height) // 2), im)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', type=Path, help='dir of already-downloaded originals <slug>.<ext>')
    ap.add_argument('--out', type=Path, required=True, help='where the 512 px files go')
    ap.add_argument('--sheet', type=Path, help='contact sheet PNG for review')
    ap.add_argument('--circles', type=Path, help='second sheet: each tile under the page\'s circular mask')
    ap.add_argument('--only', help='comma-separated slugs to bake + sheet (the .gen.ts still covers everyone)')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    people = json.loads(MANIFEST.read_text())['people']
    only = set(a.only.split(',')) if a.only else None

    tiles: list[tuple[dict, Image.Image | None]] = []
    gen: dict[str, dict] = {}
    for e in people:
        kind = e['kind']
        bake = only is None or e['slug'] in only
        prefix = e.get('prefix', PREFIX)
        img = None
        # `file`: the R2 object's name when a person was re-keyed after the
        # bake (the store is immutable; e.g. David Zhen Yin)
        fname = e.get('file', e['slug'])
        if kind == 'photo':
            if bake:
                img = crop_face(load_source(e, a.raw), e['crop'], e.get('pad', False), int(e.get('size', SIZE)))
                img.save(a.out / f"{fname}.jpg", 'JPEG', quality=85, optimize=True, progressive=True)
            gen[e['slug']] = {'kind': 'photo', 'key': f"{prefix}/{fname}.jpg"}
        elif kind == 'logo':
            if bake:
                img = square_logo(load_source(e, a.raw), e.get('mask'))
                img.save(a.out / f"{e['slug']}.png", 'PNG', optimize=True)
            gen[e['slug']] = {'kind': 'logo', 'key': f"{prefix}/{e['slug']}.png"}
        else:  # initials | text
            gen[e['slug']] = {'kind': kind}
        if e.get('url'):
            gen[e['slug']]['url'] = e['url']
        if e.get('dark_filter'):
            gen[e['slug']]['filter'] = e['dark_filter']
        if bake:
            tiles.append((e, img))

    lines = [
        '// GENERATED by cinematic/scene_acks/build_headshots.py from',
        '// cinematic/scene_acks/headshots.json — do not edit by hand.',
        '// `url`: the person\'s own site (or official profile); absent = unlinked.',
        '// `filter`: a CSS filter the page applies to a logo drawn for white (headshots.json dark_filter).',
        "export type AckFace = ({ kind: 'photo' | 'logo'; key: string } | { kind: 'initials' | 'text' }) & { url?: string; filter?: string }",
        'export const ACK_HEADSHOTS: Record<string, AckFace> = {',
    ]
    for slug, f in gen.items():
        parts = [f"kind: '{f['kind']}'"]
        if 'key' in f:
            parts.append(f"key: '{f['key']}'")
        if 'url' in f:
            parts.append(f"url: '{f['url']}'")
        if 'filter' in f:
            parts.append(f"filter: '{f['filter']}'")
        lines.append(f"  '{slug}': {{ {', '.join(parts)} }},")
    lines.append('}')
    GEN_TS.write_text('\n'.join(lines) + '\n')

    if a.sheet:
        contact_sheet(tiles, a.sheet)
    if a.circles:
        circle_sheet(tiles, a.circles)


def font(size: int) -> ImageFont.ImageFont:
    for p in ('/System/Library/Fonts/Supplemental/Arial.ttf', '/System/Library/Fonts/Helvetica.ttc'):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()


def contact_sheet(tiles: list[tuple[dict, Image.Image | None]], path: Path) -> None:
    T, cols, pad, cap = 260, 6, 24, 96
    rows = (len(tiles) + cols - 1) // cols
    W = cols * (T + pad) + pad
    H = 70 + rows * (T + cap + pad) + pad
    sheet = Image.new('RGB', (W, H), (12, 14, 20))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 22), 'Acknowledgements headshots — check every face (INITIALS = no confirmed photo)', fill=(232, 185, 74), font=font(26))
    f1, f2 = font(18), font(15)
    for i, (e, img) in enumerate(tiles):
        x = pad + (i % cols) * (T + pad)
        y = 70 + (i // cols) * (T + cap + pad)
        if img is not None:
            t = img.convert('RGBA').resize((T, T), Image.LANCZOS)
            bg = Image.new('RGBA', (T, T), (30, 33, 40, 255) if e['kind'] == 'logo' else (20, 24, 32, 255))
            bg.alpha_composite(t)
            sheet.paste(bg.convert('RGB'), (x, y))
        else:
            d.rectangle((x, y, x + T, y + T), fill=(29, 36, 51), outline=(232, 185, 74))
            label = 'INITIALS' if e['kind'] == 'initials' else 'TEXT TILE'
            d.text((x + T / 2, y + T / 2), label, fill=(232, 185, 74), font=font(30), anchor='mm')
        d.text((x, y + T + 8), e['name'], fill=(245, 245, 245), font=f1)
        d.text((x, y + T + 32), ' · '.join(e['groups'])[:40], fill=(200, 200, 200), font=f2)
        dom = urlparse(e['source_page']).netloc if e.get('source_page') else '—'
        conf = e.get('confidence', '')
        d.text((x, y + T + 52), f"{dom}", fill=(150, 170, 200), font=f2)
        if conf and conf != 'high':
            d.text((x, y + T + 72), f'CHECK: {conf} confidence', fill=(240, 120, 110), font=f2)
    sheet.save(path)


def initials_of(name: str) -> str:
    w = [x for x in name.split() if not (len(x) == 2 and x.endswith('.'))]
    return ((w[0][0] if w else '') + (w[-1][0] if len(w) > 1 else '')).upper()


def circle_sheet(tiles: list[tuple[dict, Image.Image | None]], path: Path) -> None:
    """Each tile as SectionAcknowledgements.vue shows it: a photo or the
    initials in a CIRCLE with the 2 px gold rim; a logo whole on the dark
    translucent plate (earlier a light one) in a soft square. What the
    circle hides is hidden here too."""
    T, cols, pad, cap, k = 240, 6, 30, 60, 3  # draw at 3x, then downsample
    rows = (len(tiles) + cols - 1) // cols
    W = cols * (T + pad) + pad
    H = 70 + rows * (T + cap + pad) + pad
    sheet = Image.new('RGB', (W, H), (8, 10, 16))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 22), 'Acknowledgements headshots — as the page shows them (circular mask)', fill=(232, 185, 74), font=font(26))
    gold = (232, 185, 74)
    for i, (e, img) in enumerate(tiles):
        x = pad + (i % cols) * (T + pad)
        y = 70 + (i // cols) * (T + cap + pad)
        big = T * k
        tile = Image.new('RGBA', (big, big), (0, 0, 0, 0))
        m = Image.new('L', (big, big), 0)
        md = ImageDraw.Draw(m)
        if e['kind'] == 'logo':
            md.rounded_rectangle((0, 0, big - 1, big - 1), radius=round(0.14 * big), fill=255)
            face = Image.new('RGBA', (big, big), (8, 10, 16, 255))
            face.alpha_composite(Image.new('RGBA', (big, big), (255, 255, 255, 20)))
            inner = round(big * 0.76)
            face.alpha_composite(img.convert('RGBA').resize((inner, inner), Image.LANCZOS), ((big - inner) // 2, (big - inner) // 2))
        else:
            md.ellipse((0, 0, big - 1, big - 1), fill=255)
            if img is not None:
                face = img.convert('RGBA').resize((big, big), Image.LANCZOS)
            else:
                face = Image.new('RGBA', (big, big), (20, 25, 36, 255))
                ImageDraw.Draw(face).text((big / 2, big / 2), initials_of(e['name']), fill=gold, font=font(round(big * 0.36)), anchor='mm')
        tile.paste(face, (0, 0), m)
        rim = ImageDraw.Draw(tile)
        if e['kind'] == 'logo':
            rim.rounded_rectangle((0, 0, big - 1, big - 1), radius=round(0.14 * big), outline=gold + (150,), width=2 * k)
        else:
            rim.ellipse((0, 0, big - 1, big - 1), outline=gold + (150,), width=2 * k)
        tile = tile.resize((T, T), Image.LANCZOS)
        sheet.paste(tile, (x, y), tile)
        d.text((x + T / 2, y + T + 10), e['name'], fill=(245, 245, 245), font=font(18), anchor='ma')
        if e['kind'] == 'initials':
            d.text((x + T / 2, y + T + 34), 'initials — no confirmed photo', fill=(240, 120, 110), font=font(14), anchor='ma')
    sheet.save(path)


if __name__ == '__main__':
    main()
