"""Chapter 2's physically meaningful POST-DRAINAGE ELASTIC field, and the
stress-space points to go with it.

The two static elastic solves (no blister / blister) are a body loaded by
gravity from an unstressed reference, so their ABSOLUTE stresses have no
physical meaning; only their difference Δσ^E does. The stress just after
drainage is the viscous pre-drainage state plus that elastic increment —
exact for any viscoelastic solid with an instantaneous linear elastic
response (the creep term is bounded, so it integrates to nothing across
the instant; the jump obeys Hooke's law and, by linearity, adds to what
was there). Tensors first, principals after: σ_t1(A + B) ≠ σ_t1(A) + σ_t1(B).

    σ^S = σ^V_nopatch + (σ^E_blister − σ^E_nopatch)      (six Cauchy components, surface)

Per center lake (same frame, colour scale and alpha as the other drapes
in build_sim_domains.py — its helpers are imported, not copied):
  simstress_s_post_<id>.png      σ_t1 of σ^S, seismic ±1 MPa
  simstress_s_post_t2_<id>.png   σ_t2 of σ^S
Shared:
  sim_domains_v2.json   sim_domains.json + `stress_s_post`, `stress_s_post_t2`
  phase_space_v2.json   phase_space.json with the ELASTIC points' x1/x2 =
                        polygon means of σ_t1/σ_t2 of σ^S, and on EVERY
                        point x1_pre/x2_pre = polygon means of the viscous
                        pre-drainage σ_t1/σ_t2 (one background for both
                        models). The viscous x1/y1 are recomputed the same
                        way and checked against the published pickles'
                        values (phase_space.json) — the method's error.

R2 objects are immutable: new names only, the old files stay.

Run (defense checkout root):
  python -u cinematic/scene_ch02/build_sim_superposed.py
then
  rclone copy cinematic/scene_ch02/output_simdomains/ r2:<bucket>/ch02/sim/ \
      --include "simstress_s_post*" --include "*_v2.json" \
      --header-upload "Cache-Control: public, max-age=31536000, immutable"
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import xarray as xr
from matplotlib import colormaps
from PIL import Image, ImageDraw

sys.stdout.reconfigure(line_buffering=True)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import build_sim_domains as bsd  # noqa: E402

OUT_DIR = bsd.OUT_DIR
COMPS = ('sigma_xx', 'sigma_yy', 'sigma_zz', 'sigma_xy', 'sigma_xz', 'sigma_yz')


def tangent_principals(surf: dict, topo: np.ndarray, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The SI §4C recipe on an arbitrary surface Cauchy tensor (MPa → kPa):
    project onto the plane tangent to the (shared) surface, eigenvalues of
    the in-plane block. Returns (σ_t1, σ_t2), tension positive."""
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


def surface_tensor(ds: xr.Dataset, case: str) -> dict:
    return {k: ds[k].sel(level='surf', case=case).values for k in COMPS}


def fields(ds: xr.Dataset, dsv: xr.Dataset) -> dict:
    """Every surface principal field the talk needs, kPa, on the sim grid."""
    topo = ds['topo_surf'].sel(level='surf', case='nopatch').values
    x, y = ds['x'].values, ds['y'].values
    e_ref, e_bl = surface_tensor(ds, 'nopatch'), surface_tensor(ds, 'blister')
    v_pre, v_post = surface_tensor(dsv, 'nopatch'), surface_tensor(dsv, 'patch')
    d_e = {k: e_bl[k] - e_ref[k] for k in COMPS}
    d_v = {k: v_post[k] - v_pre[k] for k in COMPS}
    s_post = {k: v_pre[k] + d_e[k] for k in COMPS}          # σ^S: the viscous background + the elastic increment
    out = {}
    out['pre_v'] = tangent_principals(v_pre, topo, x, y)
    out['post_v'] = tangent_principals(v_post, topo, x, y)
    out['diff_v'] = tangent_principals(d_v, topo, x, y)
    out['diff_e'] = tangent_principals(d_e, topo, x, y)
    out['post_s'] = tangent_principals(s_post, topo, x, y)
    return out


