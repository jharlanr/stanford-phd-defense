<template>
  <!-- Ch.3 beat 0: the ESSD paper's Fig. 4b, live.
       Five callout panels — one per drainage-class example lake — each
       joined to its lake on the globe by a leader line, all five stepping
       through ONE shared season clock (the parent's `day`; the bottom
       timebar drives it). The director wanted no black tiles —
       the clock steps only through dates on which some lake has a new
       valid frame, two a second, and a lake with none HOLDS its last one
       (its own date quietly bottom-right); the clock's date is stamped on
       every panel, its p_water curve ticking underneath. Panels are OPAQUE,
       ever so slightly faded at rest; hovering a panel OR its lake on
       the globe brings it to full colour with a lit outline; a click
       pins it. While one is lit (hovered, lake-hovered or pinned) the
       OTHERS step back a little — a touch of opacity and colour off,
       their leaders too — to accentuate the one under the pointer (the
       director's request); with nothing lit, nothing moves.
       Placement is SOLVED per viewport (see the solver below):
       as big as they can be without overlapping each other, the lake
       polygons, the nav, or a neighbour's leader — seeded by the director's
       sketch of where each should sit. Labels are the figure's own. -->
  <div class="elp-root" :class="{ 'elp-hidden': props.opacity <= 0.001 || !solved || !allReady }">
    <svg class="elp-lines" :viewBox="`0 0 ${vw} ${vh}`" preserveAspectRatio="none">
      <template v-for="p in placed" :key="`ln-${p.id}`">
        <line
          v-if="p.anchor"
          :x1="p.anchor.x" :y1="p.anchor.y" :x2="p.contact.x" :y2="p.contact.y"
          :stroke="p.color"
          :class="['elp-line', { 'elp-line-lit': isLit(p.id), 'elp-line-back': isBack(p.id) }]"
        />
        <circle
          v-if="p.anchor"
          :cx="p.anchor.x" :cy="p.anchor.y" r="3.4"
          :fill="p.color"
          :class="['elp-dot', { 'elp-line-lit': isLit(p.id), 'elp-line-back': isBack(p.id) }]"
        />
      </template>
    </svg>

    <div
      v-for="p in placed"
      :key="p.id"
      class="elp-panel"
      :class="{ 'elp-lit': isLit(p.id), 'elp-back': isBack(p.id), 'elp-pinned': pinnedId === p.id, 'elp-idle': isIdle(p.id) }"
      :style="{
        left: p.rect.x + 'px', top: p.rect.y + 'px',
        width: p.rect.w + 'px', height: p.rect.h + 'px',
        '--acc': p.color,
      }"
      @mouseenter="hoverId = p.id; $emit('hover', p.id)"
      @mouseleave="hoverId = null; $emit('hover', null)"
      @click="togglePin(p.id)"
    >
      <div class="elp-head">
        <span class="elp-id">{{ p.id }}</span>
        <span class="elp-class" :style="{ color: p.color }">{{ p.className }}</span>
      </div>
      <div class="elp-frame">
        <video
          :ref="(el) => setVideo(p.id, el as HTMLVideoElement | null)"
          class="elp-video"
          :src="p.src"
          muted playsinline preload="auto"
          @loadeddata="onLoaded(p.id)"
        />
        <!-- the clock's date — the same on all five panels -->
        <div class="elp-date">
          <span class="elp-date-day">{{ clockLabel }}</span>
          <span class="elp-date-year">2019</span>
        </div>
        <!-- a held frame says when it was taken (a figure label) -->
        <div v-if="heldLabel(p.id)" class="elp-held">{{ heldLabel(p.id) }}</div>
      </div>
      <!-- p_water over the season — the Fig. 4a strip; marker = the clock -->
      <svg class="elp-curve" :viewBox="`0 0 ${CW} ${CH}`" preserveAspectRatio="none">
        <path :d="areaPath(p.id)" :fill="p.color" class="elp-area" />
        <path :d="linePath(p.id)" :stroke="p.color" class="elp-curveline" />
        <line
          :x1="markerX" :y1="2" :x2="markerX" :y2="CH - CURVE_B"
          class="elp-marker"
        />
        <text :x="2" :y="CH - 2" class="elp-tick">{{ fmt(props.t0) }}</text>
        <text :x="CW - 2" :y="CH - 2" text-anchor="end" class="elp-tick">{{ lastTick }}</text>
      </svg>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { mediaUrl } from '../config/media'

