<template>
  <!-- Chapter 3 · the NETWORK segment.
       Beat 0: the architecture alone, large (EssdNetworkDiagram). Beats
       1…: the diagram docks at the bottom as the road map and the data at
       the lit block fills the stage above it; next steps one block along
       the forward pass (the figure shrinks into the next block and the
       next figure grows out of it, a dot riding the edge), a click on any
       block jumps straight there. The lake picker puts any of the five
       example lakes through; the day scrubber moves every stage through
       the season. Baked by cinematic/scene_ch03/build_network.py → R2
       ch03/network/.

       Two refinements the director asked for: (A) the lit block's shape label is the
       shape of what is on screen (a tensor lights with the block that
       made it), and the channel stages are a textbook stack of sheets
       above their block that fans out into the grid under the pointer;
       (B) the axis is legible — DAY (weights fixed at the best-F1 epoch;
       the per-frame chain sees day t, the recurrent loops fill with days
       1 → t, the verdict reads "if the season ended …") — and a second
       axis, EPOCH (data fixed; every 5-epoch checkpoint + the best,
       build_network_epochs.py → R2 ch03/network_epochs/), toggled by the
       DAY | EPOCH pair beside the scrubber, `?axis=epoch` deep-links it.

       Narrator rule: labels only — block names, tensor shapes, dates,
       class names and values. -->
  <div class="nw" :class="{ 'nw-hero': stage === 0, 'nw-ready': !!index }">
    <!-- ── the stage: two figure slots, double-buffered ── -->
    <div
      class="nw-area"
      :style="{ left: `${area.x}px`, top: `${area.y}px`, width: `${area.w}px`, height: `${area.h}px` }"
    >
      <div
        v-for="(s, i) in slots"
        :key="s.uid"
        class="nw-slot"
        :class="{ 'nw-slot-live': i === active, 'nw-slot-hidden': s.hidden }"
      >
        <EssdNetworkFigure
          v-if="s.stage !== null && NETWORK_STAGES[s.stage] && s.man && index"
          :ref="(el) => setFigRef(i, el)"
          :stage="NETWORK_STAGES[s.stage]"
          :man="s.man"
          :index="index"
          :day="i === active ? day : s.day"
          :pool="s.pool"
          :box-w="area.w"
          :box-h="area.h"
          :frozen="i !== active"
          :axis="axis"
          :ep="i === active ? ep : s.ep"
          :ep-man="s.epMan"
          :ep-index="epIndex"
          :ep-pool="s.epPool"
          :stack-cx="stackCxOf(s.stage)"
          :prefetch="i === active ? prefetchEp : null"
        />
      </div>
    </div>

    <!-- ── the five lakes ── -->
    <div
      v-if="index"
      class="nw-lakes"
      :class="{ 'nw-off': stage === 0 }"
      :style="{ left: `${lakeCol.x}px`, top: `${lakeCol.y}px`, width: `${lakeCol.w}px` }"
    >
      <button
        v-for="l in index.lakes"
        :key="l.id"
        class="nw-lake"
        :class="{ 'nw-lake-on': l.id === lakeId }"
        :style="{ '--c': l.color }"
        :data-lake="l.id"
        @click="setLake(l.id)"
      >
        <img :src="netUrl(l.thumb)" :alt="l.id" />
        <span class="nw-lake-text">
          <span class="nw-lake-code" :class="{ 'nw-lake-code-long': l.true.length > 2 }">{{ classLabel(l.true) }}</span>
          <span class="nw-lake-id">{{ l.id.replace('CW2019_', '') }}</span>
        </span>
      </button>
    </div>

    <!-- ── the block's name, shape, and the day ── -->
    <div
      v-if="man && cur"
      ref="infoEl"
      class="nw-info"
      :class="{ 'nw-off': stage === 0 }"
      :style="{ left: `${infoCol.x}px`, top: `${infoCol.y}px`, width: `${infoCol.w}px` }"
    >
      <!-- one line always: a long title ("ConvLSTM hidden state") used to
           wrap and push the whole column down -->
      <div ref="titleEl" class="nw-title" :style="titleStyle">{{ cur.title }}</div>
      <div class="nw-shape">{{ shapeText }}</div>
      <!-- the axis: a DAY of the season (weights fixed) or an EPOCH of
           training (data fixed) -->
      <template v-if="axis === 'day' || !epOn">
        <div class="nw-date">{{ dayText }}<span class="nw-year">2019</span></div>
        <div class="nw-axis-note">
          <div><span class="nw-k">days</span> 1 → {{ day + 1 }}</div>
          <div><span class="nw-k">weights fixed</span> · epoch {{ index?.model.epoch ?? 189 }}</div>
        </div>
      </template>
      <template v-else>
        <div class="nw-date">
          <span class="nw-epoch-k">epoch</span>{{ epochNow }}
          <span v-if="ep === epIndex!.best_index" class="nw-best-tag">best val F1</span>
        </div>
        <!-- (no "epochs 1 → N" row here, at the director's request —
             the epoch headline above already says it) -->
        <div class="nw-axis-note">
          <div><span class="nw-k">data fixed</span> · {{ epochDataText }}</div>
        </div>
      </template>
      <svg
        v-if="axis === 'day' || !epOn"
        ref="scrubEl"
        class="nw-scrub"
        viewBox="0 0 300 118"
        data-axis="day"
        @pointerdown="onScrubDown"
        @pointermove="onScrubMove"
        @pointerup="onScrubUp"
        @pointercancel="onScrubUp"
      >
        <rect x="0" y="0" width="300" height="118" class="nw-scrub-hit" />
        <rect x="8" y="4" :width="Math.max(0, sx(day) - 8)" height="80" class="nw-scrub-seen" />
        <path :d="scrubArea" class="nw-scrub-area" />
        <path :d="scrubLine" class="nw-scrub-line" />
        <line x1="8" x2="292" y1="84" y2="84" class="nw-scrub-axis" />
        <text v-for="m in scrubMonths" :key="m.label" :x="m.x" y="114" class="nw-scrub-month">{{ m.label }}</text>
        <g
          v-for="p in pips"
          :key="p"
          class="nw-pip"
          :class="{ 'nw-pip-on': p === day }"
          :data-day="p"
          @pointerdown.stop="pickDay(p)"
        >
          <circle :cx="sx(p)" cy="96" r="11" class="nw-pip-hit" />
          <circle :cx="sx(p)" cy="96" r="5" class="nw-pip-dot" />
        </g>
        <line :x1="sx(day)" :x2="sx(day)" y1="4" y2="86" class="nw-scrub-cursor" />
        <circle :cx="sx(day)" :cy="sy(man.p_water_input[day])" r="5" class="nw-scrub-knob" />
      </svg>
      <svg
        v-else
        ref="scrubEl"
        class="nw-scrub"
        viewBox="0 0 300 160"
        data-axis="epoch"
        @pointerdown="onScrubDown"
        @pointermove="onScrubMove"
        @pointerup="onScrubUp"
        @pointercancel="onScrubUp"
      >
        <rect x="0" y="0" width="300" height="160" class="nw-scrub-hit" />
        <!-- legend: the left axis's curve, the right axis's two -->
        <line x1="4" x2="20" y1="9" y2="9" class="nw-scrub-line nw-scrub-line-f1" />
        <text x="25" y="14" class="nw-leg nw-leg-f1">val F1</text>
        <template v-if="hasLoss">
          <line x1="120" x2="136" y1="9" y2="9" class="nw-scrub-loss" />
          <text x="141" y="14" class="nw-leg nw-leg-loss">val</text>
          <line x1="176" x2="192" y1="9" y2="9" class="nw-scrub-loss nw-scrub-loss-train" />
          <text x="197" y="14" class="nw-leg nw-leg-loss">train loss</text>
        </template>
        <!-- the two y-axes -->
        <line :x1="EX0" :x2="EX0" :y1="EY0" :y2="EY1" class="nw-scrub-axis" />
        <text
          v-for="t in f1Ticks"
          :key="`f${t}`"
          :x="EX0 - 5" :y="ey(t) + 5"
          class="nw-scrub-month nw-yt nw-yt-l"
        >{{ t === 0 ? '0' : t.toFixed(1) }}</text>
        <template v-if="hasLoss">
          <line :x1="EX1" :x2="EX1" :y1="EY0" :y2="EY1" class="nw-scrub-axis nw-scrub-axis-loss" />
          <text
            v-for="t in lossTicks"
            :key="`l${t}`"
            :x="EX1 + 5" :y="ly(t) + 5"
            class="nw-scrub-month nw-yt nw-yt-r"
          >{{ t === 0 ? '0' : t.toFixed(1) }}</text>
        </template>
        <path :d="f1Area" class="nw-scrub-area nw-scrub-area-f1" />
        <path v-if="hasLoss" :d="trainLossLine" class="nw-scrub-loss nw-scrub-loss-train" />
        <path v-if="hasLoss" :d="valLossLine" class="nw-scrub-loss" />
        <path :d="f1Line" class="nw-scrub-line nw-scrub-line-f1" />
        <line :x1="EX0" :x2="EX1" :y1="EY1" :y2="EY1" class="nw-scrub-axis" />
        <line
          v-for="e in epIndex!.epochs"
          :key="`t${e}`"
          :x1="ex(e)" :x2="ex(e)" :y1="EY1" :y2="EY1 + 4"
          class="nw-scrub-tick"
        />
        <text
          v-for="e in [0, 100, 200, 300, 400]"
          :key="e"
          :x="ex(e)"
          y="156"
          class="nw-scrub-month nw-scrub-ep"
        >{{ e }}</text>
        <g
          class="nw-pip nw-pip-best"
          :class="{ 'nw-pip-on': ep === epIndex!.best_index }"
          data-epoch="best"
          @pointerdown.stop="pickEp(epIndex!.best_index)"
        >
          <circle :cx="ex(epIndex!.best_epoch)" :cy="EY1 + 15" r="11" class="nw-pip-hit" />
          <circle :cx="ex(epIndex!.best_epoch)" :cy="EY1 + 15" r="5" class="nw-pip-dot" />
        </g>
        <line :x1="ex(epochNow)" :x2="ex(epochNow)" :y1="EY0 - 4" :y2="EY1 + 2" class="nw-scrub-cursor" />
        <circle v-if="hasLoss" :cx="ex(epochNow)" :cy="ly(lossAt(epochNow))" r="4.5" class="nw-scrub-knob-loss" />
        <circle :cx="ex(epochNow)" :cy="ey(f1At(epochNow))" r="5" class="nw-scrub-knob" />
        <!-- the readouts beside the cursor -->
        <text
          :x="ex(epochNow) + (readFlip ? -7 : 7)"
          :y="readY.f1"
          class="nw-scrub-val"
          :style="{ textAnchor: readFlip ? 'end' : 'start' }"
        >F1 {{ f1At(epochNow).toFixed(2) }}</text>
        <text
          v-if="hasLoss"
          :x="ex(epochNow) + (readFlip ? -7 : 7)"
          :y="readY.loss"
          class="nw-scrub-val nw-scrub-val-loss"
          :style="{ textAnchor: readFlip ? 'end' : 'start' }"
        >loss {{ lossAt(epochNow).toFixed(2) }}</text>
      </svg>
      <div class="nw-controls">
        <button class="nw-play" :aria-label="playing ? 'pause' : 'play'" @click="togglePlay">
          <span v-if="playing">❚❚</span><span v-else>▶</span>
        </button>
        <div class="nw-axis-toggle" role="radiogroup">
          <button
            v-for="a in (['day', 'epoch'] as const)"
            :key="a"
            class="nw-axis-stop"
            :class="{ 'nw-axis-on': axis === a }"
            role="radio"
            :aria-checked="axis === a"
            :data-axis-stop="a"
            :disabled="a === 'epoch' && !epAvail"
            :title="a === 'epoch' && !epAvail ? 'epoch checkpoints not baked for this model' : undefined"
            @click="setAxis(a)"
          >{{ a }}</button>
        </div>
      </div>
    </div>

    <!-- ── the TAXONOMY (the director asked for a toggle at the bottom
         right, labelled TAXONOMY, with 4-class and 5-class below it) —
         off the NEXT path: only a click changes it, a reload is 5-class,
         `?taxonomy=4c` deep-links the other ── -->
    <div v-if="index" class="nw-tax" role="radiogroup" aria-label="taxonomy" :style="taxStyle">
      <div class="nw-tax-k">taxonomy</div>
      <div class="nw-tax-row">
      <button
        v-for="t in (['5c', '4c'] as const)"
        :key="t"
        class="nw-tax-stop"
        :class="{ 'nw-tax-on': taxonomy === t }"
        role="radio"
        :aria-checked="taxonomy === t"
        :data-taxonomy="t"
        @click="taxonomy !== t && emit('set-taxonomy', t)"
      >{{ t === '5c' ? '5-class' : '4-class' }}</button>
      </div>
    </div>

    <!-- ── the road map ── -->
    <div
      class="nw-diagram"
      :class="{ 'nw-diagram-snap': snapDiagram, 'nw-diagram-moving': diagMoving }"
      :style="diagramStyle"
    >
      <EssdNetworkDiagram
        v-if="index"
        ref="diagRef"
        :mode="stage === 0 ? 'hero' : 'dock'"
        :current="cur ? cur.id : null"
        :thumb="man ? netUrl(`${man.lake}/thumb.jpg`) : null"
        :pwater="man ? man.p_water_input : null"
        :day="diagDay"
        :v-gap="axVec ? axVec.gap[axT] : null"
        :v-slstm="axVec ? axVec.slstm[axT] : null"
        :v-hidden="axVec ? axVec.hidden[axT] : null"
        :gap-scale="scales.gap"
        :slstm-scale="scales.slstm"
        :hidden-scale="scales.hidden"
        :probs="cur && cur.id === 'out' && axVec ? axVec.probs[axT] : null"
        :classes="index.classes"
        :colors="index.colors"
        :frame-tag="frameTag"
        :loop-frac="loopFrac"
        :loop-text="loopText"
        @select="onSelect"
      />
    </div>

    <!-- the stage videos live here, never shown -->
    <div ref="poolHost" class="nw-pool" aria-hidden="true" />
  </div>
