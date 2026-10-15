<!-- The helicopter flyby (GH010200, 2:35–2:45) — the Introduction card's
     thumb (was ExtrasThumb, the Extras side door's).
     It loops the window all the time; the card's veil
     keeps it quiet until hovered. The window is
     its own 10 s file (cinematic/scene_menu/build_flyby_loop.sh: 1280×720,
     no audio, faststart, keyframe on frame 0) looped natively — it used to
     seek inside the full 186 MB clip, which streamed it on every menu
     visit. -->
<template>
  <video
    ref="video"
    class="extras-video"
    :src="src"
    muted
    loop
    playsinline
    autoplay
    preload="auto"
    @loadedmetadata="start"
  />
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { mediaUrl } from '../../config/media'

defineProps<{ playing?: boolean; lit?: boolean }>()
const src = mediaUrl('menu/intro/flyby_loop_v1.mp4')
const video = ref<HTMLVideoElement | null>(null)

function start() {
  video.value?.play().catch(() => {})
}

onBeforeUnmount(() => {
  video.value?.pause()
})
</script>

<style scoped>
.extras-video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  background: #050505;
}
</style>
