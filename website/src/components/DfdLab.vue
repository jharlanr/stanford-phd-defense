<template>
  <!-- THE LAB: the closed-form theory live, on continuous sliders over
       every parameter (H · α · c₀ · R — the PAPER's four; the sweep's
       γ = c₀H/2η stays internal, the director's rule: the paper's notation). Left: the 2-D depth-averaged field of
       any component on the central ±25 km, painted from lib/slabTheory
       (Bessel K, no rasters). Right: the centreline profile — the 2-D
       τ̄_xx along y = 0 (the dotted line across the field is where the
       section is cut; the 2-D curve is dotted to match) against the 1-D
       closed form for the SAME parameters (patch length 2R, the same c₀),
       solid — and the scales as numbers. ONE fixed scale everywhere, the
       director's rule: the colour bar and the profile's axis are both
       ±600 kPa (his call, 2026-11-21 night), whatever the sliders say (a
       curve past it is clipped).
       Flow is toward +x (to the right); tension sits upstream. -->
  <div class="lab">
    <div class="lab-controls">
      <div v-for="sl in SLIDERS" :key="sl.key" class="lab-sl">
        <DfdEq :name="sl.sym" :k="2.3" class="lab-sym" />
        <input
          type="range"
          min="0"
          max="1000"
          step="1"
          :value="toPos(sl)"
          :aria-label="sl.key"
          @input="onSlide(sl, $event)"
        />
        <span class="lab-val">{{ sl.fmt(val(sl.key)) }}</span>
      </div>
      <button class="lab-reset" @click="reset">↺ the paper’s case</button>
    </div>

    <div class="lab-body">
      <!-- the 2-D field -->
      <div class="lab-field">
        <div class="lab-fields">
          <button
            v-for="f in FIELDS"
            :key="f"
            class="lab-fpill"
            :class="{ 'lab-fpill-on': f === field }"
            :aria-label="f"
            @click="field = f"
          >
            <DfdEq :name="'fb_' + f" set="slab" :k="2.0" />
          </button>
        </div>
        <div class="lab-sq">
          <canvas ref="canvasEl" :width="N" :height="N" class="lab-canvas" />
          <svg class="lab-over" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            <circle cx="50" cy="50" :r="patchPct" class="lab-patch" vector-effect="non-scaling-stroke" />
          </svg>
          <!-- where the profile is cut: y = 0, through the patch centre (dotted like the 2-D curve) -->
          <div class="lab-cut" aria-hidden="true" />
          <span class="lab-flow">ice flow →</span>
          <div class="lab-xt"><span v-for="t in TICKS" :key="'x' + t">{{ t }}</span></div>
          <div class="lab-yt"><span v-for="t in [...TICKS].reverse()" :key="'y' + t">{{ t }}</span></div>
          <span class="lab-xlab">x [km]</span>
          <span class="lab-ylab">y [km]</span>
        </div>
        <div class="lab-cbar">
          <div class="lab-cbar-row">
            <div class="lab-cbar-bar" />
            <div class="lab-cbar-ticks"><span>{{ VLIM_KPA }} kPa</span><span>0</span><span>−{{ VLIM_KPA }}</span></div>
          </div>
        </div>
      </div>

      <!-- the centreline: 1-D against 2-D -->
      <div class="lab-prof">
        <div class="lab-plot">
          <svg :viewBox="`0 0 ${PW} ${PH}`" class="lab-svg" aria-label="The along-flow stress profile through the patch centre: the 1-D closed form against the 2-D one">
            <!-- the patch -->
            <rect :x="px(-p.R)" :y="PT" :width="px(p.R) - px(-p.R)" :height="PB - PT" class="lab-band" />
            <!-- the decay length, bracketed upstream of the patch edge -->
            <line :x1="px(-p.R - s.decayM)" :x2="px(-p.R)" :y1="PB - 14" :y2="PB - 14" class="lab-brk" />
            <line :x1="px(-p.R - s.decayM)" :x2="px(-p.R - s.decayM)" :y1="PB - 20" :y2="PB - 8" class="lab-brk" />
            <line :x1="px(-p.R)" :x2="px(-p.R)" :y1="PB - 20" :y2="PB - 8" class="lab-brk" />
            <!-- axes -->
            <line :x1="PL" :x2="PR" :y1="py(0)" :y2="py(0)" class="lab-ax0" />
            <g v-for="t in yTicks" :key="'yt' + t">
              <line :x1="PL - 6" :x2="PL" :y1="py(t)" :y2="py(t)" class="lab-ax" />
              <text :x="PL - 10" :y="py(t) + 4" text-anchor="end" class="lab-tt">{{ t }}</text>
            </g>
            <g v-for="t in TICKS" :key="'xt' + t">
              <line :x1="px(t * 1000)" :x2="px(t * 1000)" :y1="PB" :y2="PB + 6" class="lab-ax" />
              <text :x="px(t * 1000)" :y="PB + 20" text-anchor="middle" class="lab-tt">{{ t }}</text>
            </g>
            <rect :x="PL" :y="PT" :width="PR - PL" :height="PB - PT" class="lab-frame" />
            <!-- the curves, inside the frame (the axis is fixed) -->
            <clipPath id="lab-clip"><rect :x="PL" :y="PT" :width="PR - PL" :height="PB - PT" /></clipPath>
            <g clip-path="url(#lab-clip)">
              <path :d="path2d" class="lab-c2" />
              <path :d="path1d" class="lab-c1" />
            </g>
            <text :x="(PL + PR) / 2" :y="PH - 4" text-anchor="middle" class="lab-tt">x [km]</text>
            <text :x="14" :y="(PT + PB) / 2" text-anchor="middle" class="lab-tt" :transform="`rotate(-90 14 ${(PT + PB) / 2})`">kPa</text>
          </svg>
          <!-- the legend and the bracket's name, as HTML over the plot (baked LaTeX) -->
          <div class="lab-legend">
            <span class="lab-leg"><i class="lab-leg-2" /><DfdEq name="lab_2d" :k="1.9" /></span>
            <span class="lab-leg"><i class="lab-leg-1" /><DfdEq name="lab_1d" :k="1.9" /></span>
          </div>
          <span class="lab-brk-name" :style="{ left: brkLeftPct + '%' }"><DfdEq name="sym_k0inv" :k="1.8" /></span>
        </div>
        <div class="lab-read">
          <span class="lab-r"><DfdEq name="sym_tau_scale" :k="2.2" /><b>{{ fmtK(s.stressPa / 1000) }} kPa</b></span>
          <span class="lab-r"><DfdEq name="sym_k0inv" :k="2.2" /><b>{{ (s.decayM / 1000).toFixed(2) }} km</b></span>
          <span class="lab-r"><DfdEq name="sym_lambda" :k="2.2" /><b>{{ s.lambda.toFixed(2) }}</b></span>
          <span class="lab-r"><DfdEq name="sym_ssa_ratio" :k="2.2" /><b>{{ ((s.c0 * p.H) / ETA).toFixed(2) }}</b></span>
          <span class="lab-r lab-r-ratio"><span class="lab-r-k">peak 2-D / 1-D</span><b>{{ ratio.toFixed(2) }}</b></span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import DfdEq from './DfdEq.vue'
