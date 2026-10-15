"""Exploration sweep: variogram/nugget/model/conditioning choices for MGSIM.

Goal: honor the radar to <= ~1 m AND kill the node-scale grain.

Mechanism being exploited (gstatsim.okrige_sgs): a grid node coinciding with a
conditioning datum is assigned that datum EXACTLY when vario nugget == 0; with
nugget > 0 it is simulated instead, and its kriging variance reduces to exactly
the nugget -> per-node white noise of std sqrt(nugget) in NST units. So the
nugget sets both the conditioning error and the salt-and-pepper.
"""
import contextlib, io, itertools, json, os, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
DERIVED = HERE / 'data/derived'
OUT = Path(os.environ.get('SWEEP_DIR', '/path/to/a/scratch/dir/sweep'))  # scratch space the sweep scripts share
N_GRID, PX_M = 166, 150.0
FIT_RANGE, FIT_SILL = 13.5904, 0.9783        # notebook-03 fitted omni Gaussian


def load():
    trend = np.loadtxt(HERE / 'data/source_copies/2019cw428_bed_d25km_h1004_a0.792.dat')[:, 2].reshape(N_GRID, N_GRID)
    gz = np.load(DERIVED / 'gridded_bed_cw1951_150m.npz')
    I0, I1 = json.loads(str(gz['meta']))['dem_sub_lattice']
    radar = gz['bed_hm'][I0:I1 + 1, I0:I1 + 1]
    shift = float(np.nanmedian(radar - trend))
    aligned = radar - shift
    resid = aligned - trend
    lo, hi = np.nanpercentile(resid, [0.25, 99.75])
    obs = np.isfinite(resid) & (resid >= lo) & (resid <= hi)
    return trend, aligned, obs


TREND, ALIGNED, OBS = load()
CHK = (np.add.outer(np.arange(N_GRID), np.arange(N_GRID)) % 2) == 0


def run_one(cfg):
    from sklearn.preprocessing import QuantileTransformer
    from multigrid_sgsim import mgsim
    tag = cfg['tag']
    f = OUT / f'{tag}.npz'
    if f.exists():
        return json.loads(str(np.load(f, allow_pickle=True)['metrics']))
    cond = OBS & CHK if cfg['thin'] else OBS.copy()
    resid_c = (ALIGNED - TREND)[cond]
    nst = QuantileTransformer(output_distribution='normal',
                              n_quantiles=min(1000, cond.sum())).fit(resid_c.reshape(-1, 1))
    sill = FIT_SILL
    vario = [0.0, cfg['nug_frac'] * sill, FIT_RANGE * cfg['range_mult'],
             FIT_RANGE * cfg['range_mult'], sill, cfg['model']]
    if cfg['model'].lower() == 'matern':
        vario.append(cfg['s'])
    gy, gx = np.mgrid[0:N_GRID, 0:N_GRID]
    df = pd.DataFrame({'x': gx.ravel().astype(float), 'y': gy.ravel().astype(float),
                       'trend': TREND.ravel(), 'cluster': 0,
                       'value': np.where(cond, ALIGNED, np.nan).ravel()})
    df['set'] = np.isfinite(df['value']).astype(int)
    t0 = time.time()
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            out = mgsim(mg_resols=cfg['sched'], df_xyvtcs=df, vario=vario, nst_trans=nst,
                        seed=0, xx='x', yy='y', kk='cluster', num_points=cfg['k'],
                        radius=50.0, sgs_or_krige='sgs', clip_nst=True,
                        clip_percentile=cfg['clip'])
        field = out['newtrend'].values.reshape(N_GRID, N_GRID)
    except Exception as e:
        return dict(cfg, failed=repr(e)[:200])
    dt = time.time() - t0
    core = slice(20, -20)
    d2 = np.diff(field, n=2, axis=1)[core, core]
    from scipy.ndimage import gaussian_filter
    hp = float(np.std((field - gaussian_filter(field, 1.0))[core, core]))
    ec = np.abs(field[cond] - ALIGNED[cond])                 # at conditioned nodes
    eo = np.abs(field[OBS] - ALIGNED[OBS])                   # at ALL radar nodes
    m = dict(cfg,
             seconds=round(dt),
             cond_med=float(np.median(ec)), cond_p95=float(np.percentile(ec, 95)), cond_max=float(ec.max()),
             obs_med=float(np.median(eo)), obs_p95=float(np.percentile(eo, 95)),
             rough=float(np.sqrt(np.mean(d2 ** 2))), highpass=hp,
             dep_std=float(np.std((field - TREND)[core, core])),
             finite=bool(np.isfinite(field).all()))
    np.savez_compressed(f, field=field.astype(np.float32), metrics=json.dumps(m))
    return m


