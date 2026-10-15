<template>
  <!-- Chapter 2 · THEORY: the idealized periodic slab —
       Elmer/Ice against the shallow-stream theory (config/ch2Beats.ts
       `slab` · `slab-da` · `slab-compare`, data config/ch2Slab.ts) — between
       the two flat pages: the population page
       gives way to it (a dip under the page's fade), and its three panels
       dissolve into the implications page (Ch2Results, z 9 above it).
       An opaque full-screen layer ABOVE the still-rendering globe (the
       globe is PAUSED under it, as under Chapter 1's twins — never hidden),
       its own WebGL canvas: the block, its depth average, the three panels.
       Mounted from the bed beat on so its shaders compile and the current
       run's textures are on the GPU before the beat is reachable.
       Figure labels only. -->
  <div class="cs-root">
    <div class="cs-stage" :style="{ visibility: shown ? 'visible' : 'hidden' }">
      <canvas ref="canvasEl" class="cs-canvas" />

      <!-- the field toggle: σ_t1 | τ_rr | τ_xx (the tier pills' look) -->
      <div class="cs-fields" :class="{ 'cs-locked': locked }" :style="{ top: ui.topY + 'px' }">
        <button
          v-for="f in SLAB_TALK_FIELDS"
          :key="f"
          class="cs-pill"
          :class="{ 'cs-pill-on': f === slabState.field }"
          :data-field="f"
          @click="setField(f)"
          v-html="SLAB_FIELD_HTML[f]"
        />
      </div>

      <!-- the colour bar: ONE fixed ±300 kPa scale for every run, field and
           panel (the director wanted the colorbar static;
           the v2 rasters are baked at it — nothing is recoloured here) -->
      <div v-if="cur" class="cs-cbar" :style="{ top: ui.topY + 'px' }">
        <div class="cs-cbar-title">
          <img :src="slabEqUrl((avg ? 'fb_' : 'f_') + slabState.field)" :style="eqStyle((avg ? 'fb_' : 'f_') + slabState.field, 3)" alt="" />
          <span class="cs-cbar-unit">[kPa]</span>
        </div>
        <div class="cs-cbar-bar" />
        <div class="cs-cbar-ticks">
          <span>−{{ fmtLim(vlim) }}</span><span>0</span><span>{{ fmtLim(vlim) }}</span>
        </div>
      </div>

      <!-- DEPTH AVERAGE (= NEXT), over the landed block -->
      <button
        v-if="ui.btn"
        class="cs-da-btn"
        :style="{ left: ui.btnX + 'px', top: ui.btnY + 'px' }"
        @click="emit('advance')"
      >
        <span>Depth average</span><span class="cs-da-arrow">↓</span>
      </button>

      <!-- The block's vertical exaggeration, stated (the director asked
           that it be declared on the figure) — a figure label, shown
           while the block is 3D (it fades with the ICE FLOW band). -->
      <div class="cs-vexag" :style="{ opacity: ui.flowA }" aria-hidden="true">
        <span class="cs-vexag-k">vertical exaggeration</span><span class="cs-vexag-v">{{ VEXAG }}×</span>
      </div>

      <!-- ICE FLOW along the block's far edge (Ch2FlowArrow's band) -->
      <svg class="cs-flow" :width="ui.W" :height="ui.H" :style="{ opacity: ui.flowA }" aria-hidden="true">
        <g :transform="`translate(${ui.flowX} ${ui.flowY}) rotate(${ui.flowPhi})`">
          <text x="-44" y="0" text-anchor="middle" dominant-baseline="central" class="cs-flow-lbl">ICE FLOW</text>
          <line x1="12" x2="56" y1="0" y2="0" class="cs-flow-ink" />
          <path d="M 76 0 L 50 -13 L 50 13 Z" class="cs-flow-ink" />
          <line x1="12" x2="56" y1="0" y2="0" class="cs-flow-gold" />
          <path d="M 76 0 L 50 -13 L 50 13 Z" class="cs-flow-gold" />
        </g>
      </svg>

      <!-- ICE FLOW in the top-left corner of each of the three panels
           (the ice flow direction must still be readable when the three
           panels sit side by side, so each panel carries the arrow in
           its top left corner, as the director
           asked) — the band above fades with the orbit, these fade in
           as the nadir settles, each with its panel. -->
      <svg class="cs-flow" :width="ui.W" :height="ui.H" aria-hidden="true">
        <g v-for="(pl, i) in ui.panels" :key="i" :transform="`translate(${pl.fx} ${pl.fy}) rotate(${pl.fphi})`" :opacity="pl.fa">
          <text x="0" y="0" text-anchor="start" dominant-baseline="central" class="cs-flow-lbl">ICE FLOW</text>
          <line x1="106" x2="150" y1="0" y2="0" class="cs-flow-ink" />
          <path d="M 170 0 L 144 -13 L 144 13 Z" class="cs-flow-ink" />
          <line x1="106" x2="150" y1="0" y2="0" class="cs-flow-gold" />
          <path d="M 170 0 L 144 -13 L 144 13 Z" class="cs-flow-gold" />
        </g>
      </svg>

      <!-- the three panels' titles (no "max" callouts — the director
           dropped them). Beside "Theory": Niall Coffey's headshot (the
           Acknowledgements' own) + "Coffey 2026", then Jamie Hilditch
           (the director asked for a headshot and name here too — no
           official photo exists, so the
           Acknowledgements' initials tile; the two credits sit next to
           each other, even at the cost of moving 'Theory' a little to
           the left) — the row is one box centred on the Theory panel. -->
      <template v-if="cur">
        <div
          v-for="(p, i) in PANELS"
          :key="p.id"
          class="cs-ptitle"
          :style="{ left: ui.panels[i].x + 'px', top: ui.panels[i].top + 'px', opacity: ui.panels[i].a }"
        >{{ p.title }}<span v-if="p.id === 'theory'" class="cs-credit">
          <span class="cs-credit-row"><img
            v-if="COFFEY_FACE"
            class="cs-credit-face"
            :src="COFFEY_FACE"
            alt="Niall B. Coffey"
          /><span class="cs-credit-txt">Coffey 2026</span></span>
          <span class="cs-credit-row"><img
            v-if="HILDITCH_FACE"
            class="cs-credit-face"
            :src="HILDITCH_FACE"
            alt="Jamie Hilditch"
          /><span v-else class="cs-credit-face cs-credit-initials" aria-hidden="true">JH</span
          ><span class="cs-credit-txt">Jamie Hilditch</span></span>
        </span></div>
      </template>

      <!-- the sweep's four sliders, snapping to its stops -->
      <div v-if="man" class="cs-sliders" :class="{ 'cs-locked': locked }">
        <div v-for="p in SLAB_PARAMS" :key="p.key" class="cs-sl">
          <span class="cs-sym">{{ p.sym }}</span>
          <input
            type="range"
            min="0"
            :max="stopsOf(p.key).length - 1"
            step="1"
            :value="idxOf(p.key)"
            :class="{ 'cs-binary': stopsOf(p.key).length === 2 }"
            :data-param="p.key"
            :aria-label="p.sym"
            @input="onSlide(p.key, $event)"
          />
          <span class="cs-val">{{ p.fmt(valOf(p.key)) + (p.unit === '°' ? '°' : p.unit ? ' ' + p.unit : '') }}</span>
        </div>
      </div>

      <!-- BOUNDARY CONDITIONS (the landed block only) -->
      <button
        v-if="ui.bcBtn"
        class="cs-bc-btn"
        :class="{ 'cs-bc-on': bcOn }"
        @click="bcOn = !bcOn"
      >
        <span class="cs-bc-icon">⊞</span>
        Boundary conditions
      </button>
      <Ch2SlabBcCards :active="bcOn && ui.bcBtn" :anchors="bcAnchors" :l-km="lKm" @hover="bcHover = $event" />

      <!-- the door: every field, in the Chapter 2 deeper dive -->
      <Transition name="cs-fade">
        <MoreDetailsPill
          v-if="ui.door"
          class="cs-door"
          to="/additional-work/deeper/chapter2#slab-fields"
          label="More fields"
        />
      </Transition>
    </div>
    <div class="cs-veil" :class="veilClass" aria-hidden="true" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, shallowRef, watch } from 'vue'
