// "Deeper dive into the chapters" — the Additional-Work page the director
// keeps for the committee's deeper questions (his bonus or backup slides,
// one set per chapter). One scrollable
// page per chapter at /additional-work/deeper/<chapter>; Chapter 1's
// log-log and twins beats link to /additional-work/deeper/chapter1.
//
// This is a REFERENCE page, so each figure carries a one-line caption —
// the gist of the paper's own caption, never new interpretation.
//
// Chapter 1's figures are the JoG paper's own figure files (the accepted
// version, JOG-2026-0047), whole or cropped along their white gutters by
// cinematic/scene_addl/build_deeper_ch01.py → R2 addl/deeper/ch01/.
// Tables are the paper's Tables 1 and 2, typeset here.
//
// Chapter 2 opens on the FIELD VIEWER (#fields,
// Ch2FieldViewer.vue — every surface field of the SI overview figures for
// the seven lakes and both models), then the thesis's stress spaces
// (#stress-spaces) with the two tables behind them, then the PNAS paper's
// main-text figures and the rest of the chapter's figures. Figure files:
// the thesis zip's Chapter 2 PNGs and the PNAS Overleaf zips, baked by
// cinematic/scene_addl/build_deeper_ch02.py → R2 addl/deeper/ch02/figs/.
// Tags: chapter-numbered (Fig. 2.20, Table 2.1) = the thesis's numbering;
// Fig. 1–5 / Fig. S1–S26 = the PNAS paper's and its SI's. Every figure is
// whole except SI Fig. S6, a tall single column re-set as two columns of
// its own rows (each with its own colour bar) so it reads at one screen.
//
// Chapter 3 (the director asked for every figure of his most recent ESSD
// revised submission): all ten figures of essd-2026-406 MANUSCRIPT
// VERSION 3 (the September 2026 revision), in the paper's order, whole, baked by
// cinematic/scene_addl/build_deeper_ch03.py → R2 addl/deeper/ch03/figs/
// (essd_v3_* — a later revision gets new names). Captions are the
// version-3 PDF's, trimmed; credits name only what the caption credits.

import { REFERENCES, type Reference } from './references'
import type { Ch2RelBlock } from './ch2StressRel'

export type DeeperChapter = 'chapter1' | 'chapter2' | 'chapter3'
export const DEEPER_CHAPTERS: DeeperChapter[] = ['chapter1', 'chapter2', 'chapter3']

export function isDeeperChapter(v: unknown): v is DeeperChapter {
  return typeof v === 'string' && (DEEPER_CHAPTERS as string[]).includes(v)
}

export interface DeeperFigure {
  /** Anchor id (unique within a chapter). */
  id: string
  /** Where it sits in the paper: "Fig. 3", "Fig. 4 c, d, g, h", "Table 2". */
  tag: string
  /** Short entry for the page's figure index. */
  short: string
  /** Garamond title — the figure's subject. Trusted static HTML (only
   *  #superposition uses any: its σ^V_pre + Δσ^E). */
  title: string
  /** One line, the paper's own caption in gist. Trusted static HTML
   *  (italics, sub/superscripts only). Absent = no caption (the stress
   *  relations: the heading is the label, the director narrates). */
  caption?: string
  /** Who made the figure, when it is not the presenter's own (shown as its
   *  own line under the caption, at the director's request) — or, for
   *  Chapter 3, the data sources the paper's caption credits. */
  credit?: string
  /** R2 key of the image (absent for a table). */
  src?: string
  /** The baked image's pixel size — reserves its box before it loads. */
  size?: [number, number]
  alt?: string
  /** A typeset table instead of an image. */
  table?: 'params' | 'kappa' | 'ch2-lakes' | 'ch2-elastic' | 'ch2-viscous'
  /** An interactive viewer instead of an image (Chapter 2's fields). */
  viewer?: 'ch2-fields' | 'ch2-slab' | 'ch2-sequence'
  /** A door to another page instead of a figure (the APS DFD 2026 presentation). */
  door?: 'dfd'
  /** A live plot instead of an image (Chapter 2's elastic stress space
   *  from phase_space_v2.json, Ch2ElasticStressSpaces.vue;
   *  the elastic | viscous population pair, Ch2PopulationSpaces.vue). */
  plot?: 'ch2-ss-elastic' | 'ch2-ss-both'
  /** Typeset equations instead of an image (Chapter 2's stress-space
   *  definitions, Ch2StressEqs.vue). */
  eqs?: 'ch2-stress-defs' | 'ch2-superposition' | 'ch1-derivation' | 'ch1-glen' | 'ch3-metrics'
  /** One block of Chapter 2's stress relations (#stress-relations),
   *  typeset — config/ch2StressRel.ts, Ch2StressRelations.vue. */
  relations?: Ch2RelBlock
  /** The paper itself (the director wanted one click to open each paper's
   *  PDF in a new browser tab — the PDF itself, not a link to wherever the
   *  manuscript is hosted online): the PDF on R2 under papers/ (immutable —
   *  a new version is a new name), its first page baked as the cover. */
  pdf?: DeeperPdf
  /** The rail index's tag when shortTag(tag) would not fit. */
  indexTag?: string
  /** Show the image no wider than this (CSS px) — for small source figures. */
  maxWidth?: number
}

export interface DeeperPdf {
  /** R2 key of the PDF. */
  key: string
  /** R2 key of the page-1 cover (WebP) and its pixel size. */
  cover: string
  coverSize: [number, number]
  pages: number
  /** Shown as "N MB" (a string: keeps "5.0"). */
  mb: string
  /** One line under the button: which version this is. */
  note?: string
}

export interface DeeperGroup {
  label: string
  /** Anchor id for the group (#<id> on the URL lands on its label). */
  id?: string
  figures: DeeperFigure[]
}

export interface DeeperPage {
  id: DeeperChapter
  /** "Chapter 1" — the switch's label. */
  label: string
  /** Journal short form. */
  venue: string
  /** Publication stage (the ribbon's word). */
  status: string
  paper: Reference
  groups: DeeperGroup[]
  /** Stub pages: how many empty frames to draw. */
  placeholders?: number
}

function ref(id: string): Reference {
  const r = REFERENCES.find((x) => x.id === id)
  if (!r) throw new Error(`deeperDive: no reference ${id}`)
  return r
}

const K = 'addl/deeper/ch01/'

