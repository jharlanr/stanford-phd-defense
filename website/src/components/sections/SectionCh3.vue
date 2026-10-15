<template>
  <!-- Ch.3 (ESSD) — built to the director's brief.
       Globe-native like chapters 1–2: the root is transparent, the
       live Globe is the ground, and the chapter drives it through emits
       (camera, exag, hillshade, the five featured lakes, the lake strip).
       Beats:
         0  Fig. 4b live — Ch.1's opening view, the five drainage-class
            lakes, each joined to a callout panel stepping its Sentinel-2
            season on the shared clock (EssdLakePanels)
         1  Fig. 1 live — the dome flattens and the camera dives to a
            nadir map of the central-west strip; all N labeled lakes
            paint in, area ∝ p_water, the season ticking
         2  a label made live — the lakelabel procedure on the moulin
            example (EssdLabelDemo; nothing saved)
         3  Fig. 6 — the three labelers' pairwise confusion matrices
         4  the same, the HF–MD and MD–LD blocks outlined
         5…20 the network: the architecture as a road map, then one block
              of the forward pass per beat, any of the five lakes (EssdNetwork);
              the class head twice (stopped at epoch 0, then training plays),
              then once more in the four-class taxonomy (its training plays)
         21…26 training (EssdTraining) — the five-class run plays, NEXT
              rolls back to its best + TEST, the hard pairs, the four-class
              run plays, NEXT rolls back to its best + TEST; the two
              five-class beats carry the door to the Terminal-Bench task
              (TbsDoorPill)
         26 implications: RATE → MECHANISM + the takeaway (Ch3Implications)
         27 takeaway: the same page dimmed, the takeaway popped into a
            centred card (Explore's TakeawayPop)
       (config/ch3Beats.ts is the truth for these numbers)
       Beats 0 and 1 share ONE season clock + the bottom timebar: under
       the callouts it steps two a second through the dates some lake was
       imaged on, one day per second on the map, and the day
       carries across the dive. -->
  <div class="ch3-root" :class="{ 'ch3-root-panel': beat >= LABEL_BEAT }">
    <!-- ── beat 0: the five example lakes, each with its season ──
         Stays MOUNTED (hidden) through beat 1 so coming back never
         re-creates five <video>s (a 700 ms task, measured on film). -->
    <EssdLakePanels
      v-if="beat <= MAP_BEAT"
      :lakes="panelLakes"
      :globe-hover-id="globeHoverId ?? null"
      :globe-click="globeClick ?? null"
      :opacity="panelsOpacity"
      :day="day"
      :t0="T0"
      @hover="$emit('lake-hover', $event)"
      @clock="clockDays = $event"
      @ready="panelsReady = $event"
    />

    <!-- ── beat 1: the labeled population on the map ── -->
    <div v-if="beat === MAP_BEAT" class="ch3-legend" :style="{ opacity: mapUiOpacity }">
      <div class="ch3-leg-title">
        <span class="ch3-leg-n">{{ total }}</span> labeled lakes · {{ year }}
      </div>
      <!-- click a class: the map shows only it; click it again (or
           double-click any row) for all five -->
      <button
        v-for="c in classRows"
        :key="c.code"
        class="ch3-leg-row"
        :class="{ 'ch3-leg-on': soloClass === c.code, 'ch3-leg-off': soloClass !== null && soloClass !== c.code }"
        :style="{ '--acc': c.color }"
        :aria-pressed="soloClass === c.code"
        @click="toggleSolo(c.code)"
        @dblclick="soloClass = null"
      >
        <span class="ch3-leg-chip" :style="{ background: c.color }" />
        <span class="ch3-leg-code">{{ c.code }}</span>
        <span class="ch3-leg-name">{{ c.name }}</span>
        <span class="ch3-leg-count">{{ c.count }}</span>
      </button>
      <!-- the paper's Fig. 1 pies: the per-class population per year;
           each pie is the year toggle -->
      <div class="ch3-pies">
        <button
          v-for="pie in pies"
          :key="pie.year"
          class="ch3-pie"
          :class="{ 'ch3-pie-on': pie.year === year }"
          @click="setYear(pie.year)"
        >
          <svg viewBox="-115 -115 230 230">
            <path v-for="s in pie.slices" :key="s.code" :d="s.d" :fill="s.color" />
            <text
              v-for="s in pie.slices"
              :key="`t-${s.code}`"
              :x="s.lx" :y="s.ly"
              class="ch3-pie-lbl"
              text-anchor="middle"
            >{{ s.pct }}</text>
          </svg>
          <span class="ch3-pie-cap">{{ pie.year }} · n = {{ pie.n }}</span>
        </button>
      </div>
    </div>

    <router-link
      v-if="beat === MAP_BEAT"
      class="corner-link"
      :style="{ opacity: mapUiOpacity }"
      :to="REFS_LINK"
    >[lake locations from Dunmire 2021, 2025]</router-link>

    <!-- ── the season timebar (beats 0 and 1) ── -->
    <div v-if="beat <= MAP_BEAT" class="ch3-season" :style="{ opacity: seasonUiOpacity }">
      <button class="ch3-play" :aria-label="playing ? 'pause' : 'play'" @click="playing = !playing">
        <PlayPauseGlyph :playing="playing" :size="12" />
      </button>
      <input
        type="range" min="0" :max="Math.max(1, days - 1)" step="1"
        :value="day"
        @input="onScrub"
      />
      <span class="ch3-date">{{ dateLabel }}</span>
    </div>

    <!-- ── beat 2: a label made live ── -->
    <EssdLabelDemo v-if="beat === LABEL_BEAT" lake-id="CW2019_1848" />

    <!-- ── inter-rater agreement: the matrices, then the same matrices
         with HF–MD and MD–LD outlined (one instance across both beats) ── -->
    <EssdIrrMatrices v-else-if="isIrr" :step="beat - IRR_BEAT" />

    <!-- ── the training segment: curves + confusion matrices ── -->
    <EssdTraining
      v-else-if="ch3At(beat)?.id === 'training'"
      :step="beat - ch3First('training')"
    />

    <!-- ── implications: the same lakes by rate and by mechanism ──
         (its ribbons roll out 3 s in, or on the first NEXT — see next()) -->
    <Ch3Implications
      v-else-if="ch3IsImplicationsStage(beat)"
      ref="implRef"
      :settled="beat === TAKEAWAY_BEAT"
    />

    <!-- ── the network: architecture, forward pass, five lakes ──
         A taxonomy change re-mounts it; the old one fades out over the
         new (onNetLeave) so the swap on the NEXT path never dips to the
         globe. Leaving the segment is instant, as the beats above. -->
    <Transition :css="false" @leave="onNetLeave">
      <EssdNetwork
        v-if="isWalkthrough"
        :key="taxonomy"
        :stage="wtStage"
        :taxonomy="taxonomy"
        :lake="netLake"
        :play-head="netPlayHead"
        @goto-stage="gotoWtStage"
        @set-taxonomy="setTaxonomy"
        @lake="netLake = $event"
      />
    </Transition>

    <!-- the label beat's door to "Label lakes yourself" (the director
         asked for a proper, good-looking button bottom-right, not just a
         link) — a route out of the chapter -->
    <MakeLabelsPill v-if="beat === LABEL_BEAT" class="ch3-mklabels" />

    <!-- the five-class results' door to the Terminal-Bench task (the
         director asked for a button in the results part of the chapter,
         on the five-class results, linking to the Terminal-Bench
         task) — bottom-right, beside the epoch clock -->
    <TbsDoorPill v-if="beat === TRAIN_FIRST || beat === TRAIN_FIRST + 1" class="ch3-tbsdoor" />

    <!-- the implications figure's rate classes, credited like the map's -->
    <router-link
      v-if="ch3IsImplicationsStage(beat)"
      class="corner-link"
      :to="REFS_LINK"
    >[rate classes from Dunmire 2025]</router-link>
  </div>
