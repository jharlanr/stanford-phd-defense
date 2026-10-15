#!/bin/bash
# Sanctioned copy step (project data rule): bring the published Elmer DEMs
# for lake 2019cw428 into this project's own tree. Reads the sgl-stress
# repo on the lab Google Drive READ-ONLY; never writes there.
set -euo pipefail

LAB_DRIVE="${LAB_DRIVE:-/path/to/your/lab/drive}"
SGL="$LAB_DRIVE/Lab_files/pnas2025/repos/sgl-stress/3d"
SRC="$SGL/simulations/realtopos/2019cw428/dems"
DST="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/data/source_copies"

mkdir -p "$DST"
cp -n "$SRC/2019cw428_bed_d25km_h1004_a0.792.dat" "$DST/" || true
cp -n "$SRC/2019cw428_surface_d25km_h1004_a0.792.dat" "$DST/" || true
ls -la "$DST"
