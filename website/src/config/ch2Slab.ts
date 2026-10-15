// Chapter 2's THEORY segment — the idealized periodic
// slab of the PNAS SI's validation: Elmer/Ice (3D Stokes, Newtonian, linear
// Weertman sliding, a free-slip patch of radius R on a 100 km periodic
// domain) against the shallow-stream theory, swept over R · H · α · γ.
// The pipeline (cinematic/scene_ch02/build_slab_validation.py) writes R2
// ch02/slab_v1/manifest.json + per-run rasters, already coloured (blue −,
// white 0, red +, ONE symmetric vlim per field and run, shared by the
// surface / depth-average / theory / difference of that run). The talk
// beats (Ch2Slab.vue) and the deeper dive's viewer (Ch2SlabFieldViewer.vue)
// both read it here; the visitor's run + field are one shared state, so the
// deeper dive opens on whatever the talk was showing.
import { reactive } from 'vue'
import { mediaUrl } from './media'

export const CH2_SLAB_PREFIX = 'ch02/slab_v1/'
/** The TALK's assets (contract v2): 32 runs (R 2.5 |
 *  5 km, α 0.5 | 1°), three fields, ONE fixed ±300 kPa colour scale, and the
 *  CUMULATIVE depth average from the surface down to each mesh level
 *  (`cum`), which the depth-average beat paints as the block collapses.
 *  The deeper dive's viewer keeps v1 (all 75 runs, all 11 fields). */
export const CH2_SLAB_V2_PREFIX = 'ch02/slab_v2/'
/** The R2 prefix of the slab's LaTeX (build_slab_eqs.py). */
export const CH2_SLAB_EQ_PREFIX = 'ch02/slab_eq_v1/'

export type SlabField = string // 'st1' | 'trr' | 'txx' | … (manifest.fields_all)
export type SlabKind = 'surf' | 'da' | 'theory' | 'diff' | 'diff_zoom'

export interface SlabRun {
  R: number
  H: number
  alpha_deg: number
  gamma: number
  /** false on the three odd runs outside the full-factorial sweep (kept
   *  off the sliders). */
  sweep?: boolean
  /** [x0, x1, y0, y1] in km, the patch centred at (0, 0). */
  domain_km: [number, number, number, number]
  patch_km: number
  scales?: { stress_kpa: number; decay_km: number }
  vlim_kpa: Record<SlabField, number>
  max_kpa: { sim_da: Record<SlabField, number>; theory: Record<SlabField, number>; diff_abs: Record<SlabField, number> }
  surf: Record<SlabField, string>
  da: Record<SlabField, string>
  theory: Record<SlabField, string>
  diff: Record<SlabField, string>
  diff_zoom?: Record<SlabField, string>
}

export interface SlabManifest {
  version: number
  hero: string
  params: { R: number[]; H: number[]; alpha_deg: number[]; gamma: number[] }
  fields: SlabField[]
  fields_all: SlabField[]
  runs: Record<string, SlabRun>
}

/** A v2 (talk) run: `cum[field][k]` = the depth average from the surface
 *  down to mesh level k (k = 0 the surface, K the full depth average) at
 *  depth z_k = depth_frac[k] · H. Paths are relative to the v2 prefix. */
export interface SlabTalkRun {
  R: number
  H: number
  alpha_deg: number
  gamma: number
  sweep?: boolean
  domain_km: [number, number, number, number]
  patch_km: number
  scales?: { stress_kpa: number; decay_km: number }
  K: number
  depth_frac: number[]
  cum: Record<SlabField, string[]>
  theory: Record<SlabField, string>
  diff: Record<SlabField, string>
}
export interface SlabTalkManifest {
  version: number
  hero: string
  params: { R: number[]; H: number[]; alpha_deg: number[]; gamma: number[] }
  fields: SlabField[]
  vlim_kpa: number
  runs: Record<string, SlabTalkRun>
}
/** What the slider helpers need of either manifest. */
interface SlabSweep {
  params: { R: number[]; H: number[]; alpha_deg: number[]; gamma: number[] }
  runs: Record<string, { R: number; H: number; alpha_deg: number; gamma: number; sweep?: boolean }>
}

