"""
Standalone preview of the Greenland scale comparator:
  - 2 Californias laid alongside (length comparison)
  - 1 cropped California rotated 90° (width comparison)
  - 6× One World Trade Center stack at Greenland's tallest point (thickness)

Output: cinematic/output/rulers_preview.png

Run:
    cd cinematic
    source .venv/bin/activate
    python scene_01_intro/render_rulers_preview.py
"""

import os
import sys
from pathlib import Path

import certifi

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cartopy.io.shapereader as shapereader  # noqa: E402
import numpy as np  # noqa: E402
import pyvista as pv  # noqa: E402
import xarray as xr  # noqa: E402
from pyproj import Transformer  # noqa: E402
from scipy.ndimage import gaussian_filter  # noqa: E402

from shared import BEDMACHINE_PATH, OUTPUT_DIR  # noqa: E402

OUT = OUTPUT_DIR / "rulers_preview.png"

# ---- Constants ----
EXAG = 60.0
STRIDE = 16
WTC_HEIGHT = 541          # One World Trade Center, m
WTC_COUNT = 6
WTC_FOOTPRINT = 60_000    # 60 km square — at EXAG=60, stack is 195 km tall (3.25:1)


# ---- 1. Greenland DEM -----------------------------------------------
print("Loading BedMachine...")
with xr.open_dataset(BEDMACHINE_PATH) as ds:
    surface = ds["surface"].isel(
        x=slice(None, None, STRIDE), y=slice(None, None, STRIDE)
    ).values
    mask_arr = ds["mask"].isel(
        x=slice(None, None, STRIDE), y=slice(None, None, STRIDE)
    ).values
    xs = ds["x"].values[::STRIDE]
    ys = ds["y"].values[::STRIDE]
print(f"  DEM grid: {surface.shape}")

ice = (mask_arr == 2) | (mask_arr == 3)
land = (mask_arr == 1)
in_gl = ice | land

# Smooth the surface so the coast doesn't render as cliff faces at EXAG=60.
# Gaussian blur of the elevation field within Greenland, zeroed elsewhere.
surface_smooth = gaussian_filter(np.where(in_gl, surface, 0.0).astype(np.float32), sigma=3.0)
Z = np.where(in_gl, surface_smooth, np.nan) * EXAG
nx, ny = len(xs), len(ys)

print("Building PyVista mesh...")
X, Y = np.meshgrid(xs, ys)
points = np.column_stack([X.ravel(), Y.ravel(), np.nan_to_num(Z, nan=0.0).ravel()])
grid = pv.StructuredGrid()
grid.points = points
grid.dimensions = (nx, ny, 1)
grid["elevation"] = np.where(in_gl, surface, 0.0).ravel()
grid["mask"] = in_gl.astype(np.int32).ravel()
glmesh = grid.threshold(0.5, scalars="mask")


# ---- 2. California polygon ------------------------------------------
print("Loading California polygon...")
shp = shapereader.natural_earth(
    resolution="10m", category="cultural", name="admin_1_states_provinces"
)
ca_geom = None
for rec in shapereader.Reader(shp).records():
    attrs = rec.attributes
    if (
        attrs.get("name") == "California"
        and attrs.get("admin") == "United States of America"
    ):
        ca_geom = rec.geometry
        break
if ca_geom is None:
    raise RuntimeError("California polygon not found")

ca_centroid = ca_geom.centroid
to_local = Transformer.from_crs(
    "EPSG:4326",
    f"+proj=aeqd +lat_0={ca_centroid.y} +lon_0={ca_centroid.x} +x_0=0 +y_0=0",
    always_xy=True,
)


def project_polygon_to_local(geom):
    """Pick the largest exterior ring; project to local AEQD meters."""
    if geom.geom_type == "Polygon":
        coords = np.array(geom.exterior.coords)
    else:  # MultiPolygon — pick largest by point count
        biggest = max(geom.geoms, key=lambda p: len(p.exterior.coords))
        coords = np.array(biggest.exterior.coords)
    lon, lat = coords[:, 0], coords[:, 1]
    x, y = to_local.transform(lon, lat)
    return np.column_stack([x, y])


ca_xy_local = project_polygon_to_local(ca_geom)
ca_x_min, ca_y_min = ca_xy_local.min(axis=0)
ca_x_max, ca_y_max = ca_xy_local.max(axis=0)
ca_length = ca_y_max - ca_y_min
ca_width = ca_x_max - ca_x_min
print(f"  California N-S length: {ca_length/1000:.0f} km")
print(f"  California E-W width:  {ca_width/1000:.0f} km")


