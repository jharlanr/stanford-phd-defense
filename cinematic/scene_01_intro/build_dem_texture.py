"""
Build a normalized Greenland surface-elevation heightmap PNG from
BedMachine v6, in the same lat/lon extent as greenland_basemap.png.
Three.js reads it in the vertex shader and displaces each basemap-mesh
vertex radially, producing a vertically-exaggerated 3D ice sheet.

ENCODING — two outputs, picked by mode:

  "gray8" (legacy)
      8-bit grayscale. R channel = elev/3500 m. 256 elevation levels
      over the 0–3500 m range → ~14 m quantization step. At 90×
      vertical exaggeration the byte boundaries read as visible step
      terraces on the dome ("3D printed" / contour-line stairs).
      Original output; still on R2 as shared/greenland_dem.png.

  "rg16" (default, current)
      16-bit fixed-point packed across R (high byte) + G (low byte).
      65,536 levels over 0–3500 m → ~0.05 m precision. Decoder in
      Globe.vue's vertex shader reconstructs as `R * 256/257 + G / 257`
      (approximate) or `(R*65280 + G*255) / 65535` (exact). The shader
      ALSO has to set tex.minFilter/magFilter = NearestFilter and do
      its own 4-tap bilinear interp — GPU bilinear blends R and G
      independently, which corrupts the encoding at byte-rollover
      boundaries (a 14 m step the eye DEFINITELY catches).

Pipeline:
  1. Load BedMachine v6 surface variable (Drive checkout via shared.py).
  2. Stride-downsample (150 m × stride → coarser raster).
  3. Reproject EPSG:3413 → PlateCarree via cartopy pcolormesh.
  4. Apply Greenland coastline mask (same dilate+feather as the basemap).
  5. Encode + save PNG.

Run:
    cd cinematic
    source .venv/bin/activate
    python scene_01_intro/build_dem_texture.py

Output:
    data/greenland_dem_rg16.png  (RG-packed 16-bit, default)
    data/greenland_dem.png       (8-bit grayscale, if ENCODING="gray8")
"""

import os
import sys
from pathlib import Path

import certifi  # noqa: E402

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cartopy.crs as ccrs  # noqa: E402
import cartopy.io.shapereader as shapereader  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import xarray as xr  # noqa: E402
from PIL import Image, ImageFilter  # noqa: E402

from shared import BEDMACHINE_PATH, CINEMATIC_DIR  # noqa: E402

DATA_DIR = CINEMATIC_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Output mode. See module docstring. Default "rg16" is the high-precision
# 16-bit packed encoding paired with Globe.vue's RG-decoding vertex
# shader. Set to "gray8" to regenerate the legacy 8-bit asset.
ENCODING = "rg16"

# Gaussian smoothing sigma in OUTPUT-PIXEL UNITS (at 10400×4000 over
# ~770 km lat, sigma=8 ≈ 1.5 km, sigma=2 ≈ 400 m on the ground).
# Override via env var DEM_SIGMA. Two values are useful at present:
#   * sigma=8 — displacement: kills sub-km fjord-cut spikes at 90×
#               vertical exaggeration. Produces the asset Globe.vue
#               consumes via demTextureHi.
#   * sigma=2 — hillshade: preserves catchment-scale (~km) surface
#               detail so the fragment-shader gradient has something
#               to shade with. Without this, the smooth-for-
#               displacement interior reads as featureless "fog" at
#               chapter framing. Produces greenland_dem_rg16_detail.png.
SIGMA = float(os.environ.get("DEM_SIGMA", "8"))
OUT_NAME_FOR_SIGMA = {
    8.0: "greenland_dem_rg16.png",
    # "Detail" variant for hillshade. At sigma=2 (~400 m) the bare
    # BedMachine sub-km roughness reads as visible ripples/dunes on
    # the dome — geometrically correct but distracting at 90× exag.
    # Sigma=4 (~750 m) preserves catchment-scale structure (visible
    # outlet glaciers + drainage divides) without resolving the
    # smaller bumps the eye reads as noise.
    4.0: "greenland_dem_rg16_detail.png",
}
default_name = "greenland_dem_rg16.png" if ENCODING == "rg16" else "greenland_dem.png"
OUT = DATA_DIR / OUT_NAME_FOR_SIGMA.get(SIGMA, default_name)

