#!/usr/bin/env python3
"""Build the Sentinel-2 basemap for the Extras section.

Pulls Sentinel-2 L2A raw reflectance bands (B04 red, B03 green, B02
blue, 10 m) from Microsoft Planetary Computer, mosaics them in GDAL's
/vsicurl/ streaming mode, reprojects from per-tile UTM to
equirectangular WGS84, applies the standard L2A surface-reflectance stretch (band ÷ 10000,
i.e. 0–10000 → 0–255) so the ice has real headroom and visible
texture (lakes, melt patterns, crevasse fields) instead of the
washed-out look the TCI gives, and writes a 4-channel RGBA PNG plus
a final lossy WebP. Nodata pixels (outside the satellite swath) come
out transparent so the global ESRI basemap shows through in the Vue
SVG.

The flight was 2023-09-01 but that day had a swath edge running
straight through the AOI, leaving the flight area in nodata. 2023-09-10
is the nearest mostly-cloud-free pass that fully covers the flight
point (0.4 % cloud on tile 22WEB). Surface conditions a week later
still show the same supraglacial-lake population.

Output: a PNG (lossless RGBA, ~7 MB) plus a sibling WebP file (same
basename, ~800 KB) ready to upload to R2 as
    extras/extras_basemap_sentinel2_<DATE>.webp

Usage:
    python3 tools/build_extras_basemap.py [--out OUT.png]

Requirements: GDAL CLI tools + cwebp.

If the system Python has no usable CA bundle (common with the macOS
framework Python), the STAC query fails with CERTIFICATE_VERIFY_FAILED.
Run it as:

    SSL_CERT_FILE=$(python3 -c 'import certifi;print(certifi.where())') \
        python3 tools/build_extras_basemap.py --preset wide

(gdalwarp streams the COGs over its own curl and is unaffected.)
"""

from __future__ import annotations
import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

# Element-84's earth-search STAC API points at AWS Open Data's
# sentinel-cogs bucket (public, no auth). We tried Planetary Computer
# first but their STAC has been flaking; Element-84 is more reliable
# and the underlying COGs are the same.
STAC_SEARCH = "https://earth-search.aws.element84.com/v1/search"

# AOI is defined in local-tangent-plane meters around the flight
# centroid, not lat/lon. Reprojecting to a local CRS (rather than
# WGS84/equirectangular) avoids the 2.7× horizontal stretch you get
# at high latitudes from equirectangular, so circles look round and
# tracks/lakes are physically proportioned in the SVG. Same
# constants below also live in SectionExtras.vue so the Vue side can
# project GPX points into the matching coord system.
LAT_C = 68.59
LON_C = -48.88

