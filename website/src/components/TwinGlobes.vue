<template>
  <!-- Ch.1's closing beat: TWO 3D Greenland OBJECTS side
       by side — absolute coupling length painted on the left, max
       surface stress on the right. One camera drives BOTH viewports
       (the director's rule: whatever is done to either side happens to
       the other), orbiting a target ON Greenland so it reads as handling
       a Greenland object, not spinning a whole globe. Mounted one beat
       early (active=false) so textures decode before the reveal. -->
  <div class="tg-root" :class="{ 'tg-hidden': !active, 'tg-closing': closing }">
    <canvas ref="canvasRef" class="tg-canvas" />
    <div v-if="active && !closing && !linger" ref="padRef" class="tg-pad" />
    <div v-if="!closing && !linger" class="tg-divider" />

    <!-- Each half's colorbar card sits in the
         TOP-RIGHT of its own frame, out of the Greenland object's way. -->
    <div class="tg-legend tg-legend-left">
      <div class="tg-cardtitle">Absolute coupling length</div>
      <div class="tg-bar tg-bar-acl" />
      <div class="tg-ticks">
        <span>0</span><span>3</span><span>6</span><span>9</span><span>12</span><span>15 km</span>
      </div>
      <div class="tg-varname">ACL [km] · γ = {{ GAMMAS[gammaIdx] }} · n = {{ NS[nIdx] }}</div>
    </div>
    <!-- The director asked to explore the parameter space ON the island —
         discretized τ_val + ℓ sliders straddling the two panels; each
         move swaps in the pre-baked drape pair for that combo (25 ACL
         tiles; τ_max depends only on ℓ, so 5 tiles there). Later:
         bigger type, the n toggle, and the "more details" door. -->
    <div v-if="active && !closing && !linger" class="tg-controls">
      <!-- The chapter's takeaway — the Conclusion page's Chapter 1 line,
           word for word (config/takeaways.ts), as Chapters 2 and 3 close
           their implications pages on theirs (the director wanted each
           chapter's implications written on its own
           implications page). The two Greenlands fill this page to its
           edges, so the line sits in the gap between them, riding on the
           controller's top edge (it comes and goes with it). -->
      <p class="tg-takeaway">{{ CH1_TAKEAWAY }}</p>
      <div class="tg-ctl-row">
        <span class="tg-ctl-sym">τ<sub>val</sub></span>
        <input
          type="range" min="0" :max="TAU_VALS.length - 1" step="1"
          v-model.number="tauIdx"
        />
        <span class="tg-ctl-val">{{ TAU_VALS[tauIdx] }} kPa</span>
      </div>
      <div class="tg-ctl-row">
        <span class="tg-ctl-sym">ℓ</span>
        <input
          type="range" min="0" :max="ELLS.length - 1" step="1"
          v-model.number="ellIdx"
        />
        <span class="tg-ctl-val">{{ ELLS[ellIdx] }} km</span>
      </div>
      <div class="tg-ctl-toggles">
        <!-- γ — the basal-friction ratio behind the
             boundary-layer length — as a two-position slider (0.1 · 0.5).
             x_bl = h·√(2/γ + 4/3) for n = 1, so γ = 0.5 halves every
             ACL; the max-stress twin does not depend on γ. -->
        <div class="tg-toggle">
          <span class="tg-ctl-sym">γ</span>
          <input
            type="range" min="0" :max="GAMMAS.length - 1" step="1"
            v-model.number="gammaIdx"
            class="tg-binary"
          />
          <span class="tg-ctl-val">{{ GAMMAS[gammaIdx] }}</span>
        </div>
        <!-- n = 1 | n = 3 — Newtonian vs Glen.
             Changes ONLY the ACL half: max τxx = ρgαℓ/4 has no n in it.
             ACL_n = [x]_n / n^(−1/(n+1)) · ln([τ]/τ_val), [x]_n =
             h·[2ⁿ(n+2+2γ)/((n+2)γ)]^(1/(n+1)) (B cancels at fixed γ). -->
        <div class="tg-toggle">
          <span class="tg-ctl-sym">n</span>
          <input
            type="range" min="0" :max="NS.length - 1" step="1"
            v-model.number="nIdx"
            class="tg-binary tg-n"
          />
          <span class="tg-ctl-val">{{ NS[nIdx] }}</span>
        </div>
        <MoreDetailsPill class="tg-more" />
      </div>
    </div>

    <div class="tg-legend tg-legend-right">
      <div class="tg-cardtitle">Maximum surface stress</div>
      <div class="tg-bar tg-bar-stress" />
      <div class="tg-ticks">
        <span>0</span><span>75</span><span>150</span><span>225</span><span>300 kPa</span>
      </div>
      <div class="tg-varname">max τₓₓ = ρgαℓ/4 [kPa]</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { mediaUrl } from '../config/media'
