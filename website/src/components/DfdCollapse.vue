<template>
  <!-- THE COLLAPSE: the paper's Fig. 3 C–D re-drawn live from the sweep.
       View 0 (Profiles): the depth-averaged 3-D Stokes Δσ̄_rr along the
       flow line (y = 0) for the runs sharing one λ = k₀R — dimensional on
       the left, and on the right scaled by the two closed-form scales
       ([τ] = ½ρgαR, 1/k₀), where they fall on ONE theory curve. View 1
       (Maxima): every run's simulated maximum against its theoretical one
       (Fig. 3D), marker = H, colour = αR. Profiles: dfd/slab_profiles_v1.json
       (cinematic/scene_addl/build_dfd_profiles.py); theory: lib/slabTheory;
       maxima: the sweep manifest. Flow is toward +x; tension sits upstream. -->
  <div class="cl">
    <!-- ── the controls ── -->
    <div class="cl-top">
      <div class="cl-views">
        <button
          v-for="(v, i) in VIEWS"
          :key="v"
          class="cl-view"
          :class="{ 'cl-view-on': i === step }"
          :aria-current="i === step ? 'step' : undefined"
          @click="emit('step', i)"
        >
          {{ v }}
        </button>
      </div>
      <template v-if="step === 0">
        <div class="cl-lam">
          <DfdEq name="def_lambda" :k="1.9" class="cl-lam-def" />
          <input
            type="range"
            min="0"
            :max="Math.max(0, groups.length - 1)"
            step="1"
            :value="lamIdx"
            aria-label="lambda"
            @input="onLam"
          />
          <b class="cl-lam-v">{{ group ? group.lambda.toFixed(2) : '—' }}</b>
          <span class="cl-lam-n">{{ group ? group.ids.length : 0 }} runs</span>
        </div>
        <button class="cl-sw" :class="{ 'cl-sw-on': showAll }" @click="showAll = !showAll">
          all {{ profiles ? Object.keys(profiles.runs).length : 75 }} runs
        </button>
      </template>
      <template v-else>
        <div class="cl-fields">
          <button
            v-for="f in FIELDS"
            :key="f"
            class="cl-fpill"
            :class="{ 'cl-fpill-on': f === field }"
            :aria-label="f"
            @click="field = f"
          >
            <DfdEq :name="'fb_' + f" set="slab" :k="2.0" />
          </button>
        </div>
        <span class="cl-note">{{ dots.length }} runs · depth average</span>
      </template>
    </div>

    <!-- ── view 0: the profiles and their collapse ── -->
    <div v-if="step === 0" class="cl-prof">
      <div class="cl-plots">
        <!-- dimensional -->
        <svg :viewBox="`0 0 ${W} ${H}`" class="cl-svg" aria-label="Depth-averaged radial Cauchy stress perturbation along the flow line, kPa against signed r in km, Stokes against theory" @mousemove="onMoveD" @mouseleave="hovD = null">
          <text :x="PL" :y="21" class="cl-title">DIMENSIONAL</text>
          <text :x="PR" :y="21" text-anchor="end" class="cl-title cl-title-dim">y = 0 · Stokes ——— · theory – – –</text>
          <rect v-if="series.length" :x="px(-series[0].p.R / 1000)" :y="PT" :width="px(series[0].p.R / 1000) - px(-series[0].p.R / 1000)" :height="PB - PT" class="cl-band" />
          <line :x1="PL" :x2="PR" :y1="py(0)" :y2="py(0)" class="cl-ax0" />
          <g v-for="t in yTicks" :key="'y' + t">
            <line :x1="PL - 6" :x2="PL" :y1="py(t)" :y2="py(t)" class="cl-ax" />
            <text :x="PL - 10" :y="py(t) + 4.5" text-anchor="end" class="cl-tt">{{ t }}</text>
          </g>
          <g v-for="t in xTicks" :key="'x' + t">
            <line :x1="px(t)" :x2="px(t)" :y1="PB" :y2="PB + 6" class="cl-ax" />
            <text :x="px(t)" :y="PB + 21" text-anchor="middle" class="cl-tt">{{ t }}</text>
          </g>
          <rect :x="PL" :y="PT" :width="PR - PL" :height="PB - PT" class="cl-frame" />
          <text :x="PR - 10" :y="PT + 19" text-anchor="end" class="cl-flow">ice flow →</text>
          <g v-for="(sr, i) in series" :key="sr.id">
            <path :d="dimSim[i].line" class="cl-sim" :style="{ stroke: sr.colour }" />
            <path :d="dimSim[i].marks" class="cl-mk" :style="{ fill: sr.colour }" />
          </g>
          <path v-for="(d, i) in dimTheory" :key="'t' + i" :d="d" class="cl-th" :style="{ stroke: series[i].colour }" />
          <!-- the hover: a hairline and the numbers at that x -->
          <g v-if="hovD !== null">
            <line :x1="px(hovD)" :x2="px(hovD)" :y1="PT" :y2="PB" class="cl-hair" />
            <text :x="PL + 10" :y="PT + 20" class="cl-tt cl-hov">r = {{ hovD.toFixed(2) }} km</text>
            <text v-for="(r, i) in hovReadD" :key="r.id" :x="PL + 10" :y="PT + 38 + i * 17" class="cl-tt cl-hov" :style="{ fill: r.colour }">{{ r.text }}</text>
          </g>
          <text :x="(PL + PR) / 2" :y="H - 8" text-anchor="middle" class="cl-tt cl-axt"><tspan font-style="italic">r</tspan> [km]</text>
          <text :x="17" :y="(PT + PB) / 2" text-anchor="middle" class="cl-tt cl-axt" :transform="`rotate(-90 17 ${(PT + PB) / 2})`">Δ<tspan font-style="italic">σ̄</tspan><tspan dy="4" font-size="10.5" font-style="italic">rr</tspan><tspan dy="-4"> [kPa]</tspan></text>
        </svg>

        <!-- dimensionless -->
        <svg :viewBox="`0 0 ${W} ${H}`" class="cl-svg" aria-label="The same profiles scaled by the stress scale and the decay length, falling on the one theory curve for this lambda" @mousemove="onMoveN" @mouseleave="hovN = null">
          <text :x="PL" :y="21" class="cl-title">DIMENSIONLESS · λ = {{ lam.toFixed(2) }}</text>
          <text :x="PR" :y="21" text-anchor="end" class="cl-title cl-title-dim">one theory curve – – –</text>
          <rect :x="nx(-lam)" :y="PT" :width="nx(lam) - nx(-lam)" :height="PB - PT" class="cl-band" />
          <line :x1="PL" :x2="PR" :y1="ny(0)" :y2="ny(0)" class="cl-ax0" />
          <g v-for="t in nyTicks" :key="'y' + t">
            <line :x1="PL - 6" :x2="PL" :y1="ny(t)" :y2="ny(t)" class="cl-ax" />
            <text :x="PL - 10" :y="ny(t) + 4.5" text-anchor="end" class="cl-tt">{{ t }}</text>
          </g>
          <g v-for="t in nxTicks" :key="'x' + t">
            <line :x1="nx(t)" :x2="nx(t)" :y1="PB" :y2="PB + 6" class="cl-ax" />
            <text :x="nx(t)" :y="PB + 21" text-anchor="middle" class="cl-tt">{{ t }}</text>
          </g>
          <rect :x="PL" :y="PT" :width="PR - PL" :height="PB - PT" class="cl-frame" />
          <path v-for="(d, i) in nAll" :key="'a' + i" :d="d" class="cl-all" />
          <g v-for="(sr, i) in series" :key="sr.id">
            <path :d="nSim[i].line" class="cl-sim" :style="{ stroke: sr.colour }" />
            <path :d="nSim[i].marks" class="cl-mk" :style="{ fill: sr.colour }" />
          </g>
          <path :d="nTheoryPath" class="cl-th1" />
          <!-- k₀'s definition (the axes carry the scales themselves), in the quadrant the curves never enter (downstream is compression) -->
          <foreignObject :x="PR - CAPW - 6" :y="PT + 8" :width="CAPW" :height="CAPH">
            <div class="cl-capwrap"><div class="cl-cap"><DfdEq name="def_k0" :k="1.9" :inline="false" /></div></div>
          </foreignObject>
          <g v-if="hovN !== null">
            <line :x1="nx(hovN)" :x2="nx(hovN)" :y1="PT" :y2="PB" class="cl-hair" />
            <text :x="PL + 10" :y="PT + 20" class="cl-tt cl-hov">r̃ = {{ hovN.toFixed(2) }}</text>
            <text v-for="(r, i) in hovReadN" :key="r.id" :x="PL + 10" :y="PT + 38 + i * 17" class="cl-tt cl-hov" :style="{ fill: r.colour }">{{ r.text }}</text>
          </g>
          <text :x="(PL + PR) / 2" :y="H - 8" text-anchor="middle" class="cl-tt cl-axt"><tspan font-style="italic">r̃</tspan> = <tspan font-style="italic">k</tspan><tspan dy="4" font-size="10.5">0</tspan><tspan dy="-4"> </tspan><tspan font-style="italic">r</tspan></text>
          <text :x="17" :y="(PT + PB) / 2" text-anchor="middle" class="cl-tt cl-axt" :transform="`rotate(-90 17 ${(PT + PB) / 2})`">Δ<tspan font-style="italic">σ̄</tspan><tspan dy="4" font-size="10.5" font-style="italic">rr</tspan><tspan dy="-4"> / (½</tspan><tspan font-style="italic">ρgαR</tspan><tspan>)</tspan></text>
        </svg>
      </div>

      <!-- the runs of this λ: click to show / hide; the scales of the shown ones -->
      <div class="cl-leg">
        <button
          v-for="sr in groupSeries"
          :key="sr.id"
          class="cl-chip"
          :class="{ 'cl-chip-on': isSel(sr.id) }"
          :style="{ '--c': sr.colour }"
          :aria-pressed="isSel(sr.id)"
          @click="toggle(sr.id)"
        >
          <svg class="cl-chip-m" viewBox="-9 -9 18 18" aria-hidden="true">
            <line x1="-9" x2="9" y1="0" y2="0" :stroke="sr.colour" stroke-width="2.2" />
            <path :d="markerPath(sr.shape, 0, 0, 4.6)" :fill="sr.colour" stroke="#0a0a0c" stroke-width="1" />
          </svg>
          <span class="cl-chip-p">{{ sr.label }}</span>
          <span class="cl-chip-s">
            <DfdEq name="sym_tau_scale" :k="1.45" /> {{ fmtK(sr.s.stressPa / 1000) }} kPa
            &nbsp;·&nbsp;
            <DfdEq name="sym_k0inv" :k="1.45" /> {{ (sr.s.decayM / 1000).toFixed(2) }} km
          </span>
        </button>
      </div>
    </div>

    <!-- ── view 1: the maxima against theory (Fig. 3D) ── -->
    <div v-else class="cl-max">
      <div class="cl-sc">
        <svg :viewBox="`0 0 ${SW} ${SH}`" class="cl-svg" aria-label="Each run's simulated maximum stress perturbation against the theoretical one, with the one-to-one line">
          <g v-for="t in sTicks" :key="'sx' + t">
            <line :x1="sx(t)" :x2="sx(t)" :y1="SPB" :y2="SPB + 6" class="cl-ax" />
            <text :x="sx(t)" :y="SPB + 22" text-anchor="middle" class="cl-tt">{{ t }}</text>
            <line :x1="SPL - 6" :x2="SPL" :y1="sy(t)" :y2="sy(t)" class="cl-ax" />
            <text :x="SPL - 10" :y="sy(t) + 4.5" text-anchor="end" class="cl-tt">{{ t }}</text>
          </g>
          <rect :x="SPL" :y="SPT" :width="SPR - SPL" :height="SPB - SPT" class="cl-frame" />
          <line :x1="sx(0)" :y1="sy(0)" :x2="sx(sLim)" :y2="sy(sLim)" class="cl-yx" />
          <text :x="sx(0.52 * sLim) + 16" :y="sy(0.52 * sLim) + 10" class="cl-tt cl-yx-t"><tspan font-style="italic">y</tspan> = <tspan font-style="italic">x</tspan></text>
          <g v-for="d in dots" :key="d.id" class="cl-dot" :class="{ 'cl-dot-on': hov && hov.id === d.id }" @mouseenter="hov = d" @mouseleave="hov = null">
            <circle :cx="sx(d.x)" :cy="sy(d.y)" r="13" class="cl-hit" />
            <path :d="markerPath(d.shape, sx(d.x), sy(d.y), 6.5)" class="cl-mark" :style="{ fill: d.fill }" />
          </g>
          <text :x="(SPL + SPR) / 2" :y="SH - 10" text-anchor="middle" class="cl-tt cl-axt">theory · max |Δ<tspan font-style="italic">σ̄</tspan><tspan dy="4" font-size="10.5" font-style="italic">{{ SUB[field] }}</tspan><tspan dy="-4">| [kPa]</tspan></text>
          <text :x="20" :y="(SPT + SPB) / 2" text-anchor="middle" class="cl-tt cl-axt" :transform="`rotate(-90 20 ${(SPT + SPB) / 2})`">3-D Stokes · max |Δ<tspan font-style="italic">σ̄</tspan><tspan dy="4" font-size="10.5" font-style="italic">{{ SUB[field] }}</tspan><tspan dy="-4">| [kPa]</tspan></text>
        </svg>
        <div v-if="hov" class="cl-tip" :class="{ 'cl-tip-below': sy(hov.y) < 0.22 * SH }" :style="{ left: (sx(hov.x) / SW) * 100 + '%', top: (sy(hov.y) / SH) * 100 + '%' }">
          <b>{{ hov.id }}</b>
          <span>{{ hov.label }} · c₀ {{ fmtPow(hov.c0) }} Pa s m⁻¹</span>
          <span>theory {{ fmtK(hov.x) }} · Stokes {{ fmtK(hov.y) }} kPa</span>
        </div>
      </div>
      <div class="cl-side">
        <div class="cl-hleg">
          <span class="cl-hleg-k">marker · <i>H</i></span>
          <span v-for="h in H_LIST" :key="h" class="cl-hleg-r">
            <svg viewBox="-9 -9 18 18" class="cl-hleg-m" aria-hidden="true"><path :d="markerPath(H_SHAPES[h], 0, 0, 6)" fill="#f5f0e6" /></svg>
            <span>{{ h >= 1000 ? h / 1000 + ' km' : h + ' m' }}</span>
          </span>
        </div>
        <div class="cl-cbar">
          <span class="cl-hleg-k">colour · <i>αR</i> [m]</span>
          <div class="cl-cbar-row">
            <div class="cl-cbar-bar" />
            <div class="cl-cbar-ticks"><span v-for="t in [...AR_TICKS].reverse()" :key="t">{{ t }}</span></div>
          </div>
          <span class="cl-cbar-eq"><DfdEq name="scales" :k="1.5" :inline="false" /></span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, shallowRef, watch } from 'vue'
