<template>
  <!-- One block of Chapter 2's stress relations (deeper dive
       #stress-relations): its LaTeX SVGs stacked and
       centred on the same dark plate between gold rules as the stress-space
       definitions (Ch2StressEqs.vue). The type scale --eqk (CSS px per TeX
       bp) puts Computer Modern's x-height at ≈ 15 px at 1440 wide; a row
       wider than the column scales down to fit (never a horizontal
       scroll). Lazy: an SVG loads when its block nears the viewport. -->
  <div class="sr-plate">
    <img
      v-for="n in CH2_REL_BLOCKS[block]"
      :key="n"
      :src="ch2RelEqUrl(n)"
      :alt="CH2_REL_ALT[n]"
      :style="box(n)"
      class="sr-eq"
      loading="lazy"
      decoding="async"
    />
  </div>
</template>

<script setup lang="ts">
import { CH2_REL_EQ, type Ch2RelEqName } from '../config/ch2RelEqs'
import { CH2_REL_ALT, CH2_REL_BLOCKS, ch2RelEqUrl, type Ch2RelBlock } from '../config/ch2StressRel'

defineProps<{ block: Ch2RelBlock }>()

/** The TeX box at --eqk CSS px per bp, its aspect kept when it shrinks. */
function box(name: Ch2RelEqName) {
  const b = CH2_REL_EQ[name]
  return { width: `calc(${b.w} * var(--eqk))`, aspectRatio: `${b.w} / ${b.h}` }
}
</script>

<style scoped>
.sr-plate {
  /* 3.5 px per bp → CM's 4.3 bp x-height ≈ 15 px at 1440 wide */
  --eqk: min(3.5px, 0.243vw);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: calc(9 * var(--eqk));
  width: fit-content;
  max-width: 100%;
  box-sizing: border-box;
  margin: 0 auto;
  padding: 1.4rem 2rem;
  background: rgba(0, 0, 0, 0.35);
  border-top: 1.5px solid var(--gold);
  border-bottom: 1.5px solid var(--gold);
  user-select: none;
}
.sr-eq {
  display: block;
  max-width: 100%;
  height: auto;
}
</style>
