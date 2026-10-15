<template>
  <!-- The References page — every paper,
       report and dataset the site leans on, organised by Chapter, by
       Author or by CONCEPT — five sections, each entry
       authors · year · title · one line; a paper may sit in several. The
       control sits UNDER its "Organize by" title (the director's placement); the
       choice lives in ?by=. The
       Introduction's bottom-right link lands on ?chapter=introduction,
       which scrolls to and lights that group. A flat opaque layer ABOVE
       the globe, which keeps rendering beneath it — never a veil. The
       header + control stay put; only the list scrolls. Headings, the
       control and entries only (narrator rule). Data: config/references.ts. -->
  <div class="rf">
    <header class="rf-head">
      <h2 class="rf-title">References</h2>
      <div class="rf-org">
        <span class="rf-seg-label">Organize by</span>
        <div class="rf-seg" role="radiogroup" aria-label="Organize by">
        <button
          v-for="opt in BY_OPTIONS"
          :key="opt.value"
          class="rf-seg-btn"
          :class="{ 'rf-seg-btn--on': by === opt.value }"
          role="radio"
          :aria-checked="by === opt.value"
          @click="setBy(opt.value)"
        >{{ opt.label }}</button>
        </div>
      </div>
    </header>

    <div ref="scroller" class="rf-scroll">
      <div class="rf-inner">
        <!-- CHAPTER view: groups in talk order. -->
        <template v-if="by === 'chapter'">
          <section
            v-for="g in groups"
            :key="g.key"
            :ref="(el) => setGroupEl(g.key, el)"
            class="rf-group"
            :class="{ 'rf-group--lit': focusChapter === g.key }"
            :data-chapter="g.key"
          >
            <h3 class="rf-group-head">
              <span>{{ g.label }}</span>
              <span class="rf-group-n">{{ g.refs.length }}</span>
            </h3>
            <ol class="rf-list">
              <li v-for="r in g.refs" :key="r.id">
                <component
                  :is="refUrl(r) ? 'a' : 'div'"
                  class="rf-entry"
                  :class="{ 'rf-entry--link': !!refUrl(r) }"
                  :href="refUrl(r) ?? undefined"
                  :target="refUrl(r) ? '_blank' : undefined"
                  :rel="refUrl(r) ? 'noopener noreferrer' : undefined"
                >
                  <p class="rf-byline">
                    <template v-for="(a, i) in shownAuthors(r)" :key="i">
                      <span v-if="i > 0">, </span>
                      <strong v-if="AUTHOR_NAMES.has(a)" class="rf-author">{{ a }}</strong>
                      <span v-else>{{ a }}</span>
                    </template>
                    <span v-if="isTruncated(r)"> et al.</span>
                    <span class="rf-year"> · {{ r.year }}</span>
                  </p>
                  <p class="rf-titleline">
                    {{ r.title }}<span v-if="refUrl(r)" class="rf-arrow">↗</span>
                  </p>
                  <p class="rf-venue">
                    <em>{{ r.venue }}</em><span v-if="r.volume">, {{ r.volume }}</span><span v-if="r.pages">, {{ r.pages }}</span>
                    <span v-if="r.status" class="rf-status">{{ r.status }}</span>
                  </p>
                </component>
              </li>
            </ol>
          </section>
        </template>

        <!-- CONCEPT view: the five sections in the director's order,
             each entry authors · year · title · one line. -->
        <template v-else-if="by === 'concept'">
          <section v-for="g in conceptGroups" :key="g.key" class="rf-group">
            <h3 class="rf-group-head">
              <span>{{ g.label }}</span>
              <span class="rf-group-n">{{ g.refs.length }}</span>
            </h3>
            <ol class="rf-list">
              <li v-for="r in g.refs" :key="r.id">
                <component
                  :is="refUrl(r) ? 'a' : 'div'"
                  class="rf-entry rf-entry--concept"
                  :class="{ 'rf-entry--link': !!refUrl(r) }"
                  :href="refUrl(r) ?? undefined"
                  :target="refUrl(r) ? '_blank' : undefined"
                  :rel="refUrl(r) ? 'noopener noreferrer' : undefined"
                >
                  <p class="rf-byline">
                    <template v-for="(a, i) in shownAuthors(r)" :key="i">
                      <span v-if="i > 0">, </span>
                      <strong v-if="AUTHOR_NAMES.has(a)" class="rf-author">{{ a }}</strong>
                      <span v-else>{{ a }}</span>
                    </template>
                    <span v-if="isTruncated(r)"> et al.</span>
                    <span class="rf-year"> · {{ r.year }}</span>
                  </p>
                  <p class="rf-titleline">
                    {{ r.title }}<span v-if="refUrl(r)" class="rf-arrow">↗</span>
                  </p>
                  <p v-if="r.summary" class="rf-summary">{{ r.summary }}</p>
                </component>
              </li>
            </ol>
          </section>
        </template>

        <!-- AUTHOR view: one list by first-author surname, then year. -->
        <ol v-else class="rf-list rf-list--flat">
          <li v-for="r in byAuthor" :key="r.id">
            <component
              :is="refUrl(r) ? 'a' : 'div'"
              class="rf-entry"
              :class="{ 'rf-entry--link': !!refUrl(r) }"
              :href="refUrl(r) ?? undefined"
              :target="refUrl(r) ? '_blank' : undefined"
              :rel="refUrl(r) ? 'noopener noreferrer' : undefined"
            >
              <p class="rf-byline">
                <template v-for="(a, i) in shownAuthors(r)" :key="i">
                  <span v-if="i > 0">, </span>
                  <strong v-if="AUTHOR_NAMES.has(a)" class="rf-author">{{ a }}</strong>
                  <span v-else>{{ a }}</span>
                </template>
                <span v-if="isTruncated(r)"> et al.</span>
                <span class="rf-year"> · {{ r.year }}</span>
              </p>
              <p class="rf-titleline">
                {{ r.title }}<span v-if="refUrl(r)" class="rf-arrow">↗</span>
              </p>
              <p class="rf-venue">
                <em>{{ r.venue }}</em><span v-if="r.volume">, {{ r.volume }}</span><span v-if="r.pages">, {{ r.pages }}</span>
                <span v-if="r.status" class="rf-status">{{ r.status }}</span>
              </p>
              <p class="rf-tags">
                <span v-for="c in chapterShorts(r)" :key="c" class="rf-tag">{{ c }}</span>
              </p>
            </component>
          </li>
        </ol>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch, type ComponentPublicInstance } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  REFERENCES,
  REF_CHAPTERS,
  REF_CONCEPTS,
  AUTHOR_NAMES,
  compareRefs,
  refUrl,
  type ChapterKey,
  type Reference,
} from '../../config/references'

