<template>
  <!-- The 2023 fieldwork ride-along map,
       grown from SectionExtras: a Sentinel-2 crop in local-tangent metres
       with the helicopter GPX tracks drawn on it; click a track → its
       GoPro clip plays with the marker + camera wedge riding the track;
       wheel zooms about the cursor, drag pans. `initialView` is the
       viewBox the parent measured off the Globe's landing frame, so the
       map takes over the 3-D frame pixel-for-pixel; `revealed` fades the
       whole layer; `clip` (the Introduction's clip steps) opens that clip
       from its start as a click would. An opaque layer ABOVE the live
       Globe — never a veil. No prose (narrator rule): the only text is
       the clip id + date. -->
  <div
    class="fw-stage"
    :class="{ revealed: revealed && imgLoaded, 'fw-intro': mode === 'intro', panning: isPanning }"
    :style="wide ? { '--day': dayColor } : undefined"
    @wheel.prevent="onWheel"
    @mousedown="onPanStart"
    @transitionend.self="onStageTransitionEnd"
  >
    <svg ref="svgEl" class="fw-map" :viewBox="viewBox" preserveAspectRatio="none">
      <!-- Full mode (the door page): the whole flying day at 20 m beneath the
           10 m detail crop, same frame, so the detail simply sits on top
           over the flight area. Absent in the Introduction on purpose. -->
      <image
        v-if="wide"
        :href="wideSrc"
        :x="FW_WIDE_X0"
        :y="FW_WIDE_Y0"
        :width="FW_WIDE_X1 - FW_WIDE_X0"
        :height="FW_WIDE_Y1 - FW_WIDE_Y0"
        preserveAspectRatio="none"
      />
      <image
        :href="src ?? undefined"
        :x="-FW_HALF_X_M"
        :y="-FW_HALF_Y_M"
        :width="2 * FW_HALF_X_M"
        :height="2 * FW_HALF_Y_M"
        preserveAspectRatio="none"
      />
      <!-- Full mode: each day's helicopter route (handheld GPS) and the
           station landings, faint, beneath the clip tracks. The only text
           is the station id. -->
      <g v-if="wide" class="fw-day" :class="{ shown: tracksShown }">
        <template v-for="d in visibleDays" :key="d.date">
          <polyline v-if="showRoute && dayLines[d.date]" :points="dayLines[d.date]" class="day-line-outline" />
          <polyline v-if="showRoute && dayLines[d.date]" :points="dayLines[d.date]" class="day-line" :style="{ '--track': d.color }" />
        </template>
        <g v-for="st in visibleStations" :key="st.name" class="station">
          <circle :cx="st.x" :cy="st.y" :r="markerDotR * 0.42" class="station-dot" />
          <text
            :x="st.x + markerDotR * 0.9"
            :y="st.y - markerDotR * 0.7"
            :font-size="markerDotR * 1.6"
            class="station-label"
          >{{ st.label }}</text>
        </g>
      </g>
      <g class="fw-tracks" :class="{ shown: tracksShown }">
        <g
          v-for="t in visibleTracks"
          :key="t.id"
          :class="['track-group', { active: t.id === selectedId, dimmed: selectedId && t.id !== selectedId }]"
          :style="wide ? { '--track': t.color } : undefined"
          :data-id="t.id"
          @click="onTrackClick(t, $event)"
        >
          <polyline :points="t.svgPoints" class="track-line-glow" />
          <polyline :points="t.svgPoints" class="track-line-outline" />
          <polyline :points="t.svgPoints" class="track-line" />
        </g>
        <template v-if="markerPos">
          <!-- The camera wedge: a black edge under a dark, saturated fill
               with the day's colour as its rim (the director found it
               washed out over bright ice), and the same black ring under
               the marker — so both stand off bright snow and dark water. -->
          <path v-if="sectorPath" :d="sectorPath" class="marker-sector-edge" />
          <path v-if="sectorPath" :d="sectorPath" class="marker-sector" />
          <circle :cx="markerPos.x" :cy="markerPos.y" :r="markerDotR" class="marker-dot-edge" />
          <circle
            :cx="markerPos.x"
            :cy="markerPos.y"
            :r="markerDotR"
            :class="['marker-dot', { dragging: isDragging }]"
            @mousedown="onMarkerMouseDown"
            @touchstart.passive="onMarkerTouchStart"
          />
        </template>
      </g>
    </svg>

    <!-- Full page (Additional Work door): the way back to the cards. -->
    <button v-if="mode === 'full'" class="fw-exit" @click="emit('exit')">← doors</button>

    <!-- Minimap: where on Greenland this is. -->
    <div class="minimap">
      <div class="silhouette" :style="{ '--silhouette-url': `url(${silhouetteUrl})` }" />
      <div class="minimap-aoi-halo" />
      <div class="minimap-aoi-dot" />
    </div>

    <!-- Full mode: the legend — which day's tracks, which layers, which
         Sentinel-2 pass. Labels are the data (dates, layer names). -->
    <div v-if="wide" class="fw-legend" @mousedown.stop @wheel.stop>
      <div class="lg-row">
        <button
          v-for="d in FW_DAYS"
          :key="d.date"
          class="lg-btn"
          :class="{ on: selectedDay === d.date }"
          :style="{ '--sw': d.color }"
          @click="pickDay(d.date)"
        ><i class="sw" />{{ d.label }}</button>
        <button class="lg-btn" :class="{ on: selectedDay === 'all' }" @click="pickDay('all')"><i class="sw sw-all" />Both days</button>
      </div>
      <div class="lg-row">
        <button class="lg-btn lg-layer" :class="{ on: showRoute }" @click="showRoute = !showRoute"><i class="sw sw-route" />Helicopter route</button>
        <button class="lg-btn lg-layer" :class="{ on: showClips }" @click="showClips = !showClips"><i class="sw sw-clip" />GoPro clips</button>
        <button class="lg-btn lg-layer" :class="{ on: showStations }" @click="showStations = !showStations"><i class="sw sw-station" />GNSS stations</button>
      </div>
      <div class="lg-row lg-imagery">
        <span class="lg-k">Sentinel-2</span>
        <button
          v-for="im in FW_IMAGERY"
          :key="im.date"
          class="lg-btn lg-pass"
          :class="{ on: imagery.date === im.date, gap: !!im.gap }"
          :title="im.gap === 'array' ? 'swath edge: the array is not imaged' : im.gap === 'west' ? 'swath edge: the Ilulissat half is not imaged' : undefined"
          @click="imagery = im"
        >{{ im.label }}</button>
      </div>
    </div>

    <!-- Scale bar, bottom-right on both pages (the director's request): a
         1-2-5 length near an eighth of the screen, re-read on every zoom
         and resize from the view's metres-per-pixel. -->
    <div class="fw-corner">
      <!-- The Introduction's door to the rest of the footage (the director
           asked for a "more footage" button in the bottom right, just above
           the scale bar on the Introduction's footage step, linking to the
           additional work): the fieldwork door, all four days' clips. A
           plain router-link — Explore's door trail brings BACK to this
           step. Not on the door itself. -->
      <!-- A north arrow just left of the door, above the scale bar (the
           director asked for a north arrow above the scale bar, just to
           the left of the "more footage" button). The
           map is the site's equidistant cylindrical frame, north up, so
           it is a fixed arrow straight up; on the door (no pill) it sits
           alone above the scale bar. Drawn like the scale bar: cream
           line over a dark halo on the same dark pad. -->
      <div class="fw-corner-top">
        <div class="fw-north" aria-label="North">
          <span class="fw-north-label">N</span>
          <svg class="fw-north-arrow" width="22" height="34" viewBox="0 0 22 34">
            <path class="fw-scale-halo" d="M11 32 V10" />
            <path class="fw-north-head fw-north-head-halo" d="M11 2 L19 14 L11 11 L3 14 Z" />
            <path class="fw-scale-line" d="M11 32 V10" />
            <path class="fw-north-head" d="M11 2 L19 14 L11 11 L3 14 Z" />
          </svg>
        </div>
        <MoreDetailsPill
          v-if="mode === 'intro'"
          class="fw-more"
          label="More footage"
          to="/additional-work/fieldwork"
        />
      </div>
      <div class="fw-scale" aria-hidden="true">
        <span class="fw-scale-label">{{ scaleBar.label }}</span>
        <svg class="fw-scale-bar" :width="scaleBar.px + 4" height="10" :viewBox="`0 0 ${scaleBar.px + 4} 10`">
          <path class="fw-scale-halo" :d="`M2 1 V9 M2 5 H${scaleBar.px + 2} M${scaleBar.px + 2} 1 V9`" />
          <path class="fw-scale-line" :d="`M2 1 V9 M2 5 H${scaleBar.px + 2} M${scaleBar.px + 2} 1 V9`" />
        </svg>
      </div>
    </div>

    <!-- The clip panel, the same on both pages: pinned bottom-left and
         RESIZED from its upper-right corner (drag the handle; up-and-right
         grows it, down-and-left shrinks it); the ✕ is top-left. It opens
         big (the director wanted a larger default size for the movie
         box), a little bigger still in the Introduction; the map
         eases so the playing track stays clear of it (clearOfPanel). -->
    <Transition name="video-slide">
      <div
        v-if="selectedId"
        ref="panelEl"
        class="video-panel"
        :class="{ resizing: isResizing }"
        :style="panelW ? { width: `${panelW}px` } : undefined"
        @mousedown.stop
        @wheel.stop.prevent
      >
        <video
          ref="videoEl"
          class="video"
          :src="selectedVideoSrc"
          loop
          muted
          playsinline
          @loadedmetadata="onVideoReady"
          @play="playing = true"
          @pause="playing = false"
        />
        <!-- The caption row: play/pause FIRST (a fixed slot — the
             director saw the button move when the clock showed different
             times; it used to sit after the label, so the clock's
             appearance pushed it), then id · date · the local clock in
             tabular digits on a reserved width, then the scrub bar
             (the director's ordering). The glyph is geometry
             (PlayPauseGlyph — the ❚❚ / ▶ dingbats were not crisp).
             Scrubbing moves the marker with the frame; the wedge and
             clock follow. The clock is local Greenland time: the GPX is
             UTC, shifted by FW_UTC_OFFSET_H (WGST = UTC−2). -->
        <div class="video-meta">
          <button class="play-btn" :aria-label="playing ? 'Pause' : 'Play'" @click="togglePlay">
            <PlayPauseGlyph :playing="playing" :size="10" />
          </button>
          <span class="video-label">{{ selectedId }} · {{ selectedClipDate }} · <span class="video-clock">{{ clockLabel }}</span></span>
          <input
            class="scrub"
            type="range"
            min="0"
            :max="duration || 0"
            step="0.05"
            :value="videoTime"
            :style="{ '--fill': `${duration ? (100 * videoTime) / duration : 0}%` }"
            aria-label="Scrub"
            @input="onScrub"
            @mousedown.stop
          />
        </div>
        <button class="close-btn" @click="closeSelection" aria-label="Close">✕</button>
        <div class="resize-handle" title="Drag to resize" @mousedown.prevent.stop="onResizeStart" />
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { mediaUrl } from '../config/media'
import PlayPauseGlyph from './PlayPauseGlyph.vue'
import MoreDetailsPill from './MoreDetailsPill.vue'
import {
  FW_BASEMAP_KEY,
  FW_CLIPS,
  FW_DAYS,
  FW_DEFAULT_VIEW,
  FW_HALF_X_M,
  FW_HALF_Y_M,
  FW_IMAGERY,
  FW_INTRO_CLIP_IDS,
  FW_INTRO_CLIP_START,
  FW_MIN_HEIGHT_M,
  FW_STATIONS_KEY,
  FW_UTC_OFFSET_H,
  FW_WIDE_X0,
  FW_WIDE_Y0,
  FW_WIDE_X1,
  FW_WIDE_Y1,
  FW_INTRO_TRACKS_BOX,
  fwBounds,
  fwDoorClips,
  fwGpxKey,
  fwImageryFor,
  fwLandingView,
  fwSideAt,
  type FieldworkClip,
  type FieldworkDay,
  fwLatToY,
  fwLonToX,
  fwVideoKey,
} from '../config/fieldwork'

export interface FieldworkView { x: number; y: number; w: number; h: number }

const props = defineProps<{
  mode: 'intro' | 'full'
  /** viewBox (metres) to adopt — the parent measures it off the Globe's
   *  landing frame. Null = the default view. */
  initialView: FieldworkView | null
  revealed: boolean
  /**
   * The crop's URL — the Introduction hands over a blob: URL it fetched
   * once (null while still downloading); the door page (full mode) leaves
   * it undefined and the config URL is used.
   */
  basemapSrc?: string | null
  /**
   * The Introduction's clip steps: the clip to play. A change opens it
   * from its start (as a click would) once the map shows; null closes the
   * panel. Clicks on tracks still work in between — a click is not a step.
   */
  clip?: string | null
}>()
const emit = defineEmits<{ select: [id: string | null]; exit: []; covering: [on: boolean] }>()

// The wide context layer, the legend and the pan bounds belong to the
// door page only. There the imagery is one Sentinel-2 pass at a time
// (FW_IMAGERY: wide 20 m + a feathered 10 m inset of the SAME date); the
// Introduction keeps its plain 2023-08-18 crop.
const wide = props.mode === 'full'
const silhouetteUrl = mediaUrl('shared/greenland_silhouette.png')
const bounds = fwBounds(wide)
const imagery = ref(FW_IMAGERY[0])
const wideUrl = computed(() => mediaUrl(imagery.value.wideKey))
const basemapUrl = computed(() => (wide ? mediaUrl(imagery.value.detailKey) : mediaUrl(FW_BASEMAP_KEY)))

// Legend state (full mode). A day selects its nearest imagery; the
// imagery buttons override that until the next day pick.
const selectedDay = ref<string>('all')
const showRoute = ref(true)
const showClips = ref(true)
const showStations = ref(true)
function pickDay(date: string): void {
  selectedDay.value = date
  if (date !== 'all') imagery.value = fwImageryFor(date)
  if (selectedId.value && !visibleTracks.value.some((t) => t.id === selectedId.value)) closeSelection()
}
const visibleDays = computed<FieldworkDay[]>(() =>
  FW_DAYS.filter((d) => selectedDay.value === 'all' || d.date === selectedDay.value))
/** The colour everything of the playing clip's day wears (marker, wedge,
 *  panel frame) — the day's own when a clip plays, else the gold. */
const dayColor = computed<string>(() => selectedClip.value?.color ?? 'var(--gold)')

// ── the clip panel's size ─────────────────────────────────────────────
// 0 = the CSS default (about half the width; see .video-panel); otherwise px, set by dragging the upper-right
// handle — kept from clip to clip. Cleared when the viewport changes.
const panelEl = ref<HTMLDivElement | null>(null)
const panelW = ref(0)
const isResizing = ref(false)
let resizeStart: { x: number; y: number; w: number; h: number } | null = null
function onResizeStart(e: MouseEvent): void {
  const el = panelEl.value
  if (!el || e.button !== 0) return
  resizeStart = { x: e.clientX, y: e.clientY, w: el.offsetWidth, h: el.offsetHeight }
  isResizing.value = true
  window.addEventListener('mousemove', onResizeMove)
  window.addEventListener('mouseup', onResizeEnd)
}
function onResizeMove(e: MouseEvent): void {
  if (!resizeStart) return
  const { x, y, w, h } = resizeStart
  // The corner follows the cursor: whichever way it moved further wins,
  // so a pure sideways or pure upward drag both work.
  const fromX = w + (e.clientX - x)
  const fromY = w + (y - e.clientY) * (w / Math.max(1, h))
  const want = Math.max(fromX, fromY)
  const { w: vw } = vp()
  panelW.value = Math.round(Math.max(300, Math.min(vw * 0.92, want)))
}
function onResizeEnd(): void {
  resizeStart = null
  isResizing.value = false
  window.removeEventListener('mousemove', onResizeMove)
  window.removeEventListener('mouseup', onResizeEnd)
}

interface Pt { lat: number; lon: number; t: number; abs: number }
interface Track {
  id: string
  date: string
  color: string
  clip: FieldworkClip
  videoFile: string
  points: Pt[]
  svgPoints: string
}

const SIDE_OFFSET = { right: Math.PI / 2, left: -Math.PI / 2, forward: 0, back: Math.PI }
const SECTOR_RADIUS_M = 375
/** …but never shorter on screen than this (px): at the Introduction's
 *  landing 375 m is ~22 px, a speck from the back of the room. */
const SECTOR_MIN_PX = 44
const SECTOR_HALF_ANGLE = Math.PI / 6

const tracks = ref<Track[]>([])
const tracksShown = ref(false)
// Full mode: each day's route + station landings (see config FW_DAYS).
interface Station { name: string; label: string; x: number; y: number }
const dayLines = ref<Record<string, string>>({})
const stations = ref<Station[]>([])
const visibleTracks = computed(() =>
  showClips.value || !wide
    ? tracks.value.filter((t) => !wide || selectedDay.value === 'all' || t.date === selectedDay.value)
    : [])
const visibleStations = computed<Station[]>(() => (showStations.value ? stations.value : []))
// The 15 Mpx crop must be DECODED before the layer shows — on a slow link
// the dive can land first, and an SVG <image> that has loaded but not yet
// decoded paints nothing for a second or more (dark frames where the map
// should be, seen on film; the <image>'s own load event fires before
// that decode). A same-URL HTMLImageElement.decode() fills the shared
// image cache, so the SVG <image> (same URL) paints at once. In the
// Introduction `src` is a blob: URL of the one fetched copy (null until
// then), so the SVG never has a network request of its own that could
// still be in flight when the decode resolves — that was filmed as a black
// layer until it landed. The door page uses the config URL. Fail-safe in
// the watcher below.
const wanted = computed(() => (props.basemapSrc === undefined ? basemapUrl.value : props.basemapSrc))
// What the SVG actually draws. On the FIRST image the stage stays hidden
// until it has decoded (the dark-frames fix). On a later swap —
// the legend's imagery toggle — the stage must NOT un-reveal: the new
// pass decodes in the background and replaces the old one only when it
// can paint at once, so a toggle is a cut, never a blank.
const src = ref<string | null>(null)
const wideSrc = ref<string>(wideUrl.value)
const imgLoaded = ref(false)
function decodeThen(u: string, apply: () => void): void {
  const im = new Image()
  im.src = u
  im.decode().then(apply).catch(apply)
}
watch(
  wanted,
  (u) => {
    if (!u) { src.value = null; imgLoaded.value = false; return }
    if (!imgLoaded.value) {
      src.value = u
      decodeThen(u, () => { if (wanted.value === u) imgLoaded.value = true })
    } else {
      decodeThen(u, () => { if (wanted.value === u) src.value = u })
    }
  },
  { immediate: true },
)
watch(wideUrl, (u) => decodeThen(u, () => { if (wideUrl.value === u) wideSrc.value = u }))
const selectedId = ref<string | null>(null)
const videoEl = ref<HTMLVideoElement | null>(null)
const svgEl = ref<SVGSVGElement | null>(null)
const videoTime = ref(0)
const duration = ref(0)
const playing = ref(false)
const isDragging = ref(false)
const isPanning = ref(false)
let dragSuppressSync = false

// ── the view (metres) ─────────────────────────────────────────────────
// Width always follows the viewport's aspect so preserveAspectRatio=none
// stays a uniform scale (the landing handoff may be a hair anisotropic —
// that's exactly what `none` absorbs).
const view = ref<FieldworkView>(defaultView())
const viewBox = computed(() => {
  const v = view.value
  return `${v.x.toFixed(1)} ${v.y.toFixed(1)} ${v.w.toFixed(1)} ${v.h.toFixed(1)}`
})

function vp(): { w: number; h: number } {
  return { w: window.innerWidth || 1440, h: window.innerHeight || 900 }
}

// ── the scale bar ─────────────────────────────────────────────────────
// Metres per screen pixel come straight from the view (the SVG's width
// in metres over the window's width in pixels — preserveAspectRatio is
// `none`, so that ratio IS the horizontal scale). The bar picks the
// 1-2-5 length nearest a sixth of the screen (5 km at the landing).
const winW = ref(vp().w)
const scaleBar = computed(() => {
  const mPerPx = view.value.w / Math.max(1, winW.value)
  const targetM = 0.18 * winW.value * mPerPx
  const pow = Math.pow(10, Math.floor(Math.log10(Math.max(1, targetM))))
  const nice = [1, 2, 5, 10].map((k) => k * pow)
  const metres = nice.reduce((best, m) => (Math.abs(m - targetM) < Math.abs(best - targetM) ? m : best), nice[0])
  const px = Math.round(metres / mPerPx)
  const label = metres >= 1000 ? `${metres / 1000} km` : `${metres} m`
  return { px, label }
})
function defaultView(): FieldworkView {
  const { w, h } = vp()
  // The Introduction: the landing frame the Globe dives to (the parent
  // normally hands over the measured one; this is the fallback).
  if (!wide) return fwLandingView(w, h)
  const H = FW_DEFAULT_VIEW.heightM
  const W = (H * w) / h
  return { x: FW_DEFAULT_VIEW.cx - W / 2, y: FW_DEFAULT_VIEW.cy - H / 2, w: W, h: H }
}
function maxHeightM(): number {
  const { w, h } = vp()
  const bw = bounds.x1 - bounds.x0
  const bh = bounds.y1 - bounds.y0
  return Math.min(bh, (bw * h) / w)
}
function clampView(v: FieldworkView): FieldworkView {
  const { w: vw, h: vh } = vp()
  const H = Math.max(FW_MIN_HEIGHT_M, Math.min(maxHeightM(), v.h))
  const W = (H * vw) / vh
  const cx = v.x + v.w / 2
  const cy = v.y + v.h / 2
  const x = Math.max(bounds.x0, Math.min(bounds.x1 - W, cx - W / 2))
  const y = Math.max(bounds.y0, Math.min(bounds.y1 - H, cy - H / 2))
  return { x, y, w: W, h: H }
}

// The frame the map returns to between clips: the measured landing frame
// (Introduction) or the default view.
let homeView: FieldworkView = defaultView()
/** The eased move in flight (flyTo below); 0 = none. */
let flyRaf = 0
watch(
  () => props.initialView,
  (v) => {
    // Adopt the measured landing frame verbatim (no clamp: it IS the
    // frame on screen); later interaction clamps from there.
    if (v) {
      cancelFly()
      view.value = { ...v }
      homeView = { ...v }
    }
  },
  { immediate: true },
)

watch(
  () => props.revealed,
  (r) => {
    if (r) {
      window.setTimeout(() => { tracksShown.value = true }, 350)
      // If the decode never resolves (it should), show the map anyway.
      if (!imgLoaded.value) window.setTimeout(() => { imgLoaded.value = true }, 4000)
    } else {
      tracksShown.value = false
      // Hidden (the Introduction left the map): no clip plays unseen.
      if (selectedId.value) closeSelection()
    }
  },
  { immediate: true },
)

// `covering`: true once the reveal fade has finished
// — the stage is then opaque over the whole screen — and false the moment
// it starts to hide, in the same flush as the cut. The Introduction idles
// the Globe under it (Globe's `covered`): left rendering at 60 fps while
// hidden, the Globe's WebGL frames queued up in the GPU process (3–4 s of
// them after the clip steps), and the first frame that showed the Globe
// again had to wait for that whole queue — the Intro 7 → 8 freeze.
const stageShown = computed(() => props.revealed && imgLoaded.value)
function onStageTransitionEnd(e: TransitionEvent): void {
  if (e.propertyName === 'opacity' && stageShown.value) emit('covering', true)
}
watch(stageShown, (on) => { if (!on) emit('covering', false) })
onBeforeUnmount(() => emit('covering', false))

// ── eased view moves (the Introduction's clip steps) ──────────────────
// Centre lerped, size lerped in log space (a zoom reads evenly); any
// wheel / drag / marker grab takes over at once.
const FLY_MS = 900
function cancelFly(): void {
  if (flyRaf) cancelAnimationFrame(flyRaf)
  flyRaf = 0
}
function flyTo(to: FieldworkView, ms = FLY_MS): void {
  cancelFly()
  const from = { ...view.value }
  const { w: vw } = vp()
  const pxPerM = vw / from.w
  const moved = Math.max(
    Math.abs(to.x - from.x) * pxPerM,
    Math.abs(to.y - from.y) * pxPerM,
    Math.abs(to.w - from.w) * pxPerM,
    Math.abs(to.h - from.h) * pxPerM,
  )
  if (moved < 0.5) return
  const c0 = { x: from.x + from.w / 2, y: from.y + from.h / 2 }
  const c1 = { x: to.x + to.w / 2, y: to.y + to.h / 2 }
  const t0 = performance.now()
  const tick = (now: number) => {
    const t = Math.min(1, (now - t0) / ms)
    const e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
    const w = from.w * Math.pow(to.w / from.w, e)
    const h = from.h * Math.pow(to.h / from.h, e)
    const cx = c0.x + (c1.x - c0.x) * e
    const cy = c0.y + (c1.y - c0.y) * e
    view.value = { x: cx - w / 2, y: cy - h / 2, w, h }
    flyRaf = t < 1 ? requestAnimationFrame(tick) : 0
  }
  flyRaf = requestAnimationFrame(tick)
}

// ── the clip cue (Introduction steps 5–7) ─────────────────────────────
// A clip step = a click on its track, from the clip's start: the track
// lights, the panel opens bottom-left and plays, the marker rides. The
// map eases back to the landing frame if the visitor has moved it, and
// pans just enough that the track (and the wedge around the marker)
// clears the panel — at the landing framing it already does, so on the
// usual screens nothing moves. Honoured once the map shows and the tracks
// are in (a deep link waits for the tracks to draw on).
const CUE_AFTER_REVEAL_MS = 450
const cueReady = computed(() => props.revealed && imgLoaded.value && tracks.value.length > 0)
let cueTimer: number | null = null
watch(
  [() => props.clip, cueReady],
  ([id, ready], [oldId, wasReady]) => {
    if (props.clip === undefined) return // the door: clicks only
    if (cueTimer !== null) { window.clearTimeout(cueTimer); cueTimer = null }
    if (!ready) return
    if (!wasReady) {
      // Just shown: a clip step reached by a deep link (or back from the
      // timeline) starts once the tracks have drawn on.
      if (id) cueTimer = window.setTimeout(() => { cueTimer = null; if (props.clip === id) void cueClip(id) }, CUE_AFTER_REVEAL_MS)
      return
    }
    if (id === oldId) return
    if (id) void cueClip(id)
    else uncue()
  },
)
/** Seconds into the SERVED clip at which its clock reads `hms` (local
 *  Greenland time, the clock the panel shows); 0 when the clip has no
 *  timed points or the time falls before it. */
function clockToVideoTime(t: Track, hms: string): number {
  const first = t.points.find((p) => Number.isFinite(p.abs))
  const last = [...t.points].reverse().find((p) => Number.isFinite(p.abs))
  if (!first || !last) return 0
  const [hh, mm, ss] = hms.split(':').map(Number)
  const want = hh * 3600 + mm * 60 + (ss || 0)
  const day = (((first.abs + FW_UTC_OFFSET_H * 3600) % 86400) + 86400) % 86400
  // Into the original clip (its GPX), then into the served cut; never past
  // the last second of the track.
  const into = first.t + (want - day)
  return Math.max(0, Math.min(into, last.t - 1) - (t.clip.cropStart ?? 0))
}
async function cueClip(id: string): Promise<void> {
  const track = tracks.value.find((t) => t.id === id)
  if (!track) return
  const from = FW_INTRO_CLIP_START[id]
  await selectTrack(id, true, from ? clockToVideoTime(track, from) : 0)
  await nextTick()
  flyTo(clearOfPanel(homeView, id))
}
function uncue(): void {
  if (selectedId.value) closeSelection()
  flyTo(homeView)
}
/**
 * `v`, moved so the track `id` (and the wedge riding it) stays clear of
 * the clip panel and of the ribbon: the smallest pan that does it, at the
 * home scale if any pan can; failing that (a short screen with the big
 * panel), zoomed out a step at a time about the top-right corner — away
 * from the panel — until one does. A panel dragged huge is the visitor's
 * call: if nothing clears it, `v` stands.
 */
function clearOfPanel(v: FieldworkView, id: string): FieldworkView {
  const panel = panelEl.value
  const t = tracks.value.find((k) => k.id === id)
  if (!panel || !t || t.points.length === 0) return v
  const { w: vw, h: vh } = vp()
  // The top of the clear area: under the ribbon and its sub-menu bar.
  let top = 0.09 * vh
  for (const sel of ['.top-nav', '.landmarks']) {
    const r = document.querySelector(sel)?.getBoundingClientRect()
    if (r && r.height > 0) top = Math.max(top, r.bottom + 8)
  }
  // The door's legend (top-right) must stay clear of the track too.
  const lg = document.querySelector('.fw-legend')?.getBoundingClientRect()
  const legend = lg && lg.width > 0 ? lg : null
  const mx = t.points.map((p) => fwLonToX(p.lon))
  const my = t.points.map((p) => fwLatToY(p.lat))
  for (const f of [1, 0.94, 0.88, 0.82, 0.76]) {
    // Zoom out by 1/f about the screen point (vw, top).
    const w = v.w / f
    const h = v.h / f
    const vf: FieldworkView = {
      x: v.x + v.w - w, // keeps the right edge
      y: v.y + (top / vh) * (v.h - h),
      w,
      h,
    }
    const sx = vw / w
    const sy = vh / h
    const wedge = Math.max(SECTOR_RADIUS_M * sx, SECTOR_MIN_PX)
    const m = 24 + wedge // the wedge's reach, plus air
    const pr = panel.offsetLeft + panel.offsetWidth + m
    const pt = panel.offsetTop - m
    const xs = mx.map((x) => (x - vf.x) * sx)
    const ys = my.map((y) => (y - vf.y) * sy)
    const minX = Math.min(...xs)
    const maxX = Math.max(...xs)
    const minY = Math.min(...ys)
    const maxY = Math.max(...ys)
    // dy = px the map moves UP, dx = px it moves RIGHT; the whole track
    // stays on screen, its top a wedge's reach under the ribbon.
    const dyHi = minY - (top + wedge)
    const dyLo = maxY - (vh - 16)
    const dxHi = vw - m - maxX
    const dxLo = 16 - minX
    let best: { dx: number; dy: number } | null = null
    const tryDy = (dy: number) => {
      // The rightward move this dy still needs.
      let need = 0
      for (let k = 0; k < xs.length; k++) if (ys[k] - dy > pt && xs[k] < pr) need = Math.max(need, pr - xs[k])
      const dx = Math.max(need, dxLo, 0)
      if (dx > dxHi) return
      if (legend) {
        for (let k = 0; k < xs.length; k++) {
          const x = xs[k] + dx
          const y = ys[k] - dy
          if (x > legend.left - m && x < legend.right + m && y > legend.top - m && y < legend.bottom + m) return
        }
      }
      if (!best || Math.abs(dx) + Math.abs(dy) < Math.abs(best.dx) + Math.abs(best.dy)) best = { dx, dy }
    }
    if (dyLo <= dyHi) {
      tryDy(Math.max(dyLo, Math.min(dyHi, 0)))
      for (let dy = Math.ceil(dyLo); dy <= dyHi; dy += 4) tryDy(dy)
      tryDy(dyHi)
    }
    if (best) {
      const b = best as { dx: number; dy: number }
      if (f === 1 && Math.abs(b.dx) < 1 && Math.abs(b.dy) < 1) return v
      return clampView({ ...vf, x: vf.x - b.dx / sx, y: vf.y + b.dy / sy })
    }
  }
  return v
}

// ── projection helpers (config/fieldwork.ts frame) ────────────────────
function parseWaypoints(text: string): Station[] {
  const doc = new DOMParser().parseFromString(text, 'application/xml')
  const out: Station[] = []
  for (const w of doc.querySelectorAll('wpt')) {
    const lat = Number(w.getAttribute('lat'))
    const lon = Number(w.getAttribute('lon'))
    const name = w.querySelector('name')?.textContent?.trim() ?? ''
    if (!Number.isFinite(lat) || !Number.isFinite(lon) || !name) continue
    // "G206 HFELO" / "G303HELO" → "G206" / "G303": the suffix marks the
    // helicopter landing, the station id is the label.
    const label = name.replace(/\s*H?F?ELO$/i, '').trim() || name
    out.push({ name, label, x: fwLonToX(lon), y: fwLatToY(lat) })
  }
  return out
}
function parseGpx(text: string): Pt[] {
  const doc = new DOMParser().parseFromString(text, 'application/xml')
  const trkpts = doc.querySelectorAll('trkpt')
  let t0 = NaN
  const out: Pt[] = []
  for (const p of trkpts) {
    const lat = Number(p.getAttribute('lat'))
    const lon = Number(p.getAttribute('lon'))
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue
    const timeEl = p.querySelector('time')
    const ts = timeEl?.textContent ? Date.parse(timeEl.textContent) / 1000 : NaN
    if (!Number.isFinite(t0) && Number.isFinite(ts)) t0 = ts
    out.push({ lat, lon, t: Number.isFinite(ts) ? ts - t0 : NaN, abs: ts })
  }
  return out
}
function decimate<T>(arr: T[], target: number): T[] {
  if (arr.length <= target) return arr
  const stride = Math.ceil(arr.length / target)
  const out: T[] = []
  for (let i = 0; i < arr.length; i += stride) out.push(arr[i])
  if (out[out.length - 1] !== arr[arr.length - 1]) out.push(arr[arr.length - 1])
  return out
}
function buildSvgPoints(pts: Pt[]): string {
  return pts.map((p) => `${fwLonToX(p.lon).toFixed(1)},${fwLatToY(p.lat).toFixed(1)}`).join(' ')
}

// ── pan + zoom ────────────────────────────────────────────────────────
function svgPointFromClient(clientX: number, clientY: number): { x: number; y: number } | null {
  const svg = svgEl.value
  if (!svg) return null
  const pt = svg.createSVGPoint()
  pt.x = clientX
  pt.y = clientY
  const ctm = svg.getScreenCTM()
  if (!ctm) return null
  const p = pt.matrixTransform(ctm.inverse())
  return { x: p.x, y: p.y }
}

function onWheel(e: WheelEvent): void {
  cancelFly()
  const before = svgPointFromClient(e.clientX, e.clientY)
  const f = Math.exp(e.deltaY * 0.0016)
  const v = view.value
  const H = Math.max(FW_MIN_HEIGHT_M, Math.min(maxHeightM(), v.h * f))
  const s = H / v.h
  // Zoom about the cursor: keep the map point under it fixed.
  const px = before ? (before.x - v.x) / v.w : 0.5
  const py = before ? (before.y - v.y) / v.h : 0.5
  const W = v.w * s
  view.value = clampView({ x: (before?.x ?? v.x + v.w / 2) - px * W, y: (before?.y ?? v.y + v.h / 2) - py * H, w: W, h: H })
}

let panStart: { cx: number; cy: number; vx: number; vy: number } | null = null
let didPan = false
function onPanStart(e: MouseEvent): void {
  if (e.button !== 0) return
  // A map drag must not start a text selection (it was highlighting the
  // ribbon's labels).
  e.preventDefault()
  cancelFly()
  panStart = { cx: e.clientX, cy: e.clientY, vx: view.value.x, vy: view.value.y }
  didPan = false
  window.addEventListener('mousemove', onPanMove)
  window.addEventListener('mouseup', onPanEnd)
}
function onPanMove(e: MouseEvent): void {
  if (!panStart) return
  const dx = e.clientX - panStart.cx
  const dy = e.clientY - panStart.cy
  if (!didPan && Math.hypot(dx, dy) < 4) return
  didPan = true
  isPanning.value = true
  const { w: vw, h: vh } = vp()
  const v = view.value
  view.value = clampView({
    x: panStart.vx - (dx * v.w) / vw,
    y: panStart.vy - (dy * v.h) / vh,
    w: v.w,
    h: v.h,
  })
}
function onPanEnd(): void {
  panStart = null
  isPanning.value = false
  window.removeEventListener('mousemove', onPanMove)
  window.removeEventListener('mouseup', onPanEnd)
  // Let the click that ends a pan be ignored by the track handler.
  window.setTimeout(() => { didPan = false }, 0)
}

// ── marker + scrub (SectionExtras, unchanged) ─────────────────────────
const markerDotR = ref(14)
const DOT_PX = 6
function updateMarkerScale(): void {
  const { h: vh } = vp()
  markerDotR.value = (DOT_PX * view.value.h) / vh
}
watch(view, updateMarkerScale)

const selectedClip = computed(() => tracks.value.find((t) => t.id === selectedId.value) ?? null)
const selectedVideoSrc = computed(() => (selectedClip.value ? mediaUrl(selectedClip.value.videoFile) : ''))
const selectedClipDate = computed(() => selectedClip.value?.date ?? '')
/** Seconds into the ORIGINAL clip (= its GPX): served time + crop offset. */
const clipTime = computed(() => videoTime.value + (selectedClip.value?.clip.cropStart ?? 0))
/** Local time of day at the marker (GPX is UTC; WGST = UTC−2). */
const clockLabel = computed<string>(() => {
  const t = selectedClip.value
  if (!t || t.points.length === 0) return ''
  const pts = t.points
  const time = clipTime.value
  let lo = 0, hi = pts.length - 1
  while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (pts[mid].t <= time) lo = mid; else hi = mid }
  const a = pts[lo], b = pts[hi]
  const u = Math.max(0, Math.min(1, (time - a.t) / Math.max(1e-6, b.t - a.t)))
  const abs = a.abs + u * (b.abs - a.abs)
  if (!Number.isFinite(abs)) return ''
  const local = new Date((abs + FW_UTC_OFFSET_H * 3600) * 1000)
  const hh = String(local.getUTCHours()).padStart(2, '0')
  const mm = String(local.getUTCMinutes()).padStart(2, '0')
  const ss = String(local.getUTCSeconds()).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
})

