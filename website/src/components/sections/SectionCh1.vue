<template>
  <!-- HEADLESS (at the director's request): Ch.1 renders no side panel — no
       chapter title, no beat blurbs. The presenter narrates; this
       component just drives the Globe + panels via emits. Navigation
       lives in Explore.vue's top-right beat-nav (next / back), plus the
       in-canvas anchored buttons on beats 0–3. -->
  <span class="ch1-headless" hidden />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const props = defineProps<{
  /** Parent (Explore.vue) bumps this counter to advance one beat (the
   *  in-canvas buttons + the top-right "next" pill both route through
   *  it). One bump = one advance. */
  advanceTrigger?: number
  /** Same pattern for the top-right "back" pill. */
  backTrigger?: number
  /** A sub-menu landmark jump (config/landmarks.ts): land on `beat` the
   *  way a `?beat=` deep link does. `seq` bumps per click. */
  jumpTo?: { beat: number; seq: number } | null
  /** "Where does the water go?" over North Lake's popup: from anywhere
   *  on the lakes stage (a hand-clicked popup on the lakes beat or the
   *  ND movie step) go straight to the reveal with its live flight —
   *  NEXT from the HF movie step is the same move. Bumps per click. */
  revealTrigger?: number
}>()

const emit = defineEmits<{
  advance: []
  /** Emitted whenever the active beat changes (mount, ?beat=N
   *  deeplink, prev/next, or trigger bump). Carries [beat, lastBeat]
   *  so Explore.vue can label the next pill ("next" vs "Chapter 2")
   *  and auto-dismiss the lake video when leaving Beat 0. */
  'beat-change': [value: number, isLast: boolean]
  /** Underlying Globe clicks override: 1 = snow basemap. */
  'globe-clicks': [value: number]
  /** Camera pan target. Null clears any chapter focus. `fit` asks the
   *  Globe to SOLVE the framing (focal lat/lon, distance, exag) so the
   *  slab's ±halfKm window around the fracture projects exactly onto
   *  the given screen rect — the beat 3→4 seam. The
   *  explicit lat/lon/distance double as the solver's initial guess
   *  and its fallback. */
  'chapter-focus': [
    | {
        lat: number
        lon: number
        cameraLat?: number
        cameraLon?: number
        distance?: number
        fovDeg?: number
        durationMs?: number
        fit?: {
          fracTLon: number
          halfKm: number
          rect: { x: number; y: number; w: number; h: number }
        }
      }
    | null,
  ]
  /** Lake disc marker, single feature. Null hides it. */
  'lake-overlay': [
    | {
        lat: number
        lon: number
        radiusKm?: number
        color?: string
        opacity?: number
      }
    | null,
  ]
  /** Lake-polygons overlay (featured mode = the five ESSD fig-4
   *  drainage-class lakes). Null hides + disposes. */
  'lake-polygons': [
    | {
        dataUrl: string
        opacity?: number
        baseColor?: string
        baseAlpha?: number
        highlightId?: string | null
        highlightFillColor?: string
        highlightOutlineColor?: string
        highlightScale?: number
        highlightGlow?: boolean
        featured?: boolean
        inert?: boolean
        keep?: { id: string; opacity: number } | null
      }
    | null,
  ]
  /** North Lake at cartoon scale on the surface behind the
   *  cross-section face (beats 1–2). Null hides. */
  'lake-cutaway': [
    | {
        dataUrl: string
        id: string
        cutLatDeg: number
        color: string
        opacity: number
        water: number
      }
    | null,
  ]
  /** Surface-velocity colormap + streamlines toggle. */
  'velocity-mode': [
    | {
        active: boolean
        dataUrl?: string
        highlightColor?: string
        showDashes?: boolean
        highlightOpacity?: number
      }
    | null,
  ]
  /** Unified south-to-NL knife reveal (see Globe.vue's chapterReveal
   *  prop). idealize: 1 morphs the slab's real topography into the
   *  flat rectangular Elmer/Ice domain — the beat 3 → 4 handoff rides
   *  Globe's internal 3 s uIdealize lerp (the director's intent: the
   *  topography BECOMES the rectangle, then math mode fades in over it). */
  'chapter-reveal': [
    | {
        latDeg: number
        slabOpacity?: number
        idealize?: number
        cutBasemap?: boolean
      }
    | null,
  ]
  'rollback-progress': [value: number]
  /** Vertical-exaggeration override for the chapter view. */
  'chapter-exag': [value: number | null]
  /** Cross-section slab effects: water-drain + Elmer stress paint. */
  'slab-fx': [
    value: {
      fracTLon: number
      drainT: number
      paintT?: number
      paintUrl?: string
      spinT?: number
      levelT?: number
      cropT?: number
    } | null,
  ]
  /** Theory-panel stage (beat − ch1First('field'); config/ch1Beats.ts)
   *  while the derivation beats are active; null closes the panel. */
  'theory-stage': [value: number | null]
  /** One-shot entry effect for TheoryPanel's stage-0 mount — 'seam' on
   *  the beat 3→4 morph (transparent backdrop over the camera-fit
   *  slab). Null everywhere else. */
  'theory-entry-fx': [value: 'seam' | null]
}>()

const route = useRoute()

// North Lake — confirmed from labels_2019_volumes.csv (CW2019_1889).
const NORTH_LAKE = { lat: 68.7249, lon: -49.4957, id: 'CW2019_1889' }

// Camera framing (eyes-on tuned via the Globe's __getCamera hook).
const CW_CAM_LAT = 61.6
const CW_CAM_LON = -67.2
const XSEC_CAM_LAT = 56.0
const XSEC_CAM_LON = -49.4957
const CW_CAM_DISTANCE_MEDIUM = 0.58
const CW_CAM_FOV_MEDIUM_DEG = 13
const PAN_MS = 1800

// Beat-0 landing (the director asked for the view centred on the five
// lakes, the camera slid a little up the west coast). The old
// framing aimed AT North Lake, which the Globe's 0.30 view shift draws
// at 35 % of the width, so the five lakes (68.6–70.5°N) sat in the
// top-left. Focal and camera now slide TOGETHER (same distance, fov,
// tilt — a translation, not a new angle) so the lakes' bounding box
// lands at mid-height and as near mid-width as the lake-video dock
// allows: the dock takes the right min(50vw, 760 px), and the set's
// right edge (the NL / MD cluster) stays ≥ 50 px clear of it so North
// Lake's popup never hides the lake or its "Where does the water go?"
// button. The slide is linear in u = (bbox-centre x − 0.35 W) / H —
// fitted offline on a projection model calibrated against
// __featuredLakeScreens (exact on the old framing); 0.28 H ≈ the
// distance from the bbox centre to its right edge. 1440×900 → +1.07°N
// +2.06°E; 1920×1080 → +1.58°N +0.92°E.
function beat0Slide(): { dLat: number; dLon: number } {
  const W = window.innerWidth
  const H = window.innerHeight
  const dockLeft = W - Math.min(W / 2, 760)
  const xCentre = Math.min(W / 2, dockLeft - 50 - 0.28 * H)
  const u = (xCentre - 0.35 * W) / H
  return { dLat: 1.289 + 2.348 * u, dLon: 1.570 - 5.173 * u }
}

// ── The arc — config/ch1Beats.ts owns the order and every number ───────
//   lakes    five drainage-class lakes (hover/click; legend top-right)
//   reveal   south-to-NL knife reveal ("DRAIN THE LAKE ↓" over the lake)
//   drain    hydrofracture drain ("HOW DOES THE ICE RESPOND? →")
//   paint    Elmer n=1 τxx paint ("TOY MODEL →")
//   paint→field  the slab's topography MORPHS into the flat rectangle,
//          cropping to the sim window AS it flattens, then
//          math mode fades in over it
//   field … maps  TheoryPanel stages (field+schematic → wipe+SSA → the
//          patch / boundary-layer derivation walk → ensemble → collapse
//          → log-log → ACL → ACL + the α/h Greenland maps)
//   twins    TWIN GLOBES: two live 3D Greenlands — ACL (left) and max
//          surface stress (right), τ_val/ℓ sliders between them
//   takeaway the twins dimmed, the chapter's takeaway popped into a card
//          (Explore's TakeawayPop; nothing here changes — the twins
//          stay up; NEXT from it is the twins' close into Chapter 2)
const BEATS = CH1_BEATS
const beat = ref(0)

// The lakes beat + its two movie steps: the
// globe holds the same five-lake view; Explore opens each step's popup.
const isLakesStage = ch1IsLakesStage
const REVEAL_BEAT = ch1First('reveal')
const DRAIN_BEAT = ch1First('drain')
const PAINT_BEAT = ch1First('paint')
const THEORY_FIRST_BEAT = CH1_THEORY_FIRST
const THEORY_LAST_BEAT = CH1_THEORY_LAST
const TWIN_BEAT = ch1First('twins')

import { mediaUrl } from '../../config/media'
import { parseBeatParam } from '../../config/sitePath'
import { CH1_BEATS, CH1_THEORY_FIRST, CH1_THEORY_LAST, ch1First, ch1IsLakesStage } from '../../config/ch1Beats'
import { theoryFieldScreenRect, TP_HALF_KM } from '../../config/theoryLayout'
const FEATURED_LAKES_URL = mediaUrl('ch01/featured_lakes.json')
// n=1 (Newtonian) hero paint — the chapter is n=1 throughout.
const TAU_PAINT_URL = mediaUrl('ch01/tau_paint_n1.png')

// North Lake's position along the chapter slab, as the 0..1 tLon
// fraction Globe's slab shader uses (slab spans −58°..−12°).
const NL_FRAC_TLON = (-49.4957 - -58) / (-12 - -58)

// ─────────────────────── rAF utility ──────────────────────────────────
function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}

