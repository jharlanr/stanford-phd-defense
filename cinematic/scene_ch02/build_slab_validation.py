"""Bake the Chapter 2 VALIDATION assets: the idealized periodic-slab
Elmer/Ice sweep (75 Newtonian flat-slab runs with a circular free-slip
patch) against the 2-D analytical theory (slab_theory.py, a faithful port
of the notebook cell behind PNAS SI Fig. S1 / the thesis validation
figure).

Per run (id R{R}_H{H}_a{A}_G{G}, exactly as in the filename), for each
field in FIELDS_ALL:
  fields/<id>/surf_<f>.webp       the simulation's SURFACE field
  fields/<id>/da_<f>.webp         the simulation's DEPTH-AVERAGED field
  fields/<id>/theory_<f>.webp     the analytical field
  fields/<id>/diff_<f>.webp       da − theory, on the field's vlim
  fields/<id>/diff_zoom_<f>.webp  da − theory, on vlim / 10
All five share one pixel grid: full domain, row 0 = y1 (north up),
column 0 = x0; RGB, matplotlib 'seismic' (blue −, white 0, red +) on a
symmetric ±vlim — the same colour convention as build_sim_domains.py.
1024 px (long side) for the talk's three fields, 800 px for the rest;
area-averaged (BOX) from the 50 m grid before colouring.

Fields (kPa; the netCDF stores MPa):
  txx tyy txy        Cartesian deviatoric stress (theory: polar → Cartesian)
  trr trt ttt        polar deviatoric stress about the patch centre (the
                     cell's rotation: tau_rr = txx cos² + tyy sin² + txy sin 2θ …)
  srr stt srt        in-plane Cauchy PERTURBATION, Δσ_rr = 2τ_rr + τ_θθ,
                     Δσ_θθ = 2τ_θθ + τ_rr, Δσ_rθ = τ_rθ (PNAS SI boxed forms)
  st1 st2            principals of that perturbation tensor (sim: built from
                     the level's own τ_xx, τ_yy, τ_xy — NOT the netCDF's sigma1)
No background is subtracted from the simulation (the cell does not).

Outputs: cinematic/output/slab_v1/ (manifest.json, fields/, _runs/ per-run
json, _qc/ contact sheets + the thesis-figure reproduction) → R2 ch02/slab_v1/.

Run (worktree/checkout root):
  nice -n 15 ./cinematic/.venv/bin/python -u cinematic/scene_ch02/build_slab_validation.py [--force] [RUN_ID ...]
Re-running skips runs already baked (their _runs/<id>.json exists) and
rewrites manifest.json from every baked run.
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
import xarray as xr
from PIL import Image
from matplotlib import colormaps

sys.stdout.reconfigure(line_buffering=True)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from shared import SOURCE_DATA, require_source  # noqa: E402
import slab_theory as T  # noqa: E402

NC_DIR = SOURCE_DATA / 'pnas_slab' / 'ncfiles'
OUT = HERE.parent / 'output' / 'slab_v1'
HERO = 'R5000_H3000_a01_G01'
FIELDS = ['st1', 'trr', 'txx']
FIELDS_ALL = ['st1', 'st2', 'trr', 'trt', 'ttt', 'txx', 'tyy', 'txy', 'srr', 'stt', 'srt']
KINDS = ['surf', 'da', 'theory', 'diff', 'diff_zoom']
SWEEP = {'R': [1000, 2500, 5000], 'H': [300, 1000, 2000, 3000],
         'alpha_deg': [0.1, 0.5, 1.0], 'gamma': [0.1, 1.0]}
NAME_RE = re.compile(r'flatslabnewt_(R(\d+)_H(\d+)_a(\d+)_G(\d+))_periodicBC_t0001\.nc$')
CMAP = colormaps['seismic']
NICE = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]
WEBP_Q = 90


def nice_ceil(v):
    """Smallest 'nice' number (1 · 1.5 · 2 · 2.5 · 3 · 4 · 5 · 6 · 8 × 10^k) ≥ v."""
    if not np.isfinite(v) or v <= 0:
        return 1.0
    e = 10.0 ** np.floor(np.log10(v))
    for m in NICE:
        if m * e >= v * (1 - 1e-9):
            out = m * e
            return float(round(out, 6))
    return float(10 * e)


def derived(txx, tyy, txy, theta):
    """All eleven fields from a level's Cartesian (τ_xx, τ_yy, τ_xy)."""
    trr, trt, ttt = T.cart_to_polar(txx, tyy, txy, theta)
    return finish(txx, tyy, txy, trr, trt, ttt)


