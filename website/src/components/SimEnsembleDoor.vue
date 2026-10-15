<template>
  <!-- The door from Ch.2 to the Additional-Work bed
       ensemble — shown only while the PNAS chapter is looking at lake
       1951 (the ensemble's lake). It lives in the
       bottom-right card row (SimBlockCards places it) and reads in upper
       case like every other block button. The handoff keeps the
       block on screen (Explore swallows the old section's unmount nulls)
       so the MGSIM page continues in place. -->
  <!-- The director asked that this button say ADDITIONAL WORK on top
       and then MGSIM + glaciology: the two-line form of MoreDetailsPill —
       the kicker over the name, nothing else; the name keeps the
       director's casing. -->
  <button class="sed-btn" @click="$emit('click')">
    <span class="sed-kicker">Additional work</span>
    <span class="sed-label">MGSIM + glaciology</span>
  </button>
</template>

<script setup lang="ts">
defineEmits<{ click: [] }>()
</script>

<style scoped>
.sed-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.15rem;
  border: 1.5px solid var(--gold);
  background: rgba(8, 6, 4, 0.78);
  color: var(--gold-bright);
  font-family: 'Inter', system-ui, sans-serif;
  padding: 0.5rem 1.15rem 0.55rem;
  border-radius: 999px;
  cursor: pointer;
  pointer-events: auto;
  white-space: nowrap;
  backdrop-filter: blur(8px);
  box-shadow:
    0 6px 28px rgba(0, 0, 0, 0.55),
    0 0 22px rgba(245, 199, 94, 0.18);
  transition: color 0.2s, border-color 0.2s, background 0.2s;
  animation: sed-pulse 2.8s ease-in-out infinite;
}
.sed-btn:hover {
  color: #fff8d8;
  background: rgba(56, 38, 12, 0.85);
}
.sed-kicker {
  font-size: 0.74rem;
  font-weight: 500;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(232, 185, 74, 0.9);
}
.sed-label {
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.06em;
}
@keyframes sed-pulse {
  0%, 100% { box-shadow: 0 6px 28px rgba(0,0,0,0.55), 0 0 22px rgba(245,199,94,0.18); }
  50%      { box-shadow: 0 6px 28px rgba(0,0,0,0.55), 0 0 34px rgba(245,199,94,0.38); }
}
</style>
