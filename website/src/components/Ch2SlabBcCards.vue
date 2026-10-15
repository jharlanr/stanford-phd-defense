<template>
  <!-- The idealized slab's BOUNDARY CONDITIONS (the director wanted a
       boundary-conditions button for the slab, showing the periodic
       boundary conditions and the rest): one card per boundary — the free SURFACE,
       the two PERIODIC pairs (the x-walls are one wall, the y-walls are
       one), the BED (impenetrable, linear Weertman outside the free-slip
       patch, traction-free inside) — each tied by gold leaders to its
       boundary on the block (both walls of a periodic pair). The LaTeX is
       the PNAS SI's notation (cinematic/scene_ch02/build_slab_eqs.py →
       R2 ch02/slab_eq_v1/). Hovering a card lights its walls on the block
       (Ch2Slab.vue). Figure labels only. -->
  <div v-if="active" class="sbc-root">
    <svg class="sbc-leaders" :width="vw" :height="vh">
      <g v-for="l in leaders" :key="l.id">
        <line :x1="l.x1" :y1="l.y1" :x2="l.x2" :y2="l.y2" class="sbc-lead" :class="{ 'sbc-lead-on': l.key === hover }" />
        <circle :cx="l.x2" :cy="l.y2" r="4.2" class="sbc-dot" :class="{ 'sbc-dot-on': l.key === hover }" />
      </g>
    </svg>
    <div
      v-for="c in CARDS"
      :key="c.key"
      :ref="(el) => setCardEl(c.key, el as HTMLElement | null)"
      class="sbc-card"
      :class="[`sbc-${c.side}`, { 'sbc-on': c.key === hover }]"
      :style="cardStyle(c)"
      :data-bc="c.key"
      @pointerenter="setHover(c.key)"
      @pointerleave="setHover(null)"
    >
      <span class="sbc-head">
        <span class="sbc-kicker">{{ c.name }}</span>
        <img class="sbc-loc" :src="slabEqUrl(c.loc)" :style="eqStyle(c.loc, LOC_K)" alt="" />
      </span>
      <span class="sbc-body">
        <span v-for="(ln, i) in c.lines" :key="ln + i" class="sbc-line" :class="{ 'sbc-rule': ln === 'eta' }">
          <img :src="slabEqUrl(ln)" :style="eqStyle(ln, EQ_K)" alt="" />
        </span>
        <span v-if="c.key === 'perx' || c.key === 'pery'" class="sbc-val">L = {{ lKm }} km</span>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { CH2_SLAB_EQ } from '../config/ch2SlabEqs'
import { slabEqUrl } from '../config/ch2Slab'

export type SlabBcKey = 'surface' | 'perx' | 'pery' | 'bed'
export interface SlabBcAnchors {
  /** Screen points per boundary (a periodic pair has two). */
  points: Record<SlabBcKey, { x: number; y: number }[]>
  /** The two card columns' inner edges + the band they live in [px]. */
  leftX: number
  rightX: number
  top: number
  bottom: number
}

const props = defineProps<{ active: boolean; anchors: SlabBcAnchors | null; lKm: number }>()
const emit = defineEmits<{ hover: [key: SlabBcKey | null] }>()

const EQ_K = 2.0
const LOC_K = 1.5

interface Card { key: SlabBcKey; name: string; loc: string; lines: string[]; side: 'l' | 'r' }
const CARDS: Card[] = [
  { key: 'surface', name: 'Surface', loc: 'loc_zs', lines: ['surface'], side: 'l' },
  { key: 'perx', name: 'Periodic', loc: 'loc_x', lines: ['per_x'], side: 'l' },
  { key: 'pery', name: 'Periodic', loc: 'loc_y', lines: ['per_y'], side: 'r' },
  { key: 'bed', name: 'Bed', loc: 'loc_zb', lines: ['bed_imp', 'bed_w', 'bed_cb', 'bed_c', 'eta'], side: 'r' },
]

function eqStyle(name: string, k: number): Record<string, string> {
  const b = CH2_SLAB_EQ[name]
  if (!b) return { display: 'none' }
  return { width: `${b.w * k}px`, height: `${b.h * k}px` }
}

const hover = ref<SlabBcKey | null>(null)
function setHover(k: SlabBcKey | null): void {
  hover.value = k
  emit('hover', k)
}

