// Depth-averaged shallow-stream (SSA) stress perturbation of a Newtonian ice
// slab sliding over a circular free-slip patch — the closed-form theory of
// Lai, Rines, Coffey et al. (2026, PNAS), SI section "Solving for the
// coefficients" onward. A TypeScript port of the notebook code behind the
// published figures (defense/cinematic/scene_ch02/slab_theory.py in the
// dissertation repo, itself a faithful port of the notebook's "cell 32"),
// validated numerically against it at 240 points and four parameter sets
// (scratchpad theory/test_theory.mjs). Pure functions; imports only ./bessel.
//
// Set-up (SI): a slab of thickness H and Newtonian viscosity eta on a plane
// of slope alpha slides with a linear Weertman law tau_b = c0 u everywhere
// except on a free-slip disc of radius R. c0 is parameterised by gamma with
// c0 = gamma / (A H), A = 1 / (2 eta). The solution has two scales,
//   [tau] = rho g alpha R / 2       stress   (SI, text after eq:tau_components)
//   1 / k0 = sqrt(4 eta H / c0)     decay length
// and depends on the one dimensionless group lambda = k0 R; Q = rho g alpha R
// / (4 eta) is the SI's strain-rate scale, so [tau] = 2 eta Q.
//   fDelta, fZeta ........ SI eq:delta_0, eq:zeta_0 (delta_0 = −Q f_delta,
//                          zeta_0 = Q f_zeta; note f_zeta ≡ 4 (1 − f_delta))
//   tauHat ............... SI eq:tau_components_rescaled, the boxed
//                          dimensionless tau~_ij(r~, lambda) (Eq. 34 of the
//                          compiled SI), r~ = k0 r
//   cauchyPerturbation ... SI text before eq:cauchy_stresses:
//                          Δσ_11 = 2 τ_11 + τ_22, Δσ_22 = 2 τ_22 + τ_11, Δσ_12 = τ_12
//                          (−rho g H / 2 cancels), valid in any in-plane basis
//   principals ........... SI's Δσ_1,2 (the 2-D eigenvalues)
// Caution: the SI's PRINTED inner (r < R) branch of Δσ~_rr in eq:s_rr_rescaled
// (Eq. 35) is inconsistent with the deviatoric components it is built from:
// 2 τ~_rr + τ~_θθ gives −(1 + 3/4 f_delta) r~/lambda, not −(1 − 7/4 f_delta).
// Like slab_theory.py, this file always forms the Cauchy perturbation from
// the deviatoric components and never uses the printed inner formula.
//
// Coordinates: x, y in metres from the patch centre, theta = atan2(y, x), no
// rotation (slab_theory.py's ROTATION_ANGLE = 0, the published unrotated
// figure). Upstream is NEGATIVE x: evaluated numerically with slab_theory.py
// and this port, tau_rr(x = −1.5 R, y = 0) > 0 (along-flow tension, the ice
// being pulled toward the patch) and tau_rr(x = +1.5 R, y = 0) < 0
// (compression) for every parameter set, so the slab flows toward +x. Inside
// the patch tau_xx ramps linearly from +[tau](1 − f_delta/4) at x = −R to
// the opposite at x = +R.

import { besselK0K1, besselK1pp, besselK2 } from './bessel'

export const RHO = 917 // kg m^-3
export const G = 9.81 // m s^-2
export const ETA = 1e14 // Pa s
const A = 1 / (2 * ETA) // slab_theory.py's A; c0 = gamma / (A H)

/** The run parameters: thickness (m), surface slope (degrees), gamma (–), patch radius (m). */
export interface SlabParams {
  H: number
  alphaDeg: number
  gamma: number
  R: number
}

/** slab_theory.py's solution_params plus the named scales. */
export interface SlabScales {
  /** Linear sliding coefficient gamma / (A H), Pa s m^-1. */
  c0: number
  /** sqrt(c0 / (4 eta H)), m^-1 — inverse decay length. */
  k0: number
  /** k0 R, the dimensionless patch radius. */
  lambda: number
  /** rho g alpha R / (4 eta), s^-1 — the SI's strain-rate scale. */
  Q: number
  /** rho g alpha R / 2, Pa — the stress scale [tau] = 2 eta Q. */
  stressPa: number
  /** 1 / k0 = sqrt(4 eta H / c0), m. */
  decayM: number
  fDelta: number
  fZeta: number
  /** −Q fDelta, s^-1. */
  delta0: number
  /** Q fZeta, s^-1. */
  zeta0: number
}

/** The two K0/K1 ratios sigma(lambda), sigma(2 lambda) and the common denominator of SI eq:delta_0 / eq:zeta_0. */
function coefficientParts(lambda: number): { s1: number; s2: number; denom: number } {
  const [k0a, k1a] = besselK0K1(lambda)
  const [k0b, k1b] = besselK0K1(2 * lambda)
  const s1 = k0a / k1a
  const s2 = k0b / k1b
  return { s1, s2, denom: 4 + lambda * s1 + 2 * lambda * s2 + 1.25 * lambda * lambda }
}

