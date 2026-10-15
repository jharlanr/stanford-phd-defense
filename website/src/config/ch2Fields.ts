// The Chapter 2 FIELD VIEWER (the director's brief: for any lake, pick
// viscous or elastic and see every field painted on the surface — all of
// the fields in all of the SI figures). It lives on the deeper-dive page,
// /additional-work/deeper/
// chapter2#fields (Ch2FieldViewer.vue); the talk's block beat links there.
//
// Rasters, per-lake overlays and the LaTeX names are baked by
// cinematic/scene_addl/build_deeper_ch02.py → R2 addl/deeper/ch02/:
//   fields_v3/<num>_<v|e>_<key>.webp   the field, 1600 px (+ _t.webp thumb)
//   fields_v3/lake_<num>.json          frame, ticks, lake outlines, ranges
//   tex/<key>.svg                      the field's name, latex + dvisvgm
// (fields_v2 — the director asked for the deeper dive's colour bar to be
// always −1000 to 1000 kPa for viscous and elastic fields alike: every stress
// raster on one seismic ±1000 kPa scale; fields/ was the SI's ±400 kPa for
// the viscous rows. fields_v3 — the director noticed the elastic blister
// plots lacked the SI's hash marks: the elastic POST σ cells are baked from
// the superposed tensor with the SI's hashes and contour. R2 objects are
// immutable, hence a new prefix each time.)
//
// The grid mirrors the SI overview figures (S7–S13 viscous, S14–S20
// elastic): a data row (model inputs), then one row per quantity with the
// three columns no patch / patch / difference (no blister / blister /
// difference). The SI's own rows come first; σn, σrθ, σθθ (and σrr for the
// elastic model) follow — the same netCDFs, the same recipe.

import { mediaUrl } from './media'

export type Ch2Model = 'elastic' | 'viscous'
/** The two-stop's order (the director's brief: ELASTIC | VISCOUS). */
export const CH2_MODELS: Ch2Model[] = ['elastic', 'viscous']

/** The seven center lakes: Dunmire number (the paper's) and sim id. */
export const CH2_FIELD_LAKES: { num: number; sim: string }[] = [
  { num: 1910, sim: 'cw387' },
  { num: 1951, sim: 'cw428' },
  { num: 2394, sim: 'cw871' },
  { num: 2411, sim: 'cw888' },
  { num: 2416, sim: 'cw893' },
  { num: 2511, sim: 'cw988' },
  { num: 2520, sim: 'cw997' },
]
export const CH2_DEFAULT_LAKE = 2511 // PNAS Fig. 1's lake, Ch.2's default
export const CH2_DEFAULT_MODEL: Ch2Model = 'viscous'
export const CH2_DEFAULT_FIELD = 'st1_d'

export type Ch2Row = 'data' | 'u' | 'st1' | 'st2' | 'srr' | 'sn' | 'srt' | 'stt'

export interface Ch2RowDef {
  id: Ch2Row
  /** Row label (trusted static HTML: italics, sub/superscripts). */
  label: string
  /** Colour-bar title prefix for this quantity (HTML). */
  quantity: string
}

const ROWS: Record<Ch2Row, Ch2RowDef> = {
  data: { id: 'data', label: '', quantity: '' },
  u: { id: 'u', label: '|<b>u</b>|', quantity: 'speed' },
  st1: { id: 'st1', label: '<i>σ</i><sub>t1</sub>', quantity: '<i>σ</i><sub>t1</sub>' },
  st2: { id: 'st2', label: '<i>σ</i><sub>t2</sub>', quantity: '<i>σ</i><sub>t2</sub>' },
  srr: { id: 'srr', label: '<i>σ</i><sub><i>rr</i></sub>', quantity: '<i>σ</i><sub><i>rr</i></sub>' },
  sn: { id: 'sn', label: '<i>σ</i><sub><i>n</i></sub>', quantity: '<i>σ</i><sub><i>n</i></sub>' },
  srt: { id: 'srt', label: '<i>σ</i><sub><i>rθ</i></sub>', quantity: '<i>σ</i><sub><i>rθ</i></sub>' },
  stt: { id: 'stt', label: '<i>σ</i><sub><i>θθ</i></sub>', quantity: '<i>σ</i><sub><i>θθ</i></sub>' },
}

