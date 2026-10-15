<template>
  <!-- The literature timeline (Introduction).
       Years along the bottom, title-page cards along the top in
       chronological order, each card joined to its year by a branch;
       above each card its author/year pill, and above the pills the
       citation arcs — one arc per (citing → cited) pair in the papers'
       reference lists, nothing editorial (the director's rule). HOVER is
       the highlight (the director's choice): the hovered card lifts, its pill
       POPS to roughly twice its size (readable from the back of the
       room — the reason the pills moved above the cards; the pop keeps
       ONE on-screen size however many cards share the row — see POP_ROW), its
       label/branch/year go gold, the arcs to the papers it cites draw
       in from it with a chevron at the cited end, the arcs from the
       papers that cite it glow faintly, and its one-line summary (the
       director's words, config/timeline.ts; none for the director's own paper) appears under
       the row. Each card's lower half is a hand-drawn
       cartoon of the paper's defining figure (TimelineFigure.vue).
       Click opens the DOI in a new tab. Labels are the figure (narrator
       rule); the summaries are the director's own exception to it.
       On the Introduction's first visit NEXT walks that same highlight
       across the cards left → right, one per press (`walk`); a hover
       overrides it while the mouse is on a card.
       A layer ABOVE the Globe, never a veil on it — the globe keeps
       rendering underneath (see Explore.vue's flat-layer note). -->
  <div
    ref="rootRef"
    class="lit-timeline"
    :class="{ focus4: focusOn }"
    :style="{
      '--lift': `${HOT_LIFT}px`,
      '--hot-scale': hotScale,
      '--label-hot': labelHot,
      '--focus-scale': focusScale,
      '--label-focus': focusLayout.scale,
    }"
  >
    <div class="lt-backdrop" />

    <svg
      v-if="W > 0"
      class="lt-svg"
      :viewBox="`0 0 ${W} ${H}`"
      :width="W"
      :height="H"
      aria-hidden="true"
    >
      <!-- Citation arcs, drawn citing → cited: base (always faint) + a
           gold overlay that draws in from the hovered (citing) paper,
           and a chevron landing on the cited paper's pill. The glow is
           a wide translucent HALO stroke, not an SVG blur filter — a
           feGaussianBlur on these paths stalled the raster thread for
           ~0.95 s at mount (rAF gap with an idle main thread). -->
      <g class="lt-arcs">
        <template v-for="a in arcs" :key="a.key">
          <path :d="a.d" class="lt-arc-base" />
          <path
            :d="a.d"
            pathLength="1"
            class="lt-arc-hot lt-halo"
            :class="{ on: a.hot, out: a.warm }"
          />
          <path
            :d="a.d"
            pathLength="1"
            class="lt-arc-hot"
            :class="{ on: a.hot, out: a.warm }"
          />
          <path :d="a.tip" class="lt-arc-tip" :class="{ on: a.hot }" />
        </template>
      </g>

      <!-- Branches: card → its year on the axis. -->
      <g class="lt-branches">
        <template v-for="b in branches" :key="b.id">
          <path
            :d="b.d"
            pathLength="1"
            class="lt-branch-base"
            :style="{ '--i': b.i }"
          />
          <path
            :d="b.d"
            pathLength="1"
            class="lt-branch-hot lt-halo"
            :class="{ on: b.hot || !!b.fc, fc: !!b.fc }"
            :style="b.fc ? { '--fc': b.fc } : undefined"
          />
          <path
            :d="b.d"
            pathLength="1"
            class="lt-branch-hot"
            :class="{ on: b.hot || !!b.fc, fc: !!b.fc }"
            :style="b.fc ? { '--fc': b.fc } : undefined"
          />
        </template>
      </g>

      <!-- Year axis. -->
      <g class="lt-axis">
        <line :x1="axisX0" :x2="axisX1" :y1="axisY" :y2="axisY" class="lt-axis-line" />
        <template v-for="t in ticks" :key="t.year">
          <line
            :x1="t.x" :x2="t.x"
            :y1="axisY - (t.major ? 7 : 4)" :y2="axisY + (t.major ? 7 : 4)"
            class="lt-tick" :class="{ major: t.major }"
          />
          <text
            v-if="t.label"
            :x="t.x" :y="axisY + 24"
            class="lt-year"
            :class="{ major: t.major, hot: t.hot, fc: !!t.fc }"
            :style="t.fc ? { fill: t.fc } : undefined"
            text-anchor="middle"
          >{{ t.year }}</text>
        </template>
      </g>
    </svg>

    <!-- The highlighted paper's summary (the director's request):
         shown only while a card is highlighted (hovered or walked),
         crossfaded between cards. Now a ≤ 5-word bullet, a notch larger
         (the director judged that nobody would read a full sentence). -->
    <Transition name="lt-cap">
      <div
        v-if="hiPaper && hiPaper.summary"
        :key="hiPaper.id"
        class="lt-caption"
        :style="{ top: `${captionY}px` }"
      >
        <span class="lt-cap-who">{{ hiPaper.label }}</span>
        <span class="lt-cap-dot" aria-hidden="true">•</span>
        <span class="lt-cap-text">{{ hiPaper.summary }}</span>
      </div>
    </Transition>

    <!-- Pill + title-page card, one anchor per paper. The anchor's
         transform origin is its bottom edge, so the hot lift + scale
         carry the pill up with the card; the pill then scales again
         about ITS bottom edge (the gap above the page). -->
    <a
      v-for="c in cards"
      :key="c.paper.id"
      class="lt-paper"
      :class="{ hot: c.hot, dim: c.dim, rest: c.rest, focus: !!c.fc }"
      :data-id="c.paper.id"
      :style="{
        left: `${c.x}px`,
        top: `${anchorTop}px`,
        width: `${cardW}px`,
        height: `${anchorH}px`,
        '--i': c.i,
        '--cw': `${cardW}px`,
        '--slot': `${slot}px`,
        '--lf': `${labelFont}px`,
        '--pill': `${pillH}px`,
        '--band': `${labelBand}px`,
        '--dx': `${c.dx}px`,
        ...(c.fc ? { '--fc': c.fc } : {}),
      }"
      :href="c.url ?? undefined"
      :target="c.url ? '_blank' : undefined"
      rel="noopener noreferrer"
      @mouseenter="hoverIdx = c.i"
      @mouseleave="hoverIdx = -1"
    >
      <div class="lt-label-slot">
        <div class="lt-label">
          <!-- (The revisit's "Chapter 1" eyebrow over Rines 2026 is gone —
               the director wanted the pop-out to look just like all the
               others; the NEXT pill says "Ch. 1 →" there anyway.) -->
          <span class="lt-label-name">{{ c.labelName }}</span>
          <span class="lt-label-year">{{ c.paper.year }}</span>
        </div>
      </div>
      <TimelinePage :paper="c.paper" />
    </a>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  TIMELINE_PAPERS,
  TIMELINE_YEAR_MAX,
  TIMELINE_YEAR_MIN,
  paperUrl,
} from '../config/timeline'
import { COUPLING_PAPERS } from '../config/couplingLength'
import TimelinePage from './TimelinePage.vue'

