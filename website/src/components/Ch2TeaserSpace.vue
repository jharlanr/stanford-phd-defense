<template>
  <!-- Chapter 2's teaser (`teaser/2`): the VISCOUS STRESS SPACE right of
       the two blocks (the director's design: a stress space for the
       viscous stress to the right, ticking through where each of Lake
       1938's stresses plots depending on the bed realization; all of
       them present at all times but faded except the one being looked at
       as it ticks by).
       Lake 1938 on BedMachine + the ten MGSIM beds (config/ch2Teaser.ts),
       x = σ_t1^post, y = Δσ_t1, on THE CHAPTER'S OWN FRAME — the same
       ±1000 kPa square as every other stress space (the director's
       reasoning: it is the same stress space plot, so changing the axis
       limits is confusing; keep the shared −1000…1000 frame and add a
       zoom-in box with the tighter
       axis) — so the eleven points sit as one small cluster near the
       origin with a dashed gold ZOOM BOX round them, and an INSET ABOVE
       the plot, top-right of the page (the pop-out box sits OUTSIDE the
       phase space, to the top right, where the page has room),
       shows that box at −300…−100 × 0…60 kPa.
       In both, the active bed's point is full, larger, haloed; the other
       ten stay visible at ~40 %. No ring on BedMachine (it read as a
       second halo). Its box is laid out per frame from the Globe's
       projected block (window.__simDomainScreen) and the twin's SETTLED
       offset (window.__simTwinScreen.full): left edge clear of the twin's
       right-most corner, top under the title + pips, bottom above the
       door; it fades in with the twin's slide (`t`). -->
  <div
    v-if="pts"
    class="cts"
    :style="{ left: box.x + 'px', top: box.y + 'px', width: box.w + 'px', height: box.h + 'px', opacity: box.a }"
  >
    <svg :width="box.w" :height="box.h" :viewBox="`0 0 ${box.w} ${box.h}`">
      <!-- header: model + component (as Ch2StressSpace), the key right -->
      <text :x="g.ml" :y="34" class="cts-model">Viscous</text>
      <image v-if="ins.x - (g.ml + 128) >= 56" v-bind="eqAt('t1', K_SYM, g.ml + 128, 34, 'left', 'baseline')" />
      <!-- the key sits INSIDE the frame, lower-right — that quadrant
           (σ_t1^post > 0, Δσ_t1 < 0) is empty for this lake. Just the
           lake: the title names the bed, the bed key names the lake. -->
      <g :transform="`translate(${g.ml + g.p - KEY_W} ${g.mt + g.p - 16})`" class="cts-key">
        <path :d="phaseMarkerPath(SHAPE, 0, -6, 8)" class="cts-pt" />
        <text x="16" y="0">1938</text>
      </g>

      <!-- the chapter's frame: ±1000, major grid every 500, minor at 250 -->
      <rect :x="g.ml" :y="g.mt" :width="g.p" :height="g.p" class="cts-frame" />
      <template v-for="t in grid" :key="`g${t}`">
        <line :x1="sx(t)" :x2="sx(t)" :y1="g.mt" :y2="g.mt + g.p" :class="t % CH2_AXIS_STEP === 0 ? 'cts-grid' : 'cts-grid-minor'" />
        <line :x1="g.ml" :x2="g.ml + g.p" :y1="sy(t)" :y2="sy(t)" :class="t % CH2_AXIS_STEP === 0 ? 'cts-grid' : 'cts-grid-minor'" />
      </template>
      <line :x1="sx(0)" :x2="sx(0)" :y1="g.mt" :y2="g.mt + g.p" class="cts-zero" />
      <line :x1="g.ml" :x2="g.ml + g.p" :y1="sy(0)" :y2="sy(0)" class="cts-zero" />

      <!-- x axis: edge, ticks, labels, typeset title -->
      <line :x1="g.ml" :x2="g.ml + g.p" :y1="g.mt + g.p" :y2="g.mt + g.p" class="cts-axline" />
      <template v-for="t in ticks" :key="`tx${t}`">
        <line :x1="sx(t)" :x2="sx(t)" :y1="g.mt + g.p" :y2="g.mt + g.p + 8" class="cts-tick" />
        <text :x="sx(t)" :y="g.mt + g.p + 31" text-anchor="middle" class="cts-ticklbl">{{ fmt(t) }}</text>
      </template>
      <image v-bind="eqAt('ax_post_t1', K_AX, g.ml + g.p / 2, box.h - 4, 'center', 'bottom')" />
      <!-- y axis -->
      <line :x1="g.ml" :x2="g.ml" :y1="g.mt" :y2="g.mt + g.p" class="cts-axline" />
      <template v-for="t in ticks" :key="`ty${t}`">
        <line :x1="g.ml - 8" :x2="g.ml" :y1="sy(t)" :y2="sy(t)" class="cts-tick" />
        <text :x="g.ml - 13" :y="sy(t) + 7" text-anchor="end" class="cts-ticklbl">{{ fmt(t) }}</text>
      </template>
      <g :transform="`rotate(-90 ${AXY_X} ${g.mt + g.p / 2})`">
        <image v-bind="eqAt('ax_diff_t1', K_AX, AXY_X, g.mt + g.p / 2, 'center', 'middle')" />
      </g>

      <!-- the cluster on the chapter's frame: small symbols, the dashed
           gold zoom box round the window the inset shows -->
      <rect :x="sx(ZX[0])" :y="sy(ZY[1])" :width="sx(ZX[1]) - sx(ZX[0])" :height="sy(ZY[0]) - sy(ZY[1])" class="cts-zoombox" />
      <g
        v-for="q in drawOrder"
        :key="`m${q.i}`"
        class="cts-p"
        :class="{ 'cts-on': q.i === frame }"
        :transform="`translate(${sx(q.x)} ${sy(q.y)})`"
      >
        <circle class="cts-halo" :r="S_MAIN + 3" />
        <g class="cts-sym">
          <path :d="phaseMarkerPath(SHAPE, 0, 0, S_MAIN)" class="cts-pt" />
        </g>
      </g>

      <!-- the INSET: the zoom box's window at −300…−100 × 0…60, OUTSIDE
           the plot in the band above it, flush right; two leaders rise
           from the box's top corners to the inset's bottom corners -->
      <line :x1="sx(ZX[0])" :y1="sy(ZY[1])" :x2="ins.x" :y2="ins.y + ins.q" class="cts-leader" />
      <line :x1="sx(ZX[1])" :y1="sy(ZY[1])" :x2="ins.x + ins.q" :y2="ins.y + ins.q" class="cts-leader" />
      <rect :x="ins.x" :y="ins.y" :width="ins.q" :height="ins.q" class="cts-inset" />
      <line v-for="t in zxGrid" :key="`zgx${t}`" :x1="zx(t)" :x2="zx(t)" :y1="ins.y" :y2="ins.y + ins.q" class="cts-grid" />
      <line v-for="t in zyGrid" :key="`zgy${t}`" :x1="ins.x" :x2="ins.x + ins.q" :y1="zy(t)" :y2="zy(t)" class="cts-grid" />
      <template v-for="t in zxTicks" :key="`ztx${t}`">
        <line :x1="zx(t)" :x2="zx(t)" :y1="ins.y + ins.q" :y2="ins.y + ins.q + 6" class="cts-tick" />
        <text :x="zx(t)" :y="ins.y + ins.q + 24" text-anchor="middle" class="cts-ticklbl cts-ticklbl-z">{{ fmt(t) }}</text>
      </template>
      <template v-for="t in zyTicks" :key="`zty${t}`">
        <line :x1="ins.x + ins.q" :x2="ins.x + ins.q + 6" :y1="zy(t)" :y2="zy(t)" class="cts-tick" />
        <text :x="ins.x + ins.q + 10" :y="zy(t) + 6" text-anchor="start" class="cts-ticklbl cts-ticklbl-z">{{ fmt(t) }}</text>
      </template>
      <g
        v-for="q in drawOrder"
        :key="`z${q.i}`"
        class="cts-p"
        :class="{ 'cts-on': q.i === frame }"
        :transform="`translate(${zx(q.x)} ${zy(q.y)})`"
      >
        <circle class="cts-halo" r="24" />
        <g class="cts-sym">
          <path :d="phaseMarkerPath(SHAPE, 0, 0, S0)" class="cts-pt" />
        </g>
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { PHASE_CENTER_MARKERS, phaseMarkerPath } from '../config/simLakes'
import { CH2_EQ, type Ch2EqName } from '../config/ch2Eqs'
import { ch2EqUrl } from '../config/ch2Results'
import { CH2_AXIS_KPA, CH2_AXIS_MINOR, CH2_AXIS_STEP } from '../config/ch2Results'
import {
  CH2_TEASER_SPACE_CENTER,
  CH2_TEASER_SPACE_X,
  CH2_TEASER_SPACE_Y,
  loadCh2TeaserSpace,
  type Ch2TeaserPoint,
} from '../config/ch2Teaser'

