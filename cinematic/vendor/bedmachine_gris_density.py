"""
bedmachine_gris_density.py
==========================
Downloads BedMachine Greenland v6 and combines with an ITS_LIVE velocity
mosaic to compute along-flow surface slope α, and provides:

  (a) (α, h) density contours for overlay on SSA phase-space figures
  (b) point queries of (α, h) at arbitrary lake / site locations

PIPELINE OVERVIEW
-----------------
1. BedMachine v6 (150 m, EPSG:3413)
       → coarsen to working resolution (default 1.5 km)
       → surface DEM s(x,y), ice thickness h(x,y), grounded-ice mask

2. ITS_LIVE velocity mosaic (120 m, EPSG:3413)
       Download manually from https://nsidc.org/apps/itslive/
       Select: Greenland, desired year, NetCDF or COG GeoTIFF format.
       No authentication required — open access.
       → coarsen to working resolution
       → bilinearly interpolate onto BedMachine coarsened grid
       → unit flow-direction vector û = (vx, vy) / |v|

3. Along-flow slope
       α = arctan( ∇s · û )   [projection of surface gradient onto flow]
       This is exactly the slope that enters the SSA driving stress τ_d = ρghα.
       Pixels with |v| < min_speed (stagnant / undefined flow direction) → NaN.

4a. 2D histogram of (α, h) over grounded ice → contour thresholds.
4b. Point-sample (α, h) at lake locations from a CSV with lon/lat columns.

USAGE
-----
Step 1 — Set up NASA Earthdata auth (required for BedMachine):
    python bedmachine_gris_density.py --setup-auth

Step 2 — Download BedMachine:
    python bedmachine_gris_density.py --download-bedmachine

Step 3 — Download ITS_LIVE velocity mosaic manually:
    Go to https://nsidc.org/apps/itslive/
    Select Greenland, choose year (e.g. 2018), download NetCDF or GeoTIFF.
    Place the file in the same directory as BedMachine.

Step 4 — Sanity-check plot:
    python bedmachine_gris_density.py --demo --its <itslive_file>

Step 5 — In your notebook:

    from bedmachine_gris_density import (
        build_grid_state,
        get_gris_density_contours,
        query_lake_locations,
        overlay_gris_contours,
        overlay_lake_scatter,
    )

    grid = build_grid_state(
        bedmachine_path='BedMachineGreenland-v6.nc',
        itslive_path='<your_itslive_file>.nc',
    )

    contours = get_gris_density_contours(grid=grid)
    overlay_gris_contours(ax, contours)

    lakes = query_lake_locations('labels_2019_volumes.csv', grid)
    overlay_lake_scatter(ax, lakes)
"""

import argparse
import os
import sys
import stat
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
from scipy.ndimage import uniform_filter
from scipy.interpolate import RegularGridInterpolator


# ── URLs ──────────────────────────────────────────────────────────────────────
BEDMACHINE_URL = (
    "https://n5eil01u.ecs.nsidc.org/ICEBRIDGE/IDBMG4.006/"
    "1993.01.01/BedMachineGreenland-v6.nc"
)

# ITS_LIVE — download manually from https://nsidc.org/apps/itslive/
# Select region (Greenland), year (e.g. 2018), format (NetCDF or COG GeoTIFF).
# No authentication required; open access.
# v2 mosaics cover 1985–2022+ at 120 m for Greenland, EPSG:3413.
ITSLIVE_DEFAULT_FILE = "GRE_G0120_2018.nc"  # adjust to match your downloaded file

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_COARSEN_BM   = 10   # 10 × 150 m  = 1500 m
DEFAULT_COARSEN_ITS  = 12   # 12 × 120 m  = 1440 m  (≈ same working resolution as BM)
MIN_SPEED_MS        = 5.0  # m/yr — below this, flow direction is undefined
SMOOTH_PASSES       = 3    # uniform_filter iterations on surface DEM
CONTOUR_LEVELS      = [0.50, 0.90, 0.99]
H_RANGE             = (200, 3000)   # metres
ALPHA_RANGE         = (0.05, 1.0)  # degrees

# EPSG:3413 — NSIDC Sea Ice Polar Stereographic North
# Used by both BedMachine v6 and ITS_LIVE
EPSG_3413 = "+proj=stere +lat_0=90 +lat_ts=70 +lon_0=-45 +k=1 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"


# ── Authentication (BedMachine requires NASA Earthdata login) ─────────────────

def setup_netrc(username=None, password=None):
    """Write ~/.netrc entry for urs.earthdata.nasa.gov."""
    netrc_path = Path.home() / ".netrc"
    if username is None:
        username = input("NASA Earthdata username: ").strip()
    if password is None:
        import getpass
        password = getpass.getpass("NASA Earthdata password: ")
    entry = (
        f"\nmachine urs.earthdata.nasa.gov\n"
        f"    login {username}\n"
        f"    password {password}\n"
    )
    with open(netrc_path, "a") as f:
        f.write(entry)
    os.chmod(netrc_path, stat.S_IRUSR | stat.S_IWUSR)
    print(f"✓ Written to {netrc_path}")