let rafId = 0
function startSyncLoop(): void {
  cancelAnimationFrame(rafId)
  const tick = () => {
    const v = videoEl.value
    if (v && !dragSuppressSync) videoTime.value = v.currentTime
    rafId = requestAnimationFrame(tick)
  }
  rafId = requestAnimationFrame(tick)
}
function stopSyncLoop(): void {
  cancelAnimationFrame(rafId)
  rafId = 0
}

function nearestPointIndex(track: Track, x: number, y: number): number {
  let bestI = 0
  let bestD = Infinity
  const pts = track.points
  for (let i = 0; i < pts.length; i++) {
    const dx = fwLonToX(pts[i].lon) - x
    const dy = fwLatToY(pts[i].lat) - y
    const d = dx * dx + dy * dy
    if (d < bestD) {
      bestD = d
      bestI = i
    }
  }
  return bestI
}
function seekToTrackPoint(track: Track, idx: number): void {
  const p = track.points[idx]
  if (!p || !Number.isFinite(p.t)) return
  videoTime.value = p.t
  const v = videoEl.value
  if (v) v.currentTime = p.t
}
function onMarkerMouseDown(e: MouseEvent): void {
  e.preventDefault()
  e.stopPropagation()
  beginDrag()
  window.addEventListener('mousemove', onDragMove)
  window.addEventListener('mouseup', endDrag)
}
function onMarkerTouchStart(e: TouchEvent): void {
  e.stopPropagation()
  beginDrag()
  window.addEventListener('touchmove', onTouchDragMove, { passive: false })
  window.addEventListener('touchend', endDrag)
  window.addEventListener('touchcancel', endDrag)
}
function beginDrag(): void {
  cancelFly()
  isDragging.value = true
  dragSuppressSync = true
}
function onDragMove(e: MouseEvent): void {
  if (!selectedClip.value) return
  const p = svgPointFromClient(e.clientX, e.clientY)
  if (!p) return
  seekToTrackPoint(selectedClip.value, nearestPointIndex(selectedClip.value, p.x, p.y))
}
function onTouchDragMove(e: TouchEvent): void {
  if (!selectedClip.value) return
  const touch = e.touches[0]
  if (!touch) return
  e.preventDefault()
  const p = svgPointFromClient(touch.clientX, touch.clientY)
  if (!p) return
  seekToTrackPoint(selectedClip.value, nearestPointIndex(selectedClip.value, p.x, p.y))
}
function endDrag(): void {
  isDragging.value = false
  dragSuppressSync = false
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', endDrag)
  window.removeEventListener('touchmove', onTouchDragMove)
  window.removeEventListener('touchend', endDrag)
  window.removeEventListener('touchcancel', endDrag)
}

