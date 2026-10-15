<template>
  <!-- One lake-drainage stress space (the thesis's Fig. 5 recipe): x =
       the post-drainage principal, y = its perturbation Δσ, one symbol
       per neighbouring lake, shape = its center lake, colour = how it
       drained. The director's rule: ONE diagram at a time, big,
       LaTeX axes; on the walk only the chosen center lake's neighbours.
       The points TWEEN between beats (model ↔ component), so the same
       lakes visibly move; the FRAME never does (the x and y axis scales
       of every stress space diagram are fixed, by the director's rule)
       — one ±1000 kPa square on every diagram of beats 3–8. -->
  <svg
    class="ss-svg"
    :viewBox="`0 0 ${VW} ${VH}`"
    :preserveAspectRatio="hugTop ? 'xMidYMin meet' : 'xMidYMid meet'"
    @pointerleave="emit('lake-hover', null)"
  >
    <defs>
      <clipPath :id="clipId">
        <rect :x="ML" :y="MT" :width="P" :height="P" />
      </clipPath>
      <!-- the emphasised title's soft gold glow (a blurred gold copy of
           its ink, under it) -->
      <filter :id="glowId" x="-20%" y="-60%" width="140%" height="220%">
        <feGaussianBlur in="SourceAlpha" stdDeviation="5" result="b" />
        <feFlood flood-color="#f5c75e" />
        <feComposite in2="b" operator="in" />
      </filter>
    </defs>

    <!-- header: model + component (left), the key (right) -->
    <g v-if="header" class="ss-head">
      <text v-if="headerModel" ref="modelEl" :x="ML" :y="MT - 22 * fs" class="ss-model" :font-size="40 * fs">{{ model === 'elastic' ? 'Elastic' : 'Viscous' }}</text>
      <image v-bind="eqAt(comp === 't1' ? 't1' : 't2', K_SYM, headerModel ? ML + modelW + 16 * fs : ML, MT - 22 * fs, 'left', 'baseline')" />
      <g v-for="k in key" :key="k.label" :transform="`translate(${k.x} ${MT - 30 * fs})`">
        <path :d="phaseMarkerPath(k.shape, 0, 0, 7 * fs)" :fill="k.open ? 'none' : k.color" :stroke="k.open ? k.color : 'rgba(0,0,0,0.6)'" :stroke-width="k.open ? 2 : 1" />
        <text :x="13 * fs" :y="6 * fs" class="ss-key" :font-size="17 * fs">{{ k.label }}</text>
      </g>
    </g>

    <!-- frame, grid, zero lines -->
    <rect :x="ML" :y="MT" :width="P" :height="P" class="ss-frame" />
    <g :clip-path="`url(#${clipId})`">
      <template v-for="t in grid" :key="`g${t}`">
        <line :x1="sx(t)" :x2="sx(t)" :y1="MT" :y2="MT + P" :class="t % CH2_AXIS_STEP === 0 ? 'ss-grid' : 'ss-grid-minor'" />
        <line :x1="ML" :x2="ML + P" :y1="sy(t)" :y2="sy(t)" :class="t % CH2_AXIS_STEP === 0 ? 'ss-grid' : 'ss-grid-minor'" />
      </template>
      <line :x1="sx(0)" :x2="sx(0)" :y1="MT" :y2="MT + P" class="ss-zero" />
      <line :x1="ML" :x2="ML + P" :y1="sy(0)" :y2="sy(0)" class="ss-zero" />
    </g>
    <!-- the axes (the director found the earlier math-axis typography
         ugly; these replace it): each axis = its edge line, ticks,
         tick labels and its LaTeX title, drawn as ONE group so an
         EMPHASISED axis (`emphasis`) reads at full strength with a bolder
         edge while the other steps back to ~0.55. And BREATHES (the
         director wanted the emphasised axis subtly pulsing, with a bold
         title pulsing with it, to make clear which
         axis the beat is about): its edge goes gold and swells 4 →
         5.5 px on a 2.4 s cycle, its title — the TeX-bold variant — grows
         1.0 → 1.08 over a gold glow in step. -->
    <g class="ss-axis" :class="axClass('x')">
      <line v-if="emOn('x')" :x1="ML" :x2="ML + P" :y1="MT + P" :y2="MT + P" class="ss-axglow" />
      <line :x1="ML" :x2="ML + P" :y1="MT + P" :y2="MT + P" class="ss-axline" />
      <template v-for="t in ticks" :key="`tx${t}`">
        <line :x1="sx(t)" :x2="sx(t)" :y1="MT + P" :y2="MT + P + 8 * fs" class="ss-tick" />
        <text :x="sx(t)" :y="MT + P + 33 * fs" text-anchor="middle" class="ss-ticklbl" :font-size="22 * fs">{{ fmtTick(t) }}</text>
      </template>
      <g class="ss-axtitle">
        <image v-if="emOn('x')" v-bind="eqAt(axName('x'), kX, xTitleCx, VH - 8 - NOTE_H, 'center', 'bottom')" :filter="`url(#${glowId})`" class="ss-axtitle-glow" />
        <image v-bind="eqAt(axName('x'), kX, xTitleCx, VH - 8 - NOTE_H, 'center', 'bottom')" />
      </g>
      <text v-if="note" :x="xTitleCx" :y="VH - 10" text-anchor="middle" class="ss-note" :font-size="17 * fs">{{ note }}</text>
    </g>
    <g class="ss-axis" :class="axClass('y')">
      <line v-if="emOn('y')" :x1="ML" :x2="ML" :y1="MT" :y2="MT + P" class="ss-axglow" />
      <line :x1="ML" :x2="ML" :y1="MT" :y2="MT + P" class="ss-axline" />
      <template v-for="t in ticks" :key="`ty${t}`">
        <line :x1="ML - 8 * fs" :x2="ML" :y1="sy(t)" :y2="sy(t)" class="ss-tick" />
        <text :x="ML - 13 * fs" :y="sy(t) + 7.5 * fs" text-anchor="end" class="ss-ticklbl" :font-size="22 * fs">{{ fmtTick(t) }}</text>
      </template>
      <g :transform="`rotate(-90 ${AXY_X} ${MT + P / 2})`">
        <g class="ss-axtitle">
          <image v-if="emOn('y')" v-bind="eqAt(axName('y'), K_AX, AXY_X, MT + P / 2, 'center', 'middle')" :filter="`url(#${glowId})`" class="ss-axtitle-glow" />
          <image v-bind="eqAt(axName('y'), K_AX, AXY_X, MT + P / 2, 'center', 'middle')" />
        </g>
      </g>
    </g>

    <!-- the ghost lake's key: inside the frame, top-left -->
    <g v-if="ghostOn" class="ss-ghostkey" :transform="`translate(${ML + 20 * fs} ${MT + 26 * fs})`">
      <path :d="phaseMarkerPath(PHASE_CENTER_MARKERS[ghostNum!] ?? 'o', 0, 0, 8 * fs)" :fill="GHOST_COLOR" stroke="rgba(0,0,0,0.6)" stroke-width="1" />
      <text :x="14 * fs" :y="6 * fs" class="ss-key" :font-size="17 * fs" fill-opacity="0.75">{{ ghostNum }}</text>
    </g>

    <text v-if="empty" :x="ML + P / 2" :y="MT + P / 2 + 7" text-anchor="middle" class="ss-empty" :font-size="17 * fs">no assessable neighbours</text>

    <!-- points: a STABLE order (never re-sorted by hover — an early
         hysteresis bug), each with a generous transparent hit disc -->
    <g :clip-path="`url(#${clipId})`">
      <g
        v-for="pt in drawn"
        :key="pt.key"
        class="ss-pt"
        :data-num="pt.num"
        :opacity="pt.a"
        :style="{ pointerEvents: pt.a > 0.3 ? 'auto' : 'none' }"
        @pointerenter="emit('lake-hover', pt.num)"
        @pointerleave="emit('lake-hover', null)"
      >
        <path
          :d="phaseMarkerPath(pt.shape, pt.px, pt.py, pt.s)"
          :fill="pt.open ? 'none' : pt.color"
          :stroke="pt.open ? pt.color : 'rgba(0,0,0,0.6)'"
          :stroke-width="pt.open ? 2.4 : 1.1"
        />
        <circle :cx="pt.px" :cy="pt.py" :r="Math.max(16, pt.s + 6)" fill="transparent" />
      </g>
    </g>
    <!-- (the population diagram used to ring the chosen lake's neighbours
         in gold — the director found the yellow circles unnecessary and
         confusing — every lake reads alike there) -->
    <!-- lake numbers beside the lit points (single-lake views) -->
    <g v-if="labels" class="ss-labels">
      <line
        v-for="l in placedLabels.filter((q) => q.leader)"
        :key="`ld${l.key}`"
        :x1="l.leader![0]"
        :y1="l.leader![1]"
        :x2="l.leader![2]"
        :y2="l.leader![3]"
        :opacity="l.a * l.lead * 0.9"
        class="ss-leader"
      />
      <text
        v-for="l in placedLabels"
        :key="`l${l.key}`"
        :x="l.x"
        :y="l.y"
        text-anchor="middle"
        :opacity="l.a"
        class="ss-lbl"
        :font-size="17 * fs"
        :class="{ 'ss-lbl-hl': l.num === highlightNum }"
      >{{ l.num }}</text>
    </g>
    <!-- the hover highlight: its own pointer-transparent layer -->
    <g :clip-path="`url(#${clipId})`" class="ss-hl">
      <template v-for="pt in drawn" :key="`h${pt.key}`">
        <template v-if="pt.num === highlightNum && pt.a > 0.05">
          <circle :cx="pt.px" :cy="pt.py" :r="pt.s + 8" class="ss-glow" />
          <path
            :d="phaseMarkerPath(pt.shape, pt.px, pt.py, pt.s)"
            :fill="pt.open ? 'none' : pt.color"
            stroke="#f5c75e"
            stroke-width="2.6"
          />
        </template>
      </template>
    </g>
    <g v-if="!labels && hoverLabel" class="ss-hl">
      <text :x="hoverLabel.x" :y="hoverLabel.y" class="ss-lbl ss-lbl-hl" text-anchor="start" :font-size="17 * fs">{{ hoverLabel.num }}</text>
    </g>
  </svg>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  PHASE_CENTER_MARKERS,
  PHASE_GROUP_STYLE,
  phaseMarkerPath,
  type PhasePoint,
} from '../config/simLakes'
import { CH2_EQ, type Ch2EqName } from '../config/ch2Eqs'
import { CH2_AXIS_KPA, CH2_AXIS_MINOR, CH2_AXIS_STEP, ch2EqUrl } from '../config/ch2Results'
import type { Ch2Comp, Ch2Field, Ch2Model } from '../config/ch2Beats'

