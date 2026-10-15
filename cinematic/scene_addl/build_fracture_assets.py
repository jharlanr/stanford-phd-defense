#!/usr/bin/env python
"""Bake the Additional-Work assets for the fracture / stream mapping card
and its door, /additional-work/fracture.

The work: I. Xia, J. H. Rines, C.-Y. Lai, R. Culberg, AGU Fall Meeting
2024, C41D-0203 — a two-output U-Net on ~0.5 m WorldView-1 / QuickBird-2
panchromatic scenes. The imagery is commercial (Maxar, via the Polar
Geospatial Center): every derivative carries "Imagery © Maxar" burned
into its pixels, and nothing here approaches the scene's native
resolution (the whole-scene maps are ~1/25 of it).

Inputs — project COPIES only, the originals are never touched:
  cinematic/source_data/fracture/training_viz.mp4
      2560 x 2560, 59 frames @ 5 fps: a 10 x 10 block of 256 px tiles,
      one frame per saved checkpoint (create_visualization.ipynb walks
      epochs 1-60), fractures red, streams blue.
      (copy of ${SOURCE_ROOT}/streams-vs-fractures/assets/)
  cinematic/source_data/fracture/iona_result.mov
      2716 x 1740 screen recording, three hard-cut states of 3 s each:
      the scene, the fracture map, the stream map (white on black).
      (copy of ${SOURCE_ROOT}/fd_cnn/)

Outputs: cinematic/output/fracture/{fracture,cards}/  ->  R2 addl/
  fracture/training_epochs.mp4         960 sq, 30 fps (frames blended), the hero
  fracture/training_epochs_poster.jpg  its last frame
  fracture/scene_maps.mp4              whole scene -> fractures (red) ->
                                       streams (blue) -> both, one loop
  fracture/scene_maps_poster.jpg       the "both" state
  cards/fracture_loop.mp4              360 sq card thumb, centre crop of the hero

A worktree has no source_data of its own: point FRACTURE_SRC at the main
checkout's copy.

Run:  ./cinematic/.venv/bin/python cinematic/scene_addl/build_fracture_assets.py
then copy the NEW files into website/.r2-cache/addl/ and
      rclone copy cinematic/output/fracture/ r2:<bucket>/addl/ --checksum --header-upload 'Cache-Control: public, max-age=31536000, immutable'
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(os.environ.get('FRACTURE_SRC', ROOT / 'cinematic' / 'source_data' / 'fracture'))
VIZ = SRC / 'training_viz.mp4'
RESULT = SRC / 'iona_result.mov'
OUT = ROOT / 'cinematic' / 'output' / 'fracture'
WORK = OUT / '_work'

CREDIT = 'Imagery © Maxar'
FONT = '/System/Library/Fonts/Supplemental/Arial.ttf'
RED = np.array([255, 48, 48], dtype=np.float32)
BLUE = np.array([64, 120, 255], dtype=np.float32)

# The result movie's three states (hard cuts at 3 s and 6 s).
T_SCENE, T_FRACTURE, T_STREAM = 1.5, 4.5, 7.5
MAPS_W = 1280
MAPS_FPS = 24


def ffmpeg(*args: str) -> None:
    subprocess.run(['nice', '-n', '15', 'ffmpeg', '-loglevel', 'error', '-y', *args], check=True)


def credit_png(dest: Path, size_px: int) -> None:
    """The credit as a small translucent plate, to overlay bottom-right."""
    font = ImageFont.truetype(FONT, size_px)
    box = font.getbbox(CREDIT)
    pad = round(size_px * 0.45)
    w, h = box[2] - box[0] + 2 * pad, box[3] - box[1] + 2 * pad
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=pad, fill=(0, 0, 0, 150))
    d.text((pad - box[0], pad - box[1]), CREDIT, font=font, fill=(255, 255, 255, 235))
    img.save(dest)


def stamp(img: Image.Image, size_px: int) -> Image.Image:
    plate = WORK / f'credit_{size_px}.png'
    if not plate.exists():
        credit_png(plate, size_px)
    p = Image.open(plate)
    out = img.convert('RGBA')
    m = round(size_px * 0.7)
    out.alpha_composite(p, (out.width - p.width - m, out.height - p.height - m))
    return out.convert('RGB')


def bake_training() -> None:
    hero = OUT / 'fracture' / 'training_epochs.mp4'
    plate = WORK / 'credit_20.png'
    credit_png(plate, 20)
    # 5 fps checkpoints blended up to 30 fps so the maps sharpen smoothly;
    # a short GOP keeps the scrub bar's seeks tight.
    ffmpeg(
        '-i', str(VIZ), '-i', str(plate),
        '-filter_complex',
        '[0:v]scale=960:960:flags=lanczos,framerate=fps=30[v];[v][1:v]overlay=W-w-16:H-h-16,format=yuv420p[o]',
        '-map', '[o]', '-an', '-c:v', 'libx264', '-preset', 'slow', '-crf', '29',
        '-g', '15', '-movflags', '+faststart', str(hero),
    )
    ffmpeg('-sseof', '-0.2', '-i', str(hero), '-frames:v', '1', '-update', '1', '-q:v', '3',
           str(OUT / 'fracture' / 'training_epochs_poster.jpg'))

    # Card thumb: the centre 1280 px of the block, so single cracks still
    # read at card size. Plays forward then holds the last frame 2 s.
    plate_s = WORK / 'credit_11.png'
    credit_png(plate_s, 11)
    ffmpeg(
        '-i', str(VIZ), '-i', str(plate_s),
        '-filter_complex',
        '[0:v]crop=1280:1280:640:640,scale=360:360:flags=lanczos,framerate=fps=24,'
        'tpad=stop_mode=clone:stop_duration=2[v];[v][1:v]overlay=W-w-6:H-h-6,format=yuv420p[o]',
        '-map', '[o]', '-an', '-c:v', 'libx264', '-preset', 'slow', '-crf', '30',
        '-movflags', '+faststart', str(OUT / 'cards' / 'fracture_loop.mp4'),
    )


def grab(t: float, name: str) -> np.ndarray:
    dest = WORK / name
    ffmpeg('-ss', f'{t:.2f}', '-i', str(RESULT), '-frames:v', '1', '-update', '1', str(dest))
    return np.asarray(Image.open(dest).convert('L'), dtype=np.float32)


def bake_maps() -> None:
    scene = grab(T_SCENE, 'state_scene.png')
    frac = grab(T_FRACTURE, 'state_fracture.png')
    strm = grab(T_STREAM, 'state_stream.png')

    # Crop to the scene's footprint (the recording has a black surround).
    ys, xs = np.where(scene > 12)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    h = round(MAPS_W * (y1 - y0) / (x1 - x0) / 2) * 2

    def fit(a: np.ndarray) -> np.ndarray:
        im = Image.fromarray(a[y0:y1, x0:x1].astype(np.uint8)).resize((MAPS_W, h), Image.LANCZOS)
        return np.asarray(im, dtype=np.float32) / 255.0

    scene, frac, strm = fit(scene), fit(frac), fit(strm)
    inside = (scene > 0.05).astype(np.float32)
    # Map strength: lift the thin lines so they survive the downsample.
    frac = np.clip(frac * 1.6, 0, 1) * inside
    strm = np.clip(strm * 2.2, 0, 1) * inside

    def frame(dim: float, a_f: float, a_s: float) -> Image.Image:
        base = scene * (1.0 - 0.72 * dim)
        rgb = np.repeat(base[..., None], 3, axis=2) * 255.0
        for strength, colour, a in ((frac, RED, a_f), (strm, BLUE, a_s)):
            k = (strength * a)[..., None]
            rgb = rgb * (1 - k) + colour * k
        return stamp(Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)), 18)

    # (seconds, dim, fractures, streams) keyframes; the loop closes on the scene.
    keys = [
        (0.0, 0, 0, 0), (1.6, 0, 0, 0),
        (3.0, 1, 1, 0), (5.2, 1, 1, 0),
        (6.6, 1, 0, 1), (8.8, 1, 0, 1),
        (10.2, 1, 1, 1), (13.0, 1, 1, 1),
        (14.4, 0, 0, 0),
    ]
    frames = WORK / 'maps'
    frames.mkdir(exist_ok=True)
    for f in frames.glob('*.png'):
        f.unlink()
    n = round(keys[-1][0] * MAPS_FPS)
    for i in range(n):
        t = i / MAPS_FPS
        for (ta, *a), (tb, *b) in zip(keys, keys[1:]):
            if ta <= t <= tb:
                u = (t - ta) / (tb - ta)
                u = u * u * (3 - 2 * u)
                vals = [pa + (pb - pa) * u for pa, pb in zip(a, b)]
                break
        frame(*vals).save(frames / f'{i:04d}.png', compress_level=1)

    ffmpeg('-framerate', str(MAPS_FPS), '-i', str(frames / '%04d.png'), '-an',
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '27', '-pix_fmt', 'yuv420p',
           '-g', '24', '-movflags', '+faststart', str(OUT / 'fracture' / 'scene_maps.mp4'))
    frame(1, 1, 1).save(OUT / 'fracture' / 'scene_maps_poster.jpg', quality=86)


def main() -> None:
    for f in (VIZ, RESULT):
        assert f.is_file(), f'missing {f} — copy it from the research folder (see the header)'
    for d in (OUT / 'fracture', OUT / 'cards', WORK):
        d.mkdir(parents=True, exist_ok=True)
    bake_training()
    bake_maps()
    for f in sorted([*(OUT / 'fracture').iterdir(), *(OUT / 'cards').iterdir()]):
        probe = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
             '-of', 'csv=p=0', str(f)], capture_output=True, text=True, check=True).stdout.strip()
        print(f'{f.parent.name}/{f.name:32s} {probe:>10s}  {f.stat().st_size / 1024:7.0f} KB')


if __name__ == '__main__':
    main()