def frame(meta: dict, x: np.ndarray, y: np.ndarray):
    """build_sim_domains.write_field_drapes' frame: the lake's plate-carree
    tile grid → the rotated sim frame, the alpha of the domain square, and
    a bilinear sampler of a sim-grid field onto it."""
    b = meta['bbox']
    e0, n0 = bsd.T4326_3413.transform(meta['lon'], meta['lat'])
    th = np.deg2rad(meta['flow_angle_deg'])
    cos_t, sin_t = np.cos(th), np.sin(th)
    glon = np.linspace(b['lon_w'], b['lon_e'], bsd.OUT_PX)
    glat = np.linspace(b['lat_n'], b['lat_s'], bsd.OUT_PX)
    glon2, glat2 = np.meshgrid(glon, glat)
    ge, gn = bsd.T4326_3413.transform(glon2, glat2)
    lx = (ge - e0) * cos_t + (gn - n0) * sin_t
    ly = -(ge - e0) * sin_t + (gn - n0) * cos_t
    half_m = meta['domain_half_km'] * 1e3
    alpha = (((np.abs(lx) <= half_m) & (np.abs(ly) <= half_m)) * 255).astype(np.uint8)

    def sample(field: np.ndarray) -> np.ndarray:
        fx = np.clip((lx - x[0]) / (x[-1] - x[0]), 0, 1) * (len(x) - 1)
        fy = np.clip((ly - y[0]) / (y[-1] - y[0]), 0, 1) * (len(y) - 1)
        x0 = np.clip(np.floor(fx).astype(int), 0, len(x) - 2)
        y0 = np.clip(np.floor(fy).astype(int), 0, len(y) - 2)
        tx, ty = fx - x0, fy - y0
        return (field[y0, x0] * (1 - tx) * (1 - ty) + field[y0, x0 + 1] * tx * (1 - ty)
                + field[y0 + 1, x0] * (1 - tx) * ty + field[y0 + 1, x0 + 1] * tx * ty)

    return alpha, sample, (e0, n0, cos_t, sin_t)


def drape(field: np.ndarray, alpha: np.ndarray, sample, fname: str) -> None:
    norm = np.clip((sample(field) + bsd.VLIM_KPA) / (2 * bsd.VLIM_KPA), 0, 1)
    rgba = (colormaps['seismic'](norm) * 255).astype(np.uint8)
    rgba[..., 3] = alpha
    Image.fromarray(rgba).save(OUT_DIR / fname, optimize=True)