const CH1_GROUPS: DeeperGroup[] = [
  // The paper's PDF opens in a new tab — the FIRST
  // section of every chapter's dive (the director's order).
  {
    label: 'The paper',
    id: 'paper',
    figures: [
      {
        id: 'pdf',
        tag: 'J. Glaciol. 72, e76',
        indexTag: 'PDF',
        short: 'The paper',
        title: 'The paper',
        // The director supplied the file: the published Cambridge article (15 pp,
        // Appendix B numbered B.1–B.22), hand-dropped, no recompression
        // (its images are ~265 ppi). v1 was the accepted manuscript (38 pp).
        pdf: {
          key: 'papers/rines2026_jog_v2.pdf',
          cover: 'papers/rines2026_jog_cover_v2.webp',
          coverSize: [912, 1213],
          pages: 15,
          mb: '5.3',
          note: 'The published article — Journal of Glaciology 72, e76 (2026).',
        },
      },
    ],
  },
  {
    label: 'Derivation',
    id: 'derivation',
    figures: [
      {
        id: 'derivation',
        tag: '§2.2 · Appendix B',
        indexTag: '∂',
        short: 'The 1-D model',
        title: 'The one-dimensional model · from the SSA to the three-zone solution',
        // The director's rule: the text between the equations is the paper's
        // own (Ch1DerivationEqs.vue) — the caption only says where it is from.
        caption: 'Journal of Glaciology 72, e76 — §2.2 and Appendix B, equation by equation, in the paper’s own words.',
        eqs: 'ch1-derivation',
      },
    ],
  },
  {
    label: 'Model',
    figures: [
      {
        id: 'schematic',
        tag: 'Fig. 1',
        short: 'Schematic',
        title: 'The 2d flowline model',
        caption:
          'A slab of thickness <i>h</i> on slope <i>α</i> over a slippery patch of length <i>ℓ</i> (<i>C</i> = 0); boundary layers of width [<i>x</i>] form at both patch edges, <i>C</i> &gt; 0 outside.',
        src: `${K}fig01_schematic.webp`,
        size: [2000, 485],
        maxWidth: 1180,
        alt: 'Schematic of the 2d flowline model: ice slab, slippery patch, boundary layers',
      },
      {
        id: 'params',
        tag: 'Table 1',
        short: 'Ensemble',
        title: 'The simulation ensemble',
        caption: 'Range of parameter values used in the numerical experiments (2d Elmer/Ice, periodic inflow/outflow).',
        table: 'params',
      },
      {
        id: 'domain',
        tag: 'Fig. 2 a, b, d, e',
        short: 'Example domain',
        title: 'Example domain · velocity and stress fields',
        caption:
          '<i>h</i> = 1000 m, <i>α</i> = 0.5°, <i>ℓ</i> = 5 km, <i>γ</i> = 0.1: horizontal velocity <i>u</i>(<i>x</i>,<i>z</i>) and deviatoric normal stress <i>τ</i><sub>xx</sub>(<i>x</i>,<i>z</i>) — Newtonian <i>n</i> = 1 (top), Glen <i>n</i> = 3 (bottom).',
        src: `${K}fig02_fields.webp`,
        size: [2000, 1153],
        alt: 'Velocity and normal-stress fields of the example domain for n = 1 and n = 3',
      },
      // The director noticed Glen's flow law appeared nowhere in the
      // additional work: the paper's eq. 6 + Table 1's rows,
      // glossed with the paper's sentences (Ch1DerivationEqs set="glen").
      {
        id: 'glen',
        tag: 'Eq. 6 · Table 1',
        indexTag: 'n',
        short: 'Glen’s flow law',
        title: 'Glen’s flow law · the rheology',
        eqs: 'ch1-glen',
      },
    ],
  },
  {
    label: 'Stress',
    figures: [
      {
        id: 'surface',
        tag: 'Fig. 3',
        short: 'Surface stress',
        title: 'Surface stress · n = 1 and n = 3',
        caption:
          'Surface <i>τ</i><sub>xx</sub> across the patch for the ensemble (a, d); max|<i>τ</i><sub>xx</sub>| against <i>ρgαℓ</i>/4 (b, e) and the decay length against [<i>x</i>] = (2<i>Bh</i>/<i>C</i>)<sup><i>n</i>/(<i>n</i>+1)</sup> (c, f). Runs with <i>h</i> &lt; [<i>x</i>] &lt; <i>ℓ</i>.',
        src: `${K}fig03_surface_stress.webp`,
        size: [2000, 1144],
        alt: 'Surface stress profiles and log-log scalings for n = 1 and n = 3',
      },
      {
        id: 'kappa',
        tag: 'Table 2',
        short: 'Prefactors κ',
        title: 'The scaling prefactors',
        caption:
          'Medians across the ensemble; superscripts and subscripts give the 16th–84th percentile bounds. S = surface, DA = depth-averaged.',
        table: 'kappa',
      },
      {
        id: 'da-collapse',
        tag: 'Fig. 4 a, b, e, f',
        short: 'Depth-avg collapse',
        title: 'Depth-averaged stress · profiles and collapse',
        caption:
          'Dimensional <i>τ̄</i><sub>xx</sub> across the patch (a, e), and the non-dimensional collapse onto the 1d solution in the upstream boundary layer, patch interior and downstream boundary layer (b, f). Profiles with <i>δ</i> = [<i>x</i>]/<i>ℓ</i> &lt; 0.3.',
        src: `${K}fig04_profiles_collapse.webp`,
        size: [2000, 991],
        alt: 'Depth-averaged stress profiles and their collapse in three regions, n = 1 and n = 3',
      },
      {
        id: 'da-loglog',
        tag: 'Fig. 4 c, d, g, h',
        short: 'Depth-avg log-log',
        title: 'Depth-averaged stress · scaling',
        caption:
          'max|<i>τ̄</i><sub>xx</sub>| = <i>κ ρgαℓ</i>/4 and DL = <i>κ</i> [<i>x</i>] for <i>n</i> = 1 (c, d) and <i>n</i> = 3 (g, h); grey band = 16th–84th percentile of <i>κ</i>.',
        src: `${K}fig04_loglog.webp`,
        size: [2000, 596],
        alt: 'Log-log scaling of depth-averaged maximum stress and decay length, n = 1 and n = 3',
      },
    ],
  },
  {
    label: 'Velocity',
    figures: [
      {
        id: 'sia',
        tag: 'Fig. 2 c, f',
        short: 'Background flow',
        title: 'Background flow · velocity at the domain edges',
        caption:
          'Vertical profiles of <i>u</i> at the periodic inflow and outflow boundaries against the basal-sliding SIA solution (red), <i>n</i> = 1 and <i>n</i> = 3.',
        src: `${K}fig02_sia_profiles.webp`,
        size: [2000, 775],
        alt: 'Velocity profiles at the domain edges against the SIA solution',
      },
      {
        id: 'velocity-n1',
        tag: 'Fig. B1 a–c',
        short: 'Velocity · n = 1',
        title: 'Perturbation velocity · n = 1',
        caption:
          'Depth-averaged <i>u′</i> above the background: dimensional (a), non-dimensional in the three regions against the 1d model (b), and max <i>u′</i> from Elmer against theory (c).',
        src: `${K}figB1_velocity_n1.webp`,
        size: [2000, 782],
        alt: 'Depth-averaged perturbation velocity for n = 1',
      },
      {
        id: 'velocity-n3',
        tag: 'Fig. B1 d–f',
        short: 'Velocity · n = 3',
        title: 'Perturbation velocity · n = 3',
        caption:
          'The same for Glen’s law: dimensional (d), non-dimensional in the three regions (e), max <i>u′</i> from Elmer against theory (f).',
        src: `${K}figB1_velocity_n3.webp`,
        size: [2000, 779],
        alt: 'Depth-averaged perturbation velocity for n = 3',
      },
    ],
  },
  {
    label: 'Coupling length',
    figures: [
      {
        id: 'acl-h-alpha',
        tag: 'Fig. 5 a, b',
        short: 'ACL · h and α',
        title: 'Absolute coupling length · thickness and slope',
        caption:
          'ACL with <i>ℓ</i> = 5 km, <i>γ</i> = 0.1, <i>τ</i><sub>val</sub> = 30 kPa for <i>n</i> = 1 (a) and <i>n</i> = 3 (b); magenta = where driving stress, the observed GrIS (<i>h</i>, <i>α</i>) and <i>δ</i> &lt; 1 all hold.',
        src: `${K}fig05_acl_h_alpha.webp`,
        size: [2000, 759],
        alt: 'Phase-space maps of absolute coupling length over thickness and slope, n = 1 and n = 3',
      },
      {
        id: 'acl-h-ell',
        tag: 'Fig. 5 c, d',
        short: 'ACL · h and ℓ',
        title: 'Absolute coupling length · thickness and patch length',
        caption:
          'ACL at <i>α</i> = 0.5° for <i>n</i> = 1 (c) and <i>n</i> = 3 (d); dashed <i>ℓ</i> = 10 km, horizontal lines the 5th–95th percentile GrIS thickness at that slope.',
        src: `${K}fig05_acl_h_ell.webp`,
        size: [2000, 759],
        alt: 'Phase-space maps of absolute coupling length over thickness and patch length, n = 1 and n = 3',
      },
      {
        id: 'profile',
        tag: 'Fig. 6',
        short: 'Ice-sheet profile',
        title: 'Along an idealized ice-sheet profile',
        caption:
          'Weertman (1976) convex profile, <i>n</i> = 3, <i>ℓ</i> = 5 km: ACL peaks near 3 km ~75 km from the terminus (a) while max <i>τ</i><sub>xx</sub> falls toward the interior (b); both against <i>h</i> (c) and <i>α</i> (d).',
        src: `${K}fig06_ice_sheet_profile.webp`,
        size: [2000, 1342],
        alt: 'Absolute coupling length and maximum stress along a convex ice-sheet profile',
      },
      {
        id: 'acl-n',
        tag: 'Fig. 7',
        short: 'ACL vs n',
        title: 'Coupling length against the flow-law exponent',
        caption:
          '<i>h</i> = 1 km, <i>α</i> = 0.5°, <i>ℓ</i> = 5 km, <i>τ</i><sub>val</sub> = 30 kPa: only weakly sensitive to <i>n</i>, and non-monotonic at larger <i>γ</i>.',
        src: `${K}fig07_acl_vs_n.webp`,
        size: [1341, 932],
        alt: 'Absolute coupling length against flow-law exponent n for three sliding ratios',
        maxWidth: 980,
      },
    ],
  },
  {
    label: 'Appendix',
    figures: [
      {
        id: 'greenland',
        tag: 'Fig. A1',
        short: 'Greenland · n = 3',
        title: 'Greenland at n = 3',
        caption:
          'ACL (a) and max surface stress <i>ρgαℓ</i>/4 (b) at every ice pixel from BedMachine v6 and ITS_LIVE, <i>ℓ</i> = 5 km, <i>γ</i> = 0.1; insets = the central-west lakes, white = the 1600 m contour.',
        src: `${K}figA1_greenland_n3.webp`,
        size: [2000, 1316],
        alt: 'Maps of absolute coupling length and maximum surface stress over Greenland for n = 3',
      },
      {
        id: 'delta',
        tag: 'Fig. C1',
        short: 'Collapse vs δ',
        title: 'The collapse against δ',
        caption:
          'Non-dimensional depth-averaged stress (top) and velocity (bottom) coloured by <i>δ</i> = [<i>x</i>]/<i>ℓ</i>, <i>n</i> = 1 left, <i>n</i> = 3 right: smaller <i>δ</i>, tighter agreement with the 1d theory.',
        src: `${K}figC1_collapse_delta.webp`,
        size: [2000, 917],
        alt: 'Non-dimensional stress and velocity profiles coloured by delta, n = 1 and n = 3',
      },
    ],
  },
]

