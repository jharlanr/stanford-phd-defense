"""The "Label lakes yourself" door: the season movies of the
ESSD inter-rater 200 (100 CW2018 + 100 CW2019 lakes) and the deck the page
deals from.

The movies follow build_callout_movies.py's rules, which are the labelers'
evidence: every Sentinel-2 frame with pct_nans < 1 (the whole tile imaged)
is kept, cloudy frames INCLUDED (the labelers saw them); days with no
acquisition are simply not frames; 1 fps; a keyframe every GOP frames and
no B-frames so a seek decodes at most GOP frames. The p_water curve in the
sidecar stays on the full 153-day axis (T0 = <year>-05-01).

One deliberate difference: the lake outline burned into the frames is
lakelabel's RED (the director asked for a red lake outline; the GUI,
sat_tile_stack/labeling.py api_frame, draws the mask contour with
matplotlib colors="red" = #ff0000), the same on every lake — never the
class colour (the Ch.3 callouts wear their class colour because they are
the class examples; here that would give the answer away). The first
bake (R2 ch03/irr/) was white.

Imagery: the stacks for all 200 live on Oak (the lab's cluster storage,
mounted at $CLUSTER_MOUNT; stacks_v2, ~140 MB each, 28 GB in all). Oak is
READ-ONLY to this script. A lake whose stack is
already in cinematic/source_data/stacks/CW_<year>/ is read there; any
other is copied ONE AT A TIME into source_data/stacks/_irr_stage/, baked,
and the staged copy deleted. If Oak is not mounted (or unmounts mid-run)
the run stops, says which lakes are done, and writes the rest to
output_irr/_todo.txt; re-running skips every lake whose <id>.mp4 AND
<id>.json exist, so it RESUMES where it stopped.

A bake can stop part-way when the mount drops: the lakes left are in
output_irr/_todo.txt. RESUME when Oak is mounted again
(`ls ${CLUSTER_MOUNT}/sherlock_sattilestack/stacks_v2/CW_2018 | wc -l` → 679):
  nice -n 15 python -u cinematic/scene_ch03/build_irr_movies.py
then, only once _todo.txt is EMPTY, the upload below and the one-line flip
in SectionLabelLakes.vue (IRR_MOVIES 'ch03/irr' → 'ch03/irr2'). Until then
the page keeps the complete white set (one outline colour for all 200).

Outputs (cinematic/scene_ch03/output_irr/ → R2 ch03/irr2/ — a NEW prefix
for the red bake, so the immutable Cache-Control is safe and the white
ch03/irr/ keeps serving the live site until all 200 are red):
  <id>.mp4    kept frames only (see above)
  <id>.json   {lake_id, year, t0, days, fps, frame_count, frames:[{day,
              date_iso, p_water}], p_water_daily:[153 values | null]}
  deck.json   per lake {id, year, consensus, experts:[{hard, p:[ND,HF,MD,
              LD,CD]} ×3], contested, split, votes, majority} + the
              paper's reference numbers, recomputed here and checked
              against ch03/essd_irr.json — the site never parses CSV.

`consensus` is the reference CSV's `label`. That column equals Labeler 1's
hard label for all 200 lakes (it is the dataset's PRIMARY label — the
paper: "The lead author's labels constitute the primary labels"), so the
deck also carries `majority` (the 2-of-3 vote, null for the five three-way
splits).

Run (from the defense checkout root):
  nice -n 15 python -u \
      cinematic/scene_ch03/build_irr_movies.py [--deck-only] [--todo]
      [--ids A,B] [--size 512] [--crf 25] [--limit N] [--force]
  (--todo only rewrites output_irr/_todo.txt from what is on disk)
  then, with _todo.txt empty
  rclone copy cinematic/scene_ch03/output_irr r2:<bucket>/ch03/irr2/ \
      --exclude '_frames/**' \
      --header-upload "Cache-Control: public, max-age=31536000, immutable"
"""

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared import SOURCE_DATA, require_source  # noqa: E402

