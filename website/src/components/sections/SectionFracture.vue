<template>
  <!-- Additional Work → fracture / stream mapping.
       The AGU 2024 poster Iona Xia led. A flat page above the live globe
       (the Terminal-Bench pattern), ONE screen, two visuals and ONE
       interaction: play / scrub the training visualisation. The
       whole-scene loop rides the same play button. Nothing plays until
       clicked; both videos are silent. Figures and labels only, no
       narration (the site-wide rule: the presenter narrates). Facts and
       links: config/fracture.ts. -->
  <div class="fx-root">
    <header class="fx-head">
      <button class="fx-pill fx-pill-dim fx-exit" @click="emit('exit')">← doors</button>
      <div class="fx-titles">
        <p class="fx-eyebrow">{{ FRACTURE.venue }} · {{ FRACTURE.poster }}</p>
        <h2 class="fx-title">{{ FRACTURE.title }}</h2>
        <p class="fx-authors">
          <template v-for="(a, ai) in FRACTURE.authors" :key="a"><b v-if="a === FRACTURE.boldAuthor">{{ a }}</b><span v-else>{{ a }}</span><span v-if="ai < FRACTURE.authors.length - 1">, </span></template>
        </p>
      </div>
    </header>

    <div class="fx-grid">
      <!-- The hero: the training visualisation with its scrub row. -->
      <figure class="fx-hero">
        <div class="fx-frame fx-frame-sq" @click="togglePlay">
          <video
            ref="heroEl"
            class="fx-video"
            :src="FRACTURE_TRAINING.video"
            :poster="FRACTURE_TRAINING.poster"
            muted
            playsinline
            preload="metadata"
            :aria-label="`Fractures (red) and streams (blue) mapped over training. ${FRACTURE.credit}`"
            @loadedmetadata="onMeta"
            @timeupdate="onTime"
            @play="playing = true"
            @pause="playing = false"
            @ended="onEnded"
          />
          <span v-if="!started" class="fx-play"><span class="fx-play-tri">▶</span></span>
          <span class="fx-tag">{{ FRACTURE_TRAINING.panel }}</span>
        </div>
        <div class="fx-meta">
          <button class="fx-play-btn" :aria-label="playing ? 'Pause' : 'Play'" @click="togglePlay">{{ playing ? '❚❚' : '▶' }}</button>
          <span class="fx-meta-label">{{ FRACTURE_TRAINING.label }}</span>
          <input
            class="fx-scrub"
            type="range"
            min="0"
            :max="duration || 0"
            step="0.02"
            :value="time"
            :style="{ '--fill': `${duration ? (100 * time) / duration : 0}%` }"
            aria-label="Scrub through training"
            @input="onScrub"
          />
        </div>
      </figure>

      <aside class="fx-right">
        <figure class="fx-scene">
          <div class="fx-frame fx-frame-scene" @click="togglePlay">
            <video
              ref="sceneEl"
              class="fx-video"
              :src="FRACTURE_SCENE.video"
              :poster="FRACTURE_SCENE.poster"
              muted
              loop
              playsinline
              preload="metadata"
              :aria-label="`One whole scene, then its fracture map (red) and stream map (blue). ${FRACTURE.credit}`"
            />
            <span class="fx-tag">{{ FRACTURE_SCENE.panel }}</span>
          </div>
        </figure>

        <div class="fx-legend">
          <span v-for="c in FRACTURE_CLASSES" :key="c.name" class="fx-key">
            <i class="fx-swatch" :style="{ background: c.color }" />{{ c.name }}
          </span>
          <span class="fx-imagery">{{ FRACTURE.imagery }}</span>
        </div>

        <div class="fx-tiles">
          <div v-for="t in FRACTURE_TILES" :key="t.label" class="fx-tile">
            <span class="fx-tile-n">{{ t.value }}</span>
            <span class="fx-tile-l">{{ t.label }}</span>
          </div>
        </div>

        <div class="fx-doors">
          <a
            v-for="d in FRACTURE_LINKS"
            :key="d.href"
            class="fx-pill"
            :class="{ 'fx-pill-primary': d.primary }"
            :href="d.href"
            target="_blank"
            rel="noopener noreferrer"
          >{{ d.label }} ↗</a>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  FRACTURE,
  FRACTURE_CLASSES,
  FRACTURE_LINKS,
  FRACTURE_SCENE,
  FRACTURE_TILES,
  FRACTURE_TRAINING,
} from '../../config/fracture'

const emit = defineEmits<{ exit: [] }>()