const K2 = 'addl/deeper/ch02/figs/'

const CH2_GROUPS: DeeperGroup[] = [
  // The APS DFD 2026 Interact presentation of this chapter's paper (the
  // director's ask, 2026-11-21: a DFD door right at the top of this page)
  // — the two-minute flash slide and the interactive poster live on their
  // own page, /additional-work/dfd (SectionDfd.vue, config/dfd.ts).
  {
    label: 'APS DFD 2026',
    id: 'dfd',
    figures: [
      {
        id: 'dfd',
        tag: 'Interact · 22 November 2026',
        indexTag: 'DFD',
        short: 'The presentation',
        title: 'The flash talk and the interactive poster',
        door: 'dfd',
      },
    ],
  },
  // The PDFs open in a new tab — the manuscript as
  // submitted (August 2026, line-numbered) and its supporting information.
  {
    label: 'The paper',
    id: 'paper',
    figures: [
      {
        id: 'pdf',
        tag: 'PNAS · in revision',
        indexTag: 'PDF',
        short: 'The paper',
        title: 'The paper',
        pdf: {
          key: 'papers/lai2026_pnas_v1.pdf',
          cover: 'papers/lai2026_pnas_cover_v1.webp',
          coverSize: [935, 1210],
          pages: 8,
          mb: '2.2',
          note: 'The manuscript as submitted (August 2026).',
        },
      },
      {
        id: 'pdf-si',
        tag: 'PNAS SI',
        indexTag: 'SI',
        short: 'The SI',
        title: 'The supporting information',
        pdf: {
          key: 'papers/lai2026_pnas_si_v1.pdf',
          cover: 'papers/lai2026_pnas_si_cover_v1.webp',
          coverSize: [935, 1210],
          pages: 39,
          mb: '20',
          note: 'The SI as submitted — the theory, the simulations, Figs. S1–S26.',
        },
      },
    ],
  },
  // The director limited Chapter 2 on the talk to the viscous model (the
  // elastic model was too much to fit in) and moved the full sequence,
  // elastic results included, here: the talk's results walk as it was, the two
  // elastic stations included, for any of the seven lakes — and the
  // population page's elastic | viscous pair. The talk itself walks the
  // viscous stations only (config/ch2Beats.ts); its population page's
  // DIVE DEEPER door lands here.
  {
    label: 'The full sequence',
    id: 'sequence',
    figures: [
      {
        id: 'walk',
        tag: 'Both models',
        indexTag: '5',
        short: 'Five stations',
        title: 'The results, in time · elastic and viscous',
        // The director asked for the long caption trimmed to one line.
        caption:
          'The talk’s walk with the elastic stations too, any center lake: the surface field left, that lake’s neighbours in the stress space right. POST · ELASTIC is <i>σ</i><sup>V</sup><sub>pre</sub> + Δ<i>σ</i><sup>E</sup> (qualitative; see <i>Why pre + Δσ</i>).',
        viewer: 'ch2-sequence',
      },
      {
        id: 'populations',
        tag: 'Fig. 5 recipe',
        indexTag: 'E|V',
        short: 'Both populations',
        title: 'Every lake · elastic | viscous',
        caption: 'Every center lake’s neighbours, one stress space per model (shape = center lake, colour = drainage class).',
        plot: 'ch2-ss-both',
      },
    ],
  },
  {
    label: 'Fields',
    figures: [
      {
        id: 'fields',
        tag: 'Figs. S7–S20',
        indexTag: 'S7+',
        short: 'Every field',
        title: 'Every surface field · seven lakes, two models',
        caption:
          'The 15 × 15 km analysis tile in EPSG:3413. Black hashes: principal-stress orientations; dashed: the +100 kPa contour; white vectors: surface velocity; outlines: drainage class from imagery. Δ = principal value of the tensor difference.',
        viewer: 'ch2-fields',
      },
    ],
  },
  {
    label: 'Stress spaces',
    id: 'stress-spaces',
    figures: [
      // The director took the equations off the summary page and wanted
      // them here in the deeper dive instead: the definitions of the
      // diagrams' axes, which rode the results beats and the population
      // page until then.
      {
        id: 'stress-defs',
        tag: 'SI Eqs. 52–54',
        indexTag: 'Eqs',
        short: 'The axes, defined',
        title: 'The stress-space axes · definitions',
        caption:
          '<i>σ</i><sub>t1</sub> ≥ <i>σ</i><sub>t2</sub>: the principal values of the stress in the plane tangent to the ice surface (<b>e</b><sub>1</sub>, <b>e</b><sub>2</sub> ⊥ <b>n</b>; tension positive). Δ<i>σ</i><sub>t1</sub>, Δ<i>σ</i><sub>t2</sub>: the same, of the full tensors’ difference <i>σ</i><sup>post</sup> − <i>σ</i><sup>pre</sup>. PNAS SI §4C, Eqs. 52–54.',
        eqs: 'ch2-stress-defs',
      },
      // The director wanted the theoretical justification — even just a
      // few equations — for adding the elastic perturbation to the viscous
      // background somewhere on the site: the jump condition
      // across the instant of drainage, Ch2SuperpositionEqs.vue.
      {
        id: 'superposition',
        tag: 'Jump condition',
        indexTag: 'σ⁺',
        short: 'Why pre + Δσ',
        title: 'The post-drainage elastic state · <i>σ</i><span class="dd-ss"><span>V</span><span>pre</span></span> + Δ<i>σ</i><sup>E</sup>',
        // The director cut the extra text below the six-line derivation:
        // the caveats alone, stated plainly, no preamble. The wording
        // follows a second reviewer's reading: (1) softened, (2) with the
        // size of the correction, (3) with n δt/τ_M and where the jump
        // over- or mis-states the perturbation.
        caption:
          'Caveats. (1) The elastic solves’ own absolute fields are an elastic body loaded by gravity from an unstressed state (laterally confined, <i>σ</i><sub><i>xx</i></sub> ≈ 0.43 <i>σ</i><sub><i>zz</i></sub> rather than near-cryostatic), not a state of the ice sheet; only the difference Δ<i>σ</i><sup>E</sup> is meant physically, and it carries the reference’s footprint traction — (2). (2) Δ<i>σ</i><sup>E</sup> is the published blister − no-blister difference: the traction it releases on the footprint is the elastic reference’s (the blister is a traction load, PNAS SI Eqs. 50–51), not the viscous pre-drainage one, so the true jump is Δ<i>σ</i><sup>E</sup> + ℰ[<b>t</b><sup>E</sup><sub>ref</sub> − <b>t</b><sup>V</sup><sub>pre</sub>] — a correction that is zero on a uniform slab (equilibrium fixes both tractions) but, over real bed, of the order of the sliding-release part of Δ<i>σ</i><sup>E</sup> itself (the clamped, laterally confined reference carries 260–400 kPa of footprint shear on the three largest tiles, against a driving stress of 140–230 kPa) — uncomputed, inside every published elastic field; the superposition neither adds nor removes it, and one gravity-free solve would. (3) The jump is Hookean only where the drainage is short against the time a Glen dashpot takes to relax a perturbation, <i>τ</i><sub>M</sub>/<i>n</i> (<i>n</i> = 3), with <i>τ</i><sub>M</sub> = <i>η</i>/<i>G</i> = 1/(2<i>Aτ</i><sub>e</sub><sup><i>n</i>−1</sup><i>G</i>). At −10 °C (<i>A</i> = 3.5 × 10<sup>−25</sup> Pa<sup>−3</sup> s<sup>−1</sup>; <i>E</i> = 3.077 GPa, <i>ν</i> = 0.3 ⇒ <i>G</i> = 1.18 GPa) <i>τ</i><sub>M</sub> is 134 h at <i>τ</i><sub>e</sub> = 50 kPa, 34 h at 100, 8.4 h at 200 and 1.3 h at 500; for a 1–2 h drainage <i>n δt</i>/<i>τ</i><sub>M</sub> is ≤ 0.05, 0.1–0.2, 0.4–0.7 and &gt; 2. So <i>σ</i><sup>V</sup><sub>pre</sub> + Δ<i>σ</i><sup>E</sup> is the post-drainage state where the effective stress is tens of kPa, overstates the perturbation by tens of percent near ~200 kPa (the blister rim), and is not the state at 500 kPa; deeper, warmer ice relaxes faster still. (4) The pressure part of Δ<i>σ</i><sup>E</sup> scales with <i>E</i>: at a fixed 1 m uplift, Δ<i>p</i> ∝ <i>E</i> (SI Eq. 47), so 9 GPa instead of 3.077 would give ×2.9 — the value of <i>E</i> at the ~1 h timescale is itself uncertain.',
        eqs: 'ch2-superposition',
      },
      {
        id: 'stress-space-elastic',
        tag: 'Fig. 2.20',
        short: 'Elastic',
        title: 'Stress space · elastic (blister-induced)',
        // The director's physics: the elastic solves' absolute fields have no
        // physical meaning — only Δσ^E does — so the x-axis is the
        // post-drainage state σ^V_pre + Δσ^E, drawn live (the thesis's
        // baked Fig. 2.20, stress_space_elastic.webp, plotted the elastic
        // solve's own post-blister stress there)
        caption:
          'One symbol per neighboring lake (shape = center lake; colour = drainage class from imagery: englacial cyan, lateral gray, none open). Post-drainage = the viscous pre-drainage stress plus the elastic perturbation, <i>σ</i><sup>V</sup><sub>pre</sub> + Δ<i>σ</i><sup>E</sup> (tensors first). Top: Δ<i>σ</i><sub>t1</sub>, Δ<i>σ</i><sub>t2</sub> against it; bottom: the viscous pre-drainage stresses against it. Polygon means.',
        plot: 'ch2-ss-elastic',
      },
      {
        id: 'stress-space-viscous',
        tag: 'Fig. 2.21',
        short: 'Viscous',
        title: 'Stress space · viscous (sliding-induced)',
        caption:
          'The same for the free-slip patch: top, the patch-induced Δ<i>σ</i><sub>t1</sub>, Δ<i>σ</i><sub>t2</sub> against the post-patch stresses (the paper’s Fig. 5); bottom, pre- against post-patch.',
        src: `${K2}stress_space_viscous.webp`,
        size: [2000, 1922],
        alt: 'Viscous stress-space diagram: perturbation and pre-patch stress against post-patch stress for the neighboring lakes',
      },
      {
        id: 'table-elastic',
        tag: 'Table 2.2',
        short: 'Elastic · the lakes',
        title: 'The neighboring lakes · elastic',
        caption:
          'Polygon means of <i>σ</i><sub>t1</sub>, <i>σ</i><sub>t2</sub> before the blister (pre), the perturbation (Δ, tensor-first) and after (post); kPa, tension positive. <i>σ</i><sup>post</sup> ≠ <i>σ</i><sup>pre</sup> + Δ<i>σ</i>: the principal directions rotate. Uncertainty ~10–50 kPa.',
        table: 'ch2-elastic',
      },
      {
        id: 'table-viscous',
        tag: 'Table 2.3',
        short: 'Viscous · the lakes',
        title: 'The neighboring lakes · viscous',
        caption: 'The same for the free-slip patch (pre = no patch, post = with the patch).',
        table: 'ch2-viscous',
      },
    ],
  },
  // The director wanted the conversions between all the stresses written
  // out here so he can point to their relationships — σ_t1 and σ_t2, the
  // Cartesian τ_xx, τ_yy, τ_xz, τ_zz, and the corresponding τ_rr and
  // company in polar coordinates: the
  // agreed seven blocks, LaTeX → SVG (build_stress_rel_eqs.py, R2
  // ch02/eq_rel/). The heading IS the label — no captions; the SI's own
  // σ_t1/σ_t2/Δσ definitions stay in #stress-spaces above, not repeated.
  {
    label: 'Stress relations',
    id: 'stress-relations',
    figures: [
      // Added when the director noticed Glen's flow law appeared nowhere in the additional work.
      { id: 'rel-glen', tag: 'SI §4, Eq. 39', indexTag: 'η', short: 'Glen’s flow law', title: 'Glen’s flow law · the viscous model’s rheology', relations: 'glen' },
      { id: 'rel-cauchy', tag: 'SI before Eq. 35', indexTag: 'σ, τ', short: 'Cauchy ↔ deviatoric', title: 'Cauchy ↔ deviatoric', relations: 'cauchy' },
      { id: 'rel-ssa', tag: 'SI before Eq. 35', indexTag: 'SSA', short: 'Depth-avg. Cauchy', title: 'Depth-averaged Cauchy · SSA', relations: 'ssa' },
      { id: 'rel-polar', tag: '', indexTag: 'r, θ', short: 'Cartesian ↔ polar', title: 'Cartesian ↔ polar', relations: 'polar' },
      { id: 'rel-surface', tag: 'SI §4C', indexTag: 'n', short: 'Free surface', title: 'Free surface', relations: 'surface' },
      { id: 'rel-principals', tag: 'SI §4C, Eq. 52', indexTag: 't1, t2', short: 'In-plane principals', title: 'In-plane principals · from the six surface components', relations: 'principals' },
      { id: 'rel-perturbation', tag: 'SI Eqs. 53–54', indexTag: 'Δ', short: 'Perturbations', title: 'Perturbations', relations: 'perturbation' },
      { id: 'rel-theory', tag: 'PNAS SI Eqs. S23, S34–S35', indexTag: 'Thy', short: 'Slippery-patch theory', title: 'Slippery-patch theory', relations: 'theory' },
    ],
  },
  {
    label: 'Main-text figures',
    figures: [
      {
        id: 'fig1',
        tag: 'Fig. 1',
        short: 'Blister to sliding',
        title: 'From blister-induced to sliding-induced stress',
        caption:
          'Lake 2511 before and after drainage (A); the pre-drainage, blister-induced and sliding-induced states as schematics (B–D) and as full-Stokes <i>σ</i><sub>t1</sub> over the real bed (E–G).',
        src: `${K2}pnas_fig1.webp`,
        size: [2000, 1300],
        alt: 'PNAS Figure 1: imagery of lake 2511, schematics and simulated surface stress for the three stages',
      },
      {
        id: 'fig2',
        tag: 'Fig. 2',
        short: 'Theory vs Stokes',
        title: 'The sliding-induced perturbation · theory and simulation',
        caption:
          'Δ<i>σ̄</i><sub><i>rr</i></sub>, Δ<i>σ̄</i><sub><i>rθ</i></sub>, Δ<i>σ̄</i><sub><i>θθ</i></sub> over a circular free-slip patch: Stokes against the analytical solution (A), lake 2394 over real topography (B), the dimensionless collapse (C), maxima against theory across <i>R</i>, <i>H</i>, <i>α</i> (D).',
        src: `${K2}pnas_fig2.webp`,
        size: [1902, 1483],
        alt: 'PNAS Figure 2: analytical and simulated stress perturbations over a free-slip patch',
      },
      {
        id: 'fig3',
        tag: 'Fig. 3',
        short: 'Viscoelastic',
        title: 'The elastic-to-viscous transition',
        caption:
          'A 2d Maxwell slab over a water-filled patch: the setup (A); <i>τ</i><sub>xx</sub> at <i>t</i> = 0, blister-dominated (B), and at <i>t</i> = 16.79 h, sliding-dominated (C); the surface stress through time (D).',
        src: `${K2}pnas_fig3.webp`,
        size: [2000, 510],
        alt: 'PNAS Figure 3: viscoelastic simulation of the transition from blister- to sliding-induced stress',
        credit: 'Figure by Eojin Lee, Fiona Clerc and Ching-Yao Lai',
      },
      {
        id: 'fig4',
        tag: 'Fig. 4',
        short: 'Three lake groups',
        title: 'Observation and simulation · three lake groups',
        caption:
          'Sentinel-2 before (i) and after (ii) the englacial drainage of center lakes 2394, 1951 and 2416 (A–C), with the pre- and post-drainage viscous <i>σ</i><sub>t1</sub> beneath (D–F).',
        src: `${K2}pnas_fig4.webp`,
        size: [2000, 1446],
        alt: 'PNAS Figure 4: imagery and simulated surface stress for lakes 2394, 1951 and 2416',
      },
    ],
  },
  {
    label: 'Setup',
    figures: [
      {
        id: 'lakes',
        tag: 'Table 2.1',
        short: 'Seven lakes',
        title: 'The seven center lakes',
        caption:
          'Centroids; tile means of surface elevation, thickness and observed speed (BedMachine v5, MEaSUREs v5, summer 2019); drainage dates from imagery; the basal friction <i>c</i><sub>b</sub> tuned so the simulated mean speed matches the observed to ~10 %.',
        table: 'ch2-lakes',
      },
      {
        id: 'locations',
        tag: 'Fig. 2.2',
        short: 'Locations',
        title: 'Where the seven tiles sit',
        caption:
          'Each center lake with its 15 × 15 km analysis tile, rotated along flow (a), and zoom-ins (b–e), on a BedMachine v6 hillshade; EPSG:3413.',
        src: `${K2}center_lakes_map.webp`,
        size: [2000, 2287],
        alt: 'Map of the seven center lakes and their analysis tiles in central-west Greenland',
      },
      {
        id: 'imagery',
        tag: 'Fig. S4',
        short: 'Other imagery',
        title: 'Imagery · the remaining center lakes',
        caption:
          'Sentinel-2 before (i) and after (ii) drainage for 2520, 2411 and 1910 (A–C); the black square is the model tile, the arrow the local flow direction.',
        src: `${K2}si_s4_imagery.webp`,
        size: [2000, 1290],
        alt: 'Sentinel-2 imagery before and after drainage for lakes 2520, 2411 and 1910',
      },
      {
        id: 'timing',
        tag: 'Fig. S3',
        short: 'Center-lake check',
        title: 'Distance and timing of nearby drainages',
        caption:
          'Around lake 2394’s englacial drainage on 16 June 2019 — the check, run for every candidate, that a background stress state is a reasonable assumption.',
        src: `${K2}si_s3_drainage_timing.webp`,
        size: [2000, 1947],
        alt: 'Nearby lake drainages around lake 2394 by distance and date',
      },
      {
        id: 'worldview',
        tag: 'Fig. S2',
        short: 'Lake 2280',
        title: 'A hydrofracture from above',
        caption:
          'WorldView panchromatic, 5 July 2019: lake 2280 still draining englacially into its hydrofracture scarp, two weeks after the fracture (17 June). Imagery © 2019 Vantor.',
        src: `${K2}si_s2_worldview_2280.webp`,
        size: [1699, 1207],
        alt: 'WorldView image of lake 2280 draining into a hydrofracture and moulin',
        credit: 'Figure by Niall B. Coffey',
        maxWidth: 1100,
      },
      {
        id: 'temperature',
        tag: 'Fig. S5',
        short: 'Temperature',
        title: 'Vertical temperature profiles',
        caption:
          'SICOPOLIS ice temperature in along-flow rotated coordinates, lake 2394 (a), and the tile-mean profiles with their quartic fits (b) — the viscous runs’ rheology.',
        src: `${K2}si_s5_temperature.webp`,
        size: [2000, 838],
        alt: 'Grid-cell intersections and vertical temperature profiles for lake 2394',
        credit: 'Figure by Niall B. Coffey',
      },
      {
        id: 'rotation',
        tag: 'Fig. S6',
        short: 'Flow rotation',
        title: 'Rotating the tile along flow',
        caption: 'The along-flow rotation applied to the geometry and velocity products, lake 2394.',
        src: `${K2}si_s6_flow_rotation.webp`,
        size: [2000, 1162],
        alt: 'Bed, thickness, surface, flow direction and speed before and after the along-flow rotation',
        credit: 'Figure by Niall B. Coffey',
      },
      {
        id: 'blister',
        tag: 'Fig. S23',
        short: 'The blister',
        title: 'Building the basal blister',
        caption:
          'Lake 2394: the bed without (a) and with (b) the Timoshenko blister, and their difference <i>w</i>(<i>r</i>) (c), 1 m at its peak.',
        src: `${K2}blister.webp`,
        size: [2000, 661],
        alt: 'Bed elevation without and with the basal blister, and the blister shape',
      },
    ],
  },
  {
    label: 'Validation',
    figures: [
      {
        id: 'ssa',
        tag: 'Fig. 2.19',
        short: 'Theory vs Stokes',
        title: 'The analytical theory against full Stokes',
        caption:
          'Depth-averaged <i>τ̄</i><sub><i>rr</i></sub>, <i>τ̄</i><sub><i>rθ</i></sub>, <i>τ̄</i><sub><i>θθ</i></sub>: Elmer/Ice (left), the shallow-stream solution (middle), their difference (right); Newtonian slab, <i>H</i> = 3000 m, <i>α</i> = 0.1°, <i>γ</i> = 0.1, <i>R</i> = 5 km. Modified from Coffey (2026).',
        src: `${K2}ssa_validation.webp`,
        size: [2000, 1934],
        alt: 'Simulated and analytical depth-averaged stress components and their difference',
      },
      {
        id: 'theory-error',
        tag: 'Fig. S1',
        short: 'Fractional error',
        title: 'Simulation, theory and fractional error',
        caption:
          'The same comparison as |(simulation − theory) / theory|, plotted where the theoretical stress exceeds 0.1 Pa.',
        src: `${K2}si_s1_theory_error.webp`,
        size: [2000, 1967],
        alt: 'Simulated and analytical stress components and their fractional error',
        credit: 'Figure by Niall B. Coffey',
      },
      {
        id: 'ub',
        tag: 'Fig. S24',
        short: 'Basal displacement',
        title: 'Elastic sliding · the basal displacement',
        caption:
          'Lake 2394, no blister, <i>E</i> = 9 GPa: the bed outside the free-slip patch displaced along flow by <i>u</i><sub>b</sub> = 0, 0.5, 1 m; the patch-induced <i>σ</i><sub>t1</sub>, <i>σ</i><sub>t2</sub> barely change (right: 0 m − 1 m).',
        src: `${K2}ub_sensitivity.webp`,
        size: [2000, 1282],
        alt: 'Elastic stress perturbation for three basal displacements and their difference',
      },
      {
        id: 'sigma-n',
        tag: 'Fig. S25',
        short: 'σn residual',
        title: 'The free-surface residual',
        caption:
          'Lake 2394: <i>σ</i><sub>t1</sub>, <i>σ</i><sub>t2</sub> and <i>σ</i><sub><i>n</i></sub> (zero in theory) for the viscous patch run (top, 10 vertical levels) and the elastic blister perturbation (bottom, 30 levels), with the distribution of <i>σ</i><sub><i>n</i></sub>.',
        src: `${K2}sigma_n.webp`,
        size: [2000, 1019],
        alt: 'Surface-local stress decomposition and the normal-stress residual for lake 2394',
      },
      {
        id: 'mesh',
        tag: 'Fig. S26',
        short: 'Mesh resolution',
        title: 'Vertical mesh resolution',
        caption:
          'Lake 2394, viscous, no patch: 10 vertical levels (top) against 20 (middle) and their difference (bottom), ≈ 6 kPa tile-averaged — the uncertainty the center-lake runs carry.',
        src: `${K2}mesh_resolution.webp`,
        size: [2000, 1464],
        alt: 'Surface stresses at 10 and 20 vertical levels and their difference',
      },
      // The idealized slab's every field (the talk's THEORY beats' MORE
      // FIELDS door lands here: /additional-work/deeper/
      // chapter2#slab-fields). Ch2SlabFieldViewer.vue, data config/ch2Slab.ts.
      // The director judged it belongs under validation: folded in from
      // its own group, id unchanged.
      {
        id: 'slab-fields',
        tag: 'Sweep',
        indexTag: 'Slab',
        short: 'Slab fields',
        title: 'The idealized slab · simulation, theory, difference',
        caption:
          'Depth-averaged Elmer/Ice fields of the periodic slab (Newtonian, linear Weertman sliding, a free-slip patch of radius <i>R</i>, dashed), the shallow-stream theory, and their difference — on the field\'s own colour scale and ×10.',
        viewer: 'ch2-slab',
      },
    ],
  },
]

