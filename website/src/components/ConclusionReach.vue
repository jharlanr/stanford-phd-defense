<!-- The Conclusion visual (the director asked for one visual, or one
     combined visual, for the conclusions page and for the conclusions
     thumbnail in the menu card, the same thing or versions of the same
     thing). ONE renderer, two modes: the Conclusion page's figure and
     the menu card's thumb.

     The playback rule: no lake fires another — the 2019
     season PLAYS, 1 May → 30 Sep, and each lake drains on its own
     observed day; a toggle HF | HF + MD picks which classes drain.

     No reach circles (the director removed the
     Christoffersen circle and every circle around the lake drainage
     events: the events are shown without implying anything about
     their 'radius of influence', because that undersells the
     point of the thesis). No circle, no rings, no halo that
     grows to a distance — nothing on the figure is a reach. The EVENTS
     carry it:
       · the stage: central-west Greenland's 2019 lakes as Chapter 3 shows
         them (five mechanism classes, Dunmire outlines), north up, km, a
         rectangular view round CW2019_2394; BedMachine ice margin, land,
         sea, 200 m surface contours;
       · a lake still full = filled in its class colour; on its observed
         day it flashes and blooms — a soft glow of ONE fixed pixel size,
         confined to the lake, that never grows — and settles a FAINTER
         GOLD: a gold outline over a soft gold fill (the director wanted
         the map more obvious about which lakes have drained: a lake
         drains with the gold flash, then stays a fainter gold; the
         flash itself was liked and could be accentuated
         a little more). Full lakes
         keep their class colours, so the colour change itself says
         "drained". Recent drainages stand a little brighter than old
         ones. Tiny lakes are drawn at a
         minimum on-screen size (their own outline, scaled up about the
         lake) so a back row can see each one change;
       · the season strip (page): every drainage in view as one block in
         its week, stacked by class; ahead of the clock a block is a ghost,
         on its day it flashes gold and lights in its class colour — the
         room sees when drainages cluster (the strip stays in class
         colours: it is the per-class tally, like the counts). A
         playhead rides the date;
       · the counts (page, top-right): drained so far / in view, per class;
       · the date clock (top-left), the scale bar, the toggle.
     Everything — the days (the rule is in the bake), the outlines, the
     field — comes from cinematic/scene_conclusion/
     build_conclusion_visual.py's conclusion/reach_v2.json (its reach
     fields are no longer read). No prose: the figure's labels only (the
     date, the counts, the months, the scale bar, the class codes).

     The page plays the season once on arrival, holds 30 Sep, then loops
     calmly — and every loop SWITCHES the drain set, HF → HF + MD → HF …
     (the director wanted it to restart automatically and alternate
     between HF and HF + MD on each loop; the toggle still picks
     by hand, and the loop alternates on from there); the card plays HF
     only, a little faster, with a shorter hold.

     Knobs to tune: the story timings (FIELD_IN … RESET, MODE), the
     drainage gesture (FLASH, BLOOM_PX, the settle), the minimum lake size
     (MIN_PX), the framing (layout(): VIEW_KM on the page, 16.5 km
     half-height on the card), the strip (STRIP_H, BIN_DAYS).

     Cheap: the field (land, sea, contours, margin, scale bar, the strip's
     axis) and the three classes that never drain are painted once per
     resize into offscreen layers; a frame is two drawImage calls, ≤ 67
     lake outlines, a bloom per live drainage and ≤ 67 strip blocks. A
     stalled frame pauses the season rather than skipping it. Reduced
     motion: the season's end, still. Dev: window.__concT pins the story
     clock (seconds) for stills; window.__concPerf counts frame cost. -->
