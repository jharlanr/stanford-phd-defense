"""Build the Ch.1 ACL + max-surface-stress Greenland maps.

Evaluates the JOG paper's eq. (48) (absolute coupling length) and the
max-stress definition max tau_xx = rho*g*alpha*ell/4 at every GrIS
pixel — figureA1_grispaint.ipynb's method, but with the CHAPTER's
parameters (Newtonian n=1, the hero patch ell=10 km, gamma=0.1,
tau_val=30 kPa) so the maps continue the n=1 story the derivation
beats just told. (The paper's fig. A1 uses n=3, ell=5 km — the
patterns are the same; the paper says ACL is only weakly sensitive
to n.)

Outputs (cinematic/data/):
  ch01_acl_map.png           drape texture for the 3D globe
                             (PlateCarree frame matching Globe.vue's
                             makeGreenlandPatch; turbo, 0..15 km;
                             alpha ramps in so the sub-threshold
                             interior stays transparent — that is what
                             reads as "white" over the snow dome).
  ch01_stress_map.png        drape texture for the max-stress twin
                             globe (inferno, 0..300 kPa, fully opaque
                             over the valid ice mask — fig A1b's look).
  ch01_acl_stress_panel.png  full-screen side-by-side panel, fig-A1
                             layout on the site's dark chalkboard:
                             (a) ACL [km] turbo · (b) max tau_xx [kPa]
                             inferno, over gray hillshade, 1600 m
                             contour, big colorbars.
  ch01_acl_maps_qa.png       QA quicklook.

Inputs (local copies only — bash cinematic/fetch_sources.sh):
  source_data/data/BedMachineGreenland-v6.nc
  source_data/data/ITS_LIVE_velocity_120m_RGI05A_0000_V02.1.nc

Run:  python -u cinematic/scene_ch01/build_acl_maps.py
Then:
  rclone copyto cinematic/data/ch01_acl_map.png r2:<bucket>/ch01/acl_map.png --header-upload 'Cache-Control: public, max-age=31536000, immutable'
  rclone copyto cinematic/data/ch01_acl_stress_panel.png r2:<bucket>/ch01/acl_stress_panel.png --header-upload 'Cache-Control: public, max-age=31536000, immutable'
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared import BEDMACHINE_PATH, SOURCE_DATA, require_source  # noqa: E402

sys.stdout.reconfigure(line_buffering=True)

ITSLIVE_PATH = SOURCE_DATA / "data" / "ITS_LIVE_velocity_120m_RGI05A_0000_V02.1.nc"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vendor"))
from bedmachine_gris_density import build_grid_state  # noqa: E402

# ── Physics — the CHAPTER's n=1 hero parameters ────────────────────────
RHO, G = 917.0, 9.81
N_FLOW = 1
ETA = 1e14                      # [Pa s] — same as build_theory_n1.py
A_RATE = 1.0 / (2.0 * ETA)      # 5e-15 Pa^-1 s^-1
GAMMA = 0.1
ELL = 10000.0                   # hero patch length [m]
TAU_VAL = 30.0                  # fracture threshold [kPa]

# ── Drape texture frame: must match Globe.vue's makeGreenlandPatch ────
LON_W, LON_E = -75.0, -10.0
LAT_S, LAT_N = 59.0, 84.0
TEX_W, TEX_H = 5200, 2000

# ── Styling ────────────────────────────────────────────────────────────
ACL_CMAP, ACL_VMAX_KM = "turbo", 15.0     # fig-A1a is jet; turbo = same
                                          # ramp, perceptually smoother
STRESS_CMAP, STRESS_VMAX_KPA = "inferno", 300.0
ALPHA_FULL_KM = 2.0
MAX_ALPHA = 0.88
PAGE_BG = "#0a0908"
INK = "#f5f0e6"
GOLD = "#f5c75e"

OUT = Path(__file__).resolve().parents[1] / "data"
OUT.mkdir(exist_ok=True)


def compute_grids():
    """ACL [km] + max stress [kPa] on the BedMachine 1.5 km grid."""
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
        print(f"filled {no_flow.sum():,} stagnant pixels with |∇s| fallback")

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

    tau_max = np.full_like(h, np.nan)
    tau_max[valid] = RHO * G * a_rad[valid] * ELL / 4 / 1e3  # [kPa]

    lam = n ** (-1.0 / (n + 1))  # = 1 for n=1
    acl = np.full_like(h, np.nan)
    above = valid & (tau_max > TAU_VAL)
    acl[above] = (x_bl[above] / lam) * np.log(tau_max[above] / TAU_VAL) / 1e3
    acl[valid & ~above] = 0.0
    print(
        f"n={n} ell={ELL/1e3:g} km: valid={valid.sum():,} px, "
        f"above tau_val={above.sum():,} px, ACL p50={np.nanmedian(acl[above]):.2f} km, "
        f"p99={np.nanpercentile(acl[above], 99):.2f} km, "
        f"stress p50={np.nanmedian(tau_max[valid]):.0f} kPa, "
        f"p99={np.nanpercentile(tau_max[valid], 99):.0f} kPa"
    )
    return dict(acl=acl, tau_max=tau_max, valid=valid, surf=surf,
                mask=mask, x=grid["x"], y=grid["y"], dx=grid["dx"])


def _to_platecarree(g, field):
    """Reproject an EPSG:3413 grid to the globe-patch PlateCarree frame."""
    from pyproj import Transformer
    from scipy.interpolate import RegularGridInterpolator

    y_asc = g["y"][::-1]
    interp = RegularGridInterpolator(
        (y_asc, g["x"]), field[::-1, :], method="linear",
        bounds_error=False, fill_value=np.nan,
    )
    lons = np.linspace(LON_W, LON_E, TEX_W)
    lats = np.linspace(LAT_N, LAT_S, TEX_H)
    lon2, lat2 = np.meshgrid(lons, lats)
    tr = Transformer.from_crs("EPSG:4326", "EPSG:3413", always_xy=True)
    px, py = tr.transform(lon2, lat2)
    return interp(np.stack([py.ravel(), px.ravel()], axis=-1)).reshape(TEX_H, TEX_W)


def write_drape(g) -> None:
    """Reproject ACL to the PlateCarree globe-patch frame → RGBA drape."""
    from PIL import Image
    from matplotlib import cm

    acl_ll = _to_platecarree(g, g["acl"])
    norm = np.clip(acl_ll / ACL_VMAX_KM, 0, 1)
    rgba = cm.get_cmap(ACL_CMAP)(norm)
    alpha = np.clip(acl_ll / ALPHA_FULL_KM, 0, 1) * MAX_ALPHA
    alpha[~np.isfinite(acl_ll)] = 0.0
    rgba[..., 3] = alpha
    out = OUT / "ch01_acl_map.png"
    Image.fromarray((rgba * 255).astype(np.uint8)).save(out, optimize=True)
    print(f"wrote {out.name} ({out.stat().st_size / 1e6:.1f} MB)")


def write_stress_drape(g) -> None:
    """Max-stress drape for the twin-globes closer (fig A1b's inferno).

    Unlike the ACL drape, this one is (nearly) fully opaque across the
    valid ice mask — on fig A1b the whole sheet is colored, with the
    low-stress interior reading dark. A soft alpha ramp over the first
    few kPa just anti-aliases the mask edge.
    """
    from PIL import Image
    from matplotlib import cm

    tau_ll = _to_platecarree(g, g["tau_max"])
    norm = np.clip(tau_ll / STRESS_VMAX_KPA, 0, 1)
    rgba = cm.get_cmap(STRESS_CMAP)(norm)
    alpha = np.where(np.isfinite(tau_ll), MAX_ALPHA + 0.06, 0.0)
    rgba[..., 3] = alpha
    out = OUT / "ch01_stress_map.png"
    Image.fromarray((rgba * 255).astype(np.uint8)).save(out, optimize=True)
    print(f"wrote {out.name} ({out.stat().st_size / 1e6:.1f} MB)")


def write_panel(g) -> None:
    """Side-by-side fig-A1-style panel on the site's dark chalkboard."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import cm
    from matplotlib.colors import LightSource, Normalize

    x_km, y_km = g["x"] / 1e3, g["y"] / 1e3
    extent = [x_km[0], x_km[-1], y_km[-1], y_km[0]]

    # Gray hillshade base wherever there is land/ice; dark page elsewhere.
    surf = np.where(np.isfinite(g["surf"]), g["surf"], 0.0)
    hs = LightSource(azdeg=315, altdeg=45).hillshade(surf, vert_exag=0.02, dx=g["dx"], dy=g["dx"])
    land = g["mask"] > 0

    plt.rcParams.update({
        "font.family": "serif", "text.color": INK,
        "axes.edgecolor": INK, "xtick.color": INK, "ytick.color": INK,
    })
    fig, axs = plt.subplots(1, 2, figsize=(17.6, 10.2), facecolor=PAGE_BG)
    panels = [
        ("Absolute coupling length", g["acl"], ACL_CMAP, 0, ACL_VMAX_KM,
         "ACL  [km]"),
        ("Maximum surface stress", g["tau_max"], STRESS_CMAP, 0, STRESS_VMAX_KPA,
         r"max $\tau_{xx}=\rho g \alpha \ell/4$  [kPa]"),
    ]
    for ax, (title, field, cmap, vmin, vmax, cbar_label) in zip(axs, panels):
        ax.set_facecolor(PAGE_BG)
        base = np.zeros((*hs.shape, 4))
        base[..., 0] = base[..., 1] = base[..., 2] = 0.32 + 0.38 * hs
        base[..., 3] = np.where(land, 1.0, 0.0)
        ax.imshow(base, extent=extent, aspect="equal", interpolation="bilinear")

        norm = Normalize(vmin=vmin, vmax=vmax)
        rgba = cm.get_cmap(cmap)(norm(np.clip(field, vmin, vmax)))
        shade = (0.55 + 0.45 * hs)[..., None]
        rgba[..., :3] *= shade
        rgba[..., 3] = np.where(np.isfinite(field), 1.0, 0.0)
        ax.imshow(rgba, extent=extent, aspect="equal", interpolation="bilinear")

        # 1600 m contour — the approximate upper bound of current lakes.
        ax.contour(x_km, y_km, surf, levels=[1600], colors="white",
                   linewidths=0.7, alpha=0.85)

        ax.set_title(title, fontsize=26, color=GOLD, pad=16)
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)

        sm = cm.ScalarMappable(cmap=cmap, norm=norm)
        cb = fig.colorbar(sm, ax=ax, fraction=0.045, pad=0.02, shrink=0.86)
        cb.set_label(cbar_label, fontsize=17, color=INK)
        cb.ax.tick_params(labelsize=14, colors=INK)
        cb.outline.set_edgecolor("#777")

    fig.text(0.5, 0.028,
             r"1-D boundary-layer model on BedMachine v6 + ITS_LIVE  ·  "
             r"$n=1$ · $\ell=10$ km · $\gamma=0.1$ · $\tau_{val}=30$ kPa  ·  "
             "white contour: 1600 m (approx. upper bound of lakes)",
             ha="center", fontsize=15, color="#c9c2b4")
    fig.subplots_adjust(left=0.01, right=0.945, top=0.94, bottom=0.06, wspace=0.12)
    out = OUT / "ch01_acl_stress_panel.png"
    fig.savefig(out, dpi=150, facecolor=PAGE_BG)
    plt.close(fig)
    print(f"wrote {out.name} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    g = compute_grids()
    write_drape(g)
    write_stress_drape(g)
    write_panel(g)
    print("\nupload:\n"
          "  rclone copyto cinematic/data/ch01_acl_map.png r2:<bucket>/ch01/acl_map.png --header-upload 'Cache-Control: public, max-age=31536000, immutable'\n"
          "  rclone copyto cinematic/data/ch01_stress_map.png r2:<bucket>/ch01/stress_map.png --header-upload 'Cache-Control: public, max-age=31536000, immutable'\n"
          "  rclone copyto cinematic/data/ch01_acl_stress_panel.png r2:<bucket>/ch01/acl_stress_panel.png --header-upload 'Cache-Control: public, max-age=31536000, immutable'")
