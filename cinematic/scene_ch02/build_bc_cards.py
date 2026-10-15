"""Bake the Ch.2 boundary-condition CARDS.

The director's brief: the boundary-condition view needed the bed
boundary condition, which it lacked; each card should be clickable and
take the viewer to a head-on view of that boundary — the inflow arrows
appear, or the patch appears on the bed with the Weertman sliding law —
with the coefficients actually used (or the pressure values, for the
elastic simulations), and something tracing the arrow tips (or tails)
to show the profile.

Everything here is READ from the published run inputs, never invented:

  * the run .sif files (viscous `step1glen_patch/*_tsic_base.sif`,
    elastic `step2elastic/elastic_sif_template_*.sif` + its
    `runsims_localH.sh` sed table) and the BC user function
    `PROG/USF_TAVz.F90` (BC_SIA_Tsicopolis) — copied by
    cinematic/fetch_sources.sh into cinematic/source_data/pnas_sims/bc/;
  * the per-lake MODEL INPUT DEMs (BedMachine v5 on the 166 x 166,
    150 m Elmer grid, x = along flow, 0..24 750 m) — same folder;
  * the published netCDF filenames (viscous `csi<c_b>`, elastic
    `pw<P_w>` in `source_blister`) — the c_b actually run (lake 893's
    checked-in sif still says 5.5e6; the published run is 7.5e6, as SI
    Fig. S11 states);
  * PNAS SI Appendix section 4 (Eqs. 40-51) for the notation, and the
    SI figure captions S7-S20 for c_b / P_w (asserted equal below).

The model domain is the FULL 24.75 km Elmer tile (sif Lx = 24750); the
block the site shows is the 14.75 km ANALYSIS tile (netCDF border_m =
5000 cropped from every side). The boundary conditions live on the
outer 24.75 km walls — so this script also bakes those walls' surface
and bed elevations, for the ghost domain shell drawn in BC mode.

Outputs
  cinematic/data/ch02_bc2/*.svg          LaTeX (latex + dvisvgm) -> R2 ch02/bc2/
  website/src/config/ch2BcEqs.ts         SVG sizes (bp), generated
  website/src/config/ch2BcData.ts        per-lake values + walls + wall
                                         profiles, generated, with sources

Run:  cinematic/.venv/bin/python -u cinematic/scene_ch02/build_bc_cards.py
Then: rclone copy cinematic/data/ch02_bc2 r2:<bucket>/ch02/bc2 --header-upload 'Cache-Control: public, max-age=31536000, immutable'
      mkdir -p website/.r2-cache/ch02/bc2 && cp cinematic/data/ch02_bc2/*.svg website/.r2-cache/ch02/bc2/
"""

from __future__ import annotations

import glob
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "cinematic" / "source_data" / "pnas_sims"
BC_SRC = SRC / "bc"
OUT = ROOT / "cinematic" / "data" / "ch02_bc2"
TS_EQS = ROOT / "website" / "src" / "config" / "ch2BcEqs.ts"
TS_DATA = ROOT / "website" / "src" / "config" / "ch2BcData.ts"
TEXBIN = "/Library/TeX/texbin"

T4326_3413 = Transformer.from_crs("EPSG:4326", "EPSG:3413", always_xy=True)
T3413_4326 = Transformer.from_crs("EPSG:3413", "EPSG:4326", always_xy=True)

# old sim id -> Dunmire new id (new = old + 1523)
LAKES = [387, 428, 871, 888, 893, 988, 997]

# SI figure captions (Lake_pnas_SI.pdf, Figs. S7-S13 c_b; S14-S20 P_w) —
# asserted against the run filenames below, never used blindly.
SI_CB = {387: 5.4e6, 428: 6.5e6, 871: 8.5e6, 888: 8.5e6, 893: 7.5e6, 988: 8.6e6, 997: 6.7e6}
SI_PW = {387: 1.0378, 428: 1.0276, 871: 1.0164, 888: 1.0306, 893: 1.0309, 988: 1.0298, 997: 1.0257}

