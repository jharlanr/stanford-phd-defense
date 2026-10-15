<template>
  <!-- The Conclusion is one page — the
       implications of the work as the main takeaways, one per chapter.
       A flat opaque layer ABOVE the globe, which keeps rendering beneath
       it — never a veil. The presenter narrates over
       it; the bullets are the figure, so they stay short.

       A beat page (the director wanted a NEXT path through the
       conclusions that steps through each chapter's takeaway by making
       its text pop out — larger and bolder, as if coming out at the
       audience a little): step 0 = the page at rest; steps 1–3 =
       that chapter's takeaway pops out (larger, bolder, lifted on a soft
       shadow, its number and eyebrow lit gold) while the other two step
       back a touch — still fully legible. Only the takeaways column
       moves; the figure keeps playing (it is never re-keyed). -->
  <div class="cn">
    <div class="cn-inner">
      <header class="cn-head">
        <h2 class="cn-title">Conclusion</h2>
      </header>

      <div class="cn-grid">
        <ol class="cn-list">
          <li
            v-for="(t, i) in TAKEAWAYS"
            :key="t.chapter"
            class="cn-item"
            :class="{ 'is-pop': step === i + 1, 'is-back': step > 0 && step !== i + 1 }"
            :style="{ '--body-h': bodyH[i] + 'px' }"
            @click="goStep(i + 1)"
          >
            <span class="cn-num">{{ i + 1 }}</span>
            <div class="cn-body" :ref="(el) => setBody(i, el)">
              <span class="cn-chapter">{{ t.chapter }}</span>
              <p class="cn-point">{{ t.point }}</p>
            </div>
          </li>
        </ol>

        <!-- The figure — the 2019
             season plays and each lake drains on its observed day (a
             gold flash, then a fainter gold), a strip of the season's drainages under
             the map, the counts, an HF | HF + MD toggle; no circles, no
             reach (ConclusionReach.vue; the menu card plays the same
             renderer, HF only). Labels only, no prose. -->
        <figure class="cn-figure" aria-label="The 2019 lake drainages, each on its observed day">
          <ConclusionReach mode="page" />
        </figure>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { ComponentPublicInstance } from 'vue'
import { useRoute } from 'vue-router'
import ConclusionReach from '../ConclusionReach.vue'
import { parseBeatParam } from '../../config/sitePath'
import { TAKEAWAYS } from '../../config/takeaways'

// Next/back are the site's shared pills (Explore's .beat-nav,
// config/sitePath.ts) — no page-level next. A beat page like the
// Acknowledgements: the pills bump advanceTrigger / backTrigger, one step
// per bump; the last step's next emits `advance` (on to the
// Acknowledgements), step 0's back is Explore's (Chapter 3's last beat).
// `?beat=N` deep links; `?beat=last` is what BACK from the
// Acknowledgements asks for.
const props = defineProps<{
  advanceTrigger?: number
  backTrigger?: number
}>()
const emit = defineEmits<{
  'beat-change': [value: number, isLast: boolean]
  advance: []
}>()
const route = useRoute()

// The three takeaways, one per chapter, are worded in
// config/takeaways.ts — the same lines each chapter's Implications slide
// closes on.

/** 0 = at rest, k = takeaway k pops out. */
const STEPS = TAKEAWAYS.length + 1
const step = ref(0)

