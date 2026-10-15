<template>
  <!-- The ESSD revision's baseline classifier as a road map: a slightly
       more detailed version of the paper's Fig. 7 (essd-2026-406 v3).
       Both streams, every block named, tensor shapes on the connections,
       the recurrence drawn as loops over the season, the two streams
       merging into the head, the five classes in their colours. Every
       block is a clickable node (`data-node` = the stage id). The data
       glyphs (thumbnail, p_water sparkline, the vectors' cells, the class
       bars) are the current lake at the current day.

       Units: viewBox 1600 × 370. The parent sizes the element to that
       aspect exactly, so 1 unit = width / 1600 px. -->
  <svg
    class="nd"
    :class="[`nd-${mode}`]"
    viewBox="0 0 1600 370"
    preserveAspectRatio="xMidYMid meet"
  >
    <defs>
      <marker id="nd-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
        <path d="M0,0 L10,5 L0,10 z" class="nd-arrowhead" />
      </marker>
      <marker id="nd-arrow-lit" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
        <path d="M0,0 L10,5 L0,10 z" class="nd-arrowhead-lit" />
      </marker>
      <clipPath id="nd-thumb-clip"><rect x="30" y="80" width="84" height="84" rx="4" /></clipPath>
    </defs>

    <!-- group furniture -->
    <g class="nd-furniture">
      <path d="M328 214 L328 220 L731 220 L731 214" class="nd-bracket" />
      <text x="512" y="243" class="nd-group">FrontCNN · conv 3×3 · GroupNorm · LeakyReLU · max-pool</text>
      <!-- the per-frame chain sees ONE day (the day on the axis, or the
           fixed day when the axis is the epoch) -->
      <g v-if="frameTag" class="nd-frametag" :class="{ 'nd-frametag-lit': frameLit }">
        <path d="M30 34 L30 28 L731 28 L731 34" class="nd-bracket" />
        <text x="380" y="20" class="nd-frametag-text">{{ frameTag }}</text>
      </g>
      <rect x="1188" y="84" width="404" height="281" rx="14" class="nd-groupbox" />
      <text x="1390" y="74" class="nd-group">classification head</text>
    </g>

    <!-- edges (drawn first, under the blocks) -->
    <g class="nd-edges">
      <path
        v-for="e in EDGES"
        :key="e.id"
        :ref="(el) => setEdgeEl(e.id, el)"
        :d="e.d"
        class="nd-edge"
        :class="edgeClass(e)"
        :marker-end="e.arrow === false ? undefined : (edgeClass(e) === 'nd-e-lit' ? 'url(#nd-arrow-lit)' : 'url(#nd-arrow)')"
      />
      <!-- the head's fan: concat → hidden 64 → logits -->
      <g class="nd-fan" :class="fanClass('fc')">
        <line v-for="(l, i) in FAN1" :key="`f1${i}`" :x1="1222" :y1="l[0]" :x2="1316" :y2="l[1]" />
      </g>
      <g class="nd-fan" :class="fanClass('out')">
        <line v-for="(l, i) in FAN2" :key="`f2${i}`" :x1="1332" :y1="l[0]" :x2="1393" :y2="l[1]" />
      </g>
      <!-- a shape label is its source block's output: clicking it opens
           that block -->
      <text
        v-for="e in EDGES.filter((x) => x.label)"
        :key="`l${e.id}`"
        :x="e.lx" :y="e.ly"
        class="nd-shape"
        :class="edgeClass(e)"
        :data-shape="e.from"
        @click="pick(e.from)"
      >{{ e.label }}</text>
    </g>

    <!-- ── nodes ── -->
    <!-- input: the season as a stack of frames, this lake on top -->
    <g class="nd-node" :class="nodeClass('input')" data-node="input" @click="pick('input')">
      <rect x="18" y="52" width="124" height="186" class="nd-hit" />
      <rect x="46" y="64" width="84" height="84" rx="4" class="nd-frame nd-frame-back" />
      <rect x="38" y="72" width="84" height="84" rx="4" class="nd-frame nd-frame-back" />
      <rect x="30" y="80" width="84" height="84" rx="4" class="nd-frame" />
      <image
        v-if="thumb"
        :href="thumb"
        x="30" y="80" width="84" height="84"
        preserveAspectRatio="xMidYMid slice"
        clip-path="url(#nd-thumb-clip)"
      />
      <rect x="30" y="80" width="84" height="84" rx="4" class="nd-frame-line" />
      <text x="78" y="202" class="nd-name">Sentinel-2</text>
      <text x="78" y="226" class="nd-sub">153 days</text>
    </g>

    <!-- the five input channels as five thin sheets -->
    <g class="nd-node" :class="nodeClass('chan')" data-node="chan" @click="pick('chan')">
      <rect x="162" y="44" width="90" height="190" class="nd-hit" />
      <g v-for="(c, i) in CHAN_COLORS" :key="i">
        <polygon :points="slabTop(172 + 12 * i, 7, 110, 12)" :style="{ fill: c, opacity: 0.55 }" />
        <polygon :points="slabSide(172 + 12 * i, 7, 110, 12)" :style="{ fill: c, opacity: 0.35 }" />
        <rect :x="172 + 12 * i" y="67" width="7" height="110" :style="{ fill: c }" class="nd-sheet" />
      </g>
      <text x="219" y="202" class="nd-name">5 channels</text>
    </g>

    <!-- FrontCNN's four blocks: height ∝ resolution, depth ∝ channels -->
    <g
      v-for="b in CONV"
      :key="b.id"
      class="nd-node"
      :class="nodeClass(b.id)"
      :data-node="b.id"
      @click="pick(b.id)"
    >
      <rect :x="b.x - 10" y="36" :width="b.w + b.k + 20" height="176" class="nd-hit" />
      <polygon :points="slabTop(b.x, b.w, b.h, b.k)" class="nd-prism-top" />
      <polygon :points="slabSide(b.x, b.w, b.h, b.k)" class="nd-prism-side" />
      <rect :x="b.x" :y="122 - b.h / 2" :width="b.w" :height="b.h" class="nd-prism" />
      <text :x="b.x + (b.w + b.k) / 2" y="202" class="nd-name">{{ b.name }}</text>
    </g>

    <!-- ConvLSTM, with its loop over the season -->
    <g class="nd-node" :class="nodeClass('clstm')" data-node="clstm" @click="pick('clstm')">
      <rect x="808" y="30" width="156" height="154" class="nd-hit" />
      <path d="M930 92 C 932 50, 840 50, 842 90" class="nd-loop" :class="{ 'nd-loop-base': loopFrac !== null }" marker-end="url(#nd-arrow)" />
      <path
        v-if="loopFrac !== null"
        d="M930 92 C 932 50, 840 50, 842 90"
        pathLength="1"
        class="nd-loop-fill"
        :style="{ strokeDasharray: `${loopFrac} 1` }"
      />
      <text x="886" y="44" class="nd-loop-label" :class="{ 'nd-loop-acc': loopFrac !== null }">{{ loopText }}</text>
      <rect x="816" y="92" width="140" height="60" rx="10" class="nd-block" />
      <text x="886" y="130" class="nd-name nd-in">ConvLSTM</text>
      <text x="886" y="176" class="nd-sub">hidden 32 · 3×3</text>
    </g>

    <!-- global average pool → the 32-vector -->
    <g class="nd-node" :class="nodeClass('gap')" data-node="gap" @click="pick('gap')">
      <rect x="1022" y="48" width="118" height="164" class="nd-hit" />
      <polygon points="1030,94 1072,110 1072,134 1030,150" class="nd-block" />
      <text x="1051" y="202" class="nd-name">GAP</text>
      <rect
        v-for="(c, i) in vecCells(vGap, gapScale, 32, 55, 4.2)"
        :key="`g${i}`"
        x="1118" :y="c.y" width="14" height="3.6"
        :style="{ fill: c.fill }"
      />
    </g>

    <!-- scalar stream: p_water → LSTM → the 16-vector -->
    <g class="nd-node" :class="nodeClass('pwater')" data-node="pwater" @click="pick('pwater')">
      <rect x="22" y="254" width="226" height="104" class="nd-hit" />
      <rect x="30" y="262" width="210" height="60" rx="8" class="nd-block" />
      <path v-if="spark" :d="spark" class="nd-spark" />
      <line v-if="pwater" :x1="sparkX(day)" :x2="sparkX(day)" y1="266" y2="318" class="nd-cursor" />
      <text x="135" y="346" class="nd-name">p_water</text>
    </g>

    <g class="nd-node" :class="nodeClass('slstm')" data-node="slstm" @click="pick('slstm')">
      <rect x="808" y="222" width="156" height="132" class="nd-hit" />
      <path d="M930 262 C 932 226, 840 226, 842 260" class="nd-loop" :class="{ 'nd-loop-base': loopFrac !== null }" marker-end="url(#nd-arrow)" />
      <path
        v-if="loopFrac !== null"
        d="M930 262 C 932 226, 840 226, 842 260"
        pathLength="1"
        class="nd-loop-fill"
        :style="{ strokeDasharray: `${loopFrac} 1` }"
      />
      <text x="886" y="216" class="nd-loop-label" :class="{ 'nd-loop-acc': loopFrac !== null }">{{ loopText }}</text>
      <rect x="816" y="262" width="140" height="60" rx="10" class="nd-block" />
      <text x="886" y="300" class="nd-name nd-in">LSTM</text>
      <text x="886" y="346" class="nd-sub">hidden 16</text>
      <rect
        v-for="(c, i) in vecCells(vSlstm, slstmScale, 16, 258, 4.2)"
        :key="`s${i}`"
        x="1118" :y="c.y" width="14" height="3.6"
        :style="{ fill: c.fill }"
      />
    </g>

    <!-- the head -->
    <g class="nd-node" :class="nodeClass('concat')" data-node="concat" @click="pick('concat')">
      <rect x="1196" y="96" width="34" height="250" class="nd-hit" />
      <rect
        v-for="(c, i) in concatCells"
        :key="`c${i}`"
        x="1206" :y="c.y" width="14" height="3.6"
        :style="{ fill: c.fill }"
      />
      <text x="1210" y="334" class="nd-name nd-head">concat</text>
    </g>

    <g class="nd-node" :class="nodeClass('fc')" data-node="fc" @click="pick('fc')">
      <rect x="1236" y="96" width="112" height="266" class="nd-hit" />
      <rect
        v-for="(c, i) in hiddenCells"
        :key="`h${i}`"
        x="1318" :y="c.y" width="14" height="2.7"
        :style="{ fill: c.fill }"
      />
      <text x="1332" y="334" class="nd-name nd-head">hidden 64</text>
      <text x="1332" y="357" class="nd-sub">ReLU · dropout 0.3</text>
    </g>

    <g class="nd-node" :class="nodeClass('out')" data-node="out" @click="pick('out')">
      <rect x="1384" y="112" width="206" height="250" class="nd-hit" />
      <g v-for="(c, i) in classes" :key="c">
        <circle cx="1400" :cy="OUT_Y[i]" r="5.5" class="nd-logit" :style="{ stroke: colors[c] }" />
        <line x1="1407" :y1="OUT_Y[i]" x2="1426" :y2="OUT_Y[i]" class="nd-edge nd-edge-short" />
        <rect x="1430" :y="OUT_Y[i] - 14" width="150" height="28" rx="14" class="nd-pill" :style="{ stroke: colors[c], fill: tint(colors[c]) }" />
        <rect
          v-if="probs"
          x="1430" :y="OUT_Y[i] - 14" :width="Math.max(0, Math.min(1, probs[i])) * 150" height="28" rx="14"
          class="nd-pill-fill"
          :style="{ fill: colors[c] }"
        />
        <text x="1446" :y="OUT_Y[i] + 7" class="nd-pill-code" :class="{ 'nd-pill-code-long': c.length > 2 }" :style="{ fill: probs ? '#f5f0e6' : colors[c] }">{{ classLabel(c) }}</text>
        <text v-if="probs" x="1568" :y="OUT_Y[i] + 6" class="nd-pill-p">{{ probs[i].toFixed(2) }}</text>
      </g>
      <text x="1484" y="355" class="nd-name">softmax</text>
    </g>

    <!-- the data pulse: rides the incoming edge(s) of the block just reached -->
    <circle
      v-for="(p, i) in pulses"
      :key="`p${i}`"
      :cx="p.x" :cy="p.y" r="5"
      class="nd-pulse"
      :style="{ opacity: p.o }"
    />
  </svg>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { STAGE_INDEX, classLabel, diverging, rgbCss, type StageId } from '../config/essdNetwork'