import { CH1_TAKEAWAY } from '../config/takeaways'
import MoreDetailsPill from './MoreDetailsPill.vue'

const props = defineProps<{
  /** False while warming up behind the theory panel (beat 11):
   *  invisible + no pointer capture; true on the twin beat. */
  active: boolean
  /** The director asked for a smooth transition to Chapter 2: true
   *  starts the CLOSE-OUT — the stress pane collapses, the ACL paint
   *  dissolves off the left greenland object, and the camera glides to
   *  Chapter 2's opening framing (matching the main globe underneath,
   *  view-shift included) — then 'closed' fires and Explore routes. */
  closing?: boolean
  /** True through Explore's post-route crossfade (`twins-linger`): the
   *  closed canvas fades over the main globe and NOTHING else of this
   *  layer may show. The director saw a flash of the colourbar from the
   *  Chapter 1 implications page while zooming to the Chapter 2
   *  lakes page — `closing` cleared the moment the
   *  linger began, so the legend cards (and the divider, the controls)
   *  snapped back to full strength and faded out with the canvas. */
  linger?: boolean
}>()

const emit = defineEmits<{ closed: [] }>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const padRef = ref<HTMLDivElement | null>(null)

// Matches Globe.vue's world: radius 0.5, +z = north pole (meshes are
// rotated x+90°), Greenland basemap patch spanning lon −75..−10,
// lat 59..84, DEM displacement at the full 90× hub exaggeration.
const GLOBE_RADIUS = 0.5
const EXAG = 0.025
// Chapter 2's main-globe exaggeration — the close-out settles the twin
// terrain to match before the crossfade.
const CLOSE_EXAG = 0.014
const twinShaders: Array<{ uniforms: any }> = []
const LAT_S = 59.0, LAT_N = 84.0
const LON_W = -75.0, LON_E = -10.0

const LIGHT_AZIMUTH = (315 * Math.PI) / 180
const LIGHT_ALTITUDE = (35 * Math.PI) / 180
const LIGHT_TANGENT = new THREE.Vector3(
  Math.sin(LIGHT_AZIMUTH) * Math.cos(LIGHT_ALTITUDE),
  Math.cos(LIGHT_AZIMUTH) * Math.cos(LIGHT_ALTITUDE),
  Math.sin(LIGHT_ALTITUDE),
).normalize()

// Opening framing ≈ the chapter's own oblique vantage (SectionCh1's
// GRIS pull-out: camera over (61.6°, −67.2°), fov 26), orbiting a
// target ON Greenland (72°, −40°) so drags handle the island itself.
function dir(latDeg: number, lonDeg: number): THREE.Vector3 {
  const la = (latDeg * Math.PI) / 180
  const lo = (lonDeg * Math.PI) / 180
  return new THREE.Vector3(
    Math.cos(la) * Math.cos(lo),
    Math.cos(la) * Math.sin(lo),
    Math.sin(la),
  )
}
const TARGET = dir(72, -40).multiplyScalar(GLOBE_RADIUS * 1.02)
const CAM_POS = dir(61.6, -67.2).multiplyScalar(0.95)
const CAM_FOV = 26

let renderer: THREE.WebGLRenderer | null = null
let rafId = 0
let resizeObserver: ResizeObserver | null = null
const disposables: Array<{ dispose: () => void }> = []
let controls: OrbitControls | null = null
let sceneL: THREE.Scene | null = null
let sceneR: THREE.Scene | null = null
let cam: THREE.PerspectiveCamera | null = null
let drapeMatL: THREE.MeshBasicMaterial | null = null
let drapeMatR: THREE.MeshBasicMaterial | null = null

// ── The τ_val × ℓ drape grid (build_twins_grid.py) ──
// Values match cinematic/data/twins/grid.json; index 1/2 = the hero
// default (30 kPa, 10 km), whose full-res pair stays acl_map.png /
// stress_map.png.
const TAU_VALS = [10, 30, 50, 70, 100]
const ELLS = [2, 5, 10, 15, 20]
// γ ∈ {0.1, 0.5}; index 0 = the hero γ (the original paths).
const GAMMAS = [0.1, 0.5]
// Flow-law exponent n ∈ {1, 3}; index 0 = the
// chapter's Newtonian n = 1 (the original paths). n = 3 tiles nest
// under twins/n3/ (build_twins_grid.py --only n3); the max-stress
// drapes are shared — max τxx has no n in it.
const NS = [1, 3]
const tauIdx = ref(1)
const ellIdx = ref(2)
const gammaIdx = ref(0)
const nIdx = ref(0)
const texCache = new Map<string, THREE.Texture>()
const texLoaded = new Set<string>()
let maxAnisoCached = 1