IRR_DIR = SOURCE_DATA / 'essd' / 'irr'
LOCAL_STACKS = SOURCE_DATA / 'stacks'
STAGE_DIR = LOCAL_STACKS / '_irr_stage'
OAK_STACKS = Path(os.environ.get('CLUSTER_MOUNT', '/path/to/your/cluster/mount')) / 'sherlock_sattilestack' / 'stacks_v2'
OUT_DIR = Path('cinematic/scene_ch03/output_irr')
FRAMES_DIR = OUT_DIR / '_frames'
ESSD_IRR_JSON = Path('website/.r2-cache/ch03/essd_irr.json')

CLASSES = ['ND', 'HF', 'MD', 'LD', 'CD']  # the paper's order
S2_QUANT = 10000.0
MAX_PCT_NANS = 1.0  # percent of the tile unimaged
OUTLINE_RGB = (255, 0, 0)  # lakelabel's matplotlib 'red'
GOP = '6'


# ── the deck ──────────────────────────────────────────────────────────────
def read_irr() -> tuple[list[str], dict, dict]:
    ref = {}
    with open(require_source(IRR_DIR / 'irr_subset_reference.csv')) as f:
        for r in csv.DictReader(f):
            ref[r['lake_id']] = r['label']
    experts: dict[str, dict[int, dict]] = {}
    for k in (1, 2, 3):
        for y in (2018, 2019):
            with open(require_source(IRR_DIR / f'irr_labels_labeler{k}_CW_{y}.csv')) as f:
                for r in csv.DictReader(f):
                    p = [float(r[f'p_{c}']) for c in CLASSES]
                    experts.setdefault(r['lake_id'], {})[k] = {'hard': r['label'], 'p': p}
    ids = sorted(ref)
    assert set(ids) == set(experts) and len(ids) == 200, 'IRR files disagree on the 200'
    for i in ids:
        assert set(experts[i]) == {1, 2, 3}, i
    return ids, ref, experts


def fleiss_kappa(rows: list[list[str]]) -> float:
    n = len(rows[0])
    N = len(rows)
    pj = Counter()
    P = 0.0
    for labs in rows:
        c = Counter(labs)
        P += (sum(v * v for v in c.values()) - n) / (n * (n - 1))
        for k, v in c.items():
            pj[k] += v / (N * n)
    P /= N
    Pe = sum(v * v for v in pj.values())
    return (P - Pe) / (1 - Pe)


def cohen_kappa(a: list[str], b: list[str]) -> float:
    N = len(a)
    po = sum(x == y for x, y in zip(a, b)) / N
    pe = sum((a.count(c) / N) * (b.count(c) / N) for c in CLASSES)
    return (po - pe) / (1 - pe)