def finish(txx, tyy, txy, trr, trt, ttt):
    srr, stt, srt = T.cauchy_perturbation(trr, ttt, trt)
    st1, st2 = T.principals(srr, stt, srt)
    return dict(st1=st1, st2=st2, trr=trr, trt=trt, ttt=ttt,
                txx=txx, tyy=tyy, txy=txy, srr=srr, stt=stt, srt=srt)


def to_rgb(field, vlim, size):
    """(y, x) array, y ascending → RGB image, north up, BOX-resampled."""
    a = np.flipud(np.asarray(field, np.float32))
    h, w = a.shape
    W, H = (size, round(size * h / w)) if w >= h else (round(size * w / h), size)
    a = np.asarray(Image.fromarray(a, mode='F').resize((W, H), Image.BOX))
    norm = np.clip((a + vlim) / (2 * vlim), 0, 1)
    return Image.fromarray((CMAP(norm)[..., :3] * 255).astype(np.uint8), 'RGB')


def r1(v, n=2):
    return float(round(float(v), n))


def bake_run(nc: Path, run_id, Rm, Hm, acode, gcode):
    alpha_deg = T.decode_slope(acode)
    gamma = T.decode_gamma(gcode)
    alpha = np.radians(alpha_deg)
    ds = xr.open_dataset(nc)
    x = ds['x'].values.astype(float)
    y = ds['y'].values.astype(float)
    _, _, r, theta = T.polar_grid(x, y)

    def lvl(v, l):
        return ds[v].sel(level=l).values.astype(np.float64) * 1e3  # MPa → kPa

    sim = {l: derived(lvl('tau_xx', l), lvl('tau_yy', l), lvl('tau_xy', l), theta)
           for l in ('surf', 'da')}
    ds.close()
    trr, trt, ttt = (a / 1e3 for a in T.theory_polar(x, y, Rm, Hm, alpha, gamma))
    th = finish(*T.polar_to_cart(trr, trt, ttt, theta), trr, trt, ttt)
    diff = {f: sim['da'][f] - th[f] for f in FIELDS_ALL}

    vlim, mx = {}, {'sim_da': {}, 'sim_surf': {}, 'theory': {}, 'diff_abs': {}, 'diff_p99': {}}
    for f in FIELDS_ALL:
        m_da = np.nanmax(np.abs(sim['da'][f]))
        m_th = np.nanmax(np.abs(th[f]))
        vlim[f] = nice_ceil(max(m_da, m_th))
        mx['sim_da'][f] = r1(m_da)
        mx['sim_surf'][f] = r1(np.nanmax(np.abs(sim['surf'][f])))
        mx['theory'][f] = r1(m_th)
        mx['diff_abs'][f] = r1(np.nanmax(np.abs(diff[f])))
        mx['diff_p99'][f] = r1(np.nanpercentile(np.abs(diff[f]), 99), 3)

    rel = {k: {} for k in KINDS}
    d = OUT / 'fields' / run_id
    d.mkdir(parents=True, exist_ok=True)
    for f in FIELDS_ALL:
        size = 1024 if f in FIELDS else 800
        srcs = {'surf': (sim['surf'][f], vlim[f]), 'da': (sim['da'][f], vlim[f]),
                'theory': (th[f], vlim[f]), 'diff': (diff[f], vlim[f]),
                'diff_zoom': (diff[f], vlim[f] / 10)}
        for k, (arr, vl) in srcs.items():
            p = d / f'{k}_{f}.webp'
            to_rgb(arr, vl, size).save(p, 'WEBP', quality=WEBP_Q, method=6)
            rel[k][f] = f'fields/{run_id}/{p.name}'

    entry = {
        'R': Rm, 'H': Hm, 'alpha_deg': alpha_deg, 'gamma': gamma,
        'sweep': (Rm in SWEEP['R'] and Hm in SWEEP['H']),
        'domain_km': [r1(x.min() / 1e3, 3), r1(x.max() / 1e3, 3),
                      r1(y.min() / 1e3, 3), r1(y.max() / 1e3, 3)],
        'patch_km': Rm / 1e3,
        'grid_m': r1(np.diff(x).mean(), 3),
        'scales': {'stress_kpa': r1(T.stress_scale_pa(Rm, alpha) / 1e3, 1),
                   'decay_km': r1(T.decay_length_m(Hm, gamma) / 1e3, 2)},
        'vlim_kpa': vlim,
        'max_kpa': mx,
        **rel,
    }
    qc_sheet(run_id, entry, sim['da'], th, diff)
    if run_id == HERO:
        thesis_repro(x, y, Rm, Hm, alpha_deg, gamma, sim['da'], th, diff, r)
    return entry


