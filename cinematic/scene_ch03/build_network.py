"""Bake Chapter 3's NETWORK segment: five lakes through the ESSD revision's
baseline classifier, every stage, every day of the season.

The site's network segment (website/src/components/EssdNetwork.vue) is an
architecture diagram that doubles as a road map, with the data at the lit
block shown above it. Any of the five example lakes can be put through.
Everything is precomputed here; nothing runs a model in the browser.

Model: the revision's five-class baseline with p_water (essd-2026-406
version 3, Sect. 5 + Appendix B; run y2019_5c_pw_noaug, best-val epoch
189, 140,309 parameters), rebuilt from the checkpoint's own config by the
revision's run_inference.build_from_config — exactly as
build_walkthrough_rev.py does, so nothing about the architecture or the
preprocessing is hard-coded here.

What is baked per lake (R2 ch03/network/<lake>/):
  scene.mp4      the Sentinel-2 RGB, all 153 days (display stretch)
  chan.mp4       the five channels the network receives (3 x 2 grid)
  conv1..4.mp4   the output of each FrontCNN block (after the MaxPool)
  clstm.mp4      the ConvLSTM hidden state h_t, day by day
  thumb.jpg      the scene at peak fill (lake picker, diagram input)
  manifest.json  the vectors per day (pooled 32, scalar-LSTM 16, head 64,
                 logits, probabilities), p_water, picks, the published row
Videos are 10 fps (one frame per day), a keyframe every 30 frames (the
surface texture barely changes between clear days, so P-frames carry most
of the season cheaply; a seek decodes <= 29 frames); CRF per stage in
CRF. The site seeks them to the selected day. Sized for a 60 MB budget.
Plus ch03/network/index.json: the five lakes and the head's weights (the
MLP drawing).

THE PROBABILITIES THROUGH THE SEASON. Both recurrent streams are causal
(ConvLSTM and LSTM, final-state readout), so the network's output for the
sequence truncated at day t is exactly: GAP(ConvLSTM h_t) ++ LSTM h_t ->
head -> softmax. We read h_t off the full-season pass and push it through
the head; `check_truncation` re-runs the network on a truncated sequence
for one lake/day and asserts the two agree. The inputs are prepared for the
FULL season (p_water gap-fill and per-lake min-max use the whole season;
imagery standardisation uses train-split band stats, which do not depend on
the season). The network was trained only on full 153-day seasons, so
every day before the last is out of distribution: those probabilities are
illustrative of how the evidence accumulates, not predictions. Day 152
(30 Sep) is the real prediction.

SPLITS (checked against revision/essd_CW_2019only/*_ids.json and the
published tables): CW2019_1597, _1848 and _1907 are TRAIN
lakes; CW2019_1889 and _2330 are VALIDATION lakes (the checkpoint was
selected on validation macro-F1, so neither is held out either). None is
in test. The manifest carries the split; the site's verdict tags it.
Final probabilities match the published rows to <= 0.0073 (float32 here,
bfloat16 there).

Run (needs torch — the cinematic venv does NOT have it; use a Python env with torch installed):
  nice -n 15 python \
      cinematic/scene_ch03/build_network.py [--lakes CW2019_1848 ...]
  (--run y2019_4c_pw_noaug bakes the four-class model, HF + MD merged,
  into cinematic/data/ch03/network_4c → R2 ch03/network_4c/.)
Then:
  rclone copy cinematic/data/ch03/network r2:<bucket>/ch03/network --header-upload 'Cache-Control: public, max-age=31536000, immutable'
  rclone copy cinematic/data/ch03/network website/.r2-cache/ch03/network
"""

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import torch

CINEMATIC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CINEMATIC))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared import SOURCE_DATA, require_source  # noqa: E402
from PIL import Image  # noqa: E402

ESSD = SOURCE_DATA / "essd"
SRC = ESSD / "lakevision_src_rev"
FPS = 10
GOP = 30
T0 = "2019-05-01"