def build_deck() -> dict:
    ids, ref, experts = read_irr()
    lakes = []
    for i in ids:
        hard = [experts[i][k]['hard'] for k in (1, 2, 3)]
        votes = Counter(hard)
        top, n_top = votes.most_common(1)[0]
        contested = len(votes) > 1
        lakes.append({
            'id': i,
            'year': int(i[2:6]),
            'consensus': ref[i],
            'majority': top if n_top >= 2 else None,
            'experts': [{'hard': experts[i][k]['hard'], 'p': experts[i][k]['p']} for k in (1, 2, 3)],
            'contested': contested,
            'split': '/'.join(sorted(votes)) if contested else None,
            # class → how many of the three chose it, the larger first
            'votes': dict(sorted(votes.items(), key=lambda kv: (-kv[1], CLASSES.index(kv[0])))),
        })

    # The paper's numbers, recomputed from the same CSVs.
    rows = [[e['hard'] for e in L['experts']] for L in lakes]
    col = {k: [r[k - 1] for r in rows] for k in (1, 2, 3)}
    unanimous = sum(not L['contested'] for L in lakes) / len(lakes)
    pair_agree = {f'{a}{b}': sum(x == y for x, y in zip(col[a], col[b])) / len(lakes)
                  for a, b in ((1, 2), (1, 3), (2, 3))}
    pair_kappa = {f'{a}{b}': cohen_kappa(col[a], col[b]) for a, b in ((1, 2), (1, 3), (2, 3))}
    fk = fleiss_kappa(rows)
    ref_is_l1 = sum(L['consensus'] == L['experts'][0]['hard'] for L in lakes)

    paper = None
    if ESSD_IRR_JSON.exists():
        paper = json.loads(ESSD_IRR_JSON.read_text())
        assert abs(paper['fleiss_kappa'] - round(fk, 3)) < 1e-9, (paper['fleiss_kappa'], fk)
        assert abs(paper['all3_agree'] - unanimous) < 1e-9
        for p in paper['pairs']:
            assert abs(p['agreement'] - pair_agree[f"{p['row']}{p['col']}"]) < 1e-9

    print(f'deck: {len(lakes)} lakes · {sum(L["contested"] for L in lakes)} contested · '
          f'unanimous {unanimous:.3f} · Fleiss κ {fk:.4f} · pairwise '
          + ' '.join(f'{k}:{v:.3f}/κ{pair_kappa[k]:.3f}' for k, v in pair_agree.items())
          + f' · reference == Labeler 1 on {ref_is_l1}/200'
          + (' · matches essd_irr.json' if paper else ' · (essd_irr.json not found, unchecked)'))
    return {
        'class_order': CLASSES,
        # Labelers 2 and 3 stay anonymous on the site (the director asked
        # for no initials on them); Labeler 1 is the lead author.
        'labelers': [
            {'n': 1, 'initials': 'J. H. R.'},
            {'n': 2},
            {'n': 3},
        ],
        'paper': {
            'n': len(lakes),
            'all3_agree': round(unanimous, 4),
            'fleiss_kappa': round(fk, 4),
            'pairwise_agree': {k: round(v, 4) for k, v in pair_agree.items()},
            'pairwise_kappa': {k: round(v, 4) for k, v in pair_kappa.items()},
        },
        'consensus_note': 'consensus = irr_subset_reference.csv label = Labeler 1 (the primary label) on all 200',
        'lakes': lakes,
    }


# ── the movies ────────────────────────────────────────────────────────────
def lake_outline_mask(lake_boundary: np.ndarray, thickness: int = 2) -> np.ndarray:
    """build_featured_lakes.py's outline recipe."""
    m = (lake_boundary > 0).astype(np.uint8)
    pad = np.pad(m, 1, mode='edge')
    nb_min = np.minimum.reduce([
        pad[0:-2, 0:-2], pad[0:-2, 1:-1], pad[0:-2, 2:],
        pad[1:-1, 0:-2],                  pad[1:-1, 2:],
        pad[2:,   0:-2], pad[2:,   1:-1], pad[2:,   2:],
    ])
    outline = (m == 1) & (nb_min == 0)
    for _ in range(thickness - 1):
        pad = np.pad(outline.astype(np.uint8), 1, mode='edge')
        nb_max = np.maximum.reduce([
            pad[0:-2, 1:-1], pad[1:-1, 0:-2], pad[1:-1, 2:], pad[2:, 1:-1],
        ])
        outline = nb_max > 0
    return outline


def encode(lake_id: str, crf: str) -> Path:
    out_mp4 = OUT_DIR / f'{lake_id}.mp4'
    subprocess.run([
        'ffmpeg', '-y', '-loglevel', 'error',
        '-framerate', '1', '-i', str(FRAMES_DIR / lake_id / 'f%04d.png'),
        '-c:v', 'libx264', '-crf', crf, '-preset', 'slow', '-pix_fmt', 'yuv420p',
        '-g', GOP, '-bf', '0',
        '-movflags', '+faststart', '-r', '1', str(out_mp4),
    ], check=True)
    return out_mp4


def oak_mounted() -> bool:
    return OAK_STACKS.is_dir() and (OAK_STACKS / 'CW_2018').is_dir()