</template>

<script lang="ts">
// Module scope: what the chapter's opening needs, warmed from Chapter 2's
// last beats (Explore.vue calls warmCh3Openers once the population beat
// is reached). Beat 0 shows five <video>s and waits for a decoded frame
// of EVERY one before the panels appear — 26 MB of movies that, cold,
// put the panels up ~5.5 s after the press (measured in a performance walk). A
// plain (no-cors) fetch is the <video> element's own request mode, so
// the entry it leaves in the HTTP cache is the one the element reads
// (config/media.ts warmPlain).
import { mediaUrl as mediaUrlOf, warmPlain } from '../../config/media'

/** The five ESSD Fig. 4 lakes of beat 0, in panel order (the ids
 *  panelLakes below carries, kept here so the warm-up shares them). */
export const CH3_PANEL_LAKE_IDS = ['CW2019_1597', 'CW2019_1907', 'CW2019_1848', 'CW2019_1889', 'CW2019_2330'] as const

let openersWarmed = false
export function warmCh3Openers(): void {
  if (openersWarmed) return
  openersWarmed = true
  for (const id of CH3_PANEL_LAKE_IDS) {
    warmPlain(mediaUrlOf(`ch03/lakes_valid/${id}.mp4`))
    fetch(mediaUrlOf(`ch03/lakes_valid/${id}.json`)).catch(() => {})
  }
  fetch(mediaUrlOf('ch03/essd_stats.json')).catch(() => {})
}
</script>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { CH3_BEATS, ch3At, ch3Count, ch3First, ch3IsImplicationsStage } from '../../config/ch3Beats'
import { useRoute, useRouter } from 'vue-router'
import EssdLakePanels, { type PanelLake } from '../EssdLakePanels.vue'
import EssdLabelDemo from '../EssdLabelDemo.vue'
import MakeLabelsPill from '../MakeLabelsPill.vue'
import EssdIrrMatrices from '../EssdIrrMatrices.vue'
import EssdNetwork from '../EssdNetwork.vue'
import EssdTraining from '../EssdTraining.vue'
import TbsDoorPill from '../TbsDoorPill.vue'
import Ch3Implications from '../Ch3Implications.vue'
import PlayPauseGlyph from '../PlayPauseGlyph.vue'
import { mediaUrl } from '../../config/media'
import type { Taxonomy } from '../../config/essdNetwork'
import { warmNetworkOpeners } from '../../config/essdNetworkPool'
import { parseBeatParam } from '../../config/sitePath'

const props = defineProps<{
  advanceTrigger?: number
  backTrigger?: number
  /** A sub-menu landmark jump (config/landmarks.ts): land on `beat` the
   *  way a `?beat=` deep link does. `seq` bumps per click. */
  jumpTo?: { beat: number; seq: number } | null
  /** Lake under the pointer on the globe (Globe → Explore → here). */
  globeHoverId?: string | null
  /** Lake clicked on the globe, {id, seq}. */
  globeClick?: { id: string; seq: number } | null
}>()

const route = useRoute()
const router = useRouter()

