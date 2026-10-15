<template>
  <!-- The play / pause glyph as geometry, not text (the director found
       the pause button blurry). It used to be the characters ❚❚ / ▶ —
       dingbats Inter and Arial lack, drawn from a fallback font at 12 px:
       the two bars sat < 1 px apart and landed on half pixels, so at 1×
       they smeared into one soft block. Here the bars are whole-unit rects
       snapped with crispEdges; the triangle is a path. Colour = currentColor. -->
  <svg
    class="ppg"
    :width="size"
    :height="size"
    :viewBox="`0 0 ${size} ${size}`"
    aria-hidden="true"
  >
    <g v-if="playing" shape-rendering="crispEdges">
      <rect :x="bar.x1" :y="bar.y" :width="bar.w" :height="bar.h" />
      <rect :x="bar.x2" :y="bar.y" :width="bar.w" :height="bar.h" />
    </g>
    <path v-else :d="tri" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ playing: boolean; size?: number }>(), { size: 12 })

// Integer geometry in CSS px: two bars of width ⌈s/4⌉ with a gap of the
// same width, centred; height = the size minus a pixel top and bottom.
const bar = computed(() => {
  const s = props.size
  const w = Math.max(2, Math.round(s / 4))
  const gap = Math.max(2, Math.round(s / 5))
  const x1 = Math.round((s - (2 * w + gap)) / 2)
  const h = s - 2 * Math.max(1, Math.round(s / 12))
  return { x1, x2: x1 + w + gap, w, y: Math.round((s - h) / 2), h }
})
// Play: an isoceles triangle, optically centred (nudged right by s/12).
const tri = computed(() => {
  const s = props.size
  const h = s * 0.86
  const w = h * 0.87
  const x0 = (s - w) / 2 + s / 12
  const y0 = (s - h) / 2
  return `M${x0.toFixed(2)},${y0.toFixed(2)} L${(x0 + w).toFixed(2)},${(s / 2).toFixed(2)} L${x0.toFixed(2)},${(y0 + h).toFixed(2)} Z`
})
</script>

<style scoped>
.ppg {
  display: block;
  pointer-events: none; /* the button is the hit target */
  fill: currentColor;
}
</style>