/** f_delta(lambda) of SI eq:delta_0, so that delta_0 = −Q f_delta. */
export function fDelta(lambda: number): number {
  const { s2, denom } = coefficientParts(lambda)
  return (2 + 2 * lambda * s2 + lambda * lambda) / denom
}

/** f_zeta(lambda) of SI eq:zeta_0, so that zeta_0 = Q f_zeta. */
export function fZeta(lambda: number): number {
  const { s1, denom } = coefficientParts(lambda)
  return (4 * (2 + lambda * s1 + 0.25 * lambda * lambda)) / denom
}

/** All derived scales for a parameter set (gamma must be > 0; alphaDeg in degrees). */
export function slabScales(p: SlabParams): SlabScales {
  const alpha = (p.alphaDeg * Math.PI) / 180
  const c0 = p.gamma / (A * p.H)
  const k0 = Math.sqrt(c0 / (4 * ETA * p.H))
  const lambda = k0 * p.R
  const Q = (RHO * G * alpha * p.R) / (4 * ETA)
  const fd = fDelta(lambda)
  const fz = fZeta(lambda)
  return {
    c0,
    k0,
    lambda,
    Q,
    stressPa: (RHO * G * alpha * p.R) / 2,
    decayM: 1 / k0,
    fDelta: fd,
    fZeta: fz,
    delta0: -Q * fd,
    zeta0: Q * fz,
  }
}

/** Dimensionless radial amplitudes, with the branch chosen by the caller. */
function tauHatBranch(rt: number, inner: boolean, s: SlabScales): { rr: number; rt: number; tt: number } {
  const fd = s.fDelta
  const fz = s.fZeta
  if (inner) {
    // r < R: linear in r~/lambda = r/R (SI eq:tau_components_rescaled, first rows)
    const q = rt / s.lambda
    return { rr: -(1 - 0.25 * fd) * q, rt: (1 - 0.75 * fd) * q, tt: (1 - 1.25 * fd) * q }
  }
  // r >= R: K-Bessel branch. Both K1(lambda) and K1(2 lambda) are O(1); the
  // K(r~) factors underflow to 0 for huge r~, which is the correct limit.
  const [, k1lam] = besselK0K1(s.lambda)
  const [, k1lam2] = besselK0K1(2 * s.lambda)
  const cd = fd / k1lam
  const cz = fz / k1lam2
  const [, k1r2] = besselK0K1(2 * rt)
  const k2r = besselK2(rt) / rt
  const k2r2 = besselK2(2 * rt) / (2 * rt)
  return {
    rr: -cd * besselK1pp(rt) + cz * k2r2,
    rt: -cd * k2r + cz * (besselK1pp(2 * rt) - 0.5 * k1r2),
    tt: cd * k2r - cz * k2r2,
  }
}

/**
 * The dimensionless radial amplitude functions of SI eq:tau_components_rescaled
 * (Eq. 34), in units of rho g alpha R / 2, as functions of r~ = k0 r:
 * tau~_rr = rr cos(theta), tau~_rtheta = rt sin(theta), tau~_thetatheta = tt cos(theta).
 * Inner (linear) branch for r~ < lambda, Bessel branch for r~ >= lambda.
 */
export function tauHat(rt: number, s: SlabScales): { rr: number; rt: number; tt: number } {
  return tauHatBranch(rt, rt < s.lambda, s)
}

/**
 * Polar deviatoric components (Pa) at (x, y) metres from the patch centre,
 * theta = atan2(y, x), as slab_theory.theory_polar (branch test r < R, as the
 * Python). Upstream / tension is x < 0 — see the header.
 */
export function tauPolarAt(x: number, y: number, p: SlabParams, s: SlabScales): { trr: number; trt: number; ttt: number } {
  const r = Math.hypot(x, y)
  const theta = Math.atan2(y, x)
  const h = tauHatBranch(s.k0 * r, r < p.R, s)
  const c = Math.cos(theta)
  const sn = Math.sin(theta)
  return { trr: s.stressPa * h.rr * c, trt: s.stressPa * h.rt * sn, ttt: s.stressPa * h.tt * c }
}

/** Cartesian deviatoric components (Pa) via slab_theory.polar_to_cart. */
export function tauCartesianAt(x: number, y: number, p: SlabParams, s: SlabScales): { txx: number; tyy: number; txy: number } {
  const { trr, trt, ttt } = tauPolarAt(x, y, p, s)
  const theta = Math.atan2(y, x)
  const c = Math.cos(theta)
  const sn = Math.sin(theta)
  const s2 = Math.sin(2 * theta)
  return {
    txx: trr * c * c + ttt * sn * sn - trt * s2,
    tyy: trr * sn * sn + ttt * c * c + trt * s2,
    txy: (trr - ttt) * sn * c + trt * Math.cos(2 * theta),
  }
}

