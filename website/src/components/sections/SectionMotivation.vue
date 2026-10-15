<template>
  <!-- The Introduction is HEADLESS (the director's choice): no title, no prose,
       no aside. Its back/next are the site's shared pills (Explore's
       .beat-nav, driven by advanceTrigger/backTrigger like the chapters).
       What stays on screen are FIGURE labels: at step 0 two measuring
       lines floating beside the greenland object (true lengths at the
       object's scale, config/introDims.ts) and the sea-level number at
       its south-east tip; a small reference link bottom-right on steps 0
       and 1. Positions track the object every frame via the Globe's
       screenAnchors → window.__globeAnchorScreens, written imperatively
       (no Vue tick in the loop, the InsetZoom pattern). -->
  <div class="intro-hud">
    <svg
      v-if="step === 0"
      class="dims"
      :class="{ on: dimsOn }"
      :width="vw"
      :height="vh"
      aria-hidden="true"
    >
      <g v-for="l in DIM_LINES" :key="l.id">
        <polyline :ref="(el) => setRef(`${l.id}:line`, el)" class="dim-line dim-halo" />
        <polyline :ref="(el) => setRef(`${l.id}:line2`, el)" class="dim-line" />
        <line :ref="(el) => setRef(`${l.id}:t0`, el)" class="dim-tick" />
        <line :ref="(el) => setRef(`${l.id}:t1`, el)" class="dim-tick" />
      </g>
      <polyline ref="slrLeader" class="slr-leader" />
    </svg>
    <template v-if="step === 0">
      <div
        v-for="l in DIM_LINES"
        :key="l.id"
        :ref="(el) => setRef(`${l.id}:label`, el)"
        class="dim-label"
        :class="{ on: dimsOn }"
      >{{ l.label }}</div>
      <div ref="slrLabel" class="slr-label" :class="{ on: dimsOn }">
        <span class="slr-num">≈ {{ SLR_TEXT }} m</span>
        <span class="slr-unit">sea-level rise equivalent</span>
      </div>
    </template>

    <!-- The "coupling length" step (a SAMPLE): the four papers'
         cards top-left and their footprints on central-west Greenland. -->
    <Transition name="cpl-leave">
      <CouplingMap v-if="step === S.coupling" :visible="couplingOn" />
    </Transition>
    <!-- …and its door (the director asked for a "dive deeper" button that
         opens an additional-work page): Christoffersen 2018's cascade, lake
         by lake — /additional-work/revisit. A plain router-link: Explore's
         door trail brings BACK to this step. -->
    <Transition name="cpl-leave">
      <MoreDetailsPill
        v-if="step === S.coupling"
        class="cpl-deeper"
        label="Dive deeper"
        to="/additional-work/revisit"
      />
    </Transition>

    <router-link v-if="step === S.dims" class="corner-link" :to="REFS_LINK">[references]</router-link>
    <!-- (the seasons step carries IntroSeasons' own corner credit) -->

    <!-- (The "Greenland flows" step — IntroFlowSites' five call-outs — left
         the path: dims → seasons straight away.) -->

    <!-- Step 1, "the seasons": the month clock's figure labels (the globe
         itself is recoloured by the Globe from seasonDrape). Speed ↔
         Anomaly is a view on this one step, so the clock and
         the column stay put while it switches. -->
    <Transition name="sz-leave">
      <IntroSeasons
        v-if="seasonView"
        :view="seasonView"
        :visible="true"
        @view="onSeasonToggle"
      />
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import type { ComponentPublicInstance } from 'vue'
import { useRoute } from 'vue-router'
import { mediaUrl } from '../../config/media'
import { parseBeatParam } from '../../config/sitePath'
import { INTRO_STEP as S, INTRO_STEP_COUNT, INTRO_WALK } from '../../config/introSteps'
import { TIMELINE_PAPERS } from '../../config/timeline'
import IntroSeasons from '../IntroSeasons.vue'
import CouplingMap from '../CouplingMap.vue'
import MoreDetailsPill from '../MoreDetailsPill.vue'
import { CPL_ALL_ANCHORS } from '../couplingShapes'
import { seasonDrape } from '../seasonDrape'
import { disposeSeasons, seasonPlay, seasonUi, warmSeasons } from '../seasonClock'
import {
  GRIS_EAST_76,
  GRIS_LENGTH_KM,
  GRIS_NORTH,
  GRIS_SLR_M,
  GRIS_SOUTH,
  GRIS_WEST_76,
  GRIS_WIDTH_KM,
  dimLine,
  drawnLengthKm,
} from '../../config/introDims'
import {
  FW_BASEMAP_KEY,
  FW_HALF_X_M,
  FW_HALF_Y_M,
  FW_LAND_FOV_DEG,
  FW_LAT_C,
  FW_LON_C,
  FW_R_EARTH,
  FW_INTRO_CLIP_IDS,
  fwLandingFocus,
} from '../../config/fieldwork'
import type { FieldworkView } from '../FieldworkExplorer.vue'

// Internal step state. Each step requests a Globe state via the
// `globe-clicks` emit; `show-arrows` toggles the silvery 3D length-
// scale arrows; `rollback-progress` drives the DEM rollback / cross-
// section reveal on step 0; `timeline-step` mounts the literature
// timeline layer in Explore (null = hidden, 0 = shown); `advance` jumps
// to the next chapter.
// The fly-along (step 4) drives the Globe the way the
// headless chapters do — chapter-focus / chapter-exag — plus three
// intro-only knobs (strip the velocity paint, fade the hillshade, the
// Sentinel-2 patch) and the flat-map layer's state.
export interface FieldworkLayerState {
  active: boolean
  revealed: boolean
  view: FieldworkView | null
  /** The crop as a blob: URL once fetched (null = not yet; the plain URL if the fetch failed) — see fetchCrop(). */
  src: string | null
  /** Steps 5–7: the clip this step plays (FW_INTRO_CLIP_IDS); null = none. */
  clip: string | null
}
const props = defineProps<{
  /** Bumped by the shared next pill (Explore's .beat-nav). */
  advanceTrigger?: number
  /** Bumped by the shared back pill when step > 0 (at step 0 Explore
   *  takes back along the site path itself). */
  backTrigger?: number
  /** A sub-menu landmark jump (config/landmarks.ts): land on `beat` the
   *  way a `?beat=` deep link does. `seq` bumps per click. */
  jumpTo?: { beat: number; seq: number } | null
}>()
const emit = defineEmits<{
  'beat-change': [value: number, isLast: boolean]
  'screen-anchors': [value: { id: string; lat: number; lon: number; lift?: number; surface?: boolean }[] | null]
  'globe-clicks': [value: number]
  'show-arrows': [value: boolean]
  'rollback-progress': [value: number]
  'timeline-step': [value: number | null]
  /** The first timeline visit's walked paper (INTRO_WALK id; null = none). */
  'timeline-paper': [value: string | null]
  /** The four-papers step: the coupling papers lit together on the timeline. */
  'timeline-focus': [value: boolean]
  'chapter-focus': [
    value: {
      lat: number
      lon: number
      cameraLat?: number
      cameraLon?: number
      distance?: number
      fovDeg?: number
      durationMs?: number
      upNorth?: boolean
      focalOnSurface?: boolean
    } | null,
  ]
  'chapter-exag': [value: number | null]
  'chapter-exag-ms': [value: number]
  'strip-velocity': [value: boolean]
  hillshade: [value: number | null]
  'fieldwork-patch': [
    value: {
      url: string
      latC: number
      lonC: number
      halfXm: number
      halfYm: number
      rEarthM: number
      opacity: number
    } | null,
  ]
  'fieldwork-layer': [value: FieldworkLayerState | null]
  /** Steps 2–3: which map the month drape shows (Explore swaps the colorbar). */
  'season-view': [value: 'speed' | 'anom' | null]
  advance: []
}>()

const route = useRoute()

// `arrows` was supposed to show 3D silvery length-scale arrows on
// step 0; the current geometry positions them badly (the director
// rejected the look). Hidden until redesigned.
// `rollback`: target rollback amount on this step. Step 0 ramps 0→1
// over ROLLBACK_DURATION_MS to peel the east half away and reveal the
// cross-section.
// Step 4 is the FLY-ALONG: from the "it
// flows" scene the greenland object sheds its velocity paint, colour
// and streamlines and flattens into a map while the camera dives to
// the 2023 flight area; the flat Sentinel-2 map takes over pixel-
// aligned and the visitor rides the GPX tracks (FieldworkExplorer).
// Steps 2–3 are "the seasons": the same
// camera and drape as step 1, recoloured month by month from the NASA
// MEaSUREs monthly mosaics (step 2 speed, step 3 the seasonal anomaly with
// the camera on central-west Greenland), a play/scrub month clock, and the
// Russell-sector curve. So the fly-along is step 4, its three clips steps
// 5–7 and the timeline step 8 (config/introSteps.ts holds the order).
// Steps 5–7: each NEXT plays one GoPro clip on the
// landed map — the step's track lights, its panel opens bottom-left and
// plays from the start with the marker riding the track (FieldworkExplorer
// honours the layer's `clip`). No camera move, no re-decode: the map just
// stays revealed.
// Step 8 is the literature timeline, arriving with nothing
// highlighted; then the WALK: one NEXT per paper, left
// → right, each the card's hover state (steps paper-<id>, INTRO_WALK) —
// hovering another card still highlights it, and the walk's paper comes
// back when the mouse leaves. The walk stops at Stevens 2026; NEXT then
// lights the coupling step's four papers together in their colours (step
// four-papers) and goes on to the coupling step. Arriving on the timeline plays the
// fly-along in REVERSE under the timeline's backdrop (map hides, patch
// fades, camera returns, dome + hillshade + paint come back) so the globe
// sits in the "it flows" scene again — exactly what Chapter 1 used to take
// over from. With the globe left at the nadir telephoto instead, the
// Introduction → Chapter 1 handoff was a wild zoom-out (the director found
// it clunky beside the earlier version, which had the globe ready to
// go). The map layer + patch stay mounted hidden, so back from 8 → 7 is a
// 900 ms settle, not a decode.
// The timeline is visited TWICE (the director's path): first the walk
// (Rines 2026's card shown, never walked), then — after the
// coupling-length step, which strips the paint and flies to central-west
// Greenland — again with Rines 2026 highlighted and "Chapter 1" over it;
// that second visit's next is Chapter 1. The reverse fly-along only ever
// runs on the first visit (it keys on flyState, which the coupling step
// never sets); the coupling step's own camera and paint return under the
// second visit's backdrop.
interface IntroStep {
  clicks: number
  arrows: boolean
  rollback: number
  timeline: number | null
  fieldwork: boolean
  /** The month drape's map on this step (null = no month drape). */
  seasons: 'speed' | 'anom' | null
  /** The GoPro clip this step plays on the fieldwork map (null = none). */
  clip: string | null
  /** The coupling-length map (the velocity paint stripped, the camera on
   *  central-west Greenland, CouplingMap on top). */
  coupling?: boolean
  /** The first timeline visit's walk: the paper this step highlights. */
  paper?: string
  /** The four-papers step: the coupling step's four papers lit together
   *  in their comparison-page colours. */
  focus?: boolean
}
const FIELD = { clicks: 2, arrows: false, rollback: 0, timeline: null, fieldwork: true, seasons: null } as const
/** The timeline's first visit: the arrival, then one step per walked paper. */
const TIMELINE1 = { clicks: 2, arrows: false, rollback: 0, timeline: 0, fieldwork: false, seasons: null, clip: null } as const
const STEPS: IntroStep[] = [
  { clicks: 1, arrows: false, rollback: 1, timeline: null, fieldwork: false, seasons: null, clip: null }, // 0: dimensions + DEM rollback
  // (the "alive — velocity + streamlines" step and the anomaly
  // step are gone from the path; the seasons step paints the velocity
  // itself and the Speed | Anomaly switch is a view on it)
  { clicks: 2, arrows: false, rollback: 0, timeline: null, fieldwork: false, seasons: 'speed', clip: null }, // 1: the seasons · speed (+ runoff)
  { ...FIELD, clip: null }, // 2: the fly-along — lands on the three tracks, then clip 1 opens by itself
  { ...FIELD, clip: FW_INTRO_CLIP_IDS[0] }, // 3: clip 1 — the long NW–SE track
  { ...FIELD, clip: FW_INTRO_CLIP_IDS[1] }, // 4: clip 2 — the squiggly track NW of it
  { ...FIELD, clip: FW_INTRO_CLIP_IDS[2] }, // 5: clip 3 — the north-westernmost track
  { ...TIMELINE1 }, // timeline: the literature timeline, nothing highlighted (globe back in the flows scene)
  ...INTRO_WALK.map((paper) => ({ ...TIMELINE1, paper })), // paper-<id>: the walk, one paper per NEXT
  { ...TIMELINE1, focus: true }, // four-papers: the coupling step's four papers lit in their colours
  { clicks: 2, arrows: false, rollback: 0, timeline: null, fieldwork: false, seasons: null, clip: null, coupling: true }, // coupling length (SAMPLE)
  { clicks: 2, arrows: false, rollback: 0, timeline: 1, fieldwork: false, seasons: null, clip: null }, // timeline2: Rines 2026 highlighted; next → Chapter 1
]
if (STEPS.length !== INTRO_STEP_COUNT) console.error('[intro] STEPS out of step with config/introSteps.ts')
// The walk runs left → right: the timeline's card order (sorted by `when`)
// up to, not including, its last card.
if (
  [...TIMELINE_PAPERS].sort((a, b) => a.when - b.when).slice(0, -1).map((p) => p.id).join() !== INTRO_WALK.join()
) {
  console.error('[intro] INTRO_WALK out of step with the timeline\'s card order (config/timeline.ts)')
}

const step = ref(0)

// ── step 0: the object, its measuring lines, the sea-level number ─────
//
// The director asked for the greenland object bigger on the screen, a
// measuring line along the length and another across the width (hovering
// to the top left and top right of the ice sheet), a big font, and the
// ≈ 7 m number closer to the south-east tip.
//
// The camera: step 0 frames the object closer than the shared settled
// view (a chapter-focus of its own, narrower fov); step 1 flies on to its
// own top-down framing (FLOWS_FOCUS), which the fly-along and Chapter 1's
// hand-off start from. The 0.30 view shift stays (the fly-along's landing
// math depends on it); the focal is moved instead, so the object sits
// nearer the middle of the now-empty screen.
//
// The director supplied a screenshot of the camera angle wanted here —
// a low, grazing view from the south-east that looks straight at the cut
// face (the ice slab reads as a wall). The screenshot was solved for the
// camera (6 projected points — the rules' four ends, the scale arrow's
// two tips — rms 1 px): the same fov, the camera orbited down from 50°N
// 30°W at 0.925 to 38.5°N 24°W at 0.807 about the old focal (65.5°N
// 72°W), i.e. the view had been dragged there by hand. This is that
// camera, its aim tipped up a hair (focal 65.5°N 72°W → 67.4°N 91.3°W:
// the whole picture sits 5 % of the screen height lower, the angle
// unchanged) so the length rule clears the size-comparison card's corner
// on a 1440 × 900 screen too (the screenshot was ~2080 px wide).
// cameraLat 35 = Explore's Introduction `cameraTilt` (the flight used to
// land at 38.5° and a tilt lerp then yanked it to 35° — the same resting
// view, now reached by the flight alone).
const STEP0_FOCUS = {
  lat: 67.4,
  lon: -91.3,
  cameraLat: 35,
  cameraLon: -24,
  distance: 0.807,
  fovDeg: 24,
  durationMs: 1500,
}

// The two measuring arcs (config/introDims.ts): length beside the west
// coast (screen top-left in this SE-oblique view), width beyond the north
// coast (screen top-right). offsetKm slides each off the ice sheet; lift
// floats it above the sphere (world units; the arc's angular span is
// shrunk to keep its drawn length exact).
// labelAt: where along the arc (0 = first end) the label may sit, in order
// of preference — the first spot whose box clears the size-comparison
// card, the top nav, the pills and the other label wins (the director
// asked that the size-comparison card never overlap any text — the card
// is 640 px wide at every viewport, so how far up the arc the length
// label must ride depends on the viewport).
const DIM_LINES = [
  {
    ...dimLine({ id: 'len', a: GRIS_SOUTH, b: GRIS_NORTH, lengthKm: GRIS_LENGTH_KM, offsetKm: 650, lift: 0.02 }),
    label: `${GRIS_LENGTH_KM.toLocaleString('en-US')} km`,
    // Rides low on its arc when it can, then climbs toward the middle.
    labelAt: [0.18, 0.24, 0.3, 0.36, 0.42, 0.48, 0.54, 0.6, 0.66, 0.72, 0.78],
  },
  {
    ...dimLine({ id: 'wid', a: GRIS_WEST_76, b: GRIS_EAST_76, lengthKm: GRIS_WIDTH_KM, offsetKm: 950, lift: 0.02 }),
    label: `${GRIS_WIDTH_KM.toLocaleString('en-US')} km`,
    labelAt: [0.5, 0.42, 0.58, 0.34, 0.66],
  },
]
// The width label (all but fixed) is placed first; the length label yields.
const LABEL_ORDER = ['wid', 'len']
// The SE tip anchor (on the ice surface) for the sea-level label.
const SLR_ANCHOR = { id: 'slr', lat: 60.35, lon: -43.2, surface: true }
const SLR_TEXT = GRIS_SLR_M.toFixed(1)
const STEP0_ANCHORS = [
  ...DIM_LINES.flatMap((l) => l.points.map(([lat, lon], i) => ({ id: `${l.id}:${i}`, lat, lon, lift: l.lift }))),
  SLR_ANCHOR,
]
// Debug/verification: the drawn arcs' lengths in km at the object's scale.
;(window as any).__introDimLengths = Object.fromEntries(DIM_LINES.map((l) => [l.id, Math.round(drawnLengthKm(l))]))

/** Both corner links go to the References page, filtered to this chapter. */
const REFS_LINK = { path: '/references', query: { chapter: 'introduction' } }

const vw = ref(window.innerWidth)
const vh = ref(window.innerHeight)
function onResize(): void {
  vw.value = window.innerWidth
  vh.value = window.innerHeight
  obstacleAge = Infinity
}

// Element refs by key (template function refs).
const els = new Map<string, Element>()
function setRef(key: string, el: Element | ComponentPublicInstance | null): void {
  if (el instanceof Element) els.set(key, el)
  else els.delete(key)
}
const slrLabel = ref<HTMLElement | null>(null)
const slrLeader = ref<SVGPolylineElement | null>(null)

// The lines show once the step-0 camera has settled (and the anchors are
// on screen) — never sliding in from the shared view.
const dimsOn = ref(false)
let dimsTimer: number | null = null
let hudRaf: number | null = null

type Scr = { x: number; y: number; visible: boolean }
type Box = { l: number; t: number; r: number; b: number }
const TICK_PX = 12
const LABEL_GAP_PX = 18
// What the rules' labels keep clear of: Explore's size-comparison card,
// the top nav, its sub-menu and the site's pills (static CSS; re-read every ~30 frames
// since they mount on their own schedule), by LABEL_CLEAR_PX.
const OBSTACLES = ['.scale-reference', '.top-nav', '.landmarks', '.beat-nav']
const LABEL_CLEAR_PX = 16
let obstacleBoxes: Box[] = []
let obstacleAge = Infinity
function readObstacles(): Box[] {
  if (obstacleAge++ < 30) return obstacleBoxes
  obstacleAge = 0
  obstacleBoxes = []
  for (const sel of OBSTACLES) {
    const r = document.querySelector(sel)?.getBoundingClientRect()
    if (r && r.width > 0) obstacleBoxes.push({ l: r.left, t: r.top, r: r.right, b: r.bottom })
  }
  return obstacleBoxes
}
function overlaps(a: Box, others: Box[]): boolean {
  const m = LABEL_CLEAR_PX
  return others.some((o) => a.l < o.r + m && a.r > o.l - m && a.t < o.b + m && a.b > o.t - m)
}
function drawHud(): void {
  hudRaf = window.requestAnimationFrame(drawHud)
  if (step.value !== 0) return
  const scr = (window as any).__globeAnchorScreens as Record<string, Scr> | null
  if (!scr) return
  // Screen centre of the object, for "which side is outside".
  const cx = vw.value * 0.5
  const cy = vh.value * 0.5
  const taken = [...readObstacles()]
  for (const id of LABEL_ORDER) {
    const l = DIM_LINES.find((d) => d.id === id)!
    const pts: Scr[] = []
    for (let i = 0; i < l.points.length; i++) {
      const p = scr[`${l.id}:${i}`]
      if (p) pts.push(p)
    }
    if (pts.length < 2) continue
    const str = pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
    els.get(`${l.id}:line`)?.setAttribute('points', str)
    els.get(`${l.id}:line2`)?.setAttribute('points', str)
    // End ticks, perpendicular to the line's screen direction at each end.
    for (const [k, i0, i1] of [['t0', 0, 1], ['t1', pts.length - 1, pts.length - 2]] as const) {
      const a = pts[i0]
      const b = pts[i1]
      const dx = b.x - a.x
      const dy = b.y - a.y
      const n = Math.hypot(dx, dy) || 1
      const nx = -dy / n
      const ny = dx / n
      const t = els.get(`${l.id}:${k}`)
      t?.setAttribute('x1', (a.x + nx * TICK_PX).toFixed(1))
      t?.setAttribute('y1', (a.y + ny * TICK_PX).toFixed(1))
      t?.setAttribute('x2', (a.x - nx * TICK_PX).toFixed(1))
      t?.setAttribute('y2', (a.y - ny * TICK_PX).toFixed(1))
    }
    // Label on the arc (at the first clear labelAt), pushed off the line
    // on the side away from the object (the screen centre).
    const a = pts[0]
    const b = pts[pts.length - 1]
    const dx = b.x - a.x
    const dy = b.y - a.y
    const n = Math.hypot(dx, dy) || 1
    const lab = els.get(`${l.id}:label`) as HTMLElement | undefined
    if (!lab) continue
    const w = lab.offsetWidth
    const h = lab.offsetHeight
    let first: Box | null = null
    let box: Box | null = null
    for (const at of l.labelAt) {
      const m = pts[Math.round((pts.length - 1) * at)]
      let nx = -dy / n
      let ny = dx / n
      if (nx * (m.x - cx) + ny * (m.y - cy) < 0) {
        nx = -nx
        ny = -ny
      }
      // Centre the label along the normal far enough that its box's
      // nearest corner sits LABEL_GAP_PX off the line.
      const d = LABEL_GAP_PX + (Math.abs(nx) * w) / 2 + (Math.abs(ny) * h) / 2
      const lx = m.x + nx * d - w / 2
      const ly = m.y + ny * d - h / 2
      const cand = { l: lx, t: ly, r: lx + w, b: ly + h }
      first ??= cand
      if (!overlaps(cand, taken)) {
        box = cand
        break
      }
    }
    box ??= first!
    taken.push(box)
    lab.style.transform = `translate(${box.l.toFixed(1)}px, ${box.t.toFixed(1)}px)`
  }
  const s = scr[SLR_ANCHOR.id]
  if (s && slrLabel.value && slrLeader.value) {
    // Label to the right of the tip (below the south-east coast), its
    // top-left a little up-right of the tip, with a short leader.
    const h = slrLabel.value.offsetHeight
    const lx = s.x + 64
    const ly = Math.min(s.y - h * 0.35, vh.value - h - 14)
    slrLabel.value.style.transform = `translate(${lx.toFixed(1)}px, ${ly.toFixed(1)}px)`
    slrLeader.value.setAttribute(
      'points',
      `${(s.x + 4).toFixed(1)},${s.y.toFixed(1)} ${(lx - 8).toFixed(1)},${(ly + h * 0.42).toFixed(1)}`,
    )
  }
}

const ROLLBACK_DURATION_MS = 3000  // 3 s ease from 0 → target

let rollbackRafId: number | null = null
let rollbackStartT: number | null = null
let rollbackFromValue = 0
let rollbackToValue = 0
let rollbackCurrent = 0

function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}

