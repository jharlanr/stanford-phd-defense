<template>
  <!-- One stage of the forward pass, for one lake, at one point of the
       axis: a DAY of the season (weights fixed at the best-F1 epoch) or an
       EPOCH of training (data fixed). The parent double-buffers two of
       these and moves them in and out of the diagram's blocks. Everything
       drawn is baked (build_network.py, build_network_epochs.py); labels
       are the figure's own (channel names, sizes, axes, classes, values). -->
  <div class="nf" :class="`nf-${stage.kind}`">
    <!-- ── the imagery: the season's frames behind this one ── -->
    <div v-if="stage.kind === 'video' && !isStack" ref="figEl" class="nf-fig nf-video" :style="videoBoxStyle">
      <div class="nf-ghost nf-ghost-2" />
      <div class="nf-ghost nf-ghost-1" />
      <canvas
        ref="canvasEl"
        class="nf-canvas"
        :width="vs?.vw ?? 2"
        :height="vs?.vh ?? 2"
      />
      <span class="nf-stamp">{{ stampText }}</span>
    </div>

    <!-- ── the channel stages: a stack of sheets, one per channel (depth =
         channels, sheet size ∝ resolution), each carrying its real map;
         pointer over it fans the stack out into the grid of channels ── -->
    <div
      v-else-if="stage.kind === 'video'"
      ref="figEl"
      class="nf-fig nf-stackfig"
      :style="{ width: `${boxW}px`, height: `${boxH}px` }"
    >
      <canvas ref="stackEl" class="nf-stack-canvas" />
      <div
        class="nf-stack-hit"
        :style="hitStyle"
        data-stack
        @pointerenter="onStackEnter"
        @pointerleave="onStackLeave"
        @click="onStackClick"
      />
      <!-- stacked: the textbook dimensions -->
      <div class="nf-dims" :style="{ opacity: 1 - fanP }">
        <span class="nf-dim nf-dim-w" :style="dimWStyle">{{ resText }}</span>
        <span class="nf-dim nf-dim-c" :style="dimCStyle">{{ chanText }}</span>
        <span class="nf-stamp nf-stamp-abs nf-stamp-lines" :style="stampStackStyle">
          <span v-for="l in stampLines" :key="l">{{ l }}</span>
        </span>
      </div>
      <!-- fanned: each channel's name -->
      <div class="nf-badges" :style="{ opacity: Math.max(0, fanP * 1.6 - 0.6) }">
        <span
          v-for="(b, i) in badges"
          :key="i"
          class="nf-badge"
          :class="{ 'nf-badge-name': !!vs?.channels }"
          :style="{ left: `${b.x}px`, top: `${b.y}px` }"
        >{{ b.text }}</span>
        <span class="nf-stamp nf-stamp-abs" :style="stampGridStyle">{{ stampText }}</span>
      </div>
    </div>

    <!-- ── vectors: the axis as a raster (days or epochs → , units ↓) and
         the current column pulled out, big ── -->
    <div v-else-if="stage.kind === 'vec'" ref="figEl" class="nf-fig nf-vec" :style="vecBoxStyle">
      <div class="nf-raster-wrap">
        <canvas ref="rasterEl" class="nf-raster nf-pix" :width="axisLen" :height="vecRows.length" />
        <!-- DAY: the days after t have not been seen yet -->
        <div
          v-if="!epochOn"
          class="nf-unseen"
          :style="{ left: `${((tIdx + 1) / axisLen) * 100}%` }"
        />
        <div class="nf-raster-cursor" :style="{ left: `${((tIdx + 0.5) / axisLen) * 100}%` }" />
        <div
          v-for="g in vecGroups"
          :key="g.name"
          class="nf-vec-group"
          :style="{ top: `${(g.from / vecRows.length) * 100}%`, height: `${((g.to - g.from) / vecRows.length) * 100}%` }"
        >
          <span>{{ g.name }}</span>
        </div>
        <div class="nf-months" :class="{ 'nf-months-ep': epochOn }">
          <span
            v-for="m in axisTicks"
            :key="m.label"
            :class="{ 'nf-tick-best': m.best }"
            :style="{ left: `${m.x * 100}%` }"
          >{{ m.label }}</span>
        </div>
      </div>
      <div class="nf-link" />
      <div class="nf-column">
        <span
          v-for="(c, i) in columnCells"
          :key="i"
          class="nf-cell"
          :class="{ 'nf-cell-split': vecGroups.length > 1 && i === vecGroups[0].to }"
          :style="{ background: c }"
        />
      </div>
      <div class="nf-scale">
        <span class="nf-scale-stamp">{{ stampText }}</span>
        <!-- the activations are drawn in units of each stage's own scale
             (v / max|v|), so the bar is −1 … +1 whatever the stage (the
             director wanted the yellow–blue colour bar fixed at −1 to 1) -->
        <span>−1</span>
        <span class="nf-scale-bar" />
        <span>+1</span>
      </div>
    </div>

    <!-- ── p_water: the scalar stream's input (data: the same on both axes) ── -->
    <div v-else-if="stage.kind === 'curve'" ref="figEl" class="nf-fig nf-curve" :style="chartBoxStyle">
      <svg :viewBox="`0 0 ${CW} ${CH}`" class="nf-svg">
        <g class="nf-axis">
          <line :x1="CX0" :x2="CX1" :y1="CY1" :y2="CY1" />
          <line :x1="CX0" :x2="CX0" :y1="CY0" :y2="CY1" />
          <text v-for="m in months" :key="m.label" :x="CX0 + m.x * (CX1 - CX0)" :y="CY1 + 34" class="nf-tick">{{ m.label }}</text>
          <text :x="CX0 - 14" :y="CY1 + 6" class="nf-tick nf-tick-y">0</text>
          <text :x="CX0 - 14" :y="CY0 + 6" class="nf-tick nf-tick-y">1</text>
          <text :x="CX0 - 52" :y="(CY0 + CY1) / 2" class="nf-axis-name" :transform="`rotate(-90 ${CX0 - 52} ${(CY0 + CY1) / 2})`">p_water (min–max)</text>
        </g>
        <path :d="curvePath(man.p_water_input)" class="nf-curve-area" />
        <path :d="curveLine(man.p_water_input)" class="nf-curve-line" />
        <circle
          v-for="d in observedDays"
          :key="d"
          :cx="xOf(d)" :cy="yOf(man.p_water_input[d])" r="4.5"
          class="nf-obs"
        />
        <!-- DAY: the LSTM has read days 1 → t -->
        <template v-if="axis === 'day'">
          <rect :x="CX0" :y="CY0 - 10" :width="Math.max(0, xOf(day) - CX0)" :height="CY1 - CY0 + 10" class="nf-read" />
          <line :x1="xOf(day)" :x2="xOf(day)" :y1="CY0 - 10" :y2="CY1" class="nf-cursor" />
          <circle :cx="xOf(day)" :cy="yOf(man.p_water_input[day])" r="8" class="nf-cursor-dot" />
          <text :x="xOf(day)" :y="CY0 - 18" class="nf-cursor-val">{{ man.p_water_input[day].toFixed(2) }}</text>
        </template>
        <text v-else :x="CX1" :y="CY0 - 18" class="nf-end-label">1 MAY → 30 SEP</text>
      </svg>
    </div>

    <!-- ── the head's hidden layer: 48 → 64, edges = weight × input ── -->
    <div v-else-if="stage.kind === 'mlp'" ref="figEl" class="nf-fig nf-mlp" :style="chartBoxStyle">
      <canvas ref="mlpEl" class="nf-mlp-canvas" />
      <span class="nf-mlp-label nf-mlp-l">concat · 48</span>
      <span class="nf-mlp-label nf-mlp-r">hidden · 64</span>
      <span class="nf-stamp nf-mlp-stamp">{{ stampText }}</span>
    </div>

    <!-- ── the verdict ── -->
    <div v-else ref="figEl" class="nf-fig nf-verdict" :style="verdictBoxStyle">
      <div class="nf-bars" :class="{ 'nf-bars-long': classes.some((c) => c.length > 2) }">
        <div class="nf-bars-head">
          <span class="nf-lake">{{ man.lake }}</span>
          <span v-if="man.published" class="nf-split">{{ man.published.split }} split</span>
          <span class="nf-when" :class="{ 'nf-when-final': isFinal }">{{ whenText }}</span>
          <span v-if="axis === 'epoch' && f1Now !== null" class="nf-f1">
            <span class="nf-f1-k">val macro-F1</span>
            <span class="nf-f1-v">{{ f1Now.toFixed(2) }}</span>
          </span>
        </div>
        <div v-for="(c, i) in classes" :key="c" class="nf-bar-row">
          <span class="nf-bar-code" :style="{ color: colors[c] }">{{ classLabel(c) }}</span>
          <span class="nf-bar-track">
            <span class="nf-bar-fill" :style="{ width: pct(probsNow[i]), background: colors[c] }" />
            <span class="nf-bar-final" :style="{ left: pct(finalProbs[i]) }" />
          </span>
          <span class="nf-bar-val">{{ probsNow[i].toFixed(3) }}</span>
          <span class="nf-bar-flags">
            <span v-if="man.true === c" class="nf-flag nf-flag-label">labeled</span>
            <span v-if="predNow === c" class="nf-flag nf-flag-pred">predicted</span>
          </span>
        </div>
      </div>
      <!-- DAY: the probabilities through the season -->
      <svg v-if="axis === 'day'" :viewBox="`0 0 ${CW} ${SH}`" class="nf-svg nf-season" preserveAspectRatio="xMidYMid meet">
        <path
          v-for="(c, i) in classes"
          :key="c"
          :d="stackPath(i)"
          :style="{ fill: colors[c] }"
          class="nf-stack"
        />
        <path :d="seasonPw" class="nf-season-pw" />
        <rect
          v-if="day < man.days - 1"
          :x="xOf(day)" :y="SY0 - 2"
          :width="CX1 - xOf(day)" :height="SY1 - SY0 + 2"
          class="nf-unseen-svg"
        />
        <g class="nf-axis">
          <line :x1="CX0" :x2="CX1" :y1="SY1" :y2="SY1" />
          <text v-for="m in months" :key="m.label" :x="CX0 + m.x * (CX1 - CX0)" :y="SY1 + 30" class="nf-tick">{{ m.label }}</text>
          <text :x="CX0 - 14" :y="SY1 + 6" class="nf-tick nf-tick-y">0</text>
          <text :x="CX0 - 14" :y="SY0 + 6" class="nf-tick nf-tick-y">1</text>
        </g>
        <line :x1="xOf(day)" :x2="xOf(day)" :y1="SY0 - 8" :y2="SY1" class="nf-cursor" />
        <text :x="CX1" :y="SY0 - 14" class="nf-end-label">prediction ▾</text>
      </svg>
      <!-- EPOCH: the season-end probabilities through training, with the
           validation macro-F1 the checkpoint was chosen on -->
      <svg v-else :viewBox="`0 0 ${CW} ${SH}`" class="nf-svg nf-season" preserveAspectRatio="xMidYMid meet">
        <path
          v-for="(c, i) in classes"
          :key="c"
          :d="epochStackPath(i)"
          :style="{ fill: colors[c] }"
          class="nf-stack"
        />
        <!-- the epochs not trained yet (the second class-head beat plays
             how the network learns, over the epochs, which class it is —
             the history fills in behind the cursor) -->
        <rect
          v-if="epochNow < EPOCH_MAX"
          :x="xEp(epochNow)" :y="SY0 - 2"
          :width="CX1 - xEp(epochNow)" :height="SY1 - SY0 + 2"
          class="nf-unseen-svg"
        />
        <g class="nf-axis">
          <line :x1="CX0" :x2="CX1" :y1="SY1" :y2="SY1" />
          <text v-for="m in epochTicks" :key="m" :x="xEp(m)" :y="SY1 + 30" class="nf-tick">{{ m }}</text>
          <text :x="CX1" :y="SY1 + 58" class="nf-tick nf-tick-end">epoch</text>
          <text :x="CX0 - 14" :y="SY1 + 6" class="nf-tick nf-tick-y">0</text>
          <text :x="CX0 - 14" :y="SY0 + 6" class="nf-tick nf-tick-y">1</text>
        </g>
        <line v-if="epIndex" :x1="xEp(epIndex.best_epoch)" :x2="xEp(epIndex.best_epoch)" :y1="SY0 - 4" :y2="SY1" class="nf-best" />
        <text v-if="epIndex" :x="xEp(epIndex.best_epoch)" :y="SY0 - 12" class="nf-best-label">best val F1 · {{ epIndex.best_epoch }}</text>
        <line :x1="xEp(epochNow)" :x2="xEp(epochNow)" :y1="SY0 - 8" :y2="SY1" class="nf-cursor" />
      </svg>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  EPOCH_MEDIA, classLabel, dayLabel, decodeW1, diverging, rgbCss, symScale,
  type Axis, type EpochIndex, type EpochManifest, type NetIndex, type NetManifest, type StageDef,
} from '../config/essdNetwork'
import type { FramePool } from '../config/essdNetworkPool'

