<template>
  <!-- The Introduction's "coupling length" step (first built as a sample
       for the director): the two end members of the "how far does one drainage
       reach?" conversation, on the greenland object over central-west
       Greenland. Top-left, the four papers' title-page cards (the
       timeline's own pages, small); on the ice, each paper's footprint in
       its key colour with a true-length scale rule. Hovering a card lights
       its footprint; hovering a footprint lights its card (a card click
       opens the DOI, as on the timeline; the map never opens anything —
       a stray click mid-talk must not). Figure labels only. Positions track the object every frame from the Globe's
       screen anchors (couplingShapes.ts), written imperatively. -->
  <div class="cpl" :class="{ hot: hot !== null }" :style="{ '--s24': colorOf('stevens2024') }">
    <div class="cpl-map" :class="{ on }">
    <svg class="cpl-svg" :width="vw" :height="vh" aria-hidden="true">
      <g
        v-for="s in CPL_SHAPES"
        :key="s.key"
        class="cpl-shape"
        :class="[`k-${s.kind}`, { lit: hot === s.paper, dim: hot !== null && hot !== s.paper, big: s.big }]"
        :style="{ '--c': colorOf(s.paper) }"
        @mouseenter="hot = s.paper"
        @mouseleave="hot = null"
      >
        <path :ref="(el) => setEl(`${s.key}:halo`, el)" class="halo" />
        <path :ref="(el) => setEl(`${s.key}:main`, el)" class="main" />
      </g>

      <!-- The North Lake loupe: its circle on the ice, the two tangents,
           and a plan view of Stevens 2024's lakes + array and Lai 2021's
           North Lake blisters, turned to the map's heading. -->
      <path ref="loupeRingHalo" class="cpl-loupe-ring halo" />
      <path ref="loupeRing" class="cpl-loupe-ring" />
      <path ref="loupeLeadHalo" class="cpl-loupe-lead halo" />
      <path ref="loupeLead" class="cpl-loupe-lead" />
      <defs>
        <clipPath id="cpl-loupe-clip"><circle ref="loupeClip" /></clipPath>
      </defs>
      <circle ref="loupeBg" class="cpl-loupe-bg" />
      <g clip-path="url(#cpl-loupe-clip)">
        <g
          v-for="it in LOUPE_ITEMS"
          :key="it.key"
          class="cpl-shape"
          :class="[`k-${it.kind}`, 'in-loupe', { lit: hot === it.paper, dim: hot !== null && hot !== it.paper, big: it.big }]"
          :style="{ '--c': colorOf(it.paper) }"
          @mouseenter="hot = it.paper"
          @mouseleave="hot = null"
        >
          <path :ref="(el) => setEl(`${it.key}:halo`, el)" class="halo" />
          <path :ref="(el) => setEl(`${it.key}:main`, el)" class="main" />
        </g>
        <text
          v-for="n in LOUPE_NAMES"
          :key="n.name"
          :ref="(el) => setEl(`lpn:${n.name}`, el)"
          class="cpl-loupe-name"
          :class="{ dim: hot !== null && hot !== 'stevens2024' }"
        >{{ n.name }}</text>
      </g>
      <circle ref="loupeRim" class="cpl-loupe-rim" />
    </svg>

    <!-- Each footprint's figure label: the paper, and its length. -->
    <div
      v-for="l in LABELS"
      :key="l.paper"
      :ref="(el) => setEl(`lab:${l.paper}`, el)"
      class="cpl-label"
      :class="{ lit: hot === l.paper, dim: hot !== null && hot !== l.paper }"
      :style="{ '--c': colorOf(l.paper) }"
      @mouseenter="hot = l.paper"
      @mouseleave="hot = null"
    >
      <span class="cpl-label-who">{{ l.who }}</span>
      <span class="cpl-label-len">{{ l.len }}</span>
    </div>
    <!-- The legend (the director asked for one in the top right corner
         of this page, just beneath the BACK
         and NEXT buttons): the SHAPES the map draws, keyed in a neutral
         ice-white — colour is the paper's and lives on the cards. Glyph +
         a two-or-three-word label a row; a dark plate like the labels';
         no hover. -->
    <div class="cpl-legend" aria-label="Map legend">
      <div v-for="row in LEGEND" :key="row.label" class="cpl-legend-row">
        <svg class="cpl-legend-glyph" viewBox="0 0 30 18" width="30" height="18" aria-hidden="true" v-html="row.svg"></svg>
        <span class="cpl-legend-text">{{ row.label }}</span>
      </div>
    </div>

    <svg class="cpl-svg cpl-leaders" :width="vw" :height="vh" aria-hidden="true">
      <path
        v-for="l in LABELS"
        :key="l.paper"
        :ref="(el) => setEl(`lead:${l.paper}`, el)"
        class="cpl-leader"
        :class="{ dim: hot !== null && hot !== l.paper }"
        :style="{ '--c': colorOf(l.paper) }"
      />
    </svg>

    </div>

    <!-- The four papers, top-left, in the timeline's chronological order
         (up at once; the footprints fade in when the camera has landed). -->
    <div ref="cardsEl" class="cpl-cards" :class="{ flip: flipping }" :style="{ '--cw': `${cardW}px` }">
      <a
        v-for="(c, i) in CARDS"
        :key="c.paper.id"
        class="cpl-card"
        :data-id="c.id"
        :class="{ lit: hot === c.id, dim: hot !== null && hot !== c.id }"
        :style="{ '--c': colorOf(c.id), '--i': i }"
        :href="c.url ?? undefined"
        target="_blank"
        rel="noopener noreferrer"
        @mouseenter="hot = c.id"
        @mouseleave="hot = null"
      >
        <div class="cpl-pill">
          <span class="cpl-pill-name">{{ c.name }}</span>
          <span class="cpl-pill-year">{{ c.paper.year }}</span>
        </div>
        <div class="cpl-page-wrap">
          <TimelinePage :paper="c.paper" class="cpl-page" />
        </div>
      </a>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { ComponentPublicInstance } from 'vue'