# The five ESSD Fig. 4 lakes (= Ch.1's featured lakes), in the site's
# class palette.
LAKES = [
    ("CW2019_1597", "ND"), ("CW2019_1889", "HF"), ("CW2019_1848", "MD"),
    ("CW2019_1907", "LD"), ("CW2019_2330", "CD"),
]
# (CLASSES, CLASS_NAMES and pick_days lived in the since-retired
# build_walkthrough.py; they live here now.)
CLASSES_5 = ["ND", "HF", "MD", "LD", "CD"]
CLASS_NAMES_5 = {
    "ND": "No drainage", "HF": "Hydrofracture", "MD": "Moulin drainage",
    "LD": "Lateral drainage", "CD": "Crevasse drainage",
}
COLORS_5 = {"ND": "#e8524a", "HF": "#4caf50", "MD": "#42a5f5",
            "LD": "#ff9800", "CD": "#ab47bc"}

# THE TAXONOMY (the director asked for a TAXONOMY toggle with 4-class and
# 5-class beneath it). `--run` picks the model; the four-class run merges
# HF and MD into HFMD (its checkpoint's own class code), drawn in Fig. B2's
# HFMD teal — the colour Chapter 3's training beat already uses for it.
# The five-class run keeps the original output names (R2 ch03/network/);
# every other run bakes under a new prefix (ch03/network_<tag>/).
RUNS = {
    "y2019_5c_pw_noaug": {"tag": "", "classes": CLASSES_5},
    "y2019_4c_pw_noaug": {"tag": "4c", "classes": ["ND", "HFMD", "LD", "CD"]},
}
TO_4C = {"ND": "ND", "HF": "HFMD", "MD": "HFMD", "LD": "LD", "CD": "CD"}

RUN = "y2019_5c_pw_noaug"
OUT = CINEMATIC / "data" / "ch03" / "network"
CLASSES = CLASSES_5
CLASS_NAMES = CLASS_NAMES_5
COLORS = COLORS_5
TRUE_OF = dict(LAKES)


def configure(run: str) -> None:
    """Point the module's globals at one run (classes, names, colours, the
    lakes' labels in that taxonomy, the output directory)."""
    global RUN, OUT, CLASSES, CLASS_NAMES, COLORS, TRUE_OF
    spec = RUNS[run]
    RUN = run
    OUT = CINEMATIC / "data" / "ch03" / ("network" + (f"_{spec['tag']}" if spec["tag"] else ""))
    CLASSES = list(spec["classes"])
    if "HFMD" in CLASSES:
        CLASS_NAMES = {**{c: CLASS_NAMES_5[c] for c in CLASSES if c in CLASS_NAMES_5},
                       "HFMD": "Hydrofracture + moulin drainage"}
        COLORS = {**{c: COLORS_5[c] for c in CLASSES if c in COLORS_5}, "HFMD": "#26a69a"}
        TRUE_OF = {l: TO_4C[c] for l, c in LAKES}
    else:
        CLASS_NAMES, COLORS, TRUE_OF = dict(CLASS_NAMES_5), dict(COLORS_5), dict(LAKES)


def pick_days(p_water: np.ndarray, n: int = 6) -> list:
    """Days that tell the season's story: start, fill, peak, drain, after.

    The drainage day is the steepest fall in p_water, which is the event the
    whole chapter is about — never let it fall outside the selection.
    """
    T = len(p_water)
    pw = np.nan_to_num(p_water, nan=0.0)
    peak = int(np.argmax(pw))
    drop = int(np.argmin(np.diff(pw))) + 1 if T > 1 else peak
    picks = {0, peak, drop, min(T - 1, drop + 8), T - 1}
    # fill toward n with evenly spaced days
    for t in np.linspace(0, T - 1, n).astype(int):
        if len(picks) >= n:
            break
        picks.add(int(t))
    return sorted(picks)