const props = withDefaults(defineProps<{
  stage: StageDef
  man: NetManifest
  index: NetIndex
  day: number
  pool: FramePool | null
  /** Box the figure may fill (px). */
  boxW: number
  boxH: number
  /** Stop following the axis (an outgoing figure keeps its last frame). */
  frozen?: boolean
  axis?: Axis
  /** The EPOCH axis: frame index into epMan.epochs. */
  ep?: number
  epMan?: EpochManifest | null
  epIndex?: EpochIndex | null
  epPool?: FramePool | null
  /** Where the lit block sits (box-local x): the stack stands above it. */
  stackCx?: number | null
  /** EPOCH playback: the frame coming next — its video is sought and
   *  decoded while the current one shows (the director had seen feature
   *  maps that were not rendering in time). */
  prefetch?: number | null
}>(), { frozen: false, axis: 'day', ep: 0, epMan: null, epIndex: null, epPool: null, stackCx: null, prefetch: null })

const figEl = ref<HTMLElement | null>(null)
const canvasEl = ref<HTMLCanvasElement | null>(null)
const stackEl = ref<HTMLCanvasElement | null>(null)
const rasterEl = ref<HTMLCanvasElement | null>(null)
const mlpEl = ref<HTMLCanvasElement | null>(null)

const classes = computed(() => props.index.classes)
const colors = computed(() => props.index.colors)
function pct(v: number): string {
  return `${Math.max(0, Math.min(1, v)) * 100}%`
}

