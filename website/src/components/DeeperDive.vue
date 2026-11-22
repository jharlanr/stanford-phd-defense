<template>
  <!-- "Deeper dive into the chapters" (a page the director asked for): the
       backup slides for the committee's deeper questions, one scrollable
       page per chapter. Lives inside SectionAdditionalWork's scroller
       (the toggle's second stop). Left: a sticky rail — the chapter switch
       and this chapter's figure index (click = scroll to it; the figure
       in view is lit). Right: the paper, then its figures, each a title,
       the image on its own white paper (click = full screen), one line of
       caption. A reference page, so captions are allowed here (the
       paper's own, in gist) — no other prose. Data: config/deeperDive.ts. -->
  <div class="dd">
    <aside ref="railEl" class="dd-rail">
      <nav class="dd-switch" aria-label="Chapter">
        <button
          v-for="c in DEEPER_CHAPTERS"
          :key="c"
          class="dd-switch-btn"
          :class="{ 'dd-switch-btn--on': c === chapter }"
          :aria-current="c === chapter ? 'page' : undefined"
          @click="setChapter(c)"
        >
          <span class="dd-switch-name">{{ DEEPER_PAGES[c].label }}</span>
          <span class="dd-switch-venue">{{ DEEPER_PAGES[c].venue }}</span>
        </button>
      </nav>

      <ol v-if="page.groups.length" class="dd-index">
        <template v-for="g in page.groups" :key="g.label">
          <li class="dd-index-group">{{ g.label }}</li>
          <li v-for="f in g.figures" :key="f.id">
            <button
              class="dd-index-btn"
              :class="{ 'dd-index-btn--on': f.id === activeId }"
              :data-index="f.id"
              @click="jump(f.id)"
            >
              <span class="dd-index-tag">{{ f.indexTag ?? shortTag(f.tag) }}</span>
              <span class="dd-index-label">{{ f.short }}</span>
            </button>
          </li>
        </template>
      </ol>
    </aside>

    <article :key="chapter" class="dd-page">
      <header class="dd-paper">
        <p class="dd-paper-meta">
          {{ page.label }} · {{ page.venue }} · <span class="dd-paper-status">{{ page.status }}</span>
        </p>
        <h3 class="dd-paper-title">{{ page.paper.title }}</h3>
        <p class="dd-paper-authors">
          <template v-for="(a, i) in page.paper.authors" :key="i"><b v-if="AUTHOR_NAMES.has(a)">{{ a }}</b><span v-else>{{ a }}</span><span v-if="i < page.paper.authors.length - 1">, </span></template>
        </p>
        <component
          :is="paperUrl ? 'a' : 'p'"
          class="dd-paper-venue"
          :class="{ 'dd-paper-venue--link': !!paperUrl }"
          :href="paperUrl ?? undefined"
          :target="paperUrl ? '_blank' : undefined"
          :rel="paperUrl ? 'noopener noreferrer' : undefined"
        >
          <em>{{ page.paper.venue }}</em>{{ page.paper.volume ? `, ${page.paper.volume}` : '' }}{{ page.paper.pages ? `, ${page.paper.pages}` : '' }}{{ page.paper.status ? '' : ` (${page.paper.year})` }}<span v-if="page.paper.doi" class="dd-doi">doi:{{ page.paper.doi }} ↗</span><span v-else-if="page.paper.status" class="dd-doi dd-doi--none">{{ page.paper.status }}</span>
        </component>
      </header>

      <section
        v-for="g in page.groups"
        :id="g.id ? `dd-${g.id}` : undefined"
        :key="g.label"
        :ref="(el) => g.id && setGroupEl(g.id, el)"
        class="dd-group"
      >
        <h4 class="dd-group-label">{{ g.label }}</h4>
        <figure
          v-for="f in g.figures"
          :id="`dd-${f.id}`"
          :key="f.id"
          :ref="(el) => setFigEl(f.id, el)"
          :data-fig="f.id"
          class="dd-fig"
        >
          <div class="dd-fig-head">
            <!-- trusted static HTML (sub/superscripts: #superposition) -->
            <h5 class="dd-fig-title" v-html="f.title" />
            <span class="dd-fig-tag">{{ f.tag }}</span>
          </div>

          <!-- A figure: its own white paper, sized to fit one screen. -->
          <button
            v-if="f.src && f.size"
            class="dd-frame"
            :style="frameStyle(f)"
            :aria-label="`${f.tag} — full screen`"
            @click="openLightbox(f)"
          >
            <img :src="mediaUrl(f.src)" :alt="f.alt ?? f.title" :width="f.size[0]" :height="f.size[1]" loading="lazy" decoding="async" />
          </button>

          <!-- The paper itself (the director wanted each paper's PDF one
               click away, opening in a new browser tab rather than inside
               the page): the PDF on R2 (papers/), its first
               page as the cover, both open it in a new tab. -->
          <div v-else-if="f.pdf" class="dd-pdf">
            <a
              class="dd-pdf-cover"
              :href="mediaUrl(f.pdf.key)"
              target="_blank"
              rel="noopener noreferrer"
              :aria-label="`${f.title} — open the PDF in a new tab`"
            >
              <img :src="mediaUrl(f.pdf.cover)" :width="f.pdf.coverSize[0]" :height="f.pdf.coverSize[1]" alt="" loading="lazy" decoding="async" />
            </a>
            <div class="dd-pdf-side">
              <a class="dd-pdf-btn" :href="mediaUrl(f.pdf.key)" target="_blank" rel="noopener noreferrer">
                Open the PDF <span class="dd-pdf-arrow" aria-hidden="true">↗</span>
              </a>
              <p class="dd-pdf-meta">{{ f.pdf.pages }} pages · {{ f.pdf.mb }} MB · opens in a new tab</p>
              <p v-if="f.pdf.note" class="dd-pdf-note">{{ f.pdf.note }}</p>
            </div>
          </div>

          <!-- APS DFD 2026: the door to the conference presentation's own
               page — the two-minute flash slide and the interactive poster
               (/additional-work/dfd, SectionDfd.vue). -->
          <div v-else-if="f.door === 'dfd'" class="dd-door">
            <button class="dd-door-logo" aria-label="Open the APS DFD 2026 presentation" @click="openDfd">
              <img :src="mediaUrl(DFD_LOGO_KEY)" alt="" />
            </button>
            <div class="dd-door-side">
              <p class="dd-door-title">{{ DFD_TITLE }}</p>
              <p class="dd-door-meta">{{ DFD_MEETING.format }} · {{ DFD_MEETING.session }} · {{ DFD_MEETING.place }}, {{ DFD_MEETING.date }}</p>
              <button class="dd-pdf-btn" @click="openDfd">
                Open the presentation <span class="dd-pdf-arrow" aria-hidden="true">→</span>
              </button>
              <p class="dd-pdf-meta">the two-minute slide · the interactive poster · {{ DFD_BEATS }} beats</p>
            </div>
          </div>

          <!-- Chapter 2's results walk WITH the elastic model (taken off
               the talk; the director wanted the full sequence, elastic
               model included, kept here as a deeper-dive section). -->
          <Ch2SequenceViewer v-else-if="f.viewer === 'ch2-sequence'" />
          <!-- …and the population pair, elastic | viscous (the talk's
               population page as it was until then). -->
          <div v-else-if="f.plot === 'ch2-ss-both'" class="dd-plate">
            <Ch2PopulationSpaces />
          </div>

          <!-- Chapter 2's field viewer: lakes × models × fields. -->
          <Ch2FieldViewer v-else-if="f.viewer === 'ch2-fields'" />
          <!-- Chapter 2's idealized slab: every field of the sweep. -->
          <Ch2SlabFieldViewer v-else-if="f.viewer === 'ch2-slab'" />

          <!-- Chapter 2's elastic stress space, live (x = the
               viscous pre-drainage stress + the elastic perturbation). -->
          <div v-else-if="f.plot === 'ch2-ss-elastic'" class="dd-frame dd-frame--plot">
            <Ch2ElasticStressSpaces />
          </div>

          <!-- Chapter 2's stress-space definitions (PNAS SI §4C), typeset. -->
          <div v-else-if="f.eqs === 'ch2-stress-defs'" class="dd-eqs">
            <Ch2StressEqs />
          </div>

          <!-- Why the post-drainage elastic state is σ^V_pre + Δσ^E:
               the jump condition, typeset. -->
          <div v-else-if="f.eqs === 'ch2-superposition'" class="dd-eqs dd-eqs--sup">
            <Ch2SuperpositionEqs />
          </div>

          <!-- Chapter 1's derivation: the SSA to the three-zone
               solution, typeset, with the velocity solutions the talk
               no longer shows. -->
          <div v-else-if="f.eqs === 'ch1-derivation'" class="dd-eqs dd-eqs--sup">
            <Ch1DerivationEqs />
          </div>

          <!-- Glen's flow law: the paper's eq. 6 + Table 1. -->
          <div v-else-if="f.eqs === 'ch1-glen'" class="dd-eqs dd-eqs--sup">
            <Ch1DerivationEqs set="glen" />
          </div>

          <!-- Chapter 3's metrics + loss, typeset. -->
          <div v-else-if="f.eqs === 'ch3-metrics'" class="dd-eqs dd-eqs--sup">
            <Ch3MetricEqs />
          </div>

          <!-- Chapter 2's stress relations, one block each. -->
          <Ch2StressRelations v-else-if="f.relations" :block="f.relations" />

          <!-- The paper's tables, typeset. -->
          <div v-else-if="f.table === 'params'" class="dd-table-wrap">
            <table class="dd-table">
              <thead>
                <tr><th>Parameter</th><th>Symbol</th><th>Value(s)</th><th>Units</th></tr>
              </thead>
              <tbody>
                <tr v-for="r in CH1_PARAMS" :key="r.name">
                  <td>{{ r.name }}</td>
                  <td class="dd-math" v-html="r.symbol" />
                  <td class="dd-math" v-html="r.values" />
                  <td class="dd-math" v-html="r.units" />
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else-if="f.table === 'kappa'" class="dd-table-wrap">
            <table class="dd-table dd-table--kappa">
              <thead>
                <tr>
                  <th>Case</th>
                  <th class="dd-math">max(<i>τ</i><sub>xx</sub>) = <span class="dd-k">κ</span> [<i>ρgαℓ</i>/4]</th>
                  <th class="dd-math">DL = <span class="dd-k">κ</span> [(2<i>Bh</i>/<i>C</i>)<sup><i>n</i>/(<i>n</i>+1)</sup>]</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in CH1_KAPPA" :key="`${r.n}${r.kind}`" :class="{ 'dd-row-n3': r.n === 3 }">
                  <td class="dd-math"><i>n</i> = {{ r.n }}, {{ r.kind }}</td>
                  <td class="dd-kappa">
                    <span class="dd-k">κ</span><span class="dd-ss"><span>{{ r.kind === 'S' ? 's' : 'da' }}</span><span>{{ r.n }},<i>τ</i></span></span>
                    = {{ r.tau.median }}<span class="dd-ss"><span>+{{ r.tau.plus }}</span><span>−{{ r.tau.minus }}</span></span>
                  </td>
                  <td class="dd-kappa">
                    <span class="dd-k">κ</span><span class="dd-ss"><span>{{ r.kind === 'S' ? 's' : 'da' }}</span><span>{{ r.n }},<i>L</i></span></span>
                    = {{ r.dl.median }}<span class="dd-ss"><span>+{{ r.dl.plus }}</span><span>−{{ r.dl.minus }}</span></span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Thesis Table 2.1: the seven center lakes. -->
          <div v-else-if="f.table === 'ch2-lakes'" class="dd-table-wrap">
            <table class="dd-table dd-table--wide">
              <thead>
                <tr>
                  <th>Lake</th><th>Lat.</th><th>Lon.</th><th>Surface</th><th>Thickness</th><th>Speed</th><th>Drained</th>
                  <th class="dd-math"><i>c</i><sub>b</sub></th>
                </tr>
                <tr class="dd-units">
                  <th /><th>°N</th><th>°W</th><th>m</th><th>m</th><th class="dd-math">m yr<sup>−1</sup></th><th>2019</th>
                  <th class="dd-math">10<sup>6</sup> Pa m<sup>−1/3</sup> s<sup>1/3</sup></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in CH2_LAKES_TABLE" :key="r.lake">
                  <td class="dd-num dd-lake">{{ r.lake }}</td>
                  <td class="dd-num">{{ r.lat }}</td>
                  <td class="dd-num">{{ r.lon }}</td>
                  <td class="dd-num">{{ r.surface }}</td>
                  <td class="dd-num">{{ r.thickness }}</td>
                  <td class="dd-num">{{ r.speed }}</td>
                  <td>{{ r.drained }}</td>
                  <td class="dd-num">{{ r.cb }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Thesis Tables 2.2 / 2.3: the stress spaces' numbers. -->
          <div v-else-if="f.table === 'ch2-elastic' || f.table === 'ch2-viscous'" class="dd-table-wrap">
            <table class="dd-table dd-table--wide dd-table--stress">
              <thead>
                <tr>
                  <th>Center</th><th>Neighbor</th><th>Drainage</th><th>Drained</th>
                  <th class="dd-math dd-num"><i>σ</i><span class="dd-ss"><span>pre</span><span>t1</span></span></th>
                  <th class="dd-math dd-num">Δ<i>σ</i><sub>t1</sub></th>
                  <th class="dd-math dd-num"><i>σ</i><span class="dd-ss"><span>post</span><span>t1</span></span></th>
                  <th class="dd-math dd-num"><i>σ</i><span class="dd-ss"><span>pre</span><span>t2</span></span></th>
                  <th class="dd-math dd-num">Δ<i>σ</i><sub>t2</sub></th>
                  <th class="dd-math dd-num"><i>σ</i><span class="dd-ss"><span>post</span><span>t2</span></span></th>
                </tr>
                <tr class="dd-units">
                  <th>lake</th><th>lake</th><th>class</th><th>2019</th>
                  <th class="dd-num">kPa</th><th class="dd-num">kPa</th><th class="dd-num">kPa</th>
                  <th class="dd-num">kPa</th><th class="dd-num">kPa</th><th class="dd-num">kPa</th>
                </tr>
              </thead>
              <tbody v-for="g in CH2_RESULTS[f.table === 'ch2-elastic' ? 'elastic' : 'viscous']" :key="g.center" class="dd-tgroup">
                <tr v-for="(r, ri) in g.rows" :key="r[0]">
                  <td v-if="ri === 0" :rowspan="g.rows.length" class="dd-center">
                    <span class="dd-lake">{{ g.center }}</span>
                    <span class="dd-center-date">{{ g.date }}</span>
                  </td>
                  <td class="dd-num dd-lake">{{ r[0] }}</td>
                  <td><span class="dd-cls" :class="`dd-cls--${r[1]}`" />{{ r[1] }}</td>
                  <td>{{ r[2] }}</td>
                  <td class="dd-num">{{ r[3] }}</td>
                  <td class="dd-num dd-delta">{{ r[4] }}</td>
                  <td class="dd-num">{{ r[5] }}</td>
                  <td class="dd-num">{{ r[6] }}</td>
                  <td class="dd-num dd-delta">{{ r[7] }}</td>
                  <td class="dd-num">{{ r[8] }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <figcaption v-if="f.caption || f.credit" class="dd-cap">
            <span v-if="f.caption" v-html="f.caption" />
            <span v-if="f.credit" class="dd-credit">{{ f.credit }}</span>
          </figcaption>
        </figure>
      </section>

      <!-- Stub chapters: empty frames, nothing else (the director fills them). -->
      <div v-if="page.placeholders" class="dd-stub-grid">
        <div v-for="k in page.placeholders" :key="k" class="dd-stub-frame" />
      </div>
    </article>

    <!-- Full screen: the figure alone on black. Click or Esc closes;
         ← / → step through this chapter's figures. Teleported so it
         covers the ribbon and the pills too. -->
    <Teleport to="body">
      <Transition name="dd-lb">
        <div
          v-if="lightbox"
          class="dd-lb"
          role="dialog"
          aria-modal="true"
          :aria-label="lightbox.title"
          @click="closeLightbox"
        >
          <div class="dd-lb-head">
            <span class="dd-lb-tag">{{ lightbox.tag }}</span>
            <span class="dd-lb-title">{{ lightbox.title }}</span>
          </div>
          <img class="dd-lb-img" :src="mediaUrl(lightbox.src!)" :alt="lightbox.alt ?? lightbox.title" />
          <button class="dd-lb-close" aria-label="Close" @click.stop="closeLightbox">✕</button>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, type ComponentPublicInstance } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Ch2ElasticStressSpaces from './Ch2ElasticStressSpaces.vue'
import Ch2FieldViewer from './Ch2FieldViewer.vue'
import Ch2SequenceViewer from './Ch2SequenceViewer.vue'
import Ch2PopulationSpaces from './Ch2PopulationSpaces.vue'
import Ch2SlabFieldViewer from './Ch2SlabFieldViewer.vue'
import Ch2StressEqs from './Ch2StressEqs.vue'
import Ch2SuperpositionEqs from './Ch2SuperpositionEqs.vue'
import Ch1DerivationEqs from './Ch1DerivationEqs.vue'
import Ch3MetricEqs from './Ch3MetricEqs.vue'
import Ch2StressRelations from './Ch2StressRelations.vue'
import {
  CH1_KAPPA,
  CH1_PARAMS,
  CH2_LAKES_TABLE,
  CH2_RESULTS,
  DEEPER_CHAPTERS,
  DEEPER_PAGES,
  type DeeperChapter,
  type DeeperFigure,
} from '../config/deeperDive'
import { AUTHOR_NAMES, refUrl } from '../config/references'
import { mediaUrl } from '../config/media'
import { DFD_BEATS, DFD_LOGO_KEY, DFD_MEETING, DFD_TITLE } from '../config/dfd'

const props = defineProps<{ chapter: DeeperChapter }>()

const route = useRoute()
const router = useRouter()

/** The APS DFD door (Chapter 2's first entry) → the presentation's page. */
function openDfd(): void {
  void router.push({ name: 'additional-work-dfd' })
}

const page = computed(() => DEEPER_PAGES[props.chapter])
const paperUrl = computed(() => refUrl(page.value.paper))
const figures = computed(() => page.value.groups.flatMap((g) => g.figures))
const withImages = computed(() => figures.value.filter((f) => f.src))

function setChapter(c: DeeperChapter): void {
  if (c === props.chapter) return
  router.push({ name: 'additional-work-deeper', params: { chapter: c } })
}

/** "Fig. 4 c, d, g, h" → "4", "Table 2" → "T2", "Fig. B1 a–c" → "B1". */
function shortTag(tag: string): string {
  const t = /^Table\s+(\S+)/.exec(tag)
  if (t) return `T${t[1]}`
  const m = /^Figs?\.\s+(\S+)/.exec(tag)
  return m ? m[1] : tag
}

/** A figure fits one screen: as wide as the column allows, never taller
 *  than the viewport less the title/caption chrome (--dd-chrome). */
function frameStyle(f: DeeperFigure): Record<string, string> {
  const [w, h] = f.size!
  const cap = f.maxWidth ? `, ${f.maxWidth}px` : ''
  return {
    aspectRatio: `${w} / ${h}`,
    width: `min(100%, calc((100vh - var(--dd-chrome)) * ${(w / h).toFixed(4)})${cap})`,
  }
}

// ── The figure in view (scroll-spy) and the index jump ──────────────────
const figEls = new Map<string, HTMLElement>()
function setFigEl(id: string, el: Element | ComponentPublicInstance | null): void {
  if (el instanceof HTMLElement) figEls.set(id, el)
  else figEls.delete(id)
}
const groupEls = new Map<string, HTMLElement>()
function setGroupEl(id: string, el: Element | ComponentPublicInstance | null): void {
  if (el instanceof HTMLElement) groupEls.set(id, el)
  else groupEls.delete(id)
}
const activeId = ref<string | null>(null)
let io: IntersectionObserver | null = null
const visible = new Map<string, number>()

function observe(): void {
  io?.disconnect()
  visible.clear()
  activeId.value = figures.value[0]?.id ?? null
  io = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        const id = (e.target as HTMLElement).dataset.fig
        if (!id) continue
        if (e.isIntersecting) visible.set(id, e.intersectionRatio)
        else visible.delete(id)
      }
      // The first figure (in page order) that fills most of the band.
      let best: string | null = null
      let bestR = 0
      for (const f of figures.value) {
        const r = visible.get(f.id) ?? 0
        if (r > bestR + 0.05) {
          best = f.id
          bestR = r
        }
      }
      if (best) activeId.value = best
    },
    // The band below the ribbon: a figure counts while it crosses it.
    { rootMargin: '-12% 0px -35% 0px', threshold: [0, 0.1, 0.25, 0.5, 0.75, 1] },
  )
  for (const el of figEls.values()) io.observe(el)
}

