<template>
  <button
    v-if="visible"
    class="sbc-btn"
    :class="{ 'sbc-active': active }"
    @click="$emit('toggle')"
  >
    <span class="sbc-icon">⊞</span>
    Boundary conditions
  </button>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

// The bottom-left pill over the zoomed block. Toggles
// BC mode — the Globe paints inflow/outflow velocity-profile arrows on
// the walls, marks the basal patch/blister, and floats the equation
// chips (SimBcChips) coupled to each interface of the object.
const props = defineProps<{ active: boolean }>()
defineEmits<{ toggle: [] }>()

const visible = ref(false)
let rafId = 0
function tick(): void {
  const proj = (window as any).__simDomainScreen as
    | { visible: boolean; spread: number }
    | null
  // (always up while BC mode is on — its overview / head-on views
  // may frame the block smaller than the landed zoom)
  visible.value = props.active || !!(proj && proj.visible && proj.spread > 260)
  rafId = requestAnimationFrame(tick)
}
onMounted(() => { rafId = requestAnimationFrame(tick) })
onBeforeUnmount(() => cancelAnimationFrame(rafId))
</script>

<style scoped>
.sbc-btn {
  position: absolute;
  left: 22px;
  bottom: 22px;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  border: 1.5px solid var(--gold);
  background: rgba(8, 6, 4, 0.78);
  color: var(--gold-bright);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.98rem;
  font-weight: 600;
  /* every block button upper case (the director's rule) */
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 0.55rem 1.05rem;
  border-radius: 999px;
  cursor: pointer;
  pointer-events: auto;
  z-index: 12;
  white-space: nowrap;
  box-shadow:
    0 6px 28px rgba(0, 0, 0, 0.55),
    0 0 22px rgba(245, 199, 94, 0.16);
  transition: color 0.2s, background 0.2s, box-shadow 0.2s;
}

.sbc-icon { font-size: 1.1rem; }

.sbc-btn:hover {
  color: #fff8d8;
  background: rgba(56, 38, 12, 0.85);
}

.sbc-active {
  color: #1c1305;
  background: var(--gold);
  box-shadow:
    0 6px 28px rgba(0, 0, 0, 0.55),
    0 0 30px rgba(245, 199, 94, 0.45);
}
.sbc-active:hover { color: #1c1305; background: var(--gold-bright, var(--gold)); }
</style>