</template>

<script setup lang="ts">
import { computed, markRaw, nextTick, onBeforeUnmount, onMounted, reactive, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter, type LocationQuery } from 'vue-router'
import EssdNetworkDiagram from './EssdNetworkDiagram.vue'
import EssdNetworkFigure from './EssdNetworkFigure.vue'
import {
  EPOCH_INDEX_FILE, NETWORK_STAGES, STAGE_INDEX, classLabel, dayLabel, netEpochUrlOf, netUrlOf, symScale,
  type Axis, type EpochIndex, type EpochManifest, type NetIndex, type NetManifest, type StageId, type Taxonomy,
} from '../config/essdNetwork'
import { VideoPool, warmLake, type FramePool } from '../config/essdNetworkPool'

const props = withDefaults(defineProps<{
  /** 0 = the diagram alone; k ≥ 1 = NETWORK_STAGES[k − 1]; the class head
   *  has two more beats, NETWORK_STAGES.length + 1 and + 2 (same figure). */
  stage: number
  /** Which model (the parent re-mounts this component on a change). */
  taxonomy?: Taxonomy
  /** The lake this mount opens on (a re-mount keeps the one on screen). */
  lake?: string
  /** Mounted by the NEXT into the four-class head beat: play its training
   *  from the first checkpoint (a deep link rests at the end instead). */
  playHead?: boolean
}>(), { taxonomy: '5c', lake: undefined, playHead: false })
const emit = defineEmits<{
  'goto-stage': [value: number]
  'set-taxonomy': [value: Taxonomy]
  lake: [value: string]
}>()
// fixed for this mount (a taxonomy change re-mounts)
const netUrl = netUrlOf(props.taxonomy)
const netEpochUrl = netEpochUrlOf(props.taxonomy)

