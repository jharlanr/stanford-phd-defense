<template>
  <!-- Additional Work → Chapter 2's deeper dive → APS DFD 2026. The
       conference presentation as a page of the site: the flash slide
       (beat 0) and the interactive ePoster (beats 1–8), a flat opaque
       layer above the live globe like the other door pages. The site's
       NEXT / BACK (and the presenter remote) step the beats — and, inside
       the beats that have them (config/dfd.ts DFD_SUBSTEPS), the steps:
       the field's landed map then its three clips, the problem's five
       stations, the collapse's two views — one deterministic path, BACK
       retracing it. `?beat=N&s=M` deep-links. The beats and the title
       block live in config/dfd.ts. Figure labels only — the presenter
       narrates (the one exception: the PHYSICAL INTUITION labels, the
       director's ask). -->
  <div class="dfd-root" :class="{ 'dfd-print': print }">
    <!-- the page's own rail: one word per beat, click = jump -->
    <nav v-if="!print" class="dfd-rail" aria-label="DFD beats">
      <button class="dfd-exit" @click="emit('exit')">← deeper dive</button>
      <div class="dfd-words">
        <button
          v-for="(id, i) in DFD_BEAT_IDS"
          :key="id"
          class="dfd-word"
          :class="{ 'dfd-word-on': i === beat }"
          :aria-current="i === beat ? 'step' : undefined"
          @click="go(i)"
        >
          {{ DFD_BEAT_LABELS[id] }}
        </button>
      </div>
    </nav>

    <!-- the field: the Introduction's fieldwork map, exactly — its intro
         mode (the plain 2023 crop, the three tracks, the clip panel),
         landed; steps 1–3 cue the Introduction's three GoPro clips, as the
         Introduction's steps 3–5 do. Mounted on the first visit and KEPT
         (hidden) for the page's life: tearing it down after a clip had
         played stalled the next beat's first frame by ~2 s (seen in the
         headless walk) — the Introduction pre-mounts it the same way. -->
    <div v-if="fieldSeen" class="dfd-fieldwrap" :class="{ 'dfd-fieldwrap-hidden': fieldHidden }">
      <FieldworkExplorer mode="intro" :initial-view="null" :revealed="true" :clip="fieldClip" />
    </div>
    <!-- the page's own ground over the kept map while another beat is up.
         The map itself is never touched AT a hand-off (hiding it then, by
         display or by opacity, cost the same stalled frame); it goes
         visibility-hidden a moment later, once the next beat has painted,
         so its 5000 × 3000 basemap is not re-rasterised under the cover. -->
    <div v-if="fieldSeen && beatId !== 'field'" class="dfd-cover" />

    <Transition name="dfd-fade" mode="out-in">
      <div :key="beatId" class="dfd-beat" :class="`dfd-beat-${beatId}`">
        <DfdSlide v-if="beatId === 'slide'" />

        <!-- the field beat's own layer is the kept map above -->
        <div v-else-if="beatId === 'field'" />

        <!-- the problem: lake 2394 in time, station by station -->
        <DfdProblem v-else-if="beatId === 'problem'" :step="sub" @step="setSub" />

        <DfdModel v-else-if="beatId === 'model'" />
        <DfdSolutions v-else-if="beatId === 'solutions'" />
        <DfdLab v-else-if="beatId === 'lab'" />
        <DfdValidity v-else-if="beatId === 'stokes'" />

        <!-- the collapse: the paper's Fig. 3 C–D re-drawn live from the sweep -->
        <DfdCollapse v-else-if="beatId === 'collapse'" :step="sub" @step="setSub" />

        <!-- the takeaway -->
        <div v-else class="dfd-take">
          <div class="dfd-take-card">
            <p class="dfd-take-k">APS DFD 2026 · takeaway</p>
            <!-- trusted static HTML (the subscript) --><p class="dfd-take-line" v-html="DFD_TAKEAWAY" />
            <div class="dfd-take-eq"><DfdEq name="scales" :k="2.4" :inline="false" /></div>
          </div>
          <p class="dfd-take-paper">{{ DFD_PAPER_LINE }}</p>
          <p class="dfd-take-fund">{{ DFD_FUNDING }}</p>
          <p class="dfd-take-url">{{ DFD_SITE_URL }}</p>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DfdSlide from '../DfdSlide.vue'
