<template>
  <!-- APS DFD 2026 · THE PROBLEM: lake 2394 in time, the elmerfiles
       README's graphical summary rebuilt live from the Chapter 2 data
       (config/dfdProblem.ts). LEFT the centre-lakes map, the lake on the
       tile in gold, with a where-in-Greenland silhouette under it. RIGHT
       the lake's 15 km tile, drawn in the model's own frame — ice flows
       LEFT → RIGHT, the page's convention (the implications figure, the
       lab) — through the five stations: the two Sentinel-2 scenes, then
       the viscous σt1 before and after drainage and their difference, the
       block's drapes on the block's ±1 MPa seismic bar; the catalogue's
       lake outlines and numbers over it. BESIDE it the talk's stress space
       (Ch2StressSpace): blank until the pre-drainage field, x lit on post,
       y lit on the difference. The station bar along the bottom emits the
       step; NEXT / BACK drive it from the page. Figure labels only. -->
  <div ref="root" class="pb" :style="vars">
    <!-- ── the map ── -->
    <div class="pb-map">
      <svg v-if="inset" :viewBox="`0 0 ${mapW} ${mapH}`" :width="mapW" :height="mapH" class="pb-map-svg">
        <rect x="0" y="0" :width="mapW" :height="mapH" class="pbm-ice" />
        <path v-for="(d, i) in seaPaths" :key="`s${i}`" :d="d" class="pbm-sea" fill-rule="evenodd" />
        <path v-for="(d, i) in landPaths" :key="`l${i}`" :d="d" class="pbm-land" fill-rule="evenodd" />
        <polyline v-for="(p, i) in marginLines" :key="`m${i}`" :points="p" class="pbm-margin" />
        <!-- the other centre lakes: their tiles, glyphs and numbers, dim -->
        <g v-for="lk in mapLakes.filter((l) => !l.cur)" :key="lk.num" class="pbm-other" :class="{ 'pbm-hit': canPick }" @click="onMapPick">
          <polygon v-if="lk.tile" :points="lk.tile" class="pbm-tile" />
          <path :d="phaseMarkerPath(lk.shape, lk.px, lk.py, 5)" class="pbm-dim" />
          <text :x="lk.px + lk.lbl.dx" :y="lk.py + lk.lbl.dy" :text-anchor="lk.lbl.anchor" class="pbm-num pbm-num-dim">{{ lk.num }}</text>
          <circle :cx="lk.px" :cy="lk.py" r="16" class="pbm-disc" />
        </g>
        <!-- the lake on the tile: gold, its flow arrow on the tile's top edge -->
        <g v-if="mapCur">
          <polygon v-if="mapCur.tile" :points="mapCur.tile" class="pbm-tile-cur" />
          <line v-if="mapCur.flow" :x1="mapCur.flow.x1" :y1="mapCur.flow.y1" :x2="mapCur.flow.x2" :y2="mapCur.flow.y2" class="pbm-flow" marker-end="url(#pbm-head)" />
          <path :d="phaseMarkerPath(mapCur.shape, mapCur.px, mapCur.py, 8)" class="pbm-cur" />
          <text :x="mapCur.px + mapCur.lbl.dx" :y="mapCur.py + mapCur.lbl.dy" :text-anchor="mapCur.lbl.anchor" class="pbm-num">{{ mapCur.num }}</text>
        </g>
        <defs>
          <marker id="pbm-head" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
            <path d="M 0 0 L 10 5 L 0 10 Z" fill="#f4cf6a" />
          </marker>
        </defs>
        <!-- 50 km, top-right (open ice) -->
        <g class="pbm-bar">
          <line :x1="mapW - 12 - bar50" :x2="mapW - 12" y1="30" y2="30" />
          <line :x1="mapW - 12 - bar50" :x2="mapW - 12 - bar50" y1="24" y2="36" />
          <line :x1="mapW - 12" :x2="mapW - 12" y1="24" y2="36" />
          <text :x="mapW - 12 - bar50 / 2" y="19" text-anchor="middle" class="pbm-bartxt">50 km</text>
        </g>
        <rect x="0.75" y="0.75" :width="mapW - 1.5" :height="mapH - 1.5" class="pbm-frame" />
      </svg>
      <!-- where in Greenland: the silhouette, the map's window on it -->
      <div class="pb-sil" :style="{ width: silW + 'px', height: silH + 'px' }">
        <div class="pb-sil-mask" :style="{ '--sil': `url(${silhouetteUrl})` }" />
        <div class="pb-sil-box" :style="silBox" />
      </div>
    </div>

    <!-- ── the title over the tile ── -->
    <div class="pb-title">
      <span class="pb-ttl-wrap">
        <!-- trusted static HTML (the subscripts) --><span class="pb-ttl" v-html="station.title" />
        <span v-if="dateShown" class="pb-date">{{ dateShown }}</span>
      </span>
      <!-- the tile's frame: ice flows left → right along it -->
      <span class="pb-flow" aria-hidden="true">
        <svg :width="arrowL + 16" height="16" :viewBox="`0 0 ${arrowL + 16} 16`">
          <line x1="1" y1="8" :x2="arrowL" y2="8" class="pb-gold" />
          <path :d="`M ${arrowL + 14} 8 l -12 -7 v 14 Z`" class="pb-gold pb-gold-fill" />
        </svg>
        <span>ICE FLOW</span>
      </span>
    </div>

    <!-- ── the tile ── -->
    <div class="pb-tile">
      <svg :viewBox="`0 0 ${T} ${T}`" :width="T" :height="T" class="pb-tile-svg">
        <defs>
          <clipPath :id="clipId"><rect x="0" y="0" :width="T" :height="T" /></clipPath>
        </defs>
        <g :clip-path="`url(#${clipId})`">
          <rect x="0" y="0" :width="T" :height="T" class="pb-under" />
          <!-- the five drapes, stacked: the station's opaque, a crossfade
               between them (each is in the DOM from the start — that is
               the preload) -->
          <image
            v-for="(r, i) in rasters"
            :key="r.key"
            :href="r.url"
            x="0"
            y="0"
            width="1"
            height="1"
            preserveAspectRatio="none"
            :transform="xform"
            class="pb-raster"
            :style="{ opacity: i === step ? 1 : 0 }"
          />
        </g>
        <!-- the catalogue's outlines: a dark halo under each colour -->
        <g class="pb-rings">
          <template v-for="lk in tileLakes" :key="lk.num">
            <path :d="lk.d" class="pb-ring-halo" :class="{ 'pb-ring-c': lk.center }" />
            <path :d="lk.d" class="pb-ring" :class="{ 'pb-ring-c': lk.center }" :stroke="lk.color" :stroke-dasharray="lk.dash" />
          </template>
          <text
            v-for="lk in tileLakes"
            :key="`n${lk.num}`"
            :x="lk.lx"
            :y="lk.ly"
            :text-anchor="lk.anchor"
            class="pb-num"
            :class="{ 'pb-num-c': lk.center }"
            :font-size="lk.center ? lblPx * 1.25 : lblPx"
          >{{ lk.num }}</text>
        </g>
        <!-- furniture (the corners the catalogue leaves free): north
             top-right, 5 km bottom-right; the flow arrow is the title row's -->
        <g class="pb-furn" :transform="`translate(${T - furn - 14} ${furn + 8}) rotate(${northDeg})`">
          <line x1="0" y1="0" :x2="northL" y2="0" class="pb-ink" />
          <path :d="`M ${northL} 0 l -11 -6 v 12 Z`" class="pb-ink pb-ink-fill" />
          <line x1="0" y1="0" :x2="northL - 2" y2="0" class="pb-gold" />
          <path :d="`M ${northL} 0 l -11 -6 v 12 Z`" class="pb-gold pb-gold-fill" />
          <text :x="northL + 11" y="0" :transform="`rotate(${-northDeg} ${northL + 11} 0)`" dominant-baseline="central" text-anchor="middle" class="pb-flbl">N</text>
        </g>
        <g class="pb-furn" :transform="`translate(${T - furn} ${T - furn})`">
          <line :x1="-scaleL" y1="0" x2="0" y2="0" class="pb-ink" />
          <line :x1="-scaleL" y1="-7" :x2="-scaleL" y2="7" class="pb-ink" />
          <line x1="0" y1="-7" x2="0" y2="7" class="pb-ink" />
          <line :x1="-scaleL" y1="0" x2="0" y2="0" class="pb-gold" />
          <line :x1="-scaleL" y1="-7" :x2="-scaleL" y2="7" class="pb-gold" />
          <line x1="0" y1="-7" x2="0" y2="7" class="pb-gold" />
          <text :x="-scaleL / 2" y="-12" text-anchor="middle" class="pb-flbl">{{ SCALE_KM }} KM</text>
        </g>
        <rect x="0.75" y="0.75" :width="T - 1.5" :height="T - 1.5" class="pb-frame" />
      </svg>
    </div>

    <!-- ── under the tile: the block's colour bar (the stress stations) ── -->
    <div class="pb-cbar" :class="{ 'pb-cbar-on': station.cbar }">
      <img v-if="cbarSym" :src="ch2EqUrl(cbarSym)" :style="cbarBox" class="pb-cbar-sym" :alt="cbarSym" />
      <div class="pb-cbar-scale">
        <div class="pb-cbar-bar" />
        <div class="pb-cbar-ticks">
          <span v-for="t in CBAR_TICKS" :key="t.p" :style="{ left: t.p + '%' }"><i />{{ t.l }}</span>
        </div>
      </div>
    </div>

    <!-- ── the stress space ── -->
    <div class="pb-space" :class="{ 'pb-space-dim': !station.step }">
      <Ch2StressSpace
        v-if="phase && centerNum"
        model="viscous"
        comp="t1"
        :field="spaceStep.field"
        :emphasis="spaceStep.emphasis"
        :points="phase.models.viscous?.points ?? []"
        :center-num="centerNum"
        :fs="1.3"
        :header-model="false"
        labels
      />
    </div>

    <!-- ── the stations ── -->
    <nav class="pb-bar" aria-label="Stations">
      <span class="pb-bar-line" aria-hidden="true" />
      <button
        v-for="(s, i) in DFD_PROBLEM_STATIONS"
        :key="s.id"
        class="pb-st"
        :class="{ 'pb-st-on': i === step, 'pb-st-done': i < step }"
        :aria-pressed="i === step"
        @click="emit('step', i)"
      >
        <span class="pb-dot" />
        <span class="pb-st-stage">{{ s.stage }}</span>
        <span class="pb-st-layer">
          <template v-if="s.layer === 'imagery'">imagery</template>
          <span v-else class="pb-sym">{{ s.layer === 'diff' ? 'Δσ' : 'σ' }}<sub>t1</sub></span>
        </span>
        <span class="pb-st-date">{{ s.date ? dfdProblemDate(s.date === 'pre' ? lake?.date_pre : lake?.date_post) : '' }}</span>
      </button>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import Ch2StressSpace from './Ch2StressSpace.vue'
