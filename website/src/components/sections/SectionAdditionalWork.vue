<template>
  <!-- Additional Work — two labelled columns, to the director's brief:
       PAST WORK (done and published)
       and ONGOING WORK, newest at the top, the two MGSIM cards side by
       side in the first row, a sleek line between the columns, one
       shared grid so the rows lock together on scroll. Cards are faded
       until hovered, then pop to full colour. Every thumbnail is square;
       the glaciology card's thumbnail ticks through the ten MGSIM beds
       under the translucent block. Each card has AT MOST ONE door and
       the whole card is the click target (no sub-buttons): an external
       link opens a new tab, an in-site door routes to a sub-page or a
       section. The labeler card's door is the labeler itself
       (/additional-work/label); the classifier card's
       door is the lake-vision repository
       (it began as a doorless JSTARS stub); COP27 and the fracture /
       stream mapping card each carry their own door. Published work quotes
       the paper's own abstract, never a paraphrase.
       Six and six — the fieldwork card and its paper (Stevens
       et al. 2026) are two cards (they once shared one split card),
       and "Revisiting lake drainage papers" closes the
       ongoing column (door: /additional-work/revisit).
       A two-stop toggle under the title: this
       grid ("Beyond the chapters", /additional-work) and "Deeper dive
       into the chapters" (/additional-work/deeper/<chapter>, DeeperDive.vue
       — the per-chapter backup slides). The same page, so the header
       stays put when the stop changes. -->
  <div class="aw">
    <!-- Deeper dive: figures and captions scroll under the ribbon — a
         shade of the page's own background fades them out there. -->
    <div v-if="view === 'deeper'" class="aw-shade" />
    <div class="aw-inner">
      <!-- The two stops: the work beyond the
           chapters (this grid, /additional-work) and the deeper dive into
           them (/additional-work/deeper/<chapter> — the committee's backup
           slides). The stop lives in the URL. -->
      <header class="aw-head">
        <h2 class="aw-title">Additional Work</h2>
        <div class="aw-seg" role="tablist" aria-label="Additional Work">
          <button
            v-for="v in VIEWS"
            :key="v.value"
            class="aw-seg-btn"
            :class="{ 'aw-seg-btn--on': view === v.value }"
            role="tab"
            :aria-selected="view === v.value"
            @click="setView(v.value)"
          >{{ v.label }}</button>
        </div>
      </header>

      <DeeperDive v-if="view === 'deeper'" :chapter="chapter" />

      <div v-else class="aw-cols">
        <h3 class="aw-col-label" style="grid-column: 1">{{ columns[0].label }}</h3>
        <div class="aw-divider" :style="{ gridRow: `1 / span ${rows.length + 1}` }" />
        <h3 class="aw-col-label" style="grid-column: 3">{{ columns[1].label }}</h3>
        <template v-for="(row, ri) in rows" :key="ri">
          <template v-for="(c, ci) in row" :key="`${ri}-${ci}`">
          <div
            v-if="c"
            class="aw-cell"
            :style="{ gridColumn: ci === 0 ? 1 : 3 }"
          >
          <component
            :is="c.door?.href ? 'a' : 'div'"
            class="aw-card"
            :class="{ 'aw-card-live': !!c.door, 'aw-card-soon': !c.door }"
            :href="c.door?.href"
            :target="c.door?.href ? '_blank' : undefined"
            :rel="c.door?.href ? 'noopener noreferrer' : undefined"
            :role="c.door && !c.door.href ? 'button' : undefined"
            :tabindex="c.door && !c.door.href ? 0 : undefined"
            :aria-label="c.door ? `${c.title} — ${c.door.hint}` : undefined"
            @click="enter(c)"
            @keydown.enter.prevent="enter(c)"
          >
            <div class="aw-media">
              <div class="aw-thumb" :class="{ 'aw-thumb-light': c.light, 'aw-thumb-page': c.page }" :style="c.gradient ? { background: c.gradient } : undefined">
                <AddlCycleThumb v-if="c.frames" :frames="c.frames" :interval-ms="2000" :alt="c.alt" />
                <!-- A looping scene (the fieldwork card): silent, plays from
                     mount like the menu thumbs; the idle veil greys it. -->
                <video v-else-if="c.video" class="aw-video" :src="c.video" autoplay muted loop playsinline :aria-label="c.alt" />
                <!-- A paper as its title page: the masthead and a cartoon of
                     its defining figure (the timeline's own). -->
                <div v-else-if="c.figure" class="aw-page">
                  <span class="aw-mast">{{ c.masthead }}</span>
                  <TimelineFigure :id="c.figure" />
                </div>
                <img v-else-if="c.thumb" :src="c.thumb" :alt="c.alt ?? ''" />
              </div>
              <span class="aw-tag">{{ c.tag }}</span>
            </div>
            <div class="aw-text">
              <h4 class="aw-card-title">
                <template v-if="c.titleParts">
                  <span>{{ c.titleParts[0] }}</span><em>{{ c.titleParts[1] }}</em><span>{{ c.titleParts[2] }}</span>
                </template>
                <template v-else>{{ c.title }}</template>
              </h4>
              <!-- Every author, the site's own in bold (so the reader sees
                   at once that the site's author is on another paper). -->
              <p v-if="c.authors" class="aw-authors">
                <template v-for="(a, ai) in c.authors" :key="ai"><b v-if="a === c.boldAuthor">{{ a }}</b><span v-else>{{ a }}</span><span v-if="ai < c.authors.length - 1">, </span></template>
              </p>
              <p v-if="c.body" class="aw-card-body">{{ c.body }}</p>
              <span v-if="c.door" class="aw-door">{{ c.door.hint }} {{ c.door.href ? '↗' : '→' }}</span>
              <span v-else class="aw-door aw-door-none">no door yet</span>
            </div>
          </component>
          </div>
          </template>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import AddlCycleThumb from '../AddlCycleThumb.vue'
import DeeperDive from '../DeeperDive.vue'
import TimelineFigure from '../TimelineFigure.vue'
import type { DeeperChapter } from '../../config/deeperDive'
import { mediaUrl } from '../../config/media'
import { TBS_VIDEO } from '../../config/tbs'
import { FRACTURE } from '../../config/fracture'
import { REVISIT_CARD, revisitUrl } from '../../config/revisit'

type AddlPage = 'mgsim' | 'terminal-bench' | 'fieldwork' | 'fracture' | 'label' | 'revisit'
const emit = defineEmits<{ open: [page: AddlPage] }>()

type View = 'beyond' | 'deeper'
const props = defineProps<{ view: View; chapter: DeeperChapter }>()
const VIEWS: { value: View; label: string }[] = [
  { value: 'beyond', label: 'Beyond the chapters' },
  { value: 'deeper', label: 'Deeper dive into the chapters' },
]
const router = useRouter()
function setView(v: View): void {
  if (v === props.view) return
  if (v === 'deeper') router.push({ name: 'additional-work-deeper', params: { chapter: props.chapter } })
  else router.push({ name: 'additional-work' })
}
// A new stop starts at the top of the page.
watch(
  () => props.view,
  async () => {
    await nextTick()
    document.querySelector('.aw')?.scrollTo({ top: 0, behavior: 'auto' })
  },
)

/** A card's single door. Exactly one of href / page. */
interface Door {
  /** Short verb phrase shown at the foot of the card ("Read the paper"). */
  hint: string
  href?: string
  page?: AddlPage
}
interface Card {
  title: string
  /** [prefix, italic title, suffix] — for citation-style headings. */
  titleParts?: [string, string, string]
  tag: string
  body: string
  thumb?: string
  /** Frames for a ticking thumbnail (overrides `thumb`). */
  frames?: string[]
  alt?: string
  light?: boolean
  gradient?: string
  door?: Door
  /** A looping silent clip as the thumbnail (overrides `thumb`). */
  video?: string
  /** A paper as its title page: TimelineFigure id + masthead. */
  figure?: string
  /** The thumb is a page: crop from its top, not its centre. */
  page?: boolean
  masthead?: string
  /** Every author; `boldAuthor` is set in bold. */
  authors?: string[]
  boldAuthor?: string
}

/** Whole-card click. Links are real <a> elements and handle themselves. */
function enter(c: Card) {
  if (!c.door || c.door.href) return
  if (c.door.page) emit('open', c.door.page)
}

const bedFrames = Array.from({ length: 10 }, (_, k) =>
  mediaUrl(`addl/cards/bed_prism_${String(k).padStart(2, '0')}.jpg`),
)
// The Dask tutorial's Oakland tiles: one frame per Sentinel-2 day in
// August 2019 (DASK_DAYS is the bake's output count).
const DASK_DAYS = 6
const daskFrames = Array.from({ length: DASK_DAYS }, (_, k) =>
  mediaUrl(`addl/cards/dask_oak_${String(k).padStart(2, '0')}.jpg`),
)
// Three ticking thumbs (the director asked for slick thumbnails), baked
// by cinematic/scene_addl/build_card_thumbs.py — the counts
// are the bake's output counts.
const cardFrames = (stem: string, n: number) =>
  Array.from({ length: n }, (_, k) => mediaUrl(`addl/cards/${stem}_${String(k).padStart(2, '0')}.jpg`))
// The same lake in 2018, 2019, then both outlines; its ID tag stays put.
const idsFrames = cardFrames('persist_ids', 3)
// A contested lake of the 200 (CW2019_1989, HF/MD) filling and draining
// under the labeler's red outline, the five sliders settling beneath.
const labelFrames = cardFrames('label_irr', 8)
// The classifier's loss and F1 drawing across epochs over the validation
// confusion matrix finding its diagonal (epochs 1 → 189, the best).
const clfFrames = cardFrames('clf_opt', 8)

// ORDER RULE (the director's): row 1 is the deliberate MGSIM
// pair — the C&G METHOD paper on the left, its glaciology APPLICATION on
// the right — then newest-first down each column. (Terminal-Bench merged
// Aug 2026 and is the newest ongoing item, so it sits SECOND on purpose.)
// The order is explicit in these arrays; there is no sort key.
const columns: { label: string; cards: Card[] }[] = [
  {
    label: 'Past work',
    cards: [
      {
        // The METHOD. No body (the director asked that the paper cards
        // carry just the title and the authors) — every author,
        // the director's name in bold, like the Stevens card.
        title: 'Rines et al., 2026: Interpolation of large-scale airborne geophysical data with uncertainty quantification — Computers & Geosciences',
        titleParts: [
          'Rines et al., 2026: ',
          'Interpolation of large-scale airborne geophysical data with uncertainty quantification',
          ' — Computers & Geosciences',
        ],
        tag: 'C&G 215 · June 2026',
        body: '',
        authors: ['J. H. Rines', 'Z. Yin', 'J. Kloeckner', 'J. Caers'],
        boldAuthor: 'J. H. Rines',
        // The paper's first page (the same treatment as the Nature
        // Communications card), the top square of page 1 rendered from the
        // PDF at 160 dpi. The MGSIM stack thumb (cg_capesmith_sq) stays on R2.
        thumb: mediaUrl('addl/cards/cg2026_page1.webp'),
        page: true,
        light: true,
        alt: 'Rines et al. 2026, Computers & Geosciences — the first page',
        door: { hint: 'Read the paper', href: 'https://doi.org/10.1016/j.cageo.2026.106201' },
      },
      {
        // ABOVE the Dask card (the director's ordering: the fractures vs
        // streams card sits above the parallelized cloud computing card).
        // The AGU 2024 poster C41D-0203, the poster's
        // own title; Iona Xia led the work (first author), the director
        // mentored.
        // Thumb = the training visualisation (fractures red, streams
        // blue), the centre of the block at 360 px, baked silent by
        // cinematic/scene_addl/build_fracture_assets.py with the Maxar
        // credit in its pixels. Facts and links: config/fracture.ts.
        title: FRACTURE.title,
        tag: 'AGU 2024 · led by Iona Xia',
        body: 'Fractures and streams, told apart across whole sub-metre satellite scenes.',
        video: mediaUrl('addl/cards/fracture_loop.mp4'),
        alt: 'A neural network’s map of fractures (red) and streams (blue) sharpening over training, on sub-metre satellite imagery. Imagery © Maxar',
        door: { hint: 'See the maps', page: 'fracture' },
      },
      {
        // The fieldwork explorer (the old Extras side door folded
        // in here). Same component the Introduction lands on.
        // 2023 only (the director's scope for the footage).
        // The thumb is a looping scene — GH010179 over the crevasse
        // fields, 10 s from the served cut, baked silent at 720 px
        // (addl/cards/fieldwork_loop.mp4). Its own card again: the director
        // split the card that combined the field-work footage with the
        // Nature Communications paper so each column has an even number of
        // cards; before that it was the top half of a split card over the
        // campaign's paper.
        title: 'Greenland field work 2023',
        tag: 'Helicopter footage · GPX tracks · two flying days',
        body: 'A season on the west margin instrumenting draining lakes.',
        video: mediaUrl('addl/cards/fieldwork_loop.mp4'),
        alt: 'Helicopter footage over crevasse fields and meltwater streams, 22 August 2023',
        door: { hint: 'Ride along', page: 'fieldwork' },
      },
      {
        // The campaign's paper, directly under its fieldwork card (once the
        // split card's lower half). The director asked for
        // the title like the C&G card's — italics — and the thumb a
        // screenshot of the paper's first page (the top of page 1, rendered
        // from the PDF at 160 dpi), not the cartoon. Every author, the
        // director's name in bold; no body — a coauthored paper is not
        // paraphrased.
        title: 'Stevens et al., 2026: Ice-sheet hydro-fracture not advanced inland by lower-elevation lake drainages in Kalaallit Nunaat — Nature Communications',
        titleParts: [
          'Stevens et al., 2026: ',
          'Ice-sheet hydro-fracture not advanced inland by lower-elevation lake drainages in Kalaallit Nunaat',
          ' — Nature Communications',
        ],
        tag: 'Nature Communications · 2026',
        body: '',
        authors: ['L. A. Stevens', 'M. Nettles', 'S. Larochelle', 'M. Okal', 'E. Falconer', 'N. Turner', 'J. Rines', 'C.-Y. Lai', 'G. Lu'],
        boldAuthor: 'J. Rines',
        thumb: mediaUrl('addl/cards/stevens2026_page1.webp'),
        page: true,
        light: true,
        alt: 'Stevens et al. 2026, Nature Communications — the first page',
        door: { hint: 'Read the paper', href: 'https://doi.org/10.1038/s41467-026-73033-z' },
      },
      {
        // Below the field work + its paper (the director's ordering: the
        // field work and the Stevens paper both sit above the cloud
        // computing card).
        // The CryoCloud tutorial "Parallelized Cloud
        // Computing with Dask for Geoscientists", by Ellianna Abrahams and
        // the director; its last part compiles Sentinel-2 tiles over the Oakland
        // port terminals with sat-tile-stack. The thumb ticks through the
        // days of August 2019 that actually carry imagery (the 5-day
        // revisit), red outline = the tutorial's terminal mask — frames
        // from cinematic/scene_addl/build_dask_card.py (dask_oak_: the first bake's
        // dask_oakland_ frames had the outline 15 px off — see the script).
        title: 'Parallelized cloud computing with Dask for geoscientists',
        tag: 'CryoCloud tutorial · with Ellianna Abrahams',
        body: 'Satellite imagery streamed from the cloud, analysed in chunks, stacked for machine learning.',
        frames: daskFrames,
        alt: 'Sentinel-2 tiles over the Oakland port terminals, August 2019, the terminal mask outlined in red',
        door: { hint: 'Open the tutorial', href: 'https://book.cryointhecloud.com/dask-for-geoscientists/' },
      },
      {
        // The door is C-PREE's article
        // "Beyond the Negotiations at COP27", to which the director
        // contributed the Cryosphere section. Body = the director's own
        // words from it (quoted, never paraphrased).
        // Thumb = the article's HEADLINE image, centre-cropped square by
        // cinematic/scene_addl/build_addl_cards.py — a UNFCCC Flickr photo
        // by Kiara Worth, credited on the article; the alt text carries it.
        title: 'Princeton delegation to COP27',
        tag: 'Sharm el-Sheikh · November 2022',
        body: '“What happens in the cryo-regions does not stay in the cryo-regions.”',
        thumb: mediaUrl('addl/cards/cop27_sideevent_sq.jpg'),
        alt: 'Simon Stiell, UNFCCC Executive Secretary, at a COP27 side event on loss and damage (UNFCCC Flickr / Kiara Worth)',
        door: { hint: 'Read the delegation’s report', href: 'https://cpree.princeton.edu/news/2023/beyond-negotiations-cop27' },
      },
    ],
  },
  {
    label: 'Ongoing work',
    cards: [
      {
        // The APPLICATION — the method pointed at Greenland's bed.
        // Sits level with the C&G method card.
        title: 'Multigrid simulation applied to glaciology',
        tag: '10 beds · 20 Elmer/Ice runs',
        body: 'The method pointed at the ice-sheet bed: ten beds under the PNAS lake, and how much the bed matters.',
        frames: bedFrames,
        alt: 'The translucent simulation block over each of the ten MGSIM bed realizations',
        door: { hint: 'Apply the method to glaciology', page: 'mgsim' },
      },
      {
        title: 'A benchmark task for AI agents',
        tag: `${TBS_VIDEO.channel} · ${TBS_VIDEO.date} · ${TBS_VIDEO.stamp}`,
        body: "Chapter 3's labeling workflow as a Terminal-Bench Science task for AI agents: forty lakes, five ways to drain. Four frontier-model trials have missed the bar; I also review the benchmark's science.",
        thumb: mediaUrl('addl/cards/tbs_lakes_sq.jpg'),
        alt: "One Greenland lake across a 153-day season, from AI Explained's Task Lens page",
        door: { hint: 'Explore the task', page: 'terminal-bench' },
      },
      {
        // Doorless until the work got a public
        // home — the door is now the repository itself ("Browse the code").
        // Thumb: one lake, CW2018_1583 in 2018 and
        // CW2019_1996 in 2019 — CW_0506 in the CW lookup table — over its own
        // Sentinel-2 full-lake day each year.
        title: 'Long-term meltwater tracking · persistent lake IDs',
        tag: 'In progress',
        body: 'Track meltwater across the ice sheet over the whole satellite record. The hard part: what makes a lake the same lake next year.',
        frames: idsFrames,
        alt: 'One Greenland lake in 2018 and in 2019, its outline redrawn each year, its persistent ID unchanged',
        door: { hint: 'Browse the code', href: 'https://github.com/jharlanr/supraglacial-lakes' },
      },
      {
        // The labeler: the same 200 lakes
        // as the ESSD inter-rater study, soft labels scored against the
        // three labelers — SectionLabelLakes.vue at /additional-work/label.
        // A visitor's labels are kept only when they SAVE under a name: a
        // lakelabel-format CSV via the labels Worker to R2 labels/irr/ (or
        // downloaded, until the Worker is deployed).
        title: 'Label lakes yourself · the inter-rater 200',
        tag: 'The ESSD IRR subset · 200 lakes',
        body: 'The 200 lakes three of us labeled independently, opened to anyone: label them and see how you agree.',
        frames: labelFrames,
        alt: 'A contested lake filling and draining over one season under a red outline, five class sliders beneath',
        door: { hint: 'Label lakes yourself', page: 'label' },
      },
      {
        // The lake-classification extension (was the JSTARS stub; the
        // director dropped the JSTARS framing in favour of a plain link to
        // the lake-vision repo). The door is the repository —
        // YaoGroup/lake-vision, public, the director's code; its own words
        // for the tag line. The title is the director's wording ("lake
        // drainage deep learning classifier optimization"); the thumb is
        // the optimization itself (was the white jstars_arch_sq.jpg).
        title: 'Lake drainage deep learning classifier optimization',
        tag: 'lake-vision · in active development',
        body: "Chapter 3's two-stream ConvLSTM, growing into a framework for tracking supraglacial lakes: developed for Greenland, applicable globally.",
        frames: clfFrames,
        alt: 'Training and validation loss and F1 drawing across the epochs above a confusion matrix converging toward its diagonal',
        door: { hint: 'Browse the code', href: 'https://github.com/YaoGroup/lake-vision' },
      },
      {
        // The director named the card "Revisiting lake drainage papers";
        // its page is a more detailed view of the Christoffersen
        // AOI — SectionRevisit.vue at /additional-work/revisit, also the
        // DIVE DEEPER door on the Introduction's coupling step. LAST in the
        // column, so every row above keeps its pair. Thumb: one cascade lake
        // on one day, MODIS left, Landsat 7 right (config/revisit.ts).
        title: 'Revisiting lake drainage papers',
        tag: 'Christoffersen et al. 2018 · June 2010',
        body: 'The lakes Christoffersen et al. (2018) drain to the bed in June 2010, re-examined: each lake’s season in MODIS, Landsat 7 and Sentinel-2.',
        thumb: revisitUrl(REVISIT_CARD),
        alt: 'One of the cascade lakes on the same day at MODIS resolution (left) and in Landsat 7 (right)',
        door: { hint: 'Dive deeper', page: 'revisit' },
      },
    ],
  },
]

// Row-major pairs: [past[i], ongoing[i]]. The columns need not be the
// same length (six and six at present) —
// a missing partner is null and its cell stays empty.
const nRows = Math.max(columns[0].cards.length, columns[1].cards.length)
const rows = Array.from({ length: nRows }, (_, i) => [
  columns[0].cards[i] ?? null,
  columns[1].cards[i] ?? null,
])
</script>

<style scoped>
.aw {
  position: fixed;
  inset: 0;
  z-index: 1;
  overflow-y: auto;
  background: radial-gradient(ellipse at 50% 0%, #0f1420 0%, #050505 60%);
  color: #f5f5f5;
  font-family: 'Inter', system-ui, sans-serif;
  padding: 7vh 3vw 4vh;
  box-sizing: border-box;
  pointer-events: auto;
}

.aw-inner {
  max-width: 1560px;
  margin: 0 auto;
}

/* Fixed to the viewport's top, the same gradient as .aw (whose
   background does not scroll), masked to fade out downward. */
.aw-shade {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  /* To just above where a figure's title lands (DeeperDive's
     scroll-margin-top, 6.2vh + 2.6rem). */
  height: calc(6.2vh + 2.5rem);
  z-index: 2;
  pointer-events: none;
  background: radial-gradient(ellipse at 50% 0%, #0f1420 0%, #050505 60%);
  background-size: 100vw 100vh;
  -webkit-mask-image: linear-gradient(to bottom, #000 70%, transparent);
  mask-image: linear-gradient(to bottom, #000 70%, transparent);
}

.aw-head {
  text-align: center;
  margin-bottom: 1.2rem;
}

.aw-title {
  font-family: 'EB Garamond', serif;
  font-weight: 400;
  font-size: 2.4rem;
  color: var(--gold);
  margin: 0;
  letter-spacing: 0.02em;
}

/* The two-stop toggle under the title (References' segmented control). */
.aw-seg {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin-top: 0.55rem;
  padding: 0.28rem;
  border: 1px solid var(--gold-faint);
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.45);
}

.aw-seg-btn {
  background: transparent;
  border: 1px solid transparent;
  border-radius: 999px;
  color: var(--gold-dim);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.84rem;
  font-weight: 500;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 0.45rem 1.2rem;
  cursor: pointer;
  transition: color 0.2s, background 0.2s, border-color 0.2s;
}

.aw-seg-btn:hover {
  color: var(--gold-bright);
}

.aw-seg-btn--on,
.aw-seg-btn--on:hover {
  color: #0a0a0a;
  background: var(--gold-bright);
  border-color: var(--gold-bright);
}

/* Column 1 · a 1px divider · column 3. One grid, so the rows line up and
   both columns scroll as one. */
.aw-cols {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 1px minmax(0, 1fr);
  gap: 1rem 2.2rem;
  align-items: stretch;
}

.aw-divider {
  grid-column: 2;
  width: 1px;
  background: linear-gradient(to bottom, transparent, var(--gold) 12%, var(--gold) 88%, transparent);
  opacity: 0.55;
}

.aw-col-label {
  font-family: 'Inter', system-ui, sans-serif;
  font-weight: 500;
  font-size: 1.05rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--gold);
  text-align: center;
  margin: 0;
  padding-bottom: 0.4rem;
}

@media (max-width: 1000px) {
  .aw-cols {
    grid-template-columns: minmax(0, 1fr);
  }
  .aw-divider {
    display: none;
  }
  .aw-col-label,
  .aw-cell {
    grid-column: 1 !important;
  }
}

/* Cards: [square thumb + tag] | text. The card is as tall as the taller
   of the two columns; both cards in a grid row stretch to the same
   height, so the columns stay locked. Faded until hovered, then they
   pop. The WHOLE card is the door (an <a> for external links). */
.aw-card {
  --sq: clamp(230px, 16.5vw, 280px);
  display: grid;
  grid-template-columns: var(--sq) minmax(0, 1fr);
  min-height: var(--sq);
  background: #050505;
  border: 1.5px solid var(--gold-faint);
  border-radius: 16px;
  overflow: hidden;
  color: inherit;
  text-decoration: none;
  /* Idle: MOSTLY grey, not fully (the director's preference) — a little colour
     stays, then it pops on hover. */
  filter: saturate(0.42) brightness(0.8);
  opacity: 0.88;
  transition: filter 0.3s ease, opacity 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease, transform 0.3s ease;
}

.aw-card:hover,
.aw-card:focus-visible {
  filter: none;
  opacity: 1;
  transform: translateY(-2px);
  border-color: var(--gold-bright);
  box-shadow: 0 10px 30px -8px rgba(232, 185, 74, 0.5);
  outline: none;
}

.aw-card-live {
  border-color: var(--gold);
  cursor: pointer;
}

.aw-card-soon {
  opacity: 0.6;
  cursor: default;
}

.aw-card-soon:hover {
  opacity: 0.9;
}

/* A grid slot. */
.aw-cell {
  display: grid;
  min-width: 0;
}

.aw-thumb-page img { object-position: top; }

.aw-video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

/* The paper's title page: cream, a masthead, the cartoon below. */
.aw-page {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  background: #f8f6f0;
  padding: 0.55rem 0.6rem 0.4rem;
  box-sizing: border-box;
}

.aw-mast {
  font-family: 'EB Garamond', serif;
  font-size: 0.72rem;
  letter-spacing: 0.02em;
  color: #1c1a16;
  border-bottom: 1px solid #1c1a16;
  padding-bottom: 0.2rem;
  margin-bottom: 0.35rem;
  white-space: nowrap;
  overflow: hidden;
}

.aw-page :deep(.tl-fig) {
  flex: 1;
  width: 100%;
  min-height: 0;
}

.aw-authors {
  margin: 0.35rem 0 0.4rem;
  font-size: 0.98rem;
  line-height: 1.45;
  color: rgba(245, 245, 245, 0.72);
}

.aw-authors b {
  font-weight: 600;
  color: var(--gold-bright);
}

.aw-media {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.aw-thumb {
  position: relative;
  width: var(--sq);
  height: var(--sq);
  background: #0a0a14;
  overflow: hidden;
  flex: none;
}

.aw-thumb img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.aw-thumb-light {
  background: #fff;
}

.aw-tag {
  display: block;
  padding: 0.55rem 0.75rem 0.5rem;
  font-size: 0.8rem;
  line-height: 1.3;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--gold-bright);
}

.aw-text {
  display: flex;
  flex-direction: column;
  padding: 0.9rem 1.2rem 0.9rem;
  min-width: 0;
  min-height: 0;
}

.aw-card-title {
  font-family: 'EB Garamond', serif;
  font-weight: 400;
  font-size: 1.6rem;
  line-height: 1.12;
  color: var(--gold);
  margin: 0 0 0.5rem;
}

.aw-card-title em {
  font-style: italic;
}

.aw-card-body {
  margin: 0 0 0.7rem;
  font-size: 1.2rem;
  line-height: 1.4;
  color: #e2ded6;
}

/* The single door, as a text affordance at the foot of the card (the
   whole card is the click target). */
.aw-door {
  margin-top: auto;
  align-self: flex-start;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1rem;
  font-weight: 500;
  letter-spacing: 0.05em;
  color: var(--gold);
  border-bottom: 1px solid transparent;
  transition: color 0.2s, border-color 0.2s;
}

.aw-card:hover .aw-door {
  color: var(--gold-bright);
  border-bottom-color: var(--gold-bright);
}

.aw-door-none {
  color: #8a8478;
  font-weight: 400;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 0.82rem;
}

.aw-card:hover .aw-door-none {
  color: #a39d90;
  border-bottom-color: transparent;
}
</style>