const props = withDefaults(defineProps<{
  mode: 'hero' | 'dock'
  /** The lit block; null = none (the diagram alone). */
  current: StageId | null
  thumb: string | null
  /** The network's p_water input for this lake (min–max, [0, 1]). */
  pwater: number[] | null
  day: number
  /** The current day's vectors, and their season-wide symmetric scales. */
  vGap: number[] | null
  vSlstm: number[] | null
  vHidden: number[] | null
  gapScale: number
  slstmScale: number
  hiddenScale: number
  /** Class probabilities to draw in the class pills (the verdict), or null. */
  probs: number[] | null
  /** The per-frame chain's tag ("day 32" / the fixed day), or null. */
  frameTag?: string | null
  /** The recurrent loops: the fraction of the season accumulated (DAY
   *  axis), or null = the whole season, not accumulating (EPOCH axis). */
  loopFrac?: number | null
  loopText?: string
  classes: string[]
  colors: Record<string, string>
}>(), { frameTag: null, loopFrac: null, loopText: '× 153 days' })
const emit = defineEmits<{ select: [id: StageId] }>()

// ── geometry (viewBox units) ─────────────────────────────────────────
const CHAN_COLORS = ['#ff6b5e', '#6be07a', '#6fa0ff', '#d9d3c6', '#f5f0e6']
const CONV = [
  { id: 'conv1' as StageId, name: 'conv 1', x: 328, w: 12, h: 120, k: 16 },
  { id: 'conv2' as StageId, name: 'conv 2', x: 442, w: 18, h: 92, k: 15 },
  { id: 'conv3' as StageId, name: 'conv 3', x: 560, w: 26, h: 66, k: 13 },
  { id: 'conv4' as StageId, name: 'conv 4', x: 684, w: 36, h: 46, k: 11 },
]
// one row per class, centred on the head (five: 142…282; the four-class
// TAXONOMY sits in the middle four slots' span)
const OUT_Y = computed(() => props.classes.map((_, i) => 212 + (i - (props.classes.length - 1) / 2) * 35))

