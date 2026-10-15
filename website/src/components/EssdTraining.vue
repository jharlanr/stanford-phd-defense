<template>
  <!-- Ch.3, the TRAINING segment — the ESSD revision's Appendix B made
       dynamic: Fig. B2's training curves beside Fig. B3's confusion
       matrices, one epoch clock driving both. Five steps (the director's
       script: start at the beginning of training, go through the 400
       epochs, then at the NEXT click roll back to show the TEST at the
       best-validation epoch; the same again for the four-class run):
         0  five-class (with p_water): ARRIVING plays training from epoch 1
            to 400 (30 epochs/s ≈ 13 s — the curves draw up to the cursor,
            the train/val matrices tick as the log has them, test empty)
            and RESTS at 400; BACK from step 1 lands on that rest
         1  NEXT: the cursor ROLLS BACK to the best-validation epoch (189,
            1.4 s), the matrices pin to the best checkpoint and the TEST
            matrix appears; pressed mid-play it stops and rolls back from
            wherever the clock is
         2  the hard pairs: the HF–MD and MD–LD 2×2 blocks outlined on the
            three matrices, everything else dimmed (the labelers' matrix
            that used to take the training slot is gone — the director
            wanted only the training confusion matrix here)
         3  four-class (HF + MD merged): the HF and MD rows/columns slide
            together into one while the five-class panel fades out; the
            four-class panel fades in AT EPOCH 1 (no landing
            on 363, no rewind), a short hold, and the four-class run plays
            1→400 the same way, resting at 400
         4  NEXT: roll back to its best epoch (363), matrices pinned, TEST
         5  NEXT: the middle 2×2 (HF+MD–LD) outlined on the four-class
            matrices — the same beat as 2
       The TEST matrix shows only on the pinned steps (1, 2, 4, 5), never
       while the clock passes the best epoch mid-play (the director did not
       want the TEST matrix flashing before the NEXT click).
       Deep links land each step's settled state; steps 0 and 3 play from
       epoch 1 on a deep link too (that is what the beat is). The play
       button on steps 0/3 replays and rests at 400; on 1/2/4 it replays
       and lands back on the best epoch. A scrub or pause stops any
       auto-play.
       Data: ch03/training/training_dynamics_v2.json
       (cinematic/scene_ch03/build_training_dynamics.py — every number at
       rest is asserted there against Table B2 / Fig. B3). Per-epoch
       matrices appear only where the JSON has them (`confusion_by_epoch`,
       from the training log); otherwise the matrices are empty away from
       the best epoch — nothing is interpolated. -->
  <div class="tr-root">
    <svg
      v-if="doc"
      class="tr-svg"
      :viewBox="`0 0 ${VW} ${VH}`"
      preserveAspectRatio="xMidYMid meet"
    >
      <defs>
        <clipPath v-for="P in PANELS" :id="`tr-clip-${P.key}`" :key="`clip-${P.key}`">
          <rect :x="P.x0 - 4" :y="P.y0 - 30" :width="Math.max(0, revealX - P.x0 + 5)" :height="P.y1 - P.y0 + 60" />
        </clipPath>
      </defs>

      <!-- ── the two curve panels ── -->
      <g v-for="P in PANELS" :key="P.key" :transform="`translate(${P.off} 0)`">
        <rect class="tr-panel" x="0" y="0" :width="PANEL_W" :height="CURVE_H" rx="14" />
        <text class="tr-ptitle" :x="P.x0" y="38">{{ P.key === 'loss' ? 'Loss' : 'F' }}<tspan v-if="P.key === 'f1'" class="tr-sub" dy="6">1</tspan></text>
        <!-- grid + ticks -->
        <g class="tr-grid">
          <line v-for="t in P.yticks" :key="`gy${t}`" :x1="P.x0" :x2="P.x1" :y1="P.sy(t)" :y2="P.sy(t)" />
        </g>
        <g class="tr-tick">
          <text v-for="t in P.yticks" :key="`ty${t}`" :x="P.x0 - 10" :y="P.sy(t) + 6" text-anchor="end">{{ P.fmt(t) }}</text>
          <text v-for="t in XTICKS" :key="`tx${t}`" :x="sx(t)" :y="P.y1 + 26" text-anchor="middle">{{ t }}</text>
        </g>
        <text class="tr-axis" :x="(P.x0 + P.x1) / 2" :y="P.y1 + 50" text-anchor="middle">Epoch</text>
        <line class="tr-baseline" :x1="P.x0" :x2="P.x1" :y1="P.y1" :y2="P.y1" />

        <!-- one layer per run; the four-class layer fades in with the merge -->
        <g
          v-for="R in runLayers"
          :key="`${P.key}-${R.key}`"
          :opacity="R.opacity"
          :style="{ display: R.opacity < 0.005 ? 'none' : undefined }"
        >
          <!-- random-guess reference (F1 only) -->
          <line
            v-if="P.key === 'f1'"
            class="tr-random"
            :x1="P.x0" :x2="P.x1"
            :y1="P.sy(R.doc.random_f1)" :y2="P.sy(R.doc.random_f1)"
            :opacity="dimOther"
          />
          <text
            v-if="P.key === 'f1'"
            class="tr-random-lbl"
            :x="P.x1 - 6"
            :y="P.sy(R.doc.random_f1) + 20"
            text-anchor="end"
            :opacity="dimOther"
          >random {{ R.doc.random_f1.toFixed(2) }}</text>
          <!-- best-validation epoch -->
          <line class="tr-best" :x1="sx(R.doc.best_epoch)" :x2="sx(R.doc.best_epoch)" :y1="P.y0" :y2="P.y1" />
          <text
            v-if="P.key === 'f1'"
            class="tr-best-lbl"
            :x="sx(R.doc.best_epoch)"
            :y="P.y0 - 24"
            :text-anchor="sx(R.doc.best_epoch) > P.x1 - 110 ? 'end' : 'middle'"
          >best val · epoch {{ R.doc.best_epoch }}</text>
          <g :clip-path="`url(#tr-clip-${P.key})`">
            <template v-if="P.key === 'loss'">
              <path class="tr-line tr-train" :d="R.paths.lossTrain" :opacity="dimLoss" />
              <path class="tr-line tr-val tr-dash" :d="R.paths.lossVal" :opacity="dimLoss" />
            </template>
            <template v-else>
              <path
                v-for="c in R.doc.classes"
                :key="`pc-${c}`"
                class="tr-pc"
                :d="R.paths.perClass[c]"
                :stroke="R.doc.colors[c]"
                :opacity="HARD.has(c) ? 1 : dimOther"
              />
              <path class="tr-line tr-train tr-thick" :d="R.paths.f1Train" :opacity="dimOther" />
              <path class="tr-line tr-val tr-thick" :d="R.paths.f1Val" :opacity="dimOther" />
            </template>
          </g>
          <!-- direct labels at the revealed end of every line -->
          <text
            v-for="L in R.labels[P.key]"
            :key="`lbl-${L.id}`"
            class="tr-dlabel"
            :x="L.x + 10"
            :y="L.y + 6"
            :fill="L.color"
            :opacity="L.dim"
          >{{ L.text }}</text>
          <!-- cursor dots -->
          <circle
            v-for="D in R.dots[P.key]"
            :key="`dot-${D.id}`"
            class="tr-dot"
            :cx="D.x" :cy="D.y" r="5.5"
            :fill="D.color"
          />
        </g>
        <!-- the epoch cursor (hidden at rest: the best line is the cursor) -->
        <line
          v-if="cursorVisible"
          class="tr-cursor"
          :x1="sx(epoch)" :x2="sx(epoch)" :y1="P.y0" :y2="P.y1"
        />
      </g>

      <!-- ── the three confusion matrices ── -->
      <g v-for="(S, si) in slots" :key="`slot-${si}`" :transform="`translate(${S.x} ${MAT_Y})`">
        <rect class="tr-panel" x="0" y="0" :width="SLOT_W" :height="MAT_H" rx="14" />
        <!-- title + subtitle; crossfades (training ↔ human, five ↔ four) -->
        <text
          v-for="T in S.titles"
          :key="`t-${T.id}`"
          class="tr-mtitle"
          :x="SLOT_W / 2" y="40"
          text-anchor="middle"
          :opacity="T.a"
        >{{ T.title }}</text>
        <text
          v-for="T in S.titles"
          :key="`s-${T.id}`"
          class="tr-msub"
          :x="SLOT_W / 2" y="68"
          text-anchor="middle"
          :opacity="T.a"
        >{{ T.sub }}</text>

        <g :transform="`translate(${GX} ${GY})`">
          <!-- empty cells underneath (opaque, so merged cells never double) -->
          <rect
            v-for="c in baseCells"
            :key="`b-${c.id}`"
            :x="c.x" :y="c.y" :width="c.w" :height="c.h" rx="6"
            :fill="EMPTY"
          />
          <!-- data layers -->
          <g v-for="Lr in S.layers" :key="`ly-${Lr.id}`" :opacity="Lr.a" :style="{ display: Lr.a < 0.005 ? 'none' : undefined }">
            <g v-for="c in Lr.cells" :key="`c-${c.id}`">
              <rect :x="c.x" :y="c.y" :width="c.w" :height="c.h" rx="6" :fill="c.fill" :class="{ 'tr-diag': c.diag }" :stroke-opacity="c.diag ? c.diagA : undefined">
                <title>{{ c.tip }}</title>
              </rect>
              <text
                class="tr-count"
                :x="c.x + c.w / 2" :y="c.y + c.h / 2 + c.fs * 0.12"
                text-anchor="middle"
                :font-size="c.fs"
                :fill="c.ink"
              >{{ c.count }}</text>
              <text
                class="tr-pct"
                :x="c.x + c.w / 2" :y="c.y + c.h / 2 + c.fs * 0.12 + c.fs * 0.78"
                text-anchor="middle"
                :font-size="c.fs * 0.68"
                :fill="c.ink"
              >{{ c.pct }}</text>
            </g>
          </g>
          <!-- the hard pairs: HF–MD and MD–LD blocks (step 2); the four-class middle block (step 5) -->
          <!-- Same look as the human matrices' ConfusionBlockOutlines
               (the director asked for exactly that style): a 3 px light
               border with a dark halo, fading + settling in. -->
          <g v-if="hardA > 0.005" class="tr-hard" :opacity="hardA">
            <g
              v-for="B in hardBlocks"
              :key="`hb-${B.id}`"
              :transform="`translate(${B.x + B.w / 2} ${B.y + B.h / 2}) scale(${1 + 0.12 * (1 - hardA)}) translate(${-(B.x + B.w / 2)} ${-(B.y + B.h / 2)})`"
            >
              <rect class="tr-hard-halo" :x="B.x" :y="B.y" :width="B.w" :height="B.h" rx="9" />
              <rect class="tr-hard-line" :x="B.x" :y="B.y" :width="B.w" :height="B.h" rx="9" />
            </g>
          </g>
          <!-- class heads: rows left, columns below -->
          <text
            v-for="Hd in heads.rows"
            :key="`rh-${Hd.id}`"
            class="tr-head"
            :x="-12" :y="Hd.pos + 7"
            text-anchor="end"
            :fill="Hd.color" :opacity="Hd.a"
          >{{ Hd.text }}</text>
          <text
            v-for="Hd in heads.cols"
            :key="`ch-${Hd.id}`"
            class="tr-head"
            :x="Hd.pos" :y="GRID + 30"
            text-anchor="middle"
            :fill="Hd.color" :opacity="Hd.a"
          >{{ Hd.text }}</text>
          <text
            v-for="T in S.axes"
            :key="`ax-${T.id}`"
            class="tr-axis"
            :x="GRID / 2" :y="GRID + 60"
            text-anchor="middle"
            :opacity="T.a"
          >{{ T.x }}</text>
          <text
            v-for="T in S.axes"
            :key="`ay-${T.id}`"
            class="tr-axis"
            :transform="`translate(-90 ${GRID / 2}) rotate(-90)`"
            text-anchor="middle"
            :opacity="T.a"
          >{{ T.y }}</text>
        </g>
      </g>
    </svg>

    <!-- ── the epoch clock: play/pause + scrub (the site's timebar) ── -->
    <div v-if="doc" class="tr-clock">
      <button class="tr-play" :aria-label="playing ? 'Pause' : 'Play'" @click="togglePlay">
        {{ playing ? '❚❚' : '▶' }}
      </button>
      <div class="tr-scrub-wrap">
        <input
          class="tr-scrub"
          type="range" min="1" :max="EPOCHS" step="1"
          :value="Math.round(epoch)"
          :style="{ '--fill': `${(100 * (epoch - 1)) / (EPOCHS - 1)}%` }"
          aria-label="Epoch"
          @input="onScrub"
        />
        <span class="tr-best-tick" :style="{ left: `${(100 * (activeRun.best_epoch - 1)) / (EPOCHS - 1)}%` }" />
      </div>
      <span class="tr-epoch">epoch {{ Math.round(epoch) }}</span>
    </div>
  </div>
</template>

<script lang="ts">
import { mediaUrl } from '../config/media'

// The two small JSONs, fetched once per page and shared by every mount;
// warmed a few seconds after the app loads so entering the segment never
// waits on the network (27 kB + 2 kB).
let loadOnce: Promise<[unknown, unknown]> | null = null
function getJson(name: string): Promise<unknown> {
  return fetch(mediaUrl(name)).then((r) => {
    if (!r.ok) throw new Error(`${name} ${r.status}`)
    return r.json()
  })
}
function loadTrainingData(): Promise<[unknown, unknown]> {
  if (!loadOnce) {
    loadOnce = Promise.all([
      getJson('ch03/training/training_dynamics_v2.json'),
      getJson('ch03/essd_irr.json').catch(() => null),
    ])
    loadOnce.catch(() => { loadOnce = null }) // a failure may retry next mount
  }
  return loadOnce
}
if (typeof window !== 'undefined') window.setTimeout(() => { loadTrainingData().catch(() => {}) }, 6000)
</script>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{ step: number }>()

// ── data ───────────────────────────────────────────────────────────────
type Split = 'train' | 'val' | 'test'
interface BestSplit { n: number; cm: number[][]; macro_f1: number; acc: number; f1: Record<string, number> }
interface RunDoc {
  run: string
  classes: string[]
  colors: Record<string, string>
  random_f1: number
  best_epoch: number
  curves: { train_loss: number[]; val_loss: number[]; train_f1: number[]; val_f1: number[] }
  per_class_val: Record<string, number[]> & { epoch: number[] }
  best: Record<Split, BestSplit>
  confusion_by_epoch: { epochs?: number[]; train?: number[][][]; val?: number[][][] }
}
interface TrainingDoc { epochs: number; runs: { '5c': RunDoc; '4c': RunDoc } }
interface IrrFile {
  n: number
  class_order: string[]
  pairs: { row: number; col: number; counts: number[][]; agreement: number | null }[]
}
const doc = ref<TrainingDoc | null>(null)
const irr = ref<IrrFile | null>(null)

// ── geometry (one SVG, viewBox units; scales with the screen) ─────────
const VW = 1600
const VH = 830
const PANEL_W = 770
const CURVE_H = 320
const EPOCHS = 400
const XTICKS = [0, 100, 200, 300, 400]
const X0 = 78
const X1 = PANEL_W - 92
const Y0 = 64
const Y1 = CURVE_H - 62
const LOSS_MAX = 1.8 // same for both runs so the beats compare
function sx(e: number): number {
  return X0 + (e / EPOCHS) * (X1 - X0)
}
const syLoss = (v: number): number => Y1 - (Math.min(v, LOSS_MAX) / LOSS_MAX) * (Y1 - Y0)
const syF1 = (v: number): number => Y1 - v * (Y1 - Y0)
const PANELS = [
  { key: 'loss' as const, off: 0, x0: X0, x1: X1, y0: Y0, y1: Y1, sy: syLoss, yticks: [0, 0.5, 1, 1.5], fmt: (t: number) => t.toFixed(1) },
  { key: 'f1' as const, off: VW - PANEL_W, x0: X0, x1: X1, y0: Y0, y1: Y1, sy: syF1, yticks: [0, 0.2, 0.4, 0.6, 0.8, 1], fmt: (t: number) => t.toFixed(1) },
]

const MAT_Y = CURVE_H + 30
const MAT_H = VH - MAT_Y
const SLOT_W = 500
const SLOT_GAP = (VW - 3 * SLOT_W) / 2
const GRID = 316 // the cells' square
const GX = (SLOT_W - GRID) / 2 + 22
const GY = 90
const GAP = 4
const STEP5 = (GRID + GAP) / 5
const S5 = STEP5 - GAP
const STEP4 = (GRID + GAP) / 4
const S4 = STEP4 - GAP
const K4 = [0, 1, 1, 2, 3] // five-class index → four-class index (HF, MD → HF+MD)
const REPS4 = [[0], [1, 2], [3], [4]] // four-class index → its five-class indices
const MERGED_COLOR = '#26a69a' // Fig. B2's own HFMD teal
const HARD = new Set(['HF', 'MD', 'LD'])

// ── state: the epoch clock + three tweened levers ─────────────────────
const epoch = ref(189)
const replay = ref(false) // true while (or after) replaying from epoch 1
const playing = ref(false)
// At rest (entering a step, or landing after a replay) the matrices are
// PINNED to the best checkpoint's, whatever the cursor is doing mid-tween;
// playing or scrubbing unpins them so they follow the epoch.
const pinBest = ref(true)
const hardT = ref(0) // step 1's hard-pair highlight
const humanT = ref(0) // training slot → the human labelers' matrix
const mergeT = ref(0) // five → four classes
// true while the merge is carrying the page INTO the four-class play
// (2 → 3): the four-class run arrives at the beginning of its training
const mergeToStart = ref(false)

const activeKey = computed<'5c' | '4c'>(() => (mergeT.value >= 0.5 ? '4c' : '5c'))
const activeRun = computed<RunDoc>(() => doc.value!.runs[activeKey.value])

function smooth(a: number, b: number, x: number): number {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)))
  return t * t * (3 - 2 * t)
}
function ease(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}

