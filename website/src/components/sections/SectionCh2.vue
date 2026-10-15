<template>
  <!-- HEADLESS (same pattern as Ch.1): Ch.2 renders no panel — this
       component drives the Globe via emits. -->
  <span class="ch2-headless" hidden />
  <!-- THE HOP's veil (the director asked to hop straight to the next lake): a
       black dip over the globe canvas only — above .globe-wrap, below
       every Ch.2 overlay (inset z 8, stress space 9, tiers 12), so the
       inset's lake number and the tiers change in the clear. -->
  <div class="ch2-hop-veil" :class="{ on: veilOn }" aria-hidden="true" />
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { mediaUrl, corsUrl } from '../../config/media'
import {
  CH2_BEAT,
  CH2_BEATS,
  CH2_PHASE,
  CH2_TEASER_FRAMES,
  CH2_TEASER_LAKE,
  CH2_TEASER_PERIOD_MS,
  ch2BlockPass,
  ch2BlockPaint,
  ch2BedRange,
  ch2IsBlockPhase,
  ch2IsResultsPhase,
  ch2IsStationPhase,
  ch2Phase,
  type Ch2Step,
} from '../../config/ch2Beats'
import { ch2T2DrapeUrl, loadCh2Phase, loadCh2Results } from '../../config/ch2Results'
import { parseBeatParam } from '../../config/sitePath'
import { loadCh2TeaserSpace } from '../../config/ch2Teaser'
import type { SimDomainPayload } from '../../config/simLakes'
import {
  CH2_DEFAULT_LAKE,
  ch2View,
  setCh2View,
} from '../../config/ch2State'

const props = defineProps<{
  advanceTrigger?: number
  backTrigger?: number
  /** A sub-menu landmark jump (config/landmarks.ts): land on `beat` the
   *  way a `?beat=` deep link does. `seq` bumps per click. */
  jumpTo?: { beat: number; seq: number } | null
  /** Which PNAS lake the zoom beat carves (set by the "Zoom in"
   *  button over the open popup). */
  selectedLakeId?: string
  /** The SECOND center lake (config/ch2Beats.ts `lakes/2` …): the block
   *  from `lakes/2` on is this lake's (1951, or 2394 when 1951 went
   *  first — Explore resolves it). */
  secondLakeId?: string
  /** Lake whose popup is open at beat 0 — the sim block pre-builds
   *  invisibly (the "Zoom in" click was choppy because the
   *  tile geometry + three shaders + five textures all built at the
   *  click; now they build during the popup idle). Also the beat-0
   *  NEXT test: no popup open → NEXT opens the chapter's lake. */
  warmLakeId?: string | null
}>()

const emit = defineEmits<{
  advance: []
  /** Beat 0's NEXT with no popup open (the deterministic path the
   *  director asked for): open this lake's popup as if it were clicked. */
  'open-lake': [id: string]
  'beat-change': [value: number, isLast: boolean]
  'globe-clicks': [value: number]
  'chapter-focus': [
    | {
        lat: number
        lon: number
        cameraLat?: number
        cameraLon?: number
        distance?: number
        fovDeg?: number
        durationMs?: number
        focalElevM?: number
        focalExag?: number
      }
    | null,
  ]
  'lake-polygons': [
    | {
        dataUrl: string
        opacity?: number
        featured?: boolean
        inert?: boolean
        keep?: { id: string; opacity: number; track?: boolean; shrink?: number } | null
      }
    | null,
  ]
  /** The teaser beat's cycle position (null off the teaser). */
  teaser: [value: { frame: number; n: number; label: string } | null]
  'chapter-exag': [value: number | null]
  /** Pre/post Sentinel-2 dates of the active lake (the tiers' label). */
  'sim-dates': [value: { pre: string; post: string } | null]
  'sim-domain': [SimDomainPayload | null]
}>()

const route = useRoute()

// The beats and their order live in config/ch2Beats.ts (the sub-menu
// reads them too); this file is their choreography.
const BEATS = CH2_BEATS
const beat = ref(0)

const CH2_FOCAL = { lat: 70.1, lon: -49.3 }
const CW_CAM_LAT = 61.6
const CW_CAM_LON = -67.2
const CW_CAM_DISTANCE_MEDIUM = 0.60
const CW_CAM_FOV_MEDIUM_DEG = 13
const PAN_MS = 1800

const CH2_EXAG = 0.014
// Zoomed-in exaggeration. True scale on this globe is
// 3500 m / 6.371e6 m × R(0.5) ≈ 2.747e-4 world per full DEM range.
// A first pass landed at 5×; the director asked for 2×.
const CH2_EXAG_ZOOM = 2.747e-4 * 2
// Zoom framing (the director asked for the block further to the left and
// bigger): closer still, and the FOCAL sits ~0.3° east of the lake so
// the block lands left-of-center — freeing the right column for the
// full-height phase-space panels.
const CH2_ZOOM_DIST = 0.528
const CH2_ZOOM_FOV = 2.0
const CH2_FOCAL_LON_EAST = 0.12
const PNAS_LAKES_URL = mediaUrl('ch02/pnas_lakes.json')
// Lake 2394 (sim 2019cw871) is the chapter's lake: beat 0's NEXT opens it and
// deep links without `?lake=` land on it (config/ch2State.ts).
const DEFAULT_LAKE = CH2_DEFAULT_LAKE
// The bed view (`bed/2`): the MGSIM page's glass + hypsometric ramp (the
// same palette PNG; the range per lake, config/ch2Beats.ts ch2BedRange).
const GLASS_A = 0.22
// The Globe's CORS load of the ramp, on its own cache key: the legend's
// plain load of the same PNG poisoned `?v=3` for anyone who ever opened
// Chapter 2 (a grey bed on the live site; config/media.ts).
const BED_PALETTE_URL = corsUrl(mediaUrl('addl/mgsim/bed_palette.png'))

interface SimDomainMeta {
  id: string
  lon: number
  lat: number
  center_surf_m: number
  domain_half_km: number
  bbox: { lon_w: number; lon_e: number; lat_s: number; lat_n: number }
  corners_lonlat: [number, number][]
  bed_off_m: number
  bed_scale_m: number
  dem: string
  bed: string
  stress: string
  stress_viscous: string
  s2_pre: string
  s2_post: string
  date_pre: string
  date_post: string
  lakes: string
  /** Absolute no-patch / with-patch σ_t1 drapes, both models. */
  stress_e_nopatch?: string
  stress_e_patch?: string
  stress_v_nopatch?: string
  stress_v_patch?: string
  /** sim_domains_v2.json: the PHYSICAL post-drainage elastic
   *  state, σ_t1 / σ_t2 of σ^V_pre + Δσ^E (the viscous no-patch tensor plus
   *  the elastic perturbation, then principals; seismic ±1 MPa, the same
   *  frame) — the elastic solves' own absolute fields (stress_e_nopatch /
   *  stress_e_patch: an elastic body loaded from an unstressed state) are
   *  no longer painted anywhere. */
  stress_s_post?: string
  stress_s_post_t2?: string
}
const simMeta = ref<Record<string, SimDomainMeta> | null>(null)

/** The lake the block under the current beat belongs to: the first
 *  center lake, or the second from `lakes/2` on. */
