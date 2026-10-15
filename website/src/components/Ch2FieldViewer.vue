<template>
  <!-- The Chapter 2 field viewer: any of the
       seven center lakes, ELASTIC | VISCOUS, and every surface field of the
       SI overview figures (and the rest of the same netCDFs), one big panel.
       The picker is the SI overview in miniature — the same rows and
       columns, each cell the field's own thumbnail. Data + recipe:
       config/ch2Fields.ts, cinematic/scene_addl/build_deeper_ch02.py. -->
  <div class="fv">
    <div class="fv-controls">
      <div class="fv-lakes" role="radiogroup" aria-label="Lake">
        <button
          v-for="l in CH2_FIELD_LAKES"
          :key="l.num"
          class="fv-lake"
          :class="{ 'fv-lake--on': l.num === lake }"
          role="radio"
          :aria-checked="l.num === lake"
          @click="setLake(l.num)"
        >
          <span class="fv-lake-num">{{ l.num }}</span>
          <span class="fv-lake-sim">{{ l.sim }}</span>
        </button>
      </div>
      <div class="fv-model" role="radiogroup" aria-label="Model">
        <button
          v-for="m in CH2_MODELS"
          :key="m"
          class="fv-model-btn"
          :class="{ 'fv-model-btn--on': m === model }"
          role="radio"
          :aria-checked="m === model"
          @click="setModel(m)"
        >{{ m }}</button>
      </div>
    </div>

    <div class="fv-body">
      <div class="fv-pick">
        <template v-for="r in rows" :key="r.id">
          <div v-if="r.id === 'data'" class="fv-head">
            <span />
            <span v-for="c in CH2_DATA_COLUMNS" :key="c">{{ c }}</span>
          </div>
          <div v-if="r.id === rows[1]?.id" class="fv-head">
            <span />
            <span v-for="c in CH2_COLUMNS[model]" :key="c">{{ c }}</span>
          </div>
          <div class="fv-row">
            <span class="fv-row-label" v-html="r.label" />
            <button
              v-for="c in [0, 1, 2]"
              :key="c"
              class="fv-cell"
              :class="{ 'fv-cell--on': ch2FieldKey(r.id, c) === field }"
              :aria-label="`${r.id === 'data' ? CH2_DATA_COLUMNS[c] : CH2_COLUMNS[model][c]}${r.id === 'data' ? '' : ' ' + r.id}`"
              :aria-pressed="ch2FieldKey(r.id, c) === field"
              @click="setField(ch2FieldKey(r.id, c))"
            >
              <img v-if="thumbSrc(r.id, c)" :src="thumbSrc(r.id, c) ?? undefined" alt="" draggable="false" fetchpriority="low" />
            </button>
          </div>
        </template>

        <ul class="fv-legend">
          <li v-for="c in CH2_CLASS_LEGEND" :key="c.cls">
            <svg width="26" height="10" viewBox="0 0 26 10" aria-hidden="true">
              <line x1="1" y1="5" x2="25" y2="5" stroke="#d8d2c4" stroke-width="5" :stroke-dasharray="CH2_CLASS_STYLE[c.cls].dash ? '3 3' : undefined" />
              <line x1="1" y1="5" x2="25" y2="5" :stroke="CH2_CLASS_STYLE[c.cls].color" stroke-width="3" :stroke-dasharray="CH2_CLASS_STYLE[c.cls].dash ? '3 3' : undefined" />
            </svg>
            <span>{{ c.label }}</span>
          </li>
        </ul>
      </div>

      <div
        class="fv-paper"
        role="button"
        tabindex="0"
        :aria-label="`${shown ? `Lake ${shown.meta.num}` : 'Field'} — full screen`"
        @click="openFull"
        @keydown.enter.prevent="openFull"
      >
        <Ch2FieldPaper
          v-if="shown"
          :meta="shown.meta"
          :model="shown.model"
          :field-key="shown.key"
          :src="shown.src"
          :label="shown.label"
        />
        <div v-else class="fv-paper-blank" />
      </div>
    </div>

    <Teleport to="body">
      <Transition name="fv-full">
        <div v-if="full && shown" class="fv-full" role="dialog" aria-modal="true" :aria-label="`Lake ${shown.meta.num}`" @click="full = false">
          <div class="fv-full-paper" @click.stop="full = false">
            <Ch2FieldPaper :meta="shown.meta" :model="shown.model" :field-key="shown.key" :src="shown.src" :label="shown.label" />
          </div>
          <button class="fv-full-close" aria-label="Close" @click.stop="full = false">✕</button>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import Ch2FieldPaper from './Ch2FieldPaper.vue'
