<template>
  <!-- One field of the Chapter 2 viewer as an SI panel on white paper: the
       baked field (img, under) and everything that must stay crisp and
       identical across fields (svg, over) — the LaTeX name, the axes in
       EPSG:3413 km, the 15 km tile, the drainage-class lake outlines and
       numbers, the colour bar. One viewBox, so it scales as a figure. -->
  <div class="fp" :style="{ aspectRatio: `${VB_W} / ${VB_H}` }">
    <img
      v-if="src"
      class="fp-img"
      :src="src"
      alt=""
      draggable="false"
      :style="{
        left: pct(MX, VB_W),
        top: pct(MY, VB_H),
        width: pct(MS, VB_W),
        height: pct(MS, VB_H),
      }"
    />
    <svg class="fp-svg" :viewBox="`0 0 ${VB_W} ${VB_H}`" role="img" :aria-label="ariaLabel">
      <defs>
        <clipPath :id="`fp-clip-${uid}`">
          <rect :x="MX - 3" :y="MY - 3" :width="MS + 6" :height="MS + 6" />
        </clipPath>
        <linearGradient :id="`fp-cmap-${uid}`" x1="0" y1="1" x2="0" y2="0">
          <stop v-for="(c, i) in stops" :key="i" :offset="i / (stops.length - 1)" :stop-color="c" />
        </linearGradient>
      </defs>

      <!-- header: the name (latex) left; lake · model and the SI's panel title right -->
      <image
        :href="texSrc"
        :x="MX - 4"
        :y="TITLE_BASE - TITLE_H * (CH2_TEX_BOX.baseline / CH2_TEX_BOX.height)"
        :height="TITLE_H"
        width="420"
        preserveAspectRatio="xMinYMid meet"
      />
      <text class="fp-kicker" :x="MX + MS" y="54" text-anchor="end">LAKE {{ meta.num }} · {{ model.toUpperCase() }}</text>
      <text class="fp-case" :x="MX + MS" :y="TITLE_BASE" text-anchor="end">
        {{ caseLabel }}<tspan v-if="meanText" class="fp-mean" dx="14">{{ meanText }}</tspan>
      </text>

      <!-- lakes, tile, frame -->
      <g :clip-path="`url(#fp-clip-${uid})`">
        <polygon class="fp-tile" :points="tilePoints" />
        <template v-for="l in lakes" :key="l.num">
          <polyline
            v-for="(r, ri) in l.rings"
            :key="`u${ri}`"
            :points="r"
            fill="none"
            stroke="#000"
            :stroke-width="l.dash ? LW_DASH + 1.6 : LW + 1.6"
            :stroke-dasharray="l.dash ? DASH : undefined"
            stroke-linejoin="round"
          />
          <polyline
            v-for="(r, ri) in l.rings"
            :key="`o${ri}`"
            :points="r"
            fill="none"
            :stroke="l.color"
            :stroke-width="l.dash ? LW_DASH : LW"
            :stroke-dasharray="l.dash ? DASH : undefined"
            stroke-linejoin="round"
          />
        </template>
        <text
          v-for="l in lakes"
          :key="`t${l.num}`"
          class="fp-lake-num"
          :x="l.lx"
          :y="l.ly"
          :text-anchor="l.anchor"
          :fill="l.color"
          :stroke="l.halo"
        >{{ l.num }}</text>
      </g>
      <rect class="fp-frame" :x="MX" :y="MY" :width="MS" :height="MS" />

      <!-- axes -->
      <g class="fp-axis">
        <template v-for="t in xTicks" :key="`x${t.v}`">
          <line :x1="t.p" :x2="t.p" :y1="MY + MS" :y2="MY + MS + 8" />
          <text :x="t.p" :y="MY + MS + 32" text-anchor="middle">{{ t.label }}</text>
        </template>
        <template v-for="t in yTicks" :key="`y${t.v}`">
          <line :x1="MX - 8" :x2="MX" :y1="t.p" :y2="t.p" />
          <text :x="MX - 13" :y="t.p + 7" text-anchor="end">{{ t.label }}</text>
        </template>
      </g>
      <text class="fp-axis-title" :x="MX + MS / 2" :y="MY + MS + 70" text-anchor="middle">Easting [km]</text>
      <text
        class="fp-axis-title"
        :transform="`translate(17 ${MY + MS / 2}) rotate(-90)`"
        text-anchor="middle"
        dominant-baseline="central"
      >Northing [km]</text>

      <!-- colour bar (extend = both, as the SI) -->
      <g class="fp-cbar">
        <polygon :points="`${CBX},${CB0} ${CBX + CBW},${CB0} ${CBX + CBW / 2},${CB0 - EXT}`" :fill="stops[stops.length - 1]" />
        <polygon :points="`${CBX},${CB1} ${CBX + CBW},${CB1} ${CBX + CBW / 2},${CB1 + EXT}`" :fill="stops[0]" />
        <rect :x="CBX" :y="CB0" :width="CBW" :height="CB1 - CB0" :fill="`url(#fp-cmap-${uid})`" />
        <polygon
          class="fp-cbar-edge"
          :points="`${CBX + CBW / 2},${CB0 - EXT} ${CBX + CBW},${CB0} ${CBX + CBW},${CB1} ${CBX + CBW / 2},${CB1 + EXT} ${CBX},${CB1} ${CBX},${CB0}`"
        />
        <g class="fp-axis">
          <template v-for="t in cTicks" :key="`c${t.v}`">
            <line :x1="CBX + CBW" :x2="CBX + CBW + 7" :y1="t.p" :y2="t.p" />
            <text :x="CBX + CBW + 12" :y="t.p + 7">{{ t.label }}</text>
          </template>
        </g>
      </g>
      <text
        class="fp-axis-title"
        :transform="`translate(${VB_W - 14} ${(CB0 + CB1) / 2}) rotate(-90)`"
        text-anchor="middle"
        dominant-baseline="central"
      >
        <tspan
          v-for="(s, i) in cbarParts"
          :key="i"
          :font-style="s.italic ? 'italic' : undefined"
          :baseline-shift="s.sub ? 'sub' : undefined"
          :font-size="s.sub ? '0.72em' : undefined"
          :font-weight="s.bold ? 700 : undefined"
        >{{ s.text }}</tspan>
      </text>

      <!-- the run's parameters, as the SI captions give them -->
      <text class="fp-params" :x="MX" :y="VB_H - 16">
        <template v-if="model === 'viscous'">
          <tspan font-style="italic">c</tspan><tspan baseline-shift="sub" font-size="0.72em">b</tspan><tspan> = {{ meta.cb.toFixed(1) }} × 10</tspan><tspan baseline-shift="super" font-size="0.72em">6</tspan><tspan> Pa m</tspan><tspan baseline-shift="super" font-size="0.72em">−1/3</tspan><tspan> s</tspan><tspan baseline-shift="super" font-size="0.72em">1/3</tspan>
        </template>
        <template v-else>
          <tspan font-style="italic">E</tspan><tspan> = 3.077 GPa · </tspan><tspan font-style="italic">ν</tspan><tspan> = 0.3 · </tspan><tspan font-style="italic">P</tspan><tspan baseline-shift="sub" font-size="0.72em">w</tspan><tspan> = {{ meta.pw.toFixed(4) }} × overburden</tspan>
        </template>
      </text>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  CH2_CLASS_STYLE,
  CH2_TEX_BOX,
  ch2CaseLabel,
  ch2CbarLabel,
  ch2FieldCell,
  ch2TexSrc,
  type Ch2LakeMeta,
  type Ch2Model,
} from '../config/ch2Fields'
import { CH2_CMAPS } from '../config/ch2Fields.gen'