const heroEl = ref<HTMLVideoElement | null>(null)
const sceneEl = ref<HTMLVideoElement | null>(null)
const playing = ref(false)
/** False until the first play: the posters (the finished maps) show. */
const started = ref(false)
const duration = ref(0)
const time = ref(0)

function onMeta(): void {
  duration.value = heroEl.value?.duration ?? 0
}
function onTime(): void {
  time.value = heroEl.value?.currentTime ?? 0
}

/** One button for the page: the hero plays once through and rests on
 *  its last frame; the whole-scene loop runs while it does. */
function togglePlay(): void {
  const hero = heroEl.value
  const scene = sceneEl.value
  if (!hero) return
  if (hero.paused) {
    if (hero.ended || (duration.value && hero.currentTime >= duration.value - 0.05)) {
      hero.currentTime = 0
      if (scene) scene.currentTime = 0
    }
    started.value = true
    void hero.play().catch(() => {})
    void scene?.play().catch(() => {})
  } else {
    hero.pause()
    scene?.pause()
  }
}

function onEnded(): void {
  playing.value = false
  sceneEl.value?.pause()
}

function onScrub(e: Event): void {
  const hero = heroEl.value
  if (!hero) return
  started.value = true
  hero.currentTime = Number((e.target as HTMLInputElement).value)
  time.value = hero.currentTime
}
</script>

<style scoped>
.fx-root {
  position: fixed;
  inset: 0;
  z-index: 1;
  overflow-y: auto;
  background: radial-gradient(ellipse at 28% 18%, #0f1420 0%, #050505 62%);
  color: #f5f5f5;
  font-family: 'Inter', system-ui, sans-serif;
  padding: 8.5vh 3vw 2.5vh;
  box-sizing: border-box;
  pointer-events: auto;
  /* The hero is a square sized by the HEIGHT left under the header, so
     the page holds one screen; the right column takes the rest. */
  --hero: clamp(300px, calc(100vh - 8.5vh - 2.5vh - 11.6rem), 44vw);
}

.fx-head {
  display: flex;
  align-items: flex-start;
  gap: 1.2rem;
  margin-bottom: 1.6vh;
}

.fx-exit {
  flex: none;
  margin-top: 0.2rem;
}

.fx-titles {
  flex: 1;
  min-width: 0;
}

.fx-eyebrow {
  margin: 0 0 0.15rem;
  color: var(--gold-dim);
  font-size: 0.8rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.fx-title {
  font-family: 'EB Garamond', serif;
  font-weight: 400;
  font-size: clamp(1.25rem, 1.95vw, 1.9rem);
  line-height: 1.12;
  color: var(--gold);
  margin: 0;
  letter-spacing: 0.01em;
  text-wrap: balance;
}

.fx-authors {
  margin: 0.35rem 0 0;
  font-size: 0.86rem;
  color: rgba(245, 245, 245, 0.72);
}

.fx-authors b {
  font-weight: 600;
  color: var(--gold-bright);
}

.fx-grid {
  display: grid;
  grid-template-columns: var(--hero) minmax(0, 1fr);
  gap: 2.2vw;
  align-items: stretch;
}

.fx-hero,
.fx-scene {
  margin: 0;
  min-width: 0;
}

.fx-hero {
  background: #050505;
  border: 1.5px solid var(--gold);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 10px 40px -12px rgba(232, 185, 74, 0.35);
}

.fx-frame {
  position: relative;
  width: 100%;
  background: #000;
  overflow: hidden;
  cursor: pointer;
}

.fx-frame-sq {
  aspect-ratio: 1 / 1;
}

.fx-frame-scene {
  aspect-ratio: 1280 / 820;
  border: 1px solid var(--gold-faint);
  border-radius: 12px;
  /* Never taller than what the legend, tiles and pills leave. */
  max-height: calc(var(--hero) + 2.4rem - 10.6rem);
  margin: 0 auto;
}

.fx-video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.fx-play {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 84px;
  height: 84px;
  border-radius: 50%;
  border: 2px solid var(--gold-bright);
  background: rgba(8, 6, 4, 0.72);
  color: var(--gold-bright);
  display: grid;
  place-items: center;
  pointer-events: none;
  transition: transform 0.2s, background 0.2s, box-shadow 0.2s;
  box-shadow: 0 0 30px rgba(245, 199, 94, 0.25);
}

.fx-frame:hover .fx-play {
  transform: translate(-50%, -50%) scale(1.06);
  background: rgba(56, 38, 12, 0.85);
  box-shadow: 0 0 44px rgba(245, 199, 94, 0.45);
}

.fx-play-tri {
  font-size: 1.9rem;
  padding-left: 0.3rem;
}

.fx-tag {
  position: absolute;
  left: 0.8rem;
  top: 0.7rem;
  font-size: 0.74rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--gold-bright);
  background: rgba(0, 0, 0, 0.72);
  padding: 0.22rem 0.55rem;
  border-radius: 999px;
  pointer-events: none;
}

/* The caption row — the fieldwork clip panel's: play/pause, label, scrub. */
.fx-meta {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  height: 2.4rem;
  box-sizing: border-box;
  padding: 0 0.75rem;
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  color: rgba(244, 207, 106, 0.88);
  border-top: 1px solid var(--gold-faint);
  text-transform: uppercase;
}

.fx-meta-label {
  white-space: nowrap;
  flex: none;
}

.fx-play-btn {
  flex: none;
  width: 1.7rem;
  height: 1.5rem;
  border: 1px solid var(--gold-faint);
  border-radius: 999px;
  background: transparent;
  color: var(--gold);
  font-size: 0.62rem;
  line-height: 1;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}

.fx-play-btn:hover {
  border-color: var(--gold);
  color: #fff;
}

.fx-scrub {
  flex: 1 1 auto;
  min-width: 80px;
  height: 14px;
  margin: 0;
  cursor: pointer;
  -webkit-appearance: none;
  appearance: none;
  background: transparent;
}

.fx-scrub::-webkit-slider-runnable-track {
  height: 3px;
  border-radius: 2px;
  background: linear-gradient(to right, var(--gold) var(--fill, 0%), rgba(245, 245, 245, 0.18) var(--fill, 0%));
}

.fx-scrub::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 11px;
  height: 11px;
  margin-top: -4px;
  border-radius: 50%;
  background: #fff8d8;
  border: 1.5px solid var(--gold);
  box-shadow: 0 0 5px rgba(0, 0, 0, 0.6);
}