# ── shared physical constants, with their source ──────────────────────
YEAR_S = 365.25 * 24 * 60 * 60   # sif: $ yearinsec = 365.25*24*60*60
RHO_I = 917.0                    # sif Constants rhoi = 917.0; SI §4A
G = 9.81                         # sif Constants g = -9.81 (|g|)
N_GLEN = 3.0                     # sif $ n = 3.0; SI Eq. 39
M_SLIDE = 1.0 / 3.0              # sif $ m = 1.0/n; SI Eq. 42
A1SI, A2SI = 2.89165e-13, 2.42736e-02  # sif A1si/A2si [Pa^-3 s^-1] (Cuffey & Paterson 2010)
Q1, Q2 = 60.0e3, 115.0e3         # sif Q1/Q2 [J mol^-1]
E_PA = 3.077e9                   # nc filename youngmod3.077e3 [MPa]; SI §4B
NU = 0.3                         # elastic nc source *_nu0.3_*; SI §4B
U_B = 0.0                        # elastic nc source *_u0p0_*; SI Eq. 50
R_PATCH = 2500.0                 # sif/template R = 2500 [m]; SI §4
LX = 24750.0                     # sif Lx = 24750.0 [m] (166 nodes x 150 m)
NGRID = 166                      # sif Grid2DInterpolator Nx = Ny = 166
TILE_HALF = 7375.0               # netCDF analysis tile half-width (border_m 5000)

# Wall-profile sampling: stations along each x-wall and heights.
STATION_FRAC = [0.1, 0.3, 0.5, 0.7, 0.9]       # of L_y
ZETA = np.linspace(0.0, 1.0, 25)                # z'/H for the trace
WALL_STRIDE = 3                                 # wall elevation sampling (450 m)
GRID_IDX = [int(round(v)) for v in np.linspace(0, NGRID - 1, 23)]  # coarse full-domain grid (~1.1 km)


# ───────────────────────── run inputs ──────────────────────────────────

def sif_value(text: str, name: str) -> float:
    m = re.search(rf"^\$\s*{name}\s*=\s*([-\d.eE+]+)", text, re.M)
    if not m:
        raise SystemExit(f"sif: no ${name}")
    return float(m.group(1))


def lake_inputs(n: int) -> dict:
    vsif = (BC_SRC / f"2019cw{n}_glen_d25km_r2500m_tsic_base.sif").read_text()
    alpha = sif_value(vsif, "alphadeg")
    hp = sif_value(vsif, "Hp")
    tco = [sif_value(vsif, f"c{i}") for i in range(5)]
    cb_sif = sif_value(vsif, "Csi")
    # The c_b actually RUN = the published viscous netCDF's filename token.
    vnc = sorted(glob.glob(str(SRC / f"2019cw{n}_d25km_r2500m_csi*_tsic_viscous.nc")))
    if len(vnc) != 1:
        raise SystemExit(f"2019cw{n}: expected one viscous nc, got {vnc}")
    cb = float(re.search(r"_csi([\d.eE+]+)_tsic", vnc[0]).group(1))
    # P_w actually RUN = the published blister input DEM's pw token (the
    # elastic nc's source_blister carries the same token).
    tok = f"{alpha:.3f}"
    bpb = sorted(glob.glob(str(BC_SRC / f"2019cw{n}_bedplusblister_d25km_h{int(hp)}_a{tok}_timoblister_pw*_r2500m.dat")))
    if len(bpb) != 1:
        raise SystemExit(f"2019cw{n}: expected one published blister DEM, got {bpb}")
    pw = float(re.search(r"_pw(\d+p\d+)_", bpb[0]).group(1).replace("p", "."))
    assert abs(cb - SI_CB[n]) < 1, (n, cb, SI_CB[n])
    assert abs(pw - SI_PW[n]) < 1e-6, (n, pw, SI_PW[n])
    # elastic template E is the stale 9 GPa; the published runs are 3.077
    etxt = (BC_SRC / f"elastic_sif_template_2019cw{n}.sif").read_text()
    assert "u_elastic_local" in etxt and "Normal-Tangential Displacement" in etxt
    return dict(
        n=n, id=f"CW2019_{n + 1523}", alpha=alpha, hp=hp, tco=tco, cb=cb, cb_sif=cb_sif, pw=pw,
        surf=BC_SRC / f"2019cw{n}_surface_d25km_h{int(hp)}_a{tok}.dat",
        bed=BC_SRC / f"2019cw{n}_bed_d25km_h{int(hp)}_a{tok}.dat",
        bpb=Path(bpb[0]),
    )