/** One panel per featured lake; `slot` = where the director wants the panel's
 *  CENTRE, in viewport fractions (from a sketch). The solver
 *  keeps each panel as close to its slot as the constraints allow. */
export interface PanelLake {
  id: string
  cls: string
  className: string
  color: string
  slot: { x: number; y: number }
}

const props = defineProps<{
  lakes: PanelLake[]
  /** Lake under the pointer on the globe (Globe's lake-beacon-hover). */
  globeHoverId: string | null
  /** A lake clicked on the globe — {id, seq}; seq bumps per click. */
  globeClick: { id: string; seq: number } | null
  /** Panel + line opacity (0 → 1 as the beat lands). */
  opacity: number
  /** The shared season day (0 = t0). */
  day: number
  /** ISO date of day 0 (the season's first day). */
  t0: string
}>()

const emit = defineEmits<{
  /** Pointer over a panel → the parent pulses that lake on the globe. */
  hover: [id: string | null]
  /** The season clock's dates (days since t0, ascending) once known. */
  clock: [days: number[]]
  /** The panels can be seen: placed, and every movie has a frame. */
  ready: [value: boolean]
}>()

const vw = ref(window.innerWidth)
const vh = ref(window.innerHeight)
function onResize(): void {
  vw.value = window.innerWidth
  vh.value = window.innerHeight
  solvedFor = null
}

const hoverId = ref<string | null>(null)
const pinnedId = ref<string | null>(null)
function isLit(id: string): boolean {
  return hoverId.value === id || props.globeHoverId === id || pinnedId.value === id
}
/** Is any of the five lit? (hovered here, hovered on the globe, or pinned) */
const anyLit = computed(() => props.lakes.some((lk) => isLit(lk.id)))
/** The panels that step back: everything NOT lit while something is. A
 *  pinned panel is lit, so it stays forward while another is hovered. */
function isBack(id: string): boolean {
  return anyLit.value && !isLit(id)
}
function togglePin(id: string): void {
  pinnedId.value = pinnedId.value === id ? null : id
}
watch(
  () => props.globeClick,
  (c, old) => {
    if (!c || c.seq === old?.seq) return
    togglePin(c.id)
  },
)

// ── sidecars ──────────────────────────────────────────────────────────
// Beat 0 plays the VALID-ONLY movies (ch03/lakes_valid/, baked by
// cinematic/scene_ch03/build_callout_movies.py, following the
// valid-frame rule): each movie holds only the days its tile was fully imaged
// (the stack's own pct_nans < 1 %), one frame per kept day at 1 fps. The
// label demo reads the same valid-frame movies (ch03/lakes/ is retired).
interface KeptFrame { day: number; date_iso: string; p_water: number | null }
interface Sidecar {
  lake_id: string
  t0: string
  days: number
  fps: number
  frame_count: number
  frames: KeptFrame[]
  p_water_daily: (number | null)[]
}
const sidecars = reactive<Record<string, Sidecar>>({})
const videos: Record<string, HTMLVideoElement | null> = {}
const loaded = reactive<Record<string, boolean>>({})

function setVideo(id: string, el: HTMLVideoElement | null): void {
  videos[id] = el
}
function onLoaded(id: string): void {
  loaded[id] = true
  seek(id)
}
async function fetchSidecar(id: string): Promise<void> {
  try {
    const r = await fetch(mediaUrl(`ch03/lakes_valid/${id}.json`))
    if (!r.ok) return
    sidecars[id] = (await r.json()) as Sidecar
    seek(id)
  } catch {
    // date + curve simply stay blank for that panel
  }
}
// The panels never show before every movie has a decoded frame — an
// unloaded <video> is a black tile.
const allReady = computed(() => props.lakes.every((lk) => loaded[lk.id] && sidecars[lk.id]))

