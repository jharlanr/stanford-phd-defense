"""
Build a hi-resolution Greenland basemap PNG by directly fetching ESRI
World Imagery tiles, stitching in Web Mercator, then reprojecting to
PlateCarree (same lat/lon extent as the legacy basemap).

Bypasses cartopy's GoogleTiles + matplotlib pipeline because at zoom 11
that pipeline deadlocks on 50k tile fetches via its threaded fetcher
(4.4 GB memory, hung pthread_cond_wait inside cartopy's image stitching
for 30+ min before being killed). Direct sequential fetcher with
explicit progress + pyproj reprojection is faster, fully deterministic,
and works.

Output: data/greenland_basemap_hires.png, intended to ship as
        shared/greenland_basemap_hires.png on R2.

Run:
    cd cinematic
    source .venv/bin/activate
    python scene_01_intro/build_greenland_basemap_hires.py
"""

import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

# Unbuffered stdout so progress prints appear immediately when piped.
sys.stdout.reconfigure(line_buffering=True)

import certifi

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cartopy.io.shapereader as shapereader  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import requests  # noqa: E402
from PIL import Image, ImageFilter  # noqa: E402

from shared import CINEMATIC_DIR  # noqa: E402

OUT_DIR = CINEMATIC_DIR / "data"
OUT_DIR.mkdir(exist_ok=True)
TILE_CACHE = OUT_DIR / "_tile_cache"
TILE_CACHE.mkdir(exist_ok=True)
OUT = OUT_DIR / "greenland_basemap_hires.png"

# Tight bounding box around Greenland (matches legacy basemap).
LON_W, LON_E = -75.0, -10.0
LAT_S, LAT_N = 59.0, 84.0

ESRI_URL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}.jpg"
)
# Zoom 10 = ~250 m/pixel ground resolution at Greenland latitudes.
# Supraglacial lakes (~1 km²) → ~4 px each, big enough to read as
# discrete features. ~13k tiles total; sequential fetch ~5 min.
# Zoom 11 would give ~125 m/px (~8 px per lake, crisper) but ~50k
# tiles is too many for ESRI sequential.
ZOOM = int(os.environ.get("BASEMAP_ZOOM", "10"))

# Output dimensions in PlateCarree. Aspect 2.6:1 matches 65° × 25°.
# 16380 wide = just under WebGL's 16384 texture-size ceiling.
OUT_W = 16380
OUT_H = 6300

TILE_SIZE = 256


def lonlat_to_tile(lon: float, lat: float, z: int) -> tuple[int, int]:
    """Web Mercator tile coords for a given lon/lat at zoom z."""
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def tile_nw_lonlat(x: int, y: int, z: int) -> tuple[float, float]:
    """North-west corner of tile (x, y) at zoom z in lon/lat degrees."""
    n = 2 ** z
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n)))
    return lon, math.degrees(lat_rad)


def fetch_tile(z: int, x: int, y: int, session: requests.Session) -> Image.Image:
    """Fetch one tile (with on-disk cache + 3-retry network resilience)."""
    cache_path = TILE_CACHE / f"{z}_{x}_{y}.jpg"
    if cache_path.exists() and cache_path.stat().st_size > 100:
        return Image.open(cache_path)
    url = ESRI_URL.format(z=z, y=y, x=x)
    last_err = None
    for attempt in range(3):
        try:
            r = session.get(url, timeout=15)
            if r.status_code == 200 and len(r.content) > 100:
                cache_path.write_bytes(r.content)
                return Image.open(BytesIO(r.content))
            last_err = f"HTTP {r.status_code}"
        except Exception as e:
            last_err = repr(e)
        time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"failed {url}: {last_err}")