def stack_path(lake_id: str) -> tuple[Path, bool]:
    """(path, staged?) — a local copy when there is one, else a staged copy
    from Oak (read-only: copied, never moved)."""
    year = lake_id[2:6]
    local = LOCAL_STACKS / f'CW_{year}' / f'{lake_id}.nc'
    if local.exists():
        return local, False
    if not oak_mounted():
        raise RuntimeError('Oak is not mounted')
    src = OAK_STACKS / f'CW_{year}' / f'{lake_id}.nc'
    if not src.exists():
        raise FileNotFoundError(src)
    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    for old in STAGE_DIR.glob('*.nc'):  # one lake at a time, always
        old.unlink()
    dst = STAGE_DIR / f'{lake_id}.nc'
    # /bin/cp, not shutil.copyfile: over the Oak SMB mount (VPN) the
    # latter ran ~4x slower (107 s vs 29 s for one stack).
    try:
        subprocess.run(['cp', str(src), str(dst)], check=True)
    except BaseException:
        dst.unlink(missing_ok=True)
        raise
    return dst, True


def build_movie(lake_id: str, size: int, crf: str) -> dict:
    import xarray as xr

    year = lake_id[2:6]
    t0, t1 = f'{year}-05-01', f'{year}-09-30'
    path, staged = stack_path(lake_id)
    try:
        ds = xr.open_dataset(path)
        t = ds['time'].values
        sel = (t >= np.datetime64(t0)) & (t <= np.datetime64(t1 + 'T23:59:59'))
        ds = ds.isel(time=sel)
        n = ds.sizes['time']
        times = ds['time'].values
        pct_nans = ds['pct_nans'].values
        p_water = ds['p_water'].values
        band_names = [str(x) for x in ds['common_name'].values]
        rgb_idx = [band_names.index(b) for b in ('red', 'green', 'blue')]
        boundary = ds['lake_boundary'].values
        cube = ds['reflectance'].isel(band=rgb_idx).values  # one read
        ds.close()
    finally:
        if staged:
            path.unlink(missing_ok=True)

    H, W = boundary.shape
    if size != W:
        b_small = np.array(Image.fromarray((boundary > 0).astype(np.uint8) * 255)
                           .resize((size, size), Image.NEAREST)) > 127
        outline = lake_outline_mask(b_small, thickness=2)
    else:
        outline = lake_outline_mask(boundary, thickness=2)

    day0 = np.datetime64(t0)
    fdir = FRAMES_DIR / lake_id
    shutil.rmtree(fdir, ignore_errors=True)
    fdir.mkdir(parents=True, exist_ok=True)
    kept = []
    for i in range(n):
        pn = pct_nans[i]
        if not np.isfinite(pn) or pn >= MAX_PCT_NANS:
            continue
        refl = cube[i]
        if np.isnan(refl).all():
            continue
        r = np.clip(np.nan_to_num(refl) / S2_QUANT, 0.0, 1.0)
        frame = (np.transpose(r, (1, 2, 0)) * 255.0).clip(0, 255).astype(np.uint8)
        if size != W:
            frame = np.array(Image.fromarray(frame).resize((size, size), Image.LANCZOS))
        frame[outline] = OUTLINE_RGB
        Image.fromarray(frame).save(fdir / f'f{len(kept):04d}.png', compress_level=1)
        day = int((times[i].astype('datetime64[D]') - day0) / np.timedelta64(1, 'D'))
        pw = p_water[i]
        kept.append({
            'day': day,
            'date_iso': str(times[i])[:10],
            'p_water': None if np.isnan(pw) else round(float(pw), 4),
        })
    if not kept:
        raise RuntimeError(f'{lake_id}: no valid frames')

    out_mp4 = encode(lake_id, crf)
    shutil.rmtree(fdir, ignore_errors=True)

    sidecar = {
        'lake_id': lake_id,
        'year': int(year),
        't0': t0,
        'days': n,
        'fps': 1.0,
        'frame_count': len(kept),
        'size': size,
        'valid_rule': f'pct_nans < {MAX_PCT_NANS} (percent of the tile unimaged)',
        'frames': kept,
        'p_water_daily': [None if np.isnan(p) else round(float(p), 4) for p in p_water],
        'source': 'Sentinel-2 L2A · Microsoft Planetary Computer',
    }
    (OUT_DIR / f'{lake_id}.json').write_text(json.dumps(sidecar, separators=(',', ':')))
    return {'frames': len(kept), 'days': n, 'mb': out_mp4.stat().st_size / 1e6, 'staged': staged}


