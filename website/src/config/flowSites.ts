// The call-outs on the Introduction's "Greenland flows" step (the
// director's brief: point out a few key locations on the ice sheet —
// Jakobshavn and the same three sites the speed/anomaly page highlights,
// NEGIS, Summit Station — with little sticks pointing to the regions, a
// label naming each, and its average annual velocity beside it).
//
// THE NUMBERS are sampled from the SAME field the drape is coloured from:
// ITS_LIVE v2.1 120 m Greenland mosaic, `v` = "climatological [2014-2024]
// velocity" (per pixel a weighted least-squares line through the MEAN
// ANNUAL velocities 2014-2024, evaluated at 1 Jan 2018) — the multi-year
// mean annual surface speed, which is what the colour bar shows.
//   source  cinematic/source_data/data/ITS_LIVE_velocity_120m_RGI05A_0000_V02.1.nc
//   script  cinematic/scene_01_intro/sample_flow_sites.py (prints this table)
//   method  the median of `v` over a 2 × 2 km box centred on the marker
//           (Russell: over the seasons steps' own 40 × 40 km Russell /
//           Isunnguata Sermia box, the box step 2 plots in m/yr), NaN
//           excluded; the label rounds to two significant figures.
// Cross-check vs the seasons manifest (NASA MEaSUREs NSIDC-0731 v5, the
// seasons boxes, mean of 112–119 monthly box medians): Russell 91.7 vs
// ITS_LIVE 93.9 (+2 %); Petermann 1,273 vs 1,235 (−3 %). Jakobshavn's
// seasons box straddles the trunk's north margin (200–7,900 m/yr inside
// it), so its median depends on pixel size: 1,026 vs 1,519 at 120 m,
// 1,181 at 840 m (+15 %) — the call-out samples the trunk centreline.
//
// Placement: each label sits beside the object on its `side`, clear of
// the land (GRIS_ENVELOPE) and of the colour bar, the pills and the corner
// link — solved every frame in IntroFlowSites.vue from the projected
// anchors, so it holds at any viewport.

export interface FlowSite {
  id: string
  /** The label (the seasons steps' names for the three shared sites). */
  name: string
  /** Marker (on the ice surface), degrees. */
  lat: number
  lon: number
  /** Median ITS_LIVE `v` over the footprint, m/yr, unrounded. */
  speed: number
  /** What was sampled (for the record; not drawn). */
  footprint: string
  /** Which side of the object the label goes. */
  side: 'W' | 'E'
  /** Preferred vertical offset of the label from the dot, in label heights (+ down). */
  dy: number
}

export const FLOW_SITES: FlowSite[] = [
  {
    id: 'petermann',
    name: 'Petermann',
    lat: 80.6339,
    lon: -60.4578,
    speed: 1226.4,
    footprint: 'grounding zone, the seasons box centre (EPSG:3413 −271, −980 km); 2 km box p10–p90 1,210–1,239',
    side: 'W',
    dy: 0,
  },
  {
    id: 'jakobshavn',
    name: 'Jakobshavn',
    lat: 69.1012,
    lon: -49.4613,
    speed: 7153.0,
    footprint: 'trunk centreline ~10 km above the 2016 front (−178, −2281.4 km); p10–p90 6,371–7,634; the drape’s 480 m cells: 6,812',
    side: 'W',
    dy: -0.35,
  },
  {
    id: 'russell',
    name: 'Russell / Isunnguata Sermia',
    lat: 67.1473,
    lon: -49.46,
    speed: 93.9,
    footprint: 'the seasons box, 40 × 40 km, 10–50 km inland (−215…−175, −2520…−2480 km); p10–p90 53–130',
    side: 'W',
    dy: 0.35,
  },
  {
    id: 'negis',
    name: 'NEGIS',
    lat: 76.9654,
    lon: -30.7089,
    speed: 114.1,
    footprint: 'trunk centreline ~200 km below EastGRIP (350, −1374 km), 55 m/yr ice either side; p10–p90 114–115',
    side: 'E',
    dy: 0,
  },
  {
    id: 'summit',
    name: 'Summit Station',
    lat: 72.5796,
    lon: -38.4592,
    speed: 1.4,
    footprint: 'the station (216.6, −1888.8 km); p10–p90 1.2–1.5, ITS_LIVE v_error ~1 m/yr (noise level)',
    side: 'E',
    dy: 0,
  },
]