// The lit index entry stays on screen inside the rail (it scrolls on its
// own; the rail is moved, never the page).
const railEl = ref<HTMLElement | null>(null)
watch(activeId, async (id) => {
  await nextTick()
  const rail = railEl.value
  const btn = id ? rail?.querySelector<HTMLElement>(`[data-index="${id}"]`) : null
  if (!rail || !btn) return
  const r = rail.getBoundingClientRect()
  const b = btn.getBoundingClientRect()
  const pad = 24
  const bottom = Math.min(r.bottom, window.innerHeight)
  if (b.top < r.top + pad) rail.scrollTop -= r.top + pad - b.top
  else if (b.bottom > bottom - pad) rail.scrollTop += b.bottom - (bottom - pad)
})

function jump(id: string, smooth = true): void {
  const el = figEls.get(id)
  if (!el) return
  el.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'start' })
  activeId.value = id
}

/** The scroller (SectionAdditionalWork's .aw) back to the top. */
function scrollTop(): void {
  const scroller = document.querySelector('.aw')
  scroller?.scrollTo({ top: 0, behavior: 'auto' })
}

/** A #<figure id> on the URL lands on that figure, a #<group id> on that
 *  group's label (deep links: Chapter 2's #fields and #stress-spaces). */
async function landOnHash(): Promise<void> {
  await nextTick()
  const id = route.hash.replace(/^#(dd-)?/, '')
  if (!id) return
  if (figEls.has(id)) jump(id, false)
  else groupEls.get(id)?.scrollIntoView({ behavior: 'auto', block: 'start' })
}

onMounted(() => {
  observe()
  void landOnHash()
})
// A new #anchor on the same page (a link, or the back button) lands too.
watch(
  () => route.hash,
  () => void landOnHash(),
)
watch(
  () => props.chapter,
  async () => {
    closeLightbox()
    await nextTick()
    scrollTop()
    observe()
    void landOnHash()
  },
)

// ── Full screen ─────────────────────────────────────────────────────────
const lightbox = ref<DeeperFigure | null>(null)
function openLightbox(f: DeeperFigure): void {
  lightbox.value = f
}
function closeLightbox(): void {
  lightbox.value = null
}
function step(d: number): void {
  const list = withImages.value
  const i = list.findIndex((f) => f.id === lightbox.value?.id)
  if (i < 0) return
  const next = list[i + d]
  if (!next) return
  lightbox.value = next
  jump(next.id, false)
}
function onKey(e: KeyboardEvent): void {
  if (!lightbox.value) return
  if (e.key === 'Escape') closeLightbox()
  else if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === 'PageDown') step(1)
  else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp' || e.key === 'PageUp') step(-1)
  else return
  e.preventDefault()
  e.stopPropagation()
}
onMounted(() => window.addEventListener('keydown', onKey, true))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey, true)
  io?.disconnect()
})
</script>

