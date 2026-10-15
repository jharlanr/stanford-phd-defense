<template>
  <!-- The section's sub-menu: a slim bar hanging under
       the ribbon across its middle 75 %, in the ribbon's own glass. The
       landmark words ARE the notches, set on the bar's midline with a
       hairline running between them — gold up to where you are, a lit
       bead at its tip; walked words warm, the current one lit gold with a
       faint underline, the ones ahead dim (the docked network map's
       warm → lit → dim). A word is a jump, not a next: the shared
       back/next pills stay the site's one path. Landmarks and counts:
       config/landmarks.ts. -->
  <div class="landmarks" role="group" aria-label="Section landmarks">
    <div ref="trackEl" class="lm-track">
      <div class="lm-rule" :style="maskStyle" />
      <div class="lm-fill" :style="{ width: px(fillPx), ...maskStyle }" />
      <div class="lm-bead" :class="{ hidden: beadHidden }" :style="{ left: px(fillPx) }" />
      <button
        v-for="(l, i) in data.landmarks"
        :key="l.id"
        class="lm-notch"
        :class="{ current: i === cur, passed: i < cur }"
        :style="{ left: pct(pos[i]) }"
        :aria-current="i === cur ? 'step' : undefined"
        @click="emit('jump', l.beat)"
      >
        <span :ref="(el) => setLabel(el as HTMLElement | null, i)" class="lm-label">{{ l.label }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { beatFraction, currentLandmark, notchPositions, type SectionLandmarks } from '../config/landmarks'

const props = defineProps<{
  data: SectionLandmarks
  /** The section's current beat. */
  beat: number
}>()
const emit = defineEmits<{ jump: [beat: number] }>()

// The track's width, the bar's side padding and each word's width (px):
// the words are laid out — and the hairline broken around them — from
// their measured widths, re-read on resize and once the fonts land.
const trackEl = ref<HTMLElement | null>(null)
const trackW = ref(0)
const padW = ref(0)
const labelW = ref<number[]>([])
const labelEls: (HTMLElement | null)[] = []
function setLabel(el: HTMLElement | null, i: number): void {
  labelEls[i] = el
}
function measure(): void {
  const t = trackEl.value
  trackW.value = t?.clientWidth ?? 0
  padW.value = t?.parentElement ? parseFloat(getComputedStyle(t.parentElement).paddingLeft) || 0 : 0
  labelW.value = props.data.landmarks.map((_, i) => labelEls[i]?.offsetWidth ?? 0)
}
let ro: ResizeObserver | null = null
onMounted(() => {
  measure()
  ro = new ResizeObserver(measure)
  if (trackEl.value) ro.observe(trackEl.value)
  document.fonts?.ready.then(measure).catch(() => {})
})
onBeforeUnmount(() => ro?.disconnect())

/** Clear air between a word and the hairline (px). */
const GAP = 7
/** The shortest hairline left between two words (px). */
const MIN_RULE = 30
/** How far inside the bar's rounded ends the end words stop (px). */
const END_INSET = 18

// Notch positions (0 … 1 of the track): proportional to the beat, with
// neighbouring words kept a whole word-plus-hairline apart and the end
// words kept inside the capsule (config/landmarks.ts notchPositions).
const pos = computed(() => {
  const W = trackW.value
  const lw = labelW.value
  const n = props.data.landmarks.length
  if (!W || lw.length !== n || lw.some((w) => !w)) return notchPositions(props.data)
  const hw = lw.map((w) => w / 2)
  const gaps = hw.slice(1).map((h, i) => (hw[i] + h + 2 * GAP + MIN_RULE) / W)
  const reach = padW.value - END_INSET
  const lo = Math.max(0, (hw[0] - reach) / W)
  const hi = Math.min(1, 1 - (hw[n - 1] - reach) / W)
  return notchPositions(props.data, gaps, lo, hi)
})
const fill = computed(() => beatFraction(props.data, props.beat, pos.value))
const cur = computed(() => currentLandmark(props.data.landmarks, props.beat))
const fillPx = computed(() => fill.value * trackW.value)

/** Each word's clear zone along the track (px). */
const zones = computed(() => {
  const W = trackW.value
  return pos.value.map((p, i) => {
    const hw = (labelW.value[i] ?? 0) / 2 + GAP
    return [p * W - hw, p * W + hw] as const
  })
})
// One mask for the rule and its gold fill: opaque between the words,
// clear under them, the run past the last word fading out (the section's
// closing beats). One element each, so the fill sweeps as one line.
const mask = computed(() => {
  const W = trackW.value
  if (!W) return 'none'
  const stops: string[] = []
  let a = 0
  for (const [z0, z1] of zones.value) {
    if (z0 > a) stops.push(`#000 ${px(a)}`, `#000 ${px(z0)}`)
    stops.push(`transparent ${px(Math.max(a, z0))}`, `transparent ${px(z1)}`)
    a = Math.max(a, z1)
  }
  if (W > a + 2) stops.push(`#000 ${px(a)}`, `#000 ${px(a + 0.4 * (W - a))}`, `transparent ${px(W)}`)
  return `linear-gradient(90deg, ${stops.join(', ')})`
})
// Laid against the whole track (px), so the fill — narrower than the
// track — wears the same stencil as the rule under it.
const maskStyle = computed(() => {
  const size = `${px(trackW.value)} 100%`
  return { maskImage: mask.value, WebkitMaskImage: mask.value, maskSize: size, WebkitMaskSize: size }
})
// The bead rides the fill's tip; on a landmark's own beat it sits under
// that word, which is lit instead.
const beadHidden = computed(() => zones.value.some(([z0, z1]) => fillPx.value > z0 && fillPx.value < z1))

function pct(v: number): string {
  return `${(v * 100).toFixed(3)}%`
}
function px(v: number): string {
  return `${v.toFixed(2)}px`
}
</script>

<style scoped>
/* Hung from the ribbon wrapper's bottom edge (Explore .top-nav-wrap is
   exactly the ribbon's box), so percentages are the ribbon's own width:
   the TRACK spans its middle 75 %; the bar's side padding holds the end
   words. Its box is what the layout solvers steer clear of
   (IntroFlowSites, EssdLakePanels, the Introduction's dims labels). */
.landmarks {
  --lm-pad: 3rem;
  --lm-ls: 0.15em;
  --lm-ease: cubic-bezier(0.4, 0, 0.2, 1);
  position: absolute;
  left: calc(12.5% - var(--lm-pad));
  /* …and, when the back/next pills drop to this row (Explore's narrow
     breakpoint), its right end stops 16 px short of them: the wrapper is
     centred, so its right edge sits at 50vw + 50 %, the pills start at
     98vw − --pills-w. Never binds while the pills ride the ribbon's row. */
  right: max(calc(12.5% - var(--lm-pad)), calc(50% - 48vw + var(--pills-w, 13.3rem) + 16px));
  /* gap + height live on Explore's .explore (--lm-gap, --lm-h): the
     overlays that open under the chrome read the same numbers. */
  top: calc(100% + var(--lm-gap, 0.3rem));
  height: var(--lm-h, 1.75rem);
  padding: 0 var(--lm-pad);
  box-sizing: border-box;
  /* The ribbon's own material (Explore .top-nav). */
  background: rgba(0, 0, 0, 0.6);
  /* 1 → 1.5 px and stronger, for projector contrast */
  border: 1.5px solid rgba(232, 185, 74, 0.38);
  border-radius: 999px;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  pointer-events: none;
}

.lm-track {
  position: relative;
  height: 100%;
}

.lm-rule,
.lm-fill {
  position: absolute;
  left: 0;
  top: 50%;
  height: 1.5px;
  margin-top: -0.75px;
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
}
.lm-rule {
  right: 0;
  background: rgba(232, 185, 74, 0.36);
}
.lm-fill {
  background: rgba(232, 185, 74, 0.9);
  transition: width 0.6s var(--lm-ease);
}

.lm-bead {
  position: absolute;
  top: 50%;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--gold-bright);
  box-shadow: 0 0 0 2px rgba(244, 207, 106, 0.16), 0 0 8px rgba(244, 207, 106, 0.7);
  transform: translate(-50%, -50%);
  transition: left 0.6s var(--lm-ease), opacity 0.3s;
  pointer-events: none;
}
.lm-bead.hidden {
  opacity: 0;
}