# ── PRESETS ───────────────────────────────────────────────────────────────
# Two basemaps share ONE projection origin (LAT_C, LON_C), so a point's
# metres are the same number in both and config/fieldwork.ts needs only one
# set of projection helpers:
#
#   detail — the original 50 × 30 km crop at S2-native 10 m/px. The
#            Introduction's fly-along lands on this image, and the director
#            judged that landing near-perfect, so its date does NOT change.
#   wide   — the whole 2023-09-01 flying day. The day track runs
#            x -91.4..13.3 km, y -74.0..12.3 km — from Ilulissat out to the
#            lake cluster — so the detail crop holds only the last few
#            kilometres of it. 20 m/px keeps the file near the detail crop's
#            size while covering ~13× the area; the detail image draws on
#            top of it, so 10 m is still what you see over the flight area.
#
# Extents are explicit (x0, y0, x1, y1) rather than half-widths because the
# wide box is asymmetric: the day track goes west and south of the origin.
PRESETS = {
    "detail": {
        # 2023-08-18 — only pass within ±2 weeks of the flight that is both
        # atmospherically clean AND catches bright supraglacial lakes at
        # peak melt. The flight day had a swath gap; Sep 10 was hazed;
        # Sep 20 was clearest but the lakes had drained.
        "date": "2023-08-18",
        "tiles": ("22WEB",),
        "extent": (-25000, -15000, 25000, 15000),
        "m_per_px": 10,
        "key": "extras_basemap_sentinel2_{date}",
    },
    "wide": {
        # 2023-08-06 is the one date in the season with all THREE covering
        # tiles acquired and near-cloudless: 22WDB 1.0 %, 22WEA 0.1 %,
        # 22WEB 0.5 %. That matters more than it sounds — S2 swaths mean
        # neighbouring tiles are usually imaged on different days, and a
        # multi-date mosaic would seam visibly across the transit.
        "date": "2023-08-06",
        # Row C tiles for the north edge; missing tiles only warn.
        "tiles": ("22WDA", "22WDB", "22WDC", "22WEA", "22WEB", "22WEC"),
        # 10 km wider on every side than the tracks' box (the director
        # wanted the map's limits a little further out than the GPX
        # tracks', so panning around never runs into an edge).
        # Was (-97000, -80000, 19000, 18000).
        "extent": (-107000, -90000, 29000, 28000),
        "m_per_px": 20,
        "key": "extras_basemap_wide_sentinel2_{date}",
    },
}

# Filled in by main() from the chosen preset.
DATE = PRESETS["detail"]["date"]
PREFERRED_TILES = PRESETS["detail"]["tiles"]
EXTENT = PRESETS["detail"]["extent"]
M_PER_PX = PRESETS["detail"]["m_per_px"]

# Element-84 names bands by colour (red/green/blue) rather than by S2
# band number. Translation table below.
BAND_ASSET = {"B04": "red", "B03": "green", "B02": "blue"}

# proj4 string for the target CRS: azimuthal equidistant projection
# centered on the AOI. Locally indistinguishable from any conformal
# projection (UTM, polar stereo) at this scale, and trivial to
# replicate in JS without adding proj4js.
# The SITE's own frame, exactly (config/fieldwork.ts: x = R·Δλ·cos φ₀,
# y = R·Δφ on the sphere R = 6378137): equirectangular with the standard
# parallel at φ₀. The aeqd used earlier agreed with it to
# the pixel over the ±25 km crop but is a different projection over the
# 116 × 98 km wide box.
TARGET_SRS = f"+proj=eqc +lat_ts={LAT_C} +lat_0={LAT_C} +lon_0={LON_C} +R=6378137 +units=m"

# Same sphere + local-tangent mapping as config/fieldwork.ts, so a
# point's metres mean the same thing on both sides.
R_EARTH = 6378137
DEG2RAD = math.pi / 180

# L2A surface reflectance is stored as uint16 × 10000 (so 0.0–1.0 → 0–
# 10000). Straight linear scale to 0–255: ice at ~0.7–0.95 reflectance
# becomes byte 179–242 (bright but with headroom), bare rock at
# ~0.05–0.20 becomes 13–51, supraglacial lakes at ~0.10–0.40 become
# 25–102 — natural relative brightness with no saturation.
STRETCH_LO = 0
STRETCH_HI = 10000
# Fresh snow in September reflects ABOVE 1.0 in L2A (a quarter of the
# 10 Sep pixels clipped at white, and the image read as washed out).
# `--stretch auto` (the default) raises the top of the
# stretch so the 99.5th percentile of B03 over the DETAIL box lands at
# byte ~242, never lowering it below 10000 — so the clean August passes
# come out exactly as before and only the bright ones change.
#
# RECIPE for a date: build `--preset detail` with auto, read the printed
# "stretch top = N", then build `--preset wide --stretch N` — the two
# images must share ONE stretch or the feathered inset shows as a
# brightness step. (Auto on the wide measures the same box but at 20 m
# after averaging, and came out 1–10 % different.)
AUTO_P = 99.5
AUTO_TARGET = 242 / 255


