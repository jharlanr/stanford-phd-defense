<template>
  <!-- One lake of the "Revisiting lake drainage papers" page: its
       season as a movie — every day a frame, days with no
       image BLACK on purpose (the director wanted blank days shown as
       black tiles) — in the year and the sensor the two toggles pick, or both of a
       year's sensors side by side on ONE clock. The movies are frame stores
       (2 fps, frame i = day i): the clock here steps the day and every
       video on screen seeks to it, so two tracks can never drift.

       Under the movie(s): the date and each frame's instrument; a scrubber
       over the season's 153 days with a tick on every day that HAS an image
       (one row per track shown), the paper's drainage days for this lake in
       gold and its two cloud days hatched (2010 only — they are June 2010's),
       and the water area the bake measured within 1.25 km of the centre.
       Previous / next IMAGE jump between the days the high-resolution track
       has a picture (most of its days are black).

       A track the bake has not produced yet (most of 2019's Sentinel-2,
       today) is a plain NOT YET PROCESSED plate — never a broken video.
       Figure labels only. The arrow keys stay the site's BACK / NEXT: no
       key is bound here, and every button gives the focus back. -->
  <div class="rvp" :style="{ '--n': panels.length }">
    <header class="rvp-head">
      <h3 class="rvp-id">{{ lake.id }}</h3>
      <div class="rvp-claims">
        <span v-for="c in claims" :key="c.iso" class="rvp-chip">{{ c.label }}</span>
        <span v-if="claims.length" class="rvp-claims-year">{{ CLAIM_YEAR }}</span>
        <span v-else class="rvp-chip rvp-chip-none">not drained</span>
      </div>
      <button class="rvp-close" @click="close($event)">← All lakes</button>
    </header>

    <div class="rvp-toggles">
      <div class="rvp-seg" role="tablist" aria-label="Year">
        <button
          v-for="y in REVISIT_YEARS"
          :key="y"
          class="rvp-seg-btn"
          :class="{ 'rvp-seg-btn--on': year === y }"
          role="tab"
          :aria-selected="year === y"
          :data-year="y"
          @click="pick($event, () => emit('update:year', y))"
        >{{ y }}</button>
      </div>
      <div class="rvp-seg" role="tablist" aria-label="Sensor">
        <button
          v-for="o in modeOpts"
          :key="o.value"
          class="rvp-seg-btn"
          :class="{ 'rvp-seg-btn--on': mode === o.value }"
          role="tab"
          :aria-selected="mode === o.value"
          :data-mode="o.value"
          @click="pick($event, () => emit('update:mode', o.value))"
        >{{ o.label }}</button>
      </div>
    </div>

    <div class="rvp-stage">
      <figure v-for="p in panels" :key="p.key" class="rvp-panel">
        <div class="rvp-frame" :data-sensor="p.sensor">
          <template v-if="p.track">
            <video
              :ref="(el) => setVideo(p.key, el)"
              class="rvp-video"
              :class="{ ready: ready[p.key] }"
              :src="revisitUrl(p.track.src)"
              muted
              playsinline
              preload="auto"
              disablepictureinpicture
              @loadedmetadata="onMeta(p.key)"
              @seeked="ready[p.key] = true"
            />
            <!-- 1 km on the tile (tile_km across) -->
            <span class="rvp-scale" :style="{ width: `${100 / tileKm}%` }"><i>1 km</i></span>
          </template>
          <div v-else class="rvp-plate">
            <span>Not yet processed</span>
          </div>
          <span class="rvp-tag">{{ p.label }}</span>
        </div>
        <figcaption class="rvp-cap" :class="{ 'rvp-cap-none': p.track && !p.sensorName }">
          {{ p.track ? (p.sensorName ?? 'No image') : '' }}
        </figcaption>
      </figure>
    </div>

    <div class="rvp-bar">
      <div class="rvp-btns">
        <button class="rvp-btn" aria-label="Previous image" :disabled="prevImage === null" @click="pick($event, () => jump(prevImage))">
          <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><rect x="2" y="2.5" width="2.4" height="11" /><path d="M14 2.5 L6 8 L14 13.5 Z" /></svg>
        </button>
        <button class="rvp-btn rvp-btn-play" :aria-label="playing ? 'Pause' : 'Play'" @click="pick($event, togglePlay)">
          <PlayPauseGlyph :playing="playing" :size="16" />
        </button>
        <button class="rvp-btn" aria-label="Next image" :disabled="nextImage === null" @click="pick($event, () => jump(nextImage))">
          <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M2 2.5 L10 8 L2 13.5 Z" /><rect x="11.6" y="2.5" width="2.4" height="11" /></svg>
        </button>
      </div>
      <div class="rvp-clock">
        <span class="rvp-date">{{ dateText }}</span>
        <span class="rvp-date-year">{{ year }}</span>
      </div>
      <div class="rvp-key">
        <span v-if="claimDays.length" class="rvp-key-item"><i class="rvp-key-claim" />drained in the paper</span>
        <span v-if="cloudBand" class="rvp-key-item"><i class="rvp-key-cloud" />cloud {{ cloudLabel }}</span>
        <span class="rvp-key-item"><i class="rvp-key-tick" />image</span>
      </div>
    </div>

    <div class="rvp-scrub" :class="{ 'rvp-scrub-rows': panels.length > 1 }">
      <!-- one unit of x = one day; the svg spans the thumb's travel -->
      <svg class="rvp-axis" :viewBox="`0 0 ${last} ${AXIS_H}`" preserveAspectRatio="none" aria-hidden="true">
        <!-- water within 1.25 km of the centre -->
        <path v-for="w in waterCurves" :key="w.key" :d="w.line" class="rvp-water" :class="{ 'rvp-water-coarse': w.coarse }" />
        <!-- the paper's cloud days: no observation -->
        <rect
          v-if="cloudBand"
          class="rvp-cloud"
          :x="cloudBand.x0"
          :y="ROW0 - 4"
          :width="cloudBand.x1 - cloudBand.x0"
          :height="TRACK_Y - ROW0 + 4"
        />
        <!-- a tick on every day with an image, one row per track -->
        <path v-for="r in tickRows" :key="r.key" :d="r.d" class="rvp-tick" />
        <!-- the paper's drainage days for this lake -->
        <path v-if="claimPath" :d="claimPath" class="rvp-claim" />
        <path :d="monthPath" class="rvp-month-tick" />
      </svg>
      <!-- the curve's points (the images), round whatever the stretch -->
      <i
        v-for="d in waterDots"
        :key="d.key"
        class="rvp-water-dot"
        :style="{ left: pct(d.day), top: `${d.y}px` }"
      />
      <i v-for="day in claimDays" :key="day" class="rvp-claim-cap" :style="{ left: pct(day) }" />
      <span v-for="m in months" :key="m.day" class="rvp-month" :style="{ left: pct(m.day) }">{{ m.label }}</span>
      <template v-if="panels.length > 1">
        <span v-for="r in rowLabels" :key="r.key" class="rvp-row-label" :style="{ top: `${r.y}px` }">{{ r.label }}</span>
      </template>
      <span v-if="waterMax > 0" class="rvp-water-label">water · max {{ waterMax.toFixed(2) }} km²</span>
      <input
        class="rvp-range"
        type="range"
        min="0"
        :max="last"
        step="1"
        :value="frame"
        :style="{ '--fill': `${(100 * frame) / last}%` }"
        aria-label="Day of the season"
        @input="onScrub"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import type { ComponentPublicInstance } from 'vue'
import PlayPauseGlyph from './PlayPauseGlyph.vue'
import {
  REVISIT_YEARS,
  SENSOR_NAME,
  claimLabel,
  dayLabel,
  dayOfIso,
  isoOfDay,
  monthTicks,
  revisitUrl,
  sensorWord,
  type C18Lake,
  type C18Manifest,
  type RevisitMode,
  type RevisitSensor,
  type RevisitSidecar,
  type RevisitTrack,
  type RevisitYear,
} from '../config/revisit'

const props = defineProps<{
  lake: C18Lake
  manifest: C18Manifest
  year: RevisitYear
  mode: RevisitMode
}>()
const emit = defineEmits<{
  'update:year': [RevisitYear]
  'update:mode': [RevisitMode]
  close: []
}>()

/** The paper's days are June 2010's: marked on that year's scrubber only. */
const CLAIM_YEAR: RevisitYear = '2010'

// ── the sidecar ───────────────────────────────────────────────────────
const sidecar = ref<RevisitSidecar | null>(null)
let alive = true
async function loadSidecar(id: string): Promise<void> {
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const r = await fetch(revisitUrl(`lakes/${id}.json`))
      if (r.ok) {
        const j = (await r.json()) as RevisitSidecar
        if (alive && props.lake.id === id) {
          sidecar.value = j
          settleOpening()
        }
        return
      }
    } catch {
      // once more
    }
  }
  console.warn('[revisit] sidecar failed to load:', id)
}

