<template>
  <!-- Ch.2 boundary-condition cards. One card
       per boundary of the 24.75 km model domain — SURFACE, INFLOW,
       OUTFLOW, the two LATERAL walls, the BED — each a figure label
       (name + where + the condition, LaTeX) tied to its boundary by a
       leader line (window.__simBcScreens, projected per frame by the
       Globe). Click a card → Explore flies the camera to that boundary
       head-on and the Globe draws its overlay; the card lifts, opens
       to the full condition + this lake's values, and the others dock
       in a column. Click it again → back to the overview. -->
  <div v-if="active" class="bcd-root">
    <svg class="bcd-leaders" :width="vw" :height="vh">
      <g v-for="c in laid" :key="c.key">
        <template v-if="c.lead">
          <line
            :x1="c.lead.x1" :y1="c.lead.y1" :x2="c.lead.x2" :y2="c.lead.y2"
            class="bcd-lead" :class="{ 'bcd-lead-on': c.key === focus }"
            :style="{ opacity: c.alpha * leadAlpha }"
          />
          <circle
            :cx="c.lead.x2" :cy="c.lead.y2" r="4.2"
            class="bcd-dot" :class="{ 'bcd-dot-on': c.key === focus }"
            :style="{ opacity: c.alpha * leadAlpha }"
          />
        </template>
      </g>
    </svg>
    <button
      v-for="c in laid"
      :key="c.key"
      type="button"
      class="bcd-card"
      :class="{ 'bcd-on': c.key === focus, 'bcd-docked': !!focus && c.key !== focus }"
      :style="{ left: c.x + 'px', top: c.y + 'px', width: c.w + 'px', opacity: c.alpha }"
      :data-bc="c.key"
      @click="onClick(c.key)"
      @pointerenter="emit('hover', c.key)"
      @pointerleave="emit('hover', null)"
    >
      <span class="bcd-head">
        <span class="bcd-kicker">{{ NAMES[c.key] }}</span>
        <img
          class="bcd-loc"
          :src="eqUrl(c.loc)"
          :style="eqStyle(c.loc, LOC_K)"
          alt=""
        />
        <span v-if="c.key === focus" class="bcd-x" aria-hidden="true">×</span>
      </span>
      <span v-if="c.lines.length" class="bcd-body">
        <span
          v-for="(ln, i) in c.lines"
          :key="ln.name + i"
          class="bcd-line"
          :class="{ 'bcd-val': ln.val, 'bcd-rule': ln.rule }"
        >
          <img :src="eqUrl(ln.name)" :style="eqStyle(ln.name, ln.k)" alt="" />
        </span>
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { mediaUrl } from '../config/media'
import { CH2_BC_EQ } from '../config/ch2BcEqs'
import { BC_KEYS, type BcKey } from '../config/simBcGeo'

const props = defineProps<{
  active: boolean
  model: 'viscous' | 'elastic'
  focus: BcKey | null
  lakeId: string
}>()
const emit = defineEmits<{ focus: [key: BcKey | null]; hover: [key: BcKey | null] }>()

const NAMES: Record<BcKey, string> = {
  surface: 'Surface',
  inflow: 'Inflow',
  outflow: 'Outflow',
  lat0: 'Lateral',
  lat1: 'Lateral',
  bed: 'Bed',
}
const LOC: Record<BcKey, string> = {
  surface: 'loc_zs',
  inflow: 'loc_x0',
  outflow: 'loc_xL',
  lat0: 'loc_y0',
  lat1: 'loc_yL',
  bed: 'loc_zb',
}

// px per bp for the TeX images
// (projector legibility: ×~1.2 — a 10 pt condition now ~17 px at 1440)
const EQ_K = 1.7 // conditions
const BIG_K = 1.8 // conditions on the open card
const VAL_K = 1.6 // this lake's values
const LOC_K = 1.4 // the x = 0 / z = z_b tags