function tickRollback(now: number): void {
  if (rollbackStartT === null) rollbackStartT = now
  const elapsed = now - rollbackStartT
  const t = Math.min(1, elapsed / ROLLBACK_DURATION_MS)
  rollbackCurrent = rollbackFromValue + (rollbackToValue - rollbackFromValue) * easeInOutCubic(t)
  emit('rollback-progress', rollbackCurrent)
  if (t < 1) {
    rollbackRafId = window.requestAnimationFrame(tickRollback)
  } else {
    rollbackRafId = null
    rollbackStartT = null
  }
}

function startRollbackRamp(target: number): void {
  if (rollbackRafId !== null) {
    window.cancelAnimationFrame(rollbackRafId)
  }
  rollbackFromValue = rollbackCurrent
  rollbackToValue = target
  rollbackStartT = null
  rollbackRafId = window.requestAnimationFrame(tickRollback)
}

// ── the fly-along choreography ────────────────────────────────────────
//
// Live (from step 1), one continuous move, ~7.5 s:
//   0        velocity paint + streamlines fade out (Globe UNSTREAM_MS
//            2.2 s); hillshade fades (2.6 s); the dome flattens to 0
//            over FLATTEN_MS (3.2 s) — the object sheds colour + relief
//   500      the dolly: oblique island view → straight down over the
//            flight area at fov 2°, north up (DOLLY_MS 6.5 s)
//   5300     the 10 m Sentinel-2 crop crossfades onto the (now flat)
//            object over PATCH_MS 1.5 s — the last stretch of the dive,
//            when the feathered crop already spans most of the frame,
//            so it reads as the landing coming into focus (an earlier
//            crossfade showed the crop as a hard sharp rectangle on the
//            coarse basemap — seen on film)
//   7000     landed: read the Globe's screen projection of the frame,
//            hand the flat map the SAME view, reveal it (0.55 s), tracks
//            draw on 0.35 s later
// Live from the step before it (the seasons' anomaly view: the month
// paint strips with the speed paint).
// Deep link (?beat=4, and 5–7 — the clip starts once the map shows):
// every target at once, 900 ms settle, then reveal.
// Back (4 → 3) and on to the timeline (7 → 8): map cut, patch fades
// (0.4 s), camera returns (Globe 1.2 s), dome re-inflates + hillshade +
// paint return — under the timeline's backdrop for 7 → 8, to the anomaly
// view (its camera, its month) for 4 → 3. Out of a clip the panel closes
// FIRST (CLIP_CLOSE_MS), then the reverse starts.
const FLATTEN_MS = 3200
const DOLLY_AT = 500
const DOLLY_MS = 6500
const PATCH_AT = 5300
const PATCH_MS = 1500
const LAND_AT = DOLLY_AT + DOLLY_MS
const SETTLE_MS = 900
// Out of a clip step onto the timeline: the clip panel slides out (the
// explorer's 0.4 s video-slide) and the track dims before the reverse
// fly-along begins.
const CLIP_CLOSE_MS = 420

