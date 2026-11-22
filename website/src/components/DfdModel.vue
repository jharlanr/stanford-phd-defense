<template>
  <!-- THE MODEL: Stokes → the shallow-stream equations, with the
       assumptions stated as figure labels, and the slab itself drawn
       (thickness H, slope α, a free-slip patch of radius R, linear Weertman
       sliding c₀ outside it). Every equation is the paper's own LaTeX
       (config/dfdEqs.ts). The three terms of each SSA stand apart so the
       presenter can point at them: membrane · basal drag · driving. -->
  <div class="md">
    <div class="md-eqs">
      <div class="md-row">
        <span class="md-k">Stokes</span>
        <DfdEq name="pde_stokes" :k="K" />
      </div>
      <div class="md-row">
        <span class="md-k">Newtonian</span>
        <DfdEq name="pde_newton" :k="K" />
        <DfdEq name="eta" set="slab" :k="K * 0.85" class="md-aside" />
      </div>
      <div class="md-row">
        <span class="md-k">Free surface</span>
        <DfdEq name="pde_surface" :k="K" />
      </div>
      <div class="md-row">
        <span class="md-k">Bed</span>
        <DfdEq name="pde_bed" :k="K" />
      </div>
      <div class="md-row md-row-assume">
        <span class="md-k">Shallow stream</span>
        <DfdEq name="assum_shallow" :k="K" />
        <DfdEq name="def_k0" :k="K * 0.9" class="md-aside" />
      </div>
      <div class="md-row md-row-ssa">
        <span class="md-k">2-D</span>
        <span class="md-terms">
          <span class="md-term"><DfdEq name="pde_ssa2d_mem" :k="K" /><i>membrane</i></span>
          <span class="md-term"><DfdEq name="pde_ssa2d_drag" :k="K" /><i>basal drag</i></span>
          <span class="md-term"><DfdEq name="pde_ssa2d_drv" :k="K" /><i>driving</i></span>
        </span>
      </div>
      <div class="md-row md-row-ssa">
        <span class="md-k">1-D</span>
        <span class="md-terms">
          <span class="md-term"><DfdEq name="pde_ssa1d_mem" :k="K" /><i>membrane</i></span>
          <span class="md-term"><DfdEq name="pde_ssa1d_drag" :k="K" /><i>basal drag</i></span>
          <span class="md-term"><DfdEq name="pde_ssa1d_drv" :k="K" /><i>driving</i></span>
        </span>
      </div>
      <div class="md-row">
        <span class="md-k">Perturbation</span>
        <span class="md-stack">
          <DfdEq name="def_dz" :k="K * 0.95" />
          <DfdEq name="pde_helm" :k="K" />
        </span>
      </div>
    </div>

    <!-- the slab: an oblique sketch, symbols from the same bake -->
    <figure class="md-sketch">
      <svg viewBox="0 0 640 430" class="md-svg" aria-label="An ice slab of thickness H on a bed of slope α, sliding over a circular free-slip patch of radius R">
        <defs>
          <linearGradient id="md-ice" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#cfe3f3" />
            <stop offset="1" stop-color="#8fb3cf" />
          </linearGradient>
          <linearGradient id="md-top" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stop-color="#f3f8fc" />
            <stop offset="1" stop-color="#dbe9f4" />
          </linearGradient>
          <marker id="md-arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#f5c75e" />
          </marker>
          <marker id="md-arr-w" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#f5f0e6" />
          </marker>
        </defs>
        <!-- bedrock -->
        <polygon points="70,262 490,290 490,330 70,302" fill="#5a4630" />
        <polygon points="490,290 600,228 600,268 490,330" fill="#453524" />
        <!-- ice: front face, right face, top face -->
        <polygon points="70,172 490,200 490,290 70,262" fill="url(#md-ice)" stroke="#f5c75e" stroke-width="1.6" />
        <polygon points="490,200 600,138 600,228 490,290" fill="#9cbbd6" stroke="#f5c75e" stroke-width="1.6" />
        <polygon points="70,172 490,200 600,138 180,110" fill="url(#md-top)" stroke="#f5c75e" stroke-width="1.6" />
        <!-- the patch on the bed, seen through the ice: dashed ellipse projected onto the top face -->
        <ellipse cx="335" cy="156" rx="72" ry="24" transform="rotate(3.8 335 156)" fill="rgba(0,0,0,0)" stroke="#0a0a0a" stroke-width="1.8" stroke-dasharray="6 4" />
        <!-- R from the centre -->
        <line x1="335" y1="156" x2="405" y2="152" stroke="#0a0a0a" stroke-width="1.4" />
        <circle cx="335" cy="156" r="2.2" fill="#0a0a0a" />
        <image :href="eq('sym_R')" v-bind="at('sym_R', 366, 124, 2.4)" />
        <!-- the bed under the patch: free slip -->
        <text x="335" y="178" class="md-t" text-anchor="middle">τ<tspan class="md-sub">b</tspan> = 0</text>
        <!-- outside: Weertman -->
        <text x="212" y="150" class="md-t" text-anchor="middle">τ<tspan class="md-sub">b</tspan> = −c<tspan class="md-sub">0</tspan> u<tspan class="md-sub">b</tspan></text>
        <text x="518" y="172" class="md-t" text-anchor="middle">τ<tspan class="md-sub">b</tspan> = −c<tspan class="md-sub">0</tspan> u<tspan class="md-sub">b</tspan></text>
        <!-- ice flow along the far edge -->
        <g transform="translate(300 96) rotate(-3.8)">
          <text x="-12" y="-8" class="md-flow" text-anchor="end">ICE FLOW</text>
          <line x1="0" y1="-12" x2="84" y2="-12" stroke="#f5c75e" stroke-width="3.5" marker-end="url(#md-arr)" />
        </g>
        <!-- thickness H at the left front edge -->
        <line x1="48" y1="172" x2="48" y2="262" stroke="#f5f0e6" stroke-width="1.6" marker-start="url(#md-arr-w)" marker-end="url(#md-arr-w)" />
        <image :href="eq('sym_H')" v-bind="at('sym_H', 12, 204, 2.6)" />
        <!-- slope α: the bed against the horizontal, at the right end -->
        <line x1="300" y1="290" x2="520" y2="290" stroke="#f5f0e6" stroke-width="1.2" stroke-dasharray="4 4" />
        <path d="M 440 290 A 60 60 0 0 1 438 299" fill="none" stroke="#f5f0e6" stroke-width="1.4" />
        <image :href="eq('sym_alpha')" v-bind="at('sym_alpha', 452, 294, 2.5)" />
        <!-- gravity -->
        <line x1="604" y1="300" x2="604" y2="350" stroke="#f5f0e6" stroke-width="1.6" marker-end="url(#md-arr-w)" />
        <text x="614" y="332" class="md-t md-t-light">g</text>
        <!-- the slab's coordinates: x along flow, y across, r and θ from the patch centre -->
        <g transform="translate(110 386)">
          <line x1="0" y1="0" x2="64" y2="5" stroke="#f5c75e" stroke-width="2" marker-end="url(#md-arr)" />
          <line x1="0" y1="0" x2="34" y2="-20" stroke="#f5c75e" stroke-width="2" marker-end="url(#md-arr)" />
          <text x="72" y="12" class="md-t md-t-light">x</text>
          <text x="40" y="-24" class="md-t md-t-light">y</text>
          <text x="-8" y="34" class="md-t md-t-light">r, θ from the patch centre</text>
        </g>
      </svg>
      <figcaption class="md-caption">
        <DfdEq name="def_ssa_ratio" :k="K" />
      </figcaption>
    </figure>
  </div>
