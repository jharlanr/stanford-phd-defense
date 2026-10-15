// The sub-menu's LANDMARKS — the few major beats of each beat section,
// marked as notches on the thin bar that hangs under the ribbon while
// you are inside that section (the director's brief: a sub-menu with
// the major beats marked so the user can jump to any given beat — about
// five main beats per chapter, with very short one- or two-word
// descriptions next to their notch locations).
//
// One ordered list per beat section: `{ id, label, beat }`. `beat` goes
// through each section's own registry (INTRO_STEP.<id>, ch1First(
// '<segment>'), CH2_BEAT.<id>, ch3First('<segment>')), so adding a beat
// anywhere moves the notch with it. Clicking a notch lands on that
// beat the way a `?beat=N` deep link does (Explore.vue, jumpToBeat).
// The counts (for the progress fill) come from the same registries —
// never a number typed here. Each chapter's last beat is its `takeaway`,
// lit under Implications with the bead at the bar's end.
import type { SectionId } from './sections'
import { INTRO_STEP, INTRO_STEP_COUNT } from './introSteps'
import { CH2_BEAT, CH2_BEATS } from './ch2Beats'
import { CH3_BEATS, ch3First } from './ch3Beats'

// Chapter 1's beats come from its registry (config/ch1Beats.ts); the
// landmark ids below are the registry's segment ids.
import { ch1First as ch1, CH1_BEATS } from './ch1Beats'

export interface Landmark {
  id: string
  /** One or two words, set in small caps beside the notch. */
  label: string
  /** The beat the notch jumps to (and lights from). */
  beat: number
}

export interface SectionLandmarks {
  /** The section's beat count — the fill runs 0 → count − 1. */
  count: number
  landmarks: Landmark[]
}

export const LANDMARKS: Partial<Record<SectionId, SectionLandmarks>> = {
  introduction: {
    count: INTRO_STEP_COUNT,
    landmarks: [
      { id: 'dims', label: 'Ice sheet', beat: INTRO_STEP.dims },
      { id: 'seasons', label: 'Seasons', beat: INTRO_STEP.seasons }, // speed (+ the Anomaly tab, which is a view, not a beat)
      { id: 'flyalong', label: 'Field', beat: INTRO_STEP.flyalong }, // the landing + the three clips
      { id: 'timeline', label: 'Literature', beat: INTRO_STEP.timeline }, // timeline · its ten-paper walk · the four papers lit · coupling · timeline again
    ],
  },
  chapter1: {
    count: CH1_BEATS,
    landmarks: [
      { id: 'lakes', label: 'Lakes', beat: ch1('lakes') }, // the five drainage classes, the ND + HF movies, reveal, drain
      { id: 'paint', label: 'Model', beat: ch1('paint') }, // the Elmer τxx paint, the idealized domain
      { id: 'average', label: 'Theory', beat: ch1('average') }, // depth average → SSA → the derivation
      { id: 'ensemble', label: 'Results', beat: ch1('ensemble') }, // ensemble · collapse · log-log · ACL
      { id: 'maps', label: 'Implications', beat: ch1('maps') }, // the Greenland maps + twin globes + the takeaway beat (the bead's last stop)
    ],
  },
  chapter2: {
    count: CH2_BEATS,
    landmarks: [
      { id: 'lakes', label: 'Lakes', beat: CH2_BEAT.lakes },
      { id: 'model', label: 'Model', beat: CH2_BEAT.outline }, // the marker, the zoom, pre · post imagery
      { id: 'results', label: 'Results', beat: CH2_BEAT['pre-viscous-t1'] }, // viscous pre, elastic post · Δσ_t1, then viscous (in time order) (σ_t2 → Additional Work)
      // RESULTS runs through the second center lake (1951: imagery ·
      // viscous · bed · the ensemble teaser) and the population's stress
      // spaces, up to THEORY (the director took TOPOGRAPHY out of the menu
      // bar altogether — everything is under RESULTS until THEORY; before
      // that a Topography landmark sat on `pre/2`).
      // (Earlier the population sat under IMPLICATIONS; with the theory
      // between them, one landmark cannot carry both.)
      // The idealized slab: Elmer/Ice against the
      // shallow-stream theory — the block, its depth average, the three panels.
      { id: 'theory', label: 'Theory', beat: CH2_BEAT.slab },
      // The chapter in one figure, then its takeaway popped over it (the
      // chapter's last beat).
      { id: 'implications', label: 'Implications', beat: CH2_BEAT.implications },
    ],
  },
  chapter3: {
    count: CH3_BEATS,
    landmarks: [
      { id: 'callouts', label: 'Lakes', beat: ch3First('callouts') }, // five lakes · the population map
      { id: 'label', label: 'Labels', beat: ch3First('label') },
      { id: 'irr', label: 'Agreement', beat: ch3First('irr') },
      { id: 'network', label: 'Model', beat: ch3First('network') }, // the architecture + its 13 blocks
      { id: 'training', label: 'Results', beat: ch3First('training') }, // five beats: the five-class run plays · its best + TEST · hard pairs · the four-class run plays · its best + TEST
      { id: 'implications', label: 'Implications', beat: ch3First('implications') }, // rate → mechanism, then the takeaway popped over it (the last beat)
    ],
  },
}

