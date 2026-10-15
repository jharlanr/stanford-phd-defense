<template>
  <!-- The Acknowledgements page: a flat opaque layer above the live globe,
       like SectionRepos — the globe keeps rendering beneath, never veiled.
       One route; NEXT/BACK walk the steps (overview, one group at a time,
       the full page again). -->
  <!-- On a split-out step, clicking off into blank space returns to the
       acknowledgements overview — a click that
       lands on this root itself (the faces, names and links sit above it
       with their own pointer-events; the pills/ribbon live outside it)
       is blank space, and goes to the overview the way the pills would. -->
  <div class="ak" :class="{ 'ak--split': splitGroup !== null }" @click.self="onBlankClick">
    <div class="ak-inner">
      <header class="ak-head">
        <h2 class="ak-title">Acknowledgements</h2>
      </header>

      <!-- THE GROUPS -->
      <div class="ak-groups">
        <!-- The director wanted any section of the acknowledgements to be
             clickable, popping up that group's photos
             — every group with a split-out step is a subtle button
             that jumps to that step; NEXT/BACK carry on from there. -->
        <!-- One grid cell per group, except a `stackUnder` group, whose card
             sits under the previous one in the same cell (the
             small Earlier advisors card under Fieldwork teammates). -->
        <div v-for="cell in overviewCells" :key="cell[0]" class="ak-cell">
          <section
            v-for="gi in cell"
            :key="PUBLIC_GROUPS[gi].heading"
            class="ak-group"
            :class="{ 'ak-group--lifted': splitShown === gi, 'ak-group--btn': stepOfGroup(gi) >= 0 }"
            :role="stepOfGroup(gi) >= 0 ? 'button' : undefined"
            :tabindex="stepOfGroup(gi) >= 0 ? 0 : undefined"
            :aria-label="stepOfGroup(gi) >= 0 ? `Show ${PUBLIC_GROUPS[gi].heading}` : undefined"
            @click="goGroup(gi)"
            @keydown.enter.self.prevent="goGroup(gi)"
            @keydown.space.self.prevent="goGroup(gi)"
          >
            <h3 ref="overviewHeads" class="ak-group-head" :data-gi="gi">{{ PUBLIC_GROUPS[gi].heading }}</h3>
            <ul class="ak-names" :class="{ 'ak-names--todo': PUBLIC_GROUPS[gi].placeholder }">
              <!-- The roles are under the faces on the split-out only —
                   the overview list carries no "Second project advisor"
                   or "Master's advisor" lines.
                   A name with a site is a link (new tab) —
                   the click stops here so the group doesn't also open.
                   The bare name only — no "(U. Oxford)"; the
                   affiliation prints under the face on the step. -->
              <li v-for="n in PUBLIC_GROUPS[gi].names" :key="ackNameText(n)">
                <a
                  v-if="siteOf(n)"
                  class="ak-name-link"
                  :href="siteOf(n)"
                  target="_blank"
                  rel="noopener"
                  @click.stop
                >{{ ackNameText(n) }}</a>
                <template v-else>{{ ackNameText(n) }}</template>
              </li>
            </ul>
          </section>
        </div>
      </div>

    </div>

    <!-- THE SPLIT-OUT: one group per NEXT, lifted out
         of the overview — its heading flies from its column head to the
         top (FLIP in onSplitEnter), the faces rise in under it. No prose:
         heading, faces, names, the affiliation the config already gives. -->
    <Transition :css="false" @enter="onSplitEnter" @leave="onSplitLeave">
      <!-- Keyed by the group whose ROW is shown, so an isolate step
           (a group whose step borrows another group's row)
           keeps the layer — and the faces — on screen: the others fade
           back, the kept face stays lit, the newcomer joins beside it. -->
      <div v-if="splitShown !== null" :key="splitShown" class="ak-split" :data-gi="splitShown">
        <h3 class="ak-split-head">{{ PUBLIC_GROUPS[splitShown].heading }}</h3>
        <ul
          class="ak-faces"
          :class="[
            `ak-faces--n${splitTiles.length}`,
            { 'ak-faces--wrap': splitTiles.length > 7, 'ak-faces--wrap7': splitTiles.length > 10 },
          ]"
        >
          <li
            v-for="({ p, back, join }, i) in splitTiles"
            :key="p.slug"
            class="ak-face"
            :class="{ 'ak-face--back': back, 'ak-face--join': join }"
            :style="{ '--i': i }"
          >
            <!-- Clicking a name or headshot opens that person's own
                 website, if they have one — face + name are one link
                 (new tab) when the manifest has a site; otherwise the
                 same tile, unlinked. -->
            <component
              :is="faceOf(p).url ? 'a' : 'div'"
              class="ak-face-tile"
              :class="{ 'ak-face-tile--link': !!faceOf(p).url }"
              :href="faceOf(p).url"
              :target="faceOf(p).url ? '_blank' : undefined"
              :rel="faceOf(p).url ? 'noopener' : undefined"
            >
              <div class="ak-portrait" :class="`ak-portrait--${faceOf(p).kind}`">
                <img
                  v-if="faceOf(p).kind === 'photo' || faceOf(p).kind === 'logo'"
                  :src="faceSrc(p)!"
                  :alt="p.display"
                  :style="faceOf(p).filter ? { filter: faceOf(p).filter } : undefined"
                  decoding="sync"
                  draggable="false"
                />
                <span v-else-if="faceOf(p).kind === 'text'" class="ak-portrait-text">{{ p.display }}</span>
                <span v-else class="ak-portrait-initials">{{ p.initials }}</span>
              </div>
              <div v-if="faceOf(p).kind !== 'text'" class="ak-face-name">{{ p.display }}</div>
              <div v-if="p.role" class="ak-face-sub">{{ p.role }}</div>
              <div v-if="p.affil" class="ak-face-sub">{{ p.affil }}</div>
            </component>
            <!-- Under a group card (Princeton AOS): a small list of
                 people, each with a small round headshot to the left of
                 the name in place of the bullet point (ACK_GROUP_PEOPLE). -->
            <ul v-if="peopleUnder(p).length" class="ak-sublist">
              <li v-for="q in peopleUnder(p)" :key="q.slug" class="ak-sub">
                <component
                  :is="faceOf(q).url ? 'a' : 'span'"
                  class="ak-sub-row"
                  :class="{ 'ak-sub-row--link': !!faceOf(q).url }"
                  :href="faceOf(q).url"
                  :target="faceOf(q).url ? '_blank' : undefined"
                  :rel="faceOf(q).url ? 'noopener' : undefined"
                >
                  <span class="ak-mini" :class="`ak-mini--${faceOf(q).kind}`">
                    <img v-if="faceSrc(q)" :src="faceSrc(q)!" :alt="q.display" decoding="sync" draggable="false" />
                    <span v-else class="ak-mini-initials">{{ q.initials }}</span>
                  </span>
                  <span class="ak-sub-name">{{ q.display }}</span>
                </component>
              </li>
            </ul>
          </li>
        </ul>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  PUBLIC_GROUPS,
  ACK_STEPS,
  ACK_GROUP_PEOPLE,
  parseAckName,
  ackNameText,
  type AckGroup,
  type AckName,
  type AckPerson,
} from '../../config/acknowledgements'
import { ACK_HEADSHOTS, type AckFace } from '../../config/ackHeadshots.gen'
import { mediaUrl } from '../../config/media'
import { parseBeatParam } from '../../config/sitePath'