const K3 = 'addl/deeper/ch03/figs/essd_v3_'
const PW = '<i>p</i><sub>water</sub>'
const F1 = '<i>F</i><sub>1</sub>'

const CH3_GROUPS: DeeperGroup[] = [
  // The PDF opens in a new tab — manuscript version 3,
  // the September 2026 revision (what the site's numbers are).
  {
    label: 'The paper',
    id: 'paper',
    figures: [
      {
        id: 'pdf',
        tag: 'essd-2026-406 · v3',
        indexTag: 'PDF',
        short: 'The paper',
        title: 'The paper',
        pdf: {
          key: 'papers/rines2026_essd_v3_v1.pdf',
          cover: 'papers/rines2026_essd_v3_cover_v1.webp',
          coverSize: [936, 1066],
          pages: 35,
          mb: '5.0',
          note: 'Manuscript version 3 — the September 2026 revision, in final revision.',
        },
      },
    ],
  },
  {
    // The director asked for the definitions of F1, accuracy, precision
    // and recall in Chapter 3's deeper dive — every metric the model
    // reports, and the form of the loss function too.
    label: 'Metrics',
    id: 'metrics',
    figures: [
      {
        id: 'metrics',
        tag: 'App. B',
        indexTag: 'Σ',
        short: 'Metrics & loss',
        title: 'Metrics and the loss · what the RESULTS beats score',
        caption:
          'Every number on the training and confusion-matrix beats, defined from the confusion matrix (ESSD v3 Sect. 3–4, Appendix B): accuracy, per-class precision, recall and <i>F</i><sub>1</sub>, their macro averages, the random floor, the softmax head, the inverse-frequency class weights and the weighted cross-entropy the network is trained on, and the inter-rater <i>κ</i> behind the labels.',
        eqs: 'ch3-metrics',
      },
    ],
  },
  {
    label: 'The dataset',
    id: 'dataset',
    figures: [
      {
        id: 'study-area',
        tag: 'Fig. 1',
        short: 'Study area',
        title: 'Study area · the 1679 labeled lakes',
        caption:
          '(a) All supraglacial lakes of Dunmire et al. (2025), 2018 and 2019 (magenta), the <i>N</i> = 1679 lakes of the central-west (CW) basin in cyan; white lines, the IMBIE-3 basin divides. (b) The CW region, each lake coloured by its human-assigned class: no drainage (ND, red), hydrofracture (HF, green), moulin drainage (MD, blue), lateral drainage (LD, orange), crevasse drainage (CD, purple); pie charts, the per-class populations of 2018 (top) and 2019 (bottom).',
        credit:
          'Lakes: Dunmire et al. (2021, 2025) · basin divides: IMBIE-3 (Mouginot and Rignot, 2019) · basemap: Esri World Imagery (Maxar, Airbus)',
        src: `${K3}fig1_study_area.webp`,
        size: [2400, 1510],
        alt: 'Map of Greenland lakes and the central-west basin, lakes coloured by drainage class, with per-year class pie charts',
      },
      {
        id: 'pipeline',
        tag: 'Fig. 2',
        short: 'Data pipeline',
        title: 'Building the dataset',
        caption:
          `External sources (blue: Sentinel-2 L2A via the Microsoft Planetary Computer; the Dunmire et al. lake polygons and ${PW}) are processed by the open-source sat-tile-stack package (green) into four co-registered per-lake products (yellow); the labeling GUI (pink) adds the expert labels; all five are co-registered onto one UTM grid and time axis in a single CF-1.8 NetCDF per lake (red) — the 1679 files of the dataset. Right: a representative file, CW2019_2330.nc.`,
        credit: 'Imagery: ESA Sentinel-2 L2A (Microsoft Planetary Computer) · lake polygons and p_water: Dunmire et al. (2021, 2025)',
        src: `${K3}fig2_datapipeline.webp`,
        size: [2400, 1307],
        alt: 'Workflow diagram from Sentinel-2 imagery and lake polygons through sat-tile-stack to one NetCDF per lake',
      },
      {
        id: 'masking',
        tag: 'Fig. 3',
        short: 'Water masks',
        title: 'Static lake boundary · dynamic water mask',
        caption:
          'CW2019_1848 (49.59° W, 68.56° N): five Sentinel-2 snapshots across the 2019 melt season (top), and the same with the static lake boundary of Dunmire et al. (2021) (cyan) and the per-pixel, per-day NDWI water mask computed from the file’s own reflectance (magenta).',
        credit: 'Lake boundary: Dunmire et al. (2021)',
        src: `${K3}fig3_masking.webp`,
        size: [2400, 1083],
        alt: 'Five Sentinel-2 snapshots of lake CW2019_1848 with its static boundary and its daily water mask',
      },
      {
        id: 'classes',
        tag: 'Fig. 4',
        short: 'Five classes',
        title: 'The five drainage classes',
        caption:
          `(a) One 2019 example per class — ND, HF, MD, LD, CD — at five key timesteps, its daily fractional water-area series ${PW} beneath. (b) Where the five lakes sit, each inset its Dunmire et al. (2021) polygon in the class colour. (c) ${PW} for every labeled lake of each class (faint), the class mean (bold) and three representative lakes (black).`,
        credit: 'p_water: Dunmire et al. (2025) · lake polygons: Dunmire et al. (2021) · basemap: Esri World Imagery',
        src: `${K3}fig4_classes.webp`,
        size: [2400, 2393],
        alt: 'Example Sentinel-2 timestacks and water-area series for the five drainage classes, their locations, and per-class series',
      },
      {
        id: 'gui',
        tag: 'Fig. 5',
        short: 'Labeling GUI',
        title: 'The labeling interface',
        caption:
          'CW2019_1889: (a) lake-centred Sentinel-2 imagery, scrubbable through time; (b) the frame slider; (c) per-class probability sliders in 25 % steps, summing to 1; (d) the hard label (the argmax) and notes; (e) submit, back, skip and “flag for revisit”; (f) the per-class label distribution; (g) the filterable lake list. Implemented in sat-tile-stack.labeling.',
        src: `${K3}fig5_gui.webp`,
        size: [2400, 1479],
        alt: 'Screenshot of the labeling GUI with imagery, timeline slider, probability sliders and lake list',
      },
      {
        id: 'irr',
        tag: 'Fig. 6',
        short: 'Inter-rater',
        title: 'Three labelers · inter-rater agreement',
        caption:
          'A random <i>n</i> = 200 lakes (100 from 2018, 100 from 2019): row-normalized pairwise confusion matrices, Labeler 1 (the lead author) against Labeler 2 (a) and Labeler 3 (b), and Labelers 2 and 3 (c); each cell the count and the row percentage. Overall three-labeler agreement is 72.5 %; the largest disagreements concentrate along the MD row.',
        src: `${K3}fig6_irr.webp`,
        size: [2400, 767],
        alt: 'Three pairwise confusion matrices between labelers on 200 lakes',
      },
    ],
  },
  {
    label: 'The model',
    id: 'model',
    figures: [
      {
        id: 'architecture',
        tag: 'Fig. 7',
        short: 'Architecture',
        title: 'The baseline classifier',
        caption:
          `LakeDrainageClassifier, a two-stream temporal recurrent network of ≈ 140,000 parameters: the imagery branch (top) learns the evolution of spatial features through the Sentinel-2 time series, the scalar branch (bottom) the evolution of ${PW}; joined, a fully connected head predicts the class (ND, HF, MD, LD, CD), compared against the hand labels. Bracketed tuples are tensor shapes (<i>B</i>, batch size).`,
        src: `${K3}fig7_architecture.webp`,
        size: [2400, 893],
        alt: 'Architecture diagram of the two-stream classifier: CNN and ConvLSTM on imagery, LSTM on the water-area series, MLP head',
      },
    ],
  },
  {
    label: 'Appendix B · results',
    id: 'results',
    figures: [
      {
        id: 'results-map',
        tag: 'Fig. B1',
        short: 'Results map',
        title: 'Results on the map · five classes',
        caption:
          `Trained on the CW2019 training split, at the best-validation-macro-${F1} checkpoint: training (<i>n</i> = 600), validation (<i>n</i> = 200) and held-out test (<i>n</i> = 200) lakes. Top: expert labels; bottom: predictions, per-class and macro ${F1} in the legend — correct as faded circles, wrong as crosses filled with the predicted class and outlined in the true class.`,
        src: `${K3}figB1_map.webp`,
        size: [2057, 2400],
        alt: 'Maps of expert labels and model predictions for the training, validation and test lakes',
      },
      {
        id: 'training',
        tag: 'Fig. B2',
        short: 'Training curves',
        title: 'Training curves',
        caption:
          `Five-class (blue) and four-class (orange; HF and MD merged) baselines with the ${PW} stream. (a) Training (solid) and validation (dashed) cross-entropy loss. (b, c) Macro-${F1} (black training, grey validation) and per-class validation ${F1} (thin, dashed); dark red, the random classifier (0.20, 0.25); dotted, each model’s best-validation epoch — the checkpoint behind every reported number.`,
        src: `${K3}figB2_training.webp`,
        size: [2024, 2400],
        alt: 'Loss and F1 curves against epoch for the five-class and four-class baselines',
      },
      {
        id: 'confusion',
        tag: 'Fig. B3',
        short: 'Confusion',
        title: 'Confusion matrices',
        caption:
          `Five-class (top) and four-class (bottom; HF and MD merged) baselines with ${PW}, at each model’s best-validation checkpoint, on the training (<i>n</i> = 600), validation (<i>n</i> = 200) and test (<i>n</i> = 200) splits. Rows true, columns predicted; shading row-normalized, so the diagonal reads as per-class recall.`,
        src: `${K3}figB3_confusion_matrices.webp`,
        size: [2400, 1583],
        alt: 'Confusion matrices for the five-class and four-class baselines on the training, validation and test splits',
      },
    ],
  },
]

