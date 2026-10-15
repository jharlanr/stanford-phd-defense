"""Bake the Chapter 2 TALK slab assets v2 (R2 ch02/slab_v2/): the
CUMULATIVE depth average of the periodic-slab Elmer/Ice runs, level by
level from the surface down, plus the theory and sim_da − theory, all on
ONE fixed colour scale ±300 kPa (contract E_contract_v2: the stress
pattern projected to the surface is the value of the in-progress depth
averaging, as the director specified).

Reuses v1 (build_slab_validation.py) for the theory port (slab_theory.py),
the field derivations, the rasteriser (seismic RGB WebP, north up, BOX)
and its conventions; only the 3-D read is new.

THE 3-D READ (the lab's recipe, make_ncfiles_flatslabnewt.ipynb
`fieldstack_fast`, followed exactly where it applies):
  * grid: the top surface (GeometryIds 106) x/y span, gridres 50 m,
    border 0, recentred to (0, 0) — the netCDFs' x/y, asserted equal.
  * the mesh is an extruded wedge mesh: N node layers at equal fractions
    of H (12 for these runs → K = 11). Each node layer is gridded with
    the lab's own surface-branch interpolator (scipy griddata 'linear' on
    the layer's nodes, 'nearest' where linear is NaN); one Delaunay serves
    every layer (same x/y footprint). Layer 0 = the surface → identical to
    the netCDF's `surf` level.
  * cum_k = (1/z_k) ∫_0^{z_k} τ dz' by the trapezoid rule over the node
    layers (z measured down from the surface; cum_0 = the surface field;
    cum_K = the full depth average).
  * CHECKS, printed per run:
      surf  : layer 0 vs the netCDF `surf`          (the gridding)
      GL3   : the lab's 3-point Gauss–Legendre average, linear-in-z between
              layers (= what the wedge probe returns) vs the netCDF `da`
              (the probe / weighting reproduce the lab's)
      cum_K : the trapezoid full average vs the netCDF `da` (the contract's
              check; the two quadratures differ only by the profile's
              curvature)
    and, for the hero, theory vs sim_da peak τ_rr.

σ_t1 = the in-plane principal of the Cauchy PERTURBATION from the
(cumulative-)averaged τ_xx/τ_yy/τ_xy (v1's `derived`).

Input: ONE staged VTU at a time, staged by
  bash cinematic/fetch_sources.sh slab_vtu <RUN_ID>
→ cinematic/source_data/pnas_slab/vtu/; this script deletes that staged
copy after baking the run (disk). It never reads the Drive.

Output: cinematic/output/slab_v2/
  manifest.json
  fields/<id>/cum/<f>_<k>.webp       k = 0 … K   (surf ≡ k 0, da ≡ k K)
  fields/<id>/theory_<f>.webp, fields/<id>/diff_<f>.webp
  _runs/<id>.json, _qc/qc_<id>.png, _qc/cum_<hero>.gif, _qc/checks.json

Run (worktree root):
  nice -n 15 ./cinematic/.venv/bin/python -u cinematic/scene_ch02/build_slab_v2.py [--force] [--keep] [RUN_ID ...]
With no RUN_IDs it does all 32 (hero first), staging each in turn; runs
already baked (_runs/<id>.json) are skipped unless --force.
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import xarray as xr
from scipy.spatial import Delaunay, cKDTree

sys.stdout.reconfigure(line_buffering=True)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from shared import SOURCE_DATA, require_source  # noqa: E402
import slab_theory as T  # noqa: E402
from build_slab_validation import to_rgb, r1, WEBP_Q  # noqa: E402

NC_DIR = SOURCE_DATA / 'pnas_slab' / 'ncfiles'
VTU_DIR = SOURCE_DATA / 'pnas_slab' / 'vtu'
FETCH = HERE.parent / 'fetch_sources.sh'
OUT = HERE.parent / 'output' / 'slab_v2'
HERO = 'R2500_H1000_a10_G01'
FIELDS = ['st1', 'trr', 'txx']
VLIM = 300.0  # kPa, every raster
SIZE = 1024
MAX_LEVELS = 16
PARAMS = {'R': [2500, 5000], 'H': [300, 1000, 2000, 3000],
          'alpha_deg': [0.5, 1.0], 'gamma': [0.1, 1.0]}
A_CODE = {0.5: '05', 1.0: '10'}
G_CODE = {0.1: '01', 1.0: '1'}
GRIDRES_M = 50
TOP_ID = 106


def run_ids():
    ids = [f'R{R}_H{H}_a{A_CODE[a]}_G{G_CODE[g]}'
           for R in PARAMS['R'] for H in PARAMS['H']
           for a in PARAMS['alpha_deg'] for g in PARAMS['gamma']]
    return sorted(ids, key=lambda k: (k != HERO, k))


def vtu_name(run_id):
    return f'flatslabnewt_{run_id}_periodicBC_t0001.vtu'


def nc_name(run_id):
    return f'flatslabnewt_{run_id}_periodicBC_t0001.nc'


# ── the 3-D read ───────────────────────────────────────────────────────
class LayerGridder:
    """griddata(method='linear') with nearest fallback — the lab's
    _grid_surface_field — split so the Delaunay + barycentric weights are
    built once and applied to every layer and component."""

    def __init__(self, x, y, XI, YI):
        pts = np.column_stack([x, y])
        q = np.column_stack([XI.ravel(), YI.ravel()])
        tri = Delaunay(pts)
        s = tri.find_simplex(q)
        self.inside = s >= 0
        si = s[self.inside]
        Tm = tri.transform[si]
        b = np.einsum('nij,nj->ni', Tm[:, :2], q[self.inside] - Tm[:, 2])
        self.w = np.column_stack([b, 1 - b.sum(1)])
        self.v = tri.simplices[si]
        self.shape = XI.shape
        self.near = None
        if not self.inside.all():
            self.near = cKDTree(pts).query(q[~self.inside])[1]

    def __call__(self, vals):
        out = np.empty(self.inside.size, np.float64)
        out[self.inside] = (vals[self.v] * self.w).sum(1)
        if self.near is not None:
            out[~self.inside] = vals[self.near]
        return out.reshape(self.shape)


def read_layers(vtu: Path):
    """Return (x, y, zfrac, layers) with layers[c] = (L, ny, nx) arrays in
    kPa for c in txx/tyy/txy, layer 0 = surface, zfrac = depth / H."""
    import pyvista as pv
    mesh = pv.read(str(vtu))
    surf = mesh.extract_surface()
    top = surf.extract_cells(surf.cell_data['GeometryIds'] == TOP_ID)
    x, y = top.points[:, 0], top.points[:, 1]
    span_x, span_y = x.max() - x.min(), y.max() - y.min()
    xi = np.linspace(x.min(), x.max(), max(2, int(round(span_x / GRIDRES_M)) + 1))
    yi = np.linspace(y.min(), y.max(), max(2, int(round(span_y / GRIDRES_M)) + 1))
    XI, YI = np.meshgrid(xi, yi)
    xc = (XI - 0.5 * (XI.min() + XI.max())).astype(np.float32)[0, :]
    yc = (YI - 0.5 * (YI.min() + YI.max())).astype(np.float32)[:, 0]

    P = mesh.points
    zs = mesh.point_data['zsdem']
    zb = mesh.point_data['beddem']
    H = zs - zb
    frac = np.round((zs - P[:, 2]) / H, 6)  # depth fraction from the surface
    levels = np.unique(frac)
    comp = {'txx': 'stress 1', 'tyy': 'stress 2', 'txy': 'stress 4'}
    gridder, key0 = None, None
    layers = {c: [] for c in comp}
    for lv in levels:
        idx = np.nonzero(frac == lv)[0]
        key = np.round(P[idx, :2], 3)
        order = np.lexsort((key[:, 1], key[:, 0]))
        idx, key = idx[order], key[order]
        if gridder is None:
            # the lab grids the surface from the TOP cells' points; same footprint
            assert len(idx) == len(np.unique(np.round(np.column_stack([x, y]), 3), axis=0)), 'footprint'
            gridder = LayerGridder(P[idx, 0], P[idx, 1], XI, YI)
            key0 = key
        else:
            assert np.array_equal(key, key0), f'layer {lv} footprint differs'
        for c, name in comp.items():
            layers[c].append(gridder(mesh.point_data[name][idx].astype(np.float64) * 1e3))
    layers = {c: np.stack(v) for c, v in layers.items()}
    return xc, yc, levels.astype(float), layers


def cumulative(lay, zf):
    """(L, ny, nx) layers at depth fractions zf (0 = surface) → cum (L, ny, nx):
    cum_0 = surface, cum_k = trapezoid mean over [0, zf_k]."""
    out = np.empty_like(lay)
    out[0] = lay[0]
    acc = np.zeros_like(lay[0])
    for k in range(1, len(zf)):
        acc += 0.5 * (lay[k - 1] + lay[k]) * (zf[k] - zf[k - 1])
        out[k] = acc / zf[k]
    return out


def gl3(lay, zf):
    """The lab's GL3 depth average, linear-in-z between layers (the wedge probe)."""
    t = np.array([0.5 - 0.5 * np.sqrt(3 / 5), 0.5, 0.5 + 0.5 * np.sqrt(3 / 5)])  # from the bed
    w = np.array([5 / 9, 8 / 9, 5 / 9]) * 0.5
    w = w / w.sum()
    tot = 0.0
    for ti, wi in zip(t, w):
        d = 1.0 - ti  # depth fraction from the surface
        k = min(np.searchsorted(zf, d, side='right') - 1, len(zf) - 2)
        f = (d - zf[k]) / (zf[k + 1] - zf[k])
        tot = tot + wi * ((1 - f) * lay[k] + f * lay[k + 1])
    return tot