// "Greenland flows" (step 1, the seasons' speed step 2, and step 8's
// backdrop — Chapter 1 starts from it): top-down with ~12° of tilt from the
// south, the whole ice sheet in frame beside the colorbar (the director
// asked for a mostly top-down view that still keeps some angle). The
// camera sits south of the ice sheet's centre (60°N 41.5°W);
// the FOCAL is panned ~450 km west of it so the sheet lands right of the
// fixed 0.30 view shift's 35 % line, centred in the space the headless
// Introduction leaves. No upNorth: the default up (radial at 72°N 40°W)
// keeps the sheet itself north-up, where north at the panned focal would
// roll it ~10°. Step 0 has its own framing (STEP0_FOCUS above).
const FLOWS_FOCUS = { lat: 70.4, lon: -57, cameraLat: 60, cameraLon: -41.5, distance: 0.93, fovDeg: 28 }
const FLOWS_MS = 2600

// The seasons' ANOMALY step (3): the camera tightens onto central-west
// Greenland (~66–72°N, the study region), where the summer band of red
// runs along the land-terminating margin — same near-top-down grammar as
// FLOWS_FOCUS (camera south of the focal, north up on screen), the focal
// on the band so it lands left of the right-hand column.
const ANOM_FOCUS = { lat: 68.4, lon: -50.2, cameraLat: 63.2, cameraLon: -49.0, distance: 0.93, fovDeg: 10 }
const ANOM_MS = 2600

