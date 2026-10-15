// The Introduction's "seasons" steps — the hand-off between the page
// (IntroSeasons.vue: the month clock, the frame pool) and the Globe (which
// recolours its speed drape from the frames every render).
//
// Deliberately NOT Vue state: the clock writes `mix` every animation frame
// and the Globe reads it every render — a reactive prop would cost a Vue
// update per frame for nothing (the same reason the fly-along publishes
// window.__fieldworkScreen). The Globe owns the GPU side; this module owns
// decoding.
//
// Frames are ping-ponged between two texture slots: a month step writes the
// NEW month into the slot that is not showing and eases `mix` towards it, so
// exactly one texture upload happens per month.

import { seasonsUrl, type SeasonFrame } from '../config/seasons'

export interface SeasonDrapeState {
  /** Target recolour amount 0..1 (0 = the plain "Greenland flows" drape). */
  on: number
  /** Target view 0 = speed, 1 = anomaly (the Globe eases between them). */
  view: number
  /** Target multiplier on the comet trails' opacity. */
  trails: number
  /** The two month slots and which frame index each holds (−1 = none). */
  a: ImageBitmap | null
  aIdx: number
  b: ImageBitmap | null
  bIdx: number
  /** 0 = slot a showing, 1 = slot b (written by the clock, eased there). */
  mix: number
  /** The drape's own log-speed fraction (greyscale, 8192 × 3152). */
  staticT: ImageBitmap | null
  /** Anomaly colour stops from the manifest ([fraction, '#rrggbb']). */
  anomStops: [number, string][] | null
  anomLim: number
  /** Decades per R byte and the anomaly fade (m/yr) — from the manifest. */
  deltaScale: number
  anomFade: [number, number]
  anomGrey: number
  /** Measured by the Globe: per-upload ms (last, max, count). */
  stats: { lastUploadMs: number; maxUploadMs: number; uploads: number; staticUploadMs: number }
}

export const seasonDrape: SeasonDrapeState = {
  on: 0,
  view: 0,
  trails: 1,
  a: null,
  aIdx: -1,
  b: null,
  bIdx: -1,
  mix: 0,
  staticT: null,
  anomStops: null,
  anomLim: 50,
  deltaScale: 256,
  anomFade: [15, 40],
  anomGrey: 0.3,
  stats: { lastUploadMs: 0, maxUploadMs: 0, uploads: 0, staticUploadMs: 0 },
}
;(window as any).__seasonDrape = seasonDrape

// Data textures: no colour management, no premultiply, flipped the way
// WebGL's UNPACK_FLIP_Y would (three ignores flipY for ImageBitmaps).
const BITMAP_OPTS: ImageBitmapOptions = {
  imageOrientation: 'flipY',
  premultiplyAlpha: 'none',
  colorSpaceConversion: 'none',
}

async function fetchBlob(url: string): Promise<Blob> {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`HTTP ${r.status} ${url}`)
  return r.blob()
}

let staticPromise: Promise<void> | null = null
/** Fetch + decode the static t texture once (off the main thread). */
export function loadSeasonStatic(file: string): Promise<void> {
  if (!staticPromise) {
    staticPromise = (async () => {
      let blob: Blob
      try {
        blob = await fetchBlob(seasonsUrl(file))
      } catch (e) {
        console.warn('[seasons] static t fetch failed, retrying once:', e)
        await new Promise((res) => window.setTimeout(res, 1200))
        blob = await fetchBlob(seasonsUrl(file))
      }
      seasonDrape.staticT = await createImageBitmap(blob, BITMAP_OPTS)
    })()
    staticPromise.catch((e) => {
      console.warn('[seasons] static t unavailable:', e)
      staticPromise = null
    })
  }
  return staticPromise
}

/**
 * The frames: every month's compressed bytes are fetched once (a few
 * hundred kB each, four at a time, starting from the month the page opens
 * on), and a small window of them is kept DECODED as ImageBitmaps around
 * the clock — decoded off the main thread by createImageBitmap, ahead of
 * the clock in the direction it runs. A decoded 2600 × 1000-class bitmap
 * is ~6–10 MB, so the window stays small.
 */
export class SeasonFramePool {
  private blobs: (Promise<Blob> | null)[]
  private bitmaps = new Map<number, Promise<ImageBitmap>>()
  private done = new Map<number, ImageBitmap>()
  private queue: number[] = []
  private inflight = 0
  private disposed = false

  constructor(private frames: SeasonFrame[], private keepBehind = 3, private keepAhead = 10) {
    this.blobs = frames.map(() => null)
  }

  /** Queue every frame's download, nearest-first from `from` (forward first). */
  fetchAll(from: number): void {
    const n = this.frames.length
    const order: number[] = []
    for (let k = 0; k < n; k++) {
      const f = from + k
      if (f < n) order.push(f)
      const b = from - 1 - Math.floor(k / 3)
      if (k % 3 === 2 && b >= 0 && !order.includes(b)) order.push(b)
    }
    for (let i = 0; i < n; i++) if (!order.includes(i)) order.push(i)
    this.queue = order.filter((i) => this.blobs[i] === null)
    this.pump()
  }

  private pump(): void {
    while (!this.disposed && this.inflight < 4 && this.queue.length) {
      const i = this.queue.shift()!
      if (this.blobs[i]) continue
      this.blob(i)
    }
  }

  private blob(i: number): Promise<Blob> {
    let p = this.blobs[i]
    if (!p) {
      this.inflight += 1
      const url = seasonsUrl(this.frames[i].file)
      p = fetchBlob(url)
        .catch(() => new Promise<void>((res) => window.setTimeout(res, 800)).then(() => fetchBlob(url)))
        .finally(() => {
          this.inflight -= 1
          this.pump()
        })
      p.catch(() => {
        this.blobs[i] = null
      })
      this.blobs[i] = p
    }
    return p
  }

  /** The decoded frame i (decoding it now if it is not in the window). */
  get(i: number): Promise<ImageBitmap> {
    let p = this.bitmaps.get(i)
    if (!p) {
      p = this.blob(i).then((b) => createImageBitmap(b, BITMAP_OPTS))
      p.then(
        (bmp) => {
          if (this.disposed || !this.bitmaps.has(i)) bmp.close()
          else this.done.set(i, bmp)
        },
        () => this.bitmaps.delete(i),
      )
      this.bitmaps.set(i, p)
    }
    return p
  }

  /** Decoded already? (the clock only steps onto ready frames while playing) */
  ready(i: number): boolean {
    return this.done.has(i)
  }

  /** Keep the window around `cur` (dir = +1 playing forward) and drop the rest. */
  window(cur: number, dir: 1 | -1 = 1): void {
    const n = this.frames.length
    const lo = dir > 0 ? cur - this.keepBehind : cur - this.keepAhead
    const hi = dir > 0 ? cur + this.keepAhead : cur + this.keepBehind
    for (let i = Math.max(0, lo); i <= Math.min(n - 1, hi); i++) this.get(i)
    for (const [i, bmp] of this.done) {
      if (i < lo || i > hi) {
        // Never close a bitmap a texture slot still holds (the Globe may
        // not have uploaded it yet).
        if (seasonDrape.a === bmp || seasonDrape.b === bmp) continue
        bmp.close()
        this.done.delete(i)
        this.bitmaps.delete(i)
      }
    }
  }

  dispose(): void {
    this.disposed = true
    this.queue = []
    for (const [, bmp] of this.done) {
      if (seasonDrape.a === bmp || seasonDrape.b === bmp) continue
      bmp.close()
    }
    this.done.clear()
    this.bitmaps.clear()
  }
}