// ── the beats that drive the EPOCH playback (the director's script) ────
// The model walk defaults to the EPOCH axis and plays the epochs slowly
// enough to follow (about one checkpoint a second at first), looping
// once; the playback starts on the NEXT click that takes the walk from
// the 5 channels into the conv1 block. When a NEXT click finally reaches
// the classification head, the epochs stop wherever they are and go back
// to the beginning, and the next NEXT click shows how the network learns,
// over the epochs, which class it is.
const N_STAGES = NETWORK_STAGES.length
const CHAN_BEAT = STAGE_INDEX.chan + 1
const CONV1_BEAT = STAGE_INDEX.conv1 + 1
const HEAD_BEAT = STAGE_INDEX.out + 1
const HEAD2_BEAT = N_STAGES + 1
// The director's closing beat: once the 5-class walk is through, switch
// to 4-class and show just the classification head's epoch stepping — the
// segment's last beat, the same head in the four-class taxonomy (the
// parent switches the taxonomy; arriving plays training on the head)
const HEAD4C_BEAT = N_STAGES + 2
/** A beat's figure (the class head's two beats share one). */
function figOf(beat: number): number {
  return Math.min(beat, N_STAGES)
}

const DEFAULT_LAKE = 'CW2019_1848' // the moulin example the label demo just labeled

// ── data ─────────────────────────────────────────────────────────────
const index = shallowRef<NetIndex | null>(null)
const mans = new Map<string, Promise<NetManifest | null>>()
const lakeId = ref(props.lake ?? DEFAULT_LAKE)
const man = shallowRef<NetManifest | null>(null)
const pools = new Map<string, VideoPool>()
const poolHost = ref<HTMLElement | null>(null)

function loadManifest(id: string): Promise<NetManifest | null> {
  let p = mans.get(id)
  if (!p) {
    p = fetch(netUrl(`${id}/manifest.json`))
      .then((r) => (r.ok ? (r.json() as Promise<NetManifest>) : null))
      .catch(() => null)
    mans.set(id, p)
  }
  return p
}
function poolFor(m: NetManifest): VideoPool | null {
  if (!poolHost.value) return null
  let p = pools.get(m.lake)
  if (!p) {
    p = markRaw(new VideoPool(m, poolHost.value, netUrl))
    pools.set(m.lake, p)
  }
  return p
}

// ── the axis: DAY (weights fixed, the season walks) | EPOCH (data fixed,
// training walks). `?axis=epoch` deep-links the second. ─────────────────
const route = useRoute()
const router = useRouter()
// EPOCH by default (the director's choice); `?axis=day` deep-links the season.
const axis = ref<Axis>(route.query.axis === 'day' ? 'day' : 'epoch')
/** The EPOCH bake exists for this model (else the pill is disabled). */
const epAvail = ref(true)
const epIndex = shallowRef<EpochIndex | null>(null)
let epIndexP: Promise<EpochIndex | null> | null = null
const epMans = new Map<string, Promise<EpochManifest | null>>()
const epMan = shallowRef<EpochManifest | null>(null)
const epPools = new Map<string, VideoPool>()
/** Frame index into the epochs (epoch 5, 10, …, 189 (best), …, 400). */
const ep = ref(0)
let epSeeded = false
const epOn = computed(() => axis.value === 'epoch' && !!epIndex.value && !!epMan.value)
const epochNow = computed(() => epIndex.value?.epochs[ep.value] ?? 0)

function loadEpIndex(): Promise<EpochIndex | null> {
  if (!epIndexP) {
    epIndexP = fetch(netEpochUrl(EPOCH_INDEX_FILE))
      .then((r) => (r.ok ? (r.json() as Promise<EpochIndex>) : null))
      .catch(() => null)
  }
  return epIndexP
}
function loadEpManifest(id: string): Promise<EpochManifest | null> {
  let p = epMans.get(id)
  if (!p) {
    p = fetch(netEpochUrl(`${id}/manifest.json`))
      .then((r) => (r.ok ? (r.json() as Promise<EpochManifest>) : null))
      .catch(() => null)
    epMans.set(id, p)
  }
  return p
}
function epPoolFor(m: EpochManifest | null): VideoPool | null {
  if (!m || !poolHost.value) return null
  let p = epPools.get(m.lake)
  if (!p) {
    p = markRaw(new VideoPool(m, poolHost.value, netEpochUrl))
    epPools.set(m.lake, p)
  }
  return p
}
/** The epoch data for a lake, loaded (null when it is not baked). */
async function ensureEpoch(lake: string): Promise<EpochManifest | null> {
  const [ix, m] = await Promise.all([loadEpIndex(), loadEpManifest(lake)])
  if (!ix || !m) return null
  epIndex.value = ix
  if (!epSeeded) {
    ep.value = ix.best_index // the DAY axis's own model first
    epSeeded = true
  }
  return m
}
async function setAxis(a: Axis): Promise<void> {
  if (a === axis.value) return
  stopDayAnim()
  if (a === 'epoch') {
    const m = await ensureEpoch(lakeId.value)
    if (!m) {
      epAvail.value = false
      return
    }
    epMan.value = m
    const pool = epPoolFor(m)
    for (const s of slots) {
      if (s.man && s.man.lake === m.lake) {
        s.epMan = m
        s.epPool = pool
      }
    }
  }
  axis.value = a
  const query: LocationQuery = { ...route.query }
  if (a === 'day') query.axis = 'day'
  else delete query.axis
  void router.replace({ query })
}

// the vectors on the current axis
const axVec = computed(() => (epOn.value ? (epMan.value as EpochManifest).vectors : man.value?.vectors ?? null))
const axT = computed(() => (epOn.value ? ep.value : day.value))
const scales = computed(() => {
  const v = axVec.value
  if (!v) return { gap: 1, slstm: 1, hidden: 1 }
  return { gap: symScale(v.gap), slstm: symScale(v.slstm), hidden: symScale(v.hidden) }
})

// ── the day ──────────────────────────────────────────────────────────
const day = ref(0)
const dayText = computed(() => (man.value ? dayLabel(man.value.t0, day.value) : ''))
const playing = ref(false)
let dayRaf: number | null = null
function stopDayAnim(): void {
  if (dayRaf !== null) cancelAnimationFrame(dayRaf)
  dayRaf = null
  playing.value = false
}
/** Ease the day to `to` (a click-triggered move, e.g. into the verdict). */
function animateDay(to: number, ms: number): void {
  stopDayAnim()
  const from = day.value
  const t0 = performance.now()
  const tick = (now: number) => {
    const t = Math.min(1, (now - t0) / ms)
    const e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2
    day.value = Math.round(from + (to - from) * e)
    dayRaf = t < 1 ? requestAnimationFrame(tick) : null
  }
  dayRaf = requestAnimationFrame(tick)
}
const PLAY_DAYS_PER_S = 10
// Two checkpoints a second (the director wanted the epoch stepping twice
// as fast as the original one a second): the run saved every 5 epochs, so 81
// frames ≈ 40 s a pass, and each frame's mp4 seek has half a second (the
// figure pre-seeks the next frame meanwhile).
const PLAY_EPOCH_FRAMES_PER_S = 2
/** Passes still to come after this one (the conv1 start loops once). */
let loopsLeft = 0
function togglePlay(): void {
  if (playing.value) {
    stopDayAnim()
    return
  }
  startPlay(false)
}
/** Play the current axis from where it is (the end restarts it); with
 *  `fromZero` from its first frame. Loops `loopsLeft` more times on the
 *  EPOCH axis, holding the last frame a beat before each restart, and
 *  rests on the last frame. */
