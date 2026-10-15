<template>
  <!-- Additional Work → "Revisiting lake drainage papers". The director's
       brief: gather every lake that Christoffersen 2018 claims drained
       englacially to the ice-bed interface, stack their time series into
       movies, and look in each for evidence of drainage into the ice.

       The Globe — the greenland object — stays live behind everything on
       this page; nothing here hides or veils its canvas. This component is
       a click-through layer of figure labels and controls above it, and it
       drives the camera and the marks ON THE ICE (the Globe's lakeStrip,
       laid on the displaced surface) with the chapters' own emits.

       VIEW A, the cascade on the ice: the paper's lake area seen from the
       coast looking inland (the Introduction's coupling step looks the
       other way), a time slider over its days 5 → 10 June 2010. On each
       drainage day that day's drained lakes PING GOLD — the Conclusion's
       gesture: a hot flash and a bloom, then gold; a day later a fainter
       gold — while the lakes it leaves unchanged stay water-blue. 8 and 9
       June are the paper's cloud days: nothing was observed, the slider
       says so. The site's NEXT / BACK step the paper's four maps (5 · 6 ·
       7 · 8–10 June); NEXT after the last opens VIEW B.

       VIEW B, every lake: five columns of cards — the lakes the paper
       drains first, then the nine it never does. A click: the other cards
       fall away, the card becomes the player (RevisitPlayer.vue) and the
       Globe flies to that lake, a gold dot on the ice.

       Deep links: ?day=2010-06-07 · ?view=lakes · ?lake=C18_010&year=2010
       &sensor=modis|hires|side. Figure labels only; the director narrates. -->
  <div class="rv" :class="[`rv-is-${view}`, { 'rv-has-lake': !!selected }]">
    <!-- ───────────── VIEW A: the cascade on the ice ───────────── -->
    <Transition name="rv-fade">
      <div v-if="view === 'cascade' && manifest" class="rv-a">
        <div class="rv-stamp" :class="{ 'rv-stamp-cloud': today?.kind === 'cloud' }">
          <span class="rv-stamp-date">{{ stampDate }} <i>{{ today?.iso.slice(0, 4) }}</i></span>
          <span class="rv-stamp-big">{{ stampBig }}</span>
          <span v-if="stampSmall" class="rv-stamp-small">{{ stampSmall }}</span>
        </div>

        <div class="rv-legend">
          <span class="rv-leg"><i class="rv-dot rv-dot-fresh" />drained that day</span>
          <span class="rv-leg"><i class="rv-dot rv-dot-gone" />drained earlier</span>
          <span class="rv-leg"><i class="rv-dot rv-dot-lake" />lake</span>
          <span class="rv-leg"><i class="rv-dot rv-dot-lake rv-dot-again" />lake · drained earlier</span>
        </div>

        <div class="rv-time">
          <button class="rv-play" :aria-label="playing ? 'Pause' : 'Play'" @click="pick($event, togglePlay)">
            <PlayPauseGlyph :playing="playing" :size="16" />
          </button>
          <div class="rv-slider" :style="{ '--n': days.length - 1 }">
            <span
              v-if="cloudSpan"
              class="rv-cloud"
              :style="{ left: stopPct(cloudSpan.from - 0.5), width: stopWidth(cloudSpan.to - cloudSpan.from + 1) }"
            ><i>cloud</i></span>
            <input
              class="rv-range"
              type="range"
              min="0"
              :max="days.length - 1"
              step="1"
              :value="dayIdx"
              :style="{ '--fill': `${(100 * dayIdx) / Math.max(1, days.length - 1)}%` }"
              aria-label="Day of the cascade"
              @input="onSlide"
            />
            <span
              v-for="(d, i) in days"
              :key="d.iso"
              class="rv-stop"
              :class="{ 'rv-stop-on': i === dayIdx, 'rv-stop-cloud': d.kind === 'cloud' }"
              :style="{ left: stopPct(i) }"
            >{{ dayLabel(d.iso) }}</span>
          </div>
        </div>

        <a class="rv-cite" :href="manifest.paper.doi" target="_blank" rel="noopener noreferrer">[{{ citeShort }}]</a>

        <button class="rv-door" data-rv="lakes" @click="pick($event, () => setView('lakes'))">
          See each lake time series <span class="rv-door-arrow" aria-hidden="true">→</span>
        </button>
      </div>
    </Transition>

    <!-- ───────────── VIEW B: every lake ───────────── -->
    <Transition name="rv-fade">
      <div v-if="view === 'lakes' && manifest" class="rv-b">
        <!-- a dark gauze over the live Globe while the grid is up; it lifts
             off the ice when a lake is chosen -->
        <div class="rv-gauze" />

        <button class="rv-back" data-rv="cascade" @click="pick($event, () => setView('cascade'))">
          <span aria-hidden="true">←</span> The cascade
        </button>
        <!-- the grid's pictures are one year's (the player has the same toggle) -->
        <Transition name="rv-fade">
          <div v-if="!selected" class="rv-year" role="tablist" aria-label="Year">
            <button
              v-for="y in REVISIT_YEARS"
              :key="y"
              class="rv-year-btn"
              :class="{ 'rv-year-btn--on': year === y }"
              role="tab"
              :aria-selected="year === y"
              :data-year="y"
              @click="pick($event, () => (year = y))"
            >{{ y }}</button>
          </div>
        </Transition>

        <div ref="scrollEl" class="rv-scroll" :class="{ 'rv-falling': !!selected }">
          <template v-for="g in groups" :key="g.key">
            <h3 class="rv-group">{{ g.label }} · {{ g.lakes.length }}</h3>
            <div class="rv-grid">
              <button
                v-for="(l, i) in g.lakes"
                :key="l.id"
                class="rv-card"
                :class="{ 'rv-card-chosen': selected === l.id, 'rv-card-home': homing === l.id }"
                :data-lake="l.id"
                :style="fallStyle(l.id, i)"
                :tabindex="selected ? -1 : 0"
                @click="openLake(l.id, $event)"
              >
                <span class="rv-thumb">
                  <img v-if="thumbOf(l)" :src="thumbOf(l)!" loading="lazy" decoding="async" alt="" />
                  <span class="rv-card-id">{{ l.id }}</span>
                </span>
                <span class="rv-chips">
                  <i v-for="d in l.drained_days" :key="d" class="rv-chip">{{ claimLabel(d, manifest) }}</i>
                </span>
              </button>
            </div>
          </template>
        </div>

        <Transition name="rv-player">
          <div v-if="selectedLake && playerOn" :key="selectedLake.id" class="rv-player">
            <RevisitPlayer
              :lake="selectedLake"
              :manifest="manifest"
              :year="year"
              :mode="mode"
              @update:year="year = $event"
              @update:mode="mode = $event"
              @close="closeLake"
            />
          </div>
        </Transition>

        <!-- the chosen card's picture, flying between its card and the player -->
        <img v-if="ghost" ref="ghostEl" class="rv-ghost" :src="ghost.src" alt="" :style="ghost.style" />
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter, type LocationQueryRaw } from 'vue-router'
import PlayPauseGlyph from '../PlayPauseGlyph.vue'
import RevisitPlayer from '../RevisitPlayer.vue'
import {
  REVISIT_MANIFEST,
  REVISIT_MODES,
  REVISIT_YEARS,
  claimLabel,
  dayLabel,
  dayOfIso,
  isoOfDay,
  revisitUrl,
  type C18Lake,
  type C18Manifest,
  type C18ObsDay,
  type RevisitMode,
  type RevisitYear,
} from '../../config/revisit'