import { COUPLING_PAPERS, type CouplingPaperId } from '../config/couplingLength'
import { TIMELINE_PAPERS, paperUrl } from '../config/timeline'
import {
  CPL_SHAPES,
  LOUPE_ITEMS,
  LOUPE_NAMES,
  LOUPE_R_KM,
  type CplShape,
  type LoupeItem,
} from './couplingShapes'
import TimelinePage from './TimelinePage.vue'

const props = defineProps<{
  /** Fade the footprints in (the camera has settled). */
  visible: boolean
}>()

const on = ref(false)
watch(
  () => props.visible,
  (v) => (on.value = v),
  { immediate: true },
)

const hot = ref<CouplingPaperId | null>(null)

const COLOR = Object.fromEntries(COUPLING_PAPERS.map((p) => [p.id, p.color])) as Record<CouplingPaperId, string>
function colorOf(id: CouplingPaperId): string {
  return COLOR[id]
}

const IDS: CouplingPaperId[] = ['christoffersen2018', 'lai2021', 'stevens2024', 'stevens2026']
const CARDS = IDS.map((id) => {
  const paper = TIMELINE_PAPERS.find((p) => p.id === id)!
  return { id, paper, url: paperUrl(paper), name: paper.label.replace(/,?\s*\d{4}$/, '') }
})


// Where each figure label sits: at a shape's anchor point, pushed off by
// (dx, dy) px with a thin leader back to that point.
interface Label {
  paper: CouplingPaperId
  who: string
  len: string
  /** The shape whose point the label hangs from, and which point (a
   *  loupe item's key = a point inside the loupe). */
  at: { key: string; i: number | 'mid' }
  dx: number
  dy: number
}
const LEN = Object.fromEntries(COUPLING_PAPERS.map((p) => [p.id, p.rule.label])) as Record<CouplingPaperId, string>
const LABELS: Label[] = [
  { paper: 'christoffersen2018', who: 'Christoffersen 2018', len: LEN.christoffersen2018, at: { key: 'c18rule', i: 'mid' }, dx: -125, dy: 0 },
  { paper: 'lai2021', who: 'Lai 2021', len: LEN.lai2021, at: { key: 'lp-l21-0', i: 0 }, dx: 0, dy: 150 },
  { paper: 'stevens2024', who: 'Stevens 2024', len: LEN.stevens2024, at: { key: 'lp-s24rule', i: 'mid' }, dx: -215, dy: 118 }, // below the four cards' bottom edge at 1280 too
  // dy −40 → +70: the legend's plate now hangs under the
  // BACK/NEXT pills, where this label used to sit at 1280–1440 wide
  { paper: 'stevens2026', who: 'Stevens 2026', len: LEN.stevens2026, at: { key: 's26rule', i: 'mid' }, dx: 185, dy: 70 },
]