export const DEEPER_PAGES: Record<DeeperChapter, DeeperPage> = {
  chapter1: {
    id: 'chapter1',
    label: 'Chapter 1',
    venue: 'JoG',
    status: 'published',
    paper: ref('rines2026'),
    groups: CH1_GROUPS,
  },
  chapter2: {
    id: 'chapter2',
    label: 'Chapter 2',
    venue: 'PNAS',
    status: 'in revision',
    paper: ref('lai2026pnas'),
    groups: CH2_GROUPS,
  },
  chapter3: {
    id: 'chapter3',
    label: 'Chapter 3',
    venue: 'ESSD',
    status: 'in final revision',
    paper: ref('rines2026essd'),
    groups: CH3_GROUPS,
  },
}

// ── The paper's tables (JOG-2026-0047) ──────────────────────────────────────

/** Table 1 — range of parameter values (HTML cells, trusted static). */
export const CH1_PARAMS: { name: string; symbol: string; values: string; units: string }[] = [
  { name: 'Ice thickness', symbol: '<i>h</i>', values: '0.3, 1.0, 2.0, 3.0', units: 'km' },
  { name: 'Surface (bed) slope', symbol: '<i>α</i>', values: '0.1, 0.5, 1.0', units: '°' },
  { name: 'Patch length', symbol: '<i>ℓ</i>', values: '2.5, 5.0, 10.0, 25.0', units: 'km' },
  { name: 'Flow-law exponent', symbol: '<i>n</i>', values: '1 or 3', units: '—' },
  {
    name: 'Flow-law parameter',
    symbol: '<i>B</i><sup>−<i>n</i></sup>',
    values: '5.0 × 10<sup>−15</sup> (<i>n</i> = 1) · 2.4 × 10<sup>−24</sup> (<i>n</i> = 3)',
    units: 'Pa<sup>−<i>n</i></sup> s<sup>−1</sup>',
  },
  { name: 'Sliding ratio', symbol: '<i>γ</i>', values: '0.1, 0.5', units: '—' },
  {
    name: 'Basal sliding coefficient',
    symbol: '<i>C</i><sub>b</sub>',
    values: '<i>B</i> (<i>γ</i>/<i>h</i>)<sup>1/<i>n</i></sup>',
    units: 'Pa s<sup>1/<i>n</i></sup> m<sup>−1/<i>n</i></sup>',
  },
]

