<template>
  <transition name="psp">
    <div
      v-if="visible && data"
      class="psp-root"
      :class="{ 'psp-reserve': reserveBottom }"
      @pointerleave="$emit('lake-hover', null)"
    >
      <!-- The director asked for the stress math symbols alone, without
           words like "difference" and "with patch": Chapter 2
           heads the panel with the model's name alone; the MGSIM page
           keeps its own label. -->
      <div class="psp-head">
        <div v-if="label" class="psp-kicker">Lake-drainage stress space</div>
        <div v-if="label" class="psp-model">{{ label }}</div>
        <div v-else class="psp-title">{{ model === 'viscous' ? 'Viscous' : 'Elastic' }}</div>
      </div>
      <div class="psp-legend">
        <span class="psp-leg-item"><span class="psp-dot" style="background:#31e5ff" /> englacial</span>
        <span class="psp-leg-item"><span class="psp-dot" style="background:#c7cdd4" /> lateral</span>
        <span class="psp-leg-item"><span class="psp-dot psp-open" /> none</span>
        <span v-if="hasMagenta" class="psp-leg-item"><span class="psp-dot" style="background:#ff5df2" /> same-day</span>
        <span v-if="label" class="psp-leg-note">{{ ghostKeys?.length ? '· small = the other beds' : '◇ other lake groups' }}</span>
      </div>
      <div v-for="p in panels" :key="p.slot" class="psp-panel">
        <svg :viewBox="`0 0 ${W} ${W}`" class="psp-svg">
          <defs>
            <clipPath :id="`psp-clip-${p.slot}`">
              <rect :x="PAD_L" :y="PAD_T" :width="plotW" :height="plotW" />
            </clipPath>
          </defs>
          <!-- frame + zero lines -->
          <rect :x="PAD_L" :y="PAD_T" :width="plotW" :height="plotW" class="psp-frame" />
          <line :x1="sx(0)" :x2="sx(0)" :y1="PAD_T" :y2="PAD_T + plotW" class="psp-zero" />
          <line :x1="PAD_L" :x2="PAD_L + plotW" :y1="sy(0)" :y2="sy(0)" class="psp-zero" />
          <!-- ticks -->
          <template v-for="t in ticks" :key="`t${t}`">
            <line :x1="sx(t)" :x2="sx(t)" :y1="PAD_T + plotW" :y2="PAD_T + plotW + 5" class="psp-tick" />
            <text :x="sx(t)" :y="PAD_T + plotW + 22" text-anchor="middle" class="psp-ticklbl">{{ fmtTick(t) }}</text>
            <line :x1="PAD_L - 5" :x2="PAD_L" :y1="sy(t)" :y2="sy(t)" class="psp-tick" />
            <text :x="PAD_L - 9" :y="sy(t) + 5" text-anchor="end" class="psp-ticklbl">{{ fmtTick(t) }}</text>
          </template>
          <!-- the axis titles as typeset math (the results beats' LaTeX
               SVGs, R2 ch02/eq/): σ^post_t1,t2 [kPa] · Δσ_t1,t2 [kPa] -->
          <image v-bind="eqAt(p.slot === 1 ? 'ax_post_t1' : 'ax_post_t2', PAD_L + plotW / 2, W - 3, 'bottom')" />
          <g :transform="`rotate(-90 ${AXY_X} ${PAD_T + plotW / 2})`">
            <image v-bind="eqAt(p.slot === 1 ? 'ax_diff_t1' : 'ax_diff_t2', AXY_X, PAD_T + plotW / 2, 'middle')" />
          </g>
          <!-- MGSIM page: the ensemble cloud — every OTHER
               bed's value for each of this domain's lakes, small and
               faint, so the bright markers hop inside their own spread
               as the viewer flips beds. -->
          <g :clip-path="`url(#psp-clip-${p.slot})`" class="psp-ghosts">
            <path
              v-for="(g, gi) in p.ghosts"
              :key="`g${gi}`"
              :d="markerPath(g.shape, g.x, g.y, 4)"
              :fill="g.open ? 'none' : g.color"
              :stroke="g.color"
              :stroke-width="1"
              :opacity="g.num === highlightNum ? 0.85 : 0.32"
            />
          </g>
          <!-- points: other groups first (faint), this group on top.
               Axes are FIXED at ±500 kPa for every model —
               points beyond the frame clip out instead of pinning to
               the edge. The DOM order never changes with the hover
               (re-sorting the hovered node to
               the end moved it under the pointer, the browser never
               fired its mouseleave and the gold outline STUCK); the
               highlight is a separate, pointer-transparent layer. -->
          <g :clip-path="`url(#psp-clip-${p.slot})`"
            v-for="pt in p.pts"
            :key="`${pt.group}-${pt.num}-${pt.center}`"
            :data-num="pt.num"
            :style="{ opacity: pt.mine ? 1 : 0.22 }"
            class="psp-pt"
            @pointerenter="$emit('lake-hover', pt.num)"
            @pointerleave="$emit('lake-hover', null)"
          >
            <path
              :d="markerPath(pt.shape, pt.x, pt.y, pt.mine ? 9.5 : 6)"
              :fill="pt.open ? 'none' : pt.color"
              :stroke="pt.open ? pt.color : 'rgba(0,0,0,0.55)'"
              :stroke-width="pt.open ? 2 : 0.9"
            />
            <circle :cx="pt.x" :cy="pt.y" r="11" fill="transparent" />
          </g>
          <g :clip-path="`url(#psp-clip-${p.slot})`" class="psp-hl">
            <template v-for="pt in p.pts" :key="`h${pt.group}-${pt.num}-${pt.center}`">
              <template v-if="pt.num === highlightNum">
                <circle :cx="pt.x" :cy="pt.y" r="12" class="psp-glow" />
                <path
                  :d="markerPath(pt.shape, pt.x, pt.y, pt.mine ? 9.5 : 6)"
                  :fill="pt.open ? 'none' : pt.color"
                  stroke="#f5c75e"
                  stroke-width="2.4"
                  :opacity="pt.mine ? 1 : 0.6"
                />
              </template>
            </template>
          </g>
        </svg>
      </div>
      <div v-if="label" class="psp-foot">
        polygon-mean per lake · with patch vs (with − no patch) · marker = lake group · ±{{ data.error_kpa[0] }}–{{ data.error_kpa[1] }} kPa numerical error
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { mediaUrl } from '../config/media'
import { CH2_EQ, type Ch2EqName } from '../config/ch2Eqs'
import { CH2_AXIS_KPA, ch2EqUrl } from '../config/ch2Results'
import {
  PHASE_CENTER_MARKERS,
  PHASE_GROUP_STYLE,
  phaseMarkerPath,
  type PhasePoint,
  type PhaseSpaceFile,
} from '../config/simLakes'