// Next/back are the site's shared pills (Explore's .beat-nav,
// config/sitePath.ts): this is a beat page — the pills bump
// advanceTrigger / backTrigger, one step of ACK_STEPS per bump; the last
// step's next emits `advance` (the path goes on), step 0's back is
// Explore's.
const props = defineProps<{
  advanceTrigger?: number
  backTrigger?: number
}>()
const emit = defineEmits<{
  'beat-change': [value: number, isLast: boolean]
  advance: []
}>()
const route = useRoute()

const step = ref(0)
const splitGroup = computed<number | null>(() => {
  const s = ACK_STEPS[step.value]
  return s?.kind === 'group' ? s.group : null
})
/** The group a split-out step's `isolate` borrows the row of, or -1. */
function isolateBase(g: AckGroup): number {
  return g.isolate ? PUBLIC_GROUPS.findIndex((h) => h.heading === g.isolate!.withGroup) : -1
}
/** The group whose heading + row the split-out layer shows: the step's own,
 *  or for an isolate step the group it borrows. */
const splitShown = computed<number | null>(() => {
  if (splitGroup.value === null) return null
  const base = isolateBase(PUBLIC_GROUPS[splitGroup.value])
  return base >= 0 ? base : splitGroup.value
})
type SplitTile = { p: AckPerson; back: boolean; join: boolean }
/** The faces on a split-out step. An isolate step (one face of another
 *  row kept lit, the newcomers joining it) = the borrowed row, every face but
 *  `keep` faded back, then the step's own people joining at the end — beside
 *  the kept face, which is last in its row. */
