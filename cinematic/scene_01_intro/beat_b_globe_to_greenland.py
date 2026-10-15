"""
Scene 1, Beat B — globe rotates to Greenland and zooms in. As we
approach, a high-res Greenland basemap (ESRI World Imagery, polar-
stereographic) fades IN over the Greenland location on the globe;
shortly after, the globe itself fades OUT. End state: just the
high-res Greenland basemap on a clean black background, viewed at
an oblique angle. Beat C will grow the DEM from this surface.

Render:
    cd cinematic
    source .venv/bin/activate
    python scene_01_intro/beat_b_globe_to_greenland.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pyvista as pv  # noqa: E402

from shared import CINEMATIC_DIR, OUTPUT_DIR  # noqa: E402

OUT = OUTPUT_DIR / "01b_globe_to_greenland.mp4"
BASEMAP_PNG = CINEMATIC_DIR / "data" / "greenland_basemap.png"

FPS = 30
DURATION_S = 7.0
N_FRAMES = int(FPS * DURATION_S)

# Camera trajectory.
START_LAT_DEG = 24.2
START_LON_DEG = 0.0
START_D_FACTOR = 5.485
END_LAT_DEG = 55.0       # oblique end angle
END_LON_DEG = -40.0
END_D_FACTOR = 1.7       # zoom in further — basemap takes over before pixelation

# Greenland basemap plane — center matches the PNG's geographic centroid
# (the basemap covers lat 58.5-84, lon -75 to -10 in NorthPolarStereo).
GREENLAND_LAT_DEG = 71.25     # midpoint of the PNG's lat extent
GREENLAND_LON_DEG = -40.0     # PNG's central meridian
PLANE_I_SIZE = 0.36           # east-west, matches 65° lon at lat 71° on globe
PLANE_J_SIZE = 0.44           # north-south, matches 25.5° lat span

# Fade windows (fractions of total duration).
BASEMAP_FADE_IN = (0.40, 0.80)   # basemap fades in mid-motion
GLOBE_FADE_OUT = (0.70, 1.00)    # globe fades out near the end
FOCAL_SHIFT = (0.40, 0.80)       # camera focal point pans from origin to Greenland


def ease_out_cubic(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3


def smoothstep(t: float, a: float, b: float) -> float:
    if t <= a:
        return 0.0
    if t >= b:
        return 1.0
    u = (t - a) / (b - a)
    return u * u * (3.0 - 2.0 * u)


def make_greenland_quad(globe_radius: float):
    """Build a tangent quad at Greenland's surface point on the globe,
    with explicit UVs so the basemap's 'north' aligns with Earth's
    north along the local meridian."""
    lat = np.deg2rad(GREENLAND_LAT_DEG)
    lon = np.deg2rad(GREENLAND_LON_DEG)

    # Surface point (slightly outside sphere so it's visible above the texture).
    r = globe_radius * 1.002
    center = np.array([
        r * np.cos(lat) * np.cos(lon),
        r * np.cos(lat) * np.sin(lon),
        r * np.sin(lat),
    ])

    # Local east (∂/∂lon) and north (∂/∂lat) tangent unit vectors.
    east = np.array([-np.sin(lon), np.cos(lon), 0.0])
    north = np.array([
        -np.sin(lat) * np.cos(lon),
        -np.sin(lat) * np.sin(lon),
        np.cos(lat),
    ])

    half_i = PLANE_I_SIZE * globe_radius / 2.0
    half_j = PLANE_J_SIZE * globe_radius / 2.0

    p_bl = center - east * half_i - north * half_j
    p_br = center + east * half_i - north * half_j
    p_tr = center + east * half_i + north * half_j
    p_tl = center - east * half_i + north * half_j

    points = np.array([p_bl, p_br, p_tr, p_tl])
    faces = np.array([4, 0, 1, 2, 3])
    mesh = pv.PolyData(points, faces=faces)

    # Standard UV: texture (0,0) at bottom-left, (1,1) at top-right.
    mesh.active_texture_coordinates = np.array([
        [0.0, 0.0],
        [1.0, 0.0],
        [1.0, 1.0],
        [0.0, 1.0],
    ])
    return mesh


def main() -> None:
    pv.global_theme.background = "black"
    plotter = pv.Plotter(off_screen=True, window_size=(1920, 1080))

    globe = pv.examples.load_globe()
    globe_texture = pv.examples.load_globe_texture()
    globe_actor = plotter.add_mesh(
        globe, texture=globe_texture, smooth_shading=True
    )
    globe_actor.prop.backface_culling = True

    bounds = globe.bounds
    spans = [bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4]]
    globe_radius = max(spans) / 2.0

    # Greenland's surface position — used as the camera's end focal point.
    g_lat = np.deg2rad(GREENLAND_LAT_DEG)
    g_lon = np.deg2rad(GREENLAND_LON_DEG)
    greenland_pos = globe_radius * np.array([
        np.cos(g_lat) * np.cos(g_lon),
        np.cos(g_lat) * np.sin(g_lon),
        np.sin(g_lat),
    ])

    # Greenland basemap plane.
    quad = make_greenland_quad(globe_radius)
    basemap_texture = pv.read_texture(str(BASEMAP_PNG))
    basemap_actor = plotter.add_mesh(
        quad, texture=basemap_texture, lighting=False
    )
    basemap_actor.prop.opacity = 0.0  # invisible at the start

    plotter.open_movie(str(OUT), framerate=FPS, quality=8)

    for i in range(N_FRAMES):
        t = i / max(1, N_FRAMES - 1)
        e = ease_out_cubic(t)

        lat_deg = START_LAT_DEG + (END_LAT_DEG - START_LAT_DEG) * e
        lon_deg = START_LON_DEG + (END_LON_DEG - START_LON_DEG) * e
        d_factor = START_D_FACTOR + (END_D_FACTOR - START_D_FACTOR) * e

        lat = np.deg2rad(lat_deg)
        lon = np.deg2rad(lon_deg)
        d = d_factor * globe_radius

        cam_x = d * np.cos(lat) * np.cos(lon)
        cam_y = d * np.cos(lat) * np.sin(lon)
        cam_z = d * np.sin(lat)

        # Focal point pans from origin to Greenland during the zoom-in.
        focal_progress = smoothstep(t, *FOCAL_SHIFT)
        focal = greenland_pos * focal_progress

        plotter.camera_position = [
            (cam_x, cam_y, cam_z),
            (float(focal[0]), float(focal[1]), float(focal[2])),
            (0.0, 0.0, 1.0),
        ]

        # Basemap fades in mid-motion (covers Greenland on the globe).
        basemap_actor.prop.opacity = smoothstep(t, *BASEMAP_FADE_IN)

        # Globe fades out near the end (basemap is already in place).
        globe_actor.prop.opacity = 1.0 - smoothstep(t, *GLOBE_FADE_OUT)

        plotter.write_frame()

    plotter.close()
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
