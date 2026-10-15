// The literature timeline (Introduction).
//
// One entry per paper, in CHRONOLOGICAL order (`when`). The component
// sorts by `when` for the left-to-right card order, so the array order
// here is only the tiebreaker within a month — the two 2008 papers once
// sat Das-then-Price while their branches went Price-then-Das and
// crossed (the director caught it).
//
// Bylines were checked against CrossRef (api.crossref.org/works/<DOI>)
// — first author, full author list, journal, and issue
// date all come from the DOI record, NOT from Zotero (whose creator
// table is not in author order; it produced two wrong bylines before
// this file existed). If a paper is added, check
// its byline against the paper itself before it renders as "X et al."
//
// `when` is the fractional year used to place the paper on the year
// axis (issue month / 12). `cites` is exactly that — the other entries
// this paper's reference list contains, nothing editorial (the
// director's rule: the arcs indicate which papers cite which other
// papers, and carry no other meaning). Checked against
// each DOI's CrossRef reference list (api.crossref.org/works/<DOI>,
// `reference[]`, matched by DOI and by first author + year where the
// deposit had no DOI) and, for Rines et al., against the manuscript's
// own \cite keys (cinematic/source_data/manuscript_jog/main.tex). The
// arcs are drawn citing → cited and lit gold when the citing paper is
// hovered; a hovered paper's citers glow faintly.
//   Not in the lists, on purpose: Rines 2026 cites neither Zwally 2002
//   nor Price 2008 (both in paper_jog.bib, neither \cite'd), Stevens
//   2024 and Stevens 2026 do not cite Zwally 2002, Lai 2021 does not
//   cite Leeson 2015 or Price 2008. Stevens 2026 cites the Rines
//   EarthArXiv preprint (10.31223/X50J2P) — counted as citing Rines.
//
// Schoof 2010 joined later (the director: it belongs on the literature
// page too). Byline, issue (Nature 468, 803–806, 9 December
// 2010) and reference list from its CrossRef record and the paper
// itself: it cites Zwally 2002 and Das 2008 (not Price 2008). Cited by
// Leeson 2015, Christoffersen 2018, Lai 2021 and Stevens 2026 (DOI
// 10.1038/nature09618 in each CrossRef reference list) and by Rines
// 2026 (\citep{schoof_ice-sheet_2010} in main.tex); NOT by Stevens 2015
// or Stevens 2024 (no such DOI or title in either list). One author, so
// its label has no "et al.".

export interface TimelinePaper {
  id: string
  /** On-screen label over the card: "Das et al., 2008" ("Schoof, 2010"
   *  for a single author). */
  label: string
  /** First author surname (label = `${first} et al., ${year}`). */
  first: string
  /** Full author list as printed, surnames + initials, for the card. */
  authors: string
  title: string
  journal: string
  /** Masthead form for the card ("Nat. Commun."). */
  journalShort: string
  year: number
  /** Fractional year for the axis position (year + month/12). */
  when: number
  doi: string | null
  /** Where a click goes. Defaults to https://doi.org/<doi>. */
  url?: string
  /** ids of the other timeline papers in this paper's reference list. */
  cites: string[]
  /**
   * A bullet (≤ 5 words, no full stop) naming the paper's defining
   * finding. Shown ONLY while the paper is highlighted (hovered, or walked
   * by the Introduction's NEXT) — the director asked for these, meaning
   * to edit them himself, so they are a deliberate exception to the
   * no-narration rule. He then cut them to at most one short sentence,
   * or just five words that need not be a sentence — a bullet point; the
   * old sentences sit in a `was:` comment beside each entry for
   * comparison. The current summaries are THE DIRECTOR'S OWN WORDS,
   * verbatim but for the first capital; '' = no caption at all (he
   * wanted no summary of his own paper).
   */
  summary: string
}