import DfdEq from './DfdEq.vue'
import { loadSlabManifest, type SlabManifest } from '../config/ch2Slab'
import {
  COLLAPSE_COLOURS,
  COLLAPSE_DEFAULT_LAMBDA,
  COLLAPSE_PAPER_RUNS,
  COLLAPSE_SHAPES,
  H_SHAPES,
  fmtPow,
  fmtRunParams,
  goldRamp,
  lambdaGroups,
  loadSlabProfiles,
  markerPath,
  niceCeil,
  niceStep,
  symTicks,
  type LambdaGroup,
  type MarkerShape,
  type SlabProfiles,
} from '../config/dfdCollapse'
import { ETA, fieldAt, slabScales, tauHat, type SlabParams, type SlabScales } from '../lib/slabTheory'

defineProps<{
  /** The view on screen: 0 the profiles and their collapse, 1 the maxima. */
  step: number
}>()
const emit = defineEmits<{ step: [n: number] }>()
const VIEWS = ['Profiles', 'Maxima']

const profiles = shallowRef<SlabProfiles | null>(null)
const man = shallowRef<SlabManifest | null>(null)
onMounted(async () => {
  const [p, m] = await Promise.all([loadSlabProfiles(), loadSlabManifest()])
  profiles.value = p
  man.value = m
})

