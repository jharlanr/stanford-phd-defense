"""Ch.2 RESULTS beats: the assets behind
the stress-space walk, the elastic/viscous DIFFERENCE comparison and the
chapter's IMPLICATIONS figure. Everything is derived from the same
published sim netCDFs the block's drapes come from (build_sim_domains.py
— its tensor recipe, lake catalog and georeference are imported, never
re-derived), so the map, the diagrams and the figures agree.

Per center lake (new_id = old sim number + 1523):

  1. simstress_t2_{e,v}_<id>.png  → R2 ch02/sim/
     Δσ_t2 drapes for the block (the σ_t2 beats paint the block with the
     SECOND in-plane principal of the tangent-projected difference
     tensor — the same tensor whose first principal is simstress_*),
     seismic ±1 MPa, on the block's own plate-carrée tile grid (rebuilt
     from sim_domains.json exactly as build_sim_domains.write_field_drapes
     does).
  2. diff_{e,v}_<id>.png          → R2 ch02/results/
     Δσ_t1 as a FLAT figure for the comparison beat: EPSG:3413 north-up
     (the thesis overview figures' frame, and the block's view from the
     south), the rotated 14.75 km domain inside a square image, seismic
     ±1 MPa (the block's scale), transparent outside the domain.

One results.json → R2 ch02/results/:
  lakes[id]  extent + the domain square (image uv), every catalog lake's
             rings (image uv) with class / center / phase flags, the
             Δσ_t1 = +100 kPa contour of each model (image uv), and per
             model the peak tension (p99.9 of Δσ_t1) and the area above
             +100 kPa.
  footprints the IMPLICATIONS figure: for each lake and model the
             Δσ_t1 = +100 kPa contour in the FLOW-ALIGNED local frame
             (km, origin = the drained lake, +x downstream), plus every
             assessable neighbour (the 18 stress-space points) at its
             position in that frame.
  summary    medians over the seven lakes (peak, area, reach).

100 kPa: the tensile strength HLD studies commonly take for the ice
surface (thesis Ch.2 §Discussion, e.g. Hoffman 2018, Ultee 2020) — the
same dashed contour the thesis viscous overview figures draw.

Run (defense checkout root, the cinematic venv):
  ./cinematic/.venv/bin/python -u cinematic/scene_ch02/build_results_assets.py
Outputs: cinematic/scene_ch02/output_results/
Upload:
  rclone copy cinematic/scene_ch02/output_results/sim r2:<bucket>/ch02/sim --header-upload 'Cache-Control: public, max-age=31536000, immutable'
  rclone copy cinematic/scene_ch02/output_results/results r2:<bucket>/ch02/results --header-upload 'Cache-Control: public, max-age=31536000, immutable'
"""

import json
import sys
from pathlib import Path

import contourpy
import numpy as np
import xarray as xr
from matplotlib import colormaps
from PIL import Image

sys.stdout.reconfigure(line_buffering=True)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import build_sim_domains as bsd  # noqa: E402

ROOT = HERE.parents[1]
OUT = HERE / 'output_results'
OUT_SIM = OUT / 'sim'
OUT_RES = OUT / 'results'
# The block's tile meta (bbox, flow angle) — the published copy.
SIM_DOMAINS = ROOT / 'website' / '.r2-cache' / 'ch02' / 'sim' / 'sim_domains.json'
PHASE = ROOT / 'website' / '.r2-cache' / 'ch02' / 'sim' / 'phase_space.json'

VLIM = bsd.VLIM_KPA          # ±1 MPa, the block's drape scale
LEVEL_KPA = 100.0            # the tensile-strength contour
DIFF_PX = 800                # flat comparison image size
DECIMATE_M = 60.0            # contour vertex spacing (m)
IMPL_PX = 640                # implications composite image size
IMPL_CMAP = 'inferno'        # tension 0 → 1 MPa (Ch.1's max-stress globe)

# The seven lakes' Δσ_t1 fields on the shared flow-aligned grid, for the
# IMPLICATIONS composite (filled by build_lake).
STACK: dict[str, list[np.ndarray]] = {}
GRID: dict[str, np.ndarray] = {}


def tangent_principals_diff(ds: xr.Dataset, patch_case: str) -> tuple[np.ndarray, np.ndarray]:
    """bsd.tangent_sigma_t1_diff, returning BOTH in-plane principals of
    the tangent-projected difference tensor (kPa, tension positive)."""
    surf = {}
    for k in ('sigma_xx', 'sigma_yy', 'sigma_zz', 'sigma_xy', 'sigma_xz', 'sigma_yz'):
        v = ds[k].sel(level='surf')
        surf[k] = v.sel(case=patch_case).values - v.sel(case='nopatch').values
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
    return (mean + rad) * bsd.MPA_TO_KPA, (mean - rad) * bsd.MPA_TO_KPA