const props = withDefaults(
  defineProps<{
    model: Ch2Model
    comp: Ch2Comp
    /** Every point of this model (phase_space.json). */
    points: PhasePoint[]
    /** The chosen center lake (display number, e.g. 2394). */
    centerNum: number
    /** Draw every lake's neighbours (the complete stress space); else
     *  only the chosen center lake's. */
    showAll?: boolean
    /** A second center lake drawn FAINT beneath the chosen one's (the
     *  second center lake's walk keeps the first lake's points as the
     *  contrast, on the same fixed frame). Ignored with showAll. */
    ghostNum?: number | null
    highlightNum?: number | null
    /** Lake numbers beside the lit points. */
    labels?: boolean
    /** Component symbol + key above the plot … */
    header?: boolean
    /** … led by the model's name (off where a column title names it). */
    headerModel?: boolean
    /** Tween changes (false = snap). */
    animate?: boolean
    /** Type scale: every font, symbol and margin × fs (the plot square
     *  stays 520 units) — for diagrams shown small (the comparison). */
    fs?: number
    /** The axis the beat is about: drawn at full strength with a bolder
     *  edge; the other steps back (null = both plain). */
    emphasis?: 'x' | 'y' | null
    /** The walk's field (config/ch2Beats.ts): `pre` shows the FRAME ALONE
     *  (on the pre-drainage viscous beat nothing has happened yet, so
     *  the director wanted the stress state plot present but
     *  blank) — every symbol parked
     *  invisible at (x1_pre, 0); the next beat fades them in where they
     *  belong; anything else plots (post, Δ). */
    field?: Ch2Field | null
    /** The x-axis title in place of the component's σ^post label — the
     *  population page's ELASTIC column shows the ≈ definition there
     *  (the director asked for the ≈ equation itself on the
     *  x-axis). Drawn no wider than the diagram (its own scale). */
    xTitle?: Ch2EqName | null
    /** A line of small type under the x-axis title ("(qualitative, for
     *  illustration only)"). `noteRow` reserves its row WITHOUT text so
     *  two diagrams side by side keep the same plot size. */
    note?: string | null
    noteRow?: boolean
    /** Hug the top of the box instead of centring (the slack goes below,
     *  so a column title sits right over the diagram). */
    hugTop?: boolean
  }>(),
  { field: null, showAll: false, ghostNum: null, highlightNum: null, labels: false, header: true, headerModel: true, animate: true, fs: 1, emphasis: null, xTitle: null, note: null, noteRow: false, hugTop: false },
)
const emit = defineEmits<{ 'lake-hover': [num: number | null] }>()

