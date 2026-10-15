"""Chapter 1's lake popups without the blank days (the director asked
for the blank days to come out again, for ease of viewing).

The SAME five ESSD fig-4 lakes and the SAME event-cut windows as
build_featured_lakes.py (FEATURED), baked with Chapter 2's valid-frame
recipe (scene_ch02/build_pnas_lakes.py build_valid_movie, the --valid
mode): a day is kept when the stack's own pct_nans < 1 (the whole tile
imaged) — the no-pass days and the swath-edge wedges go, cloudy frames
stay (they are data); 2 fps; the outline burned in the CLASS colour. The
sidecar carries each kept frame's real `day` (days since `t0`) and the
full daily p_water series, so LakeVideoPopup's date badge, volume curve
and marker stay on the calendar. The ND lake's event marker keeps its
'freeze-up' label.

Inputs (local copies only — bash cinematic/fetch_sources.sh):
  cinematic/source_data/stacks/CW_2019/CW2019_{1597,1848,1889,1907,2330}.nc

Outputs (a NEW prefix — R2 objects are immutable for a year):
  cinematic/scene_ch01/output_lakes_valid/<id>.mp4 / .json
      → R2 ch01/lakes_valid/<id>.mp4 / <id>.json

Run (defense checkout root, a Python env with cinematic/requirements.txt installed):
  nice -n 15 python -u \
      cinematic/scene_ch01/build_featured_lakes_valid.py
then
  rclone copy cinematic/scene_ch01/output_lakes_valid \
      r2:<bucket>/ch01/lakes_valid/ --exclude "_frames/**" \
      --header-upload "Cache-Control: public, max-age=31536000, immutable"
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'scene_ch02'))

import build_pnas_lakes as bpl  # noqa: E402  (imports build_featured_lakes as bfl)

bpl.VALID_DIR = Path('cinematic/scene_ch01/output_lakes_valid')


def main() -> None:
    bpl.VALID_DIR.mkdir(parents=True, exist_ok=True)
    for lake in bpl.bfl.FEATURED:
        bpl.build_valid_movie(dict(lake))
    print('\nupload:\n  rclone copy cinematic/scene_ch01/output_lakes_valid '
          'r2:<bucket>/ch01/lakes_valid/ --exclude "_frames/**" '
          '--header-upload "Cache-Control: public, max-age=31536000, immutable"')


if __name__ == '__main__':
    main()
