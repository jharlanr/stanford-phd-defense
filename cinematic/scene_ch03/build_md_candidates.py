"""Candidate MOULIN-DRAINAGE lakes for Chapter 3's label demo — season movies
for the director to choose from (the labelling example should use a
different moulin-drainage lake, so the ask was a shortlist of four
candidates with a movie of each to decide between — the demo's
CW2019_1848 is already beat 0's MD callout, so the audience has seen it
by then).

Decision-grade only. The deposit stacks live on the cluster storage (not mounted), so the
imagery is Earth Engine's Sentinel-2 L2A (`COPERNICUS/S2_SR_HARMONIZED`,
the same ESA product sat-tile-stack reads), fetched like the revisit page's
fetch_s2_2019.py: the lake's own 512 × 512, 10 m, UTM 22N tile, one mosaic
per day, 8-bit (reflectance = DN / 250). The chosen lake is then baked the
site's way (build_callout_movies.py from its real stack + the network bake)
once the cluster storage is mounted — this script's output never ships.

Candidates come from the labels (cinematic/source_data/essd/labels,
label MD with p_MD = 1, unflagged), the IRR-200 (all three labelers MD =
"U"), and the site's own per-lake daily p_water (cinematic/data/ch03/
essd_lakes_2019.json): a clear decline to near-empty with no refill, a
large basin, not a lake the site already uses.

Movie recipe = build_callout_movies.py's: a day is KEPT when the whole tile
was imaged (≥ 99 % of pixels have data); cloudy days stay (they are data);
the Dunmire outline burned in the MD blue; 2 fps for review; a date stamp
and the lake id top-left; a contact sheet of every kept frame and the
p_water curve beside it.

Outputs: cinematic/scene_ch03/output_md_candidates/
  <id>.npz          the fetched days (gitignored with the rest of output_*)
  <id>.mp4 / .json  the movie + sidecar (kept days, cloud fraction per day)
  <id>_sheet.png    contact sheet · <id>_curve.png  the season's p_water
  index.html        all candidates side by side (open locally)

Run (defense checkout root):
  python cinematic/scene_ch03/build_md_candidates.py --fetch  CW2019_1986 …   (a Python env with earthengine-api)
  cinematic/.venv/bin/python     cinematic/scene_ch03/build_md_candidates.py --movies CW2019_1986 …
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(line_buffering=True)
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'cinematic' / 'scene_ch03' / 'output_md_candidates'
LAKES_JSON = ROOT / 'cinematic' / 'data' / 'ch03' / 'essd_lakes_2019.json'
LABELS = ROOT / 'cinematic' / 'source_data' / 'essd' / 'labels' / 'labels_CW_2019.csv'

EPSG = 32622
RES = 10.0
N = 512
TILE_M = N * RES
T0 = date(2019, 5, 1)
BANDS = ['B4', 'B3', 'B2']
CHUNK = 20                 # computePixels caps a request at 48 MB
MD_BLUE = (0x42, 0xa5, 0xf5)
FPS = 2
MIN_COVER = 0.99


def lakes_by_id() -> dict:
    return {l['id']: l for l in json.loads(LAKES_JSON.read_text())['lakes']}


def utm(lon: float, lat: float) -> tuple[float, float]:
    from pyproj import Transformer
    return Transformer.from_crs('EPSG:4326', f'EPSG:{EPSG}', always_xy=True).transform(lon, lat)


def grid_for(lake: dict) -> dict:
    e, n = utm(*lake['c'])
    x0 = round((e - TILE_M / 2) / RES) * RES
    y1 = round((n + TILE_M / 2) / RES) * RES
    return {'x0': x0, 'y1': y1}


# ── fetch (a Python env with earthengine-api) ──
def pixels(img, grid: dict) -> np.ndarray:
    import ee
    for attempt in range(6):
        try:
            return np.load(io.BytesIO(ee.data.computePixels({'expression': img, 'fileFormat': 'NPY', 'grid': grid})))
        except Exception as e:  # noqa: BLE001
            if attempt == 5:
                raise
            print('   retry', str(e)[:100])
            time.sleep(4 * (attempt + 1))
    raise RuntimeError


def fetch(lake: dict) -> str:
    import ee
    out = OUT / f"{lake['id']}.npz"
    if out.exists():
        return f"{lake['id']} have"
    g = grid_for(lake)
    x0, y1 = g['x0'], g['y1']
    grid = {
        'dimensions': {'width': N, 'height': N},
        'affineTransform': {'scaleX': RES, 'shearX': 0, 'translateX': x0, 'shearY': 0, 'scaleY': -RES, 'translateY': y1},
        'crsCode': f'EPSG:{EPSG}',
    }
    box = ee.Geometry.Rectangle([x0, y1 - TILE_M, x0 + TILE_M, y1], f'EPSG:{EPSG}', False)
    ic = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(box).filterDate('2019-05-01', '2019-10-01')
    stamps = ic.aggregate_array('system:time_start').getInfo()
    dates = sorted({time.strftime('%Y-%m-%d', time.gmtime(t / 1000)) for t in stamps})
    days, rgb, scl = [], [], []
    for k in range(0, len(dates), CHUNK):
        part = dates[k:k + CHUNK]
        imgs = []
        for d in part:
            nxt = (date.fromisoformat(d) + timedelta(days=1)).isoformat()
            m = ic.filterDate(d, nxt).mosaic()
            tag = d.replace('-', '')
            imgs.append(m.select(BANDS).divide(40).round().clamp(0, 255).unmask(0).toUint8().rename([f'd{tag}_{b}' for b in BANDS]))
            imgs.append(m.select('SCL').unmask(0).toUint8().rename(f'd{tag}_SCL'))
        arr = pixels(ee.Image.cat(imgs), grid)
        for d in part:
            tag = d.replace('-', '')
            a = np.stack([arr[f'd{tag}_{b}'] for b in BANDS])
            if (a.max(axis=0) > 0).mean() < 0.02:
                continue          # the day's granules miss the tile
            days.append(d)
            rgb.append(a)
            scl.append(arr[f'd{tag}_SCL'])
        print(f"   {lake['id']}: {len(days)} days so far")
    np.savez_compressed(out, days=np.array(days), rgb=np.stack(rgb), scl=np.stack(scl), x0=x0, y1=y1, res=RES, epsg=EPSG)
    return f"{lake['id']}: Sentinel-2 on {len(days)} days ({len(dates)} dates searched)"


# ── movies (cinematic/.venv) ──
def outline_mask(lake: dict, x0: float, y1: float) -> np.ndarray:
    from PIL import Image, ImageDraw
    im = Image.new('L', (N, N), 0)
    dr = ImageDraw.Draw(im)
    for ring in lake['rings']:
        pts = [((utm(lon, lat)[0] - x0) / RES, (y1 - utm(lon, lat)[1]) / RES) for lon, lat in ring]
        dr.line(pts + [pts[0]], fill=255, width=2)
    return np.array(im) > 0


def movie(lake: dict, label_row: dict | None) -> str:
    from PIL import Image, ImageDraw, ImageFont
    z = np.load(OUT / f"{lake['id']}.npz")
    days, rgb, scl = list(z['days']), z['rgb'], z['scl']
    x0, y1 = float(z['x0']), float(z['y1'])
    ol = outline_mask(lake, x0, y1)
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 22)
    except OSError:
        font = ImageFont.load_default()
    frames_dir = OUT / '_frames' / lake['id']
    frames_dir.mkdir(parents=True, exist_ok=True)
    for f in frames_dir.glob('*.png'):
        f.unlink()
    kept = []
    for i, d in enumerate(days):
        a = rgb[i]
        cover = float((a.max(axis=0) > 0).mean())
        if cover < MIN_COVER:
            continue
        s = scl[i]
        cloud = float(np.isin(s, (3, 8, 9, 10)).mean())
        img = np.moveaxis(a, 0, -1).copy()
        img[ol] = MD_BLUE
        im = Image.fromarray(img)
        dr = ImageDraw.Draw(im)
        txt = f"{lake['id'].replace('CW2019_', 'CW2019 ')}  ·  {d}"
        dr.rectangle([8, 8, 8 + dr.textlength(txt, font=font) + 14, 42], fill=(0, 0, 0))
        dr.text((15, 13), txt, fill=(255, 255, 255), font=font)
        im.save(frames_dir / f'f{len(kept):03d}.png')
        kept.append({'day': (date.fromisoformat(d) - T0).days, 'date_iso': d, 'cloud': round(cloud, 3),
                     'p_water': lake['pw'][(date.fromisoformat(d) - T0).days] / 100.0})
    mp4 = OUT / f"{lake['id']}.mp4"
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-framerate', str(FPS), '-i', str(frames_dir / 'f%03d.png'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-g', '8', '-bf', '0', '-movflags', '+faststart', str(mp4)], check=True)
    # contact sheet: every kept frame, 128 px, 12 a row
    th, cols = 128, 12
    rows = (len(kept) + cols - 1) // cols
    from PIL import Image as _I
    sheet = _I.new('RGB', (cols * th, max(1, rows) * (th + 16)), 'black')
    sdr = ImageDraw.Draw(sheet)
    for k in range(len(kept)):
        fr = _I.open(frames_dir / f'f{k:03d}.png').resize((th, th))
        x, y = (k % cols) * th, (k // cols) * (th + 16)
        sheet.paste(fr, (x, y))
        sdr.text((x + 3, y + th), kept[k]['date_iso'][5:], fill=(230, 230, 230))
    sheet.save(OUT / f"{lake['id']}_sheet.png")
    # the season's p_water
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 2.2), dpi=120)
    ax.plot(range(153), [v / 100 for v in lake['pw']], color='#42a5f5', lw=2)
    ax.scatter([k['day'] for k in kept], [k['p_water'] for k in kept], s=10, color='#f4cf6a', zorder=3, label='kept frames')
    ax.set_xlim(0, 152); ax.set_ylim(0, 1.05); ax.set_ylabel('p_water'); ax.set_xlabel('day since 1 May 2019')
    ax.legend(loc='upper right', fontsize=8, frameon=False)
    ax.set_title(f"{lake['id']}  ·  {label_row['notes'] if label_row and label_row.get('notes') else 'MD'}", fontsize=10)
    fig.tight_layout(); fig.savefig(OUT / f"{lake['id']}_curve.png"); plt.close(fig)
    side = {'lake_id': lake['id'], 't0': T0.isoformat(), 'days': 153, 'fps': FPS, 'frame_count': len(kept), 'frames': kept,
            'p_water_daily': [v / 100 for v in lake['pw']], 'source': 'Earth Engine COPERNICUS/S2_SR_HARMONIZED (decision grade)',
            'center': lake['c'], 'label': label_row}
    (OUT / f"{lake['id']}.json").write_text(json.dumps(side))
    return f"{lake['id']}: {len(kept)} frames kept of {len(days)} days; cloud during the season median {np.median([k['cloud'] for k in kept]):.2f}"


def index_html(ids: list[str], lakes: dict, labels: dict) -> None:
    cards = []
    for i in ids:
        l = lakes[i]
        side = json.loads((OUT / f'{i}.json').read_text())
        lab = labels.get(i, {})
        cards.append(f"""<section>
  <h2>{i} <small>{lab.get('irr', '')}</small></h2>
  <video src="{i}.mp4" controls loop muted playsinline></video>
  <img class="curve" src="{i}_curve.png">
  <p>{side['frame_count']} frames · centre {l['c'][1]:.3f}°N {abs(l['c'][0]):.3f}°W · {lab.get('notes') or ''}</p>
  <details><summary>every kept frame</summary><img class="sheet" src="{i}_sheet.png"></details>