interface Edge {
  id: string
  /** The tensor on an edge is its SOURCE block's output: the edge (and its
   *  shape label) lights with the block that produced it — the lit block's
   *  label is the shape of the thing on screen. */
  from: StageId
  /** The block the data pulse rides into. */
  to: StageId
  d: string
  label?: string
  lx?: number
  ly?: number
  arrow?: boolean
}
const EDGES: Edge[] = [
  { id: 'in-chan', from: 'input', to: 'chan', d: 'M144 122 L164 122' },
  { id: 'chan-c1', from: 'chan', to: 'conv1', d: 'M252 122 L324 122', label: '5 × 512²', lx: 289, ly: 111 },
  { id: 'c1-c2', from: 'conv1', to: 'conv2', d: 'M358 122 L438 122', label: '8 × 256²', lx: 399, ly: 111 },
  { id: 'c2-c3', from: 'conv2', to: 'conv3', d: 'M477 122 L556 122', label: '16 × 128²', lx: 517, ly: 111 },
  { id: 'c3-c4', from: 'conv3', to: 'conv4', d: 'M601 122 L680 122', label: '32 × 64²', lx: 641, ly: 111 },
  { id: 'c4-lstm', from: 'conv4', to: 'clstm', d: 'M733 122 L812 122', label: '64 × 32²', lx: 773, ly: 111 },
  { id: 'lstm-gap', from: 'clstm', to: 'gap', d: 'M956 122 L1026 122', label: '32 × 32²', lx: 996, ly: 86 },
  { id: 'gap-vec', from: 'gap', to: 'gap', d: 'M1072 122 L1114 122', label: '32', lx: 1093, ly: 111 },
  { id: 'pw-lstm', from: 'pwater', to: 'slstm', d: 'M242 292 L812 292', label: '153 × 1', lx: 527, ly: 281 },
  { id: 'lstm-vec', from: 'slstm', to: 'slstm', d: 'M956 292 L1114 292', label: '16', lx: 1035, ly: 281 },
  { id: 'v32-cat', from: 'gap', to: 'concat', d: 'M1134 122 C 1172 122, 1166 173, 1202 173' },
  { id: 'v16-cat', from: 'slstm', to: 'concat', d: 'M1134 292 C 1172 292, 1166 274, 1202 274' },
]
// The head's fans: a few representative connections, not all 3,392.
const FAN1: [number, number][] = [
  [110, 106], [140, 150], [170, 128], [196, 196], [220, 172], [236, 240],
  [260, 214], [284, 262], [300, 306], [126, 236], [250, 130], [180, 290],
]
const FAN2 = computed(() => {
  const out: [number, number][] = []
  for (const y1 of [110, 160, 210, 260, 305]) for (const y2 of OUT_Y.value) out.push([y1, y2])
  return out
})