// tweens
const tweens = new Map<string, number>()
function tween(key: string, from: number, to: number, ms: number, set: (v: number) => void, done?: () => void, fn: (t: number) => number = ease): void {
  const prev = tweens.get(key)
  if (prev != null) cancelAnimationFrame(prev)
  if (ms <= 0 || from === to) {
    set(to)
    tweens.delete(key)
    done?.()
    return
  }
  const t0 = performance.now()
  const tick = (now: number) => {
    const t = Math.min(1, (now - t0) / ms)
    set(from + (to - from) * fn(t))
    if (t < 1) tweens.set(key, requestAnimationFrame(tick))
    else {
      tweens.delete(key)
      done?.()
    }
  }
  tweens.set(key, requestAnimationFrame(tick))
}

// ── curves ────────────────────────────────────────────────────────────
function pathOf(xs: number[], ys: number[], sy: (v: number) => number): string {
  let d = ''
  for (let i = 0; i < xs.length; i++) d += `${i ? 'L' : 'M'}${sx(xs[i]).toFixed(1)},${sy(ys[i]).toFixed(1)}`
  return d
}
const EP = Array.from({ length: EPOCHS }, (_, i) => i + 1)
const runPaths = computed(() => {
  const d = doc.value
  if (!d) return null
  const out: Record<string, { lossTrain: string; lossVal: string; f1Train: string; f1Val: string; perClass: Record<string, string> }> = {}
  for (const k of ['5c', '4c'] as const) {
    const r = d.runs[k]
    const perClass: Record<string, string> = {}
    for (const c of r.classes) perClass[c] = pathOf(r.per_class_val.epoch, r.per_class_val[c], syF1)
    out[k] = {
      lossTrain: pathOf(EP, r.curves.train_loss, syLoss),
      lossVal: pathOf(EP, r.curves.val_loss, syLoss),
      f1Train: pathOf(EP, r.curves.train_f1, syF1),
      f1Val: pathOf(EP, r.curves.val_f1, syF1),
      perClass,
    }
  }
  return out
})

