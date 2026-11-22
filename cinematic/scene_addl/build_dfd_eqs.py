"""
The APS DFD 2026 page, SectionDfd.vue (the shallow-stream theory, 1-D and 2-D,
from the Stokes problem to the closed-form stress solutions) — its math,
compiled by REAL LaTeX with Ch.1's pipeline
(cinematic/scene_ch01/build_theory_eqs.py: latex + dvisvgm, Computer
Modern, the TeX box as the viewBox, the baseline recorded) — imported,
not copied. Every equation is set in display style, colour "ink" (warm
white) for the dark page.

Four groups:
  * the GOVERNING equations and model: Stokes, the Newtonian rheology,
    the free-surface and bed conditions (PNAS SI Eqs. stokes_mom,
    stokes_cont, bc_surface, bc_bed_weertman, bc_bed_patch), the 2-D SSA
    (PNAS Eq. SSA) and the 1-D SSA (Rines et al. 2026 Eq. 7, n = 1) split
    into membrane / basal-drag / driving-stress pieces, the modified
    Helmholtz equations for the perturbation's divergence and vorticity
    (SI Eqs. kg-delta, kg-zeta), the definitions k0, lambda, gamma, the
    stress and length scales (PNAS Eq. scales) and the shallow assumption.
  * the 1-D SOLUTION (Rines et al. 2026 Eq. 42 with n = 1, patch length
    l = 2R, x from the patch centre): the three rows as separate pieces
    with their x-range conditions, plus the equation as published.
  * the 2-D SOLUTION (PNAS SI Eq. 34): the rr component split into
    highlightable pieces, the theta-theta and r-theta components whole,
    the mode amplitudes f_delta, f_zeta (SI Eqs. delta_0, zeta_0), the
    Bessel asymptote and the Cauchy-stress combinations (SI text before
    Eq. 35).
  * SYMBOLS and readouts: the sweep's parameters, the curve labels, the
    validity metric and the axis titles of the validity map.

Outputs:
  cinematic/data/eq_dfd/<name>.svg       (upload to R2 dfd/eq_v1/)
  website/.r2-cache/dfd/eq_v1/<name>.svg (the dev server's local mirror)
  website/src/config/dfdEqs.ts           (sizes in bp, committed)

Run:  python3 -I cinematic/scene_addl/build_dfd_eqs.py
Then: rclone copy cinematic/data/eq_dfd r2:<bucket>/dfd/eq_v1 --header-upload 'Cache-Control: public, max-age=31536000, immutable'
      (the website/.r2-cache mirror is written by this script)
Needs /Library/TeX/texbin (latex, dvisvgm).
"""

import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "cinematic" / "scene_ch01"))
import build_theory_eqs as bte  # noqa: E402

OUT = ROOT / "cinematic" / "data" / "eq_dfd"
R2_CACHE = ROOT / "website" / ".r2-cache" / "dfd" / "eq_v1"
TS_OUT = ROOT / "website" / "src" / "config" / "dfdEqs.ts"