// The coupling-length step (INTRO_STEP.coupling): oblique over central-west Greenland from
// the EAST — standing on the ice sheet, looking west to the coast — so the
// two regions ~150 km apart along the margin sit side by side: Christoffersen
// 2018's Kangerlussuaq sector (~67 °N) on the left, the North Lake /
// Stevens 2026 region (~68.6 °N) on the right, the order of their cards.
// (A south-west camera, Chapter 1's, stacks them north-up-left, under the
// cards.) The dome calms to Chapter 1's ~50× and the speed paint strips to
// the satellite basemap.
const COUPLING_FOCUS = { lat: 67.44, lon: -50.0, cameraLat: 67.19, cameraLon: -43.5, distance: 0.555, fovDeg: 15 }
const COUPLING_MS = 2600
const COUPLING_EXAG = 0.014
let couplingActive = false
const couplingOn = ref(false)
let couplingTimer: number | null = null

// Trails over the month drape: the comets keep flowing on speed (the step
// is "the same picture, now in time"), fainter so the colour change reads;
// off under the anomaly (red/blue is a different quantity).
const SEASON_TRAILS = { speed: 0.55, anom: 0 }

type FlyState = 'none' | 'flying' | 'landed'
let flyState: FlyState = 'none'
let flyTimers: number[] = []
let flyRaf: number | null = null
let patchOpacity = 0
let patchWanted = false
let patchPending = false
const layerState = ref<FieldworkLayerState | null>(null)

