// Chapter 2's RESULTS + IMPLICATIONS beats (from the director's brief) —
// the data behind them.
//
//   ch02/sim/phase_space_v2.json    the stress-space points (Fig. 5 recipe:
//                                   polygon-mean σ_t1/σ_t2 per neighbour,
//                                   both models; build_sim_domains.py) —
//                                   v2: the elastic x = the
//                                   superposed σ^V_pre + Δσ^E, and every
//                                   point's x1_pre/x2_pre (viscous pre)
//   ch02/results/results.json       per center lake: the flat Δσ_t1 figure
//                                   frame (EPSG:3413 north-up, image uv),
//                                   catalog rings, the +100 kPa contours;
//                                   the IMPLICATIONS composite (the seven
//                                   drainages stacked, flow-aligned km)
//   ch02/results/diff_{e,v}_<id>.png  the flat Δσ_t1 figures (±1 MPa)
//   ch02/results/impl_{e,v}.png       the seven-lake composites (unused
//                                     since beat 9 became the chosen lake's)
//   ch02/results/impl_lakes.json      the IMPLICATIONS figure per center
//                                     lake: +100 kPa contour, upstream reach,
//                                     peak, area, catalog rings — model
//                                     frame km (x downstream, y left of flow)
//   ch02/results/impl_{e,v}_<id>.png  its Δσ_t1 fields, inferno 0 → 1 MPa,
//                                     turned 180° (ice flows right → left)
//   ch02/results/impl_lakes_v2.json + impl2_{e,v}_<id>.png  the same, in
//                                     the block's seismic ±1 MPa
//   ch02/results/impl_lakes_v3.json + impl3_{e,v}_<id>.png  the same
//                                     numbers drawn the block's way round —
//                                     ice flows LEFT → RIGHT (what the page
//                                     reads); the sidecar's
//                                     `display` carries the mapping
//   ch02/sim/simstress_t2_{e,v}_<id>.png  Δσ_t2 block drapes (σ_t2 beats)
//   ch02/eq/<name>.svg                LaTeX labels (config/ch2Eqs.ts)
// Bakes: cinematic/scene_ch02/build_results_assets.py, build_impl_lakes.py,
// build_results_eqs.py.
import { mediaUrl } from './media'
import type { PhaseSpaceFile } from './simLakes'
import type { Ch2EqName } from './ch2Eqs'
import type { Ch2Model } from './ch2Beats'

export interface Ch2ResultLake {
  id: string
  num: number
  half_km: number
  bbox_half_km: number
  flow_angle_deg: number
  /** The rotated model domain's corners, image uv. */
  square: [number, number][]
  lakes: {
    num: number
    cls: 'cyan' | 'gray' | 'black' | 'dashcyan' | 'dashgray' | 'magenta'
    center: boolean
    phase: boolean
    rings: [number, number][][]
    /** Ring centroid, image uv. */
    c: [number, number]
    local_km: [number, number]
  }[]
  models: Record<Ch2Model, {
    image: string
    /** Δσ_t1 = +100 kPa, image uv polylines. */
    contour100: [number, number][][]
    peak_kpa: number
    area100_km2: number
    reach100_km: number
  }>
  /** The stress-space neighbours in the flow-aligned frame (km). */
  neighbours: { center: number; num: number; cls: string; x: number; y: number }[]
}

export interface Ch2ResultsFile {
  level_kpa: number
  vlim_kpa: number
  /** Half-size of the flow-aligned composite frame (km). */
  half_km: number
  composite: Record<Ch2Model, {
    image: string
    contour100_km: [number, number][][]
    peak_kpa: number
    area100_km2: number
    upstream100_km: number
  }>
  lakes: Record<string, Ch2ResultLake>
  drapes: Record<string, { stress_t2_e: string; stress_t2_v: string }>
}

/** How the sidecar's model-frame km land on the page (and in its PNGs):
 *  screen-x = half + sx·x, screen-y = half + sy·y. v3 (the director asked
 *  for ice flowing left to right) = { sx: 1, sy: −1 }, the
 *  block's own frame; v2 had no field and was the 180° turn { −1, 1 }. */