function comboUrls(ti: number, ei: number, gi = 0, ni = 0): { acl: string; tau: string } {
  const tv = TAU_VALS[ti]
  const el = ELLS[ei]
  // γ = 0.1 keeps the original paths; other γs nest under <n dir>/g05/
  // with a full-res hero pair partner acl_map[_n3]_g05.png.
  const gTag = `g${String(GAMMAS[gi]).replace('.', '')}`
  const gDir = gi === 0 ? '' : `${gTag}/`
  const n = NS[ni]
  const nDir = n === 1 ? '' : `n${n}/`
  if (tv === 30 && el === 10) {
    const stem = n === 1 ? 'ch01/acl_map' : `ch01/acl_map_n${n}`
    return {
      acl: mediaUrl(gi === 0 ? `${stem}.png` : `${stem}_${gTag}.png`),
      tau: mediaUrl('ch01/stress_map.png'),
    }
  }
  const t3 = String(tv).padStart(3, '0')
  const l2 = String(el).padStart(2, '0')
  return {
    acl: mediaUrl(`ch01/twins/${nDir}${gDir}acl_t${t3}_l${l2}.png`),
    tau: mediaUrl(`ch01/twins/taumax_l${l2}.png`),
  }
}

// The drape pair the controls currently ask for — a texture that
// finishes loading re-applies the combo if it is still wanted.
let wantAcl = ''
let wantTau = ''

function gridTex(url: string): THREE.Texture {
  let t = texCache.get(url)
  if (!t) {
    t = loadTex(url, () => {
      texLoaded.add(url)
      if (url === wantAcl || url === wantTau) applyCombo()
    })
    t.colorSpace = THREE.SRGBColorSpace
    t.anisotropy = maxAnisoCached
    texCache.set(url, t)
  }
  return t
}

function applyCombo(): void {
  if (!drapeMatL || !drapeMatR) return
  const { acl, tau } = comboUrls(tauIdx.value, ellIdx.value, gammaIdx.value, nIdx.value)
  wantAcl = acl
  wantTau = tau
  // Built-in map slot: the renderer refreshes material.map every
  // frame, so a plain swap shows as soon as the texture is resident.
  // Swap only once it IS resident — a still-loading texture
  // samples black, so the previous drape holds until then (the grid
  // preloads on activation, so this is normally instant).
  const tA = gridTex(acl)
  const tT = gridTex(tau)
  if (texLoaded.has(acl)) drapeMatL.map = tA
  if (texLoaded.has(tau)) drapeMatR.map = tT
}

// The sliders' 200 paint textures (n = 1 first, the chapter's default,
// then n = 3). Requested in small batches on a timer, starting while the
// twins warm behind the theory panel — the one-shot burst on arrival
// used to land ~0.5 s of image decodes on the twins' first second
// (the director found the jump from the ACL slider page to the
// painted-on-Greenland page choppy). Idempotent.
let gridPreloadStarted = false
function preloadGrid(): void {
  if ((window as any).__noGridPreload || gridPreloadStarted) return
  gridPreloadStarted = true
  const urls: string[] = []
  for (let ni = 0; ni < NS.length; ni++) {
    for (let gi = 0; gi < GAMMAS.length; gi++) {
      for (let ti = 0; ti < TAU_VALS.length; ti++) {
        for (let ei = 0; ei < ELLS.length; ei++) {
          const { acl, tau } = comboUrls(ti, ei, gi, ni)
          urls.push(acl, tau)
        }
      }
    }
  }
  const BATCH = 6
  const EVERY_MS = 120
  let i = 0
  const step = (): void => {
    if (unmounted) return
    for (let k = 0; k < BATCH && i < urls.length; k++, i++) gridTex(urls[i])
    if (i < urls.length) window.setTimeout(step, EVERY_MS)
  }
  step()
}

watch([tauIdx, ellIdx, gammaIdx, nIdx], applyCombo)

// ── Close-out: glide to Chapter 2's opening framing ──
// Matches Globe.vue's ch2 beat-0 target: camera dir(61.6, −67.2)·0.60,
// focal dir(70.1, −49.3)·R, up = radial-out at the Greenland centroid,
// fov 13, and the site-wide 0.30 view shift (subject left-of-center).
const CLOSE_MS = 1700
const CLOSE_CAM_POS = dir(61.6, -67.2).multiplyScalar(0.6)
const CLOSE_TARGET = dir(70.1, -49.3).multiplyScalar(GLOBE_RADIUS)
const CLOSE_UP = dir(72, -40)
const CLOSE_FOV = 13
const CLOSE_VIEW_SHIFT = 0.3
let closeT0 = 0
let closeFrom: {
  pos: THREE.Vector3
  target: THREE.Vector3
  up: THREE.Vector3
  fov: number
} | null = null
let closedEmitted = false

function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}