// ── the shared clock ──────────────────────────────────────────────────
// ONE season clock for all five (the parent's `day`, days since t0). It
// steps only through the CLOCK DATES — the days on which at least one of
// the five has a new valid frame (emitted to the parent below) — and each
// lake shows its latest valid frame at or before the clock's day: on a
// day it has none it HOLDS (its own acquisition date shows, quietly).
// Before a lake's first valid frame it shows that first frame, dimmed.
const clockDays = computed<number[]>(() => {
  if (!props.lakes.every((lk) => sidecars[lk.id])) return []
  const set = new Set<number>()
  for (const lk of props.lakes) for (const f of sidecars[lk.id].frames) set.add(f.day)
  return [...set].sort((a, b) => a - b)
})
watch(clockDays, (d) => { if (d.length) emit('clock', d) }, { immediate: true })

/** Index into the lake's kept frames for the clock's day. */
function frameIndex(id: string): number {
  const fr = sidecars[id]?.frames
  if (!fr || !fr.length) return 0
  // last kept frame with day ≤ clock day (binary search)
  let lo = 0
  let hi = fr.length - 1
  if (fr[0].day > props.day) return 0
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1
    if (fr[mid].day <= props.day) lo = mid
    else hi = mid - 1
  }
  return lo
}
function isIdle(id: string): boolean {
  const fr = sidecars[id]?.frames
  return !!fr && fr.length > 0 && fr[0].day > props.day
}
function seek(id: string): void {
  const v = videos[id]
  const sc = sidecars[id]
  if (!v || !sc || !loaded[id]) return
  // The middle of the frame's display interval — no browser rounds that
  // onto a neighbour. A held frame is the same index: no seek at all.
  const t = (frameIndex(id) + 0.5) / sc.fps
  if (Math.abs(v.currentTime - t) > 0.01) v.currentTime = t
}
watch(() => props.day, () => { for (const lk of props.lakes) seek(lk.id) })

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
function fmt(iso: string | undefined): string {
  if (!iso) return '—'
  const [, m, d] = iso.split('-')
  return `${parseInt(d, 10)} ${MONTHS[parseInt(m, 10) - 1]}`
}
const DAY_MS = 86400e3
function isoOfDay(day: number): string {
  return new Date(Date.parse(props.t0 + 'T00:00:00Z') + day * DAY_MS).toISOString().slice(0, 10)
}
const clockLabel = computed(() => fmt(isoOfDay(props.day)))
const nDays = computed(() => {
  for (const lk of props.lakes) if (sidecars[lk.id]) return sidecars[lk.id].days
  return 153
})
const lastTick = computed(() => fmt(isoOfDay(nDays.value - 1)))
/** The held frame's own date, when it is not the clock's. */
function heldLabel(id: string): string {
  const f = sidecars[id]?.frames[frameIndex(id)]
  if (!f || f.day === props.day) return ''
  return `imaged ${fmt(f.date_iso)}`
}

