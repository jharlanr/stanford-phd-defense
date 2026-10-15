"""Final report for the variogram sweep: Pareto frontier + contender maps."""
import glob, json, os
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent.parent
DERIVED, FIGS = HERE / 'data/derived', HERE / 'figures'
SW = Path(os.environ.get('SWEEP_DIR', '/path/to/a/scratch/dir/sweep'))  # scratch space the sweep scripts share
N_GRID, PX_M = 166, 150.0

rows = [json.loads(str(np.load(f, allow_pickle=True)['metrics'])) for f in sorted(glob.glob(str(SW / '*.npz')))]
sgs = pd.DataFrame([r for r in rows if 'failed' not in r])
sgs['gen'] = 'SGS (package)'
grf = pd.read_csv(SW / 'grf_sweep.csv'); grf['gen'] = 'conditional GRF'
grf['sched'] = '-'; grf['k'] = '-'

trend = np.loadtxt(HERE / 'data/source_copies/2019cw428_bed_d25km_h1004_a0.792.dat')[:, 2].reshape(N_GRID, N_GRID)
R = np.load(DERIVED / 'bed_realizations_cw1951.npz')
obs, shipped = R['obs_mask'], R['beds'][0]
gz = np.load(DERIVED / 'gridded_bed_cw1951_150m.npz')
I0, I1 = json.loads(str(gz['meta']))['dem_sub_lattice']
data_map = gz['bed_hm'][I0:I1 + 1, I0:I1 + 1] - json.loads(str(R['meta']))['datum_shift_m']
iy, ix = np.where(obs)
core = slice(20, -20)
NOISE = 7.1   # median within-cell pick scatter (n>1 cells)

def rough(b):
    return float(np.sqrt(np.mean(np.diff(b, n=2, axis=1)[core, core] ** 2)))

both = pd.concat([sgs, grf], ignore_index=True)
both = both[both.get('finite', True) != False]
print('=== Pareto frontier: lowest roughness at each conditioning-error level ===')
for lo, hi, lab in [(0, .001, 'exact'), (.001, 1, '<= 1 m'), (1, 3, '1-3 m'),
                    (3, 8, '3-8 m'), (8, 12, '8-12 m (= data noise)')]:
    sel = both[(both.obs_med >= lo) & (both.obs_med < hi)].sort_values('rough')
    if len(sel):
        b = sel.iloc[0]
        s = f"s={b['s']}" if b.get('s') == b.get('s') and b.get('s') else ''
        print(f"  {lab:22s} rough {b['rough']:6.1f} m | {b['gen']:16s} {b['model']:11s} {s:7s}"
              f" nug {b['nug_frac']:g} k={b['k']} mg={b.get('sched','-')} r×{b.get('range_mult',1)} "
              f"| err {b['obs_med']:.3f} m, dep-std {b['dep_std']:.0f} m")
print(f"\n  shipped nb-03           rough {rough(shipped):6.1f} m | SGS Gaussian nug 0.01 k=12 mg=[3,1] "
      f"| err {np.median(np.abs(shipped[obs] - data_map[obs])):.2f} m")
print(f"  published bed           rough {rough(trend):6.1f} m | (no conditioning) "
      f"| err {np.median(np.abs(trend[obs] - data_map[obs])):.2f} m")

# ---- Pareto scatter
fig, ax = plt.subplots(figsize=(9.5, 6.4))
for gen, mk in [('SGS (package)', 'o'), ('conditional GRF', '^')]:
    d = both[both.gen == gen]
    sc = ax.scatter(np.maximum(d.obs_med, 3e-3), d.rough, c=np.log10(d.nug_frac.clip(1e-6)),
                    marker=mk, s=46, cmap='viridis', edgecolor='0.3', lw=.4, label=gen)
ax.scatter([np.median(np.abs(shipped[obs] - data_map[obs]))], [rough(shipped)], marker='*',
           s=420, color='tab:red', edgecolor='k', zorder=5, label='shipped nb-03')
ax.axhline(rough(trend), color='k', ls='--', lw=1, label=f'published bed roughness ({rough(trend):.1f} m)')
ax.axvspan(3e-3, NOISE, color='0.88', zorder=0)
n_off = int((both.rough > 70).sum())
ax.set_ylim(0, 70)
ax.text(4e-3, 66.5, f'shaded: conditioning tighter than the data\'s own within-cell\n'
        f'scatter (7.1 m) — i.e. fitting measurement noise\n'
        f'({n_off} zero-nugget Gaussian configs blow up off-scale, to 161 m)',
        fontsize=8.5, color='0.3', va='top')
ax.axhline(np.sqrt(6) * NOISE, color='tab:purple', ls=':', lw=1.6,
           label=f'roughness floor forced by exact conditioning (√6·7.1 = {np.sqrt(6)*NOISE:.0f} m)')
ax.set_xscale('log')
ax.set_xlabel('|map − radar| at the radar cells, median [m]   ←  honors the data better')
ax.set_ylabel('2nd-difference roughness [m]   ←  smoother')
ax.set_title('the trade-off the sweep maps out\n(colour = variogram nugget fraction)')
fig.colorbar(sc, ax=ax, label='log₁₀ nugget fraction')
ax.legend(fontsize=8, loc='center right'); ax.grid(alpha=.3)
fig.savefig(FIGS / 'sweep_pareto.png', dpi=130, bbox_inches='tight')

# ---- contender maps
def field(tag):
    return np.load(SW / f'{tag}.npz')['field']

cands = []
for lab, q in [('exact conditioning', 'obs_med < 0.001'), ('sub-metre', '0.001 <= obs_med < 1'),
               ('smoothest overall', 'obs_med < 8')]:
    d = sgs.query(q).sort_values('rough')
    if len(d):
        cands.append((lab, d.iloc[0]))
vmin, vmax = np.percentile(trend, [2, 98])
panels = [('published bed', trend, ''), ('shipped MGSIM (nb 03)', shipped,
           f'err {np.median(np.abs(shipped[obs]-data_map[obs])):.1f} m · rough {rough(shipped):.0f} m')]
seen = set()
for lab, r in cands:
    if r.tag in seen: continue
    seen.add(r.tag)
    s = f"ν={r['s']:g} " if r.get('s') == r.get('s') and r.get('s') else ''
    panels.append((f"{lab}\n{r['model']} {s}nug {r['nug_frac']:g} k{r['k']} r×{r['range_mult']:g}",
                   field(r.tag), f"err {r['obs_med']:.2f} m · rough {r['rough']:.0f} m"))
n = len(panels)
fig2, axs = plt.subplots(2, n, figsize=(4.2 * n, 8.8), constrained_layout=True)
for j, (name, M, sub) in enumerate(panels):
    axs[0, j].imshow(M, origin='lower', cmap='terrain', vmin=vmin, vmax=vmax)
    axs[0, j].set_title(f'{name}\n{sub}', fontsize=9)
    axs[1, j].imshow(M[55:105, 55:105], origin='lower', cmap='terrain', vmin=vmin, vmax=vmax)
    axs[1, j].set_title('7.5 km zoom', fontsize=8)
    for a in (axs[0, j], axs[1, j]):
        a.set_xticks([]); a.set_yticks([])
fig2.savefig(FIGS / 'sweep_contenders.png', dpi=120, bbox_inches='tight')
print('\nsaved figures/sweep_pareto.png + figures/sweep_contenders.png')
both.to_csv(DERIVED / 'variogram_sweep_results.csv', index=False)
print(f'saved data/derived/variogram_sweep_results.csv ({len(both)} configs)')