function activeLakeId(b: number = beat.value): string {
  return ch2BlockPass(b) === 1
    ? (props.secondLakeId ?? DEFAULT_LAKE)
    : (props.selectedLakeId ?? DEFAULT_LAKE)
}
function activeLake(): SimDomainMeta | null {
  return simMeta.value?.[activeLakeId()] ?? simMeta.value?.[DEFAULT_LAKE] ?? null
}
/** The current beat's phase (config/ch2Beats.ts) — what it IS, whichever
 *  pass it belongs to. */
const phase = computed(() => ch2Phase(beat.value))

// ─────────────────────── rAF lerp (Ch.1's pattern) ────────────────────
function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}
type Lerp = {
  rafId: number | null
  startT: number | null
  fromV: number
  toV: number
  current: number
  durationMs: number
  baseMs: number
  onTick: (v: number) => void
  /** Called once when the lerp lands (dropped by a cancel / restart). */
  done: (() => void) | null
}
function makeLerp(durationMs: number, onTick: (v: number) => void): Lerp {
  return { rafId: null, startT: null, fromV: 0, toV: 0, current: 0, durationMs, baseMs: durationMs, onTick, done: null }
}
/** Ease L toward `target` (over `ms`, else its own duration); `onDone`
 *  runs when it lands (at once if it is already there). */
function startLerp(L: Lerp, target: number, ms?: number, onDone?: () => void): void {
  // Already there, or already on its way there: no restart (a restart
  // would re-ease from mid-flight).
  if (L.toV === target && (L.rafId !== null || L.current === target)) {
    if (L.rafId !== null) L.done = onDone ?? null
    else onDone?.()
    return
  }
  if (L.rafId !== null) window.cancelAnimationFrame(L.rafId)
  L.done = onDone ?? null
  L.durationMs = ms ?? L.baseMs
  L.fromV = L.current
  L.toV = target
  L.startT = null
  const tick = (now: number) => {
    if (L.startT === null) L.startT = now
    const t = Math.min(1, (now - L.startT) / L.durationMs)
    L.current = L.fromV + (L.toV - L.fromV) * easeInOutCubic(t)
    L.onTick(L.current)
    if (t < 1) {
      L.rafId = window.requestAnimationFrame(tick)
    } else {
      L.rafId = null
      L.startT = null
      const d = L.done
      L.done = null
      d?.()
    }
  }
  L.rafId = window.requestAnimationFrame(tick)
}
function cancelLerp(L: Lerp): void {
  L.done = null
  if (L.rafId !== null) {
    window.cancelAnimationFrame(L.rafId)
    L.rafId = null
    L.startT = null
  }
}
/** Jump L to v (no animation; the next startLerp eases from here). */
function setLerp(L: Lerp, v: number): void {
  cancelLerp(L)
  L.current = v
  L.toV = v
}

// The block's choreography lerps. tileLerp
// crossfades the 25 m domain object over the coarse surface at WIDE
// framing; carveLerp sweeps the rest of the greenland object's relief
// away (knife); s2Lerp brings the face from the basemap crop to the
// pre-drainage Sentinel-2 scene (AT the landing, with
// the lake numbers, as the green polygon fades); drainLerp crossfades pre
// ↔ post imagery; lakesLerp fades the catalog outlines + numbers;
// stressLerp fades a drape; modelMixLerp crossfades elastic ↔ viscous;
// imgDiffLerp fades the imagery difference; altMixLerp fades the alt slot
// (the absolute σ_t1 drapes) over the Δσ_t1 pair, altMixBLerp the second
// alt slot over all of them (the crossfade partner).
const tileLerp = makeLerp(700, () => emitSimDomain())
const carveLerp = makeLerp(3800, () => emitSimDomain())
const s2Lerp = makeLerp(1300, () => emitSimDomain())
const drainLerp = makeLerp(1400, () => emitSimDomain())
const lakesLerp = makeLerp(1100, () => emitSimDomain())
const stressLerp = makeLerp(1200, () => emitSimDomain())
const modelMixLerp = makeLerp(500, () => emitSimDomain())
const imgDiffLerp = makeLerp(700, () => emitSimDomain())
const altMixLerp = makeLerp(900, () => emitSimDomain())
const altMixBLerp = makeLerp(900, () => emitSimDomain())
// The bed beat: the ice goes glassy (surfA 1 → GLASS_A) and the bed takes
// the hypsometric ramp (bedPalMix 0 → 1).
const glassLerp = makeLerp(900, () => emitSimDomain())
const palLerp = makeLerp(900, () => emitSimDomain())
// The outline beat: the marker stroke round the domain (progress) and its
// opacity; the teaser's twin block sliding out (config/simLakes.ts).
const markerLerp = makeLerp(1300, () => emitSimDomain())
const markerALerp = makeLerp(600, () => emitSimDomain())
const twinLerp = makeLerp(1300, () => emitSimDomain())
// The centre lake's green polygon through the dive: the six others fade,
// it shrinks from the overview's enlargement to its true footprint with
// the dolly, then fades at the landing.
const polyOthersLerp = makeLerp(600, () => emitPolys())
const polyKeepLerp = makeLerp(1200, () => emitPolys())
const polyShrinkLerp = makeLerp(5600, () => emitPolys())
/** What the two alt slots hold (the Globe's uStressTexA / uStressTexB). */
let altUrlA: string | null = null
let altUrlB: string | null = null

const ALL_LERPS = [
  tileLerp, carveLerp, s2Lerp, drainLerp, lakesLerp, stressLerp, modelMixLerp, imgDiffLerp,
  altMixLerp, altMixBLerp, glassLerp, palLerp, markerLerp, markerALerp, twinLerp,
  polyOthersLerp, polyKeepLerp, polyShrinkLerp,
]

let drainTimers: number[] = []
function later(ms: number, fn: () => void): void {
  drainTimers.push(window.setTimeout(fn, ms))
}
function clearDrainTimers(): void {
  for (const id of drainTimers) window.clearTimeout(id)
  drainTimers = []
  for (const L of ALL_LERPS) cancelLerp(L)
  stopAltWait()
}

function resetLerps(): void {
  for (const L of ALL_LERPS) setLerp(L, 0)
  altUrlA = null
  altUrlB = null
  paintedKey = ''
}

// ── The centre lake's green polygon (the seven at the lakes vantage) ──
type PolyMode = 'none' | 'lakes' | 'held'
let polyMode: PolyMode = 'none'
function emitPolys(): void {
  if (polyMode === 'none') {
    emit('lake-polygons', null)
  } else if (polyMode === 'lakes') {
    emit('lake-polygons', { dataUrl: PNAS_LAKES_URL, opacity: 1, featured: true })
  } else {
    emit('lake-polygons', {
      dataUrl: PNAS_LAKES_URL,
      opacity: polyOthersLerp.current,
      featured: true,
      inert: true,
      keep: { id: activeLakeId(), opacity: polyKeepLerp.current, track: true, shrink: polyShrinkLerp.current },
    })
  }
}
function setPolys(mode: PolyMode): void {
  polyMode = mode
  emitPolys()
}

