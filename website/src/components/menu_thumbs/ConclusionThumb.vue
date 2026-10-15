<!-- Conclusion card (the director asked for the Conclusion page's
     figure, or a version of it, as the menu card's
     thumbnail). The Conclusion page's figure at card
     size: the 2019 season plays and each hydrofracture lake
     drains on its observed day — a gold flash on the lake, then a fainter gold; no
     circles, no rings, nothing drawn between lakes.
     HF only, no toggle, no labels on the card; looping a little faster
     than the page, grey under the card's veil until hovered
     (MenuCard.vue). The renderer and its data: ../ConclusionReach.vue. -->
<template>
  <ConclusionReach mode="thumb" />
</template>

<script setup lang="ts">
import ConclusionReach from '../ConclusionReach.vue'

defineProps<{ playing?: boolean; lit?: boolean }>()
</script>