function onTrackClick(t: Track, e: MouseEvent): void {
  if (didPan) return
  if (t.id !== selectedId.value) {
    // The door: the bigger panel opens bottom-left — ease the map just
    // enough that the clicked track stays clear of it (and the legend).
    void selectTrack(t.id).then(() => nextTick()).then(() => {
      if (selectedId.value !== t.id) return
      const v = clearOfPanel(view.value, t.id)
      if (v !== view.value) flyTo(v)
    })
    return
  }
  const p = svgPointFromClient(e.clientX, e.clientY)
  if (!p) return
  seekToTrackPoint(t, nearestPointIndex(t, p.x, p.y))
}
/** Open a clip from its start — or from `startAt` seconds into it (an
 *  Introduction step's FW_INTRO_CLIP_START). `restart`: also when it is
 *  already open (a clip step replays it; a second click on the same track
 *  seeks). */
async function selectTrack(id: string, restart = false, startAt = 0): Promise<void> {
  if (selectedId.value === id && !restart) return
  selectedId.value = id
  emit('select', id)
  videoTime.value = startAt
  await nextTick()
  const v = videoEl.value
  if (v) {
    v.currentTime = startAt
    v.play().catch(() => {})
  }
  startSyncLoop()
}
function closeSelection(): void {
  selectedId.value = null
  emit('select', null)
  videoTime.value = 0
  duration.value = 0
  playing.value = false
  stopSyncLoop()
}
function onVideoReady(): void {
  duration.value = videoEl.value?.duration ?? 0
  videoEl.value?.play().catch(() => {})
}
function togglePlay(): void {
  const v = videoEl.value
  if (!v) return
  if (v.paused) v.play().catch(() => {})
  else v.pause()
}
function onScrub(e: Event): void {
  const t = Number((e.target as HTMLInputElement).value)
  if (!Number.isFinite(t)) return
  videoTime.value = t
  const v = videoEl.value
  if (v) v.currentTime = t
}

