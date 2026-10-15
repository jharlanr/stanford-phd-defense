"""
Ch.2 RESULTS math labels, compiled by REAL LaTeX (the director wanted
the stress-space fonts bigger and in a much more elegant math
font). Same pipeline as Ch.1's (cinematic/scene_ch01/
build_theory_eqs.py: latex + dvisvgm, Computer Modern, the TeX box as the
viewBox with the baseline recorded) — its functions are imported, not
copied.

Notation follows the thesis Chapter 2 (tab:results_elastic / tab:results_viscous and the stress-
space figures): σ_t1, σ_t2 = the surface-tangent principal stresses,
σ^post = post-drainage, Δσ = the perturbation (with − without the
blister / patch).

The DEFINITIONS on every stress-space beat (the director wanted the
formulas for sigma1 and sigma2 on screen whenever a stress-space
diagram is shown) are the PNAS SI's, §4C "Principal stresses and
stress perturbations" (Lake_pnas_SI.pdf p. 16; source_data/
manuscript_pnas/si/main.tex, eqn:principals_calc; the thesis Ch.2 repeats
them verbatim): Eq. [52] σ_t1,t2 = (s11+s22)/2 ± √((s11−s22)²/4 + s12²)
with s_ij = e_iᵀ σ e_j, e1, e2 spanning the plane tangent to the surface
(normal n), σ_t1 ≥ σ_t2, tension positive; Eq. [53] Δσ = σ^post-drainage
− σ^pre-drainage (the FULL tensors differenced first); Eq. [54] Δσ_t1,t2
= the same eigenvalues of Δs_ij = e_iᵀ Δσ e_j. (The main text cites them
as "SI Eq. S53" / "S55" — one off the SI's printed [52] / [54].) Eq. [52]
is set as two lines, + and −, so the beat can light the one it plots.

The implications figure's numbers are per lake (beat 9 is the chosen
lake's figure), read from impl_lakes.json
(build_impl_lakes.py), so run that first.

Outputs:
  cinematic/data/eq_ch02/<name>.svg      (upload to R2 ch02/eq/)
  website/src/config/ch2Eqs.ts           (sizes in bp, committed)

Run:  python3 cinematic/scene_ch02/build_results_eqs.py
      (or `--only name1,name2` to add labels without re-baking the rest)
Then: rclone copy cinematic/data/eq_ch02 r2:<bucket>/ch02/eq --header-upload 'Cache-Control: public, max-age=31536000, immutable'
"""

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "cinematic" / "scene_ch01"))
import build_theory_eqs as bte  # noqa: E402

OUT = ROOT / "cinematic" / "data" / "eq_ch02"
TS_OUT = ROOT / "website" / "src" / "config" / "ch2Eqs.ts"
# impl_lakes_v2.json = impl_lakes.json's numbers with the seismic image
# names (build_impl_lakes.py); v3 the same numbers
# drawn flow left → right. The labels read only numbers.
IMPL = HERE / "output_results" / "impl" / "impl_lakes_v3.json"

# Eq. [52]'s right-hand side, verbatim (\frac{}{} display style).
EIG_RHS = r"\frac{s_{11}+s_{22}}{2} {sign} \sqrt{\frac{(s_{11}-s_{22})^2}{4}+s_{12}^2}"


def fmt_mpa(kpa: float) -> str:
    """1195 → '1.2', 230 → '0.23' (two significant figures)."""
    v = kpa / 1000.0
    return f"{v:.1f}" if v >= 1 else f"{v:.2f}"


def fmt_area(km2: float) -> str:
    """56.43 → '56', 3.85 → '3.9' (two significant figures)."""
    return f"{km2:.0f}" if km2 >= 10 else f"{km2:.1f}"


def impl_lake_eqs() -> dict:
    """Per lake + model: the reach over the bracket, peak + area under
    the panel. A reach that runs to the analysis window's upstream edge
    is a lower bound (≥)."""
    impl = json.loads(IMPL.read_text())
    out = {}
    for lake in impl["lakes"].values():
        num = lake["num"]
        half = lake["half_km"]
        for model, tag in (("elastic", "e"), ("viscous", "v")):
            m = lake["models"][model]
            up = m["upstream100_km"]
            edge = up >= half - 0.01
            reach = (rf"\geq {half:.1f}\ \mathrm{{km}}" if edge else rf"{up:.1f}\ \mathrm{{km}}")
            out[f"impl_reach_{tag}_{num}"] = (reach, False, "gold",
                                              f"{num} {model} upstream reach of >100 kPa {up} km"
                                              + (" (window edge)" if edge else ""))
            out[f"impl_nums_{tag}_{num}"] = (
                rf"\max\,\Delta\sigma_{{t1}} \approx {fmt_mpa(m['peak_kpa'])}\ \mathrm{{MPa}}"
                rf"\qquad A_{{\,\Delta\sigma_{{t1}} > 100\,\mathrm{{kPa}}}} \approx {fmt_area(m['area100_km2'])}\ \mathrm{{km}}^2",
                False, "ink",
                f"{num} {model} p99.9 {m['peak_kpa']} kPa, area>100 {m['area100_km2']} km2")
    return out