const emit = defineEmits<{
  advance: []
  'beat-change': [value: number, isLast: boolean]
  /** Same Globe levers Ch.1 uses (Explore fans them out). */
  'chapter-focus': [
    | {
        lat: number
        lon: number
        cameraLat?: number
        cameraLon?: number
        distance?: number
        fovDeg?: number
        durationMs?: number
        upNorth?: boolean
      }
    | null,
  ]
  'lake-polygons': [
    | { dataUrl: string; opacity?: number; featured?: boolean }
    | null,
  ]
  'globe-clicks': [value: number]
  'chapter-exag': [value: number | null]
  'chapter-exag-ms': [value: number]
  hillshade: [value: number | null]
  'lake-strip': [
    | {
        canvas: HTMLCanvasElement
        lonW: number
        lonE: number
        latS: number
        latN: number
        opacity: number
        version: number
      }
    | null,
  ]
  /** Pointer over a beat-0 panel → Explore pulses that lake on the globe. */
  'lake-hover': [id: string | null]
}>()

// ── beat map ──────────────────────────────────────────────────────────
// Order and counts live in config/ch3Beats.ts — change them THERE.
const MAP_BEAT = ch3First('map')
const LABEL_BEAT = ch3First('label')
const IRR_BEAT = ch3First('irr')
const WT_FIRST = ch3First('network')
/** The lake EssdNetwork opens on (its DEFAULT_LAKE). */
const NET_OPENING_LAKE = 'CW2019_1848'
const TRAIN_FIRST = ch3First('training')
const IMPL_BEAT = ch3First('implications')
const TAKEAWAY_BEAT = ch3First('takeaway')
const WT_STAGES = ch3Count('network')
/** The network segment's last beat: the four-class class head. */
const WT_HEAD4C_BEAT = WT_FIRST + WT_STAGES - 1
const BEATS = CH3_BEATS
function initialBeat(): number {
  // `last` = the path's back from the Conclusion (config/sitePath.ts).
  return parseBeatParam(route.query.beat, BEATS)
}
const beat = ref(initialBeat())

const isWalkthrough = computed(() => ch3At(beat.value)?.id === 'network')
const isIrr = computed(() => ch3At(beat.value)?.id === 'irr')
const wtStage = computed(() => beat.value - WT_FIRST)
function gotoWtStage(i: number): void {
  beat.value = WT_FIRST + Math.max(0, Math.min(WT_STAGES - 1, i))
}
// The walkthrough's TAXONOMY: 5-class unless a click
// (or `?taxonomy=4c`) says otherwise; the walkthrough re-mounts on a
// change. A click clears the query, so a reload is the talk's 5-class.
const taxonomy = ref<Taxonomy>(route.query.taxonomy === '4c' || beat.value === WT_HEAD4C_BEAT ? '4c' : '5c')
function setTaxonomy(t: Taxonomy): void {
  taxonomy.value = t
  if (route.query.taxonomy !== undefined) {
    const query = { ...route.query }
    delete query.taxonomy
    void router.replace({ query })
  }
}
// The network segment's last beat: the class head in
// the FOUR-class taxonomy, its training playing — on the NEXT path after
// the five-class head. Arriving switches the taxonomy (the walkthrough
// re-mounts on the lake that was on screen); leaving goes back to five.
/** A taxonomy re-mount: the outgoing walkthrough fades out over the
 *  incoming one (its own fade-in waits on its index). */
function onNetLeave(el: Element, done: () => void): void {
  if (!isWalkthrough.value) {
    done()
    return
  }
  const h = el as HTMLElement
  h.style.pointerEvents = 'none'
  h.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 520, easing: 'ease-in', fill: 'forwards' })
    .finished.then(done, done)
}
/** The lake on screen in the walkthrough (a re-mount opens on it). */
const netLake = ref(NET_OPENING_LAKE)
/** The re-mount into the four-class head came from the five-class one. */
const netPlayHead = ref(false)
watch(beat, (b, old) => {
  if (b === WT_HEAD4C_BEAT) {
    netPlayHead.value = old === WT_HEAD4C_BEAT - 1
    if (taxonomy.value !== '4c') setTaxonomy('4c')
  } else if (old === WT_HEAD4C_BEAT) {
    netPlayHead.value = false
    if (taxonomy.value !== '5c') setTaxonomy('5c')
  }
  // the four-class head's data, warmed while the five-class one plays
  if (b === WT_HEAD4C_BEAT - 1) warmNetworkOpeners(netLake.value, '4c')
})

// ── Ch.1's opening view, verbatim (SectionCh1 beat 0) ─────────────────
const NORTH_LAKE = { lat: 68.7249, lon: -49.4957 }
const CW_CAM_LAT = 61.6
const CW_CAM_LON = -67.2
const CW_CAM_DISTANCE_MEDIUM = 0.58
const CW_CAM_FOV_MEDIUM_DEG = 13
const CH1_EXAG = 0.014
const PAN_MS = 1800
const FEATURED_LAKES_URL = mediaUrl('ch01/featured_lakes.json')

