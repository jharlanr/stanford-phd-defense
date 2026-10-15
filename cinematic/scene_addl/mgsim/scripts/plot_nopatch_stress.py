"""Goofy-check plots for the MGSIM bed ensemble's NOPATCH Elmer runs.

The published PNAS analysis tile (591x591 @ 25 m, +/-7375 m, stresses in
MPa) is reproduced for each realization by extract_surface_vtu.py, so the
runs can be put side by side with the published nopatch case on the same
lattice with the same recipe.

sigma_t1 here is the published SI recipe (build_sim_domains.py
tangent_sigma_t1_diff) applied to the ABSOLUTE nopatch tensor instead of
the patch-minus-nopatch difference: project the surface Cauchy tensor into
the tangent plane of the surface, take the most-tensile in-plane
principal, tension positive, kPa.

  ./cinematic/.venv/bin/python cinematic/scene_addl/mgsim/scripts/plot_nopatch_stress.py
"""
import glob
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.gridspec import GridSpec

ROOT = Path(__file__).resolve().parents[4]
RESULTS = ROOT / 'cinematic' / 'scene_addl' / 'mgsim' / 'elmer_bundle' / 'results'
FIGS = ROOT / 'cinematic' / 'scene_addl' / 'mgsim' / 'figures'
PUB_NC = (ROOT / 'cinematic' / 'source_data' / 'pnas_sims' /
          '2019cw428_d25km_r2500m_csi6.5e6_tsic_viscous.nc')

MPA_TO_KPA = 1e3
SIGMA_KEYS = ('sigma_xx', 'sigma_yy', 'sigma_zz',
              'sigma_xy', 'sigma_yz', 'sigma_xz')


def tangent_sigma_t1(sig, topo, x, y):
    """Published SI recipe, absolute (not differenced): project the
    surface Cauchy tensor into the surface tangent plane and return the
    most-tensile in-plane principal, tension positive, in kPa."""
    hy, hx = np.gradient(topo, y, x)          # row = y, col = x
    n = np.stack([-hx, -hy, np.ones_like(hx)], axis=0)
    n /= np.linalg.norm(n, axis=0, keepdims=True)
    xhat = np.zeros_like(n)
    xhat[0] = 1.0
    e1 = xhat - (xhat * n).sum(axis=0, keepdims=True) * n
    e1 /= np.linalg.norm(e1, axis=0, keepdims=True)
    e2 = np.cross(n, e1, axis=0)

    def T_dot(v):
        return np.stack([
            sig['sigma_xx'] * v[0] + sig['sigma_xy'] * v[1] + sig['sigma_xz'] * v[2],
            sig['sigma_xy'] * v[0] + sig['sigma_yy'] * v[1] + sig['sigma_yz'] * v[2],
            sig['sigma_xz'] * v[0] + sig['sigma_yz'] * v[1] + sig['sigma_zz'] * v[2],
        ], axis=0)

    t11 = (e1 * T_dot(e1)).sum(axis=0)
    t22 = (e2 * T_dot(e2)).sum(axis=0)
    t12 = (e1 * T_dot(e2)).sum(axis=0)
    mean = 0.5 * (t11 + t22)
    rad = np.sqrt((0.5 * (t11 - t22)) ** 2 + t12 ** 2)
    return (mean + rad) * MPA_TO_KPA


def nice_lim(vals, pct=99.5):
    v = np.nanpercentile(np.abs(np.concatenate([a.ravel() for a in vals])), pct)
    step = 10 ** np.floor(np.log10(v))
    return float(np.ceil(v / (step / 2)) * (step / 2))


def load():
    ds = xr.open_dataset(PUB_NC)
    x, y = ds.x.values.astype(float), ds.y.values.astype(float)
    pub_sig = {k: ds[k].sel(level='surf', case='nopatch').values.astype(float)
               for k in SIGMA_KEYS}
    pub = {
        'label': 'published bed',
        'bed': ds['topo_bed'].sel(level='surf', case='nopatch').values,
        'surf': ds['topo_surf'].sel(level='surf', case='nopatch').values,
        'speed': ds['speed_h'].sel(level='surf', case='nopatch').values,
    }
    pub['s1'] = tangent_sigma_t1(pub_sig, pub['surf'].astype(float), x, y)

    reals = []
    for f in sorted(glob.glob(str(RESULTS / '*_nopatch_mgsim*.npz'))):
        z = np.load(f)
        sig = {k: z[k].astype(float) for k in SIGMA_KEYS}
        num = re.search(r'mgsim(\d+)', f).group(1)
        reals.append({
            'label': 'MGSIM ' + num,
            'bed': z['topo_bed'], 'surf': z['topo_surf'], 'speed': z['speed_h'],
            's1': tangent_sigma_t1(sig, z['topo_surf'].astype(float), x, y),
        })
    return x, y, pub, reals


