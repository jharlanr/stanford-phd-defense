#!/bin/bash
# One-time fetch of every private source dataset the cinematic/ pipelines
# read, copied into cinematic/source_data/ (gitignored).
#
# RULE: the original data directories (lab Google
# Drive, Oak, external drives) are NEVER referenced, linked, or modified
# by any pipeline. This script is the single sanctioned copy step; every
# build script reads only from cinematic/source_data/.
#
# Run:  bash cinematic/fetch_sources.sh
# Sizes: BedMachine 2.9 GB · ITS_LIVE 3.9 GB · glen_400km VTUs ~1 GB ·
#        newt_400km VTUs ~6.8 GB · JOG manuscript ~13 MB.
# Drive-streamed files hydrate from the cloud on first copy — be patient.

set -euo pipefail

# The two private roots every source path below hangs off. Set them in the
# environment; the defaults are placeholders.
LAB_DRIVE="${LAB_DRIVE:-/path/to/your/lab/drive}"              # the lab's shared drive (a Google Drive mount)
CLUSTER_MOUNT="${CLUSTER_MOUNT:-/path/to/your/cluster/mount}"  # the cluster's project storage (an SMB mount)
LAB_2D="$LAB_DRIVE/Lab_files/pnas2025/repos/sgl-stress/2d"
OAK_STACKS="$CLUSTER_MOUNT/sherlock_sattilestack/stacks_v2"
DST="$(cd "$(dirname "$0")" && pwd)/source_data"

# ── Ch.2 slab v2: ONE raw Elmer/Ice VTU at a time ────────────────────────
# The talk's cumulative depth average (ch02/slab_v2/) needs every node
# layer of the 3-D field, which only the raw VTUs hold (~240–280 MB each,
# 75 on the Drive, ~19 GB — too much to stage at once on this disk). So
# this is a separate MODE, not part of the full fetch:
#   bash cinematic/fetch_sources.sh slab_vtu R2500_H1000_a10_G01   # stage one copy
#   bash cinematic/fetch_sources.sh slab_vtu_warm R2500_H1000_a10_G01  # read-only hydrate, no copy
# → source_data/pnas_slab/vtu/flatslabnewt_<id>_periodicBC_t0001.vtu (read-only
# copy, chmod a-w). The consumer (scene_ch02/build_slab_v2.py) deletes its
# staged copy after baking that run; the Drive is only ever READ.
# BEGIN slab_vtu
SLAB_VTU_SRC="$LAB_DRIVE/Lab_files/pnas2025/elmer/postprocess/flatslabnewt/vtufiles"
if [ "${1:-}" = "slab_vtu" ] || [ "${1:-}" = "slab_vtu_warm" ]; then
  RUN="${2:?usage: fetch_sources.sh slab_vtu <RUN_ID e.g. R2500_H1000_a10_G01>}"
  F="flatslabnewt_${RUN}_periodicBC_t0001.vtu"
  [ -f "$SLAB_VTU_SRC/$F" ] || { echo "no such VTU on the Drive: $F" >&2; exit 2; }
  if [ "$1" = "slab_vtu_warm" ]; then
    cat "$SLAB_VTU_SRC/$F" > /dev/null   # makes Drive hydrate it; writes nothing
    exit 0
  fi
  VDST="$DST/pnas_slab/vtu"
  mkdir -p "$VDST"
  if [ ! -f "$VDST/$F" ]; then
    rsync -a --partial-dir=.rsync-partial "$SLAB_VTU_SRC/$F" "$VDST/"
    chmod a-w "$VDST/$F"
  fi
  echo "$VDST/$F"
  exit 0
fi
# END slab_vtu

mkdir -p "$DST/data" "$DST/results/glen_400km" "$DST/results/newt_400km" \
  "$DST/manuscript_jog"

rsync -av --ignore-existing \
  "$LAB_2D/data/BedMachineGreenland-v6.nc" \
  "$LAB_2D/data/ITS_LIVE_velocity_120m_RGI05A_0000_V02.1.nc" \
  "$LAB_2D/data/labels_2019_volumes.csv" \
  "$DST/data/"

