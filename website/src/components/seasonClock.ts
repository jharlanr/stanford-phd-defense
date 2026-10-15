// The month clock of the Introduction's "seasons" steps — one per page
// load, living OUTSIDE the components so it survives the step changes
// (2 ↔ 3, and 3 → the fly-along → back to 3 keeps the month).
//
// It owns: the manifest, the frame pool, which month is showing, play /
// pause, and the ~150 ms crossfade between consecutive months (writing
// seasonDrape.mix every animation frame). The UI reads `seasonUi`
// (reactive, changes once per month); the Globe reads `seasonDrape`.
//
// Warm-up: SectionMotivation calls warmSeasons() from step 1 on, so the
// manifest, the 3 MB static texture and the opening month are decoded and
// on the GPU (at zero recolour) before "next" is pressed — the step-2
// click then only eases a uniform.

import { markRaw, reactive } from 'vue'
import {
  SEASON_MONTHS_PER_S,
  SEASON_XFADE_MS,
  SEASONS_STATIC_KEY,
  SEASONS_PREFIX,
  loadSeasonsManifest,
  loadSeasonsRunoff,
  type SeasonsManifest,
  type SeasonsRunoff,
} from '../config/seasons'
import { SeasonFramePool, loadSeasonStatic, seasonDrape } from './seasonDrape'

export const seasonUi = reactive({
  manifest: null as SeasonsManifest | null,
  /** Monthly meltwater runoff for the curve panel (null: off / not yet). */
  runoff: null as SeasonsRunoff | null,
  /** The month showing (index into manifest.frames); −1 before the first. */
  idx: -1,
  startIdx: 0,
  playing: false,
})

let pool: SeasonFramePool | null = null
let warmPromise: Promise<void> | null = null
let raf: number | null = null
let lastStepAt = 0
let fade: { from: number; to: number; t0: number; ms: number } | null = null
let token = 0

/** Idempotent: manifest → static t + the opening month, all decoded. */
export function warmSeasons(): Promise<void> {
  if (!warmPromise) {
    warmPromise = (async () => {
      // The runoff is 17 kB beside the frames; it never holds the clock.
      void loadSeasonsRunoff().then((r) => {
        if (r) seasonUi.runoff = markRaw(r)
      })
      const m = await loadSeasonsManifest()
      seasonUi.manifest = markRaw(m)
      seasonDrape.anomStops = m.anomaly_colour.stops
      seasonDrape.anomLim = m.anomaly_colour.lim
      seasonDrape.anomFade = m.anomaly_colour.fade_mps
      seasonDrape.anomGrey = m.anomaly_colour.neutral_grey
      seasonDrape.deltaScale = m.delta.scale
      const start = Math.max(0, m.frames.findIndex((f) => f.ym === m.start_at))
      seasonUi.startIdx = start
      pool = new SeasonFramePool(m.frames)
      pool.fetchAll(start)
      const statics = loadSeasonStatic(SEASONS_STATIC_KEY.slice(SEASONS_PREFIX.length))
      const first = pool.get(start)
      await statics
      if (seasonUi.idx < 0) show(start, await first, 0)
      ensureLoop()
    })()
    warmPromise.catch((e) => {
      console.warn('[seasons] warm-up failed:', e)
      warmPromise = null
    })
  }
  return warmPromise
}

function ensureLoop(): void {
  if (raf === null) raf = window.requestAnimationFrame(tick)
}

function tick(now: number): void {
  raf = window.requestAnimationFrame(tick)
  if (fade) {
    const t = Math.min(1, (now - fade.t0) / fade.ms)
    seasonDrape.mix = fade.from + (fade.to - fade.from) * t
    if (t >= 1) fade = null
  }
  const m = seasonUi.manifest
  if (!seasonUi.playing || !m || !pool) return
  if (now - lastStepAt < 1000 / SEASON_MONTHS_PER_S) return
  const n = m.frames.length
  let next = seasonUi.idx + 1
  if (next >= n) next = seasonUi.startIdx
  // Hold (never skip a month) until the next one is decoded.
  if (!pool.ready(next)) {
    pool.get(next)
    return
  }
  lastStepAt = now
  void seasonGoto(next, SEASON_XFADE_MS)
}

function show(i: number, bmp: ImageBitmap, fadeMs: number): void {
  // Finish a running fade first so the slot being replaced is invisible.
  if (fade) {
    seasonDrape.mix = fade.to
    fade = null
  }
  const toB = seasonDrape.mix < 0.5
  if (toB) {
    seasonDrape.b = bmp
    seasonDrape.bIdx = i
  } else {
    seasonDrape.a = bmp
    seasonDrape.aIdx = i
  }
  const to = toB ? 1 : 0
  if (fadeMs > 0 && seasonUi.idx >= 0) fade = { from: seasonDrape.mix, to, t0: performance.now(), ms: fadeMs }
  else seasonDrape.mix = to
  const dir = i >= seasonUi.idx ? 1 : -1
  seasonUi.idx = i
  pool?.window(i, dir)
}

/** Show month i (crossfading from the current one). */
export async function seasonGoto(i: number, fadeMs = SEASON_XFADE_MS): Promise<void> {
  if (!pool || !seasonUi.manifest) return
  const n = seasonUi.manifest.frames.length
  i = Math.max(0, Math.min(n - 1, i))
  if (i === seasonUi.idx) return
  const my = ++token
  const bmp = await pool.get(i)
  if (my !== token) return
  show(i, bmp, fadeMs)
}

export function seasonPlay(on: boolean): void {
  seasonUi.playing = on
  // The first step after play comes one full month-period later.
  lastStepAt = performance.now()
  if (on) ensureLoop()
}

/** The Introduction is leaving: drop the frames and the recolour. */
export function disposeSeasons(): void {
  if (raf !== null) window.cancelAnimationFrame(raf)
  raf = null
  fade = null
  token += 1
  seasonUi.playing = false
  seasonUi.idx = -1
  pool?.dispose()
  pool = null
  warmPromise = null
  seasonDrape.on = 0
  seasonDrape.view = 0
  seasonDrape.trails = 1
  // The Globe keeps what it uploaded (cheap to keep, instant next time);
  // only the references to the bitmaps it no longer needs are dropped.
  seasonDrape.a = seasonDrape.b = null
  seasonDrape.aIdx = seasonDrape.bIdx = -1
  seasonDrape.mix = 0
}
