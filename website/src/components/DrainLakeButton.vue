<template>
  <button
    v-if="visible"
    class="drain-btn"
    :style="{ left: anchorX + 'px', top: anchorY + 'px' }"
    @click="$emit('click')"
  >
    <span class="drain-btn-label">Zoom in</span>
    <span class="drain-btn-arrow">↓</span>
  </button>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

// Ch.2 Beat 0 (the label was later changed to "Zoom in"): while a
// PNAS lake's imagery popup is open, this button floats ABOVE that
// lake on the globe (anchored via window.__featuredLakeScreens,
// projected by Globe.vue every frame). Clicking it launches the
// zoom/carve beat for that lake.
const props = defineProps<{ lakeId: string }>()
defineEmits<{ click: [] }>()

const anchorX = ref(0)
const anchorY = ref(0)
const visible = ref(false)
let rafId = 0

function tick(): void {
  const screens = (window as any).__featuredLakeScreens as
    | Record<string, { x: number; y: number; visible: boolean }>
    | null
  const proj = screens?.[props.lakeId]
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
.drain-btn {
  position: absolute;
  transform: translate(-50%, -220%);
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  border: 1px solid var(--gold);
  background: rgba(8, 6, 4, 0.78);
  color: var(--gold-bright);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.85rem;
  font-weight: 500;
  letter-spacing: 0.1em;
  text-transform: uppercase; /* the director asked for upper-case pill labels */
  padding: 0.55rem 1rem;
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
  animation: drain-btn-pulse 2.4s ease-in-out infinite;
}

.drain-btn:hover {
  color: #fff8d8;
  background: rgba(56, 38, 12, 0.85);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.65),
    0 0 30px rgba(245, 199, 94, 0.36);
}

.drain-btn-arrow {
  display: inline-block;
  font-size: 0.95rem;
  color: var(--gold);
  transform: translateY(1px);
}

@keyframes drain-btn-pulse {
  0%, 100% { box-shadow: 0 6px 28px rgba(0,0,0,0.55), 0 0 22px rgba(245,199,94,0.18); }
  50%      { box-shadow: 0 6px 28px rgba(0,0,0,0.55), 0 0 36px rgba(245,199,94,0.40); }
}
</style>