export const TIMELINE_PAPERS: TimelinePaper[] = [
  {
    id: 'zwally2002',
    label: 'Zwally et al., 2002',
    first: 'Zwally',
    authors: 'H. J. Zwally, W. Abdalati, T. Herring, K. Larson, J. Saba, K. Steffen',
    title: 'Surface Melt-Induced Acceleration of Greenland Ice-Sheet Flow',
    journal: 'Science',
    journalShort: 'Science',
    year: 2002,
    when: 2002 + 6 / 12,
    doi: '10.1126/science.1072708',
    cites: [],
    // was: "GPS on the ice sheet showed summer flow speeding up in step with surface melt: meltwater reaches the bed and lubricates it."
    // then (five words): "Summer melt speeds up flow"
    summary: 'Summer surface melt accelerates ice flow',
  },
  {
    id: 'price2008',
    label: 'Price et al., 2008',
    first: 'Price',
    authors: 'S. F. Price, A. J. Payne, G. A. Catania, T. A. Neumann',
    title: 'Seasonal acceleration of inland ice via longitudinal coupling to marginal ice',
    journal: 'Journal of Glaciology',
    journalShort: 'J. Glaciol.',
    year: 2008,
    when: 2008 + 1 / 12,
    doi: '10.3189/002214308784886117',
    cites: ['zwally2002'],
    // was: "Modelled how a lubricated margin drags the ice inland of it along too: seasonal speed-up transmitted by longitudinal stress coupling."
    // then (five words): "Margin speed-up couples inland"
    summary: 'Ice margin conditions accelerate ice flow',
  },
  {
    id: 'das2008',
    label: 'Das et al., 2008',
    first: 'Das',
    authors: 'S. B. Das, I. Joughin, M. D. Behn, I. M. Howat, M. A. King, D. Lizarralde, M. P. Bhatia',
    title: 'Fracture Propagation to the Base of the Greenland Ice Sheet During Supraglacial Lake Drainage',
    journal: 'Science',
    journalShort: 'Science',
    year: 2008,
    when: 2008 + 4 / 12,
    doi: '10.1126/science.1153360',
    cites: ['zwally2002'],
    // was: "Watched North Lake drain to the bed through a kilometre of ice in under two hours, the first direct proof of hydro-fracture through the ice sheet."
    // then (five words): "Lake drainage fractures to bed"
    summary: 'Observed surface-to-bed pathways: hydrofracture driven lake drainage',
  },
  {
    id: 'schoof2010',
    label: 'Schoof, 2010',
    first: 'Schoof',
    authors: 'C. Schoof',
    title: 'Ice-sheet acceleration driven by melt supply variability',
    journal: 'Nature',
    journalShort: 'Nature',
    year: 2010,
    when: 2010 + 11 / 12,
    doi: '10.1038/nature09618',
    cites: ['zwally2002', 'das2008'],
    // was: "Modelled the drainage system at the bed: steady melt carves efficient channels that slow the sliding, so it is sudden pulses of water, like a lake draining, that speed the ice up."
    // then (five words): "Pulses of melt speed ice"
    summary: 'Meltwater injection rate modulates ice flow',
  },
  {
    id: 'leeson2015',
    label: 'Leeson et al., 2015',
    first: 'Leeson',
    authors: 'A. A. Leeson, A. Shepherd, K. Briggs, I. Howat, X. Fettweis, M. Morlighem, E. Rignot',
    title: 'Supraglacial lakes on the Greenland ice sheet advance inland under warming climate',
    journal: 'Nature Climate Change',
    journalShort: 'Nat. Clim. Change',
    year: 2015,
    when: 2015 + 0 / 12,
    doi: '10.1038/nclimate2463',
    cites: ['zwally2002', 'das2008', 'schoof2010'],
    // was: "Projected lakes spreading roughly 100 km further inland by 2060, putting drainages over thicker, colder ice that has never seen them."
    // then (five words): "Lakes advance inland with warming"
    summary: 'Lake presence to advance inland under warming climate',
  },
  {
    id: 'stevens2015',
    label: 'Stevens et al., 2015',
    first: 'Stevens',
    authors: 'L. A. Stevens, M. D. Behn, J. J. McGuire, S. B. Das, I. Joughin, T. Herring, D. E. Shean, M. A. King',
    title: 'Greenland supraglacial lake drainages triggered by hydrologically induced basal slip',
    journal: 'Nature',
    journalShort: 'Nature',
    year: 2015,
    when: 2015 + 5 / 12,
    doi: '10.1038/nature14480',
    cites: ['zwally2002', 'das2008', 'price2008', 'leeson2015'],
    // was: "A GPS array around North Lake caught the trigger: basal slip hours before drainage puts the lake basin in tension and opens the fracture."
    summary: 'Basal slip triggers lake drainage',
  },
  {
    id: 'christoffersen2018',
    label: 'Christoffersen et al., 2018',
    first: 'Christoffersen',
    authors: 'P. Christoffersen, M. Bougamont, A. Hubbard, S. H. Doyle, S. Grigsby, R. Pettersson',
    title: 'Cascading lake drainage on the Greenland Ice Sheet triggered by tensile shock and fracture',
    journal: 'Nature Communications',
    journalShort: 'Nat. Commun.',
    year: 2018,
    when: 2018 + 2 / 12,
    doi: '10.1038/s41467-018-03420-8',
    cites: ['zwally2002', 'das2008', 'price2008', 'schoof2010', 'leeson2015', 'stevens2015'],
    // was: "One drainage's tensile shock can fracture and drain its neighbours in turn, a cascade of lakes emptying within hours across tens of kilometres."
    // then (five words): "Drainages cascade via tensile shock"
    summary: 'Lake drainage cascades may be possible via long-range tensile shock',
  },
  {
    id: 'lai2021',
    label: 'Lai et al., 2021',
    first: 'Lai',
    authors: 'C.-Y. Lai, L. A. Stevens, D. L. Chase, T. T. Creyts, M. D. Behn, S. B. Das, H. A. Stone',
    title: 'Hydraulic transmissivity inferred from ice-sheet relaxation following Greenland supraglacial lake drainages',
    journal: 'Nature Communications',
    journalShort: 'Nat. Commun.',
    year: 2021,
    when: 2021 + 5 / 12,
    doi: '10.1038/s41467-021-24186-6',
    cites: ['zwally2002', 'das2008', 'schoof2010', 'stevens2015', 'christoffersen2018'],
    // was: "Read the ice's slow settling after North Lake drainages as a gauge of the bed, inferring the hydraulic transmissivity of the drainage system below."
    // then (five words): "Post-drainage relaxation reveals bed transmissivity"
    summary: 'Post-drainage subglacial blister dynamics',
  },
  {
    id: 'stevens2024',
    label: 'Stevens et al., 2024',
    first: 'Stevens',
    authors: 'L. A. Stevens, S. B. Das, M. D. Behn, J. J. McGuire, C.-Y. Lai, I. Joughin, S. Larochelle, M. Nettles',
    title: 'Elastic Stress Coupling Between Supraglacial Lakes',
    journal: 'JGR Earth Surface',
    journalShort: 'JGR Earth Surf.',
    year: 2024,
    when: 2024 + 4 / 12,
    doi: '10.1029/2023JF007481',
    cites: ['das2008', 'price2008', 'leeson2015', 'stevens2015'],
    // was: "Quantified the elastic stress one drainage transfers to a neighbouring basin: how far, and how strongly, a drainage can push the next lake toward fracture."
    // then (five words): "Elastic stress couples neighbouring lakes"; the
    // director, after re-reading the abstract, settled on the current line
    summary: 'Elastic stress couples nearby lakes',
  },
  {
    id: 'stevens2026',
    label: 'Stevens et al., 2026',
    first: 'Stevens',
    authors: 'L. A. Stevens, M. Nettles, S. Larochelle, M. Okal, E. Falconer, N. Turner, J. Rines, C.-Y. Lai, G. Lu',
    title: 'Ice-sheet hydro-fracture not advanced inland by lower-elevation lake drainages in Kalaallit Nunaat',
    journal: 'Nature Communications',
    journalShort: 'Nat. Commun.',
    year: 2026,
    when: 2026 + 4 / 12,
    doi: '10.1038/s41467-026-73033-z',
    cites: ['das2008', 'price2008', 'schoof2010', 'leeson2015', 'stevens2015', 'christoffersen2018', 'lai2021', 'stevens2024', 'rines2026'],
    // was: "Tested the cascade going uphill: lower-elevation drainages do not trigger hydro-fracture inland, so the inland advance needs another route."
    // then (five words): "Hydro-fracture not advanced inland"
    summary: 'Hydrofracture not advanced inland by lower elevation lake drainages',
  },
  {
    id: 'rines2026',
    label: 'Rines et al., 2026',
    first: 'Rines',
    authors: 'J. H. Rines, C.-Y. Lai, Y. Wang',
    title: 'Longitudinal stress induced by basal slippery patch',
    journal: 'Journal of Glaciology',
    journalShort: 'J. Glaciol.',
    year: 2026,
    when: 2026 + 7 / 12,
    doi: '10.1017/jog.2026.10192',
    cites: ['das2008', 'schoof2010', 'leeson2015', 'stevens2015', 'christoffersen2018', 'lai2021', 'stevens2024', 'stevens2026'],
    // was: "The stress a slippery patch at the bed sends to the surface, and how far it reaches: the coupling length that decides whether one drainage can reach the next lake."
    // then (five words): "Slippery patch sets coupling length"; then the
    // director asked for no summary of his own paper — no caption (the
    // takeaway card is the Introduction's last word instead).
    summary: '',
  },
]

/** Year-axis extent (inclusive years, half a year of margin each side). */
export const TIMELINE_YEAR_MIN = 2001.5
export const TIMELINE_YEAR_MAX = 2027.5

export function paperUrl(p: TimelinePaper): string | null {
  if (p.url) return p.url
  if (p.doi) return `https://doi.org/${p.doi}`
  return null
}
