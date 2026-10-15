<!-- Chapter 1 card: the chapter's curve-collapse moment, as the chapter
     draws it (the director liked the feel of an earlier sketch but wanted
     the card to show exactly what the chapter shows later at the
     curve-collapse moment). A miniature of TheoryPanel's stages 4 → 5:
     the SAME 36 Elmer/Ice runs (the δ ≤ 0.3 profile subset) in the same
     fig-4 encoding — colour = h (Okabe-Ito H_COLORS), glyph = α (● 0.1°,
     ◆ 0.5°, ▲ 1.0°), dashed = γ 0.5 — on the same axes (±40 km ·
     ±1100 kPa, then the composite x̂ axis with the patch zone and
     τ̄ₓₓ / [τ]), the gold master curve, the scales + master equations
     top-left. (The legend stays in the chapter: at card size its text
     would be ~6 px and its box would cover the downstream tail.) The
     card's title sits in the collapsed figure's empty lower-left, so the
     negative y ticks keep their marks but not their numbers. The motion
     is the chapter's own: the dimensional ensemble holds, collapses
     (1.7 s, cubic), the master and its equations land (0.6 s, starting
     1.75 s in), and the figure then RESTS on the collapse (9 s); it
     eases back to kPa and km (0.8 s, the chapter's back-step) and plays
     again. Data:
     menu/ch01/collapse_thumb.json (cinematic/scene_menu/
     build_menu_thumbs.py, bake_ch01_collapse). -->
<template>
  <div class="jog-stage">
    <canvas ref="canvas" class="jog-canvas" />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { mediaUrl } from '../../config/media'

defineProps<{ playing?: boolean; lit?: boolean }>()
const canvas = ref<HTMLCanvasElement | null>(null)

// TheoryPanel's palette, marker rule and composite axis, copied so the
// card and the chapter cannot drift apart.
const H_COLORS: Record<number, string> = {
  300: '#e69f00',
  1000: '#56b4e9',
  2000: '#f0e442',
  3000: '#7bd8b4',
}
const MASTER_GOLD = '#f5c75e'
const HALF_KM = 40
const ND_TAU_MAX = 1.35
const ZONE_UP_F = 0.4
const ZONE_MID_F = 0.24
const X_TICKS_KM = [-40, -30, -20, -10, 0, 10, 20, 30, 40]
const ND_UP_TICKS = [-6, -4, -2]
const ND_DN_TICKS = [2, 4, 6]

// The chapter's timings (TheoryPanel.applyStage): collapse 1700 ms
// cubic, master 600 ms starting 1750 ms in; back-step 800 ms.
const HOLD_DIM_MS = 2600
const COLLAPSE_MS = 1700
const MASTER_DELAY_MS = 1750
const MASTER_MS = 600
const HOLD_ND_MS = 9000
const BACK_MS = 800
const T_COLLAPSE = HOLD_DIM_MS
const T_MASTER = T_COLLAPSE + MASTER_DELAY_MS
const T_BACK = T_MASTER + MASTER_MS + HOLD_ND_MS
const PERIOD_MS = T_BACK + BACK_MS
const FIRST_HOLD_MS = 1400 // the first collapse comes soon after mount

interface Run { h: number; a: number; g: number; l: number; xs: number; ts: number; x: number[]; t: number[]; m: number[] }
interface Master { xhat_up: number[]; tauhat_up: number[]; xfrac_patch: number[]; tauhat_patch: number[]; xhat_dn: number[]; tauhat_dn: number[] }
// A point in both frames, as fractions: u across the plot (0..1),
// v up from the zero line in half-heights (−1..1 fills the box).
interface Pt { ud: number; vd: number; un: number; vn: number }
interface Curve { color: string; dashed: boolean; alpha: number; pts: Pt[]; marks: number[] }

function uNd(zone: 0 | 1 | 2, v: number): number {
  if (zone === 0) return ((v + 6) / 6) * ZONE_UP_F
  if (zone === 1) return ZONE_UP_F + v * ZONE_MID_F
  return ZONE_UP_F + ZONE_MID_F + (v / 6) * (1 - ZONE_UP_F - ZONE_MID_F)
}

let ymaxKpa = 1100
function toCurve(r: Run): Curve {
  const half = r.l / 2
  const pts: Pt[] = r.x.map((xk, i) => {
    const xm = xk * 1e3
    const tau = r.t[i]
    let u: number
    if (xm < -half) u = uNd(0, Math.max(-7.5, (xm + half) / r.xs))
    else if (xm <= half) u = uNd(1, (xm + half) / r.l)
    else u = uNd(2, Math.min(7.5, (xm - half) / r.xs))
    return { ud: (xk + HALF_KM) / (2 * HALF_KM), vd: tau / ymaxKpa, un: u, vn: tau / r.ts / ND_TAU_MAX }
  })
  return { color: H_COLORS[r.h] ?? '#cccccc', dashed: r.g === 0.5, alpha: r.a, pts, marks: r.m }
}

function masterPoints(m: Master): { u: number; v: number }[] {
  const out: { u: number; v: number }[] = []
  m.xhat_up.forEach((x, i) => out.push({ u: uNd(0, x), v: m.tauhat_up[i] / ND_TAU_MAX }))
  m.xfrac_patch.forEach((f, i) => out.push({ u: uNd(1, f), v: m.tauhat_patch[i] / ND_TAU_MAX }))
  m.xhat_dn.forEach((x, i) => out.push({ u: uNd(2, x), v: m.tauhat_dn[i] / ND_TAU_MAX }))
  return out
}

// TheoryPanel.markerPathAt, on a canvas.
function glyph(ctx: CanvasRenderingContext2D, x: number, y: number, alpha: number, s: number): void {
  ctx.beginPath()
  if (alpha === 0.1) ctx.arc(x, y, s, 0, 2 * Math.PI)
  else if (alpha === 0.5) { ctx.moveTo(x, y - s); ctx.lineTo(x + s, y); ctx.lineTo(x, y + s); ctx.lineTo(x - s, y); ctx.closePath() }
  else { ctx.moveTo(x, y - s); ctx.lineTo(x + s, y + s); ctx.lineTo(x - s, y + s); ctx.closePath() }
}

function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}
const clamp01 = (v: number) => Math.min(1, Math.max(0, v))

