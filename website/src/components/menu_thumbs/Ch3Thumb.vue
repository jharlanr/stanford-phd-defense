<!-- Chapter 3 card: the network itself — the chapter's road map
     (EssdNetworkDiagram) in miniature, with a light walking the forward
     pass. The director wanted more of the architecture and less of an
     image hopping from one stage to the next.

     The diagram's shapes, sizes and palette in its own viewBox units, no
     text: both streams, the five input sheets, the four conv slabs
     (height = resolution, depth = channels), the two recurrent blocks
     with their loops, GAP, the 32- and 16-vectors, the head's 48 → 64 → 5
     wiring and the five class pills. Where the diagram leaves room for
     its labels the miniature closes up (the gaps between blocks, the
     scalar stream lifted under the image stream, pills without their
     codes), so the whole network fits above the card's title.

     One pass per example lake (the chapter's five, 1848 first). The lit
     block walks Sentinel-2 → channels → conv 1–4 → ConvLSTM while p_water
     glides along the scalar stream to its LSTM; both loops then tick
     through the season while the p_water cursor sweeps May → Sep; the
     states pool into their vectors, concatenate, cross the hidden layer,
     and the class pills fill to the checkpoint's season-end softmax; the
     verdict holds, then the warmth recedes right to left, back to
     Sentinel-2, as the next lake arrives. Lit = gold, passed = warm,
     ahead = dim — the docked map's rule. The data
     glyphs are the chapter's own numbers (ch3ThumbData.ts, generated from
     the bake); the only fetches are the five 18 kB lake thumbnails the
     diagram already shows. -->
<template>
  <canvas ref="canvas" class="net-canvas" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { diverging, netUrl, rgbCss } from '../../config/essdNetwork'
import { CLASSES, COLORS, LAKES } from './ch3ThumbData'

defineProps<{ playing?: boolean; lit?: boolean }>()
const canvas = ref<HTMLCanvasElement | null>(null)

// ── geometry (EssdNetworkDiagram's viewBox units) ────────────────────
const YT = 122 // image stream axis, as the diagram
const YB = 240 // scalar stream axis (the diagram's 292, lifted)
const VB = { x: 14, y: 40, w: 1394, h: 250 } // the box fitted to the card
const FRAME = { x: 30, y: YT - 42, s: 84 } // Sentinel-2, front frame
const CHAN_X = 172
const CHAN_COLORS = ['#ff6b5e', '#6be07a', '#6fa0ff', '#d9d3c6', '#f5f0e6']
const CONV = [
  { id: 'conv1', x: 300, w: 12, h: 120, k: 16 },
  { id: 'conv2', x: 390, w: 18, h: 92, k: 15 },
  { id: 'conv3', x: 485, w: 26, h: 66, k: 13 },
  { id: 'conv4', x: 586, w: 36, h: 46, k: 11 },
] as const
const RNN_X = 696 // ConvLSTM and LSTM blocks, 140 × 60
const RNN_W = 140
const GAP_X = 896 // the pooling trapezoid, 42 wide
const VEC_X = 976 // the 32- and 16-vectors
const PW = { x: 30, w: 210 } // p_water box
// the head, between the two streams
const BOX = { x: 1044, y: 80, w: 356, h: 202 }
const CAT_X = 1062
const CAT_Y0 = 94
const CAT_STEP = 3.6
const HID_X = 1162
const HID_Y0 = 93
const HID_STEP = 2.75
const LOGIT_X = 1238
const PILL_X = 1266
const PILL_W = 120
const PILL_H = 21
const OUT_Y = [127, 154, 181, 208, 235]
const Y_CAT_GAP = CAT_Y0 + 16 * CAT_STEP // where the 32 lands
const Y_CAT_SL = CAT_Y0 + 32 * CAT_STEP + 2 + 8 * CAT_STEP // where the 16 lands
const CAT_H = 48 * CAT_STEP + 2
// The diagram's representative fans (12 of the 3,072 concat → hidden
// weights; 5 hidden → each logit), its y's mapped onto this head.
function remapHead(y: number): number {
  return CAT_Y0 + ((y - 106) / (309 - 106)) * CAT_H
}
const FAN1 = ([
  [110, 106], [140, 150], [170, 128], [196, 196], [220, 172], [236, 240],
  [260, 214], [284, 262], [300, 306], [126, 236], [250, 130], [180, 290],
] as [number, number][]).map(([a, b]) => [remapHead(a), remapHead(b)] as [number, number])
const FAN2: [number, number][] = []
for (const y1 of [110, 160, 210, 260, 305]) for (const y2 of OUT_Y) FAN2.push([remapHead(y1), y2])

