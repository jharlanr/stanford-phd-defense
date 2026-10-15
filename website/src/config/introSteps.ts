// The Introduction's steps — the ONE place their order and count live.
// SectionMotivation drives them (the shared back/next pills bump it one
// step at a time); `?beat=N` deep-links to step N; anything that links to
// an Introduction step should use INTRO_STEP.<id>, never a bare number.
//
//   0 dims      the object, its measuring lines, the sea-level number
//   1 seasons   the month drape — SPEED, the RACMO runoff already behind
//               the land curve (the director cut the number of beats:
//               go from the Greenland size-comparison page straight to
//               the seasons page with the RACMO runoff already overlaid;
//               the Anomaly tab stays but is not on the deterministic NEXT
//               pathway, which goes right from speed to the fieldwork
//               map). FLOWS (the speed drape + comet trails as
//               its own beat) and ANOMALY (as a beat) are gone from the
//               path; the Speed | Anomaly switch is a VIEW on this step.
//   2 flyalong  the dive to the 2023 fieldwork map — lands on
//               the three tracks; 2 s after they appear the first clip
//               opens by itself (= NEXT)
//   3 clip1     the long NW–SE track's GoPro clip plays (GH010200)
//   4 clip2     the squiggly track NW of it (GH010212)
//   5 clip3     the north-westernmost track (GH010194)
//   6 timeline  the literature timeline, first visit — nothing highlighted
//   7–16 paper-<id>  the first visit's WALK (the director's design: each
//               NEXT highlights one paper, left to right, one at a
//               time): one NEXT per paper, INTRO_WALK below — each step
//               is that card's hover state (lift, gold pill, arcs, caption);
//               the walk stops at Stevens 2026, Rines 2026 is left for last
//  17 four-papers  the same timeline with the coupling step's four papers
//               lit together, each in ITS comparison-page colour (config/
//               couplingLength.ts COUPLING_PAPERS), every other card dimmed —
//               the beat where the talk dives a little deeper into these
//               four papers; NEXT hands the four cards to the coupling
//               page, which flies them from here to its top-left row
//  18 coupling  the "coupling length" end members on central-west Greenland
//               (built as a sample for the director's review): Christoffersen 2018 · Lai 2021
//               · Stevens 2024 · Stevens 2026, cards top-left, footprints on the ice
//  19 timeline2 the timeline again, Rines 2026 highlighted with "Chapter 1"
//               over it; next → Chapter 1
//
// Step 1 is one figure with a Speed | Anomaly switch; the
// switch is NOT a step (it was: Anomaly on the speed step = next) — it
// swaps the view and the camera on the same beat; NEXT goes to the field.
// Steps 3–5 (the director wanted NEXT to take the audience through each
// of the videos): one clip per NEXT on the same landed map; which
// clip is which lives in config/fieldwork.ts (FW_INTRO_CLIP_IDS, same
// order). A click on a track is not a step.
// The walk (steps paper-<id>): the timeline's papers left → right — its
// card order, i.e. config/timeline.ts sorted by `when` — up to Stevens
// 2026. Rines 2026, the last card, is not walked: the revisit (timeline2)
// highlights it after the coupling step. Ids are config/timeline.ts's.
export const INTRO_WALK = [
  'zwally2002',
  'price2008',
  'das2008',
  'schoof2010',
  'leeson2015',
  'stevens2015',
  'christoffersen2018',
  'lai2021',
  'stevens2024',
  'stevens2026',
] as const
export type IntroWalkPaper = (typeof INTRO_WALK)[number]

export const INTRO_STEP_IDS = [
  'dims',
  'seasons',
  'flyalong',
  'clip1',
  'clip2',
  'clip3',
  'timeline',
  ...INTRO_WALK.map((p) => `paper-${p}` as const),
  'four-papers',
  'coupling',
  'timeline2',
] as const
export type IntroStepId = (typeof INTRO_STEP_IDS)[number]

export const INTRO_STEP = Object.fromEntries(INTRO_STEP_IDS.map((id, i) => [id, i])) as Record<IntroStepId, number>
export const INTRO_STEP_COUNT = INTRO_STEP_IDS.length

/** The paper a walk step highlights (null = not a walk step). */
export function introWalkPaper(step: number): IntroWalkPaper | null {
  const id = INTRO_STEP_IDS[step]
  return id?.startsWith('paper-') ? (id.slice(6) as IntroWalkPaper) : null
}