const markerPos = computed<{ x: number; y: number } | null>(() => {
  const t = selectedClip.value
  if (!t) return null
  const pts = t.points
  if (pts.length === 0) return null
  const time = clipTime.value
  if (time <= pts[0].t) return { x: fwLonToX(pts[0].lon), y: fwLatToY(pts[0].lat) }
  const last = pts[pts.length - 1]
  if (time >= last.t) return { x: fwLonToX(last.lon), y: fwLatToY(last.lat) }
  let lo = 0, hi = pts.length - 1
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1
    if (pts[mid].t <= time) lo = mid
    else hi = mid
  }
  const a = pts[lo], b = pts[hi]
  const u = (time - a.t) / Math.max(1e-6, b.t - a.t)
  return { x: fwLonToX(a.lon + u * (b.lon - a.lon)), y: fwLatToY(a.lat + u * (b.lat - a.lat)) }
})

const markerHeading = computed<number | null>(() => {
  const t = selectedClip.value
  if (!t) return null
  const pts = t.points
  if (pts.length < 2) return null
  const time = clipTime.value
  let lo = 0, hi = pts.length - 1
  if (time > pts[0].t && time < pts[hi].t) {
    while (hi - lo > 1) {
      const mid = (lo + hi) >> 1
      if (pts[mid].t <= time) lo = mid
      else hi = mid
    }
  }
  const WIN = 30
  const i0 = Math.max(0, lo - WIN)
  const i1 = Math.min(pts.length - 1, hi + WIN)
  const dx = fwLonToX(pts[i1].lon) - fwLonToX(pts[i0].lon)
  const dy = fwLatToY(pts[i1].lat) - fwLatToY(pts[i0].lat)
  if (Math.hypot(dx, dy) < 1e-3) return null
  return Math.atan2(dy, dx)
})