def post(url: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode())


def probe_points() -> list[tuple[float, float]]:
    """Lon/lat samples covering EXTENT: the four corners and the centre.

    Element-84's search 500s on a `bbox` and returns nothing for a
    Polygon `intersects` at this size (both checked), but
    Point queries are reliable — so we ask at several points and union
    the tiles that come back.
    """
    x0, y0, x1, y1 = EXTENT
    # A 5 × 5 grid, not just corners + centre: with the 136 × 98 km wide
    # box a 100 km MGRS tile can sit between nine probes and go
    # unfound — the 2 Jul wide came out with a black block where 22WDB
    # should have been.
    xs = [x0 + (x1 - x0) * i / 4 for i in range(5)]
    ys = [y0 + (y1 - y0) * i / 4 for i in range(5)]
    out = []
    for x in xs:
        for y in ys:
            # inverse of the local-tangent mapping used everywhere else
            lat = LAT_C - (y / R_EARTH) / DEG2RAD
            lon = LON_C + (x / (R_EARTH * math.cos(LAT_C * DEG2RAD))) / DEG2RAD
            out.append((lon, lat))
    return out


def list_items() -> dict[str, dict]:
    """Find each preferred tile's STAC item on DATE. Element-84 names
    MGRS tiles via `grid:code` (e.g. "MGRS-22WEB"); we strip the prefix
    to match PREFERRED_TILES."""
    feats = []
    for lon, lat in probe_points():
        body = {
            "collections": ["sentinel-2-l2a"],
            "intersects": {"type": "Point", "coordinates": [lon, lat]},
            "datetime": f"{DATE}T00:00:00Z/{DATE}T23:59:59Z",
            "limit": 50,
        }
        feats.extend(post(STAC_SEARCH, body).get("features", []))
    by_tile: dict[str, dict] = {}
    for f in feats:
        grid = f["properties"].get("grid:code", "")
        tile = grid.split("-", 1)[1] if grid.startswith("MGRS-") else grid
        if tile not in PREFERRED_TILES:
            continue
        cloud = f["properties"].get("eo:cloud_cover", 100.0)
        # A date can carry TWO granules of one tile (2 Jul: 22WEB _0 with
        # 11 % nodata and _1 with 72 %) — prefer the one with more DATA,
        # then the less cloudy. Picking by cloud alone took the sliver and
        # left a black block.
        nodata = f["properties"].get("s2:nodata_pixel_percentage", 0.0)
        key = (nodata, cloud)
        if tile not in by_tile or key < by_tile[tile]["key"]:
            by_tile[tile] = {"item": f, "cloud": cloud, "key": key}
    missing = [t for t in PREFERRED_TILES if t not in by_tile]
    if missing:
        print(f"warning: missing tiles {missing} — alpha will be transparent there", file=sys.stderr)
    if not by_tile:
        sys.exit("no tiles available for this date / AOI")
    return by_tile


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd[:6]), "..." if len(cmd) > 6 else "", file=sys.stderr)
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)


