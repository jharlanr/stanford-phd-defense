<template>
  <!-- "Greenland flows" (Introduction step 1): five places on the ice
       sheet, each a dot on the surface, a thin stick, and a label = its
       name + its multi-year mean speed (config/flowSites.ts — sampled from
       the field the drape is coloured from). Figure labels only (the
       narrator rule). Positions follow the Globe's projected anchors every
       frame (window.__globeAnchorScreens, the IntroSeasons pattern); the
       layer fades in once the camera has settled on the step. -->
  <div class="fsites" :class="{ on: shown }">
    <svg class="fs-marks" :width="vw" :height="vh" aria-hidden="true">
      <g v-for="s in FLOW_SITES" :key="s.id">
        <polyline :ref="(el) => setRef(`${s.id}:haloLead`, el)" class="fs-lead-halo" />
        <polyline :ref="(el) => setRef(`${s.id}:lead`, el)" class="fs-lead" />
        <circle :ref="(el) => setRef(`${s.id}:dot`, el)" class="fs-dot" :r="dotR" />
      </g>
    </svg>
    <div
      v-for="s in FLOW_SITES"
      :key="s.id"
      :ref="(el) => setRef(`${s.id}:label`, el)"
      class="fs-label"
      :class="s.side === 'W' ? 'fs-w' : 'fs-e'"
      :data-site="s.id"
    >
      <div class="fs-name">{{ s.name }}</div>
      <div class="fs-speed">
        <span class="fs-num">{{ flowSpeedLabel(s.speed) }}</span>
        <span class="fs-unit">m yr<sup>−1</sup></span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { ComponentPublicInstance } from 'vue'
import { FLOW_SITES, GRIS_ENVELOPE, flowSpeedLabel } from '../config/flowSites'

const vw = ref(window.innerWidth)
const vh = ref(window.innerHeight)
/** Marker radius: 3.6 px at 900 px tall, 4.3 at 1080. */
const dotR = computed(() => Math.max(3, Math.min(4.8, vh.value / 250)))
function onResize(): void {
  vw.value = window.innerWidth
  vh.value = window.innerHeight
}

const els = new Map<string, Element>()
function setRef(key: string, el: Element | ComponentPublicInstance | null): void {
  if (el instanceof Element) els.set(key, el)
  else els.delete(key)
}

type Scr = { x: number; y: number; visible: boolean }
type Rect = { l: number; t: number; r: number; b: number }

/** Label ↔ land / other furniture, px. */
const GAP = 18
/** Shortest horizontal reach of a stick (dot → label edge), px. */
const MIN_REACH = 34
/** Between two labels on the same side, px. */
const VGAP = 12
/** Space between a label's edge and its stick's end, px. */
const LEAD_PAD = 8
/** Keep clear of the viewport edges, px. */
const EDGE = 14

// ── fade-in: after the camera has settled on the step ──────────────────
// Shown once the markers have held still for STILL_MS (the flight from
// step 0 is 2.6 s; back from step 2 the camera is already there) and the
// drape's textures are in, never sooner than MIN_MS after the step.
const shown = ref(false)
const STILL_MS = 450
const MIN_MS = 900
const t0 = performance.now()
let stillSince: number | null = null
let last: Record<string, { x: number; y: number }> = {}

// Furniture to keep clear of — re-read a few times a second, not every frame.
let furniture: { cb: Rect | null; top: number; corner: Rect | null } = { cb: null, top: 0, corner: null }
let furnitureAt = -1e9
function rectOf(sel: string): Rect | null {
  const el = document.querySelector(sel)
  if (!el) return null
  const b = el.getBoundingClientRect()
  if (b.width === 0 && b.height === 0) return null
  return { l: b.left, t: b.top, r: b.right, b: b.bottom }
}
function readFurniture(now: number): void {
  if (now - furnitureAt < 300) return
  furnitureAt = now
  const nav = rectOf('.top-nav')
  const sub = rectOf('.landmarks')
  const pills = rectOf('.beat-nav')
  furniture = {
    cb: rectOf('.vcb'),
    top: Math.max(nav?.b ?? 0, sub?.b ?? 0, pills?.b ?? 0),
    corner: rectOf('.corner-link'),
  }
}

/** The land's outermost screen x on `side` between y0 and y1 (the
 *  projected envelope, linearly interpolated at the band's ends). */
