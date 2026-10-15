<template>
  <!-- Why the post-drainage elastic state is σ^V_pre + Δσ^E (the
       director wanted the theoretical justification for adding the
       elastic perturbation to the viscous background written down
       somewhere on the site). The Chapter 2 deeper
       dive's #superposition entry, the sibling of Ch2StressEqs.vue: the
       same LaTeX → SVG pipeline (cinematic/scene_ch02/build_results_eqs.py,
       sup_* labels, R2 ch02/eq/), one column, each equation with its
       one-line gloss beneath (HTML, the page's caption voice). The
       integration across the drainage is WRITTEN OUT (the director asked
       whether the integration was actually performed, not just named —
       sup_int, sup_bound), and the Δσ^E line carries the
       footprint-traction correction (the director pointed out that
       sigma_ref^E is not quite right on its own — sup_bvp_v2, sup_dsig_v2,
       sup_post_v2; caveat 2 made explicit). A second review pass
       added the volumetric companion of the jump (sup_jump_v2),
       the walls (sup_bvp_v3 + sup_bvp_walls), the Glen factor n in the
       dropped-term ratio and the long-time limit's conditions
       (sup_limit_v2). The type scale is --eqk (CSS px per TeX bp), set by
       the parent. -->
  <ol class="sp-root">
    <li v-for="r in ROWS" :key="r.eq" class="sp-row">
      <img :src="ch2EqUrl(r.eq)" :style="box(r.eq)" class="sp-eq" :alt="r.alt" />
      <p class="sp-gloss" v-html="r.gloss" />
    </li>
  </ol>
</template>

<script setup lang="ts">
import { CH2_EQ, type Ch2EqName } from '../config/ch2Eqs'
import { ch2EqUrl } from '../config/ch2Results'

const ROWS: { eq: Ch2EqName; alt: string; gloss: string }[] = [
  {
    eq: 'sup_maxwell',
    alt: "ε̇' = σ̇'/2G + σ'/2η(σ)",
    gloss: 'Maxwell: the strain rate is an elastic part (the spring, <i>σ̇</i>′/2<i>G</i> — instantaneous) plus viscous creep (the dashpot, <i>σ</i>′/2<i>η</i> with Glen’s <i>η</i> = 1/(2<i>Aτ</i><sub>e</sub><sup><i>n</i>−1</sup>) — accumulating with time). Written for the deviatoric parts <i>σ</i>′ = <i>σ</i> + <i>p</i><b>I</b>, the shape-changing part of the stress. Ice creeps at constant volume, so the mean stress has no dashpot and is purely elastic (bulk modulus <i>K</i> = <i>E</i>/3(1 − 2<i>ν</i>) ≈ 2.6 GPa) — which is also why the incompressible Stokes solution is this body’s steady state.',
  },
  {
    eq: 'sup_int',
    alt: "∫ε̇' dt = (1/2G)∫σ̇' dt + ∫σ'/2η dt over 0− to 0+",
    gloss: 'Integrate both sides over the drainage, from 0<sup>−</sup> to 0<sup>+</sup>, a duration <i>δt</i>.',
  },
  {
    eq: 'sup_bound',
    alt: "‖∫σ'/2η dt‖ ≤ max‖σ'‖/(2 min η) · δt → 0 as δt → 0",
    gloss: 'The spring term integrates exactly to the change in stress, however short <i>δt</i> is. The dashpot term is a finite creep rate — <i>σ</i>′/2<i>η</i> = <i>Aτ</i><sub>e</sub><sup><i>n</i>−1</sup><i>σ</i>′ — so its integral is at most that rate × <i>δt</i>: the creep that accumulates <i>during</i> the drainage, which vanishes as <i>δt</i> → 0 wherever the stress stays finite. It does not at the blister’s rim, where the elastic stress is singular and the ice creeps at once.',
  },
  {
    eq: 'sup_jump_v2',
    alt: "[ε'] = [σ']/2G, tr[ε] = tr[σ]/3K, [·] ≡ (·)|0+ − (·)|0−",
    gloss: 'What is left: the change in strain across the drainage equals the change in stress over 2<i>G</i> (and, for the volume, over 3<i>K</i>) — Hooke’s law for the jump, the paper’s <i>E</i> and <i>ν</i>. The ice answers a sudden load as an elastic solid; the creep comes after. For a real <i>δt</i> of 1–2 h the dropped term is of order <i>n δt</i>/<i>τ</i><sub>M</sub> of the kept one (<i>n</i> = 3: a Glen dashpot relaxes the part of a perturbation coaxial with the background on <i>τ</i><sub>M</sub>/<i>n</i>, the rest on <i>τ</i><sub>M</sub>; <i>τ</i><sub>M</sub> at the local effective stress) — caveat 3.',
  },
  {
    eq: 'sup_bvp_v3',
    alt: '∇·[σ] = 0, [σ]n = 0 (surface), [t] = −Pw ρgH n_b − t^V_pre (footprint)',
    gloss: 'The jump solves a linear elastostatic problem, unique once every boundary is set. On the footprint the traction goes from what the sliding ice carried before drainage, <b>t</b><sup>V</sup><sub>pre</sub> (overburden and basal shear), to water pressure alone: a net upward load of about (<i>P</i><sub><i>w</i></sub> − 1)<i>ρgH</i> (≈ 0.24 MPa for a 1 m blister under 1 km of ice) plus the release of the basal shear. Neglected here, as in the paper: the lake’s weight leaving the surface (~10 kPa per metre of depth — 50–100 kPa over a typical basin) and the hydrofracture itself.',
  },
  {
    eq: 'sup_bvp_walls',
    alt: '[u] = 0 (bed outside the footprint; inflow and outflow walls), [u]·ŷ = 0, [t]∥ = 0 (lateral walls)',
    gloss: 'Nothing moves in zero time: outside the footprint the bed cannot be penetrated and Weertman sliding is a rate law (a finite traction gives a finite slip rate — no slip in an instant); the inflow and outflow walls carry prescribed velocities; the lateral walls stay free-slip.',
  },
  {
    eq: 'sup_dsig_v2',
    alt: 'Δσ^E ≡ σ^E_blister − σ^E_ref ⇒ [σ] = Δσ^E + ℰ[t^E_ref − t^V_pre] on the footprint',
    gloss: 'The paper’s blister − no-blister difference solves the same problem — to <i>O</i>(<i>w</i>/<i>H</i>) ≈ 10<sup>−3</sup>, the blister solve’s bed being lifted by <i>w</i> ≤ 1 m — except that the traction it releases on the footprint is the elastic reference solve’s, <b>t</b><sup>E</sup><sub>ref</sub>, not the viscous pre-drainage one; ℰ[·] is the elastic response to a footprint traction. On a uniform slab equilibrium alone fixes both tractions (overburden <i>ρgH</i> cos <i>α</i>, driving stress <i>ρgH</i> sin <i>α</i>), so they agree and [<i>σ</i>] = Δ<i>σ</i><sup>E</sup> exactly. Over real bed the reference, clamped and laterally confined (<i>σ</i><sub><i>xx</i></sub> ≈ 0.43 <i>σ</i><sub><i>zz</i></sub> at <i>ν</i> = 0.3), carries footprint shear of a few hundred kPa (260–400 kPa on the three largest tiles, against a driving stress of 140–230 kPa), so the correction is of the same order as the sliding-release part of Δ<i>σ</i><sup>E</sup> and roughly half the overpressure; its normal traction differs by a few per cent. The correction is not computed — one gravity-free solve would remove it — caveat 2.',
  },
  {
    eq: 'sup_post_v2',
    alt: 'σ(0+) = σ^V_pre + [σ] ≈ σ^V_pre + Δσ^E, σt1^post = σt1(σ^V_pre + Δσ^E)',
    gloss: 'The paper’s Δ<i>σ</i><sup>E</sup> stands in for the jump — exact on a slab within the model (instantaneous drainage; the lake’s weight, the hydrofracture and the blister’s <i>O</i>(<i>w</i>/<i>H</i>) bed lift neglected), the footprint-traction correction dropped over real topography. Tensors added first, principals after: <i>σ</i><sub>t1</sub> is nonlinear, so Δ<i>σ</i><sub>t1</sub> ≠ <i>σ</i><sub>t1</sub><sup>post</sup> − <i>σ</i><sub>t1</sub><sup>pre</sup>. This is what the talk’s POST · ELASTIC station paints and the elastic stress space plots on <i>x</i>.',
  },
  {
    eq: 'sup_limit_v2',
    alt: 't ≫ τM/n, τr (Pw → 1, τb = 0 on the footprint) ⇒ σ → σ^V_post',
    gloss: 'The long-time limit is the viscous with-patch state — reached only once the blister has drained to overburden (the paper’s <i>τ</i><sub>r</sub>) and closed while the footprint stays lubricated; if it re-couples to the bed the limit is <i>σ</i><sup>V</sup><sub>pre</sub> instead. The approach takes about <i>τ</i><sub>M</sub>/<i>n</i> at the local stress: days in the far field.',
  },
]

/** The TeX box at --eqk CSS px per bp. */
function box(name: Ch2EqName) {
  const b = CH2_EQ[name]
  // width + aspect ratio (not a fixed height): a line wider than the
  // column (the BVP, 474 bp) is clamped by max-width and keeps its shape
  return { width: `calc(${b.w} * var(--eqk))`, aspectRatio: `${b.w} / ${b.h}` }
}
</script>

<style scoped>
.sp-root {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: calc(11 * var(--eqk));
}
.sp-row {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.3rem;
}
.sp-eq {
  display: block;
  flex: 0 0 auto;
  max-width: 100%;
  height: auto;
  user-select: none;
}

.sp-gloss {
  margin: 0;
  max-width: 52rem;
  font-size: 0.95rem;
  line-height: 1.4;
  color: #cfc9bd;
}
.sp-gloss :deep(i) { font-family: 'EB Garamond', serif; font-size: 1.12em; }
.sp-gloss :deep(sub),
.sp-gloss :deep(sup) { font-size: 0.72em; }
</style>
