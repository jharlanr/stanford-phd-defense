"""Bake Ch.3's TRAINING segment: the ESSD revision's training curves and
confusion matrices (manuscript version 3, Appendix B: Fig. B2, Fig. B3,
Table B2) as ONE small JSON the site animates.

What is real per epoch, and what is not:
  * loss + macro-F1 (train, val)      every epoch 1..400   (metrics JSON)
  * per-class F1 (train, val)         epochs 1, 10, 20..400 (metrics JSON)
  * confusion matrices at the best-validation checkpoint, train/val/test
                                      from the prediction CSVs (= Fig. B3)
  * confusion matrices every 10 epochs (train + val) ONLY if the training
    logs have been copied to source_data/essd/revision/logs/ — the trainer
    (lake-vision f73f3bf, engine/training/run_training.py) printed them at
    epoch 1 and every 10th epoch. They live on the cluster storage; without them the JSON's
    `confusion_by_epoch` is empty and the site shows matrices only at the
    best epoch. Nothing is interpolated or invented.

Every number the site shows at rest is recomputed here from the CSVs and
ASSERTED against the paper (Table B2, Fig. B3 cell for cell, Sect. 5 text).

Inputs (local copies only — bash cinematic/fetch_sources.sh; READ-ONLY):
  source_data/essd/revision/metrics_rev_y2019_{5c,4c}_pw_noaug.json
  source_data/essd/revision/essd_CW_2019only/{train,val,test}_ids.json
  source_data/essd/inference/inference_essd/essd_revision/
        y2019_{5c,4c}_{pw,nopw}_noaug_{train,val,test}_predictions_bestf1.csv
  source_data/essd/checkpoints/essd_revision/*_bestf1.pth   (epoch, metrics)
  source_data/essd/revision/logs/lv_essd_rev_44279083_{1,5}.out  (optional)

Run (torch for the checkpoints — the cinematic venv has none; use a Python env with torch installed):
  python cinematic/scene_ch03/build_training_dynamics.py
Then:
  rclone copy cinematic/data/ch03/training r2:<bucket>/ch03/training --header-upload 'Cache-Control: public, max-age=31536000, immutable'
  cp cinematic/data/ch03/training/training_dynamics_v2.json <main>/website/.r2-cache/ch03/training/
"""

import csv
import json
import re
import sys
from pathlib import Path

import numpy as np

CINEMATIC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CINEMATIC))
from shared import SOURCE_DATA, require_source  # noqa: E402

ESSD = SOURCE_DATA / "essd"
REV = ESSD / "revision"
INF = ESSD / "inference" / "inference_essd" / "essd_revision"
CKPT = ESSD / "checkpoints" / "essd_revision"
LOGS = REV / "logs"
OUT = CINEMATIC / "data" / "ch03" / "training"

SPLITS = ("train", "val", "test")
RUNS = {  # key -> (run name, class order, random-guess macro-F1)
    "5c": ("y2019_5c_pw_noaug", ["ND", "HF", "MD", "LD", "CD"], 0.20),
    "4c": ("y2019_4c_pw_noaug", ["ND", "HFMD", "LD", "CD"], 0.25),
}
ABLATION = [  # Table B2's four cells: (run, classes, p_water)
    ("y2019_5c_pw_noaug", 5, True),
    ("y2019_5c_nopw_noaug", 5, False),
    ("y2019_4c_pw_noaug", 4, True),
    ("y2019_4c_nopw_noaug", 4, False),
]
COLORS = {"ND": "#e8524a", "HF": "#4caf50", "MD": "#42a5f5", "LD": "#ff9800",
          "CD": "#ab47bc", "HFMD": "#26a69a"}  # HFMD = Fig. B2's own teal

