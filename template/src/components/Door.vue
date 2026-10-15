<script setup lang="ts">
// A door: a button on one beat that opens a side room (a deeper dive, a
// method page). The engine records which beat it was opened from, so BACK
// from the room lands exactly there. Put a <Door> on any beat in App.vue.
import { useBeats } from '../useBeats'

defineProps<{ id: string; label?: string }>()
const { openDoor } = useBeats()
</script>

<template>
  <button class="door" @click="openDoor(id)">{{ label ?? 'Deeper dive' }} ↗</button>
</template>

<style scoped>
.door {
  border-color: var(--accent);
  color: var(--accent);
}
</style>
