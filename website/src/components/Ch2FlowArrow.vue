<template>
  <!-- Chapter 2's ICE FLOW arrow (the director placed it near the mini
       map, just above the top-left edge of the simulation
       domain). Was a 3D arrow + sprite upstream of the block
       (Globe.vue buildSimFlow — the MGSIM page keeps that one); now the
       implications page's gold arrow with "ICE FLOW" under it, drawn in
       HTML/SVG and anchored per frame to the block's projected upper-left
       edge (window.__simDomainScreen.corners): one band — the arrow, then
       "ICE FLOW" beside it (the arrow on the side the ice flows to) —
       lies parallel to that edge, lifted just clear of it, slid along it
       as far toward the centre-lakes inset as it can go without meeting
       the inset, the tier pills or the stress key (blockAnchor.ts) — one
       top-left cluster. The arrowhead points along the projected flow
       (flowDirDeg). Its box is published as window.__simFlowArrowRect and
       its top as __simDomainScreen.flowTopY (Globe.vue), so the tier
       pills (SimViewControls) still clear it. Figure label only.
       The director also asked for a scale bar parallel to the ICE FLOW
       arrow but on its other side (to the right), a 5 km bar floating
       like the arrow rather than fixed to the block:
       the same band carries a 5 km bar with end ticks
       and its "5 KM" label to the RIGHT of the arrow + label group, its
       length = 5 km at the upper-left edge's projected scale
       (__simDomainScreen.edgeKm, the model square's side). -->
  <svg class="cfa" :class="{ 'cfa-off': !on }" :width="vw" :height="vh" aria-hidden="true">
    <g :transform="`translate(${cx} ${cy}) rotate(${phi})`">
      <g :transform="`translate(${ax} 0) rotate(${alpha})`">
        <line :x1="-A / 2" :x2="A / 2 - 20" y1="0" y2="0" class="cfa-ink" />
        <path :d="HEAD" class="cfa-ink" />
        <line :x1="-A / 2" :x2="A / 2 - 20" y1="0" y2="0" class="cfa-gold" />
        <path :d="HEAD" class="cfa-gold" />
      </g>
      <text ref="lblEl" :x="lx" y="0" text-anchor="middle" dominant-baseline="central" class="cfa-lbl">ICE FLOW</text>
      <!-- the 5 km scale bar: ticks at both ends, the label beside it -->
      <g v-if="barPx > 0">
        <line :x1="bx - barPx / 2" :x2="bx + barPx / 2" y1="0" y2="0" class="cfa-ink" />
        <line :x1="bx - barPx / 2" :x2="bx - barPx / 2" :y1="-TICK" :y2="TICK" class="cfa-ink" />
        <line :x1="bx + barPx / 2" :x2="bx + barPx / 2" :y1="-TICK" :y2="TICK" class="cfa-ink" />
        <line :x1="bx - barPx / 2" :x2="bx + barPx / 2" y1="0" y2="0" class="cfa-gold cfa-bar" />
        <line :x1="bx - barPx / 2" :x2="bx - barPx / 2" :y1="-TICK" :y2="TICK" class="cfa-gold cfa-bar" />
        <line :x1="bx + barPx / 2" :x2="bx + barPx / 2" :y1="-TICK" :y2="TICK" class="cfa-gold cfa-bar" />
        <text ref="barLblEl" :x="blx" y="0" text-anchor="middle" dominant-baseline="central" class="cfa-lbl">{{ SCALE_KM }} KM</text>
      </g>
    </g>
  </svg>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { blockTopY, insetRect, simScreen, tierSlot, upperLeftEdge, type Rect } from './blockAnchor'

const props = defineProps<{ visible: boolean }>()

// Band geometry in its own frame (x along the edge, rightward; +y toward
// the block): the arrow (length A, head 26 × 28) and the label side by
// side on y = 0, GAP apart; the band is ±HALF_H tall.
const A = 62
const GAP = 12
/** The head's half-width (13) + the ink's half-stroke (5). blockAnchor.ts
 *  BAND_ROOM keeps room for 2 × HALF_H + EDGE_CLEAR under the key. */
const HALF_H = 18
const HEAD = `M ${A / 2} 0 L ${A / 2 - 26} -13 L ${A / 2 - 26} 13 Z`
/** Clearance band ↔ block edge, band ↔ inset / key [px]. */
const EDGE_CLEAR = 14
const KEEP = 8
/** The scale bar: SCALE_KM at the edge's projected scale,
 *  end ticks ±TICK, GAP_BAR between the arrow + label group and it. */
const SCALE_KM = 5
const TICK = 9
const GAP_BAR = 34

const vw = ref(window.innerWidth)
const vh = ref(window.innerHeight)
const cx = ref(0)
const cy = ref(0)
/** The edge's angle (the band's), and the arrow's within the band [deg]. */
const phi = ref(0)
const alpha = ref(180)
/** The arrow's and the label's centres along the band. */
const ax = ref(0)
const lx = ref(0)
/** The scale bar's centre, its px length, and its label's centre. */
const bx = ref(0)
const barPx = ref(0)
const blx = ref(0)
const placed = ref(false)
const lblEl = ref<SVGTextElement | null>(null)
const barLblEl = ref<SVGTextElement | null>(null)
let lblW = 100
let barLblW = 44

let raf = 0
let frame = 0
let chromeBottom = 100
let keepOuts: Rect[] = []
let tierKeep: Rect | null = null

const on = computed(() => props.visible && placed.value)

function publish(r: Rect | null): void {
  ;(window as unknown as { __simFlowArrowRect?: unknown }).__simFlowArrowRect = r
    ? { ...r, width: r.right - r.left, height: r.bottom - r.top }
    : null
}

function tick(): void {
  vw.value = window.innerWidth
  vh.value = window.innerHeight
  const s = simScreen()
  const edge = s?.corners ? upperLeftEdge(s.corners) : null
  // the block is the subject (the model pills' spread gate), not a speck
  if (!props.visible || !s || !s.visible || (s.spread ?? 0) <= 260 || !edge || s.flowDirDeg == null) {
    placed.value = false
    publish(null)
    raf = requestAnimationFrame(tick)
    return
  }
  // chrome + keep-outs, re-measured a few times a second: the inset, and
  // the stress / imagery keys' label and bar separately (their slots are
  // reserved even while hidden, so the arrow never moves on a layer pick)
  if (frame++ % 15 === 0) {
    let b = 0
    for (const sel of ['.landmarks', '.beat-nav']) {
      const r = document.querySelector(sel)?.getBoundingClientRect()
      if (r && r.height > 0) b = Math.max(b, r.bottom)
    }
    chromeBottom = b || 100
    keepOuts = [insetRect()]
    // the tier pills at their highest (they rise to clear this arrow —
    // planning round their top slot keeps the two from chasing each other)
    tierKeep = tierSlot()
    if (tierKeep) keepOuts.push(tierKeep)
    for (const sel of ['.ch2-key > img', '.ch2-key > div']) {
      document.querySelectorAll(sel).forEach((el) => {
        const r = el.getBoundingClientRect()
        if (r.width > 0) keepOuts.push({ left: r.left, top: r.top, right: r.right, bottom: r.bottom })
      })
    }
    try {
      const w = lblEl.value?.getComputedTextLength()
      if (w && w > 0) lblW = w
      const bw = barLblEl.value?.getComputedTextLength()
      if (bw && bw > 0) barLblW = bw
    } catch {
      // not rendered yet
    }
  }
  const { T, L } = edge
  const ex = L.x - T.x
  const ey = L.y - T.y
  const len = Math.hypot(ex, ey) || 1
  let ux = ex / len
  let uy = ey / len
  // the band reads left → right: its x axis points rightward
  if (ux < 0) {
    ux = -ux
    uy = -uy
  }
  // outward normal (away from the block = up); the band's +y is its opposite
  const nx = uy
  const ny = -ux
  const ph = (Math.atan2(uy, ux) * 180) / Math.PI
  // the arrow on the side the ice flows toward, the label beyond it
  const al = s.flowDirDeg - ph
  const toward = Math.cos((al * Math.PI) / 180) < 0 ? -1 : 1
  // the 5 km bar at this edge's projected scale (0 = no edge length yet)
  const bar = s.edgeKm && s.edgeKm > 0 ? (SCALE_KM * len) / s.edgeKm : 0
  // the band: [arrow + ICE FLOW] GAP_BAR [bar + "5 KM"], centred on 0
  const wFlow = A + GAP + lblW
  const wBar = bar > 0 ? bar + GAP + barLblW : 0
  const hw = (wFlow + (bar > 0 ? GAP_BAR + wBar : 0)) / 2
  const cFlow = -hw + wFlow / 2
  ax.value = cFlow + toward * (wFlow / 2 - A / 2)
  lx.value = cFlow - toward * (wFlow / 2 - lblW / 2)
  barPx.value = bar
  bx.value = -hw + wFlow + GAP_BAR + bar / 2
  blx.value = -hw + wFlow + GAP_BAR + bar + GAP + barLblW / 2
  // (+ the arrow tip's ink, 5 px past the band's end)
  const hwK = hw + 5
  const lift = HALF_H + EDGE_CLEAR
  // the band's corners on screen with its edge point at (px, py)
  const bandAt = (px: number, py: number): [number, number][] => {
    const c0x = px + nx * lift
    const c0y = py + ny * lift
    return [
      [-hwK, -HALF_H],
      [hwK, -HALF_H],
      [hwK, HALF_H],
      [-hwK, HALF_H],
    ].map(([x, y]) => [c0x + x * ux - y * nx, c0y + x * uy - y * ny])
  }
  const aabb = (pts: [number, number][]): Rect => ({
    left: Math.min(...pts.map((p) => p[0])),
    right: Math.max(...pts.map((p) => p[0])),
    top: Math.min(...pts.map((p) => p[1])),
    bottom: Math.max(...pts.map((p) => p[1])),
  })
  // the band (a rotated rectangle) vs a keep-out box grown by KEEP:
  // separating axes = the box's two and the band's two
  const hits = (pts: [number, number][], o: Rect): boolean => {
    const b = { left: o.left - KEEP, right: o.right + KEEP, top: o.top - KEEP, bottom: o.bottom + KEEP }
    const bb = aabb(pts)
    if (bb.right < b.left || bb.left > b.right || bb.bottom < b.top || bb.top > b.bottom) return false
    const boxPts: [number, number][] = [
      [b.left, b.top],
      [b.right, b.top],
      [b.right, b.bottom],
      [b.left, b.bottom],
    ]
    for (const [axx, axy] of [
      [ux, uy],
      [nx, ny],
    ]) {
      const pa = pts.map(([x, y]) => x * axx + y * axy)
      const pb = boxPts.map(([x, y]) => x * axx + y * axy)
      if (Math.max(...pa) < Math.min(...pb) || Math.min(...pa) > Math.max(...pb)) return false
    }
    return true
  }
  // never over the block: the band's block-side edge stays EDGE_CLEAR
  // above its silhouette (past the top corner that is the upper-RIGHT edge)
  const overBlock = (pts: [number, number][]): boolean => {
    const [a, b] = [pts[3], pts[2]]
    for (let k = 0; k <= 6; k++) {
      const x = a[0] + ((b[0] - a[0]) * k) / 6
      const y = a[1] + ((b[1] - a[1]) * k) / 6
      if (y > blockTopY(s.corners!, x) - EDGE_CLEAR + 1) return true
    }
    return false
  }
  // slide along the edge (from the left corner to a little past the top
  // one) and take the clear spot nearest the inset's bottom-right corner
  // — "near the mini map"
  // three passes, each giving up a keep-out the arrow can live without:
  // all of them; then not the tiers' top slot (they still rise to clear
  // the arrow — __simFlowArrowRect); then only the inset
  const ins = keepOuts[0]
  const fMin = Math.min(0.5, hwK / len)
  let best: { px: number; py: number; box: Rect } | null = null
  for (const ko of [keepOuts, keepOuts.filter((o) => o !== tierKeep), [ins]]) {
    let bestD = Infinity
    for (let f = 1 - fMin; f >= -0.35; f -= 0.01) {
      const px = T.x + ex * f
      const py = T.y + ey * f
      const pts = bandAt(px, py)
      const box = aabb(pts)
      if (box.left < 10 || box.top < chromeBottom + 6) continue
      if (f < fMin && overBlock(pts)) continue
      if (ko.some((o) => o && hits(pts, o))) continue
      const d = ins ? Math.hypot((box.left + box.right) / 2 - ins.right, (box.top + box.bottom) / 2 - ins.bottom) : -f
      if (d < bestD) {
        bestD = d
        best = { px, py, box }
      }
    }
    if (best) break
  }
  ;(window as unknown as { __simFlowArrowFallback?: boolean }).__simFlowArrowFallback = !best
  if (!best) {
    const px = T.x + ex * fMin
    const py = T.y + ey * fMin
    best = { px, py, box: aabb(bandAt(px, py)) }
  }
  const tx = best.px + nx * lift
  const ty = best.py + ny * lift
  // ease toward the target (the camera settles over a few frames); snap
  // on the first frame or a long jump (a new block)
  const far = Math.hypot(tx - cx.value, ty - cy.value) > 160
  if (!placed.value || far) {
    cx.value = tx
    cy.value = ty
  } else {
    cx.value += (tx - cx.value) * 0.3
    cy.value += (ty - cy.value) * 0.3
  }
  phi.value = ph
  alpha.value = al
  placed.value = true
  publish(best.box)
  raf = requestAnimationFrame(tick)
}

onMounted(() => {
  raf = requestAnimationFrame(tick)
})
onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  publish(null)
})
</script>

<style scoped>
.cfa {
  position: absolute;
  left: 0;
  top: 0;
  z-index: 8;
  pointer-events: none;
  overflow: visible;
  transition: opacity 0.6s;
}
.cfa-off {
  opacity: 0;
}
/* gold over a black band — the implications page's arrow */
.cfa-ink {
  stroke: #050505;
  stroke-width: 10;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: #050505;
}
.cfa-gold {
  stroke: var(--gold, #f4cf6a);
  stroke-width: 5;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: var(--gold, #f4cf6a);
}
.cfa-bar {
  stroke-width: 4;
}
.cfa-lbl {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.14em;
  fill: var(--gold, #f4cf6a);
  paint-order: stroke;
  stroke: #050505;
  stroke-width: 5px;
  stroke-linejoin: round;
}
</style>
