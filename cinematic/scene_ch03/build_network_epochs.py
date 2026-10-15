"""Bake Chapter 3's network segment on its EPOCH axis: the five lakes through
the ESSD revision's baseline as it TRAINS.

The DAY axis (build_network.py) holds the weights fixed (the best-F1
checkpoint, epoch 189) and walks the season. This holds the data fixed and
walks training: every 5-epoch checkpoint the run saved (epochs 5..400) plus
the best-F1 checkpoint itself (epoch 189, so the EPOCH axis passes through
the exact model the DAY axis shows), 81 frames in all.

WHICH DAY. Two, and the figures say which by their date stamp:
  * the per-frame stages (conv blocks 1-4) look at ONE frame; they are
    baked at the lake's peak-fill day (the manifest's `default_day`, the
    day the DAY axis opens on). 30 Sep was the first choice, but four of
    the five lakes have no scene on 30 Sep (a missing day is a constant
    fill frame, so every conv map would be featureless);
  * the recurrent state and everything after it (ConvLSTM h, GAP 32,
    LSTM 16, concat 48, hidden 64, softmax 5) are the SEASON-END values,
    t = 152 (30 Sep) — the state the network's prediction is read from and
    the one the validation macro-F1 was scored on.
The input imagery, the five channels and p_water are data: they do not
change with the epoch, so the site reuses the DAY axis's frames for them.

Each checkpoint carries its own config (provenance format); every one is
checked equal to the best-F1's config and loaded strict through the
revision's run_inference.build_from_config — the same path as
build_network.py. The epoch-189 frame is checked against the DAY bake's
season-end row (probabilities to 1e-4). Each checkpoint's logged validation
macro-F1 (its `metrics`) is checked against the run's metrics JSON curve.

Per lake (R2 ch03/network_epochs/<lake>/):
  conv1..4.mp4  FrontCNN block outputs at the peak day, one frame an epoch
  clstm.mp4     the ConvLSTM hidden state at 30 Sep, one frame an epoch
  manifest.json epochs, the two days, per-epoch vectors + probabilities,
                per-epoch val/train macro-F1
Plus ch03/network_epochs/index.json: the epochs, the best epoch, the F1
curves (all 400 epochs) and each frame's head weights w1 (int8, for the
hidden-64 drawing).

The director asked for a loss curve on the same plot as the F1 curve
(two y-axes): the index is now written as index_v2.json with
`curves` carrying val_loss + train_loss as well (R2 objects are immutable —
new bytes, new name). `--index-only` rebuilds index_v2.json from an
existing bake's index.json + the metrics JSON without running the model.
`--run y2019_4c_pw_noaug` bakes the four-class model (its 80 snapshots sit
beside its best-F1 checkpoint, not in epochs/) into ch03/network_epochs_4c/;
it reads the four-class DAY bake (build_network.py --run ...) for the peak
day and the best-epoch cross-check, so bake that first.

Run (needs torch; use a Python env with torch installed):
  nice -n 15 python \
      cinematic/scene_ch03/build_network_epochs.py [--lakes CW2019_1848 ...]
      [--run y2019_4c_pw_noaug] [--index-only]
Then:
  rclone copy cinematic/data/ch03/network_epochs r2:<bucket>/ch03/network_epochs --header-upload 'Cache-Control: public, max-age=31536000, immutable'
  rclone copy cinematic/data/ch03/network_epochs website/.r2-cache/ch03/network_epochs
"""

import argparse
import base64
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import build_network as bn  # noqa: E402
from build_network import (  # noqa: E402
    CRF, ESSD, LAKES, LAYOUT, SRC, Video, colormap,
    per_channel_range, r, robust_picks, sheet, sheet_geometry, upscale,
)
from shared import SOURCE_DATA, require_source  # noqa: E402