/** Table 2 — κ prefactors: median, +upper, −lower (16th–84th percentile). */
export interface KappaCell { median: string; plus: string; minus: string }
export const CH1_KAPPA: { n: 1 | 3; kind: 'S' | 'DA'; tau: KappaCell; dl: KappaCell }[] = [
  { n: 1, kind: 'S', tau: { median: '0.78', plus: '0.12', minus: '0.13' }, dl: { median: '1.40', plus: '0.50', minus: '0.31' } },
  { n: 3, kind: 'S', tau: { median: '0.95', plus: '0.07', minus: '0.03' }, dl: { median: '3.22', plus: '2.64', minus: '0.67' } },
  { n: 1, kind: 'DA', tau: { median: '0.93', plus: '0.04', minus: '0.07' }, dl: { median: '1.04', plus: '0.56', minus: '0.06' } },
  { n: 3, kind: 'DA', tau: { median: '0.94', plus: '0.03', minus: '0.06' }, dl: { median: '2.86', plus: '0.64', minus: '0.78' } },
]

// ── The thesis's Chapter 2 tables ───────────────────────────────────────────

/** Table 2.1 — the seven center lakes. */
export const CH2_LAKES_TABLE: {
  lake: number; lat: string; lon: string; surface: number; thickness: number; speed: number; drained: string; cb: string
}[] = [
  { lake: 1910, lat: '69.375', lon: '48.077', surface: 1460, thickness: 1452, speed: 287, drained: '22–23 Jul', cb: '5.4' },
  { lake: 1951, lat: '69.415', lon: '48.919', surface: 1147, thickness: 984, speed: 267, drained: '6–8 Jul', cb: '6.5' },
  { lake: 2394, lat: '70.285', lon: '49.880', surface: 934, thickness: 794, speed: 212, drained: '14–16 Jun', cb: '8.5' },
  { lake: 2411, lat: '71.079', lon: '50.266', surface: 1392, thickness: 992, speed: 158, drained: '2–3 Aug', cb: '8.5' },
  { lake: 2416, lat: '71.023', lon: '50.111', surface: 1424, thickness: 1117, speed: 175, drained: '21 Aug', cb: '7.5' },
  { lake: 2511, lat: '70.973', lon: '50.082', surface: 1389, thickness: 1034, speed: 210, drained: '21 Aug', cb: '8.6' },
  { lake: 2520, lat: '69.415', lon: '49.046', surface: 1095, thickness: 927, speed: 280, drained: '5–8 Jul', cb: '6.7' },
]