const sectorPath = computed<string | null>(() => {
  const pos = markerPos.value
  const heading = markerHeading.value
  const sel = selectedClip.value
  if (!pos || heading === null || !sel) return null
  const side = fwSideAt(sel.clip, videoTime.value)
  if (!side) return null
  const bearing = heading + SIDE_OFFSET[side]
  const a1 = bearing - SECTOR_HALF_ANGLE
  const a2 = bearing + SECTOR_HALF_ANGLE
  const r = Math.max(SECTOR_RADIUS_M, (SECTOR_MIN_PX * view.value.h) / vp().h)
  const x1 = pos.x + r * Math.cos(a1)
  const y1 = pos.y + r * Math.sin(a1)
  const x2 = pos.x + r * Math.cos(a2)
  const y2 = pos.y + r * Math.sin(a2)
  return `M ${pos.x.toFixed(0)} ${pos.y.toFixed(0)} L ${x1.toFixed(0)} ${y1.toFixed(0)} A ${r} ${r} 0 0 1 ${x2.toFixed(0)} ${y2.toFixed(0)} Z`
})

function onResize(): void {
  winW.value = vp().w
  cancelFly()
  view.value = clampView(view.value)
  homeView = clampView(homeView)
  updateMarkerScale()
  panelW.value = 0
}