def subsample(zf, L):
    """≤ MAX_LEVELS levels, evenly in depth, always keeping 0 and 1."""
    if L <= MAX_LEVELS:
        return list(range(L))
    want = np.linspace(0, 1, MAX_LEVELS)
    return sorted({int(np.argmin(np.abs(zf - w))) for w in want})


def talk_fields(txx, tyy, txy, theta):
    """v1's `derived`, cut to the talk's three fields (float32: 12 levels × 4 M px)."""
    trr, _, _ = T.cart_to_polar(txx, tyy, txy, theta)
    sxx, syy, sxy = T.cauchy_perturbation(txx, tyy, txy)  # basis-free; principals are invariant
    st1, _ = T.principals(sxx, syy, sxy)
    return {'st1': st1.astype(np.float32), 'trr': trr.astype(np.float32), 'txx': txx.astype(np.float32)}


# ── bake ───────────────────────────────────────────────────────────────
def bake_run(run_id, vtu: Path):
    R, Hm, acode, gcode = run_id.split('_')
    Rm, Hm = int(R[1:]), int(Hm[1:])
    alpha_deg, gamma = T.decode_slope(acode[1:]), T.decode_gamma(gcode[1:])
    alpha = np.radians(alpha_deg)

    x, y, zf, lay = read_layers(vtu)
    ds = xr.open_dataset(NC_DIR / nc_name(run_id))
    assert np.allclose(ds['x'].values, x) and np.allclose(ds['y'].values, y), 'grid ≠ netCDF grid'
    nc = {(c, l): ds[f'tau_{c[1:]}'].sel(level=l).values.astype(np.float64) * 1e3
          for c in lay for l in ('surf', 'da')}
    ds.close()

    keep = subsample(zf, len(zf))
    cum = {c: cumulative(lay[c], zf)[keep] for c in lay}
    zk = zf[keep]
    K = len(keep) - 1

    chk = {'L': int(len(zf)), 'K': K}
    for c in lay:
        chk[f'surf_{c}'] = r1(np.nanmax(np.abs(lay[c][0] - nc[(c, 'surf')])), 4)
        chk[f'gl3_{c}'] = r1(np.nanmax(np.abs(gl3(lay[c], zf) - nc[(c, 'da')])), 4)
        chk[f'cumK_{c}'] = r1(np.nanmax(np.abs(cum[c][-1] - nc[(c, 'da')])), 4)
        dk = np.abs(cum[c][-1] - nc[(c, 'da')])
        chk[f'cumK_p99_{c}'] = r1(np.nanpercentile(dk, 99), 4)
        chk[f'cumK_frac_gt_0p5_{c}'] = r1((dk > 0.5).mean(), 6)
    print(f'  {run_id} K={K} | max|Δ| kPa  surf ' +
          ' '.join(f"{c} {chk[f'surf_{c}']}" for c in lay) + ' | GL3 vs nc da ' +
          ' '.join(f"{c} {chk[f'gl3_{c}']}" for c in lay) + ' | cum_K vs nc da ' +
          ' '.join(f"{c} {chk[f'cumK_{c}']} (p99 {chk[f'cumK_p99_{c}']})" for c in lay))

    _, _, r, theta = T.polar_grid(x, y)
    levels = [talk_fields(cum['txx'][k], cum['tyy'][k], cum['txy'][k], theta) for k in range(K + 1)]
    del cum, lay
    trr, trt, ttt = (a / 1e3 for a in T.theory_polar(x, y, Rm, Hm, alpha, gamma))
    th = talk_fields(*T.polar_to_cart(trr, trt, ttt, theta), theta)
    da = levels[-1]
    diff = {f: da[f] - th[f] for f in FIELDS}

    d = OUT / 'fields' / run_id
    (d / 'cum').mkdir(parents=True, exist_ok=True)
    rel = {'cum': {f: [] for f in FIELDS}, 'theory': {}, 'diff': {}}
    for f in FIELDS:
        for k in range(K + 1):
            p = d / 'cum' / f'{f}_{k}.webp'
            to_rgb(levels[k][f], VLIM, SIZE).save(p, 'WEBP', quality=WEBP_Q, method=6)
            rel['cum'][f].append(f'fields/{run_id}/cum/{p.name}')
        for kind, arr in (('theory', th[f]), ('diff', diff[f])):
            p = d / f'{kind}_{f}.webp'
            to_rgb(arr, VLIM, SIZE).save(p, 'WEBP', quality=WEBP_Q, method=6)
            rel[kind][f] = f'fields/{run_id}/{p.name}'

    mx = {'sim_surf': {}, 'sim_da': {}, 'theory': {}, 'diff_abs': {}, 'cum': {}}
    for f in FIELDS:
        mx['sim_surf'][f] = r1(np.nanmax(np.abs(levels[0][f])))
        mx['sim_da'][f] = r1(np.nanmax(np.abs(da[f])))
        mx['theory'][f] = r1(np.nanmax(np.abs(th[f])))
        mx['diff_abs'][f] = r1(np.nanmax(np.abs(diff[f])))
        mx['cum'][f] = [r1(np.nanmax(np.abs(levels[k][f]))) for k in range(K + 1)]
    entry = {
        'R': Rm, 'H': Hm, 'alpha_deg': alpha_deg, 'gamma': gamma,
        'domain_km': [r1(x.min() / 1e3, 3), r1(x.max() / 1e3, 3),
                      r1(y.min() / 1e3, 3), r1(y.max() / 1e3, 3)],
        'patch_km': Rm / 1e3,
        'scales': {'stress_kpa': r1(T.stress_scale_pa(Rm, alpha) / 1e3, 1),
                   'decay_km': r1(T.decay_length_m(Hm, gamma) / 1e3, 2)},
        'K': K,
        'depth_frac': [r1(v, 6) for v in zk],
        'cum': rel['cum'],
        'surf': {f: rel['cum'][f][0] for f in FIELDS},
        'da': {f: rel['cum'][f][-1] for f in FIELDS},
        'theory': rel['theory'],
        'diff': rel['diff'],
        'max_kpa': mx,
        'saturates': {f: bool(max(mx['sim_surf'][f], mx['sim_da'][f], mx['theory'][f], mx['diff_abs'][f]) > VLIM)
                      for f in FIELDS},
        'check_kpa': chk,
    }
    qc_sheet(run_id, entry, x, y, levels, th, diff, zk)
    if run_id == HERO:
        hero_extras(run_id, entry, levels, th, diff, zk, r)
    return entry