def warp_band(band: str, items: dict, out_path: Path, width: int, height: int) -> None:
    """Mosaic + reproject + crop one band across all tiles.

    `band` is a Sentinel-2 band code ("B04"); Element-84 names assets
    by colour, so BAND_ASSET maps to "red" etc. AWS COG URLs are
    public, no signing needed.
    """
    asset_key = BAND_ASSET.get(band, band.lower())
    inputs: list[str] = []
    for tile, info in items.items():
        href = info["item"]["assets"][asset_key]["href"]
        print(f"  {tile}  {band}  cloud={info['cloud']:.1f}%", file=sys.stderr)
        inputs.append(f"/vsicurl/{href}")
    cmd = [
        "gdalwarp",
        "-t_srs", TARGET_SRS,
        # EXTENT is in the map's frame, y DOWN (south positive); gdalwarp's
        # target y is north-up — negate and swap. Passing the map extent
        # straight through put the whole wide image 62 km south of where
        # the site draws it (the lake-half-cut-off bug; the
        # symmetric detail crop never showed it).
        "-te", str(EXTENT[0]), str(-EXTENT[3]), str(EXTENT[2]), str(-EXTENT[1]),
        "-ts", str(width), str(height),
        "-r", "average",
        "-srcnodata", "0",
        "-dstnodata", "0",
        "-ot", "UInt16",
        "-of", "GTiff",
        "-overwrite",
        "-multi",
        "-wo", "NUM_THREADS=ALL_CPUS",
        "--config", "GDAL_HTTP_TIMEOUT", "120",
        "--config", "VSI_CACHE", "TRUE",
        "--config", "VSI_CACHE_SIZE", "1000000000",
        "--config", "GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR",
        "--config", "CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif,.TIF",
        *inputs,
        str(out_path),
    ]
    run(cmd)


def percentile_from_hist(tif: Path, p: float) -> float:
    """The p-th percentile of a band's non-zero values via `gdalinfo -hist`
    (no numpy in the framework Python)."""
    info = json.loads(subprocess.run(["gdalinfo", "-json", "-hist", str(tif)], check=True, capture_output=True, text=True).stdout)
    h = info["bands"][0]["histogram"]
    counts, lo, hi = h["buckets"], h["min"], h["max"]
    n = len(counts)
    width = (hi - lo) / n
    # skip the zero bucket (nodata)
    counts = list(counts)
    counts[0] = 0 if lo <= 0 < lo + width else counts[0]
    total = sum(counts)
    acc = 0
    for i, c in enumerate(counts):
        acc += c
        if acc >= total * p / 100:
            return lo + (i + 1) * width
    return hi


def scale_to_byte(in_path: Path, out_path: Path, lo: int, hi: int) -> None:
    """Scale a UInt16 band to Byte using the given source range."""
    run([
        "gdal_translate",
        "-scale", str(lo), str(hi), "0", "255",
        "-ot", "Byte",
        "-of", "GTiff",
        "-a_nodata", "0",
        str(in_path), str(out_path),
    ])


def build_alpha(b04_byte: Path, alpha_path: Path) -> None:
    """Derive an opaque/transparent alpha mask from one band's nodata.

    Wherever B04 > 0 (i.e. swath had data → already stretched) → 255.
    Anywhere B04 == 0 (nodata) → 0 (transparent).
    """
    run([
        "gdal_calc.py",
        "-A", str(b04_byte),
        f"--outfile={alpha_path}",
        "--calc=(A>0)*255",
        "--type=Byte",
        "--NoDataValue=0",
        "--quiet",
    ])


