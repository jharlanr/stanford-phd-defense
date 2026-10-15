"""Published bed + four MGSIM (nb 03) realizations, with value histograms.

Top row: maps on a common color scale. Bottom row, per column: the full-map
value distribution (filled), the map sampled at the radar cells (blue), and
the raw datum-aligned radar bed at those same cells (black) — so blue vs
black measures smoothing at identical support.
"""
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent.parent
DERIVED, FIGS = HERE / 'data/derived', HERE / 'figures'
PX_M = 150.0

R = np.load(DERIVED / 'bed_realizations_cw1951.npz')
beds, trend, obs = R['beds'], R['trend'], R['obs_mask']
meta = json.loads(str(R['meta']))
gz = np.load(DERIVED / 'gridded_bed_cw1951_150m.npz')
I0, I1 = json.loads(str(gz['meta']))['dem_sub_lattice']
data = (gz['bed_hm'][I0:I1 + 1, I0:I1 + 1] - meta['datum_shift_m'])[obs]

panels = [('published bed (trend)', trend)] + [(f'MGSIM realization {i}', beds[i]) for i in range(4)]
allv = np.concatenate([p[1].ravel() for p in panels] + [data])
lo, hi = np.percentile(allv, [0.5, 99.5])
bins = np.linspace(lo, hi, 70)
n = trend.shape[0]
ext = [0, (n - 1) * PX_M / 1e3] * 2

fig, axs = plt.subplots(2, 5, figsize=(23, 8.8), constrained_layout=True,
                        gridspec_kw={'height_ratios': [1.25, 1]})
for j, (title, b) in enumerate(panels):
    ax = axs[0, j]
    im = ax.imshow(b, origin='lower', extent=ext, cmap='terrain', vmin=lo, vmax=hi)
    ax.set_title(title, fontsize=11)
    ax.set_xticks([]); ax.set_yticks([])
    at_data = b[obs]
    h = axs[1, j]
    h.hist(b.ravel(), bins=bins, density=True, color='0.75', label=f'whole map (std {b.std():.0f} m)')
    h.hist(at_data, bins=bins, density=True, histtype='step', lw=1.8, color='tab:blue',
           label=f'map at radar cells (std {at_data.std():.0f} m)')
    h.hist(data, bins=bins, density=True, histtype='step', lw=1.8, color='k',
           label=f'raw radar bed (std {data.std():.0f} m)')
    h.set_xlabel('bed elevation [m]')
    h.legend(fontsize=8, loc='upper right', frameon=False)
    h.grid(alpha=0.25)
    if j == 0:
        h.set_ylabel('density')
    h.set_title(f'|map − radar| at radar cells: median {np.median(np.abs(at_data - data)):.1f} m', fontsize=9)
fig.colorbar(im, ax=axs[0, :], shrink=0.85, pad=0.01, label='bed elevation [m]')
axs[0, 0].set_xlabel('24.75 km Elmer domain'); 
fig.suptitle(f'published bed vs MGSIM realizations (nb 03) — value distributions over the whole map and at the '
             f'{int(obs.sum())} radar cells', fontsize=12)
fig.savefig(FIGS / 'mgsim_reals_vs_data.png', dpi=130, bbox_inches='tight')
print('saved', FIGS / 'mgsim_reals_vs_data.png')
print(f"std — radar {data.std():.1f} m; published at radar cells {trend[obs].std():.1f} m; "
      f"published whole map {trend.std():.1f} m; realizations whole map "
      f"{np.mean([b.std() for b in beds[:4]]):.1f} m")
