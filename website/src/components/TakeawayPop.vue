<template>
  <!-- THE TAKEAWAY BEAT (the director's design: on each chapter's final
       NEXT beat everything fades into the background and the chapter's
       main takeaway is highlighted, the card it sits in growing a
       little). Each chapter's last beat (`takeaway` in
       its registry) and the Introduction's last step: the page behind dims
       to ~0.25 under a veil (the page — the Globe included — keeps
       rendering beneath it; never hidden) and the takeaway line grows out
       of where it already sits into a larger, centred, gold-edged card.
       The card SCALES as one block from the line's box (a FLIP), never a
       font-size tween — that re-wraps. BACK shrinks it home again.

       Wording: config/takeaways.ts only (Explore passes the line).
       `source` = the on-page line it grows out of (hidden while the card
       is up, so it never shows twice); `spotlight` = elements that stay
       bright through the dim (the Introduction's highlighted Rines 2026
       card); `place` = where the card rests. The chrome (ribbon, sub-menu,
       BACK/NEXT) sits above the veil and stays live. -->
  <div v-if="mounted" class="tkp-root" :class="{ on: shownOn, instant }" aria-live="polite">
    <!-- The veil: one full-screen dim; with spotlights, the holes are cut
         out of it by an even-odd clip path (one veil, any number of
         holes — a hole per element with its own rounded corners; the
         earlier one-box-per-group with a giant shadow lit the rectangle
         round the Introduction's card + pill, far too strongly). -->
    <div class="tkp-veil" :style="veilStyle" />
    <!-- Takes the page's pointer while the card is up (no hover effects
         or drags behind the dim); the chrome above it stays clickable. -->
    <div class="tkp-catch" />
    <div class="tkp-place" :class="`tkp-place-${place}`">
      <div ref="cardEl" class="tkp-card">
        <p class="tkp-text">{{ text }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    /** Up or down. */
    show: boolean
    /** The takeaway line (config/takeaways.ts). */
    text: string
    /** Grow out of the line on screen (true) or land settled (a deep
     *  link, a BACK onto the beat from the next page). */
    animate?: boolean
    /** CSS selector of the on-page line the card grows out of. */
    source?: string | null
    /** CSS selectors of elements kept bright through the dim; each
     *  group's matches are unioned into one hole, with the first match's
     *  corner radius. One element per group keeps the hole its shape. */
    spotlight?: string[][] | null
    /** Where the card rests: the screen's centre, or the lower band (the
     *  Introduction's timeline holds the middle). */
    place?: 'center' | 'low'
    /** Wait this long before growing (the Introduction's highlight lands
     *  first). */
    delayMs?: number
  }>(),
  { animate: false, source: null, spotlight: null, place: 'center', delayMs: 0 },
)

// The card's face (EB Garamond 600, used nowhere else) is fetched at
// startup, not on the first pop: arriving with it unloaded, the swap's
// re-layout stalled the frames under the first card's growth (filmed,
// /chapter3 25 → 26, a 0.9 s rAF gap).
void document.fonts?.load('600 33px "EB Garamond"').catch(() => {})

const DUR = 600
const EASE = 'cubic-bezier(0.2, 0.8, 0.2, 1)'
const LIFTED = 'takeaway-lifted'

const mounted = ref(false)
/** The veil's state (CSS transition on .on). */
const shownOn = ref(false)
/** Landing settled (no veil fade). */
const instant = ref(false)
const cardEl = ref<HTMLElement | null>(null)
const holes = ref<{ x: number; y: number; w: number; h: number; r: number }[]>([])
/** The veil minus its holes: an even-odd path — a huge outer rectangle
 *  (the veil is fixed, inset 0, so the units are viewport px) and one
 *  rounded rectangle per hole. */
const veilStyle = computed(() => {
  if (!holes.value.length) return {}
  const rr = ({ x, y, w, h, r }: { x: number; y: number; w: number; h: number; r: number }) => {
    const k = Math.min(r, w / 2, h / 2)
    return (
      `M${x + k} ${y}H${x + w - k}A${k} ${k} 0 0 1 ${x + w} ${y + k}V${y + h - k}` +
      `A${k} ${k} 0 0 1 ${x + w - k} ${y + h}H${x + k}A${k} ${k} 0 0 1 ${x} ${y + h - k}` +
      `V${y + k}A${k} ${k} 0 0 1 ${x + k} ${y}Z`
    )
  }
  const d = 'M-99999 -99999H99999V99999H-99999Z' + holes.value.map(rr).join('')
  return { clipPath: `path(evenodd, "${d}")` }
})

let anim: Animation | null = null
let liftedEl: Element | null = null
let delayTimer: number | null = null
let findTimer: number | null = null
let holeRaf: number | null = null
let holeUntil = 0
let seq = 0

/** The visible match of a selector (several instances can be mounted). */
function findVisible(sel: string): HTMLElement | null {
  for (const el of Array.from(document.querySelectorAll<HTMLElement>(sel))) {
    const r = el.getBoundingClientRect()
    if (r.width > 0 && r.height > 0 && shown(el)) return el
  }
  return null
}
/** Not hidden by itself or an ancestor (Ch2Results keeps its pages
 *  mounted and fades the idle ones out). */