<template>
  <div class="reach" :class="`is-${mode}`">
    <canvas ref="canvas" class="reach-canvas" />
    <template v-if="mode === 'page'">
      <!-- the season clock: a figure label (EssdLakePanels' date style) -->
      <div ref="dateEl" class="reach-date" :style="dateStyle" aria-hidden="true">
        <span ref="dateDay" class="reach-date-day">1 May</span>
        <span class="reach-date-year">2019</span>
      </div>
      <!-- drained so far / in view, per draining class -->
      <div ref="countEl" class="reach-count" :style="countStyle" aria-hidden="true">
        <span class="reach-count-cls" :style="{ color: hfColor }">HF</span>
        <span ref="countHf" class="reach-count-n">0 / 0</span>
        <span ref="countMdWrap" class="reach-count-md">
          <span class="reach-count-cls" :style="{ color: mdColor }">MD</span>
          <span ref="countMd" class="reach-count-n">0 / 0</span>
        </span>
      </div>
      <!-- which classes drain (Additional Work's segmented control) -->
      <div ref="segEl" class="reach-seg" role="tablist" aria-label="Draining classes" :style="segStyle">
        <button
          v-for="o in drainOpts"
          :key="o.value"
          class="reach-seg-btn"
          :class="{ 'reach-seg-btn--on': drainSet === o.value }"
          role="tab"
          :aria-selected="drainSet === o.value"
          @click="setDrain(o.value, $event)"
        >{{ o.label }}</button>
      </div>
    </template>
  </div>
</template>

<script lang="ts">
// Module scope: the figure is fetched and decoded once, shared by every
// mount (the card and the page).
import { mediaUrl } from '../config/media'

// ── the baked figure (the fields this renderer reads) ────────────────
interface ReachJson {
  frame: { q: number }
  season: { t0: string; days: number }
  // [x, y, class, outline (relative), drainage day (-1: none), (unused)]
  lakes: [number, number, number, number[], number, number][]
  margin: number[][]
  land: number[][][]
  sea: number[][][]
  contours: { z: number; lines: number[][] }[]
}
interface Lake {
  x: number
  y: number
  cls: number
  poly: Float32Array // outline, km relative to (x, y)
  ext: number // the outline's larger extent, km
  day: number // observed drainage day from t0 (-1: does not drain here)
  drains: boolean // HF or MD with a day: drawn each frame
}
interface Fig {
  q: number
  lakes: Lake[]
  drainers: number[] // indices of the HF and MD lakes that drain
  days: number // season length (153: 1 May – 30 Sep)
  t0: number // season start, UTC ms
  raw: ReachJson
}

// ── the story (story seconds; MODE.speed maps them to wall seconds) ──
const FIELD_IN = 1.0 // lakes, margin, contours fade in
const DIM0 = 0.5 // the classes that do not drain recede …
const DIM_LEN = 1.0 // … over this long (and stay receded through loops)
const SEASON0 = 1.8 // 1 May
const LOOP0 = 1.55 // each loop (and each toggle) restarts here: field and dim settled
const UI0 = 0.6 // the date, counts and toggle come in from here
const RESET = 1.6 // the calm reset before the next season
// per mode: playback speed, the season's length (story s) and the hold at
// 30 Sep. Page: the season in 22 s (~7 days a second); the card: 15.7 s.
const MODE = {
  page: { speed: 1, season: 22, hold: 2.5 },
  thumb: { speed: 1.4, season: 22, hold: 1.6 },
} as const
// the drainage gesture: a hot gold flash of the lake itself, then a
// fainter gold. The flash was accentuated at the director's request:
// the flash 0.35 → 0.5 s, the bloom 18 → 24 px and
// slower, plus a second, softer halo — both a FIXED pixel size (the
// no-reach rule: nothing grows to a distance).
const FLASH = 0.5 // story s the lake burns hot
const SETTLE = 1.1 // … then its gold eases down to the drained level over this long
const BLOOM_E = 0.42 // the bloom e-folds this fast (it never changes size)
const HALO_E = 0.75 // the softer halo lingers a little longer
const FRESH = 1.6 // a drainage stays "recent" (brighter outline) this long
const BLOOM_PX = { page: 24, thumb: 12 } // the bloom's radius, px — fixed, not km
const HALO_PX = { page: 46, thumb: 22 } // the softer halo's radius, px — fixed
const MIN_PX = { page: 9, thumb: 4 } // a lake is drawn at least this big, px
const LINE_PX = { page: 2.6, thumb: 1.2 } // the drained outline
// the drained lake's gold: outline / fill alpha once settled ("a fainter
// gold" — still plainly gold from the back row, faint only beside the flash)
const DRAINED_LINE_A = 0.78
const DRAINED_FILL_A = 0.4
// the page's view: at least this many km across × tall round 2394
const VIEW_KM = { w: 72, h: 58 }
// the season strip (page): height px, and days per block column
const STRIP_H = 118
const BIN_DAYS = 7

function clamp01(u: number): number {
  return u < 0 ? 0 : u > 1 ? 1 : u
}
function smooth(u: number): number {
  const x = clamp01(u)
  return x * x * (3 - 2 * x)
}

let figP: Promise<Fig> | null = null
/** One fetch shared by every mount (the card and the page). */
function loadFig(): Promise<Fig> {
  if (!figP) {
    figP = fetch(mediaUrl('conclusion/reach_v2.json'))
      .then((r) => {
        if (!r.ok) throw new Error(`reach_v2.json ${r.status}`)
        return r.json() as Promise<ReachJson>
      })
      .then(decode)
    figP.catch(() => {
      figP = null
    })
  }
  return figP
}

function decode(j: ReachJson): Fig {
  const q = j.frame.q
  const lakes: Lake[] = j.lakes.map(([x, y, cls, flat, day]) => {
    const poly = new Float32Array(flat.length)
    let x0 = Infinity
    let x1 = -Infinity
    let y0 = Infinity
    let y1 = -Infinity
    for (let i = 0; i < flat.length; i++) {
      const v = flat[i] / q
      poly[i] = v
      if (i % 2 === 0) {
        if (v < x0) x0 = v
        if (v > x1) x1 = v
      } else {
        if (v < y0) y0 = v
        if (v > y1) y1 = v
      }
    }
    const drains = (cls === HF || cls === MD) && day >= 0
    return { x: x / q, y: y / q, cls, poly, ext: Math.max(x1 - x0, y1 - y0, 0), day, drains }
  })
  const drainers: number[] = []
  lakes.forEach((l, i) => {
    if (l.drains) drainers.push(i)
  })
  return {
    q,
    lakes,
    drainers,
    days: j.season.days,
    t0: Date.parse(`${j.season.t0}T00:00:00Z`),
    raw: j,
  }
}

// ── palette ──────────────────────────────────────────────────────────
const CLASS_COLOR = ['#e8524a', '#4caf50', '#42a5f5', '#ff9800', '#ab47bc'] // ND HF MD LD CD
const HF = 1
const MD = 2
const HOT = 'rgb(255, 244, 214)'
const GOLD = 'rgb(244, 207, 106)'
const GOLD_DEEP = 'rgb(232, 185, 74)' // --gold: the drained fill
const INK = 'rgba(245, 240, 230, 0.82)'
const INK_SOFT = 'rgba(245, 240, 230, 0.7)' // (0.42 washed out on a projector)
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

type DrainSet = 'hf' | 'hfmd'
const DRAIN_OPTS: { value: DrainSet; label: string }[] = [
  { value: 'hf', label: 'HF' },
  { value: 'hfmd', label: 'HF + MD' },
]
</script>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = withDefaults(defineProps<{ mode?: 'page' | 'thumb' }>(), { mode: 'page' })
const canvas = ref<HTMLCanvasElement | null>(null)
const dateDay = ref<HTMLSpanElement | null>(null)
const dateEl = ref<HTMLDivElement | null>(null)
const countEl = ref<HTMLDivElement | null>(null)
const countHf = ref<HTMLSpanElement | null>(null)
const countMd = ref<HTMLSpanElement | null>(null)
const countMdWrap = ref<HTMLSpanElement | null>(null)
const segEl = ref<HTMLDivElement | null>(null)
// HF by default; the card is always HF
const drainSet = ref<DrainSet>('hf')
/** Which loop of the season is playing (0 = the first play); the page
 *  flips the drain set each time it changes. */
let loopIdx = 0
const dateStyle = ref<Record<string, string>>({ visibility: 'hidden' })
const countStyle = ref<Record<string, string>>({ visibility: 'hidden' })
const segStyle = ref<Record<string, string>>({ visibility: 'hidden' })
const drainOpts = DRAIN_OPTS
const hfColor = CLASS_COLOR[HF]
const mdColor = CLASS_COLOR[MD]

// ── state ────────────────────────────────────────────────────────────
let fig: Fig | null = null
let ctx: CanvasRenderingContext2D | null = null
let rafId = 0
let t0 = 0
let lastNow = 0 // the previous frame's timestamp
let ro: ResizeObserver | null = null
let reduced = false
let cw = 2
let ch = 2
let dpr = 1
let s = 10 // px per km
let ox = 0 // 2394, px
let oy = 0
// the map's rectangle, px — on the page exactly VIEW_KM round 2394, so
// every screen shows (and counts) the same lakes; the strip sits under it
let mapL = 0
let mapR = 2
let mapTop = 0
let mapBot = 2
let field: HTMLCanvasElement | null = null // land, sea, contours, margin, scale bar, strip axis
let lakesRest: HTMLCanvasElement | null = null // ND, LD, CD: they never drain here
let paths: (Path2D | null)[] = [] // the HF and MD outlines, px (null: the other classes)
let vis: Float32Array = new Float32Array(0) // per lake: the view's edge fade at its centre
let bloom: HTMLCanvasElement | null = null
let halo: HTMLCanvasElement | null = null // the bloom's softer, wider partner
// the strip: per draining lake in view, its block (px), and the totals
let blocks: { i: number; x: number; y: number; w: number; h: number }[] = []
let inView = { hf: 0, md: 0 }
let stripX0 = 0
let stripX1 = 1
let stripTop = 0
let stripBase = 0
let mdOn = 0 // MD's share of the draining look (eases to the toggle)
let shownDay = -1 // the day the clock label shows
let shownUi = -1 // the DOM labels' opacity, as last written
let shownHf = -1
let shownMd = -1
let shownMdOn = -1
let dead = false

const px = (xKm: number) => ox + xKm * s
const py = (yKm: number) => oy - yKm * s
const dayX = (d: number) => stripX0 + (d / fig!.days) * (stripX1 - stripX0)

function layout() {
  const c = canvas.value
  if (!c) return
  const r = c.getBoundingClientRect()
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  cw = Math.max(2, r.width)
  ch = Math.max(2, r.height)
  c.width = Math.round(cw * dpr)
  c.height = Math.round(ch * dpr)
  if (props.mode === 'page') {
    // the map fills the figure above the strip; the date and the counts
    // ride its top edge
    const top = 34
    const bot = Math.max(top + 40, ch - STRIP_H - 10)
    s = Math.min(cw / VIEW_KM.w, (bot - top) / VIEW_KM.h)
    ox = cw / 2
    oy = (top + bot) / 2
    mapL = ox - (VIEW_KM.w / 2) * s
    mapR = ox + (VIEW_KM.w / 2) * s
    mapTop = oy - (VIEW_KM.h / 2) * s
    mapBot = oy + (VIEW_KM.h / 2) * s
  } else {
    // the card: a wide strip, 2394 clear of the title in the bottom-left
    mapL = 0
    mapR = cw
    mapTop = 0
    mapBot = ch
    s = ch / 2 / 16.5
    ox = cw * 0.5
    oy = ch * 0.42
  }
  paintStatic()
  if (reduced) draw(performance.now())
}

function layer(): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const el = document.createElement('canvas')
  el.width = Math.round(cw * dpr)
  el.height = Math.round(ch * dpr)
  const g = el.getContext('2d')!
  g.setTransform(dpr, 0, 0, dpr, 0, 0)
  return [el, g]
}

type PathSink = Pick<Path2D, 'moveTo' | 'lineTo' | 'closePath'>
function tracePoly(g: PathSink, flat: number[], q: number, close: boolean) {
  for (let i = 0; i < flat.length; i += 2) {
    const x = px(flat[i] / q)
    const y = py(flat[i + 1] / q)
    if (i === 0) g.moveTo(x, y)
    else g.lineTo(x, y)
  }
  if (close) g.closePath()
}

/** A lake's outline, px — scaled up about the lake if it would be drawn
 *  smaller than MIN_PX (its own shape, never a symbol). */
function lakePath<P extends PathSink>(l: Lake, p: P): P {
  const k = Math.max(1, MIN_PX[props.mode] / Math.max(l.ext * s, 0.01))
  const n = l.poly.length
  for (let i = 0; i < n; i += 2) {
    const x = px(l.x + l.poly[i] * k)
    const y = py(l.y + l.poly[i + 1] * k)
    if (i === 0) p.moveTo(x, y)
    else p.lineTo(x, y)
  }
  p.closePath()
  return p
}

// The view's edge fade, px: page = the map rectangle's four sides; card =
// the strip's left and right ends.
const fadePx = () => (props.mode === 'page' ? 5 * s : cw * 0.06)
function edgeFade(xPx: number, yPx: number): number {
  const f = fadePx()
  const fx = Math.min(clamp01((xPx - mapL) / f), clamp01((mapR - xPx) / f))
  if (props.mode !== 'page') return yPx < -4 || yPx > ch + 4 ? 0 : fx
  return fx * Math.min(clamp01((yPx - mapTop) / f), clamp01((mapBot - yPx) / f))
}

/** Fade a layer out towards the edge of the view. */
function vignette(g: CanvasRenderingContext2D) {
  const f = fadePx()
  g.save()
  g.globalCompositeOperation = 'destination-in'
  const w = mapR - mapL
  const gx = g.createLinearGradient(mapL, 0, mapR, 0)
  gx.addColorStop(0, 'rgba(0,0,0,0)')
  gx.addColorStop(f / w, 'rgba(0,0,0,1)')
  gx.addColorStop(1 - f / w, 'rgba(0,0,0,1)')
  gx.addColorStop(1, 'rgba(0,0,0,0)')
  g.fillStyle = gx
  g.fillRect(0, 0, cw, ch)
  if (props.mode === 'page') {
    const h = mapBot - mapTop
    const gy = g.createLinearGradient(0, mapTop, 0, mapBot)
    gy.addColorStop(0, 'rgba(0,0,0,0)')
    gy.addColorStop(f / h, 'rgba(0,0,0,1)')
    gy.addColorStop(1 - f / h, 'rgba(0,0,0,1)')
    gy.addColorStop(1, 'rgba(0,0,0,0)')
    g.fillStyle = gy
    g.fillRect(0, 0, cw, ch)
  }
  g.restore()
}

function paintStatic() {
  if (!fig) return
  const j = fig.raw
  const q = fig.q
  const page = props.mode === 'page'
  // the scale bar (page): bottom-left of the map — the toggle mirrors it
  // on the right
  const barX = mapL + 6
  const barY = mapBot - 14
  // ── the field ──
  {
    const [el, g] = layer()
    g.fillStyle = 'rgba(2, 4, 9, 0.55)' // sea: darker than the ice
    for (const poly of j.sea) {
      g.beginPath()
      for (const ring of poly) tracePoly(g, ring, q, true)
      g.fill('evenodd')
    }
    g.fillStyle = page ? 'rgba(245, 240, 230, 0.03)' : 'rgba(245, 240, 230, 0.022)' // ice-free land: a warm lift
    for (const poly of j.land) {
      g.beginPath()
      for (const ring of poly) tracePoly(g, ring, q, true)
      g.fill('evenodd')
    }
    g.lineJoin = 'round'
    g.strokeStyle = 'rgba(245, 240, 230, 0.075)'
    g.lineWidth = 0.8
    for (const c of j.contours) {
      g.beginPath()
      for (const ln of c.lines) tracePoly(g, ln, q, false)
      g.stroke()
    }
    g.strokeStyle = page ? 'rgba(245, 240, 230, 0.45)' : 'rgba(245, 240, 230, 0.3)'
    g.lineWidth = page ? 1.7 : 0.9
    g.beginPath()
    for (const ln of j.margin) tracePoly(g, ln, q, false)
    g.stroke()
    vignette(g)
    if (page) {
      // the scale bar
      const L = 10 * s
      g.strokeStyle = INK_SOFT
      g.lineWidth = 2
      g.beginPath()
      g.moveTo(barX, barY - 5)
      g.lineTo(barX, barY)
      g.lineTo(barX + L, barY)
      g.lineTo(barX + L, barY - 5)
      g.stroke()
      g.font = '600 16px Inter, system-ui, sans-serif'
      g.fillStyle = INK
      g.textBaseline = 'middle'
      g.textAlign = 'left'
      g.fillText('10 km', barX + L + 9, barY - 1)
      // the strip's axis: a baseline, month ticks and names
      stripX0 = mapL + 6
      stripX1 = mapR - 6
      stripBase = mapBot + STRIP_H - 16
      stripTop = mapBot + 28
      g.strokeStyle = INK_SOFT
      g.lineWidth = 1.8
      g.beginPath()
      g.moveTo(stripX0, stripBase + 0.5)
      g.lineTo(stripX1, stripBase + 0.5)
      g.stroke()
      g.font = '600 16px Inter, system-ui, sans-serif'
      g.fillStyle = 'rgba(245, 240, 230, 0.88)'
      g.textBaseline = 'middle'
      g.textAlign = 'left'
      const t0d = new Date(fig.t0)
      for (let m = 0; m < 5; m++) {
        const d = (Date.UTC(t0d.getUTCFullYear(), t0d.getUTCMonth() + m, 1) - fig.t0) / 86400e3
        const x = dayX(d)
        g.beginPath()
        g.moveTo(x + 0.5, stripBase)
        g.lineTo(x + 0.5, stripBase + 6)
        g.stroke()
        g.fillText(MONTHS[(t0d.getUTCMonth() + m) % 12], x + 5, stripBase + 14)
      }
    }
    field = el
  }
  // ── the three classes that never drain here, on their own layer ──
  {
    const [el, g] = layer()
    for (const l of fig.lakes) {
      if (l.drains) continue
      g.fillStyle = CLASS_COLOR[l.cls]
      g.beginPath()
      lakePath(l, g)
      g.fill()
    }
    vignette(g)
    lakesRest = el
  }
  // ── HF and MD: drawn each frame (they drain) ──
  paths = fig.lakes.map((l) => (l.drains ? lakePath(l, new Path2D()) : null))
  vis = new Float32Array(fig.lakes.map((l) => edgeFade(px(l.x), py(l.y))))
  // ── the strip's blocks: one per draining lake in view (centre inside
  // the edge fade's midline), stacked by week, HF under MD ──
  blocks = []
  inView = { hf: 0, md: 0 }
  if (page) {
    const bins = Math.ceil(fig.days / BIN_DAYS)
    const stack = new Array<number>(bins).fill(0)
    const mine: { i: number; b: number; k: number }[] = []
    for (const i of fig.drainers) {
      const l = fig.lakes[i]
      if (vis[i] < 0.5) continue
      if (l.cls === HF) inView.hf++
      else inView.md++
      mine.push({ i, b: Math.min(bins - 1, Math.floor(l.day / BIN_DAYS)), k: 0 })
    }
    // each week: HF at the bottom, MD on top, each by day
    const L = fig.lakes
    mine.sort((a, b) => a.b - b.b || L[a.i].cls - L[b.i].cls || L[a.i].day - L[b.i].day)
    for (const e of mine) e.k = stack[e.b]++
    const most = Math.max(1, ...stack)
    const colW = (stripX1 - stripX0) / (fig.days / BIN_DAYS)
    const bh = Math.min(16, (stripBase - 2 - stripTop) / most)
    for (const { i, b, k } of mine) {
      blocks.push({ i, x: stripX0 + b * colW + 1.5, y: stripBase - 2 - (k + 1) * bh, w: colW - 3, h: bh - 2 })
    }
  }
  // ── the figure's DOM labels, placed on the figure's own geometry ──
  if (page) {
    // (their opacity is paint()'s, written straight to the elements, so it
    // never enters these bindings)
    dateStyle.value = { left: `${barX}px`, top: `${mapTop - 4}px` }
    countStyle.value = { right: `${cw - mapR + 6}px`, top: `${mapTop - 4}px` }
    // the toggle: on the map's top edge right after the date (its longest,
    // "30 Sep 2019", ends ~125 px in), clear of the counts at 1280 with
    // MD on (at the bottom-right a rim lake hid under it)
    segStyle.value = {
      left: `${barX + 140}px`,
      top: `${mapTop - 15}px`,
      transform: 'translateY(-50%)',
    }
    shownHf = shownMd = shownMdOn = -1
  }
  // ── the bloom: a soft disc, drawn at one fixed pixel size ──
  if (!bloom) {
    const el = document.createElement('canvas')
    el.width = el.height = 64
    const g = el.getContext('2d')!
    const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32)
    grad.addColorStop(0, 'rgba(255, 244, 214, 0.95)')
    grad.addColorStop(0.35, 'rgba(244, 207, 106, 0.5)')
    grad.addColorStop(1, 'rgba(244, 207, 106, 0)')
    g.fillStyle = grad
    g.fillRect(0, 0, 64, 64)
    bloom = el
  }
  if (!halo) {
    const el = document.createElement('canvas')
    el.width = el.height = 64
    const g = el.getContext('2d')!
    const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32)
    grad.addColorStop(0, 'rgba(244, 207, 106, 0.55)')
    grad.addColorStop(0.5, 'rgba(232, 185, 74, 0.22)')
    grad.addColorStop(1, 'rgba(232, 185, 74, 0)')
    g.fillStyle = grad
    g.fillRect(0, 0, 64, 64)
    halo = el
  }
}