// The five ESSD Fig. 4 lakes (= Ch.1's featured lakes; class palette is
// the site-wide one). `slot` = where the director sketched each callout's
// centre, in viewport fractions; EssdLakePanels solves the actual
// rectangles around these — as big as they can be without overlapping
// each other, the lake polygons, the nav or a neighbour's leader.
const panelLakes: PanelLake[] = [
  { id: CH3_PANEL_LAKE_IDS[0], cls: 'ND', className: 'No drainage',       color: '#e8524a', slot: { x: 0.38, y: 0.19 } },
  { id: CH3_PANEL_LAKE_IDS[1], cls: 'LD', className: 'Lateral drainage',  color: '#ff9800', slot: { x: 0.63, y: 0.24 } },
  { id: CH3_PANEL_LAKE_IDS[2], cls: 'MD', className: 'Moulin drainage',   color: '#42a5f5', slot: { x: 0.65, y: 0.63 } },
  { id: CH3_PANEL_LAKE_IDS[3], cls: 'HF', className: 'Hydrofracture',     color: '#4caf50', slot: { x: 0.37, y: 0.69 } },
  { id: CH3_PANEL_LAKE_IDS[4], cls: 'CD', className: 'Crevasse drainage', color: '#ab47bc', slot: { x: 0.125, y: 0.50 } },
]

// ── the map view (beat 1): Fig. 1b's strip, straight down, north up ──
// Same bbox EssdFig1Globes used for the labeled strip. Frame height on
// the surface = 2·A·tan(fov/2): a 6° telephoto from A ≈ 4800 km shows
// 500 km, so the belt fills the height and the view reads as a flat map
// (the curvature across it sags < 4 km). This globe-to-map move is the
// transition the director singled out as the site's best; mapFocus
// below is its framing math, applyBeat its timings.
const CW = { lonW: -51.7, lonE: -46.6, latS: 68.1, latN: 72.1 }
const MAP_FOV_DEG = 6
const MAP_FRAME_KM = 500
const EARTH_R_KM = 6371
// The Globe's 0.30 view shift puts the focal at 35 % of the width (the
// fly-along measured it), so the focal sits 2.4° WEST of the lake belt
// (over the fjords) to bring the belt to ~48 % and leave the right for
// the legend. Centre a tad north of the belt (the northern lakes were
// otherwise under the top ribbon).
const MAP_FOCAL = { lat: 70.05, lon: (CW.lonW + CW.lonE) / 2 - 2.4 }
function mapFocus(durationMs: number) {
  const altKm = MAP_FRAME_KM / (2 * Math.tan((MAP_FOV_DEG * Math.PI) / 360))
  return {
    lat: MAP_FOCAL.lat,
    lon: MAP_FOCAL.lon,
    cameraLat: MAP_FOCAL.lat,
    cameraLon: MAP_FOCAL.lon,
    distance: 0.5 * (1 + altKm / EARTH_R_KM),
    fovDeg: MAP_FOV_DEG,
    durationMs,
    upNorth: true,
  }
}

// ── rAF lerps ─────────────────────────────────────────────────────────
function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}
type Lerp = { raf: number | null; from: number; to: number; current: number; ms: number; onTick: (v: number) => void }
function makeLerp(ms: number, onTick: (v: number) => void): Lerp {
  return { raf: null, from: 0, to: 0, current: 0, ms, onTick }
}
function startLerp(L: Lerp, to: number, ms = L.ms): void {
  if (L.raf !== null) cancelAnimationFrame(L.raf)
  L.from = L.current
  L.to = to
  const t0 = performance.now()
  const tick = (now: number) => {
    const t = Math.min(1, (now - t0) / ms)
    L.current = L.from + (L.to - L.from) * easeInOutCubic(t)
    L.onTick(L.current)
    L.raf = t < 1 ? requestAnimationFrame(tick) : null
  }
  L.raf = requestAnimationFrame(tick)
}
function snapLerp(L: Lerp, v: number): void {
  if (L.raf !== null) cancelAnimationFrame(L.raf)
  L.raf = null
  L.current = v
  L.onTick(v)
}

const panelsOpacity = ref(0)
const panelsLerp = makeLerp(500, (v) => { panelsOpacity.value = v })
const featuredLerp = makeLerp(700, (v) => emitFeatured(v))
const stripLerp = makeLerp(1200, (v) => emitStrip(v))
const mapUiOpacity = ref(0)
const mapUiLerp = makeLerp(500, (v) => { mapUiOpacity.value = v })
const seasonUiOpacity = ref(0)
const seasonUiLerp = makeLerp(500, (v) => { seasonUiOpacity.value = v })

function emitFeatured(opacity: number): void {
  if (opacity <= 0.001) {
    emit('lake-polygons', null)
    return
  }
  emit('lake-polygons', { dataUrl: FEATURED_LAKES_URL, opacity, featured: true })
}

let timers: number[] = []
function later(ms: number, fn: () => void): void {
  timers.push(window.setTimeout(fn, ms))
}
function clearTimers(): void {
  for (const id of timers) window.clearTimeout(id)
  timers = []
}

