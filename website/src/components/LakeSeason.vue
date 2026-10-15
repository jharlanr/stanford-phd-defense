<template>
  <!-- One lake's melt season as the labelers saw it (ESSD Fig. 5, lakelabel):
       the Sentinel-2 movie to scrub (play, the scrub bar, or the wheel over
       the image), its date, and the daily water fraction under it. Shared by
       Chapter 3's "a label made live" (EssdLabelDemo) and the "Label lakes
       yourself" door (SectionLabelLakes). Three root nodes on purpose: they
       sit straight in the parent's column, so its gap spaces them.
       The movie is the VALID-frame bake (build_callout_movies.py /
       build_irr_movies.py): days with no Sentinel-2 acquisition are simply
       not frames, while the p_water curve stays on the full daily axis. -->
  <div class="ld-frame" @wheel="onWheel">
    <video
      ref="videoEl"
      class="ld-video"
      :src="src ?? undefined"
      muted playsinline preload="auto"
      @loadedmetadata="onLoaded"
    />
    <div class="ld-date">
      <span class="ld-date-day">{{ dateLabel }}</span>
      <span class="ld-date-year">{{ yearLabel }}</span>
    </div>
  </div>
  <!-- the season: scrub, or let it step -->
  <div class="ld-scrub">
    <button class="ld-play" :aria-label="playing ? 'pause' : 'play'" @click="playing = !playing">
      <PlayPauseGlyph :playing="playing" :size="12" />
    </button>
    <input
      type="range" min="0" :max="Math.max(1, frames.length - 1)" step="1"
      :style="{ '--fill': (100 * frame / Math.max(1, frames.length - 1)) + '%' }"
      :value="frame"
      @input="onScrub"
    />
  </div>
  <svg class="ld-curve" :viewBox="`0 0 ${CW} ${CH}`" preserveAspectRatio="none">
    <path :d="areaPath" class="ld-area" />
    <path :d="linePath" class="ld-line" />
    <line :x1="markerX" :y1="4" :x2="markerX" :y2="CH - 14" class="ld-marker" />
    <text :x="4" :y="12" class="ld-lbl">p_water</text>
    <text :x="4" :y="CH - 3" class="ld-tick">{{ tick(0) }}</text>
    <text :x="CW - 4" :y="CH - 3" text-anchor="end" class="ld-tick">{{ tick(1) }}</text>
  </svg>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import PlayPauseGlyph from './PlayPauseGlyph.vue'

export interface SeasonFrame { date_iso: string; p_water: number | null; day?: number }
export interface SeasonSidecar {
  fps: number
  frame_count: number
  date_range?: [string, string]
  /** the valid-frame bake: season start, season length, daily p_water */
  t0?: string
  days?: number
  p_water_daily?: Array<number | null>
  frames: SeasonFrame[]
}

// Every season opens on its FIRST kept frame — the first day of the stack
// (the director asked for this on the label door; Ch.3's demo always did).
const props = defineProps<{
  src: string | null
  sidecar: SeasonSidecar | null
  /** The date chip's year; defaults to the sidecar's season start. */
  year?: string | number
}>()

const videoEl = ref<HTMLVideoElement | null>(null)
const frames = computed(() => props.sidecar?.frames ?? [])
const frame = ref(0)
const playing = ref(false)
let playTimer: number | null = null
let loadedMeta = false

function onLoaded(): void {
  loadedMeta = true
  seek(true)
}
function seek(force = false): void {
  const v = videoEl.value
  const sc = props.sidecar
  if (!v || !sc || !loadedMeta) return
  const t = frame.value / sc.fps + 0.001
  // The first seek is forced: a video at currentTime 0 that has never
  // been seeked may sit unpainted (black) until it is.
  if (force || Math.abs(v.currentTime - t) > 0.01) v.currentTime = t
}
function onScrub(e: Event): void {
  frame.value = parseInt((e.target as HTMLInputElement).value, 10) || 0
  playing.value = false
}
// Scroll wheel over the image scrubs frames, as in lakelabel.
function onWheel(e: WheelEvent): void {
  e.preventDefault()
  const n = frames.value.length
  if (!n) return
  playing.value = false
  frame.value = Math.max(0, Math.min(n - 1, frame.value + (e.deltaY > 0 ? 1 : -1)))
}
watch(frame, () => seek())
watch(() => props.sidecar, () => seek(), { immediate: true })
// A new movie in the same element starts over, on its first frame.
watch(
  () => props.src,
  () => {
    loadedMeta = false
    playing.value = false
    frame.value = 0
  },
)
watch(playing, (pl) => {
  if (playTimer !== null) {
    window.clearInterval(playTimer)
    playTimer = null
  }
  if (pl) {
    playTimer = window.setInterval(() => {
      frame.value = (frame.value + 1) % Math.max(1, frames.value.length)
    }, 1000)
  }
})

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
function fmt(iso: string | undefined): string {
  if (!iso) return '—'
  const [, m, d] = iso.split('-')
  return `${parseInt(d, 10)} ${MONTHS[parseInt(m, 10) - 1]}`
}
const dateLabel = computed(() => fmt(frames.value[frame.value]?.date_iso))
const yearLabel = computed(() => {
  if (props.year !== undefined) return String(props.year)
  const sc = props.sidecar
  return (sc?.t0 ?? sc?.frames[0]?.date_iso ?? '').slice(0, 4)
})
function tick(end: 0 | 1): string {
  const sc = props.sidecar
  if (!sc) return ''
  if (sc.date_range) return fmt(sc.date_range[end])
  if (!sc.t0) return ''
  const d = new Date(`${sc.t0}T00:00:00Z`)
  if (end) d.setUTCDate(d.getUTCDate() + (sc.days ?? 153) - 1)
  return fmt(d.toISOString().slice(0, 10))
}