def load_dat(path: Path) -> np.ndarray:
    d = np.loadtxt(path)
    assert d.shape == (NGRID * NGRID, 3), path
    z = d[:, 2].reshape(NGRID, NGRID)       # [iy, ix], x fastest
    assert abs(d[1, 0] - 150.0) < 1e-6 and abs(d[NGRID, 1] - 150.0) < 1e-6
    return z


# ───────────────────── BC functions, as RUN ────────────────────────────

def u_sia(H: float, zp: np.ndarray, L: dict) -> np.ndarray:
    """PROG/USF_TAVz.F90 BC_SIA_Tsicopolis, line for line [m/yr]:
    T(z'/H) = SICOPOLIS quartic; A(T) two-regime Arrhenius around -10 C;
    u = 2A/(n+1) (rho g |alpha|)^n [H^(n+1) - (H-z')^(n+1)]
        + (rho g H |alpha| / Csi)^(1/m)            (SI Eq. 44)."""
    zt = zp / H
    c = L["tco"]
    T = c[0] + c[1] * zt + c[2] * zt**2 + c[3] * zt**3 + c[4] * zt**4
    A = np.where(T < -10.0,
                 A1SI * np.exp(-Q1 / (8.314 * (273.15 + T))),
                 A2SI * np.exp(-Q2 / (8.314 * (273.15 + T))))
    a = np.deg2rad(L["alpha"])
    n = N_GLEN
    u = 2.0 * A / (n + 1.0) * (RHO_I * G * a) ** n * (H ** (n + 1.0) - (H - zp) ** (n + 1.0)) \
        + (RHO_I * G * H * a / L["cb"]) ** (1.0 / M_SLIDE)
    return u * YEAR_S


def u_elastic(H: float, zp: np.ndarray, L: dict) -> np.ndarray:
    """elastic template LUA u_elastic_local (SI Eq. 49) [m]:
    u = u_b + 2(1+nu) rho g sin(alpha)/E (H z' - z'^2/2)."""
    a = np.deg2rad(L["alpha"])
    return U_B + 2.0 * (1.0 + NU) * RHO_I * G * np.sin(a) / E_PA * (H * zp - zp**2 / 2.0)


def blister_w0(L: dict) -> tuple[float, float]:
    """SI Eq. 47 at r = 0 with dp = (P_w - 1) rho g H_p -> (dp [Pa], w0 [m])."""
    hp = L["hp"]
    dp = (L["pw"] - 1.0) * RHO_I * G * hp
    w0 = 3 * dp * (1 - NU**2) / (16 * E_PA * hp**3) * (R_PATCH**4 + 4 * hp**2 / (1 - NU) * R_PATCH**2)
    return dp, w0


# ───────────────────────── geometry ────────────────────────────────────

def domain_corners(meta: dict) -> list[list[float]]:
    """Exact lon/lat of the FULL model domain's corners, same frame as
    build_sim_domains.py (local x along flow at flow_angle_deg in EPSG:3413,
    corner order (-x,-y),(+x,-y),(+x,+y),(-x,+y))."""
    e0, n0 = T4326_3413.transform(meta["lon"], meta["lat"])
    th = np.deg2rad(meta["flow_angle_deg"])
    c, s = np.cos(th), np.sin(th)
    h = LX / 2
    out = []
    for cx, cy in [(-h, -h), (h, -h), (h, h), (-h, h)]:
        lon, lat = T3413_4326.transform(e0 + cx * c - cy * s, n0 + cx * s + cy * c)
        out.append([round(lon, 6), round(lat, 6)])
    return out