// ── the shared season clock ───────────────────────────────────────────
const T0 = '2019-05-01'
const day = ref(0)
const days = ref(153)
const playing = ref(false)
let playTimer: number | null = null
// Under the callouts the clock steps through the CLOCK DATES only — days
// on which at least one of the five lakes has a new valid frame (from
// EssdLakePanels) — two a second (the director's pacing: stepping every
// calendar day, the panels would just wait for each other). On the map
// it is one day per second. The day itself is the shared state, so it
// carries across the dive either way.
const MS_PER_STEP: Record<number, number> = { 0: 500, [MAP_BEAT]: 1000 }
const clockDays = ref<number[]>([])
// The callouts' season starts only once the panels can be seen (placed,
// every movie decoded) — else a cold load opens weeks into the season.
const panelsReady = ref(false)
let playWhenPanelsReady = false
watch(panelsReady, (r) => {
  if (r && playWhenPanelsReady && beat.value === 0) {
    playWhenPanelsReady = false
    playing.value = true
    restartClock()
  }
})
function nextDay(d: number): number {
  const n = Math.max(1, days.value)
  const clock = clockDays.value
  if (beat.value === 0 && clock.length) {
    for (const c of clock) if (c > d) return c
    return clock[0]
  }
  return (d + 1) % n
}
function restartClock(): void {
  if (playTimer !== null) {
    window.clearInterval(playTimer)
    playTimer = null
  }
  if (!playing.value) return
  const ms = MS_PER_STEP[beat.value] ?? 1000
  playTimer = window.setInterval(() => {
    day.value = nextDay(day.value)
  }, ms)
}
watch(playing, restartClock)
function onScrub(e: Event): void {
  day.value = parseInt((e.target as HTMLInputElement).value, 10) || 0
  playing.value = false
}
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const dateLabel = computed(() => {
  const t0 = new Date(`${beat.value === MAP_BEAT ? (data.value?.t0 ?? `${year.value}-05-01`) : T0}T00:00:00Z`)
  const t = new Date(t0.getTime() + day.value * 86400e3)
  return `${t.getUTCDate()} ${MONTHS[t.getUTCMonth()]} ${t.getUTCFullYear()}`
})

// ── the labeled population (beat 1 data + canvas) ─────────────────────
interface EssdLake { id: string; cls: string; c: [number, number]; rings: [number, number][][]; pw: number[] | null }
interface EssdFile {
  year: number
  t0: string
  days: number
  classes: Record<string, { name: string; color: string }>
  class_order: string[]
  lakes: EssdLake[]
}
interface EssdStats {
  counts: Record<string, Record<string, number>>
  classes: Record<string, { name: string; color: string }>
  class_order: string[]
}
const year = ref(2019)
const data = ref<EssdFile | null>(null)
// The map's class filter: click a legend row → only that
// class's lakes are drawn; click it again, or double-click any row → all.
const soloClass = ref<string | null>(null)
function toggleSolo(code: string): void {
  soloClass.value = soloClass.value === code ? null : code
}
watch(soloClass, () => { if (beat.value === MAP_BEAT) drawStrip() })
/** The References page, opened at Chapter 3's group (Dunmire 2021, 2025). */
const REFS_LINK = { path: '/references', query: { chapter: 'chapter3' } }
const stats = ref<EssdStats | null>(null)

// Equirectangular canvas over the strip's bbox; the Globe drapes it on
// the sphere. ~4.6 px/km — 1.4× the screen at the map framing (a 1536 ×
// 3072 canvas cost 120–180 ms per day tick, mostly the texture upload,
// and the page ran at ~6 fps while the season played; measured on film).
const STRIP_W = 1024
const STRIP_H = 2048
const stripCanvas = document.createElement('canvas')
stripCanvas.width = STRIP_W
stripCanvas.height = STRIP_H
// Per-lake rings pre-projected to canvas px (centroid + points).
let projected: { cls: string; color: string; cx: number; cy: number; rings: Float32Array[]; pw: number[] | null }[] = []
let stripVersion = 0
let stripOpacity = 0
// Lakes are drawn LAKE_MAG× their true size — at the map framing a
// 1.5 km lake is ~2 px, so the population is enlarged uniformly the way
// Ch.1's lake symbols are (the presenter narrates it). Each day's polygon is the
// lake's true SHAPE scaled by √p_water about its centroid (area ∝
// p_water), class-filled with a thin black outline — nothing persists
// when the water is gone (the director's rule: only a dynamic outline).
const LAKE_MAG = 3.0

function trace(ctx: CanvasRenderingContext2D, ring: Float32Array, cx: number, cy: number, s: number): void {
  ctx.beginPath()
  for (let i = 0; i < ring.length; i += 2) {
    const x = cx + (ring[i] - cx) * s
    const y = cy + (ring[i + 1] - cy) * s
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  }
  ctx.closePath()
}

// Project the year's lakes once.
function projectStrip(): void {
  const d = data.value
  projected = []
  if (!d) return
  const px = (lon: number): number => ((lon - CW.lonW) / (CW.lonE - CW.lonW)) * STRIP_W
  const py = (lat: number): number => ((CW.latN - lat) / (CW.latN - CW.latS)) * STRIP_H
  for (const lk of d.lakes) {
    const color = d.classes[lk.cls]?.color ?? '#ffffff'
    const cx = px(lk.c[0])
    const cy = py(lk.c[1])
    const rings = lk.rings.map((ring) => {
      const f = new Float32Array(ring.length * 2)
      for (let i = 0; i < ring.length; i++) {
        f[i * 2] = px(ring[i][0])
        f[i * 2 + 1] = py(ring[i][1])
      }
      return f
    })
    projected.push({ cls: lk.cls, color, cx, cy, rings, pw: lk.pw })
  }
}

function drawStrip(): void {
  const d = data.value
  const ctx = stripCanvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, STRIP_W, STRIP_H)
  if (!d) return
  if (!projected.length) projectStrip()
  const di = Math.min(day.value, (d.days || 1) - 1)
  ctx.lineWidth = 1.3
  ctx.strokeStyle = '#000'
  ctx.lineJoin = 'round'
  const solo = soloClass.value
  for (const lk of projected) {
    if (solo && lk.cls !== solo) continue
    const pw = lk.pw ? lk.pw[di] / 100 : 0
    if (pw <= 0.005) continue
    ctx.fillStyle = lk.color
    const s = LAKE_MAG * Math.sqrt(pw)
    for (const r of lk.rings) {
      trace(ctx, r, lk.cx, lk.cy, s)
      ctx.fill()
      ctx.stroke()
    }
  }
  stripVersion += 1
  emitStrip(stripOpacity)
}