// ── view 0: the λ groups and the selection ──
const groups = computed<LambdaGroup[]>(() => (profiles.value ? lambdaGroups(profiles.value.runs) : []))
const lamIdx = ref(0)
const selected = ref<string[]>([])
const showAll = ref(false)
const group = computed(() => groups.value[lamIdx.value] ?? null)
/** The paper's three when the group holds them, else the whole group. */
function selectDefault(): void {
  const g = group.value
  if (!g) return
  const paper = COLLAPSE_PAPER_RUNS.filter((id) => g.ids.includes(id))
  selected.value = paper.length ? paper : [...g.ids]
}
watch(groups, (gs) => {
  if (!gs.length) return
  let best = 0
  for (let i = 1; i < gs.length; i++) {
    if (Math.abs(gs[i].lambda - COLLAPSE_DEFAULT_LAMBDA) < Math.abs(gs[best].lambda - COLLAPSE_DEFAULT_LAMBDA)) best = i
  }
  lamIdx.value = best
  selectDefault()
})
function onLam(e: Event): void {
  lamIdx.value = parseInt((e.target as HTMLInputElement).value, 10)
  selectDefault()
}
function isSel(id: string): boolean {
  return selected.value.includes(id)
}
function toggle(id: string): void {
  if (isSel(id)) {
    if (selected.value.length > 1) selected.value = selected.value.filter((x) => x !== id)
  } else {
    selected.value = [...selected.value, id]
  }
}