export interface Ch2ImplDisplay {
  sx: 1 | -1
  sy: 1 | -1
}
/** One center lake's IMPLICATIONS figure (impl_lakes_v3.json). Coordinates
 *  in the model frame, km: x downstream, y to the left of flow, origin =
 *  the drained lake. Drawn by the file's `display` mapping (copied onto
 *  each lake by `loadCh2Impl`), the same one its PNG fields were baked in. */
export interface Ch2ImplLake {
  num: number
  half_km: number
  display: Ch2ImplDisplay
  models: Record<Ch2Model, {
    image: string
    contour100_km: [number, number][][]
    peak_kpa: number
    area100_km2: number
    /** Farthest-upstream extent of Δσ_t1 > 100 kPa (km); = half_km when
     *  it runs to the window's upstream edge (a lower bound). */
    upstream100_km: number
  }>
  lakes: {
    num: number
    cls: 'cyan' | 'gray' | 'black' | 'dashcyan' | 'dashgray' | 'magenta'
    center: boolean
    phase: boolean
    rings_km: [number, number][][]
  }[]
}
export interface Ch2ImplFile {
  level_kpa: number
  vlim_kpa: number
  display?: Ch2ImplDisplay
  lakes: Record<string, Ch2ImplLake>
}

let resultsP: Promise<Ch2ResultsFile | null> | null = null
let phaseP: Promise<PhaseSpaceFile | null> | null = null
let implP: Promise<Ch2ImplFile | null> | null = null

function getJson<T>(key: string): Promise<T | null> {
  return fetch(mediaUrl(key))
    .then((r) => (r.ok ? (r.json() as Promise<T>) : null))
    .catch(() => null)
}

/** One in-flight fetch per file, shared across mounts. A failed fetch is
 *  forgotten so the next caller retries. */
export function loadCh2Results(): Promise<Ch2ResultsFile | null> {
  if (!resultsP) {
    resultsP = getJson<Ch2ResultsFile>('ch02/results/results.json').then((j) => {
      if (!j) resultsP = null
      return j
    })
  }
  return resultsP
}
export function loadCh2Impl(): Promise<Ch2ImplFile | null> {
  if (!implP) {
    // v2: the same numbers, the fields re-baked in the block's seismic
    // ±1 MPa (impl2_{e,v}_<id>.png), the scale the director chose.
    // v3: the same again, ice flowing left → right
    // (impl3_{e,v}_<id>.png); the file says how it is drawn.
    implP = getJson<Ch2ImplFile>('ch02/results/impl_lakes_v3.json').then((j) => {
      if (!j) implP = null
      else {
        const d: Ch2ImplDisplay = j.display ?? { sx: -1, sy: 1 }
        for (const lk of Object.values(j.lakes)) lk.display = d
      }
      return j
    })
  }
  return implP
}
export function loadCh2Phase(): Promise<PhaseSpaceFile | null> {
  if (!phaseP) {
    phaseP = getJson<PhaseSpaceFile>('ch02/sim/phase_space_v2.json').then((j) => {
      if (!j) phaseP = null
      return j
    })
  }
  return phaseP
}

export function ch2ResultUrl(file: string): string {
  return mediaUrl(`ch02/results/${file}`)
}
export function ch2EqUrl(name: Ch2EqName): string {
  return mediaUrl(`ch02/eq/${name}.svg`)
}

/** The block's Δσ_t2 drape for a lake + model (the σ_t2 beats). Built
 *  from the naming rule so the block needs no results.json round trip. */
export function ch2T2DrapeUrl(lakeId: string, model: Ch2Model): string {
  return mediaUrl(`ch02/sim/simstress_t2_${model === 'elastic' ? 'e' : 'v'}_${lakeId}.png`)
}

/** ONE fixed stress-space frame for every diagram of the results walk
 *  (beats 3–8 — the director asked for fixed x and y axis scales on the
 *  stress-space diagrams): the same ±1000 kPa on both
 *  axes for σ_t1 and σ_t2, elastic and viscous, so the frame never
 *  rescales between beats and only the points move. It holds every
 *  point of every lake (phase_space.json max |value|: σ_t1 426 kPa,
 *  viscous Δσ_t1 at 2283; σ_t2 845 kPa, elastic σ_t2^post at 2296).
 *  Labelled ticks every 500 kPa, a fainter grid every 250. */
export const CH2_AXIS_KPA = 1000
export const CH2_AXIS_STEP = 500
export const CH2_AXIS_MINOR = 250