/** Collapse + master opacity at time t into the loop. */
function phaseAt(t: number): { c: number; m: number } {
  const p = ((t % PERIOD_MS) + PERIOD_MS) % PERIOD_MS
  if (p >= T_BACK) {
    const k = 1 - easeInOutCubic(clamp01((p - T_BACK) / BACK_MS))
    return { c: k, m: k }
  }
  return {
    c: easeInOutCubic(clamp01((p - T_COLLAPSE) / COLLAPSE_MS)),
    m: easeInOutCubic(clamp01((p - T_MASTER) / MASTER_MS)),
  }
}

let curves: Curve[] = []
let master: { u: number; v: number }[] = []
let eqScales: HTMLImageElement | null = null
let eqMaster: HTMLImageElement | null = null
let ctx: CanvasRenderingContext2D | null = null
let rafId = 0
let t0 = 0
let ro: ResizeObserver | null = null
let cw = 2
let ch = 2
let dirty = true
let lastKey = ''
let dead = false

function setSize() {
  const c = canvas.value
  if (!c) return
  const r = c.getBoundingClientRect()
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  cw = Math.max(2, r.width)
  ch = Math.max(2, r.height)
  c.width = Math.round(cw * dpr)
  c.height = Math.round(ch * dpr)
  ctx?.setTransform(dpr, 0, 0, dpr, 0, 0)
  dirty = true
}