const props = defineProps<{
  /** The site's NEXT / BACK (and the presenter remote), while this page
   *  says it has a step for them (`nav-state`). */
  advanceTrigger?: number
  backTrigger?: number
}>()

interface Focus {
  lat: number
  lon: number
  cameraLat?: number
  cameraLon?: number
  distance?: number
  fovDeg?: number
  durationMs?: number
  focalElevM?: number
  focalOnSurface?: boolean
  focalExag?: number
}
const emit = defineEmits<{
  'globe-clicks': [value: number]
  'chapter-focus': [Focus | null]
  'chapter-exag': [value: number | null]
  'chapter-exag-ms': [value: number]
  hillshade: [value: number | null]
  'lake-strip': [
    | { canvas: HTMLCanvasElement; lonW: number; lonE: number; latS: number; latN: number; opacity: number; version: number; surface: boolean }
    | null,
  ]
  /** Does the page have a step for the site's NEXT / BACK right now? */
  'nav-state': [{ next: boolean; back: boolean }]
}>()

const route = useRoute()
const router = useRouter()

// ── the manifest ──────────────────────────────────────────────────────
const manifest = ref<C18Manifest | null>(null)
let alive = true

type View = 'cascade' | 'lakes'
const view = ref<View>('cascade')
const year = ref<RevisitYear>('2010')
/** Opens side by side: the daily coarse track beside the sparse sharp one. */
const mode = ref<RevisitMode>('side')
const selected = ref<string | null>(null)
const selectedLake = computed(() => manifest.value?.lakes.find((l) => l.id === selected.value) ?? null)

// ── VIEW A: the paper's days ──────────────────────────────────────────
interface Day {
  iso: string
  kind: 'obs' | 'cloud' | 'gap'
  obs: C18ObsDay | null
}
/** Every calendar day from the paper's first map to its last. */
const days = computed<Day[]>(() => {
  const m = manifest.value
  if (!m || !m.obs_days.length) return []
  const first = m.obs_days[0].date
  const n = dayOfIso(first, m.obs_days[m.obs_days.length - 1].date) + 1
  return Array.from({ length: n }, (_, i) => {
    const iso = isoOfDay(first, i)
    const obs = m.obs_days.find((o) => o.date === iso) ?? null
    return { iso, kind: obs ? 'obs' : m.cloud_days.includes(iso) ? 'cloud' : 'gap', obs }
  })
})
const dayIdx = ref(0)
const today = computed(() => days.value[dayIdx.value] ?? null)
/** The paper's maps, as indices into `days` — what NEXT / BACK step. */
const obsIdx = computed(() => days.value.flatMap((d, i) => (d.kind === 'obs' ? [i] : [])))
const nextObs = computed(() => obsIdx.value.find((i) => i > dayIdx.value) ?? null)
const prevObs = computed(() => [...obsIdx.value].reverse().find((i) => i < dayIdx.value) ?? null)

const cloudSpan = computed(() => {
  const c = days.value.flatMap((d, i) => (d.kind === 'cloud' ? [i] : []))
  return c.length ? { from: c[0], to: c[c.length - 1] } : null
})

// The day's figure label: the paper's own dating (its last map is "8–10
// June") and its own counts (its captions).
const stampDate = computed(() => {
  const d = today.value
  const m = manifest.value
  if (!d || !m) return ''
  return d.kind === 'obs' ? claimLabel(d.iso, m) : dayLabel(d.iso)
})
const stampBig = computed(() => {
  const d = today.value
  if (!d) return ''
  if (d.kind !== 'obs' || !d.obs) return d.kind === 'cloud' ? 'cloud' : ''
  const c = d.obs.caption
  if (c.drained !== undefined) return `${c.drained} drained`
  if (c.present !== undefined) return `${c.present} lakes`
  return ''
})
const stampSmall = computed(() => {
  const c = today.value?.obs?.caption
  return c?.unchanged !== undefined ? `${c.unchanged} unchanged` : ''
})
const citeShort = computed(() => manifest.value?.paper.cite.split(',')[0] ?? '')

/** A stop's x along the slider (the thumb's travel), as CSS. */
function stopPct(i: number): string {
  const n = Math.max(1, days.value.length - 1)
  return `calc(var(--thumb) / 2 + (100% - var(--thumb)) * ${(i / n).toFixed(5)})`
}
function stopWidth(nDays: number): string {
  const n = Math.max(1, days.value.length - 1)
  return `calc((100% - var(--thumb)) * ${(nDays / n).toFixed(5)})`
}

// ── play: the days in turn, a beat on each map, quicker under cloud ───
const playing = ref(false)
let playTimer: number | null = null
const DWELL_OBS_MS = 2600
const DWELL_OTHER_MS = 900
function clearPlay(): void {
  if (playTimer !== null) {
    window.clearTimeout(playTimer)
    playTimer = null
  }
}
function schedulePlay(): void {
  clearPlay()
  if (!playing.value) return
  if (dayIdx.value >= days.value.length - 1) {
    playing.value = false
    return
  }
  playTimer = window.setTimeout(
    () => {
      playTimer = null
      showDay(dayIdx.value + 1)
      schedulePlay()
    },
    today.value?.kind === 'obs' ? DWELL_OBS_MS : DWELL_OTHER_MS,
  )
}
function togglePlay(): void {
  if (playing.value) {
    playing.value = false
    clearPlay()
    return
  }
  playing.value = true
  // From the last day, the cascade starts over.
  if (dayIdx.value >= days.value.length - 1) showDay(0)
  schedulePlay()
}
function onSlide(e: Event): void {
  playing.value = false
  clearPlay()
  showDay(parseInt((e.target as HTMLInputElement).value, 10) || 0)
}

// ── the marks on the ice ──────────────────────────────────────────────
// An equirectangular canvas over the lakes' box (padded for the bloom),
// square on the ground at its mid-latitude; the Globe lays it on the ice.
const PX_PER_KM = 18
const PAD_LAT = 0.07
const PAD_LON = 0.18
const KM_PER_DEG = 111.19
let box: { latS: number; latN: number; lonW: number; lonE: number } | null = null
const strip = document.createElement('canvas')
let stripVersion = 0
/** Per lake: canvas px. */
let spots: { lake: C18Lake; x: number; y: number; jitter: number }[] = []

