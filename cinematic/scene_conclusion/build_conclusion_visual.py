"""Bake the Conclusion visual: the 2019 season's drainages and their reach
(the re-bake; v1 was the cascade version).

The director asked for a visual (or one combined visual) for the
conclusions page and for the conclusions thumbnail in the menu card, and
then for the drainages to be shown in a date-accurate order, by observed
drainage date: the conclusion must not imply that any one lake triggers
another, but keep the same picture and the same animation, with the lakes
draining (no connecting line segments) on their observed drainage dates —
for the hydrofracture lakes alone, and for HF + MD lakes, with a toggle
between the two.

So there is no cascade any more: no lake fires another. Each lake drains
on its own OBSERVED day; the renderer (website/src/components/
ConclusionReach.vue, page + menu-card modes) plays the season 1 May →
30 Sep and lets the reaches overlap where they happen to. This script
precomputes everything into one small JSON so the browser only projects
and animates.

The figure, in the thesis's own numbers:
  * the stage — central-west Greenland's 2019 lake population as the
    site's Chapter 3 shows it (ch03/essd_lakes_2019.json: the ESSD hand
    labels, five mechanism classes, Dunmire outlines), in a local
    azimuthal-equidistant frame centred on lake CW2019_2394, north up,
    km; BedMachine v6 ice margin, land and sea, 200 m surface contours.
  * the claim — Christoffersen et al. 2018, "tens of km": a 30 km circle.
  * the reaches — CW2019_2394 (Chapter 2's lake): from the PNAS
    lake-specific runs (ch02/results/impl_lakes.json, the 100 kPa
    contour's upstream reach): elastic 2.65 km (peak 1.11 MPa), viscous
    >= 7.38 km (peak 0.51 MPa; the contour reaches the 7.375 km window
    edge, so a lower bound). Every other draining lake's viscous reach is
    that number scaled by Chapter 1's absolute coupling length at the
    lake (ACL ratio), sampled from the twins-grid cache the ch01 ACL map
    is drawn from (n = 1, gamma = 0.1, tau_val = 30 kPa, ell = 10 km —
    the hero parameters of ch01/acl_map.png):
        ACL = x_bl ln(tau_max / tau_val),
        x_bl = h sqrt(2/gamma + 4/3),  tau_max = rho g alpha ell / 4.
    The elastic reach stays 2.65 km everywhere (the seven PNAS lakes'
    elastic reaches span only 2.35–3.10 km).
  * the dates — each HF and MD lake's observed drainage day (below).
    ND, LD and CD lakes carry no day: they never drain in this figure
    (LD and CD lakes do drain in nature; the director scoped the figure to
    HF and HF + MD).

THE DRAINAGE-DAY RULE (one rule for HF and MD):
  From the lake's daily water fraction p_water (the `pw` series in
  ch03/essd_lakes_2019.json: Sentinel-2 S2_water, 1 May – 30 Sep 2019,
  forward/back-filled over unusable days, 0–100), the drainage day is
      the first day on which the lake holds less than half of the most
      water it has held so far — counted only once that running maximum
      has reached half of the lake's season peak.
  For a hydrofracture lake that is the day of its one big drop (it falls
  through half in a single observation; the rule and "the largest
  single-day drop" agree within a day for 153 of the 184 HF lakes, and
  87 of the 163 MD lakes — printed). For a
  moulin-drainage lake, whose decline is gradual, it is the day the
  decline crosses half — the middle of the drainage, not its first or
  last day.
  Why not the largest single-day drop, as first proposed: that picks
  the wrong event whenever a lake has a later, larger artefact — a
  late-August blip (CW2019_2366: 79 % on days 122–128, back to 0 on day
  129, long after the June drainage that Dunmire et al. date to day 37;
  the rule gives day 46), or a refill that freezes over or drains again
  late in the season (CW2019_1524: 97 → 0 on day 125 vs its 70 → 21
  drainage on day 63, which the rule takes). The half-of-running-max
  form also ignores early noise below half the peak (CW2019_2445: 38 %
  on days 4–6, 1 % on day 7; drainage day 91).
  The same rule for MD lakes is the brief's half-peak crossing, taken
  against the running maximum so a later refill or blip cannot move it.
  Because the series is forward-filled, a drop is seen on the first
  clear image after the drainage; the day is that observation's day.
  Cross-check (printed): Dunmire et al.'s own `drain_date` (the
  labels_2019_volumes.geojson property, day of year; present for 128 of
  the 184 HF lakes and 55 of the 163 MD lakes — the rest have none) sits
  a median 3 days EARLIER than this rule and within 7 days of it for
  95 % of those HF lakes and 91 % of those MD lakes (one lake of each
  class differs by > 14 days) — the forward-fill lag. The pw rule is used because
  it covers every lake and is the same series Chapter 3's population map
  plays (a lake shrinks there on the day it drains here).

Inputs (copies only):
  website/.r2-cache/ch03/essd_lakes_2019.json
  website/.r2-cache/ch02/results/impl_lakes.json
  cinematic/data/twins_grid_cache.npz   (scene_ch01/build_twins_grid.py;
                                         --twins-cache to point elsewhere)
  cinematic/source_data/data/BedMachineGreenland-v6.nc
  cinematic/source_data/essd/dunmire/labels_2019_volumes.geojson
                                        (the drain_date cross-check only)

Run (a Python env with pyproj, shapely, contourpy, scipy, xarray):
  nice -n 15 python -u \
      cinematic/scene_conclusion/build_conclusion_visual.py
Then (new bytes = new name; never overwrite a published key — v1, the
cascade version, stays in R2 untouched):
  rclone copyto cinematic/data/conclusion/reach_v2.json \
      r2:<bucket>/conclusion/reach_v2.json \
      --header-upload 'Cache-Control: public, max-age=31536000, immutable'
  mkdir -p website/.r2-cache/conclusion && \
      cp cinematic/data/conclusion/reach_v2.json website/.r2-cache/conclusion/
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared import BEDMACHINE_PATH, CINEMATIC_DIR, SOURCE_DATA, require_source  # noqa: E402

sys.stdout.reconfigure(line_buffering=True)

REPO = CINEMATIC_DIR.parent
R2 = REPO / "website" / ".r2-cache"
LAKES_JSON = R2 / "ch03" / "essd_lakes_2019.json"
IMPL_JSON = R2 / "ch02" / "results" / "impl_lakes.json"
TWINS_CACHE = CINEMATIC_DIR / "data" / "twins_grid_cache.npz"
DUNMIRE_GJ = SOURCE_DATA / "essd" / "dunmire" / "labels_2019_volumes.geojson"
OUT = CINEMATIC_DIR / "data" / "conclusion" / "reach_v2.json"

SOURCE = "CW2019_2394"
CLASS_ORDER = ["ND", "HF", "MD", "LD", "CD"]  # the site's order (essd json)
DRAINING = ("HF", "MD")  # the classes this figure drains (the director's scope)

# Window baked around the source lake (km, local frame). The page shows
# ~±36 km, the menu card a wide strip; both fit inside.
HALF_X, HALF_Y = 80.0, 52.0
LIT_KM = 30.0  # Christoffersen et al. 2018, "tens of km"
NUNATAK_KM2 = 6.0  # ice-free islands in the sheet smaller than this are filled

# Chapter 1 hero parameters (build_acl_maps.py / build_twins_grid.py)
RHO, G = 917.0, 9.81
GAMMA, ELL_M, TAU_VAL_KPA = 0.1, 10_000.0, 30.0

# Quantisation: positions in 0.01 km (10 m) integers.
Q = 100.0


def q(v: float) -> int:
    return int(round(v * Q))


def drainage_day(pw) -> int:
    """The first day the lake holds less than half of the most water it has
    held so far, once that running maximum has reached half its season
    peak (see the module docstring). -1 when it never happens."""
    s = np.asarray(pw, float)
    peak = s.max()
    if peak <= 0:
        return -1
    run = np.maximum.accumulate(s)
    hit = np.where((run >= 0.5 * peak) & (s < 0.5 * run))[0]
    return int(hit[0]) if len(hit) else -1


def largest_drop_day(pw) -> int:
    """The first proposal, kept for the printed comparison only."""
    return int(np.argmin(np.diff(np.asarray(pw, float)))) + 1


def local_transformer(lon0: float, lat0: float):
    from pyproj import Transformer

    return Transformer.from_crs(
        "EPSG:4326",
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +datum=WGS84 +units=km",
        always_xy=True,
    )


def acl_km(h: np.ndarray, alpha_deg: np.ndarray) -> np.ndarray:
    """Chapter 1's absolute coupling length (n = 1) at the hero parameters."""
    x_bl = h * np.sqrt(2.0 / GAMMA + 4.0 / 3.0)
    tau_max = RHO * G * np.radians(alpha_deg) * ELL_M / 4.0 / 1e3
    out = np.zeros_like(h)
    ok = np.isfinite(tau_max) & (tau_max > TAU_VAL_KPA)
    out[ok] = x_bl[ok] * np.log(tau_max[ok] / TAU_VAL_KPA) / 1e3
    out[~np.isfinite(h)] = np.nan
    return out