type P2 = [number, number]
type Path = (u: number) => P2
function line(x0: number, y0: number, x1: number, y1: number): Path {
  return (u) => [x0 + (x1 - x0) * u, y0 + (y1 - y0) * u]
}
function cubic(a: P2, b: P2, c: P2, d: P2): Path {
  return (u) => {
    const v = 1 - u
    const A = v * v * v, B = 3 * v * v * u, C = 3 * v * u * u, D = u * u * u
    return [A * a[0] + B * b[0] + C * c[0] + D * d[0], A * a[1] + B * b[1] + C * c[1] + D * d[1]]
  }
}
/** The diagram's loop over a recurrent block whose top edge is at y. */
function loopOver(y: number): Path {
  return cubic([RNN_X + 114, y], [RNN_X + 116, y - 38], [RNN_X + 24, y - 38], [RNN_X + 26, y - 2])
}
const LOOP_T = loopOver(YT - 30)
const LOOP_B = loopOver(YB - 30)
const slabRight = (b: (typeof CONV)[number]) => b.x + b.w + b.k

// ── the pass (seconds) ───────────────────────────────────────────────
const PERIOD = 12
const R0 = 3.5 // the recurrent blocks tick through the season …
const R1 = 5.4 // … until here
const ORBIT = 0.475 // one loop round (four per season)
// The verdict holds until RECEDE0; then the warmth recedes, softmax
// first, back to Sentinel-2 (RECEDE_SPREAD later), each block cooling
// over RECEDE_LEN, while the next lake arrives.
const RECEDE0 = 10.3
const RECEDE_SPREAD = 1.0
const RECEDE_LEN = 0.6
const ARRIVE: Record<string, number> = {
  input: 0.4, pwater: 0.4,
  chan: 0.9, conv1: 1.4, conv2: 1.9, conv3: 2.4, conv4: 2.9,
  clstm: 3.4, slstm: 3.4,
  gap: 5.85, v32: 6.25, v16: 6.25,
  concat: 6.9, fc: 7.5, out: 8.1,
}
const DWELL: Record<string, number> = {
  input: 0.3, pwater: 0.3, clstm: R1 - 3.4, slstm: R1 - 3.4, out: RECEDE0 - 8.1,
}
// Each block's centre along the network (units), for the recession.
const NODE_X: Record<string, number> = {
  input: 72, pwater: 135, chan: 200, conv1: 306, conv2: 399, conv3: 498, conv4: 604,
  clstm: 766, slstm: 766, gap: 917, v32: 983, v16: 983, concat: 1069, fc: 1169, out: 1320,
}
interface Edge { to: string; path: Path; t0: number }
const EDGES: Edge[] = [
  { to: 'chan', path: line(144, YT, 164, YT), t0: 0.55 },
  { to: 'conv1', path: line(250, YT, CONV[0].x - 4, YT), t0: 0.95 },
  { to: 'conv2', path: line(slabRight(CONV[0]) + 2, YT, CONV[1].x - 4, YT), t0: 1.45 },
  { to: 'conv3', path: line(slabRight(CONV[1]) + 2, YT, CONV[2].x - 4, YT), t0: 1.95 },
  { to: 'conv4', path: line(slabRight(CONV[2]) + 2, YT, CONV[3].x - 4, YT), t0: 2.45 },
  { to: 'clstm', path: line(slabRight(CONV[3]) + 2, YT, RNN_X - 4, YT), t0: 2.95 },
  { to: 'slstm', path: line(PW.x + PW.w + 2, YB, RNN_X - 4, YB), t0: 0.6 },
  { to: 'gap', path: line(RNN_X + RNN_W, YT, GAP_X - 4, YT), t0: R1 },
  { to: 'v32', path: line(GAP_X + 42, YT, VEC_X - 4, YT), t0: 5.9 },
  { to: 'v16', path: line(RNN_X + RNN_W, YB, VEC_X - 4, YB), t0: R1 },
  { to: 'concat', path: cubic([VEC_X + 16, YT], [VEC_X + 50, YT], [CAT_X - 38, Y_CAT_GAP], [CAT_X - 4, Y_CAT_GAP]), t0: 6.45 },
  { to: 'concat', path: cubic([VEC_X + 16, YB], [VEC_X + 50, YB], [CAT_X - 38, Y_CAT_SL], [CAT_X - 4, Y_CAT_SL]), t0: 6.45 },
]