def baked(lake_id: str) -> bool:
    """A lake is done when both its movie and its sidecar exist (the
    sidecar is written last, after the encode)."""
    return (OUT_DIR / f'{lake_id}.mp4').exists() and (OUT_DIR / f'{lake_id}.json').exists()


def write_todo(all_ids: list[str]) -> list[str]:
    todo = [i for i in all_ids if not baked(i)]
    (OUT_DIR / '_todo.txt').write_text(''.join(f'{i}\n' for i in todo))
    print(f'todo: {len(todo)} of {len(all_ids)} lakes unbaked → {OUT_DIR / "_todo.txt"}')
    return todo


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--deck-only', action='store_true')
    ap.add_argument('--todo', action='store_true')
    ap.add_argument('--ids', default='')
    ap.add_argument('--size', type=int, default=512)
    ap.add_argument('--crf', default='25')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--force', action='store_true')
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    deck = build_deck()
    (OUT_DIR / 'deck.json').write_text(json.dumps(deck, separators=(',', ':')))
    if args.deck_only:
        return
    all_ids = [L['id'] for L in deck['lakes']]
    if args.todo:
        write_todo(all_ids)
        return

    ids = list(all_ids)
    if args.ids:
        want = args.ids.split(',')
        ids = [i for i in ids if i in want]
    # Contested lakes first: the page deals them first, so they land first.
    contested = {L['id'] for L in deck['lakes'] if L['contested']}
    ids.sort(key=lambda i: (i not in contested, i))

    done, failed, total_mb = [], [], 0.0
    t_start = time.time()
    for k, lake_id in enumerate(ids):
        if args.limit and len(done) >= args.limit:
            break
        if baked(lake_id) and not args.force:
            total_mb += (OUT_DIR / f'{lake_id}.mp4').stat().st_size / 1e6
            done.append(lake_id)
            continue
        try:
            t = time.time()
            r = build_movie(lake_id, args.size, args.crf)
        except (RuntimeError, OSError, subprocess.CalledProcessError) as e:
            # Oak can vanish between the mount check and the copy
            # (a FileNotFoundError mid-run has happened) — either way, stop.
            if not oak_mounted() or 'Oak is not mounted' in str(e):
                print(f'STOP: Oak unmounted at {lake_id}; {len(done)} lakes done, '
                      f'{len(ids) - len(done)} to go (re-run to resume)')
                break
            failed.append((lake_id, str(e)))
            print(f'  {lake_id}: FAILED {e}')
            continue
        total_mb += r['mb']
        done.append(lake_id)
        print(f'  [{k + 1:3d}/{len(ids)}] {lake_id}: {r["frames"]}/{r["days"]} frames · '
              f'{r["mb"]:.2f} MB · {time.time() - t:.0f} s{" (staged)" if r["staged"] else ""}')
    print(f'\n{len(done)} lakes done · {len(failed)} failed · {total_mb:.0f} MB · '
          f'{(time.time() - t_start) / 60:.1f} min')
    for f in failed:
        print('  failed:', *f)
    if write_todo(all_ids):
        print('NOT uploading a partial set: re-run when Oak is mounted.')
        return
    print('\nupload:\n  rclone copy cinematic/scene_ch03/output_irr r2:<bucket>/ch03/irr2/ '
          "--exclude '_frames/**' "
          '--header-upload "Cache-Control: public, max-age=31536000, immutable"')


if __name__ == '__main__':
    main()