interface Line { name: string; k: number; val?: boolean; rule?: boolean }

/** The card's lines: compact (overview) or open (focused). */
function linesFor(key: BcKey, open: boolean): Line[] {
  const v = props.model === 'viscous'
  const id = props.lakeId
  const L = (name: string, k = open ? BIG_K : EQ_K): Line => ({ name, k })
  const V = (name: string, rule = false): Line => ({ name, k: VAL_K, val: true, rule })
  switch (key) {
    case 'surface':
      return [L('surface')]
    case 'lat0':
    case 'lat1':
      return open ? [L('lateral'), L('lateral_tan')] : [L('lateral')]
    case 'inflow':
    case 'outflow': {
      const io = key === 'inflow' ? 'in' : 'out'
      if (!open) return [L(v ? 'v_wall' : 'e_wall')]
      return v
        ? [L('v_wall'), L('v_wall_full'), L('wall_tan'),
          V(`vals_alpha_${id}`, true), V(`vals_cb_${id}`), V('vals_n'), V(`vals_vu_${io}_${id}`)]
        : [L('e_wall'), L('wall_tan'),
          V(`vals_alpha_${id}`, true), V('vals_E'), V(`vals_eu_${io}_${id}`)]
    }
    case 'bed':
      if (!open) return v ? [L('v_bed'), L('v_patch')] : [L('e_bed'), L('e_patch')]
      return v
        ? [L('v_bed_n'), L('v_bed'), L('v_bed_cb'), V(`vals_cb_${id}`, true), V('vals_n'), V('vals_R')]
        : [L('e_bed'), L('e_patch'), V(`vals_pw_${id}`, true), V(`vals_pc_${id}`), V('vals_R')]
  }
}

function eqUrl(name: string): string {
  return mediaUrl(`ch02/bc2/${name}.svg`)
}
function eqStyle(name: string, k: number): Record<string, string> {
  const b = CH2_BC_EQ[name]
  if (!b) return { display: 'none' }
  return { width: `${b.w * k}px`, height: `${b.h * k}px` }
}

// Card box model (must match the CSS below).
const PAD_X = 16
const PAD_TOP = 10
const PAD_BOT = 11
const HEAD_H = 20
const GAP = 5
const RULE_GAP = 9
function cardSize(key: BcKey, lines: Line[]): { w: number; h: number } {
  let w = 0
  let h = PAD_TOP + HEAD_H + PAD_BOT
  const loc = CH2_BC_EQ[LOC[key]]
  w = Math.max(w, 84 + (loc ? loc.w * LOC_K : 0) + 30)
  for (const ln of lines) {
    const b = CH2_BC_EQ[ln.name]
    if (!b) continue
    w = Math.max(w, b.w * ln.k)
    h += b.h * ln.k + (ln.rule ? RULE_GAP + GAP : GAP)
  }
  return { w: Math.ceil(w + 2 * PAD_X), h: Math.ceil(h) }
}

// ── per-frame state ──
interface Anchor { x: number; y: number; visible: boolean; face: boolean }
interface Screens {
  focus: BcKey | null
  settled: boolean
  box: { minX: number; minY: number; maxX: number; maxY: number }
  anchors: Record<BcKey, Anchor>
}
const scr = ref<Screens | null>(null)
const vw = ref(window.innerWidth)
const vh = ref(window.innerHeight)
// smoothed card positions + fades
const pos: Record<string, { x: number; y: number; a: number }> = {}
const tick = ref(0)
let raf = 0
let last = performance.now()
function frame(now: number): void {
  const dt = Math.min(0.1, (now - last) / 1000)
  last = now
  scr.value = ((window as any).__simBcScreens as Screens | null) ?? null
  ;(window as any).__simBcActive = props.active
  if (props.active) readObstacles()
  vw.value = window.innerWidth
  vh.value = window.innerHeight
  const k = 1 - Math.exp(-dt * 10)
  for (const t of targets.value) {
    const p = pos[t.key] ?? (pos[t.key] = { x: t.x, y: t.y, a: 0 })
    // a card that was hidden jumps to its spot (no fly-in from nowhere)
    if (p.a < 0.02) {
      p.x = t.x
      p.y = t.y
    } else {
      p.x += (t.x - p.x) * k
      p.y += (t.y - p.y) * k
    }
    p.a += (t.alpha - p.a) * (1 - Math.exp(-dt * 7))
  }
  tick.value++
  raf = requestAnimationFrame(frame)
}
function onKey(e: KeyboardEvent): void {
  if (e.key === 'Escape' && props.active && props.focus) emit('focus', null)
}
onMounted(() => {
  raf = requestAnimationFrame(frame)
  window.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  window.removeEventListener('keydown', onKey)
  ;(window as any).__simBcActive = false
})