// ── the axis ─────────────────────────────────────────────────────────
const epochOn = computed(() => props.axis === 'epoch' && !!props.epMan && !!props.epIndex)
/** Stages that hold the season-end state on the EPOCH axis. */
const STATE_STAGES = new Set(['clstm', 'gap', 'slstm', 'concat', 'fc', 'out'])
const epochNow = computed(() => props.epMan?.epochs[props.ep] ?? 0)
/** The stamp on the figure: the day it shows (and, on the EPOCH axis, the
 *  epoch whose weights made it). */
/** The stack's stamp sits on its front sheet: the day, then the epoch on
 *  a line of its own (a 32 × 32 sheet is narrow). */
const stampLines = computed(() => stampText.value.split(' · '))
const stampText = computed(() => {
  if (!epochOn.value) return dayLabel(props.man.t0, props.day)
  const em = props.epMan as EpochManifest
  const learned = props.stage.media ? EPOCH_MEDIA.has(props.stage.media) : props.stage.kind !== 'curve'
  const d = STATE_STAGES.has(props.stage.id) ? em.state_day : em.image_day
  const date = dayLabel(props.man.t0, d)
  return learned ? `${date} · EPOCH ${epochNow.value}` : date
})

// ── months along a 153-day May–Sep axis ─────────────────────────────
const months = computed(() => {
  const out: { label: string; x: number }[] = []
  const t0 = new Date(`${props.man.t0}T00:00:00Z`).getTime()
  const n = props.man.days
  for (let m = 0; m < 5; m++) {
    const d = new Date(t0)
    d.setUTCMonth(d.getUTCMonth() + m)
    const day = Math.round((d.getTime() - t0) / 86400e3)
    if (day < n) out.push({ label: d.toLocaleDateString('en-GB', { month: 'short', timeZone: 'UTC' }).toUpperCase(), x: day / (n - 1) })
  }
  return out
})

// ── video stages ─────────────────────────────────────────────────────
const vs = computed(() => {
  const key = props.stage.media
  if (!key) return null
  if (epochOn.value && EPOCH_MEDIA.has(key)) return props.epMan?.stages[key] ?? props.man.stages[key]
  return props.man.stages[key]
})
const isStack = computed(() => props.stage.kind === 'video' && props.stage.id !== 'input')
/** Which pool, which frame. Data stages on the EPOCH axis read the DAY
 *  videos at the fixed day. */
function videoSource(): { pool: FramePool | null; frame: number } {
  const key = props.stage.media ?? ''
  if (epochOn.value) {
    const em = props.epMan as EpochManifest
    if (EPOCH_MEDIA.has(key)) return { pool: props.epPool, frame: props.ep }
    return { pool: props.pool, frame: em.image_day }
  }
  return { pool: props.pool, frame: props.day }
}
const videoBoxStyle = computed(() => {
  const v = vs.value
  if (!v) return {}
  const s = Math.min(props.boxW / v.w, props.boxH / v.h)
  return { width: `${Math.floor(v.w * s)}px`, height: `${Math.floor(v.h * s)}px` }
})
const probeCv = document.createElement('canvas')
probeCv.width = 1
probeCv.height = 1
const probeCtx = probeCv.getContext('2d', { willReadFrequently: true }) as CanvasRenderingContext2D
// the channel stages keep the frame they show here, so a fan animation
// never draws from a video mid-seek
const srcCv = document.createElement('canvas')
let srcReady = false
let drawToken = 0
let drawnOnce = false
let firstDraw: (() => void) | null = null
const firstDrawn = new Promise<void>((res) => { firstDraw = res })
async function drawVideo(): Promise<void> {
  const my = ++drawToken
  const key = props.stage.media
  const { pool, frame } = videoSource()
  if (!key || !pool) return
  const el = await pool.frame(key, frame)
  if (my !== drawToken || !el) return
  // WebKit reports `seeked` before the frame can be drawn (drawImage
  // paints nothing); a video frame is opaque, so an empty pixel means
  // "not yet" — try again on the next frames.
  // The check runs on a 1 × 1 CPU canvas, never on the figure's own.
  let drawn = false
  for (let tries = 0; tries < 30; tries++) {
    drawn = true
    try {
      probeCtx.clearRect(0, 0, 1, 1)
      probeCtx.drawImage(el, 0, 0, 1, 1)
      drawn = probeCtx.getImageData(0, 0, 1, 1).data[3] !== 0
    } catch {
      // a tainted probe (the direct-URL fallback) cannot be read: trust it
    }
    if (drawn) break
    await new Promise((r) => requestAnimationFrame(r))
    if (my !== drawToken) return
  }
  // never paint a blank over a good frame: hold the previous one
  if (!drawn && drawnOnce) return
  drawnOnce = true
  if (isStack.value) {
    const v = vs.value
    if (!v) return
    if (srcCv.width !== v.vw || srcCv.height !== v.vh) {
      srcCv.width = v.vw
      srcCv.height = v.vh
    }
    srcCv.getContext('2d')?.drawImage(el, 0, 0, v.vw, v.vh)
    srcReady = true
    paintStack()
  } else {
    const cv = canvasEl.value
    const ctx = cv?.getContext('2d')
    if (!cv || !ctx) return
    ctx.drawImage(el, 0, 0, cv.width, cv.height)
  }
  firstDraw?.()
  // the canvas holds this frame now: let the video go and decode the next
  const nx = props.prefetch
  if (nx !== null && nx !== frame && epochOn.value && EPOCH_MEDIA.has(key) && !props.frozen) {
    void pool.frame(key, nx)
  }
}

