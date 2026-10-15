// The coupling-length step's footprints as the Globe's screen anchors
// (config/couplingLength.ts holds the data and where each item came from).
// SectionMotivation publishes CPL_ANCHORS through the Globe's
// `screenAnchors` prop; CouplingMap reads their projections back from
// `window.__globeAnchorScreens` every frame, by the ids built here.
import {
  C18_DOMAIN,
  C18_LAKES,
  C18_SHOCK,
  COUPLING_PAPERS,
  L21_LAKES,
  S24_LAKES,
  S24_STATIONS,
  S26_HF,
  S26_NAMED,
  S26_ROI,
  S26_STATIONS,
  type CouplingPaperId,
  type LatLon,
} from '../config/couplingLength'

export type CplKind =
  | 'area' // filled region (the tensile shock)
  | 'outline' // dashed boundary (a model domain, a region of interest)
  | 'dots' // lakes (small filled circles)
  | 'stations' // GPS / GNSS receivers (small triangles)
  | 'ring' // a true-size circle (a blister radius)
  | 'rule' // the scale rule (two ends)

export interface CplShape {
  key: string
  paper: CouplingPaperId
  kind: CplKind
  pts: LatLon[]
  /** Emphasised members of a dots set (named lakes) — bigger + outlined. */
  big?: boolean
}

const R_EARTH_KM = 6371.0
const DEG = Math.PI / 180

/** A true-size circle of radius rKm about `c`, as `n` lat/lon points. */
function circle(c: LatLon, rKm: number, n = 40): LatLon[] {
  const out: LatLon[] = []
  for (let i = 0; i <= n; i++) {
    const t = (i / n) * 2 * Math.PI
    const dN = rKm * Math.sin(t)
    const dE = rKm * Math.cos(t)
    out.push([c[0] + (dN / R_EARTH_KM) / DEG, c[1] + (dE / (R_EARTH_KM * Math.cos(c[0] * DEG))) / DEG])
  }
  return out
}

const rule = (id: CouplingPaperId): LatLon[] => {
  const p = COUPLING_PAPERS.find((q) => q.id === id)!
  return [p.rule.from, p.rule.to]
}

// Drawing order = list order (later on top): the big regions first, the
// small end members last so they are never buried.
export const CPL_SHAPES: CplShape[] = [
  // Christoffersen 2018 — the model domain, the tensile shock, the cascade.
  { key: 'c18dom', paper: 'christoffersen2018', kind: 'outline', pts: C18_DOMAIN },
  ...C18_SHOCK.map((ring, i) => ({ key: `c18shk${i}`, paper: 'christoffersen2018' as const, kind: 'area' as const, pts: ring })),
  { key: 'c18lk', paper: 'christoffersen2018', kind: 'dots', pts: C18_LAKES },
  { key: 'c18rule', paper: 'christoffersen2018', kind: 'rule', pts: rule('christoffersen2018') },
  // Stevens 2026 — the region of interest, its hydro-fractures, the array.
  { key: 's26roi', paper: 'stevens2026', kind: 'outline', pts: S26_ROI },
  { key: 's26hf', paper: 'stevens2026', kind: 'dots', pts: S26_HF.map(([a, b]) => [a, b] as LatLon) },
  { key: 's26st', paper: 'stevens2026', kind: 'stations', pts: S26_STATIONS.map(([, a, b]) => [a, b] as LatLon) },
  {
    key: 's26nm',
    paper: 'stevens2026',
    kind: 'dots',
    big: true,
    pts: S26_NAMED.filter(([n]) => n.startsWith('L2')).map(([, a, b]) => [a, b] as LatLon),
  },
  { key: 's26rule', paper: 'stevens2026', kind: 'rule', pts: rule('stevens2026') },
  // Lai 2021 — the blisters, true radius, at its three lakes.
  ...L21_LAKES.flatMap((l, li) =>
    l.rKm.map((r, ri) => ({ key: `l21r${li}_${ri}`, paper: 'lai2021' as const, kind: 'ring' as const, pts: circle(l.at, r) })),
  ),
  // Stevens 2024 — the 2012 GPS array and L1A–D, then its rule on top.
  { key: 's24st', paper: 'stevens2024', kind: 'stations', pts: S24_STATIONS },
  { key: 's24lk', paper: 'stevens2024', kind: 'dots', big: true, pts: S24_LAKES.map((l) => l.at) },
  { key: 's24rule', paper: 'stevens2024', kind: 'rule', pts: rule('stevens2024') },
]

