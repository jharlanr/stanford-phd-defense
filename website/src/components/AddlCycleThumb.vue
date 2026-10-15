<template>
  <!-- A square thumbnail that slowly ticks through a set of frames (the
       translucent sim block over each of the ten MGSIM beds) with a
       crossfade. Two stacked images: the "back" one holds the previous
       frame while the front one fades in. Frames are preloaded so the
       first tick never flashes. -->
  <div class="cyc">
    <img class="cyc-img" :src="frames[prev]" alt="" />
    <img class="cyc-img cyc-front" :class="{ 'cyc-show': showFront }" :src="frames[idx]" :alt="alt" />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = withDefaults(defineProps<{ frames: string[]; intervalMs?: number; alt?: string }>(), {
  intervalMs: 2000,
  alt: '',
})

const idx = ref(0)
const prev = ref(0)
const showFront = ref(true)
let timer: number | null = null

onMounted(() => {
  for (const f of props.frames) {
    const im = new Image()
    im.src = f
  }
  timer = window.setInterval(() => {
    prev.value = idx.value
    idx.value = (idx.value + 1) % props.frames.length
    // Swap: front becomes the new frame (fades in over the previous one).
    showFront.value = false
    window.requestAnimationFrame(() => {
      showFront.value = true
    })
  }, props.intervalMs)
})

onBeforeUnmount(() => {
  if (timer !== null) window.clearInterval(timer)
})
</script>

<style scoped>
.cyc {
  position: absolute;
  inset: 0;
  background: #000;
}

.cyc-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.cyc-front {
  opacity: 0;
}

.cyc-show {
  opacity: 1;
  transition: opacity 0.9s ease;
}
</style>
