<template>
  <!-- Borders around sub-blocks of a confusion matrix (config/
       confusionBlocks.ts). CONTRACT: render this component as a DIRECT
       CHILD of the matrix's CSS-grid container, and give that container
       `position: relative`. Each outline is an ABSOLUTELY positioned grid
       item placed by grid lines, so it takes the block's grid area as its
       box and never enters auto-placement — the cells do not move, and
       nothing is measured. Outlines animate in when `show` turns true and
       out when it turns false. -->
  <div
    v-for="(b, k) in blocks"
    :key="`${b.pair[0]}-${b.pair[1]}`"
    class="cbo"
    :class="{ 'cbo-on': show }"
    :style="{
      gridRow: b.area.gridRow,
      gridColumn: b.area.gridColumn,
      '--cbo-color': color,
      '--cbo-pad': pad + 'px',
      transitionDelay: show ? `${k * stagger}ms` : '0ms',
    }"
    aria-hidden="true"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { blockArea, CONFUSING_PAIRS, type ConfusionPair } from '../config/confusionBlocks'

const props = withDefaults(
  defineProps<{
    /** The matrix's class order (rows = columns), e.g. ND HF MD LD CD. */
    order: readonly string[]
    /** Which blocks — default HF–MD and MD–LD. */
    pairs?: readonly ConfusionPair[]
    show: boolean
    /** Header tracks before the first cell (a label row/column = 1). */
    offset?: number
    /** px the border stands off the cells (about half the grid gap). */
    pad?: number
    color?: string
    /** ms between one block's entrance and the next. */
    stagger?: number
  }>(),
  { pairs: () => CONFUSING_PAIRS, offset: 1, pad: 3, color: '#f5f0e6', stagger: 260 },
)

const blocks = computed(() =>
  props.pairs.flatMap((pair) => {
    const area = blockArea(props.order, pair, props.offset)
    return area ? [{ pair, area }] : []
  }),
)
</script>

<style scoped>
.cbo {
  position: absolute;
  inset: calc(-1 * var(--cbo-pad));
  border: 3px solid var(--cbo-color);
  border-radius: 9px;
  box-shadow:
    0 0 0 1.5px rgba(0, 0, 0, 0.75),
    inset 0 0 0 1.5px rgba(0, 0, 0, 0.55),
    0 0 18px rgba(245, 240, 230, 0.25);
  pointer-events: none;
  z-index: 3;
  opacity: 0;
  transform: scale(1.12);
  transition: opacity 0.45s ease-out, transform 0.6s cubic-bezier(0.2, 0.9, 0.25, 1);
}
.cbo.cbo-on {
  opacity: 1;
  transform: scale(1);
}
</style>
