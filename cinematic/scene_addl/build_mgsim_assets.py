"""Build the Additional-Work "apply MGSIM to glaciology" page assets for
lake 1951 (2019cw428): the bed-topography ensemble under the Ch.2
simulation-domain block, the radar data that conditioned it, and the
Elmer/Ice stress results per bed.

Everything lands in the SAME plate-carree frame as the published Ch.2
tile (build_sim_domains.py: sim_domains.json bbox, 1024 px, row 0 =
north, alpha = the rotated-domain footprint) so the website can swap a
realization in for the published bed with one texture assignment.

Per realization i (00..09), plus the published bed:
  simbed_mgsimNN_rg16.png       bed RG16, same off/scale as the Ch.2 tile
  panel_diff_<bed>.png          side panel: bed − radar on the 150 m grid
Every drape on this page is seismic at ONE scale, ±VLIM_KPA (the director
set −400 to 400 kPa for everything in the ensemble; Ch.2 keeps its own ±1 MPa).
Where the bed's NO-PATCH run has landed (cinematic/scene_addl/mgsim/elmer_bundle/results/):
  simstress_nopatch_<bed>.png      σ_t1, no patch (absolute)
  simstress_nopatchdiff_<bed>.png  σ_t1 no patch: this bed − published bed
Where its PATCH twin has landed too:
  simstress_patch_<bed>.png        σ_t1, with patch (absolute)
  simstress_patchdiff_<bed>.png    with patch: this bed − published bed
  simstress_dsig_<bed>.png         Δσ_t1 = with patch − no patch (the
                                   published SI recipe)
  simstress_dsigdiff_<bed>.png     difference: this bed − published bed
  simlakes_<bed>.json           the Ch.2 drainage catalog with THIS bed's
                                in-polygon stress tables (same recipe as the
                                paper's pickles — verified to 0.1 kPa on the
                                published run)
Shared:
  panel_tracks.png              side panel: the radar picks over the domain
  bed_palette.png               256×1 hypsometric ramp (globe shader + panels
                                share it so colors match exactly)
  summary_<fam>_<kind>.png      one panel each: fam ∈ {nopatch, patch, dsig},
                                kind ∈ {published, mean, std, bias}
  phase_space_mgsim.json        Fig.-5 stress space per bed: the published
                                context lakes + this domain's five lakes
  cg_fig05.jpg                  C&G Fig. 5 thumbnail for the menu card
  mgsim_meta.json               everything the page needs to know

Inputs (project copies only):
  cinematic/scene_addl/mgsim/data/derived/bed_realizations_cw1951.npz    (nb 03 ensemble)
  cinematic/scene_addl/mgsim/data/derived/gridded_bed_cw1951_150m.npz    (nb 02 radar grid)
  cinematic/scene_addl/mgsim/data/derived/radar_picks_cw1951_aoi50km.csv (nb 01 picks)
  cinematic/scene_addl/mgsim/elmer_bundle/results/*_{nopatch,patch}_mgsimNN_*.npz
  cinematic/source_data/pnas_sims/2019cw428_*_viscous.nc (published run)
  cinematic/scene_ch02/output_simdomains/{sim_domains,simlakes_CW2019_1951,
                                           phase_space}.json
  cinematic/source_data/cg_paper/fig05_synthcompare.png (fetch_sources.sh)

Outputs: cinematic/scene_addl/output_mgsim/ → R2 addl/mgsim/

Run (defense checkout root):
  ./cinematic/.venv/bin/python -u cinematic/scene_addl/build_mgsim_assets.py
"""
import glob
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import xarray as xr  # noqa: E402
from matplotlib import colormaps  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, Normalize  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402
from PIL import Image  # noqa: E402
from pyproj import Transformer  # noqa: E402
from scipy.ndimage import map_coordinates  # noqa: E402

sys.stdout.reconfigure(line_buffering=True)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'cinematic'))
sys.path.insert(0, str(ROOT / 'cinematic' / 'scene_addl' / 'mgsim' / 'scripts'))
from shared import SOURCE_DATA, require_source  # noqa: E402
from plot_nopatch_stress import MPA_TO_KPA, SIGMA_KEYS  # noqa: E402

LAKE_ID = 'CW2019_1951'
OLD_ID = '2019cw428'
CENTER_NUM = 1951
DERIVED = ROOT / 'cinematic' / 'scene_addl' / 'mgsim' / 'data' / 'derived'
RESULTS = ROOT / 'cinematic' / 'scene_addl' / 'mgsim' / 'elmer_bundle' / 'results'
CH2_OUT = ROOT / 'cinematic' / 'scene_ch02' / 'output_simdomains'
SIM_DOMAINS = CH2_OUT / 'sim_domains.json'
CH2_LAKES = CH2_OUT / f'simlakes_{LAKE_ID}.json'
CH2_PHASE = CH2_OUT / 'phase_space.json'
PUB_NC = SOURCE_DATA / 'pnas_sims' / f'{OLD_ID}_d25km_r2500m_csi6.5e6_tsic_viscous.nc'
CG_FIG = SOURCE_DATA / 'cg_paper' / 'fig05_synthcompare.png'
OUT = ROOT / 'cinematic' / 'scene_addl' / 'output_mgsim'

