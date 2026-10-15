<template>
  <button
    v-if="visible"
    class="slab-btn"
    :class="`slab-btn-${placement}`"
    :style="{ left: anchorX + offsetX + 'px', top: anchorY + offsetY + 'px' }"
    @click="$emit('click')"
  >
    <span class="slab-btn-label">{{ label }}</span>
    <span class="slab-btn-arrow">{{ arrow }}</span>
  </button>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

// Beat-anchored action button riding the cross-section slab's fracture
// anchor (window.__slabFracScreen, projected by Globe.vue every frame).
// Ch.1 uses three instances (labels set in UPPER CASE by the CSS —
// the director's rule for block buttons):
//   Beat 1 — "Drain the lake" ↓, hovering ABOVE the surface lake
//   Beat 2 — "How does the ice respond?" →, just RIGHT of the column
//   Beat 3 — "Toy model" →, same spot (runs the 3→4 seam morph)
withDefaults(defineProps<{
  label: string
  arrow?: string
  /** 'above' floats above the anchor (down-arrow points at the lake);
   *  'right' floats to the anchor's right (next to the drain column). */
  placement?: 'above' | 'right'
  offsetX?: number
  offsetY?: number
}>(), { arrow: '→', placement: 'above', offsetX: 0, offsetY: 0 })

defineEmits<{ click: [] }>()

const anchorX = ref(0)
const anchorY = ref(0)
const visible = ref(false)
let rafId = 0

function tick(): void {
  const proj = (window as any).__slabFracScreen as
    | { x: number; y: number; visible: boolean }
    | null
  if (proj && proj.visible) {
    anchorX.value = proj.x
    anchorY.value = proj.y
    visible.value = true
  } else {
    visible.value = false
  }
  rafId = requestAnimationFrame(tick)
}

onMounted(() => { rafId = requestAnimationFrame(tick) })
onBeforeUnmount(() => cancelAnimationFrame(rafId))
</script>

<style scoped>
.slab-btn {
  position: absolute;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  border: 1.5px solid var(--gold);
  background: rgba(8, 6, 4, 0.82);
  color: var(--gold-bright);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1rem;
  font-weight: 500;
  /* Upper case wants wider tracking than the old sentence case. */
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 0.55rem 1rem 0.55rem 1.1rem;
  border-radius: 999px;
  cursor: pointer;
  pointer-events: auto;
  z-index: 12;
  white-space: nowrap;
  backdrop-filter: blur(8px);
  box-shadow:
    0 6px 28px rgba(0, 0, 0, 0.55),
    0 0 22px rgba(245, 199, 94, 0.18);
  transition: color 0.2s, border-color 0.2s, background 0.2s;
  animation: slab-btn-pulse 2.4s ease-in-out infinite;
}

/* Hovering above the lake, arrow pointing down at it. */
.slab-btn-above { transform: translate(-50%, -220%); }
/* Floating just right of the drain column. */
.slab-btn-right { transform: translate(3.5rem, -50%); }

.slab-btn:hover {
  color: #fff8d8;
  background: rgba(56, 38, 12, 0.85);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.65),
    0 0 30px rgba(245, 199, 94, 0.36);
}

.slab-btn-arrow {
  display: inline-block;
  font-size: 0.95rem;
  color: var(--gold);
  transform: translateY(1px);
}

@keyframes slab-btn-pulse {
  0%, 100% { box-shadow: 0 6px 28px rgba(0,0,0,0.55), 0 0 22px rgba(245,199,94,0.18); }
  50%      { box-shadow: 0 6px 28px rgba(0,0,0,0.55), 0 0 36px rgba(245,199,94,0.40); }
}
</style>