def qc_sheet(run_id, e, da, th, diff):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    ext = e['domain_km']
    fig, ax = plt.subplots(3, 4, figsize=(15, 11.5))
    for i, f in enumerate(FIELDS):
        v = e['vlim_kpa'][f]
        for j, (lab, a, vl) in enumerate([('sim da', da[f], v), ('theory', th[f], v),
                                          ('diff', diff[f], v), ('diff ×10', diff[f], v / 10)]):
            im = ax[i, j].imshow(a[::4, ::4], origin='lower', extent=ext, cmap='seismic',
                                 vmin=-vl, vmax=vl)
            ax[i, j].set_title(f'{f} {lab}  ±{vl:g}', fontsize=11)
            ax[i, j].add_patch(plt.Circle((0, 0), e['patch_km'], fill=False, ls='--', lw=1, color='k'))
            plt.colorbar(im, ax=ax[i, j], shrink=0.8)
    m = e['max_kpa']
    fig.suptitle(f"{run_id}  stress scale {e['scales']['stress_kpa']} kPa · decay {e['scales']['decay_km']} km  |  "
                 f"max|trr| sim {m['sim_da']['trr']} th {m['theory']['trr']} diff {m['diff_abs']['trr']} (p99 {m['diff_p99']['trr']})",
                 fontsize=12)
    fig.tight_layout()
    (OUT / '_qc').mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / '_qc' / f'qc_{run_id}.png', dpi=80)
    plt.close(fig)