<style scoped>
.dd {
  /* Title row + caption + the ribbon's clearance: what a figure leaves
     of the viewport's height. */
  --dd-chrome: 15.5rem;
  --dd-top: calc(1.2vh + 3.7rem);
  display: grid;
  grid-template-columns: 12.5rem minmax(0, 1fr);
  gap: 2.4rem;
  align-items: start;
  padding-top: 0.6rem;
}

/* ── the rail ─────────────────────────────────────────────────────── */
.dd-rail {
  position: sticky;
  top: var(--dd-top);
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
  /* The scroller (SectionAdditionalWork's .aw, padding 7vh 3vw 4vh) is
     the sticky's containing scrollport, and a sticky's `top` counts from
     the scrollport's PADDING edge: the rail sticks at 7vh + --dd-top, and
     its bottom may come no lower than 4vh above the viewport's. The old
     calc(100vh - --dd-top - 1rem) left out both paddings, so the rail ran
     ~11vh below the screen and its last entries could not be scrolled to
     (the director caught this). */
  max-height: calc(100vh - 7vh - 4vh - var(--dd-top) - 0.5rem);
  overflow-y: auto;
  scrollbar-width: none;
  padding-bottom: 0.6rem;
  box-sizing: border-box;
}
.dd-rail::-webkit-scrollbar { display: none; }

