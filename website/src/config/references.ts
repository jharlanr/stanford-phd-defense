// The References page (/references): every paper,
// report and dataset the site leans on, organised by chapter or by author.
//
// PROVENANCE (every entry checked at its source — never written from memory):
//   · journal articles: title, author order, venue, volume, issue/pages and
//     year copied from the DOI's CrossRef record
//     (api.crossref.org/works/<doi>); author names are CrossRef's given
//     names reduced to initials.
//   · the two IPCC chapters: the official citation printed on the
//     chapter's ipcc.ch page (AR6 WG1 Ch. 9; SROCC Ch. 4), DOI included.
//   · the datasets: the "Data Citation" block of the NSIDC landing page
//     (BedMachine v6, ITS_LIVE NSIDC-0776 v2) and the DataCite record of
//     the Stanford Digital Repository deposit.
//   · ITS_LIVE: its-live.jpl.nasa.gov "How to Cite" asks for BOTH the
//     auto-RIFT paper (Gardner et al. 2018) and the dataset. The site's
//     velocity map is ITS_LIVE_velocity_120m_RGI05A_0000_V02.1 (a v2
//     regional mosaic, cinematic/scene_01_intro/), hence NSIDC-0776 v2.
//   · the literature-timeline papers are NOT retyped: they come from
//     config/timeline.ts (bylines CrossRef-checked there); only the
//     volume/pages below are added, from the same CrossRef records.
//   · the AGU poster comes from config/fracture.ts (authors checked against
//     the AGU24 meeting API, abstract 1598183).
//   · the PNAS manuscript (in review, no DOI yet): title + author order
//     from the submitted main.tex (the PNAS Overleaf zip).
//   · the CONCEPT papers (after a Q&A rehearsal the director asked for
//     these and other relevant literature in the references, under a
//     separate 'concept' toggle — just authors, year, title and a one-line
//     summary each): every byline, year, venue, volume and pages from the
//     DOI's CrossRef record (a scratch lookup script: a bibliographic
//     query by title + first author, then the published DOI fetched
//     directly where the query matched a preprint — Grinsted 2024,
//     Williamson 2018, Crozier 2018 — or nothing — Ignéczi 2018). Two
//     have no CrossRef article: Weertman 1973 (IAHS Publ. 95, cited as
//     the literature cites it, no DOI) and Culberg 2025 (an EGU25
//     abstract, its abstract DOI). The one-line summaries are the
//     narrator's, not quotes.
//
// `key` records ONE number each source supports, with where it is said,
// so the presenter can quote it aloud. It is NOT rendered (narrator rule).
//
// ORDER: none needed — the page sorts. Chapter view = groups in talk
// order, each alphabetical by first author; Author view = one list by
// first-author surname, then year.

import { TIMELINE_PAPERS, paperUrl } from './timeline'
import { FRACTURE, FRACTURE_LINKS } from './fracture'

export type ChapterKey =
  | 'introduction'
  | 'chapter1'
  | 'chapter2'
  | 'chapter3'
  | 'additional-work'

/** Groups in talk order, with the headings the page prints. */
export const REF_CHAPTERS: { key: ChapterKey; label: string; short: string }[] = [
  { key: 'introduction', label: 'Introduction', short: 'Introduction' },
  { key: 'chapter1', label: 'Chapter 1 · JOG', short: 'Chapter 1' },
  { key: 'chapter2', label: 'Chapter 2 · PNAS', short: 'Chapter 2' },
  { key: 'chapter3', label: 'Chapter 3 · ESSD', short: 'Chapter 3' },
  { key: 'additional-work', label: 'Additional Work', short: 'Additional Work' },
]

/** The Concept view's sections, in the director's order. A paper may
 *  belong to several (`concepts` on the entry) and is listed under each. */
export type ConceptKey = 'hydrofracture' | 'observations' | 'moulins' | 'subglacial-hydrology' | 'stress-transmission'
export const REF_CONCEPTS: { key: ConceptKey; label: string }[] = [
  { key: 'hydrofracture', label: 'Hydrofracture' },
  { key: 'observations', label: 'Observations' },
  { key: 'moulins', label: 'Moulins' },
  { key: 'subglacial-hydrology', label: 'Subglacial hydrology' },
  { key: 'stress-transmission', label: 'Stress transmission' },
]

export interface Reference {
  id: string
  /** Authors as printed, initials first ("M. R. van den Broeke"). */
  authors: string[]
  /** True when `authors` is only the first few of a longer list. */
  etAl?: boolean
  /** Total number of authors when `authors` is truncated. */
  nAuthors?: number
  year: number
  title: string
  venue: string
  volume?: string
  /** Pages or article number. */
  pages?: string
  doi?: string
  /** Where a click goes. Defaults to https://doi.org/<doi>. */
  url?: string
  /** Publication stage for unpublished work — the ribbon's words. */
  status?: 'in review' | 'in revision' | 'in final revision'
  chapters: ChapterKey[]
  /** The Concept view's sections this paper sits in (none = not listed there). */
  concepts?: ConceptKey[]
  /** The Concept view's one line under the title. */
  summary?: string
  /** One verified number this source supports, and where (not rendered). */
  key?: string
}

// ── The literature timeline (Introduction step 3) ──────────────────────────
// Reused from config/timeline.ts. Every one is an Introduction reference;
// Rines 2026 is also Chapter 1's paper, Stevens 2026 also the fieldwork
// card's paper (Additional Work).

const TIMELINE_EXTRA: Record<string, { volume: string; pages: string; chapters?: ChapterKey[] }> = {
  zwally2002: { volume: '297', pages: '218–222' },
  price2008: { volume: '54', pages: '213–219' },
  das2008: { volume: '320', pages: '778–781' },
  schoof2010: { volume: '468', pages: '803–806' },
  leeson2015: { volume: '5', pages: '51–55' },
  stevens2015: { volume: '522', pages: '73–76' },
  christoffersen2018: { volume: '9', pages: '1064' },
  lai2021: { volume: '12', pages: '3955' },
  stevens2024: { volume: '129', pages: 'e2023JF007481' },
  stevens2026: { volume: '17', pages: '4598', chapters: ['introduction', 'additional-work'] },
  rines2026: { volume: '72', pages: 'e76', chapters: ['introduction', 'chapter1'] },
}

const FROM_TIMELINE: Reference[] = TIMELINE_PAPERS.map((p) => {
  const extra = TIMELINE_EXTRA[p.id]
  return {
    id: p.id,
    authors: p.authors.split(', '),
    year: p.year,
    title: p.title,
    venue: p.journal,
    volume: extra?.volume,
    pages: extra?.pages,
    doi: p.doi ?? undefined,
    url: paperUrl(p) ?? undefined,
    chapters: extra?.chapters ?? ['introduction'],
  }
})

// ── Introduction: Greenland and sea level ──────────────────────────────────

