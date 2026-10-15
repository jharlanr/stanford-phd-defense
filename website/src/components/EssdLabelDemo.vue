<template>
  <!-- Ch.3 beat 2 (the director wanted a moment where a label is made
       together, live) — the labeling procedure on one example lake, the
       way lakelabel (sat-tile-stack's Flask GUI) frames it: the lake's
       Sentinel-2 season to scrub through, its daily water fraction, and
       soft probabilities across the five classes. Nothing is saved.
       Committing reveals the published label. The season is the full
       153 days. The movie is the VALID-frame bake
       (ch03/lakes_valid/, build_callout_movies.py): days with no Sentinel-2
       acquisition are simply not frames (the director wanted no black tiles), while the
       p_water curve below stays on the full daily axis.
       At the director's request the sliders snap to quarters with
       ticks, as lakelabel's do, and wear their class colours in every
       engine (they are drawn here, not left to accent-color: Chromium
       gives a DARK accent colour a white unfilled track — ND and CD); the
       water curve is blue; the play/pause glyph is geometry.
       Later the season player and the sliders moved, as
       they were, into LakeSeason.vue and SoftSliders.vue, which the "Label
       lakes yourself" door (/additional-work/label) shares. -->

  <div class="ld-root">
    <div class="ld-stage">
      <div class="ld-left">
        <div class="ld-id">{{ lakeId }}</div>
        <LakeSeason :src="src" :sidecar="sidecar" />
      </div>

      <div class="ld-right">
        <SoftSliders v-model="raw" :disabled="committed" />

        <div class="ld-actions">
          <!-- as in lakelabel, a label commits only when the five sum to 1 -->
          <button class="ld-commit" :disabled="committed || total !== 100" @click="commit">
            Commit label
          </button>
          <button class="ld-reset" @click="reset">↺</button>
        </div>

        <!-- after the commit: the published label for this lake -->
        <div v-if="committed" class="ld-reveal">
          <div class="ld-reveal-row">
            <span class="ld-reveal-k">published label</span>
            <span class="ld-reveal-v" :style="{ color: colorOf(published.label) }">
              {{ published.label }} · {{ nameOf(published.label) }}
            </span>
          </div>
          <div class="ld-bar ld-bar-pub">
            <span
              v-for="c in CLASSES"
              :key="`p-${c.code}`"
              class="ld-bar-seg"
              :style="{ width: (published.p[c.code] * 100) + '%', background: c.color }"
            />
          </div>
          <div class="ld-reveal-row">
            <span class="ld-reveal-k">yours</span>
            <span class="ld-reveal-v" :style="{ color: colorOf(argmax) }">
              {{ argmax }} · {{ nameOf(argmax) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { mediaUrl } from '../config/media'
import LakeSeason, { type SeasonSidecar } from './LakeSeason.vue'
import SoftSliders from './SoftSliders.vue'
import { classColor as colorOf, className as nameOf, emptySoft, softArgmax, ESSD_CLASSES as CLASSES } from '../config/essdLabel'

const props = defineProps<{ lakeId: string }>()

// The published label for the demo lake — labels_CW_2019.csv row 326:
// CW2019_1848, MD, p = [0, 0, 1, 0, 0]. (Not in the IRR-200, so there is
// no three-expert row to compare against — the published label it is.)
const PUBLISHED: Record<string, { label: string; p: Record<string, number> }> = {
  CW2019_1848: { label: 'MD', p: { ND: 0, HF: 0, MD: 1, LD: 0, CD: 0 } },
}
const published = computed(() => PUBLISHED[props.lakeId] ?? { label: '—', p: { ND: 0, HF: 0, MD: 0, LD: 0, CD: 0 } })

// ── the soft label (the sliders + their rules: SoftSliders.vue,
// config/essdLabel.ts) ─────────────────────────────────────────────────
const raw = ref(emptySoft())
const committed = ref(false)
const total = computed(() => CLASSES.reduce((a, c) => a + raw.value[c.code], 0))
const argmax = computed(() => softArgmax(CLASSES.map((c) => raw.value[c.code])))
function commit(): void {
  committed.value = true
}
function reset(): void {
  committed.value = false
  raw.value = emptySoft()
}

// ── the season (the movie + its water curve: LakeSeason.vue) ─────────
const src = computed(() => mediaUrl(`ch03/lakes_valid/${props.lakeId}.mp4`))
const sidecar = ref<SeasonSidecar | null>(null)

onMounted(async () => {
  try {
    const r = await fetch(mediaUrl(`ch03/lakes_valid/${props.lakeId}.json`))
    if (r.ok) sidecar.value = (await r.json()) as SeasonSidecar
  } catch {
    // the scrubber simply has one frame
  }
})
</script>

<style scoped>

.ld-root {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 9vh 3vw 4vh;
  font-family: 'Inter', system-ui, sans-serif;
  color: #f5f0e6;
}
.ld-stage {
  display: flex;
  gap: 3.2vw;
  align-items: center;
  width: 100%;
  max-width: 1500px;
}
.ld-left {
  flex: 0 0 auto;
  width: min(58vh, 40vw);
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.ld-id {
  font-family: ui-monospace, 'SF Mono', Menlo, monospace;
  font-size: 1.05rem;
  letter-spacing: 0.03em;
  color: rgba(245, 240, 230, 0.85);
}
.ld-right {
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
  padding: 1.6rem 1.8rem;
  background: rgba(10, 9, 8, 0.85);
  border: 1.5px solid rgba(245, 199, 94, 0.36);
  border-radius: 14px;
}
.ld-bar {
  display: flex;
  height: 14px;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.06);
}
.ld-bar-seg { display: block; height: 100%; transition: width 0.2s; }
.ld-bar-pub { height: 10px; margin: 0.2rem 0 0.5rem; }

.ld-actions { display: flex; gap: 0.7rem; align-items: center; }
.ld-commit {
  border: 1.5px solid var(--gold);
  background: rgba(56, 38, 12, 0.5);
  color: var(--gold-bright);
  font-family: inherit;
  font-size: 0.95rem;
  letter-spacing: 0.06em;
  padding: 0.6rem 1.4rem;
  border-radius: 999px;
  cursor: pointer;
}
.ld-commit:disabled { opacity: 0.45; cursor: default; }
.ld-reset {
  border: 1.5px solid rgba(245, 199, 94, 0.5);
  background: transparent;
  color: var(--gold-dim);
  font-size: 1rem;
  width: 2.3rem;
  height: 2.3rem;
  border-radius: 50%;
  cursor: pointer;
}
.ld-reveal {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding-top: 0.6rem;
  border-top: 1px solid rgba(245, 199, 94, 0.2);
}
.ld-reveal-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 1rem;
  font-size: 1rem;
}
.ld-reveal-k { color: rgba(245, 240, 230, 0.78); letter-spacing: 0.06em; font-size: 0.92rem; }
/* The back row of the room: the shared slider + season widgets'
   small print, larger and brighter on this beat only (the labeler door
   at /additional-work/label keeps its own). */
.ld-root :deep(.ld-tick-lbls span) { font-size: 0.92rem; color: rgba(245, 240, 230, 0.9); }
.ld-root :deep(.ld-tick-mark) { background: rgba(245, 240, 230, 0.75); }
.ld-root :deep(.ld-val) { color: rgba(245, 240, 230, 0.9); }
.ld-root :deep(.ld-lbl) { font-size: 12.5px; fill: rgba(245, 240, 230, 0.95); }
.ld-root :deep(.ld-tick) { font-size: 12.5px; fill: rgba(245, 240, 230, 0.92); }
.ld-root :deep(.ld-line) { stroke-width: 2.2; }
.ld-root :deep(.ld-date-year) { font-size: 0.82rem; color: rgba(245, 240, 230, 0.78); }
.ld-reveal-v { font-weight: 600; }
</style>