def imshow(ax, a, x, y, **kw):
    ext = [x[0] / 1e3, x[-1] / 1e3, y[0] / 1e3, y[-1] / 1e3]
    return ax.imshow(a, origin='lower', extent=ext, **kw)


def figure_grid(x, y, pub, reals):
    """Row 1 bed · row 2 nopatch sigma_t1 · row 3 sigma_t1 minus published."""
    cols = [pub] + reals
    n = len(cols)
    bmin = min(np.nanmin(c['bed']) for c in cols)
    bmax = max(np.nanmax(c['bed']) for c in cols)
    slim = nice_lim([c['s1'] for c in cols])
    diffs = [r['s1'] - pub['s1'] for r in reals]
    dlim = nice_lim(diffs)

    fig = plt.figure(figsize=(3.05 * n, 9.9))
    gs = GridSpec(3, n + 1, figure=fig, width_ratios=[1] * n + [0.055],
                  wspace=0.09, hspace=0.16, left=0.045, right=0.94,
                  top=0.925, bottom=0.045)

    for j, c in enumerate(cols):
        ax = fig.add_subplot(gs[0, j])
        im0 = imshow(ax, c['bed'], x, y, cmap='terrain', vmin=bmin, vmax=bmax)
        ax.set_title(c['label'], fontsize=11, pad=6)
        style(ax, j, 'bed elevation')

        ax = fig.add_subplot(gs[1, j])
        im1 = imshow(ax, c['s1'], x, y, cmap='seismic', vmin=-slim, vmax=slim)
        style(ax, j, r'nopatch  $\sigma_{t1}$')

        ax = fig.add_subplot(gs[2, j])
        if j == 0:
            ax.text(0.5, 0.5, 'reference\n(published run)', ha='center',
                    va='center', fontsize=10, color='0.45',
                    transform=ax.transAxes)
            ax.set_xticks([]); ax.set_yticks([])
            for s in ax.spines.values():
                s.set_color('0.85')
        else:
            im2 = imshow(ax, diffs[j - 1], x, y, cmap='seismic',
                         vmin=-dlim, vmax=dlim)
            style(ax, j, r'$\sigma_{t1}$ $-$ published')

    for row, im, lab in ((0, im0, 'bed elevation (m)'),
                         (1, im1, r'$\sigma_{t1}$ (kPa, tension +)'),
                         (2, im2, r'$\Delta\sigma_{t1}$ vs published (kPa)')):
        cax = fig.add_subplot(gs[row, n])
        fig.colorbar(im, cax=cax).set_label(lab, fontsize=9)
        cax.tick_params(labelsize=8)

    fig.suptitle('Lake 1951 / 2019cw428 — MGSIM bed ensemble, NOPATCH viscous runs\n'
                 'published 14.75 km analysis tile, published tangent-'
                 r'$\sigma_{t1}$ recipe', fontsize=13)
    out = FIGS / 'elmer_nopatch_sigma_t1.png'
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print('wrote', out)


def style(ax, j, ylab):
    ax.set_aspect('equal')
    ax.tick_params(labelsize=8)
    if j == 0:
        ax.set_ylabel(f'{ylab}\ny (km)', fontsize=9)
    else:
        ax.set_yticklabels([])
    ax.set_xlabel('x (km)', fontsize=9)