rsync -av --ignore-existing \
  "$LAB_2D/elmer/postprocess/results/glen_400km/" \
  "$DST/results/glen_400km/"

# Newtonian (n=1) ensemble — Ch.1 theory beats show n=1 results.
rsync -av --ignore-existing \
  "$LAB_2D/elmer/postprocess/results/newt_400km/" \
  "$DST/results/newt_400km/"

# JOG manuscript (equations 7/12/46, figs 1 & 4 drive the theory beats).
rsync -av --ignore-existing \
  "$LAB_2D/jog/revision02/main.tex" \
  "$LAB_2D/jog/revision02/paper_jog.bib" \
  "$LAB_2D/jog/revision02/Longitudinal_stress_induced_by_basal_slippery_patch.pdf" \
  "$DST/manuscript_jog/"

# JOG FINAL (accepted, JOG-2026-0047, July 2026): the tex, the ten figure
# PNGs and the final PDF — the Additional-Work "deeper dive" page for
# Chapter 1 (cinematic/scene_addl/build_deeper_ch01.py) shows these figures.
JOG_FINAL="$LAB_2D/jog/revision_final"
mkdir -p "$DST/manuscript_jog/final/figs"
rsync -av --ignore-existing \
  "$JOG_FINAL/Longitudinal_stress_induced_by_basal_slippery_patch/202607_final/JOG-2026-0047.tex" \
  "$JOG_FINAL/Longitudinal_stress_induced_by_basal_slippery_patch.pdf" \
  "$DST/manuscript_jog/final/"
rsync -av --ignore-existing \
  "$JOG_FINAL/Longitudinal_stress_induced_by_basal_slippery_patch/202607_final/figs/" \
  "$DST/manuscript_jog/final/figs/"

# PNAS (Chapter 2) figure files for the Additional-Work "deeper dive" page
# (cinematic/scene_addl/build_deeper_ch02.py): Chapter 2 of the THESIS
# (tex + every figure PNG, the thesis's Overleaf zip), the PNAS main-text figures
# and the SI figure files (the two PNAS Overleaf zips). unzip -n never
# overwrites an existing copy.
DISS="${THESIS_ZIPS:-/path/to/your/overleaf/zips}"   # where the three Overleaf exports sit
THESIS_ZIP="${THESIS_ZIP:-PhD_Thesis.zip}"            # the thesis project's Overleaf export
mkdir -p "$DST/manuscript_pnas"
unzip -n -q "$DISS/$THESIS_ZIP" 'chapters/chapter2/*' \
  -d "$DST/manuscript_pnas/thesis"
unzip -n -q "$DISS/Lake_pnas.zip" 'Fig*.png' main.tex -d "$DST/manuscript_pnas/main"
unzip -n -q "$DISS/Lake_pnas_SI.zip" 'SI_Figures/*' main.tex -d "$DST/manuscript_pnas/si"

# Sentinel-2 timestacks (lake-drain movie sources, Oak) — the five
# ESSD fig-4 representative lakes, one per drainage class:
#   CW2019_1597 ND · CW2019_1889 HF (North Lake) · CW2019_1848 MD ·
#   CW2019_1907 LD · CW2019_2330 CD          (~750 MB total)
if [ -d "$OAK_STACKS" ]; then
  mkdir -p "$DST/stacks/CW_2019"
  rsync -av --ignore-existing \
    "$OAK_STACKS/CW_2019/CW2019_1597.nc" \
    "$OAK_STACKS/CW_2019/CW2019_1848.nc" \
    "$OAK_STACKS/CW_2019/CW2019_1889.nc" \
    "$OAK_STACKS/CW_2019/CW2019_1907.nc" \
    "$OAK_STACKS/CW_2019/CW2019_2330.nc" \
    "$OAK_STACKS/CW_2019_centroids.csv" \
    "$DST/stacks/CW_2019/"
else
  echo "WARN: Oak not mounted — skipping lake timestacks (movie sources)"
fi