type Lerp = {
  rafId: number | null
  startT: number | null
  fromV: number
  toV:   number
  current: number
  durationMs: number
  onTick: (v: number) => void
}

function makeLerp(durationMs: number, onTick: (v: number) => void): Lerp {
  return { rafId: null, startT: null, fromV: 0, toV: 0, current: 0, durationMs, onTick }
}

function startLerp(L: Lerp, target: number): void {
  if (L.rafId !== null) window.cancelAnimationFrame(L.rafId)
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
    }
  }
  L.rafId = window.requestAnimationFrame(tick)
}

function cancelLerp(L: Lerp): void {
  if (L.rafId !== null) {
    window.cancelAnimationFrame(L.rafId)
    L.rafId = null
    L.startT = null
  }
}

// ──────────────────── per-feature lerp state ──────────────────────────

// Featured-lakes overlay opacity (Beat 0).
const FLASH_IN_MS = 700
const flashLerp = makeLerp(FLASH_IN_MS, (v) => emitLakePolygons(v))

// Beat-1 south-to-NL peel.
const REVEAL_MS = 3500
const SOUTH_PEEL_START_LAT = 59
const SOUTH_PEEL_END_LAT   = 68.6
const revealLerp = makeLerp(REVEAL_MS, (v) => {
  emitSouthPeel(v)
  emitLakeCutaway()
  if (nlHandoff) emitLakePolygons(flashLerp.current)
})

