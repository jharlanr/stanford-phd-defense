<template>
  <!-- Additional Work → "Label lakes yourself · the inter-rater 200"
       (the director's brief: a section where a visitor tries
       their hand at labeling lakes — specifically the same 200 lakes used
       in the ESSD paper's inter-rater-reliability study).

       Chapter 3's "a label made live" stage, dealt as a deck: the same
       evidence the three labelers had (the lake's Sentinel-2 season and its
       daily water fraction — LakeSeason.vue) and their own workflow (five
       soft sliders in quarters that must sum to 1 — SoftSliders.vue).
       COMMIT reveals the three labelers' soft labels and their majority;
       the tally on the right scores hard-label agreement from the first
       lake. Labelers 2 and 3 are anonymous; Labeler 1
       is the director (the dataset's primary labeler).

       The deck (ch03/irr2/deck.json, build_irr_movies.py; the movies stay
       the white-outline ch03/irr/ until the red bake has all 200 — see
       IRR_MOVIES): the 55 lakes the labelers split on are dealt two in every
       three until they run out, shuffled per visit; `?lake=<id>` deals
       that lake first; every lake opens on the first day of its stack.
       SUBMIT (a name, once a lake is committed) sends ALL the rows
       committed so far to the labels Worker, which writes that labeler's
       ONE lakelabel-format CSV to R2 (labels/irr/<name-slug>_<16 hex>.csv;
       config/irrCsv.ts fixes the format and the key). A name is used once
       (409 → the director's wording under the field); later SUBMITs carry the
       Worker's token and overwrite the same file. Never a download; a
       failed POST leaves SUBMIT to press again. No storage anywhere — a
       reload starts fresh (and forgets the token: a new name then).
       Movies are fetched as blobs, the next lake's while this one is
       labeled, so NEXT never waits. Keys 1–5 set a hard label (← → PgUp
       PgDn belong to the site's BACK / NEXT). Figures and labels only; the
       definitions live in hover titles (the site-wide rule: the presenter
       narrates). -->
  <div class="lb-root">
    <header class="lb-head">
      <!-- (no eyebrow — the director found the "ESSD · inter-rater subset"
           line unnecessary on this page) -->
      <h2 class="lb-title">Label lakes yourself · the inter-rater 200</h2>
    </header>

    <div class="lb-grid">
      <!-- the lake: the labelers' evidence -->
      <section class="lb-lake">
        <div class="lb-idrow">
          <span class="lb-id">{{ lake?.id ?? '' }}</span>
          <span v-if="order.length" class="lb-pos">{{ pos + 1 }} / {{ order.length }}</span>
        </div>
        <LakeSeason
          :key="lake?.id ?? 'none'"
          :src="cur?.src ?? null"
          :sidecar="cur?.sidecar ?? null"
          :year="lake?.year"
        />
      </section>

      <!-- the label -->
      <section class="lb-label">
        <SoftSliders v-model="raw" :disabled="committed || !lake" />

        <div class="lb-actions">
          <button class="lb-commit" :disabled="committed || total !== 100 || !lake" @click="commit">
            Commit label
          </button>
          <button class="lb-reset" :disabled="committed" aria-label="clear" @click="raw = emptySoft()">↺</button>
          <!-- lakelabel's notes box: one line, saved with the label -->
          <input
            v-model="notes"
            class="lb-field lb-notes"
            type="text"
            :maxlength="IRR_NOTES_MAX"
            :disabled="committed || !lake"
            placeholder="notes"
            aria-label="notes"
            autocomplete="off"
            spellcheck="false"
          />
          <button v-if="!committed" class="lb-skip" :disabled="!hasNext" @click="advance">Skip</button>
          <button v-else class="lb-next" :disabled="!hasNext" @click="advance">Next lake →</button>
        </div>

        <!-- after the commit: the three labelers on this lake -->
        <div v-if="committed && lake && mine" class="lb-reveal">
          <div class="lb-callout" :class="{ 'lb-callout-split': lake.contested }">
            <span class="lb-callout-k">{{ lake.contested ? 'Experts split' : 'Experts agree' }}</span>
            <span class="lb-callout-sep">·</span>
            <template v-for="(code, ci) in voteCodes" :key="code">
              <span v-if="ci" class="lb-callout-slash">/</span>
              <span class="lb-callout-code" :style="{ color: classColor(code) }">{{ code }}</span>
            </template>
          </div>

          <div class="lb-rev-grid">
            <span />
            <span class="lb-rev-h">soft label</span>
            <span class="lb-rev-h lb-rev-c">hard</span>

            <span class="lb-rev-who lb-rev-you">you</span>
            <div class="lb-rev-bar"><span v-for="(v, i) in mine.p" :key="i" :style="{ width: v * 100 + '%', background: ESSD_CLASSES[i].color }" /></div>
            <span class="lb-rev-code lb-rev-c" :style="{ color: classColor(mine.hard) }">{{ mine.hard }}</span>

            <template v-for="(e, k) in lake.experts" :key="k">
              <span class="lb-rev-who">
                Labeler {{ k + 1 }}<span v-if="k === 0" class="lb-rev-ini"> · {{ LABELER1 }}</span>
              </span>
              <div class="lb-rev-bar"><span v-for="(v, i) in e.p" :key="i" :style="{ width: v * 100 + '%', background: ESSD_CLASSES[i].color }" /></div>
              <span class="lb-rev-code lb-rev-c" :style="{ color: classColor(e.hard) }">
                {{ e.hard }}<i class="lb-mark" :class="e.hard === mine.hard ? 'lb-mark-y' : 'lb-mark-n'">{{ e.hard === mine.hard ? '✓' : '✗' }}</i>
              </span>
            </template>

            <span class="lb-rev-who lb-rev-maj">majority<template v-if="lake.majority"> · {{ lake.votes[lake.majority] }} of 3</template></span>
            <span />
            <span class="lb-rev-code lb-rev-c" :style="{ color: classColor(lake.majority) }">
              <template v-if="lake.majority">{{ lake.majority }}<i class="lb-mark" :class="lake.majority === mine.hard ? 'lb-mark-y' : 'lb-mark-n'">{{ lake.majority === mine.hard ? '✓' : '✗' }}</i></template>
              <template v-else>—</template>
            </span>
          </div>
        </div>
      </section>

      <!-- the running tally: from the first lake, against the three -->
      <aside class="lb-tally">
        <div class="lb-t-head">
          <span class="lb-t-n">{{ tally.n }}</span>
          <span class="lb-t-unit">{{ tally.n === 1 ? 'lake' : 'lakes' }}</span>
          <span class="lb-t-sub">{{ tally.contested }} contested<template v-if="skipped"> · {{ skipped }} skipped</template></span>
        </div>
        <div class="lb-t-legend">
          <span><i class="lb-key-you" />you</span>
          <span :title="REF_DEF"><i class="lb-key-ref" />labelers · same lakes</span>
        </div>

        <div class="lb-t-sec">hard label agreement</div>
        <div v-for="r in tally.rows" :key="r.key" class="lb-t-row" :title="r.def">
          <span class="lb-t-k">{{ r.label }}</span>
          <span class="lb-t-frac">{{ r.den ? `${r.num}/${r.den}` : '' }}</span>
          <span class="lb-t-v">{{ r.you === null ? '—' : pct(r.you) }}</span>
          <div class="lb-t-track">
            <span class="lb-t-fill" :style="{ width: (r.you ?? 0) * 100 + '%' }" />
            <span v-if="r.ref !== null" class="lb-t-mark" :style="{ left: r.ref * 100 + '%' }" />
          </div>
        </div>

        <!-- SUBMIT: a name, then every lake committed so far → that
             labeler's one CSV (nothing to submit to → no row at all) -->
        <template v-if="CAN_SUBMIT && results.length">
          <form class="lb-submit" @submit.prevent="submit">
            <span v-if="owner" class="lb-name-locked" :title="irrShownName(owner.key)">{{ owner.name }}</span>
            <input
              v-else
              ref="nameEl"
              v-model="submitName"
              class="lb-field lb-name"
              type="text"
              name="name"
              :maxlength="IRR_NAME_MAX"
              placeholder="name"
              aria-label="name"
              autocomplete="name"
              spellcheck="false"
              :aria-invalid="nameTaken"
              @input="nameTaken = false"
            />
            <button class="lb-submit-btn" type="submit" :disabled="!canSubmit">{{ submitting ? '…' : 'Submit' }}</button>
          </form>
          <div class="lb-submit-state" aria-live="polite">
            <span v-if="nameTaken" class="lb-wrong">{{ NAME_TAKEN }}</span>
            <span v-else-if="failed" class="lb-wrong">not submitted<template v-if="failed.status"> · {{ failed.status }}</template></span>
            <span v-if="submitted" class="lb-submitted"><b>{{ submitted.n }} {{ submitted.n === 1 ? 'lake' : 'lakes' }}</b> · submitted</span>
          </div>
        </template>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import { useRoute } from 'vue-router'
import LakeSeason, { type SeasonSidecar } from '../LakeSeason.vue'
import SoftSliders from '../SoftSliders.vue'
import { mediaUrl } from '../../config/media'
import { ESSD_CLASSES, LABELS_ENDPOINT, classColor, emptySoft, softArgmax, softTotal } from '../../config/essdLabel'
import { IRR_NAME_MAX, IRR_NOTES_MAX, IRR_NO_SLUG, irrShownName, nameSlug, type IrrRow } from '../../config/irrCsv'

// The deck + the movies and sidecars: R2 ch03/irr2/ — the RED-outline
// bake (the director asked for a red lake outline), all 200 lakes,
// no initials for Labelers 2 and 3 in the deck. The white-outline set
// ch03/irr/ is superseded; it stays on R2 until the director retires it.
const IRR_DECK = 'ch03/irr2/deck.json'
const IRR_MOVIES = 'ch03/irr2'

// ── the deck ──────────────────────────────────────────────────────────
interface Expert { hard: string; p: number[] }
interface DeckLake {
  id: string
  year: number
  /** the reference CSV's label = Labeler 1's (the dataset's primary label) */
  consensus: string
  /** the 2-of-3 vote; null on the five three-way splits */
  majority: string | null
  experts: Expert[]
  contested: boolean
  split: string | null
  votes: Record<string, number>
}
interface Deck {
  lakes: DeckLake[]
}

const deck = shallowRef<Deck | null>(null)
const byId = computed(() => new Map((deck.value?.lakes ?? []).map((l) => [l.id, l])))
const order = ref<string[]>([])
const pos = ref(0)
const lake = computed<DeckLake | null>(() => byId.value.get(order.value[pos.value]) ?? null)
const hasNext = computed(() => pos.value < order.value.length - 1)

function shuffle<T>(a: T[]): T[] {
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}
// The contested lakes two in every three (C C U C C U …) until they run
// out, then the unanimous rest; `first` (a ?lake= deep link) leads.
function deal(lakes: DeckLake[], first: string | null): string[] {
  const c = shuffle(lakes.filter((l) => l.contested && l.id !== first).map((l) => l.id))
  const u = shuffle(lakes.filter((l) => !l.contested && l.id !== first).map((l) => l.id))
  const out: string[] = first ? [first] : []
  let k = out.length
  while (c.length || u.length) {
    const wantU = k % 3 === 2
    out.push((wantU ? u.shift() ?? c.shift() : c.shift() ?? u.shift()) as string)
    k++
  }
  return out
}

// Labeler 1 is the director; Labelers 2 and 3 carry no initials anywhere
// (the director asked that they be anonymised).
const LABELER1 = 'J. H. R.'

// ── the movies, as blobs: this lake's and the next one's ──────────────
interface Loaded { src: string; sidecar: SeasonSidecar | null; blob: boolean }
const loads = new Map<string, Promise<Loaded>>()
const loaded = new Map<string, Loaded>()
const cur = shallowRef<Loaded | null>(null)
let alive = true

// The lake on screen asks first ('high'); the next lake warms behind it
// ('low') — on a cold deep link the Globe's textures share the host.
async function fetchBlobUrl(url: string, priority: RequestPriority): Promise<string | null> {
  try {
    const r = await fetch(url, { priority })
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    // Typed explicitly: WebKit will not play an untyped blob.
    return URL.createObjectURL(new Blob([await r.arrayBuffer()], { type: 'video/mp4' }))
  } catch (e) {
    console.warn('[label] movie fetch failed, falling back to the URL', url, e)
    return null
  }
}
async function fetchSidecar(url: string, priority: RequestPriority): Promise<SeasonSidecar | null> {
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const r = await fetch(url, { priority })
      if (r.ok) return (await r.json()) as SeasonSidecar
    } catch {
      // once more, then the scrubber simply has one frame
    }
  }
  console.warn('[label] sidecar fetch failed', url)
  return null
}
function load(id: string, priority: RequestPriority = 'low'): Promise<Loaded> {
  let p = loads.get(id)
  if (!p) {
    const mp4 = mediaUrl(`${IRR_MOVIES}/${id}.mp4`)
    const job: Promise<Loaded> = Promise.all([fetchBlobUrl(mp4, priority), fetchSidecar(mediaUrl(`${IRR_MOVIES}/${id}.json`), priority)]).then(([blob, sidecar]) => {
      const l: Loaded = { src: blob ?? mp4, sidecar, blob: !!blob }
      // Released while in flight (skipped past, or the page left): let go.
      if (!alive || loads.get(id) !== job) {
        if (l.blob) URL.revokeObjectURL(l.src)
      } else {
        loaded.set(id, l)
      }
      return l
    })
    p = job
    loads.set(id, p)
  }
  return p
}
function release(id: string): void {
  const l = loaded.get(id)
  if (l?.blob) URL.revokeObjectURL(l.src)
  loaded.delete(id)
  loads.delete(id)
}
// Show this lake (instantly when pre-warmed), warm the next, let go of
// anything further back than the previous one.
async function show(): Promise<void> {
  const id = order.value[pos.value]
  if (!id) return
  const ready = loaded.get(id)
  cur.value = ready ?? null
  const next = order.value[pos.value + 1]
  const keep = new Set([order.value[pos.value - 1], id, next])
  for (const k of [...loads.keys()]) if (!keep.has(k)) release(k)
  if (!ready) {
    const l = await load(id, 'high')
    if (order.value[pos.value] === id) cur.value = l
  }
  if (next) void load(next)
}

// ── the label ─────────────────────────────────────────────────────────
const raw = ref(emptySoft())
const total = computed(() => softTotal(raw.value))
const committed = ref(false)
const notes = ref('')
interface Result { lake: DeckLake; p: number[]; hard: string; notes: string }
const results = ref<Result[]>([])
const skipped = ref(0)
const mine = computed<Result | null>(() => {
  const r = results.value[results.value.length - 1]
  return committed.value && r && r.lake.id === lake.value?.id ? r : null
})
const voteCodes = computed(() => Object.keys(lake.value?.votes ?? {}))

function commit(): void {
  const l = lake.value
  if (!l || committed.value || total.value !== 100) return
  const p = ESSD_CLASSES.map((c) => raw.value[c.code] / 100)
  results.value = [...results.value, { lake: l, p, hard: softArgmax(p), notes: notes.value }]
  committed.value = true
}
function advance(): void {
  if (!hasNext.value) return
  if (!committed.value) skipped.value += 1
  pos.value += 1
  committed.value = false
  raw.value = emptySoft()
  notes.value = ''
  void show()
}

// A slider on THIS page keeps the arrow keys, however it got the focus
// (a visitor nudging a slider must not lose the tally to the site-wide
// ← → = BACK/NEXT rule, Explore.vue's onPresenterKey — this is an
// explorable, not a talk beat; Page Down / Page Up still navigate).
// Capture phase, so the window's bubble listener never sees it; the
// native nudge is left alone.
function onArrowGuard(e: KeyboardEvent): void {
  const t = e.target as HTMLInputElement | null
  if (e.key.startsWith('Arrow') && t?.tagName === 'INPUT' && t.type === 'range') e.stopPropagation()
}

// 1–5: a hard label in one key (100 % on that class).
function onKey(e: KeyboardEvent): void {
  if (e.defaultPrevented || e.repeat || e.metaKey || e.ctrlKey || e.altKey) return
  const k = '12345'.indexOf(e.key)
  if (k < 0 || committed.value || !lake.value) return
  const t = e.target as HTMLElement | null
  if (t && (t.tagName === 'TEXTAREA' || t.isContentEditable || (t.tagName === 'INPUT' && (t as HTMLInputElement).type === 'text'))) return
  const next = emptySoft()
  next[ESSD_CLASSES[k].code] = 100
  raw.value = next
  e.preventDefault()
}

// ── the scores: hard-label agreement ──────────────────────────────────
const REF_DEF = 'On the lakes you labeled: how the other labelers score against the same reference.'

interface TallyRow { key: string; label: string; def: string; you: number | null; ref: number | null; num: number; den: number }
const tally = computed(() => {
  const R = results.value
  const n = R.length
  const rows: TallyRow[] = []
  for (let k = 0; k < 3; k++) {
    const num = R.filter((r) => r.hard === r.lake.experts[k].hard).length
    // the other two labelers' agreement with Labeler k, on these lakes
    let refSum = 0
    for (let j = 0; j < 3; j++) {
      if (j === k) continue
      refSum += R.filter((r) => r.lake.experts[j].hard === r.lake.experts[k].hard).length
    }
    rows.push({
      key: `l${k}`,
      label: `Labeler ${k + 1}`,
      def: `Labeler ${k + 1}${k === 0 ? ` (${LABELER1}), the published label` : ''}: the share of your lakes where your hard label (argmax; a tie goes to the lower class) is theirs. Tick = the other two labelers against Labeler ${k + 1} on the same lakes.`,
      you: n ? num / n : null,
      ref: n ? refSum / (2 * n) : null,
      num,
      den: n,
    })
  }
  const withMaj = R.filter((r) => r.lake.majority !== null)
  const numMaj = withMaj.filter((r) => r.hard === r.lake.majority).length
  rows.push({
    key: 'maj',
    label: 'Majority',
    def: 'The 2-of-3 vote of the labelers (none on a three-way split — those lakes are left out).',
    you: withMaj.length ? numMaj / withMaj.length : null,
    ref: null,
    num: numMaj,
    den: withMaj.length,
  })
  return { n, contested: R.filter((r) => r.lake.contested).length, rows }
})

function pct(v: number): string {
  return `${Math.round(v * 100)}%`
}

// ── SUBMIT: every lake committed so far → the labels Worker → R2 ──────
// The director's requirements: the visitor must never see a save-to-disk
// dialog; the button says "submit", not "save"; and a name entered twice
// is refused with the message "labeler with that name already exists,
// use a different name".
// So: NO download, ever. A name is used once (by slug); the first SUBMIT
// gets a token from the Worker, kept in memory only, and every later SUBMIT
// sends it, so the Worker overwrites that labeler's one file with all the
// rows. A reload forgets the token — that visitor then needs a new name.
// A failed POST keeps the rows and leaves SUBMIT to press again (a 429
// waits out its Retry-After first).
const CAN_SUBMIT = !!LABELS_ENDPOINT
/** The refusal shown for a taken name; the director's wording, verbatim. */
const NAME_TAKEN = 'labeler with that name already exists, use a different name'
const submitName = ref('')
const nameEl = ref<HTMLInputElement | null>(null)
const submitting = ref(false)
const nameTaken = ref(false)
const failed = ref<{ status: number | null } | null>(null)
const cooling = ref(false)
let coolTimer = 0
/** The name this visitor submitted under, once the Worker took it. */
const owner = ref<{ name: string; key: string } | null>(null)
let ownerToken: string | null = null // memory only, never stored
const submitted = ref<{ n: number } | null>(null)
const canSubmit = computed(
  () =>
    !submitting.value &&
    !cooling.value &&
    !nameTaken.value &&
    results.value.length > (submitted.value?.n ?? 0) &&
    !!(owner.value?.name ?? submitName.value.trim()),
)

function rowsToSubmit(): IrrRow[] {
  return results.value.map((r) => ({
    lake_id: r.lake.id,
    p_ND: r.p[0],
    p_HF: r.p[1],
    p_MD: r.p[2],
    p_LD: r.p[3],
    p_CD: r.p[4],
    notes: r.notes,
    flagged: false,
  }))
}
type Posted =
  | { ok: true; key: string; token: string | null }
  | { ok: false; status: number | null; nameRefused: boolean; retryAfter: number }

/** One POST to the Worker. status null = no answer (offline, timeout). */
async function postSubmit(name: string, rows: IrrRow[], token: string | null): Promise<Posted> {
  const ctl = new AbortController()
  const timer = window.setTimeout(() => ctl.abort(), 12000)
  try {
    const r = await fetch(LABELS_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(token ? { name, rows, token } : { name, rows }),
      signal: ctl.signal,
    })
    const j = (await r.json().catch(() => ({}))) as { key?: unknown; token?: unknown; field?: unknown; retryAfter?: unknown }
    if (r.ok && typeof j.key === 'string') {
      return { ok: true, key: j.key, token: typeof j.token === 'string' ? j.token : null }
    }
    console.warn('[label] submit refused', r.status, j)
    const wait = Number(j.retryAfter ?? r.headers.get('Retry-After'))
    return {
      ok: false,
      status: r.status,
      // 409: the name is someone else's; 400 + field name: a name with no a-z/0-9
      nameRefused: r.status === 409 || (r.status === 400 && j.field === 'name'),
      retryAfter: Number.isFinite(wait) && wait > 0 ? Math.min(wait, 60) : 10,
    }
  } catch (e) {
    console.warn('[label] submit failed', e)
    return { ok: false, status: null, nameRefused: false, retryAfter: 0 }
  } finally {
    window.clearTimeout(timer)
  }
}
async function submit(): Promise<void> {
  if (!canSubmit.value) return
  const name = owner.value?.name ?? submitName.value.trim()
  if (nameSlug(name) === IRR_NO_SLUG) {
    nameTaken.value = true // the Worker would refuse it (400) — no round trip
    return
  }
  submitting.value = true
  failed.value = null
  const rows = rowsToSubmit()
  try {
    const res = await postSubmit(name, rows, ownerToken)
    if (res.ok) {
      if (res.token) ownerToken = res.token
      owner.value = { name, key: res.key }
      submitted.value = { n: rows.length }
    } else if (res.nameRefused) {
      // Not (or no longer) this visitor's name: back to the field.
      ownerToken = null
      if (owner.value) submitted.value = null
      owner.value = null
      submitName.value = name
      nameTaken.value = true
      void nextTick(() => nameEl.value?.focus())
    } else {
      failed.value = { status: res.status }
      if (res.status === 429) {
        cooling.value = true
        window.clearTimeout(coolTimer)
        coolTimer = window.setTimeout(() => (cooling.value = false), res.retryAfter * 1000)
      }
    }
  } finally {
    submitting.value = false
  }
}

const route = useRoute()
onMounted(async () => {
  window.addEventListener('keydown', onKey)
  window.addEventListener('keydown', onArrowGuard, true)
  for (let attempt = 0; attempt < 2 && !deck.value; attempt++) {
    try {
      const r = await fetch(mediaUrl(IRR_DECK), { priority: 'high' })
      if (r.ok) deck.value = (await r.json()) as Deck
    } catch {
      // once more
    }
  }
  if (!deck.value || !alive) {
    if (!deck.value) console.warn('[label] deck.json failed to load')
    return
  }
  const q = typeof route.query.lake === 'string' ? route.query.lake : null
  order.value = deal(deck.value.lakes, q && byId.value.has(q) ? q : null)
  pos.value = 0
  void show()
})
onBeforeUnmount(() => {
  alive = false
  window.clearTimeout(coolTimer)
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('keydown', onArrowGuard, true)
  for (const k of [...loaded.keys()]) release(k)
})
</script>

<style scoped>
.lb-root {
  position: fixed;
  inset: 0;
  z-index: 1;
  overflow-y: auto;
  background: radial-gradient(ellipse at 28% 18%, #0f1420 0%, #050505 62%);
  color: #f5f0e6;
  font-family: 'Inter', system-ui, sans-serif;
  padding: 8.5vh 3vw 2.5vh;
  box-sizing: border-box;
  pointer-events: auto;
  /* The lake column is as wide as the HEIGHT under the header allows
     (square movie + scrub + curve ≈ 1.175 × width + 4 rem), and never
     more than a third of the width. */
  --lake: clamp(300px, min(31vw, calc((100vh - 11vh - 4.2rem - 4rem) / 1.175)), 600px);
  --tally: 16.5rem;
}

.lb-head { margin-bottom: 1.6vh; }
.lb-title {
  font-family: 'EB Garamond', serif;
  font-weight: 400;
  font-size: clamp(1.4rem, 2vw, 1.95rem);
  line-height: 1.1;
  color: var(--gold);
  margin: 0;
  letter-spacing: 0.01em;
}

.lb-grid {
  display: grid;
  grid-template-columns: var(--lake) minmax(0, 1fr) var(--tally);
  gap: 1.9vw;
  align-items: start;
}

/* ── the lake ── */
.lb-lake {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  min-width: 0;
}
.lb-idrow {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
  min-height: 1.4rem;
}
.lb-id {
  font-family: ui-monospace, 'SF Mono', Menlo, monospace;
  font-size: 1.05rem;
  letter-spacing: 0.03em;
  color: rgba(245, 240, 230, 0.85);
}
.lb-pos {
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  color: rgba(245, 240, 230, 0.45);
  font-variant-numeric: tabular-nums;
}

/* ── the label ── */
.lb-label {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.3rem 1.4rem 1.2rem;
  background: rgba(10, 9, 8, 0.85);
  border: 1px solid rgba(245, 199, 94, 0.22);
  border-radius: 14px;
  /* SoftSliders' rows, a notch denser than the Ch.3 stage */
  --ld-name-w: 9.4rem;
  --ld-row-fs: 0.98rem;
}
.lb-actions { display: flex; gap: 0.6rem; align-items: center; }
/* the two text fields — a rounded pill, like the site's other inputs */
.lb-field {
  min-width: 0;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(245, 199, 94, 0.3);
  border-radius: 999px;
  color: #f5f0e6;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.85rem;
  letter-spacing: 0.04em;
  padding: 0.42rem 1rem;
  outline: none;
  transition: border-color 0.2s, opacity 0.2s;
}
.lb-field::placeholder { color: rgba(245, 240, 230, 0.35); letter-spacing: 0.08em; }
.lb-field:focus { border-color: var(--gold); }
.lb-field:disabled { opacity: 0.5; }
.lb-notes { flex: 1 1 6rem; }
.lb-commit,
.lb-next,
.lb-skip {
  border: 1px solid var(--gold);
  background: rgba(56, 38, 12, 0.5);
  color: var(--gold-bright);
  font-family: inherit;
  font-size: 0.92rem;
  letter-spacing: 0.06em;
  padding: 0.55rem 1.25rem;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s, opacity 0.2s;
}
.lb-commit:disabled,
.lb-next:disabled,
.lb-skip:disabled { opacity: 0.4; cursor: default; }
.lb-next {
  background: var(--gold-bright);
  border-color: var(--gold-bright);
  color: #0a0a0a;
  font-weight: 600;
}
.lb-next:not(:disabled):hover { background: var(--gold); }
.lb-skip {
  border-color: rgba(245, 199, 94, 0.35);
  background: transparent;
  color: var(--gold-dim);
}
.lb-skip:not(:disabled):hover { color: var(--gold-bright); border-color: var(--gold); }
.lb-commit:not(:disabled):hover { background: rgba(86, 60, 18, 0.7); }
.lb-reset {
  border: 1px solid rgba(245, 199, 94, 0.35);
  background: transparent;
  color: var(--gold-dim);
  font-size: 1rem;
  width: 2.2rem;
  height: 2.2rem;
  border-radius: 50%;
  cursor: pointer;
}
.lb-reset:disabled { opacity: 0.35; cursor: default; }

/* the reveal */
.lb-reveal {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(245, 199, 94, 0.2);
}
.lb-callout {
  display: flex;
  align-items: baseline;
  gap: 0.45rem;
  font-size: 0.82rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(245, 240, 230, 0.6);
}
.lb-callout-split .lb-callout-k { color: var(--gold-bright); }
.lb-callout-sep,
.lb-callout-slash { color: rgba(245, 240, 230, 0.4); font-weight: 400; }
.lb-callout-code { font-size: 0.98rem; letter-spacing: 0.06em; }

.lb-rev-grid {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr) 3.4rem;
  align-items: center;
  column-gap: 0.8rem;
  row-gap: 0.42rem;
  font-size: 0.9rem;
}
.lb-rev-h {
  font-size: 0.74rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(245, 240, 230, 0.7);
}
.lb-rev-c { text-align: center; }
.lb-rev-who { color: rgba(245, 240, 230, 0.82); white-space: nowrap; }
.lb-rev-you { color: var(--gold-bright); font-weight: 600; }
.lb-rev-maj { color: rgba(245, 240, 230, 0.6); font-size: 0.82rem; letter-spacing: 0.04em; }
.lb-rev-ini { color: rgba(245, 240, 230, 0.45); font-size: 0.8rem; }
.lb-rev-bar {
  display: flex;
  height: 12px;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.06);
}
.lb-rev-bar span { display: block; height: 100%; }
.lb-rev-code { font-weight: 700; letter-spacing: 0.04em; white-space: nowrap; }
.lb-mark { font-style: normal; font-weight: 600; margin-left: 0.3em; font-size: 0.8rem; }
.lb-mark-y { color: var(--gold-bright); }
.lb-mark-n { color: rgba(245, 240, 230, 0.35); }

