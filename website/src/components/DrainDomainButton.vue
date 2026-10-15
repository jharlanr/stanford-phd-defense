<template>
  <button
    v-if="visible"
    class="ddb-btn"
    :style="{ left: anchorX + 'px', top: anchorY + 'px' }"
    @click="$emit('click')"
  >
    <span class="ddb-label">Drain the lake</span>
    <span class="ddb-arrow">↓</span>
  </button>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

// The MGSIM page's landed block (Chapter 2 retired this pill in favour
// of its PRE / POST / DIFFERENCE tier). Once the block has landed on its
// PRE-drainage Sentinel-2 face, this pill hovers over it (anchored via
// window.__simDomainScreen, same spread gate as the model pills).
// Clicking crossfades the face to the POST-drainage scene, reveals the
// drainage-catalog outlines, and brings up the elastic/viscous pills.
defineEmits<{ click: [] }>()

const anchorX = ref(0)
const anchorY = ref(0)
const visible = ref(false)
let rafId = 0

function tick(): void {
  const proj = (window as any).__simDomainScreen as
    | { x: number; y: number; topY: number; visible: boolean; spread: number }
    | null
  if (proj && proj.visible && proj.spread > 260) {
    anchorX.value = proj.x
    anchorY.value = Math.max(70, proj.topY)
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
.ddb-btn {
  position: absolute;
  transform: translate(-50%, -160%);
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
  animation: ddb-pulse 2.4s ease-in-out infinite;
}

.ddb-btn:hover {
  color: #fff8d8;
  background: rgba(56, 38, 12, 0.85);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.65),
    0 0 30px rgba(245, 199, 94, 0.36);
}

.ddb-arrow {
  display: inline-block;
  font-size: 0.95rem;
  color: var(--gold);
  transform: translateY(1px);
}

@keyframes ddb-pulse {
  0%, 100% { box-shadow: 0 6px 28px rgba(0,0,0,0.55), 0 0 22px rgba(245,199,94,0.18); }
  50%      { box-shadow: 0 6px 28px rgba(0,0,0,0.55), 0 0 36px rgba(245,199,94,0.40); }
}
</style>