// Beat-2 water drain and Beat-3 stress paint fade.
const DRAIN_MS = 3200
const PAINT_MS = 2200
const drainLerp = makeLerp(DRAIN_MS, () => {
  emitSlabFx()
  // Beat 2: the surface outline's water empties with the lens.
  emitLakeCutaway()
})
const paintLerp = makeLerp(PAINT_MS, () => emitSlabFx())

// ── Beat 3 → 4 handoff: "the cross-section BECOMES the model domain" ──
// ONE continuous same-object motion (the director's rule — no fade to
// black, no separate pieces):
//   1. Globe's 3 s uIdealize lerp — the painted topography flattens
//      into the rectangle, in place.
//   2. The idealized tilt levels out (levelT) — the object settles into
//      diagram proportions.
//   3. The slab spins 180° about the fracture's radial axis (spinT) —
//      the flow direction visibly flips IN 3-D (globe flows right→left,
//      the simulation domain left→right).
//   4. The camera dives in with a FIT solve: the Globe computes the
//      framing (and vertical exaggeration) that lands the slab's ±40 km
//      window EXACTLY on the theory panel's stage-0 field rect.
//   5. The panel enters with a transparent backdrop ('seam'): its field
//      image fades in over the identical-looking slab, the chalkboard
//      then dims the surroundings.
let morphTimers: number[] = []
function clearMorphTimers(): void {
  for (const id of morphTimers) window.clearTimeout(id)
  morphTimers = []
  cancelLerp(spinLerp)
  cancelLerp(levelLerp)
  cancelLerp(cropLerp)
}
const spinLerp = makeLerp(2000, () => emitSlabFx())
const levelLerp = makeLerp(1200, () => emitSlabFx())
const cropLerp = makeLerp(2600, () => emitSlabFx())