.dd-switch {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.35rem;
  border: 1px solid var(--gold-faint);
  border-radius: 14px;
  background: rgba(0, 0, 0, 0.45);
}

.dd-switch-btn {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.6rem;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 10px;
  color: var(--gold-dim);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.98rem;
  font-weight: 500;
  letter-spacing: 0.03em;
  padding: 0.5rem 0.8rem;
  cursor: pointer;
  text-align: left;
  transition: color 0.2s, background 0.2s, border-color 0.2s;
}
.dd-switch-btn:hover { color: var(--gold-bright); }
.dd-switch-btn--on,
.dd-switch-btn--on:hover {
  color: #0a0a0a;
  background: var(--gold-bright);
  border-color: var(--gold-bright);
}
.dd-switch-venue {
  font-size: 0.7rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  opacity: 0.8;
}

.dd-index {
  list-style: none;
  margin: 0;
  padding: 0 0 0 0.2rem;
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
}
.dd-index-group {
  margin: 0.7rem 0 0.2rem;
  font-size: 0.66rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--gold-dim);
}
.dd-index-group:first-child { margin-top: 0; }

.dd-index-btn {
  display: grid;
  grid-template-columns: 2.1rem minmax(0, 1fr);
  align-items: baseline;
  width: 100%;
  background: transparent;
  border: none;
  border-left: 2px solid transparent;
  color: #a39d90;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.82rem;
  line-height: 1.25;
  padding: 0.22rem 0.4rem 0.22rem 0.55rem;
  text-align: left;
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s, background 0.2s;
}
.dd-index-btn:hover { color: var(--gold-bright); }
.dd-index-btn--on {
  color: var(--gold-bright);
  border-left-color: var(--gold);
  background: linear-gradient(90deg, rgba(232, 185, 74, 0.1), rgba(232, 185, 74, 0));
}
.dd-index-tag {
  font-size: 0.7rem;
  letter-spacing: 0.04em;
  color: var(--gold-dim);
}
.dd-index-btn--on .dd-index-tag { color: var(--gold); }

