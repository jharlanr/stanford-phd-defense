// The software repositories behind the
// dissertation, for the /repos page. Descriptions are the repos' own
// one-liners (GitHub "About"), checked against GitHub when added;
// every repo is public. `work` = where on this site the
// repo's work lives (in-site pills), plus the paper where one names it.
// ORDER: the chapters' repos first, in chapter order, then the work
// beyond them. Add a row here and the table follows.
import type { SectionId } from './sections'

export interface RepoWorkLink {
  label: string
  /** In-site section … */
  section?: SectionId
  /** … or an Additional-Work sub-page … */
  page?: 'mgsim' | 'terminal-bench'
  /** … or an outbound link (paper DOI). */
  href?: string
}

export interface RepoDef {
  owner: string
  name: string
  href: string
  description: string
  work: RepoWorkLink[]
}

export const REPOS: RepoDef[] = [
  {
    owner: 'jharlanr',
    name: 'sat-tile-stack',
    href: 'https://github.com/jharlanr/sat-tile-stack',
    description: 'Create ML-ready datasets from satellite imagery.',
    work: [{ label: 'Chapter 3 · ESSD', section: 'chapter3' }],
  },
  {
    owner: 'jharlanr',
    name: 'cloudy-tile',
    href: 'https://github.com/jharlanr/cloudy-tile',
    description: 'Helper package to classify satellite-derived imagery tiles as useful or not.',
    work: [{ label: 'Chapter 3 · ESSD', section: 'chapter3' }],
  },
  {
    owner: 'YaoGroup',
    name: 'lake-vision',
    href: 'https://github.com/YaoGroup/lake-vision',
    description: 'Constraining surface-to-bed meltwater pathways on the Greenland Ice Sheet.',
    work: [
      { label: 'Chapter 3 · ESSD', section: 'chapter3' },
      { label: 'Classifying at scale · Additional Work', section: 'additional-work' },
    ],
  },
  {
    owner: 'Stanford-Mineral-X',
    name: 'multigrid-sgsim',
    href: 'https://github.com/Stanford-Mineral-X/multigrid-sgsim',
    description: 'mgsim is a Python package for stochastic interpolation of airborne geophysical data.',
    work: [
      { label: 'Computers & Geosciences 2026', href: 'https://doi.org/10.1016/j.cageo.2026.106201' },
      { label: 'MGSIM bed ensemble', page: 'mgsim' },
    ],
  },
  {
    // Added with the persistent-lake-IDs Additional-Work card's door.
    owner: 'jharlanr',
    name: 'supraglacial-lakes',
    href: 'https://github.com/jharlanr/supraglacial-lakes',
    description: 'A living database of supraglacial lakes with persistent IDs (Greenland first).',
    work: [{ label: 'Persistent lake IDs · Additional Work', section: 'additional-work' }],
  },
]