def sample_twins(cache_path: Path, lon: np.ndarray, lat: np.ndarray):
    """h [m] and alpha [deg] at points, from the Ch.1 twins-grid cache
    (BedMachine thickness + flow-direction surface slope, 1.5 km grid)."""
    from pyproj import Transformer
    from scipy.interpolate import RegularGridInterpolator

    if not cache_path.exists():
        raise SystemExit(
            f"Missing {cache_path}\n"
            "Run cinematic/scene_ch01/build_twins_grid.py once (it writes the cache),\n"
            "or pass --twins-cache <path to an existing twins_grid_cache.npz>."
        )
    c = np.load(cache_path)
    gx, gy = c["x"], c["y"]
    px, py = Transformer.from_crs("EPSG:4326", "EPSG:3413", always_xy=True).transform(lon, lat)

    def at(field):
        f = RegularGridInterpolator(
            (gy[::-1], gx), field[::-1, :].astype(float), bounds_error=False, fill_value=np.nan
        )
        return f(np.c_[py, px])

    return at(c["h"]), at(c["alpha"])


def outer_ring(rings) -> list:
    """Largest ring of a lake's outline (holes / slivers dropped)."""
    best, best_a = None, -1.0
    for r in rings:
        pts = np.asarray(r, float)
        if pts.ndim != 2 or len(pts) < 3:
            continue
        a = abs(np.dot(pts[:-1, 0], pts[1:, 1]) - np.dot(pts[1:, 0], pts[:-1, 1]))
        if a > best_a:
            best, best_a = pts, a
    return best