onMounted(async () => {
  window.addEventListener('resize', onResize)
  updateMarkerScale()
  try {
    const clips = wide ? fwDoorClips() : FW_CLIPS.filter((c) => FW_INTRO_CLIP_IDS.includes(c.id))
    const loaded = await Promise.all(
      clips.map(async (c) => {
        try {
          const text = await fetch(mediaUrl(fwGpxKey(c.id))).then((r) => (r.ok ? r.text() : Promise.reject(r.status)))
          const points = parseGpx(text)
          return {
            id: c.id,
            date: c.date,
            color: FW_DAYS.find((d) => d.date === c.date)?.color ?? '#f4cf6a',
            clip: c,
            videoFile: fwVideoKey(c.id),
            points,
            svgPoints: buildSvgPoints(decimate(points, 600)),
          } as Track
        } catch (e) {
          console.warn('[fieldwork] track', c.id, e)
          return null
        }
      }),
    )
    tracks.value = loaded.filter((t): t is Track => t !== null)
    if (!wide) {
      // The landing framing is frozen from these tracks' box
      // (FW_INTRO_TRACKS_BOX) so the Globe can dive before they load —
      // say so if the data and the frozen box ever disagree.
      const xs = tracks.value.flatMap((t) => t.points.map((p) => fwLonToX(p.lon)))
      const ys = tracks.value.flatMap((t) => t.points.map((p) => fwLatToY(p.lat)))
      const b = FW_INTRO_TRACKS_BOX
      const off = Math.max(
        Math.abs(Math.min(...xs) - b.x0), Math.abs(Math.max(...xs) - b.x1),
        Math.abs(Math.min(...ys) - b.y0), Math.abs(Math.max(...ys) - b.y1),
      )
      if (xs.length && off > 50) console.warn(`[fieldwork] the intro tracks' box is ${Math.round(off)} m off FW_INTRO_TRACKS_BOX`)
    }
  } catch (e) {
    console.error('FieldworkExplorer: failed to load tracks', e)
  }
  if (wide) {
    // Context only — a failure here leaves the clip tracks untouched.
    for (const d of FW_DAYS) {
      if (d.dayTrackKey) {
        fetch(mediaUrl(d.dayTrackKey))
          .then((r) => (r.ok ? r.text() : Promise.reject(r.status)))
          .then((t) => { dayLines.value = { ...dayLines.value, [d.date]: buildSvgPoints(decimate(parseGpx(t), 1500)) } })
          .catch((e) => console.warn('[fieldwork] day track', d.date, e))
      }
    }
    fetch(mediaUrl(FW_STATIONS_KEY))
      .then((r) => (r.ok ? r.text() : Promise.reject(r.status)))
      .then((t) => { stations.value = parseWaypoints(t) })
      .catch((e) => console.warn('[fieldwork] stations', e))
  }
})