// Texture-load progress for out-of-band tooling. Separate counters
// from the main globe's __texturesPending (Globe.vue owns those).
function trackWindowCounters(delta: number): void {
  const w = window as unknown as Record<string, number>
  w.__twinTexPending = Math.max(0, (w.__twinTexPending ?? 0) + delta)
  if (delta > 0) w.__twinTexStarted = (w.__twinTexStarted ?? 0) + 1
}

function loadTex(url: string, onLoad?: () => void): THREE.Texture {
  trackWindowCounters(1)
  const t = new THREE.TextureLoader().load(
    url,
    () => {
      trackWindowCounters(-1)
      onLoad?.()
    },
    undefined,
    () => trackWindowCounters(-1),
  )
  disposables.push(t)
  return t
}

// The two 10400 × 4000 DEM PNGs, decoded OFF the main thread. Through
// loadTex() the decode ran inside texImage2D on the first render — ~0.35 s
// per DEM, the bulk of the 1.2–3 s block 1.5 s into the maps beat, when
// this component warm-mounts (found in a performance pass; a NEXT pressed
// then waited for it). createImageBitmap decodes on a worker; the upload is
// then ~35 ms. The GPU texture is byte-identical to the <img> path's in
// Chromium and WebKit (verified by a full GPU readback of both DEMs; the
// twins beat's screenshot is pixel-identical too) — for these opaque PNGs
// only: WebKit's bitmaps differ in translucent pixels, so the alpha-masked
// basemap and drapes take this path only in Chromium (`alpha` — a later
// performance pass: the mid-res basemap's decode was 0.5–1.4 s and the two
// 5200 × 2000 maps ~0.3 s more of the maps beat's 1.2–1.5 s block; the
// talk is presented in Chrome, Safari keeps loadTex()). Same CORS
// request as three's loader (same cache entry); any failure falls back to
// loadTex()'s path.
let unmounted = false
const chromiumLike = typeof (window as unknown as { chrome?: unknown }).chrome === 'object'
function loadDemTex(url: string, opts: { alpha?: boolean } = {}): THREE.Texture {
  if (opts.alpha && !chromiumLike) return loadTex(url)
  trackWindowCounters(1)
  const t = new THREE.Texture()
  let settled = false
  const settle = (): void => {
    if (!settled) {
      settled = true
      trackWindowCounters(-1)
    }
  }
  const viaImg = (): void => {
    new THREE.ImageLoader().setCrossOrigin('anonymous').load(
      url,
      (img) => {
        if (unmounted) return settle()
        t.image = img
        t.flipY = true
        t.needsUpdate = true
        settle()
      },
      undefined,
      settle,
    )
  }
  if (typeof createImageBitmap !== 'function') viaImg()
  else {
    fetch(url, { mode: 'cors', credentials: 'same-origin' })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.blob()
      })
      .then((b) => createImageBitmap(b, { imageOrientation: 'flipY', premultiplyAlpha: 'none', colorSpaceConversion: 'none' }))
      .then((bmp) => {
        if (unmounted) {
          bmp.close()
          return settle()
        }
        // The bitmap is already flipped; WebGL ignores UNPACK_FLIP_Y for it.
        t.flipY = false
        t.image = bmp
        // Uploaded once; don't hold 166 MB of decoded pixels after that.
        t.onUpdate = () => {
          t.onUpdate = null
          bmp.close()
        }
        t.needsUpdate = true
        settle()
      })
      .catch((e) => {
        console.warn('[twins] DEM bitmap decode failed, loading it as an image:', e)
        viaImg()
      })
  }
  disposables.push(t)
  return t
}

