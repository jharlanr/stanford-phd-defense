// Chapter 3's beat map — the ONE place its order and counts live.
//
// The chapter is a run of SEGMENTS, each `n` beats long. `?beat=N` is the
// running index across them. Every consumer (SectionCh3, the
// Terminal-Bench ladder's doors) asks this file where a segment starts,
// so adding a beat to one segment never breaks a deep link's meaning in
// code — only the number in the URL moves.
//
// To add beats to a segment, change ITS `n` on ITS line and nothing else.
// To add a segment, add a line in talk order.

export type Ch3SegmentId =
  | 'callouts'
  | 'map'
  | 'label'
  | 'irr'
  | 'network'
  | 'training'
  | 'implications'
  | 'takeaway'

export const CH3_SEGMENTS: ReadonlyArray<{ id: Ch3SegmentId; n: number }> = [
  { id: 'callouts', n: 1 }, // the five example lakes, each with its season
  { id: 'map', n: 1 }, // the labeled population on the map
  { id: 'label', n: 1 }, // a label made live
  { id: 'irr', n: 2 }, // inter-rater agreement · then HF–MD / MD–LD outlined
  { id: 'network', n: 16 }, // the architecture, its 13 blocks in forward order, the class head again (training plays on it), then the same head in the four-class taxonomy (its training plays)
  // SIX beats (the director's sequence: start at the beginning of training,
  // play through the 400 epochs, then on the NEXT click roll back to show
  // the TEST at the best-validation epoch — and the same for the 4-class):
  //   0 five-class — arriving plays training 1→400, rests at 400
  //   1 NEXT rolls back to the best-val epoch (189): matrices pinned, TEST
  //   2 the hard pairs
  //   3 four-class — the merge, then its run plays 1→400, rests at 400
  //   4 NEXT rolls back to its best epoch (363): matrices pinned, TEST
  //   5 the four-class hard pair: the middle 2×2 outlined
  { id: 'training', n: 6 },
  { id: 'implications', n: 1 }, // rate → mechanism, the same lakes + the takeaway
  // The chapter's last beat (the director's rule for every chapter: on the
  // final NEXT everything fades into the background and the chapter's
  // main takeaway is highlighted): the implications page
  // stays (ribbons rolled out), dimmed; its takeaway line pops into a
  // centred card (Explore's TakeawayPop). NEXT from it = the Conclusion.
  { id: 'takeaway', n: 1 },
]

export const CH3_BEATS = CH3_SEGMENTS.reduce((a, s) => a + s.n, 0)

/** First beat of a segment. */
export function ch3First(id: Ch3SegmentId): number {
  let b = 0
  for (const s of CH3_SEGMENTS) {
    if (s.id === id) return b
    b += s.n
  }
  return 0
}

/** Number of beats in a segment. */
export function ch3Count(id: Ch3SegmentId): number {
  return CH3_SEGMENTS.find((s) => s.id === id)?.n ?? 0
}

/** Which segment a beat falls in, and the step within it (0-based);
 *  null when the beat is out of range. */
export function ch3At(beat: number): { id: Ch3SegmentId; step: number } | null {
  let b = 0
  for (const s of CH3_SEGMENTS) {
    if (beat >= b && beat < b + s.n) return { id: s.id, step: beat - b }
    b += s.n
  }
  return null
}

/** The implications page is on screen: its own beat and the takeaway
 *  beat over it (one Ch3Implications instance across both). */
export function ch3IsImplicationsStage(beat: number): boolean {
  const id = ch3At(beat)?.id
  return id === 'implications' || id === 'takeaway'
}
