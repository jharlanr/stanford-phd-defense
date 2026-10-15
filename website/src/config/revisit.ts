// Additional Work → "Revisiting lake drainage papers" (the director's idea):
// the lakes Christoffersen et al. 2018 drain to the bed in the cascade of
// 6–10 June 2010, each with its own season of imagery to check the claim
// against — MODIS and Landsat 7 / ASTER in 2010, MODIS and Sentinel-2 in
// 2019. SectionRevisit.vue is the page (/additional-work/revisit);
// RevisitPlayer.vue plays one lake.
//
// Everything is baked to R2 under ONE prefix. New bytes = a new name (every
// R2 object is `immutable`), so a re-bake bumps this constant and nothing
// else.
import { mediaUrl } from './media'

export const REVISIT_BASE = 'addl/revisit_v1/'

/** A file under the prefix (`c18_lakes.json`, `lakes/<id>.json`, a track's `src`). */
export function revisitUrl(rel: string): string {
  return mediaUrl(REVISIT_BASE + rel)
}
export const REVISIT_MANIFEST = 'c18_lakes.json'
/** The Additional Work card's thumbnail (MODIS | Landsat 7, one lake). */
export const REVISIT_CARD = 'card/revisit_card.jpg'

export type RevisitYear = '2010' | '2019'
export const REVISIT_YEARS: RevisitYear[] = ['2010', '2019']
/** A baked track; `side` = both of a year's tracks on one clock. */
export type RevisitSensor = 'modis' | 'hires'
export type RevisitMode = RevisitSensor | 'side'
export const REVISIT_MODES: RevisitMode[] = ['modis', 'hires', 'side']

export type C18State = 'present' | 'drained' | 'unchanged'

export interface C18ObsDay {
  date: string
  /** The paper's own counts for the day (its figure captions). */
  caption: { present?: number; drained?: number; unchanged?: number }
  note?: string
}
export interface C18Lake {
  id: string
  lat: number
  lon: number
  /** day → the lake's state on that day's map; a day is absent when the lake is not on it */
  states: Record<string, C18State>
  drained_days: string[]
  /** year → images per track (null = not built) */
  tracks: Record<string, { modis: number | null; hires: number | null } | undefined>
  thumbs: Record<string, boolean | undefined>
}
export interface C18Season {
  start: string
  end: string
  modis: string
  hires: string
}
export interface C18Manifest {
  paper: { cite: string; doi: string }
  counts: { lakes: number; drained_lakes: number; events_digitised: number; events_paper: number }
  obs_days: C18ObsDay[]
  cloud_days: string[]
  lake_bbox: { south: number; north: number; west: number; east: number }
  seasons: Record<string, C18Season | undefined>
  fps: number
  frame_count: number
  tile_km: number
  lakes: C18Lake[]
}

export interface RevisitTrack {
  /** relative to the prefix */
  src: string
  label: string
  /** per day: '1' = an image that day */
  has: string
  /** per day: '.' none · T/Q MODIS Terra/Aqua · L Landsat 7 · A ASTER · S Sentinel-2 */
  sensor: string
  /** km² of water within `water_radius_km` of the centre (null = no image / not measured) */
  water_km2?: (number | null)[]
  n_images: number
}
export interface RevisitSidecar {
  id: string
  fps: number
  frame_count: number
  tile_km: number
  tracks: Record<string, Partial<Record<RevisitSensor, RevisitTrack>> | undefined>
}

/** The frame's instrument, as the figure names it. */
export const SENSOR_NAME: Record<string, string> = {
  T: 'MODIS Terra',
  Q: 'MODIS Aqua',
  L: 'Landsat 7',
  A: 'ASTER',
  S: 'Sentinel-2',
}

const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
const DAY_MS = 86400e3
const utc = (iso: string): number => Date.parse(`${iso}T00:00:00Z`)

/** "6 JUN" (the figure's date style: day, month in caps). */
export function dayLabel(iso: string): string {
  const d = new Date(utc(iso))
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`
}
/** Day index → ISO date, counted from a season's start. */
export function isoOfDay(start: string, i: number): string {
  return new Date(utc(start) + i * DAY_MS).toISOString().slice(0, 10)
}
/** ISO date → day index from a season's start (may fall outside it). */
export function dayOfIso(start: string, iso: string): number {
  return Math.round((utc(iso) - utc(start)) / DAY_MS)
}
/** The first of each month inside a season: [day index, "JUN"]. */
export function monthTicks(start: string, days: number): { day: number; label: string }[] {
  const out: { day: number; label: string }[] = []
  const d0 = new Date(utc(start))
  for (let m = 0; m < 12; m++) {
    const t = Date.UTC(d0.getUTCFullYear(), d0.getUTCMonth() + m, 1)
    const day = Math.round((t - utc(start)) / DAY_MS)
    if (day >= days) break
    if (day >= 0) out.push({ day, label: MONTHS[new Date(t).getUTCMonth()] })
  }
  return out
}

/** A drainage day as the paper dates it: its last map is "8–10 June" —
 *  clouds hid the lakes on the 8th and 9th. */
export function claimLabel(iso: string, m: Pick<C18Manifest, 'cloud_days'>): string {
  const cloudy = [...m.cloud_days].sort()
  if (cloudy.length && isoOfDay(cloudy[cloudy.length - 1], 1) === iso) {
    const a = new Date(utc(cloudy[0]))
    const b = new Date(utc(iso))
    return `${a.getUTCDate()}–${b.getUTCDate()} ${MONTHS[b.getUTCMonth()]}`
  }
  return dayLabel(iso)
}

/** "Landsat 7 · ASTER · 15 m" → "Landsat 7 · ASTER" (the toggle's word). */
export function sensorWord(label: string): string {
  return label.replace(/\s*·\s*\d+(\.\d+)?\s*k?m$/i, '')
}