let manifestP: Promise<SlabManifest | null> | null = null
/** The manifest (one fetch; a failure is retried on the next call). */
export function loadSlabManifest(): Promise<SlabManifest | null> {
  if (!manifestP) {
    manifestP = fetch(mediaUrl(`${CH2_SLAB_PREFIX}manifest.json`))
      .then((r) => (r.ok ? (r.json() as Promise<SlabManifest>) : null))
      .catch(() => null)
      .then((m) => {
        if (!m) manifestP = null
        return m
      })
  }
  return manifestP
}

let talkManifestP: Promise<SlabTalkManifest | null> | null = null
/** The talk's v2 manifest (one fetch; a failure is retried on the next call). */
export function loadSlabTalkManifest(): Promise<SlabTalkManifest | null> {
  if (!talkManifestP) {
    talkManifestP = fetch(mediaUrl(`${CH2_SLAB_V2_PREFIX}manifest.json`))
      .then((r) => (r.ok ? (r.json() as Promise<SlabTalkManifest>) : null))
      .catch(() => null)
      .then((m) => {
        if (!m) talkManifestP = null
        return m
      })
  }
  return talkManifestP
}

/** The talk's three fields, in toggle order (decided with the director: σ_t1 the
 *  default; τ_rr the published comparison, PNAS SI Fig. S1 / thesis Fig.
 *  2.19; τ_xx Chapter 1's field). */
export const SLAB_TALK_FIELDS: SlabField[] = ['st1', 'trr', 'txx']
export const SLAB_DEFAULT_FIELD: SlabField = 'st1'
/** The deeper dive's v1 hero (the thesis figure's): R 5 km, H 3 km, α 0.1°, γ 0.1. */
export const SLAB_HERO = 'R5000_H3000_a01_G01'
/** The TALK's default run (the director's sweep: α 0.5 | 1° only, so v1's
 *  hero is off the sliders; he asked for a 3× vertical exaggeration on the
 *  theory domains to start — the block already draws at VEXAG 3, later
 *  5 — so the default is the THICK case instead of PNAS Fig. 2's
 *  H = 1 km): R 2.5 km, H 3 km, α 1°, γ 0.1 — max |σ_t1| 108 kPa at the
 *  surface, 235 depth-averaged, 272 in theory, all inside the ±300 kPa bar.
 *  It wins over the v2 manifest's own `hero` (Ch2Slab snapRun). It exists
 *  in v1 too, so the deeper dive opens on it. */
export const SLAB_TALK_HERO = 'R2500_H1000_a05_G01' // the director's default theory view: H = 1000 m, α = 0.5°

/** A field's name as HTML (pills, the viewer's picker; the colour bar and
 *  the viewer's big panel use the LaTeX SVGs `f_<id>` / `fb_<id>`). */
export const SLAB_FIELD_HTML: Record<string, string> = {
  st1: '<i>σ</i><sub>t1</sub>',
  st2: '<i>σ</i><sub>t2</sub>',
  trr: '<i>τ</i><sub><i>rr</i></sub>',
  trt: '<i>τ</i><sub><i>rθ</i></sub>',
  ttt: '<i>τ</i><sub><i>θθ</i></sub>',
  txx: '<i>τ</i><sub><i>xx</i></sub>',
  tyy: '<i>τ</i><sub><i>yy</i></sub>',
  txy: '<i>τ</i><sub><i>xy</i></sub>',
  srr: 'Δ<i>σ</i><sub><i>rr</i></sub>',
  stt: 'Δ<i>σ</i><sub><i>θθ</i></sub>',
  srt: 'Δ<i>σ</i><sub><i>rθ</i></sub>',
}

export function slabEqUrl(name: string): string {
  return mediaUrl(`${CH2_SLAB_EQ_PREFIX}${name}.svg`)
}

/** A raster's URL. `cors` = a WebGL texture's load (its own cache entry —
 *  config/media.ts corsUrl); plain for an <img>. */
export function slabRasterUrl(path: string, cors: boolean, prefix: string = CH2_SLAB_PREFIX): string {
  const u = mediaUrl(`${prefix}${path}`)
  return cors ? u + (u.includes('?') ? '&' : '?') + 'cors=1' : u
}