function startPlay(fromZero: boolean): void {
  const m = man.value
  if (!m) return
  stopDayAnim()
  const onEpoch = epOn.value
  const n = onEpoch ? (epIndex.value as EpochIndex).epochs.length : m.days
  const at = onEpoch ? ep : day
  const rate = onEpoch ? PLAY_EPOCH_FRAMES_PER_S : PLAY_DAYS_PER_S
  if (fromZero || at.value >= n - 1) at.value = 0
  playing.value = true
  let last = performance.now()
  let acc = at.value
  const tick = (now: number) => {
    acc += ((now - last) / 1000) * rate
    last = now
    if (onEpoch && loopsLeft > 0 && acc >= n) {
      loopsLeft--
      acc -= n
    }
    const d = Math.min(n - 1, Math.floor(acc))
    if (d !== at.value) at.value = d
    if (d >= n - 1 && !(onEpoch && loopsLeft > 0)) {
      dayRaf = null
      playing.value = false
      return
    }
    dayRaf = requestAnimationFrame(tick)
  }
  dayRaf = requestAnimationFrame(tick)
}
/** What a NEXT/BACK does to the EPOCH playback. */
function onPlaybackBeat(from: number, to: number): void {
  if (!epOn.value) return
  if (to < CONV1_BEAT) {
    // back before the learned blocks: nothing to train
    stopDayAnim()
  } else if (from === CHAN_BEAT && to === CONV1_BEAT) {
    // the 5 channels → conv block 1: training starts, epoch 0, loops once
    loopsLeft = 1
    startPlay(true)
  } else if (to === HEAD_BEAT && from !== HEAD_BEAT) {
    // the class head: wherever the epochs are, stop and go back to 0
    stopDayAnim()
    loopsLeft = 0
    ep.value = 0
  } else if (from === HEAD_BEAT && to === HEAD2_BEAT) {
    // … and the next NEXT plays training on the head, once
    loopsLeft = 0
    startPlay(true)
  } else if (from === HEAD2_BEAT && to === HEAD4C_BEAT) {
    // … then the four-class head plays its own (a mount already in the
    // four-class taxonomy; otherwise the re-mount plays it, `playHead`)
    loopsLeft = 0
    startPlay(true)
  }
}
/** The frame the active figure pre-seeks while this one shows. */
const prefetchEp = computed(() => {
  const ix = epIndex.value
  if (!playing.value || !epOn.value || !ix) return null
  const n = ix.epochs.length
  return ep.value + 1 < n ? ep.value + 1 : loopsLeft > 0 ? 0 : null
})
function pickEp(i: number): void {
  stopDayAnim()
  ep.value = i
}
function pickDay(d: number): void {
  stopDayAnim()
  day.value = d
}

// the scrubber (right column): p_water with the six picked days
const scrubEl = ref<SVGSVGElement | null>(null)
function sx(d: number): number {
  const n = man.value?.days ?? 153
  return 8 + (d / Math.max(1, n - 1)) * 284
}
function sy(v: number): number {
  return 80 - Math.max(0, Math.min(1, v)) * 72
}
const scrubLine = computed(() => {
  const p = man.value?.p_water_input
  if (!p) return ''
  return p.map((v, i) => `${i ? 'L' : 'M'}${sx(i).toFixed(1)} ${sy(v).toFixed(1)}`).join(' ')
})
const scrubArea = computed(() => {
  const p = man.value?.p_water_input
  if (!p) return ''
  return `${scrubLine.value} L${sx(p.length - 1)} 84 L${sx(0)} 84 Z`
})
const scrubMonths = computed(() => {
  const m = man.value
  if (!m) return []
  const t0 = new Date(`${m.t0}T00:00:00Z`).getTime()
  const out: { label: string; x: number }[] = []
  for (let k = 0; k < 5; k++) {
    const d = new Date(t0)
    d.setUTCMonth(d.getUTCMonth() + k)
    const di = Math.round((d.getTime() - t0) / 86400e3)
    out.push({ label: d.toLocaleDateString('en-GB', { month: 'short', timeZone: 'UTC' }).toUpperCase(), x: sx(di) })
  }
  return out
})
// The picked days as stops. pick_days pads start / peak / drain / after /
// end with evenly spaced filler days; a filler within 2 days of another
// pick would sit on the same spot (LD 1907: drain 29, filler 30), so it goes.
const pips = computed(() => {
  const m = man.value
  if (!m) return []
  const picks = m.picks
  const fill = new Set([1, 2, 3, 4].map((k) => Math.floor((k * (m.days - 1)) / 5)))
  return picks.filter((p) => !(fill.has(p) && picks.some((q) => q !== p && Math.abs(q - p) <= 2)))
})
// the EPOCH scrubber: x = epoch 0 → 400; validation macro-F1 on the left
// axis and — the director asked for a loss curve on the same plot as
// the F1, on a second y-axis — the losses on the right one
// (validation solid, training dashed, one blue). Its own frame: a legend
// row on top, the two axes' tick labels in the side margins.
const EPOCH_MAX = 400
const EX0 = 34
const EX1 = 264
const EY0 = 26 // plot top
const EY1 = 112 // plot bottom (the epoch axis)
function ex(e: number): number {
  return EX0 + (e / EPOCH_MAX) * (EX1 - EX0)
}
/** F1 axis: 0 → F1_MAX. */
const F1_MAX = 0.8
function ey(v: number): number {
  return EY1 - Math.max(0, Math.min(1, v / F1_MAX)) * (EY1 - EY0)
}
const f1Ticks = [0, 0.4, 0.8]
function curveAt(arr: number[] | undefined, e: number): number {
  const c = epIndex.value?.curves
  if (!c || !arr) return 0
  const k = Math.max(0, Math.min(arr.length - 1, e - c.epoch[0]))
  return arr[k]
}
function f1At(e: number): number {
  return curveAt(epIndex.value?.curves.val_f1, e)
}
function lossAt(e: number): number {
  return curveAt(epIndex.value?.curves.val_loss, e)
}
const hasLoss = computed(() => !!epIndex.value?.curves.val_loss)
/** Loss axis: 0 → the run's largest loss, rounded up to 0.5. */
const lossMax = computed(() => {
  const c = epIndex.value?.curves
  if (!c?.val_loss) return 2
  const m = Math.max(...c.val_loss, ...(c.train_loss ?? []))
  return Math.ceil(m * 2) / 2
})
const lossTicks = computed(() => {
  const out: number[] = []
  for (let v = 0; v <= lossMax.value + 1e-9; v += 0.5) out.push(Math.round(v * 10) / 10)
  return out
})
function ly(v: number): number {
  return EY1 - Math.max(0, Math.min(1, v / lossMax.value)) * (EY1 - EY0)
}
function curvePath(arr: number[] | undefined, y: (v: number) => number): string {
  const c = epIndex.value?.curves
  if (!c || !arr) return ''
  return c.epoch.map((e, i) => `${i ? 'L' : 'M'}${ex(e).toFixed(1)} ${y(arr[i]).toFixed(1)}`).join(' ')
}
const f1Line = computed(() => curvePath(epIndex.value?.curves.val_f1, ey))
const f1Area = computed(() => {
  const c = epIndex.value?.curves
  if (!c) return ''
  return `${f1Line.value} L${ex(c.epoch[c.epoch.length - 1])} ${EY1} L${ex(c.epoch[0])} ${EY1} Z`
})
const valLossLine = computed(() => curvePath(epIndex.value?.curves.val_loss, ly))
const trainLossLine = computed(() => curvePath(epIndex.value?.curves.train_loss, ly))
/** The readouts sit beside the cursor, flipped left past ~60 %. */
const readFlip = computed(() => ex(epochNow.value) > EX0 + 0.6 * (EX1 - EX0))
/** Each readout by its knob: the higher knob's above it, the lower's
 *  below it, so the two never overlap. */
