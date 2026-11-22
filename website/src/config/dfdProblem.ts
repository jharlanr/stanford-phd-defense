// APS DFD 2026 · THE PROBLEM beat (DfdProblem.vue): lake 2394 in time —
// the elmerfiles README's graphical summary, rebuilt live from the site's
// own Chapter 2 data. LEFT the centre-lakes map (the Chapter 2 inset's
// file, ch02/inset/centerlakes_v1.json, drawn large); RIGHT the lake's
// 15 km tile through five STATIONS, the viscous stress space filling
// beside it. The stations are the talk's (config/ch2Beats.ts THE PATH,
// minus the elastic two): each paints the block's own drape — the
// sim_domains_v2.json key SectionCh2's paintView hands the Globe for that
// station — on the block's one seismic ±1 MPa scale (BlisterStressLegend),
// and shows the talk's stress-space step for it (ch2StepOf: PRE the frame
// alone, POST the x axis lit, DIFFERENCE the y axis).
import { ch2StepOf, type Ch2PhaseId, type Ch2Step } from './ch2Beats'
import type { Ch2EqName } from './ch2Eqs'
import { CH2_DEFAULT_LAKE } from './ch2State'

/** The lake the beat opens on: the chapter's own default (2394). */
export const DFD_PROBLEM_LAKE = CH2_DEFAULT_LAKE

/** The manifest (sim_domains_v2.json) key of the drape a station paints. */
export type DfdProblemRaster = 's2_pre' | 's2_post' | 'stress_v_nopatch' | 'stress_v_patch' | 'stress_viscous'

export interface DfdProblemStation {
  /** The talk's phase (config/ch2Beats.ts). */
  id: Ch2PhaseId
  raster: DfdProblemRaster
  /** The station bar's words: the stage over the layer (SimViewControls'). */
  stage: string
  layer: 'imagery' | 'post' | 'diff'
  /** The title line over the tile (trusted static HTML: the subscripts). */
  title: string
  /** Which Sentinel-2 date the station shows (the imagery only). */
  date: 'pre' | 'post' | null
  /** The colour bar's LaTeX symbol (the block's bar; none on the imagery). */
  cbar: Ch2EqName | null
  /** The stress space beside the tile (null = the blank frame). */
  step: Ch2Step | null
}

export const DFD_PROBLEM_STATIONS: DfdProblemStation[] = [
  { id: 'pre', raster: 's2_pre', stage: 'Pre drainage', layer: 'imagery', title: 'pre-drainage imagery', date: 'pre', cbar: null, step: null },
  { id: 'post', raster: 's2_post', stage: 'Post drainage', layer: 'imagery', title: 'post-drainage imagery', date: 'post', cbar: null, step: null },
  { id: 'pre-viscous-t1', raster: 'stress_v_nopatch', stage: 'Pre drainage', layer: 'post', title: 'viscous <i>σ</i><sub>t1</sub> · pre-drainage', date: null, cbar: 'cb_pre_t1', step: ch2StepOf('pre-viscous-t1') },
  { id: 'post-viscous-t1', raster: 'stress_v_patch', stage: 'Post drainage', layer: 'post', title: 'viscous <i>σ</i><sub>t1</sub> · post-drainage', date: null, cbar: 'cb_post_t1', step: ch2StepOf('post-viscous-t1') },
  { id: 'diff-viscous-t1', raster: 'stress_viscous', stage: 'Difference', layer: 'diff', title: 'Δ<i>σ</i><sub>t1</sub> · drainage-induced change', date: null, cbar: 'cb_diff_t1', step: ch2StepOf('diff-viscous-t1') },
]

/** The map's numbers: where each centre lake's label sits (px from its
 *  glyph; the one on the tile is placed by the component). 2411 · 2416 ·
 *  2511 lie within 12 km and 1951 · 2520 5 km apart, so the sides are
 *  chosen by hand. */
export const DFD_PROBLEM_MAP_LABELS: Record<number, { dx: number; dy: number; anchor: 'start' | 'end' | 'middle' }> = {
  1910: { dx: 18, dy: 5, anchor: 'start' },
  1951: { dx: 14, dy: 20, anchor: 'start' },
  2520: { dx: -16, dy: 5, anchor: 'end' },
  2394: { dx: 22, dy: 7, anchor: 'start' },
  2411: { dx: -18, dy: 5, anchor: 'end' },
  2416: { dx: 20, dy: -4, anchor: 'start' },
  2511: { dx: 20, dy: 15, anchor: 'start' },
}

/** Where the map's window sits on shared/greenland_silhouette.png, as a
 *  fraction of the picture: FieldworkExplorer's North Lake mark (45, 200)
 *  on 170 × 298, moved the 1.6° north to the inset's centre. */
export const DFD_PROBLEM_SILHOUETTE_AOI = { x: 0.265, y: 0.6 }
/** Greenland's north–south extent on the silhouette [km], for the window's size. */
export const DFD_PROBLEM_GREENLAND_NS_KM = 2650

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'June', 'July', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
/** "2019-06-13" → "13 June 2019" (the block's station dates). */
export function dfdProblemDate(iso: string | null | undefined): string {
  if (!iso) return ''
  const [y, m, d] = iso.split('-')
  return `${parseInt(d, 10)} ${MONTHS[parseInt(m, 10) - 1] ?? ''} ${y}`
}
