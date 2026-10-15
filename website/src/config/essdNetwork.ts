// Chapter 3's NETWORK segment — the forward pass, stage by stage.
//
// The segment is the ESSD revision's baseline classifier drawn as a road
// map (EssdNetworkDiagram) with the data at the lit block above it
// (EssdNetworkFigure), for any of the five example lakes. Everything shown
// is baked by cinematic/scene_ch03/build_network.py → R2 ch03/network/.
//
// Beat 0 of the segment is the diagram alone; beats 1… are STAGES in
// forward order. The `network` line of config/ch3Beats.ts must equal
// NETWORK_STAGES.length + 2: the class head has two beats (the director's
// design: arriving there stops the epochs and goes back to the
// beginning; the next NEXT click then shows how the network learns, over
// the epochs, which class it is).

import { mediaUrl } from './media'

export type StageId =
  | 'input' | 'chan'
  | 'conv1' | 'conv2' | 'conv3' | 'conv4'
  | 'clstm' | 'gap'
  | 'pwater' | 'slstm'
  | 'concat' | 'fc' | 'out'

export type StageKind = 'video' | 'vec' | 'curve' | 'mlp' | 'verdict'

export interface StageDef {
  id: StageId
  /** Name on the figure (the block's own name). */
  title: string
  kind: StageKind
  /** Video stages: the manifest's stage key (scene · chan · conv1…). */
  media?: string
  /** Vector stages: which vector(s) from the manifest. */
  vec?: 'gap' | 'slstm' | 'concat'
  /** Draw the feature maps with square pixels (not the photograph). */
  pixelated?: boolean
}

export const NETWORK_STAGES: StageDef[] = [
  { id: 'input', title: 'Sentinel-2', kind: 'video', media: 'scene' },
  { id: 'chan', title: 'input channels', kind: 'video', media: 'chan' },
  { id: 'conv1', title: 'conv block 1', kind: 'video', media: 'conv1', pixelated: true },
  { id: 'conv2', title: 'conv block 2', kind: 'video', media: 'conv2', pixelated: true },
  { id: 'conv3', title: 'conv block 3', kind: 'video', media: 'conv3', pixelated: true },
  { id: 'conv4', title: 'conv block 4', kind: 'video', media: 'conv4', pixelated: true },
  { id: 'clstm', title: 'ConvLSTM hidden state', kind: 'video', media: 'clstm', pixelated: true },
  { id: 'gap', title: 'global average pool', kind: 'vec', vec: 'gap' },
  { id: 'pwater', title: 'p_water', kind: 'curve' },
  { id: 'slstm', title: 'LSTM hidden state', kind: 'vec', vec: 'slstm' },
  { id: 'concat', title: 'concatenate', kind: 'vec', vec: 'concat' },
  { id: 'fc', title: 'hidden 64 · ReLU', kind: 'mlp' },
  { id: 'out', title: 'softmax', kind: 'verdict' },
]

export const STAGE_INDEX: Record<StageId, number> = Object.fromEntries(
  NETWORK_STAGES.map((s, i) => [s.id, i]),
) as Record<StageId, number>

// ── the bake's JSON ──────────────────────────────────────────────────
export interface VideoStage {
  file: string
  shape: number[]
  w: number
  h: number
  vw: number
  vh: number
  rows?: number
  cols?: number
  tile?: number
  gutter?: number
  channels?: string[]
}
export interface NetManifest {
  lake: string
  true: string
  class_name: string
  color: string
  t0: string
  days: number
  fps: number
  default_day: number
  picks: number[]
  p_water_input: number[]
  p_water_raw: (number | null)[] | null
  valid_frac: number[]
  stages: Record<string, VideoStage>
  vectors: {
    gap: number[][]
    slstm: number[][]
    hidden: number[][]
    logits: number[][]
    probs: number[][]
  }
  prediction: { probs: Record<string, number>; pred: string }
  published: { split: string; true: string; pred: string; probs: Record<string, number> } | null
  published_max_abs_delta: number | null
}
export interface NetIndexLake {
  id: string
  true: string
  class_name: string
  color: string
  pred: string
  p_pred: number
  split: string | null
  thumb: string
}
export interface NetIndex {
  lakes: NetIndexLake[]
  classes: string[]
  class_names: Record<string, string>
  colors: Record<string, string>
  t0: string
  fps: number
  model: { params: number; epoch: number }
  head: { w1: number[][]; w2: number[][] }
}

export const NET_PREFIX = 'ch03/network'
export function netUrl(f: string): string {
  return mediaUrl(`${NET_PREFIX}/${f}`)
}

