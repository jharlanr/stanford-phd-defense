"""2-D analytical (shallow-shelf) theory for a circular free-slip patch of
radius R in a Newtonian slab of thickness H on a plane inclined at alpha,
with a linear Weertman sliding law (gamma = c0 H / (2 eta)) outside the
patch — the theory the PNAS SI (Fig. S1) and the thesis Chapter 2
validation figure (ssa_validation_R5000_H3000_a01_G01_err.png) compare
the periodic-slab Elmer/Ice sweep against.

FAITHFUL PORT of the live code of the notebook cell that produced those
figures (plot_simulations_flatslabnewt_vs_theory.ipynb, "cell 32"):
same constants, same functions, same inner (r < R) / outer (r >= R,
K-Bessel) branches, a_1 = 0, ROTATION_ANGLE = 0 (the "_forpaper_unrotated"
figure is the published one). Only additions: one vectorised assembler
that returns all three components at once (identical arithmetic), the
polar <-> Cartesian rotations the cell uses, and the in-plane Cauchy
PERTURBATION tensor (PNAS SI boxed forms; -rho g H / 2 cancels).

Units: SI inside (Pa, m, rad); the notebook divides by 1000 -> kPa.

Parameter decoding (as in the cell): slope code "01" -> 0.1 deg,
"05" -> 0.5 deg, "10" -> 1.0 deg (alpha = radians(float(code) / 10));
gamma code "01" -> 0.1, "1" -> 1.0.

Self-test (python slab_theory.py) checks the hero run's stress scale
(rho g alpha R / 2 = 39 kPa) and decay length (sqrt(4 eta H / c0) = 13.4 km),
the numbers the thesis quotes.
"""

import numpy as np
from scipy.special import kv, kvp

# Constants (from the cell)
eta = 1e14   # Pa s
rho = 917    # kg m^-3
g = 9.81     # m s^-2
A = 1 / (2 * eta)
ROTATION_ANGLE = 0  # degrees; the cell has `0#180` — 0 = the published, unrotated figure


# ── parameter decoding ─────────────────────────────────────────────────
def decode_slope(code: str) -> float:
    """Slope code -> alpha in DEGREES ("01" -> 0.1, "05" -> 0.5, "10" -> 1.0)."""
    return float(code) / 10.0


def decode_gamma(code: str) -> float:
    """Gamma code -> gamma ("01" -> 0.1, "1" -> 1.0), exactly as the cell."""
    return float(code) if code == "1" else float(code) / 10


# ── the cell's functions, verbatim arithmetic ──────────────────────────
def calculate_c0(gamma, h):
    return gamma / (A * h)


def calculate_k0(c0, h):
    return np.sqrt(c0 / (4 * eta * h))


def calculate_lambda(k0, R):
    return k0 * R


def calculate_Q(alpha, R):
    return (rho * g * alpha * R) / (4 * eta)


def delta_0(Q, lambda_val):
    numerator = -Q * (2 + 2 * lambda_val * kv(0, 2 * lambda_val) / kv(1, 2 * lambda_val) + lambda_val**2)
    denominator = (4 + lambda_val * kv(0, lambda_val) / kv(1, lambda_val)
                   + 2 * lambda_val * kv(0, 2 * lambda_val) / kv(1, 2 * lambda_val) + 1.25 * lambda_val**2)
    return numerator / denominator


def zeta_0(Q, lambda_val):
    numerator = 4 * Q * (2 + lambda_val * kv(0, lambda_val) / kv(1, lambda_val) + 0.25 * lambda_val**2)
    denominator = (4 + lambda_val * kv(0, lambda_val) / kv(1, lambda_val)
                   + 2 * lambda_val * kv(0, 2 * lambda_val) / kv(1, 2 * lambda_val) + 1.25 * lambda_val**2)
    return numerator / denominator


def calculate_a1(delta_0_val, k0, R):
    """a_1 (= b_1). The cell returns 0 (power-law terms cancel with a_1 = b_1)."""
    return 0


def calculate_tau_rr_inner(r, theta, delta_0_val, zeta_0_val, R):
    strain_rate_rr = (3 * delta_0_val - zeta_0_val) * r * np.cos(theta) / (4 * R)
    return 2 * eta * strain_rate_rr


