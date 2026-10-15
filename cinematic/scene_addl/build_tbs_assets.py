#!/usr/bin/env python
"""Bake the Additional-Work assets for the Terminal-Bench Science door and
the JSTARS card.

Inputs — project copies only, originals never touched:
  cinematic/source_data/tbs/aiexplained_Spuza-KwTJ4_0205-0235.mp4
      30 s clip of AI Explained's 2026-09-04 video around 2:18 (see the
      README beside it for the yt-dlp command).
  cinematic/source_data/essd/figs/fig7_architecture.png
      ESSD Fig. 7, the two-stream ConvLSTM classifier (copied by
      cinematic/fetch_sources.sh) — the JSTARS card thumbnail.

Outputs: cinematic/scene_addl/output_tbs/  →  R2 addl/tbs/
  aiexplained_0218.jpg   1920×1080 frame at 2:22 (the Task Lens page for
                         the task with "Hidden answers" lit) — card thumb
                         and door poster
  jstars_arch.jpg        architecture figure, 1600 px wide — JSTARS card

Run:  ./cinematic/.venv/bin/python cinematic/scene_addl/build_tbs_assets.py
then  rsync -a --delete cinematic/scene_addl/output_tbs/ website/.r2-cache/addl/tbs/
      rclone copy cinematic/scene_addl/output_tbs/ r2:<bucket>/addl/tbs/ --checksum --header-upload 'Cache-Control: public, max-age=31536000, immutable'
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'cinematic' / 'source_data'
CLIP = SRC / 'tbs' / 'aiexplained_Spuza-KwTJ4_0205-0235.mp4'
ARCH = SRC / 'essd' / 'figs' / 'fig7_architecture.png'
OUT = ROOT / 'cinematic' / 'scene_addl' / 'output_tbs'
CLIP_T0 = 125.0  # the clip starts at 2:05 of the video
FRAME_T = 142.0  # 2:22 — the page with "5 · Hidden answers" highlighted


def ffmpeg(*args: str) -> None:
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', *args], check=True)


def main() -> None:
    assert CLIP.is_file(), f'missing {CLIP} — see cinematic/source_data/tbs/README.md'
    assert ARCH.is_file(), f'missing {ARCH} — run cinematic/fetch_sources.sh'
    OUT.mkdir(parents=True, exist_ok=True)

    frame = OUT / 'aiexplained_0218.jpg'
    ffmpeg('-ss', f'{FRAME_T - CLIP_T0:.3f}', '-i', str(CLIP), '-frames:v', '1', '-q:v', '2', str(frame))

    arch = OUT / 'jstars_arch.jpg'
    # White figure on the dark site: keep it white (the card crops it), just
    # scale to 1600 px and flatten any alpha onto white.
    ffmpeg('-i', str(ARCH), '-vf', 'format=rgba,pad=iw:ih:0:0:white,scale=1600:-2', '-q:v', '3', str(arch))

    for f in sorted(OUT.iterdir()):
        probe = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
             '-of', 'csv=p=0', str(f)], capture_output=True, text=True, check=True).stdout.strip()
        print(f'{f.name:24s} {probe:>10s}  {f.stat().st_size / 1024:7.0f} KB')


if __name__ == '__main__':
    main()