# ── Ch.2 (PNAS) sources ─────────────────────────────────────────────────
# The seven simulated "center lakes" of the PNAS paper (all englacial/HF
# drainages). Old sim numbering = Dunmire new_id − 1523:
#   2019cw387↔1910 · 428↔1951 · 871↔2394 · 888↔2411 · 893↔2416 ·
#   988↔2511 · 997↔2520
# (a) Sentinel-2 timestacks for the popup movies (~1 GB total);
# (b) processed elastic blister netCDFs — the PUBLISHED runs
#     (E = 3.077 GPa, per-lake tuned P_w, localh; ~150 MB each);
# (c) per-lake tile georeferencing attrs (center lon/lat, EPSG:3413
#     extent, flow angle) pulled from the lake-tiles H5 into one small
#     JSON (the 6.8 GB H5 itself is NOT copied).
LAB_3D="$LAB_DRIVE/Lab_files/pnas2025/repos/sgl-stress/3d"
PNAS_LAKES_OLD="387 428 871 888 893 988 997"

if [ -d "$OAK_STACKS" ]; then
  mkdir -p "$DST/stacks/CW_2019"
  rsync -av --ignore-existing \
    "$OAK_STACKS/CW_2019/CW2019_1910.nc" \
    "$OAK_STACKS/CW_2019/CW2019_1951.nc" \
    "$OAK_STACKS/CW_2019/CW2019_2394.nc" \
    "$OAK_STACKS/CW_2019/CW2019_2411.nc" \
    "$OAK_STACKS/CW_2019/CW2019_2416.nc" \
    "$OAK_STACKS/CW_2019/CW2019_2511.nc" \
    "$OAK_STACKS/CW_2019/CW2019_2520.nc" \
    "$DST/stacks/CW_2019/"
else
  echo "WARN: Oak not mounted — skipping Ch.2 lake timestacks"
fi

if [ -d "$LAB_3D" ]; then
  mkdir -p "$DST/pnas_sims"
  for n in $PNAS_LAKES_OLD; do
    rsync -av --ignore-existing \
      "$LAB_3D/elmer/sim_data/elastic/realtopos/processed/ncfiles/youngsmod_3p077e9/elastic_2019cw${n}_d25km_r2500m_youngmod3.077e3_elastic_localh.nc" \
      "$DST/pnas_sims/"
  done
  # The published VISCOUS runs (t_sic snapshot; per-lake csi in
  # the filename). Same processed structure (case nopatch/patch,
  # level surf/da, stresses MPa).
  for pair in 387:5.4e6 428:6.5e6 871:8.5e6 888:8.5e6 893:7.5e6 988:8.6e6 997:6.7e6; do
    n="${pair%%:*}"; csi="${pair##*:}"
    rsync -av --ignore-existing \
      "$LAB_3D/elmer/sim_data/viscous/realtopos/processed/ncfiles/stress_response/2019cw${n}_d25km_r2500m_csi${csi}_tsic_viscous.nc" \
      "$DST/pnas_sims/"
  done
  # The boundary-condition cards: the run INPUTS behind every
  # boundary condition the cards quote — the viscous + elastic .sif files,
  # the elastic run script (its sed table holds the blister BCs), the SIA
  # wall-profile user function, and the 166 x 166 x 150 m Elmer input DEMs
  # (surface, bed, the published blister bed) per lake.
  # → cinematic/scene_ch02/build_bc_cards.py
  mkdir -p "$DST/pnas_sims/bc"
  RT="$LAB_3D/simulations/realtopos"
  for pair in 387:1p0378 428:1p0276 871:1p0164 888:1p0306 893:1p0309 988:1p0298 997:1p0257; do
    n="${pair%%:*}"; pw="${pair##*:}"
    rsync -a --ignore-existing \
      "$RT/2019cw$n/step1glen_patch/2019cw${n}_glen_d25km_r2500m_tsic_base.sif" \
      "$RT/2019cw$n/step2elastic/elastic_sif_template_2019cw${n}.sif" \
      "$DST/pnas_sims/bc/"
    rsync -a --ignore-existing "$RT/2019cw$n/step2elastic/runsims_localH.sh" \
      "$DST/pnas_sims/bc/runsims_localH_2019cw${n}.sh"
    for f in "$RT/2019cw$n/dems/2019cw${n}"_{bed,surface}_d25km_h*_a*.dat \
             "$RT/2019cw$n/dems/2019cw${n}"_bedplusblister_*_pw${pw}_r2500m.dat; do
      case "$f" in *a89.977*) continue ;; esac  # (an unrelated raised-cosine test)
      rsync -a --ignore-existing "$f" "$DST/pnas_sims/bc/"
    done
  done
  rsync -a --ignore-existing "$RT/PROG/USF_TAVz.F90" "$RT/rerun_elastic_3077.sh" "$DST/pnas_sims/bc/"
  if [ ! -f "$DST/pnas_sims/tile_attrs.json" ]; then
    "$(dirname "$0")/.venv/bin/python" - "$LAB_3D" "$DST" <<'PYEOF'
