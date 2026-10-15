<script setup lang="ts">
// The frame. It installs the engine once, lays out ribbon / stage / footer,
// and decides by beat NAME which extras are on screen: the title on the
// first beat, the door button on 'ch1-deeper', the card on 'takeaway'.
// When a door is open its page replaces the stage.
import { onBeforeUnmount, watchEffect, type Component } from 'vue'
import Ribbon from './components/Ribbon.vue'
import Stage from './components/Stage.vue'
import TakeawayCard from './components/TakeawayCard.vue'
import Door from './components/Door.vue'
import DeeperDive from './views/DeeperDive.vue'
import { BEATS } from './beats'
import { useBeats } from './useBeats'

// Every door page, by the id its <Door> button carries. Add a page here.
const DOORS: Record<string, Component> = { deeper: DeeperDive }

const { index, phase, door, reduced, install, closeDoor } = useBeats()
onBeforeUnmount(install())
// A `?door=` the app does not know (an old link) falls back to the talk.
watchEffect(() => {
  if (door.value && !DOORS[door.value]) closeDoor()
})
</script>

<template>
  <div class="app" :data-reduced="reduced">
    <Ribbon />
    <main>
      <component :is="DOORS[door]" v-if="door && DOORS[door]" />
      <template v-else>
        <Transition name="fade">
          <h1 v-if="phase === 'intro-title'" class="title">Your talk's title</h1>
        </Transition>
        <Stage />
        <p class="caption">{{ BEATS[index].title }}</p>
        <Transition name="fade">
          <Door v-if="phase === 'ch1-deeper'" id="deeper" class="centred" />
        </Transition>
        <Transition name="fade">
          <TakeawayCard v-if="phase === 'takeaway'" />
        </Transition>
      </template>
    </main>
    <footer class="hint">
      ← → (or a presenter remote) to move · Home for the first beat · the address bar's
      <code>?beat=N</code> is a deep link
    </footer>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
main {
  position: relative;
  flex: 1;
  width: min(56rem, 100% - 4rem);
  margin: 0 auto;
  padding: 3rem 0 2rem;
}
.title {
  position: absolute;
  inset: 0;
  margin: auto;
  height: fit-content;
  text-align: center;
  font-size: 2.5rem;
  font-weight: 600;
}
.caption {
  min-height: 1.5em;
  margin: 1rem 0 0;
  text-align: center;
  color: var(--muted);
}
.centred {
  display: block;
  margin: 1.5rem auto 0;
}
.hint {
  padding: 1rem 2rem;
  text-align: center;
  font-size: 0.85rem;
  color: var(--muted);
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--dur);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
