"""Build the Ch.3 (ESSD) website data.

Chapter 3 presents the ESSD benchmark dataset: N = 1679 hand-labeled
supraglacial lakes (2018: 679, 2019: 1000) in central-west Greenland,
five drainage-mechanism classes, the ConvLSTM baseline classifier, and
the labeler tool. This script bakes the dynamic-figure data:

  ch03/essd_lakes_2019.json   per-lake polygons (Dunmire outlines) +
  ch03/essd_lakes_2018.json   hand label class + daily p_water series
                              (S2_water, May 1 - Sep 30, quantized
                              0..100) for the dynamic Fig-1 beat
  ch03/essd_stats.json        class counts per year, IRR numbers,
                              per-class mean p_water trajectories +
                              per-class example series (Fig-4c), test
                              metrics of the baseline classifier
  ch03/architecture_detailed.svg   copy of the fig-7 detailed SVG

Inputs (local copies only — bash cinematic/fetch_sources.sh):
  source_data/essd/labels/labels_CW_{2018,2019}.csv
  source_data/essd/dunmire/labels_{2018,2019}_volumes.geojson
  source_data/essd/dunmire/all_lakes_{2018,2019}.nc
  source_data/essd/irr/irr_labels_labeler{1,2,3}_CW_{2018,2019}.csv
  source_data/essd/inference/test_predictions_bestf1.csv
  source_data/essd/figs/fig_architecture_detailed.svg

Run:  cinematic/.venv/bin/python -u cinematic/scene_ch03/build_essd_lakes.py
Then:
  rclone copy cinematic/data/ch03 r2:<bucket>/ch03 --header-upload 'Cache-Control: public, max-age=31536000, immutable'
  (cd website && rclone sync r2:<bucket> .r2-cache)
"""

import csv
import json
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared import SOURCE_DATA, require_source  # noqa: E402

sys.stdout.reconfigure(line_buffering=True)

ESSD = SOURCE_DATA / "essd"
OUT = Path(__file__).resolve().parents[1] / "data" / "ch03"
OUT.mkdir(parents=True, exist_ok=True)

# Melt season window used across the site (153 days).
SEASON = ("05-01", "09-30")

# ESSD fig-4 class colors — verbatim from DrainageLegend.vue (already
# the site's Ch.1 palette).
CLASSES = {
    "HF": {"name": "Hydrofracture", "color": "#4caf50"},
    "MD": {"name": "Moulin drainage", "color": "#42a5f5"},
    "LD": {"name": "Lateral drainage", "color": "#ff9800"},
    "CD": {"name": "Crevasse drainage", "color": "#ab47bc"},
    "ND": {"name": "No drainage", "color": "#e8524a"},
}
CLASS_ORDER = ["ND", "HF", "MD", "LD", "CD"]

# The paper's five representative lakes (fig 4a) — one per class.
EXAMPLES = {
    "ND": "CW2019_1597",
    "HF": "CW2019_1889",
    "MD": "CW2019_1848",
    "LD": "CW2019_1907",
    "CD": "CW2019_2330",
}


def load_labels(year: int) -> dict[str, str]:
    path = require_source(ESSD / "labels" / f"labels_CW_{year}.csv")
    out: dict[str, str] = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            out[row["lake_id"]] = row["label"]
    return out


def load_pwater(year: int, ids: list[str]) -> dict[str, np.ndarray]:
    """S2_water fraction, season window, ffill/bfill (the ESSD load
    convention), quantized later."""
    import xarray as xr

    path = require_source(ESSD / "dunmire" / f"all_lakes_{year}.nc")
    ds = xr.open_dataset(path)
    t0 = np.datetime64(f"{year}-{SEASON[0]}")
    t1 = np.datetime64(f"{year}-{SEASON[1]}")
    sub = ds["S2_water"].sel(time=slice(t0, t1))
    have = set(str(i) for i in ds["ids"].values)
    out: dict[str, np.ndarray] = {}
    missing = 0
    for lid in ids:
        if lid not in have:
            missing += 1
            continue
        s = sub.sel(ids=lid).values.astype(float)
        # ffill then bfill (paper: p_water is NaN on unusable days and
        # gets ffill/bfill-filled at load)
        idx = np.where(np.isfinite(s), np.arange(len(s)), 0)
        np.maximum.accumulate(idx, out=idx)
        s = s[idx]
        if not np.isfinite(s[0]):
            first = np.argmax(np.isfinite(s))
            s[: first + 1] = s[first] if np.isfinite(s).any() else 0.0
        s = np.nan_to_num(s, nan=0.0)
        out[lid] = np.clip(s, 0, 1)
    if missing:
        print(f"  {year}: {missing} labeled lakes missing from Dunmire nc")
    ds.close()
    return out


