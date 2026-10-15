<template>
  <!-- Chapter 2 · RESULTS + IMPLICATIONS (the director's walk, revised
       twice: first the walk became post σ_t1 → Δσ_t1 → Δσ_t2, elastic then
       viscous, the stress space's x- then y-axis emphasised, only the
       center lake's symbols; the per-lake comparison page is gone — the
       population page follows the teaser. Then the Δσ_t2 step
       left the walk for the Chapter 2 deeper dive — post σ_t1 → Δσ_t1
       per model; the component still draws a σ_t2 space when asked).
       The beats after the drained block (config/ch2Beats.ts):
         3–6  ONE stress space at a time beside the block — elastic σ_t1,
              elastic σ_t2, viscous σ_t1, viscous σ_t2 — only the chosen
              center lake's neighbours (2394 on the deterministic path,
              any lake the visitor zoomed otherwise: same cadence).
         7    the DIFFERENCE fields flat, elastic | viscous, each with its
              σ_t1 stress space beneath. [gone]
         8    the complete σ_t1 stress space (every lake) — VISCOUS ONLY
              (elastic | viscous before; the pair is now the
              deeper dive's #sequence); DIVE DEEPER → that group.
         9    the implications page (the chosen lake's viscous Δσ_t1 field
              + the seven lakes' viscous stress space).
       Every stress space of 3–8 shares ONE fixed ±1000 kPa frame. The
       definitions of its axes (σ_t1, σ_t2, Δσ — PNAS SI Eqs. 52–54) live
       on the Chapter 2 deeper dive (the director found the equations
       cluttered the bottom of the page and moved them off the talk).
       7–9 are one opaque full-screen page ABOVE the still-rendering
       globe (never a veil on it). No prose: figure labels only.
       The page comes TWICE (config/ch2Beats.ts):
       the population after the teaser, then — past the theory's slab
       (Ch2Slab.vue, z 8, under this layer) — the implications; each
       time it dissolves in above what was there (ch2IsFlatPage). -->
  <div class="cr-root">
    <Transition name="cr-fade">
      <div v-if="single && phase" class="cr-single" :style="ssMaxW ? { maxWidth: ssMaxW + 'px' } : undefined">
        <Ch2StressSpace
          :model="single.model"
          :comp="single.comp"
          :emphasis="single.emphasis"
          :field="single.field"
          :points="phase.models[single.model]?.points ?? []"
          :center-num="centerNum"
          :ghost-num="ghostNum"
          :highlight-num="highlightNum"
          labels
          @lake-hover="emit('lake-hover', $event)"
        />
      </div>
    </Transition>

    <Transition name="cr-page">
      <div v-if="flat" class="cr-page">
        <!-- THE POPULATION — viscous only (the director limited the talk's
             Chapter 2 to the viscous model: the elastic model was too
             much to fit into the talk): ONE stress space,
             every center lake's neighbours. The elastic | viscous pair
             this page showed until then is the deeper dive's #sequence
             (Ch2PopulationSpaces.vue). -->
        <div class="cr-cols" :class="{ 'cr-gone': ph === CH2_PHASE.implications }">
          <div class="cr-col">
            <!-- the model's name is in the title: at fs 1.6 the header's
                 "Viscous σ_t1" ran into its englacial · lateral · none key -->
            <div class="cr-title">All lakes · viscous</div>
            <div class="cr-ss">
              <Ch2StressSpace
                v-if="phase"
                model="viscous"
                comp="t1"
                :points="phase.models.viscous?.points ?? []"
                :center-num="centerNum"
                :ghost-num="ghostNum"
                :show-all="ph === CH2_PHASE.population"
                :labels="false"
                :header-model="false"
                :fs="1.6"
                :highlight-num="highlightNum"
                hug-top
                @lake-hover="emit('lake-hover', $event)"
              />
            </div>
          </div>
        </div>

        <!-- the complete stress spaces' center-lake key -->
        <Transition name="cr-fade">
          <div v-if="ph === CH2_PHASE.population" class="cr-centers">
            <!-- every centre lake alike (no gold for the chosen one) -->
            <span v-for="c in centersWithPoints" :key="c" class="cr-center">
              <svg width="24" height="24"><path :d="phaseMarkerPath(PHASE_CENTER_MARKERS[c] ?? 'o', 12, 12, 8.5)" fill="rgba(245,240,230,0.85)" stroke="rgba(0,0,0,0.6)" stroke-width="1" /></svg>
              {{ c }}
            </span>
          </div>
        </Transition>
        <Transition name="cr-fade">
          <!-- the door to the elastic model: the deeper dive's
               first group — the five-station walk + both populations -->
          <MoreDetailsPill
            v-if="ph === CH2_PHASE.population"
            class="cr-deeper"
            label="Elastic & viscous"
            to="/additional-work/deeper/chapter2#sequence"
          />
        </Transition>

        <!-- mounted a beat early (hidden) so its two composites have
             decoded before the fade-in -->
        <Ch2Implications
          v-if="ph >= CH2_PHASE.population && implLake"
          class="cr-impl"
          :class="{ 'cr-impl-hidden': ph !== CH2_PHASE.implications }"
          :lake="implLake"
          :points="phase?.models.viscous?.points ?? []"
          :center-num="centerNum"
          :highlight-num="highlightNum"
          @lake-hover="emit('lake-hover', $event)"
        />
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Ch2StressSpace from './Ch2StressSpace.vue'
import Ch2Implications from './Ch2Implications.vue'
import MoreDetailsPill from './MoreDetailsPill.vue'
import { CH2_PHASE, ch2IsFlatPage, ch2Phase, ch2SingleStep, type Ch2Step } from '../config/ch2Beats'
import { ch2ResultUrl, loadCh2Impl, loadCh2Phase, type Ch2ImplFile } from '../config/ch2Results'
import {
  PHASE_CENTER_MARKERS,
  phaseMarkerPath,
  type PhaseSpaceFile,
} from '../config/simLakes'

const props = defineProps<{
  beat: number
  /** The chosen center lake, e.g. "CW2019_2394". */
  lakeId: string
  centerNum: number
  /** The first center lake's number on the second lake's walk (its
   *  points stay, faint); null elsewhere. */
  ghostNum?: number | null
  highlightNum: number | null
  /** The step the single stress space draws (Explore's ch2Single — the
   *  station on screen, config/ch2State.ts ch2StepShown; null = none, e.g.
   *  an imagery station). Omitted: the beat's own step. */
  step?: Ch2Step | null
}>()
const emit = defineEmits<{ 'lake-hover': [num: number | null] }>()

const phase = ref<PhaseSpaceFile | null>(null)
const impl = ref<Ch2ImplFile | null>(null)
// A busy dev server or a dropped request must not leave the page empty:
// the loaders forget a failure, so retry a few times.
function loadWithRetry<T>(load: () => Promise<T | null>, set: (v: T) => void, tries = 4): void {
  load().then((j) => {
    if (j) set(j)
    else if (tries > 1) window.setTimeout(() => loadWithRetry(load, set, tries - 1), 1500)
  })
}
// The single stress space keeps clear of the block's axis triad (the
// axes stay on the Δσ pages, so the stress space plots move over to
// accommodate them): the column may be no wider than the room
// right of __simDomainScreen.axesBox (+ a gap); the diagram scales down
// inside it (its SVG keeps its aspect).
const ssMaxW = ref(0)
let ssRaf = 0
function ssTick(): void {
  ssRaf = requestAnimationFrame(ssTick)
  const sc = (window as unknown as { __simDomainScreen?: { visible: boolean; axesBox: { maxX: number } | null } | null }).__simDomainScreen
  const W = window.innerWidth
  const right = 0.022 * W
  const on = !!(sc && sc.visible && sc.axesBox)
  // the hop's dip (a lake change, the inset): the block is gone for a
  // moment — the diagram keeps its size instead of swelling and back
  if (!on && (window as unknown as { __ch2Hop?: boolean }).__ch2Hop) return
  const want = on ? Math.max(260, W - right - sc!.axesBox!.maxX - 22) : 0
  if (Math.abs(want - ssMaxW.value) > 1) ssMaxW.value = Math.round(want)
}
onMounted(() => {
  ssRaf = requestAnimationFrame(ssTick)
})
onBeforeUnmount(() => cancelAnimationFrame(ssRaf))

onMounted(() => {
  loadWithRetry(loadCh2Phase, (j) => (phase.value = j))
  loadWithRetry(loadCh2Impl, (j) => (impl.value = j))
})

const ph = computed(() => ch2Phase(props.beat))
const single = computed(() => (props.step !== undefined ? props.step : ch2SingleStep(props.beat)))
const flat = computed(() => ch2IsFlatPage(props.beat))
const implLake = computed(() => impl.value?.lakes[props.lakeId] ?? null)

const centersWithPoints = computed(() => {
  const s = new Set<number>()
  for (const p of phase.value?.models.viscous?.points ?? []) s.add(p.center)
  return [...s].sort((a, b) => a - b)
})

// Warm the implications page's field a few beats early (a plain <img>
// load — the same request mode as the SVG <image> that shows it).
const warmed = new Set<string>()
function warm(url: string): void {
  if (warmed.has(url)) return
  warmed.add(url)
  const im = new Image()
  im.decoding = 'async'
  im.src = url
}
watch(
  () => [props.beat, implLake.value] as const,
  () => {
    const im = implLake.value
    if (im && ph.value >= CH2_PHASE.teaser) warm(ch2ResultUrl(im.models.viscous.image))
  },
  { immediate: true },
)
</script>

<style scoped>
.cr-root {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 9;
  /* the single diagram's column (3–6): its top clears the sub-menu bar
     and the Back/Next pills; its width = the diagram's (Ch2StressSpace
     viewBox 674 × 680 at fs = 1), capped at 46vw */
  /* …and under the block's stations (SimViewControls --svc-bottom: the
     one-row timeline runs above the stress space) */
  --ss-top: max(calc(var(--chrome-bottom, 0px) + 0.9rem), calc(6.2vh + 2.8rem), calc(var(--svc-bottom, 0px) + 0.6rem));
  --ss-w: min(46vw, calc((100vh - var(--ss-top) - 2.5vh) * 674 / 680));
}

/* ── 3–6: one big stress space in the right column, beside the block ── */
.cr-single {
  position: absolute;
  right: 2.2vw;
  top: var(--ss-top);
  bottom: 2.5vh;
  width: var(--ss-w);
  pointer-events: auto;
}

/* ── 7–9: the flat page ── */
.cr-page {
  position: fixed;
  inset: 0;
  background: radial-gradient(ellipse at 50% 0%, #0f1420 0%, #050505 62%);
  pointer-events: auto;
}
.cr-cols {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(var(--chrome-bottom, 7vh) + 0.9vh);
  bottom: 7.5vh; /* the center-lake key's row */
  display: flex;
  justify-content: center;
  align-items: stretch;
  gap: 1.6vw;
  transition: opacity 0.6s ease;
}
.cr-cols.cr-gone {
  opacity: 0;
  pointer-events: none;
}
.cr-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 0 1 44vw;
  min-width: 0;
  min-height: 0;
}
.cr-title {
  font-family: 'EB Garamond', serif;
  font-size: 2.2rem;
  line-height: 1.05;
  color: var(--gold);
  letter-spacing: 0.02em;
  flex: 0 0 auto;
  /* the diagram hugs the top of its slot (Ch2StressSpace `hugTop`) and
     the title closes up onto its key row (the Elastic and Viscous titles
     sit close to their respective stress state
     plots) */
  margin-bottom: -2.2vh;
}
.cr-ss {
  flex: 1 1 0;
  width: 100%;
  min-height: 0;
}

.cr-centers {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 2.6vh;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1.4rem;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1.15rem;
  font-variant-numeric: tabular-nums;
  color: rgba(245, 240, 230, 0.92);
}
.cr-center {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
.cr-deeper {
  position: absolute;
  right: 2vw;
  bottom: 2.4vh;
}
/* lit like the block's pills so it reads from the back row */
.cr-page .cr-deeper {
  font-size: 0.98rem;
  color: var(--gold-bright);
  border: 1.5px solid rgba(232, 185, 74, 0.85);
}

.cr-impl {
  transition: opacity 0.6s ease;
}
.cr-impl-hidden {
  opacity: 0;
  pointer-events: none;
}

.cr-fade-enter-active,
.cr-fade-leave-active {
  transition: opacity 0.5s ease;
}
.cr-fade-enter-from,
.cr-fade-leave-to {
  opacity: 0;
}
.cr-page-enter-active,
.cr-page-leave-active {
  transition: opacity 0.7s ease;
}
.cr-page-enter-from,
.cr-page-leave-to {
  opacity: 0;
}
</style>