import {
  CH2_CLASS_LEGEND,
  CH2_CLASS_STYLE,
  CH2_COLUMNS,
  CH2_DATA_COLUMNS,
  CH2_DEFAULT_FIELD,
  CH2_DEFAULT_LAKE,
  CH2_DEFAULT_MODEL,
  CH2_FIELD_LAKES,
  CH2_MODELS,
  CH2_ROWS,
  ch2CellLabel,
  ch2CellModel,
  ch2FieldKey,
  ch2FieldKeys,
  type Ch2Row,
  ch2FieldSrc,
  ch2CaseLabel,
  ch2LakeJson,
  ch2MapField,
  ch2TexSrc,
  type Ch2LakeMeta,
  type Ch2Model,
} from '../config/ch2Fields'

// ── the selection (what was clicked) ────────────────────────────────────
// Optional deep link: ?lake=2394&model=elastic&field=st1_d (read once).
const route = useRoute()
function q(name: string): string | null {
  const v = route.query[name]
  return typeof v === 'string' ? v : null
}
const qLake = Number(q('lake'))
const lake = ref<number>(CH2_FIELD_LAKES.some((l) => l.num === qLake) ? qLake : CH2_DEFAULT_LAKE)
const qModel = q('model')
const model = ref<Ch2Model>(qModel === 'elastic' || qModel === 'viscous' ? qModel : CH2_DEFAULT_MODEL)
const qField = q('field')
const field = ref<string>(qField && ch2FieldKeys(model.value).includes(qField) ? qField : CH2_DEFAULT_FIELD)

const rows = computed(() => CH2_ROWS[model.value])

function setLake(n: number): void {
  lake.value = n
}
function setModel(m: Ch2Model): void {
  if (m === model.value) return
  field.value = ch2MapField(field.value, m)
  model.value = m
}
function setField(k: string): void {
  field.value = k
}

// ── what is on the paper (committed only once its image has decoded) ───
interface Shown {
  meta: Ch2LakeMeta
  /** The model whose colour bar + words the panel shows (the elastic σ
   *  pre cells show the viscous no-patch field — ch2CellModel). */
  model: Ch2Model
  key: string
  src: string
  label?: string
}

// ── the elastic σ cells (config/ch2Fields.ts): pre = the
// viscous no-patch field; post = the superposed σ^V_pre + Δσ^E, BAKED since
// fields_v3 with the SI's hashes and contour (it was re-projected here from
// the block's drape until then — hence no hashes, which the director noticed) ──
/** A cell's raster: the bake's (the elastic σ pre cells = the viscous pre's). */
function cellSrc(n: number, m: Ch2Model, k: string, thumb = false): string | null {
  return ch2FieldSrc(n, ch2CellModel(m, k), k, thumb)
}
function thumbSrc(row: Ch2Row, c: number): string | null {
  const k = ch2FieldKey(row, c)
  return cellSrc(lake.value, model.value, k, true)
}
const shown = shallowRef<Shown | null>(null)

const metaCache = new Map<number, Promise<Ch2LakeMeta>>()
function loadMeta(n: number): Promise<Ch2LakeMeta> {
  let p = metaCache.get(n)
  if (!p) {
    p = fetch(ch2LakeJson(n)).then((r) => {
      if (!r.ok) throw new Error(`lake_${n}.json: HTTP ${r.status}`)
      return r.json() as Promise<Ch2LakeMeta>
    })
    p.catch(() => metaCache.delete(n))
    metaCache.set(n, p)
  }
  return p
}

// Background preloads: plain <img> requests (the same mode the paper's
// <img> uses — never a CORS fetch of the same URL), kept referenced so
// the browser does not cancel them. Decoding happens on show.
const warm = new Map<string, HTMLImageElement>()
function preload(url: string, priority: 'high' | 'low' = 'low'): HTMLImageElement {
  let im = warm.get(url)
  if (!im) {
    im = new Image()
    im.decoding = 'async'
    im.fetchPriority = priority
    im.src = url
    warm.set(url, im)
  }
  return im
}
async function decoded(url: string): Promise<void> {
  try {
    await preload(url, 'high').decode()
  } catch {
    // A failed decode still shows (the browser retries on paint).
    console.warn(`[fields] could not decode ${url}`)
  }
}