const props = defineProps<{
  /** The Introduction's SECOND visit (after the coupling-length step):
   *  Rines 2026 is highlighted exactly as a hovered card is — no eyebrow,
   *  no caption (the director wanted the pop-out to look just like all
   *  the others; the takeaway card pops over it, Explore.vue). On the
   *  first visit it is a card like any other — shown, hoverable, never
   *  walked. */
  revisit?: boolean
  /** The first visit's walk (config/introSteps.ts INTRO_WALK): the paper
   *  id NEXT has reached, highlighted as if hovered; null = none. */
  walk?: string | null
  /** The four-papers step (the director's request): the coupling step's four
   *  papers lit together, each in its comparison-page colour (card
   *  outline + glow, pill, branch, year), every other card dimmed — to
   *  tell the viewer that the talk is about to dive a little deeper into
   *  these four papers. A hover still highlights the hovered card meanwhile. */
  focus?: boolean
}>()

/** The paper the Introduction ends on — Chapter 1. */
const FINAL_ID = 'rines2026'

const rootRef = ref<HTMLElement | null>(null)
const W = ref(0)
const H = ref(0)
const hoverIdx = ref(-1)

let ro: ResizeObserver | null = null
function measure(): void {
  const el = rootRef.value
  if (!el) return
  W.value = el.clientWidth
  H.value = el.clientHeight
  // The pills' widths follow the font size, which follows W: read them
  // once Vue has applied the new --lf.
  void nextTick(measureLabels)
}
const onFontsDone = (): void => measureLabels()
onMounted(() => {
  measure()
  ro = new ResizeObserver(measure)
  if (rootRef.value) ro.observe(rootRef.value)
  // Inter arrives after first paint: re-measure the pills when it lands.
  document.fonts?.ready.then(onFontsDone)
  document.fonts?.addEventListener('loadingdone', onFontsDone)
})
onBeforeUnmount(() => {
  ro?.disconnect()
  ro = null
  document.fonts?.removeEventListener('loadingdone', onFontsDone)
})

// Left-to-right = chronological, whatever order the config is in: two
// papers from the same year once sat in narration order while their
// branches went to their months and crossed (the 2008 pair).
const papers = [...TIMELINE_PAPERS].sort(
  (a, b) => a.when - b.when || TIMELINE_PAPERS.indexOf(a) - TIMELINE_PAPERS.indexOf(b),
)
const N = papers.length
const idIndex = new Map(papers.map((p, i) => [p.id, i]))

