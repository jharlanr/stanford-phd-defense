"""
Ch.1 math-mode typography, compiled by REAL LaTeX (the director wanted
every math term set in a LaTeX-compiled font, even the terms on the
axes of charts). Replaces build_theory_n1.py's
matplotlib-mathtext equation SVGs (ch01/eq/) with Computer Modern set by
latex + dvisvgm (ch01/eq2/).

Every equation below is quoted from the JOG manuscript
(cinematic/source_data/manuscript_jog/main.tex; numbers = the compiled
PDF's): the source is noted on each line. Axis titles follow the paper's
figure labels (Fig. 4a: x - l/2 [km], tau-bar_xx [kPa]; Fig. B1a: u'
[m yr^-1]; Fig. 4b: x/[x], x/l, (x-l)/[x]).

Each entry is typeset as ONE TeX box; the SVG's viewBox is that box
(baseline at y = 0) plus a fixed pad, NOT the ink bbox — so the SSA's
split pieces (the membrane / basal-drag / gravity terms, each compiled
with the other two \\phantom'ed) register exactly on top of each other,
and the frontend can fade the basal-drag term out and slide the gravity
term left by a MEASURED width (TeX's own \\wd), closing the gap the way
the equation would really re-typeset.

Outputs:
  cinematic/data/eq2/<name>.svg          (upload to R2 ch01/eq2/)
  website/src/config/ch1Eqs.ts           (sizes in bp, committed)

Run:  python3 cinematic/scene_ch01/build_theory_eqs.py
Then: rclone copy cinematic/data/eq2 r2:<bucket>/ch01/eq2 --header-upload 'Cache-Control: public, max-age=31536000, immutable'
      (+ the same into website/.r2-cache/ch01/eq2 for dev)
Needs /Library/TeX/texbin (latex, dvisvgm).
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "cinematic" / "data" / "eq2"
TS_OUT = ROOT / "website" / "src" / "config" / "ch1Eqs.ts"
TEXBIN = "/Library/TeX/texbin"

PT_TO_BP = 72.0 / 72.27
PAD_BP = 1.5  # room for italic overhang beyond the TeX box

COLORS = {
    "ink": "F5F0E6",     # warm white — equations + axis titles on the dark board
    "dark": "4A3110",    # dark bronze — labels sitting ON the white field raster
    "bronze": "7A4A10",  # schematic h / alpha (matches the arrows' ink)
    "gold": "F5C75E",    # the slippery patch's gold (l, sweep label)
    "golddim": "E8B94A",  # legend column heads (drawn at 0.65 opacity)
    "violet": "B9A3EC",  # the u' velocity curve + its right-hand axis
}

# Reused sub-formulae (paper notation).
SSA_MEM = r"2Bh(|u_x|^{1/n-1}u_x)_x"
SSA_DRAG = r"C|u|^{1/n-1}u"
SSA_GRAV = r"\rho g h \alpha = 0"

# name: (tex, display?, color, source)
EQS = {
    # ── the talk's layout: the theory beats show the velocity PROFILE and the
    # stress–velocity relation, never the velocity solution; the τxx
    # solution in BOTH boundary layers; the collapse page's non-dimensional
    # solutions in the plot; the derivation itself in the deeper dive ──
    # eq (42) bottom row — the downstream boundary layer (dimensional).
    "tau_bl_dn": (r"\frac{\tau_{xx}(x)}{\rho g \alpha \ell/4} = -\exp\left(-n^{-\frac{1}{n+1}}\frac{x-\ell}{[x]}\right), \quad x \geq \ell",
                  True, "ink", "eq (42) bottom row (eq 41 mirrored downstream)"),
    # the director wanted rho g alpha l/4 on the right-hand side of the
    # upstream and downstream equations — eq (42)'s rows solved for τxx.
    "tau_bl_v2": (r"\tau_{xx}(x) = \frac{\rho g \alpha \ell}{4}\exp\left(n^{-\frac{1}{n+1}}\frac{x}{[x]}\right), \quad x \leq 0",
                  True, "ink", "eq (42) top row, solved for tau_xx"),
    "tau_bl_dn_v2": (r"\tau_{xx}(x) = -\frac{\rho g \alpha \ell}{4}\exp\left(-n^{-\frac{1}{n+1}}\frac{x-\ell}{[x]}\right), \quad x \geq \ell",
                     True, "ink", "eq (42) bottom row, solved for tau_xx"),
    # eq (42) with tildes, the patch and downstream rows (the collapse plot).
    "nd_mid": (r"\tilde{\tau}_{xx} = 1 - 2\,\frac{x}{\ell}", True, "ink", "eq (42) middle row, non-dimensional"),
    "nd_dn": (r"\tilde{\tau}_{xx}(\tilde{x}) = -\exp\left(-n^{-\frac{1}{n+1}}\,\tilde{x}\right)", True, "ink", "eq (42) bottom row, non-dimensional"),
    # ── the derivation (deeper dive #derivation, Ch1DerivationEqs.vue) ──
    "drv_patch_ode": (r"(2h\,\tau_{xx})_x = -\tau_d, \qquad C = 0,\quad 0 \leq x \leq \ell", True, "ink", "§2.2 inside the patch"),
    "drv_patch_bc": (r"\tau_{xx}(0) = -\tau_{xx}(\ell) = \frac{\tau_d\,\ell}{4h} = \frac{\rho g \alpha \ell}{4} \equiv [\tau_{xx}]", True, "ink", "eq (10) eqn:bc_patchedge + eq (13) eqn:tauscale"),
    "drv_patch_ux": (r"u'_x = \left|\frac{\tau_{xx}}{B}\right|^{n-1}\frac{\tau_{xx}}{B} = \left(\frac{\rho g \alpha \ell}{4B}\right)^{n}\left|1-2\frac{x}{\ell}\right|^{n-1}\left(1-2\frac{x}{\ell}\right)", True, "ink", "Appendix B, the patch velocity gradient"),
    "u_max": (r"u'_{\mathrm{max}} = [u]\left[\left(\frac{1}{n}\right)^{\frac{n}{n+1}} + \frac{\ell}{2(n+1)[x]}\right], \qquad [u] \equiv [x]\left(\frac{\rho g \alpha \ell}{4B}\right)^{n}", True, "ink", "eq (63) eqn:umax (dimensional) + eq (16) eqn:u_scale"),
    "drv_bl_balance": (r"2Bh\,(|u_x|^{1/n-1}u_x)_x \sim C|u|^{1/n-1}u \;\Rightarrow\; [x] = \left(\frac{2Bh}{C}\right)^{\frac{n}{n+1}}", True, "ink", "eq (14)-(15) eqn:x_scale"),
    "drv_bl_ode": (r"(|\tilde{u}'_{\tilde{x}}|^{1/n-1}\tilde{u}'_{\tilde{x}})_{\tilde{x}} = |\tilde{u}'|^{1/n-1}\tilde{u}', \qquad \tilde{u}' \to 0\ (\tilde{x} \to -\infty), \quad |\tilde{u}'_{\tilde{x}}|^{1/n-1}\tilde{u}'_{\tilde{x}} = 1\ (\tilde{x} = 0)", True, "ink", "eqs (27)-(29) eqn:goveq_nondim_leadingo + BCs"),
    "drv_bl_first": (r"y \equiv |\tilde{u}'_{\tilde{x}}|^{1/n-1}\tilde{u}'_{\tilde{x}} = \tilde{\tau}_{xx}: \qquad \frac{1}{n+1}\frac{d}{d\tilde{u}'}\,|y|^{n+1} = |\tilde{u}'|^{1/n-1}\tilde{u}' \;\Rightarrow\; |y|^{n+1} = n\,|\tilde{u}'|^{\frac{n+1}{n}}", True, "ink", "eqs (30)-(35), the first integral"),
    "drv_bl_u": (r"\tilde{u}'_{\tilde{x}} = n^{\frac{n}{n+1}}\,\tilde{u}' \;\Rightarrow\; \tilde{u}'(\tilde{x}) = \tilde{u}'_0\, \exp\!\left(n^{\frac{n}{n+1}}\tilde{x}\right), \qquad \tilde{u}'_0 = \left(\frac{1}{n}\right)^{\frac{n}{n+1}}", True, "ink", "eqs (36)-(38) eqn:velocity_bl"),
    "drv_bl_tau": (r"\tilde{\tau}_{xx} = y = n^{\frac{1}{n+1}}\,\tilde{u}'^{\,1/n} = \exp\!\left(n^{-\frac{1}{n+1}}\,\tilde{x}\right)", True, "ink", "eqs (39)-(40) eq:tauexp"),
    "drv_summary": (r"\frac{\tau_{xx}(x)}{\rho g \alpha \ell/4} = \begin{cases} \exp\left(n^{-\frac{1}{n+1}}\frac{x}{[x]}\right), & x \leq 0 \\[6pt] 1 - 2\dfrac{x}{\ell}, & 0 \leq x \leq \ell \\[6pt] -\exp\left(-n^{-\frac{1}{n+1}}\frac{x-\ell}{[x]}\right), & x \geq \ell \end{cases}", True, "ink", "eq (42) eqn:stresssoln"),
    "drv_velo_summary": (r"\frac{u'(x)}{u'_0} = \exp\!\left(n^{\frac{n}{n+1}}\frac{x}{[x]}\right)\ (x \leq 0), \qquad \frac{u' - u'_{\mathrm{max}}}{(\rho g \alpha \ell/4B)^{n}\,\ell} = -\frac{2^{n}}{n+1}\left|\frac{x}{\ell}-\frac{1}{2}\right|^{n+1}\ (0 \leq x \leq \ell), \qquad \frac{u'(x)}{u'_0} = \exp\!\left(-n^{\frac{n}{n+1}}\frac{x-\ell}{[x]}\right)\ (x \geq \ell)", True, "ink", "eq (66) eqn:velo_summary"),
    # ── the director's rule for the deeper-dive derivation: the connecting
    # text comes from the paper itself, never invented to join equations. The
    # derivation therefore follows §2.2 + Appendix B equation by equation, each
    # row glossed with the paper's own sentences (Ch1DerivationEqs.vue), so
    # the steps the combined rows above skipped get their own SVGs. Equation
    # numbers = the published PDF (JOG-2026-0047), checked against it.
    "drv_ssa": (r"\partial_x(2h\tau_{xx}) - \tau_b - \rho g h\,\partial_x s = 0", True, "ink", "eq (4), the SSA"),
    "drv_weertman": (r"\tau_b = C|u|^{1/n-1}u, \qquad C = C_b\left(\frac{u_b}{u}\right)^{1/n}", True, "ink", "eq (5) + eq (47) eqn:c_cb"),
    "drv_glen": (r"\tau_{xx} = B|\dot{\epsilon}_{xx}|^{1/n-1}\dot{\epsilon}_{xx}, \qquad \dot{\epsilon}_{xx} = \partial_x u", True, "ink", "eq (6), Glen's flow law in the 1d model"),
    "drv_cx": (r"C(x) = \begin{cases} 0, & x \in [0, \ell] \\[4pt] C > 0, & x \in (-\infty, 0] \cup [\ell, \infty) \end{cases}", True, "ink", "eq (8), the basal traction condition"),
    "drv_patch_linear": (r"\tau_{xx}(x) = \tau_{xx}(0) - \frac{\tau_d}{2h}\,x, \qquad \tau_d = \rho g h \alpha", True, "ink", "eq (10) eqn:linear_stress_patch"),
    "drv_outside": (r"(2h\tau_{xx})_x - C|u|^{1/n-1}u = -\tau_d, \qquad x \in (-\infty, 0] \cup [\ell, \infty)", True, "ink", "eq (14), outside the patch"),
    "drv_u_scale": (r"2Bh\,\frac{[u]^{1/n}}{[x]^{1/n}} = \frac{\tau_d\,\ell}{2} \;\Rightarrow\; [u] = [x]\left(\frac{\tau_d\,\ell}{4Bh}\right)^{n} = [x]\left(\frac{\rho g \alpha \ell}{4B}\right)^{n}", True, "ink", "eqs (17)-(18) eqn:u_scale"),
    "drv_nondim": (r"u = [u]\tilde{u}, \qquad x = [x]\tilde{x}, \qquad \tau_{xx} = [\tau_{xx}]\tilde{\tau}_{xx}", True, "ink", "eqs (19)-(21)"),
    "drv_nondim_ode": (r"(|\tilde{u}_{\tilde{x}}|^{1/n-1}\tilde{u}_{\tilde{x}})_{\tilde{x}} - |\tilde{u}|^{1/n-1}\tilde{u} = -2\delta, \qquad \delta \equiv \frac{[x]}{\ell} = \frac{(2Bh/C)^{n/(n+1)}}{\ell}", True, "ink", "eqs (22)-(23) eqn:goveq_with_delta + eqn:delta_define"),
    "drv_decomp": (r"\tilde{u}(\tilde{x}) = \varepsilon + \tilde{u}'(\tilde{x}), \qquad \varepsilon \equiv \frac{u_\infty}{[u]}", True, "ink", "eqs (24)-(25) eqn:epsilon"),
    "drv_subst": (r"(|\tilde{u}'_{\tilde{x}}|^{1/n-1}\tilde{u}'_{\tilde{x}})_{\tilde{x}} - |\varepsilon + \tilde{u}'|^{1/n-1}(\varepsilon + \tilde{u}') = -2\delta", True, "ink", "eq (26)"),
    "drv_bg": (r"|\varepsilon|^{1/n-1}\varepsilon = 2\delta", True, "ink", "eq (27) eqn:epsilon_to_delta"),
    "drv_exact": (r"(|\tilde{u}'_{\tilde{x}}|^{1/n-1}\tilde{u}'_{\tilde{x}})_{\tilde{x}} = |\varepsilon + \tilde{u}'|^{1/n-1}(\varepsilon + \tilde{u}') - |\varepsilon|^{1/n-1}\varepsilon", True, "ink", "eq (28) eqn:up_exact"),
    "drv_patch_xi": (r"\tilde{u}' = \frac{u'}{[u]}, \qquad \xi = \frac{x}{\ell} \;\Rightarrow\; \frac{du'}{d\xi} = \frac{\ell}{[x]}\,|1-2\xi|^{n-1}(1-2\xi) = \frac{1}{\delta}\,|1-2\xi|^{n-1}(1-2\xi)", True, "ink", "eqs (52), (55) eqn:dimless_uvars"),
    "drv_patch_int": (r"u'(\xi) = u'_0 + \frac{1}{\delta}\int_0^{\xi}|1-2\xi'|^{n-1}(1-2\xi')\,d\xi' = u'_0 + \frac{1}{2(n+1)\delta}\left[1 - |1-2\xi|^{n+1}\right]", True, "ink", "eqs (56), (62) eqn:patchcenter_eqn"),
    "drv_umax_nd": (r"u'_{\mathrm{max}} = u'_0 + \frac{1}{2(n+1)\delta} = \left(\frac{1}{n}\right)^{\frac{n}{n+1}} + \frac{1}{2(n+1)\delta}", True, "ink", "eq (63) eqn:umax"),
    # Glen's flow law as its own deeper-dive entry (the director noticed the
    # flow law appeared nowhere in the deeper-dive material):
    # eq (6) above + Table 1's n and B^-n.
    "glen_table": (r"n = 1 \text{ or } 3, \qquad B^{-n} = \begin{cases} 5.0 \times 10^{-15} & (n = 1) \\[2pt] 2.4 \times 10^{-24} & (n = 3) \end{cases}\ \mathrm{Pa^{-n}\,s^{-1}}", True, "ink", "Table 1, the flow-law rows"),
    # ── the reserved equation area ─────────────────────────────────────
    # eq (1): the incompressible Stokes system Elmer/Ice solves.
    "stokes": (r"\nabla \cdot \boldsymbol{\sigma} + \rho_i \mathbf{g} = \mathbf{0}, \qquad \nabla \cdot \mathbf{u} = 0",
               True, "ink", "eq (1)"),
    # eq (7) eqn:goveq_10 — the SSA in velocity form (split: see SPLITS).
    # eq (66) eqn:velo_summary, middle row — patch-interior velocity.
    "u_patch": (r"\frac{u' - u'_{\mathrm{max}}}{(\rho g \alpha \ell/4B)^n\,\ell} = -\frac{2^n}{n+1}\left|\frac{x}{\ell} - \frac{1}{2}\right|^{n+1}, \quad 0 \leq x \leq \ell",
                True, "ink", "eq (66) middle row = eq (65) eqn:vel_shape_dimensional"),
    # The constitutive relation as the paper writes it before eqs (15)
    # and (50): eq (6) with strain rate u_x.
    "tau_u": (r"\tau_{xx} = B|u_x|^{1/n-1}u_x",
              True, "ink", "constitutive relation, text before eqs (15) and (50); eq (6) with eps_xx = u_x"),
    # eq (12) eqn:linear_stress_patch_dimensionless — the patch solution.
    "tau_patch": (r"\tau_{xx} = \frac{\rho g \alpha \ell}{4}\left(1-2\frac{x}{\ell}\right)",
                  True, "ink", "eq (12)"),
    # eq (66) top row — boundary-layer velocity (upstream).
    "u_bl": (r"\frac{u'(x)}{\,u'_0} = \exp\!\left(n^{\frac{n}{n+1}}\,\frac{x}{[x]}\right), \quad x \leq 0",
             True, "ink", "eq (66) top row (eqs 39-40 dimensional)"),
    # eq (43) eqn:stresssoln, top row — boundary-layer stress (upstream).
    "tau_bl": (r"\frac{\tau_{xx}(x)}{\rho g \alpha \ell/4} = \exp\left(n^{-\frac{1}{n+1}}\frac{x}{[x]}\right), \quad x \leq 0",
               True, "ink", "eq (43) top row (eq 42 dimensional)"),
    # eqs (13) + (16), with the paper's own \equiv from the surface-stress
    # section ("[tau_xx] = rho g alpha l/4 and [x] = (2Bh/C)^(n/(n+1))").
    "scales": (r"[\tau_{xx}] \equiv \frac{\rho g \alpha \ell}{4}, \qquad [x] \equiv \left(\frac{2Bh}{C}\right)^{\frac{n}{n+1}}",
               True, "ink", "eqs (13), (16)"),
    # eq (42), tildes kept (the paper drops them after eq 28).
    "master": (r"\tilde{\tau}_{xx}(\tilde{x}) = \exp\left(n^{-\frac{1}{n+1}}\,\tilde{x}\right)",
               True, "ink", "eq (42) with tildes"),
    # ── stage-0 schematic: sliding laws UNDER the bed (dark board), the
    # h / alpha labels ON the white field (bronze), l in the patch gold ──
    # Weertman sliding as the paper writes it for Elmer/Ice (Appendix B,
    # text before eq 47: "the Elmer simulation uses tau_b = C_b u_b^{1/n}").
    "slide": (r"\tau_b = C_b u_b^{1/n}", False, "ink", "Appendix B text before eq (47); eq (2) for u_b > 0"),
    "slide0": (r"\tau_b = 0", False, "gold", "C_b = 0 on the patch (Fig. 1 caption)"),
    "lbl_h": (r"h", False, "bronze", "Fig. 1"),
    "lbl_alpha": (r"\alpha", False, "bronze", "Fig. 1"),
    "lbl_ell": (r"\ell", False, "gold", "Fig. 1"),
    # ── in-plot zone reminders (eq 8) ──────────────────────────────────
    "c0": (r"C = 0", False, "ink", "eq (8)"),
    "cpos": (r"C > 0", False, "ink", "eq (8)"),
    # ── axis titles (paper figure labels) ──────────────────────────────
    "ax_field_tau": (r"\tau_{xx}\ [\mathrm{kPa}]", False, "ink", "Fig. 2 colorbar"),
    "ax_tau": (r"\bar{\tau}_{xx}\ [\mathrm{kPa}]", False, "ink", "Fig. 4a"),
    "ax_x": (r"x - \ell/2\ [\mathrm{km}]", False, "ink", "Fig. 4a / B1a"),
    "ax_u": (r"u'\ [\mathrm{m\;yr^{-1}}]", False, "violet", "Fig. B1a"),
    "ax_nd_tau": (r"\bar{\tau}_{xx}/[\tau_{xx}]", False, "ink", "Fig. 4b with eq (13)"),
    "ax_nd_up": (r"x/[x]", False, "ink", "Fig. 4b"),
    "ax_nd_mid": (r"x/\ell", False, "ink", "Fig. 4b"),
    "ax_nd_dn": (r"(x-\ell)/[x]", False, "ink", "Fig. 4b"),
    # ── the TALK's coordinate (the director found it cleaner to centre the
    # talk's equations on the patch, with the equations modified
    # accordingly): the plot has always been drawn about the patch CENTRE
    # (Fig. 4a's axis is x - l/2), so the talk's equations are written with
    # x = 0 at the centre and the patch on |x| <= l/2 — the paper's eqs (10),
    # (42)-(43), (66) with x -> x + l/2. The deeper dive keeps the paper's
    # own forms (drv_*). New names = new R2 objects (immutable bucket).
    "tau_patch_c": (r"\tau_{xx} = -\frac{\rho g \alpha \ell}{4}\,\frac{2x}{\ell}, \quad |x| \leq \frac{\ell}{2}", True, "ink", "eq (43) middle row, centred on the patch"),
    # to save room, all three x-range conditions go: the patch row without |x| ≤ ℓ/2
    "tau_patch_v2_c": (r"\tau_{xx} = -\frac{\rho g \alpha \ell}{4}\,\frac{2x}{\ell}", True, "ink", "eq (43) middle row, centred on the patch, no x-range"),
    # likewise the boundary-layer rows lose their x \leq -\ell/2 and x \geq \ell/2 conditions
    "tau_bl_up_v3_c": (r"\tau_{xx}(x) = \frac{\rho g \alpha \ell}{4}\exp\left(n^{-\frac{1}{n+1}}\frac{x+\ell/2}{[x]}\right)", True, "ink", "eq (43) top row, centred on the patch, no x-range"),
    "tau_bl_dn_v3_c": (r"\tau_{xx}(x) = -\frac{\rho g \alpha \ell}{4}\exp\left(-n^{-\frac{1}{n+1}}\frac{x-\ell/2}{[x]}\right)", True, "ink", "eq (43) bottom row, centred on the patch, no x-range"),
    "nd_mid_c": (r"\tilde{\tau}_{xx} = -2\,\frac{x}{\ell}", True, "ink", "eq (43) middle row, non-dimensional, centred"),
    "ax_x_c": (r"x\ [\mathrm{km}]", False, "ink", "Fig. 4a, centred on the patch"),
    "ax_nd_up_c": (r"(x+\ell/2)/[x]", False, "ink", "Fig. 4b, centred on the patch"),
    "ax_nd_dn_c": (r"(x-\ell/2)/[x]", False, "ink", "Fig. 4b, centred on the patch"),
    "sweep_zh": (r"z/h =", False, "gold", "depth-average sweep level"),
    # ── log-log cards (Fig. 4c/d) ──────────────────────────────────────
    "ll_x_tau": (r"\rho g \alpha \ell/4\ [\mathrm{kPa}]", False, "ink", "Fig. 4c"),
    "ll_y_tau": (r"\max|\bar{\tau}_{xx}|\ [\mathrm{kPa}]", False, "ink", "Fig. 4c"),
    "ll_x_dl": (r"[x] = (2Bh/C)^{n/(n+1)}\ [\mathrm{m}]", False, "ink", "Fig. 4d"),
    "ll_y_dl": (r"\mathrm{DL}\ [\mathrm{m}]", False, "ink", "Fig. 4d"),
    "ll_kappa": (r"\kappa =", False, "ink", "Fig. 4c/d"),
    # ── ensemble legend (Fig. 4 legend) ────────────────────────────────
    "leg_h": (r"h\ [\mathrm{m}]", False, "golddim", "Fig. 4 legend"),
    "leg_alpha": (r"\alpha\ [^\circ]", False, "golddim", "Fig. 4 legend"),
    "leg_gamma": (r"\gamma", False, "golddim", "Fig. 4 legend"),
    "leg_n1": (r"n = 1", False, "gold", "Fig. 4 panel title"),
}

# Split equations: pieces compiled on ONE shared box. `meas` are prefix
# formulae whose TeX widths the frontend needs (term extents, gap).
SPLITS = {
    # eq (7) eqn:goveq_10 — the SSA; pieces = membrane / basal drag /
    # gravity. Prefix widths give each term's extent for the braces and
    # the exact slide that closes the gap when the drag term drops.
    "ssa": dict(
        pieces={
            "mem": (SSA_MEM, "{}", "{}"),
            "drag": ("{}", r"{}-" + SSA_DRAG, "{}"),
            "grav": ("{}", "{}", r"{}+" + SSA_GRAV),
        },
        full=SSA_MEM + " - " + SSA_DRAG + " + " + SSA_GRAV,
        meas={
            "memEnd": SSA_MEM,
            "dragStart": SSA_MEM + " - {}",
            "dragEnd": SSA_MEM + " - " + SSA_DRAG,
            "gravStart": SSA_MEM + " - " + SSA_DRAG + " + {}",
            "gravEnd": SSA_MEM + " - " + SSA_DRAG + r" + \rho g h \alpha",
        },
        color="ink",
        src="eq (7)",
    ),
}

PREAMBLE = r"""\documentclass[preview,border=0pt]{standalone}
\usepackage{amsmath,amssymb}
\usepackage{xcolor}
""" + "".join(f"\\definecolor{{{k}}}{{HTML}}{{{v}}}\n" for k, v in COLORS.items())


def run(cmd, cwd):
    env = dict(os.environ, PATH=f"{TEXBIN}:{os.environ.get('PATH', '')}")
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stdout.write(r.stdout[-3000:])
        sys.stdout.write(r.stderr[-3000:])
        raise SystemExit(f"failed: {' '.join(cmd)}")
    return r.stdout


def math(tex, display):
    return f"$\\displaystyle {tex}$" if display else f"${tex}$"


def compile_one(tex_body_box, meas, color, workdir, stem):
    """Typeset box 0 (the visible content) plus measurement boxes; returns
    (svg_text, dims dict in pt)."""
    lines = [PREAMBLE, r"\begin{document}"]
    lines.append(f"\\sbox0{{\\color{{{color}}}{tex_body_box}}}%")
    lines.append(r"\typeout{BOX:\the\wd0,\the\ht0,\the\dp0}%")
    for key, mtex in (meas or {}).items():
        lines.append(f"\\sbox2{{{mtex}}}\\typeout{{MEAS:{key}:\\the\\wd2}}%")
    lines.append(r"\usebox0%")
    lines.append(r"\end{document}")
    (workdir / f"{stem}.tex").write_text("\n".join(lines))
    run(["latex", "-interaction=nonstopmode", f"{stem}.tex"], workdir)
    log = (workdir / f"{stem}.log").read_text(errors="replace")
    m = re.search(r"BOX:([\d.]+)pt,([\d.]+)pt,([\d.]+)pt", log)
    dims = dict(w=float(m.group(1)), h=float(m.group(2)), d=float(m.group(3)))
    for mm in re.finditer(r"MEAS:(\w+):([\d.]+)pt", log):
        dims[mm.group(1)] = float(mm.group(2))
    run(["dvisvgm", "--no-fonts", "-o", f"{stem}.svg", f"{stem}.dvi"], workdir)
    svg = (workdir / f"{stem}.svg").read_text()
    return svg, dims


def set_box(svg, w_pt, h_pt, d_pt):
    """Replace dvisvgm's bbox with the TeX box (+PAD) — baseline at 0."""
    W = w_pt * PT_TO_BP + 2 * PAD_BP
    H = (h_pt + d_pt) * PT_TO_BP + 2 * PAD_BP
    y0 = -h_pt * PT_TO_BP - PAD_BP
    head = re.search(r"<svg [^>]*>", svg).group(0)
    new = re.sub(r"width='[^']*'", f"width='{W:.4f}pt'", head)
    new = re.sub(r"height='[^']*'", f"height='{H:.4f}pt'", new)
    new = re.sub(r"viewBox='[^']*'", f"viewBox='{-PAD_BP:.4f} {y0:.4f} {W:.4f} {H:.4f}'", new)
    return svg.replace(head, new, 1), W, H, (h_pt * PT_TO_BP + PAD_BP)