function emitSlabFx(): void {
  emit('slab-fx', {
    fracTLon: NL_FRAC_TLON,
    drainT: drainLerp.current,
    paintT: paintLerp.current,
    paintUrl: TAU_PAINT_URL,
    spinT: spinLerp.current,
    levelT: levelLerp.current,
    cropT: cropLerp.current,
  })
}

// Beat 0's five lakes. Leaving the lakes stage they fade out during the
// flight (inert — no popup mid-fade) instead of vanishing on the click.
// North Lake's own outline does NOT fade with them (the director's rule:
// it never disappears until the lake drains): on the live
// lakes → reveal flight it stays at full opacity and hands over to the
// cartoon-scale cutaway exactly as that fades in (the same smoothstep of
// the reveal, emitLakeCutaway) — the outline is never off the screen.
let nlHandoff = false
function nlKeepOpacity(): number {
  return 1 - smoothstep(0.9, 1, revealLerp.current)
}
function emitLakePolygons(opacity: number): void {
  const keep = nlHandoff ? nlKeepOpacity() : null
  if (opacity <= 0.001 && !(keep !== null && keep > 0.001)) {
    emit('lake-polygons', null)
    return
  }
  emit('lake-polygons', {
    dataUrl: FEATURED_LAKES_URL,
    opacity,
    featured: true,
    inert: !isLakesStage(beat.value),
    keep: keep !== null ? { id: NORTH_LAKE.id, opacity: keep } : null,
  })
}

// North Lake on beats 1–2 (the director asked that its outline stay
// visible through these beats). Its true footprint is inside the
// cut-away volume and ~3 km across, so Globe draws it at the slab lens's
// cartoon scale with the face through its middle (Globe
// buildLakeCutaway), as on beat 0 (green fill, dark rim). Beat 1: fades
// in as the knife arrives. Beat 2: empties in step with the lens (the
// slab shader's lakeFill = 1 − drainT/0.6); the slab's green basin rim
// keeps the lake's outline in the section through beat 2 (and fades
// under the beat-3 paint).
const NORTH_LAKE_CLASS_COLOR = '#4caf50' // HF — DrainageLegend / ESSD
function smoothstep(e0: number, e1: number, x: number): number {
  const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0)))
  return t * t * (3 - 2 * t)
}
function emitLakeCutaway(): void {
  const b = beat.value
  let opacity = 0
  let water = 1
  if (b === REVEAL_BEAT) {
    opacity = smoothstep(0.9, 1, revealLerp.current)
  } else if (b === DRAIN_BEAT) {
    opacity = 1
    water = 1 - Math.min(1, drainLerp.current / 0.6)
  }
  if (opacity <= 0.001) {
    emit('lake-cutaway', null)
    return
  }
  emit('lake-cutaway', {
    dataUrl: FEATURED_LAKES_URL,
    id: NORTH_LAKE.id,
    cutLatDeg: SOUTH_PEEL_END_LAT,
    color: NORTH_LAKE_CLASS_COLOR,
    opacity,
    water,
  })
}

function emitSouthPeel(progress: number): void {
  const lat = SOUTH_PEEL_START_LAT + (SOUTH_PEEL_END_LAT - SOUTH_PEEL_START_LAT) * progress
  emit('chapter-reveal', {
    latDeg: lat,
    slabOpacity: 1,
    idealize: 0,
    cutBasemap: true,
  })
}

// ────────────────────────── beat dispatch ─────────────────────────────

let prevBeat = -1