const splitTiles = computed<SplitTile[]>(() => {
  if (splitGroup.value === null) return []
  const g = PUBLIC_GROUPS[splitGroup.value]
  const own = g.names.map(parseAckName)
  const base = isolateBase(g)
  if (base < 0) return own.map((p) => ({ p, back: false, join: false }))
  const keep = parseAckName(g.isolate!.keep).slug
  return [
    ...PUBLIC_GROUPS[base].names.map(parseAckName).map((p) => ({ p, back: p.slug !== keep, join: false })),
    ...own.map((p) => ({ p, back: false, join: true })),
  ]
})
/** The overview's grid cells: group indices, a `stackUnder` group joining
 *  the cell before it. */
const overviewCells = computed<number[][]>(() => {
  const cells: number[][] = []
  PUBLIC_GROUPS.forEach((g, gi) => {
    if (g.stackUnder && cells.length) cells[cells.length - 1].push(gi)
    else cells.push([gi])
  })
  return cells
})

function faceOf(p: AckPerson): AckFace {
  return ACK_HEADSHOTS[p.slug] ?? { kind: 'initials' }
}
function faceSrc(p: AckPerson): string | null {
  const f = faceOf(p)
  return f.kind === 'photo' || f.kind === 'logo' ? mediaUrl(f.key) : null
}
/** The person's site for an overview name line (headshots.json `url`), if any. */
function siteOf(n: AckName): string | undefined {
  return faceOf(parseAckName(n)).url
}
/** The small list under a group's card on its split-out step (ACK_GROUP_PEOPLE). */
function peopleUnder(p: AckPerson): AckPerson[] {
  return (ACK_GROUP_PEOPLE[p.display] ?? []).map(parseAckName)
}

function report(): void {
  emit('beat-change', step.value, step.value === ACK_STEPS.length - 1)
}
function next(): void {
  if (step.value >= ACK_STEPS.length - 1) {
    emit('advance')
    return
  }
  step.value += 1
  report()
}
function prev(): void {
  if (step.value <= 0) return
  step.value -= 1
  report()
}
/** The ACK_STEPS index of a group's split-out step, or -1 (no step). */
function stepOfGroup(gi: number): number {
  return ACK_STEPS.findIndex((s) => s.kind === 'group' && s.group === gi)
}
function goGroup(gi: number): void {
  const k = stepOfGroup(gi)
  if (k < 0 || step.value === k) return
  step.value = k
  report()
}
/** Blank space on a split-out step → the overview (step 0), the pills' own path. */
function onBlankClick(): void {
  if (splitGroup.value === null) return
  step.value = 0
  report()
}
watch(() => props.advanceTrigger, (v, old) => {
  if (v != null && v !== old) next()
})
watch(() => props.backTrigger, (v, old) => {
  if (v != null && v !== old) prev()
})