const props = defineProps<{
  meta: Ch2LakeMeta
  model: Ch2Model
  fieldKey: string
  /** The field raster (already decoded by the viewer). */
  src: string | null
  /** The panel title when it is not the SI's (the elastic σ cells —
   *  config/ch2Fields.ts ch2CellLabel). */
  label?: string
}>()

// ── layout (viewBox units) ──────────────────────────────────────────────
const VB_W = 1000
const MX = 128 // map left
const MY = 118 // map top
const MS = 700 // map side (the square E/N frame of the rotated tile)
const VB_H = MY + MS + 112
const TITLE_BASE = 94
const TITLE_H = 66
const CBX = 856
const CBW = 24
const CB0 = MY + 0.1 * MS // shrink 0.8, as the SI's colour bars
const CB1 = MY + 0.9 * MS
const EXT = 0.05 * (CB1 - CB0)
// The SI's outline weights (2.2 pt solid, 1.5 pt dashed, 1.2 pt dashes)
// on its 4.2-inch panel, in this viewBox.
const PT = MS / (4.2 * 72)
const LW = 2.2 * PT
const LW_DASH = 1.5 * PT
const DASH = `${(1.2 * 1.5 * PT).toFixed(2)} ${(1.2 * 1.5 * PT).toFixed(2)}`

// Unique ids for this instance's clip path and gradient (the viewer and
// its full-screen copy are on the page at once).
const uid = Math.random().toString(36).slice(2, 10)

function pct(v: number, of: number): string {
  return `${((v / of) * 100).toFixed(4)}%`
}
function fmt(v: number): string {
  const s = Math.abs(v - Math.round(v)) < 1e-6 ? String(Math.round(v)) : v.toFixed(1)
  return s.replace('-', '−')
}