function applyBeat(b: number): void {
  clearMorphTimers()

  // Outside the live 3→4 morph, the slab's flip/level state resets —
  // back-nav to the globe beats must show the un-mirrored, tilted slab.
  if (!(b === THEORY_FIRST_BEAT && prevBeat === PAINT_BEAT)) {
    spinLerp.current = 0
    levelLerp.current = 0
    cropLerp.current = 0
  }

  // ── Camera ──
  if (b >= TWIN_BEAT) {
    // Twin-globes beat: opaque panel covers the main globe; leave the
    // camera where it is (returning "back" restores framing below).
  } else if (isLakesStage(b)) {
    // A movie step arriving from the lakes stage holds the view (no
    // camera move); anything else lands on the five-lake framing.
    if (!isLakesStage(prevBeat)) {
      const { dLat, dLon } = beat0Slide()
      emit('chapter-focus', {
        lat: NORTH_LAKE.lat + dLat,
        lon: NORTH_LAKE.lon + dLon,
        cameraLat: CW_CAM_LAT + dLat,
        cameraLon: CW_CAM_LON + dLon,
        distance: CW_CAM_DISTANCE_MEDIUM,
        fovDeg: CW_CAM_FOV_MEDIUM_DEG,
        durationMs: PAN_MS,
      })
    }
  } else {
    // Beats 1..11: head-on at the cross-section face; the drain/paint
    // beats (2–3) dolly in further so the zoom-in MOTION survives.
    // The beat-0→1 flight ("Where does the water go?") was once a
    // 1.8 s whip across half the island that landed mid-peel and read
    // as a cut — it now takes 3.4 s, paced with the reveal.
    const zoomed = b === DRAIN_BEAT || b === PAINT_BEAT
    emit('chapter-focus', {
      lat: NORTH_LAKE.lat + 0.9,
      lon: NORTH_LAKE.lon,
      cameraLat: XSEC_CAM_LAT,
      cameraLon: XSEC_CAM_LON,
      distance: zoomed ? 0.60 : 0.64,
      fovDeg: zoomed ? 11 : 16,
      durationMs: b === REVEAL_BEAT && isLakesStage(prevBeat) ? 3400 : PAN_MS,
    })
  }

  // Snow basemap throughout.
  emit('globe-clicks', 1)

  // ── Knife reveal + slab (beats 1..11) ──
  if (b === REVEAL_BEAT) {
    if (isLakesStage(prevBeat)) {
      // Live arrival: let the camera's first ~600 ms read as pure
      // flight, then the peel front crosses while it's still moving —
      // one continuous motion instead of two stacked jolts.
      morphTimers.push(window.setTimeout(() => startLerp(revealLerp, 1), 600))
    } else {
      startLerp(revealLerp, 1)
    }
  } else if (b >= DRAIN_BEAT && b <= THEORY_LAST_BEAT) {
    cancelLerp(revealLerp)
    revealLerp.current = 1
    emit('chapter-reveal', {
      latDeg: SOUTH_PEEL_END_LAT,
      slabOpacity: 1,
      // Beats ≥ 4 park the slab idealized. When ARRIVING from beat 3
      // this same emit is what kicks Globe's 3 s uIdealize morph —
      // the painted topography visibly becomes the flat rectangle.
      idealize: b >= THEORY_FIRST_BEAT ? 1 : 0,
      cutBasemap: true,
    })
  } else if (isLakesStage(b)) {
    // WARM the slab during beat 0 — build geometry + compile
    // its shader invisibly (opacity 0, basemap uncut) while the lake
    // popup idles, so the "Where does the water go?" click only moves
    // uniforms. (Pacing the flight was the first fix; the residual hitch
    // was the slab's lazy build + first-render program link.)
    cancelLerp(revealLerp)
    revealLerp.current = 0
    emit('chapter-reveal', {
      latDeg: SOUTH_PEEL_START_LAT,
      slabOpacity: 0,
      idealize: 0,
      cutBasemap: false,
    })
  } else {
    cancelLerp(revealLerp)
    revealLerp.current = 0
    emit('chapter-reveal', null)
  }

  // ── Water drain + stress paint (slab-fx) ──
  if (b < DRAIN_BEAT || b >= TWIN_BEAT) {
    cancelLerp(drainLerp)
    cancelLerp(paintLerp)
    drainLerp.current = 0
    paintLerp.current = 0
    emit('slab-fx', null)
  } else {
    if (b === DRAIN_BEAT) {
      cancelLerp(paintLerp)
      paintLerp.current = 0
      drainLerp.current = 0
      startLerp(drainLerp, 1)
    } else if (b === PAINT_BEAT) {
      cancelLerp(drainLerp)
      drainLerp.current = 1
      paintLerp.current = 0
      startLerp(paintLerp, 1)
    } else {
      cancelLerp(drainLerp)
      cancelLerp(paintLerp)
      drainLerp.current = 1
      paintLerp.current = 1
      emitSlabFx()
    }
  }

  // ── Drainage-class lakes: beat 0 only; they fade out on the flight
  //    to the cross-section. ──
  nlHandoff = false
  if (isLakesStage(b)) {
    if (flashLerp.current < 1) startLerp(flashLerp, 1)
    else emitLakePolygons(1) // a movie step: refresh `inert`, no re-fade
  } else if (b === REVEAL_BEAT && isLakesStage(prevBeat) && flashLerp.current > 0.001) {
    nlHandoff = true
    startLerp(flashLerp, 0)
  } else {
    cancelLerp(flashLerp)
    flashLerp.current = 0
    emit('lake-polygons', null)
  }

  // ── North Lake on the surface (beats 1–2; see emitLakeCutaway).
  //    After the reveal + slab-fx blocks so it reads their reset values. ──
  emitLakeCutaway()

  // ── Theory panel ──
  if (b >= THEORY_FIRST_BEAT && b <= THEORY_LAST_BEAT) {
    if (b === THEORY_FIRST_BEAT && prevBeat === PAINT_BEAT) {
      // One fluid same-object motion, retimed once after a first
      // pass: flatten → level → 3-D flip → fit-dolly → seam entry.
      // Every phase OVERLAPS its neighbors — the eased segments hand
      // velocity to each other so the motion never stops and restarts
      // (the first version had dead gaps between phases and read as
      // choppy).
      emit('theory-stage', null)
      const later = (ms: number, fn: () => void) =>
        morphTimers.push(window.setTimeout(fn, ms))
      // No zoom-out (the director asked for the crop to the simulation
      // domain AT THE SAME TIME as the topography goes flat, then the
      // flip and fade): flatten (Globe's 3.4 s uIdealize,
      // kicked by the b>=2 reveal emit above), CROP (0–2600) and level
      // (400–1600) all run together from the first frame; the fit
      // dolly rides along from 250 (4.0 s) so the camera tracks the
      // condensing object continuously; the flip turns the ALREADY
      // compact domain (2400–4400); the seam lands at 4600.
      startLerp(cropLerp, 1)
      later(400, () => startLerp(levelLerp, 1))
      later(800, () => startLerp(drainLerp, 0))
      later(250, () => {
        emit('chapter-focus', {
          lat: 69.05,
          lon: NORTH_LAKE.lon,
          cameraLat: XSEC_CAM_LAT,
          cameraLon: XSEC_CAM_LON,
          distance: 0.585,
          fovDeg: 7,
          durationMs: 4000,
          fit: {
            fracTLon: NL_FRAC_TLON,
            halfKm: TP_HALF_KM,
            rect: theoryFieldScreenRect(window.innerWidth, window.innerHeight),
          },
        })
      })
      later(2400, () => startLerp(spinLerp, 1))
      later(4600, () => {
        // Panel reveal starts in the dolly's last ~100 ms (sub-pixel
        // motion) so the crossfade masks the stop.
        emit('theory-entry-fx', 'seam')
        emit('theory-stage', 0)
      })
    } else {
      emit('theory-entry-fx', null)
      emit('theory-stage', b - THEORY_FIRST_BEAT)
    }
  } else {
    emit('theory-entry-fx', null)
    emit('theory-stage', null)
  }

  // Chapter exag: calm 50× dome throughout the globe beats. The twin
  // globes render their own scenes, so the override is irrelevant
  // there — keep it so returning "back" needs no re-lerp.
  emit('chapter-exag', CH1_EXAG)

  emit('beat-change', b, b === BEATS - 1)
  prevBeat = b
}