def calculate_tau_rtheta_inner(r, theta, delta_0_val, zeta_0_val, R):
    strain_rate_rtheta = (zeta_0_val - delta_0_val) * r * np.sin(theta) / (4 * R)
    return 2 * eta * strain_rate_rtheta


def calculate_tau_thetatheta_inner(r, theta, delta_0_val, zeta_0_val, R):
    strain_rate_thetatheta = (delta_0_val + zeta_0_val) * r * np.cos(theta) / (4 * R)
    return 2 * eta * strain_rate_thetatheta


def calculate_tau_rtheta_outer(r, theta, delta_0_val, zeta_0_val, k0, R, lambda_val, Q):
    """eps_rtheta = -d/dr(phi/r) - d2psi/dr2 - zeta/2 (a_1 = b_1)."""
    t1_coeff = delta_0_val / kv(1, lambda_val)
    term1 = t1_coeff * kv(2, k0 * r) / (k0 * r)
    psi_coeff = -zeta_0_val / (4 * k0**2 * kv(1, 2 * k0 * R))
    psi_second_deriv = psi_coeff * (2 * k0)**2 * kvp(1, 2 * k0 * r, 2)
    term2 = -psi_second_deriv
    zeta_hat = zeta_0_val * kv(1, 2 * k0 * r) / kv(1, 2 * k0 * R)
    term3 = -0.5 * zeta_hat
    strain_rate_rtheta = (term1 + term2 + term3) * np.sin(theta)
    return 2 * eta * strain_rate_rtheta


def calculate_tau_thetatheta_outer(r, theta, delta_0_val, zeta_0_val, k0, R, lambda_val, Q):
    t1_coeff = delta_0_val / kv(1, lambda_val)
    term1 = t1_coeff * kv(2, k0 * r) / (k0 * r)
    t2_coeff = zeta_0_val / kv(1, 2 * lambda_val)
    term2 = t2_coeff * kv(2, 2 * k0 * r) / (2 * k0 * r)
    strain_rate_thetatheta = (-term1 - term2) * np.cos(theta)
    return 2 * eta * strain_rate_thetatheta


def calculate_tau_rr_outer(r, theta, delta_0_val, zeta_0_val, k0, R, lambda_val, Q):
    t1 = kvp(1, k0 * r, 2) * delta_0_val / kv(1, lambda_val)
    t2_coeff = zeta_0_val / kv(1, 2 * lambda_val)
    t2 = t2_coeff * kv(2, 2 * k0 * r) / (2 * k0 * r)
    strain_rate_rr = (t1 + t2) * np.cos(theta)
    return 2 * eta * strain_rate_rr


# ── assemblers ─────────────────────────────────────────────────────────
def solution_params(R, H, alpha, gamma):
    """alpha in RADIANS. Returns the cell's intermediate numbers."""
    c0 = calculate_c0(gamma, H)
    k0 = calculate_k0(c0, H)
    lam = calculate_lambda(k0, R)
    Q = calculate_Q(alpha, R)
    return dict(c0=c0, k0=k0, lambda_val=lam, Q=Q,
                delta_0=delta_0(Q, lam), zeta_0=zeta_0(Q, lam))


def polar_grid(x, y):
    """Patch centre = domain centre (as the cell). Returns X, Y, r, theta
    (theta WITHOUT rotation — the sim's polar projection uses this one)."""
    x_center = (x.max() + x.min()) / 2
    y_center = (y.max() + y.min()) / 2
    X, Y = np.meshgrid(x - x_center, y - y_center, indexing='xy')
    r = np.sqrt(X**2 + Y**2)
    theta = np.arctan2(Y, X)
    return X, Y, r, theta