onBeforeUnmount(() => {
  cancelFly()
  if (cueTimer !== null) window.clearTimeout(cueTimer)
  stopSyncLoop()
  endDrag()
  onPanEnd()
  onResizeEnd()
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.fw-stage {
  position: fixed;
  inset: 0;
  background: #050505;
  overflow: hidden;
  pointer-events: auto;
  /* No positive z-index: the aside (title row + next/back) comes later
     in Explore's DOM and must paint above this layer. */
  z-index: 0;
  cursor: grab;
  user-select: none;
  -webkit-user-select: none;
}
/* Reveal = a 0.55 s fade in. Hide = a CUT (visibility), never a fade out:
   taking this layer's opacity below 1 — faded, jumped, transitioned or
   not, with or without will-change — froze the page's frames for 4–7 s
   with an idle main thread (the compositor rasterising a group-opacity
   surface for a fixed full-screen layer holding a 15 Mpx SVG <image>
   and drop-shadowed polylines); `visibility: hidden` measured free.
   Bisected in a headed browser, one property at a time. The cut is
   invisible in practice: on the way out the Globe's Sentinel-2 patch
   sits pixel-aligned under this map, and the timeline's own backdrop
   fades in over 2 → 3. */
.fw-stage.revealed {
  opacity: 1;
  visibility: visible;
  transition: opacity 0.55s ease;
}
.fw-stage:not(.revealed) {
  opacity: 0;
  visibility: hidden;
  transition: none;
  /* Warm (mounted, hidden) during step 1 and the dive: never eat the mouse. */
  pointer-events: none;
}
.fw-stage.panning { cursor: grabbing; }

.fw-map {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}

.fw-tracks {
  opacity: 0;
  transition: opacity 0.9s ease;
}
.fw-tracks.shown { opacity: 1; }

.track-group { cursor: pointer; }

.track-line {
  fill: none;
  stroke: var(--track, var(--gold));
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
  transition: stroke 0.2s, stroke-width 0.2s, filter 0.2s;
}
.track-line-outline {
  fill: none;
  stroke: rgba(0, 0, 0, 0.9);
  stroke-width: 6;
  stroke-linecap: round;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
  transition: stroke-width 0.2s;
}
/* The day layer (full mode): quiet, beneath the clip tracks. */
.fw-day {
  opacity: 0;
  transition: opacity 0.8s ease;
  pointer-events: none;
}
.fw-day.shown { opacity: 1; }
.day-line {
  fill: none;
  stroke: var(--track, rgba(244, 207, 106, 0.7));
  stroke-width: 1.25;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 6 5;
  vector-effect: non-scaling-stroke;
  opacity: 0.55;
}
.day-line-outline {
  fill: none;
  stroke: rgba(0, 0, 0, 0.32);
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
}
.station-dot {
  fill: rgba(244, 207, 106, 0.85);
  stroke: rgba(0, 0, 0, 0.6);
  stroke-width: 1.5;
  vector-effect: non-scaling-stroke;
}
.station-label {
  font-family: 'Inter', system-ui, sans-serif;
  font-weight: 500;
  letter-spacing: 0.04em;
  fill: #fff4c8;
  paint-order: stroke;
  stroke: rgba(0, 0, 0, 0.7);
  stroke-width: 0.22em;
  stroke-linejoin: round;
}

.track-line-glow {
  fill: none;
  stroke: rgba(244, 207, 106, 0);
  stroke-width: 14;
  stroke-linecap: round;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
  transition: stroke 0.2s;
}
.track-group:hover .track-line { stroke: var(--gold-bright); stroke-width: 5; }
.track-group:hover .track-line-outline { stroke-width: 9; }
.track-group:hover .track-line-glow { stroke: rgba(244, 207, 106, 0.22); }
.track-group.active .track-line {
  stroke: #fff4c8;
  stroke-width: 6;
  filter: drop-shadow(0 0 7px rgba(244, 207, 106, 0.85));
}
.track-group.active .track-line-outline { stroke-width: 10; }
.track-group.active .track-line-glow { stroke: rgba(244, 207, 106, 0.45); }
.track-group.dimmed .track-line { stroke: rgba(232, 185, 74, 0.65); }
.track-group.dimmed .track-line-outline { stroke: rgba(0, 0, 0, 0.55); }
.track-group.dimmed:hover .track-line { stroke: var(--gold-bright); }
/* The door: every day keeps ITS colour through hover, dimming and play
   (--track is the day's; --day on the stage is the playing clip's day). */
.fw-stage:not(.fw-intro) .track-group:hover .track-line { stroke: color-mix(in srgb, var(--track) 72%, #fff); }
.fw-stage:not(.fw-intro) .track-group:hover .track-line-glow { stroke: color-mix(in srgb, var(--track) 22%, transparent); }
.fw-stage:not(.fw-intro) .track-group.active .track-line {
  stroke: color-mix(in srgb, var(--track) 45%, #fff);
  filter: drop-shadow(0 0 7px color-mix(in srgb, var(--track) 85%, transparent));
}
.fw-stage:not(.fw-intro) .track-group.active .track-line-glow { stroke: color-mix(in srgb, var(--track) 45%, transparent); }
.fw-stage:not(.fw-intro) .track-group.dimmed .track-line { stroke: color-mix(in srgb, var(--track) 60%, transparent); }
.fw-stage:not(.fw-intro) .track-group.dimmed:hover .track-line { stroke: color-mix(in srgb, var(--track) 72%, #fff); }
/* (the wedge + marker wear the day's colour through --wedge, below) */
.fw-stage:not(.fw-intro) { --wedge: var(--day, var(--gold)); }
.fw-stage:not(.fw-intro) .marker-dot { stroke: var(--day); }
.fw-stage:not(.fw-intro) .video-panel { border-color: var(--day); }
.fw-stage:not(.fw-intro) .close-btn { color: var(--day); }

/* The camera wedge (the director wanted more contrast between it and
   the ice, and suggested a black outline):
   a black edge drawn first and wide, then a dark, saturated fill of the
   day's colour (the gold in the Introduction) with that colour as a rim
   inside the black — dark enough to sit on white ice, rimmed bright
   enough to sit on dark water. The marker gets the same black ring. */
.fw-stage { --wedge: var(--gold); }
.marker-sector-edge {
  fill: none;
  stroke: #000;
  stroke-width: 6;
  stroke-linejoin: round;
  stroke-opacity: 0.9;
  vector-effect: non-scaling-stroke;
  pointer-events: none;
}
.marker-sector {
  fill: color-mix(in srgb, var(--wedge) 62%, #000);
  fill-opacity: 0.82;
  stroke: var(--wedge);
  stroke-width: 2;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
  pointer-events: none;
}
.marker-dot-edge {
  fill: none;
  stroke: #000;
  stroke-width: 7;
  stroke-opacity: 0.9;
  vector-effect: non-scaling-stroke;
  pointer-events: none;
}
.marker-dot {
  fill: #fff8d8;
  stroke: var(--gold-bright);
  stroke-width: 3;
  vector-effect: non-scaling-stroke;
  cursor: grab;
  transition: filter 0.18s;
}
.marker-dot:hover { filter: drop-shadow(0 0 6px rgba(0, 0, 0, 0.9)); }
.marker-dot.dragging { cursor: grabbing; }

/* The legend (full mode), top-right under the ribbon. */
.fw-legend {
  position: absolute;
  top: 5.2rem;
  right: 1.2rem;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  padding: 0.7rem 0.8rem;
  background: rgba(5, 5, 5, 0.72);
  border: 1px solid var(--gold-faint);
  border-radius: 10px;
  backdrop-filter: blur(6px);
  font-family: 'Inter', system-ui, sans-serif;
  pointer-events: auto;
}
/* Under 1840 px the site's back/next pills drop below the top nav
   (Explore's .beat-nav, top 6.2vh) — the legend starts under them. */
@media (max-width: 1840px) {
  .fw-legend { top: calc(6.2vh + 2.6rem); }
}
.lg-row { display: flex; align-items: center; gap: 0.35rem; flex-wrap: wrap; }
.lg-k {
  font-size: 0.66rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--gold-dim);
  margin-right: 0.2rem;
}
.lg-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: transparent;
  border: 1px solid transparent;
  color: rgba(245, 245, 245, 0.55);
  font-family: inherit;
  font-size: 0.78rem;
  letter-spacing: 0.03em;
  padding: 0.28rem 0.6rem;
  border-radius: 999px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}
.lg-btn:hover { color: #f5f5f5; }
.lg-btn.on { color: #f5f5f5; border-color: var(--gold-faint); background: rgba(232, 185, 74, 0.08); }
.sw {
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 50%;
  background: var(--sw, var(--gold));
  border: 1px solid rgba(0, 0, 0, 0.6);
  opacity: 0.45;
  flex-shrink: 0;
}
.lg-btn.on .sw { opacity: 1; }
.sw-all { background: linear-gradient(135deg, #f4cf6a 50%, #d5a6ff 50%); }
/* The pass row — many while the director chooses; wraps to a fixed width. */
.lg-imagery { max-width: 26rem; row-gap: 0.15rem; }
.lg-pass { padding: 0.2rem 0.5rem; font-size: 0.74rem; }
.lg-pass.gap { color: rgba(245, 245, 245, 0.3); font-style: italic; }
.lg-pass.gap.on { color: rgba(245, 245, 245, 0.75); }
.sw-route { border-radius: 2px; height: 0.2rem; width: 0.9rem; background: rgba(245, 245, 245, 0.8); }
.sw-clip { border-radius: 2px; height: 0.3rem; width: 0.9rem; background: var(--gold-bright); }
.sw-station { background: rgba(244, 207, 106, 0.85); width: 0.55rem; height: 0.55rem; }

/* Exit pill (full page), top-left under the ribbon — the Terminal-Bench
   page's "← doors". */
.fw-exit {
  position: absolute;
  top: 8vh;
  left: 1.6vw;
  z-index: 16;
  border: 1px solid var(--gold-dim);
  background: rgba(8, 6, 4, 0.78);
  color: var(--gold-dim);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.76rem;
  font-weight: 500;
  letter-spacing: 0.06em;
  padding: 0.42rem 0.9rem;
  border-radius: 999px;
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
}
.fw-exit:hover { color: var(--gold-bright); border-color: var(--gold); }
.fw-stage:not(.fw-intro) .minimap { top: 14vh; }

/* Minimap — top-left under the ribbon: Greenland's silhouette with the
   flight area pulsing. */
.minimap {
  position: absolute;
  top: 8vh;
  left: 1.6vw;
  width: 120px;
  z-index: 15;
  pointer-events: none;
  filter: drop-shadow(0 8px 24px rgba(0, 0, 0, 0.7));
}
.silhouette {
  width: 120px;
  height: 210px;
  background: rgba(232, 185, 74, 0.75);
  -webkit-mask: var(--silhouette-url) center / contain no-repeat;
  mask: var(--silhouette-url) center / contain no-repeat;
  filter:
    drop-shadow(1.2px 0 0 rgba(0, 0, 0, 1))
    drop-shadow(-1.2px 0 0 rgba(0, 0, 0, 1))
    drop-shadow(0 1.2px 0 rgba(0, 0, 0, 1))
    drop-shadow(0 -1.2px 0 rgba(0, 0, 0, 1))
    drop-shadow(0 0 3px rgba(0, 0, 0, 0.55));
}
/* North Lake ≈ (45, 200) on the 170 × 298 silhouette → scaled 120/170. */
.minimap-aoi-halo,
.minimap-aoi-dot {
  position: absolute;
  top: 141px;
  left: 32px;
  transform: translate(-50%, -50%);
}
.minimap-aoi-halo {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid rgba(244, 207, 106, 0.85);
  background: rgba(244, 207, 106, 0.15);
  animation: minimap-pulse 2s ease-in-out infinite;
}
.minimap-aoi-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--gold-bright);
  border: 1.5px solid #fff8d8;
  box-shadow: 0 0 10px rgba(244, 207, 106, 0.95);
}
@keyframes minimap-pulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.85; }
  50% { transform: translate(-50%, -50%) scale(1.35); opacity: 0.35; }
}

/* The bottom-right corner, clear of the clip panel: the scale bar, and on
   the Introduction the MORE FOOTAGE door stacked just above it. */
.fw-corner {
  position: absolute;
  right: 2vw;
  bottom: 2.2vh;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.7rem;
  pointer-events: none;
  z-index: 15;
}
/* The row above the scale bar: the north arrow, then (Introduction) the
   MORE FOOTAGE door on its right; bottoms aligned. */
.fw-corner-top {
  display: flex;
  flex-direction: row;
  align-items: flex-end;
  gap: 0.7rem;
}
.fw-north {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.05rem;
  padding: 0.3rem 0.55rem 0.4rem;
  border-radius: 8px;
  background: rgba(6, 5, 4, 0.62);
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.6s ease 0.3s;
}
.fw-stage.revealed .fw-north { opacity: 1; }
.fw-north-label {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1.2rem;
  font-weight: 700;
  line-height: 1;
  color: #f5f0e6;
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.9), 0 0 2px rgba(0, 0, 0, 0.9);
}
.fw-north-arrow { display: block; overflow: visible; }
.fw-north-head { fill: #f5f0e6; stroke: #f5f0e6; stroke-width: 1.5; stroke-linejoin: round; }
.fw-north-head-halo { fill: rgba(0, 0, 0, 0.85); stroke: rgba(0, 0, 0, 0.85); stroke-width: 5; }
/* The door: the chapters' lit door pill (readable on bright ice from the
   back row); it shows, and takes clicks, once the map has landed. */
.fw-more {
  font-size: 0.98rem;
  color: var(--gold-bright);
  border: 1.5px solid rgba(232, 185, 74, 0.85);
  background: rgba(8, 6, 4, 0.78);
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.55), 0 0 22px rgba(245, 199, 94, 0.18);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.6s ease 0.3s, color 0.2s, border-color 0.2s, background 0.2s;
}
.fw-stage.revealed .fw-more {
  opacity: 1;
  pointer-events: auto;
}
.fw-more:hover {
  color: #fff8d8;
  border-color: var(--gold-bright);
  background: rgba(56, 38, 12, 0.88);
}
/* Scale bar: cream line over a dark halo so it reads on bright ice. */
.fw-scale {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.2rem;
  /* A dark pad under it so the bar and its label hold on bright ice
     from the back of a projected room (the contrast sweep). */
  padding: 0.35rem 0.7rem 0.55rem;
  border-radius: 8px;
  background: rgba(6, 5, 4, 0.62);
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.6s ease 0.3s;
}
.fw-stage.revealed .fw-scale { opacity: 1; }
.fw-scale-label {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1.2rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.04em;
  color: #f5f0e6;
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.9), 0 0 2px rgba(0, 0, 0, 0.9);
}
.fw-scale-bar { display: block; overflow: visible; }
.fw-scale-halo { fill: none; stroke: rgba(0, 0, 0, 0.85); stroke-width: 6.5; stroke-linecap: round; }
.fw-scale-line { fill: none; stroke: #f5f0e6; stroke-width: 3; stroke-linecap: round; }

/* Clip panel: bottom-left on both pages, resizable from its upper-right
   corner. Bigger by default at the director's request (a larger default
   size for the movie box — the video is what the room
   watches): in the Introduction 60 % of the width, or 66 % of the height
   on a wide screen; on the door 54 % / 56 %. clearOfPanel() eases the
   map so the playing track, its marker and wedge stay clear of it (and
   of the ribbon and the door's legend). */
.video-panel {
  position: absolute;
  bottom: 3vh;
  left: 1.6vw;
  width: min(54vw, calc((56vh - 2.3rem) * 16 / 9));
  min-width: 300px;
  max-width: 92vw;
  background: #050505;
  border: 1.5px solid var(--gold);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 16px 56px -14px rgba(0, 0, 0, 0.9);
  z-index: 20;
  cursor: default;
}
.fw-intro .video-panel {
  width: min(60vw, calc((66vh - 2.3rem) * 16 / 9));
}
.video-panel.resizing { transition: none; }
.video-panel.resizing .video { pointer-events: none; }
/* Every clip is 1920 × 1080: the frame holds its 16:9 box from the first
   moment, so the panel opens at its full size instead of growing (and,
   pinned to the bottom, jumping up) when the video's metadata lands. */
.video {
  display: block;
  width: 100%;
  height: auto;
  aspect-ratio: 16 / 9;
  object-fit: contain;
  background: #050505;
}
.video-meta {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.35rem 0.75rem;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.95rem;
  letter-spacing: 0.08em;
  color: var(--gold-bright);
  border-top: 1px solid var(--gold-faint);
  text-transform: uppercase;
}
.video-label { white-space: nowrap; flex: none; font-variant-numeric: tabular-nums; }
/* The clock's slot is reserved (8 tabular digits + 2 colons) so the row
   never reflows when the time appears or ticks. */
.video-clock { display: inline-block; min-width: 8ch; }
.play-btn {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 1.75rem;
  padding: 0;
  border: 1.5px solid var(--gold-dim);
  border-radius: 999px;
  background: transparent;
  color: var(--day, var(--gold));
  line-height: 1;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.play-btn:hover { border-color: var(--day, var(--gold)); color: #fff; }
/* The scrub bar: a thin track filled to the playhead in the day's colour. */
.scrub {
  flex: 1 1 auto;
  min-width: 80px;
  height: 14px;
  margin: 0;
  cursor: pointer;
  -webkit-appearance: none;
  appearance: none;
  background: transparent;
}
.scrub::-webkit-slider-runnable-track {
  height: 5px;
  border-radius: 3px;
  background: linear-gradient(to right, var(--day, var(--gold)) var(--fill, 0%), rgba(245, 245, 245, 0.32) var(--fill, 0%));
}
.scrub::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 15px;
  height: 15px;
  margin-top: -5px;
  border-radius: 50%;
  background: #fff8d8;
  border: 1.5px solid var(--day, var(--gold));
  box-shadow: 0 0 5px rgba(0, 0, 0, 0.6);
}
.scrub::-moz-range-track {
  height: 5px;
  border-radius: 3px;
  background: rgba(245, 245, 245, 0.32);
}
.scrub::-moz-range-progress { height: 5px; border-radius: 3px; background: var(--day, var(--gold)); }
.scrub::-moz-range-thumb {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background: #fff8d8;
  border: 1.5px solid var(--day, var(--gold));
}
/* Top-LEFT: the upper-right corner is the resize grip. */
.close-btn {
  position: absolute;
  top: 0.45rem;
  left: 0.45rem;
  width: 26px;
  height: 26px;
  border: none;
  background: rgba(0, 0, 0, 0.7);
  color: var(--gold);
  font-size: 0.8rem;
  cursor: pointer;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s, background 0.2s;
}
.close-btn:hover { color: var(--gold-bright); background: rgba(0, 0, 0, 0.9); }
.fw-stage:not(.fw-intro) .close-btn:hover { color: #fff; }
/* The resize grip: the panel's upper-right corner, a small bevelled
   triangle that brightens on hover; the cursor says what it does. */
.resize-handle {
  position: absolute;
  top: 0;
  right: 0;
  width: 30px;
  height: 30px;
  cursor: nesw-resize;
  background: linear-gradient(225deg, color-mix(in srgb, var(--day, var(--gold)) 85%, transparent) 0 11px, rgba(0, 0, 0, 0.55) 11px 13px, transparent 13px);
  opacity: 0.75;
  transition: opacity 0.15s;
}
.resize-handle:hover, .video-panel.resizing .resize-handle { opacity: 1; }

.video-slide-enter-active,
.video-slide-leave-active { transition: transform 0.4s ease, opacity 0.4s ease; }
.video-slide-enter-from,
.video-slide-leave-to { transform: translateY(20px); opacity: 0; }
</style>