function slabTop(x: number, w: number, h: number, k: number): string {
  const top = 122 - h / 2
  return `${x},${top} ${x + k},${top - k} ${x + w + k},${top - k} ${x + w},${top}`
}
function slabSide(x: number, w: number, h: number, k: number): string {
  const top = 122 - h / 2
  const bot = 122 + h / 2
  return `${x + w},${top} ${x + w + k},${top - k} ${x + w + k},${bot - k} ${x + w},${bot}`
}

// The core box of each block (what a figure grows out of / shrinks into).
const CORE: Record<StageId, [number, number, number, number]> = {
  input: [30, 64, 100, 100],
  chan: [172, 55, 67, 122],
  conv1: [328, 46, 28, 136],
  conv2: [442, 61, 33, 107],
  conv3: [560, 76, 39, 79],
  conv4: [684, 88, 47, 57],
  clstm: [816, 92, 140, 60],
  gap: [1030, 55, 102, 134],
  pwater: [30, 262, 210, 60],
  slstm: [816, 262, 140, 60],
  concat: [1206, 106, 14, 202],
  fc: [1318, 104, 14, 205],
  out: [1430, 128, 150, 168],
}
function coreBox(id: StageId): { x: number; y: number; w: number; h: number } {
  const [x, y, w, h] = CORE[id]
  return { x, y, w, h }
}