OUT_PX = 1024              # same raster size as the Ch.2 tiles
DEM_STEP_M = 150.0         # the Elmer DEM lattice
DEM_N = 166
DEM_HALF_M = 12375.0       # 24.75 km Elmer domain
VLIM_KPA = 400.0           # EVERY seismic drape + summary panel on this page
DIFF_VLIM_M = 100.0        # bed − radar side panel

# Site-dark figure style (Ch.1 map beats).
PAGE_BG = '#0a0908'
INK = '#f5f0e6'
INK_DIM = '#9a948a'
GOLD = '#f5c75e'

# "Classic" hypsometric bed ramp: deep blue below sea level → sea-green
# lowlands → pale green → tan → white highs. Stops in metres.
BED_VMIN_M, BED_VMAX_M = -300.0, 600.0
BED_STOPS_M = [
    (-300, '#081d4f'), (-120, '#1d4fa8'), (-1, '#57a5e0'),
    (0, '#1f7a4d'), (120, '#4fae5c'), (260, '#a9d67a'),
    (380, '#e5d8a5'), (480, '#f1ebd6'), (600, '#ffffff'),
]
T4326_3413 = Transformer.from_crs('EPSG:4326', 'EPSG:3413', always_xy=True)

# Fig.-5 group of each catalog class (the dashed/uncertain classes share
# their solid hue; the phase panel colors by group).
PHASE_GROUP = {'cyan': 'cyan', 'dashcyan': 'cyan', 'gray': 'gray', 'dashgray': 'gray',
               'black': 'black', 'magenta': 'magenta'}


def bed_cmap() -> LinearSegmentedColormap:
    stops = [((m - BED_VMIN_M) / (BED_VMAX_M - BED_VMIN_M), c) for m, c in BED_STOPS_M]
    return LinearSegmentedColormap.from_list('bed_hypso', stops)