const props = defineProps<{
  /** The cycle's active frame (CH2_TEASER_FRAMES index; 0 = BedMachine). */
  frame: number
}>()

// 1938 is 1951's neighbour: 1951's triangle, open (it does not drain).
const SHAPE = PHASE_CENTER_MARKERS[CH2_TEASER_SPACE_CENTER] ?? '^'
const S0 = 10 // the inset's marker half-size (px); the active one scales 1.35×
const S_MAIN = 6 // the cluster's markers on the ±1000 frame
const K_AX = 2.75 // px per bp: the typeset axis titles
const K_SYM = 2.9 // the header's component symbol
const AXY_X = 18 // rotated y-title centre line

const pts = ref<(Ch2TeaserPoint | null)[] | null>(null)
onMounted(() => {
  loadCh2TeaserSpace().then((p) => {
    pts.value = p
  })
})
const drawOrder = computed(() => {
  const out: { i: number; x: number; y: number }[] = []
  ;(pts.value ?? []).forEach((p, i) => {
    if (p) out.push({ i, x: p.x, y: p.y })
  })
  // the active point last (on top)
  return out.sort((a, b) => (a.i === props.frame ? 1 : 0) - (b.i === props.frame ? 1 : 0) || a.i - b.i)
})

// ── Layout (screen px; the SVG is drawn 1:1) ──
const ML = 100 // the rotated y title + "−1000" ticks
const MR = 40 // half a "1000" past the plot's right edge; the inset's "60"
const KEY_W = 74 // the key row (symbol + "1938") from the frame's right edge
const INSET_F = 0.42 // the inset's side as a fraction of the plot's
const INSET_PAD = 62 // under the inset: its x tick labels + a gap to the frame
const MB = 96 // x ticks + the x title
const PMAX = 600
const box = reactive({ x: 0, y: 0, w: 0, h: 0, a: 0 })
/** The band above the plot holds the header (left) and the inset (right). */
function mtFor(p: number): number {
  return Math.round(INSET_F * p) + INSET_PAD
}
const g = computed(() => {
  const p = Math.max(10, box.w - ML - MR)
  return { ml: ML, mt: mtFor(p), p }
})

