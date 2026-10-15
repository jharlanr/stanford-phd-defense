<template>
  <!-- Chapter 2's bed beat (`bed/2`, config/ch2Beats.ts): the key to the
       glassy block's bed — the MGSIM page's hypsometric ramp over the
       same range (the palette PNG itself is the bar, so block and key
       agree to the byte) — and the lit neighbour's outline. Figure labels
       only (the speaker narrates). Sits where the stress colorbar sits on
       the other block beats (that one is hidden here). It borrows the
       stress bar's bare style and place — no card, under the block's left
       area (components/blockAnchor.ts); the top-left is the centre-lakes
       inset's. -->
  <div
    ref="root"
    class="cbl-card"
    :class="{ 'cbl-hidden': !visible || !ready }"
    :style="{ left: left + 'px', top: top + 'px' }"
  >
    <div class="cbl-title">Bed elevation</div>
    <div class="cbl-bar" :style="{ backgroundImage: `url(${paletteUrl})` }" />
    <div class="cbl-ticks">
      <span v-for="t in ticks" :key="t" :style="{ left: `${((t - vmin) / (vmax - vmin)) * 100}%` }">{{ fmt(t) }}</span>
    </div>
    <div class="cbl-unit">m above sea level</div>
    <div v-if="litNum !== null" class="cbl-key">
      <span class="cbl-ring" />
      <span>Lake {{ litNum }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useBlockAnchor } from './blockAnchor'

const props = withDefaults(
  defineProps<{
    visible: boolean
    paletteUrl: string
    vmin?: number
    vmax?: number
    /** The neighbour lit gold on the block (null = no key row). */
    litNum?: number | null
  }>(),
  { vmin: -300, vmax: 600, litNum: null },
)
const root = ref<HTMLElement | null>(null)
const { left, top, ready } = useBlockAnchor(root)
const ticks = computed(() => {
  const out: number[] = []
  // two or three steps across the range (0…400 → 200; −300…600 → 300)
  const span = props.vmax - props.vmin
  const step = span <= 400 ? 200 : span <= 750 ? 250 : 300
  for (let t = Math.ceil(props.vmin / step) * step; t <= props.vmax + 1e-6; t += step) out.push(t)
  return out
})
function fmt(t: number): string {
  return t < 0 ? `−${Math.abs(t)}` : `${t}`
}
</script>

<style scoped>
.cbl-card {
  position: absolute;
  width: 280px;
  z-index: 8;
  pointer-events: none;
  transition: opacity 0.6s;
  filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.9));
}
.cbl-hidden {
  opacity: 0;
  pointer-events: none;
}
.cbl-title {
  font-family: 'EB Garamond', serif;
  font-size: 1.35rem;
  line-height: 1.2;
  color: var(--gold-bright);
  margin-bottom: 0.55rem;
}
.cbl-bar {
  height: 18px;
  border-radius: 2px;
  box-shadow: 0 0 0 1.5px rgba(245, 240, 230, 0.85);
  background-size: 100% 100%;
  background-repeat: no-repeat;
  image-rendering: auto;
}
.cbl-ticks {
  position: relative;
  height: 1.3rem;
  margin: 0.3rem 0 0;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 18px;
  font-weight: 600;
  color: #f5f0e6;
  font-variant-numeric: tabular-nums;
}
.cbl-ticks span {
  position: absolute;
  transform: translateX(-50%);
  white-space: nowrap;
}
.cbl-unit {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.95rem;
  color: rgba(245, 245, 245, 0.86);
  text-align: center;
  margin-top: 0.1rem;
}
.cbl-key {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  margin-top: 0.6rem;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1rem;
  font-variant-numeric: tabular-nums;
  color: #f5c75e;
}
.cbl-ring {
  width: 18px;
  height: 14px;
  border-radius: 50%;
  border: 2.5px solid #f5c75e;
  box-sizing: border-box;
}
</style>
