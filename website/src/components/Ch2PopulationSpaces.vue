<template>
  <!-- The population pair — every center lake's neighbours in ONE stress
       space per model, elastic | viscous: the talk's population page as
       it was before the director limited the talk's Chapter 2 to the
       viscous model (viscous only there since). The elastic x
       is the superposed σ^V_pre + Δσ^E (the ≈ definition on its axis),
       flagged qualitative; the talk's ±1000 kPa frame; a hovered lake
       lights in both. -->
  <div class="pp">
    <div class="pp-cols">
      <div v-for="m in MODELS" :key="m" class="pp-col">
        <div class="pp-title">{{ m === 'elastic' ? 'Elastic' : 'Viscous' }}</div>
        <div class="pp-ss">
          <Ch2StressSpace
            v-if="phase"
            :model="m"
            comp="t1"
            :points="phase.models[m]?.points ?? []"
            :center-num="CENTER"
            show-all
            :labels="false"
            :header-model="false"
            :fs="1.3"
            :highlight-num="hl"
            :x-title="m === 'elastic' ? 'ax_post_s_t1' : null"
            :note="m === 'elastic' ? '(qualitative, for illustration only)' : null"
            note-row
            hug-top
            @lake-hover="hl = $event"
          />
        </div>
      </div>
    </div>
    <!-- the center-lake key -->
    <div class="pp-centers">
      <span v-for="c in centers" :key="c" class="pp-center">
        <svg width="24" height="24"><path :d="phaseMarkerPath(PHASE_CENTER_MARKERS[c] ?? 'o', 12, 12, 8.5)" fill="rgba(245,240,230,0.85)" stroke="rgba(0,0,0,0.6)" stroke-width="1" /></svg>
        {{ c }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, shallowRef } from 'vue'
import Ch2StressSpace from './Ch2StressSpace.vue'
import type { Ch2Model } from '../config/ch2Beats'
import { loadCh2Phase } from '../config/ch2Results'
import { PHASE_CENTER_MARKERS, phaseMarkerPath, type PhaseSpaceFile } from '../config/simLakes'

const MODELS: Ch2Model[] = ['elastic', 'viscous']
const CENTER = 2394 // every lake draws alike with show-all; the prop wants one
const hl = ref<number | null>(null)
const phase = shallowRef<PhaseSpaceFile | null>(null)
loadCh2Phase().then((j) => (phase.value = j))
const centers = computed(() => {
  const s = new Set<number>()
  for (const p of phase.value?.models.viscous?.points ?? []) s.add(p.center)
  return [...s].sort((a, b) => a - b)
})
</script>

<style scoped>
.pp {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
}
.pp-cols {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  gap: 2rem;
  width: 100%;
  flex-wrap: wrap;
}
.pp-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 0 1 min(46%, calc((100vh - var(--dd-chrome, 15.5rem)) * 0.9));
  min-width: 300px;
}
.pp-title {
  font-family: 'EB Garamond', serif;
  font-size: 1.9rem;
  line-height: 1.05;
  color: var(--gold);
  letter-spacing: 0.02em;
  margin-bottom: -1.2rem;
}
.pp-ss {
  width: 100%;
}
.pp-ss :deep(.ss-svg) {
  width: 100%;
  height: auto;
}
.pp-centers {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1.4rem;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1.05rem;
  font-variant-numeric: tabular-nums;
  color: rgba(245, 240, 230, 0.92);
}
.pp-center {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
</style>