// ── palette (the diagram's) ──────────────────────────────────────────
type RGBA = [number, number, number, number]
const GOLD: RGBA = [244, 207, 106, 1]
const GOLD_CSS = 'rgb(244, 207, 106)'
const GOLD_GLOW = 'rgba(244, 207, 106, 0.9)'
const LINE: RGBA = [245, 240, 230, 0.58]
const LINE_SOFT: RGBA = [245, 240, 230, 0.46]
const EDGE = 'rgba(245, 240, 230, 0.44)'
const ARROW = 'rgba(245, 240, 230, 0.6)'
const BLOCK: RGBA = [28, 25, 20, 0.95]
const BLOCK_LIT: RGBA = [64, 50, 20, 0.95]
const PRISM: RGBA = [42, 37, 29, 0.98]
const PRISM_LIT: RGBA = [96, 74, 26, 0.98]
const PRISM_TOP: RGBA = [92, 82, 64, 0.9]
const PRISM_TOP_LIT: RGBA = [150, 120, 50, 0.95]
const PRISM_SIDE: RGBA = [60, 53, 42, 0.95]
const PRISM_SIDE_LIT: RGBA = [110, 86, 34, 0.97]
const CELL_OFF = 'rgba(245, 240, 230, 0.22)'
const AHEAD = 0.5 // opacity of what the light has not reached
const WARM = 0.9 // … and of what it has passed
const WARM_TINT = 0.3 // how gold a passed block stays