// The 15 Mpx Sentinel-2 crop is fetched ONCE, from the moment the
// Introduction mounts (step 0 lasts a while), and handed on as a blob: URL
// to both the Globe's patch texture and the flat map's <image>, which the
// map also decodes before it shows. One download, no second request that
// could still be in flight when the first lands. Before this the Globe
// drew the patch as a white feathered plate while its texture was still
// downloading — a bright flash of white before the Sentinel-2 imagery
// landed (the director saw it live; every film had waited for textures,
// so it never showed there) — and the map could reveal as a black layer.
/** The flat map's source: the blob, or the plain URL as the fallback. */
let cropSrc: string | null = null
/** The Globe's texture source: the blob, or the cors URL as the fallback
 *  (its <img crossorigin> load must never share a plain load's entry). */
let cropPatchUrl: string | null = null
let cropPromise: Promise<string | null> | null = null
/** The crop's plain URL — the map's fallback, and what the door page uses. */
const cropPlainUrl = mediaUrl(FW_BASEMAP_KEY)
/** The URL fetch() uses: the plain one with a marker query so no plain
 *  <img>/<image> load ever shares its cache entry — R2 answers no-Origin
 *  requests without Vary/ACAO, and a cors request served from such an
 *  entry is CORS-blocked in some browsers. */
const cropCorsUrl = cropPlainUrl + (cropPlainUrl.includes('?') ? '&' : '?') + 'cors=1'
async function fetchCropOnce(): Promise<string> {
  const r = await fetch(cropCorsUrl)
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  const b = await r.blob()
  const u = URL.createObjectURL(b)
  // Prove the bytes decode before anyone draws them: a 200 that is not an
  // image (a rate-limit page, an error body) would otherwise leave the
  // Globe's patch invisible and the map blank, silently.
  const im = new Image()
  im.src = u
  try {
    await im.decode()
  } catch {
    URL.revokeObjectURL(u)
    throw new Error(`not decodable (${b.type || 'no type'}, ${b.size} B)`)
  }
  return u
}
function fetchCrop(): Promise<string | null> {
  if (!cropPromise) {
    cropPromise = fetchCropOnce()
      .catch((e) => {
        console.warn('[fieldwork] crop fetch failed, retrying once:', e)
        return new Promise<void>((res) => window.setTimeout(res, 1500)).then(fetchCropOnce)
      })
      .catch((e): null => {
        // Last resort: direct URLs. The map's <image> loads the plain one
        // no-cors (always fine); the Globe's texture needs CORS and may
        // stay invisible — the dive then lands on the coarse basemap and
        // the map reveals with the imagery. Never a frozen dive.
        console.warn('[fieldwork] crop fetch failed twice — falling back to direct URLs:', e)
        return null
      })
      .then((u) => {
        cropSrc = u ?? cropPlainUrl
        cropPatchUrl = u ?? cropCorsUrl
        if (layerState.value) emitLayer({ src: cropSrc })
        return cropSrc
      })
  }
  return cropPromise
}

function later(ms: number, fn: () => void): void {
  flyTimers.push(window.setTimeout(fn, ms))
}
function clearFly(): void {
  for (const t of flyTimers) window.clearTimeout(t)
  flyTimers = []
  if (flyRaf !== null) {
    window.cancelAnimationFrame(flyRaf)
    flyRaf = null
  }
}
function emitPatch(opacity: number): void {
  patchOpacity = opacity
  patchWanted = true
  if (cropPatchUrl) {
    emit('fieldwork-patch', {
      url: cropPatchUrl,
      latC: FW_LAT_C,
      lonC: FW_LON_C,
      halfXm: FW_HALF_X_M,
      halfYm: FW_HALF_Y_M,
      rEarthM: FW_R_EARTH,
      opacity,
    })
  } else if (!patchPending) {
    // Nothing to draw until the crop is here; emit the opacity of that
    // moment when it is (the Globe ramps the texture in itself).
    patchPending = true
    fetchCrop().then(() => {
      patchPending = false
      if (patchWanted && cropPatchUrl) emitPatch(patchOpacity)
    })
  }
}
function dropPatch(): void {
  patchWanted = false
  patchOpacity = 0
  emit('fieldwork-patch', null)
}
function emitLayer(patch: Partial<FieldworkLayerState> | null): void {
  if (patch === null) {
    layerState.value = null
  } else {
    layerState.value = {
      active: patch.active ?? layerState.value?.active ?? false,
      revealed: patch.revealed ?? layerState.value?.revealed ?? false,
      view: patch.view !== undefined ? patch.view : (layerState.value?.view ?? null),
      src: patch.src !== undefined ? patch.src : (layerState.value?.src ?? cropSrc),
      clip: patch.clip !== undefined ? patch.clip : (layerState.value?.clip ?? null),
    }
  }
  emit('fieldwork-layer', layerState.value)
}
// rAF lerp of the patch's crossfade (the Globe just mirrors the prop).
function lerpPatch(to: number, ms: number, then?: () => void): void {
  const from = patchOpacity
  const t0 = performance.now()
  const tick = (now: number) => {
    const t = Math.min(1, (now - t0) / ms)
    const e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
    emitPatch(from + (to - from) * e)
    if (t < 1) flyRaf = window.requestAnimationFrame(tick)
    else {
      flyRaf = null
      then?.()
    }
  }
  if (flyRaf !== null) window.cancelAnimationFrame(flyRaf)
  flyRaf = window.requestAnimationFrame(tick)
}
function landingFocus(durationMs: number) {
  const f = fwLandingFocus()
  return {
    lat: f.lat,
    lon: f.lon,
    cameraLat: f.lat,
    cameraLon: f.lon,
    distance: f.distance,
    fovDeg: FW_LAND_FOV_DEG,
    durationMs,
    upNorth: true,
  }
}
// The flat map's view = the Globe's landing frame, solved from the three
// reference points the Globe projects (frame origin, 1 km east, 1 km
// south) — an affine map from frame metres to CSS px.
function viewFromScreen(): FieldworkView | null {
  const fs = (window as any).__fieldworkScreen as
    | { ox: number; oy: number; ex: number; ey: number; sx: number; sy: number; settled: boolean }
    | null
  if (!fs) return null
  const ax = (fs.ex - fs.ox) / 1000 // px per metre, x
  const by = (fs.sy - fs.oy) / 1000 // px per metre, y (south)
  if (!(ax > 0) || !(by > 0)) return null
  const vw = window.innerWidth
  const vh = window.innerHeight
  return { x: -fs.ox / ax, y: -fs.oy / by, w: vw / ax, h: vh / by }
}
// The Globe publishes __fieldworkScreen only once the patch mesh exists,
// i.e. once the crop is here. If it is late (or never comes), reveal at
// the deadline anyway — with the frame solved if it can be, else the
// map's default view, which is the landing frame by construction.
const REVEAL_DEADLINE_MS = 8000
/** The landing's own NEXT: the tracks' 350 ms fade + the director's 2 s pause. */
const AUTO_CLIP_AFTER_LANDING_MS = 350 + 2000
let autoClipTimer: number | null = null
function revealWhenSettled(): void {
  const t0 = performance.now()
  const tick = (now: number) => {
    const fs = (window as any).__fieldworkScreen as { settled: boolean } | null
    if (fs?.settled || now - t0 > REVEAL_DEADLINE_MS) {
      const view = viewFromScreen()
      flyState = 'landed'
      emitLayer({ active: true, revealed: true, view })
      flyRaf = null
      // The director asked that the first video start by itself once we
      // reach the field, about two seconds after the tracks appear — the
      // tracks fade in 350 ms after the reveal (FieldworkExplorer); 2 s
      // after that, the landing step takes its own NEXT. Only a landing
      // arms it (BACK from clip 1 finds the map already up and stays);
      // any step change disarms it (syncStepNow).
      if (step.value === S.flyalong) {
        autoClipTimer = window.setTimeout(() => {
          autoClipTimer = null
          if (step.value === S.flyalong) next()
        }, AUTO_CLIP_AFTER_LANDING_MS)
      }
      return
    }
    flyRaf = window.requestAnimationFrame(tick)
  }
  flyRaf = window.requestAnimationFrame(tick)
}