function shown(el: HTMLElement): boolean {
  if (getComputedStyle(el).visibility === 'hidden') return false
  for (let e: HTMLElement | null = el; e; e = e.parentElement) {
    const cs = getComputedStyle(e)
    if (cs.display === 'none') return false
    // (the line we lifted ourselves is transparent on purpose)
    if (parseFloat(cs.opacity) < 0.05 && !(e === el && el.classList.contains(LIFTED))) return false
  }
  return true
}

function lift(el: Element | null): void {
  if (liftedEl && liftedEl !== el) liftedEl.classList.remove(LIFTED)
  liftedEl = el
  el?.classList.add(LIFTED)
}
function unlift(): void {
  liftedEl?.classList.remove(LIFTED)
  liftedEl = null
}
/** Hide the source line once it exists (a deep link may land before the
 *  page has mounted it). */
function liftWhenFound(my: number): void {
  if (!props.source) return
  const t0 = performance.now()
  const tryFind = () => {
    findTimer = null
    if (my !== seq) return
    const el = findVisible(props.source!)
    if (el) { lift(el); return }
    if (performance.now() - t0 < 15000) findTimer = window.setTimeout(tryFind, 120)
  }
  tryFind()
}

// ── spotlights ──
function measureHoles(): void {
  const out: { x: number; y: number; w: number; h: number; r: number }[] = []
  for (const group of props.spotlight ?? []) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity
    let radius = 0
    let first = true
    for (const sel of group) {
      for (const el of Array.from(document.querySelectorAll(sel))) {
        const r = el.getBoundingClientRect()
        if (r.width <= 0 || r.height <= 0) continue
        if (first) {
          // the element's own corner, as rendered (its transform's scale
          // is in the rect, so scale the radius by the same ratio)
          const cs = getComputedStyle(el)
          const k = (el as HTMLElement).offsetWidth > 0 ? r.width / (el as HTMLElement).offsetWidth : 1
          radius = (parseFloat(cs.borderTopLeftRadius) || 0) * k
          first = false
        }
        x0 = Math.min(x0, r.left); y0 = Math.min(y0, r.top)
        x1 = Math.max(x1, r.right); y1 = Math.max(y1, r.bottom)
      }
    }
    if (x1 > x0 && y1 > y0) {
      // just past the element's edge: the card's 1.5 px gold ring stays lit
      const PAD = 3
      out.push({ x: x0 - PAD, y: y0 - PAD, w: x1 - x0 + 2 * PAD, h: y1 - y0 + 2 * PAD, r: radius + PAD })
    }
  }
  holes.value = out
}
/** Follow the spotlit elements for a while (they settle with their own
 *  transitions), then on resize only. */
function trackHoles(ms: number): void {
  if (!props.spotlight?.length) { holes.value = []; return }
  holeUntil = performance.now() + ms
  if (holeRaf !== null) return
  const tick = () => {
    measureHoles()
    holeRaf = performance.now() < holeUntil ? requestAnimationFrame(tick) : null
  }
  holeRaf = requestAnimationFrame(tick)
}
function onResize(): void {
  if (!mounted.value) return
  trackHoles(400)
  if (!anim) fitCard()
}
window.addEventListener('resize', onResize)

/** Shrink the card to its text: `text-wrap: balance` evens the lines but
 *  leaves the box at its max width (a wide empty margin round a short
 *  line). Measured untransformed, before any animation. */
function fitCard(): void {
  const card = cardEl.value
  const p = card?.querySelector('.tkp-text')
  if (!card || !p) return
  card.style.width = ''
  const range = document.createRange()
  range.selectNodeContents(p)
  let w = 0
  for (const r of Array.from(range.getClientRects())) w = Math.max(w, r.width)
  if (w <= 0) return
  const cs = getComputedStyle(card)
  const extra =
    parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight) +
    parseFloat(cs.borderLeftWidth) + parseFloat(cs.borderRightWidth)
  card.style.width = `${Math.ceil(w + extra + 2)}px`
}

/** The card's transform that puts it over the source line's box. */
function fromSource(): string | null {
  const card = cardEl.value
  const src = props.source ? findVisible(props.source) : null
  if (!card || !src) return null
  const s = src.getBoundingClientRect()
  // the card's untransformed box (offset* ignore transforms)
  const c = card.getBoundingClientRect()
  if (c.width <= 0 || s.width <= 0) return null
  // The type grows from the line's size to the card's — the scale is the
  // ratio of the two font sizes, not of the boxes (the card sets the
  // line on two balanced lines, narrower than the one-line source).
  const fs = (el: Element) => parseFloat(getComputedStyle(el).fontSize) || 1
  const txt = card.querySelector('.tkp-text')
  const k = txt ? Math.min(1, fs(src) / fs(txt)) : 0.8
  const dx = s.left + s.width / 2 - (c.left + c.width / 2)
  const dy = s.top + s.height / 2 - (c.top + c.height / 2)
  return `translate(${dx}px, ${dy}px) scale(${k})`
}