import * as THREE from 'three'
import { LineSegments2 } from 'three/addons/lines/LineSegments2.js'
import { LineSegmentsGeometry } from 'three/addons/lines/LineSegmentsGeometry.js'
import { LineMaterial } from 'three/addons/lines/LineMaterial.js'
import MoreDetailsPill from './MoreDetailsPill.vue'
import Ch2SlabBcCards, { type SlabBcAnchors, type SlabBcKey } from './Ch2SlabBcCards.vue'
import { CH2_BEAT_IDS, ch2IsFlatPage, ch2IsSlabPhase, ch2Phase } from '../config/ch2Beats'
import { CH2_SLAB_EQ } from '../config/ch2SlabEqs'
import { ACK_HEADSHOTS } from '../config/ackHeadshots.gen'
import { mediaUrl } from '../config/media'
import {
  CH2_SLAB_V2_PREFIX,
  SLAB_FIELD_HTML,
  SLAB_PARAMS,
  SLAB_TALK_FIELDS,
  SLAB_TALK_HERO,
  findSlabRun,
  loadSlabTalkManifest,
  parseSlabRunId,
  slabEqUrl,
  slabNeighbours,
  slabRasterUrl,
  slabState,
  type SlabField,
  type SlabParam,
  type SlabTalkManifest,
  type SlabTalkRun,
} from '../config/ch2Slab'

/** The Acknowledgements' Coauthors assets: Niall B. Coffey's headshot;
 *  Jamie Hilditch's would be too, but none exists (an initials entry in
 *  cinematic/scene_acks/headshots.json — '' here = the "JH" tile). */
function ackFace(slug: string): string {
  const f = ACK_HEADSHOTS[slug]
  return f && 'key' in f ? mediaUrl(f.key) : ''
}
const COFFEY_FACE = ackFace('niall-coffey')
const HILDITCH_FACE = ackFace('james-hilditch')

const props = defineProps<{ beat: number }>()
const emit = defineEmits<{
  /** DEPTH AVERAGE — the same as NEXT. */
  advance: []
  /** The depth-average animation has landed (slab-da → slab-compare). */
  'transit-done': []
  /** The layer owns the screen (Explore pauses the globe under it). */
  covering: [value: boolean]
}>()

// ───────────────────────── look + timings ─────────────────────────
/** Vertical exaggeration of the block: H = 3 km stands 15 % of the 100 km
 *  side (the director raised the theory slab's exaggeration to 5×; it
 *  was 3× at first). The side framing (`Tmax`) and the
 *  stated label follow it. */
const VEXAG = 5
/** The depth-averaged sheet's drawn thickness [km]. */
const SHEET = 0.45
/** Room for a panel title above the panels' top edge: the title sits 12 px
 *  above the projected panel top (the frame's bbox lands ~5 px above the
 *  band's top), the Theory row with its two faces is ~38 px tall, + 8 px
 *  clear of the colourbar: 12 + 38 + 8 + 6. */
const TITLE_ROOM = 64
/** The slope, drawn ×4 (α = 0.1–1° would not read at true scale). */
const TILT_EXAG = 4
/** The side view (the centre-lake blocks' oblique look): azimuth from
 *  south (− = west of south) and elevation. */
const SIDE_AZ = (-22 * Math.PI) / 180
const SIDE_EL = (31 * Math.PI) / 180
const NADIR_EL = (89.95 * Math.PI) / 180
const FOV = 18
/** The three panels: px gap between them. */
const PANEL_GAP = 40
/** THE DEPTH AVERAGE (forward) and its reverse, ms. The collapse (5.2 s,
 *  easeInOutSine) — its progress t is the depth d = t·H the surface paint
 *  has been averaged down to (the director's rule: no wipe line; at
 *  any given timestep along the depth averaging, the stress pattern that is
 *  being projected to the surface is the value of the in-progress depth
 *  averaging); then the director's 2 s pause; the orbit to nadir; the slide. */
interface Seg { key: keyof typeof P; t0: number; dur: number; ease: (t: number) => number }
const sine = (t: number) => -(Math.cos(Math.PI * t) - 1) / 2
const cubic = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)
const lin = (t: number) => t
const FWD: Seg[] = [
  { key: 'depth', t0: 0, dur: 5200, ease: sine },
  { key: 'orbit', t0: 7200, dur: 2200, ease: cubic },
  { key: 'slide', t0: 9300, dur: 1200, ease: cubic },
  { key: 'theory', t0: 9800, dur: 1100, ease: cubic },
  { key: 'diff', t0: 10200, dur: 1100, ease: cubic },
  { key: 'labels', t0: 10800, dur: 700, ease: lin },
]
const REV: Seg[] = [
  { key: 'labels', t0: 0, dur: 300, ease: lin },
  { key: 'diff', t0: 0, dur: 500, ease: cubic },
  { key: 'theory', t0: 150, dur: 500, ease: cubic },
  { key: 'slide', t0: 400, dur: 900, ease: cubic },
  { key: 'orbit', t0: 1100, dur: 1800, ease: cubic },
  { key: 'depth', t0: 2700, dur: 2000, ease: sine },
]
const PANELS = [
  { id: 'sim', title: 'Simulation' },
  { id: 'theory', title: 'Theory' },
  { id: 'diff', title: 'Simulation − Theory' },
] as const

// The choreography's progress values (0 = the landed block, 1 = the
// three panels). Everything on screen is a function of these.
const P = { depth: 0, orbit: 0, slide: 0, theory: 0, diff: 0, labels: 0 }
type PKey = keyof typeof P
const PKEYS = Object.keys(P) as PKey[]

// ───────────────────────── state ─────────────────────────
const canvasEl = ref<HTMLCanvasElement | null>(null)
const man = shallowRef<SlabTalkManifest | null>(null)
const shown = ref(false)
const bcOn = ref(false)
const bcHover = ref<SlabBcKey | null>(null)
const bcAnchors = shallowRef<SlabBcAnchors | null>(null)
const locked = ref(false)
const veil = ref<'off' | 'in' | 'on'>('off')
const veilClass = computed(() => ({ 'cs-veil-in': veil.value === 'in', 'cs-veil-on': veil.value === 'on' }))
const ui = reactive({
  W: window.innerWidth,
  H: window.innerHeight,
  topY: 110,
  btn: false,
  btnX: 0,
  btnY: 0,
  bcBtn: false,
  door: false,
  flowX: -999,
  flowY: -999,
  flowPhi: 0,
  flowA: 0,
  panels: [0, 1, 2].map(() => ({ x: 0, top: 0, bottom: 0, a: 0, fx: -999, fy: -999, fphi: 0, fa: 0 })),
})
const avg = ref(false)

const cur = computed<SlabTalkRun | null>(() => man.value?.runs[slabState.run] ?? null)
/** The fixed colour scale [kPa] (the manifest's; contract v2 = 300). */
const vlim = computed(() => man.value?.vlim_kpa ?? 300)
/** The simulation's periodic domain [km] (the BC cards' L). */
const lKm = computed(() => {
  const d = cur.value?.domain_km
  return d ? Math.round(d[1] - d[0]) : 100
})
/** The block + the three panels show the CENTRAL HALF of the domain (±25 km
 *  about the patch; the director's choice: at the fixed ±300 kPa
 *  the R 2.5 km pattern is a small feature on the full 100 km) — a UV crop
 *  of the rasters, the geometry a VIEW_CROP·L square. */
const VIEW_CROP = 0.5
const viewKm = computed(() => lKm.value * VIEW_CROP)
function fmtLim(v: number): string {
  return String(Math.round(v * 10) / 10)
}
function eqStyle(name: string, k: number): Record<string, string> {
  const b = CH2_SLAB_EQ[name]
  return b ? { width: `${b.w * k}px`, height: `${b.h * k}px` } : { display: 'none' }
}

// ── sliders ──
function stopsOf(k: SlabParam): number[] {
  const p = man.value?.params
  if (!p) return [0]
  return k === 'H' ? p.H : k === 'alpha_deg' ? p.alpha_deg : k === 'gamma' ? p.gamma : p.R
}
function valOf(k: SlabParam): number {
  return cur.value ? cur.value[k] : 0
}
function idxOf(k: SlabParam): number {
  const s = stopsOf(k)
  const v = valOf(k)
  let j = 0
  for (let i = 0; i < s.length; i++) if (Math.abs(s[i] - v) < Math.abs(s[j] - v)) j = i
  return j
}
function onSlide(k: SlabParam, e: Event): void {
  const m = man.value
  const r = cur.value
  if (!m || !r || locked.value) return
  const i = parseInt((e.target as HTMLInputElement).value, 10)
  const want = { H: r.H, alpha_deg: r.alpha_deg, gamma: r.gamma, R: r.R }
  want[k] = stopsOf(k)[i]
  const id = findSlabRun(m, want, k)
  if (id && id !== slabState.run) slabState.run = id
  else (e.target as HTMLInputElement).value = String(idxOf(k))
}
function setField(f: SlabField): void {
  if (!locked.value) slabState.field = f
}

// ───────────────────────── three.js ─────────────────────────
let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let raf = 0
let alive = true