// ── the season clock ─────────────────────────────────────────────────
const dayLen = () => MODE[props.mode].season / fig!.days // story s per day
const seasonEnd = () => SEASON0 + MODE[props.mode].season // 30 Sep is over
const cycleEnd = () => seasonEnd() + MODE[props.mode].hold + RESET
/** Story second a lake drains: a third into its day, so the clock reads its date. */
const drainT = (day: number) => SEASON0 + (day + 0.35) * dayLen()

/** Story seconds from wall-clock seconds: one full play, then calm
 *  loops of the season (the field stays). */
function storyTime(sec: number): number {
  const t = sec * MODE[props.mode].speed
  const end = cycleEnd()
  if (t <= end) return t
  return LOOP0 + ((t - LOOP0) % (end - LOOP0))
}

/** The date label: "16 Jun" (the year sits beside it, fixed). */
function showDay(day: number) {
  if (day === shownDay || !dateDay.value || !fig) return
  shownDay = day
  const d = new Date(fig.t0 + day * 86400e3)
  dateDay.value.textContent = `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`
}

/** The counts: drained so far / in view, per class. */
function showCounts(nHf: number, nMd: number) {
  if (nHf !== shownHf && countHf.value) {
    shownHf = nHf
    countHf.value.textContent = `${nHf} / ${inView.hf}`
  }
  if (nMd !== shownMd && countMd.value) {
    shownMd = nMd
    countMd.value.textContent = `${nMd} / ${inView.md}`
  }
  const on = Math.round(mdOn * 100) / 100
  if (on !== shownMdOn && countMdWrap.value) {
    shownMdOn = on
    countMdWrap.value.style.opacity = String(on)
    countMdWrap.value.style.display = on > 0 ? '' : 'none'
  }
}

