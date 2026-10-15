#!/bin/bash
# Sanctioned copy step (project data rule): bring the published viscous
# simulation inputs for lake 2019cw428 into this project's own tree.
# Reads the sgl-stress repo on the lab Google Drive READ-ONLY; never writes there.
set -euo pipefail

LAB_DRIVE="${LAB_DRIVE:-/path/to/your/lab/drive}"
SGL="$LAB_DRIVE/Lab_files/pnas2025/repos/sgl-stress/3d"
CASE="$SGL/simulations/realtopos/2019cw428/step1glen_patch"
PROG="$SGL/simulations/realtopos/PROG"
DST="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/data/source_copies"

mkdir -p "$DST/PROG"
cp -n "$CASE/2019cw428_glen_d25km_r2500m_tsic_base.sif" "$DST/" || true
cp -n "$CASE/2019cw428_d25km_r2500m.geo"                "$DST/" || true
cp -n "$PROG/USF_TAVz"     "$DST/PROG/" || true
cp -n "$PROG/USF_TAVz.F90" "$DST/PROG/" || true
ls -la "$DST" "$DST/PROG"