/* ── the page ─────────────────────────────────────────────────────── */
.dd-page {
  min-width: 0;
  padding-bottom: 30vh;
}

.dd-paper {
  padding: 0.2rem 0 1.4rem;
  border-bottom: 1px solid var(--gold-faint);
  margin-bottom: 0.6rem;
}
.dd-paper-meta {
  margin: 0 0 0.35rem;
  font-size: 0.74rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--gold-dim);
}
.dd-paper-status { color: var(--gold); }
.dd-paper-title {
  font-family: 'EB Garamond', serif;
  font-weight: 400;
  font-size: clamp(1.5rem, 2.1vw, 2.1rem);
  line-height: 1.15;
  color: var(--gold);
  margin: 0;
  text-wrap: balance;
}
.dd-paper-authors {
  margin: 0.45rem 0 0.3rem;
  font-size: 0.98rem;
  color: rgba(245, 245, 245, 0.75);
}
.dd-paper-authors b { font-weight: 600; color: var(--gold-bright); }
.dd-paper-venue {
  display: inline-block;
  margin: 0;
  font-size: 0.92rem;
  color: #d8d3c8;
  text-decoration: none;
}
.dd-doi {
  margin-left: 0.9rem;
  color: var(--gold);
  letter-spacing: 0.02em;
  border-bottom: 1px solid transparent;
  transition: color 0.2s, border-color 0.2s;
}
.dd-paper-venue--link:hover .dd-doi {
  color: var(--gold-bright);
  border-bottom-color: var(--gold-bright);
}
.dd-doi--none {
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--gold-dim);
}

