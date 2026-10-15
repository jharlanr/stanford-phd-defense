"""The Introduction's "coupling length" step (built as a SAMPLE for review).

The director's brief: put the Christoffersen 2018 / Lai 2021 / Stevens 2024 /
Stevens 2026 cards top-left and, on the greenland object over central-west
Greenland, each paper's footprint — the two end members of the
"how far does one drainage reach?" conversation.

Writes website/src/config/couplingLength.ts (generated; every item carries
its `source`). Run from the repo root (needs pyproj, scipy, shapely, matplotlib, PIL):

    python cinematic/scene_01_intro/build_coupling_length.py

Inputs (all copies, `bash cinematic/fetch_sources.sh` → source_data/coupling/):
  christoffersen2018.pdf                    a local Zotero copy (Nat. Commun. 9:1064)
  apcoords_lle_2012_FLOW.mat                goodnesglaciers/lake_strain (Stevens 2024)
  apcoords_lle_2023.mat                     goodnesglaciers/lakes_cluster (Stevens 2026)
  environs_lakes_2022B_250416_noboundaries.mat, environs_lakes_2023B_S1S2MO_250416_noboundaries.mat
                                            goodnesglaciers/lakes_cluster (Stevens 2026)
  data/BedMachineGreenland-v6.nc            (ice mask, to register Christoffersen's model grid)

What is EXACT and what is DIGITISED is written into every item. In short:
  Christoffersen 2018 — DIGITISED. The paper gives no coordinates for its
    model grid. Fig. 4's raster panels (x/y in km) were registered to the
    real ice margin: the off-ice (white) region of Fig. 4a matches the
    BedMachine v6 ice mask at 95 % of 0.5-km cells with the model grid on
    UTM 22N, (x, y) km → (523.25 + x, 7404.0 + y) km (a translation-only
    fit; a free rotation gains nothing). The tensile-shock region is the
    ΔRxx ≥ 50 kPa area of Fig. 4h, colour-matched to its colour bar:
    942 km² here vs the paper's 925 km². The 124 cascade lakes are the
    magenta dots of Fig. 4a/d/g (43 + 30 + 51), found as distance-transform maxima; in the
    densest clusters a dot can be missed or doubled.
  Lai 2021 — EXACT to the paper's printed precision (Supp. Table 1 lake
    positions to 0.01°; blister radii R from the Fig. 3a table).
  Stevens 2024 — lakes EXACT to the paper's printed 0.01°; GPS stations
    EXACT (the paper's own a-priori coordinates, lake_strain repo).
  Stevens 2026 — EXACT from the paper's own code: the ROI polygon
    (paperfig1_map_fullROI_260122.m, km from the M1 moulin in EPSG:3413 —
    7189 km², as the paper states), the 23 GNSS stations, the FASTER lake
    centres (L-numbers → names from the cluster scripts' figure labels).
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pyproj
import scipy.io as sio
import xarray as xr
from matplotlib import path as mpath
from matplotlib import pyplot as plt
from PIL import Image
from scipy import ndimage as ndi
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'cinematic' / 'source_data'
CPL = SRC / 'coupling'
OUT = ROOT / 'website' / 'src' / 'config' / 'couplingLength.ts'

LL2UTM = pyproj.Transformer.from_crs(4326, 32622, always_xy=True)
UTM2LL = pyproj.Transformer.from_crs(32622, 4326, always_xy=True)
LL2PS = pyproj.Transformer.from_crs(4326, 3413, always_xy=True)
PS2LL = pyproj.Transformer.from_crs(3413, 4326, always_xy=True)
UTM2PS = pyproj.Transformer.from_crs(32622, 3413, always_xy=True)


def r4(v: float) -> float:
    return float(round(float(v), 4))


# ─── Christoffersen et al. 2018 ────────────────────────────────────────
# Page 6 (Fig. 4) of the PDF. The map panels are 300-ppi rasters placed at
# these PDF-point boxes (read with PyMuPDF `get_image_info`); the axis
# calibration comes from the tick labels' text boxes on the same page:
# x = 20…100 km at 126.46 / 146.0 / 165.53 / 185.07 / 204.6 pt (left
# column; the middle column is +148.31 pt), y = 20 / 40 / 60 km at
# 582.0 / 562.42 / 542.83 pt (bottom row); rows a/d/g share the scale.
C18_PT_PER_KM = 0.9768
C18_Y_PT_PER_KM = 0.9785
C18_X0_LEFT = 106.93      # pt at x = 0, left column (a, d, g)
C18_X0_MID = 255.24       # pt at x = 0, middle column (b, e, h)
C18_Y0 = {'a': 448.9, 'd': 505.57 + 20 * 0.9785, 'g': 601.6, 'h': 601.6}
# pdfimages page-6 index, panel, PDF bbox (x0, x1, y0, y1)
C18_PANELS = {
    'a': (0, (113.65, 232.73, 381.08, 435.36)),
    'd': (1, (113.68, 232.76, 457.28, 511.67)),
    'g': (2, (113.71, 233.03, 533.60, 588.47)),
    'h': (5, (261.85, 357.17, 533.57, 587.60)),
    'i': (8, (367.93, 487.25, 533.60, 587.88)),  # its colour bar is ΔR's (−100…100 kPa)
}
# The registration (see the module docstring): model km → UTM 22N km.
C18_UTM0 = (523.25, 7404.0)
# Drained lakes per day of the 6–10 June 2010 cascade (Fig. 4 caption).
C18_DAY_COUNTS = {'a': 43, 'd': 30, 'g': 51}


def c18_rasters(tmp: Path) -> dict[str, np.ndarray]:
    subprocess.run(
        ['pdfimages', '-f', '6', '-l', '6', '-png', str(CPL / 'christoffersen2018.pdf'), str(tmp / 'p6')],
        check=True,
    )
    return {
        k: np.asarray(Image.open(tmp / f'p6-{idx:03d}.png').convert('RGB')).astype(float)
        for k, (idx, _) in C18_PANELS.items()
    }


def c18_axes(panel: str, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    h, w = shape
    x0p, x1p, y0p, y1p = C18_PANELS[panel][1]
    xorig = C18_X0_MID if panel == 'h' else C18_X0_LEFT
    xs = (x0p + (np.arange(w) + 0.5) / w * (x1p - x0p) - xorig) / C18_PT_PER_KM
    ys = (C18_Y0[panel] - (y0p + (np.arange(h) + 0.5) / h * (y1p - y0p))) / C18_Y_PT_PER_KM
    return xs, ys


def model_to_ll(x, y):
    lon, lat = UTM2LL.transform((C18_UTM0[0] + np.asarray(x)) * 1e3, (C18_UTM0[1] + np.asarray(y)) * 1e3)
    return lat, lon


def bm_ice_at_model(xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    ds = xr.open_dataset(SRC / 'data' / 'BedMachineGreenland-v6.nc')
    sub = ds['mask'].sel(x=slice(-320000, -60000), y=slice(-2380000, -2620000))
    X = sub['x'].values / 1e3
    Y = sub['y'].values / 1e3
    ice = sub.values == 2
    PX, PY = np.meshgrid(xs, ys)
    bx, by = UTM2PS.transform((C18_UTM0[0] + PX) * 1e3, (C18_UTM0[1] + PY) * 1e3)
    xi = np.clip(np.searchsorted(X, bx / 1e3), 0, len(X) - 1)
    yi = np.clip(np.searchsorted(-Y, -by / 1e3), 0, len(Y) - 1)
    return ice[yi, xi]


def c18_tensile_shock(r: dict[str, np.ndarray]) -> tuple[list[list[list[float]]], float]:
    """ΔRxx ≥ 50 kPa (Fig. 4h), as lat/lon rings (area-sorted) + total km²."""
    cbim = r['i']
    rows = np.arange(cbim.shape[0])
    # Colour-bar labels (page 6 text boxes): +100 at 534.2 pt, −100 at 587.39 pt.
    y_pt = 533.6 + (rows + 0.5) / cbim.shape[0] * 54.28
    val = 100 - (y_pt - 534.2) / 53.19 * 200
    sel = (val <= 100) & (val >= -100)
    cb = cbim[sel][:, 445:470].mean(axis=1)
    vals = val[sel]
    im = r['h']
    d2 = ((im[:, :, None, :] - cb[None, None, :, :]) ** 2).sum(-1)
    v = vals[d2.argmin(-1)]
    xs, ys = c18_axes('h', im.shape[:2])
    onice = ndi.binary_erosion(bm_ice_at_model(xs, ys), iterations=3)
    hi = ndi.binary_closing((v >= 50) & onice, iterations=2) & onice
    pa = (xs[1] - xs[0]) * (ys[0] - ys[1])
    area = float(hi.sum() * pa)
    fig = plt.figure()
    cs = plt.contour(xs, ys, hi.astype(float), levels=[0.5])
    rings = []
    for seg in cs.allsegs[0]:
        if len(seg) < 8:
            continue
        poly = Polygon(seg)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.area < 8:  # km² — drop specks
            continue
        poly = poly.simplify(0.25)
        xy = np.asarray(poly.exterior.coords)
        lat, lon = model_to_ll(xy[:, 0], xy[:, 1])
        rings.append((poly.area, [[r4(a), r4(b)] for a, b in zip(lat, lon)]))
    plt.close(fig)
    rings.sort(key=lambda t: -t[0])
    return [ring for _, ring in rings], area


def find_dots(im: np.ndarray, n: int) -> list[tuple[float, float, float]]:
    """The n largest magenta discs (x_px, y_px, r_px): maxima of the
    distance transform of the magenta mask — each dot's white rim splits
    overlapping dots — taken greedily, largest first, never two within
    0.7 of the larger radius. (A Hough transform on the rims put centres on
    the rims of the big, overlapped dots; checked against the figure.)"""
    mag = (im[:, :, 0] > 190) & (im[:, :, 1] < 110) & (im[:, :, 2] > 190)
    mag[:, 400:] = False  # the raster's colour bar
    edt = ndi.distance_transform_edt(mag)
    peak = (edt == ndi.maximum_filter(edt, size=5)) & (edt >= 1.5)
    cand = np.argwhere(peak)
    vals = edt[cand[:, 0], cand[:, 1]]
    keep: list[tuple[float, float, float]] = []
    for k in np.argsort(-vals):
        y, x = cand[k]
        r = float(vals[k])
        if any((x - a) ** 2 + (y - b) ** 2 < (0.7 * max(r, c)) ** 2 for a, b, c in keep):
            continue
        keep.append((float(x), float(y), r))
        if len(keep) >= n:
            break
    return keep


def c18_lakes(r: dict[str, np.ndarray]) -> list[dict]:
    out = []
    for panel, n in C18_DAY_COUNTS.items():
        im = r[panel]
        xs, ys = c18_axes(panel, im.shape[:2])
        for x, y, _ in find_dots(im, n):
            lat, lon = model_to_ll(np.interp(x, np.arange(len(xs)), xs), np.interp(y, np.arange(len(ys)), ys))
            out.append({'lat': r4(lat), 'lon': r4(lon), 'day': {'a': '6 Jun', 'd': '7 Jun', 'g': '8–10 Jun'}[panel]})
    return out


def densify(latlon: list[tuple[float, float]], step_deg: float = 0.02) -> list[list[float]]:
    pts: list[list[float]] = []
    for (a0, b0), (a1, b1) in zip(latlon[:-1], latlon[1:]):
        n = max(1, int(max(abs(a1 - a0), abs(b1 - b0) * 0.37) / step_deg))
        for i in range(n):
            t = i / n
            pts.append([r4(a0 + (a1 - a0) * t), r4(b0 + (b1 - b0) * t)])
    pts.append([r4(latlon[-1][0]), r4(latlon[-1][1])])
    return pts


def c18_domain() -> list[list[float]]:
    # 9000 km² = 120 × 75 km: Fig. 1a's axes run x 0–120, y 0–~75 km.
    corners = [(0, 0), (120, 0), (120, 75), (0, 75), (0, 0)]
    ll = [tuple(float(v) for v in model_to_ll(x, y)) for x, y in corners]
    return densify(ll)


# ─── Stevens et al. 2026 ───────────────────────────────────────────────
# M1 moulin origin + ROI vertices: paperfig1_map_fullROI_260122.m lines
# 48–50 and 224–225 (km in EPSG:3413 from the "North Lake" M1 moulin,
# 68.72 °N 49.53 °W).
S26_ORIGIN = (68.72, -49.53)
S26_ROI_X = [-15, 60, 104, 104, 15, -10, -33, -33, -15]
S26_ROI_Y = [15, 4, -8, -50, -50, -41, -33, -1, 15]
# 2022 FASTER lake numbers → the paper's names (cluster1/3 scripts' labels).
S26_NAMED_2022 = {81: 'L1A', 78: 'L1B', 72: 'L72', 47: 'L47', 34: 'L34', 156: 'L2A', 143: 'L2B', 187: 'L2C'}


def s26() -> dict:
    mx, my = LL2PS.transform(S26_ORIGIN[1], S26_ORIGIN[0])
    xs = (np.array(S26_ROI_X) * 1e3 + mx)
    ys = (np.array(S26_ROI_Y) * 1e3 + my)
    # densify in projected space so the edges follow the projection
    ring = []
    for i in range(len(xs) - 1):
        for t in np.linspace(0, 1, 12, endpoint=False):
            ring.append((xs[i] + (xs[i + 1] - xs[i]) * t, ys[i] + (ys[i + 1] - ys[i]) * t))
    ring.append((xs[0], ys[0]))
    rx, ry = zip(*ring)
    lon, lat = PS2LL.transform(np.array(rx), np.array(ry))
    area = Polygon(zip(S26_ROI_X, S26_ROI_Y)).area
    st = sio.loadmat(CPL / 'apcoords_lle_2023.mat')['apcoords_lle_2023']
    names = ['QIET'] + [f'SQ1{i}' for i in range(1, 7)] + [f'SQ2{i}' for i in range(1, 8)] + \
        [f'SQ3{i}' for i in range(1, 8)] + ['MHIH', 'MLOW']
    stations = [{'name': n, 'lat': r4(st[0, i]), 'lon': r4(st[1, i])} for i, n in enumerate(names)]
    roi_path = mpath.Path(np.c_[S26_ROI_X, S26_ROI_Y])
    hf = []
    named = {}
    for yr, fn in [(2022, 'environs_lakes_2022B_250416_noboundaries.mat'),
                   (2023, 'environs_lakes_2023B_S1S2MO_250416_noboundaries.mat')]:
        e = sio.loadmat(CPL / fn, squeeze_me=True, struct_as_record=False)['environs_lakes']
        mech = e.laketypeing_dates[:, 6]
        inroi = roi_path.contains_points(np.c_[e.X_km, e.Y_km])
        for i in np.nonzero((mech == 1) & inroi)[0]:
            hf.append({'lat': r4(e.lat[i]), 'lon': r4(e.lon[i]), 'year': yr})
        if yr == 2022:
            for num, nm in S26_NAMED_2022.items():
                named[nm] = {'name': nm, 'lat': r4(e.lat[num - 1]), 'lon': r4(e.lon[num - 1]),
                             'hKm': round(float(e.H[num - 1]) / 1e3, 2)}
    return {
        'roi': [[r4(a), r4(b)] for a, b in zip(lat, lon)],
        'roiAreaKm2': round(area),
        'stations': stations,
        'hf': hf,
        'named': named,
    }


# ─── Stevens et al. 2024 ───────────────────────────────────────────────
def s24_stations() -> list[dict]:
    a = sio.loadmat(CPL / 'apcoords_lle_2012_FLOW.mat')['apcoords_lle_2012']
    # 21 columns: the 16 main-array receivers, then FL01, FL02, FL06 (the
    # three up/down-flow sites of 2012: 16 km and 8.6 km down-flow, 26.6 km
    # up-flow of L1A), then two at South Lake (SLSS; Lai 2021's) — dropped.
    out = []
    for i in range(19):
        out.append({'lat': r4(a[0, i]), 'lon': r4(a[1, i]), 'flow': i >= 16})
    return out


def dest(lat: float, lon: float, east_km: float, north_km: float) -> tuple[float, float]:
    x, y = LL2UTM.transform(lon, lat)
    lo, la = UTM2LL.transform(x + east_km * 1e3, y + north_km * 1e3)
    return r4(la), r4(lo)


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        r = c18_rasters(Path(td))
        shock, shock_area = c18_tensile_shock(r)
        lakes = c18_lakes(r)
    domain = c18_domain()
    s26d = s26()
    s24st = s24_stations()
    lat_l = [p['lat'] for p in lakes]
    lon_l = [p['lon'] for p in lakes]
    # Christoffersen's scale rule: 80 km (the abstract's "lakes as far as
    # 80 km apart"), laid along ice flow through the cascade's centre.
    cx = float(np.mean([LL2UTM.transform(b, a)[0] for a, b in zip(lat_l, lon_l)])) / 1e3
    cy = float(np.mean([LL2UTM.transform(b, a)[1] for a, b in zip(lat_l, lon_l)])) / 1e3
    c18_rule = [list(UTM2LL.transform((cx - 40) * 1e3, (cy - 26) * 1e3))[::-1],
                list(UTM2LL.transform((cx + 40) * 1e3, (cy - 26) * 1e3))[::-1]]
    c18_rule = [[r4(a), r4(b)] for a, b in c18_rule]
    l1a = (68.72, -49.50)
    s24_rule = [[l1a[0], l1a[1]], list(dest(*l1a, 3.0, 0.0))]
    l2a = s26d['named']['L2A']
    s26_rule = [[l2a['lat'], l2a['lon']], list(dest(l2a['lat'], l2a['lon'], 5.0, 0.0))]
    ux, uy = LL2UTM.transform(np.array(lon_l), np.array(lat_l))
    pts = np.c_[ux, uy] / 1e3
    span = float(max(np.hypot(*(pts[i] - pts[j])) for i in range(len(pts)) for j in range(i)))
    data = {
        'c18': {'spanKm': round(span), 'domain': domain, 'shock': shock, 'shockAreaKm2': round(shock_area), 'lakes': lakes, 'rule': c18_rule},
        's26': {**s26d, 'rule': s26_rule},
        's24': {'stations': s24st, 'rule': s24_rule},
    }
    print('christoffersen: shock', round(shock_area), 'km² in', len(shock), 'rings;', len(lakes), 'lakes')
    print('stevens 2026: roi', s26d['roiAreaKm2'], 'km²,', len(s26d['stations']), 'stations,', len(s26d['hf']), 'HF lakes')
    OUT.write_text(render_ts(data))
    print('wrote', OUT.relative_to(ROOT))


def js(v) -> str:
    return json.dumps(v, separators=(',', ':'))


def render_ts(d: dict) -> str:
    c18, s26d, s24 = d['c18'], d['s26'], d['s24']
    n = s26d['named']
    return TEMPLATE.format(
        c18_domain=js(c18['domain']),
        c18_shock=js(c18['shock']),
        c18_shock_area=c18['shockAreaKm2'],
        c18_lakes=js([[p['lat'], p['lon']] for p in c18['lakes']]),
        c18_lake_n=len(c18['lakes']),
        c18_span=c18['spanKm'],
        c18_from=js(c18['rule'][0]), c18_to=js(c18['rule'][1]),
        s26_roi=js(s26d['roi']),
        s26_roi_area=s26d['roiAreaKm2'],
        s26_stations=js([[s['name'], s['lat'], s['lon']] for s in s26d['stations']]),
        s26_hf=js([[p['lat'], p['lon'], p['year']] for p in s26d['hf']]),
        s26_hf_n=len(s26d['hf']),
        s26_named=js([[v['name'], v['lat'], v['lon']] for v in n.values()]),
        s26_from=js(s26d['rule'][0]), s26_to=js(s26d['rule'][1]),
        s24_stations=js([[s['lat'], s['lon']] for s in s24['stations']]),
        s24_from=js(s24['rule'][0]), s24_to=js(s24['rule'][1]),
        l2a_h=n['L2A']['hKm'],
    )


TEMPLATE = '''// GENERATED by cinematic/scene_01_intro/build_coupling_length.py — edit
// the script, not this file (the colours and labels live in the script's
// TEMPLATE too). The Introduction's "coupling length" step (built as a
// SAMPLE for review): each paper's footprint on central-west Greenland.
//
// Every item says where it came from and whether it is EXACT (the paper's
// own numbers or its authors' own code/data) or DIGITISED (read off a
// figure — approximate). Coordinates are [lat, lon] in degrees.

export type LatLon = [number, number]

export type CouplingPaperId = 'christoffersen2018' | 'lai2021' | 'stevens2024' | 'stevens2026'

export interface CouplingRule {{
  /** The rule's two ends, true length on the ice. */
  from: LatLon
  to: LatLon
  /** The figure label, e.g. "≈ 80 km". */
  label: string
  source: string
}}

export interface CouplingPaper {{
  id: CouplingPaperId
  /** Key colour — the card's tab, the footprint, the rule. */
  color: string
  rule: CouplingRule
}}

// Colours: four hues that hold on white ice (drawn over a dark halo) and on
// the dark page. Warm = the large end member, cool = the small ones.
export const COUPLING_PAPERS: CouplingPaper[] = [
  {{
    id: 'christoffersen2018',
    color: '#ff8a5c',
    rule: {{
      from: {c18_from},
      to: {c18_to},
      label: '≈ 80 km',
      source:
        'Christoffersen et al. 2018, abstract: "lakes as far as 80 km apart form expansive networks and drain in rapid ' +
        'succession" (also Discussion: "as far as 80 km apart"; Stevens 2024 §1 quotes it as ~80 km). EXACT number; the ' +
        'rule is a true-length 80 km scale bar laid W–E along the southern edge of the digitised cascade (the {c18_lake_n} digitised lakes span {c18_span} km).',
    }},
  }},
  {{
    id: 'lai2021',
    color: '#c7a6ff',
    rule: {{
      from: [68.72, -49.5],
      to: [68.72, -49.5],
      label: 'R ≈ 2–3 km',
      source:
        'Lai et al. 2021, Fig. 3a table: blister radius R = 3.2 km (North Lake 2006), 2.9 (South Lake 2009), 2.4 (Lake F ' +
        '2010), 1.8 (North Lake 2011), 2.2 (North Lake 2012). EXACT. Drawn as circles of radius R, not a rule.',
    }},
  }},
  {{
    id: 'stevens2024',
    color: '#5fe3c0',
    rule: {{
      from: {s24_from},
      to: {s24_to},
      label: '≲ 3 km',
      source:
        'Stevens et al. 2024 §4: "the up-flow, elastic stress-coupling length scale is short: no more than 3 km inland of ' +
        'the center of the draining lake"; rm = 2.2 km (2011) and 1.9 km (2012) for L1A. EXACT number; rule = 3 km true ' +
        'length from the L1A centre (68.72 °N 49.50 °W, the paper) due east (up-flow).',
    }},
  }},
  {{
    id: 'stevens2026',
    color: '#6cb8ff',
    rule: {{
      from: {s26_from},
      to: {s26_to},
      label: '≈ 5 km',
      source:
        'Stevens et al. 2026: the limit is "a few ice thicknesses" (ice {l2a_h} km thick at L2A); their one plausible inland ' +
        'trigger is L2A → L2C, "~5 km inland of L2A" (2022, slippery-patch mechanism). EXACT number; rule = 5 km true length ' +
        'from L2A (FASTER centre, lakes_cluster) due east. NOTE: "≈ 5 km" is our reading of "a few ice thicknesses".',
    }},
  }},
]

// ─── Christoffersen et al. 2018 (Nat. Commun. 9:1064) ─────────────────
// All DIGITISED — the paper publishes no coordinates for its model grid.
// Registration: Fig. 4a's off-ice area matched to the BedMachine v6 ice
// mask (95 % of 0.5-km cells) with the model grid on UTM 22N,
// (x, y) km → (523.25 + x, 7404.0 + y) km, translation only (±1 km).

/** The CISM model domain: 9000 km² (text) = 120 × 75 km (Fig. 1a axes). DIGITISED (registered). */
export const C18_DOMAIN: LatLon[] = {c18_domain}

/** The tensile shock: ΔRxx ≥ 50 kPa after the 8–10 June 2010 drainages
 *  (Fig. 4h), colour-matched to the figure's colour bar. DIGITISED:
 *  {c18_shock_area} km² here vs 925 km² in the paper's text. Rings largest first. */
export const C18_SHOCK: LatLon[][] = {c18_shock}

/** The cascade of 6–10 June 2010: the {c18_lake_n} lakes that drained (43 on 6 June,
 *  30 on 7 June, 51 over 8–10 June — the magenta dots of Fig. 4a, d, g).
 *  DIGITISED (distance-transform maxima on the figure rasters, ±1 km; in the densest
 *  clusters a dot can be missed or doubled). */
export const C18_LAKES: LatLon[] = {c18_lakes}

// ─── Lai et al. 2021 (Nat. Commun. 12:3955) ───────────────────────────
// Supplementary Table 1 (positions, 0.01°) and the Fig. 3a table (R). EXACT.
export const L21_LAKES: {{ name: string; at: LatLon; rKm: number[] }}[] = [
  {{ name: 'North Lake', at: [68.72, -49.5], rKm: [3.2, 1.8, 2.2] }},
  {{ name: 'South Lake', at: [68.57, -49.37], rKm: [2.9] }},
  {{ name: 'Lake F', at: [67.01, -48.74], rKm: [2.4] }},
]

// ─── Stevens et al. 2024 (JGR Earth Surf. 129, e2023JF007481) ─────────
/** L1A–L1D, the paper's §1 and Appendix (0.01°). EXACT. */
export const S24_LAKES: {{ name: string; at: LatLon }}[] = [
  {{ name: 'L1A', at: [68.72, -49.5] }},
  {{ name: 'L1B', at: [68.7, -49.53] }},
  {{ name: 'L1C', at: [68.75, -49.51] }},
  {{ name: 'L1D', at: [68.77, -49.44] }},
]
/** The 2012 GPS array: 16 main-array receivers + FL01, FL02, FL06
 *  (a-priori coordinates, goodnesglaciers/lake_strain
 *  NIF_L1A/apcoords_lle_2012_FLOW.mat). EXACT. */
export const S24_STATIONS: LatLon[] = {s24_stations}

// ─── Stevens et al. 2026 (Nat. Commun. 17:4598) ───────────────────────
/** The subglacial-catchment ROI: {s26_roi_area} km² (the paper: 7189 km²).
 *  EXACT — lakes_cluster paperfig1_map_fullROI_260122.m, EPSG:3413 km from
 *  the M1 moulin (68.72 °N 49.53 °W), densified along its edges. */
export const S26_ROI: LatLon[] = {s26_roi}
/** The 23 GNSS receivers (22 after 2023 attrition): name, lat, lon —
 *  apcoords_lle_2023.mat, the same list as config/fieldwork.ts. EXACT. */
export const S26_STATIONS: [string, number, number][] = {s26_stations}
/** Every lake in the ROI that drained by hydro-fracture, 2022 + 2023
 *  ({s26_hf_n}; the FASTER catalogue's 250416 version — the paper's final
 *  count is 52): lat, lon, year. EXACT (the authors' catalogue). */
export const S26_HF: [number, number, number][] = {s26_hf}
/** Named lakes: the 2022 C1 cluster (L1A, L1B, L72, L47, L34) and the
 *  1150-m instrumented lakes L2A–C. EXACT (FASTER centres; names from the
 *  cluster scripts' figure labels). */
export const S26_NAMED: [string, number, number][] = {s26_named}
'''


if __name__ == '__main__':
    main()