function paint(c: number, mA: number) {
  if (!ctx) return
  const g = ctx
  g.clearRect(0, 0, cw, ch)

  // Plot box: the chapter's frame, stretched to the card. Left margin
  // holds the y ticks + axis name; the card's title rides the empty
  // lower-left of the collapsed figure, as the legend does in the
  // chapter's log-log stage.
  const x0 = 44
  const x1 = cw - 10
  const yTop = 8
  const yBot = ch - 9
  const pw = x1 - x0
  const half = (yBot - yTop) / 2
  const yMid = yTop + half
  const X = (u: number) => x0 + u * pw
  const Y = (v: number) => yMid - v * half
  const s = pw / 1490 // chapter units → card px, horizontally

  // frame + zero line
  g.lineWidth = 1
  g.setLineDash([])
  g.strokeStyle = 'rgba(245,245,245,0.35)'
  g.strokeRect(x0 + 0.5, yTop + 0.5, pw - 1, yBot - yTop - 1)
  g.strokeStyle = 'rgba(245,245,245,0.25)'
  g.beginPath()
  g.moveTo(x0, Math.round(yMid) + 0.5)
  g.lineTo(x1, Math.round(yMid) + 0.5)
  g.stroke()

  g.font = '400 8.5px Inter, system-ui, sans-serif'
  g.textBaseline = 'middle'

  // dimensional axes (fade out on collapse)
  const aD = 1 - c
  if (aD > 0.004) {
    g.globalAlpha = aD
    g.strokeStyle = 'rgba(245,245,245,0.5)'
    g.fillStyle = 'rgba(245,245,245,0.72)'
    g.textAlign = 'right'
    g.beginPath()
    for (const k of [-800, -400, 0, 400, 800]) {
      const y = Math.round(Y(k / ymaxKpa)) + 0.5
      g.moveTo(x0 - 3, y)
      g.lineTo(x0, y)
    }
    g.stroke()
    for (const k of [0, 800]) g.fillText(String(k), x0 - 5, Y(k / ymaxKpa))
    g.beginPath()
    for (const k of X_TICKS_KM) {
      const x = Math.round(X((k + HALF_KM) / (2 * HALF_KM))) + 0.5
      g.moveTo(x, yBot)
      g.lineTo(x, yBot - 3)
    }
    g.stroke()
    g.fillStyle = 'rgba(245,245,245,0.6)'
    g.save()
    g.translate(9, yMid)
    g.rotate(-Math.PI / 2)
    g.textAlign = 'center'
    g.fillText('τ̄ₓₓ [kPa]', 0, 0)
    g.restore()
  }

  // non-dimensional composite axis (fades in with the collapse)
  if (c > 0.004) {
    g.globalAlpha = c
    g.strokeStyle = 'rgba(245,245,245,0.20)'
    g.setLineDash([2, 3])
    g.beginPath()
    for (const u of [ZONE_UP_F, ZONE_UP_F + ZONE_MID_F]) {
      const x = Math.round(X(u)) + 0.5
      g.moveTo(x, yTop)
      g.lineTo(x, yBot)
    }
    g.stroke()
    g.setLineDash([])
    g.strokeStyle = 'rgba(245,245,245,0.5)'
    g.fillStyle = 'rgba(245,245,245,0.72)'
    g.textAlign = 'right'
    g.beginPath()
    for (const k of [-1, 0, 1]) {
      const y = Math.round(Y(k / ND_TAU_MAX)) + 0.5
      g.moveTo(x0 - 3, y)
      g.lineTo(x0, y)
    }
    g.stroke()
    for (const k of [0, 1]) g.fillText(String(k), x0 - 5, Y(k / ND_TAU_MAX))
    g.beginPath()
    for (const u of [...ND_UP_TICKS.map((t) => uNd(0, t)), uNd(1, 0.5), ...ND_DN_TICKS.map((t) => uNd(2, t))]) {
      const x = Math.round(X(u)) + 0.5
      g.moveTo(x, yBot)
      g.lineTo(x, yBot - 3)
    }
    g.stroke()
    g.fillStyle = 'rgba(245,245,245,0.6)'
    g.save()
    g.translate(9, yMid)
    g.rotate(-Math.PI / 2)
    g.textAlign = 'center'
    g.fillText('τ̄ₓₓ / [τ]', 0, 0)
    g.restore()
  }
  g.globalAlpha = 1

  // Scales + master equations — land with the master (chapter: top-left,
  // FX + 40, widths 520 and 400 units).
  if (mA > 0.004) {
    g.globalAlpha = mA
    const ex = x0 + 40 * s
    if (eqScales?.complete && eqScales.naturalWidth) {
      const w = 520 * s
      g.drawImage(eqScales, ex, yTop + 4, w, w / 8.43)
    }
    if (eqMaster?.complete && eqMaster.naturalWidth) {
      const w = 400 * s
      g.drawImage(eqMaster, ex, yTop + 6 + (520 * s) / 8.43, w, w / 6.88)
    }
    g.globalAlpha = 1
  }

  // Clip to the plot box (the chapter's tp-curveclip).
  g.save()
  g.beginPath()
  g.rect(x0, yTop, pw, yBot - yTop)
  g.clip()

  // The ensemble: colour = h, dashed = γ 0.5, glyph = α.
  const lw = Math.max(0.9, 2.2 * s)
  const dash = [8 * s, 6 * s]
  const gs = Math.max(2, 6 * s)
  const at = (p: Pt) => ({ x: X(p.ud + (p.un - p.ud) * c), y: Y(p.vd + (p.vn - p.vd) * c) })
  g.lineJoin = 'round'
  g.globalAlpha = 0.85
  for (const cv of curves) {
    g.strokeStyle = cv.color
    g.lineWidth = lw
    g.setLineDash(cv.dashed ? dash : [])
    g.beginPath()
    cv.pts.forEach((p, i) => {
      const q = at(p)
      if (i === 0) g.moveTo(q.x, q.y)
      else g.lineTo(q.x, q.y)
    })
    g.stroke()
    g.setLineDash([])
    g.fillStyle = cv.color
    g.strokeStyle = 'rgba(0,0,0,0.5)'
    g.lineWidth = 0.5
    for (const i of cv.marks) {
      const q = at(cv.pts[i])
      glyph(g, q.x, q.y, cv.alpha, gs)
      g.globalAlpha = 0.85 * 0.9
      g.fill()
      g.globalAlpha = 0.85
      g.stroke()
    }
  }

  // The master curve (n = 1: exp / linear / −exp), gold, on top.
  if (mA > 0.004 && master.length) {
    g.globalAlpha = mA
    g.strokeStyle = MASTER_GOLD
    g.lineWidth = Math.max(1.6, 4.5 * s)
    g.beginPath()
    master.forEach((p, i) => {
      if (i === 0) g.moveTo(X(p.u), Y(p.v))
      else g.lineTo(X(p.u), Y(p.v))
    })
    g.stroke()
  }
  g.restore()
  g.globalAlpha = 1
}