def main() -> None:
    import json

    meta_all = {m["id"]: m for m in json.loads(
        (ROOT / "website" / ".r2-cache" / "ch02" / "sim" / "sim_domains.json").read_text())["lakes"]}
    lakes = []
    for n in LAKES:
        L = lake_inputs(n)
        zs = load_dat(L["surf"])
        zb = load_dat(L["bed"])
        zbp = load_dat(L["bpb"])
        meta = meta_all[L["id"]]
        # sanity: the site's tile corners must be the ±7375 m square of
        # the same frame (bilinear-extrapolating them must hit ours)
        dc = domain_corners(meta)
        t = np.array(meta["corners_lonlat"])
        k = LX / 2 / TILE_HALF
        ctr = t.mean(axis=0)
        approx = ctr + (t - ctr) * k
        assert np.abs(approx - np.array(dc)).max() < 2e-3, (n, approx, dc)
        # ── outer walls (zs, zb) along each wall, in the corner order ──
        idx = list(range(0, NGRID, WALL_STRIDE))
        if idx[-1] != NGRID - 1:
            idx.append(NGRID - 1)
        walls = {
            # x = 0 (sif BC 4 "west_inflow"): along +y
            "inflow": (zs[idx, 0], zb[idx, 0]),
            # x = Lx (sif BC 2 "east_outflow"): along +y
            "outflow": (zs[idx, -1], zb[idx, -1]),
            # y = 0 (sif BC 1): along +x
            "lat0": (zs[0, idx], zb[0, idx]),
            # y = Ly (sif BC 3): along +x
            "lat1": (zs[-1, idx], zb[-1, idx]),
        }
        # ── wall profiles at the stations ──
        prof = {}
        for wall, ix in (("inflow", 0), ("outflow", NGRID - 1)):
            st = []
            for f in STATION_FRAC:
                iy = int(round(f * (NGRID - 1)))
                H = float(zs[iy, ix] - zb[iy, ix])
                zp = ZETA * H
                st.append(dict(
                    ly=float(iy * 150.0 - LX / 2), zb=float(zb[iy, ix]), H=H,
                    uv=u_sia(H, zp, L), ue=u_elastic(H, zp, L)))
            prof[wall] = st
        dp, w0 = blister_w0(L)
        w0_dem = float((zbp - zb).max())
        Hc = float(zs[NGRID // 2, NGRID // 2] - zb[NGRID // 2, NGRID // 2])
        gi = np.array(GRID_IDX)
        grid = (zs[np.ix_(gi, gi)], zb[np.ix_(gi, gi)])
        L.update(walls=walls, prof=prof, dp=dp, w0=w0, w0_dem=w0_dem, corners=dc, Hc=Hc, grid=grid)
        lakes.append(L)
        ci = prof["inflow"][2]
        co = prof["outflow"][2]
        print(f"{L['id']} (2019cw{n}): alpha {L['alpha']}°  Hp {L['hp']:.0f}  c_b {L['cb']:.2g}"
              f"{'  (sif says ' + format(L['cb_sif'], '.2g') + ')' if L['cb_sif'] != L['cb'] else ''}"
              f"  P_w {L['pw']}  dp {dp/1e3:.0f} kPa  w0 {w0:.3f} m (DEM max {w0_dem:.3f})")
        for nm, c in (("inflow", ci), ("outflow", co)):
            uv, ue = c["uv"], c["ue"]
            print(f"    {nm:7s} centre H {c['H']:.0f} m: viscous u(0) {uv[0]:.1f} u(H) {uv[-1]:.1f}"
                  f" max {uv.max():.1f} @ z'/H {ZETA[uv.argmax()]:.2f} m/yr | elastic u(H) {ue[-1]*100:.2f} cm")

    write_data_ts(lakes)
    write_svgs(lakes)


# ───────────────────────── TS data ─────────────────────────────────────

def r(x: float, nd: int = 1) -> str:
    return f"{x:.{nd}f}".rstrip("0").rstrip(".") if nd else f"{x:.0f}"


def write_data_ts(lakes: list[dict]) -> None:
    L = []
    L.append("// GENERATED by cinematic/scene_ch02/build_bc_cards.py — do not edit.")
    L.append("// Ch.2 boundary conditions, per lake, read from the published run")
    L.append("// inputs (cinematic/source_data/pnas_sims/bc/: the viscous + elastic")
    L.append("// .sif files, PROG/USF_TAVz.F90, the 166 × 166 × 150 m Elmer input")
    L.append("// DEMs) and the published netCDF filenames; notation = PNAS SI §4.")
    L.append("//")
    L.append("// Frame: local x along flow (inflow x = −Lx/2, outflow +Lx/2), y")
    L.append("// across (lat0 y = −Ly/2, lat1 +Ly/2), origin at the patch centre;")
    L.append("// the FULL model domain is Lx = Ly = 24.75 km (sif Lx), the site's")
    L.append("// block is the central 14.75 km analysis tile.")
    L.append("")
    L.append("export const BC_CONST = {")
    L.append("  /** Model domain side [m] — sif `$ Lx = 24750.0`. */")
    L.append(f"  Lx: {LX:.0f},")
    L.append("  /** Patch / blister radius [m] — sif `$ R = 2500`, SI §4. */")
    L.append(f"  R: {R_PATCH:.0f},")
    L.append("  /** Glen exponent — sif `$ n = 3.0`, SI Eq. 39. */")
    L.append("  n: 3,")
    L.append("  /** Weertman exponent m = 1/n — sif `$ m = 1.0/n`, SI Eq. 42. */")
    L.append("  m: 1 / 3,")
    L.append("  /** Ice density [kg m⁻³] — sif Constants rhoi, SI §4A. */")
    L.append("  rhoI: 917,")
    L.append("  /** Young's modulus [Pa] — published nc `youngmod3.077e3` [MPa], SI §4B. */")
    L.append(f"  E: {E_PA:.4g},")
    L.append("  /** Poisson ratio — nc source `_nu0.3_`, SI §4B. */")
    L.append("  nu: 0.3,")
    L.append("  /** Basal displacement outside the blister [m] — nc source `_u0p0_`, SI Eq. 50. */")
    L.append("  uB: 0,")
    L.append("} as const")
    L.append("")
    L.append("/** z'/H levels of every wall profile below (25, bed → surface). */")
    L.append("export const BC_ZETA = [" + ", ".join(r(z, 4) for z in ZETA) + "] as const")
    L.append("")
    L.append("/** Coarse full-domain grid node indices on the 166-node Elmer grid (× 150 m from x, y = 0). */")
    L.append("export const BC_GRID_IDX = [" + ", ".join(str(i) for i in GRID_IDX) + "] as const")
    L.append("")
    L.append("export interface BcWall { /** surface [m] */ zs: number[]; /** bed [m] */ zb: number[] }")
    L.append("export interface BcStation {")
    L.append("  /** across-flow position on the wall [m] */ ly: number")
    L.append("  /** bed elevation [m] */ zb: number")
    L.append("  /** local ice thickness [m] */ H: number")
    L.append("  /** viscous Dirichlet u_x(z') [m yr⁻¹] at BC_ZETA — USF_TAVz.F90 BC_SIA_Tsicopolis */ uv: number[]")
    L.append("  /** elastic Dirichlet u_x(z') [m] at BC_ZETA — template LUA u_elastic_local */ ue: number[]")
    L.append("}")
    L.append("export interface BcLake {")
    L.append("  /** sim id (2019cwNNN) */ cw: string")
    L.append("  /** tile-mean surface slope α [°] — viscous sif `$ alphadeg` (also the DEM/elastic token) */ alphaDeg: number")
    L.append("  /** mean ice thickness over the blister footprint H_p [m] — sif `$ Hp` */ hpM: number")
    L.append("  /** Weertman coefficient c_b [Pa m^-1/3 s^1/3] — published viscous nc `csi` token (= SI Figs. S7–S13) */ cb: number")
    L.append("  /** blister water pressure P_w [× overburden] — published blister DEM / nc `pw` token (= SI Figs. S14–S20) */ pw: number")
    L.append("  /** ice thickness at the patch centre [m] — input DEMs */ hCentreM: number")
    L.append("  /** blister footprint peak [m] — max(bedplusblister − bed) of the published input DEM */ w0Dem: number")
    L.append("  /** SICOPOLIS T(z'/H) quartic c0..c4 [°C] — viscous sif */ tCoef: number[]")
    L.append("  /** FULL-domain corners [lon, lat]: (−x,−y), (+x,−y), (+x,+y), (−x,+y) */ corners: [number, number][]")
    L.append("  /** outer walls (inflow/outflow along +y, lat0/lat1 along +x), every 450 m */")
    L.append("  walls: { inflow: BcWall; outflow: BcWall; lat0: BcWall; lat1: BcWall }")
    L.append("  /** full-domain surface / bed on BC_GRID_IDX × BC_GRID_IDX, row-major [iy][ix] (x along flow) [m] */")
    L.append("  grid: { zs: number[]; zb: number[] }")
    L.append("  /** Dirichlet profiles at y = 0.1, 0.3, 0.5, 0.7, 0.9 L_y */")
    L.append("  prof: { inflow: BcStation[]; outflow: BcStation[] }")
    L.append("}")
    L.append("")
    L.append("export const BC_LAKES: Record<string, BcLake> = {")
    for k in lakes:
        L.append(f"  // 2019cw{k['n']}: sif α {k['alpha']}°, H_p {k['hp']:.0f} m; c_b {k['cb']:.2g}"
                 + (f" (the checked-in sif says {k['cb_sif']:.2g} — the PUBLISHED run is {k['cb']:.2g})" if k['cb_sif'] != k['cb'] else "")
                 + f"; P_w {k['pw']}")
        L.append(f"  {k['id']}: {{")
        L.append(f"    cw: '2019cw{k['n']}', alphaDeg: {k['alpha']}, hpM: {k['hp']:.0f}, cb: {k['cb']:.4g}, pw: {k['pw']},")
        L.append(f"    hCentreM: {k['Hc']:.0f}, w0Dem: {k['w0_dem']:.3f},")
        L.append("    tCoef: [" + ", ".join(f"{c:g}" for c in k["tco"]) + "],")
        L.append("    corners: [" + ", ".join(f"[{c[0]}, {c[1]}]" for c in k["corners"]) + "],")
        L.append("    walls: {")
        for w, (zs, zb) in k["walls"].items():
            L.append(f"      {w}: {{ zs: [" + ", ".join(f"{v:.0f}" for v in zs) + "],")
            L.append("        zb: [" + ", ".join(f"{v:.0f}" for v in zb) + "] },")
        L.append("    },")
        L.append("    grid: {")
        L.append("      zs: [" + ", ".join(f"{v:.0f}" for v in k["grid"][0].ravel()) + "],")
        L.append("      zb: [" + ", ".join(f"{v:.0f}" for v in k["grid"][1].ravel()) + "],")
        L.append("    },")
        L.append("    prof: {")
        for w, st in k["prof"].items():
            L.append(f"      {w}: [")
            for s in st:
                L.append(f"        {{ ly: {s['ly']:.0f}, zb: {s['zb']:.0f}, H: {s['H']:.0f},")
                L.append("          uv: [" + ", ".join(f"{v:.2f}" for v in s["uv"]) + "],")
                L.append("          ue: [" + ", ".join(f"{v:.5f}" for v in s["ue"]) + "] },")
            L.append("      ],")
        L.append("    },")
        L.append("  },")
    L.append("}")
    TS_DATA.write_text("\n".join(L) + "\n")
    print(f"wrote {TS_DATA.relative_to(ROOT)}")


# ───────────────────────── LaTeX SVGs ──────────────────────────────────

PT_TO_BP = 72.0 / 72.27
PAD_BP = 1.5
COLORS = {"ink": "F5F0E6", "gold": "F5C75E", "dim": "CFC6B4"}
PREAMBLE = (r"""\documentclass[preview,border=0pt]{standalone}
\usepackage{amsmath,amssymb,bm}
\usepackage{xcolor}
""" + "".join(f"\\definecolor{{{k}}}{{HTML}}{{{v}}}\n" for k, v in COLORS.items()))


def run(cmd: list[str], cwd: Path) -> None:
    env = dict(os.environ, PATH=f"{TEXBIN}:{os.environ.get('PATH', '')}")
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stdout.write(p.stdout[-3000:] + p.stderr[-3000:])
        raise SystemExit(f"failed: {' '.join(cmd)}")


def compile_svg(tex: str, color: str, wd: Path, stem: str) -> tuple[str, float, float, float]:
    """One TeX box -> SVG whose viewBox is the box (+pad), baseline at 0
    (the Ch.1 build_theory_eqs.py recipe)."""
    lines = [PREAMBLE, r"\begin{document}",
             f"\\sbox0{{\\color{{{color}}}{tex}}}%",
             r"\typeout{BOX:\the\wd0,\the\ht0,\the\dp0}%",
             r"\usebox0%", r"\end{document}"]
    (wd / f"{stem}.tex").write_text("\n".join(lines))
    run(["latex", "-interaction=nonstopmode", f"{stem}.tex"], wd)
    log = (wd / f"{stem}.log").read_text(errors="replace")
    m = re.search(r"BOX:([\d.]+)pt,([\d.]+)pt,([\d.]+)pt", log)
    w, h, d = (float(m.group(i)) for i in (1, 2, 3))
    run(["dvisvgm", "--no-fonts", "-o", f"{stem}.svg", f"{stem}.dvi"], wd)
    svg = (wd / f"{stem}.svg").read_text()
    W = w * PT_TO_BP + 2 * PAD_BP
    H = (h + d) * PT_TO_BP + 2 * PAD_BP
    y0 = -h * PT_TO_BP - PAD_BP
    head = re.search(r"<svg [^>]*>", svg).group(0)
    new = re.sub(r"width='[^']*'", f"width='{W:.4f}pt'", head)
    new = re.sub(r"height='[^']*'", f"height='{H:.4f}pt'", new)
    new = re.sub(r"viewBox='[^']*'", f"viewBox='{-PAD_BP:.4f} {y0:.4f} {W:.4f} {H:.4f}'", new)
    return svg.replace(head, new, 1), W, H, h * PT_TO_BP + PAD_BP


def sci(x: float) -> str:
    """8.6e6 -> 8.6\\times10^{6}"""
    e = int(np.floor(np.log10(abs(x))))
    m = x / 10**e
    return f"{m:.2g}\\times10^{{{e}}}"


CB_UNIT = r"\,\mathrm{Pa\,m^{-1/3}\,s^{1/3}}"

# shared equations: name -> (tex, display?, color, source)
SHARED = {
    # locations (the sif boundaries; SI §4 coordinates)
    "loc_x0": (r"x = 0", False, "dim", "sif BC 4 west_inflow; SI §4A"),
    "loc_xL": (r"x = L_x", False, "dim", "sif BC 2 east_outflow; SI §4A"),
    "loc_y0": (r"y = 0", False, "dim", "sif BC 1; SI §4A"),
    "loc_yL": (r"y = L_y", False, "dim", "sif BC 3; SI §4A"),
    "loc_zb": (r"z = z_b", False, "dim", "sif BC 5; SI Eq. 41"),
    "loc_zs": (r"z = z_s", False, "dim", "sif BC 6; SI Eq. 40/48"),
    # free surface — both models (SI Eqs. 40, 48; sif BC 6 = natural)
    "surface": (r"\boldsymbol{\sigma}\cdot\mathbf{n} = \mathbf{0}", False, "ink", "SI Eqs. 40, 48"),
    # lateral walls — both models: Velocity/Displacement 2 = 0, the
    # other two components natural (zero traction) = free slip
    "lateral": (r"\mathbf{u}\cdot\hat{\mathbf{y}} = 0", False, "ink", "SI §4A (u·ŷ = 0); sif BC 1/3 Velocity 2 = 0"),
    "lateral_tan": (r"\sigma_{xy} = \sigma_{zy} = 0", False, "ink", "free slip: sif BC 1/3 leave components 1, 3 natural"),
    # x-walls: Dirichlet u_x only; y, z components natural
    "wall_tan": (r"\sigma_{yx} = \sigma_{zx} = 0", False, "ink", "sif BC 2/4 set component 1 only"),
    # viscous
    "v_wall": (r"u_x = u_{\mathrm{SIA}}(z')", False, "ink", "SI Eq. 44; sif BC 2/4 BC_SIA_Tsicopolis"),
    "v_wall_full": (r"u_{\mathrm{SIA}}(z') = \frac{2A(T)}{n+1}\,(\rho_i g \sin\alpha)^{n}"
                    r"\left[H^{n+1} - (H-z')^{n+1}\right]"
                    r" + \left(\frac{\rho_i g H \sin\alpha}{c_b}\right)^{1/m}",
                    True, "ink", "SI Eq. 44 (c_b as run: USF_TAVz.F90 divides by Csi)"),
    "v_bed": (r"\boldsymbol{\tau}_b = -C_b\,|\mathbf{u}_b|^{m-1}\,\mathbf{u}_b", False, "ink", "SI Eq. 42"),
    "v_bed_n": (r"\mathbf{u}\cdot\mathbf{n}_b = 0", False, "ink", "SI Eq. 41"),
    "v_bed_cb": (r"C_b = \begin{cases} c_b, & r > R \\ 0, & r \le R \end{cases}", True, "ink", "SI Eq. 43; sif Weertman Friction Coefficient MATC"),
    "v_patch": (r"\boldsymbol{\tau}_b = \mathbf{0}\quad (r \le R)", False, "gold", "SI Eq. 43"),
    # elastic
    "e_wall": (r"u_x = u_b + \frac{2(1+\nu)\,\rho_i g \sin\alpha}{E}\left(H z' - \tfrac{1}{2}z'^2\right)",
               False, "ink", "SI Eq. 49; template LUA u_elastic_local"),
    "e_bed": (r"\mathbf{u} = \mathbf{0}\quad (r > R)", False, "ink", "SI Eq. 50; template BC 5"),
    "e_patch": (r"\boldsymbol{\sigma}\cdot\mathbf{n}_b = -P_w\,\rho_i g H\,\mathbf{n}_b\quad (r \le R)", False, "gold",
                "SI Eq. 51; runsims_localH.sh Normal Force = -Pw rho g (zs - zb)"),
    # shared values
    "vals_n": (r"n = 3,\quad m = 1/3", False, "dim", "sif $ n, $ m"),
    "vals_R": (r"R = 2.5\ \mathrm{km}", False, "dim", "sif $ R"),
    "vals_E": (r"E = 3.077\ \mathrm{GPa},\quad \nu = 0.3,\quad u_b = 0", False, "dim", "published nc tokens; SI §4B"),
}


def per_lake_eqs(k: dict) -> dict:
    """Per-lake value lines (numbers with units — the run's values)."""
    i = k["id"]
    c_in = k["prof"]["inflow"][2]
    c_out = k["prof"]["outflow"][2]
    out = {}
    out[f"vals_alpha_{i}"] = (rf"\alpha = {k['alpha']:.3f}^\circ", False, "dim", "sif $ alphadeg")
    out[f"vals_cb_{i}"] = (rf"c_b = {sci(k['cb'])}{CB_UNIT}", False, "dim", "published nc csi token")
    for nm, c in (("in", c_in), ("out", c_out)):
        uv, ue = c["uv"], c["ue"]
        out[f"vals_vu_{nm}_{i}"] = (
            rf"H = {c['H']:.0f}\ \mathrm{{m}}:\quad u_x(0) = {uv[0]:.0f},\ \ u_x(H) = {uv[-1]:.0f}\ \mathrm{{m\,yr^{{-1}}}}",
            False, "dim", "USF_TAVz.F90 at the wall centre, input DEMs")
        out[f"vals_eu_{nm}_{i}"] = (
            rf"H = {c['H']:.0f}\ \mathrm{{m}}:\quad u_x(H) = {ue[-1] * 100:.1f}\ \mathrm{{cm}}",
            False, "dim", "u_elastic_local at the wall centre, input DEMs")
    out[f"vals_pw_{i}"] = (rf"P_w = {k['pw']:.4f}", False, "gold", "published blister pw token")
    # The applied traction at the patch centre (runsims_localH.sh Normal
    # Force = -Pw rho g (zs - zb), local H from the input DEMs).
    pc = k["pw"] * RHO_I * G * k["Hc"]
    out[f"vals_pc_{i}"] = (
        rf"P_w\,\rho_i g H\,\big|_{{r=0}} = {pc / 1e6:.2f}\ \mathrm{{MPa}}\quad (H = {k['Hc']:.0f}\ \mathrm{{m}})",
        False, "dim", "Normal Force LUA at the patch centre, input DEMs")
    return out


def write_svgs(lakes: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    eqs = dict(SHARED)
    for k in lakes:
        eqs.update(per_lake_eqs(k))
    manifest = {}
    with tempfile.TemporaryDirectory() as td:
        wd = Path(td)
        for name, (tex, display, color, src) in eqs.items():
            body = f"$\\displaystyle {tex}$" if display else f"${tex}$"
            svg, W, H, base = compile_svg(body, color, wd, name)
            (OUT / f"{name}.svg").write_text(svg)
            manifest[name] = (W, H, base, src)
    lines = [
        "// GENERATED by cinematic/scene_ch02/build_bc_cards.py — do not edit.",
        "// LaTeX (latex + dvisvgm, Computer Modern) boundary-condition cards,",
        "// served from R2 ch02/bc2/<name>.svg. Sizes in bp; base = image top →",
        "// baseline. Sources: PNAS SI §4 equation numbers + the run inputs.",
        "export interface BcEqBox { w: number; h: number; base: number }",
        "export const CH2_BC_EQ: Record<string, BcEqBox> = {",
    ]
    for name, (W, H, base, src) in manifest.items():
        lines.append(f"  {name}: {{ w: {W:.3f}, h: {H:.3f}, base: {base:.3f} }}, // {src}")
    lines.append("}")
    TS_EQS.write_text("\n".join(lines) + "\n")
    print(f"wrote {len(manifest)} svgs -> {OUT.relative_to(ROOT)} + {TS_EQS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