def theory_polar(x, y, R, H, alpha, gamma):
    """tau_rr, tau_rtheta, tau_thetatheta (Pa) on the (y, x) grid — the
    cell's calculate_tau_{rr,rtheta,thetatheta}_theory, all three at once."""
    p = solution_params(R, H, alpha, gamma)
    d0, z0, k0, lam, Q = p['delta_0'], p['zeta_0'], p['k0'], p['lambda_val'], p['Q']
    _, _, r, theta = polar_grid(np.asarray(x, float), np.asarray(y, float))
    theta = theta + np.radians(ROTATION_ANGLE)
    trr = np.full_like(r, np.nan)
    trt = np.full_like(r, np.nan)
    ttt = np.full_like(r, np.nan)
    i = r < R
    o = r >= R
    trr[i] = calculate_tau_rr_inner(r[i], theta[i], d0, z0, R)
    trt[i] = calculate_tau_rtheta_inner(r[i], theta[i], d0, z0, R)
    ttt[i] = calculate_tau_thetatheta_inner(r[i], theta[i], d0, z0, R)
    trr[o] = calculate_tau_rr_outer(r[o], theta[o], d0, z0, k0, R, lam, Q)
    trt[o] = calculate_tau_rtheta_outer(r[o], theta[o], d0, z0, k0, R, lam, Q)
    ttt[o] = calculate_tau_thetatheta_outer(r[o], theta[o], d0, z0, k0, R, lam, Q)
    return trr, trt, ttt


# ── rotations (the cell's sim -> polar; and its inverse) ───────────────
def cart_to_polar(txx, tyy, txy, theta):
    trr = txx * np.cos(theta)**2 + tyy * np.sin(theta)**2 + txy * np.sin(2 * theta)
    ttt = txx * np.sin(theta)**2 + tyy * np.cos(theta)**2 - txy * np.sin(2 * theta)
    trt = (tyy - txx) * np.sin(theta) * np.cos(theta) + txy * np.cos(2 * theta)
    return trr, trt, ttt


def polar_to_cart(trr, trt, ttt, theta):
    c, s = np.cos(theta), np.sin(theta)
    txx = trr * c**2 + ttt * s**2 - trt * np.sin(2 * theta)
    tyy = trr * s**2 + ttt * c**2 + trt * np.sin(2 * theta)
    txy = (trr - ttt) * s * c + trt * np.cos(2 * theta)
    return txx, tyy, txy


# ── Cauchy perturbation + in-plane principals ──────────────────────────
def cauchy_perturbation(t11, t22, t12):
    """Delta sigma_11 = 2 tau_11 + tau_22, Delta sigma_22 = 2 tau_22 + tau_11,
    Delta sigma_12 = tau_12 (PNAS SI boxed forms) — valid in any in-plane
    orthonormal basis (polar or Cartesian)."""
    return 2 * t11 + t22, 2 * t22 + t11, t12


def principals(s11, s22, s12):
    m = 0.5 * (s11 + s22)
    rad = np.sqrt((0.5 * (s11 - s22))**2 + s12**2)
    return m + rad, m - rad


# ── per-run scales ─────────────────────────────────────────────────────
def stress_scale_pa(R, alpha):
    """rho g alpha R / 2 (alpha in radians)."""
    return rho * g * alpha * R / 2


def decay_length_m(H, gamma):
    """sqrt(4 eta H / c0) = 1 / k0."""
    return float(np.sqrt(4 * eta * H / calculate_c0(gamma, H)))


if __name__ == '__main__':
    a = np.radians(decode_slope('01'))
    gm = decode_gamma('01')
    s = stress_scale_pa(5000, a) / 1e3
    L = decay_length_m(3000, gm) / 1e3
    c0 = calculate_c0(gm, 3000)
    print(f'hero: stress scale {s:.1f} kPa (thesis 39), decay {L:.2f} km (thesis 13.4), c0 {c0:.2e} (fig 6.7e+09)')
    assert round(s) == 39 and round(L, 1) == 13.4 and f'{c0:.1e}' == '6.7e+09'
    assert decode_gamma('1') == 1.0 and decode_slope('10') == 1.0
    # rotation round trip
    rng = np.random.default_rng(0)
    t = rng.uniform(-np.pi, np.pi, 50)
    xx, yy, xy = rng.normal(size=(3, 50))
    back = polar_to_cart(*cart_to_polar(xx, yy, xy, t), t)
    assert np.allclose(back, (xx, yy, xy))
    print('ok')