/** The toggle: which classes drain. The season starts again from 1 May. */
function setDrain(v: DrainSet, e?: MouseEvent) {
  // keep the site's keys (the presenter remote) off the button
  const btn = e?.currentTarget as HTMLElement | null
  btn?.blur()
  if (drainSet.value === v) return
  drainSet.value = v
  if (reduced) {
    mdOn = v === 'hfmd' ? 1 : 0
    draw(performance.now())
    return
  }
  const now = performance.now()
  t0 = now - (LOOP0 / MODE[props.mode].speed) * 1000
  lastNow = now
  loopIdx = 0
}

/** The loop the story clock is in: 0 through the first play, then one
 *  more per wrap (storyTime's modulo). */
function loopOf(sec: number): number {
  const t = sec * MODE[props.mode].speed
  const end = cycleEnd()
  return t <= end ? 0 : Math.floor((t - LOOP0) / (end - LOOP0))
}

function draw(now: number) {
  if (dead || !ctx) return
  if (!reduced) rafId = requestAnimationFrame(draw)
  // A stall (the app booting under a deep link, a tab switch) pauses the
  // story instead of skipping it: the clock only runs on drawn frames.
  const dtWall = lastNow > 0 ? now - lastNow : 16
  if (lastNow > 0 && dtWall > 100) t0 += dtWall - 1000 / 60
  lastNow = now
  // each loop of the season switches the drain set (page only): HF, then
  // HF + MD, then HF … — the wrap lands at LOOP0, before 1 May, so the
  // switch is only MD's population easing between its two looks
  if (props.mode === 'page' && !reduced) {
    const k = loopOf(Math.max(0, (now - t0) / 1000))
    if (k !== loopIdx) {
      loopIdx = k
      drainSet.value = drainSet.value === 'hf' ? 'hfmd' : 'hf'
    }
  }
  // MD eases into (or out of) the draining look over ~0.4 s
  const mdTarget = props.mode === 'page' && drainSet.value === 'hfmd' ? 1 : 0
  mdOn = reduced ? mdTarget : mdOn + (mdTarget - mdOn) * (1 - Math.exp(-Math.min(dtWall, 100) / 120))
  if (Math.abs(mdTarget - mdOn) < 0.002) mdOn = mdTarget
  const c0 = import.meta.env.DEV ? performance.now() : 0
  paint(now)
  if (import.meta.env.DEV) {
    // dev-only frame cost probe: window.__concPerf[mode] = { n, sum, max, over2 } ms
    const w = window as unknown as { __concPerf?: Record<string, { n: number; sum: number; max: number; over2: number }> }
    const pf = ((w.__concPerf ??= {})[props.mode] ??= { n: 0, sum: 0, max: 0, over2: 0 })
    const dt = performance.now() - c0
    pf.n++
    pf.sum += dt
    if (dt > 2) pf.over2 = (pf.over2 ?? 0) + 1
    if (dt > pf.max) pf.max = dt
  }
}

