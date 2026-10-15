<template>
  <!-- The chapter's TITLE CARD (the director's spec: each chapter's
       landing beat carries a card, not too big but noticeable, that
       says 'Chapter 1: <chapter 1 title>', and on NEXT it goes away in
       the same beat that brings up
       whatever comes next for that chapter). A label, not
       narration: the chapter and its thesis title (config/sections.ts,
       `title`), set as the drainage legend's sibling — the same card, the
       top-LEFT corner under the ribbon where the legend holds the
       top-right (Chapter 3's takes the top-right: its lake callouts hold
       the left). Explore shows it on a chapter's first beat only and
       drops it on the first NEXT (also while a lake's popup is open, so
       it never sits under one). Never takes a click. -->
  <Transition name="ctc">
    <div v-if="show" class="ctc-card" :class="{ 'ctc-right': side === 'right' }" role="heading" aria-level="1">
      <span class="ctc-chapter">{{ chapter }}:</span>
      <span class="ctc-title">{{ title }}</span>
      <!-- the paper's stage · its venue (the director's wording: "published
           · JoG" on the title card for Chapter 1's LAKES moment,
           "in revision · PNAS" for Chapter 2 and
           "in final revision · ESSD" for Chapter 3) — config/sections.ts
           `status` + `venue` -->
      <span v-if="status && venue" class="ctc-status">{{ status }} · {{ venue }}</span>
    </div>
  </Transition>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    show: boolean
    /** "Chapter 1" — the registry's label. */
    chapter: string
    /** The chapter's title in the thesis. */
    title: string
    /** Which top corner. Left unless the landing's own furniture holds it
     *  (Chapter 3's lake callouts do — its card takes the right, which
     *  that page leaves free). */
    side?: 'left' | 'right'
    /** The paper's stage ("published", "in revision", …) and venue
     *  ("JoG", "PNAS", "ESSD"): a line under the title, "stage · venue". */
    status?: string
    venue?: string
  }>(),
  { side: 'left', status: '', venue: '' },
)
</script>

<style scoped>
/* The drainage legend's card (DrainageLegend .dlg-card), mirrored to the
   left edge; same top rule, so both hang level under the sub-menu. */
.ctc-card {
  position: absolute;
  top: max(9.5vh, calc(var(--chrome-bottom, 0px) + 0.75rem));
  left: 2vw;
  z-index: 8;
  /* wide enough that Chapter 2's title sets in two lines: a third would
     reach down to the two westernmost center lakes on its landing */
  max-width: min(33rem, 42vw);
  box-sizing: border-box;
  padding: 0.95rem 1.3rem 1rem;
  background: rgba(8, 6, 4, 0.74);
  border: 1px solid var(--gold-dim);
  border-radius: 12px;
  backdrop-filter: blur(8px);
  pointer-events: none;
}
/* The right-hand corner (Chapter 3): narrower, to stay clear of the
   lateral-drainage callout that hangs beside it. */
.ctc-card.ctc-right {
  left: auto;
  right: 2vw;
  max-width: min(21.5rem, 24vw);
}
.ctc-chapter {
  display: block;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--gold-bright);
  margin-bottom: 0.4rem;
}
.ctc-title {
  display: block;
  font-family: 'EB Garamond', serif;
  font-size: 1.6rem;
  line-height: 1.22;
  letter-spacing: 0.01em;
  color: #f5f5f5;
  /* even lines — at 1280 px Chapter 1's title left "patch" alone */
  text-wrap: balance;
}
.ctc-status {
  display: block;
  margin-top: 0.5rem;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  /* the director's casing — "published · JoG", not PUBLISHED · JOG */
  color: var(--gold);
}

/* In a moment after the page settles (so a deep link to a later beat, or
   BACK onto a chapter's last beat, never flashes it); out with the beat
   that replaces it. */
.ctc-enter-active {
  transition: opacity 600ms ease 350ms, transform 600ms cubic-bezier(0.2, 0.8, 0.2, 1) 350ms;
}
.ctc-leave-active {
  transition: opacity 400ms ease, transform 400ms ease;
}
.ctc-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.ctc-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

@media (max-width: 900px) {
  .ctc-card { max-width: 60vw; padding: 0.7rem 0.95rem 0.75rem; }
  .ctc-title { font-size: 1.3rem; }
  .ctc-chapter { font-size: 0.8rem; }
  .ctc-status { font-size: 0.8rem; }
}
</style>
