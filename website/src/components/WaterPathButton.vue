<template>
  <button
    v-if="visible"
    class="water-btn"
    :style="{ left: anchorX + 'px', top: anchorY + 'px' }"
    @click="$emit('click')"
  >
    <span class="water-btn-label">Where does the water go?</span>
    <span class="water-btn-arrow">↓</span>
  </button>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

defineEmits<{ click: [] }>()

// Mirrors ClickHereHint's screen-tracking pattern: reads
// window.__nlBeaconScreen (set by Globe.vue every frame, projects NL's
// 3D position to pixels) and snaps the button to that location, with
// a CSS transform that floats it BELOW the lake (translate(-50%, +160%))
// so it doesn't cover NL itself. The button replaces the "North Lake"
// hint label after the user has opened the drain video — same anchor,
// opposite side of the lake, different call-to-action.
const anchorX = ref(0)
const anchorY = ref(0)
const visible = ref(false)
let rafId = 0

function tick(): void {
  const proj = (window as any).__nlBeaconScreen as
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

onMounted(() => {
  rafId = requestAnimationFrame(tick)
})
onBeforeUnmount(() => {
  cancelAnimationFrame(rafId)
})
</script>

<style scoped>
.water-btn {
  position: absolute;
  /* Below NL, extending LEFT with its ↓ right under the lake:
     the recentred beat-0 landing puts NL ~100 px from the
     lake-video dock at 1440 px, and a button centred on the lake ran
     under the dock card. 23px = padding-right + half the arrow glyph. */
  transform: translate(calc(-100% + 23px), 160%);
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  border: 1px solid var(--gold);
  background: rgba(8, 6, 4, 0.78);
  color: var(--gold-bright);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.85rem;
  font-weight: 500;
  /* Upper case like Ch.1's slab action buttons (the director's rule). */
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
  transition: color 0.2s, border-color 0.2s, background 0.2s, transform 0.2s;
  animation: water-btn-pulse 2.4s ease-in-out infinite;
}

.water-btn:hover {
  color: #fff8d8;
  background: rgba(56, 38, 12, 0.85);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.65),
    0 0 30px rgba(245, 199, 94, 0.36);
}

.water-btn-arrow {
  display: inline-block;
  font-size: 0.95rem;
  color: var(--gold);
  transform: translateY(1px);
}

@keyframes water-btn-pulse {
  0%, 100% { box-shadow: 0 6px 28px rgba(0,0,0,0.55), 0 0 22px rgba(245,199,94,0.18); }
  50%      { box-shadow: 0 6px 28px rgba(0,0,0,0.55), 0 0 36px rgba(245,199,94,0.40); }
}
</style>