const texCache = new Map<string, THREE.Texture>()
const texLoads = new Map<string, Promise<THREE.Texture | null>>()
const texUsed = new Map<string, number>()
let texPending = 0
const loader = new THREE.TextureLoader()
loader.setCrossOrigin('anonymous')
const blankTex = new THREE.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1)
blankTex.needsUpdate = true

function loadTex(path: string): Promise<THREE.Texture | null> {
  const url = slabRasterUrl(path, true, CH2_SLAB_V2_PREFIX)
  texUsed.set(url, performance.now())
  const hit = texCache.get(url)
  if (hit) return Promise.resolve(hit)
  const inflight = texLoads.get(url)
  if (inflight) return inflight
  texPending++
  const p = loader
    .loadAsync(url)
    .then(async (t) => {
      // decode off the main thread now, not synchronously inside the
      // texImage2D of the first upload (a slider move's hitch)
      try {
        await (t.image as HTMLImageElement).decode?.()
      } catch {
        /* the upload decodes it then */
      }
      t.colorSpace = THREE.SRGBColorSpace
      t.anisotropy = renderer?.capabilities.getMaxAnisotropy() ?? 1
      t.generateMipmaps = true
      t.minFilter = THREE.LinearMipmapLinearFilter
      texCache.set(url, t)
      pruneTex()
      return t
    })
    .catch(() => {
      console.warn('[slab] texture failed', url)
      return null
    })
    .finally(() => {
      texPending--
      texLoads.delete(url)
    })
  texLoads.set(url, p)
  return p
}
/** Keep the GPU/decoded set bounded: drop the least recently used beyond
 *  TEX_KEEP — never one a material is showing, nor any of the current run's
 *  (all its cum levels of the three fields + theory + diff, ~39). */
const TEX_KEEP = 72
const protectUrls = new Set<string>()
function pruneTex(): void {
  if (texCache.size <= TEX_KEEP) return
  const inUse = new Set<THREE.Texture>(shownLevels.filter(Boolean) as THREE.Texture[])
  for (const m of paintMats()) for (const k of ['uA', 'uB'] as const) inUse.add(m.uniforms[k].value)
  if (simFade) inUse.add(simFade.from)
  const order = [...texCache.keys()].sort((a, b) => (texUsed.get(a) ?? 0) - (texUsed.get(b) ?? 0))
  for (const url of order) {
    if (texCache.size <= TEX_KEEP) break
    const t = texCache.get(url)!
    if (inUse.has(t) || protectUrls.has(url)) continue
    t.dispose()
    texCache.delete(url)
  }
}
const uploaded = new WeakSet<THREE.Texture>()
function upload(t: THREE.Texture | null): void {
  if (!t || !renderer || uploaded.has(t)) return
  renderer.initTexture(t)
  uploaded.add(t)
}
/** Uploads while the layer is on screen go through a queue drained under a
 *  per-frame budget (a run's 13–39 textures at once stalled a frame). */
const uploadQ: { t: THREE.Texture; done?: () => void }[] = []
function queueUpload(t: THREE.Texture | null, done?: () => void): void {
  if (!t || uploaded.has(t)) {
    done?.()
    return
  }
  uploadQ.push({ t, done })
}
function uploadAll(ts: (THREE.Texture | null)[]): Promise<void> {
  if (!shown.value) {
    for (const t of ts) upload(t)
    return Promise.resolve()
  }
  return Promise.all(ts.map((t) => new Promise<void>((res) => queueUpload(t, res)))).then(() => {})
}
const UPLOAD_BUDGET_MS = 6
function drainUploads(): void {
  const t0 = performance.now()
  while (uploadQ.length && performance.now() - t0 < UPLOAD_BUDGET_MS) {
    const j = uploadQ.shift()!
    upload(j.t)
    j.done?.()
  }
}
/** A neighbour run's rasters into the HTTP cache only (no decode, no GPU):
 *  a slider move then decodes from cache before it swaps. */
const warmed = new Set<string>()
function warmHttp(path: string): void {
  const url = slabRasterUrl(path, true, CH2_SLAB_V2_PREFIX)
  if (warmed.has(url) || texCache.has(url)) return
  warmed.add(url)
  void fetch(url, { mode: 'cors', credentials: 'same-origin' })
    .then((r) => r.blob())
    .catch(() => warmed.delete(url))
}

// The paint: ONE mix of two textures — on the simulation block the two cum
// levels either side of the in-progress depth (or, at rest, a run / field
// crossfade); on the theory + difference panels a run / field crossfade —
// and the free-slip patch dashed.
const PAINT_VS = /* glsl */ `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`
const PAINT_FS = /* glsl */ `
uniform sampler2D uA; uniform sampler2D uB; uniform float uMix;
uniform vec2 uC; uniform float uL; uniform float uR; uniform float uOpacity;
uniform vec2 uCropO; uniform float uCropS;
varying vec2 vUv;
void main() {
  vec2 st = uCropO + vUv * uCropS; // the shown window of the raster
  vec3 col = mix(texture2D(uA, st).rgb, texture2D(uB, st).rgb, uMix);
  // the free-slip patch: a dashed black circle of radius R (2.6 px)
  vec2 q = (vUv - uC) * uL;
  float r = length(q);
  float w = fwidth(r);
  float ring = 1.0 - smoothstep(1.3 * w, 2.3 * w, abs(r - uR));
  float ang = atan(q.y, q.x);
  float dash = step(fract(ang / 6.2831853 * 28.0), 0.56);
  col = mix(col, vec3(0.02), ring * dash);
  gl_FragColor = vec4(col, uOpacity);
  #include <colorspace_fragment>
}`
function makePaintMat(): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: {
      uA: { value: blankTex },
      uB: { value: blankTex },
      uMix: { value: 0 },
      uC: { value: new THREE.Vector2(0.5, 0.5) },
      uL: { value: 100 },
      uCropO: { value: new THREE.Vector2(0, 0) },
      uCropS: { value: 1 },
      uR: { value: 5 },
      uOpacity: { value: 1 },
    },
    vertexShader: PAINT_VS,
    fragmentShader: PAINT_FS,
    transparent: true,
    polygonOffset: true,
    polygonOffsetFactor: -2,
    polygonOffsetUnits: -2,
  })
}

// Ice walls: the centre-lake blocks' pale ice, shaded per face.
const WALL = {
  px: 0x93a6bc, // +x (downstream) wall
  nx: 0xa9bacd,
  py: 0xb9c7d6, // far side
  ny: 0xc7d4e2, // the near side
  bot: 0x5d6b7c,
}
const GOLD = 0xf4cf6a
const GOLD_C = new THREE.Color(GOLD)
interface Slab {
  group: THREE.Group // position / tilt
  zg: THREE.Group // scale.z = drawn thickness
  body: THREE.Mesh
  wallMats: THREE.MeshBasicMaterial[]
  paint: THREE.Mesh
  paintMat: THREE.ShaderMaterial
  lineMat: LineMaterial
  inkMat: LineMaterial
}
let sim: Slab
let theoryP: Slab
let diffP: Slab
function paintMats(): THREE.ShaderMaterial[] {
  return [sim, theoryP, diffP].filter(Boolean).map((s) => s.paintMat)
}

function makeSlab(L: number): Slab {
  const group = new THREE.Group()
  const zg = new THREE.Group()
  group.add(zg)
  const g = new THREE.BoxGeometry(L, L, 1)
  g.translate(0, 0, 0.5)
  const mk = (c: number) => new THREE.MeshBasicMaterial({ color: c, transparent: true })
  const wallMats = [mk(WALL.px), mk(WALL.nx), mk(WALL.py), mk(WALL.ny), mk(0x000000), mk(WALL.bot)]
  wallMats[4].visible = false // the top is the paint
  const body = new THREE.Mesh(g, wallMats)
  zg.add(body)
  const paintMat = makePaintMat()
  const paint = new THREE.Mesh(new THREE.PlaneGeometry(L, L), paintMat)
  paint.position.z = 1
  paint.renderOrder = 2
  zg.add(paint)
  // the twelve edges: black 5.5 px under gold 2.2 px (the Globe's block rim)
  const h = L / 2
  const c = [
    [-h, -h], [h, -h], [h, h], [-h, h],
  ]
  const pos: number[] = []
  for (let i = 0; i < 4; i++) {
    const [ax, ay] = c[i]
    const [bx, by] = c[(i + 1) % 4]
    pos.push(ax, ay, 1, bx, by, 1, ax, ay, 0, bx, by, 0, ax, ay, 0, ax, ay, 1)
  }
  const lg = new LineSegmentsGeometry()
  lg.setPositions(pos)
  const lineMat = new LineMaterial({ color: GOLD, linewidth: 2.2, transparent: true, depthWrite: false })
  const inkMat = new LineMaterial({ color: 0x050505, linewidth: 5.5, transparent: true, depthWrite: false })
  const line = new LineSegments2(lg, lineMat)
  const ink = new LineSegments2(lg, inkMat)
  line.renderOrder = 5
  ink.renderOrder = 4
  line.frustumCulled = false
  ink.frustumCulled = false
  zg.add(ink, line)
  return { group, zg, body, wallMats, paint, paintMat, lineMat, inkMat }
}
function setSlabOpacity(s: Slab, a: number): void {
  s.group.visible = a > 0.002
  for (const m of s.wallMats) m.opacity = a
  s.paintMat.uniforms.uOpacity.value = a
  s.lineMat.opacity = a
  s.inkMat.opacity = a
}

