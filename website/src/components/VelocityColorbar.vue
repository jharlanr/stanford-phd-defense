<template>
  <!-- The Introduction's colour scale, left of the object. Figure labels
       only (the narrator rule): title, unit, tick values, legend chips.
       "Greenland flows" and the seasons' speed step: the speed scale of the
       drape (config/velocityScale.ts — the same stops the drape was baked
       with). The seasons' anomaly step: the diverging scale of the anomaly, its
       stops from the bake's manifest (never typed here), and the grey chip
       for "no monthly signal". Never both at once — they crossfade. -->
  <Transition name="vcb-fade" mode="out-in">
    <div v-if="visible && !anomaly" key="speed" class="vcb" aria-label="Surface speed colour scale">
      <div class="vcb-title">Surface speed</div>
      <div class="vcb-unit">m yr<sup>−1</sup></div>
      <div class="vcb-body">
        <div class="vcb-cap" :style="{ borderBottomColor: topColor }"></div>
        <div class="vcb-bar" :style="{ background: gradient }"></div>
        <div class="vcb-ticks">
          <div
            v-for="t in ticks"
            :key="t.v"
            class="vcb-tick"
            :style="{ bottom: t.pct + '%' }"
          >
            <span class="vcb-mark"></span>
            <span class="vcb-label">{{ t.label }}</span>
          </div>
        </div>
        <!-- (the MONTHLY / MULTI-YEAR brackets are gone — the director
             found them unnecessary on the speed card and asked for them
             to go) -->
      </div>
    </div>
    <div v-else-if="visible && anomaly" key="anom" class="vcb" aria-label="Speed anomaly colour scale">
      <div class="vcb-title">Speed vs usual</div>
      <div class="vcb-unit">%</div>
      <div class="vcb-word">faster</div>
      <div class="vcb-body">
        <div class="vcb-bar" :style="{ background: anomGradient }"></div>
        <div class="vcb-ticks">
          <div
            v-for="t in anomTicks"
            :key="t.v"
            class="vcb-tick"
            :style="{ bottom: t.pct + '%' }"
          >
            <span class="vcb-mark"></span>
            <span class="vcb-label">{{ t.label }}</span>
          </div>
        </div>
      </div>
      <div class="vcb-word vcb-word-low">slower</div>
      <div class="vcb-chip">
        <i :style="{ background: greyCss }"></i>
        <span>no monthly signal</span>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { speedGradientStops, speedTicks, speedToFrac } from '../config/velocityScale'
import { anomalyGradient } from '../config/seasons'
import palette from '../config/velocityPalette.json'

const props = defineProps<{
  visible: boolean
  /** The seasons' anomaly scale (from the manifest); null = the speed scale. */
  anomaly?: { stops: [number, string][]; lim: number; grey: number } | null
}>()

// Bottom = slow, top = fast.
const gradient = `linear-gradient(to top, ${speedGradientStops()})`
const stops = palette.stops as [number, string][]
const topColor = stops[stops.length - 1][1]
const ticks = speedTicks().map((v) => ({
  v,
  pct: speedToFrac(v) * 100,
  label: v.toLocaleString('en-US'),
}))

const anomGradient = computed(() =>
  props.anomaly ? `linear-gradient(to top, ${anomalyGradient(props.anomaly.stops)})` : 'none',
)
const anomTicks = computed(() => {
  const lim = props.anomaly?.lim ?? 50
  const out: { v: number; pct: number; label: string }[] = []
  for (const f of [-1, -0.5, 0, 0.5, 1]) {
    const v = Math.round(f * lim)
    out.push({ v, pct: (f + 1) * 50, label: v > 0 ? `+${v}` : v < 0 ? `−${-v}` : '0' })
  }
  return out
})
const greyCss = computed(() => {
  const g = Math.round((props.anomaly?.grey ?? 0.3) * 255)
  return `rgb(${g}, ${g}, ${g})`
})
</script>

<style scoped>
.vcb {
  position: fixed;
  left: clamp(20px, 3.2vw, 64px);
  top: 50%;
  transform: translateY(-42%);
  z-index: 30;
  pointer-events: none;
  color: #f2efe6;
  font-family: 'Inter', system-ui, sans-serif;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.85);
  user-select: none;
}
.vcb-title {
  font-family: 'EB Garamond', Georgia, serif;
  font-size: clamp(1.35rem, 1.75vw, 2.1rem);
  line-height: 1.05;
  letter-spacing: 0.01em;
  white-space: nowrap;
}
.vcb-unit {
  font-size: clamp(0.95rem, 1.1vw, 1.3rem);
  opacity: 0.95;
  margin: 0.2em 0 0.9em;
}
.vcb-unit sup {
  font-size: 0.7em;
}
.vcb-body {
  position: relative;
  height: clamp(220px, 40vh, 520px);
  width: clamp(18px, 1.5vw, 28px);
  margin-top: clamp(10px, 1.3vh, 18px);
}
.vcb-bar {
  position: absolute;
  inset: 0;
  border-radius: 2px;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.55), 0 2px 10px rgba(0, 0, 0, 0.5);
}
/* Saturation cap: speeds above the top tick draw the top colour. */
.vcb-cap {
  position: absolute;
  left: 0;
  bottom: 100%;
  width: 0;
  height: 0;
  border-left: calc(clamp(18px, 1.5vw, 28px) / 2) solid transparent;
  border-right: calc(clamp(18px, 1.5vw, 28px) / 2) solid transparent;
  border-bottom: clamp(10px, 1.3vh, 18px) solid;
  filter: drop-shadow(0 -1px 0 rgba(0, 0, 0, 0.55));
}
.vcb-ticks {
  position: absolute;
  left: 100%;
  top: 0;
  bottom: 0;
}
.vcb-tick {
  position: absolute;
  left: 0;
  display: flex;
  align-items: center;
  transform: translateY(50%);
}
.vcb-mark {
  display: block;
  width: 8px;
  height: 2px;
  background: #f2efe6;
  box-shadow: 0 0 2px rgba(0, 0, 0, 0.8);
}
.vcb-label {
  margin-left: 8px;
  font-size: clamp(1rem, 1.2vw, 1.45rem);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}
/* The seasons' brackets, right of the tick labels. */
.vcb-word {
  font-size: clamp(0.95rem, 1.1vw, 1.25rem);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(242, 239, 230, 0.92);
  margin-bottom: -0.2rem;
}
.vcb-word-low {
  margin: clamp(8px, 1.1vh, 14px) 0 0;
}
.vcb-chip {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: clamp(14px, 2vh, 24px);
  font-size: clamp(0.95rem, 1.1vw, 1.25rem);
  color: rgba(242, 239, 230, 0.92);
  white-space: nowrap;
}
.vcb-chip i {
  display: inline-block;
  width: clamp(18px, 1.5vw, 28px);
  height: 14px;
  border-radius: 2px;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.55);
}
.vcb-fade-enter-active {
  transition: opacity 1.2s ease 0.3s;
}
.vcb-fade-leave-active {
  transition: opacity 0.6s ease;
}
.vcb-fade-enter-from,
.vcb-fade-leave-to {
  opacity: 0;
}
</style>
