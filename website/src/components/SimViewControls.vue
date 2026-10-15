<template>
  <!-- Chapter 2's block STATIONS (the director wanted a linear flow for
       the header buttons rather than two rows, because the talk should
       flow in time):
       ONE row, the first lake's walk in time order — PRE DRAINAGE ·
       IMAGERY → POST DRAINAGE · IMAGERY → PRE DRAINAGE · VISCOUS σ_t1 →
       POST DRAINAGE · ELASTIC σ_t1 → DIFFERENCE · ELASTIC Δσ_t1 → POST
       DRAINAGE · VISCOUS σ_t1 → DIFFERENCE · VISCOUS Δσ_t1 — each station
       the stage over the layer (the SlabActionButton language), derived
       from the beat registry (config/ch2Beats.ts CH2_STATIONS: delete a
       beat, its station goes). It replaces the earlier two tiers
       (PRE · POST · DIFFERENCE over IMAGERY · ELASTIC · VISCOUS). The two
       Sentinel-2 dates sit under the imagery stations as a small figure
       label. The lit station is the view on screen — they double as the
       headings for what is on screen in the imagery and phase spaces
       (the director's framing) — and
       every station is a control on every beat that
       shows the row (the director wanted any button clickable, with the
       same views of the stress space from each): a click
       shows that station's view — the block painted with its step and
       its single stress space beside it (config/ch2State.ts).
       Seven stations do not fit between the centre-lakes inset and the
       stress space at a legible size (≈ 590 px at 1440 × 900), so the row
       runs from the inset to the right gutter, ABOVE the stress space —
       which starts under it (--svc-bottom, Ch2Results .cr-root). -->
  <div
    ref="rootEl"
    class="svc"
    :class="{ 'svc-tight': tight }"
    :data-key-right="keyRight"
    :style="{ left: left + 'px', top: top + 'px', '--svc-k': k, visibility: visible ? 'visible' : 'hidden' }"
  >
    <div class="svc-row">
      <template v-for="(st, i) in CH2_STATIONS" :key="st.id">
        <span v-if="i > 0" class="svc-link" aria-hidden="true" />
        <div class="svc-cell">
          <button
            class="svc-st"
            :class="{ 'svc-on': lit(st) }"
            :aria-pressed="lit(st)"
            @click="$emit('pick', st.stage, st.layer)"
          >
            <span class="svc-stage">{{ STAGE_WORDS[st.stage] }}</span>
            <span class="svc-layer">{{ LAYER_WORDS[st.layer] }}<span v-if="st.sym" class="svc-sym">{{ st.sym === 'diff' ? 'Δσ' : 'σ' }}<sub>t1</sub></span></span>
          </button>
          <span v-if="st.layer === 'imagery'" class="svc-date" :class="{ 'svc-date-on': lit(st) }">{{
            st.stage === 'pre' ? fmt(datePre) : fmt(datePost)
          }}</span>
          <!-- POST · ELASTIC's definition: the post-drainage
               elastic state is the viscous pre-drainage state plus the
               elastic perturbation, σ_t1^post ≈ σ_t1(σ^pre_viscous +
               Δσ_elastic) — LaTeX (build_results_eqs.py def_post_s_v2),
               whenever that station is the one shown -->
          <img
            v-if="lit(st) && st.id === 'post-elastic-t1'"
            class="svc-def"
            :src="ch2EqUrl(DEF_POST_S)"
            :style="defBox"
            alt="σt1 post ≈ σt1(σ pre viscous + Δσ elastic)"
          />
          <!-- The director asked that the talk flag the
               superposed field as illustrative; the deeper dive's
               #superposition holds the justification and its caveats -->
          <span v-if="lit(st) && st.id === 'post-elastic-t1'" class="svc-def-note">(qualitative, for illustration only)</span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { type Ch2Layer, type Ch2Stage } from '../config/ch2State'
import { CH2_STATIONS, type Ch2Station } from '../config/ch2Beats'
import { CH2_EQ, type Ch2EqName } from '../config/ch2Eqs'
import { ch2EqUrl } from '../config/ch2Results'

const props = defineProps<{
  stage: Ch2Stage | null
  layer: Ch2Layer | null
  /** ISO dates of the pre/post Sentinel-2 scenes (sim_domains_v2.json). */
  datePre: string | null
  datePost: string | null
}>()
defineEmits<{ pick: [stage: Ch2Stage, layer: Ch2Layer | null] }>()

const STAGE_WORDS: Record<Ch2Station['stage'], string> = {
  pre: 'Pre drainage',
  post: 'Post drainage',
  difference: 'Difference',
}
const LAYER_WORDS: Record<Ch2Station['layer'], string> = {
  imagery: 'Imagery',
  elastic: 'Elastic',
  viscous: 'Viscous',
}
/** The lit station: the block's view (the beat's own station, or the
 *  one the visitor clicked — config/ch2State.ts). */
function lit(st: Ch2Station): boolean {
  return props.stage === st.stage && props.layer === st.layer
}

// ≈, not = (the director wanted it clear that this is an
// approximation): the deeper dive's #superposition entry has the why.
const DEF_POST_S: Ch2EqName = 'def_post_s_v2'
/** The definition at 1.75 CSS px per bp (≈ 17 px math). */
const defBox = {
  width: `${CH2_EQ[DEF_POST_S].w * 1.75}px`,
  height: `${CH2_EQ[DEF_POST_S].h * 1.75}px`,
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'June', 'July', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
function fmt(iso: string | null): string {
  if (!iso) return ''
  const [y, m, d] = iso.split('-')
  return `${parseInt(d, 10)} ${MONTHS[parseInt(m, 10) - 1] ?? ''} ${y}`
}

const rootEl = ref<HTMLElement | null>(null)
const left = ref(0)
const top = ref(0)
const visible = ref(false)
/** The type scale: 1 = 15 px station type; below 1 only when the seven
 *  stations would not otherwise fit the room (measured per width). */
const k = ref(1)
/** Tight = less tracking, padding and connector (the type unchanged) —
 *  tried before the type shrinks (1280 × 800). */
const tight = ref(false)
/** Where the keys hung under the row right-align (blockAnchor.ts
 *  useInsetKeyAnchor): left of the stress space, as before the row. */
const keyRight = ref(0)
let rafId = 0
let chromeBottom = 100
let insetRight = 0
let chromeFrame = 0
let panelLeft = Infinity
let fitAtW = 0
let natW = 0
// The stress space's left edge (Ch2Results .cr-single): measured while it
// is up; otherwise its own CSS formula, so the keys sit in the same place
// on the imagery beats and never slide when the diagram arrives.
function stressSpaceLeft(W: number, H: number, chromeB: number): number {
  const el = document.querySelector('.cr-single')?.getBoundingClientRect()
  if (el && el.width > 0) return el.left
  // Ch2Results.vue .cr-root: --ss-top / --ss-w, .cr-single right 2.2vw
  const rem = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16
  const ssTop = Math.max(chromeB + 0.9 * rem, 0.062 * H + 2.8 * rem)
  const ssW = Math.min(0.46 * W, ((H - ssTop - 0.025 * H) * 674) / 680)
  return W - 0.022 * W - ssW
}

function tick(): void {
  const proj = (window as any).__simDomainScreen as
    | { x: number; topY: number; flowTopY?: number; visible: boolean; spread: number }
    | null
  const el = rootEl.value
  // spread gate: the stations appear once the block is the subject (the
  // zoom settled), not while it's a speck mid-dive.
  if (proj && proj.visible && proj.spread > 260 && el) {
    const W = window.innerWidth
    // The sub-menu / Back-Next bottom and the centre-lakes inset's right
    // edge, re-measured a few times a second.
    if (chromeFrame++ % 20 === 0) {
      let b = 0
      for (const sel of ['.landmarks', '.beat-nav']) {
        const r = document.querySelector(sel)?.getBoundingClientRect()
        if (r && r.height > 0) b = Math.max(b, r.bottom)
      }
      chromeBottom = b || 100
      const ir = document.querySelector('.ccl')?.getBoundingClientRect()
      insetRight = ir && ir.width > 0 ? ir.right : 0.02 * W + 220
      panelLeft = stressSpaceLeft(W, window.innerHeight, chromeBottom)
    }
    // The room: the inset's right edge to the right gutter (the stress
    // space's own right edge, 2.2vw).
    const minL = insetRight + 18
    const maxR = W - 0.022 * W
    const room = maxR - minL
    // A new window width: measure the row at full size, then fit it.
    if (W !== fitAtW) {
      fitAtW = W
      k.value = 1
      tight.value = false
      natW = 0
      rafId = requestAnimationFrame(tick)
      return
    }
    if (!natW) {
      natW = el.offsetWidth
      if (natW > room && !tight.value) {
        // first the spacing, measured again next frame…
        tight.value = true
        natW = 0
        rafId = requestAnimationFrame(tick)
        return
      }
      // …then, never two rows: shrink the type until the seven fit
      k.value = Math.min(1, room / natW)
    }
    const w = el.offsetWidth
    // Centred on the screen (under the centred menu and sub-menu) where
    // the room allows, else pushed right of the inset — the stations run
    // the width of the screen above the block and the stress space.
    left.value = Math.max(minL, Math.min(W / 2 - w / 2, maxR - w))
    top.value = chromeBottom + 14
    keyRight.value = Math.min(left.value + w, panelLeft - 24)
    // The stress space starts under the row (Ch2Results --ss-top).
    document.documentElement.style.setProperty('--svc-bottom', `${Math.round(top.value + el.offsetHeight)}px`)
    // Boundary-conditions overview (SimBcCards): the block sits inside
    // the ghost model domain with a card on every side — the row pins
    // top-centre under the sub-menu instead of hovering on the domain.
    if ((window as any).__simBcActive) {
      left.value = W / 2 - w / 2
      top.value = chromeBottom + 14
    }
    visible.value = true
  } else if (!(window as any).__ch2Hop) {
    // (Chapter 2's hop between the center lakes: the block is rebuilt
    // under a black dip — the stations stay where they are through it.)
    visible.value = false
  }
  rafId = requestAnimationFrame(tick)
}

onMounted(() => { rafId = requestAnimationFrame(tick) })
onBeforeUnmount(() => {
  cancelAnimationFrame(rafId)
  document.documentElement.style.removeProperty('--svc-bottom')
})
</script>

<style scoped>
.svc {
  position: absolute;
  z-index: 12;
  pointer-events: none;
  /* 15 px station type at k = 1 (projector legibility) */
  font-size: calc(15px * var(--svc-k, 1));
}

.svc-row {
  display: flex;
  align-items: flex-start;
  white-space: nowrap;
}

.svc-cell {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.22rem;
}

/* The connector between stations: the walk runs left → right in time. */
.svc-link {
  flex: 0 0 auto;
  width: 0.75em;
  height: 1.5px;
  margin-top: 1.45em;
  background: rgba(245, 199, 94, 0.7);
}

/* A station — the SlabActionButton language (upper case, gold on black),
   two lines: the stage over the layer. */
.svc-st {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.12em;
  border: 1.5px solid var(--gold);
  background: rgba(8, 6, 4, 0.78);
  color: var(--gold-bright);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1em;
  font-weight: 600;
  line-height: 1.15;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 0.42em 0.8em;
  border-radius: 1.4em;
  cursor: pointer;
  pointer-events: auto;
  white-space: nowrap;
  backdrop-filter: blur(8px);
  box-shadow:
    0 6px 28px rgba(0, 0, 0, 0.55),
    0 0 22px rgba(245, 199, 94, 0.18);
  transition: color 0.2s, border-color 0.2s, background 0.2s, box-shadow 0.2s, opacity 0.2s;
}
.svc-st:hover {
  color: #fff8d8;
  background: rgba(56, 38, 12, 0.85);
}
.svc-layer {
  font-weight: 500;
}
/* σ_t1 / Δσ_t1: math, never upper-cased (σ would become Σ) */
.svc-sym {
  margin-left: 0.4em;
  font-family: 'EB Garamond', serif;
  font-style: italic;
  font-size: 1.12em;
  font-weight: 500;
  letter-spacing: 0;
  text-transform: none;
}
.svc-sym sub {
  font-size: 0.7em;
  font-style: italic;
  vertical-align: -0.25em;
  line-height: 0;
}

/* The dates: a figure label in EB Garamond numerals under the imagery. */
.svc-date {
  min-height: 1.15rem;
  font-family: 'EB Garamond', serif;
  font-size: 1.12rem;
  line-height: 1.15;
  letter-spacing: 0.02em;
  font-variant-numeric: lining-nums;
  color: rgba(232, 185, 74, 0.88);
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.95);
  transition: color 0.2s;
}
.svc-date-on { color: var(--gold-bright); }

/* Tight: the spacing gives before the type does. */
.svc-tight .svc-st { letter-spacing: 0.035em; padding-left: 0.6em; padding-right: 0.6em; }
.svc-tight .svc-link { width: 0.45em; }

/* POST · ELASTIC's definition, hung under its station (centred). */
.svc-def {
  position: absolute;
  top: calc(100% + 0.45rem);
  left: 50%;
  transform: translateX(-50%);
  max-width: none;
  filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.95));
  pointer-events: none;
}

/* …and the note under it (small, same place, that beat only) */
.svc-def-note {
  position: absolute;
  top: calc(100% + 0.45rem + 15px * 1.75 + 0.3rem);
  left: 50%;
  transform: translateX(-50%);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.8em;
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: none;
  color: rgba(232, 185, 74, 0.9);
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.95);
  white-space: nowrap;
  pointer-events: none;
}

/* The stations NOT lit step back a tad (the director asked for the
   unselected buttons faded just a touch, to reduce distraction) —
   still gold on black from the back row; hover brings one back. */
.svc-st:not(.svc-on) {
  opacity: 0.72;
}
.svc-st:not(.svc-on):hover {
  opacity: 1;
}

.svc-on,
.svc-on:hover {
  color: #1c1305;
  background: var(--gold);
  border-color: var(--gold);
  box-shadow:
    0 6px 28px rgba(0, 0, 0, 0.55),
    0 0 30px rgba(245, 199, 94, 0.45);
}
</style>