import { mediaUrl } from '../config/media'
import { CH2_EQ } from '../config/ch2Eqs'
import { ch2EqUrl, loadCh2Phase } from '../config/ch2Results'
import type { Ch2Step } from '../config/ch2Beats'
import { PHASE_CENTER_MARKERS, phaseMarkerPath, SIM_LAKE_STYLE, type PhaseSpaceFile, type SimLakesFile } from '../config/simLakes'
import {
  DFD_PROBLEM_GREENLAND_NS_KM,
  DFD_PROBLEM_LAKE,
  DFD_PROBLEM_MAP_LABELS,
  DFD_PROBLEM_SILHOUETTE_AOI,
  DFD_PROBLEM_STATIONS,
  dfdProblemDate,
  type DfdProblemRaster,
} from '../config/dfdProblem'

const props = defineProps<{
  /** The station on screen, 0–4 (NEXT / BACK step it; a click emits one). */
  step: number
}>()
const emit = defineEmits<{ step: [n: number] }>()

const step = computed(() => Math.min(DFD_PROBLEM_STATIONS.length - 1, Math.max(0, props.step)))
const station = computed(() => DFD_PROBLEM_STATIONS[step.value])
/** The stress space's step: the station's, or the blank PRE frame on the imagery. */
const BLANK: Ch2Step = { model: 'viscous', comp: 't1', field: 'pre', emphasis: null }
const spaceStep = computed(() => station.value.step ?? BLANK)