// the x / y / z triad at the block's right-most corner (the Globe's)
let triad: THREE.Group | null = null
const triadMats: THREE.Material[] = []
function labelMat(letter: string): THREE.SpriteMaterial {
  const S = 128
  const cv = document.createElement('canvas')
  cv.width = S
  cv.height = S
  const tex = new THREE.CanvasTexture(cv)
  tex.colorSpace = THREE.SRGBColorSpace
  const draw = () => {
    const ctx = cv.getContext('2d')!
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
  document.fonts?.load('italic 500 96px "EB Garamond"').then(draw).catch(() => {})
  const m = new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false })
  triadMats.push(m)
  return m
}
function buildTriad(L: number, corner: [number, number]): void {
  if (triad) {
    scene.remove(triad)
    triad.traverse((o) => (o as THREE.Mesh).geometry?.dispose())
  }
  const [cx, cy] = corner
  const xs = Math.sign(cx)
  const ys = Math.sign(cy)
  // outside the corner, at bed level (clear of the walls)
  const O = new THREE.Vector3(cx + xs * (ys < 0 ? 0.16 : 0.05) * L, cy + ys * (xs < 0 ? 0.16 : 0.05) * L, 0)
  const len = 0.14 * L
  const head = 0.042 * L
  const g = new THREE.Group()
  const shaftMat = new LineMaterial({ color: 0xf3ead2, linewidth: 2.2, transparent: true, depthWrite: false })
  const headMat = new THREE.MeshBasicMaterial({ color: 0xf3ead2, transparent: true })
  triadMats.push(shaftMat, headMat)
  const pos: number[] = []
  const axes: [string, THREE.Vector3][] = [
    ['x', new THREE.Vector3(1, 0, 0)],
    ['y', new THREE.Vector3(0, 1, 0)],
    ['z', new THREE.Vector3(0, 0, 1)],
  ]
  for (const [letter, dir] of axes) {
    const tip = O.clone().addScaledVector(dir, len)
    const shaftEnd = tip.clone().addScaledVector(dir, -head * 0.9)
    pos.push(O.x, O.y, O.z, shaftEnd.x, shaftEnd.y, shaftEnd.z)
    const cone = new THREE.Mesh(new THREE.ConeGeometry(head * 0.32, head, 14), headMat)
    cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir)
    cone.position.copy(tip).addScaledVector(dir, -head / 2)
    g.add(cone)
    const sp = new THREE.Sprite(labelMat(letter))
    sp.position.copy(tip).addScaledVector(dir, 0.06 * L)
    sp.scale.set(0.085 * L, 0.085 * L, 1)
    g.add(sp)
  }
  const lg = new LineSegmentsGeometry()
  lg.setPositions(pos)
  g.add(new LineSegments2(lg, shaftMat))
  g.traverse((o) => (o.frustumCulled = false))
  triad = g
  scene.add(g)
}
function setTriadOpacity(a: number): void {
  if (!triad) return
  triad.visible = a > 0.01
  for (const m of triadMats) (m as THREE.MeshBasicMaterial).opacity = a
}

// ── the live (smoothed) geometry: thickness, tilt, patch radius ──
const live = { T: 9, tilt: 0, R: 5 }
const target = { T: 9, tilt: 0, R: 5 }
function setTargets(snap: boolean): void {
  const r = cur.value
  if (!r) return
  target.T = (r.H / 1000) * VEXAG
  target.tilt = (r.alpha_deg * TILT_EXAG * Math.PI) / 180
  target.R = r.patch_km ?? r.R / 1000
  if (snap) Object.assign(live, target)
}

// ── framing ──
interface Frame { d: number; offX: number; offY: number; tz: number; ty: number }
const side: Frame = { d: 400, offX: 0, offY: 0, tz: 0, ty: 0 }
const sideGoal: Frame = { ...side }
const nadir: Frame = { d: 600, offX: 0, offY: 0, tz: 0, ty: 0 }
let panelPx = 400
let worldGap = 10
let sideCorner: [number, number] = [50, -50]

function placeCamera(az: number, el: number, f: Frame): void {
  const t = new THREE.Vector3(0, f.ty, f.tz)
  const ce = Math.cos(el)
  camera.position.set(t.x + f.d * Math.sin(az) * ce, t.y - f.d * Math.cos(az) * ce, t.z + f.d * Math.sin(el))
  camera.up.set(-Math.sin(az) * Math.sin(el), Math.cos(az) * Math.sin(el), Math.cos(el))
  camera.lookAt(t)
  camera.setViewOffset(ui.W, ui.H, f.offX, f.offY, ui.W, ui.H)
  camera.updateProjectionMatrix()
  camera.updateMatrixWorld()
}
const _v = new THREE.Vector3()
function toScreen(p: THREE.Vector3): { x: number; y: number } {
  _v.copy(p).project(camera)
  return { x: (_v.x * 0.5 + 0.5) * ui.W, y: (-_v.y * 0.5 + 0.5) * ui.H }
}
/** Solve distance + offset so `pts` fill (maxW × maxH) centred on (cx, cy). */
function fit(pts: THREE.Vector3[], az: number, el: number, f: Frame, cx: number, cy: number, maxW: number, maxH: number): void {
  f.offX = 0
  f.offY = 0
  for (let it = 0; it < 5; it++) {
    placeCamera(az, el, f)
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity
    for (const p of pts) {
      const s = toScreen(p)
      x0 = Math.min(x0, s.x); x1 = Math.max(x1, s.x); y0 = Math.min(y0, s.y); y1 = Math.max(y1, s.y)
    }
    const k = Math.min(maxW / (x1 - x0), maxH / (y1 - y0))
    if (it < 4) f.d /= k
    else {
      f.offX = (x0 + x1) / 2 - cx
      f.offY = (y0 + y1) / 2 - cy
    }
  }
}
/** The page furniture's bands (measured): the ribbon + pills above, the
 *  sliders below. */
function bands(): { top: number; bottom: number } {
  let b = 0
  for (const sel of ['.top-nav-wrap', '.beat-nav']) {
    const r = document.querySelector(sel)?.getBoundingClientRect()
    if (r && r.height > 0) b = Math.max(b, r.bottom)
  }
  const top = Math.max(96, b + 12)
  const sl = document.querySelector('.cs-sliders')?.getBoundingClientRect()
  const bottom = sl && sl.height > 0 ? sl.top - 12 : ui.H - 120
  return { top, bottom }
}
function reframe(snap: boolean): void {
  if (!renderer || !cur.value) return
  ui.W = window.innerWidth
  ui.H = window.innerHeight
  camera.aspect = ui.W / ui.H
  const { top, bottom } = bands()
  ui.topY = top
  const L = viewKm.value
  const h = L / 2
  // side: the block at its tallest (H = 3 km) so a slider never reframes it
  const Tmax = (Math.max(...(man.value?.params.H ?? [3000])) / 1000) * VEXAG
  const pts: THREE.Vector3[] = []
  for (const x of [-h, h]) for (const y of [-h, h]) for (const z of [0, Tmax]) pts.push(new THREE.Vector3(x, y, z))
  const sTop = top + 64 + 46 // the pills band + the DEPTH AVERAGE button
  const sBot = bottom - 8
  const maxW = bcOn.value ? ui.W - 2 * 380 : Math.min(0.62 * ui.W, ui.W - 2 * 300)
  sideGoal.tz = Tmax / 2
  sideGoal.ty = 0
  sideGoal.d = side.d || 400
  fit(pts, SIDE_AZ, SIDE_EL, sideGoal, ui.W / 2, (sTop + sBot) / 2, maxW, sBot - sTop)
  if (snap) Object.assign(side, sideGoal)
  // the corner that sits right-most → the triad
  placeCamera(SIDE_AZ, SIDE_EL, sideGoal)
  let best = -Infinity
  for (const [x, y] of [[-h, -h], [h, -h], [h, h], [-h, h]] as [number, number][]) {
    const s = toScreen(new THREE.Vector3(x, y, 0))
    if (s.x > best) { best = s.x; sideCorner = [x, y] }
  }
  buildTriad(L, sideCorner)
  // nadir: three equal panels between the bands, titles above, callouts below.
  // The band above the panels holds the field pills + the DEPTH AVERAGE
  // button on the left and the COLOURBAR on the right, and the titles hang
  // above the panels' top edge — so the panels start below whichever is
  // taller (the colour bar must clear the Simulation / Theory titles on
  // short viewports — at 1280×720 / 1366×768 the
  // height-limited panels rose until the right title sat under the bar).
  const cbarH = document.querySelector('.cs-cbar')?.getBoundingClientRect().height || 78
  const pTop = top + Math.max(64 + 44, cbarH + TITLE_ROOM)
  const pBot = bottom - 40
  panelPx = Math.min((ui.W - 2 * 28 - 2 * PANEL_GAP) / 3, pBot - pTop)
  worldGap = (PANEL_GAP * L) / panelPx
  const X = 1.5 * L + worldGap
  const np = [new THREE.Vector3(-X, -h, 0), new THREE.Vector3(X, -h, 0), new THREE.Vector3(-X, h, 0), new THREE.Vector3(X, h, 0)]
  nadir.tz = 0
  nadir.ty = 0
  nadir.d = nadir.d || 600
  fit(np, 0, NADIR_EL, nadir, ui.W / 2, (pTop + pBot) / 2, 3 * panelPx + 2 * PANEL_GAP, panelPx)
  for (const m of [sim, theoryP, diffP]) {
    m.lineMat.resolution.set(ui.W, ui.H)
    m.inkMat.resolution.set(ui.W, ui.H)
  }
  for (const m of triadMats) if (m instanceof LineMaterial) m.resolution.set(ui.W, ui.H)
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t
}
const camF: Frame = { d: 0, offX: 0, offY: 0, tz: 0, ty: 0 }