def main():
    if not Path(TEXBIN, "latex").exists():
        raise SystemExit(f"no latex at {TEXBIN}")
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    with tempfile.TemporaryDirectory() as td:
        wd = Path(td)
        for name, (tex, display, color, src) in EQS.items():
            svg, dims = compile_one(math(tex, display), None, color, wd, name)
            svg, W, H, base = set_box(svg, dims["w"], dims["h"], dims["d"])
            (OUT / f"{name}.svg").write_text(svg)
            manifest[name] = dict(w=W, h=H, base=base, src=src)
            print(f"  {name:12s} {W:7.2f} x {H:6.2f} bp   [{src}]")

        for name, spec in SPLITS.items():
            # Full box + prefix widths from the FULL equation.
            meas = {k: math(v, True) for k, v in spec["meas"].items()}
            full_raw, dims = compile_one(math(spec["full"], True), meas, spec["color"], wd, f"{name}_full")
            full_svg, W, H, base = set_box(full_raw, dims["w"], dims["h"], dims["d"])
            (OUT / f"{name}.svg").write_text(full_svg)
            entry = dict(w=W, h=H, base=base, src=spec["src"], cuts={})
            for k in spec["meas"]:
                entry["cuts"][k] = dims[k] * PT_TO_BP + PAD_BP  # from image left
            # Each piece: its own term visible, the other terms \phantom'ed
            # (same widths, same atom classes) — an identical box, so the
            # pieces register exactly on the full equation.
            keys = list(spec["pieces"].keys())
            for pk in keys:
                seq = []
                for j, qk in enumerate(keys):
                    vis = spec["pieces"][qk][j]
                    seq.append(vis if qk == pk else f"\\phantom{{{vis}}}")
                svg, pd = compile_one(math(" ".join(seq), True), None, spec["color"], wd, f"{name}_{pk}")
                if abs(pd["w"] - dims["w"]) > 0.01:
                    raise SystemExit(f"{name}_{pk}: box {pd['w']} != full {dims['w']}")
                svg, *_ = set_box(svg, dims["w"], dims["h"], dims["d"])
                (OUT / f"{name}_{pk}.svg").write_text(svg)
            manifest[name] = entry
            print(f"  {name:12s} {W:7.2f} x {H:6.2f} bp   cuts {entry['cuts']}   [{spec['src']}]")

    # TS manifest (committed): sizes in bp, image-left / image-top origin.
    lines = [
        "// GENERATED by cinematic/scene_ch01/build_theory_eqs.py — do not edit.",
        "// LaTeX-compiled (Computer Modern) Ch.1 equations + math labels,",
        "// served from R2 ch01/eq2/<name>.svg. Sizes in bp (1/72 in):",
        "// w × h is the whole image (TeX box + pad), base = image top →",
        "// baseline. cuts = x positions (from image left) of TeX-measured",
        "// prefix widths, for the split SSA's term extents and gap.",
        "export interface EqBox { w: number; h: number; base: number }",
        "export const CH1_EQ = {",
    ]
    for name, e in manifest.items():
        lines.append(f"  {name}: {{ w: {e['w']:.3f}, h: {e['h']:.3f}, base: {e['base']:.3f} }}, // {e['src']}")
    lines.append("} as const satisfies Record<string, EqBox>")
    lines.append("export type Ch1EqName = keyof typeof CH1_EQ")
    for name, e in manifest.items():
        if "cuts" in e:
            lines.append(f"/** {name}: TeX prefix widths [bp from image left] — term extents. */")
            lines.append(f"export const CH1_EQ_CUTS_{name.upper()} = {{ "
                         + ", ".join(f"{k}: {v:.3f}" for k, v in e["cuts"].items()) + " } as const")
    TS_OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {len(manifest)} entries -> {TS_OUT.relative_to(ROOT)}")
    print(f"svgs in {OUT.relative_to(ROOT)}: {len(list(OUT.glob('*.svg')))}")
    r2 = ROOT / "website" / ".r2-cache"
    print("\nupload:\n  rclone copy cinematic/data/eq2 r2:<bucket>/ch01/eq2 --header-upload 'Cache-Control: public, max-age=31536000, immutable'\n"
          f"  mirror: cp cinematic/data/eq2/*.svg {r2}/ch01/eq2/")


if __name__ == "__main__":
    main()
