<template>
  <!-- The literature timeline's title-page cartoons:
       one hand-drawn sketch of each paper's defining figure, in ink on
       the card's paper, where the author/year pill used to sit.
       Qualitative, not quantitative — the director's brief was a simple
       cartoon that need not be scientifically accurate but should be
       qualitatively accurate. Same 120 × 80 frame for all eleven; ink strokes inherit
       from the root group, colour is water-blue, tensile red,
       compressive blue, the Ch.1 patch gold. -->
  <svg
    class="tl-fig"
    viewBox="0 0 120 80"
    preserveAspectRatio="xMidYMid meet"
    aria-hidden="true"
  >
    <g
      :stroke="INK"
      stroke-width="1.6"
      fill="none"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <!-- Zwally 2002 · surface velocity rises with the summer melt:
           a year of GPS speed (ink) over the melt season (blue). -->
      <g v-if="id === 'zwally2002'">
        <path d="M14 66 H112 M14 66 V12" stroke-width="1.4" />
        <path
          d="M30 66 C 44 66, 50 30, 62 30 C 74 30, 80 66, 94 66 Z"
          :fill="WATER"
          fill-opacity="0.5"
          stroke="none"
        />
        <path d="M14 54 H34 C 48 54, 54 20, 66 20 C 78 20, 84 54, 98 54 H112" stroke-width="2.2" />
        <g :fill="SUN" stroke-width="1">
          <circle cx="100" cy="18" r="4" />
          <path d="M100 10 v-3 M100 26 v3 M92 18 h-3 M108 18 h3 M94.3 12.3 l-2.1-2.1 M105.7 23.7 l2.1 2.1 M94.3 23.7 l-2.1 2.1 M105.7 12.3 l2.1-2.1" />
        </g>
        <text x="17" y="18" class="tl-t" :fill="INK" stroke="none">u</text>
        <text x="108" y="75" class="tl-t" :fill="INK" stroke="none">t</text>
      </g>

      <!-- Price 2008 · a lubricated margin drags the inland ice along:
           flowline with the sliding zone at the bed near the margin
           (blue) and the speed-up arrows shrinking inland. -->
      <g v-else-if="id === 'price2008'">
        <path d="M6 63 C 22 44, 52 30, 114 22 V65 H6 Z" :fill="ICE" />
        <path d="M6 65 H114" stroke-width="1.4" />
        <path :d="hatch(65, 12, 112)" stroke-width="0.9" />
        <path d="M8 64.6 H44" :stroke="WATER" stroke-width="3.2" />
        <path :d="arrow(38, 52, 18, 52)" stroke-width="2.1" />
        <path :d="arrow(60, 48, 46, 48)" stroke-width="2.1" />
        <path :d="arrow(82, 46, 72, 46)" stroke-width="2.1" />
        <path :d="arrow(102, 44, 96, 44)" stroke-width="2.1" />
      </g>

      <!-- Das 2008 · hydro-fracture: the lake drains through a crack to
           the bed, water spreads as a blister, the surface lifts. -->
      <g v-else-if="id === 'das2008'">
        <path d="M6 22 C 30 19, 90 19, 114 22 V65 H6 Z" :fill="ICE" />
        <path d="M6 65 H114" stroke-width="1.4" />
        <path :d="hatch(65, 12, 112)" stroke-width="0.9" />
        <path d="M38 20.6 C 44 30, 76 30, 82 20.6" :fill="BOWL" />
        <path d="M42.5 25 C 48 28.6, 72 28.6, 77.5 25 Z" :fill="WATER" stroke="none" />
        <path d="M60 28 L58 37 L62 46 L59 55 L61 64" stroke-width="2.2" />
        <path d="M60 28 L58 37 L62 46 L59 55 L61 64" :stroke="WATER" stroke-width="0.9" />
        <path d="M32 65 C 42 57, 78 57, 88 65 Z" :fill="WATER" stroke="none" />
        <path d="M32 65 C 42 57, 78 57, 88 65" :stroke="WATER_DK" stroke-width="1" />
        <path :d="arrow(42, 16, 42, 7)" stroke-width="1.8" />
        <path :d="arrow(78, 16, 78, 7)" stroke-width="1.8" />
      </g>

      <!-- Schoof 2010 · the paper's Fig. 1: a cavity in the lee of a bed
           step (left) and a melt-cut channel (right), and under them the
           steady effective pressure N against discharge Q — falling
           while the conduit is a cavity, rising once it is a channel,
           the switch at the open circle (Q_c). -->
      <g v-else-if="id === 'schoof2010'">
        <path d="M18 8 H52 V25 H34 V15 H18 Z M68 8 H104 V25 H68 Z" :fill="ICE" stroke="none" />
        <path d="M34 15 C 41 15, 47 20, 52 25 H34 Z" :fill="WATER" stroke="none" />
        <path d="M18 15 H34 V25 H52" stroke-width="1.4" />
        <path :d="hatch(15, 23, 33, 6, 3) + ' ' + hatch(25, 40, 52, 6, 3)" stroke-width="0.8" />
        <path :d="arrow(22, 11, 38, 11, 3)" stroke-width="1.2" />
        <path d="M77 25 A 9 9 0 0 1 95 25 Z" :fill="WATER" stroke="none" />
        <path d="M68 25 H104" stroke-width="1.4" />
        <path :d="hatch(25, 72, 104, 6, 3)" stroke-width="0.8" />
        <path d="M14 70 H112 M14 70 V32" stroke-width="1.4" />
        <path d="M20 35 C 24 52, 34 62, 46 62" stroke-width="2.2" />
        <path d="M46 62 C 66 62, 90 52, 108 35" stroke-width="2.2" stroke-dasharray="4 3" />
        <circle cx="46" cy="62" r="2.6" :fill="ICE" stroke-width="1.4" />
        <text x="4" y="40" class="tl-t" :fill="INK" stroke="none">N</text>
        <text x="106" y="79" class="tl-t" :fill="INK" stroke="none">Q</text>
      </g>

      <!-- Leeson 2015 · lakes march inland under warming: the west
           coast (ocean left), today's lake band, the projected band
           further up the ice sheet. -->
      <g v-else-if="id === 'leeson2015'">
        <path
          d="M0 0 H20 C 26 8, 14 14, 22 22 C 30 30, 12 36, 20 44 C 28 52, 14 60, 22 68 C 27 74, 18 78, 24 80 H0 Z"
          :fill="OCEAN"
          stroke="none"
        />
        <path d="M20 0 C 26 8, 14 14, 22 22 C 30 30, 12 36, 20 44 C 28 52, 14 60, 22 68 C 27 74, 18 78, 24 80" stroke-width="1.5" />
        <path
          d="M50 0 C 46 20, 54 40, 48 60 C 46 70, 50 76, 49 80 M74 0 C 70 20, 78 40, 72 60 C 70 70, 74 76, 73 80 M98 0 C 94 20, 102 40, 96 60 C 94 70, 98 76, 97 80"
          :stroke="FAINT"
          stroke-width="0.8"
          stroke-dasharray="2.5 2.5"
        />
        <g :fill="WATER" :stroke="WATER_DK" stroke-width="0.8">
          <circle cx="30" cy="10" r="2.3" />
          <circle cx="38" cy="19" r="2.3" />
          <circle cx="33" cy="30" r="2.3" />
          <circle cx="45" cy="26" r="2.3" />
          <circle cx="36" cy="48" r="2.3" />
          <circle cx="46" cy="56" r="2.3" />
          <circle cx="31" cy="64" r="2.3" />
          <circle cx="42" cy="72" r="2.3" />
          <circle cx="50" cy="66" r="2.3" />
          <circle cx="44" cy="8" r="2.3" />
        </g>
        <g :stroke="WATER_DK" stroke-width="1" stroke-dasharray="1.6 1.4">
          <circle cx="62" cy="16" r="2.3" />
          <circle cx="70" cy="28" r="2.3" />
          <circle cx="66" cy="50" r="2.3" />
          <circle cx="78" cy="58" r="2.3" />
          <circle cx="72" cy="70" r="2.3" />
          <circle cx="84" cy="22" r="2.3" />
          <circle cx="82" cy="72" r="2.3" />
          <circle cx="88" cy="48" r="2.3" />
        </g>
        <path :d="arrow(50, 40, 88, 40, 6)" stroke-width="2.4" />
      </g>

      <!-- Stevens 2015 · the trigger: meltwater down a moulin slips the
           bed upstream, the basin goes into tension (GPS array on the
           surface) and the crack opens under the lake. -->
      <g v-else-if="id === 'stevens2015'">
        <path d="M6 24 C 30 21, 90 21, 114 24 V65 H6 Z" :fill="ICE" />
        <path d="M6 65 H114" stroke-width="1.4" />
        <path :d="hatch(65, 12, 112)" stroke-width="0.9" />
        <path d="M40 22.6 C 46 31, 74 31, 80 22.6 Z" :fill="WATER" :stroke="WATER_DK" stroke-width="1" />
        <path d="M100 22.3 L100 64" :stroke="WATER" stroke-width="2" />
        <path d="M96 22 L104 22 L100 27 Z" :fill="WATER" stroke="none" />
        <path d="M100 63.6 H34" :stroke="WATER" stroke-width="3" />
        <path :d="arrow(90, 59, 58, 59)" stroke-width="1.8" />
        <path :d="arrow(44, 12, 30, 12)" stroke-width="1.8" />
        <path :d="arrow(76, 12, 90, 12)" stroke-width="1.8" />
        <path d="M60 30 L59 35 L61.5 41" stroke-width="2" />
        <path
          d="M28 23.4 l2.6-4.5 l2.6 4.5 Z M46 22.8 l2.6-4.5 l2.6 4.5 Z M68 22.8 l2.6-4.5 l2.6 4.5 Z M86 23.2 l2.6-4.5 l2.6 4.5 Z"
          :fill="INK"
          stroke="none"
        />
      </g>

      <!-- Christoffersen 2018 · the cascade: one drainage's tensile
           shock cracks the next lake, and the next, across the chain. -->
      <g v-else-if="id === 'christoffersen2018'">
        <g :fill="BOWL" stroke-width="1.4">
          <ellipse cx="16" cy="62" rx="9" ry="5" />
          <ellipse cx="34" cy="52" rx="9" ry="5" />
          <ellipse cx="52" cy="43" rx="9" ry="5" />
          <ellipse cx="70" cy="34" rx="9" ry="5" />
        </g>
        <path
          d="M10 63 l4-2 l3 2 l4-2 l3 2 M28 53 l4-2 l3 2 l4-2 l3 2 M46 44 l4-2 l3 2 l4-2 l3 2 M64 35 l4-2 l3 2 l4-2 l3 2"
          stroke-width="1.2"
        />
        <path d="M5 52 l3 3 M16 50 v4 M27 52 l-3 3 M2 63 h4 M26 69 l-3-2 M6 71 l3-2" stroke-width="1" />
        <g :fill="WATER" :stroke="WATER_DK" stroke-width="1">
          <ellipse cx="88" cy="25" rx="9" ry="5" />
          <ellipse cx="106" cy="16" rx="9" ry="5" />
        </g>
        <path :d="qarrow(18, 56, 26, 45, 32, 47)" stroke-width="1.6" />
        <path :d="qarrow(36, 46, 44, 36, 50, 38)" stroke-width="1.6" />
        <path :d="qarrow(54, 37, 62, 27, 68, 29)" stroke-width="1.6" />
        <path :d="qarrow(72, 28, 80, 18, 86, 20)" stroke-width="1.6" />
        <path d="M90 19 Q 98 9, 104 11" stroke-width="1.4" stroke-dasharray="2.2 2" />
        <path :d="head(98, 9, 104, 11)" stroke-width="1.4" />
      </g>

      <!-- Lai 2021 · the relaxation: uplift jumps at the drainage, then
           settles over days as the blister of water spreads at the bed;
           the settling rate reads the bed's transmissivity. -->
      <g v-else-if="id === 'lai2021'">
        <path d="M14 66 H112 M14 66 V12" stroke-width="1.4" />
        <path d="M14 58 H36 L38 20 C 46 20, 56 44, 72 52 C 86 57, 100 58, 112 58" stroke-width="2" />
        <g :fill="WATER" :stroke="WATER_DK" stroke-width="0.6">
          <circle cx="20" cy="58.3" r="1.5" />
          <circle cx="28" cy="57.6" r="1.5" />
          <circle cx="34" cy="58.4" r="1.5" />
          <circle cx="40" cy="21.5" r="1.5" />
          <circle cx="44.5" cy="24.5" r="1.5" />
          <circle cx="52" cy="33.5" r="1.5" />
          <circle cx="61" cy="43" r="1.5" />
          <circle cx="72" cy="51.5" r="1.5" />
          <circle cx="82" cy="55" r="1.5" />
          <circle cx="93" cy="57" r="1.5" />
          <circle cx="104" cy="57.6" r="1.5" />
        </g>
        <path d="M74 18 H110 M74 40 H110" stroke-width="1" />
        <path :d="hatch(40, 78, 110, 6, 3)" stroke-width="0.7" />
        <path d="M84 40 C 88 28, 96 28, 100 40 Z" :fill="WATER" stroke="none" />
        <path d="M77 40 C 84 33, 100 33, 107 40" :stroke="WATER_DK" stroke-width="1" stroke-dasharray="2 1.6" />
        <path :d="arrow(82, 37, 76, 37, 2.5)" stroke-width="1" />
        <path :d="arrow(102, 37, 108, 37, 2.5)" stroke-width="1" />
      </g>

      <!-- Stevens 2024 · elastic coupling: a drained lake's stress
           field, tensile lobes (red) along flow, compressive (blue)
           across, and the neighbour sitting in a tensile lobe. -->
      <g v-else-if="id === 'stevens2024'">
        <ellipse cx="26" cy="40" rx="18" ry="10" :fill="RED" fill-opacity="0.32" stroke="none" />
        <ellipse cx="74" cy="40" rx="18" ry="10" :fill="RED" fill-opacity="0.32" stroke="none" />
        <ellipse cx="50" cy="17" rx="10" ry="8" :fill="BLUE" fill-opacity="0.3" stroke="none" />
        <ellipse cx="50" cy="63" rx="10" ry="8" :fill="BLUE" fill-opacity="0.3" stroke="none" />
        <ellipse cx="50" cy="40" rx="10" ry="6" :fill="BOWL" stroke-width="1.5" />
        <path d="M43 41 l4-2 l3 2 l4-2 l3 2" stroke-width="1.2" />
        <ellipse cx="96" cy="40" rx="9" ry="5.5" :fill="WATER" :stroke="WATER_DK" stroke-width="1" />
        <path d="M87.4 38.4 l-2.4 1.2 l-1.6 2.6" stroke-width="1.2" />
        <path d="M62 40 H80" stroke-width="1.6" stroke-dasharray="2.5 2" />
        <path :d="head(78, 40, 84, 40)" stroke-width="1.6" />
        <path :d="arrow(8, 10, 24, 10, 3.5)" stroke-width="1.4" />
      </g>

      <!-- Stevens 2026 · the cascade does not climb: lower lakes drain
           in sequence, the chain stops at the elevation line, the
           inland lakes stay full. -->
      <g v-else-if="id === 'stevens2026'">
        <path d="M6 62 C 30 54, 70 34, 114 16 V66 H6 Z" :fill="ICE" />
        <path d="M6 66 H114" stroke-width="1.4" />
        <path :d="hatch(66, 12, 112)" stroke-width="0.9" />
        <path d="M6 36 H114" :stroke="FAINT" stroke-width="0.8" stroke-dasharray="2.5 2.5" />
        <g :fill="BOWL" stroke-width="1.3">
          <ellipse cx="18" cy="57.6" rx="6" ry="2.6" transform="rotate(-20 18 57.6)" />
          <ellipse cx="37" cy="49.8" rx="6" ry="2.6" transform="rotate(-24 37 49.8)" />
          <ellipse cx="58" cy="40.2" rx="6" ry="2.6" transform="rotate(-26 58 40.2)" />
        </g>
        <path d="M18 60 L17 62 L19 64 L18 66 M37 52 L36 55 L38 58 L37 61 L38 66 M58 43 L57 47 L59 52 L58 57 L59 66" stroke-width="1.5" />
        <g :fill="WATER" :stroke="WATER_DK" stroke-width="1">
          <ellipse cx="82" cy="29.6" rx="6" ry="2.6" transform="rotate(-24 82 29.6)" />
          <ellipse cx="101" cy="21.4" rx="6" ry="2.6" transform="rotate(-20 101 21.4)" />
        </g>
        <path :d="arrow(24, 52, 31, 49)" stroke-width="1.8" />
        <path :d="arrow(43, 44.5, 51, 41)" stroke-width="1.8" />
        <path d="M64 35 L69 32.8" stroke-width="1.6" stroke-dasharray="1.6 1.6" />
        <path d="M71 28.5 L74 34.5" stroke-width="2.6" />
      </g>

      <!-- Rines 2026 · the longitudinal stress a slippery patch (gold)
           sends to the surface: tension upstream, compression down,
           and the coupling length over which it reaches. -->
      <g v-else-if="id === 'rines2026'">
        <path d="M6 50 H114 V66 H6 Z" :fill="ICE" />
        <path d="M6 66 H114" stroke-width="1.4" />
        <path :d="hatch(66, 12, 112)" stroke-width="0.9" />
        <path d="M46 65.6 H78" :stroke="GOLD" stroke-width="3.6" />
        <path :d="arrow(12, 58, 26, 58, 3.5)" stroke-width="1.6" />
        <path d="M8 28 H112" :stroke="FAINT" stroke-width="0.8" stroke-dasharray="2 2" />
        <path d="M8 28 C 28 28, 40 25, 46 10 L62 28 Z" :fill="RED" fill-opacity="0.3" stroke="none" />
        <path d="M62 28 L78 46 C 84 32, 96 29, 112 28 Z" :fill="BLUE" fill-opacity="0.3" stroke="none" />
        <path d="M8 28 C 28 28, 40 25, 46 10 L78 46 C 84 32, 96 29, 112 28" stroke-width="2" />
        <path d="M46 50 V10 M78 50 V46 M20 50 V16" :stroke="FAINT" stroke-width="0.7" stroke-dasharray="1.5 1.5" />
        <path :d="arrow(33, 16, 20, 16, 3) + ' ' + arrow(33, 16, 46, 16, 3)" stroke-width="1.2" />
        <text x="33" y="13" text-anchor="middle" class="tl-t tl-t-sm" :fill="INK" stroke="none">ACL</text>
      </g>
    </g>
  </svg>
