"""
Bake the monthly meltwater RUNOFF over the Introduction's "seasons" region
boxes (the director asked for RACMO runoff laid over the anomaly speed, so
the correlation between more meltwater runoff and faster ice can be seen
directly). The curve panel draws it as quiet bars behind the Russell /
Isunnguata Sermia speed curve.

DATA
    RACMO2.3p2 (ERA5-forced, FGRN055 ~5.5 km), statistically downscaled to
    1 km by B. Noel (IMAU): variable `runoffcorr`, "1km Topography corrected
    runoff", mm w.e. per month, one NetCDF per year, 1990-2023, on the GIMP
    1 km polar-stereographic grid (EPSG:3413; x, y in METRES although the
    file says km, and half a cell NE of the true centres — GRID_SHIFT_M,
    measured against BedMachine's ice margin; the file's LAT/LON variables
    are copies of y/x in km and are not used). Off-ice cells are 0, not NaN.
    Redistributed on Zenodo with Vries et al. (2025):
        Vries, A. L. (2025). Data supporting: "Seasonal and interannual
        variability of freshwater sources for Greenland's fjords" ...
        Zenodo. https://doi.org/10.5281/zenodo.15013761 (CC BY 4.0)
        archive.zip -> Zenodo_data/Monthly_downscaled_runoff_GrIS_GIC/
        runoff.YYYY.BN_RACMO2.3p2_ERA5_3h_FGRN055.1km.MM.nc.gz
    The model and the downscaling:
        Noel, B., et al. (2016). A daily, 1 km resolution data set of
        downscaled Greenland ice sheet surface mass balance (1958-2015).
        The Cryosphere, 10, 2361-2377. https://doi.org/10.5194/tc-10-2361-2016
        Noel, B., van de Berg, W. J., Lhermitte, S., & van den Broeke, M. R.
        (2019). Rapid ablation zone expansion amplifies north Greenland mass
        loss. Science Advances, 5, eaaw0123. https://doi.org/10.1126/sciadv.aaw0123
    The public record ends Dec 2023, so the site's last year (2024) has no
    runoff: null, never filled.

    Fetched (range reads of the Zenodo zip, only the years needed, ~110 MB)
    into cinematic/source_data/racmo/ (gitignored); gunzip -k before a run.

WHAT IS BAKED
    For each region box of bake_velocity_series.REGIONS (EPSG:3413 km, the
    SAME boxes the speed curves and the globe's outlines use), every month
    of the seasons manifest (2015-01 .. 2024-11):
        runoff_mm   area mean over the box's ICE cells (BedMachine v6 mask
                    2/3 at the cell centre), mm w.e. per month
        runoff_gt   the box total, Gt per month (1 mm on 1 km2 = 1e-6 Gt)
    The page plots runoff_mm: the boxes were picked by eye and differ in
    size (40 x 40 km vs 10 x 8 km), so a box total measures the box as much
    as the melt; the area mean is per square metre of ice and comparable.

CHECKS (printed, and qa/runoff_*.png beside the velocity QA)
    · units: the whole-grid sum per year against the Zenodo deposit's own
      section sums (runoff_GrIS...section_sum.nc) and against ~300-500 Gt/yr
    · geolocation: the fraction of cells with runoff that sit on BedMachine
      ice, for grid shifts of -3..+3 km in x and y — the maximum must be at
      zero shift (the 62 km trap: never trust a grid's metadata alone)

OUTPUT -> cinematic/data/intro/seasons/runoff_racmo_v1.json (R2 intro/seasons/)

Run (~1 min):
    cd cinematic
    nice -n 15 python \\
        scene_01_intro/bake_runoff_series.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import xarray as xr

HERE = Path(__file__).resolve().parent
CINEMATIC_DIR = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(CINEMATIC_DIR))
from bake_velocity_series import REGIONS, SITE_REGIONS  # noqa: E402

SRC = CINEMATIC_DIR / "source_data" / "racmo"
BEDMACHINE = CINEMATIC_DIR / "source_data" / "data" / "BedMachineGreenland-v6.nc"
MANIFEST = CINEMATIC_DIR.parent / "website" / ".r2-cache" / "intro" / "seasons" / "manifest.json"
OUT = CINEMATIC_DIR / "data" / "intro" / "seasons"
FILE = "runoff.{y}.BN_RACMO2.3p2_ERA5_3h_FGRN055.1km.MM.nc"
SECTION_SUM = "runoff_GrIS.1990-2023.RACMO2.3p2_ERA5_3h_FGRN055.1km.MM.GrIS.section_sum.nc"
GT_PER_MM_KM2 = 1e-6
# The file's x / y sit half a cell NE of the cell centres: the ice margin
# (runoff cells beside no-runoff cells) matches BedMachine's best at -500 m
# in both x and y (0.838 / 0.850 on ice vs 0.797 unshifted; 2015, 81,661
# margin cells, scanned -1000..+500 m in 250 m steps). Measured, not read
# from the metadata; the check below re-measures it on every run.
GRID_SHIFT_M = (-500.0, -500.0)
SHIFT_SCAN_M = (-500, -250, 0, 250, 500)


_BM: tuple | None = None


def bedmachine_ice_on(xc: np.ndarray, yc: np.ndarray) -> np.ndarray:
    """BedMachine v6 mask (ice = 2 grounded, 3 floating) sampled at the given
    cell centres (EPSG:3413 m), nearest neighbour on its 150 m grid."""
    global _BM
    if _BM is None:
        b = xr.open_dataset(BEDMACHINE)
        _BM = (b.x.values.astype(float), b.y.values.astype(float), b["mask"].values)
    bx, by, m = _BM
    ix = np.clip(np.round((xc - bx[0]) / (bx[1] - bx[0])).astype(int), 0, bx.size - 1)
    iy = np.clip(np.round((yc - by[0]) / (by[1] - by[0])).astype(int), 0, by.size - 1)
    inside = (xc >= bx.min()) & (xc <= bx.max()) & (yc >= by.min()) & (yc <= by.max())
    ice = np.isin(m[iy, ix], (2, 3)) & inside
    return ice


def main() -> None:
    man = json.loads(MANIFEST.read_text())
    months = man["region_months"]                      # "2015-01" .. "2024-11"
    years = sorted({int(m[:4]) for m in months})
    have = [y for y in years if (SRC / FILE.format(y=y)).exists()]
    print(f"months {months[0]}..{months[-1]} ({len(months)}); RACMO years on disk {have}")

    # --- grid + the region cells ------------------------------------------
    g = xr.open_dataset(SRC / FILE.format(y=have[0]))
    x = g.x.values.astype(float) + GRID_SHIFT_M[0]
    y = g.y.values.astype(float) + GRID_SHIFT_M[1]
    assert abs(x[1] - x[0] - 1000) < 1 and abs(y[1] - y[0] - 1000) < 1, "expected a 1 km grid in metres"
    cells = {}
    for k, r in REGIONS.items():
        x0, x1, y0, y1 = (v * 1e3 for v in r["box"])
        cx = np.where((x > x0) & (x < x1))[0]
        cy = np.where((y > y0) & (y < y1))[0]
        XX, YY = np.meshgrid(x[cx], y[cy])
        ice = bedmachine_ice_on(XX.ravel(), YY.ravel()).reshape(XX.shape)
        cells[k] = dict(sx=slice(cx[0], cx[-1] + 1), sy=slice(cy[0], cy[-1] + 1), ice=ice)
        print(f"  {k:24s} {XX.shape[1]} x {XX.shape[0]} cells, ice {ice.mean():.3f}")

    # --- geolocation check: margin cells on BedMachine ice vs grid shift ---
    # The cells with runoff that touch a no-runoff cell ARE the ice margin;
    # the fraction of them BedMachine calls ice peaks where the grid sits.
    ann = xr.open_dataset(SRC / FILE.format(y=have[0]))["runoffcorr"].values.sum(0)
    wet = ann > 1.0
    pad = np.pad(wet, 1)
    edge = wet & ((~pad[:-2, 1:-1]) | (~pad[2:, 1:-1]) | (~pad[1:-1, :-2]) | (~pad[1:-1, 2:]))
    YI, XI = np.nonzero(edge)
    xc, yc = x[XI], y[YI]
    shift = {}
    for d in SHIFT_SCAN_M:
        shift[f"dx{d:+d}"] = float(bedmachine_ice_on(xc + d, yc).mean())
        shift[f"dy{d:+d}"] = float(bedmachine_ice_on(xc, yc + d).mean())
    best_x = max(SHIFT_SCAN_M, key=lambda d: shift[f"dx{d:+d}"])
    best_y = max(SHIFT_SCAN_M, key=lambda d: shift[f"dy{d:+d}"])
    print(f"  geolocation ({edge.sum()} margin cells, after the {GRID_SHIFT_M} m correction): on ice "
          f"{shift['dx+0']:.4f} at 0; best dx {best_x:+d} m, dy {best_y:+d} m")
    print("   ", {k: round(v, 4) for k, v in sorted(shift.items())})
    assert best_x == 0 and best_y == 0, "RACMO grid is not where the corrected EPSG:3413 coords say — stop"

    # --- the series ---------------------------------------------------------
    by_month: dict[str, dict] = {}
    grid_sum = {}
    for yr in have:
        ds = xr.open_dataset(SRC / FILE.format(y=yr))
        ro = ds["runoffcorr"]
        times = [str(t)[:7] for t in ro.time.values]
        grid_sum[yr] = float(ro.sum(("x", "y")).values.sum() * GT_PER_MM_KM2)
        for ti, ym in enumerate(times):
            a = ro.isel(time=ti).values
            rec = {}
            for k, c in cells.items():
                sub = a[c["sy"], c["sx"]]
                v = sub[c["ice"]]
                rec[k] = (float(v.mean()), float(v.sum() * GT_PER_MM_KM2)) if v.size else (None, None)
            by_month[ym] = rec
        print(f"  {yr}: whole grid {grid_sum[yr]:.0f} Gt/yr (GrIS + peripheral glaciers)")

    # the deposit's own GrIS sums (7 sections) for the same years
    try:
        s = xr.open_dataset(SRC / SECTION_SUM)
        tt = np.array([str(t)[:4] for t in s.time.values])
        gris = s["runoffcorr"].values                  # (section, time), mm-sum over cells
        for yr in have:
            tot = float(gris[:, tt == str(yr)].sum() * GT_PER_MM_KM2)
            print(f"    deposit GrIS section sum {yr}: {tot:.0f} Gt/yr")
    except Exception as e:  # noqa: BLE001
        print("  (section sums not read:", e, ")")

    regions = {}
    for k in SITE_REGIONS + tuple(kk for kk in REGIONS if kk not in SITE_REGIONS):
        mm = [None if ym not in by_month else round(by_month[ym][k][0], 1) for ym in months]
        gt = [None if ym not in by_month else round(by_month[ym][k][1], 4) for ym in months]
        yrs = {}
        for yr in have:
            vals = [(v, ym) for v, ym in zip(mm, months) if ym[:4] == str(yr) and v is not None]
            if len(vals) == 12:
                pk, pm = max(vals)
                jan = next(v for v, ym in vals if ym[5:] == "01")
                yrs[str(yr)] = dict(total_mm=round(sum(v for v, _ in vals), 0), peak_mm=pk,
                                    peak_month=pm[5:], jan_mm=jan)
        c = cells[k]
        regions[k] = dict(label=REGIONS[k]["label"], kind=REGIONS[k]["kind"], site=k in SITE_REGIONS,
                          box_epsg3413_km=REGIONS[k]["box"], n_cells=int(c["ice"].size),
                          ice_fraction=round(float(c["ice"].mean()), 3),
                          runoff_mm=mm, runoff_gt=gt, by_year=yrs)

    out = dict(
        model="RACMO2.3p2",
        label="runoff · RACMO2.3p2",
        product="RACMO2.3p2 (ERA5, FGRN055) statistically downscaled to 1 km (B. Noel, IMAU): "
                "'runoffcorr', 1 km topography-corrected runoff, monthly",
        source="Zenodo doi:10.5281/zenodo.15013761 (Vries 2025, CC BY 4.0), "
               "Zenodo_data/Monthly_downscaled_runoff_GrIS_GIC/runoff.YYYY.BN_RACMO2.3p2_ERA5_3h_FGRN055.1km.MM.nc.gz",
        citation=[
            "Vries, A. L. (2025). Data supporting: \"Seasonal and interannual variability of freshwater "
            "sources for Greenland's fjords\". Zenodo. https://doi.org/10.5281/zenodo.15013761",
            "Noel, B., et al. (2016). A daily, 1 km resolution data set of downscaled Greenland ice "
            "sheet surface mass balance (1958-2015). The Cryosphere, 10, 2361-2377. "
            "https://doi.org/10.5194/tc-10-2361-2016",
            "Noel, B., van de Berg, W. J., Lhermitte, S., & van den Broeke, M. R. (2019). Rapid "
            "ablation zone expansion amplifies north Greenland mass loss. Science Advances, 5, "
            "eaaw0123. https://doi.org/10.1126/sciadv.aaw0123",
        ],
        units=dict(runoff_mm="mm w.e. per month (area mean over the box's ice cells)",
                   runoff_gt="Gt per month (box total)"),
        definition="the seasons manifest's region boxes (EPSG:3413); ice = BedMachine v6 mask 2/3 at "
                   "the 1 km cell centre; null where RACMO has no month (after 2023-12)",
        date_range=[min(by_month), max(by_month)],
        months=months,
        checks=dict(grid_total_gt_per_yr={str(k): round(v) for k, v in grid_sum.items()},
                    geolocation_on_ice_by_shift_km={k: round(v, 4) for k, v in shift.items()}),
        regions=regions,
    )
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "runoff_racmo_v1.json"
    p.write_text(json.dumps(out, separators=(",", ":")))
    print(f"wrote {p} ({p.stat().st_size / 1e3:.1f} kB)")
    for k in SITE_REGIONS:
        for yr, d in regions[k]["by_year"].items():
            print(f"  {k:20s} {yr} total {d['total_mm']:6.0f} mm  peak {d['peak_mm']:6.1f} ({d['peak_month']})"
                  f"  Jan {d['jan_mm']:.1f}")
    qa(man, out)


def qa(man: dict, out: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    qd = OUT / "qa"
    qd.mkdir(parents=True, exist_ok=True)
    months = man["region_months"]
    t = np.arange(len(months))
    fig, axs = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    for ax, k in zip(axs, SITE_REGIONS):
        sp = man["regions"][k]["speed"]
        ro = [np.nan if v is None else v for v in out["regions"][k]["runoff_mm"]]
        ax2 = ax.twinx()
        ax2.bar(t, ro, color="#5aa9e6", alpha=0.5, width=0.8)
        ax2.set_ylabel("runoff mm w.e./month")
        ax.plot(t, sp, color="#c9a227", lw=2, zorder=5)
        ax.set_zorder(ax2.get_zorder() + 1)
        ax.patch.set_visible(False)
        ax.set_ylabel("speed m/yr")
        ax.set_title(f"{man['regions'][k]['label']}: NSIDC-0731 speed vs RACMO2.3p2 runoff")
    axs[-1].set_xticks(t[::12])
    axs[-1].set_xticklabels([m[:4] for m in months[::12]])
    plt.tight_layout()
    plt.savefig(qd / "runoff_vs_speed.png", dpi=80)
    plt.close(fig)
    print("qa ->", qd / "runoff_vs_speed.png")


if __name__ == "__main__":
    main()