def main() -> None:
    from scipy.ndimage import binary_dilation  # noqa: PLC0415

    print(f"zoom: {ZOOM}")
    print(f"output: {OUT_W} × {OUT_H}")

    # Tile range covering Greenland's lat/lon extent. Web Mercator
    # y is inverted (smaller y = north), so we use (LAT_N, LAT_S) to
    # bracket the y range correctly.
    x_min, y_min = lonlat_to_tile(LON_W, LAT_N, ZOOM)
    x_max, y_max = lonlat_to_tile(LON_E, LAT_S, ZOOM)
    n_tiles = (x_max - x_min + 1) * (y_max - y_min + 1)
    print(f"tile range: x={x_min}..{x_max} ({x_max - x_min + 1}), "
          f"y={y_min}..{y_max} ({y_max - y_min + 1})  → {n_tiles} tiles")

    # Phase 1: download tiles to local cache. No stitching — a full
    # Web Mercator stitched canvas for Greenland at zoom 10 would be
    # 47616 × 76000 px ≈ 11 GB of RGB (Mercator stretches polar
    # latitudes, so the bounding box in Mercator px is much taller
    # than in PlateCarree). Phase 2 will reproject row-by-row by
    # opening just the tiles each row needs.
    tile_jobs = [
        (x, y)
        for x in range(x_min, x_max + 1)
        for y in range(y_min, y_max + 1)
    ]
    session = requests.Session()
    session.headers.update({
        "User-Agent": "defense-basemap-build/1.0 (one-shot, cached)",
    })
    t0 = time.time()
    fetched = 0
    cached = 0
    failed: list[str] = []
    done = 0
    PROGRESS_EVERY = 1000

    def _worker(job):
        x, y = job
        cache_path = TILE_CACHE / f"{ZOOM}_{x}_{y}.jpg"
        already = cache_path.exists() and cache_path.stat().st_size > 100
        if already:
            return (x, y, True, None)
        try:
            fetch_tile(ZOOM, x, y, session)
            return (x, y, False, None)
        except Exception as e:  # noqa: BLE001
            return (x, y, False, repr(e))

    print(f"phase 1: downloading {n_tiles} tiles via 16-thread pool...")
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(_worker, job) for job in tile_jobs]
        for fut in as_completed(futures):
            x, y, was_cached, err = fut.result()
            if err is not None:
                failed.append(f"{x},{y}: {err}")
            elif was_cached:
                cached += 1
            else:
                fetched += 1
            done += 1
            if done % PROGRESS_EVERY == 0 or done == n_tiles:
                elapsed = time.time() - t0
                rate = done / elapsed if elapsed > 0 else 0
                eta = (n_tiles - done) / rate if rate > 0 else 0
                print(f"  done={done}/{n_tiles}  cached={cached} fetched={fetched} "
                      f"failed={len(failed)}  rate={rate:.0f}/s  ETA {eta:.0f}s")
    print(f"phase 1 done in {time.time() - t0:.0f}s.")
    if failed:
        print(f"  {len(failed)} failures, first: {failed[0]}")

    # Phase 2: reproject row-by-row. For each output PlateCarree row,
    # compute the Mercator y range it spans, decode JUST those tile
    # rows (one tile row at a time), and bilinearly sample. Memory
    # caps at ~(186 tiles × 256 × 256 × 3 = ~36 MB per tile row) plus
    # the output strip — never more than a few hundred MB total.
    print("phase 2: reprojecting Web Mercator → PlateCarree row-by-row...")
    n = 2 ** ZOOM
    out_lon = np.linspace(LON_W, LON_E, OUT_W, dtype=np.float64)
    # Per-pixel source-x is constant across rows (PlateCarree lon doesn't
    # depend on row).  Precompute once.
    src_x_per_col = (out_lon + 180.0) / 360.0 * n  # fractional tile-x
    px_per_col = (src_x_per_col - x_min) * TILE_SIZE
    px_per_col = np.clip(px_per_col, 0, (x_max - x_min + 1) * TILE_SIZE - 1.001)
    px0_col = np.floor(px_per_col).astype(np.int32)
    px1_col = px0_col + 1
    fx_col = (px_per_col - px0_col).astype(np.float32)

    rgb = np.zeros((OUT_H, OUT_W, 3), dtype=np.uint8)

    # Tile-row cache: stores decoded (TILE_SIZE rows × stitch_w pixels)
    # RGB strips by integer tile-y. LRU-ish — keep at most 4 in memory.
    strip_cache: dict[int, np.ndarray] = {}
    STRIP_CACHE_SIZE = 4

    def get_strip(ty: int) -> np.ndarray:
        """Decode + cache a horizontal strip of all tiles at tile-y=ty.
        Returns a (TILE_SIZE, stitch_w, 3) uint8 array."""
        if ty in strip_cache:
            return strip_cache[ty]
        if len(strip_cache) >= STRIP_CACHE_SIZE:
            strip_cache.pop(next(iter(strip_cache)))
        stitch_w = (x_max - x_min + 1) * TILE_SIZE
        strip = np.zeros((TILE_SIZE, stitch_w, 3), dtype=np.uint8)
        for xi, x in enumerate(range(x_min, x_max + 1)):
            cache_path = TILE_CACHE / f"{ZOOM}_{x}_{ty}.jpg"
            if cache_path.exists() and cache_path.stat().st_size > 100:
                try:
                    tile = np.asarray(Image.open(cache_path).convert("RGB"))
                    strip[:, xi * TILE_SIZE:(xi + 1) * TILE_SIZE, :] = tile
                except Exception:
                    pass  # leave as black
        strip_cache[ty] = strip
        return strip

    t1 = time.time()
    for row in range(OUT_H):
        lat = LAT_N - (LAT_N - LAT_S) * (row / (OUT_H - 1))
        lat_rad = math.radians(lat)
        src_y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
        py = (src_y - y_min) * TILE_SIZE
        py = max(0.0, min(py, (y_max - y_min + 1) * TILE_SIZE - 1.001))
        py0 = int(math.floor(py))
        py1 = py0 + 1
        fy = py - py0

        # Tile-y for the two neighbouring source rows.
        ty0 = y_min + (py0 // TILE_SIZE)
        ty1 = y_min + (py1 // TILE_SIZE)
        strip0 = get_strip(ty0)
        strip1 = get_strip(ty1) if ty1 != ty0 else strip0

        # Local pixel offsets within each strip (0..255).
        ly0 = py0 % TILE_SIZE
        ly1 = py1 % TILE_SIZE if ty1 != ty0 else (py1 % TILE_SIZE)

        # Bilinear: 4 corner samples per output column, per channel.
        c00 = strip0[ly0, px0_col, :].astype(np.float32)
        c10 = strip0[ly0, px1_col, :].astype(np.float32)
        c01 = strip1[ly1, px0_col, :].astype(np.float32)
        c11 = strip1[ly1, px1_col, :].astype(np.float32)
        fxc = fx_col[:, None]
        top = c00 * (1 - fxc) + c10 * fxc
        bot = c01 * (1 - fxc) + c11 * fxc
        rgb[row] = np.clip(top * (1 - fy) + bot * fy, 0, 255).astype(np.uint8)

        if (row + 1) % 500 == 0 or row == OUT_H - 1:
            elapsed = time.time() - t1
            rate = (row + 1) / elapsed if elapsed > 0 else 0
            eta = (OUT_H - row - 1) / rate if rate > 0 else 0
            print(f"  row {row + 1}/{OUT_H}  rate={rate:.0f} rows/s  ETA {eta:.0f}s")
    print(f"phase 2 done in {time.time() - t1:.0f}s.")

    # Mask outside Greenland to transparent (same dilate+feather as
    # the legacy basemap so the patch hides the underlying globe's
    # halo near the coast).
    print("rendering greenland mask...")
    geom = find_greenland_geometry()
    mask = render_mask_array(geom, OUT_W, OUT_H)
    binary = mask > 128
    binary = binary_dilation(binary, iterations=40)  # scale dilate to higher res
    mask_arr = (binary.astype(np.float32) * 255).astype(np.uint8)
    mask_img = Image.fromarray(mask_arr, mode="L").filter(
        ImageFilter.GaussianBlur(radius=20)
    )
    alpha = np.array(mask_img)

    rgba = np.zeros((OUT_H, OUT_W, 4), dtype=np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = alpha
    Image.fromarray(rgba, mode="RGBA").save(OUT, optimize=True)
    print(f"wrote {OUT}")
    print(f"  dimensions: {OUT_W} × {OUT_H}")
    print(f"  size:       {OUT.stat().st_size / 1024 / 1024:.1f} MB")


def find_greenland_geometry():
    shp = shapereader.natural_earth(
        resolution="10m", category="cultural", name="admin_0_countries"
    )
    for record in shapereader.Reader(shp).records():
        if record.attributes.get("NAME") == "Greenland":
            return record.geometry
    raise RuntimeError("Greenland not found in Natural Earth countries shapefile")


def render_mask_array(geom, w: int, h: int) -> np.ndarray:
    """Render Greenland silhouette as a binary mask via matplotlib."""
    import cartopy.crs as ccrs  # noqa: PLC0415
    proj = ccrs.PlateCarree()
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100, facecolor="black")
    ax = fig.add_axes([0, 0, 1, 1], projection=proj)
    ax.set_extent([LON_W, LON_E, LAT_S, LAT_N], crs=proj)
    ax.set_facecolor("black")
    ax.set_axis_off()
    ax.add_geometries([geom], crs=proj, facecolor="white", edgecolor="none")
    tmp = OUT_DIR / "_mask_basemap.png"
    fig.savefig(tmp, dpi=100, facecolor="black", bbox_inches=None, pad_inches=0)
    plt.close(fig)
    mask = np.array(Image.open(tmp).convert("L").resize((w, h), Image.LANCZOS))
    tmp.unlink()
    return mask


if __name__ == "__main__":
    main()