import DfdProblem from '../DfdProblem.vue'
import DfdModel from '../DfdModel.vue'
import DfdSolutions from '../DfdSolutions.vue'
import DfdLab from '../DfdLab.vue'
import DfdValidity from '../DfdValidity.vue'
import DfdCollapse from '../DfdCollapse.vue'
import DfdEq from '../DfdEq.vue'
import FieldworkExplorer from '../FieldworkExplorer.vue'
import {
  DFD_BEATS,
  DFD_BEAT_IDS,
  DFD_BEAT_LABELS,
  DFD_FUNDING,
  DFD_PAPER_LINE,
  DFD_SITE_URL,
  DFD_TAKEAWAY,
  dfdSteps,
} from '../../config/dfd'
import { FW_INTRO_CLIP_IDS } from '../../config/fieldwork'

const props = defineProps<{
  /** The site's NEXT / BACK (and the presenter remote), while this page
   *  says it has a step for them (`nav-state`). */
  advanceTrigger?: number
  backTrigger?: number
}>()
const emit = defineEmits<{
  'nav-state': [{ next: boolean; back: boolean }]
  exit: []
}>()

const route = useRoute()
const router = useRouter()

function parseBeat(v: unknown): number {
  const n = typeof v === 'string' ? parseInt(v, 10) : NaN
  return Number.isFinite(n) ? Math.min(DFD_BEATS - 1, Math.max(0, n)) : 0
}
function parseSub(v: unknown, b: number): number {
  const n = typeof v === 'string' ? parseInt(v, 10) : NaN
  return Number.isFinite(n) ? Math.min(dfdSteps(DFD_BEAT_IDS[b]) - 1, Math.max(0, n)) : 0
}
const beat = ref(parseBeat(route.query.beat))
const sub = ref(parseSub(route.query.s, beat.value))
const beatId = computed(() => DFD_BEAT_IDS[beat.value])
const steps = computed(() => dfdSteps(beatId.value))
/** `?print=1`: the slide alone, no site chrome (the PDF/PNG export). */
const print = computed(() => route.query.print === '1')

/** Jump to a beat (its first step) or to a step of it. */
function go(b: number, s = 0): void {
  if (b === beat.value && s === sub.value) return
  beat.value = b
  sub.value = s
  const q: Record<string, string | string[] | null> = { ...route.query, beat: String(b) }
  if (s > 0) q.s = String(s)
  else delete q.s
  void router.replace({ query: q })
}
function setSub(s: number): void {
  go(beat.value, Math.min(steps.value - 1, Math.max(0, s)))
}
watch(
  () => [route.query.beat, route.query.s] as const,
  ([qb, qs]) => {
    const b = parseBeat(qb)
    const s = parseSub(qs, b)
    if (b !== beat.value) beat.value = b
    if (s !== sub.value) sub.value = s
  },
)

const navState = computed(() => ({
  next: beat.value < DFD_BEATS - 1 || sub.value < steps.value - 1,
  back: beat.value > 0 || sub.value > 0,
}))
watch(navState, (s) => emit('nav-state', s), { immediate: true })
watch(
  () => props.advanceTrigger,
  (v, old) => {
    if (v == null || v === old) return
    if (sub.value < steps.value - 1) go(beat.value, sub.value + 1)
    else if (beat.value < DFD_BEATS - 1) go(beat.value + 1, 0)
  },
)
watch(
  () => props.backTrigger,
  (v, old) => {
    if (v == null || v === old) return
    if (sub.value > 0) go(beat.value, sub.value - 1)
    else if (beat.value > 0) go(beat.value - 1, dfdSteps(DFD_BEAT_IDS[beat.value - 1]) - 1)
  },
)

/** The field's clip: none on the landed map, then the Introduction's three. */
const fieldClip = computed<string | null>(() => (beatId.value === 'field' && sub.value > 0 ? FW_INTRO_CLIP_IDS[sub.value - 1] ?? null : null))
/** The map mounts on the field beat's first visit and stays (see the template);
 *  off the field beat it is hidden a beat later, under the cover. */
const fieldSeen = ref(beatId.value === 'field')
const fieldHidden = ref(false)
let hideTimer: number | null = null
watch(
  beatId,
  (id) => {
    if (hideTimer !== null) {
      window.clearTimeout(hideTimer)
      hideTimer = null
    }
    if (id === 'field') {
      fieldSeen.value = true
      fieldHidden.value = false
    } else if (fieldSeen.value) {
      hideTimer = window.setTimeout(() => {
        hideTimer = null
        if (beatId.value !== 'field') fieldHidden.value = true
      }, 1200)
    }
  },
  { immediate: true },
)

// the print mode hides the site's chrome (ribbon + pills) through a body class
onMounted(() => {
  if (print.value) document.body.classList.add('dfd-print-body')
})
onBeforeUnmount(() => {
  if (hideTimer !== null) window.clearTimeout(hideTimer)
  document.body.classList.remove('dfd-print-body')
  emit('nav-state', { next: false, back: false })
})
</script>