const INTRO_SEA_LEVEL: Reference[] = [
  {
    id: 'morlighem2017',
    authors: ['M. Morlighem', 'C. N. Williams', 'E. Rignot'],
    etAl: true,
    nAuthors: 32,
    year: 2017,
    title:
      'BedMachine v3: Complete Bed Topography and Ocean Bathymetry Mapping of Greenland From Multibeam Echo Sounding Combined With Mass Conservation',
    venue: 'Geophysical Research Letters',
    volume: '44',
    doi: '10.1002/2017GL074954',
    chapters: ['introduction'],
    key: 'Sea-level potential of the whole ice sheet 7.42 ± 0.05 m, 7 cm more than earlier estimates (abstract).',
  },
  {
    id: 'imbie2020',
    authors: ['The IMBIE Team'],
    year: 2020,
    title: 'Mass balance of the Greenland Ice Sheet from 1992 to 2018',
    venue: 'Nature',
    volume: '579',
    pages: '233–239',
    doi: '10.1038/s41586-019-1855-2',
    chapters: ['introduction'],
    key: 'Greenland lost 3,902 ± 342 Gt of ice 1992–2018 = 10.8 ± 0.9 mm of sea-level rise; losses peaked at 345 ± 66 Gt/yr in 2011; 50.3 % from surface mass balance, 49.7 % from glacier dynamics (abstract). Online 2019-12-10, print 2020-03-12. (The thesis bib keys it shepherd_mass_2020.)',
  },
  {
    id: 'otosaka2023',
    authors: ['I. N. Otosaka', 'A. Shepherd', 'E. R. Ivins'],
    etAl: true,
    nAuthors: 68,
    year: 2023,
    title: 'Mass balance of the Greenland and Antarctic ice sheets from 1992 to 2020',
    venue: 'Earth System Science Data',
    volume: '15',
    pages: '1597–1616',
    doi: '10.5194/essd-15-1597-2023',
    chapters: ['introduction'],
    key: 'Greenland lost 169 ± 9 Gt/yr on average 1992–2020, from 86 Gt/yr (2017) to 444 Gt/yr (2019); both ice sheets together 21.0 ± 1.9 mm of sea level (abstract).',
  },
  {
    id: 'mouginot2019',
    authors: [
      'J. Mouginot', 'E. Rignot', 'A. A. Bjørk', 'M. van den Broeke', 'R. Millan',
      'M. Morlighem', 'B. Noël', 'B. Scheuchl', 'M. Wood',
    ],
    year: 2019,
    title: 'Forty-six years of Greenland Ice Sheet mass balance from 1972 to 2018',
    venue: 'Proceedings of the National Academy of Sciences',
    volume: '116',
    pages: '9239–9244',
    doi: '10.1073/pnas.1904242116',
    chapters: ['introduction'],
    key: 'Greenland has raised sea level 13.7 ± 1.1 mm since 1972, half of it in 2010–2018; loss rose from 41 ± 17 Gt/yr (1990s) to 286 ± 20 Gt/yr (2010–2018), sixfold since the 1980s (abstract + significance).',
  },
  {
    id: 'vandenbroeke2016',
    authors: [
      'M. R. van den Broeke', 'E. M. Enderlin', 'I. M. Howat', 'P. Kuipers Munneke',
      'B. P. Y. Noël', 'W. J. van de Berg', 'E. van Meijgaard', 'B. Wouters',
    ],
    year: 2016,
    title: 'On the recent contribution of the Greenland ice sheet to sea level change',
    venue: 'The Cryosphere',
    volume: '10',
    pages: '1933–1946',
    doi: '10.5194/tc-10-1933-2016',
    chapters: ['introduction'],
    key: 'About 60 % of the mass loss since 1991 comes from surface mass balance (more melt and runoff), the rest from ice discharge (abstract).',
  },
  {
    id: 'king2020',
    authors: [
      'M. D. King', 'I. M. Howat', 'S. G. Candela', 'M. J. Noh', 'S. Jeong',
      'B. P. Y. Noël', 'M. R. van den Broeke', 'B. Wouters', 'A. Negrete',
    ],
    year: 2020,
    title: 'Dynamic ice loss from the Greenland Ice Sheet driven by sustained glacier retreat',
    venue: 'Communications Earth & Environment',
    volume: '1',
    pages: '1',
    doi: '10.1038/s43247-020-0001-2',
    chapters: ['introduction'],
    key: 'Widespread glacier retreat in 2000–2005 caused a step increase in discharge and a new state of sustained mass loss; 4–5 % speed-up per km of retreat (abstract).',
  },
  {
    id: 'goelzer2020',
    authors: ['H. Goelzer', 'S. Nowicki', 'A. Payne'],
    etAl: true,
    nAuthors: 42,
    year: 2020,
    title:
      'The future sea-level contribution of the Greenland ice sheet: a multi-model ensemble study of ISMIP6',
    venue: 'The Cryosphere',
    volume: '14',
    pages: '3071–3096',
    doi: '10.5194/tc-14-3071-2020',
    chapters: ['introduction'],
    key: 'ISMIP6: 90 ± 50 mm (RCP8.5) and 32 ± 17 mm (RCP2.6) of sea-level rise from Greenland by 2100 (abstract).',
  },
  {
    id: 'aschwanden2019',
    authors: [
      'A. Aschwanden', 'M. A. Fahnestock', 'M. Truffer', 'D. J. Brinkerhoff',
      'R. Hock', 'C. Khroulev', 'R. Mottram', 'S. A. Khan',
    ],
    year: 2019,
    title: 'Contribution of the Greenland Ice Sheet to sea level over the next millennium',
    venue: 'Science Advances',
    volume: '5',
    pages: 'eaav9396',
    doi: '10.1126/sciadv.aav9396',
    chapters: ['introduction'],
    key: 'Greenland could add 5–33 cm of sea level by 2100 and very likely becomes ice-free within a millennium without large emission cuts (abstract; it quotes 7.2 m SLE for the ice sheet).',
  },
  {
    id: 'box2022',
    authors: [
      'J. E. Box', 'A. Hubbard', 'D. B. Bahr', 'W. T. Colgan', 'X. Fettweis', 'K. D. Mankoff',
      'A. Wehrlé', 'B. Noël', 'M. R. van den Broeke', 'B. Wouters', 'A. A. Bjørk', 'R. S. Fausto',
    ],
    year: 2022,
    title: 'Greenland ice sheet climate disequilibrium and committed sea-level rise',
    venue: 'Nature Climate Change',
    volume: '12',
    pages: '808–813',
    doi: '10.1038/s41558-022-01441-2',
    chapters: ['introduction'],
    key: 'The 2000–2019 climate already commits at least 274 ± 68 mm of sea-level rise (3.3 ± 0.9 % of the ice volume) whatever the 21st-century pathway; 2012 in perpetuity commits 782 ± 135 mm (abstract).',
  },
  {
    id: 'foxkemper2021',
    authors: [
      'B. Fox-Kemper', 'H. T. Hewitt', 'C. Xiao', 'G. Aðalgeirsdóttir', 'S. S. Drijfhout',
      'T. L. Edwards', 'N. R. Golledge', 'M. Hemer', 'R. E. Kopp', 'G. Krinner', 'A. Mix',
      'D. Notz', 'S. Nowicki', 'I. S. Nurhati', 'L. Ruiz', 'J.-B. Sallée', 'A. B. A. Slangen',
      'Y. Yu',
    ],
    year: 2021,
    title: 'Ocean, Cryosphere and Sea Level Change',
    venue:
      'Climate Change 2021: The Physical Science Basis. Contribution of Working Group I to the Sixth Assessment Report of the IPCC',
    pages: '1211–1362',
    doi: '10.1017/9781009157896.011',
    chapters: ['introduction'],
    key: 'Executive Summary: Greenland lost 4,890 [4,140–5,640] Gt over 1992–2020 = 13.5 [11.4–15.6] mm of GMSL rise; 243 Gt/yr in 2010–2019; likely 2100 contribution 0.01–0.10 m (SSP1-2.6), 0.04–0.13 m (SSP2-4.5), 0.09–0.18 m (SSP5-8.5).',
  },
  {
    id: 'oppenheimer2019',
    authors: [
      'M. Oppenheimer', 'B. C. Glavovic', 'J. Hinkel', 'R. van de Wal', 'A. K. Magnan',
      'A. Abd-Elgawad', 'R. Cai', 'M. Cifuentes-Jara', 'R. M. DeConto', 'T. Ghosh', 'J. Hay',
      'F. Isla', 'B. Marzeion', 'B. Meyssignac', 'Z. Sebesvari',
    ],
    year: 2019,
    title: 'Sea Level Rise and Implications for Low-Lying Islands, Coasts and Communities',
    venue: 'IPCC Special Report on the Ocean and Cryosphere in a Changing Climate',
    pages: '321–445',
    doi: '10.1017/9781009157964.006',
    chapters: ['introduction'],
    key: 'Executive Summary: GMSL rise 3.6 mm/yr over 2006–2015, and glaciers + ice sheets are now its dominant source; Sect. 4.2.2.2: Greenland 0.68 (0.64–0.72) mm/yr over 2012–2016.',
  },
]