def build_configs(stage):
    cfgs = []
    if stage == 1:
        for model, nug, thin in itertools.product(['Gaussian', 'Spherical', 'Exponential'],
                                                  [0.0, 1e-4, 1e-2], [True, False]):
            cfgs.append(dict(model=model, nug_frac=nug, thin=thin, sched=[1], k=12,
                             range_mult=1.0, clip=100.0))
    elif stage == 2:
        # stage 1 verdict: Gaussian is far the smoothest model (18-34 m vs
        # Spherical 44, Exponential 58); nugget trades exactness against
        # numerical stability. Stage 2 attacks the untested lever -- the
        # kriging neighborhood -- plus Matern, which is smooth like Gaussian
        # but better conditioned.
        base = dict(thin=False, clip=100.0, range_mult=1.0, sched=[1], s=None)
        for nug, k in [(1e-4, 24), (1e-4, 48), (1e-5, 24), (1e-5, 48),
                       (0.0, 24), (0.0, 48), (3e-5, 24)]:
            cfgs.append(dict(base, model='Gaussian', nug_frac=nug, k=k))
        for smooth, nug in [(2.5, 1e-4), (2.5, 0.0), (1.5, 1e-4)]:
            cfgs.append(dict(base, model='Matern', nug_frac=nug, k=24, s=smooth))
        for rm in [0.5, 2.0]:
            cfgs.append(dict(base, model='Gaussian', nug_frac=1e-4, k=24, range_mult=rm))
        cfgs.append(dict(base, model='Gaussian', nug_frac=1e-4, k=24, sched=[3, 1]))
    if stage == 3:
        # stage 2 verdict: Matern fixes the zero-nugget catastrophe that ruins
        # Gaussian (rough 22 vs 126) and reaches sub-metre conditioning, while a
        # doubled range was the single strongest smoother (rough 22 -> 9.7).
        # Stage 3 combines them.
        base = dict(thin=False, clip=100.0, sched=[1], model='Matern', k=24)
        for smooth, nug, rm in [(2.5, 0.0, 2.0), (2.5, 1e-4, 2.0), (2.5, 0.0, 1.5),
                                (1.5, 0.0, 2.0), (2.5, 0.0, 3.0)]:
            cfgs.append(dict(base, s=smooth, nug_frac=nug, range_mult=rm))
        cfgs.append(dict(base, s=2.5, nug_frac=0.0, range_mult=2.0, k=48))
    if stage == 4:
        # Does the package's MULTIGRID actually smooth the realizations?
        # Controlled: the stage-3 winner, only the schedule varies.
        base = dict(thin=False, clip=100.0, model='Matern', s=1.5, nug_frac=0.0,
                    k=24, range_mult=2.0)
        for sched in [[1], [3, 1], [6, 3, 1], [12, 6, 3, 1]]:
            cfgs.append(dict(base, sched=sched))
    for c in cfgs:
        c.setdefault('s', None)
        c['tag'] = (f"s{stage}_{c['model'][:4]}{c['s'] or ''}_n{c['nug_frac']:g}_"
                    f"{'thin' if c['thin'] else 'full'}_k{c['k']}_"
                    f"mg{'-'.join(map(str, c['sched']))}_r{c['range_mult']:g}_c{c['clip']:g}")
    return cfgs


if __name__ == '__main__':
    stage = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    cfgs = build_configs(stage)
    print(f'stage {stage}: {len(cfgs)} configs, {OBS.sum()} radar nodes '
          f'({int((OBS & CHK).sum())} if thinned)', flush=True)
    from multiprocessing import Pool
    with Pool(6) as p:
        res = p.map(run_one, cfgs)
    df = pd.DataFrame(res)
    df.to_csv(OUT / f'sweep_stage{stage}.csv', index=False)
    cols = ['model', 'nug_frac', 'thin', 'k', 'sched', 'range_mult', 'clip',
            'cond_med', 'cond_p95', 'obs_med', 'rough', 'highpass', 'dep_std', 'seconds']
    cols = [c for c in cols if c in df.columns]
    print(df[cols].sort_values('rough').to_string(index=False), flush=True)