interface Screen {
  visible: boolean
  bbox?: { minX: number; minY: number; maxX: number; maxY: number }
}
let raf = 0
let frameN = 0
let headBottom = 0
let doorTop = Infinity
function tick(): void {
  raf = requestAnimationFrame(tick)
  const w = window as unknown as {
    __simDomainScreen?: Screen | null
    __simTwinScreen?: { full: number; t: number } | null
  }
  const s = w.__simDomainScreen
  const tw = w.__simTwinScreen
  if (!s || !s.visible || !s.bbox || !tw) {
    box.a = 0
    return
  }
  const W = window.innerWidth
  const H = window.innerHeight
  if (frameN++ % 20 === 0) {
    const hr = document.querySelector('.ctz-pips')?.getBoundingClientRect()
    headBottom = hr && hr.height > 0 ? hr.bottom : 0.18 * H
    const dr = document.querySelector('.sbk-row')?.getBoundingClientRect()
    doorTop = dr && dr.height > 0 ? dr.top : Infinity
  }
  const b = s.bbox
  // left: clear of the twin's SETTLED right-most corner (its slide never
  // moves the panel); right: the page's 22 px inset
  const x0 = b.maxX + tw.full + Math.max(24, 0.02 * W)
  const x1 = W - 22
  const top = headBottom + 18
  const bottom = Math.min(H - 16, doorTop - 14)
  // height = band (INSET_F·p + pad) + p + MB → p from the room available
  const p = Math.max(120, Math.min(PMAX, x1 - x0 - ML - MR, (bottom - top - INSET_PAD - MB) / (1 + INSET_F)))
  const mt = mtFor(p)
  const wpx = ML + p + MR
  const hpx = mt + p + MB
  // centred in its column; the plot square level with the block's middle
  box.x = Math.round(x0 + Math.max(0, (x1 - x0 - wpx) / 2))
  const midY = (b.minY + b.maxY) / 2
  box.y = Math.round(Math.max(top, Math.min(bottom - hpx, midY - mt - p / 2)))
  box.w = wpx
  box.h = hpx
  box.a = Math.max(0, Math.min(1, (tw.t - 0.35) / 0.65))
}
onMounted(() => {
  raf = requestAnimationFrame(tick)
})
onBeforeUnmount(() => cancelAnimationFrame(raf))