function enterFieldwork(live: boolean, clip: string | null): void {
  clearFly()
  flyState = 'flying'
  emit('strip-velocity', true)
  emit('hillshade', 0)
  emit('chapter-exag-ms', live ? FLATTEN_MS : SETTLE_MS)
  emit('chapter-exag', 0)
  // (A clip step's clip rides along; the explorer starts it once revealed.)
  emitLayer({ active: true, revealed: false, view: null, clip })
  if (live) {
    emitPatch(0)
    later(DOLLY_AT, () => emit('chapter-focus', landingFocus(DOLLY_MS)))
    later(PATCH_AT, () => lerpPatch(1, PATCH_MS))
    later(LAND_AT - 200, () => revealWhenSettled())
  } else {
    emit('chapter-focus', landingFocus(SETTLE_MS))
    emitPatch(1)
    later(SETTLE_MS + 100, () => revealWhenSettled())
  }
}

function leaveFieldwork(): void {
  clearFly()
  flyState = 'none'
  // The map layer + the patch stay mounted (hidden) — step 1 keeps them
  // warm (and 2, 3) so 3 → 4 → 3 → 4 never re-decodes the 15 Mpx crop.
  emitLayer({ revealed: false, clip: null })
  lerpPatch(0, 400)
  // (the camera returns to FLOWS_FOCUS — syncStep emits it for 1 and 3).
  // The speed paint + trails come back once the camera has pulled most of
  // the way out: re-painted at the nadir telephoto they filled the whole
  // screen with one saturated colour for a second.
  later(1300, () => emit('strip-velocity', false))
  later(300, () => {
    emit('chapter-exag-ms', 1500)
    emit('chapter-exag', null)
    emit('hillshade', null)
  })
}

// A step whose sync waits for the clip panel to close (clip → timeline).
let closeTimer: number | null = null
function syncStep(s: number, from: number | null): void {
  if (closeTimer !== null) {
    window.clearTimeout(closeTimer)
    closeTimer = null
  }
  // Out of a playing clip and off the map (7 → 8): close the clip first —
  // the panel slides out and the track dims — THEN reverse the dive. The
  // pills update at once; a click back within the close lands here again
  // and simply cancels it (the map never left).
  if (from !== null && STEPS[from].clip && !STEPS[s].fieldwork && flyState === 'landed') {
    emit('beat-change', s, s === STEPS.length - 1)
    emitLayer({ clip: null })
    closeTimer = window.setTimeout(() => {
      closeTimer = null
      if (step.value === s) syncStepNow(s, from)
    }, CLIP_CLOSE_MS)
    return
  }
  syncStepNow(s, from)
}
function syncStepNow(s: number, from: number | null): void {
  emit('beat-change', s, s === STEPS.length - 1)
  if (autoClipTimer !== null) {
    window.clearTimeout(autoClipTimer)
    autoClipTimer = null
  }
  if (dimsTimer !== null) {
    window.clearTimeout(dimsTimer)
    dimsTimer = null
  }
  if (idleWarmTimer !== null) {
    window.clearTimeout(idleWarmTimer)
    idleWarmTimer = null
  }
  if (s === 0) {
    // Closer framing for the dimensions (deep links settle faster).
    emit('chapter-focus', { ...STEP0_FOCUS, durationMs: from === null ? 900 : STEP0_FOCUS.durationMs })
    emit('screen-anchors', STEP0_ANCHORS)
    dimsTimer = window.setTimeout(() => {
      dimsOn.value = true
      dimsTimer = null
    }, (from === null ? 900 : STEP0_FOCUS.durationMs) + 150)
  } else {
    dimsOn.value = false
    // Step 1 publishes its five call-outs + the land envelope their labels
    // keep clear of (IntroFlowSites); steps 2–3 the curve regions' boxes
    // (IntroSeasons outlines them).
    emit('screen-anchors', STEPS[s].seasons ? seasonAnchors : null)
    // (the seasons step + both timeline visits fly to FLOWS_FOCUS below —
    // the Anomaly view to ANOM_FOCUS in onSeasonToggle; 2–5 dive; the
    // coupling step flies in syncCoupling)
  }
  if ((from === null || from === S.dims) && STEPS[s].seasons) {
    // Deep link — or the NEXT from the dims step —
    // straight onto the seasons step: hold the paint back until the month
    // data is on hand (6 s deadline), so the drape streams in already
    // wearing the month — without this ?beat=3 opened on the plain speed
    // palette and crossfaded to the anomaly a second later (film).
    emit('globe-clicks', 1)
    const want = s
    let done = false
    const go = () => {
      if (done) return
      done = true
      if (step.value === want) emit('globe-clicks', STEPS[want].clicks)
    }
    void warmSeasons().then(go, go)
    window.setTimeout(go, 6000)
  } else {
    emit('globe-clicks', STEPS[s].clicks)
  }
  emit('show-arrows', STEPS[s].arrows)
  emit('timeline-step', STEPS[s].timeline)
  emit('timeline-paper', STEPS[s].paper ?? null)
  emit('timeline-focus', !!STEPS[s].focus)
  startRollbackRamp(STEPS[s].rollback)
  let leftField = false
  if (STEPS[s].fieldwork) {
    // Live from the step before it; a settle on deep links and on the way
    // back from the timeline (the globe returned to the flows scene there).
    // Between the landing and the clips (4 ↔ 5 ↔ 6 ↔ 7) the map stays up
    // and only the clip changes.
    if (flyState === 'landed') emitLayer({ active: true, revealed: true, clip: STEPS[s].clip })
    else enterFieldwork(from === S.flyalong - 1, STEPS[s].clip)
  } else if (flyState !== 'none') {
    leaveFieldwork()
    leftField = true
  }
  syncSeasons(s)
  syncCoupling(s, from)
  // The first visit's walk is one scene: the camera flies home on the
  // arrival only — re-aimed mid-flight it would restart its ease. A deep
  // link, the way back from the coupling step, and a NEXT that cuts the
  // reverse fly-along short (leaveFieldwork ran just now) still fly.
  const walking = from !== null && STEPS[from].timeline === 0 && STEPS[s].timeline === 0 && !leftField
  if (s === S.seasons || (STEPS[s].timeline !== null && !walking)) {
    emit('chapter-focus', { ...FLOWS_FOCUS, durationMs: from === null ? 1500 : FLOWS_MS })
  }
  if (s === S.seasons) {
    warmFlyAlong()
  } else if (s === 0) {
    // Step 0 used to FREE the map + patch and leave the warm-up to step 1
    // — which put its ~0.25 s texture upload and the 30 MB month fetch on
    // the 0 → 1 click, exactly as the camera starts for the flows view
    // (found in a performance pass). The dims step is where the talk lingers:
    // warm there once the step's own moves (camera, the 3 s peel-back,
    // the inset's fade) are done. A NEXT before then warms at step 1 as
    // it always did. Nothing here is visible (patch opacity 0, map layer
    // hidden, recolour at 0).
    idleWarmTimer = window.setTimeout(() => {
      idleWarmTimer = null
      if (step.value === 0) warmFlyAlong()
    }, ROLLBACK_DURATION_MS + STEP0_IDLE_WARM_MS)
  }
}