// The pop is a TRANSFORM, not a font-size change (the director objected
// to the text re-wrapping as it popped out — it read as
// unclean): the body scales as one block, so its line breaks never move.
// A transform takes no layout room, so each body's natural height is
// measured and the row pads itself by the scale's extra (POP_SCALE − 1)
// while popped — the card and the rule below follow the grown text.
const bodyEls: (HTMLElement | null)[] = []
const bodyH = ref<number[]>(TAKEAWAYS.map(() => 0))
let ro: ResizeObserver | null = null
function setBody(i: number, el: Element | ComponentPublicInstance | null): void {
  const node = el instanceof HTMLElement ? el : null
  if (bodyEls[i] === node) return
  if (bodyEls[i] && ro) ro.unobserve(bodyEls[i]!)
  bodyEls[i] = node
  if (node && ro) ro.observe(node)
}
function measure(): void {
  bodyH.value = bodyEls.map((el) => (el ? el.offsetHeight : 0))
}
function report(): void {
  emit('beat-change', step.value, step.value === STEPS - 1)
}
function next(): void {
  if (step.value >= STEPS - 1) {
    emit('advance')
    return
  }
  step.value += 1
  report()
}
function prev(): void {
  if (step.value <= 0) return
  step.value -= 1
  report()
}
/** A takeaway clicked: pop it (or, if it is already out, back to rest). */
function goStep(k: number): void {
  step.value = step.value === k ? 0 : k
  report()
}
watch(() => props.advanceTrigger, (v, old) => {
  if (v != null && v !== old) next()
})
watch(() => props.backTrigger, (v, old) => {
  if (v != null && v !== old) prev()
})
onMounted(() => {
  ro = new ResizeObserver(measure)
  for (const el of bodyEls) if (el) ro.observe(el)
  measure()
  // EB Garamond may still be loading — re-measure once it is in
  document.fonts?.ready.then(measure)
  step.value = parseBeatParam(route.query.beat, STEPS)
  report()
})
onBeforeUnmount(() => ro?.disconnect())
</script>

<style scoped>
.cn {
  position: fixed;
  inset: 0;
  z-index: 1;
  overflow-y: auto;
  background: radial-gradient(ellipse at 50% 0%, #0f1420 0%, #050505 60%);
  color: #f5f5f5;
  font-family: 'Inter', system-ui, sans-serif;
  padding: 8vh 3vw 3vh;
  box-sizing: border-box;
  pointer-events: auto;
}

/* The takeaways keep the left ~45 %, the figure fills the
   right; the whole page is still one screen (title + grid = the
   viewport's height, the figure takes what is left). */
.cn-inner {
  max-width: 1500px;
  height: 100%;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
}

.cn-head {
  text-align: center;
  margin-bottom: 2rem;
  flex-shrink: 0;
}

.cn-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 45fr) minmax(0, 55fr);
  column-gap: 3vw;
  align-items: center;
}

.cn-figure {
  position: relative;
  margin: 0;
  height: 100%;
  min-height: 0;
}

.cn-title {
  font-family: 'EB Garamond', serif;
  font-weight: 400;
  font-size: 2.4rem;
  color: var(--gold);
  margin: 0;
  letter-spacing: 0.02em;
}


.cn-list {
  list-style: none;
  margin: 0;
  padding: 0;
  border-top: 1px solid rgba(232, 185, 74, 0.35);
}

.cn-item {
  position: relative;
  display: flex;
  align-items: baseline;
  gap: 1.6rem;
  padding: 1.5rem 0.5rem;
  border-bottom: 1px solid rgba(232, 185, 74, 0.35);
  cursor: pointer;
}

/* ── the steps ────────────────────────────────────────────────────────
   The popped takeaway's body SCALES as one block from its top-left
   (--pop 1.2) — never a font-size change, so its wrapping never moves
   (a font-size change re-wrapped the text mid-pop, which the director
   found unclean); at rest the body is capped at 76 % of the row
   so the scaled block still fits the column (+ a little of the grid gap).
   Its ink thickens with a text-stroke (glyph advances unchanged — a
   weight change would re-wrap too) and goes white over a dark shadow;
   the row pads itself by the scale's extra height (--body-h, measured).
   Behind it a card lifts on a soft dark shadow — as if the takeaway
   were coming out at the audience a little. The others ease back a little
   (scale 0.94) but keep full-strength ink (back-row rule). */
