<template>
  <!-- The Introduction's "seasons" steps: the globe wears
       the month (the Globe recolours its speed drape — seasonDrape.ts), and
       this layer draws only FIGURE labels (the narrator rule): the Speed |
       Anomaly switch, the curve of the region the markers outline (on the anomaly step with
       one plot per step, three places), the timebar, the source link.
       One right-hand column, clear of the pills (top) and the corner link
       (bottom). -->
  <div class="seasons" :class="{ on: shown }">
    <!-- the three regions of the curve, outlined on the globe -->
    <svg class="sz-marks" :width="vw" :height="vh" aria-hidden="true">
      <g v-for="r in markRegions" :key="r.key" :class="['sz-mark', `sz-${r.key}`]">
        <polygon :ref="(el) => setRef(`${r.key}:box`, el)" class="sz-box-halo" />
        <polygon :ref="(el) => setRef(`${r.key}:box2`, el)" class="sz-box" :style="{ stroke: r.color }" />
        <polyline :ref="(el) => setRef(`${r.key}:lead`, el)" class="sz-lead" :style="{ stroke: r.color }" />
      </g>
    </svg>
    <div
      v-for="r in markRegions"
      :key="r.key"
      :ref="(el) => setRef(`${r.key}:label`, el)"
      class="sz-mark-label"
      :style="{ color: r.color }"
    >{{ r.label }}</div>

    <div class="sz-col">
      <div class="sz-toggle" role="group" aria-label="map">
        <button
          class="sz-pill"
          :class="{ active: view === 'speed' }"
          @click="$emit('view', 'speed')"
        >Speed</button>
        <button
          class="sz-pill"
          :class="{ active: view === 'anom' }"
          @click="$emit('view', 'anom')"
        >Anomaly</button>
      </div>

      <!-- The big month stamp and the "% observed" coverage bar are gone
           (the director found them unnecessarily large); the month rides
           small under the scrub bar instead, between the years. -->

      <!-- ONE plot per step (the director asked for the raw speed rather
           than a percent change by season, one plot with the three example
           locations on it, and on the anomaly step just the anomaly
           percentage time series — one plot per page, never two
           stacked): SPEED = the three places' monthly speed on a log
           axis (70 m/yr beside 1,400 m/yr); ANOMALY = the same three as
           percent vs each place's usual, in step with the drape. -->
      <div v-if="plot" class="sz-curve">
        <div class="sz-curve-title">
          <span class="sz-curve-name">{{ plot.title }}</span>
          <span class="sz-curve-kind">{{ plot.kind }}</span>
        </div>
        <svg :viewBox="`0 0 ${CW} ${CH}`" class="sz-svg" preserveAspectRatio="xMidYMid meet">
          <rect
            v-for="sm in plot.summers"
            :key="'s' + sm.x"
            class="sz-summer"
            :x="sm.x" :y="PAD.t" :width="sm.w" :height="CH - PAD.t - PAD.b"
          />
          <!-- meltwater runoff over the land sector's box: a quiet area BEHIND
               the anomaly lines, on its own right-hand axis (the director
               asked for it, and kept it on the one-plot card) -->
          <g v-if="melt" class="sz-melt" :class="{ on: meltOn }">
            <path class="sz-melt-area" :d="melt.area" />
            <path class="sz-melt-edge" :d="melt.edge" />
            <g class="sz-rlab">
              <text v-for="t in melt.ticks" :key="'r' + t.v" :x="CW - PAD.r + 7" :y="t.y + 5">{{ t.label }}</text>
            </g>
            <text class="sz-runit" :x="CW" :y="PAD.t - 16">mm w.e. mo<tspan dy="-7" font-size="14">−1</tspan></text>
          </g>
          <g class="sz-grid">
            <line v-for="t in plot.yTicks" :key="'y' + t.v" :x1="PAD.l" :x2="CW - PAD.r" :y1="t.y" :y2="t.y" :class="{ zero: t.zero }" />
          </g>
          <g class="sz-ylab">
            <text v-for="t in plot.yTicks" :key="'yl' + t.v" :x="PAD.l - 8" :y="t.y + 5">{{ t.label }}</text>
          </g>
          <text v-if="view === 'speed'" class="sz-yunit" :x="PAD.l - 8" :y="PAD.t - 16">m yr<tspan dy="-7" font-size="14">−1</tspan></text>
          <text v-else class="sz-yunit" :x="PAD.l - 8" :y="PAD.t - 16">%</text>
          <g class="sz-xlab">
            <text v-for="t in plot.xTicks" :key="'x' + t.label" :x="t.x" :y="CH - PAD.b + 22">{{ t.label }}</text>
          </g>
          <path
            v-for="l in plot.lines"
            :key="l.key"
            class="sz-pline"
            :class="{ main: l.main }"
            :d="l.path"
            :style="{ stroke: l.color }"
          />
          <g class="sz-cursor" :style="{ transform: `translateX(${cursorX}px)` }">
            <line :x1="0" :x2="0" :y1="PAD.t" :y2="CH - PAD.b" />
          </g>
          <circle
            v-if="melt && meltCursorY !== null"
            class="sz-melt-dot"
            :class="{ on: meltOn }"
            :cx="cursorX" :cy="meltCursorY" r="4.5"
          />
          <template v-for="c in cursors" :key="'c' + c.key">
            <circle class="sz-cursor-dot" :cx="cursorX" :cy="c.y" r="5" :style="{ fill: c.color }" />
            <text
              class="sz-readout"
              :x="cursorX + (flip ? -12 : 12)"
              :y="c.ty"
              :text-anchor="flip ? 'end' : 'start'"
              :style="{ fill: c.color }"
            >{{ c.text }}<tspan v-if="c.sup" dy="-7" font-size="14">−1</tspan></text>
          </template>
        </svg>
        <div class="sz-legend">
          <span v-for="l in plot.lines" :key="'lg' + l.key" class="sz-leg">
            <i :style="{ background: l.color, height: l.main ? '3px' : '2px' }"></i>{{ l.label }}
            <em>{{ l.kind }}</em>
          </span>
          <!-- The runoff legend item was unclear: the
               swatch had no height (invisible); now a filled turquoise box
               like the area, and the words say what and which axis -->
          <span v-if="melt" class="sz-leg sz-leg-melt" :class="{ on: meltOn }">
            <i class="sz-leg-area"></i>meltwater runoff
            <em>{{ melt.model }} · right axis</em>
          </span>
        </div>
      </div>

      <div class="sz-timebar">
        <button class="sz-play" :aria-label="seasonUi.playing ? 'pause' : 'play'" @click="togglePlay">
          <PlayPauseGlyph :playing="seasonUi.playing" :size="12" />
        </button>
        <div class="sz-range-wrap">
          <input
            type="range" min="0" :max="Math.max(1, nFrames - 1)" step="1"
            :value="Math.max(0, seasonUi.idx)"
            :style="{ '--fill': (100 * Math.max(0, seasonUi.idx) / Math.max(1, nFrames - 1)) + '%' }"
            @input="onScrub"
          />
          <div class="sz-range-years">
            <span>{{ firstYear }}</span>
            <span class="sz-range-stamp" aria-live="off">{{ stamp.month }} {{ stamp.year }}</span>
            <span>{{ lastYear }}</span>
          </div>
        </div>
      </div>
    </div>

    <router-link class="corner-link" :to="REFS_LINK">[monthly velocity from MEaSUREs NSIDC-0731 v5]</router-link>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { ComponentPublicInstance } from 'vue'