// ── Scales: the chapter's frame (±1000, ticks every 500, minor grid at
// 250 — config/ch2Results.ts), and the inset's window (config/ch2Teaser.ts) ──
const LIM = CH2_AXIS_KPA
function steps(lo: number, hi: number, st: number): number[] {
  const out: number[] = []
  for (let v = lo; v <= hi + 1e-6; v += st) out.push(Math.round(v))
  return out
}
const ticks = steps(-LIM, LIM, CH2_AXIS_STEP)
const grid = steps(-LIM, LIM, CH2_AXIS_MINOR).filter((t) => t !== 0 && Math.abs(t) < LIM)
function sx(v: number): number {
  return g.value.ml + ((v + LIM) / (2 * LIM)) * g.value.p
}
function sy(v: number): number {
  return g.value.mt + g.value.p - ((v + LIM) / (2 * LIM)) * g.value.p
}
// the zoom box (data units) and the inset square that shows it: in the
// plot's upper-right, clear of the cluster (x ≈ −200, y ≈ +30)
const ZX: [number, number] = [CH2_TEASER_SPACE_X[0], CH2_TEASER_SPACE_X[1]]
const ZY: [number, number] = [CH2_TEASER_SPACE_Y[0], CH2_TEASER_SPACE_Y[1]]
const zxTicks = steps(ZX[0], ZX[1], CH2_TEASER_SPACE_X[2])
const zyTicks = steps(ZY[0], ZY[1], CH2_TEASER_SPACE_Y[2])
const zxGrid = steps(ZX[0], ZX[1], CH2_TEASER_SPACE_X[2] / 2).filter((t) => t > ZX[0] && t < ZX[1])
const zyGrid = steps(ZY[0], ZY[1], CH2_TEASER_SPACE_Y[2] / 2).filter((t) => t > ZY[0] && t < ZY[1])
const ins = computed(() => {
  // in the band above the plot, flush to the frame's right edge (its y
  // ticks spill into MR); its x tick labels sit between it and the frame
  const q = Math.round(INSET_F * g.value.p)
  return { x: g.value.ml + g.value.p - q, y: 4, q }
})
function zx(v: number): number {
  return ins.value.x + ((v - ZX[0]) / (ZX[1] - ZX[0])) * ins.value.q
}
function zy(v: number): number {
  return ins.value.y + ins.value.q - ((v - ZY[0]) / (ZY[1] - ZY[0])) * ins.value.q
}
function fmt(t: number): string {
  return t < 0 ? `−${Math.abs(t)}` : `${t}`
}

