# MGSIM bed-topography ensemble (lake 1951 / 2019cw428)

A quick-and-dirty stochastic-UQ experiment for the defense website's
"additional work" section: condition MGSIM (multigrid SGSIM,
[Stanford-Mineral-X/multigrid-sgsim](https://github.com/Stanford-Mineral-X/multigrid-sgsim))
on real ice-penetrating-radar bed picks over the lake-1951 simulation
domain, generate ~10 bed-topography realizations, run each through the
published viscous Elmer/Ice setup with everything else held fixed, and
look at the spread of the surface stress field.

Everything in here follows the project data rule: this directory holds
its **own copies** of whatever it uses; nothing reads from or writes to
the original paper repos.

> **Final home.** Lives at `cinematic/scene_addl/mgsim/`
> beside the bake (`../build_mgsim_assets.py`); the raw radar download cache
> is in gitignored `cinematic/source_data/mgsim/raw/`. Path prefixes in the
> numbered history below predate the move.

## Layout

```
cinematic/scene_addl/mgsim/
├── scripts/
│   ├── fetch_radar_lines.py   # step 0: pull CReSIS bed picks over the AOI
│   └── copy_source_dems.sh    # sanctioned copy of the published sif DEMs
├── notebooks/
│   ├── 01_radar_lines.ipynb   # coverage maps + radar-vs-published-bed check
│   ├── 02_grid_picks.ipynb    # collapse picks onto the Elmer DEM lattice
│   ├── 03_mgsim_realizations.ipynb  # trend/variogram/MG schedule/ensemble
│   ├── 04_kriging_multigrid.ipynb   # demo (kriging) implementation ported +
│                              #   3-way comparison + conditional-GRF hybrid
│   └── 05_mgsim_perlevel_variogram.ipynb  # the package with WestPilbara's
│                              #   fresh-variogram-per-level schedule
├── data/
│   ├── raw/ → cinematic/source_data/mgsim/raw/  (gitignored, re-fetchable)
│   ├── source_copies/         # published bed+surface .dat (tracked, ~2 MB)
│   └── derived/               # AOI/frame defs, gridded product, realization
│                              #   npz (tracked); 138 MB picks CSV, per-seed
│                              #   real_cache/, and sif-format dems/ gitignored
└── figures/                   # notebook output PNGs (tracked)
```

Notebooks 01–02 need pandas, pyproj, xarray and matplotlib; notebooks 03–05
also import `multigrid_sgsim`, gstatsim, skgstat and gstools.

## Quick start

```bash
# 1. Pull/refresh the radar picks (CReSIS csv_good, public, ~30 files)
python cinematic/scene_addl/mgsim/scripts/fetch_radar_lines.py

# 2. Open or re-execute the coverage notebook
cd cinematic/scene_addl/mgsim/notebooks
jupyter nbconvert --to notebook \
    --execute --inplace 01_radar_lines.ipynb
```

## Geometry (from the site's own ch2 build data)

- AOI: **50 km × 50 km in the along-flow domain orientation**, concentric
  with the Elmer domain (`|LX|, |LY| ≤ 25 km`; the domain center sits
  ~40 m from the lake centroid at 69.41511 N, 48.91966 W).
- Elmer simulation domain: 24.75 km along-flow square (the sifs' `Lx`).
- Site analysis tile: 14.75 km (the published nc's 591×591 @ 25 m grid).
- `data/derived/aoi_cw1951.json` records both frames; local coords
  `LX, LY` map to Elmer DEM coords as `LX + 12375, LY + 12375`.
- Gridded product (`gridded_bed_cw1951_150m.{csv,npz}`): the sif DEM's
  150 m node lattice extended to the AOI (334×334; the Elmer 166×166 is
  the central sub-lattice, indices 84…249). Per cell: harmonic-mean ice
  thickness over all picks (thickness is datum-free), arithmetic-mean
  surface over datum-good picks, and the conditioning bed
  `BED_HM = MEAN_SURF − HM_THICK` (WGS-84 ellipsoidal). The harmonic
  mean is applied to thickness, not bed elevation — elevation crosses
  zero in this AOI, where a harmonic mean is undefined.

## Data provenance

Radar: CReSIS L2 "good picks" aggregates,
https://data.cresis.ku.edu/data/rds/csv_good/ (seasons 1993–2017) and
per-season `csv_good/` for 2018–2019. Acknowledgment per CReSIS policy:
*"We acknowledge the use of data from CReSIS generated with support
from the University of Kansas, NASA Operation IceBridge, and NSF."*
Radar elevations are WGS-84 ellipsoidal; the published bed is
geoid-referenced — the datum shift is handled at the conditioning step,
not in the raw picks.

Published-bed basemap: `cinematic/source_data/pnas_sims/*.nc`
(the defense repo's copies, populated by `cinematic/fetch_sources.sh`).

## Plan

1. Acquire + map radar lines (notebook 01). ✅
2. Grid the picks onto the Elmer DEM lattice — the MGSIM "raw" data
   (notebook 02). ✅
3. Variogram fitting on detrended residuals (radar − published bed),
   then N=10 seeded MGSIM realizations on the same lattice, edge-tapered
   to the published bed so wall BCs stay identical across the ensemble
   (notebook 03, published `multigrid_sgsim` package). ✅ Notebook 04
   additionally ports the kriging-based demo implementation
   (AutoMultigridSim; WestPilbara turns out to run SGeMS sgsim
   per level — see the nb-04 addendum), compares the two head-to-head, and
   saves a conditional-GRF hybrid (smooth *and* statistically honest) as
   an alternate DEM set: `dems/*_mgsim??.dat` (default, SGS) vs
   `dems/*_condgrf??.dat`. ✅ Notebook 05 tries WestPilbara's
   fresh-variogram-per-level schedule inside the package: it transfers
   faithfully (ranges 2.0→1.3→0.6→0.3 km) but makes the bed rougher and
   more over-dispersed on our sparse lines — the fine passes add
   short-range noise grid-wide. Saved as `dems/*_mgpl??.dat`, not
   recommended. ✅
3b. Variogram exploration sweep (`scripts/variogram_sweep.py`,
   `scripts/grf_sweep.py`, `scripts/sweep_report.py`; 90 configs over
   model x nugget x neighborhood x range x schedule x conditioning set,
   both generators). Mechanism: in gstatsim a node coinciding with a datum
   is assigned it EXACTLY only when the nugget is zero, and the nugget is
   also the per-node simulated noise — so one knob sets both the
   conditioning error and the salt-and-pepper. Hard limit: the picks
   disagree with themselves by 7.1 m (median) inside a 150 m cell, so a map
   honoring every cell forces 2nd-difference roughness >= sqrt(6)*7.1 =
   17.5 m; no config in the sweep beats that. Frontier (see
   `figures/sweep_pareto.png`, `figures/sweep_contenders.png`,
   `data/derived/variogram_sweep_results.csv`): exact -> SGS Matern nu=1.5,
   nugget 0, k=24, range x2 (rough 18.2); ~6 m -> GRF Matern-3.5 nugget 1e-2
   (rough 8.8); ~10 m (= data noise) -> GRF Gaussian nugget 1e-2 (rough 6.0).
   All beat the shipped nb-03 config (err 11.5 m, rough 29.8) on both axes. ✅

3c. Tran-style multiple-grid SGS (`scripts/tran_multigrid.py`,
   `scripts/tran_figure.py`). Two different things are called "multigrid":
   the `multigrid_sgsim` package simulates the FULL grid at every level from
   a subsampled conditioning set and SUMS the levels (a residual cascade);
   Tran (1994, Computers & Geosciences 20(7-8) 1161-1168) coarsens the
   simulation PATH — level L simulates only the not-yet-known nodes of an
   L-spaced lattice, conditioning on the data plus everything simulated so
   far, each node once, nothing summed, total cost ~ one pass. Measured on
   this bed (Matern nu=1.5, nugget 0, k=24, range x2; all honor the radar
   exactly): the package cascade degrades monotonically with added levels
   (roughness 18.2 -> 19.7, departure std 69 -> 84, variogram ratio
   1.63 -> 2.22, runtime 101 -> 421 s) while Tran's improves on all three
   (roughness 17.7 = the data-noise floor, departure std 64, ratio 1.42) at
   single-pass cost. Tran's path refinement also honors the data exactly BY
   CONSTRUCTION (conditioning nodes are never re-simulated), decoupling
   exactness from the nugget. See `figures/tran_vs_cascade.png`,
   `figures/tran_metrics.png`, `data/derived/tran_multigrid_comparison.csv`.
   Caveat: the variogram ratio is calibrated against the nb-03 sill while
   the model uses range x2, so read it comparatively, not absolutely. ✅

3d. DECISION, made by the director: **the shipped nb-03 MGSIM ensemble
   (`dems/*_mgsim??.dat`) is what feeds the Elmer runs.** Reason found by
   inspecting the maps and confirmed by `scripts/track_imprinting.py`:
   exactly-conditioned realizations draw the flight lines onto the bed.
   Roughness within 1.5 px of a pick vs >= 6 px away — shipped nb-03
   29.7/30.3 (ratio 0.98, unstructured speckle); Tran multiple-grid
   24.8/6.4 (ratio 3.88); single pass 25.2/7.8 (3.23). Global roughness is
   a misleading score: Tran won it (17.7 m) precisely by being smooth in
   the gaps while concentrating roughness into linear artifacts. Speckle is
   unstructured and the ice low-passes it; track imprinting is geometrically
   aligned with the 2015 flight paths and would alias into the surface-stress
   ensemble as apparent signal. The 1% nugget buys that immunity. The sweep,
   Tran port and GRF variants stay in the repo as method exploration.

4. Viscous Elmer/Ice runs (docker `andrewdnolan/elmerice`), one per bed;
   everything else pinned to the published setup (Csi = 6.5e6, SICOPOLIS
   temperature, BCs). **Bundle ready to port: `elmer_bundle/`** — built by
   `scripts/make_elmer_bundle.py` from the published sif (sanctioned copies in
   `data/source_copies/`, incl. the `.geo` and the `PROG/USF_TAVz` UDF, which
   is a Linux x86-64 build). Self-contained: **20 sifs (each bed run with and
   without the slippery patch, so every realization yields a Δσ₁)** + 10 bed DEMs + surface +
   geo + UDF + `run_ensemble.sh` + `MANIFEST.txt` (11 MB). `diff` vs the
   published sif is exactly five edits — bed DEM path, lowercase surface path
   (the published sif's `_D25km_H` capitals are fatal on Linux), removal of the
   unused `speedDEM` Variable 3 + its Exported Variable, per-realization output
   names, the UDF path rebase, and `Output File` dropped (the ~466 MB `.result`
   restart dump; σ₁ comes from the `.vtu` and 20 of them would not fit on the
   VM). Physics untouched. The `nopatch` twins differ from `patch` by exactly
   two lines: the output-name tag and the Weertman friction coefficient
   (`"(1 - ((...) < R^2)) * C_out"` → `"C_out"`). The director submits
   these on the VM. ✅ prepared
4b. Ensemble launched on the VM (`MAX_PARALLEL=4`, nopatch
   first). Solve time per run is very uneven — 7.1 h to >17 h, driven by
   how many Navier-Stokes nonlinear iterations the realization's bed
   needs (17 vs 44+ seen). Each run drops one ~192 MB `.vtu`.

4c. Surface fields come back off the VM with
   `scripts/extract_surface_vtu.py`, which parses the raw-appended VTK XML
   with numpy alone (no vtk/meshio/pyvista on the VM), picks the top node
   of each extruded column, and resamples onto the PUBLISHED analysis
   lattice (591×591 @ 25 m, ±7375 m, centered) so runs drop straight into
   the published nc's frame. Landed in `elmer_bundle/results/*.npz`
   (gitignored, ~15 MB each; the bundle generator preserves that
   directory and keeps it out of MANIFEST.txt). Validation: `topo_surf`
   matches the published nc to 0.05 m, and correlating each extracted
   Cauchy component against the published nc confirms Elmer's Voigt order
   is (xx, yy, zz, xy, yz, xz) — diagonal 0.61–0.79, off-diagonal ≤0.55.

5. Ensemble σ₁ mean/spread maps → website "additional work" beat.
   `scripts/plot_nopatch_stress.py` (σ_t1 = the published SI recipe from
   `cinematic/scene_ch02/build_sim_domains.py`, applied to the ABSOLUTE
   nopatch tensor instead of the patch−nopatch difference) →
   `figures/elmer_nopatch_sigma_t1.png` (bed / σ_t1 / Δ-vs-published, one
   column per run) and `figures/elmer_nopatch_ensemble.png` (mean, std,
   bias, distributions, per-pixel agreement). First 4 nopatch runs:
   ensemble spread **61.6 kPa** (mean per-pixel std), mean bias +10.1 kPa,
   RMS(mean − published) 95.4 kPa, per-run correlation with the published
   nopatch field 0.64–0.69. Realization σ_t1 std (140–147 kPa) runs ~5–10%
   above the published bed's 134.3 kPa — the published bed is smoother, so
   it carries less stress structure. Headline for the UQ beat: bed
   uncertainty alone moves surface σ_t1 by ~±100–300 kPa, a substantial
   fraction of the ±1 MPa scale the paper uses for the drainage Δσ₁.
   ⏳ patch runs pending → per-realization Δσ₁.

6. **Website seam.** Additional Work is now a card
   menu (`website/src/components/sections/SectionAdditionalWork.vue`);
   the MGSIM card opens the paper or `/additional-work/mgsim` —
   `SectionMgsim.vue`, a headless driver of the SAME Ch.2 sim-domain
   block landed on lake 1951 (drain, imagery/elastic/viscous faces,
   catalog, phase space, BCs all work) plus its own pill row: *See the
   bed topography* (block goes glassy, bed to a hypsometric ramp) →
   prev/next through published + 10 realizations → *See the data* (right
   column: radar tracks + bed−radar on the 150 m grid, CReSIS credit) →
   *Use this bed* → *Drain the lake* → *Viscous solution with this bed*
   (the realization's no-patch σ_t1 drape, ±400 kPa, where an Elmer run
   has landed; dashed "run in progress" otherwise) → *Summary* (ensemble
   mean/std/bias figure). Assets baked by
   `cinematic/scene_addl/build_mgsim_assets.py` into the published tile
   frame → R2 `addl/mgsim/` (31 files, 15 MB): per-bed RG16 tiles, σ_t1
   drapes, side panels, `bed_palette.png` (shared by shader + panels),
   `mgsim_meta.json`. Globe additions: `surfA`, `bedPalMix`/palette,
   hot-swappable `bedUrl` (walls + BC overlays rebuild) and a third
   `stressAltUrl` drape slot. Re-bake + `rclone copy` when more runs
   land — the page reads `stress_nopatch` / `stress_dsig` per
   realization from the meta.

7. **Δσ₁ on the page.** 16/20 runs
   extracted (10 no-patch + patch 00–05); the bake writes
   `simstress_dsig_mgsimNN.png` = tangent-σ_t1(patch − no-patch) at the
   Ch.2 ±1 MPa scale wherever both twins exist (the published pair
   reproduces sim_domains.json's p99.7 = 320 kPa — recipe verified), and
   the page drapes Δσ₁ by default with an intact-ice σ₁ toggle. Result:
   bed uncertainty moves intact-ice σ_t1 by 65 kPa spread / 89 kPa RMS
   (n=10) but the drainage response Δσ₁ by only 15 kPa spread / 47 kPa
   RMS (n=6). Also fixed a live-only CORS cache-poison (image preloads
   must be `crossOrigin='anonymous'`), the landing now replays Ch.2's
   two-step animation, the summary lives in the right column, and the
   flow arrow hovers left of the drain pill (Ch.2 too). Remaining: patch
   06–09 → re-bake; then per-bed lake stats / phase space.

8. **Page-scale drapes and per-bed tables.** The bake now also writes the page-scale
   Δσ₁ drapes (±400 kPa), `simstress_{dsigdiff,s1diff}_*` (this bed −
   published), single-panel `summary_<fam>_<kind>.png`, per-bed
   `simlakes_<bed>.json` (in-polygon tables — the paper's pickle recipe,
   reproduced exactly on the published run) and `phase_space_mgsim.json`.
   Website: viscous-only page, linear flow, "change vs published" view,
   per-bed stress space with the ensemble cloud, a door from Ch.2 at
   lake 1951 (in-place handoff), and versioned asset URLs (`?v=`) to
   escape the earlier cache poison. Verify live in both Chromium and
   WebKit (the poison showed in one engine and not the other).
   **Follow-up:** fields are named *no patch / with patch / difference*; the
   bake writes all three families (+ "this bed − published" twins and
   summary panels) at ONE ±400 kPa scale (`VLIM_KPA`). Ch.2's own
   absolute fields come from `scene_ch02/build_sim_domains.py
   --fields-only`.

9. **Ensemble complete.** All 20 runs finished on the VM
   (last two: patch 08 in 8.8 h, patch 09 in 7.9 h);
   surfaces extracted and pulled (20 npz in `elmer_bundle/results/`),
   re-baked at **n = 10 patch/no-patch pairs** (112 files, 31 MB →
   R2 `addl/mgsim/`). Final numbers (per-pixel spread · RMS of ensemble
   mean vs published · bias, kPa): no patch 65 · 89 · +9, with patch
   68 · 96 · −13, **difference 16 · 48 · −21** — the published smooth
   bed overstates the drainage response ~25 % (its Δσ₁ p99.7 = 320 kPa
   vs realizations 181–259). Per-bed Δσ₁ corr with published 0.62–0.79.
   `ASSET_VERSION` bumped to 3 (same filenames, new bytes, R2 sends no
   Cache-Control).
