// Chapter 2's block-anchored keys, read per frame from the Globe's
// window.__simDomainScreen (the same anchor the tier pills ride).
//
// useBlockAnchor — (the director's placement: no card, just the
// colorbar, beneath the left
// area of the simulation domain): a key hung just under the block's
// projected bottom edge, left-aligned with its left area. The bed beat's
// key (Ch2BedLegend) and the teaser's twin key (Ch2Teaser) ride it.
//
// useInsetKeyAnchor — (the director then moved the scale bar farther
// left and up, clear of the simulation
// domain object): the stress and imagery-difference keys move UP to the
// top cluster — under the tier pills (which now stay up on the
// results beats as headings, right of the centre-lakes inset), right-
// aligned with them, over the open ground beyond the block's top corner.
// The wedge directly UNDER the inset is only 26–75 px tall at 1440×900 —
// too little for a key — so that spot is the ICE FLOW arrow's
// (Ch2FlowArrow), along the block's upper-left edge.
// Now only the imagery-difference key rides it; the stress
// key hangs under the block's outflow edge (useOutflowKeyAnchor, below).
import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

export interface ScreenPt {
  x: number
  y: number
}
export interface SimScreen {
  visible: boolean
  landed?: boolean
  spread?: number
  bbox?: { minX: number; minY: number; maxX: number; maxY: number }
  /** The four projected surface corners (Globe.vue). */
  corners?: ScreenPt[]
  /** Projected ice-flow direction [deg, atan2(dy, dx), y down]. */
  flowDirDeg?: number | null
  /** Length of each edge of the model square [km]. */
  edgeKm?: number | null
}
export interface Rect {
  left: number
  top: number
  right: number
  bottom: number
}

export function simScreen(): SimScreen | null {
  return (window as unknown as { __simDomainScreen?: SimScreen | null }).__simDomainScreen ?? null
}

/** The block's upper-left edge on screen: its top-most corner T and its
 *  left-most corner L (adjacent on every framing the chapter uses). */
export function upperLeftEdge(c: ScreenPt[]): { T: ScreenPt; L: ScreenPt } | null {
  if (c.length !== 4) return null
  let ti = 0
  let li = 0
  for (let i = 1; i < 4; i++) {
    if (c[i].y < c[ti].y) ti = i
    if (c[i].x < c[li].x) li = i
  }
  if (ti === li) return null
  return { T: c[ti], L: c[li] }
}

/** The block's top silhouette at screen x: the upper-left edge left of
 *  the top corner, the upper-right edge right of it (Infinity outside). */
export function blockTopY(c: ScreenPt[], x: number): number {
  let ti = 0
  for (let i = 1; i < 4; i++) if (c[i].y < c[ti].y) ti = i
  const T = c[ti]
  const a = c[(ti + 1) % 4]
  const b = c[(ti + 3) % 4]
  const [L, R] = a.x < b.x ? [a, b] : [b, a]
  const on = (P: ScreenPt, Q: ScreenPt) => P.y + ((x - P.x) * (Q.y - P.y)) / (Q.x - P.x || 1e-6)
  if (x <= T.x) return x < L.x ? Infinity : on(T, L)
  return x > R.x ? Infinity : on(T, R)
}

/** The centre-lakes inset's box — measured, or (hidden / not yet in) where
 *  its CSS puts it (left 2vw, top max(7vh, chrome + 0.9rem), ≈172 × 229). */
let lastInset: Rect | null = null
export function insetRect(): Rect {
  const r = document.querySelector('.ccl')?.getBoundingClientRect()
  if (r && r.width > 0) {
    lastInset = { left: r.left, top: r.top, right: r.right, bottom: r.bottom }
    return lastInset
  }
  if (lastInset) return lastInset
  const left = 0.02 * window.innerWidth
  const top = Math.max(0.07 * window.innerHeight, 109)
  return { left, top, right: left + 172, bottom: top + 229 }
}

/** `el` = the key's root (its height keeps it on screen). `shiftX` (px)
 *  moves the anchor sideways — the teaser's twin block (Globe
 *  window.__simTwinScreen) sits that far right of the first. */
export function useBlockAnchor(el: Ref<HTMLElement | null>, shiftX?: () => number) {
  const left = ref(0)
  const top = ref(0)
  /** False until the block has a projected box (the key stays hidden). */
  const ready = ref(false)
  let raf = 0
  const tick = () => {
    const s = simScreen()
    const W = window.innerWidth
    const H = window.innerHeight
    if (s && s.visible && s.bbox) {
      const b = s.bbox
      const h = el.value?.offsetHeight ?? 60
      // the block's left area: a little in from its left-most corner
      left.value = Math.max(0.022 * W, b.minX + 0.06 * (b.maxX - b.minX)) + (shiftX?.() ?? 0)
      top.value = Math.max(b.minY, Math.min(b.maxY + 14, H - 16 - h))
      ready.value = true
    } else {
      ready.value = false
    }
    raf = requestAnimationFrame(tick)
  }
  onMounted(() => {
    raf = requestAnimationFrame(tick)
  })
  onBeforeUnmount(() => cancelAnimationFrame(raf))
  return { left, top, ready }
}

/** The tier pills' (SimViewControls .svc) slot at its HIGHEST — under the
 *  sub-menu — with their current width: they rise there to clear the ICE
 *  FLOW arrow or the keys, so the keys and the arrow plan around it. */