function emitStrip(opacity: number): void {
  stripOpacity = opacity
  if (opacity <= 0.001 && beat.value !== MAP_BEAT) {
    emit('lake-strip', null)
    return
  }
  emit('lake-strip', {
    canvas: stripCanvas,
    lonW: CW.lonW, lonE: CW.lonE, latS: CW.latS, latN: CW.latN,
    opacity,
    version: stripVersion,
  })
}

async function setYear(y: number): Promise<void> {
  if (year.value === y && data.value) return
  year.value = y
  try {
    const r = await fetch(mediaUrl(`ch03/essd_lakes_${y}.json`))
    if (!r.ok) return
    data.value = (await r.json()) as EssdFile
    days.value = data.value.days || 153
    projectStrip()
    drawStrip()
  } catch {
    // keep the previous year's lakes
  }
}
watch(day, () => { if (beat.value === MAP_BEAT) drawStrip() })

const total = computed(() => data.value?.lakes.length ?? 0)
const classRows = computed(() => {
  const d = data.value
  if (!d) return []
  const counts: Record<string, number> = {}
  for (const lk of d.lakes) counts[lk.cls] = (counts[lk.cls] ?? 0) + 1
  return d.class_order.map((code) => ({
    code,
    name: d.classes[code]?.name ?? code,
    color: d.classes[code]?.color ?? '#fff',
    count: counts[code] ?? 0,
  }))
})
// Fig. 1's pies — per-class share per year, from essd_stats.json.
const pies = computed(() => {
  const st = stats.value
  if (!st) return []
  return [2018, 2019].map((y) => {
    const counts = st.counts[String(y)] ?? {}
    const n = Object.values(counts).reduce((a, b) => a + b, 0)
    let a0 = -Math.PI / 2
    const slices = st.class_order.map((code) => {
      const f = n ? (counts[code] ?? 0) / n : 0
      const a1 = a0 + f * 2 * Math.PI
      const large = a1 - a0 > Math.PI ? 1 : 0
      // Drawn in a 230-unit box (radius 100) — a unit-radius box gave the
      // labels a sub-pixel font size the browser refused to lay out.
      const R = 100
      const d = `M0,0 L${(R * Math.cos(a0)).toFixed(2)},${(R * Math.sin(a0)).toFixed(2)} A${R},${R} 0 ${large} 1 ${(R * Math.cos(a1)).toFixed(2)},${(R * Math.sin(a1)).toFixed(2)} Z`
      const am = (a0 + a1) / 2
      const s = { code, d, color: st.classes[code]?.color ?? '#fff', pct: `${Math.round(f * 100)}%`, lx: (0.62 * R * Math.cos(am)).toFixed(1), ly: (0.62 * R * Math.sin(am) + 7).toFixed(1) }
      a0 = a1
      return s
    })
    return { year: y, n, slices }
  })
})

// ── beat dispatch ─────────────────────────────────────────────────────
// Beat 0 → 1 is ONE move (~7 s), the Introduction fly-along's grammar:
// the callouts and the five polygons fade, the hillshade goes, the dome
// flattens (3.2 s), the camera dives to the nadir map (6 s from 0.5 s),
// and the population paints in over the last stretch; the season plays
// on once landed. Back (1 → 0) reverses it under Ch.1's camera return.
const FLATTEN_MS = 3200
const DOLLY_AT = 500
const DOLLY_MS = 6000
const STRIP_AT = 5200
const SETTLE_MS = 900

let prevBeat = -1

function applyBeat(b: number): void {
  clearTimers()
  playWhenPanelsReady = false
  emit('globe-clicks', 1)
  if (b !== MAP_BEAT) soloClass.value = null
  // The walkthrough's videos, warmed while the agreement beats are
  // narrated (EssdNetwork's own lake: the moulin example it opens on).
  if (b >= IRR_BEAT && b < WT_FIRST) warmNetworkOpeners(NET_OPENING_LAKE, taxonomy.value)

  if (b === 0) {
    startLerp(stripLerp, 0, 400)
    later(450, () => emitStrip(0))
    emit('chapter-focus', {
      lat: NORTH_LAKE.lat,
      lon: NORTH_LAKE.lon,
      cameraLat: CW_CAM_LAT,
      cameraLon: CW_CAM_LON,
      distance: CW_CAM_DISTANCE_MEDIUM,
      fovDeg: CW_CAM_FOV_MEDIUM_DEG,
      durationMs: PAN_MS,
    })
    emit('chapter-exag-ms', 1500)
    emit('chapter-exag', CH1_EXAG)
    emit('hillshade', null)
    startLerp(featuredLerp, 1)
    snapLerp(mapUiLerp, 0)
    // Panels land once the camera has: live from beat 1 that is the
    // 1.8 s return; a fresh mount pays only the featured fetch. (The
    // panels themselves also wait for their layout to solve.)
    later(prevBeat === MAP_BEAT ? 1500 : 500, () => {
      startLerp(panelsLerp, 1)
      startLerp(seasonUiLerp, 1)
      if (panelsReady.value) {
        playing.value = true
        restartClock()
      } else {
        playWhenPanelsReady = true
      }
    })
  } else if (b === MAP_BEAT) {
    const live = prevBeat === 0
    snapLerp(panelsLerp, 0)
    playing.value = false
    emit('hillshade', 0)
    emit('chapter-exag-ms', live ? FLATTEN_MS : SETTLE_MS)
    emit('chapter-exag', 0)
    if (!data.value) setYear(year.value)
    const land = () => {
      drawStrip()
      startLerp(stripLerp, 1, live ? 1400 : 900)
      startLerp(mapUiLerp, 1, live ? 900 : 500)
      startLerp(seasonUiLerp, 1, 500)
    }
    if (live) {
      startLerp(featuredLerp, 0, 900)
      startLerp(seasonUiLerp, 0, 400)
      later(DOLLY_AT, () => emit('chapter-focus', mapFocus(DOLLY_MS)))
      later(STRIP_AT, land)
      later(DOLLY_AT + DOLLY_MS + 200, () => { playing.value = true; restartClock() })
    } else {
      snapLerp(featuredLerp, 0)
      emit('chapter-focus', mapFocus(SETTLE_MS))
      later(SETTLE_MS + 100, () => {
        land()
        later(900, () => { playing.value = true; restartClock() })
      })
    }
  } else {
    // Opaque panels above the Globe: park it, calm.
    playing.value = false
    snapLerp(panelsLerp, 0)
    snapLerp(seasonUiLerp, 0)
    snapLerp(stripLerp, 0)
    emitStrip(0)
    snapLerp(featuredLerp, 0)
    snapLerp(mapUiLerp, 0)
    emit('hillshade', null)
    emit('chapter-exag-ms', 1500)
    emit('chapter-exag', CH1_EXAG)
  }

  emit('beat-change', b, b === BEATS - 1)
  prevBeat = b
}

