"""
The APS DFD 2026 page's COLLAPSE beat (DfdCollapse.vue): the paper's Fig. 3C
re-drawn live — the depth-averaged 3-D Stokes stress perturbation along the
flow line through the patch centre, for EVERY run of the Chapter 2 slab sweep
(the 75 Elmer/Ice netCDFs behind ch02/slab_v1), baked once to one small JSON
the page fetches. The theory curves (dimensional and dimensionless) are
computed in the browser (website/src/lib/slabTheory.ts), so only the
simulation is baked.

Per run: the y = 0 row of the 'da' (depth-average) level — the mean of the
three rows nearest y = 0 (y = −50, 0, +50 m on the 50 m grid) — of τ̄_xx and
τ̄_yy (MPa in the files → kPa), combined into
  srr = 2 τ̄_xx + τ̄_yy   the Cauchy perturbation Δσ̄_rr on the flow line
                         (= 2 τ̄_rr + τ̄_θθ there; PNAS SI text before Eq. 35)
  trr = τ̄_xx            the deviatoric τ̄_rr on the flow line
subsampled to 250 m on x ∈ [−25, 25] km (201 points), rounded to 0.01 kPa.
Flow is toward +x: tension (positive) sits upstream of the patch.

Output (one file; both copies are written here):
  cinematic/data/dfd/slab_profiles_v1.json
  website/.r2-cache/dfd/slab_profiles_v1.json   (the dev server's mirror)
  { version: 1, x_km: [...] (shared), runs: { <id>: { R, H, alpha_deg,
    gamma, lambda, stress_kpa, decay_km, srr_kpa: [...], trr_kpa: [...] } } }

Run (checkout root; the netCDFs are private — fetch_sources.sh copies them
to cinematic/source_data/pnas_slab/ncfiles — or pass --ncdir):
  cinematic/.venv/bin/python cinematic/scene_addl/build_dfd_profiles.py [--ncdir DIR]
Then:
  rclone copy cinematic/data/dfd/slab_profiles_v1.json r2:<bucket>/dfd/ --header-upload 'Cache-Control: public, max-age=31536000, immutable'

QC, printed per run: the profile's max |srr| against the sweep manifest's
max over the whole domain (website/.r2-cache/ch02/slab_v1/manifest.json,
when present — the profile's must be ≤ and close) and against the theory
(scene_ch02/slab_theory.py) on the same points.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import xarray as xr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'cinematic'))
sys.path.insert(0, str(ROOT / 'cinematic' / 'scene_ch02'))
from shared import SOURCE_DATA, require_source  # noqa: E402
import slab_theory as T  # noqa: E402

NC_DIR = SOURCE_DATA / 'pnas_slab' / 'ncfiles'
OUT = ROOT / 'cinematic' / 'data' / 'dfd' / 'slab_profiles_v1.json'
R2_CACHE = ROOT / 'website' / '.r2-cache' / 'dfd' / 'slab_profiles_v1.json'
MANIFEST = ROOT / 'website' / '.r2-cache' / 'ch02' / 'slab_v1' / 'manifest.json'
NAME_RE = re.compile(r'flatslabnewt_(R(\d+)_H(\d+)_a(\d+)_G(\d+))_periodicBC_t0001\.nc$')
HALF_KM = 25.0
STEP_M = 250
ROWS = 1  # rows either side of y = 0 averaged with it


def r2(v):
    return float(round(float(v) + 0.0, 2))


def profile(nc: Path):
    """x (m) and the depth-averaged srr, trr (kPa) along y = 0, subsampled."""
    ds = xr.open_dataset(nc)
    x = ds['x'].values.astype(float)
    y = ds['y'].values.astype(float)
    j = int(np.argmin(np.abs(y)))
    rows = slice(max(0, j - ROWS), j + ROWS + 1)
    stride = max(1, int(round(STEP_M / float(np.diff(x).mean()))))
    i0 = int(np.argmin(np.abs(x + HALF_KM * 1e3)))
    i1 = int(np.argmin(np.abs(x - HALF_KM * 1e3)))
    cols = slice(i0, i1 + 1, stride)

    def row(v):
        # one strided read of three rows; MPa → kPa
        a = ds[v].sel(level='da').isel(y=rows, x=cols).values.astype(np.float64) * 1e3
        return a.mean(axis=0)

    txx = row('tau_xx')
    tyy = row('tau_yy')
    xs = x[cols]
    ds.close()
    return xs, 2 * txx + tyy, txx


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--ncdir', type=Path, default=NC_DIR, help='the sweep netCDFs (default: the source_data copy)')
    args = ap.parse_args()
    ncdir = require_source(args.ncdir)
    files = sorted(p for p in ncdir.iterdir() if NAME_RE.search(p.name))
    expected = ncdir.parent / 'expected_runs.txt'
    if expected.exists():
        want = set(expected.read_text().split())
        have = {NAME_RE.search(p.name).group(1) for p in files}
        if want - have:
            print(f'WARNING missing runs: {sorted(want - have)}')
    manifest = json.loads(MANIFEST.read_text())['runs'] if MANIFEST.exists() else {}

    x_km = None
    runs = {}
    print(f'{"run":22s} {"max|srr|":>9s} {"manifest":>9s} {"theory":>9s} {"rms/[τ]":>8s}')
    for nc in files:
        m = NAME_RE.search(nc.name)
        run_id, Rm, Hm = m.group(1), float(m.group(2)), float(m.group(3))
        alpha_deg = T.decode_slope(m.group(4))
        gamma = T.decode_gamma(m.group(5))
        alpha = np.radians(alpha_deg)
        xs, srr, trr = profile(nc)
        if x_km is None:
            x_km = [r2(v / 1e3) for v in xs]
        p = T.solution_params(Rm, Hm, alpha, gamma)
        stress_kpa = T.stress_scale_pa(Rm, alpha) / 1e3
        # the theory on the same points (y = 0: Δσ̄_rr = 2 τ̄_rr + τ̄_θθ)
        th_rr, _, th_tt = T.theory_polar(xs, np.array([0.0]), Rm, Hm, alpha, gamma)
        th = (2 * th_rr + th_tt)[0] / 1e3
        rms = float(np.sqrt(np.mean((srr - th) ** 2))) / stress_kpa
        man = manifest.get(run_id, {}).get('max_kpa', {}).get('sim_da', {}).get('srr')
        flag = '' if man is None or np.max(np.abs(srr)) <= man + 0.01 else '  ** above manifest'
        print(f'{run_id:22s} {np.max(np.abs(srr)):9.2f} {man if man is not None else float("nan"):9.2f} '
              f'{np.max(np.abs(th)):9.2f} {rms:8.3f}{flag}')
        runs[run_id] = {
            'R': Rm, 'H': Hm, 'alpha_deg': alpha_deg, 'gamma': gamma,
            'lambda': float(round(p['lambda_val'], 4)),
            'stress_kpa': r2(stress_kpa), 'decay_km': r2(T.decay_length_m(Hm, gamma) / 1e3),
            'srr_kpa': [r2(v) for v in srr], 'trr_kpa': [r2(v) for v in trr],
        }

    out = dict(version=1, x_km=x_km, runs=runs)
    text = json.dumps(out, separators=(',', ':'))
    for dst in (OUT, R2_CACHE):
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text)
    print(f'wrote {len(runs)} runs × {len(x_km)} points → {OUT.relative_to(ROOT)} + {R2_CACHE.relative_to(ROOT)} ({len(text) / 1024:.0f} KB)')
    print("\nupload:\n  rclone copy cinematic/data/dfd/slab_profiles_v1.json r2:<bucket>/dfd/ "
          "--header-upload 'Cache-Control: public, max-age=31536000, immutable'")


if __name__ == '__main__':
    main()