// ── the p_water strip ─────────────────────────────────────────────────
const CW = 240
const CH = 40
function series(id: string): number[] {
  const daily = sidecars[id]?.p_water_daily
  if (!daily) return []
  // Backward-fill NaN days (drops land on the day that SAW them).
  const out: number[] = new Array(daily.length).fill(0)
  let next = 0
  for (let i = daily.length - 1; i >= 0; i--) {
    const p = daily[i]
    if (p !== null && Number.isFinite(p)) next = p
    out[i] = next
  }
  return out
}
function xAt(i: number, n: number): number {
  return n <= 1 ? CW / 2 : (i / (n - 1)) * (CW - 4) + 2
}
// The curve's floor sits CURVE_B above the bottom so the projector-sized
// tick dates fit under it — same panel geometry.
const CURVE_B = 16
function yAt(p: number): number {
  return CH - CURVE_B - Math.max(0, Math.min(1, p)) * (CH - CURVE_B - 3)
}
function linePath(id: string): string {
  const s = series(id)
  return s.map((p, i) => `${i ? 'L' : 'M'}${xAt(i, s.length).toFixed(1)},${yAt(p).toFixed(1)}`).join(' ')
}
function areaPath(id: string): string {
  const s = series(id)
  if (!s.length) return ''
  return `${linePath(id)} L${xAt(s.length - 1, s.length).toFixed(1)},${CH - CURVE_B} L${xAt(0, s.length).toFixed(1)},${CH - CURVE_B} Z`
}
const markerX = computed(() => xAt(Math.min(props.day, nDays.value - 1), nDays.value))

// ── placement: the solver ─────────────────────────────────────────────
//
// The director's brief: the cards as big as they can be without
// overlapping each other or the lake polygons, seeded by the director's
// sketch of where each sits. The five lakes project to a tight cluster
// (LD/HF/MD 30 px apart on a diagonal at 1440×900) with ND above and CD
// left, and their screen positions shift with the viewport's aspect, so
// this is solved live: for a panel width w from big to small, place the
// panels one by one (most constrained first) on a 16 px grid, each at
// the grid cell nearest its slot that keeps it on screen, off the nav
// and the beat pills, clear of every lake polygon, clear of the panels
// already placed, and whose leader (lake → nearest border point) crosses
// no other panel and grazes no other lake — and no earlier leader
// crosses it. The first width with a full placement wins.
interface Rect { x: number; y: number; w: number; h: number }
interface Pt { x: number; y: number }
interface Placed {
  id: string
  color: string
  className: string
  src: string
  rect: Rect
  anchor: Pt | null
  contact: Pt
}
const anchors = reactive<Record<string, { x: number; y: number; visible: boolean }>>({})
const solved = ref(false)
const layout = ref<Record<string, Rect>>({})
let solvedFor: string | null = null
let stableFrames = 0
let lastSig = ''

// Panel chrome (must match the CSS): head 34 · pad 8 · curve 40/240 of
// the frame width · bottom 6.
const PAD = 8
const HEAD = 34
function panelH(w: number): number {
  const frame = w - 2 * PAD
  return HEAD + frame + Math.round(frame * (CH / CW)) + PAD + 6
}
const LAKE_CLEAR = 18   // px around a lake centre no panel may cover
const LEADER_CLEAR = 15 // px a leader must keep from another lake
const GAP = 10          // px between panels
const EDGE = 8
const GRID = 16

function inflate(r: Rect, m: number): Rect {
  return { x: r.x - m, y: r.y - m, w: r.w + 2 * m, h: r.h + 2 * m }
}
function overlaps(a: Rect, b: Rect): boolean {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y
}
function contains(r: Rect, p: Pt): boolean {
  return p.x >= r.x && p.x <= r.x + r.w && p.y >= r.y && p.y <= r.y + r.h
}
function contactOf(a: Pt, r: Rect): Pt {
  const cx = r.x + r.w / 2
  const cy = r.y + r.h / 2
  const dx = cx - a.x
  const dy = cy - a.y
  const sx = dx !== 0 ? (r.w / 2) / Math.abs(dx) : Infinity
  const sy = dy !== 0 ? (r.h / 2) / Math.abs(dy) : Infinity
  const t = Math.max(0, 1 - Math.min(sx, sy))
  return { x: a.x + dx * t, y: a.y + dy * t }
}
function segPointDist(a: Pt, b: Pt, p: Pt): number {
  const vx = b.x - a.x
  const vy = b.y - a.y
  const l2 = vx * vx + vy * vy
  const t = l2 ? Math.max(0, Math.min(1, ((p.x - a.x) * vx + (p.y - a.y) * vy) / l2)) : 0
  return Math.hypot(p.x - (a.x + vx * t), p.y - (a.y + vy * t))
}
// Liang–Barsky: does segment a→b pass through rect r?
function segRect(a: Pt, b: Pt, r: Rect): boolean {
  let t0 = 0
  let t1 = 1
  const dx = b.x - a.x
  const dy = b.y - a.y
  const tests: [number, number][] = [
    [-dx, a.x - r.x], [dx, r.x + r.w - a.x],
    [-dy, a.y - r.y], [dy, r.y + r.h - a.y],
  ]
  for (const [p, q] of tests) {
    if (p === 0) {
      if (q < 0) return false
      continue
    }
    const t = q / p
    if (p < 0) { if (t > t1) return false; if (t > t0) t0 = t }
    else { if (t < t0) return false; if (t < t1) t1 = t }
  }
  return t0 <= t1
}