/** Δσ_11 = 2 τ_11 + τ_22, Δσ_22 = 2 τ_22 + τ_11, Δσ_12 = τ_12 (any in-plane orthonormal basis). */
export function cauchyPerturbation(t11: number, t22: number, t12: number): { s11: number; s22: number; s12: number } {
  return { s11: 2 * t11 + t22, s22: 2 * t22 + t11, s12: t12 }
}

/** In-plane principal values of a symmetric 2×2 tensor, t1 >= t2. */
export function principals(s11: number, s22: number, s12: number): { t1: number; t2: number } {
  const m = 0.5 * (s11 + s22)
  const d = 0.5 * (s11 - s22)
  const rad = Math.sqrt(d * d + s12 * s12)
  return { t1: m + rad, t2: m - rad }
}

/**
 * Field names: deviatoric polar (trr, trt, ttt), deviatoric Cartesian (txx,
 * tyy, txy), polar Cauchy perturbation (srr, stt, srt) and the in-plane
 * principals of the Cartesian Cauchy perturbation (st1 >= st2).
 */
export type SlabField = 'trr' | 'trt' | 'ttt' | 'txx' | 'tyy' | 'txy' | 'srr' | 'stt' | 'srt' | 'st1' | 'st2'

/** One named field (Pa) at (x, y) metres from the patch centre. */
export function fieldAt(x: number, y: number, p: SlabParams, s: SlabScales, field: SlabField): number {
  switch (field) {
    case 'trr':
    case 'trt':
    case 'ttt':
      return tauPolarAt(x, y, p, s)[field]
    case 'txx':
    case 'tyy':
    case 'txy':
      return tauCartesianAt(x, y, p, s)[field]
    case 'srr':
    case 'stt':
    case 'srt': {
      const { trr, trt, ttt } = tauPolarAt(x, y, p, s)
      const { s11, s22, s12 } = cauchyPerturbation(trr, ttt, trt)
      return field === 'srr' ? s11 : field === 'stt' ? s22 : s12
    }
    case 'st1':
    case 'st2': {
      const { txx, tyy, txy } = tauCartesianAt(x, y, p, s)
      const { s11, s22, s12 } = cauchyPerturbation(txx, tyy, txy)
      const { t1, t2 } = principals(s11, s22, s12)
      return field === 'st1' ? t1 : t2
    }
  }
}

/**
 * The 2-D theory's depth-averaged tau_xx along the centreline y = 0 (Pa),
 * for signed x in metres — equal to tau_rr there, with cos(theta) = sign(x).
 * Positive (tension) for x < 0, the upstream side; negative downstream.
 */
export function centreline2D(x: number, p: SlabParams, s: SlabScales): number {
  const r = Math.abs(x)
  const sign = x < 0 ? -1 : 1
  return s.stressPa * tauHatBranch(s.k0 * r, r < p.R, s).rr * sign
}

/**
 * The 1-D closed form of Rines et al. (J. Glaciol. 2026, Eq. 42) for a
 * Newtonian slab (n = 1) on a free-slip patch of length ℓ = 2 R: decay length
 * [x] = sqrt(4 eta H / c0) = 1 / k0 and amplitude [tau] = rho g alpha ℓ / 4 =
 * rho g alpha R / 2. A linear ramp −[tau] x / R inside |x| <= R, and
 * ∓[tau] exp(−(|x| − R) k0) outside. SIGN CONVENTION matches centreline2D:
 * upstream is x < 0, where the ramp is +[tau] at the patch edge (tension);
 * the ice is compressed on the downstream (+x) side. |oneD| peaks at
 * exactly [tau] at x = ±R.
 */
export function oneD(x: number, p: SlabParams, s: SlabScales): number {
  const ax = Math.abs(x)
  if (ax <= p.R) return -s.stressPa * (x / p.R)
  const sign = x < 0 ? -1 : 1
  return -sign * s.stressPa * Math.exp(-(ax - p.R) * s.k0)
}

/**
 * A field sampled on an n×n grid over [−halfWidthM, halfWidthM]² (Pa), for
 * painting a canvas: row-major, index = row * n + col, with x = −hw + col·step
 * and y = −hw + row·step (step = 2 hw / (n − 1); endpoints included), i.e.
 * y increasing downward as in image coordinates. Of the fields only trt,
 * srt and txy are antisymmetric in y, so the row order matters only for
 * those three; reverse the rows for a "+y up" map.
 */
export function fieldGrid(p: SlabParams, s: SlabScales, field: SlabField, halfWidthM: number, n: number): Float32Array {
  const out = new Float32Array(n * n)
  const step = n > 1 ? (2 * halfWidthM) / (n - 1) : 0
  for (let row = 0; row < n; row++) {
    const y = -halfWidthM + row * step
    for (let col = 0; col < n; col++) {
      const x = -halfWidthM + col * step
      out[row * n + col] = fieldAt(x, y, p, s, field)
    }
  }
  return out
}