// ── the channel stack ────────────────────────────────────────────────
interface Sheet { x: number; y: number; s: number }
const nChan = computed(() => vs.value?.shape[0] ?? 1)
const res = computed(() => vs.value?.shape[1] ?? 512)
const resText = computed(() => `${res.value} × ${res.value}`)
const chanText = computed(() => `${nChan.value} channels`)
/** Fanned: today's grid of channels, scaled into the box. */
const grid = computed(() => {
  const v = vs.value
  if (!v || !v.cols || !v.tile) return null
  const g = v.gutter ?? 0
  const s = Math.min(props.boxW / v.w, props.boxH / v.h)
  const w = v.w * s
  const h = v.h * s
  const x0 = (props.boxW - w) / 2
  const y0 = (props.boxH - h) / 2
  const cols = v.cols
  const rects: Sheet[] = []
  for (let i = 0; i < nChan.value; i++) {
    const r = Math.floor(i / cols)
    const c = i % cols
    rects.push({ x: x0 + c * (v.tile + g) * s, y: y0 + r * (v.tile + g) * s, s: v.tile * s })
  }
  return { rects, x0, y0, w, h }
})
/** Stacked: sheets offset into depth, front = channel 1. Sheet size falls
 *  with resolution, the stack's depth grows with the channel count. */
const stack = computed(() => {
  const C = nChan.value
  const W = props.boxW
  const H = props.boxH
  const sMax = Math.min(H * 0.72, W * 0.42)
  const S = sMax * Math.pow(res.value / 512, 0.36)
  const D = sMax * (0.1 + 0.105 * Math.log2(Math.max(2, C)))
  const dx = D * 0.86
  const dy = D * 0.5
  const bottomPad = 40
  const y0 = Math.max(dy + 4, H - S - bottomPad)
  const cx = props.stackCx ?? W / 2
  const x0 = Math.max(8, Math.min(W - S - dx - 8, cx - (S + dx) / 2))
  const rects: Sheet[] = []
  for (let i = 0; i < C; i++) {
    const f = C > 1 ? i / (C - 1) : 0
    rects.push({ x: x0 + f * dx, y: y0 - f * dy, s: S })
  }
  return { rects, x0, y0, S, dx, dy }
})

// fan progress 0 (stacked) → 1 (fanned)
const fanP = ref(0)
const hovering = ref(false)
const pinned = ref(false)
let fanRaf: number | null = null
function fanTo(to: number): void {
  if (fanRaf !== null) cancelAnimationFrame(fanRaf)
  const from = fanP.value
  if (from === to) return
  const ms = to > from ? 560 : 440
  const t0 = performance.now()
  const tick = (now: number) => {
    const k = Math.min(1, (now - t0) / (ms * Math.abs(to - from)))
    fanP.value = from + (to - from) * k
    paintStack()
    fanRaf = k < 1 ? requestAnimationFrame(tick) : null
  }
  fanRaf = requestAnimationFrame(tick)
}
watch([hovering, pinned], () => fanTo(hovering.value || pinned.value ? 1 : 0))
function onStackEnter(): void { hovering.value = true }
function onStackLeave(): void { hovering.value = false }
function onStackClick(): void { pinned.value = !pinned.value }

function ease(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}
/** Sheet i's progress: the front sheets peel off first. */
function sheetP(i: number): number {
  const C = nChan.value
  const k = 0.3
  const f = C > 1 ? i / (C - 1) : 0
  return ease(Math.max(0, Math.min(1, (fanP.value - k * f) / (1 - k))))
}
function sheetAt(i: number): Sheet {
  const a = stack.value.rects[i]
  const b = grid.value?.rects[i] ?? a
  const p = sheetP(i)
  return { x: a.x + (b.x - a.x) * p, y: a.y + (b.y - a.y) * p, s: a.s + (b.s - a.s) * p }
}

function paintStack(): void {
  const cv = stackEl.value
  const v = vs.value
  if (!cv || !v || !v.cols || !v.tile) return
  const dpr = Math.min(2, window.devicePixelRatio || 1)
  const W = props.boxW
  const H = props.boxH
  const pw = Math.round(W * dpr)
  const ph = Math.round(H * dpr)
  if (cv.width !== pw || cv.height !== ph) {
    cv.width = pw
    cv.height = ph
    cv.style.width = `${W}px`
    cv.style.height = `${H}px`
  }
  const ctx = cv.getContext('2d')
  if (!ctx) return
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, W, H)
  ctx.imageSmoothingEnabled = !props.stage.pixelated
  ctx.imageSmoothingQuality = 'high'
  const C = nChan.value
  const g = v.gutter ?? 0
  for (let i = C - 1; i >= 0; i--) {
    const r = sheetAt(i)
    const p = sheetP(i)
    const depth = C > 1 ? i / (C - 1) : 0
    ctx.fillStyle = '#0b0a08'
    ctx.fillRect(r.x, r.y, r.s, r.s)
    if (srcReady) {
      const sr = Math.floor(i / v.cols)
      const sc = i % v.cols
      ctx.drawImage(srcCv, sc * (v.tile + g), sr * (v.tile + g), v.tile, v.tile, r.x, r.y, r.s, r.s)
    }
    // depth: the further back, the darker (stacked only)
    const shade = (1 - p) * 0.55 * depth
    if (shade > 0.003) {
      ctx.fillStyle = `rgba(6,5,4,${shade.toFixed(3)})`
      ctx.fillRect(r.x, r.y, r.s, r.s)
    }
    // the sheet's edges: a dark seam under a hairline of light
    ctx.lineWidth = 1
    ctx.strokeStyle = 'rgba(6,5,4,0.9)'
    ctx.strokeRect(r.x - 0.5, r.y - 0.5, r.s + 1, r.s + 1)
    ctx.strokeStyle = i === 0 && p < 0.5 ? 'rgba(244,207,106,0.95)' : `rgba(245,240,230,${(0.32 - 0.18 * depth * (1 - p)).toFixed(3)})`
    ctx.lineWidth = i === 0 && p < 0.5 ? 2 : 1
    ctx.strokeRect(r.x + 0.5, r.y + 0.5, r.s - 1, r.s - 1)
  }
}

