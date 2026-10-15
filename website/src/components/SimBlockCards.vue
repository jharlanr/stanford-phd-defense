<template>
  <!-- Chapter 2's bottom-right card row (the director's choice of
       corner: the bottom right is where all such cards should
       go): the bed-ensemble door (lake 1951 only) beside SEE MORE
       FIELDS → the chapter's deeper-dive page. Mirrors the
       BOUNDARY CONDITIONS pill in the bottom-left corner (22 px insets);
       the phase-space column ends above it (PhaseSpacePanel
       reserve-bottom). -->
  <Transition name="sbk-fade">
    <div v-if="visible" class="sbk-row">
      <SimEnsembleDoor v-if="ensemble" @click="$emit('ensemble')" />
      <MoreDetailsPill
        v-if="fields"
        class="sbk-more"
        label="See more fields"
        to="/additional-work/deeper/chapter2#fields"
      />
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import SimEnsembleDoor from './SimEnsembleDoor.vue'
import MoreDetailsPill from './MoreDetailsPill.vue'

withDefaults(
  defineProps<{
    /** Show the bed-ensemble door (Ch.2's teaser beat, lake 1951). */
    ensemble: boolean
    /** Show SEE MORE FIELDS (off on the teaser: the door stands alone). */
    fields?: boolean
  }>(),
  { fields: true },
)
defineEmits<{ ensemble: [] }>()

// Same gate as the other block pills: only once the block is the
// subject (the zoom settled), never as a speck mid-dive.
const visible = ref(false)
let rafId = 0
function tick(): void {
  const proj = (window as any).__simDomainScreen as
    | { visible: boolean; spread: number }
    | null
  visible.value = !!(proj && proj.visible && proj.spread > 260)
  rafId = requestAnimationFrame(tick)
}
onMounted(() => { rafId = requestAnimationFrame(tick) })
onBeforeUnmount(() => cancelAnimationFrame(rafId))
</script>

<style scoped>
.sbk-row {
  position: absolute;
  right: 22px;
  bottom: 22px;
  display: flex;
  align-items: flex-end;
  gap: 0.7rem;
  z-index: 12;
  pointer-events: none;
}
/* sized to sit level with the two-line ensemble door; lit (gold, 1.5 px
   outline) so it reads from the back row */
.sbk-row .sbk-more {
  font-size: 0.98rem;
  padding: 0.5rem 1.15rem 0.55rem;
  letter-spacing: 0.1em;
  color: var(--gold-bright);
  border: 1.5px solid rgba(232, 185, 74, 0.85);
  background: rgba(8, 6, 4, 0.78);
}
.sbk-fade-enter-active,
.sbk-fade-leave-active { transition: opacity 0.4s; }
.sbk-fade-enter-from,
.sbk-fade-leave-to { opacity: 0; }
</style>