/* ── the tally ── */
.lb-tally {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1.1rem 1.1rem 1rem;
  background: rgba(10, 9, 8, 0.85);
  border: 1px solid rgba(245, 199, 94, 0.22);
  border-radius: 14px;
  font-size: 0.86rem;
}
.lb-t-head { display: flex; align-items: baseline; gap: 0.45rem; flex-wrap: wrap; }
.lb-t-n {
  font-family: 'EB Garamond', serif;
  font-size: 2.2rem;
  line-height: 1;
  color: var(--gold-bright);
  font-variant-numeric: tabular-nums;
}
.lb-t-unit { font-size: 0.8rem; letter-spacing: 0.12em; text-transform: uppercase; color: rgba(245, 240, 230, 0.7); }
.lb-t-sub { flex-basis: 100%; font-size: 0.8rem; letter-spacing: 0.06em; color: rgba(245, 240, 230, 0.72); }
.lb-t-legend {
  display: flex;
  gap: 0.9rem;
  flex-wrap: wrap;
  font-size: 0.8rem;
  color: rgba(245, 240, 230, 0.82);
  padding-bottom: 0.15rem;
}
.lb-t-legend span { display: inline-flex; align-items: center; gap: 0.35rem; }
.lb-key-you { display: inline-block; width: 14px; height: 8px; border-radius: 2px; background: var(--gold); }
.lb-key-ref { display: inline-block; width: 2px; height: 12px; background: #f5f0e6; }
.lb-t-sec {
  margin-top: 0.45rem;
  font-size: 0.74rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(245, 240, 230, 0.72);
}
/* label · n/N · value on one line, the bar under them */
.lb-t-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto 3rem;
  align-items: baseline;
  column-gap: 0.55rem;
  row-gap: 0.28rem;
}
.lb-t-row .lb-t-track { grid-column: 1 / -1; }
.lb-t-k { color: rgba(245, 240, 230, 0.82); white-space: nowrap; }
.lb-t-track {
  position: relative;
  height: 10px;
  border-radius: 3px;
  background: rgba(245, 240, 230, 0.08);
}
.lb-t-fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  border-radius: 3px;
  background: var(--gold);
  transition: width 0.35s ease;
}
.lb-t-mark {
  position: absolute;
  top: -3px;
  bottom: -3px;
  width: 2px;
  margin-left: -1px;
  background: #f5f0e6;
  border-radius: 1px;
  transition: left 0.35s ease;
}
.lb-t-v { text-align: right; font-variant-numeric: tabular-nums; color: var(--gold-bright); font-weight: 600; }
.lb-t-frac { text-align: right; font-variant-numeric: tabular-nums; font-size: 0.78rem; color: rgba(245, 240, 230, 0.7); }

