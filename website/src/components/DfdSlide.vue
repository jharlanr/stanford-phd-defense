<template>
  <!-- The FLASH SLIDE (APS DFD Interact: one slide, two minutes). A small
       title block; the two cartoons — blistering, then sliding — drawn
       as objects on the dark page (DfdCartoons.vue); under them the one
       equation, the paper's closed form for the radial stress (SI Eq.
       34a, τ̄_rr — on the flow line that is τ̄_xx; the main text's Eq. 2
       is its Cauchy combination 2τ̄_rr + τ̄_θθ) with its two scales. The
       same component is exported to PDF/PNG for the room laptop
       (tools/dfd-export.mjs, `?print=1` hides the site's chrome). The
       abstract waits behind a pill; never on screen by default. -->
  <div class="sl">
    <header class="sl-head">
      <img class="sl-logo" :src="logoUrl" alt="APS Division of Fluid Dynamics · DFD 2026" />
      <div class="sl-titles">
        <h1 class="sl-title">{{ DFD_TITLE }}</h1>
        <p class="sl-authors">
          <template v-for="(a, i) in DFD_AUTHORS" :key="a.name"><b v-if="a.presenter">{{ a.name }}</b><span v-else>{{ a.name }}</span><sup>{{ a.aff }}</sup><span v-if="i < DFD_AUTHORS.length - 1">, </span></template>
          <span class="sl-affil"><template v-for="(f, i) in DFD_AFFILIATIONS" :key="f"><sup>{{ i + 1 }}</sup>{{ f }}<span v-if="i < DFD_AFFILIATIONS.length - 1"> · </span></template></span>
        </p>
      </div>
      <div class="sl-meta">
        <p class="sl-eyebrow">{{ DFD_MEETING.meeting }} · {{ DFD_MEETING.format }}<br />{{ DFD_MEETING.session }}</p>
        <button class="sl-pill" :class="{ 'sl-pill-on': abstractOn }" @click="abstractOn = !abstractOn">Abstract</button>
      </div>
    </header>

    <div class="sl-body">
      <div class="sl-pair">
        <figure class="sl-fig">
          <DfdCartoons kind="blister" />
          <figcaption><b>hours</b> · blistering · tension above the blister</figcaption>
        </figure>
        <span class="sl-arrow" aria-hidden="true">→</span>
        <figure class="sl-fig">
          <DfdCartoons kind="sliding" />
          <figcaption><b>days</b> · sliding · tension upstream, compression downstream</figcaption>
        </figure>
      </div>

      <div class="sl-eqs">
        <DfdEq name="slide_s2" :k="KE" :inline="false" class="sl-eq-main" />
        <div class="sl-eq-side">
          <DfdEq name="scales" :k="KS" :inline="false" />
          <DfdEq name="slide_defs" :k="KS * 0.86" :inline="false" />
        </div>
      </div>
    </div>

    <Transition name="sl-fade">
      <div v-if="abstractOn" class="sl-abstract" role="dialog" aria-label="Abstract" @click="abstractOn = false">
        <div class="sl-abstract-card">
          <p class="sl-abstract-k">Abstract</p>
          <p>{{ DFD_ABSTRACT }}</p>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import DfdEq from './DfdEq.vue'
import DfdCartoons from './DfdCartoons.vue'
import {
  DFD_ABSTRACT,
  DFD_AFFILIATIONS,
  DFD_AUTHORS,
  DFD_LOGO_KEY,
  DFD_MEETING,
  DFD_TITLE,
} from '../config/dfd'
import { mediaUrl } from '../config/media'

const logoUrl = mediaUrl(DFD_LOGO_KEY)
const abstractOn = ref(false)
/** px per bp, with the viewport (the room's 1920 px screen reads at 3;
 *  a 1440 px laptop at 2.25): the solution, the scales beside it. */
const vw = ref(typeof window === 'undefined' ? 1920 : window.innerWidth)
function onResize(): void {
  vw.value = window.innerWidth
}
onMounted(() => window.addEventListener('resize', onResize))
onBeforeUnmount(() => window.removeEventListener('resize', onResize))
const KE = computed(() => Math.min(3.2, Math.max(2.1, vw.value / 620)))
const KS = computed(() => KE.value * 0.88)
</script>

<style scoped>
.sl {
  position: relative;
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 1vh;
  padding: 0 1.6vw 2.2vh;
  box-sizing: border-box;
  color: #f5f0e6;
  font-family: 'Inter', system-ui, sans-serif;
}

/* ── the title block: small, one band ── */
.sl-head {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 1.6vw;
  padding-bottom: 0.8vh;
  border-bottom: 1px solid rgba(232, 185, 74, 0.25);
}
.sl-logo {
  display: block;
  width: 10.5vw;
  max-width: 200px;
  height: auto;
}
.sl-titles { min-width: 0; }
.sl-title {
  margin: 0;
  font-family: 'EB Garamond', Georgia, serif;
  font-weight: 500;
  font-size: clamp(1.25rem, 1.85vw, 2.1rem);
  line-height: 1.15;
  color: var(--gold-bright);
  text-wrap: balance;
}
.sl-authors {
  margin: 0.35rem 0 0;
  font-size: clamp(0.72rem, 0.92vw, 1rem);
  line-height: 1.45;
  color: rgba(245, 240, 230, 0.9);
}
.sl-authors b { color: #fff; font-weight: 700; }
.sl-authors sup { font-size: 0.62em; color: var(--gold); margin-left: 1px; }
.sl-affil {
  display: block;
  color: rgba(245, 240, 230, 0.62);
  font-size: 0.92em;
}
.sl-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 0.5rem; }
.sl-eyebrow {
  margin: 0;
  text-align: right;
  color: var(--gold-dim);
  font-size: clamp(0.62rem, 0.78vw, 0.84rem);
  line-height: 1.4;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.sl-pill {
  border: 1px solid var(--gold-dim);
  background: rgba(8, 6, 4, 0.78);
  color: var(--gold-dim);
  font: 500 0.72rem/1 'Inter', system-ui, sans-serif;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.45rem 0.85rem;
  border-radius: 999px;
  cursor: pointer;
}
.sl-pill:hover, .sl-pill-on { color: #1c1305; background: var(--gold); border-color: var(--gold-bright); }

/* ── the body: the cartoons, then the equation ── */
.sl-body {
  display: grid;
  grid-template-rows: auto auto;
  align-content: space-evenly;
  justify-items: center;
  row-gap: 1vh;
  min-height: 0;
}
.sl-pair {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  column-gap: 1vw;
  width: min(100%, 94vw);
}
.sl-fig { margin: 0; min-width: 0; }
.sl-fig figcaption {
  margin-top: 0.1vh;
  text-align: center;
  font-size: clamp(0.82rem, 1.05vw, 1.2rem);
  color: rgba(245, 240, 230, 0.82);
  letter-spacing: 0.02em;
}
.sl-fig figcaption b { color: var(--gold); font-weight: 600; }
.sl-arrow {
  font-family: 'EB Garamond', Georgia, serif;
  font-size: clamp(2rem, 3.4vw, 4rem);
  color: var(--gold-bright);
  line-height: 1;
  padding-bottom: 2.2vh;
}
.sl-eqs {
  display: flex;
  align-items: center;
  gap: 2.6vw;
  padding: 1.2vh 2vw;
  border: 1px solid rgba(232, 185, 74, 0.22);
  border-radius: 14px;
  background: rgba(8, 6, 4, 0.5);
}
.sl-eq-side { display: flex; flex-direction: column; align-items: flex-start; gap: 1.2vh; }

.sl-abstract {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.72);
  cursor: pointer;
  z-index: 3;
}
.sl-abstract-card {
  max-width: min(60rem, 80vw);
  padding: 2rem 2.4rem;
  border: 1.5px solid var(--gold);
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(30, 24, 12, 0.985), rgba(10, 8, 5, 0.985));
  box-shadow: 0 14px 40px rgba(0, 0, 0, 0.8);
}
.sl-abstract-k {
  margin: 0 0 0.6rem;
  color: var(--gold);
  font-size: 0.8rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}
.sl-abstract-card p:last-child {
  margin: 0;
  font-family: 'EB Garamond', Georgia, serif;
  font-size: clamp(1rem, 1.35vw, 1.45rem);
  line-height: 1.45;
  color: #f5f0e6;
}
.sl-fade-enter-active, .sl-fade-leave-active { transition: opacity 0.25s; }
.sl-fade-enter-from, .sl-fade-leave-to { opacity: 0; }
</style>