/** Two significant figures, en-US grouping: 7153 → "7,200", 93.9 → "94", 1.4 → "1.4". */
export function flowSpeedLabel(v: number): string {
  if (!(v > 0)) return '0'
  const d = Math.floor(Math.log10(v))
  const step = Math.pow(10, d - 1)
  const digits = Math.max(0, 1 - d)
  const r = Number((Math.round(v / step) * step).toFixed(digits))
  return r.toLocaleString('en-US', { maximumFractionDigits: digits })
}

/** The object's west and east land edges per half-degree of latitude
 *  [lat, lonW, lonE]: the westmost / eastmost land or ice (BedMachine
 *  Greenland v6 `mask` ≥ 1 at 600 m, mainland + islands ≥ 300 km²,
 *  Canada excluded). Projected as screen anchors so a label can sit just
 *  outside the land at its own height. */
export const GRIS_ENVELOPE: [number, number, number][] = [
  [59.75, -44.87, -43.13], [60.25, -45.62, -43.04], [60.75, -48.41, -42.63], [61.25, -49.11, -42.4],
  [61.75, -49.72, -42.09], [62.25, -50.26, -42.11], [62.75, -50.59, -41.45], [63.25, -51.38, -40.77],
  [63.75, -51.63, -40.51], [64.25, -52.21, -40.16], [64.75, -52.23, -40.21], [65.25, -52.76, -38.83],
  [65.75, -53.51, -35.95], [66.25, -53.69, -34.49], [66.75, -53.83, -33.77], [67.25, -53.95, -33.31],
  [67.75, -53.79, -32.04], [68.25, -53.62, -27.65], [68.75, -53.14, -25.52], [69.25, -54.27, -24.05],
  [69.75, -54.96, -22.33], [70.25, -54.83, -21.54], [70.75, -54.59, -21.48], [71.25, -55.51, -21.64],
  [71.75, -55.85, -21.91], [72.25, -55.62, -21.94], [72.75, -55.89, -22.07], [73.25, -55.9, -20.41],
  [73.75, -56.73, -20.26], [74.25, -57.49, -18.99], [74.75, -57.52, -18.32], [75.25, -58.67, -17.67],
  [75.75, -67.26, -18.45], [76.25, -69.62, -18.46], [76.75, -71.29, -18.18], [77.25, -71.35, -18.18],
  [77.75, -72.26, -18.89], [78.25, -73.02, -21.03], [78.75, -72.46, -19.14], [79.25, -68.78, -18.86],
  [79.75, -65.04, -17.2], [80.25, -67.48, -15.7], [80.75, -66.77, -13.34], [81.25, -64.53, -11.52],
  [81.75, -61.93, -11.73], [82.25, -60.16, -18.91], [82.75, -48.46, -19.79], [83.25, -47.14, -24.11],
  [83.75, -38.95, -26.6],
]

/** The Globe screen anchors for the step: the five markers on the ice
 *  surface (`fs:<id>`) and the land envelope on the sphere (`fe:w:<i>`,
 *  `fe:e:<i>` — coast points, sea level, so no DEM lookups per frame). */
export const FLOW_ANCHORS: { id: string; lat: number; lon: number; surface?: boolean; lift?: number }[] = [
  ...FLOW_SITES.map((s) => ({ id: `fs:${s.id}`, lat: s.lat, lon: s.lon, surface: true, lift: 0.0004 })),
  ...GRIS_ENVELOPE.flatMap(([lat, w, e], i) => [
    { id: `fe:w:${i}`, lat, lon: w },
    { id: `fe:e:${i}`, lat, lon: e },
  ]),
]