import { ETA, centreline2D, fieldGrid, oneD, slabScales, type SlabField, type SlabParams } from '../lib/slabTheory'
import { fmtPow } from '../config/dfdCollapse'

// ── the parameters ──
/** The paper's Fig. 3 case (R 2.5 km, H 1 km, α 1°, c₀ = 2·10¹⁰ Pa s m⁻¹ ⇒ γ 0.1; λ = 0.56). */
const PAPER: SlabParams = { H: 1000, alphaDeg: 1.0, gamma: 0.1, R: 2500 }
const PAPER_C0 = 2e10
const p = reactive<SlabParams>({ ...PAPER })
/** The slider's c₀ (the paper's parameter); the theory's γ = c₀H / 2η follows it and H. */
const c0 = ref(PAPER_C0)
watch([c0, () => p.H], ([c, H]) => {
  p.gamma = (c * H) / (2 * ETA)
}, { immediate: true })
function reset(): void {
  Object.assign(p, PAPER)
  c0.value = PAPER_C0
}
type SliderKey = 'H' | 'alphaDeg' | 'c0' | 'R'
function val(key: SliderKey): number {
  return key === 'c0' ? c0.value : p[key]
}
function setVal(key: SliderKey, v: number): void {
  if (key === 'c0') c0.value = v
  else p[key] = v
}

