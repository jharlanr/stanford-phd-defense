<template>
  <!-- Chapter 2's implications, for THE CHOSEN LAKE (one lake, not the
       seven-lake stack it replaced: that stack left the room asking which
       centre lake it was looking at and why several lakes shared one
       symbol). [The stress colours are the ones the talk has already used
       (the red-blue seismic map), because a different scheme here read as
       confusing, and each simulation domain carries the ice flow arrow in
       its top-left corner: the
       fields are the block's seismic ±1 MPa (impl_lakes_v2.json →
       impl2_*.png), the classes wear the flat difference maps' darker
       inks, the colourbar is the block's bare bar, and each panel carries
       ICE FLOW top-left.] [Ice flow runs left to right (it first ran right
       to left; the director reversed it): impl_lakes_v3.json →
       impl3_*.png, ice flows LEFT → RIGHT, upstream is LEFT, left-of-flow
       up (the block's own frame); every position goes through the
       sidecar's `display` mapping, and ICE FLOW points right from the
       top-left corner.]
       [THE VISCOUS MODEL ONLY — the director dropped the elastic frame
       from the talk: the implications page shows the surface stress of
       lake 2394 on the left and the full summary stress space on the
       right: LEFT, the drained lake's
       viscous Δσ_t1 surface field — the dashed line its 100 kPa contour,
       the dotted ring the R = 2.5 km patch, the bracket its reach
       upstream, the outlines the drainage catalog in its class colours
       with numbers (the drained lake gold), the colourbar beneath; RIGHT,
       the population page's stress space (every center lake's
       neighbours, viscous, the talk's ±1000 kPa frame) with its
       center-lake key. The elastic panel that stood beside the viscous
       one lives in the deeper dive (#sequence).] One Garamond line
       beneath: the Conclusion page's Chapter 2 takeaway, verbatim. -->
  <div class="im-root">
    <div class="im-row">
      <!-- LEFT: the drained lake's viscous perturbation on the surface -->
      <div class="im-col">
        <div class="im-title">Lake {{ lake.num }}</div>
        <svg class="im-svg" :viewBox="`${-PADL} ${-PADT} ${S + PADL + PADR} ${S + PADT + PADB}`" preserveAspectRatio="xMidYMid meet">
          <defs>
            <clipPath :id="clipId"><rect x="0" y="0" :width="S" :height="S" /></clipPath>
          </defs>
          <image :href="ch2ResultUrl(lake.models.viscous.image)" x="0" y="0" :width="S" :height="S" />
          <rect x="0" y="0" :width="S" :height="S" class="im-frame-ink" />
          <rect x="0" y="0" :width="S" :height="S" class="im-frame" />
          <g :clip-path="`url(#${clipId})`">
            <!-- the patch, R = 2.5 km -->
            <circle :cx="kx(0)" :cy="ky(0)" :r="R_KM * k" class="im-patch" />
            <!-- +100 kPa -->
            <polyline
              v-for="(ln, i) in lake.models.viscous.contour100_km"
              :key="`c${i}`"
              :points="kpts(ln)"
              class="im-contour"
            />
            <!-- the drainage catalog: a dark halo under each class-coloured outline -->
            <g v-for="lk in rings" :key="lk.num">
              <polygon v-for="(r, j) in lk.rings_km" :key="`h${j}`" :points="kpts(r)" class="im-ring-halo" :class="{ 'im-ring-halo-center': lk.center }" />
              <polygon
                v-for="(r, j) in lk.rings_km"
                :key="j"
                :points="kpts(r)"
                class="im-ring"
                :class="{ 'im-ring-dash': lk.cls.startsWith('dash'), 'im-ring-hl': lk.num === highlightNum }"
                :style="{ stroke: lk.center ? GOLD : ringColor(lk.cls) }"
                :stroke-width="lk.center ? 4.2 : lk.phase ? 3 : 2.2"
                @pointerenter="lk.phase ? emit('lake-hover', lk.num) : undefined"
                @pointerleave="lk.phase ? emit('lake-hover', null) : undefined"
              />
            </g>
          </g>
          <g class="im-labels">
            <text
              v-for="l in labels"
              :key="`t${l.num}`"
              :x="l.lx"
              :y="l.ly"
              :text-anchor="l.anchor"
              class="im-num"
              :class="{ 'im-num-center': l.center, 'im-num-hl': l.num === highlightNum }"
              :style="{ fill: l.center ? undefined : ringColor(l.cls) }"
            >{{ l.num }}</text>
          </g>
          <text :x="kx(0)" :y="ky(0) + R_KM * k + 30" text-anchor="middle" class="im-patchlbl">patch</text>
          <!-- ice flow, top-left of the domain, pointing downstream (right
               since v3; the head follows the display's sx) -->
          <g class="im-flowmark">
            <line :x1="flowArrow.tail" :x2="flowArrow.neck" :y1="FLOW.y" :y2="FLOW.y" class="im-flow-ink" />
            <path :d="flowArrow.head" class="im-flow-ink" />
            <line :x1="flowArrow.tail" :x2="flowArrow.neck" :y1="FLOW.y" :y2="FLOW.y" class="im-flow-gold" />
            <path :d="flowArrow.head" class="im-flow-gold" />
            <text :x="(FLOW.x0 + FLOW.x1) / 2" :y="FLOW.y + 40" text-anchor="middle" class="im-flowlbl">ICE FLOW</text>
          </g>
          <!-- upstream (LEFT since v3) reach of the +100 kPa region: a bracket above -->
          <template v-if="reach > 0">
            <g class="im-reach">
              <line :x1="kx(0)" :x2="kx(-reach)" :y1="-30" :y2="-30" />
              <line :x1="kx(0)" :x2="kx(0)" :y1="-42" :y2="-18" />
              <line :x1="kx(-reach)" :x2="kx(-reach)" :y1="-42" :y2="-18" />
              <line :x1="kx(0)" :x2="kx(0)" :y1="-18" :y2="0" class="im-reach-tie" />
              <line :x1="kx(-reach)" :x2="kx(-reach)" :y1="-18" :y2="0" class="im-reach-tie" />
            </g>
            <image v-bind="eqAt(reachEq, 2.6, (kx(-reach) + kx(0)) / 2, -48, 'center', 'bottom')" />
          </template>
          <!-- the peak · area line under the panel is gone (the director
               dropped the max-stress and A_Δσ readouts: just the
               colorbar) -->
        </svg>
        <!-- the key: the block's colourbar, Δσ_t1 [MPa], −1 · 0 · +1 -->
        <div class="im-key">
          <div class="im-key-item im-cbitem">
            <img :src="ch2EqUrl('cb_diff_t1')" class="im-eq" :style="eqStyle('cb_diff_t1', 1.9)" alt="Δσt1 [MPa]" />
            <div class="im-cbscale">
              <div class="im-cb" />
              <div class="im-cbticks">
                <span v-for="t in CB_TICKS" :key="t.p" :style="{ left: t.p + '%' }"><i />{{ t.l }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- RIGHT: every center lake's neighbours in the viscous stress space -->
      <div class="im-col im-col-ss">
        <div class="im-title">All lakes</div>
        <div class="im-ss">
          <Ch2StressSpace
            model="viscous"
            comp="t1"
            :points="points"
            :center-num="centerNum"
            show-all
            :labels="false"
            :header-model="false"
            :fs="1.5"
            :highlight-num="highlightNum ?? null"
            hug-top
            @lake-hover="emit('lake-hover', $event)"
          />
        </div>
        <!-- the center-lake key (the population page's) -->
        <div class="im-centers">
          <span v-for="c in centers" :key="c" class="im-center">
            <svg width="24" height="24"><path :d="phaseMarkerPath(PHASE_CENTER_MARKERS[c] ?? 'o', 12, 12, 8.5)" fill="rgba(245,240,230,0.85)" stroke="rgba(0,0,0,0.6)" stroke-width="1" /></svg>
            {{ c }}
          </span>
        </div>
      </div>
    </div>

    <p class="im-takeaway">{{ TAKEAWAY }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Ch2StressSpace from './Ch2StressSpace.vue'
import { CH2_EQ, type Ch2EqName } from '../config/ch2Eqs'
import { ch2EqUrl, ch2ResultUrl, type Ch2ImplLake } from '../config/ch2Results'
import { CH2_TAKEAWAY } from '../config/takeaways'
import { PHASE_CENTER_MARKERS, phaseMarkerPath, type PhasePoint } from '../config/simLakes'

const props = defineProps<{
  /** The chosen center lake's figure (impl_lakes_v3.json). */
  lake: Ch2ImplLake
  /** Every VISCOUS stress-space point (phase_space_v2.json) — the right
   *  panel draws all of them. */
  points: PhasePoint[]
  /** The chosen center lake's number (the stress space's own). */
  centerNum: number
  highlightNum?: number | null
}>()
const emit = defineEmits<{ 'lake-hover': [num: number | null] }>()

const GOLD = '#f4cf6a'
// The Conclusion page's Chapter 2 takeaway, word for word — the director's line
// (worded once, in config/takeaways.ts).
const TAKEAWAY = CH2_TAKEAWAY
const R_KM = 2.5 // patch radius, every lake (thesis §2 limitations)
const clipId = `im-clip-${Math.random().toString(36).slice(2, 8)}`

// Panel geometry: S units square = the ±half_km analysis window.
const S = 600
const PADL = 14
const PADR = 14
const PADT = 96 // the reach bracket + its label
const PADB = 12
const half = computed(() => props.lake.half_km)
const k = computed(() => S / (2 * half.value)) // units per km
// The sidecar's display mapping (screen = half + s·model, km) — v3:
// downstream (+x) RIGHT, left-of-flow (+y) UP, the block's own frame; the
// PNG fields were baked through the same mapping.
const sx = computed(() => props.lake.display.sx)
const sy = computed(() => props.lake.display.sy)
function kx(xKm: number): number {
  return (half.value + sx.value * xKm) * k.value
}
function ky(yKm: number): number {
  return (half.value + sy.value * yKm) * k.value
}
function kpts(ln: [number, number][]): string {
  return ln.map(([x, y]) => `${kx(x).toFixed(1)},${ky(y).toFixed(1)}`).join(' ')
}
const reach = computed(() => props.lake.models.viscous.upstream100_km)
const reachEq = computed(() => `impl_reach_v_${props.lake.num}` as Ch2EqName)

/** Class inks on the white-centred seismic field — the flat difference
 *  maps': cyan, dark gray, black. */
function ringColor(cls: string): string {
  if (cls.endsWith('cyan')) return '#00b8d9'
  if (cls.endsWith('gray')) return '#5d646d'
  if (cls === 'magenta') return '#d63fcf'
  return '#14171c'
}
const CB_TICKS = [
  { p: 0, l: '−1' },
  { p: 50, l: '0' },
  { p: 100, l: '+1' },
]
// ICE FLOW: the arrow (pointing downstream — right since v3) in the
// domain's top-left corner, its label under it — panel units.
const FLOW = { x0: 26, x1: 140, y: 40 }
const flowArrow = computed(() => {
  const right = sx.value > 0
  const tip = right ? FLOW.x1 : FLOW.x0
  const back = right ? tip - 28 : tip + 28
  return {
    tail: right ? FLOW.x0 : FLOW.x1,
    neck: right ? tip - 22 : tip + 22,
    head: `M ${tip} ${FLOW.y} L ${back} ${FLOW.y - 15} L ${back} ${FLOW.y + 15} Z`,
  }
})
// The drained lake drawn last (on top).
const rings = computed(() => [...props.lake.lakes].sort((a, b) => Number(a.center) - Number(b.center)))
// Numbers for the drained lake and its assessable neighbours: above each
// outline if free, else below / right / left — greedy against every
// outline and the numbers already placed, inside the panel.
const labels = computed(() => {
  type Box = { x0: number; y0: number; x1: number; y1: number }
  const bbox = (l: Ch2ImplLake['lakes'][number]): Box => {
    const pts = l.rings_km.flat()
    const xs = pts.map((p) => kx(p[0]))
    const ys = pts.map((p) => ky(p[1]))
    return { x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys) }
  }
  const taken: Box[] = [...props.lake.lakes.map(bbox), { x0: FLOW.x0 - 6, y0: FLOW.y - 20, x1: FLOW.x1 + 12, y1: FLOW.y + 48 }]
  const over = (b: Box) =>
    b.x0 < 4 || b.x1 > S - 4 || b.y0 < 4 || b.y1 > S - 4 ||
    taken.some((o) => b.x0 < o.x1 && b.x1 > o.x0 && b.y0 < o.y1 && b.y1 > o.y0)
  const lks = props.lake.lakes
    .filter((l) => l.center || l.phase)
    .sort((a, b) => Number(b.center) - Number(a.center))
  const out: { num: number; cls: string; center: boolean; lx: number; ly: number; anchor: 'middle' | 'start' | 'end' }[] = []
  for (const l of lks) {
    const r = bbox(l)
    const w = String(l.num).length * 17 + 6
    const cx = (r.x0 + r.x1) / 2
    const cy = (r.y0 + r.y1) / 2
    const cands: { lx: number; ly: number; anchor: 'middle' | 'start' | 'end' }[] = [
      { lx: cx, ly: r.y0 - 9, anchor: 'middle' },
      { lx: cx, ly: r.y1 + 29, anchor: 'middle' },
      { lx: r.x1 + 8, ly: cy + 10, anchor: 'start' },
      { lx: r.x0 - 8, ly: cy + 10, anchor: 'end' },
      { lx: cx, ly: r.y0 - 36, anchor: 'middle' },
      { lx: cx, ly: r.y1 + 56, anchor: 'middle' },
    ]
    const boxOf = (c: (typeof cands)[number]): Box => {
      const x0 = c.anchor === 'middle' ? c.lx - w / 2 : c.anchor === 'start' ? c.lx : c.lx - w
      return { x0, y0: c.ly - 22, x1: x0 + w, y1: c.ly + 5 }
    }
    const pick = cands.find((c) => !over(boxOf(c))) ?? cands[0]
    taken.push(boxOf(pick))
    out.push({ num: l.num, cls: l.cls, center: l.center, ...pick })
  }
  return out
})
// The center-lake key under the stress space: every center lake with a
// point, in order.
const centers = computed(() => [...new Set(props.points.map((p) => p.center))].sort((a, b) => a - b))

type HA = 'left' | 'center' | 'right'
type VA = 'top' | 'middle' | 'bottom'
function eqAt(name: Ch2EqName, kk: number, x: number, y: number, ha: HA, va: VA) {
  const b = CH2_EQ[name]
  const w = b.w * kk
  const h = b.h * kk
  const x0 = ha === 'left' ? x : ha === 'center' ? x - w / 2 : x - w
  const y0 = va === 'top' ? y : va === 'middle' ? y - h / 2 : y - h
  return { href: ch2EqUrl(name), x: x0, y: y0, width: w, height: h }
}
/** An <img> of a LaTeX label at `px` CSS px per bp. */
function eqStyle(name: Ch2EqName, px: number) {
  const b = CH2_EQ[name]
  return {
    width: `${b.w * px}px`,
    height: `${b.h * px}px`,
    verticalAlign: `${-(b.h - b.base) * px}px`,
  }
}
</script>

<style scoped>
.im-root {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1.2vh;
  padding: calc(var(--chrome-bottom, 7vh) + 1.5vh) 3vw 3vh;
  box-sizing: border-box;
}
.im-row {
  display: flex;
  justify-content: center;
  align-items: stretch;
  gap: 4vw;
  width: 100%;
  flex: 1 1 auto;
  min-height: 0;
}
.im-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 0;
  flex: 0 1 min(42vw, 64vh);
}
.im-title {
  font-family: 'EB Garamond', serif;
  font-size: 2.3rem;
  line-height: 1;
  color: var(--gold);
  letter-spacing: 0.02em;
  flex: 0 0 auto;
}
.im-svg {
  width: 100%;
  flex: 1 1 auto;
  min-height: 0;
  display: block;
  overflow: visible;
}
/* the stress space's slot: the diagram hugs the top of it (hugTop), its
   svg keeps its own aspect inside */
.im-ss {
  width: 100%;
  flex: 1 1 auto;
  min-height: 0;
  margin-top: 0.4vh;
}
/* the domain's edge: black band, gold line (the block's outline) */
.im-frame-ink {
  fill: none;
  stroke: #050505;
  stroke-width: 7;
}
.im-frame {
  fill: none;
  stroke: var(--gold, #f4cf6a);
  stroke-width: 2.6;
}
/* on the white-centred field: the R ring and its word in dark ink */
.im-patch {
  fill: none;
  stroke: #14171c;
  stroke-width: 2.4;
  stroke-dasharray: 3 6;
  stroke-linecap: round;
}
.im-patchlbl {
  font-family: 'EB Garamond', serif;
  font-style: italic;
  font-size: 28px;
  fill: #14171c;
  paint-order: stroke;
  stroke: rgba(255, 255, 255, 0.9);
  stroke-width: 6px;
  pointer-events: none;
}
.im-contour {
  fill: none;
  stroke: #111;
  stroke-width: 3;
  stroke-dasharray: 10 8;
  pointer-events: none;
}
.im-ring-halo {
  fill: none;
  stroke: rgba(255, 255, 255, 0.75);
  stroke-width: 7;
  stroke-linejoin: round;
  pointer-events: none;
}
.im-ring-halo-center {
  /* the drained lake sits in the field's dark core */
  stroke: rgba(0, 0, 0, 0.85);
  stroke-width: 10;
}
.im-ring {
  fill: transparent;
  stroke-linejoin: round;
  cursor: default;
}
.im-ring-dash {
  stroke-dasharray: 9 7;
}
.im-ring-hl {
  stroke: #f5c75e !important;
}
.im-labels {
  pointer-events: none;
}
.im-num {
  font-family: 'Inter', system-ui, sans-serif;
  font-variant-numeric: tabular-nums;
  font-size: 25px;
  font-weight: 700;
  paint-order: stroke;
  stroke: rgba(255, 255, 255, 0.95);
  stroke-width: 6px;
  stroke-linejoin: round;
}
.im-num-center {
  fill: var(--gold, #f4cf6a);
  stroke: rgba(0, 0, 0, 0.9);
  font-size: 28px;
}
.im-num-hl {
  fill: #f5c75e !important;
}
.im-reach line {
  stroke: var(--gold, #f4cf6a);
  stroke-width: 2.4;
}
.im-reach .im-reach-tie {
  stroke: rgba(244, 207, 106, 0.4);
  stroke-width: 1.4;
  stroke-dasharray: 3 4;
}
.im-key {
  flex: 0 0 auto;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  gap: 0.6rem 2rem;
  margin-top: 0.8vh;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1rem;
  color: rgba(245, 240, 230, 0.94);
}
.im-key-item {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}
/* the block's bar (BlisterStressLegend): matplotlib seismic ±1 MPa */
.im-cbitem {
  align-items: flex-start;
  gap: 0.9rem;
}
.im-cbscale {
  width: 260px;
  padding-top: 4px;
}
.im-cb {
  height: 18px;
  border-radius: 2px;
  box-shadow: 0 0 0 1.5px rgba(245, 240, 230, 0.85);
  background: linear-gradient(to right,
    #00004c, #0000db 12%, #4747ff 26%, #b3b3ff 40%, #ffffff 50%,
    #ffb3b3 60%, #ff4747 74%, #db0000 88%, #800000 100%);
}
.im-cbticks {
  position: relative;
  height: 28px;
  font-size: 17px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.im-cbticks span {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1;
  white-space: nowrap;
}
.im-cbticks i {
  display: block;
  width: 2px;
  height: 7px;
  margin-bottom: 3px;
  background: #f5f0e6;
}
.im-eq {
  display: inline-block;
}
/* the center-lake key under the stress space (the population page's) */
.im-centers {
  flex: 0 0 auto;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1.4rem;
  margin-top: 0.8vh;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1.15rem;
  font-variant-numeric: tabular-nums;
  color: rgba(245, 240, 230, 0.92);
}
.im-center {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
/* ICE FLOW on the field: gold over a black band (the block's arrow) */
.im-flowmark {
  pointer-events: none;
}
.im-flow-ink {
  stroke: #050505;
  stroke-width: 13;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: #050505;
}
.im-flow-gold {
  stroke: var(--gold, #f4cf6a);
  stroke-width: 7;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: var(--gold, #f4cf6a);
}
.im-flowlbl {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.1em;
  fill: var(--gold, #f4cf6a);
  paint-order: stroke;
  stroke: #050505;
  stroke-width: 5px;
  stroke-linejoin: round;
}
.im-takeaway {
  margin: 0.4vh 0 0;
  max-width: 94vw;
  text-align: center;
  font-family: 'EB Garamond', serif;
  font-size: clamp(1.3rem, 2.05vw, 2.1rem);
  line-height: 1.3;
  color: #f5f5f5;
  letter-spacing: 0.01em;
}
</style>
