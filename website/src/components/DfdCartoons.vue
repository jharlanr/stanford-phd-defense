<template>
  <!-- The flash slide's two cartoons, drawn as objects on the dark page
       (the director: the paper's panels on their white ground looked
       "pasted on"): the paper's Fig. 1 C and D in the Model beat's slab
       language — one block of ice on its bed, the stress on the top
       face, the cross-section on the front. `blister`: hours after the
       drainage, the water blister lifts the ice and the surface above it
       is in tension all round. `sliding`: days after, the ice relaxes
       onto the slippery patch and sliding sets a dipole — tension
       upstream, compression downstream (flow toward +x, to the right,
       the Lab's convention). Figure labels only. -->
  <svg viewBox="0 0 640 300" class="ct" :aria-label="kind === 'blister' ? 'An ice block lifted by a water blister at its bed; tension on the surface above it' : 'An ice block sliding over a free-slip patch; tension upstream, compression downstream'">
    <defs>
      <linearGradient :id="id('ice')" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#cfe3f3" />
        <stop offset="1" stop-color="#8fb3cf" />
      </linearGradient>
      <linearGradient :id="id('top')" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="#f3f8fc" />
        <stop offset="1" stop-color="#dbe9f4" />
      </linearGradient>
      <radialGradient :id="id('red')">
        <stop offset="0" stop-color="#e8322a" stop-opacity="0.95" />
        <stop offset="0.45" stop-color="#f0574b" stop-opacity="0.7" />
        <stop offset="1" stop-color="#f7a39a" stop-opacity="0" />
      </radialGradient>
      <radialGradient :id="id('blue')">
        <stop offset="0" stop-color="#2d4fd6" stop-opacity="0.95" />
        <stop offset="0.45" stop-color="#4f73e6" stop-opacity="0.7" />
        <stop offset="1" stop-color="#a9b9f3" stop-opacity="0" />
      </radialGradient>
      <marker :id="id('arr-red')" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#e63b2e" />
      </marker>
      <marker :id="id('arr-ink')" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#0a0a0a" />
      </marker>
      <marker :id="id('arr-gold')" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#f5c75e" />
      </marker>
      <clipPath :id="id('topclip')"><polygon :points="poly(TOP)" /></clipPath>
    </defs>

    <!-- bedrock -->
    <polygon :points="poly(BED_FRONT)" fill="#5a4630" />
    <polygon :points="poly(BED_RIGHT)" fill="#453524" />
    <!-- ice: front, right, top -->
    <polygon :points="poly(FRONT)" :fill="`url(#${id('ice')})`" stroke="#f5c75e" stroke-width="1.6" />
    <polygon :points="poly(RIGHT)" fill="#9cbbd6" stroke="#f5c75e" stroke-width="1.6" />
    <polygon :points="poly(TOP)" :fill="`url(#${id('top')})`" stroke="#f5c75e" stroke-width="1.6" />

    <!-- the stress on the top face, in the face's own (sheared) frame -->
    <g :clip-path="`url(#${id('topclip')})`">
      <g :transform="TOP_TF">
        <template v-if="kind === 'blister'">
          <circle cx="0.5" cy="0.45" r="0.34" :fill="`url(#${id('red')})`" />
        </template>
        <template v-else>
          <circle cx="0.33" cy="0.45" r="0.3" :fill="`url(#${id('red')})`" />
          <circle cx="0.67" cy="0.45" r="0.3" :fill="`url(#${id('blue')})`" />
          <!-- the patch, seen through the ice -->
          <circle cx="0.5" cy="0.45" r="0.15" fill="none" stroke="#0a0a0a" stroke-width="0.004" stroke-dasharray="0.014 0.009" />
        </template>
      </g>
    </g>
    <polygon :points="poly(TOP)" fill="none" stroke="#f5c75e" stroke-width="1.6" />

    <!-- the principal-stress marks and their words -->
    <template v-if="kind === 'blister'">
      <g :transform="`translate(${pt(top(0.5, 0.45))})`">
        <line x1="-26" y1="0" x2="26" y2="0" class="ct-ps" :marker-start="mk('arr-ink')" :marker-end="mk('arr-ink')" />
        <line x1="0" y1="-16" x2="0" y2="16" class="ct-ps" :marker-start="mk('arr-ink')" :marker-end="mk('arr-ink')" />
        <text x="34" y="5" class="ct-w">tension</text>
      </g>
    </template>
    <template v-else>
      <g :transform="`translate(${pt(top(0.27, 0.45))})`">
        <line x1="-26" y1="0" x2="26" y2="0" class="ct-ps" :marker-start="mk('arr-ink')" :marker-end="mk('arr-ink')" />
        <text x="0" y="-14" class="ct-w" text-anchor="middle">tension</text>
      </g>
      <g :transform="`translate(${pt(top(0.74, 0.45))})`">
        <line x1="-34" y1="0" x2="-8" y2="0" class="ct-ps" :marker-end="mk('arr-ink')" />
        <line x1="34" y1="0" x2="8" y2="0" class="ct-ps" :marker-end="mk('arr-ink')" />
        <text x="0" y="-14" class="ct-w" text-anchor="middle">compression</text>
      </g>
    </template>

    <!-- the cross-section on the front face -->
    <template v-if="kind === 'blister'">
      <!-- the blister on the bed and the lifted surface -->
      <path :d="lens(0.32, 0.68, 0.6)" fill="#2f7fe6" stroke="#1b5fc0" stroke-width="1" />
      <path :d="bump(0.3, 0.7, -0.26)" fill="none" stroke="#0a0a0a" stroke-width="1.6" stroke-dasharray="3 3" />
      <!-- uplift: the surface and the bed -->
      <line v-for="a in [0.38, 0.5, 0.62]" :key="'s' + a" v-bind="seg(a, 0.26, a, 0.06)" class="ct-up" :marker-end="mk('arr-red')" />
      <line v-for="a in [0.38, 0.5, 0.62]" :key="'b' + a" v-bind="seg(a, 0.98, a, 0.8)" class="ct-up" :marker-end="mk('arr-red')" />
      <!-- the hydrofracture: from the surface into the blister -->
      <line v-bind="segPts(top(0.5, 0.45), front(0.5, 0.8))" stroke="#eaf4ff" stroke-width="4" stroke-opacity="0.55" />
      <line v-bind="segPts(top(0.5, 0.45), front(0.5, 0.8))" stroke="#2f7fe6" stroke-width="1.8" />
      <text v-bind="at(front(0.72, 0.93))" class="ct-w ct-w-blue">blister</text>
      <text v-bind="at(front(0.7, 0.45))" class="ct-w">uplift</text>
      <text v-bind="at(front(0.455, 0.56))" class="ct-w ct-w-blue" text-anchor="end">hydrofracture</text>
    </template>
    <template v-else>
      <!-- the blister gone: its outline, the free-slip patch it leaves -->
      <path :d="lens(0.32, 0.68, 0.6)" fill="none" stroke="#0a0a0a" stroke-width="1.4" stroke-dasharray="3 3" />
      <path :d="bump(0.3, 0.7, -0.26)" fill="none" stroke="#0a0a0a" stroke-width="1.4" stroke-dasharray="3 3" />
      <line v-bind="seg(0.3, 1, 0.7, 1)" stroke="#2f7fe6" stroke-width="5" stroke-linecap="round" />
      <!-- relaxation: the surface and the bed settle -->
      <line v-for="a in [0.38, 0.5, 0.62]" :key="'s' + a" v-bind="seg(a, 0.04, a, 0.24)" class="ct-up" :marker-end="mk('arr-red')" />
      <line v-for="a in [0.38, 0.5, 0.62]" :key="'b' + a" v-bind="seg(a, 0.72, a, 0.92)" class="ct-up" :marker-end="mk('arr-red')" />
      <text v-bind="at(front(0.72, 0.93))" class="ct-w ct-w-blue">free-slip patch</text>
      <text v-bind="at(front(0.7, 0.45))" class="ct-w">relaxation</text>
    </template>

    <!-- ice flow along the back edge -->
    <g :transform="`translate(${pt(top(0.3, 1))}) rotate(3.7)`">
      <text x="-10" y="-9" class="ct-flow" text-anchor="end">ICE FLOW</text>
      <line x1="0" y1="-13" x2="80" y2="-13" stroke="#f5c75e" stroke-width="3.5" :marker-end="mk('arr-gold')" />
    </g>
    <!-- gravity, down the slope's normal -->
    <line :x1="600" :y1="236" :x2="600" :y2="276" stroke="#f5f0e6" stroke-width="1.4" :marker-end="mk('arr-gold')" />
    <text x="610" y="262" class="ct-g">g</text>
  </svg>
</template>

<script setup lang="ts">
const props = defineProps<{ kind: 'blister' | 'sliding' }>()

// ── the block (viewBox units): the top face is the unit square under
// TOP_TF (a along the flow, c into the depth), the front face is
// front(a, b) with b = 0 at the surface, 1 at the bed ──
type P = [number, number]
const O: P = [60, 118]
const U: P = [430, 28]
const V: P = [110, -62]
const T = 104
function top(a: number, c: number): P {
  return [O[0] + U[0] * a + V[0] * c, O[1] + U[1] * a + V[1] * c]
}
function front(a: number, b: number): P {
  return [O[0] + U[0] * a, O[1] + U[1] * a + T * b]
}
const TOP_TF = `matrix(${U[0]} ${U[1]} ${V[0]} ${V[1]} ${O[0]} ${O[1]})`
const TOP: P[] = [top(0, 0), top(1, 0), top(1, 1), top(0, 1)]
const FRONT: P[] = [front(0, 0), front(1, 0), front(1, 1), front(0, 1)]
const RIGHT: P[] = [front(1, 0), top(1, 1), [top(1, 1)[0], top(1, 1)[1] + T], front(1, 1)]
const BED_FRONT: P[] = [front(0, 1), front(1, 1), [front(1, 1)[0], front(1, 1)[1] + 40], [front(0, 1)[0], front(0, 1)[1] + 40]]
const BED_RIGHT: P[] = [front(1, 1), [top(1, 1)[0], top(1, 1)[1] + T], [top(1, 1)[0], top(1, 1)[1] + T + 40], [front(1, 1)[0], front(1, 1)[1] + 40]]

function pt(p: P): string {
  return `${p[0].toFixed(1)} ${p[1].toFixed(1)}`
}
function poly(ps: P[]): string {
  return ps.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ')
}
function at(p: P): { x: number; y: number } {
  return { x: p[0], y: p[1] }
}
function segPts(p: P, q: P): { x1: number; y1: number; x2: number; y2: number } {
  return { x1: p[0], y1: p[1], x2: q[0], y2: q[1] }
}
function seg(a1: number, b1: number, a2: number, b2: number): { x1: number; y1: number; x2: number; y2: number } {
  return segPts(front(a1, b1), front(a2, b2))
}
/** A lens on the bed between a0 and a1 (a quadratic whose peak sits at
 *  b = 1 − (1 − bc)/2 … the control point at bc). */
function lens(a0: number, a1: number, bc: number): string {
  const p0 = front(a0, 1)
  const c = front((a0 + a1) / 2, bc)
  const p1 = front(a1, 1)
  return `M ${pt(p0)} Q ${pt(c)} ${pt(p1)} Z`
}
/** The lifted surface: a quadratic above the front-top edge. */
function bump(a0: number, a1: number, bc: number): string {
  const p0 = front(a0, 0)
  const c = front((a0 + a1) / 2, bc)
  const p1 = front(a1, 0)
  return `M ${pt(p0)} Q ${pt(c)} ${pt(p1)}`
}
function id(s: string): string {
  return `ct-${props.kind}-${s}`
}
function mk(s: string): string {
  return `url(#${id(s)})`
}
</script>

<style scoped>
.ct { width: 100%; height: auto; display: block; overflow: visible; }
.ct-ps { stroke: #0a0a0a; stroke-width: 2.2; }
.ct-up { stroke: #e63b2e; stroke-width: 2.4; }
.ct-w {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.06em;
  fill: #0a0a0a;
}
.ct-w-blue { fill: #0b3f8f; }
.ct-flow {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.16em;
  fill: #f5c75e;
}
.ct-g {
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  font-size: 21px;
  fill: #f5f0e6;
}
</style>
