// The site's ONE linear path (the director's rule: the BACK and NEXT
// buttons are always there, in the same spot at the same size and font,
// so the user has a deterministic path through the website).
//
// Every page shows the same two pills (Explore.vue's `.beat-nav`), and
// both read their destination from here:
//
//   menu ← Introduction (steps, config/introSteps.ts) → Ch.1 (beats) → Ch.2 → Ch.3 →
//   Conclusion → Additional Work → Acknowledgements → Repos →
//   References → menu
//   (Additional Work before the Acknowledgements.)
//
// The order IS the section registry's (`navSections`, config/sections.ts)
// — add or move a section there and the path follows. A section that has
// internal beats (the Introduction and the three chapters) steps through
// them first; `back` at its first beat lands on the PREVIOUS page's LAST
// beat (`?beat=last`), so the path retraces exactly.
// Each chapter's last beat is its `takeaway` (the page dimmed,
// the takeaway popped — TakeawayPop.vue), so `?beat=last` lands there.
//
// The Additional-Work door pages (MGSIM, Terminal-Bench, fieldwork,
// fracture, label, revisit) are side rooms under Additional Work: `back` returns to the
// Additional-Work grid, `next` goes on to the page after it (the
// Acknowledgements). Their
// own "← doors" pills stay as they are. EXCEPT when a page was reached
// through a door (the door trail below): then `back` returns to exactly
// where the door was used.
// The revisit page ("Revisiting lake drainage papers") has steps of its own
// (the paper's days, then every lake): while it has one, the pills step it
// (Explore.vue `revisitNav`); on its first day `back` is as above, and from
// its lake grid `next` is.
//
// The ends: `back` on the Introduction's first step and `next` on the
// last page (References) both go to the menu, and say so ("← menu",
// "menu →") in the same footprint.
import { navSections, type SectionId } from './sections'

/** Sections whose pages have internal beats driven by the shared pills. */
// The Acknowledgements joined (the split-out steps, ACK_STEPS in
// config/acknowledgements.ts). The Conclusion joined too (the director
// wanted a NEXT path through the conclusions that simply steps
// through each chapter's takeaway) — rest, then one step per
// takeaway (SectionConclusion.vue).
export const BEAT_SECTIONS: readonly SectionId[] = ['introduction', 'chapter1', 'chapter2', 'chapter3', 'conclusion', 'acknowledgements']

export function isBeatSection(id: SectionId | null | undefined): boolean {
  return !!id && BEAT_SECTIONS.includes(id)
}

/** The previous / next page on the path; null = the menu. */
export function pathPrev(id: SectionId | null | undefined): SectionId | null {
  const i = navSections.findIndex((s) => s.id === id)
  return i > 0 ? navSections[i - 1].id : null
}
export function pathNext(id: SectionId | null | undefined): SectionId | null {
  const i = navSections.findIndex((s) => s.id === id)
  return i >= 0 && i < navSections.length - 1 ? navSections[i + 1].id : null
}

/**
 * The next pill's label when it leaves the page. Plain "next" unless the
 * destination is a chapter ("Ch. 2") or the menu — the pill has a fixed
 * 6.4rem footprint, so longer names ("Acknowledgements") never appear.
 */
export function leaveLabel(dest: SectionId | null): string {
  if (dest === null) return 'menu'
  const label = navSections.find((s) => s.id === dest)?.label ?? ''
  const m = /^Chapter\s+(\d+)/.exec(label)
  return m ? `Ch. ${m[1]}` : 'next'
}

// ── The door trail (the director's rule: when a button such as SEE MORE
// FIELDS leads into the additional work, BACK must return to the page
// that button was on, so the user never gets lost in the website).
//
// A DOOR is any in-site link that is not the path itself — MORE DETAILS,
// SEE MORE FIELDS, DIVE DEEPER, the bed-ensemble card, MAKE YOUR OWN
// LABELS, the `[…]` reference links, the Additional-Work cards, the
// Terminal-Bench ladder's chapter rows, the Repos pills. Explore.vue
// classifies every navigation (no door component knows about this): the
// pills, the ribbon and the menu are the PATH and clear the trail; the
// door pages' own exit pills pop it when they lead where the trail
// leads, else clear it; anything else that changes page is a door and
// pushes where it was used from — the route plus the beat on screen, so
// BACK lands on exactly that beat. The trail rides `history.state`, so a
// reload of the destination keeps it (a copied URL does not, and simply
// gets the page's usual BACK). Door from a door → one level per BACK.
export const DOOR_TRAIL_KEY = 'doorTrail'

/** Where a door was used from (a router location) + the beat it landed on. */
export interface DoorStop {
  name: string
  params: Record<string, string | string[]>
  query: Record<string, string | null | (string | null)[]>
  hash: string
  /** the destination's `?beat=` when the door led into a beat page */
  landed: string | null
}

export function readDoorTrail(state: unknown): DoorStop[] | null {
  const t = (state as Record<string, unknown> | null)?.[DOOR_TRAIL_KEY]
  if (!Array.isArray(t)) return null
  return t.filter((s): s is DoorStop => !!s && typeof (s as DoorStop).name === 'string')
}

/** Two route names that are one page for the trail: a tab inside it
 *  (the Additional-Work grid ⇄ its deeper-dive stop) is not a door. */
export function sameDoorPage(a: string, b: string): boolean {
  const grid = (n: string) => n === 'additional-work' || n === 'additional-work-deeper'
  return a === b || (grid(a) && grid(b))
}

/**
 * A beat section's `?beat=` deep link: a number in range, or `last`
 * (what `back` from the next page asks for). Anything else → 0.
 */
export function parseBeatParam(raw: unknown, beats: number): number {
  if (raw === 'last') return beats - 1
  const b = parseInt(String(raw ?? '0'), 10)
  return Number.isFinite(b) && b >= 0 && b < beats ? b : 0
}
