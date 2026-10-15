import type { Component } from 'vue'
import { markRaw } from 'vue'
import Ch1Thumb from '../components/menu_thumbs/Ch1Thumb.vue'
import Ch2Thumb from '../components/menu_thumbs/Ch2Thumb.vue'
import Ch3Thumb from '../components/menu_thumbs/Ch3Thumb.vue'
import ConclusionThumb from '../components/menu_thumbs/ConclusionThumb.vue'
import FlybyThumb from '../components/menu_thumbs/FlybyThumb.vue'

// ---------------------------------------------------------------------
// SINGLE SOURCE OF TRUTH for the talk's structure. The router table,
// Explore.vue's menu/nav/advance ordering, and SectionStub's blurbs all
// derive from this array — add or reorder a section HERE and every
// consumer follows. (Chapter identity was once duplicated across five
// files; this registry replaced them.)
//
// Talk structure (defense: October 9, 2026):
//   Introduction → Ch.1 (JOG, 1D slippery-patch stress) →
//   Ch.2 (PNAS, 3D viscous + elastic) → Ch.3 (ESSD, the drainage-
//   classification dataset) → Conclusion.
// After the divider: Additional Work (a card grid: the
//   Terminal-Bench Science task, MGSIM, the lake-vision classifier, …),
//   Acknowledgements, Repos (the software-repositories table), References.
// (The Extras side door folded into the Additional-Work fieldwork door;
//  the Introduction opens on its clip.)
//
// `kind` controls placement:
//   primary — big menu cards + talk spine
//   aux     — small text buttons under the menu's gold rule
//   side    — (unused; kept for a future off-spine card)
// `group` says which side of the ribbon's divider a section sits on:
//   the thesis's talk (Introduction … Conclusion)
//   or everything after it. The ribbon draws its break wherever `group`
//   changes — never at a hand-placed index. Independent of `kind`.
//   (Earlier the Acknowledgements counted as 'thesis' and the
//   break fell after them.)
// `status` is the publication stage a chapter carries in the ribbon:
//   a bare stage word, edited here as it changes.
// `venue` is the journal, in its own short form (JoG, PNAS, ESSD). The
//   menu card reads "Chapter 1" over "published · JoG" (the director's
//   wording: just "Chapter 1", "Chapter 2" and so on, with the stage and
//   journal below); the ribbon keeps "Chapter 1 · JoG" + stage.
//   Kept out of `label` so the path pills' "Ch. 1" parsing and every
//   other label consumer see the bare chapter name.
// ---------------------------------------------------------------------

export type SectionId =
  | 'introduction'
  | 'chapter1'
  | 'chapter2'
  | 'chapter3'
  | 'conclusion'
  | 'acknowledgements'
  | 'additional-work'
  | 'repos'
  | 'references'

export interface SectionDef {
  id: SectionId
  /** Route path ('' means the id doubles as the path). */
  path: string
  label: string
  subtitle?: string
  /** The chapter's title in the thesis (main.tex `\chapter`), shown on
   *  the card over its landing beat — "Chapter 1: <title>"
   *  (ChapterTitleCard.vue). Chapters only. */
  title?: string
  /** One-line blurb shown by SectionStub while the section is unbuilt. */
  hint: string
  kind: 'primary' | 'aux' | 'side'
  /** The thesis proper, or the work beyond it (see the header note). */
  group: 'thesis' | 'beyond'
  /** Publication stage shown quietly beside the label in the ribbon. */
  status?: string
  /** Journal short form (JoG, PNAS, ESSD) — the card's line under the title. */
  venue?: string
  /** Menu-card hover thumbnail (primary + side sections only). */
  thumb?: Component
}