interface Series {
  id: string
  colour: string
  shape: MarkerShape
  p: SlabParams
  s: SlabScales
  /** Δσ̄_rr along y = 0, kPa, on profiles.x_km */
  srr: number[]
  label: string
}
/** The group's runs in its fixed order — colour and marker follow the run, not the selection. */
const groupSeries = computed<Series[]>(() => {
  const pr = profiles.value
  const g = group.value
  if (!pr || !g) return []
  return g.ids.map((id, i) => {
    const r = pr.runs[id]
    const p: SlabParams = { H: r.H, alphaDeg: r.alpha_deg, gamma: r.gamma, R: r.R }
    return {
      id,
      colour: COLLAPSE_COLOURS[i % COLLAPSE_COLOURS.length],
      shape: COLLAPSE_SHAPES[i % COLLAPSE_SHAPES.length],
      p,
      s: slabScales(p),
      srr: r.srr_kpa,
      label: fmtRunParams(r),
    }
  })
})
const series = computed(() => groupSeries.value.filter((sr) => isSel(sr.id)))
const xs = computed(() => profiles.value?.x_km ?? [])

// ── the two profile plots (one viewBox) ──
const W = 720
const H = 560
const PL = 70
const PR = W - 18
const PT = 34
const PB = H - 46
const NTH = 241
/** markers: about twenty per curve, whatever the window */
const MARKS = 20
type Pt = [number, number]
function linePath(pts: Pt[], fx: (x: number) => number, fy: (y: number) => number): string {
  let d = ''
  for (const [x, y] of pts) d += `${d ? 'L' : 'M'}${fx(x).toFixed(1)} ${fy(y).toFixed(1)}`
  return d
}
function markPath(pts: Pt[], shape: MarkerShape, fx: (x: number) => number, fy: (y: number) => number): string {
  let d = ''
  const every = Math.max(2, Math.round(pts.length / MARKS))
  for (let k = 0; k < pts.length; k += every) d += markerPath(shape, fx(pts[k][0]), fy(pts[k][1]), 4.6)
  return d
}

