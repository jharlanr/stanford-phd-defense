"""Second front: can the conditional-GRF generator honor the radar to <=1 m?

Its roughness is already ~5 m (vs 30 for SGS). The only barrier to tight
conditioning was that a Gaussian covariance over 5177 near-collinear line
points is too ill-conditioned to take a small nugget. Matern with finite
smoothness is far better conditioned -- this sweeps model x nugget x
conditioning-set and reports where both targets are met.
"""
import json, os, time
from pathlib import Path
import numpy as np, pandas as pd
from scipy.spatial.distance import cdist
from scipy.linalg import cho_factor, cho_solve
import gstools as gst

HERE = Path(__file__).resolve().parent.parent
DERIVED = HERE / 'data/derived'
OUT = Path(os.environ.get('SWEEP_DIR', '/path/to/a/scratch/dir/sweep'))  # scratch space the sweep scripts share
N_GRID, PX_M = 166, 150.0
N_SEEDS = 3

trend = np.loadtxt(HERE / 'data/source_copies/2019cw428_bed_d25km_h1004_a0.792.dat')[:, 2].reshape(N_GRID, N_GRID)
gz = np.load(DERIVED / 'gridded_bed_cw1951_150m.npz')
I0, I1 = json.loads(str(gz['meta']))['dem_sub_lattice']
radar = gz['bed_hm'][I0:I1 + 1, I0:I1 + 1]
shift = float(np.nanmedian(radar - trend))
resid = radar - shift - trend
lo, hi = np.nanpercentile(resid, [0.25, 99.75])
obs = np.isfinite(resid) & (resid >= lo) & (resid <= hi)
CHK = (np.add.outer(np.arange(N_GRID), np.arange(N_GRID)) % 2) == 0
iy, ix = np.where(obs)
P_all = np.column_stack([ix, iy]).astype(float)
r_all = resid[obs]
gy, gx = np.mgrid[0:N_GRID, 0:N_GRID]
TGT = np.column_stack([gx.ravel(), gy.ravel()]).astype(float)
core = slice(20, -20)

# --- candidate covariances, all pinned to the SAME effective range/variance -
# gstools' fit_variogram collapses len_scale -> 0 on this data (R2 < 0), so we
# do NOT refit here: we pin every model to the skgstat-fitted 2.44 km effective
# range and 3259 m^2 sill from notebook 04, and vary only the covariance SHAPE.
EFF_RANGE_PX, SILL = 16.3, 3259.0

def pinned(ctor):
    m = ctor(dim=2, var=SILL, len_scale=1.0)
    m.len_scale = EFF_RANGE_PX / m.percentile_scale(0.99)
    m.var = SILL
    return m

CANDIDATES = {
    'Gaussian':   pinned(gst.Gaussian),
    'Matern-3.5': pinned(lambda **kw: gst.Matern(nu=3.5, **kw)),
    'Matern-2.5': pinned(lambda **kw: gst.Matern(nu=2.5, **kw)),
    'Matern-1.5': pinned(lambda **kw: gst.Matern(nu=1.5, **kw)),
    'Stable-1.7': pinned(lambda **kw: gst.Stable(alpha=1.7, **kw)),
}
fits = {n: (m, None) for n, m in CANDIDATES.items()}
for name, m in CANDIDATES.items():
    print(f'{name:12s} len_scale {m.len_scale:6.2f} px · var {m.var:7.0f} m² · '
          f'eff.range {m.percentile_scale(0.99) * PX_M / 1e3:5.2f} km', flush=True)


def rough(b):
    return float(np.sqrt(np.mean(np.diff(b, n=2, axis=1)[core, core] ** 2)))


def run(model_name, nug_frac, thin):
    model, _ = fits[model_name]
    cond = obs & CHK if thin else obs
    cy_, cx_ = np.where(cond)
    P = np.column_stack([cx_, cy_]).astype(float)
    rc = resid[cond]
    t0 = time.time()
    C = model.covariance(cdist(P, P))
    jit = nug_frac * model.var
    try:
        cf = cho_factor(C + jit * np.eye(len(P)), lower=True)
    except np.linalg.LinAlgError:
        return dict(model=model_name, nug_frac=nug_frac, thin=thin, failed='not positive-definite')
    # generate unconditional fields first, then one solve for all right-hand sides
    gs_fields = []
    for s in range(N_SEEDS):
        srf = gst.SRF(model, seed=s)
        gs_fields.append(srf((np.arange(N_GRID), np.arange(N_GRID)), mesh_type='structured').T)
    RHS = np.column_stack([rc] + [g[cond] for g in gs_fields])
    W = cho_solve(cf, RHS)
    acc = np.zeros((len(TGT), W.shape[1]))
    for a in range(0, len(TGT), 2000):
        acc[a:a + 2000] = model.covariance(cdist(TGT[a:a + 2000], P)) @ W
    k_data = acc[:, 0].reshape(N_GRID, N_GRID)
    beds = np.array([trend + k_data + (g - acc[:, j + 1].reshape(N_GRID, N_GRID))
                     for j, g in enumerate(gs_fields)])
    e = np.abs(beds[:, iy, ix] - r_all[None] - trend[iy, ix][None])
    ec = np.abs(beds[:, cy_, cx_] - rc[None] - trend[cy_, cx_][None])
    return dict(model=model_name, nug_frac=nug_frac, thin=thin,
                obs_med=float(np.median(e)), obs_p95=float(np.percentile(e, 95)),
                cond_med=float(np.median(ec)),
                rough=float(np.mean([rough(b) for b in beds])),
                dep_std=float(np.mean([np.std((b - trend)[core, core]) for b in beds])),
                ens_std=float(beds.std(0)[core, core].mean()),
                max_dep=float(np.abs(beds - trend)[:, core, core].max()),
                seconds=round(time.time() - t0))


rows = []
for name in CANDIDATES:
    for nug in [1e-2, 1e-3, 1e-4, 1e-5]:
        for thin in [False, True]:
            r = run(name, nug, thin)
            rows.append(r)
            print('  ' + ' '.join(f'{k}={v}' for k, v in r.items()), flush=True)
df = pd.DataFrame(rows)
df.to_csv(OUT / 'grf_sweep.csv', index=False)
print('\n=== stable configs (max departure < 400 m), ranked by roughness ===')
good = df[(df.get('max_dep', 1e9) < 400)].sort_values('rough')
print(good.to_string(index=False))
print('\n=== honors radar to <= 1 m AND stable ===')
print(good[good.obs_med <= 1.0].to_string(index=False))