// ── Data behind the Introduction's globe (and Chapter 1's maps) ────────────
// Chapter 1's data availability (thesis ch1_main.tex) names exactly these
// two products and versions.

const DATA: Reference[] = [
  {
    id: 'morlighem2025bedmachine',
    authors: ['M. Morlighem'],
    etAl: true,
    year: 2025,
    title: 'IceBridge BedMachine Greenland (IDBMG4, Version 6)',
    venue: 'NASA National Snow and Ice Data Center DAAC [data set]',
    doi: '10.5067/6B6B225B8V2D',
    chapters: ['introduction', 'chapter1'],
    key: 'The globe’s ice-surface and bed relief (cinematic/scene_01_intro/build_dem_texture.py reads BedMachineGreenland-v6.nc).',
  },
  {
    id: 'gardner2025itslive',
    authors: [
      'A. S. Gardner', 'M. Fahnestock', 'C. A. Greene', 'J. H. Kennedy', 'M. Liukis',
      'L. A. López', 'T. Scambos',
    ],
    year: 2025,
    title: 'MEaSUREs ITS_LIVE Regional Glacier and Ice Sheet Surface Velocities (NSIDC-0776, Version 2)',
    venue: 'NASA National Snow and Ice Data Center DAAC [data set]',
    doi: '10.5067/JQ6337239C96',
    chapters: ['introduction', 'chapter1'],
    key: 'The “Greenland flows” velocity map and streamlines (the 120 m v02.1 mosaic). NSIDC’s recommended citation says 2025; the DataCite record says 2024.',
  },
  {
    id: 'gardner2018',
    authors: [
      'A. S. Gardner', 'G. Moholdt', 'T. Scambos', 'M. Fahnstock', 'S. Ligtenberg',
      'M. van den Broeke', 'J. Nilsson',
    ],
    year: 2018,
    title: 'Increased West Antarctic and unchanged East Antarctic ice discharge over the last 7 years',
    venue: 'The Cryosphere',
    volume: '12',
    pages: '521–547',
    doi: '10.5194/tc-12-521-2018',
    chapters: ['introduction'],
    key: 'The auto-RIFT method behind ITS_LIVE velocities — ITS_LIVE asks that it be cited with the data set. (“Fahnstock” is spelled so in the CrossRef record.)',
  },
  // The Introduction's "seasons" steps: the monthly mosaics (checked
  // against the DataCite record of the DOI: title, sole creator
  // Joughin, publisher NSIDC DAAC, 2023; NSIDC's "Data Citation" block names
  // it NSIDC-0731 Version 5) and the paper that describes them (CrossRef).
  {
    id: 'joughin2023nsidc0731',
    authors: ['I. Joughin'],
    year: 2023,
    title: 'MEaSUREs Greenland Monthly Ice Sheet Velocity Mosaics from SAR and Landsat (NSIDC-0731, Version 5)',
    venue: 'NASA National Snow and Ice Data Center DAAC [data set]',
    doi: '10.5067/EGKZX6FXXM4P',
    chapters: ['introduction'],
    key: 'The "seasons" steps: 119 monthly mosaics Jan 2015 – Nov 2024 (800 m overview). The Russell / Isunnguata Sermia land-terminating sector runs ~85 m/yr in winter and 114–141 m/yr at its summer peak, +36 to +64 % every year (cinematic/data/intro/seasons/manifest.json).',
  },
  {
    id: 'joughin2018',
    authors: ['I. Joughin', 'B. E. Smith', 'I. Howat'],
    year: 2018,
    title: 'Greenland Ice Mapping Project: ice flow velocity variation at sub-monthly to decadal timescales',
    venue: 'The Cryosphere',
    volume: '12',
    pages: '2211–2227',
    doi: '10.5194/tc-12-2211-2018',
    chapters: ['introduction'],
    key: 'The paper describing the GIMP velocity products the monthly mosaics (NSIDC-0731) belong to; NSIDC asks that it be cited with the data set.',
  },
  // The anomaly step's meltwater runoff (the director's addition): RACMO2.3p2,
  // ERA5-forced, statistically downscaled to 1 km by B. Noël — the monthly
  // files as deposited on Zenodo with Vries et al. (2025, The Cryosphere
  // 19, 3897; its data statement names this DOI and says the downscaled
  // RACMO data "were previously published in Noël et al. (2019)", and it
  // cites Noël et al. 2016, 2019 for the downscaling). Checked:
  // the dataset from its DataCite record (title verbatim, sole creator
  // Vries, Zenodo, 2025, CC BY 4.0); the two papers from CrossRef.
  {
    id: 'vries2025racmo',
    authors: ['A. L. Vries'],
    year: 2025,
    title:
      'Data supporting: "Seasonal and interannual variability of freshwater sources for Greenland’s fjords" submitted to The Cryosphere special issue "Northern hydrology in transition – impacts of a changing cryosphere on water resources, ecosystems, and humans" on November 29, 2024 by Anneke Vries et al.',
    venue: 'Zenodo [data set]',
    doi: '10.5281/zenodo.15013761',
    chapters: ['introduction'],
    key: 'The runoff behind the Russell / Isunnguata Sermia curve (RACMO2.3p2 1 km monthly runoffcorr, 2015–2023; the record ends Dec 2023): 1.9–3.6 m w.e. a year over the box, 0 every January, peak every July at 0.82–1.37 m w.e. (2019 the largest). GrIS total 280–532 Gt/yr (cinematic/data/intro/seasons/runoff_racmo_v1.json).',
  },
  {
    id: 'noel2016',
    authors: [
      'B. Noël', 'W. J. van de Berg', 'H. Machguth', 'S. Lhermitte', 'I. Howat',
      'X. Fettweis', 'M. R. van den Broeke',
    ],
    year: 2016,
    title: 'A daily, 1 km resolution data set of downscaled Greenland ice sheet surface mass balance (1958–2015)',
    venue: 'The Cryosphere',
    volume: '10',
    pages: '2361–2377',
    doi: '10.5194/tc-10-2361-2016',
    chapters: ['introduction'],
    key: 'The statistical downscaling (corrections for elevation, bare-ice albedo and accumulation bias) from native RACMO2.3 output (11 km in this paper) to the 1 km GIMP grid and ice mask the runoff comes on (abstract).',
  },
  {
    id: 'noel2019',
    authors: ['B. Noël', 'W. J. van de Berg', 'S. Lhermitte', 'M. R. van den Broeke'],
    year: 2019,
    title: 'Rapid ablation zone expansion amplifies north Greenland mass loss',
    venue: 'Science Advances',
    volume: '5',
    pages: 'eaaw0123',
    doi: '10.1126/sciadv.aaw0123',
    chapters: ['introduction'],
    key: 'The 5.5 km RACMO2.3p2 run downscaled to 1 km that the Zenodo runoff files come from (Vries et al. 2025 data statement).',
  },
]

