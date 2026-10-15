"""
Build the Ch.1 math-mode assets from the JOG paper's NEWTONIAN (n=1)
Elmer/Ice ensemble. The director chose to show every animation in
this chapter with the n=1 results — for n=1 the boundary-layer equation
is exact (independent of delta), so the collapse is tight by
construction.

Hero run: newt_400km h=1000 m, alpha=0.5 deg, gamma=0.1, ell=10 km
(n=1, A=1/(2*1e14) Pa^-1 s^-1 -> B=2e14 Pa s, figure4 notebook verbatim).

Outputs (cinematic/data/, then upload to R2 ch01/):
  ch01_tau_paint_n1.png   slab paint: tau_xx(x,z) raster, +/-50 km
                          around patch center, RdBu_r +/-250 kPa,
                          bed at the BOTTOM row (same spec as the old
                          glen paint the slab shader samples).
  ch01_field2d_n1.png     math-mode field raster: +/-40 km, 1600x400.
  ch01_theory_n1.json     everything TheoryPanel v2 animates:
                          hero scales, depth-average sweep stack
                          (partial averages bed->surface), hero DA
                          profile, dimensional analytic segments
                          (eqs 12 + 46), n=1 ensemble profiles
                          (h < [x] < ell), fig-4c/d loglog points +
                          kappa medians, n=1 master curves.
  eq/eqn1_*.svg           mathtext (Computer Modern) equation SVGs —
                          SUPERSEDED: the site now draws
                          every Ch.1 equation + math label from real
                          LaTeX (build_theory_eqs.py → R2 ch01/eq2/,
                          build_acl_eqs.py for the ACL pair); ch01/eq/
                          is no longer referenced.
  ch01_theory_n1_qa.png   QA figure.

Inputs (local copies only — bash cinematic/fetch_sources.sh):
  cinematic/source_data/results/newt_400km/*.vtu  (m1p000000 = paper n=1 runs)
  cinematic/source_data/manuscript_jog/main.tex   (equation ground truth)

Run:  python -u cinematic/scene_ch01/build_theory_n1.py
Then: rclone copy ... (see bottom of main()).
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared import SOURCE_DATA, require_source  # noqa: E402

sys.stdout.reconfigure(line_buffering=True)

RESULTS = SOURCE_DATA / "results" / "newt_400km"

# ── Physics (figure4_dastress.ipynb verbatim, Newtonian column) ───────
RHO, G = 917.0, 9.81
N_FLOW = 1
ETA = 1e14                      # dynamic viscosity [Pa s]
A_NEWT = 1.0 / (2.0 * ETA)      # rate factor [Pa^-1 s^-1] = 5e-15
M_STR = "1p000000"              # sliding exponent 1/n token in filenames
                                # (m0p500000 files are a side experiment
                                # NOT in the paper's 96-run n=1 ensemble)

H_VALS = [300, 1000, 2000, 3000]
ALPHA_VALS = [0.1, 0.5, 1.0]
GAMMA_VALS = [0.1, 0.5]
ELL_VALS = [2500, 5000, 10000, 25000]
DELTA_MAX_PROFILES = 0.3        # paper fig-4a display filter

HERO = dict(h=1000, alpha_deg=0.5, gamma=0.1, ell=10000)

# ── Styling / extents ─────────────────────────────────────────────────
VMAX_KPA = 250.0
PAINT_HALF_KM = 50.0            # slab paint window (matches shader spec)
FIELD_HALF_KM = 40.0            # math-mode field window
PAINT_W, PAINT_H = 1600, 256
FIELD_W, FIELD_H = 1600, 400
SWEEP_NX, SWEEP_NZ = 240, 80    # sweep-stack raster
SWEEP_LEVELS = 41               # partial-average levels (bed -> surface)
XC = 200e3                      # patch center in domain coords

OUT = Path(__file__).resolve().parents[1] / "data"
OUT.mkdir(exist_ok=True)
EQ_DIR = OUT / "eq"
EQ_DIR.mkdir(exist_ok=True)


def vtu_path(h, alpha_deg, gamma, ell):
    a = f"{alpha_deg:.1f}".replace(".", "p")
    g = f"{gamma:.1f}".replace(".", "p")
    return RESULTS / f"h{int(h)}_a{a}_m{M_STR}_gamma{g}_ell{int(ell)}_t0001.vtu"


def compute_scales(h, alpha_deg, gamma, ell):
    """([x] m, [tau] kPa, delta) — depth-averaged C, figure4 verbatim."""
    alpha = np.radians(alpha_deg)
    n, A = N_FLOW, A_NEWT
    m = 1.0 / n
    B = A ** (-1.0 / n)
    C_b = gamma**m * (RHO * G * alpha) ** (1 - m * n) * A ** (-m) * h ** (1 - m - m * n)
    ub_over_u = 1.0 / (1.0 + (2 * A / (n + 2)) * h * C_b**n)
    C = C_b * ub_over_u**m
    x_bl = (2 * B * h / C) ** (n / (n + 1))
    tau = RHO * G * alpha * ell / 4 / 1e3
    return x_bl, tau, x_bl / ell


def raster(mesh, x_lo, x_hi, nx, nz, h):
    """griddata tau_xx [kPa] onto a regular (x, z) grid over the ice."""
    from scipy.interpolate import griddata

    pts = mesh.points[:, :2]
    tau = np.asarray(mesh.point_data["stress 1"]) * 1e3
    xs = np.linspace(x_lo, x_hi, nx)
    zs = np.linspace(0, h, nz)
    gx, gz = np.meshgrid(xs, zs)
    grid = griddata(pts, tau, (gx, gz), method="linear")
    hole = ~np.isfinite(grid)
    if hole.any():
        grid[hole] = griddata(pts, tau, (gx[hole], gz[hole]), method="nearest")
    return xs, zs, grid  # grid[z, x], z ascending (bed -> surface)


def depth_avg(mesh, h, nx=1000, nz=80):
    xs, _, grid = raster(mesh, 0, 400e3, nx, nz, h)
    return (xs - XC) / 1e3, np.nanmean(grid, axis=0)  # x centered [km]


def adaptive_profile(x_km, tau_kpa, ell_m, xscale_m, half_km=62.0):
    """Resample a DA profile onto an x-set that is DENSE around the two
    patch edges (where the exponential boundary layers live) and coarse
    in the far field. A uniform-1-km sampling puts only ~2 points per
    decay length on the small-[x] runs, which renders as visible
    polyline kinks — especially after the nondimensional stretch, where
    the director flagged the curves as looking sharp. Points per run: ~320."""
    half_ell_km = ell_m / 2 / 1e3
    dense_span_km = max(6 * xscale_m, ell_m) / 1e3
    dense_step_km = max(xscale_m / 12, 100) / 1e3
    xs = set(np.round(np.arange(-half_km, half_km + 1e-9, 1.0), 3))
    for edge in (-half_ell_km, half_ell_km):
        lo = max(-half_km, edge - dense_span_km)
        hi = min(half_km, edge + dense_span_km)
        xs.update(np.round(np.arange(lo, hi + 1e-9, dense_step_km), 3))
    # Patch interior at ell/40 steps so the linear ramp + corners are crisp.
    xs.update(np.round(np.arange(-half_ell_km, half_ell_km + 1e-9,
                                 max(ell_m / 40, 100) / 1e3), 3))
    xq = np.array(sorted(xs))
    tq = np.interp(xq, x_km, tau_kpa)
    return xq, tq


def measure_dl_m(x_km, tau_kpa, ell_m):
    """Decay length [m]: distance upstream from the patch onset over
    which the perturbed stress stays above max|tau|/e (paper metric)."""
    onset_km = -ell_m / 2 / 1e3
    peak = np.nanmax(tau_kpa)
    thr = peak / np.e
    above = np.where((tau_kpa >= thr) & (x_km <= onset_km + 0.5))[0]
    if len(above) == 0:
        return None
    x_first = x_km[above[0]]
    return max(0.0, (onset_km - x_first) * 1e3)


def field_png(grid, path, cmap, w, h_px):
    """Write a tau raster (grid[z, x], bed at row 0) as a PNG with the
    BED AT THE BOTTOM row of the image."""
    from matplotlib import cm
    from PIL import Image

    norm = np.clip(grid / VMAX_KPA, -1, 1) * 0.5 + 0.5
    rgba = cm.get_cmap(cmap)(norm)
    img = (np.flipud(rgba) * 255).astype(np.uint8)
    Image.fromarray(img).save(path, optimize=True)
    print(f"wrote {path.name} ({w}x{h_px})")
    return img


def write_equations(plt):
    """Math-mode equation SVGs (mathtext Computer Modern, warm white on
    transparent). Numbering follows the JOG manuscript: eq 7 = SSA in
    velocity form, eq 12 = linear patch profile, eq 46 = upstream BL
    exponential (here in the DIMENSIONAL form the director asked for)."""
    plt.rcParams.update({"text.usetex": False, "mathtext.fontset": "cm"})
    EQS = {
        # Stage 0 — incompressible Stokes (what Elmer/Ice actually solves)
        "eqn1_stokes": r"$\nabla \cdot \boldsymbol{\sigma} + \rho\, \mathbf{g} = \mathbf{0}\ , \qquad \nabla \cdot \mathbf{u} = 0$",
        # Stage 2 — depth-average definition (the sweep animation)
        "eqn1_depthavg": r"$\bar{\tau}_{xx}(x)\ =\ \frac{1}{h}\int_0^{h} \tau_{xx}(x,z)\, dz$",
        # Stage 3 — manuscript eq (7): SSA in velocity form
        "eqn1_ssa07": r"$2Bh\left(|u_x|^{\frac{1}{n}-1}u_x\right)_x\ -\ C|u|^{\frac{1}{n}-1}u\ +\ \rho g h\,\alpha\ =\ 0$",
        # Stage 4 — manuscript eq (12): linear profile across the patch
        "eqn1_patch12": r"$\tau_{xx}(x)\ =\ \frac{\rho g \alpha \ell}{4}\left(1 - \frac{2x}{\ell}\right)$",
        # Stage 5 — manuscript eq (46), dimensionalized (x from patch onset)
        "eqn1_bl46": r"$\tau_{xx}(x)\ =\ \frac{\rho g \alpha \ell}{4}\,\exp\!\left(n^{-\frac{1}{n+1}}\,\frac{x}{[x]}\right),\ \ \ x \leq 0$",
        # Stage 7 — scales + nondimensionalization + master curve
        "eqn1_scales": r"$[\tau_{xx}]\ \equiv\ \frac{\rho g \alpha \ell}{4}\ , \qquad [x]\ \equiv\ \left(\frac{2Bh}{C}\right)^{\frac{n}{n+1}}$",
        "eqn1_nondim": r"$\tilde{x} \equiv x\,/\,[x]\ , \qquad \tilde{\tau}_{xx} \equiv \tau_{xx}\,/\,[\tau_{xx}]$",
        "eqn1_master": r"$\tilde{\tau}_{xx}(\tilde{x})\ =\ \exp\!\left(n^{-\frac{1}{n+1}}\,\tilde{x}\right)$",
        # ACL stage — manuscript eq (48) with [x] spelled out so h, alpha,
        # ell, tau_val are all VISIBLE glyphs (the site pulse-highlights them),
        # plus the max-stress definition that comes up alongside it.
        "eqn1_acl48": r"$\mathrm{ACL}\ =\ \frac{(2Bh/C)^{\frac{n}{n+1}}}{n^{-\frac{1}{n+1}}}\;\ln\!\left(\frac{\rho g \alpha \ell/4}{\tau_{val}}\right)$",
        "eqn1_taumax": r"$\max\,\tau_{xx}\ =\ \frac{\rho g \alpha \ell}{4}$",
        # Schematic labels (fig-1-style overlay on the field). Talk-level
        # notation: just C (the C_b vs C distinction stays in the paper).
        "eqn1_taud": r"$\tau_d = \rho g h \alpha$",
        "eqn1_c0": r"$C = 0$",
        "eqn1_cpos": r"$C > 0$",
        "eqn1_lbl_h": r"$h$",
        "eqn1_lbl_ell": r"$\ell$",
        "eqn1_lbl_alpha": r"$\alpha$",
    }
    # Dark-ink variants for labels that sit ON the white field raster
    # (the schematic overlay) — warm white would vanish there.
    DARK = {"eqn1d_taud", "eqn1d_c0", "eqn1d_cpos"}
    EQS["eqn1d_taud"] = EQS["eqn1_taud"]
    EQS["eqn1d_c0"] = EQS["eqn1_c0"]
    EQS["eqn1d_cpos"] = EQS["eqn1_cpos"]
    # The CSS-mask gold overlay looked poor on screen (the director's note):
    # re-ink the ACL equation's tunable parameters — h, α, ℓ, τ_val —
    # as REAL gold glyphs in the SVG source. Matplotlib's SVG places
    # each glyph as a <use href="#font-codepoint">; a style attribute
    # on the <use> overrides the parent <g>'s warm-white fill. Target
    # ids verified against the generated file (BaKoMa cmmi10 charmap):
    # 68=h · ae=α · 60=ℓ · bf=τ · 76/61/6c = the "val" subscript.
    GOLD = "#f5c75e"
    GOLD_GLYPHS = {
        "eqn1_acl48": {"Cmmi10-68", "Cmmi10-ae", "Cmmi10-60",
                       "Cmmi10-bf", "Cmmi10-76", "Cmmi10-61", "Cmmi10-6c"},
    }

    import re as _re

    for name, tex in EQS.items():
        fig = plt.figure()
        color = "#4a3110" if name in DARK else "#f5f0e6"
        t = fig.text(0, 0, tex, fontsize=24, color=color)
        fig.canvas.draw()
        bb = t.get_window_extent()
        fig.set_size_inches(bb.width / fig.dpi + 0.1, bb.height / fig.dpi + 0.1)
        out_svg = EQ_DIR / f"{name}.svg"
        fig.savefig(out_svg, transparent=True, bbox_inches="tight", pad_inches=0.04)
        plt.close(fig)
        if name in GOLD_GLYPHS:
            targets = GOLD_GLYPHS[name]
            svg = out_svg.read_text()

            def _gild(m: "_re.Match[str]") -> str:
                gid = m.group(1)
                if gid in targets:
                    return m.group(0).replace(
                        "<use ", f'<use style="fill:{GOLD}" ', 1)
                return m.group(0)

            svg2 = _re.sub(r'<use xlink:href="#([A-Za-z0-9-]+)"[^/]*/>', _gild, svg)
            n_gold = svg2.count(f'style="fill:{GOLD}"')
            out_svg.write_text(svg2)
            print(f"  gilded {n_gold} glyphs in {name}.svg")
        print(f"wrote eq/{name}.svg")


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pyvista as pv

    # ── Hero rasters ──────────────────────────────────────────────────
    hero_path = require_source(vtu_path(**HERO))
    print(f"hero: {hero_path.name}")
    mesh = pv.read(str(hero_path))
    h = HERO["h"]

    _, _, paint_grid = raster(
        mesh, XC - PAINT_HALF_KM * 1e3, XC + PAINT_HALF_KM * 1e3, PAINT_W, PAINT_H, h
    )
    paint_img = field_png(paint_grid, OUT / "ch01_tau_paint_n1.png", "RdBu_r", PAINT_W, PAINT_H)

    _, _, fgrid = raster(
        mesh, XC - FIELD_HALF_KM * 1e3, XC + FIELD_HALF_KM * 1e3, FIELD_W, FIELD_H, h
    )
    field_img = field_png(fgrid, OUT / "ch01_field2d_n1.png", "RdBu_r", FIELD_W, FIELD_H)

    # ── Depth-average sweep stack (partial means, bed -> level z) ─────
    sx, szs, sgrid = raster(
        mesh, XC - FIELD_HALF_KM * 1e3, XC + FIELD_HALF_KM * 1e3, SWEEP_NX, SWEEP_NZ, h
    )
    cum = np.cumsum(sgrid, axis=0) / np.arange(1, SWEEP_NZ + 1)[:, None]
    lvl_idx = np.linspace(0, SWEEP_NZ - 1, SWEEP_LEVELS).round().astype(int)
    sweep_levels = [round(float(szs[i]) / h, 4) for i in lvl_idx]
    sweep_curves = [[round(float(v), 2) for v in cum[i]] for i in lvl_idx]
    sweep_x_km = [round(float(v - XC) / 1e3, 3) for v in sx]

    # ── Hero depth-averaged profile + scales ──────────────────────────
    hx_raw, htau_raw = depth_avg(mesh, h, nx=2400)
    hxbl, htau_scale, hdelta = compute_scales(**HERO)
    hx, htau = adaptive_profile(hx_raw, htau_raw, HERO["ell"], hxbl)
    hero_max = float(np.nanmax(np.abs(htau)))
    print(
        f"hero scales: [x]={hxbl:.0f} m, [tau]={htau_scale:.1f} kPa, "
        f"delta={hdelta:.3f}, max|tau_da|={hero_max:.1f} kPa "
        f"(kappa_hero={hero_max / htau_scale:.3f})"
    )

    # ── Dimensional analytic overlays (eqs 12 + 46/47, n=1) ──────────
    ell = HERO["ell"]
    lam = N_FLOW ** (-1.0 / (N_FLOW + 1))  # = 1 for n=1
    half_km = ell / 2 / 1e3
    ax_up = np.linspace(-FIELD_HALF_KM, -half_km, 240)
    ay_up = htau_scale * np.exp(((ax_up + half_km) * 1e3) / (lam * hxbl))
    ax_mid = np.linspace(-half_km, half_km, 80)
    ay_mid = htau_scale * (1 - 2 * (ax_mid + half_km) / (ell / 1e3))
    ax_dn = np.linspace(half_km, FIELD_HALF_KM, 240)
    ay_dn = -htau_scale * np.exp(-((ax_dn - half_km) * 1e3) / (lam * hxbl))

    # ── Ensemble: paper n=1 runs, h < [x] < ell ───────────────────────
    ensemble = []
    for hh in H_VALS:
        for a in ALPHA_VALS:
            for gmm in GAMMA_VALS:
                for el in ELL_VALS:
                    xbl, tsc, dlt = compute_scales(hh, a, gmm, el)
                    if not (hh < xbl < el):
                        continue
                    p = vtu_path(hh, a, gmm, el)
                    if not p.exists():
                        print(f"  MISSING {p.name}")
                        continue
                    m2 = pv.read(str(p))
                    ex, etau = depth_avg(m2, hh, nx=2400, nz=60)
                    max_tau = float(np.nanmax(np.abs(etau)))
                    dl = measure_dl_m(ex, etau, el)
                    axq, atq = adaptive_profile(ex, etau, el, xbl)
                    ensemble.append(
                        dict(
                            h=hh, alpha_deg=a, gamma=gmm, ell_m=el,
                            xscale_m=round(xbl, 1), tauscale_kpa=round(tsc, 2),
                            delta=round(dlt, 4),
                            max_tau_kpa=round(max_tau, 2),
                            dl_m=(round(dl, 1) if dl is not None else None),
                            x_km=[round(float(v), 3) for v in axq],
                            tau_kpa=[round(float(v), 3) for v in atq],
                        )
                    )
                    print(
                        f"  ensemble: {p.name}  [x]={xbl:.0f} m delta={dlt:.2f} "
                        f"max={max_tau:.0f} kPa DL={dl and f'{dl:.0f}'} m"
                    )
    n_prof = sum(1 for e in ensemble if e["delta"] <= DELTA_MAX_PROFILES)
    print(f"ensemble kept {len(ensemble)} runs ({n_prof} pass delta<={DELTA_MAX_PROFILES} for profiles)")

    # ── fig-4c/d kappa medians (self-check vs paper: 0.93, 1.04) ─────
    k_tau = float(np.median([e["max_tau_kpa"] / e["tauscale_kpa"] for e in ensemble]))
    dls = [(e["dl_m"], e["xscale_m"]) for e in ensemble if e["dl_m"]]
    k_dl = float(np.median([d / x for d, x in dls]))
    print(f"kappa medians: stress {k_tau:.3f} (paper 0.93), DL {k_dl:.3f} (paper 1.04)")

    # ── Master curves (n=1: lam=1) ────────────────────────────────────
    xh_up = np.linspace(-6, 0, 200)
    xh_dn = np.linspace(0, 6, 200)
    xh_patch = np.linspace(0, 1, 100)

    out = dict(
        n=N_FLOW,
        lam=round(lam, 6),
        vmax_kpa=VMAX_KPA,
        field=dict(half_km=FIELD_HALF_KM, h_m=h, png="ch01/field2d_n1.png"),
        paint=dict(half_km=PAINT_HALF_KM, png="ch01/tau_paint_n1.png"),
        hero=dict(
            h=h, alpha_deg=HERO["alpha_deg"], gamma=HERO["gamma"], ell_m=ell,
            xscale_m=round(hxbl, 1), tauscale_kpa=round(htau_scale, 2),
            delta=round(hdelta, 4), max_tau_kpa=round(hero_max, 2),
            x_km=[round(float(v), 2) for v in hx],
            tau_kpa=[round(float(v), 3) for v in htau],
        ),
        sweep=dict(x_km=sweep_x_km, levels=sweep_levels, curves=sweep_curves),
        analytic=dict(
            up_x_km=[round(float(v), 3) for v in ax_up],
            up_kpa=[round(float(v), 3) for v in ay_up],
            mid_x_km=[round(float(v), 3) for v in ax_mid],
            mid_kpa=[round(float(v), 3) for v in ay_mid],
            dn_x_km=[round(float(v), 3) for v in ax_dn],
            dn_kpa=[round(float(v), 3) for v in ay_dn],
        ),
        ensemble=ensemble,
        kappa=dict(tau=round(k_tau, 3), dl=round(k_dl, 3)),
        # ACL stage: tau_val threshold on the hero's dimensional plot.
        # For n=1 the prefactor n^{-1/(n+1)} = 1, so ACL = [x] ln(tau/30).
        acl=dict(
            tau_val_kpa=30.0,
            acl_m=round(float(hxbl * np.log(htau_scale / 30.0)), 1),
            onset_km=-ell / 2 / 1e3,
            x_cross_km=round(float(-ell / 2 / 1e3 - hxbl * np.log(htau_scale / 30.0) / 1e3), 3),
        ),
        master=dict(
            xhat_up=[round(float(v), 4) for v in xh_up],
            tauhat_up=[round(float(v), 5) for v in np.exp(xh_up / lam)],
            xfrac_patch=[round(float(v), 4) for v in xh_patch],
            tauhat_patch=[round(float(v), 5) for v in 1 - 2 * xh_patch],
            xhat_dn=[round(float(v), 4) for v in xh_dn],
            tauhat_dn=[round(float(v), 5) for v in -np.exp(-xh_dn / lam)],
        ),
    )
    jpath = OUT / "ch01_theory_n1.json"
    jpath.write_text(json.dumps(out))
    print(f"wrote {jpath.name} ({jpath.stat().st_size / 1e3:.0f} kB)")

    write_equations(plt)

    # ── QA figure ─────────────────────────────────────────────────────
    fig, axs = plt.subplots(2, 2, figsize=(15, 9))
    a1, a2, a3, a4 = axs.flat
    a1.imshow(field_img, extent=[-FIELD_HALF_KM, FIELD_HALF_KM, 0, h], aspect="auto", origin="upper")
    a1.set_title(f"field2d n=1 (tau_xx, +/-{VMAX_KPA:g} kPa)")
    for i in (0, 10, 20, 30, 40):
        a2.plot(sweep_x_km, sweep_curves[i], lw=0.9, label=f"z/h={sweep_levels[i]:.2f}")
    a2.plot(hx, htau, "k--", lw=1.2, label="full DA")
    a2.set_xlim(-FIELD_HALF_KM, FIELD_HALF_KM)
    a2.legend(fontsize=7)
    a2.set_title("sweep stack (partial depth-averages)")
    a3.plot(hx, htau, "k-", lw=1.4, label="hero DA")
    a3.plot(ax_up, ay_up, "-", color="goldenrod", lw=1.2, label="analytic")
    a3.plot(ax_mid, ay_mid, "-", color="goldenrod", lw=1.2)
    a3.plot(ax_dn, ay_dn, "-", color="goldenrod", lw=1.2)
    a3.set_xlim(-FIELD_HALF_KM, FIELD_HALF_KM)
    a3.axhline(0, color="0.7", lw=0.5)
    a3.legend()
    a3.set_title("hero DA vs analytic (eqs 12+46)")
    for e in ensemble:
        if e["delta"] > DELTA_MAX_PROFILES:
            continue
        xi_up = [(xx * 1e3 + e["ell_m"] / 2) / e["xscale_m"] for xx in e["x_km"]]
        nn = [t / e["tauscale_kpa"] for t in e["tau_kpa"]]
        a4.plot(xi_up, nn, lw=0.5, alpha=0.5)
    a4.plot(xh_up, np.exp(xh_up / lam), "k-", lw=1.5)
    a4.set_xlim(-6, 1)
    a4.set_ylim(-0.3, 1.3)
    a4.set_title("upstream collapse check (n=1)")
    fig.savefig(OUT / "ch01_theory_n1_qa.png", dpi=100, bbox_inches="tight")
    print("wrote ch01_theory_n1_qa.png")
    print(
        "\nupload:\n"
        "  rclone copyto cinematic/data/ch01_tau_paint_n1.png r2:<bucket>/ch01/tau_paint_n1.png --header-upload 'Cache-Control: public, max-age=31536000, immutable'\n"
        "  rclone copyto cinematic/data/ch01_field2d_n1.png r2:<bucket>/ch01/field2d_n1.png --header-upload 'Cache-Control: public, max-age=31536000, immutable'\n"
        "  rclone copyto cinematic/data/ch01_theory_n1.json r2:<bucket>/ch01/theory_n1.json --header-upload 'Cache-Control: public, max-age=31536000, immutable'\n"
        "  rclone copy cinematic/data/eq r2:<bucket>/ch01/eq --include 'eqn1*.svg' --header-upload 'Cache-Control: public, max-age=31536000, immutable'\n"
    )


if __name__ == "__main__":
    if "--eqs-only" in sys.argv:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        write_equations(plt)
    else:
        main()
