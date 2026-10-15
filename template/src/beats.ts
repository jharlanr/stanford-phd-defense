// THE BEAT REGISTRY — the one place the talk's order lives.
//
// A beat is one press of NEXT. The talk is this ordered list, and the
// current position is an index into it. Everything else in the app asks
// "which beat am I on?" by NAME (`phase(index) === 'ch1-highlight'`), never
// by number. That rule is what lets you insert, remove or reorder beats
// here without touching the components: the numbers in the URL shift, the
// names do not, so no `if (beat === 4)` anywhere can go stale.
//
// To add a beat: add a line below, in talk order, then teach Stage.vue
// what the object does on it. Nothing else changes.

export interface Beat {
  /** Stable name, used in code. Keep it short and kebab-case. */
  id: string
  /** The section it belongs to; the ribbon groups consecutive beats by it. */
  section: string
  /** Optional caption shown under the stage. */
  title?: string
}

export const BEATS = [
  { id: 'intro-title', section: 'Introduction', title: 'A title, and nothing else on stage.' },
  { id: 'intro-question', section: 'Introduction', title: 'The object arrives — the question the talk asks.' },
  { id: 'intro-object', section: 'Introduction', title: 'Name its parts.' },
  { id: 'ch1-zoom', section: 'Chapter 1', title: 'Move in on the part this chapter is about.' },
  { id: 'ch1-highlight', section: 'Chapter 1', title: 'Light the piece; dim the rest.' },
  { id: 'ch1-annotate', section: 'Chapter 1', title: 'Annotate a measurement.' },
  { id: 'ch1-deeper', section: 'Chapter 1', title: 'Offer a door to the detail.' },
  { id: 'takeaway', section: 'Takeaway', title: 'Everything fades; one sentence stays.' },
] as const satisfies readonly Beat[]

/** The union of every id above — a typo in `phase(i) === '...'` is a type error. */
export type BeatId = (typeof BEATS)[number]['id']

/** Section names in talk order, each once. */
export const SECTIONS: readonly string[] = [...new Set(BEATS.map((b) => b.section))]

/** Index of a named beat (−1 if unknown — but the type makes that hard). */
export function beatIndex(id: BeatId): number {
  return BEATS.findIndex((b) => b.id === id)
}

/** The name of the beat at an index — the question components ask. */
export function phase(index: number): BeatId {
  return BEATS[clampIndex(index)].id
}

/** The section a beat belongs to. */
export function sectionOf(index: number): string {
  return BEATS[clampIndex(index)].section
}

/** First beat of a section (where a click on its ribbon label lands). */
export function sectionStart(section: string): number {
  return Math.max(0, BEATS.findIndex((b) => b.section === section))
}

/** Keep any index inside the list. */
export function clampIndex(index: number): number {
  return Math.min(BEATS.length - 1, Math.max(0, Math.trunc(index) || 0))
}
