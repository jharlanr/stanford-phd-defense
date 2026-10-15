<template>
  <Transition name="dlg-fade">
    <div v-if="visible" class="dlg-card" @mouseleave="$emit('hover', null)">
      <div class="dlg-title">Lake drainage styles · 2019</div>
      <div class="dlg-rows">
        <button
          v-for="c in CLASSES"
          :key="c.code"
          class="dlg-row"
          @mouseenter="$emit('hover', c.lakeId)"
          @focus="$emit('hover', c.lakeId)"
          @click="$emit('select', c.lakeId)"
        >
          <span class="dlg-chip" :style="{ background: c.color }" />
          <span class="dlg-code">{{ c.code }}</span>
          <span class="dlg-name">{{ c.name }}</span>
        </button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
// ESSD fig-4 drainage classes, CLASS_COLORS verbatim. The five colored
// lake polygons on the globe (featured_lakes.json) use the same palette.
// Interactive (the director asked for it): hovering a row pulses that lake
// on the globe (1× → 2.4×, Globe FEATURED_PULSE_MAX); clicking a row
// opens its season video — same action as clicking the lake itself.
defineProps<{ visible: boolean }>()
defineEmits<{ hover: [lakeId: string | null]; select: [lakeId: string] }>()

// ND on top (the director's ordering); the draining classes follow in the
// ESSD order.
const CLASSES = [
  { code: 'ND', name: 'No drainage',       color: '#e8524a', lakeId: 'CW2019_1597' },
  { code: 'HF', name: 'Hydrofracture',     color: '#4caf50', lakeId: 'CW2019_1889' },
  { code: 'MD', name: 'Moulin drainage',   color: '#42a5f5', lakeId: 'CW2019_1848' },
  { code: 'LD', name: 'Lateral drainage',  color: '#ff9800', lakeId: 'CW2019_1907' },
  { code: 'CD', name: 'Crevasse drainage', color: '#ab47bc', lakeId: 'CW2019_2330' },
] as const
</script>

<style scoped>
/* Top-right (the director's placement), big enough for the back of the room. Sits below
   the beat-nav pills. */
.dlg-card {
  position: absolute;
  top: max(9.5vh, calc(var(--chrome-bottom, 0px) + 0.75rem)); /* below the ribbon's sub-menu while one hangs there (Explore --chrome-bottom) */
  right: 2vw;
  z-index: 8;
  padding: 1.1rem 1.3rem 1rem;
  background: rgba(8, 6, 4, 0.74);
  border: 1px solid var(--gold-faint);
  border-radius: 12px;
  backdrop-filter: blur(8px);
  font-family: 'Inter', system-ui, sans-serif;
  color: rgba(245, 245, 245, 0.9);
  pointer-events: auto;
}

.dlg-title {
  font-family: 'EB Garamond', serif;
  font-size: 1.45rem;
  color: var(--gold-bright);
  margin-bottom: 0.7rem;
  letter-spacing: 0.02em;
}

.dlg-rows { display: flex; flex-direction: column; gap: 0.15rem; }

.dlg-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.12rem;
  font-family: inherit;
  color: inherit;
  background: transparent;
  border: none;
  border-radius: 8px;
  padding: 0.32rem 0.5rem;
  cursor: pointer;
  text-align: left;
  transition: background 0.18s;
}
.dlg-row:hover {
  background: rgba(245, 199, 94, 0.12);
}

.dlg-chip {
  width: 19px;
  height: 19px;
  border-radius: 4px;
  border: 1px solid rgba(0, 0, 0, 0.6);
  display: inline-block;
  flex: 0 0 auto;
}

.dlg-code {
  width: 2.1em;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: rgba(245, 245, 245, 0.92);
}

.dlg-name { color: rgba(245, 245, 245, 0.92); white-space: nowrap; }

.dlg-fade-enter-active,
.dlg-fade-leave-active { transition: opacity 0.5s; }
.dlg-fade-enter-from,
.dlg-fade-leave-to { opacity: 0; }
</style>