# Must match build_greenland_basemap.py / build_velocity_colormap.py.
LON_W, LON_E = -75.0, -10.0
LAT_S, LAT_N = 59.0, 84.0
FIGSIZE = (26, 10)
# DPI 400 = 10400 × 4000 PNG (matches the basemap). At the previous 200
# DPI (5200 × 2000) the mesh vertices at 1536 × 384 sampled multiple
# texels per vertex, so vertex displacement aliased the DEM into visible
# terraces even at the basemap mesh's finer subdivision. 400 DPI puts
# DEM texel spacing (~350 m) BELOW vertex spacing (~875 m E-W × 3.6 km
# N-S), so each vertex's bilinear sample is genuinely interpolated.
DPI = 400

# Greenland Summit ~3300 m. Pad to 3500 for headroom — anything taller
# clamps to 1.0 in the texture.
ELEV_MAX_M = 3500.0
# 150 m × 2 = 300 m grid (was 1200 m at STRIDE=8). At the higher render
# DPI we want to feed pcolormesh denser source data so the projected
# raster captures real BedMachine detail at sub-km scale.
STRIDE = 2


def find_greenland_geometry():
    shp = shapereader.natural_earth(
        resolution="10m", category="cultural", name="admin_0_countries"
    )
    for record in shapereader.Reader(shp).records():
        if record.attributes.get("NAME") == "Greenland":
            return record.geometry
    raise RuntimeError("Greenland not found in Natural Earth countries shapefile")