def _download_via_earthaccess(concept_id, output_path, label="file"):
    """
    Download a single-granule dataset from NASA Earthdata Cloud using earthaccess.
    Prompts interactively for Earthdata credentials if ~/.netrc is not set up.
    Install: pip install earthaccess
    """
    output_path = Path(output_path)
    if output_path.exists():
        print(f"✓ {output_path} already exists — skipping download.")
        return
    try:
        import earthaccess
    except ImportError:
        raise ImportError(
            "earthaccess is required for downloading NASA Earthdata files.\n"
            "Install with:  pip install earthaccess\n"
            "Then re-run the download command."
        )
    print(f"Downloading {label} → {output_path}")
    earthaccess.login(strategy="netrc", persist=True)
    results = earthaccess.search_data(concept_id=concept_id, count=10)
    if not results:
        raise RuntimeError(
            f"No granules found for concept_id={concept_id}. "
            "Check that the dataset exists and your Earthdata account is active."
        )
    # BedMachine has 2 granules (a .tif and a .nc); select the NetCDF one
    nc_results = [r for r in results if any(l.endswith('.nc') for l in r.data_links())]
    if not nc_results:
        nc_results = results  # fallback: download whatever is available
    files = earthaccess.download(nc_results, local_path=str(output_path.parent))
    # earthaccess names the file by its original name; rename if needed
    if files and Path(files[0]).resolve() != output_path.resolve():
        Path(files[0]).rename(output_path)
    print(f"✓ Downloaded to {output_path}")


def _download_via_curl(url, output_path, token=None, label="file"):
    """Fallback: curl with either a Bearer token or ~/.netrc credentials."""
    output_path = Path(output_path)
    if output_path.exists():
        print(f"✓ {output_path} already exists — skipping download.")
        return
    print(f"Downloading {label} via curl → {output_path}")
    if token:
        cmd = (f'curl -L -H "Authorization: Bearer {token}" '
               f'-b ~/.urs_cookies -c ~/.urs_cookies '
               f'-o "{output_path}" "{url}"')
    else:
        cmd = (f'curl -L -n --netrc-file ~/.netrc '
               f'-b ~/.urs_cookies -c ~/.urs_cookies '
               f'-o "{output_path}" "{url}"')
    ret = os.system(cmd)
    if ret != 0:
        raise RuntimeError(
            f"curl download failed for {label}.\n"
            "Make sure you have a valid ~/.netrc with your NASA Earthdata credentials:\n"
            "  machine urs.earthdata.nasa.gov\n"
            "      login YOUR_USERNAME\n"
            "      password YOUR_PASSWORD\n"
            "Or run: python bedmachine_gris_density.py --setup-auth"
        )
    print(f"✓ Downloaded to {output_path}")


# BedMachine v6 concept ID (IDBMG4.006, NSIDC_CPRD)
BEDMACHINE_CONCEPT_ID = "C3903728370-NSIDC_CPRD"


def download_bedmachine(output_path="BedMachineGreenland-v6.nc", token=None):
    """
    Download BedMachine Greenland v6 (~8 GB). Requires a free NASA Earthdata account.
    https://urs.earthdata.nasa.gov/

    Uses earthaccess (pip install earthaccess) for authentication and download.
    Falls back to curl with ~/.netrc if earthaccess is unavailable.

    Citation: Morlighem et al. (2025), IDBMG4 v6,
              https://doi.org/10.5067/6B6B225B8V2D
    """
    output_path = Path(output_path)
    if output_path.exists():
        print(f"✓ {output_path} already exists — skipping download.")
        return
    try:
        _download_via_earthaccess(BEDMACHINE_CONCEPT_ID, output_path,
                                   label="BedMachine v6 (~8 GB)")
    except ImportError as e:
        print(f"earthaccess not available ({e})\nFalling back to curl …")
        _download_via_curl(BEDMACHINE_URL, output_path, token=token,
                           label="BedMachine v6 (~8 GB)")


# ── BedMachine loading ────────────────────────────────────────────────────────

def _infer_dx(ds, dim):
    if dim in ds.coords and ds.coords[dim].size > 1:
        return abs(float(ds.coords[dim].diff(dim).median()))
    return None


def load_bedmachine(nc_path, coarsen_factor=DEFAULT_COARSEN_BM):
    """
    Load and coarsen BedMachine v6 (or v5 — same format, variable names unchanged).

    Returns
    -------
    surf  : 2D ndarray  surface elevation (m)
    h     : 2D ndarray  ice thickness (m)
    mask  : 2D ndarray  BedMachine mask (int)
    x_bm  : 1D ndarray  x-coords of coarsened grid (m, EPSG:3413)
    y_bm  : 1D ndarray  y-coords of coarsened grid (m, EPSG:3413)
    dx_bm : float       coarsened pixel size (m)
    """
    print(f"Loading BedMachine: {nc_path} …")
    ds = xr.open_dataset(nc_path, engine="netcdf4")

    y_dim, x_dim = ds["thickness"].dims
    dx_native = _infer_dx(ds, x_dim) or 150.0
    cf = coarsen_factor
    print(f"  Native {dx_native:.0f} m → coarsen {cf}× "
          f"→ {dx_native*cf/1000:.2f} km …")

    ck = {y_dim: cf, x_dim: cf}
    surf_c = ds["surface"  ].coarsen(**ck, boundary="trim").mean().values
    h_c    = ds["thickness"].coarsen(**ck, boundary="trim").mean().values
    mask_c = np.round(
        ds["mask"].coarsen(**ck, boundary="trim").mean().values
    ).astype(int)

    x_c = ds.coords[x_dim].coarsen({x_dim: cf}, boundary="trim").mean().values
    y_c = ds.coords[y_dim].coarsen({y_dim: cf}, boundary="trim").mean().values

    ds.close()
    dx_bm = dx_native * cf
    print(f"  Shape: {h_c.shape},  dx = {dx_bm/1000:.2f} km")
    return surf_c, h_c, mask_c, x_c, y_c, dx_bm