</section>""")
    html = f"""<!doctype html><meta charset="utf-8"><title>MD candidates</title>
<style>body{{background:#0b0b0d;color:#eee;font:15px Inter,system-ui,sans-serif;margin:24px}}
main{{display:grid;grid-template-columns:repeat(2,1fr);gap:28px}} section{{background:#15161a;border:1px solid #333;border-radius:10px;padding:14px}}
video{{width:100%;border-radius:6px}} .curve{{width:100%;margin-top:6px;border-radius:6px}} .sheet{{width:100%}} h2{{margin:0 0 8px;color:#f4cf6a}} small{{color:#aaa;font-weight:400}}</style>
<h1>Moulin-drainage candidates for the Chapter 3 label demo</h1>
<p>Sentinel-2 L2A via Earth Engine, the lake's 5.12 km tile, days with the whole tile imaged, 2 fps, Dunmire outline in MD blue. The current demo lake is CW2019_1848 (1.40 km², drains 3–14 Jun).</p>
<main>{''.join(cards)}</main>"""
    (OUT / 'index.html').write_text(html)


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else '--movies'
    ids = sys.argv[2:]
    lakes = lakes_by_id()
    OUT.mkdir(parents=True, exist_ok=True)
    if mode == '--fetch':
        import ee
        ee.Initialize()
        from concurrent.futures import ThreadPoolExecutor
        t = time.time()
        with ThreadPoolExecutor(4) as ex:
            for msg in ex.map(fetch, [lakes[i] for i in ids]):
                print(msg, f'({time.time() - t:.0f} s)')
        return
    import csv
    labels = {}
    with LABELS.open() as f:
        for r in csv.DictReader(f):
            labels[r['lake_id']] = r
    for i in ids:
        print(movie(lakes[i], labels.get(i)))
    index_html(ids, lakes, labels)
    print('open', OUT / 'index.html')


if __name__ == '__main__':
    main()