// The implications beat: a NEXT pressed before its
// ribbons have rolled out rolls them out instead of leaving; the next
// NEXT leaves for the Conclusion. The pill and the remote's → both come
// through here (Explore's navNext → advanceTrigger).
const implRef = ref<{ startRoll: () => boolean } | null>(null)
function next(): void {
  if (beat.value === IMPL_BEAT && implRef.value?.startRoll()) return
  if (beat.value < BEATS - 1) beat.value += 1
  else emit('advance')
}
function prev(): void {
  if (beat.value > 0) beat.value -= 1
}

watch(beat, (b) => applyBeat(b))
watch(
  () => props.advanceTrigger,
  (v, old) => {
    if (v == null || v === old) return
    next()
  },
)
watch(
  () => props.backTrigger,
  (v, old) => {
    if (v == null || v === old) return
    prev()
  },
)
// Sub-menu landmark jump: land on the beat exactly as `?beat=N` does on
// mount (prevBeat = −1 → the settled path, no live dive).
watch(
  () => props.jumpTo?.seq,
  () => {
    const j = props.jumpTo
    if (!j) return
    const b = Math.max(0, Math.min(BEATS - 1, j.beat))
    if (b === beat.value) return
    prevBeat = -1
    beat.value = b
  },
)

onMounted(() => {
  // Warm the map beat's data so the dive never waits on a fetch.
  setYear(year.value)
  fetch(mediaUrl('ch03/essd_stats.json'))
    .then((r) => (r.ok ? r.json() : null))
    .then((j) => { stats.value = j as EssdStats | null })
    .catch(() => {})
  prevBeat = -1
  applyBeat(beat.value)
})

onBeforeUnmount(() => {
  clearTimers()
  playing.value = false
  if (playTimer !== null) window.clearInterval(playTimer)
  snapLerp(panelsLerp, 0)
  snapLerp(featuredLerp, 0)
  snapLerp(stripLerp, 0)
  beat.value = -1 // so emitStrip(0) really clears
  emit('lake-strip', null)
  emit('lake-polygons', null)
  emit('lake-hover', null)
  emit('chapter-focus', null)
  emit('chapter-exag', null)
  emit('hillshade', null)
  emit('globe-clicks', 1)
})
</script>

<style scoped>
/* Globe-native: the root is TRANSPARENT so the live Globe shows through.
   Beats that want a ground get it from .ch3-root-panel — an opaque layer
   painted ABOVE the Globe, which is fine; hiding the Globe itself (v-show,
   visibility, opacity on the component) is not — see Explore.vue. */
.ch3-root {
  position: fixed;
  inset: 0;
  background: transparent;
  pointer-events: none;
  font-family: 'Inter', system-ui, sans-serif;
  color: #f5f0e6;
}
.ch3-root > * { pointer-events: auto; }
.ch3-root-panel {
  background:
    radial-gradient(120% 90% at 30% 20%, rgba(18, 16, 12, 0.94) 0%,
      rgba(10, 9, 8, 0.96) 55%, rgba(6, 6, 6, 0.97) 100%);
  pointer-events: auto;
}

/* ── beat 1: legend — down and left of the beat pills, with the Fig. 1
   pies. Later enlarged to ~2× its first size so it
   fills the empty ice on the right, type large; each class row is a
   button that isolates its class on the map. Sizes ride the viewport
   HEIGHT so the card never reaches the timebar. ── */