const season = computed(() => props.manifest.seasons[props.year])
const frames = computed(() => sidecar.value?.frame_count ?? props.manifest.frame_count)
const last = computed(() => Math.max(1, frames.value - 1))
const fps = computed(() => sidecar.value?.fps ?? props.manifest.fps)
const tileKm = computed(() => sidecar.value?.tile_km ?? props.manifest.tile_km)

function trackOf(sensor: RevisitSensor): RevisitTrack | null {
  // The manifest says which tracks were built; the sidecar carries them.
  if (props.lake.tracks[props.year]?.[sensor] == null) return null
  return sidecar.value?.tracks[props.year]?.[sensor] ?? null
}

// ── the toggles ───────────────────────────────────────────────────────
const hiresWord = computed(() => sensorWord(season.value?.hires ?? 'High resolution'))
const modeOpts = computed<{ value: RevisitMode; label: string }[]>(() => [
  { value: 'modis', label: sensorWord(season.value?.modis ?? 'MODIS') },
  { value: 'hires', label: hiresWord.value },
  { value: 'side', label: 'Side by side' },
])

// ── the clock: one day index for everything on screen ─────────────────
/** The paper's first map (5 June) — the day before its cascade. */
function firstMapFrame(): number {
  const s = props.manifest.seasons[CLAIM_YEAR]
  const first = props.manifest.obs_days[0]?.date
  const i = s && first ? dayOfIso(s.start, first) : 0
  return Math.max(0, Math.min(props.manifest.frame_count - 1, i))
}
const frame = ref(firstMapFrame())
const playing = ref(false)
let playTimer: number | null = null
/** Nothing has moved the clock yet (the opening frame may still settle). */
let untouched = true
/** The opening frame: the last high-resolution image on or before the
 *  paper's first map — the sharp look at the lake before the cascade
 *  (5 June itself is rarely a Landsat day). The sidecar brings the days. */