// ── Geometry (viewBox units ≈ CSS px at the design size, fs = 1) ──
// fs is read ONCE per instance, so the viewBox never jumps.
const fs = props.fs
// 22-unit tick labels and 3.1× axis titles (the back row).
const ML = 22 + 104 * fs // y ticks ("−1000") + the rotated y title
const MR = 14 + 30 * fs // half the "1000" tick label past the plot's right edge
const MT = 64 * fs // the header
const NOTE_H = props.note != null || props.noteRow ? 30 * fs : 0 // the note's row under the x title
const MB = 10 + 102 * fs + NOTE_H // x ticks + the x title (+ the note)
const P = 520 // the square plot
const VW = ML + P + MR
const VH = MT + P + MB
const AXY_X = 4 + 22 * fs // rotated y-title centre line
const K_AX = 3.1 * fs // LaTeX units per bp: axis titles (10 pt → 31 units)
const K_SYM = 3.2 * fs // the component symbol in the header

const clipId = `ss-clip-${Math.random().toString(36).slice(2, 8)}`
const glowId = clipId.replace('clip', 'glow')
/** Is axis `a` the emphasised one? */
function emOn(a: 'x' | 'y'): boolean {
  return props.emphasis === a
}
function axClass(a: 'x' | 'y'): Record<string, boolean> {
  return { 'ss-axis-em': emOn(a), 'ss-axis-dim': props.emphasis != null && !emOn(a) }
}
/** An axis's TeX title — its bold variant while it is emphasised. */
function axName(a: 'x' | 'y'): Ch2EqName {
  const bold = emOn(a)
  if (a === 'x' && props.xTitle) return props.xTitle
  if (a === 'x') return props.comp === 't1' ? (bold ? 'ax_post_t1_bold' : 'ax_post_t1') : bold ? 'ax_post_t2_bold' : 'ax_post_t2'
  return props.comp === 't1' ? (bold ? 'ax_diff_t1_bold' : 'ax_diff_t1') : bold ? 'ax_diff_t2_bold' : 'ax_diff_t2'
}