import json, sys
import h5py
lab3d, dst = sys.argv[1], sys.argv[2]
h5 = (lab3d + '/elmer/data/'
      'lake_tiles_alongflow_summer2019_bedmach5_circularmean_25.0kmx25.0km.h5')
out = {}
with h5py.File(h5, 'r') as f:
    for n in [387, 428, 871, 888, 893, 988, 997]:
        g = f[f'2019cw_{n}']
        a = {k: (v.item() if hasattr(v, 'item') else str(v))
             for k, v in g.attrs.items()}
        out[f'2019cw{n}'] = {
            'new_id': f'CW2019_{n + 1523}',
            'lon': a['lon'], 'lat': a['lat'],
            'flow_angle_deg': a['flow_angle_deg'],
            'extent_xmin': a['extent_xmin'], 'extent_xmax': a['extent_xmax'],
            'extent_ymin': a['extent_ymin'], 'extent_ymax': a['extent_ymax'],
        }
with open(dst + '/pnas_sims/tile_attrs.json', 'w') as fo:
    json.dump(out, fo, indent=1)
print('wrote', dst + '/pnas_sims/tile_attrs.json')
PYEOF
  fi
else
  echo "WARN: lab Google Drive (3d) not mounted — skipping Ch.2 sims"
fi

# ── PNAS figure-source data (S2 imagery + per-lake stresses) ────────────
# (a) 30-km Sentinel-2 truecolor timestacks for the 7 center-lake tiles
#     (~1 GB each) — pre/post-drain block-face imagery, dates per
#     making_pnas_figs (871: 06/13-06/19 · 428: 07/04-07/08 · 893 & 988:
#     08/18-08/23 · 997: 07/04-07/08 · 888: 08/01-08/05 · 387: 07/21-07/23);
# (b) per-lake in-polygon local-principal stress arrays behind Fig. 5's
#     phase space (viscous tsic + published elastic-localh pickles);
# (c) the lake polygon inventory geojson (drainage-catalog outlines).
PNAS_ROOT="$(dirname "$(dirname "$(dirname "$LAB_3D")")")"   # .../pnas2025
if [ -d "$LAB_3D" ]; then
  mkdir -p "$DST/pnas_s2" "$DST/pnas_lakestresses"
  for n in $PNAS_LAKES_OLD; do
    rsync -av --ignore-existing \
      "$PNAS_ROOT/sentinel2/tstacks/tstack_2019cw${n}.nc" \
      "$DST/pnas_s2/"
  done
  for pair in 387:5.4e6 428:6.5e6 871:8.5e6 888:8.5e6 893:7.5e6 988:8.6e6 997:6.7e6; do
    n="${pair%%:*}"; csi="${pair##*:}"
    rsync -av --ignore-existing \
      "$LAB_3D/elmer/sim_data/viscous/realtopos/processed/lakestresses/localprincipals/stress_arrays_inside_lakes_2019cw${n}_d25km_r2500m_csi${csi}_tsic_viscous.pkl" \
      "$LAB_3D/elmer/sim_data/elastic/realtopos/processed/lakestresses/localprincipals/stress_arrays_inside_lakes_elastic_2019cw${n}_d25km_r2500m_youngmod3.077e3_elastic_localh.pkl" \
      "$DST/pnas_lakestresses/"
  done
  rsync -av --ignore-existing \
    "$LAB_3D/elmer/data/labels_2019_volumes.geojson" \
    "$DST/data/"
