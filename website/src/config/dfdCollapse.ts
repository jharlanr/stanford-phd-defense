// The APS DFD 2026 page's COLLAPSE beat (DfdCollapse.vue): the paper's
// Fig. 3 C–D re-drawn live from the Chapter 2 slab sweep. The 3-D Stokes
// centreline profiles are baked by cinematic/scene_addl/build_dfd_profiles.py
// to dfd/slab_profiles_v1.json (every run's depth-averaged Δσ̄_rr and τ̄_rr
// along y = 0, ±25 km at 250 m, kPa); the theory is lib/slabTheory in the
// browser; the maxima (Fig. 3D) come from the sweep manifest
// (config/ch2Slab loadSlabManifest). Flow is toward +x: tension upstream.
import { mediaUrl } from './media'

export const DFD_PROFILES_KEY = 'dfd/slab_profiles_v1.json'

export interface SlabProfileRun {
  R: number
  H: number
  alpha_deg: number
  gamma: number
  lambda: number
  stress_kpa: number
  decay_km: number
  /** Δσ̄_rr = 2 τ̄_xx + τ̄_yy along y = 0, kPa, on x_km. */
  srr_kpa: number[]
  /** τ̄_xx (= τ̄_rr on the flow line), kPa. */
  trr_kpa: number[]
}
export interface SlabProfiles {
  version: number
  x_km: number[]
  runs: Record<string, SlabProfileRun>
}

let profilesP: Promise<SlabProfiles | null> | null = null
/** The baked profiles (one fetch; a failure is retried on the next call). */
export function loadSlabProfiles(): Promise<SlabProfiles | null> {
  if (!profilesP) {
    profilesP = fetch(mediaUrl(DFD_PROFILES_KEY))
      .then((r) => (r.ok ? (r.json() as Promise<SlabProfiles>) : null))
      .catch(() => null)
      .then((p) => {
        if (!p) profilesP = null
        return p
      })
  }
  return profilesP
}

/** The paper's Fig. 3C cases, in its legend order — all three are in the
 *  sweep (λ = 0.56: R/H = 2.5, γ = 0.1). */
export const COLLAPSE_PAPER_RUNS = ['R2500_H1000_a10_G01', 'R1875_H750_a05_G01', 'R1250_H500_a01_G01']
export const COLLAPSE_DEFAULT_LAMBDA = 0.559

export interface LambdaGroup {
  lambda: number
  ids: string[]
}
/** The sweep's runs grouped by λ = k₀R, ascending; runs within 2 % of a
 *  group's λ join it (the one odd R 1850 m case joins the paper's 0.56).
 *  Inside a group: the paper's cases first, then by R, H, α descending —
 *  a fixed order, so a run keeps its colour whatever is selected. */
export function lambdaGroups(runs: Record<string, { lambda: number; R: number; H: number; alpha_deg: number }>): LambdaGroup[] {
  const ids = Object.keys(runs).sort((a, b) => runs[a].lambda - runs[b].lambda)
  const out: LambdaGroup[] = []
  for (const id of ids) {
    const lam = runs[id].lambda
    const g = out[out.length - 1]
    if (g && Math.abs(lam - g.lambda) / g.lambda < 0.02) g.ids.push(id)
    else out.push({ lambda: lam, ids: [id] })
  }
  for (const g of out) {
    g.ids.sort((a, b) => {
      const pa = COLLAPSE_PAPER_RUNS.indexOf(a)
      const pb = COLLAPSE_PAPER_RUNS.indexOf(b)
      if (pa >= 0 || pb >= 0) return (pa < 0 ? 9 : pa) - (pb < 0 ? 9 : pb)
      const ra = runs[a]
      const rb = runs[b]
      return rb.R - ra.R || rb.H - ra.H || rb.alpha_deg - ra.alpha_deg
    })
    // the group's λ: the paper's exact value when it holds that case
    const ref = g.ids.find((id) => COLLAPSE_PAPER_RUNS.includes(id))
    if (ref) g.lambda = runs[ref].lambda
  }
  return out
}

/** Series colours for the dark page, in fixed order (validated for
 *  colour-vision separation of neighbours; markers add a shape). */
export const COLLAPSE_COLOURS = ['#f4cf6a', '#7cc4ff', '#ff8a7a', '#7fe0b8', '#d4a8ff', '#ffb070', '#4fd1d9', '#c8d96a', '#ff8fd2']