// The highlighted paper IS the hovered card (-1 = none) — whenever nothing
// is hovered, the walked paper, or on the revisit Rines 2026.
const finalIdx = papers.findIndex((p) => p.id === FINAL_ID)
const walkIdx = computed(() => (props.walk ? idIndex.get(props.walk) ?? -1 : -1))
const hi = computed(() => (hoverIdx.value >= 0 ? hoverIdx.value : props.revisit ? finalIdx : walkIdx.value))
const hiPaper = computed(() => (hi.value >= 0 ? papers[hi.value] : null))

// The four-papers step: the coupling papers' colours (config/couplingLength.ts).
const FOCUS_COLOR = new Map<string, string>(COUPLING_PAPERS.map((p) => [p.id, p.color]))
const focusOn = computed(() => !!props.focus && hoverIdx.value < 0)
/** Lit paper i's colour on the four-papers step (null = not lit). */
function focusColor(i: number): string | null {
  return focusOn.value ? FOCUS_COLOR.get(papers[i].id) ?? null : null
}
// Four neighbouring cards lit at once: a smaller lift than one hovered card
// (they would overlap), and their pills scaled for the back row — on ONE
// row (the director disliked the staggered names and asked for them
// all on one row). Four 1.5× pills are wider than their card slots,
// so each slides sideways from its card's centre, as little as possible,
// FOCUS_GAP between neighbours; the two dim neighbours' pills (Stevens
// 2015, Rines 2026) step aside when the row needs the room, and only if
// even that is not enough (a narrow window) do the four scale down, just
// enough to fit. Pill widths are measured (the resolved CSS width —
// transform-free); the shifts are the 1-D packing with the least total
// squared displacement (pool adjacent violators), the row walled by the
// next pills outward. See focusLayout.
const FOCUS_CARD = 1.1 // a lit card ÷ a POP_ROW resting card (see POP_ROW)
const FOCUS_LABEL = 1.5 // a lit pill ÷ that card's pill, on top of FOCUS_CARD
const FOCUS_GAP = 8
/** Lit neighbours never touch: the least gap between two lit cards. */
const FOCUS_CARD_GAP = 8
/** How far a pill may slide from its card's centre, as a fraction of the
 *  card slot: past this it would read as the neighbour's pill, so the
 *  four scale down instead. */
const FOCUS_SHIFT_MAX = 0.3
/** The lit papers' indices, left → right (consecutive on the timeline). */
const focusIdx = papers.map((p, i) => (FOCUS_COLOR.has(p.id) ? i : -1)).filter((i) => i >= 0)

/** Each pill's natural width (unscaled layout px), measured from the DOM:
 *  text + padding at the current --lf, so it follows the font load and
 *  every resize (labelFont is a function of W). */
const labelW = ref<number[]>([])
function measureLabels(): void {
  const root = rootRef.value
  if (!root) return
  const els = root.querySelectorAll<HTMLElement>('.lt-paper .lt-label')
  if (els.length !== N) return
  // The resolved width is fractional and ignores transforms (offsetWidth
  // rounds, and half a pixel per pill eats the gaps).
  const next = [...els].map((el) => parseFloat(getComputedStyle(el).width) || el.offsetWidth)
  if (next.some((w, i) => w !== labelW.value[i])) labelW.value = next
}

/** One pill of the chain the packing solves: its target x (the card's
 *  centre) and its on-screen width. */
interface ChainPill {
  target: number
  w: number
}
/** Pills packed left → right with FOCUS_GAP between them, each as near its
 *  target as the packing allows (least total squared displacement, PAV).
 *  Returns the pills' centres. */
function packPills(pills: ChainPill[]): number[] {
  // A block = a run of pills packed edge to edge; `off` = each pill's
  // centre relative to the block's first pill's centre; `pos` = the first
  // pill's centre = mean over the block of (target − off).
  const blocks: { a: number; b: number; off: number[]; pos: number }[] = []
  pills.forEach((p, k) => {
    let blk = { a: k, b: k, off: [0], pos: p.target }
    while (blocks.length) {
      const prev = blocks[blocks.length - 1]
      const prevLastC = prev.pos + prev.off[prev.off.length - 1]
      const prevRight = prevLastC + pills[prev.b].w / 2
      const left = blk.pos - pills[blk.a].w / 2
      if (prevRight + FOCUS_GAP <= left) break
      // Merge: re-chain the offsets across the two blocks.
      blocks.pop()
      const off = [...prev.off]
      let last = off[off.length - 1]
      for (let j = blk.a; j <= blk.b; j++) {
        last += pills[j - 1].w / 2 + FOCUS_GAP + pills[j].w / 2
        off.push(last)
      }
      let sum = 0
      for (let j = prev.a; j <= blk.b; j++) sum += pills[j].target - off[j - prev.a]
      blk = { a: prev.a, b: blk.b, off, pos: sum / (blk.b - prev.a + 1) }
    }
    blocks.push(blk)
  })
  const out: number[] = []
  for (const blk of blocks) for (const o of blk.off) out.push(blk.pos + o)
  return out
}