// An overriding x title (the ≈ definition) is long: scaled to fit the
// whole width and centred on it; the usual titles sit on the plot's centre.
const kX = props.xTitle ? Math.min(K_AX, (VW - 16) / CH2_EQ[props.xTitle].w) : K_AX
const xTitleCx = props.xTitle ? VW / 2 : ML + P / 2

type HA = 'left' | 'center' | 'right'
type VA = 'top' | 'middle' | 'bottom' | 'baseline'
function eqAt(name: Ch2EqName, k: number, x: number, y: number, ha: HA, va: VA) {
  const b = CH2_EQ[name]
  const w = b.w * k
  const h = b.h * k
  const x0 = ha === 'left' ? x : ha === 'center' ? x - w / 2 : x - w
  const y0 = va === 'top' ? y : va === 'middle' ? y - h / 2 : va === 'bottom' ? y - h : y - b.base * k
  return { href: ch2EqUrl(name), x: x0, y: y0, width: w, height: h }
}

// Header: the component symbol sits right after the model name, whose
// width is MEASURED (EB Garamond may still be loading — re-measure when
// the fonts are in).
const modelEl = ref<SVGTextElement | null>(null)
const modelW = ref(props.model === 'elastic' ? 106 : 124)
function measureModel(): void {
  const el = modelEl.value
  if (!el) return
  try {
    const w = el.getComputedTextLength()
    if (w > 0) modelW.value = w
  } catch {
    // not rendered yet
  }
}
watch(() => props.model, () => requestAnimationFrame(measureModel))
// The class key, right-aligned on the plot's right edge (Inter 17 units
// ≈ 9.2 units per lower-case character).
const key = computed(() => {
  const shape = props.showAll ? 'o' : (PHASE_CENTER_MARKERS[props.centerNum] ?? 'o')
  const items = (['cyan', 'gray', 'black'] as const).map((g) => {
    const st = PHASE_GROUP_STYLE[g]
    return { label: st.label, shape, color: st.color, open: st.open, w: (20 + st.label.length * 9.2) * fs, x: 0 }
  })
  let x = ML + P
  for (let i = items.length - 1; i >= 0; i--) {
    x -= items[i].w
    items[i].x = x + 7 * fs
    // the big-type diagrams (fs > 1.3: compare / complete) close the
    // gaps so the key clears the component symbol on the left
    x -= (fs > 1.3 ? 14 : 24) * fs
  }
  return items
})

// ── The frame: ONE fixed square for every diagram (never tweened) ──
const LIM = CH2_AXIS_KPA
function steps(s: number): number[] {
  const out: number[] = []
  const n = Math.floor((LIM * 1.0001) / s)
  for (let i = -n; i <= n; i++) out.push(i * s)
  return out
}
const ticks = steps(CH2_AXIS_STEP)
const grid = steps(CH2_AXIS_MINOR).filter((t) => t !== 0 && Math.abs(t) < LIM)
function fmtTick(t: number): string {
  return t < 0 ? `−${Math.abs(t)}` : `${t}`
}
function sx(v: number): number {
  return ML + ((v + LIM) / (2 * LIM)) * P
}
function sy(v: number): number {
  return MT + P - ((v + LIM) / (2 * LIM)) * P
}

// The ghost lake's points: faint, in their drainage colours.
const GHOST_A = 0.28
const GHOST_COLOR = 'rgba(245, 240, 230, 0.45)'
const ghostOn = computed(
  () => !props.showAll && props.ghostNum != null && props.points.some((p) => p.center === props.ghostNum),
)

