<template>
  <div class="globe-wrap">
    <canvas ref="canvasRef" class="globe-canvas"></canvas>
    <!-- Camera-state debug HUD. Toggled by appending ?debug=cam to the
         URL. Reads currentLat/Lon/Distance + camera.fov each frame so
         the agent can read off framing values directly from a
         screenshot instead of inferring from code. -->
    <div v-if="debugCam" class="cam-hud">
      <div><span>lat</span> {{ camHud.latDeg.toFixed(2) }}°</div>
      <div><span>lon</span> {{ camHud.lonDeg.toFixed(2) }}°</div>
      <div><span>dist</span> {{ camHud.distWorld.toFixed(3) }} <em>×R</em></div>
      <div><span>dist</span> {{ camHud.distApi.toFixed(3) }} <em>API</em></div>
      <div><span>fov</span> {{ camHud.fov.toFixed(1) }}°</div>
      <div><span>focal</span> ({{ camHud.focalLatDeg.toFixed(2) }}°, {{ camHud.focalLonDeg.toFixed(2) }}°)</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { LineSegments2 } from 'three/addons/lines/LineSegments2.js'
import { LineSegmentsGeometry } from 'three/addons/lines/LineSegmentsGeometry.js'
import { LineMaterial } from 'three/addons/lines/LineMaterial.js'
import { mediaUrl } from '../config/media'
import { IMAGERY_DIFF_LIM } from '../config/ch2State'
import velocityPaletteJson from '../config/velocityPalette.json'
import { seasonDrape } from './seasonDrape'
import { buildBcGroup, bcMaterialList, setBcFade, setBcHover, type BcAnchor } from './simBcOverlay'
import type { BcKey } from '../config/simBcGeo'
import {
  SIM_HOVER_GOLD,
  SIM_LAKE_STYLE,
  type SimCatalogLake,
  type SimLakesFile,
} from '../config/simLakes'

// Slidev-agnostic version of the original components/Globe.vue. Accepts
// `clicks` as a prop driven by the parent (Landing splash, Explore HUD,
// guided-tour state machine, etc.) instead of importing useNav() from
// @slidev/client.
const props = defineProps<{
  clicks: number
  // When true, hovering the mouse over Greenland on the spinning globe
  // softly glows it gold (with a black outline) to indicate it's a
  // clickable button. Clicking it emits 'greenland-click' for the
  // parent to handle (typically: begin the tour).
  greenlandHoverable?: boolean
  // When true, the 3D silvery length-scale arrows fade in beside the
  // elevated Greenland surface (length / width / height), lit by the
  // same world-fixed sun direction that drives the hillshade.
  showArrows?: boolean
  // DEM rollback amount (0–1). 0 = full elevated dome (no cut), 1 =
  // east half (lon > uCutLon ≈ −37°W) fully collapsed and cross-section
  // slab fully visible. Driven by SectionMotivation step 0.
  rollback?: number
  // Camera tilt override in degrees (world-space lat). Sections can dip
  // the camera lower for a more oblique view (e.g. Motivation uses ~35°
  // to expose the cross-section with depth). When undefined, falls back
  // to the default ELEV_CAM_LAT (50°). Smoothly lerps on change.
  cameraTilt?: number
  // The menu's stage fit (the director asked for the object on the menu
  // page to be a bit bigger, filling more of the space it has on the left
  // side). The room is the viewport minus what the menu panel covers
  // on the right — min(rightVw × width, rightMaxPx); the object is
  // magnified to fill that room (see STAGE_*) and centred in it. A
  // magnification of the PROJECTION, not a camera move: currentDistance
  // stays at ELEV_CAM_DIST, so every section's flight still leaves from
  // the same camera. Eases in and out over STAGE_FIT_MS; null/undefined =
  // the plain shifted view.
  stageFit?: { rightVw: number; rightMaxPx: number } | null
  // Leaving the menu for a section whose opening flies the camera: hold
  // the stage fit where it is until that flight starts, so the flight
  // carries its unwind (one motion, not shrink-then-fly). Explore drops
  // it when the focus arrives (or after a safety timeout).
  stageFitHold?: boolean
  // Chapter-driven camera focus. When set, retargets the look-at focal
  // to the surface point at (lat, lon) — geographic, in degrees — and
  // smoothly orbits the camera to a viewing position over `durationMs`.
  // `cameraLat`/`cameraLon` (degrees) are the camera's polar coords;
  // sensible defaults (oblique view, south of the focal at the focal's
  // longitude) get used if omitted. `distance` is camera distance from
  // sphere centre (NOT from focal). Setting to null lerps the camera
  // back to the state it had at the chapter's onset, so returning to
  // menu / motivation lands at the original framing.
  chapterFocus?: {
    lat: number
    lon: number
    cameraLat?: number
    cameraLon?: number
    /** Camera distance from sphere CENTRE in world units (matches what
     *  __getCamera() reports). The sphere itself has radius 0.5; the
     *  elevated ice dome extends to ~0.525, so distance < ~0.55 puts
     *  the camera inside the visible ice. */
    distance?: number
    /** Optical zoom for chapter views. Default Three.js camera FOV is
     *  30°; smaller values "zoom in" without moving the camera (so we
     *  don't end up inside the elevated ice dome at small distances).
     *  Null/undefined = leave at the menu default. */
    fovDeg?: number
    durationMs?: number
    /** Aim at the DISPLACED ice surface instead of the bare sphere —
     *  required for telephoto framings (small fov), where the ~70
     *  exaggerated-km between sphere and surface throws the subject
     *  out of frame. `focalElevM` gives the surface elevation
     *  explicitly (robust on deep links, where the DEM readback may
     *  not be decoded yet); `focalOnSurface` looks it up instead. */
    focalElevM?: number
    focalOnSurface?: boolean
    /** Exaggeration to compute the focal lift with, when the flight's
     *  END exaggeration differs from the live chapterExag prop (Ch.2
     *  drops to true-ish scale mid-flight; the camera must fly to the
     *  FINAL surface height from the start or it lands mis-aimed). */
    focalExag?: number
    /** Beat 3→4 seam fit: solve the framing so the
     *  chapter slab's ±halfKm window around the fracture projects
     *  exactly onto `rect` (screen px). The solver adjusts focal
     *  lat/lon, camera distance AND the vertical exaggeration (so the
     *  slab's aspect matches the theory panel's field rect); the
     *  explicit lat/lon/distance above are its initial guess and its
     *  fallback if textures aren't ready. */
    fit?: {
      fracTLon: number
      halfKm: number
      rect: { x: number; y: number; w: number; h: number }
    }
    /** Roll the camera so screen-up is local NORTH at the focal — for
     *  nadir framings (the Introduction's fly-along lands straight down
     *  on the fieldwork map; the flat SVG map that takes over is north-
     *  up, so the 3-D frame must be too). */
    upNorth?: boolean
    /** Explicit world-space camera up (Ch.2 BC head-on views: walls
     *  upright, the bed seen from above with no roll). Wins over
     *  upNorth and the default radial-out. */
    up?: [number, number, number]
  } | null
  /** Duration of the next chapterExag lerp (ms). Default CHAPTER_EXAG_MS
   *  (1.5 s); the Introduction's flatten asks for ~3 s. Read when the
   *  chapterExag prop changes, so set it first. */
  chapterExagMs?: number
  /** Introduction fly-along: TRUE fades the velocity paint +
   *  streamlines OUT and the satellite basemap IN while `clicks` stays
   *  at 2 (the phase machine's mirror of 'streaming'); FALSE re-streams.
   *  Backward `clicks` snap; this is the smooth strip the director asked for. */
  stripVelocity?: boolean
  /** Hillshade strength override (0–1), lerped over HILLSHADE_MS. The
   *  hillshade is computed from the DEM gradient, NOT the exaggeration,
   *  so flattening the dome to 0 alone leaves the relief texture on the
   *  basemap; the fly-along fades it out so the object becomes a flat
   *  map. Null = back to 1. */
  hillshade?: number | null
  /** Screen anchors (the Introduction's step-0 measuring lines + sea-
   *  level label): geographic points, each either `lift` world units
   *  above the bare sphere or, with `surface`, on the displaced ice
   *  surface (+ lift). Projected every frame to
   *  `window.__globeAnchorScreens` = { id: {x, y, visible} } (CSS px),
   *  the `__featuredLakeScreens` pattern. Null = nothing published. */
  screenAnchors?: { id: string; lat: number; lon: number; lift?: number; surface?: boolean }[] | null
  /** The fieldwork Sentinel-2 patch: a sphere-hugging rectangle in the
   *  fieldwork local-tangent frame (see config/fieldwork.ts), textured
   *  with the 10 m crop, crossfaded over the coarse basemap by
   *  `opacity`. No DEM displacement — it is only shown once the dome is
   *  flat (fade it out BEFORE re-inflating). While mounted, the Globe
   *  publishes `window.__fieldworkScreen` (screen px of three frame
   *  reference points) so the flat map can match the landing exactly. */
  fieldworkPatch?: {
    url: string
    latC: number
    lonC: number
    halfXm: number
    halfYm: number
    rEarthM: number
    opacity: number
  } | null
  /** Ch.3 beat 1 (the dynamic Fig. 1): a lon/lat-gridded patch over the
   *  central-west study strip whose texture is a CANVAS the section owns
   *  and redraws per season day (all 1,000 labeled lake polygons, fill
   *  scaled by p_water). `version` bumps mark the canvas dirty; the
   *  Globe re-uploads on the next frame. Drawn at the sphere surface —
   *  meant for the flattened (exag 0) nadir map view, like the fieldwork
   *  patch. Null disposes.
   *  `surface` (the "Revisiting lake drainage papers" page):
   *  the patch lies ON the displaced ice surface instead — the marks are
   *  painted on the object, whatever the exaggeration and the camera —
   *  and its texture is mip-mapped (it is seen oblique and zoomed). */
  lakeStrip?: {
    canvas: HTMLCanvasElement
    lonW: number
    lonE: number
    latS: number
    latN: number
    opacity: number
    version: number
    surface?: boolean
  } | null
  // Chapter-driven lake / region marker. When set, renders a flat
  // circular disc tangent to the sphere at (lat, lon) in geographic
  // degrees. `radiusKm` is the marker's physical radius in km
  // (exaggerated for visibility — a 3 km lake only spans ~1 px on the
  // globe so we render at 100s of km for narrative purposes). Setting
  // to null hides the disc.
  lakeOverlay?: {
    lat: number
    lon: number
    radiusKm?: number
    color?: string
    opacity?: number
  } | null
  // Unified south-to-NL knife reveal. ONE prop drives both the
  // basemap latitude cut AND the cross-section slab that fills the
  // gap. Single source of truth for "where is the knife edge right
  // now?" — the slab's effective latitude is biased internally by
  // Globe.vue's CHAPTER_CUT_BAND_FRAG_SINLAT so callers work purely
  // in geographic degrees and don't have to know about the shader's
  // discard band. Setting to null retracts the cut, hides + disposes
  // the slab, and clears uChapterCutSinLat on the basemap shaders.
  //
  // Parameters:
  //   latDeg       — knife latitude in degrees (e.g. 68.6 for NL).
  //   slabOpacity  — 0..1. Default 1. Pass 0 to apply the cut
  //                  without showing the slab (rare).
  //   idealize     — 0..1 morph of the slab's bed/surface curves
  //                  toward flat parallel lines (Elmer/Ice domain).
  //                  Default 0 (real texture).
  //   cutBasemap   — false to show the slab WITHOUT discarding the
  //                  basemap (callout mode, no peel). Default true.
  chapterReveal?: {
    latDeg: number
    slabOpacity?: number
    idealize?: number
    cutBasemap?: boolean
  } | null
  // Bulk lake polygons overlay (Ch.1 Beat 1+2). `dataUrl` points at a
  // JSON of polygon rings (featured mode: featured_lakes.json from
  // cinematic/scene_ch01/build_featured_lakes.py). `opacity` (0-1) drives a fade-in flash. When
  // `highlightId` is set, that one lake is drawn in `highlightColor`
  // and the rest dimmed with `baseColor`/`baseAlpha`. Null = hide +
  // dispose.
  lakePolygons?: {
    dataUrl: string
    opacity?: number
    baseColor?: string
    baseAlpha?: number
    highlightId?: string | null
    // Beacon-style highlight (Ch.1 Beat 1 — the hi-res basemap shows
    // peer lakes natively, so the highlight is now a "click me"
    // affordance for NL rather than just a coloured flag): cyan fill
    // + gold outline + pulsing additive glow halo, all at ~3× the
    // real lake size (was 28× before the basemap upgrade).
    highlightFillColor?: string
    highlightOutlineColor?: string
    highlightScale?: number
    highlightGlow?: boolean
    // FEATURED mode (Ch.1 Beat 0): dataUrl points at
    // featured_lakes.json — the five ESSD fig-4 drainage-class lakes,
    // each with its own `color`. Every lake renders as a class-colored
    // clickable polygon; hovering scales it 1.5× (the director's spec — no
    // more "North Lake" label). All highlight* fields are ignored.
    featured?: boolean
    // Featured mode only: no hover grow, no click — Ch.1 fades the five
    // lakes out on the way to the cross-section and they must not open
    // a popup mid-fade.
    inert?: boolean
    // Featured mode only: one lake held at its own
    // opacity while the others fade — North Lake's outline stays up
    // through the flight to the cross-section until the cutaway takes it.
    // Chapter 2's dive: `track` keeps the held lake ON the
    // live surface through exaggeration changes, and `shrink` (0…1) eases
    // its drawn size from the overview's enlargement to the lake's true
    // footprint — so at the landing it lies exactly on the lake.
    keep?: { id: string; opacity: number; track?: boolean; shrink?: number } | null
  } | null
  // Ch.1 beats 1–2 (the North Lake outline must stay visible through the
  // cutaway): North Lake drawn ON the surface at the slab
  // lens's cartoon scale, straddling the cross-section face so the knife
  // visibly cuts through it (see buildLakeCutaway). `water` (0..1) fades
  // it with the drain, as does the slab's green basin rim.
  // Null = hide.
  lakeCutaway?: {
    /** featured_lakes.json — the ring comes from here. */
    dataUrl: string
    id: string
    /** The chapter reveal's cut latitude (chapterReveal.latDeg at the
     *  end of the peel); the face sits at slabLatRadFromCutLatDeg(it). */
    cutLatDeg: number
    /** Fill colour (the lake's drainage-class colour). */
    color: string
    opacity: number
    water: number
  } | null
  // Velocity colormap + single-streamline highlight (Ch.1 Beat 4).
  // `active=true` ensures the velocity colormap is showing (mirrors
  // clicks≥2); `dataUrl` (optional) loads a single-streamline JSON
  // whose polyline is drawn in `highlightColor` on top of the standard
  // streamline pulses. `showDashes=false` suppresses the global animated
  // streamline-pulse overlay so only the highlight tube is visible —
  // Ch.1 uses this because the dashes read as visual noise on top of
  // the velocity colormap at chapter framing. `highlightOpacity`
  // (default 1) lerps the tube's opacity — Beat 4 sets this to 0 so
  // the tube fades out as the cross-section reveal takes over, instead
  // of doubling up the "here's the flow" cue with the slab. Null =
  // hide overlay.
  velocityMode?: {
    active: boolean
    dataUrl?: string
    highlightColor?: string
    showDashes?: boolean
    highlightOpacity?: number
  } | null
  // Generic chapter colormap drape: a texture (same PlateCarree frame
  // as greenland_velocity.png — lon −75..−10, lat 59..84) rendered as
  // its own Greenland patch above the basemap, opacity lerped toward
  // `opacity`. Ch.1 Beat 2 drapes the ACL map (ch01/acl_map.png).
  // Null fades the current drape out (mesh disposed on url change).
  chapterOverlay?: { url: string; opacity?: number } | null
  // Ch.2 "drain the lake" carve: a high-res
  // simulation-domain tile (25 m DEM from the Elmer/Ice mesh, satellite
  // color from the shared basemap, published elastic Δσ_t1 drape) is
  // mounted flush on the Greenland surface. The carve happens
  // TO the greenland object itself — the rotated model-domain square
  // (from `corners`) is immune while `carveT` sweeps the rest of the
  // relief away in the chosen `mode`; `tileT` crossfades the 25 m tile
  // over the coarse surface (done at wide framing, where the swap is
  // sub-pixel) while the coarse relief beneath it collapses; `stressT`
  // fades the stress drape onto the carved tile. Null disposes.
  // Sections drive carve/tile/stress with per-frame emits.
  // The payload type lives in config/simLakes.ts (shared with Explore,
  // SectionCh2 and the Additional-Work MGSIM page); the later-added
  // optional fields (surfA, bedPalMix, stressAltUrl…) are the MGSIM
  // page's and default to the published look when absent.
  simDomain?: import('../config/simLakes').SimDomainPayload | null
  // Cross-section slab effects (Ch.1 water-drain + Elmer stress paint).
  // Sections drive the animation with per-frame emits (chapter-reveal
  // pattern); Globe direct-writes the slab-material uniforms.
  //   fracTLon — fracture position as 0..1 fraction along the slab
  //   drainT   — 0..1: 0..0.6 water descends the fracture, 0.6..1 the
  //              bed layer spreads outward from the fracture foot
  //   paintT   — 0..1 fade of the Elmer tau_xx paint over the ice
  //   paintUrl — paint texture (x: along-flow, y: bed->surface)
  slabFx?: {
    fracTLon: number
    drainT: number
    paintT?: number
    paintUrl?: string
    /** 0..1 spin of the slab mesh (π·spinT) about the radial axis at
     *  the fracture — the beat 3→4 morph flips the cross-section
     *  around so its (mirrored) back face points at the camera and
     *  ice flow reads left→right, matching the simulation domain. */
    spinT?: number
    /** 0..1 removal of the idealized slab's cosmetic along-flow tilt —
     *  the morph levels the object into the panel's flat diagram
     *  proportions before the seam handoff. */
    levelT?: number
    /** 0..1 CROP of the slab to the ±40 km theory window around the
     *  fracture: the ends of the 46°-wide cross-section
     *  slide into the window edges so the object condenses to the
     *  simulation domain BEFORE it flips — no more whole-island spin. */
    cropT?: number
  } | null
  // Vertical-exaggeration override for chapter sections. When set
  // (e.g. Ch.1 = 10× ≈ 0.0028), Globe.vue lerps `currentExag` from
  // whatever it was (typically TARGET_EXAGGERATION ≈ 90× = 0.025) to
  // this value, smoothly deflating the ice dome so lake polygons and
  // streamlines can sit FLUSH on the surface instead of hovering
  // above the dome peak. Null = restore TARGET_EXAGGERATION.
  chapterExag?: number | null
  // Featured lake to pulse (Ch.1 Beat 0): set while the user hovers a
  // drainage-legend row so the corresponding lake swells 1× → 2.4× on
  // the globe (FEATURED_PULSE_MAX). Null = no pulse.
  featuredPulseId?: string | null
  // Ch.2 block: externally-driven catalog-lake glow — the
  // phase-space panel hovers feed back onto the block's outlines.
  // Catalog number (cw + 1523) or null.
  simLakeHighlight?: number | null
  // Boundary-condition mode over the landed block: the ghost 24.75 km
  // model domain + ONE boundary's overlay
  // (`focus`, a clicked card — components/simBcOverlay.ts), and per-
  // boundary screen anchors (window.__simBcScreens) for the cards.
  simBc?: {
    on: boolean
    model: 'viscous' | 'elastic'
    focus?: BcKey | null
    /** CW2019_NNNN — keys config/ch2BcData.ts BC_LAKES */
    lakeId?: string
    /** the card under the pointer — its boundary lights up */
    hover?: BcKey | null
  } | null
  // Skip all per-frame work (including renderer.render) while
  // an opaque overlay owns the screen (the twin-globes beat) — the two
  // renderers otherwise fight for the GPU and the reveal stutters.
  paused?: boolean
  /** Covered mode: an opaque full-screen layer covers the canvas
   *  (the Introduction's revealed fieldwork map, steps 4–7) — run the loop
   *  at a trickle (one frame per COVERED_FRAME_MS) instead of 60 fps.
   *  Frames rendered unseen at 60 fps queued up in the GPU process (the
   *  compositor never waited on them while the canvas was hidden): 3–4 s
   *  of them after the clip steps, and the first frame that showed the
   *  globe again waited for the whole queue — the Intro 7 → 8 freeze. A
   *  full pause instead left a 0.8–1.1 s first frame (the GPU cold after
   *  ~20 s without the globe's work); the trickle keeps it warm and is far
   *  too slow to build a queue. */
  covered?: boolean
}>()
const emit = defineEmits<{
  'greenland-click': []
  /** User clicked the highlighted lake beacon (Ch.1 Beat 0 — NL).
   *  Parent opens a video popup with the lake's time-series imagery. */
  'lake-beacon-click': [highlightId: string]
  /** Pointer entered / left one of the five featured drainage-class
   *  lakes (Ch.3 beat 0 lights that lake's callout panel; null = left).
   *  Fires only on change. */
  'lake-beacon-hover': [highlightId: string | null]
  /** Click landed on empty globe/space (no interactive hit). Parent
   *  uses it to dismiss transient UI like the lake-video dock. */
  'canvas-blank-click': []
  /** Ch.2 block: pointer is over a drainage-catalog lake on
   *  the sim-domain face (null = left every lake). Carries the lake's
   *  catalog record so the parent can show the stress popout + glow
   *  the phase-space symbols. */
  'sim-lake-hover': [lake: SimCatalogLake | null]
  /** Click on a catalog lake (parent pins/unpins the popout). */
  'sim-lake-pick': [lake: SimCatalogLake | null]
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)

let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let globe: THREE.Mesh
let basemap: THREE.Mesh
let velocityMap: THREE.Mesh
// Generic chapter colormap drape (e.g. Ch.1's ACL map): a Greenland
// patch mesh whose texture comes from the chapterOverlay prop's url,
// opacity smoothed toward its target each frame. One mesh at a time —
// a url change disposes and rebuilds.
let chapterOverlayMesh: THREE.Mesh | null = null
let chapterOverlayUrl: string | null = null
let chapterOverlayOpacityTarget = 0
let chapterOverlayOpacityCurrent = 0
let animationId = 0
let lastTime = 0
let resizeObserver: ResizeObserver | null = null

let demTexture: THREE.Texture | null = null
// High-precision DEM. RG-packed 16-bit elevation fraction (R=hi byte,
// G=lo byte) at 10400×4000, encoded by cinematic/scene_01_intro/build_dem_texture.py.
// Used ONLY for vertex displacement and the CPU readback (getDemElevAt) —
// places where 0.05 m elevation precision matters. The fragment shaders
// that draw hillshade gradients + the cross-section slab keep using the
// legacy 8-bit demTexture because they want GPU bilinear sampling, which
// RG-packing breaks (R and G blend independently, decoding garbage at
// byte-rollover boundaries — visible as a 14 m step at exactly the
// places we're trying to make smooth).
let demTextureHi: THREE.Texture | null = null
// Same encoding as demTextureHi (RG-packed 16-bit at 10400 × 4000)
// but smoothed at sigma=2 (≈400 m) instead of sigma=8 (≈1.5 km).
// Used ONLY for fragment-shader hillshade gradient — the displacement
// wants the smooth-for-shape version, but the hillshade wants enough
// km-scale surface detail to actually shade with (otherwise the
// 1.5-km-flat interior reads as featureless "fog" at chapter framing).
let demTextureHiDetail: THREE.Texture | null = null
let bedTexture: THREE.Texture | null = null
const elevatedShaders: { uniforms: any }[] = []

// Cross-section slab — appears at the moving cut line as it sweeps
// east→west, sampling the bed + surface DEM textures in its fragment
// shader so the visible cross-section content updates with the cut
// longitude. Mesh rotates around the polar axis each frame to track
// uCutLon.
let crossSectionMesh: THREE.Mesh | null = null
let crossSectionMat: THREE.ShaderMaterial | null = null

// Vertical scale arrow rendered just east of the cross-section, in the
// open ocean alongside the cut. Spans bed → surface at the central
// dome. Reads as "this is the height of the ice column" with a km
// label. Paired with an inset zoom window (separate canvas) showing
// the same height as 6 stacked OWTCs. Metallic bronze (MeshStandard)
// so it catches the same directional light as the arrows-on-globe.
let scaleArrow: THREE.Group | null = null
const scaleArrowMaterials: THREE.MeshStandardMaterial[] = []
// World-space positions of the arrow's bottom and top tips — used by
// the InsetZoom SVG expander to draw lines from these tips to the
// inset frame's left edge each frame.
let scaleArrowTipBottom: THREE.Vector3 | null = null
let scaleArrowTipTop: THREE.Vector3 | null = null

// USA scale-reference handled as a flat HTML/CSS overlay in
// Explore.vue (top-left corner) — see ScaleReferenceOverlay-style
// markup there. The 3D underlay version was removed because it
// confused the rotated camera view (a flat top-left corner card is
// cleaner reference and keeps the cross-section the focal element).

// Greenland basemap PNG extent — must match build_*_texture.py.
const BASEMAP_LON_W = (-75 * Math.PI) / 180
const BASEMAP_LON_E = (-10 * Math.PI) / 180
const BASEMAP_LAT_S = (59 * Math.PI) / 180
const BASEMAP_LAT_N = (84 * Math.PI) / 180

// Slab spans the same lat range as the basemap. The elevation range
// is asymmetric on purpose: ice can reach +3500 m (Summit), but most
// of central Greenland's bedrock is only slightly below sea level
// (-300 m at the dome, deeper at coasts). Capping the slab's bottom
// edge at -1000 m keeps the visible bedrock band a THIN floor below
// the ice column rather than visually dominating it.
const SLAB_ELEV_MIN_M = -1000
const SLAB_ELEV_MAX_M = 3500

// Bed texture encoding (must match build_bed_texture.py).
const BED_MIN_M = -3000
const BED_MAX_M = 2500
// Surface texture encoding (must match build_dem_texture.py — ELEV_MAX_M).
const SURF_MAX_M = 3500

// The basemap fragment shader discards fragments where
// sin(lat) < uChapterCutSinLat + CHAPTER_CUT_BAND_FRAG (= 0.0015) so the
// partially-collapsed wall triangles in the smoothstep band don't paint
// stretched basemap texture. That leaves the basemap's actually-visible
// southern edge at sin(lat) = uChapterCutSinLat + 0.0015, i.e. ~9 km
// north of the cut latitude itself. The chapter slab, on the other
// hand, sits exactly at the cut lat — so without a matching bias there
// is a ~9 km gap between the slab's top edge and the basemap edge,
// which reads as a "see through to the hollow ice interior" band when
// the dome and slab are supposed to be married.
//
// Bias the slab's effective latitude by the same band offset so the
// slab sits at the basemap edge instead of at the cut. Tracking the
// JS constant in lockstep with the shader's CHAPTER_CUT_BAND_FRAG.
const CHAPTER_CUT_BAND_FRAG_SINLAT = 0.0015
function slabLatRadFromCutLatDeg(latDeg: number): number {
  const sinLat = Math.sin((latDeg * Math.PI) / 180)
  return Math.asin(Math.min(1, sinLat + CHAPTER_CUT_BAND_FRAG_SINLAT))
}

// Initial cut longitude — placed just east of Greenland's east edge so
// nothing is collapsed at rest. SectionMotivation animates this from
// here to CUT_LON_FINAL.
const CUT_LON_INITIAL = (-5 * Math.PI) / 180
const CUT_LON_FINAL = (-37 * Math.PI) / 180   // central dome, max thickness

// Greenland-clickable hover state (intro mode only). A glow mesh
// (slightly larger sphere segment, golden additive) plus an outline
// mesh (back-side render at slightly larger radius) appear when the
// mouse hovers over Greenland on the spinning globe — communicating
// "this is a button". Click triggers the 'greenland-click' emit.
let greenlandGlow: THREE.Mesh | null = null
let greenlandOutline: THREE.Mesh | null = null
let isHoveringGreenland = false
let hoverTargetOpacity = 0
const raycaster = new THREE.Raycaster()
const mouseNDC = new THREE.Vector2()
// Off-screen canvas with the basemap PNG drawn into it, used to
// alpha-test raycaster hits. The basemap mesh covers Greenland's
// lat/lon bounding box geometrically — but Iceland and the Canadian
// Arctic also fall within that box. The texture's alpha channel masks
// them out visually; we need the same mask for hover hit-detection.
let basemapAlphaCanvas: HTMLCanvasElement | null = null
let basemapAlphaCtx: CanvasRenderingContext2D | null = null

// DEM PNG drawn into an off-screen canvas so we can read out local
// elevation in JS via getDemElevAt(lon, lat). The shaders read the
// same PNG as a GPU texture; this is the CPU-side mirror used by any
// overlay (lake polygons, streamline tubes, future cutout boxes) that
// needs to sit ON the elevated DEM rather than at a constant radius
// above the dome peak.
let demReadbackCanvas: HTMLCanvasElement | null = null
let demReadbackCtx: CanvasRenderingContext2D | null = null

// Texture-load readiness gate. Every TextureLoader.load in this file
// goes through loadTexTracked() so out-of-band tooling (screenshot.mjs,
// shot-grid.mjs) can wait for `window.__texturesPending === 0` instead
// of guessing a settle time — the hi-res basemap + RG16 DEMs total
// ~110 MB and their decode can outlast any fixed settleMs on first load.
// Errors also decrement: a missing texture must not wedge the gate.
let texturesPending = 0
let texturesStarted = 0
;(window as any).__texturesPending = 0
// Started-count lets the tools' readiness gate distinguish "all done"
// from "none requested yet" — the pending counter alone reads 0 in the
// window between this module importing and the first loader firing.
;(window as any).__texturesStarted = 0
const texturesInflight = new Set<string>()
;(window as any).__texturesInflight = texturesInflight
function loadTexTracked(
  url: string,
  onLoad?: (t: THREE.Texture) => void,
): THREE.Texture {
  texturesPending += 1
  texturesStarted += 1
  texturesInflight.add(url)
  ;(window as any).__texturesPending = texturesPending
  ;(window as any).__texturesStarted = texturesStarted
  const done = (): void => {
    texturesPending -= 1
    texturesInflight.delete(url)
    ;(window as any).__texturesPending = texturesPending
  }
  return new THREE.TextureLoader().load(
    url,
    (t) => {
      try {
        onLoad?.(t)
      } finally {
        done()
      }
    },
    undefined,
    done,
  )
}

// The giant textures, decoded OFF the main thread (a performance pass).
// Through TextureLoader the decode of a 16000 × 8000 JPEG or a 10400 ×
// 4000 PNG runs INSIDE texSubImage2D on the first render frame — a CDP
// profile read, with a WARM HTTP cache: the Earth
// 1.3–7.9 s, each DEM 0.4–4 s, the hi-res basemap 1.4–8.9 s, all serial on
// the main thread — the landing's 12–24 s black globe, and the same bill
// again on any deep link that first shows them. createImageBitmap decodes
// on a worker thread; the upload is then tens of ms (TwinGlobes measured
// ~35 ms per DEM). The same CORS request as three's loader (same cache
// entry); any failure falls back to loadTexTracked's path.
// Opaque images (the DEMs, the bed, the Earth JPEG) go this way in every
// engine — the GPU texture is byte-identical (as TwinGlobes verified).
// WebKit's bitmaps differ in TRANSLUCENT pixels, so the alpha-masked
// basemaps and the speed drape take it only in Chromium (`alpha`).
// The bitmap is already flipped (imageOrientation), so the texture keeps
// flipY = false — WebGL ignores UNPACK_FLIP_Y for an ImageBitmap — and a
// readback canvas drawn from it must flip back (drawTexImageUpright).
const bitmapDecodeOk = typeof createImageBitmap === 'function'
const chromiumLike = typeof (window as unknown as { chrome?: unknown }).chrome === 'object'
function loadTexBitmap(
  url: string,
  onLoad?: (t: THREE.Texture) => void,
  opts: { alpha?: boolean } = {},
): THREE.Texture {
  if (!bitmapDecodeOk || (opts.alpha && !chromiumLike)) return loadTexTracked(url, onLoad)
  texturesPending += 1
  texturesStarted += 1
  texturesInflight.add(url)
  ;(window as any).__texturesPending = texturesPending
  ;(window as any).__texturesStarted = texturesStarted
  let settled = false
  const done = (): void => {
    if (settled) return
    settled = true
    texturesPending -= 1
    texturesInflight.delete(url)
    ;(window as any).__texturesPending = texturesPending
  }
  const t = new THREE.Texture()
  t.flipY = false
  const viaImg = (): void => {
    new THREE.ImageLoader().setCrossOrigin('anonymous').load(
      url,
      (img) => {
        t.image = img
        t.flipY = true
        t.needsUpdate = true
        try {
          onLoad?.(t)
        } finally {
          done()
        }
      },
      undefined,
      done,
    )
  }
  fetch(url, { mode: 'cors', credentials: 'same-origin' })
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      return r.blob()
    })
    .then((b) => createImageBitmap(b, { imageOrientation: 'flipY', premultiplyAlpha: 'none', colorSpaceConversion: 'none' }))
    .then((bmp) => {
      t.image = bmp
      // Uploaded once; the decoded pixels (up to 512 MB) go after that.
      t.onUpdate = () => {
        t.onUpdate = null
        bmp.close()
      }
      t.needsUpdate = true
      try {
        onLoad?.(t)
      } finally {
        done()
      }
      // Upload NOW, not on the first frame that shows the mesh: a deep link
      // into Chapter 2's block (basemap hidden) used to pay the hi-res
      // basemap's upload on the press into Chapter 3 (1.5–8.9 s there).
      try {
        renderer?.initTexture(t)
      } catch {
        /* lazy upload on first use */
      }
    })
    .catch((e) => {
      console.warn('[globe] bitmap decode failed, loading it as an image:', url, e)
      viaImg()
    })
  return t
}
/** A texture's image onto a 2D canvas in the image's own orientation
 *  (row 0 = north), whichever loader brought it. */
function drawTexImageUpright(ctx: CanvasRenderingContext2D, t: THREE.Texture): void {
  const img = t.image as HTMLImageElement | ImageBitmap
  const w = (img as HTMLImageElement).naturalWidth || img.width
  const h = (img as HTMLImageElement).naturalHeight || img.height
  ctx.canvas.width = w
  ctx.canvas.height = h
  if (!t.flipY && typeof ImageBitmap !== 'undefined' && img instanceof ImageBitmap) {
    ctx.save()
    ctx.translate(0, h)
    ctx.scale(1, -1)
    ctx.drawImage(img, 0, 0)
    ctx.restore()
  } else {
    ctx.drawImage(img, 0, 0)
  }
}

// Surface elevation lookup. Returns metres above sea level at (lon, lat)
// in degrees. Returns 0 outside the basemap coverage range so callers
// can safely use the value as a radial-displacement multiplier without
// branching.
//
// The CPU-side mirror is built from the RG-packed 16-bit DEM PNG
// (greenland_dem_rg16.png). Decode: hi = data[0], lo = data[1] →
// u16 = (hi << 8) | lo → fraction = u16 / 65535 → metres = frac × SURF_MAX_M.
// 0.05 m precision vs the legacy 8-bit's 14 m — important when
// overlays compute their surface-hugging radii from this value
// (lake polygons + streamline tube), where the per-step 14 m jumps
// were visible as a faint waviness on the dome surface.
function getDemElevAt(lonDeg: number, latDeg: number): number {
  if (!demReadbackCtx || !demReadbackCanvas) return 0
  const lonRad = (lonDeg * Math.PI) / 180
  const latRad = (latDeg * Math.PI) / 180
  const u = (lonRad - BASEMAP_LON_W) / (BASEMAP_LON_E - BASEMAP_LON_W)
  const v = (latRad - BASEMAP_LAT_S) / (BASEMAP_LAT_N - BASEMAP_LAT_S)
  if (u < 0 || u > 1 || v < 0 || v > 1) return 0
  const w = demReadbackCanvas.width
  const h = demReadbackCanvas.height
  const px = Math.max(0, Math.min(w - 1, Math.floor(u * w)))
  // Three.js flipY=true on textures by default; the DEM PNG is
  // matplotlib origin-top-left, so v=0 (south edge of basemap) maps to
  // the BOTTOM row of the canvas image.
  const py = Math.max(0, Math.min(h - 1, Math.floor((1 - v) * h)))
  const data = demReadbackCtx.getImageData(px, py, 1, 1).data
  const u16 = (data[0] << 8) | data[1]
  return (u16 / 65535) * SURF_MAX_M
}

/**
 * getDemElevAt's SMOOTH twin: bilinear between the four nearest pixel
 * centres (what the GPU's linear filter does to the displacement), so the
 * elevation varies continuously with position. For geometry that MOVES over
 * the surface: Chapter 2's held lake polygon shrinks through the dive, and
 * with the nearest-pixel lookup each of its vertices jumped a DEM step
 * (times the exaggeration) whenever it crossed a pixel edge — the polygon
 * read as a little choppy against an otherwise smooth scene.
 */
function getDemElevSmoothAt(lonDeg: number, latDeg: number): number {
  if (!demReadbackCtx || !demReadbackCanvas) return 0
  const lonRad = (lonDeg * Math.PI) / 180
  const latRad = (latDeg * Math.PI) / 180
  const u = (lonRad - BASEMAP_LON_W) / (BASEMAP_LON_E - BASEMAP_LON_W)
  const v = (latRad - BASEMAP_LAT_S) / (BASEMAP_LAT_N - BASEMAP_LAT_S)
  if (u < 0 || u > 1 || v < 0 || v > 1) return 0
  const w = demReadbackCanvas.width
  const h = demReadbackCanvas.height
  if (w < 2 || h < 2) return getDemElevAt(lonDeg, latDeg)
  // Pixel centres sit at (i + 0.5) / w; clamp the 2 × 2 window inside.
  const fx = Math.max(0, Math.min(w - 1, u * w - 0.5))
  const fy = Math.max(0, Math.min(h - 1, (1 - v) * h - 0.5))
  const x0 = Math.min(w - 2, Math.floor(fx))
  const y0 = Math.min(h - 2, Math.floor(fy))
  const tx = fx - x0
  const ty = fy - y0
  const d = demReadbackCtx.getImageData(x0, y0, 2, 2).data
  const e = (k: number): number => (d[k * 4] << 8) | d[k * 4 + 1]
  const top = e(0) + (e(1) - e(0)) * tx
  const bot = e(2) + (e(3) - e(2)) * tx
  return ((top + (bot - top) * ty) / 65535) * SURF_MAX_M
}
/** surfaceRadiusAt on the smooth lookup. */
function surfaceRadiusSmoothAt(lonDeg: number, latDeg: number, extraLiftWorld = 0): number {
  return GLOBE_RADIUS + (getDemElevSmoothAt(lonDeg, latDeg) / SURF_MAX_M) * currentExag + extraLiftWorld
}

// Bed elevation lookup — same pattern as getDemElevAt but for the 8-bit
// bed texture (pixel/255 → BED_MIN_M..BED_MAX_M). Used by the beat 3→4
// fit solve to know the idealized slab's bed level. Returns BED_MIN_M
// outside coverage (callers clamp anyway).
let bedReadbackCanvas: HTMLCanvasElement | null = null
let bedReadbackCtx: CanvasRenderingContext2D | null = null
function getBedElevAt(lonDeg: number, latDeg: number): number {
  if (!bedReadbackCtx || !bedReadbackCanvas) return BED_MIN_M
  const lonRad = (lonDeg * Math.PI) / 180
  const latRad = (latDeg * Math.PI) / 180
  const u = (lonRad - BASEMAP_LON_W) / (BASEMAP_LON_E - BASEMAP_LON_W)
  const v = (latRad - BASEMAP_LAT_S) / (BASEMAP_LAT_N - BASEMAP_LAT_S)
  if (u < 0 || u > 1 || v < 0 || v > 1) return BED_MIN_M
  const w = bedReadbackCanvas.width
  const h = bedReadbackCanvas.height
  const px = Math.max(0, Math.min(w - 1, Math.floor(u * w)))
  const py = Math.max(0, Math.min(h - 1, Math.floor((1 - v) * h)))
  const data = bedReadbackCtx.getImageData(px, py, 1, 1).data
  return (data[0] / 255) * (BED_MAX_M - BED_MIN_M) + BED_MIN_M
}

// Surface-hugging radial lift. Returns the GLOBE_RADIUS + displacement
// at (lon, lat) using the CURRENT exaggeration (so overlays float with
// the surface as exag is reduced for chapter view). The optional
// `extraLiftWorld` adds a constant world-unit offset on top — pass a
// few × 1e-4 to keep an overlay disc clear of the basemap fragment
// shader's hillshade z-fight band.
function surfaceRadiusAt(lonDeg: number, latDeg: number, extraLiftWorld = 0): number {
  const elevM = getDemElevAt(lonDeg, latDeg)
  return GLOBE_RADIUS + (elevM / SURF_MAX_M) * currentExag + extraLiftWorld
}

// CURRENT vertical exaggeration value applied to the displacement
// uniforms. Starts at 0 (no displacement during the spinning hub
// phase), ramps to TARGET_EXAGGERATION over the open-to-Greenland
// transition, and is overridden by chapter sections that want a
// flatter surface (e.g. Ch.1 reduces to ~10×, so lakes/streamlines
// can sit FLUSH on the surface instead of hovering above the dome).
// All other code that builds overlay geometry reads this single
// value (via surfaceRadiusAt or directly) so a section change ripples
// through every dependent mesh.
let currentExag = 0

// NJ → Princeton AOS easter egg state. Same pattern as Greenland but
// scoped to a tiny region. Hover glows the state orange + outlined;
// click opens https://aos.princeton.edu/.
let njMesh: THREE.Mesh | null = null  // raycaster target (geometry-only)
let njGlow: THREE.Mesh | null = null
let njOutline: THREE.Mesh | null = null
let njAlphaCanvas: HTMLCanvasElement | null = null
let njAlphaCtx: CanvasRenderingContext2D | null = null
let isHoveringNJ = false
let njHoverOpacity = 0
const NJ_BOUNDS = { latS: 38.8, latN: 41.5, lonW: -75.7, lonE: -73.7 }
const NJ_URL = 'https://aos.princeton.edu/'

// 3D silvery length-scale arrow group — three arrows for length /
// width / height of Greenland. Materials are MeshStandardMaterial so
// they catch the same DirectionalLight that defines the hillshade
// sun direction.
let arrowsGroup: THREE.Group | null = null
const arrowMaterials: THREE.MeshStandardMaterial[] = []
let arrowsCurrentOpacity = 0

// User-driven camera control. The scripted phase machine drives the
// camera by default; click+drag temporarily hands control to OrbitControls,
// and after USER_IDLE_MS of inactivity the camera lerps back to whatever
// the scripted state would put it at.
let controls: OrbitControls | null = null
type CameraMode = 'scripted' | 'user' | 'returning'
let cameraMode: CameraMode = 'scripted'
let userIdleTimerId: number | null = null
// Idle timeout (ms) after the user lets go of OrbitControls before
// the camera lerps back to the scripted view. Phase-aware:
//   * Spinning hub: 5 s — the user might be hunting easter eggs and
//     wants longer to inspect.
//   * Post-zoom (Greenland in view, Motivation/Chapter section): 2 s —
//     a brief pause is enough; the canonical framing should reassert
//     quickly so the camera stays roughly aligned with the section's
//     designed view.
const USER_IDLE_MS_SPINNING = 5000
const USER_IDLE_MS_POST_ZOOM = 2000
const RETURN_LERP_MS = 1500
let returnLerp: {
  start: number
  posFrom: THREE.Vector3
  targetFrom: THREE.Vector3
  upFrom: THREE.Vector3
} | null = null

let currentLat = (24.2 * Math.PI) / 180
let currentLon = 0
let currentDistance = 5.485

// Debug HUD — opt-in via ?debug=cam. Lets the agent (and the director) read
// camera framing values directly from a screenshot rather than
// inferring them from code. Updated each animate() tick.
const debugCam = ref(false)
const camHud = ref({
  latDeg:       0,
  lonDeg:       0,
  distWorld:    0,   // multiplier of GLOBE_RADIUS (internal units)
  distApi:      0,   // chapter-API world units (distWorld × GLOBE_RADIUS)
  fov:          0,
  focalLatDeg:  0,
  focalLonDeg:  0,
})

// Phase machine — drives the 3D scene only. UI state (which section
// is selected, menu visibility, etc.) lives in Explore.vue.
//   clicks=0 → 'spinning'                  (idle globe loop)
//   clicks=1 → 'opening' → 'opened'        (combined motion: zoom +
//                                          DEM rise + view-shift)
//   clicks=2 → 'streaming' → 'streamed'    (velocity colormap + dashes)
type Phase =
  | 'spinning'
  | 'opening'
  | 'opened'
  | 'streaming'
  | 'streamed'
  // Intro fly-along: velocity paint fading back OUT to the basemap while
  // clicks stays 2, then holding there (stripVelocity prop).
  | 'unstreaming'
  | 'stripped'
let phase: Phase = 'spinning'

let openStart = 0
let openStartLat = 0, openStartLon = 0, openStartDist = 0
let openStartUp: [number, number, number] = [0, 0, 1]

let streamStart = 0
let streamFrom = 0

// Very slow, contemplative spin — one rotation per 96 s. The intro is
// a hub the user can sit on (and where easter eggs eventually live);
// any visible spin is a "the world is alive" signal, not motion.
const SPIN_RATE = (2 * Math.PI) / 96

// Click 1 — combined motion. Camera flies to SE oblique, globe fades to
// black, satellite Greenland fades in, DEM rises with vertical
// exaggeration, all in one ~7s eased transition.
const OPENING_MS = 7000

// Click 2 — overlays fade in. Camera doesn't move (already at SE oblique).
// Click 2 — basemap → velocity cross-fade, streamlines fade in.
const STREAM_FADEIN_MS = 1800
// Intro fly-along: velocity paint fading back out (stripVelocity).
const UNSTREAM_MS = 2200
let unstreamStart = 0
let unstreamFrom = 1
// Hillshade override lerp (hillshade prop).
const HILLSHADE_MS = 2600
let hillshadeLerp: { from: number; to: number; tStart: number } | null = null

// Camera target for the SE oblique elevated view (settled state for clicks 1+).
// 50° is the menu / general-section default. Motivation overrides via the
// `cameraTilt` prop to dip lower (≈35°) so the cross-section reads with depth.
const ELEV_CAM_LAT = (50 * Math.PI) / 180
const ELEV_CAM_LON = (-20 * Math.PI) / 180
const ELEV_CAM_DIST = 1.85
const TARGET_EXAGGERATION = 0.025

// Greenland shifts off-center to the left at the end of click 1, leaving
// the right ~30% of the viewport free for the menu / section panel.
// Implemented via `camera.setViewOffset` so the projection itself shifts
// — the canvas stays full-bleed (no aspect-ratio jitter during the lerp).
//   shift=0    → Greenland centered
//   shift=0.30 → Greenland at ~35% from left
const TARGET_VIEW_SHIFT = 0.30
let currentViewShift = 0
// The stage fit (the `stageFit` prop): its progress 0…1 and the last room
// asked for (kept while it eases back out). A page that mounts with it on
// (a deep link to the menu) starts there, no ease.
const STAGE_FIT_MS = 900
let stageFitSpec: { rightVw: number; rightMaxPx: number } = props.stageFit ?? { rightVw: 0, rightMaxPx: 0 }
let stageFitT = props.stageFit ? 1 : 0
// While a menu⇄section flight carries the stage fit, its eased progress
// is driven by the flight (null = the timer's easeInOutCubic(stageFitT)).
let stageFitEOverride: number | null = null
// The object's silhouette at ELEV_CAM, unmagnified, relative to the look-at
// point and in units of the viewport HEIGHT (the picture scales with the
// height): measured on the menu page at 1440 × 900 — x 213…742, y 271…680
// around the look-at point's (504, 450).
const STAGE_BBOX = { l: -0.3233, r: 0.2644, t: -0.1989, b: 0.2556 }
/** Clear room left and right of the fitted object, of the viewport width. */
const STAGE_MARGIN_X = 0.055
/** The fitted object's height, of the viewport height, at most. */
const STAGE_MAX_H = 0.6

const GLOBE_RADIUS = 0.5
// Scratch vectors for the per-frame screenAnchors projection.
const _anchorV = new THREE.Vector3()
const _anchorN = new THREE.Vector3()
const GREENLAND_LAT = (72 * Math.PI) / 180
const GREENLAND_LON = (-40 * Math.PI) / 180

const GREENLAND_RADIAL_OUT: [number, number, number] = [
  Math.cos(GREENLAND_LAT) * Math.cos(GREENLAND_LON),
  Math.cos(GREENLAND_LAT) * Math.sin(GREENLAND_LON),
  Math.sin(GREENLAND_LAT),
]

// Sun direction in tangent frame at Greenland centroid (axes:
// x=local-east, y=local-north, z=radial-out). Derived once so the
// hillshade fragment shader has it precomputed; world-space light is
// fixed at azimuth=315° (NW) altitude=35° (mid-morning sun feel).
const LIGHT_AZIMUTH = (315 * Math.PI) / 180
const LIGHT_ALTITUDE = (35 * Math.PI) / 180
const LIGHT_TANGENT = new THREE.Vector3(
  Math.sin(LIGHT_AZIMUTH) * Math.cos(LIGHT_ALTITUDE),
  Math.cos(LIGHT_AZIMUTH) * Math.cos(LIGHT_ALTITUDE),
  Math.sin(LIGHT_ALTITUDE),
).normalize()

const GREENLAND_FOCAL = [
  GLOBE_RADIUS * Math.cos(GREENLAND_LAT) * Math.cos(GREENLAND_LON),
  GLOBE_RADIUS * Math.cos(GREENLAND_LAT) * Math.sin(GREENLAND_LON),
  GLOBE_RADIUS * Math.sin(GREENLAND_LAT),
]
let focal: [number, number, number] = [0, 0, 0]
let cameraUp: [number, number, number] = [0, 0, 1]

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3)
}

function easeInOutCubic(t: number): number {
  return t < 0.5
    ? 4 * t * t * t
    : 1 - Math.pow(-2 * t + 2, 3) / 2
}

function smoothstep(t: number, a: number, b: number): number {
  if (t <= a) return 0
  if (t >= b) return 1
  const u = (t - a) / (b - a)
  return u * u * (3 - 2 * u)
}

function attachDemDisplacement(material: THREE.MeshBasicMaterial, hillshadeScale = 1): void {
  // Three shader-side jobs:
  //   (1) vertex displacement — push vertices outward by elev * uExag
  //       so the basemap mesh becomes the elevated ice-sheet surface
  //   (2) fragment hillshade — shade based on the DEM gradient lit by
  //       a WORLD-FIXED sun direction
  //   (3) DEM cut — vertices east of uCutLon (binary) have their
  //       displacement collapsed AND their fragment alpha dropped, so
  //       the east half disappears entirely as the slider sweeps west.
  //       The cross-section slab (separate mesh) renders the bed + ice
  //       profile at the moving cut line.
  if (!demTexture || !demTextureHi || !demTextureHiDetail) return
  material.transparent = true
  material.onBeforeCompile = (shader) => {
    // Three DEM textures, three distinct sampling needs:
    //   demMap          — 8-bit grayscale, BILINEAR. Legacy slot, kept
    //                     loaded for compatibility but no longer
    //                     sampled by the basemap shader after the
    //                     16-bit pipeline shipped.
    //   demMapHi        — 16-bit RG-packed, sigma=8 (km-smoothed),
    //                     NEAREST. Vertex displacement with manual
    //                     4-tap bilinear + RG-decode. Smooth-for-
    //                     shape: kills sub-km BedMachine spikes at
    //                     90× vertical exaggeration.
    //   demMapHiDetail  — 16-bit RG-packed, sigma=2 (~400 m smoothed),
    //                     NEAREST. Fragment-shader hillshade gradient.
    //                     The displacement DEM is too smooth (1.5 km)
    //                     to give the lighting useful gradients on the
    //                     dome interior; this variant preserves the
    //                     km-scale surface character the eye reads as
    //                     "ice texture" instead of "fog."
    shader.uniforms.demMap = { value: demTexture }
    shader.uniforms.demMapHi = { value: demTextureHi }
    shader.uniforms.demMapHiDetail = { value: demTextureHiDetail }
    // Seed from LIVE state, not zeros: exag/hillshade are only pushed
    // to registered shaders during transitions (opening animation,
    // exag lerps). A material compiled after the last transition — e.g.
    // the chapter drape on a deep link, where exag is already at its
    // target — would otherwise keep 0 forever and render flat, buried
    // inside the displaced dome. At t=0 currentExag IS 0, so the
    // original behavior is preserved for the opening animation.
    shader.uniforms.uExaggeration = { value: currentExag }
    shader.uniforms.uLightTangent = { value: LIGHT_TANGENT.clone() }
    shader.uniforms.uHillshadeStrength = { value: currentExag > 0 ? 1 : 0 }
    // Cut longitude (radians). Vertices east of this longitude
    // (lon > uCutLon) are removed. Initial value puts the cut just
    // east of Greenland so nothing is removed at rest. Seeded from the
    // LIVE cut too (same reason as exag above): applyRollback only
    // reaches shaders registered while the 3 s rollback runs, and the
    // speed drape compiles whenever its texture lands — when that was
    // after the rollback it kept the uncut value and, invisible at
    // opacity 0 on the Introduction's step 0 but still writing depth,
    // hid the cut face behind the removed east half (the symptom:
    // the slab missing in ~1 of 3 loads, back with depthTest off or the
    // drape hidden).
    shader.uniforms.uCutLon = {
      value: (elevatedShaders[0]?.uniforms.uCutLon?.value as number | undefined) ?? CUT_LON_INITIAL,
    }
    // Ch.1+ latitude cut: discard fragments where sin(lat) < uChapterCutSinLat.
    // Using sin(lat) = z / |worldPos| means the threshold is
    // radius-independent — works for both the sphere surface and the
    // elevated DEM at any displacement. JS pre-computes sin(target_lat).
    // Initial -2.0 is "never cut" (sin can't be < -1).
    shader.uniforms.uChapterCutSinLat = { value: -2.0 }
    // Ch.2 "zoom in" carve (settled on the
    // KNIFE sweep): the greenland object ITSELF is carved. The rotated
    // model-domain square (frame uDomA/uDomB around uDomC, half-size
    // uDomHalf, all on the unit sphere) is immune; everywhere else the
    // relief flattens back onto the sphere and darkens into the black
    // backdrop as the north→south front (uCarveT) passes.
    // uTileCollapseT sinks the coarse relief INSIDE the square under
    // the 25 m sim tile while the tile crossfades over it at wide
    // framing, so the swap is invisible. uCarveOn 0 = no-op.
    shader.uniforms.uCarveOn = { value: 0 }
    shader.uniforms.uCarveT = { value: 0 }
    shader.uniforms.uTileCollapseT = { value: 0 }
    shader.uniforms.uDomC = { value: new THREE.Vector3(0, 0, 1) }
    shader.uniforms.uDomA = { value: new THREE.Vector3(1, 0, 0) }
    shader.uniforms.uDomB = { value: new THREE.Vector3(0, 1, 0) }
    shader.uniforms.uDomHalf = { value: 0 }
    shader.uniforms.uKnifeS0 = { value: 0.999 }
    shader.uniforms.uKnifeS1 = { value: 0.84 }

    // ---- Vertex: radial displacement + binary east-of-cut collapse ----
    // World position passes through to the fragment shader so the
    // discard can be per-fragment-longitude rather than per-vertex
    // interpolated. Per-vertex discard produces vertical streaks
    // (basemap texture stretched on the cut-zone wall triangles);
    // per-fragment discard kills those triangles cleanly.
    shader.vertexShader = shader.vertexShader.replace(
      '#include <common>',
      `#include <common>
       uniform sampler2D demMap;
       uniform sampler2D demMapHi;
       uniform float uExaggeration;
       uniform float uCutLon;
       uniform float uChapterCutSinLat;
       uniform int uCarveOn;
       uniform float uCarveT;
       uniform float uTileCollapseT;
       uniform vec3 uDomC;
       uniform vec3 uDomA;
       uniform vec3 uDomB;
       uniform float uDomHalf;
       uniform float uKnifeS0;
       uniform float uKnifeS1;
       varying vec3 vWorldPos;
       varying float vCarve;
       varying float vInSquare;

       // Decode an RG-packed 16-bit elevation fraction. Encoder:
       //   u16  = round(frac * 65535)
       //   R    = (u16 >> 8) / 255    G = (u16 & 0xFF) / 255
       // Decoder (exact round-trip):
       //   frac = (R * 65280 + G * 255) / 65535
       float decodeDemRG(vec4 rgba) {
         return (rgba.r * 65280.0 + rgba.g * 255.0) / 65535.0;
       }

       // 4-tap bilinear sample of the RG-packed DEM. demMapHi MUST be
       // NEAREST-filtered (otherwise hardware bilinear blends R and G
       // independently, decoding garbage at byte-rollover boundaries —
       // a 14 m step exactly where smoothness matters). We sample four
       // adjacent texels and bilinear-interp the DECODED elevations,
       // which is the right way to interpolate packed-byte data.
       float sampleDemHi(vec2 uv) {
         vec2 texSize = vec2(10400.0, 4000.0);   // demMapHi dims
         vec2 px = uv * texSize - 0.5;            // pixel-space coords
         vec2 pxFloor = floor(px);
         vec2 t = px - pxFloor;                   // fractional offset
         vec2 uv00 = (pxFloor + 0.5) / texSize;
         vec2 uv10 = uv00 + vec2(1.0 / texSize.x, 0.0);
         vec2 uv01 = uv00 + vec2(0.0, 1.0 / texSize.y);
         vec2 uv11 = uv00 + vec2(1.0 / texSize.x, 1.0 / texSize.y);
         float e00 = decodeDemRG(texture2D(demMapHi, uv00));
         float e10 = decodeDemRG(texture2D(demMapHi, uv10));
         float e01 = decodeDemRG(texture2D(demMapHi, uv01));
         float e11 = decodeDemRG(texture2D(demMapHi, uv11));
         float e0 = mix(e00, e10, t.x);
         float e1 = mix(e01, e11, t.x);
         return mix(e0, e1, t.y);
       }`
    )
    shader.vertexShader = shader.vertexShader.replace(
      '#include <begin_vertex>',
      `vec3 transformed = vec3( position );
       // Vertex displacement uses the high-precision 16-bit DEM via
       // shader-side 4-tap bilinear (because the texture is NEAREST-
       // filtered — see Three.js setup). 0.05 m elevation precision +
       // proper sub-texel interpolation means no more "3D printed"
       // contour-line terraces at 90× exag. Cost: 4 vertex-shader
       // texture samples + a few mixes per vertex; vertex shaders run
       // ~1.2M times/frame for the basemap meshes — cheap.
       float elev = sampleDemHi(uv);
       vec3 N = normalize(position);
       // Vertex world position; we'll use it for per-fragment longitude
       // AND for the latitude-cut northness factor below.
       vec3 worldPos = (modelMatrix * vec4(position, 1.0)).xyz;
       vWorldPos = worldPos;
       float lon = atan(worldPos.y, worldPos.x);
       // CRITICAL: use WORLD-space z, not LOCAL position.z. The basemap
       // mesh is rotated 90 deg around X in makeGreenlandPatch -- local
       // Z points along the equator, not the polar axis -- so the prior
       // position.z / length(position) returned about -0.28 even for
       // vertices at lat 68 N and zeroed displacement everywhere when
       // any chapter-cut was active. Ch.1 Beat 4 was the symptom: the
       // dome flattened the moment the slider engaged.
       float vSinLat = worldPos.z / length(worldPos);
       // Vertex-side smoothstep keeps the displacement motion smooth as
       // uCutLon sweeps. Width ≈ one longitude segment.
       const float CUT_BAND_VERT = 0.003;
       float westness = 1.0 - smoothstep(uCutLon - CUT_BAND_VERT, uCutLon + CUT_BAND_VERT, lon);
       // Same trick on the latitude axis for the Ch.1 knife-cut: vertices
       // south of uChapterCutSinLat get their displacement collapsed back
       // to the sphere, so the band of triangles straddling the cut
       // (which the fragment shader will discard) doesn't form vertical
       // walls with stretched basemap texture.
       const float CHAPTER_CUT_BAND_VERT = 0.0015;
       float northness = smoothstep(
         uChapterCutSinLat - CHAPTER_CUT_BAND_VERT,
         uChapterCutSinLat + CHAPTER_CUT_BAND_VERT,
         vSinLat
       );
       // Ch.2 carve: the greenland object itself is carved.
       // outFlat = how flattened this vertex is. The
       // model-domain square is NOT masked out of the flatten — its
       // coarse skin has already crossfaded (in place, same displaced
       // height) into the 25 m sim tile via vInSquare*uTileCollapseT
       // in the fragment shader, so by the time the sweep reaches it
       // there is nothing visible left to protect. The immunity the
       // viewer sees is the tile itself standing while everything
       // around it sinks away.
       float outFlat = 0.0;
       float inSquare = 0.0;
       if (uCarveOn > 0) {
         vec3 nUnit = normalize(worldPos);
         vec3 dvec = nUnit - uDomC;
         float du = dot(dvec, uDomA);
         float dv = dot(dvec, uDomB);
         // Soft edge kept INSIDE the footprint so the whole crossfade
         // band hides under the sim tile (a band reaching outside the
         // rim showed as a dark halo ring around the tile mid-carve).
         inSquare = 1.0 - smoothstep(uDomHalf * 0.88, uDomHalf * 0.985,
                                     max(abs(du), abs(dv)));
         // KNIFE (the director's pick for the carve): a straight front
         // sweeps north→south (screen top-down at the drain framing) —
         // the cross-section slider's cut, running down the map. The
         // sweep spans uKnifeS0→uKnifeS1 (set from the lake's latitude
         // so the front crosses the VISIBLE frame over most of the
         // sweep, not the whole island in a blink). Terrain north of
         // uKnifeS0 leaves via the ease-in factor rather than a hard
         // pop at t=0.
         float s = nUnit.z;                    // sin(lat)
         const float KNIFE_W = 0.007;
         float sFront = mix(uKnifeS0 + KNIFE_W, uKnifeS1 - KNIFE_W, uCarveT);
         outFlat = smoothstep(sFront - KNIFE_W, sFront + KNIFE_W, s)
                 * smoothstep(0.0, 0.12, uCarveT);
       }
       vCarve = outFlat;
       vInSquare = inSquare;
       // In-square: sink the coarse skin a few percent under the sim
       // tile as the tile fades in on top. The coarse stays OPAQUE —
       // the tile crossfades over an identical-looking backdrop — but
       // the sink guarantees the tile wins the depth test everywhere
       // in the footprint (without it, patches of coarse relief above
       // the 25 m surface occluded the tile and the fade blended to
       // black instead of to the tile).
       float sink = 0.08 * inSquare * uTileCollapseT;
       transformed += N * elev * uExaggeration * westness * northness
                    * (1.0 - max(outFlat, sink));`
    )

    // ---- Fragment: hillshade + per-fragment longitude discard ----
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <common>',
      `#include <common>
       uniform sampler2D demMap;
       uniform sampler2D demMapHi;
       uniform sampler2D demMapHiDetail;
       uniform vec3 uLightTangent;
       uniform float uHillshadeStrength;
       uniform float uCutLon;
       uniform float uChapterCutSinLat;
       varying vec3 vWorldPos;
       varying float vCarve;
       // Same RG-decode the vertex shader uses. The hillshade gradient
       // walks demMapHiDetail (less-smoothed than the displacement
       // DEM) so the dome interior has km-scale surface variation for
       // the lighting to grip — without that the smooth-for-shape
       // displacement leaves the foreground reading as featureless
       // "fog" at chapter framing.
       float decodeDemRG(vec4 rgba) {
         return (rgba.r * 65280.0 + rgba.g * 255.0) / 65535.0;
       }`
    )
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <map_fragment>',
      `#include <map_fragment>
       // Per-fragment longitude — clean longitude-aligned cut.
       float fragLon = atan(vWorldPos.y, vWorldPos.x);
       // CRITICAL: discard the ENTIRE smoothstep-band zone, not just
       // east-of-cut. The vertex shader applies a smoothstep over
       // [uCutLon - CUT_BAND_VERT, uCutLon + CUT_BAND_VERT] to keep
       // the slider sweep smooth, which produces partially-elevated
       // vertices in the band. Wall triangles between those vertices
       // span vertically and stretch the basemap texture into ugly
       // pinstripes. Discarding the whole band kills those wall
       // fragments — the cross-section slab takes over the visual.
       const float CUT_BAND_FRAG = 0.003;
       if (fragLon > uCutLon - CUT_BAND_FRAG) discard;
       // Ch.1+ latitude cut: sin(lat) = z / |worldPos|. Discard the
       // band [uChapterCutSinLat - BAND, uChapterCutSinLat + BAND] —
       // matches the vertex-side smoothstep so the partially-collapsed
       // wall triangles in that band are killed entirely. Without this,
       // the wall fragments stretch the basemap into vertical streaks
       // at the cut edge. Default uChapterCutSinLat=-2 = never cuts.
       float sinLat = vWorldPos.z / length(vWorldPos);
       const float CHAPTER_CUT_BAND_FRAG = 0.0015;
       if (sinLat < uChapterCutSinLat + CHAPTER_CUT_BAND_FRAG) discard;
       // Ch.2 carve: as a fragment flattens it first darkens into the
       // black backdrop, and only fully-flattened pixels release
       // their alpha — the terrain reads as sinking away into the
       // dark, never as a transparent hole cut in the object. (The
       // in-square handoff to the sim tile is handled vertex-side:
       // the coarse skin stays opaque and sinks under the tile while
       // the tile fades in over it.)
       diffuseColor.rgb *= 1.0 - 0.92 * smoothstep(0.10, 0.85, vCarve);
       diffuseColor.a *= 1.0 - smoothstep(0.85, 1.0, vCarve);
       // 1-pixel anti-alias at the discard edge.
       float lonDx = fwidth(fragLon);
       diffuseColor.a *= 1.0 - smoothstep(
         uCutLon - CUT_BAND_FRAG - lonDx,
         uCutLon - CUT_BAND_FRAG,
         fragLon
       );
       // Tangent-space hillshade. Sources from demMapHi (16-bit
       // RG-packed at 10400 × 4000, NEAREST-filtered). The previous
       // implementation averaged 3 samples at (1×, 2×, 3×) eps as a
       // low-pass against the 8-bit DEM's per-step quantization noise
       // — visible as soft hillshade haze on the snow basemap and a
       // "popcorn" stipple on the velocity colormap. With 16-bit
       // precision that noise is gone, and the wide stencil over-
       // smoothed the lighting on the foreground interior at chapter
       // framing (a "blurry" / washed-out look — the closest part of
       // the dome lost local hillshade contrast). Drop back to a
       // single-tap gradient so local slope detail reads sharp.
       // Tangent-space hillshade. Sources from demMapHiDetail — the
       // sigma=2 (~400 m smoothed) variant of the 16-bit DEM. The
       // displacement DEM is intentionally smoothed at sigma=8
       // (~1.5 km) to kill BedMachine's sub-km fjord-cut spikes at
       // 90× vertical exaggeration, but that same smoothing leaves
       // the dome interior nearly flat — the hillshade gradient over
       // a few-pixel stencil gives near-zero slope, so the lit-side
       // dot product collapses to the sun's altitude (~0.57 = bright
       // white). The detail variant keeps catchment-scale surface
       // texture intact, so the lighting actually reads as ice
       // instead of fog.
       float eps = 2.0 / 2048.0;
       float hC = decodeDemRG(texture2D(demMapHiDetail, vMapUv));
       float hE = decodeDemRG(texture2D(demMapHiDetail, vMapUv + vec2(eps, 0.0)));
       float hN = decodeDemRG(texture2D(demMapHiDetail, vMapUv + vec2(0.0, eps)));
       float gE = (hE - hC) / eps;
       float gN = (hN - hC) / eps;
       // Z bias 2.0: middle ground between the old 3.0 (which
       // flattened slopes into near-vertical normals = no relief)
       // and the over-dramatic 1.0 (which made the dome interior
       // read as too textured). 2.0 gives ice-cap-like soft shading.
       vec3 nT = normalize(vec3(-gE, -gN, 2.0));
       float light = clamp(dot(nT, uLightTangent), 0.0, 1.0);
       // Softened factor range: was [0.15, 1.0] with light coefficient
       // 1.05 (so dark side could clamp aggressively). Pull both ends
       // in: [0.55, 1.0] with coefficient 0.5 means even the shadow
       // side stays mid-grey rather than dark grey, smoothing out
       // the bright/dark dome split the user flagged.
       float factor = mix(1.0, 0.55 + light * 0.5, uHillshadeStrength * ${hillshadeScale.toFixed(3)});
       factor = clamp(factor, 0.55, 1.0);
       diffuseColor.rgb *= factor;`
    )
    elevatedShaders.push(shader)
  }
  material.needsUpdate = true
}

function makeArrow(length: number, color = 0xc8c8c8): THREE.Group {
  // Single-headed arrow oriented along local +Z. Cylinder shaft +
  // cone head. Silvery MeshStandardMaterial — catches scene
  // lighting (DirectionalLight at sun direction).
  const g = new THREE.Group()
  const shaftLen = length * 0.85
  const headLen = length * 0.15
  const radius = Math.max(0.0008, length * 0.012)

  const mat = new THREE.MeshStandardMaterial({
    color,
    metalness: 0.92,
    roughness: 0.22,
    transparent: true,
    opacity: 0,
  })
  arrowMaterials.push(mat)

  const shaft = new THREE.Mesh(
    new THREE.CylinderGeometry(radius, radius, shaftLen, 16),
    mat,
  )
  // CylinderGeometry's axis is +Y by default; rotate to +Z.
  shaft.rotation.x = Math.PI / 2
  shaft.position.z = shaftLen / 2
  g.add(shaft)

  const head = new THREE.Mesh(
    new THREE.ConeGeometry(radius * 2.4, headLen, 16),
    mat,
  )
  head.rotation.x = Math.PI / 2
  head.position.z = shaftLen + headLen / 2
  g.add(head)

  return g
}

function buildArrowsAndLights(): void {
  // Local axes at Greenland centroid (world frame).
  const east = new THREE.Vector3(
    -Math.sin(GREENLAND_LON), Math.cos(GREENLAND_LON), 0,
  )
  const north = new THREE.Vector3(
    -Math.sin(GREENLAND_LAT) * Math.cos(GREENLAND_LON),
    -Math.sin(GREENLAND_LAT) * Math.sin(GREENLAND_LON),
    Math.cos(GREENLAND_LAT),
  )
  const radial = new THREE.Vector3(
    GREENLAND_RADIAL_OUT[0],
    GREENLAND_RADIAL_OUT[1],
    GREENLAND_RADIAL_OUT[2],
  )

  // World-fixed sun direction, computed by un-projecting LIGHT_TANGENT
  // (which is the sun in centroid tangent frame) back to world. This is
  // the SAME light direction the hillshade fragment shader uses, so
  // the arrows glint to match.
  const sunDir = new THREE.Vector3()
    .addScaledVector(east, LIGHT_TANGENT.x)
    .addScaledVector(north, LIGHT_TANGENT.y)
    .addScaledVector(radial, LIGHT_TANGENT.z)
    .normalize()

  const dirLight = new THREE.DirectionalLight(0xffffff, 1.6)
  dirLight.position.copy(sunDir).multiplyScalar(8)
  scene.add(dirLight)

  scene.add(new THREE.AmbientLight(0xffffff, 0.32))

  // Arrows group, positioned in the tangent plane at Greenland
  // centroid, slightly above the elevated DEM peak so they float
  // visibly. World-units-per-km factor: GLOBE_RADIUS / Earth radius.
  const KM = GLOBE_RADIUS / 6371
  const ARROW_BASE_R = GLOBE_RADIUS * (1 + TARGET_EXAGGERATION + 0.012)

  arrowsGroup = new THREE.Group()
  const cx = ARROW_BASE_R * Math.cos(GREENLAND_LAT) * Math.cos(GREENLAND_LON)
  const cy = ARROW_BASE_R * Math.cos(GREENLAND_LAT) * Math.sin(GREENLAND_LON)
  const cz = ARROW_BASE_R * Math.sin(GREENLAND_LAT)
  arrowsGroup.position.set(cx, cy, cz)
  arrowsGroup.visible = false  // hidden until showArrows is true

  // Length arrow: 2,670 km, runs north along local-north axis. Offset
  // slightly east so it sits beside Greenland's east coast.
  const lengthArrow = makeArrow(2670 * KM, 0xd8dde0)
  orientArrow(lengthArrow, north)
  lengthArrow.position.copy(east).multiplyScalar(900 * KM)
  // Re-center so the arrow's midpoint sits beside Greenland's center.
  lengthArrow.position.addScaledVector(north, -2670 * KM * 0.5)
  arrowsGroup.add(lengthArrow)

  // Width arrow: 1,300 km, runs east along local-east axis. Offset
  // slightly north so it sits north of Greenland.
  const widthArrow = makeArrow(1300 * KM, 0xd8dde0)
  orientArrow(widthArrow, east)
  widthArrow.position.copy(north).multiplyScalar(1500 * KM)
  widthArrow.position.addScaledVector(east, -1300 * KM * 0.5)
  arrowsGroup.add(widthArrow)

  // Height arrow: scaled to TARGET_EXAGGERATION (matches the elevated
  // peak), running radially outward. Offset to the east-and-south so
  // it doesn't overlap the length arrow.
  const heightArrow = makeArrow(TARGET_EXAGGERATION, 0xd8dde0)
  orientArrow(heightArrow, radial)
  heightArrow.position.copy(east).multiplyScalar(900 * KM)
  heightArrow.position.addScaledVector(north, -1500 * KM)
  // Start the arrow at the surface, not from the centroid (which is
  // already above the surface by the offset above).
  heightArrow.position.addScaledVector(radial, -GLOBE_RADIUS * 0.012)
  arrowsGroup.add(heightArrow)

  scene.add(arrowsGroup)
}

function orientArrow(arrow: THREE.Group, target: THREE.Vector3): void {
  // Rotate so the arrow's local +Z axis points along `target`.
  const q = new THREE.Quaternion().setFromUnitVectors(
    new THREE.Vector3(0, 0, 1),
    target.clone().normalize(),
  )
  arrow.quaternion.copy(q)
}

function makeNJHoverMeshes(): {
  hit: THREE.Mesh
  glow: THREE.Mesh
  outline: THREE.Mesh
} {
  // Three meshes for the NJ easter egg, all sphere segments over NJ's
  // lat/lon bounding box.
  //   HIT      — invisible, used only as the raycaster target. (Glow's
  //              alpha-tinted color blending complicates hits, so we
  //              use a dedicated mesh.)
  //   GLOW     — Princeton-orange additive layer.
  //   OUTLINE  — edge-detect shader for a thin black state outline.
  const phiStart = Math.PI + (NJ_BOUNDS.lonW * Math.PI) / 180
  const phiLength = ((NJ_BOUNDS.lonE - NJ_BOUNDS.lonW) * Math.PI) / 180
  const thetaStart = Math.PI / 2 - (NJ_BOUNDS.latN * Math.PI) / 180
  const thetaLength = ((NJ_BOUNDS.latN - NJ_BOUNDS.latS) * Math.PI) / 180

  const segs = (g: number) =>
    new THREE.SphereGeometry(g, 96, 64, phiStart, phiLength, thetaStart, thetaLength)

  const tex = loadTexTracked(
    mediaUrl('shared/egg_nj.png'),
    (loaded) => {
      const img = loaded.image as HTMLImageElement
      const c = document.createElement('canvas')
      c.width = img.naturalWidth || img.width
      c.height = img.naturalHeight || img.height
      const ctx = c.getContext('2d')
      if (ctx) {
        ctx.drawImage(img, 0, 0)
        njAlphaCanvas = c
        njAlphaCtx = ctx
      }
    },
  )
  tex.colorSpace = THREE.SRGBColorSpace
  tex.anisotropy = renderer.capabilities.getMaxAnisotropy()

  // HIT — invisible but raycastable. Slightly outside surface so it
  // wins depth tests against the Earth mesh.
  const hitMat = new THREE.MeshBasicMaterial({
    transparent: true,
    opacity: 0,
    depthWrite: false,
    depthTest: false,
    map: tex,
  })
  const hit = new THREE.Mesh(segs(GLOBE_RADIUS * 1.0008), hitMat)
  hit.rotation.x = Math.PI / 2
  hit.renderOrder = 6  // above Greenland glow (5)

  // GLOW — Princeton orange (#ff8c1a), additive blend.
  const glowMat = new THREE.MeshBasicMaterial({
    map: tex,
    transparent: true,
    opacity: 0,
    color: new THREE.Color(0xff8c1a),
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  })
  const glow = new THREE.Mesh(segs(GLOBE_RADIUS * 1.002), glowMat)
  glow.rotation.x = Math.PI / 2
  glow.renderOrder = 7

  // OUTLINE — same edge-detect shader as Greenland but with a tighter
  // eps because NJ is a much smaller area in UV space.
  const outlineMat = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    uniforms: {
      map: { value: tex },
      uOpacity: { value: 0 },
    },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform sampler2D map;
      uniform float uOpacity;
      varying vec2 vUv;
      void main() {
        float eps = 0.006;
        float aC = texture2D(map, vUv).a;
        float aR = texture2D(map, vUv + vec2(eps, 0.0)).a;
        float aL = texture2D(map, vUv + vec2(-eps, 0.0)).a;
        float aU = texture2D(map, vUv + vec2(0.0, eps)).a;
        float aD = texture2D(map, vUv + vec2(0.0, -eps)).a;
        float maxN = max(max(aR, aL), max(aU, aD));
        float edge = step(aC, 0.4) * step(0.5, maxN);
        if (edge < 0.5) discard;
        gl_FragColor = vec4(0.0, 0.0, 0.0, uOpacity);
      }
    `,
  })
  const outline = new THREE.Mesh(segs(GLOBE_RADIUS * 1.005), outlineMat)
  outline.rotation.x = Math.PI / 2
  outline.renderOrder = 6

  return { hit, glow, outline }
}

function makeGreenlandHoverMeshes(): { glow: THREE.Mesh; outline: THREE.Mesh } {
  // Two meshes that visualize "Greenland is a clickable button" on the
  // spinning globe. Both are sphere segments at slightly larger radii
  // than the basemap, sharing its texture (so they're masked to
  // Greenland's coastline).
  //   GLOW   — golden additive layer, brightens Greenland without
  //            covering the imagery
  //   OUTLINE — custom edge-detect shader, reads the texture alpha at
  //            the texel + neighbours and renders only where the
  //            current texel is outside the coastline but a neighbour
  //            is inside (i.e. the rim itself). Thin black contour.
  const LAT_S = 59.0, LAT_N = 84.0
  const LON_W = -75.0, LON_E = -10.0
  const phiStart = Math.PI + (LON_W * Math.PI) / 180
  const phiLength = ((LON_E - LON_W) * Math.PI) / 180
  const thetaStart = Math.PI / 2 - (LAT_N * Math.PI) / 180
  const thetaLength = ((LAT_N - LAT_S) * Math.PI) / 180

  const tex = loadTexBitmap(mediaUrl('shared/greenland_basemap.png'), undefined, { alpha: true })
  tex.colorSpace = THREE.SRGBColorSpace
  tex.anisotropy = renderer.capabilities.getMaxAnisotropy()

  // GLOW — bright saturated gold, additive, opacity ramps with hover.
  const glowGeom = new THREE.SphereGeometry(
    GLOBE_RADIUS * 1.003, 128, 64,
    phiStart, phiLength, thetaStart, thetaLength,
  )
  const glowMat = new THREE.MeshBasicMaterial({
    map: tex,
    transparent: true,
    opacity: 0,
    color: new THREE.Color(0xffc844),
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  })
  const glow = new THREE.Mesh(glowGeom, glowMat)
  glow.rotation.x = Math.PI / 2
  glow.renderOrder = 5

  // OUTLINE — sphere segment at slightly larger radius with edge-detect
  // shader. Renders only the rim of Greenland's coastline as black.
  const outlineGeom = new THREE.SphereGeometry(
    GLOBE_RADIUS * 1.006, 192, 96,
    phiStart, phiLength, thetaStart, thetaLength,
  )
  const outlineMat = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    uniforms: {
      map: { value: tex },
      uOpacity: { value: 0 },
    },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform sampler2D map;
      uniform float uOpacity;
      varying vec2 vUv;
      void main() {
        // Sample alpha at current texel and four neighbours. We render
        // black where the current texel is OUTSIDE the silhouette but
        // any neighbour is INSIDE — i.e. the coastline rim, one texel
        // outside the visible Greenland.
        float eps = 0.003;
        float aC = texture2D(map, vUv).a;
        float aR = texture2D(map, vUv + vec2(eps, 0.0)).a;
        float aL = texture2D(map, vUv + vec2(-eps, 0.0)).a;
        float aU = texture2D(map, vUv + vec2(0.0, eps)).a;
        float aD = texture2D(map, vUv + vec2(0.0, -eps)).a;
        // Diagonals sharpen corners.
        float aNE = texture2D(map, vUv + vec2(eps, eps)).a;
        float aNW = texture2D(map, vUv + vec2(-eps, eps)).a;
        float aSE = texture2D(map, vUv + vec2(eps, -eps)).a;
        float aSW = texture2D(map, vUv + vec2(-eps, -eps)).a;
        float maxN = max(
          max(max(aR, aL), max(aU, aD)),
          max(max(aNE, aNW), max(aSE, aSW))
        );
        float edge = step(aC, 0.4) * step(0.5, maxN);
        if (edge < 0.5) discard;
        gl_FragColor = vec4(0.0, 0.0, 0.0, uOpacity);
      }
    `,
  })
  const outline = new THREE.Mesh(outlineGeom, outlineMat)
  outline.rotation.x = Math.PI / 2
  outline.renderOrder = 4

  return { glow, outline }
}

function makeGreenlandPatch(
  textureUrl: string,
  polyOffset: number,
  hideUntilLoaded = false,
): THREE.Mesh {
  const LAT_S = 59.0, LAT_N = 84.0
  const LON_W = -75.0, LON_E = -10.0

  const phiStart = Math.PI + (LON_W * Math.PI) / 180
  const phiLength = ((LON_E - LON_W) * Math.PI) / 180
  const thetaStart = Math.PI / 2 - (LAT_N * Math.PI) / 180
  const thetaLength = ((LAT_N - LAT_S) * Math.PI) / 180

  // Segment count is tuned so DEM-driven vertex displacement reads as
  // a smooth surface at chapter-framing close-up. History:
  //   * 384×96  — visibly faceted ("lego blocks"); vertex spacing
  //               ~7 km E–W × 29 km N–S coarser than DEM resolution.
  //   * 768×192 — better, but at full 90× exaggeration the elevated
  //               dome still read as "3D printed" because 14.5 km
  //               N–S vertex spacing × 14 m DEM quantization (8-bit
  //               grayscale over 0–3500 m) showed step terraces.
  //   * 1536×384 (current) — ~1.75 km E–W × 7.25 km N–S. Approaches the
  //               1.4 km/px DEM source resolution, so the displaced
  //               surface stays smooth even at 90×. Paired with the
  //               3×3 multi-tap displacement smoothing in the vertex
  //               shader (see attachDemDisplacement), which low-passes
  //               the 26 m quantization step the 8-bit DEM enforces.
  //               ~590k verts per basemap mesh × 2 (basemap +
  //               velocityMap) = ~1.2M total — still cheap on any GPU
  //               built in the last decade. Future option if needed:
  //               re-render the DEM at higher DPI + RG-packed 16-bit
  //               encoding for true sub-metre elevation precision.
  const geom = new THREE.SphereGeometry(
    GLOBE_RADIUS,
    1536, 384,
    phiStart, phiLength,
    thetaStart, thetaLength,
  )

  let mesh: THREE.Mesh | null = null
  const tex = loadTexBitmap(textureUrl, (loaded) => {
    if (hideUntilLoaded && mesh) {
      // Never while Ch.2's block is in inspect mode (basemap hidden):
      // the drape's opacity-0 material still writes depth, and a late
      // texture (deep link: the ~webp lands after the carve settled)
      // used to un-hide it and depth-kill most of the block's surface.
      mesh.visible = !basemap || basemap.visible
      velocityDrapeAt = performance.now()
    }
    // For the satellite basemap, build an off-screen canvas so we can
    // alpha-test raycaster hits later (Iceland and the Canadian Arctic
    // fall inside Greenland's lat/lon bounding box, so geometry-only
    // hits would falsely register as Greenland hover).
    if (textureUrl.includes('greenland_basemap')) {
      const c = document.createElement('canvas')
      const ctx = c.getContext('2d')
      if (ctx) {
        drawTexImageUpright(ctx, loaded)
        basemapAlphaCanvas = c
        basemapAlphaCtx = ctx
      }
    }
  }, { alpha: true })
  tex.colorSpace = THREE.SRGBColorSpace
  tex.anisotropy = renderer.capabilities.getMaxAnisotropy()

  const mat = new THREE.MeshBasicMaterial({
    map: tex,
    transparent: true,
    opacity: 0,
    polygonOffset: true,
    polygonOffsetFactor: polyOffset,
    polygonOffsetUnits: polyOffset,
    // DoubleSide so the cross-section wall is visible when the rollback
    // collapses the west-half. Without this, looking at the elevated
    // east-half from the west would show only back-faces (culled) and
    // the cross-section profile would be invisible.
    side: THREE.DoubleSide,
  })

  mesh = new THREE.Mesh(geom, mat)
  mesh.rotation.x = Math.PI / 2
  if (hideUntilLoaded && !tex.image) mesh.visible = false
  return mesh
}

function makeCrossSectionMesh(): THREE.Mesh {
  // Cross-section slab at the moving cut line. Geometry is canonical at
  // lon = CUT_LON_FINAL; the mesh is rotated around the polar axis each
  // frame so it tracks uCutLon. The fragment shader samples bed + surface
  // textures at (lat_from_uv, current_cut_lon) to compute bedrock vs ice
  // vs sky for each pixel — the cross-section content updates as the cut
  // moves, so the slider visually reveals different profiles in turn.
  const N_COLS = 96
  const WORLD_PER_M = TARGET_EXAGGERATION / 3500

  const positions: number[] = []
  const uvs: number[] = []
  const indices: number[] = []

  const cosLon = Math.cos(CUT_LON_FINAL)
  const sinLon = Math.sin(CUT_LON_FINAL)

  for (let i = 0; i <= N_COLS; i++) {
    const tLat = i / N_COLS
    const lat = BASEMAP_LAT_S + tLat * (BASEMAP_LAT_N - BASEMAP_LAT_S)
    const cosLat = Math.cos(lat)
    const sinLat = Math.sin(lat)
    const nx = cosLat * cosLon
    const ny = cosLat * sinLon
    const nz = sinLat
    for (const elevM of [SLAB_ELEV_MAX_M, SLAB_ELEV_MIN_M]) {
      const r = GLOBE_RADIUS + elevM * WORLD_PER_M
      positions.push(r * nx, r * ny, r * nz)
    }
    // u = lat fraction (0 = LAT_S, 1 = LAT_N).
    // v = 0 at top (ELEV_MAX), 1 at bottom (ELEV_MIN).
    uvs.push(tLat, 0)
    uvs.push(tLat, 1)
  }

  for (let i = 0; i < N_COLS; i++) {
    const v0 = i * 2
    const v1 = i * 2 + 1
    const v2 = (i + 1) * 2
    const v3 = (i + 1) * 2 + 1
    indices.push(v0, v1, v2, v2, v1, v3)
  }

  const geom = new THREE.BufferGeometry()
  geom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  geom.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2))
  geom.setIndex(indices)

  const mat = new THREE.ShaderMaterial({
    uniforms: {
      uBedTex:    { value: bedTexture },
      uSurfTex:   { value: demTexture },
      uCutLon:    { value: CUT_LON_INITIAL },
      uOpacity:   { value: 1 },
      uBedMin:    { value: BED_MIN_M },
      uBedMax:    { value: BED_MAX_M },
      uSurfMax:   { value: SURF_MAX_M },
      uElevMin:   { value: SLAB_ELEV_MIN_M },
      uElevMax:   { value: SLAB_ELEV_MAX_M },
      uLatS:      { value: BASEMAP_LAT_S },
      uLatN:      { value: BASEMAP_LAT_N },
      uLonW:      { value: BASEMAP_LON_W },
      uLonE:      { value: BASEMAP_LON_E },
    },
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      varying vec2 vUv;
      uniform sampler2D uBedTex;
      uniform sampler2D uSurfTex;
      uniform float uCutLon;
      uniform float uOpacity;
      uniform float uBedMin;
      uniform float uBedMax;
      uniform float uSurfMax;
      uniform float uElevMin;
      uniform float uElevMax;
      uniform float uLatS;
      uniform float uLatN;
      uniform float uLonW;
      uniform float uLonE;

      void main() {
        // vUv.x = lat fraction; vUv.y = elev fraction (0 top, 1 bottom).
        float lat = mix(uLatS, uLatN, vUv.x);
        float ourElev = mix(uElevMax, uElevMin, vUv.y);

        // Sample bed and surface textures at (lon=uCutLon, lat).
        // Texture u = lon fraction in basemap range; v = lat fraction.
        // Default Three.js flipY=true means v=0 is the bottom of the
        // PNG which corresponds to LAT_S (matplotlib origin top-left,
        // inverted by flipY). Confirmed against existing greenland_dem.
        float u_tex = (uCutLon - uLonW) / (uLonE - uLonW);
        float v_tex = (lat - uLatS) / (uLatN - uLatS);

        if (u_tex < 0.0 || u_tex > 1.0 || v_tex < 0.0 || v_tex > 1.0) {
          discard;
        }

        float bedNorm = texture2D(uBedTex, vec2(u_tex, v_tex)).r;
        float surfNorm = texture2D(uSurfTex, vec2(u_tex, v_tex)).r;
        float bedElev = bedNorm * (uBedMax - uBedMin) + uBedMin;
        float surfElev = surfNorm * uSurfMax;

        // Clamp very deep beds (e.g. -1500 m at outlet glaciers) so
        // they stay within the slab's visible range — otherwise those
        // columns render as ice all the way down (since ourElev is
        // never < bedElev). Floor at uElevMin + small offset.
        bedElev = max(bedElev, uElevMin + 30.0);

        // Outside Greenland mask: surface PNG is 0 (sea level). Treat
        // those columns as "no slab at all" — discard so we don't get
        // a gold bedrock band extending past Greenland's coast.
        bool outsideMask = (surfNorm < 0.005);
        if (outsideMask) discard;

        // Gold edge band — thicker for visibility from defense distance.
        float GOLD_BAND_M = 140.0;
        vec3 GOLD = vec3(0.95, 0.74, 0.30);

        // Sea-level reference: a thin warm-cream stripe at z=0 that
        // overlays the slab regardless of bed/ice/sky. Reads as
        // "this horizontal line is sea level" — answers the audience's
        // implicit "where's sea level?" question once they see the
        // cross-section. Drawn LAST so it sits on top.
        const float SEA_BAND_M = 22.0;
        bool atSeaLevel = abs(ourElev) < SEA_BAND_M;
        vec3 SEA_COLOUR = vec3(0.96, 0.92, 0.65);

        if (ourElev < bedElev - GOLD_BAND_M) {
          // Bedrock interior: terrain colour ramp.
          float t = clamp((bedElev - uBedMin) / (uBedMax - uBedMin), 0.0, 1.0);
          vec3 darkBed  = vec3(0.18, 0.11, 0.07);
          vec3 midBed   = vec3(0.55, 0.38, 0.24);
          vec3 lightBed = vec3(0.82, 0.74, 0.55);
          vec3 col = mix(darkBed, midBed, smoothstep(0.0, 0.5, t));
          col = mix(col, lightBed, smoothstep(0.5, 1.0, t));
          if (atSeaLevel) col = SEA_COLOUR;
          gl_FragColor = vec4(col, uOpacity);
        } else if (ourElev < bedElev) {
          // Gold band at the top of the bedrock (ice/bed interface).
          vec3 col = atSeaLevel ? SEA_COLOUR : GOLD;
          gl_FragColor = vec4(col, uOpacity);
        } else if (!outsideMask && ourElev <= surfElev - GOLD_BAND_M) {
          // Ice column interior — blue.
          vec3 ice = vec3(0.72, 0.84, 0.96);
          if (atSeaLevel) ice = SEA_COLOUR;
          gl_FragColor = vec4(ice, uOpacity);
        } else if (!outsideMask && ourElev <= surfElev) {
          // Gold band at the top of the surface (ice/sky interface).
          vec3 col = atSeaLevel ? SEA_COLOUR : GOLD;
          gl_FragColor = vec4(col, uOpacity);
        } else if (atSeaLevel) {
          // Above the surface but ON the sea-level line — render the
          // line so the audience can trace it past the ice.
          gl_FragColor = vec4(SEA_COLOUR, uOpacity * 0.70);
        } else {
          discard;
        }
      }
    `,
    transparent: true,
    side: THREE.DoubleSide,
    depthWrite: false,
  })
  crossSectionMat = mat

  const mesh = new THREE.Mesh(geom, mat)
  mesh.renderOrder = 5
  return mesh
}

function makeScaleArrow(): THREE.Group {
  // Vertical double-headed arrow positioned just east of the cross-
  // section in the open ocean. Spans bed → surface at the central
  // dome. Reads as "this is how thick Greenland's ice is". Cylinder
  // shaft + two SHARP cone heads, MeshStandardMaterial in bronze so
  // it picks up the world-fixed directional light and reads as a
  // metallic instrument rather than a flat gold flag.
  const SUMMIT_LAT = (72.5 * Math.PI) / 180
  const ARROW_LON = (-33 * Math.PI) / 180
  const WORLD_PER_M_VERT = TARGET_EXAGGERATION / 3500
  // BedMachine v6's thickest column (3,413 m at 71.5°N 36.5°W): the bed
  // 281 m below sea level, the surface 3,132 m above (previously it was
  // −300 → 3,200, a 3,500 m arrow under a "≈ 3,200 m" label).
  const ARROW_BED_M = -281
  const ARROW_SRF_M = 3132
  const ARROW_HEIGHT_W = (ARROW_SRF_M - ARROW_BED_M) * WORLD_PER_M_VERT
  // Slightly thicker shaft + much sharper (longer, narrower) heads so
  // the arrow reads as a precision dimension callout rather than a
  // stubby pin.
  const SHAFT_RADIUS = 0.0011
  const HEAD_LENGTH = ARROW_HEIGHT_W * 0.18    // longer cone heads
  const HEAD_RADIUS = SHAFT_RADIUS * 2.8       // narrower head base relative to length
  const SHAFT_LENGTH = ARROW_HEIGHT_W - 2 * HEAD_LENGTH
  // Theme gold (matches --gold-bright in style.css and the cross-
  // section's surface/bed gold rim) — replaces the earlier bronze so
  // the whole comparator reads as one consistent gold accent palette.
  const ARROW_GOLD = 0xf4cf6a

  const cosLat = Math.cos(SUMMIT_LAT)
  const sinLat = Math.sin(SUMMIT_LAT)
  const cosLon = Math.cos(ARROW_LON)
  const sinLon = Math.sin(ARROW_LON)
  const radial = new THREE.Vector3(cosLat * cosLon, cosLat * sinLon, sinLat)

  const group = new THREE.Group()
  const arrowBase = radial.clone().multiplyScalar(
    GLOBE_RADIUS + ARROW_BED_M * WORLD_PER_M_VERT,
  )
  group.position.copy(arrowBase)
  const upY = new THREE.Vector3(0, 1, 0)
  group.quaternion.setFromUnitVectors(upY, radial)

  const matBuilder = (): THREE.MeshStandardMaterial => {
    const m = new THREE.MeshStandardMaterial({
      color: ARROW_GOLD,
      metalness: 0.85,
      roughness: 0.25,
      emissive: 0x352510,   // warm self-glow for theme-gold tone
      transparent: true,
      opacity: 0,
    })
    scaleArrowMaterials.push(m)
    return m
  }

  // Bottom arrowhead (cone pointing -Y / down toward bed).
  const bottomHead = new THREE.Mesh(
    new THREE.ConeGeometry(HEAD_RADIUS, HEAD_LENGTH, 32),
    matBuilder(),
  )
  bottomHead.position.y = HEAD_LENGTH * 0.5
  bottomHead.rotation.z = Math.PI
  group.add(bottomHead)

  // Shaft.
  const shaft = new THREE.Mesh(
    new THREE.CylinderGeometry(SHAFT_RADIUS, SHAFT_RADIUS, SHAFT_LENGTH, 24),
    matBuilder(),
  )
  shaft.position.y = HEAD_LENGTH + SHAFT_LENGTH * 0.5
  group.add(shaft)

  // Top arrowhead (cone pointing +Y / up toward surface).
  const topHead = new THREE.Mesh(
    new THREE.ConeGeometry(HEAD_RADIUS, HEAD_LENGTH, 32),
    matBuilder(),
  )
  topHead.position.y = ARROW_HEIGHT_W - HEAD_LENGTH * 0.5
  group.add(topHead)

  // Cache world-space positions of the bottom and top tips so the
  // InsetZoom expander SVG can project them to screen each frame.
  // These are static (the group never moves), so we compute once.
  scaleArrowTipBottom = radial.clone().multiplyScalar(
    GLOBE_RADIUS + ARROW_BED_M * WORLD_PER_M_VERT,
  )
  scaleArrowTipTop = radial.clone().multiplyScalar(
    GLOBE_RADIUS + ARROW_SRF_M * WORLD_PER_M_VERT,
  )

  group.visible = false
  return group
}

// ─────────── Introduction · "Greenland flows": comet trails ───────────
//
// The NASA SVS 3848 grammar (Rignot et al., "Antarctic ice flow"): the
// log speed colour map on the ice (velocityMap, FLOW_DRAPE_KEY) and on top
// of it thousands of thin dark streaks, each a comet — a darker head and
// a fading, tapering tail — sliding down evenly spaced ITS_LIVE
// streamlines. Built offline by cinematic/scene_01_intro/
// build_flow_trails.py into a compact binary (FLW1, layout in the script
// header): per vertex lon/lat (uint16) and tau, the ANIMATION time (s) a
// head takes to reach it from the line's upstream end at a display speed
// that is a compressed power of the true speed (interior creeps, outlets
// move briskly). The fragment shader lights a fragment when a head passed
// it less than `tail` seconds ago: d = (t − tau + phase) mod period —
// exact per fragment (tau is interpolated along each ribbon segment), so
// heads glide continuously instead of hopping vertex to vertex, several
// comets ride each long line, every line has its own phase (no global
// pulse) and the pattern is periodic in t (no loop seam).
//
// The ribbons are camera-facing, a fixed width in screen pixels, and sit
// ON the displaced surface: the vertex shader samples the same RG16 DEM
// texture + exaggeration + rollback cut the basemap shader uses, so the
// DEM race cannot strand them at sea level and no CPU rebuild is ever
// needed. Normal alpha blending (additive vanishes on snow).
//
// Knobs (window.__flow.set(key, value) in the console; FLOW_KNOBS below):
// slow / fast (m/yr: the speed gate), fastTail (tail × on fast ice), rate (animation
// speed ×), tail (s of tau), period (s of tau between comets on a line),
// width (half-width at the head, CSS px), alpha, color. The comet head
// moves at rate × f(v) km/s of ground; its tail is tail × f(v) km long. Density and the speed law are baked (script constants).
const FLOW_TRAILS_KEY = 'shared/greenland_flow_trails_v1.bin'
const FLOW_DRAPE_KEY = 'shared/greenland_speed_nasa_v1.webp'
const FLOW_KNOBS = {
  rate: 1.8,
  tail: 5,
  period: 12,
  width: 0.55,
  // Speed gate (m/yr): comets are invisible below `slow`, full above
  // `fast` (smoothstep in log speed) — NASA's slow interior is colour
  // only; streaks live where the ice moves. Set slow 0, fast 1 for
  // comets everywhere.
  slow: 6,
  fast: 60,
  // Tail length multiplier at and above `fast` (1 = same everywhere):
  // outlets read as streaked tongues.
  fastTail: 1.8,
  alpha: 0.9,
  color: [0.03, 0.06, 0.16] as [number, number, number],
}
let flowMesh: THREE.Mesh | null = null
let flowMat: THREE.ShaderMaterial | null = null
// 0 → 1 over FLOW_READY_MS once the trails exist, so a late binary
// fades in instead of popping onto an already-streamed scene.
let flowReadyAt = 0
const FLOW_READY_MS = 900
// Phase-machine opacity (streaming / unstreaming / click snaps write it).
let flowOpacity = 0
// When the speed drape's texture arrived (0 = not yet).
let velocityDrapeAt = 0
let flowClock = 0
let flowWarmFrames = 0

async function loadFlowTrails(): Promise<void> {
  let buf: ArrayBuffer
  try {
    const res = await fetch(mediaUrl(FLOW_TRAILS_KEY))
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    buf = await res.arrayBuffer()
  } catch (err) {
    console.warn('[flow] trails fetch failed', err)
    return
  }
  const dv = new DataView(buf)
  const magic = String.fromCharCode(dv.getUint8(0), dv.getUint8(1), dv.getUint8(2), dv.getUint8(3))
  if (magic !== 'FLW1') {
    console.warn('[flow] not a FLW1 payload', magic, buf.byteLength)
    return
  }
  const nLines = dv.getUint32(4, true)
  const nPts = dv.getUint32(8, true)
  const lonW = dv.getFloat32(12, true)
  const lonE = dv.getFloat32(16, true)
  const latS = dv.getFloat32(20, true)
  const latN = dv.getFloat32(24, true)
  let off = 40
  const starts = new Uint32Array(buf, off, nLines + 1)
  off += 4 * (nLines + 1)
  const tau = new Float32Array(buf, off, nPts)
  off += 4 * nPts
  const lonQ = new Uint16Array(buf, off, nPts)
  off += 2 * nPts
  const latQ = new Uint16Array(buf, off, nPts)
  off += 2 * nPts
  const speedQ = new Uint8Array(buf, off, nPts) // log10(v m/yr) × 64

  const D2R = Math.PI / 180
  const lonOf = (i: number) => (lonW + (lonQ[i] / 65535) * (lonE - lonW)) * D2R
  const latOf = (i: number) => (latS + (latQ[i] / 65535) * (latN - latS)) * D2R

  // Two vertices (sides) per point. Attributes: aLL (this point), aNb
  // (prev.xy, next.xy — the screen tangent), aSide, aTau, aLine (phase,
  // tau at the line's downstream end).
  const nV = 2 * nPts
  const aLL = new Float32Array(nV * 2)
  const aNb = new Float32Array(nV * 4)
  const aSide = new Float32Array(nV)
  const aTau = new Float32Array(nV)
  const aLine = new Float32Array(nV * 2)
  const aLogV = new Float32Array(nV)
  let nSeg = 0
  for (let l = 0; l < nLines; l++) nSeg += Math.max(0, starts[l + 1] - starts[l] - 1)
  const index = new Uint32Array(nSeg * 6)
  let ii = 0
  // Deterministic per-line phase (golden-ratio sequence): no two
  // neighbouring lines pulse together, no Math.random() drift per load.
  const GOLD = 0.6180339887
  for (let l = 0; l < nLines; l++) {
    const a = starts[l]
    const b = starts[l + 1]
    if (b - a < 2) continue
    const phase = ((l * GOLD) % 1) * 1000 // scaled by period in the shader
    const tauEnd = tau[b - 1]
    for (let i = a; i < b; i++) {
      const ip = Math.max(a, i - 1)
      const inx = Math.min(b - 1, i + 1)
      const lo = lonOf(i)
      const la = latOf(i)
      for (let s = 0; s < 2; s++) {
        const v = 2 * i + s
        aLL[2 * v] = lo
        aLL[2 * v + 1] = la
        aNb[4 * v] = lonOf(ip)
        aNb[4 * v + 1] = latOf(ip)
        aNb[4 * v + 2] = lonOf(inx)
        aNb[4 * v + 3] = latOf(inx)
        aSide[v] = s === 0 ? -1 : 1
        aTau[v] = tau[i]
        aLine[2 * v] = phase
        aLine[2 * v + 1] = tauEnd
        aLogV[v] = speedQ[i] / 64
      }
      if (i < b - 1) {
        const v0 = 2 * i
        index[ii++] = v0
        index[ii++] = v0 + 1
        index[ii++] = v0 + 2
        index[ii++] = v0 + 2
        index[ii++] = v0 + 1
        index[ii++] = v0 + 3
      }
    }
  }
  const geom = new THREE.BufferGeometry()
  // `position` is required by three for bounds; the shader ignores it.
  geom.setAttribute('position', new THREE.BufferAttribute(new Float32Array(nV * 3), 3))
  geom.setAttribute('aLL', new THREE.BufferAttribute(aLL, 2))
  geom.setAttribute('aNb', new THREE.BufferAttribute(aNb, 4))
  geom.setAttribute('aSide', new THREE.BufferAttribute(aSide, 1))
  geom.setAttribute('aTau', new THREE.BufferAttribute(aTau, 1))
  geom.setAttribute('aLine', new THREE.BufferAttribute(aLine, 2))
  geom.setAttribute('aLogV', new THREE.BufferAttribute(aLogV, 1))
  geom.setIndex(new THREE.BufferAttribute(index, 1))

  const cutLon = (elevatedShaders[0]?.uniforms.uCutLon?.value as number | undefined) ?? CUT_LON_INITIAL
  flowMat = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    // The basemap interpolates the DEM between vertices 7 km apart N–S;
    // these ribbons sample it per vertex, so a depth test would let the
    // coarser surface slice through them. They only ever face the camera
    // on Greenland's own side, drawn last.
    depthTest: false,
    // The ribbon winding is clockwise on screen (the side offset is +90°
    // from the travel direction) — without DoubleSide every quad culls.
    side: THREE.DoubleSide,
    uniforms: {
      demMapHi: { value: demTextureHi },
      uExaggeration: { value: currentExag },
      uCutLon: { value: cutLon },
      uFrame: { value: new THREE.Vector4(BASEMAP_LON_W, BASEMAP_LON_E, BASEMAP_LAT_S, BASEMAP_LAT_N) },
      uResolution: { value: new THREE.Vector2(1, 1) },
      uHalfWidthPx: { value: 1 },
      uLift: { value: GLOBE_RADIUS * 0.0003 },
      uTime: { value: 0 },
      uPeriod: { value: FLOW_KNOBS.period },
      uTail: { value: FLOW_KNOBS.tail },
      uSpeedGate: { value: new THREE.Vector2(Math.log10(FLOW_KNOBS.slow), Math.log10(FLOW_KNOBS.fast)) },
      uFastTail: { value: FLOW_KNOBS.fastTail },
      uOpacity: { value: 0 },
      uColor: { value: new THREE.Color().setRGB(...FLOW_KNOBS.color) },
    },
    vertexShader: /* glsl */ `
      attribute vec2 aLL;
      attribute vec4 aNb;
      attribute float aSide;
      attribute float aTau;
      attribute vec2 aLine;
      attribute float aLogV;
      uniform sampler2D demMapHi;
      uniform float uExaggeration;
      uniform float uCutLon;
      uniform vec4 uFrame;
      uniform vec2 uResolution;
      uniform float uHalfWidthPx;
      uniform float uLift;
      varying float vTau;
      varying float vPhase;
      varying float vTauEnd;
      varying float vAcross;
      varying float vLon;
      varying float vLogV;

      float decodeDemRG(vec4 rgba) {
        return (rgba.r * 65280.0 + rgba.g * 255.0) / 65535.0;
      }
      // Same 4-tap decode-then-interpolate the basemap vertex shader uses
      // (the RG16 DEM is NEAREST-filtered).
      float sampleDemHi(vec2 uv) {
        vec2 texSize = vec2(10400.0, 4000.0);
        vec2 px = uv * texSize - 0.5;
        vec2 pf = floor(px);
        vec2 t = px - pf;
        vec2 uv00 = (pf + 0.5) / texSize;
        float e00 = decodeDemRG(texture2D(demMapHi, uv00));
        float e10 = decodeDemRG(texture2D(demMapHi, uv00 + vec2(1.0 / texSize.x, 0.0)));
        float e01 = decodeDemRG(texture2D(demMapHi, uv00 + vec2(0.0, 1.0 / texSize.y)));
        float e11 = decodeDemRG(texture2D(demMapHi, uv00 + 1.0 / texSize));
        return mix(mix(e00, e10, t.x), mix(e01, e11, t.x), t.y);
      }
      vec3 dirOf(vec2 ll) {
        return vec3(cos(ll.y) * cos(ll.x), cos(ll.y) * sin(ll.x), sin(ll.y));
      }
      void main() {
        vec2 uv = vec2((aLL.x - uFrame.x) / (uFrame.y - uFrame.x),
                       (aLL.y - uFrame.z) / (uFrame.w - uFrame.z));
        float elev = sampleDemHi(uv);
        // The step-0 rollback collapses everything east of uCutLon; ride it.
        float west = 1.0 - smoothstep(uCutLon - 0.003, uCutLon + 0.003, aLL.x);
        float r = 0.5 + elev * uExaggeration * west + uLift;
        mat4 pv = projectionMatrix * viewMatrix;
        vec4 c  = pv * vec4(dirOf(aLL) * r, 1.0);
        vec4 cp = pv * vec4(dirOf(aNb.xy) * r, 1.0);
        vec4 cn = pv * vec4(dirOf(aNb.zw) * r, 1.0);
        vec2 t = (cn.xy / cn.w - cp.xy / cp.w) * uResolution;
        float tl = length(t);
        vec2 dir = tl > 1e-6 ? t / tl : vec2(1.0, 0.0);
        vec2 nrm = vec2(-dir.y, dir.x);
        // +1 px of skirt for the fragment shader's anti-aliasing.
        float hw = uHalfWidthPx + 1.0;
        c.xy += nrm * aSide * hw * 2.0 / uResolution * c.w;
        gl_Position = c;
        vTau = aTau;
        vPhase = aLine.x;
        vTauEnd = aLine.y;
        vAcross = aSide * hw;
        vLon = aLL.x;
        vLogV = aLogV;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform float uTime;
      uniform float uPeriod;
      uniform float uTail;
      uniform float uOpacity;
      uniform float uHalfWidthPx;
      uniform float uCutLon;
      uniform vec3 uColor;
      uniform vec2 uSpeedGate;
      uniform float uFastTail;
      varying float vTau;
      varying float vPhase;
      varying float vTauEnd;
      varying float vAcross;
      varying float vLon;
      varying float vLogV;
      void main() {
        if (vLon > uCutLon - 0.003) discard;
        // Speed gate: streaks only where the ice moves (NASA's grammar).
        float gate = uSpeedGate.y > uSpeedGate.x
          ? smoothstep(uSpeedGate.x, uSpeedGate.y, vLogV) : 1.0;
        if (gate < 0.002) discard;
        // Seconds since a comet head passed this fragment.
        // (explicit floor: the built-in mod() came back NEGATIVE for
        // negative arguments on ANGLE/Metal, lighting only tau < t)
        float x = uTime - vTau + fract(vPhase / 1000.0) * uPeriod;
        float d = x - uPeriod * floor(x / uPeriod);
        float tail = uTail * mix(1.0, uFastTail, gate);
        if (d > tail) discard;
        float k = d / tail;
        // Soft head (≈0.12 s ramp), long fading tail.
        float a = smoothstep(0.0, 0.12, d) * pow(1.0 - k, 1.35);
        // Comets are born at the upstream end and die at the calving
        // front — a short fade in tau at each end (tau runs fastest at the
        // front, so a long end-fade would blank the outlets' last ~30 km).
        a *= smoothstep(0.0, 0.5, vTau) * smoothstep(0.0, 0.12, vTauEnd - vTau);
        // Width tapers head → tail; 1 px anti-aliased edge.
        float w = uHalfWidthPx * mix(1.0, 0.3, k);
        float cov = 1.0 - smoothstep(w - 0.5, w + 0.7, abs(vAcross));
        a *= cov * gate * uOpacity;
        if (a < 0.004) discard;
        gl_FragColor = vec4(uColor, a);
      }
    `,
  })
  flowMesh = new THREE.Mesh(geom, flowMat)
  flowMesh.frustumCulled = false
  flowMesh.renderOrder = 10
  scene.add(flowMesh)
  flowReadyAt = performance.now()
  flowWarmFrames = 2
  ;(window as any).__flow = {
    knobs: FLOW_KNOBS,
    lines: nLines,
    vertices: nV,
    set(k: keyof typeof FLOW_KNOBS, v: number | [number, number, number]) {
      ;(FLOW_KNOBS as any)[k] = v
    },
  }
}

// ─────────── Introduction · "the seasons": the month drape ───────────
//
// Steps 2–3 recolour the SAME speed drape month by month (config/
// seasons.ts, components/seasonDrape.ts). The shader keeps the drape's
// alpha (the ice mask), its relief and its geometry, and changes only the
// colour:
//   speed    drape + palette(t_static + Δ/log10(vmax/vmin)) − palette(t_static)
//   anomaly  RdBu_r(pct), faded to grey on slow ice / filled months
// with t_static the drape's own log-speed fraction (uSeasonT), Δ and pct
// from the two ping-ponged month textures (uSeasonA/B, mixed by uSeasonMix
// in encoded space — both encodings are linear). At Δ = 0 the colour IS
// the drape's, so the hand-over from "Greenland flows" has no seam.
// Uploads happen here, one per month step, timed into seasonDrape.stats.
const SEASON_PLACEHOLDER = (() => {
  const t = new THREE.DataTexture(new Uint8Array([128, 128, 0, 255]), 1, 1)
  t.needsUpdate = true
  return t
})()
function makeLutTexture(stops: [number, string][], n = 1024): THREE.DataTexture {
  // The bake's np.interp in sRGB byte space, rounded — same as the drape.
  const fr = stops.map((s) => s[0])
  const rgb = stops.map((s) => [1, 3, 5].map((i) => parseInt(s[1].slice(i, i + 2), 16)))
  const data = new Uint8Array(n * 4)
  for (let k = 0; k < n; k++) {
    const t = k / (n - 1)
    let j = 0
    while (j < fr.length - 2 && t > fr[j + 1]) j++
    const f = fr[j + 1] > fr[j] ? Math.min(1, Math.max(0, (t - fr[j]) / (fr[j + 1] - fr[j]))) : 0
    for (let c = 0; c < 3; c++) data[4 * k + c] = Math.round(rgb[j][c] + (rgb[j + 1][c] - rgb[j][c]) * f)
    data[4 * k + 3] = 255
  }
  const tex = new THREE.DataTexture(data, n, 1)
  tex.colorSpace = THREE.SRGBColorSpace
  tex.magFilter = THREE.LinearFilter
  tex.minFilter = THREE.LinearFilter
  tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping
  tex.needsUpdate = true
  return tex
}
function makeSeasonSlot(): THREE.Texture {
  const t = new THREE.Texture()
  t.colorSpace = THREE.NoColorSpace
  t.flipY = false // ImageBitmaps come pre-flipped (imageOrientation 'flipY')
  t.premultiplyAlpha = false
  t.generateMipmaps = true
  t.minFilter = THREE.LinearMipmapLinearFilter
  t.magFilter = THREE.LinearFilter
  t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping
  return t
}
const seasonTexA = makeSeasonSlot()
const seasonTexB = makeSeasonSlot()
const seasonTexT = makeSeasonSlot()
seasonTexT.format = THREE.RedFormat // 8 bits of t: a quarter of the RGBA memory
const seasonUniforms = {
  uSeasonOn: { value: 0 },
  uSeasonView: { value: 0 },
  uSeasonMix: { value: 0 },
  uSeasonA: { value: SEASON_PLACEHOLDER as THREE.Texture },
  uSeasonB: { value: SEASON_PLACEHOLDER as THREE.Texture },
  uSeasonT: { value: SEASON_PLACEHOLDER as THREE.Texture },
  uSpeedLut: { value: makeLutTexture(velocityPaletteJson.stops as [number, string][]) as THREE.Texture },
  uAnomLut: { value: SEASON_PLACEHOLDER as THREE.Texture },
  // Δ byte → t:  (byte·255 − 128) / scale / log10(vmax/vmin)
  uSeasonDeltaK: { value: 255 / 256 / Math.log10(velocityPaletteJson.vmax / velocityPaletteJson.vmin) },
  uSeasonLogRange: { value: Math.log10(velocityPaletteJson.vmax / velocityPaletteJson.vmin) },
  uAnomFade: { value: new THREE.Vector2(Math.log10(15), Math.log10(40)) },
  uAnomGrey: { value: new THREE.Color().setRGB(0.3, 0.3, 0.3, THREE.SRGBColorSpace) },
  /** 1 / the month frames' size (set from the first frame). */
  uSeasonTexel: { value: new THREE.Vector2(1 / 1200, 1 / 1400) },
}
// Debug / verification: the live uniforms (read-only use, please).
;(window as any).__seasonUniforms = seasonUniforms
let seasonOnNow = 0
let seasonViewNow = 0
let seasonTrailsNow = 1
let seasonShownA: ImageBitmap | null = null
let seasonShownB: ImageBitmap | null = null
let seasonShownT: ImageBitmap | null = null
let seasonAnomStops: [number, string][] | null = null

function attachSeasonDrape(material: THREE.MeshBasicMaterial): void {
  const prev = material.onBeforeCompile
  material.onBeforeCompile = (shader, r) => {
    prev.call(material, shader, r)
    Object.assign(shader.uniforms, seasonUniforms)
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <common>',
      `#include <common>
       uniform float uSeasonOn;
       uniform float uSeasonView;
       uniform float uSeasonMix;
       uniform sampler2D uSeasonA;
       uniform sampler2D uSeasonB;
       uniform sampler2D uSeasonT;
       uniform sampler2D uSpeedLut;
       uniform sampler2D uAnomLut;
       uniform float uSeasonDeltaK;
       uniform float uSeasonLogRange;
       uniform vec2 uAnomFade;
       uniform vec3 uAnomGrey;
       uniform vec2 uSeasonTexel;`,
    )
    // Right after the drape's texel (before the relief + cut code the DEM
    // hook appended there): the drape's alpha stays, its colour is swapped.
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <map_fragment>',
      `#include <map_fragment>
       if (uSeasonOn > 0.001) {
         vec3 sd = mix(texture2D(uSeasonA, vMapUv).rgb, texture2D(uSeasonB, vMapUv).rgb, uSeasonMix);
         float st = texture2D(uSeasonT, vMapUv).r;
         float tm = clamp(st + (sd.r - 128.0 / 255.0) * uSeasonDeltaK, 0.0, 1.0);
         // The month's palette colour minus the drape-time one, ADDED to the
         // drape's own texel: at Δ = 0 this is the drape bit for bit, even
         // on its feathered, lossily-coded edge pixels (where a re-lookup
         // of the palette would differ and flicker at the hand-over).
         vec3 cSpeed = clamp(diffuseColor.rgb + texture2D(uSpeedLut, vec2(tm, 0.5)).rgb
                             - texture2D(uSpeedLut, vec2(st, 0.5)).rgb, 0.0, 1.0);
         float pct = (sd.g * 255.0 - 128.0) / 127.0;
         float fade = clamp((st * uSeasonLogRange - uAnomFade.x) / (uAnomFade.y - uAnomFade.x), 0.0, 1.0);
         // Validity feathered over ~±2 texels (4 extra taps) so a swath
         // edge — observed this month | not — is a soft seam, not a wall.
         vec2 vo = uSeasonTexel * 1.6;
         float valid = 0.2 * sd.b + 0.2 * (
             mix(texture2D(uSeasonA, vMapUv + vec2(vo.x, vo.y)).b, texture2D(uSeasonB, vMapUv + vec2(vo.x, vo.y)).b, uSeasonMix)
           + mix(texture2D(uSeasonA, vMapUv + vec2(-vo.x, vo.y)).b, texture2D(uSeasonB, vMapUv + vec2(-vo.x, vo.y)).b, uSeasonMix)
           + mix(texture2D(uSeasonA, vMapUv + vec2(vo.x, -vo.y)).b, texture2D(uSeasonB, vMapUv + vec2(vo.x, -vo.y)).b, uSeasonMix)
           + mix(texture2D(uSeasonA, vMapUv - vo).b, texture2D(uSeasonB, vMapUv - vo).b, uSeasonMix));
         vec3 cAnom = mix(uAnomGrey, texture2D(uAnomLut, vec2(clamp(0.5 + 0.5 * pct, 0.0, 1.0), 0.5)).rgb,
                          fade * clamp(valid, 0.0, 1.0));
         diffuseColor.rgb = mix(diffuseColor.rgb, mix(cSpeed, cAnom, uSeasonView), uSeasonOn);
       }`,
    )
  }
  // Its own program: the shared DEM hook's source is identical for every
  // elevated material, so without a key three would hand this material the
  // basemap's program (without the month code).
  material.customProgramCacheKey = () => 'velocity-drape-seasons-v1'
  material.needsUpdate = true
}

function uploadSeasonSlot(tex: THREE.Texture, bmp: ImageBitmap): number {
  tex.image = bmp
  tex.needsUpdate = true
  const t0 = performance.now()
  renderer.initTexture(tex)
  return performance.now() - t0
}

function updateSeason(dt: number): void {
  const s = seasonDrape
  // Ease the three targets (~0.8 s for on/view, the trails a little slower)
  // — but while the drape itself is invisible (a deep link still streaming
  // the paint in, the fly-along's stripped state) jump straight there: an
  // ease then would show as the wrong map fading in (film: ?beat=3 opened
  // on the speed palette crossfading to the anomaly).
  const k = flowOpacity < 0.02 || velocityDrapeAt === 0 ? 1 : 1 - Math.exp(-dt * 4.2)
  // Not before the static t and a month are on the GPU (a late arrival
  // eases in rather than popping).
  const onTarget = seasonShownT && (seasonShownA || seasonShownB) ? s.on : 0
  seasonOnNow += (onTarget - seasonOnNow) * k
  if (Math.abs(onTarget - seasonOnNow) < 0.002) seasonOnNow = onTarget
  seasonViewNow += (s.view - seasonViewNow) * k
  if (Math.abs(s.view - seasonViewNow) < 0.002) seasonViewNow = s.view
  seasonTrailsNow += (s.trails - seasonTrailsNow) * (1 - Math.exp(-dt * 3))
  if (Math.abs(s.trails - seasonTrailsNow) < 0.002) seasonTrailsNow = s.trails
  if (!renderer) return
  // Uploads (the warm-up does them while the recolour is still at 0).
  if (s.staticT && s.staticT !== seasonShownT) {
    seasonShownT = s.staticT
    s.stats.staticUploadMs = uploadSeasonSlot(seasonTexT, s.staticT)
    seasonUniforms.uSeasonT.value = seasonTexT
  }
  for (const [bmp, tex, key] of [
    [s.a, seasonTexA, 'a'],
    [s.b, seasonTexB, 'b'],
  ] as const) {
    const shown = key === 'a' ? seasonShownA : seasonShownB
    if (bmp && bmp !== shown) {
      const ms = uploadSeasonSlot(tex, bmp)
      s.stats.lastUploadMs = ms
      s.stats.maxUploadMs = Math.max(s.stats.maxUploadMs, ms)
      s.stats.uploads += 1
      seasonUniforms.uSeasonTexel.value.set(1 / bmp.width, 1 / bmp.height)
      if (key === 'a') {
        seasonShownA = bmp
        seasonUniforms.uSeasonA.value = tex
      } else {
        seasonShownB = bmp
        seasonUniforms.uSeasonB.value = tex
      }
    }
  }
  if (s.anomStops && s.anomStops !== seasonAnomStops) {
    seasonAnomStops = s.anomStops
    ;(seasonUniforms.uAnomLut.value as THREE.Texture).dispose?.()
    seasonUniforms.uAnomLut.value = makeLutTexture(s.anomStops)
    seasonUniforms.uAnomFade.value.set(Math.log10(s.anomFade[0]), Math.log10(s.anomFade[1]))
    seasonUniforms.uAnomGrey.value.setRGB(s.anomGrey, s.anomGrey, s.anomGrey, THREE.SRGBColorSpace)
    seasonUniforms.uSeasonDeltaK.value = 255 / s.deltaScale / seasonUniforms.uSeasonLogRange.value
  }
  // Nothing to draw until the static t and one month are on the GPU.
  const ready = !!seasonShownT && (!!seasonShownA || !!seasonShownB)
  seasonUniforms.uSeasonOn.value = ready ? seasonOnNow : 0
  seasonUniforms.uSeasonView.value = seasonViewNow
  seasonUniforms.uSeasonMix.value = !seasonShownB ? 0 : !seasonShownA ? 1 : s.mix
}

// Per-frame: the speed drape's opacity (the phase machine's paint level ×
// a 0.8 s ramp from the moment its texture arrived — a late drape fades
// in instead of popping), then the trails: clock, knobs, resolution,
// exaggeration, opacity.
function updateFlow(now: number, dt: number): void {
  updateSeason(dt)
  if (velocityMap) {
    const r = velocityDrapeAt > 0 ? Math.min(1, (now - velocityDrapeAt) / 800) : 0
    ;(velocityMap.material as THREE.MeshBasicMaterial).opacity = flowOpacity * r * r * (3 - 2 * r)
  }
  if (!flowMat || !flowMesh) return
  const u = flowMat.uniforms
  const ready = Math.min(1, (now - flowReadyAt) / FLOW_READY_MS)
  const op = flowOpacity * ready * ready * (3 - 2 * ready) * FLOW_KNOBS.alpha * seasonTrailsNow
  const hideForCh1 = props.velocityMode?.showDashes === false
  u.uOpacity.value = hideForCh1 ? 0 : op
  // Draw the first frames after the build at opacity 0 (every fragment
  // discards): the program link + the ~23 MB vertex upload happen at load,
  // not as a ~300 ms hitch on the step-1 click.
  flowMesh.visible = u.uOpacity.value > 0.001 || flowWarmFrames > 0
  if (flowWarmFrames > 0) flowWarmFrames -= 1
  if (!flowMesh.visible) return
  // The pattern is periodic in `period`: wrap the clock in double
  // precision here so the float32 shader never loses the fraction.
  flowClock = (flowClock + Math.min(dt, 0.1) * FLOW_KNOBS.rate) % FLOW_KNOBS.period
  u.uTime.value = flowClock
  u.uPeriod.value = FLOW_KNOBS.period
  u.uTail.value = FLOW_KNOBS.tail
  u.uFastTail.value = FLOW_KNOBS.fastTail
  ;(u.uSpeedGate.value as THREE.Vector2).set(
    Math.log10(Math.max(1e-3, FLOW_KNOBS.slow)),
    Math.log10(Math.max(1e-3, FLOW_KNOBS.fast)),
  )
  ;(u.uColor.value as THREE.Color).setRGB(...FLOW_KNOBS.color)
  const pr = renderer.getPixelRatio()
  u.uHalfWidthPx.value = FLOW_KNOBS.width * pr
  renderer.getDrawingBufferSize(u.uResolution.value as THREE.Vector2)
  u.uExaggeration.value = currentExag
}

function updateMouseNDC(event: MouseEvent): void {
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  mouseNDC.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouseNDC.y = -(((event.clientY - rect.top) / rect.height) * 2 - 1)
}

function alphaHitAtUV(
  ctx: CanvasRenderingContext2D | null,
  canvas: HTMLCanvasElement | null,
  uv: { x: number; y: number },
): boolean {
  if (!ctx || !canvas) return true  // texture not loaded yet — bbox fallback
  const w = canvas.width
  const h = canvas.height
  const px = Math.max(0, Math.min(w - 1, Math.floor(uv.x * w)))
  const py = Math.max(0, Math.min(h - 1, Math.floor((1 - uv.y) * h)))
  return ctx.getImageData(px, py, 1, 1).data[3] >= 128
}

function checkGreenlandHover(): boolean {
  if (!props.greenlandHoverable || !basemap || !camera) return false
  raycaster.setFromCamera(mouseNDC, camera)
  const hits = raycaster.intersectObject(basemap, false)
  if (hits.length === 0 || !hits[0].uv) return false
  return alphaHitAtUV(basemapAlphaCtx, basemapAlphaCanvas, hits[0].uv)
}

function checkNJHover(): boolean {
  if (!props.greenlandHoverable || !njMesh || !camera) return false
  raycaster.setFromCamera(mouseNDC, camera)
  const hits = raycaster.intersectObject(njMesh, false)
  if (hits.length === 0 || !hits[0].uv) return false
  return alphaHitAtUV(njAlphaCtx, njAlphaCanvas, hits[0].uv)
}

// True if the mouse is currently over the NL beacon's hit envelope.
// The hit mesh is an invisible filled disc at the pulse ring's MAX
// extent (5× lake radius) so the user can click anywhere within the
// pulse's outer envelope — not just the tiny real-size lake. Only
// mounted when SectionCh1 emits a lake-polygons payload with a
// highlightId, so this naturally returns false outside Ch.1 Beat 0.
function checkLakeBeaconHover(): boolean {
  if (!lakePolyHighlightHitMesh || !camera) return false
  raycaster.setFromCamera(mouseNDC, camera)
  const hits = raycaster.intersectObject(lakePolyHighlightHitMesh, false)
  return hits.length > 0
}

let isHoveringLakeBeacon = false

function onCanvasMouseMove(event: MouseEvent): void {
  updateMouseNDC(event)
  // Lake-beacon hover works in any phase — the beacon only exists
  // when SectionCh1 has mounted it, so the check naturally gates.
  isHoveringLakeBeacon = checkLakeBeaconHover()
  // Featured drainage-class lakes: hover grows the lake 1.5×.
  const wasFeatured = hoveredFeaturedId
  hoveredFeaturedId = checkFeaturedHover()
  if (hoveredFeaturedId !== wasFeatured) emit('lake-beacon-hover', hoveredFeaturedId)
  // Ch.2 block: catalog-lake hover (gated inside on lakesA > 0).
  const simHover = simLakeAtPointer()
  setSimLakeHover(simHover)
  if (!props.greenlandHoverable) {
    isHoveringGreenland = false
    isHoveringNJ = false
    if (canvasRef.value) {
      canvasRef.value.style.cursor =
        isHoveringLakeBeacon || hoveredFeaturedId || simHover ? 'pointer' : ''
    }
    return
  }
  // Check NJ first — it's much smaller, and if the mouse hits it we
  // want the orange glow, not the gold (Greenland fully encloses
  // North America in the bounding sense, so they don't actually
  // overlap, but checking NJ first is consistent if we add more eggs).
  isHoveringNJ = checkNJHover()
  isHoveringGreenland = !isHoveringNJ && checkGreenlandHover()
  if (canvasRef.value) {
    canvasRef.value.style.cursor =
      isHoveringLakeBeacon || isHoveringGreenland || isHoveringNJ ? 'pointer' : ''
  }
}

function onCanvasMouseLeave(): void {
  isHoveringGreenland = false
  isHoveringNJ = false
  isHoveringLakeBeacon = false
  if (hoveredFeaturedId !== null) emit('lake-beacon-hover', null)
  hoveredFeaturedId = null
  setSimLakeHover(null)
  if (canvasRef.value) canvasRef.value.style.cursor = ''
}

// Distinguish real clicks from orbit-drag releases (the browser fires
// `click` after a drag too): remember where the press started.
let pressX = 0
let pressY = 0
function onCanvasMouseDown(event: MouseEvent): void {
  pressX = event.clientX
  pressY = event.clientY
}

function onCanvasClick(event: MouseEvent): void {
  updateMouseNDC(event)
  const dragged = Math.hypot(event.clientX - pressX, event.clientY - pressY) > 9
  // Ch.2 block: click pins/unpins a catalog lake's stress popout.
  if (!dragged && simTileMesh && (props.simDomain?.lakesA ?? 0) >= 0.2) {
    const simHit = simLakeAtPointer()
    if (simHit) {
      simLakePinCw = simLakePinCw === simHit.cw ? null : simHit.cw
      updateSimLakesVisibility()
      emit('sim-lake-pick', simLakePinCw === null ? null : simHit)
      return
    }
    if (simLakePinCw !== null) {
      simLakePinCw = null
      updateSimLakesVisibility()
      emit('sim-lake-pick', null)
    }
  }
  // Featured drainage-class lake click → open that lake's movie popup.
  const featuredHit = checkFeaturedHover()
  if (featuredHit) {
    emit('lake-beacon-click', featuredHit)
    return
  }
  // Lake beacon click is gated by mesh existence, not greenlandHoverable
  // (which is specifically the intro-mode easter-egg flag).
  if (checkLakeBeaconHover() && lakePolyHighlightId) {
    emit('lake-beacon-click', lakePolyHighlightId)
    return
  }
  if (!props.greenlandHoverable) {
    // Nothing interactive hit — let the parent dismiss transient UI
    // (e.g. the lake-video dock closes when you click empty globe).
    emit('canvas-blank-click')
    return
  }
  if (checkNJHover()) {
    window.open(NJ_URL, '_blank', 'noopener,noreferrer')
    return
  }
  if (checkGreenlandHover()) {
    emit('greenland-click')
  }
}

function applyCamera(): void {
  const r = GLOBE_RADIUS * currentDistance
  camera.position.set(
    r * Math.cos(currentLat) * Math.cos(currentLon),
    r * Math.cos(currentLat) * Math.sin(currentLon),
    r * Math.sin(currentLat),
  )
  camera.up.set(cameraUp[0], cameraUp[1], cameraUp[2])
  camera.lookAt(focal[0], focal[1], focal[2])
  applyViewOffset()
}

function applyViewOffset(): void {
  // Shift the projection's principal point so Greenland renders left
  // of viewport-center. fullWidth = w*(1+s) so the rendered window is
  // a sub-rect of a virtual image that's `s` fraction wider; offset
  // by s*w means we render the rightmost portion, which makes the
  // virtual-image-center (= camera lookAt) appear at (1-s)/2 of the
  // window — left of center by s/2.
  //
  // GOTCHA: PerspectiveCamera.setViewOffset() *mutates* camera.aspect
  // to (fullWidth / fullHeight). clearViewOffset() does NOT restore it.
  // So when transitioning from offset-on to offset-off (e.g. Return to
  // globe), we must explicitly reset aspect to the canvas's true ratio
  // — otherwise the globe renders egg-shaped (squished tall) until the
  // next ResizeObserver tick.
  //
  //
  // The stage fit rides the same call: the virtual image is `z` times
  // larger both ways, and the window is placed so the look-at point shows
  // at (px, py) of it — z = 1 and (px, py) = ((1 − s)/2 · w, h/2) is the
  // plain shift above.
  if (!canvasRef.value || !camera) return
  const w = canvasRef.value.clientWidth
  const h = canvasRef.value.clientHeight
  const e = stageFitEOverride ?? (stageFitT > 0 ? easeInOutCubic(stageFitT) : 0)
  if (currentViewShift <= 0.001 && e === 0) {
    camera.clearViewOffset()
    camera.aspect = w / h
    camera.updateProjectionMatrix()
  } else {
    let z = 1
    let px = (w * (1 - currentViewShift)) / 2
    let py = h / 2
    if (e > 0) {
      // The room beside the panel; the silhouette as large as the room's
      // width (less its margins) and STAGE_MAX_H allow, never smaller than
      // it already is, its box centred in the room.
      const room = w - Math.min(stageFitSpec.rightVw * w, stageFitSpec.rightMaxPx)
      const bw = (STAGE_BBOX.r - STAGE_BBOX.l) * h
      const bh = (STAGE_BBOX.b - STAGE_BBOX.t) * h
      const zFit = Math.max(1, Math.min((room - 2 * STAGE_MARGIN_X * w) / bw, (STAGE_MAX_H * h) / bh))
      const pxFit = room / 2 - ((STAGE_BBOX.l + STAGE_BBOX.r) / 2) * h * zFit
      const pyFit = h / 2 - ((STAGE_BBOX.t + STAGE_BBOX.b) / 2) * h * zFit
      z += (zFit - 1) * e
      px += (pxFit - px) * e
      py += (pyFit - py) * e
    }
    const fw = w * (1 + currentViewShift) * z
    const fh = h * z
    camera.setViewOffset(fw, fh, fw / 2 - px, fh / 2 - py, w, h)
  }
}

function init(): void {
  if (!canvasRef.value) return
  const canvas = canvasRef.value

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x000000)

  const w = canvas.clientWidth || 1920
  const h = canvas.clientHeight || 1080
  camera = new THREE.PerspectiveCamera(30, w / h, 0.01, 100)

  renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    // Required for canvas.toDataURL() to capture the rendered frame
    // — without it the buffer is cleared on present and the screenshot
    // tool gets a blank canvas. Tiny perf cost on most GPUs.
    preserveDrawingBuffer: true,
  })
  // Super-sample for sharper output: render at >= 2× device-pixel
  // resolution then let the browser downsample. On retina screens the
  // browser is already 2×; we cap at 3 to avoid GPU thrash on 4K
  // displays. This is the cheapest single-knob upgrade for "still
  // pixelated" feedback — the source texture and aniso are already
  // maxed; we just weren't sampling them often enough per frame.
  const targetPR = Math.min(3, Math.max(2, window.devicePixelRatio || 1))
  renderer.setPixelRatio(targetPR)
  renderer.setSize(w, h, false)

  // Asset URLs honor Vite's BASE_URL so they resolve correctly under
  // High-segment-count globe so the satellite texture wraps without
  // visible polygon faceting, especially at oblique viewing angles.
  const geometry = new THREE.SphereGeometry(GLOBE_RADIUS, 192, 96)
  const tex = loadTexBitmap(mediaUrl('shared/earth_esri.jpg'))
  tex.colorSpace = THREE.SRGBColorSpace
  // Anisotropic filtering — sharpens texels at oblique angles where
  // standard bilinear sampling otherwise looks blocky.
  tex.anisotropy = renderer.capabilities.getMaxAnisotropy()
  const material = new THREE.MeshBasicMaterial({ map: tex })
  globe = new THREE.Mesh(geometry, material)
  globe.rotation.x = Math.PI / 2
  scene.add(globe)

  // Legacy 8-bit grayscale DEM. Still used by the basemap fragment
  // shader's hillshade gradient + the cross-section / chapter-slab
  // fragment shaders, where GPU bilinear sampling is wanted (and
  // 8-bit precision is plenty since these are colour/gradient
  // decisions, not displacement).
  demTexture = loadTexBitmap(mediaUrl('shared/greenland_dem.png')) as THREE.Texture
  demTexture.colorSpace = THREE.NoColorSpace
  demTexture.anisotropy = renderer.capabilities.getMaxAnisotropy()

  // High-precision DEM. RG-packed 16-bit at 10400 × 4000 (matches the
  // basemap). MUST use NearestFilter — GPU bilinear blends R and G
  // independently, which corrupts the encoding at byte-rollover
  // boundaries (visible as a 14 m terrace step at exactly the places
  // we're trying to make smooth). The vertex shader does its own
  // 4-tap bilinear interp to compensate (see attachDemDisplacement).
  // We mirror the CPU readback canvas off THIS texture, not the
  // legacy one, so getDemElevAt() gets the same 0.05 m precision
  // surface-hugging overlays now expect.
  demTextureHi = loadTexBitmap(
    mediaUrl('shared/greenland_dem_rg16.png'),
    (loaded) => {
      const c = document.createElement('canvas')
      const ctx = c.getContext('2d', { willReadFrequently: true })
      if (ctx) {
        drawTexImageUpright(ctx, loaded)
        demReadbackCanvas = c
        demReadbackCtx = ctx
        // Overlays that sample the DEM through getDemElevAt() may have
        // been built before this readback existed (elevation read as 0
        // → the five featured lakes sat at SEA LEVEL, drawn through the
        // ice ~100 px below their true spot whenever the 18 MB DEM lost
        // the race to the lakes' JSON — seen on Ch.1 and Ch.3 beat 0).
        // Rebuild them now that the surface is known.
        if (featuredData) buildFeaturedGroups()
        if (lakePolyData) buildLakePolyGeometries()
        if (streamHiPolyline) buildStreamHiTube()
        if (lakeStripSurf) relayLakeStrip(true)
      }
    },
  )
  demTextureHi.colorSpace = THREE.NoColorSpace
  demTextureHi.minFilter = THREE.NearestFilter
  demTextureHi.magFilter = THREE.NearestFilter
  demTextureHi.generateMipmaps = false  // mipmaps would average R+G channels — same corruption as bilinear

  // Detail-resolution variant for hillshade. Same encoding, sigma=2 km
  // smoothing instead of sigma=8 km — preserves catchment-scale surface
  // structure that the lighting can grip.
  demTextureHiDetail = loadTexBitmap(mediaUrl('shared/greenland_dem_rg16_detail.png'))
  demTextureHiDetail.colorSpace = THREE.NoColorSpace
  demTextureHiDetail.minFilter = THREE.NearestFilter
  demTextureHiDetail.magFilter = THREE.NearestFilter
  demTextureHiDetail.generateMipmaps = false

  // Bed elevation texture for the cross-section slab fragment shader.
  // Produced by build_bed_texture.py; encoding: pixel/255 → bed_m via
  // BED_MIN_M..BED_MAX_M. The CPU readback mirror feeds the beat 3→4
  // fit solve (getBedElevAt — the idealized slab's bed level).
  bedTexture = loadTexBitmap(mediaUrl('shared/greenland_bed.png'), (loaded) => {
    const c = document.createElement('canvas')
    const ctx = c.getContext('2d', { willReadFrequently: true })
    if (ctx) {
      drawTexImageUpright(ctx, loaded)
      bedReadbackCanvas = c
      bedReadbackCtx = ctx
    }
  })
  bedTexture.colorSpace = THREE.NoColorSpace
  bedTexture.anisotropy = renderer.capabilities.getMaxAnisotropy()

  // Hi-res ESRI basemap at zoom 11 (16380 × 6300, ~50 MB). At
  // ~125 m/pixel ground resolution, supraglacial lakes appear naturally
  // as cyan patches in the imagery — removes the need for the
  // synthetic flat-disc lake overlay for "where are the lakes?" beats.
  // The legacy 10400 × 4000 / zoom-7 asset stays on R2 at
  // greenland_basemap.png for the hover-glow texture (which only needs
  // the alpha mask, not pixel detail).
  basemap = makeGreenlandPatch(mediaUrl('shared/greenland_basemap_hires.png'), -1)
  attachDemDisplacement(basemap.material as THREE.MeshBasicMaterial)
  scene.add(basemap)

  // The Introduction's speed drape (NASA SVS 3848 palette, log 1–3000
  // m/yr, alpha = the ITS_LIVE ice mask — rock and tundra show the
  // satellite basemap through it). Hidden until its texture is in: a
  // MeshBasicMaterial with no map renders its colour (a white plate).
  velocityMap = makeGreenlandPatch(mediaUrl(FLOW_DRAPE_KEY), -2, true)
  // Relief on the speed drape at FULL strength — what the site has always
  // shown. (It was written as 0.55, "half-strength", but three keys
  // programs by onBeforeCompile's SOURCE TEXT, identical for every
  // elevated material, so this drape silently ran the basemap's 1.0
  // program; the seasons hook below gives it a program of its own, and
  // 0.55 then really halved the relief — a visible change to the
  // "Greenland flows" look the director approved. Keep 1.0 unless asked.)
  attachDemDisplacement(velocityMap.material as THREE.MeshBasicMaterial, 1.0)
  // The Introduction's "seasons" steps recolour this same drape by month.
  attachSeasonDrape(velocityMap.material as THREE.MeshBasicMaterial)
  scene.add(velocityMap)

  // Cross-section slab — appears at the moving cut line when the
  // slider sweeps east→west. Geometry is canonical at lon=CUT_LON_FINAL;
  // animate() rotates the mesh around the polar axis each frame to
  // track the current uCutLon.
  crossSectionMesh = makeCrossSectionMesh()
  scene.add(crossSectionMesh)

  // Vertical scale arrow east of the cross-section. Pairs with the
  // inset zoom window (separate canvas) showing the ice column height
  // as 6 stacked OWTCs. Fades in once the cut sweep nears completion.
  scaleArrow = makeScaleArrow()
  scene.add(scaleArrow)
  // Warm the standard-material shader these two groups share (the dims
  // step's measuring arrows + the scale arrow, hidden until the
  // Introduction) off the menu → Introduction click, where its first-use
  // compile cost ~270 ms of main thread (measured). Deferred past the
  // first paint; compile() takes any Object3D and the scene's lights.
  // compileAsync also waits for the LINK (KHR_parallel_shader_compile),
  // so the first draw does not block on getProgramInfoLog either.
  window.setTimeout(() => {
    const warm = async () => {
      if (arrowsGroup) await renderer.compileAsync(arrowsGroup, camera, scene)
      if (scaleArrow) await renderer.compileAsync(scaleArrow, camera, scene)
    }
    warm().catch(() => { /* a lost context: nothing to warm */ })
  }, 2500)


  // Hover meshes for the "click on Greenland to begin" intro affordance.
  // Always in the scene; opacity controlled by hover state in animate().
  const hover = makeGreenlandHoverMeshes()
  greenlandGlow = hover.glow
  greenlandOutline = hover.outline
  scene.add(greenlandGlow)
  scene.add(greenlandOutline)

  // NJ → Princeton AOS easter egg.
  const nj = makeNJHoverMeshes()
  njMesh = nj.hit
  njGlow = nj.glow
  njOutline = nj.outline
  scene.add(njMesh)
  scene.add(njGlow)
  scene.add(njOutline)

  // Mouse listeners for hover + click on Greenland (intro mode only).
  canvas.addEventListener('mousemove', onCanvasMouseMove)
  canvas.addEventListener('mousedown', onCanvasMouseDown)
  canvas.addEventListener('click', onCanvasClick)
  canvas.addEventListener('mouseleave', onCanvasMouseLeave)

  // 3D silvery length-scale arrows + scene lighting.
  buildArrowsAndLights()

  loadFlowTrails()

  applyCamera()

  // OrbitControls — drag to rotate, scroll to zoom. Damping smooths the
  // motion. enablePan off so users can't translate away from the scene.
  controls = new OrbitControls(camera, canvas)
  controls.enablePan = false
  controls.enableDamping = true
  controls.dampingFactor = 0.06
  controls.rotateSpeed = 0.6
  controls.zoomSpeed = 0.7
  // minDistance is the minimum distance from camera to controls.target
  // (NOT to the globe origin). Chapter framings put the orbit target
  // at a surface point and the camera ~0.15 away — well inside the
  // old 0.525 floor, which caused the camera to snap out to that floor
  // the instant the user grabbed to rotate. 0.01 lets the user freely
  // rotate at any chapter zoom level. The camera can't realistically
  // get inside the globe at typical rotation angles, since the orbit
  // target sits at the surface and standard horizontal rotation
  // preserves "above the surface" by symmetry.
  controls.minDistance = 0.01
  controls.maxDistance = GLOBE_RADIUS * 12
  controls.target.set(focal[0], focal[1], focal[2])

  controls.addEventListener('start', () => {
    // Never enter user-control mode while a scripted cinematic
    // transition is mid-flight ('opening', 'streaming') — otherwise a
    // stray click during the zoom-to-Greenland would pause the camera
    // and leave the globe half-faded. User control is only allowed in
    // settled phases (spinning hub, opened, streamed).
    const settled = phase === 'spinning' || phase === 'opened' || phase === 'streamed' || phase === 'stripped'
    if (!settled) return
    cameraMode = 'user'
    if (userIdleTimerId !== null) {
      window.clearTimeout(userIdleTimerId)
      userIdleTimerId = null
    }
    returnLerp = null
  })
  controls.addEventListener('end', () => {
    // Only schedule the return-lerp if we actually entered user mode
    // (i.e. the 'start' handler didn't bail out due to a transitioning
    // phase). Otherwise this would queue a needless transition.
    if (cameraMode !== 'user') return
    if (userIdleTimerId !== null) window.clearTimeout(userIdleTimerId)
    // Phase-aware idle timeout: 5 s on the spinning hub (user might
    // be hunting easter eggs), 2 s once Greenland is on screen.
    const idleMs = phase === 'spinning'
      ? USER_IDLE_MS_SPINNING
      : USER_IDLE_MS_POST_ZOOM
    userIdleTimerId = window.setTimeout(() => {
      // Snapshot current camera state, then lerp back to scripted.
      returnLerp = {
        start: performance.now(),
        posFrom: camera.position.clone(),
        targetFrom: controls!.target.clone(),
        upFrom: camera.up.clone(),
      }
      cameraMode = 'returning'
      userIdleTimerId = null
    }, idleMs)
  })

  resizeObserver = new ResizeObserver(() => {
    const w2 = canvas.clientWidth
    const h2 = canvas.clientHeight
    if (w2 === 0 || h2 === 0) return
    camera.aspect = w2 / h2
    camera.updateProjectionMatrix()
    renderer.setSize(w2, h2, false)
  })
  resizeObserver.observe(canvas)

  lastTime = performance.now()
  animate(lastTime)
}

// While paused (an opaque overlay owns the screen), the globe still
// renders ONE frame each time its pending texture set drains — GPU
// uploads happen at first bind, and deferring them all to the unpause
// frame was a single ~5 s texSubImage2D stall on deep links straight
// to the twins beat (profiled).
let pausedWarmCount = -1
// `covered`: the trickle's clock (see the prop).
const COVERED_FRAME_MS = 250
let lastCoveredFrame = 0
// The featured drainage-class lakes, once per frame AFTER the camera is
// placed and the exaggeration tween has written `currentExag` (the second
// pass at the director's report that lake 2394's polygon looked choppy):
// this block used to run at the TOP of animate(), before the chapter-focus
// lerp, the chapter-exag lerp and applyCamera() — so the held lake was
// relaid from the previous frame's exaggeration and projected with the
// previous frame's camera while the terrain wore the new ones. One frame
// behind is invisible at a steady 60 fps (0.04 px — why the first fix
// measured clean) and an alternating jump at ~30 fps with uneven frames
// (17 px at retina in Chrome on the live site, as the director sees it).
// Called from every render path right before renderer.render.
function updateFeaturedLakes(time: number, dt: number): void {
  // `Vector3.project()` reads the camera's matrixWorldInverse, which only
  // renderer.render refreshes — applyCamera() moves the camera without it.
  // Refresh here so the ring is projected from THIS frame's camera, not the
  // last rendered one (the residual one-frame jumps on long frames).
  if (camera) {
    camera.updateMatrixWorld()
    camera.matrixWorldInverse.copy(camera.matrixWorld).invert()
  }
  // Featured drainage-class lakes: hover-scale lerp (grow the hovered
  // lake toward 1.5×, others back to 1×) + screen projections for
  // out-of-band tooling (popup click tests).
  if (featuredGroups.length && camera && renderer) {
    const cw = renderer.domElement.clientWidth
    const ch = renderer.domElement.clientHeight
    // `scale` rides along for tooling (the pulse is otherwise invisible
    // to DOM probes).
    const screens: Record<string, {
      x: number; y: number; visible: boolean; scale: number
      color: string; op: number; ring: [number, number][]
    }> = {}
    const camDirF = camera.position.clone().normalize()
    // Pulse for the legend-hovered lake (the director wanted a much
    // bigger pulse; was 1× → 1.35× on a 1.9 s breath): 1× →
    // 2.4× → 1× on a 1.4 s cycle, phase reset on each new hover so the
    // first motion is always a grow. Direct hover on the globe still
    // wins with the steady 1.5× grow.
    if (props.featuredPulseId !== featuredPulseLastId) {
      featuredPulseLastId = props.featuredPulseId ?? null
      featuredPulseSince = time
    }
    const pulsePhase = ((time - featuredPulseSince) / 1000) * (2 * Math.PI / FEATURED_PULSE_PERIOD_S)
    const legPulse = 1 + (FEATURED_PULSE_MAX - 1) * (0.5 - 0.5 * Math.cos(pulsePhase))
    for (const fg of featuredGroups) {
      if (featuredKeep?.track && featuredKeep.id === fg.id) {
        const k = Math.min(1, Math.max(0, featuredKeep.shrink ?? 0))
        const want = fg.vizScale + (1 - fg.vizScale) * k
        if (Math.abs(want - fg.builtScale) > 1e-3 || fg.builtExag !== currentExag) relayFeatured(fg, want)
      }
      const target =
        fg.id === hoveredFeaturedId
          ? FEATURED_HOVER_SCALE
          : fg.id === props.featuredPulseId
            ? legPulse
            : 1
      fg.scaleCurrent += (target - fg.scaleCurrent) * Math.min(1, dt * 10)
      fg.group.scale.setScalar(fg.scaleCurrent)
      // The swelling lake draws over its neighbours (NL / MD / LD sit a
      // few pixels apart at the landing framing). A Group's renderOrder
      // sorts its whole subtree (three's groupOrder).
      fg.group.renderOrder = fg.scaleCurrent > 1.02 ? 10 : 9
      const ndc = fg.centroid.clone().project(camera)
      // The drawn outline in screen px (the leader line's stop).
      const ring: [number, number][] = fg.edge.map((e) => {
        _anchorV.copy(e).multiplyScalar(fg.scaleCurrent).add(fg.centroid).project(camera)
        return [(_anchorV.x + 1) * 0.5 * cw, (1 - _anchorV.y) * 0.5 * ch]
      })
      screens[fg.id] = {
        x: (ndc.x + 1) * 0.5 * cw,
        y: (1 - ndc.y) * 0.5 * ch,
        visible: ndc.z > -1 && ndc.z < 1 && camDirF.dot(_anchorN.copy(fg.centroid).normalize()) > 0.05,
        scale: Math.round(fg.scaleCurrent * 100) / 100,
        color: fg.color,
        op: featuredOpFor(fg.id),
        ring,
      }
    }
    ;(window as any).__featuredLakeScreens = screens
  } else {
    ;(window as any).__featuredLakeScreens = null
  }
}
/** When the pause began (performance.now ms; −1 = not paused). */
let pausedSince = -1
const PAUSED_WARM_DELAY_MS = 2600
const PAUSED_WARM_STEP_MS = 150
let pausedWarmLast = -1e9
let pausedWarmQueue: THREE.Texture[] | null = null
/** Every texture a scene material references that the renderer has not
 *  uploaded yet (the warm-while-paused backlog). */
function sceneTexturesNotUploaded(): THREE.Texture[] {
  const out: THREE.Texture[] = []
  const seen = new Set<THREE.Texture>()
  const props = renderer.properties as unknown as { get: (t: THREE.Texture) => { __webglTexture?: unknown } }
  const consider = (t: unknown): void => {
    if (!(t instanceof THREE.Texture) || seen.has(t)) return
    seen.add(t)
    if (props.get(t).__webglTexture === undefined) out.push(t)
  }
  scene.traverse((o) => {
    const m = (o as THREE.Mesh).material
    const mats = Array.isArray(m) ? m : m ? [m] : []
    for (const mat of mats) {
      const mm = mat as unknown as Record<string, unknown>
      for (const k of ['map', 'alphaMap', 'emissiveMap', 'normalMap', 'roughnessMap', 'metalnessMap']) consider(mm[k])
      const u = mm.uniforms as Record<string, { value: unknown }> | undefined
      if (u) for (const key of Object.keys(u)) consider(u[key]?.value)
    }
  })
  return out
}
function animate(time: number): void {
  animationId = requestAnimationFrame(animate)
  ;(window as any).__globePaused = !!props.paused
  if (props.paused) {
    // A framing asked for while covered (the twins' close-out aims us at
    // Chapter 2's opening) lands NOW, under the cover — the flight can't
    // tick here, and unpausing mid-flight showed the old framing for a
    // frame and then a late glide (the Chapter 1 takeaway flashed, then
    // the greenland object flashed in, as the director reported).
    if (chapterLerp) finishChapterLerp()
    // The warm render (every texture not yet on the GPU goes up in one
    // frame — seconds of texSubImage2D in software GL, a long hitch on
    // any GPU) waits until the cover has settled: it used to fire the
    // instant the twin globes paused us, inside their fade-in (the
    // director found the jump from the ACL slider page to the
    // painted-on-greenland-surface page choppy).
    if (pausedSince < 0) pausedSince = time
    if (
      time - pausedSince > PAUSED_WARM_DELAY_MS &&
      texturesPending === 0 &&
      pausedWarmCount !== texturesStarted &&
      time - pausedWarmLast > PAUSED_WARM_STEP_MS
    ) {
      // One texture per step, then the shaders, then one render — never
      // the whole backlog in a single frame.
      pausedWarmLast = time
      if (pausedWarmQueue === null) pausedWarmQueue = sceneTexturesNotUploaded()
      const next = pausedWarmQueue.shift()
      if (next) {
        try { renderer.initTexture(next) } catch { /* lazy on first use */ }
      } else {
        pausedWarmCount = texturesStarted
        pausedWarmQueue = null
        renderer.compileAsync(scene, camera).then(() => {
          if (props.paused) renderer.render(scene, camera)
        }).catch(() => { /* a lost context */ })
      }
    }
    return
  }
  pausedSince = -1
  pausedWarmQueue = null
  if (props.covered) {
    if (time - lastCoveredFrame < COVERED_FRAME_MS) return
    lastCoveredFrame = time
  }
  const dt = (time - lastTime) / 1000
  lastTime = time

  // Flow comets advance regardless of camera mode.
  updateFlow(time, dt)

  // Smooth lerp of the NL highlight tube's opacity toward its target.
  // Beat 3 → Beat 4 sets target 1 → 0; the rate-of-approach below is
  // tuned so the fade reads as a deliberate hand-off (~0.5 s to ≈0)
  // rather than an abrupt clear.
  if (streamHiMat) {
    streamHiOpacityCurrent += (streamHiOpacityTarget - streamHiOpacityCurrent) * Math.min(1, dt * 4)
    streamHiMat.opacity = streamHiOpacityCurrent
  }

  // Chapter colormap drape — same deliberate-hand-off fade rate as the
  // tube (≈0.5 s), driven by the chapterOverlay prop's opacity target.
  if (chapterOverlayMesh) {
    chapterOverlayOpacityCurrent +=
      (chapterOverlayOpacityTarget - chapterOverlayOpacityCurrent) * Math.min(1, dt * 4)
    ;(chapterOverlayMesh.material as THREE.MeshBasicMaterial).opacity =
      chapterOverlayOpacityCurrent
  }

  // NL beacon pulse — sonar-style ring expanding/contracting around
  // the real-size lake. The pulse ring's scale animates 1×→5×→1× over
  // a 3-second cycle; opacity also fades (1.0 at min scale → 0.0 at
  // max scale) so the ring looks like a ripple dissipating outward.
  // The static fill + outline stay at steady opacity at real size.
  if (lakePolyHighlightPulseMesh && lakePolyHighlightPulseMat) {
    const t = (time / 1000) * (2 * Math.PI / 3.0)  // 3 s period
    const pulse = 0.5 + 0.5 * Math.sin(t)
    lakePolyHighlightPulseMesh.scale.setScalar(1 + 4 * pulse)
    lakePolyHighlightPulseMat.opacity = lakePolyState.opacity * (1 - pulse * 0.85)
  }

  // Ch.1 beats 1–2: North Lake's cutaway outline on the surface.
  updateLakeCutaway()

  // A surface lake strip follows the dome through exaggeration changes.
  if (lakeStripSurf && lakeStripSurf.exag !== currentExag) relayLakeStrip(false)

  // Generic screen anchors (screenAnchors prop) — see the prop's doc.
  if (props.screenAnchors?.length && camera && renderer) {
    const cw = renderer.domElement.clientWidth
    const ch = renderer.domElement.clientHeight
    const camDir = camera.position.clone().normalize()
    const out: Record<string, { x: number; y: number; visible: boolean }> = {}
    for (const a of props.screenAnchors) {
      const la = (a.lat * Math.PI) / 180
      const lo = (a.lon * Math.PI) / 180
      const r =
        GLOBE_RADIUS +
        (a.surface ? (getDemElevAt(a.lon, a.lat) / SURF_MAX_M) * currentExag : 0) +
        (a.lift ?? 0)
      _anchorV.set(r * Math.cos(la) * Math.cos(lo), r * Math.cos(la) * Math.sin(lo), r * Math.sin(la))
      const facing = camDir.dot(_anchorN.copy(_anchorV).normalize()) > 0.05
      _anchorV.project(camera)
      out[a.id] = {
        x: (_anchorV.x + 1) * 0.5 * cw,
        y: (1 - _anchorV.y) * 0.5 * ch,
        visible: facing && _anchorV.z > -1 && _anchorV.z < 1,
      }
    }
    ;(window as any).__globeAnchorScreens = out
  } else if ((window as any).__globeAnchorScreens) {
    ;(window as any).__globeAnchorScreens = null
  }

  // NL screen-position projection. Consumed by the "Where does the
  // water go?" HTML button in Explore.vue, which positions itself at
  // these pixel coords each frame so the affordance tracks the lake
  // through camera pans, rotation, and exag changes. `visible` is
  // false when the lake is behind the globe (back hemisphere) or
  // off-screen. Fires in both the legacy highlight mode and the
  // featured-lakes mode (Beat 0's current overlay).
  const nlOverlayActive =
    (lakePolyHighlightFillMesh && lakePolyHighlightId === 'CW2019_1889') ||
    featuredGroups.some((f) => f.id === 'CW2019_1889')
  if (nlOverlayActive && camera && renderer) {
    const NL_LAT_RAD = (68.7249 * Math.PI) / 180
    const NL_LON_RAD = (-49.4957 * Math.PI) / 180
    const rNL = surfaceRadiusAt(-49.4957, 68.7249, GLOBE_RADIUS * 0.0001)
    const pNL = new THREE.Vector3(
      rNL * Math.cos(NL_LAT_RAD) * Math.cos(NL_LON_RAD),
      rNL * Math.cos(NL_LAT_RAD) * Math.sin(NL_LON_RAD),
      rNL * Math.sin(NL_LAT_RAD),
    )
    // Visible = same hemisphere as camera (dot > some small positive).
    const camDir = camera.position.clone().normalize()
    const facing = camDir.dot(pNL.clone().normalize()) > 0.05
    const ndc = pNL.project(camera)
    const cw = renderer.domElement.clientWidth
    const ch = renderer.domElement.clientHeight
    ;(window as any).__nlBeaconScreen = {
      x: (ndc.x + 1) * 0.5 * cw,
      y: (1 - ndc.y) * 0.5 * ch,
      visible: facing && ndc.z > -1 && ndc.z < 1,
    }
  } else {
    ;(window as any).__nlBeaconScreen = null
  }

  // Slab fracture screen anchor — where the surface lake / drain column
  // meets the ice surface on the cross-section slab. Consumed by the
  // beat-anchored action buttons ("drain the lake ↓", "how does the
  // ice respond? →", "idealize the geometry →") in Explore.vue.
  if (chapterSlabMat && camera && renderer &&
      (chapterSlabMat.uniforms.uOpacity.value as number) > 0.05) {
    const fracT = chapterSlabMat.uniforms.uFracTLon.value as number
    const lonRad = CH_SLAB_LON_W + fracT * (CH_SLAB_LON_E - CH_SLAB_LON_W)
    const cutLat = chapterSlabMat.uniforms.uCutLatRad.value as number
    const lonDeg = (lonRad * 180) / Math.PI
    const latDeg = (cutLat * 180) / Math.PI
    const elevM = getDemElevAt(lonDeg, latDeg)
    const r = GLOBE_RADIUS + (elevM / SURF_MAX_M) * currentExag
    const p = new THREE.Vector3(
      r * Math.cos(cutLat) * Math.cos(lonRad),
      r * Math.cos(cutLat) * Math.sin(lonRad),
      r * Math.sin(cutLat),
    )
    const ndc = p.project(camera)
    const cw = renderer.domElement.clientWidth
    const ch = renderer.domElement.clientHeight
    ;(window as any).__slabFracScreen = {
      x: (ndc.x + 1) * 0.5 * cw,
      y: (1 - ndc.y) * 0.5 * ch,
      visible: ndc.z > -1 && ndc.z < 1,
    }
  } else {
    ;(window as any).__slabFracScreen = null
  }

  // Ch.1 morph variant B: spin the chapter slab about the radial axis
  // at the fracture (0 → π). At π the camera sees the slab's BACK face
  // — DoubleSide renders the texture mirrored, so ice flow reverses to
  // the simulation domain's left→right before math mode fades in.
  if (chapterSlabMesh && chapterSlabMat) {
    if (chapterSlabSpinT > 0.0005) {
      const fracT = chapterSlabMat.uniforms.uFracTLon.value as number
      const lonRad = CH_SLAB_LON_W + fracT * (CH_SLAB_LON_E - CH_SLAB_LON_W)
      const latRad = chapterSlabMat.uniforms.uCutLatRad.value as number
      const axis = new THREE.Vector3(
        Math.cos(latRad) * Math.cos(lonRad),
        Math.cos(latRad) * Math.sin(lonRad),
        Math.sin(latRad),
      )
      chapterSlabMesh.quaternion.setFromAxisAngle(axis, Math.PI * chapterSlabSpinT)
    } else if (chapterSlabMesh.quaternion.w !== 1) {
      chapterSlabMesh.quaternion.identity()
    }
  }

  // Cross-section slab follows the moving cut line. Rotate around the
  // polar axis (world +Z) to translate the slab from its canonical lon
  // (CUT_LON_FINAL) to wherever uCutLon is right now.
  if (crossSectionMesh && crossSectionMat) {
    const cutLon = crossSectionMat.uniforms.uCutLon.value as number
    crossSectionMesh.rotation.z = cutLon - CUT_LON_FINAL
  }

  // Project the scale arrow's bottom + top tips to screen pixel coords.
  // InsetZoom reads them in the SAME frame (its rAF loop was registered
  // after this one, so it runs after it every frame): it parks the tower
  // stack beside the cut face and draws the two dashed ties from here —
  // no cross-component frame lag while the user OrbitControls-rotates.
  if (scaleArrowTipBottom && scaleArrowTipTop && camera && renderer) {
    const canvas = renderer.domElement
    const cw = canvas.clientWidth
    const ch = canvas.clientHeight
    const ndcB = scaleArrowTipBottom.clone().project(camera)
    const ndcT = scaleArrowTipTop.clone().project(camera)
    const arrowBottomX = (ndcB.x + 1) * 0.5 * cw
    const arrowBottomY = (1 - ndcB.y) * 0.5 * ch
    const arrowTopX = (ndcT.x + 1) * 0.5 * cw
    const arrowTopY = (1 - ndcT.y) * 0.5 * ch
    ;(window as any).__arrowScreenPos = {
      bottomX: arrowBottomX, bottomY: arrowBottomY,
      topX: arrowTopX, topY: arrowTopY,
    }
  }

  // Easter-egg hover glow / outline lerps. Both Greenland and NJ are
  // only interactive during the intro spinning phase.
  const interactive = props.greenlandHoverable && phase === 'spinning'
  const lerpRate = Math.min(1, dt * 8)

  if (greenlandGlow && greenlandOutline) {
    hoverTargetOpacity = (interactive && isHoveringGreenland) ? 1 : 0
    const gMat = greenlandGlow.material as THREE.MeshBasicMaterial
    const oMat = greenlandOutline.material as THREE.ShaderMaterial
    gMat.opacity += (hoverTargetOpacity * 0.85 - gMat.opacity) * lerpRate
    oMat.uniforms.uOpacity.value +=
      (hoverTargetOpacity * 0.95 - oMat.uniforms.uOpacity.value) * lerpRate
  }
  if (njGlow && njOutline) {
    njHoverOpacity += ((interactive && isHoveringNJ ? 1 : 0) - njHoverOpacity) * lerpRate
    const gMat = njGlow.material as THREE.MeshBasicMaterial
    const oMat = njOutline.material as THREE.ShaderMaterial
    gMat.opacity = njHoverOpacity * 0.95
    oMat.uniforms.uOpacity.value = njHoverOpacity * 1.0
    if (njMesh) njMesh.visible = interactive  // skip raycaster work otherwise
  }

  // Length-scale arrows fade in/out based on showArrows prop.
  if (arrowsGroup) {
    const target = props.showArrows ? 1 : 0
    arrowsCurrentOpacity += (target - arrowsCurrentOpacity) * Math.min(1, dt * 4)
    for (const m of arrowMaterials) {
      m.opacity = arrowsCurrentOpacity
    }
    arrowsGroup.visible = arrowsCurrentOpacity > 0.01
  }

  if (cameraMode === 'user') {
    // User is driving — phase machine is paused. Just damp the controls
    // and render. Phase will resume when the user releases + idle timer
    // fires + return-lerp completes.
    if (controls) controls.update()
    updateFeaturedLakes(time, dt)
    renderer.render(scene, camera)
    renderSimTwin()
    return
  }

  if (cameraMode === 'returning') {
    // Lerp camera from the user's last view back to whatever scripted
    // state would put it at right now (which is the same state as when
    // they grabbed — phase machine froze through user + returning).
    if (controls) controls.update()
    if (returnLerp) {
      const t = Math.min((time - returnLerp.start) / RETURN_LERP_MS, 1)
      const e = easeInOutCubic(t)

      const r = GLOBE_RADIUS * currentDistance
      const scriptedPos = new THREE.Vector3(
        r * Math.cos(currentLat) * Math.cos(currentLon),
        r * Math.cos(currentLat) * Math.sin(currentLon),
        r * Math.sin(currentLat),
      )
      const scriptedTarget = new THREE.Vector3(focal[0], focal[1], focal[2])
      const scriptedUp = new THREE.Vector3(cameraUp[0], cameraUp[1], cameraUp[2])

      camera.position.lerpVectors(returnLerp.posFrom, scriptedPos, e)
      if (controls) {
        controls.target.lerpVectors(returnLerp.targetFrom, scriptedTarget, e)
      }
      camera.up.copy(returnLerp.upFrom).lerp(scriptedUp, e)
      camera.lookAt(controls ? controls.target : scriptedTarget)

      if (t >= 1) {
        cameraMode = 'scripted'
        returnLerp = null
      }
    }
    updateFeaturedLakes(time, dt)
    renderer.render(scene, camera)
    renderSimTwin()
    return
  }

  // cameraMode === 'scripted' from here on.
  if (props.clicks >= 1 && phase === 'spinning') {
    phase = 'opening'
    openStart = time
    openStartLat = currentLat
    openStartLon = currentLon
    openStartDist = currentDistance
    openStartUp = [cameraUp[0], cameraUp[1], cameraUp[2]]
  }
  if (props.clicks >= 2 && phase === 'opened') {
    if (props.stripVelocity) {
      // Deep link straight into the fly-along: skip the paint entirely.
      phase = 'stripped'
      if (basemap) (basemap.material as THREE.MeshBasicMaterial).opacity = 1
      flowOpacity = 0
    } else {
      phase = 'streaming'
      streamStart = time
      // Resume from wherever an interrupted strip left the paint.
      streamFrom = flowOpacity
    }
  }

  if (phase === 'spinning') {
    // Pause the spin while the user is hovering ANY easter-egg hotspot
    // (Greenland, NJ → Princeton, future eggs). Otherwise the target
    // slides across the screen and becomes impossible to click.
    if (!isHoveringGreenland && !isHoveringNJ) {
      currentLon += SPIN_RATE * dt
    }
  } else if (phase === 'opening') {
    // Combined motion: zoom-in, globe fade, basemap reveal, DEM rise,
    // tilt to SE oblique with radial-out up vector — all on overlapping
    // sub-windows of the same eased timeline. The OUTER ease drives
    // camera position; using easeOutCubic (fast start, slow end) makes
    // the click feel snappy — the camera leaves the spinning hub
    // immediately rather than crawling away over the first half-second.
    const t = Math.min((time - openStart) / OPENING_MS, 1)
    const eOuter = easeOutCubic(t)

    // Camera lat/lon/dist + focal lerp over the FULL window.
    currentLat = openStartLat + (ELEV_CAM_LAT - openStartLat) * eOuter
    let dLon = ELEV_CAM_LON - openStartLon
    while (dLon > Math.PI) dLon -= 2 * Math.PI
    while (dLon < -Math.PI) dLon += 2 * Math.PI
    currentLon = openStartLon + dLon * eOuter
    currentDistance = openStartDist + (ELEV_CAM_DIST - openStartDist) * eOuter
    focal = [
      GREENLAND_FOCAL[0] * eOuter,
      GREENLAND_FOCAL[1] * eOuter,
      GREENLAND_FOCAL[2] * eOuter,
    ]

    // Up-vector lerp — held world-Z early, swings to radial-out from
    // 40%-100% so the elevation profile reads vertically as DEM rises.
    const tu = Math.max(0, Math.min(1, (t - 0.4) / 0.6))
    const eu = easeInOutCubic(tu)
    cameraUp = [
      openStartUp[0] + (GREENLAND_RADIAL_OUT[0] - openStartUp[0]) * eu,
      openStartUp[1] + (GREENLAND_RADIAL_OUT[1] - openStartUp[1]) * eu,
      openStartUp[2] + (GREENLAND_RADIAL_OUT[2] - openStartUp[2]) * eu,
    ]

    // Basemap fades in from 35%-75% — Greenland reveals as snow as we close in.
    const tb = Math.max(0, Math.min(1, (t - 0.35) / 0.4))
    const bmat = basemap.material as THREE.MeshBasicMaterial
    bmat.opacity = smoothstep(tb, 0, 1)

    // Globe fades to black from 50%-90% — once Greenland is visible, the
    // rest of Earth dims away to focus the viewer on the ice sheet.
    const tg = Math.max(0, Math.min(1, (t - 0.5) / 0.4))
    const gmat = globe.material as THREE.MeshBasicMaterial
    const k = 1 - easeInOutCubic(tg)
    gmat.color.setRGB(k, k, k)

    // DEM exaggeration ramps over 55%-100% — the ice mound rises last,
    // after the camera has settled into its oblique angle. Hillshade
    // intensity tracks elevation: zero on the un-displaced sphere, full
    // strength once the ice mound is at target height. Writes to the
    // shared `currentExag` reactive so overlays (lake polygons,
    // streamline tube) that hug the surface see the same value.
    const td = Math.max(0, Math.min(1, (t - 0.55) / 0.45))
    const ed = easeInOutCubic(td)
    currentExag = TARGET_EXAGGERATION * ed
    for (const s of elevatedShaders) {
      if (s.uniforms.uExaggeration) s.uniforms.uExaggeration.value = currentExag
      if (s.uniforms.uHillshadeStrength) s.uniforms.uHillshadeStrength.value = ed
    }

    // View offset (Greenland shifts off-center) ramps over 35%-100% so
    // the leftward slide is ALL part of the same combined zoom motion —
    // not a separate adjustment after settling.
    const ts = Math.max(0, Math.min(1, (t - 0.35) / 0.65))
    currentViewShift = TARGET_VIEW_SHIFT * easeInOutCubic(ts)

    if (t >= 1) phase = 'opened'
  } else if (phase === 'streaming') {
    // The speed drape + comet trails fade in OVER the satellite basemap,
    // which stays on underneath: the drape is masked to the ice, so rock
    // and tundra keep their imagery (NASA SVS 3848 does the same).
    const t = Math.min((time - streamStart) / STREAM_FADEIN_MS, 1)
    const v = streamFrom + (1 - streamFrom) * easeOutCubic(t)
    ;(basemap.material as THREE.MeshBasicMaterial).opacity = 1
    flowOpacity = v
    if (t >= 1) phase = 'streamed'
  } else if (phase === 'unstreaming') {
    // The mirror of 'streaming' (Intro fly-along): paint + trails fade
    // out to the satellite basemap, then hold in 'stripped'.
    const t = Math.min((time - unstreamStart) / UNSTREAM_MS, 1)
    const v = unstreamFrom * (1 - easeInOutCubic(t))
    ;(basemap.material as THREE.MeshBasicMaterial).opacity = 1
    flowOpacity = v
    if (t >= 1) phase = 'stripped'
  }

  // Apply camera-tilt lerp (set by `cameraTilt` prop watcher).
  // Drives currentLat from latFrom → latTo over CAMERA_TILT_MS,
  // overriding whichever phase-controlled lat was just computed —
  // sections own the tilt while they're active.
  if (tiltLerp) {
    const t = (time - tiltLerp.tStart) / CAMERA_TILT_MS
    if (t >= 1) {
      currentLat = tiltLerp.latTo
      tiltLerp = null
    } else {
      const e = easeInOutCubic(t)
      currentLat = tiltLerp.latFrom + (tiltLerp.latTo - tiltLerp.latFrom) * e
    }
  }

  // Apply chapter-focus lerp (set by `chapterFocus` prop watcher).
  // Drives focal + lat + lon + distance simultaneously. Direction
  // depends on whether we're entering a chapter (lerp toward target)
  // or returning (lerp back to saved menu state). Wins over tiltLerp
  // and phase logic while running.
  if (chapterLerp) {
    const o = chapterLerp.orbit
    if (o) {
      o.elapsed += Math.min(ORBIT_MAX_STEP_MS, Math.max(0, time - o.last))
      o.last = time
    }
    const t = o ? o.elapsed / chapterLerp.durationMs : (time - chapterLerp.tStart) / chapterLerp.durationMs
    if (t >= 1) {
      finishChapterLerp()
    } else if (o) {
      const e = easeInOutCubic(t)
      applyOrbitFlight(o, e)
      const ux = chapterLerp.upFrom[0] + (chapterLerp.upTo[0] - chapterLerp.upFrom[0]) * e
      const uy = chapterLerp.upFrom[1] + (chapterLerp.upTo[1] - chapterLerp.upFrom[1]) * e
      const uz = chapterLerp.upFrom[2] + (chapterLerp.upTo[2] - chapterLerp.upFrom[2]) * e
      const un = Math.hypot(ux, uy, uz) || 1
      cameraUp = [ux / un, uy / un, uz / un]
      camera.updateProjectionMatrix()
    } else {
      const e = easeInOutCubic(t)
      focal = [
        chapterLerp.focalFrom[0] + (chapterLerp.focalTo[0] - chapterLerp.focalFrom[0]) * e,
        chapterLerp.focalFrom[1] + (chapterLerp.focalTo[1] - chapterLerp.focalFrom[1]) * e,
        chapterLerp.focalFrom[2] + (chapterLerp.focalTo[2] - chapterLerp.focalFrom[2]) * e,
      ]
      currentLat = chapterLerp.latFrom + (chapterLerp.latTo - chapterLerp.latFrom) * e
      currentLon = chapterLerp.lonFrom + (chapterLerp.lonTo - chapterLerp.lonFrom) * e
      currentDistance = chapterLerp.distFrom + (chapterLerp.distTo - chapterLerp.distFrom) * e
      camera.fov = chapterLerp.fovFrom + (chapterLerp.fovTo - chapterLerp.fovFrom) * e
      // Small-angle up-vector blend (the seam dolly rolls the camera to
      // the fracture's radial so the slab lands upright in the panel's
      // field rect).
      const ux = chapterLerp.upFrom[0] + (chapterLerp.upTo[0] - chapterLerp.upFrom[0]) * e
      const uy = chapterLerp.upFrom[1] + (chapterLerp.upTo[1] - chapterLerp.upFrom[1]) * e
      const uz = chapterLerp.upFrom[2] + (chapterLerp.upTo[2] - chapterLerp.upFrom[2]) * e
      const un = Math.hypot(ux, uy, uz) || 1
      cameraUp = [ux / un, uy / un, uz / un]
      camera.updateProjectionMatrix()
    }
  }

  // Apply chapter-cut lerp (uChapterCutSinLat). Beat 2's "knife slide":
  // value walks from -2 (no cut) up to sin(lake_lat), so the south side
  // of the basemap progressively collapses, exposing the slab.
  if (chapterCutLerp) {
    const t = (time - chapterCutLerp.tStart) / CHAPTER_CUT_MS
    const v = t >= 1
      ? chapterCutLerp.to
      : chapterCutLerp.from + (chapterCutLerp.to - chapterCutLerp.from) * easeInOutCubic(t)
    for (const s of elevatedShaders) {
      if (s.uniforms.uChapterCutSinLat) s.uniforms.uChapterCutSinLat.value = v
    }
    if (t >= 1) chapterCutLerp = null
  }

  // Apply chapter-slab idealize lerp (uIdealize). Beat 2 → Beat 3:
  // value walks 0 → 1, morphing the textured bed/surface curves toward
  // flat parallel lines (the canonical Elmer/Ice domain).
  if (chapterIdealizeLerp && chapterSlabMat) {
    const t = (time - chapterIdealizeLerp.tStart) / CHAPTER_IDEALIZE_MS
    const v = t >= 1
      ? chapterIdealizeLerp.to
      : chapterIdealizeLerp.from + (chapterIdealizeLerp.to - chapterIdealizeLerp.from) * easeInOutCubic(t)
    chapterSlabMat.uniforms.uIdealize.value = v
    if (t >= 1) chapterIdealizeLerp = null
  }

  // Apply chapter-exag lerp. Walks currentExag from its current value
  // toward the chapter's requested exaggeration (typically 10× = 0.0028
  // when a chapter enters; back to TARGET_EXAGGERATION = 90× when the
  // chapter clears). All elevated shaders + every surface-hugging
  // overlay (lakes, streamline tube, cross-section ribbon) re-derive
  // their positions from this single value each frame.
  if (chapterExagLerp) {
    const t = (time - chapterExagLerp.tStart) / chapterExagLerp.durationMs
    currentExag = t >= 1
      ? chapterExagLerp.to
      : chapterExagLerp.from + (chapterExagLerp.to - chapterExagLerp.from) * easeInOutCubic(t)
    for (const s of elevatedShaders) {
      if (s.uniforms.uExaggeration) s.uniforms.uExaggeration.value = currentExag
    }
    // Overlays whose vertex positions bake in the exag factor (lake
    // polygons, streamline tube) rebuild their geometries from the
    // cached source data each lerp tick. Cheap — each mesh is at most
    // ~200 vertices.
    if (lakePolyData) buildLakePolyGeometries()
    if (featuredData) buildFeaturedGroups()
    if (streamHiPolyline) buildStreamHiTube()
    if (t >= 1) chapterExagLerp = null
  }

  // Hillshade override (Intro fly-along): lerp uHillshadeStrength on
  // every elevated shader toward the prop's target.
  if (hillshadeLerp) {
    const t = (time - hillshadeLerp.tStart) / HILLSHADE_MS
    const v = t >= 1
      ? hillshadeLerp.to
      : hillshadeLerp.from + (hillshadeLerp.to - hillshadeLerp.from) * easeInOutCubic(t)
    for (const s of elevatedShaders) {
      if (s.uniforms.uHillshadeStrength) s.uniforms.uHillshadeStrength.value = v
    }
    if (t >= 1) hillshadeLerp = null
  }

  // The chapter slab's vertical scale tracks the LIVE DEM exaggeration
  // every frame — the old fixed TARGET_EXAGGERATION bake made the
  // cross-section ~1.8× taller than the 50×-exag dome it kisses
  // (the director noticed the cross-section standing far taller than the DEM).
  if (chapterSlabMat) {
    chapterSlabMat.uniforms.uWorldPerM.value = currentExag / SURF_MAX_M
  }

  // The stage fit (the menu's) eases toward on / off; applyViewOffset
  // reads its progress.
  if (props.stageFit) stageFitSpec = props.stageFit
  const stageFitWant = props.stageFit ? 1 : 0
  const stageFitCarried = chapterLerp?.orbit?.fit != null
  const stageFitHeld = !props.stageFit && !!props.stageFitHold && !chapterLerp
  if (!stageFitCarried && !stageFitHeld && stageFitT !== stageFitWant) {
    const step = Math.min(0.25, (dt * 1000) / STAGE_FIT_MS)
    stageFitT = stageFitWant > stageFitT ? Math.min(1, stageFitT + step) : Math.max(0, stageFitT - step)
  }

  applyCamera()
  updateFeaturedLakes(time, dt)
  applyFieldworkOpacity(time)
  publishFieldworkScreen()
  // Keep the OrbitControls target in sync with the scripted focal so
  // when the user starts dragging, the orbit pivot is correct. Rotate
  // speed scales with fov — at the Ch.2 drain telephoto (2°) the
  // default speed whips the whole frame across in a few pixels of
  // drag.
  if (controls) {
    controls.target.set(focal[0], focal[1], focal[2])
    // Orbiting the sim-domain block: the target is the block itself,
    // so screen motion doesn't scale with fov — a moderate fixed
    // speed feels right. Elsewhere, telephoto framings still damp the
    // rotate speed so a drag can't whip the whole frame.
    controls.rotateSpeed = simTileMesh
      ? 0.35
      : 0.6 * Math.min(1, Math.max(0.15, camera.fov / 40))
    // Inspecting the domain block: near-FULL polar freedom —
    // the earlier black-outs were polygonOffset's slope term exploding
    // at grazing incidence, and applySimDomain now drops the offset
    // once the greenland object is carved away. Only the exact poles
    // stay clamped (lookAt degenerates on the up axis).
    controls.minPolarAngle = simTileMesh ? 0.05 : 0
    controls.maxPolarAngle = simTileMesh ? Math.PI - 0.05 : Math.PI
  }
  // Screen anchor for the Ch.2 model buttons hovering over the domain
  // block (Explore reads it per-frame, like __featuredLakeScreens).
  if (simTileMesh && simAnchorDirs.length > 0) {
    const lift = GLOBE_RADIUS + (simAnchorElevM / SURF_MAX_M) * currentExag
    let cx = 0
    let cy = 0
    let topY = Infinity
    let ok = true
    let minX = Infinity
    let maxX = -Infinity
    let maxY = -Infinity
    let minY = Infinity
    const v = new THREE.Vector3()
    // The four surface corners on screen (c0…c3, build_sim_domains.py
    // order) — Chapter 2's HTML ICE FLOW arrow and the stress
    // key read the block's upper-left edge from them (Ch2FlowArrow.vue).
    const corners: { x: number; y: number }[] = []
    for (let i = 0; i < simAnchorDirs.length; i++) {
      v.copy(simAnchorDirs[i]).multiplyScalar(lift).project(camera)
      if (v.z > 1) ok = false
      const sx = (v.x * 0.5 + 0.5) * window.innerWidth
      const sy = (-v.y * 0.5 + 0.5) * window.innerHeight
      if (i === 0) {
        cx = sx
        cy = sy
      } else corners.push({ x: sx, y: sy })
      topY = Math.min(topY, sy)
      minX = Math.min(minX, sx)
      maxX = Math.max(maxX, sx)
      minY = Math.min(minY, sy)
      maxY = Math.max(maxY, sy)
    }
    // spread = projected footprint size [px] — the model buttons hold
    // off until the block is actually the subject (the zoom settled),
    // not a speck mid-dive.
    const spread = Math.max(maxX - minX, maxY - minY)
    // The bbox of the WHOLE prism (bed corners too) plus the
    // ice-flow tag — render_bed_thumbs.mjs crops the card frames to it.
    if (simEdgeSamples.length === 4) {
      for (let e = 0; e < 4; e++) {
        const q = simEdgeSamples[e][0]
        v.copy(simAnchorDirs[e + 1])
          .multiplyScalar(GLOBE_RADIUS + (q.bedM / SURF_MAX_M) * currentExag)
          .project(camera)
        const sx = (v.x * 0.5 + 0.5) * window.innerWidth
        const sy = (-v.y * 0.5 + 0.5) * window.innerHeight
        minX = Math.min(minX, sx)
        maxX = Math.max(maxX, sx)
        minY = Math.min(minY, sy)
        maxY = Math.max(maxY, sy)
      }
    }
    const labelPos = simFlowGroup?.visible ? (simFlowGroup.userData.labelPos as THREE.Vector3 | undefined) : undefined
    if (labelPos) {
      v.copy(labelPos).project(camera)
      const sx = (v.x * 0.5 + 0.5) * window.innerWidth
      const sy = (-v.y * 0.5 + 0.5) * window.innerHeight
      minX = Math.min(minX, sx)
      maxX = Math.max(maxX, sx)
      minY = Math.min(minY, sy)
      maxY = Math.max(maxY, sy)
    }
    // The ICE FLOW arrow's highest screen point (it hangs
    // upstream of the block now; the tier row above the block clears it).
    // Chapter 2's arrow is now an HTML overlay (the director wanted the
    // ice flow arrow near the mini map, just above the top-left
    // edge of the simulation domain) — Ch2FlowArrow publishes its rect.
    let flowTopY = Infinity
    if (props.simDomain?.flowOverlay) {
      const r = (window as any).__simFlowArrowRect as { top: number; height: number } | null | undefined
      if (r && r.height > 0) flowTopY = r.top
    }
    const ends = simFlowGroup?.visible ? (simFlowGroup.userData.ends as THREE.Vector3[] | undefined) : undefined
    if (ends) {
      for (const e of ends) {
        v.copy(e).project(camera)
        flowTopY = Math.min(flowTopY, (-v.y * 0.5 + 0.5) * window.innerHeight)
      }
      // The ICE FLOW tag hangs a SCREEN distance under the
      // arrow's lowest point — the old world-up offset collapsed on steep
      // views (the bed beat), where the arrowhead touched the "I".
      const flowLbl = simFlowGroup!.userData.label as THREE.Sprite | undefined
      if (flowLbl) {
        const camUp = simFlowCamUp.setFromMatrixColumn(camera.matrixWorld, 1).normalize()
        const L = ends[0].distanceTo(ends[1])
        const hv = Math.abs(simFlowTmp.copy(ends[1]).sub(ends[0]).dot(camUp)) / 2
        flowLbl.position
          .copy(simFlowGroup!.userData.labelPos as THREE.Vector3)
          .addScaledVector(camUp, -(hv + 0.27 * L))
      }
    }
    // The block's pills (spread-gated) wait for the LANDING — carve
    // done, camera and exaggeration settled — instead of popping in
    // mid-dive once the footprint passes their size threshold.
    const landedNow =
      (props.simDomain?.carveT ?? 0) >= 0.999 && chapterLerp === null && chapterExagLerp === null
    // The axis triad's screen box (null while it is off): its anchors
    // plus half a letter sprite of padding.
    let axesBox: { minX: number; minY: number; maxX: number; maxY: number } | null = null
    if (simAxesGroup && simAxesGroup.visible && simAxesGroup.userData.anchors) {
      const half = simAxesGroup.userData.labelHalf as number
      let aMinX = Infinity, aMinY = Infinity, aMaxX = -Infinity, aMaxY = -Infinity
      for (const a of simAxesGroup.userData.anchors as THREE.Vector3[]) {
        v.copy(a).project(camera)
        const ax = (v.x * 0.5 + 0.5) * window.innerWidth
        const ay = (-v.y * 0.5 + 0.5) * window.innerHeight
        // the letter's half-size in px: a world offset of `half` projected
        v.copy(a).addScaledVector(camera.up, half).project(camera)
        const pad = Math.max(10, Math.abs((-v.y * 0.5 + 0.5) * window.innerHeight - ay))
        aMinX = Math.min(aMinX, ax - pad); aMaxX = Math.max(aMaxX, ax + pad)
        aMinY = Math.min(aMinY, ay - pad); aMaxY = Math.max(aMaxY, ay + pad)
      }
      if (Number.isFinite(aMinX)) axesBox = { minX: aMinX, minY: aMinY, maxX: aMaxX, maxY: aMaxY }
    }
    ;(window as any).__simDomainScreen = {
      x: cx,
      y: cy,
      topY,
      flowTopY,
      visible: ok,
      spread: landedNow ? spread : 0,
      rawSpread: spread,
      landed: landedNow,
      bbox: { minX, minY, maxX, maxY },
      axesBox,
      corners,
      // Every edge of the rotated model square is 2·halfKm long [km] —
      // Chapter 2's 5 km scale bar (Ch2FlowArrow) reads px
      // per km off the upper-left edge from this.
      edgeKm: props.simDomain?.halfKm != null ? 2 * props.simDomain.halfKm : null,
      // Screen-space ice-flow direction [deg, atan2(dy, dx), y down]: the
      // inflow wall's midpoint (c3–c0) → the outflow wall's (c1–c2).
      flowDirDeg: corners.length === 4
        ? (Math.atan2(
            (corners[1].y + corners[2].y - corners[3].y - corners[0].y) / 2,
            (corners[1].x + corners[2].x - corners[3].x - corners[0].x) / 2,
          ) * 180) / Math.PI
        : null,
    }
    if (simEdgeGroup && simEdgeExag !== currentExag) buildSimEdges()
    // Per-catalog-lake anchors — tooling + tests target
    // hovers at exact lake centroids.
    if (simLakesData) {
      const out: Record<string, { x: number; y: number }> = {}
      for (const lk of simLakesData) {
        v.copy(lonLatUnit(lk.centroid_ll[0], lk.centroid_ll[1]))
          .multiplyScalar(lift)
          .project(camera)
        out[lk.num] = {
          x: (v.x * 0.5 + 0.5) * window.innerWidth,
          y: (-v.y * 0.5 + 0.5) * window.innerHeight,
        }
      }
      ;(window as any).__simLakeScreens = out
    }
  } else {
    ;(window as any).__simDomainScreen = null
    ;(window as any).__simLakeScreens = null
  }
  // ── The flow arrow lives exactly while the block is landed
  // (carve complete, exaggeration settled); BC overlays ride it. ──
  {
    const d = props.simDomain
    const landed =
      !!simTileMesh && !!d && d.carveT >= 0.999 && chapterExagLerp === null
    if (landed && !simFlowGroup) buildSimFlow(d!)
    else if (!landed && (simFlowGroup || simBcGroup)) {
      disposeSimFlow()
      disposeSimBc()
    }
    tickSimOutline(d ?? null, landed)
    tickSimMarker(d ?? null)
    {
      // BC head-on WALL views: the tile's gold rim would read as the
      // focused boundary's gold, and the triad sits in the profile field
      const f = props.simBc?.on ? props.simBc.focus : null
      const wall = f === 'inflow' || f === 'outflow' || f === 'lat0' || f === 'lat1'
      if (simOutline) simOutline.visible = !wall
      // (AND: tickSimOutline just applied the results beats' axesOff)
      if (simAxesGroup) simAxesGroup.visible = simAxesGroup.visible && !wall
    }
    // Boundary-conditions mode draws the inflow velocity field right where
    // the (upstream) ICE FLOW arrow hangs — and says the same thing; the
    // arrow steps aside while it is on. So it does on the results beats
    // (`axesOff`, with the triad): at 1440 the arrow + its label sat on the
    // stress-space diagram's y-axis ticks and Δσ title.
    // Chapter 2 draws its arrow as an HTML overlay (flowOverlay);
    // the MGSIM page and the bed thumbnails keep this 3D one.
    if (simFlowGroup) {
      simFlowGroup.visible =
        !props.simBc?.on && !props.simDomain?.axesOff && !props.simDomain?.flowOverlay
    }
    // BC mode: the overlay for the wanted (lake,
    // model, focus, exag) appears once the camera has ARRIVED (the
    // director's cue: the cards show up at that point); a stale one fades out.
    const wantKey = landed ? simBcWantedKey() : null
    if (simBcGroup && simBcKey !== wantKey) {
      if (simBcFadeOutT0 === 0) simBcFadeOutT0 = time
      const k = 1 - Math.min(1, (time - simBcFadeOutT0) / 220)
      setBcFade(k * Math.min(1, (time - simBcFadeT0) / SIM_BC_FADE_MS))
      if (k <= 0) {
        disposeSimBc()
        simBcFadeOutT0 = 0
      }
    } else if (!simBcGroup && wantKey && !chapterLerp) {
      buildSimBc(d!)
      simBcFadeOutT0 = 0
    } else if (simBcGroup) {
      setBcFade(Math.min(1, (time - simBcFadeT0) / SIM_BC_FADE_MS))
    }
    if (simBcGroup && simBcKey === wantKey && simBcGroup.userData.hover !== (props.simBc?.hover ?? null)) {
      simBcGroup.userData.hover = props.simBc?.hover ?? null
      setBcHover(simBcGroup, simBcGroup.userData.hover)
    }
    const anchors = simBcGroup?.userData.anchors as Record<string, BcAnchor> | undefined
    if (anchors && camera && simBcKey === wantKey) {
      const w = window.innerWidth
      const h = window.innerHeight
      const v = new THREE.Vector3()
      const proj = (pos: THREE.Vector3) => {
        v.copy(pos).project(camera)
        return {
          x: (v.x * 0.5 + 0.5) * w,
          y: (-v.y * 0.5 + 0.5) * h,
          visible: v.z > -1 && v.z < 1,
        }
      }
      const facing = (a: BcAnchor): number =>
        camera.position.clone().sub(a.pos).normalize().dot(a.n)
      const out: Record<string, { x: number; y: number; visible: boolean; face: boolean }> = {}
      for (const key of ['inflow', 'outflow', 'lat0', 'lat1'] as const) {
        const a = anchors[key]
        const face = facing(a) > 0.05
        out[key] = { ...proj(face ? a.pos : a.edge), face }
      }
      out.surface = { ...proj(anchors.surface.pos), face: facing(anchors.surface) > 0 }
      // the bed: its lowest on-screen bottom corner (where the bed meets
      // the two near walls — the corner the eye reads as "underneath")
      let best: { x: number; y: number; visible: boolean } | null = null
      for (const c of simBcGroup!.userData.bedCorners as THREE.Vector3[]) {
        const p = proj(c)
        if (!best || p.y > best.y) best = p
      }
      out.bed = { ...best!, face: facing(anchors.bed) > 0 }
      // looking down through the glassy ice at it: the patch centre
      if (props.simBc?.focus === 'bed') out.bed = { ...proj(anchors.bed.pos), face: true }
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
      for (const c of simBcGroup!.userData.corners as THREE.Vector3[]) {
        const p = proj(c)
        minX = Math.min(minX, p.x)
        maxX = Math.max(maxX, p.x)
        minY = Math.min(minY, p.y)
        maxY = Math.max(maxY, p.y)
      }
      ;(window as any).__simBcScreens = {
        focus: props.simBc?.focus ?? null,
        settled: !chapterLerp,
        box: { minX, minY, maxX, maxY },
        anchors: out,
      }
    } else {
      ;(window as any).__simBcScreens = null
    }
  }
  // Debug HUD update — only when ?debug=cam is on. Cheap to compute
  // and only touches reactive state when the user opts in. Also
  // mirrors the snapshot to window.__camHud so shot-grid can pull it
  // out of the page (canvas.toDataURL doesn't capture HTML overlays,
  // so shot-grid re-renders the HUD on top of each tile).
  if (debugCam.value) {
    const focalR = Math.hypot(focal[0], focal[1], focal[2])
    const focalLat = focalR > 1e-9 ? Math.asin(focal[2] / focalR) : 0
    const focalLon = Math.atan2(focal[1], focal[0])
    const next = {
      latDeg:       (currentLat * 180) / Math.PI,
      lonDeg:       (currentLon * 180) / Math.PI,
      distWorld:    currentDistance,
      distApi:      currentDistance * GLOBE_RADIUS,
      fov:          camera.fov,
      focalLatDeg:  (focalLat * 180) / Math.PI,
      focalLonDeg:  (focalLon * 180) / Math.PI,
    }
    camHud.value = next
    ;(window as any).__camHud = next
  }
  renderer.render(scene, camera)
  renderSimTwin()
}

// Snap the scene to whatever its canonical end-state is for click count
// `n`. Used for backward navigation (Prev button): we don't smoothly
// reverse the animations, we just jump.
function applyClickState(n: number): void {
  // Cancel any user-control state — backward nav should put us straight
  // into 'scripted' mode at the snapped state.
  cameraMode = 'scripted'
  returnLerp = null
  if (userIdleTimerId !== null) {
    window.clearTimeout(userIdleTimerId)
    userIdleTimerId = null
  }

  if (n <= 0) {
    phase = 'spinning'
    currentLat = (24.2 * Math.PI) / 180
    currentDistance = 5.485
    focal = [0, 0, 0]
    cameraUp = [0, 0, 1]
    currentViewShift = 0
    if (basemap) {
      const mat = basemap.material as THREE.MeshBasicMaterial
      mat.opacity = 0
      mat.color.setRGB(1, 1, 1)
    }
    if (globe) {
      const mat = globe.material as THREE.MeshBasicMaterial
      mat.color.setRGB(1, 1, 1)
      mat.opacity = 1
    }
    currentExag = 0
    for (const s of elevatedShaders) {
      if (s.uniforms.uExaggeration) s.uniforms.uExaggeration.value = 0
      if (s.uniforms.uHillshadeStrength) s.uniforms.uHillshadeStrength.value = 0
    }
    flowOpacity = 0
    return
  }

  // Clicks 1, 2 share the same camera (settled SE-oblique elevated view).
  // Differences: clicks=1 = snow basemap, clicks>=2 = speed drape + comet
  // trails over it.
  phase = n === 1 ? 'opened' : 'streamed'
  // A chapter focus owns the camera (the Introduction's "flows" framing,
  // the chapters): the paint snaps, the camera does not — the focus lerp
  // arriving in the same flush flies from where the camera IS. Snapping
  // it to ELEV_CAM first was a visible jump on Introduction → Chapter 1
  // once the flows scene stopped sitting at ELEV_CAM.
  if (!chapterSavedState && !chapterLerp) {
    currentLat = ELEV_CAM_LAT
    currentLon = ELEV_CAM_LON
    currentDistance = ELEV_CAM_DIST
    focal = [GREENLAND_FOCAL[0], GREENLAND_FOCAL[1], GREENLAND_FOCAL[2]]
    cameraUp = [
      GREENLAND_RADIAL_OUT[0],
      GREENLAND_RADIAL_OUT[1],
      GREENLAND_RADIAL_OUT[2],
    ]
  }
  currentViewShift = TARGET_VIEW_SHIFT

  if (globe) {
    ;(globe.material as THREE.MeshBasicMaterial).color.setRGB(0, 0, 0)
  }
  currentExag = TARGET_EXAGGERATION
  for (const s of elevatedShaders) {
    if (s.uniforms.uExaggeration) s.uniforms.uExaggeration.value = TARGET_EXAGGERATION
    if (s.uniforms.uHillshadeStrength) s.uniforms.uHillshadeStrength.value = 1
  }

  if (basemap) (basemap.material as THREE.MeshBasicMaterial).opacity = 1
  if (n >= 2) {
    // Click 2+: speed drape + comet trails over the basemap.
    flowOpacity = 1
  } else {
    // Click 1: satellite basemap only.
    flowOpacity = 0
  }
  if (controls) controls.target.set(focal[0], focal[1], focal[2])
}

watch(
  () => props.clicks,
  (now, prev) => {
    // Forward clicks animate via the phase machine in animate(). Backward
    // clicks snap (the director was happy for backward moves not to be smooth).
    if (now < (prev ?? now)) {
      applyClickState(now)
    } else if (cameraMode !== 'scripted') {
      // Forward click while user is dragging or returning — abort the
      // user-control state so the new transition begins on the next frame.
      cameraMode = 'scripted'
      returnLerp = null
      if (userIdleTimerId !== null) {
        window.clearTimeout(userIdleTimerId)
        userIdleTimerId = null
      }
    }
  }
)

function applyRollback(progress: number): void {
  // `progress` ∈ [0, 1] drives the cut longitude from CUT_LON_INITIAL
  // (no cut, east of Greenland) to CUT_LON_FINAL (central dome). The
  // basemap shaders and the slab shader share the same uCutLon value.
  const cutLon = CUT_LON_INITIAL + (CUT_LON_FINAL - CUT_LON_INITIAL) * progress
  for (const s of elevatedShaders) {
    if (s.uniforms.uCutLon) s.uniforms.uCutLon.value = cutLon
  }
  if (flowMat) flowMat.uniforms.uCutLon.value = cutLon
  if (crossSectionMat) {
    crossSectionMat.uniforms.uCutLon.value = cutLon
    // Slab opacity ramps in over the first 8% of the sweep so it
    // doesn't pop on at t=0 (where it's geometrically off-Greenland
    // anyway, but the ramp-in feels more deliberate).
    crossSectionMat.uniforms.uOpacity.value = Math.min(1, progress * 12)
  }
  // Scale arrow: fade in over the last 12% of the sweep so it appears
  // once the cut reaches the central dome. Indicates the ice column
  // height; the inset zoom window (separate canvas) shows the same
  // height in stacked OWTCs.
  if (scaleArrow && scaleArrowMaterials.length > 0) {
    const arrowOpacity = Math.max(0, Math.min(1, (progress - 0.88) / 0.12))
    scaleArrow.visible = arrowOpacity > 0
    for (const m of scaleArrowMaterials) m.opacity = arrowOpacity
  }
  // USA scale-reference is now an HTML overlay (top-left of the
  // canvas) — its opacity is driven from Explore.vue via the same
  // rollbackProgress prop, no in-scene mesh to update.
}

watch(
  () => props.rollback ?? 0,
  (v) => applyRollback(v),
)

// Camera-tilt lerp: when a section sets/clears `cameraTilt`, animate
// `currentLat` from its current value to the target over CAMERA_TILT_MS.
// Driven by the same `animate()` rAF that handles the spinning globe and
// other camera motions; we just install a small bookkeeping struct
// (`tiltLerp`) and let `applyCamera()` see the lerped lat each frame.
const CAMERA_TILT_MS = 1200
let tiltLerp:
  | {
      latFrom: number
      latTo: number
      tStart: number
    }
  | null = null

function startTiltLerp(targetDeg: number): void {
  // Skip if already at target (within 0.05°).
  const targetRad = (targetDeg * Math.PI) / 180
  if (Math.abs(currentLat - targetRad) < 0.0009) return
  // A chapter flight in progress owns the landing (its framing names the
  // camera latitude; the Introduction's first framing carries its tilt).
  if (chapterLerp) return
  tiltLerp = {
    latFrom: currentLat,
    latTo: targetRad,
    tStart: performance.now(),
  }
}

watch(
  () => props.cameraTilt,
  (v) => {
    const targetDeg =
      v != null && Number.isFinite(v) ? v : (ELEV_CAM_LAT * 180) / Math.PI
    startTiltLerp(targetDeg)
  },
)

// Chapter-focus lerp: pans camera + retargets focal to a chapter's
// requested feature. On clear, lerps BACK to the saved state so the
// menu / motivation views aren't left in chapter framing.
//
// Math: focal is set to the 3D surface position of the geographic
// (lat, lon). Camera position uses the existing currentLat/Lon polar
// coords (relative to globe centre) so the framing stays consistent
// with the rest of the codebase's camera reasoning. The default
// camera placement is at the focal's longitude, slightly oblique
// (latitude lowered ~25° from the focal so the camera sits "south"
// of straight-overhead) — gives a tilted view of the focal area.
let chapterLerp:
  | {
      focalFrom: [number, number, number]
      focalTo: [number, number, number]
      latFrom: number
      latTo: number
      lonFrom: number
      lonTo: number
      distFrom: number
      distTo: number
      fovFrom: number
      fovTo: number
      upFrom: [number, number, number]
      upTo: [number, number, number]
      tStart: number
      durationMs: number
      /** Menu ⇄ section flights only (see orbitFlight). */
      orbit?: OrbitFlight
    }
  | null = null

// ── Menu ⇄ section flight (the director saw the greenland object spin
// wildly on the way into a section) ───────────────────────────────────────
// The plain chapter lerp interpolates the camera's own lat / lon /
// distance linearly while the look-at focal slides in a straight line.
// Between the menu (camera SSE of the object, 1.85 R) and a chapter's
// vantage (e.g. Chapter 2: camera SW of a west-coast focal, 1.2 R) that
// swings the camera AROUND the focal late and fast, at close range: the
// object rolls ~115° in about 0.8 s while it also grows 2–3× and swerves
// across the screen. The orbit flight instead interpolates what the eye
// reads: the focal along its great circle, the camera's heading and
// elevation AS SEEN FROM the focal, the log of its range and the log of
// tan(fov/2) — so the same turn spreads evenly over the whole flight and
// the zoom is one steady push. Endpoints are the same camera exactly.
// Its clock advances at most ORBIT_MAX_STEP_MS per frame, so a main-
// thread stall (the section mounting mid-flight) pauses the flight
// instead of jumping it. It also carries the menu's stage-fit
// magnification in or out on the same eased progress.
type OrbitFlight = {
  fFromDir: THREE.Vector3
  fToDir: THREE.Vector3
  fFromR: number
  fToR: number
  headFrom: number
  headTo: number
  elFrom: number
  elTo: number
  logRangeFrom: number
  logRangeTo: number
  logTanFrom: number
  logTanTo: number
  fit: { from: number; to: number } | null
  elapsed: number
  last: number
}
const ORBIT_MAX_STEP_MS = 40
const _ofE = new THREE.Vector3()
const _ofN = new THREE.Vector3()
const _ofZ = new THREE.Vector3(0, 0, 1)
function orbitFrame(dir: THREE.Vector3): { east: THREE.Vector3; north: THREE.Vector3 } {
  _ofE.crossVectors(_ofZ, dir)
  if (_ofE.lengthSq() < 1e-12) _ofE.set(0, 1, 0)
  _ofE.normalize()
  _ofN.crossVectors(dir, _ofE).normalize()
  return { east: _ofE.clone(), north: _ofN.clone() }
}
function polarToCart(lat: number, lon: number, dist: number): THREE.Vector3 {
  const r = GLOBE_RADIUS * dist
  return new THREE.Vector3(
    r * Math.cos(lat) * Math.cos(lon),
    r * Math.cos(lat) * Math.sin(lon),
    r * Math.sin(lat),
  )
}
/** Camera relative to a focal, in the focal's local frame. */
function orbitPose(f: THREE.Vector3, cam: THREE.Vector3): { head: number; el: number; range: number } {
  const dir = f.clone().normalize()
  const { east, north } = orbitFrame(dir)
  const v = cam.clone().sub(f)
  const range = v.length() || 1e-9
  return {
    head: Math.atan2(v.dot(east), v.dot(north)),
    el: Math.asin(Math.max(-1, Math.min(1, v.dot(dir) / range))),
    range,
  }
}
/** Land a chapter flight on its target framing. A section tilt lerp
 *  (`cameraTilt`) started alongside the flight dies with it: the flight's
 *  explicit framing is the landing — a tilt outliving the flight by a few
 *  frames snapped the camera 3.5° after the menu → Introduction glide
 *  (the director saw the greenland object jump a little). */
function finishChapterLerp(): void {
  if (!chapterLerp) return
  const o = chapterLerp.orbit
  if (o?.fit) {
    stageFitT = o.fit.to > 0.5 ? 1 : 0
    stageFitEOverride = null
  }
  focal = [chapterLerp.focalTo[0], chapterLerp.focalTo[1], chapterLerp.focalTo[2]]
  currentLat = chapterLerp.latTo
  currentLon = chapterLerp.lonTo
  currentDistance = chapterLerp.distTo
  camera.fov = chapterLerp.fovTo
  cameraUp = [chapterLerp.upTo[0], chapterLerp.upTo[1], chapterLerp.upTo[2]]
  camera.updateProjectionMatrix()
  chapterLerp = null
  tiltLerp = null
}
function makeOrbitFlight(
  focalFrom: [number, number, number],
  focalTo: [number, number, number],
  latFrom: number, lonFrom: number, distFrom: number,
  latTo: number, lonTo: number, distTo: number,
  fovFrom: number, fovTo: number,
  fit: { from: number; to: number } | null,
): OrbitFlight {
  const fA = new THREE.Vector3(...focalFrom)
  const fB = new THREE.Vector3(...focalTo)
  const a = orbitPose(fA, polarToCart(latFrom, lonFrom, distFrom))
  const b = orbitPose(fB, polarToCart(latTo, lonTo, distTo))
  let dh = b.head - a.head
  dh = Math.atan2(Math.sin(dh), Math.cos(dh)) // the short way round
  const tanHalf = (deg: number) => Math.tan((deg * Math.PI) / 360)
  return {
    fFromDir: fA.clone().normalize(),
    fToDir: fB.clone().normalize(),
    fFromR: fA.length(),
    fToR: fB.length(),
    headFrom: a.head,
    headTo: a.head + dh,
    elFrom: a.el,
    elTo: b.el,
    logRangeFrom: Math.log(a.range),
    logRangeTo: Math.log(b.range),
    logTanFrom: Math.log(tanHalf(fovFrom)),
    logTanTo: Math.log(tanHalf(fovTo)),
    fit,
    elapsed: 0,
    last: performance.now(),
  }
}
/** Set focal / currentLat / currentLon / currentDistance / fov at eased e. */
function applyOrbitFlight(o: OrbitFlight, e: number): void {
  const lerp = (x: number, y: number) => x + (y - x) * e
  // focal: slerp of the direction, lerp of the radius
  const cosW = Math.max(-1, Math.min(1, o.fFromDir.dot(o.fToDir)))
  const w = Math.acos(cosW)
  let dir: THREE.Vector3
  if (w < 1e-6) dir = o.fToDir.clone()
  else {
    const sw = Math.sin(w)
    dir = o.fFromDir.clone().multiplyScalar(Math.sin((1 - e) * w) / sw)
      .addScaledVector(o.fToDir, Math.sin(e * w) / sw)
      .normalize()
  }
  const f = dir.clone().multiplyScalar(lerp(o.fFromR, o.fToR))
  const { east, north } = orbitFrame(dir)
  const head = lerp(o.headFrom, o.headTo)
  const el = lerp(o.elFrom, o.elTo)
  const range = Math.exp(lerp(o.logRangeFrom, o.logRangeTo))
  const c = f.clone()
    .addScaledVector(north, range * Math.cos(el) * Math.cos(head))
    .addScaledVector(east, range * Math.cos(el) * Math.sin(head))
    .addScaledVector(dir, range * Math.sin(el))
  const cr = c.length()
  focal = [f.x, f.y, f.z]
  currentDistance = cr / GLOBE_RADIUS
  currentLat = Math.asin(c.z / cr)
  currentLon = Math.atan2(c.y, c.x)
  camera.fov = (Math.atan(Math.exp(lerp(o.logTanFrom, o.logTanTo))) * 360) / Math.PI
  if (o.fit) stageFitEOverride = o.fit.from + (o.fit.to - o.fit.from) * e
}

// Snapshot of camera state at the moment a chapter took over, so we
// can lerp back when the chapter clears. Cleared on each successful
// return.
let chapterSavedState:
  | {
      focal: [number, number, number]
      lat: number
      lon: number
      dist: number
      fov: number
    }
  | null = null

// ── Beat 3→4 seam-fit solver ─────────────────────────────────────────────
// Finds (focal lat, focal lon, camera distance, vertical exaggeration)
// such that the chapter slab's ±halfKm window around the fracture
// projects EXACTLY onto the requested screen rect — the theory panel's
// stage-0 field rect, so the panel's field image can fade in over the
// identical-looking slab. Camera polar angles, fov, up-vector and view
// offset are taken as given; damped Newton iteration with a numeric
// Jacobian on a scratch camera. Returns null (caller falls back to the
// explicit framing) if textures/canvas aren't ready or it diverges.
let fitExagActive = false

function solve4(A: number[][], b: number[]): number[] | null {
  const M = A.map((row, i) => [...row, b[i]])
  for (let c = 0; c < 4; c++) {
    let piv = c
    for (let r = c + 1; r < 4; r++) {
      if (Math.abs(M[r][c]) > Math.abs(M[piv][c])) piv = r
    }
    if (Math.abs(M[piv][c]) < 1e-12) return null
    ;[M[c], M[piv]] = [M[piv], M[c]]
    for (let r = 0; r < 4; r++) {
      if (r === c) continue
      const f = M[r][c] / M[c][c]
      for (let k = c; k < 5; k++) M[r][k] -= f * M[c][k]
    }
  }
  return [0, 1, 2, 3].map((i) => M[i][4] / M[i][i])
}

function solveSeamFit(
  fit: { fracTLon: number; halfKm: number; rect: { x: number; y: number; w: number; h: number } },
  camLatDeg: number,
  camLonDeg: number,
  guess: { latDeg: number; lonDeg: number; distWorld: number; fovDeg: number },
): { latDeg: number; lonDeg: number; fovDeg: number; exag: number } | null {
  const fail = (why: string): null => {
    ;(window as any).__seamFit = { fail: why }
    return null
  }
  if (!canvasRef.value || !chapterSlabMat) return fail('no canvas/slab')
  if (!bedReadbackCtx || !demReadbackCtx) return fail('readbacks not ready')
  const w = canvasRef.value.clientWidth
  const h = canvasRef.value.clientHeight
  if (!w || !h) return fail('zero canvas')

  const cutLat = chapterSlabMat.uniforms.uCutLatRad.value as number
  const cutLatDeg = (cutLat * 180) / Math.PI
  // The idealized slab's uniform bed/surface = the slab-CENTER column's
  // values (see the slab fragment shader's lakeBed/lakeSrf); the tilt
  // is leveled out (uLevelT → 1) by the time the fit dolly runs.
  const centerLonDeg = (((CH_SLAB_LON_W + CH_SLAB_LON_E) / 2) * 180) / Math.PI
  const bedM = Math.max(getBedElevAt(centerLonDeg, cutLatDeg), CH_SLAB_ELEV_MIN_M + 30)
  const surfM = getDemElevAt(centerLonDeg, cutLatDeg)
  if (surfM <= bedM + 50) return fail(`degenerate column bed=${bedM} surf=${surfM}`)

  // By fit time the slab is leveled AND unrolled (uLevelT = 1): the
  // window lives on the tangent PLANE at the fracture (see the slab
  // vertex shader's flatPos).
  const fracLon = CH_SLAB_LON_W + fit.fracTLon * (CH_SLAB_LON_E - CH_SLAB_LON_W)
  const up = new THREE.Vector3(
    Math.cos(cutLat) * Math.cos(fracLon),
    Math.cos(cutLat) * Math.sin(fracLon),
    Math.sin(cutLat),
  )
  const east = new THREE.Vector3(-Math.sin(fracLon), Math.cos(fracLon), 0)
  const xw = GLOBE_RADIUS * ((fit.halfKm * 1000) / 6.371e6)

  const want = {
    cx: fit.rect.x + fit.rect.w / 2,
    cy: fit.rect.y + fit.rect.h / 2,
    ww: fit.rect.w,
    hh: fit.rect.h,
  }

  // The camera sits on a fixed polar ray at a fixed distance — it can
  // never get geometrically closer to the slab face than the ray's
  // perpendicular miss distance, so SCALE is solved with the FOV (the
  // camera's "optical zoom"), not the distance.
  const dist = guess.distWorld
  const cam = new THREE.PerspectiveCamera(guess.fovDeg, w / h, 0.001, 100)
  const camLat = (camLatDeg * Math.PI) / 180
  const camLon = (camLonDeg * Math.PI) / 180

  const project = (latF: number, lonF: number, fovDeg: number, exag: number) => {
    cam.aspect = w / h
    cam.fov = fovDeg
    cam.position.set(
      dist * Math.cos(camLat) * Math.cos(camLon),
      dist * Math.cos(camLat) * Math.sin(camLon),
      dist * Math.sin(camLat),
    )
    // The dolly also rolls the camera's up to the fracture radial (see
    // startChapterLerp's upTo) so the flat slab lands upright.
    cam.up.copy(up)
    cam.lookAt(
      GLOBE_RADIUS * Math.cos(latF) * Math.cos(lonF),
      GLOBE_RADIUS * Math.cos(latF) * Math.sin(lonF),
      GLOBE_RADIUS * Math.sin(latF),
    )
    if (currentViewShift > 0.001) {
      cam.setViewOffset(w * (1 + currentViewShift), h, w * currentViewShift, 0, w, h)
    } else {
      cam.clearViewOffset()
    }
    cam.updateProjectionMatrix()
    cam.updateMatrixWorld()
    const wpm = exag / SURF_MAX_M
    const px: number[] = []
    const py: number[] = []
    for (const sx of [-1, 1]) {
      for (const elevM of [surfM, bedM]) {
        const p = up
          .clone()
          .multiplyScalar(GLOBE_RADIUS + elevM * wpm)
          .addScaledVector(east, sx * xw)
          .project(cam)
        px.push((p.x + 1) * 0.5 * w)
        py.push((1 - p.y) * 0.5 * h)
      }
    }
    // corner order: [W-surf, W-bed, E-surf, E-bed]
    return {
      cx: (px[0] + px[1] + px[2] + px[3]) / 4,
      cy: (py[0] + py[1] + py[2] + py[3]) / 4,
      ww: Math.abs((px[2] + px[3]) / 2 - (px[0] + px[1]) / 2),
      hh: Math.abs((py[1] + py[3]) / 2 - (py[0] + py[2]) / 2),
    }
  }

  // Initial exag from matching the window's world aspect to the rect's
  // screen aspect (horizontal world-per-metre on the globe is the
  // constant GLOBE_RADIUS / R_earth).
  const worldW = (GLOBE_RADIUS / 6.371e6) * 2 * fit.halfKm * 1000
  const exag0 = Math.min(
    0.02,
    Math.max(0.002, ((want.hh / want.ww) * worldW * SURF_MAX_M) / (surfM - bedM)),
  )

  const v = [
    (guess.latDeg * Math.PI) / 180,
    (guess.lonDeg * Math.PI) / 180,
    guess.fovDeg,
    exag0,
  ]
  const resid = (vv: number[]): number[] => {
    const p = project(vv[0], vv[1], vv[2], vv[3])
    return [p.cx - want.cx, p.cy - want.cy, p.ww - want.ww, p.hh - want.hh]
  }
  const CLAMP = [0.04, 0.04, 5, 0.004]
  let converged = false
  const trace: string[] = []
  for (let iter = 0; iter < 48; iter++) {
    const r0 = resid(v)
    if (iter < 4) {
      trace.push(`it${iter} r=[${r0.map((x) => x.toFixed(0)).join(',')}] v=[${v.map((x) => x.toFixed(4)).join(',')}]`)
    }
    if (Math.max(...r0.map(Math.abs)) < 0.4) {
      converged = true
      break
    }
    const steps = [1e-4, 1e-4, 0.05, 1e-5]
    const cols: number[][] = []
    for (let j = 0; j < 4; j++) {
      const vj = v.slice()
      vj[j] += steps[j]
      const rj = resid(vj)
      cols.push(rj.map((val, i) => (val - r0[i]) / steps[j]))
    }
    const A = [0, 1, 2, 3].map((i) => [0, 1, 2, 3].map((j) => cols[j][i]))
    const delta = solve4(A, r0.map((x) => -x))
    if (!delta) return fail('singular jacobian')
    for (let j = 0; j < 4; j++) {
      v[j] += Math.max(-CLAMP[j], Math.min(CLAMP[j], delta[j]))
    }
    v[2] = Math.max(0.8, Math.min(45, v[2]))
    v[3] = Math.max(0.0005, Math.min(0.02, v[3]))
  }
  if (!converged) {
    return fail(
      `diverged bed=${bedM.toFixed(0)} surf=${surfM.toFixed(0)} want=[${Object.values(want).map((x) => x.toFixed(0)).join(',')}] ` +
        trace.join(' | '),
    )
  }
  const out = {
    latDeg: (v[0] * 180) / Math.PI,
    lonDeg: (v[1] * 180) / Math.PI,
    fovDeg: v[2],
    exag: v[3],
  }
  ;(window as any).__seamFit = { ...out, residual: resid(v).map((x) => Math.round(x * 10) / 10) }
  return out
}

function startChapterLerp(target: NonNullable<typeof props.chapterFocus>): void {
  // Kill the intro 'opening' phase if it's still running. On a direct
  // deep-link (e.g. /chapter1?beat=2) the 7-second spinning→ELEV_CAM
  // opening animation is mid-flight while the chapter lerp completes
  // in 1.8s; once the chapter lerp ends, the still-running opening
  // phase silently overwrites currentLat/Lon/Dist back to ELEV_CAM
  // every frame, undoing the chapter framing. Snap to 'opened' so
  // chapter framing wins permanently. Cosmetic loss: no establishing
  // shot when deep-linking, which is fine — the chapter is the target.
  if (phase === 'spinning' || phase === 'opening') {
    phase = 'opened'
    focal = [GREENLAND_FOCAL[0], GREENLAND_FOCAL[1], GREENLAND_FOCAL[2]]
    cameraUp = [
      GREENLAND_RADIAL_OUT[0],
      GREENLAND_RADIAL_OUT[1],
      GREENLAND_RADIAL_OUT[2],
    ]
    currentViewShift = TARGET_VIEW_SHIFT
    // ALSO snap the camera polar coords to ELEV_CAM. Without this, the
    // chapter lerp's `latFrom` is whatever the Earth-spinning intro view
    // happens to be (lat 24.2°, lon 0°, distance 5.485 — Earth view from
    // ~5× globe radius). Lerping from there to the chapter target takes
    // 1.8 s, during which the camera is too far away to see Greenland
    // (which is now the only visible thing — Earth globe color was just
    // set to black). Result: black screen for the first ~2 s of any
    // chapter deeplink. Snapping to ELEV_CAM here means the lerp starts
    // with Greenland already in view, so the entry animation feels like
    // a pan-in rather than a "loading…" black.
    currentLat = ELEV_CAM_LAT
    currentLon = ELEV_CAM_LON
    currentDistance = ELEV_CAM_DIST
    if (basemap) {
      const mat = basemap.material as THREE.MeshBasicMaterial
      mat.opacity = 1
    }
    if (globe) {
      ;(globe.material as THREE.MeshBasicMaterial).color.setRGB(0, 0, 0)
    }
    currentExag = TARGET_EXAGGERATION
    for (const s of elevatedShaders) {
      if (s.uniforms.uExaggeration) s.uniforms.uExaggeration.value = TARGET_EXAGGERATION
      if (s.uniforms.uHillshadeStrength) s.uniforms.uHillshadeStrength.value = 1
    }
  }
  // Save the camera state ONCE per chapter session — multiple beat
  // changes inside the same chapter shouldn't repeatedly re-save.
  // Save the menu-ready state (ELEV_CAM) rather than whatever transient
  // value currentLat happens to hold mid-opening-lerp — that way when
  // the user backs out of the chapter, they return to menu framing,
  // not a half-zoomed Earth view.
  // No saved state = the camera is on the menu's framing (the menu, a
  // page without a flight, or a deep link's snap): this is an ENTRY
  // flight — it takes the orbit path (see OrbitFlight).
  const entry = !chapterSavedState
  if (!chapterSavedState) {
    chapterSavedState = {
      focal: [GREENLAND_FOCAL[0], GREENLAND_FOCAL[1], GREENLAND_FOCAL[2]],
      lat: ELEV_CAM_LAT,
      lon: ELEV_CAM_LON,
      dist: ELEV_CAM_DIST,
      fov: camera.fov,
    }
  }

  // Camera polar coords. Defaults: same lon as feature (so the feature
  // is centered on screen), latitude 25° below the feature (oblique
  // angle, "looking at" the feature from the south). cameraLat/Lon
  // overrides are degrees.
  const camLatDeg = target.cameraLat ?? Math.max(20, target.lat - 25)
  const camLonDeg = target.cameraLon ?? target.lon
  const targetCamLat = (camLatDeg * Math.PI) / 180
  const targetCamLon = (camLonDeg * Math.PI) / 180
  let targetFov = target.fovDeg ?? chapterSavedState.fov

  // Seam fit (beat 3→4): solve focal + fov + exag so the slab window
  // lands on the theory panel's field rect; fall back to the explicit
  // framing if the solve isn't possible. A later NON-fit chapter focus
  // restores the prop-driven exaggeration.
  let focalLatDeg = target.lat
  let focalLonDeg = target.lon
  const distWorld = target.distance ?? 0.95
  let upTo: [number, number, number] = [
    GREENLAND_RADIAL_OUT[0],
    GREENLAND_RADIAL_OUT[1],
    GREENLAND_RADIAL_OUT[2],
  ]
  if (target.fit) {
    const solved = solveSeamFit(target.fit, camLatDeg, camLonDeg, {
      latDeg: target.lat,
      lonDeg: target.lon,
      distWorld,
      fovDeg: targetFov,
    })
    if (solved) {
      focalLatDeg = solved.latDeg
      focalLonDeg = solved.lonDeg
      targetFov = solved.fovDeg
      setChapterExagTarget(solved.exag)
      fitExagActive = true
      // Roll the camera upright relative to the slab window (the
      // solver's scratch camera assumed this same up).
      const cutLat = chapterSlabMat
        ? (chapterSlabMat.uniforms.uCutLatRad.value as number)
        : (target.fit ? slabLatRadFromCutLatDeg(target.lat) : 0)
      const fracLon =
        CH_SLAB_LON_W + target.fit.fracTLon * (CH_SLAB_LON_E - CH_SLAB_LON_W)
      upTo = [
        Math.cos(cutLat) * Math.cos(fracLon),
        Math.cos(cutLat) * Math.sin(fracLon),
        Math.sin(cutLat),
      ]
    }
  } else if (fitExagActive) {
    setChapterExagTarget(props.chapterExag ?? TARGET_EXAGGERATION)
    fitExagActive = false
  }

  // Nadir framings (Intro fly-along): screen-up = local north at the
  // focal. The default radial-out up is parallel to the view direction
  // straight down, which would make lookAt degenerate.
  if (target.upNorth) {
    const fl = (focalLatDeg * Math.PI) / 180
    const fo = (focalLonDeg * Math.PI) / 180
    upTo = [-Math.sin(fl) * Math.cos(fo), -Math.sin(fl) * Math.sin(fo), Math.cos(fl)]
  }
  if (target.up) {
    const n = Math.hypot(target.up[0], target.up[1], target.up[2]) || 1
    upTo = [target.up[0] / n, target.up[1] / n, target.up[2] / n]
  }

  // Geographic lat/lon → 3D focal on the sphere surface. Same convention
  // as GREENLAND_FOCAL above (geographic lon stays signed: −49.5°W is
  // a negative number in degrees). focalOnSurface lifts the focal to
  // the displaced ice surface at the TARGET exaggeration.
  const featLat = (focalLatDeg * Math.PI) / 180
  const featLon = (focalLonDeg * Math.PI) / 180
  let focalR = GLOBE_RADIUS
  if (target.focalElevM !== undefined || target.focalOnSurface) {
    const elevM = target.focalElevM ?? getDemElevAt(focalLonDeg, focalLatDeg)
    focalR =
      GLOBE_RADIUS +
      (elevM / SURF_MAX_M) *
        (target.focalExag ?? props.chapterExag ?? TARGET_EXAGGERATION)
  }
  const focalTo: [number, number, number] = [
    focalR * Math.cos(featLat) * Math.cos(featLon),
    focalR * Math.cos(featLat) * Math.sin(featLon),
    focalR * Math.sin(featLat),
  ]

  // Convert chapter API's WORLD distance to currentDistance (the
  // GLOBE_RADIUS multiplier this codebase uses internally).
  const targetDist = distWorld / GLOBE_RADIUS

  settleCarriedStageFit()
  // The stage fit rides an entry flight: from wherever it stands (held at
  // the menu's full fit while the section mounted) out to none.
  const fitNow = stageFitT > 0 ? easeInOutCubic(stageFitT) : 0
  const orbit = entry
    ? makeOrbitFlight(
        [focal[0], focal[1], focal[2]], focalTo,
        currentLat, currentLon, currentDistance,
        targetCamLat, targetCamLon, targetDist,
        camera.fov, targetFov,
        !props.stageFit && fitNow > 0 ? { from: fitNow, to: 0 } : null,
      )
    : undefined
  chapterLerp = {
    focalFrom: [focal[0], focal[1], focal[2]],
    focalTo,
    latFrom: currentLat,
    latTo: targetCamLat,
    lonFrom: currentLon,
    lonTo: targetCamLon,
    distFrom: currentDistance,
    distTo: targetDist,
    fovFrom: camera.fov,
    fovTo: targetFov,
    upFrom: [cameraUp[0], cameraUp[1], cameraUp[2]],
    upTo,
    tStart: performance.now(),
    durationMs: target.durationMs ?? 1500,
    orbit,
  }
  cameraMode = 'scripted'
}

// ───────── fieldwork Sentinel-2 patch (Intro fly-along) ───────────────────
//
// A sphere-hugging rectangle in the fieldwork local-tangent frame
// (config/fieldwork.ts: x east, y south, R = 6378137, cos φ₀ fixed),
// textured with the 10 m Sentinel-2 crop. Built once per url; opacity
// follows the prop (the crossfade over the coarse basemap). Rendered
// with depthTest OFF above everything so it never z-fights the flat
// basemap — which is why it must be faded out before the dome re-
// inflates (it has no DEM displacement of its own).
let fieldworkMesh: THREE.Mesh | null = null
let fieldworkTex: THREE.Texture | null = null
let fieldworkUrl: string | null = null
// The crop's texture arrives asynchronously (a 1.5 MB webp from R2, then
// a 15 Mpx decode + upload). Until it has, the mesh is NOT drawn: a
// MeshBasicMaterial with no map renders its colour, and a white feathered
// plate in the crop's place is exactly the bright flash of white before
// landing on the Sentinel-2 imagery that the director saw live — every
// film had waited for textures, so it never showed there. Arriving late,
// it ramps in over FW_TEX_FADE_MS on top of the choreography's opacity.
let fieldworkTexReadyAt: number | null = null
let fieldworkOpacity = 0
const FW_TEX_FADE_MS = 600
function applyFieldworkOpacity(now: number): void {
  if (!fieldworkMesh) return
  if (fieldworkTexReadyAt === null) {
    fieldworkMesh.visible = false
    return
  }
  const ramp = Math.min(1, (now - fieldworkTexReadyAt) / FW_TEX_FADE_MS)
  const m = fieldworkMesh.material as THREE.MeshBasicMaterial
  m.opacity = fieldworkOpacity * ramp
  fieldworkMesh.visible = m.opacity > 0.001
}
const FW_PATCH_LIFT = 1.00005
const FW_SEG_X = 64
const FW_SEG_Y = 40

function fieldworkLatLon(
  p: NonNullable<typeof props.fieldworkPatch>,
  xm: number,
  ySouthM: number,
): [number, number] {
  const deg = Math.PI / 180
  const lat = p.latC - ySouthM / (p.rEarthM * deg)
  const lon = p.lonC + xm / (p.rEarthM * deg * Math.cos(p.latC * deg))
  return [lat, lon]
}

function fieldworkWorld(p: NonNullable<typeof props.fieldworkPatch>, xm: number, ySouthM: number): THREE.Vector3 {
  const [latD, lonD] = fieldworkLatLon(p, xm, ySouthM)
  const la = (latD * Math.PI) / 180
  const lo = (lonD * Math.PI) / 180
  const r = GLOBE_RADIUS * FW_PATCH_LIFT
  return new THREE.Vector3(r * Math.cos(la) * Math.cos(lo), r * Math.cos(la) * Math.sin(lo), r * Math.sin(la))
}

const FW_FEATHER = 0.12
let fieldworkFeather: THREE.CanvasTexture | null = null
function fieldworkFeatherTex(): THREE.CanvasTexture {
  if (fieldworkFeather) return fieldworkFeather
  const A = 256
  const c = document.createElement('canvas')
  c.width = A
  c.height = A
  const ctx = c.getContext('2d')!
  const img = ctx.createImageData(A, A)
  const band = A * FW_FEATHER
  for (let j = 0; j < A; j++) {
    for (let i = 0; i < A; i++) {
      const fx = Math.min(i, A - 1 - i) / band
      const fy = Math.min(j, A - 1 - j) / band
      const u = Math.max(0, Math.min(1, Math.min(fx, fy)))
      const a = u * u * (3 - 2 * u)
      const k = (j * A + i) * 4
      img.data[k] = img.data[k + 1] = img.data[k + 2] = Math.round(a * 255)
      img.data[k + 3] = 255
    }
  }
  ctx.putImageData(img, 0, 0)
  fieldworkFeather = new THREE.CanvasTexture(c)
  return fieldworkFeather
}

function disposeFieldworkPatch(): void {
  if (fieldworkMesh) {
    scene.remove(fieldworkMesh)
    fieldworkMesh.geometry.dispose()
    ;(fieldworkMesh.material as THREE.Material).dispose()
    fieldworkMesh = null
  }
  fieldworkTexReadyAt = null
  if (fieldworkTex) {
    fieldworkTex.dispose()
    fieldworkTex = null
  }
  fieldworkUrl = null
  ;(window as any).__fieldworkScreen = null
}

function buildFieldworkPatch(p: NonNullable<typeof props.fieldworkPatch>): void {
  disposeFieldworkPatch()
  fieldworkUrl = p.url
  const nx = FW_SEG_X + 1
  const ny = FW_SEG_Y + 1
  const pos = new Float32Array(nx * ny * 3)
  const uv = new Float32Array(nx * ny * 2)
  let k = 0
  for (let j = 0; j < ny; j++) {
    // j = 0 is the SOUTH edge → v = 0 (three.js flipY: v = 0 samples the
    // image's bottom row, which is the crop's south edge).
    const ySouth = p.halfYm - (2 * p.halfYm * j) / FW_SEG_Y
    for (let i = 0; i < nx; i++) {
      const xm = -p.halfXm + (2 * p.halfXm * i) / FW_SEG_X
      const w = fieldworkWorld(p, xm, ySouth)
      pos[k * 3] = w.x
      pos[k * 3 + 1] = w.y
      pos[k * 3 + 2] = w.z
      uv[k * 2] = i / FW_SEG_X
      uv[k * 2 + 1] = j / FW_SEG_Y
      k++
    }
  }
  const idx: number[] = []
  for (let j = 0; j < FW_SEG_Y; j++) {
    for (let i = 0; i < FW_SEG_X; i++) {
      const a = j * nx + i
      const b = a + 1
      const c = a + nx
      const d = c + 1
      idx.push(a, b, d, a, d, c)
    }
  }
  const geom = new THREE.BufferGeometry()
  geom.setAttribute('position', new THREE.BufferAttribute(pos, 3))
  geom.setAttribute('uv', new THREE.BufferAttribute(uv, 2))
  geom.setIndex(idx)
  // Feathered edge: the crop is sharper and cooler than the coarse
  // basemap it crossfades over, and a hard 50 × 30 km rectangle showed
  // mid-dive (seen on film). The alphaMap fades the outer FW_FEATHER
  // of each side; the landing frame sits well inside the opaque core.
  const mat = new THREE.MeshBasicMaterial({
    color: 0xffffff,
    transparent: true,
    opacity: p.opacity,
    depthTest: false,
    depthWrite: false,
    side: THREE.DoubleSide,
    alphaMap: fieldworkFeatherTex(),
  })
  fieldworkMesh = new THREE.Mesh(geom, mat)
  fieldworkMesh.renderOrder = 6
  fieldworkOpacity = p.opacity
  fieldworkMesh.visible = false // until the texture is ready
  fieldworkMesh.frustumCulled = false
  scene.add(fieldworkMesh)
  const url = p.url
  new THREE.TextureLoader().load(url, (tex) => {
    if (fieldworkUrl !== url || !fieldworkMesh) {
      tex.dispose()
      return
    }
    tex.colorSpace = THREE.SRGBColorSpace
    tex.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy())
    tex.generateMipmaps = true
    tex.minFilter = THREE.LinearMipmapLinearFilter
    fieldworkTex = tex
    // Upload to the GPU NOW (15 Mpx + mipmaps ≈ 1.4 s main-thread stall
    // as measured) — the patch is warmed invisibly at step 1, so
    // the fly-along's crossfade never pays it mid-dive.
    renderer.initTexture(tex)
    const m = fieldworkMesh.material as THREE.MeshBasicMaterial
    m.map = tex
    m.needsUpdate = true
    fieldworkTexReadyAt = performance.now()
    applyFieldworkOpacity(fieldworkTexReadyAt)
  }, undefined, (err) => {
    // The patch simply never shows (never a white plate); the flat map
    // has its own fallback. Say so, for the next diagnosis.
    console.warn('[fieldwork] patch texture failed to load:', url.slice(0, 80), err)
  })
}

// Screen positions (CSS px) of three frame reference points — the
// frame origin, 1 km east and 1 km south — so the flat map can solve
// the affine map from its metres to the screen and take over pixel-
// aligned. `settled` = no camera / exag lerp in flight.
function publishFieldworkScreen(): void {
  const p = props.fieldworkPatch
  if (!p || !fieldworkMesh) return
  const w = window.innerWidth
  const h = window.innerHeight
  const proj = (xm: number, ym: number): [number, number] => {
    const v = fieldworkWorld(p, xm, ym).project(camera)
    return [(v.x * 0.5 + 0.5) * w, (-v.y * 0.5 + 0.5) * h]
  }
  const o = proj(0, 0)
  const e = proj(1000, 0)
  const s = proj(0, 1000)
  ;(window as any).__fieldworkScreen = {
    ox: o[0], oy: o[1],
    ex: e[0], ey: e[1],
    sx: s[0], sy: s[1],
    settled: chapterLerp === null && chapterExagLerp === null,
  }
}

// ───────── Ch.3 lake strip (the dynamic Fig. 1 on the main Globe) ────────
//
// Same idea as the fieldwork patch — a surface-hugging quad at the sphere
// radius for the flattened map view — but gridded in lon/lat (the canvas is
// equirectangular over the strip's bbox, like EssdFig1Globes' lakes
// texture was) and textured from a CanvasTexture the section repaints.
let lakeStripMesh: THREE.Mesh | null = null
let lakeStripTex: THREE.CanvasTexture | null = null
let lakeStripCanvas: HTMLCanvasElement | null = null
let lakeStripVersion = -1
const LS_SEG = 96
// `surface` strips: each vertex's direction, lon/lat and surface elevation,
// so the patch rides the displaced ice through exaggeration changes (the
// featured lakes' relay pattern) and re-reads the DEM when it arrives.
let lakeStripSurf: {
  dir: Float32Array
  lonLat: Float32Array
  elevM: Float32Array
  exag: number
} | null = null

function disposeLakeStrip(): void {
  if (lakeStripMesh) {
    scene.remove(lakeStripMesh)
    lakeStripMesh.geometry.dispose()
    ;(lakeStripMesh.material as THREE.Material).dispose()
    lakeStripMesh = null
  }
  if (lakeStripTex) {
    lakeStripTex.dispose()
    lakeStripTex = null
  }
  lakeStripCanvas = null
  lakeStripVersion = -1
  lakeStripSurf = null
}

/** Lay a `surface` strip on the ice at the CURRENT exaggeration; `resample`
 *  re-reads its elevations (the DEM readback has just arrived). */
function relayLakeStrip(resample: boolean): void {
  const s = lakeStripSurf
  if (!s || !lakeStripMesh) return
  const n = s.elevM.length
  if (resample) {
    for (let k = 0; k < n; k++) s.elevM[k] = getDemElevAt(s.lonLat[k * 2], s.lonLat[k * 2 + 1])
  }
  const attr = lakeStripMesh.geometry.getAttribute('position') as THREE.BufferAttribute
  const pos = attr.array as Float32Array
  for (let k = 0; k < n; k++) {
    const r = GLOBE_RADIUS * FW_PATCH_LIFT + (s.elevM[k] / SURF_MAX_M) * currentExag
    pos[k * 3] = s.dir[k * 3] * r
    pos[k * 3 + 1] = s.dir[k * 3 + 1] * r
    pos[k * 3 + 2] = s.dir[k * 3 + 2] * r
  }
  attr.needsUpdate = true
  s.exag = currentExag
}

function buildLakeStrip(p: NonNullable<typeof props.lakeStrip>): void {
  disposeLakeStrip()
  const n = LS_SEG + 1
  const pos = new Float32Array(n * n * 3)
  const uv = new Float32Array(n * n * 2)
  const r = GLOBE_RADIUS * FW_PATCH_LIFT
  const surf = p.surface
    ? { dir: new Float32Array(n * n * 3), lonLat: new Float32Array(n * n * 2), elevM: new Float32Array(n * n), exag: -1 }
    : null
  let k = 0
  for (let j = 0; j < n; j++) {
    // j = 0 is the SOUTH edge → v = 0 (flipY: the canvas's bottom row).
    const lat = p.latS + ((p.latN - p.latS) * j) / LS_SEG
    for (let i = 0; i < n; i++) {
      const lon = p.lonW + ((p.lonE - p.lonW) * i) / LS_SEG
      const v: number[] = [] // lonlatTo3D pushes
      lonlatTo3D(lon, lat, r, v)
      pos[k * 3] = v[0]
      pos[k * 3 + 1] = v[1]
      pos[k * 3 + 2] = v[2]
      uv[k * 2] = i / LS_SEG
      uv[k * 2 + 1] = j / LS_SEG
      if (surf) {
        surf.dir[k * 3] = v[0] / r
        surf.dir[k * 3 + 1] = v[1] / r
        surf.dir[k * 3 + 2] = v[2] / r
        surf.lonLat[k * 2] = lon
        surf.lonLat[k * 2 + 1] = lat
      }
      k++
    }
  }
  const idx: number[] = []
  for (let j = 0; j < LS_SEG; j++) {
    for (let i = 0; i < LS_SEG; i++) {
      const a = j * n + i
      const b = a + 1
      const c = a + n
      const d = c + 1
      idx.push(a, b, d, a, d, c)
    }
  }
  const geom = new THREE.BufferGeometry()
  geom.setAttribute('position', new THREE.BufferAttribute(pos, 3))
  geom.setAttribute('uv', new THREE.BufferAttribute(uv, 2))
  geom.setIndex(idx)
  lakeStripCanvas = p.canvas
  lakeStripTex = new THREE.CanvasTexture(p.canvas)
  lakeStripTex.colorSpace = THREE.SRGBColorSpace
  lakeStripTex.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy())
  // A surface strip is seen oblique and at two zooms: mip-map it. The flat
  // map strip (Chapter 3) keeps its plain filter — it is repainted every
  // season day and drawn near 1:1.
  lakeStripTex.generateMipmaps = !!p.surface
  lakeStripTex.minFilter = p.surface ? THREE.LinearMipmapLinearFilter : THREE.LinearFilter
  const mat = new THREE.MeshBasicMaterial({
    map: lakeStripTex,
    transparent: true,
    opacity: p.opacity,
    depthTest: false,
    depthWrite: false,
    side: THREE.DoubleSide,
  })
  lakeStripMesh = new THREE.Mesh(geom, mat)
  lakeStripMesh.renderOrder = 7
  lakeStripMesh.frustumCulled = false
  scene.add(lakeStripMesh)
  lakeStripVersion = p.version
  lakeStripSurf = surf
  if (surf) relayLakeStrip(true)
}

watch(
  () => props.lakeStrip,
  (v) => {
    if (!v) {
      disposeLakeStrip()
      return
    }
    if (!lakeStripMesh || lakeStripCanvas !== v.canvas) buildLakeStrip(v)
    if (lakeStripMesh) {
      ;(lakeStripMesh.material as THREE.MeshBasicMaterial).opacity = v.opacity
      lakeStripMesh.visible = v.opacity > 0.002
    }
    if (lakeStripTex && v.version !== lakeStripVersion) {
      lakeStripTex.needsUpdate = true
      lakeStripVersion = v.version
    }
  },
  { deep: true },
)

watch(
  () => props.fieldworkPatch,
  (v) => {
    if (!v) {
      disposeFieldworkPatch()
      return
    }
    if (!fieldworkMesh || fieldworkUrl !== v.url) buildFieldworkPatch(v)
    fieldworkOpacity = v.opacity
    applyFieldworkOpacity(performance.now())
  },
  { deep: true },
)

watch(
  () => props.stripVelocity,
  (strip) => {
    if (strip) {
      if (phase === 'streamed' || phase === 'streaming') {
        phase = 'unstreaming'
        unstreamStart = performance.now()
        unstreamFrom = flowOpacity
      }
      // 'opened'/'opening'/'spinning': the animate() gate routes clicks≥2
      // straight to 'stripped' while the prop is true.
    } else if (phase === 'unstreaming' || phase === 'stripped') {
      // Back to 'opened': the animate() gate re-streams on the next
      // frame when clicks is still 2.
      phase = 'opened'
    }
  },
)

watch(
  () => props.hillshade,
  (v) => {
    const to = v != null && Number.isFinite(v) ? Math.max(0, Math.min(1, v)) : 1
    const from = (elevatedShaders[0]?.uniforms.uHillshadeStrength?.value as number | undefined) ?? 1
    hillshadeLerp = { from, to, tStart: performance.now() }
  },
)

// ───────── lake overlay (Ch.1+ chapter marker) ──────────
//
// Flat circular disc tangent to the sphere at a given (lat, lon),
// with its surface normal pointing radially outward. Renders just
// above the basemap so it's not z-fought-out by the basemap fragment
// shader. radiusKm is exaggerated for narrative visibility — North
// Lake's true ~1 km radius would be sub-pixel at any reasonable zoom.
const EARTH_RADIUS_KM = 6371

let lakeOverlayMesh: THREE.Mesh | null = null

function disposeLakeOverlay(): void {
  if (!lakeOverlayMesh) return
  scene.remove(lakeOverlayMesh)
  lakeOverlayMesh.geometry.dispose()
  ;(lakeOverlayMesh.material as THREE.Material).dispose()
  lakeOverlayMesh = null
}

function applyLakeOverlay(o: NonNullable<typeof props.lakeOverlay>): void {
  // World-coords surface position at (lat, lon).
  const latRad = (o.lat * Math.PI) / 180
  const lonRad = (o.lon * Math.PI) / 180
  const ox = GLOBE_RADIUS * Math.cos(latRad) * Math.cos(lonRad)
  const oy = GLOBE_RADIUS * Math.cos(latRad) * Math.sin(lonRad)
  const oz = GLOBE_RADIUS * Math.sin(latRad)
  const outward = new THREE.Vector3(ox, oy, oz).normalize()

  const radiusKm = o.radiusKm ?? 500
  const radiusWorld = (radiusKm / EARTH_RADIUS_KM) * GLOBE_RADIUS

  // Rebuild geometry/material if size or color changed; otherwise
  // just update transform.
  disposeLakeOverlay()
  const geom = new THREE.CircleGeometry(radiusWorld, 64)
  const mat = new THREE.MeshBasicMaterial({
    color: new THREE.Color(o.color ?? '#4a9eff'),
    transparent: true,
    opacity: o.opacity ?? 0.85,
    depthWrite: false,
    side: THREE.DoubleSide,
  })
  lakeOverlayMesh = new THREE.Mesh(geom, mat)
  // Position above the *elevated* DEM (which can push the visible
  // surface up by ~3% at high-elevation interior). Need more lift than
  // a basemap-only z-fight buffer to avoid being clipped by the ice
  // dome.
  const lift = GLOBE_RADIUS * 1.025
  lakeOverlayMesh.position.set(outward.x * lift, outward.y * lift, outward.z * lift)
  // Orient so disc normal = outward direction (CircleGeometry's default
  // normal is +Z).
  lakeOverlayMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), outward)
  // Render after basemap (renderOrder default 0).
  lakeOverlayMesh.renderOrder = 4
  scene.add(lakeOverlayMesh)
}

watch(
  () => props.lakeOverlay,
  (v) => {
    if (v) applyLakeOverlay(v)
    else disposeLakeOverlay()
  },
)

// ───────── Ch.1 bulk lake-polygons overlay ──────────
//
// Renders ALL CW (or whatever region) lake outlines fetched from the
// JSON at `dataUrl`, lifted slightly above the elevated DEM so they
// read on top of the snow basemap. Beats 1 + 2 use this to flash the
// catchment-wide lakes (Beat 1) and then highlight North Lake among
// them (Beat 2). Each polygon is a closed THREE.LineLoop — batched
// into TWO line-segments meshes for performance: one for the "base"
// lakes (everything except the highlight) and one for the "highlight"
// lake (rendered with a brighter color on top). Materials are reused
// across opacity changes; geometry is only rebuilt when the dataset
// itself or the highlight target changes.

type LakePoly = {
  id: string
  lon: number
  lat: number
  ring: number[][]
  // featured_lakes.json extras (absent in the bulk CW polygons file)
  color?: string
  name?: string
  class?: string
}

// Filled triangle-fan meshes (one per lake, batched into two combined
// meshes — "base" for the bulk and "highlight" for the one highlighted
// lake). Triangle-fan-from-centroid is good enough for lake outlines
// which are mostly convex blobs; we don't bother with ear-clipping.
// Lines (LineBasicMaterial) were too thin to read at chapter framing
// distance, so we use fills.
let lakePolyBaseMesh:               THREE.Mesh | null = null
let lakePolyBaseMat:                THREE.MeshBasicMaterial | null = null
// Highlight is rendered as three coordinated meshes — see
// buildLakePolyGeometries() comment block for the visual design.
let lakePolyHighlightFillMesh:      THREE.Mesh | null = null  // deep-blue lake at real size
let lakePolyHighlightFillMat:       THREE.MeshBasicMaterial | null = null
let lakePolyHighlightOutlineMesh:   THREE.Mesh | null = null  // black rim (lake-polygon-shaped, slightly larger)
let lakePolyHighlightOutlineMat:    THREE.MeshBasicMaterial | null = null
let lakePolyHighlightGlowMesh:      THREE.Mesh | null = null  // (legacy additive halo path, gated off)
let lakePolyHighlightGlowMat:       THREE.MeshBasicMaterial | null = null
// "Click here" affordance: a thin black ring in the tangent plane at
// the lake centroid whose mesh.scale animates 1×→5×→1× over a 3-second
// cycle, so the user sees a sonar-style ring pulsing out from the
// real-size lake. Geometry is centroid-local (origin = lake centroid)
// so mesh.scale scales from the lake centre, not the world origin.
let lakePolyHighlightPulseMesh:     THREE.Mesh | null = null
let lakePolyHighlightPulseMat:      THREE.MeshBasicMaterial | null = null
// Invisible filled disc co-located with the pulse mesh at its MAX
// extent — used as the raycaster click target so the user can click
// anywhere within the pulse's outer envelope (not just on the thin
// visible ring).
let lakePolyHighlightHitMesh:       THREE.Mesh | null = null
let lakePolyUrl:                    string | null = null
let lakePolyHighlightId:            string | null = null
let lakePolyData:                   LakePoly[] | null = null
let lakePolyFetchInFlight = false
// Latest desired material state. Stored separately from the materials
// because applyLakePolygons gets called BEFORE the async XHR completes
// (and before the materials are created in buildLakePolyGeometries),
// so the first opacity set would otherwise be lost. Both
// applyLakePolygons and buildLakePolyGeometries pull from this struct.
const lakePolyState = {
  baseColor:             '#4ad1ff',
  baseAlpha:             0.85,
  opacity:               0,
  highlightFillColor:    '#1abc9c',  // Caribbean blue / turquoise
  highlightOutlineColor: '#f5c75e',  // gold
  highlightScale:        3.0,
  highlightGlow:         true,
}

function lonlatTo3D(lon: number, lat: number, r: number, out: number[]): void {
  // Geographic (lon, lat) in degrees → cartesian on a sphere of
  // radius r. Geographic convention: lon=0 at +X, lat increases toward
  // +Z (north). Matches GREENLAND_FOCAL math elsewhere in this file.
  const la = (lat * Math.PI) / 180
  const lo = (lon * Math.PI) / 180
  const c = Math.cos(la)
  out.push(r * c * Math.cos(lo))
  out.push(r * c * Math.sin(lo))
  out.push(r * Math.sin(la))
}

function buildLakePolyGeometries(): void {
  if (!lakePolyData) return
  // Highlight design (NL beacon):
  //   * OUTLINE — same polygon as the fill but scaled 5% larger,
  //               filled gold. Drawn behind the fill so only the
  //               5% rim is visible.
  //   * FILL    — polygon at highlightScale (default 2.0), deep
  //               supraglacial-lake blue. Drawn on top. animate()
  //               pulses its opacity for a "click me" affordance —
  //               replaced the older additive cyan glow halo, which
  //               was invisible on the white snow basemap (cyan
  //               additive into white = whiter white).
  //   * (glow path remains for back-compat but is gated off by
  //    highlightGlow=false from SectionCh1 emit.)
  //
  // Per-ring-vertex DEM sampling: each ring vertex's radius is the
  // LOCAL surface elevation × currentExag, so the polygon FOLLOWS
  // the surface contour instead of sitting flat on the centroid's
  // single elevation (which made it look like a disc floating above
  // a sloped surface on the previous build). Centroid stays at its
  // single elevation; the surrounding ring drapes over the local DEM.
  const EXTRA_LIFT = GLOBE_RADIUS * 0.0001
  const baseVerts:    number[] = []
  const baseIdx:      number[] = []
  const fillVerts:    number[] = []
  const fillIdx:      number[] = []
  const outlineVerts: number[] = []
  const outlineIdx:   number[] = []
  const glowVerts:    number[] = []
  const glowIdx:      number[] = []

  const VIZ_SCALE_BASE = 8.0
  const FILL_SCALE     = lakePolyState.highlightScale
  // Outline scale 1.5× the fill: at real-size lakes (FILL_SCALE=1) the
  // previous 1.05 ratio gave a sub-pixel rim at chapter framing
  // (~70 km/pixel viewport, 0.05 × 500 m lake-radius = 25 m). 1.5×
  // gives a ~500 m rim that reads as a visible ring at all reasonable
  // chapter zooms. At larger FILL_SCALE the proportional rim still
  // works (1.5× is generous at 2×+ scales, no harm).
  const OUTLINE_SCALE  = FILL_SCALE * 1.5
  const GLOW_RADIUS_KM = 8.0
  const GLOW_RING_N    = 48

  for (const lake of lakePolyData) {
    const ring = lake.ring
    if (!ring || ring.length < 3) continue
    const isHighlight = lakePolyHighlightId !== null && lake.id === lakePolyHighlightId
    const cx = lake.lon
    const cy = lake.lat
    const liftC = surfaceRadiusAt(cx, cy, EXTRA_LIFT)

    if (!isHighlight) {
      // Bulk lake: single triangle fan at VIZ_SCALE_BASE. Centroid-
      // sampled lift is fine here — bulk overlay is mostly hidden
      // (basemap shows lakes naturally) and the visible-flash only
      // beats don't require precise surface following.
      const startVert = baseVerts.length / 3
      lonlatTo3D(cx, cy, liftC, baseVerts)
      for (const p of ring) {
        const sx = cx + (p[0] - cx) * VIZ_SCALE_BASE
        const sy = cy + (p[1] - cy) * VIZ_SCALE_BASE
        lonlatTo3D(sx, sy, liftC, baseVerts)
      }
      const ringStart = startVert + 1
      for (let i = 0; i < ring.length; i++) {
        baseIdx.push(startVert, ringStart + i, ringStart + ((i + 1) % ring.length))
      }
    } else {
      // Highlight: two fans (fill, outline). Per-vertex DEM sampling
      // makes the disc drape over the local surface contour.
      let startVert = fillVerts.length / 3
      lonlatTo3D(cx, cy, liftC, fillVerts)
      for (const p of ring) {
        const sx = cx + (p[0] - cx) * FILL_SCALE
        const sy = cy + (p[1] - cy) * FILL_SCALE
        const liftV = surfaceRadiusAt(sx, sy, EXTRA_LIFT)
        lonlatTo3D(sx, sy, liftV, fillVerts)
      }
      let ringStart = startVert + 1
      for (let i = 0; i < ring.length; i++) {
        fillIdx.push(startVert, ringStart + i, ringStart + ((i + 1) % ring.length))
      }

      startVert = outlineVerts.length / 3
      lonlatTo3D(cx, cy, liftC, outlineVerts)
      for (const p of ring) {
        const sx = cx + (p[0] - cx) * OUTLINE_SCALE
        const sy = cy + (p[1] - cy) * OUTLINE_SCALE
        const liftV = surfaceRadiusAt(sx, sy, EXTRA_LIFT)
        lonlatTo3D(sx, sy, liftV, outlineVerts)
      }
      ringStart = startVert + 1
      for (let i = 0; i < ring.length; i++) {
        outlineIdx.push(startVert, ringStart + i, ringStart + ((i + 1) % ring.length))
      }

      if (lakePolyState.highlightGlow) {
        // Optional legacy additive-cyan halo. Off by default — see
        // header comment for why it doesn't work over snow.
        const cosLat = Math.cos((cy * Math.PI) / 180)
        const dlat = GLOW_RADIUS_KM / 111.0
        const dlon = GLOW_RADIUS_KM / (111.0 * Math.max(0.1, cosLat))
        startVert = glowVerts.length / 3
        lonlatTo3D(cx, cy, liftC, glowVerts)
        for (let i = 0; i < GLOW_RING_N; i++) {
          const a = (i / GLOW_RING_N) * 2 * Math.PI
          lonlatTo3D(cx + dlon * Math.cos(a), cy + dlat * Math.sin(a), liftC, glowVerts)
        }
        ringStart = startVert + 1
        for (let i = 0; i < GLOW_RING_N; i++) {
          glowIdx.push(startVert, ringStart + i, ringStart + ((i + 1) % GLOW_RING_N))
        }
      }
    }
  }

  // Tear down stale meshes before rebuilding.
  for (const m of [lakePolyBaseMesh, lakePolyHighlightFillMesh,
                   lakePolyHighlightOutlineMesh, lakePolyHighlightGlowMesh,
                   lakePolyHighlightPulseMesh, lakePolyHighlightHitMesh]) {
    if (m) { scene.remove(m); m.geometry.dispose() }
  }
  lakePolyBaseMesh = null
  lakePolyHighlightFillMesh = null
  lakePolyHighlightOutlineMesh = null
  lakePolyHighlightGlowMesh = null
  lakePolyHighlightPulseMesh = null
  lakePolyHighlightHitMesh = null

  const mkGeom = (verts: number[], idx: number[]): THREE.BufferGeometry => {
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3))
    g.setIndex(idx)
    return g
  }
  const mkMatBasic = (color: string, opacity: number, opts: any = {}): THREE.MeshBasicMaterial =>
    new THREE.MeshBasicMaterial({
      color:       new THREE.Color(color),
      transparent: true,
      opacity,
      depthWrite:  false,
      depthTest:   false,
      side:        THREE.DoubleSide,
      ...opts,
    })

  // ── Base (bulk lakes; usually hidden at baseAlpha=0 in beat 1+) ──
  if (baseVerts.length > 0) {
    if (!lakePolyBaseMat) {
      lakePolyBaseMat = mkMatBasic(
        lakePolyState.baseColor,
        lakePolyState.opacity * lakePolyState.baseAlpha,
      )
    } else {
      lakePolyBaseMat.color.set(lakePolyState.baseColor)
      lakePolyBaseMat.opacity = lakePolyState.opacity * lakePolyState.baseAlpha
    }
    lakePolyBaseMesh = new THREE.Mesh(mkGeom(baseVerts, baseIdx), lakePolyBaseMat)
    lakePolyBaseMesh.renderOrder = 6
    scene.add(lakePolyBaseMesh)
  }

  // ── Highlight glow (additive halo — pulses in animate()) ──
  if (glowVerts.length > 0 && lakePolyState.highlightGlow) {
    if (!lakePolyHighlightGlowMat) {
      lakePolyHighlightGlowMat = mkMatBasic(
        lakePolyState.highlightFillColor,
        lakePolyState.opacity * 0.6,
        { blending: THREE.AdditiveBlending },
      )
    } else {
      lakePolyHighlightGlowMat.color.set(lakePolyState.highlightFillColor)
      lakePolyHighlightGlowMat.opacity = lakePolyState.opacity * 0.6
    }
    lakePolyHighlightGlowMesh = new THREE.Mesh(
      mkGeom(glowVerts, glowIdx), lakePolyHighlightGlowMat,
    )
    lakePolyHighlightGlowMesh.renderOrder = 7  // beneath outline + fill
    scene.add(lakePolyHighlightGlowMesh)
  }

  // ── Highlight outline (gold underlay at 1.05× the fill) ──
  if (outlineVerts.length > 0) {
    if (!lakePolyHighlightOutlineMat) {
      lakePolyHighlightOutlineMat = mkMatBasic(
        lakePolyState.highlightOutlineColor,
        lakePolyState.opacity,
      )
    } else {
      lakePolyHighlightOutlineMat.color.set(lakePolyState.highlightOutlineColor)
      lakePolyHighlightOutlineMat.opacity = lakePolyState.opacity
    }
    lakePolyHighlightOutlineMesh = new THREE.Mesh(
      mkGeom(outlineVerts, outlineIdx), lakePolyHighlightOutlineMat,
    )
    lakePolyHighlightOutlineMesh.renderOrder = 8  // above glow, below fill
    scene.add(lakePolyHighlightOutlineMesh)
  }

  // ── Highlight fill (Caribbean blue centre — drawn last, on top) ──
  if (fillVerts.length > 0) {
    if (!lakePolyHighlightFillMat) {
      lakePolyHighlightFillMat = mkMatBasic(
        lakePolyState.highlightFillColor,
        lakePolyState.opacity,
      )
    } else {
      lakePolyHighlightFillMat.color.set(lakePolyState.highlightFillColor)
      lakePolyHighlightFillMat.opacity = lakePolyState.opacity
    }
    lakePolyHighlightFillMesh = new THREE.Mesh(
      mkGeom(fillVerts, fillIdx), lakePolyHighlightFillMat,
    )
    lakePolyHighlightFillMesh.renderOrder = 9
    scene.add(lakePolyHighlightFillMesh)
  }

  // ── Pulse ring + hit disc — built once per highlighted lake in
  //    centroid-local coords so mesh.scale animates around the lake
  //    centre (not the world origin). Both lie in the tangent plane
  //    at the centroid. The pulse ring is a thin annulus visible all
  //    the time; the hit disc is invisible but raycaster-hittable at
  //    the pulse's max extent. ──
  if (lakePolyHighlightId && lakePolyData) {
    const highlightLake = lakePolyData.find((l) => l.id === lakePolyHighlightId)
    if (highlightLake) {
      const cx = highlightLake.lon
      const cy = highlightLake.lat
      const cR = surfaceRadiusAt(cx, cy, EXTRA_LIFT)
      const cLatRad = (cy * Math.PI) / 180
      const cLonRad = (cx * Math.PI) / 180
      const centroidWorld = new THREE.Vector3(
        cR * Math.cos(cLatRad) * Math.cos(cLonRad),
        cR * Math.cos(cLatRad) * Math.sin(cLonRad),
        cR * Math.sin(cLatRad),
      )
      // Tangent basis at centroid: east, north, up=radial.
      const radialOut = centroidWorld.clone().normalize()
      const eastDir = new THREE.Vector3(-Math.sin(cLonRad), Math.cos(cLonRad), 0).normalize()
      const northDir = new THREE.Vector3().crossVectors(radialOut, eastDir).normalize()

      // Estimate the lake's effective radius from its ring vertices —
      // mean distance from centroid in degrees, converted to world units.
      let meanRingDeg = 0
      for (const p of highlightLake.ring) {
        const dlon = (p[0] - cx) * Math.cos(cLatRad)
        const dlat = p[1] - cy
        meanRingDeg += Math.sqrt(dlon * dlon + dlat * dlat)
      }
      meanRingDeg /= Math.max(1, highlightLake.ring.length)
      const lakeRadiusKm = meanRingDeg * 111.0
      const lakeRadiusWorld = (lakeRadiusKm / 6371.0) * GLOBE_RADIUS

      // Pulse ring (thin annulus, 5% thickness, base radius = lake radius;
      // mesh.scale 1×→5× animates it outward).
      const PULSE_N = 64
      const RING_INNER = 0.95
      const RING_OUTER = 1.00
      const pulseVerts: number[] = []
      const pulseIdx:   number[] = []
      for (let i = 0; i < PULSE_N; i++) {
        const a = (i / PULSE_N) * 2 * Math.PI
        const dir = eastDir.clone().multiplyScalar(Math.cos(a))
          .add(northDir.clone().multiplyScalar(Math.sin(a)))
        const inner = dir.clone().multiplyScalar(lakeRadiusWorld * RING_INNER)
        const outer = dir.clone().multiplyScalar(lakeRadiusWorld * RING_OUTER)
        pulseVerts.push(inner.x, inner.y, inner.z, outer.x, outer.y, outer.z)
      }
      for (let i = 0; i < PULSE_N; i++) {
        const i0 = i * 2, i1 = i * 2 + 1
        const i2 = ((i + 1) % PULSE_N) * 2, i3 = ((i + 1) % PULSE_N) * 2 + 1
        pulseIdx.push(i0, i1, i2, i2, i1, i3)
      }
      lakePolyHighlightPulseMat = mkMatBasic('#000000', lakePolyState.opacity)
      lakePolyHighlightPulseMesh = new THREE.Mesh(
        mkGeom(pulseVerts, pulseIdx), lakePolyHighlightPulseMat,
      )
      lakePolyHighlightPulseMesh.position.copy(centroidWorld)
      lakePolyHighlightPulseMesh.renderOrder = 10
      scene.add(lakePolyHighlightPulseMesh)

      // Hit disc — invisible filled disc at 5× lake radius. Raycaster
      // hits any triangle of the disc, so click-anywhere-in-the-pulse
      // works regardless of where in the cycle the ring currently is.
      const HIT_N = 32
      const HIT_R = lakeRadiusWorld * 5
      const hitVerts: number[] = [0, 0, 0]
      const hitIdx:   number[] = []
      for (let i = 0; i < HIT_N; i++) {
        const a = (i / HIT_N) * 2 * Math.PI
        const dir = eastDir.clone().multiplyScalar(Math.cos(a))
          .add(northDir.clone().multiplyScalar(Math.sin(a)))
        const v = dir.multiplyScalar(HIT_R)
        hitVerts.push(v.x, v.y, v.z)
      }
      for (let i = 0; i < HIT_N; i++) {
        hitIdx.push(0, 1 + i, 1 + ((i + 1) % HIT_N))
      }
      lakePolyHighlightHitMesh = new THREE.Mesh(
        mkGeom(hitVerts, hitIdx),
        new THREE.MeshBasicMaterial({
          visible: false,
          side: THREE.DoubleSide,
          depthTest: false, depthWrite: false,
        }),
      )
      lakePolyHighlightHitMesh.position.copy(centroidWorld)
      lakePolyHighlightHitMesh.renderOrder = 1  // doesn't actually render
      scene.add(lakePolyHighlightHitMesh)
    }
  }
}

function fetchLakePolygons(url: string): void {
  // Hard-learned bug: `await fetch(); await resp.text()` hung indefinitely
  // inside Playwright Chromium on this specific URL via the Vite /r2/
  // proxy, even though curl returned in 300 ms. XHR works fine for the
  // same payload and is simpler. Keep this path as XHR — fetch is fine
  // for everything else (and motivation's streamlines fetch works), but
  // for whatever reason this one combination hangs.
  if (lakePolyFetchInFlight) return
  lakePolyFetchInFlight = true
  const xhr = new XMLHttpRequest()
  xhr.open('GET', url, true)
  xhr.responseType = 'json'
  xhr.onload = () => {
    lakePolyFetchInFlight = false
    if (xhr.status !== 200) {
      console.warn('[lake polygons] xhr non-200', xhr.status)
      return
    }
    const data = xhr.response
    if (!data || !Array.isArray(data.lakes)) {
      console.warn('[lake polygons] bad payload', data)
      return
    }
    lakePolyData = data.lakes as LakePoly[]
    lakePolyUrl  = url
    buildLakePolyGeometries()
  }
  xhr.onerror = () => {
    lakePolyFetchInFlight = false
    console.warn('[lake polygons] xhr network error')
  }
  xhr.send()
}

function disposeLakePolygons(): void {
  for (const m of [lakePolyBaseMesh, lakePolyHighlightFillMesh,
                   lakePolyHighlightOutlineMesh, lakePolyHighlightGlowMesh,
                   lakePolyHighlightPulseMesh, lakePolyHighlightHitMesh]) {
    if (m) {
      scene.remove(m)
      m.geometry.dispose()
      ;(m.material as THREE.Material | undefined)?.dispose?.()
    }
  }
  lakePolyBaseMesh = null
  lakePolyHighlightFillMesh = null
  lakePolyHighlightOutlineMesh = null
  lakePolyHighlightGlowMesh = null
  lakePolyHighlightPulseMesh = null
  lakePolyHighlightHitMesh = null
  if (lakePolyBaseMat)             { lakePolyBaseMat.dispose();             lakePolyBaseMat = null }
  if (lakePolyHighlightFillMat)    { lakePolyHighlightFillMat.dispose();    lakePolyHighlightFillMat = null }
  if (lakePolyHighlightOutlineMat) { lakePolyHighlightOutlineMat.dispose(); lakePolyHighlightOutlineMat = null }
  if (lakePolyHighlightGlowMat)    { lakePolyHighlightGlowMat.dispose();    lakePolyHighlightGlowMat = null }
  if (lakePolyHighlightPulseMat)   { lakePolyHighlightPulseMat.dispose();   lakePolyHighlightPulseMat = null }
  lakePolyData = null
  lakePolyUrl  = null
  lakePolyHighlightId = null
}

function applyLakePolygons(p: NonNullable<typeof props.lakePolygons>): void {
  const newHighlight = p.highlightId ?? null
  const needsLoad     = lakePolyUrl !== p.dataUrl
  const needsRebuild  = needsLoad || lakePolyHighlightId !== newHighlight
  lakePolyHighlightId = newHighlight
  // Cache the desired material state. buildLakePolyGeometries pulls
  // from here when it (re)creates materials AFTER the async XHR — so
  // the first emit's opacity isn't lost.
  lakePolyState.baseColor             = p.baseColor             ?? '#4ad1ff'
  lakePolyState.baseAlpha             = p.baseAlpha             ?? 0.85
  lakePolyState.opacity               = p.opacity               ?? 0
  lakePolyState.highlightFillColor    = p.highlightFillColor    ?? '#1abc9c'
  lakePolyState.highlightOutlineColor = p.highlightOutlineColor ?? '#f5c75e'
  lakePolyState.highlightScale        = p.highlightScale        ?? 3.0
  lakePolyState.highlightGlow         = p.highlightGlow         ?? true
  if (needsLoad) {
    fetchLakePolygons(p.dataUrl)
  } else if (needsRebuild && lakePolyData) {
    buildLakePolyGeometries()
  } else {
    // Same data, same highlight — just refresh material opacities/colors.
    if (lakePolyBaseMat) {
      lakePolyBaseMat.color.set(lakePolyState.baseColor)
      lakePolyBaseMat.opacity = lakePolyState.opacity * lakePolyState.baseAlpha
    }
    if (lakePolyHighlightFillMat) {
      lakePolyHighlightFillMat.color.set(lakePolyState.highlightFillColor)
      lakePolyHighlightFillMat.opacity = lakePolyState.opacity
    }
    if (lakePolyHighlightOutlineMat) {
      lakePolyHighlightOutlineMat.color.set(lakePolyState.highlightOutlineColor)
      lakePolyHighlightOutlineMat.opacity = lakePolyState.opacity
    }
    if (lakePolyHighlightGlowMat) {
      lakePolyHighlightGlowMat.color.set(lakePolyState.highlightFillColor)
      // base glow opacity (the pulse animation in animate() modulates around this)
      lakePolyHighlightGlowMat.opacity = lakePolyState.opacity * 0.6
    }
  }
}

watch(
  () => props.lakePolygons,
  (v) => {
    if (v?.featured) {
      disposeLakePolygons()
      applyFeaturedLakes(v)
    } else {
      disposeFeaturedLakes()
      if (v) applyLakePolygons(v)
      else disposeLakePolygons()
    }
  },
)

// ─────────── Featured drainage-class lakes (Ch.1 Beat 0) ─────────────
//
// Five ESSD fig-4 representative lakes, each rendered as its own
// centroid-local mesh group (fill in the class color over a black
// outline underlay, plus an invisible hit disc). Centroid-local
// geometry so group.scale animates around the lake centre — hovering
// grows the lake 1.5× (the director's spec: hover-to-discover replaces the
// "North Lake" label). Clicking any lake emits lake-beacon-click(id)
// and the parent opens that lake's Sentinel-2 movie popup.

interface FeaturedGroup {
  /** The lake's ring + its overview enlargement (rebuilds for `keep.track`). */
  lake: LakePoly
  vizScale: number
  builtExag: number
  builtScale: number
  id: string
  color: string
  centroid: THREE.Vector3
  lon: number
  lat: number
  group: THREE.Group
  hitMesh: THREE.Mesh
  mats: THREE.MeshBasicMaterial[]
  scaleCurrent: number
  /** The dark outline's ring (centroid-local, ≤ 48 points) — projected
   *  every frame into `__featuredLakeScreens[id].ring` so the lake-movie
   *  popup's leader line stops AT the drawn polygon edge. */
  edge: THREE.Vector3[]
}

let featuredGroups: FeaturedGroup[] = []
let featuredData: LakePoly[] | null = null
let featuredUrl: string | null = null
let featuredFetchInFlight = false
let featuredOpacity = 0
let featuredKeep: { id: string; opacity: number; track?: boolean; shrink?: number } | null = null
function featuredOpFor(id: string): number {
  return featuredKeep && featuredKeep.id === id ? featuredKeep.opacity : featuredOpacity
}
let featuredInert = false
let hoveredFeaturedId: string | null = null
let featuredPulseLastId: string | null = null
let featuredPulseSince = 0
const FEATURED_PULSE_MAX = 2.4
const FEATURED_PULSE_PERIOD_S = 1.4
const FEATURED_HOVER_SCALE = 1.5
const FEATURED_VIZ_SCALE = 2.2   // base size: larger than real so the
                                 // small LD/ND lakes read at framing
const FEATURED_HIT_SCALE = 3.2   // hit disc radius vs lake radius

const FEATURED_EXTRA_LIFT = GLOBE_RADIUS * 0.00012
/** A featured lake's ring as a centroid-local fan at `scale` × its true
 *  size, on the CURRENT surface (exaggeration included). */
function featuredFan(lake: LakePoly, centroid: THREE.Vector3, scale: number, lift = FEATURED_EXTRA_LIFT): THREE.BufferGeometry {
  const cx = lake.lon
  const cy = lake.lat
  const verts: number[] = [0, 0, 0]
  const idx: number[] = []
  for (const p of lake.ring) {
    const sx = cx + (p[0] - cx) * scale
    const sy = cy + (p[1] - cy) * scale
    const tmp: number[] = []
    // the smooth lookup: these vertices slide over the surface as the held
    // lake shrinks (relayFeatured) and must not step with the DEM's pixels
    lonlatTo3D(sx, sy, surfaceRadiusSmoothAt(sx, sy, lift), tmp)
    verts.push(tmp[0] - centroid.x, tmp[1] - centroid.y, tmp[2] - centroid.z)
  }
  const n = lake.ring.length
  for (let i = 0; i < n; i++) idx.push(0, 1 + i, 1 + ((i + 1) % n))
  const g = new THREE.BufferGeometry()
  g.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3))
  g.setIndex(idx)
  return g
}
/** Chapter 2's dive: re-lay the held lake on the live surface at `scale`
 *  (its fill + dark rim; the hit disc is irrelevant — the lake is inert). */
function relayFeatured(fg: FeaturedGroup, scale: number): void {
  // No lift: it is drawn without a depth test, and a fixed world lift
  // floats ~400 m above the block at the landed 2×.
  const cR = surfaceRadiusSmoothAt(fg.lon, fg.lat, 0)
  const la = (fg.lat * Math.PI) / 180
  const lo = (fg.lon * Math.PI) / 180
  fg.centroid.set(cR * Math.cos(la) * Math.cos(lo), cR * Math.cos(la) * Math.sin(lo), cR * Math.sin(la))
  fg.group.position.copy(fg.centroid)
  const [rim, fill] = fg.group.children as THREE.Mesh[]
  rim.geometry.dispose()
  rim.geometry = featuredFan(fg.lake, fg.centroid, scale * 1.28, 0)
  fill.geometry.dispose()
  fill.geometry = featuredFan(fg.lake, fg.centroid, scale, 0)
  fg.builtExag = currentExag
  fg.builtScale = scale
  // The published ring (`__featuredLakeScreens[id].ring`) follows the drawn rim.
  const pos = rim.geometry.getAttribute('position')
  const n = pos.count - 1
  const step = Math.max(1, Math.ceil(n / 48))
  fg.edge = []
  for (let i = 1; i <= n; i += step) fg.edge.push(new THREE.Vector3().fromBufferAttribute(pos, i))
}

function buildFeaturedGroups(): void {
  disposeFeaturedMeshes()
  if (!featuredData) return
  const EXTRA_LIFT = GLOBE_RADIUS * 0.00012
  for (const lake of featuredData) {
    if (!lake.ring || lake.ring.length < 3) continue
    // Per-lake visual scale: normalize by area so the small LD/ND
    // lakes (0.3–0.4 km²) read at chapter framing instead of being
    // 4-px flecks next to the 3-km² NL. sqrt(area) normalization,
    // extra factor clamped ≤ 2.5×; the legend notes the enlargement.
    const areaM2 = (lake as any).area_m2 as number | undefined
    const areaBoost = areaM2
      ? Math.min(2.5, Math.max(1, Math.sqrt(2.0e6 / areaM2)))
      : 1
    const vizScale = FEATURED_VIZ_SCALE * areaBoost
    const cx = lake.lon
    const cy = lake.lat
    const cR = surfaceRadiusSmoothAt(cx, cy, EXTRA_LIFT)
    const cLatRad = (cy * Math.PI) / 180
    const cLonRad = (cx * Math.PI) / 180
    const centroid = new THREE.Vector3(
      cR * Math.cos(cLatRad) * Math.cos(cLonRad),
      cR * Math.cos(cLatRad) * Math.sin(cLonRad),
      cR * Math.sin(cLatRad),
    )

    const fan = (scale: number) => featuredFan(lake, centroid, scale)

    const mkMat = (color: string, opacity: number): THREE.MeshBasicMaterial =>
      new THREE.MeshBasicMaterial({
        color: new THREE.Color(color),
        transparent: true,
        opacity,
        depthWrite: false,
        depthTest: false,
        side: THREE.DoubleSide,
      })

    const outlineMat = mkMat('#0d0a06', featuredOpFor(lake.id) * 0.9)
    const fillMat = mkMat(lake.color ?? '#4ad1ff', featuredOpFor(lake.id))
    const outline = new THREE.Mesh(fan(vizScale * 1.28), outlineMat)
    outline.renderOrder = 8
    const fill = new THREE.Mesh(fan(vizScale), fillMat)
    fill.renderOrder = 9

    // Effective lake radius (mean ring distance) for the hit disc.
    let meanRingDeg = 0
    for (const p of lake.ring) {
      const dlon = (p[0] - cx) * Math.cos(cLatRad)
      const dlat = p[1] - cy
      meanRingDeg += Math.sqrt(dlon * dlon + dlat * dlat)
    }
    meanRingDeg /= Math.max(1, lake.ring.length)
    const hitR = Math.max(
      (meanRingDeg * 111.0 / 6371.0) * GLOBE_RADIUS * vizScale * FEATURED_HIT_SCALE,
      GLOBE_RADIUS * 0.0016,  // floor so the tiny LD lake is still clickable
    )
    const radialOut = centroid.clone().normalize()
    const eastDir = new THREE.Vector3(-Math.sin(cLonRad), Math.cos(cLonRad), 0).normalize()
    const northDir = new THREE.Vector3().crossVectors(radialOut, eastDir).normalize()
    const HIT_N = 24
    const hitVerts: number[] = [0, 0, 0]
    const hitIdx: number[] = []
    for (let i = 0; i < HIT_N; i++) {
      const a = (i / HIT_N) * 2 * Math.PI
      const v = eastDir.clone().multiplyScalar(Math.cos(a) * hitR)
        .add(northDir.clone().multiplyScalar(Math.sin(a) * hitR))
      hitVerts.push(v.x, v.y, v.z)
    }
    for (let i = 0; i < HIT_N; i++) hitIdx.push(0, 1 + i, 1 + ((i + 1) % HIT_N))
    const hitGeom = new THREE.BufferGeometry()
    hitGeom.setAttribute('position', new THREE.Float32BufferAttribute(hitVerts, 3))
    hitGeom.setIndex(hitIdx)
    const hitMesh = new THREE.Mesh(hitGeom, new THREE.MeshBasicMaterial({
      visible: false, side: THREE.DoubleSide, depthTest: false, depthWrite: false,
    }))
    hitMesh.userData.lakeId = lake.id

    const group = new THREE.Group()
    group.add(outline)
    group.add(fill)
    group.add(hitMesh)
    group.position.copy(centroid)
    group.renderOrder = 9
    scene.add(group)

    featuredGroups.push({
      lake,
      vizScale,
      builtExag: currentExag,
      builtScale: vizScale,
      id: lake.id,
      color: lake.color ?? '#4ad1ff',
      centroid,
      lon: cx,
      lat: cy,
      group,
      hitMesh,
      mats: [outlineMat, fillMat],
      scaleCurrent: 1,
      edge: (() => {
        const pos = outline.geometry.getAttribute('position')
        const n = pos.count - 1 // vertex 0 = the fan's centre
        const step = Math.max(1, Math.ceil(n / 48))
        const out: THREE.Vector3[] = []
        for (let i = 1; i <= n; i += step) out.push(new THREE.Vector3().fromBufferAttribute(pos, i))
        return out
      })(),
    })
  }
}

function disposeFeaturedMeshes(): void {
  for (const fg of featuredGroups) {
    scene.remove(fg.group)
    fg.group.traverse((o) => {
      const m = o as THREE.Mesh
      if (m.geometry) m.geometry.dispose()
      ;(m.material as THREE.Material | undefined)?.dispose?.()
    })
  }
  featuredGroups = []
  hoveredFeaturedId = null
}

function disposeFeaturedLakes(): void {
  disposeFeaturedMeshes()
  featuredData = null
  featuredUrl = null
  featuredOpacity = 0
  featuredKeep = null
  featuredInert = false
}

function applyFeaturedLakes(p: NonNullable<typeof props.lakePolygons>): void {
  featuredOpacity = p.opacity ?? 0
  featuredKeep = p.keep ?? null
  featuredInert = !!p.inert
  if (featuredInert && hoveredFeaturedId !== null) {
    hoveredFeaturedId = null
    emit('lake-beacon-hover', null)
  }
  for (const fg of featuredGroups) {
    fg.mats[0].opacity = featuredOpFor(fg.id) * 0.9
    fg.mats[1].opacity = featuredOpFor(fg.id)
  }
  if (featuredUrl === p.dataUrl) return
  if (featuredFetchInFlight) return
  featuredFetchInFlight = true
  // XHR (not fetch) — see fetchLakePolygons for the Playwright hang note.
  const xhr = new XMLHttpRequest()
  xhr.open('GET', p.dataUrl, true)
  xhr.responseType = 'json'
  xhr.onload = () => {
    featuredFetchInFlight = false
    if (xhr.status !== 200 || !xhr.response?.lakes) {
      console.warn('[featured lakes] bad response', xhr.status)
      return
    }
    featuredData = xhr.response.lakes as LakePoly[]
    featuredUrl = p.dataUrl
    buildFeaturedGroups()
  }
  xhr.onerror = () => {
    featuredFetchInFlight = false
    console.warn('[featured lakes] xhr network error')
  }
  xhr.send()
}

function checkFeaturedHover(): string | null {
  if (!featuredGroups.length || !camera || featuredInert) return null
  raycaster.setFromCamera(mouseNDC, camera)
  const hits = raycaster.intersectObjects(featuredGroups.map((f) => f.hitMesh), false)
  if (!hits.length) return null
  return (hits[0].object.userData.lakeId as string) ?? null
}

// ─────────── Ch.1 North Lake cutaway (beats 1–2) ───────────────────────
//
// The North Lake outline must stay visible through the cutaway. At the
// cross-section framing the lake's TRUE footprint is useless: it lies
// inside the cut-away volume (the slab and the basemap's visible edge
// sit at slabLatRadFromCutLatDeg(68.6) ≈ 68.84°N, ~13 km north of the
// lake's 68.72°N centroid) and it is ~3 km across — a few pixels here.
// The slab already draws the lake as a cartoon lens at the fracture
// (CH_SLAB_LAKE_HALF_TLON, ~30 km). This draws the lake's own outline at
// that same cartoon scale ON the surface: NL's ring (Chaikin-smoothed),
// scaled so its east–west extent matches the lens, centred on the
// fracture with the FACE through its middle, and clipped to the part
// north of the face — the knife visibly cuts through the lake and the
// lens is its cross-section. Beat 0's look (class-coloured fill, dark
// rim); `water` (the drain) empties it, while the slab shader's green
// basin rim keeps the lake's outline in the section. N–S is stretched
// ×CUTAWAY_NS_STRETCH: the camera sees the surface obliquely and a
// true-proportion half-lake is a 4-px sliver.
//
// Vertices carry a unit direction + the DEM elevation; the vertex shader
// applies the LIVE exaggeration, so the outline stays on the dome
// through chapter-exag lerps without rebuilds. Drawn without depth test
// like the featured lakes (it lies on the surface; no z-fighting).

let cutawayMeshes: THREE.Mesh[] = []
let cutawayMats: { fill: THREE.ShaderMaterial; dark: THREE.ShaderMaterial } | null = null
let cutawayKey: string | null = null      // id|cutLat|color the meshes were built for
let cutawayRing: { id: string; lon: number; lat: number; ring: number[][] } | null = null
let cutawayRingUrl: string | null = null
let cutawayFetchInFlight = false
const CUTAWAY_RIM_KM = 2.2                 // dark rim ribbon width (beat 0's dark outline)
const CUTAWAY_WIDTH_OF_LENS = 0.9          // outline E–W extent / lens full width
                                           // (the parabolic lens thins to nothing at its tips)
const CUTAWAY_NS_STRETCH = 3               // N–S stretch: the camera sees the surface
                                           // obliquely, so a true-proportion half-lake is a sliver

function cutawayMat(color: string): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: {
      uColor: { value: new THREE.Color(color) },
      uOpacity: { value: 0 },
      uGlobeRadius: { value: GLOBE_RADIUS },
      uWorldPerM: { value: currentExag / SURF_MAX_M },
      uLift: { value: GLOBE_RADIUS * 0.00012 },
    },
    vertexShader: `
      attribute vec3 aDir;
      attribute float aElev;
      uniform float uGlobeRadius;
      uniform float uWorldPerM;
      uniform float uLift;
      void main() {
        vec3 p = aDir * (uGlobeRadius + aElev * uWorldPerM + uLift);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
      }
    `,
    fragmentShader: `
      uniform vec3 uColor;
      uniform float uOpacity;
      void main() { gl_FragColor = vec4(uColor, uOpacity); }
    `,
    transparent: true,
    depthTest: false,
    depthWrite: false,
    side: THREE.DoubleSide,
  })
}

function disposeLakeCutaway(): void {
  for (const m of cutawayMeshes) {
    scene.remove(m)
    m.geometry.dispose()
  }
  cutawayMeshes = []
  if (cutawayMats) {
    cutawayMats.fill.dispose()
    cutawayMats.dark.dispose()
  }
  cutawayMats = null
  cutawayKey = null
}

/** Build the clipped, cartoon-scaled outline. Needs the ring + the DEM
 *  readback (elevations); returns false to be retried next frame. */
function buildLakeCutaway(p: NonNullable<typeof props.lakeCutaway>): boolean {
  if (!cutawayRing || cutawayRing.id !== p.id || !demReadbackCtx) return false
  disposeLakeCutaway()
  const faceLat = (slabLatRadFromCutLatDeg(p.cutLatDeg) * 180) / Math.PI
  const lon0 = cutawayRing.lon
  const lat0 = cutawayRing.lat
  const KM = 111.32
  const cosF = Math.cos((faceLat * Math.PI) / 180)
  // Ring → local km (x east, y north) about the lake centroid.
  let pts = cutawayRing.ring.map((q) => new THREE.Vector2(
    (q[0] - lon0) * KM * Math.cos((lat0 * Math.PI) / 180),
    (q[1] - lat0) * KM,
  ))
  if (pts.length > 2 && pts[0].distanceTo(pts[pts.length - 1]) < 1e-9) pts.pop()
  // Chaikin corner cutting ×3 — the 14-vertex ring reads as a polygon
  // at ten times its size; a lake outline should be smooth.
  for (let it = 0; it < 3; it++) {
    const out: THREE.Vector2[] = []
    for (let i = 0; i < pts.length; i++) {
      const a = pts[i]
      const b = pts[(i + 1) % pts.length]
      out.push(a.clone().lerp(b, 0.25), a.clone().lerp(b, 0.75))
    }
    pts = out
  }
  // Scale to the lens: E–W extent = CUTAWAY_WIDTH_OF_LENS × lens width.
  const lensKm =
    2 * CH_SLAB_LAKE_HALF_TLON * ((CH_SLAB_LON_E - CH_SLAB_LON_W) * 180 / Math.PI) * KM * cosF
  let xMin = Infinity, xMax = -Infinity, yMin = Infinity, yMax = -Infinity
  for (const q of pts) {
    xMin = Math.min(xMin, q.x); xMax = Math.max(xMax, q.x)
    yMin = Math.min(yMin, q.y); yMax = Math.max(yMax, q.y)
  }
  const k = (CUTAWAY_WIDTH_OF_LENS * lensKm) / (xMax - xMin)
  const xc = (xMin + xMax) / 2
  const yc = (yMin + yMax) / 2
  // Centre on the fracture (the lake's own longitude = the lens centre)
  // with the face through the ring's N–S middle.
  pts = pts.map((q) => new THREE.Vector2((q.x - xc) * k, (q.y - yc) * k * CUTAWAY_NS_STRETCH))
  // Clip to y ≥ 0 (north of the face) — Sutherland–Hodgman, one plane.
  const clipped: THREE.Vector2[] = []
  for (let i = 0; i < pts.length; i++) {
    const a = pts[i]
    const b = pts[(i + 1) % pts.length]
    const aIn = a.y >= 0
    const bIn = b.y >= 0
    if (aIn) clipped.push(a)
    if (aIn !== bIn) {
      const t = a.y / (a.y - b.y)
      clipped.push(new THREE.Vector2(a.x + (b.x - a.x) * t, 0))
    }
  }
  if (clipped.length < 3) return true
  if (THREE.ShapeUtils.isClockWise(clipped)) clipped.reverse()

  const toLonLat = (q: THREE.Vector2): [number, number] =>
    [lon0 + q.x / (KM * cosF), faceLat + q.y / KM]
  const geomFrom = (verts: THREE.Vector2[], idx: number[]): THREE.BufferGeometry => {
    const dir: number[] = []
    const elev: number[] = []
    const pos: number[] = []
    for (const q of verts) {
      const [lo, la] = toLonLat(q)
      const tmp: number[] = []
      lonlatTo3D(lo, la, 1, tmp)
      dir.push(tmp[0], tmp[1], tmp[2])
      pos.push(tmp[0] * GLOBE_RADIUS, tmp[1] * GLOBE_RADIUS, tmp[2] * GLOBE_RADIUS)
      elev.push(getDemElevAt(lo, la))
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3))
    g.setAttribute('aDir', new THREE.Float32BufferAttribute(dir, 3))
    g.setAttribute('aElev', new THREE.Float32BufferAttribute(elev, 1))
    g.setIndex(idx)
    return g
  }

  // Water fill: ear-clipped polygon.
  const tris = THREE.ShapeUtils.triangulateShape(clipped, [])
  const fillGeom = geomFrom(clipped, tris.flat())

  // Outline: the boundary WITHOUT the straight cut edge along the face
  // (that edge is the slab's own gold top line). Start the open chain at
  // the vertex that leaves the face.
  const n = clipped.length
  const onFace = (i: number): boolean => Math.abs(clipped[i].y) < 1e-6
  let start = 0
  for (let i = 0; i < n; i++) {
    if (onFace(i) && !(onFace((i + 1) % n))) { start = i; break }
  }
  const chain: THREE.Vector2[] = [clipped[start]]
  for (let j = 1; j <= n; j++) {
    const i = (start + j) % n
    chain.push(clipped[i])
    if (onFace(i)) break
  }
  const ribbon = (widthKm: number): THREE.BufferGeometry => {
    const verts: THREE.Vector2[] = []
    const idx: number[] = []
    const h = widthKm / 2
    for (let i = 0; i < chain.length; i++) {
      const prev = chain[Math.max(0, i - 1)]
      const next = chain[Math.min(chain.length - 1, i + 1)]
      const t = next.clone().sub(prev).normalize()
      const nrm = new THREE.Vector2(-t.y, t.x)
      verts.push(chain[i].clone().addScaledVector(nrm, h), chain[i].clone().addScaledVector(nrm, -h))
      if (i > 0) {
        const a = 2 * (i - 1), b = a + 1, c = 2 * i, d = c + 1
        idx.push(a, b, c, c, b, d)
      }
    }
    return geomFrom(verts, idx)
  }

  cutawayMats = {
    fill: cutawayMat(p.color),
    dark: cutawayMat('#0d0a06'),
  }
  // Same render band as the featured lakes (fill 9, rim 10).
  const parts: [THREE.BufferGeometry, THREE.ShaderMaterial, number][] = [
    [fillGeom, cutawayMats.fill, 9],
    [ribbon(CUTAWAY_RIM_KM), cutawayMats.dark, 10],
  ]
  for (const [g, m, order] of parts) {
    const mesh = new THREE.Mesh(g, m)
    mesh.renderOrder = order
    mesh.frustumCulled = false
    scene.add(mesh)
    cutawayMeshes.push(mesh)
  }
  cutawayKey = `${p.id}|${p.cutLatDeg}|${p.color}`
  return true
}

function fetchCutawayRing(p: NonNullable<typeof props.lakeCutaway>): void {
  if (cutawayRingUrl === p.dataUrl && cutawayRing?.id === p.id) return
  if (cutawayFetchInFlight) return
  cutawayFetchInFlight = true
  // XHR (not fetch) — see fetchLakePolygons for the Playwright hang note.
  const xhr = new XMLHttpRequest()
  xhr.open('GET', p.dataUrl, true)
  xhr.responseType = 'json'
  xhr.onload = () => {
    cutawayFetchInFlight = false
    const lake = (xhr.response?.lakes as LakePoly[] | undefined)?.find((l) => l.id === p.id)
    if (xhr.status !== 200 || !lake) {
      console.warn('[lake cutaway] bad response', xhr.status)
      return
    }
    cutawayRing = { id: lake.id, lon: lake.lon, lat: lake.lat, ring: lake.ring }
    cutawayRingUrl = p.dataUrl
  }
  xhr.onerror = () => {
    cutawayFetchInFlight = false
    console.warn('[lake cutaway] xhr network error')
  }
  xhr.send()
}

/** Per frame: (re)build when needed, then drive exaggeration + opacity. */
function updateLakeCutaway(): void {
  const p = props.lakeCutaway
  if (!p || p.opacity <= 0.001) {
    if (cutawayMeshes.length) disposeLakeCutaway()
    return
  }
  fetchCutawayRing(p)
  if (cutawayKey !== `${p.id}|${p.cutLatDeg}|${p.color}` && !buildLakeCutaway(p)) return
  if (!cutawayMats) return
  const wpm = currentExag / SURF_MAX_M
  const water = Math.max(0, Math.min(1, p.water))
  // Beat 0's look (class-coloured fill, dark rim); the drain empties it
  // (the section's green basin rim empties with it — slab shader).
  cutawayMats.fill.uniforms.uOpacity.value = p.opacity * water
  cutawayMats.dark.uniforms.uOpacity.value = p.opacity * water * 0.9
  for (const m of [cutawayMats.fill, cutawayMats.dark]) {
    m.uniforms.uWorldPerM.value = wpm
  }
}

// ─────────── Ch.1 streamline highlight ───────────────
//
// Renders the streamline-through-North-Lake (from R2's
// ch01/north_lake_streamline.json) as a thin tube tangent to the
// elevated DEM, sitting on top of the surface velocity colormap so
// the viewer can follow the flow line from interior to coast. Tube
// (instead of plain LineBasicMaterial) so the line reads visibly at
// chapter framing where 1-px lines disappear.

let streamHiMesh:        THREE.Mesh | null = null
let streamHiMat:          THREE.MeshBasicMaterial | null = null
let streamHiUrl:         string | null = null
let streamHiFetchInFlight = false
let streamHiPolyline: number[][] | null = null  // [[lon, lat], ...]
// Smoothly-lerped opacity for the streamHi tube. Beat 3 sets target=1
// (tube visible), Beat 4 sets target=0 (tube fades out so the cross-
// section can take over the "here's the flow path" visual without
// doubling up the cue). animate() ramps streamHiMat.opacity toward
// this target each frame so the transition is gradual.
let streamHiOpacityTarget = 1
let streamHiOpacityCurrent = 1

function buildStreamHiTube(): void {
  if (!streamHiPolyline) return
  // Surface-hugging: each polyline vertex is lifted to the LOCAL DEM
  // elevation × currentExag, plus a tiny offset to clear the
  // basemap/velocity hillshade band. The streamline therefore drapes
  // along the actual ice surface (rather than floating at a fixed
  // radius matching the dome peak, which made it hover ~100 km above
  // the surface at chapter view). Extra lift is slightly larger than
  // the lake-polygon lift so the tube renders ON TOP of the polygons
  // when they overlap (the gold tube reads cleanly over the cyan
  // flash at Beat 3).
  const EXTRA_LIFT = GLOBE_RADIUS * 0.0014
  const pts: THREE.Vector3[] = []
  for (const [lon, lat] of streamHiPolyline) {
    const r = surfaceRadiusAt(lon, lat, EXTRA_LIFT)
    const v: number[] = []
    lonlatTo3D(lon, lat, r, v)
    pts.push(new THREE.Vector3(v[0], v[1], v[2]))
  }
  if (pts.length < 2) return
  const curve = new THREE.CatmullRomCurve3(pts)
  // Tube parameters: ~3 km radius at chapter scale. tubularSegments
  // = denser than streamline vertex count so curvature stays smooth;
  // radialSegments = 6 (low — at chapter framing a hexagonal cross-
  // section reads as round and saves draw calls).
  const TUBE_RADIUS_KM = 5
  const TUBE_RADIUS_WORLD = (TUBE_RADIUS_KM / EARTH_RADIUS_KM) * GLOBE_RADIUS
  const tubeGeom = new THREE.TubeGeometry(
    curve,
    Math.max(64, streamHiPolyline.length * 4),
    TUBE_RADIUS_WORLD,
    6,
    false,
  )
  if (streamHiMesh) {
    scene.remove(streamHiMesh)
    streamHiMesh.geometry.dispose()
  }
  if (!streamHiMat) {
    streamHiMat = new THREE.MeshBasicMaterial({
      // Black against the rainbow velocity colormap reads more like a
      // schematic flow line ("here's the streamline") than the previous
      // gold, which competed with the cross-section's gold rim on the
      // peel beat. The director's choice.
      color: new THREE.Color(0x000000),
      transparent: true,
      opacity: 1,
      depthWrite: false,
      depthTest: false,
    })
  }
  streamHiMesh = new THREE.Mesh(tubeGeom, streamHiMat)
  streamHiMesh.renderOrder = 8
  scene.add(streamHiMesh)
}

function fetchStreamHi(url: string): void {
  if (streamHiFetchInFlight) return
  streamHiFetchInFlight = true
  const xhr = new XMLHttpRequest()
  xhr.open('GET', url, true)
  xhr.responseType = 'json'
  xhr.onload = () => {
    streamHiFetchInFlight = false
    if (xhr.status !== 200) {
      console.warn('[stream highlight] bad payload', xhr.status)
      return
    }
    // Prefer `lonlat_full` (entire streamline interior→coast) for the
    // highlight tube, then trim the leading hook at the eastern end:
    // points 0..6 form a tight S-shape at lat ~69.3 / lon ~-38 where
    // the streamline doubles back before settling into its main WSW
    // run, which reads as a stray curl in the upper-right of the CW
    // framing. The "true elbow" is at index 7 (-38.76, 68.78), where
    // the polyline starts moving clearly westward toward the coast —
    // start the tube there.
    const fullPolyline = (xhr.response?.lonlat_full ?? xhr.response?.lonlat) as number[][] | undefined
    if (!fullPolyline) {
      console.warn('[stream highlight] no polyline in payload', xhr.response)
      return
    }
    const HOOK_TRIM = 7
    const polyline = fullPolyline.length > HOOK_TRIM + 2
      ? fullPolyline.slice(HOOK_TRIM)
      : fullPolyline
    streamHiPolyline = polyline
    streamHiUrl      = url
    buildStreamHiTube()
  }
  xhr.onerror = () => {
    streamHiFetchInFlight = false
    console.warn('[stream highlight] xhr network error')
  }
  xhr.send()
}

function disposeStreamHi(): void {
  if (streamHiMesh) {
    scene.remove(streamHiMesh)
    streamHiMesh.geometry.dispose()
    streamHiMesh = null
  }
  if (streamHiMat) { streamHiMat.dispose(); streamHiMat = null }
  streamHiPolyline = null
  streamHiUrl = null
}

function applyVelocityMode(v: NonNullable<typeof props.velocityMode>): void {
  if (!v.active) {
    disposeStreamHi()
    streamHiOpacityTarget = 1
    streamHiOpacityCurrent = 1
    return
  }
  if (v.dataUrl) {
    if (streamHiUrl !== v.dataUrl) {
      fetchStreamHi(v.dataUrl)
    }
    if (streamHiMat && v.highlightColor) {
      streamHiMat.color.set(v.highlightColor)
    }
  }
  // Update fade target; animate() smooths the current value toward it.
  streamHiOpacityTarget = v.highlightOpacity ?? 1
}

watch(
  () => props.velocityMode,
  (v) => {
    if (v) applyVelocityMode(v)
    else disposeStreamHi()
  },
)

// ───────── generic chapter colormap drape ──────────

function disposeChapterOverlay(): void {
  if (!chapterOverlayMesh) return
  scene.remove(chapterOverlayMesh)
  const mat = chapterOverlayMesh.material as THREE.MeshBasicMaterial
  mat.map?.dispose()
  mat.dispose()
  chapterOverlayMesh.geometry.dispose()
  chapterOverlayMesh = null
  chapterOverlayUrl = null
  chapterOverlayOpacityCurrent = 0
  chapterOverlayOpacityTarget = 0
}

let chapterOverlayRetryTimer: number | null = null
function applyChapterOverlay(v: NonNullable<typeof props.chapterOverlay>): void {
  // Deep-link guard (same class of bug as the chapter-slab's
  // build-pending retry): if the drape mesh is built while the DEM
  // textures are still loading, its displacement shader compiles
  // against empty textures and the patch renders flat — buried inside
  // the exag-inflated dome. Defer creation until the initial texture
  // batch settles; the prop is re-applied from the retry.
  if (chapterOverlayUrl !== v.url && (texturesPending > 0 || !demTextureHi?.image)) {
    if (chapterOverlayRetryTimer !== null) window.clearTimeout(chapterOverlayRetryTimer)
    chapterOverlayRetryTimer = window.setTimeout(() => {
      chapterOverlayRetryTimer = null
      if (props.chapterOverlay) applyChapterOverlay(props.chapterOverlay)
    }, 300)
    return
  }
  if (chapterOverlayUrl !== v.url) {
    disposeChapterOverlay()
    // Above the velocity patch (−2) so a chapter drape always wins the
    // depth fight against the standing basemap/velocity pair.
    chapterOverlayMesh = makeGreenlandPatch(v.url, -3)
    const overlayMat = chapterOverlayMesh.material as THREE.MeshBasicMaterial
    // The drape is mostly-transparent (alpha ramps with the data).
    // It must NOT write depth: Three's transparent sort can put it
    // before the basemap (identical mesh positions), and depth-written
    // invisible texels would then z-cull the basemap into blackness.
    // renderOrder pins it after the basemap/velocity pair explicitly.
    overlayMat.depthWrite = false
    attachDemDisplacement(overlayMat)
    chapterOverlayMesh.renderOrder = 1
    scene.add(chapterOverlayMesh)
    chapterOverlayUrl = v.url
  }
  chapterOverlayOpacityTarget = v.opacity ?? 1
}

watch(
  () => props.chapterOverlay,
  (v) => {
    if (v) applyChapterOverlay(v)
    // Null = fade out in place; the mesh is disposed on the next url
    // change (or page teardown) so a quick beat back/forward doesn't
    // re-decode the texture.
    else chapterOverlayOpacityTarget = 0
  },
)

// ───────── chapter cross-section slab ──────────
//
// Reuses the motivation step-0 slab pattern: a flat rectangle in
// (along × elevation) space, with the fragment shader sampling the
// bed / DEM textures to paint bedrock / ice / sky regions. This Ch.1
// version differs from motivation only in orientation — motivation's
// slab cuts along a meridian (lat-aligned) at the central dome's
// longitude; Ch.1 cuts along a parallel of latitude at North Lake's
// latitude (since flow at North Lake is roughly east-west, that's
// the along-flow cross-section).

const NORTH_LAKE_LAT = (68.7249 * Math.PI) / 180

let chapterSlabMesh: THREE.Mesh | null = null
let chapterSlabMat: THREE.ShaderMaterial | null = null
// Guard against scheduling parallel deferred builds. applyChapterReveal
// fires once per frame during the south-to-NL lerp; if bed/dem textures
// aren't loaded yet, the first call schedules a setTimeout retry —
// without this flag every subsequent per-frame call would queue its
// own retry, racing to build the same mesh many times over.
let chapterSlabBuildPending = false

function disposeChapterSlab(): void {
  if (!chapterSlabMesh) return
  scene.remove(chapterSlabMesh)
  chapterSlabMesh.geometry.dispose()
  ;(chapterSlabMesh.material as THREE.Material).dispose()
  chapterSlabMesh = null
  chapterSlabMat = null
  // Reset the paint-texture guard. Without this, a rebuild after a
  // dispose (leave the slab beats, come back) sees slabPaintUrl still
  // equal to the incoming paintUrl, skips the texture reload, and the
  // shader samples a null uPaintTex — which is BLACK. That was the
  // bug where the stress paint showed the right colours at first but
  // only black after running through the sequence and coming back.
  slabPaintUrl = null
}

// Latitude span the chapter slab is built across. Wider than NL's tight
// lon band (was -55..-22) so the slab still covers Greenland at the
// south-tip latitudes the Beat 4 knife sweeps through (south tip is
// at lon ~-43, but at lat=60° Greenland is ~-46..-42; at lat=68° it's
// ~-55..-22). The shader's outside-mask discards fragments where the
// surface PNG is 0 (ocean) so over-wide bounds get masked off cleanly.
const CH_SLAB_LON_W = (-58 * Math.PI) / 180
const CH_SLAB_LON_E = (-12 * Math.PI) / 180
// ±40 km (the theory panel's field window) as a fraction of the slab's
// lon span, measured along the NL-latitude arc: Δlon = d / (R·cosφ).
const CH_SLAB_CROP_HALF_TLON =
  (40e3 / (6.371e6 * Math.cos((68.7249 * Math.PI) / 180))) /
  (CH_SLAB_LON_E - CH_SLAB_LON_W)
// North Lake's cartoon lens in the slab (half-width in tLon units —
// ~30 km across; the real lake is ~3 km). Shared by the slab shader and
// the surface cutaway outline (buildLakeCutaway) so the two agree.
const CH_SLAB_LAKE_HALF_TLON = 0.008
const CH_SLAB_ELEV_MIN_M = -300
const CH_SLAB_ELEV_MAX_M = 3500

function buildChapterSlab(): void {
  // Defensive: motivation's slab also references bedTexture and
  // demTexture; both are loaded asynchronously. Without this guard
  // we'd build the slab with null textures and see nothing.
  if (!bedTexture || !demTexture) {
    if (chapterSlabBuildPending) return  // already scheduled — don't queue another
    chapterSlabBuildPending = true
    console.warn('chapter slab: textures not ready, deferring build')
    setTimeout(() => {
      chapterSlabBuildPending = false
      buildChapterSlab()
    }, 200)
    return
  }
  // Geometry: canonical (aTLon, aElevFrac) attribute pairs. Vertex
  // shader recomputes the world position from uCutLatRad each frame —
  // so the slab can SWEEP across latitudes without any geometry
  // rebuild. This is the motivation pattern (slab rotating around the
  // polar axis to track a moving longitude cut), axis-flipped for
  // Ch.1's south-to-NL latitude sweep.
  const N_COLS = 96
  const WORLD_PER_M = TARGET_EXAGGERATION / SURF_MAX_M
  const aTLon: number[] = []
  const aElevFrac: number[] = []
  // `position` is only used for Three.js's bounding-sphere computation
  // (so the mesh isn't frustum-culled). Real per-frame positions come
  // from the vertex shader's uCutLatRad transform — but if `position`
  // is all (0,0,0), the bounding sphere has zero radius at the origin
  // and the mesh gets culled the moment the camera doesn't look at
  // origin. Bake the CANONICAL NL_LAT positions in here so the
  // bounding sphere covers a realistic slab volume; the vertex shader
  // ignores these values and recomputes from uCutLatRad anyway.
  const positions: number[] = []
  const indices: number[] = []
  const canonCosLat = Math.cos(NORTH_LAKE_LAT)
  const canonSinLat = Math.sin(NORTH_LAKE_LAT)

  for (let i = 0; i <= N_COLS; i++) {
    const tLon = i / N_COLS
    const lon = CH_SLAB_LON_W + tLon * (CH_SLAB_LON_E - CH_SLAB_LON_W)
    const cosLon = Math.cos(lon)
    const sinLon = Math.sin(lon)
    for (const elevM of [CH_SLAB_ELEV_MAX_M, CH_SLAB_ELEV_MIN_M]) {
      const r = GLOBE_RADIUS + elevM * WORLD_PER_M
      positions.push(r * canonCosLat * cosLon, r * canonCosLat * sinLon, r * canonSinLat)
    }
    // Two vertices per column: top (elevFrac=0 → max elev) and bottom
    // (elevFrac=1 → min elev). Vertex shader maps these to world space.
    aTLon.push(tLon); aElevFrac.push(0)
    aTLon.push(tLon); aElevFrac.push(1)
  }

  for (let i = 0; i < N_COLS; i++) {
    const v0 = i * 2
    const v1 = i * 2 + 1
    const v2 = (i + 1) * 2
    const v3 = (i + 1) * 2 + 1
    indices.push(v0, v1, v2, v2, v1, v3)
  }

  const geom = new THREE.BufferGeometry()
  geom.setAttribute('position',  new THREE.Float32BufferAttribute(positions, 3))
  geom.setAttribute('aTLon',     new THREE.Float32BufferAttribute(aTLon, 1))
  geom.setAttribute('aElevFrac', new THREE.Float32BufferAttribute(aElevFrac, 1))
  geom.setIndex(indices)

  const mat = new THREE.ShaderMaterial({
    uniforms: {
      uBedTex:      { value: bedTexture },
      uSurfTex:     { value: demTexture },
      uOpacity:     { value: 0 },
      uIdealize:    { value: 0 },
      uBedMin:      { value: BED_MIN_M },
      uBedMax:      { value: BED_MAX_M },
      uSurfMax:     { value: SURF_MAX_M },
      uElevMin:     { value: CH_SLAB_ELEV_MIN_M },
      uElevMax:     { value: CH_SLAB_ELEV_MAX_M },
      uCutLatRad:   { value: NORTH_LAKE_LAT },
      uLonW:        { value: CH_SLAB_LON_W },
      uLonE:        { value: CH_SLAB_LON_E },
      uMapLatS:     { value: BASEMAP_LAT_S },
      uMapLatN:     { value: BASEMAP_LAT_N },
      uMapLonW:     { value: BASEMAP_LON_W },
      uMapLonE:     { value: BASEMAP_LON_E },
      uWorldPerM:   { value: TARGET_EXAGGERATION / SURF_MAX_M },
      uGlobeRadius: { value: GLOBE_RADIUS },
      // ── Ch.1 slab effects (slabFx prop) ──
      uDrainT:            { value: 0 },       // 0..0.6 fracture descends, 0.6..1 bed layer spreads
      uFracTLon:          { value: 0.1849 },  // fracture tLon (default: North Lake)
      uPaintTex:          { value: null },    // Elmer tau_xx raster (x along-flow, y bed->surface)
      uPaintT:            { value: 0 },       // paint fade 0..1
      // Paint half-width in tLon units. Stretched (real topography,
      // "paint the cross section") vs accurate (idealized slab: the
      // raster's +/-50 km at its true 68.7°N ground scale). The shader
      // mixes between them with uIdealize so the un-stretch rides the
      // same lerp as the geometry morph. 0.07 puts the raster's central
      // 10-km patch at ±0.007 tLon — exactly the (narrowed) bed-water
      // spread, so the painted patch visibly aligns with the injected
      // water (the director asked for the patch stretched to match the injection).
      uPaintHalfStretch:  { value: 0.07 },
      uPaintHalfAccurate: { value: 0.026915 },
      // Idealized-slab visual tilt (m across the full slab span) so the
      // uniform slab still reads as flowing downhill. Not to scale.
      uTiltM:             { value: 900 },
      // 0..1 tilt removal + curvature unroll (beat 3→4 morph levels the
      // slab AND flattens the earth-curvature arc onto the tangent
      // plane at the fracture — the object becomes the flat model
      // domain before the seam handoff into the theory panel).
      uLevelT:            { value: 0 },
      // 0..1 crop to the ±40 km theory window + the window's
      // half-width in tLon units (40 km of arc at the NL latitude).
      uCropT:             { value: 0 },
      uCropHalf:          { value: CH_SLAB_CROP_HALF_TLON },
    },
    vertexShader: `
      attribute float aTLon;
      attribute float aElevFrac;
      varying vec2  vUv;
      varying float vLon;
      uniform float uCutLatRad;
      uniform float uLonW;
      uniform float uLonE;
      uniform float uElevMin;
      uniform float uElevMax;
      uniform float uWorldPerM;
      uniform float uGlobeRadius;
      uniform float uLevelT;
      uniform float uFracTLon;
      uniform float uCropT;
      uniform float uCropHalf;
      void main() {
        // Crop: columns beyond the ±40 km theory window slide
        // INTO its edges as uCropT rises — the cross-section condenses
        // to the simulation domain in place (uv follows, so collapsed
        // columns sample the edge longitude: no smear, no seam).
        float tEff = mix(aTLon,
                         clamp(aTLon, uFracTLon - uCropHalf, uFracTLon + uCropHalf),
                         uCropT);
        float lon  = mix(uLonW, uLonE, tEff);
        float elev = mix(uElevMax, uElevMin, aElevFrac);
        float r = uGlobeRadius + elev * uWorldPerM;
        float cosLat = cos(uCutLatRad);
        float sinLat = sin(uCutLatRad);
        vec3 pos = vec3(r * cosLat * cos(lon),
                        r * cosLat * sin(lon),
                        r * sinLat);
        // Curvature unroll (rides uLevelT): blend each column from its
        // position on the spherical arc to the tangent PLANE at the
        // fracture — the slab straightens into the flat model domain
        // (the theory panel's field rect is straight; without this the
        // seam would crossfade a bowed edge into a straight one).
        float lon0 = mix(uLonW, uLonE, uFracTLon);
        vec3 up = vec3(cosLat * cos(lon0), cosLat * sin(lon0), sinLat);
        vec3 east = vec3(-sin(lon0), cos(lon0), 0.0);
        float xArc = uGlobeRadius * cosLat * (lon - lon0);
        vec3 flatPos = up * r + east * xArc;
        pos = mix(pos, flatPos, uLevelT);
        // Pass aTLon to fragment via vUv (so the cell math below still
        // talks in 0..1 along-cut fraction), and lon explicitly for
        // texture sampling.
        vUv = vec2(tEff, aElevFrac);
        vLon = lon;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
      }
    `,
    fragmentShader: `
      varying vec2  vUv;
      varying float vLon;
      uniform sampler2D uBedTex;
      uniform sampler2D uSurfTex;
      uniform float uOpacity;
      uniform float uIdealize;
      uniform float uBedMin;
      uniform float uBedMax;
      uniform float uSurfMax;
      uniform float uElevMin;
      uniform float uElevMax;
      uniform float uCutLatRad;
      uniform float uLonW;
      uniform float uLonE;
      uniform float uMapLatS;
      uniform float uMapLatN;
      uniform float uMapLonW;
      uniform float uMapLonE;
      uniform float uDrainT;
      uniform float uFracTLon;
      uniform sampler2D uPaintTex;
      uniform float uPaintT;
      uniform float uPaintHalfStretch;
      uniform float uPaintHalfAccurate;
      uniform float uTiltM;
      uniform float uLevelT;

      void main() {
        float ourElev = mix(uElevMax, uElevMin, vUv.y);

        // Sample bed + surface textures at the CURRENT cut latitude and
        // this column's longitude. As the slider sweeps north, the slab
        // shows a different cross-section at each latitude — motivation
        // pattern, axis-flipped.
        float u_tex = (vLon       - uMapLonW) / (uMapLonE - uMapLonW);
        float v_tex = (uCutLatRad - uMapLatS) / (uMapLatN - uMapLatS);

        if (u_tex < 0.0 || u_tex > 1.0 || v_tex < 0.0 || v_tex > 1.0) {
          discard;
        }

        float bedNorm  = texture2D(uBedTex,  vec2(u_tex, v_tex)).r;
        float surfNorm = texture2D(uSurfTex, vec2(u_tex, v_tex)).r;
        float bedElev  = bedNorm  * (uBedMax - uBedMin) + uBedMin;
        float surfElev = surfNorm * uSurfMax;

        bedElev = max(bedElev, uElevMin + 30.0);

        // Idealised mode (Beat 2→3 in the old layout, unused in the
        // new Ch.1 flow but kept as a no-op when uIdealize=0). Pulls
        // the curves toward the slab-centre column's local values.
        float lakeBed = texture2D(uBedTex, vec2(
          (((uLonW + uLonE) * 0.5) - uMapLonW) / (uMapLonE - uMapLonW),
          v_tex
        )).r * (uBedMax - uBedMin) + uBedMin;
        lakeBed = max(lakeBed, uElevMin + 30.0);
        float lakeSrf = texture2D(uSurfTex, vec2(
          (((uLonW + uLonE) * 0.5) - uMapLonW) / (uMapLonE - uMapLonW),
          v_tex
        )).r * uSurfMax;
        bedElev  = mix(bedElev,  lakeBed, uIdealize);
        surfElev = mix(surfElev, lakeSrf, uIdealize);

        // Idealized-slab tilt: gentle along-flow slope (west high,
        // east low — matches the flow direction the streamline showed).
        // uLevelT removes it (the morph levels the object into the
        // theory panel's flat diagram proportions).
        float tilt = uIdealize * uTiltM * (0.5 - vUv.x) * (1.0 - uLevelT);
        bedElev  += tilt;
        surfElev += tilt;

        bool outsideMask = (surfNorm < 0.005);
        if (outsideMask) discard;

        // Cap visible bedrock at 300 m below the actual bed so the
        // tan band stays a thin floor, not a column-tall slab — the director
        // flagged that the bedrock dwarfing the Greenland surface was
        // the main visual problem with the old wider-range fill.
        const float BEDROCK_DEPTH_LIMIT_M = 300.0;
        if (ourElev < bedElev - BEDROCK_DEPTH_LIMIT_M) discard;

        // Surface outline only — the bed stays plain brown (the director
        // found the yellow-on-brown bed line confusing and distracting).
        // 60 m band ≈ half the old 140 m so the outline reads lighter.
        float GOLD_BAND_M = 60.0;
        vec3 GOLD = vec3(0.95, 0.74, 0.30);

        // ── North Lake, sitting on the surface at the future fracture ──
        // Parabolic basin (cartoon width/depth — the real lake is ~2 km
        // across, invisible at this framing). The water level falls as
        // the drain's phase-1 fracture descends, so clicking "drain the
        // lake" visibly empties the surface lake into the ice.
        // Same dark water blue as the drain column below (the director
        // wanted the lake colour to match the drainage animation's
        // water — that dark blue reads well).
        vec3 LAKE_BLUE = vec3(0.07, 0.26, 0.52);
        float LAKE_HALF_TLON = ${CH_SLAB_LAKE_HALF_TLON.toFixed(4)};
        float LAKE_DEPTH_M = 190.0;
        float lakeND = (vUv.x - uFracTLon) / LAKE_HALF_TLON;
        float lakeBasinDepth = LAKE_DEPTH_M * max(1.0 - lakeND * lakeND, 0.0);
        float lakeFill = 1.0 - clamp(uDrainT / 0.6, 0.0, 1.0);
        bool inLakeWater =
          ourElev <= surfElev &&
          ourElev > surfElev - lakeBasinDepth &&
          ourElev <= surfElev - (1.0 - lakeFill) * LAKE_DEPTH_M &&
          uIdealize < 0.5;
        if (inLakeWater) {
          gl_FragColor = vec4(LAKE_BLUE, uOpacity);
          return;
        }

        // NL basin RIM (the North Lake outline must stay visible through
        // the cutaway): a ~4 px line in North Lake's
        // beat-0 colour (HF green) just under the basin floor. It empties
        // WITH the water (gone once the lake drains),
        // and is never drawn under the paint or on the idealized slab.
        float dBasin = (surfElev - lakeBasinDepth) - ourElev; // > 0 below the floor
        // Distance in PIXELS (true gradient, not fwidth's L1 sum, so the
        // line keeps its width where the basin wall is steep).
        float pxB = dBasin / max(length(vec2(dFdx(dBasin), dFdy(dBasin))), 1e-4);
        // The rim goes WITH the water (lakeFill) —
        // once the lake has drained no green may remain in the section.
        float rimA = lakeFill * (1.0 - uPaintT) * step(uIdealize, 0.49)
                   * step(abs(lakeND), 1.0) * step(0.0, dBasin)
                   * (1.0 - smoothstep(3.2, 4.2, pxB))
                   * step(GOLD_BAND_M, surfElev - ourElev);
        if (rimA > 0.01) {
          gl_FragColor = vec4(mix(vec3(0.72, 0.84, 0.96), vec3(0.298, 0.686, 0.314), rimA), uOpacity);
          return;
        }

        if (ourElev < bedElev) {
          float t = clamp((bedElev - uBedMin) / (uBedMax - uBedMin), 0.0, 1.0);
          vec3 darkBed  = vec3(0.18, 0.11, 0.07);
          vec3 midBed   = vec3(0.55, 0.38, 0.24);
          vec3 lightBed = vec3(0.82, 0.74, 0.55);
          vec3 col = mix(darkBed, midBed, smoothstep(0.0, 0.5, t));
          col = mix(col, lightBed, smoothstep(0.5, 1.0, t));
          gl_FragColor = vec4(col, uOpacity);
        } else if (ourElev <= surfElev - GOLD_BAND_M) {
          vec3 ice = vec3(0.72, 0.84, 0.96);

          // ── Elmer tau_xx paint (Beat: "color the cross section") ──
          // Texture x spans [uFracTLon - half, uFracTLon + half] so the
          // patch center rides the fracture; y is bed(0) -> surface(1)
          // of the LOCAL column, so real topography stretches the field
          // and the idealized slab shows it undistorted.
          float paintHalf = mix(uPaintHalfStretch, uPaintHalfAccurate, uIdealize);
          // FLIPPED: at North Lake the ice flows WEST toward the margin,
          // so the simulation's +x (downstream) axis points west — i.e.
          // decreasing tLon. Tension (red, upstream) lands inland/east
          // of the fracture, compression seaward/west.
          float px = (uFracTLon - vUv.x) / (2.0 * paintHalf) + 0.5;
          float py = clamp((ourElev - bedElev) / max(surfElev - bedElev, 1.0), 0.0, 1.0);
          if (uPaintT > 0.001 && px >= 0.0 && px <= 1.0) {
            vec3 paint = texture2D(uPaintTex, vec2(px, py)).rgb;
            // Cartoon mode fades the paint's far field into plain ice
            // over the outer quarter so the visible perturbation hugs
            // the injected bed water; the idealized (accurate-scale)
            // slab keeps a crisp honest window.
            float fadeW = mix(0.22, 0.06, uIdealize);
            float edgeFade = smoothstep(0.0, fadeW, px) * smoothstep(1.0, 1.0 - fadeW, px);
            ice = mix(ice, paint, uPaintT * edgeFade);
          }

          // ── Water drain (Beat: "where does the water go?") ──
          // Phase 1 (uDrainT 0..0.6): a slim darker-blue column descends
          // the full-thickness fracture. Phase 2 (0.6..1): a thin water
          // layer spreads along the bed outward from the fracture foot.
          // Thinner column + narrower bed footprint (the director's ask).
          vec3 WATER = vec3(0.07, 0.26, 0.52);
          float FRAC_HALF = 0.0008;
          float descend = clamp(uDrainT / 0.6, 0.0, 1.0);
          float depthFrac = (surfElev - ourElev) / max(surfElev - bedElev, 1.0);
          if (uDrainT > 0.001 && abs(vUv.x - uFracTLon) < FRAC_HALF && depthFrac <= descend) {
            ice = WATER;
          }
          float spread = clamp((uDrainT - 0.6) / 0.4, 0.0, 1.0);
          if (spread > 0.001 && ourElev < bedElev + 60.0 && abs(vUv.x - uFracTLon) < spread * 0.007) {
            ice = WATER;
          }

          gl_FragColor = vec4(ice, uOpacity);
        } else if (ourElev <= surfElev) {
          gl_FragColor = vec4(GOLD, uOpacity);
        } else {
          discard;
        }
      }
    `,
    transparent: true,
    depthWrite: false,
    depthTest: false,
    side: THREE.DoubleSide,
  })

  const mesh = new THREE.Mesh(geom, mat)
  mesh.renderOrder = 5
  // Belt-and-suspenders: even with the canonical-NL position
  // bounding sphere, the vertex shader can move the slab south to
  // lat=59° (basemap edge) where the bounding-sphere check may
  // disagree with the actual rendered position. Skip culling.
  mesh.frustumCulled = false
  scene.add(mesh)
  chapterSlabMesh = mesh
  chapterSlabMat = mat

  // Catch up to whatever the parent's chapterReveal prop currently asks
  // for — if the deferred build completed AFTER the watcher fired,
  // applyChapterReveal returned early without setting slab uniforms,
  // so we'd be stuck at opacity=0.
  if (props.chapterReveal && chapterSlabMat) {
    chapterSlabMat.uniforms.uOpacity.value  = props.chapterReveal.slabOpacity ?? 1
    chapterSlabMat.uniforms.uIdealize.value = props.chapterReveal.idealize ?? 0
    chapterSlabMat.uniforms.uCutLatRad.value = slabLatRadFromCutLatDeg(props.chapterReveal.latDeg)
  }
  if (props.slabFx) applySlabFx(props.slabFx)
}

// ── Ch.1 slab effects (water drain + Elmer paint) ──
let slabPaintUrl: string | null = null
// Morph-variant-B spin (0..1 → 0..π about the radial axis at the
// fracture). Applied to the mesh quaternion each frame in animate().
let chapterSlabSpinT = 0
function applySlabFx(v: NonNullable<typeof props.slabFx>): void {
  if (!chapterSlabMat) return
  const u = chapterSlabMat.uniforms
  u.uFracTLon.value = v.fracTLon
  u.uDrainT.value = v.drainT
  u.uPaintT.value = v.paintT ?? 0
  u.uLevelT.value = v.levelT ?? 0
  u.uCropT.value = v.cropT ?? 0
  chapterSlabSpinT = v.spinT ?? 0
  if (v.paintUrl && v.paintUrl !== slabPaintUrl) {
    slabPaintUrl = v.paintUrl
    const tex = loadTexTracked(v.paintUrl)
    tex.colorSpace = THREE.SRGBColorSpace
    u.uPaintTex.value = tex
  }
}

watch(
  () => props.slabFx,
  (v) => {
    if (v) {
      applySlabFx(v)
    } else if (chapterSlabMat) {
      chapterSlabMat.uniforms.uDrainT.value = 0
      chapterSlabMat.uniforms.uPaintT.value = 0
      chapterSlabMat.uniforms.uCropT.value = 0
    }
  },
)

// ───────── Ch.2 simulation-domain tile ───────────────────────────────
// A 25 m-resolution DEM tile of ONE lake's Elmer/Ice model domain,
// flush on the Greenland surface: satellite color from the shared
// basemap (uv-windowed), relief + hillshade from the sim's own surface
// DEM, and the published elastic Δσ_t1 drape mixed in by uStressT. The
// surrounding ice sheet is carved away by the attachDemDisplacement
// sweep (uCarveT), the immune square exactly under this
// tile — so the tile reads as CARVED out of the greenland object.
let simTileMesh: THREE.Mesh | null = null
let simTileMat: THREE.MeshBasicMaterial | null = null
let simTileShader: { uniforms: any } | null = null
let simTileUrl: string | null = null
let simTileTextures: THREE.Texture[] = []
// The domain is a SOLID object — bed-topography underside +
// ice cross-section walls close the surface into a block the viewer
// can orbit (the director wanted a solid block, not a floating surface
// draped in empty space).
let simBedMesh: THREE.Mesh | null = null
let simBedMat: THREE.MeshBasicMaterial | null = null
let simBedShader: { uniforms: any } | null = null
let simWallMesh: THREE.Mesh | null = null
let simWallMat: THREE.MeshBasicMaterial | null = null
let simWallShader: { uniforms: any } | null = null
let simSurfDemImage: HTMLImageElement | null = null
let simBedDemImage: HTMLImageElement | null = null
// Anchor dirs for the hovering model buttons (window.__simDomainScreen).
let simAnchorDirs: THREE.Vector3[] = []
let simAnchorElevM = 0
// THUMBNAIL-ONLY render knobs for
// website/tools/render_bed_thumbs.mjs, which sets window.__simThumb
// before the page loads. Never set on the live site. `edges` draws a
// thin black tube along the prism's twelve edges (top profile, bed
// profile, four verticals) so the block reads as an object at card
// size; `arrowScale` grows the ice-flow arrow + tag.
function simThumb(): { edges?: boolean; edgeRadius?: number; arrowScale?: number; arrowOffset?: number } {
  return (window as any).__simThumb ?? {}
}
type SimEdgeSample = { lon: number; lat: number; surfM: number; bedM: number }
let simEdgeSamples: SimEdgeSample[][] = []
let simEdgeGroup: THREE.Group | null = null
let simEdgeExag = -1
let simEdgeMat: THREE.MeshBasicMaterial | null = null

/** Exact polyline curve (no smoothing) for TubeGeometry. */
class SimPolyline extends THREE.Curve<THREE.Vector3> {
  constructor(private pts: THREE.Vector3[]) {
    super()
  }
  getPoint(t: number, target = new THREE.Vector3()): THREE.Vector3 {
    const n = this.pts.length - 1
    const f = Math.min(Math.max(t, 0), 1) * n
    const i = Math.min(Math.floor(f), n - 1)
    return target.copy(this.pts[i]).lerp(this.pts[i + 1], f - i)
  }
}

function disposeSimEdges(): void {
  if (!simEdgeGroup) return
  scene.remove(simEdgeGroup)
  simEdgeGroup.traverse((c) => {
    ;(c as THREE.Mesh).geometry?.dispose()
  })
  simEdgeGroup = null
  simEdgeExag = -1
}

/** Thumbnail mode only: the prism outline at the CURRENT exaggeration
 *  (CPU positions — rebuilt from the per-frame hook if exag moves). */
function buildSimEdges(): void {
  disposeSimEdges()
  if (!simThumb().edges || simEdgeSamples.length !== 4) return
  simEdgeMat ??= new THREE.MeshBasicMaterial({ color: 0x0a0a0a })
  const at = (q: SimEdgeSample, elevM: number) => simElevPos(q.lon, q.lat, elevM)
  const e0 = simEdgeSamples[0]
  const L = at(e0[0], e0[0].surfM).distanceTo(at(e0[e0.length - 1], e0[e0.length - 1].surfM))
  const r = L * (simThumb().edgeRadius ?? 0.003)
  const tube = (pts: THREE.Vector3[], segs: number) =>
    new THREE.Mesh(new THREE.TubeGeometry(new SimPolyline(pts), segs, r, 6, false), simEdgeMat!)
  const g = new THREE.Group()
  for (const e of simEdgeSamples) {
    g.add(tube(e.map((q) => at(q, q.surfM)), e.length * 2))
    g.add(tube(e.map((q) => at(q, q.bedM)), e.length * 2))
    g.add(tube([at(e[0], e[0].surfM), at(e[0], e[0].bedM)], 2))
  }
  g.renderOrder = 6
  g.traverse((c) => {
    c.frustumCulled = false
  })
  scene.add(g)
  simEdgeGroup = g
  simEdgeExag = currentExag
}
// Additional-Work MGSIM page: the block's bed and its
// stress result are HOT-SWAPPABLE — the page flips through bed
// realizations without rebuilding the tile. These track what is
// currently bound so applySimDomain can diff the payload.
let simBedUrl: string | null = null
let simAltUrl: string | null = null
let simAltUrlB: string | null = null
let simBedPalTex: THREE.Texture | null = null
let simBedPalUrl: string | null = null

type SimDomainD = NonNullable<typeof props.simDomain>

/** The hypsometric bed ramp (256×1 PNG baked next to the side panels so
 *  globe and panels agree to the byte). A 1×1 white fallback keeps the
 *  sampler bound for Ch.2, which never sets a palette. */
function ensureBedPalette(d: SimDomainD): THREE.Texture {
  const url = d.bedPaletteUrl ?? null
  if (url && url !== simBedPalUrl) {
    simBedPalTex?.dispose()
    const t = loadTexTracked(url)
    t.colorSpace = THREE.SRGBColorSpace
    t.generateMipmaps = false
    t.minFilter = THREE.LinearFilter
    t.magFilter = THREE.LinearFilter
    t.wrapS = THREE.ClampToEdgeWrapping
    simBedPalTex = t
    simBedPalUrl = url
  }
  if (!simBedPalTex) {
    const t = new THREE.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1)
    t.needsUpdate = true
    simBedPalTex = t
  }
  return simBedPalTex
}

function disposeSimWalls(): void {
  disposeSimEdges()
  simEdgeSamples = []
  if (!simWallMesh) return
  scene.remove(simWallMesh)
  simWallMesh.geometry.dispose()
  if (simWallShader) {
    const i = elevatedShaders.indexOf(simWallShader as any)
    if (i >= 0) elevatedShaders.splice(i, 1)
  }
  simWallMat?.dispose()
  simWallMesh = null
  simWallMat = null
  simWallShader = null
}

/** Swap the bed DEM under a live block: new RG16 texture into the bed
 *  shader, then the ice walls (CPU-sampled from the bed image) and the
 *  basal-patch overlay (sampled onto the bed) rebuild against it. */
function swapSimBed(d: SimDomainD): void {
  simBedUrl = d.bedUrl
  if (!simBedShader) return // no block yet — buildSimTile binds it
  const old = simBedShader.uniforms.uDemTex.value as THREE.Texture | null
  const releaseOld = () => {
    if (!old || [...simTwinCache.values()].includes(old)) return
    const i = simTileTextures.indexOf(old)
    if (i >= 0) simTileTextures.splice(i, 1)
    old.dispose()
  }
  // The teaser's cycle: a preloaded bed swaps in THIS frame.
  const cached = simTwinReady(d.bedUrl)
  if (cached) {
    simBedDemImage = cached.image as HTMLImageElement
    simBedShader.uniforms.uDemTex.value = cached
    disposeSimWalls()
    maybeBuildSimWalls(d)
    disposeSimBc()
    disposeSimOutline() // its bottom edge follows the new bed
    if (old !== cached) releaseOld()
    return
  }
  const tex = loadTexTracked(d.bedUrl, (t) => {
    if (simBedUrl !== d.bedUrl || !simBedShader) {
      t.dispose()
      return // superseded while loading
    }
    simBedDemImage = t.image as HTMLImageElement
    simBedShader.uniforms.uDemTex.value = t
    disposeSimWalls()
    maybeBuildSimWalls(d)
    disposeSimBc() // the animate loop rebuilds it on the new bed
    disposeSimOutline() // its bottom edge follows the new bed
    releaseOld()
  })
  tex.colorSpace = THREE.NoColorSpace
  tex.minFilter = THREE.NearestFilter
  tex.magFilter = THREE.NearestFilter
  tex.generateMipmaps = false
  simTileTextures.push(tex)
}

/** Swap the third (alt) stress drape — a realization's no-patch σ_t1. */
function swapSimAlt(d: SimDomainD): void {
  simAltUrl = d.stressAltUrl ?? null
  if (!simTileShader) return
  const u = simTileShader.uniforms
  if (!d.stressAltUrl) {
    u.uStressTexA.value = u.uStressTexV.value
    return
  }
  const tex = loadTexTracked(d.stressAltUrl, (t) => {
    if (simAltUrl !== d.stressAltUrl || !simTileShader) {
      t.dispose()
      return
    }
    const prev = u.uStressTexA.value as THREE.Texture | null
    u.uStressTexA.value = t
    if (prev && prev !== u.uStressTexV.value) {
      const i = simTileTextures.indexOf(prev)
      if (i >= 0) simTileTextures.splice(i, 1)
      prev.dispose()
    }
    // Ch.2 results (σ_t2 beats): the section fades the alt drape in only
    // once it is really in the slot — never toward the previous texture.
    window.dispatchEvent(new CustomEvent('sim-alt-ready', { detail: d.stressAltUrl }))
  })
  tex.colorSpace = THREE.SRGBColorSpace
  simTileTextures.push(tex)
}

/** Swap the fourth (second alt) stress drape — Ch.2's crossfade partner. */
function swapSimAltB(d: SimDomainD): void {
  simAltUrlB = d.stressAltUrlB ?? null
  if (!simTileShader?.uniforms.uStressTexB) return
  const u = simTileShader.uniforms
  if (!d.stressAltUrlB) {
    u.uStressTexB.value = u.uStressTexV.value
    return
  }
  const tex = loadTexTracked(d.stressAltUrlB, (t) => {
    if (simAltUrlB !== d.stressAltUrlB || !simTileShader) {
      t.dispose()
      return
    }
    const prev = u.uStressTexB.value as THREE.Texture | null
    u.uStressTexB.value = t
    if (prev && prev !== u.uStressTexV.value && prev !== u.uStressTexA.value) {
      const i = simTileTextures.indexOf(prev)
      if (i >= 0) simTileTextures.splice(i, 1)
      prev.dispose()
    }
    window.dispatchEvent(new CustomEvent('sim-altb-ready', { detail: d.stressAltUrlB }))
  })
  tex.colorSpace = THREE.SRGBColorSpace
  simTileTextures.push(tex)
}

// Shared satellite-color crop for the sim tiles. An earlier build gave each
// tile the FULL mid-res basemap as a fresh texture — THREE resized the
// 16380×6300 image to GPU limits on the main thread at drain-click,
// freezing the renderer for seconds and reducing the whole drain
// choreography to ~5 rendered frames ("choppy"). Instead: one small
// canvas crop of the CW-lakes window, cut once from the (browser-
// cached) basemap image, reused by every tile via offset/repeat.
const SIM_BASE_WIN = {
  lonW: (-50.9 * Math.PI) / 180,
  lonE: (-47.5 * Math.PI) / 180,
  latS: (69.0 * Math.PI) / 180,
  latN: (71.5 * Math.PI) / 180,
}
let simBaseCropTex: THREE.CanvasTexture | null = null
function ensureSimBaseCropTex(): THREE.CanvasTexture {
  if (simBaseCropTex) return simBaseCropTex
  // Opaque snow-white placeholder until the crop is drawn. NOTE: the
  // ready crop replaces this with a FRESH texture object — resizing
  // the placeholder's canvas + needsUpdate left the GPU copy stale
  // (deep links rendered the tile fully transparent).
  const placeholder = document.createElement('canvas')
  placeholder.width = 8
  placeholder.height = 8
  const pctx = placeholder.getContext('2d')!
  pctx.fillStyle = '#eceff1'
  pctx.fillRect(0, 0, 8, 8)
  const tex = new THREE.CanvasTexture(placeholder)
  tex.colorSpace = THREE.SRGBColorSpace
  tex.anisotropy = renderer.capabilities.getMaxAnisotropy()
  simBaseCropTex = tex
  const cropFrom = (img: HTMLImageElement | ImageBitmap): void => {
    const iw = (img as HTMLImageElement).naturalWidth || img.width
    const ih = (img as HTMLImageElement).naturalHeight || img.height
    const u0 = (SIM_BASE_WIN.lonW - BASEMAP_LON_W) / (BASEMAP_LON_E - BASEMAP_LON_W)
    const u1 = (SIM_BASE_WIN.lonE - BASEMAP_LON_W) / (BASEMAP_LON_E - BASEMAP_LON_W)
    const v0 = (SIM_BASE_WIN.latS - BASEMAP_LAT_S) / (BASEMAP_LAT_N - BASEMAP_LAT_S)
    const v1 = (SIM_BASE_WIN.latN - BASEMAP_LAT_S) / (BASEMAP_LAT_N - BASEMAP_LAT_S)
    const sx = Math.floor(u0 * iw)
    const sw = Math.max(1, Math.ceil((u1 - u0) * iw))
    // Image row 0 = north; v measures from south.
    const sy = Math.floor((1 - v1) * ih)
    const sh = Math.max(1, Math.ceil((v1 - v0) * ih))
    const canvas = document.createElement('canvas')
    canvas.width = sw
    canvas.height = sh
    canvas.getContext('2d')!.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh)
    const ready = new THREE.CanvasTexture(canvas)
    ready.colorSpace = THREE.SRGBColorSpace
    ready.anisotropy = renderer.capabilities.getMaxAnisotropy()
    ready.offset.copy(tex.offset)
    ready.repeat.copy(tex.repeat)
    const old = simBaseCropTex
    simBaseCropTex = ready
    if (simTileMat && simTileMat.map === old) {
      simTileMat.map = ready
      simTileMat.needsUpdate = true
    }
    old?.dispose()
    ;(window as any).__cropReady = { w: sw, h: sh }
    ;(window as any).__cropCanvas = canvas
  }
  const cropUrl = mediaUrl('shared/greenland_basemap.png')
  const viaImg = (): void => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => cropFrom(img)
    img.onerror = (e) => {
      ;(window as any).__cropReady = { error: String(e) }
    }
    img.src = cropUrl
  }
  // The 10400 × 4000 basemap decoded OFF the main thread (a performance
  // pass found drawImage(<img>) decoding it on the main thread — the
  // ~0.9 s block on Chapter 2's first popup, where the block warm-builds).
  // Image orientation, no flip: the crop reads image rows. Same CORS
  // request as the <img> path (same cache entry); any failure falls back.
  if (bitmapDecodeOk) {
    fetch(cropUrl, { mode: 'cors', credentials: 'same-origin' })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.blob()
      })
      .then((b) => createImageBitmap(b))
      .then((bmp) => {
        cropFrom(bmp)
        bmp.close()
      })
      .catch((e) => {
        console.warn('[globe] basemap crop bitmap decode failed, loading it as an image:', e)
        viaImg()
      })
  } else viaImg()
  return tex
}

// ── Drainage-catalog overlay ──
// The paper's Fig-1 lake outlines (mechanism-colored, numbered) drawn
// onto a canvas texture in the tile's uv frame; rebuilt whenever the
// hover/pin state changes so the active lake glows gold. The parsed
// catalog also drives pointer hit-testing (uv point-in-polygon).
let simLakesData: SimCatalogLake[] | null = null
let simLakesUrl: string | null = null
let simLakeHoverCw: number | null = null
let simLakePinCw: number | null = null
// The outlines render on their OWN overlay meshes. HARD-WON
// lesson: on this GPU stack (Chromium ANGLE/Metal + this three
// version), a texture bound into a COMPILED program never re-uploads
// — not via needsUpdate, not via fresh-texture swaps, not via
// material.needsUpdate recompiles, not via renderer.initTexture. The
// canvas held the gold ring; the screen never did. So the hover
// highlight is N+1 PRE-DRAWN textures on N+1 overlay meshes (base
// outlines + one per catalog lake with that lake gilded), and hover
// just flips mesh VISIBILITY — first-use uploads work, and visibility
// toggles are rock solid.
interface SimLakesOverlay {
  cw: number | null
  mesh: THREE.Mesh
  mat: THREE.MeshBasicMaterial
}
let simLakesOverlays: SimLakesOverlay[] = []

const SIM_LAKES_PX = 1024

function renderSimLakesCanvas(activeCw: number | null): HTMLCanvasElement {
  const S = SIM_LAKES_PX
  const canvas = document.createElement('canvas')
  canvas.width = S
  canvas.height = S
  const ctx = canvas.getContext('2d')!
  const data = simLakesData ?? []
  // Draw non-active lakes first so the gilded one sits on top.
  const ordered = [...data].sort(
    (a, b) => Number(a.cw === activeCw) - Number(b.cw === activeCw),
  )
  // The numbers' spots, solved ONCE in catalog order (so a
  // hover variant never moves them): above the polygon, or below it when
  // that would overlap a number already placed (the bigger type made
  // close neighbours, e.g. 2311 · 2296, collide).
  ctx.font = '700 34px Inter, system-ui, sans-serif'
  const placed: { x0: number; x1: number; y0: number; y1: number }[] = []
  const labelAt = new Map<SimCatalogLake, [number, number]>()
  for (const lk of data) {
    const vs = lk.rings_uv.flat().map((pt) => pt[1])
    const lx = lk.centroid_uv[0] * S
    const hw = ctx.measureText(String(lk.num)).width / 2 + 4
    const above = Math.max(38, Math.min(...vs) * S - 10)
    const below = Math.max(...vs) * S + 44
    const box = (y: number) => ({ x0: lx - hw, x1: lx + hw, y0: y - 34, y1: y + 2 })
    const hit = (b: ReturnType<typeof box>) =>
      placed.some((o) => b.x0 < o.x1 && b.x1 > o.x0 && b.y0 < o.y1 && b.y1 > o.y0)
    const ly = hit(box(above)) && !hit(box(below)) && below < S - 4 ? below : above
    placed.push(box(ly))
    labelAt.set(lk, [lx, ly])
  }
  for (const lk of ordered) {
    const st = SIM_LAKE_STYLE[lk.cls]
    const isActive = lk.cw === activeCw
    for (const ring of lk.rings_uv) {
      ctx.beginPath()
      for (let i = 0; i < ring.length; i++) {
        const [u, v] = ring[i]
        if (i === 0) ctx.moveTo(u * S, v * S)
        else ctx.lineTo(u * S, v * S)
      }
      ctx.closePath()
      // Dark halo for contrast on bright snow (paper: black stroke).
      ctx.setLineDash(st.dash)
      ctx.lineJoin = 'round'
      ctx.shadowBlur = 0
      ctx.strokeStyle = 'rgba(0,0,0,0.8)'
      ctx.lineWidth = isActive ? 7 : 5.5
      ctx.stroke()
      if (isActive) {
        ctx.shadowColor = SIM_HOVER_GOLD
        ctx.shadowBlur = 14
      }
      ctx.strokeStyle = isActive ? SIM_HOVER_GOLD : st.color
      ctx.lineWidth = isActive ? 4.5 : 3.2
      ctx.stroke()
      ctx.shadowBlur = 0
    }
    // Catalog number above the polygon (paper's default placement).
    ctx.setLineDash([])
    // For the projector: the numbers were ~13 px on screen at 1440 —
    // larger and bolder, and the dark 'no drainage' ink gets a LIGHT halo
    // (a black number in a black halo vanished on the white drape).
    ctx.font = `700 ${isActive ? 38 : 34}px Inter, system-ui, sans-serif`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'bottom'
    const [lx, ly] = labelAt.get(lk)!
    ctx.lineWidth = 7
    ctx.strokeStyle = lk.cls === 'black' && !isActive ? 'rgba(255,255,255,0.85)' : 'rgba(0,0,0,0.8)'
    ctx.strokeText(String(lk.num), lx, ly)
    ctx.fillStyle = isActive ? SIM_HOVER_GOLD : st.color
    ctx.fillText(String(lk.num), lx, ly)
  }
  return canvas
}

/** The tile's surface DEM texture (buildSimTile), for the lake drapes. */
let simSurfDemTex: THREE.Texture | null = null
function disposeSimLakesOverlays(): void {
  for (const o of simLakesOverlays) {
    scene.remove(o.mesh)
    o.mat.map?.dispose()
    o.mat.dispose()
  }
  simLakesOverlays = []
}

/** Build the N+1 pre-drawn overlay meshes (base + one gilded variant
 *  per catalog lake). Needs the tile mesh (shared geometry + DEM
 *  displacement) AND the catalog data. */
function buildSimLakesOverlays(): void {
  if (!simTileMesh || !simLakesData || simLakesOverlays.length > 0) return
  const geom = simTileMesh.geometry
  // The tile's surface DEM straight from buildSimTile — NOT the tile
  // shader's uniform: that shader only exists after the tile's first
  // compile, and a catalog fetch that beat it (a slow deep link) draped
  // the outlines at elevation 0, buried under the bed.
  const demTex = simSurfDemTex ?? ((simTileShader?.uniforms?.uDemTex?.value ?? null) as THREE.Texture | null)
  const variants: (number | null)[] = [
    null,
    ...simLakesData.map((lk) => lk.cw),
  ]
  for (const cw of variants) {
    const canvas = renderSimLakesCanvas(cw)
    const tex = new THREE.CanvasTexture(canvas)
    tex.colorSpace = THREE.SRGBColorSpace
    const mat = new THREE.MeshBasicMaterial({
      map: tex,
      transparent: true,
      opacity: props.simDomain?.lakesA ?? 0,
      depthWrite: false,
      side: THREE.DoubleSide,
    })
    mat.onBeforeCompile = (shader) => {
      shader.uniforms.uDemTex = { value: demTex }
      shader.uniforms.uExaggeration = { value: currentExag }
      shader.uniforms.uHillshadeStrength = { value: 0 }
      shader.vertexShader = shader.vertexShader
        .replace(
          '#include <common>',
          `#include <common>
           uniform sampler2D uDemTex;
           uniform float uExaggeration;
           float decodeDemRG(vec4 rgba) {
             return (rgba.r * 65280.0 + rgba.g * 255.0) / 65535.0;
           }
           float sampleTileDem(vec2 uv) {
             vec2 texSize = vec2(1024.0, 1024.0);
             vec2 px = uv * texSize - 0.5;
             vec2 pxFloor = floor(px);
             vec2 t = px - pxFloor;
             vec2 uv00 = (pxFloor + 0.5) / texSize;
             float e00 = decodeDemRG(texture2D(uDemTex, uv00));
             float e10 = decodeDemRG(texture2D(uDemTex, uv00 + vec2(1.0 / texSize.x, 0.0)));
             float e01 = decodeDemRG(texture2D(uDemTex, uv00 + vec2(0.0, 1.0 / texSize.y)));
             float e11 = decodeDemRG(texture2D(uDemTex, uv00 + vec2(1.0 / texSize.x, 1.0 / texSize.y)));
             return mix(mix(e00, e10, t.x), mix(e01, e11, t.x), t.y);
           }`,
        )
        .replace(
          '#include <begin_vertex>',
          `vec3 transformed = vec3( position );
           float elev = sampleTileDem(uv) + 18.0 / 3500.0;
           transformed += normalize(position) * elev * uExaggeration;`,
        )
      elevatedShaders.push(shader)
    }
    mat.needsUpdate = true
    const mesh = new THREE.Mesh(geom, mat)
    mesh.rotation.x = Math.PI / 2
    // Above the block's gold rim + its ink (6/7) — the director wanted the
    // lake id labels on top of the simulation domain outlines
    // (a number near an edge used to be cut by the rim); still under the
    // centre-lake marker + halo (11/12).
    mesh.renderOrder = 8
    mesh.frustumCulled = false
    // Every variant renders its FIRST frames at near-zero opacity so
    // its texture uploads while first-use uploads still work; the
    // visibility switcher takes over immediately after.
    mesh.visible = true
    mat.opacity = 0.001
    scene.add(mesh)
    simLakesOverlays.push({ cw, mesh, mat })
  }
  // Warm window: every variant stays visible at ~zero opacity for its
  // first frames so all textures upload; the switcher takes over after.
  simLakesWarmUntil = performance.now() + 350
  const builtFor = simLakesUrl
  window.setTimeout(() => {
    updateSimLakesVisibility()
    // Which lakes file's outlines + numbers are showing (Ch.2's hop
    // lifts its veil only once the new block has them).
    if (simLakesUrl === builtFor) (window as any).__simLakesReady = builtFor
  }, 400)
}

let simLakesWarmUntil = 0

function updateSimLakesVisibility(): void {
  if (simLakesOverlays.length === 0) return
  if (performance.now() < simLakesWarmUntil) return
  // The director's spec: the gold outline follows the HOVER only — it
  // clears the moment the pointer leaves the lake. A click still pins
  // the stats card (SimLakeCard), but never the glow.
  const active = simLakeHoverCw
  const a = props.simDomain?.lakesA ?? 0
  const hasActive = simLakesOverlays.some((o) => o.cw === active)
  for (const o of simLakesOverlays) {
    const isCurrent = hasActive && active !== null ? o.cw === active : o.cw === null
    o.mesh.visible = isCurrent && a > 0.005
    o.mat.opacity = a
  }
}

function ensureSimLakes(d: NonNullable<typeof props.simDomain>): void {
  if (simLakesUrl !== d.lakesUrl) {
    simLakesUrl = d.lakesUrl
    simLakesData = null
    simLakeHoverCw = null
    simLakePinCw = null
    disposeSimLakesOverlays()
    const url = d.lakesUrl
    fetch(url)
      .then((r) => (r.ok ? r.json() : null))
      .then((j: SimLakesFile | null) => {
        if (!j || simLakesUrl !== url) return
        simLakesData = j.lakes
        buildSimLakesOverlays()
      })
      .catch(() => {})
  } else if (simLakesData) {
    buildSimLakesOverlays()
  }
}

function pointInRing(u: number, v: number, ring: [number, number][]): boolean {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i]
    const [xj, yj] = ring[j]
    if (yi > v !== yj > v && u < ((xj - xi) * (v - yi)) / (yj - yi) + xi) {
      inside = !inside
    }
  }
  return inside
}

/** Catalog lake under the pointer (tile-uv space), or null. Hit pads
 *  small polygons by testing the exact ring first, then a loose
 *  centroid radius so slim lakes stay hoverable.
 *
 *  NOTE the intersection is a manual ray–sphere solve at the LIFTED
 *  surface radius — raycasting the mesh hits the un-displaced
 *  geometry (the DEM lift lives in the vertex shader), which at the
 *  oblique inspect framing lands the hit a couple of km north of
 *  where the pointer visually sits (an earlier bug: hovers never hit). */
function simLakeAtPointer(): SimCatalogLake | null {
  if (!simTileMesh || !camera || !simLakesData) return null
  const d = props.simDomain
  if (!d || (d.lakesA ?? 0) < 0.2) return null
  raycaster.setFromCamera(mouseNDC, camera)
  const rSurf = GLOBE_RADIUS + (simAnchorElevM / SURF_MAX_M) * currentExag
  const o = raycaster.ray.origin
  const dir = raycaster.ray.direction
  // |o + t·dir|² = rSurf² → t² + 2(o·dir)t + (|o|² − rSurf²) = 0
  const b = o.dot(dir)
  const c = o.lengthSq() - rSurf * rSurf
  const disc = b * b - c
  if (disc < 0) return null
  const sq = Math.sqrt(disc)
  // Nearest intersection in front of the camera (outside-looking-in
  // takes −b−√, inside-looking-out takes −b+√).
  let t = -b - sq
  if (t < 0) t = -b + sq
  if (t < 0) return null
  const p = o.clone().addScaledVector(dir, t)
  const lat = (Math.asin(p.z / p.length()) * 180) / Math.PI
  const lon = (Math.atan2(p.y, p.x) * 180) / Math.PI
  const u = (lon - d.bbox.lonW) / (d.bbox.lonE - d.bbox.lonW)
  const v = (d.bbox.latN - lat) / (d.bbox.latN - d.bbox.latS)
  if (u < -0.05 || u > 1.05 || v < -0.05 || v > 1.05) return null
  let best: SimCatalogLake | null = null
  for (const lk of simLakesData) {
    if (lk.rings_uv.some((ring) => pointInRing(u, v, ring))) {
      best = lk
      break
    }
  }
  if (!best) {
    let bestD = 0.018 // ~loose pick radius in uv (~0.27 km per 0.018)
    for (const lk of simLakesData) {
      const dx = u - lk.centroid_uv[0]
      const dy = v - lk.centroid_uv[1]
      const dist = Math.hypot(dx, dy)
      if (dist < bestD) {
        bestD = dist
        best = lk
      }
    }
  }
  return best
}

function setSimLakeHover(lake: SimCatalogLake | null): void {
  const cw = lake?.cw ?? null
  if (cw === simLakeHoverCw) return
  simLakeHoverCw = cw
  updateSimLakesVisibility()
  emit('sim-lake-hover', lake)
}

// Debug probe: why is/isn't the pointer hitting a catalog lake?
;(window as any).__simHoverProbe = () => {
  if (!simTileMesh || !camera) return { stage: 'no-mesh' }
  if (!simLakesData) return { stage: 'no-data', url: simLakesUrl }
  const lakesA = props.simDomain?.lakesA ?? 0
  raycaster.setFromCamera(mouseNDC, camera)
  const hits = raycaster.intersectObject(simTileMesh, false)
  return {
    stage: 'ok',
    lakesA,
    mouseNDC: [mouseNDC.x, mouseNDC.y],
    nHits: hits.length,
    uv: hits[0]?.uv ? [hits[0].uv.x, hits[0].uv.y] : null,
    hoverCw: simLakeHoverCw,
    hit: simLakeAtPointer()?.num ?? null,
    nOverlays: simLakesOverlays.length,
    meshMatSame: simTileMesh ? simTileMesh.material === simTileMat : null,
    meshInScene: simTileMesh ? simTileMesh.parent === scene : null,
    simMeshCount: scene.children.filter(
      (c) => (c as THREE.Mesh).isMesh && c.renderOrder === 3,
    ).length,
  }
}

// Phase-space panel hover → glow the lake on the block (no emit back:
// the panel already owns that hover state).
watch(
  () => props.simLakeHighlight,
  (num) => {
    const cw = num != null ? num - 1523 : null
    if (cw === simLakeHoverCw) return
    simLakeHoverCw = cw
    updateSimLakesVisibility()
  },
)

function disposeSimTile(): void {
  if (!simTileMesh) return
  disposeSimLakesOverlays()
  disposeSimEdges()
  simEdgeSamples = []
  disposeSimFlow()
  disposeSimBc()
  disposeSimOutline()
  disposeSimAxes()
  simAxesCorner = -1
  simOutlineBornAt = 0
  disposeSimMatWarmMesh()
  disposeSimMarker()
  for (const [mesh, mat, sh] of [
    [simTileMesh, simTileMat, simTileShader],
    [simBedMesh, simBedMat, simBedShader],
    [simWallMesh, simWallMat, simWallShader],
  ] as const) {
    if (mesh) {
      scene.remove(mesh)
      mesh.geometry.dispose()
    }
    if (sh) {
      const idx = elevatedShaders.indexOf(sh as any)
      if (idx >= 0) elevatedShaders.splice(idx, 1)
    }
    mat?.dispose()
  }
  for (const t of simTileTextures) t.dispose()
  simTileTextures = []
  disposeSimTwinCache()
  simTileMesh = null
  simTileMat = null
  simTileShader = null
  simBedMesh = null
  simBedMat = null
  simBedShader = null
  simWallMesh = null
  simWallMat = null
  simWallShader = null
  simSurfDemImage = null
  simSurfDemTex = null
  simBedDemImage = null
  simAnchorDirs = []
  simTileUrl = null
  simBedUrl = null
  simAltUrl = null
  simAltUrlB = null
  simLakesData = null
  simLakesUrl = null
  if (simLakeHoverCw !== null) emit('sim-lake-hover', null)
  simLakeHoverCw = null
  simLakePinCw = null
}

function buildSimTile(d: NonNullable<typeof props.simDomain>): void {
  disposeSimTile()
  const phiStart = Math.PI + (d.bbox.lonW * Math.PI) / 180
  const phiLength = ((d.bbox.lonE - d.bbox.lonW) * Math.PI) / 180
  const thetaStart = Math.PI / 2 - (d.bbox.latN * Math.PI) / 180
  const thetaLength = ((d.bbox.latN - d.bbox.latS) * Math.PI) / 180
  const geom = new THREE.SphereGeometry(
    GLOBE_RADIUS, 256, 256, phiStart, phiLength, thetaStart, thetaLength,
  )

  const demTex = loadTexTracked(d.demUrl, (t) => {
    simSurfDemImage = t.image as HTMLImageElement
    maybeBuildSimWalls(d)
  })
  demTex.colorSpace = THREE.NoColorSpace
  demTex.minFilter = THREE.NearestFilter
  demTex.magFilter = THREE.NearestFilter
  demTex.generateMipmaps = false
  simSurfDemTex = demTex
  const stressTex = loadTexTracked(d.stressUrl)
  stressTex.colorSpace = THREE.SRGBColorSpace
  const stressTexV = loadTexTracked(d.stressViscousUrl)
  stressTexV.colorSpace = THREE.SRGBColorSpace
  // The alt drape slot starts bound to the viscous texture
  // (so the sampler is always valid) unless the payload names one.
  // (Ch.2 waits on 'sim-alt-ready' before fading a slot in — announce the
  // build's own loads too, so a wait on a fresh tile is never stranded.)
  const altReady = (evt: string, url: string | undefined) => () => {
    if (url) window.dispatchEvent(new CustomEvent(evt, { detail: url }))
  }
  const stressTexA = d.stressAltUrl ? loadTexTracked(d.stressAltUrl, altReady('sim-alt-ready', d.stressAltUrl)) : stressTexV
  if (d.stressAltUrl) stressTexA.colorSpace = THREE.SRGBColorSpace
  simAltUrl = d.stressAltUrl ?? null
  // The second alt slot (Ch.2's crossfades between two absolute fields).
  const stressTexB = d.stressAltUrlB ? loadTexTracked(d.stressAltUrlB, altReady('sim-altb-ready', d.stressAltUrlB)) : stressTexV
  if (d.stressAltUrlB) stressTexB.colorSpace = THREE.SRGBColorSpace
  simAltUrlB = d.stressAltUrlB ?? null
  // Sentinel-2 truecolor faces: pre-drainage (the zoom's
  // landing face — the real lake, full) and post-drainage ("Drain the
  // lake" crossfades to it).
  const s2PreTex = loadTexTracked(d.s2PreUrl)
  s2PreTex.colorSpace = THREE.SRGBColorSpace
  s2PreTex.anisotropy = renderer.capabilities.getMaxAnisotropy()
  const s2PostTex = loadTexTracked(d.s2PostUrl)
  s2PostTex.colorSpace = THREE.SRGBColorSpace
  s2PostTex.anisotropy = renderer.capabilities.getMaxAnisotropy()
  ensureSimLakes(d)
  // Satellite color from the shared CW-window crop (see
  // ensureSimBaseCropTex — one small canvas, uv-windowed per tile).
  // Mid-res suffices: the 25 m DEM hillshade carries the close-up
  // detail.
  const baseTex = ensureSimBaseCropTex()
  const lonWr = (d.bbox.lonW * Math.PI) / 180
  const lonEr = (d.bbox.lonE * Math.PI) / 180
  const latSr = (d.bbox.latS * Math.PI) / 180
  const latNr = (d.bbox.latN * Math.PI) / 180
  baseTex.offset.set(
    (lonWr - SIM_BASE_WIN.lonW) / (SIM_BASE_WIN.lonE - SIM_BASE_WIN.lonW),
    (latSr - SIM_BASE_WIN.latS) / (SIM_BASE_WIN.latN - SIM_BASE_WIN.latS),
  )
  baseTex.repeat.set(
    (lonEr - lonWr) / (SIM_BASE_WIN.lonE - SIM_BASE_WIN.lonW),
    (latNr - latSr) / (SIM_BASE_WIN.latN - SIM_BASE_WIN.latS),
  )
  // The shared crop + lakes canvas are NOT per-tile — excluded from
  // dispose.
  simTileTextures = [demTex, stressTex, stressTexV, s2PreTex, s2PostTex]
  if (stressTexA !== stressTexV) simTileTextures.push(stressTexA)
  if (stressTexB !== stressTexV) simTileTextures.push(stressTexB)

  const mat = new THREE.MeshBasicMaterial({
    map: baseTex,
    transparent: true,
    polygonOffset: true,
    polygonOffsetFactor: -4,
    polygonOffsetUnits: -4,
    side: THREE.DoubleSide,
  })
  mat.onBeforeCompile = (shader) => {
    shader.uniforms.uDemTex = { value: demTex }
    shader.uniforms.uStressTex = { value: stressTex }
    shader.uniforms.uStressTexV = { value: stressTexV }
    shader.uniforms.uS2PreTex = { value: s2PreTex }
    shader.uniforms.uS2PostTex = { value: s2PostTex }
    shader.uniforms.uS2T = { value: props.simDomain?.s2T ?? 0 }
    shader.uniforms.uDrainT = { value: props.simDomain?.drainT ?? 0 }
    shader.uniforms.uStressT = { value: props.simDomain?.stressT ?? 0 }
    shader.uniforms.uModelMix = { value: props.simDomain?.modelMix ?? 0 }
    // MGSIM page: glassy-surface alpha + the hot-swappable
    // alt stress drape mixed over the published elastic/viscous pair.
    shader.uniforms.uSurfA = { value: props.simDomain?.surfA ?? 1 }
    shader.uniforms.uStressTexA = { value: stressTexA }
    shader.uniforms.uAltMix = { value: props.simDomain?.altMix ?? 0 }
    shader.uniforms.uStressTexB = { value: stressTexB }
    shader.uniforms.uAltMixB = { value: props.simDomain?.altMixB ?? 0 }
    // The IMAGERY · DIFFERENCE cell — mean-RGB
    // reflectance change post − pre on BrBG, ± uImgDiffLim.
    shader.uniforms.uImgDiffT = { value: props.simDomain?.imgDiffT ?? 0 }
    shader.uniforms.uImgDiffLim = { value: IMAGERY_DIFF_LIM }
    // Tile crossfade: the 25 m tile fades in over the coarse
    // greenland surface at WIDE framing — where the two are sub-pixel
    // identical — so the swap can never read as a pop.
    shader.uniforms.uTileA = { value: props.simDomain?.tileT ?? 1 }
    shader.uniforms.uExaggeration = { value: currentExag }
    shader.uniforms.uHillshadeStrength = { value: 1 }
    shader.uniforms.uLightTangent = { value: LIGHT_TANGENT.clone() }
    shader.vertexShader = shader.vertexShader
      .replace(
        '#include <common>',
        `#include <common>
         uniform sampler2D uDemTex;
         uniform float uExaggeration;
         varying vec2 vUvT;
         float decodeDemRG(vec4 rgba) {
           return (rgba.r * 65280.0 + rgba.g * 255.0) / 65535.0;
         }
         float sampleTileDem(vec2 uv) {
           vec2 texSize = vec2(1024.0, 1024.0);
           vec2 px = uv * texSize - 0.5;
           vec2 pxFloor = floor(px);
           vec2 t = px - pxFloor;
           vec2 uv00 = (pxFloor + 0.5) / texSize;
           vec2 uv10 = uv00 + vec2(1.0 / texSize.x, 0.0);
           vec2 uv01 = uv00 + vec2(0.0, 1.0 / texSize.y);
           vec2 uv11 = uv00 + vec2(1.0 / texSize.x, 1.0 / texSize.y);
           float e00 = decodeDemRG(texture2D(uDemTex, uv00));
           float e10 = decodeDemRG(texture2D(uDemTex, uv10));
           float e01 = decodeDemRG(texture2D(uDemTex, uv01));
           float e11 = decodeDemRG(texture2D(uDemTex, uv11));
           float e0 = mix(e00, e10, t.x);
           float e1 = mix(e01, e11, t.x);
           return mix(e0, e1, t.y);
         }`,
      )
      .replace(
        '#include <begin_vertex>',
        `vec3 transformed = vec3( position );
         vUvT = uv;
         float elev = sampleTileDem(uv);
         vec3 N = normalize(position);
         transformed += N * elev * uExaggeration;`,
      )
    shader.fragmentShader = shader.fragmentShader
      .replace(
        '#include <common>',
        `#include <common>
         uniform sampler2D uDemTex;
         uniform sampler2D uStressTex;
         uniform sampler2D uStressTexV;
         uniform sampler2D uS2PreTex;
         uniform sampler2D uS2PostTex;
         uniform float uS2T;
         uniform float uDrainT;
         uniform float uStressT;
         uniform float uModelMix;
         uniform float uTileA;
         uniform sampler2D uStressTexA;
         uniform float uAltMix;
         uniform sampler2D uStressTexB;
         uniform float uAltMixB;
         uniform float uSurfA;
         uniform float uImgDiffT;
         uniform float uImgDiffLim;
         uniform float uHillshadeStrength;
         uniform vec3 uLightTangent;
         varying vec2 vUvT;
         float decodeDemRG(vec4 rgba) {
           return (rgba.r * 65280.0 + rgba.g * 255.0) / 65535.0;
         }
         // matplotlib BrBG (sRGB stops at 0, .1, … 1) — the legend's
         // gradient (SimImageryDiffLegend.vue).
         vec3 simImgDiffRamp(float t) {
           vec3 c[11];
           c[0] = vec3(0.329, 0.188, 0.020); c[1] = vec3(0.549, 0.318, 0.039);
           c[2] = vec3(0.749, 0.506, 0.176); c[3] = vec3(0.875, 0.761, 0.490);
           c[4] = vec3(0.965, 0.910, 0.765); c[5] = vec3(0.961, 0.961, 0.961);
           c[6] = vec3(0.780, 0.918, 0.898); c[7] = vec3(0.502, 0.804, 0.757);
           c[8] = vec3(0.208, 0.592, 0.561); c[9] = vec3(0.004, 0.400, 0.369);
           c[10] = vec3(0.0, 0.235, 0.188);
           float f = clamp(t, 0.0, 1.0) * 10.0;
           int i = int(min(floor(f), 9.0));
           vec3 a = c[0]; vec3 b = c[1];
           for (int k = 0; k < 10; k++) {
             if (k == i) { a = c[k]; b = c[k + 1]; }
           }
           return mix(a, b, f - float(i));
         }`,
      )
      .replace(
        '#include <map_fragment>',
        `#include <map_fragment>
         vec4 demPix = texture2D(uDemTex, vUvT);
         // The DEM alpha IS the rotated model-domain footprint.
         if (demPix.a < 0.5) discard;
         diffuseColor.a *= uTileA * uSurfA;
         // Face imagery: basemap crop (embedded, matches the coarse
         // skin) → Sentinel-2 PRE-drainage truecolor (sharpens in on
         // the zoom approach — the real lake, full) → POST-drainage
         // ("Drain the lake" crossfade — the lake visibly empties).
         vec4 s2PreC = texture2D(uS2PreTex, vUvT);
         vec4 s2PostC = texture2D(uS2PostTex, vUvT);
         vec3 s2 = mix(s2PreC.rgb, s2PostC.rgb, uDrainT);
         diffuseColor.rgb = mix(diffuseColor.rgb, s2, uS2T);
         // IMAGERY · DIFFERENCE: the jpgs ARE reflectance (bands / 1e4,
         // clipped) — undo three's sRGB decode to get them back, then
         // the mean-RGB change post − pre on the BrBG ramp.
         if (uImgDiffT > 0.001) {
           vec3 rPre = sRGBTransferOETF(s2PreC).rgb;
           vec3 rPost = sRGBTransferOETF(s2PostC).rgb;
           float dR = dot(rPost - rPre, vec3(1.0 / 3.0));
           vec3 dCol = simImgDiffRamp(dR / uImgDiffLim * 0.5 + 0.5);
           dCol = sRGBTransferEOTF(vec4(dCol, 1.0)).rgb;
           diffuseColor.rgb = mix(diffuseColor.rgb, dCol, uImgDiffT * uS2T);
         }
         // Model drape: elastic ↔ viscous (shared ±1 MPa scale), only
         // once a model is chosen (uStressT).
         vec4 stressPix = mix(mix(mix(texture2D(uStressTex, vUvT),
                                      texture2D(uStressTexV, vUvT), uModelMix),
                                  texture2D(uStressTexA, vUvT), uAltMix),
                              texture2D(uStressTexB, vUvT), uAltMixB);
         diffuseColor.rgb = mix(diffuseColor.rgb, stressPix.rgb, uStressT * stressPix.a);
         // Hillshade from the 25 m sim DEM (gradient of the decoded
         // elevation fraction — same recipe as the global shaders).
         float epsT = 2.0 / 1024.0;
         float hC = decodeDemRG(texture2D(uDemTex, vUvT));
         float hE = decodeDemRG(texture2D(uDemTex, vUvT + vec2(epsT, 0.0)));
         float hN = decodeDemRG(texture2D(uDemTex, vUvT + vec2(0.0, epsT)));
         float gE = (hE - hC) / epsT;
         float gN = (hN - hC) / epsT;
         vec3 nT = normalize(vec3(-gE, -gN, 1.2));
         float light = clamp(dot(nT, uLightTangent), 0.0, 1.0);
         // Capped at 1.0 (was 1.1) so the tile never reads brighter
         // than the surrounding basemap while embedded.
         float factor = mix(1.0, clamp(0.5 + light * 0.55, 0.5, 1.0), uHillshadeStrength);
         diffuseColor.rgb *= factor;`,
      )
    simTileShader = shader
    elevatedShaders.push(shader)
  }
  mat.needsUpdate = true

  const mesh = new THREE.Mesh(geom, mat)
  mesh.rotation.x = Math.PI / 2
  mesh.renderOrder = 4 // above bed (2) + walls (3); see buildSimBed
  // The telephoto drain framing (fov ~2°) makes the frustum a needle —
  // the un-displaced bounding sphere misjudges the shader-displaced
  // patch, so skip culling (one tiny mesh).
  mesh.frustumCulled = false
  scene.add(mesh)
  simTileMesh = mesh
  simTileMat = mat
  simTileUrl = d.demUrl

  // Catalog-outline overlays build once the lakes JSON lands (see
  // buildSimLakesOverlays — N+1 pre-drawn visibility-switched meshes).
  buildSimLakesOverlays()
  // Overlay materials compile during the tile's warm window.
  buildSimMatWarmMesh()

  buildSimBed(d)
  // Button-anchor dirs: domain center + the 4 corners.
  simAnchorDirs = [
    lonLatUnit(d.centerLon, d.centerLat),
    ...d.corners.map(([lon, lat]) => lonLatUnit(lon, lat)),
  ]
  simAnchorElevM = d.centerSurfM
}

// ── Bed underside ──
function buildSimBed(d: NonNullable<typeof props.simDomain>): void {
  const phiStart = Math.PI + (d.bbox.lonW * Math.PI) / 180
  const phiLength = ((d.bbox.lonE - d.bbox.lonW) * Math.PI) / 180
  const thetaStart = Math.PI / 2 - (d.bbox.latN * Math.PI) / 180
  const thetaLength = ((d.bbox.latN - d.bbox.latS) * Math.PI) / 180
  const geom = new THREE.SphereGeometry(
    GLOBE_RADIUS, 192, 192, phiStart, phiLength, thetaStart, thetaLength,
  )
  const bedTex = loadTexTracked(d.bedUrl, (t) => {
    simBedDemImage = t.image as HTMLImageElement
    maybeBuildSimWalls(d)
  })
  bedTex.colorSpace = THREE.NoColorSpace
  bedTex.minFilter = THREE.NearestFilter
  bedTex.magFilter = THREE.NearestFilter
  bedTex.generateMipmaps = false
  simTileTextures.push(bedTex)

  const mat = new THREE.MeshBasicMaterial({
    transparent: true,
    side: THREE.DoubleSide,
    color: 0xffffff,
  })
  mat.onBeforeCompile = (shader) => {
    shader.uniforms.uDemTex = { value: bedTex }
    shader.uniforms.uBedScaleM = { value: d.bedScaleM }
    shader.uniforms.uBedOffM = { value: d.bedOffM }
    shader.uniforms.uExaggeration = { value: currentExag }
    shader.uniforms.uHillshadeStrength = { value: 1 }
    shader.uniforms.uLightTangent = { value: LIGHT_TANGENT.clone() }
    shader.uniforms.uTileA = { value: props.simDomain?.tileT ?? 1 }
    // Hypsometric palette (256×1 ramp shared with the MGSIM
    // side panels) mixed over the brown bedrock by uBedPalMix.
    shader.uniforms.uBedPalTex = { value: ensureBedPalette(d) }
    shader.uniforms.uBedPalMix = { value: props.simDomain?.bedPalMix ?? 0 }
    shader.uniforms.uBedVmin = { value: d.bedVminM ?? -300 }
    shader.uniforms.uBedVmax = { value: d.bedVmaxM ?? 600 }
    shader.vertexShader = shader.vertexShader
      .replace(
        '#include <common>',
        `#include <common>
         uniform sampler2D uDemTex;
         uniform float uExaggeration;
         uniform float uBedScaleM;
         uniform float uBedOffM;
         varying vec2 vUvT;
         float decodeDemRG(vec4 rgba) {
           return (rgba.r * 65280.0 + rgba.g * 255.0) / 65535.0;
         }
         float sampleBedFrac(vec2 uv) {
           vec2 texSize = vec2(1024.0, 1024.0);
           vec2 px = uv * texSize - 0.5;
           vec2 pxFloor = floor(px);
           vec2 t = px - pxFloor;
           vec2 uv00 = (pxFloor + 0.5) / texSize;
           float e00 = decodeDemRG(texture2D(uDemTex, uv00));
           float e10 = decodeDemRG(texture2D(uDemTex, uv00 + vec2(1.0 / texSize.x, 0.0)));
           float e01 = decodeDemRG(texture2D(uDemTex, uv00 + vec2(0.0, 1.0 / texSize.y)));
           float e11 = decodeDemRG(texture2D(uDemTex, uv00 + vec2(1.0 / texSize.x, 1.0 / texSize.y)));
           return mix(mix(e00, e10, t.x), mix(e01, e11, t.x), t.y);
         }`,
      )
      .replace(
        '#include <begin_vertex>',
        `vec3 transformed = vec3( position );
         vUvT = uv;
         // Decode to metres (offset encoding — bed can dip below sea
         // level), then displace with the SAME 3500 m normalization
         // the rest of the site uses.
         float elevM = sampleBedFrac(uv) * uBedScaleM + uBedOffM;
         transformed += normalize(position) * (elevM / 3500.0) * uExaggeration;`,
      )
    shader.fragmentShader = shader.fragmentShader
      .replace(
        '#include <common>',
        `#include <common>
         uniform sampler2D uDemTex;
         uniform float uHillshadeStrength;
         uniform float uTileA;
         uniform vec3 uLightTangent;
         uniform sampler2D uBedPalTex;
         uniform float uBedPalMix;
         uniform float uBedVmin;
         uniform float uBedVmax;
         uniform float uBedScaleM;
         uniform float uBedOffM;
         varying vec2 vUvT;
         float decodeDemRG(vec4 rgba) {
           return (rgba.r * 65280.0 + rgba.g * 255.0) / 65535.0;
         }`,
      )
      .replace(
        '#include <color_fragment>',
        `#include <color_fragment>
         vec4 demPix = texture2D(uDemTex, vUvT);
         if (demPix.a < 0.5) discard;
         diffuseColor.a *= uTileA;
         // Bedrock: the Ch.1 slab's bed palette, hillshaded from the
         // bed DEM itself.
         float epsT = 2.0 / 1024.0;
         float hC = decodeDemRG(texture2D(uDemTex, vUvT));
         float hE = decodeDemRG(texture2D(uDemTex, vUvT + vec2(epsT, 0.0)));
         float hN = decodeDemRG(texture2D(uDemTex, vUvT + vec2(0.0, epsT)));
         vec3 nT = normalize(vec3(-(hE - hC) / epsT, -(hN - hC) / epsT, 1.5));
         float light = clamp(dot(nT, uLightTangent), 0.0, 1.0);
         vec3 bedCol = mix(vec3(0.55, 0.38, 0.24), vec3(0.82, 0.74, 0.55),
                           clamp(0.25 + light * 0.75, 0.0, 1.0));
         // Hypsometric ramp — decode metres, look up the
         // shared palette, mix over the bedrock by uBedPalMix.
         float bedM = hC * uBedScaleM + uBedOffM;
         float palU = clamp((bedM - uBedVmin) / (uBedVmax - uBedVmin), 0.002, 0.998);
         vec3 hypso = texture2D(uBedPalTex, vec2(palU, 0.5)).rgb;
         bedCol = mix(bedCol, hypso, uBedPalMix);
         diffuseColor.rgb = bedCol * mix(1.0, 0.6 + light * 0.45, uHillshadeStrength);`,
      )
    simBedShader = shader
    elevatedShaders.push(shader)
  }
  mat.needsUpdate = true

  const mesh = new THREE.Mesh(geom, mat)
  mesh.rotation.x = Math.PI / 2
  // Explicit back-to-front order inside the block (bed 2 <
  // walls 3 < surface 4) so a glassy surface tints OVER the bed rather
  // than the bed overpainting it. Opaque rendering is unaffected.
  mesh.renderOrder = 2
  mesh.frustumCulled = false
  scene.add(mesh)
  simBedMesh = mesh
  simBedMat = mat
  simBedUrl = d.bedUrl
}

// ── Ice cross-section walls ──
// Built once BOTH DEM images are decoded: CPU-sample surf + bed along
// the four rotated-square edges and extrude an ice wall between them
// (the Ch.1 slab's ice color, one fixed shade per face). Vertices
// carry their elevation in metres; a tiny vertex shader applies the
// SAME uExaggeration as everything else, so the walls track the
// landing's settle to ~true scale.
// Images never change under a URL: one readback each (the teaser's 3 s
// bed swaps rebuild the walls from cached pixels).
const readbackCache = new WeakMap<HTMLImageElement, { data: Uint8ClampedArray; w: number; h: number }>()
function readbackRG16(img: HTMLImageElement): {
  data: Uint8ClampedArray
  w: number
  h: number
} {
  const hit = readbackCache.get(img)
  if (hit) return hit
  const rb = readbackRG16Raw(img)
  readbackCache.set(img, rb)
  return rb
}
function readbackRG16Raw(img: HTMLImageElement): {
  data: Uint8ClampedArray
  w: number
  h: number
} {
  const c = document.createElement('canvas')
  c.width = img.naturalWidth || img.width
  c.height = img.naturalHeight || img.height
  const ctx = c.getContext('2d', { willReadFrequently: true })!
  ctx.drawImage(img, 0, 0)
  const data = ctx.getImageData(0, 0, c.width, c.height).data
  return { data: data as Uint8ClampedArray, w: c.width, h: c.height }
}

function sampleRG16(
  rb: { data: Uint8ClampedArray; w: number; h: number },
  u: number,
  vTop: number,
): number {
  // vTop measured from the image TOP (row 0 = north).
  const px = Math.min(rb.w - 1, Math.max(0, Math.round(u * (rb.w - 1))))
  const py = Math.min(rb.h - 1, Math.max(0, Math.round(vTop * (rb.h - 1))))
  const i = (py * rb.w + px) * 4
  return (rb.data[i] * 256 + rb.data[i + 1]) / 65535
}

function maybeBuildSimWalls(d: NonNullable<typeof props.simDomain>): void {
  if (!simSurfDemImage || !simBedDemImage || simWallMesh) return
  if (props.simDomain?.demUrl !== d.demUrl) return
  const surfRb = readbackRG16(simSurfDemImage)
  const bedRb = readbackRG16(simBedDemImage)

  const N = 96
  const ICE = new THREE.Color(0.72, 0.84, 0.96)
  const EDGE_SHADE = [0.95, 0.74, 0.62, 0.85]
  const positions: number[] = []
  const elevs: number[] = []
  const colors: number[] = []
  const index: number[] = []
  const corners = d.corners
  simEdgeSamples = []
  for (let e = 0; e < 4; e++) {
    const [lon0, lat0] = corners[e]
    const [lon1, lat1] = corners[(e + 1) % 4]
    const shade = EDGE_SHADE[e]
    const base = positions.length / 3
    const samples: SimEdgeSample[] = []
    simEdgeSamples.push(samples)
    for (let i = 0; i <= N; i++) {
      const t = i / N
      const lon = lon0 + (lon1 - lon0) * t
      const lat = lat0 + (lat1 - lat0) * t
      const u = (lon - d.bbox.lonW) / (d.bbox.lonE - d.bbox.lonW)
      const vTop = (d.bbox.latN - lat) / (d.bbox.latN - d.bbox.latS)
      // Nudge the sample INSIDE the footprint so the alpha border
      // (which the encoder zeroes) never reads as elevation 0.
      const cu = 0.5 + (u - 0.5) * 0.995
      const cv = 0.5 + (vTop - 0.5) * 0.995
      const surfM = sampleRG16(surfRb, cu, cv) * 3500
      const bedM = sampleRG16(bedRb, cu, cv) * d.bedScaleM + d.bedOffM - 60
      samples.push({ lon, lat, surfM, bedM })
      const dir = lonLatUnit(lon, lat)
      for (const elevM of [surfM, bedM]) {
        positions.push(dir.x * GLOBE_RADIUS, dir.y * GLOBE_RADIUS, dir.z * GLOBE_RADIUS)
        elevs.push(elevM)
        colors.push(ICE.r * shade, ICE.g * shade, ICE.b * shade)
      }
      if (i > 0) {
        const a = base + (i - 1) * 2
        index.push(a, a + 1, a + 2, a + 1, a + 3, a + 2)
      }
    }
  }
  const geom = new THREE.BufferGeometry()
  geom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  geom.setAttribute('aElevM', new THREE.Float32BufferAttribute(elevs, 1))
  geom.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
  geom.setIndex(index)

  const mat = new THREE.MeshBasicMaterial({
    vertexColors: true,
    transparent: true,
    side: THREE.DoubleSide,
  })
  mat.onBeforeCompile = (shader) => {
    shader.uniforms.uExaggeration = { value: currentExag }
    shader.uniforms.uTileA = { value: props.simDomain?.tileT ?? 1 }
    shader.uniforms.uSurfA = { value: props.simDomain?.surfA ?? 1 }
    shader.vertexShader = shader.vertexShader
      .replace(
        '#include <common>',
        `#include <common>
         attribute float aElevM;
         uniform float uExaggeration;`,
      )
      .replace(
        '#include <begin_vertex>',
        `vec3 transformed = vec3( position );
         transformed += normalize(position) * (aElevM / 3500.0) * uExaggeration;`,
      )
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <color_fragment>',
      `#include <color_fragment>
       diffuseColor.a *= uTileA * uSurfA;`,
    )
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <common>',
      `#include <common>
       uniform float uTileA;
       uniform float uSurfA;`,
    )
    simWallShader = shader
    elevatedShaders.push(shader)
  }
  mat.needsUpdate = true

  const mesh = new THREE.Mesh(geom, mat)
  mesh.renderOrder = 3
  mesh.frustumCulled = false
  scene.add(mesh)
  simWallMesh = mesh
  simWallMat = mat
  buildSimEdges()
}

function lonLatUnit(lonDeg: number, latDeg: number): THREE.Vector3 {
  const lat = (latDeg * Math.PI) / 180
  const lon = (lonDeg * Math.PI) / 180
  return new THREE.Vector3(
    Math.cos(lat) * Math.cos(lon),
    Math.cos(lat) * Math.sin(lon),
    Math.sin(lat),
  )
}

// ── Flow arrow + boundary-condition overlays ──
// The domain's local x-axis is the along-flow direction (SI §4: the
// tile is rotated so x ∥ flow), so corners c3→c0 bound the INFLOW
// wall and c1→c2 the OUTFLOW wall (build_sim_domains.py corner order:
// (-x,-y),(+x,-y),(+x,+y),(-x,+y)). All geometry here is built in
// world coordinates at the CURRENT exaggeration — only reachable once
// the block has landed (exag settled at CH2's zoom value) and
// disposed the moment the inspect state ends.
let simFlowGroup: THREE.Group | null = null
const simFlowCamUp = new THREE.Vector3()
const simFlowTmp = new THREE.Vector3()
let simBcGroup: THREE.Group | null = null

// Shared materials for the flow arrow + BC overlays. Created once and
// warm-rendered with the tile (a micro-triangle at build time) so
// their program link never lands on the zoom's arrival frame
// (profiling: ~300 ms of getProgram/link at the landed moment).
let simGoldMat: THREE.MeshBasicMaterial | null = null
let simMatWarmMesh: THREE.Group | null = null

function ensureSimOverlayMats(): void {
  if (simGoldMat) return
  simGoldMat = new THREE.MeshBasicMaterial({ color: 0xf5c75e })
}

function buildSimMatWarmMesh(): void {
  if (simMatWarmMesh) return
  ensureSimOverlayMats()
  const g = new THREE.Group()
  const tri = new THREE.BufferGeometry()
  tri.setAttribute('position', new THREE.Float32BufferAttribute(
    [0, 0, 0, 1e-6, 0, 0, 0, 1e-6, 0], 3,
  ))
  // the flow arrow's gold + every BC-mode material (components/
  // simBcOverlay.ts) — lines warm as lines, meshes as meshes
  g.add(new THREE.Mesh(tri, simGoldMat!))
  for (const m of bcMaterialList()) {
    g.add((m as THREE.LineBasicMaterial).isLineBasicMaterial
      ? new THREE.Line(tri, m)
      : new THREE.Mesh(tri, m))
  }
  // The outline / axis-triad line program too.
  ensureSimOutlineMats()
  g.add(new THREE.Mesh(tri, simAxesHeadMat!))
  const warmLines = new LineSegmentsGeometry()
  warmLines.setPositions([0, 0, 0, 1e-6, 0, 0])
  g.add(new LineSegments2(warmLines, simOutlineMat!))
  g.traverse((c) => { c.frustumCulled = false })
  scene.add(g)
  simMatWarmMesh = g
}

function disposeSimMatWarmMesh(): void {
  if (!simMatWarmMesh) return
  scene.remove(simMatWarmMesh)
  simMatWarmMesh.traverse((c) => {
    (c as THREE.Mesh).geometry?.dispose()
  })
  simMatWarmMesh = null
}

function simElevPos(lonDeg: number, latDeg: number, elevM: number): THREE.Vector3 {
  return lonLatUnit(lonDeg, latDeg).multiplyScalar(
    GLOBE_RADIUS + (elevM / SURF_MAX_M) * currentExag,
  )
}

function disposeGroupDeep(g: THREE.Group | null): void {
  if (!g) return
  scene.remove(g)
  g.traverse((c) => {
    const m = c as THREE.Mesh
    if ((m as any).isMesh || (c as any).isLine) {
      m.geometry?.dispose()
      // materials are the SHARED sim-overlay set — never disposed here
    }
  })
}

function disposeSimFlow(): void {
  disposeGroupDeep(simFlowGroup)
  simFlowGroup = null
}
function disposeSimBc(): void {
  disposeGroupDeep(simBcGroup)
  simBcGroup = null
  simBcKey = null
}

function addArrow(
  group: THREE.Group,
  from: THREE.Vector3,
  to: THREE.Vector3,
  radius: number,
  mat: THREE.Material,
): void {
  const dir = to.clone().sub(from)
  const len = dir.length()
  if (len < 1e-9) return
  dir.normalize()
  const headLen = Math.min(len * 0.42, radius * 5.5)
  const shaftLen = len - headLen
  const quat = new THREE.Quaternion().setFromUnitVectors(
    new THREE.Vector3(0, 1, 0), dir,
  )
  const shaft = new THREE.Mesh(
    new THREE.CylinderGeometry(radius, radius, shaftLen, 8), mat,
  )
  shaft.quaternion.copy(quat)
  shaft.position.copy(from).addScaledVector(dir, shaftLen / 2)
  const head = new THREE.Mesh(new THREE.ConeGeometry(radius * 2.5, headLen, 12), mat)
  head.quaternion.copy(quat)
  head.position.copy(from).addScaledVector(dir, shaftLen + headLen / 2)
  group.add(shaft, head)
}

interface SimWallMids {
  inLL: [number, number]
  outLL: [number, number]
  lat0LL: [number, number]
  lat1LL: [number, number]
}
function simWallMids(d: NonNullable<typeof props.simDomain>): SimWallMids {
  const c = d.corners
  const mid = (a: [number, number], b: [number, number]): [number, number] =>
    [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]
  return {
    inLL: mid(c[3], c[0]),
    outLL: mid(c[1], c[2]),
    lat0LL: mid(c[0], c[1]),
    lat1LL: mid(c[2], c[3]),
  }
}

/** Persistent gold "ice flow" arrow floating above the landed block. */
function buildSimFlow(d: NonNullable<typeof props.simDomain>): void {
  disposeSimFlow()
  const mids = simWallMids(d)
  const mix = (a: [number, number], b: [number, number], t: number): [number, number] =>
    [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]
  // The arrow used to ride the middle of the surface
  // and compete with the imagery/drapes. Now it hovers OFF the block,
  // outside the c0→c1 (y = −Ly/2) edge, part-way along it from c0 —
  // the domain's bottom-left corner, which the default framing shows
  // as the far/top corner — so it sits just LEFT of the "Drain the
  // lake" pill and clear of the 2×2 face grid; smaller, still along
  // flow (c0→c1 IS +x, the flow direction).
  const elev = d.centerSurfM + 700
  const pIn = simElevPos(mids.inLL[0], mids.inLL[1], elev)
  const pOut = simElevPos(mids.outLL[0], mids.outLL[1], elev)
  const flowDir = pOut.clone().sub(pIn).normalize()
  const L = pIn.distanceTo(pOut)
  const c = d.corners
  // On the LIVE block the arrow moved UPSTREAM — outside the
  // inflow wall (c3–c0), mid-wall, pointing into the domain. Its old
  // spot (outside c0→c1) sat under the colour-bar card at 1440 px once
  // the tag grew 1.5×, and upstream it can never meet the
  // card, the tiers or the axis triad. Thumbnails keep the old spot.
  const thumb = simThumb().arrowOffset !== undefined || !!simThumb().edges
  const alongEdge = thumb ? mix(c[0], c[1], 0.45) : mix(c[3], c[0], 0.5)
  const off = simThumb().arrowOffset ?? 0.3
  const outLL: [number, number] = thumb
    ? [c[0][0] - c[3][0], c[0][1] - c[3][1]]
    : [c[0][0] - c[1][0], c[0][1] - c[1][1]]
  const anchorLL: [number, number] = [
    alongEdge[0] + outLL[0] * (thumb ? off : 0.34),
    alongEdge[1] + outLL[1] * (thumb ? off : 0.34),
  ]
  const center = simElevPos(anchorLL[0], anchorLL[1], elev)
  const half = 0.09 * L * (simThumb().arrowScale ?? 1)
  const from = center.clone().addScaledVector(flowDir, -half)
  const to = center.clone().addScaledVector(flowDir, half)
  ensureSimOverlayMats()
  const g = new THREE.Group()
  const radius = from.distanceTo(to) * 0.035
  addArrow(g, from, to, radius, simGoldMat!)
  g.renderOrder = 4
  // The "ice flow" tag rides the arrow IN the scene —
  // a billboard sprite just above it — so it follows under any camera
  // motion with no per-frame projection or overlay lag.
  const mid = to.clone().add(from).multiplyScalar(0.5)
  const up = lonLatUnit(anchorLL[0], anchorLL[1])
  const arrowLen = from.distanceTo(to)
  const label = new THREE.Sprite(simFlowLabelMat())
  // The director asked for a larger ICE FLOW font: 1.5×
  // the earlier tag, lifted to clear the shaft.
  const labelW = arrowLen * 1.15 * 1.5
  // Live block: the tag hangs UNDER the (upstream) arrow — above it sits
  // the tier row. Thumbnails keep it on top.
  label.position.copy(mid).addScaledVector(up, thumb ? arrowLen * 0.62 : -arrowLen * 0.55)
  label.scale.set(labelW, labelW / 4, 1)
  label.renderOrder = 5
  g.add(label)
  g.traverse((c) => { c.frustumCulled = false })
  g.userData.labelPos = mid
  g.userData.ends = [from, to]
  // live block: the render loop re-hangs the tag under the arrow on screen
  if (!thumb) g.userData.label = label
  scene.add(g)
  simFlowGroup = g
}

/** Shared "ICE FLOW" sprite material (canvas text, built once). */
let simFlowLabelMaterial: THREE.SpriteMaterial | null = null
function simFlowLabelMat(): THREE.SpriteMaterial {
  if (simFlowLabelMaterial) return simFlowLabelMaterial
  const W = 512
  const H = 128
  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')!
  ctx.clearRect(0, 0, W, H)
  ctx.font = '700 50px Inter, system-ui, sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.shadowColor = 'rgba(0, 0, 0, 0.95)'
  ctx.shadowBlur = 14
  ctx.fillStyle = '#ffe9a8'
  // letter-spaced by hand (canvas letterSpacing support is uneven)
  const text = 'ICE FLOW'
  const gap = 8
  const widths = [...text].map((ch) => ctx.measureText(ch).width)
  const total = widths.reduce((a, b) => a + b, 0) + gap * (text.length - 1)
  let x = W / 2 - total / 2
  ;[...text].forEach((ch, i) => {
    ctx.fillText(ch, x + widths[i] / 2, H / 2)
    x += widths[i] + gap
  })
  const tex = new THREE.CanvasTexture(canvas)
  tex.colorSpace = THREE.SRGBColorSpace
  simFlowLabelMaterial = new THREE.SpriteMaterial({
    map: tex, transparent: true, depthTest: false, depthWrite: false,
  })
  return simFlowLabelMaterial
}

// ── The live block's PRISM OUTLINE (thin
// gold lines on its twelve edges — the surface rim, the bed rim, the four
// verticals) and an x/y/z AXIS TRIAD at the corner that sits right-most
// in the landed view (x along flow = the domain's +x, c0→c1; y = +y,
// c0→c3; z up). Both live exactly while the block is landed (the flow
// arrow's gate), are CPU-built at the current exaggeration (rebuilt if it
// moves) and anchored in 3-D, so they ride any orbit. Screen-space line
// widths (LineMaterial) keep the outline thin at every zoom. The thumbnail
// knobs (__simThumb) keep their own black tubes instead.
const SIM_OUTLINE_GOLD = 0xf4cf6a
// The director found a plain yellow-gold outline on the Chapter 2
// simulation domain hard to see and asked for black, or black and
// gold: every face edge is a BLACK band (5.5 px) with the
// gold line (2.2 px) down its middle — the black holds on the white
// Sentinel-2 ice and on the white of the stress drapes, the gold on the
// dark board. The black line is the gold one's child (same geometry).
const SIM_OUTLINE_INK = 0x050505
const SIM_AXES_INK = 0xf3ead2
let simOutline: LineSegments2 | null = null
let simOutlineMat: LineMaterial | null = null
let simOutlineInkMat: LineMaterial | null = null
let simOutlineExag = -1
let simOutlineBornAt = 0
let simAxesGroup: THREE.Group | null = null
let simAxesMat: LineMaterial | null = null
let simAxesHeadMat: THREE.MeshBasicMaterial | null = null
let simAxesCorner = -1
let simAxesExag = -1
const simAxesLabelMats: Record<string, THREE.SpriteMaterial> = {}

function ensureSimOutlineMats(): void {
  if (simOutlineMat) return
  simOutlineMat = new LineMaterial({
    color: SIM_OUTLINE_GOLD,
    linewidth: 2.2, // CSS px
    transparent: true,
    opacity: 0,
    depthWrite: false,
  })
  simOutlineInkMat = new LineMaterial({
    color: SIM_OUTLINE_INK,
    linewidth: 5.5, // CSS px — 1.65 px of black each side of the gold
    transparent: true,
    opacity: 0,
    depthWrite: false,
  })
  simAxesMat = new LineMaterial({
    color: SIM_AXES_INK,
    linewidth: 2.2,
    transparent: true,
    opacity: 1,
    depthWrite: false,
  })
  simAxesHeadMat = new THREE.MeshBasicMaterial({ color: SIM_AXES_INK })
}

function simLineResolution(): THREE.Vector2 {
  const v = new THREE.Vector2()
  renderer.getSize(v)
  return v
}

function disposeSimOutline(): void {
  if (simOutline) {
    scene.remove(simOutline)
    simOutline.geometry.dispose()
    simOutline = null
  }
  simOutlineExag = -1
}

function disposeSimAxes(): void {
  if (simAxesGroup) {
    scene.remove(simAxesGroup)
    simAxesGroup.traverse((c) => {
      ;(c as THREE.Mesh).geometry?.dispose()
    })
    simAxesGroup = null
  }
  simAxesExag = -1
}

/** Horizontal unit vector from the domain centre out through (lon, lat). */
function simOutward(d: SimDomainD, lon: number, lat: number): THREE.Vector3 {
  const dir = lonLatUnit(lon, lat)
  const out = dir.clone().sub(lonLatUnit(d.centerLon, d.centerLat))
  out.addScaledVector(dir, -out.dot(dir))
  return out.normalize()
}

function buildSimOutline(d: SimDomainD): void {
  disposeSimOutline()
  if (simEdgeSamples.length !== 4) return
  ensureSimOutlineMats()
  const e0 = simEdgeSamples[0]
  const L = simElevPos(e0[0].lon, e0[0].lat, e0[0].surfM)
    .distanceTo(simElevPos(e0[e0.length - 1].lon, e0[e0.length - 1].lat, e0[e0.length - 1].surfM))
  // A hair outside the walls so the lines win the depth test against the
  // faces they rim (hidden edges stay hidden behind the block).
  const push = 0.0025 * L
  const at = (q: SimEdgeSample, elevM: number) =>
    simElevPos(q.lon, q.lat, elevM).addScaledVector(simOutward(d, q.lon, q.lat), push)
  const pos: number[] = []
  const seg = (a: THREE.Vector3, b: THREE.Vector3) => pos.push(a.x, a.y, a.z, b.x, b.y, b.z)
  for (const e of simEdgeSamples) {
    for (let i = 1; i < e.length; i++) {
      seg(at(e[i - 1], e[i - 1].surfM + 2), at(e[i], e[i].surfM + 2))
      seg(at(e[i - 1], e[i - 1].bedM), at(e[i], e[i].bedM))
    }
    seg(at(e[0], e[0].surfM + 2), at(e[0], e[0].bedM))
  }
  const geom = new LineSegmentsGeometry()
  geom.setPositions(pos)
  const line = new LineSegments2(geom, simOutlineMat!)
  line.renderOrder = 7
  line.frustumCulled = false
  const ink = new LineSegments2(geom, simOutlineInkMat!)
  ink.renderOrder = 6
  ink.frustumCulled = false
  line.add(ink)
  scene.add(line)
  simOutline = line
  simOutlineExag = currentExag
  if (simOutlineBornAt === 0) simOutlineBornAt = performance.now()
}

/** Canvas-text sprite material for one axis letter: italic EB Garamond
 *  (the LaTeX-figure look), built once per letter. */
function simAxisLabelMat(letter: string): THREE.SpriteMaterial {
  const hit = simAxesLabelMats[letter]
  if (hit) return hit
  const S = 128
  const canvas = document.createElement('canvas')
  canvas.width = S
  canvas.height = S
  const tex = new THREE.CanvasTexture(canvas)
  tex.colorSpace = THREE.SRGBColorSpace
  const draw = () => {
    const ctx = canvas.getContext('2d')!
    ctx.clearRect(0, 0, S, S)
    ctx.font = 'italic 500 96px "EB Garamond", Georgia, serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.shadowColor = 'rgba(0, 0, 0, 0.95)'
    ctx.shadowBlur = 12
    ctx.fillStyle = '#f3ead2'
    ctx.fillText(letter, S / 2, S / 2 - 6)
    tex.needsUpdate = true
  }
  draw()
  // The web font may land after the first draw — redraw when it does.
  document.fonts?.load('italic 500 96px "EB Garamond"').then(draw).catch(() => {})
  const m = new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false })
  simAxesLabelMats[letter] = m
  return m
}

/** The corner (0–3) whose surface point projects furthest RIGHT now. */
function simRightmostCorner(d: SimDomainD): number {
  let best = 0
  let bestX = -Infinity
  d.corners.forEach(([lon, lat], i) => {
    const q = simEdgeSamples[i]?.[0]
    const x = simElevPos(lon, lat, q ? q.surfM : d.centerSurfM).project(camera).x
    if (x > bestX) { bestX = x; best = i }
  })
  return best
}

function buildSimAxes(d: SimDomainD): void {
  disposeSimAxes()
  if (simEdgeSamples.length !== 4 || simAxesCorner < 0) return
  ensureSimOutlineMats()
  const c = d.corners
  const k = simAxesCorner
  const q = simEdgeSamples[k][0] // edge k starts at corner k
  const e0 = simEdgeSamples[0]
  const L = simElevPos(e0[0].lon, e0[0].lat, e0[0].surfM)
    .distanceTo(simElevPos(e0[e0.length - 1].lon, e0[e0.length - 1].lat, e0[e0.length - 1].surfM))
  // Origin: outside the corner at BED level. An axis that points back
  // along the block from this corner (corner order (−x,−y) (+x,−y)
  // (+x,+y) (−x,+y)) would lie on the block's edge, so the origin steps
  // well clear of the face that axis runs along — at bed level the arrow
  // then passes under the wall's bottom edge, in free space.
  const corner0 = simElevPos(q.lon, q.lat, q.bedM)
  const zHat = corner0.clone().normalize()
  const tangent = (v: THREE.Vector3) => v.addScaledVector(zHat, -v.dot(zHat)).normalize()
  const xHat = tangent(lonLatUnit(c[1][0], c[1][1]).sub(lonLatUnit(c[0][0], c[0][1])))
  const yHat = tangent(lonLatUnit(c[3][0], c[3][1]).sub(lonLatUnit(c[0][0], c[0][1])))
  const xSign = k === 1 || k === 2 ? 1 : -1
  const ySign = k === 2 || k === 3 ? 1 : -1
  const O = corner0
    .addScaledVector(xHat, xSign * (ySign < 0 ? 0.13 : 0.03) * L)
    .addScaledVector(yHat, ySign * (xSign < 0 ? 0.13 : 0.03) * L)
  // (The domain frame is right-handed: x × y · z > 0 — logged once.)
  ;(window as any).__simAxesHand = xHat.clone().cross(yHat).dot(zHat)
  const len = 0.14 * L
  const head = 0.042 * L
  const g = new THREE.Group()
  const pos: number[] = []
  const tips: [string, THREE.Vector3, THREE.Vector3][] = [
    ['x', xHat, O.clone().addScaledVector(xHat, len)],
    ['y', yHat, O.clone().addScaledVector(yHat, len)],
    ['z', zHat, O.clone().addScaledVector(zHat, len)],
  ]
  for (const [letter, dir, tip] of tips) {
    const shaftEnd = tip.clone().addScaledVector(dir, -head * 0.9)
    pos.push(O.x, O.y, O.z, shaftEnd.x, shaftEnd.y, shaftEnd.z)
    const cone = new THREE.Mesh(new THREE.ConeGeometry(head * 0.32, head, 14), simAxesHeadMat!)
    cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir)
    cone.position.copy(tip).addScaledVector(dir, -head / 2)
    g.add(cone)
    const label = new THREE.Sprite(simAxisLabelMat(letter))
    label.position.copy(tip).addScaledVector(dir, 0.06 * L)
    label.scale.set(0.085 * L, 0.085 * L, 1)
    label.renderOrder = 7
    g.add(label)
  }
  const geom = new LineSegmentsGeometry()
  geom.setPositions(pos)
  const shafts = new LineSegments2(geom, simAxesMat!)
  g.add(shafts)
  g.renderOrder = 7
  g.traverse((o) => { o.frustumCulled = false })
  // The triad's extremes (origin + the three letters' centres) — projected
  // each frame into __simDomainScreen.axesBox so Chapter 2's stress space
  // can keep clear of it (the director wanted the axes kept on the Δσ
  // pages, with the stress-space plots moved over to accommodate them).
  g.userData.anchors = [O.clone(), ...tips.map(([, dir, tip]) => tip.clone().addScaledVector(dir, 0.06 * L))]
  g.userData.labelHalf = 0.0425 * L
  scene.add(g)
  simAxesGroup = g
  simAxesExag = currentExag
}

// ── Chapter 2's TWIN (the `teaser` beat) ──
// The director wanted the stress response shown in a nearly identical
// simulation domain object sitting to the RIGHT of the bed elevation view. It is
// the SAME block — geometry, walls, rim, catalog drape — rendered a second
// time per frame through the same camera, its viewport shifted so it
// mirrors the first about the screen's centre (or, with `twin.gap`, sits
// IMMEDIATELY right of the first — the director later asked for the
// stress figure moved left, closer to the
// bed-elevation figure), with the surface opaque and
// painted by `twin.stressUrl`. `twin.t` slides it out from behind the first
// (alpha rides the first 45 %). Every bed + drape of the cycle is decoded
// and uploaded up front (`twin.preload`): a 3 s tick swaps bound textures
// only — swapSimBed takes a cached bed synchronously.
const simTwinCache = new Map<string, THREE.Texture>()
const simTwinTmp = new THREE.Vector3()
const simTwinVp = new THREE.Vector4()
function simTwinPreload(urls: string[]): void {
  for (const url of urls) {
    if (simTwinCache.has(url)) continue
    const isBed = url.includes('simbed_')
    const tex = loadTexTracked(url, (t) => {
      // upload now, not on the tick that first shows it
      try { renderer.initTexture(t) } catch { /* older three: lazy */ }
    })
    if (isBed) {
      tex.colorSpace = THREE.NoColorSpace
      tex.minFilter = THREE.NearestFilter
      tex.magFilter = THREE.NearestFilter
      tex.generateMipmaps = false
    } else {
      tex.colorSpace = THREE.SRGBColorSpace
    }
    simTwinCache.set(url, tex)
  }
}
function disposeSimTwinCache(): void {
  for (const t of simTwinCache.values()) t.dispose()
  simTwinCache.clear()
}
function simTwinReady(url: string): THREE.Texture | null {
  const t = simTwinCache.get(url)
  return t && (t.image as HTMLImageElement | undefined)?.complete !== false && t.image ? t : null
}
/** Where the first block sits on screen: its corner ring's x-centre and
 *  x-extent (px). */
function simBlockScreenX(d: SimDomainD): { cx: number; w: number } | null {
  if (!camera) return null
  let lo = Infinity
  let hi = -Infinity
  d.corners.forEach(([lon, lat], i) => {
    const q = simEdgeSamples[i]?.[0]
    simTwinTmp.copy(simElevPos(lon, lat, q ? q.surfM : d.centerSurfM)).project(camera)
    const x = (simTwinTmp.x * 0.5 + 0.5) * renderer.domElement.clientWidth
    lo = Math.min(lo, x)
    hi = Math.max(hi, x)
  })
  return Number.isFinite(lo) ? { cx: (lo + hi) / 2, w: hi - lo } : null
}
function renderSimTwin(): void {
  const d = props.simDomain
  const tw = d?.twin
  if (!d || !tw || tw.t <= 0.001 || !simTileShader || !simTileMesh || !simBedShader) {
    ;(window as any).__simTwinScreen = null
    return
  }
  const tex = simTwinReady(tw.stressUrl)
  if (!tex) return
  const W = renderer.domElement.clientWidth
  const H = renderer.domElement.clientHeight
  const bx = simBlockScreenX(d)
  if (bx === null) return
  const cx = bx.cx
  const t = Math.min(1, tw.t)
  const e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
  // the settled offset: one block width + the gap, or the mirror rule
  const full = tw.gap != null ? bx.w * (1 + tw.gap) : W - 2 * cx
  const shift = full * e
  const a = Math.min(1, t / 0.45)
  const keep = new Set<THREE.Object3D>([simTileMesh, simBedMesh!])
  if (simWallMesh) keep.add(simWallMesh)
  if (simOutline) keep.add(simOutline)
  for (const o of simLakesOverlays) keep.add(o.mesh)
  const vis = scene.children.map((c) => c.visible)
  scene.children.forEach((c) => { c.visible = c.visible && keep.has(c) })
  const u = simTileShader.uniforms
  const su = {
    surfA: u.uSurfA.value, stressT: u.uStressT.value, altMix: u.uAltMix.value, alt: u.uStressTexA.value,
    altMixB: u.uAltMixB?.value ?? 0,
    s2T: u.uS2T.value, drainT: u.uDrainT.value, img: u.uImgDiffT.value, tileA: u.uTileA.value,
  }
  const bu = simBedShader.uniforms
  const sb = { pal: bu.uBedPalMix.value, tileA: bu.uTileA.value }
  const wu = simWallShader?.uniforms
  const sw = wu ? { surfA: wu.uSurfA.value, tileA: wu.uTileA.value } : null
  const tileDW = simTileMat!.depthWrite
  const wallDW = simWallMat?.depthWrite ?? true
  const outlineOp = simOutlineMat?.opacity ?? 0
  u.uSurfA.value = 1
  u.uStressT.value = 1
  u.uAltMix.value = 1
  if (u.uAltMixB) u.uAltMixB.value = 0
  u.uStressTexA.value = tex
  u.uS2T.value = 1
  u.uDrainT.value = 1
  u.uImgDiffT.value = 0
  u.uTileA.value = a
  bu.uBedPalMix.value = 0
  bu.uTileA.value = a
  if (wu) {
    wu.uSurfA.value = 1
    wu.uTileA.value = a
  }
  simTileMat!.depthWrite = true
  if (simWallMat) simWallMat.depthWrite = true
  if (simOutlineMat) simOutlineMat.opacity = outlineOp * a
  renderer.getViewport(simTwinVp)
  const autoClear = renderer.autoClear
  renderer.autoClear = false
  // A Color background FORCES a full clear inside render() whatever
  // autoClear says — it would wipe the first block. Off for this pass.
  const bg = scene.background
  scene.background = null
  renderer.clearDepth()
  renderer.setViewport(shift, 0, W, H)
  renderer.render(scene, camera)
  renderer.setViewport(simTwinVp)
  scene.background = bg
  renderer.autoClear = autoClear
  u.uSurfA.value = su.surfA
  u.uStressT.value = su.stressT
  u.uAltMix.value = su.altMix
  if (u.uAltMixB) u.uAltMixB.value = su.altMixB
  u.uStressTexA.value = su.alt
  u.uS2T.value = su.s2T
  u.uDrainT.value = su.drainT
  u.uImgDiffT.value = su.img
  u.uTileA.value = su.tileA
  bu.uBedPalMix.value = sb.pal
  bu.uTileA.value = sb.tileA
  if (wu && sw) {
    wu.uSurfA.value = sw.surfA
    wu.uTileA.value = sw.tileA
  }
  simTileMat!.depthWrite = tileDW
  if (simWallMat) simWallMat.depthWrite = wallDW
  if (simOutlineMat) simOutlineMat.opacity = outlineOp
  scene.children.forEach((c, i) => { c.visible = vis[i] })
  ;(window as any).__simTwinScreen = { shift, full, cx: cx + shift, t }
}

// ── Chapter 2's MARKER STROKE (the `outline` beat) ──
// The director's image: right before the cut to the simulation domain,
// show the outline of the simulation domain on the ice sheet object, as
// if outlining it with a marker before cutting it with a knife.
// The domain's rotated rectangle (the tile's corner ring) laid ON the
// greenland object's live surface, drawn round its four sides as
// `markerT` runs 0 → 1: a gold stroke over a dark halo (gold alone
// vanishes on white ice — the back-row rule). It follows the exaggeration
// through the dive and hands over to the block's own gold rim at the
// landing. Drawn without a depth test (it lies on the surface).
const SIM_MARKER_GOLD = 0xf5c75e
const SIM_MARKER_PER_EDGE = 96
let simMarker: LineSegments2 | null = null
let simMarkerHalo: LineSegments2 | null = null
let simMarkerMat: LineMaterial | null = null
let simMarkerHaloMat: LineMaterial | null = null
let simMarkerKey = ''
function disposeSimMarker(): void {
  if (simMarker) {
    scene.remove(simMarker)
    scene.remove(simMarkerHalo!)
    simMarker.geometry.dispose()
    simMarker = null
    simMarkerHalo = null
  }
  simMarkerKey = ''
}
function tickSimMarker(d: SimDomainD | null): void {
  const a = d?.markerA ?? 0
  if (!d || a <= 0.001) {
    if (simMarker) disposeSimMarker()
    return
  }
  const key = `${d.corners.flat().join(',')}|${currentExag}|${simEdgeSamples.length}`
  if (!simMarker || simMarkerKey !== key) {
    const pos: number[] = []
    let prev: number[] | null = null
    for (let e = 0; e < 4; e++) {
      const [lon0, lat0] = d.corners[e]
      const [lon1, lat1] = d.corners[(e + 1) % 4]
      for (let i = e === 0 ? 0 : 1; i <= SIM_MARKER_PER_EDGE; i++) {
        const t = i / SIM_MARKER_PER_EDGE
        const lon = lon0 + (lon1 - lon0) * t
        const lat = lat0 + (lat1 - lat0) * t
        // On the block's own 25 m rim once its walls are sampled (the
        // marker then lands exactly on the block's top edge); the coarse
        // surface before. A FIXED world lift would float it ~400 m above
        // the block at the landed 2× — the line needs none (no depth test).
        const q = simEdgeSamples.length === 4 ? simEdgeSamples[e]?.[i] : undefined
        const v = q
          ? simElevPos(lon, lat, q.surfM + 4)
          : simElevPos(lon, lat, getDemElevAt(lon, lat))
        const p = [v.x, v.y, v.z]
        if (prev) pos.push(prev[0], prev[1], prev[2], p[0], p[1], p[2])
        prev = p
      }
    }
    if (!simMarkerMat) {
      simMarkerMat = new LineMaterial({ color: SIM_MARKER_GOLD, linewidth: 3.6, transparent: true, depthTest: false, depthWrite: false })
      simMarkerHaloMat = new LineMaterial({ color: 0x0b0906, linewidth: 8.5, transparent: true, depthTest: false, depthWrite: false })
    }
    if (simMarker) {
      ;(simMarker.geometry as LineSegmentsGeometry).setPositions(pos)
    } else {
      const geom = new LineSegmentsGeometry()
      geom.setPositions(pos)
      simMarkerHalo = new LineSegments2(geom, simMarkerHaloMat!)
      simMarkerHalo.renderOrder = 11
      simMarkerHalo.frustumCulled = false
      simMarker = new LineSegments2(geom, simMarkerMat)
      simMarker.renderOrder = 12
      simMarker.frustumCulled = false
      scene.add(simMarkerHalo)
      scene.add(simMarker)
    }
    simMarkerKey = key
  }
  const n = 4 * SIM_MARKER_PER_EDGE
  ;(simMarker!.geometry as LineSegmentsGeometry).instanceCount = Math.round(n * Math.min(1, Math.max(0, d.markerT ?? 1)))
  const res = simLineResolution()
  simMarkerMat!.resolution.copy(res)
  simMarkerHaloMat!.resolution.copy(res)
  simMarkerMat!.opacity = a
  simMarkerHaloMat!.opacity = 0.62 * a
}

/** Per frame (the landed gate): keep the outline + triad built, sized and
 *  faded in. `landed` false tears both down. */
function tickSimOutline(d: SimDomainD | null, landed: boolean): void {
  if (!landed || !d || simThumb().edges) {
    if (simOutline || simAxesGroup) {
      disposeSimOutline()
      disposeSimAxes()
    }
    simOutlineBornAt = 0
    simAxesCorner = -1
    return
  }
  if (simEdgeSamples.length !== 4) return
  if (!simOutline || simOutlineExag !== currentExag) buildSimOutline(d)
  if (simAxesCorner < 0) simAxesCorner = simRightmostCorner(d)
  if (!simAxesGroup || simAxesExag !== currentExag) buildSimAxes(d)
  const res = simLineResolution()
  simOutlineMat!.resolution.copy(res)
  simOutlineInkMat!.resolution.copy(res)
  simAxesMat!.resolution.copy(res)
  // 600 ms fade-in from the landing (the triad rides the same alpha).
  const a = Math.min(1, (performance.now() - simOutlineBornAt) / 600)
  simOutlineMat!.opacity = a
  simOutlineInkMat!.opacity = 0.92 * a
  simAxesMat!.opacity = a
  simAxesHeadMat!.transparent = a < 1
  simAxesHeadMat!.opacity = a
  for (const m of Object.values(simAxesLabelMats)) m.opacity = a
  // Ch.2's results walk: the stress space owns the right column.
  if (simAxesGroup) simAxesGroup.visible = !d.axesOff
}

/** BC mode: the ghost model domain +
 *  the focused boundary's overlay, built by components/simBcOverlay.ts
 *  at the CURRENT exaggeration. Keyed so the animate loop rebuilds it
 *  whenever the lake / model / focus / landed exaggeration changes (a
 *  head-on wall view lifts the exaggeration — the overlay re-forms once
 *  the lift settles and fades in). */
let simBcKey: string | null = null
let simBcFadeT0 = 0
let simBcFadeOutT0 = 0
const SIM_BC_FADE_MS = 450
function simBcWantedKey(): string | null {
  const bc = props.simBc
  if (!bc || !bc.on || !bc.lakeId) return null
  return `${bc.lakeId}|${bc.model}|${bc.focus ?? '-'}|${currentExag.toPrecision(6)}`
}
function buildSimBc(d: NonNullable<typeof props.simDomain>): void {
  disposeSimBc()
  const bc = props.simBc
  if (!bc || !bc.on || !bc.lakeId) return
  let tileBedAt: ((lon: number, lat: number) => number | null) | undefined
  if (simBedDemImage) {
    const bedRb = readbackRG16(simBedDemImage)
    tileBedAt = (lon, lat) => {
      // the analysis tile only (its rotated square, via the alpha-free
      // bbox mapping + the corner ring test)
      const u = (lon - d.bbox.lonW) / (d.bbox.lonE - d.bbox.lonW)
      const vTop = (d.bbox.latN - lat) / (d.bbox.latN - d.bbox.latS)
      if (u < 0 || u > 1 || vTop < 0 || vTop > 1 || !insideCorners(d.corners, lon, lat)) return null
      const cu = 0.5 + (u - 0.5) * 0.99
      const cv = 0.5 + (vTop - 0.5) * 0.99
      return sampleRG16(bedRb, cu, cv) * d.bedScaleM + d.bedOffM
    }
  }
  const g = buildBcGroup({
    lakeId: bc.lakeId,
    model: bc.model,
    focus: bc.focus ?? null,
    exag: currentExag,
    tileBedAt,
  })
  if (!g) return
  scene.add(g)
  simBcGroup = g
  simBcKey = simBcWantedKey()
  simBcFadeT0 = performance.now()
  setBcFade(0)
}

/** Point-in-quad test in lon/lat (the rotated tile square). */
function insideCorners(c: [number, number][], lon: number, lat: number): boolean {
  let inside = false
  for (let i = 0, j = c.length - 1; i < c.length; j = i++) {
    const [xi, yi] = c[i]
    const [xj, yj] = c[j]
    if (yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside
  }
  return inside
}

watch(
  () => props.simBc,
  (v) => {
    if (!v || !v.on) disposeSimBc()
    // (re)builds happen in the animate loop once the block is landed
  },
  { deep: true },
)

function applySimDomain(d: NonNullable<typeof props.simDomain> | null): void {
  if (!d) {
    disposeSimTile()
    basemap.visible = true
    globe.visible = true
    // (never before its texture is in — a map-less material is a white plate)
    velocityMap.visible = !!(velocityMap.material as THREE.MeshBasicMaterial).map?.image
    for (const s of elevatedShaders) {
      if (!s.uniforms.uCarveOn) continue
      s.uniforms.uCarveOn.value = 0
      s.uniforms.uCarveT.value = 0
      s.uniforms.uTileCollapseT.value = 0
    }
    return
  }
  if (d.demUrl !== simTileUrl) buildSimTile(d)
  if (d.twin?.preload.length) simTwinPreload(d.twin.preload)
  // Hot-swaps on a live block (the MGSIM page flips beds and
  // their stress results without rebuilding the tile).
  if (d.bedUrl !== simBedUrl) swapSimBed(d)
  if ((d.stressAltUrl ?? null) !== simAltUrl) swapSimAlt(d)
  if ((d.stressAltUrlB ?? null) !== simAltUrlB) swapSimAltB(d)
  const surfA = d.surfA ?? 1
  if (simTileShader?.uniforms.uStressT) {
    simTileShader.uniforms.uStressT.value = d.stressT
    simTileShader.uniforms.uTileA.value = d.tileT
    simTileShader.uniforms.uModelMix.value = d.modelMix
    simTileShader.uniforms.uS2T.value = d.s2T
    simTileShader.uniforms.uDrainT.value = d.drainT
    simTileShader.uniforms.uSurfA.value = surfA
    simTileShader.uniforms.uAltMix.value = d.altMix ?? 0
    if (simTileShader.uniforms.uAltMixB) simTileShader.uniforms.uAltMixB.value = d.altMixB ?? 0
    simTileShader.uniforms.uImgDiffT.value = d.imgDiffT ?? 0
  }
  updateSimLakesVisibility()
  if (simBedShader?.uniforms.uTileA) {
    const u = simBedShader.uniforms
    u.uTileA.value = d.tileT
    u.uBedPalMix.value = d.bedPalMix ?? 0
    u.uBedVmin.value = d.bedVminM ?? -300
    u.uBedVmax.value = d.bedVmaxM ?? 600
    if (d.bedPaletteUrl && d.bedPaletteUrl !== simBedPalUrl) {
      u.uBedPalTex.value = ensureBedPalette(d)
    }
  }
  if (simWallShader?.uniforms.uTileA) {
    simWallShader.uniforms.uTileA.value = d.tileT
    simWallShader.uniforms.uSurfA.value = surfA
  }
  // A glassy surface must not depth-kill the bed beneath it: surface +
  // walls stop writing depth while translucent (draw order bed < walls
  // < surface, set at build).
  const glassy = surfA < 0.999
  if (simTileMat && simTileMat.depthWrite === glassy) simTileMat.depthWrite = !glassy
  if (simWallMat && simWallMat.depthWrite === glassy) simWallMat.depthWrite = !glassy
  // Once the sweep completes, the greenland object AND the earth
  // sphere must be GONE from every angle — the user can orbit the
  // domain block freely (including from below, where the sphere used
  // to eclipse it), and the knife only ever flattened what its front
  // reached. (South of the sweep span is off-frame at the drain
  // framing, so this hide is invisible.) Restored on beat 0 / dispose.
  const inspect = d.carveT >= 0.999
  basemap.visible = !inspect
  globe.visible = !inspect
  // The velocity map rides the basemap at opacity 0 outside velocity
  // mode — but its transparent material still WRITES DEPTH. From
  // outside it hides behind the displaced block; from INSIDE (the
  // below-horizon orbit) it blankets the sky in front of the camera
  // and depth-kills the whole block (the "black underside" bug).
  velocityMap.visible = !inspect && !!(velocityMap.material as THREE.MeshBasicMaterial).map?.image
  // Free orbit: while embedded, the tile needs polygonOffset
  // to win the z-fight against the basemap skin — but polygonOffset's
  // slope term explodes at grazing incidence, which is what blacked
  // out every below-horizon view (an earlier build clamped them away). With
  // the greenland object gone there is nothing left to fight: drop
  // the offset and the block renders from ANY angle. (Bed + walls
  // never carried an offset.)
  if (simTileMat) simTileMat.polygonOffset = !inspect
  // The immune square on the greenland object: an exact rotated-domain
  // frame built from the tile's own corner ring (unit-sphere tangent
  // axes + half-size), so the mask seam sits under the tile's rim.
  const c = d.corners.map(([lon, lat]) => lonLatUnit(lon, lat))
  const center = lonLatUnit(d.centerLon, d.centerLat)
  const e1 = c[1].clone().sub(c[0])
  const e3 = c[3].clone().sub(c[0])
  const axA = e1.clone().normalize()
  const axB = e3.clone().sub(axA.clone().multiplyScalar(e3.dot(axA))).normalize()
  const half = (e1.length() + e3.length()) / 4
  // Out-of-band debug for the shot tools (like __simTileProbe below).
  const w = window as any
  ;(w.__carveLog = w.__carveLog ?? []).push({
    t: Math.round(performance.now()),
    carveT: +d.carveT.toFixed(3),
    tileT: +d.tileT.toFixed(3),
    stressT: +d.stressT.toFixed(3),
  })
  if (w.__carveLog.length > 600) w.__carveLog.splice(0, 300)
  ;(window as any).__carveProbe = {
    carveT: d.carveT,
    tileT: d.tileT,
    half,
    center: center.toArray(),
    axA: axA.toArray(),
    axB: axB.toArray(),
    corners: d.corners,
    nShaders: elevatedShaders.filter((s) => s.uniforms.uCarveOn).length,
  }
  // Knife sweep span: from just above the drain framing's horizon to
  // just south of the domain — so the front crosses the VISIBLE frame
  // over most of the sweep's duration.
  const knifeS0 = Math.sin(((d.centerLat + 4.5) * Math.PI) / 180)
  const knifeS1 = Math.sin(((d.centerLat - 2.2) * Math.PI) / 180)
  for (const s of elevatedShaders) {
    if (!s.uniforms.uCarveOn) continue
    s.uniforms.uCarveOn.value = 1
    s.uniforms.uCarveT.value = d.carveT
    s.uniforms.uTileCollapseT.value = d.tileT
    s.uniforms.uDomHalf.value = half
    s.uniforms.uKnifeS0.value = knifeS0
    s.uniforms.uKnifeS1.value = knifeS1
    ;(s.uniforms.uDomC.value as THREE.Vector3).copy(center)
    ;(s.uniforms.uDomA.value as THREE.Vector3).copy(axA)
    ;(s.uniforms.uDomB.value as THREE.Vector3).copy(axB)
  }
  // Scene bisect (below-horizon debug): list every scene
  // child with its render-relevant flags, and toggle visibility by
  // index — lets a headed probe find full-screen occluders.
  ;(window as any).__r9Scene = () =>
    scene.children.map((c, i) => {
      const m = (c as THREE.Mesh).material as THREE.Material | undefined
      return {
        i,
        type: c.type,
        visible: c.visible,
        renderOrder: c.renderOrder,
        mat: m
          ? {
              t: m.type,
              transparent: m.transparent,
              opacity: (m as any).opacity,
              depthWrite: m.depthWrite,
              depthTest: m.depthTest,
              side: (m as any).side,
            }
          : null,
      }
    })
  ;(window as any).__r9SetVisible = (i: number, v: boolean) => {
    const c = scene.children[i]
    if (c) c.visible = v
    return c?.type
  }
  ;(window as any).__r9Frame = () => renderer.info.render.frame
  // Out-of-band debug for the shot tools (live probe — reads current
  // state at call time, not emit time).
  ;(window as any).__simTileProbe = () => {
    const bs = simTileMesh?.geometry.boundingSphere
    const ndc = simTileMesh && camera
      ? simTileMesh
          .getWorldPosition(new THREE.Vector3())
          .add(bs ? new THREE.Vector3().copy(bs.center).applyQuaternion(simTileMesh.quaternion) : new THREE.Vector3())
          .project(camera)
          .toArray()
          .map((x) => Math.round(x * 100) / 100)
      : null
    const verts: number[][] = []
    if (simTileMesh && camera) {
      simTileMesh.updateMatrixWorld()
      const pos = (simTileMesh.geometry as THREE.BufferGeometry).attributes.position
      for (const i of [0, Math.floor(pos.count / 2), pos.count - 1]) {
        const p = new THREE.Vector3()
          .fromBufferAttribute(pos as THREE.BufferAttribute, i)
          .applyMatrix4(simTileMesh.matrixWorld)
          .project(camera)
        verts.push(p.toArray().map((x) => Math.round(x * 100) / 100))
      }
    }
    return {
      built: !!simTileMesh,
      compiled: !!simTileShader,
      visible: simTileMesh?.visible ?? null,
      inScene: simTileMesh ? simTileMesh.parent === scene : null,
      bsCenterNdc: ndc,
      verts,
      carveT: d.carveT,
      tileT: d.tileT,
      stressT: d.stressT,
      tileExag: simTileShader?.uniforms.uExaggeration?.value ?? null,
      currentExag,
    }
  }
}

watch(
  () => props.simDomain,
  (v) => applySimDomain(v ?? null),
)

;(window as any).__camDump = () => ({
  // the projection itself (stage-fit view offsets, aspect) and where the
  // origin lands on screen — a camera that does not move can still JUMP
  // through these (the menu → Introduction hop)
  view: camera.view ? { ...camera.view } : null,
  aspect: +camera.aspect.toFixed(5),
  proj: camera.projectionMatrix.elements.map((v: number) => +v.toFixed(5)),
  originNdc: new THREE.Vector3(0, 0, 0).project(camera).toArray().map((v: number) => +v.toFixed(4)),
  programs: renderer ? renderer.info.programs?.map((p: any) => `${p.name}#${p.usedTimes}`) : null,
  programKeys: renderer ? renderer.info.programs?.map((p: any) => String(p.cacheKey ?? '').replace(/\s+/g, ' ').slice(0, 220)) : null,
  pos: camera.position.toArray().map((v: number) => +v.toFixed(4)),
  up: camera.up.toArray().map((v: number) => +v.toFixed(3)),
  fov: camera.fov,
  near: camera.near,
  far: camera.far,
  target: controls ? controls.target.toArray().map((v: number) => +v.toFixed(4)) : null,
  targetNdc: controls
    ? controls.target.clone().project(camera).toArray().map((v: number) => +v.toFixed(3))
    : null,
  blockNdc: simAnchorDirs.length
    ? simAnchorDirs[0]
        .clone()
        .multiplyScalar(GLOBE_RADIUS + (simAnchorElevM / SURF_MAX_M) * currentExag)
        .project(camera)
        .toArray()
        .map((v: number) => +v.toFixed(3))
    : null,
  viewOffset: camera.view ? { ...camera.view } : null,
})

// Debug bisect for the shot tools (mirrors the earlier tile hunt).
;(window as any).__tileBisect = (step: number): string => {
  if (!simTileMat) return 'no mat'
  if (step === 1) {
    simTileMat.map = null
    simTileMat.color.set(0xff3333)
    simTileMat.needsUpdate = true
  } else if (step === 2) {
    simTileMat.depthTest = false
    simTileMat.needsUpdate = true
  } else if (step === 3) {
    simTileMat.onBeforeCompile = () => {}
    simTileMat.customProgramCacheKey = () => 'plain'
    simTileMat.needsUpdate = true
  }
  return 'ok'
}

// ───────── chapter cross-section animations ──────────
//
// Two uniforms get rAF-lerped so the chapter beats read as
// continuous transformations rather than state snaps:
//
//   uChapterCutSinLat  (basemap shaders) — Beat 2 reveal
//   uIdealize          (slab shader)     — Beat 2 → Beat 3 morph
//
// Both use the same easeInOutCubic + animate() rAF pattern as the
// chapter-focus camera lerp, just with a single scalar target.

const CHAPTER_CUT_MS = 3000
const CHAPTER_IDEALIZE_MS = 3400
const CHAPTER_EXAG_MS = 1500

let chapterCutLerp:
  | { from: number; to: number; tStart: number }
  | null = null
let chapterIdealizeLerp:
  | { from: number; to: number; tStart: number }
  | null = null
let chapterExagLerp:
  | { from: number; to: number; tStart: number; durationMs: number }
  | null = null

function setChapterExagTarget(target: number, durationMs: number = CHAPTER_EXAG_MS): void {
  if (Math.abs(currentExag - target) < 1e-6) {
    chapterExagLerp = null
    return
  }
  chapterExagLerp = {
    from: currentExag,
    to: target,
    tStart: performance.now(),
    durationMs,
  }
}

function setChapterIdealizeTarget(target: number): void {
  // Slab might not be built yet (deferred on texture load). When it
  // is, snap; otherwise lerp from current uniform value.
  if (!chapterSlabMat) return
  const current = chapterSlabMat.uniforms.uIdealize.value as number
  if (Math.abs(current - target) < 1e-4) {
    chapterIdealizeLerp = null
    return
  }
  chapterIdealizeLerp = {
    from: current,
    to: target,
    tStart: performance.now(),
  }
}

// Unified south-to-NL knife reveal. Fans the single chapterReveal prop
// out to both the basemap shader's uChapterCutSinLat (where the cut
// edge sits) AND the cross-section slab (its position + opacity +
// idealize morph). Sections drive the animation themselves with their
// own rAF lerps emitting one chapterReveal per frame — so we DIRECT-
// WRITE the basemap uniform here rather than starting a 3s
// chapter-cut lerp on every emit (chained 60 FPS emits otherwise reset
// the lerp every frame, producing a slow walk instead of the intended
// sweep). The slab uses the same latitude internally biased by
// slabLatRadFromCutLatDeg so its top edge kisses the basemap edge
// instead of leaving the ~9 km band-offset gap.
function applyChapterReveal(r: NonNullable<typeof props.chapterReveal> | null): void {
  chapterCutLerp = null  // cancel any in-flight legacy lerp
  // Basemap cut: -2.0 is the "never cut" sentinel (sin can't be < -1).
  let targetSinLat = -2.0
  if (r && r.cutBasemap !== false) {
    targetSinLat = Math.sin((r.latDeg * Math.PI) / 180)
  }
  for (const s of elevatedShaders) {
    if (s.uniforms.uChapterCutSinLat) s.uniforms.uChapterCutSinLat.value = targetSinLat
  }
  // Slab: build-once on first activation; dispose on null.
  if (!r) {
    disposeChapterSlab()
    return
  }
  if (!chapterSlabMesh && !chapterSlabBuildPending) {
    // First activation. buildChapterSlab catches up to props.chapterReveal
    // at its end so the slab's first frame already has the correct
    // uniforms even if the build was deferred for texture loading.
    buildChapterSlab()
  }
  if (chapterSlabMat) {
    chapterSlabMat.uniforms.uOpacity.value = r.slabOpacity ?? 1
    chapterSlabMat.uniforms.uCutLatRad.value = slabLatRadFromCutLatDeg(r.latDeg)
    // uIdealize lerps so callers can morph the slab toward flat
    // parallel lines without jump-cutting.
    setChapterIdealizeTarget(r.idealize ?? 0)
  }
}

watch(
  () => props.chapterReveal,
  (v) => applyChapterReveal(v ?? null),
)

// Chapter-driven vertical-exaggeration override. Null clears back to
// TARGET_EXAGGERATION. Lerp duration matches CHAPTER_EXAG_MS so the
// dome deflation is gentle (looks like the ice settling, not a
// snap-cut). All overlays rebuild from currentExag inside the lerp
// tick — see animate()'s chapterExagLerp branch.
watch(
  () => props.chapterExag,
  (v) => {
    const target = v != null && Number.isFinite(v) ? (v as number) : TARGET_EXAGGERATION
    setChapterExagTarget(target, props.chapterExagMs ?? CHAPTER_EXAG_MS)
  },
)

/** A flight that was carrying the stage fit is being replaced: hand the
 *  fit back to its own timer from where it stands. */
function settleCarriedStageFit(): void {
  if (stageFitEOverride === null) return
  stageFitT = stageFitEOverride
  stageFitEOverride = null
}

function startChapterReturn(): void {
  // Lerp back to the saved state so menu / motivation see their
  // original camera framing instead of being stuck in chapter view.
  if (!chapterSavedState) return
  settleCarriedStageFit()
  // Back to the menu: the orbit path in reverse, carrying the stage fit
  // in on the same progress (the menu's fit would otherwise ease in on
  // its own 900 ms clock under the 1200 ms flight).
  const fitNow = stageFitT > 0 ? easeInOutCubic(stageFitT) : 0
  const fitTo = props.stageFit ? 1 : 0
  const orbit = makeOrbitFlight(
    [focal[0], focal[1], focal[2]], chapterSavedState.focal,
    currentLat, currentLon, currentDistance,
    chapterSavedState.lat, chapterSavedState.lon, chapterSavedState.dist,
    camera.fov, chapterSavedState.fov,
    fitNow !== fitTo ? { from: fitNow, to: fitTo } : null,
  )
  chapterLerp = {
    orbit,
    focalFrom: [focal[0], focal[1], focal[2]],
    focalTo: chapterSavedState.focal,
    latFrom: currentLat,
    latTo: chapterSavedState.lat,
    lonFrom: currentLon,
    lonTo: chapterSavedState.lon,
    distFrom: currentDistance,
    distTo: chapterSavedState.dist,
    fovFrom: camera.fov,
    fovTo: chapterSavedState.fov,
    upFrom: [cameraUp[0], cameraUp[1], cameraUp[2]],
    upTo: [
      GREENLAND_RADIAL_OUT[0],
      GREENLAND_RADIAL_OUT[1],
      GREENLAND_RADIAL_OUT[2],
    ],
    tStart: performance.now(),
    durationMs: 1200,
  }
  chapterSavedState = null
}

watch(
  () => props.chapterFocus,
  (v) => {
    if (v) {
      startChapterLerp(v)
    } else {
      startChapterReturn()
    }
  },
)

onMounted(() => {
  init()
  applyRollback(props.rollback ?? 0)
  // Warm the sim-tile satellite crop well before any drain-click needs
  // it (the source PNG is browser-cached by then; the crop itself is a
  // one-shot small canvas draw).
  window.setTimeout(() => ensureSimBaseCropTex(), 12000)
  // Debug HUD opt-in. ?debug=cam shows live camera framing values
  // as a small overlay so the agent can read them off a screenshot.
  try {
    const params = new URLSearchParams(window.location.search)
    if (params.get('debug') === 'cam') debugCam.value = true
  } catch {}
  // If we mount already past the intro (deep-link with ?clicks>=1 or
  // ?section=...), snap straight to the menu/section camera state so
  // the intro→menu phase machine doesn't run and clobber any chapter
  // lerp the parent is about to start. Forward `clicks` watcher
  // intentionally only handles backward nav, so this onMounted hook
  // is the right place to handle the initial-deeplink case.
  if (props.clicks >= 1) {
    applyClickState(props.clicks)
  }
  // Debug: scrub the rollback progress (0..1) via console or Playwright.
  // Internally maps to a uCutLon between CUT_LON_INITIAL and CUT_LON_FINAL.
  ;(window as any).__setRollback = applyRollback
  ;(window as any).__getExag = (): object => {
    const u = elevatedShaders.length > 0 ? elevatedShaders[0].uniforms.uExaggeration?.value : null
    return {
      currentExag,
      uExaggeration: u,
      chapterExagLerp: chapterExagLerp ? {
        from: chapterExagLerp.from,
        to: chapterExagLerp.to,
        elapsedMs: performance.now() - chapterExagLerp.tStart,
      } : null,
    }
  }
  ;(window as any).__getRollback = (): number => {
    if (elevatedShaders.length === 0) return -1
    const u = elevatedShaders[0].uniforms.uCutLon
    if (!u) return -2
    // Invert the mapping so the getter returns the same 0..1 progress.
    return (u.value - CUT_LON_INITIAL) / (CUT_LON_FINAL - CUT_LON_INITIAL)
  }
  // Read out the current camera state — for tuning chapter framings.
  // Drag with the mouse to position the camera (OrbitControls), then
  // run __getCamera() in the console to see the polar coords + focal
  // + a SectionCh1-ready snippet.
  //
  // Reads directly from camera.position (not the scripted
  // currentLat/Lon variables) so user-driven OrbitControls rotations
  // are picked up. Polar conversion uses +Z=north convention to match
  // the rest of this codebase.
  ;(window as any).__getCamera = (): object => {
    const px = camera.position.x
    const py = camera.position.y
    const pz = camera.position.z
    const dist = Math.sqrt(px * px + py * py + pz * pz)
    const camLatRad = Math.asin(pz / dist)
    const camLonRad = Math.atan2(py, px)
    const camLatDeg = (camLatRad * 180) / Math.PI
    const camLonDeg = (camLonRad * 180) / Math.PI
    return {
      cameraLat: Number(camLatDeg.toFixed(2)),
      cameraLon: Number(camLonDeg.toFixed(2)),
      distance:  Number(dist.toFixed(3)),
      cameraXYZ: [Number(px.toFixed(4)), Number(py.toFixed(4)), Number(pz.toFixed(4))],
      focal: focal.map((v) => Number(v.toFixed(4))),
      // Drop straight into SectionCh1.vue:
      snippet: `CAMERA_LAT=${camLatDeg.toFixed(1)}, CAMERA_LON=${camLonDeg.toFixed(1)}, FOCUS_DISTANCE=${dist.toFixed(2)}`,
    }
  }
  // Single-call scene state dump. Lets the screenshot tool capture
  // "what's on screen right now" as JSON alongside the PNG so an
  // out-of-band reader (a coding agent, a test, a log line) can reason about
  // every overlay's opacity / cut latitude / shader uniform without
  // having to interpret pixels. Round numerics aggressively — the
  // point is human / model readability, not precise replay.
  ;(window as any).__dumpScene = (): object => {
    const r2 = (n: number, d = 3): number => Number(n.toFixed(d))
    const matOpacity = (m: any): number | null =>
      m && 'opacity' in m ? r2(m.opacity) : null
    const meshDump = (mesh: THREE.Object3D | null, extras: object = {}): object => {
      if (!mesh) return { exists: false }
      const mat = (mesh as any).material as THREE.Material | undefined
      const geomVerts = ((mesh as any).geometry?.attributes?.position?.count as number | undefined) ?? null
      return {
        exists: true,
        visible: mesh.visible,
        opacity: matOpacity(mat),
        verts: geomVerts,
        ...extras,
      }
    }
    const sh0 = elevatedShaders[0]?.uniforms
    const uCutLon = sh0?.uCutLon?.value as number | undefined
    const uCutSinLat = sh0?.uChapterCutSinLat?.value as number | undefined
    const slabU = chapterSlabMat?.uniforms
    const xsU = crossSectionMat?.uniforms
    const camFocalR = Math.hypot(focal[0], focal[1], focal[2])
    return {
      phase,
      cameraMode,
      texturesPending,
      props: {
        clicks: props.clicks,
        greenlandHoverable: !!props.greenlandHoverable,
        showArrows: !!props.showArrows,
        rollback: props.rollback ?? null,
        cameraTilt: props.cameraTilt ?? null,
        chapterFocus: props.chapterFocus ?? null,
        lakeOverlay: props.lakeOverlay ?? null,
        chapterReveal: props.chapterReveal ?? null,
        lakePolygons: props.lakePolygons ?? null,
        velocityMode: props.velocityMode ?? null,
        chapterOverlay: props.chapterOverlay ?? null,
        chapterExag: props.chapterExag ?? null,
      },
      camera: {
        latDeg: r2((currentLat * 180) / Math.PI, 2),
        lonDeg: r2((currentLon * 180) / Math.PI, 2),
        distWorld: r2(currentDistance),
        fov: r2(camera?.fov ?? 0, 1),
        viewShift: r2(currentViewShift, 3),
        focalLatDeg: camFocalR > 1e-9 ? r2((Math.asin(focal[2] / camFocalR) * 180) / Math.PI, 2) : null,
        focalLonDeg: camFocalR > 1e-9 ? r2((Math.atan2(focal[1], focal[0]) * 180) / Math.PI, 2) : null,
      },
      exag: {
        currentExag: r2(currentExag, 5),
        targetExag: r2(TARGET_EXAGGERATION, 5),
        lerping: chapterExagLerp ? {
          from: r2(chapterExagLerp.from, 5),
          to: r2(chapterExagLerp.to, 5),
          elapsedMs: Math.round(performance.now() - chapterExagLerp.tStart),
        } : null,
      },
      cuts: {
        // Motivation east→west rollback. uCutLon ∈ [-5°, -37°] mapped 0..1.
        uCutLonDeg: uCutLon != null ? r2((uCutLon * 180) / Math.PI, 2) : null,
        rollbackProgress: uCutLon != null
          ? r2((uCutLon - CUT_LON_INITIAL) / (CUT_LON_FINAL - CUT_LON_INITIAL), 3)
          : null,
        // Ch.1+ south-to-NL knife. uChapterCutSinLat ∈ [-2 (off), sin(cut_lat)].
        chapterCutLatDeg: uCutSinLat != null && uCutSinLat > -1.001
          ? r2((Math.asin(uCutSinLat) * 180) / Math.PI, 2)
          : null,
        chapterCutOff: uCutSinLat == null || uCutSinLat <= -1.001,
      },
      lerps: {
        tilt: tiltLerp ? { latToDeg: r2((tiltLerp.latTo * 180) / Math.PI, 2),
                           elapsedMs: Math.round(performance.now() - tiltLerp.tStart) } : null,
        chapterFocus: chapterLerp ? { elapsedMs: Math.round(performance.now() - chapterLerp.tStart),
                                      durationMs: chapterLerp.durationMs } : null,
        chapterCut: chapterCutLerp ? { from: r2(chapterCutLerp.from, 3), to: r2(chapterCutLerp.to, 3),
                                       elapsedMs: Math.round(performance.now() - chapterCutLerp.tStart) } : null,
        chapterIdealize: chapterIdealizeLerp ? { from: r2(chapterIdealizeLerp.from, 3), to: r2(chapterIdealizeLerp.to, 3),
                                                  elapsedMs: Math.round(performance.now() - chapterIdealizeLerp.tStart) } : null,
        returning: returnLerp ? { elapsedMs: Math.round(performance.now() - returnLerp.start) } : null,
      },
      overlays: {
        // Always-mounted scene meshes.
        globe:             meshDump(globe, { colorR: r2((globe.material as THREE.MeshBasicMaterial).color.r, 2) }),
        basemap:           meshDump(basemap),
        velocityMap:       meshDump(velocityMap),
        chapterOverlay:    meshDump(chapterOverlayMesh, {
          url: chapterOverlayUrl,
          opacityTarget: r2(chapterOverlayOpacityTarget, 3),
        }),
        flowTrails:        flowMesh ? { exists: true, visible: flowMesh.visible,
                                        uOpacity: r2(flowMat?.uniforms.uOpacity.value ?? 0, 3) } : { exists: false },
        crossSectionSlab:  crossSectionMesh ? { exists: true, visible: crossSectionMesh.visible,
                                                uOpacity: r2(xsU?.uOpacity.value ?? 0, 3),
                                                uCutLonDeg: xsU ? r2((xsU.uCutLon.value * 180) / Math.PI, 2) : null } : { exists: false },
        scaleArrow:        meshDump(scaleArrow, { opacity: scaleArrowMaterials[0] ? r2(scaleArrowMaterials[0].opacity, 3) : null }),
        arrowsGroup:       meshDump(arrowsGroup, { opacity: arrowMaterials[0] ? r2(arrowMaterials[0].opacity, 3) : null }),
        // Hover affordances.
        greenlandGlow:     meshDump(greenlandGlow),
        greenlandOutline:  greenlandOutline ? { exists: true, visible: greenlandOutline.visible,
                                                 uOpacity: r2((greenlandOutline.material as THREE.ShaderMaterial).uniforms.uOpacity.value, 3) } : { exists: false },
        njGlow:            meshDump(njGlow),
        njOutline:         njOutline ? { exists: true, visible: njOutline.visible,
                                          uOpacity: r2((njOutline.material as THREE.ShaderMaterial).uniforms.uOpacity.value, 3) } : { exists: false },
        // Chapter-mediated overlays (may not exist).
        lakeOverlay:       meshDump(lakeOverlayMesh),
        lakePolyBase:      meshDump(lakePolyBaseMesh, { lakeCount: lakePolyData?.length ?? null,
                                                        opacity: lakePolyBaseMat ? r2(lakePolyBaseMat.opacity, 3) : null }),
        lakePolyHighlightFill:    meshDump(lakePolyHighlightFillMesh, { highlightId: lakePolyHighlightId,
                                                                         opacity: lakePolyHighlightFillMat ? r2(lakePolyHighlightFillMat.opacity, 3) : null }),
        lakePolyHighlightOutline: meshDump(lakePolyHighlightOutlineMesh, { opacity: lakePolyHighlightOutlineMat ? r2(lakePolyHighlightOutlineMat.opacity, 3) : null }),
        lakePolyHighlightGlow:    meshDump(lakePolyHighlightGlowMesh, { opacity: lakePolyHighlightGlowMat ? r2(lakePolyHighlightGlowMat.opacity, 3) : null }),
        streamHiTube:      meshDump(streamHiMesh, { polylineLen: streamHiPolyline?.length ?? null,
                                                     opacityTarget: r2(streamHiOpacityTarget, 3),
                                                     opacityCurrent: r2(streamHiOpacityCurrent, 3) }),
        chapterSlab:       chapterSlabMesh ? { exists: true, visible: chapterSlabMesh.visible,
                                                uOpacity: r2(slabU?.uOpacity.value ?? 0, 3),
                                                uCutLatDeg: slabU ? r2((slabU.uCutLatRad.value * 180) / Math.PI, 2) : null,
                                                uIdealize: r2(slabU?.uIdealize.value ?? 0, 3),
                                                uDrainT: r2(slabU?.uDrainT.value ?? 0, 3),
                                                uPaintT: r2(slabU?.uPaintT.value ?? 0, 3),
                                                paintUrl: slabPaintUrl } : { exists: false },
      },
      fetched: {
        flowTrails: !!flowMesh,
        lakePolygons: lakePolyUrl,
        streamHi: streamHiUrl,
      },
    }
  }
})
onBeforeUnmount(() => {
  if (animationId) cancelAnimationFrame(animationId)
  if (resizeObserver) resizeObserver.disconnect()
  if (userIdleTimerId !== null) {
    window.clearTimeout(userIdleTimerId)
    userIdleTimerId = null
  }
  if (canvasRef.value) {
    canvasRef.value.removeEventListener('mousemove', onCanvasMouseMove)
    canvasRef.value.removeEventListener('mousedown', onCanvasMouseDown)
    canvasRef.value.removeEventListener('click', onCanvasClick)
    canvasRef.value.removeEventListener('mouseleave', onCanvasMouseLeave)
  }
  if (controls) {
    controls.dispose()
    controls = null
  }
  disposeLakeStrip()
  if (renderer) {
    renderer.dispose()
  }
})
</script>

<style scoped>
.globe-wrap {
  position: absolute;
  inset: 0;
  background: black;
}
.globe-canvas {
  display: block;
  width: 100%;
  height: 100%;
}

.arrows-overlay {
  position: absolute;
  top: 6vh;
  right: 4vw;
  pointer-events: auto;
  transition: opacity 0.4s;
}

.dim-card {
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 14px;
  padding: 1.2rem 1.4rem;
  backdrop-filter: blur(10px);
  max-width: 24rem;
  color: #f5f5f5;
  font-family: 'Inter', system-ui, sans-serif;
}

.dim-card h3 {
  margin: 0 0 0.6rem 0;
  font-family: 'EB Garamond', serif;
  font-weight: 400;
  font-size: 1.4rem;
  letter-spacing: 0.02em;
}

.dim-card ul.dims {
  list-style: none;
  padding: 0;
  margin: 0 0 0.9rem 0;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.15rem 0.9rem;
}

.dim-card ul.dims li {
  display: contents;
  font-size: 0.95rem;
}

.dim-card ul.dims li .num {
  text-align: right;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.dim-card ul.dims li .unit {
  opacity: 0.7;
}

.dim-card .slr {
  margin: 0.6rem 0 0.4rem 0;
  font-size: 0.95rem;
  line-height: 1.4;
  color: #d6e8ff;
}

.dim-card .slr strong {
  color: #ffffff;
  font-weight: 700;
}

.dim-card a.cite {
  display: inline-block;
  margin-top: 0.4rem;
  font-size: 0.8rem;
  letter-spacing: 0.04em;
  color: #6cf;
  text-decoration: none;
  border-bottom: 1px dotted rgba(108, 204, 255, 0.4);
}

.dim-card a.cite:hover {
  color: #ffffff;
  border-bottom-color: rgba(255, 255, 255, 0.7);
}

/* ?debug=cam HUD: small, monospaced, fixed top-right. Each line shows
   one camera-framing scalar so screenshots are self-documenting. */
.cam-hud {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 10px 14px;
  background: rgba(0, 0, 0, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 6px;
  color: #fff;
  font: 600 12px/1.4 ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: 0.02em;
  pointer-events: none;
  z-index: 100;
}
.cam-hud div {
  display: grid;
  grid-template-columns: 38px 1fr;
  gap: 0 8px;
}
.cam-hud span {
  color: #f5c75e;
  font-weight: 500;
}
.cam-hud em {
  font-style: normal;
  opacity: 0.55;
  font-size: 10px;
  margin-left: 2px;
}
</style>
