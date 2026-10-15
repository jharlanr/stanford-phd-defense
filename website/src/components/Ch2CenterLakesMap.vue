<template>
  <!-- Chapter 2's CENTRE-LAKES INSET (the director asked for a small
       zoom-in map covering the seven centre lakes, so the one being
       looked at can be highlighted): BedMachine v6's
       ice, land and sea around the seven PNAS centre lakes (north up,
       cinematic/scene_ch02/build_center_lakes_inset.py → R2
       ch02/inset/centerlakes_v1.json), each lake as its stress-space
       glyph (config/simLakes PHASE_CENTER_MARKERS); the lake on the block
       in gold with its number, the other six dim. Top-left on every block
       beat; follows the second lake's zoom. Figure labels only.
       Any centre lake in the mini map can be clicked to see the same
       sequence for that lake (a later request from the director): the
       glyphs are click targets — a generous invisible
       hit disc (16 px) round each, the NEAREST glyph to the pointer wins
       (1951 · 2520 sit 5 px apart, 2411 · 2416 · 2511 within 8), a gold
       ring + its number on hover; the rest of the inset stays inert. -->
  <Transition name="ccl-fade">
    <div v-if="on && data" class="ccl" :style="{ width: W + 'px', height: H + 'px' }">
      <svg :viewBox="`0 0 ${W} ${H}`" :width="W" :height="H" class="ccl-svg">
        <rect x="0" y="0" :width="W" :height="H" class="ccl-ice" />
        <path v-for="(d, i) in seaPaths" :key="`s${i}`" :d="d" class="ccl-sea" fill-rule="evenodd" />
        <path v-for="(d, i) in landPaths" :key="`l${i}`" :d="d" class="ccl-land" fill-rule="evenodd" />
        <polyline v-for="(p, i) in marginLines" :key="`m${i}`" :points="p" class="ccl-margin" />
        <!-- the other six, dim, then the lake on the block on top -->
        <path
          v-for="lk in others"
          :key="lk.num"
          :d="phaseMarkerPath(lk.shape, lk.px, lk.py, 6)"
          class="ccl-dim"
        />
        <template v-if="cur">
          <path :d="phaseMarkerPath(cur.shape, cur.px, cur.py, 10)" class="ccl-cur" />
          <text :x="lbl.x" :y="lbl.y" :text-anchor="lbl.anchor" class="ccl-num">{{ cur.num }}</text>
        </template>
        <!-- the hovered lake: a ring and its number -->
        <g v-if="hov" class="ccl-hov">
          <circle :cx="hov.px" :cy="hov.py" r="10" class="ccl-ring" />
          <text :x="hovLbl.x" :y="hovLbl.y" :text-anchor="hovLbl.anchor" class="ccl-num ccl-hovnum">{{ hov.num }}</text>
        </g>
        <!-- the hit discs (on top, invisible): the only live part -->
        <circle
          v-for="lk in others"
          :key="`h${lk.num}`"
          :cx="lk.px"
          :cy="lk.py"
          :r="HIT_R"
          class="ccl-hit"
          @pointermove="onHover"
          @pointerleave="hovNum = null"
          @click="onPick"
        />
        <!-- 50 km, top-right (open ice there) -->
        <g class="ccl-bar">
          <line :x1="W - 10 - barPx" :x2="W - 10" :y1="30" :y2="30" />
          <line :x1="W - 10 - barPx" :x2="W - 10 - barPx" :y1="24" :y2="36" />
          <line :x1="W - 10" :x2="W - 10" :y1="24" :y2="36" />
          <text :x="W - 10 - barPx / 2" :y="19" text-anchor="middle" class="ccl-bartxt">50 km</text>
        </g>
        <rect x="0.75" y="0.75" :width="W - 1.5" :height="H - 1.5" class="ccl-frame" />
      </svg>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { mediaUrl } from '../config/media'
import { PHASE_CENTER_MARKERS, phaseMarkerPath } from '../config/simLakes'

const props = defineProps<{
  /** Chapter 2's block beats (the caller's gate). */
  visible: boolean
  /** The centre lake on the block (display number, e.g. 2394). */
  centerNum: number
}>()
const emit = defineEmits<{
  /** A centre lake clicked: its id (e.g. "CW2019_2520"). */
  pick: [id: string]
}>()