// Ch.2 zoomed-in state: the paper's Fig. 5 stress-space
// diagram, rebuilt live from the published per-lake stress arrays.
// Appears on the RIGHT once a model pill is active. The CURRENT
// domain's lakes render bright with their group's marker shape; every
// other lake group stays as faint context (the full published phase
// space, so the separation boundary reads). Hovering a lake on the
// block glows its symbols here — and hovering a symbol glows the lake.
const props = defineProps<{
  visible: boolean
  model: 'elastic' | 'viscous'
  /** Display number of this domain's center lake (e.g. 2511). */
  centerNum: number
  highlightNum: number | null
  /** MGSIM page: another phase file (per-bed keys), the key
   *  to draw bright, the keys to draw as the faint ensemble cloud, and
   *  the header label. Ch.2 leaves these unset. */
  dataUrl?: string
  modelKey?: string
  ghostKeys?: string[]
  label?: string
  /** Ch.2: end above the bottom-right card row (bed-
   *  ensemble door, SEE MORE FIELDS) instead of running to the floor. */
  reserveBottom?: boolean
}>()

defineEmits<{ 'lake-hover': [num: number | null] }>()

// Markers + class colours: config/simLakes.ts (shared with the results
// beats' diagrams).
const CENTER_MARKERS = PHASE_CENTER_MARKERS
const GROUP_COLORS = PHASE_GROUP_STYLE
const markerPath = phaseMarkerPath