// Pre-warm every face on the overview so no step's images pop in late:
// the same plain <img> request the split-out makes, decoded now, held so
// the decoded bitmaps stay warm.
const warm: HTMLImageElement[] = []
function prewarm(): void {
  const seen = new Set<string>()
  // The group lines plus the small lists under the group cards.
  const lines: AckName[] = PUBLIC_GROUPS.flatMap((g) => (g.placeholder ? [] : g.names))
  for (const under of Object.values(ACK_GROUP_PEOPLE)) lines.push(...under)
  for (const n of lines) {
    const src = faceSrc(parseAckName(n))
    if (!src || seen.has(src)) continue
    seen.add(src)
    const im = new Image()
    im.decoding = 'async'
    im.src = src
    im.decode().catch(() => {})
    warm.push(im)
  }
}

onMounted(() => {
  step.value = parseBeatParam(route.query.beat, ACK_STEPS.length)
  report()
  prewarm()
})
onBeforeUnmount(() => {
  warm.length = 0
})

// ── the lift ────────────────────────────────────────────────────────
// The split heading starts where its column head sits in the overview
// (position + scale), and flies to its own place; the faces rise in,
// staggered by CSS (--i). Leaving, the layer simply fades. Durations are
// short — the remote may be pressed quickly.
const overviewHeads = ref<HTMLElement[]>([])
const LIFT_MS = 620
const EASE = 'cubic-bezier(0.22, 0.8, 0.24, 1)'
function onSplitEnter(el: Element, done: () => void): void {
  const layer = el as HTMLElement
  const gi = Number(layer.dataset.gi)
  const head = layer.querySelector<HTMLElement>('.ak-split-head')
  const src = overviewHeads.value.find((h) => Number(h.dataset.gi) === gi)
  layer.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 260, easing: 'ease-out', fill: 'backwards' })
  // A joining face (isolate step) brings its own entrance (CSS ak-join).
  const faces = layer.querySelectorAll<HTMLElement>('.ak-face:not(.ak-face--join)')
  faces.forEach((f, i) => {
    f.animate(
      [
        { opacity: 0, transform: 'translateY(28px) scale(0.96)' },
        { opacity: 1, transform: 'none' },
      ],
      { duration: 560, delay: 140 + i * 55, easing: EASE, fill: 'backwards' },
    )
  })
  if (head && src) {
    const a = src.getBoundingClientRect()
    const b = head.getBoundingClientRect()
    // Scale by text height (the two are different fonts and sizes);
    // anchor at the heading's top-centre so it reads as one object moving.
    const k = b.height > 0 ? a.height / b.height : 1
    const dx = a.left + a.width / 2 - (b.left + b.width / 2)
    const dy = a.top - b.top
    head.style.transformOrigin = '50% 0'
    const anim = head.animate(
      [
        { transform: `translate(${dx}px, ${dy}px) scale(${k})`, opacity: 0.6 },
        { transform: 'none', opacity: 1 },
      ],
      { duration: LIFT_MS, easing: EASE },
    )
    anim.onfinish = () => done()
    anim.oncancel = () => done()
  } else {
    window.setTimeout(done, LIFT_MS)
  }
}
function onSplitLeave(el: Element, done: () => void): void {
  const anim = (el as HTMLElement).animate([{ opacity: 1 }, { opacity: 0 }], {
    duration: 220,
    easing: 'ease-in',
    fill: 'forwards',
  })
  anim.onfinish = () => done()
  anim.oncancel = () => done()
}

</script>