def figure_ensemble(x, y, pub, reals):
    """Ensemble mean / spread against the published nopatch field."""
    stack = np.stack([r['s1'] for r in reals])
    mean, std = stack.mean(0), stack.std(0, ddof=1)
    bias = mean - pub['s1']
    slim = nice_lim([pub['s1'], mean])
    dlim = nice_lim([bias])

    fig = plt.figure(figsize=(16.6, 7.8))
    gs = GridSpec(2, 4, figure=fig, hspace=0.34, wspace=0.42,
                  left=0.045, right=0.995, top=0.9, bottom=0.09)

    panels = [
        (gs[0, 0], pub['s1'], 'seismic', -slim, slim,
         f'published nopatch $\\sigma_{{t1}}$', 'kPa'),
        (gs[0, 1], mean, 'seismic', -slim, slim,
         f'MGSIM ensemble mean (n={len(reals)})', 'kPa'),
        (gs[0, 2], std, 'magma', 0, np.nanpercentile(std, 99.5),
         'MGSIM ensemble std', 'kPa'),
        (gs[0, 3], bias, 'seismic', -dlim, dlim,
         'ensemble mean $-$ published', 'kPa'),
    ]
    for k, (spec, a, cmap, lo, hi, title, unit) in enumerate(panels):
        ax = fig.add_subplot(spec)
        im = imshow(ax, a, x, y, cmap=cmap, vmin=lo, vmax=hi)
        ax.set_aspect('equal'); ax.set_title(title, fontsize=11)
        ax.set_xlabel('x (km)', fontsize=9)
        if k == 0:
            ax.set_ylabel('y (km)', fontsize=9)
        ax.tick_params(labelsize=8)
        cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cb.set_label(unit, fontsize=9, labelpad=2)
        cb.ax.tick_params(labelsize=8)

    ax = fig.add_subplot(gs[1, 0])
    bins = np.linspace(-nice_lim([pub['s1']]), nice_lim([pub['s1']]), 90)
    ax.hist(pub['s1'].ravel(), bins=bins, histtype='step', lw=2.2,
            color='k', label='published', density=True)
    for r in reals:
        ax.hist(r['s1'].ravel(), bins=bins, histtype='step', lw=1.1,
                alpha=0.85, label=r['label'], density=True)
    ax.set_xlabel(r'$\sigma_{t1}$ (kPa)', fontsize=9)
    ax.set_ylabel('density', fontsize=9)
    ax.set_title(r'$\sigma_{t1}$ distribution', fontsize=11)
    ax.legend(fontsize=7.5, frameon=False)
    ax.tick_params(labelsize=8)

    ax = fig.add_subplot(gs[1, 1])
    bedbins = 70
    ax.hist(pub['bed'].ravel(), bins=bedbins, histtype='step', lw=2.2,
            color='k', label='published', density=True)
    for r in reals:
        ax.hist(r['bed'].ravel(), bins=bedbins, histtype='step', lw=1.1,
                alpha=0.85, label=r['label'], density=True)
    ax.set_xlabel('bed elevation (m)', fontsize=9)
    ax.set_ylabel('density', fontsize=9)
    ax.set_title('bed distribution', fontsize=11)
    ax.tick_params(labelsize=8)

    ax = fig.add_subplot(gs[1, 2])
    sub = (slice(None, None, 7), slice(None, None, 7))
    for r in reals:
        ax.scatter(pub['s1'][sub].ravel(), r['s1'][sub].ravel(), s=1.5,
                   alpha=0.15, label=r['label'])
    lo, hi = -slim, slim
    ax.plot([lo, hi], [lo, hi], 'k--', lw=1)
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect('equal')
    ax.set_xlabel(r'published $\sigma_{t1}$ (kPa)', fontsize=9)
    ax.set_ylabel(r'MGSIM $\sigma_{t1}$ (kPa)', fontsize=9)
    ax.set_title('per-pixel agreement', fontsize=11)
    ax.tick_params(labelsize=8)

    ax = fig.add_subplot(gs[1, 3])
    ax.axis('off')
    corr = [np.corrcoef(pub['s1'].ravel(), r['s1'].ravel())[0, 1] for r in reals]
    rms = np.sqrt(np.nanmean((mean - pub['s1']) ** 2))

    def statrow(name, a, c=None):
        return (f'{name:<11s}{np.nanmean(a):>7.1f}{np.nanstd(a):>8.1f}'
                + (f'{c:>7.2f}' if c is not None else f'{"-":>7s}'))
    rows = [f"{'':<11s}{'mean':>7s}{'std':>8s}{'corr':>7s}",
            statrow('published', pub['s1'])]
    rows += [statrow(r['label'], r['s1'], c) for r, c in zip(reals, corr)]
    rows += ['',
             f'ens. spread   {np.nanmean(std):>6.1f} kPa (mean std)',
             f'mean bias     {np.nanmean(bias):>+6.1f} kPa',
             f'RMS vs pub    {rms:>6.1f} kPa',
             f'corr vs pub   {np.mean(corr):>6.2f} (mean)']
    ax.text(0.0, 0.98, '\n'.join(rows), family='monospace', fontsize=8.8,
            va='top', transform=ax.transAxes)
    ax.set_title(r'$\sigma_{t1}$ statistics (kPa)', fontsize=11)

    fig.suptitle('MGSIM nopatch ensemble vs published nopatch run — '
                 'lake 1951 / 2019cw428', fontsize=13)
    out = FIGS / 'elmer_nopatch_ensemble.png'
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print('wrote', out)
    print(f'\nensemble mean spread {np.nanmean(std):.1f} kPa · '
          f'mean bias {np.nanmean(bias):+.1f} kPa · '
          f'RMS(mean - published) {np.sqrt(np.nanmean((mean - pub["s1"])**2)):.1f} kPa')


if __name__ == '__main__':
    FIGS.mkdir(parents=True, exist_ok=True)
    x, y, pub, reals = load()
    print(f'{len(reals)} realizations: ' + ', '.join(r['label'] for r in reals))
    figure_grid(x, y, pub, reals)
    figure_ensemble(x, y, pub, reals)