function paint(now: number) {
  if (!ctx) return
  const g = ctx
  g.setTransform(dpr, 0, 0, dpr, 0, 0)
  g.clearRect(0, 0, cw, ch)
  if (!fig || !field || !lakesRest || !bloom || !halo) return
  const F = fig
  const page = props.mode === 'page'
  const m = MODE[props.mode]
  const end = seasonEnd()
  const pin = import.meta.env.DEV ? (window as unknown as { __concT?: number }).__concT : undefined
  const t = reduced
    ? end + m.hold - 0.01
    : typeof pin === 'number'
      ? pin
      : storyTime(Math.max(0, (now - t0) / 1000))
  // the reset: what the season did recedes, then it plays again
  const live = 1 - smooth((t - (end + m.hold)) / RESET)
  const fieldA = smooth(t / FIELD_IN)
  const dim = smooth((t - DIM0) / DIM_LEN)
  const restA = fieldA * (0.85 - 0.6 * dim) // the population that does not drain
  const ui = Math.round(smooth((t - UI0) / 0.6) * 100) / 100
  const dl = dayLen()
  const dayNow = Math.min(F.days, Math.max(0, (t - SEASON0) / dl))
  if (page) {
    showDay(Math.min(F.days - 1, Math.floor(dayNow)))
    if (ui !== shownUi && dateEl.value && segEl.value && countEl.value) {
      shownUi = ui
      dateEl.value.style.opacity = segEl.value.style.opacity = countEl.value.style.opacity = String(ui)
    }
  }

  // ── the field and the classes that never drain ──
  g.globalAlpha = fieldA
  g.drawImage(field, 0, 0, cw, ch)
  g.globalAlpha = restA
  g.drawImage(lakesRest, 0, 0, cw, ch)

  // ── the HF and MD lakes: full → a gold flash → a fainter gold ──
  const mdDim = 1 - mdOn // MD's share of the dim population
  const lw = LINE_PX[props.mode]
  const bR = BLOOM_PX[props.mode]
  const hR = HALO_PX[props.mode]
  let nHf = 0
  let nMd = 0
  g.lineJoin = 'round'
  for (const i of F.drainers) {
    const l = F.lakes[i]
    const w = vis[i]
    if (w <= 0) continue
    const path = paths[i]!
    const share = l.cls === MD ? mdOn : 1 // how much this lake drains
    const col = CLASS_COLOR[l.cls]
    const tau = t - drainT(l.day)
    // 0 = still full (or refilled in the reset), 1 = drained
    const gone = tau < 0 ? 0 : live
    if (gone > 0.5 && w >= 0.5) {
      if (l.cls === HF) nHf++
      else nMd++
    }
    if (l.cls === MD && mdDim > 0) {
      // MD when it does not drain: part of the dim population
      g.globalAlpha = restA * w * mdDim
      g.fillStyle = col
      g.fill(path)
    }
    const a = fieldA * w * share
    if (a < 0.004) continue
    // full: filled in its class colour
    if (gone < 1) {
      g.globalAlpha = 0.95 * a * (1 - gone)
      g.fillStyle = col
      g.fill(path)
    }
    if (gone > 0) {
      // drained: a fainter gold — a soft gold fill under a gold outline;
      // the fill starts full gold and eases down to its drained level
      // after the flash; a recent drainage stands brighter than an old one
      const fresh = 1 - smooth((tau - FRESH) / 1.2)
      const settle = 1 - smooth((tau - FLASH) / SETTLE) // 1 in the flash → 0
      g.globalAlpha = a * gone * (DRAINED_FILL_A + (0.95 - DRAINED_FILL_A) * settle)
      g.fillStyle = GOLD_DEEP
      g.fill(path)
      g.globalAlpha = a * gone * (DRAINED_LINE_A + (1 - DRAINED_LINE_A) * fresh)
      g.strokeStyle = GOLD
      g.lineWidth = lw * (1 + 0.35 * fresh)
      g.stroke(path)
      // the drain itself: the lake burns hot, a fixed bloom on it and a
      // softer, wider halo behind (both one pixel size, never growing)
      if (tau < FLASH) {
        g.globalAlpha = a * gone * (1 - smooth(tau / FLASH))
        g.fillStyle = HOT
        g.fill(path)
      }
      const hA = Math.exp(-tau / HALO_E) * a * gone * w * 0.55
      const bA = Math.exp(-tau / BLOOM_E) * a * gone * w
      if (bA > 0.01 || hA > 0.01) {
        g.globalCompositeOperation = 'lighter'
        const cx = px(l.x)
        const cy = py(l.y)
        if (hA > 0.01) {
          g.globalAlpha = hA
          g.drawImage(halo!, cx - hR, cy - hR, 2 * hR, 2 * hR)
        }
        if (bA > 0.01) {
          g.globalAlpha = Math.min(1, bA * 1.15)
          g.drawImage(bloom, cx - bR, cy - bR, 2 * bR, 2 * bR)
        }
        g.globalCompositeOperation = 'source-over'
      }
    }
  }

  // ── the season strip (page): a block per drainage in view ──
  if (page) {
    g.globalAlpha = 1
    for (const b of blocks) {
      const l = F.lakes[b.i]
      const share = l.cls === MD ? mdOn : 1
      if (share < 0.01) continue
      const tau = t - drainT(l.day)
      const on = tau < 0 ? 0 : live
      const col = CLASS_COLOR[l.cls]
      // ahead of the clock: a ghost outline
      g.globalAlpha = ui * share * (0.5 - 0.5 * on)
      g.strokeStyle = col
      g.lineWidth = 1.5
      g.strokeRect(b.x + 0.75, b.y + 0.75, b.w - 1.5, b.h - 1.5)
      if (on > 0) {
        g.globalAlpha = ui * share * on * 0.95
        g.fillStyle = tau < FLASH ? GOLD : col // the gold flash, then its class
        g.fillRect(b.x, b.y, b.w, b.h)
      }
    }
    // the playhead: the clock's day on the strip
    if (t > SEASON0 - 0.3) {
      const x = Math.round(dayX(dayNow)) + 0.5
      g.globalAlpha = ui * live * smooth((t - SEASON0 + 0.3) / 0.3)
      g.strokeStyle = GOLD
      g.lineWidth = 2
      g.beginPath()
      g.moveTo(x, stripTop - 4)
      g.lineTo(x, stripBase + 4)
      g.stroke()
    }
    showCounts(nHf, nMd)
  }
  g.globalAlpha = 1
}

