#!/bin/zsh
# The Introduction menu card's thumb loop: the director's chosen
# window of the helicopter flyby — GH010200, 2:35–2:45 — as its own 10 s
# file, so the card no longer streams the full 186 MB clip to seek into it.
#
# Source: the R2 mirror of the site's 1080p clip (never the footage drive).
# The cut starts on the frame the old thumb showed after its seek to 155 s
# (pts 154.988 — the frame whose interval holds 155.0) and keeps 300 frames
# (29.97 fps → 10.01 s). 1280×720 = the card's ~553 CSS px at DPR 2 with
# room to spare; CRF 20 → 3.4 MB, SSIM 0.988 vs the source at that size.
# Full-range BT.709 like the GoPro source; no audio; +faststart; frame 0 is
# a keyframe so the native loop restarts instantly.
#
#   zsh cinematic/scene_menu/build_flyby_loop.sh
# then upload (copy, never sync; the cache header on every upload):
#   rclone copy website/.r2-cache/menu/intro r2:<bucket>/menu/intro --include 'flyby_loop_v1.mp4' --header-upload 'Cache-Control: public, max-age=31536000, immutable'
set -e
cd "$(dirname "$0")/../.."
SRC=website/.r2-cache/extras/fieldwork_2023/video/GH010200_1080p.mp4
OUT=website/.r2-cache/menu/intro/flyby_loop_v1.mp4
mkdir -p "$(dirname "$OUT")"
nice -n 15 ffmpeg -hide_banner -loglevel error -y -ss 154.97 -i "$SRC" \
  -map 0:v:0 -frames:v 300 -an -sn -dn \
  -vf "setpts=PTS-STARTPTS,scale=1280:720:flags=lanczos:in_range=pc:out_range=pc" \
  -c:v libx264 -preset slow -crf 20 -profile:v high -level 4.0 \
  -pix_fmt yuvj420p -color_range pc -colorspace bt709 -color_trc bt709 -color_primaries bt709 \
  -g 150 -movflags +faststart -tag:v avc1 -map_metadata -1 "$OUT"
ls -l "$OUT"