.fx-scrub::-moz-range-track {
  height: 3px;
  border-radius: 2px;
  background: rgba(245, 245, 245, 0.18);
}

.fx-scrub::-moz-range-progress {
  height: 3px;
  border-radius: 2px;
  background: var(--gold);
}

.fx-scrub::-moz-range-thumb {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: #fff8d8;
  border: 1.5px solid var(--gold);
}

/* ---- right: the scene, the key, the numbers, the doors ---- */
.fx-right {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 0.9rem;
  min-width: 0;
}

.fx-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem 1.4rem;
  font-size: 0.86rem;
  color: #e2ded6;
}

.fx-key {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  white-space: nowrap;
}

.fx-swatch {
  display: inline-block;
  width: 1.5rem;
  height: 0.28rem;
  border-radius: 2px;
}

.fx-imagery {
  margin-left: auto;
  font-size: 0.76rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--gold-dim);
}

.fx-tiles {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.5rem;
}

.fx-tile {
  background: #050505;
  border: 1px solid var(--gold-faint);
  border-radius: 10px;
  padding: 0.6rem 0.4rem 0.55rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
}

.fx-tile-n {
  font-family: 'EB Garamond', serif;
  font-size: clamp(1.2rem, 1.8vw, 1.7rem);
  color: var(--gold);
  line-height: 1;
}

.fx-tile-l {
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #b9b4aa;
  text-align: center;
}

.fx-doors {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.fx-pill {
  border: 1px solid var(--gold);
  background: rgba(8, 6, 4, 0.78);
  color: var(--gold-bright);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.76rem;
  font-weight: 500;
  letter-spacing: 0.06em;
  padding: 0.42rem 0.9rem;
  border-radius: 999px;
  cursor: pointer;
  text-decoration: none;
  white-space: nowrap;
  transition: color 0.2s, background 0.2s, box-shadow 0.2s;
}

.fx-pill:hover {
  color: #fff8d8;
  background: rgba(56, 38, 12, 0.85);
}

.fx-pill-dim {
  border-color: var(--gold-dim);
  color: var(--gold-dim);
}

.fx-pill-dim:hover {
  color: var(--gold-bright);
}

.fx-pill-primary {
  color: #1c1305;
  background: var(--gold);
  box-shadow: 0 0 22px rgba(245, 199, 94, 0.25);
}

.fx-pill-primary:hover {
  color: #1c1305;
  background: var(--gold-bright);
}

/* Narrow: one column, the hero as wide as the page allows. */
@media (max-width: 1000px) {
  .fx-root {
    --hero: min(100%, 640px);
  }
  .fx-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .fx-hero {
    width: var(--hero);
    margin: 0 auto;
  }
  .fx-frame-scene {
    max-height: none;
  }
  .fx-head {
    flex-wrap: wrap;
  }
  .fx-tiles {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .fx-imagery {
    margin-left: 0;
  }
}
</style>