def polygon_mask(ring_ll: list, rot, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """A Dunmire lake ring (lon/lat) rasterised on the sim grid (row = y
    ascending as stored, col = x), through EPSG:3413 and the tile's
    rotation — the inverse of the drape frame."""
    e0, n0, cos_t, sin_t = rot
    lon = np.array([p[0] for p in ring_ll])
    lat = np.array([p[1] for p in ring_ll])
    ge, gn = bsd.T4326_3413.transform(lon, lat)
    lx = (ge - e0) * cos_t + (gn - n0) * sin_t
    ly = -(ge - e0) * sin_t + (gn - n0) * cos_t
    px = (lx - x[0]) / (x[1] - x[0])
    py = (ly - y[0]) / (y[1] - y[0])
    im = Image.new('L', (len(x), len(y)), 0)
    ImageDraw.Draw(im).polygon(list(zip(px.tolist(), py.tolist())), fill=255)
    return np.array(im) > 0


def pmean(field: np.ndarray, mask: np.ndarray) -> float | None:
    v = field[mask]
    v = v[np.isfinite(v)]
    return round(float(v.mean()), 1) if v.size else None


def main() -> None:
    doc = json.loads((OUT_DIR / 'sim_domains.json').read_text())
    ps = json.loads((OUT_DIR / 'phase_space.json').read_text())
    rings_all = bsd.geojson_rings()
    # the published points, by (model, center, num) — to update in place
    pts = {(m, p['center'], p['num']): p for m, mm in ps['models'].items() for p in mm['points']}
    checks = []
    for meta in doc['lakes']:
        old_n = int(meta['old_id'][6:])
        print(f"{meta['id']} (2019cw{old_n}):")
        ds, dsv = bsd.open_lake_ncs(old_n)
        x, y = ds['x'].values, ds['y'].values
        F = fields(ds, dsv)
        alpha, sample, rot = frame(meta, x, y)
        f1 = f"simstress_s_post_{meta['id']}.png"
        f2 = f"simstress_s_post_t2_{meta['id']}.png"
        drape(F['post_s'][0], alpha, sample, f1)
        drape(F['post_s'][1], alpha, sample, f2)
        meta['stress_s_post'] = f1
        meta['stress_s_post_t2'] = f2
        p997 = np.nanpercentile(np.abs(F['post_s'][0]), 99.7)
        print(f"  σ^S_t1 p99.7 {p997:.0f} kPa · range {np.nanmin(F['post_s'][0]):.0f} … {np.nanmax(F['post_s'][0]):.0f} → {f1}, {f2}")
        # the stress-space points of this center lake's neighbours
        for (model, center, num), p in pts.items():
            if center != old_n + 1523:
                continue
            cw_rings = rings_all.get(num - 1523)
            if not cw_rings:
                print(f'  WARN {num}: no ring')
                continue
            mask = np.zeros((len(y), len(x)), bool)
            for r in cw_rings:
                mask |= polygon_mask(r, rot, x, y)
            if not mask.any():
                print(f'  WARN {num}: ring outside the grid')
                continue
            p['x1_pre'] = pmean(F['pre_v'][0], mask)
            p['x2_pre'] = pmean(F['pre_v'][1], mask)
            if model == 'elastic':
                p['x1'] = pmean(F['post_s'][0], mask)
                p['x2'] = pmean(F['post_s'][1], mask)
                # the method against the pickles: Δσ^E means must agree
                checks.append((num, 'elastic y1', p['y1'], pmean(F['diff_e'][0], mask)))
            else:
                checks.append((num, 'viscous x1', p['x1'], pmean(F['post_v'][0], mask)))
                checks.append((num, 'viscous y1', p['y1'], pmean(F['diff_v'][0], mask)))
        ds.close()
        dsv.close()
    # the method check: polygon means recomputed here vs the published pickles
    print('\nmethod check (published → recomputed, kPa):')
    worst = 0.0
    for num, what, a, b in checks:
        if a is None or b is None:
            continue
        worst = max(worst, abs(a - b))
        print(f'  {num} {what:11s} {a:8.1f} → {b:8.1f}  (Δ {b - a:+.1f})')
    print(f'  worst |Δ| = {worst:.1f} kPa (the published error bars are {ps["error_kpa"]} kPa)')
    for m in ps['models'].values():
        vals = [abs(v) for p in m['points'] for k in ('x1', 'y1', 'x2', 'y2', 'x1_pre', 'x2_pre') for v in [p.get(k)] if v is not None]
        m['axis_kpa'] = float(np.ceil(max(vals) / 50) * 50) if vals else m['axis_kpa']
    ps['note'] = ('v2: elastic x1/x2 = polygon means of the surface principals of '
                  'σ^V_pre + Δσ^E (tensors added, then eigenvalues); x1_pre/x2_pre = the viscous '
                  'pre-drainage principals, every point. build_sim_superposed.py')
    (OUT_DIR / 'sim_domains_v2.json').write_text(json.dumps(doc, indent=1))
    (OUT_DIR / 'phase_space_v2.json').write_text(json.dumps(ps, separators=(',', ':')))
    print(f'\nwrote {OUT_DIR}/sim_domains_v2.json and phase_space_v2.json')
    print('upload:\n  rclone copy cinematic/scene_ch02/output_simdomains/ r2:<bucket>/ch02/sim/ '
          '--include "simstress_s_post*" --include "*_v2.json" '
          '--header-upload "Cache-Control: public, max-age=31536000, immutable"')


if __name__ == '__main__':
    main()