/* A notch = its word, centred on its position; the padded word is the
   click target. */
.lm-notch {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.3rem 0.4rem;
  background: none;
  border: 0;
  cursor: pointer;
  pointer-events: auto;
  font-family: 'Inter', system-ui, sans-serif;
}

.lm-label {
  position: relative;
  display: block;
  /* 0.64 → 0.8rem (10.2 → 12.8 px), for the back row */
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1;
  letter-spacing: var(--lm-ls);
  /* The trailing tracking would push the word off its notch. */
  margin-right: calc(-1 * var(--lm-ls));
  text-transform: uppercase;
  white-space: nowrap;
  color: rgba(232, 185, 74, 0.72);
  transition: color 0.25s ease, transform 0.25s ease, text-shadow 0.25s ease;
}
.lm-notch.passed .lm-label {
  color: rgba(232, 185, 74, 0.92);
}
.lm-notch.current .lm-label {
  color: var(--gold-bright);
  text-shadow: 0 0 10px rgba(244, 207, 106, 0.45);
}
/* The current word's faint gold underline. */
.lm-label::after {
  content: '';
  position: absolute;
  left: 0;
  right: var(--lm-ls);
  bottom: -4px;
  height: 1.5px;
  background: linear-gradient(90deg, transparent, rgba(244, 207, 106, 0.7), transparent);
  opacity: 0;
  transition: opacity 0.3s ease;
}
.lm-notch.current .lm-label::after {
  opacity: 1;
}

/* Hover: the word brightens (the ribbon's own hover gold) and lifts a
   pixel; the lit word goes to the ribbon's active cream. */
.lm-notch:hover .lm-label,
.lm-notch:focus-visible .lm-label {
  color: var(--gold-bright);
  transform: translateY(-1px);
}
.lm-notch.current:hover .lm-label,
.lm-notch.current:focus-visible .lm-label {
  color: #fff8d8;
}
.lm-notch:focus {
  outline: none;
}
</style>