// The back-row legibility rule: 15-unit ticks and LaTeX axis titles
// need wider margins — the square plot shrinks to fit.
const W = 320
const PAD_L = 92
const PAD_T = 10
const PAD_R = 16
const plotW = W - PAD_L - PAD_R // square plot area
const AXY_X = 14 // the rotated y title's centre line
const K_AX = 2.15 // LaTeX units per bp (10 pt → ~21.5 units)
function eqAt(name: Ch2EqName, x: number, y: number, va: 'middle' | 'bottom') {
  const b = CH2_EQ[name]
  const w = b.w * K_AX
  const h = b.h * K_AX
  return { href: ch2EqUrl(name), x: x - w / 2, y: va === 'middle' ? y - h / 2 : y - h, width: w, height: h }
}
function fmtTick(t: number): string {
  return t < 0 ? `−${Math.abs(t)}` : `${t}`
}

// One in-flight promise per file (Ch.2's phase_space_v2.json, the MGSIM
// page's phase_space_mgsim.json) — shared across remounts.
const dataPromises = new Map<string, Promise<PhaseSpaceFile | null>>()
const data = ref<PhaseSpaceFile | null>(null)

function loadData(): void {
  const url = props.dataUrl ?? mediaUrl('ch02/sim/phase_space_v2.json')
  let p = dataPromises.get(url)
  if (!p) {
    p = fetch(url)
      .then((r) => (r.ok ? r.json() : null))
      .catch(() => null)
    dataPromises.set(url, p)
  }
  p.then((j) => {
    if ((props.dataUrl ?? mediaUrl('ch02/sim/phase_space_v2.json')) === url) data.value = j
  })
}
onMounted(loadData)
watch(() => props.dataUrl, loadData)

const hasMagenta = computed(() => {
  const d = data.value
  if (!d) return false
  const key = props.modelKey ?? props.model
  return (d.models[key]?.points ?? []).some((p) => p.group === 'magenta')
})

// The director asked for FIXED axes for all models and both stress
// components — the frame never changes between elastic and viscous.
// Points beyond it clip out of the plot. Chapter 2 uses the
// results beats' ONE ±1000 kPa frame (config/ch2Results CH2_AXIS_KPA) so
// the stress space doesn't rescale between beat 2 and beat 3; the MGSIM
// page keeps its ±500 kPa.
const axis = computed(() => (props.dataUrl ? 500 : CH2_AXIS_KPA))
const ticks = computed(() => {
  const a = axis.value
  return [-a, -a / 2, 0, a / 2, a]
})

function sx(kpa: number): number {
  return PAD_L + ((kpa + axis.value) / (2 * axis.value)) * plotW
}
function sy(kpa: number): number {
  return PAD_T + plotW - ((kpa + axis.value) / (2 * axis.value)) * plotW
}

interface PanelPt {
  num: number
  group: string
  center: number
  x: number
  y: number
  color: string
  open: boolean
  shape: string
  mine: boolean
}

const panels = computed(() => {
  const d = data.value
  if (!d) return []
  const key = props.modelKey ?? props.model
  const pts = d.models[key]?.points ?? []
  // The ensemble cloud: this domain's lakes under every OTHER bed.
  const ghostPts: PhasePoint[] = []
  for (const gk of props.ghostKeys ?? []) {
    if (gk === key) continue
    for (const p of d.models[gk]?.points ?? []) {
      if (p.center === props.centerNum) ghostPts.push(p)
    }
  }
  const mk = (slot: 1 | 2, xName: string) => {
    const ghosts: PanelPt[] = []
    for (const p of ghostPts) {
      const xv = slot === 1 ? p.x1 : p.x2
      const yv = slot === 1 ? p.y1 : p.y2
      const g = GROUP_COLORS[p.group]
      if (xv === null || yv === null || !g) continue
      ghosts.push({ num: p.num, group: p.group, center: p.center, x: sx(xv), y: sy(yv), color: g.color, open: g.open,
        shape: CENTER_MARKERS[p.center] ?? 'o', mine: false })
    }
    const out: PanelPt[] = []
    for (const p of pts as PhasePoint[]) {
      const xv = slot === 1 ? p.x1 : p.x2
      const yv = slot === 1 ? p.y1 : p.y2
      if (xv === null || yv === null) continue
      const g = GROUP_COLORS[p.group]
      if (!g) continue
      out.push({
        num: p.num,
        group: p.group,
        center: p.center,
        x: sx(xv),
        y: sy(yv),
        color: g.color,
        open: g.open,
        shape: CENTER_MARKERS[p.center] ?? 'o',
        mine: p.center === props.centerNum,
      })
    }
    // faint context first, this domain on top — a STABLE order that
    // never depends on the hover (the highlight has its own layer).
    out.sort((a, b) => Number(a.mine) - Number(b.mine))
    return { slot, xName, pts: out, ghosts }
  }
  return [mk(1, 'σ_t1'), mk(2, 'σ_t2')]
})