// ── The chapters' own papers and their key sources ─────────────────────────

const CHAPTERS: Reference[] = [
  {
    id: 'lai2026pnas',
    authors: [
      'C.-Y. Lai', 'J. H. Rines', 'N. B. Coffey', 'E. Lee', 'F. Clerc', 'J. P. Hilditch',
      'O. Gagliardini', 'L. A. Stevens',
    ],
    year: 2026,
    title: 'From blistering to sliding: Ice-sheet stress perturbations from water injection to the bed',
    venue: 'Proceedings of the National Academy of Sciences',
    status: 'in revision',
    chapters: ['chapter2'],
    key: 'Lai, Rines and Coffey are co-first authors (the manuscript’s equal-authorship note).',
  },
  // Niall Coffey's PhD thesis — Chapter 2's theory segment credits it beside
  // "Theory" (the director's credit line: Coffey 2026). Copied from the
  // thesis's .bib (@phdthesis coffey_thesis_2026); no
  // DOI or URL there, so no link.
  {
    id: 'coffey2026thesis',
    authors: ['N. B. Coffey'],
    year: 2026,
    title: 'On the Tensile Fracture of Glacial Ice',
    venue: 'PhD thesis, Stanford University',
    chapters: ['chapter2'],
    key: 'Credited beside “Theory” on Chapter 2’s slab beats (thesis bib key coffey_thesis_2026).',
  },
  {
    id: 'rines2026essd',
    authors: [
      'J. H. Rines', 'C.-Y. Lai', 'E. Abrahams', 'M. G. Shahin', 'N. B. Coffey', 'E. Lee',
      'L. A. Stevens',
    ],
    year: 2026,
    title:
      'A benchmark deep learning dataset for the classification of supraglacial lake drainage mechanism across the central-west Greenland Ice Sheet',
    venue: 'Earth System Science Data',
    doi: '10.5194/essd-2026-406',
    status: 'in final revision',
    chapters: ['chapter3'],
  },
  {
    id: 'rines2026sdr',
    authors: [
      'J. H. Rines', 'C.-Y. Lai', 'E. Abrahams', 'M. G. Shahin', 'N. B. Coffey', 'E. Lee',
      'L. A. Stevens',
    ],
    year: 2026,
    title: 'Central West Greenland Supraglacial Lake Drainage Classification Dataset (2018–2019)',
    venue: 'Stanford Digital Repository [data set]',
    doi: '10.25740/sf350xp4038',
    chapters: ['chapter3'],
  },
  // Chapter 1's Elmer/Ice model (the beat-3 corner link the director
  // asked for). CrossRef record of the DOI: 15
  // authors, GMD 6(4), 1299–1318, published 2013-08-22.
  {
    id: 'gagliardini2013',
    authors: [
      'O. Gagliardini', 'T. Zwinger', 'F. Gillet-Chaulet', 'G. Durand', 'L. Favier',
      'B. de Fleurian', 'R. Greve', 'M. Malinen', 'C. Martín', 'P. Råback',
      'J. Ruokolainen', 'M. Sacchettini', 'M. Schäfer', 'H. Seddik', 'J. Thies',
    ],
    year: 2013,
    title: 'Capabilities and performance of Elmer/Ice, a new-generation ice sheet model',
    venue: 'Geoscientific Model Development',
    volume: '6',
    pages: '1299–1318',
    doi: '10.5194/gmd-6-1299-2013',
    chapters: ['chapter1'],
    key: 'The full-Stokes finite-element model behind Chapter 1’s τxx paint and 2-D stress fields (cinematic/scene_ch01/build_theory_n1.py).',
  },
  {
    id: 'dunmire2021',
    authors: ['D. Dunmire', 'A. F. Banwell', 'N. Wever', 'J. T. M. Lenaerts', 'R. T. Datta'],
    year: 2021,
    title:
      'Contrasting regional variability of buried meltwater extent over 2 years across the Greenland Ice Sheet',
    venue: 'The Cryosphere',
    volume: '15',
    pages: '2983–3005',
    doi: '10.5194/tc-15-2983-2021',
    chapters: ['chapter3'],
    key: 'Source of the static lake boundary polygons the ESSD dataset uses (ESSD Sect. 2).',
  },
  {
    id: 'dunmire2025',
    authors: [
      'D. Dunmire', 'A. C. Subramanian', 'E. Hossain', 'M. O. Gani', 'A. F. Banwell',
      'H. Younas', 'B. Myers',
    ],
    year: 2025,
    title:
      'Greenland Ice Sheet Wide Supraglacial Lake Evolution and Dynamics: Insights From the 2018 and 2019 Melt Seasons',
    venue: 'Earth and Space Science',
    volume: '12',
    pages: 'e2024EA003793',
    doi: '10.1029/2024EA003793',
    chapters: ['chapter1', 'chapter2', 'chapter3'],
    key: 'The lake inventory and ID convention: 679 (2018) + 1,000 (2019) central-west lakes = ESSD’s 1,679; PNAS lake numbers follow it; JOG Fig. A1 draws its outlines.',
  },
]

// ── Additional Work ────────────────────────────────────────────────────────