else
  echo "WARN: lab Google Drive (3d) not mounted — skipping PNAS S2/lakestress data"
fi

# ── Ch.2 VALIDATION: the idealized periodic-slab sweep ──────────────────
# 75 Elmer/Ice Newtonian flat-slab runs with a circular slippery patch,
# periodic BCs (flatslabnewt_R*_H*_a*_G*_periodicBC_t0001.nc, ~179 MB
# each, ~12 GB). Variables tau_*/sigma1/velo_*/speed_* on (level, y, x),
# level in {surf, da}, stress MPa, x/y m. The hero run (the thesis
# validation figure) is copied first.
# → cinematic/scene_ch02/build_slab_validation.py (+ slab_theory.py)
# BEGIN slab_fetch
SLAB_NC="$LAB_DRIVE/Lab_files/pnas2025/elmer/postprocess/flatslabnewt/ncfiles"
SLAB_DST="$(cd "$(dirname "$0")" && pwd)/source_data/pnas_slab/ncfiles"
if [ -d "$SLAB_NC" ]; then
  mkdir -p "$SLAB_DST"
  # the run list, so the builder can say which runs have not arrived yet
  ( cd "$SLAB_NC" && ls flatslabnewt_*_periodicBC_t0001.nc ) \
    | sed -E 's/^flatslabnewt_(.*)_periodicBC_t0001\.nc$/\1/' > "$SLAB_DST/../expected_runs.txt"
  rsync -a --partial-dir=.rsync-partial --ignore-existing \
    "$SLAB_NC/flatslabnewt_R5000_H3000_a01_G01_periodicBC_t0001.nc" "$SLAB_DST/"
  rsync -av --partial-dir=.rsync-partial --ignore-existing \
    --include='flatslabnewt_*_periodicBC_t0001.nc' --exclude='*' \
    "$SLAB_NC/" "$SLAB_DST/"
else
  echo "WARN: lab Google Drive (flatslabnewt) not mounted — skipping the slab sweep"
fi
# END slab_fetch

# ── JOG published article (Ch.1 deeper dive, "The paper") ───────────────
# The Cambridge version (J. Glaciol. 72, e76; 15 pp, Appendix B = B.1–B.22)
# was placed in source_data by hand — there is no lab-drive copy to fetch.
# It is what R2 papers/rines2026_jog_v2.pdf serves and what
# Ch1DerivationEqs.vue's equation numbers follow. If it goes missing, the
# PDF has to be supplied by hand again.
if [ ! -f "$DST/manuscript_jog/published/longitudinal-stress-induced-by-basal-slippery-patch.pdf" ]; then
  echo "WARN: manuscript_jog/published/…slippery-patch.pdf missing — a hand-placed file, not fetched by this script"
fi

# ── ESSD manuscript (Ch.3) ──────────────────────────────────────────────
# essd-2026-406.pdf (submission 2026-406) was placed in source_data by
# hand — there is NO Lab/Oak path to re-fetch it from. If it goes missing,
# the PDF has to be supplied by hand again.
if [ ! -f "$DST/manuscript_essd/essd-2026-406.pdf" ]; then
  echo "WARN: manuscript_essd/essd-2026-406.pdf missing — a hand-placed file, not fetched by this script"
fi