// ── The teaser (`teaser/2`): the bed ensemble cycling every 3 s ──
const teaserOn = ref(false)
const teaserFrame = ref(0)
let teaserTimer: number | null = null
const TEASER_PRELOAD = CH2_TEASER_FRAMES.flatMap((f) => [mediaUrl(f.bed), mediaUrl(f.stress)])
function teaserFor(lake: SimDomainMeta): boolean {
  const has = lake.id === CH2_TEASER_LAKE
  // the stress space's eleven points, warm with the frame textures
  if (has) void loadCh2TeaserSpace()
  return has
}
function stopTeaserCycle(): void {
  if (teaserTimer !== null) window.clearInterval(teaserTimer)
  teaserTimer = null
}
function startTeaserCycle(): void {
  stopTeaserCycle()
  teaserTimer = window.setInterval(() => {
    teaserFrame.value = (teaserFrame.value + 1) % CH2_TEASER_FRAMES.length
    emitSimDomain()
    emitTeaser()
  }, CH2_TEASER_PERIOD_MS)
}
function emitTeaser(): void {
  const f = CH2_TEASER_FRAMES[teaserFrame.value]
  emit('teaser', teaserOn.value ? { frame: teaserFrame.value, n: CH2_TEASER_FRAMES.length, label: f.label } : null)
}

function payloadFor(lake: SimDomainMeta): SimDomainPayload {
  const ph = phase.value
  const teaser = teaserFor(lake) && (ph >= CH2_PHASE.bed)
  const frame = CH2_TEASER_FRAMES[teaserOn.value ? teaserFrame.value : 0]
  return {
    demUrl: mediaUrl(`ch02/sim/${lake.dem}`),
    bedUrl: teaser && teaserOn.value ? mediaUrl(frame.bed) : mediaUrl(`ch02/sim/${lake.bed}`),
    bedOffM: lake.bed_off_m,
    bedScaleM: lake.bed_scale_m,
    stressUrl: mediaUrl(`ch02/sim/${lake.stress}`),
    stressViscousUrl: mediaUrl(`ch02/sim/${lake.stress_viscous}`),
    s2PreUrl: mediaUrl(`ch02/sim/${lake.s2_pre}`),
    s2PostUrl: mediaUrl(`ch02/sim/${lake.s2_post}`),
    lakesUrl: mediaUrl(`ch02/sim/${lake.lakes}`),
    bbox: {
      lonW: lake.bbox.lon_w,
      lonE: lake.bbox.lon_e,
      latS: lake.bbox.lat_s,
      latN: lake.bbox.lat_n,
    },
    centerLon: lake.lon,
    centerLat: lake.lat,
    halfKm: lake.domain_half_km,
    corners: lake.corners_lonlat,
    centerSurfM: lake.center_surf_m,
    carveT: carveLerp.current,
    tileT: tileLerp.current,
    s2T: s2Lerp.current,
    drainT: drainLerp.current,
    lakesA: lakesLerp.current,
    stressT: stressLerp.current,
    modelMix: modelMixLerp.current,
    // the two alt slots (paintView): whatever they hold, at their mixes
    stressAltUrl: altUrlA ?? undefined,
    altMix: altUrlA ? altMixLerp.current : 0,
    stressAltUrlB: altUrlB ?? undefined,
    altMixB: altUrlB ? altMixBLerp.current : 0,
    imgDiffT: imgDiffLerp.current,
    // The triad stays up through the results beats (the director wanted
    // the axes kept on the Δσ pages, with the stress-space plots moved
    // over to make room for them — Ch2Results keeps clear of
    // __simDomainScreen .axesBox); only the teaser's twin owns the
    // right side.
    axesOff: ph >= CH2_PHASE.teaser,
    // The ICE FLOW arrow is Ch2FlowArrow.vue's (near the inset), not the Globe's.
    flowOverlay: true,
    // The bed + teaser beats' glass + ramp (0 elsewhere = the published look).
    surfA: 1 - (1 - GLASS_A) * glassLerp.current,
    bedPalMix: palLerp.current,
    bedPaletteUrl: BED_PALETTE_URL,
    bedVminM: ch2BedRange(lake.id)[0],
    bedVmaxM: ch2BedRange(lake.id)[1],
    markerT: markerLerp.current,
    markerA: markerALerp.current,
    // From the bed beat on, the ensemble is preloaded (twin at t = 0
    // draws nothing) so the teaser's first frame and every tick are warm.
    twin: teaser
      ? { stressUrl: mediaUrl(frame.stress), t: twinLerp.current, preload: TEASER_PRELOAD, gap: TEASER_TWIN_GAP }
      : null,
  }
}

// ── THE PAINT ──
// ONE path for everything the block's surface shows on the station beats
// (pre … diff-viscous-t1, both passes, any lake): ch2View — the beat's own
// station, or the one the visitor clicked (config/ch2State.ts: the view IS
// the override) — maps to a TARGET, and paintView moves the block there.
// The director noticed that clicking across the sequence to, for
// example, PRE DRAINAGE VISCOUS flashed the imagery on the surface
// before the stress was plotted; the block should simply shift to
// showing the stresses. The rules:
//   · imagery → a field: the drape's texture goes in invisibly, the fade
//     waits for it (the Globe's 'sim-alt-ready'), then fades in over the
//     CURRENT imagery; the imagery under it (pre-drainage under the pre
//     field, drained under the rest) changes only once it is opaque.
//   · a field → a field: a true crossfade — the pair's elastic ↔ viscous
//     mix, or the two alt slots ping-ponging (the new field loads into
//     the slot not showing and fades in over the one that is), never a
//     dip through the imagery.
//   · a field → imagery: the imagery under the opaque drape is set to the
//     target at once, then the drape fades away on its own texture.
type Target =
  | { kind: 'img'; drain: number; diff: number }
  | { kind: 'pair'; mix: number; drain: number }
  | { kind: 'alt'; url: string; drain: number }

// The textures in the Globe's two alt slots, as it announced them.
const slotReady: { A: string | null; B: string | null } = { A: null, B: null }
let lastEmit: { dem: string | null; A: string | null; B: string | null } = { dem: null, A: null, B: null }
let altWait: { slot: 'A' | 'B'; url: string; fn: () => void; timer: number } | null = null
function stopAltWait(): void {
  if (altWait) window.clearTimeout(altWait.timer)
  altWait = null
}
/** Run `fn` once `url` is really in `slot` (never fade toward the slot's
 *  previous texture); a slow texture never strands the move. */
function whenSlotReady(slot: 'A' | 'B', url: string, fn: () => void): void {
  stopAltWait()
  if (slotReady[slot] === url) {
    fn()
    return
  }
  altWait = {
    slot,
    url,
    fn,
    timer: window.setTimeout(() => {
      const w = altWait
      altWait = null
      w?.fn()
    }, 1600),
  }
}
function onSlotReady(slot: 'A' | 'B', url: string | null): void {
  slotReady[slot] = url
  if (altWait && altWait.slot === slot && altWait.url === url) {
    const w = altWait
    stopAltWait()
    w.fn()
  }
}
function onAltReadyEvt(e: Event): void {
  onSlotReady('A', (e as CustomEvent<string>).detail ?? null)
}
function onAltBReadyEvt(e: Event): void {
  onSlotReady('B', (e as CustomEvent<string>).detail ?? null)
}

