"""
Ch.2 deeper dive · STRESS RELATIONS (#stress-relations), compiled by REAL
LaTeX → SVG. The director wanted the Chapter 2 deeper dive to write out
the conversions between all the different stresses, so their
relationships can be pointed to during the talk: sigma_t1 and sigma_t2,
then tau_xx, tau_yy, tau_xz, tau_zz, and the corresponding tau_rr etc.
in polar coordinates.
The agreed set (τ_xz / τ_yz left out; the free-surface line simplified):

  1  Cauchy ↔ deviatoric          σ_ij = −p δ_ij + τ_ij, tr τ = 0, p
  2  Depth-averaged Cauchy (SSA)  PNAS SI text before Eq. [35]
  3  Cartesian ↔ polar            rotation by θ about the patch centre,
                                  θ from the flow direction x, + inverse
  4  Free surface                 σ·n = 0; in-plane components; σ_n
  5  In-plane principals          added later (the director wanted the
                                  in-plane stresses' computation shown
                                  from the start: at the surface there
                                  are all six stress components, and they
                                  reduce to these two): the SI §4C recipe
                                  in full — n from z_s, the tangent basis
                                  (e_1 = x̂ projected, e_2 = n × e_1, as
                                  build_sim_superposed.tangent_principals
                                  does it), the six-component σ projected
                                  to s_ij, Eq. [52] in s_ij; then the SAME
                                  eigenvalues from (xx, yy, xy) or
                                  (rr, θθ, rθ) on a flat surface. The old
                                  rel_princ.svg stays on R2, unused
                                  (immutable); the new rows are new names.
  6  Perturbations                principal of the differenced tensor,
                                  not the difference of the principals
  7  Slippery-patch theory        the SI's parameters (Eqs. [22], [23c,d]),
                                  the rescaled τ̃ (Eq. [34]) and the boxed
                                  Δσ̃ (Eq. [35]) — notation copied from
                                  source_data/manuscript_pnas/si/main.tex

Same pipeline as Ch.1/Ch.2 (cinematic/scene_ch01/build_theory_eqs.py:
latex + dvisvgm, Computer Modern, the TeX box as the viewBox) — its
functions are imported, not copied.

Outputs:
  cinematic/data/eq_ch02_rel/<name>.svg   (upload to R2 ch02/eq_rel/)
  website/src/config/ch2RelEqs.ts         (sizes in bp, committed)

Run:  cinematic/.venv/bin/python cinematic/scene_ch02/build_stress_rel_eqs.py
Then: rclone copy cinematic/data/eq_ch02_rel r2:<bucket>/ch02/eq_rel --header-upload 'Cache-Control: public, max-age=31536000, immutable'
      (+ the same into website/.r2-cache/ch02/eq_rel for dev)
R2 objects are immutable: new bytes = a new prefix (eq_rel_v2), never a re-upload.
"""

import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "cinematic" / "scene_ch01"))
import build_theory_eqs as bte  # noqa: E402

# dcases (mathtools): the theory's case lines in display style, so the
# ¼ f_δ(λ) inside a numerator is not set at scriptscript size.
bte.PREAMBLE += "\\usepackage{mathtools}\n"

OUT = ROOT / "cinematic" / "data" / "eq_ch02_rel"
TS_OUT = ROOT / "website" / "src" / "config" / "ch2RelEqs.ts"

G = lambda s: r"\textcolor{gold}{" + s + "}"  # noqa: E731

