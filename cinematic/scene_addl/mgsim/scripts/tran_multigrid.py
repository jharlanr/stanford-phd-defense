"""Tran (1994)-style multiple-grid SGS, and the variogram-reproduction test.

Tran, T.T., 1994, "Improving variogram reproduction on dense simulation grids",
Computers & Geosciences 20(7-8), 1161-1168.

Difference from the multigrid_sgsim package:
  package  : every level simulates the FULL grid from a subsampled conditioning
             set, and the level results are SUMMED (a residual cascade).
  Tran here: the SIMULATION PATH is coarsened. Level L simulates only the nodes
             of an L-spaced lattice that are not yet known, conditioning on the
             data PLUS everything simulated so far. Each node is simulated ONCE;
             nothing is summed. Total cost ~ one single-level pass.

Side effect worth noting: conditioning nodes are never in the target list, so
they are honored EXACTLY by construction, whatever the nugget -- unlike the
package, where they sit in the prediction grid and are re-simulated when the
nugget is non-zero.
"""
import contextlib, io, json, os, time
from pathlib import Path
import numpy as np, pandas as pd
import gstatsim as gs
import skgstat as skg
from sklearn.preprocessing import QuantileTransformer

HERE = Path(__file__).resolve().parent.parent
DERIVED = HERE / 'data/derived'
SW = Path(os.environ.get('SWEEP_DIR', '/path/to/a/scratch/dir/sweep'))  # scratch space the sweep scripts share
N_GRID, PX_M = 166, 150.0
FIT_RANGE, FIT_SILL = 13.5904, 0.9783

trend = np.loadtxt(HERE / 'data/source_copies/2019cw428_bed_d25km_h1004_a0.792.dat')[:, 2].reshape(N_GRID, N_GRID)
gz = np.load(DERIVED / 'gridded_bed_cw1951_150m.npz')
I0, I1 = json.loads(str(gz['meta']))['dem_sub_lattice']
radar = gz['bed_hm'][I0:I1 + 1, I0:I1 + 1]
shift = float(np.nanmedian(radar - trend))
aligned = radar - shift
resid = aligned - trend
lo, hi = np.nanpercentile(resid, [0.25, 99.75])
OBS = np.isfinite(resid) & (resid >= lo) & (resid <= hi)
iy, ix = np.where(OBS)
core = slice(20, -20)

# stage-3 winning model: Matern nu=1.5, range x2, k=24 (nugget only for stability)
RANGE, K, RADIUS, NU = FIT_RANGE * 2.0, 24, 50.0, 1.5
VARIO = [0.0, 1e-4 * FIT_SILL, RANGE, RANGE, FIT_SILL, 'Matern', NU]
nst = QuantileTransformer(output_distribution='normal',
                          n_quantiles=min(1000, int(OBS.sum()))).fit(resid[OBS].reshape(-1, 1))


def tran_mgs(levels, seed=0):
    rng = np.random.default_rng(seed)
    Nres = nst.transform(resid[OBS].reshape(-1, 1)).ravel()
    sim = np.full((N_GRID, N_GRID), np.nan)
    sim[OBS] = Nres
    done = OBS.copy()
    df = pd.DataFrame({'x': ix.astype(float), 'y': iy.astype(float), 'z': Nres})
    t0 = time.time()
    for L in levels:
        yy, xx = np.mgrid[0:N_GRID:L, 0:N_GRID:L]
        tgt = np.column_stack([xx.ravel(), yy.ravel()]).astype(float)
        keep = ~done[tgt[:, 1].astype(int), tgt[:, 0].astype(int)]
        tgt = tgt[keep]
        if not len(tgt):
            continue
        with contextlib.redirect_stdout(io.StringIO()):
            vals = gs.Interpolation.okrige_sgs(tgt, df.copy(), 'x', 'y', 'z', K, VARIO,
                                               RADIUS, seed=rng, quiet=True)
        ti, tj = tgt[:, 1].astype(int), tgt[:, 0].astype(int)
        sim[ti, tj] = vals
        done[ti, tj] = True
        df = pd.concat([df, pd.DataFrame({'x': tgt[:, 0], 'y': tgt[:, 1], 'z': np.asarray(vals)})],
                       ignore_index=True)
        print(f'    level {L:2d}px: simulated {len(tgt):6d} nodes '
              f'({100*done.mean():5.1f}% known) [{time.time()-t0:.0f} s]', flush=True)
    assert done.all(), 'not every node simulated'
    return trend + nst.inverse_transform(sim.reshape(-1, 1)).reshape(N_GRID, N_GRID)