// Safe area: below the ribbon + its sub-menu and the Back/Next pills,
// clear of the bottom-left BC pill and the bottom-right model cards.
const TOP_SAFE = 116
const BOTTOM_SAFE = 96
const DOCK_X = 22

// Other figure furniture the cards must never cover — measured live:
// the stress legend, the floating face grid, and anything that opts in
// with a data-ui-obstacle attribute (e.g. the bottom-right model cards).
const OBSTACLE_SEL =
  '.bsl-card:not(.bsl-hidden), .idl-card:not(.idl-hidden), .svc, .sbk-row, [data-ui-obstacle]'
interface Rect { x: number; y: number; w: number; h: number }
const obstacles = ref<Rect[]>([])
/** Bottom of the ribbon's sub-menu + the Back/Next pills (measured). */
const topSafe = ref(TOP_SAFE)
function readObstacles(): void {
  let b = 0
  for (const sel of ['.landmarks', '.beat-nav']) {
    const r = document.querySelector(sel)?.getBoundingClientRect()
    if (r && r.height > 0) b = Math.max(b, r.bottom)
  }
  topSafe.value = Math.max(TOP_SAFE - 20, (b || TOP_SAFE - 20) + 22)
  const out: Rect[] = []
  document.querySelectorAll(OBSTACLE_SEL).forEach((el) => {
    const r = (el as HTMLElement).getBoundingClientRect()
    const op = parseFloat(getComputedStyle(el as HTMLElement).opacity || '1')
    if (r.width > 0 && r.height > 0 && op > 0.05) out.push({ x: r.left, y: r.top, w: r.width, h: r.height })
  })
  obstacles.value = out
}
const hits = (a: Rect, b: Rect, pad = 10): boolean =>
  a.x < b.x + b.w + pad && b.x < a.x + a.w + pad && a.y < b.y + b.h + pad && b.y < a.y + a.h + pad

interface Target {
  key: BcKey
  x: number
  y: number
  w: number
  h: number
  alpha: number
  lines: Line[]
  loc: string
}