// the stack's furniture (box-local px)
const hitStyle = computed(() => {
  const st = stack.value
  let x0 = st.x0
  let y0 = st.y0 - st.dy
  let x1 = st.x0 + st.S + st.dx
  let y1 = st.y0 + st.S
  if ((hovering.value || pinned.value) && grid.value) {
    const gr = grid.value
    x0 = Math.min(x0, gr.x0)
    y0 = Math.min(y0, gr.y0)
    x1 = Math.max(x1, gr.x0 + gr.w)
    y1 = Math.max(y1, gr.y0 + gr.h)
  }
  return { left: `${x0}px`, top: `${y0}px`, width: `${x1 - x0}px`, height: `${y1 - y0}px` }
})
const dimWStyle = computed(() => {
  const st = stack.value
  return { left: `${st.x0 + st.S / 2}px`, top: `${st.y0 + st.S + 8}px` }
})
const dimCStyle = computed(() => {
  // along the stack's top edge, from the front sheet's top-right corner
  const st = stack.value
  const ang = (Math.atan2(-st.dy, st.dx) * 180) / Math.PI
  return {
    left: `${st.x0 + st.S + st.dx / 2}px`,
    top: `${st.y0 - st.dy / 2}px`,
    transform: `translate(-50%, -50%) rotate(${ang.toFixed(1)}deg) translate(0, -1.5em) translateX(-0.5em)`,
  }
})
const stampStackStyle = computed(() => {
  const st = stack.value
  return { left: `${st.x0 + st.S}px`, top: `${st.y0 + st.S}px`, transform: 'translate(calc(-100% - 0.5rem), calc(-100% - 0.45rem))' }
})
const stampGridStyle = computed(() => {
  const gr = grid.value
  if (!gr) return { display: 'none' }
  return { left: `${gr.x0 + gr.w}px`, top: `${gr.y0 + gr.h}px`, transform: 'translate(calc(-100% - 0.5rem), calc(-100% - 0.45rem))' }
})
const badges = computed(() => {
  const gr = grid.value
  if (!gr) return []
  const names = vs.value?.channels
  return gr.rects.map((r, i) => ({ x: r.x, y: r.y, text: names ? names[i] : `${i + 1}` }))
})

// ── vector stages ────────────────────────────────────────────────────
interface VecRow { series: number[][]; i: number; scale: number }
const vecs = computed(() => (epochOn.value ? (props.epMan as EpochManifest).vectors : props.man.vectors))
const axisLen = computed(() => vecs.value.gap.length)
const tIdx = computed(() => Math.max(0, Math.min(axisLen.value - 1, epochOn.value ? props.ep : props.day)))
const scales = computed(() => ({
  gap: symScale(vecs.value.gap),
  slstm: symScale(vecs.value.slstm),
  hidden: symScale(vecs.value.hidden),
}))
const vecRows = computed<VecRow[]>(() => {
  const v = vecs.value
  const rows: VecRow[] = []
  if (props.stage.vec === 'gap' || props.stage.vec === 'concat')
    for (let i = 0; i < 32; i++) rows.push({ series: v.gap, i, scale: scales.value.gap })
  if (props.stage.vec === 'slstm' || props.stage.vec === 'concat')
    for (let i = 0; i < 16; i++) rows.push({ series: v.slstm, i, scale: scales.value.slstm })
  return rows
})
const vecGroups = computed(() =>
  props.stage.vec === 'concat'
    ? [{ name: 'imagery 32', from: 0, to: 32 }, { name: 'p_water 16', from: 32, to: 48 }]
    : [],
)
const columnCells = computed(() => {
  const d = tIdx.value
  // a column outside the axis must never throw inside a render (it once
  // broke Vue's patch for the whole segment in a film; not reproduced)
  if (!vecRows.value[0]?.series[d]) console.warn('[network] index out of range', d, props.man.lake, props.stage.id)
  return vecRows.value.map((r) => rgbCss(diverging((r.series[d]?.[r.i] ?? 0) / r.scale)))
})
/** The raster's x labels: months (DAY) or epochs (EPOCH, by frame). */
const axisTicks = computed(() => {
  if (!epochOn.value) return months.value.map((m) => ({ ...m, best: false }))
  const em = props.epMan as EpochManifest
  const n = em.epochs.length
  const out: { label: string; x: number; best: boolean }[] = []
  for (const e of [100, 200, 300, 400]) {
    const i = em.epochs.indexOf(e)
    if (i >= 0) out.push({ label: `${e}`, x: (i + 0.5) / n, best: false })
  }
  out.push({ label: `${em.epochs[em.best_index]}`, x: (em.best_index + 0.5) / n, best: true })
  return out
})
const vecBoxStyle = computed(() => {
  const w = Math.min(props.boxW, 1200)
  const h = Math.min(props.boxH, 560)
  return { width: `${w}px`, height: `${h}px` }
})
function drawRaster(): void {
  const c = rasterEl.value
  if (!c) return
  const ctx = c.getContext('2d')
  if (!ctx) return
  const rows = vecRows.value
  const T = axisLen.value
  if (c.width !== T) c.width = T
  const img = ctx.createImageData(T, rows.length)
  rows.forEach((r, y) => {
    for (let t = 0; t < T; t++) {
      const [R, G, B] = diverging(r.series[t][r.i] / r.scale)
      const o = (y * T + t) * 4
      img.data[o] = R
      img.data[o + 1] = G
      img.data[o + 2] = B
      img.data[o + 3] = 255
    }
  })
  ctx.putImageData(img, 0, 0)
  firstDraw?.()
}

// ── charts (p_water, the probabilities) ──────────────────────────────
const CW = 900
const CH = 460
const CX0 = 70
const CX1 = 880
const CY0 = 40
const CY1 = 400
const chartBoxStyle = computed(() => {
  const s = Math.min(props.boxW / CW, props.boxH / CH, 1.5)
  return { width: `${Math.floor(CW * s)}px`, height: `${Math.floor(CH * s)}px` }
})
// the verdict's chart: wider, shorter
const SH = 300
const SY0 = 34
const SY1 = 262
function ySeason(v: number): number {
  return SY1 - Math.max(0, Math.min(1, v)) * (SY1 - SY0)
}
const verdictBoxStyle = computed(() => ({
  width: `${Math.floor(Math.min(props.boxW, 1100))}px`,
  height: `${Math.floor(props.boxH)}px`,
}))
const seasonPw = computed(() =>
  props.man.p_water_input.map((v, i) => `${i ? 'L' : 'M'}${xOf(i).toFixed(1)} ${ySeason(v).toFixed(1)}`).join(' '),
)
function xOf(d: number): number {
  return CX0 + (d / Math.max(1, props.man.days - 1)) * (CX1 - CX0)
}
function yOf(v: number): number {
  return CY1 - Math.max(0, Math.min(1, v)) * (CY1 - CY0)
}
function curveLine(p: number[]): string {
  return p.map((v, i) => `${i ? 'L' : 'M'}${xOf(i).toFixed(1)} ${yOf(v).toFixed(1)}`).join(' ')
}
function curvePath(p: number[]): string {
  return `${curveLine(p)} L${xOf(p.length - 1)} ${CY1} L${xOf(0)} ${CY1} Z`
}
const observedDays = computed(() => {
  const raw = props.man.p_water_raw
  if (!raw) return []
  const out: number[] = []
  raw.forEach((v, i) => { if (v !== null) out.push(i) })
  return out
})