CKPTS = ESSD / "checkpoints" / "essd_revision"
STATS = ESSD / "revision" / "band_stats_essd_2019only_deposit.json"
STAGES = ["conv1", "conv2", "conv3", "conv4", "clstm"]
INDEX_NAME = "index_v2.json"
# set by configure() for the run (bn.configure sets the classes)
RUN = bn.RUN
OUT = HERE.parent / "data" / "ch03" / "network_epochs"
BEST = CKPTS / f"lakevision_essd_rev_{RUN}_bestf1.pth"
METRICS = ESSD / "revision" / f"metrics_rev_{RUN}.json"
# The DAY bake's manifests (what the site shows on the DAY axis), for the
# peak day and the best-epoch cross-check.
DAY_MANIFESTS = HERE.parents[1] / "website" / ".r2-cache" / "ch03" / "network"


def configure(run: str) -> None:
    global RUN, OUT, BEST, METRICS, DAY_MANIFESTS
    bn.configure(run)
    tag = bn.RUNS[run]["tag"]
    sfx = f"_{tag}" if tag else ""
    RUN = run
    OUT = HERE.parent / "data" / "ch03" / f"network_epochs{sfx}"
    BEST = CKPTS / f"lakevision_essd_rev_{run}_bestf1.pth"
    METRICS = ESSD / "revision" / f"metrics_rev_{run}.json"
    DAY_MANIFESTS = HERE.parents[1] / "website" / ".r2-cache" / "ch03" / f"network{sfx}"
    if not DAY_MANIFESTS.exists():
        DAY_MANIFESTS = bn.OUT            # the DAY bake not yet mirrored


def epoch_checkpoints(best_epoch: int) -> list:
    """[(epoch, path, is_best)] in epoch order, the best-F1 file included.
    The five-class snapshots live in epochs/, the others beside the best."""
    out = []
    for d in (CKPTS / "epochs", CKPTS):
        out = []
        for p in sorted(d.glob(f"lakevision_essd_rev_{RUN}_epoch*.pth")):
            m = re.search(r"_epoch(\d+)\.pth$", p.name)
            out.append((int(m.group(1)), p, False))
        if out:
            break
    assert len(out) == 80, f"expected 80 epoch checkpoints, found {len(out)}"
    out.append((best_epoch, require_source(BEST), True))
    out.sort(key=lambda e: (e[0], e[2]))
    return out


def curves_of(metrics: Path) -> dict:
    tc = json.loads(metrics.read_text())["per_epoch"]
    return {"epoch": tc["epoch"], "val_f1": r(tc["val_f1"]),
            "train_f1": r(tc["train_f1"]), "val_loss": r(tc["val_loss"]),
            "train_loss": r(tc["train_loss"])}


def index_only() -> None:
    """index_v2.json = the bake's index.json with the loss curves added."""
    src = OUT / "index.json"
    if not src.exists():
        src = DAY_MANIFESTS.parent / OUT.name / "index.json"   # the R2 mirror
    index = json.loads(require_source(src).read_text())
    assert index["run"] == RUN, (index["run"], RUN)
    index["curves"] = curves_of(require_source(METRICS))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / INDEX_NAME).write_text(json.dumps(index, separators=(",", ":")))
    print(f"{src} -> {OUT / INDEX_NAME} (curves: {sorted(index['curves'])})")


def feature_video_epochs(arr: np.ndarray, key: str, out: Path, lo, hi) -> dict:
    """[E, C, H, W] -> the heat-tile grid video, one frame an epoch. The
    colour range is the DAY bake's own (per channel, over the season, at the
    best-F1 checkpoint): the epoch-189 frame is then the DAY axis's frame
    pixel for pixel, and every other epoch is drawn on the trained
    network's scale (a channel that has not formed yet reads dim or
    saturated — that is the point)."""
    E, C, H, W = arr.shape
    g = sheet_geometry(C, LAYOUT[key]["cols"], LAYOUT[key]["tile"])
    v = Video(out / f"{key}.mp4", g["w"], g["h"], crf=CRF[key])
    for e in range(E):
        norm = (arr[e] - lo[:, None, None]) / (hi - lo)[:, None, None]
        v.write(sheet([upscale(colormap(norm[c]), g["tile"]) for c in range(C)], g))
    v.close()
    return {"file": f"{key}.mp4", "shape": [C, H, W], **g, "vw": v.w, "vh": v.h}


