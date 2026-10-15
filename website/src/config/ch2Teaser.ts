// The teaser's VISCOUS STRESS SPACE (the director asked for a viscous
// stress space on the right that ticks through where Lake 1938's stress
// plots for each bed realisation — all the points present at all times,
// faded except the one currently in view as the cycle ticks by).
// Lake 1938 — 1951's neighbour that does not drain — on BedMachine and the
// ten MGSIM beds, read from the MGSIM page's own file (R2
// addl/mgsim/phase_space_mgsim.json, the same one PhaseSpacePanel reads):
// x = viscous σ_t1^post, y = viscous Δσ_t1 [kPa]. One entry per
// CH2_TEASER_FRAMES frame, in the same order.
import { mediaUrl } from './media'
import { CH2_TEASER_FRAMES } from './ch2Beats'
import type { PhaseSpaceFile } from './simLakes'

export const CH2_TEASER_SPACE_URL = 'addl/mgsim/phase_space_mgsim.json'
export const CH2_TEASER_SPACE_CENTER = 1951
export const CH2_TEASER_SPACE_LAKE = 1938
/** The ZOOM-IN window (the plot itself is the chapter's ±1000 frame —
 *  the director wanted the same ±1000 axis space as the chapter, with a
 *  zoom-in box carrying the tighter axis): 1938 sits
 *  at x −238…−169, y +21…+44 kPa on the eleven beds — compressive on every
 *  one; −300…−100 × 0…+60 shows that cloud at ~35 % of the inset. */
export const CH2_TEASER_SPACE_X: [number, number, number] = [-300, -100, 100] // lo, hi, tick step (grid at ½)
export const CH2_TEASER_SPACE_Y: [number, number, number] = [0, 60, 20]

export interface Ch2TeaserPoint {
  x: number
  y: number
}

let promise: Promise<(Ch2TeaserPoint | null)[] | null> | null = null
/** The eleven points (null where a model lacks 1938) — fetched once,
 *  shared; called from the bed beat on so the first tick never waits. */
export function loadCh2TeaserSpace(): Promise<(Ch2TeaserPoint | null)[] | null> {
  if (!promise) {
    promise = fetch(mediaUrl(CH2_TEASER_SPACE_URL))
      .then((r) => (r.ok ? (r.json() as Promise<PhaseSpaceFile>) : null))
      .then((j) => {
        if (!j) return null
        return CH2_TEASER_FRAMES.map((f) => {
          const p = j.models[f.id]?.points.find(
            (q) => q.center === CH2_TEASER_SPACE_CENTER && q.num === CH2_TEASER_SPACE_LAKE,
          )
          return p && p.x1 != null && p.y1 != null ? { x: p.x1, y: p.y1 } : null
        })
      })
      .catch(() => {
        promise = null
        return null
      })
  }
  return promise
}