/** The alt-slot drape a results step wears: the PRE-drainage σ_t1 (the
 *  viscous no-patch run — the one background both models share), the
 *  model's POST-drainage σ_t1 (viscous: the with-patch run; elastic: the
 *  superposed σ^V_pre + Δσ^E), its Δσ_t2, or null for Δσ_t1 (the
 *  published elastic/viscous pair, modelMix). */
function stepAltUrl(lake: SimDomainMeta, p: Ch2Step): string | null {
  if (p.field === 'pre' || p.field === 'post') {
    const fn = p.field === 'pre'
      ? lake.stress_v_nopatch
      : p.model === 'elastic' ? lake.stress_s_post : lake.stress_v_patch
    return fn ? mediaUrl(`ch02/sim/${fn}`) : null
  }
  return p.comp === 't2' ? ch2T2DrapeUrl(lake.id, p.model) : null
}
function viewOf(p: Ch2Step): void {
  setCh2View(p.field === 'diff' ? 'difference' : p.field, p.model)
}
/** What the view paints on this lake's block. */
function targetOfView(lake: SimDomainMeta): Target {
  const L = ch2View.layer
  const S = ch2View.stage
  if (L === 'elastic' || L === 'viscous') {
    const p: Ch2Step = { model: L, comp: 't1', field: S === 'difference' ? 'diff' : (S ?? 'pre'), emphasis: null }
    // the imagery under a field: pre-drainage under the pre field (the
    // lakes still full), drained under everything after it
    const drain = p.field === 'pre' ? 0 : 1
    const url = stepAltUrl(lake, p)
    return url ? { kind: 'alt', url, drain } : { kind: 'pair', mix: L === 'viscous' ? 1 : 0, drain }
  }
  if (S === 'difference') return { kind: 'img', drain: 1, diff: 1 }
  return { kind: 'img', drain: S === 'post' ? 1 : 0, diff: 0 }
}

/** The view last painted (lake · stage · layer) — a repeat is a no-op, so
 *  the beat's own apply and the view watcher never paint twice. */
let paintedKey = ''
function viewKey(lake: SimDomainMeta): string {
  return `${lake.id}|${ch2View.stage}|${ch2View.layer}`
}
function markPainted(): void {
  const lake = activeLake()
  paintedKey = lake ? viewKey(lake) : ''
}

/** Paint the view on the block: `live` = the moves above; else settled
 *  in one frame (deep links, jumps, the hop's swap). */
function paintView(live: boolean): void {
  const lake = activeLake()
  if (!lake) return
  const key = viewKey(lake)
  if (live && key === paintedKey) return
  paintedKey = key
  const t = targetOfView(lake)
  if (live) paintLive(t)
  else paintInstant(t)
}

/** The layers under the drape set at once (nothing of them visible). */
function layersInstant(t: Target): 'A' | 'B' | null {
  if (t.kind === 'pair') {
    setLerp(modelMixLerp, t.mix)
    setLerp(altMixLerp, 0)
    setLerp(altMixBLerp, 0)
    return null
  }
  if (t.kind !== 'alt') return null
  if (altUrlB === t.url) {
    setLerp(altMixBLerp, 1)
    return 'B'
  }
  altUrlA = t.url
  setLerp(altMixLerp, 1)
  setLerp(altMixBLerp, 0)
  return 'A'
}

function paintInstant(t: Target): void {
  stopAltWait()
  if (t.kind === 'img') {
    setLerp(stressLerp, 0)
    setLerp(drainLerp, t.drain)
    setLerp(imgDiffLerp, t.diff)
  } else {
    setLerp(stressLerp, 1)
    setLerp(drainLerp, t.drain)
    setLerp(imgDiffLerp, 0)
    layersInstant(t)
  }
  emitSimDomain()
}

/** A field's layers crossfade under a drape that is (partly) up. The
 *  composite is pair → A (altMix) → B (altMixB) on top. */
function layersCrossfade(t: Target): void {
  const a = altUrlA ? altMixLerp.current : 0
  const b = altUrlB ? altMixBLerp.current : 0
  if (t.kind === 'pair') {
    if (a < 0.001 && b < 0.001) {
      startLerp(modelMixLerp, t.mix) // elastic ↔ viscous: two textures, one mix
      return
    }
    // an alt is up: the pair goes in under it, the top fades away
    if (b > 0.001 && a > 0.001) setLerp(altMixLerp, 0)
    setLerp(modelMixLerp, t.mix)
    startLerp(altMixLerp, 0)
    startLerp(altMixBLerp, 0)
    return
  }
  if (t.kind !== 'alt') return
  const url = t.url
  if (altUrlB === url) {
    // B holds it: bring B up over whatever is under it
    startLerp(altMixBLerp, 1)
    return
  }
  if (altUrlA === url) {
    if (b > 0.001) {
      // A holds it under B: A to full (hidden), B away
      setLerp(altMixLerp, 1)
      startLerp(altMixBLerp, 0)
    } else startLerp(altMixLerp, 1)
    return
  }
  if (a < 0.001 && b < 0.001) {
    // the pair is showing: the new field into A, faded up once it is in
    altUrlA = url
    setLerp(altMixLerp, 0)
    emitSimDomain()
    whenSlotReady('A', url, () => startLerp(altMixLerp, 1))
    return
  }
  if (b >= 0.5) {
    // B is on top: the new field into A under it, then B fades away
    altUrlA = url
    setLerp(altMixLerp, 1)
    emitSimDomain()
    whenSlotReady('A', url, () => startLerp(altMixBLerp, 0))
    return
  }
  // A is on top: the new field into B over it, faded up once it is in
  if (b > 0.001) setLerp(altMixLerp, 1)
  altUrlB = url
  setLerp(altMixBLerp, 0)
  emitSimDomain()
  whenSlotReady('B', url, () => startLerp(altMixBLerp, 1))
}

function paintLive(t: Target): void {
  stopAltWait()
  const covered = stressLerp.current > 0.999
  if (t.kind === 'img') {
    if (covered) {
      // the imagery changes under the opaque drape, then the drape lifts
      setLerp(drainLerp, t.drain)
      setLerp(imgDiffLerp, t.diff)
    } else {
      startLerp(drainLerp, t.drain)
      startLerp(imgDiffLerp, t.diff)
    }
    startLerp(stressLerp, 0)
    emitSimDomain()
    return
  }
  // a field: once the drape is opaque, the imagery under it follows
  const under = () => {
    setLerp(drainLerp, t.drain)
    setLerp(imgDiffLerp, 0)
    emitSimDomain()
  }
  if (stressLerp.current < 0.001) {
    // nothing draped: the layers set invisibly, the fade waits for the
    // texture and runs over the imagery as it is
    const slot = layersInstant(t)
    emitSimDomain()
    const fadeIn = () => startLerp(stressLerp, 1, undefined, under)
    if (slot && t.kind === 'alt') whenSlotReady(slot, t.url, fadeIn)
    else fadeIn()
    return
  }
  if (covered) under()
  layersCrossfade(t)
  if (!covered) startLerp(stressLerp, 1, undefined, under)
  emitSimDomain()
}