// ── the per-frame scene ──
let lastT = performance.now()
function frame(now: number): void {
  raf = requestAnimationFrame(frame)
  const dt = Math.min(0.1, (now - lastT) / 1000)
  lastT = now
  if (renderer) drainUploads()
  if (!renderer || !shown.value) return
  stepAnim(now)
  stepFades(now)
  const k = 1 - Math.exp(-dt / 0.28)
  live.T += (target.T - live.T) * k
  live.tilt += (target.tilt - live.tilt) * k
  live.R += (target.R - live.R) * k
  const kc = 1 - Math.exp(-dt / 0.35)
  for (const key of ['d', 'offX', 'offY', 'tz', 'ty'] as const) side[key] += (sideGoal[key] - side[key]) * kc
  drawState()
  renderer.render(scene, camera)
}

function drawState(): void {
  const r = cur.value
  if (!r) return
  const L = viewKm.value
  const o = P.orbit
  // camera: the side view → nadir
  const az = lerp(SIDE_AZ, 0, o)
  const el = lerp(SIDE_EL, NADIR_EL, o)
  camF.d = Math.exp(lerp(Math.log(side.d), Math.log(nadir.d), o))
  camF.offX = lerp(side.offX, nadir.offX, o)
  camF.offY = lerp(side.offY, nadir.offY, o)
  camF.tz = lerp(side.tz, nadir.tz, o)
  camF.ty = lerp(side.ty, nadir.ty, o)
  placeCamera(az, el, camF)
  // the simulation block: the collapse, tilt (eased flat by nadir), slide;
  // its top paint = the cumulative depth average down to d = P.depth · H
  const thick = lerp(live.T, SHEET, P.depth)
  sim.zg.scale.z = Math.max(0.01, thick)
  sim.group.rotation.y = live.tilt * (1 - o)
  sim.group.position.x = -(L + worldGap) * P.slide
  paintSim(performance.now())
  for (const s of [sim, theoryP, diffP]) {
    const u = s.paintMat.uniforms
    u.uR.value = live.R
    // the window: VIEW_CROP of the raster centred on the patch (0, 0)
    const dx = r.domain_km[1] - r.domain_km[0]
    const dy = r.domain_km[3] - r.domain_km[2]
    u.uCropS.value = VIEW_CROP
    u.uCropO.value.set((0 - r.domain_km[0]) / dx - VIEW_CROP / 2, (0 - r.domain_km[2]) / dy - VIEW_CROP / 2)
    u.uL.value = L
    u.uC.value.set(0.5, 0.5)
  }
  avg.value = P.depth > 0.5
  // the theory + difference panels rise
  for (const [s, t, x] of [[theoryP, P.theory, 0], [diffP, P.diff, L + worldGap]] as [Slab, number, number][]) {
    s.zg.scale.z = SHEET
    s.group.position.set(x, -0.16 * L * (1 - t), 0)
    // opaque early in its rise (a slow fade reads as a grey card)
    setSlabOpacity(s, Math.min(1, 2.5 * t))
  }
  // the walls a BC card names light gold
  const hx = bcOn.value && bcHover.value === 'perx'
  const hy = bcOn.value && bcHover.value === 'pery'
  const hb = bcOn.value && bcHover.value === 'bed'
  const gold = GOLD_C
  const base = [WALL.px, WALL.nx, WALL.py, WALL.ny, 0, WALL.bot]
  sim.wallMats.forEach((m, i) => {
    if (i === 4) return
    const lit = (hx && i < 2) || (hy && (i === 2 || i === 3)) || (hb && i === 5)
    m.color.set(base[i])
    if (lit) m.color.lerp(gold, 0.55)
  })
  setTriadOpacity(bcOn.value ? 0 : Math.max(0, 1 - 3 * o))
  overlays()
}

/** Screen positions of the HTML furniture (written only when they move). */
function overlays(): void {
  const L = viewKm.value
  const h = L / 2
  const o = P.orbit
  const top = sim.zg.scale.z
  const onSlab = phaseId() === 'slab'
  // DEPTH AVERAGE: above the block's top face (its highest projected corner)
  const tops = [[-h, -h], [h, -h], [h, h], [-h, h]].map(([x, y]) => toScreen(sim.paint.localToWorld(new THREE.Vector3(x, y, 0))))
  const minY = Math.min(...tops.map((p) => p.y))
  const cx = tops.reduce((s, p) => s + p.x, 0) / 4
  ui.btn = onSlab && !anim && P.depth === 0 && !bcOn.value
  ui.btnX = Math.round(cx)
  ui.btnY = Math.round(minY - 30)
  ui.bcBtn = onSlab && !anim && P.depth === 0
  // ICE FLOW: along the far (+y) top edge's upstream half, lifted off it
  const a = toScreen(sim.paint.localToWorld(new THREE.Vector3(-0.42 * L, h, 0)))
  const b = toScreen(sim.paint.localToWorld(new THREE.Vector3(-0.02 * L, h, 0)))
  let phi = (Math.atan2(b.y - a.y, b.x - a.x) * 180) / Math.PI
  const nx = Math.sin((phi * Math.PI) / 180)
  const ny = -Math.cos((phi * Math.PI) / 180)
  ui.flowX = Math.round((a.x + b.x) / 2 + nx * 26)
  ui.flowY = Math.round((a.y + b.y) / 2 + ny * 26)
  ui.flowPhi = Math.round(phi * 10) / 10
  ui.flowA = Math.max(0, 1 - 4 * o) * (top > 0 ? 1 : 0)
  // the panels' titles
  const xs = [-(L + worldGap) * P.slide, 0, L + worldGap]
  const as = [P.labels, P.labels * P.theory, P.labels * P.diff]
  for (let i = 0; i < 3; i++) {
    const yT = i === 0 ? 0 : -0.16 * L * (1 - (i === 1 ? P.theory : P.diff))
    const t = toScreen(new THREE.Vector3(xs[i], h + yT, 0))
    const bt = toScreen(new THREE.Vector3(xs[i], -h + yT, 0))
    const pl = ui.panels[i]
    pl.x = Math.round(t.x)
    pl.top = Math.round(t.y - 12)
    pl.bottom = Math.round(bt.y + 12)
    pl.a = Math.round(as[i] * 100) / 100
    // ICE FLOW in the panel's top-left corner, along its +x (downstream) edge
    const c = toScreen(new THREE.Vector3(xs[i] - h, h + yT, 0))
    const d = toScreen(new THREE.Vector3(xs[i] - h + 0.2 * L, h + yT, 0))
    const fphi = (Math.atan2(d.y - c.y, d.x - c.x) * 180) / Math.PI
    const cs = Math.cos((fphi * Math.PI) / 180)
    const sn = Math.sin((fphi * Math.PI) / 180)
    pl.fx = Math.round(c.x + 16 * cs - 24 * sn)
    pl.fy = Math.round(c.y + 16 * sn + 24 * cs)
    pl.fphi = Math.round(fphi * 10) / 10
    pl.fa = Math.round(as[i] * Math.max(0, 4 * o - 3) * 100) / 100
  }
  ui.door = phaseId() === 'slab-compare' && P.labels > 0.99 && !anim
  // BC anchors: the faces' centres (a hidden far wall: its top edge)
  if (bcOn.value && ui.bcBtn) {
    const w = (x: number, y: number, z: number) => toScreen(sim.zg.localToWorld(new THREE.Vector3(x, y, z)))
    const { top: bt, bottom: bb } = bands()
    bcAnchors.value = {
      points: {
        surface: [w(-0.18 * L, 0.12 * L, 1)],
        perx: [w(-h, -0.1 * L, 0.5), w(h, 0.1 * L, 1)],
        pery: [w(0.25 * L, -h, 0.5), w(0.25 * L, h, 1)],
        bed: [w(-0.3 * L, -h, 0)],
      },
      leftX: 24,
      rightX: ui.W - 24,
      top: bt + 70,
      bottom: bb - 10,
    }
  }
}