/** Lift above the displaced ice surface (world units) — keeps the marks
 *  off the relief without floating visibly. */
const LIFT = 0.0003

export const CPL_ANCHORS = CPL_SHAPES.flatMap((s) =>
  s.pts.map((p, i) => ({ id: `cpl:${s.key}:${i}`, lat: p[0], lon: p[1], surface: true, lift: LIFT })),
)

// ── the North Lake loupe ──────────────────────────────────────────────
// Stevens 2024's footprint (L1A–D, 2–6 km apart, a ~100 km² GPS array) and
// Lai 2021's North Lake blisters are a few pixels on the regional view, so
// a loupe magnifies a LOUPE_R_KM circle around North Lake: a plan view
// (true shape, turned to the map's heading), linked to its circle on the
// ice. Features are local east/north km from LOUPE_CENTER.
export const LOUPE_CENTER: LatLon = [68.73, -49.5]
export const LOUPE_R_KM = 7

function kmOffset(c: LatLon, eastKm: number, northKm: number): LatLon {
  return [c[0] + northKm / R_EARTH_KM / DEG, c[1] + eastKm / (R_EARTH_KM * Math.cos(c[0] * DEG)) / DEG]
}
function toPlan(p: LatLon): [number, number] {
  return [
    (p[1] - LOUPE_CENTER[1]) * DEG * R_EARTH_KM * Math.cos(LOUPE_CENTER[0] * DEG),
    (p[0] - LOUPE_CENTER[0]) * DEG * R_EARTH_KM,
  ]
}

export const LOUPE_ANCHORS = [
  { id: 'cpl:loupe:c', lat: LOUPE_CENTER[0], lon: LOUPE_CENTER[1], surface: true, lift: LIFT },
  { id: 'cpl:loupe:n', ...ll(kmOffset(LOUPE_CENTER, 0, 1)), surface: true, lift: LIFT },
  { id: 'cpl:loupe:e', ...ll(kmOffset(LOUPE_CENTER, 1, 0)), surface: true, lift: LIFT },
  ...circle(LOUPE_CENTER, LOUPE_R_KM, 48).map((p, i) => ({ id: `cpl:loupe:ring:${i}`, lat: p[0], lon: p[1], surface: true, lift: LIFT })),
]
function ll(p: LatLon): { lat: number; lon: number } {
  return { lat: p[0], lon: p[1] }
}

export interface LoupeItem {
  key: string
  paper: CouplingPaperId
  kind: 'dots' | 'stations' | 'ring' | 'rule'
  /** Plan km (east, north) from LOUPE_CENTER. */
  pts: [number, number][]
  big?: boolean
}
const within = (p: [number, number]) => Math.hypot(p[0], p[1]) <= LOUPE_R_KM + 0.5
const S26_SQ1 = S26_STATIONS.filter(([n]) => n.startsWith('SQ1')).map(([, a, b]) => toPlan([a, b]))
export const LOUPE_ITEMS: LoupeItem[] = [
  ...L21_LAKES.filter((l) => l.name === 'North Lake').flatMap((l) =>
    l.rKm.map((r, i) => ({ key: `lp-l21-${i}`, paper: 'lai2021' as const, kind: 'ring' as const, pts: circle(l.at, r).map(toPlan) })),
  ),
  { key: 'lp-s26st', paper: 'stevens2026', kind: 'stations', pts: S26_SQ1.filter(within) },
  { key: 'lp-s24st', paper: 'stevens2024', kind: 'stations', pts: S24_STATIONS.map(toPlan).filter(within) },
  { key: 'lp-s24lk', paper: 'stevens2024', kind: 'dots', big: true, pts: S24_LAKES.map((l) => toPlan(l.at)) },
  { key: 'lp-s24rule', paper: 'stevens2024', kind: 'rule', pts: rule('stevens2024').map(toPlan) },
]
/** The loupe's lake names (Stevens 2024's own), plan km. */
export const LOUPE_NAMES = S24_LAKES.map((l) => ({ name: l.name, at: toPlan(l.at) }))

export const CPL_ALL_ANCHORS = [...CPL_ANCHORS, ...LOUPE_ANCHORS]