// ── the legend's rows ──────────────────────────────────────────────────
// Each glyph is the map's own mark (shapePath's geometry: DOT_R / DOT_R_BIG
// dots, the TRI_R triangle, a ring, a dashed outline, a filled patch, the
// rule with its end ticks, the loupe with its tangents) in a 30 × 18 box,
// stroked ice-white like the loupe's rim. Colour is the paper's and is NOT
// keyed here.
const LEGEND: { label: string; svg: string }[] = [
  { label: 'Lake', svg: '<circle class="lg-fill" cx="15" cy="9" r="2.6"/>' },
  { label: 'Named lake', svg: '<circle class="lg-fill lg-big" cx="15" cy="9" r="4"/>' },
  { label: 'GPS receiver', svg: '<path class="lg-tri" d="M15,4.2L19.3,11.4L10.7,11.4Z"/>' },
  { label: 'Blister radius', svg: '<circle class="lg-ring" cx="15" cy="9" r="6.5"/>' },
  { label: 'Model domain', svg: '<path class="lg-dash" d="M4,3.5L26,3.5L26,14.5L4,14.5Z"/>' },
  { label: 'Cascade region', svg: '<path class="lg-area" d="M5,10C6,4.5 12,3 16,4.5C21,6 26,5 25.5,10C25,14.5 19,15.5 14.5,14.5C10,13.5 4.5,14.5 5,10Z"/>' },
  { label: 'Coupling length', svg: '<path class="lg-rule" d="M4,9L26,9M4,4.5L4,13.5M26,4.5L26,13.5"/>' },
  { label: 'North Lake, magnified', svg: '<path class="lg-lead" d="M12.5,4.5L25,2M12.5,13.5L25,16"/><circle class="lg-loupe" cx="8" cy="9" r="5.6"/><circle class="lg-fill" cx="8" cy="9" r="1.6"/><circle class="lg-dotsm" cx="24.5" cy="9" r="1.1"/>' },
]

// ── the per-frame redraw ──────────────────────────────────────────────
const vw = ref(window.innerWidth)
const vh = ref(window.innerHeight)
/** Card width: the timeline's small size, a little larger on big screens. */
const cardW = computed(() => Math.round(Math.max(108, Math.min(150, vw.value * 0.078))))
function onResize(): void {
  vw.value = window.innerWidth
  vh.value = window.innerHeight
}

const els = new Map<string, Element>()
function setEl(key: string, el: Element | ComponentPublicInstance | null): void {
  if (el instanceof Element) els.set(key, el)
  else els.delete(key)
}

type Scr = { x: number; y: number; visible: boolean }
const DOT_R = 2.4
const DOT_R_BIG = 3.6
const TRI_R = 3.4
const TICK = 7

function pts(s: CplShape, scr: Record<string, Scr>): Scr[] {
  const out: Scr[] = []
  for (let i = 0; i < s.pts.length; i++) {
    const p = scr[`cpl:${s.key}:${i}`]
    if (p) out.push(p)
  }
  return out
}
const f = (v: number) => v.toFixed(1)

function shapePath(s: CplShape, p: Scr[]): string {
  switch (s.kind) {
    case 'area':
    case 'ring':
      return p.length > 2 ? `M${p.map((q) => `${f(q.x)},${f(q.y)}`).join('L')}Z` : ''
    case 'outline':
      return p.length > 1 ? `M${p.map((q) => `${f(q.x)},${f(q.y)}`).join('L')}` : ''
    case 'dots': {
      const r = s.big ? DOT_R_BIG : DOT_R
      return p
        .filter((q) => q.visible)
        .map((q) => `M${f(q.x - r)},${f(q.y)}a${r},${r} 0 1,0 ${2 * r},0a${r},${r} 0 1,0 ${-2 * r},0`)
        .join('')
    }
    case 'stations': {
      const r = TRI_R
      return p
        .filter((q) => q.visible)
        .map((q) => `M${f(q.x)},${f(q.y - r)}L${f(q.x + r * 0.95)},${f(q.y + r * 0.7)}L${f(q.x - r * 0.95)},${f(q.y + r * 0.7)}Z`)
        .join('')
    }
    case 'rule': {
      if (p.length < 2) return ''
      const [a, b] = p
      const dx = b.x - a.x
      const dy = b.y - a.y
      const n = Math.hypot(dx, dy) || 1
      const nx = (-dy / n) * TICK
      const ny = (dx / n) * TICK
      return (
        `M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}` +
        `M${f(a.x + nx)},${f(a.y + ny)}L${f(a.x - nx)},${f(a.y - ny)}` +
        `M${f(b.x + nx)},${f(b.y + ny)}L${f(b.x - nx)},${f(b.y - ny)}`
      )
    }
  }
}