const readY = computed(() => {
  const e = epochNow.value
  const fy = ey(f1At(e))
  const ly0 = ly(lossAt(e))
  // baselines inside the plot (a readout above EY0 + 10 ran into the legend)
  const clamp = (y: number) => Math.max(EY0 + 10, Math.min(EY1 - 4, y))
  if (!hasLoss.value) return { f1: clamp(fy - 8), loss: 0 }
  return fy <= ly0
    ? { f1: clamp(fy - 8), loss: clamp(Math.max(ly0 + 18, fy + 12)) }
    : { f1: clamp(Math.max(fy + 18, ly0 + 12)), loss: clamp(ly0 - 8) }
})
const epochDataText = computed(() => {
  const s = cur.value
  const em = epMan.value
  const m = man.value
  if (!s || !em || !m) return ''
  if (['clstm', 'gap', 'pwater', 'slstm', 'concat', 'fc', 'out'].includes(s.id))
    // no year on the range: it ran off the column at 1440
    return `${dayLabel(m.t0, 0)} → ${dayLabel(m.t0, em.state_day)}`
  return `${dayLabel(m.t0, em.image_day)} 2019`
})

let scrubbing = false
function unitFromEvent(e: PointerEvent): number | null {
  const el = scrubEl.value
  if (!el) return null
  const r = el.getBoundingClientRect()
  return ((e.clientX - r.left) / r.width) * 300
}
function dayFromEvent(e: PointerEvent): number {
  const m = man.value
  const u = unitFromEvent(e)
  if (u === null || !m) return day.value
  return Math.max(0, Math.min(m.days - 1, Math.round(((u - 8) / 284) * (m.days - 1))))
}
function epFromEvent(e: PointerEvent): number {
  const ix = epIndex.value
  const u = unitFromEvent(e)
  if (u === null || !ix) return ep.value
  const want = ((u - EX0) / (EX1 - EX0)) * EPOCH_MAX
  let best = 0
  for (let i = 1; i < ix.epochs.length; i++)
    if (Math.abs(ix.epochs[i] - want) < Math.abs(ix.epochs[best] - want)) best = i
  return best
}
function scrubTo(e: PointerEvent): void {
  if (epOn.value) ep.value = epFromEvent(e)
  else day.value = dayFromEvent(e)
}
function onScrubDown(e: PointerEvent): void {
  e.preventDefault() // a drag must not select the axis labels
  stopDayAnim()
  scrubbing = true
  ;(e.currentTarget as Element).setPointerCapture?.(e.pointerId)
  scrubTo(e)
}
function onScrubMove(e: PointerEvent): void {
  if (scrubbing) scrubTo(e)
}
function onScrubUp(): void {
  scrubbing = false
}

// ── geometry ─────────────────────────────────────────────────────────
const vw = ref(window.innerWidth)
const vh = ref(window.innerHeight)
function onResize(): void {
  vw.value = window.innerWidth
  vh.value = window.innerHeight
}
const ASPECT = 370 / 1600
const hero = computed(() => {
  const w = Math.min(0.94 * vw.value, (0.62 * vh.value) / ASPECT)
  const h = w * ASPECT
  return { x: (vw.value - w) / 2, y: 0.52 * vh.value - h / 2, w, h }
})
const dock = computed(() => {
  // 0.285 → 0.31 of the height (the road map's labels
  // must reach the back row — 1 unit = 0.75 px at 1440 × 900)
  let h = 0.31 * vh.value
  let w = h / ASPECT
  if (w > 0.96 * vw.value) {
    w = 0.96 * vw.value
    h = w * ASPECT
  }
  return { x: (vw.value - w) / 2, y: vh.value - h - 0.02 * vh.value, w, h }
})
const TOP = computed(() => Math.max(0.115 * vh.value, 96))
const lakeCol = computed(() => ({ x: 0.018 * vw.value, y: TOP.value, w: Math.max(118, 0.095 * vw.value) }))
const infoCol = computed(() => {
  const w = Math.max(270, 0.2 * vw.value)
  return { x: vw.value - w - 0.022 * vw.value, y: TOP.value + 0.03 * vh.value, w }
})
// the TAXONOMY toggle: under the info column, right-aligned with it; on
// the architecture beat (no column) in the free bottom-right corner
const infoEl = ref<HTMLElement | null>(null)
const infoBottom = ref(0)
let infoRo: ResizeObserver | null = null
watch(infoEl, (el) => {
  infoRo?.disconnect()
  if (!el) return
  infoRo = new ResizeObserver(() => { infoBottom.value = el.offsetTop + el.offsetHeight; fitTitle() })
  infoRo.observe(el)
})
// The title's fit: 1 = the stylesheet size; below 1 the font is scaled so
// the (nowrap) line ends inside the column. Text width is linear in the
// font size, so one measurement at the current fit gives the natural width.
const titleEl = ref<HTMLElement | null>(null)
const titleFit = ref(1)
const titleStyle = computed(() =>
  titleFit.value < 0.999 ? { fontSize: `calc(clamp(1.7rem, 2.3vw, 2.6rem) * ${titleFit.value.toFixed(3)})` } : undefined,
)
function fitTitle(): void {
  const el = titleEl.value
  if (!el) return
  const w = el.clientWidth
  const natural = el.scrollWidth / titleFit.value
  if (!w || !natural) return
  titleFit.value = natural > w + 0.5 ? Math.max(0.5, w / natural) : 1
}
const taxStyle = computed(() => {
  const right = `${vw.value - infoCol.value.x - infoCol.value.w}px`
  if (props.stage === 0 || !infoBottom.value) return { right, bottom: `${0.025 * vh.value}px` }
  return { right, top: `${infoBottom.value + 0.014 * vh.value}px` }
})
const area = computed(() => {
  const x = lakeCol.value.x + lakeCol.value.w + 0.02 * vw.value
  const x1 = infoCol.value.x - 0.02 * vw.value
  const y = TOP.value
  const y1 = dock.value.y - 0.025 * vh.value
  return { x, y, w: Math.max(200, x1 - x), h: Math.max(160, y1 - y) }
})
// The diagram's LAYOUT box is the hero box; docking is a transform (a
// scale < 1 keeps the text crisp at rest).
const snapDiagram = ref(true)
// composited only while it moves (at rest it repaints crisp at its scale)
const diagMoving = ref(false)
let diagMovingTimer: number | null = null
function markDiagramMoving(): void {
  diagMoving.value = true
  if (diagMovingTimer !== null) clearTimeout(diagMovingTimer)
  diagMovingTimer = window.setTimeout(() => { diagMoving.value = false }, DOCK_MS + 150)
}
function nextFrames(n = 2): Promise<void> {
  return new Promise((res) => {
    const step = (k: number) => requestAnimationFrame(() => (k <= 1 ? res() : step(k - 1)))
    step(n)
  })
}
const diagramStyle = computed(() => {
  const H = hero.value
  const D = dock.value
  const s = D.w / H.w
  const t = props.stage === 0 ? 'none' : `translate(${D.x - H.x}px, ${D.y - H.y}px) scale(${s})`
  return { left: `${H.x}px`, top: `${H.y}px`, width: `${H.w}px`, height: `${H.h}px`, transform: t }
})
/** A block's core box in screen px, in the DOCKED diagram. */
function nodeScreen(id: StageId): { x: number; y: number; w: number; h: number } | null {
  const b = diagRef.value?.coreBox(id)
  if (!b) return null
  const D = dock.value
  const s = D.w / 1600
  return { x: D.x + b.x * s, y: D.y + b.y * s, w: b.w * s, h: b.h * s }
}