function layoutStrip(m: C18Manifest): void {
  const b = m.lake_bbox
  box = { latS: b.south - PAD_LAT, latN: b.north + PAD_LAT, lonW: b.west - PAD_LON, lonE: b.east + PAD_LON }
  const midLat = ((box.latS + box.latN) / 2) * (Math.PI / 180)
  strip.width = Math.round((box.lonE - box.lonW) * KM_PER_DEG * Math.cos(midLat) * PX_PER_KM)
  strip.height = Math.round((box.latN - box.latS) * KM_PER_DEG * PX_PER_KM)
  const bx = box
  spots = m.lakes.map((lake, i) => ({
    lake,
    x: ((lake.lon - bx.lonW) / (bx.lonE - bx.lonW)) * strip.width,
    y: ((bx.latN - lake.lat) / (bx.latN - bx.latS)) * strip.height,
    // a fixed scatter of up to PING_SPREAD s, so 40-odd lakes do not fire as one frame
    jitter: ((i * 0.6180339887) % 1) * PING_SPREAD,
  }))
}

type Mark = 'none' | 'lake' | 'lake-drained' | 'gone' | 'fresh'
/** A lake on day `k`: what the paper's maps say up to that day. */
function markOf(lake: C18Lake, k: number): Mark {
  const ds = days.value
  if (k < 0 || !ds.length) return 'none'
  let lastState: string | null = null
  let lastAt = -1
  let drainedBefore = false
  for (let i = 0; i <= k && i < ds.length; i++) {
    if (ds[i].kind !== 'obs') continue
    const s = lake.states[ds[i].iso]
    if (!s) continue
    if (lastState === 'drained') drainedBefore = true
    lastState = s
    lastAt = i
  }
  if (lastState === null) return 'none'
  if (lastState === 'drained') return lastAt === k ? 'fresh' : 'gone'
  return drainedBefore ? 'lake-drained' : 'lake'
}

// The marks (canvas px). On white ice a colour needs a dark edge to hold
// from the back row, and the bloom a dark bed to glow on.
const MARK_R = 0.85 * PX_PER_KM
const DOT_R = 0.8 * PX_PER_KM
const EDGE = 'rgba(8, 9, 12, 0.92)'
const LAKE_FILL = '#3f9fe0'
const LAKE_FILL_DIM = 'rgba(63, 159, 224, 0.5)'
const GOLD = 'rgb(244, 207, 106)'
const GOLD_DEEP = 'rgb(232, 185, 74)'
const HOT = 'rgb(255, 246, 220)'
// The ping (the Conclusion's drainage gesture, ConclusionReach.vue).
const FLASH = 0.55 // s the lake burns hot
const SETTLE = 1.1 // s its gold eases down after the flash
const BLOOM_E = 0.45 // s, the bloom's e-fold
const HALO_E = 0.8 // s, the wider halo's
const PING_SPREAD = 0.45 // s over which a day's lakes fire
const PING_END = PING_SPREAD + FLASH + SETTLE + 2.4 * HALO_E
const BLOOM_R = 2.3 * PX_PER_KM
const HALO_R = 4.2 * PX_PER_KM
let bloomImg: HTMLCanvasElement | null = null
let haloImg: HTMLCanvasElement | null = null
let bedImg: HTMLCanvasElement | null = null
function glow(stops: [number, string][]): HTMLCanvasElement {
  const el = document.createElement('canvas')
  el.width = el.height = 128
  const g = el.getContext('2d')!
  const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64)
  for (const [o, c] of stops) grad.addColorStop(o, c)
  g.fillStyle = grad
  g.fillRect(0, 0, 128, 128)
  return el
}

/** When the day on screen changed (ms), and the day it changed from. */
let pingT0 = -1
let pingFrom = -1
let paintRaf: number | null = null

function disc(g: CanvasRenderingContext2D, x: number, y: number, r: number): void {
  g.beginPath()
  g.arc(x, y, r, 0, Math.PI * 2)
}
function drawMark(g: CanvasRenderingContext2D, x: number, y: number, mark: Mark, a: number): void {
  if (mark === 'none' || a <= 0) return
  g.globalAlpha = a
  g.lineWidth = 3
  if (mark === 'lake' || mark === 'lake-drained') {
    disc(g, x, y, MARK_R)
    g.fillStyle = LAKE_FILL
    g.fill()
    g.strokeStyle = EDGE
    g.stroke()
    if (mark === 'lake-drained') {
      // water again today, but the paper drained it on an earlier day
      disc(g, x, y, MARK_R + 3.6)
      g.strokeStyle = GOLD
      g.lineWidth = 3.2
      g.stroke()
    }
  } else if (mark === 'gone') {
    // drained on an earlier day: the fainter gold — a soft gold fill
    // under a gold outline, on a dark bed so it stays gold on white ice
    disc(g, x, y, MARK_R)
    g.fillStyle = 'rgba(14, 11, 5, 0.6)'
    g.fill()
    g.globalAlpha = a * 0.5
    g.fillStyle = GOLD_DEEP
    g.fill()
    g.globalAlpha = a * 0.95
    g.strokeStyle = GOLD
    g.stroke()
  } else {
    disc(g, x, y, MARK_R)
    g.fillStyle = GOLD
    g.fill()
    g.strokeStyle = EDGE
    g.stroke()
  }
  g.globalAlpha = 1
}

