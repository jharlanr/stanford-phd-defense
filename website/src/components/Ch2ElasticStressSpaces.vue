<template>
  <!-- The thesis's ELASTIC stress space (Fig. 2.20), drawn live from
       phase_space_v2.json — the baked thesis figure put
       the elastic solve's own absolute post-blister stress on x, which has
       no physical meaning (an elastic body loaded by gravity from an
       unstressed state). Here x is the physical post-drainage state,
       σ(σ^V_pre + Δσ^E): the viscous pre-drainage tensor plus the elastic
       perturbation, then the principals (x1/x2); top row y = Δσ (y1/y2),
       bottom row y = the viscous pre-drainage principal (x1_pre/x2_pre).
       The thesis figure's layout, frame (±2000 kPa) and marker language,
       on its white paper. -->
  <svg class="ess" :viewBox="`0 0 ${VW} ${VH}`" role="img" aria-label="Elastic stress space: perturbation and pre-drainage stress against the post-drainage stress (viscous pre plus elastic perturbation)">
    <rect :width="VW" :height="VH" fill="#fff" />
    <!-- column titles -->
    <text v-for="(c, ci) in COMPS" :key="`ct${c}`" :x="px0(ci) + P / 2" :y="MT - 22" text-anchor="middle" class="ess-title">
      <tspan font-style="italic">σ</tspan><tspan baseline-shift="sub" font-size="0.72em" font-style="italic">t{{ ci + 1 }}</tspan>
    </text>
    <!-- row labels -->
    <text
      v-for="(r, ri) in ROWS"
      :key="`rl${r}`"
      :transform="`translate(40 ${py0(ri) + P / 2}) rotate(-90)`"
      text-anchor="middle"
      class="ess-row"
    >{{ r === 'diff' ? 'Post-drainage vs Δ' : 'Post-drainage vs pre' }}</text>

    <g v-for="(r, ri) in ROWS" :key="r">
      <g v-for="(c, ci) in COMPS" :key="c">
        <!-- grid, zero lines, frame -->
        <line v-for="t in TICKS" :key="`gx${t}`" :x1="sx(ci, t)" :x2="sx(ci, t)" :y1="py0(ri)" :y2="py0(ri) + P" class="ess-grid" />
        <line v-for="t in TICKS" :key="`gy${t}`" :x1="px0(ci)" :x2="px0(ci) + P" :y1="sy(ri, t)" :y2="sy(ri, t)" class="ess-grid" />
        <line :x1="sx(ci, 0)" :x2="sx(ci, 0)" :y1="py0(ri)" :y2="py0(ri) + P" class="ess-zero" />
        <line :x1="px0(ci)" :x2="px0(ci) + P" :y1="sy(ri, 0)" :y2="sy(ri, 0)" class="ess-zero" />
        <rect :x="px0(ci)" :y="py0(ri)" :width="P" :height="P" class="ess-frame" />
        <!-- ticks -->
        <template v-for="t in TICKS" :key="`t${t}`">
          <line :x1="sx(ci, t)" :x2="sx(ci, t)" :y1="py0(ri) + P" :y2="py0(ri) + P + 9" class="ess-tick" />
          <text :x="sx(ci, t)" :y="py0(ri) + P + 38" text-anchor="middle" class="ess-tl">{{ fmt(t) }}</text>
          <line :x1="px0(ci) - 9" :x2="px0(ci)" :y1="sy(ri, t)" :y2="sy(ri, t)" class="ess-tick" />
          <text :x="px0(ci) - 14" :y="sy(ri, t) + 9" text-anchor="end" class="ess-tl">{{ fmt(t) }}</text>
        </template>
        <!-- axis titles -->
        <text :x="px0(ci) + P / 2" :y="py0(ri) + P + 84" text-anchor="middle" class="ess-ax">
          Post-drainage <tspan font-style="italic">σ</tspan><tspan baseline-shift="sub" font-size="0.72em" font-style="italic">t{{ ci + 1 }}</tspan><tspan dx="6">(kPa)</tspan>
        </text>
        <text :transform="`translate(${px0(ci) - 104} ${py0(ri) + P / 2}) rotate(-90)`" text-anchor="middle" class="ess-ax">
          <tspan v-if="r === 'diff'">Δ<tspan font-style="italic">σ</tspan></tspan><tspan v-else>Pre-drainage <tspan font-style="italic">σ</tspan></tspan><tspan baseline-shift="sub" font-size="0.72em" font-style="italic">t{{ ci + 1 }}</tspan><tspan dx="6">(kPa)</tspan>
        </text>
        <!-- points -->
        <g :clip-path="`url(#ess-clip-${uid})`">
          <path
            v-for="pt in pts(r, c)"
            :key="pt.k"
            :d="phaseMarkerPath(pt.shape, pt.x, pt.y, 13)"
            :fill="pt.fill"
            stroke="#000"
            :stroke-width="pt.open ? 3.2 : 1.6"
          />
        </g>
        <!-- the drainage-group key (top-left) and the center-lake key (bottom-right) -->
        <g :transform="`translate(${px0(ci) + 14} ${py0(ri) + 14})`">
          <rect width="214" height="150" rx="6" class="ess-key" />
          <text x="14" y="32" class="ess-kt">Drainage group</text>
          <g v-for="(g, gi) in GROUPS" :key="g.id" :transform="`translate(30 ${62 + gi * 32})`">
            <path :d="phaseMarkerPath('o', 0, 0, 11)" :fill="g.fill" stroke="#000" :stroke-width="g.open ? 3.2 : 1.6" />
            <text x="26" y="8" class="ess-kl">{{ g.label }}</text>
          </g>
        </g>
        <g :transform="`translate(${px0(ci) + P - 14 - 150} ${py0(ri) + P - 14 - (46 + centers.length * 30)})`">
          <rect width="150" :height="46 + centers.length * 30" rx="6" class="ess-key" />
          <text x="75" y="32" text-anchor="middle" class="ess-kt">Center lake</text>
          <g v-for="(n, ni) in centers" :key="n" :transform="`translate(40 ${60 + ni * 30})`">
            <path :d="phaseMarkerPath(PHASE_CENTER_MARKERS[n] ?? 'o', 0, 0, 11)" fill="#d9d9d9" stroke="#000" stroke-width="1.6" />
            <text x="28" y="8" class="ess-kl">{{ n }}</text>
          </g>
        </g>
      </g>
    </g>
    <defs>
      <clipPath :id="`ess-clip-${uid}`">
        <rect v-for="(b, i) in clipRects" :key="i" :x="b[0]" :y="b[1]" :width="P" :height="P" />
      </clipPath>
    </defs>
  </svg>