.dd-group { scroll-margin-top: calc(6.2vh + 2.6rem); }
.dd-group-label {
  margin: 2.2rem 0 0;
  font-family: 'Inter', system-ui, sans-serif;
  font-weight: 500;
  font-size: 0.8rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--gold);
}

.dd-fig {
  margin: 0;
  padding: 1.4rem 0 1.6rem;
  scroll-margin-top: calc(6.2vh + 2.6rem);
}
.dd-fig + .dd-fig { border-top: 1px solid rgba(232, 185, 74, 0.08); }

.dd-fig-head {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  margin-bottom: 0.7rem;
}
.dd-fig-title {
  margin: 0;
  font-family: 'EB Garamond', serif;
  font-weight: 400;
  font-size: 1.65rem;
  line-height: 1.15;
  color: var(--gold-bright);
}
.dd-fig-tag {
  flex: none;
  margin-left: auto;
  font-size: 0.74rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--gold-dim);
  white-space: nowrap;
}

/* The figure's paper: white, rounded, a gold hairline; lifts on hover
   (it opens full screen). */
.dd-frame {
  display: block;
  margin: 0 auto;
  padding: 0;
  border: 1px solid var(--gold-faint);
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
  cursor: zoom-in;
  box-shadow: 0 12px 40px -18px rgba(0, 0, 0, 0.9);
  transition: box-shadow 0.25s, border-color 0.25s, transform 0.25s;
}
.dd-frame:hover,
.dd-frame:focus-visible {
  border-color: var(--gold);
  box-shadow: 0 14px 44px -14px rgba(232, 185, 74, 0.35);
  outline: none;
}
.dd-frame--plot {
  /* the thesis figure's 2000 × 1892, one screen tall at most */
  width: min(100%, calc((100vh - var(--dd-chrome)) * 1.057));
  cursor: default;
}
/* The talk's dark plate for its own diagrams (the stress spaces draw
   pale ink on black): the equations' plate, full width. */
.dd-plate {
  width: 100%;
  margin: 0 auto;
  padding: 1rem 1.2rem 0.8rem;
  box-sizing: border-box;
  background: rgba(0, 0, 0, 0.35);
  border-top: 1.5px solid var(--gold);
  border-bottom: 1.5px solid var(--gold);
}
.dd-frame img {
  display: block;
  width: 100%;
  height: 100%;
}

/* ── the paper's PDF card ─────────────────────────────────────────── */
.dd-pdf {
  display: flex;
  align-items: center;
  gap: 2.4rem;
  width: fit-content;
  max-width: 100%;
  margin: 0 auto;
}
.dd-pdf-cover {
  display: block;
  flex: none;
  width: min(240px, 28vw);
  border: 1px solid var(--gold-faint);
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 12px 40px -18px rgba(0, 0, 0, 0.9);
  transition: box-shadow 0.25s, border-color 0.25s, transform 0.25s;
}
.dd-pdf-cover:hover,
.dd-pdf-cover:focus-visible {
  border-color: var(--gold);
  box-shadow: 0 14px 44px -14px rgba(232, 185, 74, 0.35);
  transform: translateY(-2px);
  outline: none;
}
.dd-pdf-cover img {
  display: block;
  width: 100%;
  height: auto;
}
.dd-pdf-side {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.7rem;
}
/* The APS DFD door: the meeting's mark on its white plate (the SVG carries
   its own white ground), the talk's title, the button in the PDF button's
   clothes. */