def thesis_repro(x, y, R, H, alpha_deg, gamma, da, th, diff, r):
    """The thesis figure layout (rows τ_rr, τ_rθ, τ_θθ × sim | theory |
    sim − theory), the cell's plotting choices: RdBu_r, one global
    min/max over sim+theory, diff on ±1 kPa, dashed r = R."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    comps = [('trr', r'$\overline{\tau}_{rr}$'), ('trt', r'$\overline{\tau}_{r\theta}$'),
             ('ttt', r'$\overline{\tau}_{\theta\theta}$')]
    allv = [a for f, _ in comps for a in (da[f], th[f])]
    vmin = min(np.nanmin(a) for a in allv)
    vmax = max(np.nanmax(a) for a in allv)
    fig, axes = plt.subplots(3, 3, figsize=(24, 22))
    fig.subplots_adjust(top=0.93, hspace=0.4, wspace=0.4)
    xk, yk = x / 1e3, y / 1e3
    for i, (f, nm) in enumerate(comps):
        for j, (ttl, a, lo, hi) in enumerate([('Simulation', da[f], vmin, vmax),
                                               ('Theory', th[f], vmin, vmax),
                                               ('Simulation − Theory', diff[f], -1, 1)]):
            axp = axes[i, j]
            im = axp.pcolormesh(xk[::2], yk[::2], a[::2, ::2], shading='auto', cmap='RdBu_r', vmin=lo, vmax=hi)
            cb = plt.colorbar(im, ax=axp, pad=0.05, shrink=0.8)
            cb.set_label(f'{nm} (kPa)', fontsize=18)
            cb.ax.tick_params(labelsize=16)
            axp.set_title(f'{ttl} {nm}', fontsize=20, fontweight='bold')
            axp.set_xlabel('x (km)', fontsize=18)
            axp.set_ylabel('y (km)', fontsize=18)
            axp.set_aspect('equal')
            axp.tick_params(labelsize=16)
            axp.add_patch(plt.Circle((0, 0), R / 1e3, fill=False, color='black', lw=3, ls='--',
                                     label='r = R'))
            if i == 0 and j == 1:
                from matplotlib.lines import Line2D
                axp.legend([Line2D([0], [0], color='black', lw=3, ls='--')], ['r = R'],
                           loc='upper right', fontsize=16)
    c0 = T.calculate_c0(gamma, H)
    fig.suptitle(f'Simulation vs Theory Comparison\nR={R} m, H={H} m, α={alpha_deg:.1f}°, '
                 + rf'$\mathbf{{c_0}}$={c0:.1e}$\ \mathbf{{Pa\,s\,m^{{-1}}}}$', fontsize=22, fontweight='bold')
    (OUT / '_qc').mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / '_qc' / f'thesis_repro_{HERO}.png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    # the three numbers the thesis text / brief quote
    d = np.abs(diff['trr'])
    ring = np.abs(r - R) < 500
    nums = {
        'theory_trr_peak_kpa': r1(np.nanmax(np.abs(th['trr']))),
        'sim_trr_peak_kpa': r1(np.nanmax(np.abs(da['trr']))),
        'diff_trr_frac_below_0p5kpa': r1((d < 0.5).mean(), 4),
        'diff_trr_p99_kpa': r1(np.percentile(d, 99), 3),
        'diff_trr_max_kpa': r1(d.max()),
        'diff_trr_max_ring_kpa': r1(d[ring].max()),
        'diff_trr_max_off_ring_kpa': r1(d[~ring].max()),
    }
    (OUT / '_qc' / 'hero_numbers.json').write_text(json.dumps(nums, indent=1))
    print('HERO NUMBERS', json.dumps(nums))


def write_manifest(expected):
    runs = {}
    for p in sorted((OUT / '_runs').glob('*.json')):
        runs[p.stem] = json.loads(p.read_text())
    man = {
        'version': 1,
        'hero': HERO,
        'params': SWEEP,
        'fields': FIELDS,
        'fields_all': FIELDS_ALL,
        'kinds': KINDS,
        'raster': {'colormap': 'matplotlib seismic, symmetric ±vlim (diff_zoom: ±vlim/10)',
                   'orientation': 'row 0 = domain_km y1 (north up), column 0 = x0',
                   'units': 'kPa', 'diff': 'sim_da − theory'},
        'runs_expected': len(expected),
        'runs_missing': sorted(set(expected) - set(runs)),
        'runs': runs,
    }
    (OUT / 'manifest.json').write_text(json.dumps(man, separators=(',', ':')))
    print(f'manifest: {len(runs)} runs, missing {len(man["runs_missing"])}')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    force = '--force' in sys.argv
    require_source(NC_DIR)
    (OUT / '_runs').mkdir(parents=True, exist_ok=True)
    expected_file = NC_DIR.parent / 'expected_runs.txt'
    files = sorted(NC_DIR.glob('flatslabnewt_*_periodicBC_t0001.nc'))
    found = {}
    for f in files:
        m = NAME_RE.search(f.name)
        if m:
            found[m.group(1)] = (f, int(m.group(2)), int(m.group(3)), m.group(4), m.group(5))
    expected = (expected_file.read_text().split() if expected_file.exists() else list(found))
    order = sorted(found, key=lambda k: (k != HERO, k))
    for run_id in order:
        if args and run_id not in args:
            continue
        rj = OUT / '_runs' / f'{run_id}.json'
        if rj.exists() and not force:
            continue
        f, Rm, Hm, a, gm = found[run_id]
        try:
            e = bake_run(f, run_id, Rm, Hm, a, gm)
        except Exception as ex:  # a partially-copied file, etc.
            print(f'FAILED {run_id}: {ex!r}')
            continue
        rj.write_text(json.dumps(e))
        print(f"{run_id}: vlim trr {e['vlim_kpa']['trr']} | max|trr| sim {e['max_kpa']['sim_da']['trr']} "
              f"th {e['max_kpa']['theory']['trr']} diff {e['max_kpa']['diff_abs']['trr']}")
    write_manifest(expected)


if __name__ == '__main__':
    main()