// how far the curves are drawn: all 400 epochs at rest, up to the cursor
// while replaying (`reveal` overrides the cursor when set — the four-class
// arrival's old rewind used it; nothing sets it now)
const reveal = ref<number | null>(null)
const revealEpoch = computed(() => (replay.value ? Math.max(1, reveal.value ?? epoch.value) : EPOCHS))
const revealX = computed(() => sx(revealEpoch.value))
const cursorVisible = computed(() => replay.value || Math.round(epoch.value) !== activeRun.value.best_epoch)

const dimOther = computed(() => 1 - 0.62 * hardT.value)
const dimLoss = computed(() => 1 - 0.5 * hardT.value)

function lastSample(r: RunDoc, e: number): number {
  // index of the last per-class sample at or before epoch e
  const ep = r.per_class_val.epoch
  let k = 0
  for (let i = 0; i < ep.length; i++) if (ep[i] <= e) k = i
  return k
}

interface Lbl { id: string; x: number; y: number; text: string; color: string; dim: number }
// Push direct labels apart vertically (min gap), keep them inside the plot.
function declutter(ls: Lbl[], gap: number): Lbl[] {
  const s = [...ls].sort((a, b) => a.y - b.y)
  for (let it = 0; it < 6; it++) {
    for (let i = 1; i < s.length; i++) {
      const d = s[i].y - s[i - 1].y
      if (d < gap) {
        const push = (gap - d) / 2
        s[i - 1].y -= push
        s[i].y += push
      }
    }
  }
  const lo = Y0 - 4
  const hi = Y1 + 4
  if (s.length && s[0].y < lo) {
    const sh = lo - s[0].y
    for (const l of s) l.y += sh
  }
  if (s.length && s[s.length - 1].y > hi) {
    const sh = s[s.length - 1].y - hi
    for (const l of s) l.y -= sh
  }
  return s
}