<style scoped>
.ak {
  position: fixed;
  inset: 0;
  z-index: 1;
  overflow-y: auto;
  background: radial-gradient(ellipse at 50% 0%, #0f1420 0%, #050505 60%);
  color: #f5f5f5;
  font-family: 'Inter', system-ui, sans-serif;
  padding: 7vh 3vw 3vh;
  box-sizing: border-box;
  pointer-events: auto;
}

.ak-inner {
  max-width: 1260px;
  margin: 0 auto;
}

.ak-head {
  text-align: center;
  /* The overview carries 13 coauthors and 7 post-doc mentors; the rhythm
     below is a notch tighter so the whole grid still sits on a 1440×900
     screen. Same layout. */
  margin-bottom: 1rem;
}

.ak-title {
  font-family: 'EB Garamond', serif;
  font-weight: 400;
  font-size: 2.4rem;
  color: var(--gold);
  margin: 0;
  letter-spacing: 0.02em;
}

.ak-sub {
  margin: 0.15rem 0 0;
  color: rgba(244, 207, 106, 0.88);
  font-size: 1rem;
  letter-spacing: 0.04em;
}

/* ── the groups ───────────────────────────────────────────── */

.ak-groups {
  display: grid;
  /* The director asked that a name such as "Laura A. Stevens" never break
     across two lines: a name never wraps (.ak-names li below),
     so a column's floor is its own longest name instead of a fixed 250 px.
     Four equal columns (298 px at 1440, a 264 px name line) cannot hold
     "Prof. Olivier Gagliardini (U. Grenoble Alpes)" (341 px at 16.8 px) or
     "Prof. Laura A. Stevens (U. Oxford)" (268 px) without dropping to
     ~13 px, so the names keep their size and that column takes the width
     it needs: 1fr still shares the row equally, and any column whose
     longest name is wider than its share is held at that name's width
     while the others split the rest. Same 4 × 2 grid, same row heights.
     The director then found the left-hand cards too wide and moved the
     parenthesised institutions out of the cards and under the faces on
     the split-out step: the overview prints bare names now, so the longest
     line is "Prof. Olivier Gagliardini" (~210 px) and no column outgrows
     its 1fr share — the four columns are equal again at 1440 and 1280. */
  grid-template-columns: repeat(4, minmax(min-content, 1fr));
  gap: 1rem 1.4rem;
  border-top: 1px solid rgba(232, 185, 74, 0.35);
  padding-top: 1.1rem;
}
/* A window narrower than the 1260 px page (the 1280×800 check): the
   External column still takes its 375 px, so the other three get tight —
   16 px gutters (and a hair less card padding, .ak-group below) keep
   "FIELDWORK TEAMMATES" (219 px) on one line there, as it was. A 1440
   window never sees this. */
@media (min-width: 1181px) and (max-width: 1339px) {
  .ak-groups {
    column-gap: 1rem;
  }
}
/* A window too narrow for the four no-wrap columns (they need ~1073 px of
   page, i.e. a ~1141 px window): exactly the grid this page had before —
   as many 250 px columns as fit, names free to wrap. Not a talk size. */
@media (max-width: 1180px) {
  .ak-groups {
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  }
}

/* A grid cell: one card, or a card with a `stackUnder` card beneath it.
   Stacked cards SHARE the cell's height equally (the director wanted the
   Internship mentors card and the Research groups card the same size);
   a card never shrinks below its names (the
   default min-height of a column flex item), so Fieldwork teammates keeps
   its six lines and Earlier advisors takes the rest. Bottoms line up. */
.ak-cell {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.ak-cell > .ak-group {
  flex: 1 1 0;
}

.ak-group {
  border-radius: 10px;
  padding: 0.8rem 1rem 0.7rem;
}
@media (min-width: 1181px) and (max-width: 1339px) {
  .ak-group {
    padding-inline: 0.9rem;
  }
}
/* A group you can open: a faint outline + a slightly lighter ground,
   brighter on hover. Legible from the back row, never loud. */
.ak-group--btn {
  cursor: pointer;
  border: 1.5px solid rgba(232, 185, 74, 0.28);
  background: rgba(255, 255, 255, 0.045);
  transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
}
.ak-group--btn:hover,
.ak-group--btn:focus-visible {
  border-color: rgba(244, 207, 106, 0.75);
  background: rgba(255, 255, 255, 0.09);
  box-shadow: 0 0 0 1px rgba(244, 207, 106, 0.25);
  outline: none;
}
.ak-group:not(.ak-group--btn) {
  border: 1.5px solid transparent;
}
.ak-group-head {
  /* the projector legibility pass: was 0.72rem (~11 px) */
  font-size: 0.92rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--gold);
  margin: 0 0 0.7rem;
}

.ak-names {
  list-style: none;
  margin: 0;
  padding: 0;
  font-size: 1.05rem;
  line-height: 1.42;
  color: rgba(245, 245, 245, 0.95);
}

/* One name, one line — see .ak-groups for how the columns
   make room. A placeholder sentence (--todo) is prose and still wraps. */
.ak-names:not(.ak-names--todo) li {
  white-space: nowrap;
}
@media (max-width: 1180px) {
  .ak-names:not(.ak-names--todo) li {
    white-space: normal;
  }
}

.ak-names--todo {
  color: rgba(245, 245, 245, 0.8);
  font-style: italic;
}
/* A name with a site: quiet — same colour, no underline until
   hovered, then a faint gold one. The click stops at the link so the
   group button underneath doesn't open as well. */
.ak-name-link {
  color: inherit;
  text-decoration: none;
  cursor: pointer;
  transition: color 0.15s;
}
.ak-name-link:hover,
.ak-name-link:focus-visible {
  color: #fff;
  text-decoration: underline;
  text-decoration-color: rgba(244, 207, 106, 0.65);
  text-decoration-thickness: 1.5px;
  text-underline-offset: 0.2em;
  outline: none;
}

/* ── the split-out steps ──────────────────────────────────── */

/* The overview stays put underneath, dimmed — the group came out of it. */
.ak-inner {
  transition: opacity 0.45s ease, transform 0.6s cubic-bezier(0.22, 0.8, 0.24, 1), filter 0.45s ease;
}
.ak--split {
  overflow: hidden;
}
.ak--split .ak-inner {
  opacity: 0.09;
  transform: scale(0.985);
  filter: blur(1.5px);
  pointer-events: none;
}
.ak-group-head {
  transition: opacity 0.3s ease;
}
.ak-group--lifted .ak-group-head {
  opacity: 0;
}

/* The closing step: the full page again. */

.ak-split {
  position: fixed;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: clamp(1.6rem, 5vh, 3.4rem);
  padding: 13vh 3vw 6vh;
  box-sizing: border-box;
  pointer-events: none;
}

.ak-split-head {
  margin: 0;
  pointer-events: auto; /* the title is not blank space */
  font-family: 'EB Garamond', serif;
  font-weight: 400;
  font-size: clamp(2.4rem, 4.2vw, 3.6rem);
  line-height: 1.1;
  color: var(--gold);
  letter-spacing: 0.01em;
  text-align: center;
  will-change: transform;
}

/* The faces: one row for up to six. Tile width scales with the window
   (and its height, so 1280×800 still fits name lines under the row). */
.ak-faces {
  /* six tiles + five gaps = 6·13 + 5·2.2 = 89vw at most */
  --tile: min(13vw, 25vh, 230px);
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: nowrap;
  justify-content: center;
  align-items: flex-start;
  gap: 2.2vw;
}
.ak-faces--n4,
.ak-faces--n5 {
  --tile: min(14.5vw, 27vh, 240px);
  gap: 3vw;
}
.ak-faces--n1,
.ak-faces--n2,
.ak-faces--n3 {
  --tile: min(19vw, 33vh, 290px);
  gap: 5vw;
}
/* Seven (the Post-doc mentors): still one row, at the
   smaller tile; eight to ten: two rows of five; eleven or more (the
   Coauthors are thirteen): two rows of seven. Tiles sized so both rows +
   two-line names still fit at 1280×800. */
.ak-faces--n7 {
  --tile: min(11.4vw, 21vh, 190px);
  gap: 2.2vw;
}
.ak-faces--wrap {
  --tile: min(14.5vw, 22vh, 220px);
  --gap: 3vw;
  flex-wrap: wrap;
  gap: 1.6vh var(--gap);
  max-width: calc(5 * var(--tile) + 4 * var(--gap));
}
.ak-faces--wrap7 {
  --tile: min(11.4vw, 21vh, 190px);
  --gap: 2.2vw;
  max-width: calc(7 * var(--tile) + 6 * var(--gap));
}
/* Seven across: the name may run a little wider than its tile (the gap
   absorbs it) at a slightly smaller size, so most names stay one line —
   still ≥ 16 px. */
.ak-faces--n7 .ak-face-name,
.ak-faces--wrap7 .ak-face-name {
  font-size: clamp(1rem, 1.18vw, 1.25rem);
  width: calc(100% + 1.6vw);
  margin-left: -0.8vw;
  margin-right: -0.8vw;
}
/* …and the role line likewise ("Undergrad advisor" on one line at
   1280×800). */
.ak-faces--n7 .ak-face-sub,
.ak-faces--wrap7 .ak-face-sub {
  width: calc(100% + 1.6vw);
  margin-left: -0.8vw;
  margin-right: -0.8vw;
}

.ak-face {
  width: var(--tile);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  /* An isolate step changes the row's tile size (six → seven across):
     the faces ease to it instead of jumping. */
  transition: width 0.6s cubic-bezier(0.22, 0.8, 0.24, 1);
}
.ak-faces {
  transition: gap 0.6s cubic-bezier(0.22, 0.8, 0.24, 1);
}

/* THE ISOLATE STEP (a beat that keeps one face of a row lit and then
   brings a newcomer in beside it): the row's other
   faces fade back, the kept face stays lit, and the newcomer's slot opens
   beside it (its footprint grows from nothing — a negative margin, so the
   tile itself never squeezes and the row never jumps), then the face
   rises in. BACK simply un-fades the row. */
.ak-face-tile {
  transition: opacity 0.5s ease, filter 0.5s ease;
}
.ak-face--back .ak-face-tile {
  opacity: 0.2;
  filter: saturate(0.4);
}
.ak-face--join {
  animation: ak-join-slot 0.6s cubic-bezier(0.22, 0.8, 0.24, 1) 0.35s backwards;
}
.ak-face--join .ak-face-tile {
  animation: ak-join-in 0.6s cubic-bezier(0.22, 0.8, 0.24, 1) 0.8s backwards;
}
@keyframes ak-join-slot {
  from {
    margin-left: calc(-1 * (var(--tile) + 2.2vw));
  }
}
@keyframes ak-join-in {
  from {
    opacity: 0;
    transform: translateY(28px) scale(0.96);
  }
}
/* Face + name as one block; a link when the person has a site:
   pointer cursor and a small lift + gold glow on hover.
   The split layer passes clicks through to the root (blank space →
   overview); the tile and the small rows take their own. */
.ak-face-tile {
  pointer-events: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  color: inherit;
  text-decoration: none;
  width: 100%;
}
.ak-face-tile--link {
  cursor: pointer;
}
.ak-face-tile--link .ak-portrait {
  transition: transform 0.22s cubic-bezier(0.22, 0.8, 0.24, 1), box-shadow 0.22s ease, border-color 0.22s ease,
    width 0.6s cubic-bezier(0.22, 0.8, 0.24, 1), height 0.6s cubic-bezier(0.22, 0.8, 0.24, 1);
}
.ak-face-tile--link:hover .ak-portrait,
.ak-face-tile--link:focus-visible .ak-portrait {
  transform: translateY(-4px);
  border-color: var(--gold);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6), 0 0 0 3px rgba(244, 207, 106, 0.28), 0 0 28px rgba(244, 207, 106, 0.22);
}
.ak-face-tile--link:focus-visible {
  outline: none;
}
.ak-face-tile--link:hover .ak-face-name {
  color: #fff;
}

