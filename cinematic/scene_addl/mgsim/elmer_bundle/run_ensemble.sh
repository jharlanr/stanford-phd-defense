#!/bin/bash
# Build the mesh once, then solve the 10 MGSIM bed realizations.
# Run from the bundle directory. Mirrors the conventions in the published
# runsims_localH.sh (docker image andrewdnolan/elmerice).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

DOCKER_IMAGE="${DOCKER_IMAGE:-andrewdnolan/elmerice}"
MAX_PARALLEL="${MAX_PARALLEL:-4}"     # set to 1 if you see any odd mesh I/O
MESH="2019cw428_d25km_r2500m"
NATIVE="${NATIVE:-0}"                 # 1 = tools already on PATH, skip docker

run() {                                # run a command inside the container
  if [[ "$NATIVE" == "1" ]]; then
    "$@"
  else
    docker run --rm --user "$(id -u)":"$(id -g)" \
      -v "$HERE":/work -w /work "$DOCKER_IMAGE" "$@"
  fi
}

############################################
# 1. mesh (identical for all realizations: #
#    the bed enters via bedDEM, not the    #
#    footprint, so it is built once)       #
############################################
if [[ ! -d "$MESH" ]]; then
  echo "==> meshing $MESH.geo"
  run gmsh -1 -2 "$MESH.geo" -o "$MESH.msh"
  run ElmerGrid 14 2 "$MESH.msh" -autoclean
else
  echo "==> mesh $MESH already present, skipping"
fi
[[ -d "$MESH" ]] || { echo "ERROR: mesh directory $MESH was not created"; exit 1; }

############################################
# 2. solve                                 #
############################################
mkdir -p logs
for sif in sifs/*.sif; do
  tag="$(basename "$sif" .sif)"
  if [[ -f "logs/$tag.done" ]]; then echo "==> $tag already done, skipping"; continue; fi
  echo "==> solving $tag"
  (
    if run ElmerSolver "$sif" > "logs/$tag.log" 2>&1; then
      touch "logs/$tag.done"
    else
      echo "FAILED: $tag (see logs/$tag.log)"
    fi
  ) &
  while (( $(jobs -rp | wc -l) >= MAX_PARALLEL )); do wait -n; done
done
wait

echo
echo "==> results:"
ls -la "$MESH"/*_cauchy.vtu 2>/dev/null || ls -la *_cauchy.vtu 2>/dev/null \
  || echo "  (no .vtu found — check logs/)"
echo "==> completeness:"
for sif in sifs/*.sif; do
  tag="$(basename "$sif" .sif)"
  [[ -f "logs/$tag.done" ]] && echo "  ok        $tag" || echo "  INCOMPLETE $tag"
done