interface Slider {
  key: SliderKey
  sym: string
  min: number
  max: number
  log?: boolean
  step?: number
  fmt: (v: number) => string
}
const SLIDERS: Slider[] = [
  { key: 'H', sym: 'sym_H', min: 300, max: 3000, step: 50, fmt: (v) => `${(v / 1000).toFixed(2)} km` },
  { key: 'alphaDeg', sym: 'sym_alpha', min: 0.1, max: 1.0, step: 0.05, fmt: (v) => `${v.toFixed(2)}°` },
  { key: 'c0', sym: 'sym_c0', min: 1e9, max: 1e12, log: true, fmt: (v) => `${fmtPow(v)} Pa s m⁻¹` },
  { key: 'R', sym: 'sym_R', min: 500, max: 7500, step: 100, fmt: (v) => `${(v / 1000).toFixed(1)} km` },
]
function toPos(sl: Slider): number {
  const v = val(sl.key)
  const t = sl.log
    ? (Math.log10(v) - Math.log10(sl.min)) / (Math.log10(sl.max) - Math.log10(sl.min))
    : (v - sl.min) / (sl.max - sl.min)
  return Math.round(Math.min(1, Math.max(0, t)) * 1000)
}
function onSlide(sl: Slider, e: Event): void {
  const t = parseInt((e.target as HTMLInputElement).value, 10) / 1000
  let v = sl.log
    ? Math.pow(10, Math.log10(sl.min) + t * (Math.log10(sl.max) - Math.log10(sl.min)))
    : sl.min + t * (sl.max - sl.min)
  if (sl.step) v = Math.round(v / sl.step) * sl.step
  setVal(sl.key, v)
}

const s = computed(() => slabScales(p))

// ── the field ──
const FIELDS: SlabField[] = ['txx', 'trr', 'trt', 'ttt', 'srr', 'st1']
const field = ref<SlabField>('txx')
const N = 160
const HALF_M = 25000
const TICKS = [-25, -12.5, 0, 12.5, 25]
/** The one scale: the colour bar and the profile axis alike. */
/** The one fixed scale: colour bar and profile axis, ±600 kPa, ticks every 300 — never fitted. */
const VLIM_KPA = 600
const Y_TICK_KPA = 300
const patchPct = computed(() => (p.R / (2 * HALF_M)) * 100)

const canvasEl = ref<HTMLCanvasElement | null>(null)
let img: ImageData | null = null
let raf = 0
/** blue − · white 0 · red + (the slab rasters' ramp) */
const STOPS: [number, number, number][] = [
  [0, 0, 76],
  [0, 0, 255],
  [255, 255, 255],
  [255, 0, 0],
  [128, 0, 0],
]
function paint(): void {
  const c = canvasEl.value
  if (!c) return
  // a CPU-backed canvas: the GPU-backed one stalled its first frames for seconds
  // after a GoPro clip had played (the field beat), seen headed and headless
  const ctx = c.getContext('2d', { willReadFrequently: true })
  if (!ctx) return
  const g = fieldGrid(p, s.value, field.value, HALF_M, N)
  const lim = VLIM_KPA * 1000
  if (!img) img = ctx.createImageData(N, N)
  const d = img.data
  for (let row = 0; row < N; row++) {
    // the grid's row 0 is y = −half; the image's row 0 is the top (+y up)
    const src = (N - 1 - row) * N
    for (let col = 0; col < N; col++) {
      const v = g[src + col]
      let t = (v / lim + 1) / 2
      t = t < 0 ? 0 : t > 1 ? 1 : t
      const f = t * 4
      const i0 = Math.min(3, Math.floor(f))
      const u = f - i0
      const a = STOPS[i0]
      const b = STOPS[i0 + 1]
      const o = (row * N + col) * 4
      d[o] = a[0] + (b[0] - a[0]) * u
      d[o + 1] = a[1] + (b[1] - a[1]) * u
      d[o + 2] = a[2] + (b[2] - a[2]) * u
      d[o + 3] = 255
    }
  }
  ctx.putImageData(img, 0, 0)
}
function schedule(): void {
  if (raf) return
  raf = requestAnimationFrame(() => {
    raf = 0
    paint()
  })
}
onMounted(schedule)
watch([() => p.H, () => p.alphaDeg, () => p.gamma, () => p.R, field], schedule)