function paint(now: number): boolean {
  const g = strip.getContext('2d')
  if (!g || !box) return false
  g.clearRect(0, 0, strip.width, strip.height)
  let animating = false
  if (view.value === 'lakes') {
    // every lake, quiet; the chosen one a gold dot
    for (const s of spots) {
      if (s.lake.id === selected.value) continue
      g.globalAlpha = 1
      disc(g, s.x, s.y, selected.value ? MARK_R * 0.5 : MARK_R * 0.8)
      g.fillStyle = selected.value ? LAKE_FILL_DIM : LAKE_FILL
      g.fill()
      g.lineWidth = 2
      g.strokeStyle = selected.value ? 'rgba(8, 9, 12, 0.6)' : EDGE
      g.stroke()
    }
    const s = spots.find((q) => q.lake.id === selected.value)
    if (s) {
      bedImg ??= glow([[0, 'rgba(0,0,0,0.55)'], [0.6, 'rgba(0,0,0,0.3)'], [1, 'rgba(0,0,0,0)']])
      g.drawImage(bedImg, s.x - DOT_R * 2.6, s.y - DOT_R * 2.6, DOT_R * 5.2, DOT_R * 5.2)
      disc(g, s.x, s.y, DOT_R * 1.8)
      g.lineWidth = 3.5
      g.strokeStyle = GOLD
      g.stroke()
      disc(g, s.x, s.y, DOT_R)
      g.fillStyle = GOLD
      g.fill()
      g.lineWidth = 3
      g.strokeStyle = EDGE
      g.stroke()
    }
  } else {
    const k = dayIdx.value
    const t = pingT0 < 0 ? Infinity : (now - pingT0) / 1000
    bloomImg ??= glow([[0, 'rgba(255, 246, 220, 0.98)'], [0.35, 'rgba(244, 207, 106, 0.6)'], [1, 'rgba(244, 207, 106, 0)']])
    haloImg ??= glow([[0, 'rgba(244, 207, 106, 0.6)'], [0.5, 'rgba(232, 185, 74, 0.26)'], [1, 'rgba(232, 185, 74, 0)']])
    bedImg ??= glow([[0, 'rgba(0,0,0,0.55)'], [0.6, 'rgba(0,0,0,0.3)'], [1, 'rgba(0,0,0,0)']])
    const fresh: typeof spots = []
    for (const s of spots) {
      const mark = markOf(s.lake, k)
      if (mark === 'fresh') fresh.push(s)
      else drawMark(g, s.x, s.y, mark, 1)
    }
    // the day's drainages, over everything else
    for (const s of fresh) {
      const tau = t - s.jitter
      if (tau < 0) {
        // not fired yet: as it stood on the day we came from
        drawMark(g, s.x, s.y, pingFrom >= 0 && pingFrom < k ? markOf(s.lake, pingFrom) : 'lake', 1)
        animating = true
        continue
      }
      const hA = Math.exp(-tau / HALO_E)
      const bA = Math.exp(-tau / BLOOM_E)
      if (hA > 0.012) {
        animating = true
        // a dark bed first: gold cannot glow on white ice
        g.globalAlpha = Math.min(1, hA * 1.2)
        g.drawImage(bedImg, s.x - HALO_R, s.y - HALO_R, 2 * HALO_R, 2 * HALO_R)
        g.globalAlpha = hA
        g.drawImage(haloImg, s.x - HALO_R, s.y - HALO_R, 2 * HALO_R, 2 * HALO_R)
      }
      if (bA > 0.012) {
        g.globalAlpha = Math.min(1, bA * 1.15)
        g.drawImage(bloomImg, s.x - BLOOM_R, s.y - BLOOM_R, 2 * BLOOM_R, 2 * BLOOM_R)
      }
      g.globalAlpha = 1
      // the lake itself: swollen and hot in the flash, then gold
      const pop = tau < FLASH ? 1 + 0.55 * (1 - tau / FLASH) : 1
      disc(g, s.x, s.y, MARK_R * pop)
      g.fillStyle = GOLD
      g.fill()
      if (tau < FLASH) {
        g.globalAlpha = 1 - tau / FLASH
        g.fillStyle = HOT
        g.fill()
        g.globalAlpha = 1
      }
      g.lineWidth = 3
      g.strokeStyle = EDGE
      g.stroke()
    }
    if (t < PING_END && fresh.length) animating = true
  }
  g.globalAlpha = 1
  stripVersion += 1
  emit('lake-strip', { canvas: strip, ...box, opacity: 1, version: stripVersion, surface: true })
  return animating
}
/** Paint now; keep painting while a ping is in flight. */
function repaint(): void {
  if (paintRaf !== null) return
  const step = (now: number): void => {
    paintRaf = null
    if (!alive) return
    if (paint(now)) paintRaf = window.requestAnimationFrame(step)
  }
  paintRaf = window.requestAnimationFrame(step)
}

/** Put day `i` on screen; its drainages ping. */
function showDay(i: number): void {
  const n = days.value.length
  if (!n) return
  const k = Math.max(0, Math.min(n - 1, i))
  pingFrom = k === dayIdx.value ? -1 : dayIdx.value
  dayIdx.value = k
  pingT0 = performance.now()
  repaint()
  syncUrl()
}

// ── the camera ────────────────────────────────────────────────────────
// From the coast looking inland: the camera stands far to the west, low
// (≈ 22° above the horizon at the lakes), and looks east — the ice-free
// land in the foreground, the ice sheet rising behind it. (The
// Introduction's coupling step stands on the ice and looks west to the
// coast.) A long lens: the lake area is ~50 × 64 km.
const CAM = { lat: 67.1, lon: -62.8, distance: 0.5249 }
/** The cascade: the whole lake area, a little above mid-height so the
 *  coast shows under it and the slider covers no lake. */
const CASCADE_FOV = 6.3
const CASCADE_AT = { x: 0.5, y: 0.46 }
/** One lake: closer on the same line of sight. */
const LAKE_FOV = 3.3
/** The dome calmed to ~25× (the coupling step's is ~50×): at this low
 *  angle a taller dome turns the ice into a wall facing the camera. */
let EXAG = 0.007
const SURF_MAX_M = 3500 // Globe.vue's DEM range
const GLOBE_R = 0.5
/** The Globe shifts its projection so a focal lands at this share of the
 *  width (Globe.vue TARGET_VIEW_SHIFT 0.30 → (1 − 0.30) / 2). */
const FOCAL_X = 0.35
/** Greenland's radial at 72 °N 40 °W — the Globe's default camera up. */
const UP0 = unit(72, -40)

type V3 = [number, number, number]
function unit(latDeg: number, lonDeg: number): V3 {
  const la = (latDeg * Math.PI) / 180
  const lo = (lonDeg * Math.PI) / 180
  return [Math.cos(la) * Math.cos(lo), Math.cos(la) * Math.sin(lo), Math.sin(la)]
}
const sub = (a: V3, b: V3): V3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
const add = (a: V3, b: V3): V3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]]
const mul = (a: V3, k: number): V3 => [a[0] * k, a[1] * k, a[2] * k]
const len = (a: V3): number => Math.hypot(a[0], a[1], a[2])
const norm = (a: V3): V3 => mul(a, 1 / (len(a) || 1))
const cross = (a: V3, b: V3): V3 => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]

/** The surface elevation here, good enough to aim before the DEM is in:
 *  the K-transect's slope (S6 1020 m at 49.38 °W, S9 1520 m at 48.25 °W). */
function elevGuess(lon: number): number {
  return Math.max(300, 1020 + (lon + 49.38) * 450)
}

/**
 * The focal that puts a point on the ice at (fx, fy) of the viewport: the
 * Globe aims its focal at FOCAL_X × the width, mid-height, so the focal is
 * the point moved by the opposite screen offset, in the camera's own
 * right / up directions at that distance.
 */
