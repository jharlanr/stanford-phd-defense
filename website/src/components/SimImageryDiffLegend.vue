<template>
  <!-- The IMAGERY · DIFFERENCE cell's scale:
       mean-RGB Sentinel-2 surface reflectance, post − pre, on BrBG —
       brown darkened, teal brightened (a drained lake). It takes the
       stress colourbar's bare style and place (no card, no kicker; under
       the block's left area): ΔR and the bar; now it hangs in the
       stress bar's place under the tier pills (components/blockAnchor.ts
       useInsetKeyAnchor) — nothing jumps.
       Never on screen with the stress bar (that one belongs to the model
       layers). -->
  <div
    ref="root"
    class="idl ch2-key"
    :class="{ 'idl-hidden': !visible || !ready }"
    :style="{ left: left + 'px', top: top + 'px' }"
  >
    <img :src="ch2EqUrl('cb_dR')" class="idl-sym" :style="eqBox" alt="ΔR" />
    <div class="idl-scale">
      <div class="idl-bar" />
      <div class="idl-ticks">
        <span v-for="t in ticks" :key="t.p" :style="{ left: t.p + '%' }"><i />{{ t.l }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { IMAGERY_DIFF_LIM } from '../config/ch2State'
import { CH2_EQ } from '../config/ch2Eqs'
import { ch2EqUrl } from '../config/ch2Results'
import { useInsetKeyAnchor } from './blockAnchor'

defineProps<{ visible: boolean }>()
const lim = IMAGERY_DIFF_LIM.toFixed(1)
const ticks = [
  { p: 0, l: `−${lim}` },
  { p: 50, l: '0' },
  { p: 100, l: `+${lim}` },
]
const eqBox = { width: `${CH2_EQ.cb_dR.w * 2.1}px`, height: `${CH2_EQ.cb_dR.h * 2.1}px` }

const root = ref<HTMLElement | null>(null)
const { left, top, ready } = useInsetKeyAnchor(root)
</script>

<style scoped>
.idl {
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
.idl-hidden {
  opacity: 0;
}
.idl-sym {
  display: block;
}
/* the bar and its ticks under it */
.idl-scale {
  width: 180px;
  margin-left: 6px;
}
/* matplotlib BrBG, the shader's ramp (Globe.vue simImgDiffRamp) */
.idl-bar {
  height: 16px;
  border-radius: 2px;
  box-shadow: 0 0 0 1.5px rgba(245, 240, 230, 0.85);
  background: linear-gradient(
    to right,
    #543005, #8c510a 10%, #bf812d 20%, #dfc27d 30%, #f6e8c3 40%,
    #f5f5f5 50%,
    #c7eae5 60%, #80cdc1 70%, #35978f 80%, #01665e 90%, #003c30
  );
}
.idl-ticks {
  position: relative;
  height: 28px;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 18px;
  font-weight: 600;
  color: #f5f0e6;
  font-variant-numeric: tabular-nums;
}
.idl-ticks span {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  white-space: nowrap;
  line-height: 1;
}
.idl-ticks i {
  display: block;
  width: 2px;
  height: 7px;
  margin-bottom: 3px;
  background: #f5f0e6;
}
</style>
