"""Is a realization's roughness spread evenly, or drawn along the flight lines?

Global roughness is a misleading score: a map can post a low map-average while
concentrating all of its roughness into linear artifacts along the radar
tracks. This splits roughness by distance to the nearest pick. A ratio near 1
means unstructured speckle; a ratio >> 1 means the acquisition geometry is
imprinted on the bed, which would alias into the surface-stress ensemble as
features aligned with the flight paths.
"""
import json
import os
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent.parent
DERIVED = HERE / 'data/derived'
SW = Path(os.environ.get('SWEEP_DIR', '/path/to/a/scratch/dir/sweep'))  # scratch space the sweep scripts share
N = 166

trend = np.loadtxt(HERE / 'data/source_copies/2019cw428_bed_d25km_h1004_a0.792.dat')[:, 2].reshape(N, N)
R = np.load(DERIVED / 'bed_realizations_cw1951.npz')
obs = R['obs_mask']
iy, ix = np.where(obs)
gy, gx = np.mgrid[0:N, 0:N]
d = cKDTree(np.column_stack([ix, iy]).astype(float)).query(
    np.column_stack([gx.ravel(), gy.ravel()]).astype(float))[0].reshape(N, N)
core = np.zeros((N, N), bool); core[20:-20, 20:-20] = True
NEAR, FAR = core & (d <= 1.5), core & (d >= 6)


def rough_mask(b, m):
    d2 = np.full((N, N), np.nan)
    d2[:, 1:-1] = np.diff(b, n=2, axis=1)
    v = d2[m & np.isfinite(d2)]
    return float(np.sqrt(np.mean(v ** 2)))


def report(cases):
    print(f"{'field':34s}{'on tracks':>11}{'off tracks':>12}{'ratio':>8}")
    print('  roughness (m) within 1.5 px of a pick vs >= 6 px away;'
          ' ratio >> 1 = flight lines imprinted')
    for name, b in cases:
        rn, rf = rough_mask(b, NEAR), rough_mask(b, FAR)
        print(f'{name:34s}{rn:11.1f}{rf:12.1f}{rn / rf:8.2f}')


if __name__ == '__main__':
    cases = [('shipped nb-03 (nugget 1%)', R['beds'][0])]
    for tag, lab in [('s3_Mate1.5_n0_full_k24_mg1_r2_c100', 'single pass [1] (nugget 0)'),
                     ('s4_Mate1.5_n0_full_k24_mg12-6-3-1_r2_c100', 'package [12,6,3,1] (nugget 0)')]:
        p = SW / f'{tag}.npz'
        if p.exists():
            cases.append((lab, np.load(p)['field']))
    p = SW / 'tran_fields.npz'
    if p.exists():
        cases.append(('Tran [8,4,2,1] (nugget 0)', np.load(p)['Tran MG 8-4-2-1']))
    cases.append(('published bed', trend))
    report(cases)