# Tile size (px in the video) and grid per stage: native resolution, except
# the 32 x 32 maps, doubled NEAREST so each network pixel is a whole 2 x 2
# chroma block after H.264. The site upscales on a canvas with smoothing
# off (pixelated). The gutter keeps the tiles apart. Sized for the 60 MB
# budget of five lakes.
GUTTER = 4
LAYOUT = {
    "chan":  {"cols": 3, "tile": 256},
    "conv1": {"cols": 4, "tile": 192},   # 256 -> 192 bilinear (budget)
    "conv2": {"cols": 4, "tile": 128},
    "conv3": {"cols": 8, "tile": 64},
    "conv4": {"cols": 8, "tile": 64},
    "clstm": {"cols": 8, "tile": 64},
}

# H.264 quality per video (higher = smaller). The feature maps are
# heat-tiles with noise-like texture on rough ice; they take the most bits.
CRF = {"scene": 25, "chan": 27, "conv1": 29, "conv2": 28, "conv3": 28,
       "conv4": 28, "clstm": 25}

# Inferno-ish ramp: dark ground, gold highs (the site's palette).
RAMP = np.array([
    [0, 0, 4], [22, 11, 57], [66, 10, 104], [114, 31, 129],
    [159, 47, 127], [206, 70, 103], [240, 111, 66], [252, 165, 39],
    [246, 222, 60], [252, 255, 164],
], dtype=np.float32) / 255.0


def colormap(x: np.ndarray) -> np.ndarray:
    """[..] in [0,1] -> [.., 3] uint8 on RAMP."""
    idx = np.clip(x, 0, 1) * (len(RAMP) - 1)
    lo = np.floor(idx).astype(int)
    hi = np.minimum(lo + 1, len(RAMP) - 1)
    f = (idx - lo)[..., None]
    return ((RAMP[lo] * (1 - f) + RAMP[hi] * f) * 255).astype(np.uint8)


def even(n: int) -> int:
    return n + (n % 2)