interface InsetFile {
  frame: { half_x: number; half_y: number; q: number }
  lakes: { id: string; num: number; x: number; y: number }[]
  margin: number[][]
  land: number[][][]
  sea: number[][][]
}

// One fetch per page life (the JSON is 66 kB).
let insetP: Promise<InsetFile | null> | null = null
const data = ref<InsetFile | null>(null)

// 172 CSS px wide (12 vw below 1440 — it must clear the block's top-left
// corner at 1280); the height keeps the baked window's aspect.
const W = Math.round(Math.min(172, 0.12 * window.innerWidth))
const H = computed(() => (data.value ? Math.round((W * data.value.frame.half_y) / data.value.frame.half_x) : 268))
const kpx = computed(() => (data.value ? W / (2 * data.value.frame.half_x) : 1)) // px per km
function px(xKm: number): number {
  return (xKm + data.value!.frame.half_x) * kpx.value
}
function py(yKm: number): number {
  return (data.value!.frame.half_y - yKm) * kpx.value
}
/** Quantised flat [x0, y0, x1, y1, …] (0.01 km) → screen points. */
function flatPts(a: number[]): [number, number][] {
  const q = data.value!.frame.q
  const out: [number, number][] = []
  for (let i = 0; i + 1 < a.length; i += 2) out.push([px(a[i] / q), py(a[i + 1] / q)])
  return out
}
function ringD(rings: number[][]): string {
  return rings
    .map((r) => 'M ' + flatPts(r).map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join(' L ') + ' Z')
    .join(' ')
}
const seaPaths = computed(() => (data.value ? data.value.sea.map(ringD) : []))
const landPaths = computed(() => (data.value ? data.value.land.map(ringD) : []))
const marginLines = computed(() =>
  data.value ? data.value.margin.map((m) => flatPts(m).map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')) : [],
)
const lakes = computed(() =>
  data.value
    ? data.value.lakes.map((l) => ({ id: l.id, num: l.num, px: px(l.x), py: py(l.y), shape: PHASE_CENTER_MARKERS[l.num] ?? 'o' }))
    : [],
)
const cur = computed(() => lakes.value.find((l) => l.num === props.centerNum) ?? null)
const others = computed(() => lakes.value.filter((l) => l.num !== props.centerNum))
// The number: right of the glyph if it fits, else left — unless a close
// neighbour sits there (1951 and 2520 are 5 km apart; 2411 · 2416 · 2511
// within 12 km), then above.
const LBL_W = 50
const lbl = computed(() => {
  const c = cur.value
  if (!c) return { x: 0, y: 0, anchor: 'start' as const }
  const near = (side: 1 | -1) =>
    others.value.some((o) => Math.abs(o.py - c.py) < 14 && (o.px - c.px) * side > 0 && Math.abs(o.px - c.px) < LBL_W + 18)
  if (c.px + 15 + LBL_W <= W - 4 && !near(1)) return { x: c.px + 15, y: c.py + 6, anchor: 'start' as const }
  if (c.px - 15 - LBL_W >= 4 && !near(-1)) return { x: c.px - 15, y: c.py + 6, anchor: 'end' as const }
  const x = Math.max(4 + LBL_W / 2, Math.min(W - 4 - LBL_W / 2, c.px))
  return c.py > 40 ? { x, y: c.py - 15, anchor: 'middle' as const } : { x, y: c.py + 30, anchor: 'middle' as const }
})
const barPx = computed(() => 50 * kpx.value)

// ── The click targets ──
const HIT_R = 16
const hovNum = ref<number | null>(null)
const hov = computed(() => others.value.find((l) => l.num === hovNum.value) ?? null)
/** The hovered number: above the ring, kept inside the frame. */
const hovLbl = computed(() => {
  const h = hov.value
  if (!h) return { x: 0, y: 0, anchor: 'middle' as const }
  const x = Math.max(4 + LBL_W / 2, Math.min(W - 4 - LBL_W / 2, h.px))
  return h.py > 40 ? { x, y: h.py - 15, anchor: 'middle' as const } : { x, y: h.py + 30, anchor: 'middle' as const }
})
/** The lake nearest the pointer (the hit discs overlap), unless it is
 *  the one on the block. */
function nearest(e: PointerEvent | MouseEvent): { id: string; num: number } | null {
  const svg = (e.currentTarget as SVGElement | null)?.ownerSVGElement
  const r = svg?.getBoundingClientRect()
  if (!r) return null
  const x = e.clientX - r.left
  const y = e.clientY - r.top
  let best: { id: string; num: number } | null = null
  let bd = Infinity
  // nearest of ALL seven — on the lake already on the block, no pick
  for (const l of lakes.value) {
    const d = Math.hypot(l.px - x, l.py - y)
    if (d < bd) {
      bd = d
      best = l
    }
  }
  return bd <= HIT_R + 1 && best && best.num !== props.centerNum ? best : null
}
function onHover(e: PointerEvent): void {
  hovNum.value = nearest(e)?.num ?? null
}
function onPick(e: MouseEvent): void {
  const l = nearest(e)
  hovNum.value = null
  if (l) emit('pick', l.id)
}

// Shown once the block has landed (not while it is a speck mid-dive).
const landed = ref(false)
let raf = 0
const poll = () => {
  const s = (window as unknown as { __simDomainScreen?: { landed?: boolean } | null }).__simDomainScreen
  landed.value = !!s?.landed
  raf = requestAnimationFrame(poll)
}
const on = computed(() => props.visible && landed.value)

onMounted(() => {
  insetP ??= fetch(mediaUrl('ch02/inset/centerlakes_v1.json'))
    .then((r) => (r.ok ? (r.json() as Promise<InsetFile>) : null))
    .catch(() => null)
  insetP.then((j) => {
    if (j) data.value = j
    else console.warn('[ch2] centre-lakes inset failed to load')
  })
  raf = requestAnimationFrame(poll)
})
onBeforeUnmount(() => cancelAnimationFrame(raf))
</script>

<style scoped>
.ccl {
  position: absolute;
  top: max(7vh, calc(var(--chrome-bottom, 0px) + 0.9rem));
  left: 2vw;
  z-index: 8;
  pointer-events: none;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.6);
}
.ccl-svg {
  display: block;
}
/* the sheet pale, the land dark, the sea darker — the Conclusion map's
   stage, quieter, so the gold lake is the brightest thing in it */