// ── the loupe ──────────────────────────────────────────────────────────
const loupeRing = ref<SVGPathElement | null>(null)
const loupeRingHalo = ref<SVGPathElement | null>(null)
const loupeLead = ref<SVGPathElement | null>(null)
const loupeLeadHalo = ref<SVGPathElement | null>(null)
const loupeClip = ref<SVGCircleElement | null>(null)
const loupeBg = ref<SVGCircleElement | null>(null)
const loupeRim = ref<SVGCircleElement | null>(null)
/** The loupe disc, as viewport fractions (over the coast, clear of the
 *  cards, the footprints and the pills in the chosen framing). y 0.235 →
 *  0.25: at 900 px tall its top touched the ribbon's
 *  sub-menu bar; now ~14 px under it. */
const LOUPE_AT = { x: 0.565, y: 0.25, r: 0.135 }

function loupePath(it: LoupeItem, map: (p: [number, number]) => { x: number; y: number }): { d: string; scr: Scr[] } {
  const scr = it.pts.map((p) => ({ ...map(p), visible: true }))
  const shape: CplShape = { key: it.key, paper: it.paper, kind: it.kind, pts: [], big: it.big }
  return { d: shapePath(shape, scr), scr }
}

/** The two outer tangents between circles (a, ra) and (b, rb). */
function tangents(a: { x: number; y: number }, ra: number, b: { x: number; y: number }, rb: number): string {
  const dx = b.x - a.x
  const dy = b.y - a.y
  const d = Math.hypot(dx, dy)
  if (d <= Math.abs(ra - rb) + 1) return ''
  const base = Math.atan2(dy, dx)
  const off = Math.acos((ra - rb) / d)
  let out = ''
  for (const sgn of [1, -1]) {
    const t = base + sgn * off
    const c = Math.cos(t)
    const s2 = Math.sin(t)
    out += `M${f(a.x + ra * c)},${f(a.y + ra * s2)}L${f(b.x + rb * c)},${f(b.y + rb * s2)}`
  }
  return out
}

function drawLoupe(scr: Record<string, Scr>, loupePts: Map<string, Scr[]>): void {
  const c = scr['cpl:loupe:c']
  const n = scr['cpl:loupe:n']
  if (!c || !n) return
  // The map's heading at North Lake: screen direction of north; east is a
  // quarter-turn clockwise of it (plan view — no foreshortening).
  let nx = n.x - c.x
  let ny = n.y - c.y
  const nl = Math.hypot(nx, ny) || 1
  nx /= nl
  ny /= nl
  const ex = -ny
  const ey = nx
  const R = Math.min(LOUPE_AT.r * vh.value, 0.1 * vw.value)
  const L = { x: LOUPE_AT.x * vw.value, y: LOUPE_AT.y * vh.value }
  const k = R / (LOUPE_R_KM + 0.4)
  const map = (p: [number, number]) => ({ x: L.x + k * (p[0] * ex + p[1] * nx), y: L.y + k * (p[0] * ey + p[1] * ny) })
  for (const el of [loupeClip.value, loupeBg.value, loupeRim.value]) {
    el?.setAttribute('cx', f(L.x))
    el?.setAttribute('cy', f(L.y))
    el?.setAttribute('r', f(R))
  }
  for (const it of LOUPE_ITEMS) {
    const { d, scr: sp } = loupePath(it, map)
    loupePts.set(it.key, sp)
    els.get(`${it.key}:halo`)?.setAttribute('d', d)
    els.get(`${it.key}:main`)?.setAttribute('d', d)
  }
  for (const nm of LOUPE_NAMES) {
    const t = els.get(`lpn:${nm.name}`)
    const q = map(nm.at)
    t?.setAttribute('x', f(q.x + 7))
    t?.setAttribute('y', f(q.y - 6))
  }
  // Its circle on the ice, and the tangents to the disc.
  const ring: Scr[] = []
  for (let i = 0; i <= 48; i++) {
    const p = scr[`cpl:loupe:ring:${i}`]
    if (p) ring.push(p)
  }
  if (ring.length > 3) {
    const rd = `M${ring.map((q) => `${f(q.x)},${f(q.y)}`).join('L')}Z`
    loupeRing.value?.setAttribute('d', rd)
    loupeRingHalo.value?.setAttribute('d', rd)
    const gx = ring.reduce((a, q) => a + q.x, 0) / ring.length
    const gy = ring.reduce((a, q) => a + q.y, 0) / ring.length
    const gr = ring.reduce((a, q) => a + Math.hypot(q.x - gx, q.y - gy), 0) / ring.length
    const td = tangents({ x: gx, y: gy }, gr, L, R)
    loupeLead.value?.setAttribute('d', td)
    loupeLeadHalo.value?.setAttribute('d', td)
  }
}