/** The rows each model has, top to bottom. */
export const CH2_ROWS: Record<Ch2Model, Ch2RowDef[]> = {
  viscous: (['data', 'u', 'st1', 'st2', 'srr', 'sn', 'srt', 'stt'] as Ch2Row[]).map((r) => ROWS[r]),
  elastic: (['data', 'st1', 'st2', 'srr', 'sn', 'srt', 'stt'] as Ch2Row[]).map((r) => ROWS[r]),
}

/** Column heads: the SI's words. */
export const CH2_COLUMNS: Record<Ch2Model, [string, string, string]> = {
  viscous: ['No patch', 'Patch', 'Difference'],
  elastic: ['No blister', 'Blister', 'Difference'],
}
export const CH2_DATA_COLUMNS: [string, string, string] = ['Observed speed', 'Surface', 'Bed']
const DATA_KEYS = ['obs', 'zs', 'zb'] as const
const CASE_KEYS = ['pre', 'post', 'd'] as const

/** The baked field key of a grid cell. */
export function ch2FieldKey(row: Ch2Row, col: number): string {
  return row === 'data' ? DATA_KEYS[col] : `${row}_${CASE_KEYS[col]}`
}
/** Grid cell of a field key (inverse of ch2FieldKey). */
export function ch2FieldCell(key: string): { row: Ch2Row; col: number } {
  const d = (DATA_KEYS as readonly string[]).indexOf(key)
  if (d >= 0) return { row: 'data', col: d }
  const [row, c] = key.split('_')
  return { row: row as Ch2Row, col: Math.max(0, (CASE_KEYS as readonly string[]).indexOf(c)) }
}
/** Every field of a model, in grid (reading) order. */
export function ch2FieldKeys(model: Ch2Model): string[] {
  return CH2_ROWS[model].flatMap((r) => [0, 1, 2].map((c) => ch2FieldKey(r.id, c)))
}
/** The same cell under the other model, or the nearest one it has. */
export function ch2MapField(key: string, model: Ch2Model): string {
  const { row, col } = ch2FieldCell(key)
  if (CH2_ROWS[model].some((r) => r.id === row)) return key
  return ch2FieldKey('st1', col)
}

/** Colour-bar title (HTML) for a field. */
export function ch2CbarLabel(key: string, units: string): string {
  const { row } = ch2FieldCell(key)
  if (row === 'data') return key === 'obs' ? `speed [${units}]` : `elevation [${units}]`
  if (row === 'u') return `speed [${units}]`
  return `${ROWS[row].quantity} [${units}]`
}

/** The header's words for a field: the SI panel title. */
export function ch2CaseLabel(key: string, model: Ch2Model): string {
  const { row, col } = ch2FieldCell(key)
  if (row === 'data') return ['Observed speed', 'Surface elevation', 'Bed elevation'][col]
  return CH2_COLUMNS[model][col]
}

// ── assets ─────────────────────────────────────────────────────────────────
const K = 'addl/deeper/ch02/'
/** The field rasters' prefix (a re-bake = a new name; see the file head). */
const FIELDS = 'fields_v3'
export function ch2FieldSrc(num: number, model: Ch2Model, key: string, thumb = false): string {
  return mediaUrl(`${K}${FIELDS}/${num}_${model[0]}_${key}${thumb ? '_t' : ''}.webp`)
}
export function ch2LakeJson(num: number): string {
  return mediaUrl(`${K}${FIELDS}/lake_${num}.json`)
}
export function ch2TexSrc(key: string): string {
  return mediaUrl(`${K}tex/${key}.svg`)
}
/** The TeX names' shared box (bp, the bake's log): every name is set on
 *  one baseline in a box this tall, so a fixed display height aligns them. */
export const CH2_TEX_BOX = { height: 13.352, baseline: 9.676 }

