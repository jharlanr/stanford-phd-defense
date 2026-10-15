<template>
  <!-- Chapter 3's implications (the director wanted a real
       implications page here: the earlier one only
       repeated the four-class model's results, and the implication to
       carry is that lakes can be classified by mechanism and not just
       rate, and that this is
       what the field should strive for). RATE → MECHANISM: the same 1000
       CW2019 lakes classified two ways — on the left Dunmire et al.
       (2025)'s rate-based classes in their own words, on the right the
       five drainage mechanisms in the class colours — ribbons = lakes,
       coloured by mechanism. Every rate class splits across several
       mechanisms (rapidly drains → hydrofracture, crevasse, moulin …),
       so rate alone cannot tell them apart; the counts are baked by
       cinematic/scene_ch03/build_implications.py. The sibling of
       Chapter 2's implications page: one figure, labels only, and
       beneath it the Conclusion page's Chapter 3 takeaway, verbatim.
       The ribbons roll out left → right (rate, then what it hides) 3 s
       after arrival — or on a NEXT pressed before then (the parent's
       next() calls startRoll(); that press does not leave the beat) —
       slowly (the director's timing: a little slower, and a 3 s wait
       before rolling out, or a NEXT click if it comes before
       the roll-out); a ribbon under the pointer lifts and shows its
       count. -->
  <div class="ci-root">
    <svg class="ci-svg" :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="xMidYMid meet">
      <defs>
        <clipPath id="ci-sweep"><rect x="0" y="0" :width="sweep * W" :height="H" /></clipPath>
      </defs>

      <!-- column titles -->
      <text :x="LX + BW / 2" y="34" text-anchor="middle" class="ci-head">By rate</text>
      <text :x="RX + BW / 2" y="34" text-anchor="middle" class="ci-head">By mechanism</text>

      <!-- ribbons -->
      <g clip-path="url(#ci-sweep)">
        <path
          v-for="f in flows"
          :key="f.key"
          :d="f.d"
          :fill="f.color"
          class="ci-flow"
          :class="{ 'ci-flow-on': flowOn(f), 'ci-flow-off': anyHover && !flowOn(f) }"
          @pointerenter="hover = f.key"
          @pointerleave="hover = null"
        ><title>{{ f.title }}</title></path>
      </g>

      <!-- left nodes: the rate classes. Hovering a node (its bar OR its
           label — the director wanted a hover on any of the big
           categories on either side to highlight the branches
           coming out of, or going to, that category) lights every ribbon
           attached to it; the hit rect spans bar + label. -->
      <g
        v-for="n in rateNodes"
        :key="n.id"
        class="ci-node"
        :class="{ 'ci-node-off': anyHover && hoverNode?.id !== n.id && !nodeTouched('rate', n.id) }"
        @pointerenter="hoverNode = { side: 'rate', id: n.id }"
        @pointerleave="hoverNode = null"
      >
        <rect :x="LX - LBL_W" :y="n.y - 6" :width="BW + LBL_W" :height="n.h + 12" class="ci-hit" />
        <rect :x="LX" :y="n.y" :width="BW" :height="n.h" rx="3" class="ci-bar-rate" :class="{ 'ci-bar-lit': hoverNode?.id === n.id }" />
        <text :x="LX - 18" :y="n.y + n.h / 2 - 4" text-anchor="end" class="ci-name">{{ n.name }}</text>
        <text :x="LX - 18" :y="n.y + n.h / 2 + 26" text-anchor="end" class="ci-count">{{ n.total }}</text>
      </g>

      <!-- right nodes: the mechanisms -->
      <g
        v-for="n in mechNodes"
        :key="n.code"
        class="ci-node"
        :class="{ 'ci-node-off': anyHover && hoverNode?.id !== n.code && !nodeTouched('mech', n.code) }"
        @pointerenter="hoverNode = { side: 'mech', id: n.code }"
        @pointerleave="hoverNode = null"
      >
        <rect :x="RX" :y="n.y - 6" :width="BW + LBL_W" :height="n.h + 12" class="ci-hit" />
        <rect :x="RX" :y="n.y" :width="BW" :height="n.h" rx="3" :fill="n.color" class="ci-bar-mech" :class="{ 'ci-bar-lit': hoverNode?.id === n.code }" />
        <text :x="RX + BW + 18" :y="n.y + n.h / 2 - 4" class="ci-name" :style="{ fill: n.color }">{{ n.name }}</text>
        <text :x="RX + BW + 18" :y="n.y + n.h / 2 + 26" class="ci-count">{{ n.code }} · {{ n.total }}</text>
      </g>

      <!-- the hovered ribbon's count, at its middle -->
      <text
        v-if="hoverFlow"
        :x="(LX + BW + RX) / 2"
        :y="hoverFlow.ym + 8"
        text-anchor="middle"
        class="ci-flowcount"
      >{{ hoverFlow.n }}</text>
    </svg>

    <p class="ci-takeaway">{{ TAKEAWAY }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { CH3_IMPL_COUNTS, CH3_IMPL_MECH, CH3_IMPL_RATE } from '../config/ch3Implications.gen'
import { classColor, className } from '../config/essdLabel'
import { CH3_TAKEAWAY } from '../config/takeaways'

const props = withDefaults(
  defineProps<{
    /** The chapter's takeaway beat is up over this page: ribbons out,
     *  no 3 s wait (SectionCh3). */
    settled?: boolean
  }>(),
  { settled: false },
)

// The Conclusion page's Chapter 3 takeaway, word for word — the director's line
// (worded once, in config/takeaways.ts).
const TAKEAWAY = CH3_TAKEAWAY

// Figure units (the SVG scales to fit; at 1280×800 one unit ≈ 0.8 px, so
// names 27 → ≥ 21 px and counts 23 → ≥ 18 px — the back-row rule).
const W = 1500
const H = 740
const BW = 26 // node bar width
const LX = 400 // left bars
const RX = W - 400 - BW // right bars
const TOP = 70 // under the column titles
const SPAN = H - TOP - 6 // both columns fill the same height
const GAP_R = 24 // between mechanism nodes

const rateTotals = CH3_IMPL_COUNTS.map((row) => row.reduce((a, b) => a + b, 0))
const mechTotals = CH3_IMPL_MECH.map((_, j) => CH3_IMPL_COUNTS.reduce((a, row) => a + row[j], 0))
const N = rateTotals.reduce((a, b) => a + b, 0)
const K = (SPAN - GAP_R * (CH3_IMPL_MECH.length - 1)) / N // units per lake
// The rate side has one node fewer: its gaps widen so both columns span alike.
const GAP_L = (SPAN - K * N) / (CH3_IMPL_RATE.length - 1)

function stack(totals: number[], gap: number) {
  let y = TOP
  return totals.map((t) => {
    const n = { y, h: t * K }
    y += t * K + gap
    return n
  })
}
const rateNodes = stack(rateTotals, GAP_L).map((p, i) => ({ ...p, ...CH3_IMPL_RATE[i], total: rateTotals[i] }))
const mechNodes = stack(mechTotals, GAP_R).map((p, j) => ({
  ...p,
  code: CH3_IMPL_MECH[j],
  name: className(CH3_IMPL_MECH[j]),
  color: classColor(CH3_IMPL_MECH[j]),
  total: mechTotals[j],
}))

// Ribbons: within a rate node they stack in mechanism order, within a
// mechanism node in rate order — so no two ribbons cross inside a node.
const flows = (() => {
  const outY = rateNodes.map((n) => n.y)
  const inY = mechNodes.map((n) => n.y)
  const x0 = LX + BW
  const x1 = RX
  const xm = (x0 + x1) / 2
  const out: { key: string; rate: string; mech: string; d: string; color: string; title: string; n: number; ym: number }[] = []
  CH3_IMPL_RATE.forEach((r, i) => {
    CH3_IMPL_MECH.forEach((m, j) => {
      const n = CH3_IMPL_COUNTS[i][j]
      if (!n) return
      const h = n * K
      const a = outY[i]
      const b = inY[j]
      outY[i] += h
      inY[j] += h
      const d =
        `M${x0},${a} C${xm},${a} ${xm},${b} ${x1},${b} ` +
        `L${x1},${b + h} C${xm},${b + h} ${xm},${a + h} ${x0},${a + h} Z`
      out.push({
        key: `${r.id}-${m}`,
        rate: r.id,
        mech: m,
        d,
        color: classColor(m),
        title: `${r.name} → ${className(m)}: ${n} lakes`,
        n,
        ym: (a + b + h) / 2,
      })
    })
  })
  return out
})()

const hover = ref<string | null>(null)
const hoverFlow = computed(() => flows.find((f) => f.key === hover.value) ?? null)
/** A hovered CATEGORY (either side): all its ribbons light. */
const hoverNode = ref<{ side: 'rate' | 'mech'; id: string } | null>(null)
/** The roll-out has begun (or, under reduced motion, is already done). */
const rolling = ref(false)
// Before the roll-out there is nothing to relate: a hovered category
// brightens its bar but dims nothing (the ribbons light as they roll).
const anyHover = computed(() => rolling.value && (hover.value !== null || hoverNode.value !== null))
function flowOn(f: { key: string; rate: string; mech: string }): boolean {
  if (hover.value === f.key) return true
  const n = hoverNode.value
  return !!n && (n.side === 'rate' ? f.rate === n.id : f.mech === n.id)
}
/** Does any lit ribbon touch this node? (the other side's nodes stay lit
 *  where a ribbon arrives; the rest step back) */
function nodeTouched(side: 'rate' | 'mech', id: string): boolean {
  return flows.some((f) => flowOn(f) && (side === 'rate' ? f.rate === id : f.mech === id))
}
/** The label column's width (hit area) beside each bar. */
const LBL_W = 300

// The roll-out: the bars and categories are there on arrival, the
// ribbons are not. ARM_MS after mount — or on the first NEXT, whichever
// comes first — they roll out left → right once, over ROLL_MS (was a
// 1400 ms sweep on mount; the director asked for slower, after a 3 s wait).
const ARM_MS = 3000
const ROLL_MS = 2600
const sweep = ref(0)
let raf: number | null = null
let arm: number | null = null
/** Start the roll-out now. Returns true when THIS call started it —
 *  the parent's NEXT swallows that press; a later one leaves the beat. */
function startRoll(): boolean {
  if (rolling.value) return false
  rolling.value = true
  if (arm !== null) { window.clearTimeout(arm); arm = null }
  const t0 = performance.now()
  const tick = (now: number) => {
    const t = Math.max(0, Math.min(1, (now - t0) / ROLL_MS))
    sweep.value = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
    raf = t < 1 ? requestAnimationFrame(tick) : null
  }
  raf = requestAnimationFrame(tick)
  return true
}
defineExpose({ startRoll })
/** Land rolled out at once — the takeaway beat over this page (its deep
 *  link, or BACK onto it from the Conclusion) never waits on the roll. */
function settleNow(): void {
  if (raf !== null) { cancelAnimationFrame(raf); raf = null }
  if (arm !== null) { window.clearTimeout(arm); arm = null }
  sweep.value = 1
  rolling.value = true
}
watch(
  () => props.settled,
  (v) => { if (v && sweep.value < 1 && raf === null) settleNow() },
)
onMounted(() => {
  if (props.settled || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
    sweep.value = 1
    rolling.value = true
    return
  }
  arm = window.setTimeout(() => startRoll(), ARM_MS)
})
onBeforeUnmount(() => {
  if (raf !== null) cancelAnimationFrame(raf)
  if (arm !== null) window.clearTimeout(arm)
})
</script>

<style scoped>
.ci-root {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2vh;
  padding: calc(var(--chrome-bottom, 7vh) + 2vh) 3vw 7vh;
  box-sizing: border-box;
}
.ci-svg {
  width: 100%;
  flex: 1 1 auto;
  min-height: 0;
  display: block;
  overflow: visible;
}
.ci-head {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 23px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  fill: var(--gold, #f4cf6a);
}
.ci-flow {
  opacity: 0.6;
  transition: opacity 0.2s;
}
.ci-flow-on {
  opacity: 0.95;
}
.ci-flow-off {
  opacity: 0.28;
}
.ci-bar-rate {
  fill: #e6dcc6;
}
.ci-hit {
  fill: transparent;
  cursor: pointer;
}
.ci-node {
  transition: opacity 0.2s;
}
.ci-node-off {
  opacity: 0.4;
}
.ci-bar-rate,
.ci-bar-mech {
  transition: filter 0.2s;
}
.ci-bar-lit {
  filter: brightness(1.25) drop-shadow(0 0 10px rgba(255, 255, 255, 0.45));
}
.ci-name {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 27px;
  font-weight: 600;
  fill: #f5f0e6;
}
.ci-count {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 23px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  fill: rgba(245, 240, 230, 0.92);
}
.ci-flowcount {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 26px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  fill: #fff;
  paint-order: stroke;
  stroke: rgba(0, 0, 0, 0.85);
  stroke-width: 6px;
  stroke-linejoin: round;
  pointer-events: none;
}
/* Chapter 2's implications sentence, set alike */
.ci-takeaway {
  margin: 0;
  max-width: 94vw;
  text-align: center;
  font-family: 'EB Garamond', serif;
  font-size: clamp(1.3rem, 2.05vw, 2.1rem);
  line-height: 1.3;
  color: #f5f5f5;
  letter-spacing: 0.01em;
}
</style>