// Warm the drapes + the results data while the block is up, in the
// TextureLoader's own request mode (CORS) so the beat's load is a cache hit.
const warmedDrapes = new Set<string>()
function warmResults(lake: SimDomainMeta): void {
  void loadCh2Phase()
  void loadCh2Results()
  // (the Δσ_t2 drapes are no longer warmed: no beat of the walk wears one
  // — config/ch2Beats.ts, THE PATH)
  const urls = [
    ...[lake.stress_v_nopatch, lake.stress_s_post, lake.stress_v_patch].filter(Boolean).map((f) => mediaUrl(`ch02/sim/${f}`)),
  ]
  for (const url of urls) {
    if (warmedDrapes.has(url)) continue
    warmedDrapes.add(url)
    const im = new Image()
    im.crossOrigin = 'anonymous'
    im.src = url
  }
}

function emitSimDomain(): void {
  // The hop's dip: the OLD block stays as it is until the swap (the beat
  // already names the new lake — a payload now would rebuild the tile
  // before the veil is down).
  if (veilOn.value && !inHopSwap) return
  const lake = activeLake()
  if (!lake) return
  emitPayload(payloadFor(lake))
}
/** Emit a payload, keeping slotReady honest: a slot whose URL changes (or
 *  a rebuilt tile) reloads in the Globe and is announced again. */
function emitPayload(d: SimDomainPayload | null): void {
  const dem = d?.demUrl ?? null
  const A = d?.stressAltUrl ?? null
  const B = d?.stressAltUrlB ?? null
  if (dem !== lastEmit.dem) {
    slotReady.A = null
    slotReady.B = null
  } else {
    if (A !== lastEmit.A) slotReady.A = null
    if (B !== lastEmit.B) slotReady.B = null
  }
  lastEmit = { dem, A, B }
  emit('sim-domain', d)
}

function emitDates(): void {
  const lake = activeLake()
  emit(
    'sim-dates',
    lake && ch2IsBlockPhase(phase.value) ? { pre: lake.date_pre, post: lake.date_post } : null,
  )
}

// ── Beat-0 warm build ──
// While a lake's popup is open, pre-build its block invisibly (all
// choreography scalars 0): geometry + shaders compile and all textures
// decode during the popup idle, so the zoom only has uniforms to move.
function syncWarm(): void {
  if (phase.value !== CH2_PHASE.lakes) return
  const id = props.warmLakeId
  const lake = id ? (simMeta.value?.[id] ?? null) : null
  if (lake) {
    resetLerps()
    emitPayload(payloadFor(lake))
  } else {
    emitPayload(null)
  }
}
watch(() => props.warmLakeId, syncWarm)

// A station click (or a deep link's tiers) on a landed station beat: the
// block moves to the view live. The beat's own apply paints first (and
// marks it), so its own view change is a no-op here.
watch(
  () => [ch2View.stage, ch2View.layer] as const,
  () => {
    if (!ch2IsStationPhase(phase.value)) return
    if (veilOn.value) return // the hop's swap paints the view as it lands
    const lake = activeLake()
    if (!lake || landedLakeId !== lake.id) return
    paintView(true)
  },
)

// ────────────────────────── beat dispatch ─────────────────────────────
let prevBeat = -1
// Which lake's block is LANDED on screen (the dive done, or settled) —
// null while diving or off the block. "Live" moves need it.
let landedLakeId: string | null = null
// Which lake the current apply used (guards the selectedLakeId watcher —
// selecting a lake and advancing happen in the SAME flush).
let appliedLakeId: string | null = null

// The bed beat looks down more steeply (the camera 1.5° south of the lake
// instead of 5.4°) so the bed reads as a map through the glass; the fov
// widens to keep the block the same size on screen.
const BED_CAM_SOUTH_DEG = 1.5
const BED_FOV_DEG = 3.6
// The teaser: the same steep view; the bed block on the LEFT, its twin
// IMMEDIATELY to its right (TEASER_TWIN_GAP block widths between them —
// the director asked for the stress-on-the-domain figure moved left,
// close to the bed-elevation figure, the bed block itself shifted a
// little left to make room, and each object as large as possible with
// nothing drawn on top of anything else), and the right column is
// Lake 1938's stress
// space (Ch2TeaserSpace, laid out from the twin's settled corner). The
// camera is SOLVED per viewport (teaserCamera) because the chrome around
// the blocks is fixed px while the blocks scale with the height.
const TEASER_TWIN_GAP = 0.04
/** The steep view's projection, fitted on 1280×800 / 1440×900 / 1920×1080
 *  (agrees to ~3 px): block width B = K_B·H/fov; its centre x = 0.35·W
 *  (the Globe's 0.30 view shift) − K_X·H·(lonEast + X0)/fov; its centre
 *  y = H/2 + H·(Y0 + K_Y·latNorth)/fov. The diamond: height 0.94 B, the
 *  top vertex 0.536 B from its left corner, the upper-left edge dropping
 *  0.80 px per px. */
const TEASER_CAM = { K_B: 3.015, K_X: 5.579, X0: 0.0013, Y0: 0.1933, K_Y: 21.22 }
function teaserCamera(): { fov: number; lonEast: number; latNorth: number } {
  const W = window.innerWidth
  const H = window.innerHeight
  // the inset (Ch2CenterLakesMap: 2vw in, min(172, 12vw) wide, 4:3 tall)
  const ir = document.querySelector('.ccl')?.getBoundingClientRect()
  const iw = Math.min(172, 0.12 * W)
  const insetR = ir && ir.width > 0 ? ir.right : 0.02 * W + iw
  const insetB = ir && ir.width > 0 ? ir.bottom : Math.max(0.07 * H, 110) + 1.333 * iw
  const KEY_H = 130 // the bed key under the block (Ch2BedLegend)
  const SPACE_CHROME = 114 // Ch2TeaserSpace's ML + MR
  const gapSpace = Math.max(24, 0.02 * W)
  const bottomMax = H - 16 - KEY_H - 14
  let best = { B: 0, L: 22, top: 0 }
  for (let L = Math.max(20, 0.015 * W); L <= 0.06 * W; L += 6) {
    for (let B = 0.75 * H; B > 0.3 * H; B -= 2) {
      if (B <= best.B) break
      // the stress plot keeps at least 0.78 of a block's width
      const P = W - 22 - L - (2 + TEASER_TWIN_GAP) * B - gapSpace - SPACE_CHROME
      if (P < 0.78 * B) continue
      const h = 0.94 * B
      const topV = L + 0.536 * B
      const topMin = Math.max(
        0.17 * H,
        insetR < topV ? insetB + 10 - 0.8 * (topV - insetR) : insetB + 10,
      )
      if (topMin + h > bottomMax) continue
      best = { B, L, top: (topMin + bottomMax - h) / 2 }
      break
    }
  }
  if (!best.B) return { fov: 6.03, lonEast: 0.307, latNorth: 0.0102 } // the 1440×900 solve
  const C = TEASER_CAM
  const fov = (C.K_B * H) / best.B
  const cx = best.L + best.B / 2
  const cy = best.top + (0.94 * best.B) / 2
  return {
    fov,
    lonEast: ((0.35 * W - cx) * fov) / (C.K_X * H) - C.X0,
    latNorth: (((cy - H / 2) * fov) / H - C.Y0) / C.K_Y,
  }
}
function zoomFocus(
  lake: SimDomainMeta,
  durationMs: number,
  camSouthDeg = 5.4,
  fovDeg = CH2_ZOOM_FOV,
  lonEast = CH2_FOCAL_LON_EAST,
  latNorth = 0,
): void {
  emit('chapter-focus', {
    lat: lake.lat + latNorth,
    // Focal east of the lake → the block sits left-of-center (the
    // right column belongs to the stress space).
    lon: lake.lon + lonEast,
    cameraLat: lake.lat + latNorth - camSouthDeg,
    cameraLon: lake.lon + lonEast,
    distance: CH2_ZOOM_DIST,
    fovDeg,
    durationMs,
    focalElevM: lake.center_surf_m,
    focalExag: CH2_EXAG_ZOOM,
  })
}
function bedFocus(lake: SimDomainMeta, ms: number): void {
  zoomFocus(lake, ms, BED_CAM_SOUTH_DEG, BED_FOV_DEG)
}
function teaserFocus(lake: SimDomainMeta, ms: number): void {
  const c = teaserCamera()
  zoomFocus(lake, ms, BED_CAM_SOUTH_DEG, c.fov, c.lonEast, c.latNorth)
}
// A window resize on the teaser re-solves its framing (debounced).
let teaserResizeTimer: number | null = null
function onTeaserResize(): void {
  if (teaserResizeTimer !== null) window.clearTimeout(teaserResizeTimer)
  teaserResizeTimer = window.setTimeout(() => {
    teaserResizeTimer = null
    const lake = activeLake()
    if (lake && teaserOn.value && phase.value === CH2_PHASE.teaser && landedLakeId === lake.id) teaserFocus(lake, 500)
  }, 250)
}
function lakesFocus(ms: number): void {
  emit('chapter-focus', {
    lat: CH2_FOCAL.lat,
    lon: CH2_FOCAL.lon,
    cameraLat: CW_CAM_LAT,
    cameraLon: CW_CAM_LON,
    distance: CW_CAM_DISTANCE_MEDIUM,
    fovDeg: CW_CAM_FOV_MEDIUM_DEG,
    durationMs: ms,
  })
}