# ── the paper, transcribed (manuscript version 3) ─────────────────────────
PAPER = {
    "5c": {
        "best_epoch": 189,
        "macro_f1": {"train": 0.809, "val": 0.626, "test": 0.619},
        "acc": {"train": 0.800, "val": 0.625, "test": 0.605},
        "test_f1_2dp": {"CD": 0.76, "ND": 0.69, "HF": 0.68, "LD": 0.61, "MD": 0.35},
        "val_f1_2dp": {"CD": 0.88, "MD": 0.42},  # Appendix B0.9
        "cm": {  # Fig. B3 top row, rows true ND HF MD LD CD
            "train": [[78, 0, 0, 4, 0], [0, 72, 28, 10, 0], [0, 12, 75, 11, 0],
                      [6, 7, 34, 146, 3], [0, 0, 2, 3, 109]],
            "val": [[21, 1, 1, 5, 0], [4, 17, 7, 6, 3], [1, 5, 15, 12, 0],
                    [7, 2, 15, 39, 2], [0, 1, 1, 2, 33]],
            "test": [[17, 0, 2, 8, 0], [3, 23, 6, 1, 4], [1, 6, 15, 8, 2],
                     [1, 1, 24, 37, 3], [0, 1, 6, 2, 29]],
        },
    },
    "4c": {
        "best_epoch": 363,
        "macro_f1": {"train": 1.000, "val": 0.738, "test": 0.641},
        "acc": {"train": 1.000, "val": 0.705, "test": 0.605},
        "cm": {  # Fig. B3 bottom row, rows true ND HFMD LD CD
            "train": [[82, 0, 0, 0], [0, 208, 0, 0], [0, 0, 196, 0], [0, 0, 0, 114]],
            "val": [[24, 1, 3, 0], [0, 43, 22, 5], [8, 17, 40, 0], [0, 1, 2, 34]],
            "test": [[17, 2, 8, 0], [0, 40, 24, 5], [4, 24, 37, 1], [0, 7, 4, 27]],
        },
    },
    # Table B2, test macro-F1 of the four ablation cells
    "ablation_test_f1": {"y2019_5c_pw_noaug": 0.619, "y2019_5c_nopw_noaug": 0.551,
                         "y2019_4c_pw_noaug": 0.641, "y2019_4c_nopw_noaug": 0.696},
}


def read_preds(run: str, split: str):
    p = require_source(INF / f"{run}_{split}_predictions_bestf1.csv")
    with open(p) as f:
        rd = csv.DictReader(f)
        rows = list(rd)
        classes = [c[2:] for c in rd.fieldnames if c.startswith("p_")]
    return classes, rows


def confusion(rows, classes):
    k = len(classes)
    cm = np.zeros((k, k), dtype=int)
    for r in rows:
        cm[classes.index(r["true_label"]), classes.index(r["pred_label"])] += 1
    return cm


def per_class_f1(cm):
    tp = np.diag(cm).astype(float)
    fp = cm.sum(axis=0) - tp
    fn = cm.sum(axis=1) - tp
    den = 2 * tp + fp + fn
    return np.divide(2 * tp, den, out=np.zeros_like(tp), where=den > 0)


def r3(x: float) -> float:
    return float(round(float(x), 3))


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")
    print(f"  ok  {msg}")


# ── training log (optional): confusion matrices every 10 epochs ───────────
CM_HEAD = re.compile(r"^\s+(Train|Validation) Confusion Matrix \(epoch (\d+)\):")
CM_ROW = re.compile(r"^\s+([A-Z]+):\s*\[([\d\s]+)\]\s*$")


def parse_log_matrices(path: Path, classes):
    """{'train': {epoch: cm}, 'val': {epoch: cm}} from the trainer's prints:
         Train Confusion Matrix (epoch 10):
         Classes: ['ND', 'HF', ...]
         (rows=true, cols=pred)
           ND: [78  0  0  4  0]
       (numpy's row repr; a row can wrap onto a continuation line)."""
    out = {"train": {}, "val": {}}
    lines = path.read_text(errors="replace").splitlines()
    i = 0
    while i < len(lines):
        m = CM_HEAD.match(lines[i])
        if not m:
            i += 1
            continue
        split = "train" if m.group(1) == "Train" else "val"
        ep = int(m.group(2))
        rows, j = [], i + 1
        while j < len(lines) and len(rows) < len(classes):
            s = lines[j]
            rm = re.match(r"^\s+([A-Z]+):\s*\[(.*)$", s)
            if rm and rm.group(1) in classes:
                body = rm.group(2)
                while "]" not in body and j + 1 < len(lines):  # wrapped row
                    j += 1
                    body += " " + lines[j].strip()
                body = body.split("]")[0]
                rows.append([int(v) for v in body.split()])
            j += 1
        if len(rows) == len(classes) and all(len(r) == len(classes) for r in rows):
            out[split][ep] = rows
        i = j
    return out