// verdict
const probsNow = computed(() => vecs.value.probs[tIdx.value] ?? [0, 0, 0, 0, 0])
/** The tick on each bar: where the site's model lands (DAY: 30 Sep; EPOCH:
 *  the best-F1 epoch). */
const finalProbs = computed(() =>
  epochOn.value
    ? (props.epMan as EpochManifest).vectors.probs[(props.epMan as EpochManifest).best_index]
    : props.man.vectors.probs[props.man.days - 1],
)
const predNow = computed(() => {
  const p = probsNow.value
  let k = 0
  for (let i = 1; i < p.length; i++) if (p[i] > p[k]) k = i
  return classes.value[k]
})
const isFinal = computed(() => epochOn.value || props.day >= props.man.days - 1)
const whenText = computed(() => {
  if (epochOn.value) return `${dayLabel(props.man.t0, (props.epMan as EpochManifest).state_day)} · epoch ${epochNow.value}`
  const d = dayLabel(props.man.t0, props.day)
  return props.day >= props.man.days - 1 ? `${d} · season end` : `if the season ended ${d}`
})
const f1Now = computed(() => {
  const ix = props.epIndex
  if (!ix) return null
  const k = ix.curves.epoch.indexOf(epochNow.value)
  return k >= 0 ? ix.curves.val_f1[k] : null
})
function stackPath(k: number): string {
  // layer k sits on the sum of layers < k
  const P = props.man.vectors.probs
  const lo: string[] = []
  const hi: string[] = []
  for (let t = 0; t < P.length; t++) {
    let a = 0
    for (let j = 0; j < k; j++) a += P[t][j]
    const b = a + P[t][k]
    hi.push(`${t ? 'L' : 'M'}${xOf(t).toFixed(1)} ${ySeason(b).toFixed(1)}`)
    lo.push(`L${xOf(t).toFixed(1)} ${ySeason(a).toFixed(1)}`)
  }
  return `${hi.join(' ')} ${lo.reverse().join(' ')} Z`
}
// the EPOCH chart: x = epoch 0 → 400
const EPOCH_MAX = 400 // also read by the template (the unseen veil)
function xEp(e: number): number {
  return CX0 + (e / EPOCH_MAX) * (CX1 - CX0)
}
const epochTicks = [0, 100, 200, 300, 400]
function epochStackPath(k: number): string {
  const em = props.epMan
  if (!em) return ''
  const P = em.vectors.probs
  const lo: string[] = []
  const hi: string[] = []
  for (let t = 0; t < P.length; t++) {
    let a = 0
    for (let j = 0; j < k; j++) a += P[t][j]
    const b = a + P[t][k]
    const x = xEp(em.epochs[t]).toFixed(1)
    hi.push(`${t ? 'L' : 'M'}${x} ${ySeason(b).toFixed(1)}`)
    lo.push(`L${x} ${ySeason(a).toFixed(1)}`)
  }
  return `${hi.join(' ')} ${lo.reverse().join(' ')} Z`
}

// ── the MLP ──────────────────────────────────────────────────────────
const w1Cache = new Map<number, number[][]>()
function w1Now(): number[][] {
  if (!epochOn.value || !props.epIndex) return props.index.head.w1
  const k = props.ep
  let w = w1Cache.get(k)
  if (!w) {
    w = decodeW1(props.epIndex.w1[k])
    w1Cache.set(k, w)
  }
  return w
}
function drawMlp(): void {
  const c = mlpEl.value
  const box = figEl.value
  if (!c || !box) return
  const dpr = Math.min(2, window.devicePixelRatio || 1)
  const W = box.clientWidth
  const H = box.clientHeight
  c.width = Math.round(W * dpr)
  c.height = Math.round(H * dpr)
  c.style.width = `${W}px`
  c.style.height = `${H}px`
  const ctx = c.getContext('2d')
  if (!ctx) return
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, W, H)
  const v = vecs.value
  const t = tIdx.value
  const x = [...v.gap[t], ...v.slstm[t]]
  const h = v.hidden[t]
  const w1 = w1Now() // [64][48]
  const top = 44
  const bot = H - 20
  const xl = W * 0.2
  const xr = W * 0.8
  const yl = (i: number) => top + ((i + 0.5) / 48) * (bot - top)
  const yr = (j: number) => top + ((j + 0.5) / 64) * (bot - top)
  // contributions w · x; draw weakest first
  const lines: { i: number; j: number; c: number }[] = []
  let cmax = 1e-9
  for (let j = 0; j < 64; j++)
    for (let i = 0; i < 48; i++) {
      const cc = w1[j][i] * x[i]
      lines.push({ i, j, c: cc })
      cmax = Math.max(cmax, Math.abs(cc))
    }
  lines.sort((a, b) => Math.abs(a.c) - Math.abs(b.c))
  // only the connections that carry this signal: |w·x| over a quarter of
  // the strongest; opacity rises with the square
  for (const l of lines) {
    const a = Math.abs(l.c) / cmax
    if (a < 0.25) continue
    ctx.lineWidth = 0.8 + 1.6 * a
    ctx.strokeStyle = l.c > 0 ? `rgba(244,207,106,${(a * a).toFixed(3)})` : `rgba(79,182,196,${(a * a).toFixed(3)})`
    ctx.beginPath()
    ctx.moveTo(xl + 12, yl(l.i))
    ctx.lineTo(xr - 12, yr(l.j))
    ctx.stroke()
  }
  const cellH = (n: number) => Math.max(2, ((bot - top) / n) * 0.78)
  x.forEach((val, i) => {
    const s = i < 32 ? scales.value.gap : scales.value.slstm
    ctx.fillStyle = rgbCss(diverging(val / s))
    ctx.fillRect(xl - 12, yl(i) - cellH(48) / 2, 24, cellH(48))
  })
  h.forEach((val, j) => {
    ctx.fillStyle = rgbCss(diverging(Math.max(0, val / scales.value.hidden)))
    ctx.fillRect(xr - 12, yr(j) - cellH(64) / 2, 24, cellH(64))
  })
  firstDraw?.()
}