/** The lit block's centre in the figure area's px (the stack stands above it). */
function stackCxOf(stage: number | null): number | null {
  const def = stage === null ? null : NETWORK_STAGES[stage]
  if (!def) return null
  const node = nodeScreen(def.id)
  if (!node) return null
  return node.x + node.w / 2 - area.value.x
}
// the diagram's day marks: the per-frame chain sees one day, the
// recurrent loops have seen days 1 → t (DAY axis); on the EPOCH axis the
// chain's day is the fixed one and the loops hold the whole season
const diagDay = computed(() => (epOn.value && man.value ? man.value.days - 1 : day.value))
const frameTag = computed(() => {
  const m = man.value
  if (props.stage === 0 || !m) return null
  if (epOn.value) return dayLabel(m.t0, (epMan.value as EpochManifest).image_day)
  return `day ${day.value + 1}`
})
const loopFrac = computed(() => {
  const m = man.value
  if (props.stage === 0 || !m || epOn.value) return null
  return (day.value + 1) / m.days
})
const loopText = computed(() => (loopFrac.value === null ? '× 153 days' : `days 1 → ${day.value + 1}`))

// ── stages + the figure slots ────────────────────────────────────────
const cur = computed(() => (props.stage >= 1 ? NETWORK_STAGES[figOf(props.stage) - 1] ?? null : null))
// (after `cur`: a watcher's getter runs at once)
watch(() => cur.value?.title, () => { titleFit.value = 1; nextTick(fitTitle) })
watch(titleEl, (el) => { if (el) { titleFit.value = 1; nextTick(fitTitle) } })
if (typeof document !== 'undefined' && document.fonts?.ready) document.fonts.ready.then(() => nextTick(fitTitle))
const shapeText = computed(() => {
  const m = man.value
  const s = cur.value
  if (!m || !s) return ''
  if (s.media) return m.stages[s.media].shape.join(' × ')
  const v = m.vectors
  switch (s.id) {
    case 'gap': return `${v.gap[0].length}`
    case 'pwater': return `${m.days} × 1`
    case 'slstm': return `${v.slstm[0].length}`
    case 'concat': return `${v.gap[0].length} + ${v.slstm[0].length} = ${v.gap[0].length + v.slstm[0].length}`
    case 'fc': return `Linear ${v.gap[0].length + v.slstm[0].length} → ${v.hidden[0].length}`
    case 'out': return `Linear ${v.hidden[0].length} → ${v.probs[0].length}`
  }
  return ''
})

interface Slot {
  uid: number
  stage: number | null
  man: NetManifest | null
  pool: FramePool | null
  day: number
  ep: number
  epMan: EpochManifest | null
  epPool: FramePool | null
  hidden: boolean
}
let uid = 0
const slots = reactive<Slot[]>([
  { uid: uid++, stage: null, man: null, pool: null, day: 0, ep: 0, epMan: null, epPool: null, hidden: false },
  { uid: uid++, stage: null, man: null, pool: null, day: 0, ep: 0, epMan: null, epPool: null, hidden: false },
])
const active = ref(0)
type FigApi = { ready: (ms?: number) => Promise<void>; box: () => DOMRect | null; el: HTMLElement | null }
const figRefs: (FigApi | null)[] = [null, null]
function setFigRef(i: number, el: unknown): void {
  figRefs[i] = (el as FigApi | null) ?? null
}
const diagRef = ref<InstanceType<typeof EssdNetworkDiagram> | null>(null)

function figElOf(i: number): HTMLElement | null {
  const f = figRefs[i]
  const e = f?.el as unknown
  // exposed refs arrive unwrapped
  return (e as HTMLElement | null) ?? null
}
function toNodeTransform(fig: DOMRect, node: { x: number; y: number; w: number; h: number }): string {
  const s = Math.max(0.03, Math.min(node.w / fig.width, node.h / fig.height))
  const dx = node.x + node.w / 2 - (fig.left + fig.width / 2)
  const dy = node.y + node.h / 2 - (fig.top + fig.height / 2)
  return `translate(${dx.toFixed(1)}px, ${dy.toFixed(1)}px) scale(${s.toFixed(4)})`
}
const running: Animation[] = []
function finishAnims(): void {
  for (const a of running.splice(0)) {
    try { a.finish() } catch { /* already gone */ }
  }
}
function fillSlot(i: number, stage: number, m: NetManifest): void {
  // a fresh mount per assignment: a figure never changes stage in place
  slots[i].uid = uid++
  figRefs[i] = null
  slots[i].stage = stage
  slots[i].man = m
  slots[i].pool = poolFor(m)
  slots[i].day = day.value
  slots[i].ep = ep.value
  const em = epMan.value && epMan.value.lake === m.lake ? epMan.value : null
  slots[i].epMan = em
  slots[i].epPool = em ? epPoolFor(em) : null
  // mounted (so it can load + measure) but unseen until its move begins
  slots[i].hidden = true
}
function clearSlot(i: number): void {
  slots[i].stage = null
  slots[i].man = null
  slots[i].pool = null
  slots[i].epMan = null
  slots[i].epPool = null
  figRefs[i] = null
  slots[i].uid = uid++
}

let transTok = 0
const OUT_MS = 430
const IN_MS = 600
const IN_DELAY = 170
const DOCK_MS = 900
const EASE_OUT = 'cubic-bezier(0.55, 0.05, 0.75, 0.3)'
const EASE_IN = 'cubic-bezier(0.18, 0.8, 0.25, 1)'

/** Move to stage index `to` (1-based beat within the segment). */
async function showStage(from: number, to: number, opts: { snap?: boolean } = {}): Promise<void> {
  const tok = ++transTok
  finishAnims()
  const m = man.value
  const out = active.value
  const outEl = slots[out].stage !== null ? figElOf(out) : null

  if (to === 0) {
    // back to the diagram alone: the figure returns into its block
    if (outEl && from >= 1) {
      const node = nodeScreen(NETWORK_STAGES[from - 1].id)
      const box = outEl.getBoundingClientRect()
      if (node && box.width) {
        const a = outEl.animate(
          [{ transform: 'none', opacity: 1 }, { transform: toNodeTransform(box, node), opacity: 0 }],
          { duration: OUT_MS, easing: EASE_OUT, fill: 'forwards' },
        )
        running.push(a)
        await a.finished.catch(() => {})
      }
    }
    if (tok === transTok) clearSlot(out)
    return
  }
  if (!m) return
  const target = NETWORK_STAGES[to - 1]
  const inn = 1 - out
  // leaving the diagram alone: let the dock move start before the figure's
  // mount work lands on the main thread
  if (from === 0 && !opts.snap) {
    await nextFrames(2)
    if (tok !== transTok) return
  }
  fillSlot(inn, to - 1, m)
  await nextTick()
  const fig = figRefs[inn]
  if (!fig) return
  // the diagram docks first when coming from the diagram alone
  const docking = from === 0 && !opts.snap
  await Promise.all([fig.ready(), docking ? wait(DOCK_MS - 120) : Promise.resolve()])
  if (tok !== transTok) return
  const inEl = figElOf(inn)
  const node = nodeScreen(target.id)
  if (opts.snap || !node || !inEl) {
    if (inEl) running.push(inEl.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 320, fill: 'both' }))
    slots[inn].hidden = false
    if (slots[out].stage !== null) clearSlot(out)
    active.value = inn
    return
  }
  if (to === from + 1) diagRef.value?.pulse(target.id, OUT_MS + 120)
  if (outEl) {
    const ob = outEl.getBoundingClientRect()
    running.push(
      outEl.animate(
        [{ transform: 'none', opacity: 1 }, { transform: toNodeTransform(ob, node), opacity: 0 }],
        { duration: OUT_MS, easing: EASE_OUT, fill: 'forwards' },
      ),
    )
  }
  const ib = inEl.getBoundingClientRect()
  const grow = inEl.animate(
    [
      { transform: toNodeTransform(ib, node), opacity: 0.15 },
      { transform: 'none', opacity: 1 },
    ],
    { duration: IN_MS, delay: outEl ? IN_DELAY + 120 : 0, easing: EASE_IN, fill: 'both' },
  )
  running.push(grow)
  slots[inn].hidden = false
  active.value = inn
  // into the verdict by next: the season runs out to its last day
  if (target.id === 'out' && from === to - 1 && !epOn.value) animateDay(m.days - 1, 1500)
  await grow.finished.catch(() => {})
  if (tok !== transTok) return
  if (slots[out].stage !== null) clearSlot(out)
  grow.cancel()
}
function wait(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}