// ── the data (one fetch each per page life) ──
interface SimDomainMeta {
  id: string
  lon: number
  lat: number
  domain_half_km: number
  bbox: { lon_w: number; lon_e: number; lat_s: number; lat_n: number }
  corners_lonlat: [number, number][]
  date_pre: string
  date_post: string
  s2_pre: string
  s2_post: string
  stress_viscous: string
  lakes: string
  stress_v_nopatch?: string
  stress_v_patch?: string
}
interface InsetFile {
  frame: { half_x: number; half_y: number; q: number }
  lakes: { id: string; num: number; x: number; y: number }[]
  margin: number[][]
  land: number[][][]
  sea: number[][][]
}
function getJson<T>(key: string): Promise<T | null> {
  return fetch(mediaUrl(key))
    .then((r) => (r.ok ? (r.json() as Promise<T>) : null))
    .catch(() => null)
}
let metaP: Promise<Record<string, SimDomainMeta> | null> | null = null
let insetP: Promise<InsetFile | null> | null = null
const ringsP = new Map<string, Promise<SimLakesFile | null>>()

const meta = shallowRef<Record<string, SimDomainMeta> | null>(null)
const inset = shallowRef<InsetFile | null>(null)
const rings = shallowRef<SimLakesFile | null>(null)
const phase = shallowRef<PhaseSpaceFile | null>(null)
const lakeId = ref(DFD_PROBLEM_LAKE)
const lake = computed(() => meta.value?.[lakeId.value] ?? null)
const centerNum = computed(() => rings.value?.lakes.find((l) => l.center)?.num ?? 0)

function loadRings(id: string): void {
  let p = ringsP.get(id)
  if (!p) {
    p = getJson<SimLakesFile>(`ch02/sim/simlakes_${id}.json`)
    ringsP.set(id, p)
  }
  p.then((j) => {
    if (id !== lakeId.value) return
    if (j) rings.value = j
    else console.warn('[dfd problem] lake outlines failed to load', id)
  })
}
/** Another centre lake clicked on the map: the whole panel becomes its. */
const canPick = computed(() => !!meta.value)
function pick(id: string): void {
  if (!meta.value?.[id] || id === lakeId.value) return
  lakeId.value = id
  rings.value = null
  loadRings(id)
}
/** The hit discs overlap (1951 · 2520 sit 5 km apart, 2411 · 2416 · 2511
 *  within 12): the lake NEAREST the pointer wins, the inset's rule. */