const targets = computed<Target[]>(() => {
  void tick.value
  const s = scr.value
  const W = vw.value
  const H = vh.value
  const f = props.focus
  const out: Target[] = []
  if (f) {
    // ── docked column: the open card in its place in the list ──
    let y = topSafe.value + 4
    for (const key of BC_KEYS) {
      const open = key === f
      const lines = open ? linesFor(key, true) : []
      const sz = cardSize(key, lines)
      // start below any furniture in the column (the stress legend)
      for (const o of obstacles.value) {
        if (hits({ x: DOCK_X, y, w: sz.w, h: sz.h }, o)) y = o.y + o.h + 12
      }
      out.push({ key, x: DOCK_X, y, w: sz.w, h: sz.h, alpha: 1, lines, loc: LOC[key] })
      y += sz.h + 8
    }
    return out
  }
  // ── overview: each card beside its boundary, sides by direction ──
  if (!s) return []
  const box = s.box
  const cx = (box.minX + box.maxX) / 2
  const cy = (box.minY + box.maxY) / 2
  const show = s.settled ? 1 : 0
  type Side = 'left' | 'right' | 'top' | 'bottom'
  const items: Array<Target & { side: Side; ax: number; ay: number }> = []
  for (const key of BC_KEYS) {
    const a = s.anchors[key]
    if (!a) continue
    const lines = linesFor(key, false)
    const sz = cardSize(key, lines)
    let side: Side
    if (key === 'surface') side = 'top'
    else if (key === 'bed') side = 'bottom'
    else {
      const dx = (a.x - cx) / Math.max(1, box.maxX - box.minX)
      const dy = (a.y - cy) / Math.max(1, box.maxY - box.minY)
      side = Math.abs(dx) >= Math.abs(dy) * 0.9 ? (dx < 0 ? 'left' : 'right') : dy < 0 ? 'top' : 'bottom'
    }
    items.push({ key, x: 0, y: 0, w: sz.w, h: sz.h, alpha: show, lines, loc: LOC[key], side, ax: a.x, ay: a.y })
  }
  const G = 26
  // initial spots
  for (const it of items) {
    if (it.side === 'left') { it.x = box.minX - G - it.w; it.y = it.ay - it.h / 2 }
    if (it.side === 'right') { it.x = box.maxX + G; it.y = it.ay - it.h / 2 }
    if (it.side === 'top') { it.x = it.ax - it.w / 2; it.y = box.minY - G - it.h }
    if (it.side === 'bottom') { it.x = it.ax - it.w / 2; it.y = box.maxY + G }
  }
  // clamp into the safe area, then step off any furniture — side cards
  // along their side (left/right: down; top/bottom: sideways)
  const clamp = (it: Target & { side: Side }) => {
    it.x = Math.max(16, Math.min(W - 16 - it.w, it.x))
    it.y = Math.max(topSafe.value, Math.min(H - BOTTOM_SAFE - it.h, it.y))
    for (const o of obstacles.value) {
      if (!hits(it, o)) continue
      if (it.side === 'left' || it.side === 'right') {
        const below = o.y + o.h + 12
        it.y = below + it.h <= H - BOTTOM_SAFE ? below : o.y - 12 - it.h
      } else if (it.side === 'top' && o.y + o.h + 12 + it.h <= box.minY + 0.1 * (box.maxY - box.minY)) {
        // a top card that meets the tier row drops just
        // under it, over the ghost frame's empty top, while that keeps it
        // off the block — rather than sliding far along the row
        it.y = o.y + o.h + 12
      } else {
        const right = o.x + o.w + 12
        it.x = right + it.w <= W - 16 ? right : o.x - 12 - it.w
      }
    }
  }
  items.forEach(clamp)
  // de-overlap: side cards slide along their side only — left/right
  // ones vertically, top/bottom ones horizontally — so none drifts
  // over the object
  const vert = (it: { side: Side }) => it.side === 'left' || it.side === 'right'
  for (let iter = 0; iter < 60; iter++) {
    let moved = false
    for (let i = 0; i < items.length; i++) {
      for (let j = i + 1; j < items.length; j++) {
        const a = items[i]
        const b = items[j]
        const ox = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x)
        const oy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y)
        if (ox <= -10 || oy <= -10) continue
        moved = true
        for (const [p, q] of [[a, b], [b, a]] as const) {
          if (vert(p)) {
            const d = (oy + 12) / 2
            p.y += p.y + p.h / 2 < q.y + q.h / 2 ? -d : d
          } else {
            const d = (ox + 12) / 2
            p.x += p.x + p.w / 2 < q.x + q.w / 2 ? -d : d
          }
        }
        clamp(a)
        clamp(b)
      }
    }
    if (!moved) break
  }
  return items
})