/* SUBMIT */
.lb-submit {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-top: 0.75rem;
  padding-top: 0.8rem;
  border-top: 1px solid rgba(245, 199, 94, 0.2);
}
.lb-name { flex: 1 1 auto; width: 0; }
.lb-name[aria-invalid='true'] { border-color: rgba(232, 90, 74, 0.7); }
/* the name, once the Worker took it: text where the field was */
.lb-name-locked {
  flex: 1 1 auto;
  min-width: 0;
  padding: 0.42rem 0.15rem;
  font-size: 0.9rem;
  letter-spacing: 0.03em;
  color: var(--gold-bright);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* the site's uppercase pill (Explore .beat-btn), in the commit's gold */
.lb-submit-btn {
  flex: 0 0 auto;
  min-width: 5.8rem;
  text-align: center;
  border: 1px solid var(--gold);
  background: rgba(56, 38, 12, 0.5);
  color: var(--gold-bright);
  font-family: inherit;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.48rem 0.9rem;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.2s, opacity 0.2s;
}
.lb-submit-btn:not(:disabled):hover { background: rgba(86, 60, 18, 0.7); }
.lb-submit-btn:disabled { opacity: 0.4; cursor: default; }
.lb-submit-state {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  font-size: 0.78rem;
  line-height: 1.4;
}
.lb-submit-state:empty { display: none; }
/* the taken-name message under the field */
.lb-wrong { font-size: 0.8rem; color: rgba(232, 120, 110, 0.9); letter-spacing: 0.02em; }
.lb-submitted { color: rgba(245, 240, 230, 0.55); letter-spacing: 0.03em; font-variant-numeric: tabular-nums; }
.lb-submitted b { color: var(--gold-bright); font-weight: 600; }

/* Narrow screens: one column, the lake first. */
@media (max-width: 1100px) {
  .lb-grid { grid-template-columns: minmax(0, 1fr); }
  .lb-lake { width: min(100%, 520px); }
}
</style>