/** Tables 2.2 / 2.3 — neighbor lakes: [neighbor, class, drained (2019),
 *  σt1 pre, Δσt1, σt1 post, σt2 pre, Δσt2, σt2 post] (kPa), grouped by
 *  center lake (its drainage date beneath it), verbatim from ch2_main.tex. */
export type Ch2NeighborRow = [number, 'englacial' | 'lateral' | 'none', string, string, string, string, string, string, string]
export interface Ch2NeighborGroup { center: number; date: string; rows: Ch2NeighborRow[] }
export const CH2_RESULTS: Record<'elastic' | 'viscous', Ch2NeighborGroup[]> = {
  elastic: [
    { center: 1951, date: '6–8 Jul', rows: [[1938, 'none', '', '94', '0', '93', '−2', '−3', '−4']] },
    {
      center: 2394, date: '14–16 Jun', rows: [
        [2280, 'englacial', '17 Jun', '52', '+7', '57', '−76', '+1', '−73'],
        [2283, 'englacial', '17 Jun', '−70', '+47', '−32', '−131', '−93', '−216'],
        [2294, 'englacial', '18–19 Jun', '−45', '0', '−45', '−185', '0', '−185'],
        [2296, 'lateral', '', '−50', '−39', '−173', '−179', '−750', '−845'],
        [2300, 'lateral', '', '−245', '−33', '−281', '−303', '−288', '−588'],
        [2309, 'lateral', '', '244', '0', '243', '91', '0', '91'],
        [2311, 'lateral', '', '−111', '−31', '−147', '−141', '−334', '−470'],
      ],
    },
    {
      center: 2416, date: '21 Aug', rows: [
        [2398, 'englacial', '22 Aug', '−68', '−7', '−157', '−246', '−101', '−266'],
        [2399, 'englacial', '22 Aug', '−37', '−10', '−101', '−93', '−140', '−179'],
        [2402, 'englacial', '22 Aug', '−54', '−1', '−56', '−285', '−4', '−287'],
        [2414, 'englacial', '22 Aug', '148', '−4', '119', '68', '−46', '47'],
      ],
    },
    {
      center: 2511, date: '21 Aug', rows: [
        [2374, 'none', '', '39', '−1', '32', '−133', '−8', '−135'],
        [2398, 'englacial', '22 Aug', '−71', '−3', '−89', '−251', '−34', '−269'],
        [2399, 'englacial', '22 Aug', '−34', '−2', '−44', '−92', '−17', '−101'],
        [2414, 'englacial', '22 Aug', '142', '−1', '137', '65', '−5', '64'],
      ],
    },
    {
      center: 2520, date: '5–8 Jul', rows: [
        [2015, 'none', '', '195', '0', '192', '135', '−4', '133'],
        [2017, 'none', '', '−46', '+4', '−44', '−248', '0', '−246'],
      ],
    },
  ],
  viscous: [
    { center: 1951, date: '6–8 Jul', rows: [[1938, 'none', '', '−204', '+44', '−169', '−284', '−8', '−283']] },
    {
      center: 2394, date: '14–16 Jun', rows: [
        [2280, 'englacial', '17 Jun', '−49', '+321', '188', '−138', '+46', '−8'],
        [2283, 'englacial', '17 Jun', '−56', '+426', '311', '−131', '+114', '41'],
        [2294, 'englacial', '18–19 Jun', '−77', '+22', '−56', '−270', '−2', '−271'],
        [2296, 'lateral', '', '121', '−34', '−33', '−88', '−335', '−303'],
        [2300, 'lateral', '', '−11', '−35', '−48', '−206', '−123', '−326'],
        [2309, 'lateral', '', '−236', '+23', '−220', '−348', '−4', '−345'],
        [2311, 'lateral', '', '−15', '−29', '−157', '−202', '−287', '−377'],
      ],
    },
    {
      center: 2416, date: '21 Aug', rows: [
        [2398, 'englacial', '22 Aug', '81', '+176', '153', '−29', '+5', '80'],
        [2399, 'englacial', '22 Aug', '29', '+254', '146', '−113', '+34', '58'],
        [2402, 'englacial', '22 Aug', '137', '+49', '173', '74', '−21', '67'],
        [2414, 'englacial', '22 Aug', '25', '+199', '100', '−112', '+21', '33'],
      ],
    },
    {
      center: 2511, date: '21 Aug', rows: [
        [2374, 'none', '', '168', '+49', '182', '18', '−2', '51'],
        [2398, 'englacial', '22 Aug', '−24', '+124', '55', '−194', '+14', '−135'],
        [2399, 'englacial', '22 Aug', '−45', '+84', '16', '−209', '+7', '−179'],
        [2414, 'englacial', '22 Aug', '−71', '+55', '−30', '−218', '+5', '−200'],
      ],
    },
    {
      center: 2520, date: '5–8 Jul', rows: [
        [2015, 'none', '', '−108', '+1', '−133', '−200', '−67', '−241'],
        [2017, 'none', '', '−92', '+38', '−63', '−246', '−12', '−250'],
      ],
    },
  ],
}