// ── Points (tweened in DATA space so the frame and points move together) ──
interface Disp { x: number; y: number; a: number; s: number }
const disp = reactive<Record<string, Disp>>({})
const meta = new Map<string, PhasePoint>()

function keyOf(p: PhasePoint): string {
  return `${p.center}-${p.num}`
}
function targets(): Record<string, Disp> {
  const out: Record<string, Disp> = {}
  for (const p of props.points) {
    // the pre-drainage beat: the plot is BLANK — the symbols
    // park invisible at the viscous pre-drainage principal on the axis
    const pre = props.field === 'pre'
    const x = pre ? ((props.comp === 't1' ? p.x1_pre : p.x2_pre) ?? null) : props.comp === 't1' ? p.x1 : p.x2
    const y = pre ? (x === null ? null : 0) : props.comp === 't1' ? p.y1 : p.y2
    if (x === null || y === null || !PHASE_GROUP_STYLE[p.group]) continue
    const mine = p.center === props.centerNum
    const ghost = !props.showAll && !mine && props.ghostNum != null && p.center === props.ghostNum
    const shown = props.showAll || mine
    // the single views grow the chosen lake's points; the population
    // diagram shows every lake alike
    const emph = mine && !props.showAll
    out[keyOf(p)] = {
      x,
      y,
      a: pre ? 0 : ghost ? GHOST_A : shown ? 1 : 0,
      s: (emph ? 11 : 8.5) * fs,
    }
    meta.set(keyOf(p), p)
  }
  return out
}

let raf: number | null = null
function ease(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}
// Several props can change across two flushes for one move (the model
// and the field, then the points): a retarget within this window of the
// last one keeps ITS clock (the travel stays one eased path, no second
// start from rest mid-flight).
let tweenT0: number | null = null
function retarget(animate: boolean): void {
  const to = targets()
  // Keys that left the data fade out where they are.
  for (const k of Object.keys(disp)) if (!to[k]) to[k] = { ...disp[k], a: 0 }
  // New keys appear in place.
  for (const k of Object.keys(to)) if (!disp[k]) disp[k] = { ...to[k], a: 0 }
  // The labels' slots for the TARGET layout; each label slides from the
  // slot it is in now to its new one on the symbols' own clock (the
  // director wanted the symbols and their labels to move smoothly
  // together on the stress state plots — the slot used to switch at the
  // START of the travel, so a label hopped sides while its symbol flew).
  const pl = computePlacement(to)
  for (const k of Object.keys(lblOff)) if (!pl.has(k)) delete lblOff[k]
  for (const [k, o] of pl) if (!lblOff[k]) lblOff[k] = { ...o }
  if (raf !== null) cancelAnimationFrame(raf)
  if (!animate) {
    for (const k of Object.keys(to)) Object.assign(disp[k], to[k])
    for (const [k, o] of pl) Object.assign(lblOff[k], o)
    raf = null
    tweenT0 = null
    return
  }
  const from: Record<string, Disp> = {}
  for (const k of Object.keys(to)) from[k] = { ...disp[k] }
  // A symbol that is invisible fades IN where it belongs and fades OUT
  // where it is — it never travels while unseen (the blank pre-drainage
  // plot would otherwise launch every lake off the x-axis).
  for (const k of Object.keys(to)) {
    const f = from[k]
    const g = to[k]
    if (f.a < 0.01 && g.a >= 0.01) { f.x = g.x; f.y = g.y }
    else if (g.a < 0.01 && f.a >= 0.01) { g.x = f.x; g.y = f.y }
  }
  const lFrom: Record<string, LblOff> = {}
  for (const [k] of pl) lFrom[k] = { ...lblOff[k] }
  // ~0.6 s: the symbols TRAVEL between the walk's beats —
  // from the elastic point to the viscous one — rather than crossfading
  // (they fade in from the blank pre-drainage plot where they belong)
  const DUR = 650
  // a retarget hard on the heels of another (< 1 frame-ish) joins its clock
  const now0 = performance.now()
  const join = tweenT0 !== null && now0 - tweenT0 < 50
  let t0: number | null = join ? tweenT0 : null
  // (joined: re-base `from` so the eased path still starts where the
  // first retarget began — the symbols have barely moved in < 50 ms)
  const tick = (now: number) => {
    if (t0 === null) t0 = now
    tweenT0 = t0
    const t = Math.min(1, Math.max(0, (now - t0) / DUR))
    const e = ease(t)
    for (const k of Object.keys(to)) {
      const f = from[k]
      const g = to[k]
      const d = disp[k]
      d.x = f.x + (g.x - f.x) * e
      d.y = f.y + (g.y - f.y) * e
      d.a = f.a + (g.a - f.a) * e
      d.s = f.s + (g.s - f.s) * e
    }
    for (const [k, g] of pl) {
      const f = lFrom[k]
      const d = lblOff[k]
      d.cx = f.cx + (g.cx - f.cx) * e
      d.dy = f.dy + (g.dy - f.dy) * e
      d.lead = f.lead + (g.lead - f.lead) * e
    }
    if (t < 1) raf = requestAnimationFrame(tick)
    else {
      raf = null
      tweenT0 = null
    }
  }
  raf = requestAnimationFrame(tick)
}

