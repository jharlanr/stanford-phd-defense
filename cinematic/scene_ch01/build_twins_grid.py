"""Build the twins slider grid + the alpha/h map figures.

The director's ask: on the twin-globes beat, two sliders (tau_val, ell —
discretized) re-render the ACL and max-stress drapes live; and the ACL
beat gains two small Greenland maps (along-flow slope alpha, thickness
h) that motivate applying the ACL to the whole ice sheet.

Physics split (why the grid is cheap): x_bl depends only on (h, alpha,
gamma, n) — invariant under tau_val and ell; tau_max = rho*g*alpha*ell/4
is linear in ell and independent of tau_val. So the expensive part
(BedMachine + ITS_LIVE load, slope smoothing, EPSG:3413 → PlateCarree
resample) runs ONCE; each grid tile is pure numpy + PIL.

Outputs (cinematic/data/):
  twins_grid_cache.npz          x_bl (per gamma), tau-per-m-of-ell, h,
                                alpha in the 2600x1000 PlateCarree frame
                                (+ the EPSG:3413 grids for the map figures)
  twins/acl_t{TTT}_l{LL}.png    25 ACL drapes at gamma=0.1 (turbo, 0..15 km, PNG-8)
  twins/g05/acl_t{TTT}_l{LL}.png the same 25 at gamma=0.5 (the director
                                asked for a binary gamma toggle on the ACL globes)
  ch01_acl_map_g05.png          the hero combo (30 kPa, 10 km) at gamma=0.5,
                                full 5200x2000 res like build_acl_maps' acl_map.png
  twins/taumax_l{LL}.png         5 max-stress drapes (inferno, 0..300;
                                gamma-independent)
  twins/grid.json               axis values + naming manifest
  ch01_alpha_map_fig.png        along-flow slope map (site-dark style)
  ch01_h_map_fig.png            ice-thickness map (site-dark style)
  ch01_twins_grid_qa.png        QA contact sheet (4 corner combos)

Later additions (the n toggle and the transparent map figures):
  twins/n3/acl_t{TTT}_l{LL}.png     the 25 ACL drapes for Glen n=3, gamma=0.1
  twins/n3/g05/acl_t{TTT}_l{LL}.png the same 25 at gamma=0.5
  ch01_acl_map_n3.png               hero combo (30 kPa, 10 km), n=3, gamma=0.1,
                                    full 5200x2000 res
  ch01_acl_map_n3_g05.png           the same at gamma=0.5
      The n toggle on the twin globes changes ONLY the ACL half: max
      tau_xx = rho*g*alpha*ell/4 does not depend on n. ACL follows the
      paper's eqn:acl exactly, ACL = [x] / n^(-1/(n+1)) * ln(tau_max/tau_val)
      with [x] = (2Bh/C)^(n/(n+1)); B cancels at fixed gamma (paper
      line ~417), so [x] = h*[2^n (n+2+2gamma)/((n+2)gamma)]^(1/(n+1)).
  ch01_alpha_map_fig2.png           the alpha map, MAP ONLY on a TRANSPARENT
  ch01_h_map_fig2.png               background (no title, no colorbar — the
                                    theory panel draws both as SVG so the
                                    ticks stay legible at any size)
  twins_map_fig2.json               the figures' geographic extent + the
                                    colormap stops the SVG colorbars use

Inputs (local copies only — bash cinematic/fetch_sources.sh):
  source_data/data/BedMachineGreenland-v6.nc
  source_data/data/ITS_LIVE_velocity_120m_RGI05A_0000_V02.1.nc

Run:  python -u cinematic/scene_ch01/build_twins_grid.py [--only n1,n3,maps,maps2,qa,check]
Then:
  rclone copy cinematic/data/twins r2:<bucket>/ch01/twins --header-upload 'Cache-Control: public, max-age=31536000, immutable'
  rclone copyto cinematic/data/ch01_acl_map_g05.png r2:<bucket>/ch01/acl_map_g05.png --header-upload 'Cache-Control: public, max-age=31536000, immutable'
  rclone copyto cinematic/data/ch01_acl_map_n3.png r2:<bucket>/ch01/acl_map_n3.png --header-upload 'Cache-Control: public, max-age=31536000, immutable'
  rclone copyto cinematic/data/ch01_acl_map_n3_g05.png r2:<bucket>/ch01/acl_map_n3_g05.png --header-upload 'Cache-Control: public, max-age=31536000, immutable'
  rclone copyto cinematic/data/ch01_alpha_map_fig2.png r2:<bucket>/ch01/alpha_map_fig2.png --header-upload 'Cache-Control: public, max-age=31536000, immutable'
  rclone copyto cinematic/data/ch01_h_map_fig2.png r2:<bucket>/ch01/h_map_fig2.png --header-upload 'Cache-Control: public, max-age=31536000, immutable'
  (then `rclone copy` the same keys into website/.r2-cache — never `sync`)
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared import BEDMACHINE_PATH, SOURCE_DATA, require_source  # noqa: E402

sys.stdout.reconfigure(line_buffering=True)

ITSLIVE_PATH = SOURCE_DATA / "data" / "ITS_LIVE_velocity_120m_RGI05A_0000_V02.1.nc"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vendor"))
from bedmachine_gris_density import build_grid_state  # noqa: E402

# ── Physics — identical constants to build_acl_maps.py ────────────────
RHO, G = 917.0, 9.81
N_FLOW = 1
ETA = 1e14
A_RATE = 1.0 / (2.0 * ETA)
GAMMA = 0.1                     # the hero gamma (the legacy cache key x_bl_ll)
GAMMAS = [0.1, 0.5]             # the toggle on the twin globes
# The n toggle. A per n: n=1 from eta (above); n=3 = the
# paper's fig A1 value B^-n = 2.4e-24 Pa^-3 s^-1. B cancels in [x] at
# fixed gamma, so A only has to be self-consistent.
N_FLOWS = [1, 3]
A_BY_N = {1: A_RATE, 3: 2.4e-24}

# ── The slider grid (matches TheoryPanel's ranges; includes the hero
#    default 30 kPa / 10 km so the grid's center tile IS today's map) ──
TAU_VALS_KPA = [10, 30, 50, 70, 100]
ELLS_KM = [2, 5, 10, 15, 20]

# ── Texture frames ────────────────────────────────────────────────────
LON_W, LON_E = -75.0, -10.0
LAT_S, LAT_N = 59.0, 84.0
GRID_W, GRID_H = 2600, 1000     # grid tiles: half the hero pair's res
HERO_W, HERO_H = 5200, 2000     # the hero pair's res (build_acl_maps.py)

ACL_CMAP, ACL_VMAX_KM = "turbo", 15.0
STRESS_CMAP, STRESS_VMAX_KPA = "inferno", 300.0
ALPHA_FULL_KM = 2.0
MAX_ALPHA = 0.88
PAGE_BG = "#0a0908"
INK = "#f5f0e6"
GOLD = "#f5c75e"

OUT = Path(__file__).resolve().parents[1] / "data"
OUT.mkdir(exist_ok=True)
TWINS = OUT / "twins"
TWINS.mkdir(exist_ok=True)
CACHE = OUT / "twins_grid_cache.npz"


def compute_base():
    """Parameter-free stage: h, alpha, x_bl on the BedMachine grid."""
    grid = build_grid_state(
        bedmachine_path=str(require_source(BEDMACHINE_PATH)),
        itslive_path=str(require_source(ITSLIVE_PATH)),
    )
    h = grid["h"]
    alpha = grid["alpha"].copy()
    mask = grid["mask"]
    surf = grid["surf"]

    no_flow = ~np.isfinite(alpha)
    if no_flow.any():
        alpha_fb = np.degrees(np.arctan(np.sqrt(grid["dsdx"] ** 2 + grid["dsdy"] ** 2)))
        alpha[no_flow] = alpha_fb[no_flow]
        print(f"filled {no_flow.sum():,} stagnant pixels with |grad s| fallback")

    valid = (mask == 2) & np.isfinite(alpha) & (alpha > 0) & (h > 0)
    a_rad = np.radians(alpha)

    n, A = N_FLOW, A_RATE
    m = 1.0 / n
    B = A ** (-1.0 / n)
    C_b = np.full_like(h, np.nan)
    C_b[valid] = (
        GAMMA**m * (RHO * G * a_rad[valid]) ** (1 - m * n)
        * A ** (-m) * h[valid] ** (1 - m - m * n)
    )
    ub_over_u = 1.0 / (1.0 + (2 * A / (n + 2)) * h * C_b**n)
    C = C_b * ub_over_u**m
    x_bl = np.full_like(h, np.nan)
    x_bl[valid] = (2 * B * h[valid] / C[valid]) ** (n / (n + 1))

    # tau_max per metre of ell: tau_max[kPa] = tau_per_m * ell[m]
    tau_per_m = np.full_like(h, np.nan)
    tau_per_m[valid] = RHO * G * a_rad[valid] / 4 / 1e3

    print(
        f"base grids: valid={valid.sum():,} px, "
        f"x_bl p50={np.nanmedian(x_bl[valid])/1e3:.2f} km, "
        f"alpha p50={np.nanmedian(alpha[valid]):.3f} deg, "
        f"h p50={np.nanmedian(h[valid]):.0f} m"
    )
    return dict(
        h=h, alpha=alpha, x_bl=x_bl, tau_per_m=tau_per_m, valid=valid,
        surf=surf, mask=mask, x=grid["x"], y=grid["y"], dx=grid["dx"],
    )


def x_bl_for_gamma(h, alpha_deg, valid, gamma, n=N_FLOW):
    """Boundary-layer length x_bl [m] on the native grid for one gamma
    and flow-law exponent n (the same formula as compute_base; for n=1,
    x_bl = h*sqrt(2/gamma + 4/3); in general B cancels and
    x_bl = h*[2^n (n+2+2gamma)/((n+2)gamma)]^(1/(n+1)))."""
    A = A_BY_N[n]
    m = 1.0 / n
    B = A ** (-1.0 / n)
    a_rad = np.radians(alpha_deg)
    C_b = np.full_like(h, np.nan)
    C_b[valid] = (
        gamma**m * (RHO * G * a_rad[valid]) ** (1 - m * n)
        * A ** (-m) * h[valid] ** (1 - m - m * n)
    )
    ub_over_u = 1.0 / (1.0 + (2 * A / (n + 2)) * h * C_b**n)
    C = C_b * ub_over_u**m
    x_bl = np.full_like(h, np.nan)
    x_bl[valid] = (2 * B * h[valid] / C[valid]) ** (n / (n + 1))
    return x_bl


def gamma_tag(gamma: float) -> str:
    return f"g{gamma:.1f}".replace(".", "")   # 0.1 -> g01, 0.5 -> g05


def x_bl_closed_form(h, gamma, n):
    """Paper line ~417: [x] = h*[2^n (n+2+2gamma)/((n+2)gamma)]^(1/(n+1))."""
    return h * (2.0**n * (n + 2 + 2 * gamma) / ((n + 2) * gamma)) ** (1.0 / (n + 1))


def acl_point(h, alpha_deg, ell_m, gamma, tau_val_kpa, n):
    """ACL [m] at one (h, alpha, ell, gamma, tau_val) — eqn:acl."""
    tau_max = RHO * G * np.radians(alpha_deg) * ell_m / 4 / 1e3
    if tau_max <= tau_val_kpa:
        return 0.0
    lam = n ** (-1.0 / (n + 1))
    return x_bl_closed_form(h, gamma, n) / lam * np.log(tau_max / tau_val_kpa)


def to_platecarree(g, field, w, h):
    from pyproj import Transformer
    from scipy.interpolate import RegularGridInterpolator

    y_asc = g["y"][::-1]
    interp = RegularGridInterpolator(
        (y_asc, g["x"]), field[::-1, :], method="linear",
        bounds_error=False, fill_value=np.nan,
    )
    lons = np.linspace(LON_W, LON_E, w)
    lats = np.linspace(LAT_N, LAT_S, h)
    lon2, lat2 = np.meshgrid(lons, lats)
    tr = Transformer.from_crs("EPSG:4326", "EPSG:3413", always_xy=True)
    px, py = tr.transform(lon2, lat2)
    return interp(np.stack([py.ravel(), px.ravel()], axis=-1)).reshape(h, w)


def build_cache():
    if CACHE.exists():
        print(f"cache hit: {CACHE.name}")
        cache = dict(np.load(CACHE))
        return ensure_gamma_layers(cache)
    g = compute_base()
    print("reprojecting x_bl / tau_per_m / h / alpha to PlateCarree ...")
    x_bl_ll = to_platecarree(g, g["x_bl"], GRID_W, GRID_H)
    tau_per_m_ll = to_platecarree(g, g["tau_per_m"], GRID_W, GRID_H)
    cache = dict(
        x_bl_ll=x_bl_ll.astype(np.float32),
        tau_per_m_ll=tau_per_m_ll.astype(np.float32),
        # EPSG:3413 grids for the two map figures
        h=g["h"].astype(np.float32),
        alpha=g["alpha"].astype(np.float32),
        surf=np.where(np.isfinite(g["surf"]), g["surf"], 0.0).astype(np.float32),
        mask=g["mask"].astype(np.int8),
        valid=g["valid"],
        x=g["x"].astype(np.float64),
        y=g["y"].astype(np.float64),
        dx=np.array(g["dx"], dtype=np.float64),
    )
    np.savez_compressed(CACHE, **cache)
    print(f"wrote {CACHE.name} ({CACHE.stat().st_size / 1e6:.1f} MB)")
    return ensure_gamma_layers(cache)


def ensure_gamma_layers(cache: dict) -> dict:
    """x_bl per gamma in BOTH frames (grid tiles 2600x1000, hero
    5200x2000), computed from the cached native h / alpha — no BedMachine
    reload. Added to the cache file the first time."""
    g = dict(x=cache["x"], y=cache["y"])
    valid = cache["valid"].astype(bool)
    h = cache["h"].astype(float)
    alpha = cache["alpha"].astype(float)
    changed = False
    for n in N_FLOWS:
        for gamma in GAMMAS:
            tag = gamma_tag(gamma)
            key = n_key(n, tag)
            if f"x_bl_ll_{key}" in cache and f"x_bl_hero_{key}" in cache:
                continue
            x_bl = x_bl_for_gamma(h, alpha, valid, gamma, n)
            # closed-form cross-check (B cancels): x_bl / h is one number
            ratio = x_bl[valid] / h[valid]
            print(f"n={n} gamma={gamma}: x_bl p50={np.nanmedian(x_bl[valid])/1e3:.2f} km; "
                  f"x_bl/h = {np.nanmin(ratio):.4f}..{np.nanmax(ratio):.4f} "
                  f"(closed form {x_bl_closed_form(1.0, gamma, n):.4f})")
            cache[f"x_bl_ll_{key}"] = to_platecarree(g, x_bl, GRID_W, GRID_H).astype(np.float32)
            cache[f"x_bl_hero_{key}"] = to_platecarree(g, x_bl, HERO_W, HERO_H).astype(np.float32)
            changed = True
    if changed:
        np.savez_compressed(CACHE, **cache)
        print(f"updated {CACHE.name} with per-(n, gamma) x_bl ({CACHE.stat().st_size / 1e6:.1f} MB)")
    return cache


def n_key(n: int, tag: str) -> str:
    """Cache-key suffix: n=1 keeps the original keys (g01/g05); n=3 → n3_g01."""
    return tag if n == 1 else f"n{n}_{tag}"


def save_png8(rgba: np.ndarray, out: Path) -> None:
    """Quantize an RGBA float array to a 256-color palette PNG."""
    from PIL import Image

    img = Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBA")
    pal = img.quantize(colors=256, method=Image.FASTOCTREE)
    pal.save(out, optimize=True)


def acl_rgba(x_bl, tau_max, tau_val, finite, n=N_FLOW):
    """ACL [km] → turbo RGBA with the alpha ramp (the drape encoding)."""
    from matplotlib import cm

    lam = n ** (-1.0 / (n + 1))  # 1 for n=1; 3^(-1/4) for n=3
    acl = np.zeros_like(x_bl)
    above = finite & (tau_max > tau_val)
    acl[above] = (x_bl[above] / lam) * np.log(tau_max[above] / tau_val) / 1e3
    acl[~finite] = np.nan
    norm = np.clip(acl / ACL_VMAX_KM, 0, 1)
    rgba = cm.get_cmap(ACL_CMAP)(np.where(finite, norm, 0.0))
    alpha = np.clip(acl / ALPHA_FULL_KM, 0, 1) * MAX_ALPHA
    alpha[~finite] = 0.0
    rgba[..., 3] = alpha
    return rgba, int(above.sum())


def write_grid_tiles(cache, n: int = N_FLOW) -> None:
    from matplotlib import cm

    tau_per_m = cache["tau_per_m_ll"]
    tau_cmap = cm.get_cmap(STRESS_CMAP)
    # n=1 keeps the original paths; n=3 nests everything under twins/n3/
    base = TWINS if n == 1 else TWINS / f"n{n}"
    base.mkdir(exist_ok=True)

    for ell_km in ELLS_KM:
        ell_m = ell_km * 1e3
        tau_max = tau_per_m * ell_m  # [kPa]
        finite = np.isfinite(cache["x_bl_ll"]) & np.isfinite(tau_per_m)

        # max-stress drape (independent of tau_val, gamma AND n — 5 tiles
        # total, written on the n=1 pass only)
        if n == 1:
            norm = np.clip(tau_max / STRESS_VMAX_KPA, 0, 1)
            rgba = tau_cmap(np.where(finite, norm, 0.0))
            rgba[..., 3] = np.where(finite, MAX_ALPHA + 0.06, 0.0)
            out = TWINS / f"taumax_l{ell_km:02d}.png"
            save_png8(rgba, out)
            print(f"wrote {out.name} ({out.stat().st_size / 1e3:.0f} kB)  "
                  f"tau p99={np.nanpercentile(tau_max[finite], 99):.0f} kPa")

        for gamma in GAMMAS:
            tag = gamma_tag(gamma)
            if n == 1 and gamma == GAMMA:
                x_bl = cache["x_bl_ll"]
            else:
                x_bl = cache[f"x_bl_ll_{n_key(n, tag)}"]
            # gamma=0.1 keeps the original paths; other gammas nest in <base>/<tag>/
            sub = base if gamma == GAMMA else base / tag
            sub.mkdir(exist_ok=True)
            for tau_val in TAU_VALS_KPA:
                rgba, n_above = acl_rgba(x_bl, tau_max, tau_val, finite, n)
                out = sub / f"acl_t{tau_val:03d}_l{ell_km:02d}.png"
                save_png8(rgba, out)
                print(f"wrote {out.relative_to(TWINS)} ({out.stat().st_size / 1e3:.0f} kB)  "
                      f"ACL>0 px={n_above:,}")

    # The hero combo (30 kPa, 10 km) at every non-legacy (n, gamma), at
    # the hero pair's full res (acl_map.png itself — n=1, gamma=0.1 —
    # comes from build_acl_maps.py).
    from PIL import Image
    tau_per_m_hero = None
    for gamma in GAMMAS:
        if n == 1 and gamma == GAMMA:
            continue
        tag = gamma_tag(gamma)
        x_bl = cache[f"x_bl_hero_{n_key(n, tag)}"]
        if tau_per_m_hero is None:
            tau_per_m_hero = to_platecarree(
                dict(x=cache["x"], y=cache["y"]),
                np.where(cache["valid"], RHO * G * np.radians(cache["alpha"].astype(float)) / 4 / 1e3, np.nan),
                HERO_W, HERO_H)
        finite = np.isfinite(x_bl) & np.isfinite(tau_per_m_hero)
        rgba, n_above = acl_rgba(x_bl, tau_per_m_hero * 10e3, 30, finite, n)
        if n == 1:
            out = OUT / f"ch01_acl_map_{tag}.png"
        else:
            out = OUT / (f"ch01_acl_map_n{n}.png" if gamma == GAMMA else f"ch01_acl_map_n{n}_{tag}.png")
        Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8)).save(out, optimize=True)
        print(f"wrote {out.name} ({out.stat().st_size / 1e6:.1f} MB)  ACL>0 px={n_above:,}")
    if n != 1:
        (base / "grid.json").write_text(json.dumps({
            "n": n,
            "a_rate": A_BY_N[n],
            "tau_vals_kpa": TAU_VALS_KPA,
            "ells_km": ELLS_KM,
            "gammas": GAMMAS,
            "acl_tpl": "acl_t{tau:03d}_l{ell:02d}.png",
            "acl_gamma_tpl": "g{gamma_tag}/acl_t{tau:03d}_l{ell:02d}.png",
            "hero_tpl": f"../../acl_map_n{n}.png",
            "hero_gamma_tpl": f"../../acl_map_n{n}_g{{gamma_tag}}.png",
            "taumax": "n-independent: ../taumax_l{ell:02d}.png",
            "acl_vmax_km": ACL_VMAX_KM,
            "size": [GRID_W, GRID_H],
        }, indent=2))
        print(f"wrote {(base / 'grid.json').relative_to(TWINS)}")
        return

    manifest = {
        "tau_vals_kpa": TAU_VALS_KPA,
        "ells_km": ELLS_KM,
        "gammas": GAMMAS,
        "defaults": {"tau_val_kpa": 30, "ell_km": 10, "gamma": GAMMA},
        "acl_tpl": "acl_t{tau:03d}_l{ell:02d}.png",
        "acl_gamma_tpl": "g{gamma_tag}/acl_t{tau:03d}_l{ell:02d}.png",
        "hero_gamma_tpl": "../acl_map_g{gamma_tag}.png",
        "taumax_tpl": "taumax_l{ell:02d}.png",
        "acl_vmax_km": ACL_VMAX_KM,
        "tau_vmax_kpa": STRESS_VMAX_KPA,
        "size": [GRID_W, GRID_H],
    }
    (TWINS / "grid.json").write_text(json.dumps(manifest, indent=2))
    print("wrote grid.json")


def write_map_fig(cache, field, cmap, vmin, vmax, title, cbar_label, out_name,
                  contour_m=1600.0) -> None:
    """Single-panel Greenland map in the site's dark write_panel style —
    compact portrait sized for the ACL beat's in-figure corner."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import cm
    from matplotlib.colors import LightSource, Normalize

    x_km, y_km = cache["x"] / 1e3, cache["y"] / 1e3
    extent = [x_km[0], x_km[-1], y_km[-1], y_km[0]]
    surf = cache["surf"]
    dx = float(cache["dx"])
    hs = LightSource(azdeg=315, altdeg=45).hillshade(surf, vert_exag=0.02, dx=dx, dy=dx)
    land = cache["mask"] > 0

    plt.rcParams.update({
        "font.family": "serif", "text.color": INK,
        "axes.edgecolor": INK, "xtick.color": INK, "ytick.color": INK,
    })
    fig, ax = plt.subplots(figsize=(6.4, 9.4), facecolor=PAGE_BG)
    ax.set_facecolor(PAGE_BG)
    base = np.zeros((*hs.shape, 4))
    base[..., 0] = base[..., 1] = base[..., 2] = 0.32 + 0.38 * hs
    base[..., 3] = np.where(land, 1.0, 0.0)
    ax.imshow(base, extent=extent, aspect="equal", interpolation="bilinear")

    norm = Normalize(vmin=vmin, vmax=vmax)
    rgba = cm.get_cmap(cmap)(norm(np.clip(field, vmin, vmax)))
    shade = (0.55 + 0.45 * hs)[..., None]
    rgba[..., :3] *= shade
    rgba[..., 3] = np.where(np.isfinite(field) & (cache["mask"] == 2), 1.0, 0.0)
    ax.imshow(rgba, extent=extent, aspect="equal", interpolation="bilinear")
    ax.contour(x_km, y_km, surf, levels=[contour_m], colors="white",
               linewidths=0.7, alpha=0.8)

    ax.set_title(title, fontsize=30, color=GOLD, pad=14)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    cb = fig.colorbar(sm, ax=ax, fraction=0.055, pad=0.02, shrink=0.8)
    cb.set_label(cbar_label, fontsize=20, color=INK)
    cb.ax.tick_params(labelsize=16, colors=INK)
    cb.outline.set_edgecolor("#777")

    fig.subplots_adjust(left=0.01, right=0.86, top=0.93, bottom=0.02)
    out = OUT / out_name
    fig.savefig(out, dpi=150, facecolor=PAGE_BG, transparent=False)
    plt.close(fig)
    print(f"wrote {out.name} ({out.stat().st_size / 1e6:.1f} MB)")