const CREAM = '#f5f0e6'
const GOLD = '#f4cf6a'
const runLayers = computed(() => {
  const d = doc.value
  const P = runPaths.value
  if (!d || !P) return []
  // The two runs' curves crossfade through the merge — except on the way
  // INTO the four-class play (`mergeToStart`): there the five-class curves
  // fade right out before the four-class ones begin, so the clock can
  // return to epoch 1 while nothing is drawn.
  const out5 = mergeToStart.value ? smooth(0.1, 0.45, mergeT.value) : smooth(0.2, 0.8, mergeT.value)
  const in4 = mergeToStart.value ? smooth(0.55, 0.8, mergeT.value) : smooth(0.2, 0.8, mergeT.value)
  const e = Math.max(1, Math.min(EPOCHS, Math.round(epoch.value)))
  const eEnd = Math.max(1, Math.min(EPOCHS, Math.round(revealEpoch.value)))
  return (['5c', '4c'] as const).map((key) => {
    const r = d.runs[key]
    const xEnd = sx(eEnd)
    const k = lastSample(r, eEnd)
    const lossLbl: Lbl[] = [
      { id: 'lt', x: xEnd, y: syLoss(r.curves.train_loss[eEnd - 1]), text: 'train', color: CREAM, dim: dimLoss.value },
      { id: 'lv', x: xEnd, y: syLoss(r.curves.val_loss[eEnd - 1]), text: 'val', color: GOLD, dim: dimLoss.value },
    ]
    const f1Lbl: Lbl[] = [
      { id: 'ft', x: xEnd, y: syF1(r.curves.train_f1[eEnd - 1]), text: 'train', color: CREAM, dim: dimOther.value },
      { id: 'fv', x: xEnd, y: syF1(r.curves.val_f1[eEnd - 1]), text: 'val', color: GOLD, dim: dimOther.value },
      ...r.classes.map((c) => ({
        id: `pc-${c}`,
        x: sx(r.per_class_val.epoch[k]),
        y: syF1(r.per_class_val[c][k]),
        text: c === 'HFMD' ? 'HF+MD' : c,
        color: r.colors[c],
        dim: HARD.has(c) || c === 'HFMD' ? 1 : dimOther.value,
      })),
    ]
    // labels sit in the right margin at the revealed end; per-class ones
    // share the column so they declutter together
    for (const l of f1Lbl) l.x = Math.max(l.x, xEnd)
    const dots = {
      loss: [
        { id: 'lt', x: sx(e), y: syLoss(r.curves.train_loss[e - 1]), color: CREAM },
        { id: 'lv', x: sx(e), y: syLoss(r.curves.val_loss[e - 1]), color: GOLD },
      ],
      f1: [
        { id: 'ft', x: sx(e), y: syF1(r.curves.train_f1[e - 1]), color: CREAM },
        { id: 'fv', x: sx(e), y: syF1(r.curves.val_f1[e - 1]), color: GOLD },
      ],
    }
    return {
      key,
      doc: r,
      paths: P[key],
      opacity: key === '5c' ? 1 - out5 : in4,
      labels: { loss: declutter(lossLbl, 23), f1: declutter(f1Lbl, 22) },
      dots,
    }
  })
})