function settleOpening(): void {
  if (!untouched) return
  const has = sidecar.value?.tracks[props.year]?.hires?.has
  if (!has || props.lake.tracks[props.year]?.hires == null) return
  for (let i = firstMapFrame(); i >= 0; i--) {
    if (has[i] === '1') {
      frame.value = i
      return
    }
  }
}

const iso = computed(() => (season.value ? isoOfDay(season.value.start, frame.value) : ''))
const dateText = computed(() => (iso.value ? dayLabel(iso.value) : ''))

interface Panel {
  key: string
  sensor: RevisitSensor
  label: string
  track: RevisitTrack | null
  /** the frame's instrument, null on a day with no image */
  sensorName: string | null
}
const panels = computed<Panel[]>(() => {
  const sensors: RevisitSensor[] = props.mode === 'side' ? ['modis', 'hires'] : [props.mode]
  return sensors.map((sensor) => {
    const track = trackOf(sensor)
    const code = track?.sensor[frame.value] ?? '.'
    return {
      key: `${props.year}:${sensor}`,
      sensor,
      label: track?.label ?? season.value?.[sensor] ?? sensor,
      track,
      sensorName: track && track.has[frame.value] === '1' ? (SENSOR_NAME[code] ?? null) : null,
    }
  })
})

// ── the videos: frame stores, seeked to the clock ─────────────────────
const videos = new Map<string, HTMLVideoElement>()
const metaReady = new Set<string>()
const ready = reactive<Record<string, boolean>>({})
function setVideo(key: string, el: Element | ComponentPublicInstance | null): void {
  if (el instanceof HTMLVideoElement) videos.set(key, el)
  else {
    videos.delete(key)
    metaReady.delete(key)
    delete ready[key]
  }
}
function seekOne(key: string, force = false): void {
  const v = videos.get(key)
  if (!v || !metaReady.has(key)) return
  // the middle of the day's frame
  const t = (frame.value + 0.5) / fps.value
  if (force || Math.abs(v.currentTime - t) > 0.01) v.currentTime = t
}
function onMeta(key: string): void {
  metaReady.add(key)
  // The first seek is forced: an unseeked video may sit unpainted.
  seekOne(key, true)
}
watch(frame, () => {
  for (const k of videos.keys()) seekOne(k)
})