def center(xy):
    cx = (xy[:, 0].min() + xy[:, 0].max()) / 2
    cy = (xy[:, 1].min() + xy[:, 1].max()) / 2
    return xy - np.array([cx, cy])


ca_centered = center(ca_xy_local)


# ---- 3. Place rulers in Greenland's EPSG:3413 frame -----------------
gl_x_min, gl_x_max = xs.min(), xs.max()
gl_y_min, gl_y_max = ys.min(), ys.max()
gl_length = gl_y_max - gl_y_min
gl_width = gl_x_max - gl_x_min
print(f"  Greenland N-S length:  {gl_length/1000:.0f} km")
print(f"  Greenland E-W width:   {gl_width/1000:.0f} km")
print(f"  2× CA / Greenland length ratio: {2*ca_length/gl_length:.2f}")

# Two Californias stacked N-S, east of Greenland, alongside the length axis
LENGTH_OFFSET = 250_000  # 250 km east buffer
ca_center_x = gl_x_max + LENGTH_OFFSET + ca_width / 2
ca_total_length = 2 * ca_length
ca_stack_y0 = gl_y_min + (gl_length - ca_total_length) / 2  # vertically centered
ca_xy_north = ca_centered + np.array([ca_center_x, ca_stack_y0 + 1.5 * ca_length])
ca_xy_south = ca_centered + np.array([ca_center_x, ca_stack_y0 + 0.5 * ca_length])

# Width ruler: rotate California 90° (so its N-S length aligns with E-W axis),
# then keep only ~85% of it (the director's framing: ~70% of California ≈ Greenland's width).
ca_rot = np.column_stack([ca_centered[:, 1], -ca_centered[:, 0]])
WIDTH_FRACTION = 0.85
rot_x_min, rot_x_max = ca_rot[:, 0].min(), ca_rot[:, 0].max()
threshold = rot_x_min + WIDTH_FRACTION * (rot_x_max - rot_x_min)
# Don't crop the polygon — keep its full shape so the audience sees California's
# silhouette laid sideways. We'll just position so the visible "matching" portion
# spans Greenland's width.
WIDTH_OFFSET = 100_000  # 100 km buffer south of Greenland's southern coast
rot_height = ca_rot[:, 1].max() - ca_rot[:, 1].min()
width_x_center = (gl_x_min + gl_x_max) / 2
width_y_center = gl_y_min - WIDTH_OFFSET - rot_height / 2
ca_xy_width = ca_rot + np.array([width_x_center, width_y_center])


# ---- 4. WTC stack at Greenland's tallest point -----------------------
masked_surface = np.where(ice, surface, -np.inf)
peak_iy, peak_ix = np.unravel_index(np.argmax(masked_surface), masked_surface.shape)
peak_x = xs[peak_ix]
peak_y = ys[peak_iy]
peak_z = surface[peak_iy, peak_ix]
print(f"  Tallest ice point: ({peak_x/1000:.0f}, {peak_y/1000:.0f}) km, "
      f"elevation {peak_z:.0f} m")

# Place stack just east of peak (so it sits on the ice surface, not inside it)
STACK_X = peak_x + 200_000
STACK_Y = peak_y
WTC_GAP = 0  # no gap — this is a unified stack, with white tier-lines


# ---- 5. PyVista render ----------------------------------------------
print("Rendering scene...")
pv.global_theme.allow_empty_mesh = True
plotter = pv.Plotter(off_screen=True, window_size=(2400, 1500))
plotter.set_background("#06101e")

# Greenland: bone colormap by elevation
plotter.add_mesh(
    glmesh,
    scalars="elevation",
    cmap="bone",
    clim=(0, 3300),
    show_scalar_bar=False,
    smooth_shading=True,
    ambient=0.30,
    diffuse=0.75,
    specular=0.10,
    specular_power=8,
)


