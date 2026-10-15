// Chapter 1's beat map — the ONE place its order and counts live.
//
// The chapter is a run of SEGMENTS, each `n` beats long. `?beat=N` is the
// running index across them. Every consumer (SectionCh1's beat engine,
// Explore's warm-mounts and in-canvas buttons, TheoryPanel's stages) asks
// this file where a segment starts, so inserting a beat never breaks a
// number somewhere else in code — only the number in the URL moves.
//
// To add a segment, add a line in talk order. A segment with n: 0 is
// skipped: its ch1Stage is -1, so `stage === S.<id>` never matches it
// (TheoryPanel's RANGE tests that start or end at it need a look too).
//
// The TheoryPanel owns every beat from 'field' through 'maps'; its stage
// index is the beat minus ch1First('field') (ch1Stage below).

export type Ch1SegmentId =
  | 'lakes' // the five drainage-class lakes on the globe
  | 'movie-nd' // the no-drainage lake's Sentinel-2 movie (popup, valid frames)
  | 'movie-hf' // North Lake's (HF) movie — NEXT then flies to the cross-section
  | 'reveal' // south-to-North-Lake knife reveal
  | 'drain' // hydrofracture drain
  | 'paint' // Elmer/Ice n = 1 τxx paint on the slab
  | 'field' // TheoryPanel: the idealized Stokes domain (seam entry lands here)
  | 'average' // depth-average wipe → SSA replaces Stokes, three zones drawn
  | 'patch-govern' // patch zone lit, the SSA's basal term drops
  | 'patch-velocity' // parabolic velocity solution + the u' curve (right axis)
  | 'patch-stress' // stress–velocity relation (arbitrary n)
  | 'patch-solution' // τxx patch solution rides the patch band
  | 'layers-govern' // outer zones lit, the full SSA returns
  | 'layers-velocity' // boundary-layer velocity solution
  | 'layers-solution' // boundary-layer stress solution, upstream + downstream
  | 'summary' // the stress alone across the domain, all three solutions
  | 'ensemble' // the n = 1 Elmer/Ice ensemble, dimensional
  | 'collapse' // nondimensional collapse + scales + master curve
  | 'loglog' // the collapse slides left; log-log scaling cards
  | 'acl' // absolute coupling length (explorable)
  | 'maps' // ACL + the α / h Greenland maps
  | 'twins' // two 3D Greenlands: ACL and max stress
  | 'takeaway' // the twins dimmed, the chapter's takeaway popped (TakeawayPop)

export const CH1_SEGMENTS: ReadonlyArray<{ id: Ch1SegmentId; n: number }> = [
  { id: 'lakes', n: 1 },
  { id: 'movie-nd', n: 1 },
  { id: 'movie-hf', n: 1 },
  { id: 'reveal', n: 1 },
  { id: 'drain', n: 1 },
  { id: 'paint', n: 1 },
  { id: 'field', n: 1 },
  { id: 'average', n: 1 },
  { id: 'patch-govern', n: 1 },
  { id: 'patch-velocity', n: 1 },
  { id: 'patch-stress', n: 0 }, // folded into patch-velocity (the τ–u relation lands with the u' profile)
  { id: 'patch-solution', n: 1 },
  { id: 'layers-govern', n: 1 },
  { id: 'layers-velocity', n: 1 },
  { id: 'layers-solution', n: 1 },
  { id: 'summary', n: 1 }, // the director asked for one more beat showing the stress alone across the full domain, with all three sections' solutions on it
  { id: 'ensemble', n: 1 },
  { id: 'collapse', n: 1 },
  { id: 'loglog', n: 1 },
  { id: 'acl', n: 1 },
  { id: 'maps', n: 1 },
  { id: 'twins', n: 1 },
  // The chapter's last beat (the director's rule for every chapter: on the
  // final NEXT everything fades into the background and the chapter's
  // main takeaway is highlighted): the twins stay up
  // under a dim, the `.tg-takeaway` line grows into a centred card.
  // NEXT from here = Chapter 2 (the twins' close hand-off).
  { id: 'takeaway', n: 1 },
]

/** Total beats in the chapter. */
export const CH1_BEATS = CH1_SEGMENTS.reduce((a, s) => a + s.n, 0)

/** First beat of a segment. */
export function ch1First(id: Ch1SegmentId): number {
  let b = 0
  for (const s of CH1_SEGMENTS) {
    if (s.id === id) return b
    b += s.n
  }
  return 0
}

/** Number of beats in a segment. */
export function ch1Count(id: Ch1SegmentId): number {
  return CH1_SEGMENTS.find((s) => s.id === id)?.n ?? 0
}

/** Last beat of a segment. */
export function ch1Last(id: Ch1SegmentId): number {
  return ch1First(id) + Math.max(1, ch1Count(id)) - 1
}

/** Which segment a beat falls in, and the step within it (0-based);
 *  null when the beat is out of range. */
export function ch1At(beat: number): { id: Ch1SegmentId; step: number } | null {
  let b = 0
  for (const s of CH1_SEGMENTS) {
    if (beat >= b && beat < b + s.n) return { id: s.id, step: beat - b }
    b += s.n
  }
  return null
}

/** The lakes stage: the lakes beat and its two movie steps (the
 *  director's framing) — the globe holds the same five-lake view on all
 *  three; only the popup changes. */
export function ch1IsLakesStage(beat: number): boolean {
  return beat >= ch1First('lakes') && beat <= ch1Last('movie-hf')
}

/** The lake each movie step opens (ESSD fig-4 ids). */
export const CH1_MOVIE_LAKE: Partial<Record<Ch1SegmentId, string>> = {
  'movie-nd': 'CW2019_1597', // No drainage
  'movie-hf': 'CW2019_1889', // Hydrofracture — North Lake
}

/** The twin Greenlands are on screen: the twins beat and the takeaway
 *  beat over them. */
export function ch1IsTwinsStage(beat: number): boolean {
  return beat >= ch1First('twins') && beat <= ch1Last('takeaway')
}

/** The TheoryPanel's beat span: 'field' through 'maps'. */
export const CH1_THEORY_FIRST = ch1First('field')
export const CH1_THEORY_LAST = ch1Last('maps')

/** TheoryPanel stage index of a segment's first beat (-1 when the
 *  segment is empty, so `stage === ch1Stage(id)` never matches it). */
export function ch1Stage(id: Ch1SegmentId): number {
  return ch1Count(id) > 0 ? ch1First(id) - CH1_THEORY_FIRST : -1
}