def bedmachine_layers(tr_local, lon0: float, lat0: float):
    """Ice margin line, ice-free land and ocean polygons, and 200 m
    surface contours, in the local frame, clipped to the window."""
    import contourpy
    import xarray as xr
    from pyproj import Transformer
    from scipy.ndimage import gaussian_filter
    from shapely.geometry import LineString, Polygon, box
    from shapely.ops import unary_union

    to_ll = Transformer.from_crs("EPSG:3413", "EPSG:4326", always_xy=True)
    to_ps = Transformer.from_crs("EPSG:4326", "EPSG:3413", always_xy=True)
    from_local = Transformer.from_crs(
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +datum=WGS84 +units=km", "EPSG:4326", always_xy=True
    )
    # 3413 bbox covering the (rotated) local window, with a margin
    cx = np.array([-1, 1, 1, -1]) * (HALF_X + 8)
    cy = np.array([-1, -1, 1, 1]) * (HALF_Y + 8)
    lo, la = from_local.transform(cx, cy)
    px, py = to_ps.transform(lo, la)
    ds = xr.open_dataset(require_source(BEDMACHINE_PATH))
    sub = ds.sel(x=slice(px.min(), px.max()), y=slice(py.max(), py.min()))
    mask = sub["mask"].values.astype(np.int8)
    surf = sub["surface"].values.astype(float)
    X, Y = np.meshgrid(sub["x"].values.astype(float), sub["y"].values.astype(float))
    print(f"BedMachine subset {mask.shape} at 150 m")

    window = box(-HALF_X, -HALF_Y, HALF_X, HALF_Y)

    def to_local(seg: np.ndarray) -> np.ndarray:
        lo_, la_ = to_ll.transform(seg[:, 0], seg[:, 1])
        x_, y_ = tr_local.transform(lo_, la_)
        return np.c_[x_, y_]

    def lines_of(field: np.ndarray, level: float, tol: float) -> list:
        gen = contourpy.contour_generator(X, Y, field, name="serial")
        out = []
        for seg in gen.lines(level):
            if len(seg) < 3:
                continue
            ls = LineString(to_local(seg)).intersection(window)
            for part in getattr(ls, "geoms", [ls]):
                if part.is_empty or part.length < 2.0:
                    continue
                s = part.simplify(tol)
                out.append([v for xy in s.coords for v in (q(xy[0]), q(xy[1]))])
        return out

    def polys_of(field: np.ndarray, lo_: float, hi_: float, tol: float) -> list:
        gen = contourpy.contour_generator(X, Y, field, name="serial", fill_type="OuterOffset")
        polys = []
        for pts, offs in zip(*gen.filled(lo_, hi_)):
            rings = [to_local(pts[offs[k]:offs[k + 1]]) for k in range(len(offs) - 1)]
            if len(rings[0]) < 4:
                continue
            p = Polygon(rings[0], [r for r in rings[1:] if len(r) >= 4]).buffer(0)
            polys.append(p)
        geom = unary_union(polys).intersection(window).simplify(tol)
        out = []
        for g in getattr(geom, "geoms", [geom]):
            if g.is_empty or g.area < 1.0:
                continue
            ring = [v for xy in g.exterior.coords for v in (q(xy[0]), q(xy[1]))]
            holes = [
                [v for xy in h.coords for v in (q(xy[0]), q(xy[1]))]
                for h in g.interiors
                if Polygon(h).area >= 1.0
            ]
            out.append([ring] + holes)
        return out

    from scipy.ndimage import label as cc_label

    # The ice SHEET only: its largest connected piece, nunataks under
    # NUNATAK_KM2 filled — the small ice caps out on the land would read
    # as noise at card size (they become land).
    ice_all = np.isin(mask, (2, 3))
    lab, n = cc_label(ice_all)
    sheet = lab == (1 + int(np.argmax(np.bincount(lab.ravel())[1:]))) if n else ice_all
    holes, nh = cc_label(~sheet)
    if nh:
        sizes = np.bincount(holes.ravel())
        edge = set(np.unique(np.r_[holes[0], holes[-1], holes[:, 0], holes[:, -1]]))
        small = [k for k in range(1, nh + 1) if sizes[k] * 0.0225 < NUNATAK_KM2 and k not in edge]
        sheet = sheet | np.isin(holes, small)
    ice = sheet.astype(float)
    ocean = (mask == 0).astype(float)
    # the ice edge as a line; land and sea as fills (their contrast is
    # the coast, so no separate coast line)
    margin = lines_of(gaussian_filter(ice, 1.0), 0.5, 0.08)
    land = polys_of(gaussian_filter(((~sheet) & (mask != 0)).astype(float), 1.0), 0.5, 1.5, 0.1)
    sea = polys_of(gaussian_filter(ocean, 1.0), 0.5, 1.5, 0.1)
    # surface contours on the ice only (smoothed ~600 m so they read as
    # the sheet's slope, not its crevasse texture)
    s = np.where(ice > 0, surf, np.nan)
    s_f = gaussian_filter(np.nan_to_num(s, nan=0.0), 4.0)
    w_f = gaussian_filter((ice > 0).astype(float), 4.0)
    s_s = np.where(w_f > 0.6, s_f / np.maximum(w_f, 1e-6), np.nan)
    contours = []
    for z in range(200, 2001, 200):
        ls = lines_of(s_s, float(z), 0.12)
        if ls:
            contours.append({"z": z, "lines": ls})
    return dict(margin=margin, land=land, sea=sea, contours=contours)