const HIT_R = 16
function onMapPick(e: MouseEvent): void {
  const svg = (e.currentTarget as SVGElement | null)?.ownerSVGElement
  const r = svg?.getBoundingClientRect()
  if (!r) return
  const x = e.clientX - r.left
  const y = e.clientY - r.top
  let best: { id: string; cur: boolean } | null = null
  let bd = Infinity
  for (const l of mapLakes.value) {
    const d = Math.hypot(l.px - x, l.py - y)
    if (d < bd) {
      bd = d
      best = l
    }
  }
  if (best && bd <= HIT_R + 1 && !best.cur) pick(best.id)
}

// ── the band's size → the layout (px, one ResizeObserver) ──
const root = ref<HTMLElement | null>(null)
const W = ref(1200)
const H = ref(700)
let ro: ResizeObserver | null = null
const GAP = 24 // column gap
const RGAP = 10 // row gap
const RT = 46 // the title row
const RB = 46 // the colour-bar row
const BAR = 80 // the station bar
/** The map's width: a fifth of the band, within bounds. */
const mapW = computed(() => Math.round(Math.min(360, Math.max(220, 0.2 * W.value))))
/** The tile's side: the square that fits beside the map and the space. */
const T = computed(() =>
  Math.max(200, Math.floor(Math.min(H.value - RT - RB - BAR - 3 * RGAP, (W.value - mapW.value - 2 * GAP) / 2))),
)
const vars = computed(() => ({
  '--map': mapW.value + 'px',
  '--T': T.value + 'px',
  '--gap': GAP + 'px',
  '--rgap': RGAP + 'px',
  '--rt': RT + 'px',
  '--rb': RB + 'px',
  '--bar': BAR + 'px',
}))