def bake_run(key: str, metrics_all: dict):
    run, classes, rnd = RUNS[key]
    paper = PAPER[key]
    print(f"\n── {key}  {run}")
    m = json.load(open(require_source(REV / f"metrics_rev_{run}.json")))
    check(m["classes"] == classes, f"{key}: metrics classes {m['classes']}")
    pe = m["per_epoch"]
    check(pe["epoch"] == list(range(1, 401)), f"{key}: per-epoch curves cover epochs 1..400")
    best = int(np.argmax(pe["val_f1"])) + 1
    check(best == paper["best_epoch"], f"{key}: best val macro-F1 epoch {best} == paper {paper['best_epoch']}")
    check(r3(pe["val_f1"][best - 1]) == paper["macro_f1"]["val"],
          f"{key}: logged val macro-F1 at best epoch {pe['val_f1'][best - 1]} == paper {paper['macro_f1']['val']}")

    # checkpoint provenance
    try:
        import torch
        ck = torch.load(CKPT / f"lakevision_essd_rev_{run}_bestf1.pth", map_location="cpu", weights_only=False)
        check(int(ck["epoch"]) == best, f"{key}: checkpoint epoch {ck['epoch']} == {best}")
        check(list(ck["class_names"]) == classes, f"{key}: checkpoint class names")
        ck_val_f1 = float(ck["metrics"]["f1_macro"])
        git_sha = str(ck.get("git_sha", ""))[:7]
    except ImportError:
        print("  (torch not available — checkpoint cross-check skipped)")
        ck_val_f1, git_sha = None, ""

    ids = {s: set(json.load(open(require_source(REV / "essd_CW_2019only" / f"{s}_ids.json")))) for s in SPLITS}
    best_block = {}
    for s in SPLITS:
        cls_csv, rows = read_preds(run, s)
        check(cls_csv == classes, f"{key}/{s}: CSV class columns {cls_csv}")
        check({r['lake_id'] for r in rows} == ids[s], f"{key}/{s}: CSV lakes == split ids (n={len(rows)})")
        cm = confusion(rows, classes)
        f1 = per_class_f1(cm)
        macro = float(f1.mean())
        acc = float(np.trace(cm) / cm.sum())
        check(cm.tolist() == paper["cm"][s], f"{key}/{s}: confusion matrix == Fig. B3 cell for cell")
        check(r3(macro) == paper["macro_f1"][s], f"{key}/{s}: macro-F1 {macro:.4f} -> {r3(macro)} == Table B2 {paper['macro_f1'][s]}")
        check(r3(acc) == paper["acc"][s], f"{key}/{s}: accuracy {acc:.4f} == Table B2 {paper['acc'][s]}")
        if s == "val" and ck_val_f1 is not None:
            check(abs(macro - ck_val_f1) < 1e-9, f"{key}/val: CSV macro-F1 == checkpoint metrics ({ck_val_f1:.6f})")
        best_block[s] = {
            "n": int(cm.sum()),
            "cm": cm.tolist(),
            "macro_f1": r3(macro),
            "acc": r3(acc),
            "f1": {c: r3(v) for c, v in zip(classes, f1)},
        }

    if key == "5c":
        tf = best_block["test"]["f1"]
        for c, v in paper["test_f1_2dp"].items():
            check(round(tf[c], 2) == v, f"5c/test per-class F1 {c} {tf[c]} -> {round(tf[c], 2)} == Sect. 5 {v}")
        vf = best_block["val"]["f1"]
        for c, v in paper["val_f1_2dp"].items():
            check(round(vf[c], 2) == v, f"5c/val per-class F1 {c} {vf[c]} == App. B0.9 {v}")
        cm = np.array(best_block["test"]["cm"])
        ld, md = classes.index("LD"), classes.index("MD")
        check(int(cm[ld, md]) == 24 and int(cm[ld].sum()) == 66, "5c/test LD predicted as MD: 24 of 66")
        off = cm.copy()
        np.fill_diagonal(off, 0)
        i, j = np.unravel_index(np.argmax(off), off.shape)
        check((classes[i], classes[j]) == ("LD", "MD"), f"5c/test dominant confusion is LD->MD ({classes[i]}->{classes[j]})")

    # per-epoch confusion matrices from the log, if copied locally
    cbe = {}
    log = LOGS / Path(m.get("source_log", "")).name
    if log.name and log.exists():
        mats = parse_log_matrices(log, classes)
        eps = sorted(set(mats["train"]) & set(mats["val"]))
        print(f"  log {log.name}: train matrices at {len(mats['train'])} epochs, val at {len(mats['val'])}")
        pcv, pct = m["per_class_val"], m["per_class_train"]
        n_val =np.array(best_block["val"]["cm"]).sum(axis=1).tolist()
        n_tr = np.array(best_block["train"]["cm"]).sum(axis=1).tolist()
        for e in eps:
            v, t = np.array(mats["val"][e]), np.array(mats["train"][e])
            check(v.sum(axis=1).tolist() == n_val and t.sum(axis=1).tolist() == n_tr,
                  f"{key}: epoch {e} matrices' row sums == split class counts")
            if e in pcv["epoch"]:
                k = pcv["epoch"].index(e)
                fv, ft = per_class_f1(v), per_class_f1(t)
                check(all(abs(r3(fv[ci]) - pcv[c][k]) <= 0.0015 for ci, c in enumerate(classes))
                      and all(abs(r3(ft[ci]) - pct[c][k]) <= 0.0015 for ci, c in enumerate(classes)),
                      f"{key}: epoch {e} matrices reproduce the logged per-class F1")
        cbe = {"epochs": eps,
               "train": [mats["train"][e] for e in eps],
               "val": [mats["val"][e] for e in eps],
               "source": log.name}
    else:
        print(f"  NO LOG at {log} — confusion_by_epoch left empty (matrices at the best epoch only)")

    metrics_all[key] = ck_val_f1
    return {
        "run": run,
        "classes": classes,
        "colors": {c: COLORS[c] for c in classes},
        "random_f1": rnd,
        "best_epoch": best,
        "git_sha": git_sha,
        "curves": {k: [r3(v) if "f1" in k else float(round(v, 4)) for v in pe[k]]
                   for k in ("train_loss", "val_loss", "train_f1", "val_f1")},
        "per_class_val": m["per_class_val"],
        "per_class_train": m["per_class_train"],
        "best": best_block,
        "confusion_by_epoch": cbe,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ck = {}
    runs = {k: bake_run(k, ck) for k in RUNS}

    print("\n── Table B2 ablation (test macro-F1)")
    ablation = []
    for run, k, pw in ABLATION:
        classes, rows = read_preds(run, "test")
        f1 = float(per_class_f1(confusion(rows, classes)).mean())
        check(r3(f1) == PAPER["ablation_test_f1"][run], f"{run}: test macro-F1 {f1:.4f} == Table B2 {PAPER['ablation_test_f1'][run]}")
        ablation.append({"run": run, "classes": k, "p_water": pw, "test_macro_f1": r3(f1)})

    doc = {
        "about": "ESSD revision (manuscript v3) baseline training dynamics — Fig. B2 curves, Fig. B3 matrices, Table B2. "
                 "Built by cinematic/scene_ch03/build_training_dynamics.py.",
        "epochs": 400,
        "runs": runs,
        "ablation": ablation,
    }
    path = OUT / "training_dynamics_v2.json"
    path.write_text(json.dumps(doc, separators=(",", ":")))
    print(f"\nwrote {path}  ({path.stat().st_size / 1024:.1f} kB)")
    for k, r in runs.items():
        cbe = r["confusion_by_epoch"]
        print(f"  {k}: confusion_by_epoch {'%d epochs' % len(cbe['epochs']) if cbe else 'EMPTY (no log)'}")


if __name__ == "__main__":
    main()