// ── drawing dispatch ─────────────────────────────────────────────────
function redraw(): void {
  if (props.stage.kind === 'video') void drawVideo()
  else if (props.stage.kind === 'vec') drawRaster()
  else if (props.stage.kind === 'mlp') drawMlp()
  else firstDraw?.()
}
watch(
  () => [props.day, props.ep],
  () => {
    if (props.frozen) return
    if (props.stage.kind === 'video') void drawVideo()
    else if (props.stage.kind === 'mlp') drawMlp()
  },
)
// a new axis or a new epoch manifest: everything redraws
watch(
  () => [props.axis, props.epMan, props.epPool],
  () => {
    if (props.frozen) return
    w1Cache.clear()
    nextTick(redraw)
  },
)
watch(
  () => [props.boxW, props.boxH, props.stackCx],
  () => nextTick(() => {
    if (props.stage.kind === 'mlp') drawMlp()
    else if (isStack.value) paintStack()
  }),
)
watch(() => props.pool, () => { if (props.stage.kind === 'video') void drawVideo() })
onMounted(() => nextTick(() => {
  if (isStack.value) paintStack()
  redraw()
}))
onBeforeUnmount(() => {
  drawToken++
  if (fanRaf !== null) cancelAnimationFrame(fanRaf)
})

/** Resolves once the figure has drawn its first frame (max `ms`). */
function ready(ms = 8000): Promise<void> {
  return Promise.race([firstDrawn, new Promise<void>((r) => setTimeout(r, ms))])
}
/** The figure's visible box (for the move into / out of a block). */
function box(): DOMRect | null {
  return figEl.value?.getBoundingClientRect() ?? null
}
defineExpose({ ready, box, el: figEl })
</script>

<style scoped>
.nf {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  pointer-events: none;
}
.nf-fig { position: relative; transform-origin: 50% 50%; }

/* ── the imagery ── */
.nf-video { display: block; }
.nf-canvas {
  position: relative;
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 8px;
  background: #000;
  box-shadow: 0 0 0 1px rgba(245, 199, 94, 0.25), 0 18px 50px rgba(0, 0, 0, 0.6);
}
.nf-pix { image-rendering: pixelated; }
.nf-ghost {
  position: absolute;
  inset: 0;
  border-radius: 8px;
  border: 1.5px solid rgba(245, 240, 230, 0.4);
  background: rgba(30, 27, 22, 0.9);
}
.nf-ghost-1 { transform: translate(14px, -14px); opacity: 0.7; }
.nf-ghost-2 { transform: translate(28px, -28px); opacity: 0.4; }
.nf-stamp {
  position: absolute;
  right: 0.7rem;
  bottom: 0.6rem;
  padding: 0.15rem 0.6rem;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.62);
  font-size: clamp(0.85rem, 1.1vw, 1.15rem);
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--gold-bright);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

/* ── the channel stack ── */
.nf-stackfig { display: block; }
.nf-stack-canvas { position: absolute; left: 0; top: 0; }
.nf-stack-hit {
  position: absolute;
  pointer-events: auto;
  cursor: zoom-in;
}
.nf-dims, .nf-badges { position: absolute; inset: 0; pointer-events: none; }
.nf-dim {
  position: absolute;
  font-size: clamp(0.85rem, 1.05vw, 1.1rem);
  letter-spacing: 0.08em;
  color: rgba(245, 240, 230, 0.78);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.nf-dim-w { transform: translateX(-50%); }
.nf-dim-c { color: var(--gold-bright); transform-origin: 50% 50%; }
.nf-stamp-abs { right: auto; bottom: auto; }
.nf-stamp-lines { display: flex; flex-direction: column; align-items: flex-end; line-height: 1.2; }
.nf-badge {
  position: absolute;
  margin: 0.25rem 0 0 0.25rem;
  padding: 0 0.32rem;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.66);
  font-size: clamp(0.8rem, 0.92vw, 0.95rem);
  line-height: 1.35;
  color: rgba(245, 240, 230, 0.9);
  font-variant-numeric: tabular-nums;
}
.nf-badge-name {
  margin: 0.6rem 0 0 0.7rem;
  padding: 0.14rem 0.6rem;
  border-radius: 999px;
  font-size: clamp(0.8rem, 1.05vw, 1.05rem);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #f5f0e6;
  white-space: nowrap;
}

/* ── vectors ── */
.nf-vec {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 48px 96px;
  grid-template-rows: minmax(0, 1fr) auto;
  column-gap: 0;
  row-gap: 0.9rem;
  padding: 0 0 0 5.5rem;
}
.nf-raster-wrap { position: relative; min-height: 0; }
.nf-raster {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 4px;
  box-shadow: 0 0 0 1px rgba(245, 199, 94, 0.22);
}
.nf-raster-cursor {
  position: absolute;
  top: -8px;
  bottom: -8px;
  width: 3px;
  margin-left: -1.5px;
  background: var(--gold-bright);
  box-shadow: 0 0 10px rgba(244, 207, 106, 0.8);
}
.nf-vec-group {
  position: absolute;
  left: -5.5rem;
  width: 5rem;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  border-right: 2px solid rgba(245, 240, 230, 0.35);
  padding-right: 0.5rem;
  font-size: clamp(0.8rem, 1vw, 1rem);
  letter-spacing: 0.06em;
  color: rgba(245, 240, 230, 0.8);
  text-align: right;
}
.nf-months {
  position: absolute;
  left: 0;
  right: 0;
  bottom: -2rem;
  height: 1.4rem;
}
.nf-months span {
  position: absolute;
  font-size: clamp(0.8rem, 1vw, 1rem);
  letter-spacing: 0.1em;
  color: rgba(245, 240, 230, 0.7);
  font-variant-numeric: tabular-nums;
}
.nf-months-ep span { transform: translateX(-50%); }
.nf-months span.nf-tick-best { color: var(--gold-bright); top: 1.3rem; }
.nf-unseen {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  background: rgba(8, 7, 6, 0.62);
  border-radius: 0 4px 4px 0;
}
.nf-link {
  align-self: center;
  height: 3px;
  background: linear-gradient(90deg, var(--gold-bright), rgba(244, 207, 106, 0.2));
}
.nf-column {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-height: 0;
}
.nf-cell {
  flex: 1 1 0;
  min-height: 2px;
  border-radius: 2px;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.25);
}
.nf-cell-split { margin-top: 8px; }
.nf-scale {
  grid-column: 1 / 4;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  justify-content: flex-end;
  font-size: 0.95rem;
  color: rgba(245, 240, 230, 0.82);
  font-variant-numeric: tabular-nums;
  margin-top: 1.4rem;
}
.nf-scale-stamp {
  margin-right: auto;
  padding-top: 1.2rem;
  font-size: clamp(0.85rem, 1.1vw, 1.15rem);
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--gold-bright);
  white-space: nowrap;
}
.nf-scale-bar {
  width: 70px;
  height: 10px;
  border-radius: 3px;
  background: linear-gradient(90deg, rgb(79, 182, 196), rgb(22, 20, 17), rgb(244, 207, 106));
}