onMounted(() => {
  const c = canvas.value
  if (!c) return
  ctx = c.getContext('2d')
  reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
  ro = new ResizeObserver(layout)
  ro.observe(c)
  loadFig()
    .then((f) => {
      if (dead) return
      fig = f
      layout()
      t0 = performance.now()
      if (reduced) draw(t0)
      else {
        cancelAnimationFrame(rafId)
        rafId = requestAnimationFrame(draw)
      }
      // canvas text waits for the webfont; repaint once it is in
      if (props.mode === 'page') document.fonts?.load('500 15px Inter').then(() => { if (!dead) { paintStatic(); if (reduced) draw(performance.now()) } })
    })
    .catch((e) => console.warn('[ConclusionReach]', e))
})

onBeforeUnmount(() => {
  dead = true
  cancelAnimationFrame(rafId)
  ro?.disconnect()
  ro = null
  ctx = null
})
</script>

<style scoped>
.reach {
  position: relative;
  width: 100%;
  height: 100%;
}
.reach.is-thumb {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 50% 42%, #0d1018 0%, #050505 75%);
}
.reach-canvas {
  display: block;
  width: 100%;
  height: 100%;
}

/* the season clock: EssdLakePanels' date (day + a dimmer year) */
.reach-date,
.reach-count {
  position: absolute;
  transform: translateY(-100%);
  opacity: 0; /* paint() brings them in with the field */
  display: flex;
  align-items: baseline;
  gap: 0.4em;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1.15rem;
  font-weight: 500;
  color: #f5f0e6;
  font-variant-numeric: tabular-nums;
  pointer-events: none;
  white-space: nowrap;
}
.reach-date-year {
  font-size: 0.8em;
  color: rgba(245, 240, 230, 0.82);
}