/** The four-papers row: each paper's pill shift (screen px, 0 = on its
 *  card's centre) and the lit pills' scale. */
const focusLayout = computed(() => {
  const dx = papers.map(() => 0)
  const zero = { dx, scale: labelFocus.value }
  const widths = labelW.value
  if (!focusOn.value || widths.length !== N || focusIdx.length === 0 || W.value <= 0) return zero
  const lo = focusIdx[0]
  const hi = focusIdx[focusIdx.length - 1]
  // The chain: the dim neighbour either side (if any) + the lit papers.
  const chain: number[] = []
  if (lo > 0) chain.push(lo - 1)
  chain.push(...focusIdx)
  if (hi < N - 1) chain.push(hi + 1)
  // The walls: the next pills outward, at rest, or the viewport's edges.
  const wallL = lo > 1 ? cx(lo - 2) + widths[lo - 2] / 2 + FOCUS_GAP : FOCUS_GAP
  const wallR = hi < N - 2 ? cx(hi + 2) - widths[hi + 2] / 2 - FOCUS_GAP : W.value - FOCUS_GAP
  const solve = (s: number): number[] | null => {
    // On screen a lit pill is its natural width × the pill scale × the
    // anchor's focusScale; a dim neighbour's is its natural width.
    const pills = chain.map((i) => ({
      target: cx(i),
      w: widths[i] * (FOCUS_COLOR.has(papers[i].id) ? s * focusScale.value : 1),
    }))
    const c = packPills(pills)
    const left = c[0] - pills[0].w / 2
    const right = c[c.length - 1] + pills[pills.length - 1].w / 2
    if (right - left > wallR - wallL) return null
    // The packing is the least displacement; keep it inside the walls.
    const shift = Math.max(0, wallL - left) - Math.max(0, right - wallR)
    const out = c.map((x) => x + shift)
    // No pill may leave its card: past the cap the row is too wide.
    const cap = FOCUS_SHIFT_MAX * slot.value
    if (out.some((x, k) => Math.abs(x - pills[k].target) > cap)) return null
    return out
  }
  let scale = labelFocus.value
  let centres = solve(scale)
  if (!centres) {
    // Too wide even with the neighbours aside (a narrow window): the
    // largest scale that fits, by bisection.
    let good = 1
    let bad = labelFocus.value
    for (let k = 0; k < 14; k++) {
      const mid = (good + bad) / 2
      if (solve(mid)) good = mid
      else bad = mid
    }
    scale = good
    centres = solve(scale) ?? chain.map((i) => cx(i))
  }
  const c = centres
  chain.forEach((i, k) => {
    dx[i] = c[k] - cx(i)
  })
  return { dx, scale }
})

/** The popped pill stays on screen: the first and last cards' pills are
 *  wider than the room beside them once popped (narrow slots, narrow
 *  windows), so the pill slides inward, just enough to keep POP_EDGE of
 *  margin. Screen px; 0 for every card away from the edges. */
const POP_EDGE = 10
const hotDx = computed(() => {
  const i = hi.value
  const w = labelW.value[i]
  if (i < 0 || !w || W.value <= 0) return 0
  const half = (w * labelHot.value * hotScale.value) / 2
  const lo = POP_EDGE + half
  const hiX = W.value - POP_EDGE - half
  if (lo > hiX) return W.value / 2 - cx(i)
  return Math.min(hiX, Math.max(lo, cx(i))) - cx(i)
})

// The highlighted anchor lifts + grows (CSS transform, origin at its
// bottom edge) and its pill grows again on top of that; the SVG needs
// the same numbers so branch and arcs meet the moved edges.
const HOT_LIFT = 12
// THE POP KEEPS ITS SIZE (when Schoof 2010 made the row eleven, the
// director asked for smaller paper icons with the pop-out kept at one
// size for every card as NEXT steps through). The pop was tuned on
// a row of POP_ROW cards: the popped card is POP_CARD × that row's resting
// card and its pill POP_LABEL × that row's pill on top. A longer row has
// narrower slots and smaller resting cards, so the scales below are
// whatever takes TODAY's resting card and pill to that same on-screen
// size; the cards stand on the same baseline (cardBottom), so the pop
// lands where it always did.
const POP_ROW = 10
const POP_CARD = 1.28
const POP_LABEL = 1.9