type By = 'chapter' | 'author' | 'concept'
const BY_OPTIONS: { value: By; label: string }[] = [
  { value: 'chapter', label: 'Chapter' },
  { value: 'author', label: 'Author' },
  { value: 'concept', label: 'Concept' },
]

const route = useRoute()
const router = useRouter()

const by = computed<By>(() => (route.query.by === 'author' ? 'author' : route.query.by === 'concept' ? 'concept' : 'chapter'))
const focusChapter = computed<ChapterKey | null>(() => {
  const c = route.query.chapter
  return typeof c === 'string' && REF_CHAPTERS.some((g) => g.key === c) ? (c as ChapterKey) : null
})

function setBy(value: By): void {
  if (value === by.value) return
  // The chapter focus only means something in the chapter view.
  const { chapter: _chapter, ...rest } = route.query
  void _chapter
  router.replace({ query: { ...rest, by: value } })
}

const groups = computed(() =>
  REF_CHAPTERS.map((g) => ({
    ...g,
    refs: REFERENCES.filter((r) => r.chapters.includes(g.key)).sort(compareRefs),
  })).filter((g) => g.refs.length > 0),
)

const byAuthor = computed(() => [...REFERENCES].sort(compareRefs))

// The Concept view: a paper under every concept it carries, each section
// alphabetical by first author like the chapter groups.
const conceptGroups = computed(() =>
  REF_CONCEPTS.map((g) => ({
    ...g,
    refs: REFERENCES.filter((r) => r.concepts?.includes(g.key)).sort(compareRefs),
  })).filter((g) => g.refs.length > 0),
)

/** Long bylines shorten to three + "et al." — never when the dissertation's author is on it. */
const MAX_AUTHORS = 10
function hasAuthor(r: Reference): boolean {
  return r.authors.some((a) => AUTHOR_NAMES.has(a))
}
function shownAuthors(r: Reference): string[] {
  if (r.authors.length > MAX_AUTHORS && !hasAuthor(r)) return r.authors.slice(0, 3)
  return r.authors
}
function isTruncated(r: Reference): boolean {
  return !!r.etAl || shownAuthors(r).length < r.authors.length
}

function chapterShorts(r: Reference): string[] {
  return REF_CHAPTERS.filter((g) => r.chapters.includes(g.key)).map((g) => g.short)
}

// ?chapter=… → scroll that group to the top of the list.
const scroller = ref<HTMLElement | null>(null)
const groupEls = new Map<ChapterKey, HTMLElement>()
function setGroupEl(key: ChapterKey, el: Element | ComponentPublicInstance | null): void {
  if (el instanceof HTMLElement) groupEls.set(key, el)
  else groupEls.delete(key)
}

async function scrollToFocus(smooth: boolean): Promise<void> {
  await nextTick()
  const box = scroller.value
  if (!box) return
  const key = by.value === 'chapter' ? focusChapter.value : null
  const el = key ? groupEls.get(key) : null
  const top = el ? el.offsetTop - 8 : 0
  box.scrollTo({ top: Math.max(0, top), behavior: smooth ? 'smooth' : 'auto' })
}

onMounted(() => { void scrollToFocus(false) })
watch([by, focusChapter], () => { void scrollToFocus(true) })
</script>