function focalFor(lat: number, lon: number, fov: number, fx: number, fy: number): { lat: number; lon: number } {
  const w = window.innerWidth
  const h = window.innerHeight
  const cam = mul(unit(CAM.lat, CAM.lon), CAM.distance)
  const p = mul(unit(lat, lon), GLOBE_R + (elevGuess(lon) / SURF_MAX_M) * EXAG)
  const fwd = norm(sub(p, cam))
  const right = norm(cross(fwd, UP0))
  const up = cross(right, fwd)
  // world units per px at the point's distance
  const perPx = (2 * len(sub(p, cam)) * Math.tan(((fov / 2) * Math.PI) / 180)) / h
  const dx = (fx - FOCAL_X) * w * perPx
  const dy = (fy - 0.5) * h * perPx
  const f = add(add(p, mul(right, -dx)), mul(up, dy))
  const n = norm(f)
  return { lat: (Math.asin(n[2]) * 180) / Math.PI, lon: (Math.atan2(n[1], n[0]) * 180) / Math.PI }
}

function demReady(): boolean {
  const w = window as unknown as { __texturesStarted?: number; __texturesPending?: number }
  return (w.__texturesStarted ?? 0) > 0 && (w.__texturesPending ?? 1) === 0
}
let reaimTimer: number | null = null
let aimed: { lake: string | null } | null = null
/** Fly to the cascade, or to one lake (left of the player). */
function aim(durationMs: number): void {
  const m = manifest.value
  if (!m) return
  const lake = view.value === 'lakes' ? selectedLake.value : null
  const b = m.lake_bbox
  const target = lake
    ? { lat: lake.lat, lon: lake.lon, fov: LAKE_FOV, fx: LAKE_AT.x, fy: LAKE_AT.y }
    : { lat: (b.south + b.north) / 2, lon: (b.west + b.east) / 2, fov: CASCADE_FOV, fx: CASCADE_AT.x, fy: CASCADE_AT.y }
  const f = focalFor(target.lat, target.lon, target.fov, target.fx, target.fy)
  const ready = demReady()
  emit('chapter-focus', {
    lat: f.lat,
    lon: f.lon,
    cameraLat: CAM.lat,
    cameraLon: CAM.lon,
    distance: CAM.distance,
    fovDeg: target.fov,
    durationMs,
    focalExag: EXAG,
    // The telephoto needs the focal ON the displaced surface. Until the DEM
    // readback is in (a cold deep link) a regional guess stands in, and the
    // aim is repeated once the surface is known.
    ...(ready ? { focalOnSurface: true } : { focalElevM: elevGuess(f.lon) }),
  })
  aimed = { lake: lake?.id ?? null }
  if (reaimTimer !== null) window.clearInterval(reaimTimer)
  reaimTimer = null
  if (!ready) {
    reaimTimer = window.setInterval(() => {
      if (!demReady()) return
      window.clearInterval(reaimTimer!)
      reaimTimer = null
      aim(600)
    }, 400)
  }
}
/** Where a chosen lake's dot sits on screen: the middle of the ice left of the player. */
const LAKE_AT = { x: 0.17, y: 0.56 }
const FLY_MS = 1700
function onResize(): void {
  if (aimed) aim(300)
}

// ── VIEW B: the grid, the fall, the player ────────────────────────────
const groups = computed(() => {
  const m = manifest.value
  if (!m) return []
  return [
    { key: 'drained', label: 'Drained in the paper', lakes: m.lakes.filter((l) => l.drained_days.length > 0) },
    { key: 'never', label: 'Not drained in the paper', lakes: m.lakes.filter((l) => l.drained_days.length === 0) },
  ].filter((g) => g.lakes.length)
})
/** A lake's picture: the chosen year's, else 2010's (2019 is still baking). */
function thumbOf(l: C18Lake): string | null {
  const y = l.thumbs[year.value] ? year.value : l.thumbs['2010'] ? '2010' : l.thumbs['2019'] ? '2019' : null
  return y ? revisitUrl(`thumbs/${y}/${l.id}.jpg`) : null
}
/** Each card's own fall: a little late, a little turned (fixed per card). */
function fallStyle(id: string, i: number): Record<string, string> {
  let h = 0
  for (let k = 0; k < id.length; k++) h = (h * 31 + id.charCodeAt(k)) >>> 0
  const r = (h % 1000) / 1000
  return {
    '--fall-delay': `${Math.round((i % 5) * 28 + r * 170)}ms`,
    '--fall-rot': `${((r - 0.5) * 22).toFixed(1)}deg`,
    '--fall-x': `${(((h >> 10) % 1000) / 1000 - 0.5) * 60}px`,
  }
}

const scrollEl = ref<HTMLElement | null>(null)
const ghostEl = ref<HTMLImageElement | null>(null)
const ghost = ref<{ src: string; style: Record<string, string> } | null>(null)
/** The player is mounted (it fades in as the cards fall). */
const playerOn = ref(false)
/** The card a closing player's picture is flying back to (kept hidden till it lands). */
const homing = ref<string | null>(null)
const GHOST_MS = 620

function cardThumbRect(id: string): DOMRect | null {
  return scrollEl.value?.querySelector<HTMLElement>(`.rv-card[data-lake="${id}"] .rv-thumb`)?.getBoundingClientRect() ?? null
}
/** The player's frame the card's picture belongs to: the high-resolution
 *  one (the pictures are that track's), else whichever is up. */
function playerFrame(): HTMLElement | null {
  return (
    document.querySelector<HTMLElement>('.rv-player .rvp-frame[data-sensor="hires"]') ??
    document.querySelector<HTMLElement>('.rv-player .rvp-frame')
  )
}
function playerFrameRect(): DOMRect | null {
  return playerFrame()?.getBoundingClientRect() ?? null
}
/** The frame's movie has painted (or it has none, or 1.6 s have passed). */
async function frameShown(): Promise<void> {
  const t0 = performance.now()
  while (alive && performance.now() - t0 < 1600) {
    const f = playerFrame()
    if (!f || f.querySelector('.rvp-plate') || f.querySelector('.rvp-video.ready')) return
    await new Promise((r) => window.setTimeout(r, 60))
  }
}
/** Fly the picture between two rects; resolves when it has landed (and,
 *  with `dissolve`, has given way to the movie under it). */
async function flyGhost(src: string, from: DOMRect, to: DOMRect, dissolve: boolean): Promise<void> {
  ghost.value = {
    src,
    style: { left: `${to.left}px`, top: `${to.top}px`, width: `${to.width}px`, height: `${to.height}px` },
  }
  await nextTick()
  const el = ghostEl.value
  if (!el) {
    ghost.value = null
    return
  }
  const sx = from.width / to.width
  const sy = from.height / to.height
  const anim = el.animate(
    [
      { transform: `translate(${from.left - to.left}px, ${from.top - to.top}px) scale(${sx}, ${sy})` },
      { transform: 'translate(0, 0) scale(1)' },
    ],
    { duration: GHOST_MS, easing: 'cubic-bezier(0.4, 0, 0.2, 1)', fill: 'both' },
  )
  await anim.finished.catch(() => undefined)
  if (dissolve) {
    await frameShown()
    if (ghostEl.value === el) {
      await el.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 260, easing: 'ease', fill: 'forwards' }).finished.catch(() => undefined)
    }
  }
  if (ghostEl.value === el || !ghostEl.value) ghost.value = null
}