// dimensional: x in km, Δσ̄_rr in kPa
// FIXED AXES, the director's rule (2026-11-21 night: "the axes are having a
// seizure when I move the slider") — nothing below depends on the group or
// the selection, so the λ slider and the chips only move the curves.
/** Half-width in km: the baked profiles' own extent. */
const X_HALF_KM = 25
/** The sweep's largest |Δσ̄_rr| along y = 0 is 618 kPa (R = 5 km, H = 300 m,
 *  α = 1°, γ = 1); ±750 puts a 250 kPa tick on each frame edge. */
const Y_LIM_KPA = 750
/** The k₀ plate inside the dimensionless plot (viewBox units). */
const CAPW = 220
const CAPH = 96
/** Dimensionless half-width: at least 2.3 decay lengths past the patch
 *  edge for 21 of the 23 λ groups (λ ≤ 3.73); the two largest (5.9, 11.8)
 *  show their patch edges at or beyond the frame. */
const N_HALF = 6
/** The sweep's largest |Δσ̄_rr| / [τ] is 1.57. */
const N_LIM = 2
const xHalf = computed(() => X_HALF_KM)
const dimSimPts = computed<Pt[][]>(() =>
  series.value.map((sr) => {
    const pts: Pt[] = []
    xs.value.forEach((x, k) => {
      if (Math.abs(x) <= xHalf.value) pts.push([x, sr.srr[k]])
    })
    return pts
  }),
)
const dimThPts = computed<Pt[][]>(() =>
  series.value.map((sr) => {
    const pts: Pt[] = []
    for (let k = 0; k < NTH; k++) {
      const x = -xHalf.value + (2 * xHalf.value * k) / (NTH - 1)
      pts.push([x, fieldAt(x * 1000, 0, sr.p, sr.s, 'srr') / 1000])
    }
    return pts
  }),
)
const yLim = computed(() => Y_LIM_KPA)
const yTicks = computed(() => symTicks(yLim.value))
const xTicks = computed(() => symTicks(xHalf.value))
function px(xkm: number): number {
  return PL + ((xkm + xHalf.value) / (2 * xHalf.value)) * (PR - PL)
}
function py(v: number): number {
  const half = (PB - PT) / 2
  return PT + half - (v / yLim.value) * half
}
const dimSim = computed(() => dimSimPts.value.map((pts, i) => ({ line: linePath(pts, px, py), marks: markPath(pts, series.value[i].shape, px, py) })))
const dimTheory = computed(() => dimThPts.value.map((pts) => linePath(pts, px, py)))

// dimensionless: x̃ = x k₀, Δσ̄_rr / [τ]
const lam = computed(() => group.value?.lambda ?? COLLAPSE_DEFAULT_LAMBDA)
const refS = computed(() => series.value[0]?.s ?? slabScales({ H: 1000, alphaDeg: 1, gamma: 0.1, R: 2500 }))
const nHalf = computed(() => N_HALF)
function scaledPts(s: SlabScales, srr: number[]): Pt[] {
  const kx = 1000 / s.decayM
  const ky = 1000 / s.stressPa
  const pts: Pt[] = []
  xs.value.forEach((x, k) => {
    const xt = x * kx
    if (Math.abs(xt) <= nHalf.value) pts.push([xt, srr[k] * ky])
  })
  return pts
}
const nSimPts = computed<Pt[][]>(() => series.value.map((sr) => scaledPts(sr.s, sr.srr)))
const nThPts = computed<Pt[]>(() => {
  const pts: Pt[] = []
  const s = refS.value
  for (let k = 0; k < NTH; k++) {
    const xt = -nHalf.value + (2 * nHalf.value * k) / (NTH - 1)
    const h = tauHat(Math.abs(xt), s)
    // y = 0: cos θ = sign(x) — tension upstream (x < 0)
    pts.push([xt, (xt < 0 ? -1 : 1) * (2 * h.rr + h.tt)])
  }
  return pts
})
const nyLim = computed(() => N_LIM)
const nyTicks = computed(() => symTicks(nyLim.value))
const nxTicks = computed(() => symTicks(nHalf.value))
function nx(xt: number): number {
  return PL + ((xt + nHalf.value) / (2 * nHalf.value)) * (PR - PL)
}
function ny(v: number): number {
  const half = (PB - PT) / 2
  return PT + half - (v / nyLim.value) * half
}
const nSim = computed(() => nSimPts.value.map((pts, i) => ({ line: linePath(pts, nx, ny), marks: markPath(pts, series.value[i].shape, nx, ny) })))
const nTheoryPath = computed(() => linePath(nThPts.value, nx, ny))
/** Every other run of the sweep, greyed, each on its own scales (the toggle). */
const nAll = computed<string[]>(() => {
  const pr = profiles.value
  if (!showAll.value || !pr) return []
  const out: string[] = []
  for (const [id, r] of Object.entries(pr.runs)) {
    if (isSel(id)) continue
    const s = slabScales({ H: r.H, alphaDeg: r.alpha_deg, gamma: r.gamma, R: r.R })
    out.push(linePath(scaledPts(s, r.srr_kpa), nx, ny))
  }
  return out
})

