<script setup lang="ts">
// Shown on a section's last beat, over the dimmed object: one sentence.
// App.vue decides WHEN (by beat name); this card only says HOW it looks.
</script>

<template>
  <aside class="takeaway" role="note">
    <span class="kicker">Takeaway</span>
    <p>Your one-sentence takeaway.</p>
  </aside>
</template>

<style scoped>
.takeaway {
  position: absolute;
  inset: 0;
  margin: auto;
  width: fit-content;
  max-width: 32rem;
  height: fit-content;
  padding: 1.5rem 2rem;
  border: 2px solid var(--accent);
  border-radius: var(--radius);
  background: #fff;
  text-align: center;
}
.kicker {
  display: block;
  font-size: 0.8rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--accent);
}
p {
  margin: 0.5rem 0 0;
  font-size: 1.4rem;
}
</style>