/** Swap the lake under the current stage: decode, then crossfade. */
let lakeSeq = 0
async function setLake(id: string): Promise<void> {
  if (id === lakeId.value && man.value) return
  // a later click wins: a slower load landing after it is dropped
  const seq = ++lakeSeq
  const [m, em] = await Promise.all([
    loadManifest(id),
    axis.value === 'epoch' ? ensureEpoch(id) : Promise.resolve(null),
  ])
  if (!m || seq !== lakeSeq) return
  stopDayAnim()
  lakeId.value = id
  emit('lake', id)
  if (axis.value === 'epoch') epMan.value = em
  else if (epMan.value && epMan.value.lake !== id) epMan.value = null
  // the beat's FIGURE: the class head's later beats share its figure (a
  // raw beat past it indexed no stage → a render error → the whole page
  // went blank)
  const stage = figOf(props.stage)
  const tok = ++transTok
  finishAnims()
  man.value = m
  day.value = cur.value?.id === 'out' ? m.days - 1 : m.default_day
  if (stage === 0) return
  const out = active.value
  const inn = 1 - out
  fillSlot(inn, stage - 1, m)
  await nextTick()
  const fig = figRefs[inn]
  if (!fig) return
  await fig.ready()
  if (tok !== transTok) return
  const outEl = slots[out].stage !== null ? figElOf(out) : null
  const inEl = figElOf(inn)
  if (outEl) running.push(outEl.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 380, fill: 'forwards' }))
  const a = inEl?.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 380, fill: 'both' })
  if (a) running.push(a)
  slots[inn].hidden = false
  active.value = inn
  await a?.finished.catch(() => {})
  if (tok !== transTok) return
  if (slots[out].stage !== null) clearSlot(out)
  // free the videos of lakes no longer on screen
  for (const map of [pools, epPools]) {
    for (const [k, p] of map) {
      if (k !== id) {
        p.destroy()
        map.delete(k)
      }
    }
  }
}

function onSelect(id: StageId): void {
  emit('goto-stage', STAGE_INDEX[id] + 1)
}

let prevStage = -1
watch(
  () => props.stage,
  (to) => {
    const from = prevStage
    prevStage = to
    onPlaybackBeat(from, to)
    // the class head's second beat keeps its figure
    if (figOf(from) === figOf(to)) return
    snapDiagram.value = false
    if ((from === 0) !== (to === 0)) markDiagramMoving()
    void showStage(figOf(from), figOf(to))
  },
)

onMounted(async () => {
  window.addEventListener('resize', onResize)
  try {
    const r = await fetch(netUrl('index.json'))
    if (r.ok) index.value = (await r.json()) as NetIndex
  } catch {
    /* the segment shows nothing without its index */
  }
  const [m, em] = await Promise.all([
    loadManifest(lakeId.value),
    axis.value === 'epoch' ? ensureEpoch(lakeId.value) : Promise.resolve(null),
  ])
  if (!m) return
  man.value = m
  if (axis.value === 'epoch') {
    if (em) epMan.value = em
    else {
      axis.value = 'day' // not baked / not reachable: the DAY axis
      epAvail.value = false
    }
  }
  // a deep link into the class head: its first beat at epoch 0, its
  // second at the end of training (what the play would have reached)
  if (epOn.value && props.stage === HEAD_BEAT) ep.value = 0
  else if (epOn.value && (props.stage === HEAD2_BEAT || props.stage === HEAD4C_BEAT))
    ep.value = props.playHead ? 0 : (epIndex.value as EpochIndex).epochs.length - 1
  // a deep link into the verdict opens on the prediction (the last day)
  day.value = cur.value?.id === 'out' ? m.days - 1 : m.default_day
  await nextTick()
  prevStage = props.stage
  void showStage(0, figOf(props.stage), { snap: true })
  // the NEXT into the four-class head: its training plays from epoch 1
  if (epOn.value && props.playHead && props.stage === HEAD4C_BEAT) {
    loopsLeft = 0
    startPlay(true)
  }
  // let the diagram's first placement land without a transition
  requestAnimationFrame(() => requestAnimationFrame(() => { snapDiagram.value = false }))
  // warm the other lakes' manifests + videos, current lake first
  const pool = poolFor(m)
  pool?.ready().then(async () => {
    // pre-seek every stage to the day, so the first move never waits
    for (const k of Object.keys(m.stages)) await pool.frame(k, day.value)
    for (const l of index.value?.lakes ?? []) {
      const mm = await loadManifest(l.id)
      if (mm) await warmLake(mm, netUrl)
    }
    // then the EPOCH axis for the lake on screen, so the toggle is instant
    const e = await ensureEpoch(lakeId.value)
    epAvail.value = !!e
    if (e) await warmLake(e, netEpochUrl)
  })
})

onBeforeUnmount(() => {
  infoRo?.disconnect()
  window.removeEventListener('resize', onResize)
  stopDayAnim()
  finishAnims()
  transTok++
  for (const p of pools.values()) p.destroy()
  pools.clear()
  for (const p of epPools.values()) p.destroy()
  epPools.clear()
})
</script>

<style scoped>
.nw {
  position: absolute;
  inset: 0;
  pointer-events: auto;
  opacity: 0;
  transition: opacity 420ms ease;
  overflow: hidden;
}
.nw-ready { opacity: 1; }
.nw-off { opacity: 0; pointer-events: none; }
/* the side columns arrive with the docking diagram, not before it */
.nw-lakes:not(.nw-off),
.nw-info:not(.nw-off) { transition-delay: 600ms; }

/* ── the stage ── */
.nw-area { position: absolute; }
.nw-slot { position: absolute; inset: 0; pointer-events: none; }
.nw-slot-hidden { visibility: hidden; }

/* ── the lakes ── */
.nw-lakes {
  position: absolute;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  transition: opacity 400ms ease;
}
.nw-lake {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.3rem;
  border: 2px solid transparent;
  border-radius: 12px;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
  opacity: 0.5;
  filter: saturate(0.5);
  transition: opacity 220ms ease, filter 220ms ease, border-color 220ms ease, background 220ms ease;
}
.nw-lake:hover { opacity: 0.85; filter: none; }
.nw-lake-on {
  opacity: 1;
  filter: none;
  border-color: var(--c);
  background: rgba(20, 18, 14, 0.8);
}
.nw-lake img {
  width: clamp(52px, 4.6vw, 80px);
  height: clamp(52px, 4.6vw, 80px);
  border-radius: 8px;
  object-fit: cover;
  display: block;
  box-shadow: 0 0 0 2px var(--c);
}
.nw-lake-text { display: flex; flex-direction: column; align-items: flex-start; gap: 0.1rem; }
.nw-lake-code {
  font-size: clamp(1rem, 1.25vw, 1.35rem);
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--c);
}
/* HF+MD (the four-class TAXONOMY) must stay inside its card */
.nw-lake-code-long { letter-spacing: 0.01em; white-space: nowrap; }
/* …by letting its card grow past the column (the others keep its width) */
.nw-lakes { align-items: flex-start; }
.nw-lake { min-width: 100%; }
.nw-lake-id {
  font-size: clamp(0.9rem, 1.05vw, 1.1rem);
  color: rgba(245, 240, 230, 0.85);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.04em;
}