// Simplified twin of Globe.vue's attachDemDisplacement: RG16 DEM vertex
// displacement + tangent-space hillshade, minus the cut machinery.
function attachDem(
  material: THREE.MeshBasicMaterial,
  demHi: THREE.Texture,
  demHiDetail: THREE.Texture,
): void {
  material.onBeforeCompile = (shader) => {
    shader.uniforms.demMapHi = { value: demHi }
    shader.uniforms.demMapHiDetail = { value: demHiDetail }
    shader.uniforms.uExaggeration = { value: EXAG }
    shader.uniforms.uLightTangent = { value: LIGHT_TANGENT.clone() }
    twinShaders.push(shader)
    shader.vertexShader = shader.vertexShader.replace(
      '#include <common>',
      `#include <common>
       uniform sampler2D demMapHi;
       uniform float uExaggeration;
       float decodeDemRG(vec4 rgba) {
         return (rgba.r * 65280.0 + rgba.g * 255.0) / 65535.0;
       }
       float sampleDemHi(vec2 uv) {
         vec2 texSize = vec2(10400.0, 4000.0);
         vec2 px = uv * texSize - 0.5;
         vec2 pxFloor = floor(px);
         vec2 t = px - pxFloor;
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
       }`,
    )
    shader.vertexShader = shader.vertexShader.replace(
      '#include <begin_vertex>',
      `vec3 transformed = vec3( position );
       float elev = sampleDemHi(uv);
       vec3 N = normalize(position);
       transformed += N * elev * uExaggeration;`,
    )
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <common>',
      `#include <common>
       uniform sampler2D demMapHiDetail;
       uniform vec3 uLightTangent;
       float decodeDemRG(vec4 rgba) {
         return (rgba.r * 65280.0 + rgba.g * 255.0) / 65535.0;
       }`,
    )
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <map_fragment>',
      `#include <map_fragment>
       float eps = 2.0 / 2048.0;
       float hC = decodeDemRG(texture2D(demMapHiDetail, vMapUv));
       float hE = decodeDemRG(texture2D(demMapHiDetail, vMapUv + vec2(eps, 0.0)));
       float hN = decodeDemRG(texture2D(demMapHiDetail, vMapUv + vec2(0.0, eps)));
       float gE = (hE - hC) / eps;
       float gN = (hN - hC) / eps;
       vec3 nT = normalize(vec3(-gE, -gN, 2.0));
       float light = clamp(dot(nT, uLightTangent), 0.0, 1.0);
       float factor = clamp(0.55 + light * 0.5, 0.55, 1.0);
       diffuseColor.rgb *= factor;`,
    )
  }
  material.needsUpdate = true
}

function greenlandPatchGeom(): THREE.SphereGeometry {
  const phiStart = Math.PI + (LON_W * Math.PI) / 180
  const phiLength = ((LON_E - LON_W) * Math.PI) / 180
  const thetaStart = Math.PI / 2 - (LAT_N * Math.PI) / 180
  const thetaLength = ((LAT_N - LAT_S) * Math.PI) / 180
  const g = new THREE.SphereGeometry(
    GLOBE_RADIUS, 1024, 256, phiStart, phiLength, thetaStart, thetaLength,
  )
  disposables.push(g)
  return g
}

