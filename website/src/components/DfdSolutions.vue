<template>
  <!-- THE SOLUTIONS: the final equations side by side — the 1-D closed
       form (Rines et al. 2026, Eq. 42 with n = 1, ℓ = 2R) and the 2-D one
       (Lai, Rines, Coffey et al. 2026, SI Eq. 34, τ̄_rr) — each cut into
       the pieces a physicist points at. PHYSICAL INTUITION (the director's
       ask) names every piece under it and pairs the two models' matching
       pieces (hover one, its twin lights). The other two 2-D components
       and the published any-n 1-D form wait behind pills; so do the
       Bessel functions themselves — BESSEL K (the director's ask: say
       what the K's are): where they arise, their equation, the function,
       both limits, the identity the solution uses, and the three curves
       against e^(−x). -->
  <div class="so" :class="{ 'so-lit': lit }">
    <div class="so-head">
      <button class="so-pill" :class="{ 'so-pill-on': lit }" @click="lit = !lit">Physical intuition</button>
      <button class="so-pill so-pill-dim" :class="{ 'so-pill-on': more }" @click="more = !more">τ<sub>rθ</sub>, τ<sub>θθ</sub> · any <i>n</i></button>
      <button class="so-pill so-pill-dim" :class="{ 'so-pill-on': bessel }" @click="bessel = !bessel">Bessel <i>K</i></button>
    </div>

    <!-- the Bessel functions: a card over the equations, click outside to close -->
    <Transition name="so-fade">
      <div v-if="bessel" class="so-bessel" role="dialog" aria-label="The modified Bessel functions K" @click.self="bessel = false">
        <div class="so-bessel-card">
          <div class="so-bplot">
            <svg :viewBox="`0 0 ${BW} ${BH}`" class="so-bsvg" aria-label="K0, K1, K2 and e^(−x) against x, log scale">
              <g v-for="d in BY_TICKS" :key="'y' + d">
                <line :x1="BL" :x2="BR" :y1="by(d)" :y2="by(d)" class="so-bgrid" />
                <text :x="BL - 8" :y="by(d) + 4" text-anchor="end" class="so-btt">10<tspan dy="-7" font-size="10">{{ d }}</tspan></text>
              </g>
              <g v-for="t in BX_TICKS" :key="'x' + t">
                <line :x1="bx(t)" :x2="bx(t)" :y1="BB" :y2="BB + 6" class="so-bax" />
                <text :x="bx(t)" :y="BB + 20" text-anchor="middle" class="so-btt">{{ t }}</text>
              </g>
              <rect :x="BL" :y="BT" :width="BR - BL" :height="BB - BT" class="so-bframe" />
              <g :clip-path="`url(#so-bclip)`">
                <clipPath id="so-bclip"><rect :x="BL" :y="BT" :width="BR - BL" :height="BB - BT" /></clipPath>
                <path :d="bpath.exp" class="so-bexp" />
                <path :d="bpath.k0" class="so-bk so-bk0" />
                <path :d="bpath.k1" class="so-bk so-bk1" />
                <path :d="bpath.k2" class="so-bk so-bk2" />
              </g>
              <text :x="bx(1.15)" :y="by(Math.log10(besselK2(1.15))) - 8" class="so-bl so-bk2t">K₂</text>
              <text :x="bx(2.6)" :y="by(Math.log10(besselK1(2.6))) - 8" class="so-bl so-bk1t">K₁</text>
              <text :x="bx(4.2)" :y="by(Math.log10(besselK0(4.2))) + 18" class="so-bl so-bk0t">K₀</text>
              <text :x="(BL + BR) / 2" :y="BH - 4" text-anchor="middle" class="so-btt so-bti">x</text>
            </svg>
            <span class="so-bax-y"><DfdEq name="bessel_ax" :k="2.0" /></span>
            <span class="so-bleg"><i /><DfdEq name="bessel_exp" :k="1.9" /></span>
          </div>
          <div class="so-brows">
            <div v-for="row in BESSEL_ROWS" :key="row.name" class="so-brow">
              <span class="so-bk-k">{{ row.kicker }}</span>
              <DfdEq :name="row.name" :k="KB" :inline="false" />
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <div class="so-cols">
      <!-- 1-D -->
      <section class="so-col">
        <h3 class="so-h">1-D · a finite slippery patch <span class="so-ref">Rines et al. 2026 · J. Glaciol.</span></h3>
        <div class="so-eq">
          <Piece v-bind="P1.lhs" :lit="lit" :hot="hot" @hot="hot = $event" />
          <span class="so-brace" aria-hidden="true"><svg viewBox="0 0 20 100" preserveAspectRatio="none"><path d="M 17 2 C 7 2 11 48 2 50 C 11 52 7 98 17 98" /></svg></span>
          <div class="so-cases">
            <div class="so-case"><Piece v-bind="P1.up" :lit="lit" :hot="hot" @hot="hot = $event" /><DfdEq name="c_up" :k="KC" class="so-cond" /></div>
            <div class="so-case"><Piece v-bind="P1.inn" :lit="lit" :hot="hot" @hot="hot = $event" /><DfdEq name="c_in" :k="KC" class="so-cond" /></div>
            <div class="so-case"><Piece v-bind="P1.dn" :lit="lit" :hot="hot" @hot="hot = $event" /><DfdEq name="c_dn" :k="KC" class="so-cond" /></div>
          </div>
        </div>
        <div class="so-defs">
          <Piece v-bind="P1.x" :lit="lit" :hot="hot" @hot="hot = $event" />
        </div>
        <div class="so-defs">
          <DfdEq name="lab_l" :k="KD" />
        </div>
        <Transition name="so-fade">
          <div v-if="more" class="so-more">
            <span class="so-more-k">as published · any <i>n</i>, x from the upstream edge</span>
            <DfdEq name="s1_jog" :k="KM" :inline="false" />
          </div>
        </Transition>
      </section>

      <!-- 2-D -->
      <section class="so-col">
        <h3 class="so-h">2-D · a circular slippery patch <span class="so-ref">Lai, Rines, Coffey et al. 2026 · PNAS</span></h3>
        <div class="so-eq">
          <Piece v-bind="P2.lhs" :lit="lit" :hot="hot" @hot="hot = $event" />
          <span class="so-brace so-brace-2" aria-hidden="true"><svg viewBox="0 0 20 100" preserveAspectRatio="none"><path d="M 17 2 C 7 2 11 48 2 50 C 11 52 7 98 17 98" /></svg></span>
          <div class="so-cases">
            <div class="so-case"><Piece v-bind="P2.inn" :lit="lit" :hot="hot" @hot="hot = $event" /><DfdEq name="c_rin" :k="KC" class="so-cond" /></div>
            <div class="so-case so-case-wrap">
              <Piece v-bind="P2.outA" :lit="lit" :hot="hot" @hot="hot = $event" />
              <Piece v-bind="P2.outB" :lit="lit" :hot="hot" @hot="hot = $event" />
              <DfdEq name="c_rout" :k="KC" class="so-cond" />
            </div>
          </div>
        </div>
        <div class="so-defs">
          <Piece v-bind="P2.lam" :lit="lit" :hot="hot" @hot="hot = $event" />
          <DfdEq name="def_k0" :k="KD" />
        </div>
        <div class="so-defs so-defs-f">
          <Piece v-bind="P2.fd" :lit="lit" :hot="hot" @hot="hot = $event" />
          <DfdEq name="s2_fz" :k="KD * 0.92" />
          <DfdEq name="s2_sigma" :k="KD" />
        </div>
        <Transition name="so-fade">
          <div v-if="more" class="so-more so-more-2">
            <DfdEq name="s2_rt" :k="KM" :inline="false" />
            <DfdEq name="s2_tt" :k="KM" :inline="false" />
            <DfdEq name="s2_cauchy" :k="KM * 0.95" :inline="false" />
          </div>
        </Transition>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import DfdEq from './DfdEq.vue'
import Piece from './DfdPiece.vue'
import { besselK0, besselK1, besselK2 } from '../lib/bessel'

/** px per bp: the equation pieces, the conditions, the definitions, the folded extras */
const KE = 3.0
const KC = 2.1
const KD = 2.3
const KM = 2.0

const lit = ref(false)
const more = ref(false)
const bessel = ref(false)
/** px per bp for the Bessel card's rows */
const KB = 2.1

// ── the Bessel card: the rows (what each line is, in a word) and the plot ──
const BESSEL_ROWS = [
  { name: 'bessel_sep', kicker: 'where they arise' },
  { name: 'bessel_ode', kicker: 'the equation' },
  { name: 'bessel_int', kicker: 'the function' },
  { name: 's2_asym', kicker: 'far field' },
  { name: 'bessel_small', kicker: 'near the patch' },
  { name: 'bessel_k1pp', kicker: 'the identity the rr solution uses' },
]
const BW = 560
const BH = 360
const BL = 54
const BR = BW - 18
const BT = 14
const BB = BH - 46
const BX0 = 0
const BX1 = 6
const BY0 = -3 // log10 K
const BY1 = 2
const BX_TICKS = [0, 1, 2, 3, 4, 5, 6]
const BY_TICKS = [-3, -2, -1, 0, 1, 2]
function bx(x: number): number {
  return BL + ((x - BX0) / (BX1 - BX0)) * (BR - BL)
}
function by(l: number): number {
  return BB - ((l - BY0) / (BY1 - BY0)) * (BB - BT)
}
function bcurve(f: (x: number) => number): string {
  let d = ''
  const n = 180
  for (let i = 0; i <= n; i++) {
    const x = 0.04 + (i / n) * (BX1 - 0.04)
    const v = f(x)
    if (!(v > 0)) continue
    d += `${d ? 'L' : 'M'}${bx(x).toFixed(1)} ${by(Math.log10(v)).toFixed(1)}`
  }
  return d
}
const bpath = computed(() => ({
  k0: bcurve(besselK0),
  k1: bcurve(besselK1),
  k2: bcurve(besselK2),
  exp: bcurve((x) => Math.exp(-x)),
}))
/** The pair under the pointer while lit (the twin lights in the other column). */
const hot = ref<string | null>(null)

// The pieces and what each one is, physically (the labels the PHYSICAL
// INTUITION toggle reveals; the director's words to edit). `pair` names
// the twin piece in the other model.
const P1 = {
  lhs: { name: 's1_lhs', k: KE, pair: 'scale', label: 'stress in units of ½ρgαR — the driving stress ρgαH acting over the half-patch R, carried by the ice column H' },
  up: { name: 's1_up', k: KE, pair: 'outer', label: 'upstream boundary layer: membrane stress against basal drag — exponential, over 1/k₀ = √(4ηH/c₀)' },
  inn: { name: 's1_in', k: KE, pair: 'inner', label: 'inside the patch: no drag, so the membrane stress alone balances the driving stress — a linear ramp, tension at the upstream edge' },
  dn: { name: 's1_dn', k: KE, pair: 'outer', label: 'downstream: the mirror image — compression that decays the same way' },
  x: { name: 's1_jog_x', k: KD, pair: 'decay', label: 'the decay length: stiffer (η), thicker (H) ice reaches farther; stronger traction (c₀) shortens the reach' },
}
const P2 = {
  lhs: { name: 's2_lhs', k: KE, pair: 'scale', label: 'the same stress scale ½ρgαR; cos θ makes it a dipole — tension upstream (θ = π), compression downstream' },
  inn: { name: 's2_in', k: KE, pair: 'inner', label: 'the same ramp, lightened by 1 − fδ/4 (0.81–0.87): the ring of ice around the patch carries part of the load as hoop and shear stress' },
  outA: { name: 's2_out_a', k: KE, pair: 'outer', label: 'the stretching mode (the divergence δ): K₁″(r̃) ~ e^(−r̃) — exponential decay over 1/k₀, as in 1-D' },
  outB: { name: 's2_out_b', k: KE, pair: 'outer2', label: 'the shearing mode (the vorticity ζ), which has no 1-D analogue: K₂(2r̃) ~ e^(−2r̃), decaying twice as fast' },
  lam: { name: 'def_lambda', k: KD, pair: 'decay', label: 'λ = R/[x]: the patch radius in decay lengths — the one parameter that sets the shape' },
  fd: { name: 's2_fd', k: KD * 0.92, pair: 'split', label: 'how the patch’s load splits between stretching (fδ) and shearing (fζ = 4 − 4fδ); fδ runs 0.5 → 0.8 as λ → 0 → ∞' },
}
</script>

<style scoped>
.so {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 1.2vh;
  overflow-y: auto;
  padding-right: 0.5rem;
}
.so-head { display: flex; gap: 0.6rem; justify-content: center; }
.so-pill {
  border: 1px solid var(--gold);
  background: rgba(8, 6, 4, 0.78);
  color: var(--gold-bright);
  font: 500 0.82rem/1 'Inter', system-ui, sans-serif;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 0.6rem 1.2rem;
  border-radius: 999px;
  cursor: pointer;
  box-shadow: 0 0 18px rgba(245, 199, 94, 0.15);
}
.so-pill sub { font-size: 0.7em; text-transform: none; }
.so-pill:hover { color: #fff8d8; background: rgba(56, 38, 12, 0.85); }
.so-pill-on, .so-pill-on:hover { color: #1c1305; background: var(--gold); }
.so-pill-dim { border-color: var(--gold-dim); color: var(--gold-dim); box-shadow: none; }

.so-cols {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.3fr);
  gap: 2.5vw;
  align-items: start;
  padding-top: 1vh;
}
.so-col { min-width: 0; display: flex; flex-direction: column; gap: 2.2vh; }
.so-h {
  margin: 0;
  font-family: 'EB Garamond', Georgia, serif;
  font-weight: 500;
  font-size: clamp(1.1rem, 1.6vw, 1.8rem);
  color: var(--gold);
}
.so-ref {
  display: block;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.74rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--gold-dim);
  margin-top: 0.2rem;
}
.so-eq {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.so-eq > :first-child { flex: 0 0 auto; }
.so-eq > :first-child :deep(.pc-label) { max-width: 13rem; }
.so-eq > .so-cases { flex: 1 1 auto; min-width: 0; }
.so-brace {
  align-self: stretch;
  width: 1.1rem;
  flex: none;
}
.so-brace svg { width: 100%; height: 100%; }
.so-brace path { fill: none; stroke: #f5f0e6; stroke-width: 1.6; vector-effect: non-scaling-stroke; }
.so-cases { display: flex; flex-direction: column; gap: 1.6vh; }
.so-case { display: flex; align-items: center; gap: 1.2rem; flex-wrap: wrap; }
.so-case-wrap { gap: 0.6rem 1.2rem; }
.so-cond { opacity: 0.75; margin-left: 0.4rem; }
.so-defs { display: flex; flex-wrap: wrap; gap: 0.8rem 2rem; align-items: center; padding-left: 0.2rem; min-width: 0; }
.so-defs > * { min-width: 0; max-width: 100%; }
.so-defs-f { opacity: 0.95; }
.so-more {
  display: flex;
  flex-direction: column;
  gap: 1vh;
  padding: 1rem 1.2rem;
  border: 1px solid rgba(232, 185, 74, 0.25);
  border-radius: 10px;
  background: rgba(8, 6, 4, 0.5);
}
.so-more-k { font-size: 0.74rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--gold-dim); }
/* ── the Bessel card ── */
.so-bessel {
  position: fixed;
  inset: 0;
  z-index: 4;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.72);
  cursor: pointer;
}
.so-bessel-card {
  cursor: default;
  width: min(92vw, 86rem);
  max-height: 84vh;
  overflow: auto;
  display: grid;
  grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr);
  gap: 2.2vw;
  align-items: center;
  padding: 1.6rem 2rem;
  border: 1.5px solid var(--gold);
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(30, 24, 12, 0.985), rgba(10, 8, 5, 0.985));
  box-shadow: 0 14px 40px rgba(0, 0, 0, 0.8);
}
.so-bplot { position: relative; width: 100%; }
.so-bsvg { width: 100%; height: auto; display: block; }
.so-bframe { fill: none; stroke: rgba(245, 240, 230, 0.55); stroke-width: 1.2; }
.so-bax { stroke: rgba(245, 240, 230, 0.55); stroke-width: 1.2; }
.so-bgrid { stroke: rgba(245, 240, 230, 0.14); stroke-width: 1; }
.so-btt { font: 13px 'Inter', system-ui, sans-serif; fill: rgba(245, 240, 230, 0.85); }
.so-bti { font-family: 'EB Garamond', Georgia, serif; font-style: italic; font-size: 18px; }
.so-bk { fill: none; stroke-width: 3; stroke-linejoin: round; }
.so-bk0 { stroke: #f5f0e6; }
.so-bk1 { stroke: #f4cf6a; }
.so-bk2 { stroke: #e8862a; }
.so-bexp { fill: none; stroke: rgba(245, 240, 230, 0.6); stroke-width: 2; stroke-dasharray: 7 6; }
.so-bl { font-family: 'EB Garamond', Georgia, serif; font-style: italic; font-size: 20px; }
.so-bk0t { fill: #f5f0e6; }
.so-bk1t { fill: #f4cf6a; }
.so-bk2t { fill: #e8862a; }
.so-bax-y { position: absolute; left: 0; top: -1.7rem; }
.so-bleg { position: absolute; right: 5%; top: 5%; display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.3rem 0.6rem; border-radius: 8px; background: rgba(8, 6, 4, 0.7); border: 1px solid rgba(232, 185, 74, 0.25); }
.so-bleg i { display: inline-block; width: 1.6rem; border-top: 2px dashed rgba(245, 240, 230, 0.7); }
.so-brows { display: flex; flex-direction: column; gap: 1.1vh; min-width: 0; }
.so-brow { display: flex; flex-direction: column; gap: 0.2rem; min-width: 0; }
.so-brow > :last-child { max-width: 100%; }
.so-bk-k { font-size: 0.7rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--gold-dim); }
.so-fade-enter-active, .so-fade-leave-active { transition: opacity 0.25s; }
.so-fade-enter-from, .so-fade-leave-to { opacity: 0; }
</style>