let raf: number | null = null
function draw(): void {
  raf = window.requestAnimationFrame(draw)
  const scr = (window as any).__globeAnchorScreens as Record<string, Scr> | null
  if (!scr) return
  const byKey = new Map<string, Scr[]>()
  for (const s of CPL_SHAPES) {
    const p = pts(s, scr)
    byKey.set(s.key, p)
    const d = shapePath(s, p)
    els.get(`${s.key}:halo`)?.setAttribute('d', d)
    els.get(`${s.key}:main`)?.setAttribute('d', d)
  }
  const loupePts = new Map<string, Scr[]>()
  drawLoupe(scr, loupePts)
  for (const l of LABELS) {
    const p = byKey.get(l.at.key) ?? loupePts.get(l.at.key)
    const lab = els.get(`lab:${l.paper}`) as HTMLElement | undefined
    const lead = els.get(`lead:${l.paper}`)
    if (!p || !p.length || !lab) continue
    const a =
      l.at.i === 'mid'
        ? { x: (p[0].x + p[p.length - 1].x) / 2, y: (p[0].y + p[p.length - 1].y) / 2 }
        : p[Math.min(l.at.i, p.length - 1)]
    const w = lab.offsetWidth
    const h = lab.offsetHeight
    // Kept on screen: at narrow windows the projector-sized type would
    // otherwise push the edge labels (Christoffersen, Stevens 2026) off it.
    const cx = Math.max(w / 2 + 8, Math.min(window.innerWidth - w / 2 - 8, a.x + l.dx))
    const cy = a.y + l.dy
    lab.style.transform = `translate(${f(cx - w / 2)}px, ${f(cy - h / 2)}px)`
    // Leader: from the anchor to the label box's nearest edge.
    const ex = Math.max(cx - w / 2, Math.min(a.x, cx + w / 2))
    const ey = Math.max(cy - h / 2, Math.min(a.y, cy + h / 2))
    const far = Math.hypot(ex - a.x, ey - a.y) > 14
    lead?.setAttribute('d', far ? `M${f(a.x)},${f(a.y)}L${f(ex)},${f(ey)}` : '')
  }
}