const ADDITIONAL: Reference[] = [
  {
    id: 'rines2026cg',
    authors: ['J. H. Rines', 'Z. Yin', 'J. Kloeckner', 'J. Caers'],
    year: 2026,
    title: 'Interpolation of large-scale airborne geophysical data with uncertainty quantification',
    venue: 'Computers & Geosciences',
    volume: '215',
    pages: '106201',
    doi: '10.1016/j.cageo.2026.106201',
    chapters: ['additional-work'],
  },
  {
    id: 'xia2024agu',
    authors: FRACTURE.authors,
    year: 2024,
    title: FRACTURE.title,
    venue: `${FRACTURE.venue}, abstract ${FRACTURE.poster}`,
    url: FRACTURE_LINKS.find((l) => l.primary)?.href,
    chapters: ['additional-work'],
  },
]

// ── The Concept view's papers ──────────────────────────────────────────────
// Hydrofracture · Observations · Moulins · Subglacial hydrology · Stress
// transmission. Bylines from CrossRef (see PROVENANCE); summaries are the
// narrator's one line each.

const CONCEPTS: Reference[] = [
  {
    id: 'weertman1973',
    authors: ['J. Weertman'],
    year: 1973,
    title: 'Can a water-filled crevasse reach the bottom surface of a glacier?',
    venue: 'Symposium on the Hydrology of Glaciers, IAHS Publication 95',
    pages: '139–145',
    chapters: ['introduction', 'chapter2'],
    concepts: ['hydrofracture'],
    summary: 'Water is denser than ice, so a crevasse that stays full keeps propagating down.',
  },
  {
    id: 'vanderveen1998',
    authors: ['C. J. van der Veen'],
    year: 1998,
    title: 'Fracture mechanics approach to penetration of surface crevasses on glaciers',
    venue: 'Cold Regions Science and Technology',
    volume: '27',
    pages: '31–47',
    doi: '10.1016/s0165-232x(97)00022-0',
    chapters: ['introduction', 'chapter2'],
    concepts: ['hydrofracture'],
    summary: 'Linear elastic fracture mechanics for how deep a crevasse goes, with and without water.',
  },
  {
    id: 'vanderveen2007',
    authors: ['C. J. van der Veen'],
    year: 2007,
    title: 'Fracture propagation as means of rapidly transferring surface meltwater to the base of glaciers',
    venue: 'Geophysical Research Letters',
    volume: '34',
    pages: '2006GL028385',
    doi: '10.1029/2006gl028385',
    chapters: ['introduction', 'chapter2'],
    concepts: ['hydrofracture'],
    summary: 'A water-filled crack reaches the bed in hours, not seasons.',
  },
  {
    id: 'alley2005',
    authors: ['R. B. Alley', 'T. K. Dupont', 'B. R. Parizek', 'S. Anandakrishnan'],
    year: 2005,
    title: 'Access of surface meltwater to beds of sub-freezing glaciers: preliminary insights',
    venue: 'Annals of Glaciology',
    volume: '40',
    pages: '8–14',
    doi: '10.3189/172756405781813483',
    chapters: ['introduction', 'chapter2'],
    concepts: ['hydrofracture'],
    summary: 'The volume argument: the crack must stay full of water all the way down.',
  },
  {
    id: 'krawczynski2009',
    authors: ['M. J. Krawczynski', 'M. D. Behn', 'S. B. Das', 'I. Joughin'],
    year: 2009,
    title: 'Constraints on the lake volume required for hydro-fracture through ice sheets',
    venue: 'Geophysical Research Letters',
    volume: '36',
    pages: '2008GL036765',
    doi: '10.1029/2008gl036765',
    chapters: ['introduction', 'chapter2'],
    concepts: ['hydrofracture'],
    summary: 'The lake volume needed to drive a fracture through a kilometre of ice, made quantitative.',
  },
  {
    id: 'grinsted2024',
    authors: ['A. Grinsted', 'N. M. Rathmann', 'R. Mottram', 'A. M. Solgaard', 'J. Mathiesen', 'C. S. Hvidberg'],
    year: 2024,
    title: 'Failure strength of glacier ice inferred from Greenland crevasses',
    venue: 'The Cryosphere',
    volume: '18',
    pages: '1947–1957',
    doi: '10.5194/tc-18-1947-2024',
    chapters: ['introduction', 'chapter2'],
    concepts: ['hydrofracture', 'observations'],
    summary: 'A von Mises failure strength of about 265 kPa, read from where Greenland crevasses begin.',
  },
  {
    id: 'culberg2025',
    authors: ['R. Culberg', 'C.-Y. Lai', 'E. Mackie'],
    year: 2025,
    title: 'Von Mises Stress a Robust Predictor of Ice Slab Fracture in Greenland',
    venue: 'EGU General Assembly 2025, abstract EGU25-6996',
    doi: '10.5194/egusphere-egu25-6996',
    chapters: ['introduction', 'chapter2'],
    concepts: ['hydrofracture', 'observations'],
    summary: 'Von Mises stress predicts where ice slabs fracture in Greenland.',
  },
  {
    id: 'doyle2013',
    authors: ['S. H. Doyle', 'A. L. Hubbard', 'C. F. Dow', 'G. A. Jones', 'A. Fitzpatrick', 'A. Gusmeroli', 'B. Kulessa', 'K. Lindback', 'R. Pettersson', 'J. E. Box'],
    year: 2013,
    title: 'Ice tectonic deformation during the rapid in situ drainage of a supraglacial lake on the Greenland Ice Sheet',
    venue: 'The Cryosphere',
    volume: '7',
    pages: '129–140',
    doi: '10.5194/tc-7-129-2013',
    chapters: ['introduction', 'chapter3'],
    concepts: ['observations'],
    summary: 'GPS strain during a rapid drainage near Russell Glacier: the ice flexes and slips.',
  },
  {
    id: 'chudley2019',
    authors: ['T. R. Chudley', 'P. Christoffersen', 'S. H. Doyle', 'M. Bougamont', 'C. M. Schoonman', 'B. Hubbard', 'M. R. James'],
    year: 2019,
    title: 'Supraglacial lake drainage at a fast-flowing Greenlandic outlet glacier',
    venue: 'Proceedings of the National Academy of Sciences',
    volume: '116',
    pages: '25468–25477',
    doi: '10.1073/pnas.1913685116',
    chapters: ['introduction', 'chapter3'],
    concepts: ['observations'],
    summary: 'A drone watches the fracture cross a lake on a fast outlet glacier, with motion before the drain.',
  },
  {
    id: 'selmes2011',
    authors: ['N. Selmes', 'T. Murray', 'T. D. James'],
    year: 2011,
    title: 'Fast draining lakes on the Greenland Ice Sheet',
    venue: 'Geophysical Research Letters',
    volume: '38',
    pages: '2011GL047872',
    doi: '10.1029/2011gl047872',
    chapters: ['introduction', 'chapter3'],
    concepts: ['observations'],
    summary: 'A satellite census: about one lake in eight drains rapidly.',
  },
  {
    id: 'fitzpatrick2014',
    authors: ['A. A. W. Fitzpatrick', 'A. L. Hubbard', 'J. E. Box', 'D. J. Quincey', 'D. van As', 'A. P. B. Mikkelsen', 'S. H. Doyle', 'C. F. Dow', 'B. Hasholt', 'G. A. Jones'],
    year: 2014,
    title: 'A decade (2002–2012) of supraglacial lake volume estimates across Russell Glacier, West Greenland',
    venue: 'The Cryosphere',
    volume: '8',
    pages: '107–121',
    doi: '10.5194/tc-8-107-2014',
    chapters: ['introduction', 'chapter3'],
    concepts: ['observations'],
    summary: 'Ten years of lake volumes and drainage timing across Russell Glacier.',
  },
  {
    id: 'williamson2018',
    authors: ['A. G. Williamson', 'A. F. Banwell', 'I. C. Willis', 'N. S. Arnold'],
    year: 2018,
    title: 'Dual-satellite (Sentinel-2 and Landsat 8) remote sensing of supraglacial lakes in Greenland',
    venue: 'The Cryosphere',
    volume: '12',
    pages: '3045–3065',
    doi: '10.5194/tc-12-3045-2018',
    chapters: ['introduction', 'chapter3'],
    concepts: ['observations'],
    summary: 'Sentinel-2 and Landsat 8 together: the rapid-drainage detection the rate-based classes descend from.',
  },
  {
    id: 'williamson2017',
    authors: ['A. G. Williamson', 'N. S. Arnold', 'A. F. Banwell', 'I. C. Willis'],
    year: 2017,
    title: 'A Fully Automated Supraglacial lake area and volume Tracking ("FAST") algorithm: Development and application using MODIS imagery of West Greenland',
    venue: 'Remote Sensing of Environment',
    volume: '196',
    pages: '113–133',
    doi: '10.1016/j.rse.2017.04.032',
    chapters: ['introduction', 'chapter3'],
    concepts: ['observations'],
    summary: 'The FAST algorithm: lake area and volume tracked automatically from MODIS.',
  },
  {
    id: 'poinar2015',
    authors: ['K. Poinar', 'I. Joughin', 'S. B. Das', 'M. D. Behn', 'J. T. M. Lenaerts', 'M. R. van den Broeke'],
    year: 2015,
    title: 'Limits to future expansion of surface-melt-enhanced ice flow into the interior of western Greenland',
    venue: 'Geophysical Research Letters',
    volume: '42',
    pages: '1800–1807',
    doi: '10.1002/2015gl063192',
    chapters: ['introduction', 'chapter3'],
    concepts: ['observations', 'hydrofracture'],
    summary: 'Inland lakes rarely reach the bed: the surface strain rates are too low to open a crack.',
  },
  {
    id: 'hoffman2018',
    authors: ['M. J. Hoffman', 'M. Perego', 'L. C. Andrews', 'S. F. Price', 'T. A. Neumann', 'J. V. Johnson', 'G. Catania', 'M. P. Lüthi'],
    year: 2018,
    title: 'Widespread moulin formation during supraglacial lake drainages in Greenland',
    venue: 'Geophysical Research Letters',
    volume: '45',
    pages: '778–788',
    doi: '10.1002/2017gl075659',
    chapters: ['introduction', 'chapter3'],
    concepts: ['moulins', 'hydrofracture', 'observations'],
    summary: 'Drainages are the birthplace of moulins: many form by hydrofracture during a drainage, even outside the basin.',
  },
  {
    id: 'catania2010',
    authors: ['G. A. Catania', 'T. A. Neumann'],
    year: 2010,
    title: 'Persistent englacial drainage features in the Greenland Ice Sheet',
    venue: 'Geophysical Research Letters',
    volume: '37',
    pages: '2009GL041108',
    doi: '10.1029/2009gl041108',
    chapters: ['introduction', 'chapter3'],
    concepts: ['moulins'],
    summary: 'Radar-mapped moulins persist from year to year.',
  },
  {
    id: 'catania2008',
    authors: ['G. A. Catania', 'T. A. Neumann', 'S. F. Price'],
    year: 2008,
    title: 'Characterizing englacial drainage in the ablation zone of the Greenland ice sheet',
    venue: 'Journal of Glaciology',
    volume: '54',
    pages: '567–578',
    doi: '10.3189/002214308786570854',
    chapters: ['introduction', 'chapter3'],
    concepts: ['moulins'],
    summary: 'How dense the moulins are across the ablation zone, from radar.',
  },
  {
    id: 'smith2015',
    authors: ['L. C. Smith', 'V. W. Chu', 'K. Yang', 'C. J. Gleason', 'L. H. Pitcher', 'A. K. Rennermalm', 'C. J. Legleiter', 'A. E. Behar', 'B. T. Overstreet', 'S. E. Moustafa', 'M. Tedesco', 'R. R. Forster', 'A. L. LeWinter', 'D. C. Finnegan', 'Y. Sheng', 'J. Balog'],
    year: 2015,
    title: 'Efficient meltwater drainage through supraglacial streams and rivers on the southwest Greenland ice sheet',
    venue: 'Proceedings of the National Academy of Sciences',
    volume: '112',
    pages: '1001–1006',
    doi: '10.1073/pnas.1413024112',
    chapters: ['introduction', 'chapter3'],
    concepts: ['moulins'],
    summary: 'Most melt leaves through streams and rivers into moulins, not lake drainages.',
  },
  {
    id: 'andrews2018',
    authors: ['L. C. Andrews', 'M. J. Hoffman', 'T. A. Neumann', 'G. A. Catania', 'M. P. Lüthi', 'R. L. Hawley', 'K. M. Schild', 'C. Ryser', 'B. F. Morriss'],
    year: 2018,
    title: 'Seasonal evolution of the subglacial hydrologic system modified by supraglacial lake drainage in western Greenland',
    venue: 'Journal of Geophysical Research: Earth Surface',
    volume: '123',
    pages: '1479–1496',
    doi: '10.1029/2017jf004585',
    chapters: ['introduction', 'chapter3'],
    concepts: ['moulins', 'subglacial-hydrology'],
    summary: 'One drainage reorganises the subglacial system for the rest of the season.',
  },
  {
    id: 'yang2016',
    authors: ['K. Yang', 'L. C. Smith'],
    year: 2016,
    title: 'Internally drained catchments dominate supraglacial hydrology of the southwest Greenland Ice Sheet',
    venue: 'Journal of Geophysical Research: Earth Surface',
    volume: '121',
    pages: '1891–1910',
    doi: '10.1002/2016jf003927',
    chapters: ['introduction', 'chapter3'],
    concepts: ['moulins'],
    summary: 'Supraglacial catchments end in moulins.',
  },
  {
    id: 'koziol2017',
    authors: ['C. Koziol', 'N. Arnold', 'A. Pope', 'W. Colgan'],
    year: 2017,
    title: 'Quantifying supraglacial meltwater pathways in the Paakitsoq region, West Greenland',
    venue: 'Journal of Glaciology',
    volume: '63',
    pages: '464–476',
    doi: '10.1017/jog.2017.5',
    chapters: ['introduction', 'chapter3'],
    concepts: ['moulins'],
    summary: 'How meltwater splits among lakes, moulins and crevasses in the Paakitsoq region.',
  },
  {
    id: 'bartholomew2010',
    authors: ['I. Bartholomew', 'P. Nienow', 'D. Mair', 'A. Hubbard', 'M. A. King', 'A. Sole'],
    year: 2010,
    title: 'Seasonal evolution of subglacial drainage and acceleration in a Greenland outlet glacier',
    venue: 'Nature Geoscience',
    volume: '3',
    pages: '408–411',
    doi: '10.1038/ngeo863',
    chapters: ['introduction'],
    concepts: ['subglacial-hydrology'],
    summary: 'The seasonal switch to efficient drainage, seen from GPS on an outlet glacier.',
  },
  {
    id: 'sundal2011',
    authors: ['A. V. Sundal', 'A. Shepherd', 'P. Nienow', 'E. Hanna', 'S. Palmer', 'P. Huybrechts'],
    year: 2011,
    title: 'Melt-induced speed-up of Greenland ice sheet offset by efficient subglacial drainage',
    venue: 'Nature',
    volume: '469',
    pages: '521–524',
    doi: '10.1038/nature09740',
    chapters: ['introduction'],
    concepts: ['subglacial-hydrology'],
    summary: 'Warm years end up slower: efficient drainage offsets the melt-driven speed-up.',
  },
  {
    id: 'hoffman2011',
    authors: ['M. J. Hoffman', 'G. A. Catania', 'T. A. Neumann', 'L. C. Andrews', 'J. A. Rumrill'],
    year: 2011,
    title: 'Links between acceleration, melting, and supraglacial lake drainage of the western Greenland Ice Sheet',
    venue: 'Journal of Geophysical Research',
    volume: '116',
    pages: 'F04035',
    doi: '10.1029/2010jf001934',
    chapters: ['introduction'],
    concepts: ['subglacial-hydrology', 'observations'],
    summary: 'GPS stations respond to melt and to a lake drainage in West Greenland.',
  },
  {
    id: 'andrews2014',
    authors: ['L. C. Andrews', 'G. A. Catania', 'M. J. Hoffman', 'J. D. Gulley', 'M. P. Lüthi', 'C. Ryser', 'R. L. Hawley', 'T. A. Neumann'],
    year: 2014,
    title: 'Direct observations of evolving subglacial drainage beneath the Greenland Ice Sheet',
    venue: 'Nature',
    volume: '514',
    pages: '80–83',
    doi: '10.1038/nature13796',
    chapters: ['introduction'],
    concepts: ['subglacial-hydrology', 'moulins'],
    summary: 'Boreholes to the bed: an inefficient drainage system persists through the summer.',
  },
  {
    id: 'hewitt2013',
    authors: ['I. J. Hewitt'],
    year: 2013,
    title: 'Seasonal changes in ice sheet motion due to melt water lubrication',
    venue: 'Earth and Planetary Science Letters',
    volume: '371-372',
    pages: '16–25',
    doi: '10.1016/j.epsl.2013.04.022',
    chapters: ['introduction'],
    concepts: ['subglacial-hydrology'],
    summary: 'A coupled channel-and-cavity model of the seasonal cycle of ice motion.',
  },
  {
    id: 'werder2013',
    authors: ['M. A. Werder', 'I. J. Hewitt', 'C. G. Schoof', 'G. E. Flowers'],
    year: 2013,
    title: 'Modeling channelized and distributed subglacial drainage in two dimensions',
    venue: 'Journal of Geophysical Research: Earth Surface',
    volume: '118',
    pages: '2140–2158',
    doi: '10.1002/jgrf.20146',
    chapters: ['introduction'],
    concepts: ['subglacial-hydrology'],
    summary: 'GlaDS: channels and distributed drainage modelled together in two dimensions.',
  },
  {
    id: 'tedstone2015',
    authors: ['A. J. Tedstone', 'P. W. Nienow', 'N. Gourmelen', 'A. Dehecq', 'D. Goldberg', 'E. Hanna'],
    year: 2015,
    title: 'Decadal slowdown of a land-terminating sector of the Greenland Ice Sheet despite warming',
    venue: 'Nature',
    volume: '526',
    pages: '692–695',
    doi: '10.1038/nature15722',
    chapters: ['introduction'],
    concepts: ['subglacial-hydrology'],
    summary: 'A land-terminating sector slowed over a decade despite warming.',
  },
  {
    id: 'dow2015',
    authors: ['C. F. Dow', 'B. Kulessa', 'I. C. Rutt', 'V. C. Tsai', 'S. Pimentel', 'S. H. Doyle', 'D. van As', 'K. Lindbäck', 'R. Pettersson', 'G. A. Jones', 'A. Hubbard'],
    year: 2015,
    title: 'Modeling of subglacial hydrological development following rapid supraglacial lake drainage',
    venue: 'Journal of Geophysical Research: Earth Surface',
    volume: '120',
    pages: '1127–1147',
    doi: '10.1002/2014jf003333',
    chapters: ['introduction'],
    concepts: ['subglacial-hydrology'],
    summary: 'The subglacial response to a single rapid lake drainage, modelled.',
  },
  {
    id: 'barcilon1993',
    authors: ['V. Barcilon', 'D. R. MacAyeal'],
    year: 1993,
    title: 'Steady flow of a viscous ice stream across a no-slip/free-slip transition at the bed',
    venue: 'Journal of Glaciology',
    volume: '39',
    pages: '167–185',
    doi: '10.3189/s0022143000015811',
    chapters: ['chapter1', 'chapter2'],
    concepts: ['stress-transmission'],
    summary: 'The stress singularity where a no-slip bed becomes free-slip.',
  },
  {
    id: 'hutter1980',
    authors: ['K. Hutter', 'V. O. S. Olunloyo'],
    year: 1980,
    title: 'On the distribution of stress and velocity in an ice strip, which is partly sliding over and partly adhering to its bed, by using a Newtonian viscous approximation',
    venue: 'Proceedings of the Royal Society of London A',
    volume: '373',
    pages: '385–403',
    doi: '10.1098/rspa.1980.0155',
    chapters: ['chapter1', 'chapter2'],
    concepts: ['stress-transmission'],
    summary: 'The earliest analytic solution for an ice strip sliding over part of its bed.',
  },
  {
    id: 'schoof2004',
    authors: ['C. Schoof'],
    year: 2004,
    title: 'On the mechanics of ice-stream shear margins',
    venue: 'Journal of Glaciology',
    volume: '50',
    pages: '208–218',
    doi: '10.3189/172756504781830024',
    chapters: ['chapter1', 'chapter2'],
    concepts: ['stress-transmission'],
    summary: 'Ice-stream shear margins as slip transitions.',
  },
  {
    id: 'haseloff2015',
    authors: ['M. Haseloff', 'C. Schoof', 'O. Gagliardini'],
    year: 2015,
    title: 'A boundary layer model for ice stream margins',
    venue: 'Journal of Fluid Mechanics',
    volume: '781',
    pages: '353–387',
    doi: '10.1017/jfm.2015.503',
    chapters: ['chapter1', 'chapter2'],
    concepts: ['stress-transmission'],
    summary: 'A boundary layer at the no-slip to free-slip transition of an ice-stream margin.',
  },
  {
    id: 'mantelli2019',
    authors: ['E. Mantelli', 'M. Haseloff', 'C. Schoof'],
    year: 2019,
    title: 'Ice sheet flow with thermally activated sliding. Part 1: the role of advection',
    venue: 'Proceedings of the Royal Society A',
    volume: '475',
    pages: '20190410',
    doi: '10.1098/rspa.2019.0410',
    chapters: ['chapter1', 'chapter2'],
    concepts: ['stress-transmission'],
    summary: 'The frozen-to-sliding transition under thermal control.',
  },
  {
    id: 'gudmundsson2003',
    authors: ['G. H. Gudmundsson'],
    year: 2003,
    title: 'Transmission of basal variability to a glacier surface',
    venue: 'Journal of Geophysical Research: Solid Earth',
    volume: '108',
    pages: '2002JB002107',
    doi: '10.1029/2002jb002107',
    chapters: ['chapter1', 'chapter2'],
    concepts: ['stress-transmission', 'observations'],
    summary: 'Transfer functions: the ice is a low-pass filter on bed topography and slipperiness.',
  },
  {
    id: 'sergienko2013',
    authors: ['O. V. Sergienko'],
    year: 2013,
    title: 'Glaciological twins: basally controlled subglacial and supraglacial lakes',
    venue: 'Journal of Glaciology',
    volume: '59',
    pages: '3–8',
    doi: '10.3189/2013jog12j040',
    chapters: ['chapter2'],
    concepts: ['stress-transmission', 'observations'],
    summary: 'Surface lakes sit over bed lows: glaciological twins.',
  },
  {
    id: 'crozier2018',
    authors: ['J. Crozier', 'L. Karlstrom', 'K. Yang'],
    year: 2018,
    title: 'Basal control of supraglacial meltwater catchments  on the Greenland Ice Sheet',
    venue: 'The Cryosphere',
    volume: '12',
    pages: '3383–3407',
    doi: '10.5194/tc-12-3383-2018',
    chapters: ['chapter2', 'chapter3'],
    concepts: ['stress-transmission', 'observations'],
    summary: 'Lake basins are transmitted bed topography.',
  },
  {
    id: 'igneczi2018',
    authors: ['Á. Ignéczi', 'A. J. Sole', 'S. J. Livingstone', 'F. S. L. Ng', 'K. Yang'],
    year: 2018,
    title: 'Greenland Ice Sheet surface topography and drainage structure controlled by the transfer of basal variability',
    venue: 'Frontiers in Earth Science',
    volume: '6',
    pages: '101',
    doi: '10.3389/feart.2018.00101',
    chapters: ['chapter2', 'chapter3'],
    concepts: ['stress-transmission', 'observations'],
    summary: 'Surface topography and drainage structure across the ice sheet, set by the bed beneath.',
  },
]