/** The landmark a beat falls under: the last one at or before it. */
export function currentLandmark(ls: Landmark[], beat: number): number {
  let k = -1
  ls.forEach((l, i) => {
    if (l.beat <= beat) k = i
  })
  return k
}

/**
 * Where each notch sits along the bar (0 … 1). Proportional to its beat
 * over the section — except that neighbouring notches keep at least
 * `minGap` apart, so labels never collide where beats bunch up (Ch.3's
 * first five beats before its fourteen network beats, the Introduction's
 * first three steps). `minGap` is one fraction for every pair, or one per
 * neighbouring pair (BeatLandmarks passes its labels' measured widths);
 * `lo` / `hi` keep the end labels inside the bar's rounded ends. A
 * forward pass pushes crowded notches right, a backward pass pulls any
 * that overran the end back in.
 */
export function notchPositions(s: SectionLandmarks, minGap: number | number[] = 0.14, lo = 0, hi = 1): number[] {
  const last = Math.max(1, s.count - 1)
  const gap = (i: number) => (typeof minGap === 'number' ? minGap : minGap[i] ?? 0.14)
  const p = s.landmarks.map((l) => Math.min(hi, Math.max(lo, l.beat / last)))
  for (let i = 1; i < p.length; i++) p[i] = Math.max(p[i], p[i - 1] + gap(i - 1))
  if (p.length && p[p.length - 1] > hi) p[p.length - 1] = hi
  for (let i = p.length - 2; i >= 0; i--) p[i] = Math.min(p[i], p[i + 1] - gap(i))
  return p.map((v) => Math.max(lo, v))
}

/**
 * The progress fill for a beat (0 … 1), piecewise-proportional between
 * the notches: a landmark's beat lands exactly on its notch, the beats
 * between two landmarks share the stretch between their notches, and
 * the last landmark's beats run on to the bar's end (the last beat).
 */
export function beatFraction(s: SectionLandmarks, beat: number, pos = notchPositions(s)): number {
  const last = Math.max(1, s.count - 1)
  const b = Math.min(last, Math.max(0, beat))
  const knots: [number, number][] = s.landmarks.map((l, i) => [l.beat, pos[i]])
  if (!knots.length || knots[0][0] > 0) knots.unshift([0, 0])
  if (knots[knots.length - 1][0] < last) knots.push([last, 1])
  for (let i = 1; i < knots.length; i++) {
    const [b0, f0] = knots[i - 1]
    const [b1, f1] = knots[i]
    if (b <= b1) return b1 === b0 ? f1 : f0 + ((b - b0) / (b1 - b0)) * (f1 - f0)
  }
  return 1
}