// ── matrices ──────────────────────────────────────────────────────────
// What a split's matrix is at an epoch: the best checkpoint's (Fig. B3,
// from the prediction CSVs) AT the best epoch; the training log's (printed
// every 10 epochs, train + val only) elsewhere when the JSON carries them;
// otherwise nothing. The test split is scored once, at the best epoch.
function matAt(r: RunDoc, split: Split, e: number): number[][] | null {
  // the test split only once pinned — the clock passing the best epoch
  // mid-play used to flash it
  if (split === 'test') return pinBest.value ? r.best[split].cm : null
  if (pinBest.value || Math.round(e) === r.best_epoch) return r.best[split].cm
  const cbe = r.confusion_by_epoch
  const eps = cbe?.epochs
  const mats = cbe?.[split]
  if (!eps || !mats || !eps.length) return null
  let k = -1
  for (let i = 0; i < eps.length; i++) if (eps[i] <= e) k = i
  return k >= 0 ? mats[k] : null
}
function macroF1(cm: number[][]): number {
  const k = cm.length
  let s = 0
  for (let i = 0; i < k; i++) {
    const tp = cm[i][i]
    let fp = 0
    let fn = 0
    for (let j = 0; j < k; j++) {
      if (j !== i) {
        fp += cm[j][i]
        fn += cm[i][j]
      }
    }
    const den = 2 * tp + fp + fn
    s += den ? (2 * tp) / den : 0
  }
  return s / k
}

// Opaque cell colours: the IRR matrices' gold ramp composited onto the
// panel, so overlapping (merging) cells never double up.
const PANEL_RGB = [13, 12, 10]
const GOLD_RGB = [244, 207, 106]
function mixGold(f: number, dim = 1): string {
  const a = 0.06 + 0.9 * Math.pow(f, 0.85)
  const c = PANEL_RGB.map((p, i) => Math.round((p + (GOLD_RGB[i] - p) * a) * dim))
  return `rgb(${c[0]},${c[1]},${c[2]})`
}
const EMPTY = mixGold(0)

function geom5(i: number, g: number): { p: number; w: number } {
  return { p: STEP5 * i + (STEP4 * K4[i] - STEP5 * i) * g, w: S5 + (S4 - S5) * g }
}
function geom4(k: number, g: number): { p: number; w: number } {
  const reps = REPS4[k].map((i) => geom5(i, g))
  const p = Math.min(...reps.map((r) => r.p))
  const q = Math.max(...reps.map((r) => r.p + r.w))
  return { p, w: q - p }
}
function inHard(i: number, j: number): boolean {
  // five-class indices ND 0, HF 1, MD 2, LD 3, CD 4: the HF–MD block
  // (1..2 × 1..2) and the MD–LD block (2..3 × 2..3)
  return (i >= 1 && i <= 2 && j >= 1 && j <= 2) || (i >= 2 && i <= 3 && j >= 2 && j <= 3)
}

interface Cell { id: string; x: number; y: number; w: number; h: number; fill: string; ink: string; count: string; pct: string; fs: number; diag: boolean; diagA: number; tip: string }
function cellsFor(cm: number[][] | null, names: string[], geom: (i: number, g: number) => { p: number; w: number }, g: number, hard: boolean, rowName: string, colName: string): Cell[] {
  const k = names.length
  const out: Cell[] = []
  for (let i = 0; i < k; i++) {
    const row = cm ? cm[i] : null
    const rs = row ? row.reduce((a, b) => a + b, 0) : 0
    const gy = geom(i, g)
    for (let j = 0; j < k; j++) {
      const gx = geom(j, g)
      const dim = hard && !inHard(i, j) ? 1 - 0.55 * hardT.value : 1
      const v = row ? row[j] : 0
      const f = rs ? v / rs : 0
      out.push({
        id: `${i}-${j}`,
        x: gx.p, y: gy.p, w: gx.w, h: gy.w,
        fill: row ? mixGold(f, dim) : mixGold(0, dim),
        ink: !row ? 'transparent' : f > 0.55 ? `rgba(26,20,8,${dim})` : `rgba(245,240,230,${dim})`,
        count: row ? String(v) : '',
        pct: row ? `${Math.round(f * 100)}%` : '',
        fs: 0.36 * Math.min(gx.w, gy.w),
        diag: i === j,
        // The diagonal's thin rule steps out with the cells the hard-pairs
        // beat dims: on that beat an outline means "a hard pair", and the
        // rule left standing on ND and CD read as two more of them (the
        // director saw the ND and CD diagonal cells outlined and asked for
        // them not to be).
        diagA: hard && !inHard(i, j) ? 1 - hardT.value : 1,
        tip: row ? `${rowName} ${names[i]} → ${colName} ${names[j]}: ${v} of ${rs} (${Math.round(f * 100)}%)` : '',
      })
    }
  }
  return out
}

// mergeT runs LINEARLY (2.6 s); each phase eases on its own window:
// numbers out 0–0.25 · cells slide 0.15–0.85 · HF+MD label 0.55–0.9 ·
// four-class numbers in 0.75–1 · curves crossfade 0.2–0.8
const gMerge = computed(() => ease(Math.max(0, Math.min(1, (mergeT.value - 0.15) / 0.7))))
const baseCells = computed(() => {
  const g = gMerge.value
  const out: { id: string; x: number; y: number; w: number; h: number }[] = []
  for (let i = 0; i < 5; i++) {
    for (let j = 0; j < 5; j++) {
      const a = geom5(j, g)
      const b = geom5(i, g)
      out.push({ id: `${i}-${j}`, x: a.p, y: b.p, w: a.w, h: b.w })
    }
  }
  return out
})

