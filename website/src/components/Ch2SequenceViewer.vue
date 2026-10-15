<template>
  <!-- Chapter 2's results walk WITH the elastic model — the talk's five
       stations as they were before the elastic model left the talk, for
       any of the seven center lakes (the director limited the talk's
       Chapter 2 to the viscous model as too much to fit; the full
       sequence, elastic included, became this section of the Chapter 2
       deeper dive). The stations row is the block's
       (SimViewControls' words, in time); LEFT the station's surface field
       on the field viewer's paper (config/ch2Fields.ts: the elastic POST
       cell is the superposed σ^V_pre + Δσ^E), RIGHT the talk's stress
       space (Ch2StressSpace: the lake's neighbours, the station's axis
       lit, blank on PRE). -->
  <div class="sq">
    <div class="sq-lakes" role="radiogroup" aria-label="Lake">
      <button
        v-for="l in CH2_FIELD_LAKES"
        :key="l.num"
        class="sq-lake"
        :class="{ 'sq-lake--on': l.num === lake }"
        role="radio"
        :aria-checked="l.num === lake"
        @click="lake = l.num"
      >
        <span class="sq-lake-num">{{ l.num }}</span>
        <span class="sq-lake-sim">{{ l.sim }}</span>
      </button>
    </div>

    <div class="sq-stations">
      <template v-for="(st, i) in STATIONS" :key="st.id">
        <span v-if="i > 0" class="sq-link" aria-hidden="true" />
        <button class="sq-st" :class="{ 'sq-on': st.id === station }" :aria-pressed="st.id === station" @click="station = st.id">
          <span class="sq-stage">{{ st.stage }}</span>
          <span class="sq-layer">{{ st.layer }}<span class="sq-sym">{{ st.sym }}<sub>t1</sub></span></span>
        </button>
      </template>
    </div>

    <div class="sq-body">
      <div class="sq-paper">
        <Ch2FieldPaper
          v-if="shown"
          :meta="shown.meta"
          :model="shown.model"
          :field-key="shown.key"
          :src="shown.src"
          :label="shown.label"
        />
        <div v-else class="sq-paper-blank" />
      </div>
      <div class="sq-plate">
        <Ch2StressSpace
          v-if="phase"
          :model="step.model"
          :comp="step.comp"
          :field="step.field"
          :emphasis="step.emphasis"
          :points="phase.models[step.model]?.points ?? []"
          :center-num="lake"
          labels
          :highlight-num="hl"
          @lake-hover="hl = $event"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, shallowRef, watch } from 'vue'
import Ch2FieldPaper from './Ch2FieldPaper.vue'
import Ch2StressSpace from './Ch2StressSpace.vue'
import { ch2StepOf, type Ch2PhaseId, type Ch2Step } from '../config/ch2Beats'
import {
  CH2_FIELD_LAKES,
  ch2CaseLabel,
  ch2CellLabel,
  ch2CellModel,
  ch2FieldSrc,
  ch2LakeJson,
  type Ch2LakeMeta,
  type Ch2Model,
} from '../config/ch2Fields'
import { loadCh2Phase } from '../config/ch2Results'
import type { PhaseSpaceFile } from '../config/simLakes'

/** The talk's five results stations, in time (config/ch2Beats.ts THE
 *  PATH; the elastic two are the deeper dive's alone),
 *  each with the field viewer's cell that paints it. */
interface Station {
  id: Ch2PhaseId
  stage: string
  layer: string
  sym: 'σ' | 'Δσ'
  model: Ch2Model
  key: string
}
const STATIONS: Station[] = [
  { id: 'pre-viscous-t1', stage: 'Pre drainage', layer: 'Viscous', sym: 'σ', model: 'viscous', key: 'st1_pre' },
  { id: 'post-elastic-t1', stage: 'Post drainage', layer: 'Elastic', sym: 'σ', model: 'elastic', key: 'st1_post' },
  { id: 'diff-elastic-t1', stage: 'Difference', layer: 'Elastic', sym: 'Δσ', model: 'elastic', key: 'st1_d' },
  { id: 'post-viscous-t1', stage: 'Post drainage', layer: 'Viscous', sym: 'σ', model: 'viscous', key: 'st1_post' },
  { id: 'diff-viscous-t1', stage: 'Difference', layer: 'Viscous', sym: 'Δσ', model: 'viscous', key: 'st1_d' },
]
const FALLBACK: Ch2Step = { model: 'viscous', comp: 't1', field: 'pre', emphasis: null }

const lake = ref<number>(2394) // the talk's first center lake
const station = ref<Ch2PhaseId>('pre-viscous-t1')
const hl = ref<number | null>(null)
const cur = computed(() => STATIONS.find((s) => s.id === station.value) ?? STATIONS[0])
const step = computed(() => ch2StepOf(cur.value.id) ?? FALLBACK)

// ── the stress-space points (one fetch, shared with the talk) ──
const phase = shallowRef<PhaseSpaceFile | null>(null)
loadCh2Phase().then((j) => (phase.value = j))