/** The current lake's set: this model's fields first (nearest the
 *  selection), then the other model's. Other lakes' rasters are let go. */
function warmLake(n: number, m: Ch2Model, key: string): void {
  const mine = `/${n}_`
  for (const url of warm.keys()) if (url.includes('/fields') && !url.includes(mine)) warm.delete(url)
  const keys = ch2FieldKeys(m)
  const i = Math.max(0, keys.indexOf(key))
  const order = [...keys.slice(i), ...keys.slice(0, i)]
  for (const k of order) preload(ch2FieldSrc(n, ch2CellModel(m, k), k))
  const other: Ch2Model = m === 'viscous' ? 'elastic' : 'viscous'
  window.setTimeout(() => {
    if (lake.value !== n) return
    for (const k of ch2FieldKeys(other)) preload(ch2FieldSrc(n, ch2CellModel(other, k), k))
  }, 1500)
}

let token = 0
async function commit(): Promise<void> {
  const my = ++token
  const n = lake.value
  const m = model.value
  const k = field.value
  try {
    const src = ch2FieldSrc(n, ch2CellModel(m, k), k)
    const [meta] = await Promise.all([loadMeta(n), decoded(src)])
    if (my !== token) return
    const label = ch2CellLabel(k, m)
    shown.value = { meta, model: ch2CellModel(m, k), key: k, src, label: label === ch2CaseLabel(k, m) ? undefined : label }
    // Only now the rest of the lake's set, so it never competes with the
    // field that was asked for.
    warmLake(n, m, k)
  } catch (e) {
    console.warn('[fields]', e)
  }
}

watch([lake, model, field], () => void commit(), { immediate: true })

// The names are tiny: fetch them all once (as the paper's <image> will).
onMounted(() => {
  for (const m of CH2_MODELS) for (const k of ch2FieldKeys(m)) preload(ch2TexSrc(k))
})

// ── full screen: the paper alone; ← / → step the fields, ↑ / ↓ the lakes ─
const full = ref(false)
function openFull(): void {
  if (shown.value) full.value = true
}
function stepField(d: number): void {
  const keys = ch2FieldKeys(model.value)
  const i = keys.indexOf(field.value)
  field.value = keys[(i + d + keys.length) % keys.length]
}
function stepLake(d: number): void {
  const i = CH2_FIELD_LAKES.findIndex((l) => l.num === lake.value)
  lake.value = CH2_FIELD_LAKES[(i + d + CH2_FIELD_LAKES.length) % CH2_FIELD_LAKES.length].num
}
function onKey(e: KeyboardEvent): void {
  if (!full.value) return
  if (e.key === 'Escape') full.value = false
  else if (e.key === 'ArrowRight') stepField(1)
  else if (e.key === 'ArrowLeft') stepField(-1)
  else if (e.key === 'ArrowDown') stepLake(1)
  else if (e.key === 'ArrowUp') stepLake(-1)
  else return
  e.preventDefault()
  e.stopPropagation()
}
onMounted(() => window.addEventListener('keydown', onKey, true))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey, true)
  warm.clear()
})
</script>

<style scoped>
.fv {
  /* What the viewer leaves of the viewport's height for the paper: its
     title row, the controls, the caption and the ribbon's clearance. */
  --fv-chrome: 19.5rem;
  --fv-thumb: 3.35rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* ── controls ─────────────────────────────────────────────────────── */
.fv-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem 1.6rem;
}
.fv-lakes {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.fv-lake {
  display: inline-flex;
  align-items: baseline;
  gap: 0.35rem;
  padding: 0.38rem 0.75rem 0.4rem;
  border: 1px solid var(--gold-faint);
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.45);
  color: var(--gold-dim);
  font-family: 'Inter', system-ui, sans-serif;
  cursor: pointer;
  transition: color 0.2s, background 0.2s, border-color 0.2s;
}
.fv-lake:hover { color: var(--gold-bright); border-color: var(--gold-dim); }
.fv-lake-num {
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  font-variant-numeric: tabular-nums;
}
.fv-lake-sim {
  font-size: 0.74rem;
  letter-spacing: 0.06em;
  opacity: 0.75;
}
.fv-lake--on,
.fv-lake--on:hover {
  color: #0a0a0a;
  background: var(--gold-bright);
  border-color: var(--gold-bright);
}