<style scoped>
.rf {
  position: fixed;
  inset: 0;
  z-index: 1;
  display: flex;
  flex-direction: column;
  background: radial-gradient(ellipse at 50% 0%, #0f1420 0%, #050505 60%);
  color: #f5f5f5;
  font-family: 'Inter', system-ui, sans-serif;
  padding-top: 8.5vh;
  box-sizing: border-box;
  pointer-events: auto;
}

.rf-head {
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.9rem;
  padding: 0 3vw 1.1rem;
  border-bottom: 1px solid var(--gold-faint);
}

.rf-title {
  font-family: 'EB Garamond', serif;
  font-weight: 400;
  font-size: 2.6rem;
  color: var(--gold);
  margin: 0;
  letter-spacing: 0.02em;
  line-height: 1.1;
}

/* the "Organize by" title ABOVE its control (the director's placement) */
.rf-org {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.45rem;
}

.rf-seg {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.3rem 0.35rem;
  border: 1px solid var(--gold-faint);
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.45);
}

.rf-seg-label {
  font-size: 0.78rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--gold-dim);
}

.rf-seg-btn {
  background: transparent;
  border: 1px solid transparent;
  border-radius: 999px;
  color: var(--gold-dim);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1.02rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  padding: 0.42rem 1.25rem;
  cursor: pointer;
  transition: color 0.2s, background 0.2s, border-color 0.2s;
}

.rf-seg-btn:hover {
  color: var(--gold-bright);
}

.rf-seg-btn--on {
  color: #0a0a0a;
  background: var(--gold-bright);
  border-color: var(--gold-bright);
}

.rf-seg-btn--on:hover {
  color: #0a0a0a;
}

.rf-scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  position: relative;
  padding: 0 3vw 6vh;
}

.rf-inner {
  max-width: 1180px;
  margin: 0 auto;
}

.rf-group {
  padding: 1.6rem 1.4rem 0.6rem;
  margin: 0 -1.4rem;
  border-left: 2px solid transparent;
  transition: background 0.6s, border-color 0.6s;
}

.rf-group--lit {
  border-left-color: var(--gold);
  background: linear-gradient(90deg, rgba(232, 185, 74, 0.07), rgba(232, 185, 74, 0) 70%);
}

.rf-group-head {
  display: flex;
  align-items: baseline;
  gap: 0.8rem;
  font-family: 'EB Garamond', serif;
  font-weight: 400;
  font-size: 1.9rem;
  color: var(--gold);
  margin: 0 0 0.4rem;
  letter-spacing: 0.02em;
}

.rf-group--lit .rf-group-head {
  color: var(--gold-bright);
}

.rf-group-n {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.85rem;
  color: var(--gold-dim);
  letter-spacing: 0.08em;
}

.rf-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.rf-list--flat {
  padding-top: 1.2rem;
}

.rf-entry {
  display: block;
  padding: 0.85rem 1rem;
  margin: 0 -1rem;
  border-radius: 10px;
  color: inherit;
  text-decoration: none;
  transition: background 0.2s;
}

.rf-entry--link {
  cursor: pointer;
}

.rf-entry--link:hover {
  background: rgba(232, 185, 74, 0.07);
}

.rf-entry p {
  margin: 0;
}

.rf-byline {
  font-size: 1.08rem;
  line-height: 1.45;
  color: rgba(245, 245, 245, 0.72);
}

.rf-author {
  color: #fff;
  font-weight: 700;
}

.rf-year {
  color: var(--gold-dim);
}

.rf-titleline {
  font-family: 'EB Garamond', serif;
  font-size: 1.55rem;
  line-height: 1.28;
  color: #f7f3ea;
  margin-top: 0.15rem !important;
}

.rf-entry--link:hover .rf-titleline {
  color: var(--gold-bright);
}

.rf-arrow {
  margin-left: 0.45rem;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.95rem;
  color: var(--gold-dim);
  opacity: 0;
  transition: opacity 0.2s;
}

.rf-entry--link:hover .rf-arrow {
  opacity: 1;
}

.rf-venue {
  font-size: 1.02rem;
  line-height: 1.4;
  color: rgba(245, 245, 245, 0.62);
  margin-top: 0.2rem !important;
}

/* the Concept view's one line under the title */
.rf-summary {
  font-size: 1.08rem;
  line-height: 1.45;
  color: rgba(245, 245, 245, 0.78);
  margin-top: 0.25rem !important;
}

.rf-status {
  display: inline-block;
  margin-left: 0.7rem;
  padding: 0.08rem 0.6rem;
  border: 1px solid var(--gold-faint);
  border-radius: 999px;
  font-size: 0.8rem;
  letter-spacing: 0.07em;
  color: var(--gold);
  vertical-align: 0.08em;
}

.rf-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 0.45rem !important;
}

.rf-tag {
  font-size: 0.8rem;
  font-weight: 500;
  letter-spacing: 0.06em;
  color: var(--gold-dim);
  border: 1px solid var(--gold-faint);
  border-radius: 999px;
  padding: 0.12rem 0.65rem;
}
</style>