function stop(): void {
  playing.value = false
}
function togglePlay(): void {
  untouched = false
  if (!playing.value && frame.value >= last.value) frame.value = 0
  playing.value = !playing.value
}
watch(playing, (on) => {
  if (playTimer !== null) {
    window.clearInterval(playTimer)
    playTimer = null
  }
  if (!on) return
  playTimer = window.setInterval(() => {
    if (frame.value >= last.value) stop()
    else frame.value += 1
  }, 1000 / fps.value)
})
function onScrub(e: Event): void {
  untouched = false
  stop()
  frame.value = parseInt((e.target as HTMLInputElement).value, 10) || 0
}
function jump(day: number | null): void {
  if (day === null) return
  untouched = false
  stop()
  frame.value = day
}

// Previous / next IMAGE: the days the high-resolution track has a picture
// (most of its days are black); with only MODIS on screen — an image every
// day — or no high-resolution track yet, the days of the track shown.
const stepHas = computed(() => {
  const hi = trackOf('hires')
  const t = props.mode !== 'modis' && hi ? hi : (trackOf('modis') ?? hi)
  return t?.has ?? ''
})
const prevImage = computed(() => {
  for (let i = Math.min(frame.value, stepHas.value.length) - 1; i >= 0; i--) if (stepHas.value[i] === '1') return i
  return null
})
const nextImage = computed(() => {
  for (let i = frame.value + 1; i < stepHas.value.length; i++) if (stepHas.value[i] === '1') return i
  return null
})

// ── the scrubber's figure ─────────────────────────────────────────────
// Vertical layout, px (the svg is AXIS_H tall; x is in days).
const WATER_Y0 = 2
const WATER_Y1 = 22
const ROW0 = 30
const ROW_H = 16
const TRACK_Y = computed(() => ROW0 + ROW_H * panels.value.length + 4)
const AXIS_H = computed(() => TRACK_Y.value + 8)

const tickRows = computed(() =>
  panels.value.map((p, r) => {
    const y0 = ROW0 + r * ROW_H
    let d = ''
    const has = p.track?.has ?? ''
    for (let i = 0; i < has.length; i++) if (has[i] === '1') d += `M${i},${y0}V${y0 + ROW_H - 3}`
    return { key: p.key, d }
  }),
)
const rowLabels = computed(() =>
  panels.value.map((p, r) => ({
    key: p.key,
    y: ROW0 + r * ROW_H + (ROW_H - 3) / 2,
    label: sensorWord(p.label),
  })),
)