// ── the centreline ──
const PW = 760
const PH = 360
const PL = 58
const PR = PW - 16
const PT = 16
const PB = PH - 46
const NPTS = 420
const yMaxKpa = computed(() => VLIM_KPA)
function px(xm: number): number {
  return PL + ((xm + HALF_M) / (2 * HALF_M)) * (PR - PL)
}
function py(kpa: number): number {
  const half = (PB - PT) / 2
  return PT + half - (kpa / yMaxKpa.value) * half
}
const yTicks = computed(() => {
  const step = Y_TICK_KPA
  const out: number[] = []
  for (let v = -Math.floor(yMaxKpa.value / step) * step; v <= yMaxKpa.value + 1e-9; v += step) out.push(Math.round(v * 100) / 100)
  return out
})
function pathOf(f: (x: number) => number): string {
  let d = ''
  for (let i = 0; i < NPTS; i++) {
    const x = -HALF_M + (i / (NPTS - 1)) * 2 * HALF_M
    const y = f(x) / 1000
    d += `${i ? 'L' : 'M'}${px(x).toFixed(1)} ${py(y).toFixed(1)}`
  }
  return d
}
const path1d = computed(() => pathOf((x) => oneD(x, p, s.value)))
const path2d = computed(() => pathOf((x) => centreline2D(x, p, s.value)))
/** the 2-D peak over the 1-D peak (= ½ρgαR) along the centreline */
const ratio = computed(() => {
  let m = 0
  for (let i = 0; i < NPTS; i++) {
    const x = -HALF_M + (i / (NPTS - 1)) * 2 * HALF_M
    const a = Math.abs(centreline2D(x, p, s.value))
    if (a > m) m = a
  }
  return m / s.value.stressPa
})
const brkLeftPct = computed(() => ((px(-p.R - s.value.decayM / 2) / PW) * 100))

function fmtK(v: number): string {
  return v >= 100 ? v.toFixed(0) : v >= 10 ? v.toFixed(1) : v.toFixed(2)
}
</script>

<style scoped>
.lab {
  height: 100%;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 1.4vh;
  color: #f5f0e6;
}
.lab-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 0.8rem 2.4rem;
}
.lab-sl {
  display: grid;
  grid-template-columns: 2.2rem 170px auto;
  align-items: center;
  gap: 0.7rem;
}
.lab-sym { justify-self: end; }
.lab-val { font-size: 1.05rem; font-variant-numeric: tabular-nums; white-space: nowrap; min-width: 4.5rem; }
.lab-sl input[type='range'] {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  margin: 0;
  border-radius: 3px;
  background: rgba(245, 199, 94, 0.42);
  cursor: pointer;
}
.lab-sl input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #f5c75e;
  border: 1px solid rgba(0, 0, 0, 0.55);
}
.lab-sl input[type='range']::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #f5c75e;
  border: 1px solid rgba(0, 0, 0, 0.55);
}
.lab-reset {
  border: 1px solid var(--gold-dim);
  background: rgba(8, 6, 4, 0.7);
  color: var(--gold-dim);
  font: 500 0.76rem/1 'Inter', system-ui, sans-serif;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.5rem 0.9rem;
  border-radius: 999px;
  cursor: pointer;
}
.lab-reset:hover { color: var(--gold-bright); }