def vario_reproduction(field, n=3500, seed=0):
    """Experimental variogram OF THE REALIZATION (in NST units) vs the model.
    This is what Tran's multiple-grid is designed to fix."""
    r = nst.transform((field - trend).reshape(-1, 1)).reshape(N_GRID, N_GRID)
    rs = np.random.default_rng(seed)
    gy, gx = np.mgrid[0:N_GRID, 0:N_GRID]
    sel = rs.choice(N_GRID * N_GRID, n, replace=False)
    P = np.column_stack([gx.ravel()[sel], gy.ravel()[sel]]).astype(float)
    V = skg.Variogram(P, r.ravel()[sel], model='gaussian', maxlag=60, n_lags=30, normalize=False)
    h, emp = np.array(V.bins), np.array(V.experimental)
    # model gamma for a Matern is not in skgstat's simple set; compare against the
    # sill the model asks for at lags beyond the range (gamma -> sill)
    far = h >= RANGE
    return float(np.mean(emp[far]) / FIT_SILL), h, emp


def rough(b):
    return float(np.sqrt(np.mean(np.diff(b, n=2, axis=1)[core, core] ** 2)))


def metrics(name, b):
    e = np.abs(b[OBS] - aligned[OBS])
    try:
        ratio, h, emp = vario_reproduction(b)
    except Exception:
        ratio = float('nan')      # constant residual (e.g. the trend itself)
    return dict(method=name, obs_med=float(np.median(e)), obs_p95=float(np.percentile(e, 95)),
                rough=rough(b), dep_std=float(np.std((b - trend)[core, core])),
                vario_ratio=ratio)


rows, fields = [], {}
for levels in ([8, 4, 2, 1], [16, 8, 4, 2, 1]):
    tag = 'Tran MG ' + '-'.join(map(str, levels))
    print(f'{tag}:', flush=True)
    f = tran_mgs(levels)
    fields[tag] = f
    np.savez_compressed(SW / 'tran_fields.npz', **{k: v.astype(np.float32) for k, v in fields.items()})
    rows.append(metrics(tag, f))
    print('   ', {k: (round(v, 3) if isinstance(v, float) else v) for k, v in rows[-1].items()}, flush=True)

# baselines from the sweep, same variogram family where available
R = np.load(DERIVED / 'bed_realizations_cw1951.npz')
rows.append(metrics('shipped nb-03 (package [3,1])', R['beds'][0]))
for tag, lab in [('s3_Mate1.5_n0_full_k24_mg1_r2_c100', 'single pass [1] (sweep winner)'),
                 ('s4_Mate1.5_n0_full_k24_mg3-1_r2_c100', 'package MG [3,1]'),
                 ('s4_Mate1.5_n0_full_k24_mg12-6-3-1_r2_c100', 'package MG [12,6,3,1]')]:
    p = SW / f'{tag}.npz'
    if p.exists():
        rows.append(metrics(lab, np.load(p)['field']))
rows.append(metrics('published bed', trend))

df = pd.DataFrame(rows)
print('\n=== vario_ratio: realization variance beyond the model range, / model sill')
print('    (1.0 = reproduces the requested structure; <1 = long-range structure lost)')
print(df.round(3).to_string(index=False))
df.to_csv(SW / 'tran_comparison.csv', index=False)
print('\nsaved tran_fields.npz + tran_comparison.csv')
