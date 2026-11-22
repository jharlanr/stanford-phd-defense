// APS DFD 2026 · Interact — the conference presentation as a page of the
// site (/additional-work/dfd, SectionDfd.vue): the two-minute flash slide
// (beat 0) and the interactive ePoster the presenter walks with visitors
// during the 40-minute discussion (beats 1–7). The director's brief
// (2026-11-21): the DFD audience wants the fluid mechanics — the 1-D and
// 2-D slippery-patch theory, its equations, sliders over every parameter,
// and the theory against the depth-averaged 3-D Stokes runs — plus the
// field videos and imagery that orient people to the place. This file is
// the ONE place the beats, the title block and the asset keys live.
//
//   0 slide      the flash slide: title block, one claim, two visuals
//   1 field      the Introduction's fieldwork map, exactly: the landed
//                2023 tracks, then the three GoPro clips, one per NEXT
//   2 problem    lake 2394 in time (the elmerfiles README's summary): the
//                tile through pre/post imagery and the viscous σt1 pre,
//                post, difference, the stress space filling alongside
//   3 model      Stokes → shallow stream: the PDEs, the assumptions, the
//                slab schematic
//   4 solutions  the final equations, 1-D and 2-D, with the PHYSICAL
//                INTUITION toggle (each term named)
//   5 lab        live theory on continuous sliders: the 2-D field and the
//                1-D vs 2-D centreline profile for the same parameters
//   6 collapse   the paper's Fig. 3 C–D re-drawn live from the sweep: the
//                profiles and their dimensionless collapse, the maxima
//                against theory (the separate Stokes-viewer beat was cut
//                by the director on 2026-11-21 night; the deeper dive
//                still has the viewer)
//   7 takeaway   the line, the funding
import { mediaUrl } from './media'

export const DFD_BEAT_IDS = [
  'slide',
  'field',
  'problem',
  'model',
  'solutions',
  'lab',
  'collapse',
  'takeaway',
] as const
export type DfdBeatId = (typeof DFD_BEAT_IDS)[number]
export const DFD_BEAT = Object.fromEntries(DFD_BEAT_IDS.map((id, i) => [id, i])) as Record<DfdBeatId, number>
export const DFD_BEATS = DFD_BEAT_IDS.length
/** Beats with steps of their own — NEXT / BACK walk them before moving on
 *  (one deterministic path, the Introduction's rule): the field's landed
 *  map then its three clips; the problem's five stations (pre imagery,
 *  post imagery, σt1 pre, σt1 post, Δσt1); the collapse's two views
 *  (the profiles, the maxima). `?s=M` deep-links a step. */
export const DFD_SUBSTEPS: Partial<Record<DfdBeatId, number>> = { field: 4, problem: 5, collapse: 2 }
export function dfdSteps(id: DfdBeatId): number {
  return DFD_SUBSTEPS[id] ?? 1
}
/** The beat's word on the page's own rail (click = jump), the sub-menu's pattern. */
export const DFD_BEAT_LABELS: Record<DfdBeatId, string> = {
  slide: 'Slide',
  field: 'Field',
  problem: 'Problem',
  model: 'Model',
  solutions: 'Solutions',
  lab: 'Lab',
  collapse: 'Collapse',
  takeaway: 'Takeaway',
}

export const DFD_MEETING = {
  society: 'APS Division of Fluid Dynamics',
  meeting: 'DFD 2026',
  format: 'Interact',
  session: 'Geophysical and Astrophysical Fluid Dynamics',
  place: 'Orlando',
  date: '22 November 2026',
}

/** The talk's title = the paper's (PNAS, in revision). */
export const DFD_TITLE = 'From blistering to sliding: Ice-sheet stress perturbations from water injection to the bed'

/** Authors and affiliations exactly as the DFD submission lists them. */
export const DFD_AUTHORS: { name: string; aff: number; presenter?: boolean }[] = [
  { name: 'Joshua Rines', aff: 1, presenter: true },
  { name: 'Niall Coffey', aff: 1 },
  { name: 'Eojin Lee', aff: 1 },
  { name: 'Fiona Clerc', aff: 2 },
  { name: 'James Hilditch', aff: 1 },
  { name: 'Olivier Gagliardini', aff: 3 },
  { name: 'Laura Stevens', aff: 4 },
  { name: 'Ching-Yao Lai', aff: 1 },
]
export const DFD_AFFILIATIONS = ['Stanford University', 'Stony Brook University', 'University of Grenoble Alpes', 'University of Oxford']

/** The submitted abstract (behind an ABSTRACT pill on the slide; never on screen by default). */
export const DFD_ABSTRACT =
  'When meltwater lakes drain via hydrofracture, the injected water lubricates the ice-sheet bed and alters the ice-sheet stresses, potentially instigating fracture, draining neighboring lakes, and accelerating ice flow toward the ocean. As more lakes form with climate change, key open questions are how far inland, and when, surface-to-bed lake drainage will occur. Prior models predict long-range triggering between drainages, yet field observations show limited spatial extent. We provide a mechanistic understanding of stress-field evolution following lake drainage: an initial elastic response transitions to a viscous, sliding-induced stress perturbation whose reach is limited by basal friction. A stress-space diagram combining simulations with satellite observations further reveals the stress conditions required for a lake to drain through the ice to the bed.'


/** The takeaway (the director's to edit — written once here, read on the last beat; trusted HTML for the subscript). */
export const DFD_TAKEAWAY =
  'A slippery patch perturbs the stress by ½ρgαR over √(4ηH/c<sub>0</sub>): tension upstream, compression downstream — the 1-D ramp and exponential tails, bent in 2-D by lateral support into Bessel functions.'

/** The meeting's logo: the DFD 2026 mark re-grounded for the dark page
 *  (the white ground dropped, its greys lifted to the site's warm white;
 *  cinematic/data/dfd/ keeps the file). */
export const DFD_LOGO_KEY = 'dfd/aps_dfd_2026_dark.svg'

/** The page's LaTeX (cinematic/scene_addl/build_dfd_eqs.py → config/dfdEqs.ts sizes). */
export const DFD_EQ_PREFIX = 'dfd/eq_v2/'
export function dfdEqUrl(name: string): string {
  return mediaUrl(`${DFD_EQ_PREFIX}${name}.svg`)
}