async function openLake(id: string, e?: MouseEvent): Promise<void> {
  ;(e?.currentTarget as HTMLElement | null)?.blur()
  const m = manifest.value
  const lake = m?.lakes.find((l) => l.id === id)
  if (!lake || selected.value) return
  const from = cardThumbRect(id)
  selected.value = id
  playerOn.value = true
  repaint()
  aim(FLY_MS)
  syncUrl()
  // the card's picture grows into the player's frame
  await nextTick()
  const to = playerFrameRect()
  const src = thumbOf(lake)
  if (from && to && src) void flyGhost(src, from, to, true)
}
async function closeLake(): Promise<void> {
  const id = selected.value
  const lake = selectedLake.value
  if (!id || !lake) return
  const from = playerFrameRect()
  const to = cardThumbRect(id)
  const src = thumbOf(lake)
  // the player leaves; its picture flies home, then the cards come back
  playerOn.value = false
  homing.value = id
  selected.value = null
  repaint()
  aim(FLY_MS)
  syncUrl()
  if (from && to && src) await flyGhost(src, from, to, false)
  homing.value = null
}

function setView(v: View): void {
  if (view.value === v) return
  playing.value = false
  clearPlay()
  if (v === 'cascade') {
    selected.value = null
    playerOn.value = false
    homing.value = null
    ghost.value = null
  }
  view.value = v
  pingT0 = -1
  repaint()
  aim(v === 'cascade' ? FLY_MS : 900)
  syncUrl()
}

// ── the site's NEXT / BACK (Explore routes them here while we say so) ─
// NEXT: the paper's next map, and after its last, every lake. BACK: the
// player closes, the grid returns to the cascade, the maps step back — and
// on the first map BACK is the site's own (where the door was used from).
const navState = computed(() => ({
  next: view.value === 'cascade',
  back: view.value === 'lakes' || prevObs.value !== null,
}))
watch(navState, (s) => emit('nav-state', s), { immediate: true })
watch(
  () => props.advanceTrigger,
  (v, old) => {
    if (v == null || v === old || view.value !== 'cascade' || !manifest.value) return
    playing.value = false
    clearPlay()
    if (nextObs.value !== null) showDay(nextObs.value)
    else setView('lakes')
  },
)
watch(
  () => props.backTrigger,
  (v, old) => {
    if (v == null || v === old) return
    if (view.value === 'lakes') {
      if (selected.value) void closeLake()
      else setView('cascade')
      return
    }
    playing.value = false
    clearPlay()
    if (prevObs.value !== null) showDay(prevObs.value)
  },
)

// ── the URL carries the state (a reload, a shared link) ───────────────
function syncUrl(): void {
  const q: LocationQueryRaw = {}
  if (view.value === 'lakes') {
    q.view = 'lakes'
    if (selected.value) {
      q.lake = selected.value
      q.year = year.value
      q.sensor = mode.value
    }
  } else if (today.value && dayIdx.value > 0) {
    q.day = today.value.iso
  }
  const cur = route.query
  const keys = new Set([...Object.keys(q), ...Object.keys(cur)])
  let same = true
  for (const k of keys) if (String(q[k] ?? '') !== String(cur[k] ?? '')) same = false
  if (!same) void router.replace({ query: q }).catch(() => undefined)
}
watch([year, mode], syncUrl)

// Buttons give the focus back, so the site's keys (the presenter remote)
// never land on one.
function pick(e: MouseEvent, fn: () => void): void {
  ;(e.currentTarget as HTMLElement | null)?.blur()
  fn()
}

async function loadManifest(): Promise<C18Manifest | null> {
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const r = await fetch(revisitUrl(REVISIT_MANIFEST), { priority: 'high' } as RequestInit)
      if (r.ok) return (await r.json()) as C18Manifest
    } catch {
      // once more
    }
  }
  console.warn('[revisit] c18_lakes.json failed to load')
  return null
}

onMounted(async () => {
  // The Globe: the satellite basemap (no speed paint), the dome calmed
  // for a close oblique view, full relief shading.
  emit('globe-clicks', 1)
  emit('hillshade', null)
  emit('chapter-exag-ms', 1500)
  emit('chapter-exag', EXAG)
  window.addEventListener('resize', onResize)
  if (import.meta.env.DEV) {
    // framing hook for the tools: __revisitAim({lat, lon, distance}, cascadeFov)
    ;(window as unknown as Record<string, unknown>).__revisitAim = (c: Partial<typeof CAM>, fov?: number, exag?: number, fy = 0.5) => {
      Object.assign(CAM, c)
      if (exag !== undefined) {
        EXAG = exag
        emit('chapter-exag-ms', 200)
        emit('chapter-exag', EXAG)
      }
      const m = manifest.value
      if (!m) return
      const b = m.lake_bbox
      const f = focalFor((b.south + b.north) / 2, (b.west + b.east) / 2, fov ?? CASCADE_FOV, 0.5, fy)
      emit('chapter-focus', { lat: f.lat, lon: f.lon, cameraLat: CAM.lat, cameraLon: CAM.lon, distance: CAM.distance, fovDeg: fov ?? CASCADE_FOV, durationMs: 300, focalExag: EXAG, focalOnSurface: true })
    }
  }
  const m = await loadManifest()
  if (!alive || !m) return
  manifest.value = m
  layoutStrip(m)
  // deep links
  const q = route.query
  const str = (v: unknown): string | null => (typeof v === 'string' ? v : null)
  const qYear = str(q.year)
  if (qYear && (REVISIT_YEARS as string[]).includes(qYear)) year.value = qYear as RevisitYear
  const qMode = str(q.sensor)
  if (qMode && (REVISIT_MODES as string[]).includes(qMode)) mode.value = qMode as RevisitMode
  const qLake = str(q.lake)
  const qDay = str(q.day)
  if (qDay) {
    const i = days.value.findIndex((d) => d.iso === qDay)
    if (i >= 0) dayIdx.value = i
  }
  if (qLake && m.lakes.some((l) => l.id === qLake)) {
    view.value = 'lakes'
    selected.value = qLake
    playerOn.value = true
  } else if (q.view === 'lakes') {
    view.value = 'lakes'
  }
  pingT0 = performance.now() + 1500 // the day's drainages ping once the camera is nearly there
  repaint()
  aim(2200)
  if (selected.value) {
    // bring the chosen card into the (hidden) grid's view, for the way back
    await nextTick()
    scrollEl.value?.querySelector<HTMLElement>(`.rv-card[data-lake="${selected.value}"]`)?.scrollIntoView({ block: 'center' })
  }
})

