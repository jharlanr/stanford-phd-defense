<template>
  <!-- The door from Chapter 3's five-class results to the Terminal-Bench
       task (the director asked for a button in Chapter 3's results, on
       the five-class results, linking to the Terminal-Bench
       task). Two lines in the bed-ensemble door's style
       (SimEnsembleDoor): an eyebrow naming the Additional Work, a hook
       above the arrow. A plain router-link — Explore's door trail
       classifies it, so BACK on the Terminal-Bench page returns to the
       beat it was opened from. -->
  <router-link class="tbd-pill" to="/additional-work/terminal-bench">
    <span class="tbd-kicker">Additional work · Terminal-Bench</span>
    <span class="tbd-label">Can AI agents do this? <span class="tbd-arrow">→</span></span>
  </router-link>
</template>

<style scoped>
.tbd-pill {
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
  text-decoration: none;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  box-shadow:
    0 6px 28px rgba(0, 0, 0, 0.55),
    0 0 22px rgba(245, 199, 94, 0.18);
  transition: color 0.2s, border-color 0.2s, background 0.2s;
}
.tbd-pill:hover,
.tbd-pill:focus-visible {
  color: #fff8d8;
  background: rgba(56, 38, 12, 0.85);
  outline: none;
}
.tbd-kicker {
  font-size: 0.78rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(232, 185, 74, 0.95);
}
.tbd-label {
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.tbd-arrow {
  display: inline-block;
  color: var(--gold);
  margin-left: 0.2rem;
  transition: transform 0.2s;
}
/* narrow projectors (≤ 1366 wide): a tighter pill, same type sizes, so
   it clears the epoch clock */
@media (max-width: 1366px) {
  .tbd-pill { padding: 0.45rem 0.85rem 0.5rem; }
  .tbd-kicker { letter-spacing: 0.05em; }
  .tbd-label { letter-spacing: 0.05em; }
}
.tbd-pill:hover .tbd-arrow,
.tbd-pill:focus-visible .tbd-arrow {
  transform: translateX(3px);
}
</style>
