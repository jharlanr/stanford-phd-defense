<template>
  <!-- Ch.3: the ESSD paper's Fig. 6 — three pairwise labeler-vs-labeler
       confusion matrices on the 200-lake inter-rater subset. Rows = the
       first labeler's class, columns = the second's; each cell carries
       the count and its row-normalized share (the colour). Data from
       ch03/essd_irr.json (cinematic/scene_ch03/build_essd_lakes.py,
       recomputed from the shipped IRR CSVs). Labels are the figure's.
       The director asked for no Fleiss' κ; a second beat (step 1)
       keeps the matrices exactly where they are and outlines the two
       most-confused blocks in each — HF–MD and MD–LD
       (ConfusionBlockOutlines) — with the other cells dimmed. -->
  <div class="irr-root">
    <!-- The two other labelers, top-left (the director asked for the
         headshots and names of Niall B. Coffey and Eojin Lee on the labeler
         comparison page, in the top-left corner). Faces
         are the Acknowledgements' own. Bare — no plate, no labeler numbers
         (the director wanted just the headshots and names, and no hint of
         which of them is labeler 2 or 3). -->
    <div class="irr-people" aria-hidden="true">
      <div v-for="l in LABELERS" :key="l.slug" class="irr-person">
        <img class="irr-face" :src="faceUrl(l.slug)" :alt="l.name" />
        <span class="irr-person-name">{{ l.name }}</span>
      </div>
    </div>
    <div v-if="irr" class="irr-panels">
      <div v-for="p in irr.pairs" :key="`${p.row}${p.col}`" class="irr-panel">
        <div class="irr-title">Labeler {{ p.row }} vs Labeler {{ p.col }}</div>
        <div class="irr-grid" :style="{ gridTemplateColumns: `auto repeat(${n}, 1fr)` }">
          <div class="irr-corner" />
          <div v-for="c in irr.class_order" :key="`ch-${c}`" class="irr-col-head" :style="{ color: irr.classes[c].color }">{{ c }}</div>
          <template v-for="(row, i) in p.counts" :key="`r-${i}`">
            <div class="irr-row-head" :style="{ color: irr.classes[irr.class_order[i]].color }">{{ irr.class_order[i] }}</div>
            <div
              v-for="(v, j) in row"
              :key="`c-${i}-${j}`"
              class="irr-cell"
              :class="{
                'irr-diag': i === j,
                'irr-dark': frac(row, v) > 0.55,
                'irr-dim': highlight && !inAnyBlock(irr.class_order, CONFUSING_PAIRS, i, j),
              }"
              :style="{ background: cellColor(frac(row, v)) }"
            >
              <span class="irr-count">{{ v }}</span>
              <span class="irr-pct">{{ Math.round(frac(row, v) * 100) }}%</span>
            </div>
          </template>
          <ConfusionBlockOutlines :order="irr.class_order" :show="highlight" />
        </div>
        <div class="irr-axes">
          <span class="irr-axis-y">Labeler {{ p.row }}</span>
          <span class="irr-axis-x">Labeler {{ p.col }}</span>
        </div>
        <div class="irr-agree">{{ Math.round((p.agreement ?? 0) * 100) }}% agree</div>
      </div>
    </div>
    <div v-if="irr" class="irr-foot">
      <span>n = {{ irr.n }}</span>
      <span>all three agree {{ Math.round(irr.all3_agree * 100) }}%</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { mediaUrl } from '../config/media'
import { CONFUSING_PAIRS, inAnyBlock } from '../config/confusionBlocks'
import ConfusionBlockOutlines from './ConfusionBlockOutlines.vue'
import { ACK_HEADSHOTS } from '../config/ackHeadshots.gen'

/** The labelers beside the director (Labeler 1), in the bake's order. */
// (no labeler numbers — the director asked not to reveal which is labeler 2 or 3)
const LABELERS = [
  { slug: 'niall-coffey', name: 'Niall B. Coffey' },
  { slug: 'eojin-lee', name: 'Eojin Lee' },
] as const
/** The face's R2 key (every labeler here has a photo entry). */
function faceUrl(slug: string): string {
  const f = ACK_HEADSHOTS[slug] as { key?: string } | undefined
  return f?.key ? mediaUrl(f.key) : ''
}

const props = withDefaults(defineProps<{
  /** 0 = the matrices · 1 = the same, HF–MD and MD–LD outlined. */
  step?: number
}>(), { step: 0 })
const highlight = computed(() => props.step >= 1)

interface IrrFile {
  n: number
  class_order: string[]
  classes: Record<string, { name: string; color: string }>
  pairs: { row: number; col: number; counts: number[][]; agreement: number | null }[]
  all3_agree: number
}
const irr = ref<IrrFile | null>(null)
const n = computed(() => irr.value?.class_order.length ?? 5)