</template>

<script setup lang="ts">
defineProps<{ id: string }>()

const INK = '#1c1a16'
const ICE = '#f8f6f0'
const BOWL = '#e2ddd0'
const OCEAN = '#c9dfef'
const WATER = '#5f9fd8'
const WATER_DK = '#2b6cb0'
const SUN = '#e6b94a'
const GOLD = '#cf9a2c'
const RED = '#d5504a'
const BLUE = '#4d7fc4'
const FAINT = '#8e8677'

/** Short diagonal ticks under a bed line. */
function hatch(y: number, x0: number, x1: number, step = 8, len = 4): string {
  let d = ''
  for (let x = x0; x <= x1; x += step) d += `M${x} ${y} l-3 ${len} `
  return d.trim()
}
/** Open chevron at (x1, y1) pointing along (x0,y0) → (x1,y1). */
function head(x0: number, y0: number, x1: number, y1: number, h = 4): string {
  const dx = x1 - x0
  const dy = y1 - y0
  const L = Math.hypot(dx, dy) || 1
  const ux = dx / L
  const uy = dy / L
  const px = -uy
  const py = ux
  const bx = x1 - ux * h
  const by = y1 - uy * h
  const w = h * 0.6
  return `M${(bx + px * w).toFixed(2)} ${(by + py * w).toFixed(2)} L${x1} ${y1} L${(bx - px * w).toFixed(2)} ${(by - py * w).toFixed(2)}`
}
/** Straight arrow with a chevron head. */
function arrow(x0: number, y0: number, x1: number, y1: number, h = 4): string {
  return `M${x0} ${y0} L${x1} ${y1} ${head(x0, y0, x1, y1, h)}`
}
/** Quadratic arrow: the head follows the end tangent. */
function qarrow(x0: number, y0: number, cx: number, cy: number, x1: number, y1: number, h = 4): string {
  return `M${x0} ${y0} Q ${cx} ${cy}, ${x1} ${y1} ${head(cx, cy, x1, y1, h)}`
}
</script>

<style scoped>
.tl-fig {
  display: block;
  width: 100%;
  height: 100%;
}
.tl-t {
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  font-size: 8px;
}
.tl-t-sm {
  font-size: 6.5px;
  font-style: normal;
  letter-spacing: 0.04em;
}
</style>