const heads = computed(() => {
  const g = gMerge.value
  const five = ['ND', 'HF', 'MD', 'LD', 'CD']
  const colors: Record<string, string> = { ND: '#e8524a', HF: '#4caf50', MD: '#42a5f5', LD: '#ff9800', CD: '#ab47bc' }
  const aMerged = smooth(0.55, 0.9, mergeT.value)
  const mk = (axis: 'r' | 'c') => {
    const list = five.map((c, i) => {
      const gg = geom5(i, g)
      return {
        id: `${axis}${c}`,
        text: c,
        color: colors[c],
        pos: gg.p + gg.w / 2,
        a: c === 'HF' || c === 'MD' ? 1 - aMerged : 1,
      }
    })
    const m = geom4(1, g)
    list.push({ id: `${axis}HFMD`, text: 'HF+MD', color: MERGED_COLOR, pos: m.p + m.w / 2, a: aMerged })
    return list
  }
  return { rows: mk('r'), cols: mk('c') }
})

// the outlines die as a merge starts and are back once it has settled —
// on the five-class geometry before, the four-class after
const hardA = computed(() => {
  const m = mergeT.value
  return hardT.value * (m > 0.5 ? smooth(0.85, 1, m) : 1 - smooth(0, 0.15, m))
})
const hardBlocks = computed(() => {
  const g = gMerge.value
  const pad = 3
  const blk = (geom: (i: number, g: number) => { p: number; w: number }, a: number, b: number) => {
    const p0 = geom(a, g)
    const p1 = geom(b, g)
    return { x: p0.p - pad, y: p0.p - pad, w: p1.p + p1.w - p0.p + 2 * pad, h: p1.p + p1.w - p0.p + 2 * pad }
  }
  // four-class: the middle 2×2 — HF+MD against LD (step 5)
  if (mergeT.value > 0.5) return [{ id: 'mid4', ...blk(geom4, 1, 2) }]
  return [{ id: 'hfmd', ...blk(geom5, 1, 2) }, { id: 'mdld', ...blk(geom5, 2, 3) }]
})

const SPLIT_TITLE: Record<Split, string> = { train: 'Training', val: 'Validation', test: 'Test' }
// The epoch the matrices answer to: the matrices only change where the
// log has one (every 10 epochs) or at a best epoch, so this key — not the
// per-frame clock — drives `slots`; while the clock runs, the 150 cells
// re-patch ~3 times a second instead of every frame.
const matEpoch = computed(() => {
  const d = doc.value
  if (!d || pinBest.value) return -1
  const e = Math.max(1, Math.min(EPOCHS, Math.round(epoch.value)))
  if (e === d.runs['5c'].best_epoch || e === d.runs['4c'].best_epoch) return e
  const eps = d.runs['5c'].confusion_by_epoch?.epochs
  if (!eps || !eps.length) return e
  let k = -1
  for (let i = 0; i < eps.length; i++) if (eps[i] <= e) k = i
  return k >= 0 ? eps[k] : 0
})
const slots = computed(() => {
  const d = doc.value
  if (!d) return []
  const r5 = d.runs['5c']
  const r4 = d.runs['4c']
  const e = matEpoch.value
  const g = gMerge.value
  const a5 = 1 - smooth(0, 0.25, mergeT.value)
  const a4 = smooth(0.7, 1, mergeT.value)
  // titles hand over in sequence (old out, then new in) — a crossfade of
  // two different strings in one spot reads as a smudge
  const t5 = 1 - smooth(0.15, 0.45, mergeT.value)
  const t4 = smooth(0.55, 0.85, mergeT.value)
  const hm = humanT.value
  return (['train', 'val', 'test'] as Split[]).map((split, si) => {
    const m5 = matAt(r5, split, e)
    const m4 = matAt(r4, split, e)
    const sub = (r: RunDoc, m: number[][] | null) => {
      const n = r.best[split].n
      if (!m) return `n = ${n} · macro F1 —`
      const f = pinBest.value || Math.round(e) === r.best_epoch ? r.best[split].macro_f1 : macroF1(m)
      return `n = ${n} · macro F1 ${f.toFixed(3)}`
    }
    const layers = [
      { id: 'm5', a: a5 * (si === 0 ? 1 - hm : 1), cells: cellsFor(m5, r5.classes, geom5, g, true, 'true', 'predicted') },
      { id: 'm4', a: a4, cells: cellsFor(m4, r4.classes, geom4, g, false, 'true', 'predicted') },
    ]
    const titles = [
      { id: 'm5', title: SPLIT_TITLE[split], sub: sub(r5, m5), a: t5 * (si === 0 ? 1 - hm : 1) },
      { id: 'm4', title: SPLIT_TITLE[split], sub: sub(r4, m4), a: t4 },
    ]
    const axes = [{ id: 'model', x: 'Predicted', y: 'True', a: si === 0 ? 1 - hm + hm * t4 : 1 }]
    return { x: si * (SLOT_W + SLOT_GAP), layers, titles, axes }
  })
})

// ── playback ──────────────────────────────────────────────────────────
const EPOCHS_PER_S = 30 // 400 epochs ≈ 13 s — a live talk's pace (unchanged)
const ROLLBACK_MS = 1400 // NEXT: 400 → the best epoch
const HOLD_MS = 350 // arriving on a play step: the panels land, then the clock starts
const MERGE_GAP_MS = 400 // the merge has settled before the four-class run plays
let raf: number | null = null
let lastT = 0
// the steps that PLAY on arrival (five-class, four-class); the others rest
// pinned on the best epoch
function isPlayStep(step: number): boolean {
  return step === 0 || step === 3
}
function stopPlay(): void {
  playing.value = false
  if (raf !== null) cancelAnimationFrame(raf)
  raf = null
}
// the arrival sequence's timers (hold → play; merge → gap → rewind → play)
let seqTimer: number | null = null
function cancelSeq(): void {
  if (seqTimer !== null) window.clearTimeout(seqTimer)
  seqTimer = null
}
function after(ms: number, fn: () => void): void {
  cancelSeq()
  seqTimer = window.setTimeout(() => {
    seqTimer = null
    fn()
  }, ms)
}
function cancelEpochTween(): void {
  for (const k of ['epoch', 'reveal']) {
    const t = tweens.get(k)
    if (t != null) {
      cancelAnimationFrame(t)
      tweens.delete(k)
    }
  }
  reveal.value = null
}
function frame(now: number): void {
  // wall-clock epochs; only a real stall (a hidden tab) loses time, not a
  // janky frame — the projector's machine keeps the ≈13 s
  const dt = Math.min(0.25, (now - lastT) / 1000)
  lastT = now
  const e = epoch.value + dt * EPOCHS_PER_S
  if (e >= EPOCHS) {
    epoch.value = EPOCHS
    stopPlay()
    // a play step RESTS at 400 — the roll-back is the NEXT press
    if (isPlayStep(props.step)) return
    // the best steps' own play lands back on the checkpoint the paper reports
    replay.value = false
    tween('epoch', EPOCHS, activeRun.value.best_epoch, ROLLBACK_MS, (v) => { epoch.value = v }, () => { pinBest.value = true })
    return
  }
  epoch.value = e
  raf = requestAnimationFrame(frame)
}
/** Run the clock from where it stands (the auto-play and the play button). */
function startPlay(): void {
  playing.value = true
  lastT = performance.now()
  raf = requestAnimationFrame(frame)
}
/** The beginning of training: epoch 1, curves and matrices following the clock. */
function replayFromStart(): void {
  cancelEpochTween()
  pinBest.value = false
  replay.value = true
  epoch.value = 1
  startPlay()
}
function togglePlay(): void {
  if (playing.value) {
    stopPlay()
    return
  }
  cancelSeq()
  cancelEpochTween()
  pinBest.value = false
  // from rest (or the end), replay training from epoch 1
  if (!replay.value || epoch.value >= EPOCHS) {
    replay.value = true
    epoch.value = 1
  }
  startPlay()
}
function onScrub(ev: Event): void {
  stopPlay()
  cancelSeq()
  cancelEpochTween()
  pinBest.value = false
  epoch.value = parseInt((ev.target as HTMLInputElement).value, 10) || 1
}

