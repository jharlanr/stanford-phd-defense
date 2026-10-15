#!/bin/bash
# Sanctioned copy step for the Additional-Work assets. Same rule as
# cinematic/fetch_sources.sh: originals are never referenced by a build
# script — they are COPIED into cinematic/source_data/ (gitignored) once,
# and everything downstream reads only the copy.
#
# Run:  bash cinematic/scene_addl/fetch_sources.sh
set -euo pipefail

SOURCE_ROOT="${SOURCE_ROOT:-/path/to/your/research/tree}"   # the private research tree the originals live in
CG_FIGS="$SOURCE_ROOT/mx/computers_geosciences/revision02/figures"
DST="$(cd "$(dirname "$0")/.." && pwd)/source_data/cg_paper"
mkdir -p "$DST"

# Computers & Geosciences (2026) Fig. 5 — SGSIM vs MGSIM on the synthetic
# magnetics benchmark. Menu-card thumbnail for the Additional-Work page.
rsync -av --ignore-existing "$CG_FIGS/fig05_synthcompare.png" "$DST/"

# C&G Fig. A.1 (appendix, Cape Smith Belt prospectivity) — panel (a), the
# stacked MGSIM realizations, is the C&G card's square thumbnail.
CG_FIGS_R1="$SOURCE_ROOT/mx/computers_geosciences/revision01/figures"
rsync -av --ignore-existing "$CG_FIGS_R1/figA1_prospectivity.png" "$DST/"

# Computers & Geosciences 215 (2026) 106201 — the published PDF (an
# original in research/mx; the C&G card quotes the paper's abstract from this copy).
CAGEO_PDF="$SOURCE_ROOT/mx/computers_geosciences/1-s2.0-S0098300426000981-main.pdf"
MDST="$(cd "$(dirname "$0")/.." && pwd)/source_data/manuscript_cageo"
mkdir -p "$MDST"
rsync -av --ignore-existing "$CAGEO_PDF" "$MDST/"

# --- COP27 (the director asked for a door + a thumb on the COP27 card) ---
# The C-PREE article "Beyond the Negotiations at COP27" (Jan 6 2023) that
# the director contributed the Cryosphere section to. Its HEADLINE image is the
# card's thumbnail: Simon Stiell, UNFCCC Executive Secretary, at the loss-
# and-damage side event. Credit UNFCCC Flickr / Kiara Worth.
# NOTE: the article's HTML sits behind a Cloudflare interstitial (curl gets
# "Just a moment..."); the image files themselves are served plainly, so we
# fetch the ORIGINAL (2048x1365) rather than one of Drupal's style crops.
COP27_DST="$(cd "$(dirname "$0")/.." && pwd)/source_data/cop27"
COP27_URL="https://cpree.princeton.edu/sites/g/files/toruqf651/files/2023-01/unfccc_cop27_16nov22_lostanddamagedpakistan_kiaraworth-35_0.jpg"
mkdir -p "$COP27_DST"
if [ ! -f "$COP27_DST/unfccc_cop27_lossanddamage_kiaraworth-35.jpg" ]; then
  curl -fsSL -A 'Mozilla/5.0' "$COP27_URL" \
    -o "$COP27_DST/unfccc_cop27_lossanddamage_kiaraworth-35.jpg"
  echo "fetched COP27 headline image"
fi

# --- The CryoCloud Dask tutorial (the director asked for a card for it) ---
# "Parallelized Cloud Computing with Dask for Geoscientists" (Abrahams &
# Rines), book.cryointhecloud.com/dask-for-geoscientists/. Its last part
# compiles Sentinel-2 tiles over the Oakland port terminals with
# sat-tile-stack; the notebook (for the exact query) and the terminal mask
# are public in the book's repo. build_dask_card.py re-runs that query.
CRYO_DST="$(cd "$(dirname "$0")/.." && pwd)/source_data/cryocloud"
CRYO_RAW="https://raw.githubusercontent.com/CryoInTheCloud/CryoCloudWebsite/main/book/tutorials"
mkdir -p "$CRYO_DST"
for f in dask_for_geoscientists.ipynb oakland_port_terminals.geojson; do
  if [ ! -f "$CRYO_DST/$f" ]; then
    curl -fsSL "$CRYO_RAW/$f" -o "$CRYO_DST/$f" && echo "fetched $f"
  fi
done

# --- The persistent-lake-IDs card thumb (another card the director asked for) ---
# The director's CW lookup (research/lakes/2026/labels/lookups/CW_lookup.csv): one
# persistent_id (CW_0000…) per Dunmire lake-year, 2018 + 2019, built with
# sat_tile_stack's centroid tracker (500 m). build_card_thumbs.py tags the
# lakes with it. The lake outlines and the two Sentinel-2 stacks it reads
# (CW2018_1583 / CW2019_1996 — the same lake, CW_0506) are already copies
# under source_data/essd/dunmire/ and source_data/stacks/.
LOOKUP_SRC="$SOURCE_ROOT/lakes/2026/labels/lookups/CW_lookup.csv"
LOOKUP_DST="$(cd "$(dirname "$0")/.." && pwd)/source_data/essd/lookups"
mkdir -p "$LOOKUP_DST"
rsync -av --ignore-existing "$LOOKUP_SRC" "$LOOKUP_DST/"

echo "done:"; du -sh "$DST"