class Video:
    """Frames piped straight into ffmpeg (H.264, yuv420p, faststart)."""

    def __init__(self, path: Path, w: int, h: int, crf: int = 23,
                 encode: bool = True):
        self.w, self.h = even(w), even(h)
        self.p = None
        if not encode:          # --no-video: geometry only, keep the file
            assert path.exists(), f"--no-video but {path} is missing"
            return
        self.p = subprocess.Popen([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{self.w}x{self.h}", "-r", str(FPS), "-i", "-",
            "-c:v", "libx264", "-preset", "slow", "-crf", str(crf),
            "-g", str(GOP), "-keyint_min", str(GOP), "-sc_threshold", "0",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-an", str(path)], stdin=subprocess.PIPE)

    def write(self, rgb: np.ndarray) -> None:
        if self.p is None:
            return
        h, w = rgb.shape[:2]
        if (h, w) != (self.h, self.w):
            pad = np.zeros((self.h, self.w, 3), np.uint8)
            pad[:h, :w] = rgb
            rgb = pad
        self.p.stdin.write(np.ascontiguousarray(rgb).tobytes())

    def close(self) -> None:
        if self.p is None:
            return
        self.p.stdin.close()
        if self.p.wait() != 0:
            raise RuntimeError("ffmpeg failed")


def sheet_geometry(C: int, cols: int, tile: int) -> dict:
    rows = int(np.ceil(C / cols))
    return {"rows": rows, "cols": cols, "tile": tile, "gutter": GUTTER,
            "w": cols * tile + (cols - 1) * GUTTER,
            "h": rows * tile + (rows - 1) * GUTTER}


def sheet(tiles_rgb: list, g: dict) -> np.ndarray:
    """Lay [tile, tile, 3] uint8 tiles out on the grid, dark gutters."""
    out = np.full((g["h"], g["w"], 3), 10, np.uint8)
    for i, t in enumerate(tiles_rgb):
        r, c = divmod(i, g["cols"])
        y, x = r * (g["tile"] + GUTTER), c * (g["tile"] + GUTTER)
        out[y:y + g["tile"], x:x + g["tile"]] = t
    return out


def upscale(a: np.ndarray, tile: int) -> np.ndarray:
    """[H, W, 3] -> [tile, tile, 3], nearest when enlarging."""
    H = a.shape[0]
    if tile % H == 0:
        k = tile // H
        return a.repeat(k, 0).repeat(k, 1)
    return np.asarray(Image.fromarray(a).resize((tile, tile), Image.BILINEAR))


def display_rgb_all(stack: Path) -> tuple:
    """All 153 RGB frames, one stretch for the season; missing stays black."""
    import netCDF4 as nc4
    with nc4.Dataset(str(stack)) as nc:
        nc.set_auto_mask(False)
        names = ["".join(c.decode() if isinstance(c, bytes) else c
                         for c in row).strip()
                 for row in nc.variables["common_name"][:]]
        idx = [names.index(b) for b in ("red", "green", "blue")]
        refl = np.stack([np.asarray(nc.variables["reflectance"][:, i, :, :],
                                    dtype=np.float32) for i in idx], axis=-1)
        p_raw = (np.asarray(nc.variables["p_water"][:], dtype=np.float32)
                 if "p_water" in nc.variables else None)
    finite = refl[np.isfinite(refl)]
    lo, hi = np.percentile(finite, 2), np.percentile(finite, 98)
    missing = ~np.isfinite(refl).all(axis=-1)
    img = np.clip((np.nan_to_num(refl) - lo) / ((hi - lo) or 1.0), 0, 1)
    img[missing] = 0.0
    valid = 1.0 - missing.reshape(missing.shape[0], -1).mean(axis=1)
    return (img * 255).astype(np.uint8), valid, p_raw


def per_channel_range(arr: np.ndarray) -> tuple:
    """arr [T, C, H, W] -> per-channel (lo, hi), season-wide."""
    flat = np.moveaxis(arr, 1, 0).reshape(arr.shape[1], -1)
    lo = np.percentile(flat, 1, axis=1)
    hi = np.percentile(flat, 99.5, axis=1)
    hi = np.where(hi - lo < 1e-6, lo + 1e-6, hi)
    return lo, hi


ENCODE = True   # False with --no-video (manifests only; videos kept)


def feature_video(arr: np.ndarray, key: str, out: Path) -> dict:
    """[T, C, H, W] activations -> a heat-tile grid video, one frame a day."""
    T, C, H, W = arr.shape
    g = sheet_geometry(C, LAYOUT[key]["cols"], LAYOUT[key]["tile"])
    lo, hi = per_channel_range(arr)
    v = Video(out / f"{key}.mp4", g["w"], g["h"], crf=CRF[key], encode=ENCODE)
    for t in range(T if ENCODE else 0):
        norm = (arr[t] - lo[:, None, None]) / (hi - lo)[:, None, None]
        tiles = [upscale(colormap(norm[c]), g["tile"]) for c in range(C)]
        v.write(sheet(tiles, g))
    v.close()
    return {"file": f"{key}.mp4", "shape": [C, H, W], **g,
            "vw": v.w, "vh": v.h}


def channel_video(x: np.ndarray, names: list, out: Path) -> dict:
    """The five channels as the network receives them. Bands share one
    display range (they are standardised), tinted in their own colour; the
    binary channels are white on black."""
    T, C, H, W = x.shape
    g = sheet_geometry(C, LAYOUT["chan"]["cols"], LAYOUT["chan"]["tile"])
    band = x[:, :3]
    lo, hi = np.percentile(band, 1), np.percentile(band, 99)
    tint = {"red": (1.0, 0.36, 0.33), "green": (0.42, 0.9, 0.45),
            "blue": (0.4, 0.62, 1.0)}
    v = Video(out / "chan.mp4", g["w"], g["h"], crf=CRF["chan"], encode=ENCODE)
    for t in range(T if ENCODE else 0):
        tiles = []
        for c in range(C):
            if c < 3:
                a = np.clip((x[t, c] - lo) / ((hi - lo) or 1.0), 0, 1)
            else:
                a = np.clip(x[t, c], 0, 1)
            col = np.array(tint.get(names[c], (1.0, 1.0, 1.0)), np.float32)
            rgb = (a[..., None] * col * 255).astype(np.uint8)
            tiles.append(np.asarray(Image.fromarray(rgb).resize(
                (g["tile"], g["tile"]), Image.BILINEAR)))
        v.write(sheet(tiles, g))
    v.close()
    return {"file": "chan.mp4", "shape": [C, H, W], "channels": names,
            **g, "vw": v.w, "vh": v.h}


def robust_picks(pw: np.ndarray, raw, n: int = 6) -> tuple:
    """pick_days on the observed p_water with lone outliers removed.

    The deposited p_water carries one-day outliers (CW2019_2330 reads 1.00
    on 5 May between 0.08 and 0.19). The network's input gap-fills that
    across the cloudy days after it, so a median over calendar days keeps
    it. So: an observation more than 0.25 from the 5-point median of its
    neighbouring acquisitions is dropped as an outlier, and the remaining
    observations are carried forward over unobserved days. The network's
    input itself is left exactly as deposited.
    """
    x = np.nan_to_num(np.asarray(pw, dtype=np.float64), nan=0.0)
    if raw is not None and np.isfinite(raw).sum() >= 5:
        obs = np.flatnonzero(np.isfinite(raw))
        v = np.asarray(raw, dtype=np.float64)[obs]
        pad = np.pad(v, 2, mode="edge")
        med = np.array([np.median(pad[i:i + 5]) for i in range(len(v))])
        keep = np.abs(v - med) <= 0.25
        obs, v = obs[keep], v[keep]
        x = np.empty(len(pw))
        j = 0
        for t in range(len(pw)):
            while j + 1 < len(obs) and obs[j + 1] <= t:
                j += 1
            x[t] = v[j] if obs[j] <= t else v[0]
    return pick_days(x, n), int(np.argmax(x))


def published_row(lake: str) -> dict | None:
    inf = ESSD / "inference" / "inference_essd" / "essd_revision"
    for split in ("train", "val", "test"):
        f = inf / f"{RUN}_{split}_predictions_bestf1.csv"
        if not f.exists():
            continue
        for row in csv.DictReader(open(f)):
            if row["lake_id"] == lake:
                return {"split": split, "true": row["true_label"],
                        "pred": row["pred_label"],
                        "probs": {c: float(row[f"p_{c}"]) for c in CLASSES}}
    return None


def r(a, n=4):
    return np.round(np.asarray(a, dtype=np.float64), n).tolist()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lakes", nargs="*", default=[l for l, _ in LAKES])
    ap.add_argument("--check-truncation", default="CW2019_1848")
    ap.add_argument("--no-video", action="store_true",
                    help="rewrite manifests + index only; keep the videos")
    ap.add_argument("--run", default=RUN, choices=sorted(RUNS))
    args = ap.parse_args()
    configure(args.run)
    global ENCODE
    ENCODE = not args.no_video
    torch.set_num_threads(4)

    ckpt = require_source(ESSD / "checkpoints" / "essd_revision" /
                          f"lakevision_essd_rev_{RUN}_bestf1.pth")
    stats = require_source(
        ESSD / "revision" / "band_stats_essd_2019only_deposit.json")
    require_source(SRC / "lakevision" / "models" / "classifier.py")
    sys.path.insert(0, str(SRC))
    sys.path.insert(0, str(SRC / "engine" / "inference"))
    from lakevision.models.checkpoint import load_checkpoint
    import run_inference as ri

    state, meta = load_checkpoint(str(ckpt), map_location="cpu")
    config = dict(meta["config"])
    config["band_stats"] = str(stats)      # the config's one cluster-absolute path, pointed at the local copy
    class_names = list(meta["class_names"])
    assert class_names == CLASSES, class_names

    true_of = TRUE_OF
    stacks = [require_source(SOURCE_DATA / "stacks" / "CW_2019" / f"{l}.nc")
              for l in args.lakes]
    labels = {l: CLASSES.index(true_of[l]) for l in args.lakes}
    dataset, model = ri.build_from_config(
        config, class_names, labels, [str(s) for s in stacks],
        torch.device("cpu"))[:2]
    model.load_state_dict(state)
    model.eval()
    n_params = sum(p.numel() for p in model.parameters())
    print(f"run {RUN} · epoch {meta.get('epoch')} · {n_params:,} params · "
          f"git {str(meta.get('git_sha'))[:7]}")
    assert model.temporal_readout == "last" and model.pool_type == "avg"

    fc = model.classifier.fc
    lin1 = [m for m in fc if isinstance(m, torch.nn.Linear)][0]
    lin2 = [m for m in fc if isinstance(m, torch.nn.Linear)][-1]

    # taps: each FrontCNN block's output (after its MaxPool) and the
    # ConvLSTM cell's hidden state per day
    taps: dict = {}
    seq = model.frontcnn.conv_block
    pools = [i for i, m in enumerate(seq) if isinstance(m, torch.nn.MaxPool2d)]
    assert len(pools) == 4, pools
    for k, i in enumerate(pools):
        seq[i].register_forward_hook(
            lambda _m, _i, out, key=f"conv{k + 1}": taps.__setitem__(
                key, out.detach()))
    hidden: list = []
    model.clstm.cell.register_forward_hook(
        lambda _m, _i, out: hidden.append(out[0].detach()))

    trunc = None
    OUT.mkdir(parents=True, exist_ok=True)
    index = {"lakes": [], "classes": CLASSES, "class_names": CLASS_NAMES,
             "colors": COLORS, "t0": T0, "fps": FPS}
    for li, lake in enumerate(args.lakes):
        out = OUT / lake
        out.mkdir(parents=True, exist_ok=True)
        taps.clear()
        hidden.clear()
        sample = dataset[li]
        img, area = sample[0], sample[1]
        cloudy = sample[2] if len(sample) > 2 and torch.is_tensor(sample[2]) else None
        T = img.shape[0]
        with torch.no_grad():
            logits_full = model(img.unsqueeze(0), area.unsqueeze(0),
                                cloudy.unsqueeze(0) if cloudy is not None else None)
            h = torch.cat(hidden, 0)                       # [T, 32, 32, 32]
            gap = h.mean(dim=(-1, -2))                     # [T, 32]
            slstm = model.area_lstm(area.unsqueeze(0))[0]  # [T, 16]
            cat = torch.cat([gap, slstm], 1)               # [T, 48]
            hid = torch.relu(lin1(cat))                    # [T, 64]
            logits = lin2(hid)                             # [T, 5]
            probs = torch.softmax(logits, 1)
        assert torch.allclose(logits[-1], logits_full.reshape(-1), atol=1e-5), \
            (logits[-1], logits_full)
        pf = probs[-1].numpy()
        pw_in = area.numpy().reshape(-1)
        rgb, valid, p_raw = display_rgb_all(stacks[li])
        picks, peak = robust_picks(pw_in, p_raw, 6)
        print(f"\n{lake} ({true_of[lake]})  T={T}  picks {picks}  peak {peak}")
        print("  final: " + "  ".join(f"{c} {p:.3f}" for c, p in zip(CLASSES, pf)))

        if lake == args.check_truncation:
            tcut = picks[3]
            hidden.clear()
            with torch.no_grad():
                lt = model(img[: tcut + 1].unsqueeze(0),
                           area[: tcut + 1].unsqueeze(0),
                           cloudy[: tcut + 1].unsqueeze(0) if cloudy is not None else None)
            d = float((lt.reshape(-1) - logits[tcut]).abs().max())
            print(f"  truncation check at day {tcut}: max |logit delta| {d:.2e}")
            assert d < 1e-4, d
            trunc = {"lake": lake, "day": tcut, "max_abs_logit_delta": d}

        # ── imagery ──
        v = Video(out / "scene.mp4", rgb.shape[2], rgb.shape[1], crf=CRF["scene"],
                  encode=not args.no_video)
        for t in range(T):
            v.write(rgb[t])
        v.close()
        Image.fromarray(rgb[peak]).resize((256, 256), Image.LANCZOS).save(
            out / "thumb.jpg", quality=86)
        stages = {"scene": {"file": "scene.mp4", "shape": [3, 512, 512],
                            "w": v.w, "h": v.h, "vw": v.w, "vh": v.h}}

        x = img.numpy()
        chan_names = ["red", "green", "blue"] + list(
            getattr(dataset, "aux_channel_names", []))
        assert len(chan_names) == x.shape[1], (chan_names, x.shape)
        pretty = {"mask_static": "lake boundary"}
        stages["chan"] = channel_video(
            x, [pretty.get(c, c) for c in chan_names], out)
        for key in ["conv1", "conv2", "conv3", "conv4"]:
            stages[key] = feature_video(taps[key].numpy(), key, out)
        stages["clstm"] = feature_video(h.numpy(), "clstm", out)
        for k, s in stages.items():
            print(f"  {k:6s} {s['shape']}  {s['w']}x{s['h']}  "
                  f"{(out / s['file']).stat().st_size / 1e6:.2f} MB")

        pub = published_row(lake)
        delta = (max(abs(float(pf[i]) - pub["probs"][c])
                     for i, c in enumerate(CLASSES)) if pub else None)
        pred = CLASSES[int(np.argmax(pf))]
        manifest = {
            "lake": lake, "true": true_of[lake],
            "class_name": CLASS_NAMES[true_of[lake]],
            "color": COLORS[true_of[lake]],
            "t0": T0, "days": T, "fps": FPS,
            "default_day": peak, "picks": [int(p) for p in picks],
            "p_water_input": r(pw_in),
            "p_water_raw": (None if p_raw is None else
                            [None if not np.isfinite(v_) else round(float(v_), 4)
                             for v_ in p_raw]),
            "valid_frac": r(valid, 3),
            "stages": stages,
            "vectors": {"gap": r(gap.numpy()), "slstm": r(slstm.numpy()),
                        "hidden": r(hid.numpy()), "logits": r(logits.numpy()),
                        "probs": r(probs.numpy())},
            "prediction": {"probs": {c: float(p) for c, p in zip(CLASSES, pf)},
                           "pred": pred},
            "published": pub,
            "published_max_abs_delta": delta,
            "season_probs": (
                "probs[t] = softmax(head(GAP(ConvLSTM h_t) ++ LSTM h_t)), read "
                "off the full-season pass. Both streams are causal, so this is "
                "the network's output for the season truncated at day t "
                "(checked against a truncated re-run). Inputs are prepared for "
                "the full season (p_water gap-fill + per-lake min-max over all "
                "153 days). The network was trained on full seasons only: every "
                "day before 30 Sep is out of distribution and illustrative; "
                "day 152 is the prediction."),
        }
        (out / "manifest.json").write_text(json.dumps(manifest, separators=(",", ":")))
        print(f"  pred {pred} · published {pub and pub['pred']} ({pub and pub['split']})"
              f" · max|delta| {delta:.4f}")
        index["lakes"].append({
            "id": lake, "true": true_of[lake], "class_name": CLASS_NAMES[true_of[lake]],
            "color": COLORS[true_of[lake]], "pred": pred,
            "p_pred": float(pf[CLASSES.index(pred)]),
            "split": pub and pub["split"], "thumb": f"{lake}/thumb.jpg",
            "published_max_abs_delta": delta})

    m = meta.get("metrics") or {}
    index["model"] = {
        "params": n_params, "checkpoint": ckpt.name, "run": RUN,
        "epoch": meta.get("epoch"), "git_sha": meta.get("git_sha"),
        "split": "CW2019 600/200/200", "val_macro_f1": m.get("f1_macro"),
        "manuscript": "essd-2026-406 version 3, Sect. 5 + Appendix B"}
    # The head's weights, for drawing the MLP (48 -> 64 -> 5).
    index["head"] = {"w1": r(lin1.weight.detach().numpy(), 3),
                     "w2": r(lin2.weight.detach().numpy(), 3)}
    if trunc:
        index["truncation_check"] = trunc
    (OUT / "index.json").write_text(json.dumps(index, separators=(",", ":")))
    total = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"\nwrote {sum(1 for f in OUT.rglob('*') if f.is_file())} files, "
          f"{total / 1e6:.1f} MB -> {OUT}")


if __name__ == "__main__":
    main()