.dd-door {
  display: flex;
  align-items: center;
  gap: 2.2rem;
  flex-wrap: wrap;
}
.dd-door-logo {
  flex: none;
  width: 280px;
  padding: 1rem 1.2rem;
  border: 0;
  border-radius: 12px;
  /* the mark is re-grounded for the dark page (config/dfd.ts DFD_LOGO_KEY) */
  background: linear-gradient(135deg, rgba(30, 24, 12, 0.95), rgba(10, 8, 5, 0.95));
  cursor: pointer;
  box-shadow: 0 0 0 1px rgba(232, 185, 74, 0.35), 0 12px 36px rgba(0, 0, 0, 0.55);
  transition: box-shadow 0.2s, transform 0.2s;
}
.dd-door-logo:hover,
.dd-door-logo:focus-visible {
  box-shadow: 0 0 0 2px var(--gold), 0 14px 40px rgba(0, 0, 0, 0.6);
  transform: translateY(-2px);
  outline: none;
}
.dd-door-logo img { display: block; width: 100%; height: auto; }
.dd-door-side { flex: 1 1 24rem; min-width: 0; display: flex; flex-direction: column; gap: 0.7rem; align-items: flex-start; }
.dd-door-title {
  margin: 0;
  font-family: 'EB Garamond', Georgia, serif;
  font-size: 1.45rem;
  line-height: 1.25;
  color: #f5f0e6;
  text-wrap: balance;
}
.dd-door-meta {
  margin: 0;
  font-size: 0.82rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--gold-dim);
}

.dd-pdf-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.85rem 1.6rem;
  border: 1.5px solid var(--gold);
  border-radius: 999px;
  font-family: 'Inter', system-ui, sans-serif;
  font-weight: 500;
  font-size: 1.05rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  text-decoration: none;
  color: var(--gold-bright);
  background: rgba(232, 185, 74, 0.08);
  transition: background 0.2s, color 0.2s, border-color 0.2s;
}
.dd-pdf-btn:hover,
.dd-pdf-btn:focus-visible {
  background: var(--gold);
  color: #141210;
  border-color: var(--gold-bright);
  outline: none;
}
.dd-pdf-arrow { font-size: 1.15em; line-height: 1; }
.dd-pdf-meta {
  margin: 0;
  font-size: 0.86rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--gold-dim);
}
.dd-pdf-note {
  margin: 0;
  max-width: 30rem;
  font-size: 0.95rem;
  line-height: 1.4;
  color: #cfc9bd;
}

.dd-cap {
  max-width: 68rem;
  margin: 0.75rem auto 0;
  font-size: 0.95rem;
  line-height: 1.45;
  color: #cfc9bd;
  text-align: center;
  text-wrap: balance;
}
.dd-credit {
  display: block;
  margin-top: 0.3rem;
  font-size: 0.82rem;
  letter-spacing: 0.04em;
  color: var(--gold);
  opacity: 0.85;
}
.dd-cap :deep(i),
.dd-math :deep(i) { font-family: 'EB Garamond', serif; font-size: 1.12em; }
.dd-cap :deep(sub),
.dd-cap :deep(sup) { font-size: 0.72em; }

/* ── tables ───────────────────────────────────────────────────────── */
/* the stress-space definitions: the TeX at ~2.3 px per bp (≈ 23 px
   math), on the tables' dark plate between gold rules */
.dd-eqs {
  --eqk: min(2.3px, 0.17vw);
  width: fit-content;
  max-width: 100%;
  margin: 0 auto;
  padding: 1.4rem 2.4rem;
  background: rgba(0, 0, 0, 0.35);
  border-top: 1.5px solid var(--gold);
  border-bottom: 1.5px solid var(--gold);
  overflow-x: auto;
}
.dd-eqs--sup {
  /* a touch smaller than the definitions' 2.3: the boundary-value line
     is ~446 bp wide and must stay one line inside the column (≈ 980 px
     at 1440, ≈ 880 px at 1280) */
  --eqk: min(2.2px, 0.15vw);
  padding: 1.5rem 2.2rem;
}
.dd-table-wrap {
  overflow-x: auto;
  display: flex;
  justify-content: center;
}
.dd-table {
  border-collapse: collapse;
  font-size: 1.08rem;
  color: #e2ded6;
  background: rgba(0, 0, 0, 0.35);
  border-top: 1.5px solid var(--gold);
  border-bottom: 1.5px solid var(--gold);
}
.dd-table th {
  font-weight: 500;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--gold);
  text-align: left;
  padding: 0.7rem 1.3rem 0.6rem;
  border-bottom: 1px solid var(--gold-faint);
}
.dd-table--kappa th.dd-math {
  text-transform: none;
  letter-spacing: 0.01em;
  font-size: 1.05rem;
}
.dd-table--kappa td { padding: 0.7rem 1.6rem; }
/* κ in a math serif: EB Garamond's κ reads as an x, Inter's as a K. */
.dd-k { font-family: 'STIX Two Text', 'Cambria Math', 'Times New Roman', Times, serif; font-style: italic; }
.dd-table td {
  padding: 0.55rem 1.3rem;
  border-bottom: 1px solid rgba(232, 185, 74, 0.07);
  white-space: nowrap;
}
.dd-table tr:last-child td { border-bottom: none; }
.dd-row-n3 td { background: rgba(232, 185, 74, 0.05); }
.dd-kappa {
  font-family: 'EB Garamond', serif;
  font-size: 1.5rem;
}
.dd-kappa i { font-size: 1.05em; }
/* A superscript over a subscript (κ^s_{1,τ}, 0.78^{+0.12}_{-0.13}). */
.dd-ss {
  display: inline-flex;
  flex-direction: column;
  vertical-align: middle;
  margin: 0 0.1em 0 0.08em;
  font-size: 0.6em;
  line-height: 1.1;
}
.dd-ss i { font-size: 1em; }
/* the same, inside a v-html figure title (#superposition) */
.dd-fig-title :deep(.dd-ss) {
  display: inline-flex;
  flex-direction: column;
  vertical-align: middle;
  margin: 0 0.1em 0 0.04em;
  font-size: 0.55em;
  line-height: 1.05;
}
.dd-fig-title :deep(sup) { font-size: 0.55em; }