// ── the per-lake JSON (lake_<num>.json) ────────────────────────────────────
export interface Ch2FieldInfo {
  cmap: 'magma' | 'terrain' | 'seismic'
  vmin: number
  vmax: number
  units: string
  mean: number
  /** 0.3 / 50 / 99.7th percentiles inside the tile. */
  p: [number, number, number]
  ticks: number[]
}
export interface Ch2MapLake {
  num: number
  cls: 'black' | 'gray' | 'cyan' | 'dashgray' | 'dashcyan' | 'magenta'
  center: boolean
  /** Rings in panel km from the top-left (y down). */
  rings: [number, number][][]
  /** The number: x, baseline y (panel km) and its text anchor. */
  label: [number, number, 'middle' | 'start' | 'end']
}
export interface Ch2LakeMeta {
  num: number
  sim: string
  size_km: number
  /** EPSG:3413 km: [Emin, Emax, Nmin, Nmax]. */
  extent_km: [number, number, number, number]
  /** The rotated 15 km tile's corners, panel km. */
  tile: [number, number][]
  xticks: number[]
  yticks: number[]
  lakes: Ch2MapLake[]
  cb: number
  pw: number
  si: Record<Ch2Model, number>
  thesis: Record<Ch2Model, number>
  fields: Record<Ch2Model, Record<string, Ch2FieldInfo>>
}

/** Drainage classes, the paper's Fig. 1 legend (georef.LAKE_STYLE). */
export const CH2_CLASS_STYLE: Record<Ch2MapLake['cls'], { color: string; dash: boolean; halo: string }> = {
  cyan: { color: '#00ffff', dash: false, halo: '#000' },
  gray: { color: '#4d4d4d', dash: false, halo: '#fff' },
  black: { color: '#000000', dash: false, halo: '#fff' },
  magenta: { color: '#ff00ff', dash: false, halo: '#000' },
  dashcyan: { color: '#00ffff', dash: true, halo: '#000' },
  dashgray: { color: '#4d4d4d', dash: true, halo: '#fff' },
}
export const CH2_CLASS_LEGEND: { cls: Ch2MapLake['cls']; label: string }[] = [
  { cls: 'cyan', label: 'englacial' },
  { cls: 'gray', label: 'lateral' },
  { cls: 'black', label: 'none' },
  { cls: 'magenta', label: 'same-day englacial' },
  { cls: 'dashcyan', label: 'englacial, much later' },
  { cls: 'dashgray', label: 'lateral, may be englacial' },
]

// ── The PHYSICAL elastic post-drainage state ───────────────────────────────
// The director's physics: the elastic solves' absolute fields have no
// physical meaning (an elastic body loaded by gravity from an unstressed
// state) — only their difference Δσ^E does. So in the ELASTIC grid:
//   σ_t1 / σ_t2 · pre    the VISCOUS no-patch field (the one pre-drainage
//                        state both models share), with its own scale
//   σ_t1 / σ_t2 / σ_n · post   the superposed state σ^V_pre + Δσ^E — baked
//                        by build_deeper_ch02.py (fields_v3) from the summed
//                        Cauchy tensors, principals after, with the SI's
//                        hashes and +100 kPa contour (before fields_v3 the
//                        page re-projected the talk's drape in the browser,
//                        hence no hashes — the director asked why)
// Every other cell is as baked.
const SHARED_PRE = new Set(['st1_pre', 'st2_pre'])
const SUPERPOSED = new Set(['st1_post', 'st2_post', 'sn_post'])
/** The model whose raster + colour bar a cell shows (the elastic σ pre
 *  cells borrow the viscous no-patch field). */
export function ch2CellModel(model: Ch2Model, key: string): Ch2Model {
  return model === 'elastic' && SHARED_PRE.has(key) ? 'viscous' : model
}
/** True for the cells painted with the superposed σ^V_pre + Δσ^E. */
export function ch2IsSuperposed(model: Ch2Model, key: string): boolean {
  return model === 'elastic' && SUPERPOSED.has(key)
}
export function ch2CellLabel(key: string, model: Ch2Model): string {
  if (model === 'elastic' && SHARED_PRE.has(key)) return 'No patch (viscous)'
  if (ch2IsSuperposed(model, key)) return 'Viscous pre + elastic Δ'
  return ch2CaseLabel(key, model)
}

