// The Introduction's "seasons" steps (from the director's brief): ten
// years of NASA MEaSUREs monthly speed mosaics (NSIDC-0731 v5) on the
// globe, month by month, so the audience watches the ice speed up every
// summer.
//
// The globe does NOT swap colour frames. It keeps the "Greenland flows"
// drape (shared/greenland_speed_nasa_v1.webp) and recolours it in the
// shader from two data textures (cinematic/scene_01_intro/
// bake_velocity_series.py, header "WHAT THE GLOBE SHOWS"):
//   · speed_t_v1.webp  — the drape's own log-speed fraction t (8192 × 3152)
//   · frames/m_YYYYMM.webp — per month, lossless RGB (2600 × 1000):
//       R = 128 + 256 · Δ   Δ = w·(log10 v_month − log10 v_median), decades
//       G = 128 + 127 · pct / lim   seasonal anomaly vs a 12-month median
//       B = 255 where the anomaly is valid (observed / interpolated)
// so a month at its median speed IS the drape, pixel for pixel, and the
// Speed | Anomaly switch is a uniform, not a new download.
//
// Everything the page draws about the data (dates, coverage, colour stops,
// the region curves) comes from the bake's manifest — never typed here.

import { mediaUrl } from './media'

/** R2 prefix (new assets get new names; ASSET_VERSION is not bumped). */
export const SEASONS_PREFIX = 'intro/seasons/'
export const SEASONS_MANIFEST_KEY = `${SEASONS_PREFIX}manifest.json`
export const SEASONS_STATIC_KEY = `${SEASONS_PREFIX}speed_t_v1.webp`

export function seasonsUrl(file: string): string {
  return mediaUrl(SEASONS_PREFIX + file)
}

export interface SeasonFrame {
  /** "2019-07" */
  ym: string
  /** Relative to SEASONS_PREFIX, e.g. "frames/m_201907.webp". */
  file: string
  /** Observed fraction of the ice the globe shows monthly (w > 0.5). */
  observed: number
  bytes: number
}

export interface SeasonRegion {
  name: string
  label: string
  kind: 'land' | 'marine' | 'interior'
  site: boolean
  centre_latlon: [number, number]
  corners_latlon: [number, number][]
  /** m/yr per month (gaps linearly interpolated). */
  speed: number[]
  /** m/yr per month, null where < 50 % of the box was observed. */
  speed_obs: (number | null)[]
  interpolated: boolean[]
  anomaly_pct: (number | null)[]
  summer_peak_vs_winter: Record<
    string,
    { winter_median: number; summer_peak: number; peak_month: string; peak_pct: number }
  >
}

export interface SeasonsManifest {
  grid: { frame_width: number; frame_height: number; static_width: number; static_height: number }
  speed_colour: { vmin: number; vmax: number }
  /** blend_mps: the globe shows the month at or above [1], the multi-year
   *  composite at or below [0] (m/yr; log-linear between). */
  delta: { scale: number; blend_mps: [number, number] }
  anomaly_colour: {
    lim: number
    /** [fraction 0..1 of −lim..+lim, '#rrggbb'] */
    stops: [number, string][]
    neutral_grey: number
    fade_mps: [number, number]
  }
  start_at: string
  frames: SeasonFrame[]
  region_months: string[]
  regions: Record<string, SeasonRegion>
}

let manifestPromise: Promise<SeasonsManifest> | null = null
/** The manifest, fetched once per page load (retried once). */
export function loadSeasonsManifest(): Promise<SeasonsManifest> {
  if (!manifestPromise) {
    const get = async (): Promise<SeasonsManifest> => {
      const r = await fetch(mediaUrl(SEASONS_MANIFEST_KEY))
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      return (await r.json()) as SeasonsManifest
    }
    manifestPromise = get().catch((e) => {
      console.warn('[seasons] manifest fetch failed, retrying once:', e)
      return new Promise<void>((res) => window.setTimeout(res, 1200)).then(get)
    })
    manifestPromise.catch(() => {
      manifestPromise = null
    })
  }
  return manifestPromise
}

/** The regions the curve panel draws, in legend order: the land-terminating
 *  sector first (the point), then the two big marine outlets. */
export const SEASON_CURVE_REGIONS = ['russell_isunnguata', 'sermeq_kujalleq', 'petermann'] as const

// ── Meltwater runoff (the director's point: increased velocities follow
// increased melt) ────────────────────────────────────────────────────────
// Monthly runoff over the SAME region boxes, drawn as a quiet filled area
// behind the land sector's speed curve. RACMO2.3p2 downscaled to 1 km
// (Noël), via Zenodo doi:10.5281/zenodo.15013761; baked by
// cinematic/scene_01_intro/bake_runoff_series.py. Its public record ends
// Dec 2023, so 2024 has no runoff (null — never filled).

/** The baked file under SEASONS_PREFIX; null hides the runoff everywhere. */
export const RUNOFF_SOURCE: string | null = 'runoff_racmo_v1.json'
/** The views that draw it — the director first asked for it on the
 *  anomaly page, then for the RACMO runoff already overlaid on the speed
 *  page (once the anomaly beat left the path). */
export const RUNOFF_VIEWS: readonly ('speed' | 'anom')[] = ['speed', 'anom']

export interface SeasonsRunoff {
  model: string
  /** The legend entry, e.g. "runoff · RACMO2.3p2". */
  label: string
  date_range: [string, string]
  /** Same months as the manifest's region_months. */
  months: string[]
  regions: Record<
    string,
    {
      label: string
      /** mm w.e. per month, area mean over the box's ice; null = no data. */
      runoff_mm: (number | null)[]
      /** Gt per month, box total. */
      runoff_gt: (number | null)[]
    }
  >
}

let runoffPromise: Promise<SeasonsRunoff | null> | null = null
/** The runoff series, fetched once per page load; null when switched off
 *  or unavailable (the panel then draws exactly what it drew before). */
export function loadSeasonsRunoff(): Promise<SeasonsRunoff | null> {
  if (!RUNOFF_SOURCE) return Promise.resolve(null)
  if (!runoffPromise) {
    const url = seasonsUrl(RUNOFF_SOURCE)
    runoffPromise = fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json() as Promise<SeasonsRunoff>
      })
      .catch((e) => {
        console.warn('[seasons] runoff fetch failed:', e)
        runoffPromise = null
        return null
      })
  }
  return runoffPromise
}

/** Months per second when playing (the director asked for a slower
 *  monthly rate, about 2 fps — speed and anomaly alike). */
export const SEASON_MONTHS_PER_S = 2
/** Crossfade between consecutive months, ms. */
export const SEASON_XFADE_MS = 150

const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
/** "2019-07" → "JUL 2019" */
export function seasonStamp(ym: string): { month: string; year: string } {
  return { month: MONTHS[parseInt(ym.slice(5, 7), 10) - 1] ?? '', year: ym.slice(0, 4) }
}

/** CSS gradient for the anomaly bar, bottom (−lim) → top (+lim). */
export function anomalyGradient(stops: [number, string][]): string {
  return stops.map(([f, c]) => `${c} ${(f * 100).toFixed(2)}%`).join(', ')
}