function forbiddenRects(): Rect[] {
  const out: Rect[] = []
  for (const sel of ['.top-nav', '.landmarks', '.beat-nav', '.ch3-season']) {
    const el = document.querySelector(sel)
    if (!el) continue
    const b = el.getBoundingClientRect()
    if (b.width > 0) out.push({ x: b.x - 6, y: b.y - 6, w: b.width + 12, h: b.height + 12 })
  }
  return out
}

function solve(): boolean {
  const pts: Record<string, Pt> = {}
  for (const lk of props.lakes) {
    const a = anchors[lk.id]
    if (!a || !a.visible) return false
    pts[lk.id] = { x: a.x, y: a.y }
  }
  const forbidden = forbiddenRects()
  const W = vw.value
  const H = vh.value
  const ids = props.lakes.map((l) => l.id)
  // Most constrained first: the lakes with the most neighbours within
  // 60 px (the cluster), then the rest.
  const crowd = (id: string) => ids.filter((o) => o !== id && Math.hypot(pts[o].x - pts[id].x, pts[o].y - pts[id].y) < 60).length
  const order = [...props.lakes].sort((a, b) => crowd(b.id) - crowd(a.id))

  const wMax = Math.round(W * 0.26)
  const wMin = Math.round(Math.max(150, W * 0.11))
  for (let w = wMax; w >= wMin; w -= 6) {
    const h = panelH(w)
    if (h > H - 2 * EDGE - 80) continue
    // Candidate cells for each panel, nearest its slot first, within
    // ~a third of the screen of it (so the picture stays the director's).
    const cands: Record<string, Rect[]> = {}
    for (const lk of order) {
      const cx = lk.slot.x * W
      const cy = lk.slot.y * H
      const list: { r: Rect; d: number }[] = []
      const radius = Math.max(W, H) * 0.36
      for (let y = EDGE; y + h <= H - EDGE; y += GRID) {
        for (let x = EDGE; x + w <= W - EDGE; x += GRID) {
          const d = Math.hypot(x + w / 2 - cx, y + h / 2 - cy)
          if (d > radius) continue
          list.push({ r: { x, y, w, h }, d })
        }
      }
      list.sort((a, b) => a.d - b.d)
      cands[lk.id] = list.map((c) => c.r)
    }
    const placedR: Record<string, Rect> = {}
    let budget = 6000
    const ok = (id: string, r: Rect): boolean => {
      for (const f of forbidden) if (overlaps(r, f)) return false
      const big = inflate(r, LAKE_CLEAR)
      for (const o of ids) if (contains(big, pts[o])) return false
      const gap = inflate(r, GAP)
      for (const pid in placedR) if (overlaps(gap, placedR[pid])) return false
      const c = contactOf(pts[id], r)
      for (const o of ids) {
        if (o === id) continue
        if (segPointDist(pts[id], c, pts[o]) < LEADER_CLEAR) return false
      }
      for (const pid in placedR) {
        if (segRect(pts[id], c, inflate(placedR[pid], 6))) return false
        const pc = contactOf(pts[pid], placedR[pid])
        if (segRect(pts[pid], pc, inflate(r, 6))) return false
      }
      return true
    }
    const dfs = (k: number): boolean => {
      if (k === order.length) return true
      const id = order[k].id
      for (const r of cands[id]) {
        if (--budget < 0) return false
        if (!ok(id, r)) continue
        placedR[id] = r
        if (dfs(k + 1)) return true
        delete placedR[id]
      }
      return false
    }
    if (dfs(0)) {
      layout.value = { ...placedR }
      return true
    }
  }
  return false
}