const CW = 400
const CH = 70
// The curve is on the DAILY axis: the valid-frame sidecar carries
// p_water_daily; the older full-season sidecar has one frame per day.
const series = computed(() => {
  const daily = props.sidecar?.p_water_daily
  const f: Array<number | null> = daily ?? frames.value.map((x) => x.p_water)
  const out: number[] = new Array(f.length).fill(0)
  let next = 0
  for (let i = f.length - 1; i >= 0; i--) {
    const p = f[i]
    if (p !== null && Number.isFinite(p)) next = p
    out[i] = next
  }
  return out
})
function xAt(i: number): number {
  const n = series.value.length
  return n <= 1 ? CW / 2 : (i / (n - 1)) * (CW - 8) + 4
}
function yAt(p: number): number {
  return CH - 14 - Math.max(0, Math.min(1, p)) * (CH - 22)
}
const linePath = computed(() =>
  series.value.map((p, i) => `${i ? 'L' : 'M'}${xAt(i).toFixed(1)},${yAt(p).toFixed(1)}`).join(' '),
)
const areaPath = computed(() => {
  const s = series.value
  if (!s.length) return ''
  return `${linePath.value} L${xAt(s.length - 1).toFixed(1)},${CH - 14} L${xAt(0).toFixed(1)},${CH - 14} Z`
})
const markerX = computed(() => xAt(frames.value[frame.value]?.day ?? frame.value))

onBeforeUnmount(() => {
  if (playTimer !== null) window.clearInterval(playTimer)
})
</script>

<style scoped>
.ld-frame {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  border-radius: 10px;
  overflow: hidden;
  background: #000;
  border: 1px solid rgba(245, 199, 94, 0.25);
}
.ld-video {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.ld-date {
  position: absolute;
  left: 10px;
  top: 10px;
  display: flex;
  align-items: baseline;
  gap: 0.4em;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(8, 7, 6, 0.78);
  font-size: 0.95rem;
  font-variant-numeric: tabular-nums;
}
.ld-date-year { font-size: 0.72rem; color: rgba(245, 240, 230, 0.6); }
.ld-scrub {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}
.ld-play {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 50%;
  border: 1px solid var(--gold);
  background: rgba(56, 38, 12, 0.5);
  color: var(--gold-bright);
  cursor: pointer;
}
/* drawn by hand too — WebKit ignores accent-color here (white thumb on a
   black track) */
.ld-scrub input[type='range'] {
  flex: 1 1 auto;
  -webkit-appearance: none;
  appearance: none;
  height: 20px;
  margin: 0;
  background: transparent;
  cursor: pointer;
}
.ld-scrub input[type='range']:focus { outline: none; }
.ld-scrub input[type='range']::-webkit-slider-runnable-track {
  height: 5px;
  border-radius: 3px;
  background: linear-gradient(to right,
    var(--gold) 0, var(--gold) var(--fill),
    rgba(245, 240, 230, 0.16) var(--fill), rgba(245, 240, 230, 0.16) 100%);
}
.ld-scrub input[type='range']::-moz-range-track { height: 5px; border-radius: 3px; background: rgba(245, 240, 230, 0.16); }
.ld-scrub input[type='range']::-moz-range-progress { height: 5px; border-radius: 3px; background: var(--gold); }
.ld-scrub input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  margin-top: -5.5px;
  border-radius: 50%;
  background: var(--gold-bright);
  border: 2px solid #0d0b09;
}
.ld-scrub input[type='range']::-moz-range-thumb {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--gold-bright);
  border: 2px solid #0d0b09;
}
.ld-curve {
  width: 100%;
  height: auto;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
}
/* Water blue (the director wanted the area curve blue, not yellow) — a
   lighter, cyan-leaning blue so it never reads as the MD class's azure
   #42a5f5 (the Ch.3 demo lake IS the MD example, outlined in it). */
.ld-area { fill: #74d4ff; opacity: 0.2; }
.ld-line { fill: none; stroke: #74d4ff; stroke-width: 1.6; vector-effect: non-scaling-stroke; }
.ld-marker { stroke: #f5f0e6; stroke-width: 1; vector-effect: non-scaling-stroke; }
.ld-lbl { fill: rgba(245, 240, 230, 0.55); font-size: 10px; letter-spacing: 0.06em; }
.ld-tick { fill: rgba(245, 240, 230, 0.5); font-size: 9px; }
</style>