function init(): void {
  const canvas = canvasRef.value
  if (!canvas) return

  renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: true,
    preserveDrawingBuffer: true,
  })
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1))
  renderer.setClearColor(0x000000, 0)

  const maxAniso = renderer.capabilities.getMaxAnisotropy()

  // ── shared textures — the MID-RES basemap (the hi-res
  // 50 MB PNG made this beat load too slowly, and at island framing
  // the mid-res one is indistinguishable). NO earth
  // sphere at all — the basemap PNG's ocean is transparent, so each
  // side is JUST the Greenland object floating on the chalkboard. ──
  const basemapTex = loadDemTex(mediaUrl('shared/greenland_basemap.png'), { alpha: true })
  basemapTex.colorSpace = THREE.SRGBColorSpace
  basemapTex.anisotropy = maxAniso

  const demHi = loadDemTex(mediaUrl('shared/greenland_dem_rg16.png'))
  demHi.colorSpace = THREE.NoColorSpace
  demHi.minFilter = THREE.NearestFilter
  demHi.magFilter = THREE.NearestFilter
  demHi.generateMipmaps = false

  const demHiDetail = loadDemTex(mediaUrl('shared/greenland_dem_rg16_detail.png'))
  demHiDetail.colorSpace = THREE.NoColorSpace
  demHiDetail.minFilter = THREE.NearestFilter
  demHiDetail.magFilter = THREE.NearestFilter
  demHiDetail.generateMipmaps = false

  // ── shared geometry + materials ──
  const patchGeom = greenlandPatchGeom()
  const basemapMat = new THREE.MeshBasicMaterial({
    map: basemapTex,
    transparent: true,
    polygonOffset: true,
    polygonOffsetFactor: -1,
    polygonOffsetUnits: -1,
    side: THREE.DoubleSide,
  })
  attachDem(basemapMat, demHi, demHiDetail)
  disposables.push(basemapMat)

  const makeSide = (drapeUrl: string): { scene: THREE.Scene; drapeMat: THREE.MeshBasicMaterial } => {
    const scene = new THREE.Scene()

    const basemap = new THREE.Mesh(patchGeom, basemapMat)
    basemap.rotation.x = Math.PI / 2
    scene.add(basemap)

    const drapeTex = loadDemTex(drapeUrl, { alpha: true })
    drapeTex.colorSpace = THREE.SRGBColorSpace
    drapeTex.anisotropy = maxAniso
    const drapeMat = new THREE.MeshBasicMaterial({
      map: drapeTex,
      transparent: true,
      depthWrite: false,
      polygonOffset: true,
      polygonOffsetFactor: -3,
      polygonOffsetUnits: -3,
      side: THREE.DoubleSide,
    })
    attachDem(drapeMat, demHi, demHiDetail)
    disposables.push(drapeMat)
    const drape = new THREE.Mesh(patchGeom, drapeMat)
    drape.rotation.x = Math.PI / 2
    drape.renderOrder = 1
    scene.add(drape)

    return { scene, drapeMat }
  }

  maxAnisoCached = maxAniso
  const left = makeSide(mediaUrl('ch01/acl_map.png'))
  const right = makeSide(mediaUrl('ch01/stress_map.png'))
  sceneL = left.scene
  sceneR = right.scene
  drapeMatL = left.drapeMat
  drapeMatR = right.drapeMat

  const halfAspect = () => {
    const w = canvas.clientWidth || window.innerWidth
    const h = canvas.clientHeight || window.innerHeight
    return (w / 2) / Math.max(1, h)
  }
  cam = new THREE.PerspectiveCamera(CAM_FOV, halfAspect(), 0.01, 100)
  cam.up.set(0, 0, 1)
  cam.position.copy(CAM_POS)
  cam.lookAt(TARGET)

  attachControls()
  // The slider grid starts loading behind the panel, after the two
  // main drapes have had first call on the network.
  window.setTimeout(() => { if (!unmounted) preloadGrid() }, 900)

  const onResize = (): void => {
    if (!renderer || !cam) return
    const w = canvas.clientWidth || window.innerWidth
    const h = canvas.clientHeight || window.innerHeight
    renderer.setSize(w, h, false)
    cam.aspect = halfAspect()
    cam.updateProjectionMatrix()
  }
  onResize()
  resizeObserver = new ResizeObserver(onResize)
  resizeObserver.observe(canvas)

  const animate = (): void => {
    rafId = requestAnimationFrame(animate)
    if (!renderer || !sceneL || !sceneR || !cam) return
    const w = canvas.clientWidth || window.innerWidth
    const h = canvas.clientHeight || window.innerHeight
    if ((props.closing || closedEmitted) && closeFrom) {
      // ── Close-out: right pane collapses while the left greenland
      // object glides into Chapter 2's opening framing and the ACL
      // paint dissolves to the plain satellite surface. ──
      const k = Math.min(1, (performance.now() - closeT0) / CLOSE_MS)
      const e = easeInOutCubic(k)
      const hw = Math.floor(w / 2 + (w - w / 2) * e)
      cam.position.lerpVectors(closeFrom.pos, CLOSE_CAM_POS, e)
      cam.up.copy(closeFrom.up).lerp(CLOSE_UP, e).normalize()
      const tgt = closeFrom.target.clone().lerp(CLOSE_TARGET, e)
      cam.fov = closeFrom.fov + (CLOSE_FOV - closeFrom.fov) * e
      cam.aspect = hw / Math.max(1, h)
      // Site-wide view shift eases in so the island lands left-of-
      // center exactly like the main globe underneath.
      const shift = CLOSE_VIEW_SHIFT * e
      if (shift > 0.001) {
        cam.setViewOffset(hw * (1 + shift), h, hw * shift, 0, hw, h)
      } else {
        cam.clearViewOffset()
      }
      cam.updateProjectionMatrix()
      cam.lookAt(tgt)
      if (drapeMatL) drapeMatL.opacity = 1 - e
      // Terrain relief settles from the twins' 90× to Chapter 2's
      // exaggeration so the island underneath matches at crossfade.
      const exagNow = EXAG + (CLOSE_EXAG - EXAG) * e
      for (const sh of twinShaders) sh.uniforms.uExaggeration.value = exagNow
      renderer.setScissorTest(true)
      renderer.setViewport(0, 0, hw, h)
      renderer.setScissor(0, 0, hw, h)
      renderer.render(sceneL, cam)
      const rw = w - hw
      if (rw > 2) {
        // The shrinking pane renders with its OWN aspect — reusing the
        // wide left-pane projection smeared it into a funhouse strip.
        cam.aspect = rw / Math.max(1, h)
        cam.clearViewOffset()
        cam.updateProjectionMatrix()
        renderer.setViewport(hw, 0, rw, h)
        renderer.setScissor(hw, 0, rw, h)
        renderer.render(sceneR, cam)
      }
      if (k >= 1 && !closedEmitted) {
        closedEmitted = true
        emit('closed')
      }
      return
    }
    controls?.update()
    const hw = Math.floor(w / 2)
    renderer.setScissorTest(true)
    renderer.setViewport(0, 0, hw, h)
    renderer.setScissor(0, 0, hw, h)
    renderer.render(sceneL, cam)
    renderer.setViewport(hw, 0, w - hw, h)
    renderer.setScissor(hw, 0, w - hw, h)
    renderer.render(sceneR, cam)
  }
  animate()
}