export const SECTIONS: SectionDef[] = [
  {
    id: 'introduction',
    path: '/introduction',
    label: 'Introduction',
    hint: 'The Greenland Ice Sheet at scale, the supraglacial lakes that pock its ablation zone, and the question that drives the dissertation: can one lake drainage trigger another?',
    kind: 'primary',
    group: 'thesis',
    // The director's opening: the talk opens on the fieldwork
    // footage, so the card carries the helicopter flyby (the same
    // 10-second window the Extras side door used); MotThumb retired.
    thumb: markRaw(FlybyThumb),
  },
  {
    id: 'chapter1',
    path: '/chapter1',
    label: 'Chapter 1',
    subtitle: 'Slippery-patch stress — 1D theory',
    title: 'Longitudinal stress induced by basal slippery patch',
    hint: 'Chapter 1 (JOG): stress induced by a finite basal slippery patch — a 1D analytical viscous model validated against 2D full-Stokes simulations, and the coupling-length insight.',
    kind: 'primary',
    group: 'thesis',
    status: 'published',
    venue: 'JoG',
    thumb: markRaw(Ch1Thumb),
  },
  {
    id: 'chapter2',
    path: '/chapter2',
    label: 'Chapter 2',
    subtitle: 'Slippery-patch stress — 3D models',
    title: '3D numerical models of stress perturbations induced by basal meltwater',
    hint: 'Chapter 2 (PNAS): stress induced by a finite slippery patch in 3D — numerical viscous and elastic models, principal-stress fields draped on real Greenland topography.',
    kind: 'primary',
    group: 'thesis',
    status: 'in revision',
    venue: 'PNAS',
    thumb: markRaw(Ch2Thumb),
  },
  {
    id: 'chapter3',
    path: '/chapter3',
    label: 'Chapter 3',
    subtitle: 'Classifying lake drainage events',
    // The thesis's own short form (its table-of-contents title); the full
    // chapter title is the ESSD paper's, 150 characters — too long for a
    // card that must stay small.
    title: 'Toward automated classification of lake drainage mechanism',
    hint: 'Chapter 3 (ESSD): how Greenland’s lakes drain — a labeled Sentinel-2 timestack dataset of 1,679 drainage events, the expert protocol behind the labels, and the baseline classifiers.',
    kind: 'primary',
    group: 'thesis',
    status: 'in final revision',
    venue: 'ESSD',
    thumb: markRaw(Ch3Thumb),
  },
  {
    id: 'conclusion',
    path: '/conclusion',
    label: 'Conclusion',
    hint: 'The synthesis: what slippery-patch stress coupling and the drainage record together say about cascading lake drainages on a warming ice sheet.',
    kind: 'primary',
    group: 'thesis',
    thumb: markRaw(ConclusionThumb),
  },
  // Additional Work comes BEFORE the Acknowledgements, and the ribbon's
  // divider falls after the Conclusion (the director wanted Additional
  // Work ahead of the Acknowledgements and the menu's vertical divider
  // bar after the Conclusion). The path follows the
  // registry (config/sitePath.ts): Conclusion → Additional Work →
  // Acknowledgements → Repos → References.
  {
    id: 'additional-work',
    path: '/additional-work',
    label: 'Additional Work',
    hint: 'Beyond the chapters: the Chapter-3 labeling workflow as a Terminal-Bench Science task for AI agents, geostatistical bed-topography ensembles (C&G, published), the lake-drainage classifier at scale (lake-vision), fracture and stream mapping in sub-metre imagery (AGU 2024, led by Iona Xia), the 2023 Greenland field campaign and its publication, and the Princeton COP27 delegation.',
    kind: 'aux',
    group: 'beyond',
  },
  {
    id: 'acknowledgements',
    path: '/acknowledgements',
    label: 'Acknowledgements',
    hint: 'Advisors, collaborators, field crew, staff.',
    kind: 'aux',
    // 'beyond': the one divider sits after the
    // Conclusion, so everything right of it is one group.
    group: 'beyond',
  },
  {
    id: 'repos',
    path: '/repos',
    label: 'Repos',
    hint: 'Software Repositories: the code behind the dissertation, each repo linked with the work it belongs to.',
    kind: 'aux',
    group: 'beyond',
  },
  {
    id: 'references',
    path: '/references',
    label: 'References',
    hint: 'Papers, datasets, code repositories, and the broader body of work this dissertation builds on.',
    kind: 'aux',
    group: 'beyond',
  },
]

export const primarySections = SECTIONS.filter((s) => s.kind === 'primary')
export const auxSections = SECTIONS.filter((s) => s.kind === 'aux')

/** Sections that appear in the top-nav pill row (everything on-spine). */
export const navSections = SECTIONS.filter((s) => s.kind !== 'side')

export function sectionById(id: string | null | undefined): SectionDef | undefined {
  return SECTIONS.find((s) => s.id === id)
}

// Legacy URLs from the earlier site structure. Old deep links (talks,
// notes, browser history) land on the nearest current equivalent.
export const LEGACY_REDIRECTS: Record<string, string> = {
  '/motivation': '/introduction', // renamed
  '/chapter4': '/additional-work', // JSTARS: merged into Ch.3, then its own card
  '/chapter5': '/additional-work', // Geostats demoted from chapter
  '/resources': '/references', // renamed
  '/extras': '/additional-work/fieldwork', // the side door folded into the fieldwork door
}