// the hover: snap to the nearest baked x, read every shown run there
const hovD = ref<number | null>(null)
const hovN = ref<number | null>(null)
function viewX(e: MouseEvent): number | null {
  const el = e.currentTarget as SVGSVGElement
  const r = el.getBoundingClientRect()
  const sc = Math.min(r.width / W, r.height / H)
  const ox = (r.width - W * sc) / 2
  const vx = (e.clientX - r.left - ox) / sc
  return vx < PL || vx > PR ? null : vx
}
function onMoveD(e: MouseEvent): void {
  const vx = viewX(e)
  if (vx === null) {
    hovD.value = null
    return
  }
  const x = -xHalf.value + ((vx - PL) / (PR - PL)) * 2 * xHalf.value
  hovD.value = Math.round(x * 4) / 4
}
function onMoveN(e: MouseEvent): void {
  const vx = viewX(e)
  hovN.value = vx === null ? null : -nHalf.value + ((vx - PL) / (PR - PL)) * 2 * nHalf.value
}
function nearest(xkm: number): number {
  const a = xs.value
  let j = 0
  for (let i = 1; i < a.length; i++) if (Math.abs(a[i] - xkm) < Math.abs(a[j] - xkm)) j = i
  return j
}
const hovReadD = computed(() => {
  const x = hovD.value
  if (x === null) return []
  const k = nearest(x)
  return series.value.map((sr) => ({ id: sr.id, colour: sr.colour, text: `${fmtK(sr.srr[k])} kPa · theory ${fmtK(fieldAt(x * 1000, 0, sr.p, sr.s, 'srr') / 1000)}` }))
})
const hovReadN = computed(() => {
  const xt = hovN.value
  if (xt === null) return []
  const h = tauHat(Math.abs(xt), refS.value)
  const th = (xt < 0 ? -1 : 1) * (2 * h.rr + h.tt)
  const rows = series.value.map((sr) => {
    const k = nearest((xt * sr.s.decayM) / 1000)
    return { id: sr.id, colour: sr.colour, text: `${((sr.srr[k] * 1000) / sr.s.stressPa).toFixed(2)}` }
  })
  rows.push({ id: '_th', colour: '#f5f0e6', text: `theory ${th.toFixed(2)}` })
  return rows
})

// ── view 1: the maxima (Fig. 3D) ──
type MaxField = 'srr' | 'srt' | 'stt'
const FIELDS: MaxField[] = ['srr', 'srt', 'stt']
const SUB: Record<MaxField, string> = { srr: 'rr', srt: 'rθ', stt: 'θθ' }
const field = ref<MaxField>('srr')
const SW = 640
const SH = 640
const SPL = 82
const SPR = SW - 24
const SPT = 24
const SPB = SH - 62
const AR_MAX = 90
const AR_TICKS = [0, 30, 60, 90]
const H_LIST = [300, 500, 750, 1000, 2000, 3000]
interface Dot {
  id: string
  x: number
  y: number
  c0: number
  aR: number
  shape: MarkerShape
  fill: string
  label: string
}
const dots = computed<Dot[]>(() => {
  const m = man.value
  if (!m) return []
  const f = field.value
  const out: Dot[] = []
  for (const [id, r] of Object.entries(m.runs)) {
    const x = r.max_kpa.theory[f]
    const y = r.max_kpa.sim_da[f]
    if (x === undefined || y === undefined) continue
    const aR = ((r.alpha_deg * Math.PI) / 180) * r.R
    out.push({ id, x, y, c0: (2 * ETA * r.gamma) / r.H, aR, shape: H_SHAPES[r.H] ?? 'circle', fill: goldRamp(aR / AR_MAX), label: fmtRunParams(r) })
  }
  // the brightest (largest αR) drawn last, on top
  out.sort((a, b) => a.aR - b.aR)
  return out
})
const sLim = computed(() => {
  let m = 1
  for (const d of dots.value) m = Math.max(m, d.x, d.y)
  return niceCeil(m * 1.04)
})
const sTicks = computed(() => {
  const st = niceStep(sLim.value / 5)
  const out: number[] = []
  for (let v = 0; v <= sLim.value + 1e-9; v += st) out.push(Math.round(v * 100) / 100)
  return out
})
function sx(v: number): number {
  return SPL + (v / sLim.value) * (SPR - SPL)
}
function sy(v: number): number {
  return SPB - (v / sLim.value) * (SPB - SPT)
}
const hov = ref<Dot | null>(null)

function fmtK(v: number): string {
  const a = Math.abs(v)
  return a >= 100 ? v.toFixed(0) : a >= 10 ? v.toFixed(1) : v.toFixed(2)
}
</script>