def qc_sheet(run_id, e, x, y, levels, th, diff, zk):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    K = e['K']
    mids = sorted({round(K * q) for q in (0.25, 0.5, 0.75)} - {0, K})
    cols = [(f'surf (k 0)', levels[0])] + [(f'cum k {k} · d/H {zk[k]:.2f}', levels[k]) for k in mids] \
        + [(f'da (k {K})', levels[K]), ('theory', th), ('da − theory', diff)]
    ext = e['domain_km']
    fig, ax = plt.subplots(3, len(cols), figsize=(3.1 * len(cols), 9.6))
    for i, f in enumerate(FIELDS):
        for j, (lab, src) in enumerate(cols):
            a = src[f]
            im = ax[i, j].imshow(a[::4, ::4], origin='lower', extent=ext, cmap='seismic',
                                 vmin=-VLIM, vmax=VLIM)
            ax[i, j].set_title(f'{f} {lab}\nmax {np.nanmax(np.abs(a)):.1f}', fontsize=9)
            ax[i, j].add_patch(plt.Circle((0, 0), e['patch_km'], fill=False, ls='--', lw=0.8, color='k'))
            ax[i, j].tick_params(labelsize=7)
    fig.colorbar(im, ax=ax, shrink=0.6, label='kPa (fixed ±300)')
    c = e['check_kpa']
    fig.suptitle(f"{run_id}  K={K}  scale {e['scales']['stress_kpa']} kPa · decay {e['scales']['decay_km']} km  |  "
                 f"cum_K − nc da max: txx {c['cumK_txx']} tyy {c['cumK_tyy']} txy {c['cumK_txy']} kPa", fontsize=11)
    (OUT / '_qc').mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / '_qc' / f'qc_{run_id}.png', dpi=80)
    plt.close(fig)