/* the counts: class code in its colour, drained / in view */
.reach-count-cls {
  font-size: 0.8em;
  font-weight: 600;
  letter-spacing: 0.08em;
}
.reach-count-md {
  display: inline-flex;
  align-items: baseline;
  gap: 0.4em;
  margin-left: 0.9em;
}

/* the two-stop toggle — Additional Work's segmented control, at figure
   scale: pill track, gold-filled active stop, uppercase Inter */
.reach-seg {
  position: absolute;
  transform: translateY(-50%);
  opacity: 0; /* paint() brings it in with the field */
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  padding: 0.22rem;
  border: 1.5px solid rgba(232, 185, 74, 0.6);
  border-radius: 999px;
  /* near-opaque (Chapter 3's season pill): a rim lake may pass under it */
  background: rgba(8, 7, 6, 0.84);
}
.reach-seg-btn {
  background: transparent;
  border: 1px solid transparent;
  border-radius: 999px;
  color: rgba(244, 207, 106, 0.92);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  white-space: nowrap;
  padding: 0.32rem 0.9rem;
  cursor: pointer;
  transition: color 0.2s, background 0.2s, border-color 0.2s;
}
.reach-seg-btn:hover {
  color: var(--gold-bright);
}
.reach-seg-btn--on,
.reach-seg-btn--on:hover {
  color: #0a0a0a;
  background: var(--gold-bright);
  border-color: var(--gold-bright);
}
</style>