export type MarkerShape = 'circle' | 'square' | 'tri' | 'diamond' | 'tri-down' | 'tri-left'
export const COLLAPSE_SHAPES: MarkerShape[] = ['circle', 'square', 'tri', 'diamond', 'tri-down', 'tri-left', 'circle', 'square', 'tri']
/** Fig. 3D's marker per thickness, the paper's order. */
export const H_SHAPES: Record<number, MarkerShape> = { 300: 'circle', 500: 'square', 750: 'tri', 1000: 'diamond', 2000: 'tri-down', 3000: 'tri-left' }

/** An SVG path for a marker of "radius" r centred at (cx, cy). */
export function markerPath(shape: MarkerShape, cx: number, cy: number, r: number): string {
  const f = (v: number) => v.toFixed(1)
  switch (shape) {
    case 'circle':
      return `M${f(cx - r)} ${f(cy)}a${f(r)} ${f(r)} 0 1 0 ${f(2 * r)} 0a${f(r)} ${f(r)} 0 1 0 ${f(-2 * r)} 0Z`
    case 'square': {
      const s = r * 0.9
      return `M${f(cx - s)} ${f(cy - s)}h${f(2 * s)}v${f(2 * s)}h${f(-2 * s)}Z`
    }
    case 'diamond':
      return `M${f(cx)} ${f(cy - r * 1.25)}L${f(cx + r * 1.25)} ${f(cy)}L${f(cx)} ${f(cy + r * 1.25)}L${f(cx - r * 1.25)} ${f(cy)}Z`
    case 'tri':
      return `M${f(cx)} ${f(cy - r * 1.2)}L${f(cx + r * 1.1)} ${f(cy + r * 0.8)}L${f(cx - r * 1.1)} ${f(cy + r * 0.8)}Z`
    case 'tri-down':
      return `M${f(cx)} ${f(cy + r * 1.2)}L${f(cx + r * 1.1)} ${f(cy - r * 0.8)}L${f(cx - r * 1.1)} ${f(cy - r * 0.8)}Z`
    case 'tri-left':
      return `M${f(cx - r * 1.2)} ${f(cy)}L${f(cx + r * 0.8)} ${f(cy - r * 1.1)}L${f(cx + r * 0.8)} ${f(cy + r * 1.1)}Z`
  }
}

/** The sequential ramp for Fig. 3D's αR (one hue, dim amber → pale gold):
 *  t in [0, 1]. */
export function goldRamp(t: number): string {
  const u = Math.min(1, Math.max(0, t))
  const a = [154, 96, 22] // #9a6016
  const b = [255, 240, 190] // #fff0be
  const c = a.map((v, i) => Math.round(v + (b[i] - v) * u))
  return `rgb(${c[0]},${c[1]},${c[2]})`
}

/** "R 2.5 km · H 1 km · α 1°" */
export function fmtRunParams(r: { R: number; H: number; alpha_deg: number }): string {
  const km = (m: number) => String(Math.round(m / 10) / 100)
  return `R ${km(r.R)} km · H ${km(r.H)} km · α ${r.alpha_deg}°`
}

/** The smallest of 1 · 1.2 · 1.5 · 2 · 2.5 · 3 · 4 · 5 · 6 · 8 · 10 × 10ᵏ ≥ v. */
export function niceCeil(v: number): number {
  if (!(v > 0)) return 1
  const e = Math.pow(10, Math.floor(Math.log10(v)))
  for (const m of [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) if (m * e >= v * (1 - 1e-9)) return m * e
  return 10 * e
}
/** A tick step of 1 · 2 · 2.5 · 3 · 5 · 10 × 10ᵏ ≥ v. */
export function niceStep(v: number): number {
  if (!(v > 0)) return 1
  const e = Math.pow(10, Math.floor(Math.log10(v)))
  const m = v / e
  return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 3 ? 3 : m <= 5 ? 5 : 10) * e
}
/** Symmetric ticks −lim … lim at a nice step (about 5–7 of them). */
export function symTicks(lim: number): number[] {
  const step = niceStep(lim / 3)
  const out: number[] = []
  for (let v = -Math.floor(lim / step + 1e-9) * step; v <= lim + 1e-9; v += step) out.push(Math.round(v * 1000) / 1000)
  return out
}