const claims = computed(() =>
  props.lake.drained_days.map((d) => ({ iso: d, label: claimLabel(d, props.manifest) })),
)
const claimDays = computed(() => {
  const s = props.manifest.seasons[CLAIM_YEAR]
  if (props.year !== CLAIM_YEAR || !s) return []
  return props.lake.drained_days.map((d) => dayOfIso(s.start, d)).filter((i) => i >= 0 && i <= last.value)
})
const claimPath = computed(() => claimDays.value.map((i) => `M${i},${ROW0 - 6}V${TRACK_Y.value}`).join(''))

const cloudBand = computed(() => {
  const s = props.manifest.seasons[CLAIM_YEAR]
  const c = props.manifest.cloud_days
  if (props.year !== CLAIM_YEAR || !s || !c.length) return null
  const idx = c.map((d) => dayOfIso(s.start, d)).sort((a, b) => a - b)
  return { x0: idx[0] - 0.5, x1: idx[idx.length - 1] + 0.5 }
})
const cloudLabel = computed(() => {
  const c = [...props.manifest.cloud_days].sort()
  if (!c.length) return ''
  const a = dayLabel(c[0])
  return c.length > 1 ? `${a.split(' ')[0]}–${dayLabel(c[c.length - 1])}` : a
})

const months = computed(() => (season.value ? monthTicks(season.value.start, frames.value) : []))
const monthPath = computed(() => months.value.map((m) => `M${m.day},${TRACK_Y.value + 3}v5`).join(''))

// Water within 1.25 km of the centre, per track shown: a thin line through
// the days that have a measurement. One scale: the high-resolution track's
// when it is up (a 250 m pixel's one-day spike must not flatten it — MODIS
// above the scale is clipped), else MODIS's own.
const waterMax = computed(() => {
  const top = (sensor: RevisitSensor | null): number => {
    let m = 0
    for (const p of panels.value) {
      if (sensor && p.sensor !== sensor) continue
      for (const w of p.track?.water_km2 ?? []) if (w !== null && w > m) m = w
    }
    return m
  }
  return top('hires') || top(null)
})
const waterY = (w: number): number =>
  WATER_Y1 - Math.min(1, w / (waterMax.value || 1)) * (WATER_Y1 - WATER_Y0)
const waterCurves = computed(() => {
  if (waterMax.value <= 0) return []
  return panels.value.flatMap((p) => {
    const w = p.track?.water_km2
    if (!w) return []
    let line = ''
    for (let i = 0; i < w.length; i++) {
      const v = w[i]
      if (v === null) continue
      line += `${line ? 'L' : 'M'}${i},${waterY(v).toFixed(2)}`
    }
    return line ? [{ key: p.key, line, coarse: p.sensor === 'modis' && panels.value.length > 1 }] : []
  })
})
// Dots only where a track is sparse (2010's high-resolution images).
const waterDots = computed(() => {
  if (waterMax.value <= 0) return []
  return panels.value.flatMap((p) => {
    const w = p.track?.water_km2
    if (!w || !p.track || p.sensor !== 'hires' || p.track.n_images > 40) return []
    const out: { key: string; day: number; y: number }[] = []
    for (let i = 0; i < w.length; i++) {
      const v = w[i]
      if (v !== null) out.push({ key: `${p.key}:${i}`, day: i, y: waterY(v) })
    }
    return out
  })
})

/** A day's x inside the scrub column (the thumb's travel), as CSS. */
function pct(day: number): string {
  return `calc(var(--thumb) / 2 + (100% - var(--thumb)) * ${(day / last.value).toFixed(5)})`
}