const vw = ref(window.innerWidth)
const vh = ref(window.innerHeight)
const cardEls: Partial<Record<SlabBcKey, HTMLElement>> = {}
function setCardEl(k: SlabBcKey, el: HTMLElement | null): void {
  if (el) cardEls[k] = el
  else delete cardEls[k]
}
// measured card heights (the column stacks them)
const heights = ref<Record<string, number>>({})
const GAP = 18
function cardStyle(c: Card): Record<string, string> {
  const a = props.anchors
  if (!a) return { visibility: 'hidden' }
  const col = CARDS.filter((x) => x.side === c.side)
  const total = col.reduce((s, x) => s + (heights.value[x.key] ?? 80), 0) + GAP * (col.length - 1)
  let y = Math.max(a.top, (a.top + a.bottom) / 2 - total / 2)
  for (const x of col) {
    if (x.key === c.key) break
    y += (heights.value[x.key] ?? 80) + GAP
  }
  return c.side === 'l'
    ? { left: `${Math.max(16, a.leftX)}px`, top: `${y}px` }
    : { right: `${Math.max(16, vw.value - a.rightX)}px`, top: `${y}px` }
}

const tick = ref(0)
const leaders = computed(() => {
  void tick.value
  const a = props.anchors
  if (!a) return []
  const out: { id: string; key: SlabBcKey; x1: number; y1: number; x2: number; y2: number }[] = []
  for (const c of CARDS) {
    const el = cardEls[c.key]
    if (!el) continue
    const r = el.getBoundingClientRect()
    if (r.width === 0) continue
    const x1 = c.side === 'l' ? r.right : r.left
    a.points[c.key].forEach((p, i) => {
      const y1 = Math.min(r.bottom - 12, Math.max(r.top + 12, p.y))
      out.push({ id: `${c.key}${i}`, key: c.key, x1, y1, x2: p.x, y2: p.y })
    })
  }
  return out
})

let raf = 0
function frame(): void {
  if (props.active) {
    vw.value = window.innerWidth
    vh.value = window.innerHeight
    const h: Record<string, number> = {}
    let changed = false
    for (const c of CARDS) {
      const el = cardEls[c.key]
      const v = el ? Math.round(el.getBoundingClientRect().height) : 80
      h[c.key] = v
      if (heights.value[c.key] !== v) changed = true
    }
    if (changed) heights.value = h
    tick.value++
  }
  raf = requestAnimationFrame(frame)
}
onMounted(() => { raf = requestAnimationFrame(frame) })
onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  emit('hover', null)
})
</script>

<style scoped>
.sbc-root {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 3;
}
.sbc-leaders {
  position: absolute;
  inset: 0;
  overflow: visible;
}
.sbc-lead {
  stroke: rgba(245, 199, 94, 0.8);
  stroke-width: 1.8;
}
.sbc-lead-on { stroke: #f5c75e; stroke-width: 2.4; }
.sbc-dot { fill: rgba(245, 199, 94, 0.9); }
.sbc-dot-on { fill: #f5c75e; }

.sbc-card {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 10px 16px 12px;
  box-sizing: border-box;
  background: rgba(10, 9, 8, 0.88);
  border: 1.5px solid rgba(245, 199, 94, 0.55);
  border-radius: 10px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.55);
  font-family: 'Inter', system-ui, sans-serif;
  pointer-events: auto;
  transition: border-color 0.25s, box-shadow 0.25s, background 0.25s;
}
.sbc-on {
  border-color: #f5c75e;
  background: rgba(22, 17, 9, 0.94);
  box-shadow: 0 10px 36px rgba(0, 0, 0, 0.6), 0 0 26px rgba(245, 199, 94, 0.28);
}
.sbc-head {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 22px;
}
.sbc-kicker {
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(245, 199, 94, 0.95);
  white-space: nowrap;
}
.sbc-loc { display: block; opacity: 0.9; }
.sbc-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.sbc-line { display: block; margin-top: 7px; }
.sbc-line img { display: block; }
.sbc-rule {
  margin-top: 10px;
  padding-top: 7px;
  border-top: 1px solid rgba(245, 199, 94, 0.35);
  width: 100%;
}
.sbc-val {
  margin-top: 8px;
  font-family: 'EB Garamond', serif;
  font-style: italic;
  font-size: 1.15rem;
  color: #f5f0e6;
}
</style>