// ---- geometry ---------------------------------------------------------
const padX = computed(() => Math.max(36, W.value * 0.035))
const span = computed(() => Math.max(1, W.value - 2 * padX.value))
const slot = computed(() => span.value / N)
/** A resting card's width on a row of n cards. */
const cardWFor = (n: number): number => Math.max(84, Math.min(158, (span.value / n) * 0.84))
/** The pill's font size on a card that wide. */
const labelFontFor = (cw: number): number => Math.max(10.5, Math.min(13.5, cw * 0.084))
const cardW = computed(() => cardWFor(N))
const cardH = computed(() => cardW.value * 1.5)
/** The POP_ROW resting card the pop sizes are measured from. */
const refCardW = computed(() => cardWFor(Math.min(N, POP_ROW)))
// The pill: two lines (name / year), a fixed height the CSS mirrors via
// --pill so the arcs can land on its top edge without measuring DOM.
// On slots narrower than REST_PILL_SLOT the two widest neighbouring pills
// (Christoffersen et al. · Stevens et al.) would touch at rest, so the
// resting font follows the slot down; the pop is unaffected (labelHot is
// measured from the POP_ROW pill, not from this).
const REST_PILL_SLOT = 113
const labelFont = computed(() => labelFontFor(cardW.value) * Math.min(1, slot.value / REST_PILL_SLOT))
const pillH = computed(() => Math.round(labelFont.value * 2.96 + 2))
const LABEL_GAP = 7
const labelBand = computed(() => pillH.value + LABEL_GAP)
const hotScale = computed(() => (POP_CARD * refCardW.value) / cardW.value)
const labelHot = computed(
  () => (POP_LABEL * POP_CARD * labelFontFor(refCardW.value)) / (hotScale.value * labelFont.value),
)
// The four-papers step: the lit cards at their POP_ROW size too, as far
// as four NEIGHBOURS can be (FOCUS_CARD_GAP between them); their pills
// start from the POP_ROW size and the row packing takes it from there.
const focusScale = computed(() =>
  Math.max(1, Math.min((FOCUS_CARD * refCardW.value) / cardW.value, (slot.value - FOCUS_CARD_GAP) / cardW.value)),
)
const labelFocus = computed(
  () => (FOCUS_LABEL * FOCUS_CARD * labelFontFor(refCardW.value)) / (focusScale.value * labelFont.value),
)
// Card band: below the header band (top nav + the section title row),
// above the branch zone. Pills sit on the cards; arcs live above them.
// The band's BASELINE is the POP_ROW row's: shorter cards stand on it.
const cardBottom = computed(() => Math.round(H.value * 0.365) + refCardW.value * 1.5)
const cardTop = computed(() => cardBottom.value - cardH.value)
const anchorTop = computed(() => cardTop.value - labelBand.value)
const anchorH = computed(() => labelBand.value + cardH.value)
const axisY = computed(() => Math.round(H.value * 0.82))
const captionY = computed(() => cardBottom.value + 44)
const axisX0 = computed(() => padX.value)
const axisX1 = computed(() => W.value - padX.value)

function cx(i: number): number {
  return padX.value + (i + 0.5) * slot.value
}
function xYear(y: number): number {
  const f = (y - TIMELINE_YEAR_MIN) / (TIMELINE_YEAR_MAX - TIMELINE_YEAR_MIN)
  return padX.value + f * span.value
}

// ---- cards -------------------------------------------------------------
const cards = computed(() =>
  papers.map((p, i) => ({
    paper: p,
    i,
    x: cx(i) - cardW.value / 2,
    url: paperUrl(p),
    // "Das et al." on the pill's first line; the year is the second.
    labelName: p.label.replace(/,?\s*\d{4}$/, ''),
    hot: i === hi.value,
    dim: (hi.value >= 0 && i !== hi.value) || (focusOn.value && !focusColor(i)),
    rest: hi.value < 0 && !focusOn.value,
    fc: focusColor(i),
    // The four-papers row's sideways shift, in the anchor's own px: a lit
    // anchor is scaled by focusScale about its centre line, so its
    // slot's translate is divided out to land on the screen shift. The
    // popped pill's own shift (hotDx) rides the hot anchor's scale.
    dx: focusColor(i) ? focusLayout.value.dx[i] / focusScale.value : i === hi.value ? hotDx.value / hotScale.value : focusLayout.value.dx[i],
  })),
)