function mix(a: RGBA, b: RGBA, t: number): string {
  const k = Math.max(0, Math.min(1, t))
  const c = (i: number) => a[i] + (b[i] - a[i]) * k
  return `rgba(${c(0) | 0},${c(1) | 0},${c(2) | 0},${c(3).toFixed(3)})`
}
function smooth(u: number): number {
  const x = Math.min(1, Math.max(0, u))
  return x * x * (3 - 2 * x)
}
function hexA(hex: string, a: number): string {
  const n = parseInt(hex.slice(1), 16)
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`
}

// ── state ────────────────────────────────────────────────────────────
let ctx: CanvasRenderingContext2D | null = null
let rafId = 0
let t0 = 0
let ro: ResizeObserver | null = null
let cw = 2
let ch = 2
let dpr = 1
const thumbs: (HTMLImageElement | null)[] = LAKES.map(() => null)

function setSize() {
  const c = canvas.value
  if (!c) return
  const r = c.getBoundingClientRect()
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  cw = Math.max(2, r.width)
  ch = Math.max(2, r.height)
  c.width = Math.round(cw * dpr)
  c.height = Math.round(ch * dpr)
}

let q = 0 // seconds into the current pass
let s = 1 // px per unit
/** 1 → 0 as the warmth recedes past a block. */
function coolOf(id: string): number {
  const start = RECEDE0 + (1 - (NODE_X[id] - NODE_X.input) / (NODE_X.out - NODE_X.input)) * RECEDE_SPREAD
  return 1 - smooth((q - start) / RECEDE_LEN)
}
interface St { reached: number; lit: number; heat: number; op: number; cool: number }
/** Where the light is relative to a block: reached (passed), lit (on it),
 *  heat (how gold: lit, or the warm residue once passed), op (opacity). */
function state(id: string): St {
  const a = ARRIVE[id]
  const d = DWELL[id] ?? 0.2
  const cool = coolOf(id)
  const reached = smooth((q - a) / 0.3) * cool
  const lit = (q < a ? 0 : q < a + d ? smooth((q - a) / 0.15) : Math.exp(-(q - a - d) / 0.5)) * cool
  return {
    reached,
    lit,
    heat: Math.max(lit, WARM_TINT * reached),
    op: AHEAD + (WARM - AHEAD) * reached + (1 - WARM) * lit,
    cool,
  }
}
/** Screen pixels → units (line widths, dots). */
function px(n: number): number {
  return n / s
}
function glow(color: string, amount: number, blurPx = 9): void {
  ctx!.shadowColor = color
  ctx!.shadowBlur = amount > 0.02 ? blurPx * amount * dpr : 0
}
function noGlow(): void {
  ctx!.shadowBlur = 0
}
function arrowHead(p: Path, size = 10): void {
  const [x, y] = p(1)
  const [xt, yt] = p(0.97)
  const L = Math.hypot(x - xt, y - yt) || 1
  const ux = (x - xt) / L, uy = (y - yt) / L
  ctx!.beginPath()
  ctx!.moveTo(x, y)
  ctx!.lineTo(x - ux * size - uy * size * 0.5, y - uy * size + ux * size * 0.5)
  ctx!.lineTo(x - ux * size + uy * size * 0.5, y - uy * size - ux * size * 0.5)
  ctx!.closePath()
  ctx!.fill()
}
function strokePath(p: Path, u0: number, u1: number, n = 24): void {
  ctx!.beginPath()
  for (let i = 0; i <= n; i++) {
    const [x, y] = p(u0 + ((u1 - u0) * i) / n)
    if (i === 0) ctx!.moveTo(x, y)
    else ctx!.lineTo(x, y)
  }
  ctx!.stroke()
}
function poly(pts: number[]): void {
  ctx!.beginPath()
  ctx!.moveTo(pts[0], pts[1])
  for (let i = 2; i < pts.length; i += 2) ctx!.lineTo(pts[i], pts[i + 1])
  ctx!.closePath()
}
function rrect(x: number, y: number, w: number, h: number, r: number): void {
  ctx!.beginPath()
  ctx!.roundRect(x, y, w, h, r)
}
/** Outline a block: gold as it heats, glowing while the light is on it. */
function outline(st: St, base: RGBA = LINE): void {
  glow(GOLD_GLOW, st.lit)
  ctx!.strokeStyle = mix(base, GOLD, st.heat)
  ctx!.lineWidth = px(1 + 0.7 * st.lit)
  ctx!.stroke()
  noGlow()
}
/** Vector cells: grey until the light arrives, then swept in top → bottom. */
function cells(x: number, y0: number, step: number, h: number, vals: number[], fill: number, cool: number, relu = false): void {
  const n = vals.length
  for (let i = 0; i < n; i++) {
    const on = smooth(fill * n - i) * cool
    ctx!.globalAlpha = 1
    ctx!.fillStyle = CELL_OFF
    ctx!.fillRect(x, y0 + i * step, 14, h)
    if (on > 0.01) {
      ctx!.globalAlpha = on
      ctx!.fillStyle = rgbCss(diverging(relu ? Math.max(0, vals[i]) : vals[i]))
      ctx!.fillRect(x, y0 + i * step, 14, h)
    }
  }
  ctx!.globalAlpha = 1
}

function draw(now: number) {
  if (!ctx) return
  // Dev-only clock pin for stills: window.__ch3t = seconds since mount.
  const pin = import.meta.env.DEV ? (window as unknown as { __ch3t?: number }).__ch3t : undefined
  // (a rAF timestamp can predate the mount's performance.now(): clamp)
  const tt = Math.max(0, typeof pin === 'number' ? pin : (now - t0) / 1000) / PERIOD
  const pass = Math.floor(tt)
  q = (tt - pass) * PERIOD
  const xf = 1 - coolOf('input') // the next lake arrives as the warmth leaves
  const L = LAKES[pass % LAKES.length]
  const Lnext = LAKES[(pass + 1) % LAKES.length]

  // Fit the box above the title (the card's bottom ~48 px carry the
  // chapter name and its subtitle).
  const padX = cw * 0.02
  const top = ch * 0.07
  const bw = cw - 2 * padX
  const bh = Math.max(20, ch - 48 - top)
  s = Math.min(bw / VB.w, bh / VB.h)
  const ox = padX + (bw - VB.w * s) / 2
  const oy = top + (bh - VB.h * s) / 2

  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.globalAlpha = 1
  const bg = ctx.createLinearGradient(0, 0, cw, ch)
  bg.addColorStop(0, '#0a0907')
  bg.addColorStop(1, '#0d0b08')
  ctx.fillStyle = bg
  ctx.fillRect(0, 0, cw, ch)
  ctx.setTransform(dpr * s, 0, 0, dpr * s, dpr * (ox - VB.x * s), dpr * (oy - VB.y * s))
  ctx.lineJoin = 'round'
  ctx.lineCap = 'round'

  // ── furniture: the FrontCNN bracket, the head's dashed box ──
  ctx.strokeStyle = 'rgba(245, 240, 230, 0.28)'
  ctx.lineWidth = px(1)
  ctx.beginPath()
  ctx.moveTo(CONV[0].x, 191)
  ctx.lineTo(CONV[0].x, 196)
  ctx.lineTo(slabRight(CONV[3]), 196)
  ctx.lineTo(slabRight(CONV[3]), 191)
  ctx.stroke()
  ctx.strokeStyle = 'rgba(245, 240, 230, 0.22)'
  ctx.setLineDash([px(3), px(3.5)])
  rrect(BOX.x, BOX.y, BOX.w, BOX.h, 14)
  ctx.stroke()
  ctx.setLineDash([])

  // ── edges: grey, then gold from the tail as the light rides them ──
  for (const e of EDGES) {
    const st = state(e.to)
    const a = ARRIVE[e.to]
    const u = smooth((q - e.t0) / Math.max(0.05, a - e.t0))
    ctx.globalAlpha = AHEAD + (1 - AHEAD) * Math.max(st.reached, u * st.cool)
    ctx.strokeStyle = EDGE
    ctx.fillStyle = ARROW
    ctx.lineWidth = px(1)
    strokePath(e.path, 0, 1)
    arrowHead(e.path)
    const goldA = (q < a ? 1 : Math.max(st.lit, WARM_TINT * st.reached)) * st.cool
    if (u > 0.001 && goldA > 0.01) {
      ctx.globalAlpha = goldA
      ctx.strokeStyle = GOLD_CSS
      ctx.fillStyle = GOLD_CSS
      ctx.lineWidth = px(1.4)
      strokePath(e.path, 0, u)
      if (u > 0.98) arrowHead(e.path)
    }
  }
  // the head's fans light as the light crosses them
  for (const [fan, x0, x1, id, from] of [
    [FAN1, CAT_X + 16, HID_X - 2, 'fc', ARRIVE.concat],
    [FAN2, HID_X + 16, LOGIT_X - 7, 'out', ARRIVE.fc],
  ] as [P2[], number, number, string, number][]) {
    const st = state(id)
    const u = smooth((q - from - 0.1) / (ARRIVE[id] - from - 0.1)) * st.cool
    ctx.lineWidth = px(0.8)
    ctx.globalAlpha = 0.6 + 0.4 * st.reached
    ctx.strokeStyle = 'rgba(245, 240, 230, 0.2)'
    ctx.beginPath()
    for (const [y0, y1] of fan) { ctx.moveTo(x0, y0); ctx.lineTo(x1, y1) }
    ctx.stroke()
    const goldA = (q < ARRIVE[id] ? 1 : Math.max(st.lit, 0.5 * WARM_TINT * st.reached)) * st.cool
    if (u > 0.001 && goldA > 0.01) {
      ctx.globalAlpha = goldA
      ctx.strokeStyle = 'rgba(244, 207, 106, 0.7)'
      ctx.beginPath()
      for (const [y0, y1] of fan) { ctx.moveTo(x0, y0); ctx.lineTo(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u) }
      ctx.stroke()
    }
  }

  // ── Sentinel-2: the season as a stack of frames, this lake on top ──
  {
    const st = state('input')
    const { x, y, s: fs } = FRAME
    ctx.globalAlpha = st.op
    for (const d of [16, 8]) {
      ctx.fillStyle = 'rgb(40, 36, 30)'
      ctx.strokeStyle = 'rgba(245, 240, 230, 0.4)'
      ctx.lineWidth = px(1)
      rrect(x + d, y - d, fs, fs, 4)
      ctx.fill()
      ctx.stroke()
    }
    ctx.fillStyle = 'rgb(28, 25, 20)'
    rrect(x, y, fs, fs, 4)
    ctx.fill()
    ctx.save()
    rrect(x, y, fs, fs, 4)
    ctx.clip()
    for (const [img, a] of [[thumbs[pass % LAKES.length], 1], [thumbs[(pass + 1) % LAKES.length], xf]] as [HTMLImageElement | null, number][]) {
      if (img && a > 0.01) {
        ctx.globalAlpha = st.op * a * 0.92
        ctx.drawImage(img, x, y, fs, fs)
      }
    }
    ctx.restore()
    ctx.globalAlpha = st.op
    rrect(x, y, fs, fs, 4)
    outline(st)
  }

  // ── the five input channels, five thin sheets ──
  {
    const st = state('chan')
    CHAN_COLORS.forEach((c, i) => {
      const x = CHAN_X + 12 * i
      ctx!.fillStyle = c
      ctx!.globalAlpha = st.op * 0.55
      poly([x, 67, x + 12, 55, x + 19, 55, x + 7, 67])
      ctx!.fill()
      ctx!.globalAlpha = st.op * 0.35
      poly([x + 7, 67, x + 19, 55, x + 19, 165, x + 7, 177])
      ctx!.fill()
      ctx!.globalAlpha = st.op
      ctx!.fillRect(x, 67, 7, 110)
      if (st.heat > 0.02) {
        ctx!.globalAlpha = st.heat
        ctx!.beginPath()
        ctx!.rect(x, 67, 7, 110)
        glow(GOLD_GLOW, st.lit, 6)
        ctx!.strokeStyle = GOLD_CSS
        ctx!.lineWidth = px(0.8 + 0.4 * st.lit)
        ctx!.stroke()
        noGlow()
      }
    })
  }

  // ── FrontCNN: height ∝ resolution, depth ∝ channels ──
  for (const b of CONV) {
    const st = state(b.id)
    const t = YT - b.h / 2
    const bo = YT + b.h / 2
    ctx.globalAlpha = st.op
    ctx.lineWidth = px(1)
    ctx.strokeStyle = mix([245, 240, 230, 0.42], GOLD, st.heat)
    ctx.fillStyle = mix(PRISM_TOP, PRISM_TOP_LIT, st.heat)
    poly([b.x, t, b.x + b.k, t - b.k, b.x + b.w + b.k, t - b.k, b.x + b.w, t])
    ctx.fill()
    ctx.stroke()
    ctx.fillStyle = mix(PRISM_SIDE, PRISM_SIDE_LIT, st.heat)
    poly([b.x + b.w, t, b.x + b.w + b.k, t - b.k, b.x + b.w + b.k, bo - b.k, b.x + b.w, bo])
    ctx.fill()
    ctx.stroke()
    ctx.fillStyle = mix(PRISM, PRISM_LIT, st.heat)
    ctx.beginPath()
    ctx.rect(b.x, t, b.w, b.h)
    ctx.fill()
    outline(st)
  }

  // ── the two recurrent blocks, each with its loop over the season ──
  const tick = q >= R0 && q < R1 ? ((q - R0) / ORBIT) % 1 : -1
  const season = smooth((q - R0) / (R1 - R0))
  for (const [id, y, loop] of [['clstm', YT - 30, LOOP_T], ['slstm', YB - 30, LOOP_B]] as [string, number, Path][]) {
    const st = state(id)
    ctx.globalAlpha = st.op
    ctx.strokeStyle = mix([245, 240, 230, 0.6], GOLD, st.heat)
    ctx.fillStyle = ctx.strokeStyle
    ctx.lineWidth = px(1 + 0.4 * st.lit)
    strokePath(loop, 0, 0.93)
    arrowHead(loop, 9)
    ctx.fillStyle = mix(BLOCK, BLOCK_LIT, st.heat)
    rrect(RNN_X, y, RNN_W, 60, 10)
    ctx.fill()
    outline(st)
    // a day ticking round the loop
    if (tick >= 0) {
      const [x, yy] = loop(tick)
      ctx.globalAlpha = 1
      glow('rgba(244, 207, 106, 1)', 1, 7)
      ctx.fillStyle = '#ffe7a3'
      ctx.beginPath()
      ctx.arc(x, yy, px(2), 0, Math.PI * 2)
      ctx.fill()
      noGlow()
    }
  }

  // ── p_water: the scalar input; its cursor sweeps the season as the
  //    LSTM reads it ──
  {
    const st = state('pwater')
    const y = YB - 30
    ctx.globalAlpha = st.op
    ctx.fillStyle = mix(BLOCK, BLOCK_LIT, st.heat * 0.6)
    rrect(PW.x, y, PW.w, 60, 8)
    ctx.fill()
    outline(st, LINE_SOFT)
    // the curve reshapes into the next lake's during the cool-down
    const n = L.pw.length
    const sx = (i: number) => PW.x + 8 + (i / (n - 1)) * (PW.w - 16)
    const mf = 1 - st.cool
    const sy = (i: number) => y + 54 - (L.pw[i] + (Lnext.pw[i] - L.pw[i]) * mf) * 48
    const spark = () => {
      ctx!.beginPath()
      for (let i = 0; i < n; i++) {
        if (i === 0) ctx!.moveTo(sx(i), sy(i))
        else ctx!.lineTo(sx(i), sy(i))
      }
      ctx!.stroke()
    }
    ctx.lineWidth = px(1.1)
    ctx.strokeStyle = 'rgba(127, 208, 255, 0.5)'
    spark()
    const readTo = q < R0 ? 0 : season
    if (readTo * st.cool > 0.001) {
      ctx.save()
      ctx.beginPath()
      ctx.rect(PW.x + 4, y, 4 + (PW.w - 16) * readTo, 60)
      ctx.clip()
      ctx.globalAlpha = st.op * st.cool
      ctx.strokeStyle = '#7fd0ff'
      ctx.lineWidth = px(1.5)
      spark()
      ctx.restore()
    }
    if (q >= R0 && q < R1 + 0.4) {
      const cx = PW.x + 8 + (PW.w - 16) * readTo
      ctx.globalAlpha = q < R1 ? 1 : 1 - (q - R1) / 0.4
      ctx.strokeStyle = GOLD_CSS
      ctx.lineWidth = px(1.2)
      ctx.beginPath()
      ctx.moveTo(cx, y + 4)
      ctx.lineTo(cx, y + 56)
      ctx.stroke()
    }
  }

  // ── GAP → the 32-vector; LSTM → the 16-vector ──
  {
    const st = state('gap')
    ctx.globalAlpha = st.op
    ctx.fillStyle = mix(BLOCK, BLOCK_LIT, st.heat)
    poly([GAP_X, YT - 28, GAP_X + 42, YT - 12, GAP_X + 42, YT + 12, GAP_X, YT + 28])
    ctx.fill()
    outline(st)
  }
  cells(VEC_X, YT - 67, 4.2, 3.4, L.gap, (q - ARRIVE.v32) / 0.4, coolOf('v32'))
  cells(VEC_X, YB - 34, 4.2, 3.4, L.slstm, (q - ARRIVE.v16) / 0.4, coolOf('v16'))

  // ── the head: concat 48 → hidden 64 → five logits → softmax ──
  cells(CAT_X, CAT_Y0, CAT_STEP, 2.9, L.gap, (q - ARRIVE.concat) / 0.35, coolOf('concat'))
  cells(CAT_X, CAT_Y0 + 32 * CAT_STEP + 2, CAT_STEP, 2.9, L.slstm, (q - ARRIVE.concat - 0.23) / 0.35, coolOf('concat'))
  cells(HID_X, HID_Y0, HID_STEP, 2.1, L.hidden, (q - ARRIVE.fc) / 0.4, coolOf('fc'), true)
  for (const [id, x, y0, h] of [['concat', CAT_X, CAT_Y0, CAT_H], ['fc', HID_X, HID_Y0, 64 * HID_STEP]] as [string, number, number, number][]) {
    const st = state(id)
    if (st.lit > 0.02) {
      ctx.globalAlpha = st.lit
      ctx.beginPath()
      ctx.rect(x - 3, y0 - 3, 20, h + 5)
      outline(st)
    }
  }
  {
    const st = state('out')
    const fill = smooth((q - ARRIVE.out) / 0.7) * st.cool
    const verdict = smooth((q - ARRIVE.out - 0.6) / 0.4) * st.cool
    CLASSES.forEach((c, i) => {
      const y = OUT_Y[i]
      const col = COLORS[c]
      const isPred = c === L.pred
      ctx!.globalAlpha = st.op
      ctx!.strokeStyle = 'rgba(245, 240, 230, 0.42)'
      ctx!.lineWidth = px(1)
      ctx!.beginPath()
      ctx!.moveTo(LOGIT_X + 7, y)
      ctx!.lineTo(PILL_X - 4, y)
      ctx!.stroke()
      ctx!.fillStyle = '#14120f'
      ctx!.strokeStyle = col
      ctx!.lineWidth = px(1.2)
      ctx!.beginPath()
      ctx!.arc(LOGIT_X, y, 5.5, 0, Math.PI * 2)
      ctx!.fill()
      ctx!.stroke()
      // pill: tint + outline in the class colour, filled to p
      if (isPred) glow(col, verdict, 10)
      ctx!.fillStyle = hexA(col, 0.15)
      rrect(PILL_X, y - PILL_H / 2, PILL_W, PILL_H, PILL_H / 2)
      ctx!.fill()
      ctx!.strokeStyle = col
      ctx!.lineWidth = px(1 + (isPred ? 0.9 * verdict : 0))
      ctx!.stroke()
      noGlow()
      const w = Math.max(0, Math.min(1, L.probs[i])) * PILL_W * fill
      if (w > 0.5) {
        ctx!.save()
        rrect(PILL_X, y - PILL_H / 2, PILL_W, PILL_H, PILL_H / 2)
        ctx!.clip()
        ctx!.globalAlpha = 0.8 * st.op
        ctx!.fillStyle = col
        ctx!.fillRect(PILL_X, y - PILL_H / 2, w, PILL_H)
        ctx!.restore()
      }
    })
  }

  // ── the light itself: a dot riding the edge into the block ahead ──
  for (const e of EDGES) {
    const a = ARRIVE[e.to]
    if (q < e.t0 || q > a + 0.12) continue
    const [x, y] = e.path(smooth((q - e.t0) / Math.max(0.05, a - e.t0)))
    ctx.globalAlpha = q <= a ? 1 : 1 - (q - a) / 0.12
    glow('rgba(244, 207, 106, 1)', 1, 8)
    ctx.fillStyle = '#ffe7a3'
    ctx.beginPath()
    ctx.arc(x, y, px(2.2), 0, Math.PI * 2)
    ctx.fill()
    noGlow()
  }
  ctx.globalAlpha = 1

  rafId = requestAnimationFrame(draw)
}

onMounted(() => {
  const c = canvas.value
  if (!c) return
  ctx = c.getContext('2d')
  setSize()
  ro = new ResizeObserver(setSize)
  ro.observe(c)
  t0 = performance.now()
  rafId = requestAnimationFrame(draw)
  LAKES.forEach((l, i) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => { thumbs[i] = img }
    img.src = netUrl(`${l.lake}/thumb.jpg`)
  })
})

onBeforeUnmount(() => {
  cancelAnimationFrame(rafId)
  ro?.disconnect()
  ro = null
  ctx = null
})
</script>

<style scoped>
.net-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  background: #0a0907;
}
</style>