/** Settle the landed block instantly (deep links, jumps, re-applies):
 *  carved, zoomed, framed, the catalog up. The caller sets the face. */
function settleBlock(lake: SimDomainMeta): void {
  // Under the hop's veil the camera SNAPS (one frame) — a 900 ms flight
  // there would carry it across the ice between the two domains.
  zoomFocus(lake, inHopSwap ? 1 : 900)
  emit('chapter-exag', CH2_EXAG_ZOOM)
  resetLerps()
  setLerp(tileLerp, 1)
  setLerp(carveLerp, 1)
  setLerp(s2Lerp, 1)
  setLerp(lakesLerp, 1)
  landedLakeId = lake.id
  setPolys('none')
}

/** A live move off a landed block: whatever the landing was still fading
 *  (the face, the numbers, the polygon, the marker) finishes now. */
function finishLanding(): void {
  startLerp(s2Lerp, 1)
  startLerp(tileLerp, 1)
  startLerp(carveLerp, 1)
  if (polyMode !== 'none' || markerALerp.current > 0) {
    startLerp(markerALerp, 0)
    startLerp(polyKeepLerp, 0, 500)
    later(520, () => setPolys('none'))
  }
}

/** The teaser's state on the block (glass, ramp, twin, cycle). */
function teaserState(lake: SimDomainMeta, live: boolean, cycle: boolean): void {
  const has = teaserFor(lake)
  teaserOn.value = has
  if (!live) teaserFrame.value = 0
  if (live) {
    startLerp(glassLerp, 1)
    startLerp(palLerp, 1)
    startLerp(stressLerp, 0)
    startLerp(altMixLerp, 0)
    startLerp(lakesLerp, 1)
    if (has) later(500, () => startLerp(twinLerp, 1))
  } else {
    setLerp(glassLerp, 1)
    setLerp(palLerp, 1)
    setLerp(stressLerp, 0)
    setLerp(altMixLerp, 0)
    setLerp(drainLerp, 1)
    setLerp(twinLerp, has ? 1 : 0)
  }
  emitSimDomain()
  emitTeaser()
  if (has && cycle) later(live ? 1800 : 0, startTeaserCycle)
}
function teaserOff(): void {
  stopTeaserCycle()
  if (teaserOn.value) {
    teaserOn.value = false
    teaserFrame.value = 0
    emitTeaser()
  }
}

/** The outline beat: the lakes vantage, the seven lakes with the centre
 *  lake held, the block warm (invisible), the marker stroke drawn.
 *  `fromBlock` = the cut out from a landed block (BACK, or the hand-off
 *  to the second lake): the camera pans out first, the stroke follows. */
function outlineState(fromBlock: boolean, live: boolean): void {
  emit('chapter-exag', CH2_EXAG)
  setCh2View(null)
  resetLerps()
  landedLakeId = null
  setLerp(polyOthersLerp, 1)
  setLerp(polyKeepLerp, 1)
  setPolys('held')
  lakesFocus(fromBlock ? PAN_MS : live ? PAN_MS : 900)
  emitSimDomain()
  const draw = () => {
    setLerp(markerALerp, 1)
    if (live) startLerp(markerLerp, 1)
    else setLerp(markerLerp, 1)
    emitSimDomain()
  }
  if (fromBlock && live) later(1200, draw)
  else draw()
}

/** THE ORIGINAL ZOOM (both center lakes), from the outline
 *  beat's vantage: one 5.6 s easeInOutCubic dolly with, overlapping it,
 *    0–700     the 25 m domain object crossfades in place
 *    1200–5000 the knife sweep carves the greenland object
 *    2700+     the exaggeration settles to 2×
 *  and around it the centre lake's green polygon rides
 *  the dive — shrinking with the dolly to its true footprint — and at the
 *  landing fades out as the lake numbers fade in, the Sentinel-2 face
 *  sharpening over 4400–5900 (it used to at 2400–4000, mid-dive); the
 *  marker stroke hands over to the block's own gold rim. */
function diveState(lake: SimDomainMeta): void {
  setCh2View('pre', 'imagery')
  zoomFocus(lake, 5600)
  emit('chapter-exag', CH2_EXAG)
  const markerA = markerALerp.current
  resetLerps()
  setLerp(markerLerp, 1)
  setLerp(markerALerp, markerA > 0 ? 1 : 0)
  setLerp(polyOthersLerp, 1)
  setLerp(polyKeepLerp, 1)
  setPolys('held')
  emitSimDomain()
  startLerp(polyOthersLerp, 0)
  startLerp(polyShrinkLerp, 1)
  startLerp(tileLerp, 1)
  later(1200, () => startLerp(carveLerp, 1))
  later(2700, () => emit('chapter-exag', CH2_EXAG_ZOOM))
  // The face sharpens over the dive's last stretch into the landing (any
  // later and the block shows the mid-res crop's big pixels full size).
  later(4400, () => startLerp(s2Lerp, 1, 1500))
  later(5600, () => {
    landedLakeId = lake.id
    startLerp(lakesLerp, 1)
    startLerp(polyKeepLerp, 0)
    startLerp(markerALerp, 0)
  })
  later(5600 + 1250, () => setPolys('none'))
}

