"""Figure: Tran-style multiple-grid vs the package's residual cascade."""
import json
import os
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent.parent
DERIVED, FIGS = HERE / 'data/derived', HERE / 'figures'
SW = Path(os.environ.get('SWEEP_DIR', '/path/to/a/scratch/dir/sweep'))  # scratch space the sweep scripts share
N_GRID = 166

trend = np.loadtxt(HERE / 'data/source_copies/2019cw428_bed_d25km_h1004_a0.792.dat')[:, 2].reshape(N_GRID, N_GRID)
R = np.load(DERIVED / 'bed_realizations_cw1951.npz')
tr = np.load(SW / 'tran_fields.npz')
cmp = pd.read_csv(SW / 'tran_comparison.csv').set_index('method')

panels = [
    ('published bed', trend, 'published'),
    ('shipped nb-03\npackage cascade [3,1]', R['beds'][0], 'shipped nb-03 (package [3,1])'),
    ('single pass [1]\n(no multigrid)', np.load(SW / 's3_Mate1.5_n0_full_k24_mg1_r2_c100.npz')['field'],
     'single pass [1] (sweep winner)'),
    ('package cascade\n[12,6,3,1]', np.load(SW / 's4_Mate1.5_n0_full_k24_mg12-6-3-1_r2_c100.npz')['field'],
     'package MG [12,6,3,1]'),
    ('Tran multiple-grid\n[8,4,2,1]', tr['Tran MG 8-4-2-1'], 'Tran MG 8-4-2-1'),
]
vmin, vmax = np.percentile(trend, [2, 98])
n = len(panels)
fig, axs = plt.subplots(2, n, figsize=(4.1 * n, 8.9), constrained_layout=True)
for j, (name, M, key) in enumerate(panels):
    sub = ''
    if key in cmp.index:
        r = cmp.loc[key]
        sub = (f"err {r.obs_med:.2f} m · rough {r.rough:.1f} m\n"
               f"dep-std {r.dep_std:.0f} m · vario {r.vario_ratio:.2f}")
    axs[0, j].imshow(M, origin='lower', cmap='terrain', vmin=vmin, vmax=vmax)
    axs[0, j].set_title(f'{name}\n{sub}', fontsize=9)
    axs[1, j].imshow(M[55:105, 55:105], origin='lower', cmap='terrain', vmin=vmin, vmax=vmax)
    axs[1, j].set_title('7.5 km zoom', fontsize=8)
    for a in (axs[0, j], axs[1, j]):
        a.set_xticks([]); a.set_yticks([])
fig.suptitle('two things called "multigrid": the package sums a full simulation per level (cascade); '
             'Tran (1994) coarsens the simulation PATH', fontsize=12)
fig.savefig(FIGS / 'tran_vs_cascade.png', dpi=120, bbox_inches='tight')

order = ['single pass [1] (sweep winner)', 'package MG [3,1]', 'package MG [12,6,3,1]',
         'Tran MG 8-4-2-1', 'Tran MG 16-8-4-2-1']
lab = ['single pass\n[1]', 'package\n[3,1]', 'package\n[12,6,3,1]', 'Tran\n[8,4,2,1]', 'Tran\n[16,8,4,2,1]']
d = cmp.loc[order]
fig2, axs2 = plt.subplots(1, 3, figsize=(15, 4.4), constrained_layout=True)
cols = ['tab:red'] * 3 + ['tab:green'] * 2
for ax, (c, t, ref, rl) in zip(axs2, [
        ('rough', '2nd-difference roughness [m]', 17.5, 'floor from data noise (√6·7.1)'),
        ('dep_std', 'departure-from-published std [m]', 56.8, "data's own residual std"),
        ('vario_ratio', 'variogram reproduction (→1 is faithful)', 1.0, 'model sill')]):
    ax.bar(lab, d[c], color=cols)
    ax.axhline(ref, ls='--', color='k', lw=1, label=rl)
    ax.set_title(t, fontsize=10); ax.legend(fontsize=8); ax.grid(alpha=.3, axis='y')
    ax.tick_params(labelsize=8)
fig2.suptitle('all five honor the radar exactly; only the multigrid style differs', fontsize=11)
fig2.savefig(FIGS / 'tran_metrics.png', dpi=130, bbox_inches='tight')
print('saved tran_vs_cascade.png + tran_metrics.png')