MAP2_W_PX = 760   # fig2 output width [px] (~2x its on-screen width at 1920)


def map2_crop(cache):
    """Row/col bounds of the land mask (+ a 6-px margin) — the fig2 frame."""
    land = cache["mask"] > 0
    rows = np.where(land.any(axis=1))[0]
    cols = np.where(land.any(axis=0))[0]
    r0, r1 = max(rows[0] - 6, 0), min(rows[-1] + 7, land.shape[0])
    c0, c1 = max(cols[0] - 6, 0), min(cols[-1] + 7, land.shape[1])
    return r0, r1, c0, c1


def write_map_fig2(cache, field, cmap, vmin, vmax, out_name, contour_m=1600.0) -> dict:
    """The map ONLY, on a TRANSPARENT background
    — no black box, no baked title/colorbar. The theory panel draws the
    title + colorbar (ticks, label) as SVG at figure scale, so they read
    at any window size. Same encoding as write_map_fig: gray hillshade
    land, field over grounded ice, white 1600 m contour."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import cm
    from matplotlib.colors import LightSource, Normalize

    r0, r1, c0, c1 = map2_crop(cache)
    surf = cache["surf"][r0:r1, c0:c1]
    mask = cache["mask"][r0:r1, c0:c1]
    fld = field[r0:r1, c0:c1]
    x_km, y_km = cache["x"][c0:c1] / 1e3, cache["y"][r0:r1] / 1e3
    dx = float(cache["dx"])
    hs = LightSource(azdeg=315, altdeg=45).hillshade(surf, vert_exag=0.02, dx=dx, dy=dx)
    land = mask > 0

    H, W = surf.shape
    dpi = 100
    fig = plt.figure(figsize=(MAP2_W_PX / dpi, MAP2_W_PX * H / W / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    extent = [x_km[0], x_km[-1], y_km[-1], y_km[0]]
    base = np.zeros((H, W, 4))
    base[..., 0] = base[..., 1] = base[..., 2] = 0.32 + 0.38 * hs
    base[..., 3] = np.where(land, 1.0, 0.0)
    ax.imshow(base, extent=extent, aspect="auto", interpolation="bilinear")
    norm = Normalize(vmin=vmin, vmax=vmax)
    rgba = cm.get_cmap(cmap)(norm(np.clip(fld, vmin, vmax)))
    rgba[..., :3] *= (0.55 + 0.45 * hs)[..., None]
    rgba[..., 3] = np.where(np.isfinite(fld) & (mask == 2), 1.0, 0.0)
    ax.imshow(rgba, extent=extent, aspect="auto", interpolation="bilinear")
    ax.contour(x_km, y_km, surf, levels=[contour_m], colors="white",
               linewidths=0.9, alpha=0.85)
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    out = OUT / out_name
    fig.savefig(out, dpi=dpi, transparent=True)
    plt.close(fig)
    from PIL import Image
    im = Image.open(out)
    print(f"wrote {out.name} ({im.size[0]}x{im.size[1]}, {out.stat().st_size / 1e6:.2f} MB, mode {im.mode})")
    # colormap stops for the SVG colorbar
    cmap_obj = cm.get_cmap(cmap)
    stops = [
        {"offset": round(t, 3), "color": matplotlib.colors.to_hex(cmap_obj(t))}
        for t in np.linspace(0, 1, 11)
    ]
    return {"file": out_name, "size": list(im.size), "aspect_h_over_w": im.size[1] / im.size[0],
            "cmap": cmap, "vmin": vmin, "vmax": vmax, "stops": stops}


def check_numbers(cache) -> None:
    """Point checks against the numbers the paper quotes."""
    print("\n── point checks (h 1 km, alpha 0.5 deg, ell 5 km, gamma 0.1, tau_val 30 kPa) ──")
    for n in N_FLOWS:
        acl = acl_point(1000.0, 0.5, 5000.0, 0.1, 30.0, n)
        print(f"  n={n}: [x]={x_bl_closed_form(1000.0, 0.1, n):.0f} m  ACL={acl/1e3:.3f} km")
    # the same through the native-grid formula (B does not cancel symbolically there)
    for n in N_FLOWS:
        h = np.array([1000.0])
        xb = x_bl_for_gamma(h, np.array([0.5]), np.array([True]), 0.1, n)[0]
        print(f"  n={n}: grid-formula [x]={xb:.1f} m (closed form {x_bl_closed_form(1000.0, 0.1, n):.1f})")
    print("  paper line ~417: ~4.7 km for n=3 (4.3 km for n=4)")

    valid = cache["valid"].astype(bool)
    h = cache["h"].astype(float)
    alpha = cache["alpha"].astype(float)
    surf = cache["surf"].astype(float)
    abl = valid & (surf < 1600.0)
    for n, ell_km in [(3, 5), (1, 5), (3, 10), (1, 10)]:
        xb = x_bl_for_gamma(h, alpha, valid, 0.1, n)
        tau = RHO * G * np.radians(alpha) * ell_km * 1e3 / 4 / 1e3
        lam = n ** (-1.0 / (n + 1))
        acl = np.where(valid & (tau > 30.0), xb / lam * np.log(np.maximum(tau, 1e-9) / 30.0), 0.0) / 1e3
        a = acl[abl]
        pos = a[a > 0]
        bins = np.arange(0, 3300, 100)
        med = []
        for lo in bins:
            sel = valid & (surf >= lo) & (surf < lo + 100)
            med.append(np.median(acl[sel]) if sel.sum() > 200 else np.nan)
        med = np.array(med)
        k = int(np.nanargmax(med))
        print(f"  map n={n} ell={ell_km} km gamma=0.1 tau_val=30: below 1600 m -> "
              f"ACL>0 on {100*pos.size/a.size:.0f}% of px; p50={np.median(pos):.2f} "
              f"p90={np.percentile(pos, 90):.2f} p99={np.percentile(pos, 99):.2f} km; "
              f"elevation-binned median peaks at {bins[k]}-{bins[k]+100} m: {med[k]:.2f} km")


def write_qa(cache) -> None:
    """Contact sheet: 4 corner combos + the hero, straight from disk."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    combos = [(10, 2), (10, 20), (30, 10), (100, 2), (100, 20)]
    fig, axs = plt.subplots(2, len(combos), figsize=(4 * len(combos), 6.6),
                            facecolor=PAGE_BG)
    for j, (tv, el) in enumerate(combos):
        a = Image.open(TWINS / f"acl_t{tv:03d}_l{el:02d}.png").convert("RGBA")
        t = Image.open(TWINS / f"taumax_l{el:02d}.png").convert("RGBA")
        axs[0, j].imshow(a)
        axs[0, j].set_title(f"ACL t={tv} l={el}", fontsize=11, color=INK)
        axs[1, j].imshow(t)
        axs[1, j].set_title(f"taumax l={el}", fontsize=11, color=INK)
        for ax in (axs[0, j], axs[1, j]):
            ax.set_xticks([])
            ax.set_yticks([])
    out = OUT / "ch01_twins_grid_qa.png"
    fig.savefig(out, dpi=110, facecolor=PAGE_BG)
    plt.close(fig)
    print(f"wrote {out.name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="n1,n3,maps,maps2,qa,check",
                    help="comma list of: n1 n3 maps maps2 qa check")
    steps = set(ap.parse_args().only.split(","))
    cache = build_cache()
    if "n1" in steps:
        write_grid_tiles(cache, 1)
    if "n3" in steps:
        write_grid_tiles(cache, 3)
    alpha = np.where(cache["valid"], cache["alpha"], np.nan)
    h = np.where(cache["valid"], cache["h"], np.nan)
    if "maps" in steps:
        write_map_fig(cache, alpha, "plasma", 0.0, 1.0,
                      "Along-flow slope", r"$\alpha$  [$^\circ$]",
                      "ch01_alpha_map_fig.png")
        write_map_fig(cache, h, "cividis", 0.0, 3400.0,
                      "Ice thickness", r"$h$  [m]",
                      "ch01_h_map_fig.png")
    if "maps2" in steps:
        meta = {
            "alpha": write_map_fig2(cache, alpha, "plasma", 0.0, 1.0, "ch01_alpha_map_fig2.png"),
            "h": write_map_fig2(cache, h, "cividis", 0.0, 3400.0, "ch01_h_map_fig2.png"),
        }
        (OUT / "twins_map_fig2.json").write_text(json.dumps(meta, indent=2))
        print("wrote twins_map_fig2.json")
    if "qa" in steps and (TWINS / "acl_t010_l02.png").exists():
        write_qa(cache)
    if "check" in steps:
        check_numbers(cache)
    print("\nupload (rclone copy, never sync):\n"
          "  rclone copy cinematic/data/twins r2:<bucket>/ch01/twins --header-upload 'Cache-Control: public, max-age=31536000, immutable'\n"
          "  rclone copyto cinematic/data/ch01_acl_map_n3.png r2:<bucket>/ch01/acl_map_n3.png --header-upload 'Cache-Control: public, max-age=31536000, immutable'\n"
          "  rclone copyto cinematic/data/ch01_acl_map_n3_g05.png r2:<bucket>/ch01/acl_map_n3_g05.png --header-upload 'Cache-Control: public, max-age=31536000, immutable'\n"
          "  rclone copyto cinematic/data/ch01_alpha_map_fig2.png r2:<bucket>/ch01/alpha_map_fig2.png --header-upload 'Cache-Control: public, max-age=31536000, immutable'\n"
          "  rclone copyto cinematic/data/ch01_h_map_fig2.png r2:<bucket>/ch01/h_map_fig2.png --header-upload 'Cache-Control: public, max-age=31536000, immutable'")