// ── state classes ────────────────────────────────────────────────────
const curIdx = computed(() => (props.current ? STAGE_INDEX[props.current] : -1))
function nodeClass(id: StageId): string {
  if (props.mode === 'hero' || !props.current) return 'nd-n-open'
  const i = STAGE_INDEX[id]
  if (i === curIdx.value) return 'nd-n-lit'
  return i < curIdx.value ? 'nd-n-warm' : 'nd-n-dim'
}
function edgeClass(e: Edge): string {
  if (props.mode === 'hero' || !props.current) return 'nd-e-open'
  const i = STAGE_INDEX[e.from]
  if (i === curIdx.value) return 'nd-e-lit'
  return i < curIdx.value ? 'nd-e-warm' : 'nd-e-dim'
}
/** The head's fans ARE their layer's weights: they light with that layer. */
function fanClass(id: StageId): string {
  if (props.mode === 'hero' || !props.current) return 'nd-e-open'
  const i = STAGE_INDEX[id]
  if (i === curIdx.value) return 'nd-e-lit'
  return i < curIdx.value ? 'nd-e-warm' : 'nd-e-dim'
}
// the per-frame tag is lit while a per-frame stage is on screen
const frameLit = computed(() => {
  const id = props.current
  return props.mode === 'dock' && !!id && ['input', 'chan', 'conv1', 'conv2', 'conv3', 'conv4'].includes(id)
})
function pick(id: StageId): void {
  emit('select', id)
}
function tint(hex: string): string {
  return `${hex}26`
}

// ── data glyphs ──────────────────────────────────────────────────────
function vecCells(v: number[] | null, scale: number, n: number, y0: number, step: number) {
  const out: { y: number; fill: string }[] = []
  for (let i = 0; i < n; i++) {
    const x = v ? v[i] / (scale || 1) : 0
    out.push({ y: y0 + i * step, fill: v ? rgbCss(diverging(x)) : 'rgba(245,240,230,0.25)' })
  }
  return out
}
const concatCells = computed(() => [
  ...vecCells(props.vGap, props.gapScale, 32, 106, 4.2),
  ...vecCells(props.vSlstm, props.slstmScale, 16, 106 + 32 * 4.2 + 2, 4.2),
])
const hiddenCells = computed(() => {
  const out: { y: number; fill: string }[] = []
  for (let i = 0; i < 64; i++) {
    const v = props.vHidden ? props.vHidden[i] / (props.hiddenScale || 1) : 0
    out.push({
      y: 104 + i * 3.2,
      fill: props.vHidden ? rgbCss(diverging(Math.max(0, v))) : 'rgba(245,240,230,0.25)',
    })
  }
  return out
})
function sparkX(d: number): number {
  const n = props.pwater?.length ?? 153
  return 38 + (d / Math.max(1, n - 1)) * 194
}
const spark = computed(() => {
  const p = props.pwater
  if (!p) return ''
  return p
    .map((v, i) => `${i ? 'L' : 'M'}${sparkX(i).toFixed(1)} ${(316 - Math.max(0, Math.min(1, v)) * 48).toFixed(1)}`)
    .join(' ')
})