// Warm-up for the fly-along and the month drape (idempotent), whatever
// brought us here (next, back, deep link): build the Sentinel-2 patch
// invisibly (decode + GPU upload ≈ 1 s) and mount the flat map hidden (its
// 5000 × 3000 <image> decode ≈ 0.65 s, its GPX fetches) so the fly-along's
// click pays nothing — on film, both stalls landed mid-dive
// without this. Same for the month drape: manifest, static texture and the
// opening month decoded + uploaded at zero recolour before "next".
function warmFlyAlong(): void {
  if (patchOpacity === 0 && flyState === 'none') emitPatch(0)
  if (!layerState.value?.active) emitLayer({ active: true, revealed: false, view: null })
  void warmSeasons()
}
/** Step 0's deferred warm-up (see syncStepNow). */
let idleWarmTimer: number | null = null
/** After the step-0 peel-back (ROLLBACK_DURATION_MS) — its inset fades in
 *  over its last 12 % + 0.4 s — leave the scene a moment before warming. */
const STEP0_IDLE_WARM_MS = 1500

// ── coupling length (INTRO_STEP.coupling) ──────────────────────────────────────────
// In: strip the speed paint to the basemap, calm the dome, fly to the
// central-west frame, publish the footprints' anchors, fade the map in once
// the camera has landed. Out (to either timeline visit, both under the
// timeline's backdrop): paint + dome back, the camera to FLOWS_FOCUS
// (syncStep) — so Chapter 1 takes over from the flows scene as before.
function syncCoupling(s: number, from: number | null): void {
  if (couplingTimer !== null) {
    window.clearTimeout(couplingTimer)
    couplingTimer = null
  }
  if (STEPS[s].coupling) {
    couplingActive = true
    couplingOn.value = false
    const ms = from === null ? 1200 : COUPLING_MS
    emit('strip-velocity', true)
    emit('hillshade', null)
    emit('chapter-exag-ms', from === null ? 900 : 1800)
    emit('chapter-exag', COUPLING_EXAG)
    emit('chapter-focus', { ...COUPLING_FOCUS, durationMs: ms })
    emit('screen-anchors', CPL_ALL_ANCHORS)
    couplingTimer = window.setTimeout(() => {
      couplingOn.value = true
      couplingTimer = null
    }, ms + 150)
  } else if (couplingActive) {
    couplingActive = false
    couplingOn.value = false
    emit('strip-velocity', false)
    emit('chapter-exag-ms', 1500)
    emit('chapter-exag', null)
  }
}

// ── the seasons (steps 2–3) ───────────────────────────────────────────
const seasonView = ref<'speed' | 'anom' | null>(null)
/** The curve regions' box corners, on the ice surface (from the manifest). */
let seasonAnchors: { id: string; lat: number; lon: number; surface: boolean; lift: number }[] | null = null
function syncSeasons(s: number): void {
  const v = STEPS[s].seasons
  seasonView.value = v
  emit('season-view', v)
  // Into the fly-along the month paint must strip WITH the drape (the dive
  // fades the drape's opacity): easing the recolour off at the same time
  // flashed the full speed palette for a second under the anomaly view
  // (seen on film). So the fly-along leaves the recolour where it was
  // — invisible once stripped — and 4 → 3 comes back to it unchanged.
  if (STEPS[s].fieldwork) {
    seasonUi.playing = false
    return
  }
  seasonDrape.on = v ? 1 : 0
  seasonDrape.view = v === 'anom' ? 1 : 0
  seasonDrape.trails = v ? SEASON_TRAILS[v] : 1
  if (!v) {
    if (seasonUi.playing) seasonUi.playing = false
    return
  }
  // (Deep links arrive here before the warm-up ran.)
  void warmSeasons().then(() => {
    const m = seasonUi.manifest
    if (!m) return
    if (!seasonAnchors) {
      seasonAnchors = Object.entries(m.regions)
        .filter(([, r]) => r.site)
        .flatMap(([k, r]) =>
          r.corners_latlon.map(([lat, lon], i) => ({ id: `sz:${k}:${i}`, lat, lon, surface: true, lift: 0.0004 })),
        )
    }
    if (!STEPS[step.value].seasons) return
    emit('screen-anchors', seasonAnchors)
    // The director asked for the speed and anomaly clock to start playing
    // on arrival — the click that brought us here is the click.
    if (!seasonUi.playing) seasonPlay(true)
  })
}
// The Speed | Anomaly switch (the director kept the anomaly tab but took
// it out of the deterministic NEXT pathway): a VIEW on the
// seasons step — the drape's recolour, its trails and the camera swap
// (ANOM_FOCUS on central-west, FLOWS_FOCUS back), the clock keeps running,
// the beat stays put. It used to be the step itself (Anomaly = next).
function onSeasonToggle(v: 'speed' | 'anom'): void {
  if (step.value !== S.seasons || seasonView.value === v) return
  seasonView.value = v
  emit('season-view', v)
  seasonDrape.view = v === 'anom' ? 1 : 0
  seasonDrape.trails = SEASON_TRAILS[v]
  emit('chapter-focus', v === 'anom' ? { ...ANOM_FOCUS, durationMs: ANOM_MS } : { ...FLOWS_FOCUS, durationMs: FLOWS_MS })
}

// Driven by the shared pills (Explore's .beat-nav): one step per bump.
// The last step's next leaves for Chapter 1 (`advance`); step 0's back is
// Explore's (the site path's), never bumped here.
function next(): void {
  if (step.value < STEPS.length - 1) {
    const from = step.value
    step.value += 1
    syncStep(step.value, from)
  } else {
    emit('advance')
  }
}

