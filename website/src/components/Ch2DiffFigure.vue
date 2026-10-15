<template>
  <!-- One model's stress response Δσ_t1 as a FLAT figure (the director's
       layout: the 'DIFFERENCE' stresses for the elastic model on the left
       and for the viscous model on the right): the block's drape for
       this lake, north-up in EPSG:3413 like the thesis overview figures,
       the shared ±1 MPa scale, the catalog lakes with their numbers, the
       +100 kPa contour dashed, ice flow + a 5 km bar in the corners the
       rotated domain leaves free. -->
  <svg class="df-svg" viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid meet">
    <image :href="ch2ResultUrl(m.image)" x="0" y="0" width="1000" height="1000" />
    <!-- the domain's edge: black band + gold line (the block's own outline) -->
    <polygon :points="pts(lake.square)" class="df-square-ink" />
    <polygon :points="pts(lake.square)" class="df-square" />
    <!-- +100 kPa -->
    <polyline
      v-for="(ln, i) in m.contour100"
      :key="`c${i}`"
      :points="pts(ln)"
      class="df-contour"
    />
    <!-- catalog lakes -->
    <g v-for="lk in lake.lakes" :key="lk.num">
      <polygon
        v-for="(r, j) in lk.rings"
        :key="j"
        :points="pts(r)"
        class="df-ring"
        :class="{ 'df-ring-dash': lk.cls.startsWith('dash'), 'df-ring-hl': lk.num === highlightNum }"
        :style="{ stroke: ringColor(lk.cls) }"
        :stroke-width="lk.center || lk.phase ? 6.5 : 4.5"
        @pointerenter="lk.phase ? emit('lake-hover', lk.num) : undefined"
        @pointerleave="lk.phase ? emit('lake-hover', null) : undefined"
      />
    </g>
    <g class="df-labels">
      <text
        v-for="lk in labelled"
        :key="`t${lk.num}`"
        :x="lk.lx"
        :y="lk.ly"
        :text-anchor="lk.anchor"
        class="df-num"
        :class="{ 'df-num-center': lk.center, 'df-num-hl': lk.num === highlightNum }"
        :style="{ fill: lk.center ? undefined : ringColor(lk.cls) }"
      >{{ lk.num }}</text>
    </g>
    <!-- ice flow (upper-left corner) -->
    <g :transform="`translate(${flowAt[0]} ${flowAt[1]}) rotate(${flowRot})`" class="df-flow">
      <line x1="-62" y1="0" x2="48" y2="0" />
      <path d="M 66 0 L 40 -13 L 40 13 Z" />
    </g>
    <text :x="flowAt[0]" :y="flowAt[1] + 66" text-anchor="middle" class="df-flowlbl">ICE FLOW</text>
    <!-- 5 km bar (lower-left corner) -->
    <g class="df-bar">
      <line :x1="60" :x2="60 + barLen" :y1="944" :y2="944" />
      <line :x1="60" :x2="60" :y1="932" :y2="956" />
      <line :x1="60 + barLen" :x2="60 + barLen" :y1="932" :y2="956" />
      <text :x="60 + barLen / 2" y="916" text-anchor="middle">5 km</text>
    </g>
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ch2ResultUrl, type Ch2ResultLake } from '../config/ch2Results'
import type { Ch2Model } from '../config/ch2Beats'

const props = defineProps<{
  lake: Ch2ResultLake
  model: Ch2Model
  highlightNum?: number | null
}>()
const emit = defineEmits<{ 'lake-hover': [num: number | null] }>()

const m = computed(() => props.lake.models[props.model])

function pts(ring: [number, number][]): string {
  return ring.map(([u, v]) => `${(u * 1000).toFixed(1)},${(v * 1000).toFixed(1)}`).join(' ')
}

// On the white-centred seismic field the classes need darker inks than
// the dark-theme symbols (the thesis overviews: cyan, dark gray, black).
function ringColor(cls: string): string {
  if (cls.endsWith('cyan')) return '#00b8d9'
  if (cls.endsWith('gray')) return '#5d646d'
  if (cls === 'magenta') return '#d63fcf'
  return '#14171c'
}