import PlayPauseGlyph from './PlayPauseGlyph.vue'
import { RUNOFF_VIEWS, SEASON_CURVE_REGIONS, seasonStamp } from '../config/seasons'
import { seasonGoto, seasonPlay, seasonUi } from './seasonClock'

const props = defineProps<{
  /** The map the globe wears: speed (step 2) or anomaly (step 3). */
  view: 'speed' | 'anom'
  /** False while the layer should be hidden (it fades). */
  visible: boolean
}>()
defineEmits<{ view: [value: 'speed' | 'anom'] }>()

const REFS_LINK = { path: '/references', query: { chapter: 'introduction' } }
const MAIN = 'russell_isunnguata'
/** Line colours: the land sector in gold, the two marine outlets cool. */
const REGION_COLOR: Record<string, string> = {
  russell_isunnguata: '#f4cf6a',
  sermeq_kujalleq: '#8fd6ff',
  petermann: '#d0b3ff',
}

// The layer rises in once mounted (the step-1 → 2 handover is quiet).
const mounted = ref(false)
const shown = computed(() => props.visible && mounted.value)

const vw = ref(window.innerWidth)
const vh = ref(window.innerHeight)
function onResize(): void {
  vw.value = window.innerWidth
  vh.value = window.innerHeight
}

const nFrames = computed(() => seasonUi.manifest?.frames.length ?? 0)
const frame = computed(() => {
  const m = seasonUi.manifest
  if (!m) return null
  return m.frames[Math.max(0, seasonUi.idx >= 0 ? seasonUi.idx : seasonUi.startIdx)]
})
const stamp = computed(() => (frame.value ? seasonStamp(frame.value.ym) : { month: '', year: '' }))
const firstYear = computed(() => seasonUi.manifest?.frames[0]?.ym.slice(0, 4) ?? '')
const lastYear = computed(() => {
  const f = seasonUi.manifest?.frames
  return f?.length ? f[f.length - 1].ym.slice(0, 4) : ''
})