SI = "PNAS SI"
JOG = "Rines et al. 2026"
# name: (tex, source)
EQS = {
    # ── governing equations and model ──
    "pde_stokes": (r"\nabla\cdot\boldsymbol{\sigma} + \rho\,\boldsymbol{g} = \boldsymbol{0},\qquad \nabla\cdot\boldsymbol{u} = 0",
                   f"Stokes: momentum + incompressibility; {SI} Eqs. stokes_mom, stokes_cont"),
    "pde_newton": (r"\boldsymbol{\sigma} = -p\,\boldsymbol{I} + 2\eta\,\dot{\boldsymbol{\varepsilon}},\qquad \dot{\boldsymbol{\varepsilon}} = \tfrac12\left(\nabla\boldsymbol{u} + \nabla\boldsymbol{u}^{\mathsf{T}}\right)",
                   "Newtonian rheology, eta = 1e14 Pa s"),
    "pde_surface": (r"\boldsymbol{\sigma}\cdot\boldsymbol{n} = \boldsymbol{0}\quad\text{on } z = z_s",
                    f"free surface; {SI} Eq. bc_surface"),
    "pde_bed": (r"\boldsymbol{\tau}_b = -\,c_0\,\boldsymbol{u}_b\quad (r > R),\qquad \boldsymbol{\tau}_b = \boldsymbol{0}\quad (r \le R)",
                f"linear Weertman sliding outside the patch, free slip inside; {SI} Eqs. bc_bed_weertman, bc_bed_patch"),
    "pde_ssa2d_mem": (r"\nabla\cdot\!\left[H\left(\overline{\boldsymbol{\tau}} + \operatorname{tr}\!\left(\overline{\boldsymbol{\tau}}\right)\boldsymbol{I}\right)\right]",
                      "2-D SSA, membrane-stress term; PNAS Eq. SSA"),
    "pde_ssa2d_drag": (r"-\;c_0\,\overline{\boldsymbol{u}}", "2-D SSA, basal drag term"),
    "pde_ssa2d_drv": (r"=\;\rho g H\,\nabla s", "2-D SSA, driving stress"),
    "pde_ssa1d_mem": (r"\partial_x\!\left(4\eta H\,\partial_x\overline{u}\right)",
                      f"1-D SSA, membrane term ({JOG} Eq. 7 with n = 1, B = 2 eta)"),
    "pde_ssa1d_drag": (r"-\;c_0\,\overline{u}", "1-D SSA, basal drag"),
    "pde_ssa1d_drv": (r"=\;-\,\rho g H\,\alpha", "1-D SSA, driving stress, s_x = -alpha"),
    "pde_helm": (r"\left(\nabla^2 - k_0^2\right)\delta = 0,\qquad \left(\nabla^2 - 4k_0^2\right)\zeta = 0",
                 f"{SI} Eqs. kg-delta, kg-zeta: the divergence and vorticity of the perturbation obey modified Helmholtz equations"),
    "def_dz": (r"\delta \equiv \nabla\cdot\boldsymbol{u}',\qquad \zeta \equiv \hat{\boldsymbol{z}}\cdot\nabla\times\boldsymbol{u}'",
               "divergence and vorticity of the velocity perturbation"),
    "def_k0": (r"k_0 \equiv \sqrt{\frac{c_0}{4\eta H}}", f"the inverse decay length; {SI} text before Eq. 34"),
    "def_lambda": (r"\lambda \equiv k_0 R,\qquad \tilde r \equiv k_0 r", f"{SI} Eq. 22 and text after Eq. 34"),
    "def_gamma": (r"\gamma \equiv \frac{c_0 H}{2\eta}", "the sweep's sliding parameter; c_b = 2 eta gamma / H"),
    "def_decay_gamma": (r"\frac{1}{k_0} = H\sqrt{\frac{2}{\gamma}}", "the decay length in terms of gamma"),
    "scales": (r"[\tau] = \tfrac12\,\rho g\alpha R,\qquad [x] = \frac{1}{k_0} = \sqrt{\frac{4\eta H}{c_0}}", "PNAS Eq. scales"),
    "scale_stress": (r"\tfrac12\,\rho g\alpha R", "stress scale"),
    "scale_decay": (r"\sqrt{4\eta H/c_0}", "decay length"),
    "assum_shallow": (r"H \ll R,\qquad H \ll 1/k_0", "the shallow-stream assumption"),
    # ── the 1-D solution (Rines et al. 2026 Eq. 42, n = 1, l = 2R, x from the patch centre, flow toward +x) ──
    "s1_lhs": (r"\frac{\tau_{xx}}{\tfrac12\rho g\alpha R}\;=", f"1-D solution, left-hand side ({JOG} Eq. 42, n = 1, scaled by [tau] = rho g alpha R/2)"),
    "s1_up": (r"e^{\,k_0\,(x + R)}", "upstream boundary layer"),
    "s1_in": (r"-\,\frac{x}{R}", "inside the patch: linear"),
    "s1_dn": (r"-\,e^{-k_0\,(x - R)}", "downstream boundary layer"),
    "c_up": (r"x < -R", "1-D condition: upstream of the patch"),
    "c_in": (r"|x| \le R", "1-D condition: inside the patch"),
    "c_dn": (r"x > R", "1-D condition: downstream of the patch"),
    "lab_l": (r"\ell = 2R", "the patch length in the 1-D paper's notation"),
    "s1_jog": (r"\frac{\tau_{xx}}{\rho g\alpha\ell/4} = \begin{cases} e^{\,x/[x]}, & x \le 0 \\[4pt] 1 - 2x/\ell, & 0 \le x \le \ell \\[4pt] -\,e^{-(x-\ell)/[x]}, & x \ge \ell \end{cases}",
               "JOG Eq. 42 as published, any n; x from the upstream edge"),
    "s1_jog_x": (r"[x] = \left(\frac{2Bh}{C}\right)^{\!\frac{n}{n+1}}\!,\qquad n = 1,\ B = 2\eta,\ C = c_0\ \Rightarrow\ [x] = \sqrt{\frac{4\eta H}{c_0}} = \frac{1}{k_0}",
                 "JOG Eq. 14 mapped to the 2-D notation"),
    # ── the 2-D solution (PNAS SI Eq. 34): rr split into highlightable pieces, the other two whole ──
    "s2_lhs": (r"\frac{\overline{\tau}_{rr}}{\tfrac12\rho g\alpha R}\;=\;\cos\theta\;\times", f"2-D solution, rr left-hand side ({SI} Eq. 34a)"),
    "s2_in": (r"-\left(1 - \tfrac14 f_\delta(\lambda)\right)\frac{\tilde r}{\lambda}", "inside the patch"),
    "s2_out_a": (r"-\;\frac{f_\delta(\lambda)}{K_1(\lambda)}\,K_1''(\tilde r)", "outside: the divergence mode, decay length 1/k0"),
    "s2_out_b": (r"+\;\frac{f_\zeta(\lambda)}{K_1(2\lambda)}\,\frac{K_2(2\tilde r)}{2\tilde r}", "outside: the vorticity mode, decay length 1/(2 k0)"),
    "c_rin": (r"r < R", "2-D condition: inside the patch"),
    "c_rout": (r"r > R", "2-D condition: outside the patch"),
    "s2_fd": (r"f_\delta(\lambda) = \frac{2 + 2\lambda\,\sigma(2\lambda) + \lambda^2}{4 + \lambda\,\sigma(\lambda) + 2\lambda\,\sigma(2\lambda) + \tfrac54\lambda^2}",
              f"{SI} Eq. delta_0"),
    "s2_fz": (r"f_\zeta(\lambda) = \frac{4\left(2 + \lambda\,\sigma(\lambda) + \tfrac14\lambda^2\right)}{4 + \lambda\,\sigma(\lambda) + 2\lambda\,\sigma(2\lambda) + \tfrac54\lambda^2}",
              f"{SI} Eq. zeta_0"),
    "s2_sigma": (r"\sigma(t) \equiv K_0(t)/K_1(t)", f"{SI} notation"),
    # ── the Bessel functions K_n (the SOLUTIONS beat's BESSEL K panel): where
    #    they come from, what defines them, how they behave ──
    "bessel_sep": (r"\delta = D(r)\cos\theta,\quad \zeta = Z(r)\sin\theta\;\Rightarrow\; r^2 D'' + r\,D' - \left(k_0^2 r^2 + 1\right) D = 0",
                   f"{SI} Eqs. kg-delta, kg-zeta in polar coordinates: the cos theta mode of the modified Helmholtz equation is the modified Bessel equation of order 1 (Z: the same with 2 k_0)"),
    "bessel_ode": (r"x^2 K_n'' + x\,K_n' - \left(x^2 + n^2\right) K_n = 0",
                   "the modified Bessel equation; K_n is its solution that decays, I_n the one that grows"),
    "bessel_int": (r"K_n(x) = \int_0^{\infty} e^{-x\cosh t}\cosh(nt)\,dt",
                   "the modified Bessel function of the second kind, as an integral"),
    "bessel_small": (r"K_n(x) \sim \tfrac12\,\Gamma(n)\left(\tfrac{2}{x}\right)^{n}\quad (x \to 0,\ n \ge 1)",
                     "near the patch: algebraic growth toward the centre"),
    "bessel_k1pp": (r"K_1''(x) = K_1(x) + \frac{K_0(x)}{x} + \frac{2K_1(x)}{x^2}",
                    "the identity the rr solution uses (from the order-1 equation and K_1' = -K_0 - K_1/x)"),
    "bessel_ax": (r"K_n(x)", "the Bessel panel's y-axis"),
    "bessel_exp": (r"e^{-x}", "the Bessel panel's reference curve"),
    # ── the FLASH SLIDE's one equation: the rr solution whole (the pieces above, in one display) ──
    "slide_s2": (r"\frac{\overline{\tau}_{rr}}{\tfrac12\rho g\alpha R} = \cos\theta \begin{cases} -\left(1 - \tfrac14 f_\delta\right)\dfrac{\tilde r}{\lambda}, & r < R \\[10pt] -\dfrac{f_\delta}{K_1(\lambda)}\,K_1''(\tilde r) + \dfrac{f_\zeta}{K_1(2\lambda)}\,\dfrac{K_2(2\tilde r)}{2\tilde r}, & r > R \end{cases}",
                 f"{SI} Eq. 34a whole, for the flash slide"),
    "slide_defs": (r"\tilde r = k_0 r,\qquad \lambda = k_0 R,\qquad f_\delta(\lambda) + \tfrac14 f_\zeta(\lambda) = 1",
                   "the slide's definitions line: the scaled radius, the one shape parameter, the two mode amplitudes"),
    "s2_asym": (r"K_n(\tilde r) \sim \sqrt{\frac{\pi}{2\tilde r}}\;e^{-\tilde r}\quad (\tilde r \to \infty)", "why the far field decays exponentially"),
    "s2_tt": (r"\frac{\overline{\tau}_{\theta\theta}}{\tfrac12\rho g\alpha R} = \cos\theta \begin{cases} \left(1 - \tfrac54 f_\delta\right)\dfrac{\tilde r}{\lambda}, & r < R \\[8pt] \dfrac{f_\delta}{K_1(\lambda)}\,\dfrac{K_2(\tilde r)}{\tilde r} - \dfrac{f_\zeta}{K_1(2\lambda)}\,\dfrac{K_2(2\tilde r)}{2\tilde r}, & r > R \end{cases}",
              f"{SI} Eq. 34c"),
    "s2_rt": (r"\frac{\overline{\tau}_{r\theta}}{\tfrac12\rho g\alpha R} = \sin\theta \begin{cases} \left(1 - \tfrac34 f_\delta\right)\dfrac{\tilde r}{\lambda}, & r < R \\[8pt] -\dfrac{f_\delta}{K_1(\lambda)}\,\dfrac{K_2(\tilde r)}{\tilde r} + \dfrac{f_\zeta}{K_1(2\lambda)}\left[K_1''(2\tilde r) - \tfrac12 K_1(2\tilde r)\right], & r > R \end{cases}",
              f"{SI} Eq. 34b"),
    "s2_cauchy": (r"\Delta\overline{\sigma}_{rr} = 2\overline{\tau}_{rr} + \overline{\tau}_{\theta\theta},\qquad \Delta\overline{\sigma}_{\theta\theta} = 2\overline{\tau}_{\theta\theta} + \overline{\tau}_{rr},\qquad \Delta\overline{\sigma}_{r\theta} = \overline{\tau}_{r\theta}",
                  f"{SI} text before Eq. 35"),
    # ── symbols and readouts ──
    "sym_H": (r"H", "symbol: ice thickness"),
    "sym_alpha": (r"\alpha", "symbol: surface slope"),
    "sym_gamma": (r"\gamma", "symbol: the sweep's sliding parameter"),
    "sym_R": (r"R", "symbol: patch radius"),
    "sym_eta": (r"\eta", "symbol: viscosity"),
    "sym_c0": (r"c_0", "symbol: basal drag coefficient"),
    "sym_lambda": (r"\lambda", "symbol: lambda = k0 R"),
    "sym_k0inv": (r"1/k_0", "symbol: the decay length"),
    "sym_tau_scale": (r"[\tau]", "symbol: the stress scale"),
    "lab_1d": (r"\tau_{xx}\ \text{(1-D)}", "curve label: the 1-D solution"),
    "lab_2d": (r"\overline{\tau}_{xx}\ \text{(2-D, } y = 0)", "curve label: the 2-D solution along the flow line"),
    "err_def": (r"\varepsilon \equiv \frac{\max\left|\overline{\tau}^{\,\mathrm{Stokes}} - \overline{\tau}^{\,\mathrm{theory}}\right|}{\max\left|\overline{\tau}^{\,\mathrm{theory}}\right|}",
                "the validity metric, from the sweep manifest's max_kpa"),
    "ax_RH": (r"R/H", "validity-map axis: patch radius over thickness"),
    "ax_LH": (r"\dfrac{1}{k_0 H} = \sqrt{2/\gamma}", "validity-map axis: decay length over thickness"),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    R2_CACHE.mkdir(parents=True, exist_ok=True)
    manifest = {}
    with tempfile.TemporaryDirectory() as td:
        wd = Path(td)
        for name, (tex, src) in EQS.items():
            svg, dims = bte.compile_one(bte.math(tex, True), None, "ink", wd, name)
            svg, W, H, base = bte.set_box(svg, dims["w"], dims["h"], dims["d"])
            (OUT / f"{name}.svg").write_text(svg)
            shutil.copy2(OUT / f"{name}.svg", R2_CACHE / f"{name}.svg")
            manifest[name] = dict(w=W, h=H, base=base, src=src)
            print(f"  {name:16s} {W:7.2f} x {H:6.2f} bp   [{src}]")
    lines = [
        "// GENERATED by cinematic/scene_addl/build_dfd_eqs.py — do not edit.",
        "// LaTeX (latex + dvisvgm, Computer Modern)  for the APS DFD 2026",
        "// page (SectionDfd.vue — the shallow-stream theory: governing equations,",
        "// the 1-D and 2-D stress solutions, symbols and readouts),",
        "// served from the media bucket at dfd/eq_v1/<name>.svg. Sizes in bp;",
        "// base = image top → baseline.",
        "export interface DfdEqBox { w: number; h: number; base: number }",
        "export const DFD_EQ: Record<string, DfdEqBox> = {",
    ]
    for name, e in manifest.items():
        lines.append(f"  {name}: {{ w: {e['w']:.3f}, h: {e['h']:.3f}, base: {e['base']:.3f} }}, // {e['src']}")
    lines.append("}")
    TS_OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {len(manifest)} -> {TS_OUT.relative_to(ROOT)}")
    print(f"svgs in {OUT.relative_to(ROOT)} + {R2_CACHE.relative_to(ROOT)}: {len(manifest)}")
    print("\nupload:\n  rclone copy cinematic/data/eq_dfd r2:<bucket>/dfd/eq_v1 "
          "--header-upload 'Cache-Control: public, max-age=31536000, immutable'")


if __name__ == "__main__":
    main()
