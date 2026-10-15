<script setup lang="ts">
// The strip along the top: section names (click one to jump to its first
// beat), the current section highlighted, a small counter, and BACK / NEXT
// buttons so a mouse or a presenter remote drives the talk as well as the
// keyboard. It knows nothing about beats beyond what the registry says.
import { computed } from 'vue'
import { SECTIONS, sectionOf, sectionStart } from '../beats'
import { useBeats } from '../useBeats'

const { index, door, total, next, back, goTo, closeDoor } = useBeats()
const current = computed(() => sectionOf(index.value))

function jump(section: string): void {
  if (door.value) closeDoor()
  goTo(sectionStart(section))
}
</script>

<template>
  <nav class="ribbon" aria-label="Talk sections">
    <button class="step" :disabled="index === 0 && !door" @click="back">← Back</button>
    <ol class="sections">
      <li v-for="s in SECTIONS" :key="s" :class="{ current: s === current && !door }">
        <button class="section" @click="jump(s)">{{ s }}</button>
      </li>
    </ol>
    <span class="counter">{{ index + 1 }} / {{ total }}</span>
    <button class="step" :disabled="index === total - 1 || !!door" @click="next">Next →</button>
  </nav>
</template>

<style scoped>
.ribbon {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 1rem 2rem;
  border-bottom: 1px solid var(--line);
  background: #fff;
}
.sections {
  display: flex;
  gap: 0.5rem;
  margin: 0 auto;
  padding: 0;
  list-style: none;
}
.section {
  border-color: transparent;
  color: var(--muted);
}
.current .section {
  color: var(--accent);
  background: var(--accent-soft);
}
.counter {
  min-width: 4ch;
  text-align: right;
  font-variant-numeric: tabular-nums;
  color: var(--muted);
}
.step:disabled {
  opacity: 0.35;
  cursor: default;
}
</style>