onBeforeUnmount(() => {
  alive = false
  clearPlay()
  if (reaimTimer !== null) window.clearInterval(reaimTimer)
  if (paintRaf !== null) window.cancelAnimationFrame(paintRaf)
  window.removeEventListener('resize', onResize)
  emit('nav-state', { next: false, back: false })
  emit('lake-strip', null)
  emit('hillshade', null)
  emit('chapter-exag-ms', 1500)
  // Explore drops these two when the next page frames itself.
  emit('chapter-exag', null)
  emit('chapter-focus', null)
  emit('globe-clicks', 1)
})
</script>

<style scoped>
/* A full-screen, click-through layer above the live Globe: only its
   controls take the mouse. */
.rv {
  position: fixed;
  inset: 0;
  z-index: 6;
  pointer-events: none;
  color: #f5f0e6;
  font-family: 'Inter', system-ui, sans-serif;
  /* under the ribbon and the BACK / NEXT pills (they drop a row under 1680 px) */
  --top: calc(1.2vh + 2.92rem + 0.3rem + 2rem + 0.9rem);
}
.rv-a,
.rv-b {
  position: absolute;
  inset: 0;
}

.rv-fade-enter-active,
.rv-fade-leave-active {
  transition: opacity 0.45s ease;
}
.rv-fade-enter-from,
.rv-fade-leave-to {
  opacity: 0;
}

/* ───────────── VIEW A ───────────── */
/* the day and the paper's count for it */
.rv-stamp {
  position: absolute;
  left: 22px;
  top: var(--top);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
  min-width: 13rem;
  padding: 0.6rem 1.1rem 0.7rem;
  border-radius: 0.7rem;
  background: rgba(6, 7, 10, 0.82);
  border: 1.5px solid rgba(244, 207, 106, 0.7);
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.55);
}
.rv-stamp-date {
  font-size: 1.15rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: var(--gold-bright);
}
.rv-stamp-date i {
  font-style: normal;
  font-weight: 500;
  color: rgba(245, 240, 230, 0.9);
}
.rv-stamp-big {
  font-family: 'EB Garamond', serif;
  font-size: clamp(2.4rem, 3.4vw, 3.4rem);
  font-weight: 600;
  line-height: 1;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--gold-bright);
  font-variant-numeric: tabular-nums;
}
.rv-stamp-small {
  font-size: 1.15rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #8fd0ff;
}
.rv-stamp-cloud {
  border-color: rgba(214, 222, 235, 0.7);
}
.rv-stamp-cloud .rv-stamp-big {
  color: #dfe6f0;
}

.rv-legend {
  position: absolute;
  left: 22px;
  bottom: calc(2.2vh + 2.6rem);
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding: 0.6rem 0.95rem 0.65rem;
  border-radius: 0.7rem;
  background: rgba(6, 7, 10, 0.82);
  border: 1.5px solid rgba(232, 185, 74, 0.4);
}
.rv-leg {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
}
.rv-dot {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  flex: none;
}
.rv-dot-fresh {
  background: var(--gold-bright);
  box-shadow: 0 0 9px 2px rgba(244, 207, 106, 0.7);
}
.rv-dot-gone {
  background: #8a6f33;
  border: 2px solid rgba(244, 207, 106, 0.95);
}
.rv-dot-lake {
  background: #3f9fe0;
}
.rv-dot-again {
  box-shadow: 0 0 0 1.5px #06070a, 0 0 0 3.5px var(--gold-bright);
}

/* the time slider: play, the six days, the cloud band */
.rv-time {
  position: absolute;
  left: 50%;
  bottom: 2.2vh;
  transform: translateX(-50%);
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 0.75rem 1.6rem 0.45rem 1rem;
  border-radius: 1.6rem;
  background: rgba(6, 7, 10, 0.84);
  border: 1.5px solid rgba(232, 185, 74, 0.55);
  box-shadow: 0 4px 22px rgba(0, 0, 0, 0.5);
  pointer-events: auto;
}
.rv-play {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  flex: none;
  padding: 0;
  border-radius: 50%;
  border: 1.5px solid var(--gold);
  background: rgba(56, 38, 12, 0.6);
  color: var(--gold-bright);
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}
.rv-play:hover {
  background: rgba(96, 66, 18, 0.85);
  color: #fff8d8;
}
.rv-slider {
  --thumb: 22px;
  position: relative;
  width: clamp(22rem, 34vw, 32rem);
  height: 4.5rem;
}
.rv-range {
  position: absolute;
  left: 0;
  top: 2px;
  width: 100%;
  -webkit-appearance: none;
  appearance: none;
  height: 24px;
  margin: 0;
  background: transparent;
  cursor: pointer;
}
.rv-range:focus {
  outline: none;
}
.rv-range::-webkit-slider-runnable-track {
  height: 6px;
  border-radius: 3px;
  background: linear-gradient(
    to right,
    var(--gold) 0,
    var(--gold) var(--fill),
    rgba(245, 240, 230, 0.32) var(--fill),
    rgba(245, 240, 230, 0.32) 100%
  );
}
.rv-range::-moz-range-track {
  height: 6px;
  border-radius: 3px;
  background: rgba(245, 240, 230, 0.32);
}
.rv-range::-moz-range-progress {
  height: 6px;
  border-radius: 3px;
  background: var(--gold);
}
.rv-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: var(--thumb);
  height: var(--thumb);
  margin-top: -8px;
  border-radius: 50%;
  background: #fff8d8;
  border: 3px solid #0d0b09;
  box-shadow: 0 0 0 2px var(--gold-bright);
}
.rv-range::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff8d8;
  border: 3px solid #0d0b09;
  box-shadow: 0 0 0 2px var(--gold-bright);
}
/* the paper's cloud days: a hatched band behind the track */
.rv-cloud {
  position: absolute;
  top: -3px;
  height: 34px;
  border-radius: 6px;
  background: repeating-linear-gradient(135deg, rgba(214, 222, 235, 0.34) 0 5px, rgba(214, 222, 235, 0.14) 5px 10px);
  pointer-events: none;
}
.rv-cloud i {
  position: absolute;
  left: 50%;
  top: calc(3.15rem + 3px);
  transform: translateX(-50%);
  font-style: normal;
  font-size: 0.95rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #dfe6f0;
}
.rv-stop {
  position: absolute;
  top: 1.85rem;
  transform: translateX(-50%);
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  white-space: nowrap;
  color: #f5f0e6;
  pointer-events: none;
  font-variant-numeric: tabular-nums;
}
.rv-stop-cloud {
  color: #c9d2df;
}
.rv-stop-on {
  color: var(--gold-bright);
  font-weight: 700;
}

.rv-cite {
  position: absolute;
  left: 22px;
  bottom: 2.2vh;
  pointer-events: auto;
  padding: 0.2rem 0.6rem;
  border-radius: 0.5rem;
  background: rgba(6, 7, 10, 0.72);
  font-size: 1.05rem;
  letter-spacing: 0.04em;
  color: var(--accent);
  text-decoration: none;
}
.rv-cite:hover {
  color: #fff;
}