/* ── the info column ── */
.nw-info {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  transition: opacity 400ms ease;
}
.nw-title {
  font-family: 'EB Garamond', serif;
  font-size: clamp(1.7rem, 2.3vw, 2.6rem);
  line-height: 1.08;
  color: var(--gold-bright);
  white-space: nowrap;
  align-self: stretch;
}
.nw-shape {
  margin-top: 0.45rem;
  font-size: clamp(1rem, 1.2vw, 1.3rem);
  letter-spacing: 0.06em;
  color: rgba(245, 240, 230, 0.88);
  font-variant-numeric: tabular-nums;
}
.nw-date {
  margin-top: 2.2rem;
  font-family: 'EB Garamond', serif;
  font-size: clamp(1.8rem, 2.4vw, 2.7rem);
  color: #f5f0e6;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em;
}
.nw-year {
  margin-left: 0.5rem;
  font-size: 0.5em;
  color: rgba(245, 240, 230, 0.75);
}
.nw-scrub {
  width: 100%;
  height: auto;
  margin-top: 0.5rem;
  cursor: ew-resize;
  touch-action: none;
  -webkit-user-select: none;
  user-select: none;
}
.nw-scrub-hit { fill: transparent; }
.nw-scrub-area { fill: rgba(127, 208, 255, 0.14); }
.nw-scrub-line { fill: none; stroke: #7fd0ff; stroke-width: 2; stroke-linejoin: round; }
.nw-scrub-axis { stroke: rgba(245, 240, 230, 0.6); stroke-width: 1.6; }
.nw-scrub-month {
  fill: rgba(245, 240, 230, 0.85);
  font-size: 15px;
  letter-spacing: 0.08em;
  font-family: 'Inter', system-ui, sans-serif;
}
.nw-pip { cursor: pointer; }
.nw-pip-hit { fill: transparent; }
.nw-pip-dot { fill: rgba(245, 240, 230, 0.75); transition: fill 150ms; }
.nw-pip:hover .nw-pip-dot { fill: #f5f0e6; }
.nw-pip-on .nw-pip-dot { fill: var(--gold-bright); }
.nw-scrub-cursor { stroke: var(--gold-bright); stroke-width: 2; }
.nw-scrub-knob { fill: var(--gold-bright); }
.nw-axis-note {
  margin-top: 0.15rem;
  /* the projector pass: ~14 → ~16 px at 1440 */
  font-size: clamp(0.95rem, 1.12vw, 1.15rem);
  letter-spacing: 0.06em;
  color: rgba(245, 240, 230, 0.92);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.nw-k { text-transform: uppercase; color: rgba(245, 240, 230, 0.86); margin-right: 0.15rem; }
.nw-sep { margin: 0 0.45rem; color: rgba(245, 240, 230, 0.6); }
.nw-epoch-k {
  margin-right: 0.45rem;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.42em;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(245, 240, 230, 0.85);
  vertical-align: 0.35em;
}
.nw-best-tag {
  margin-left: 0.6rem;
  padding: 0.05rem 0.5rem;
  border-radius: 999px;
  border: 1px solid var(--gold);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.3em;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--gold-bright);
  vertical-align: 0.6em;
}
.nw-scrub-seen { fill: rgba(244, 207, 106, 0.08); }
.nw-scrub-area-f1 { fill: rgba(245, 240, 230, 0.08); }
.nw-scrub-line-f1 { stroke: rgba(245, 240, 230, 0.9); stroke-width: 2; }
.nw-scrub-tick { stroke: rgba(245, 240, 230, 0.6); stroke-width: 1.2; }
.nw-scrub-ep { text-anchor: middle; }
.nw-pip-best .nw-pip-dot { fill: var(--gold-bright); }
.nw-scrub-val {
  fill: var(--gold-bright);
  font-size: 15px;
  font-weight: 600;
  text-anchor: middle;
  font-family: 'Inter', system-ui, sans-serif;
  font-variant-numeric: tabular-nums;
}
.nw-controls {
  margin-top: 0.7rem;
  display: flex;
  align-items: center;
  gap: 0.9rem;
}
.nw-axis-toggle {
  display: inline-flex;
  padding: 3px;
  border-radius: 999px;
  border: 1.5px solid rgba(245, 240, 230, 0.45);
  background: rgba(20, 18, 14, 0.7);
}
.nw-axis-stop {
  padding: 0.38rem 0.95rem;
  border: none;
  border-radius: 999px;
  background: transparent;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: clamp(0.85rem, 0.95vw, 1rem);
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(245, 240, 230, 0.8);
  cursor: pointer;
  transition: background 200ms ease, color 200ms ease;
}
.nw-axis-stop:hover { color: #f5f0e6; }
.nw-axis-on { background: var(--gold-bright); color: #14110b; }
.nw-axis-on:hover { color: #14110b; }
.nw-axis-stop:disabled { opacity: 0.4; cursor: not-allowed; }
.nw-axis-stop:disabled:hover { color: rgba(245, 240, 230, 0.8); }
/* the EPOCH scrubber's two axes */
.nw-scrub-loss { fill: none; stroke: #7fd0ff; stroke-width: 2; stroke-linejoin: round; }
.nw-scrub-loss-train { stroke-width: 1.6; stroke-dasharray: 4 3; }
.nw-scrub-axis-loss { stroke: rgba(127, 208, 255, 0.75); }
.nw-scrub-knob-loss { fill: #7fd0ff; stroke: #14110b; stroke-width: 1.2; }
.nw-yt { font-size: 15px; letter-spacing: 0.02em; font-variant-numeric: tabular-nums; }
.nw-yt-l { text-anchor: end; }
.nw-yt-r { text-anchor: start; fill: #9fdcff; }
.nw-leg {
  font-size: 15px;
  font-family: 'Inter', system-ui, sans-serif;
  letter-spacing: 0.04em;
}
.nw-leg-f1 { fill: rgba(245, 240, 230, 0.92); }
.nw-leg-loss { fill: #9fdcff; }
.nw-scrub-val { paint-order: stroke; stroke: rgba(14, 12, 9, 0.9); stroke-width: 4px; stroke-linejoin: round; }
.nw-scrub-val-loss { fill: #9fdcff; }
/* the TAXONOMY toggle, bottom-right */
.nw-tax {
  position: absolute;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 0.6rem;
  padding: 0.3rem 0.35rem 0.3rem 0.8rem;
  border-radius: 14px;
  border: 1.5px solid rgba(245, 240, 230, 0.4);
  background: rgba(20, 18, 14, 0.78);
}
.nw-tax-k {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(245, 240, 230, 0.9);
  text-align: center;
}
.nw-tax-row { display: flex; gap: 0.4rem; }
.nw-tax-stop {
  padding: 0.32rem 0.8rem;
  border: 1.5px solid rgba(245, 240, 230, 0.35);
  border-radius: 999px;
  background: transparent;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: rgba(245, 240, 230, 0.85);
  cursor: pointer;
  transition: background 200ms ease, color 200ms ease;
}
.nw-tax-stop:hover { color: #f5f0e6; }
.nw-tax-on { background: var(--gold-bright); border-color: var(--gold-bright); color: #14110b; }
.nw-tax-on:hover { color: #14110b; }
.nw-play {
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 50%;
  border: 1.5px solid var(--gold);
  background: rgba(56, 38, 12, 0.5);
  color: var(--gold-bright);
  font-size: 0.9rem;
  cursor: pointer;
}

/* ── the diagram ── */
.nw-diagram {
  position: absolute;
  transform-origin: 0 0;
  transition: transform 900ms cubic-bezier(0.45, 0, 0.2, 1);
}
.nw-diagram-snap { transition: none; }
.nw-diagram-moving { will-change: transform; }

.nw-pool {
  position: absolute;
  left: 0;
  top: 0;
  width: 1px;
  height: 1px;
  overflow: hidden;
  opacity: 0;
  pointer-events: none;
}
</style>