// ── the pulse ────────────────────────────────────────────────────────
const edgeEls = new Map<string, SVGPathElement>()
function setEdgeEl(id: string, el: unknown): void {
  if (el) edgeEls.set(id, el as SVGPathElement)
  else edgeEls.delete(id)
}
const pulses = ref<{ x: number; y: number; o: number }[]>([])
let pulseRaf: number | null = null
/** Send a dot along every edge into `id` (ms long). */
function pulse(id: StageId, ms = 650): void {
  if (pulseRaf !== null) cancelAnimationFrame(pulseRaf)
  const paths = EDGES.filter((e) => e.to === id)
    .map((e) => edgeEls.get(e.id))
    .filter((p): p is SVGPathElement => !!p)
  if (!paths.length) {
    pulses.value = []
    return
  }
  const lens = paths.map((p) => p.getTotalLength())
  const t0 = performance.now()
  const tick = (now: number) => {
    const t = Math.min(1, (now - t0) / ms)
    const e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2
    pulses.value = paths.map((p, i) => {
      const pt = p.getPointAtLength(e * lens[i])
      return { x: pt.x, y: pt.y, o: t < 0.85 ? 1 : (1 - t) / 0.15 }
    })
    pulseRaf = t < 1 ? requestAnimationFrame(tick) : null
    if (t >= 1) pulses.value = []
  }
  pulseRaf = requestAnimationFrame(tick)
}
onBeforeUnmount(() => {
  if (pulseRaf !== null) cancelAnimationFrame(pulseRaf)
})

defineExpose({ coreBox, pulse })
</script>

<style scoped>
.nd {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
  font-family: 'Inter', system-ui, sans-serif;
  user-select: none;
}

/* The director's legibility rule: the back row of a 50-seat room
   reads this off a projector — every stroke ≥ ~1.5 px and every label
   ≥ ~15 px at 1440 × 900 in the DOCK (1 unit = 0.75 px there), greys
   no fainter than ~0.75. Same map, same places. */
/* ── furniture ── */
.nd-bracket { fill: none; stroke: rgba(245, 240, 230, 0.55); stroke-width: 2.2; }
.nd-group {
  fill: rgba(245, 240, 230, 0.8);
  font-size: 19px;
  letter-spacing: 0.01em;
  text-anchor: middle;
  text-transform: uppercase;
}
.nd-groupbox { fill: none; stroke: rgba(245, 240, 230, 0.4); stroke-width: 2.2; stroke-dasharray: 7 7; }

/* ── edges ── */
.nd-edge { fill: none; stroke: rgba(245, 240, 230, 0.6); stroke-width: 2.8; transition: stroke 300ms, opacity 300ms; }
.nd-edge-short { stroke-width: 2.2; }
.nd-arrowhead { fill: rgba(245, 240, 230, 0.75); }
.nd-arrowhead-lit { fill: var(--gold-bright); }
.nd-e-dim { opacity: 0.5; }
.nd-e-warm { opacity: 0.9; }
.nd-e-lit { stroke: var(--gold-bright); opacity: 1; }
.nd-fan line { stroke: rgba(245, 240, 230, 0.3); stroke-width: 1.8; }
.nd-fan.nd-e-lit line { stroke: rgba(244, 207, 106, 0.75); }
.nd-fan { transition: opacity 300ms; }
.nd-shape {
  fill: rgba(245, 240, 230, 0.86);
  font-size: 20px;
  font-weight: 500;
  letter-spacing: 0;
  text-anchor: middle;
  stroke: none;
}
.nd-shape.nd-e-lit { fill: var(--gold-bright); }
.nd-shape { cursor: pointer; }
.nd-shape:hover { fill: var(--gold-bright); }

/* ── nodes ── */
.nd-node { cursor: pointer; transition: opacity 320ms ease; }
.nd-hit { fill: transparent; stroke: none; }
.nd-n-dim { opacity: 0.52; }
.nd-n-warm { opacity: 0.9; }
.nd-n-lit, .nd-n-open { opacity: 1; }
.nd-node:hover { opacity: 1; }