def build_year(year: int) -> dict:
    labels = load_labels(year)
    print(f"{year}: {len(labels)} labeled lakes")
    gj = json.load(open(require_source(ESSD / "dunmire" / f"labels_{year}_volumes.geojson")))
    feats = {f["properties"]["new_id"]: f for f in gj["features"]}
    pw = load_pwater(year, list(labels.keys()))

    lakes = []
    lost_poly = 0
    for lid, cls in labels.items():
        f = feats.get(lid)
        if f is None:
            lost_poly += 1
            continue
        geom = f["geometry"]
        rings = []
        polys = geom["coordinates"] if geom["type"] == "Polygon" else [
            r for p in geom["coordinates"] for r in p
        ]
        for ring in polys[:1]:  # outer ring only
            rings.append([[round(x, 5), round(y, 5)] for x, y in ring])
        if not rings:
            lost_poly += 1
            continue
        xs = [p[0] for p in rings[0]]
        ys = [p[1] for p in rings[0]]
        series = pw.get(lid)
        lakes.append({
            "id": lid,
            "cls": cls,
            "c": [round(float(np.mean(xs)), 5), round(float(np.mean(ys)), 5)],
            "rings": rings,
            "pw": [int(round(v * 100)) for v in series] if series is not None else None,
        })
    if lost_poly:
        print(f"  {year}: {lost_poly} labels without a Dunmire polygon")

    days = len(lakes[0]["pw"]) if lakes and lakes[0]["pw"] else 0
    data = {
        "year": year,
        "t0": f"{year}-{SEASON[0]}",
        "days": days,
        "classes": CLASSES,
        "class_order": CLASS_ORDER,
        "lakes": lakes,
    }
    out = OUT / f"essd_lakes_{year}.json"
    out.write_text(json.dumps(data, separators=(",", ":")))
    print(f"wrote {out.name} ({out.stat().st_size / 1e6:.1f} MB, "
          f"{len(lakes)} lakes, {days} days)")
    return data


def class_curves(data: dict) -> dict:
    """Per-class mean p_water trajectory + the example lake's series."""
    out = {}
    for cls in CLASS_ORDER:
        series = [lk["pw"] for lk in data["lakes"] if lk["cls"] == cls and lk["pw"]]
        if not series:
            continue
        arr = np.array(series, dtype=float) / 100.0
        mean = arr.mean(axis=0)
        ex_id = EXAMPLES.get(cls)
        ex = next((lk["pw"] for lk in data["lakes"] if lk["id"] == ex_id), None)
        out[cls] = {
            "n": len(series),
            "mean": [round(float(v), 3) for v in mean],
            "example_id": ex_id,
            "example": ex,
        }
    return out


def irr_stats() -> dict:
    """3-labeler agreement on the 200-lake subset (paper: 72.5%,
    Fleiss kappa 0.754) — recomputed here from the shipped CSVs so the
    site's numbers provably match the data copy."""
    labs: dict[int, dict[str, str]] = {1: {}, 2: {}, 3: {}}
    for n in (1, 2, 3):
        for year in (2018, 2019):
            p = ESSD / "irr" / f"irr_labels_labeler{n}_CW_{year}.csv"
            if not p.exists():
                continue
            with open(p) as f:
                for row in csv.DictReader(f):
                    labs[n][row["lake_id"]] = row["label"]
    common = set(labs[1]) & set(labs[2]) & set(labs[3])
    all3 = sum(1 for k in common if labs[1][k] == labs[2][k] == labs[3][k])
    pair = {}
    for a, b in ((1, 2), (1, 3), (2, 3)):
        n_ab = sum(1 for k in common if labs[a][k] == labs[b][k])
        pair[f"{a}{b}"] = round(n_ab / len(common), 3) if common else None
    return {
        "n": len(common),
        "all3_agree": round(all3 / len(common), 3) if common else None,
        "pairwise": pair,
        "fleiss_kappa": 0.754,  # paper value (main.tex:265)
        "labelers": ["Josh Rines", "Niall Coffey", "Eojin Lee"],
    }