# ── ESSD dataset sources (Ch.3 beats) ───────────────────────────────────
# (a) the director's own (labeler 1) full hand-label CSVs, 2018 (679) + 2019 (1000);
# (b) Dunmire lake-outline geojsons (fig-1b polygons), both years;
# (c) the Dunmire water-area NetCDFs behind the p_water curves
#     (S2_water variable; 184 + 294 MB);
# (d) the 3-labeler inter-rater subset (the director + Niall Coffey + Eojin Lee);
# (e) baseline-classifier test predictions (headline accuracy numbers);
# (f) the architecture figure SVGs (fig-7 + detailed variant).
ESSD_ROOT="${ESSD_ROOT:-/path/to/your/essd/project/root}"   # the lake-research project checkout
if [ -d "$ESSD_ROOT" ]; then
  mkdir -p "$DST/essd/labels" "$DST/essd/dunmire" "$DST/essd/irr" \
    "$DST/essd/inference" "$DST/essd/figs"
  rsync -av --ignore-existing \
    "$ESSD_ROOT/labels/CW_2018/labels_CW_2018.csv" \
    "$ESSD_ROOT/labels/CW_2019/labels_CW_2019.csv" \
    "$DST/essd/labels/"
  rsync -av --ignore-existing \
    "$ESSD_ROOT/labels/dunmire/labels_2018_volumes.geojson" \
    "$ESSD_ROOT/labels/dunmire/labels_2019_volumes.geojson" \
    "$DST/essd/dunmire/"
  rsync -av --ignore-existing \
    "$ESSD_ROOT/lake-vision/datasets/dunmire/all_lakes_2018.nc" \
    "$ESSD_ROOT/lake-vision/datasets/dunmire/all_lakes_2019.nc" \
    "$DST/essd/dunmire/"
  rsync -av --ignore-existing \
    "$ESSD_ROOT/essd/essd_sdr/labels/irr/" \
    "$DST/essd/irr/"
  rsync -av --ignore-existing \
    "$ESSD_ROOT/essd/inference/test_predictions_bestf1.csv" \
    "$ESSD_ROOT/essd/inference/val_predictions_bestf1.csv" \
    "$DST/essd/inference/"
  # per-protocol prediction tables (crossyear + combined; train/val/test)
  # behind the "results on the map" beat — a few hundred kB in total.
  rsync -av --ignore-existing \
    "$ESSD_ROOT/essd/inference/inference_essd/" \
    "$DST/essd/inference/inference_essd/"
  rsync -av --ignore-existing \
    "$ESSD_ROOT/essd/output/fig_architecture.svg" \
    "$ESSD_ROOT/essd/output/fig_architecture_detailed.svg" \
    "$ESSD_ROOT/essd/paper/figures/fig7_architecture.png" \
    "$DST/essd/figs/"
  # (g) the model SOURCE that defines LakeDrainageClassifier — needed to
  #     rebuild the graph offline and pull one lake's timestack through it
  #     layer by layer for the Ch.3 beat-2 walkthrough. Source only; the
  #     trained weights come from Oak below.
  rsync -av --ignore-existing --prune-empty-dirs \
    --include='*/' --include='*.py' --exclude='*' \
    "$ESSD_ROOT/lake-vision/lakevision/" \
    "$DST/essd/lakevision_src/"
else
  echo "WARN: ESSD project root not found — skipping Ch.3 sources"
fi

# ── Ch.3 beat 2: trained ESSD baseline checkpoints (Oak) ────────────────
# The walkthrough must run the PAPER's model, not a look-alike. The
# sandbox weights under lake-vision/sandbox/weights/ are an EARLIER
# 3-class model (plain LSTM over flattened CNN features, ~540k params)
# and are deliberately NOT copied — the ESSD baseline is a two-stream
# ConvLSTM, 5 classes, ~140k params; its weights come from the
# essd-training-runs code at the submission-era training commit.
OAK_LAKEVISION="$CLUSTER_MOUNT/sherlock_lakevision"
OAK_ESSD_MODELS="$OAK_LAKEVISION/models/essd"
if [ -d "$OAK_ESSD_MODELS" ]; then
  mkdir -p "$DST/essd/checkpoints"
  # VERIFIED: lakevision_essd_crossyear_bestf1.pth loads into
  # LakeDrainageClassifier with ZERO missing/unexpected keys at
  #   num_classes=5, frontcnn_num_layers=4, frontcnn_out_hw=(64,64),
  #   classhead_dropout>0   (139,925 params — the paper's "~140k")
  # Two of those are non-obvious: (64,64) is the model's silent upsample of
  # the front CNN's output, and a nonzero classhead_dropout inserts an
  # nn.Dropout that shifts the head's output Linear from fc.2 to fc.3.
  # Get either wrong and load_state_dict mismatches.
  #
  # The `crossyear` run is the paper's headline baseline (train 2019 ->
  # test 2018, Fig. 9); `combined` is Fig. 10. `_bestf1` is the
  # peak-validation-macro-F1 checkpoint the reported metrics come from —
  # that one drives the forward-pass walkthrough. The `_epochNNN` series
  # (every 5 epochs) is the through-training-time axis of the same beat.
  # ~91 MB per run; Oak is SMB and slow, so this is deliberately narrow —
  # the 4class / highcap / augment / lcurve variants are NOT copied.
  for run in crossyear combined; do
    rsync -av --ignore-existing \
      --include='*_bestf1.pth' --include='*_epoch*.pth' --exclude='*' \
      "$OAK_ESSD_MODELS/$run/" \
      "$DST/essd/checkpoints/$run/"
  done