function next(): void {
  if (beat.value < BEATS - 1) {
    beat.value += 1
  } else {
    emit('advance')
  }
}
function prev(): void {
  if (beat.value > 0) beat.value -= 1
}

watch(beat, (b) => applyBeat(b))

// Parent-driven advance / back (top-right pills + in-canvas buttons).
// One step per distinct counter value.
watch(
  () => props.advanceTrigger,
  (v, old) => {
    if (v == null || v === old) return
    next()
  }
)
watch(
  () => props.backTrigger,
  (v, old) => {
    if (v == null || v === old) return
    prev()
  }
)
// "Where does the water go?" — the live lakes-stage → reveal flight.
watch(
  () => props.revealTrigger,
  (v, old) => {
    if (v == null || v === old) return
    if (isLakesStage(beat.value)) beat.value = REVEAL_BEAT
  }
)
// Sub-menu landmark jump: land on the beat exactly as `?beat=N` does on
// mount (prevBeat = −1 → the beat's end state, no live choreography).
watch(
  () => props.jumpTo?.seq,
  () => {
    const j = props.jumpTo
    if (!j) return
    const b = Math.max(0, Math.min(BEATS - 1, j.beat))
    if (b === beat.value) return
    prevBeat = -1
    beat.value = b
  }
)

// Chapter-wide vertical exaggeration (≈50×), tuned by eye.
const CH1_EXAG = 0.014