const placed = computed<Placed[]>(() => {
  return props.lakes.map((lk) => {
    const w = Math.round(Math.max(150, vw.value * 0.14))
    const rect = layout.value[lk.id] ?? {
      x: Math.round(Math.max(EDGE, Math.min(vw.value - w - EDGE, lk.slot.x * vw.value - w / 2))),
      y: Math.round(Math.max(EDGE, Math.min(vh.value - panelH(w) - EDGE, lk.slot.y * vh.value - panelH(w) / 2))),
      w,
      h: panelH(w),
    }
    const a = anchors[lk.id]
    const anchor = a && a.visible ? { x: a.x, y: a.y } : null
    const contact = anchor ? contactOf(anchor, rect) : { x: rect.x + rect.w / 2, y: rect.y + rect.h / 2 }
    return {
      id: lk.id,
      color: lk.color,
      className: lk.className,
      src: mediaUrl(`ch03/lakes_valid/${lk.id}.mp4`),
      rect,
      anchor,
      contact,
    }
  })
})

// Per-frame: lake anchors from the Globe's projection. The layout is
// solved once the anchors have held still for 8 frames (the camera has
// landed) and re-solved only if they move again or the window resizes.
let rafId = 0
function tick(): void {
  const screens = (window as any).__featuredLakeScreens as
    | Record<string, { x: number; y: number; visible: boolean }>
    | null
  let sig = ''
  let moved = false
  for (const lk of props.lakes) {
    const s = screens?.[lk.id]
    const prev = anchors[lk.id]
    if (s) {
      if (prev && (Math.abs(prev.x - s.x) > 0.5 || Math.abs(prev.y - s.y) > 0.5)) moved = true
      anchors[lk.id] = { x: s.x, y: s.y, visible: s.visible }
      sig += `${lk.id}:${Math.round(s.x / 12)},${Math.round(s.y / 12)};`
    } else if (prev) {
      prev.visible = false
    }
  }
  stableFrames = moved ? 0 : stableFrames + 1
  // Also wait for the Globe's textures (the basemap is 75 MB on a cold
  // load) — callouts over a black globe read as broken (seen on film).
  const texReady = ((window as any).__texturesStarted ?? 0) > 0 && ((window as any).__texturesPending ?? 0) === 0
  if (texReady && stableFrames >= 8 && sig && sig !== solvedFor && sig !== lastSig) {
    lastSig = sig
    if (solve()) {
      solvedFor = sig
      solved.value = true
    } else if (!solved.value) {
      // No full placement at any size: fall back to the slots as drawn.
      layout.value = {}
      solved.value = true
      solvedFor = sig
    }
  }
  rafId = requestAnimationFrame(tick)
}

// (declared after `solved` — the getter runs at setup)
watch(() => solved.value && allReady.value, (r) => emit('ready', r), { immediate: true })

onMounted(() => {
  window.addEventListener('resize', onResize)
  for (const lk of props.lakes) fetchSidecar(lk.id)
  rafId = requestAnimationFrame(tick)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  cancelAnimationFrame(rafId)
  emit('hover', null)
})
</script>

<style scoped>
.elp-root {
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: v-bind('props.opacity');
  transition: opacity 0.4s;
  font-family: 'Inter', system-ui, sans-serif;
}
.elp-hidden { visibility: hidden; }