def int8_b64(a: np.ndarray) -> dict:
    s = float(np.abs(a).max()) or 1.0
    q = np.clip(np.round(a / s * 127), -127, 127).astype(np.int8)
    return {"scale": round(s / 127, 7), "b64": base64.b64encode(q.tobytes()).decode()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lakes", nargs="*", default=[l for l, _ in LAKES])
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu",
                    help="mps: ~1.2 s a season pass on the M2 (cpu: 15-27 s)")
    ap.add_argument("--run", default=bn.RUN, choices=sorted(bn.RUNS))
    ap.add_argument("--index-only", action="store_true",
                    help="rebuild index_v2.json from the bake's index.json + the metrics")
    args = ap.parse_args()
    configure(args.run)
    if args.index_only:
        index_only()
        return
    CLASSES = bn.CLASSES
    torch.set_num_threads(args.threads)
    dev = torch.device(args.device)

    sys.path.insert(0, str(SRC))
    sys.path.insert(0, str(SRC / "engine" / "inference"))
    from lakevision.models.checkpoint import load_checkpoint
    import run_inference as ri

    best_state, best_meta = load_checkpoint(str(BEST), map_location="cpu")
    best_epoch = int(best_meta["epoch"])
    ckpts = epoch_checkpoints(best_epoch)
    config = dict(best_meta["config"])
    config["band_stats"] = str(require_source(STATS))
    class_names = list(best_meta["class_names"])
    assert class_names == CLASSES, class_names
    if RUN == "y2019_5c_pw_noaug":
        assert best_epoch == 189, best_epoch

    # every checkpoint: same config, its epoch, its logged val F1
    curves = json.loads(require_source(METRICS).read_text())["per_epoch"]
    f1_of = dict(zip(curves["epoch"], curves["val_f1"]))
    states, frames = [], []
    for ep, p, is_best in ckpts:
        st, meta = load_checkpoint(str(p), map_location="cpu")
        assert meta is not None and meta["epoch"] == ep, (p.name, meta and meta.get("epoch"))
        assert meta["config"] == best_meta["config"], f"config differs: {p.name}"
        assert list(meta["class_names"]) == CLASSES
        f1 = float(meta["metrics"]["f1_macro"])
        assert abs(f1 - f1_of[ep]) < 6e-4, (ep, f1, f1_of[ep])   # the log prints 3 decimals
        states.append(st)
        frames.append({"epoch": ep, "best": is_best, "val_f1": f1,
                       "file": p.name, "git_sha": str(meta.get("git_sha"))[:7]})
    print(f"{len(frames)} checkpoints, configs identical, val F1 matches the log "
          f"(epoch 5 {f1_of[5]:.3f} · 50 {f1_of[50]:.3f} · {best_epoch} {f1_of[best_epoch]:.3f} · "
          f"200 {f1_of[200]:.3f} · 400 {f1_of[400]:.3f})")

    true_of = bn.TRUE_OF
    stacks = [require_source(SOURCE_DATA / "stacks" / "CW_2019" / f"{l}.nc") for l in args.lakes]
    labels = {l: CLASSES.index(true_of[l]) for l in args.lakes}
    dataset, model = ri.build_from_config(
        config, class_names, labels, [str(s) for s in stacks], torch.device("cpu"))[:2]
    model.to(dev).eval()
    # exact (per-image ops); keeps the 512x512 activations to 16 frames at a time
    model.frontcnn.chunk_size = 16
    assert model.temporal_readout == "last" and model.pool_type == "avg"
    fc = model.classifier.fc
    lin1 = [m for m in fc if isinstance(m, torch.nn.Linear)][0]
    lin2 = [m for m in fc if isinstance(m, torch.nn.Linear)][-1]

    taps: dict = {}
    # "one": keep the single-frame pass's output; "all": collect a season
    tapping = {"on": None}
    seq = model.frontcnn.conv_block
    pools = [i for i, m in enumerate(seq) if isinstance(m, torch.nn.MaxPool2d)]
    assert len(pools) == 4, pools
    for k, i in enumerate(pools):
        seq[i].register_forward_hook(
            lambda _m, _i, o, key=f"conv{k + 1}": (
                taps.__setitem__(key, o.detach().cpu().clone()) if tapping["on"] == "one" else
                taps.setdefault(key, []).append(o.detach().cpu()) if tapping["on"] == "all" else None))
    # the ConvLSTM cell runs once a day; the last call leaves h at t = 152
    cell_out: dict = {}
    season_h: list = []

    def on_cell(_m, _i, o):          # must return None (a value replaces the output)
        cell_out["h"] = o[0].detach()
        if tapping["on"] == "all":
            season_h.append(o[0].detach().cpu())
    model.clstm.cell.register_forward_hook(on_cell)

    OUT.mkdir(parents=True, exist_ok=True)
    w1s = []
    for st in states:
        model.load_state_dict(st, strict=True)
        w1s.append(int8_b64(lin1.weight.detach().cpu().numpy()))
    n_params = sum(p.numel() for p in model.parameters())

    E = len(frames)
    summary = {}
    for li, lake in enumerate(args.lakes):
        t_lake = time.time()
        out = OUT / lake
        out.mkdir(parents=True, exist_ok=True)
        sample = dataset[li]
        img, area = sample[0], sample[1]
        cloudy = sample[2] if len(sample) > 2 and torch.is_tensor(sample[2]) else None
        T = img.shape[0]
        _, _, p_raw = bn.display_rgb_all(stacks[li])
        picks, peak = robust_picks(area.numpy().reshape(-1), p_raw, 6)
        img, area = img.to(dev), area.to(dev)
        cloudy = cloudy.to(dev) if cloudy is not None else None
        dm_path = DAY_MANIFESTS / lake / "manifest.json"
        day_man = json.loads(dm_path.read_text()) if dm_path.exists() else None
        if day_man:
            assert day_man["default_day"] == peak, (lake, day_man["default_day"], peak)
        img_day, end_day = peak, T - 1

        # the DAY bake's colour ranges: the best-F1 model over the season
        model.load_state_dict(best_state, strict=True)
        taps.clear()
        season_h.clear()
        tapping["on"] = "all"
        with torch.no_grad():
            model(img.unsqueeze(0), area.unsqueeze(0),
                  cloudy.unsqueeze(0) if cloudy is not None else None)
        tapping["on"] = None
        ranges = {k: per_channel_range(torch.cat(taps[k], 0).numpy()) for k in STAGES[:4]}
        ranges["clstm"] = per_channel_range(torch.cat(season_h, 0).numpy())
        assert torch.cat(taps["conv1"], 0).shape[0] == T and len(season_h) == T
        taps.clear()
        season_h.clear()

        conv = {k: [] for k in STAGES}
        vec = {k: [] for k in ("gap", "slstm", "hidden", "logits", "probs")}
        for e, st in enumerate(states):
            model.load_state_dict(st, strict=True)
            with torch.no_grad():
                taps.clear()
                tapping["on"] = "one"
                model.frontcnn(img[img_day:img_day + 1].unsqueeze(0))
                tapping["on"] = None
                for k in STAGES[:4]:
                    conv[k].append(taps[k][0].numpy())
                cell_out.clear()
                logits_full = model(img.unsqueeze(0), area.unsqueeze(0),
                                    cloudy.unsqueeze(0) if cloudy is not None else None)
                h = cell_out["h"][0].cpu()                        # [32, 32, 32] at t = 152
                gap = h.mean(dim=(-1, -2))
                slstm = model.area_lstm(area.unsqueeze(0))[0][-1].cpu()
                gap = gap.to(dev)
                hid = torch.relu(lin1(torch.cat([gap, slstm.to(dev)])))
                logits = lin2(hid)
                assert torch.allclose(logits, logits_full.reshape(-1), atol=1e-4), (logits, logits_full)
                gap, hid, logits = gap.cpu(), hid.cpu(), logits.cpu()
                probs = torch.softmax(logits, 0)
            conv["clstm"].append(h.numpy())
            for k, v_ in (("gap", gap), ("slstm", slstm), ("hidden", hid),
                          ("logits", logits), ("probs", probs)):
                vec[k].append(v_.numpy())
            if frames[e]["best"] and day_man:
                dp = np.array(day_man["vectors"]["probs"][end_day])
                d = float(np.abs(dp - probs.numpy()).max())
                print(f"  epoch-{best_epoch} (best-F1) season-end probs vs the DAY bake: max |delta| {d:.2e}")
                assert d < 2e-4, d
            if e % 10 == 0:
                print(f"  {lake} epoch {frames[e]['epoch']:3d}  "
                      + " ".join(f"{c} {p:.3f}" for c, p in zip(CLASSES, probs.numpy()))
                      + f"   ({time.time() - t_lake:.0f} s)", flush=True)

        stages = {}
        for k in STAGES:
            stages[k] = feature_video_epochs(np.stack(conv[k]), k, out, *ranges[k])
            print(f"  {k:6s} {stages[k]['shape']}  {stages[k]['w']}x{stages[k]['h']}  "
                  f"{(out / stages[k]['file']).stat().st_size / 1e6:.2f} MB")
        P = np.stack(vec["probs"])
        manifest = {
            "lake": lake, "true": true_of[lake], "axis": "epoch",
            "epochs": [f["epoch"] for f in frames],
            "best_index": next(i for i, f in enumerate(frames) if f["best"]),
            "image_day": int(img_day), "state_day": int(end_day),
            "fps": bn.FPS, "stages": stages,
            "vectors": {k: r(np.stack(v_)) for k, v_ in vec.items()},
            "pred": [CLASSES[int(i)] for i in P.argmax(1)],
            "days_note": ("conv1-4: the lake's peak-fill day (image_day); "
                          "ConvLSTM h and everything after it: the season end "
                          "(state_day = 30 Sep), the state the prediction and the "
                          "validation F1 are read from."),
        }
        (out / "manifest.json").write_text(json.dumps(manifest, separators=(",", ":")))
        summary[lake] = {f["epoch"]: dict(zip(CLASSES, np.round(P[i], 3).tolist()))
                         for i, f in enumerate(frames) if f["epoch"] in (5, 50, best_epoch, 200, 400)}
        print(f"{lake}: {time.time() - t_lake:.0f} s")
        for ep, pr in summary[lake].items():
            print(f"   epoch {ep:3d}: " + "  ".join(f"{c} {p:.3f}" for c, p in pr.items()))

    index = {
        "run": RUN, "params": n_params, "fps": bn.FPS,
        "epochs": [f["epoch"] for f in frames],
        "best_index": next(i for i, f in enumerate(frames) if f["best"]),
        "best_epoch": best_epoch, "last_epoch": 400,
        "frames": frames,
        "curves": curves_of(METRICS),
        "w1": w1s,
        "lakes": args.lakes,
        "split": "CW2019 600/200/200",
    }
    (OUT / INDEX_NAME).write_text(json.dumps(index, separators=(",", ":")))
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    total = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"\nwrote {sum(1 for f in OUT.rglob('*') if f.is_file())} files, "
          f"{total / 1e6:.1f} MB -> {OUT}")


if __name__ == "__main__":
    main()