const info = computed(() => props.meta.fields[props.model]?.[props.fieldKey] ?? null)
const texSrc = computed(() => ch2TexSrc(props.fieldKey))
const caseLabel = computed(() => props.label ?? ch2CaseLabel(props.fieldKey, props.model))
const ariaLabel = computed(() => `Lake ${props.meta.num}, ${props.model}, ${caseLabel.value}`)
const meanText = computed(() => {
  const { row } = ch2FieldCell(props.fieldKey)
  if (!info.value || (row !== 'u' && props.fieldKey !== 'obs')) return ''
  return `mean ${info.value.mean.toFixed(1)} m/yr`
})
const stops = computed(() => CH2_CMAPS[info.value?.cmap ?? 'seismic'])

const km = computed(() => MS / props.meta.size_km)
const toX = (x: number) => MX + x * km.value
const toY = (y: number) => MY + y * km.value

const tilePoints = computed(() => props.meta.tile.map(([x, y]) => `${toX(x).toFixed(1)},${toY(y).toFixed(1)}`).join(' '))

const lakes = computed(() =>
  props.meta.lakes.map((l) => {
    const st = CH2_CLASS_STYLE[l.cls]
    return {
      num: l.num,
      color: st.color,
      halo: st.halo,
      dash: st.dash,
      rings: l.rings.map((r) => r.map(([x, y]) => `${toX(x).toFixed(1)},${toY(y).toFixed(1)}`).join(' ')),
      lx: toX(l.label[0]),
      ly: toY(l.label[1]),
      anchor: l.label[2] ?? 'middle',
    }
  }),
)

const xTicks = computed(() => {
  const [e0, e1] = props.meta.extent_km
  return props.meta.xticks.map((v) => ({ v, p: MX + ((v - e0) / (e1 - e0)) * MS, label: fmt(v) }))
})
const yTicks = computed(() => {
  const [, , n0, n1] = props.meta.extent_km
  return props.meta.yticks.map((v) => ({ v, p: MY + ((n1 - v) / (n1 - n0)) * MS, label: fmt(v) }))
})
const cTicks = computed(() => {
  const f = info.value
  if (!f) return []
  return f.ticks.map((v) => ({ v, p: CB1 - ((v - f.vmin) / (f.vmax - f.vmin)) * (CB1 - CB0), label: fmt(v) }))
})

/** The colour-bar title's HTML (from config) as SVG tspans. */
const cbarParts = computed(() => {
  const html = ch2CbarLabel(props.fieldKey, info.value?.units ?? '')
  const parts: { text: string; italic?: boolean; sub?: boolean; bold?: boolean }[] = []
  const re = /<(i|sub|b)>(.*?)<\/\1>|([^<]+)/g
  let m: RegExpExecArray | null
  while ((m = re.exec(html))) {
    if (m[3]) parts.push({ text: m[3] })
    else if (m[1] === 'sub') {
      // a subscript may itself hold italics: flatten, keep it italic.
      const inner = m[2].replace(/<\/?i>/g, '')
      parts.push({ text: inner, sub: true, italic: /<i>/.test(m[2]) })
    } else parts.push({ text: m[2], italic: m[1] === 'i', bold: m[1] === 'b' })
  }
  return parts
})
</script>

<style scoped>
.fp {
  position: relative;
  width: 100%;
  background: #fff;
  user-select: none;
}
.fp-img {
  position: absolute;
  display: block;
  pointer-events: none;
}
.fp-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
  pointer-events: none;
}
.fp-kicker {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 17px;
  font-weight: 500;
  letter-spacing: 0.16em;
  fill: #8a8174;
}
.fp-case {
  font-family: 'EB Garamond', serif;
  font-size: 34px;
  fill: #1c1a17;
}
.fp-mean {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 20px;
  fill: #6b6458;
}
.fp-frame {
  fill: none;
  stroke: #1c1a17;
  stroke-width: 1.6;
}
.fp-tile {
  fill: none;
  stroke: #000;
  stroke-width: 3.4;
  stroke-linejoin: miter;
}
.fp-lake-num {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 23px;
  font-weight: 700;
  stroke-width: 7px;
  stroke-linejoin: round;
  paint-order: stroke;
}
.fp-axis line {
  stroke: #1c1a17;
  stroke-width: 1.5;
}
.fp-axis text {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 20px;
  fill: #1c1a17;
  font-variant-numeric: tabular-nums;
}
.fp-axis-title {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 22px;
  fill: #1c1a17;
}
.fp-cbar-edge {
  fill: none;
  stroke: #1c1a17;
  stroke-width: 1.2;
}
.fp-params {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 18px;
  fill: #6b6458;
}
</style>