// One OrbitControls, one camera, both viewports — the twin views stay
// in perfect sync. Orbits about the on-Greenland target.
function attachControls(): void {
  if (!cam || !padRef.value || controls) return
  controls = new OrbitControls(cam, padRef.value)
  controls.target.copy(TARGET)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.rotateSpeed = 0.45
  controls.enablePan = false
  controls.enableZoom = true
  controls.minDistance = 0.12
  controls.maxDistance = 1.6
  controls.update()
  // With no earth sphere the scenes hold ONLY the Greenland patch —
  // clamp the orbit to a generous cone around the opening vantage so a
  // drag can never swing behind the island (where the patch's mirrored
  // back face would read as a glitch).
  const az = controls.getAzimuthalAngle()
  const pol = controls.getPolarAngle()
  controls.minAzimuthAngle = az - 0.9
  controls.maxAzimuthAngle = az + 0.9
  controls.minPolarAngle = Math.max(0.05, pol - 0.55)
  controls.maxPolarAngle = Math.min(Math.PI - 0.05, pol + 0.5)
}

// The drag pad only exists while active — attach controls when the
// beat arrives (the component mounts one beat early to warm textures).
watch(
  () => props.active,
  async (a) => {
    if (a && !props.closing) {
      await Promise.resolve() // let the pad v-if render
      requestAnimationFrame(() => attachControls())
      preloadGrid()
    }
  },
)

watch(
  () => props.closing,
  (c) => {
    if (!c || !cam) return
    closeT0 = performance.now()
    closedEmitted = false
    closeFrom = {
      pos: cam.position.clone(),
      target: controls ? controls.target.clone() : TARGET.clone(),
      up: cam.up.clone(),
      fov: cam.fov,
    }
    controls?.dispose()
    controls = null
  },
)

onMounted(init)

onBeforeUnmount(() => {
  unmounted = true
  cancelAnimationFrame(rafId)
  resizeObserver?.disconnect()
  controls?.dispose()
  for (const d of disposables) d.dispose()
  renderer?.dispose()
  ;(window as unknown as Record<string, unknown>).__twinTexPending = 0
})
</script>

<style scoped>
/* Opaque chalkboard — covers the main globe like the theory panel. */
.tg-root {
  position: fixed;
  inset: 0;
  background:
    radial-gradient(120% 90% at 30% 20%, #12100c 0%, #0a0908 55%, #060606 100%);
  pointer-events: none;
  transition: opacity 0.9s ease;
}
/* Closing (the cards fade out) and lingering (they stay out — the
   colourbar-flash fix). */
.tg-closing .tg-legend,
.tg-root.twins-linger .tg-legend {
  opacity: 0;
  transition: opacity 0.45s ease;
}

/* Post-route crossfade: the closed twins canvas fades away
   over the main globe, which is already parked at the same framing. */
.tg-root.twins-linger {
  opacity: 0;
  transition: opacity 0.6s ease;
  pointer-events: none;
}

.tg-hidden {
  opacity: 0;
}

.tg-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}

/* One full-screen drag pad — a single set of controls drives BOTH
   viewports (they stay in sync by construction). */
.tg-pad {
  position: absolute;
  inset: 0;
  pointer-events: auto;
  cursor: grab;
  touch-action: none;
}
.tg-pad:active { cursor: grabbing; }

.tg-divider {
  position: absolute;
  top: 8vh;
  bottom: 4vh;
  left: 50%;
  width: 2px;
  background: linear-gradient(
    180deg,
    transparent,
    rgba(245, 199, 94, 0.45) 12%,
    rgba(245, 199, 94, 0.45) 88%,
    transparent
  );
}

/* The controller stays centred between the
   halves, with bigger type (labels ≥ 1.05 rem, values ≥ 1.15 rem) and
   a toggle row: γ · n · more details. */
.tg-controls {
  position: absolute;
  bottom: 3.5vh;
  left: 50%;
  transform: translateX(-50%);
  width: 500px;
  box-sizing: border-box;
  padding: 0.8rem 1.15rem 0.85rem;
  background: rgba(8, 6, 4, 0.82);
  border: 1px solid var(--gold-faint);
  border-radius: 12px;
  backdrop-filter: blur(6px);
  pointer-events: auto;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  z-index: 3;
}
/* Chapter 1's takeaway, set like Chapter 2's and 3's (EB Garamond, near
   white) but in the controller's width: it stands on the controller's
   top edge, in the dark gap between the two islands, on a soft dark
   ground where it grazes a coast. Never takes a pointer (the pad under
   it orbits the Greenlands). */
.tg-takeaway {
  position: absolute;
  left: 0;
  right: 0;
  bottom: calc(100% + 0.7rem);
  margin: 0;
  padding: 0.5rem 0.9rem 0.55rem;
  text-align: center;
  font-family: 'EB Garamond', serif;
  font-size: 1.5rem;
  line-height: 1.25;
  letter-spacing: 0.01em;
  color: #f5f5f5;
  background: rgba(8, 6, 4, 0.72);
  border-radius: 10px;
  pointer-events: none;
}

