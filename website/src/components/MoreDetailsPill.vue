<template>
  <!-- "More details": the door from a
       chapter's closing beats to its deeper-dive page — the backup
       slides for committee questions. Same pill language as the
       Back/Next beat buttons.
       TWO LINES (the director's rule for every button that routes to
       Additional Work: a small "additional work" kicker on top and the
       button name in a bigger font below, so the user knows it leads
       to additional work): every page this pill opens is
       an Additional Work page (the deeper dives live there too). Both
       lines are sized in em, so a parent's font-size on the pill scales
       them together.
       Later the director asked that every chapter-relevant deeper-dive
       button say DIVE DEEPER instead of ADDITIONAL WORK:
       the kicker follows the route — a chapter's deeper dive
       (/additional-work/deeper/…) reads DIVE DEEPER; the true Additional
       Work pages (fieldwork, revisit, …) keep ADDITIONAL WORK. An explicit
       `kicker` prop still wins. -->
  <router-link class="more-pill" :to="to">
    <span class="more-kicker">{{ kickerText }}</span>
    <span class="more-label">{{ label }}</span>
  </router-link>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ to?: string; label?: string; kicker?: string }>(), {
  to: '/additional-work/deeper/chapter1',
  label: 'More details',
  kicker: undefined,
})
/** A chapter's deeper dive → "Dive deeper"; any other door → "Additional work". */
const kickerText = computed(
  () => props.kicker ?? (props.to.startsWith('/additional-work/deeper') ? 'Dive deeper' : 'Additional work'),
)
</script>

<style scoped>
.more-pill {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 0.14em;
  background: rgba(0, 0, 0, 0.55);
  border: 1.5px solid var(--gold-dim);
  color: var(--gold);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.95rem;
  font-weight: 500;
  line-height: 1.15;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  text-decoration: none;
  padding: 0.45rem 1.15rem 0.5rem;
  border-radius: 999px;
  cursor: pointer;
  pointer-events: auto;
  backdrop-filter: blur(10px);
  white-space: nowrap;
  transition: color 0.2s, border-color 0.2s, background 0.2s;
}
/* the small "DIVE DEEPER" / "ADDITIONAL WORK" over the name */
.more-kicker {
  font-size: 0.78em;
  font-weight: 500;
  letter-spacing: 0.14em;
  opacity: 0.9;
}
.more-label {
  font-size: 1.06em;
  font-weight: 600;
}
.more-pill:hover {
  color: var(--gold-bright);
  border-color: var(--gold);
  background: rgba(20, 16, 8, 0.75);
}
</style>