else
  echo "WARN: Oak not mounted — skipping ESSD trained checkpoints (Ch.3 beat 2)"
fi

# ── Ch.3: the ESSD REVISION baseline (manuscript version 3, Sept 2026) ──
# The revised paper reports a different classifier on a different split
# (CW2019 600/200/200; five input channels, GroupNorm, 32x32 ConvLSTM).
# build_network.py (+ build_network_epochs.py) bake from these. The revision checkpoints carry
# their own training config, so only the _bestf1 files are needed (~0.6 MB
# each, all eight ablation cells). The code snapshot is lake-vision at the
# commit the inference tables were written with (branch essd/revision01);
# it sits BESIDE the submission's lakevision_src/, never over it.
LV_REPO="$ESSD_ROOT/lake-vision"
LV_REV_SHA="adec2c8"
if [ -d "$ESSD_ROOT/essd" ]; then
  mkdir -p "$DST/essd/revision" "$DST/essd/figs/revision01" \
    "$DST/essd/inference/inference_essd" "$DST/manuscript_essd"
  rsync -av --ignore-existing \
    "$ESSD_ROOT/essd/inference/inference_essd/essd_revision" \
    "$DST/essd/inference/inference_essd/"
  rsync -av --ignore-existing \
    "$ESSD_ROOT"/essd/inference/training_metrics/metrics_rev_* \
    "$DST/essd/revision/"
  rsync -av --ignore-existing \
    "$ESSD_ROOT/essd/essd_sdr/v3/splits/essd_CW_2019only" \
    "$DST/essd/revision/"
  rsync -av --ignore-existing \
    "$ESSD_ROOT/essd/paper/revision01_202609/figures/" \
    "$DST/essd/figs/revision01/"
  rsync -av --ignore-existing \
    "$ESSD_ROOT/essd/paper/revision01_202609/essd-2026-406-manuscript-version3.pdf" \
    "$ESSD_ROOT/essd/paper/revision01_202609/author-response.pdf" \
    "$DST/manuscript_essd/"
  if [ ! -f "$DST/essd/lakevision_src_rev/lakevision/models/classifier.py" ]; then
    mkdir -p "$DST/essd/lakevision_src_rev"
    git -C "$LV_REPO" archive "$LV_REV_SHA" \
      | tar -x -C "$DST/essd/lakevision_src_rev"
  fi
fi
if [ -d "$OAK_LAKEVISION/models/essd_revision" ]; then
  mkdir -p "$DST/essd/checkpoints/essd_revision" "$DST/essd/revision"
  rsync -av --ignore-existing \
    --include='*_bestf1.pth' --exclude='*' \
    "$OAK_LAKEVISION/models/essd_revision/" \
    "$DST/essd/checkpoints/essd_revision/"
  rsync -av --ignore-existing \
    "$OAK_LAKEVISION/band_stats/band_stats_essd_2019only_deposit.json" \
    "$DST/essd/revision/"
else
  echo "WARN: Oak not mounted — skipping the ESSD revision checkpoints"