/* Chapter 2's wide tables (thesis Tables 2.1–2.3). */
.dd-table--wide { font-size: 0.98rem; }
.dd-table--wide th,
.dd-table--wide td { padding: 0.42rem 0.85rem; }
.dd-table--wide .dd-math { text-transform: none; letter-spacing: 0.01em; font-size: 0.98rem; }
.dd-table .dd-units th {
  padding-top: 0;
  font-size: 0.66rem;
  letter-spacing: 0.06em;
  text-transform: none;
  color: var(--gold-dim);
}
.dd-table--wide thead tr:first-child th { border-bottom: none; padding-bottom: 0.2rem; }
.dd-num { text-align: right; font-variant-numeric: tabular-nums; }
th.dd-num { text-align: right; }
.dd-lake { font-weight: 600; color: #f1ead8; }
.dd-delta { color: var(--gold-bright); }
.dd-table--stress tbody.dd-tgroup + tbody.dd-tgroup tr:first-child td { border-top: 1px solid var(--gold-faint); }
.dd-center { vertical-align: top; white-space: nowrap; }
.dd-center-date {
  display: block;
  font-size: 0.74rem;
  color: #a39d90;
}
.dd-cls {
  display: inline-block;
  width: 0.62rem;
  height: 0.62rem;
  margin-right: 0.45rem;
  border-radius: 50%;
  vertical-align: 0.02em;
}
.dd-cls--englacial { background: #26c6da; border: 1px solid #000; }
.dd-cls--lateral { background: #8c8c8c; border: 1px solid #000; }
.dd-cls--none { background: transparent; border: 1.5px solid #e2ded6; }

/* ── stubs ────────────────────────────────────────────────────────── */
.dd-stub-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.6rem;
  margin-top: 2rem;
}
.dd-stub-frame {
  aspect-ratio: 16 / 9;
  border: 1.5px solid var(--gold-faint);
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(232, 185, 74, 0.06), rgba(232, 185, 74, 0) 60%), #07080b;
}

/* ── full screen ──────────────────────────────────────────────────── */
.dd-lb {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(3, 3, 5, 0.97);
  cursor: zoom-out;
  padding: 3.4rem 2vw 2vh;
  box-sizing: border-box;
}
.dd-lb-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  background: #fff;
  border-radius: 6px;
  box-shadow: 0 20px 60px -20px rgba(0, 0, 0, 0.9);
}
.dd-lb-head {
  position: absolute;
  top: 1rem;
  left: 2vw;
  right: 5rem;
  display: flex;
  align-items: baseline;
  gap: 1rem;
  pointer-events: none;
}
.dd-lb-tag {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.74rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--gold-dim);
}
.dd-lb-title {
  font-family: 'EB Garamond', serif;
  font-size: 1.4rem;
  color: var(--gold-bright);
}
.dd-lb-close {
  position: absolute;
  top: 0.8rem;
  right: 1.2rem;
  width: 2.2rem;
  height: 2.2rem;
  border-radius: 50%;
  border: 1px solid var(--gold-faint);
  background: rgba(0, 0, 0, 0.6);
  color: var(--gold);
  font-size: 0.95rem;
  cursor: pointer;
}
.dd-lb-close:hover { color: #fff; border-color: var(--gold); }
.dd-lb-enter-active,
.dd-lb-leave-active { transition: opacity 0.2s ease; }
.dd-lb-enter-from,
.dd-lb-leave-to { opacity: 0; }

/* Narrow: the rail becomes a row above the page. */
@media (max-width: 1000px) {
  .dd {
    grid-template-columns: minmax(0, 1fr);
    gap: 1rem;
  }
  .dd-rail {
    position: static;
    max-height: none;
  }
  .dd-switch { flex-direction: row; }
  .dd-switch-btn { flex: 1; }
  .dd-index { display: none; }
  .dd-stub-grid { grid-template-columns: minmax(0, 1fr); }
}
</style>