</script>

<style scoped>
.psp-root {
  /* The director asked for a MUCH larger panel — the right column runs the
     full frame height below the beat-nav pills; both panels stack and
     share it equally. */
  position: absolute;
  right: 18px;
  /* Below the beat-nav pills in BOTH nav layouts (they drop to 6.2vh
     on narrower viewports). */
  top: max(106px, calc(6.2vh + 42px));
  bottom: 14px;
  width: min(30vw, 500px);
  z-index: 12;
  display: flex;
  flex-direction: column;
  background: rgba(10, 9, 8, 0.92);
  border: 1px solid rgba(245, 199, 94, 0.35);
  border-radius: 14px;
  padding: 0.8rem 0.9rem 0.6rem;
  color: #f5f0e6;
  font-family: 'Inter', system-ui, sans-serif;
  backdrop-filter: blur(10px);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.55);
  pointer-events: auto;
  overflow: hidden;
}

.psp-root.psp-reserve {
  /* SimBlockCards: 22 px from the floor, ~48 px tall, + a 14 px gap */
  bottom: 84px;
  /* …and under Chapter 2's stations, which run the screen's width above
     it (SimViewControls --svc-bottom) */
  top: max(106px, calc(6.2vh + 42px), calc(var(--svc-bottom, 0px) + 12px));
}

.psp-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
}

.psp-kicker {
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(245, 199, 94, 0.9);
}

.psp-model {
  font-size: 0.66rem;
  letter-spacing: 0.06em;
  color: rgba(245, 240, 230, 0.6);
  white-space: nowrap;
}

.psp-legend {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-top: 0.45rem;
  font-size: 15px;
  color: rgba(245, 240, 230, 0.94);
}

.psp-leg-item {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.psp-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
}

.psp-open {
  background: transparent !important;
  border: 1.6px solid #e8e4da;
}

.psp-leg-note {
  margin-left: auto;
  color: rgba(245, 240, 230, 0.4);
}

.psp-panel {
  flex: 1 1 0;
  min-height: 0;
  margin-top: 0.35rem;
}

.psp-svg {
  width: 100%;
  height: 100%;
  display: block;
}

.psp-frame {
  fill: none;
  stroke: rgba(245, 245, 245, 0.6);
  stroke-width: 1.6px;
  vector-effect: non-scaling-stroke;
}

.psp-zero {
  stroke: rgba(245, 245, 245, 0.45);
  stroke-width: 1.5px;
  vector-effect: non-scaling-stroke;
}

.psp-tick {
  stroke: rgba(245, 245, 245, 0.8);
  stroke-width: 1.6px;
  vector-effect: non-scaling-stroke;
}

.psp-ticklbl {
  fill: rgba(245, 240, 230, 0.95);
  font-size: 15px;
  font-variant-numeric: tabular-nums;
}

.psp-title {
  font-family: 'EB Garamond', serif;
  font-size: 1.9rem;
  line-height: 1;
  color: var(--gold, #f4cf6a);
}

.psp-pt {
  cursor: pointer;
}

.psp-hl {
  pointer-events: none;
}

.psp-glow {
  fill: rgba(245, 199, 94, 0.22);
  stroke: rgba(245, 199, 94, 0.7);
  stroke-width: 1.4;
}

.psp-foot {
  margin-top: 0.3rem;
  font-size: 0.6rem;
  color: rgba(245, 240, 230, 0.42);
}

.psp-enter-active,
.psp-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.psp-enter-from,
.psp-leave-to {
  opacity: 0;
  transform: translateX(14px);
}
</style>
