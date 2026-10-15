"""
Scene 1, Beat A — a spinning Earth globe that loops.
First beat of the defense intro. Slidev plays this on loop until the
audience clicks; click advances to beat B (globe → Greenland).

Render:
    cd cinematic
    source .venv/bin/activate
    python scene_01_intro/beat_a_globe_spin.py

Output: output/01a_globe_spin.mp4 (4 seconds at 30 fps, loops cleanly).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pyvista as pv  # noqa: E402

from shared import OUTPUT_DIR  # noqa: E402

OUT = OUTPUT_DIR / "01a_globe_spin.mp4"
FPS = 30
DURATION_S = 12.0      # one full rotation — slow / contemplative
N_FRAMES = int(FPS * DURATION_S)
RADIUS_FACTOR = 5.0    # camera distance as a multiple of globe radius
TILT = 0.45            # northern tilt as a fraction of camera radius


def main() -> None:
    pv.global_theme.background = "black"
    plotter = pv.Plotter(off_screen=True, window_size=(1920, 1080))

    globe = pv.examples.load_globe()
    texture = pv.examples.load_globe_texture()
    plotter.add_mesh(globe, texture=texture, smooth_shading=True)

    # Compute camera distance from the globe's actual size.
    bounds = globe.bounds  # xmin, xmax, ymin, ymax, zmin, zmax
    spans = [bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4]]
    globe_radius = max(spans) / 2.0
    radius = RADIUS_FACTOR * globe_radius

    plotter.open_movie(str(OUT), framerate=FPS, quality=8)

    for i in range(N_FRAMES):
        # Orbit around the polar axis (z), keep camera near the equator
        # with a slight northern tilt. up-vector locked to z = north pole.
        theta = 2 * np.pi * i / N_FRAMES
        cam_x = radius * np.cos(theta)
        cam_y = radius * np.sin(theta)
        cam_z = TILT * radius
        plotter.camera_position = [
            (cam_x, cam_y, cam_z),
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 1.0),
        ]
        plotter.write_frame()

    plotter.close()
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