.ccl-ice {
  fill: #b9c4cd;
}
.ccl-sea {
  fill: #0e1b27;
}
.ccl-land {
  fill: #4d463c;
}
.ccl-margin {
  fill: none;
  stroke: #1d2228;
  stroke-width: 1.5;
  stroke-linejoin: round;
}
.ccl-dim {
  fill: #2a2f36;
  stroke: rgba(245, 240, 230, 0.7);
  stroke-width: 1;
}
.ccl-cur {
  fill: #f4cf6a;
  stroke: #0a0a0a;
  stroke-width: 2.2;
  stroke-linejoin: round;
}
.ccl-num {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 19px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  fill: #f4cf6a;
  paint-order: stroke;
  stroke: #0a0a0a;
  stroke-width: 4.5px;
  stroke-linejoin: round;
}
.ccl-bar line {
  stroke: #14171c;
  stroke-width: 2;
}
.ccl-bartxt {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 15px;
  font-weight: 700;
  fill: #14171c;
}
.ccl-frame {
  fill: none;
  stroke: rgba(245, 240, 230, 0.85);
  stroke-width: 1.5;
}
.ccl-hit {
  fill: transparent;
  stroke: none;
  pointer-events: all;
  cursor: pointer;
}
.ccl-ring {
  fill: none;
  stroke: #f4cf6a;
  stroke-width: 2.2;
}
.ccl-hov {
  pointer-events: none;
}
.ccl-hovnum {
  font-size: 17px;
}
.ccl-fade-enter-active,
.ccl-fade-leave-active {
  transition: opacity 0.5s ease;
}
.ccl-fade-enter-from,
.ccl-fade-leave-to {
  opacity: 0;
}
</style>
