<template>
  <!-- THEORY AGAINST 3-D STOKES: the Chapter 2 sweep's viewer (72 Elmer/Ice
       runs on four snapping sliders, Simulation | Theory | Difference for
       every field) beside WHERE IT BREAKS DOWN — the sweep's own numbers:
       for the field on the viewer, max|Stokes − theory| / max|theory| per
       run against R/H, one series per γ. Click a point and the viewer
       shows that run. The shallow-stream assumption under it. -->
  <div class="vd">
    <div class="vd-viewer">
      <Ch2SlabFieldViewer />
    </div>
    <div class="vd-err">
      <div class="vd-err-head">
        <DfdEq name="err_def" :k="2.0" :inline="false" />
      </div>
      <div class="vd-plot">
        <svg :viewBox="`0 0 ${W} ${H}`" class="vd-svg" aria-label="Fractional error of the theory against the Stokes runs, by patch radius over thickness">
          <!-- guides at 10 % and 20 % -->
          <line :x1="PL" :x2="PR" :y1="py(10)" :y2="py(10)" class="vd-guide" />
          <line :x1="PL" :x2="PR" :y1="py(20)" :y2="py(20)" class="vd-guide" />
          <text :x="PR - 4" :y="py(10) - 4" text-anchor="end" class="vd-tt vd-tt-dim">10 %</text>
          <text :x="PR - 4" :y="py(20) - 4" text-anchor="end" class="vd-tt vd-tt-dim">20 %</text>
          <!-- axes -->
          <g v-for="t in XT" :key="'x' + t">
            <line :x1="px(t)" :x2="px(t)" :y1="PB" :y2="PB + 6" class="vd-ax" />
            <text :x="px(t)" :y="PB + 20" text-anchor="middle" class="vd-tt">{{ t }}</text>
          </g>
          <g v-for="t in YT" :key="'y' + t">
            <line :x1="PL - 6" :x2="PL" :y1="py(t)" :y2="py(t)" class="vd-ax" />
            <text :x="PL - 10" :y="py(t) + 4" text-anchor="end" class="vd-tt">{{ t }}</text>
          </g>
          <rect :x="PL" :y="PT" :width="PR - PL" :height="PB - PT" class="vd-frame" />
          <text :x="16" :y="(PT + PB) / 2" text-anchor="middle" class="vd-tt" :transform="`rotate(-90 16 ${(PT + PB) / 2})`">ε [%]</text>
          <!-- the runs -->
          <g v-for="d in dots" :key="d.id" class="vd-dot" :class="{ 'vd-dot-g1': d.gamma >= 0.5, 'vd-dot-on': d.id === slabState.run }" @click="pick(d.id)">
            <circle :cx="px(d.x)" :cy="py(d.y)" r="11" class="vd-hit" />
            <circle v-if="d.gamma < 0.5" :cx="px(d.x)" :cy="py(d.y)" r="5.5" class="vd-mark" />
            <rect v-else :x="px(d.x) - 5" :y="py(d.y) - 5" width="10" height="10" class="vd-mark" />
            <circle v-if="d.id === slabState.run" :cx="px(d.x)" :cy="py(d.y)" r="10" class="vd-ring" />
          </g>
        </svg>
        <span class="vd-xlab"><DfdEq name="ax_RH" :k="1.9" /></span>
      </div>
      <div class="vd-legend">
        <span class="vd-leg"><i class="vd-leg-circle" /><span><i class="vd-k">γ</i> = 0.1 · 1/<i class="vd-k">k</i><sub>0</sub> = 4.5 <i class="vd-k">H</i></span></span>
        <span class="vd-leg"><i class="vd-leg-square" /><span><i class="vd-k">γ</i> = 1 · 1/<i class="vd-k">k</i><sub>0</sub> = 1.4 <i class="vd-k">H</i></span></span>
        <span class="vd-leg vd-leg-note">α only scales the stress · one point per run</span>
      </div>
      <div class="vd-assume">
        <DfdEq name="assum_shallow" :k="2.1" :inline="false" />
        <DfdEq name="def_decay_gamma" :k="1.9" :inline="false" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, shallowRef } from 'vue'
import DfdEq from './DfdEq.vue'
import Ch2SlabFieldViewer from './Ch2SlabFieldViewer.vue'
import { loadSlabManifest, slabState, type SlabManifest } from '../config/ch2Slab'

const man = shallowRef<SlabManifest | null>(null)
onMounted(async () => {
  man.value = await loadSlabManifest()
})