// ── the choreography driver ──
let anim: { segs: Seg[]; dir: 1 | -1; t0: number; total: number; done: () => void } | null = null
let settle: { from: Record<PKey, number>; to: Record<PKey, number>; t0: number; ms: number; done: () => void } | null = null
function stepAnim(now: number): void {
  if (anim) {
    const t = now - anim.t0
    for (const s of anim.segs) {
      const u = Math.min(1, Math.max(0, (t - s.t0) / s.dur))
      const e = s.ease(u)
      P[s.key] = anim.dir === 1 ? e : 1 - e
    }
    if (t >= anim.total) {
      const d = anim.done
      anim = null
      locked.value = false
      d()
    }
  } else if (settle) {
    const u = Math.min(1, (now - settle.t0) / settle.ms)
    const e = cubic(u)
    for (const k of PKEYS) P[k] = lerp(settle.from[k], settle.to[k], e)
    if (u >= 1) {
      const d = settle.done
      settle = null
      locked.value = false
      d()
    }
  }
}
function play(dir: 1 | -1, done: () => void): void {
  settle = null
  const segs = dir === 1 ? FWD : REV
  anim = { segs, dir, t0: performance.now(), total: Math.max(...segs.map((s) => s.t0 + s.dur)), done }
  locked.value = true
}
function settleTo(v: 0 | 1, ms: number, done: () => void = () => {}): void {
  anim = null
  const to = Object.fromEntries(PKEYS.map((k) => [k, v])) as Record<PKey, number>
  settle = { from: { ...P }, to, t0: performance.now(), ms, done }
  locked.value = true
}
function setAll(v: 0 | 1): void {
  anim = null
  settle = null
  locked.value = false
  for (const k of PKEYS) P[k] = v
}

// ── textures for the current choice: load, upload, crossfade ──
// The theory + difference panels: a 450 ms crossfade on a run / field
// change (uA → uB). The simulation block: `shownLevels` = every cum level of
// the shown run + field (all decoded + on the GPU before they are shown),
// painted per frame by `paintSim` — the two levels either side of the
// in-progress depth, or, at rest, `simFade` from the old choice's texture.
interface Fade { mat: THREE.ShaderMaterial; t0: number }
let fades: Fade[] = []
const FADE_MS = 450
function stepFades(now: number): void {
  if (!fades.length) return
  fades = fades.filter((f) => {
    const u = Math.min(1, (now - f.t0) / FADE_MS)
    const U = f.mat.uniforms
    if (u >= 1) {
      U.uA.value = U.uB.value
      U.uMix.value = 0
      return false
    }
    U.uMix.value = u
    return true
  })
}
function swapPanel(mat: THREE.ShaderMaterial, t: THREE.Texture | null, instant: boolean): void {
  if (!t) return
  const U = mat.uniforms
  // a fade in flight lands first
  fades = fades.filter((f) => {
    if (f.mat !== mat) return true
    U.uA.value = U.uB.value
    U.uMix.value = 0
    return false
  })
  if (U.uA.value === t) return
  if (instant || !shown.value) {
    U.uA.value = t
    U.uB.value = t
    U.uMix.value = 0
    return
  }
  U.uB.value = t
  fades.push({ mat, t0: performance.now() })
}

let shownLevels: (THREE.Texture | null)[] = []
let shownFrac: number[] = [0]
let simFade: { from: THREE.Texture; t0: number } | null = null
/** Level k of the shown choice (a failed load → the nearest loaded one). */
function level(k: number): THREE.Texture {
  const n = shownLevels.length
  for (let j = 0; j < n; j++) {
    const a = shownLevels[k - j]
    if (a) return a
    const b = shownLevels[k + j]
    if (b) return b
  }
  return blankTex
}
/** The two cum levels around depth fraction d, and the mix between them. */
function levelsAt(d: number): [THREE.Texture, THREE.Texture, number] {
  const fr = shownFrac
  if (fr.length < 2) return [level(0), level(0), 0]
  let k = 0
  while (k < fr.length - 2 && d > fr[k + 1]) k++
  const u = Math.min(1, Math.max(0, (d - fr[k]) / Math.max(1e-6, fr[k + 1] - fr[k])))
  return [level(k), level(k + 1), u]
}
/** The texture the block shows at rest (the surface, or the full average). */
function restTex(): THREE.Texture {
  const [a, b, u] = levelsAt(P.depth)
  return u < 0.5 ? a : b
}
function paintSim(now: number): void {
  const U = sim.paintMat.uniforms
  const [a, b, u] = levelsAt(P.depth)
  if (simFade) {
    const f = (now - simFade.t0) / FADE_MS
    if (f < 1) {
      U.uA.value = simFade.from
      U.uB.value = u < 0.5 ? a : b
      U.uMix.value = f
      return
    }
    simFade = null
  }
  U.uA.value = a
  U.uB.value = b
  U.uMix.value = u
}

let selSeq = 0
/** Put the current run + field on every panel (crossfading on screen) once
 *  ALL its cum levels are decoded and on the GPU. */
async function applySelection(instant: boolean): Promise<void> {
  const r = cur.value
  if (!r) return
  const seq = ++selSeq
  const f = slabState.field
  const paths = [...r.cum[f], r.theory[f], r.diff[f]]
  const tex = await Promise.all(paths.map(loadTex))
  if (seq !== selSeq) return
  await uploadAll(tex)
  if (seq !== selSeq) return
  const lv = tex.slice(0, r.cum[f].length)
  const [t, df] = tex.slice(r.cum[f].length)
  const atRest = P.depth === 0 || P.depth === 1
  simFade = !instant && shown.value && atRest && shownLevels.length ? { from: restTex(), t0: performance.now() } : null
  shownLevels = lv
  shownFrac = r.depth_frac?.length === lv.length ? r.depth_frac : lv.map((_, k) => k / Math.max(1, lv.length - 1))
  swapPanel(theoryP.paintMat, t, instant)
  swapPanel(diffP.paintMat, df, instant)
  setTargets(instant)
  warmAround()
}
/** The current run's three fields — every cum level + theory + diff,
 *  decoded and on the GPU (a field toggle, then DEPTH AVERAGE, never waits)
 *  — and the current field of every run one slider stop away into the HTTP
 *  cache. */
function warmAround(): void {
  const m = man.value
  const r = cur.value
  if (!m || !r) return
  protectUrls.clear()
  for (const f of SLAB_TALK_FIELDS) {
    if (!r.cum[f]) continue
    for (const p of [...r.cum[f], r.theory[f], r.diff[f]]) {
      protectUrls.add(slabRasterUrl(p, true, CH2_SLAB_V2_PREFIX))
      void loadTex(p).then((t) => (shown.value ? queueUpload(t) : upload(t)))
    }
  }
  const f = slabState.field
  for (const id of slabNeighbours(m, slabState.run)) {
    const n = m.runs[id]
    for (const p of [...n.cum[f], n.theory[f], n.diff[f]]) warmHttp(p)
  }
}
/** A run the talk does not have (picked in the deeper dive's v1 viewer, e.g.
 *  R 1 km or α 0.1°) → the nearest v2 run. */
function snapRun(): void {
  const m = man.value
  if (!m || m.runs[slabState.run]) return
  const want = parseSlabRunId(slabState.run)
  slabState.run = (want && findSlabRun(m, want)) || (m.runs[SLAB_TALK_HERO] ? SLAB_TALK_HERO : m.runs[m.hero] ? m.hero : Object.keys(m.runs)[0])
}
watch(() => slabState.run, snapRun)
watch(() => [slabState.run, slabState.field], () => {
  if (cur.value) void applySelection(false)
})
watch(cur, () => setTargets(false))
watch(bcOn, () => reframe(false))