def add_polygon_at_z(xy, z, color, opacity=0.85, edge_color="white", edge_width=1.5):
    """Add a flat polygon. Uses delaunay_2d to triangulate."""
    n = xy.shape[0]
    pts = np.column_stack([xy[:, 0], xy[:, 1], np.full(n, z)])
    cloud = pv.PolyData(pts)
    surf = cloud.delaunay_2d()
    plotter.add_mesh(
        surf,
        color=color,
        opacity=opacity,
        show_edges=False,
        ambient=0.4,
        diffuse=0.6,
    )
    # Outline as a closed polyline
    line_pts = np.vstack([pts, pts[:1]])
    n_line = line_pts.shape[0]
    cells = np.hstack([[n_line], np.arange(n_line)])
    line = pv.PolyData(line_pts, lines=cells)
    plotter.add_mesh(line, color=edge_color, line_width=edge_width)


# Two Californias for length, one rotated for width
RULER_Z = 50.0 * EXAG  # 50 m above sea level — sits above the ocean plane
LENGTH_RED = "#c8412c"
WIDTH_RED = "#df6243"

add_polygon_at_z(ca_xy_north, RULER_Z, LENGTH_RED)
add_polygon_at_z(ca_xy_south, RULER_Z, LENGTH_RED)
add_polygon_at_z(ca_xy_width, RULER_Z, WIDTH_RED)


# WTC stack: 6 separate cubes stacked, alternating shade so each tier reads
WTC_PER_TIER_Z = WTC_HEIGHT * EXAG  # display height of a single OWTC
TIER_GAP = WTC_PER_TIER_Z * 0.06    # small gap so tiers visually separate
wtc_colors = ["#a8b0b8", "#7d858f"]  # alternating
for i in range(WTC_COUNT):
    z_bottom = i * (WTC_PER_TIER_Z + TIER_GAP)
    z_top = z_bottom + WTC_PER_TIER_Z
    cube = pv.Cube(
        center=(STACK_X, STACK_Y, (z_bottom + z_top) / 2),
        x_length=WTC_FOOTPRINT,
        y_length=WTC_FOOTPRINT,
        z_length=WTC_PER_TIER_Z,
    )
    plotter.add_mesh(
        cube,
        color=wtc_colors[i % 2],
        ambient=0.35,
        diffuse=0.55,
        specular=0.55,
        specular_power=18,
    )


# Reference: a thin disc at z=0 spanning the rulers (gives the "ocean / table")
ALL_X = np.concatenate([
    np.array([gl_x_min, gl_x_max]),
    ca_xy_north[:, 0], ca_xy_south[:, 0], ca_xy_width[:, 0],
])
ALL_Y = np.concatenate([
    np.array([gl_y_min, gl_y_max]),
    ca_xy_north[:, 1], ca_xy_south[:, 1], ca_xy_width[:, 1],
])
table_x = (ALL_X.min() - 2e5, ALL_X.max() + 2e5)
table_y = (ALL_Y.min() - 2e5, ALL_Y.max() + 2e5)
table = pv.Plane(
    center=((table_x[0] + table_x[1]) / 2, (table_y[0] + table_y[1]) / 2, -100),
    direction=(0, 0, 1),
    i_size=table_x[1] - table_x[0],
    j_size=table_y[1] - table_y[0],
)
plotter.add_mesh(table, color="#0c1a2e", ambient=0.5, opacity=1.0)


# Camera: SE oblique, matching the website's Motivation-section angle so
# Greenland reads as the elevated mound the audience already knows. Eye
# is south-east of the focal, ~38° elevation.
focal_x = (gl_x_min + gl_x_max) / 2 + 4e5   # bias east toward length rulers
focal_y = (gl_y_min + gl_y_max) / 2 - 3e5   # slight south for width ruler
focal_z = 1.5e5
eye_x = focal_x + 1.6e6
eye_y = focal_y - 2.8e6
eye_z = 2.4e6
plotter.camera_position = [
    (eye_x, eye_y, eye_z),
    (focal_x, focal_y, focal_z),
    (0, 0, 1),
]
plotter.add_light(pv.Light(
    position=(focal_x - 2e6, focal_y + 2e6, 4e6),
    focal_point=(focal_x, focal_y, 0),
    color="white",
    intensity=0.9,
))

# ---- 6. Screen-space caption text -----------------------------------
plotter.add_text(
    "Greenland: a sense of scale",
    position="upper_edge",
    font_size=22,
    color="white",
    font="arial",
)
plotter.add_text(
    "More than 2 Californias long\n"
    "More than 1 California wide\n"
    "6 One World Trade Centers tall",
    position="lower_left",
    font_size=14,
    color="#e8b94a",
    font="arial",
)

print(f"Saving to {OUT}")
plotter.show(screenshot=str(OUT), auto_close=True)
print("Done.")