const W = 560
const H = 330
const PL = 52
const PR = W - 14
const PT = 14
const PB = H - 34
const XT = [0.3, 0.5, 1, 2, 5, 10, 20]
const YT = [0, 20, 40, 60]
const X0 = Math.log10(0.25)
const X1 = Math.log10(25)
function px(rh: number): number {
  return PL + ((Math.log10(rh) - X0) / (X1 - X0)) * (PR - PL)
}
function py(pct: number): number {
  return PB - (pct / 70) * (PB - PT)
}

interface Dot {
  id: string
  x: number
  y: number
  gamma: number
}
/** One point per run for the viewer's field: ε = max|Δ| / max|theory|. */
const dots = computed<Dot[]>(() => {
  const m = man.value
  if (!m) return []
  const f = slabState.field
  const out: Dot[] = []
  for (const [id, r] of Object.entries(m.runs)) {
    if (r.sweep === false) continue
    const th = r.max_kpa.theory[f]
    const d = r.max_kpa.diff_abs[f]
    if (!th || d === undefined) continue
    out.push({ id, x: r.R / r.H, y: Math.min(70, (d / th) * 100), gamma: r.gamma })
  }
  // the chosen run drawn last, on top
  out.sort((a, b) => (a.id === slabState.run ? 1 : b.id === slabState.run ? -1 : 0))
  return out
})
function pick(id: string): void {
  slabState.run = id
}
</script>

<style scoped>
.vd {
  height: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr);
  gap: 2vw;
  align-items: start;
  overflow: hidden;
}
.vd-viewer { min-width: 0; overflow: auto; max-height: 100%; }
.vd-viewer :deep(.sv) { --sv-thumb: 50px; }
.vd-viewer :deep(.sv-head span) { font-size: 0.6rem; letter-spacing: 0.02em; }
.vd-viewer :deep(.sv-paper) { max-width: min(520px, 50vh); }
.vd-err {
  display: flex;
  flex-direction: column;
  gap: 1vh;
  min-width: 0;
  padding: 1rem 1.2rem;
  border: 1px solid rgba(232, 185, 74, 0.25);
  border-radius: 12px;
  background: rgba(8, 6, 4, 0.5);
}
.vd-err-head { display: flex; justify-content: center; }
.vd-plot { position: relative; width: 100%; }
.vd-svg { width: 100%; height: auto; display: block; }
.vd-frame { fill: none; stroke: rgba(245, 240, 230, 0.55); stroke-width: 1.2; }
.vd-ax { stroke: rgba(245, 240, 230, 0.55); stroke-width: 1.2; }
.vd-guide { stroke: rgba(244, 207, 106, 0.4); stroke-width: 1.2; stroke-dasharray: 5 5; }
.vd-tt { font: 12.5px 'Inter', system-ui, sans-serif; fill: rgba(245, 240, 230, 0.85); }
.vd-tt-dim { fill: rgba(244, 207, 106, 0.7); }
.vd-xlab { position: absolute; right: 2%; bottom: -1.5rem; }
.vd-plot { padding-bottom: 1.4rem; }
.vd-dot { cursor: pointer; }
.vd-hit { fill: transparent; }
.vd-mark { fill: #f4cf6a; stroke: #1c1305; stroke-width: 1; }
.vd-dot-g1 .vd-mark { fill: rgba(8, 6, 4, 0.9); stroke: #f5f0e6; stroke-width: 1.6; }
.vd-dot:hover .vd-mark { filter: drop-shadow(0 0 6px rgba(245, 199, 94, 0.9)); }
.vd-ring { fill: none; stroke: #fff8e6; stroke-width: 2; }
.vd-legend { display: flex; flex-wrap: wrap; gap: 0.3rem 1.4rem; font-size: 0.86rem; color: rgba(245, 240, 230, 0.85); }
.vd-leg { display: inline-flex; align-items: center; gap: 0.45rem; }
.vd-leg i.vd-leg-circle { width: 11px; height: 11px; border-radius: 50%; background: #f4cf6a; border: 1px solid #1c1305; }
.vd-leg i.vd-leg-square { width: 10px; height: 10px; background: rgba(8, 6, 4, 0.9); border: 1.6px solid #f5f0e6; }
.vd-k { font-family: 'EB Garamond', Georgia, serif; font-style: italic; }
.vd-leg-note { color: var(--gold-dim); font-size: 0.78rem; letter-spacing: 0.04em; }
.vd-assume { display: flex; flex-wrap: wrap; gap: 0.6rem 2rem; align-items: center; justify-content: center; padding-top: 0.4rem; border-top: 1px solid rgba(232, 185, 74, 0.18); }
</style>