// ── beats ──
function phaseId(b: number = props.beat): string {
  return CH2_BEAT_IDS[b]?.replace(/\/2$/, '') ?? ''
}
const timers: number[] = []
function later(ms: number, fn: () => void): void {
  timers.push(window.setTimeout(fn, ms))
}
function clearTimers(): void {
  for (const t of timers) window.clearTimeout(t)
  timers.length = 0
}
function show(v: boolean): void {
  shown.value = v
  emit('covering', v)
  if (v) {
    lastT = performance.now()
    reframe(true)
  } else {
    bcOn.value = false
  }
}
/** Lift the veil once the current choice's textures are on the GPU (a
 *  deadline: never stuck on a slow or failed load). */
let readyP: Promise<void> = Promise.resolve()
function liftWhenReady(maxMs: number, then: () => void = () => {}): void {
  const t0 = performance.now()
  let ready = false
  void readyP.then(() => (ready = true))
  const go = () => {
    if (!alive) return
    if (!ready && performance.now() - t0 < maxMs) {
      requestAnimationFrame(go)
      return
    }
    let n = 2
    const s = () => {
      if (--n > 0) requestAnimationFrame(s)
      else {
        veil.value = 'off'
        then()
      }
    }
    requestAnimationFrame(s)
  }
  requestAnimationFrame(go)
}
/** The cut through black (THE HOP's 220 ms dip): under it, `under()`. */
function cut(under: () => void, lift = true, maxMs = 2500, then?: () => void): void {
  clearTimers()
  veil.value = 'in'
  later(220, () => {
    veil.value = 'on'
    under()
    if (lift) liftWhenReady(maxMs, then)
  })
}
let seenBeat = false
function onBeat(b: number, old: number | undefined): void {
  const ph = phaseId(b)
  const pph = old === undefined ? '' : phaseId(old)
  const inSlab = ch2IsSlabPhase(ch2Phase(b))
  if (!man.value || !sim) return // the mount applies the beat once the manifest is in
  const first = !seenBeat
  seenBeat = true
  if (!inSlab) {
    if (!shown.value) return
    anim = null
    settle = null
    locked.value = false
    if (ch2IsFlatPage(b)) {
      // a flat page dissolves in above (Ch2Results, 0.7 s, z 9): NEXT from
      // the three panels → the implications, BACK from the block → the
      // population; the layer goes once it is covered
      clearTimers()
      later(760, () => show(false))
    } else {
      // a landmark jump back to the block beats: through black, the globe
      // already running
      emit('covering', false)
      cut(() => { shown.value = false; bcOn.value = false })
    }
    return
  }
  if (!shown.value) {
    if (pph === 'implications' && ph === 'slab-compare') {
      // BACK from the implications: the settled panels under the page as
      // it dissolves away (Ch2Results, 0.7 s) — the deep-link settle
      clearTimers()
      veil.value = 'off'
      setAll(1)
      show(true)
      return
    }
    if (pph === 'population' && ph === 'slab') {
      // NEXT from the population page: a dip through black — the page
      // fades out (Ch2Results, 0.7 s) onto the veil, then the veil lifts
      // (280 ms) off the landed block, its run's textures on the GPU since
      // the bed beat (a deadline all the same)
      clearTimers()
      veil.value = 'on'
      setAll(0)
      show(true)
      readyP = applySelection(true)
      later(700, () => liftWhenReady(2500))
      return
    }
    // a cut from a deep link / a landmark jump
    const under = () => {
      setAll(ph === 'slab-compare' ? 1 : 0)
      show(true)
      readyP = applySelection(true)
    }
    if (first) {
      veil.value = 'on'
      under()
      liftWhenReady(4000, () => { if (ph === 'slab-da') startForward() })
    } else {
      cut(under, true, 2500, () => { if (phaseId() === 'slab-da') startForward() })
    }
    return
  }
  // on screen already: the live moves
  clearTimers()
  if (veil.value !== 'off') veil.value = 'off'
  if (pph === 'slab' && ph === 'slab-da') startForward()
  else if (pph === 'slab-da' && ph === 'slab-compare') {
    if (anim || settle) settleTo(1, 700)
  } else if (ph === 'slab' && (pph === 'slab-compare' || pph === 'slab-da')) {
    if (pph === 'slab-compare' && !anim && !settle) play(-1, () => {})
    else settleTo(0, 1200)
  } else if (ph === 'slab-compare') settleTo(1, 900)
  else if (ph === 'slab') settleTo(0, 900)
  else if (ph === 'slab-da') startForward()
}
function startForward(): void {
  if (P.depth > 0) setAll(0)
  bcOn.value = false
  play(1, () => {
    if (phaseId() === 'slab-da') emit('transit-done')
  })
}
watch(() => props.beat, (b, old) => onBeat(b, old))

// ── life ──
function onResize(): void {
  if (!renderer) return
  renderer.setSize(window.innerWidth, window.innerHeight, false)
  reframe(false)
  Object.assign(side, sideGoal)
}
onMounted(async () => {
  const canvas = canvasEl.value
  if (!canvas) return
  // a deep link / jump straight onto a slab beat: black at once, not the
  // globe's teaser while the manifest + textures come in
  if (ch2IsSlabPhase(ch2Phase(props.beat))) veil.value = 'on'
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false })
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1))
  renderer.setSize(window.innerWidth, window.innerHeight, false)
  renderer.setClearColor(0x000000, 1)
  scene = new THREE.Scene()
  camera = new THREE.PerspectiveCamera(FOV, window.innerWidth / window.innerHeight, 1, 20000)
  const m = await loadSlabTalkManifest()
  if (!alive) return
  if (!m) {
    console.warn('[slab] no manifest — the slab beats stay dark')
    return
  }
  if (!m.fields.includes(slabState.field)) slabState.field = m.fields[0]
  man.value = m
  snapRun()
  const L = viewKm.value
  sim = makeSlab(L)
  theoryP = makeSlab(L)
  diffP = makeSlab(L)
  scene.add(sim.group, theoryP.group, diffP.group)
  setTargets(true)
  reframe(true)
  window.addEventListener('resize', onResize)
  raf = requestAnimationFrame(frame)
  // the current run on the GPU, every shader compiled, before the beat
  await applySelection(true)
  if (!alive || !renderer) return
  setAll(0)
  drawState()
  setSlabOpacity(theoryP, 1)
  setSlabOpacity(diffP, 1)
  renderer.compile(scene, camera)
  renderer.render(scene, camera)
  setSlabOpacity(theoryP, 0)
  setSlabOpacity(diffP, 0)
  ;(window as any).__slabReady = true
  onBeat(props.beat, undefined)
})
// debug / verification hooks
;(window as any).__slabState = () => ({ P: { ...P }, shown: shown.value, anim: !!anim, settle: !!settle, run: slabState.run, field: slabState.field, veil: veil.value, texPending })
onBeforeUnmount(() => {
  alive = false
  clearTimers()
  cancelAnimationFrame(raf)
  window.removeEventListener('resize', onResize)
  emit('covering', false)
  ;(window as any).__slabReady = false
  for (const t of texCache.values()) t.dispose()
  texCache.clear()
  scene?.traverse((o) => {
    const mesh = o as THREE.Mesh
    mesh.geometry?.dispose()
    const mat = mesh.material as THREE.Material | THREE.Material[] | undefined
    if (Array.isArray(mat)) mat.forEach((x) => x.dispose())
    else mat?.dispose()
  })
  renderer?.dispose()
  renderer?.forceContextLoss()
  renderer = null
})
</script>

<style scoped>
.cs-root {
  position: absolute;
  inset: 0;
  z-index: 8;
  pointer-events: none;
}
.cs-stage {
  position: fixed;
  inset: 0;
  background: #000;
  pointer-events: auto;
}
.cs-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}
.cs-veil {
  position: fixed;
  inset: 0;
  background: #000;
  opacity: 0;
  pointer-events: none;
  transition: opacity 280ms ease-out;
}
.cs-veil-in {
  opacity: 1;
  transition: opacity 220ms ease-in;
}
.cs-veil-on {
  opacity: 1;
  transition: none;
}

.cs-locked {
  pointer-events: none;
  opacity: 0.55;
  transition: opacity 0.4s;
}

