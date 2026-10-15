#!/usr/bin/env python
"""Fetch CReSIS radar bed picks over the lake-1951 (2019cw428) AOI.

Step 0 of the MGSIM bed-ensemble experiment: pull every available
ice-penetrating-radar bed pick inside a 50 km x 50 km AOI oriented like
the simulation domain (along-flow frame) and concentric with it (the
domain center sits ~40 m from the lake centroid), at full L2 posting
density (~15 m along-track).

Two-stage crawl of https://data.cresis.ku.edu/data/rds/ (public, no auth):
  1. the decimated per-season "Browse_*" aggregates (csv_good/) discover
     WHICH flight segments cross the AOI;
  2. only those segments' full-density files
     (<season>/csv_good/Data_YYYYMMDD_SS.csv) are then downloaded.
2018/2019 have no top-level aggregates, so their season csv_good/
directories are crawled directly (already full density).

Per the project data rule, this script READS the defense repo's own
copies (cinematic/scene_ch02/output_simdomains/) for the domain
geometry and writes only under cinematic/scene_addl/mgsim/data/ (raw season downloads
cached in gitignored cinematic/source_data/mgsim/raw/cresis/; filtered
picks land in cinematic/scene_addl/mgsim/data/derived/).

Run (any Python env with pandas + pyproj + requests):
    python cinematic/scene_addl/mgsim/scripts/fetch_radar_lines.py

Outputs
-------
data/derived/radar_picks_cw1951_aoi50km.csv   one row per bed pick in the AOI
data/derived/aoi_cw1951.json                  AOI + domain frames (3413 + local)
data/derived/fetch_summary.json               per-season counts + track lengths
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from pyproj import Transformer

BASE = "https://data.cresis.ku.edu/data/rds"

# All Greenland seasons with a top-level csv_good aggregate (1993-2017),
# as the live index listed them when this script was written.
AGG_SEASONS = [
    "1993_Greenland_P3", "1995_Greenland_P3", "1996_Greenland_P3",
    "1997_Greenland_P3", "1998_Greenland_P3", "1999_Greenland_P3",
    "2001_Greenland_P3", "2002_Greenland_P3", "2003_Greenland_P3",
    "2005_Greenland_TO", "2006_Greenland_TO", "2007_Greenland_P3",
    "2008_Greenland_Ground", "2008_Greenland_TO", "2009_Greenland_TO",
    "2010_Greenland_DC8", "2010_Greenland_P3", "2011_Greenland_P3",
    "2011_Greenland_TO", "2012_Greenland_P3", "2013_Greenland_P3",
    "2014_Greenland_P3", "2015_Greenland_C130", "2016_Greenland_G1XB",
    "2016_Greenland_P3", "2016_Greenland_Polar6", "2017_Greenland_P3",
]
# Later seasons publish csv_good only inside the season directory.
DIR_SEASONS = ["2018_Greenland_P3", "2019_Greenland_P3"]

REPO = Path(__file__).resolve().parents[2]
SIMDOMAINS = REPO / "cinematic/scene_ch02/output_simdomains/sim_domains.json"
SIMLAKES = REPO / "cinematic/scene_ch02/output_simdomains/simlakes_CW2019_1951.json"
RAW = REPO / "cinematic/source_data/mgsim/raw/cresis"
DERIVED = REPO / "cinematic/scene_addl/mgsim/data/derived"

LAKE_ID = "CW2019_1951"
TILE_HALF_M = 7375.0      # site analysis tile (14.75 km)
ELMER_HALF_M = 12375.0    # Elmer domain (Lx = 24750 m in the sifs)


def http_get(url: str, tries: int = 3, timeout: int = 300) -> bytes:
    last: Exception | None = None
    for i in range(tries):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            return r.content
        except Exception as e:  # noqa: BLE001 - retry any transport error
            last = e
            if getattr(getattr(e, "response", None), "status_code", 0) == 404:
                break
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"failed after {tries} tries: {url}") from last


def cached_csv(season: str, url: str) -> pd.DataFrame | None:
    """Download-or-reuse one CSV; None on failure/unexpected format."""
    RAW.mkdir(parents=True, exist_ok=True)
    cache = RAW / f"{season}__{url.rsplit('/', 1)[-1]}"
    if not (cache.exists() and cache.stat().st_size > 0):
        try:
            cache.write_bytes(http_get(url))
        except RuntimeError as e:
            print(f"  !! {season}: {e}", file=sys.stderr)
            return None
    df = pd.read_csv(io.BytesIO(cache.read_bytes()))
    df.columns = [c.strip().upper() for c in df.columns]
    if not {"LAT", "LON", "THICK", "BOTTOM"}.issubset(df.columns):
        print(f"  !! {season}: unexpected columns {list(df.columns)}", file=sys.stderr)
        return None
    # Occasional stray rows (repeated headers, padding) arrive as strings.
    for c in ("LAT", "LON", "TIME", "THICK", "ELEVATION", "SURFACE",
              "BOTTOM", "QUALITY", "FRAME"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["LAT", "LON", "THICK", "BOTTOM"])


def load_domain() -> dict:
    lakes = json.load(open(SIMDOMAINS))["lakes"]
    dom = next(l for l in lakes if l["id"] == LAKE_ID)
    centroid_ll = next(
        l for l in json.load(open(SIMLAKES))["lakes"] if l.get("center")
    )["centroid_ll"]
    return {"dom": dom, "centroid_ll": centroid_ll}


def build_frames(dom: dict, centroid_ll: list[float], aoi_half_m: float) -> dict:
    """AOI box + the along-flow local frame, all in EPSG:3413 meters."""
    t = Transformer.from_crs(4326, 3413, always_xy=True)
    cx, cy = t.transform(*centroid_ll)
    corners = np.array([t.transform(lon, lat) for lon, lat in dom["corners_lonlat"]])
    center = corners.mean(axis=0)
    # Corner order is [(-x,-y), (+x,-y), (+x,+y), (-x,+y)] in the local
    # along-flow frame (established in the ch2 build pipeline).
    ex = corners[1] - corners[0]
    ey = corners[3] - corners[0]
    side_x, side_y = np.hypot(*ex), np.hypot(*ey)
    ex, ey = ex / side_x, ey / side_y
    ortho = abs(float(ex @ ey))
    if not (14600 < side_x < 14900 and 14600 < side_y < 14900 and ortho < 0.02):
        raise RuntimeError(
            f"domain frame sanity failed: sides {side_x:.0f}/{side_y:.0f} m, "
            f"|ex.ey|={ortho:.3f}"
        )
    # The AOI is a rotated square in the along-flow frame, concentric
    # with the Elmer domain: |LX|, |LY| <= aoi_half_m.
    sign = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]], dtype=float)
    aoi_corners = center + np.outer(sign[:, 0] * aoi_half_m, ex) \
        + np.outer(sign[:, 1] * aoi_half_m, ey)
    return {
        "epsg": 3413,
        "lake_id": LAKE_ID,
        "old_id": dom["old_id"],
        "centroid_ll": centroid_ll,
        "centroid_3413": [cx, cy],
        "aoi_half_m": aoi_half_m,
        "aoi_definition": "|LX|,|LY| <= aoi_half_m (along-flow frame, "
                          "centered on the domain center)",
        "aoi_corners_3413": aoi_corners.tolist(),
        "aoi_bbox_3413": [float(aoi_corners[:, 0].min()),
                          float(aoi_corners[:, 0].max()),
                          float(aoi_corners[:, 1].min()),
                          float(aoi_corners[:, 1].max())],
        "domain_center_3413": center.tolist(),
        "domain_corners_3413": corners.tolist(),
        "domain_corners_lonlat": dom["corners_lonlat"],
        "flow_angle_deg": dom["flow_angle_deg"],
        "ex_3413": ex.tolist(),
        "ey_3413": ey.tolist(),
        "tile_half_m": TILE_HALF_M,
        "elmer_half_m": ELMER_HALF_M,
        "notes": (
            "local frame: lx = (p - domain_center).ex, ly = (p - domain_center).ey; "
            "+x is along-flow. Elmer DEM coords: dem_x = lx + 12375, "
            "dem_y = ly + 12375 (the sif grid runs 0..24750 m). The published "
            "nc (591x591, 25 m) covers |lx|,|ly| <= 7387.5 m."
        ),
    }


class AoiClipper:
    def __init__(self, frames: dict):
        self.half = frames["aoi_half_m"]
        self.center = np.array(frames["domain_center_3413"])
        self.ex = np.array(frames["ex_3413"])
        self.ey = np.array(frames["ey_3413"])
        # Coarse lon/lat envelope of the ROTATED box so each file filters
        # cheaply before the projection pass.
        corners = np.array(frames["aoi_corners_3413"])
        inv = Transformer.from_crs(3413, 4326, always_xy=True)
        e = np.linspace(0, 1, 9)[:, None]
        ring = np.vstack([
            corners[i] + e * (corners[(i + 1) % 4] - corners[i])
            for i in range(4)
        ])
        lons, lats = inv.transform(ring[:, 0], ring[:, 1])
        self.lon_lo, self.lon_hi = min(lons) - 0.05, max(lons) + 0.05
        self.lat_lo, self.lat_hi = min(lats) - 0.02, max(lats) + 0.02
        self.fwd = Transformer.from_crs(4326, 3413, always_xy=True)

    def clip(self, df: pd.DataFrame, season: str, src: str) -> pd.DataFrame | None:
        df = df[(df.LAT >= self.lat_lo) & (df.LAT <= self.lat_hi)
                & (df.LON >= self.lon_lo) & (df.LON <= self.lon_hi)]
        # THICK==0 rows are surface-only returns (SURFACE==BOTTOM) and
        # nodata is -9999 — neither is a bed pick.
        df = df[(df.THICK > 0) & (df.BOTTOM > -9000)]
        if df.empty:
            return None
        px, py = self.fwd.transform(df.LON.values, df.LAT.values)
        d = np.stack([px - self.center[0], py - self.center[1]], axis=1)
        df = df.assign(X=px, Y=py, LX=d @ self.ex, LY=d @ self.ey)
        df = df[(df.LX.abs() <= self.half) & (df.LY.abs() <= self.half)]
        if df.empty:
            return None
        df = df.assign(SEASON=season, SRC=src)
        df["IN_TILE"] = (df.LX.abs() <= TILE_HALF_M) & (df.LY.abs() <= TILE_HALF_M)
        df["IN_SIMDOMAIN"] = ((df.LX.abs() <= ELMER_HALF_M)
                              & (df.LY.abs() <= ELMER_HALF_M))
        # CReSIS L2 convention: SURFACE/BOTTOM are depths below the platform
        # (BOTTOM - SURFACE == THICK); elevations are ELEVATION minus depth,
        # WGS-84 ellipsoidal.
        if "ELEVATION" in df.columns:
            df["BED_ELEV"] = df.ELEVATION - df.BOTTOM
            df["SURF_ELEV"] = df.ELEVATION - df.SURFACE
        return df


def frame_to_segment(frame: float | int) -> tuple[str, str]:
    f = str(int(frame)).zfill(13)
    return f[:8], f[8:10]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aoi-half-km", type=float, default=25.0,
                    help="half-width of the square AOI around the lake centroid")
    args = ap.parse_args()

    geo = load_domain()
    frames = build_frames(geo["dom"], geo["centroid_ll"], args.aoi_half_km * 1000.0)
    clipper = AoiClipper(frames)

    kept: list[pd.DataFrame] = []

    # ── Stage 1: browse aggregates discover the crossing segments ──
    print(f"AOI: {args.aoi_half_km * 2:.0f} km along-flow-oriented box at "
          f"({frames['centroid_ll'][1]:.4f}N, {frames['centroid_ll'][0]:.4f}E)")
    print(f"stage 1 — scanning {len(AGG_SEASONS)} browse aggregates ...")
    discovered: list[tuple[str, str, str, pd.DataFrame]] = []
    for season in AGG_SEASONS:
        df = cached_csv(season, f"{BASE}/csv_good/Browse_{season}.csv")
        if df is None:
            continue
        hit = clipper.clip(df, season, "browse")
        if hit is None or "FRAME" not in hit:
            continue
        for (date, seg), g in hit.groupby(
                hit.FRAME.map(frame_to_segment)):
            discovered.append((season, date, seg, g))
    print(f"  {len(discovered)} crossing segments in "
          f"{len({d[0] for d in discovered})} seasons")

    # ── Stage 2: full-density files for exactly those segments ──
    print("stage 2 — fetching full-density segment files ...")
    for season, date, seg, browse_rows in discovered:
        df = cached_csv(season, f"{BASE}/{season}/csv_good/Data_{date}_{seg}.csv")
        full = clipper.clip(df, season, "segment") if df is not None else None
        if full is not None:
            kept.append(full)
        else:
            # No full-density file for this segment — keep the browse picks.
            print(f"  ~~ {season} {date}_{seg}: falling back to browse rows")
            kept.append(browse_rows)

    # ── 2018/2019: crawl the season csv_good directories directly ──
    for season in DIR_SEASONS:
        try:
            listing = http_get(f"{BASE}/{season}/csv_good/").decode("utf8", "ignore")
        except RuntimeError as e:
            print(f"  !! {season}: {e}", file=sys.stderr)
            continue
        names = sorted(set(re.findall(r'href="(Data_[^"/]+\.csv)"', listing)))
        print(f"stage 2b — {season}: {len(names)} segment files")
        for n in names:
            df = cached_csv(season, f"{BASE}/{season}/csv_good/{n}")
            if df is None:
                continue
            hit = clipper.clip(df, season, "segment")
            if hit is not None:
                kept.append(hit)

    if not kept:
        print("No picks found in the AOI — nothing written.", file=sys.stderr)
        sys.exit(1)

    allpicks = pd.concat(kept, ignore_index=True)
    dedup_keys = [k for k in ("FRAME", "TIME", "LAT", "LON") if k in allpicks.columns]
    allpicks = allpicks.drop_duplicates(subset=dedup_keys).reset_index(drop=True)

    # QC each season's vertical datum against the published bed (inside the
    # analysis tile, where the repo's nc grid exists). The bulk of the
    # ellipsoid-vs-geoid offset here is ~+28 m; a median residual far beyond
    # that means the season's ELEVATION reference is something else entirely
    # (seen in the ICORDS/ACORDS-era 2003/2005 campaigns) — those picks keep
    # their rows but get DATUM_SUSPECT=True so the conditioning step can
    # rebuild their bed as (surface DEM - THICK) instead.
    qc_median: dict[str, float] = {}
    nc = (REPO / "cinematic/source_data/pnas_sims/"
          "2019cw428_d25km_r2500m_csi6.5e6_tsic_viscous.nc")
    if nc.exists() and "BED_ELEV" in allpicks.columns:
        import xarray as xr
        from scipy.interpolate import RegularGridInterpolator
        ds = xr.open_dataset(nc)
        bed = ds.topo_bed.isel(case=0, level=0)
        itp = RegularGridInterpolator((ds.y.values, ds.x.values), bed.values,
                                      bounds_error=False)
        t = allpicks[allpicks.IN_TILE]
        pub = itp(np.stack([t.LY.values, t.LX.values], 1))
        res = pd.Series(t.BED_ELEV.values - pub, index=t.index)
        qc_median = res.groupby(t.SEASON).median().round(1).to_dict()
    allpicks["DATUM_SUSPECT"] = allpicks.SEASON.map(
        lambda s: abs(qc_median.get(s, 28.0) - 28.0) > 150.0)

    summary: dict[str, dict] = {}
    for season, g in allpicks.groupby("SEASON"):
        g = g.sort_values(["FRAME", "TIME"]) if "TIME" in g else g
        step = np.hypot(np.diff(g.X.values), np.diff(g.Y.values))
        same = (g.FRAME.values[1:] == g.FRAME.values[:-1]) if "FRAME" in g \
            else np.ones(len(g) - 1, bool)
        dates = sorted({str(int(f))[:8] for f in g.FRAME.unique()}) if "FRAME" in g else []
        summary[season] = {
            "n_aoi": int(len(g)),
            "n_simdomain": int(g.IN_SIMDOMAIN.sum()),
            "n_tile": int(g.IN_TILE.sum()),
            "track_km_aoi": round(float(step[(step < 200) & same].sum() / 1000), 1),
            "n_frames": int(g.FRAME.nunique()) if "FRAME" in g else None,
            "src": sorted(g.SRC.unique()),
            "bed_qc_median_m": qc_median.get(season),
            "datum_suspect": bool(g.DATUM_SUSPECT.iloc[0]),
            "dates": dates,
        }

    DERIVED.mkdir(parents=True, exist_ok=True)
    out_csv = DERIVED / "radar_picks_cw1951_aoi50km.csv"
    cols = [c for c in ("SEASON", "SRC", "FRAME", "TIME", "LAT", "LON", "X", "Y",
                        "LX", "LY", "THICK", "ELEVATION", "SURFACE", "BOTTOM",
                        "BED_ELEV", "SURF_ELEV", "QUALITY", "IN_TILE",
                        "IN_SIMDOMAIN", "DATUM_SUSPECT") if c in allpicks.columns]
    allpicks[cols].to_csv(out_csv, index=False, float_format="%.3f")
    json.dump(frames, open(DERIVED / "aoi_cw1951.json", "w"), indent=1)
    json.dump(summary, open(DERIVED / "fetch_summary.json", "w"), indent=1)

    print(f"\n{'season':<24}{'AOI':>8}{'simdom':>8}{'tile':>7}{'km':>8}  dates")
    for s in sorted(summary):
        r = summary[s]
        print(f"{s:<24}{r['n_aoi']:>8}{r['n_simdomain']:>8}{r['n_tile']:>7}"
              f"{r['track_km_aoi']:>8.1f}  {','.join(r['dates'][:4])}"
              f"{'…' if len(r['dates']) > 4 else ''}")
    print(f"\nTOTAL picks: AOI {len(allpicks)}, "
          f"sim domain {int(allpicks.IN_SIMDOMAIN.sum())}, "
          f"analysis tile {int(allpicks.IN_TILE.sum())}")
    print(f"wrote {out_csv.relative_to(REPO)}")


if __name__ == "__main__":
    main()