export function tierSlot(): Rect | null {
  const el = document.querySelector('.svc') as HTMLElement | null
  if (!el || el.style.visibility === 'hidden') return null
  const r = el.getBoundingClientRect()
  if (r.width <= 0) return null
  let chrome = 0
  for (const sel of ['.landmarks', '.beat-nav']) {
    const c = document.querySelector(sel)?.getBoundingClientRect()
    if (c && c.height > 0) chrome = Math.max(chrome, c.bottom)
  }
  const top = (chrome || 100) + 14
  // …and the definition hung under the POST · ELASTIC station on its beat
  // — the keys drop below it
  const def = el.querySelector('.svc-def')?.getBoundingClientRect()
  const defBottom = def && def.height > 0 ? def.bottom - r.top + top : 0
  return { left: r.left, right: r.right, top, bottom: Math.max(top + el.offsetHeight, defBottom) }
}

/** A key under the tier pills, right-aligned with them (see the file
 *  head); before the tiers are measured, beside the inset. */
export function useInsetKeyAnchor(el: Ref<HTMLElement | null>) {
  const left = ref(0)
  const top = ref(0)
  const ready = ref(false)
  let raf = 0
  let frame = 0
  let slot: Rect | null = null
  const tick = () => {
    const s = simScreen()
    // after the landing (not over the dive, before the tiers are up)
    if (s && s.visible && s.landed && s.corners?.length === 4) {
      if (frame++ % 15 === 0) slot = tierSlot() ?? slot
      const w = el.value?.offsetWidth ?? 200
      if (slot) {
        // right-aligned with the stations' key anchor (SimViewControls
        // data-key-right: left of the stress space — the row itself runs
        // on above it), else with the row's right end
        const kr = Number((document.querySelector('.svc') as HTMLElement | null)?.dataset.keyRight)
        left.value = (kr > 0 ? kr : slot.right) - w
        top.value = slot.bottom + 14
      } else {
        const r = insetRect()
        left.value = r.right + 28
        top.value = r.top
      }
      ready.value = true
    } else {
      ready.value = false
    }
    raf = requestAnimationFrame(tick)
  }
  onMounted(() => {
    raf = requestAnimationFrame(tick)
  })
  onBeforeUnmount(() => cancelAnimationFrame(raf))
  return { left, top, ready }
}

/** The block's BOTTOM silhouette at screen x (the lower envelope of the
 *  four projected surface corners; -Infinity outside the block). */
export function blockBottomY(c: ScreenPt[], x: number): number {
  let y = -Infinity
  for (let i = 0; i < 4; i++) {
    const P = c[i]
    const Q = c[(i + 1) % 4]
    const lo = Math.min(P.x, Q.x)
    const hi = Math.max(P.x, Q.x)
    if (x < lo || x > hi || hi - lo < 1e-6) continue
    y = Math.max(y, P.y + ((x - P.x) * (Q.y - P.y)) / (Q.x - P.x))
  }
  return y
}

/** useOutflowKeyAnchor — the stress key's place (the director wanted the
 *  colorbar at the bottom left, just below the visible edge of the
 *  simulation domain where the outflow is, and appearing smoothly in
 *  one place: before this it appeared and then
 *  jumped to the right from its initial position). On every block
 *  framing the chapter uses, the block's lower-left edge — its left-most
 *  corner to its bottom corner — is the OUTFLOW wall (Globe corners c1–c2,
 *  the side wall we see). The key hangs just below that edge's line (plus
 *  the side wall's projected depth) across its whole width, left-aligned a
 *  little in from the left-most corner (never inside the 2.2vw gutter),
 *  and ≥ 16 px clear of the screen bottom.
 *
 *  ONE PLACE: `ready` waits for the landed block (corners present) AND a
 *  position stable to 0.5 px for two frames — so the key fades in where it
 *  will stay; it then follows only the block (camera moves). `visible()`
 *  false re-arms the gate, so each appearance settles first. */
export function useOutflowKeyAnchor(el: Ref<HTMLElement | null>, visible: () => boolean) {
  const left = ref(0)
  const top = ref(0)
  const ready = ref(false)
  let raf = 0
  let stable = 0
  let px = NaN
  let py = NaN
  const GAP = 14
  const tick = () => {
    const s = simScreen()
    const c = s?.corners
    if (s && s.visible && s.landed && s.bbox && c && c.length === 4) {
      const W = window.innerWidth
      const H = window.innerHeight
      const w = el.value?.offsetWidth ?? 190
      const h = el.value?.offsetHeight ?? 80
      let li = 0
      let maxCornerY = -Infinity
      for (let i = 0; i < 4; i++) {
        if (c[i].x < c[li].x) li = i
        maxCornerY = Math.max(maxCornerY, c[i].y)
      }
      // the side wall's projected depth under the near corner
      const wall = Math.max(0, s.bbox.maxY - maxCornerY)
      const x0 = Math.max(Math.max(16, 0.022 * W), c[li].x + 24)
      const x1 = x0 + w
      // the lowest point of the block's bottom silhouette over [x0, x1]
      let edge = -Infinity
      const xs = [x0, x1, ...c.map((p) => p.x).filter((x) => x > x0 && x < x1)]
      for (const x of xs) edge = Math.max(edge, blockBottomY(c, x))
      if (!Number.isFinite(edge)) edge = maxCornerY
      const nx = x0
      const ny = Math.min(edge + wall + GAP, H - 16 - h)
      if (Math.abs(nx - px) < 0.5 && Math.abs(ny - py) < 0.5) stable++
      else stable = 0
      px = nx
      py = ny
      // hidden: the key holds still while it fades out (no slide)
      if (!visible()) ready.value = false
      else {
        left.value = nx
        top.value = ny
        if (stable >= 2) ready.value = true
      }
    } else {
      ready.value = false
      stable = 0
    }
    raf = requestAnimationFrame(tick)
  }
  onMounted(() => {
    raf = requestAnimationFrame(tick)
  })
  onBeforeUnmount(() => cancelAnimationFrame(raf))
  return { left, top, ready }
}