// ── THE HOP between the two center lakes (the director did not want the
// LAKES view revisited between the two center-lake examples: hop
// straight to the next one — the audience catches on because the lake
// number is different and the mini map shows it) ──
// Whenever a block beat is entered while ANOTHER lake's block is landed
// (NEXT from the first lake's last results beat onto `pre/2`, BACK the
// other way, a landmark jump across, a press mid-hop), the canvas dips
// to black (VEIL_IN_MS), the beat settles under it exactly as a deep link
// does — the new lake's block carved, framed, its face set, the camera
// snapped (never flown: the domains are ~30 km apart) — and the veil
// lifts once the new block's textures are in (warmed into the HTTP cache
// beforehand, warmBlock), never on a bare block.
const veilOn = ref(false)
// The tiers hold their place through the dip (SimViewControls).
watch(veilOn, (v) => { (window as any).__ch2Hop = v })
const VEIL_IN_MS = 220
const VEIL_HOLD_MAX_MS = 1400
let hopSeq = 0
let inHopSwap = false
function hop(b: number): void {
  const seq = ++hopSeq
  veilOn.value = true
  later(VEIL_IN_MS, () => {
    if (seq !== hopSeq) return
    inHopSwap = true
    try {
      prevBeat = -1
      applyBeat(b)
    } finally {
      inHopSwap = false
    }
    // The lake numbers fade in as the veil lifts (the landing's own move)
    // — their overlays build a beat after the tile.
    setLerp(lakesLerp, 0)
    emitSimDomain()
    const t0 = performance.now()
    const lift = () => {
      if (seq !== hopSeq) return
      const waiting = ((window as any).__texturesPending ?? 0) > 0
      if (waiting && performance.now() - t0 < VEIL_HOLD_MAX_MS) {
        window.requestAnimationFrame(lift)
        return
      }
      // two frames with the textures on the GPU before it shows
      let n = 2
      const settle = () => {
        if (seq !== hopSeq) return
        if (--n > 0) window.requestAnimationFrame(settle)
        else {
          veilOn.value = false
          startLerp(lakesLerp, 1)
        }
      }
      window.requestAnimationFrame(settle)
    }
    window.requestAnimationFrame(lift)
  })
}

/** A block beat whose lake is not the one landed (or mid-hop) on screen. */
function hopNeeded(b: number): boolean {
  if (!ch2IsBlockPhase(ch2Phase(b))) return false
  const id = activeLakeId(b)
  if (veilOn.value) return true
  return landedLakeId !== null && landedLakeId !== id
}

// Warm the OTHER center lake's block (its DEM, bed, drapes, faces, lake
// outlines) while this one is up, in the loaders' own request mode, so
// the hop's rebuild is a cache hit.
const warmedBlocks = new Set<string>()
function warmBlock(lake: SimDomainMeta | null | undefined): void {
  if (!lake || warmedBlocks.has(lake.id)) return
  warmedBlocks.add(lake.id)
  for (const f of [lake.dem, lake.bed, lake.stress, lake.stress_viscous, lake.s2_pre, lake.s2_post]) {
    const im = new Image()
    im.crossOrigin = 'anonymous'
    im.src = mediaUrl(`ch02/sim/${f}`)
  }
  void fetch(mediaUrl(`ch02/sim/${lake.lakes}`)).catch(() => {})
  warmResults(lake)
}

/** Set the view to beat `b`'s own station (pre · post · the results). A
 *  fresh landing on `post` keeps a deep link's own tiers (?stage=&layer=,
 *  ?model=, the MGSIM page's hand-back). */
function beatView(b: number, ph: number, fresh: boolean): void {
  const p = ch2BlockPaint(b)
  if (p) viewOf(p)
  else if (ph === CH2_PHASE.pre) setCh2View('pre', 'imagery')
  else if (ph === CH2_PHASE.post && !(fresh && ch2View.stage !== null)) setCh2View('post', 'imagery')
}
/** A lake hop on the SAME beat (an inset click) keeps the station
 *  on screen: the new lake lands showing what the old one showed. Set by
 *  the lake watcher, cleared by any beat move. */
let keepView = false

function applyBeat(b: number): void {
  // Idempotence guard (a re-apply of the same beat on the same lake
  // must be a no-op, or the choreography restarts under the visitor).
  if (
    b >= 1 &&
    prevBeat === b &&
    appliedLakeId !== null &&
    appliedLakeId === activeLake()?.id
  ) {
    return
  }
  const ph = ch2Phase(b)
  const pph = ch2Phase(prevBeat)
  const fresh = prevBeat < 0
  clearDrainTimers()
  // the bed, teaser, outline and lakes beats paint the block themselves:
  // what paintView last painted is no longer on it
  if (!ch2IsStationPhase(ph)) paintedKey = ''
  // A newer apply abandons a hop in flight; the veil stays down only if
  // this apply hops again (below) or IS the hop's swap.
  if (!inHopSwap) {
    hopSeq++
    if (veilOn.value && !hopNeeded(b)) veilOn.value = false
  }
  emit('globe-clicks', 1)
  if (ph < CH2_PHASE.teaser || ph > CH2_PHASE.implications) teaserOff()
  else stopTeaserCycle()

  if (ph === CH2_PHASE.lakes) {
    // The lakes vantage — the chapter's opening.
    emit('chapter-exag', CH2_EXAG)
    appliedLakeId = null
    landedLakeId = null
    setCh2View(null)
    resetLerps()
    emitPayload(null)
    emit('sim-dates', null)
    lakesFocus(PAN_MS)
    setPolys('lakes')
    // A popup may already be open (back-nav) — keep its block warm.
    syncWarm()
    emit('beat-change', b, b === BEATS - 1)
    prevBeat = b
    return
  }
  const lake = activeLake()
  if (!lake) {
    // Sim metadata still loading — the simMeta watcher re-applies.
    emit('beat-change', b, b === BEATS - 1)
    return
  }
  if (ch2IsResultsPhase(ph) || (ch2IsBlockPhase(ph) && ch2BlockPass(b) === 1)) {
    // the other center lake's block, for the hop either way (not during
    // the first dive — its own textures come first)
    const other = ch2BlockPass(b) === 1 ? props.selectedLakeId : props.secondLakeId
    warmBlock(simMeta.value?.[other ?? DEFAULT_LAKE])
  }
  if (!inHopSwap && hopNeeded(b)) {
    // Another lake's block is on screen: THE HOP (above). The tiers (and
    // what reads them) take the new beat's view NOW, under the dip — not
    // the old block's paint for the veil's first quarter-second.
    appliedLakeId = lake.id
    if (!keepView) beatView(b, ph, fresh)
    emitDates()
    hop(b)
    emit('beat-change', b, b === BEATS - 1)
    prevBeat = b
    return
  }
  // "Live" = the block on screen is THIS lake's, landed, and the previous
  // beat was on it; otherwise everything settles in place.
  const sameBlock = !fresh && landedLakeId === lake.id && ch2IsBlockPhase(pph)
  appliedLakeId = lake.id
  emitDates()
  if (ph !== CH2_PHASE.bed && ph < CH2_PHASE.teaser) {
    startLerp(glassLerp, 0)
    startLerp(palLerp, 0)
    startLerp(twinLerp, 0)
  }

  if (ph === CH2_PHASE.outline) {
    // From the lakes beat: the stroke draws where the camera already is.
    // From the landed block (BACK from `pre`): the cut out, then the
    // stroke. (The second lake has no outline beat — it is the HOP.)
    const fromBlock = !fresh && pph !== CH2_PHASE.lakes
    outlineState(fromBlock, !fresh)
  } else if (ch2IsStationPhase(ph)) {
    // ── the STATION beats (pre · post · the results, both passes): the
    // view — this beat's own station, or (a lake hop from the inset) the
    // one on screen — painted by the one path (paintView) ──
    warmResults(lake)
    if (!keepView) beatView(b, ph, fresh)
    if (ph === CH2_PHASE.pre && !fresh && pph === CH2_PHASE.outline && ch2View.layer === 'imagery') {
      diveState(lake)
      markPainted()
    } else if (sameBlock) {
      // NEXT / BACK along the walk: the moves (paintLive), the catalog stays
      finishLanding()
      startLerp(lakesLerp, 1)
      paintView(true)
      if (pph === CH2_PHASE.bed) zoomFocus(lake, 1600)
    } else {
      // Deep link / landmark jump / the hop's swap: settled, painted.
      settleBlock(lake)
      paintView(false)
    }
  } else if (ph === CH2_PHASE.bed) {
    // ── the BED (the second center lake): the drained block goes glassy
    // and the bed reads through in the MGSIM page's hypsometric ramp. ──
    warmResults(lake)
    setCh2View('post', 'imagery')
    if (sameBlock) {
      finishLanding()
      teaserOn.value = false
      teaserFrame.value = 0
      stopAltWait()
      startLerp(stressLerp, 0)
      startLerp(imgDiffLerp, 0)
      startLerp(drainLerp, 1)
      startLerp(lakesLerp, 1)
      startLerp(glassLerp, 1)
      startLerp(palLerp, 1)
      startLerp(twinLerp, 0)
      bedFocus(lake, 1600)
      emitSimDomain()
    } else {
      settleBlock(lake)
      bedFocus(lake, 900)
      setLerp(drainLerp, 1)
      setLerp(glassLerp, 1)
      setLerp(palLerp, 1)
      emitSimDomain()
    }
  } else {
    // ── the TEASER, and what covers it after — the population's flat
    // page, the idealized slab (Ch2Slab.vue, its own layer) and the
    // implications' flat page (config/ch2Beats.ts; the block keeps the
    // teaser underneath, its cycle paused, so BACK onto it is seamless) ──
    setCh2View('post', 'imagery')
    // past the teaser (population · slab · implications) the block is covered
    const covered = ph > CH2_PHASE.teaser
    if (sameBlock || (!fresh && ph >= CH2_PHASE.teaser && landedLakeId === lake.id)) {
      const live = pph === CH2_PHASE.bed
      if (live) teaserFocus(lake, 1600)
      teaserState(lake, live, !covered)
    } else {
      settleBlock(lake)
      teaserFocus(lake, 900)
      teaserState(lake, false, !covered)
    }
  }

  keepView = false
  emit('beat-change', b, b === BEATS - 1)
  prevBeat = b
}