.tg-ctl-row {
  display: grid;
  grid-template-columns: 2.8rem 1fr 5.6rem;
  align-items: center;
  gap: 0.7rem;
}

.tg-ctl-sym {
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  font-size: 1.55rem;
  line-height: 1;
  color: var(--gold-bright);
  text-align: right;
}
.tg-ctl-sym sub { font-size: 0.9rem; }

.tg-ctl-val {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1.2rem;
  line-height: 1;
  color: rgba(245, 245, 245, 0.9);
  font-variant-numeric: tabular-nums;
  text-align: right;
  white-space: nowrap;
}

.tg-ctl-toggles {
  display: flex;
  align-items: center;
  gap: 1.1rem;
  padding-top: 0.15rem;
}
.tg-toggle {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.tg-toggle .tg-ctl-sym { width: 2.8rem; }
.tg-toggle .tg-ctl-val { text-align: left; min-width: 1.9rem; }
.tg-toggle + .tg-toggle .tg-ctl-sym { width: auto; }
.tg-controls .tg-more { margin-left: auto; font-size: 0.9rem; padding: 0.45rem 0.95rem; }

.tg-controls input[type='range'] {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  margin: 0;
  border-radius: 3px;
  background: rgba(245, 199, 94, 0.42);
  outline: none;
  cursor: pointer;
}
.tg-controls input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #f5c75e;
  border: 1px solid rgba(0, 0, 0, 0.55);
  cursor: grab;
}
.tg-controls input[type='range']::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #f5c75e;
  border: 1px solid rgba(0, 0, 0, 0.55);
  cursor: grab;
}

/* the two-position sliders (γ, n): a short track, its two stops marked */
.tg-controls input[type='range'].tg-binary {
  width: 60px;
  flex: none;
  background:
    radial-gradient(circle at 10px 50%, rgba(245, 199, 94, 0.75) 3px, transparent 3.5px),
    radial-gradient(circle at calc(100% - 10px) 50%, rgba(245, 199, 94, 0.75) 3px, transparent 3.5px),
    rgba(245, 199, 94, 0.42);
}

.tg-cardtitle {
  font-family: 'EB Garamond', serif;
  font-size: 1.3rem;
  line-height: 1.15;
  letter-spacing: 0.01em;
  color: var(--gold-bright);
  margin-bottom: 0.4rem;
  text-align: center;
  white-space: nowrap;
}

/* Colorbar cards: TOP-RIGHT of each half. max(11vh, 96px)
   clears the Back/Next pills, which drop below the top nav under
   1840 px (they end at 6.2vh + ~30 px). */
.tg-legend {
  position: absolute;
  top: max(11vh, 96px, calc(var(--chrome-bottom, 0px) + 0.75rem)); /* + under the ribbon's sub-menu */
  /* compact: the empty top-right corner of each half is
     only ~260 px wide before the island's north coast at 1280–1440 */
  width: 264px;
  box-sizing: border-box;
  padding: 0.55rem 0.8rem 0.5rem;
  background: rgba(8, 6, 4, 0.78);
  border: 1px solid var(--gold-dim);
  border-radius: 10px;
  backdrop-filter: blur(6px);
}
.tg-legend-left { right: calc(50% + 1.6vw); }
.tg-legend-right { right: 1.6vw; }

.tg-bar {
  height: 14px;
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.4);
}
/* turbo (matches the ACL drape) */
.tg-bar-acl {
  background: linear-gradient(
    to right,
    rgba(48, 18, 59, 0),
    rgba(40, 116, 252, 0.9) 20%,
    #1fc8de 40%,
    #7dff56 55%,
    #f9ba38 72%,
    #e5460b 88%,
    #7a0403 100%
  );
}
/* inferno (matches the stress drape) */
.tg-bar-stress {
  background: linear-gradient(
    to right,
    #000004,
    #1b0c41 14%,
    #4a0c6b 28%,
    #781c6d 42%,
    #a52c60 54%,
    #cf4446 66%,
    #ed6925 78%,
    #fb9b06 88%,
    #f7d13d 96%,
    #fcffa4 100%
  );
}

.tg-ticks {
  display: flex;
  justify-content: space-between;
  margin-top: 0.3rem;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1rem;
  line-height: 1.2;
  letter-spacing: 0;
  color: rgba(245, 245, 245, 0.96);
  font-variant-numeric: tabular-nums;
}

.tg-varname {
  margin-top: 0.3rem;
  text-align: center;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.95rem;
  line-height: 1.2;
  letter-spacing: 0.02em;
  white-space: nowrap;
  color: var(--gold);
}
</style>