/* ── charts ── */
.nf-svg { display: block; width: 100%; height: 100%; overflow: visible; }
.nf-axis line { stroke: rgba(245, 240, 230, 0.65); stroke-width: 2; }
.nf-tick {
  fill: rgba(245, 240, 230, 0.72);
  font-size: 19px;
  letter-spacing: 0.08em;
  text-anchor: middle;
  font-family: 'Inter', system-ui, sans-serif;
  font-variant-numeric: tabular-nums;
}
.nf-tick-y { text-anchor: end; letter-spacing: 0; }
.nf-tick-end { text-anchor: end; font-size: 16px; }
.nf-axis-name {
  fill: rgba(245, 240, 230, 0.72);
  font-size: 19px;
  text-anchor: middle;
  font-family: 'Inter', system-ui, sans-serif;
}
.nf-curve-area { fill: rgba(127, 208, 255, 0.12); }
.nf-curve-line { fill: none; stroke: #7fd0ff; stroke-width: 3; stroke-linejoin: round; }
.nf-read { fill: rgba(244, 207, 106, 0.07); }
.nf-obs { fill: #0d0b09; stroke: #7fd0ff; stroke-width: 2; }
.nf-cursor { stroke: var(--gold-bright); stroke-width: 2.5; }
.nf-cursor-dot { fill: var(--gold-bright); }
.nf-cursor-val {
  fill: var(--gold-bright);
  font-size: 22px;
  font-weight: 600;
  text-anchor: middle;
  font-family: 'Inter', system-ui, sans-serif;
  font-variant-numeric: tabular-nums;
}

/* ── MLP ── */
.nf-mlp-canvas { position: absolute; inset: 0; }
.nf-mlp-label {
  position: absolute;
  top: 0;
  font-size: clamp(0.9rem, 1.15vw, 1.2rem);
  letter-spacing: 0.06em;
  color: rgba(245, 240, 230, 0.85);
  transform: translateX(-50%);
  white-space: nowrap;
}
.nf-mlp-l { left: 20%; }
.nf-mlp-r { left: 80%; }
.nf-mlp-stamp { right: 0; bottom: -0.4rem; }

/* ── verdict ── */
.nf-verdict {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 1.6rem;
}
.nf-bars { display: flex; flex-direction: column; gap: 0.6rem; }
.nf-bars-head { display: flex; align-items: baseline; gap: 0.9rem; margin-bottom: 0.2rem; flex-wrap: wrap; }
.nf-lake {
  font-family: 'EB Garamond', serif;
  font-size: clamp(1.2rem, 1.7vw, 1.7rem);
  color: #f5f0e6;
}
.nf-split {
  padding: 0.1rem 0.55rem;
  border-radius: 999px;
  border: 1.5px solid rgba(245, 240, 230, 0.55);
  font-size: 0.9rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(245, 240, 230, 0.8);
}
.nf-when {
  font-size: clamp(0.85rem, 1.05vw, 1.1rem);
  letter-spacing: 0.06em;
  color: rgba(245, 240, 230, 0.72);
  font-variant-numeric: tabular-nums;
}
.nf-when-final { color: var(--gold-bright); }
.nf-f1 { margin-left: auto; display: inline-flex; align-items: baseline; gap: 0.5rem; }
.nf-f1-k {
  font-size: 0.9rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(245, 240, 230, 0.7);
}
.nf-f1-v {
  font-family: 'EB Garamond', serif;
  font-size: clamp(1.4rem, 2vw, 2rem);
  color: var(--gold-bright);
  font-variant-numeric: tabular-nums;
}
.nf-bar-row {
  display: grid;
  grid-template-columns: 3rem minmax(0, 1fr) 4.2rem 12rem;
  align-items: center;
  gap: 0.8rem;
}
/* HF+MD (the four-class TAXONOMY) needs a wider code column */
.nf-bars-long .nf-bar-row { grid-template-columns: 4.8rem minmax(0, 1fr) 4.2rem 12rem; }
.nf-bar-code { font-weight: 700; font-size: clamp(1rem, 1.3vw, 1.3rem); letter-spacing: 0.05em; }
.nf-bar-track {
  position: relative;
  height: 18px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.07);
}
.nf-bar-fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  border-radius: 999px;
}
.nf-bar-final {
  position: absolute;
  top: -5px;
  bottom: -5px;
  width: 2px;
  margin-left: -1px;
  background: #f5f0e6;
  opacity: 0.85;
}
.nf-bar-val {
  font-size: clamp(0.95rem, 1.2vw, 1.2rem);
  color: #f5f0e6;
  font-variant-numeric: tabular-nums;
  text-align: right;
}
.nf-bar-flags { display: flex; gap: 0.4rem; }
.nf-flag {
  padding: 0.08rem 0.5rem;
  border-radius: 999px;
  font-size: 0.86rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.nf-flag-label { border: 1.5px solid rgba(245, 240, 230, 0.55); color: #f5f0e6; }
.nf-flag-pred { background: var(--gold-bright); color: #14110b; font-weight: 700; }
.nf-season { min-height: 0; }
.nf-unseen-svg { fill: rgba(8, 7, 6, 0.6); }
.nf-stack { opacity: 0.85; stroke: #0d0b09; stroke-width: 0.6; }
.nf-season-pw { fill: none; stroke: rgba(255, 255, 255, 0.85); stroke-width: 2.2; stroke-dasharray: 6 5; }
.nf-best { stroke: var(--gold-bright); stroke-width: 1.6; stroke-dasharray: 4 4; }
.nf-best-label {
  fill: var(--gold-bright);
  font-size: 16px;
  text-anchor: middle;
  letter-spacing: 0.06em;
  font-family: 'Inter', system-ui, sans-serif;
}
.nf-end-label {
  fill: rgba(245, 240, 230, 0.8);
  font-size: 18px;
  text-anchor: end;
  letter-spacing: 0.06em;
  font-family: 'Inter', system-ui, sans-serif;
}
</style>
