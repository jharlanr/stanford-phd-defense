// The network segment's per-stage videos (one frame per day of the
// season), held as blobs so a seek never waits on the network, and a
// latest-wins seeker per video so scrubbing never queues stale frames.
//
// Fetches carry a `cors=1` marker so a CORS fetch never shares an R2
// cache entry with a plain <video> load of the same URL (R2 answers
// no-Origin requests without Vary/ACAO — see the fieldwork crop in
// SectionMotivation). A failed fetch falls back to the plain URL.

import { EPOCH_INDEX_FILE, netEpochUrlOf, netUrl, netUrlOf, type Taxonomy, type VideoStage } from './essdNetwork'

/** What a pool needs of a manifest (the DAY one or the EPOCH one). */
export interface PoolSource {
  lake: string
  fps: number
  stages: Record<string, VideoStage>
}
type UrlOf = (file: string) => string

const blobCache = new Map<string, Promise<string>>()

function corsUrl(u: string): string {
  return u + (u.includes('?') ? '&' : '?') + 'cors=1'
}

/** Blob URL for a baked file (cached for the page's life). */
export function netBlob(file: string, urlOf: UrlOf = netUrl): Promise<string> {
  const direct = urlOf(file)
  let p = blobCache.get(direct)
  if (!p) {
    p = fetch(corsUrl(direct))
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status}`)
        return r.blob()
      })
      .then((b) => URL.createObjectURL(b))
      .catch((e) => {
        console.warn(`[network] fetch ${file} failed (${e}); using the direct URL`)
        blobCache.delete(direct)
        return direct
      })
    blobCache.set(direct, p)
  }
  return p
}

/** Warm every video of a lake (sequentially, so the current lake wins). */
export async function warmLake(man: PoolSource, urlOf: UrlOf = netUrl): Promise<void> {
  for (const s of Object.values(man.stages)) await netBlob(`${man.lake}/${s.file}`, urlOf)
}

// The walkthrough's opening, warmed from the beats before it (SectionCh3
// calls this on the inter-rater beats; EssdNetwork mounts two beats
// later): the lake it opens on, its DAY videos, then its EPOCH set (the
// axis the walk plays on) — 16 + 11 MB that, cold, put the first frames
// 1.2–2.4 s after the press (measured in a performance walk). The same `blobCache`
// above hands the component its blobs, so nothing is fetched twice.
const warmedOpeners = new Set<string>()
export function warmNetworkOpeners(lake: string, taxonomy: Taxonomy = '5c'): void {
  const key = `${taxonomy}/${lake}`
  if (warmedOpeners.has(key)) return
  warmedOpeners.add(key)
  const day = netUrlOf(taxonomy)
  const epoch = netEpochUrlOf(taxonomy)
  const manifest = (u: string): Promise<PoolSource | null> =>
    fetch(u)
      .then((r) => (r.ok ? (r.json() as Promise<PoolSource>) : null))
      .catch(() => null)
  void fetch(day('index.json')).catch(() => {})
  void fetch(epoch(EPOCH_INDEX_FILE)).catch(() => {})
  void manifest(day(`${lake}/manifest.json`))
    .then(async (m) => {
      if (m) await warmLake(m, day)
      const e = await manifest(epoch(`${lake}/manifest.json`))
      if (e) await warmLake(e, epoch)
    })
    .catch(() => {})
}

interface Slot {
  el: HTMLVideoElement
  ready: Promise<void>
  cur: number
  want: number
  seeking: boolean
  waiters: Array<{ day: number; resolve: () => void }>
  watchdog: number | null
}

/** What a figure needs from a pool. */
export interface FramePool {
  frame(key: string, day: number): Promise<HTMLVideoElement | null>
}

export class VideoPool implements FramePool {
  readonly lake: string
  private slots = new Map<string, Slot>()
  private fps: number

  constructor(man: PoolSource, host: HTMLElement, urlOf: UrlOf = netUrl) {
    this.lake = man.lake
    this.fps = man.fps
    for (const [key, s] of Object.entries(man.stages)) {
      const el = document.createElement('video')
      el.muted = true
      el.playsInline = true
      el.preload = 'auto'
      host.appendChild(el)
      const slot: Slot = { el, ready: Promise.resolve(), cur: -1, want: -1, seeking: false, waiters: [], watchdog: null }
      slot.ready = netBlob(`${man.lake}/${s.file}`, urlOf).then(
        (src) =>
          new Promise<void>((resolve) => {
            // Metadata is enough: Chrome stops a paused, unseen video at
            // HAVE_METADATA, and the first seek pulls the frame it needs.
            const done = () => {
              el.removeEventListener('loadedmetadata', done)
              el.removeEventListener('error', done)
              resolve()
            }
            el.addEventListener('loadedmetadata', done)
            el.addEventListener('error', done)
            el.src = src
            el.load()
          }),
      )
      el.addEventListener('seeked', () => this.onSeeked(slot))
      this.slots.set(key, slot)
    }
  }

  /** All videos have data. */
  ready(): Promise<void> {
    return Promise.all([...this.slots.values()].map((s) => s.ready)).then(() => {})
  }

  /** Resolve with the video showing `day` (or the latest day asked for). */
  async frame(key: string, day: number): Promise<HTMLVideoElement | null> {
    const s = this.slots.get(key)
    if (!s) return null
    await s.ready
    if (s.cur === day && !s.seeking) return s.el
    await new Promise<void>((resolve) => {
      s.waiters.push({ day, resolve })
      s.want = day
      if (!s.seeking) this.seek(s)
    })
    return s.el
  }

  private seek(s: Slot): void {
    s.seeking = true
    const target = s.want
    ;(s.el as HTMLVideoElement & { _target?: number })._target = target
    s.el.currentTime = (target + 0.5) / this.fps
    // watchdog: a seek that never reports back is issued again
    if (s.watchdog) clearTimeout(s.watchdog)
    s.watchdog = window.setTimeout(() => {
      s.watchdog = null
      if (s.seeking) this.seek(s)
    }, 1500)
  }

  private onSeeked(s: Slot): void {
    const landed = (s.el as HTMLVideoElement & { _target?: number })._target ?? -1
    // Only OUR seek counts: WebKit also reports a seeked for the implicit
    // seek to 0 on load, which would otherwise pass for this one.
    if (landed < 0 || Math.abs(s.el.currentTime - (landed + 0.5) / this.fps) > 0.5 / this.fps) {
      if (!s.el.seeking && landed >= 0) s.el.currentTime = (landed + 0.5) / this.fps
      return
    }
    if (s.watchdog) {
      clearTimeout(s.watchdog)
      s.watchdog = null
    }
    s.cur = landed
    if (s.want !== landed) {
      this.seek(s) // a newer day was asked for while seeking
      return
    }
    const release = () => {
      s.seeking = false
      const w = s.waiters
      s.waiters = []
      for (const x of w) x.resolve()
    }
    // drawImage needs a decoded frame (HAVE_CURRENT_DATA)
    if (s.el.readyState >= 2) release()
    else {
      const on = () => {
        s.el.removeEventListener('loadeddata', on)
        s.el.removeEventListener('canplay', on)
        release()
      }
      s.el.addEventListener('loadeddata', on)
      s.el.addEventListener('canplay', on)
    }
  }

  destroy(): void {
    for (const s of this.slots.values()) {
      if (s.watchdog) clearTimeout(s.watchdog)
      for (const x of s.waiters) x.resolve()
      s.el.removeAttribute('src')
      s.el.load()
      s.el.remove()
    }
    this.slots.clear()
  }
}