watch(
  () => [props.model, props.comp, props.field, props.points, props.showAll, props.centerNum, props.ghostNum] as const,
  () => retarget(props.animate),
)
onMounted(() => {
  retarget(props.animate)
  measureModel()
  document.fonts?.ready.then(measureModel).catch(() => {})
})
onBeforeUnmount(() => {
  if (raf !== null) cancelAnimationFrame(raf)
})

interface Drawn {
  key: string
  num: number
  px: number
  py: number
  a: number
  s: number
  shape: string
  color: string
  open: boolean
  mine: boolean
}
const drawn = computed<Drawn[]>(() => {
  const out: Drawn[] = []
  // Stable order: other groups first, then the chosen lake's (on top).
  const keys = Object.keys(disp).sort((a, b) => {
    const ma = meta.get(a)?.center === props.centerNum ? 1 : 0
    const mb = meta.get(b)?.center === props.centerNum ? 1 : 0
    return ma - mb || (a < b ? -1 : a > b ? 1 : 0)
  })
  for (const k of keys) {
    const d = disp[k]
    const p = meta.get(k)
    if (!p || d.a <= 0.002) continue
    const st = PHASE_GROUP_STYLE[p.group]
    out.push({
      key: k,
      num: p.num,
      px: sx(d.x),
      py: sy(d.y),
      a: d.a,
      s: d.s,
      shape: PHASE_CENTER_MARKERS[p.center] ?? 'o',
      color: st.color,
      open: st.open,
      mine: p.center === props.centerNum,
    })
  }
  return out
})

const empty = computed(
  () => !props.showAll && !props.points.some((p) => p.center === props.centerNum),
)