// Buttons give the focus back, so the site's keys (the presenter remote)
// never land on one.
function pick(e: MouseEvent, fn: () => void): void {
  ;(e.currentTarget as HTMLElement | null)?.blur()
  fn()
}
function close(e: MouseEvent): void {
  pick(e, () => emit('close'))
}

onMounted(() => void loadSidecar(props.lake.id))
onBeforeUnmount(() => {
  alive = false
  if (playTimer !== null) window.clearInterval(playTimer)
})
</script>

<style scoped>
.rvp {
  --thumb: 18px;
  --gap: 0.9rem;
  /* The movie's side: what the height leaves, or the panel's width shared
     by the movies on screen. */
  --sq: min(
    calc(100vh - var(--rvp-top, 6.6rem) - 19.2rem),
    calc((100cqw - (var(--n) - 1) * var(--gap)) / var(--n))
  );
  container-type: inline-size;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  color: #f5f0e6;
  font-family: 'Inter', system-ui, sans-serif;
}

/* ---- head: the lake, the paper's days for it, the way back ---------- */
.rvp-head {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  min-height: 2.5rem;
}
.rvp-id {
  margin: 0;
  font-family: 'EB Garamond', serif;
  font-weight: 500;
  font-size: 2rem;
  line-height: 1;
  letter-spacing: 0.02em;
  color: var(--gold-bright);
  white-space: nowrap;
}
.rvp-claims {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  flex: 1;
  min-width: 0;
}
.rvp-chip {
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  border: 1.5px solid var(--gold-bright);
  background: rgba(244, 207, 106, 0.16);
  color: var(--gold-bright);
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
}
.rvp-claims-year {
  align-self: center;
  margin-left: 0.15rem;
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--gold-bright);
}
.rvp-chip-none {
  border-color: rgba(245, 240, 230, 0.6);
  background: transparent;
  color: rgba(245, 240, 230, 0.92);
}
.rvp-close {
  flex: none;
  background: rgba(0, 0, 0, 0.6);
  border: 1.5px solid rgba(255, 255, 255, 0.42);
  color: rgba(245, 245, 245, 0.92);
  font-family: inherit;
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.5rem 1.05rem;
  border-radius: 999px;
  cursor: pointer;
  white-space: nowrap;
  transition: color 0.2s, border-color 0.2s, background 0.2s;
}
.rvp-close:hover {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.75);
  background: rgba(255, 255, 255, 0.06);
}

/* ---- the two toggles (Additional Work's segmented control) ---------- */
.rvp-toggles {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.7rem;
}
.rvp-seg {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  padding: 0.22rem;
  border: 1.5px solid rgba(232, 185, 74, 0.6);
  border-radius: 999px;
  background: rgba(8, 7, 6, 0.84);
}
.rvp-seg-btn {
  background: transparent;
  border: 1px solid transparent;
  border-radius: 999px;
  color: rgba(244, 207, 106, 0.95);
  font-family: inherit;
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  white-space: nowrap;
  padding: 0.34rem 0.9rem;
  cursor: pointer;
  transition: color 0.2s, background 0.2s, border-color 0.2s;
}
.rvp-seg-btn:hover {
  color: #fff8d8;
}
.rvp-seg-btn--on,
.rvp-seg-btn--on:hover {
  color: #0a0a0a;
  background: var(--gold-bright);
  border-color: var(--gold-bright);
}