/** Concepts + summaries for papers that already live above (the timeline's,
 *  the chapters'), so nothing is retyped. */
const CONCEPT_EXTRA: Record<string, { concepts: ConceptKey[]; summary: string }> = {
  zwally2002: { concepts: ['subglacial-hydrology'], summary: 'Summer melt reaches the bed and the ice sheet speeds up.' },
  price2008: { concepts: ['stress-transmission'], summary: 'Inland ice accelerates in summer through longitudinal coupling to the margin.' },
  das2008: { concepts: ['observations', 'hydrofracture', 'moulins'], summary: 'The first instrumented rapid drainage: uplift, speed-up, and a lake gone in hours.' },
  schoof2010: { concepts: ['subglacial-hydrology', 'stress-transmission'], summary: 'Channels versus cavities: more water need not mean faster flow.' },
  leeson2015: { concepts: ['observations'], summary: 'Lakes spread inland as the climate warms.' },
  stevens2015: { concepts: ['observations', 'hydrofracture', 'stress-transmission'], summary: 'Precursory basal slip opens the tensile stress that lets a lake hydrofracture.' },
  christoffersen2018: { concepts: ['observations', 'stress-transmission'], summary: 'Drainages cascade: one lake\'s drainage stresses its neighbours into draining.' },
  lai2021: { concepts: ['hydrofracture', 'stress-transmission'], summary: 'Which ice shelves are vulnerable to hydrofracture, from their flow stresses.' },
  stevens2024: { concepts: ['stress-transmission', 'hydrofracture'], summary: 'Elastic stress coupling between neighbouring lakes.' },
  stevens2026: { concepts: ['observations'], summary: 'Field observations of lake drainage in central-west Greenland.' },
  rines2026: { concepts: ['stress-transmission'], summary: 'The 1-D theory: a slippery patch sets a stress of ρgαℓ/4 at its edges, decaying over [x].' },
  lai2026pnas: { concepts: ['stress-transmission', 'hydrofracture'], summary: 'The 3-D models: blister then slip, and the stress fields each leaves at the surface.' },
  rines2026essd: { concepts: ['observations'], summary: 'The labelled Sentinel-2 dataset of how central-west Greenland\'s lakes drain.' },
  dunmire2021: { concepts: ['observations'], summary: 'Buried meltwater mapped across the ice sheet over two years.' },
  dunmire2025: { concepts: ['observations'], summary: 'Ice-sheet-wide lake evolution and the drainage classes the thesis builds on.' },
}

