"""Diagnostics: does the published bed smooth the signal that MGSIM preserves?

Figure 1 (track residuals) — |map - radar| at the radar cells, mapped for the
published bed and an MGSIM realization, with CDFs, plus a real along-track
profile from the raw CReSIS picks.

Figure 2 (statistics) — the three tests that separate "smoothed" from
"data-consistent": short-lag variogram at the radar cells, radially averaged
power spectrum of the maps, and the distribution of 150 m bed slopes measured
between adjacent radar cells.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

HERE = Path(__file__).resolve().parent.parent
DERIVED, FIGS = HERE / 'data/derived', HERE / 'figures'
N_GRID, PX_M, HALF = 166, 150.0, 12375.0

R = np.load(DERIVED / 'bed_realizations_cw1951.npz')
beds, trend, obs = R['beds'], R['trend'], R['obs_mask']
shift = json.loads(str(R['meta']))['datum_shift_m']
grf = np.load(DERIVED / 'bed_realizations_cw1951_condgrf.npz')['beds']
gz = np.load(DERIVED / 'gridded_bed_cw1951_150m.npz')
I0, I1 = json.loads(str(gz['meta']))['dem_sub_lattice']
data_map = gz['bed_hm'][I0:I1 + 1, I0:I1 + 1] - shift
iy, ix = np.where(obs)
data = data_map[obs]
real, grf0 = beds[0], grf[0]
MAPS = [('published bed', trend, 'k'), ('MGSIM realization 0', real, 'tab:orange'),
        ('conditional GRF 0', grf0, 'tab:blue')]
ext = [0, (N_GRID - 1) * PX_M / 1e3] * 2

# ---------------------------------------------------------------- figure 1
fig = plt.figure(figsize=(19, 9.5), constrained_layout=True)
gs = GridSpec(2, 3, figure=fig, height_ratios=[1.15, 1])
dpub, dmg = np.abs(trend[obs] - data), np.abs(real[obs] - data)
vmax = float(np.percentile(np.concatenate([dpub, dmg]), 98))
for j, (name, d) in enumerate([('published bed', dpub), ('MGSIM realization 0', dmg)]):
    ax = fig.add_subplot(gs[0, j])
    ax.imshow(trend, origin='lower', extent=ext, cmap='Greys', alpha=.35,
              vmin=np.percentile(trend, 2), vmax=np.percentile(trend, 98))
    sc = ax.scatter(ix * PX_M / 1e3, iy * PX_M / 1e3, c=d, s=2.5, cmap='inferno',
                    vmin=0, vmax=vmax)
    ax.set_title(f'|{name} − radar| along tracks\nmedian {np.median(d):.1f} m · '
                 f'p95 {np.percentile(d, 95):.1f} m', fontsize=11)
    ax.set_xlabel('DEM x [km]')
    if j == 0:
        ax.set_ylabel('DEM y [km]')
    fig.colorbar(sc, ax=ax, shrink=.85, label='|difference| [m]')

ax = fig.add_subplot(gs[0, 2])
for name, m, c in MAPS:
    e = np.abs(m[obs] - data)
    ax.plot(np.sort(e), np.linspace(0, 100, len(e)), color=c, lw=2,
            label=f'{name}\n   median {np.median(e):.1f} m, p95 {np.percentile(e, 95):.1f} m')
ax.axvline(10, color='0.6', ls=':', lw=1)
ax.text(10.5, 8, 'within-cell\npick scatter', fontsize=8, color='0.4')
ax.set_xscale('log'); ax.set_xlim(0.3, 400)
ax.set_xlabel('|map − radar| at radar cells [m]'); ax.set_ylabel('percentile')
ax.set_title('how closely each map reproduces the picks', fontsize=11)
ax.legend(fontsize=8, loc='lower right'); ax.grid(alpha=.3)

# --- a real along-track profile from the raw picks
cols = ['SEASON', 'FRAME', 'LX', 'LY', 'BED_ELEV', 'IN_SIMDOMAIN', 'DATUM_SUSPECT']
pk = pd.read_csv(DERIVED / 'radar_picks_cw1951_aoi50km.csv', usecols=cols)
pk = pk[(pk.IN_SIMDOMAIN == 1) & (~pk.DATUM_SUSPECT.astype(bool))]
best = (pk.groupby(['SEASON', 'FRAME']).size().sort_values(ascending=False).index[0])
seg = pk[(pk.SEASON == best[0]) & (pk.FRAME == best[1])].copy()
seg['px'] = (seg.LX + HALF) / PX_M
seg['py'] = (seg.LY + HALF) / PX_M
seg = seg[(seg.px.between(0, N_GRID - 1.001)) & (seg.py.between(0, N_GRID - 1.001))]
seg = seg.sort_values('LX')
s_km = np.r_[0, np.cumsum(np.hypot(np.diff(seg.LX.values), np.diff(seg.LY.values)))] / 1e3

def bilinear(M, px, py):
    x0, y0 = np.floor(px).astype(int), np.floor(py).astype(int)
    fx, fy = px - x0, py - y0
    return ((M[y0, x0] * (1 - fx) + M[y0, x0 + 1] * fx) * (1 - fy) +
            (M[y0 + 1, x0] * (1 - fx) + M[y0 + 1, x0 + 1] * fx) * fy)

ax = fig.add_subplot(gs[1, :])
ax.plot(s_km, seg.BED_ELEV.values - shift, '.', ms=1.6, color='0.25',
        label=f'raw CReSIS picks ({best[0]} frame {best[1]}, ~15 m posting)')
for name, m, c in MAPS:
    ax.plot(s_km, bilinear(m, seg.px.values, seg.py.values), color=c, lw=1.6, label=name)
ax.set_xlabel('distance along flight track [km]'); ax.set_ylabel('bed elevation [m]')
ax.set_title('along-track profile: the published bed rides through the topography the picks resolve', fontsize=11)
ax.legend(fontsize=9, ncol=4); ax.grid(alpha=.3)
fig.savefig(FIGS / 'smoothing_track_residuals.png', dpi=130, bbox_inches='tight')
print('saved smoothing_track_residuals.png ·', len(seg), 'picks on the profile segment')

# ---------------------------------------------------------------- figure 2
import skgstat as skg
fig2, axs = plt.subplots(1, 3, figsize=(19, 5.2), constrained_layout=True)
rng = np.random.default_rng(0)
sub = rng.choice(len(data), min(4000, len(data)), replace=False)
P = np.column_stack([ix, iy]).astype(float)[sub]
series = [('raw radar picks', data[sub], 'tab:green')] + \
         [(n, m[obs][sub], c) for n, m, c in MAPS]
for name, v, c in series:
    V = skg.Variogram(P, v, model='spherical', maxlag=40, n_lags=30, normalize=False)
    axs[0].plot(np.array(V.bins) * PX_M / 1e3, V.experimental, '-o', ms=3.5, color=c, label=name)
axs[0].set_xlabel('lag [km]'); axs[0].set_ylabel('γ(h)  [m²]')
axs[0].set_title('variogram at the radar cells\n(short lags = the detail a map resolves)', fontsize=11)
axs[0].legend(fontsize=9); axs[0].grid(alpha=.3)

def radial_psd(M):
    W = np.hanning(M.shape[0])[:, None] * np.hanning(M.shape[1])[None, :]
    F = np.abs(np.fft.fftshift(np.fft.fft2((M - M.mean()) * W))) ** 2
    cy, cx = np.array(F.shape) // 2
    yy, xx = np.mgrid[:F.shape[0], :F.shape[1]]
    r = np.hypot(yy - cy, xx - cx).astype(int)
    prof = np.bincount(r.ravel(), F.ravel()) / np.maximum(np.bincount(r.ravel()), 1)
    k = np.arange(len(prof)) / (M.shape[0] * PX_M / 1e3)     # cycles per km
    return k[1:cy], prof[1:cy]

for name, m, c in MAPS:
    k, p = radial_psd(m)
    axs[1].loglog(k, p, color=c, lw=2, label=name)
axs[1].axvline(1 / (2 * PX_M / 1e3), color='0.6', ls=':', lw=1)
axs[1].text(1 / (2 * PX_M / 1e3) * 0.62, axs[1].get_ylim()[0] * 40, 'grid Nyquist\n(300 m)', fontsize=8, color='0.4')
axs[1].set_xlabel('wavenumber [cycles km⁻¹]'); axs[1].set_ylabel('power')
axs[1].set_title('radially averaged power spectrum\n(where the published bed loses variance)', fontsize=11)
axs[1].legend(fontsize=9); axs[1].grid(alpha=.3, which='both')

# 150 m slopes measured between adjacent radar cells — apples to apples
pairs = []
oi = {(a, b) for a, b in zip(iy, ix)}
for a, b in zip(iy, ix):
    if (a, b + 1) in oi: pairs.append((a, b, a, b + 1))
    if (a + 1, b) in oi: pairs.append((a, b, a + 1, b))
pr = np.array(pairs)
def slopes(M):
    return np.abs(M[pr[:, 0], pr[:, 1]] - M[pr[:, 2], pr[:, 3]]) / PX_M * 100
bins = np.linspace(0, 40, 60)
for name, v, c in [('raw radar picks', slopes(data_map), 'tab:green')] + \
                  [(n, slopes(m), c) for n, m, c in MAPS]:
    axs[2].hist(v, bins=bins, histtype='step', lw=2, color=c, density=True,
                label=f'{name} (median {np.median(v):.1f}%)')
axs[2].set_xlabel('bed slope between adjacent radar cells [%, over 150 m]')
axs[2].set_ylabel('density')
axs[2].set_title(f'slope magnitude at {len(pr)} adjacent radar-cell pairs\n(the roughness ice actually feels)', fontsize=11)
axs[2].legend(fontsize=9); axs[2].grid(alpha=.3)
fig2.savefig(FIGS / 'smoothing_statistics.png', dpi=130, bbox_inches='tight')
print('saved smoothing_statistics.png')

print('\nsummary at the radar cells:')
print(f"{'map':22s}{'std [m]':>9}{'|err| med':>11}{'slope med %':>13}")
print(f"{'raw radar':22s}{data.std():9.1f}{0.0:11.1f}{np.median(slopes(data_map)):13.1f}")
for name, m, _ in MAPS:
    print(f'{name:22s}{m[obs].std():9.1f}{np.median(np.abs(m[obs] - data)):11.1f}'
          f'{np.median(slopes(m)):13.1f}')
