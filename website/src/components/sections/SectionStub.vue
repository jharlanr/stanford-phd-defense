<template>
  <div class="stub">
    <h2 class="title">
      {{ label }}
      <button v-if="props.nextLabel" class="next-btn" @click="emit('advance')">
        {{ props.nextLabel }} →
      </button>
    </h2>
    <p class="placeholder">
      <em>Coming soon.</em>
    </p>
    <p class="hint">{{ hint }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { sectionById } from '../../config/sections'

const props = defineProps<{
  sectionId: string
  label: string
  nextLabel: string | null
}>()
const emit = defineEmits<{
  advance: []
}>()

// Blurbs live in the section registry alongside labels + ordering.
const hint = computed(() => sectionById(props.sectionId)?.hint ?? '')
</script>

<style scoped>
.stub {
  color: #f5f5f5;
  font-family: 'Inter', system-ui, sans-serif;
}

.title {
  font-family: 'EB Garamond', serif;
  font-weight: 400;
  font-size: 2rem;
  color: var(--gold);
  margin: 0 0 1rem 0;
  letter-spacing: 0.02em;
  display: flex;
  align-items: baseline;
  gap: 0.8rem;
  flex-wrap: wrap;
}

.next-btn {
  background: transparent;
  border: 1px solid var(--gold-faint);
  color: var(--gold-dim);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 0.3rem 0.85rem;
  border-radius: 999px;
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s, background 0.2s;
}

.next-btn:hover {
  color: var(--gold-bright);
  border-color: var(--gold);
  background: var(--gold-faint);
}

.placeholder {
  margin: 0 0 1.2rem 0;
  font-size: 1.1rem;
}

.placeholder em {
  color: var(--gold-dim);
  font-style: italic;
}

.hint {
  font-size: 0.95rem;
  line-height: 1.55;
  opacity: 0.75;
  margin: 0;
}
</style>