def reproject_dem_float() -> np.ndarray:
    """Reproject BedMachine surface from EPSG:3413 to PlateCarree at
    OUT_W × OUT_H, returning a float32 array of elevation fractions in
    [0, 1] (elev_m / ELEV_MAX_M).

    Critical: this bypasses matplotlib's pcolormesh+savefig pipeline,
    which rasterizes through an 8-bit gray colormap → BedMachine's
    float-precision surface values get crushed to 256 elevation levels
    (~14 m steps) before we ever see them. That 8-bit quantization is
    what produced the visible contour bands on the dome — no amount of
    downstream RG-packing or shader smoothing fixes a precision lost
    upstream. By doing the reprojection in numpy/scipy at float32 and
    encoding ONCE to RG-16 PNG, we preserve sub-metre precision end
    to end.
    """
    import pyproj  # noqa: PLC0415
    from scipy.interpolate import RegularGridInterpolator  # noqa: PLC0415

    print(f"opening {BEDMACHINE_PATH}")
    ds = xr.open_dataset(BEDMACHINE_PATH, chunks={"x": 2000, "y": 2000})
    print(f"  full surface shape: y={len(ds.y)} x={len(ds.x)}")

    surf = ds["surface"].isel(
        x=slice(None, None, STRIDE), y=slice(None, None, STRIDE)
    ).load()
    src_x = surf.x.values.astype(np.float64)  # EPSG:3413 metres, monotonically increasing
    src_y = surf.y.values.astype(np.float64)  # EPSG:3413 metres, DECREASING (north-down)
    src_z = np.nan_to_num(surf.values.astype(np.float32), nan=0.0)
    print(f"  subset shape: y={len(src_y)} x={len(src_x)} ({src_z.dtype})")
    print(f"  source elev range: {src_z.min():.1f} – {src_z.max():.1f} m "
          f"({len(np.unique(src_z))} unique values)")

    # BedMachine y axis is north-to-south (decreasing); flip so we can
    # use scipy's RGI which requires monotonically-increasing axes.
    if src_y[0] > src_y[-1]:
        src_y = src_y[::-1]
        src_z = src_z[::-1, :]

    # Interpolator: bilinear over BedMachine's 300 m grid, returns
    # zero outside the grid (i.e. open ocean past Greenland's bounds).
    interp = RegularGridInterpolator(
        (src_y, src_x), src_z, method="linear",
        bounds_error=False, fill_value=0.0,
    )

    # Output grid in PlateCarree lat/lon.
    out_w = FIGSIZE[0] * DPI
    out_h = FIGSIZE[1] * DPI
    lon_edges = np.linspace(LON_W, LON_E, out_w + 1)
    lat_edges = np.linspace(LAT_N, LAT_S, out_h + 1)  # north-down to match PNG row order
    out_lon = 0.5 * (lon_edges[:-1] + lon_edges[1:])
    out_lat = 0.5 * (lat_edges[:-1] + lat_edges[1:])
    lon2d, lat2d = np.meshgrid(out_lon, out_lat)  # both (out_h, out_w)

    # PlateCarree (lon/lat) → EPSG:3413 (x/y in metres). Vectorised —
    # 41M points in one call (pyproj transformer is fast).
    src_proj = pyproj.Proj("EPSG:3413")
    print(f"  reprojecting {out_w}×{out_h} = {out_w * out_h / 1e6:.1f}M points...")
    qx, qy = src_proj(lon2d.ravel(), lat2d.ravel())
    qx = qx.reshape(out_h, out_w)
    qy = qy.reshape(out_h, out_w)

    # Sample the interpolator. Chunk by rows to keep memory reasonable
    # (full 41M-point query in one shot is fine but row chunks are
    # easier on RAM).
    z_out = np.zeros((out_h, out_w), dtype=np.float32)
    CHUNK = 200  # rows
    for i in range(0, out_h, CHUNK):
        j = min(i + CHUNK, out_h)
        pts = np.stack([qy[i:j].ravel(), qx[i:j].ravel()], axis=-1)
        z_out[i:j] = interp(pts).reshape(j - i, -1).astype(np.float32)
        if (i // CHUNK) % 5 == 0:
            print(f"  ...row {i}/{out_h}")

    print(f"  reprojected elev range: {z_out.min():.1f} – {z_out.max():.1f} m "
          f"({len(np.unique(z_out))} unique values)")
    z_norm = np.clip(z_out / ELEV_MAX_M, 0.0, 1.0)
    return z_norm


def render_mask(out_path, geom) -> None:
    proj = ccrs.PlateCarree()
    fig = plt.figure(figsize=FIGSIZE, facecolor="black")
    ax = fig.add_axes([0, 0, 1, 1], projection=proj)
    ax.set_extent([LON_W, LON_E, LAT_S, LAT_N], crs=ccrs.PlateCarree())
    ax.set_facecolor("black")
    ax.set_axis_off()
    ax.add_geometries(
        [geom], crs=ccrs.PlateCarree(), facecolor="white", edgecolor="none"
    )
    fig.savefig(out_path, dpi=DPI, facecolor="black", bbox_inches=None, pad_inches=0)
    plt.close(fig)


def encode_rg16(frac_norm: np.ndarray) -> Image.Image:
    """Pack a normalized [0, 1] elevation array as 16-bit fixed-point
    across R (high byte) and G (low byte) channels of an RGBA PNG.

    Decoder (in Globe.vue's vertex shader):
        rg = texture2D(demMap, uv).rg                # NEAREST sampled
        elev_norm = (rg.r * 65280.0 + rg.g * 255.0) / 65535.0

    GPU bilinear filtering MUST be disabled on this texture
    (THREE.NearestFilter min/mag) — otherwise R and G blend
    independently and decode garbage at byte-rollover boundaries.
    The shader does its own 4-tap bilinear interpolation in compensation.

    A blue channel is left available for a future mask/aux value.
    """
    val_u16 = np.clip(np.round(frac_norm * 65535.0), 0, 65535).astype(np.uint32)
    hi = ((val_u16 >> 8) & 0xFF).astype(np.uint8)
    lo = (val_u16 & 0xFF).astype(np.uint8)
    h, w = frac_norm.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[..., 0] = hi
    rgba[..., 1] = lo
    rgba[..., 2] = 0
    rgba[..., 3] = 255
    return Image.fromarray(rgba, mode="RGBA")


def main() -> None:
    from scipy.ndimage import binary_dilation, gaussian_filter  # noqa: PLC0415

    mask_tmp = DATA_DIR / "_mask_dem.png"

    print(f"encoding mode: {ENCODING}")
    print(f"DPI: {DPI} (target dims: {FIGSIZE[0] * DPI} × {FIGSIZE[1] * DPI})")
    print(f"BedMachine STRIDE: {STRIDE}")

    # Reproject DEM at float32 precision — bypasses matplotlib's 8-bit
    # gray colormap rasterization entirely. Returns elev fraction in
    # [0, 1] at output PNG dimensions.
    print("reprojecting DEM (float32)...")
    final_frac = reproject_dem_float()

    # Smooth the elevation field before exposing it as displacement.
    # BedMachine resolves real surface detail down to ~150 m (fjord
    # cuts, ice-stream crevasses, supraglacial channel networks). At
    # 90× vertical exaggeration those genuine sub-km features turn
    # into visible spikes/roughness over the dome — the data is
    # accurate but visually distracting at that exaggeration. A
    # wider gaussian (sigma=8 px ≈ 1.5 km on the ground at 10400×4000
    # over 770 km) averages over kilometre scales: ice-sheet macro
    # shape preserved (dome, drainage divides, outlet glaciers), but
    # the sub-km roughness gets smoothed to the smooth glacier look
    # the eye expects from a continental ice sheet seen from orbit.
    # Working in float32 throughout means the smoothing produces
    # genuinely smooth values, not just blurred 8-bit jumps.
    sigma_km = SIGMA * 770.0 / 4000.0
    print(f"smoothing float DEM (sigma={SIGMA} px ≈ {sigma_km:.2f} km)...")
    final_frac = gaussian_filter(final_frac, sigma=SIGMA).astype(np.float32)

    print("rendering greenland mask...")
    geom = find_greenland_geometry()
    render_mask(mask_tmp, geom)
    mask = Image.open(mask_tmp).convert("L")

    mask_arr = np.array(mask)
    binary = mask_arr > 128
    # Tight mask: stop displacement right at the coastline — past the
    # coast we want zero elevation, not feathered intermediate values
    # that produce splayed-out edges when displaced radially. Dilate/blur
    # radii scaled to render DPI so coastline behavior is consistent.
    dilate_iters = 4 if DPI >= 400 else 2
    feather_radius = 6 if DPI >= 400 else 3
    binary = binary_dilation(binary, iterations=dilate_iters)
    mask_arr = (binary.astype(np.float32) * 255).astype(np.uint8)
    mask = Image.fromarray(mask_arr, mode="L").filter(
        ImageFilter.GaussianBlur(radius=feather_radius)
    )

    mask_arr = np.array(mask).astype(np.float32) / 255.0
    final_frac = final_frac * mask_arr  # still normalized

    if ENCODING == "rg16":
        out_img = encode_rg16(final_frac)
        out_img.save(OUT, optimize=True)
    else:
        out_8 = (final_frac * 255.0).astype(np.uint8)
        Image.fromarray(out_8, mode="L").save(OUT)

    mask_tmp.unlink()

    # Sanity report: max elevation value found + size on disk + unique
    # value count (sanity check that we're NOT 8-bit-limited).
    decoded_max_m = float(final_frac.max()) * ELEV_MAX_M
    n_unique = len(np.unique((final_frac * 65535).astype(np.uint32)))
    print(f"wrote {OUT}")
    print(f"  size:               {OUT.stat().st_size / 1024:.0f} KB")
    print(f"  max elev (decoded): {decoded_max_m:.1f} m")
    print(f"  unique 16-bit vals: {n_unique} (8-bit ceiling: 256)")
    if ENCODING == "rg16":
        # Show the precision delta: 16-bit step = ELEV_MAX_M / 65535.
        print(f"  precision per LSB:  {ELEV_MAX_M / 65535:.3f} m (vs 8-bit: {ELEV_MAX_M / 255:.1f} m)")


if __name__ == "__main__":
    main()