/* ---- the movie(s) ---------------------------------------------------- */
.rvp-stage {
  display: flex;
  justify-content: center;
  gap: var(--gap);
}
.rvp-panel {
  margin: 0;
  width: var(--sq);
  flex: none;
}
.rvp-frame {
  position: relative;
  width: var(--sq);
  height: var(--sq);
  border-radius: 10px;
  overflow: hidden;
  background: #000;
  border: 1.5px solid rgba(232, 185, 74, 0.55);
}
.rvp-video {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  /* MODIS is 20 pixels across the tile: keep them pixels */
  image-rendering: pixelated;
  opacity: 0;
  transition: opacity 0.25s;
}
.rvp-video.ready {
  opacity: 1;
}
.rvp-tag {
  position: absolute;
  left: 10px;
  top: 10px;
  padding: 3px 11px;
  border-radius: 999px;
  background: rgba(8, 7, 6, 0.82);
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: #f5f0e6;
  white-space: nowrap;
}
.rvp-scale {
  position: absolute;
  right: 12px;
  bottom: 12px;
  height: 7px;
  border: 2px solid #f5f0e6;
  border-top: none;
  filter: drop-shadow(0 0 2px rgba(0, 0, 0, 0.95));
}
.rvp-scale i {
  position: absolute;
  right: 0;
  bottom: 9px;
  font-style: normal;
  font-size: 0.95rem;
  font-weight: 600;
  white-space: nowrap;
  color: #f5f0e6;
  text-shadow: 0 0 4px #000, 0 0 2px #000;
}
.rvp-plate {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: repeating-linear-gradient(135deg, #0b0c10 0 14px, #101218 14px 28px);
}
.rvp-plate span {
  padding: 0.45rem 1rem;
  border: 1.5px solid rgba(245, 240, 230, 0.55);
  border-radius: 999px;
  background: rgba(5, 5, 5, 0.85);
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #f5f0e6;
}
.rvp-cap {
  min-height: 1.5rem;
  margin-top: 0.3rem;
  text-align: center;
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #f5f0e6;
}
.rvp-cap-none {
  color: rgba(245, 240, 230, 0.92);
}

/* ---- the bar: previous image · play · next image, the date, the key -- */
.rvp-bar {
  display: flex;
  align-items: center;
  gap: 1.1rem;
  min-height: 2.75rem;
}
.rvp-clock {
  display: flex;
  align-items: baseline;
  gap: 0.45em;
  flex: none;
  /* the widest date ("30 SEP") never moves the key */
  min-width: 9.6rem;
  font-variant-numeric: tabular-nums;
}
.rvp-date {
  font-family: 'EB Garamond', serif;
  font-size: 1.9rem;
  font-weight: 500;
  line-height: 1;
  letter-spacing: 0.04em;
  color: #fff8d8;
}
.rvp-date-year {
  font-size: 1.05rem;
  font-weight: 500;
  color: rgba(245, 240, 230, 0.9);
}

.rvp-btns {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex: none;
}
.rvp-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  padding: 0;
  border-radius: 50%;
  border: 1.5px solid var(--gold);
  background: rgba(56, 38, 12, 0.6);
  color: var(--gold-bright);
  fill: currentColor;
  cursor: pointer;
  transition: background 0.2s, color 0.2s, opacity 0.2s;
}
.rvp-btn svg {
  display: block;
  pointer-events: none;
}
.rvp-btn:hover:not(:disabled) {
  background: rgba(96, 66, 18, 0.85);
  color: #fff8d8;
}
.rvp-btn:disabled {
  opacity: 0.4;
  cursor: default;
}
.rvp-btn-play {
  width: 44px;
  height: 44px;
}

