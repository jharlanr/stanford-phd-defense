"""Build the Ch.2 per-lake simulation-domain assets: for each of the
seven PNAS center lakes, the "drain the lake" beat carves the Elmer/Ice
model domain out of the Greenland object and paints the PUBLISHED
elastic blister response on it.

Per lake (new_id = old sim number + 1523):

  0. simbed_<new_id>_rg16.png — BED topography, RG-packed
     16-bit with frac = (bed_m − BED_OFF_M)/BED_SCALE_M (bed can sit
     below sea level, hence the offset); simstressv_<new_id>.png — the
     published VISCOUS response (patch − nopatch at t_sic), same
     recipe + colorbar as the elastic drape; simlake_<new_id>.png —
     the Dunmire lake ring rasterized in the tile frame (R = fill
     mask, G = outline mask) so the website can drape the lake
     over the surface DEM.
  1. simdem_<new_id>_rg16.png   — surface DEM of the 14.75 km analysis
     window (25 m grid from the processed sim netCDF), RG-packed 16-bit
     (u16 = elev/3500 m · 65535; R = hi byte, G = lo byte — same
     encoding/scale as shared/greenland_dem_rg16.png so the website
     shader math is shared). Alpha 0 outside the rotated domain.
  2. simstress_<new_id>.png     — Δσ_t1 drape: FIRST principal stress of
     the tangent-projected difference tensor (blister − nopatch) at the
     surface, exactly the published SI recipe (tensor-first difference,
     tangent basis from the nopatch surface normal), seismic colormap,
     symmetric ±VLIM_KPA. Alpha 0 outside the rotated domain.
  3. an entry in sim_domains.json — plate-carree bbox of both PNGs,
     rotated-domain corners (lon/lat), center, flow angle, vlim.

Later additions, per lake:

  4. sims2pre_<new_id>.jpg / sims2post_<new_id>.jpg — Sentinel-2
     TRUECOLOR of the domain window on the pre/post-drainage dates the
     paper uses (Fig. 1A / Fig. 4 / SI Fig. S4; recipe = bands 0..2 of
     the 30 km tstack reflectance / 1e4, clipped), sampled on the SAME
     plate-carree grid as the DEM/stress rasters so the website's tile
     shader can crossfade between all face layers with one uv.
  5. simlakes_<new_id>.json — every drainage-catalog lake of this
     center-lake group (georef.LAKE_CATEGORIES): class (cyan/gray/
     black/dashcyan/dashgray/magenta), polygon rings in bbox-uv
     coordinates (browser draws the outlines + hit-tests hovers), and
     per-lake stress stats (max/mean/min of tangent σ_t1/σ_t2, post-
     drainage AND Δ, both models) from the published in-polygon
     stress-array pickles.
  6. one shared phase_space.json — the Fig. 5 recipe verbatim: one
     point per (non-center, non-magenta, solid-class) lake, polygon
     MEAN of post-drainage σ_t{1,2} (x) and tensor-first Δσ_t{1,2}
     (y), for the viscous (Fig. 5) AND elastic (SI) models.

Inputs (local copies only — bash cinematic/fetch_sources.sh):
  cinematic/source_data/pnas_sims/elastic_2019cwNNN_*_elastic_localh.nc
  cinematic/source_data/pnas_sims/tile_attrs.json
  cinematic/source_data/pnas_s2/tstack_2019cwNNN.nc
  cinematic/source_data/pnas_lakestresses/stress_arrays_inside_lakes_*.pkl
  cinematic/source_data/data/labels_2019_volumes.geojson

Outputs: cinematic/scene_ch02/output_simdomains/ → R2 ch02/sim/

Run (defense checkout root):
  ./cinematic/.venv/bin/python -u cinematic/scene_ch02/build_sim_domains.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import xarray as xr
from PIL import Image
from matplotlib import colormaps
from pyproj import Transformer

sys.stdout.reconfigure(line_buffering=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared import SOURCE_DATA, require_source  # noqa: E402

SIM_DIR = SOURCE_DATA / 'pnas_sims'
S2_DIR = SOURCE_DATA / 'pnas_s2'
PKL_DIR = SOURCE_DATA / 'pnas_lakestresses'
GEOJSON = SOURCE_DATA / 'data' / 'labels_2019_volumes.geojson'
OUT_DIR = Path('cinematic/scene_ch02/output_simdomains')

# Old sim numbering ↔ Dunmire new_id (offset 1523), confirmed by the
# per-lake friction values in the paper's SI vs the sim filenames.
LAKES_OLD = [387, 428, 871, 888, 893, 988, 997]

# Pre/post-drainage Sentinel-2 dates, verbatim from the paper's figure
# scripts (making_pnas_figs: fig01 = 988, fig04 = 871/428/893, figS4 =
# 997/888/387).
S2_DATES = {
    387: ('2019-07-21', '2019-07-23'),
    428: ('2019-07-04', '2019-07-08'),
    871: ('2019-06-13', '2019-06-19'),
    888: ('2019-08-01', '2019-08-05'),
    893: ('2019-08-18', '2019-08-23'),
    988: ('2019-08-18', '2019-08-23'),
    997: ('2019-07-04', '2019-07-08'),
}
S2_JPEG_Q = 90

# Drainage-mechanism catalog for the 7 published center-lake groups —
# verbatim from the paper repo's georef.LAKE_CATEGORIES (internal old
# sim ids; display id = old + 1523). Classes match the Fig. 1 legend:
#   cyan = englacial · gray = lateral · black = none ·
#   dashcyan = englacial, much later than the center lake ·
#   dashgray = lateral, may also be englacial ·
#   magenta = same-day englacial (excluded from the Fig. 5 phase space)
LAKE_CATEGORIES = {
    387: {'black': [], 'gray': [], 'cyan': [387],
          'dashgray': [440], 'dashcyan': [], 'magenta': [372]},
    428: {'black': [415], 'gray': [], 'cyan': [428],
          'dashgray': [], 'dashcyan': [], 'magenta': [420, 431, 997]},
    871: {'black': [], 'gray': [786, 777, 788, 773], 'cyan': [871, 760, 757, 771],
          'dashgray': [874, 870], 'dashcyan': [867, 758], 'magenta': []},
    888: {'black': [], 'gray': [], 'cyan': [888],
          'dashgray': [], 'dashcyan': [879], 'magenta': [887, 884]},
    893: {'black': [], 'gray': [], 'cyan': [893, 875, 876, 891, 879],
          'dashgray': [], 'dashcyan': [], 'magenta': [988]},
    988: {'black': [851], 'gray': [], 'cyan': [988, 875, 876, 891],
          'dashgray': [859], 'dashcyan': [], 'magenta': [893]},
    997: {'black': [494, 492], 'gray': [], 'cyan': [997],
          'dashgray': [], 'dashcyan': [], 'magenta': [428]},
}
# Fig. 5 phase space: solid classes only, center + same-day excluded.
PHASE_CLASSES = ('black', 'gray', 'cyan')

VLIM_KPA = 1000.0       # shared symmetric range = ±1 MPa (elastic AND viscous)
DEM_MAX_M = 3500.0      # same normalization as the site's global DEM
BED_OFF_M = -1000.0     # bed RG16 encoding: frac = (bed − off) / scale
BED_SCALE_M = 4500.0
LAKE_OUTLINE_PX = 5     # outline stroke width in tile pixels
OUT_PX = 1024           # output raster size (supersamples the 25 m grid)
MARGIN_FRAC = 0.02      # bbox margin around the rotated square
MPA_TO_KPA = 1e3

T4326_3413 = Transformer.from_crs('EPSG:4326', 'EPSG:3413', always_xy=True)
T3413_4326 = Transformer.from_crs('EPSG:3413', 'EPSG:4326', always_xy=True)


def tangent_sigma_t1_diff(ds: xr.Dataset, patch_case: str = 'blister') -> np.ndarray:
    """Published SI recipe: component-difference the Cauchy tensor
    (patch − nopatch) at the surface, project into the tangent plane
    of the (shared) nopatch surface, take the most-tensile in-plane
    principal. Returns kPa, tension positive, on the (y, x) grid.
    patch_case: 'blister' (elastic files) or 'patch' (viscous files)."""
    surf = {}
    for k in ('sigma_xx', 'sigma_yy', 'sigma_zz', 'sigma_xy', 'sigma_xz', 'sigma_yz'):
        v = ds[k].sel(level='surf')
        surf[k] = v.sel(case=patch_case).values - v.sel(case='nopatch').values

    topo = ds['topo_surf'].sel(level='surf', case='nopatch').values
    x = ds['x'].values
    y = ds['y'].values
    hy, hx = np.gradient(topo, y, x)  # d/dy, d/dx (row = y, col = x)

    # Surface normal (unnormalized): (-hx, -hy, 1).
    n = np.stack([-hx, -hy, np.ones_like(hx)], axis=0)
    n /= np.linalg.norm(n, axis=0, keepdims=True)
    # Tangent basis: e1 = x̂ − (x̂·n)n (Gram–Schmidt), e2 = n × e1.
    xhat = np.zeros_like(n)
    xhat[0] = 1.0
    e1 = xhat - (xhat * n).sum(axis=0, keepdims=True) * n
    e1 /= np.linalg.norm(e1, axis=0, keepdims=True)
    e2 = np.cross(n, e1, axis=0)

    def T_dot(v: np.ndarray) -> np.ndarray:
        """ΔT · v for the symmetric tensor stored in `surf`."""
        return np.stack([
            surf['sigma_xx'] * v[0] + surf['sigma_xy'] * v[1] + surf['sigma_xz'] * v[2],
            surf['sigma_xy'] * v[0] + surf['sigma_yy'] * v[1] + surf['sigma_yz'] * v[2],
            surf['sigma_xz'] * v[0] + surf['sigma_yz'] * v[1] + surf['sigma_zz'] * v[2],
        ], axis=0)

    t11 = (e1 * T_dot(e1)).sum(axis=0)
    t22 = (e2 * T_dot(e2)).sum(axis=0)
    t12 = (e1 * T_dot(e2)).sum(axis=0)
    mean = 0.5 * (t11 + t22)
    rad = np.sqrt((0.5 * (t11 - t22)) ** 2 + t12 ** 2)
    return (mean + rad) * MPA_TO_KPA


def tangent_sigma_t1_abs(ds: xr.Dataset, case: str) -> np.ndarray:
    """The same tangent-plane projection applied to ONE case's
    absolute surface Cauchy tensor (no patch, or with patch/blister) —
    the fields the difference is made of. kPa, tension positive."""
    surf = {k: ds[k].sel(level='surf', case=case).values
            for k in ('sigma_xx', 'sigma_yy', 'sigma_zz', 'sigma_xy', 'sigma_xz', 'sigma_yz')}
    topo = ds['topo_surf'].sel(level='surf', case='nopatch').values
    x = ds['x'].values
    y = ds['y'].values
    hy, hx = np.gradient(topo, y, x)
    n = np.stack([-hx, -hy, np.ones_like(hx)], axis=0)
    n /= np.linalg.norm(n, axis=0, keepdims=True)
    xhat = np.zeros_like(n)
    xhat[0] = 1.0
    e1 = xhat - (xhat * n).sum(axis=0, keepdims=True) * n
    e1 /= np.linalg.norm(e1, axis=0, keepdims=True)
    e2 = np.cross(n, e1, axis=0)

    def T_dot(v: np.ndarray) -> np.ndarray:
        return np.stack([
            surf['sigma_xx'] * v[0] + surf['sigma_xy'] * v[1] + surf['sigma_xz'] * v[2],
            surf['sigma_xy'] * v[0] + surf['sigma_yy'] * v[1] + surf['sigma_yz'] * v[2],
            surf['sigma_xz'] * v[0] + surf['sigma_yz'] * v[1] + surf['sigma_zz'] * v[2],
        ], axis=0)

    t11 = (e1 * T_dot(e1)).sum(axis=0)
    t22 = (e2 * T_dot(e2)).sum(axis=0)
    t12 = (e1 * T_dot(e2)).sum(axis=0)
    mean = 0.5 * (t11 + t22)
    rad = np.sqrt((0.5 * (t11 - t22)) ** 2 + t12 ** 2)
    return (mean + rad) * MPA_TO_KPA


# The four absolute drapes per lake: (meta key, file tag, model file, case).
FIELD_DRAPES = (
    ('stress_e_nopatch', 'e_nopatch', 'elastic', 'nopatch'),
    ('stress_e_patch', 'e_patch', 'elastic', 'blister'),
    ('stress_v_nopatch', 'v_nopatch', 'viscous', 'nopatch'),
    ('stress_v_patch', 'v_patch', 'viscous', 'patch'),
)


def open_lake_ncs(old_n: int) -> tuple:
    nc = require_source(
        SIM_DIR / f'elastic_2019cw{old_n}_d25km_r2500m_youngmod3.077e3_elastic_localh.nc'
    )
    visc_matches = sorted(SIM_DIR.glob(
        f'2019cw{old_n}_d25km_r2500m_csi*_tsic_viscous.nc'))
    if not visc_matches:
        raise SystemExit(f'missing viscous nc for 2019cw{old_n} — run fetch_sources.sh')
    return xr.open_dataset(nc), xr.open_dataset(visc_matches[0])


def write_field_drapes(meta: dict, ds: xr.Dataset, dsv: xr.Dataset) -> dict:
    """The absolute no-patch / with-patch σ_t1 drapes for both
    models, on the lake's plate-carree tile grid (rebuilt from the
    lake's own meta so `--fields-only` reproduces build_lake's frame
    exactly), seismic ±VLIM_KPA. Returns the meta keys to add."""
    new_id = meta['id']
    b = meta['bbox']
    e0, n0 = T4326_3413.transform(meta['lon'], meta['lat'])
    th = np.deg2rad(meta['flow_angle_deg'])
    cos_t, sin_t = np.cos(th), np.sin(th)
    glon = np.linspace(b['lon_w'], b['lon_e'], OUT_PX)
    glat = np.linspace(b['lat_n'], b['lat_s'], OUT_PX)
    glon2, glat2 = np.meshgrid(glon, glat)
    ge, gn = T4326_3413.transform(glon2, glat2)
    lx = (ge - e0) * cos_t + (gn - n0) * sin_t
    ly = -(ge - e0) * sin_t + (gn - n0) * cos_t
    half_m = meta['domain_half_km'] * 1e3
    alpha = (((np.abs(lx) <= half_m) & (np.abs(ly) <= half_m)) * 255).astype(np.uint8)
    x = ds['x'].values
    y = ds['y'].values

    def sample(field: np.ndarray) -> np.ndarray:
        fx = np.clip((lx - x[0]) / (x[-1] - x[0]), 0, 1) * (len(x) - 1)
        fy = np.clip((ly - y[0]) / (y[-1] - y[0]), 0, 1) * (len(y) - 1)
        x0 = np.clip(np.floor(fx).astype(int), 0, len(x) - 2)
        y0 = np.clip(np.floor(fy).astype(int), 0, len(y) - 2)
        tx = fx - x0
        ty = fy - y0
        return (field[y0, x0] * (1 - tx) * (1 - ty) + field[y0, x0 + 1] * tx * (1 - ty)
                + field[y0 + 1, x0] * (1 - tx) * ty + field[y0 + 1, x0 + 1] * tx * ty)

    keys = {}
    for key, tag, model, case in FIELD_DRAPES:
        field = tangent_sigma_t1_abs(ds if model == 'elastic' else dsv, case)
        norm = np.clip((sample(field) + VLIM_KPA) / (2 * VLIM_KPA), 0, 1)
        rgba = (colormaps['seismic'](norm) * 255).astype(np.uint8)
        rgba[..., 3] = alpha
        fname = f'simstress_{tag}_{new_id}.png'
        Image.fromarray(rgba).save(OUT_DIR / fname, optimize=True)
        keys[key] = fname
        print(f'  {tag}: σ_t1 p99.7 {np.nanpercentile(np.abs(field), 99.7):.0f} kPa → {fname}')
    return keys


_GEO_RINGS = None


def geojson_rings() -> dict:
    """{old_id: [exterior ring [(lon, lat), ...], ...]} for every CW2019
    lake in the Dunmire-derived inventory."""
    global _GEO_RINGS
    if _GEO_RINGS is None:
        gj = json.loads(require_source(GEOJSON).read_text())
        out = {}
        for f in gj['features']:
            nid = str(f['properties'].get('new_id', ''))
            if not nid.upper().startswith('CW2019_'):
                continue
            old = int(nid.split('_')[1]) - 1523
            geom = f['geometry']
            polys = ([geom['coordinates']] if geom['type'] == 'Polygon'
                     else geom['coordinates'] if geom['type'] == 'MultiPolygon'
                     else [])
            out[old] = [p[0] for p in polys if p and len(p[0]) >= 4]
        _GEO_RINGS = out
    return _GEO_RINGS


def sample_grid(field: np.ndarray, gx: np.ndarray, gy: np.ndarray,
                qx: np.ndarray, qy: np.ndarray) -> np.ndarray:
    """Bilinear sample field[y, x] (monotonic coords, either direction)
    at query points, edge-clamped."""
    fx = np.clip((qx - gx[0]) / (gx[-1] - gx[0]), 0, 1) * (len(gx) - 1)
    fy = np.clip((qy - gy[0]) / (gy[-1] - gy[0]), 0, 1) * (len(gy) - 1)
    x0 = np.clip(np.floor(fx).astype(int), 0, len(gx) - 2)
    y0 = np.clip(np.floor(fy).astype(int), 0, len(gy) - 2)
    tx = fx - x0
    ty = fy - y0
    return (field[y0, x0] * (1 - tx) * (1 - ty)
            + field[y0, x0 + 1] * tx * (1 - ty)
            + field[y0 + 1, x0] * (1 - tx) * ty
            + field[y0 + 1, x0 + 1] * tx * ty)


def build_s2_faces(old_n: int, new_id: str, glon2: np.ndarray,
                   glat2: np.ndarray, inside: np.ndarray) -> dict | None:
    """Sentinel-2 truecolor block faces on the shared plate-carree grid.
    Paper recipe (make_fig01_v2.s2_rgb): reflectance bands 0..2 / 1e4,
    clipped to [0, 1], NaN → white."""
    tstack = S2_DIR / f'tstack_2019cw{old_n}.nc'
    if not tstack.exists():
        print(f'  WARN no tstack for 2019cw{old_n} — skipping S2 faces')
        return None
    date_pre, date_post = S2_DATES[old_n]
    ds = xr.open_dataset(tstack)
    t32622 = Transformer.from_crs('EPSG:4326', ds.attrs.get('proj:code', 'EPSG:32622'),
                                  always_xy=True)
    qe, qn = t32622.transform(glon2, glat2)
    sx = ds['x'].values
    sy = ds['y'].values
    out = {}
    for tag, date in (('pre', date_pre), ('post', date_post)):
        try:
            da = ds['reflectance'].sel(time=date)
        except KeyError:
            da = ds['reflectance'].sel(time=date, method='nearest')
            print(f'  WARN {date} not in tstack — using nearest '
                  f'{str(da.time.values)[:10]}')
        rgb = np.empty((*glon2.shape, 3), dtype=np.uint8)
        for b in range(3):
            band = np.nan_to_num(da.isel(band=b).values / 1e4, nan=1.0)
            samp = sample_grid(band, sx, sy, qe, qn)
            rgb[..., b] = (np.clip(samp, 0, 1) * 255).astype(np.uint8)
        rgb[~inside] = 255
        fname = f'sims2{tag}_{new_id}.jpg'
        Image.fromarray(rgb).save(OUT_DIR / fname, quality=S2_JPEG_Q, optimize=True)
        out[f's2_{tag}'] = fname
        out[f'date_{tag}'] = date
    ds.close()
    print(f'  S2 faces: {date_pre} → {date_post}')
    return out


def _stats(arr) -> dict:
    a = np.asarray(arr, dtype=float)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return {'max': None, 'min': None, 'mean': None}
    return {'max': round(float(np.max(a)), 1),
            'min': round(float(np.min(a)), 1),
            'mean': round(float(np.mean(a)), 1)}


def lake_stress_tables(old_n: int) -> dict:
    """{cw: {'elastic': {...}, 'viscous': {...}, 'n_points': int}} from
    the published in-polygon stress-array pickles. Each model carries
    max/mean/min of tangent-plane σ_t1/σ_t2, post-drainage and Δ."""
    import pandas as pd
    visc = sorted(PKL_DIR.glob(
        f'stress_arrays_inside_lakes_2019cw{old_n}_*_tsic_viscous.pkl'))
    elas = sorted(PKL_DIR.glob(
        f'stress_arrays_inside_lakes_elastic_2019cw{old_n}_*_elastic_localh.pkl'))
    if not visc or not elas:
        raise SystemExit(f'missing lakestress pickles for 2019cw{old_n} — run fetch_sources.sh')
    out = {}
    for model, fp in (('viscous', visc[0]), ('elastic', elas[0])):
        df = pd.read_pickle(fp)
        for _, r in df.iterrows():
            cw = int(r['lakenum_cw'])
            e = out.setdefault(cw, {'n_points': int(r['n_points'])})
            e[model] = {
                's1_post': _stats(r['sigma1_p_kPa']),
                's2_post': _stats(r['sigma2_p_kPa']),
                's1_diff': _stats(r['sigma1_diff_kPa']),
                's2_diff': _stats(r['sigma2_diff_kPa']),
            }
    return out


def lake_class(old_n: int, cw: int) -> str | None:
    """First matching class in the Fig-5 precedence order, then the
    dashed (uncertain) classes."""
    cats = LAKE_CATEGORIES[old_n]
    for cls in ('black', 'gray', 'cyan', 'magenta', 'dashgray', 'dashcyan'):
        if cw in cats.get(cls, []):
            return cls
    return None


def build_lake(old_n: int, attrs: dict, ring: list) -> dict:
    new_id = attrs['new_id']
    print(f'{new_id} (2019cw{old_n}):')
    ds, dsv = open_lake_ncs(old_n)

    sig_t1_kpa = tangent_sigma_t1_diff(ds, 'blister')
    sig_t1v_kpa = tangent_sigma_t1_diff(dsv, 'patch')
    topo = ds['topo_surf'].sel(level='surf', case='nopatch').values
    bed = ds['topo_bed'].sel(level='surf', case='nopatch').values
    x = ds['x'].values
    y = ds['y'].values
    half_m = float(min(x.max(), y.max()))  # 7375 m
    p997 = float(np.nanpercentile(np.abs(sig_t1_kpa), 99.7))
    p997v = float(np.nanpercentile(np.abs(sig_t1v_kpa), 99.7))
    print(f'  Δσ_t1 p99.7 = {p997:.0f} kPa elastic / {p997v:.0f} kPa viscous '
          f'(both draped at ±{VLIM_KPA:.0f})')

    # Georeference: local rotated frame → EPSG:3413 → lon/lat.
    e0, n0 = T4326_3413.transform(attrs['lon'], attrs['lat'])
    ext_cx = (attrs['extent_xmin'] + attrs['extent_xmax']) / 2
    ext_cy = (attrs['extent_ymin'] + attrs['extent_ymax']) / 2
    if abs(e0 - ext_cx) > 300 or abs(n0 - ext_cy) > 300:
        print(f'  WARN centroid vs tile-extent center off by '
              f'({e0 - ext_cx:.0f}, {n0 - ext_cy:.0f}) m')
    th = np.deg2rad(attrs['flow_angle_deg'])
    cos_t, sin_t = np.cos(th), np.sin(th)

    # Rotated-square corners → lon/lat (for the meta + bbox).
    corners_local = [(-half_m, -half_m), (half_m, -half_m),
                     (half_m, half_m), (-half_m, half_m)]
    corners_en = [(e0 + cx * cos_t - cy * sin_t, n0 + cx * sin_t + cy * cos_t)
                  for cx, cy in corners_local]
    corners_ll = [T3413_4326.transform(e, n) for e, n in corners_en]
    lons = [c[0] for c in corners_ll]
    lats = [c[1] for c in corners_ll]
    dlon = (max(lons) - min(lons)) * MARGIN_FRAC
    dlat = (max(lats) - min(lats)) * MARGIN_FRAC
    lon_w, lon_e = min(lons) - dlon, max(lons) + dlon
    lat_s, lat_n = min(lats) - dlat, max(lats) + dlat

    # Target plate-carree grid → local coords (inverse rotation).
    glon = np.linspace(lon_w, lon_e, OUT_PX)
    glat = np.linspace(lat_n, lat_s, OUT_PX)  # row 0 = north (image top)
    glon2, glat2 = np.meshgrid(glon, glat)
    ge, gn = T4326_3413.transform(glon2, glat2)
    lx = (ge - e0) * cos_t + (gn - n0) * sin_t
    ly = -(ge - e0) * sin_t + (gn - n0) * cos_t
    inside = (np.abs(lx) <= half_m) & (np.abs(ly) <= half_m)

    # Bilinear sample helper on the (y, x) grid, coords CLAMPED so DEM
    # displacement stays continuous at the alpha edge.
    def sample(field: np.ndarray) -> np.ndarray:
        fx = np.clip((lx - x[0]) / (x[-1] - x[0]), 0, 1) * (len(x) - 1)
        fy = np.clip((ly - y[0]) / (y[-1] - y[0]), 0, 1) * (len(y) - 1)
        x0 = np.clip(np.floor(fx).astype(int), 0, len(x) - 2)
        y0 = np.clip(np.floor(fy).astype(int), 0, len(y) - 2)
        tx = fx - x0
        ty = fy - y0
        f00 = field[y0, x0]
        f10 = field[y0, x0 + 1]
        f01 = field[y0 + 1, x0]
        f11 = field[y0 + 1, x0 + 1]
        return (f00 * (1 - tx) * (1 - ty) + f10 * tx * (1 - ty)
                + f01 * (1 - tx) * ty + f11 * tx * ty)

    alpha = (inside * 255).astype(np.uint8)

    # DEM (RG16).
    dem = sample(topo)
    u16 = np.clip(dem / DEM_MAX_M, 0, 1) * 65535
    u16 = u16.astype(np.uint32)
    dem_rgba = np.zeros((OUT_PX, OUT_PX, 4), dtype=np.uint8)
    dem_rgba[..., 0] = (u16 >> 8).astype(np.uint8)
    dem_rgba[..., 1] = (u16 & 255).astype(np.uint8)
    dem_rgba[..., 3] = alpha
    Image.fromarray(dem_rgba).save(OUT_DIR / f'simdem_{new_id}_rg16.png', optimize=True)

    # Stress drapes (seismic, shared ±VLIM = ±1 MPa): elastic + viscous.
    for field, fname in ((sig_t1_kpa, f'simstress_{new_id}.png'),
                         (sig_t1v_kpa, f'simstressv_{new_id}.png')):
        stress = sample(field)
        norm = np.clip((stress + VLIM_KPA) / (2 * VLIM_KPA), 0, 1)
        rgba = (colormaps['seismic'](norm) * 255).astype(np.uint8)
        rgba[..., 3] = alpha
        Image.fromarray(rgba).save(OUT_DIR / fname, optimize=True)

    # Bed DEM (RG16, offset encoding — bed can sit below sea level).
    bed_s = sample(bed)
    b16 = np.clip((bed_s - BED_OFF_M) / BED_SCALE_M, 0, 1) * 65535
    b16 = b16.astype(np.uint32)
    bed_rgba = np.zeros((OUT_PX, OUT_PX, 4), dtype=np.uint8)
    bed_rgba[..., 0] = (b16 >> 8).astype(np.uint8)
    bed_rgba[..., 1] = (b16 & 255).astype(np.uint8)
    bed_rgba[..., 3] = alpha
    Image.fromarray(bed_rgba).save(OUT_DIR / f'simbed_{new_id}_rg16.png', optimize=True)

    # Lake mask in the tile frame: R = fill, G = outline (2× supersampled
    # for smooth edges). Row 0 = north, same as the DEM/stress grids.
    from PIL import ImageDraw
    ss = 2
    px_ring = [((lon - lon_w) / (lon_e - lon_w) * OUT_PX * ss,
                (lat_n - lat) / (lat_n - lat_s) * OUT_PX * ss)
               for lon, lat in ring]
    fill_im = Image.new('L', (OUT_PX * ss, OUT_PX * ss), 0)
    ImageDraw.Draw(fill_im).polygon(px_ring, fill=255)
    line_im = Image.new('L', (OUT_PX * ss, OUT_PX * ss), 0)
    ImageDraw.Draw(line_im).line(px_ring + [px_ring[0]], fill=255,
                                 width=LAKE_OUTLINE_PX * ss, joint='curve')
    fill_a = np.asarray(fill_im.resize((OUT_PX, OUT_PX), Image.LANCZOS))
    line_a = np.asarray(line_im.resize((OUT_PX, OUT_PX), Image.LANCZOS))
    lake_rgba = np.zeros((OUT_PX, OUT_PX, 4), dtype=np.uint8)
    lake_rgba[..., 0] = fill_a
    lake_rgba[..., 1] = line_a
    lake_rgba[..., 3] = np.maximum(fill_a, line_a)
    Image.fromarray(lake_rgba).save(OUT_DIR / f'simlake_{new_id}.png', optimize=True)

    # Surface elevation at the domain center — the website aims its
    # telephoto drain framing at the DISPLACED surface, so it needs
    # this number without a DEM readback.
    iy = int(np.argmin(np.abs(y)))
    ix = int(np.argmin(np.abs(x)))
    center_surf_m = float(topo[iy, ix])
    bed_min_m = float(np.nanmin(bed))
    bed_max_m = float(np.nanmax(bed))

    # ── Sentinel-2 pre/post block faces (same grid) ──
    s2_meta = build_s2_faces(old_n, new_id, glon2, glat2, inside) or {}

    # ── drainage-catalog lakes — outlines + stress tables ──
    def to_uv(lon: float, lat: float) -> list:
        return [round((lon - lon_w) / (lon_e - lon_w), 4),
                round((lat_n - lat) / (lat_n - lat_s), 4)]

    rings_all = geojson_rings()
    tables = lake_stress_tables(old_n)
    catalog = []
    phase_pts = []
    listed = sorted({cw for cls in LAKE_CATEGORIES[old_n].values() for cw in cls})
    for cw in listed:
        cls = lake_class(old_n, cw)
        cw_rings = rings_all.get(cw)
        if cls is None or not cw_rings:
            print(f'  WARN lake {cw}: cls={cls} rings={bool(cw_rings)} — skipped')
            continue
        rings_uv = [[to_uv(lon, lat) for lon, lat in r] for r in cw_rings]
        main_ring = max(cw_rings, key=len)
        c_lon = float(np.mean([p[0] for p in main_ring]))
        c_lat = float(np.mean([p[1] for p in main_ring]))
        tab = tables.get(cw)
        if tab is None:
            print(f'  WARN lake {cw}: no stress arrays in pickles — outline only')
        in_phase = cls in PHASE_CLASSES and cw != old_n
        catalog.append({
            'cw': cw,
            'id': f'CW2019_{cw + 1523}',
            'num': cw + 1523,
            'cls': cls,
            'center': cw == old_n,
            'phase': in_phase and tab is not None,
            'rings_uv': rings_uv,
            'centroid_uv': to_uv(c_lon, c_lat),
            'centroid_ll': [round(c_lon, 5), round(c_lat, 5)],
            'stats': tab,
        })
        if in_phase and tab is not None:
            for model in ('viscous', 'elastic'):
                m = tab[model]
                phase_pts.append({
                    'model': model,
                    'center': old_n + 1523,
                    'num': cw + 1523,
                    'group': cls,
                    'x1': m['s1_post']['mean'], 'y1': m['s1_diff']['mean'],
                    'x2': m['s2_post']['mean'], 'y2': m['s2_diff']['mean'],
                })
    lakes_fname = f'simlakes_{new_id}.json'
    (OUT_DIR / lakes_fname).write_text(json.dumps(
        {'center': new_id, 'center_cw': old_n, 'lakes': catalog},
        separators=(',', ':')))
    print(f'  catalog: {len(catalog)} lakes, {len(phase_pts) // 2} phase points')

    meta = {
        'id': new_id,
        'old_id': f'2019cw{old_n}',
        'lon': attrs['lon'],
        'lat': attrs['lat'],
        'center_surf_m': round(center_surf_m, 1),
        'flow_angle_deg': attrs['flow_angle_deg'],
        'domain_half_km': half_m / 1e3,
        'bbox': {'lon_w': lon_w, 'lon_e': lon_e, 'lat_s': lat_s, 'lat_n': lat_n},
        'corners_lonlat': [[round(c[0], 6), round(c[1], 6)] for c in corners_ll],
        'vlim_kpa': VLIM_KPA,
        'dem_max_m': DEM_MAX_M,
        'bed_off_m': BED_OFF_M,
        'bed_scale_m': BED_SCALE_M,
        'bed_min_m': round(bed_min_m, 1),
        'bed_max_m': round(bed_max_m, 1),
        'stress_p997_kpa': round(p997, 1),
        'viscous_p997_kpa': round(p997v, 1),
        'dem': f'simdem_{new_id}_rg16.png',
        'bed': f'simbed_{new_id}_rg16.png',
        'stress': f'simstress_{new_id}.png',
        'stress_viscous': f'simstressv_{new_id}.png',
        'lake': f'simlake_{new_id}.png',
        'lakes': lakes_fname,
        **s2_meta,
    }
    # The absolute fields behind the difference (both models).
    meta.update(write_field_drapes(meta, ds, dsv))
    ds.close()
    dsv.close()
    return phase_pts, meta


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    attrs_all = json.loads(require_source(SIM_DIR / 'tile_attrs.json').read_text())
    lakes_json = Path('cinematic/scene_ch02/output_lakes/pnas_lakes.json')
    if not lakes_json.exists():
        raise SystemExit('missing output_lakes/pnas_lakes.json — run build_pnas_lakes.py first')
    rings = {l['id']: l['ring'] for l in json.loads(lakes_json.read_text())['lakes']}
    out = []
    all_phase = []
    for old_n in LAKES_OLD:
        attrs = attrs_all[f'2019cw{old_n}']
        pts, meta = build_lake(old_n, attrs, rings[attrs['new_id']])
        out.append(meta)
        all_phase.extend(pts)
    (OUT_DIR / 'sim_domains.json').write_text(json.dumps({'lakes': out}, indent=1))
    print(f'\nwrote {OUT_DIR}/sim_domains.json')

    # ── Fig. 5 phase space, both models ──
    models = {}
    for model in ('viscous', 'elastic'):
        pts = [{k: v for k, v in p.items() if k != 'model'}
               for p in all_phase if p['model'] == model]
        vals = [abs(v) for p in pts for v in (p['x1'], p['y1'], p['x2'], p['y2'])
                if v is not None]
        lim = float(np.ceil(max(vals) / 50) * 50) if vals else 450.0
        models[model] = {'points': pts, 'axis_kpa': lim}
        print(f'phase space {model}: {len(pts)} points, axis ±{lim:.0f} kPa')
    (OUT_DIR / 'phase_space.json').write_text(json.dumps({
        'models': models,
        # Fig. 5 caption: numerical error of the per-lake stress values.
        'error_kpa': [10, 50],
    }, separators=(',', ':')))
    print(f'wrote {OUT_DIR}/phase_space.json')
    print('\nupload:')
    print('  rclone copy cinematic/scene_ch02/output_simdomains/ r2:<bucket>/ch02/sim/'
          ' --include "*.png" --include "*.jpg" --include "*.json" --header-upload "Cache-Control: public, max-age=31536000, immutable"')


def fields_only() -> None:
    """Add/refresh ONLY the absolute-field drapes + their meta keys on an
    existing sim_domains.json (everything else untouched)."""
    path = OUT_DIR / 'sim_domains.json'
    doc = json.loads(path.read_text())
    for meta in doc['lakes']:
        old_n = int(meta['old_id'][6:])
        print(f'{meta["id"]} (2019cw{old_n}):')
        ds, dsv = open_lake_ncs(old_n)
        meta.update(write_field_drapes(meta, ds, dsv))
        ds.close()
        dsv.close()
    path.write_text(json.dumps(doc, indent=1))
    print(f'updated {path}')


if __name__ == '__main__':
    import sys
    if '--fields-only' in sys.argv:
        fields_only()
    else:
        main()