.fv-model {
  display: inline-flex;
  padding: 0.25rem;
  border: 1px solid var(--gold-faint);
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.45);
}
.fv-model-btn {
  min-width: 7.2rem;
  padding: 0.42rem 1.1rem;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: var(--gold-dim);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  cursor: pointer;
  transition: color 0.2s, background 0.2s;
}
.fv-model-btn:hover { color: var(--gold-bright); }
.fv-model-btn--on,
.fv-model-btn--on:hover {
  color: #0a0a0a;
  background: var(--gold-bright);
}

/* ── body: the picker beside the paper ─────────────────────────────── */
.fv-body {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 1.6rem;
}

.fv-pick {
  flex: none;
  display: flex;
  flex-direction: column;
  gap: 0.28rem;
}
.fv-head,
.fv-row {
  display: grid;
  grid-template-columns: 2.6rem repeat(3, var(--fv-thumb));
  gap: 0.3rem;
  align-items: center;
}
.fv-head {
  margin-top: 0.35rem;
  font-size: 0.62rem;
  line-height: 1.15;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: rgba(244, 207, 106, 0.85);
  text-align: center;
}
.fv-head:first-child { margin-top: 0; }
.fv-row-label {
  font-family: 'EB Garamond', serif;
  font-size: 1.22rem;
  color: #e6dfcf;
  text-align: right;
  padding-right: 0.25rem;
  white-space: nowrap;
}
.fv-row-label :deep(sub) { font-size: 0.66em; }
.fv-row-label :deep(b) { font-weight: 700; }

.fv-cell {
  position: relative;
  width: var(--fv-thumb);
  height: var(--fv-thumb);
  padding: 0;
  border: 1px solid transparent;
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.04);
  cursor: pointer;
  transition: border-color 0.18s, background 0.18s, transform 0.18s;
}
.fv-cell img {
  display: block;
  width: 100%;
  height: 100%;
  filter: saturate(0.85) brightness(0.92);
  transition: filter 0.18s;
}
.fv-cell:hover { border-color: var(--gold-dim); transform: translateY(-1px); }
.fv-cell:hover img { filter: none; }
.fv-cell--on,
.fv-cell--on:hover {
  border-color: var(--gold-bright);
  background: rgba(232, 185, 74, 0.14);
  box-shadow: 0 0 0 1px var(--gold-bright);
}
.fv-cell--on img { filter: none; }

.fv-legend {
  list-style: none;
  margin: 0.9rem 0 0;
  padding: 0 0 0 0.2rem;
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.18rem;
  font-size: 0.8rem;
  color: #bdb6a8;
}
.fv-legend li {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}

/* The paper: white, rounded, a gold hairline, one screen tall at most
   (the page's figure frames' rule); click = full screen. */
.fv-paper {
  flex: 0 1 auto;
  display: block;
  width: min(100%, calc((100vh - var(--fv-chrome)) * 1000 / 930));
  min-width: 0;
  padding: 0;
  border: 1px solid var(--gold-faint);
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
  cursor: zoom-in;
  box-shadow: 0 12px 40px -18px rgba(0, 0, 0, 0.9);
  transition: box-shadow 0.25s, border-color 0.25s;
}
.fv-paper:hover,
.fv-paper:focus-visible {
  border-color: var(--gold);
  box-shadow: 0 14px 44px -14px rgba(232, 185, 74, 0.35);
  outline: none;
}
.fv-paper-blank { aspect-ratio: 1000 / 930; }

/* ── full screen ─────────────────────────────────────────────────── */
.fv-full {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(3, 3, 5, 0.97);
  cursor: zoom-out;
  padding: 2vh 2vw;
  box-sizing: border-box;
}
.fv-full-paper {
  width: min(96vw, calc(96vh * 1000 / 930));
  border-radius: 6px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 20px 60px -20px rgba(0, 0, 0, 0.9);
}
.fv-full-close {
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
.fv-full-close:hover { color: #fff; border-color: var(--gold); }
.fv-full-enter-active,
.fv-full-leave-active { transition: opacity 0.2s ease; }
.fv-full-enter-from,
.fv-full-leave-to { opacity: 0; }

@media (max-width: 1000px) {
  .fv-body {
    flex-direction: column;
    align-items: center;
  }
  .fv-paper { width: 100%; }
  .fv-controls { justify-content: center; }
}
</style>