// ---- branches: card bottom → year on the axis --------------------------
const branches = computed(() =>
  papers.map((p, i) => {
    const x0 = cx(i)
    const y0 = cardBottom.value + 10 - (i === hi.value || focusColor(i) ? HOT_LIFT : 0)
    const x1 = xYear(p.when)
    const y1 = axisY.value - 12
    // Vertical-tangent S-curve: leaves the card straight down, lands
    // on the tick straight up.
    const ym = (y0 + y1) / 2
    const d = `M ${x0} ${y0} C ${x0} ${ym}, ${x1} ${ym}, ${x1} ${y1}`
    return {
      id: p.id,
      i,
      d,
      hot: i === hi.value,
      fc: focusColor(i),
    }
  }),
)

// ---- citation arcs above the pills ---------------------------------------
const arcs = computed(() => {
  const out: { key: string; d: string; tip: string; hot: boolean; warm: boolean }[] = []
  // Arc ends: just above a pill's top edge — at rest, or lifted + scaled
  // twice (anchor, then pill) when that paper is the hovered one.
  const restY = anchorTop.value - 3
  const hotY =
    cardBottom.value -
    HOT_LIFT -
    hotScale.value * (cardH.value + LABEL_GAP + labelHot.value * pillH.value) -
    3
  // The four-papers row: the lit pills' top edge (lifted + scaled by the
  // focus numbers), and every pill's sideways shift along that row.
  const lay = focusLayout.value
  const litY =
    cardBottom.value -
    HOT_LIFT -
    focusScale.value * (cardH.value + LABEL_GAP + lay.scale * pillH.value) -
    3
  const endX = (i: number): number => cx(i) + (i === hi.value ? hotDx.value : lay.dx[i])
  const endY = (i: number): number =>
    i === hi.value ? hotY : focusColor(i) ? litY : restY
  const ceiling = H.value * 0.15 // keep clear of the header band
  const maxPeak = Math.max(24, restY - ceiling)
  papers.forEach((p, citing) => {
    for (const id of p.cites) {
      const cited = idIndex.get(id)
      if (cited === undefined) continue
      const xa = endX(citing)
      const xb = endX(cited)
      const dx = Math.abs(xb - xa)
      // A citation of a paper that is not out yet (a preprint) is the
      // reverse half of a mutual pair; lift it so both arcs show.
      const forward = papers[cited].when >= p.when
      let peak = (18 + dx * 0.09) * (forward ? 1.8 : 1)
      peak = Math.min(peak, maxPeak)
      const ya = endY(citing)
      const yb = endY(cited)
      // Quadratic; its apex sits halfway to the control point. A lifted
      // end still gets an arch above it.
      let cy = restY - 2 * peak
      cy = Math.min(cy, Math.min(ya, yb) - 40)
      cy = Math.max(cy, ceiling - 30)
      const mx = (xa + xb) / 2
      const d = `M ${xa} ${ya} Q ${mx} ${cy}, ${xb} ${yb}`
      // The chevron at the cited end follows the end tangent (P2 − P1).
      const tx = xb - mx
      const ty = yb - cy
      const L = Math.hypot(tx, ty) || 1
      const ux = tx / L
      const uy = ty / L
      const s = 6
      const bx = xb - ux * s
      const by = yb - uy * s
      const px = -uy
      const py = ux
      const tip = `M ${bx + px * s * 0.55} ${by + py * s * 0.55} L ${xb} ${yb} L ${bx - px * s * 0.55} ${by - py * s * 0.55}`
      out.push({
        key: `${p.id}->${id}`,
        d,
        tip,
        hot: citing === hi.value,
        warm: cited === hi.value,
      })
    }
  })
  return out
})

// ---- year axis ----------------------------------------------------------
const paperYears = new Set(papers.map((p) => p.year))
const ticks = computed(() => {
  const y0 = Math.ceil(TIMELINE_YEAR_MIN)
  const y1 = Math.floor(TIMELINE_YEAR_MAX)
  const hotYear = hi.value >= 0 ? papers[hi.value].year : -1
  const out: { year: number; x: number; major: boolean; label: boolean; hot: boolean; fc: string | null }[] = []
  // On the four-papers step each lit paper's year wears its colour.
  const fcYear = new Map<number, string>()
  papers.forEach((p, i) => {
    const c = focusColor(i)
    if (c) fcYear.set(p.year, c)
  })
  for (let y = y0; y <= y1; y++) {
    const major = paperYears.has(y)
    out.push({
      year: y,
      x: xYear(y),
      major,
      label: major || y % 5 === 0,
      hot: y === hotYear,
      fc: fcYear.get(y) ?? null,
    })
  }
  return out
})
</script>

<style scoped>
.lit-timeline {
  position: absolute;
  inset: 0;
  pointer-events: none;
  font-family: 'Inter', system-ui, sans-serif;
  --paper: #ece7db;
  --ink: #1c1a16;
}