// ── the TAXONOMY (the director asked for a toggle at the bottom right
// reading TAXONOMY, with 4-class and 5-class below it). The 5-class
// model is the talk's; the 4-class one (HF + MD merged into HFMD, the run
// y2019_4c_pw_noaug, best validation macro-F1 0.738 at epoch 363) is the
// same walkthrough baked under its own prefixes. Never on the NEXT path. ──
export type Taxonomy = '5c' | '4c'
const NET_PREFIXES: Record<Taxonomy, { day: string; epoch: string }> = {
  '5c': { day: 'ch03/network', epoch: 'ch03/network_epochs' },
  '4c': { day: 'ch03/network_4c', epoch: 'ch03/network_epochs_4c' },
}
/** The DAY-axis URL maker for a taxonomy. */
export function netUrlOf(t: Taxonomy): (f: string) => string {
  return (f) => mediaUrl(`${NET_PREFIXES[t].day}/${f}`)
}
/** The EPOCH-axis URL maker for a taxonomy. */
export function netEpochUrlOf(t: Taxonomy): (f: string) => string {
  return (f) => mediaUrl(`${NET_PREFIXES[t].epoch}/${f}`)
}
/** The EPOCH axis's index (index_v2 = index + the loss curves). */
export const EPOCH_INDEX_FILE = 'index_v2.json'
/** A class code as the figures write it (the four-class run's merged class
 *  is "HFMD" in its checkpoint; Chapter 3's training beat writes HF+MD). */
export function classLabel(c: string): string {
  return c === 'HFMD' ? 'HF+MD' : c
}

// ── the EPOCH axis (build_network_epochs.py → R2 ch03/network_epochs/) ──
// The DAY axis holds the weights (epoch 189, best validation F1) and walks
// the season; the EPOCH axis holds the data and walks training: every
// 5-epoch checkpoint plus the best-F1 one, 81 frames. The per-frame stages
// (conv 1–4) are baked at the lake's peak day (`image_day`), the recurrent
// state and everything after it at the season end (`state_day`, 30 Sep).
// The imagery, the channels and p_water are data — the DAY videos serve
// them, frozen at `image_day`.
export type Axis = 'day' | 'epoch'
export const NET_EPOCH_PREFIX = 'ch03/network_epochs'
export function netEpochUrl(f: string): string {
  return mediaUrl(`${NET_EPOCH_PREFIX}/${f}`)
}
/** Stages whose figure changes with the epoch (the rest are data). */
export const EPOCH_MEDIA = new Set(['conv1', 'conv2', 'conv3', 'conv4', 'clstm'])
export interface EpochManifest {
  lake: string
  true: string
  epochs: number[]
  best_index: number
  image_day: number
  state_day: number
  fps: number
  stages: Record<string, VideoStage>
  vectors: {
    gap: number[][]
    slstm: number[][]
    hidden: number[][]
    logits: number[][]
    probs: number[][]
  }
  pred: string[]
}
export interface EpochIndex {
  epochs: number[]
  best_index: number
  best_epoch: number
  last_epoch: number
  frames: { epoch: number; best: boolean; val_f1: number }[]
  curves: {
    epoch: number[]
    val_f1: number[]
    train_f1: number[]
    /** index_v2: the losses, for the scrubber's second axis. */
    val_loss?: number[]
    train_loss?: number[]
  }
  /** The head's first layer per frame, int8 × scale ([64][48] row-major). */
  w1: { scale: number; b64: string }[]
}
/** Decode one frame's w1 into [64][48]. */
export function decodeW1(w: { scale: number; b64: string }, rows = 64, cols = 48): number[][] {
  const bin = atob(w.b64)
  const out: number[][] = []
  for (let j = 0; j < rows; j++) {
    const row: number[] = []
    for (let i = 0; i < cols; i++) {
      let b = bin.charCodeAt(j * cols + i)
      if (b > 127) b -= 256
      row.push(b * w.scale)
    }
    out.push(row)
  }
  return out
}

// ── colour ───────────────────────────────────────────────────────────
// Diverging for the recurrent states (they live in (−1, 1)): teal below
// zero, the site's gold above, near-black at zero.
const NEG: [number, number, number] = [79, 182, 196]
const MID: [number, number, number] = [22, 20, 17]
const POS: [number, number, number] = [244, 207, 106]
function mix(a: number[], b: number[], t: number): [number, number, number] {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]
}
/** v in [−1, 1] → rgb. */
export function diverging(v: number): [number, number, number] {
  const t = Math.max(-1, Math.min(1, v))
  return t < 0 ? mix(MID, NEG, Math.pow(-t, 0.8)) : mix(MID, POS, Math.pow(t, 0.8))
}
export function rgbCss(c: [number, number, number]): string {
  return `rgb(${c[0] | 0},${c[1] | 0},${c[2] | 0})`
}

/** Day index → "12 JUN". */
export function dayLabel(t0: string, d: number): string {
  const t = new Date(new Date(`${t0}T00:00:00Z`).getTime() + d * 86400e3)
  return t
    .toLocaleDateString('en-GB', { day: '2-digit', month: 'short', timeZone: 'UTC' })
    .toUpperCase()
}

/** Symmetric scale for a [T][N] series: the season's largest |v|. */
export function symScale(rows: number[][]): number {
  let m = 0
  for (const r of rows) for (const v of r) m = Math.max(m, Math.abs(v))
  return m || 1
}