// ── the paper: committed once the field has decoded (the viewer's way) ──
interface Shown {
  meta: Ch2LakeMeta
  model: Ch2Model
  key: string
  src: string
  label?: string
}
const shown = shallowRef<Shown | null>(null)
const metaCache = new Map<number, Promise<Ch2LakeMeta>>()
function loadMeta(n: number): Promise<Ch2LakeMeta> {
  let p = metaCache.get(n)
  if (!p) {
    p = fetch(ch2LakeJson(n)).then((r) => {
      if (!r.ok) throw new Error(`lake_${n}.json: HTTP ${r.status}`)
      return r.json() as Promise<Ch2LakeMeta>
    })
    p.catch(() => metaCache.delete(n))
    metaCache.set(n, p)
  }
  return p
}
const warm = new Map<string, HTMLImageElement>()
function preload(url: string): HTMLImageElement {
  let im = warm.get(url)
  if (!im) {
    im = new Image()
    im.decoding = 'async'
    im.src = url
    warm.set(url, im)
  }
  return im
}
let token = 0
async function commit(): Promise<void> {
  const my = ++token
  const n = lake.value
  const st = cur.value
  const m = ch2CellModel(st.model, st.key)
  const src = ch2FieldSrc(n, m, st.key)
  try {
    const [meta] = await Promise.all([loadMeta(n), preload(src).decode().catch(() => undefined)])
    if (my !== token) return
    const label = ch2CellLabel(st.key, st.model)
    shown.value = { meta, model: m, key: st.key, src, label: label === ch2CaseLabel(st.key, st.model) ? undefined : label }
    // the lake's other four stations next, so a click lands at once
    for (const o of STATIONS) if (o !== st) preload(ch2FieldSrc(n, ch2CellModel(o.model, o.key), o.key))
  } catch (e) {
    console.warn('[sequence]', e)
  }
}
watch([lake, station], () => void commit(), { immediate: true })
</script>

<style scoped>
.sq {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.9rem;
}

/* ── the lakes (the field viewer's pills) ── */
.sq-lakes {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.35rem;
}
.sq-lake {
  display: inline-flex;
  align-items: baseline;
  gap: 0.35rem;
  padding: 0.38rem 0.75rem 0.4rem;
  border: 1px solid var(--gold-faint);
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.45);
  color: var(--gold-dim);
  font-family: 'Inter', system-ui, sans-serif;
  cursor: pointer;
  transition: color 0.2s, background 0.2s, border-color 0.2s;
}
.sq-lake:hover { color: var(--gold-bright); border-color: var(--gold-dim); }
.sq-lake-num {
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  font-variant-numeric: tabular-nums;
}
.sq-lake-sim {
  font-size: 0.74rem;
  letter-spacing: 0.06em;
  opacity: 0.75;
}
.sq-lake--on,
.sq-lake--on:hover {
  color: #0a0a0a;
  background: var(--gold-bright);
  border-color: var(--gold-bright);
}

/* ── the stations: the block's one-row timeline (SimViewControls) ── */
.sq-stations {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0.2rem;
}
.sq-link {
  width: 1.6rem;
  height: 1.5px;
  background: rgba(244, 207, 106, 0.45);
}
.sq-st {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.1rem;
  padding: 0.45rem 0.9rem 0.5rem;
  border: 1.5px solid rgba(244, 207, 106, 0.35);
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.45);
  color: rgba(245, 240, 230, 0.72);
  font-family: 'Inter', system-ui, sans-serif;
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s, background 0.2s;
}
.sq-st:hover { color: #f5f0e6; border-color: var(--gold-dim); }
.sq-stage {
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}
.sq-layer {
  font-size: 0.98rem;
  font-weight: 600;
  letter-spacing: 0.03em;
}
.sq-sym {
  margin-left: 0.4rem;
  font-family: 'EB Garamond', serif;
  font-style: italic;
  font-size: 1.12em;
  font-weight: 500;
  letter-spacing: 0;
}
.sq-sym sub { font-size: 0.66em; font-style: normal; }
.sq-on,
.sq-on:hover {
  color: #0a0a0a;
  background: var(--gold-bright);
  border-color: var(--gold-bright);
}

/* ── the paper beside the plate ── */
.sq-body {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 1.4rem;
  width: 100%;
  flex-wrap: wrap;
}
.sq-paper {
  /* the field paper's 1000 × 930, no taller than the room (--dd-chrome:
     the deeper dive's title + caption rows) */
  flex: 0 1 min(52%, calc((100vh - var(--dd-chrome, 15.5rem)) * 1.075));
  min-width: 320px;
  border: 1px solid var(--gold-faint);
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 12px 40px -18px rgba(0, 0, 0, 0.9);
}
.sq-paper-blank {
  aspect-ratio: 1000 / 930;
  background: #fff;
}
.sq-plate {
  flex: 1 1 0;
  min-width: 320px;
  max-width: calc((100vh - var(--dd-chrome, 15.5rem)) * 0.99);
  padding: 0.8rem 0.6rem 0.4rem;
  box-sizing: border-box;
  background: rgba(0, 0, 0, 0.35);
  border-top: 1.5px solid var(--gold);
  border-bottom: 1.5px solid var(--gold);
}
.sq-plate :deep(.ss-svg) {
  width: 100%;
  height: auto;
}
</style>