// ── steps ─────────────────────────────────────────────────────────────
const MERGE_MS = 2600
function applyStep(step: number, live: boolean, from = -1): void {
  if (!doc.value) return
  stopPlay()
  cancelSeq()
  cancelEpochTween()
  mergeToStart.value = false
  const toHard = step === 2 || step === 5 ? 1 : 0
  const toHuman = 0 // the labelers' matrix is off the training slot
  const toMerge = step >= 3 ? 1 : 0
  const bestTo = doc.value.runs[toMerge ? '4c' : '5c'].best_epoch
  const plays = isPlayStep(step)
  if (!live) {
    tween('hard', hardT.value, toHard, 0, (v) => { hardT.value = v })
    tween('human', humanT.value, toHuman, 0, (v) => { humanT.value = v })
    tween('merge', mergeT.value, toMerge, 0, (v) => { mergeT.value = v })
    if (plays) {
      // a deep link into a play step: the beginning of training, as if
      // arriving — a short hold so the panels land before the clock moves
      replay.value = true
      pinBest.value = false
      epoch.value = 1
      after(HOLD_MS, replayFromStart)
    } else {
      replay.value = false
      pinBest.value = true
      epoch.value = bestTo
    }
    return
  }
  const merging = toMerge !== mergeT.value
  // leaving the hard pairs for the merge: the outlines go first
  tween('hard', hardT.value, toHard, merging ? 350 : 900, (v) => { hardT.value = v })
  if (merging) {
    // the training slot changes hands only while the five-class layer is
    // invisible: after the merge (2 → 3), or before the un-merge (3 → 2)
    if (toMerge) tween('human', humanT.value, humanT.value, 0, () => {})
    else tween('human', humanT.value, toHuman, 0, (v) => { humanT.value = v })
    tween('merge', mergeT.value, toMerge, MERGE_MS, (v) => { mergeT.value = v }, () => {
      if (toMerge) humanT.value = toHuman
    }, (t) => t)
  } else {
    tween('human', humanT.value, toHuman, 700, (v) => { humanT.value = v })
    tween('merge', mergeT.value, toMerge, 0, (v) => { mergeT.value = v })
  }
  if (!plays) {
    // the best steps: the cursor rolls back to the best epoch (the
    // matrices ticking down the log on the way), pins there, TEST appears.
    // From a play step that is the NEXT the director asked for, 1.4 s from
    // wherever the clock is; from a neighbour (2 ↔ 1, 3 → 2) a short move.
    const fromPlay = isPlayStep(from) || replay.value
    replay.value = false
    // through an un-merge (3 → 2) the matrices stay on the best checkpoints
    // — the numbers crossfade, they don't tick — as the merge always did
    pinBest.value = merging
    tween('epoch', epoch.value, bestTo, merging ? MERGE_MS : fromPlay ? ROLLBACK_MS : 700, (v) => { epoch.value = v }, () => { pinBest.value = true })
    return
  }
  if (merging && toMerge) {
    // 2 → 3: the four-class run STARTS AT THE BEGINNING (the director
    // saw the four-class results run all the way to the end and then back
    // to the beginning of the epochs, and asked for them to simply
    // start at the beginning — the merge used to land on the four-class
    // best, 363, and then rewind to 1 with the curves un-drawing). The
    // five-class panel fades out as it stood — matrices on its best
    // checkpoint, curves whole — and halfway through the merge, when
    // neither run's curves nor the five-class matrices are drawn, the
    // clock goes to epoch 1; the four-class panel fades in there, empty,
    // and its run plays once the merge has settled. No sweep, no rewind.
    mergeToStart.value = true
    replay.value = false
    pinBest.value = true
    after(MERGE_MS / 2, () => {
      replay.value = true
      pinBest.value = false
      reveal.value = null
      epoch.value = 1
      after(MERGE_MS / 2 + MERGE_GAP_MS, () => {
        mergeToStart.value = false
        startPlay()
      })
    })
    return
  }
  // BACK onto a play step (1 → 0, 4 → 3): its rest — the end of training,
  // no replay: the cursor moves out to 400 over the full curves, the
  // matrices following the log, the test slot emptying
  replay.value = false
  pinBest.value = false
  tween('epoch', epoch.value, EPOCHS, 700, (v) => { epoch.value = v }, () => { replay.value = true })
}

let mounted = false
watch(() => props.step, (s, from) => applyStep(s, mounted, from))
watch(doc, () => applyStep(props.step, false))

onMounted(async () => {
  try {
    const [a, b] = await loadTrainingData()
    irr.value = (b as IrrFile | null) ?? null
    doc.value = a as TrainingDoc
  } catch (err) {
    console.warn('[training] fetch failed', err)
  }
  mounted = true
})
onBeforeUnmount(() => {
  stopPlay()
  cancelSeq()
  for (const id of tweens.values()) cancelAnimationFrame(id)
  tweens.clear()
})
</script>