.lt-backdrop {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 70% 60% at 50% 45%, rgba(12, 14, 20, 0.94), rgba(3, 4, 6, 0.985) 100%);
  animation: lt-fade 0.6s ease-out both;
}

.lt-svg {
  position: absolute;
  inset: 0;
  overflow: visible;
}

/* ---- arcs ---------------------------------------------------------- */
.lt-arc-base {
  fill: none;
  stroke: rgba(255, 255, 255, 0.07);
  stroke-width: 1;
  transition: stroke 0.35s;
  animation: lt-fade 0.8s 0.9s ease-out both;
}
.lt-arc-hot {
  fill: none;
  stroke: var(--gold);
  stroke-width: 2.4;
  stroke-linecap: round;
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  opacity: 0;
  transition: stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s;
}
.lt-arc-hot.on {
  stroke-dashoffset: 0;
  opacity: 1;
}
/* Arcs from the papers that cite the highlighted one: a quieter
   warmth, no draw-in. */
.lt-arc-hot.out:not(.on) {
  stroke-dashoffset: 0;
  opacity: 0.32;
  transition: opacity 0.5s;
}
/* The halo twin under every gold stroke: wide, faint, same dash state. */
.lt-halo {
  stroke-width: 8;
}
.lt-halo.on,
.lt-halo.out:not(.on) {
  opacity: 0.16;
}
/* The chevron on the cited paper: lands as the draw-in arrives. */
.lt-arc-tip {
  fill: none;
  stroke: var(--gold);
  stroke-width: 2.4;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0;
  transition: opacity 0.15s;
}
.lt-arc-tip.on {
  opacity: 1;
  transition: opacity 0.25s 0.6s;
}

/* ---- branches -------------------------------------------------------- */
.lt-branch-base {
  fill: none;
  stroke: rgba(255, 255, 255, 0.17);
  stroke-width: 1;
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  transition: stroke 0.35s;
  animation: lt-draw 0.9s cubic-bezier(0.4, 0, 0.2, 1) both;
  animation-delay: calc(0.35s + var(--i) * 0.06s);
}
.lt-branch-hot {
  fill: none;
  stroke: var(--gold);
  stroke-width: 2.6;
  stroke-linecap: round;
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  opacity: 0;
  transition: stroke-dashoffset 0.7s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s;
}
.lt-branch-hot.on {
  stroke-dashoffset: 0;
  opacity: 1;
}
/* The four-papers step: each lit branch in its paper's colour. */
.lt-branch-hot.fc {
  stroke: var(--fc);
  stroke-width: 2.4;
}
.lt-branch-hot.fc.lt-halo {
  stroke-width: 9;
}

/* ---- axis ------------------------------------------------------------ */
.lt-axis-line {
  stroke: rgba(255, 255, 255, 0.55);
  stroke-width: 1.8;
  transform-origin: 0 50%;
  transform-box: fill-box;
  animation: lt-grow 0.9s 0.1s cubic-bezier(0.4, 0, 0.2, 1) both;
}
.lt-tick {
  stroke: rgba(255, 255, 255, 0.42);
  stroke-width: 1.5;
  animation: lt-fade 0.5s 0.7s ease-out both;
}
.lt-tick.major {
  stroke: rgba(255, 255, 255, 0.85);
  stroke-width: 2;
}
.lt-year {
  fill: rgba(255, 255, 255, 0.6);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 13px;
  letter-spacing: 0.04em;
  transition: fill 0.35s, font-size 0.35s;
  animation: lt-fade 0.5s 0.8s ease-out both;
}
.lt-year.major {
  fill: rgba(255, 255, 255, 0.95);
  font-size: 16.5px;
  font-weight: 600;
}
.lt-year.hot {
  fill: var(--gold-bright);
}
/* The four-papers step: the lit years in their papers' colours. */
.lt-year.fc {
  font-size: 19px;
  font-weight: 600;
}

/* ---- cards ------------------------------------------------------------ */
.lt-paper {
  position: absolute;
  display: block;
  pointer-events: auto;
  text-decoration: none;
  color: inherit;
  transform-origin: 50% 100%;
  transition: opacity 0.35s, transform 0.35s, filter 0.35s;
  animation: lt-rise 0.6s cubic-bezier(0.2, 0.7, 0.2, 1) both;
  animation-delay: calc(var(--i) * 0.06s);
  will-change: opacity, transform;
}
/* Faded = darkened, not translucent: the page stays opaque so the
   globe never shows through the type. */
.lt-paper.rest {
  filter: brightness(0.66) saturate(0.7);
}
.lt-paper.dim {
  filter: brightness(0.4) saturate(0.4);
}
.lt-paper.hot {
  filter: none;
  transform: translateY(calc(-1 * var(--lift))) scale(var(--hot-scale));
  z-index: 2;
}

