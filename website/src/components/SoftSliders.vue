<template>
  <!-- lakelabel's five class sliders and the soft label they make (the five
       sum to at most 1), shared by Chapter 3's "a label made live" and the
       "Label lakes yourself" door. The director asked that the sliders
       snap to quarters with ticks, as lakelabel's do, and wear their class
       colours in every engine (they are drawn here, not left to
       accent-color: Chromium gives a DARK accent colour a white unfilled
       track — ND and CD). Two root nodes on purpose: they sit straight in
       the parent's column, so its gap spaces them. -->
  <div class="ld-rows">
    <div
      v-for="c in ESSD_CLASSES"
      :key="c.code"
      class="ld-row"
      :style="{ '--acc': c.color, '--fill': `${modelValue[c.code]}%` }"
    >
      <span class="ld-chip" />
      <span class="ld-code">{{ c.code }}</span>
      <span class="ld-name">{{ c.name }}</span>
      <!-- lakelabel's slider: 0–1 in quarters, a tick at each -->
      <div class="ld-slider">
        <input
          type="range" :min="0" :max="100" :step="SOFT_STEP"
          :value="modelValue[c.code]"
          :disabled="disabled"
          :aria-label="c.name"
          @input="onInput(c.code, $event)"
        />
        <div class="ld-ticks" aria-hidden="true">
          <span
            v-for="t in SOFT_TICKS"
            :key="t"
            class="ld-tick-mark"
            :class="{ 'ld-tick-on': t <= modelValue[c.code] }"
            :style="{ left: t + '%' }"
          />
        </div>
        <div class="ld-tick-lbls" aria-hidden="true">
          <span v-for="t in SOFT_TICKS" :key="`l-${t}`" :style="{ left: t + '%' }">{{ t }}</span>
        </div>
      </div>
      <span class="ld-val">{{ modelValue[c.code] }}%</span>
    </div>
  </div>

  <!-- the soft label (the five sum to at most 1) + its sum -->
  <div class="ld-sum-row">
    <div class="ld-bar">
      <span
        v-for="c in ESSD_CLASSES"
        :key="`b-${c.code}`"
        class="ld-bar-seg"
        :style="{ width: modelValue[c.code] + '%', background: c.color }"
      />
    </div>
    <span class="ld-sum" :class="{ 'ld-sum-full': total === 100 }">{{ total }}%</span>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { ESSD_CLASSES, SOFT_STEP, SOFT_TICKS, clampSoft, softTotal, type SoftRaw } from '../config/essdLabel'

const props = defineProps<{ modelValue: SoftRaw; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [raw: SoftRaw] }>()

const total = computed(() => softTotal(props.modelValue))

// The label as last emitted: two inputs inside one tick (before the parent
// re-renders the prop) must each see the other's value.
let latest: SoftRaw = props.modelValue
watch(() => props.modelValue, (v) => { latest = v })

function onInput(code: string, e: Event): void {
  const el = e.target as HTMLInputElement
  const v = clampSoft(latest, code, parseInt(el.value, 10) || 0)
  if (String(v) !== el.value) el.value = String(v)
  latest = { ...latest, [code]: v }
  emit('update:modelValue', latest)
}
</script>

<style scoped>
.ld-rows { display: flex; flex-direction: column; gap: 0.35rem; }
/* The name column and row type size are variables so a denser page can
   tighten them; Chapter 3's demo uses the defaults. */
.ld-row {
  display: grid;
  grid-template-columns: 16px 2.4rem var(--ld-name-w, 11rem) 1fr 3.6rem;
  align-items: center;
  gap: 0.7rem;
  font-size: var(--ld-row-fs, 1.05rem);
}
.ld-chip { width: 16px; height: 16px; border-radius: 4px; background: var(--acc); }
.ld-code { font-weight: 700; letter-spacing: 0.04em; color: var(--acc); }
.ld-name { color: rgba(245, 240, 230, 0.9); white-space: nowrap; }
/* ── the class sliders, drawn by hand in every engine ──
   The thumb is 18 px, so its CENTRE runs from 9 px to (width − 9 px):
   the ticks and their labels sit on that same inset line. */
.ld-slider {
  position: relative;
  height: 44px;
  --thumb: 18px;
}
.ld-slider input[type='range'] {
  -webkit-appearance: none;
  appearance: none;
  position: absolute;
  left: 0;
  right: 0;
  top: 4px;
  width: 100%;
  height: 22px;
  margin: 0;
  background: transparent;
  cursor: pointer;
  z-index: 2;
}
.ld-slider input[type='range']:disabled { cursor: default; }
.ld-slider input[type='range']:focus { outline: none; }
.ld-slider input[type='range']::-webkit-slider-runnable-track {
  height: 6px;
  border-radius: 3px;
  background: linear-gradient(to right,
    var(--acc) 0, var(--acc) var(--fill),
    rgba(245, 240, 230, 0.14) var(--fill), rgba(245, 240, 230, 0.14) 100%);
}
.ld-slider input[type='range']::-moz-range-track {
  height: 6px;
  border-radius: 3px;
  background: rgba(245, 240, 230, 0.14);
}
.ld-slider input[type='range']::-moz-range-progress {
  height: 6px;
  border-radius: 3px;
  background: var(--acc);
}
.ld-slider input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: var(--thumb);
  height: var(--thumb);
  margin-top: -6px; /* (6 − 18) / 2 */
  border-radius: 50%;
  background: var(--acc);
  border: 2px solid #0d0b09;
  box-shadow: 0 0 0 1px var(--acc);
}
.ld-slider input[type='range']::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--acc);
  border: 2px solid #0d0b09;
  box-shadow: 0 0 0 1px var(--acc);
}
.ld-slider input[type='range']:focus-visible::-webkit-slider-thumb {
  box-shadow: 0 0 0 1px var(--acc), 0 0 0 4px rgba(245, 240, 230, 0.25);
}
.ld-ticks,
.ld-tick-lbls {
  position: absolute;
  left: calc(var(--thumb) / 2);
  right: calc(var(--thumb) / 2);
  pointer-events: none;
}
.ld-ticks { top: 15px; height: 0; z-index: 1; }
.ld-tick-mark {
  position: absolute;
  top: -7px; /* a notch through the track: 5 px above and below it */
  width: 2px;
  height: 14px;
  margin-left: -1px;
  border-radius: 1px;
  background: rgba(245, 240, 230, 0.32);
}
.ld-tick-mark.ld-tick-on { background: var(--acc); }
.ld-tick-lbls { top: 29px; height: 12px; }
.ld-tick-lbls span {
  position: absolute;
  transform: translateX(-50%);
  font-size: 0.66rem;
  line-height: 1;
  color: rgba(245, 240, 230, 0.45);
  font-variant-numeric: tabular-nums;
}
.ld-val { text-align: right; font-variant-numeric: tabular-nums; color: rgba(245, 240, 230, 0.75); }

.ld-sum-row {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
.ld-sum-row .ld-bar { flex: 1 1 auto; }
.ld-sum {
  min-width: 3.6rem;
  text-align: right;
  font-variant-numeric: tabular-nums;
  color: rgba(245, 240, 230, 0.5);
}
.ld-sum.ld-sum-full { color: var(--gold-bright); }
.ld-bar {
  display: flex;
  height: 14px;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.06);
}
.ld-bar-seg { display: block; height: 100%; transition: width 0.2s; }
</style>