/* bottom-right: the door to every lake (the site's lit pill) */
.rv-door,
.rv-back {
  pointer-events: auto;
  font-family: inherit;
  font-size: 0.98rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  white-space: nowrap;
  padding: 0.75rem 1.2rem;
  border-radius: 999px;
  color: var(--gold-bright);
  border: 1.5px solid rgba(232, 185, 74, 0.85);
  background: rgba(8, 6, 4, 0.8);
  cursor: pointer;
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.55), 0 0 22px rgba(245, 199, 94, 0.18);
  transition: color 0.2s, border-color 0.2s, background 0.2s;
}
.rv-door {
  position: absolute;
  right: 22px;
  bottom: 22px;
}
.rv-door:hover,
.rv-back:hover {
  color: #fff8d8;
  border-color: var(--gold-bright);
  background: rgba(56, 38, 12, 0.88);
}
.rv-door-arrow {
  display: inline-block;
  margin-left: 0.2rem;
  transition: transform 0.2s;
}
.rv-door:hover .rv-door-arrow {
  transform: translateX(3px);
}

/* ───────────── VIEW B ───────────── */
.rv-gauze {
  position: absolute;
  inset: 0;
  background: rgba(3, 4, 7, 0.74);
  transition: background 0.7s ease;
  pointer-events: none;
}
/* a lake is chosen: the ice comes back on the left, the player's side stays dark */
.rv-has-lake .rv-gauze {
  background: linear-gradient(to right, rgba(3, 4, 7, 0) 0, rgba(3, 4, 7, 0) 29%, rgba(3, 4, 7, 0.95) 37%, rgba(3, 4, 7, 0.975) 100%);
}
/* level with the site's BACK / NEXT, at the other end of their row */
.rv-back {
  position: absolute;
  left: 22px;
  top: calc(1.2vh + 2.92rem + 0.3rem);
  height: 2rem;
  z-index: 3;
  padding: 0 1.05rem;
  font-size: 0.9rem;
}

/* … and beside it the year of the grid's pictures (the player's toggle) */
.rv-year {
  position: absolute;
  left: 13.2rem;
  top: calc(1.2vh + 2.92rem + 0.3rem);
  height: 2rem;
  z-index: 3;
  display: inline-flex;
  align-items: center;
  gap: 0.15rem;
  padding: 0 0.2rem;
  border: 1.5px solid rgba(232, 185, 74, 0.6);
  border-radius: 999px;
  background: rgba(8, 7, 6, 0.84);
  pointer-events: auto;
}
.rv-year-btn {
  height: 1.5rem;
  padding: 0 0.8rem;
  background: transparent;
  border: none;
  border-radius: 999px;
  color: rgba(244, 207, 106, 0.95);
  font-family: inherit;
  font-size: 0.92rem;
  font-weight: 600;
  letter-spacing: 0.09em;
  cursor: pointer;
  transition: color 0.2s, background 0.2s;
}
.rv-year-btn:hover {
  color: #fff8d8;
}
.rv-year-btn--on,
.rv-year-btn--on:hover {
  color: #0a0a0a;
  background: var(--gold-bright);
}

.rv-scroll {
  position: absolute;
  inset: var(--top) 0 0 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  padding: 0 3vw 5vh;
  pointer-events: auto;
}
.rv-scroll.rv-falling {
  overflow: hidden;
  pointer-events: none;
}
.rv-group {
  margin: 0.2rem 0 0.8rem;
  /* clear of the back pill on the first row */
  min-height: 2.4rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.05rem;
  font-weight: 600;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--gold-bright);
  transition: opacity 0.4s;
}
.rv-grid + .rv-group {
  margin-top: 2.2rem;
}
.rv-falling .rv-group {
  opacity: 0;
}
/* five across, as many rows as it takes */
.rv-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 1.1rem;
  max-width: 1560px;
  margin: 0 auto;
}
.rv-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 0;
  border: 1.5px solid rgba(232, 185, 74, 0.55);
  border-radius: 12px;
  overflow: hidden;
  background: #060709;
  color: inherit;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  /* the way back: each card rises to its place */
  transition:
    transform 0.6s cubic-bezier(0.2, 0.7, 0.2, 1) var(--fall-delay),
    opacity 0.35s ease var(--fall-delay),
    border-color 0.25s,
    box-shadow 0.25s;
}
/* (no lift on hover: the transform is the fall's and the return's) */
.rv-card:hover,
.rv-card:focus-visible {
  border-color: var(--gold-bright);
  box-shadow: 0 0 0 1.5px var(--gold-bright), 0 10px 30px -8px rgba(232, 185, 74, 0.6);
  outline: none;
}
/* a lake is chosen: the others fall away */
.rv-falling .rv-card {
  transform: translate(var(--fall-x), 115vh) rotate(var(--fall-rot));
  opacity: 0;
  transition:
    transform 1.05s cubic-bezier(0.55, 0, 0.9, 0.6) var(--fall-delay),
    opacity 0.35s ease calc(var(--fall-delay) + 0.7s);
}
/* … and the chosen one is in the player (its picture flies there) */
.rv-falling .rv-card.rv-card-chosen,
.rv-card.rv-card-home {
  transform: none;
  opacity: 0;
  transition: none;
}
.rv-thumb {
  position: relative;
  display: block;
  width: 100%;
  aspect-ratio: 1;
  background: #0b0c10;
}
.rv-thumb img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.rv-card-id {
  position: absolute;
  left: 8px;
  bottom: 8px;
  padding: 2px 10px 3px;
  border-radius: 999px;
  background: rgba(6, 7, 10, 0.84);
  font-family: 'EB Garamond', serif;
  font-size: 1.25rem;
  font-weight: 500;
  letter-spacing: 0.03em;
  color: var(--gold-bright);
}
.rv-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  min-height: 2.5rem;
  padding: 0.45rem 0.5rem 0.5rem;
  align-items: center;
}
.rv-chip {
  font-style: normal;
  padding: 0.12rem 0.5rem;
  border-radius: 999px;
  border: 1.5px solid rgba(244, 207, 106, 0.9);
  background: rgba(244, 207, 106, 0.14);
  color: var(--gold-bright);
  font-size: 0.92rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  white-space: nowrap;
}

/* the player: the right of the screen; the lake's dot rides the ice on the left */
.rv-player {
  --rvp-top: var(--top);
  position: absolute;
  right: 2vw;
  top: var(--top);
  width: 61vw;
  pointer-events: auto;
}
.rv-player-enter-active {
  transition: opacity 0.45s ease 0.3s;
}
.rv-player-leave-active {
  transition: opacity 0.2s ease;
}
.rv-player-enter-from,
.rv-player-leave-to {
  opacity: 0;
}
.rv-ghost {
  position: fixed;
  z-index: 4;
  transform-origin: 0 0;
  border-radius: 10px;
  object-fit: cover;
  pointer-events: none;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6);
}
</style>