function frac(row: number[], v: number): number {
  const s = row.reduce((a, b) => a + b, 0)
  return s ? v / s : 0
}
// A gold ramp on the chalkboard (the paper's Blues, in the site's ink):
// 0 → near-transparent, 1 → solid gold.
function cellColor(f: number): string {
  const a = 0.06 + 0.9 * Math.pow(f, 0.85)
  return `rgba(244, 207, 106, ${a.toFixed(3)})`
}

onMounted(() => {
  fetch(mediaUrl('ch03/essd_irr.json'))
    .then((r) => (r.ok ? r.json() : null))
    .then((j) => { irr.value = j as IrrFile | null })
    .catch(() => {})
})
</script>

<style scoped>
.irr-root {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2.4vh;
  padding: 9vh 3vw 4vh;
  font-family: 'Inter', system-ui, sans-serif;
  color: #f5f0e6;
}
/* the two labelers' faces, top-left — bare, no plate (the director
   wanted no card, just the headshots and names, and a little
   smaller); back-row sizes still */
.irr-people {
  position: absolute;
  top: max(9.5vh, calc(var(--chrome-bottom, 0px) + 0.75rem));
  left: 2vw;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  pointer-events: none;
}
.irr-person {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}
.irr-face {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  border: 1.5px solid var(--gold, #f4cf6a);
  background: #222;
}
.irr-person-name {
  font-size: 0.95rem;
  font-weight: 600;
  color: #f5f5f5;
  white-space: nowrap;
  text-shadow: 0 1px 3px #000;
}

/* narrow projector widths: the labelers' card would touch the first
   matrix — start the panels a little lower (the bottom has the room) */
@media (max-width: 1320px) {
  .irr-root { padding-top: calc(9vh + 2rem); }
}

.irr-panels {
  display: flex;
  gap: 2.6vw;
  align-items: flex-start;
  justify-content: center;
  width: 100%;
  max-width: 1780px;
}
.irr-panel {
  position: relative;
  flex: 0 1 30%;
  min-width: 0;
  padding: 1rem 1.1rem 2.2rem 3.9rem;
  background: rgba(10, 9, 8, 0.85);
  border: 1.5px solid rgba(245, 199, 94, 0.36);
  border-radius: 14px;
}
.irr-title {
  font-family: 'EB Garamond', serif;
  font-size: clamp(1.15rem, 1.6vw, 1.55rem);
  color: var(--gold-bright);
  text-align: center;
  margin-bottom: 0.7rem;
  white-space: nowrap;
}
.irr-grid {
  position: relative; /* ConfusionBlockOutlines' containing block */
  display: grid;
  gap: 4px;
}
.irr-corner { }
.irr-col-head,
.irr-row-head {
  font-weight: 700;
  font-size: 1rem;
  letter-spacing: 0.04em;
  display: flex;
  align-items: center;
  justify-content: center;
}
.irr-row-head { justify-content: flex-end; padding-right: 0.5rem; }
.irr-cell {
  aspect-ratio: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  line-height: 1.15;
  color: #f5f0e6;
  min-width: 0;
}
.irr-cell.irr-dark { color: #1a1408; }
.irr-cell { transition: filter 0.6s ease, opacity 0.6s ease; }
.irr-cell.irr-dim { filter: saturate(0.55) brightness(0.5); opacity: 0.7; }
.irr-cell.irr-diag { outline: 1.5px solid rgba(245, 240, 230, 0.5); }
.irr-count {
  font-weight: 700;
  font-size: clamp(0.95rem, 1.3vw, 1.3rem);
  font-variant-numeric: tabular-nums;
}
.irr-pct {
  /* 0.78 → 0.92vw (11 → 13 px at 1440): legible from the back row */
  font-size: clamp(0.72rem, 0.92vw, 0.95rem);
  opacity: 0.92;
  font-variant-numeric: tabular-nums;
}
.irr-axes { }
.irr-axis-y {
  position: absolute;
  left: 0.45rem;
  top: 55%;
  transform: translateY(-50%) rotate(-90deg);
  transform-origin: center;
  font-size: 0.95rem;
  letter-spacing: 0.06em;
  color: rgba(245, 240, 230, 0.85);
  white-space: nowrap;
}
.irr-axis-x {
  position: absolute;
  left: 55%;
  bottom: 0.55rem;
  transform: translateX(-50%);
  font-size: 0.95rem;
  letter-spacing: 0.06em;
  color: rgba(245, 240, 230, 0.85);
  white-space: nowrap;
}
.irr-agree {
  position: absolute;
  right: 1.1rem;
  bottom: 0.5rem;
  font-size: 0.95rem;
  color: var(--gold);
  font-variant-numeric: tabular-nums;
}
.irr-foot {
  display: flex;
  gap: 2.6rem;
  font-size: 1.15rem;
  color: rgba(245, 240, 230, 0.88);
  font-variant-numeric: tabular-nums;
}
</style>
