<template>
  <!-- "Make your own labels": Chapter 3's label beat,
       bottom-right — the director wanted a proper button, not just a link — the door
       from the label made live to the "Label lakes yourself" page
       (/additional-work/label). The MORE DETAILS pill's family (Inter
       uppercase, gold hairline, 999px), with more presence: a full gold
       border and a soft standing glow, the five class colours as its
       glyph, and it fills gold on hover with the arrow stepping forward.
       Nothing moves at rest. Two lines (the director's rule: every
       button that routes to Additional Work says so, small, over its
       name). -->
  <router-link class="mk-pill" :to="to">
    <span class="mk-dots" aria-hidden="true">
      <i v-for="c in ESSD_CLASSES" :key="c.code" :style="{ background: c.color }" />
    </span>
    <span class="mk-words">
      <span class="mk-kicker">{{ kicker }}</span>
      <span class="mk-text">{{ label }}</span>
    </span>
    <span class="mk-arrow" aria-hidden="true">→</span>
  </router-link>
</template>

<script setup lang="ts">
import { ESSD_CLASSES } from '../config/essdLabel'

withDefaults(defineProps<{ to?: string; label?: string; kicker?: string }>(), {
  to: '/additional-work/label',
  label: 'Make your own labels',
  kicker: 'Additional work',
})
</script>

<style scoped>
.mk-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  background: rgba(14, 11, 6, 0.78);
  border: 1px solid var(--gold);
  color: var(--gold-bright);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.92rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  text-decoration: none;
  line-height: 1.15;
  padding: 0.48rem 1.3rem 0.52rem 1.1rem;
  border-radius: 999px;
  cursor: pointer;
  pointer-events: auto;
  white-space: nowrap;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  box-shadow: 0 0 22px -6px rgba(244, 207, 106, 0.38), inset 0 0 0 1px rgba(244, 207, 106, 0.06);
  transition: background 0.25s, color 0.25s, border-color 0.25s, box-shadow 0.25s;
}
.mk-pill:hover,
.mk-pill:focus-visible {
  background: var(--gold-bright);
  border-color: var(--gold-bright);
  color: #0a0a0a;
  box-shadow: 0 0 34px -4px rgba(244, 207, 106, 0.62);
  outline: none;
}

/* the small "ADDITIONAL WORK" over the name */
.mk-words {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.14em;
}
.mk-kicker {
  font-size: 0.78em;
  font-weight: 500;
  letter-spacing: 0.14em;
  opacity: 0.9;
}
.mk-text {
  font-size: 1.06em;
}

/* the five classes, as the sliders' knobs */
.mk-dots {
  display: inline-flex;
  gap: 4px;
}
.mk-dots i {
  display: block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  box-shadow: 0 0 0 1.5px rgba(10, 9, 8, 0.85);
}
.mk-pill:hover .mk-dots i,
.mk-pill:focus-visible .mk-dots i {
  box-shadow: none;
}

.mk-arrow {
  display: inline-block;
  font-weight: 500;
  transition: transform 0.25s;
}
.mk-pill:hover .mk-arrow,
.mk-pill:focus-visible .mk-arrow {
  transform: translateX(3px);
}
</style>
