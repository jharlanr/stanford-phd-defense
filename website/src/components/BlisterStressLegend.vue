<template>
  <!-- Ch.2's stress colourbar. The director asked for it kept simple: no
       card, just the bar, placed beneath the left area of the simulation
       domain, with the stress math symbols in place of words like
       'difference' and 'with patch'. So: the ±1 MPa seismic bar,
       its end labels, and the LaTeX symbol of what the block wears —
       σ_t1^pre · σ_t1^post · Δσ_t1 · Δσ_t2 [MPa]. No card, no kicker.
       Its place is the bottom left, just below the visible edge of the
       simulation domain where the outflow is, and it should settle
       smoothly into one position rather than jump: under the
       block's lower-left (outflow) edge, faded in only once its place has
       settled — components/blockAnchor.ts useOutflowKeyAnchor. -->
  <div
    ref="root"
    class="bsl ch2-key"
    :class="{ 'bsl-hidden': !visible || !ready }"
    :style="{ left: left + 'px', top: top + 'px' }"
  >
    <img :src="ch2EqUrl(sym)" class="bsl-sym" :style="eqBox(sym)" :alt="sym" />
    <div class="bsl-scale">
      <div class="bsl-bar" />
      <div class="bsl-ticks">
        <span v-for="t in TICKS" :key="t.p" :style="{ left: t.p + '%' }"><i />{{ t.l }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { SimField } from '../config/simLakes'
import { CH2_EQ, type Ch2EqName } from '../config/ch2Eqs'
import { ch2EqUrl } from '../config/ch2Results'
import { useOutflowKeyAnchor } from './blockAnchor'

// The published stress fields on the block share ONE seismic ±1 MPa
// scale for the elastic-blister and viscous drapes — the bar
// never changes, only the symbol: the field (pre = no blister / patch,
// post = with it, difference = the response) and, on the results walk,
// the principal (σ_t1 | σ_t2).
const props = withDefaults(
  defineProps<{ visible: boolean; model?: 'elastic' | 'viscous' | null; field?: SimField; comp?: 't1' | 't2' }>(),
  { model: 'elastic', field: 'difference', comp: 't1' },
)

const sym = computed<Ch2EqName>(() =>
  props.field === 'nopatch' ? 'cb_pre_t1' : props.field === 'patch' ? 'cb_post_t1' : props.comp === 't2' ? 'cb_diff_t2' : 'cb_diff_t1',
)
const TICKS = [
  { p: 0, l: '−1' },
  { p: 50, l: '0' },
  { p: 100, l: '+1' },
]
/** LaTeX label at 2.1 CSS px per bp (≈ 21 px math). */
function eqBox(name: Ch2EqName) {
  const b = CH2_EQ[name]
  return { width: `${b.w * 2.1}px`, height: `${b.h * 2.1}px` }
}

const root = ref<HTMLElement | null>(null)
const { left, top, ready } = useOutflowKeyAnchor(root, () => props.visible)
</script>

<style scoped>
.bsl {
  position: absolute;
  z-index: 8;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  pointer-events: none;
  transition: opacity 0.6s;
  filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.9));
}
.bsl-hidden {
  opacity: 0;
}
.bsl-sym {
  display: block;
}
/* the bar and its ticks under it */
.bsl-scale {
  width: 180px;
  margin-left: 6px;
}
/* matplotlib seismic: blue → white → red (the drape's own map) */
.bsl-bar {
  height: 16px;
  border-radius: 2px;
  box-shadow: 0 0 0 1.5px rgba(245, 240, 230, 0.85);
  background: linear-gradient(
    to right,
    #00004c,
    #0000db 12%,
    #4747ff 26%,
    #b3b3ff 40%,
    #ffffff 50%,
    #ffb3b3 60%,
    #ff4747 74%,
    #db0000 88%,
    #800000 100%
  );
}
.bsl-ticks {
  position: relative;
  height: 28px;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 18px;
  font-weight: 600;
  color: #f5f0e6;
  font-variant-numeric: tabular-nums;
}
.bsl-ticks span {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  white-space: nowrap;
  line-height: 1;
}
.bsl-ticks i {
  display: block;
  width: 2px;
  height: 7px;
  margin-bottom: 3px;
  background: #f5f0e6;
}
</style>
