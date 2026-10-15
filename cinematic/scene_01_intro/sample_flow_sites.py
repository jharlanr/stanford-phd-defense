"""
The five call-outs on the Introduction's "Greenland flows" step (the
director asked for a few key locations on the ice sheet, each with its
average annual velocity beside it): the mean speed of each site, sampled
from the SAME field the drape is coloured from.

DATA (read-only copy, the file build_flow_trails.py reads)
    cinematic/source_data/data/ITS_LIVE_velocity_120m_RGI05A_0000_V02.1.nc
    variable `v` (m/yr): "climatological [2014-2024] velocity" — per pixel a
    weighted least-squares line through the MEAN ANNUAL velocities
    2014-2024, evaluated at its time intercept, 1 Jan 2018. So it is a
    multi-year mean annual speed: what the colour bar shows.
    The drape (shared/greenland_speed_nasa_v1.webp) is this `v`, block-
    averaged 4 x 4 to 480 m, log-interpolated onto the globe's lon/lat
    frame. The 480 m block mean is reproduced here for the check column.

METHOD (per site, the median of `v` over a box in EPSG:3413, NaN excluded)
    point sites  a 2 x 2 km box centred on the marker (289 native pixels).
                 Why not 5 x 5 km: Jakobshavn's trunk is ~5 km wide at half
                 its peak speed, so a 5 km box reaches into the shear
                 margins (10th percentile 1,300 m/yr against 7,200 in the
                 centre); 2 km stays on the trunk (p10-p90 6,400-7,600).
                 Petermann and NEGIS do not care (the 1, 2, 3 and 5 km
                 medians agree within 1 %); Summit is 1.40 at 2 km, 1.47
                 at 5 km — noise level either way.
    Russell      the seasons steps' own Russell / Isunnguata Sermia box
                 (40 x 40 km, 10-50 km inland of the land-terminating
                 margin; bake_velocity_series.REGIONS), because step 2
                 plots that box's monthly speed in m/yr — step 1's number
                 must be the same kind of number.

THE SITES (markers; EPSG:3413 km -> lat/lon printed below)
    jakobshavn   the grounded trunk centreline (max of v across the
                 x = -178 km section), ~10 km above the 2016 front — where
                 the seasons box's downstream edge sits; upstream of where
                 v_error jumps (> 75 m/yr at x <= -184 km, 13 m/yr here) —
                 most likely the zone the 2014-2024 fronts swept.
    petermann    the centre of the seasons' Petermann box (grounding zone).
    russell      the centre of the seasons' Russell box.
    negis        the Northeast Greenland Ice Stream's trunk centreline
                 ~200 km downstream of EastGRIP, where the drape shows the
                 stream as a distinct blue band (115 m/yr in 55 m/yr ice)
                 and before it splits for 79N / Zachariae. (79 N 30 W, the
                 brief's guess, is 35 m/yr — west of the stream.)
    summit       Summit Station, 72.5796 N, 38.4592 W. Its value (1.4
                 m/yr) is at ITS_LIVE's noise level (v_error ~1 m/yr).

CROSS-CHECK against the seasons manifest (NASA MEaSUREs NSIDC-0731 v5,
monthly, 800 m, the SAME boxes): the median over 119 months of each box's
monthly median, next to the ITS_LIVE median over that box.

Run (a Python env with xarray and pyproj):
    nice -n 15 python \
        cinematic/scene_01_intro/sample_flow_sites.py
Prints the table; writes cinematic/data/flow/flow_sites.json (gitignored).
The numbers are copied into website/src/config/flowSites.ts by hand.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import numpy as np
import xarray as xr
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared import CINEMATIC_DIR, SOURCE_DATA, require_source  # noqa: E402

SRC = SOURCE_DATA / "data" / "ITS_LIVE_velocity_120m_RGI05A_0000_V02.1.nc"
SEASONS_MANIFEST = CINEMATIC_DIR.parent / "website" / ".r2-cache" / "intro" / "seasons" / "manifest.json"
OUT = CINEMATIC_DIR / "data" / "flow" / "flow_sites.json"

COARSEN = 4  # build_flow_trails.COARSEN: the drape's 480 m block mean
POINT_HALF_KM = 1.0

# Seasons boxes (bake_velocity_series.REGIONS, EPSG:3413 km [x0, x1, y0, y1]).
SEASON_BOX = {
    "russell": [-215, -175, -2520, -2480],
    "jakobshavn": [-178, -168, -2282, -2274],
    "petermann": [-276, -266, -985, -975],
}
SEASON_KEY = {"russell": "russell_isunnguata", "jakobshavn": "sermeq_kujalleq", "petermann": "petermann"}

# Markers, EPSG:3413 km (x, y) — or lat/lon for Summit.
SITES = {
    "jakobshavn": {"xy_km": (-178.0, -2281.4), "footprint": "point"},
    "petermann": {"xy_km": (-271.0, -980.0), "footprint": "point"},
    "russell": {"xy_km": (-195.0, -2500.0), "footprint": "season_box"},
    "negis": {"xy_km": (350.0, -1374.0), "footprint": "point"},
    "summit": {"latlon": (72.5796, -38.4592), "footprint": "point"},
}


def sig2(v: float) -> float:
    """Round to two significant figures (the label's precision)."""
    if v == 0:
        return 0.0
    d = int(np.floor(np.log10(abs(v))))
    return float(round(v, 1 - d))


def main() -> None:
    require_source(SRC)
    ds = xr.open_dataset(SRC, decode_timedelta=False)
    to3413 = Transformer.from_crs("EPSG:4326", "EPSG:3413", always_xy=True)
    to4326 = Transformer.from_crs("EPSG:3413", "EPSG:4326", always_xy=True)
    x_all = ds["x"].values
    y_all = ds["y"].values

    def box_values(x0: float, x1: float, y0: float, y1: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Native 120 m pixels whose centres fall in the box (metres)."""
        sub = ds.sel(x=slice(x0, x1), y=slice(y1, y0))
        return sub["v"].values.astype(np.float64), sub["v_error"].values.astype(np.float64), sub["count"].values

    def block480_median(x0: float, x1: float, y0: float, y1: float) -> float:
        """The drape's 480 m cells (4 x 4 block means on the file's own
        grid, as build_flow_trails.load_coarse) whose centres fall in the
        box — for the tiny 2 km box, the cells overlapping it."""
        j0 = int(np.searchsorted(x_all, x0)) // COARSEN * COARSEN
        j1 = (int(np.searchsorted(x_all, x1)) // COARSEN + 1) * COARSEN
        # y is descending in the file.
        i0 = int(np.searchsorted(-y_all, -y1)) // COARSEN * COARSEN
        i1 = (int(np.searchsorted(-y_all, -y0)) // COARSEN + 1) * COARSEN
        a = ds["v"].isel(y=slice(i0, i1), x=slice(j0, j1)).values.astype(np.float64)
        h, w = a.shape
        a = a[: h - h % COARSEN, : w - w % COARSEN].reshape(h // COARSEN, COARSEN, w // COARSEN, COARSEN)
        with np.errstate(invalid="ignore"):
            b = np.nanmean(a, axis=(1, 3))
        return float(np.nanmedian(b))

    def coarse_box_median(bx: list[int], k: int) -> float:
        """Median of k x k block means (block centres inside the box)."""
        pad = 2e3
        sub = ds.sel(x=slice(bx[0] * 1e3 - pad, bx[1] * 1e3 + pad), y=slice(bx[3] * 1e3 + pad, bx[2] * 1e3 - pad))
        a = sub["v"].values.astype(np.float64)
        xs, ys = sub["x"].values, sub["y"].values
        h, w = a.shape
        a = a[: h - h % k, : w - w % k].reshape(h // k, k, w // k, k)
        with np.errstate(invalid="ignore"):
            b = np.nanmean(a, axis=(1, 3))
        xb = xs[: w - w % k].reshape(-1, k).mean(1)
        yb = ys[: h - h % k].reshape(-1, k).mean(1)
        rows = (yb >= bx[2] * 1e3) & (yb <= bx[3] * 1e3)
        cols = (xb >= bx[0] * 1e3) & (xb <= bx[1] * 1e3)
        return float(np.nanmedian(b[np.ix_(rows, cols)]))

    manifest = json.loads(SEASONS_MANIFEST.read_text()) if SEASONS_MANIFEST.exists() else None

    out = {}
    print(f"{'site':11s} {'lat':>8s} {'lon':>9s}  {'footprint':22s} {'median':>8s} {'p10':>7s} {'p90':>7s} "
          f"{'n':>5s} {'err':>5s} {'480m':>8s}  label")
    for key, s in SITES.items():
        if "latlon" in s:
            lat, lon = s["latlon"]
            x, y = to3413.transform(lon, lat)
        else:
            x, y = s["xy_km"][0] * 1e3, s["xy_km"][1] * 1e3
            lon, lat = to4326.transform(x, y)
        if s["footprint"] == "season_box":
            bx = SEASON_BOX[key]
            x0, x1, y0, y1 = (c * 1e3 for c in bx)
            fp = f"seasons box {bx[1] - bx[0]}x{bx[3] - bx[2]} km"
        else:
            h = POINT_HALF_KM * 1e3
            x0, x1, y0, y1 = x - h, x + h, y - h, y + h
            fp = f"{2 * POINT_HALF_KM:.0f}x{2 * POINT_HALF_KM:.0f} km box"
        v, e, c = box_values(x0, x1, y0, y1)
        ok = np.isfinite(v)
        med = float(np.median(v[ok]))
        p10, p90 = (float(q) for q in np.percentile(v[ok], [10, 90]))
        err = float(np.nanmedian(e))
        b480 = block480_median(x0, x1, y0, y1)
        rec = {
            "lat": round(float(lat), 4),
            "lon": round(float(lon), 4),
            "x_km": round(x / 1e3, 1),
            "y_km": round(y / 1e3, 1),
            "footprint": fp,
            "median_m_yr": round(med, 2),
            "p10": round(p10, 1),
            "p90": round(p90, 1),
            "n_pixels": int(ok.sum()),
            "v_error_median": round(err, 1),
            "median_480m_blocks": round(b480, 2),
            "label_m_yr": sig2(med),
        }
        # Cross-check: ITS_LIVE vs MEaSUREs over the seasons box, at 120 m
        # and block-averaged 7 x 7 (840 m ~ MEaSUREs' 800 m overview).
        if key in SEASON_BOX:
            bx = SEASON_BOX[key]
            vb, _, _ = box_values(*(q * 1e3 for q in bx))
            rec["its_live_seasons_box_median"] = round(float(np.nanmedian(vb)), 1)
            rec["its_live_840m_seasons_box_median"] = round(coarse_box_median(bx, 7), 1)
            if manifest:
                r = manifest["regions"][SEASON_KEY[key]]
                sp = [q for q in r["speed_obs"] if q is not None]
                rec["measures_seasons_box_median_of_months"] = round(statistics.median(sp), 1)
                rec["measures_seasons_box_mean_of_months"] = round(statistics.mean(sp), 1)
                rec["measures_months"] = len(sp)
        out[key] = rec
        print(f"{key:11s} {lat:8.4f} {lon:9.4f}  {fp:22s} {med:8.1f} {p10:7.1f} {p90:7.1f} "
              f"{ok.sum():5d} {err:5.1f} {b480:8.1f}  {rec['label_m_yr']:g}")

    # ITS_LIVE `v` is a mean of ANNUAL means, so the like-for-like MEaSUREs
    # number is the MEAN over the months (the median over months drops the
    # summer speed-up's pull).
    print("\ncross-check over the seasons boxes (m/yr): ITS_LIVE box median at 120 m / 840 m"
          " vs MEaSUREs monthly box medians, mean (median) over the observed months")
    for key in SEASON_BOX:
        r = out[key]
        if "measures_seasons_box_median_of_months" in r:
            its, its8 = r["its_live_seasons_box_median"], r["its_live_840m_seasons_box_median"]
            mea, med = r["measures_seasons_box_mean_of_months"], r["measures_seasons_box_median_of_months"]
            print(f"  {key:11s} ITS_LIVE {its:7.1f} / {its8:7.1f}   MEaSUREs {mea:7.1f} ({med:7.1f}, "
                  f"{r['measures_months']} months)   840 m vs mean {100 * (its8 / mea - 1):+.0f} %")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"source": SRC.name, "variable": "v", "sites": out}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
