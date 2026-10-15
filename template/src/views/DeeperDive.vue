<script setup lang="ts">
// An example door page. It is a flat page, not a beat: NEXT does nothing
// here and BACK (the button, ArrowLeft, PageUp or the browser's own back)
// returns to the beat the door was opened from.
import { useBeats } from '../useBeats'

const { closeDoor } = useBeats()
</script>

<template>
  <article class="deeper">
    <button @click="closeDoor">← Back to the talk</button>
    <h2>Deeper dive</h2>
    <p>
      The room behind a door: a derivation, a method, an extra figure, a dataset. Anything that is worth
      having on hand for a question but would slow the talk down. Write it here, in your own words.
    </p>
    <div class="figure" aria-hidden="true">your figure</div>
  </article>
</template>

<style scoped>
.deeper {
  max-width: 40rem;
  margin: 0 auto;
}
h2 {
  margin-top: 1.5rem;
  font-weight: 600;
}
.figure {
  display: grid;
  place-items: center;
  height: 14rem;
  margin-top: 1.5rem;
  border: 1px dashed var(--line);
  border-radius: var(--radius);
  color: var(--muted);
}
</style>