// ── the map (the inset's recipe, larger) ──
const mapH = computed(() => (inset.value ? Math.round((mapW.value * inset.value.frame.half_y) / inset.value.frame.half_x) : Math.round(mapW.value * 1.333)))
const kpx = computed(() => (inset.value ? mapW.value / (2 * inset.value.frame.half_x) : 1)) // px per km
function mx(xKm: number): number {
  return (xKm + inset.value!.frame.half_x) * kpx.value
}
function my(yKm: number): number {
  return (inset.value!.frame.half_y - yKm) * kpx.value
}
function flatPts(a: number[]): [number, number][] {
  const q = inset.value!.frame.q
  const out: [number, number][] = []
  for (let i = 0; i + 1 < a.length; i += 2) out.push([mx(a[i] / q), my(a[i + 1] / q)])
  return out
}
function ringD(r: number[][]): string {
  return r.map((s) => 'M ' + flatPts(s).map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join(' L ') + ' Z').join(' ')
}
const seaPaths = computed(() => (inset.value ? inset.value.sea.map(ringD) : []))
const landPaths = computed(() => (inset.value ? inset.value.land.map(ringD) : []))
const marginLines = computed(() =>
  inset.value ? inset.value.margin.map((m) => flatPts(m).map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')) : [],
)
const bar50 = computed(() => 50 * kpx.value)
const KM_PER_DEG = 111.32
/** A centre lake's 15 km tile on the map: the manifest's corners, laid
 *  round the inset's lake position (local km about the lake). */
const mapLakes = computed(() => {
  if (!inset.value) return []
  return inset.value.lakes.map((l) => {
    const m = meta.value?.[l.id]
    const px = mx(l.x)
    const py = my(l.y)
    let tile: string | null = null
    let flow: { x1: number; y1: number; x2: number; y2: number } | null = null
    if (m) {
      const cl = Math.cos((m.lat * Math.PI) / 180)
      const c = m.corners_lonlat.map(([lon, lat]) => [mx(l.x + (lon - m.lon) * cl * KM_PER_DEG), my(l.y + (lat - m.lat) * KM_PER_DEG)] as [number, number])
      tile = c.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
      // ice flows along the c0 → c1 edge (the Globe's inflow wall is c3–c0)
      const [a, b] = [c[0], c[1]]
      flow = { x1: a[0] + (b[0] - a[0]) * 0.1, y1: a[1] + (b[1] - a[1]) * 0.1, x2: a[0] + (b[0] - a[0]) * 0.9, y2: a[1] + (b[1] - a[1]) * 0.9 }
    }
    return {
      id: l.id,
      num: l.num,
      px,
      py,
      tile,
      flow,
      cur: l.id === lakeId.value,
      shape: PHASE_CENTER_MARKERS[l.num] ?? 'o',
      lbl: DFD_PROBLEM_MAP_LABELS[l.num] ?? { dx: 16, dy: 5, anchor: 'start' as const },
    }
  })
})
const mapCur = computed(() => mapLakes.value.find((l) => l.cur) ?? null)

// the silhouette: a third of the map wide, the window drawn to its scale
const silhouetteUrl = mediaUrl('shared/greenland_silhouette.png')
const SIL_ASPECT = 1785 / 979
const silW = computed(() => Math.round(mapW.value * 0.34))
const silH = computed(() => Math.round(silW.value * SIL_ASPECT))
const silBox = computed(() => {
  const f = inset.value?.frame
  const kmPx = silH.value / DFD_PROBLEM_GREENLAND_NS_KM
  const w = f ? 2 * f.half_x * kmPx : 12
  const h = f ? 2 * f.half_y * kmPx : 16
  return {
    left: `${DFD_PROBLEM_SILHOUETTE_AOI.x * silW.value - w / 2}px`,
    top: `${DFD_PROBLEM_SILHOUETTE_AOI.y * silH.value - h / 2}px`,
    width: `${w}px`,
    height: `${h}px`,
  }
})

// ── the tile: the drapes are north-up plate-carrée boxes (the block's
// textures) with the rotated model square inside; the square is drawn
// axis-aligned here — the affine map from texture uv to the tile's frame
// (x along flow from the inflow wall, y across), clipped to the square ──
const clipId = `pb-clip-${Math.random().toString(36).slice(2, 8)}`
const rasters = computed(() => {
  const m = lake.value
  if (!m) return []
  const keys: DfdProblemRaster[] = ['s2_pre', 's2_post', 'stress_v_nopatch', 'stress_v_patch', 'stress_viscous']
  return keys.map((k) => ({ key: k, url: m[k] ? mediaUrl(`ch02/sim/${m[k]}`) : '' }))
})
interface Affine { m00: number; m01: number; m10: number; m11: number; e: number; f: number }
const affine = computed<Affine | null>(() => {
  const m = lake.value
  if (!m) return null
  const b = m.bbox
  const uv = ([lon, lat]: [number, number]): [number, number] => [(lon - b.lon_w) / (b.lon_e - b.lon_w), (b.lat_n - lat) / (b.lat_n - b.lat_s)]
  const [c0, c1, , c3] = m.corners_lonlat.map(uv)
  const ex = [c1[0] - c0[0], c1[1] - c0[1]]
  const ey = [c3[0] - c0[0], c3[1] - c0[1]]
  // p = c0 + a·ex + b·ey → (a, b); the screen: x = T·a, y = T·(1 − b)
  const det = ex[0] * ey[1] - ey[0] * ex[1]
  const S = T.value
  const m00 = (S * ey[1]) / det
  const m01 = (-S * ey[0]) / det
  const m10 = (S * ex[1]) / det
  const m11 = (-S * ex[0]) / det
  return { m00, m01, m10, m11, e: -(m00 * c0[0] + m01 * c0[1]), f: S - (m10 * c0[0] + m11 * c0[1]) }
})
const xform = computed(() => {
  const a = affine.value
  return a ? `matrix(${a.m00} ${a.m10} ${a.m01} ${a.m11} ${a.e} ${a.f})` : ''
})
function toTile(u: number, v: number): [number, number] {
  const a = affine.value!
  return [a.m00 * u + a.m01 * v + a.e, a.m10 * u + a.m11 * v + a.f]
}
/** Screen angle of north [deg, y down] — the frame is turned to the flow. */
const northDeg = computed(() => {
  const a = affine.value
  return a ? (Math.atan2(-a.m11, -a.m01) * 180) / Math.PI : -90
})
const lblPx = computed(() => Math.min(20, Math.max(13, T.value / 36)))
type Box = { x0: number; y0: number; x1: number; y1: number }
const hits = (a: Box, b: Box) => a.x0 < b.x1 && a.x1 > b.x0 && a.y0 < b.y1 && a.y1 > b.y0
const tileLakes = computed(() => {
  const r = rings.value
  if (!r || !affine.value) return []
  const S = T.value
  const lbl = lblPx.value
  const lakes = r.lakes.map((l) => {
    const pts = l.rings_uv.flat().map(([u, v]) => toTile(u, v))
    const xs = pts.map((p) => p[0])
    const ys = pts.map((p) => p[1])
    const st = SIM_LAKE_STYLE[l.cls] ?? SIM_LAKE_STYLE.gray
    return {
      num: l.num,
      center: l.center,
      box: { x0: Math.min(...xs) - 2, y0: Math.min(...ys) - 2, x1: Math.max(...xs) + 2, y1: Math.max(...ys) + 2 } as Box,
      d: l.rings_uv.map((ring) => 'M ' + ring.map(([u, v]) => toTile(u, v).map((q) => q.toFixed(1)).join(' ')).join(' L ') + ' Z').join(' '),
      color: l.center ? '#f4cf6a' : st.color,
      dash: st.dash.length ? '7 5' : undefined,
      lx: 0,
      ly: 0,
      anchor: 'start' as 'start' | 'end' | 'middle',
    }
  })
  // The numbers: the lake on the tile's above its outline, centred; each
  // neighbour's to the right of its outline, else left, above, below —
  // the first slot clear of every outline, the placed numbers and the
  // frame (2283 sits right under 2394's number otherwise).
  const taken: Box[] = lakes.map((l) => l.box)
  const frame: Box = { x0: 4, y0: 4, x1: S - 4, y1: S - 4 }
  const inside = (b: Box) => b.x0 >= frame.x0 && b.y0 >= frame.y0 && b.x1 <= frame.x1 && b.y1 <= frame.y1
  const cur = lakes.find((l) => l.center)
  if (cur) {
    const w = String(cur.num).length * lbl * 1.25 * 0.62
    const cx = (cur.box.x0 + cur.box.x1) / 2
    cur.lx = cx
    cur.ly = cur.box.y0 - 8
    cur.anchor = 'middle'
    taken.push({ x0: cx - w / 2, y0: cur.ly - lbl * 1.25, x1: cx + w / 2, y1: cur.ly + 4 })
  }
  for (const l of lakes) {
    if (l.center) continue
    const w = String(l.num).length * lbl * 0.62
    const b = l.box
    const cx = (b.x0 + b.x1) / 2
    const cy = (b.y0 + b.y1) / 2
    const slots: { lx: number; ly: number; anchor: 'start' | 'end' | 'middle'; box: Box }[] = [
      { lx: b.x1 + 5, ly: cy + lbl * 0.36, anchor: 'start', box: { x0: b.x1 + 5, y0: cy - lbl * 0.55, x1: b.x1 + 5 + w, y1: cy + lbl * 0.55 } },
      { lx: b.x0 - 5, ly: cy + lbl * 0.36, anchor: 'end', box: { x0: b.x0 - 5 - w, y0: cy - lbl * 0.55, x1: b.x0 - 5, y1: cy + lbl * 0.55 } },
      { lx: cx, ly: b.y0 - 6, anchor: 'middle', box: { x0: cx - w / 2, y0: b.y0 - 6 - lbl, x1: cx + w / 2, y1: b.y0 - 2 } },
      { lx: cx, ly: b.y1 + 5 + lbl * 0.8, anchor: 'middle', box: { x0: cx - w / 2, y0: b.y1 + 4, x1: cx + w / 2, y1: b.y1 + 6 + lbl } },
    ]
    const pick = slots.find((s) => inside(s.box) && !taken.some((t) => t !== b && hits(s.box, t))) ?? slots[0]
    l.lx = pick.lx
    l.ly = pick.ly
    l.anchor = pick.anchor
    taken.push(pick.box)
  }
  return lakes
})
// furniture
const SCALE_KM = 5
const furn = computed(() => Math.round(T.value * 0.045))
const arrowL = computed(() => Math.round(T.value * 0.1))
const northL = computed(() => Math.round(T.value * 0.055))
const scaleL = computed(() => (lake.value ? (SCALE_KM / (2 * lake.value.domain_half_km)) * T.value : 0))

// the block's colour bar: the symbol at 2.1 CSS px per bp (the talk's)
const cbarSym = ref(DFD_PROBLEM_STATIONS[2].cbar)
const CBAR_TICKS = [
  { p: 0, l: '−1' },
  { p: 50, l: '0' },
  { p: 100, l: '+1' },
]
const cbarBox = computed(() => {
  const b = cbarSym.value ? CH2_EQ[cbarSym.value] : null
  return b ? { width: `${b.w * 2.1}px`, height: `${b.h * 2.1}px` } : {}
})
// the symbol keeps the last stress station's while the bar fades out
watch(
  () => station.value.cbar,
  (s) => {
    if (s) cbarSym.value = s
  },
  { immediate: true },
)
const dateShown = computed(() => {
  const s = station.value
  if (!s.date || !lake.value) return ''
  return dfdProblemDate(s.date === 'pre' ? lake.value.date_pre : lake.value.date_post)
})

onMounted(() => {
  metaP ??= getJson<{ lakes: SimDomainMeta[] }>('ch02/sim/sim_domains_v2.json').then((j) =>
    j ? Object.fromEntries(j.lakes.map((l) => [l.id, l])) : null,
  )
  metaP.then((j) => {
    if (j) meta.value = j
    else console.warn('[dfd problem] sim manifest failed to load')
  })
  insetP ??= getJson<InsetFile>('ch02/inset/centerlakes_v1.json')
  insetP.then((j) => {
    if (j) inset.value = j
    else console.warn('[dfd problem] centre-lakes inset failed to load')
  })
  loadRings(lakeId.value)
  loadCh2Phase().then((j) => (phase.value = j))
  if (root.value) {
    const measure = () => {
      const r = root.value!.getBoundingClientRect()
      W.value = Math.max(320, Math.floor(r.width))
      H.value = Math.max(240, Math.floor(r.height))
    }
    measure()
    ro = new ResizeObserver(measure)
    ro.observe(root.value)
  }
})
onBeforeUnmount(() => ro?.disconnect())
</script>

<style scoped>
.pb {
  height: 100%;
  display: grid;
  grid-template-columns: var(--map) var(--T) var(--T);
  grid-template-rows: var(--rt) var(--T) var(--rb) var(--bar);
  column-gap: var(--gap);
  row-gap: var(--rgap);
  justify-content: center;
  align-content: center;
  color: #f5f0e6;
  font-family: 'Inter', system-ui, sans-serif;
  user-select: none;
}

/* ── the map column ── */
.pb-map {
  grid-column: 1;
  grid-row: 1 / span 4;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 18px;
  min-height: 0;
}
.pb-map-svg {
  display: block;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.6);
}
/* the inset's stage: the sheet pale, the land dark, the sea darker */
.pbm-ice { fill: #b9c4cd; }
.pbm-sea { fill: #0e1b27; }
.pbm-land { fill: #4d463c; }
.pbm-margin { fill: none; stroke: #1d2228; stroke-width: 1.5; stroke-linejoin: round; }
.pbm-tile { fill: none; stroke: rgba(20, 23, 28, 0.75); stroke-width: 1.25; stroke-linejoin: miter; }
.pbm-tile-cur { fill: rgba(244, 207, 106, 0.12); stroke: #e8b94a; stroke-width: 2.2; stroke-linejoin: miter; }
.pbm-flow { stroke: #f4cf6a; stroke-width: 2.2; }
.pbm-dim { fill: #2a2f36; stroke: rgba(245, 240, 230, 0.7); stroke-width: 1; }
.pbm-cur { fill: #f4cf6a; stroke: #0a0a0a; stroke-width: 2.2; stroke-linejoin: round; }
.pbm-num {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 19px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  fill: #f4cf6a;
  paint-order: stroke;
  stroke: #0a0a0a;
  stroke-width: 4.5px;
  stroke-linejoin: round;
}
.pbm-num-dim { font-size: 12.5px; font-weight: 600; fill: #14171c; stroke: rgba(185, 196, 205, 0.9); stroke-width: 3px; }
.pbm-disc { fill: transparent; stroke: none; }
.pbm-other { transition: opacity 0.2s; }
.pbm-hit { cursor: pointer; }
.pbm-hit:hover .pbm-dim { fill: #f4cf6a; }
.pbm-hit:hover .pbm-tile { stroke: #e8b94a; stroke-width: 2; }
.pbm-bar line { stroke: #14171c; stroke-width: 2; }
.pbm-bartxt { font-family: 'Inter', system-ui, sans-serif; font-size: 13px; font-weight: 700; fill: #14171c; }
.pbm-frame { fill: none; stroke: rgba(245, 240, 230, 0.85); stroke-width: 1.5; }

.pb-sil { position: relative; flex: none; }
.pb-sil-mask {
  position: absolute;
  inset: 0;
  background: rgba(185, 196, 205, 0.55);
  -webkit-mask: var(--sil) center / contain no-repeat;
  mask: var(--sil) center / contain no-repeat;
}
.pb-sil-box {
  position: absolute;
  border: 1.5px solid #f4cf6a;
  background: rgba(244, 207, 106, 0.25);
  box-shadow: 0 0 10px rgba(244, 207, 106, 0.7);
}

/* ── the title ── */
.pb-title {
  grid-column: 2;
  grid-row: 1;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1em;
  white-space: nowrap;
  overflow: hidden;
  align-self: end;
  padding-bottom: 6px;
}
.pb-ttl-wrap { display: inline-flex; align-items: baseline; gap: 0.7em; min-width: 0; }
.pb-flow {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex: none;
  align-self: center;
  color: var(--gold-bright);
  font-size: clamp(11px, calc(var(--T) / 44), 16px);
  font-weight: 700;
  letter-spacing: 0.12em;
}
.pb-flow svg { display: block; overflow: visible; }
.pb-ttl {
  font-family: 'EB Garamond', Georgia, serif;
  font-weight: 600;
  font-size: clamp(20px, calc(var(--T) / 19), 32px);
  line-height: 1;
  color: var(--gold-bright);
}
.pb-date {
  font-family: 'EB Garamond', Georgia, serif;
  font-size: clamp(16px, calc(var(--T) / 26), 24px);
  color: rgba(245, 240, 230, 0.8);
  font-variant-numeric: oldstyle-nums;
}
/* on a laptop-wide band the date in the title ran into the flow arrow; the
   station bar carries the date anyway */
@media (max-width: 1600px) {
  .pb-date { display: none; }
}

/* ── the tile ── */
.pb-tile {
  grid-column: 2;
  grid-row: 2;
  width: var(--T);
  height: var(--T);
}
.pb-tile-svg { display: block; overflow: visible; }
.pb-under { fill: #0b0d12; }
.pb-raster { transition: opacity 0.55s ease; }
.pb-ring-halo { fill: none; stroke: rgba(0, 0, 0, 0.6); stroke-width: 4.5px; stroke-linejoin: round; }
.pb-ring-halo.pb-ring-c { stroke-width: 6px; }
.pb-ring { fill: none; stroke-width: 2.2px; stroke-linejoin: round; }
.pb-ring.pb-ring-c { stroke-width: 3.2px; }
.pb-num {
  font-family: 'Inter', system-ui, sans-serif;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  fill: #f5f0e6;
  paint-order: stroke;
  stroke: rgba(0, 0, 0, 0.85);
  stroke-width: 4px;
  stroke-linejoin: round;
}
.pb-num-c { fill: #f4cf6a; font-weight: 700; stroke-width: 5px; }
.pb-frame { fill: none; stroke: rgba(232, 185, 74, 0.9); stroke-width: 1.5px; }
/* furniture: gold over a dark ink, legible on imagery and on the white 0 kPa */
.pb-ink { stroke: rgba(0, 0, 0, 0.8); stroke-width: 6px; stroke-linecap: round; stroke-linejoin: round; fill: none; }
.pb-ink-fill { fill: rgba(0, 0, 0, 0.8); }
.pb-gold { stroke: #f4cf6a; stroke-width: 2.2px; stroke-linecap: round; stroke-linejoin: round; fill: none; }
.pb-gold-fill { fill: #f4cf6a; }
.pb-flbl {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: clamp(11px, calc(var(--T) / 44), 16px);
  font-weight: 700;
  letter-spacing: 0.12em;
  fill: #f4cf6a;
  paint-order: stroke;
  stroke: rgba(0, 0, 0, 0.85);
  stroke-width: 4px;
  stroke-linejoin: round;
}

/* ── the colour bar (the block's: matplotlib seismic, ±1 MPa) ── */
.pb-cbar {
  grid-column: 2;
  grid-row: 3;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  opacity: 0;
  transition: opacity 0.5s ease;
  filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.9));
}
.pb-cbar-on { opacity: 1; }
.pb-cbar-sym { display: block; }
.pb-cbar-scale { width: calc(var(--T) * 0.42); }
.pb-cbar-bar {
  height: 14px;
  border-radius: 2px;
  box-shadow: 0 0 0 1.5px rgba(245, 240, 230, 0.85);
  background: linear-gradient(
    to right,
    #00004c,
    #0000db 12%,
    #4747ff 26%,
    #b3b3ff 40%,
    #ffffff 50%,
    #ffb3b3 60%,
    #ff4747 74%,
    #db0000 88%,
    #800000 100%
  );
}
.pb-cbar-ticks {
  position: relative;
  height: 24px;
  font-size: 15px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.pb-cbar-ticks span {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1;
}
.pb-cbar-ticks i { display: block; width: 2px; height: 6px; margin: 2px 0 4px; background: rgba(245, 240, 230, 0.85); }

/* ── the stress space ── */
.pb-space {
  grid-column: 3;
  grid-row: 1 / span 3;
  min-height: 0;
  display: flex;
  align-items: center;
  transition: opacity 0.5s ease;
}
.pb-space-dim { opacity: 0.5; }
.pb-space :deep(.ss-svg) { width: 100%; height: 100%; }

/* ── the stations: five dots on one line, the current one filled ── */
.pb-bar {
  grid-column: 2 / span 2;
  grid-row: 4;
  position: relative;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  align-items: start;
  padding-top: 6px;
}
.pb-bar-line {
  position: absolute;
  left: 10%;
  right: 10%;
  top: 13px;
  height: 1.5px;
  background: rgba(232, 185, 74, 0.45);
}
.pb-st {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  border: 0;
  background: transparent;
  color: rgba(245, 240, 230, 0.55);
  font-family: 'Inter', system-ui, sans-serif;
  cursor: pointer;
  padding: 0 4px;
  transition: color 0.25s;
}
.pb-st:hover { color: var(--gold-bright); }
.pb-dot {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  border: 2px solid rgba(232, 185, 74, 0.7);
  background: #050505;
  margin-bottom: 4px;
  transition: background 0.3s, border-color 0.3s, box-shadow 0.3s, transform 0.3s;
}
.pb-st-done .pb-dot { background: rgba(232, 185, 74, 0.55); }
.pb-st-on { color: var(--gold-bright); }
.pb-st-on .pb-dot {
  background: var(--gold-bright);
  border-color: var(--gold-bright);
  box-shadow: 0 0 14px rgba(245, 199, 94, 0.65);
  transform: scale(1.25);
}
.pb-st-stage {
  font-size: clamp(10px, calc(var(--T) / 48), 13px);
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}
.pb-st-layer {
  font-size: clamp(14px, calc(var(--T) / 32), 19px);
  font-weight: 600;
  letter-spacing: 0.02em;
  line-height: 1.1;
}
/* σ_t1 / Δσ_t1: math, never upper-cased */
.pb-sym { font-family: 'EB Garamond', Georgia, serif; font-style: italic; font-size: 1.15em; font-weight: 500; letter-spacing: 0; }
.pb-sym sub { font-size: 0.66em; font-style: normal; }
.pb-st-date {
  min-height: 1em;
  font-family: 'EB Garamond', Georgia, serif;
  font-size: clamp(12px, calc(var(--T) / 40), 15px);
  color: rgba(245, 240, 230, 0.65);
}
.pb-st-on .pb-st-date { color: rgba(245, 240, 230, 0.9); }
</style>