<style>
/* the export: no ribbon, no pills (global — the chrome is Explore's) */
body.dfd-print-body .top-nav,
body.dfd-print-body .beat-nav {
  display: none !important;
}
</style>

<style scoped>
.dfd-root {
  position: fixed;
  inset: 0;
  z-index: 1;
  overflow: hidden;
  background: radial-gradient(ellipse at 30% 12%, #0e1118 0%, #050505 60%);
  color: #f5f0e6;
  font-family: 'Inter', system-ui, sans-serif;
  pointer-events: auto;
  --dfd-top: calc(1.2vh + var(--nav-h, 2.92rem) + 1rem);
  --dfd-rail-h: 2.4rem;
}
.dfd-print {
  --dfd-top: 2vh;
  --dfd-rail-h: 0px;
}

/* ── the rail under the ribbon ── */
.dfd-rail {
  position: absolute;
  top: var(--dfd-top);
  left: 2vw;
  right: 2vw;
  height: var(--dfd-rail-h);
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  z-index: 5;
}
.dfd-rail::after { content: ''; }
.dfd-exit {
  justify-self: start;
  border: 1px solid var(--gold-dim);
  background: rgba(8, 6, 4, 0.78);
  color: var(--gold-dim);
  font: 500 0.76rem/1 'Inter', system-ui, sans-serif;
  letter-spacing: 0.06em;
  padding: 0.45rem 0.9rem;
  border-radius: 999px;
  cursor: pointer;
}
.dfd-exit:hover { color: var(--gold-bright); }
.dfd-words {
  display: flex;
  gap: 0.2rem;
  padding: 0.2rem 0.5rem;
  border-radius: 999px;
  background: rgba(8, 6, 4, 0.6);
  border: 1px solid rgba(232, 185, 74, 0.18);
}
.dfd-word {
  border: 0;
  background: transparent;
  color: rgba(245, 240, 230, 0.6);
  font: 500 0.8rem/1 'Inter', system-ui, sans-serif;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 0.45rem 0.7rem;
  border-radius: 999px;
  cursor: pointer;
}
.dfd-word:hover { color: var(--gold-bright); }
.dfd-word-on { color: #1c1305; background: var(--gold); }

/* ── the beat area ── */
.dfd-beat {
  position: absolute;
  left: 2vw;
  right: 2vw;
  top: calc(var(--dfd-top) + var(--dfd-rail-h) + 1vh);
  bottom: 1.6vh;
}
.dfd-beat-field { inset: 0; pointer-events: none; }
/* the kept map: the explorer is a fixed full-screen layer of its own */
.dfd-fieldwrap { position: fixed; inset: 0; z-index: 0; }
.dfd-fieldwrap-hidden { visibility: hidden; }
.dfd-cover {
  position: fixed;
  inset: 0;
  z-index: 0;
  background: radial-gradient(ellipse at 30% 12%, #0e1118 0%, #050505 60%);
}
.dfd-beat-slide { left: 1vw; right: 1vw; }
.dfd-fade-enter-active, .dfd-fade-leave-active { transition: opacity 0.3s; }
.dfd-fade-enter-from, .dfd-fade-leave-to { opacity: 0; }

/* the takeaway */
.dfd-take {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1.4vh;
  text-align: center;
}
.dfd-take-card {
  max-width: min(64rem, 84vw);
  padding: 2.4rem 3rem 2rem;
  border: 2px solid var(--gold);
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(30, 24, 12, 0.985), rgba(10, 8, 5, 0.985));
  box-shadow: 0 14px 40px rgba(0, 0, 0, 0.8), 0 0 40px rgba(244, 207, 106, 0.12);
}
.dfd-take-k { margin: 0 0 0.8rem; color: var(--gold); font-size: 0.8rem; letter-spacing: 0.16em; text-transform: uppercase; }
.dfd-take-line {
  margin: 0;
  font-family: 'EB Garamond', Georgia, serif;
  font-weight: 600;
  font-size: clamp(1.4rem, 2.2vw, 2.4rem);
  line-height: 1.3;
  color: #fff8e6;
  text-wrap: balance;
}
.dfd-take-eq { margin-top: 1.4rem; display: flex; justify-content: center; }
.dfd-take-paper { margin: 0.6rem 0 0; color: var(--gold-dim); font-size: 0.95rem; }
.dfd-take-fund { margin: 0; max-width: 70vw; font-size: 0.8rem; color: rgba(245, 240, 230, 0.6); }
.dfd-take-url { margin: 0; font-size: 0.85rem; color: rgba(245, 240, 230, 0.7); letter-spacing: 0.03em; }
</style>