// ── the plot ──────────────────────────────────────────────────────────
const CW = 560
const CH = 320
// r: room for the runoff's right-hand axis (the anomaly step)
const PAD = { l: 64, r: 44, t: 36, b: 30 }
/** The runoff area's tallest month reaches this fraction of the plot. */
const MELT_FRAC = 0.62

function monthX(i: number, n: number): number {
  return PAD.l + ((i + 0.5) / n) * (CW - PAD.l - PAD.r)
}
function fmtSpeed(v: number): string {
  return Math.round(v).toLocaleString('en-US')
}
function fmtPct(v: number): string {
  const r = Math.round(v)
  return r > 0 ? `+${r} %` : r < 0 ? `−${-r} %` : '0 %'
}

type Line = { key: string; label: string; kind: string; color: string; main: boolean; path: string; yOf: (v: number) => number; vals: (number | null)[] }

const plot = computed(() => {
  const m = seasonUi.manifest
  if (!m) return null
  const months = m.region_months
  const n = months.length
  const keys = SEASON_CURVE_REGIONS.filter((k) => m.regions[k])
  if (!keys.length) return null
  // Summers (Jun–Aug) shaded; July ticks labelled every other year.
  const colW = (CW - PAD.l - PAD.r) / n
  const summers: { x: number; w: number }[] = []
  const xTicks: { x: number; label: string }[] = []
  months.forEach((ym, i) => {
    const mo = parseInt(ym.slice(5, 7), 10)
    if (mo === 6) summers.push({ x: monthX(i, n) - colW / 2, w: colW * 3 })
    const yr = parseInt(ym.slice(0, 4), 10)
    if (mo === 7 && yr % 2 === 0) xTicks.push({ x: monthX(i, n), label: String(yr) })
  })
  const H = CH - PAD.t - PAD.b
  const meta = (k: string, yOf: (v: number) => number, vals: (number | null)[]): Line => {
    const r = m.regions[k]
    let d = ''
    let pen = false
    vals.forEach((v, i) => {
      if (v == null) {
        pen = false
        return
      }
      d += `${pen ? 'L' : 'M'}${monthX(i, n).toFixed(1)},${yOf(v).toFixed(1)}`
      pen = true
    })
    return {
      key: k,
      label: k === MAIN ? 'Russell / Isunnguata' : r.label,
      kind: r.kind === 'land' ? 'land' : 'marine',
      color: REGION_COLOR[k],
      main: k === MAIN,
      path: d,
      yOf,
      vals,
    }
  }
  let yTicks: { v: number; y: number; label: string; zero: boolean }[]
  let lines: Line[]
  if (props.view === 'speed') {
    // A log axis: a land-terminating sector at ~100 m/yr beside two
    // outlets at ~1,000 on one plot, each with its own seasonal swing.
    const all = keys.flatMap((k) => m.regions[k].speed)
    const lo = Math.log10(Math.min(...all)) - 0.06
    const hi = Math.log10(Math.max(...all)) + 0.06
    const yOf = (v: number) => PAD.t + (1 - (Math.log10(v) - lo) / (hi - lo)) * H
    yTicks = []
    for (let e = 0; e <= 5; e++) {
      for (const mant of [1, 2, 5]) {
        const v = mant * 10 ** e
        const lv = Math.log10(v)
        if (lv >= lo && lv <= hi) yTicks.push({ v, y: yOf(v), label: fmtSpeed(v), zero: false })
      }
    }
    lines = keys.map((k) => meta(k, yOf, m.regions[k].speed))
  } else {
    // Percent vs each place's own 12-month running median.
    const all = keys.flatMap((k) => (m.regions[k].anomaly_pct ?? []).filter((v): v is number => v != null))
    const plo = Math.floor(Math.min(-20, ...all) / 20) * 20
    const phi = Math.ceil(Math.max(40, ...all) / 20) * 20
    const yOf = (v: number) => PAD.t + (1 - (v - plo) / (phi - plo)) * H
    yTicks = []
    for (let v = plo; v <= phi; v += 20) yTicks.push({ v, y: yOf(v), label: v > 0 ? `+${v}` : v < 0 ? `−${-v}` : '0', zero: v === 0 })
    lines = keys.map((k) => meta(k, yOf, m.regions[k].anomaly_pct))
  }
  return {
    title: props.view === 'speed' ? 'Surface speed' : 'Speed vs usual',
    kind: 'three places',
    summers,
    xTicks,
    yTicks,
    lines,
    n,
  }
})

