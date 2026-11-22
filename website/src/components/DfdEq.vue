<template>
  <!-- One baked LaTeX equation (an SVG from one of the site's deterministic
       bakes), sized from its measured TeX box so a row of pieces shares a
       baseline: `k` = px per bp; inline pieces sit on the text baseline
       (vertical-align from the box's baseline). Sets: the DFD page's own
       bake (dfd), the Chapter 2 slab's field names (slab), the stress
       relations (rel), Chapter 1's derivation (ch1). -->
  <img :src="src" :style="style" :alt="alt ?? name" class="dfd-eq" draggable="false" decoding="async" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { DFD_EQ } from '../config/dfdEqs'
import { dfdEqUrl } from '../config/dfd'
import { CH2_SLAB_EQ } from '../config/ch2SlabEqs'
import { slabEqUrl } from '../config/ch2Slab'
import { CH2_REL_EQ, type Ch2RelEqName } from '../config/ch2RelEqs'
import { ch2RelEqUrl } from '../config/ch2StressRel'
import { CH1_EQ, type Ch1EqName } from '../config/ch1Eqs'
import { mediaUrl } from '../config/media'

const props = withDefaults(
  defineProps<{
    name: string
    set?: 'dfd' | 'slab' | 'rel' | 'ch1'
    /** px per bp (the TeX point) */
    k?: number
    alt?: string
    /** sit on the text baseline (false = a block, no baseline shift) */
    inline?: boolean
  }>(),
  { set: 'dfd', k: 2.2, inline: true },
)

const box = computed(() => {
  switch (props.set) {
    case 'slab':
      return CH2_SLAB_EQ[props.name] ?? null
    case 'rel':
      return CH2_REL_EQ[props.name as Ch2RelEqName] ?? null
    case 'ch1':
      return CH1_EQ[props.name as Ch1EqName] ?? null
    default:
      return DFD_EQ[props.name] ?? null
  }
})
const src = computed(() => {
  switch (props.set) {
    case 'slab':
      return slabEqUrl(props.name)
    case 'rel':
      return ch2RelEqUrl(props.name as Ch2RelEqName)
    case 'ch1':
      return mediaUrl(`ch01/eq2/${props.name}.svg`)
    default:
      return dfdEqUrl(props.name)
  }
})
const style = computed<Record<string, string>>(() => {
  const b = box.value
  if (!b) return { display: 'none' }
  // width + aspect ratio (never a fixed height): a piece wider than its
  // column shrinks with it instead of overflowing into the next one
  const s: Record<string, string> = {
    width: `${(b.w * props.k).toFixed(2)}px`,
    maxWidth: '100%',
    aspectRatio: `${b.w.toFixed(3)} / ${b.h.toFixed(3)}`,
    height: 'auto',
  }
  if (props.inline) s.verticalAlign = `${(-(b.h - b.base) * props.k).toFixed(2)}px`
  else s.display = 'block'
  return s
})
</script>

<style scoped>
.dfd-eq {
  user-select: none;
  pointer-events: none;
}
</style>