def eqs(with_impl: bool = True) -> dict:
    return {
        # ── stress-space axes (thesis fig:phasespace_elastic / fig:phasespace_viscous axis titles) ──────
        "ax_post_t1": (r"\sigma_{t1}^{\,\mathrm{post}}\ [\mathrm{kPa}]", False, "ink", "thesis fig:phasespace_viscous x-axis"),
        "ax_post_t2": (r"\sigma_{t2}^{\,\mathrm{post}}\ [\mathrm{kPa}]", False, "ink", "thesis fig:phasespace_viscous x-axis"),
        "ax_diff_t1": (r"\Delta\sigma_{t1}\ [\mathrm{kPa}]", False, "ink", "thesis fig:phasespace_viscous y-axis"),
        "ax_diff_t2": (r"\Delta\sigma_{t2}\ [\mathrm{kPa}]", False, "ink", "thesis fig:phasespace_viscous y-axis"),
        # the director asked for the axis title to go bold (and pulse with
        # the axis) so it is clear which axis is being discussed: the
        # EMPHASISED axis's title, set in TeX's bold math (\boldsymbol on
        # the whole label — the units bold too). The σ_t2 beats emphasise
        # BOTH axes (a follow-up note: the axes should also glow when
        # sigma_t2 is being looked at).
        # the population page's ELASTIC x-axis (the director wanted the
        # equation with the \\approx shown on the x-axis) — the ≈ definition with
        # the unit, drawn smaller to span the plot (Ch2StressSpace `xTitle`).
        "ax_post_s_t1": (r"\sigma_{t1}^{\,\mathrm{post}} \approx \sigma_{t1}\!\left(\boldsymbol{\sigma}^{\mathrm{pre}}_{\mathrm{viscous}} + \Delta\boldsymbol{\sigma}_{\mathrm{elastic}}\right)\ [\mathrm{kPa}]",
                         False, "ink", "population page, elastic x-axis: the approximate definition with its unit"),
        "ax_post_t1_bold": (r"\boldsymbol{\sigma_{t1}^{\,\mathrm{post}}\ [\mathrm{kPa}]}", False, "ink",
                            "thesis fig:phasespace_viscous x-axis, bold (emphasised)"),
        "ax_diff_t1_bold": (r"\boldsymbol{\Delta\sigma_{t1}\ [\mathrm{kPa}]}", False, "ink",
                            "thesis fig:phasespace_viscous y-axis, bold (emphasised)"),
        "ax_post_t2_bold": (r"\boldsymbol{\sigma_{t2}^{\,\mathrm{post}}\ [\mathrm{kPa}]}", False, "ink",
                            "thesis fig:phasespace_viscous x-axis, bold (emphasised), sigma_t2"),
        "ax_diff_t2_bold": (r"\boldsymbol{\Delta\sigma_{t2}\ [\mathrm{kPa}]}", False, "ink",
                            "thesis fig:phasespace_viscous y-axis, bold (emphasised), sigma_t2"),
        # ── panel symbols (gold) ───────────────────────────────────────
        "t1": (r"\sigma_{t1}", False, "gold", "thesis fig:phasespace_viscous column title"),
        "t2": (r"\sigma_{t2}", False, "gold", "thesis fig:phasespace_viscous column title"),
        # ── colorbars ──────────────────────────────────────────────────
        "cb_diff_t1": (r"\Delta\sigma_{t1}\ [\mathrm{MPa}]", False, "ink", "difference colorbar"),
        # the director wanted no card around the colourbar and none of the
        # words ('difference', 'with patch') — just the stress math
        # symbols: the block's bare colourbar names what is painted with
        # the symbol alone.
        "cb_diff_t2": (r"\Delta\sigma_{t2}\ [\mathrm{MPa}]", False, "ink", "difference colorbar, sigma_t2 beats"),
        "cb_pre_t1": (r"\sigma_{t1}^{\,\mathrm{pre}}\ [\mathrm{MPa}]", False, "ink", "pre-drainage (no blister / patch) colorbar"),
        "cb_post_t1": (r"\sigma_{t1}^{\,\mathrm{post}}\ [\mathrm{MPa}]", False, "ink", "post-drainage (with blister / patch) colorbar"),
        "cb_dR": (r"\Delta R", False, "ink", "imagery difference colorbar (Sentinel-2 reflectance, post - pre)"),
        # ── the DEFINITIONS (PNAS SI §4C, Eqs. [52]–[54]) ───────────────
        # Eq. [52], its + and − roots on their own lines (the symbol gold,
        # matching the diagram header's).
        "def_t1": (r"\textcolor{gold}{\sigma_{t1}} = " + EIG_RHS.replace("{sign}", "+"), True, "ink",
                   "SI Eq. [52], + root (sigma_t1 >= sigma_t2)"),
        "def_t2": (r"\textcolor{gold}{\sigma_{t2}} = " + EIG_RHS.replace("{sign}", "-"), True, "ink",
                   "SI Eq. [52], - root"),
        # the tangent-plane components Eq. [52] takes (SI §4C text)
        "def_s": (r"s_{ij} = \mathbf{e}_i^{\top}\boldsymbol{\sigma}\,\mathbf{e}_j, \qquad \mathbf{e}_1,\,\mathbf{e}_2 \perp \mathbf{n}",
                  True, "ink", "SI §4C: s_ij = e_i^T sigma e_j, e1, e2 spanning the tangent plane"),
        # Eqs. [53] + [54]: the FULL tensors differenced first (Δσ =
        # σ^post − σ^pre), then the same projection and eigenvalues —
        # Eq. [52] with s_ij replaced by Δs_ij = e_iᵀ Δσ e_j.
        "def_dt": (r"\Delta\sigma_{t1,\,t2}:\ \ s_{ij} \to \mathbf{e}_i^{\top}\big(\boldsymbol{\sigma}^{\mathrm{post}} - \boldsymbol{\sigma}^{\mathrm{pre}}\big)\,\mathbf{e}_j",
                   True, "ink", "SI Eqs. [53]-[54]: Eq. [52] on Delta s_ij = e_i^T (sigma^post - sigma^pre) e_j"),
        # ── implications figure ────────────────────────────────────────
        "impl_level": (r"\Delta\sigma_{t1} = 100\ \mathrm{kPa}", False, "ink", "the +100 kPa contour (thesis viscous overviews)"),
        "impl_R": (r"R = 2.5\ \mathrm{km}", False, "gold", "blister / patch radius (thesis §2.2, §2.3)"),
        # ── the POST · ELASTIC beat's key: the field is the
        # viscous pre-drainage state plus the elastic increment, tensors
        # added before the principal is taken (build_sim_superposed.py).
        "def_post_s": (r"\sigma_{t1}^{\,\mathrm{post}} = \sigma_{t1}\!\left(\boldsymbol{\sigma}^{\mathrm{pre}}_{\mathrm{viscous}} + \Delta\boldsymbol{\sigma}_{\mathrm{elastic}}\right)",
                       True, "ink", "post-drainage elastic = viscous pre + elastic perturbation, tensors first"),
        "def_post_s_v2": (r"\sigma_{t1}^{\,\mathrm{post}} \approx \sigma_{t1}\!\left(\boldsymbol{\sigma}^{\mathrm{pre}}_{\mathrm{viscous}} + \Delta\boldsymbol{\sigma}_{\mathrm{elastic}}\right)",
                       True, "ink", "the POST · ELASTIC key with an approximately-equal sign (an approximation, not an identity; the deeper dive #superposition has why)"),
        # ── the superposition's justification (the director wanted the
        # theoretical reasoning behind adding the elastic perturbation to
        # the viscous background written down somewhere on the
        # site): the Chapter 2 deeper dive's #superposition entry
        # (Ch2SuperpositionEqs.vue). The jump across the instant of drainage
        # of a Maxwell solid obeys Hooke's law and solves a linear
        # elastostatic problem whose solution is the paper's blister −
        # no-blister difference.
        "sup_maxwell": (r"\dot{\boldsymbol{\varepsilon}}' = \frac{\dot{\boldsymbol{\sigma}}'}{2G} + \frac{\boldsymbol{\sigma}'}{2\eta(\boldsymbol{\sigma})}",
                        True, "ink", "Maxwell viscoelastic solid (Glen's dashpot), deviatoric parts"),
        "sup_int": (r"\int_{0^-}^{0^+}\!\dot{\boldsymbol{\varepsilon}}'\,dt = \frac{1}{2G}\int_{0^-}^{0^+}\!\dot{\boldsymbol{\sigma}}'\,dt + \int_{0^-}^{0^+}\!\frac{\boldsymbol{\sigma}'}{2\eta(\boldsymbol{\sigma})}\,dt",
                     True, "ink", "the Maxwell law integrated over the load change (the drainage), 0^- to 0^+"),
        "sup_bound": (r"\Big\|\int_{0^-}^{0^+}\!\frac{\boldsymbol{\sigma}'}{2\eta(\boldsymbol{\sigma})}\,dt\,\Big\| \le \frac{\max_t\|\boldsymbol{\sigma}'\|}{2\min_t\eta}\;\delta t \;\longrightarrow\; 0 \quad (\delta t = 0^+ - 0^- \to 0)",
                     True, "ink", "the dashpot term is bounded, so its integral vanishes with the interval"),
        "sup_jump": (r"\big[\boldsymbol{\varepsilon}'\big] = \frac{\big[\boldsymbol{\sigma}'\big]}{2G}, \qquad [\,\cdot\,] \equiv (\cdot)\big|_{0^+} - (\cdot)\big|_{0^-}",
                     True, "ink", "integrated across the instant of drainage: the jump obeys Hooke's law"),
        "sup_bvp_v2": (r"\nabla\!\cdot\![\boldsymbol{\sigma}] = \mathbf{0}, \quad [\boldsymbol{\sigma}]\,\mathbf{n} = \mathbf{0}\ \text{(surface)}, \quad [\mathbf{u}] = \mathbf{0}\ \text{(bed, outside the footprint)}, \quad [\mathbf{t}] = -P_w\rho g H\,\mathbf{n} - \mathbf{t}^{V}_{\mathrm{pre}}\ \text{(footprint)}",
                    True, "ink", "the jump's elastostatic problem; on the footprint the water's pressure replaces the viscous pre-drainage traction"),
        "sup_dsig_v2": (r"\Delta\boldsymbol{\sigma}^{E} \equiv \boldsymbol{\sigma}^{E}_{\mathrm{blister}} - \boldsymbol{\sigma}^{E}_{\mathrm{ref}} \;\Rightarrow\; [\boldsymbol{\sigma}] = \Delta\boldsymbol{\sigma}^{E} + \mathcal{E}\big[\mathbf{t}^{E}_{\mathrm{ref}} - \mathbf{t}^{V}_{\mathrm{pre}}\big]_{\mathrm{footprint}}",
                     True, "ink", "the paper's difference releases the elastic reference's footprint traction, not the viscous one: the correction is the elastic response to the mismatch"),
        "sup_post_v2": (r"\boldsymbol{\sigma}(0^+) = \boldsymbol{\sigma}^{V}_{\mathrm{pre}} + [\boldsymbol{\sigma}] \approx \boldsymbol{\sigma}^{V}_{\mathrm{pre}} + \Delta\boldsymbol{\sigma}^{E}, \qquad \sigma_{t1}^{\mathrm{post}} = \sigma_{t1}\!\left(\boldsymbol{\sigma}^{V}_{\mathrm{pre}} + \Delta\boldsymbol{\sigma}^{E}\right)",
                     True, "ink", "post-drainage state with the paper's Δσ^E standing in for the jump (exact on a slab): tensors added first, principals after"),
        "sup_limit": (r"t \gg \tau_M = \eta/G \ \Rightarrow\ \boldsymbol{\sigma} \to \boldsymbol{\sigma}^{V}_{\mathrm{post}}",
                      True, "ink", "long-time limit: the viscous with-patch state"),
        "sup_jump_v2": (r"\big[\boldsymbol{\varepsilon}'\big] = \frac{\big[\boldsymbol{\sigma}'\big]}{2G}, \quad \operatorname{tr}[\boldsymbol{\varepsilon}] = \frac{\operatorname{tr}[\boldsymbol{\sigma}]}{3K}, \qquad [\,\cdot\,] \equiv (\cdot)\big|_{0^+} - (\cdot)\big|_{0^-}",
                      True, "ink", "the jump obeys Hooke's law, deviatoric and volumetric parts (the paper's E, nu)"),
        "sup_bvp_v3": (r"\nabla\!\cdot\![\boldsymbol{\sigma}] = \mathbf{0}, \qquad [\boldsymbol{\sigma}]\,\mathbf{n} = \mathbf{0}\ \text{(surface)}, \qquad [\mathbf{t}] = -P_w\rho g H\,\mathbf{n}_b - \mathbf{t}^{V}_{\mathrm{pre}}\ \text{(footprint)}",
                      True, "ink", "the jump's elastostatic problem: equilibrium, the free surface, the footprint's load"),
        "sup_bvp_walls": (r"[\mathbf{u}] = \mathbf{0}\ \text{(bed outside the footprint; inflow and outflow walls)}, \qquad [\mathbf{u}]\cdot\hat{\mathbf{y}} = 0,\ \ [\mathbf{t}]_{\parallel} = \mathbf{0}\ \text{(lateral walls)}",
                      True, "ink", "the jump's remaining boundaries: nothing moves in zero time"),
        "sup_limit_v2": (r"t \gg \tau_M/n,\ \tau_r \quad (P_w \to 1,\ \ \tau_b = 0\ \text{on the footprint}) \ \Rightarrow\ \boldsymbol{\sigma} \to \boldsymbol{\sigma}^{V}_{\mathrm{post}}",
                      True, "ink", "long-time limit: the viscous with-patch state, once the blister has drained to overburden and the footprint stays lubricated"),
        **(impl_lake_eqs() if with_impl else {}),
    }