<style scoped>
.cl {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 1.2vh;
  color: #f5f0e6;
  font-family: 'Inter', system-ui, sans-serif;
  overflow: hidden;
}

/* ── the controls ── */
.cl-top {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 1rem;
}
.cl-views { display: flex; gap: 0.3rem; justify-self: start; }
.cl-view {
  border: 1px solid rgba(232, 185, 74, 0.4);
  background: rgba(8, 6, 4, 0.7);
  color: var(--gold-dim);
  font: 500 0.78rem/1 'Inter', system-ui, sans-serif;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 0.5rem 0.95rem;
  border-radius: 999px;
  cursor: pointer;
}
.cl-view:hover { color: var(--gold-bright); }
.cl-view-on { color: #1c1305; background: var(--gold); border-color: var(--gold-bright); }
.cl-lam {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.35rem 1rem;
  border: 1px solid rgba(232, 185, 74, 0.25);
  border-radius: 999px;
  background: rgba(8, 6, 4, 0.5);
}
.cl-lam-def { margin-right: 0.3rem; }
.cl-lam input[type='range'] {
  -webkit-appearance: none;
  appearance: none;
  width: 240px;
  height: 6px;
  margin: 0;
  border-radius: 3px;
  background: rgba(245, 199, 94, 0.42);
  cursor: pointer;
}
.cl-lam input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #f5c75e;
  border: 1px solid rgba(0, 0, 0, 0.55);
}
.cl-lam input[type='range']::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #f5c75e;
  border: 1px solid rgba(0, 0, 0, 0.55);
}
.cl-lam-v { font-size: 1.1rem; font-weight: 600; color: #fff8e6; font-variant-numeric: tabular-nums; min-width: 2.6rem; }
.cl-lam-n { font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--gold-dim); white-space: nowrap; min-width: 4.2rem; font-variant-numeric: tabular-nums; }
.cl-sw {
  justify-self: end;
  border: 1px solid rgba(232, 185, 74, 0.35);
  background: transparent;
  color: var(--gold-dim);
  font: 500 0.72rem/1 'Inter', system-ui, sans-serif;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.45rem 0.8rem;
  border-radius: 999px;
  cursor: pointer;
}
.cl-sw:hover { color: var(--gold-bright); }
.cl-sw-on { color: #1c1305; background: var(--gold); border-color: var(--gold-bright); }
.cl-fields { display: flex; gap: 0.4rem; }
.cl-fpill {
  border: 1px solid rgba(232, 185, 74, 0.4);
  background: rgba(8, 6, 4, 0.7);
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  cursor: pointer;
  opacity: 0.72;
}
.cl-fpill:hover { opacity: 1; }
.cl-fpill-on { opacity: 1; border-color: var(--gold-bright); background: rgba(232, 185, 74, 0.18); box-shadow: 0 0 12px rgba(245, 199, 94, 0.3); }
.cl-note { justify-self: end; font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--gold-dim); }

