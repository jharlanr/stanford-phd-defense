// Shared geometry between TheoryPanel.vue's SVG stage and the beat 3→4
// seam morph. SectionCh1 asks the Globe to dolly the
// camera so the flattened, painted cross-section slab lands EXACTLY in
// the panel's stage-0 field rect — then the panel's field image fades in
// over the identical-looking slab with no fade-to-black. Any change to
// the panel's stage-0 field placement must go through these constants or
// the seam misaligns.

/** TheoryPanel SVG viewBox. */
export const TP_VW = 1780
export const TP_VH = 980

/** Stage-0 field-image rect in viewBox coordinates. */
export const TP_FX = 150
export const TP_FW = 1490
export const TP_FY = 64
export const TP_FH = 360
/** Stage-0 tween shifts the field group down by this many vb units. */
export const TP_FIELD_SHIFT = 150

/** Field x half-range [km] (the field image spans ±40 km). */
export const TP_HALF_KM = 40

/**
 * .tp-stage's top padding in px: max(6.5vh, --chrome-bottom + 0.5rem),
 * where --chrome-bottom (Explore.vue, set while a beat page's sub-menu
 * hangs under the ribbon) = 1.2vh + 2.92rem + 0.3rem + 2rem. Read off
 * the live element when the panel is mounted (it is, one beat early),
 * the formula otherwise — the two must agree.
 */
export function theoryStageTopPx(winH: number): number {
  if (typeof document !== 'undefined') {
    const el = document.querySelector('.tp-stage')
    if (el) {
      const p = parseFloat(getComputedStyle(el).paddingTop)
      if (Number.isFinite(p) && p > 0) return p
    }
  }
  const rem =
    typeof document !== 'undefined'
      ? parseFloat(getComputedStyle(document.documentElement).fontSize) || 16
      : 16
  return Math.max(0.065 * winH, 0.012 * winH + (2.92 + 0.3 + 2 + 0.5) * rem)
}

/**
 * Screen-pixel rect of the stage-0 field image for a given window size.
 * Mirrors TheoryPanel's layout chain: .tp-stage occupies the viewport
 * minus insets (right 1vw) with padding <theoryStageTopPx> 0 1vh 1vw;
 * the SVG fills it with preserveAspectRatio="xMidYMid meet".
 */
export function theoryFieldScreenRect(
  winW: number,
  winH: number,
): { x: number; y: number; w: number; h: number } {
  const cx0 = 0.01 * winW            // padding-left 1vw
  const cx1 = winW - 0.01 * winW     // right inset 1vw
  const cy0 = theoryStageTopPx(winH) // padding-top: under the ribbon + sub-menu
  const cy1 = winH - 0.01 * winH     // padding-bottom 1vh
  const cw = cx1 - cx0
  const ch = cy1 - cy0
  const s = Math.min(cw / TP_VW, ch / TP_VH)
  const ox = cx0 + (cw - TP_VW * s) / 2
  const oy = cy0 + (ch - TP_VH * s) / 2
  return {
    x: ox + TP_FX * s,
    y: oy + (TP_FY + TP_FIELD_SHIFT) * s,
    w: TP_FW * s,
    h: TP_FH * s,
  }
}