.lab-body {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 2.5vw;
  min-height: 0;
  align-items: start;
}
.lab-field {
  display: grid;
  grid-template-columns: auto auto;
  grid-template-rows: auto 1fr;
  column-gap: 1rem;
  row-gap: 0.6rem;
  align-items: start;
  --sq: min(42vw, calc(100vh - 37vh));
}
.lab-fields {
  grid-column: 1 / -1;
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}
.lab-fpill {
  border: 1px solid rgba(232, 185, 74, 0.4);
  background: rgba(8, 6, 4, 0.7);
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  cursor: pointer;
  opacity: 0.72;
}
.lab-fpill:hover { opacity: 1; }
.lab-fpill-on { opacity: 1; border-color: var(--gold-bright); background: rgba(232, 185, 74, 0.18); box-shadow: 0 0 12px rgba(245, 199, 94, 0.3); }
.lab-sq {
  position: relative;
  width: var(--sq);
  height: var(--sq);
  margin: 0 0 1.8rem 2.6rem;
}
.lab-canvas {
  width: 100%;
  height: 100%;
  display: block;
  image-rendering: auto;
  border: 1px solid rgba(245, 199, 94, 0.6);
  box-sizing: border-box;
}
.lab-over { position: absolute; inset: 0; width: 100%; height: 100%; }
.lab-patch { fill: none; stroke: #0a0a0a; stroke-width: 2.2; stroke-dasharray: 6 4; }
.lab-cut {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(50% - 2px);
  height: 4px;
  background: repeating-linear-gradient(90deg, #f5f0e6 0 4px, transparent 4px 13px);
  filter: drop-shadow(0 0 1.5px rgba(0, 0, 0, 0.9));
  pointer-events: none;
}
.lab-flow {
  position: absolute;
  left: 0.6rem;
  top: 0.4rem;
  font-size: 0.74rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #1c1305;
}
.lab-xt {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(100% + 0.3rem);
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  font-variant-numeric: tabular-nums;
}
.lab-yt {
  position: absolute;
  top: 0;
  bottom: 0;
  right: calc(100% + 0.4rem);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-end;
  font-size: 0.9rem;
  font-variant-numeric: tabular-nums;
}
.lab-xt span, .lab-yt span { line-height: 1; }
.lab-xlab { position: absolute; left: 50%; top: calc(100% + 1.4rem); transform: translateX(-50%); font-size: 0.9rem; }
.lab-ylab {
  position: absolute;
  top: 50%;
  right: calc(100% + 2.6rem);
  transform: translateY(-50%) rotate(-90deg);
  transform-origin: center;
  font-size: 0.9rem;
  white-space: nowrap;
}
.lab-cbar {
  align-self: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
}
.lab-cbar-bar {
  width: 14px;
  height: calc(var(--sq) * 0.6);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 3px;
  background: linear-gradient(to top, #00004c, #0000ff 25%, #ffffff 50%, #ff0000 75%, #800000);
}
.lab-cbar-row { display: flex; align-items: stretch; gap: 0.4rem; }
.lab-cbar-ticks {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-start;
  font-size: 0.88rem;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.lab-prof {
  display: flex;
  flex-direction: column;
  gap: 1.2vh;
  min-width: 0;
}
.lab-plot { position: relative; width: 100%; }
.lab-svg { width: 100%; height: auto; display: block; }
.lab-band { fill: rgba(232, 185, 74, 0.09); }
.lab-frame { fill: none; stroke: rgba(245, 240, 230, 0.55); stroke-width: 1.2; }
.lab-ax { stroke: rgba(245, 240, 230, 0.55); stroke-width: 1.2; }
.lab-ax0 { stroke: rgba(245, 240, 230, 0.28); stroke-width: 1; }
.lab-tt { font: 13px 'Inter', system-ui, sans-serif; fill: rgba(245, 240, 230, 0.85); }
.lab-c2 { fill: none; stroke: #f5f0e6; stroke-width: 4; stroke-linecap: round; stroke-dasharray: 0.01 9; }
.lab-c1 { fill: none; stroke: #f4cf6a; stroke-width: 3; stroke-linejoin: round; }
.lab-brk { stroke: #f4cf6a; stroke-width: 1.6; }
.lab-brk-name { position: absolute; bottom: 15%; transform: translateX(-50%); padding: 0 0.3rem; background: rgba(5, 5, 5, 0.75); border-radius: 4px; }
.lab-legend {
  position: absolute;
  top: 6%;
  right: 3%;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.4rem 0.7rem;
  border-radius: 8px;
  background: rgba(8, 6, 4, 0.7);
  border: 1px solid rgba(232, 185, 74, 0.25);
}
.lab-leg { display: inline-flex; align-items: center; gap: 0.5rem; }
.lab-leg i { display: inline-block; width: 1.6rem; height: 0; }
.lab-leg-2 { border-top: 4px dotted #f5f0e6; }
.lab-leg-1 { border-top: 3px solid #f4cf6a; }
.lab-read {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem 2rem;
  align-items: center;
  padding: 0.8rem 1rem;
  border: 1px solid rgba(232, 185, 74, 0.25);
  border-radius: 10px;
  background: rgba(8, 6, 4, 0.5);
}
.lab-r { display: inline-flex; align-items: baseline; gap: 0.6rem; font-size: 1.05rem; }
.lab-r b { font-weight: 600; color: #fff8e6; font-variant-numeric: tabular-nums; }
.lab-r-k { font-size: 0.78rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--gold); }
.lab-r-ratio { margin-left: auto; }
</style>