/* ── view 0 ── */
.cl-prof {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 0.8vh;
  min-height: 0;
}
.cl-plots {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 1.2vw;
  min-height: 0;
}
.cl-svg { width: 100%; height: 100%; display: block; }
.cl-frame { fill: none; stroke: rgba(245, 240, 230, 0.55); stroke-width: 1.2; }
.cl-ax { stroke: rgba(245, 240, 230, 0.55); stroke-width: 1.2; }
.cl-ax0 { stroke: rgba(245, 240, 230, 0.28); stroke-width: 1; }
.cl-tt { font: 13px 'Inter', system-ui, sans-serif; fill: rgba(245, 240, 230, 0.85); }
.cl-axt { font-size: 14px; fill: #f5f0e6; }
.cl-title { font: 500 13px 'Inter', system-ui, sans-serif; letter-spacing: 0.12em; fill: var(--gold); }
.cl-title-dim { fill: var(--gold-dim); letter-spacing: 0.06em; font-weight: 400; }
.cl-flow { font: 500 12px 'Inter', system-ui, sans-serif; letter-spacing: 0.12em; text-transform: uppercase; fill: var(--gold-dim); }
.cl-band { fill: rgba(232, 185, 74, 0.09); }
.cl-sim { fill: none; stroke-width: 2.6; stroke-linejoin: round; }
.cl-mk { stroke: #0a0a0c; stroke-width: 1; }
.cl-th { fill: none; stroke-width: 2.4; stroke-dasharray: 8 6; stroke-linejoin: round; opacity: 0.95; }
.cl-th1 { fill: none; stroke: #f5f0e6; stroke-width: 3; stroke-dasharray: 10 7; stroke-linejoin: round; }
.cl-all { fill: none; stroke: rgba(245, 240, 230, 0.16); stroke-width: 1.3; }
.cl-hair { stroke: rgba(244, 207, 106, 0.6); stroke-width: 1.2; stroke-dasharray: 4 4; pointer-events: none; }
.cl-hov { font-weight: 500; fill: #fff8e6; paint-order: stroke; stroke: rgba(5, 5, 5, 0.85); stroke-width: 4; pointer-events: none; }

.cl-leg {
  /* a grid of same-sized two-line chips, exactly two rows tall whatever the group
     (nine chips fit at 1366 px and up) — the plots above never change height */
  --chip-h: 3.1rem;
  height: calc(2 * var(--chip-h) + 0.5rem);
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  grid-auto-rows: var(--chip-h);
  gap: 0.5rem 0.7rem;
  overflow: hidden;
}
.cl-chip {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  grid-template-rows: auto auto;
  column-gap: 0.5rem;
  row-gap: 0.1rem;
  align-items: center;
  align-content: center;
  text-align: left;
  border: 1px solid rgba(232, 185, 74, 0.22);
  background: rgba(8, 6, 4, 0.55);
  color: rgba(245, 240, 230, 0.55);
  font: 400 0.84rem/1.15 'Inter', system-ui, sans-serif;
  padding: 0 0.7rem 0 0.55rem;
  border-radius: 14px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
}
.cl-chip:hover { border-color: var(--gold-dim); }
.cl-chip-on { color: #f5f0e6; border-color: var(--c); box-shadow: 0 0 10px color-mix(in srgb, var(--c) 35%, transparent); }
.cl-chip-m { width: 22px; height: 22px; grid-row: 1 / 3; }
.cl-chip:not(.cl-chip-on) .cl-chip-m { opacity: 0.5; }
.cl-chip-p { font-variant-numeric: tabular-nums; }
.cl-chip-s {
  display: block;
  line-height: 1.2;
  font-size: 0.78rem;
  color: #fff8e6;
  font-variant-numeric: tabular-nums;
}
.cl-chip:not(.cl-chip-on) .cl-chip-s { color: rgba(245, 240, 230, 0.45); }
.cl-capwrap { display: flex; justify-content: flex-end; }
.cl-cap {
  padding: 0.3rem 0.9rem;
  border: 1px solid rgba(232, 185, 74, 0.22);
  border-radius: 10px;
  background: rgba(8, 6, 4, 0.55);
}

/* ── view 1 ── */
.cl-max {
  display: flex;
  justify-content: center;
  align-items: stretch;
  gap: 2.2vw;
  min-height: 0;
}
.cl-sc { position: relative; height: 100%; aspect-ratio: 1; max-width: 62vw; }
.cl-yx { stroke: var(--gold-bright); stroke-width: 2; stroke-dasharray: 9 7; }
.cl-yx-t { fill: var(--gold-bright); font-size: 14px; }
.cl-dot { cursor: default; }
.cl-hit { fill: transparent; }
.cl-mark { stroke: #0a0a0c; stroke-width: 1.2; }
.cl-dot:hover .cl-mark, .cl-dot-on .cl-mark { stroke: #fff8e6; stroke-width: 2; filter: drop-shadow(0 0 6px rgba(245, 199, 94, 0.9)); }
.cl-tip {
  position: absolute;
  transform: translate(-50%, calc(-100% - 16px));
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  padding: 0.45rem 0.7rem;
  border-radius: 8px;
  border: 1px solid rgba(232, 185, 74, 0.4);
  background: rgba(8, 6, 4, 0.92);
  font-size: 0.84rem;
  white-space: nowrap;
  pointer-events: none;
  z-index: 2;
}
.cl-tip-below { transform: translate(-50%, 16px); }
.cl-tip b { color: var(--gold-bright); font-weight: 600; letter-spacing: 0.03em; }
.cl-tip span { color: rgba(245, 240, 230, 0.9); font-variant-numeric: tabular-nums; }
.cl-side {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 2.4vh;
  padding: 1.2rem 1.4rem;
  border: 1px solid rgba(232, 185, 74, 0.25);
  border-radius: 12px;
  background: rgba(8, 6, 4, 0.5);
  align-self: center;
}
.cl-hleg { display: flex; flex-direction: column; gap: 0.45rem; }
.cl-hleg-k { font-size: 0.74rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--gold); margin-bottom: 0.2rem; }
.cl-hleg-k i { font-family: 'EB Garamond', Georgia, serif; font-style: italic; font-size: 1.05rem; text-transform: none; letter-spacing: 0; }
.cl-hleg-r { display: inline-flex; align-items: center; gap: 0.6rem; font-size: 0.98rem; font-variant-numeric: tabular-nums; }
.cl-hleg-m { width: 22px; height: 22px; }
.cl-cbar { display: flex; flex-direction: column; gap: 0.45rem; }
.cl-cbar-row { display: flex; align-items: stretch; gap: 0.5rem; }
.cl-cbar-bar {
  width: 16px;
  height: 150px;
  border: 1px solid rgba(255, 255, 255, 0.45);
  border-radius: 3px;
  background: linear-gradient(to top, #9a6016, #fff0be);
}
.cl-cbar-ticks {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  font-size: 0.92rem;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}
.cl-cbar-eq { margin-top: 0.6rem; }
</style>