.elp-lines {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
}
.elp-line {
  stroke-width: 1.6;
  opacity: 0.7;
  transition: opacity 0.25s, stroke-width 0.25s;
  vector-effect: non-scaling-stroke;
}
.elp-dot {
  opacity: 0.8;
  transition: opacity 0.25s;
}
.elp-line-lit { opacity: 1; }
.elp-line.elp-line-lit { stroke-width: 2.4; }
/* the other lakes' leaders, while one is lit */
.elp-line.elp-line-back { opacity: 0.32; }
.elp-dot.elp-line-back { opacity: 0.4; }

/* OPAQUE (the director did not want to see through them), ever so
   slightly faded at rest — a touch less saturation and light — then full
   colour with a lit outline on hover / pin. */
.elp-panel {
  position: absolute;
  pointer-events: auto;
  box-sizing: border-box;
  padding: 6px 8px 6px;
  border: 1.5px solid color-mix(in srgb, var(--acc) 55%, #2a2520);
  border-radius: 10px;
  background: #0d0b09;
  cursor: pointer;
  filter: saturate(0.86) brightness(0.93);
  transition: filter 0.25s, box-shadow 0.25s, border-color 0.25s, transform 0.25s, opacity 0.25s ease;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.55);
}
/* While one panel is lit the others step back a little (the director
   wanted the others to fade into the background a bit, to accentuate
   the one under the pointer) — half-faded, a touch greyer; the rest look
   above is untouched when nothing is lit. */
.elp-panel.elp-back {
  opacity: 0.5;
  filter: saturate(0.7) brightness(0.9);
}
.elp-panel.elp-lit {
  filter: none;
  border-color: var(--acc);
  box-shadow:
    0 10px 36px rgba(0, 0, 0, 0.7),
    0 0 0 1.5px var(--acc),
    0 0 26px color-mix(in srgb, var(--acc) 55%, transparent);
  z-index: 3;
}
.elp-panel.elp-pinned {
  transform: scale(1.02);
}

.elp-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
  height: 30px;
  margin-bottom: 4px;
}
.elp-id {
  font-family: ui-monospace, 'SF Mono', Menlo, monospace;
  font-size: 0.88rem;
  letter-spacing: 0.01em;
  color: rgba(245, 240, 230, 0.95);
  white-space: nowrap;
}
.elp-class {
  font-weight: 600;
  font-size: 0.9rem;
  letter-spacing: 0.01em;
  white-space: nowrap;
}

.elp-frame {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  border-radius: 6px;
  overflow: hidden;
  background: #000;
}
.elp-video {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: opacity 0.4s;
}
/* Before its first valid frame a lake shows that frame, dimmed. */
.elp-idle .elp-video { opacity: 0.6; }
.elp-date {
  position: absolute;
  left: 6px;
  top: 6px;
  display: flex;
  align-items: baseline;
  gap: 0.35em;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(8, 7, 6, 0.82);
  font-size: 0.95rem;
  color: #f5f0e6;
  font-variant-numeric: tabular-nums;
}
.elp-held {
  position: absolute;
  right: 6px;
  bottom: 5px;
  padding: 1px 6px;
  border-radius: 999px;
  background: rgba(8, 7, 6, 0.6);
  font-size: 0.84rem;
  letter-spacing: 0.02em;
  color: rgba(245, 240, 230, 0.92);
  font-variant-numeric: tabular-nums;
}
.elp-date-year {
  font-size: 0.8rem;
  color: rgba(245, 240, 230, 0.88);
}

.elp-curve {
  display: block;
  width: 100%;
  height: auto;
  margin-top: 4px;
}
.elp-area { opacity: 0.3; }
.elp-curveline {
  fill: none;
  stroke-width: 2;
  vector-effect: non-scaling-stroke;
}
.elp-marker {
  stroke: #f5f0e6;
  stroke-width: 1.5;
  opacity: 0.9;
  vector-effect: non-scaling-stroke;
}
.elp-tick {
  fill: rgba(245, 240, 230, 0.95);
  font-size: 15px;
  font-weight: 500;
}
</style>