// ── Lake-number labels: a greedy placement against the TARGET layout
// (8 candidate offsets, first that overlaps no symbol and no placed
// label), riding the tweened point; the offset itself tweens with it
// (lblOff: the label's centre and baseline relative to its symbol, and
// its leader's strength). ──
// Measured (Chromium, Inter 17 units): a 4-digit number is 44 × 20.5.
const LBL_CW = 11.2 * fs
const LBL_PAD = 3
interface LblOff { cx: number; dy: number; lead: number }
const lblOff = reactive<Record<string, LblOff>>({})
function computePlacement(to: Record<string, Disp>): Map<string, LblOff> {
  const out = new Map<string, LblOff>()
  if (!props.labels) return out
  const pts = Object.entries(to)
    .filter(([k, d]) => d.a > 0.5 && meta.get(k)?.center === props.centerNum)
    .map(([k, d]) => ({ k, x: sx(d.x), y: sy(d.y), num: meta.get(k)!.num }))
  type Box = { x0: number; y0: number; x1: number; y1: number }
  const R = 14 * fs
  const boxes: Box[] = pts.map((p) => ({ x0: p.x - R, y0: p.y - R, x1: p.x + R, y1: p.y + R }))
  const hit = (b: Box) =>
    b.x0 < ML || b.x1 > ML + P || b.y0 < MT || b.y1 > MT + P ||
    boxes.some((o) => b.x0 < o.x1 && b.x1 > o.x0 && b.y0 < o.y1 && b.y1 > o.y0)
  const res = new Map<string, { dx: number; dy: number; anchor: 'start' | 'end' | 'middle' }>()
  // Place the most crowded first (by neighbour count).
  const order = [...pts].sort((a, b) => {
    const ca = pts.filter((q) => Math.hypot(q.x - a.x, q.y - a.y) < 60).length
    const cb = pts.filter((q) => Math.hypot(q.x - b.x, q.y - b.y) < 60).length
    return cb - ca
  })
  for (const p of order) {
    const w = String(p.num).length * LBL_CW
    type Cand = { dx: number; dy: number; anchor: 'start' | 'end' | 'middle' }
    const raw: Cand[] = [
      { dx: 17, dy: 6, anchor: 'start' },
      { dx: -17, dy: 6, anchor: 'end' },
      { dx: 15, dy: -12, anchor: 'start' },
      { dx: 15, dy: 24, anchor: 'start' },
      { dx: -15, dy: -12, anchor: 'end' },
      { dx: -15, dy: 24, anchor: 'end' },
      { dx: 0, dy: -19, anchor: 'middle' },
      { dx: 0, dy: 31, anchor: 'middle' },
      // set off, with a leader
      { dx: 36, dy: -26, anchor: 'start' },
      { dx: 36, dy: 38, anchor: 'start' },
      { dx: -36, dy: -26, anchor: 'end' },
      { dx: -36, dy: 38, anchor: 'end' },
      { dx: 44, dy: 6, anchor: 'start' },
      { dx: -44, dy: 6, anchor: 'end' },
      { dx: 0, dy: -40, anchor: 'middle' },
      { dx: 0, dy: 52, anchor: 'middle' },
    ]
    const cands: Cand[] = raw.map((c) => ({ ...c, dx: c.dx * fs, dy: c.dy * fs }))
    const boxOf = (c: Cand): Box => {
      const x0 = c.anchor === 'start' ? p.x + c.dx : c.anchor === 'end' ? p.x + c.dx - w : p.x + c.dx - w / 2
      return {
        x0: x0 - LBL_PAD,
        y0: p.y + c.dy - 15 * fs - LBL_PAD,
        x1: x0 + w + LBL_PAD,
        y1: p.y + c.dy + 5 * fs + LBL_PAD,
      }
    }
    let chosen: Cand | null = null
    for (const c of cands) {
      const b = boxOf(c)
      if (!hit(b)) {
        chosen = c
        boxes.push(b)
        break
      }
    }
    if (!chosen) {
      // Nothing is clear (the pre-drainage beat lines every lake up on
      // the x-axis): the candidate inside the frame that
      // overlaps the least LABEL area — never one number printed over
      // another.
      let best = Infinity
      for (const c of cands) {
        const b = boxOf(c)
        if (b.x0 < ML || b.x1 > ML + P || b.y0 < MT || b.y1 > MT + P) continue
        let ov = 0
        boxes.forEach((o, j) => {
          const ix = Math.max(0, Math.min(b.x1, o.x1) - Math.max(b.x0, o.x0))
          const iy = Math.max(0, Math.min(b.y1, o.y1) - Math.max(b.y0, o.y0))
          // a label box (past the symbols) weighs ten times a symbol
          ov += ix * iy * (j >= pts.length ? 10 : 1)
        })
        if (ov < best) {
          best = ov
          chosen = c
        }
      }
      chosen ??= cands[0]
      boxes.push(boxOf(chosen))
    }
    res.set(p.k, chosen)
  }
  for (const p of pts) {
    const c = res.get(p.k)
    if (!c) continue
    const w = String(p.num).length * LBL_CW
    out.set(p.k, {
      cx: c.anchor === 'start' ? c.dx + w / 2 : c.anchor === 'end' ? c.dx - w / 2 : c.dx,
      dy: c.dy,
      // a label set off from its symbol gets a hairline leader
      lead: Math.hypot(c.dx, c.dy) > 28 * fs ? 1 : 0,
    })
  }
  return out
}
const placedLabels = computed(() =>
  drawn.value
    .filter((d) => d.mine && lblOff[d.key])
    .map((d) => {
      const o = lblOff[d.key]
      const x = d.px + o.cx
      const y = d.py + o.dy
      // the leader: from the symbol's edge to the label box's edge,
      // fading with the slot (lead 0 → 1)
      let leader: [number, number, number, number] | null = null
      if (o.lead > 0.01) {
        const w = String(d.num).length * LBL_CW
        const cx = x
        const cy = y - 5 * fs
        const vx = cx - d.px
        const vy = cy - d.py
        const L = Math.hypot(vx, vy) || 1
        // distance from the box centre back along the ray to its edge
        const tx = Math.abs(vx) > 1e-6 ? (w / 2 + 3) / Math.abs(vx) : Infinity
        const ty = Math.abs(vy) > 1e-6 ? (12 * fs + 3) / Math.abs(vy) : Infinity
        const back = Math.min(tx, ty) * L
        const r0 = d.s + 4
        if (L - back > r0 + 4) {
          leader = [d.px + (vx / L) * r0, d.py + (vy / L) * r0, d.px + (vx / L) * (L - back), d.py + (vy / L) * (L - back)]
        }
      }
      return { key: d.key, num: d.num, x, y, a: d.a, lead: o.lead, leader }
    }),
)
const hoverLabel = computed(() => {
  if (props.highlightNum == null) return null
  const d = drawn.value.find((q) => q.num === props.highlightNum && q.a > 0.3)
  return d ? { num: d.num, x: d.px + 17 * fs, y: d.py - 12 * fs } : null
})
</script>