# ── ITS_LIVE loading ──────────────────────────────────────────────────────────

def load_itslive_onto_bedmachine(itslive_path, x_bm, y_bm,
                                  coarsen_factor=DEFAULT_COARSEN_ITS,
                                  min_speed=MIN_SPEED_MS):
    """
    Load an ITS_LIVE annual velocity mosaic (NetCDF or GeoTIFF), coarsen,
    and bilinearly interpolate onto the BedMachine grid.

    Download mosaics from https://nsidc.org/apps/itslive/ — no auth required.
    v2 mosaics (recommended) cover 1985–2022+ at 120 m for Greenland, in
    EPSG:3413 — the same projection as BedMachine, so no reprojection needed.

    Both NetCDF (.nc, opened via xarray) and GeoTIFF (.tif, opened via
    rasterio) are supported; format is inferred from the file extension.

    Returns
    -------
    ux, uy : 2D ndarrays of unit flow-direction on the BedMachine grid.
             NaN where |v| < min_speed or ITS_LIVE has no data.
    """
    print(f"Loading ITS_LIVE: {Path(itslive_path).name} …")
    suffix = Path(itslive_path).suffix.lower()

    if suffix in (".tif", ".tiff"):
        # Cloud-Optimized GeoTIFF — two separate band files or a single 2-band file.
        # The ITS_LIVE app downloads vx and vy as separate files; detect which this is
        # by checking the filename for 'vx'/'vy', otherwise treat band 1=vx, band 2=vy.
        import rasterio
        fname = Path(itslive_path).name.lower()
        if "vx" in fname:
            vy_path = str(itslive_path).replace("vx", "vy").replace("VX", "VY")
            with rasterio.open(itslive_path) as src:
                vx_c_raw = src.read(1).astype(float)
                transform = src.transform
                height, width = src.height, src.width
            with rasterio.open(vy_path) as src:
                vy_c_raw = src.read(1).astype(float)
        elif "vy" in fname:
            vx_path = str(itslive_path).replace("vy", "vx").replace("VY", "VX")
            with rasterio.open(vx_path) as src:
                vx_c_raw = src.read(1).astype(float)
                transform = src.transform
                height, width = src.height, src.width
            with rasterio.open(itslive_path) as src:
                vy_c_raw = src.read(1).astype(float)
        else:
            # Single 2-band file: band 1 = vx, band 2 = vy
            with rasterio.open(itslive_path) as src:
                vx_c_raw = src.read(1).astype(float)
                vy_c_raw = src.read(2).astype(float)
                transform = src.transform
                height, width = src.height, src.width
        dx_native = abs(transform.a)
        x_its = transform.c + transform.a * (np.arange(width) + 0.5)
        y_its = transform.f + transform.e * (np.arange(height) + 0.5)
        vx_c_raw[np.abs(vx_c_raw) > 1e10] = np.nan
        vy_c_raw[np.abs(vy_c_raw) > 1e10] = np.nan
        # Block-average coarsen
        cf = coarsen_factor
        h_c = (height // cf) * cf
        w_c = (width  // cf) * cf
        vx_c = vx_c_raw[:h_c, :w_c].reshape(h_c//cf, cf, w_c//cf, cf)
        vy_c = vy_c_raw[:h_c, :w_c].reshape(h_c//cf, cf, w_c//cf, cf)
        with np.errstate(all='ignore'):
            vx_c = np.nanmean(vx_c, axis=(1, 3))
            vy_c = np.nanmean(vy_c, axis=(1, 3))
        x_its = x_its[:w_c].reshape(w_c//cf, cf).mean(axis=1)
        y_its = y_its[:h_c].reshape(h_c//cf, cf).mean(axis=1)

    else:
        # NetCDF (default from ITS_LIVE app)
        ds = xr.open_dataset(itslive_path, engine="netcdf4")
        vx_var = "vx" if "vx" in ds else list(ds.data_vars)[0]
        vy_var = "vy" if "vy" in ds else list(ds.data_vars)[1]
        y_dim  = ds[vx_var].dims[-2]
        x_dim  = ds[vx_var].dims[-1]
        dx_native = abs(_infer_dx(ds, x_dim)) or 120.0
        cf = coarsen_factor
        ck = {y_dim: cf, x_dim: cf}
        vx_c = ds[vx_var].coarsen(**ck, boundary="trim").mean().values.astype(float)
        vy_c = ds[vy_var].coarsen(**ck, boundary="trim").mean().values.astype(float)
        x_its = ds.coords[x_dim].coarsen({x_dim: cf}, boundary="trim").mean().values
        y_its = ds.coords[y_dim].coarsen({y_dim: cf}, boundary="trim").mean().values
        ds.close()
        vx_c[np.abs(vx_c) > 1e10] = np.nan
        vy_c[np.abs(vy_c) > 1e10] = np.nan

    print(f"  Native {dx_native:.0f} m → coarsen {cf}× "
          f"→ {dx_native*cf/1000:.2f} km …")

    print("  Interpolating onto BedMachine grid …")

    def _interp(arr, y_grid, x_grid, y_target, x_target):
        if y_grid[0] > y_grid[-1]:
            arr    = arr[::-1, :]
            y_grid = y_grid[::-1]
        nan_src    = (~np.isfinite(arr)).astype(float)
        arr_filled = np.where(np.isfinite(arr), arr, 0.0)
        XX, YY = np.meshgrid(x_target, y_target)
        pts    = np.column_stack([YY.ravel(), XX.ravel()])
        shape  = (len(y_target), len(x_target))
        kw = dict(method="linear", bounds_error=False, fill_value=np.nan)
        val  = RegularGridInterpolator((y_grid, x_grid), arr_filled, **kw)(pts)
        nanf = RegularGridInterpolator((y_grid, x_grid), nan_src,    **kw)(pts)
        result = val.reshape(shape)
        result[nanf.reshape(shape) > 0.5] = np.nan
        return result

    vx_bm = _interp(vx_c, y_its, x_its, y_bm, x_bm)
    vy_bm = _interp(vy_c, y_its, x_its, y_bm, x_bm)

    speed = np.sqrt(vx_bm**2 + vy_bm**2)
    speed[speed < min_speed] = np.nan
    ux = vx_bm / speed
    uy = vy_bm / speed

    pct_valid = 100 * np.sum(np.isfinite(ux)) / ux.size
    print(f"  Flow direction valid at {pct_valid:.1f}% of grid points "
          f"(|v| ≥ {min_speed} m/yr)")
    return ux, uy

def _surface_gradient(surf, dx, smooth_passes=SMOOTH_PASSES):
    """Smooth surface DEM and return (∂s/∂x, ∂s/∂y). NaN-safe."""
    s        = surf.copy().astype(float)
    nan_mask = ~np.isfinite(s)
    s[nan_mask] = 0.0
    for _ in range(smooth_passes):
        s = uniform_filter(s, size=3)
    s[nan_mask] = np.nan
    return np.gradient(s, dx, axis=1), np.gradient(s, dx, axis=0)


def compute_alongflow_slope_deg(surf, dx, ux, uy,
                                 smooth_passes=SMOOTH_PASSES):
    """
    Along-flow surface slope: α = arctan( |∇s · û| ).

    ∇s · û is the directional derivative of the surface in the flow direction,
    which is the slope entering the SSA driving stress τ_d = ρghα.
    """
    dsdx, dsdy = _surface_gradient(surf, dx, smooth_passes)
    ds_along   = dsdx * ux + dsdy * uy
    return np.degrees(np.arctan(np.abs(ds_along)))


def compute_fullgradient_slope_deg(surf, dx, smooth_passes=SMOOTH_PASSES):
    """Fallback: full-gradient slope |∇s|. Ignores flow direction."""
    dsdx, dsdy = _surface_gradient(surf, dx, smooth_passes)
    return np.degrees(np.arctan(np.sqrt(dsdx**2 + dsdy**2)))


# ── Grid state ────────────────────────────────────────────────────────────────

def build_grid_state(
        bedmachine_path="BedMachineGreenland-v6.nc",
        itslive_path=ITSLIVE_DEFAULT_FILE,
        coarsen_bm=DEFAULT_COARSEN_BM,
        coarsen_its=DEFAULT_COARSEN_ITS,
        min_speed=MIN_SPEED_MS,
        fallback_fullgradient=False,
):
    """
    Load BedMachine + ITS_LIVE velocity, compute all derived 2D fields,
    and return a grid-state dict reusable by both the contour pipeline and
    lake queries — avoiding double loading of the large datasets.

    Parameters
    ----------
    bedmachine_path : path to BedMachineGreenland-v6.nc
    itslive_path    : path to ITS_LIVE velocity mosaic (NetCDF or GeoTIFF).
                      Download manually from https://nsidc.org/apps/itslive/
    coarsen_bm      : BedMachine coarsening (default 10 → 1.5 km)
    coarsen_its     : ITS_LIVE coarsening factor (default 12 → 1.44 km)
    min_speed       : m/yr — below this, flow direction treated as undefined
    fallback_fullgradient : if True and ITS_LIVE file not found, fall
                            back to full-gradient slope |∇s| with a warning

    Returns
    -------
    dict with keys:
        surf, h, mask   : 2D BedMachine fields
        alpha           : 2D along-flow (or full-gradient) surface slope (°)
        dsdx, dsdy      : 2D surface gradient components
        ux, uy          : 2D unit flow-direction (NaN if unavailable)
        x, y            : 1D coordinate arrays (m, EPSG:3413)
        dx              : pixel spacing (m)
        slope_type      : str describing which velocity source was used
    """
    surf, h, mask, x_bm, y_bm, dx_bm = load_bedmachine(bedmachine_path, coarsen_bm)
    dsdx, dsdy = _surface_gradient(surf, dx_bm)

    if Path(itslive_path).exists():
        ux, uy = load_itslive_onto_bedmachine(
            itslive_path, x_bm, y_bm,
            coarsen_factor=coarsen_its, min_speed=min_speed,
        )
        slope_type = f"along-flow (ITS_LIVE {Path(itslive_path).stem})"
    elif fallback_fullgradient:
        print(f"WARNING: {itslive_path} not found — falling back to |∇s|.")
        ux = uy = np.full_like(surf, np.nan)
        slope_type = "full-gradient (fallback, no ITS_LIVE)"
    else:
        raise FileNotFoundError(
            f"ITS_LIVE file not found: {itslive_path}\n"
            f"Download from: https://nsidc.org/apps/itslive/\n"
            f"Or pass fallback_fullgradient=True to use |∇s| instead."
        )

    # Compute slope — either along-flow or full-gradient fallback
    if np.any(np.isfinite(ux)):
        print("Computing along-flow surface slope α = arctan(∇s · û) …")
        alpha = np.degrees(np.arctan(np.abs(dsdx * ux + dsdy * uy)))
    else:
        print("Computing full-gradient surface slope α = arctan(|∇s|) …")
        alpha = np.degrees(np.arctan(np.sqrt(dsdx**2 + dsdy**2)))

    return dict(
        surf=surf, h=h, mask=mask, alpha=alpha,
        dsdx=dsdx, dsdy=dsdy, ux=ux, uy=uy,
        x=x_bm, y=y_bm, dx=dx_bm,
        slope_type=slope_type,
    )


# ── Lake / site point queries ─────────────────────────────────────────────────

def _lonlat_to_epsg3413(lon, lat):
    """
    Convert arrays of (lon, lat) in WGS84 to EPSG:3413 (x, y) in metres.

    Uses pyproj if available; falls back to a manual spherical approximation
    (good to ~0.1% for Greenland) so the module works without pyproj.
    """
    try:
        from pyproj import Transformer
        tf = Transformer.from_crs("EPSG:4326", "EPSG:3413", always_xy=True)
        x, y = tf.transform(lon, lat)
        return np.asarray(x), np.asarray(y)
    except ImportError:
        pass

    # Manual fallback — polar stereographic projection (NSIDC variant)
    # Reference: Snyder (1987) "Map Projections — A Working Manual", p. 160
    print("  pyproj not found — using built-in EPSG:3413 approximation.")
    lon  = np.radians(np.asarray(lon, dtype=float))
    lat  = np.radians(np.asarray(lat, dtype=float))
    lat0 = np.radians(90.0)
    lon0 = np.radians(-45.0)
    lat_ts = np.radians(70.0)
    a    = 6378137.0          # WGS84 semi-major axis
    e    = 0.0818191908426    # WGS84 eccentricity

    def _t(phi):
        e_sin = e * np.sin(phi)
        return np.tan(np.pi/4 - phi/2) / ((1 - e_sin)/(1 + e_sin))**(e/2)

    def _m(phi):
        e_sin = e * np.sin(phi)
        return np.cos(phi) / np.sqrt(1 - e_sin**2)

    t    = _t(lat)
    t_c  = _t(lat_ts)
    m_c  = _m(lat_ts)
    rho  = a * m_c * t / t_c
    x    =  rho * np.sin(lon - lon0)
    y    = -rho * np.cos(lon - lon0)
    return x, y


def query_lake_locations(
        csv_path,
        grid,
        lon_col="lon",
        lat_col="lat",
        extra_cols=None,
):
    """
    Sample (h, α) from the BedMachine/ITS_LIVE grid at lake / site locations
    given in a CSV with longitude and latitude columns.

    Coordinate conversion: WGS84 lon/lat → EPSG:3413, then nearest-grid-point
    lookup on the coarsened BedMachine grid.  This is appropriate because the
    lakes are O(100 m – 1 km) in size, smaller than the coarsened grid spacing,
    so bilinear interpolation and nearest-neighbour give essentially the same
    result.

    Parameters
    ----------
    csv_path  : str or Path
        CSV with at least `lon_col` and `lat_col` columns.
        Your file (labels_2019_volumes.csv) has columns:
            new_id, area, elevation, region, final_label, S1_label, S2_label,
            drain_date, mean_depth, max_depth, ..., lon, lat
    grid      : dict
        Output of build_grid_state().
    lon_col   : str   name of longitude column  (default 'lon')
    lat_col   : str   name of latitude column   (default 'lat')
    extra_cols: list of str, optional
        Additional columns from the CSV to carry through into the output.
        Defaults to all non-geometry columns.

    Returns
    -------
    pandas DataFrame with columns:
        [original CSV columns (minus geometry polygon)]
        + h_bm      : ice thickness at lake location (m)
        + alpha_bm  : along-flow surface slope at lake location (degrees)
        + surf_bm   : surface elevation from BedMachine (m)  [sanity check vs CSV 'elevation']
        + mask_bm   : BedMachine mask value at lake location
        + speed_bm  : ice speed magnitude at lake location (m/yr), NaN if unavailable
        + x_3413    : projected x-coordinate (m, EPSG:3413)
        + y_3413    : projected y-coordinate (m, EPSG:3413)
        + i_grid    : row index into coarsened BedMachine grid
        + j_grid    : col index into coarsened BedMachine grid
    """
    df = pd.read_csv(csv_path)

    # Drop the WKT geometry column if present (large strings, not needed)
    geom_cols = [c for c in df.columns if "geometry" in c.lower()
                 or "polygon" in c.lower() or "wkt" in c.lower()]
    df = df.drop(columns=geom_cols, errors="ignore")

    if lon_col not in df.columns or lat_col not in df.columns:
        raise ValueError(
            f"Columns '{lon_col}' and '{lat_col}' not found in {csv_path}.\n"
            f"Available columns: {list(df.columns)}"
        )

    lon = df[lon_col].values
    lat = df[lat_col].values

    print(f"  Converting {len(lon):,} lake coordinates to EPSG:3413 …")
    x_pts, y_pts = _lonlat_to_epsg3413(lon, lat)

    # ── Nearest-grid-point lookup ─────────────────────────────────────────────
    x_grid = grid["x"]   # 1D, length ncols
    y_grid = grid["y"]   # 1D, length nrows  (may be ascending or descending)

    def _nearest_idx(arr_1d, vals):
        """
        Nearest-neighbour index into a sorted 1D array.
        Works for both ascending and descending arr_1d.
        """
        # Ensure ascending for searchsorted
        if arr_1d[0] > arr_1d[-1]:
            arr_1d = arr_1d[::-1]
            flipped = True
        else:
            flipped = False
        # searchsorted gives insertion point; compare neighbours to find nearest
        idx = np.searchsorted(arr_1d, vals, side="left")
        idx = np.clip(idx, 1, len(arr_1d) - 1)
        # Choose left or right neighbour based on absolute distance
        left_closer = np.abs(vals - arr_1d[idx - 1]) < np.abs(vals - arr_1d[idx])
        idx -= left_closer.astype(int)
        idx = np.clip(idx, 0, len(arr_1d) - 1)
        if flipped:
            idx = len(arr_1d) - 1 - idx
        return idx

    j_idx = _nearest_idx(x_grid, x_pts)   # column indices
    i_idx = _nearest_idx(y_grid, y_pts)    # row indices

    # ── Extract field values ──────────────────────────────────────────────────
    h_vals     = grid["h"    ][i_idx, j_idx]
    alpha_vals = grid["alpha"][i_idx, j_idx]
    surf_vals  = grid["surf" ][i_idx, j_idx]
    mask_vals  = grid["mask" ][i_idx, j_idx]

    # Ice speed (reconstruct from unit vector × ... wait, we only stored û)
    # We can't recover |v| from û alone.  Flag as NaN if ux is NaN (slow ice),
    # but we can't give the actual magnitude without storing vx/vy separately.
    # For now store a boolean "has_flow_direction" which is more honest.
    has_flow = np.isfinite(grid["ux"][i_idx, j_idx])

    # Warn about out-of-domain points
    out_of_domain = (
        (x_pts < x_grid.min()) | (x_pts > x_grid.max()) |
        (y_pts < y_grid.min()) | (y_pts > y_grid.max())
    )
    if out_of_domain.sum() > 0:
        print(f"  WARNING: {out_of_domain.sum()} lake points fall outside the "
              f"BedMachine grid extent and will have NaN field values.")
        h_vals    [out_of_domain] = np.nan
        alpha_vals[out_of_domain] = np.nan
        surf_vals [out_of_domain] = np.nan

    # ── Assemble output DataFrame ─────────────────────────────────────────────
    out = df.copy()
    out["h_bm"           ] = h_vals
    out["alpha_bm"       ] = alpha_vals
    out["surf_bm"        ] = surf_vals
    out["mask_bm"        ] = mask_vals
    out["flow_dir_valid"  ] = has_flow    # True = |v| ≥ min_speed
    out["x_3413"         ] = x_pts
    out["y_3413"         ] = y_pts
    out["i_grid"         ] = i_idx
    out["j_grid"         ] = j_idx

    n_ice    = (mask_vals == 2).sum()
    n_noalph = (~np.isfinite(alpha_vals)).sum()
    print(f"  Done. {len(out):,} lakes queried.")
    print(f"    Grounded ice (mask=2): {n_ice:,}")
    print(f"    NaN α (slow/off-ice) : {n_noalph:,}")
    return out


# ── Histogram and contour thresholds ─────────────────────────────────────────

def compute_histogram(h, alpha, mask,
                       h_range=H_RANGE, alpha_range=ALPHA_RANGE,
                       n_bins_h=120, n_bins_alpha=120):
    """2D histogram of (α, h) over grounded ice (mask==2)."""
    ice = (mask == 2) & np.isfinite(h) & np.isfinite(alpha)

    h_ice = h[ice].ravel()
    a_ice = alpha[ice].ravel()

    in_range = (
        (h_ice >= h_range[0]) & (h_ice <= h_range[1]) &
        (a_ice >= alpha_range[0]) & (a_ice <= alpha_range[1])
    )
    print(f"  In-range grounded ice pixels: {in_range.sum():,} "
          f"({100*in_range.sum()/max(ice.sum(),1):.1f}% of grounded ice)")

    H, a_edges, h_edges = np.histogram2d(
        a_ice[in_range], h_ice[in_range],
        bins=[n_bins_alpha, n_bins_h],
        range=[alpha_range, h_range],
    )
    return H, h_edges, a_edges


def histogram_to_contour_levels(H, levels=CONTOUR_LEVELS):
    """
    For each fraction f, find H threshold V such that bins with H ≥ V
    collectively contain fraction f of total counts.
    """
    total    = H.sum()
    sorted_H = np.sort(H.ravel())[::-1]
    cumfrac  = np.cumsum(sorted_H) / total
    return np.array([
        sorted_H[min(np.searchsorted(cumfrac, f), len(sorted_H)-1)]
        for f in levels
    ])


# ── Public API ────────────────────────────────────────────────────────────────

def get_gris_density_contours(
        bedmachine_path="BedMachineGreenland-v6.nc",
        itslive_path=ITSLIVE_DEFAULT_FILE,
        coarsen_bm=DEFAULT_COARSEN_BM,
        coarsen_its=DEFAULT_COARSEN_ITS,
        min_speed=MIN_SPEED_MS,
        levels=None,
        fallback_fullgradient=False,
        grid=None,
):
    """
    Full pipeline → (α_along-flow, h) density contours.

    Parameters
    ----------
    All path/coarsen/speed args are ignored if `grid` is provided.
    levels : density fractions enclosed (default [0.50, 0.90, 0.99])
    grid   : pre-built dict from build_grid_state(); pass to skip reloading.

    Returns
    -------
    dict: H, h_edges, alpha_edges, h_centers, alpha_centers,
          thresholds, levels, slope_type
    """
    if levels is None:
        levels = CONTOUR_LEVELS

    if grid is None:
        grid = build_grid_state(
            bedmachine_path,
            itslive_path=itslive_path,
            coarsen_bm=coarsen_bm, coarsen_its=coarsen_its,
            min_speed=min_speed, fallback_fullgradient=fallback_fullgradient,
        )

    print(f"Building (α, h) histogram  [{grid['slope_type']}] …")
    H, h_edges, a_edges = compute_histogram(grid["h"], grid["alpha"], grid["mask"])
    thresholds = histogram_to_contour_levels(H, levels)

    print("Density contour thresholds:")
    for frac, thresh in zip(levels, thresholds):
        print(f"  {int(frac*100):3d}% enclosed : H ≥ {thresh:.1f} counts")

    return dict(
        H=H,
        h_edges=h_edges,
        alpha_edges=a_edges,
        h_centers=0.5*(h_edges[:-1]+h_edges[1:]),
        alpha_centers=0.5*(a_edges[:-1]+a_edges[1:]),
        thresholds=thresholds,
        levels=levels,
        slope_type=grid["slope_type"],
    )


# ── Plot helpers ──────────────────────────────────────────────────────────────

def overlay_gris_contours(ax, contours,
                           colors=None, linestyles=None, linewidths=None,
                           labels=True, label_fmt="{pct}%",
                           zorder=5, contour_alpha=1.0,
                           axis_order="h_alpha",
                           **contour_kwargs):
    """
    Overlay GrIS density contours onto an (h, α) phase-space axis.

    Parameters
    ----------
    ax          : matplotlib Axes
    contours    : dict from get_gris_density_contours()
    axis_order  : str
        'h_alpha' (default) — ax x-axis = h (m),      ax y-axis = α (degrees)
        'alpha_h'           — ax x-axis = α (degrees), ax y-axis = h (m)
        Match this to however your phase-space figure is oriented.

    Returns matplotlib ContourSet.
    """
    H, h_c, a_c    = contours["H"], contours["h_centers"], contours["alpha_centers"]
    thresholds      = contours["thresholds"]
    levels_frac     = contours["levels"]
    n               = len(thresholds)

    if colors     is None: colors     = list(plt.cm.Greys(np.linspace(0.75, 0.35, n)))
    if linestyles is None: linestyles = ([":", "--", "-"] * n)[:n]
    if linewidths is None: linewidths = ([0.8, 1.0, 1.2] * n)[:n]

    # H is stored as (alpha_bins, h_bins).
    # contour(X, Y, Z) requires Z[i,j] at point (X[j], Y[i]),
    # i.e. Z rows correspond to Y and Z cols to X.
    if axis_order == "h_alpha":
        # x=h, y=α  →  X=h_c, Y=a_c, Z=H  (already (alpha,h) = (rows,cols) ✓)
        X, Y, Z = h_c, a_c, H
    elif axis_order == "alpha_h":
        # x=α, y=h  →  X=a_c, Y=h_c, Z must be (h_bins, alpha_bins) = H.T
        X, Y, Z = a_c, h_c, H.T
    else:
        raise ValueError(f"axis_order must be 'h_alpha' or 'alpha_h', got {axis_order!r}")

    cs = ax.contour(X, Y, Z,
                    levels=sorted(thresholds),
                    colors=colors, linestyles=linestyles,
                    linewidths=linewidths, alpha=contour_alpha,
                    zorder=zorder, **contour_kwargs)

    if labels:
        sorted_t = sorted(thresholds)
        fmt = {t: label_fmt.format(pct=int(levels_frac[list(thresholds).index(t)]*100))
               for t in sorted_t}
        ax.clabel(cs, fmt=fmt, fontsize=7, inline=True, inline_spacing=4)

    return cs


def overlay_lake_scatter(ax, lakes_df,
                          h_col="h_bm",
                          alpha_col="alpha_bm",
                          color_col=None,
                          cmap="tab10",
                          marker="o",
                          size=18,
                          edgecolor="k",
                          edgewidth=0.3,
                          zorder=6,
                          label=None,
                          colorbar=True,
                          ax_cb=None,
                          axis_order="h_alpha",
                          **scatter_kwargs):
    """
    Scatter-plot lake (h, α) positions on an existing phase-space axis.

    Parameters
    ----------
    ax         : matplotlib Axes
    lakes_df   : DataFrame from query_lake_locations()
    h_col      : column name for ice thickness (default 'h_bm')
    alpha_col  : column name for along-flow slope (default 'alpha_bm')
    color_col  : optional column to colour by (e.g. 'region', 'final_label',
                 'elevation', 'area').  If None, all points share one colour.
    cmap       : colormap name (for continuous color_col) or ignored for
                 categorical (which uses tab10 by default)
    marker     : marker style
    size       : marker size (pts²)
    edgecolor  : marker edge colour
    edgewidth  : marker edge linewidth
    zorder     : drawing order
    label      : legend label (used when color_col is None)
    colorbar   : if True and color_col is continuous, add a colorbar
    ax_cb      : axis on which to place the colorbar (defaults to ax)
    axis_order : 'h_alpha' (x=h, y=α) or 'alpha_h' (x=α, y=h).
                 Must match the axis_order passed to overlay_gris_contours.

    Returns
    -------
    sc : PathCollection (scatter return value) or list thereof for categorical
    """
    valid = np.isfinite(lakes_df[h_col]) & np.isfinite(lakes_df[alpha_col])
    df    = lakes_df[valid]

    h_vals = df[h_col].values
    a_vals = df[alpha_col].values

    if axis_order == "h_alpha":
        x_vals, y_vals = h_vals, a_vals
    elif axis_order == "alpha_h":
        x_vals, y_vals = a_vals, h_vals
    else:
        raise ValueError(f"axis_order must be 'h_alpha' or 'alpha_h', got {axis_order!r}")

    if color_col is None:
        sc = ax.scatter(x_vals, y_vals,
                        s=size, marker=marker,
                        edgecolors=edgecolor, linewidths=edgewidth,
                        zorder=zorder, label=label,
                        **scatter_kwargs)
        return sc

    # ── Categorical colour_col ────────────────────────────────────────────────
    col_vals = df[color_col]

    if col_vals.dtype == object or pd.api.types.is_categorical_dtype(col_vals):
        categories = sorted(col_vals.unique())
        palette    = plt.get_cmap(cmap)
        handles    = []
        for k, cat in enumerate(categories):
            mask = (col_vals == cat).values
            c    = palette(k / max(len(categories) - 1, 1))
            sc   = ax.scatter(x_vals[mask], y_vals[mask],
                              s=size, marker=marker, color=c,
                              edgecolors=edgecolor, linewidths=edgewidth,
                              zorder=zorder, label=str(cat),
                              **scatter_kwargs)
            handles.append(sc)
        return handles

    # ── Continuous colour_col ─────────────────────────────────────────────────
    sc = ax.scatter(x_vals, y_vals, c=col_vals.values,
                    s=size, marker=marker, cmap=cmap,
                    edgecolors=edgecolor, linewidths=edgewidth,
                    zorder=zorder, label=label,
                    **scatter_kwargs)
    if colorbar:
        cb_ax = ax_cb if ax_cb is not None else ax
        plt.colorbar(sc, ax=cb_ax, label=color_col, shrink=0.8)

    return sc


# ── Demo ──────────────────────────────────────────────────────────────────────

def demo_plot(bedmachine_path="BedMachineGreenland-v6.nc",
              itslive_path=ITSLIVE_DEFAULT_FILE,
              lakes_csv=None,
              save_path="gris_density_test.pdf"):
    """Full demo: density contours, optionally with lake scatter overlay."""
    grid = build_grid_state(
        bedmachine_path, itslive_path=itslive_path,
        fallback_fullgradient=True,
    )
    contours = get_gris_density_contours(grid=grid)

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.set_xlabel("Ice thickness $h$ (m)", fontsize=11)
    ax.set_ylabel(r"Surface slope $\alpha$ (°)", fontsize=11)
    ax.set_title(
        f"GrIS $(h,\\alpha)$ distribution  [{contours['slope_type']}]\n"
        "BedMachine v6 + ITS_LIVE", fontsize=10
    )
    pcm = ax.pcolormesh(
        contours["h_edges"], contours["alpha_edges"], contours["H"],
        cmap="Blues", shading="flat", rasterized=True,
    )
    plt.colorbar(pcm, ax=ax, label="pixel count")
    overlay_gris_contours(ax, contours)

    if lakes_csv is not None:
        lakes = query_lake_locations(lakes_csv, grid)
        overlay_lake_scatter(ax, lakes, color_col="region",
                             label="lakes", size=12, zorder=7)
        ax.legend(fontsize=7, loc="upper right")

    ax.set_xlim(H_RANGE)
    ax.set_ylim(ALPHA_RANGE)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    print(f"✓ Saved → {save_path}")
    plt.show()


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="BedMachine v6 + ITS_LIVE → GrIS (h,α) along-flow density contours + lake queries"
    )
    p.add_argument("--setup-auth",          action="store_true")
    p.add_argument("--download-bedmachine", action="store_true")
    p.add_argument("--demo",                action="store_true")
    p.add_argument("--token",    default=None)
    p.add_argument("--bm",       default="BedMachineGreenland-v6.nc")
    p.add_argument("--its",      default=ITSLIVE_DEFAULT_FILE,
                   help="Path to ITS_LIVE velocity mosaic (download from https://nsidc.org/apps/itslive/)")
    p.add_argument("--lakes",    default=None,
                   help="Path to lake CSV for demo scatter overlay")
    p.add_argument("--coarsen-bm",  type=int,   default=DEFAULT_COARSEN_BM)
    p.add_argument("--coarsen-its", type=int,   default=DEFAULT_COARSEN_ITS)
    p.add_argument("--min-speed",   type=float, default=MIN_SPEED_MS)
    args = p.parse_args()

    if args.setup_auth:          setup_netrc();                              sys.exit(0)
    if args.download_bedmachine: download_bedmachine(args.bm, args.token);  sys.exit(0)
    if args.demo:                demo_plot(args.bm, args.its, args.lakes);  sys.exit(0)
    p.print_help()