function clearTimers(): void {
  if (delayTimer !== null) { window.clearTimeout(delayTimer); delayTimer = null }
  if (findTimer !== null) { window.clearTimeout(findTimer); findTimer = null }
}

async function up(animate: boolean): Promise<void> {
  const my = ++seq
  clearTimers()
  anim?.cancel()
  anim = null
  instant.value = !animate
  mounted.value = true
  await nextTick()
  if (my !== seq) return
  fitCard()
  trackHoles(animate ? 2500 + props.delayMs : 1500)
  const go = () => {
    delayTimer = null
    if (my !== seq) return
    const card = cardEl.value
    shownOn.value = true
    if (!animate || !card) {
      liftWhenFound(my)
      return
    }
    const from = fromSource()
    if (from) {
      lift(findVisible(props.source!))
      anim = card.animate(
        [
          { transform: from, opacity: 0 },
          { opacity: 1, offset: 0.3 },
          { transform: 'none', opacity: 1 },
        ],
        { duration: DUR, easing: EASE },
      )
    } else {
      liftWhenFound(my)
      anim = card.animate(
        [
          { transform: 'scale(0.9)', opacity: 0 },
          { transform: 'none', opacity: 1 },
        ],
        { duration: DUR, easing: EASE },
      )
    }
    const mine = anim
    if (mine) mine.onfinish = () => { if (anim === mine) anim = null }
  }
  if (animate && props.delayMs > 0) {
    // the card waits hidden; the veil waits with it
    delayTimer = window.setTimeout(go, props.delayMs)
  } else {
    go()
  }
}

function down(): void {
  const my = ++seq
  clearTimers()
  const card = cardEl.value
  instant.value = false
  shownOn.value = false
  if (!card || !mounted.value) { unlift(); mounted.value = false; return }
  // Shrink home onto the line when it is still on screen (BACK onto the
  // implications beat); otherwise just fade (the page is leaving).
  const to = fromSource()
  const cur = getComputedStyle(card).opacity
  anim?.cancel()
  anim = card.animate(
    to
      ? [{ transform: 'none', opacity: cur }, { opacity: 1, offset: 0.7 }, { transform: to, opacity: 0 }]
      : [{ opacity: cur }, { opacity: 0 }],
    { duration: to ? DUR : 300, easing: EASE, fill: 'forwards' },
  )
  // the line fades back in as the card arrives on it
  window.setTimeout(() => { if (my === seq) unlift() }, to ? DUR * 0.6 : 0)
  anim.onfinish = () => {
    if (my !== seq) return
    anim = null
    mounted.value = false
    holes.value = []
  }
}

watch(
  () => props.show,
  (on) => (on ? void up(props.animate) : down()),
  { immediate: true },
)

onBeforeUnmount(() => {
  seq++
  clearTimers()
  anim?.cancel()
  unlift()
  if (holeRaf !== null) cancelAnimationFrame(holeRaf)
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
/* Above every page layer (the timeline, the twin Greenlands, the flat
   implications pages, the Globe's overlays), BELOW the chrome: the
   ribbon + sub-menu (.top-nav-wrap, 10) and the BACK/NEXT pills (11). */
.tkp-root {
  position: fixed;
  inset: 0;
  z-index: 9;
  pointer-events: none;
}
.tkp-veil {
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: 0;
  transition: opacity 600ms ease;
  /* brightness ≈ 0.25 behind the card; the spotlight holes are cut out
     of it by the inline clip-path (veilStyle) */
  background: rgba(0, 0, 0, 0.75);
}
.tkp-root.on .tkp-veil {
  opacity: 1;
}
.tkp-root.instant .tkp-veil {
  transition: none;
}
.tkp-catch {
  position: fixed;
  inset: 0;
  pointer-events: auto;
}
.tkp-place {
  position: fixed;
  inset: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 0 4vw;
  box-sizing: border-box;
  pointer-events: none;
}
/* The Introduction's timeline holds the middle third (its card row): the
   card rests in the band between the row and the year axis. */
.tkp-place-low {
  align-items: flex-start;
  padding-top: 59vh;
}
.tkp-card {
  max-width: min(60vw, 880px);
  box-sizing: border-box;
  padding: 1.7rem 2.6rem 1.8rem;
  background: linear-gradient(160deg, rgba(30, 24, 12, 0.96), rgba(10, 8, 5, 0.96));
  border: 2px solid var(--gold, #f4cf6a);
  border-radius: 16px;
  box-shadow:
    0 26px 70px rgba(0, 0, 0, 0.85),
    0 0 46px rgba(244, 207, 106, 0.16);
  transform-origin: 50% 50%;
  opacity: 0;
}
.tkp-root.on .tkp-card {
  opacity: 1;
}
.tkp-text {
  margin: 0;
  text-align: center;
  font-family: 'EB Garamond', serif;
  font-size: 2.1rem;
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: 0.01em;
  color: #ffffff;
  text-wrap: balance;
}
</style>

<style>
/* The on-page line the card grew out of — out of sight while the card is
   up (set by TakeawayPop; unscoped because it marks other components'
   elements). */
.takeaway-lifted {
  opacity: 0 !important;
  transition: opacity 220ms ease !important;
}
</style>