function prev(): void {
  if (step.value > 0) {
    const from = step.value
    step.value -= 1
    syncStep(step.value, from)
  }
}

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
// Sub-menu landmark jump: land on the step exactly as `?beat=N` does on
// mount — syncStep(s, null) is the deep-link path (settle framing, the
// fly-along's settle landing); it also tears down whatever step we left.
watch(
  () => props.jumpTo?.seq,
  () => {
    const j = props.jumpTo
    if (!j) return
    const s = Math.max(0, Math.min(STEPS.length - 1, j.beat))
    if (s === step.value) return
    step.value = s
    syncStep(s, null)
  },
)

// Sync the Globe to the current step's state on mount. `?beat=N`
// deep-links straight to step N (tools + the director's links), clamped; `last`
// is the site path's back from Chapter 1.
onMounted(() => {
  // Dev-only framing hook for the coupling step (tools re-aim the camera
  // without a rebuild): __couplingFocus({lat, lon, cameraLat, ...}).
  if (import.meta.env.DEV) {
    ;(window as any).__couplingFocus = (f: typeof COUPLING_FOCUS) => emit('chapter-focus', { ...f, durationMs: 300 })
  }
  step.value = parseBeatParam(route.query.beat, STEPS.length)
  syncStep(step.value, null)
  fetchCrop()
  window.addEventListener('resize', onResize)
  hudRaf = window.requestAnimationFrame(drawHud)
})

// On unmount, clear arrows + rollback + restore base globe state for
// other sections. Cancel any in-flight rollback animation so it doesn't
// keep firing emits at a stale parent.
onBeforeUnmount(() => {
  if (rollbackRafId !== null) {
    window.cancelAnimationFrame(rollbackRafId)
    rollbackRafId = null
  }
  if (closeTimer !== null) window.clearTimeout(closeTimer)
  clearFly()
  if (hudRaf !== null) window.cancelAnimationFrame(hudRaf)
  hudRaf = null
  if (dimsTimer !== null) window.clearTimeout(dimsTimer)
  if (idleWarmTimer !== null) window.clearTimeout(idleWarmTimer)
  if (couplingTimer !== null) window.clearTimeout(couplingTimer)
  window.removeEventListener('resize', onResize)
  emit('screen-anchors', null)
  emit('rollback-progress', 0)
  emit('globe-clicks', 1)
  emit('show-arrows', false)
  emit('timeline-step', null)
  emit('timeline-paper', null)
  emit('timeline-focus', false)
  emit('fieldwork-layer', null)
  emit('season-view', null)
  disposeSeasons()
  dropPatch()
  if (cropSrc?.startsWith('blob:')) URL.revokeObjectURL(cropSrc)
  cropSrc = null
  cropPatchUrl = null
  cropPromise = null
  emit('strip-velocity', false)
  emit('hillshade', null)
  // Explore drops these two when the next section is a headless chapter
  // (it frames itself); elsewhere they return the globe to its framing.
  emit('chapter-exag', null)
  emit('chapter-focus', null)
})
</script>

<style scoped>
/* A full-screen, click-through layer: only the corner link takes the
   mouse. Figure labels, not prose (the narrator rule) — big enough to
   read from the back of the room. */
.intro-hud {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 6;
  color: #f5f5f5;
  font-family: 'Inter', system-ui, sans-serif;
}

.dims {
  position: absolute;
  inset: 0;
  overflow: visible;
  opacity: 0;
  transition: opacity 0.7s ease;
}
.dims.on {
  opacity: 1;
}

.dim-line {
  fill: none;
  stroke: var(--gold);
  stroke-width: 2.6;
  stroke-linecap: round;
  stroke-linejoin: round;
}
/* Dark halo under the gold so the line reads over snow and black alike. */
.dim-line.dim-halo {
  stroke: rgba(0, 0, 0, 0.7);
  stroke-width: 6;
}
.dim-tick {
  stroke: var(--gold);
  stroke-width: 2.6;
  stroke-linecap: round;
}

.dim-label {
  position: absolute;
  left: 0;
  top: 0;
  font-family: 'EB Garamond', serif;
  font-size: clamp(2.2rem, 3.1vw, 3.4rem);
  line-height: 1;
  color: var(--gold);
  white-space: nowrap;
  text-shadow: 0 2px 14px rgba(0, 0, 0, 0.85), 0 0 3px rgba(0, 0, 0, 0.9);
  opacity: 0;
  transition: opacity 0.7s ease;
  will-change: transform;
}
.dim-label.on {
  opacity: 1;
}

.slr-leader {
  fill: none;
  stroke: rgba(214, 232, 255, 0.95);
  stroke-width: 2.25;
}
.slr-label {
  position: absolute;
  left: 0;
  top: 0;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  white-space: nowrap;
  text-shadow: 0 2px 14px rgba(0, 0, 0, 0.85), 0 0 3px rgba(0, 0, 0, 0.9);
  opacity: 0;
  transition: opacity 0.7s ease;
  will-change: transform;
}
.slr-label.on {
  opacity: 1;
}
.slr-num {
  font-family: 'EB Garamond', serif;
  font-size: clamp(2.2rem, 3.1vw, 3.4rem);
  line-height: 1;
  color: #d6e8ff;
}
.slr-unit {
  font-size: clamp(0.95rem, 1.15vw, 1.25rem);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgba(214, 232, 255, 0.85);
}

/* Bottom-right reference link — small, unobtrusive, real. */
.corner-link {
  position: absolute;
  right: 2vw;
  bottom: 2.2vh;
  pointer-events: auto;
  font-size: 1.05rem;
  letter-spacing: 0.04em;
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px dotted rgba(108, 204, 255, 0.6);
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.8);
}
.corner-link:hover {
  color: #fff;
  border-bottom-color: rgba(255, 255, 255, 0.7);
}

/* The coupling step's door, bottom-right: the chapters' lit door pill
   (SimBlockCards' SEE MORE FIELDS) — readable on white ice from the back
   row. */
.intro-hud .cpl-deeper {
  position: absolute;
  right: 22px;
  bottom: 22px;
  font-size: 0.98rem;
  padding: 0.5rem 1.2rem 0.55rem;
  letter-spacing: 0.1em;
  color: var(--gold-bright);
  border: 1.5px solid rgba(232, 185, 74, 0.85);
  background: rgba(8, 6, 4, 0.78);
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.55), 0 0 22px rgba(245, 199, 94, 0.18);
}
.intro-hud .cpl-deeper:hover {
  color: #fff8d8;
  border-color: var(--gold-bright);
  background: rgba(56, 38, 12, 0.88);
}

/* The coupling map leaves with a short fade (under the timeline's own
   0.6 s backdrop fade on the way to either timeline visit). */
.cpl-leave-leave-active {
  transition: opacity 0.4s ease;
}
.cpl-leave-leave-to {
  opacity: 0;
}

/* The seasons' column leaves with a fade (into the fly-along, back to
   "Greenland flows"); it rises in on its own (IntroSeasons). */
.sz-leave-leave-active {
  transition: opacity 0.5s ease;
}
.sz-leave-leave-to {
  opacity: 0;
}
/* The flows call-outs leave quickly (the camera or the month paint moves
   next); they fade in on their own once the camera has settled. */
.fs-leave-leave-active {
  transition: opacity 0.35s ease;
}
.fs-leave-leave-to {
  opacity: 0;
}
</style>