// Lake numbers: above each ring if free, else below / right / left —
// a greedy pass against the rings and the numbers already placed.
const labelled = computed(() => {
  type Box = { x0: number; y0: number; x1: number; y1: number }
  const lks = props.lake.lakes.filter((l) => l.center || l.phase)
  const bbox = (l: (typeof lks)[number]): Box => {
    const xs = l.rings.flat().map((p) => p[0] * 1000)
    const ys = l.rings.flat().map((p) => p[1] * 1000)
    return { x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys) }
  }
  const taken: Box[] = props.lake.lakes.map(bbox)
  const over = (b: Box) =>
    taken.some((o) => b.x0 < o.x1 && b.x1 > o.x0 && b.y0 < o.y1 && b.y1 > o.y0)
  return lks.map((l) => {
    const r = bbox(l)
    const w = String(l.num).length * 31 + 14
    const cx = (r.x0 + r.x1) / 2
    const cy = (r.y0 + r.y1) / 2
    const cands: { lx: number; ly: number; anchor: 'middle' | 'start' | 'end' }[] = [
      { lx: cx, ly: r.y0 - 12, anchor: 'middle' },
      { lx: cx, ly: r.y1 + 46, anchor: 'middle' },
      { lx: r.x1 + 10, ly: cy + 16, anchor: 'start' },
      { lx: r.x0 - 10, ly: cy + 16, anchor: 'end' },
      { lx: cx, ly: r.y0 - 56, anchor: 'middle' },
      { lx: cx, ly: r.y1 + 90, anchor: 'middle' },
    ]
    const boxOf = (c: (typeof cands)[number]): Box => {
      const x0 = c.anchor === 'middle' ? c.lx - w / 2 : c.anchor === 'start' ? c.lx : c.lx - w
      return { x0, y0: c.ly - 36, x1: x0 + w, y1: c.ly + 8 }
    }
    const pick = cands.find((c) => !over(boxOf(c))) ?? cands[0]
    taken.push(boxOf(pick))
    return { ...l, ...pick }
  })
})

// Flow direction: the local +x axis (downstream) at flow_angle_deg from
// EPSG:3413 east, counter-clockwise; the image's y runs DOWN.
const flowRot = computed(() => -props.lake.flow_angle_deg)
// The arrow goes in a corner the rotated domain leaves free (outside
// the square) and farthest from any lake (2511's catalog spills past the
// domain into its top-right corner). The bottom-left keeps the 5 km bar.
function segDist(px: number, py: number, ax: number, ay: number, bx: number, by: number): number {
  const vx = bx - ax
  const vy = by - ay
  const t = Math.max(0, Math.min(1, ((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy || 1)))
  return Math.hypot(px - (ax + t * vx), py - (ay + t * vy))
}
function insideSquare(px: number, py: number, sq: [number, number][]): boolean {
  let inside = false
  for (let i = 0, j = sq.length - 1; i < sq.length; j = i++) {
    const [xi, yi] = sq[i]
    const [xj, yj] = sq[j]
    if (yi > py !== yj > py && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) inside = !inside
  }
  return inside
}
const flowAt = computed<[number, number]>(() => {
  const sq = props.lake.square.map(([u, v]) => [u * 1000, v * 1000] as [number, number])
  const cands: [number, number][] = [[130, 120], [870, 120], [870, 880]]
  let best: [number, number] = cands[0]
  let bestScore = -Infinity
  for (const [x, y] of cands) {
    if (insideSquare(x, y, sq)) continue
    const edge = Math.min(...sq.map((a, i) => {
      const b = sq[(i + 1) % sq.length]
      return segDist(x, y, a[0], a[1], b[0], b[1])
    }))
    if (edge < 40) continue
    const lakeD = Math.min(...props.lake.lakes.map((l) => Math.hypot(l.c[0] * 1000 - x, l.c[1] * 1000 - y)))
    const score = Math.min(lakeD, 400) + Math.min(edge, 120)
    if (score > bestScore) {
      bestScore = score
      best = [x, y]
    }
  }
  return best
})
const barLen = computed(() => (5 / (2 * props.lake.bbox_half_km)) * 1000)
</script>

<style scoped>
.df-svg {
  width: 100%;
  height: 100%;
  display: block;
}
.df-square-ink {
  fill: none;
  stroke: #050505;
  stroke-width: 18;
  stroke-linejoin: round;
}
.df-square {
  fill: none;
  stroke: #f4cf6a;
  stroke-width: 7;
}
.df-contour {
  fill: none;
  stroke: #111;
  stroke-width: 4.5;
  stroke-dasharray: 16 11;
  pointer-events: none;
}
.df-ring {
  fill: transparent;
  stroke-linejoin: round;
  cursor: default;
}
.df-ring-dash {
  stroke-dasharray: 12 9;
}
.df-ring-hl {
  stroke: #f5c75e !important;
}
.df-labels {
  pointer-events: none;
}
.df-num {
  font-family: 'Inter', system-ui, sans-serif;
  font-variant-numeric: tabular-nums;
  /* the SVG renders ~1/3 scale on the compare page: 46 units ≈ 15 px */
  font-size: 46px;
  font-weight: 700;
  paint-order: stroke;
  stroke: rgba(255, 255, 255, 0.95);
  stroke-width: 9px;
  stroke-linejoin: round;
}
.df-num-center {
  fill: #9a6a08;
}
.df-num-hl {
  fill: #b07d10 !important;
}
.df-flow line {
  stroke: var(--gold, #f4cf6a);
  stroke-width: 8;
  stroke-linecap: round;
}
.df-flow path {
  fill: var(--gold, #f4cf6a);
}
.df-flowlbl {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 38px;
  font-weight: 600;
  letter-spacing: 0.1em;
  fill: var(--gold, #f4cf6a);
}
.df-bar line {
  stroke: rgba(245, 240, 230, 0.95);
  stroke-width: 5;
}
.df-bar text {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 42px;
  font-weight: 600;
  fill: rgba(245, 240, 230, 0.9);
}
</style>