// ── the handoff from the timeline's four-papers step ─────────────────
// Arriving from that step (INTRO_STEP['four-papers']), the four lit cards
// are still on screen in the leaving timeline layer: each of this page's
// cards starts exactly over its timeline twin and flies to its place in
// the top-left row (a FLIP), while the timeline fades out under it — the
// eye stays on the same four pages, in the same colours. From anywhere
// else (a deep link, back from the revisit) the cards rise in as before.
const cardsEl = ref<HTMLElement | null>(null)
const flipping = ref(false)
const FLIP_MS = 1150
function flipFromTimeline(): void {
  const src = new Map<string, Element>()
  document.querySelectorAll('.lit-timeline.focus4 .lt-paper[data-id]').forEach((el) => {
    const id = (el as HTMLElement).dataset.id
    if (id && IDS.includes(id as CouplingPaperId)) src.set(id, el)
  })
  if (src.size !== IDS.length || !cardsEl.value) return
  flipping.value = true // no rise animation: the cards are placed now
  const cards = [...cardsEl.value.querySelectorAll<HTMLElement>('.cpl-card[data-id]')]
  cards.forEach((card, i) => {
    const from = src.get(card.dataset.id!)!
    const page = from.querySelector('.lt-page')?.getBoundingClientRect()
    const wrap = card.querySelector('.cpl-page-wrap')?.getBoundingClientRect()
    if (!page || !wrap || wrap.width === 0) return
    const c = card.getBoundingClientRect()
    const s = page.width / wrap.width
    // Scale about the card's top-left, then move its page onto the twin's.
    const tx = page.left - c.left - s * (wrap.left - c.left)
    const ty = page.top - c.top - s * (wrap.top - c.top)
    ;(from as HTMLElement).style.visibility = 'hidden'
    card.animate(
      [
        { transformOrigin: '0 0', transform: `translate(${tx}px, ${ty}px) scale(${s})` },
        { transformOrigin: '0 0', transform: 'translate(0, 0) scale(1)' },
      ],
      { duration: FLIP_MS, delay: i * 45, easing: 'cubic-bezier(0.45, 0, 0.2, 1)', fill: 'backwards' },
    )
  })
}

onMounted(() => {
  window.addEventListener('resize', onResize)
  raf = window.requestAnimationFrame(draw)
  flipFromTimeline()
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  if (raf !== null) window.cancelAnimationFrame(raf)
  raf = null
})
</script>