# name: (tex, display?, color, source)
EQS = {
    # ── 0 · Glen's flow law (the director noticed the flow law appeared
    # nowhere in the deeper-dive material) — the viscous model's
    # rheology as SI §4 states it (eq:glen_flow_law, "SI Eq. 39" on the
    # site): the law in Glen's form, the Cauchy stress + strain rate the SI
    # writes before it, the effective viscosity, and the Arrhenius rate
    # factor with the run .sif's constants (Cuffey & Paterson 2010; Limit
    # Temperature −10 °C; source_data/pnas_sims/bc/*_glen_*_tsic_base.sif).
    "rel_glen_classic": (
        r"\dot{\varepsilon}_{ij} = A(T)\,\tau_e^{\,n-1}\,\tau_{ij}, \qquad \tau_e = \sqrt{\tfrac{1}{2}\tau_{ij}\tau_{ij}} \qquad \Longleftrightarrow \qquad \tau_{ij} = 2\eta\,\dot{\varepsilon}_{ij}",
        True, "ink", "Glen (1955); the form SI Eq. [39] inverts"),
    "rel_glen_cauchy": (
        r"\boldsymbol{\sigma} = -p\,\boldsymbol{I} + 2\eta\,\dot{\boldsymbol{\varepsilon}}, \qquad \dot{\boldsymbol{\varepsilon}} = \tfrac{1}{2}\left(\nabla\boldsymbol{u} + \nabla\boldsymbol{u}^{T}\right)",
        True, "ink", "SI §4, the text before Eq. [39]"),
    "rel_glen_eta": (
        r"\eta = \frac{1}{2A(T)^{1/n}}\,\dot{\varepsilon}_e^{\,(1-n)/n}, \qquad \dot{\varepsilon}_e = \sqrt{\tfrac{1}{2}\dot{\varepsilon}_{ij}\dot{\varepsilon}_{ij}}, \qquad n = 3",
        True, "ink", "SI Eq. [39] (eq:glen_flow_law)"),
    "rel_glen_arrhenius": (
        r"A(T) = \begin{dcases} A_1 \exp\!\left(-\frac{Q_1}{R\,T}\right), & T \le -10\,^{\circ}\mathrm{C} \\[6pt] A_2 \exp\!\left(-\frac{Q_2}{R\,T}\right), & T > -10\,^{\circ}\mathrm{C} \end{dcases}",
        True, "ink", "Arrhenius rate factor (Cuffey & Paterson 2010), as the sif sets it"),
    "rel_glen_consts": (
        r"A_1 = 2.89 \times 10^{-13},\quad A_2 = 2.43 \times 10^{-2}\ \mathrm{Pa^{-3}\,s^{-1}}, \qquad Q_1 = 60,\quad Q_2 = 115\ \mathrm{kJ\,mol^{-1}}, \qquad T = T(z)",
        True, "ink", "sif A1si / A2si / Q1 / Q2; T(z) the tile's SICOPOLIS profile"),
    # ── 1 · Cauchy ↔ deviatoric ─────────────────────────────────────────
    "rel_cauchy": (
        G(r"\sigma_{ij}") + r" = -p\,\delta_{ij} + " + G(r"\tau_{ij}"),
        True, "ink", "SI text before Eq. [35]: sigma_ij = -delta_ij p + tau_ij"),
    "rel_trace": (
        r"\tau_{xx} + \tau_{yy} + \tau_{zz} = 0, \qquad p = -\frac{1}{3}\left(\sigma_{xx} + \sigma_{yy} + \sigma_{zz}\right)",
        True, "ink", "deviatoric = trace-free; p = mean compressive stress"),
    # ── 2 · Depth-averaged Cauchy in the SSA (SI, text before Eq. [35]) ──
    "rel_ssa": (
        r"\begin{aligned}"
        r"\bar{\sigma}_{rr} &= 2\bar{\tau}_{rr} + \bar{\tau}_{\theta\theta} - \rho g H/2 \\"
        r"\bar{\sigma}_{\theta\theta} &= 2\bar{\tau}_{\theta\theta} + \bar{\tau}_{rr} - \rho g H/2 \\"
        r"\bar{\sigma}_{r\theta} &= \bar{\tau}_{r\theta}"
        r"\end{aligned}",
        True, "ink", "SI text before Eq. [35]"),
    "rel_ssa_zz": (
        r"\bar{\tau}_{zz} = -\left(\bar{\tau}_{rr} + \bar{\tau}_{\theta\theta}\right)",
        True, "ink", "trace-free (incompressible)"),
    # ── 3 · Cartesian ↔ polar about the patch centre ────────────────────
    "rel_polar_xy": (
        r"x = r\cos\theta, \qquad y = r\sin\theta",
        True, "ink", "patch centre at the origin, theta from the flow direction x"),
    "rel_polar_fwd": (
        r"\begin{aligned}"
        r"\tau_{rr} &= \tau_{xx}\cos^2\theta + \tau_{yy}\sin^2\theta + \tau_{xy}\sin 2\theta \\"
        r"\tau_{\theta\theta} &= \tau_{xx}\sin^2\theta + \tau_{yy}\cos^2\theta - \tau_{xy}\sin 2\theta \\"
        r"\tau_{r\theta} &= (\tau_{yy} - \tau_{xx})\sin\theta\cos\theta + \tau_{xy}\cos 2\theta"
        r"\end{aligned}",
        True, "ink", "rotation of the in-plane tensor by theta"),
    "rel_polar_inv": (
        r"\begin{aligned}"
        r"\tau_{xx} &= \tau_{rr}\cos^2\theta + \tau_{\theta\theta}\sin^2\theta - \tau_{r\theta}\sin 2\theta \\"
        r"\tau_{yy} &= \tau_{rr}\sin^2\theta + \tau_{\theta\theta}\cos^2\theta + \tau_{r\theta}\sin 2\theta \\"
        r"\tau_{xy} &= (\tau_{rr} - \tau_{\theta\theta})\sin\theta\cos\theta + \tau_{r\theta}\cos 2\theta"
        r"\end{aligned}",
        True, "ink", "the inverse (rotation by -theta)"),
    "rel_polar_zz": (
        r"\tau_{zz} = -\left(\tau_{xx} + \tau_{yy}\right) = -\left(\tau_{rr} + \tau_{\theta\theta}\right)",
        True, "ink", "rotation about z leaves tau_zz and the in-plane trace; trace-free"),
    # ── 4 · Free surface ────────────────────────────────────────────────
    "rel_surface": (
        r"\boldsymbol{\sigma}\cdot\mathbf{n} = \mathbf{0}"
        r"\qquad s_{ij} = \mathbf{e}_i^{\top}\boldsymbol{\sigma}\,\mathbf{e}_j\ \ (\mathbf{e}_1,\mathbf{e}_2 \perp \mathbf{n})"
        r"\qquad \sigma_n = \mathbf{n}^{\top}\boldsymbol{\sigma}\,\mathbf{n}\ \ (\text{residual})",
        True, "ink", "traction-free surface; tangent-plane components; normal residual"),
    # ── 5 · In-plane principals: the SI §4C recipe, then the flat forms ──
    "rel_princ_normal": (
        r"\mathbf{n} = \frac{\left(-\partial_x z_s,\; -\partial_y z_s,\; 1\right)}{\sqrt{1 + |\nabla z_s|^{2}}}, \qquad "
        r"\mathbf{e}_1 = \frac{\hat{\mathbf{x}} - (\hat{\mathbf{x}}\cdot\mathbf{n})\,\mathbf{n}}{\left|\hat{\mathbf{x}} - (\hat{\mathbf{x}}\cdot\mathbf{n})\,\mathbf{n}\right|}, \qquad "
        r"\mathbf{e}_2 = \mathbf{n}\times\mathbf{e}_1",
        True, "ink", "SI §4C: the outward surface normal from z_s(x, y); the tangent basis (e_1 = the flow direction projected onto the surface)"),
    "rel_princ_sigma": (
        r"\boldsymbol{\sigma}\big|_{z = z_s} = \begin{pmatrix} \sigma_{xx} & \sigma_{xy} & \sigma_{xz} \\ \sigma_{xy} & \sigma_{yy} & \sigma_{yz} \\ \sigma_{xz} & \sigma_{yz} & \sigma_{zz} \end{pmatrix}, \qquad "
        r"s_{ij} = \mathbf{e}_i^{\top}\boldsymbol{\sigma}\,\mathbf{e}_j \quad (i, j = 1, 2)",
        True, "ink", "the six surface Cauchy components, projected onto the tangent plane: the 2x2 block s_11, s_22, s_12"),
    "rel_princ_s": (
        G(r"\sigma_{t1,\,t2}")
        + r" = \frac{s_{11} + s_{22}}{2} \pm \sqrt{\frac{\left(s_{11} - s_{22}\right)^{2}}{4} + s_{12}^{2}}",
        True, "ink", "SI Eq. [52]: the eigenvalues of the in-plane block"),
    # (a row of `aligned` that STARTS with & fails inside this wrapper —
    # "Missing control sequence inserted" — so the flat-surface note is its
    # own row, and the two-line form below is the unchanged rel_princ)
    "rel_princ_flat_note": (
        r"\text{on a flat surface } \left(\mathbf{n} = \hat{\mathbf{z}}:\ \mathbf{e}_1 = \hat{\mathbf{x}},\ \mathbf{e}_2 = \hat{\mathbf{y}},\ s_{ij} \to \sigma_{xx},\, \sigma_{yy},\, \sigma_{xy}\right)",
        True, "ink", "the flat-surface case: the tangent plane is the (x, y) plane and s_ij are the Cartesian in-plane components"),
    "rel_princ": (
        r"\begin{aligned}"
        + G(r"\sigma_{t1,\,t2}")
        + r" &= \frac{\sigma_{xx} + \sigma_{yy}}{2} \pm \sqrt{\left(\frac{\sigma_{xx} - \sigma_{yy}}{2}\right)^{2} + \sigma_{xy}^{2}} \\"
        r" &= \frac{\sigma_{rr} + \sigma_{\theta\theta}}{2} \pm \sqrt{\left(\frac{\sigma_{rr} - \sigma_{\theta\theta}}{2}\right)^{2} + \sigma_{r\theta}^{2}}"
        r"\end{aligned}",
        True, "ink", "SI Eq. [52] on the 2x2 tangent-plane tensor, in (x, y) and in (r, theta)"),
    "rel_princ_order": (
        G(r"\sigma_{t1}") + r" \geq " + G(r"\sigma_{t2}") + r"\qquad (\text{tension} > 0)",
        True, "ink", "sigma_t1 the most tensile"),
    # ── 6 · Perturbations ───────────────────────────────────────────────
    "rel_pert_def": (
        r"\Delta\boldsymbol{\sigma} = \boldsymbol{\sigma}^{\mathrm{patch}} - \boldsymbol{\sigma}^{\mathrm{no\ patch}}",
        True, "ink", "the full tensors differenced first (SI Eq. [53])"),
    "rel_pert_t1": (
        G(r"\Delta\sigma_{t1}") + r" = \sigma_{t1}\!\left(\Delta\boldsymbol{\sigma}\right) \;\neq\; "
        r"\sigma_{t1}\!\left(\boldsymbol{\sigma}^{\mathrm{patch}}\right) - \sigma_{t1}\!\left(\boldsymbol{\sigma}^{\mathrm{no\ patch}}\right)",
        True, "ink", "principal of the difference, not the difference of the principals (SI Eq. [54])"),
    # ── 7 · Slippery-patch theory (PNAS SI) ─────────────────────────────
    "rel_th_params": (
        r"\lambda \equiv k_0 R, \qquad \tilde{r} \equiv k_0 r, \qquad k_0 = \sqrt{c_0/4\eta H}, \qquad Q \equiv \frac{\rho g \alpha R}{4\eta}",
        True, "ink", "SI Eq. [22] + text after Eq. [34]"),
    "rel_th_coef": (
        r"\delta_0 = -Q f_{\delta}(\lambda), \qquad \zeta_0 = Q f_{\zeta}(\lambda), \qquad "
        r"\tilde{\tau} \equiv \frac{\bar{\tau}_{ij}}{\frac{1}{2}\rho g \alpha R}",
        True, "ink", "SI Eqs. [23c], [23d]; the stress scale (text before Eq. [34])"),
    "rel_th_tau": (
        r"\begin{aligned}"
        r"\tilde{\tau}_{rr} &= \cos\theta\begin{dcases}"
        r"-\frac{\left(1 - \frac{1}{4}f_{\delta}(\lambda)\right)}{\lambda}\tilde{r} & r < R \\[0.4em]"
        r"-\frac{f_{\delta}(\lambda)}{K_1(\lambda)} K_1''(\tilde{r}) + \frac{f_{\zeta}(\lambda)}{K_1(2\lambda)} \frac{K_2(2\tilde{r})}{2\tilde{r}} & r > R"
        r"\end{dcases} \\[0.8em]"
        r"\tilde{\tau}_{r\theta} &= \sin\theta\begin{dcases}"
        r"\frac{\left(1 - \frac{3}{4}f_{\delta}(\lambda)\right)}{\lambda}\tilde{r} & r < R \\[0.4em]"
        r"-\frac{f_{\delta}(\lambda)}{K_1(\lambda)} \frac{K_2(\tilde{r})}{\tilde{r}} + \frac{f_{\zeta}(\lambda)}{K_1(2\lambda)} \left[K_1''(2\tilde{r}) - \frac{1}{2}K_1(2\tilde{r})\right] & r > R"
        r"\end{dcases} \\[0.8em]"
        r"\tilde{\tau}_{\theta\theta} &= \cos\theta\begin{dcases}"
        r"\frac{\left(1 - \frac{5}{4}f_{\delta}(\lambda)\right)}{\lambda}\tilde{r} & r < R \\[0.4em]"
        r"\frac{f_{\delta}(\lambda)}{K_1(\lambda)} \frac{K_2(\tilde{r})}{\tilde{r}} - \frac{f_{\zeta}(\lambda)}{K_1(2\lambda)} \frac{K_2(2\tilde{r})}{2\tilde{r}} & r > R"
        r"\end{dcases}"
        r"\end{aligned}",
        True, "ink", "SI Eq. [34] (tau_rr_rescaled, tau_rt_rescaled, tau_tt_rescaled)"),
    "rel_th_dsig_def": (
        r"\Delta\bar{\sigma}_{rr} = 2\bar{\tau}_{rr} + \bar{\tau}_{\theta\theta}, \qquad "
        r"\Delta\bar{\sigma}_{\theta\theta} = 2\bar{\tau}_{\theta\theta} + \bar{\tau}_{rr}, \qquad "
        r"\Delta\bar{\sigma}_{r\theta} = \bar{\tau}_{r\theta}",
        True, "ink", "SI text before Eq. [35] (pre-drainage: sigma-bar = -rho g H/2 isotropic)"),
    "rel_th_dsig": (
        r"\boxed{\begin{aligned}"
        r"\Delta\tilde{\sigma}_{rr} &= \cos\theta\begin{dcases}"
        r"-\frac{\left(1 - \frac{7}{4}f_{\delta}(\lambda)\right)}{\lambda}\tilde{r} & r < R \\[0.4em]"
        r"\frac{f_{\delta}(\lambda)}{K_1(\lambda)} \left(\frac{K_2(\tilde{r})}{\tilde{r}}-2K_1''(\tilde{r})\right) + \frac{f_{\zeta}(\lambda)}{K_1(2\lambda)} \frac{K_2(2\tilde{r})}{2\tilde{r}} & r > R"
        r"\end{dcases} \\[0.8em]"
        r"\Delta\tilde{\sigma}_{r\theta} &= \sin\theta\begin{dcases}"
        r"\frac{\left(1 - \frac{3}{4}f_{\delta}(\lambda)\right)}{\lambda}\tilde{r} & r < R \\[0.4em]"
        r"-\frac{f_{\delta}(\lambda)}{K_1(\lambda)} \frac{K_2(\tilde{r})}{\tilde{r}} + \frac{f_{\zeta}(\lambda)}{K_1(2\lambda)} \left[K_1''(2\tilde{r}) - \frac{1}{2}K_1(2\tilde{r})\right] & r > R"
        r"\end{dcases} \\[0.8em]"
        r"\Delta\tilde{\sigma}_{\theta\theta} &= \cos\theta\begin{dcases}"
        r"\frac{\left(1 - \frac{9}{4}f_{\delta}(\lambda)\right)}{\lambda}\tilde{r} & r < R \\[0.4em]"
        r"\frac{f_{\delta}(\lambda)}{K_1(\lambda)} \left(\frac{2K_2(\tilde{r})}{\tilde{r}}-K_1''(\tilde{r})\right) - \frac{f_{\zeta}(\lambda)}{K_1(2\lambda)} \frac{K_2(2\tilde{r})}{2\tilde{r}} & r > R"
        r"\end{dcases}"
        r"\end{aligned}}",
        True, "ink", "SI Eq. [35] (eq:cauchy_stresses), boxed as in the SI"),
}