const frameIdx = computed(() => Math.max(0, seasonUi.idx >= 0 ? seasonUi.idx : seasonUi.startIdx))
const cursorX = computed(() => (plot.value ? monthX(frameIdx.value, plot.value.n) : PAD.l))
const flip = computed(() => cursorX.value > CW - 150)
/** One dot + readout per line at the month shown; readouts pushed apart
 *  (18 px) when two lines run close. */
const cursors = computed(() => {
  const p = plot.value
  if (!p) return []
  const i = frameIdx.value
  const out = p.lines
    .map((l) => {
      const v = l.vals[i]
      if (v == null) return null
      return {
        key: l.key,
        color: l.color,
        y: l.yOf(v),
        ty: l.yOf(v) - 10,
        text: props.view === 'speed' ? `${fmtSpeed(v)} m yr` : fmtPct(v),
        sup: props.view === 'speed',
      }
    })
    .filter((c): c is NonNullable<typeof c> => !!c)
    .sort((a, b) => a.ty - b.ty)
  for (let k = 1; k < out.length; k++) {
    if (out[k].ty - out[k - 1].ty < 18) out[k].ty = out[k - 1].ty + 18
  }
  for (const c of out) c.ty = Math.max(PAD.t + 14, c.ty)
  return out
})

// ── meltwater runoff behind the anomaly lines (the director asked for it back after a trim) ───────────────────────────
// Monthly runoff over the land sector's box (RACMO2.3p2, mm w.e. per month,
// config/seasons.ts): an area from the plot floor up to MELT_FRAC of its
// height, scaled on its own right-hand axis. Months without runoff data
// (after Dec 2023) draw nothing.
const meltOn = computed(() => RUNOFF_VIEWS.includes(props.view))
const melt = computed(() => {
  const m = seasonUi.manifest
  const r = seasonUi.runoff
  const c = plot.value
  const reg = r?.regions[MAIN]
  if (!m || !r || !c || !reg) return null
  const at = new Map(r.months.map((ym, j) => [ym, j]))
  const vals = m.region_months.map((ym) => {
    const j = at.get(ym)
    return j === undefined ? null : reg.runoff_mm[j]
  })
  const vmax = Math.max(0, ...vals.filter((v): v is number => v !== null))
  if (!(vmax > 0)) return null
  const step = [100, 200, 250, 500, 1000].find((s) => vmax / s <= 3.2) ?? 2000
  const top = Math.ceil(vmax / step) * step
  const base = CH - PAD.b
  const zone = (CH - PAD.t - PAD.b) * MELT_FRAC
  const yOf = (v: number) => base - (v / top) * zone
  // Only the humps: a month is drawn when it or a neighbour has runoff, so
  // no line runs along the floor through the winters.
  const drawn = vals.map(
    (v, i) =>
      v !== null && ((v ?? 0) > 0 || (vals[i - 1] ?? 0) > 0 || (vals[i + 1] ?? 0) > 0),
  )
  let area = ''
  let edge = ''
  let run: [number, number][] = []
  const flush = () => {
    if (run.length > 1) {
      const pts = run.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`)
      edge += `M${pts.join('L')}`
      area += `M${run[0][0].toFixed(1)},${base}L${pts.join('L')}L${run[run.length - 1][0].toFixed(1)},${base}Z`
    }
    run = []
  }
  vals.forEach((v, i) => {
    if (!drawn[i] || v === null) return flush()
    run.push([monthX(i, c.n), yOf(v)])
  })
  flush()
  const ticks: { v: number; y: number; label: string }[] = []
  for (let v = step; v <= top; v += step) ticks.push({ v, y: yOf(v), label: String(v) })
  return { area, edge, ticks, vals, yOf, label: r.label, model: r.model }
})
const meltCursorY = computed(() => {
  const mt = melt.value
  if (!mt) return null
  const i = frameIdx.value
  const v = mt.vals[i]
  return v === null || v === undefined ? null : mt.yOf(v)
})

// ── the clock controls ────────────────────────────────────────────────
function togglePlay(): void {
  seasonPlay(!seasonUi.playing)
}
function onScrub(e: Event): void {
  if (seasonUi.playing) seasonPlay(false)
  void seasonGoto(parseInt((e.target as HTMLInputElement).value, 10), 60)
}

// ── the region markers (projected every frame by the Globe) ──────────
const markRegions = computed(() => {
  const m = seasonUi.manifest
  if (!m) return []
  return SEASON_CURVE_REGIONS.filter((k) => m.regions[k]).map((k) => ({
    key: k,
    label: k === MAIN ? 'Russell / Isunnguata Sermia' : m.regions[k].label,
    color: REGION_COLOR[k],
  }))
})
const els = new Map<string, Element>()
function setRef(key: string, el: Element | ComponentPublicInstance | null): void {
  if (el instanceof Element) els.set(key, el)
  else els.delete(key)
}
type Scr = { x: number; y: number; visible: boolean }
let raf: number | null = null
const MIN_BOX_PX = 7
function drawMarks(): void {
  raf = window.requestAnimationFrame(drawMarks)
  const scr = (window as any).__globeAnchorScreens as Record<string, Scr> | null
  for (const r of markRegions.value) {
    const pts: Scr[] = []
    for (let i = 0; i < 4; i++) {
      const p = scr?.[`sz:${r.key}:${i}`]
      if (p) pts.push(p)
    }
    const lab = els.get(`${r.key}:label`) as HTMLElement | undefined
    const on =
      pts.length === 4 &&
      pts.every((p) => p.visible && p.x > 0 && p.x < vw.value && p.y > 0 && p.y < vh.value)
    if (!on) {
      for (const s of ['box', 'box2', 'lead']) els.get(`${r.key}:${s}`)?.setAttribute('visibility', 'hidden')
      if (lab) lab.style.visibility = 'hidden'
      continue
    }
    // Small boxes (whole-sheet view) are drawn at least MIN_BOX_PX across,
    // about their centre, so the outline reads as a marker.
    const cx = pts.reduce((a, p) => a + p.x, 0) / 4
    const cy = pts.reduce((a, p) => a + p.y, 0) / 4
    const span = Math.max(...pts.map((p) => Math.hypot(p.x - cx, p.y - cy)))
    const k = span < MIN_BOX_PX ? MIN_BOX_PX / Math.max(span, 0.5) : 1
    const str = pts.map((p) => `${(cx + (p.x - cx) * k).toFixed(1)},${(cy + (p.y - cy) * k).toFixed(1)}`).join(' ')
    for (const s of ['box', 'box2']) {
      const el = els.get(`${r.key}:${s}`)
      el?.setAttribute('points', str)
      el?.setAttribute('visibility', 'visible')
    }
    // Label to the WEST (screen left) of the box — over the tundra / the
    // sea, never over the ice the curve is about — with a short leader.
    if (lab) {
      const w = lab.offsetWidth
      const h = lab.offsetHeight
      const left = Math.min(...pts.map((p) => cx + (p.x - cx) * k))
      const lx = left - 26 - w
      const ly = cy - h / 2
      lab.style.transform = `translate(${lx.toFixed(1)}px, ${ly.toFixed(1)}px)`
      lab.style.visibility = 'visible'
      const lead = els.get(`${r.key}:lead`)
      lead?.setAttribute('points', `${(lx + w + 4).toFixed(1)},${cy.toFixed(1)} ${(left - 3).toFixed(1)},${cy.toFixed(1)}`)
      lead?.setAttribute('visibility', 'visible')
    }
  }
}

onMounted(() => {
  window.addEventListener('resize', onResize)
  raf = window.requestAnimationFrame(drawMarks)
  window.requestAnimationFrame(() => {
    mounted.value = true
  })
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  if (raf !== null) window.cancelAnimationFrame(raf)
})
</script>

<style scoped>
.seasons {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 7;
  color: #f2efe6;
  font-family: 'Inter', system-ui, sans-serif;
}

/* ── markers ── */
.sz-marks {
  position: absolute;
  inset: 0;
  overflow: visible;
  opacity: 0;
  transition: opacity 0.8s ease 0.4s;
}
.seasons.on .sz-marks {
  opacity: 1;
}
.sz-box-halo {
  fill: none;
  stroke: rgba(0, 0, 0, 0.75);
  stroke-width: 4.5;
  stroke-linejoin: round;
}
.sz-box {
  fill: none;
  stroke-width: 2;
  stroke-linejoin: round;
}
.sz-lead {
  fill: none;
  stroke-width: 2.2;
  opacity: 1;
}
.sz-mark-label {
  position: absolute;
  left: 0;
  top: 0;
  visibility: hidden;
  font-size: clamp(0.95rem, 1.15vw, 1.3rem);
  font-weight: 600;
  letter-spacing: 0.02em;
  white-space: nowrap;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.95), 0 0 10px rgba(0, 0, 0, 0.8);
  opacity: 0;
  transition: opacity 0.8s ease 0.4s;
  will-change: transform;
}
.seasons.on .sz-mark-label {
  opacity: 1;
}

/* ── the right-hand column ── */
.sz-col {
  position: absolute;
  right: 2vw;
  top: calc(1.2vh + 3.6rem);
  /* the director asked for the time-series card a little bigger */
  width: clamp(380px, 34.5vw, 660px);
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: clamp(8px, 1.3vh, 16px);
  opacity: 0;
  transform: translateY(14px);
  transition: opacity 0.7s ease 0.2s, transform 0.9s cubic-bezier(0.2, 0.7, 0.2, 1) 0.2s;
}
.seasons.on .sz-col {
  opacity: 1;
  transform: none;
}
@media (max-width: 1840px) {
  .sz-col { top: calc(6.2vh + 3rem); }
}

.sz-toggle {
  display: flex;
  gap: 0.5rem;
  align-self: flex-end;
}
.sz-pill {
  pointer-events: auto;
  border: 1px solid var(--gold);
  background: rgba(8, 6, 4, 0.78);
  color: var(--gold-bright);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1rem;
  font-weight: 500;
  letter-spacing: 0.06em;
  padding: 0.45rem 1.1rem;
  border-radius: 999px;
  cursor: pointer;
  white-space: nowrap;
  backdrop-filter: blur(8px);
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.55), 0 0 22px rgba(245, 199, 94, 0.18);
  transition: color 0.2s, background 0.2s, box-shadow 0.2s;
}
.sz-pill:hover {
  color: #fff8d8;
  background: rgba(56, 38, 12, 0.85);
}
.sz-pill.active {
  color: #1c1305;
  background: var(--gold);
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.55), 0 0 30px rgba(245, 199, 94, 0.45);
}

.sz-curve {
  padding: clamp(8px, 1.1vh, 14px) clamp(10px, 0.9vw, 16px) clamp(6px, 0.8vh, 10px);
  border-radius: 10px;
  background: rgba(8, 7, 6, 0.72);
  border: 1px solid rgba(245, 199, 94, 0.32);
  backdrop-filter: blur(6px);
}
.sz-curve-title {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  margin-bottom: 0.1rem;
}
.sz-curve-name {
  font-family: 'EB Garamond', Georgia, serif;
  font-size: clamp(1.15rem, 1.45vw, 1.7rem);
  color: var(--gold-bright);
}
.sz-curve-kind {
  font-size: clamp(0.9rem, 1vw, 1.1rem);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(242, 239, 230, 0.85);
}
.sz-svg {
  display: block;
  width: 100%;
  height: auto;
  overflow: visible;
}
.sz-summer {
  fill: rgba(255, 214, 120, 0.11);
}
.sz-grid line {
  stroke: rgba(255, 255, 255, 0.16);
  stroke-width: 1.2;
}
.sz-grid line.zero {
  stroke: rgba(255, 255, 255, 0.55);
  stroke-width: 1.6;
}
.sz-ylab text,
.sz-yunit {
  fill: rgba(242, 239, 230, 0.95);
  font-size: 20px;
  text-anchor: end;
  font-variant-numeric: tabular-nums;
}
.sz-xlab text {
  fill: rgba(242, 239, 230, 0.95);
  font-size: 20px;
  text-anchor: middle;
}
.sz-melt,
.sz-melt-dot,
.sz-leg-melt {
  opacity: 0;
  transition: opacity 0.7s ease;
}
/* meltwater runoff: a glacial-meltwater turquoise, quiet, behind the gold
   (validated against the gold and Jakobshavn's blue: ΔE 17 normal, 15 CVD) */
.sz-melt,
.sz-melt-dot,
.sz-leg-melt {
  opacity: 0;
  transition: opacity 0.7s ease;
}
.sz-melt.on,
.sz-melt-dot.on,
.sz-leg-melt.on {
  opacity: 1;
}
.sz-melt-area {
  fill: #2fb5a3;
  fill-opacity: 0.3;
}
/* the legend's swatch: the area's fill under its edge, a box not a line */
.sz-leg-area {
  height: 0.8rem;
  background: rgba(47, 181, 163, 0.42);
  border: 1.5px solid #2fb5a3;
  box-sizing: border-box;
}
.sz-melt-edge {
  fill: none;
  stroke: #4fd1bd;
  stroke-width: 2;
  stroke-opacity: 1;
  stroke-linejoin: round;
}
.sz-rlab text,
.sz-runit {
  fill: rgba(160, 226, 214, 0.95);
  font-size: 20px;
  font-variant-numeric: tabular-nums;
}
.sz-rlab text {
  text-anchor: start;
}
.sz-runit {
  text-anchor: end;
}
.sz-melt-dot {
  fill: #7fe6d4;
  stroke: #0b0a08;
  stroke-width: 1.5;
}
.sz-pline {
  fill: none;
  stroke-width: 2;
  stroke-linejoin: round;
  opacity: 0.9;
}
.sz-pline.main {
  stroke-width: 2.8;
  opacity: 1;
}
.sz-cursor {
  transition: transform 0.15s linear;
}
.sz-cursor line {
  stroke: rgba(255, 255, 255, 0.9);
  stroke-width: 2;
}
.sz-cursor-dot {
  fill: #fff6d6;
  stroke: #1c1305;
  stroke-width: 2;
}
.sz-readout {
  fill: #fff6d6;
  font-size: 21px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  paint-order: stroke;
  stroke: rgba(8, 7, 6, 0.9);
  stroke-width: 4px;
}
.sz-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 1rem;
  margin-top: 0.35rem;
  font-size: clamp(0.9rem, 1.05vw, 1.15rem);
  color: rgba(242, 239, 230, 0.95);
}
.sz-leg {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  white-space: nowrap;
}
.sz-leg i {
  display: inline-block;
  width: 1.4rem;
  border-radius: 2px;
}
.sz-leg em {
  font-style: normal;
  font-size: 0.85em;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgba(242, 239, 230, 0.78);
}

/* the timebar — Chapter 3's season pill */
.sz-timebar {
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.5rem 1rem;
  border-radius: 999px;
  background: rgba(8, 7, 6, 0.84);
  border: 1px solid rgba(245, 199, 94, 0.4);
  backdrop-filter: blur(8px);
}
.sz-play {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  padding: 0;
  border-radius: 50%;
  border: 1px solid var(--gold);
  background: rgba(56, 38, 12, 0.5);
  color: var(--gold-bright);
  cursor: pointer;
}
.sz-range-wrap {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
/* Same scrub bar as the label demo's: an explicit gold-filled track, so
   Safari (which only honours accent-color on the thumb) matches Chrome. */
.sz-range-wrap input[type='range'] {
  width: 100%;
  -webkit-appearance: none;
  appearance: none;
  height: 20px;
  margin: 0;
  background: transparent;
  cursor: pointer;
}
.sz-range-wrap input[type='range']:focus { outline: none; }
.sz-range-wrap input[type='range']::-webkit-slider-runnable-track {
  height: 5px;
  border-radius: 3px;
  background: linear-gradient(to right,
    var(--gold) 0, var(--gold) var(--fill),
    rgba(245, 240, 230, 0.3) var(--fill), rgba(245, 240, 230, 0.3) 100%);
}
.sz-range-wrap input[type='range']::-moz-range-track { height: 5px; border-radius: 3px; background: rgba(245, 240, 230, 0.3); }
.sz-range-wrap input[type='range']::-moz-range-progress { height: 5px; border-radius: 3px; background: var(--gold); }
.sz-range-wrap input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  margin-top: -5.5px;
  border-radius: 50%;
  background: var(--gold-bright);
  border: 2px solid #0d0b09;
}
.sz-range-wrap input[type='range']::-moz-range-thumb {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--gold-bright);
  border: 2px solid #0d0b09;
}
.sz-range-years {
  display: flex;
  justify-content: space-between;
  font-size: 0.95rem;
  color: rgba(242, 239, 230, 0.88);
  font-variant-numeric: tabular-nums;
}
.sz-range-stamp {
  color: var(--gold-bright);
  font-weight: 600;
  letter-spacing: 0.03em;
}

.corner-link {
  position: absolute;
  right: 2vw;
  bottom: 2.2vh;
  pointer-events: auto;
  font-size: 1.05rem;
  letter-spacing: 0.04em;
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px dotted rgba(108, 204, 255, 0.4);
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.8);
  opacity: 0;
  transition: opacity 0.6s ease 0.3s;
}
.seasons.on .corner-link {
  opacity: 1;
}
.corner-link:hover {
  color: #fff;
  border-bottom-color: rgba(255, 255, 255, 0.7);
}
</style>