def main() -> int:
    if not shutil.which("gdalwarp"):
        sys.exit("gdalwarp not found in PATH")
    if not shutil.which("gdal_calc.py"):
        sys.exit("gdal_calc.py not found in PATH")

    global DATE, PREFERRED_TILES, EXTENT, M_PER_PX

    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", choices=sorted(PRESETS), default="detail",
                    help="detail = the 50x30 km 10 m crop (default, unchanged); "
                         "wide = the whole flying day at 20 m")
    ap.add_argument("--out", default=None)
    ap.add_argument("--stretch", default="auto",
                    help="'auto' (99.5th pct of B03 → byte 242, floor 10000) or a fixed top "
                         "reflectance ×10000, e.g. 10000")
    ap.add_argument("--date", default=None,
                    help="override the preset's date (YYYY-MM-DD); the tiles and "
                         "extent stay. The door's per-date imagery "
                         "is the wide + detail pair built on ONE pass: "
                         "2023-08-06 and 2023-09-15 are the season's only dates "
                         "with all three tiles clean.")
    args = ap.parse_args()

    preset = PRESETS[args.preset]
    DATE = args.date or preset["date"]
    PREFERRED_TILES = preset["tiles"]
    EXTENT = preset["extent"]
    M_PER_PX = preset["m_per_px"]
    out = args.out or (
        f"/tmp/{preset['key'].format(date=DATE.replace('-', ''))}.png"
    )
    args.out = out

    x0, y0, x1, y1 = EXTENT
    print(
        f"preset {args.preset}: {DATE}, tiles {list(PREFERRED_TILES)}, "
        f"x {x0/1000:.0f}..{x1/1000:.0f} km, y {y0/1000:.0f}..{y1/1000:.0f} km "
        f"at {M_PER_PX} m/px around {LAT_C}°N, {LON_C}°W",
        file=sys.stderr,
    )
    items = list_items()
    print(f"matched {len(items)} tiles", file=sys.stderr)

    width = int(round((x1 - x0) / M_PER_PX))
    height = int(round((y1 - y0) / M_PER_PX))

    with tempfile.TemporaryDirectory() as tmpdir:
        tdir = Path(tmpdir)
        # Warp each raw band into the AOI.
        for band in ("B04", "B03", "B02"):
            warp_band(band, items, tdir / f"{band}.tif", width, height)

        hi = STRETCH_HI
        if args.stretch == "auto":
            # Measure over the DETAIL box whichever preset this is, so a
            # date's wide and inset get the SAME stretch (no brightness
            # step at the feather). An empty box (the array in the swath
            # gap) leaves the default.
            dx0, dy0, dx1, dy1 = PRESETS["detail"]["extent"]
            win = tdir / "B03_detail.tif"
            run(["gdal_translate", "-q", "-projwin", str(dx0), str(-dy0), str(dx1), str(-dy1),
                 str(tdir / "B03.tif"), str(win)])
            try:
                p = percentile_from_hist(win, AUTO_P)
                hi = max(STRETCH_HI, int(round(p / AUTO_TARGET)))
            except (KeyError, ZeroDivisionError, subprocess.CalledProcessError):
                hi = STRETCH_HI
        else:
            hi = int(args.stretch)
        print(f"stretch top = {hi} ({'auto' if args.stretch == 'auto' else 'fixed'})", file=sys.stderr)
        # Stretch each band to 8-bit.
        for band in ("B04", "B03", "B02"):
            scale_to_byte(tdir / f"{band}.tif", tdir / f"{band}_b.tif", STRETCH_LO, hi)

        # Build alpha mask from B04's nodata.
        build_alpha(tdir / "B04_b.tif", tdir / "alpha.tif")

        # Combine into RGBA VRT.
        rgba_vrt = tdir / "rgba.vrt"
        run([
            "gdalbuildvrt",
            "-separate",
            "-resolution", "user",
            "-tr", str(M_PER_PX), str(M_PER_PX),
            str(rgba_vrt),
            str(tdir / "B04_b.tif"),
            str(tdir / "B03_b.tif"),
            str(tdir / "B02_b.tif"),
            str(tdir / "alpha.tif"),
        ])

        # Final PNG output with alpha.
        run([
            "gdal_translate",
            "-of", "PNG",
            "-co", "ZLEVEL=9",
            "-co", "WORLDFILE=NO",
            "-b", "1", "-b", "2", "-b", "3", "-b", "4",
            str(rgba_vrt),
            args.out,
        ])

    print(f"wrote {args.out} ({width}×{height})", file=sys.stderr)

    # WebP sidecar — same basename, .webp extension. Preserves the alpha
    # channel and is ~10× smaller than the PNG for typical Greenland
    # imagery (compresses uniform ice cheaply).
    if shutil.which("cwebp"):
        webp_path = Path(args.out).with_suffix(".webp")
        run(["cwebp", "-q", "88", "-quiet", args.out, "-o", str(webp_path)])
        print(f"wrote {webp_path}", file=sys.stderr)
    else:
        print("cwebp not found — skipping WebP sidecar", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