// ── the visitor's choice (shared by the beats and the deeper dive) ──
export type SlabParam = 'H' | 'alpha_deg' | 'gamma' | 'R'
/** The sliders, in the director's order (thicknesses, slopes, gammas, then R). */
export const SLAB_PARAMS: { key: SlabParam; sym: string; unit: string; fmt: (v: number) => string }[] = [
  { key: 'H', sym: 'H', unit: 'km', fmt: (v) => fmtNum(v / 1000) },
  { key: 'alpha_deg', sym: 'α', unit: '°', fmt: (v) => fmtNum(v) },
  { key: 'gamma', sym: 'γ', unit: '', fmt: (v) => fmtNum(v) },
  { key: 'R', sym: 'R', unit: 'km', fmt: (v) => fmtNum(v / 1000) },
]
function fmtNum(v: number): string {
  return String(Math.round(v * 100) / 100)
}

export const slabState = reactive({
  run: SLAB_TALK_HERO as string,
  field: SLAB_DEFAULT_FIELD as SlabField,
})

/** The run with these parameters — or, when the sweep has no such run, the
 *  nearest one that keeps `keep` (the slider just moved) at its value. */
export function findSlabRun(
  m: SlabSweep,
  want: Record<SlabParam, number>,
  keep: SlabParam | null = null,
): string | null {
  let best: string | null = null
  let bestD = Infinity
  const P = m.params
  const norm: Record<SlabParam, number[]> = { H: P.H, alpha_deg: P.alpha_deg, gamma: P.gamma, R: P.R }
  const idx = (k: SlabParam, v: number) => {
    const a = norm[k]
    let j = 0
    for (let i = 0; i < a.length; i++) if (Math.abs(a[i] - v) < Math.abs(a[j] - v)) j = i
    return j
  }
  for (const [id, r] of Object.entries(m.runs)) {
    if (r.sweep === false) continue
    let d = 0
    for (const k of ['H', 'alpha_deg', 'gamma', 'R'] as SlabParam[]) {
      const di = Math.abs(idx(k, r[k]) - idx(k, want[k])) + (Math.abs(r[k] - want[k]) > 1e-9 ? 0.01 : 0)
      d += k === keep ? di * 100 : di
    }
    if (d < bestD) {
      bestD = d
      best = id
    }
  }
  return best
}

/** The runs one slider stop away from `id` (the crossfade's warm set). */
export function slabNeighbours(m: SlabSweep, id: string): string[] {
  const r = m.runs[id]
  if (!r) return []
  const out = new Set<string>()
  const P: Record<SlabParam, number[]> = { H: m.params.H, alpha_deg: m.params.alpha_deg, gamma: m.params.gamma, R: m.params.R }
  for (const k of ['H', 'alpha_deg', 'gamma', 'R'] as SlabParam[]) {
    const a = P[k]
    const i = a.findIndex((v) => Math.abs(v - r[k]) < 1e-9)
    for (const j of [i - 1, i + 1]) {
      if (i < 0 || j < 0 || j >= a.length) continue
      const want = { H: r.H, alpha_deg: r.alpha_deg, gamma: r.gamma, R: r.R }
      want[k] = a[j]
      const n = findSlabRun(m, want, k)
      if (n && n !== id && Math.abs(m.runs[n][k] - a[j]) < 1e-9) out.add(n)
    }
  }
  return [...out]
}

/** A run id's parameters ("R2500_H1000_a10_G01" → R 2500, H 1000, α 1.0°,
 *  γ 0.1) — the talk snaps a v1-only run (picked in the deeper dive) to the
 *  nearest v2 one. */
export function parseSlabRunId(id: string): Record<SlabParam, number> | null {
  const m = /^R(\d+)_H(\d+)_a(\d+)_G(\d+)$/.exec(id)
  if (!m) return null
  // two digits = tenths ("01" 0.1, "05" 0.5, "10" 1.0); one digit = units ("1")
  const dec = (s: string) => (s.length > 1 ? Number(s) / 10 : Number(s))
  return { R: Number(m[1]), H: Number(m[2]), alpha_deg: dec(m[3]), gamma: dec(m[4]) }
}

/** "33 kPa" / "4.2 kPa" / "0.31 kPa" — a data callout's number. */
export function fmtKpa(v: number): string {
  const a = Math.abs(v)
  return `${a >= 10 ? Math.round(v) : a >= 1 ? v.toFixed(1) : v.toFixed(2)} kPa`
}