.ch3-legend {
  position: absolute;
  top: 11.5vh;
  right: 4vw;
  width: clamp(400px, 38vw, 620px);
  box-sizing: border-box;
  padding: clamp(1rem, 2.6vh, 1.7rem) clamp(1.2rem, 2vw, 2rem);
  border-radius: 18px;
  background: rgba(8, 7, 6, 0.86);
  border: 1px solid rgba(245, 199, 94, 0.22);
  backdrop-filter: blur(8px);
  transition: opacity 0.3s;
}
.ch3-leg-title {
  font-family: 'EB Garamond', serif;
  font-size: clamp(1.6rem, 4.3vh, 2.6rem);
  line-height: 1.1;
  color: var(--gold-bright);
  margin-bottom: clamp(0.4rem, 1.4vh, 0.9rem);
  white-space: nowrap;
}
.ch3-leg-n {
  font-variant-numeric: tabular-nums;
}
.ch3-leg-row {
  display: grid;
  grid-template-columns: clamp(16px, 2.6vh, 24px) 3.2em 1fr auto;
  align-items: center;
  gap: 0.6em;
  width: 100%;
  margin: 0;
  padding: clamp(0.18rem, 0.75vh, 0.45rem) 0.6em;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: inherit;
  font-family: inherit;
  font-size: clamp(1.1rem, 2.9vh, 1.75rem);
  text-align: left;
  cursor: pointer;
  box-shadow: inset 0 0 0 1px transparent;
  transition: background 0.2s, box-shadow 0.2s, opacity 0.2s;
}
.ch3-leg-row:hover { background: rgba(245, 240, 230, 0.06); }
/* the isolated class: its colour behind it, a ring, full ink */
.ch3-leg-row.ch3-leg-on {
  background: color-mix(in srgb, var(--acc) 20%, transparent);
  box-shadow: inset 0 0 0 1.5px var(--acc);
}
/* the others while one is isolated */
.ch3-leg-row.ch3-leg-off { opacity: 0.38; }
.ch3-leg-row.ch3-leg-off:hover { opacity: 0.7; }
.ch3-leg-chip {
  width: clamp(16px, 2.6vh, 24px);
  height: clamp(16px, 2.6vh, 24px);
  border-radius: 4px;
}
.ch3-leg-code {
  font-weight: 700;
  letter-spacing: 0.04em;
  color: rgba(245, 240, 230, 0.85);
}
.ch3-leg-on .ch3-leg-code { color: var(--acc); }
.ch3-leg-name { color: rgba(245, 240, 230, 0.9); white-space: nowrap; }
.ch3-leg-count {
  justify-self: end;
  font-variant-numeric: tabular-nums;
  color: rgba(245, 240, 230, 0.55);
  padding-left: 0.5rem;
}
.ch3-leg-on .ch3-leg-count { color: rgba(245, 240, 230, 0.9); }
.ch3-pies {
  display: flex;
  gap: 1.2rem;
  justify-content: space-around;
  margin-top: clamp(0.6rem, 1.8vh, 1.2rem);
  padding-top: clamp(0.6rem, 1.6vh, 1.1rem);
  border-top: 1px solid rgba(245, 199, 94, 0.18);
}
.ch3-pie {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.45rem;
  background: transparent;
  border: 0;
  color: rgba(245, 240, 230, 0.6);
  font-family: inherit;
  font-size: clamp(0.86rem, 2vh, 1.2rem);
  letter-spacing: 0.04em;
  cursor: pointer;
  opacity: 0.55;
  transition: opacity 0.2s, transform 0.2s;
}
.ch3-pie:hover { opacity: 0.85; }
.ch3-pie-on { opacity: 1; color: var(--gold-bright); }
.ch3-pie-on svg { transform: scale(1.06); }
.ch3-pie svg {
  width: clamp(128px, 21vh, 220px);
  height: clamp(128px, 21vh, 220px);
  transition: transform 0.2s;
}
.ch3-pie path { stroke: #0d0b09; stroke-width: 3; }
.ch3-pie-lbl {
  fill: #0d0b09;
  font-size: 20px;
  font-weight: 700;
  font-family: 'Inter', system-ui, sans-serif;
}
.ch3-pie-cap { font-variant-numeric: tabular-nums; white-space: nowrap; }

/* the label beat's door, bottom-right — the MORE DETAILS pills' corner
   (2vw / 2.2vh), above the demo's stage */
.ch3-mklabels {
  position: absolute;
  right: 2vw;
  bottom: 2.2vh;
  z-index: 5;
}
/* bottom-right, right of the epoch clock (EssdTraining's .tr-clock) */
.ch3-tbsdoor {
  position: absolute;
  right: 1.4vw;
  bottom: 2.2vh;
  z-index: 5;
}

/* bottom-right source link — the Introduction's corner-link style, on a
   dark pill because here it sits over the white ice sheet */
.corner-link {
  position: absolute;
  right: 2vw;
  bottom: 2.2vh;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  background: rgba(8, 7, 6, 0.72);
  font-size: 0.85rem;
  letter-spacing: 0.04em;
  color: var(--accent);
  text-decoration: underline dotted rgba(108, 204, 255, 0.5);
  text-underline-offset: 3px;
  transition: opacity 0.3s;
}
.corner-link:hover {
  color: #fff;
  text-decoration-color: rgba(255, 255, 255, 0.7);
}

/* ── the season timebar (bottom-centre; beats 0 and 1) ── */
.ch3-season {
  position: absolute;
  left: 50%;
  bottom: 3.2vh;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.55rem 1rem;
  border-radius: 999px;
  background: rgba(8, 7, 6, 0.84);
  border: 1px solid rgba(245, 199, 94, 0.22);
  backdrop-filter: blur(8px);
  transition: opacity 0.3s;
}
.ch3-play {
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
.ch3-season input[type='range'] {
  width: min(38vw, 520px);
  accent-color: var(--gold);
}
.ch3-date {
  min-width: 7.2rem;
  font-variant-numeric: tabular-nums;
  font-size: 0.95rem;
  color: #f5f0e6;
}
</style>