def hero_extras(run_id, e, levels, th, diff, zk, r):
    """A filmstrip + GIF of the hero's cum levels (the average forming),
    and the hero numbers."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 22)
    except OSError:
        font = ImageFont.load_default()
    frames = []
    n = levels[0]['trr'].shape[0]
    h = min(n // 2, int(round(4 * e['patch_km'] * 1e3 / GRIDRES_M)))  # the centre ±4 R
    cs = slice(n // 2 - h, n // 2 + h + 1)
    for k in range(e['K'] + 1):
        row = [to_rgb(levels[k][f][cs, cs], VLIM, 420) for f in FIELDS]
        im = Image.new('RGB', (420 * 3, 420 + 40), 'white')
        for j, t in enumerate(row):
            im.paste(t, (420 * j, 40))
        ImageDraw.Draw(im).text((10, 8), f'{run_id}  cum level k={k}/{e["K"]}  depth/H={zk[k]:.3f}   '
                                f'st1 | trr | txx   ±300 kPa  (centre ±4R)', fill='black', font=font)
        frames.append(im)
    frames[0].save(OUT / '_qc' / f'cum_{run_id}.gif', save_all=True, append_images=frames[1:] + frames[-1:] * 3,
                   duration=600, loop=0)
    strip = Image.new('RGB', (frames[0].width, frames[0].height * len(frames)), 'white')
    for k, fr in enumerate(frames):
        strip.paste(fr, (0, k * fr.height))
    strip.resize((strip.width // 2, strip.height // 2), Image.LANCZOS).save(OUT / '_qc' / f'cum_{run_id}_strip.png')
    d = np.abs(diff['trr'])
    nums = {
        'theory_trr_peak_kpa': r1(np.nanmax(np.abs(th['trr']))),
        'sim_da_trr_peak_kpa': r1(np.nanmax(np.abs(levels[-1]['trr']))),
        'sim_surf_trr_peak_kpa': r1(np.nanmax(np.abs(levels[0]['trr']))),
        'theory_st1_peak_kpa': r1(np.nanmax(np.abs(th['st1']))),
        'sim_da_st1_peak_kpa': r1(np.nanmax(np.abs(levels[-1]['st1']))),
        'diff_trr_max_kpa': r1(d.max()),
        'diff_trr_p99_kpa': r1(np.percentile(d, 99), 3),
        'cum_trr_peak_by_level_kpa': e['max_kpa']['cum']['trr'],
    }
    (OUT / '_qc' / 'hero_numbers.json').write_text(json.dumps(nums, indent=1))
    print('  HERO NUMBERS', json.dumps(nums))


def write_manifest():
    runs = {}
    for rid in run_ids():
        p = OUT / '_runs' / f'{rid}.json'
        if p.exists():
            e = json.loads(p.read_text())
            e.pop('check_kpa', None)
            runs[rid] = e
    man = {
        'version': 2, 'hero': HERO, 'params': PARAMS, 'fields': FIELDS, 'vlim_kpa': VLIM,
        'raster': {'colormap': 'matplotlib seismic, fixed ±300 kPa (beyond saturates)',
                   'orientation': 'row 0 = domain_km y1 (north up), column 0 = x0',
                   'paths': 'relative to ch02/slab_v2/', 'size_px': SIZE,
                   'cum': 'cum[f][k] = trapezoid mean of the field from the surface to depth_frac[k]·H '
                          '(k 0 = surface, k K = full depth average); st1 from the averaged τ',
                   'diff': 'sim_da (cum K) − theory'},
        'runs_missing': [r for r in run_ids() if r not in runs],
        'runs': runs,
    }
    (OUT / 'manifest.json').write_text(json.dumps(man, separators=(',', ':')))
    checks = {rid: json.loads((OUT / '_runs' / f'{rid}.json').read_text())['check_kpa'] for rid in runs}
    (OUT / '_qc' / 'checks.json').write_text(json.dumps(checks, indent=1))
    print(f'manifest: {len(runs)} runs, missing {len(man["runs_missing"])}')


def stage(run_id):
    p = VTU_DIR / vtu_name(run_id)
    for attempt in range(5):  # Drive hydration times out now and then (mmap: Operation timed out)
        if p.exists():
            break
        if attempt:
            print(f'  staging retry {attempt} for {run_id}')
            subprocess.run(['bash', str(FETCH), 'slab_vtu_warm', run_id])
        subprocess.run(['bash', str(FETCH), 'slab_vtu', run_id], stdout=subprocess.DEVNULL)
    return require_source(p)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    force, keep = '--force' in sys.argv, '--keep' in sys.argv
    require_source(NC_DIR)
    (OUT / '_runs').mkdir(parents=True, exist_ok=True)
    todo = [r for r in run_ids() if (not args or r in args)
            and (force or not (OUT / '_runs' / f'{r}.json').exists())]
    warm = None
    for i, rid in enumerate(todo):
        print(f'[{i + 1}/{len(todo)}] {rid}')
        vtu = stage(rid)
        if warm is not None:
            warm.wait()
        # hydrate the NEXT run in Drive's cache (read-only, no copy) while baking this one
        warm = (subprocess.Popen(['bash', str(FETCH), 'slab_vtu_warm', todo[i + 1]])
                if i + 1 < len(todo) else None)
        try:
            e = bake_run(rid, vtu)
            (OUT / '_runs' / f'{rid}.json').write_text(json.dumps(e))
            c = e['check_kpa']
            worst = max(c[f'cumK_{k}'] for k in ('txx', 'tyy', 'txy'))
            print(f"  max|trr| surf {e['max_kpa']['sim_surf']['trr']} da {e['max_kpa']['sim_da']['trr']} "
                  f"th {e['max_kpa']['theory']['trr']} diff {e['max_kpa']['diff_abs']['trr']} | "
                  f"saturates {[f for f, s in e['saturates'].items() if s]} | worst cum_K−da {worst}")
        except Exception as ex:
            print(f'FAILED {rid}: {ex!r}')
        finally:
            if not keep:
                vtu.unlink()  # the staged copy this run made (never the Drive)
    if warm is not None:
        warm.wait()
    write_manifest()


if __name__ == '__main__':
    main()