<style scoped>
.ss-svg {
  width: 100%;
  height: 100%;
  display: block;
  overflow: visible;
}
.ss-model {
  font-family: 'EB Garamond', serif;
  fill: var(--gold, #f4cf6a);
}
.ss-note {
  font-family: 'Inter', system-ui, sans-serif;
  fill: var(--gold, #f4cf6a);
  letter-spacing: 0.01em;
}
.ss-key {
  font-family: 'Inter', system-ui, sans-serif;
  fill: rgba(245, 240, 230, 0.92);
}
/* Projector legibility: the frame, zero lines, ticks and
   leaders keep a SCREEN width (non-scaling) so the small diagrams of the
   compare / complete pages don't thin them to sub-pixel hairlines. */
.ss-frame {
  fill: rgba(255, 255, 255, 0.015);
  stroke: rgba(245, 245, 245, 0.55);
  stroke-width: 1.6px;
  vector-effect: non-scaling-stroke;
}
.ss-grid {
  stroke: rgba(245, 245, 245, 0.1);
  stroke-width: 1;
}
.ss-grid-minor {
  stroke: rgba(245, 245, 245, 0.04);
  stroke-width: 1;
}
.ss-zero {
  stroke: rgba(245, 245, 245, 0.5);
  stroke-width: 1.6px;
  vector-effect: non-scaling-stroke;
}
.ss-tick {
  stroke: rgba(245, 245, 245, 0.9);
  stroke-width: 2px;
  vector-effect: non-scaling-stroke;
}
.ss-ticklbl {
  font-family: 'Inter', system-ui, sans-serif;
  font-variant-numeric: tabular-nums;
  font-weight: 500;
  fill: #f5f0e6;
}
.ss-axis {
  transition: opacity 0.5s ease;
}
.ss-axline {
  stroke: rgba(245, 245, 245, 0.75);
  stroke-width: 2px;
  vector-effect: non-scaling-stroke;
  transition: stroke-width 0.5s ease;
}
/* the beat's axis: a bold gold edge that breathes (2.4 s), its title
   swelling over a gold glow in step; the other steps back */
.ss-axis-em .ss-axline {
  stroke: #f5c75e;
  stroke-width: 4px;
  animation: ss-breath-line 2.4s ease-in-out infinite;
}
.ss-axglow {
  stroke: #f5c75e;
  stroke-width: 14px;
  stroke-linecap: round;
  vector-effect: non-scaling-stroke;
  opacity: 0;
  animation: ss-breath-glow 2.4s ease-in-out infinite;
}
.ss-axtitle {
  transform-box: fill-box;
  transform-origin: center;
}
.ss-axis-em .ss-axtitle {
  animation: ss-breath-title 2.4s ease-in-out infinite;
}
.ss-axtitle-glow {
  opacity: 0.35;
  animation: ss-breath-tglow 2.4s ease-in-out infinite;
}
@keyframes ss-breath-line {
  0%, 100% { stroke-width: 4px; }
  50% { stroke-width: 5.5px; }
}
@keyframes ss-breath-glow {
  0%, 100% { opacity: 0.06; }
  50% { opacity: 0.22; }
}
@keyframes ss-breath-title {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.08); }
}
@keyframes ss-breath-tglow {
  0%, 100% { opacity: 0.35; }
  50% { opacity: 0.95; }
}
@media (prefers-reduced-motion: reduce) {
  .ss-axis-em .ss-axline,
  .ss-axglow,
  .ss-axis-em .ss-axtitle,
  .ss-axtitle-glow {
    animation: none;
  }
}
.ss-axis-em .ss-ticklbl {
  font-weight: 700;
}
.ss-axis-dim {
  opacity: 0.55;
}
.ss-empty {
  font-family: 'Inter', system-ui, sans-serif;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  fill: rgba(245, 240, 230, 0.4);
}
.ss-pt {
  cursor: pointer;
}
.ss-hl {
  pointer-events: none;
}
.ss-glow {
  fill: rgba(245, 199, 94, 0.2);
  stroke: rgba(245, 199, 94, 0.75);
  stroke-width: 1.6;
}
.ss-lit {
  fill: none;
  stroke: rgba(245, 199, 94, 0.85);
  stroke-width: 2px;
  vector-effect: non-scaling-stroke;
}
.ss-labels {
  pointer-events: none;
}
.ss-lbl {
  font-family: 'Inter', system-ui, sans-serif;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  fill: rgba(245, 240, 230, 0.96);
  paint-order: stroke;
  stroke: rgba(0, 0, 0, 0.85);
  stroke-width: 4px;
  stroke-linejoin: round;
}
.ss-leader {
  stroke: rgba(245, 240, 230, 0.9);
  stroke-width: 1.6px;
  vector-effect: non-scaling-stroke;
}
.ss-lbl-hl {
  fill: #f5c75e;
}
</style>