def main():
    if not Path(bte.TEXBIN, "latex").exists():
        raise SystemExit(f"no latex at {bte.TEXBIN}")
    # `--only a,b` compiles just those labels and merges them into the
    # committed ch2Eqs.ts (every other entry untouched) — for ADDING
    # labels: R2 objects are immutable, so an existing name is never
    # re-uploaded, and the impl JSON need not be on disk.
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    with tempfile.TemporaryDirectory() as td:
        wd = Path(td)
        for name, (tex, display, color, src) in eqs(with_impl=only is None).items():
            if only is not None and name not in only:
                continue
            svg, dims = bte.compile_one(bte.math(tex, display), None, color, wd, name)
            svg, W, H, base = bte.set_box(svg, dims["w"], dims["h"], dims["d"])
            (OUT / f"{name}.svg").write_text(svg)
            manifest[name] = dict(w=W, h=H, base=base, src=src)
            print(f"  {name:14s} {W:7.2f} x {H:6.2f} bp   [{src}]")
    if only is not None:
        merge_ts(manifest)
        return
    lines = [
        "// GENERATED by cinematic/scene_ch02/build_results_eqs.py — do not edit.",
        "// LaTeX-compiled (Computer Modern) Ch.2 results labels, served from",
        "// R2 ch02/eq/<name>.svg. Sizes in bp: w × h = the whole image (TeX",
        "// box + pad), base = image top → baseline.",
        "export interface Ch2EqBox { w: number; h: number; base: number }",
        "export const CH2_EQ = {",
    ]
    for name, e in manifest.items():
        lines.append(f"  {name}: {{ w: {e['w']:.3f}, h: {e['h']:.3f}, base: {e['base']:.3f} }}, // {e['src']}")
    lines.append("} as const satisfies Record<string, Ch2EqBox>")
    lines.append("export type Ch2EqName = keyof typeof CH2_EQ")
    TS_OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {len(manifest)} entries -> {TS_OUT.relative_to(ROOT)}")


def merge_ts(manifest: dict) -> None:
    """Add/replace `manifest`'s entries in the committed ch2Eqs.ts, each
    right after its base label's line (ax_post_t1_bold after ax_post_t1)."""
    lines = TS_OUT.read_text().splitlines()
    for name, e in manifest.items():
        row = f"  {name}: {{ w: {e['w']:.3f}, h: {e['h']:.3f}, base: {e['base']:.3f} }}, // {e['src']}"
        lines = [ln for ln in lines if not ln.startswith(f"  {name}: ")]
        base = name.removesuffix("_bold")
        at = next((i for i, ln in enumerate(lines) if ln.startswith(f"  {base}: ")), None)
        if at is None:
            at = next(i for i, ln in enumerate(lines) if ln.startswith("} as const")) - 1
        lines.insert(at + 1, row)
    TS_OUT.write_text("\n".join(lines) + "\n")
    print(f"merged {len(manifest)} entries -> {TS_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
