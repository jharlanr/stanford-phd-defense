<template>
  <!-- The definitions behind the stress-space axes, exactly as the PNAS
       SI §4C sets them (cinematic/scene_ch02/build_results_eqs.py, LaTeX
       → SVG):
         σ_t1, σ_t2   Eq. [52] — the eigenvalues of the surface stress
                      projected onto the plane tangent to the ice surface,
                      its + and − roots on their own lines
         s_ij         the tangent-plane components (e_1, e_2 ⊥ n)
         Δσ_t1,t2     Eqs. [53]–[54] — the same eigenvalues of the
                      projected DIFFERENCE of the full tensors
       They rode the results beats until the director found they
       cluttered the bottom of the page and asked that they move to the
       additional-work deep dive instead — now the Chapter 2 deeper
       dive's #stress-spaces entry (DeeperDive.vue). One column, the "="
       signs aligned; the type scale is --eqk (CSS px per TeX bp), set by
       the parent. -->
  <div class="se-root">
    <img v-for="n in EIG" :key="n" :src="ch2EqUrl(n)" :style="box(n)" class="se-eq" :alt="ALT[n]" />
    <div class="se-aux">
      <img v-for="n in AUX" :key="n" :src="ch2EqUrl(n)" :style="box(n)" class="se-eq" :alt="ALT[n]" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { CH2_EQ, type Ch2EqName } from '../config/ch2Eqs'
import { ch2EqUrl } from '../config/ch2Results'

const EIG: Ch2EqName[] = ['def_t1', 'def_t2']
const AUX: Ch2EqName[] = ['def_s', 'def_dt']
const ALT: Partial<Record<Ch2EqName, string>> = {
  def_t1: 'σt1 = (s11+s22)/2 + √((s11−s22)²/4 + s12²)',
  def_t2: 'σt2 = (s11+s22)/2 − √((s11−s22)²/4 + s12²)',
  def_s: 's_ij = e_iᵀ σ e_j, e1, e2 ⊥ n',
  def_dt: 'Δσt1,t2: s_ij → e_iᵀ(σpost − σpre)e_j',
}

/** The TeX box at --eqk CSS px per bp. */
function box(name: Ch2EqName) {
  const b = CH2_EQ[name]
  return { width: `calc(${b.w} * var(--eqk))`, height: `calc(${b.h} * var(--eqk))` }
}
</script>

<style scoped>
.se-root {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: calc(8 * var(--eqk));
  user-select: none;
}
.se-eq {
  display: block;
  flex: 0 0 auto;
}
.se-aux {
  display: flex;
  flex-direction: column;
  gap: calc(8 * var(--eqk));
  margin-top: calc(6 * var(--eqk));
}
</style>