# ── the tile frame (identical construction to build_sim_domains) ──────
class TileFrame:
    def __init__(self, meta: dict):
        self.meta = meta
        b = meta['bbox']
        self.lon_w, self.lon_e = b['lon_w'], b['lon_e']
        self.lat_s, self.lat_n = b['lat_s'], b['lat_n']
        e0, n0 = T4326_3413.transform(meta['lon'], meta['lat'])
        th = np.deg2rad(meta['flow_angle_deg'])
        cos_t, sin_t = np.cos(th), np.sin(th)
        glon = np.linspace(self.lon_w, self.lon_e, OUT_PX)
        glat = np.linspace(self.lat_n, self.lat_s, OUT_PX)   # row 0 = north
        glon2, glat2 = np.meshgrid(glon, glat)
        ge, gn = T4326_3413.transform(glon2, glat2)
        self.lx = (ge - e0) * cos_t + (gn - n0) * sin_t
        self.ly = -(ge - e0) * sin_t + (gn - n0) * cos_t
        half_m = meta['domain_half_km'] * 1e3
        self.inside = (np.abs(self.lx) <= half_m) & (np.abs(self.ly) <= half_m)
        self.alpha = (self.inside * 255).astype(np.uint8)

    def sample_dem(self, grid166: np.ndarray) -> np.ndarray:
        """Bilinear sample of a [iy, ix] 166×166 Elmer-lattice field."""
        fy = np.clip((self.ly + DEM_HALF_M) / DEM_STEP_M, 0, DEM_N - 1)
        fx = np.clip((self.lx + DEM_HALF_M) / DEM_STEP_M, 0, DEM_N - 1)
        return map_coordinates(grid166, [fy, fx], order=1, mode='nearest')

    def sample_nc(self, field: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Bilinear sample of a published-lattice (y, x) field, clamped."""
        fx = np.clip((self.lx - x[0]) / (x[-1] - x[0]), 0, 1) * (len(x) - 1)
        fy = np.clip((self.ly - y[0]) / (y[-1] - y[0]), 0, 1) * (len(y) - 1)
        return map_coordinates(field, [fy, fx], order=1, mode='nearest')

    def uv_to_local(self, ring_uv: list) -> np.ndarray:
        """Catalog ring (tile u,v ∈ [0,1], v down) → local rotated metres."""
        cols = np.array([u * (OUT_PX - 1) for u, _ in ring_uv])
        rows = np.array([v * (OUT_PX - 1) for _, v in ring_uv])
        lx = map_coordinates(self.lx, [rows, cols], order=1)
        ly = map_coordinates(self.ly, [rows, cols], order=1)
        return np.c_[lx, ly]


def write_rg16(path: Path, values_m: np.ndarray, off_m: float, scale_m: float,
               alpha: np.ndarray) -> None:
    u16 = (np.clip((values_m - off_m) / scale_m, 0, 1) * 65535).astype(np.uint32)
    rgba = np.zeros((OUT_PX, OUT_PX, 4), dtype=np.uint8)
    rgba[..., 0] = (u16 >> 8).astype(np.uint8)
    rgba[..., 1] = (u16 & 255).astype(np.uint8)
    rgba[..., 3] = alpha
    Image.fromarray(rgba).save(path, optimize=True)


def write_seismic(path: Path, kpa: np.ndarray, vlim: float, alpha: np.ndarray) -> None:
    norm = np.clip((kpa + vlim) / (2 * vlim), 0, 1)
    rgba = (colormaps['seismic'](norm) * 255).astype(np.uint8)
    rgba[..., 3] = alpha
    Image.fromarray(rgba).save(path, optimize=True)


def write_palette(path: Path) -> None:
    cm = bed_cmap()
    row = (cm(np.linspace(0, 1, 256))[None, :, :] * 255).astype(np.uint8)
    Image.fromarray(row, 'RGBA').save(path)


# ── stress recipe (published SI, verified against the paper's pickles) ─
def tangent_principals(sig: dict, topo: np.ndarray, x: np.ndarray, y: np.ndarray):
    """Project a surface Cauchy tensor into the surface tangent plane and
    return the in-plane principals (σ_t1 ≥ σ_t2), tension positive, kPa.
    Applied to (patch − no patch) it is the paper's stress response."""
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
    return (mean + rad) * MPA_TO_KPA, (mean - rad) * MPA_TO_KPA


def _stats(arr: np.ndarray) -> dict:
    a = np.asarray(arr, dtype=float)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return {'max': None, 'min': None, 'mean': None}
    return {'max': round(float(np.max(a)), 1), 'min': round(float(np.min(a)), 1),
            'mean': round(float(np.mean(a)), 1)}


def lake_masks(frame: TileFrame, catalog: list, x: np.ndarray, y: np.ndarray) -> list:
    """[(lake, mask on the published lattice)] — the paper's in-polygon
    sets (the main ring of each catalog lake)."""
    X, Y = np.meshgrid(x, y)
    pts = np.c_[X.ravel(), Y.ravel()]
    out = []
    for lk in catalog:
        ring = max(lk['rings_uv'], key=len)
        m = MPath(frame.uv_to_local(ring)).contains_points(pts).reshape(X.shape)
        out.append((lk, m))
    return out


def lake_tables(masks: list, p1, p2, d1, d2) -> dict:
    """{cw: {'n_points', 'viscous': {s1_post, s2_post, s1_diff, s2_diff}}}
    — the simlakes stats block, viscous model, for one bed."""
    out = {}
    for lk, m in masks:
        out[lk['cw']] = {
            'n_points': int(m.sum()),
            'viscous': {'s1_post': _stats(p1[m]), 's2_post': _stats(p2[m]),
                        's1_diff': _stats(d1[m]), 's2_diff': _stats(d2[m])},
            'elastic': None,   # no elastic runs in the ensemble
        }
    return out


def write_lakes_json(path: Path, catalog: list, tables: dict | None) -> None:
    lakes = []
    for lk in catalog:
        e = dict(lk)
        e['stats'] = tables.get(lk['cw']) if tables else None
        lakes.append(e)
    path.write_text(json.dumps({'center': LAKE_ID, 'center_cw': int(OLD_ID[6:]),
                                'lakes': lakes}, separators=(',', ':')))


def phase_points(catalog: list, tables: dict) -> list:
    """This domain's lakes as Fig.-5 points (polygon means: post-drainage
    σ vs Δσ) — ALL five catalog lakes here, flagged with the paper's
    Fig.-5 membership, so the ensemble cloud has more than one dot."""
    pts = []
    for lk in catalog:
        t = tables.get(lk['cw'])
        if not t:
            continue
        v = t['viscous']
        pts.append({'center': CENTER_NUM, 'num': lk['num'], 'group': PHASE_GROUP[lk['cls']],
                    'cls': lk['cls'], 'phase': bool(lk['phase']), 'is_center': bool(lk['center']),
                    'x1': v['s1_post']['mean'], 'y1': v['s1_diff']['mean'],
                    'x2': v['s2_post']['mean'], 'y2': v['s2_diff']['mean']})
    return pts


# ── side panels ────────────────────────────────────────────────────────
def style_axes(ax, title: str) -> None:
    ax.set_facecolor(PAGE_BG)
    ax.set_title(title, fontsize=15, color=GOLD, pad=8, family='serif')
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


def draw_frames(ax, half_dom_km: float, half_tile_km: float) -> None:
    ax.add_patch(plt.Rectangle((-half_dom_km, -half_dom_km), 2 * half_dom_km,
                               2 * half_dom_km, fill=False, ec=INK_DIM, lw=0.9))
    ax.add_patch(plt.Rectangle((-half_tile_km, -half_tile_km), 2 * half_tile_km,
                               2 * half_tile_km, fill=False, ec=GOLD, lw=1.4))
    ax.annotate('', xy=(half_dom_km - 1.2, -half_dom_km + 1.6),
                xytext=(half_dom_km - 5.2, -half_dom_km + 1.6),
                arrowprops=dict(arrowstyle='-|>', color=GOLD, lw=1.4))
    ax.text(half_dom_km - 3.2, -half_dom_km + 2.3, 'ice flow', color=GOLD,
            fontsize=8.5, ha='center', family='serif')


def new_panel(title: str, half_km: float = DEM_HALF_M / 1e3):
    plt.rcParams.update({'font.family': 'serif', 'text.color': INK,
                         'axes.edgecolor': INK})
    fig, ax = plt.subplots(figsize=(6.0, 5.5), facecolor=PAGE_BG)
    style_axes(ax, title)
    ax.set_aspect('equal')
    ax.set_xlim(-half_km - 0.4, half_km + 0.4)
    ax.set_ylim(-half_km - 0.4, half_km + 0.4)
    return fig, ax


def finish_panel(fig, ax, mappable, cbar_label: str, foot: str, out: Path) -> None:
    cb = fig.colorbar(mappable, ax=ax, fraction=0.046, pad=0.02, shrink=0.86)
    cb.set_label(cbar_label, fontsize=11, color=INK)
    cb.ax.tick_params(labelsize=9, colors=INK)
    cb.outline.set_edgecolor('#555')
    fig.text(0.01, 0.012, foot, fontsize=7.4, color=INK_DIM, ha='left', va='bottom',
             family='serif', wrap=True)
    fig.subplots_adjust(left=0.01, right=0.9, top=0.92, bottom=0.07)
    fig.savefig(out, dpi=150, facecolor=PAGE_BG)
    plt.close(fig)


def panel_tracks(picks: pd.DataFrame, half_tile_km: float, out: Path) -> dict:
    fig, ax = new_panel('Ice-penetrating radar bed picks')
    cm = bed_cmap()
    norm = Normalize(BED_VMIN_M, BED_VMAX_M)
    sc = ax.scatter(picks['LX'] / 1e3, picks['LY'] / 1e3, c=picks['BED_ELEV_GEOID'],
                    cmap=cm, norm=norm, s=1.1, linewidths=0, rasterized=True)
    draw_frames(ax, DEM_HALF_M / 1e3, half_tile_km)
    seasons = sorted(set(str(s)[:4] for s in picks['SEASON']))
    n = len(picks)
    foot = (f'{n:,} picks · {len(seasons)} seasons {seasons[0]}–{seasons[-1]} · '
            'CReSIS L2 radar depth sounder (Univ. of Kansas / NASA Operation IceBridge / NSF)\n'
            'gray = 24.75 km Elmer/Ice domain · gold = 14.75 km analysis tile (the block)')
    finish_panel(fig, ax, sc, 'bed elevation (m)', foot, out)
    return {'n_picks': int(n), 'seasons': seasons}


def panel_diff(diff166: np.ndarray, mask166: np.ndarray, label: str, half_tile_km: float,
               out: Path) -> dict:
    fig, ax = new_panel(f'{label} − radar')
    field = np.where(mask166, diff166, np.nan)
    ext = [-DEM_HALF_M / 1e3, DEM_HALF_M / 1e3, -DEM_HALF_M / 1e3, DEM_HALF_M / 1e3]
    im = ax.imshow(field, origin='lower', extent=ext, cmap='RdBu_r',
                   vmin=-DIFF_VLIM_M, vmax=DIFF_VLIM_M, interpolation='nearest')
    draw_frames(ax, DEM_HALF_M / 1e3, half_tile_km)
    v = diff166[mask166]
    stats = {'median_abs_m': float(np.median(np.abs(v))), 'std_m': float(np.std(v)),
             'p95_abs_m': float(np.percentile(np.abs(v), 95)), 'n_cells': int(mask166.sum())}
    foot = (f'150 m cells with picks: {stats["n_cells"]:,} · median |Δ| {stats["median_abs_m"]:.1f} m · '
            f'p95 |Δ| {stats["p95_abs_m"]:.0f} m · std {stats["std_m"]:.0f} m\n'
            'radar cell value = mean surface − harmonic-mean thickness of every pick in the cell, '
            'shifted to the published (geoid) datum')
    finish_panel(fig, ax, im, 'bed − radar (m)', foot, out)
    return stats


def summary_panel(field: np.ndarray, x: np.ndarray, y: np.ndarray, cmap: str, lo: float,
                  hi: float, title: str, foot: str, out: Path) -> None:
    """ONE readable panel (the page shows them one at a time, large)."""
    half_km = x[-1] / 1e3
    fig, ax = new_panel(title, half_km)
    ext = [x[0] / 1e3, x[-1] / 1e3, y[0] / 1e3, y[-1] / 1e3]
    im = ax.imshow(field, origin='lower', extent=ext, cmap=cmap, vmin=lo, vmax=hi)
    ax.add_patch(plt.Rectangle((-half_km, -half_km), 2 * half_km, 2 * half_km,
                               fill=False, ec=GOLD, lw=1.2))
    ax.annotate('', xy=(half_km - 0.8, -half_km + 1.0), xytext=(half_km - 3.3, -half_km + 1.0),
                arrowprops=dict(arrowstyle='-|>', color=GOLD, lw=1.4))
    ax.text(half_km - 2.05, -half_km + 1.45, 'ice flow', color=GOLD, fontsize=8.5,
            ha='center', family='serif')
    finish_panel(fig, ax, im, 'kPa', foot, out)


def summary_family(fam: str, name: str, pub: np.ndarray, reals: dict, x, y) -> tuple[dict, dict]:
    """Four panels (published · ensemble mean · ensemble std · mean −
    published) + the family's numbers."""
    V = VLIM_KPA
    stack = np.stack(list(reals.values()))
    mean = stack.mean(0)
    std = stack.std(0, ddof=1) if len(reals) > 1 else np.zeros_like(mean)
    bias = mean - pub

    def corr2(a, b):
        return float(np.corrcoef(a.ravel(), b.ravel())[0, 1])

    stats = {'n': len(reals), 'spread_kpa': float(np.nanmean(std)),
             'bias_kpa': float(np.nanmean(bias)), 'rms_kpa': float(np.sqrt(np.nanmean(bias ** 2))),
             'pub_std_kpa': float(np.nanstd(pub)),
             'real_std_kpa': [float(np.nanstd(r)) for r in reals.values()],
             'corr': [corr2(pub, r) for r in reals.values()],
             'std_p995_kpa': float(np.nanpercentile(std, 99.5))}
    n = len(reals)
    foot_pub = f'{name} with the published bed · the reference every realization is compared to'
    foot_mean = f'pixel-wise mean over {n} bed realizations · same scale as the published panel'
    foot_std = (f'pixel-wise standard deviation over {n} realizations · '
                f'mean {stats["spread_kpa"]:.0f} kPa · a map of where the bed matters')
    foot_bias = (f'ensemble mean minus the published bed\'s field · '
                 f'bias {stats["bias_kpa"]:+.0f} kPa · RMS {stats["rms_kpa"]:.0f} kPa')
    panels = {
        'published': (pub, 'seismic', -V, V, f'published bed · {name}', foot_pub),
        'mean': (mean, 'seismic', -V, V, f'ensemble mean · n = {n}', foot_mean),
        'std': (std, 'magma', 0, max(1.0, stats['std_p995_kpa']), f'ensemble spread (std) · n = {n}', foot_std),
        'bias': (bias, 'seismic', -V, V, 'ensemble mean − published', foot_bias),
    }
    files = {}
    for kind, (a, cmap, lo, hi, title, foot) in panels.items():
        fn = f'summary_{fam}_{kind}.png'
        summary_panel(a, x, y, cmap, lo, hi, title, foot, OUT / fn)
        files[kind] = fn
    return files, stats


# ── main ───────────────────────────────────────────────────────────────
def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    doms = json.loads(SIM_DOMAINS.read_text())['lakes']
    meta = next(d for d in doms if d['id'] == LAKE_ID)
    frame = TileFrame(meta)
    half_tile_km = meta['domain_half_km']
    bed_off, bed_scale = meta['bed_off_m'], meta['bed_scale_m']

    # Realizations + the published bed on the Elmer lattice.
    z = np.load(DERIVED / 'bed_realizations_cw1951.npz')
    beds, trend = z['beds'], z['trend']
    nb03 = json.loads(str(z['meta']))
    datum_shift = float(nb03['datum_shift_m'])
    n_real = beds.shape[0]

    # Radar grid (nb 02): 334×334 extended lattice; Elmer = [84, 250).
    g = np.load(DERIVED / 'gridded_bed_cw1951_150m.npz')
    lo, hi = json.loads(str(g['meta']))['dem_sub_lattice']
    sl = slice(lo, hi + 1)
    radar166 = g['bed_hm'][sl, sl] - datum_shift          # → published datum
    mask166 = np.isfinite(radar166) & (g['n_all'][sl, sl] > 0)
    assert radar166.shape == (DEM_N, DEM_N), radar166.shape
    # Frame check: the radar grid must sit on the published bed's lattice
    # (as-is 0.85; transposed 0.48, flipped −0.19 — the picks scatter 58 m
    # about the published bed, so 0.85 IS aligned).
    c = np.corrcoef(trend[mask166], radar166[mask166])[0, 1]
    assert c > 0.7, f'radar grid / published bed misaligned (corr {c:.2f})'
    print(f'radar grid vs published bed: corr {c:.3f} on {int(mask166.sum())} cells')

    # Published run on its own lattice: no-patch (intact ice) + patch.
    ds = xr.open_dataset(require_source(PUB_NC))
    x, y = ds.x.values.astype(float), ds.y.values.astype(float)
    pub_sig = {k: ds[k].sel(level='surf', case='nopatch').values.astype(float) for k in SIGMA_KEYS}
    pat_sig = {k: ds[k].sel(level='surf', case='patch').values.astype(float) for k in SIGMA_KEYS}
    pub_surf = ds['topo_surf'].sel(level='surf', case='nopatch').values.astype(float)
    pub_bed = ds['topo_bed'].sel(level='surf', case='nopatch').values.astype(float)
    pub_s1, _ = tangent_principals(pub_sig, pub_surf, x, y)
    pub_p1, pub_p2 = tangent_principals(pat_sig, pub_surf, x, y)
    pub_d1, pub_d2 = tangent_principals({k: pat_sig[k] - pub_sig[k] for k in SIGMA_KEYS}, pub_surf, x, y)
    # Sanity: the published tile bed must match the nb-03 trend (the sif DEM).
    fy = (np.meshgrid(x, y)[1] + DEM_HALF_M) / DEM_STEP_M
    fx = (np.meshgrid(x, y)[0] + DEM_HALF_M) / DEM_STEP_M
    rms = np.sqrt(np.mean((map_coordinates(trend, [fy, fx], order=1) - pub_bed) ** 2))
    assert rms < 3, f'trend vs published nc bed rms {rms:.1f} m'
    print(f'trend vs published nc bed: rms {rms:.2f} m')
    # The response recipe must be build_sim_domains' (its p99.7 is on record).
    p997 = float(np.nanpercentile(np.abs(pub_d1), 99.7))
    assert abs(p997 - meta['viscous_p997_kpa']) < 5, \
        f'published Δσ recipe drifted from build_sim_domains: {p997:.1f} vs {meta["viscous_p997_kpa"]}'
    print(f'published Δσ_t1 p99.7 = {p997:.0f} kPa (matches sim_domains.json)')

    write_palette(OUT / 'bed_palette.png')

    # ── the drainage catalog + the paper's in-polygon sets ──
    catalog = json.loads(CH2_LAKES.read_text())['lakes']
    masks = lake_masks(frame, catalog, x, y)
    pub_tables = lake_tables(masks, pub_p1, pub_p2, pub_d1, pub_d2)
    # Guard: the polygons land where the paper's pickles put them (the
    # Ch.2 catalog carries the pickled tables — same counts, same means).
    for lk, m in masks:
        ref = lk.get('stats')
        if not ref:
            continue
        mine = pub_tables[lk['cw']]
        assert abs(mine['n_points'] - ref['n_points']) <= 3, \
            f'lake {lk["num"]}: {mine["n_points"]} vs pickled {ref["n_points"]} points'
        for key in ('s1_post', 's2_post', 's1_diff', 's2_diff'):
            dv = abs(mine['viscous'][key]['mean'] - ref['viscous'][key]['mean'])
            assert dv < 1.0, f'lake {lk["num"]} {key}: {dv:.1f} kPa off the pickles'
    print(f'lake stats: {len(masks)} polygons reproduce the paper\'s pickles (counts + means)')
    write_lakes_json(OUT / 'simlakes_published.json', catalog, pub_tables)

    # ── beds ──
    entries = []
    for i in range(n_real):
        tag = f'mgsim{i:02d}'
        write_rg16(OUT / f'simbed_{tag}_rg16.png', frame.sample_dem(beds[i]),
                   bed_off, bed_scale, frame.alpha)
        entries.append({'id': tag, 'label': f'MGSIM realization {i + 1:02d}', 'seed': nb03['seeds'][i],
                        'bed': f'simbed_{tag}_rg16.png', 'bed_min_m': float(beds[i].min()),
                        'bed_max_m': float(beds[i].max())})
        print(f'  bed {tag}: {beds[i].min():.0f}..{beds[i].max():.0f} m')

    # ── side panels ──
    picks = pd.read_csv(DERIVED / 'radar_picks_cw1951_aoi50km.csv',
                        usecols=['SEASON', 'LX', 'LY', 'BED_ELEV', 'DATUM_SUSPECT'])
    picks = picks[(picks['LX'].abs() <= DEM_HALF_M) & (picks['LY'].abs() <= DEM_HALF_M)
                  & (~picks['DATUM_SUSPECT'].astype(bool))].copy()
    picks['BED_ELEV_GEOID'] = picks['BED_ELEV'] - datum_shift
    tracks = panel_tracks(picks, half_tile_km, OUT / 'panel_tracks.png')
    print(f'  tracks panel: {tracks["n_picks"]:,} picks, seasons {tracks["seasons"][0]}–{tracks["seasons"][-1]}')

    pub_stats = panel_diff(trend - radar166, mask166, 'Published bed', half_tile_km,
                           OUT / 'panel_diff_published.png')
    print(f'  diff published: median |Δ| {pub_stats["median_abs_m"]:.1f} m, std {pub_stats["std_m"]:.0f}')
    for i, e in enumerate(entries):
        e['diff'] = f'panel_diff_{e["id"]}.png'
        e['diff_stats'] = panel_diff(beds[i] - radar166, mask166, e['label'], half_tile_km,
                                     OUT / e['diff'])
    print(f'  diff realizations: median |Δ| '
          + ', '.join(f'{e["diff_stats"]["median_abs_m"]:.1f}' for e in entries) + ' m')

    # ── published drapes at THIS page's scale ──
    write_seismic(OUT / 'simstress_nopatch_published.png',
                  frame.sample_nc(pub_s1, x, y), VLIM_KPA, frame.alpha)
    write_seismic(OUT / 'simstress_patch_published.png',
                  frame.sample_nc(pub_p1, x, y), VLIM_KPA, frame.alpha)
    write_seismic(OUT / 'simstress_dsig_published.png',
                  frame.sample_nc(pub_d1, x, y), VLIM_KPA, frame.alpha)

    def corr(a, b):
        return float(np.corrcoef(a.ravel(), b.ravel())[0, 1])

    def rms_of(a, b):
        return float(np.sqrt(np.nanmean((a - b) ** 2)))

    def load_run(cfg, i):
        fs = glob.glob(str(RESULTS / f'*_{cfg}_mgsim{i:02d}_*.npz'))
        if not fs:
            return None
        r = np.load(fs[0])
        assert np.allclose(r['x'], x) and np.allclose(r['y'], y), f'{fs[0]}: lattice mismatch'
        return r

    # ── Elmer results that have landed ──
    reals_s1, reals_p1, reals_dsig = {}, {}, {}
    phase_models = {}

    def field_stats(a, pub):
        return {'std_kpa': float(np.nanstd(a)), 'p997_kpa': float(np.nanpercentile(np.abs(a), 99.7)),
                'corr_pub': corr(pub, a), 'rms_pub_kpa': rms_of(a, pub)}

    for i, e in enumerate(entries):
        tag = e['id']
        rn, rp = load_run('nopatch', i), load_run('patch', i)
        if rn is None:
            continue
        n_sig = {k: rn[k].astype(float) for k in SIGMA_KEYS}
        n_surf = rn['topo_surf'].astype(float)
        s1, _ = tangent_principals(n_sig, n_surf, x, y)
        write_seismic(OUT / f'simstress_nopatch_{tag}.png', frame.sample_nc(s1, x, y),
                      VLIM_KPA, frame.alpha)
        write_seismic(OUT / f'simstress_nopatchdiff_{tag}.png', frame.sample_nc(s1 - pub_s1, x, y),
                      VLIM_KPA, frame.alpha)
        e['stress_nopatch'] = f'simstress_nopatch_{tag}.png'
        e['stress_nopatchdiff'] = f'simstress_nopatchdiff_{tag}.png'
        e['nopatch_stats'] = field_stats(s1, pub_s1)
        reals_s1[tag] = s1
        line = (f'  {tag}: no-patch σ_t1 std {np.nanstd(s1):.0f} kPa, corr {e["nopatch_stats"]["corr_pub"]:.2f}, '
                f'RMS vs pub {e["nopatch_stats"]["rms_pub_kpa"]:.0f}')
        if rp is not None:
            p_sig = {k: rp[k].astype(float) for k in SIGMA_KEYS}
            p1, p2 = tangent_principals(p_sig, n_surf, x, y)
            d1, d2 = tangent_principals({k: p_sig[k] - n_sig[k] for k in SIGMA_KEYS}, n_surf, x, y)
            write_seismic(OUT / f'simstress_patch_{tag}.png', frame.sample_nc(p1, x, y),
                          VLIM_KPA, frame.alpha)
            write_seismic(OUT / f'simstress_patchdiff_{tag}.png', frame.sample_nc(p1 - pub_p1, x, y),
                          VLIM_KPA, frame.alpha)
            write_seismic(OUT / f'simstress_dsig_{tag}.png', frame.sample_nc(d1, x, y),
                          VLIM_KPA, frame.alpha)
            write_seismic(OUT / f'simstress_dsigdiff_{tag}.png', frame.sample_nc(d1 - pub_d1, x, y),
                          VLIM_KPA, frame.alpha)
            e['stress_patch'] = f'simstress_patch_{tag}.png'
            e['stress_patchdiff'] = f'simstress_patchdiff_{tag}.png'
            e['patch_stats'] = field_stats(p1, pub_p1)
            e['stress_dsig'] = f'simstress_dsig_{tag}.png'
            e['stress_dsigdiff'] = f'simstress_dsigdiff_{tag}.png'
            e['dsig_stats'] = field_stats(d1, pub_d1)
            reals_p1[tag] = p1
            tables = lake_tables(masks, p1, p2, d1, d2)
            e['lakes'] = f'simlakes_{tag}.json'
            write_lakes_json(OUT / e['lakes'], catalog, tables)
            e['phase_key'] = tag
            phase_models[tag] = phase_points(catalog, tables)
            reals_dsig[tag] = d1
            line += (f' · Δσ p99.7 {e["dsig_stats"]["p997_kpa"]:.0f} kPa, corr {e["dsig_stats"]["corr_pub"]:.2f}, '
                     f'RMS vs pub {e["dsig_stats"]["rms_pub_kpa"]:.0f}')
        print(line)

    # ── summary panels (one image each; three families) ──
    summary_panels, summary_stats = {}, {}
    for fam, name, pub, reals in (('nopatch', 'σ$_{t1}$ · no patch', pub_s1, reals_s1),
                                  ('patch', 'σ$_{t1}$ · with patch', pub_p1, reals_p1),
                                  ('dsig', 'Δσ$_{t1}$ · with patch − no patch', pub_d1, reals_dsig)):
        if not reals:
            summary_stats[fam] = None
            continue
        files, st = summary_family(fam, name, pub, reals, x, y)
        summary_panels[fam] = files
        summary_stats[fam] = st
        print(f'  summary {fam}: n={st["n"]} spread {st["spread_kpa"]:.0f} kPa · RMS vs pub {st["rms_kpa"]:.0f} · bias {st["bias_kpa"]:+.0f}')

    # ── phase space per bed: the published context + this domain's lakes ──
    ch2_phase = json.loads(CH2_PHASE.read_text())
    context = [p for p in ch2_phase['models']['viscous']['points'] if p['center'] != CENTER_NUM]
    pub_pts = phase_points(catalog, pub_tables)
    models = {'published': {'points': context + pub_pts, 'axis_kpa': 500}}
    for key, pts in phase_models.items():
        models[key] = {'points': context + pts, 'axis_kpa': 500}
    (OUT / 'phase_space_mgsim.json').write_text(json.dumps({
        'center': CENTER_NUM, 'models': models, 'error_kpa': ch2_phase['error_kpa'],
    }, separators=(',', ':')))
    print(f'  phase space: {len(models)} bed keys × {len(pub_pts)} domain lakes (+{len(context)} context)')

    # ── C&G Fig. 5 thumbnail ──
    im = Image.open(require_source(CG_FIG)).convert('RGB')
    im.thumbnail((1400, 1400))
    im.save(OUT / 'cg_fig05.jpg', quality=88, optimize=True)

    meta_out = {
        'lake': LAKE_ID, 'old_id': OLD_ID, 'center_num': CENTER_NUM,
        'published': {
            'id': 'published', 'label': 'Published bed (PNAS)',
            'bed': f'ch02/sim/{meta["bed"]}',       # reuse the Ch.2 tile
            'bed_min_m': float(pub_bed.min()), 'bed_max_m': float(pub_bed.max()),
            'diff': 'panel_diff_published.png', 'diff_stats': pub_stats,
            'stress_nopatch': 'simstress_nopatch_published.png',
            'nopatch_stats': field_stats(pub_s1, pub_s1),
            'stress_patch': 'simstress_patch_published.png',
            'patch_stats': field_stats(pub_p1, pub_p1),
            'stress_dsig': 'simstress_dsig_published.png',
            'dsig_stats': field_stats(pub_d1, pub_d1),
            'lakes': 'simlakes_published.json',
            'phase_key': 'published',
        },
        'realizations': entries,
        'bed_off_m': bed_off, 'bed_scale_m': bed_scale,
        'bed_vmin_m': BED_VMIN_M, 'bed_vmax_m': BED_VMAX_M,
        'bed_palette': 'bed_palette.png',
        'vlim_kpa': VLIM_KPA,
        'diff_vlim_m': DIFF_VLIM_M,
        'tracks': 'panel_tracks.png', 'tracks_stats': tracks,
        'summary_panels': summary_panels,
        'summary_stats': summary_stats,
        'phase_space': 'phase_space_mgsim.json',
        'method': {
            'generator': 'multigrid_sgsim (MGSIM), notebook 03',
            'variogram': nb03['vario'], 'vario_units': nb03['vario_units'],
            'mg_resols_px': nb03['mg_resols_px'], 'datum_shift_m': datum_shift,
            'taper_m': nb03['taper_m'], 'n_real': n_real,
        },
        'radar_source': 'CReSIS L2 radar depth-sounder bed picks, 1993–2019 '
                        '(University of Kansas, NASA Operation IceBridge, NSF)',
        'elmer': 'viscous Elmer/Ice, published 2019cw428 setup (Csi 6.5e6, SICOPOLIS '
                 'temperature, identical BCs), bed DEM swapped per realization',
    }
    (OUT / 'mgsim_meta.json').write_text(json.dumps(meta_out, indent=1))
    total = sum(p.stat().st_size for p in OUT.iterdir()) / 1e6
    print(f'wrote {len(list(OUT.iterdir()))} files, {total:.1f} MB → {OUT}')


if __name__ == '__main__':
    main()