def bilinear(field: np.ndarray, x: np.ndarray, y: np.ndarray,
             lx: np.ndarray, ly: np.ndarray) -> np.ndarray:
    fx = np.clip((lx - x[0]) / (x[-1] - x[0]), 0, 1) * (len(x) - 1)
    fy = np.clip((ly - y[0]) / (y[-1] - y[0]), 0, 1) * (len(y) - 1)
    x0 = np.clip(np.floor(fx).astype(int), 0, len(x) - 2)
    y0 = np.clip(np.floor(fy).astype(int), 0, len(y) - 2)
    tx = fx - x0
    ty = fy - y0
    return (field[y0, x0] * (1 - tx) * (1 - ty) + field[y0, x0 + 1] * tx * (1 - ty)
            + field[y0 + 1, x0] * (1 - tx) * ty + field[y0 + 1, x0 + 1] * tx * ty)


def seismic_rgba(field: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    norm = np.clip((field + VLIM) / (2 * VLIM), 0, 1)
    rgba = (colormaps['seismic'](norm) * 255).astype(np.uint8)
    rgba[..., 3] = alpha
    return rgba


def decimate(line: np.ndarray, step: float) -> np.ndarray:
    """Keep vertices at least `step` apart (same units as the line)."""
    if len(line) < 3:
        return line
    keep = [0]
    last = line[0]
    for i in range(1, len(line) - 1):
        if np.hypot(*(line[i] - last)) >= step:
            keep.append(i)
            last = line[i]
    keep.append(len(line) - 1)
    return line[keep]


def contour_lines(field: np.ndarray, level: float) -> list[np.ndarray]:
    """Contour lines of `field` (rows = y index, cols = x index) at
    `level`, in fractional (col, row) index coordinates. NaN = masked."""
    z = np.ma.masked_invalid(field)
    gen = contourpy.contour_generator(z=z, line_type='Separate')
    return [ln for ln in gen.lines(level) if len(ln) >= 4]


def r4(v: float) -> float:
    return round(float(v), 4)


def r3(v: float) -> float:
    return round(float(v), 3)


def drape_t2(meta: dict, field_t2: np.ndarray, x: np.ndarray, y: np.ndarray, tag: str) -> str:
    """Δσ_t2 on the block's plate-carrée tile grid (write_field_drapes)."""
    b = meta['bbox']
    e0, n0 = bsd.T4326_3413.transform(meta['lon'], meta['lat'])
    th = np.deg2rad(meta['flow_angle_deg'])
    c, s = np.cos(th), np.sin(th)
    glon = np.linspace(b['lon_w'], b['lon_e'], bsd.OUT_PX)
    glat = np.linspace(b['lat_n'], b['lat_s'], bsd.OUT_PX)
    glon2, glat2 = np.meshgrid(glon, glat)
    ge, gn = bsd.T4326_3413.transform(glon2, glat2)
    lx = (ge - e0) * c + (gn - n0) * s
    ly = -(ge - e0) * s + (gn - n0) * c
    half_m = meta['domain_half_km'] * 1e3
    alpha = (((np.abs(lx) <= half_m) & (np.abs(ly) <= half_m)) * 255).astype(np.uint8)
    fname = f'simstress_t2_{tag}_{meta["id"]}.png'
    Image.fromarray(seismic_rgba(bilinear(field_t2, x, y, lx, ly), alpha)).save(
        OUT_SIM / fname, optimize=True)
    return fname


def build_lake(meta: dict, phase_by_center: dict) -> tuple[dict, dict]:
    new_id = meta['id']
    old_n = int(meta['old_id'][6:])
    num = old_n + 1523
    print(f'{new_id} (2019cw{old_n}):')
    ds, dsv = bsd.open_lake_ncs(old_n)
    x = ds['x'].values
    y = ds['y'].values
    assert np.allclose(x, dsv['x'].values) and np.allclose(y, dsv['y'].values)
    t1e, t2e = tangent_principals_diff(ds, 'blister')
    t1v, t2v = tangent_principals_diff(dsv, 'patch')
    # Sanity: the first principal IS the published drape's field.
    ref = bsd.tangent_sigma_t1_diff(ds, 'blister')
    assert np.nanmax(np.abs(ref - t1e)) < 1e-6

    # 1 · Δσ_t2 drapes for the block.
    drapes = {
        'stress_t2_e': drape_t2(meta, t2e, x, y, 'e'),
        'stress_t2_v': drape_t2(meta, t2v, x, y, 'v'),
    }

    # 2 · the flat EPSG:3413 north-up figure frame.
    e0, n0 = bsd.T4326_3413.transform(meta['lon'], meta['lat'])
    th = np.deg2rad(meta['flow_angle_deg'])
    c, s = np.cos(th), np.sin(th)
    half = float(min(x.max(), y.max()))
    hb = half * (abs(c) + abs(s))  # half-extent of the axis-aligned bbox
    E = np.linspace(e0 - hb, e0 + hb, DIFF_PX)
    N = np.linspace(n0 + hb, n0 - hb, DIFF_PX)  # row 0 = north
    E2, N2 = np.meshgrid(E, N)
    lx = (E2 - e0) * c + (N2 - n0) * s
    ly = -(E2 - e0) * s + (N2 - n0) * c
    inside = (np.abs(lx) <= half) & (np.abs(ly) <= half)
    alpha = (inside * 255).astype(np.uint8)

    def to_uv(e: float, n: float) -> list[float]:
        return [r4((e - (e0 - hb)) / (2 * hb)), r4(((n0 + hb) - n) / (2 * hb))]

    def to_local(e: float, n: float) -> tuple[float, float]:
        return ((e - e0) * c + (n - n0) * s, -(e - e0) * s + (n - n0) * c)

    corners = [to_uv(e0 + cx * c - cy * s, n0 + cx * s + cy * c)
               for cx, cy in ((-half, -half), (half, -half), (half, half), (-half, half))]

    per_model = {}
    for tag, model, f1 in (('e', 'elastic', t1e), ('v', 'viscous', t1v)):
        flat = bilinear(f1, x, y, lx, ly)
        fname = f'diff_{tag}_{new_id}.png'
        Image.fromarray(seismic_rgba(flat, alpha)).save(OUT_RES / fname, optimize=True)
        masked = np.where(inside, flat, np.nan)
        step_px = DECIMATE_M / (2 * hb) * DIFF_PX
        c100 = []
        for ln in contour_lines(masked, LEVEL_KPA):
            ln = decimate(ln, step_px)
            c100.append([[r4(p[0] / (DIFF_PX - 1)), r4(p[1] / (DIFF_PX - 1))] for p in ln])
        above = f1 > LEVEL_KPA
        cell_km2 = (x[1] - x[0]) * (y[1] - y[0]) / 1e6
        X, Y = np.meshgrid(x, y)
        reach = float(np.max(np.hypot(X[above], Y[above])) / 1e3) if above.any() else 0.0
        peak = float(np.nanpercentile(f1, 99.9))
        per_model[model] = {
            'image': fname,
            'contour100': c100,
            'peak_kpa': round(peak, 1),
            'area100_km2': round(float(above.sum() * cell_km2), 2),
            'reach100_km': round(reach, 2),
        }
        print(f'  {model:8s} peak(p99.9) {peak:7.1f} kPa · area>100 {above.sum() * cell_km2:6.2f} km² '
              f'· farthest >100 {reach:5.2f} km · {len(c100)} contour pieces')

    # Catalog lakes (the block's catalog): rings in image uv, centroids
    # in the local frame for the implications figure.
    rings_all = bsd.geojson_rings()
    cats = bsd.LAKE_CATEGORIES[old_n]
    listed = sorted({cw for cls in cats.values() for cw in cls})
    phase_nums = {p['num'] for p in phase_by_center.get(num, [])}
    lakes = []
    neighbours = []
    for cw in listed:
        cls = bsd.lake_class(old_n, cw)
        rings = rings_all.get(cw)
        if cls is None or not rings:
            continue
        uv_rings = []
        for ring in rings:
            ee, nn = bsd.T4326_3413.transform([p[0] for p in ring], [p[1] for p in ring])
            uv_rings.append([to_uv(a, b) for a, b in zip(ee, nn)])
        main = max(rings, key=len)
        c_lon = float(np.mean([p[0] for p in main]))
        c_lat = float(np.mean([p[1] for p in main]))
        ce, cn = bsd.T4326_3413.transform(c_lon, c_lat)
        lxk, lyk = to_local(ce, cn)
        entry = {
            'num': cw + 1523,
            'cls': cls,
            'center': cw == old_n,
            'phase': (cw + 1523) in phase_nums and cw != old_n,
            'rings': uv_rings,
            'c': to_uv(ce, cn),
            'local_km': [r3(lxk / 1e3), r3(lyk / 1e3)],
        }
        lakes.append(entry)
        if entry['phase']:
            neighbours.append({'center': num, 'num': cw + 1523, 'cls': cls,
                               'x': entry['local_km'][0], 'y': entry['local_km'][1]})

    ds.close()
    dsv.close()
    STACK.setdefault('elastic', []).append(t1e)
    STACK.setdefault('viscous', []).append(t1v)
    GRID['x'], GRID['y'] = x, y
    out = {
        'id': new_id,
        'num': num,
        'half_km': r3(half / 1e3),
        'bbox_half_km': r3(hb / 1e3),
        'flow_angle_deg': meta['flow_angle_deg'],
        'square': corners,
        'lakes': lakes,
        'models': per_model,
        'neighbours': neighbours,
    }
    return out, drapes


def main() -> None:
    OUT_SIM.mkdir(parents=True, exist_ok=True)
    OUT_RES.mkdir(parents=True, exist_ok=True)
    doc = json.loads(SIM_DOMAINS.read_text())
    phase = json.loads(PHASE.read_text())
    phase_by_center: dict[int, list] = {}
    for p in phase['models']['viscous']['points']:
        phase_by_center.setdefault(p['center'], []).append(p)

    lakes = {}
    drapes = {}
    for meta in doc['lakes']:
        res, dr = build_lake(meta, phase_by_center)
        lakes[res['id']] = res
        drapes[res['id']] = dr

    summary = {}
    for model in ('elastic', 'viscous'):
        pk = [l['models'][model]['peak_kpa'] for l in lakes.values()]
        ar = [l['models'][model]['area100_km2'] for l in lakes.values()]
        rc = [l['models'][model]['reach100_km'] for l in lakes.values()]
        summary[model] = {
            'peak_kpa_median': round(float(np.median(pk)), 1),
            'peak_kpa_range': [min(pk), max(pk)],
            'area100_km2_median': round(float(np.median(ar)), 2),
            'reach100_km_median': round(float(np.median(rc)), 2),
        }
        print(f'{model}: peak median {np.median(pk):.0f} kPa (range {min(pk):.0f}–{max(pk):.0f}), '
              f'area>100 median {np.median(ar):.1f} km², farthest>100 median {np.median(rc):.2f} km')
    # IMPLICATIONS: the seven drainages STACKED — the mean Δσ_t1 of the
    # seven lakes on the shared flow-aligned grid (origin = the drained
    # lake, +x downstream), tension only, inferno 0 → 1 MPa, with its
    # +100 kPa contour (km). Image row 0 = +y (left of flow), column 0 =
    # −x (upstream), so the figure reads with the ice flowing left → right.
    x, y = GRID['x'], GRID['y']
    composite = {}
    for model, tag in (('elastic', 'e'), ('viscous', 'v')):
        mean = np.mean(np.stack(STACK[model]), axis=0)
        # resample to IMPL_PX on the same extent (row 0 = +y)
        gx = np.linspace(x[0], x[-1], IMPL_PX)
        gy = np.linspace(y[-1], y[0], IMPL_PX)
        GX, GY = np.meshgrid(gx, gy)
        img = bilinear(mean, x, y, GX, GY)
        norm = np.clip(img / VLIM, 0, 1)
        rgba = (colormaps[IMPL_CMAP](norm) * 255).astype(np.uint8)
        rgba[..., 3] = 255
        fname = f'impl_{tag}.png'
        Image.fromarray(rgba).save(OUT_RES / fname, optimize=True)
        lines = []
        for ln in contour_lines(mean, LEVEL_KPA):
            xs = np.interp(ln[:, 0], np.arange(len(x)), x)
            ys = np.interp(ln[:, 1], np.arange(len(y)), y)
            pts = decimate(np.stack([xs, ys], axis=1), DECIMATE_M)
            if len(pts) >= 4:
                lines.append([[r3(px / 1e3), r3(py / 1e3)] for px, py in pts])
        above = mean > LEVEL_KPA
        cell_km2 = (x[1] - x[0]) * (y[1] - y[0]) / 1e6
        composite[model] = {
            'image': fname,
            'contour100_km': lines,
            'peak_kpa': round(float(np.nanpercentile(mean, 99.9)), 1),
            'area100_km2': round(float(above.sum() * cell_km2), 2),
            'upstream100_km': round(float(-x[np.where(above.any(axis=0))[0].min()] / 1e3), 2)
            if above.any() else 0.0,
        }
        print(f'composite {model}: peak {composite[model]["peak_kpa"]} kPa · area>100 '
              f'{composite[model]["area100_km2"]} km² · upstream reach {composite[model]["upstream100_km"]} km '
              f'· {len(lines)} contour pieces')

    (OUT_RES / 'results.json').write_text(json.dumps({
        'level_kpa': LEVEL_KPA,
        'half_km': r3(float(x[-1]) / 1e3),
        'composite': composite,
        'vlim_kpa': VLIM,
        'lakes': lakes,
        'drapes': drapes,
        'summary': summary,
    }, separators=(',', ':')))
    print(f'wrote {OUT_RES / "results.json"}')


if __name__ == '__main__':
    main()