.nd-name {
  fill: #f5f0e6;
  font-size: 25px;
  font-weight: 600;
  text-anchor: middle;
  letter-spacing: 0;
  transition: fill 300ms;
}
.nd-sub {
  fill: rgba(245, 240, 230, 0.85);
  font-size: 20px;
  text-anchor: middle;
}
/* the name inside its box (ConvLSTM / LSTM) */
.nd-name.nd-in,
.nd-name.nd-head { font-size: 23px; }
.nd-n-lit .nd-name { fill: var(--gold-bright); }
.nd-node:hover .nd-name { fill: var(--gold-bright); }

.nd-block {
  fill: rgba(28, 25, 20, 0.95);
  stroke: rgba(245, 240, 230, 0.7);
  stroke-width: 2.4;
  transition: stroke 300ms, fill 300ms;
}
.nd-prism { fill: rgba(42, 37, 29, 0.98); stroke: rgba(245, 240, 230, 0.75); stroke-width: 2.2; transition: stroke 300ms, fill 300ms; }
.nd-prism-top { fill: rgba(92, 82, 64, 0.9); stroke: rgba(245, 240, 230, 0.6); stroke-width: 1.8; }
.nd-prism-side { fill: rgba(60, 53, 42, 0.95); stroke: rgba(245, 240, 230, 0.6); stroke-width: 1.8; }
.nd-frame { fill: rgba(28, 25, 20, 1); stroke: rgba(245, 240, 230, 0.6); stroke-width: 2; }
.nd-frame-back { fill: rgba(40, 36, 30, 1); }
.nd-frame-line { fill: none; stroke: rgba(245, 240, 230, 0.75); stroke-width: 2.2; transition: stroke 300ms; }
.nd-sheet { stroke: rgba(0, 0, 0, 0.45); stroke-width: 0.8; }
.nd-loop { fill: none; stroke: rgba(245, 240, 230, 0.75); stroke-width: 2.6; }
.nd-loop-label {
  fill: rgba(245, 240, 230, 0.86);
  font-size: 20px;
  text-anchor: middle;
}
.nd-loop-fill { fill: none; stroke: var(--gold-bright); stroke-width: 4.4; stroke-linecap: round; }
/* accumulating: the loop is a track the days fill */
.nd-loop.nd-loop-base,
.nd-n-lit .nd-loop.nd-loop-base { stroke: rgba(245, 240, 230, 0.45); }
.nd-loop-acc { fill: var(--gold-bright); }
.nd-frametag .nd-bracket { stroke: rgba(245, 240, 230, 0.5); }
.nd-frametag-text {
  fill: rgba(245, 240, 230, 0.88);
  font-size: 20px;
  font-weight: 500;
  letter-spacing: 0.06em;
  text-anchor: middle;
  font-variant-numeric: tabular-nums;
}
.nd-frametag-lit .nd-bracket { stroke: rgba(244, 207, 106, 0.85); }
.nd-frametag-lit .nd-frametag-text { fill: var(--gold-bright); }
.nd-spark { fill: none; stroke: #7fd0ff; stroke-width: 2.6; stroke-linejoin: round; }
.nd-cursor { stroke: var(--gold-bright); stroke-width: 2.4; }

.nd-n-lit .nd-block,
.nd-n-lit .nd-prism,
.nd-n-lit .nd-frame-line {
  stroke: var(--gold-bright);
  stroke-width: 3.4;
}
.nd-n-lit .nd-block { fill: rgba(64, 50, 20, 0.95); }
.nd-n-lit .nd-prism { fill: rgba(96, 74, 26, 0.98); }
.nd-n-lit .nd-loop { stroke: var(--gold-bright); }
.nd-n-lit .nd-loop-label { fill: var(--gold-bright); }
.nd-n-lit .nd-sheet { stroke: var(--gold-bright); stroke-width: 1.6; }

.nd-logit { fill: #14120f; stroke-width: 2.6; }
.nd-pill { stroke-width: 2.4; }
.nd-pill-fill { opacity: 0.8; transition: width 200ms linear; }
.nd-pill-code { font-size: 21px; font-weight: 700; letter-spacing: 0.04em; }
/* HF+MD (four-class TAXONOMY) leaves room for its probability */
.nd-pill-code-long { font-size: 17px; letter-spacing: 0; }
.nd-pill-p {
  fill: #f5f0e6;
  font-size: 20px;
  font-weight: 600;
  text-anchor: end;
  font-variant-numeric: tabular-nums;
}
.nd-pulse { fill: var(--gold-bright); filter: drop-shadow(0 0 5px rgba(244, 207, 106, 0.9)); }
</style>
