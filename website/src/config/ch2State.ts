// Chapter 2's block view — the ONE shared state for what the simulation-
// domain block shows (the director's design: the main choice is PRE
// DRAINAGE, POST DRAINAGE or DIFFERENCE, and once the user has picked that
// they choose between IMAGERY, ELASTIC MODEL and VISCOUS MODEL).
//
//   stage   pre | post | difference   (the primary tier; null = nothing
//                                       picked yet — the landed block shows
//                                       its pre-drainage imagery)
//   layer   imagery | elastic | viscous (the secondary tier; shown once a
//                                       stage is picked)
//
// What each cell paints on the block's surface:
//   imagery  · pre / post   the Sentinel-2 scenes (sim_domains.json dates)
//   imagery  · difference   mean-RGB reflectance change, post − pre
//                           (BrBG, ±IMAGERY_DIFF_LIM; Globe uImgDiffT)
//   elastic/viscous · pre   σ_t1 of the NO-PATCH run (the undisturbed ice
//                           before drainage)
//   elastic/viscous · post  σ_t1 of the WITH-PATCH run (after drainage)
//   elastic/viscous · diff  Δσ_t1 = with patch − no patch (the paper's
//                           stress response — the drape the site has
//                           always shown)
//
// API for other code:
//   import { ch2View, setCh2View } from '../../config/ch2State'
//   setCh2View('difference', 'viscous')   // both tiers, animated
//   setCh2View(null)                      // clear both tiers
//   ch2View.stage / ch2View.layer         // reactive, read anywhere
// Explore.vue maps the view onto the Globe payload (SectionCh2 face/field
// props), the legend, the phase panel and the control tiers. SectionCh2
// (the path, config/ch2Beats.ts) sets {pre, imagery} on the
// landing, {post, imagery} on `post`, and mirrors each results beat's
// paint ({post | difference} × its model); on the imagery beats a tier
// click only changes the view — NEXT walks the path regardless.
//
// THE STATION OVERRIDE (the director wanted every station button — PRE
// DRAINAGE VISCOUS, POST DRAINAGE ELASTIC and so on — clickable, giving
// the same views of the stress space, unified across all center lakes):
// ch2View IS the override — one state, not two. Every
// beat whose phase is `pre` … `diff-viscous-t1` (both passes, any lake)
// sets it to its own station on arrival; a station click sets it to that
// station; NEXT / BACK set it back to the next beat's own. "The step
// shown" is ch2StepShown(ch2View): SectionCh2 paints the block from the
// view, Ch2Results draws that step's single stress space, Explore's key
// names it and the stations light by it. A deep link's ?stage=&layer=
// lands in the same place (a view no station names — e.g. pre · elastic —
// still gets its step: the model's field, x then y emphasised).
import { reactive } from 'vue'
import type { SimFace, SimField } from './simLakes'
import { CH2_STATIONS, ch2StepOf, type Ch2Station, type Ch2Step } from './ch2Beats'

export type Ch2Stage = 'pre' | 'post' | 'difference'
export type Ch2Layer = 'imagery' | 'elastic' | 'viscous'

export const CH2_STAGES: { id: Ch2Stage; label: string }[] = [
  { id: 'pre', label: 'Pre drainage' },
  { id: 'post', label: 'Post drainage' },
  { id: 'difference', label: 'Difference' },
]
export const CH2_LAYERS: { id: Ch2Layer; label: string }[] = [
  { id: 'imagery', label: 'Imagery' },
  { id: 'elastic', label: 'Elastic model' },
  { id: 'viscous', label: 'Viscous model' },
]

/** The chapter's lake when nobody clicks one: Lake 2394 (sim 2019cw871).
 *  Beat 0's NEXT opens its popup; deep links without `?lake=` land on it. */
export const CH2_DEFAULT_LAKE = 'CW2019_2394'

/** Imagery difference colour range: ± this much mean-RGB surface
 *  reflectance (the S2 faces are reflectance/1e4 clipped to [0, 1]).
 *  A drained lake brightens by ~0.3–0.5; melt/illumination background
 *  sits within ±0.1. */
export const IMAGERY_DIFF_LIM = 0.4

export interface Ch2View {
  stage: Ch2Stage | null
  layer: Ch2Layer | null
}

export const ch2View = reactive<Ch2View>({ stage: null, layer: null })

/** Set the block view. A stage without a layer keeps the current layer
 *  (imagery when none); `setCh2View(null)` clears both tiers. */
export function setCh2View(stage: Ch2Stage | null, layer?: Ch2Layer | null): void {
  if (stage === null) {
    ch2View.stage = null
    ch2View.layer = null
    return
  }
  ch2View.stage = stage
  ch2View.layer = layer ?? ch2View.layer ?? 'imagery'
}

/** The legacy face/field pair the Globe payload, legend and phase panel
 *  speak (config/simLakes.ts). */
export function ch2FaceOf(v: Ch2View): SimFace {
  if (v.layer === 'elastic' || v.layer === 'viscous') return v.layer
  return v.stage === 'post' || v.stage === 'difference' ? 'post' : 'pre'
}
export function ch2FieldOf(v: Ch2View): SimField {
  return v.stage === 'pre' ? 'nopatch' : v.stage === 'post' ? 'patch' : 'difference'
}
/** True for the imagery-difference cell (a shader mode, not a texture). */
export function ch2ImageryDiff(v: Ch2View): boolean {
  return v.layer === 'imagery' && v.stage === 'difference'
}
/** The inverse map (deep links `?model=&field=`, the MGSIM handoff). */
export function ch2ViewOf(face: SimFace, field: SimField): Ch2View {
  if (face === 'elastic' || face === 'viscous') {
    return {
      layer: face,
      stage: field === 'nopatch' ? 'pre' : field === 'patch' ? 'post' : 'difference',
    }
  }
  return { layer: 'imagery', stage: face }
}

/** The station (config/ch2Beats.ts CH2_STATIONS) a view is, or null. */
export function ch2StationOf(v: Ch2View): Ch2Station | null {
  return CH2_STATIONS.find((s) => s.stage === v.stage && s.layer === v.layer) ?? null
}
/** The results step a view shows — the stress space beside the block and
 *  the key's field: its station's step, else (a deep link's model view no
 *  station names) the model's own; null on the imagery. */
export function ch2StepShown(v: Ch2View): Ch2Step | null {
  const st = ch2StationOf(v)
  if (st) return ch2StepOf(st.id)
  if ((v.layer !== 'elastic' && v.layer !== 'viscous') || !v.stage) return null
  if (v.stage === 'difference') return { model: v.layer, comp: 't1', field: 'diff', emphasis: 'y' }
  return { model: v.layer, comp: 't1', field: v.stage, emphasis: 'x' }
}