/* The four-papers step: the four lit together — lifted a little less
   than a hovered card (they are neighbours), each in its colour. */
.lt-paper.focus {
  filter: none;
  transform: translateY(calc(-1 * var(--lift))) scale(var(--focus-scale));
  z-index: 2;
}
.lt-paper.focus .lt-label {
  transform: scale(var(--label-focus));
  color: var(--fc);
  border: 1.5px solid var(--fc);
  background: rgba(7, 8, 11, 0.97);
  box-shadow:
    0 8px 24px rgba(0, 0, 0, 0.6),
    0 0 16px color-mix(in srgb, var(--fc) 35%, transparent);
}
.lt-paper.focus .lt-label-year {
  opacity: 1;
}
.lt-paper.focus .lt-page {
  box-shadow:
    0 0 0 2.5px var(--fc),
    0 20px 44px rgba(0, 0, 0, 0.65),
    0 0 30px color-mix(in srgb, var(--fc) 40%, transparent);
}

/* The pill above the page. */
.lt-label-slot {
  position: absolute;
  left: 50%;
  top: 0;
  height: var(--pill);
  /* --dx: the four-papers row's sideways slide (0 otherwise); it eases
     with the pill's scale, the same curve and length, so the pills grow
     and spread as one move. */
  transform: translateX(calc(-50% + var(--dx, 0px)));
  transition: transform 0.35s cubic-bezier(0.2, 0.7, 0.2, 1);
  display: flex;
  align-items: flex-end;
  justify-content: center;
}
.lt-label {
  position: relative;
  box-sizing: border-box;
  height: var(--pill);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0 calc(var(--lf) * 0.8);
  border-radius: calc(var(--lf) * 0.7);
  background: rgba(7, 8, 11, 0.88);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: rgba(255, 255, 255, 0.9);
  font-size: var(--lf);
  line-height: 1.2;
  letter-spacing: 0.01em;
  white-space: nowrap;
  text-align: center;
  transform-origin: 50% 100%;
  transition: transform 0.35s cubic-bezier(0.2, 0.7, 0.2, 1), color 0.35s, border-color 0.35s, background 0.35s, box-shadow 0.35s;
}
.lt-label-name {
  font-weight: 600;
}
.lt-label-year {
  font-size: 0.86em;
  letter-spacing: 0.1em;
  opacity: 0.9;
}
.lt-paper.hot .lt-label {
  transform: scale(var(--label-hot));
  color: var(--gold-bright);
  border-color: var(--gold-dim);
  background: rgba(7, 8, 11, 0.96);
  box-shadow:
    0 8px 24px rgba(0, 0, 0, 0.6),
    0 0 18px rgba(232, 185, 74, 0.18);
}
.lt-paper.hot .lt-label-year {
  color: var(--gold);
  opacity: 1;
}

.lt-page {
  position: absolute;
  left: 0;
  right: 0;
  top: var(--band);
  bottom: 0;
}
.lt-paper.hot .lt-page {
  box-shadow:
    0 0 0 1.5px var(--gold),
    0 20px 44px rgba(0, 0, 0, 0.65),
    0 0 26px rgba(232, 185, 74, 0.22);
}

/* ---- caption ---------------------------------------------------------- */
.lt-caption {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  width: max-content;
  /* The longest summary (Christoffersen) on ONE line at
     1440 × 900; where it must wrap, balanced — no one-word last line. */
  max-width: min(100ch, 92vw);
  text-wrap: balance;
  padding: 0.6em 1.15em;
  border-radius: 10px;
  background: rgba(6, 7, 10, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.22);
  color: rgba(255, 255, 255, 0.96);
  font-size: 1.5rem;
  line-height: 1.35;
  text-align: center;
  white-space: normal;
  pointer-events: none;
}
.lt-cap-who {
  color: var(--gold-bright);
  font-weight: 600;
}
.lt-cap-dot {
  color: var(--gold-bright);
  margin: 0 0.5em;
}
.lt-cap-text { font-weight: 500; }
.lt-cap-enter-active,
.lt-cap-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}
.lt-cap-enter-from {
  opacity: 0;
  transform: translate(-50%, 8px);
}
.lt-cap-leave-to {
  opacity: 0;
  transform: translate(-50%, -5px);
}

/* ---- entry ------------------------------------------------------------ */
@keyframes lt-fade {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes lt-rise {
  from { opacity: 0; transform: translateY(16px); }
}
@keyframes lt-draw {
  from { stroke-dashoffset: 1; }
  to { stroke-dashoffset: 0; }
}
@keyframes lt-grow {
  from { transform: scaleX(0); }
  to { transform: scaleX(1); }
}
</style>
