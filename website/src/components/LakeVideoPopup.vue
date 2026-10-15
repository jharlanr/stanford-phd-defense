<template>
  <Transition name="dock-slide">
    <aside class="video-dock" role="dialog" aria-label="Lake drain video">
      <!-- The LEADER (the director's request): a line from the card's nearest
           edge to the lake's drawn outline on the globe, in the lake's
           colour with a dark edge, a dot at the lake end. Re-anchored
           every frame from `__featuredLakeScreens[lakeId]` (Globe.vue
           projects the outline ring), so it follows a hand-dragged
           globe; the card is convex and the line starts on its edge, so
           it never crosses the card. Fades with the card (same root). -->
      <svg v-if="leader" class="leader" aria-hidden="true">
        <g :style="{ opacity: leader.op }">
          <line class="leader-edge" :x1="leader.x1" :y1="leader.y1" :x2="leader.x2" :y2="leader.y2" />
          <circle class="leader-edge" :cx="leader.x2" :cy="leader.y2" r="4.5" />
          <line class="leader-line" :stroke="leader.color" :x1="leader.x1" :y1="leader.y1" :x2="leader.x2" :y2="leader.y2" />
          <circle class="leader-dot" :fill="leader.color" :cx="leader.x2" :cy="leader.y2" r="4.5" />
          <circle class="leader-foot" :fill="leader.color" :cx="leader.x1" :cy="leader.y1" r="3" />
        </g>
      </svg>

      <div ref="cardEl" class="dock-card">
        <!-- Lean head: the lake's id/name + its class chip, nothing else
             (the dates live on the chart's axis). -->
        <header class="dock-header">
          <span class="dock-title">{{ title }}</span>
          <span v-if="sidecar?.class" class="dock-chip">
            <b>{{ sidecar.class }}</b>{{ sidecar.class_name ? ` ${sidecar.class_name}` : '' }}
          </span>
          <button class="close-btn" @click="$emit('close')" aria-label="Close">✕</button>
        </header>

        <!-- The figure column: the movie, then the normalized-volume
             plot BELOW it with its own margin (the frames used to
             overlap the curve, which the director disliked). Source mp4
             is built straight from the Sentinel-2 reflectance stack (no
             burn-in date stamp), so the date badge is OUR own. -->
        <div class="dock-fig">
          <div class="video-crop">
            <video
              ref="videoEl"
              class="lake-video"
              :src="src"
              autoplay
              loop
              muted
              playsinline
              @loadedmetadata="onLoaded"
            />
            <div class="date-badge">
              <span class="date-badge-day">{{ currentDateLabel || '—' }}</span>
              <span class="date-badge-year">2019</span>
            </div>
          </div>

          <!-- Normalized-lake-volume chart. Curve, dots, and outline all
               wear the lake's DRAINAGE-CLASS color (matches the outline
               burned into the movie and the polygon on the globe).
               Backward-filled across NaN days (the director specified bfill, not ffill)
               so drops land on the acquisition day that SAW them. The x
               axis is the CALENDAR: valid-frame movies (Ch.2) skip the
               unimaged days, and their sidecar's `day` puts each frame
               back on its real date. -->
          <div class="pwater-chart" v-if="frames.length">
            <div class="pwater-header">
              <span class="pwater-label">Normalized lake volume</span>
              <span class="pwater-value">
                <strong>{{ currentPWater !== null ? currentPWater.toFixed(2) : '—' }}</strong>
              </span>
            </div>
            <svg
              class="pwater-svg"
              :viewBox="`0 0 ${CHART_W} ${CHART_H}`"
              preserveAspectRatio="xMidYMid meet"
            >
              <!-- Y-axis gridlines + tick labels (0, 0.5, 1.0) -->
              <g class="pwater-grid">
                <line
                  v-for="g in Y_TICKS"
                  :key="`gy-${g}`"
                  :x1="PAD_L" :y1="yForP(g)"
                  :x2="CHART_W - PAD_R" :y2="yForP(g)"
                />
              </g>
              <g class="pwater-tick-labels">
                <text
                  v-for="g in Y_TICKS"
                  :key="`tly-${g}`"
                  :x="PAD_L - 5" :y="yForP(g) + 4"
                  text-anchor="end"
                >{{ g.toFixed(1) }}</text>
              </g>

              <!-- Filled area under curve + the backward-filled line -->
              <path :d="pwaterAreaPath" class="pwater-area" />
              <path :d="pwaterLinePath" class="pwater-line" />

              <!-- Dots — only at days with a REAL measurement. -->
              <circle
                v-for="(p, i) in pwaterPoints"
                :key="`pt-${i}`"
                :cx="p.x" :cy="p.y" :r="2.2"
                class="pwater-point"
              />

              <!-- Drain / freeze-up reference (from the sidecar) -->
              <template v-if="drainTick">
                <line
                  :x1="drainTick.x" :y1="PAD_T" :x2="drainTick.x" :y2="CHART_H - PAD_B"
                  class="pwater-drainline"
                />
                <text
                  :x="drainTick.x" :y="PAD_T - 4"
                  text-anchor="middle"
                  class="pwater-drain-label"
                >{{ drainTick.label }}</text>
              </template>

              <!-- Animated current-frame marker -->
              <line
                :x1="markerX" :y1="PAD_T" :x2="markerX" :y2="CHART_H - PAD_B"
                class="pwater-marker-line"
              />
              <circle
                v-if="currentPWater !== null"
                :cx="markerX" :cy="markerY"
                :r="4"
                class="pwater-marker-dot"
              />

              <!-- X-axis baseline + sidecar-driven date ticks -->
              <line
                :x1="PAD_L" :y1="CHART_H - PAD_B"
                :x2="CHART_W - PAD_R" :y2="CHART_H - PAD_B"
                class="pwater-axis"
              />
              <g class="pwater-tick-labels">
                <text
                  v-for="(t, i) in xTicks"
                  :key="`tx-${t.label}`"
                  :x="t.x" :y="CHART_H - PAD_B + 14"
                  :text-anchor="i === 0 ? 'start' : i === xTicks.length - 1 ? 'end' : 'middle'"
                >{{ t.label }}</text>
              </g>
            </svg>
          </div>
        </div>
      </div>
    </aside>
  </Transition>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps<{
  src: string
  /** Sidecar JSON URL — per-frame date + p_water + QA, plus the lake's
   *  drainage-class accent color, axis ticks, and drain/freeze marker.
   *  The popup reads this once on mount and uses video.currentTime to
   *  index into frames[], so the date label and chart marker stay
   *  locked to the actual mp4 cadence (no interpolation). */
  sidecarUrl: string
  /** The card's whole head: the lake's name/id ("Lake 2394", "North Lake"). */
  title: string
  /** The globe's featured-lake id the leader line points at (null = no leader). */
  lakeId?: string | null
}>()
const emit = defineEmits<{ close: [] }>()

interface FrameMeta {
  t_sec: number
  date_iso: string
  p_water: number | null
  cloud_pct: number | null
  nan_pct: number | null
  /** Valid-frame movies (Ch.2 `lakes_valid/`): days since `t0`. */
  day?: number
}
interface Sidecar {
  fps: number
  frame_count: number
  duration_sec: number
  frames: FrameMeta[]
  accent?: string
  class?: string
  class_name?: string
  lake_name?: string
  ticks?: Array<{ date_iso: string; label: string }>
  drain?: { date_iso: string; label: string } | null
  /** Valid-frame sidecars (build_pnas_lakes.py --valid): the window's
   *  first day, its length, and p_water for EVERY day — the movie skips
   *  the unimaged days, the chart's calendar does not. */
  t0?: string
  days?: number
  p_water_daily?: Array<number | null>
}

const videoEl = ref<HTMLVideoElement | null>(null)
const cardEl = ref<HTMLElement | null>(null)
const currentTime = ref(0)
const duration    = ref(0)
const frames      = ref<FrameMeta[]>([])
const sidecar     = ref<Sidecar | null>(null)

// Drainage-class accent — wired into the CSS below via v-bind().
const accent = computed(() => sidecar.value?.accent ?? '#f5c75e')

function onLoaded(): void {
  if (videoEl.value) duration.value = videoEl.value.duration || 0
}

// rAF poll of video.currentTime. Drives every overlay (date badge,
// volume readout, chart marker) at the page's repaint cadence instead
// of @timeupdate, which fires at ~4 Hz and visibly trails the frame.
let rafId = 0
function tickClock(): void {
  if (videoEl.value) currentTime.value = videoEl.value.currentTime
  updateLeader()
  rafId = requestAnimationFrame(tickClock)
}

// ─────────────── the leader line ──────────────────────────────────────
interface Leader { x1: number; y1: number; x2: number; y2: number; color: string; op: number }
const leader = ref<Leader | null>(null)
type LakeScreen = { x: number; y: number; visible: boolean; color?: string; op?: number; ring?: [number, number][] }

/** First crossing of segment A→C with the closed ring (the hit nearest A). */
function ringHit(ax: number, ay: number, cx: number, cy: number, ring: [number, number][]): [number, number] | null {
  let bestT = Infinity
  const dx = cx - ax, dy = cy - ay
  for (let i = 0; i < ring.length; i++) {
    const [px, py] = ring[i]
    const [qx, qy] = ring[(i + 1) % ring.length]
    const ex = qx - px, ey = qy - py
    const den = dx * ey - dy * ex
    if (Math.abs(den) < 1e-9) continue
    const t = ((px - ax) * ey - (py - ay) * ex) / den
    const u = ((px - ax) * dy - (py - ay) * dx) / den
    if (t >= 0 && t <= 1 && u >= 0 && u <= 1 && t < bestT) bestT = t
  }
  return bestT === Infinity ? null : [ax + dx * bestT, ay + dy * bestT]
}

function updateLeader(): void {
  const id = props.lakeId
  const card = cardEl.value
  const s = id ? ((window as any).__featuredLakeScreens?.[id] as LakeScreen | undefined) : undefined
  if (!card || !s || !s.visible || (s.op ?? 1) < 0.02) { if (leader.value) leader.value = null; return }
  const r = card.getBoundingClientRect()
  // The card's nearest point to the lake (kept off the rounded corners).
  const R = 16
  const x1 = Math.min(Math.max(s.x, r.left), r.right)
  const y1 = Math.min(Math.max(s.y, r.top + R), r.bottom - R)
  if (x1 > r.left && x1 < r.right && y1 > r.top && y1 < r.bottom) { if (leader.value) leader.value = null; return }
  const hit = s.ring && s.ring.length > 2 ? ringHit(x1, y1, s.x, s.y, s.ring) : null
  const [x2, y2] = hit ?? [s.x, s.y]
  leader.value = { x1, y1, x2, y2, color: s.color ?? accent.value, op: Math.min(1, s.op ?? 1) }
}

const currentIndex = computed<number>(() => {
  if (!sidecar.value || !duration.value) return 0
  const fps = sidecar.value.fps
  return Math.min(
    sidecar.value.frame_count - 1,
    Math.max(0, Math.floor(currentTime.value * fps + 1e-6)),
  )
})

const currentFrame = computed<FrameMeta | null>(() =>
  frames.value.length ? frames.value[currentIndex.value] : null,
)

const currentDateLabel = computed<string>(() => {
  const f = currentFrame.value
  if (!f) return ''
  const [, m, d] = f.date_iso.split('-')
  const month = ['Jan','Feb','Mar','Apr','May','June','July','Aug','Sep','Oct','Nov','Dec'][parseInt(m, 10) - 1] || ''
  return `${parseInt(d, 10)} ${month}`
})


// ─────────────── chart geometry ───────────────────────────────────────

// Chart viewBox + padding. The plot band sits LOW in the overlay (large
// PAD_T) so the curve never rides up into the imagery above the
// gradient backdrop — the director asked for the curve a little lower.
const CHART_W = 400
const CHART_H = 100
const PAD_L   = 30   // y-tick labels
const PAD_R   = 8
const PAD_T   = 26   // breathing room for the drain tag + imagery
const PAD_B   = 20   // x-tick labels
const PLOT_W  = CHART_W - PAD_L - PAD_R
const PLOT_H  = CHART_H - PAD_T - PAD_B

const Y_TICKS = [0, 0.5, 1.0]

// The chart's x axis is the CALENDAR. Day mode (valid-frame sidecars:
// `days` + `p_water_daily` + per-frame `day`) plots the daily series and
// puts each kept frame on its real day; the legacy one-frame-per-day
// sidecars (Ch.1) are the same thing with day = frame index.
const dayMode = computed<boolean>(() => {
  const s = sidecar.value
  return !!(s && s.days && s.p_water_daily && frames.value.every((f) => f.day !== undefined))
})
const nDays = computed<number>(() =>
  dayMode.value ? (sidecar.value!.days as number) : frames.value.length,
)
/** p_water per calendar day (null = no measurement that day). */
const dailyP = computed<Array<number | null>>(() =>
  dayMode.value
    ? (sidecar.value!.p_water_daily as Array<number | null>)
    : frames.value.map((f) => f.p_water),
)
function dayOfFrame(i: number): number {
  const f = frames.value[i]
  return f && f.day !== undefined && dayMode.value ? f.day : i
}

function xForDay(d: number): number {
  if (nDays.value <= 1) return PAD_L + PLOT_W / 2
  return PAD_L + (d / (nDays.value - 1)) * PLOT_W
}
function yForP(p: number): number {
  const clamped = Math.max(0, Math.min(1, p))
  return PAD_T + (1 - clamped) * PLOT_H
}

function dayForDate(iso: string): number | null {
  if (dayMode.value && sidecar.value?.t0) {
    const d = Math.round((Date.parse(iso) - Date.parse(sidecar.value.t0)) / 86400000)
    return d >= 0 && d < nDays.value ? d : null
  }
  const idx = frames.value.findIndex((f) => f.date_iso === iso)
  if (idx >= 0) return idx
  // Nearest fallback (frames are daily, so this rarely fires).
  let best = -1
  let bestD = Infinity
  const want = Date.parse(iso)
  frames.value.forEach((f, i) => {
    const d = Math.abs(Date.parse(f.date_iso) - want)
    if (d < bestD) { bestD = d; best = i }
  })
  return best >= 0 ? best : null
}

interface FilledPt { x: number; y: number; p: number; real: boolean }

// BACKWARD-filled p_water per day — each NaN day inherits the NEXT
// valid measurement, so a drain cliff lands on the acquisition day that
// saw it rather than smearing a full lake across the cloud gap.
// Trailing nulls (after the last valid sample) inherit the last value.
const pwaterFilled = computed<Array<FilledPt | null>>(() => {
  const raw = dailyP.value
  const n = raw.length
  const filled: Array<number | null> = new Array(n).fill(null)
  let nxt: number | null = null
  for (let i = n - 1; i >= 0; i--) {
    if (raw[i] !== null) nxt = raw[i]
    filled[i] = nxt
  }
  let last: number | null = null
  for (let i = 0; i < n; i++) {
    if (raw[i] !== null) last = raw[i]
    if (filled[i] === null) filled[i] = last
  }
  return raw.map((r, i) => {
    const p = filled[i]
    if (p === null) return null
    return { x: xForDay(i), y: yForP(p), p, real: r !== null }
  })
})

// Backward-filled p_water at the current frame's day (matches the curve).
const currentPWater = computed<number | null>(() =>
  pwaterFilled.value[dayOfFrame(currentIndex.value)]?.p ?? null,
)

const pwaterPoints = computed(() =>
  (pwaterFilled.value.filter((p): p is FilledPt => p !== null && p.real)),
)

const pwaterLinePath = computed<string>(() => {
  const pts = pwaterFilled.value.filter((p): p is FilledPt => p !== null)
  if (pts.length < 2) return ''
  return pts
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(' ')
})

const pwaterAreaPath = computed<string>(() => {
  const pts = pwaterFilled.value.filter((p): p is FilledPt => p !== null)
  if (pts.length < 2) return ''
  const baseY = CHART_H - PAD_B
  const parts = [`M ${pts[0].x.toFixed(1)} ${baseY.toFixed(1)}`]
  for (const p of pts) parts.push(`L ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
  parts.push(`L ${pts[pts.length - 1].x.toFixed(1)} ${baseY.toFixed(1)} Z`)
  return parts.join(' ')
})

// Sidecar-driven markers.
const drainTick = computed<{ x: number; label: string } | null>(() => {
  const d = sidecar.value?.drain
  if (!d) return null
  const day = dayForDate(d.date_iso)
  return day === null ? null : { x: xForDay(day), label: d.label }
})

const xTicks = computed<Array<{ x: number; label: string }>>(() => {
  const ticks = sidecar.value?.ticks ?? []
  return ticks
    .map((t) => {
      const day = dayForDate(t.date_iso)
      return day === null ? null : { x: xForDay(day), label: t.label }
    })
    .filter((t): t is { x: number; label: string } => t !== null)
})

const markerX = computed<number>(() => xForDay(dayOfFrame(currentIndex.value)))
const markerY = computed<number>(() => {
  const ff = pwaterFilled.value[dayOfFrame(currentIndex.value)]
  if (ff) return ff.y
  const first = pwaterFilled.value.find((p) => p !== null)
  return first ? first.y : CHART_H / 2
})

// ─────────────── lifecycle ────────────────────────────────────────────

function onKey(e: KeyboardEvent): void {
  if (e.key === 'Escape') emit('close')
}

async function fetchSidecar(): Promise<void> {
  try {
    const r = await fetch(props.sidecarUrl)
    if (!r.ok) return
    const j = (await r.json()) as Sidecar
    sidecar.value = j
    frames.value = j.frames
  } catch {
    // Non-fatal: the date label falls back to '—' and the chart stays
    // hidden (v-if frames.length).
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
  void fetchSidecar()
  rafId = requestAnimationFrame(tickClock)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  if (rafId) cancelAnimationFrame(rafId)
})
</script>

<style scoped>
/* Right-side dock, full-viewport (the leader's SVG shares it). The card
   hugs its figure column (movie over plot) and sits in the space BELOW
   the ribbon + sub-menu (--chrome-bottom), so it never rides up under
   the Back/Next pills, and against the right edge — the lakes both
   chapters frame sit in the left ~half of the screen. One size in both
   chapters (the director wanted the movies very visible): the
   square is the band's height minus the card's fixed rows (head, chart
   header, gaps, padding ≈ 6.6rem) and the chart (¼ of the width). */
.video-dock {
  --gap-top: 0.75rem;
  --gap-bot: 0.9rem;
  --fig-w: min(
    calc((100vh - var(--chrome-bottom, 6vh) - var(--gap-top) - var(--gap-bot) - 6.6rem) / 1.25),
    48vw,
    820px
  );
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: calc(var(--chrome-bottom, 6vh) + var(--gap-top)) 1.6rem var(--gap-bot) 1rem;
  pointer-events: none;
  z-index: 50;
}

.leader {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
  pointer-events: none;
}
.leader line { stroke-linecap: round; }
.leader .leader-edge { stroke: rgba(8, 6, 4, 0.9); stroke-width: 5.5; fill: rgba(8, 6, 4, 0.9); }
.leader circle.leader-edge { stroke-width: 2.5; }
.leader .leader-line { stroke-width: 2.6; }

.dock-card {
  position: relative;
  pointer-events: auto;
  width: calc(var(--fig-w) + 2rem);
  background: linear-gradient(180deg, #0c0a07 0%, #07080a 100%);
  border: 1px solid var(--gold-faint);
  border-radius: 14px;
  padding: 0.7rem 1rem 0.85rem 1rem;
  box-shadow:
    0 18px 70px rgba(0, 0, 0, 0.75),
    0 0 80px rgba(245, 199, 94, 0.10),
    inset 0 0 1px var(--gold-faint);
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

/* One slim row: the lake id, its class chip, the close button. */
.dock-header {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  height: 2.1rem;
}

.dock-title {
  font-family: 'EB Garamond', serif;
  font-size: 1.75rem;
  line-height: 1;
  letter-spacing: 0.02em;
  color: var(--gold-bright);
  white-space: nowrap;
}

.dock-chip {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.95rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: v-bind(accent);
  border: 1.5px solid v-bind(accent);
  border-radius: 999px;
  padding: 0.18rem 0.65rem;
  white-space: nowrap;
}
.dock-chip b { font-weight: 700; margin-right: 0.15em; }

.dock-fig {
  width: var(--fig-w);
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

/* Video frame — square, the 512×512 source uncropped. */
.video-crop {
  position: relative;
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 8px;
  overflow: hidden;
  background: #0a0a0a;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.lake-video {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.date-badge {
  position: absolute;
  top: 0.8rem;
  left: 0.8rem;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 0.45rem 0.75rem;
  background: rgba(8, 6, 4, 0.78);
  border: 1px solid var(--gold-faint);
  border-radius: 8px;
  backdrop-filter: blur(6px);
  pointer-events: none;
}

.date-badge-day {
  font-family: 'EB Garamond', serif;
  font-size: 2.1rem;
  line-height: 1.0;
  color: var(--gold-bright);
  letter-spacing: 0.01em;
}

.date-badge-year {
  margin-top: 0.2rem;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1.05rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--gold);
}

/* ─────────────── normalized-lake-volume chart (below the movie) ──── */
/* Its own band under the imagery, the same width — never over it. */
.pwater-chart {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  padding: 0 0.1rem;
  pointer-events: none;
}

.pwater-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.95rem;
  color: rgba(245, 245, 245, 0.85);
}

.pwater-label {
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: v-bind(accent);
  font-size: 0.98rem;
  font-weight: 600;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.9);
}

.pwater-value {
  font-variant-numeric: tabular-nums;
  color: v-bind(accent);
  font-size: 1.05rem;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.9);
}
.pwater-value strong { font-weight: 600; }

.pwater-svg {
  width: 100%;
  display: block;
  overflow: visible;
}

.pwater-axis {
  stroke: rgba(255, 255, 255, 0.6);
  stroke-width: 1.5;
}

.pwater-grid line {
  stroke: rgba(255, 255, 255, 0.16);
  stroke-width: 1;
  stroke-dasharray: 2 3;
}

.pwater-tick-labels text {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 13px;
  fill: rgba(245, 245, 245, 0.8);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.pwater-area {
  fill: v-bind(accent);
  fill-opacity: 0.16;
}

.pwater-line {
  fill: none;
  stroke: v-bind(accent);
  stroke-width: 2.4;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.pwater-point {
  fill: v-bind(accent);
  opacity: 0.85;
}

.pwater-drainline {
  stroke: rgba(255, 255, 255, 0.8);
  stroke-width: 1.6;
  stroke-dasharray: 3 3;
}

.pwater-drain-label {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 13px;
  fill: rgba(245, 245, 245, 0.9);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.pwater-marker-line {
  stroke: rgba(255, 255, 255, 0.85);
  stroke-width: 2.2;
}

.pwater-marker-dot {
  fill: #ffffff;
  stroke: v-bind(accent);
  stroke-width: 1.6;
}

.close-btn {
  margin-left: auto;
  flex: none;
  width: 32px;
  height: 32px;
  border-radius: 999px;
  border: 1px solid var(--gold-dim);
  background: rgba(0, 0, 0, 0.55);
  color: var(--gold);
  font-size: 0.85rem;
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s, background 0.2s;
}
.close-btn:hover {
  color: var(--gold-bright);
  border-color: var(--gold);
  background: rgba(36, 24, 8, 0.75);
}

/* The dock (with the leader) fades; only the CARD slides, so the
   leader's lake end stays pinned to the lake through the transition. */
.dock-slide-enter-active,
.dock-slide-leave-active {
  transition: opacity 0.32s;
}
.dock-slide-enter-active .dock-card,
.dock-slide-leave-active .dock-card {
  transition: transform 0.32s cubic-bezier(0.2, 0.7, 0.3, 1.05);
}
.dock-slide-enter-from,
.dock-slide-leave-to {
  opacity: 0;
}
.dock-slide-enter-from .dock-card,
.dock-slide-leave-to .dock-card {
  transform: translateX(40px);
}
</style>