def month_hist(days: list[int], t0: dt.date) -> dict[str, int]:
    """Drainage days binned by calendar month (May … Sep)."""
    out = {m: 0 for m in ("May", "Jun", "Jul", "Aug", "Sep")}
    for d in days:
        out[(t0 + dt.timedelta(days=d)).strftime("%b")] += 1
    return out


def print_histograms(lakes: list[dict], days: dict[str, int], t0: dt.date, label: str) -> None:
    """Per class: the drainage days by month and as a 10-day text histogram."""
    print(f"\ndrainage days per class — {label}")
    for cls in DRAINING:
        ds = [days[l["id"]] for l in lakes if l["cls"] == cls and days[l["id"]] >= 0]
        none = sum(1 for l in lakes if l["cls"] == cls and days[l["id"]] < 0)
        print(f"  {cls}: n = {len(ds)} (no day: {none}); by month {month_hist(ds, t0)}; "
              f"median {(t0 + dt.timedelta(days=int(np.median(ds)))).strftime('%d %b')}" if ds else f"  {cls}: none")
        hist, edges = np.histogram(ds, bins=np.arange(0, 161, 10))
        for k, n in enumerate(hist):
            a = (t0 + dt.timedelta(days=int(edges[k]))).strftime("%d %b")
            print(f"     {a} +10d {n:3d} {'#' * n}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--twins-cache", type=Path, default=TWINS_CACHE)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    essd = json.loads(LAKES_JSON.read_text())
    lakes = essd["lakes"]
    t0 = dt.date.fromisoformat(essd["t0"])
    n_days = int(essd["days"])
    impl = json.loads(IMPL_JSON.read_text())
    ids = [l["id"] for l in lakes]
    src = ids.index(SOURCE)
    lon0, lat0 = lakes[src]["c"]
    tr = local_transformer(lon0, lat0)

    lon = np.array([l["c"][0] for l in lakes])
    lat = np.array([l["c"][1] for l in lakes])
    x, y = tr.transform(lon, lat)
    xy = np.c_[x, y]
    cls = np.array([l["cls"] for l in lakes])

    # ── the observed drainage days (HF and MD only) ──
    days = {l["id"]: (drainage_day(l["pw"]) if l["cls"] in DRAINING and l["pw"] else -1) for l in lakes}
    print_histograms(lakes, days, t0, "all 2019 CW lakes")
    for c_ in DRAINING:
        sel = [l for l in lakes if l["cls"] == c_]
        same = sum(1 for l in sel if abs(largest_drop_day(l["pw"]) - days[l["id"]]) <= 1)
        print(f"  {c_}: rule = largest single-day drop (±1 day) for {same}/{len(sel)} lakes")
    # the cross-check against Dunmire et al.'s own drain_date (not baked)
    if DUNMIRE_GJ.exists():
        gj = json.loads(DUNMIRE_GJ.read_text())
        doy0 = t0.timetuple().tm_yday
        dd = {f["properties"]["new_id"]: f["properties"].get("drain_date") for f in gj["features"]}
        for c_ in DRAINING:
            diffs = [days[l["id"]] - (dd[l["id"]] - doy0) for l in lakes
                     if l["cls"] == c_ and dd.get(l["id"]) is not None and np.isfinite(dd[l["id"]])]
            n_c = int(np.sum(cls == c_))
            diffs_a = np.abs(diffs)
            print(f"  {c_}: Dunmire drain_date on {len(diffs)}/{n_c}; rule − Dunmire median "
                  f"{np.median(diffs):+.0f} d, within 3 d {np.mean(diffs_a <= 3):.0%}, "
                  f"within 7 d {np.mean(diffs_a <= 7):.0%}, > 14 d: {int(np.sum(diffs_a > 14))}")
    else:
        print(f"(no {DUNMIRE_GJ} — the drain_date cross-check is skipped)")

    # ── the reaches: the source's (PNAS), everyone else's ACL-scaled ──
    models = impl["lakes"][SOURCE]["models"]
    re_km = float(models["elastic"]["upstream100_km"])
    rv_km = float(models["viscous"]["upstream100_km"])
    half_km = float(impl["lakes"][SOURCE]["half_km"])
    pe = float(models["elastic"]["peak_kpa"]) / 1e3
    pv = float(models["viscous"]["peak_kpa"]) / 1e3
    elastic_all = [float(L["models"]["elastic"]["upstream100_km"]) for L in impl["lakes"].values()]
    print(f"\n{SOURCE}: elastic {re_km} km / {pe:.2f} MPa · viscous {rv_km} km / {pv:.2f} MPa "
          f"(window half {half_km} km → lower bound: {rv_km >= half_km - 0.01}); "
          f"drains day {days[SOURCE]} = {(t0 + dt.timedelta(days=days[SOURCE])).strftime('%d %b')}")
    print(f"seven PNAS lakes, elastic reach {min(elastic_all)}–{max(elastic_all)} km")

    h, alpha = sample_twins(args.twins_cache, lon, lat)
    acl = acl_km(h, alpha)
    ratio = acl / acl[src]
    reach = np.where(np.isfinite(ratio) & (ratio > 0), rv_km * ratio, 0.0)
    reach[src] = rv_km
    print(f"ACL at {SOURCE}: {acl[src]:.2f} km (h {h[src]:.0f} m, alpha {alpha[src]:.3f} deg)")

    # ── the lakes in the window: centroid, class, outline, day, reach ──
    from shapely.geometry import Polygon

    inwin = (np.abs(x) <= HALF_X) & (np.abs(y) <= HALF_Y)
    # the source first, so the renderer finds it at index 0
    order = [src] + [i for i in range(len(lakes)) if inwin[i] and i != src]
    out_lakes = []
    for i in order:
        ring = outer_ring(lakes[i]["rings"])
        rx, ry = tr.transform(ring[:, 0], ring[:, 1])
        p = Polygon(np.c_[rx, ry]).buffer(0).simplify(0.03)
        if p.geom_type != "Polygon":
            p = max(p.geoms, key=lambda g: g.area)
        cx, cy = xy[i]
        flat = []
        for vx, vy in list(p.exterior.coords)[:-1]:
            flat += [q(vx - cx), q(vy - cy)]
        day = days[ids[i]]
        out_lakes.append([q(cx), q(cy), CLASS_ORDER.index(cls[i]), flat,
                          day, q(reach[i]) if day >= 0 else 0])

    win = [lakes[i] for i in order]
    print_histograms(win, days, t0, f"the baked window (±{HALF_X:.0f} × ±{HALF_Y:.0f} km)")
    view = [lakes[i] for i in order if np.hypot(*xy[i]) <= 35.5]
    print_histograms(view, days, t0, "the page's round view (r ≤ 35.5 km)")
    rr = [reach[i] for i in order if days[ids[i]] >= 0]
    print(f"draining lakes in the window: {len(rr)}; viscous reach {min(rr):.2f}–{max(rr):.2f} km "
          f"(zero-ACL lakes: {sum(1 for v in rr if v <= 0)})")

    hist = {c_: month_hist([days[l["id"]] for l in win if l["cls"] == c_ and days[l["id"]] >= 0], t0)
            for c_ in DRAINING}

    layers = bedmachine_layers(tr, lon0, lat0)

    out = {
        "about": "the 2019 season's drainages and their reach · build_conclusion_visual.py",
        "frame": {"proj": "aeqd", "lon0": lon0, "lat0": lat0, "units": "km", "q": Q,
                  "half_x": HALF_X, "half_y": HALF_Y},
        "classes": CLASS_ORDER,
        "season": {"t0": essd["t0"], "days": n_days, "draining": list(DRAINING),
                   "rule": "first day pw < half its running max, once that max >= half the season peak",
                   "window_by_month": hist},
        "source": {"k": 0, "id": SOURCE, "day": days[SOURCE],
                   "elastic_km": round(re_km, 2), "viscous_km": round(rv_km, 2),
                   "viscous_lower_bound": bool(rv_km >= half_km - 0.01),
                   "elastic_peak_mpa": round(pe, 2), "viscous_peak_mpa": round(pv, 2),
                   # the figure labels, formatted as Chapter 2's beat 9 prints them
                   # (build_results_eqs.py: one decimal, >= at the window edge)
                   "elastic_txt": f"{re_km:.1f} km",
                   "viscous_txt": (f"≥ {half_km:.1f} km" if rv_km >= half_km - 0.01
                                   else f"{rv_km:.1f} km")},
        "elastic_km": round(re_km, 2),
        "literature": {"cite": "Christoffersen et al. 2018", "km": LIT_KM},
        "acl": {"n": 1, "gamma": GAMMA, "tau_val_kpa": TAU_VAL_KPA, "ell_km": ELL_M / 1e3},
        # [x, y, class, outline (relative), drainage day (-1: none), viscous reach] — 0.01 km
        "lakes": out_lakes,
        **layers,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, separators=(",", ":")))
    n_pts = sum(len(l[3]) // 2 for l in out_lakes)
    print(f"\nwrote {args.out} ({args.out.stat().st_size / 1e3:.1f} kB): {len(out_lakes)} lakes "
          f"({n_pts} outline vertices), {len(layers['margin'])} margin lines, "
          f"{len(layers['land'])} land / {len(layers['sea'])} sea polygons, "
          f"{sum(len(c['lines']) for c in layers['contours'])} contour lines")


if __name__ == "__main__":
    main()
