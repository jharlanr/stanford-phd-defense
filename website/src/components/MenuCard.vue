<template>
  <button
    class="menu-card"
    :class="{ 'is-hovered': hovered }"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
    @focus="hovered = true"
    @blur="hovered = false"
    @click="$emit('select')"
  >
    <!-- Thumbnail fills the entire card; the title rides over the
         bottom with a gradient backdrop so the imagery is never blocked
         by a solid label bar. Every thumb runs all the time (the
         director wanted them dynamic but gentle, moving at all times); the
         veil keeps it quiet and grey until the card is hovered, when it
         lifts and the thumb reads in full colour. -->
    <div class="menu-card-thumb">
      <slot name="thumb" :playing="true" :lit="hovered" />
      <div class="menu-card-thumb-veil" />
      <div class="menu-card-text">
        <span class="menu-card-label">{{ label }}</span>
        <!-- Under the title: the publication stage and the journal
             ("published · JoG" — the director's request), set in the ribbon's
             quiet .nav-status voice; then the one-line subtitle. -->
        <span class="menu-card-status" v-if="status || venue">
          <span v-if="status">{{ status }}</span>
          <span v-if="status && venue" class="menu-card-dot" aria-hidden="true">·</span>
          <span v-if="venue" class="menu-card-venue">{{ venue }}</span>
        </span>
        <span class="menu-card-sub" v-if="subtitle">{{ subtitle }}</span>
      </div>
    </div>
  </button>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  label: string
  subtitle?: string
  /** Publication stage (the registry's `status`), shown as in the ribbon. */
  status?: string
  /** Journal short form (the registry's `venue`), after the stage. */
  venue?: string
}>()
defineEmits<{ (e: 'select'): void }>()

const hovered = ref(false)
</script>

<style scoped>
.menu-card {
  position: relative;
  display: block;
  width: 100%;
  padding: 0;
  background: #050505;
  border: 1.5px solid var(--gold);
  border-radius: 14px;
  cursor: pointer;
  overflow: hidden;
  font-family: inherit;
  text-align: left;
  /* Each card takes an equal share of the parent flex column's
     available vertical space. With 6 cards in a fixed-height panel,
     no scrollbar — each card auto-sizes to fit. */
  flex: 1 1 0;
  min-height: 0;
  transition:
    border-color 0.2s ease,
    box-shadow 0.25s ease,
    transform 0.18s ease;
}

.menu-card.is-hovered {
  border-color: var(--gold-bright);
  box-shadow:
    0 0 0 1px var(--gold-bright),
    0 6px 22px -6px rgba(232, 185, 74, 0.45);
  transform: translateX(3px);
}

/* Thumbnail fills the card — height comes from the parent .menu-card
   (which uses flex:1 to share available vertical space). No
   aspect-ratio so cards adapt to whatever height the panel can give
   them. */
.menu-card-thumb {
  position: relative;
  width: 100%;
  height: 100%;
  background: #050505;
  overflow: hidden;
}

/* Quiet veil over the thumbnail when idle — the thumb keeps moving
   underneath, but grey and dim; the veil lifts on hover so the motion
   reads in full colour. */
.menu-card-thumb-veil {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.28);
  backdrop-filter: saturate(0.22) brightness(0.72);
  -webkit-backdrop-filter: saturate(0.22) brightness(0.72);
  pointer-events: none;
  transition: opacity 0.45s ease;
}

.menu-card.is-hovered .menu-card-thumb-veil {
  opacity: 0;
}

/* Title overlay: rides the bottom of the thumbnail with a dark gradient
   backdrop so the chapter label is legible without blocking the
   imagery. Fades to fully transparent at the top so most of the card
   shows the live thumbnail content. */
.menu-card-text {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 1.6rem 0.95rem 0.6rem 0.95rem;
  display: flex;
  flex-direction: column;
  background: linear-gradient(
    to top,
    rgba(0, 0, 0, 0.85) 0%,
    rgba(0, 0, 0, 0.55) 55%,
    rgba(0, 0, 0, 0.0) 100%
  );
  pointer-events: none;
}

.menu-card-label {
  color: var(--gold);
  font-size: 1.15rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  transition: color 0.2s ease;
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.9);
}

.menu-card.is-hovered .menu-card-label {
  color: var(--gold-bright);
}

/* Stage · journal: the ribbon's stage-word voice (Explore's
   .nav-status — small, letter-spaced, quiet), one step larger so it
   holds its own line. */
.menu-card-status {
  display: flex;
  align-items: baseline;
  gap: 0.35rem;
  color: var(--gold);
  /* projector legibility pass: 0.66 → 0.82rem, opacity 0.8 → 0.95 */
  font-size: 0.82rem;
  font-weight: 500;
  letter-spacing: 0.06em;
  opacity: 0.95;
  margin-top: 0.1rem;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.9);
}

.menu-card-venue {
  font-weight: 500;
}

.menu-card-dot {
  opacity: 0.55;
}

.menu-card-sub {
  color: rgba(244, 207, 106, 0.88);
  font-size: 0.88rem;
  letter-spacing: 0.03em;
  margin-top: 0.12rem;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.9);
}
</style>
