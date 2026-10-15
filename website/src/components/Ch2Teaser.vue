<template>
  <!-- Chapter 2's teaser beat (`teaser/2`, config/ch2Beats.ts): the figure
       labels of the two blocks — which bed both are on (BedMachine, then
       the ten MGSIM realisations, one every 3 s), the cycle's pips, and
       the right-hand (twin) block's key: the MGSIM page's ±400 kPa
       seismic scale for viscous Δσ_t1 — and, right of the twin, Lake
       1938's viscous stress space ticking with the cycle (Ch2TeaserSpace).
       Figure labels only — the speaker narrates. -->
  <Transition name="ctz-fade">
    <div v-if="state" class="ctz">
      <div class="ctz-head">
        <div class="ctz-label">{{ state.label }}</div>
        <div class="ctz-pips">
          <span
            v-for="i in state.n"
            :key="i"
            class="ctz-pip"
            :class="{ 'ctz-pip-on': i - 1 === state.frame, 'ctz-pip-first': i === 1 }"
          />
        </div>
      </div>
      <div ref="keyEl" class="ctz-card" :class="{ 'ctz-hidden': !ready || !twinOut }" :style="{ left: left + 'px', top: top + 'px' }">
        <div class="ctz-title">Viscous <img :src="ch2EqUrl('cb_diff_t1')" class="ctz-eq" :style="eqStyle" alt="Δσt1 [MPa]" /></div>
        <div class="ctz-bar" />
        <div class="ctz-ticks">
          <span v-for="t in TICKS" :key="t" :style="{ left: `${((t + VLIM) / (2 * VLIM)) * 100}%` }">{{ fmt(t) }}</span>
        </div>
      </div>
      <Ch2TeaserSpace :frame="state.frame" />
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { CH2_TEASER_VLIM_KPA } from '../config/ch2Beats'
import { useBlockAnchor } from './blockAnchor'
import Ch2TeaserSpace from './Ch2TeaserSpace.vue'
import { CH2_EQ } from '../config/ch2Eqs'
import { ch2EqUrl } from '../config/ch2Results'

defineProps<{
  /** The cycle position (null = hidden). */
  state: { frame: number; n: number; label: string } | null
}>()

// The twin's key hangs under the TWIN block's left area, in the bare
// style of the bed key under the first block (blockAnchor.ts).
const keyEl = ref<HTMLElement | null>(null)
// It waits for the twin to be most of the way out: while the twin still
// sits behind the first block, its key would land on the bed key.
const twinOut = ref(false)
const { left, top, ready } = useBlockAnchor(keyEl, () => {
  const t = (window as unknown as { __simTwinScreen?: { shift: number; t: number } | null }).__simTwinScreen
  twinOut.value = (t?.t ?? 0) >= 0.75
  return t?.shift ?? 0
})
const VLIM = CH2_TEASER_VLIM_KPA / 1000 // MPa, as the label's unit
const TICKS = [-VLIM, 0, VLIM]
function fmt(t: number): string {
  return t < 0 ? `−${Math.abs(t)}` : `${t}`
}
const b = CH2_EQ.cb_diff_t1
const eqStyle = { width: `${b.w * 1.75}px`, height: `${b.h * 1.75}px` }
</script>

<style scoped>
.ctz {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 8;
}
.ctz-head {
  position: absolute;
  top: max(7vh, calc(var(--chrome-bottom, 0px) + 0.75rem));
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.55rem;
}
.ctz-label {
  font-family: 'EB Garamond', serif;
  font-size: 1.9rem;
  line-height: 1.1;
  color: var(--gold-bright, #f4cf6a);
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.9);
  white-space: nowrap;
}
.ctz-pips {
  display: flex;
  gap: 9px;
  align-items: center;
}
.ctz-pip {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  border: 2px solid rgba(245, 240, 230, 0.7);
  transition: background 0.3s, border-color 0.3s;
}
/* BedMachine's pip, set apart from the ten realisations */
.ctz-pip-first {
  margin-right: 8px;
  border-radius: 2px;
}
.ctz-pip-on {
  background: var(--gold, #f4cf6a);
  border-color: var(--gold, #f4cf6a);
}
.ctz-card {
  position: absolute;
  width: 280px;
  filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.9));
  transition: opacity 0.6s;
}
.ctz-hidden {
  opacity: 0;
}
.ctz-title {
  font-family: 'EB Garamond', serif;
  font-size: 1.35rem;
  line-height: 1.2;
  color: var(--gold-bright);
  margin-bottom: 0.55rem;
}
.ctz-bar {
  height: 18px;
  border-radius: 2px;
  box-shadow: 0 0 0 1.5px rgba(245, 240, 230, 0.85);
  /* matplotlib seismic, −lim at the left (the drapes' own ramp) */
  background: linear-gradient(to right,
    #00004c 0%, #000092 10%, #0000db 20%, #3131ff 30%, #9999ff 40%, #fffdfd 50%,
    #ff9999 60%, #ff3131 70%, #e60000 80%, #b20000 90%, #800000 100%);
}
.ctz-ticks {
  position: relative;
  height: 1.4rem;
  margin-top: 0.3rem;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 18px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: #f5f0e6;
}
.ctz-ticks span {
  position: absolute;
  transform: translateX(-50%);
}
.ctz-ticks span:first-child {
  transform: none;
}
.ctz-ticks span:last-child {
  transform: translateX(-100%);
}
.ctz-eq {
  display: inline-block;
  vertical-align: -0.28em;
  margin-left: 0.4rem;
}
.ctz-fade-enter-active,
.ctz-fade-leave-active {
  transition: opacity 0.6s ease;
}
.ctz-fade-enter-from,
.ctz-fade-leave-to {
  opacity: 0;
}
</style>
