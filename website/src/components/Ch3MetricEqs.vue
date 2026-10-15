<template>
  <!-- Chapter 3's metrics and loss (the director wanted the definitions
       of F1, accuracy, precision and recall in the Chapter 3 deeper dive,
       along with every metric the model reports and the form of the loss
       function) — ESSD v3 Sect. 3–4 + Appendix B, typeset by
       cinematic/scene_ch03/build_metric_eqs.py (R2 ch03/eq/), one column,
       each line with its gloss. -->
  <ol class="sp-root">
    <li v-for="r in ROWS" :key="r.eq" class="sp-row">
      <img :src="eqUrl(r.eq)" :style="box(r.eq)" class="sp-eq" :alt="r.alt" />
      <p class="sp-gloss" v-html="r.gloss" />
    </li>
  </ol>
</template>

<script setup lang="ts">
import { CH3_EQ, type Ch3EqName } from '../config/ch3Eqs'
import { mediaUrl } from '../config/media'

const ROWS: { eq: Ch3EqName; alt: string; gloss: string }[] = [
  {
    eq: 'cm',
    alt: 'N_ij = lakes of true class i predicted as j; TP_c = N_cc, FP_c = Σ_{i≠c} N_ic, FN_c = Σ_{j≠c} N_cj',
    gloss: 'The confusion matrix the RESULTS beats show (Fig. B3): rows are the human label, columns the model’s prediction, <i>N</i> lakes in the split, <i>K</i> classes (5, or 4 with HF and MD merged). A class’s true positives sit on the diagonal; its false positives are the rest of its column, its false negatives the rest of its row.',
  },
  {
    eq: 'acc',
    alt: 'A = (1/N) Σ_c N_cc',
    gloss: 'Accuracy: the diagonal’s share of all lakes (Table B2, <i>A</i>). On an imbalanced split it rewards the big classes, which is why the paper selects and reports on macro-<i>F</i><sub>1</sub> instead.',
  },
  {
    eq: 'prec',
    alt: 'P_c = TP_c / (TP_c + FP_c)',
    gloss: 'Precision of class <i>c</i>: of the lakes the model called <i>c</i>, the fraction that were.',
  },
  {
    eq: 'rec',
    alt: 'R_c = TP_c / (TP_c + FN_c)',
    gloss: 'Recall of class <i>c</i>: of the lakes that were <i>c</i>, the fraction the model found.',
  },
  {
    eq: 'f1c',
    alt: 'F_1,c = 2 P_c R_c / (P_c + R_c) = 2 TP_c / (2 TP_c + FP_c + FN_c)',
    gloss: 'The per-class <i>F</i><sub>1</sub>: the harmonic mean of precision and recall, so both are penalised at once (Appendix B).',
  },
  {
    eq: 'macro',
    alt: 'P = (1/K) Σ P_c, R = (1/K) Σ R_c, F_1 = (1/K) Σ F_1,c',
    gloss: 'Macro-averaging: every drainage mechanism counts the same whatever its population. Model selection is by the best validation macro-<i>F</i><sub>1</sub> (epoch 189 five-class, 363 four-class); the train and validation numbers are reported at that epoch and the test split is scored once, there, at the end of training. Table B2’s <i>P</i> and <i>R</i> are these macro averages.',
  },
  {
    eq: 'floor',
    alt: 'F_1 random = 1/K (0.20 five-class, 0.25 four-class)',
    gloss: 'The dashed “random” line on the training curves: a classifier with no skill (uniform guesses, or any fixed prediction) scores macro-<i>F</i><sub>1</sub> = 1/<i>K</i> in expectation.',
  },
  {
    eq: 'softmax',
    alt: 'p_c(x) = exp z_c / Σ_k exp z_k',
    gloss: 'The classification head emits one logit <i>z</i><sub>c</sub> per class; a softmax turns them into the class probabilities the MODEL beats show (Sect. 4.3). The loss is applied to the logits directly.',
  },
  {
    eq: 'wc',
    alt: 'w_c = N_train / (K n_c), N_train = 600',
    gloss: 'Class weights by inverse frequency within the training split, <i>n</i><sub>c</sub> the class’s training count (Appendix B): the rare classes (ND, CD) weigh more, the common ones (HF, MD, LD) less. Recomputed for the four-class taxonomy, not summed from the five-class values.',
  },
  {
    eq: 'loss',
    alt: 'L = − Σ_i w_{y_i} log p_{y_i}(x_i) / Σ_i w_{y_i}',
    gloss: 'The training loss (Table B1): the weighted cross-entropy of each lake’s true class <i>y</i><sub>i</sub>, averaged over the batch with the weights (PyTorch’s weighted mean). Adam, peak learning rate 10<sup>−4</sup>, weight decay 10<sup>−5</sup>, 400 epochs, effective batch 8, a ten-epoch linear warm-up then cosine decay to 10<sup>−6</sup>.',
  },
  {
    eq: 'kappa',
    alt: 'κ = (p_o − p_e)/(1 − p_e), p_o = (1/N) Σ_c N_cc, p_e = Σ_c (N_c·/N)(N_·c/N)',
    gloss: 'The inter-rater agreement behind the LABELS beats, Cohen’s <i>κ</i> between two labelers over the 200-lake subset: the observed agreement <i>p</i><sub>o</sub> corrected for the agreement <i>p</i><sub>e</sub> their class frequencies would give by chance (<i>κ</i><sub>1,2</sub> = 0.744, <i>κ</i><sub>1,3</sub> = 0.781, <i>κ</i><sub>2,3</sub> = 0.738; Fleiss’s <i>κ</i> over all three 0.754).',
  },
]

function eqUrl(name: Ch3EqName): string {
  return mediaUrl(`ch03/eq/${name}.svg`)
}
/** The TeX box at --eqk CSS px per bp (width + aspect; a wide line clamps to the column). */
function box(name: Ch3EqName) {
  const b = CH3_EQ[name]
  return { width: `calc(${b.w} * var(--eqk))`, aspectRatio: `${b.w} / ${b.h}` }
}
</script>

<style scoped>
.sp-root {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: calc(11 * var(--eqk));
}
.sp-row {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.3rem;
}
.sp-eq {
  display: block;
  flex: 0 0 auto;
  max-width: 100%;
  height: auto;
  user-select: none;
}
.sp-gloss {
  margin: 0;
  max-width: 52rem;
  font-size: 0.95rem;
  line-height: 1.4;
  color: #cfc9bd;
}
.sp-gloss :deep(i) { font-family: 'EB Garamond', serif; font-size: 1.12em; }
.sp-gloss :deep(sub),
.sp-gloss :deep(sup) { font-size: 0.72em; }
</style>
