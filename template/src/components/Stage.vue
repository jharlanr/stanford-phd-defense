<script setup lang="ts">
// THE OBJECT — a placeholder. Replace this with your object: a globe, a
// mesh, a map, a specimen, a plot; the engine does not care. The one idea
// to keep is below: the object's appearance is a PURE FUNCTION of the
// current beat's NAME. No component counts beats; it asks `phase` and
// answers "what do I look like on 'ch1-highlight'?". CSS transitions carry
// it from one answer to the next.
import { computed } from 'vue'
import type { BeatId } from '../beats'
import { useBeats } from '../useBeats'

const { phase } = useBeats()

// Geometry of the stand-in: a disc with three labelled arcs.
const CX = 300
const CY = 200
const R = 110
const rad = (deg: number) => (deg * Math.PI) / 180
const at = (deg: number, r: number) => ({ x: CX + r * Math.cos(rad(deg)), y: CY + r * Math.sin(rad(deg)) })
function arc(a0: number, a1: number): string {
  const p = at(a0, R)
  const q = at(a1, R)
  return `M ${p.x} ${p.y} A ${R} ${R} 0 0 1 ${q.x} ${q.y}`
}
const ARCS = [
  { id: 'A', d: arc(-84, 24), label: at(-30, R + 32) },
  { id: 'B', d: arc(36, 144), label: at(90, R + 32) },
  { id: 'C', d: arc(156, 264), label: at(210, R + 32) },
] as const
type ArcId = (typeof ARCS)[number]['id']
const chord = { l: at(144, R), r: at(36, R) } // the span of arc B, for the measurement

interface View {
  x: number // translation of the whole object, in SVG units
  s: number // scale about its centre
  show: boolean
  labels: boolean
  lit: ArcId | null // one arc in the accent colour, the others faded
  measure: boolean
  dim: boolean
}

// The whole pattern. A `switch` over the beat NAME, exhaustive: add a beat
// to the registry and the compiler asks you here what the object does on it.
const view = computed<View>((): View => {
  const base: View = { x: 0, s: 1, show: true, labels: false, lit: null, measure: false, dim: false }
  const zoomed: View = { ...base, x: -40, s: 1.3, labels: true }
  const id: BeatId = phase.value
  switch (id) {
    case 'intro-title':
      return { ...base, show: false }
    case 'intro-question':
      return base
    case 'intro-object':
      return { ...base, labels: true }
    case 'ch1-zoom':
      return zoomed
    case 'ch1-highlight':
      return { ...zoomed, lit: 'B' }
    case 'ch1-annotate':
    case 'ch1-deeper':
      return { ...zoomed, lit: 'B', measure: true }
    case 'takeaway':
      return { ...base, labels: true, dim: true }
  }
})
</script>

<template>
  <svg class="stage" viewBox="0 0 600 400" role="img" aria-label="Placeholder object" :class="{ dim: view.dim, hidden: !view.show }">
    <g class="object" :style="{ transform: `translate(${view.x}px, 0) scale(${view.s})` }">
      <circle class="body" :cx="CX" :cy="CY" :r="R - 16" />
      <path v-for="a in ARCS" :key="a.id" class="arc" :class="{ lit: view.lit === a.id, faded: view.lit && view.lit !== a.id }" :d="a.d" />
      <g class="labels" :class="{ on: view.labels }">
        <text v-for="a in ARCS" :key="a.id" :x="a.label.x" :y="a.label.y">{{ a.id }}</text>
      </g>
      <g class="measure" :class="{ on: view.measure }">
        <line :x1="chord.l.x" :y1="chord.l.y + 14" :x2="chord.r.x" :y2="chord.r.y + 14" />
        <text :x="CX" :y="chord.l.y + 34">ℓ</text>
      </g>
    </g>
  </svg>
</template>

<style scoped>
.stage {
  display: block;
  width: 100%;
  max-height: 60vh;
  transition: opacity var(--dur);
}
.stage.dim {
  opacity: 0.2;
}
.stage.hidden {
  opacity: 0;
}
.object {
  transform-box: view-box;
  transform-origin: 300px 200px;
  transition: transform var(--dur) ease-in-out;
}
.body {
  fill: #fff;
  stroke: var(--line);
  stroke-width: 1.5;
}
.arc {
  fill: none;
  stroke: var(--ink);
  stroke-width: 10;
  stroke-linecap: round;
  transition: stroke var(--dur), opacity var(--dur);
}
.arc.lit {
  stroke: var(--accent);
}
.arc.faded {
  opacity: 0.2;
}
.labels text,
.measure text {
  font-size: 18px;
  text-anchor: middle;
  dominant-baseline: middle;
  fill: var(--muted);
}
.labels,
.measure {
  opacity: 0;
  transition: opacity var(--dur);
}
.labels.on,
.measure.on {
  opacity: 1;
}
.measure line {
  stroke: var(--accent);
  stroke-width: 1.5;
  stroke-dasharray: 4 4;
}
.measure text {
  fill: var(--accent);
}
</style>