// Warm the browser cache for the theory panel's stage-0 assets — the
// seam handoff (beat 3→4) crossfades the panel's field image over the
// slab, so that image must ALREADY be resident or the seam shows a
// dark gap while it fetches.
function preloadTheoryAssets(): void {
  const urls = [
    mediaUrl('ch01/field2d_n1.png'),
    mediaUrl('ch01/theory_n1.json'),
    // Field-stage LaTeX (ch01/eq2/, build_theory_eqs.py) + the SSA
    // pieces that replace the Stokes system after the wipe.
    ...['stokes', 'slide', 'slide0', 'lbl_h', 'lbl_alpha', 'lbl_ell', 'ax_field_tau',
      'sweep_zh', 'ssa_mem', 'ssa_drag', 'ssa_grav'].map((n) => mediaUrl(`ch01/eq2/${n}.svg`)),
    // ACL stage + the maps beat — fetched early so the late
    // beats never decode on a click.
    mediaUrl('ch01/eq2/acl.svg'),
    mediaUrl('ch01/eq2/taumax.svg'),
    mediaUrl('ch01/alpha_map_fig2.png'),
    mediaUrl('ch01/h_map_fig2.png'),
  ]
  for (const u of urls) {
    // mediaUrl() stamps ?v=N — test the PATH's extension,
    // not the whole URL (a JSON warmed as an <img> is ORB-blocked).
    if (u.split('?')[0].endsWith('.json')) {
      fetch(u).catch(() => {})
    } else {
      // Plain (no-cors) on purpose: every consumer of these is an <img>
      // (equation SVGs, map figures), never a WebGL texture. A CORS-mode
      // preload races the panel's own no-cors <img> for the cache entry
      // and, when it loses, is refused by CORS on the live site (seen
      // in a live probe). Match the consumer's mode — that is the
      // lesson.
      const img = new Image()
      img.src = u
    }
  }
}

onMounted(() => {
  preloadTheoryAssets()
  // ?beat=N deep-links straight to beat N (used by tools/screenshot.mjs
  // scenarios). Clamped to valid range; default is 0; `last` = the path's
  // back from Chapter 2 (config/sitePath.ts).
  beat.value = parseBeatParam(route.query.beat, BEATS)
  // Deep links land at the beat's end state (prevBeat = -1 disables
  // the 3→4 morph choreography).
  prevBeat = -1
  applyBeat(beat.value)
})

onBeforeUnmount(() => {
  clearMorphTimers()
  cancelLerp(flashLerp)
  cancelLerp(revealLerp)
  cancelLerp(drainLerp)
  cancelLerp(paintLerp)
  emit('chapter-focus',   null)
  emit('lake-overlay',    null)
  emit('lake-polygons',   null)
  emit('lake-cutaway',    null)
  emit('velocity-mode',   null)
  emit('chapter-reveal',  null)
  emit('slab-fx',         null)
  emit('theory-stage',    null)
  emit('chapter-exag',    null)
  // Restore the default snow-basemap view.
  emit('globe-clicks', 1)
})
</script>
