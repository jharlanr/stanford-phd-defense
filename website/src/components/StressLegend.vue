<template>
  <!-- Ch.1 beat 3's τxx colour scale: a HORIZONTAL
       bar centred beneath the greenland object, in the Introduction's
       colour-scale style (VelocityColorbar: EB Garamond title, Inter unit
       + ticks, no card, no parameter line), keeping the paint's RdBu_r.
       The model credit is a bottom-right corner link to the References
       page's Chapter 1 group (the Introduction's corner-link pattern). -->
  <Transition name="scb-fade">
    <div v-if="visible" class="scb-layer">
      <div class="scb" aria-label="Deviatoric stress colour scale">
        <div class="scb-head">
          <span class="scb-title">Deviatoric stress τ<sub>xx</sub></span>
          <span class="scb-unit">kPa</span>
        </div>
        <div class="scb-body">
          <div class="scb-bar" :style="{ background: GRADIENT }"></div>
          <div
            v-for="t in TICKS"
            :key="t.v"
            class="scb-tick"
            :style="{ left: t.pct + '%' }"
          >
            <span class="scb-mark"></span>
            <span class="scb-label">{{ t.label }}</span>
          </div>
        </div>
      </div>
      <router-link class="corner-link" :to="REFS_LINK">[Elmer/Ice · Gagliardini et al. 2013]</router-link>
    </div>
  </Transition>
</template>

<script setup lang="ts">
defineProps<{
  /** True while the τxx paint is on the cross-section (beat 3). */
  visible: boolean
}>()

// The paint's scale (cinematic/scene_ch01/build_theory_n1.py: RdBu_r,
// ±VMAX_KPA = 250): matplotlib's RdBu_r sampled at 0, 0.1, … 1 — blue =
// compression (left), red = tension (right).
const VMAX_KPA = 250
const RDBU_R = [
  '#053061', '#2065ab', '#4393c3', '#90c4dd', '#d1e5f0', '#f7f6f6',
  '#fddbc7', '#f3a481', '#d6604d', '#b1182b', '#67001f',
]
const GRADIENT = `linear-gradient(to right, ${RDBU_R.map((c, i) => `${c} ${i * 10}%`).join(', ')})`
const TICKS = [-1, -0.5, 0, 0.5, 1].map((f) => {
  const v = Math.round(f * VMAX_KPA)
  return { v, pct: (f + 1) * 50, label: v > 0 ? `+${v}` : v < 0 ? `−${-v}` : '0' }
})

const REFS_LINK = { path: '/references', query: { chapter: 'chapter1' } }
</script>

<style scoped>
.scb-layer {
  position: absolute;
  inset: 0;
  z-index: 8;
  pointer-events: none;
}

/* Centred beneath the object: the beat-3 framing leaves the lower ~third
   of the frame black under the cut slab at every aspect. */
.scb {
  position: absolute;
  left: 50%;
  bottom: clamp(56px, 10vh, 130px);
  transform: translateX(-50%);
  color: #f2efe6;
  font-family: 'Inter', system-ui, sans-serif;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.85);
  user-select: none;
}

.scb-head {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 0.6em;
  margin-bottom: clamp(10px, 1.3vh, 18px);
  white-space: nowrap;
}
.scb-title {
  font-family: 'EB Garamond', Georgia, serif;
  font-size: clamp(1.35rem, 1.75vw, 2.1rem);
  line-height: 1.05;
  letter-spacing: 0.01em;
}
.scb-title sub {
  font-size: 0.62em;
  line-height: 0;
}
.scb-unit {
  font-size: clamp(0.95rem, 1.1vw, 1.3rem);
  opacity: 0.95;
}

.scb-body {
  position: relative;
  width: clamp(320px, 30vw, 580px);
  height: clamp(18px, 1.5vw, 28px);
  /* room for the tick marks + labels hanging below the bar */
  margin-bottom: calc(10px + clamp(1rem, 1.2vw, 1.45rem) + 6px);
}
.scb-bar {
  position: absolute;
  inset: 0;
  border-radius: 2px;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.55), 0 2px 10px rgba(0, 0, 0, 0.5);
}
.scb-tick {
  position: absolute;
  top: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  transform: translateX(-50%);
}
.scb-mark {
  display: block;
  width: 2px;
  height: 8px;
  background: #f2efe6;
  box-shadow: 0 0 2px rgba(0, 0, 0, 0.8);
}
.scb-label {
  margin-top: 6px;
  font-size: clamp(1rem, 1.2vw, 1.45rem);
  font-variant-numeric: tabular-nums;
  line-height: 1;
  white-space: nowrap;
}

/* Bottom-right reference link — the Introduction's corner-link. */
.corner-link {
  position: absolute;
  right: 2vw;
  bottom: 2.2vh;
  pointer-events: auto;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1.05rem;
  letter-spacing: 0.04em;
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px dotted rgba(108, 204, 255, 0.6);
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.8);
}
.corner-link:hover {
  color: #fff;
  border-bottom-color: rgba(255, 255, 255, 0.7);
}

.scb-fade-enter-active {
  transition: opacity 1.2s ease 0.3s;
}
.scb-fade-leave-active {
  transition: opacity 0.6s ease;
}
.scb-fade-enter-from,
.scb-fade-leave-to {
  opacity: 0;
}
</style>