.ak-portrait {
  width: var(--tile);
  height: var(--tile);
  border-radius: 50%;
  overflow: hidden;
  border: 2px solid rgba(232, 185, 74, 0.55);
  background: #141820;
  box-shadow: 0 10px 34px rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  transition: width 0.6s cubic-bezier(0.22, 0.8, 0.24, 1), height 0.6s cubic-bezier(0.22, 0.8, 0.24, 1);
}
.ak-portrait img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
/* A group, not a person: a soft square. A logo sits whole on a dark
   translucent plate with a faint rim (the director wanted something
   sleeker than a harsh white plate) — the marks (Icy Physics, Mineral-X,
   the AOS badge) all carry their own light or saturated fills, so they
   read on dark. */
.ak-portrait--logo,
.ak-portrait--text {
  border-radius: 14%;
}
.ak-portrait--logo {
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05));
  border-color: rgba(255, 255, 255, 0.16);
  box-shadow: 0 10px 34px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.08);
  padding: 12%;
}
.ak-portrait--logo img {
  object-fit: contain;
}
.ak-portrait--initials,
.ak-portrait--text {
  background: radial-gradient(circle at 50% 35%, #1d2433 0%, #0d1018 75%);
}
.ak-portrait-initials {
  font-family: 'EB Garamond', serif;
  font-size: calc(var(--tile) * 0.36);
  color: var(--gold);
  letter-spacing: 0.04em;
}
.ak-portrait-text {
  font-family: 'EB Garamond', serif;
  font-size: calc(var(--tile) * 0.13);
  line-height: 1.2;
  color: #f5f5f5;
  padding: 0 12%;
}

.ak-face-name {
  margin-top: 1rem;
  /* A two-line name breaks at its space, not its hyphen ("Aleksandar /
     Diamond-Stanic"). */
  text-wrap: balance;
  font-size: clamp(1.15rem, 1.45vw, 1.5rem);
  line-height: 1.25;
  color: #f5f5f5;
  font-weight: 500;
}
.ak-face-sub {
  margin-top: 0.3rem;
  font-size: clamp(1rem, 1.15vw, 1.2rem);
  line-height: 1.25;
  color: rgba(244, 207, 106, 0.9);
  letter-spacing: 0.02em;
}

/* The small list under a group card (Princeton AOS): the
   round face IS the bullet; left-aligned with the card; names ≥ 16 px. */
.ak-sublist {
  list-style: none;
  margin: 1.1rem 0 0;
  padding: 0;
  width: 100%;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.ak-sub-row {
  pointer-events: auto;
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  color: rgba(245, 245, 245, 0.95);
  text-decoration: none;
  font-size: clamp(1rem, 1.15vw, 1.15rem);
  line-height: 1.2;
}
.ak-sub-row--link {
  cursor: pointer;
}
.ak-sub-row--link:hover .ak-sub-name,
.ak-sub-row--link:focus-visible .ak-sub-name {
  color: #fff;
  text-decoration: underline;
  text-decoration-color: rgba(244, 207, 106, 0.65);
  text-decoration-thickness: 1.5px;
  text-underline-offset: 0.2em;
}
.ak-sub-row--link:focus-visible {
  outline: none;
}
.ak-mini {
  flex: none;
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 50%;
  overflow: hidden;
  border: 1.5px solid rgba(232, 185, 74, 0.55);
  background: radial-gradient(circle at 50% 35%, #1d2433 0%, #0d1018 75%);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  transition: transform 0.22s cubic-bezier(0.22, 0.8, 0.24, 1), border-color 0.22s ease, box-shadow 0.22s ease;
}
.ak-mini img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.ak-mini-initials {
  font-family: 'EB Garamond', serif;
  font-size: 0.85rem;
  color: var(--gold);
}
.ak-sub-row--link:hover .ak-mini {
  transform: translateY(-1px) scale(1.06);
  border-color: var(--gold);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.55), 0 0 0 2px rgba(244, 207, 106, 0.28);
}

</style>