fi
# The two training logs behind Fig. B2 (array job 44279083: task 1 =
# y2019_5c_pw_noaug, task 5 = y2019_4c_pw_noaug — each metrics JSON's
# `source_log`). The trainer printed the train + validation confusion
# matrices at epoch 1 and every 10th epoch; build_training_dynamics.py
# parses them into the Ch.3 training segment's per-epoch matrices.
if [ -d "$OAK_LAKEVISION/logs" ]; then
  mkdir -p "$DST/essd/revision/logs"
  rsync -av --ignore-existing \
    "$OAK_LAKEVISION/logs/lv_essd_rev_44279083_1.out" \
    "$OAK_LAKEVISION/logs/lv_essd_rev_44279083_5.out" \
    "$DST/essd/revision/logs/"
else
  echo "WARN: Oak not mounted — skipping the ESSD revision training logs (per-epoch confusion matrices)"
fi
# The five-class baseline's every-5-epoch checkpoints (run y2019_5c_pw_noaug,
# epochs 005..400, 80 files, ~575 KB each, 46 MB): Chapter 3's network
# segment has an EPOCH axis — the five lakes through the network as it
# trains (scene_ch03/build_network_epochs.py → R2 ch03/network_epochs/).
# Each carries its config + epoch + validation metrics. The run's plain
# `…_5c_pw_noaug.pth` is NOT the last epoch (its own `epoch` says 73 — the
# trainer's other "best" save); it is kept here as `_plain.pth` only so
# nobody mistakes it for epoch 400 again.
if [ -d "$OAK_LAKEVISION/models/essd_revision" ]; then
  mkdir -p "$DST/essd/checkpoints/essd_revision/epochs"
  rsync -av --ignore-existing \
    --include='lakevision_essd_rev_y2019_5c_pw_noaug_epoch*.pth' --exclude='*' \
    "$OAK_LAKEVISION/models/essd_revision/" \
    "$DST/essd/checkpoints/essd_revision/epochs/"
  if [ ! -f "$DST/essd/checkpoints/essd_revision/epochs/lakevision_essd_rev_y2019_5c_pw_noaug_plain.pth" ]; then
    cp "$OAK_LAKEVISION/models/essd_revision/lakevision_essd_rev_y2019_5c_pw_noaug.pth" \
      "$DST/essd/checkpoints/essd_revision/epochs/lakevision_essd_rev_y2019_5c_pw_noaug_plain.pth"
  fi
else
  echo "WARN: Oak not mounted — skipping the ESSD revision epoch checkpoints (Ch.3 network EPOCH axis)"
fi

# The Introduction's "coupling length" sample step:
# scene_01_intro/build_coupling_length.py. Christoffersen et al. 2018's PDF
# (its Fig. 4 rasters are digitised) from a local Zotero library, and the two
# Stevens papers' own public code repositories (GitHub, CC BY-NC 4.0):
# goodnesglaciers/lake_strain (Stevens 2024, Zenodo 10650188) and
# goodnesglaciers/lakes_cluster (Stevens 2026, Zenodo 19387821). Small files.
CPL="$DST/coupling"
mkdir -p "$CPL"
C18_PDF="$(ls "${ZOTERO_STORAGE:-$HOME/Zotero/storage}"/*/"Christoffersen et al. - 2018 - Cascading lake drainage on the Greenland Ice Sheet.pdf" 2>/dev/null | head -1 || true)"
if [ -n "$C18_PDF" ] && [ ! -f "$CPL/christoffersen2018.pdf" ]; then
  cp "$C18_PDF" "$CPL/christoffersen2018.pdf"
fi
GH_RAW="https://raw.githubusercontent.com/goodnesglaciers"
for f in \
  "lake_strain/main/NIF_L1A/apcoords_lle_2012_FLOW.mat" \
  "lakes_cluster/main/GNSS_derived/strain_rates_2023/apcoords_lle_2023.mat" \
  "lakes_cluster/main/GNSS_derived/strain_rates_2022/environs_lakes_2022B_250416_noboundaries.mat" \
  "lakes_cluster/main/GNSS_derived/strain_rates_2023/environs_lakes_2023B_S1S2MO_250416_noboundaries.mat"; do
  out="$CPL/$(basename "$f")"
  [ -f "$out" ] || curl -fsSL "$GH_RAW/$f" -o "$out"
done

echo "done:"
du -sh "$DST"/*