function landEdge(scr: Record<string, Scr>, side: 'W' | 'E', y0: number, y1: number): number | null {
  const k = side === 'W' ? 'w' : 'e'
  let edge: number | null = null
  const take = (x: number) => {
    edge = edge === null ? x : side === 'W' ? Math.min(edge, x) : Math.max(edge, x)
  }
  let prev: Scr | null = null
  for (let i = 0; i < GRIS_ENVELOPE.length; i++) {
    const p = scr[`fe:${k}:${i}`]
    if (!p || !p.visible) {
      prev = null
      continue
    }
    if (p.y >= y0 && p.y <= y1) take(p.x)
    if (prev) {
      // A segment crossing either band edge contributes its crossing point.
      for (const yy of [y0, y1]) {
        if ((prev.y - yy) * (p.y - yy) < 0) take(prev.x + ((yy - prev.y) / (p.y - prev.y)) * (p.x - prev.x))
      }
    }
    prev = p
  }
  return edge
}

let raf: number | null = null
function draw(now: number): void {
  raf = window.requestAnimationFrame(draw)
  const scr = (window as any).__globeAnchorScreens as Record<string, Scr> | null
  if (!scr) return
  readFurniture(now)
  const W = vw.value
  const H = vh.value

  // Settled? (all visible markers moved < 0.4 px since the last frame)
  let moved = 0
  for (const s of FLOW_SITES) {
    const p = scr[`fs:${s.id}`]
    if (!p) continue
    const q = last[s.id]
    if (q) moved = Math.max(moved, Math.abs(p.x - q.x), Math.abs(p.y - q.y))
    else moved = Infinity
    last[s.id] = { x: p.x, y: p.y }
  }
  if (moved < 0.4) stillSince ??= now
  else stillSince = null
  const texturesIn = ((window as any).__texturesPending ?? 0) === 0
  if (!shown.value && stillSince !== null && now - stillSince > STILL_MS && now - t0 > MIN_MS && texturesIn) {
    shown.value = true
  }

  // Lay out each side: vertical first (anchor height, then pushed apart
  // and inside the free band), then horizontal (just outside the land).
  for (const side of ['W', 'E'] as const) {
    const items = FLOW_SITES.filter((s) => s.side === side)
      .map((s) => {
        const p = scr[`fs:${s.id}`]
        const lab = els.get(`${s.id}:label`) as HTMLElement | undefined
        const ok = !!p && p.visible && p.x > 0 && p.x < W && p.y > 0 && p.y < H && !!lab
        return { s, p, lab, ok, w: lab?.offsetWidth ?? 0, h: lab?.offsetHeight ?? 0, top: 0, left: 0 }
      })
    for (const it of items) {
      if (!it.ok) {
        for (const k of ['dot', 'lead', 'haloLead']) els.get(`${it.s.id}:${k}`)?.setAttribute('visibility', 'hidden')
        if (it.lab) it.lab.style.visibility = 'hidden'
      }
    }
    const live = items
      .filter((it) => it.ok)
      .map((it) => ({ ...it, p: it.p as Scr, lab: it.lab as HTMLElement }))
      .sort((a, b) => a.p.y - b.p.y)
    if (!live.length) continue
    for (const it of live) it.top = it.p.y - it.h / 2 + it.s.dy * it.h
    const topLim = furniture.top + GAP
    let botLim = H - EDGE
    if (side === 'E' && furniture.corner) botLim = Math.min(botLim, furniture.corner.t - GAP)
    // Forward (push down), then backward (pull up from the bottom), then
    // forward again from the top limit.
    for (let i = 0; i < live.length; i++) {
      const min = i === 0 ? topLim : live[i - 1].top + live[i - 1].h + VGAP
      live[i].top = Math.max(live[i].top, min)
    }
    for (let i = live.length - 1; i >= 0; i--) {
      const max = i === live.length - 1 ? botLim - live[i].h : live[i + 1].top - VGAP - live[i].h
      live[i].top = Math.min(live[i].top, max)
    }
    for (let i = 0; i < live.length; i++) {
      const min = i === 0 ? topLim : live[i - 1].top + live[i - 1].h + VGAP
      live[i].top = Math.max(live[i].top, min)
    }
    for (const it of live) {
      const y0 = it.top - GAP * 0.5
      const y1 = it.top + it.h + GAP * 0.5
      const land = landEdge(scr, side, y0, y1)
      if (side === 'W') {
        const right = Math.min(it.p.x - MIN_REACH, (land ?? it.p.x) - GAP)
        let left = right - it.w
        // The colour bar: never under it — slide right of it instead.
        const cb = furniture.cb
        if (cb && it.top < cb.b + GAP && it.top + it.h > cb.t - GAP && left < cb.r + GAP) left = cb.r + GAP
        if (left < EDGE) left = EDGE
        it.left = left
      } else {
        let left = Math.max(it.p.x + MIN_REACH, (land ?? it.p.x) + GAP)
        if (left + it.w > W - EDGE) left = W - EDGE - it.w
        it.left = left
      }
      const lab = it.lab
      lab.style.transform = `translate(${it.left.toFixed(1)}px, ${it.top.toFixed(1)}px)`
      lab.style.visibility = 'visible'
      // The stick: dot → the label's near edge, at the label's middle.
      const ex = side === 'W' ? it.left + it.w + LEAD_PAD : it.left - LEAD_PAD
      const ey = it.top + it.h / 2
      const pts = `${it.p.x.toFixed(1)},${it.p.y.toFixed(1)} ${ex.toFixed(1)},${ey.toFixed(1)}`
      for (const k of ['lead', 'haloLead']) {
        const el = els.get(`${it.s.id}:${k}`)
        el?.setAttribute('points', pts)
        el?.setAttribute('visibility', 'visible')
      }
      const dot = els.get(`${it.s.id}:dot`)
      dot?.setAttribute('cx', it.p.x.toFixed(1))
      dot?.setAttribute('cy', it.p.y.toFixed(1))
      dot?.setAttribute('visibility', 'visible')
    }
  }
}