/* ---- the scrubber ------------------------------------------------------ */
.rvp-scrub {
  position: relative;
  padding-bottom: 1.35rem;
}
/* two tick rows: room on the left for their names */
.rvp-scrub-rows {
  margin-left: 11.6rem;
}
.rvp-axis {
  display: block;
  width: calc(100% - var(--thumb));
  height: v-bind('`${AXIS_H}px`');
  margin: 0 calc(var(--thumb) / 2);
  overflow: visible;
}
.rvp-tick {
  fill: none;
  stroke: #f5f0e6;
  stroke-width: 2;
  vector-effect: non-scaling-stroke;
}
.rvp-claim {
  fill: none;
  stroke: var(--gold-bright);
  stroke-width: 3;
  vector-effect: non-scaling-stroke;
}
.rvp-cloud {
  fill: rgba(190, 200, 215, 0.42);
}
.rvp-month-tick {
  fill: none;
  stroke: rgba(245, 240, 230, 0.85);
  stroke-width: 1.5;
  vector-effect: non-scaling-stroke;
}
.rvp-water {
  fill: none;
  stroke: #74d4ff;
  stroke-width: 2;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
}
/* beside the high-resolution curve, the 250 m one steps back */
.rvp-water-coarse {
  stroke: rgba(116, 212, 255, 0.6);
  stroke-width: 1.5;
}
.rvp-water-dot {
  position: absolute;
  width: 7px;
  height: 7px;
  margin: -3.5px 0 0 -3.5px;
  border-radius: 50%;
  background: #74d4ff;
  box-shadow: 0 0 0 1.5px rgba(5, 8, 12, 0.9);
  pointer-events: none;
}
.rvp-water-label {
  position: absolute;
  right: calc(var(--thumb) / 2);
  top: -2px;
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: #74d4ff;
  white-space: nowrap;
  pointer-events: none;
}
.rvp-claim-cap {
  position: absolute;
  top: 19px;
  width: 9px;
  height: 9px;
  margin-left: -4.5px;
  background: var(--gold-bright);
  transform: rotate(45deg);
  box-shadow: 0 0 0 1.5px rgba(5, 8, 12, 0.9);
  pointer-events: none;
}
.rvp-row-label {
  position: absolute;
  right: calc(100% + 0.55rem);
  transform: translateY(-50%);
  font-size: 0.92rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  white-space: nowrap;
  color: #f5f0e6;
  pointer-events: none;
}
.rvp-month {
  position: absolute;
  bottom: 0;
  transform: translateX(4px);
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: #f5f0e6;
  pointer-events: none;
}
/* the range rides the axis's baseline */
.rvp-range {
  position: absolute;
  left: 0;
  right: 0;
  top: v-bind('`${TRACK_Y - 10}px`');
  width: 100%;
  -webkit-appearance: none;
  appearance: none;
  height: 20px;
  margin: 0;
  background: transparent;
  cursor: pointer;
}
.rvp-range:focus {
  outline: none;
}
.rvp-range::-webkit-slider-runnable-track {
  height: 5px;
  border-radius: 3px;
  background: linear-gradient(
    to right,
    var(--gold) 0,
    var(--gold) var(--fill),
    rgba(245, 240, 230, 0.3) var(--fill),
    rgba(245, 240, 230, 0.3) 100%
  );
}
.rvp-range::-moz-range-track {
  height: 5px;
  border-radius: 3px;
  background: rgba(245, 240, 230, 0.3);
}
.rvp-range::-moz-range-progress {
  height: 5px;
  border-radius: 3px;
  background: var(--gold);
}
.rvp-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: var(--thumb);
  height: var(--thumb);
  margin-top: -6.5px;
  border-radius: 50%;
  background: #fff8d8;
  border: 2.5px solid #0d0b09;
  box-shadow: 0 0 0 1.5px var(--gold-bright);
}
.rvp-range::-moz-range-thumb {
  width: 13px;
  height: 13px;
  border-radius: 50%;
  background: #fff8d8;
  border: 2.5px solid #0d0b09;
  box-shadow: 0 0 0 1.5px var(--gold-bright);
}

/* ---- the scrubber's key ------------------------------------------------ */
.rvp-key {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.2rem 1.2rem;
  font-size: 0.95rem;
  font-weight: 500;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #f5f0e6;
}
.rvp-key-item {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  white-space: nowrap;
}
.rvp-key-claim {
  width: 9px;
  height: 9px;
  background: var(--gold-bright);
  transform: rotate(45deg);
}
.rvp-key-cloud {
  width: 14px;
  height: 12px;
  background: rgba(190, 200, 215, 0.55);
}
.rvp-key-tick {
  width: 2px;
  height: 12px;
  background: #f5f0e6;
}
</style>