export const REFERENCES: Reference[] = [
  ...FROM_TIMELINE,
  ...INTRO_SEA_LEVEL,
  ...DATA,
  ...CHAPTERS,
  ...ADDITIONAL,
  ...CONCEPTS,
].map((r) => (CONCEPT_EXTRA[r.id] ? { ...r, ...CONCEPT_EXTRA[r.id] } : r))

/** The presenter, as bylines print him across the site. */
export const AUTHOR_NAMES = new Set(['J. H. Rines', 'J. Rines'])

export function refUrl(r: Reference): string | null {
  if (r.url) return r.url
  if (r.doi) return `https://doi.org/${r.doi}`
  return null
}

/** First author's surname for sorting: initials and a leading "The" dropped. */
export function sortName(r: Reference): string {
  const first = r.authors[0] ?? ''
  const tokens = first.split(' ').filter((t) => !/^([A-ZÀ-ɏ]\.-?)+$/.test(t) && t !== 'The')
  return tokens.join(' ').toLocaleLowerCase('en')
}

export function compareRefs(a: Reference, b: Reference): number {
  const byName = sortName(a).localeCompare(sortName(b), 'en')
  if (byName !== 0) return byName
  if (a.year !== b.year) return a.year - b.year
  return a.title.localeCompare(b.title, 'en')
}