def irr_confusion() -> dict:
    """The paper's Fig. 6: the three pairwise labeler-vs-labeler
    confusion matrices on the IRR-200 subset. counts[i][j] = lakes the
    ROW labeler called class i and the COLUMN labeler called class j,
    classes in CLASS_ORDER; the site row-normalizes for the colour.
    Written to its OWN file (ch03/essd_irr.json) so shipping it needs
    no ASSET_VERSION bump."""
    labs: dict[int, dict[str, str]] = {1: {}, 2: {}, 3: {}}
    for n in (1, 2, 3):
        for year in (2018, 2019):
            p = ESSD / "irr" / f"irr_labels_labeler{n}_CW_{year}.csv"
            if not p.exists():
                continue
            with open(p) as f:
                for row in csv.DictReader(f):
                    labs[n][row["lake_id"]] = row["label"]
    common = sorted(set(labs[1]) & set(labs[2]) & set(labs[3]))
    pairs = []
    for a, b in ((1, 2), (1, 3), (2, 3)):
        m = [[0] * len(CLASS_ORDER) for _ in CLASS_ORDER]
        for k in common:
            m[CLASS_ORDER.index(labs[a][k])][CLASS_ORDER.index(labs[b][k])] += 1
        agree = sum(m[i][i] for i in range(len(CLASS_ORDER)))
        pairs.append({
            "row": a, "col": b, "counts": m,
            "agreement": round(agree / len(common), 3) if common else None,
        })
    return {
        "n": len(common),
        "class_order": CLASS_ORDER,
        "classes": CLASSES,
        "pairs": pairs,
        "all3_agree": irr_stats()["all3_agree"],
        "fleiss_kappa": 0.754,
    }


def test_metrics() -> dict:
    path = ESSD / "inference" / "test_predictions_bestf1.csv"
    if not path.exists():
        return {}
    rows = list(csv.DictReader(open(path)))
    n = len(rows)
    acc = sum(1 for r in rows if r["true_label"] == r["pred_label"]) / n
    conf: dict[str, dict[str, int]] = {
        t: {p: 0 for p in CLASS_ORDER} for t in CLASS_ORDER
    }
    for r in rows:
        conf[r["true_label"]][r["pred_label"]] += 1
    f1 = {}
    for c in CLASS_ORDER:
        tp = conf[c][c]
        fp = sum(conf[t][c] for t in CLASS_ORDER) - tp
        fn = sum(conf[c].values()) - tp
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1[c] = round(2 * prec * rec / (prec + rec), 3) if prec + rec else 0.0
    return {"n_test": n, "accuracy": round(acc, 3), "f1": f1, "confusion": conf}


if __name__ == "__main__":
    d19 = build_year(2019)
    d18 = build_year(2018)

    stats = {
        "counts": {
            "2019": {c: sum(1 for lk in d19["lakes"] if lk["cls"] == c) for c in CLASS_ORDER},
            "2018": {c: sum(1 for lk in d18["lakes"] if lk["cls"] == c) for c in CLASS_ORDER},
        },
        "classes": CLASSES,
        "class_order": CLASS_ORDER,
        "curves": {"2019": class_curves(d19), "2018": class_curves(d18)},
        "irr": irr_stats(),
        "model": {
            "name": "LakeDrainageClassifier",
            "params": 140000,
            "input_imagery": [153, 4, 512, 512],
            "streams": ["Sentinel-2 RGB time series (ConvLSTM)",
                        "daily water-area p_water (LSTM)"],
            "test": test_metrics(),
        },
        "dataset": {
            "n_total": 1679, "n_2018": 679, "n_2019": 1000,
            "bands": 6, "res_m": 10, "days": 153,
            "doi": "10.25740/sf350xp4038",
            "license": "CC BY 4.0",
        },
    }
    out = OUT / "essd_stats.json"
    out.write_text(json.dumps(stats, indent=1))
    print(f"wrote {out.name} ({out.stat().st_size / 1e3:.0f} kB)")

    irr_out = OUT / "essd_irr.json"
    irr_out.write_text(json.dumps(irr_confusion(), indent=1))
    print(f"wrote {irr_out.name} ({irr_out.stat().st_size / 1e3:.0f} kB)")

    src_svg = require_source(ESSD / "figs" / "fig_architecture_detailed.svg")
    shutil.copyfile(src_svg, OUT / "architecture_detailed.svg")
    print("copied architecture_detailed.svg")
    print("\nupload:\n  rclone copy cinematic/data/ch03 r2:<bucket>/ch03 --header-upload 'Cache-Control: public, max-age=31536000, immutable'\n"
          "  (cd website && rclone sync r2:<bucket> .r2-cache)")