function next(): void {
  // The deterministic path (the director's): on the lakes beat,
  // NEXT first opens the chapter's lake (2394 unless one was clicked) as
  // if it were clicked; with its popup open, NEXT goes on to the outline.
  if (phase.value === CH2_PHASE.lakes && !props.warmLakeId) {
    emit('open-lake', activeLakeId())
    return
  }
  if (beat.value < BEATS - 1) {
    beat.value += 1
  } else {
    emit('advance')
  }
}
function prev(): void {
  // `slab-da` is a transit beat (the depth average plays, then lands on
  // `slab-compare` by itself): BACK from the three panels reverses to the
  // landed block, not into the animation (config/ch2Beats.ts).
  if (beat.value === CH2_BEAT['slab-compare']) beat.value = CH2_BEAT.slab
  else if (beat.value > 0) beat.value -= 1
}

watch(beat, (b) => {
  keepView = false
  applyBeat(b)
})
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
// mount (prevBeat = −1 → the settled end state, no live choreography).
watch(
  () => props.jumpTo?.seq,
  () => {
    const j = props.jumpTo
    if (!j) return
    const b = Math.max(0, Math.min(BEATS - 1, j.beat))
    if (b === beat.value) return
    prevBeat = -1
    keepView = false
    beat.value = b
  },
)
// Selected-lake change while on the block re-applies for the new lake.
watch(
  () => activeLakeId(),
  (id) => {
    if (phase.value < CH2_PHASE.outline) return
    if (id !== appliedLakeId) {
      // (an inset click: the hop lands the new lake on the same
      // station — the stress space and the key follow ch2ActiveLake)
      keepView = ch2IsStationPhase(phase.value)
      prevBeat = -1
      applyBeat(beat.value)
    }
  },
)
// Sim metadata landing late re-applies the current beat (deep links).
watch(simMeta, () => {
  if (phase.value >= CH2_PHASE.outline) {
    prevBeat = -1
    applyBeat(beat.value)
  } else syncWarm()
})

onMounted(async () => {
  window.addEventListener('sim-alt-ready', onAltReadyEvt)
  window.addEventListener('sim-altb-ready', onAltBReadyEvt)
  window.addEventListener('resize', onTeaserResize)
  try {
    const r = await fetch(mediaUrl('ch02/sim/sim_domains_v2.json'))
    if (r.ok) {
      const j = (await r.json()) as { lakes: SimDomainMeta[] }
      simMeta.value = Object.fromEntries(j.lakes.map((l) => [l.id, l]))
    }
  } catch {
    // Lakes overlay still works; the block beats wait for metadata.
  }
  const q = route.query
  // `last` = the path's back from Chapter 3 (config/sitePath.ts).
  let beatParam = parseBeatParam(q.beat, BEATS)
  // Older deep links (?drained=1 / ?model=...) and the tiers' own
  // ?stage=&layer= (Explore parsed them into ch2View) land on `post`.
  if (
    q.drained === '1' ||
    q.model === 'elastic' ||
    q.model === 'viscous' ||
    typeof q.stage === 'string'
  ) {
    beatParam = CH2_BEAT.post
  }
  beat.value = beatParam
  prevBeat = -1
  applyBeat(beat.value)
})

onBeforeUnmount(() => {
  hopSeq++
  ;(window as any).__ch2Hop = false
  window.removeEventListener('sim-alt-ready', onAltReadyEvt)
  window.removeEventListener('sim-altb-ready', onAltBReadyEvt)
  window.removeEventListener('resize', onTeaserResize)
  if (teaserResizeTimer !== null) window.clearTimeout(teaserResizeTimer)
  clearDrainTimers()
  stopTeaserCycle()
  emit('teaser', null)
  emitPayload(null)
  emit('sim-dates', null)
  emit('lake-polygons', null)
  emit('chapter-focus', null)
  emit('chapter-exag', null)
  emit('globe-clicks', 1)
})
</script>

<style scoped>
.ch2-hop-veil {
  position: absolute;
  inset: 0;
  z-index: 1;
  background: #000;
  opacity: 0;
  pointer-events: none;
  transition: opacity 280ms ease-out;
}
.ch2-hop-veil.on {
  opacity: 1;
  transition: opacity 220ms ease-in;
}
</style>