def main():
    if not Path(bte.TEXBIN, "latex").exists():
        raise SystemExit(f"no latex at {bte.TEXBIN}")
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    with tempfile.TemporaryDirectory() as td:
        wd = Path(td)
        for name, (tex, display, color, src) in EQS.items():
            svg, dims = bte.compile_one(bte.math(tex, display), None, color, wd, name)
            svg, W, H, base = bte.set_box(svg, dims["w"], dims["h"], dims["d"])
            (OUT / f"{name}.svg").write_text(svg)
            manifest[name] = dict(w=W, h=H, base=base, src=src)
            print(f"  {name:16s} {W:7.2f} x {H:6.2f} bp   [{src}]")
    lines = [
        "// GENERATED by cinematic/scene_ch02/build_stress_rel_eqs.py — do not edit.",
        "// LaTeX-compiled (Computer Modern) Ch.2 deeper-dive stress relations,",
        "// served from R2 ch02/eq_rel/<name>.svg. Sizes in bp: w × h = the whole",
        "// image (TeX box + pad), base = image top → baseline.",
        "export interface Ch2RelEqBox { w: number; h: number; base: number }",
        "export const CH2_REL_EQ = {",
    ]
    for name, e in manifest.items():
        lines.append(f"  {name}: {{ w: {e['w']:.3f}, h: {e['h']:.3f}, base: {e['base']:.3f} }}, // {e['src']}")
    lines.append("} as const satisfies Record<string, Ch2RelEqBox>")
    lines.append("export type Ch2RelEqName = keyof typeof CH2_REL_EQ")
    TS_OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {len(manifest)} entries -> {TS_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
