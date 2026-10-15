#!/usr/bin/env python
"""Bake the Additional-Work "deeper dive" page for Chapter 2
(/additional-work/deeper/chapter2 — the director's deeper-dive page for Chapter 2).

Three parts, each its own subcommand:

  fields   — the FIELD VIEWER's rasters (#fields). For each of the seven
             PNAS center lakes x {viscous, elastic} x every surface field
             the PNAS SI overview figures carry (SI Figs. S7-S20 = thesis
             Figs. 2.5-2.18), one map image: the field in the SI's own
             colour map and range, draped over a hillshade of the model's
             surface, with the SI's own overlays baked in (principal-stress
             hashes, the dashed +100 kPa contour, the white velocity
             vectors). Lake outlines, numbers, the tile outline and the
             axes are NOT baked: the page draws them as SVG from
             lake_<id>.json so they stay crisp and identical across fields.
  figures  — the static figures (#stress-spaces and the rest): the thesis
             Chapter 2 figure files, the PNAS main-text figures and the SI
             figure files, whole, flattened onto white, trimmed to their
             own white gutters, <= 2000 px wide.
  tex      — the LaTeX-typeset field names (latex + dvisvgm).

The field recipes are the SI generator's own, re-implemented here from
sgl-stress/3d/elmer/postprocess/visualize/lake_overview_localsigma.py and
elastic_overview_localsigma.py (+ src/stress_utils.py, src/georef.py):

  * georeference: E = E0 + x cos(th) - y sin(th), N = N0 + x sin(th) +
    y cos(th), (E0, N0) = the lake's geojson centroid in EPSG:3413, th =
    the tile's flow angle (tile_attrs.json);
  * sigma_t1, sigma_t2, sigma_n: the Cauchy tensor at the surface projected
    into the local basis (e1, e2, n) of the NO-PATCH surface (n from
    np.gradient of topo_surf, e1 = Gram-Schmidt of x-hat against n,
    e2 = n x e1); in-plane principals mean +- radius; sigma_n = n.S.n;
  * the DIFFERENCE column is tensor-first: subtract the tensors component
    by component, then take the principals of the difference tensor
    (Delta sigma_t1 != sigma_t1^post - sigma_t1^pre in general);
  * sigma_rr, sigma_rtheta, sigma_thetatheta straight from the netCDF
    (polar about the patch/blister centre), difference = post - pre;
  * speed = speed_h (m/yr), vectors = velo_x/velo_y rotated to E/N;
  * colour maps / ranges: speed magma 0-400 m/yr; elevations terrain,
    auto (the field's own min-max); EVERY stress field seismic +-1000 kPa
    (the director asked for one fixed colour bar, -1000 to 1000 kPa, for the
    viscous and elastic fields alike — before that the viscous rows were
    baked in the SI's +-400 kPa). R2 objects are immutable, so the
    re-bake lives under a NEW prefix (FIELDS_DIR; fields_v2 = the +-1000 kPa
    bake, fields_v3 = the same with the ELASTIC post sigma cells baked as the
    superposed state sigma^V_pre + Delta sigma^E, hashes and contour included);
    the page's config/ch2Fields.ts names it.

Fields shown beyond the two overview figures, and where they come from:
  * sigma_n (both models) — SI Fig. S25 (thesis Fig. 2.A1) shows it for
    lake 2394; here for every lake, in its model's overview range;
  * sigma_rtheta, sigma_thetatheta (viscous) — PNAS Fig. 2B shows their
    differences for lake 2394 at +-400 kPa; here for every lake;
  * sigma_rr, sigma_rtheta, sigma_thetatheta (elastic) — the same netCDF
    variables of the elastic runs, in the elastic overview's +-1000 kPa;
  * observed speed / surface / bed under ELASTIC — the model inputs
    (observed speed is the viscous file's obs_speed: it is data, the same
    MEaSUREs grid; surface and bed are the elastic run's own geometry).

Inputs (local copies only — bash cinematic/fetch_sources.sh):
  cinematic/source_data/pnas_sims/*.nc + tile_attrs.json
  cinematic/source_data/data/labels_2019_volumes.geojson
  cinematic/source_data/manuscript_pnas/{thesis,main,si}/...

Outputs: cinematic/output/deeper/ch02/{fields_v3,figs,tex}/
  -> R2 addl/deeper/ch02/{fields_v3,figs,tex}/

Run (any checkout root, the cinematic venv):
  python cinematic/scene_addl/build_deeper_ch02.py fields [--lake 2511] [--model viscous] [--field st1_d]
  python cinematic/scene_addl/build_deeper_ch02.py figures
  python cinematic/scene_addl/build_deeper_ch02.py tex
then
  rclone copy cinematic/output/deeper/ch02/ r2:<bucket>/addl/deeper/ch02/ --checksum --header-upload 'Cache-Control: public, max-age=31536000, immutable'
  (and the same into website/.r2-cache/addl/deeper/ch02/ for dev)
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'cinematic'))
from shared import SOURCE_DATA, require_source  # noqa: E402

SIM_DIR = SOURCE_DATA / 'pnas_sims'
GEOJSON = SOURCE_DATA / 'data' / 'labels_2019_volumes.geojson'
MS = SOURCE_DATA / 'manuscript_pnas'
OUT = ROOT / 'cinematic' / 'output' / 'deeper' / 'ch02'
TS_OUT = ROOT / 'website' / 'src' / 'config' / 'ch2Fields.gen.ts'

# Old sim numbering <-> Dunmire id (+1523), in Dunmire order.
LAKES_OLD = [387, 428, 871, 888, 893, 988, 997]
OFFSET = 1523

# Thesis Table 2.1 (c_b, 10^6 Pa m^-1/3 s^1/3) and the SI elastic captions
# (P_w, x overburden) — shown as data labels in the viewer.
CB = {387: 5.4, 428: 6.5, 871: 8.5, 888: 8.5, 893: 7.5, 988: 8.6, 997: 6.7}
PW = {387: 1.0378, 428: 1.0276, 871: 1.0164, 888: 1.0306, 893: 1.0309, 988: 1.0298, 997: 1.0257}
# SI figure numbers of each lake's overviews (viscous S7-S13, elastic S14-S20;
# thesis 2.12-2.18 and 2.5-2.11).
SI_FIG = {old: (7 + i, 14 + i) for i, old in enumerate(LAKES_OLD)}
THESIS_FIG = {old: (12 + i, 5 + i) for i, old in enumerate(LAKES_OLD)}

# Drainage-class catalog, verbatim from the paper repo's georef.LAKE_CATEGORIES
# (same table as scene_ch02/build_sim_domains.py).
LAKE_CATEGORIES = {
    387: {'black': [], 'gray': [], 'cyan': [387], 'dashgray': [440], 'dashcyan': [], 'magenta': [372]},
    428: {'black': [415], 'gray': [], 'cyan': [428], 'dashgray': [], 'dashcyan': [], 'magenta': [420, 431, 997]},
    871: {'black': [], 'gray': [786, 777, 788, 773], 'cyan': [871, 760, 757, 771],
          'dashgray': [874, 870], 'dashcyan': [867, 758], 'magenta': []},
    888: {'black': [], 'gray': [], 'cyan': [888], 'dashgray': [], 'dashcyan': [879], 'magenta': [887, 884]},
    893: {'black': [], 'gray': [], 'cyan': [893, 875, 876, 891, 879], 'dashgray': [], 'dashcyan': [], 'magenta': [988]},
    988: {'black': [851], 'gray': [], 'cyan': [988, 875, 876, 891], 'dashgray': [859], 'dashcyan': [], 'magenta': [893]},
    997: {'black': [494, 492], 'gray': [], 'cyan': [997], 'dashgray': [], 'dashcyan': [], 'magenta': [428]},
}

MPA_TO_KPA = 1e3
OUT_PX = 1600          # field raster (square: the rotated tile's E/N bbox)
THUMB_PX = 144         # picker thumbnails
PANEL_IN = 4.2         # the SI's panel width in inches (line widths scale with it)
WEBP_Q = 86
HS_SMOOTH_CELLS = 3.0   # 75 m
HS_EXAG = 8.0
HS_GAIN = 0.6
HALF_M = 7375.0 + 12.5  # tile half-width incl. the half cell pcolormesh draws

# ── the fields ──────────────────────────────────────────────────────────────
# key: (row, case) — rows in the SI's order, then the extra stress rows.
STRESS_ROWS = ('st1', 'st2', 'sn', 'srr', 'srt', 'stt')
CASES = ('pre', 'post', 'd')
NC_POLAR = {'srr': 'sigma_rr', 'srt': 'sigma_rtheta', 'stt': 'sigma_thetatheta'}
# Overlays, as in the SI: hashes on the absolute sigma_t panels, the dashed
# +100 kPa contour on the sigma_t1 / sigma_t2 / sigma_rr rows.
HASH_ROWS = ('st1', 'st2')
CONTOUR_ROWS = ('st1', 'st2', 'srr')
CONTOUR_KPA = 100.0
VLIM = {'viscous': 1000.0, 'elastic': 1000.0}
# The field rasters' R2 prefix (immutable objects: a re-bake = a new name).
FIELDS_DIR = 'fields_v3'  # v3: the elastic POST sigma cells are the superposed state, baked with hashes
SPEED_MAX = 400.0


def field_keys(model: str) -> list[str]:
    keys = ['obs', 'zs', 'zb']
    if model == 'viscous':
        keys += [f'u_{c}' for c in CASES]
    keys += [f'{r}_{c}' for r in STRESS_ROWS for c in CASES]
    return keys


# ── geometry ────────────────────────────────────────────────────────────────

def lake_centroid_3413(new_num: int) -> tuple[float, float]:
    from pyproj import Transformer
    gj = _geojson()
    for f in gj['features']:
        if str(f['properties'].get('new_id', '')).lower() == f'cw2019_{new_num}':
            p = f['properties']
            t = Transformer.from_crs('EPSG:4326', 'EPSG:3413', always_xy=True)
            return t.transform(float(p['centroid_x']), float(p['centroid_y']))
    raise SystemExit(f'lake CW2019_{new_num} not in {GEOJSON}')


_GJ = None


def _geojson() -> dict:
    global _GJ
    if _GJ is None:
        _GJ = json.loads(require_source(GEOJSON).read_text())
    return _GJ


def lake_rings_3413(new_num: int) -> list[np.ndarray]:
    """Exterior rings of a lake polygon, EPSG:3413 metres."""
    from pyproj import Transformer
    t = Transformer.from_crs('EPSG:4326', 'EPSG:3413', always_xy=True)
    for f in _geojson()['features']:
        if str(f['properties'].get('new_id', '')).lower() == f'cw2019_{new_num}':
            g = f['geometry']
            polys = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
            out = []
            for p in polys:
                ring = np.asarray(p[0], dtype=float)
                e, n = t.transform(ring[:, 0], ring[:, 1])
                out.append(np.stack([e, n], axis=1))
            return out
    return []


class Frame:
    """The SI's map frame for one lake: EPSG:3413 km, the rotated tile and
    its axis-aligned bbox (= the SI panel's limits)."""

    def __init__(self, old: int, x: np.ndarray, y: np.ndarray):
        attrs = json.loads(require_source(SIM_DIR / 'tile_attrs.json').read_text())[f'2019cw{old}']
        self.theta = np.deg2rad(attrs['flow_angle_deg'])
        self.c, self.s = np.cos(self.theta), np.sin(self.theta)
        self.E0, self.N0 = lake_centroid_3413(old + OFFSET)
        self.x, self.y = x, y
        x0 = 0.5 * (x.min() + x.max())
        y0 = 0.5 * (y.min() + y.max())
        X, Y = np.meshgrid(x - x0, y - y0)
        self.E = self.E0 + X * self.c - Y * self.s
        self.N = self.N0 + X * self.s + Y * self.c
        corners = [(-HALF_M, -HALF_M), (HALF_M, -HALF_M), (HALF_M, HALF_M), (-HALF_M, HALF_M)]
        self.corners = [self.to_EN(cx, cy) for cx, cy in corners]
        es = [p[0] for p in self.corners]
        ns = [p[1] for p in self.corners]
        # The bbox of a rotated square is a square.
        self.Emin, self.Emax = min(es), max(es)
        self.Nmin, self.Nmax = min(ns), max(ns)
        self.W = self.Emax - self.Emin
        # Output pixel centres -> local tile coords.
        u = (np.arange(OUT_PX) + 0.5) / OUT_PX
        Eg = self.Emin + u * (self.Emax - self.Emin)
        Ng = self.Nmax - u * (self.Nmax - self.Nmin)
        Eg2, Ng2 = np.meshgrid(Eg, Ng)
        dE, dN = Eg2 - self.E0, Ng2 - self.N0
        self.lx = dE * self.c + dN * self.s
        self.ly = -dE * self.s + dN * self.c
        px_m = (self.Emax - self.Emin) / OUT_PX
        edge = HALF_M - np.maximum(np.abs(self.lx), np.abs(self.ly))
        self.alpha = np.clip(edge / px_m + 0.5, 0.0, 1.0)

    def to_EN(self, lx: float, ly: float) -> tuple[float, float]:
        return (self.E0 + lx * self.c - ly * self.s, self.N0 + lx * self.s + ly * self.c)

    def panel(self, E, N):
        """EPSG:3413 m -> panel km from the top-left corner (y down)."""
        return (np.asarray(E) - self.Emin) / 1e3, (self.Nmax - np.asarray(N)) / 1e3

    def sample(self, field: np.ndarray) -> np.ndarray:
        """Bilinear sample a (y, x) grid field at the output pixels."""
        x, y = self.x, self.y
        fx = np.clip((self.lx - x[0]) / (x[-1] - x[0]), 0, 1) * (len(x) - 1)
        fy = np.clip((self.ly - y[0]) / (y[-1] - y[0]), 0, 1) * (len(y) - 1)
        x0 = np.clip(np.floor(fx).astype(int), 0, len(x) - 2)
        y0 = np.clip(np.floor(fy).astype(int), 0, len(y) - 2)
        tx, ty = fx - x0, fy - y0
        return (field[y0, x0] * (1 - tx) * (1 - ty) + field[y0, x0 + 1] * tx * (1 - ty)
                + field[y0 + 1, x0] * (1 - tx) * ty + field[y0 + 1, x0 + 1] * tx * ty)

    def rotate_to_EN(self, ux, uy):
        return self.c * ux - self.s * uy, self.s * ux + self.c * uy


# ── stress recipes (stress_utils.py) ────────────────────────────────────────

def surface_basis(topo: np.ndarray, x: np.ndarray, y: np.ndarray):
    dx = float(x[1] - x[0])
    dy = float(y[1] - y[0])
    dh_dy, dh_dx = np.gradient(topo, dy, dx)
    inv = 1.0 / np.sqrt(1.0 + dh_dx ** 2 + dh_dy ** 2)
    n = np.stack([-dh_dx * inv, -dh_dy * inv, inv], axis=-1)
    seed = np.zeros_like(n)
    seed[..., 0] = 1.0
    e1 = seed - np.sum(seed * n, axis=-1, keepdims=True) * n
    e1 /= np.linalg.norm(e1, axis=-1, keepdims=True)
    e2 = np.cross(n, e1)
    return n, e1, e2


def tensor(ds, case: str, level: str = 'surf') -> np.ndarray:
    S = np.zeros(ds['sigma_xx'].sel(case=case, level=level).shape + (3, 3))
    g = lambda k: ds[k].sel(case=case, level=level).values.astype(np.float64) * MPA_TO_KPA  # noqa: E731
    S[..., 0, 0] = g('sigma_xx')
    S[..., 1, 1] = g('sigma_yy')
    S[..., 2, 2] = g('sigma_zz')
    S[..., 0, 1] = S[..., 1, 0] = g('sigma_xy')
    S[..., 1, 2] = S[..., 2, 1] = g('sigma_yz')
    S[..., 0, 2] = S[..., 2, 0] = g('sigma_xz')
    return S


def principals(S: np.ndarray, n, e1, e2):
    """sigma_t1, sigma_t2, sigma_n (kPa) and the sigma_t1 / sigma_t2 unit
    eigenvectors (lab frame) of the tangent-projected tensor."""
    q = lambda a, b: np.einsum('...i,...i->...', a, np.einsum('...ij,...j->...i', S, b))  # noqa: E731
    s11, s22, s12, sn = q(e1, e1), q(e2, e2), q(e1, e2), q(n, n)
    mean = 0.5 * (s11 + s22)
    rad = np.sqrt(np.maximum(0.0, 0.25 * (s11 - s22) ** 2 + s12 ** 2))
    th = 0.5 * np.arctan2(2.0 * s12, s11 - s22)
    c, s = np.cos(th)[..., None], np.sin(th)[..., None]
    v1 = c * e1 + s * e2
    v2 = -s * e1 + c * e2
    return mean + rad, mean - rad, sn, v1, v2


def model_fields(model: str, ds, dsv) -> dict:
    """{key: dict(data=(y,x) array, vec=(U,V)|None, vec_kind)} for one
    model. `ds` = the model's netCDF, `dsv` = the viscous one (obs speed)."""
    x, y = ds['x'].values, ds['y'].values
    post = 'patch' if model == 'viscous' else 'blister'
    topo = ds['topo_surf'].sel(case='nopatch', level='surf').values.astype(np.float64)
    n, e1, e2 = surface_basis(topo, x, y)
    out: dict = {}
    out['obs'] = dict(data=dsv['obs_speed'].sel(case='nopatch', level='surf').values)
    out['zs'] = dict(data=topo)
    out['zb'] = dict(data=ds['topo_bed'].sel(case='nopatch', level='surf').values)
    if model == 'viscous':
        sp = {c: ds['speed_h'].sel(case=k, level='surf').values for c, k in (('pre', 'nopatch'), ('post', post))}
        vx = {c: ds['velo_x'].sel(case=k, level='surf').values / 1000.0 for c, k in (('pre', 'nopatch'), ('post', post))}
        vy = {c: ds['velo_y'].sel(case=k, level='surf').values / 1000.0 for c, k in (('pre', 'nopatch'), ('post', post))}
        out['u_pre'] = dict(data=sp['pre'], vec=(vx['pre'], vy['pre']), vec_kind='velocity')
        out['u_post'] = dict(data=sp['post'], vec=(vx['post'], vy['post']), vec_kind='velocity')
        out['u_d'] = dict(data=sp['post'] - sp['pre'],
                          vec=(vx['post'] - vx['pre'], vy['post'] - vy['pre']), vec_kind='velocity')
    Spre, Spost = tensor(ds, 'nopatch'), tensor(ds, post)
    a = principals(Spre, n, e1, e2)
    if model == 'elastic':
        # The director asked why the elastic blister cells carried no hash
        # marks; the reason is physical: the elastic solve's own post-blister
        # field is not a stress state of the ice sheet (an elastic body loaded
        # by gravity from an unstressed state); the POST cells show the
        # SUPERPOSED state sigma^V_nopatch + (sigma^E_blister - sigma^E_nopatch),
        # Cauchy tensors added first, principals (and the hashes' directions)
        # after, in the viscous surface's basis -- the same state the talk's
        # POST . ELASTIC station paints (build_sim_superposed.py). Until now the
        # page re-projected the talk's drape in the browser, so these cells had
        # no hashes and no +100 kPa contour.
        assert np.allclose(dsv['x'].values, x) and np.allclose(dsv['y'].values, y), 'elastic/viscous grids differ'
        topov = dsv['topo_surf'].sel(case='nopatch', level='surf').values.astype(np.float64)
        nv, e1v, e2v = surface_basis(topov, x, y)
        Ssup = tensor(dsv, 'nopatch') + (Spost - Spre)
        b = principals(Ssup, nv, e1v, e2v)
    else:
        b = principals(Spost, n, e1, e2)
    d = principals(Spost - Spre, n, e1, e2)
    for i, row in enumerate(('st1', 'st2', 'sn')):
        for case, res in (('pre', a), ('post', b), ('d', d)):
            entry = dict(data=res[i])
            if row in HASH_ROWS and case != 'd':
                v = res[3] if row == 'st1' else res[4]
                entry['vec'] = (v[..., 0], v[..., 1])
                entry['vec_kind'] = 'hash'
            out[f'{row}_{case}'] = entry
    for row, var in NC_POLAR.items():
        p0 = ds[var].sel(case='nopatch', level='surf').values * MPA_TO_KPA
        p1 = ds[var].sel(case=post, level='surf').values * MPA_TO_KPA
        out[f'{row}_pre'] = dict(data=p0)
        out[f'{row}_post'] = dict(data=p1)
        out[f'{row}_d'] = dict(data=p1 - p0)
    return out


def field_style(model: str, key: str, data: np.ndarray) -> dict:
    row = key.split('_')[0]
    if key == 'obs' or row == 'u':
        return dict(cmap='magma', vmin=0.0, vmax=SPEED_MAX, units='m/yr')
    if key in ('zs', 'zb'):
        return dict(cmap='terrain', vmin=float(np.nanmin(data)), vmax=float(np.nanmax(data)), units='m')
    lim = VLIM[model]
    return dict(cmap='seismic', vmin=-lim, vmax=lim, units='kPa')


# ── rendering ───────────────────────────────────────────────────────────────

def hillshade(fr: Frame, topo: np.ndarray) -> np.ndarray:
    """0..1 shade of the model surface on the output grid (NW light, 45 deg).
    The netCDF surface carries the Elmer mesh's facets; a 75 m Gaussian
    takes them out so the shade reads as terrain, not triangles."""
    from scipy.ndimage import gaussian_filter
    z = fr.sample(gaussian_filter(topo, sigma=HS_SMOOTH_CELLS, mode='nearest'))
    px = (fr.Emax - fr.Emin) / OUT_PX
    gy, gx = np.gradient(z, px, px)  # row = north->south, col = west->east
    gy = -gy  # dz/dN
    az, alt = np.deg2rad(315.0), np.deg2rad(45.0)
    nx, ny = -gx * HS_EXAG, -gy * HS_EXAG
    norm = np.sqrt(nx ** 2 + ny ** 2 + 1.0)
    lx, ly, lz = np.cos(alt) * np.sin(az), np.cos(alt) * np.cos(az), np.sin(alt)
    hs = (nx * lx + ny * ly + lz) / norm
    return np.clip(hs, 0, 1)


def drape(rgb: np.ndarray, hs: np.ndarray) -> np.ndarray:
    """The field's colour lit by the surface: a gentle multiply around the
    flat-ground shade, so the colour still reads against the colour bar."""
    flat = np.sin(np.deg2rad(45.0))
    k = np.clip(1.0 + HS_GAIN * (hs - flat), 0.82, 1.12)
    return np.clip(rgb * k[..., None], 0, 1)


def render_field(fr: Frame, model: str, key: str, entry: dict, hs: np.ndarray,
                 dst: Path, thumb: Path) -> dict:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as pe
    from matplotlib import colormaps
    from PIL import Image

    data = entry['data']
    st = field_style(model, key, data)
    norm = np.clip((fr.sample(data) - st['vmin']) / (st['vmax'] - st['vmin']), 0, 1)
    rgb = colormaps[st['cmap']](norm)[..., :3]
    rgba = np.concatenate([drape(rgb, hs), fr.alpha[..., None]], axis=-1)

    Ek, Nk = fr.E / 1e3, fr.N / 1e3
    ext = [fr.Emin / 1e3, fr.Emax / 1e3, fr.Nmin / 1e3, fr.Nmax / 1e3]
    fig = plt.figure(figsize=(PANEL_IN, PANEL_IN), dpi=OUT_PX / PANEL_IN)
    fig.patch.set_alpha(0.0)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.patch.set_alpha(0.0)
    ax.imshow(rgba, extent=ext, origin='upper', interpolation='nearest', zorder=0)
    ax.set_xlim(ext[0], ext[1])
    ax.set_ylim(ext[2], ext[3])
    ax.set_aspect('equal')
    row = key.split('_')[0]

    if row in CONTOUR_ROWS:
        ax.contour(Ek, Nk, data, levels=[CONTOUR_KPA], colors='#333', linestyles='--',
                   linewidths=1.2, alpha=0.9, zorder=25)

    vec = entry.get('vec')
    if vec is not None and entry.get('vec_kind') == 'hash':
        # SI _stress_ticks: headless black sticks, every min(nx,ny)//15 cells.
        U, V = fr.rotate_to_EN(vec[0], vec[1])
        span = max(fr.W / 1e3, 1.0)
        step = max(1, min(len(fr.y), len(fr.x)) // 15)
        Es, Ns = Ek[::step, ::step], Nk[::step, ::step]
        Us, Vs = U[::step, ::step], V[::step, ::step]
        L = np.hypot(Us, Vs)
        Lcap = np.nanpercentile(L, 99.0)
        if not np.isfinite(Lcap) or Lcap <= 0:
            Lcap = np.nanmax(L) if np.nanmax(L) > 0 else 1.0
        sc = 0.04 * span / Lcap
        Up, Vp = Us * sc, Vs * sc
        tiny = L < 0.02 * Lcap
        Up[tiny] = 0.0
        Vp[tiny] = 0.0
        ax.quiver(Es, Ns, Up, Vp, angles='xy', scale_units='xy', scale=1.0, width=0.003,
                  color='k', alpha=0.95, headlength=0, headaxislength=0, minlength=0,
                  pivot='middle', zorder=35)
    elif vec is not None and entry.get('vec_kind') == 'velocity':
        # SI row 2: white vectors (km/yr, scale 0.3) with a black edge.
        U, V = fr.rotate_to_EN(vec[0], vec[1])
        step = max(1, min(U.shape) // 15)
        q = ax.quiver(Ek[::step, ::step], Nk[::step, ::step], U[::step, ::step], V[::step, ::step],
                      color='w', angles='xy', scale_units='xy', scale=0.3, width=0.004, zorder=6)
        q.set_path_effects([pe.Stroke(linewidth=1.2, foreground='k'), pe.Normal()])

    dst.parent.mkdir(parents=True, exist_ok=True)
    fig.canvas.draw()
    im = Image.fromarray(np.asarray(fig.canvas.buffer_rgba()).copy(), 'RGBA')
    plt.close(fig)
    if im.size != (OUT_PX, OUT_PX):
        im = im.resize((OUT_PX, OUT_PX), Image.LANCZOS)
    im.save(dst, 'WEBP', quality=WEBP_Q, method=4)
    im.resize((THUMB_PX, THUMB_PX), Image.LANCZOS).save(thumb, 'WEBP', quality=82, method=4)

    inside = (np.abs(fr.lx) <= HALF_M) & (np.abs(fr.ly) <= HALF_M)
    vals = fr.sample(data)[inside]
    info = dict(st)
    info['mean'] = round(float(np.nanmean(data)), 1)
    info['p'] = [round(float(np.nanpercentile(vals, q)), 1) for q in (0.3, 50, 99.7)]
    return info


def colorbar_ticks(vmin: float, vmax: float) -> list[float]:
    """The ticks matplotlib's colorbar would draw (the SI's)."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(PANEL_IN, PANEL_IN))
    ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])
    im = ax.imshow(np.array([[vmin, vmax]]), vmin=vmin, vmax=vmax)
    cb = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02, aspect=30, extend='both')
    fig.canvas.draw()
    t = [float(v) for v in cb.get_ticks() if vmin - 1e-9 <= v <= vmax + 1e-9]
    plt.close(fig)
    return t


def axis_ticks(fr: Frame) -> tuple[list[float], list[float]]:
    """x: MaxNLocator(5) as the SI; y: matplotlib's default locator."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    fig = plt.figure(figsize=(PANEL_IN, PANEL_IN))
    ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])
    ax.set_xlim(fr.Emin / 1e3, fr.Emax / 1e3)
    ax.set_ylim(fr.Nmin / 1e3, fr.Nmax / 1e3)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
    fig.canvas.draw()
    xt = [float(v) for v in ax.get_xticks() if fr.Emin / 1e3 <= v <= fr.Emax / 1e3]
    yt = [float(v) for v in ax.get_yticks() if fr.Nmin / 1e3 <= v <= fr.Nmax / 1e3]
    plt.close(fig)
    return xt, yt


# The page sets the lake numbers at this size (Ch2FieldPaper.vue: 23 units
# on a 700-unit map) — the placement below needs their extent in km.
LABEL_FONT_FRAC = 23.0 / 700.0
LABEL_PAD_M = 350.0


def lake_overlay(fr: Frame, old: int) -> list[dict]:
    """The SI's categorized lake outlines + numbers (overlays.draw_lakes):
    each number above its lake (350 m pad), kept inside the frame, lakes
    wholly outside it skipped; where a number would hit another number or
    another lake, it tries below, right, then left (the SI's collision
    solver, simplified). Panel km, y down; label = [x, baseline y, anchor]."""
    size = fr.W / 1e3
    fs = LABEL_FONT_FRAC * size
    cap = 0.73 * fs
    margin = 0.025 * size
    pad = LABEL_PAD_M / 1e3
    lakes = []
    for cls, ids in LAKE_CATEGORIES[old].items():
        for lid in ids:
            rings = lake_rings_3413(lid + OFFSET)
            if not rings:
                print(f'  WARN no polygon for CW2019_{lid + OFFSET}')
                continue
            main = max(rings, key=len)
            if (main[:, 0].max() < fr.Emin or main[:, 0].min() > fr.Emax
                    or main[:, 1].max() < fr.Nmin or main[:, 1].min() > fr.Nmax):
                continue
            prings = [np.stack(fr.panel(r[:, 0], r[:, 1]), axis=1) for r in rings]
            pm = max(prings, key=len)
            lakes.append(dict(num=lid + OFFSET, cls=cls, center=lid == old, prings=prings,
                              bbox=(pm[:, 0].min(), pm[:, 0].max(), pm[:, 1].min(), pm[:, 1].max())))

    def box(x, y, anchor, w):
        x0 = x - w / 2 if anchor == 'middle' else (x if anchor == 'start' else x - w)
        return (x0, x0 + w, y - cap, y)

    def hits(b, other):
        g = 0.08
        return not (b[1] + g < other[0] or b[0] - g > other[1] or b[3] + g < other[2] or b[2] - g > other[3])

    placed = []
    out = []
    for lk in lakes:
        x0, x1, y0, y1 = lk['bbox']
        cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        w = 0.64 * fs * len(str(lk['num']))
        cands = [
            (cx, y0 - pad, 'middle'),               # above (the SI's default)
            (cx, y1 + pad + cap, 'middle'),         # below
            (x1 + pad, cy + cap / 2, 'start'),      # right
            (x0 - pad, cy + cap / 2, 'end'),        # left
        ]
        best = None
        for x, y, a in cands:
            # keep it inside the frame
            if a == 'middle':
                x = float(np.clip(x, margin + w / 2, size - margin - w / 2))
            y = float(np.clip(y, margin + cap, size - margin))
            b = box(x, y, a, w)
            if b[0] < margin - 1e-6 or b[1] > size - margin + 1e-6:
                continue
            others = [p for p in placed] + [o['bbox'] for o in lakes if o is not lk]
            if not any(hits(b, o) for o in others):
                best = (x, y, a, b)
                break
            if best is None:
                best = (x, y, a, b)  # fall back to the first in-frame spot
        x, y, a, b = best
        placed.append(b)
        out.append(dict(
            num=lk['num'], cls=lk['cls'], center=lk['center'],
            rings=[[[round(float(px), 3), round(float(py), 3)] for px, py in r] for r in lk['prings']],
            label=[round(x, 3), round(y, 3), a],
        ))
    return out


def open_ncs(old: int):
    import xarray as xr
    e = require_source(SIM_DIR / f'elastic_2019cw{old}_d25km_r2500m_youngmod3.077e3_elastic_localh.nc')
    v = sorted(SIM_DIR.glob(f'2019cw{old}_d25km_r2500m_csi*_tsic_viscous.nc'))
    if not v:
        raise SystemExit(f'missing viscous nc for 2019cw{old} — run fetch_sources.sh')
    return xr.open_dataset(e), xr.open_dataset(v[0])


def bake_fields(only_lake: int | None, only_model: str | None, only_field: str | None) -> None:
    fdir = OUT / FIELDS_DIR
    fdir.mkdir(parents=True, exist_ok=True)
    tick_cache: dict = {}
    for old in LAKES_OLD:
        num = old + OFFSET
        if only_lake and only_lake != num:
            continue
        print(f'lake {num} (2019cw{old})')
        dse, dsv = open_ncs(old)
        fr = Frame(old, dsv['x'].values, dsv['y'].values)
        xt, yt = axis_ticks(fr)
        meta_path = fdir / f'lake_{num}.json'
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        meta.update({
            'num': num, 'sim': f'2019cw{old}', 'size_km': round(fr.W / 1e3, 4),
            'extent_km': [round(v / 1e3, 4) for v in (fr.Emin, fr.Emax, fr.Nmin, fr.Nmax)],
            'tile': [[round(float(a), 4), round(float(b), 4)] for a, b in
                     (fr.panel(E, N) for E, N in fr.corners)],
            'xticks': xt, 'yticks': yt,
            'lakes': lake_overlay(fr, old),
            'cb': CB[old], 'pw': PW[old],
            'si': {'viscous': SI_FIG[old][0], 'elastic': SI_FIG[old][1]},
            'thesis': {'viscous': THESIS_FIG[old][0], 'elastic': THESIS_FIG[old][1]},
        })
        meta.setdefault('fields', {})
        for model, ds in (('viscous', dsv), ('elastic', dse)):
            if only_model and only_model != model:
                continue
            fields = model_fields(model, ds, dsv)
            topo = ds['topo_surf'].sel(case='nopatch', level='surf').values.astype(np.float64)
            hs = hillshade(fr, topo)
            mf = meta['fields'].setdefault(model, {})
            for key in field_keys(model):
                if only_field and only_field != key:
                    continue
                name = f'{num}_{model[0]}_{key}'
                info = render_field(fr, model, key, fields[key], hs,
                                    fdir / f'{name}.webp', fdir / f'{name}_t.webp')
                tk = (round(info['vmin'], 3), round(info['vmax'], 3))
                if tk not in tick_cache:
                    tick_cache[tk] = colorbar_ticks(info['vmin'], info['vmax'])
                info['ticks'] = tick_cache[tk]
                info['vmin'] = round(info['vmin'], 2)
                info['vmax'] = round(info['vmax'], 2)
                mf[key] = info
                kb = (fdir / f'{name}.webp').stat().st_size / 1024
                print(f'  {model:8s} {key:7s} {info["cmap"]:8s} [{info["vmin"]:.0f}, {info["vmax"]:.0f}] '
                      f'mean {info["mean"]:8.1f}  p0.3/50/99.7 {info["p"]}  {kb:5.0f} kB')
        meta_path.write_text(json.dumps(meta, separators=(',', ':')))
        dse.close()
        dsv.close()
    write_cmaps_ts()


def bake_lakes_only() -> None:
    """Refresh only the lake outlines + numbers in every lake_<num>.json."""
    import xarray as xr
    for old in LAKES_OLD:
        num = old + OFFSET
        p = OUT / FIELDS_DIR / f'lake_{num}.json'
        meta = json.loads(p.read_text())
        v = sorted(SIM_DIR.glob(f'2019cw{old}_d25km_r2500m_csi*_tsic_viscous.nc'))[0]
        ds = xr.open_dataset(v)
        fr = Frame(old, ds['x'].values, ds['y'].values)
        ds.close()
        meta['lakes'] = lake_overlay(fr, old)
        p.write_text(json.dumps(meta, separators=(',', ':')))
        print(num, [(l['num'], l['label'][2]) for l in meta['lakes']])


def write_cmaps_ts() -> None:
    """The three colour maps as CSS stops for the page's colour bars."""
    from matplotlib import colormaps
    lines = [
        '// GENERATED by cinematic/scene_addl/build_deeper_ch02.py — do not edit.',
        '// The PNAS SI colour maps (matplotlib) as 33 CSS stops each, for the',
        '// Chapter 2 field viewer\'s colour bars.',
        '',
        'export const CH2_CMAPS: Record<\'magma\' | \'terrain\' | \'seismic\', string[]> = {',
    ]
    for name in ('magma', 'terrain', 'seismic'):
        cm = colormaps[name]
        stops = []
        for t in np.linspace(0, 1, 33):
            r, g, b, _ = cm(t)
            stops.append(f"'#{int(round(r * 255)):02x}{int(round(g * 255)):02x}{int(round(b * 255)):02x}'")
        lines.append(f'  {name}: [')
        for i in range(0, len(stops), 8):
            lines.append('    ' + ', '.join(stops[i:i + 8]) + ',')
        lines.append('  ],')
    lines.append('}')
    lines.append('')
    TS_OUT.write_text('\n'.join(lines))
    print(f'wrote {TS_OUT.relative_to(ROOT)}')


# ── static figures ──────────────────────────────────────────────────────────

WHITE = 245
MAX_W = 2000


def load_png(p: Path):
    from PIL import Image
    require_source(p)
    im = Image.open(p)
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA')
        bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    return im.convert('RGB')


def load_pdf(p: Path, dpi: int = 600):
    from PIL import Image
    require_source(p)
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(['pdftoppm', '-r', str(dpi), '-png', '-singlefile', str(p), f'{td}/page'],
                       check=True)
        return Image.open(f'{td}/page.png').convert('RGB')


def trim(im, pad_frac: float = 0.012):
    from PIL import Image
    a = np.asarray(im.convert('L'))
    ys, xs = np.where(a <= WHITE)
    im = im.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    pad = max(8, round(pad_frac * im.width))
    out = Image.new('RGB', (im.width + 2 * pad, im.height + 2 * pad), 'white')
    out.paste(im, (pad, pad))
    return out


def save_fig(im, name: str) -> tuple[int, int]:
    from PIL import Image
    im = trim(im)
    if im.width > MAX_W:
        im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
    d = OUT / 'figs'
    d.mkdir(parents=True, exist_ok=True)
    dst = d / f'{name}.webp'
    im.save(dst, 'WEBP', quality=90, method=6)
    print(f'{dst.name:44s} {im.width:5d} x {im.height:<5d} {dst.stat().st_size / 1024:7.0f} kB')
    return im.size


# name -> source (thesis figure files first: they are the dissertation's own;
# PNAS-only figures from the Overleaf zips).
TH = MS / 'thesis' / 'chapters' / 'chapter2' / 'ch2_figures'
SI = MS / 'si' / 'SI_Figures'
PN = MS / 'main'
FIGURES = {
    # stress spaces (thesis Figs. 2.20, 2.21 = SI Figs. S22, S21)
    'stress_space_elastic': TH / 'phasespace_elastic_mean_postdelta_postpre_localprincipals_localh_fixed.png',
    'stress_space_viscous': TH / 'phasespace_viscous_mean_postdelta_postpre_localprincipals.png',
    # the paper's main-text figures
    'pnas_fig1': PN / 'Fig1.png',
    'pnas_fig2': PN / 'Fig2.png',
    'pnas_fig3': PN / 'Fig3.png',
    'pnas_fig4': PN / 'Fig4.png',
    # (Fig. 5, the stress space, is in the talk itself — the block beat's
    # live panel — and its content is the top row of thesis Fig. 2.21.)
    # the thesis chapter's own setup / validation / appendix figures
    'center_lakes_map': TH / 'center_lakes_map.png',
    'blister': TH / 'blister_example_2019cw871.png',
    'ub_sensitivity': TH / 'patch_perturbation_vs_ub_2019cw871_localprincipals.png',
    'ssa_validation': TH / 'ssa_validation_R5000_H3000_a01_G01_err.png',
    'sigma_n': TH / 'sigmats_sigman_2019cw871_localh.png',
    'mesh_resolution': TH / 'sigmats_sigman_2019cw871_convergence_patch.png',
    # SI-only figures
    'si_s1_theory_error': SI / 'polar_stress_comparison_R5000_H3000_a01_G01_forpaper_unrotated_fractional_contours_ctitle.png',
    'si_s2_worldview_2280': SI / '2280_annotated_07052019.pdf',
    'si_s3_drainage_timing': SI / 'figS3.png',
    'si_s4_imagery': SI / 'figS4.png',
    'si_s5_temperature': SI / 'vertical_temp_rotation_zplot_2394.pdf',
    'si_s6_flow_rotation': SI / 'lake_2394_rotation_check_25.0km.pdf',
}


def bands(im, min_gap: int = 12) -> list:
    """Split a figure along its full-width white gutters (rows of paper)."""
    a = np.asarray(im.convert('L')) <= WHITE
    ink = a.any(axis=1)
    out, y, h = [], 0, len(ink)
    while y < h:
        while y < h and not ink[y]:
            y += 1
        y0 = y
        while y < h:
            if ink[y]:
                y += 1
                continue
            g = y
            while g < h and not ink[g]:
                g += 1
            if g - y >= min_gap or g >= h:
                break
            y = g
        if y > y0:
            out.append(im.crop((0, y0, im.width, y)))
    return out


def two_columns(im):
    """SI Fig. S6 is one tall column of five rows (a padded | rotated map
    pair each) with each row's colour bar in a column on the right: set
    rows 1-3 and 4-5 side by side under the title so it reads at one
    screen's height. The colour bars overhang the gaps between the map
    rows, so the maps and the bars are cut along their OWN white gutters
    and each row is re-joined to its own bar. Nothing is redrawn."""
    from PIL import Image
    a = np.asarray(im.convert('L')) <= WHITE
    col_ink = a.any(axis=0)
    # The widest white gutter in the right 40 %: between the rotated maps
    # and the colour-bar column.
    W = im.width
    best, x = (0, 0), int(0.6 * W)
    while x < W:
        if col_ink[x]:
            x += 1
            continue
        x0 = x
        while x < W and not col_ink[x]:
            x += 1
        if x - x0 > best[1] and x < W:
            best = (x0, x - x0)
    x_split = best[0] + best[1] // 2
    gap_px = max(12, im.height // 200)
    maps = bands(im.crop((0, 0, x_split, im.height)), min_gap=gap_px)
    bars = bands(im.crop((x_split, 0, W, im.height)), min_gap=gap_px)
    title, rows = maps[0], maps[1:]
    if len(rows) != 5 or len(bars) != 5:
        raise SystemExit(f'S6: expected 5 map rows and 5 bars, found {len(rows)} and {len(bars)}')
    joined = []
    for r, b in zip(rows, bars):
        h = max(r.height, b.height)
        j = Image.new('RGB', (r.width + b.width, h), 'white')
        j.paste(r, (0, (h - r.height) // 2))
        j.paste(b, (r.width, (h - b.height) // 2))
        joined.append(j)
    gap = joined[0].height // 14
    col_w = max(j.width for j in joined)
    col_h = lambda rs: sum(r.height for r in rs) + gap * (len(rs) - 1)  # noqa: E731
    H = title.height + gap + max(col_h(joined[:3]), col_h(joined[3:]))
    Wo = 2 * col_w + 3 * gap
    out = Image.new('RGB', (Wo, H), 'white')
    out.paste(title, ((Wo - title.width) // 2, 0))
    for c, rs in enumerate((joined[:3], joined[3:])):
        y = title.height + gap
        for r in rs:
            out.paste(r, (c * (col_w + 3 * gap), y))
            y += r.height + gap
    return out


# Figures re-set for the screen (see the function's note).
LAYOUT = {'si_s6_flow_rotation': two_columns}
PDF_DPI = {'si_s6_flow_rotation': 1200, 'si_s5_temperature': 900}


def bake_figures(only: str | None) -> None:
    sizes = {}
    for name, src in FIGURES.items():
        if only and only != name:
            continue
        im = load_pdf(src, PDF_DPI.get(name, 600)) if src.suffix == '.pdf' else load_png(src)
        if name in LAYOUT:
            im = LAYOUT[name](trim(im, 0.0))
        sizes[name] = save_fig(im, name)
    print(json.dumps({k: list(v) for k, v in sizes.items()}))


# ── LaTeX names ─────────────────────────────────────────────────────────────

TEX_INK = '1C1A17'
TEX_SYMBOLS = {
    'st1': r'\sigma_{t1}', 'st2': r'\sigma_{t2}', 'sn': r'\sigma_{n}',
    'srr': r'\sigma_{rr}', 'srt': r'\sigma_{r\theta}', 'stt': r'\sigma_{\theta\theta}',
    'u': r'|\mathbf{u}|',
}


def tex_names() -> dict:
    """name -> TeX (math mode). pre / post superscripts and the Delta of the
    tensor-first difference are the thesis's notation (Tables 2.2, 2.3)."""
    out = {
        'obs': r'|\mathbf{u}|^{\mathrm{obs}}',
        'zs': r'z_s',
        'zb': r'z_b',
    }
    for row, sym in TEX_SYMBOLS.items():
        out[f'{row}_pre'] = sym + r'^{\mathrm{pre}}'
        out[f'{row}_post'] = sym + r'^{\mathrm{post}}'
        out[f'{row}_d'] = r'\Delta' + sym
    return out


def bake_tex() -> None:
    texbin = '/Library/TeX/texbin'
    d = OUT / 'tex'
    d.mkdir(parents=True, exist_ok=True)
    env = {'PATH': f'{texbin}:/usr/bin:/bin'}
    boxes = {}
    with tempfile.TemporaryDirectory() as wd:
        for name, tex in tex_names().items():
            src = (
                '\\documentclass[preview,border=1pt]{standalone}\n'
                '\\usepackage{amsmath,amssymb}\\usepackage{xcolor}\n'
                f'\\definecolor{{ink}}{{HTML}}{{{TEX_INK}}}\n'
                f'\\begin{{document}}\\color{{ink}}${tex}$\\end{{document}}\n'
            )
            (Path(wd) / f'{name}.tex').write_text(src)
            r = subprocess.run(['latex', '-interaction=nonstopmode', f'{name}.tex'], cwd=wd,
                               env=env, capture_output=True, text=True)
            if r.returncode:
                raise SystemExit(r.stdout[-2000:])
            subprocess.run(['dvisvgm', '--no-fonts', '--exact-bbox', '-o', str(d / f'{name}.svg'),
                            f'{name}.dvi'], cwd=wd, env=env, check=True, capture_output=True)
            svg = (d / f'{name}.svg').read_text()
            vb = re.search(r"viewBox='([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)'", svg)
            boxes[name] = tuple(float(v) for v in vb.groups())
    # dvisvgm sets the glyphs on a baseline at y = 0 and crops to the ink.
    # Re-box every name to ONE top/bottom (the tallest ascent, the deepest
    # descent of the set) so they share a baseline at a fixed display height.
    pad = 0.6
    top = max(-b[1] for b in boxes.values()) + pad
    bot = max(b[1] + b[3] for b in boxes.values()) + pad
    for name, (x0, y0, w, h) in boxes.items():
        p = d / f'{name}.svg'
        svg = p.read_text()
        W, H = w + 2 * pad, top + bot
        svg = re.sub(r"width='[^']*' height='[^']*' viewBox='[^']*'",
                     f"width='{W:.4f}pt' height='{H:.4f}pt' viewBox='{x0 - pad:.4f} {-top:.4f} {W:.4f} {H:.4f}'",
                     svg, count=1)
        p.write_text(svg)
        print(f'{name:9s} {tex_names()[name]:40s} {W:6.2f} x {H:5.2f} bp')
    print(f'baseline at {top:.3f} bp of {top + bot:.3f}')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('part', choices=['fields', 'figures', 'tex', 'cmaps', 'lakes'])
    ap.add_argument('--lake', type=int)
    ap.add_argument('--model', choices=['viscous', 'elastic'])
    ap.add_argument('--field')
    ap.add_argument('--fig')
    a = ap.parse_args()
    if a.part == 'fields':
        bake_fields(a.lake, a.model, a.field)
    elif a.part == 'figures':
        bake_figures(a.fig)
    elif a.part == 'tex':
        bake_tex()
    elif a.part == 'lakes':
        bake_lakes_only()
    else:
        write_cmaps_ts()


if __name__ == '__main__':
    main()