onMounted(() => {
  window.addEventListener('resize', onResize)
  raf = window.requestAnimationFrame(draw)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  if (raf !== null) window.cancelAnimationFrame(raf)
  raf = null
  last = {}
})
</script>

<style scoped>
.fsites {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 7;
  color: #f2efe6;
  font-family: 'Inter', system-ui, sans-serif;
}
/* The fade-in lives on the children: the root's opacity belongs to the
   parent's leave transition. */
.fs-marks,
.fs-label {
  opacity: 0;
  transition: opacity 0.9s ease;
}
.fsites.on .fs-marks,
.fsites.on .fs-label {
  opacity: 1;
}

.fs-marks {
  position: absolute;
  inset: 0;
  overflow: visible;
}
/* A dark halo under the cream stick, so it reads over pale interior ice
   and over the black alike. */
.fs-lead-halo {
  fill: none;
  stroke: rgba(0, 0, 0, 0.7);
  stroke-width: 4.6;
  stroke-linecap: round;
}
.fs-lead {
  fill: none;
  stroke: rgba(242, 239, 230, 1);
  stroke-width: 2.2;
  stroke-linecap: round;
}
.fs-dot {
  fill: var(--gold-bright);
  stroke: rgba(0, 0, 0, 0.8);
  stroke-width: 1.6;
}

.fs-label {
  position: absolute;
  left: 0;
  top: 0;
  visibility: hidden;
  white-space: nowrap;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.95), 0 0 12px rgba(0, 0, 0, 0.8);
  will-change: transform;
}
.fs-w {
  text-align: right;
}
.fs-e {
  text-align: left;
}
.fs-name {
  font-size: clamp(0.95rem, 1.2vw, 1.5rem);
  font-weight: 500;
  letter-spacing: 0.02em;
  line-height: 1.15;
  color: #f2efe6;
}
.fs-speed {
  display: flex;
  align-items: baseline;
  gap: 0.3em;
  line-height: 1;
  margin-top: 0.12em;
}
.fs-w .fs-speed {
  justify-content: flex-end;
}
.fs-num {
  font-family: 'EB Garamond', Georgia, serif;
  font-size: clamp(2rem, 2.8vw, 3.4rem);
  font-variant-numeric: lining-nums tabular-nums;
  color: var(--gold-bright);
}
.fs-unit {
  font-size: clamp(0.95rem, 1.15vw, 1.4rem);
  color: rgba(242, 239, 230, 0.95);
}
.fs-unit sup {
  font-size: 0.7em;
}
</style>
