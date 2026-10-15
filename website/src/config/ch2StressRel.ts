// Chapter 2's deeper dive · STRESS RELATIONS (#stress-relations): the
// seven blocks and the LaTeX SVGs each stacks, in order.
// SVGs: cinematic/scene_ch02/build_stress_rel_eqs.py → R2 ch02/eq_rel/
// (a rebuild = a new prefix, eq_rel_v2, never a re-upload).
import { mediaUrl } from './media'
import type { Ch2RelEqName } from './ch2RelEqs'

export type Ch2RelBlock = 'glen' | 'cauchy' | 'ssa' | 'polar' | 'surface' | 'principals' | 'perturbation' | 'theory'

/** Each block's rows, top to bottom (each row one SVG, centred). */
export const CH2_REL_BLOCKS: Record<Ch2RelBlock, Ch2RelEqName[]> = {
  // The director noticed Glen's flow law appeared nowhere in the
  // additional work: the viscous model's rheology as SI §4
  // states it — Glen's form, the Cauchy stress + strain rate, the
  // effective viscosity (SI Eq. 39), the Arrhenius rate factor with the
  // run .sif's constants (Cuffey & Paterson 2010, the switch at −10 °C).
  glen: ['rel_glen_classic', 'rel_glen_cauchy', 'rel_glen_eta', 'rel_glen_arrhenius', 'rel_glen_consts'],
  cauchy: ['rel_cauchy', 'rel_trace'],
  ssa: ['rel_ssa', 'rel_ssa_zz'],
  polar: ['rel_polar_xy', 'rel_polar_fwd', 'rel_polar_inv', 'rel_polar_zz'],
  surface: ['rel_surface'],
  // The director also wanted the in-plane stresses' derivation shown: at
  // the surface there are six stress components, which reduce to the two
  // principals. So the SI §4C recipe
  // first — n from z_s and the tangent basis, the six-component σ projected
  // to s_ij, Eq. [52] in s_ij — then the flat-surface forms.
  principals: ['rel_princ_normal', 'rel_princ_sigma', 'rel_princ_s', 'rel_princ_flat_note', 'rel_princ', 'rel_princ_order'],
  perturbation: ['rel_pert_def', 'rel_pert_t1'],
  theory: ['rel_th_params', 'rel_th_coef', 'rel_th_tau', 'rel_th_dsig_def', 'rel_th_dsig'],
}

/** Screen-reader text for each SVG. */
export const CH2_REL_ALT: Record<Ch2RelEqName, string> = {
  rel_glen_classic: 'ε̇ij = A(T) τe^(n−1) τij, τe = √(½ τij τij) ⇔ τij = 2η ε̇ij',
  rel_glen_cauchy: 'σ = −p I + 2η ε̇, ε̇ = ½(∇u + ∇uᵀ)',
  rel_glen_eta: 'η = ε̇e^((1−n)/n) / (2 A(T)^(1/n)), ε̇e = √(½ ε̇ij ε̇ij), n = 3',
  rel_glen_arrhenius: 'A(T) = A1 exp(−Q1/RT) for T ≤ −10 °C; A2 exp(−Q2/RT) for T > −10 °C',
  rel_glen_consts: 'A1 = 2.89e−13, A2 = 2.43e−2 Pa^−3 s^−1; Q1 = 60, Q2 = 115 kJ mol^−1; T = T(z)',
  rel_cauchy: 'σij = −p δij + τij',
  rel_trace: 'τxx + τyy + τzz = 0, p = −(σxx + σyy + σzz)/3',
  rel_ssa: 'σ̄rr = 2τ̄rr + τ̄θθ − ρgH/2; σ̄θθ = 2τ̄θθ + τ̄rr − ρgH/2; σ̄rθ = τ̄rθ',
  rel_ssa_zz: 'τ̄zz = −(τ̄rr + τ̄θθ)',
  rel_polar_xy: 'x = r cos θ, y = r sin θ',
  rel_polar_fwd: 'τrr = τxx cos²θ + τyy sin²θ + τxy sin 2θ; τθθ = τxx sin²θ + τyy cos²θ − τxy sin 2θ; τrθ = (τyy − τxx) sin θ cos θ + τxy cos 2θ',
  rel_polar_inv: 'τxx = τrr cos²θ + τθθ sin²θ − τrθ sin 2θ; τyy = τrr sin²θ + τθθ cos²θ + τrθ sin 2θ; τxy = (τrr − τθθ) sin θ cos θ + τrθ cos 2θ',
  rel_polar_zz: 'τzz unchanged; τxx + τyy = τrr + τθθ',
  rel_surface: 'σ·n = 0; sij = eiᵀ σ ej (e1, e2 ⊥ n); σn = nᵀ σ n (residual)',
  rel_princ_normal: 'n = (−∂x zs, −∂y zs, 1)/√(1 + |∇zs|²); e1 = (x̂ − (x̂·n) n)/|x̂ − (x̂·n) n|; e2 = n × e1',
  rel_princ_sigma: 'σ at z = zs = the 3×3 symmetric matrix of σxx, σyy, σzz, σxy, σxz, σyz; s_ij = e_iᵀ σ e_j, i, j = 1, 2',
  rel_princ_s: 'σt1,t2 = (s11 + s22)/2 ± √((s11 − s22)²/4 + s12²)',
  rel_princ_flat_note: 'on a flat surface (n = ẑ: e1 = x̂, e2 = ŷ, s_ij → σxx, σyy, σxy)',
  rel_princ: 'σt1,t2 = (σxx + σyy)/2 ± √(((σxx − σyy)/2)² + σxy²) = (σrr + σθθ)/2 ± √(((σrr − σθθ)/2)² + σrθ²)',
  rel_princ_order: 'σt1 ≥ σt2 (tension > 0)',
  rel_pert_def: 'Δσ = σ^patch − σ^no patch',
  rel_pert_t1: 'Δσt1 = σt1(Δσ) ≠ σt1(σ^patch) − σt1(σ^no patch)',
  rel_th_params: 'λ ≡ k0 R, r̃ ≡ k0 r, k0 = √(c0/4ηH), Q ≡ ρgαR/4η',
  rel_th_coef: 'δ0 = −Q fδ(λ), ζ0 = Q fζ(λ), τ̃ ≡ τ̄ij / (ρgαR/2)',
  rel_th_tau: 'τ̃rr, τ̃rθ, τ̃θθ: PNAS SI Eq. 34',
  rel_th_dsig_def: 'Δσ̄rr = 2τ̄rr + τ̄θθ, Δσ̄θθ = 2τ̄θθ + τ̄rr, Δσ̄rθ = τ̄rθ',
  rel_th_dsig: 'Δσ̃rr, Δσ̃rθ, Δσ̃θθ: PNAS SI Eq. 35',
}

export function ch2RelEqUrl(name: Ch2RelEqName): string {
  return mediaUrl(`ch02/eq_rel/${name}.svg`)
}
