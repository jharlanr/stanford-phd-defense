// Modified Bessel functions of the second kind — K0, K1, K2 and K1'' (the
// second derivative of K1) for real x > 0. These are the special functions
// the depth-averaged slab theory of Lai, Rines, Coffey et al. (2026, PNAS)
// needs outside the free-slip patch (SI eq:delta_0, eq:zeta_0 and the
// boxed eq:tau_components; see ./slabTheory.ts). Pure functions, no
// dependencies, nothing imported.
//
// K0 and K1 are the Numerical Recipes `bessk0` / `bessk1` polynomial fits,
// i.e. Abramowitz & Stegun 9.8.5–9.8.8, which below x = 2 lean on the
// small-argument fits for I0 and I1 (A&S 9.8.1, 9.8.3). Their absolute
// error on the scaled forms is ~1e-7, so about 1e-7 relative on K0 and K1
// themselves; the validation script measures 1.6e-7 max relative vs scipy.
// K2 comes from the recurrence K2 = K0 + 2 K1 / x (A&S 9.6.26) and K1''
// from the modified Bessel equation x² y'' + x y' − (x² + 1) y = 0 with
// K1' = −K0 − K1 / x (A&S 9.6.26 again):
//
//   K1''(x) = K1(x) + K0(x) / x + 2 K1(x) / x²
//
// (checked against scipy.special.kvp(1, x, 2) to 6e-16 by the fixture
// script). For large x everything underflows cleanly through exp(−x) → 0,
// so the functions return 0 rather than NaN for any finite x > 0; they are
// not meant for x ≤ 0 (K0, K1 → +∞ as x → 0⁺).

/** I0(x) for 0 < x < 3.75 (A&S 9.8.1); only ever called with x ≤ 2. */
function besselI0Small(x: number): number {
  const y = (x / 3.75) * (x / 3.75)
  return 1.0 + y * (3.5156229 + y * (3.0899424 + y * (1.2067492 + y * (0.2659732 + y * (0.360768e-1 + y * 0.45813e-2)))))
}

/** I1(x) for 0 < x < 3.75 (A&S 9.8.3); only ever called with x ≤ 2. */
function besselI1Small(x: number): number {
  const y = (x / 3.75) * (x / 3.75)
  return x * (0.5 + y * (0.87890594 + y * (0.51498869 + y * (0.15084934 + y * (0.2658733e-1 + y * (0.301532e-2 + y * 0.32411e-3))))))
}

/** K0(x), x > 0 (A&S 9.8.5 for x ≤ 2, 9.8.6 for x > 2). */
export function besselK0(x: number): number {
  if (x <= 2.0) {
    const y = (x * x) / 4.0
    return (
      -Math.log(x / 2.0) * besselI0Small(x) +
      (-0.57721566 + y * (0.4227842 + y * (0.23069756 + y * (0.348859e-1 + y * (0.262698e-2 + y * (0.1075e-3 + y * 0.74e-5))))))
    )
  }
  const y = 2.0 / x
  return (
    (Math.exp(-x) / Math.sqrt(x)) *
    (1.25331414 + y * (-0.7832358e-1 + y * (0.2189568e-1 + y * (-0.1062446e-1 + y * (0.587872e-2 + y * (-0.25154e-2 + y * 0.53208e-3))))))
  )
}

/** K1(x), x > 0 (A&S 9.8.7 for x ≤ 2, 9.8.8 for x > 2). */
export function besselK1(x: number): number {
  if (x <= 2.0) {
    const y = (x * x) / 4.0
    return (
      Math.log(x / 2.0) * besselI1Small(x) +
      (1.0 / x) * (1.0 + y * (0.15443144 + y * (-0.67278579 + y * (-0.18156897 + y * (-0.1919402e-1 + y * (-0.110404e-2 + y * -0.4686e-4))))))
    )
  }
  const y = 2.0 / x
  return (
    (Math.exp(-x) / Math.sqrt(x)) *
    (1.25331414 + y * (0.23498619 + y * (-0.365562e-1 + y * (0.1504268e-1 + y * (-0.780353e-2 + y * (0.325614e-2 + y * -0.68245e-3))))))
  )
}

/** [K0(x), K1(x)] in one call — the slab theory always needs both. */
export function besselK0K1(x: number): [number, number] {
  return [besselK0(x), besselK1(x)]
}

/** K2(x) = K0(x) + 2 K1(x) / x (A&S 9.6.26). */
export function besselK2(x: number): number {
  const [k0, k1] = besselK0K1(x)
  return k0 + (2 * k1) / x
}

/** K1''(x) = K1 + K0 / x + 2 K1 / x², from the modified Bessel equation. */
export function besselK1pp(x: number): number {
  const [k0, k1] = besselK0K1(x)
  return k1 + k0 / x + (2 * k1) / (x * x)
}