</template>

<script setup lang="ts">
import DfdEq from './DfdEq.vue'
import { DFD_EQ } from '../config/dfdEqs'
import { dfdEqUrl } from '../config/dfd'

/** px per bp for the equation column */
const K = 2.7

function eq(name: string): string {
  return dfdEqUrl(name)
}
/** An SVG <image> box for a baked symbol at (x, y) in the sketch's units. */
function at(name: string, x: number, y: number, k: number): { x: number; y: number; width: number; height: number } {
  const b = DFD_EQ[name] ?? { w: 10, h: 10, base: 7 }
  return { x, y, width: b.w * k, height: b.h * k }
}
</script>

<style scoped>
.md {
  height: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
  gap: 2.5vw;
  align-items: start;
}
.md-eqs {
  display: flex;
  flex-direction: column;
  gap: 1.9vh;
  padding-top: 0.5vh;
}
.md-row {
  display: grid;
  grid-template-columns: 8.5rem auto auto;
  justify-content: start;
  align-items: center;
  column-gap: 1rem;
  min-height: 2.6rem;
}
.md-row > :nth-child(2) { justify-self: start; }
.md-row .dfd-eq { max-width: none; }
.md-k {
  font-size: 0.78rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--gold);
  text-align: right;
}
.md-aside { margin-left: 1.4rem; opacity: 0.85; justify-self: start; }
.md-terms { display: flex; flex-wrap: wrap; gap: 0.4rem 1.6rem; align-items: flex-start; }
.md-term { display: inline-flex; flex-direction: column; align-items: center; gap: 0.25rem; }
.md-term i {
  font-family: 'EB Garamond', Georgia, serif;
  font-size: 0.95rem;
  color: var(--gold-dim);
  font-style: italic;
}
.md-stack { display: flex; flex-direction: column; gap: 0.5rem; align-items: flex-start; }
.md-row-assume .dfd-eq { filter: drop-shadow(0 0 6px rgba(244, 207, 106, 0.25)); }

.md-sketch {
  margin: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2vh;
}
.md-svg {
  width: 100%;
  max-height: calc(100vh - 34vh);
  height: auto;
}
.md-t {
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  font-size: 21px;
  fill: #0a0a0a;
}
.md-t-light { fill: #f5f0e6; }
.md-sub { font-size: 0.7em; baseline-shift: sub; }
.md-flow {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.16em;
  fill: #f5c75e;
}
.md-caption { display: flex; gap: 2.5rem; align-items: center; }
</style>