</template>

<script setup lang="ts">
import { computed, onMounted, shallowRef } from 'vue'
import { PHASE_CENTER_MARKERS, phaseMarkerPath, type PhasePoint } from '../config/simLakes'
import { loadCh2Phase } from '../config/ch2Results'

const COMPS = ['t1', 't2'] as const
const ROWS = ['diff', 'pre'] as const
type Row = (typeof ROWS)[number]
type Comp = (typeof COMPS)[number]

// ── layout (viewBox units, the thesis figure's 2000 × 1892 proportions) ──
const VW = 2000
const P = 760 // a panel's square
const ML = 215 // the row label + y ticks + y title
const GX = 215 // between the columns
const MT = 80
const GY = 170 // between the rows
const VH = MT + 2 * P + GY + 110
const LIM = 2000
const TICKS = [-2000, -1500, -1000, -500, 0, 500, 1000, 1500, 2000]
const uid = Math.random().toString(36).slice(2, 8)

function px0(ci: number): number {
  return ML + ci * (P + GX)
}
function py0(ri: number): number {
  return MT + ri * (P + GY)
}
function sx(ci: number, v: number): number {
  return px0(ci) + ((v + LIM) / (2 * LIM)) * P
}
function sy(ri: number, v: number): number {
  return py0(ri) + P - ((v + LIM) / (2 * LIM)) * P
}
function fmt(t: number): string {
  return t < 0 ? `−${Math.abs(t)}` : `${t}`
}
const clipRects = ROWS.flatMap((_, ri) => COMPS.map((__, ci) => [px0(ci), py0(ri)] as [number, number]))

// The thesis figure's colours (light paper): englacial cyan, lateral
// gray, none open (black ring).
const FILL: Record<string, { fill: string; open: boolean }> = {
  cyan: { fill: '#00d0ef', open: false },
  gray: { fill: '#8c8c8c', open: false },
  black: { fill: 'none', open: true },
}
const GROUPS = [
  { id: 'cyan', label: 'Englacial', ...FILL.cyan },
  { id: 'gray', label: 'Lateral', ...FILL.gray },
  { id: 'black', label: 'None', fill: '#fff', open: true },
]

const points = shallowRef<PhasePoint[]>([])
onMounted(async () => {
  const j = await loadCh2Phase()
  points.value = j?.models.elastic?.points ?? []
})
const centers = computed(() => [...new Set(points.value.map((p) => p.center))].sort((a, b) => a - b))

function pts(r: Row, c: Comp) {
  const ri = ROWS.indexOf(r)
  const ci = COMPS.indexOf(c)
  const out: { k: string; x: number; y: number; shape: string; fill: string; open: boolean }[] = []
  for (const p of points.value) {
    const x = c === 't1' ? p.x1 : p.x2
    const y = r === 'diff' ? (c === 't1' ? p.y1 : p.y2) : c === 't1' ? p.x1_pre : p.x2_pre
    const st = FILL[p.group]
    if (x == null || y == null || !st) continue
    out.push({ k: `${p.center}-${p.num}`, x: sx(ci, x), y: sy(ri, y), shape: PHASE_CENTER_MARKERS[p.center] ?? 'o', ...st })
  }
  // open (none) symbols on top, as matplotlib drew the groups in order
  return out.sort((a, b) => Number(a.open) - Number(b.open))
}
</script>

<style scoped>
.ess {
  display: block;
  width: 100%;
  height: auto;
}
.ess text {
  font-family: 'DejaVu Sans', 'Inter', system-ui, sans-serif;
  fill: #111;
}
.ess-title { font-size: 44px; font-family: 'EB Garamond', serif !important; }
.ess-row { font-size: 38px; font-weight: 700; }
.ess-ax { font-size: 34px; }
.ess-tl { font-size: 27px; }
.ess-kt { font-size: 25px; }
.ess-kl { font-size: 23px; }
.ess-grid { stroke: #e6e6e6; stroke-width: 1.2; }
.ess-zero { stroke: #a8a8a8; stroke-width: 2; }
.ess-frame { fill: none; stroke: #000; stroke-width: 2.2; }
.ess-tick { stroke: #000; stroke-width: 2; }
.ess-key { fill: rgba(255, 255, 255, 0.85); stroke: #ccc; stroke-width: 1.5; }
</style>