<style scoped>
.tr-root {
  position: absolute;
  inset: 0;
  font-family: 'Inter', system-ui, sans-serif;
  color: #f5f0e6;
}
.tr-svg {
  position: absolute;
  left: 2.5vw;
  right: 2.5vw;
  top: 11vh;
  bottom: 10.5vh;
  width: 95vw;
  height: 78.5vh;
}
.tr-panel {
  fill: rgba(10, 9, 8, 0.85);
  stroke: rgba(245, 199, 94, 0.36);
  stroke-width: 1.5;
  vector-effect: non-scaling-stroke;
}
.tr-ptitle {
  font-family: 'EB Garamond', serif;
  font-size: 30px;
  fill: var(--gold-bright);
}
.tr-sub { font-size: 20px; }
.tr-grid line {
  stroke: rgba(245, 240, 230, 0.07);
  stroke-width: 1;
  vector-effect: non-scaling-stroke;
}
.tr-baseline {
  stroke: rgba(245, 240, 230, 0.6);
  stroke-width: 1.6;
  vector-effect: non-scaling-stroke;
}
.tr-tick text {
  font-size: 19px;
  fill: rgba(245, 240, 230, 0.85);
  font-variant-numeric: tabular-nums;
}
.tr-axis {
  font-size: 19px;
  letter-spacing: 0.05em;
  fill: rgba(245, 240, 230, 0.85);
}
.tr-line {
  fill: none;
  stroke-width: 2;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
}
.tr-thick { stroke-width: 3; }
.tr-train { stroke: #f5f0e6; }
.tr-val { stroke: #f4cf6a; }
.tr-dash { stroke-dasharray: 7 5; }
.tr-pc {
  fill: none;
  stroke-width: 1.8;
  stroke-dasharray: 6 4;
  vector-effect: non-scaling-stroke;
  transition: opacity 0.3s;
}
.tr-random {
  stroke: #c9677a;
  stroke-width: 1.8;
  vector-effect: non-scaling-stroke;
}
.tr-random-lbl {
  font-size: 18px;
  fill: #c9677a;
}
.tr-best {
  stroke: rgba(244, 207, 106, 0.85);
  stroke-width: 1.6;
  stroke-dasharray: 2 4;
  vector-effect: non-scaling-stroke;
}
.tr-best-lbl {
  font-size: 18px;
  fill: var(--gold-bright);
  font-variant-numeric: tabular-nums;
}
.tr-cursor {
  stroke: rgba(245, 240, 230, 0.7);
  stroke-width: 1.6;
  vector-effect: non-scaling-stroke;
}
.tr-dot {
  stroke: #0d0c0a;
  stroke-width: 2;
  vector-effect: non-scaling-stroke;
}
.tr-dlabel {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.03em;
}
.tr-mtitle {
  font-family: 'EB Garamond', serif;
  font-size: 30px;
  fill: var(--gold-bright);
}
.tr-msub {
  font-size: 19px;
  fill: rgba(245, 240, 230, 0.88);
  font-variant-numeric: tabular-nums;
}
.tr-head {
  font-size: 19px;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.tr-count {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.tr-pct {
  font-variant-numeric: tabular-nums;
  opacity: 0.92;
}
.tr-diag {
  stroke: rgba(245, 240, 230, 0.5);
  stroke-width: 1.5;
  vector-effect: non-scaling-stroke;
}
.tr-hard-halo {
  fill: none;
  stroke: rgba(0, 0, 0, 0.75);
  stroke-width: 6;
  vector-effect: non-scaling-stroke;
}
.tr-hard-line {
  fill: none;
  stroke: #f5f0e6;
  stroke-width: 3;
  vector-effect: non-scaling-stroke;
  filter: drop-shadow(0 0 6px rgba(245, 240, 230, 0.35));
}

/* ── the epoch clock (the Ch.3 season timebar's house style) ── */
.tr-clock {
  position: absolute;
  left: 50%;
  bottom: 3.2vh;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.55rem 1rem;
  border-radius: 999px;
  background: rgba(8, 7, 6, 0.84);
  border: 1.5px solid rgba(245, 199, 94, 0.36);
  backdrop-filter: blur(8px);
}
.tr-play {
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 50%;
  border: 1.5px solid var(--gold);
  background: rgba(56, 38, 12, 0.5);
  color: var(--gold-bright);
  font-size: 0.8rem;
  cursor: pointer;
}
.tr-scrub-wrap {
  position: relative;
  /* 34vw (was 38vw): leaves the five-class beat's Terminal-Bench door
     (SectionCh3 .ch3-tbsdoor) its corner at 1280–1440 wide */
  width: min(34vw, 520px);
  display: flex;
  align-items: center;
}
.tr-scrub {
  width: 100%;
  height: 16px;
  margin: 0;
  cursor: pointer;
  -webkit-appearance: none;
  appearance: none;
  background: transparent;
}
.tr-scrub::-webkit-slider-runnable-track {
  height: 3px;
  border-radius: 2px;
  background: linear-gradient(to right, var(--gold) var(--fill, 0%), rgba(245, 245, 245, 0.18) var(--fill, 0%));
}
.tr-scrub::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 13px;
  height: 13px;
  margin-top: -5px;
  border-radius: 50%;
  background: #fff8d8;
  border: 1.5px solid var(--gold);
  box-shadow: 0 0 5px rgba(0, 0, 0, 0.6);
}
.tr-scrub::-moz-range-track {
  height: 3px;
  border-radius: 2px;
  background: rgba(245, 245, 245, 0.18);
}
.tr-scrub::-moz-range-progress { height: 3px; border-radius: 2px; background: var(--gold); }
.tr-scrub::-moz-range-thumb {
  width: 13px;
  height: 13px;
  border-radius: 50%;
  background: #fff8d8;
  border: 1.5px solid var(--gold);
}
/* the best-validation epoch, marked on the track */
.tr-best-tick {
  position: absolute;
  top: -3px;
  width: 2px;
  height: 7px;
  margin-left: -1px;
  background: var(--gold-bright);
  pointer-events: none;
  transition: left 0.6s;
}
.tr-epoch {
  min-width: 6.4rem;
  font-variant-numeric: tabular-nums;
  font-size: 1.05rem;
  color: #f5f0e6;
}
</style>
