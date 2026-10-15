<template>
  <!-- One title-page card of the literature timeline: masthead, rule,
       title, authors, and the hand-drawn cartoon of the paper's defining
       figure (TimelineFigure). Shared by the timeline (LiteratureTimeline)
       and the coupling-length step's corner cards (CouplingMap), so both
       draw the same page. Sized by the `--cw` custom property (the card's
       width in px) that the parent sets; the parent positions the root. -->
  <div class="lt-page">
    <div class="lt-masthead">
      <span class="lt-journal">{{ paper.journalShort }}</span>
      <span class="lt-yr">{{ paper.year }}</span>
    </div>
    <div class="lt-rule" />
    <div class="lt-title">{{ paper.title }}</div>
    <div class="lt-authors">{{ paper.authors }}</div>
    <div class="lt-figure">
      <TimelineFigure :id="paper.id" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TimelinePaper } from '../config/timeline'
import TimelineFigure from './TimelineFigure.vue'

defineProps<{ paper: TimelinePaper }>()
</script>

<style scoped>
.lt-page {
  display: flex;
  flex-direction: column;
  background: var(--paper, #ece7db);
  color: var(--ink, #1c1a16);
  border-radius: 2px;
  padding: 7% 8% 6%;
  overflow: hidden;
  box-shadow:
    0 12px 32px rgba(0, 0, 0, 0.6),
    0 0 0 1px rgba(255, 255, 255, 0.06);
  transition: box-shadow 0.35s;
}
.lt-masthead {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 4%;
  font-size: calc(var(--cw) * 0.054);
  line-height: 1;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  font-weight: 600;
  color: #6e6656;
  flex: none;
}
.lt-journal {
  white-space: nowrap;
}
.lt-yr {
  flex: none;
}
.lt-rule {
  height: 1px;
  background: var(--ink, #1c1a16);
  opacity: 0.45;
  margin: 5% 0 5%;
  flex: none;
}
.lt-title {
  font-family: 'EB Garamond', Georgia, serif;
  font-weight: 500;
  font-size: calc(var(--cw) * 0.084);
  line-height: 1.12;
  flex: none;
}
.lt-authors {
  margin-top: 4%;
  font-size: calc(var(--cw) * 0.05);
  line-height: 1.3;
  color: #4f4838;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: none;
}
/* The cartoon takes whatever the type leaves. */
.lt-figure {
  flex: 1 1 auto;
  min-height: 0;
  margin-top: 5%;
}
</style>
