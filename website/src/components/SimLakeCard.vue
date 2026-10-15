<template>
  <transition name="slc">
    <div v-if="lake" class="slc-card" :class="{ 'slc-pinned': pinned }">
      <div class="slc-head">
        <span
          class="slc-swatch"
          :style="{ borderTopColor: swatch, borderTopStyle: dashed ? 'dashed' : 'solid' }"
        />
        <span class="slc-title">Lake {{ lake.num }}</span>
        <span class="slc-cls">{{ clsLabel }}</span>
        <span v-if="pinned" class="slc-pin" title="pinned — click the lake again to release">📌</span>
      </div>
      <div class="slc-sub">
        {{ modelLabel }} · tangent-plane principal stresses [kPa]
      </div>
      <table v-if="rows" class="slc-table">
        <thead>
          <tr><th></th><th>max</th><th>mean</th><th>min</th></tr>
        </thead>
        <tbody>
          <tr class="slc-group"><td colspan="4">with patch</td></tr>
          <tr>
            <td>σ<sub>t1</sub></td>
            <td>{{ fmt(rows.s1_post.max) }}</td>
            <td class="slc-mean">{{ fmt(rows.s1_post.mean) }}</td>
            <td>{{ fmt(rows.s1_post.min) }}</td>
          </tr>
          <tr>
            <td>σ<sub>t2</sub></td>
            <td>{{ fmt(rows.s2_post.max) }}</td>
            <td class="slc-mean">{{ fmt(rows.s2_post.mean) }}</td>
            <td>{{ fmt(rows.s2_post.min) }}</td>
          </tr>
          <tr class="slc-group"><td colspan="4">difference · with − no patch</td></tr>
          <tr>
            <td>Δσ<sub>t1</sub></td>
            <td>{{ fmt(rows.s1_diff.max) }}</td>
            <td class="slc-mean">{{ fmt(rows.s1_diff.mean) }}</td>
            <td>{{ fmt(rows.s1_diff.min) }}</td>
          </tr>
          <tr>
            <td>Δσ<sub>t2</sub></td>
            <td>{{ fmt(rows.s2_diff.max) }}</td>
            <td class="slc-mean">{{ fmt(rows.s2_diff.mean) }}</td>
            <td>{{ fmt(rows.s2_diff.min) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="slc-nodata">no stress arrays for this lake</div>
      <div v-if="lake.stats" class="slc-foot">
        polygon mean of {{ lake.stats.n_points.toLocaleString() }} grid points
        <template v-if="lake.phase"> · in the phase space</template>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  SIM_LAKE_STYLE,
  type SimCatalogLake,
  type SimFace,
  type SimModelStats,
} from '../config/simLakes'

// Ch.2 zoomed-in state: hover/click a drainage-catalog lake
// on the block → this popout shows its in-polygon stress table (the
// published per-lake stress arrays; max/mean/min of σ_t1 and σ_t2,
// post-drainage and Δ) for the active model. The director asked for it
// docked top-CENTER under the top-nav — the right column now belongs
// entirely to the full-height phase-space panels.
const props = defineProps<{
  lake: SimCatalogLake | null
  pinned: boolean
  face: SimFace
  /** MGSIM page: names the bed the table belongs to (viscous only there). */
  modelLabel?: string
}>()

const effModel = computed<'elastic' | 'viscous'>(() =>
  props.face === 'elastic' || props.face === 'viscous' ? props.face : 'viscous',
)
const modelLabel = computed(() =>
  props.modelLabel
    ? props.modelLabel
    : props.face === 'elastic' || props.face === 'viscous'
      ? `${props.face} model`
      : 'viscous model (pick a model pill to switch)',
)
const rows = computed<SimModelStats | null>(() =>
  props.lake?.stats ? props.lake.stats[effModel.value] : null,
)
const swatch = computed(() =>
  props.lake ? SIM_LAKE_STYLE[props.lake.cls].color : 'transparent',
)
const dashed = computed(() => (props.lake?.cls ?? '').startsWith('dash'))
const clsLabel = computed(() =>
  props.lake ? SIM_LAKE_STYLE[props.lake.cls].label : '',
)

function fmt(v: number | null): string {
  if (v === null || v === undefined) return '—'
  return v > 0 ? `+${v.toFixed(0)}` : v.toFixed(0)
}
</script>

<style scoped>
.slc-card {
  position: absolute;
  top: max(64px, 5.6vh);
  left: 50%;
  transform: translateX(-50%);
  width: 344px;
  z-index: 13;
  background: rgba(10, 9, 8, 0.92);
  border: 1.5px solid rgba(245, 199, 94, 0.55);
  border-radius: 14px;
  padding: 0.85rem 1rem 0.7rem;
  color: #f5f0e6;
  font-family: 'Inter', system-ui, sans-serif;
  /* NO backdrop-filter: a blurred layer over the WebGL canvas FROZE
     frame presentation on Chromium/macOS — the globe kept
     rendering but the compositor stopped picking up new frames. */
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.55);
  pointer-events: none;
}

.slc-head {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}

.slc-swatch {
  width: 20px;
  height: 0;
  border-top: 3.5px solid;
}

.slc-title {
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.slc-cls {
  font-size: 0.76rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(245, 240, 230, 0.85);
  margin-left: auto;
}

.slc-pin {
  font-size: 0.7rem;
}

.slc-sub {
  margin-top: 0.3rem;
  font-size: 0.78rem;
  letter-spacing: 0.05em;
  color: rgba(245, 199, 94, 0.95);
}

.slc-table {
  width: 100%;
  margin-top: 0.55rem;
  border-collapse: collapse;
  font-size: 0.92rem;
  font-variant-numeric: tabular-nums;
}

.slc-table th {
  font-size: 0.74rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(245, 240, 230, 0.82);
  text-align: right;
  padding: 0.15rem 0.3rem;
}

.slc-table td {
  text-align: right;
  padding: 0.22rem 0.3rem;
  border-top: 1px solid rgba(245, 245, 245, 0.07);
}

.slc-table td:first-child,
.slc-table th:first-child {
  text-align: left;
  color: rgba(245, 240, 230, 0.85);
}

.slc-group td {
  font-size: 0.74rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(245, 199, 94, 0.9);
  padding-top: 0.45rem;
  border-top: none;
}

.slc-mean {
  color: var(--gold-bright, #ffe9a8);
  font-weight: 600;
}

.slc-nodata {
  margin-top: 0.6rem;
  font-size: 0.88rem;
  color: rgba(245, 240, 230, 0.82);
}

.slc-foot {
  margin-top: 0.5rem;
  font-size: 0.74rem;
  color: rgba(245, 240, 230, 0.72);
}

.slc-enter-active,
.slc-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.slc-enter-from,
.slc-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-6px);
}
</style>