<style scoped>
.cpl {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.cpl-map {
  position: absolute;
  inset: 0;
  opacity: 0;
  transition: opacity 0.8s ease;
}
.cpl-map.on {
  opacity: 1;
}

.cpl-svg {
  position: absolute;
  inset: 0;
  overflow: visible;
}

/* ---- footprints ------------------------------------------------------- */
.cpl-shape {
  transition: opacity 0.3s;
}
.cpl-shape.dim {
  opacity: 0.22;
}
.cpl-shape .halo {
  fill: none;
  stroke: rgba(0, 0, 0, 0.75);
  stroke-linejoin: round;
  stroke-linecap: round;
}
.cpl-shape .main {
  fill: none;
  stroke: var(--c);
  stroke-linejoin: round;
  stroke-linecap: round;
  transition: stroke-width 0.25s, fill-opacity 0.25s;
}

/* The tensile shock: a filled region. */
.k-area .halo {
  stroke-width: 5;
}
.k-area .main {
  fill: var(--c);
  fill-opacity: 0.32;
  stroke-width: 2.2;
  pointer-events: visiblePainted;
}
.k-area.lit .main {
  fill-opacity: 0.5;
  stroke-width: 3;
}

/* A model domain / region of interest: dashed, the whole inside hoverable. */
.k-outline .halo {
  stroke-width: 5.4;
  stroke-dasharray: 9 6;
}
.k-outline .main {
  stroke-width: 2.4;
  stroke-dasharray: 9 6;
}
/* Only the line itself is a hover target (its dark halo is the wider
   hit band) — the boxes' insides cover most of the map. */
.k-outline .halo {
  pointer-events: stroke;
}
.k-outline.lit .main {
  stroke-width: 3.2;
}

/* Lakes. */
.k-dots .halo {
  stroke-width: 2.6;
}
.k-dots .main {
  fill: var(--c);
  stroke: rgba(10, 12, 16, 0.55);
  stroke-width: 0.6;
  pointer-events: visiblePainted;
}
.k-dots.big .main {
  stroke: #fff;
  stroke-width: 1;
}

/* Receivers. */
.k-stations .halo {
  stroke-width: 2.4;
}
.k-stations .main {
  fill: #0d1015;
  stroke: var(--c);
  stroke-width: 1.8;
  pointer-events: visiblePainted;
}

/* A blister's true radius. */
.k-ring .halo {
  stroke-width: 4.6;
}
.k-ring .main {
  fill: var(--c);
  fill-opacity: 0.16;
  stroke-width: 2.2;
  pointer-events: visiblePainted;
}

/* The scale rule. */
.k-rule .halo {
  stroke-width: 5.5;
}
.k-rule .main {
  stroke-width: 2.4;
  pointer-events: stroke;
}

/* ---- the loupe ---------------------------------------------------------- */
.cpl-loupe-bg {
  fill: rgba(8, 10, 14, 0.86);
}
.cpl-loupe-rim {
  fill: none;
  stroke: rgba(236, 231, 219, 0.85);
  stroke-width: 2;
}
.cpl-loupe-ring {
  fill: none;
  stroke: rgba(246, 243, 236, 1);
  stroke-width: 2;
}
.cpl-loupe-lead {
  fill: none;
  stroke: rgba(246, 243, 236, 0.95);
  stroke-width: 1.8;
  stroke-dasharray: 5 4;
}
/* A dark under-stroke so the light lines hold on white ice. */
.cpl-loupe-ring.halo,
.cpl-loupe-lead.halo {
  stroke: rgba(0, 0, 0, 0.7);
  stroke-width: 4.5;
  stroke-dasharray: none;
}
.cpl-loupe-name {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.04em;
  fill: var(--s24, #5fe3c0);
  paint-order: stroke;
  stroke: rgba(0, 0, 0, 0.9);
  stroke-width: 4px;
  transition: opacity 0.3s;
}
.cpl-loupe-name.dim {
  opacity: 0.25;
}
/* Inside the loupe the marks are drawn at the loupe's scale. */
.in-loupe.k-stations .main {
  stroke-width: 1.9;
}

/* ---- the legend -------------------------------------------------------- */
/* Under the site-wide BACK/NEXT pair, in their gutter: the pills sit at
   1.2vh + (nav − lm)/2 (Explore .beat-nav) and are --lm-h tall; on
   narrower viewports (≤ 1680 px) they drop to the sub-menu's row. */
.cpl-legend {
  position: absolute;
  right: 2vw;
  top: calc(1.2vh + (var(--nav-h) - var(--lm-h)) / 2 + var(--lm-h) + 0.65rem);
  display: flex;
  flex-direction: column;
  gap: 0.18rem;
  padding: 0.55rem 0.85rem 0.6rem 0.7rem;
  border-radius: 10px;
  background: rgba(8, 10, 14, 0.86);
  border: 1.5px solid rgba(236, 231, 219, 0.35);
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.5);
  pointer-events: none;
}
@media (max-width: 1680px) {
  .cpl-legend { top: calc(1.2vh + var(--nav-h) + var(--lm-gap) + var(--lm-h) + 0.65rem); }
}
.cpl-legend-row {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}
.cpl-legend-glyph {
  flex: none;
  overflow: visible;
}
.cpl-legend-text {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 15px;
  font-weight: 500;
  letter-spacing: 0.04em;
  color: rgba(236, 231, 219, 0.92);
  white-space: nowrap;
}
/* the glyphs: ice-white strokes ≥ 1.6 px, translucent white fills */
.cpl-legend-glyph :deep(.lg-fill) { fill: rgba(236, 231, 219, 0.95); stroke: rgba(10, 12, 16, 0.6); stroke-width: 0.6; }
.cpl-legend-glyph :deep(.lg-big) { stroke: #fff; stroke-width: 1.2; }
.cpl-legend-glyph :deep(.lg-tri) { fill: #0d1015; stroke: rgba(236, 231, 219, 0.95); stroke-width: 1.8; stroke-linejoin: round; }
.cpl-legend-glyph :deep(.lg-ring) { fill: rgba(236, 231, 219, 0.16); stroke: rgba(236, 231, 219, 0.95); stroke-width: 1.8; }
.cpl-legend-glyph :deep(.lg-dash) { fill: none; stroke: rgba(236, 231, 219, 0.95); stroke-width: 1.8; stroke-dasharray: 4 2.6; stroke-linejoin: round; }
.cpl-legend-glyph :deep(.lg-area) { fill: rgba(236, 231, 219, 0.32); stroke: rgba(236, 231, 219, 0.95); stroke-width: 1.6; stroke-linejoin: round; }
.cpl-legend-glyph :deep(.lg-rule) { fill: none; stroke: rgba(236, 231, 219, 0.95); stroke-width: 1.8; stroke-linecap: round; }
.cpl-legend-glyph :deep(.lg-loupe) { fill: rgba(8, 10, 14, 0.6); stroke: rgba(236, 231, 219, 0.9); stroke-width: 1.6; }
.cpl-legend-glyph :deep(.lg-lead) { fill: none; stroke: rgba(236, 231, 219, 0.9); stroke-width: 1.3; stroke-dasharray: 2.4 1.8; }
.cpl-legend-glyph :deep(.lg-dotsm) { fill: rgba(236, 231, 219, 0.95); }

/* ---- labels ----------------------------------------------------------- */
.cpl-label {
  position: absolute;
  left: 0;
  top: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.1rem;
  pointer-events: auto;
  cursor: default;
  white-space: nowrap;
  /* A dark plate edged in the paper's colour: the pastel numbers sit on
     white ice, and a shadow alone left "≈ 5 km" a grey smudge from the
     back of the room (the talk is projected for ~50 people). */
  padding: 0.3rem 0.75rem 0.4rem;
  border-radius: 0.6rem;
  background: rgba(6, 7, 10, 0.8);
  border: 1.5px solid color-mix(in srgb, var(--c) 75%, transparent);
  box-shadow: 0 2px 14px rgba(0, 0, 0, 0.55);
  transition: opacity 0.3s;
  will-change: transform;
}
.cpl-label.dim {
  opacity: 0.25;
}
.cpl-label-who {
  font-size: clamp(0.9rem, 1.05vw, 1.15rem);
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--c);
}
.cpl-label-len {
  font-family: 'EB Garamond', serif;
  font-size: clamp(1.9rem, 2.6vw, 2.9rem);
  font-weight: 600;
  line-height: 1;
  color: var(--c);
}
.cpl-leaders {
  pointer-events: none;
}
.cpl-leader {
  fill: none;
  stroke: var(--c);
  stroke-width: 2;
  opacity: 0.95;
  /* a dark edge so the light leaders hold on white ice */
  filter: drop-shadow(0 0 1.5px rgba(0, 0, 0, 0.95));
  transition: opacity 0.3s;
}
.cpl-leader.dim {
  opacity: 0.18;
}

/* ---- the four cards ---------------------------------------------------- */
.cpl-cards {
  position: absolute;
  left: 22px;
  /* Clear of the ribbon's sub-menu (Explore's BeatLandmarks bar, whose
     left end reaches over the first cards; Explore --chrome-bottom). */
  top: max(76px, calc(var(--chrome-bottom, 0px) + 0.75rem));
  display: flex;
  gap: 14px;
  --paper: #ece7db;
  --ink: #1c1a16;
}
.cpl-card {
  position: relative;
  display: block;
  width: var(--cw);
  pointer-events: auto;
  text-decoration: none;
  color: inherit;
  transform-origin: 50% 0;
  transition: transform 0.3s, filter 0.3s;
  filter: brightness(0.86) saturate(0.85);
  animation: cpl-rise 0.6s cubic-bezier(0.2, 0.7, 0.2, 1) both;
  animation-delay: calc(0.25s + var(--i) * 0.07s);
}
.cpl-card.lit {
  filter: none;
  transform: translateY(4px) scale(1.06);
  z-index: 2;
}
.cpl-card.dim {
  filter: brightness(0.45) saturate(0.4);
}
.cpl-pill {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: 0 auto 7px;
  width: max-content;
  max-width: calc(var(--cw) + 30px);
  padding: 0.18rem 0.6rem;
  border-radius: 8px;
  background: rgba(7, 8, 11, 0.9);
  border: 1px solid var(--c);
  color: var(--c);
  font-size: 0.82rem;
  line-height: 1.2;
  white-space: nowrap;
}
.cpl-pill-name {
  font-weight: 600;
}
.cpl-pill-year {
  font-size: 0.86em;
  letter-spacing: 0.1em;
  opacity: 1;
}
.cpl-page-wrap {
  position: relative;
  height: calc(var(--cw) * 1.5);
  border-top: 4px solid var(--c);
  border-radius: 2px;
}
.cpl-page {
  position: absolute;
  inset: 0;
}
.cpl-card.lit .cpl-page {
  box-shadow:
    0 0 0 1.5px var(--c),
    0 16px 36px rgba(0, 0, 0, 0.65);
}
.cpl-cards.flip .cpl-card {
  animation: none;
}
@keyframes cpl-rise {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
}
</style>
