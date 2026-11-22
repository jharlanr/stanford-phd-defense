<template>
  <!-- One piece of an equation (a baked SVG) with, when the PHYSICAL
       INTUITION toggle is on, its meaning under it and a gold rule; the
       pieces that mean the same thing in the two models share a `pair`,
       and hovering one lights its twin. -->
  <span
    class="pc"
    :class="{ 'pc-lit': lit, 'pc-hot': lit && hot === pair }"
    @mouseenter="emit('hot', pair)"
    @mouseleave="emit('hot', null)"
  >
    <DfdEq :name="name" :k="k" />
    <Transition name="pc-fade">
      <span v-if="lit" class="pc-label">{{ label }}</span>
    </Transition>
  </span>
</template>

<script setup lang="ts">
import DfdEq from './DfdEq.vue'

defineProps<{
  name: string
  k: number
  label: string
  pair: string
  lit: boolean
  hot: string | null
}>()
const emit = defineEmits<{ hot: [pair: string | null] }>()
</script>

<style scoped>
.pc {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.35rem;
  padding: 0.25rem 0.35rem;
  border-radius: 8px;
  max-width: 100%;
  min-width: 0;
  transition: background 0.25s, box-shadow 0.25s;
}
.pc-lit { background: rgba(232, 185, 74, 0.06); box-shadow: inset 0 -2px 0 rgba(232, 185, 74, 0.55); }
.pc-hot { background: rgba(232, 185, 74, 0.16); box-shadow: inset 0 -2px 0 var(--gold-bright), 0 0 18px rgba(245, 199, 94, 0.25); }
.pc-label {
  max-width: 21rem;
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  font-size: 0.95rem;
  line-height: 1.25;
  color: rgba(245, 240, 230, 0.86);
}
.pc-hot .pc-label { color: #fff8e6; }
.pc-fade-enter-active, .pc-fade-leave-active { transition: opacity 0.25s; }
.pc-fade-enter-from, .pc-fade-leave-to { opacity: 0; }
</style>