function frame(now: number) {
  rafId = requestAnimationFrame(frame)
  const { c, m } = phaseAt(now - t0)
  const key = `${c.toFixed(4)}|${m.toFixed(4)}`
  if (!dirty && key === lastKey) return
  dirty = false
  lastKey = key
  paint(c, m)
}

function loadEq(name: string): HTMLImageElement {
  const img = new Image()
  img.onload = () => { dirty = true }
  img.src = mediaUrl(`ch01/eq/${name}.svg`)
  return img
}

onMounted(() => {
  const c = canvas.value
  if (!c) return
  ctx = c.getContext('2d')
  setSize()
  ro = new ResizeObserver(setSize)
  ro.observe(c)
  // Start just inside the dimensional hold so the first collapse plays
  // shortly after the menu arrives.
  t0 = performance.now() - (HOLD_DIM_MS - FIRST_HOLD_MS)
  rafId = requestAnimationFrame(frame)
  eqScales = loadEq('eqn1_scales')
  eqMaster = loadEq('eqn1_master')
  fetch(mediaUrl('menu/ch01/collapse_thumb.json'))
    .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
    .then((d: { ymax_kpa: number; runs: Run[]; master: Master }) => {
      if (dead) return
      ymaxKpa = d.ymax_kpa
      curves = d.runs.map(toCurve)
      master = masterPoints(d.master)
      dirty = true
    })
    .catch((e) => console.warn('[menu] ch1 collapse', e))
})

onBeforeUnmount(() => {
  dead = true
  cancelAnimationFrame(rafId)
  ro?.disconnect()
  ro = null
  ctx = null
})
</script>

<style scoped>
/* TheoryPanel's chalkboard (.tp-backdrop). */
.jog-stage {
  position: absolute;
  inset: 0;
  background: radial-gradient(120% 90% at 30% 20%, #12100c 0%, #0a0908 55%, #060606 100%);
}

.jog-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}
</style>