interface Laid extends Target {
  lead: { x1: number; y1: number; x2: number; y2: number } | null
}
const leadAlpha = computed(() => (scr.value?.settled ? 1 : 0))
const laid = computed<Laid[]>(() => {
  const s = scr.value
  return targets.value.map((t) => {
    const p = pos[t.key] ?? { x: t.x, y: t.y, a: 0 }
    const x = p.x
    const y = p.y
    const a = s?.anchors[t.key]
    let lead: Laid['lead'] = null
    const showLead = !!a && a.visible && (!props.focus || t.key === props.focus)
    if (showLead && a) {
      // from the nearest point on the card's border
      const x1 = Math.max(x, Math.min(x + t.w, a.x))
      const y1 = Math.max(y, Math.min(y + t.h, a.y))
      const inside = x1 === a.x && y1 === a.y
      if (!inside) lead = { x1, y1, x2: a.x, y2: a.y }
    }
    return { ...t, x, y, alpha: p.a, lead }
  })
})

// Warm every card image for this lake + model the moment BC mode is up
// (an open card otherwise shows its frame a beat before its TeX).
const warmed = new Set<string>()
watch(
  () => [props.active, props.model, props.lakeId] as const,
  ([on]) => {
    if (!on) return
    for (const key of BC_KEYS) {
      for (const open of [false, true]) {
        for (const ln of [{ name: LOC[key] }, ...linesFor(key, open)]) {
          if (warmed.has(ln.name)) continue
          warmed.add(ln.name)
          const img = new Image()
          img.src = eqUrl(ln.name)
        }
      }
    }
  },
  { immediate: true },
)

function onClick(key: BcKey): void {
  emit('focus', props.focus === key ? null : key)
}
</script>

<style scoped>
.bcd-root {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 11;
}

.bcd-leaders {
  position: absolute;
  inset: 0;
  overflow: visible;
}

.bcd-lead {
  stroke: rgba(245, 199, 94, 0.8);
  stroke-width: 1.6;
  transition: opacity 0.4s;
}
.bcd-lead-on { stroke: rgba(245, 199, 94, 0.95); stroke-width: 2; }

.bcd-dot { fill: rgba(245, 199, 94, 0.9); transition: opacity 0.4s; }
.bcd-dot-on { fill: #f5c75e; }

.bcd-card {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0;
  padding: 10px 16px 11px;
  box-sizing: border-box;
  text-align: left;
  background: rgba(10, 9, 8, 0.86);
  border: 1.5px solid rgba(245, 199, 94, 0.55);
  border-radius: 10px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.55);
  font-family: 'Inter', system-ui, sans-serif;
  color: inherit;
  cursor: pointer;
  pointer-events: auto;
  transition: border-color 0.25s, box-shadow 0.25s, background 0.25s, transform 0.25s;
}
.bcd-card:hover {
  border-color: rgba(245, 199, 94, 0.75);
  background: rgba(24, 19, 11, 0.92);
}

.bcd-on {
  border-color: #f5c75e;
  background: rgba(22, 17, 9, 0.94);
  box-shadow:
    0 10px 36px rgba(0, 0, 0, 0.6),
    0 0 26px rgba(245, 199, 94, 0.28);
  transform: translateY(-2px);
}

.bcd-docked {
  padding-top: 6px;
  padding-bottom: 6px;
  border-color: rgba(245, 199, 94, 0.4);
  background: rgba(10, 9, 8, 0.8);
}

.bcd-head {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 20px;
  width: 100%;
}

.bcd-kicker {
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(245, 199, 94, 0.95);
  white-space: nowrap;
}

.bcd-loc { display: block; opacity: 0.85; }

.bcd-x {
  margin-left: auto;
  font-size: 0.95rem;
  line-height: 1;
  color: rgba(245, 199, 94, 0.85);
}

.bcd-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.bcd-line {
  display: block;
  margin-top: 5px;
}
.bcd-line img { display: block; }

.bcd-rule {
  margin-top: 9px;
  padding-top: 5px;
  border-top: 1px solid rgba(245, 199, 94, 0.35);
  width: 100%;
}
</style>