type HA = 'left' | 'center' | 'right'
type VA = 'top' | 'middle' | 'bottom' | 'baseline'
function eqAt(name: Ch2EqName, k: number, x: number, y: number, ha: HA, va: VA) {
  const e = CH2_EQ[name]
  const w = e.w * k
  const h = e.h * k
  const x0 = ha === 'left' ? x : ha === 'center' ? x - w / 2 : x - w
  const y0 = va === 'top' ? y : va === 'middle' ? y - h / 2 : va === 'bottom' ? y - h : y - e.base * k
  return { href: ch2EqUrl(name), x: x0, y: y0, width: w, height: h }
}
</script>

<style scoped>
.cts {
  position: absolute;
  pointer-events: none;
}
.cts svg {
  display: block;
  overflow: visible;
}
.cts-model {
  font-family: 'EB Garamond', serif;
  font-size: 36px;
  fill: var(--gold, #f4cf6a);
}
.cts-frame {
  fill: rgba(255, 255, 255, 0.015);
  stroke: rgba(245, 245, 245, 0.55);
  stroke-width: 1.6px;
}
.cts-grid {
  stroke: rgba(245, 245, 245, 0.1);
  stroke-width: 1;
}
.cts-grid-minor {
  stroke: rgba(245, 245, 245, 0.04);
  stroke-width: 1;
}
.cts-zero {
  stroke: rgba(245, 245, 245, 0.5);
  stroke-width: 1.6px;
}
/* the zoom box on the chapter's frame, its inset and the two leaders */
.cts-zoombox {
  fill: rgba(245, 199, 94, 0.06);
  stroke: var(--gold, #f4cf6a);
  stroke-width: 1.8px;
  stroke-dasharray: 6 4;
}
.cts-inset {
  fill: rgba(8, 7, 6, 0.9);
  stroke: var(--gold, #f4cf6a);
  stroke-width: 1.8px;
  stroke-dasharray: 6 4;
}
.cts-leader {
  stroke: rgba(245, 199, 94, 0.55);
  stroke-width: 1.4px;
  stroke-dasharray: 4 4;
}
.cts-ticklbl-z {
  font-size: 17px;
}
.cts-axline {
  stroke: rgba(245, 245, 245, 0.75);
  stroke-width: 2px;
}
.cts-tick {
  stroke: rgba(245, 245, 245, 0.9);
  stroke-width: 2px;
}
.cts-ticklbl {
  font-family: 'Inter', system-ui, sans-serif;
  font-variant-numeric: tabular-nums;
  font-weight: 500;
  font-size: 20px;
  fill: #f5f0e6;
}
.cts-key text {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 17px;
  fill: rgba(245, 240, 230, 0.92);
}
/* 1938: the open marker of a lake that does not drain (PHASE_GROUP_STYLE.black) */
.cts-pt {
  fill: none;
  stroke: #e8e4da;
  stroke-width: 2.4px;
  stroke-linejoin: round;
}
/* the ten not being looked at: faded but present */
.cts-p {
  opacity: 0.4;
  transition: opacity 0.45s ease;
}
.cts-sym {
  transform: scale(1);
  transition: transform 0.45s ease;
}
.cts-halo {
  fill: rgba(245, 199, 94, 0.22);
  stroke: rgba(245, 199, 94, 0.7);
  stroke-width: 1.6px;
  opacity: 0;
  transition: opacity 0.45s ease;
}
/* the bed being looked at: full, larger, haloed */
.cts-on {
  opacity: 1;
}
.cts-on .cts-sym {
  transform: scale(1.35);
}
.cts-on .cts-pt {
  stroke: #ffffff;
  stroke-width: 2.6px;
}
.cts-on .cts-halo {
  opacity: 1;
}
</style>