/* the field toggle — Chapter 2's tier pills */
.cs-fields {
  position: absolute;
  left: 2vw;
  display: flex;
  gap: 0.6rem;
  z-index: 2;
  transition: opacity 0.4s;
}
.cs-pill {
  min-width: 5.6rem;
  border: 1.5px solid var(--gold);
  background: rgba(8, 6, 4, 0.78);
  color: var(--gold-bright);
  font-family: 'EB Garamond', Georgia, serif;
  font-size: 1.9rem;
  line-height: 1;
  padding: 0.3rem 1.1rem 0.5rem;
  border-radius: 999px;
  cursor: pointer;
  white-space: nowrap;
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.55), 0 0 22px rgba(245, 199, 94, 0.18);
  transition: color 0.2s, background 0.2s, box-shadow 0.2s, opacity 0.2s;
}
.cs-pill :deep(sub) {
  font-size: 0.68em;
  line-height: 0;
  font-style: normal;
}
.cs-pill:not(.cs-pill-on) {
  opacity: 0.72;
}
.cs-pill:not(.cs-pill-on):hover {
  opacity: 1;
  color: #fff8d8;
  background: rgba(56, 38, 12, 0.85);
}
.cs-pill-on,
.cs-pill-on:hover {
  color: #1c1305;
  background: var(--gold);
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.55), 0 0 30px rgba(245, 199, 94, 0.45);
}

/* the colour bar, top-right */
.cs-cbar {
  position: absolute;
  right: 2vw;
  width: min(300px, 24vw);
  z-index: 2;
  pointer-events: none;
}
.cs-cbar-title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.3rem;
}
.cs-cbar-unit {
  font-family: 'EB Garamond', serif;
  font-size: 1.3rem;
  color: #f5f0e6;
}
.cs-cbar-bar {
  height: 16px;
  border: 1px solid rgba(255, 255, 255, 0.55);
  border-radius: 3px;
  /* matplotlib seismic — the rasters' map (blue −, white 0, red +) */
  background: linear-gradient(to right, #00004c, #0000ff 25%, #ffffff 50%, #ff0000 75%, #800000);
}
.cs-cbar-ticks {
  display: flex;
  justify-content: space-between;
  margin-top: 0.25rem;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1.05rem;
  color: #f0f0f0;
  font-variant-numeric: tabular-nums;
}

/* DEPTH AVERAGE — SlabActionButton's look */
.cs-da-btn {
  position: absolute;
  transform: translate(-50%, -100%);
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  border: 1.5px solid var(--gold);
  background: rgba(8, 6, 4, 0.82);
  color: var(--gold-bright);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 0.55rem 1rem 0.55rem 1.1rem;
  border-radius: 999px;
  cursor: pointer;
  z-index: 2;
  white-space: nowrap;
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.55), 0 0 22px rgba(245, 199, 94, 0.18);
  animation: cs-pulse 2.4s ease-in-out infinite;
}
.cs-da-btn:hover {
  color: #fff8d8;
  background: rgba(56, 38, 12, 0.85);
}
.cs-da-arrow { color: var(--gold); }
@keyframes cs-pulse {
  0%, 100% { box-shadow: 0 6px 28px rgba(0,0,0,0.55), 0 0 22px rgba(245,199,94,0.18); }
  50% { box-shadow: 0 6px 28px rgba(0,0,0,0.55), 0 0 36px rgba(245,199,94,0.40); }
}

/* the vertical-exaggeration label: bottom-right under the triad, the
   colourbar's small-caps voice; back-row sizes */
.cs-vexag {
  position: absolute;
  right: 2vw;
  bottom: calc(9.5vh + 2.6rem);
  display: flex;
  align-items: baseline;
  gap: 0.55rem;
  padding: 0.35rem 0.7rem;
  background: rgba(8, 6, 4, 0.72);
  border: 1px solid rgba(244, 207, 106, 0.35);
  border-radius: 8px;
  pointer-events: none;
  transition: opacity 300ms ease;
}
.cs-vexag-k {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(244, 207, 106, 0.85);
}
.cs-vexag-v {
  font-family: 'EB Garamond', serif;
  font-size: 1.25rem;
  color: #f5f5f5;
}

/* ICE FLOW (Ch2FlowArrow's band) */
.cs-flow {
  position: absolute;
  left: 0;
  top: 0;
  pointer-events: none;
  overflow: visible;
}
.cs-flow-ink { stroke: #050505; stroke-width: 10; stroke-linecap: round; stroke-linejoin: round; fill: #050505; }
.cs-flow-gold { stroke: var(--gold, #f4cf6a); stroke-width: 5; stroke-linecap: round; stroke-linejoin: round; fill: var(--gold, #f4cf6a); }
.cs-flow-lbl {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.14em;
  fill: var(--gold, #f4cf6a);
  paint-order: stroke;
  stroke: #050505;
  stroke-width: 5px;
  stroke-linejoin: round;
}

/* the panels' titles */
/* the panels' titles — one flex row, so the Theory credit sits IN the
   title's box and the whole "Theory · Coffey · Hilditch" row is centred on
   its panel (the director wanted the two credits next to each
   other, even if that means moving 'Theory' over to the left a bit);
   1.55 → 1.85rem so the titles read a bit larger */
.cs-ptitle {
  position: absolute;
  transform: translate(-50%, -100%);
  display: inline-flex;
  align-items: center;
  gap: 0.8rem;
  white-space: nowrap;
  pointer-events: none;
  font-family: 'EB Garamond', serif;
  font-size: 1.85rem;
  line-height: 1.1;
  color: var(--gold-bright);
}
/* "Coffey 2026" + Niall's headshot and "Jamie Hilditch" + his tile,
   side by side after the Theory title */
.cs-credit {
  display: inline-flex;
  align-items: center;
  gap: 0.9rem;
}
.cs-credit-row {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  white-space: nowrap;
}
.cs-credit-face {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  object-fit: cover;
  border: 1.5px solid var(--gold);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.6);
}
/* no photo: the Acknowledgements' initials tile (EB Garamond, gold) */
.cs-credit-initials {
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(10, 9, 8, 0.92);
  font-family: 'EB Garamond', Georgia, serif;
  font-size: 1rem;
  letter-spacing: 0.04em;
  color: var(--gold);
}
.cs-credit-txt {
  font-family: 'EB Garamond', Georgia, serif;
  font-size: 1.2rem;
  color: #f3ead2;
}

/* the sliders: a 2 × 2 card, bottom centre (the twins' sliders) */
.cs-sliders {
  position: absolute;
  left: 50%;
  bottom: 18px;
  transform: translateX(-50%);
  display: grid;
  grid-template-columns: auto auto;
  column-gap: 2.2rem;
  row-gap: 0.55rem;
  padding: 0.6rem 1.3rem 0.65rem;
  background: rgba(8, 6, 4, 0.78);
  border: 1px solid var(--gold-dim);
  border-radius: 12px;
  z-index: 2;
  transition: opacity 0.4s;
}
.cs-sl {
  display: grid;
  grid-template-columns: 1.6rem 132px 4.6rem;
  align-items: center;
  gap: 0.7rem;
}
.cs-sym {
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  font-size: 1.55rem;
  line-height: 1;
  color: var(--gold-bright);
  text-align: right;
}
.cs-val {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1.15rem;
  line-height: 1;
  color: rgba(245, 245, 245, 0.92);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.cs-sl input[type='range'] {
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
.cs-sl input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #f5c75e;
  border: 1px solid rgba(0, 0, 0, 0.55);
  cursor: grab;
}
.cs-sl input[type='range']::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #f5c75e;
  border: 1px solid rgba(0, 0, 0, 0.55);
  cursor: grab;
}
.cs-sl input[type='range'].cs-binary {
  width: 60px;
  background:
    radial-gradient(circle at 10px 50%, rgba(245, 199, 94, 0.75) 3px, transparent 3.5px),
    radial-gradient(circle at calc(100% - 10px) 50%, rgba(245, 199, 94, 0.75) 3px, transparent 3.5px),
    rgba(245, 199, 94, 0.42);
}

/* BOUNDARY CONDITIONS — SimBcButton's pill */
.cs-bc-btn {
  position: absolute;
  left: 22px;
  bottom: 22px;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  border: 1.5px solid var(--gold);
  background: rgba(8, 6, 4, 0.78);
  color: var(--gold-bright);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.98rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 0.55rem 1.05rem;
  border-radius: 999px;
  cursor: pointer;
  z-index: 2;
  white-space: nowrap;
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.55), 0 0 22px rgba(245, 199, 94, 0.16);
}
.cs-bc-btn:hover { color: #fff8d8; background: rgba(56, 38, 12, 0.85); }
.cs-bc-icon { font-size: 1.1rem; }
.cs-bc-on,
.cs-bc-on:hover {
  color: #1c1305;
  background: var(--gold);
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.55), 0 0 30px rgba(245, 199, 94, 0.45);
}

.cs-door {
  position: absolute;
  right: 22px;
  bottom: 22px;
  z-index: 2;
}
.cs-fade-enter-active,
.cs-fade-leave-active { transition: opacity 0.5s; }
.cs-fade-enter-from,
.cs-fade-leave-to { opacity: 0; }
</style>