.cn-item {
  --pop: 1.2;
  --back: 0.94;
  transition: padding 500ms cubic-bezier(0.2, 0.8, 0.2, 1);
}
.cn-item.is-pop {
  padding-bottom: calc(1.5rem + (var(--pop) - 1) * var(--body-h, 0px));
}
.cn-item.is-back {
  padding-bottom: calc(1.5rem - (1 - var(--back)) * var(--body-h, 0px));
}
.cn-item::before {
  content: '';
  position: absolute;
  inset: 0 -0.6rem;
  border-radius: 10px;
  background: linear-gradient(100deg, rgba(244, 207, 106, 0.09), rgba(255, 255, 255, 0.025) 60%);
  box-shadow: 0 18px 44px rgba(0, 0, 0, 0.75), 0 0 0 1px rgba(244, 207, 106, 0.28);
  opacity: 0;
  transform: scale(0.97);
  transition: opacity 500ms ease, transform 500ms cubic-bezier(0.2, 0.8, 0.2, 1);
  pointer-events: none;
}
.cn-item.is-pop::before {
  opacity: 1;
  transform: scale(1);
}
.cn-num {
  font-variation-settings: 'wght' 400; /* = font-weight 400; interpolable */
}
.cn-num,
.cn-chapter,
.cn-point {
  position: relative; /* above the lift card */
  transition:
    font-size 500ms cubic-bezier(0.2, 0.8, 0.2, 1),
    font-variation-settings 500ms ease,
    color 500ms ease,
    text-shadow 500ms ease,
    -webkit-text-stroke-width 500ms ease;
}
.cn-item.is-pop .cn-num {
  font-size: 3.4rem;
  font-variation-settings: 'wght' 700;
  color: var(--gold-bright);
  text-shadow: 0 0 22px rgba(244, 207, 106, 0.45), 0 4px 14px rgba(0, 0, 0, 0.9);
}
.cn-item.is-pop .cn-chapter {
  color: var(--gold-bright);
  text-shadow: 0 0 14px rgba(244, 207, 106, 0.35);
}
.cn-item.is-pop .cn-point {
  color: #ffffff;
  -webkit-text-stroke: 0.55px #ffffff;
  text-shadow: 0 6px 18px rgba(0, 0, 0, 0.95), 0 2px 4px rgba(0, 0, 0, 0.8);
}
.cn-item.is-pop .cn-body {
  transform: scale(var(--pop));
}
.cn-item.is-back .cn-point {
  color: #e9e9e9;
}
.cn-item.is-back .cn-body {
  transform: scale(var(--back));
}
.cn-item.is-back .cn-num {
  font-size: 2.3rem;
}

.cn-num {
  font-family: 'EB Garamond', serif;
  font-size: 2.6rem;
  line-height: 1;
  /* was --gold-faint (0.18): invisible on a projector */
  color: rgba(232, 185, 74, 0.72);
  min-width: 2.2rem;
  text-align: right;
  flex-shrink: 0;
}

.cn-body {
  flex: 1;
  min-width: 0;
  max-width: 76%;
  transform-origin: 0 0;
  transition: transform 500ms cubic-bezier(0.2, 0.8, 0.2, 1);
}

.cn-chapter {
  display: block;
  font-size: 0.9rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 0.5rem;
}

.cn-point {
  margin: 0;
  font-family: 'EB Garamond', serif;
  font-size: 1.6rem;
  line-height: 1.3;
  color: #f5f5f5;
  letter-spacing: 0.01em;
  -webkit-text-stroke: 0 #f5f5f5;
}


@media (max-width: 900px) {
  /* narrow: the figure stacks under the takeaways and the page scrolls */
  .cn-inner { height: auto; }
  .cn-grid { display: block; }
  .cn-figure { height: min(92vw, 70vh); margin-top: 1.5rem; }
  .cn-point { font-size: 1.45rem; }
  .cn-num { font-size: 2rem; min-width: 1.6rem; }
  .cn-item { gap: 1rem; padding: 1.5rem 0.25rem; }
  .cn-item { --pop: 1.12; }
  .cn-item.is-pop .cn-num { font-size: 2.6rem; }
  .cn-item.is-back .cn-num { font-size: 1.8rem; }
}
</style>
