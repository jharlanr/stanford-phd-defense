<template>
  <!-- Additional Work → "Apply the method to glaciology".
       HEADLESS for the globe (same emits as SectionCh2: this component
       owns the sim-domain block, lands it on lake 1951 exactly as Ch.2
       does — or continues Ch.2's block in place through the door) PLUS
       its own overlay UI: a guided pill row along the bottom and a
       right column for the radar panels / the summary. ONE
       linear flow (drain → under the ice → data → other interpolations
       → use this bed → viscous solution → flip beds → summary), viscous
       only (no elastic runs exist for the realizations), every drape at
       ONE ±400 kPa scale, three fields in the director's words (no patch · with
       patch · difference) each "with this bed" or "change vs published
       bed", per-bed lake tables + stress space. -->
  <div class="mg-root">
    <div v-if="landed" class="mg-dock" :class="{ 'mg-dock-narrow': columnBusy }">
      <p class="mg-hint" v-html="hint" />
      <div class="mg-row">
        <button class="mg-pill mg-pill-dim" @click="exit">
          {{ fromCh2 ? '← PNAS chapter' : '← doors' }}
        </button>

        <button
          v-if="beat === 1"
          class="mg-pill mg-pill-dim"
          title="Refill the lake (back to the pre-drainage block)"
          @click="undrain"
        >↺ refill</button>

        <!-- 1 · under the ice -->
        <button class="mg-pill" :class="{ 'mg-on': glassy }" @click="toggleGlass">
          {{ glassy ? 'Solid block' : 'See the bed topography' }}
        </button>

        <!-- 2 · what conditioned the ensemble (glass only) -->
        <button v-if="glassy" class="mg-pill" :class="{ 'mg-on': dataOpen }" @click="toggleData">
          See the data
        </button>

        <!-- 3 · the realizations: appears once "Other interpolations"
             opened the ring (or a solution is up), then stays -->
        <span v-if="navVisible" class="mg-nav">
          <button class="mg-pill mg-pill-sq" title="previous bed" @click="stepBed(-1)">◀</button>
          <span class="mg-bedname">
            <span class="mg-bedlabel">{{ bedLabel }}</span>
            <span class="mg-bedsub">{{ bedSub }}</span>
          </span>
          <button class="mg-pill mg-pill-sq" title="next bed" @click="stepBed(1)">▶</button>
        </span>

        <!-- 4 · commit the bed -->
        <button v-if="glassy && navVisible" class="mg-pill mg-pill-primary" @click="useBed">
          Use this bed
        </button>

        <!-- 5 · the solution (solid block; drains first if needed) -->
        <button
          v-if="!glassy"
          class="mg-pill"
          :class="{
            'mg-on': solutionOn,
            'mg-pill-primary': !solutionOn && bedIdx >= 0 && hasAnyResult,
            'mg-pill-wait': !hasAnyResult && !solutionOn,
          }"
          :title="hasAnyResult ? '' : 'this realization is still running on the VM'"
          @click="toggleSolution"
        >
          {{ solutionOn ? 'Hide solution' : 'Viscous solution with this bed' }}
          <span v-if="!hasAnyResult" class="mg-wait">· run in progress</span>
        </button>

        <!-- 6 · the ensemble -->
        <button
          v-if="hasSummary"
          class="mg-pill"
          :class="{ 'mg-on': summaryOpen, 'mg-pill-dim': !summaryOpen }"
          @click="toggleSummary"
        >Summary</button>
      </div>
    </div>

    <!-- ── the solution legend (top-left, right of the flow arrow) ── -->
    <div class="mg-legend" :class="{ 'mg-hidden': !(solutionOn && view) }">
      <div class="mg-leg-kicker">{{ legend.kicker }}</div>
      <div class="mg-leg-title" v-html="legend.title" />
      <div class="mg-leg-bar" />
      <div class="mg-leg-ticks">
        <span>−{{ vlimLabel }}</span><span>0</span><span>+{{ vlimLabel }} kPa</span>
      </div>
      <div class="mg-leg-stats">{{ legend.stats }}</div>
      <div class="mg-leg-toggle">
        <button
          v-for="f in FAMS" :key="f.id"
          class="mg-mini" :class="{ 'mg-on': solFam === f.id }"
          :disabled="!hasFam(f.id)"
          :title="hasFam(f.id) ? '' : 'this bed\'s patch run is still queued on the VM'"
          @click="setFam(f.id)"
        >{{ f.label }}</button>
      </div>
      <div v-if="bedIdx >= 0" class="mg-leg-toggle">
        <button class="mg-mini" :class="{ 'mg-on': !solDiff }" @click="setDiff(false)">with this bed</button>
        <button class="mg-mini" :class="{ 'mg-on': solDiff }" @click="setDiff(true)">change vs published bed</button>
      </div>
    </div>

    <!-- ── right column: the radar data ── -->
    <transition name="mg-fade">
      <aside v-if="dataOpen && meta" class="mg-data">
        <div class="mg-data-head">
          <span class="mg-data-kicker">What conditioned the ensemble</span>
          <button class="mg-x" title="close" @click="dataOpen = false">×</button>
        </div>
        <img class="mg-panel" :src="url(meta.tracks)" alt="radar bed picks over the simulation domain" />
        <img class="mg-panel" :src="diffUrl" :alt="`${bedLabel} minus radar`" />
        <div class="mg-data-foot">
          <span class="mg-data-stat">
            {{ bedLabel }} − radar: median |Δ| {{ fmt(currentDiff?.median_abs_m) }} m ·
            std {{ fmt(currentDiff?.std_m, 0) }} m · {{ (currentDiff?.n_cells ?? 0).toLocaleString() }} cells
          </span>
          <button v-if="!explored" class="mg-pill mg-pill-sm mg-pill-primary" @click="exploreOthers">
            Other interpolations →
          </button>
          <span v-else-if="bedIdx >= 0" class="mg-data-stat mg-data-dim">
            published bed: median |Δ| {{ fmt(meta.published.diff_stats.median_abs_m) }} m
            · std {{ fmt(meta.published.diff_stats.std_m, 0) }} m
          </span>
        </div>
        <p class="mg-src">{{ meta.radar_source }}</p>
      </aside>
    </transition>

    <!-- ── right column: the summary — ONE large panel at a time ── -->
    <transition name="mg-fade">
      <aside v-if="summaryOpen && meta?.summary_panels && summaryFamily" class="mg-data mg-data-summary">
        <div class="mg-data-head">
          <span class="mg-data-kicker">How much the bed matters</span>
          <button class="mg-x" title="close" @click="summaryOpen = false">×</button>
        </div>
        <div class="mg-sum-chips">
          <button
            v-for="f in FAMS" :key="f.id"
            v-show="meta.summary_panels[f.id]"
            class="mg-mini" :class="{ 'mg-on': sumFam === f.id }"
            @click="sumFam = f.id"
          >{{ f.label }} · n = {{ meta.summary_stats?.[f.id]?.n ?? 0 }}</button>
        </div>
        <div class="mg-sum-steps">
          <button
            v-for="k in SUMMARY_KINDS" :key="k.id" class="mg-step"
            :class="{ 'mg-on': sumKind === k.id }" @click="sumKind = k.id"
          >{{ k.label }}</button>
        </div>
        <img class="mg-panel mg-panel-big" :src="url(summaryFamily[sumKind])" :alt="`${sumFam} ${sumKind}`" />
        <div class="mg-sum-nav">
          <button class="mg-pill mg-pill-sq mg-pill-dim" title="previous panel" @click="stepSummary(-1)">◀</button>
          <span class="mg-data-stat">{{ summaryCaption }}</span>
          <button class="mg-pill mg-pill-sq mg-pill-dim" title="next panel" @click="stepSummary(1)">▶</button>
        </div>
        <p v-if="meta.summary_stats" class="mg-summary-text">
          <template v-if="meta.summary_stats.dsig">
            Swapping only the bed moves the difference (with patch − no patch) by
            <b>{{ fmt(meta.summary_stats.dsig.spread_kpa, 0) }} kPa</b> (mean per-pixel spread),
            RMS <b>{{ fmt(meta.summary_stats.dsig.rms_kpa, 0) }} kPa</b> against the published bed's —
            whose own p99.7 is {{ fmt(meta.published.dsig_stats?.p997_kpa, 0) }} kPa.
          </template>
          <template v-if="meta.summary_stats.nopatch">
            The no-patch field shifts by <b>{{ fmt(meta.summary_stats.nopatch.spread_kpa, 0) }} kPa</b>
            (RMS {{ fmt(meta.summary_stats.nopatch.rms_kpa, 0) }} kPa vs published).
          </template>
          The bed sets the background; the patch sets the change.
        </p>
        <p class="mg-src">
          {{ meta.method.generator }} · variogram {{ meta.method.variogram[5] }},
          range {{ (Number(meta.method.variogram[2]) * 0.15).toFixed(1) }} km, nugget {{ (Number(meta.method.variogram[1]) * 100).toFixed(0) }}% ·
          multigrid {{ meta.method.mg_resols_px.join('→') }} px · {{ meta.elmer }}
        </p>
      </aside>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch, watchEffect } from 'vue'
import { useRoute } from 'vue-router'
import { mediaUrl, corsUrl } from '../../config/media'
import type { SimDomainPayload, SimFace, SimField } from '../../config/simLakes'

const props = defineProps<{
  /** Ch.2's active face at the moment of the handoff (read once on
   *  mount when arriving through the chapter's door). */
  face?: SimFace
  /** The drain pill / Explore's advance trigger. */
  advanceTrigger?: number
}>()

/** What Explore needs to drive the shared in-canvas pieces on this page. */
export interface MgsimUiState {
  solutionOn: boolean
  phaseVisible: boolean
  phaseKey: string
  ghostKeys: string[]
  phaseLabel: string
  cardLabel: string
  columnBusy: boolean
  drained: boolean
  /** The field on screen, in Ch.2's words (for the handoff back). */
  field: SimField
}

const emit = defineEmits<{
  exit: [target: 'menu' | 'ch2']
  'beat-change': [value: number, isLast: boolean]
  'ui-state': [value: MgsimUiState]
  'globe-clicks': [value: number]
  'chapter-focus': [
    | {
        lat: number
        lon: number
        cameraLat?: number
        cameraLon?: number
        distance?: number
        fovDeg?: number
        durationMs?: number
        focalElevM?: number
        focalExag?: number
      }
    | null,
  ]
  'lake-polygons': [{ dataUrl: string; opacity?: number; featured?: boolean } | null]
  'chapter-exag': [value: number | null]
  'face-reset': []
  'sim-dates': [value: { pre: string; post: string } | null]
  'sim-domain': [SimDomainPayload | null]
}>()

const route = useRoute()

// ── the same framing constants as SectionCh2 (the block must land
// exactly where Ch.2 puts it) ──
const LAKE_ID = 'CW2019_1951'
const CH2_FOCAL = { lat: 70.1, lon: -49.3 }
const CW_CAM_LAT = 61.6
const CW_CAM_LON = -67.2
const CW_CAM_DISTANCE_MEDIUM = 0.60
const CW_CAM_FOV_MEDIUM_DEG = 13
const PAN_MS = 1800
const PNAS_LAKES_URL = mediaUrl('ch02/pnas_lakes.json')
const CH2_EXAG = 0.014
const CH2_EXAG_ZOOM = 2.747e-4 * 2
const CH2_ZOOM_DIST = 0.528
const CH2_ZOOM_FOV = 2.0
const CH2_FOCAL_LON_EAST = 0.12
const GLASS_A = 0.22

interface SimDomainMeta {
  id: string
  lon: number
  lat: number
  center_surf_m: number
  domain_half_km: number
  bbox: { lon_w: number; lon_e: number; lat_s: number; lat_n: number }
  corners_lonlat: [number, number][]
  bed_off_m: number
  bed_scale_m: number
  dem: string
  bed: string
  stress: string
  stress_viscous: string
  s2_pre: string
  s2_post: string
  date_pre: string
  date_post: string
  lakes: string
}
interface DiffStats { median_abs_m: number; std_m: number; p95_abs_m: number; n_cells: number }
interface FieldStats { std_kpa: number; p997_kpa: number; corr_pub: number; rms_pub_kpa: number }
interface BedEntry {
  id: string
  label: string
  seed?: number
  bed: string
  bed_min_m: number
  bed_max_m: number
  diff: string
  diff_stats: DiffStats
  /** σ_t1 no patch (absolute) · this bed − published. */
  stress_nopatch?: string
  stress_nopatchdiff?: string
  nopatch_stats?: FieldStats
  /** σ_t1 with patch (absolute) · this bed − published — once BOTH runs landed. */
  stress_patch?: string
  stress_patchdiff?: string
  patch_stats?: FieldStats
  /** Δσ_t1 = with patch − no patch · this bed − published. */
  stress_dsig?: string
  stress_dsigdiff?: string
  dsig_stats?: FieldStats
  /** This bed's drainage catalog (in-polygon tables) + its phase key. */
  lakes?: string
  phase_key?: string
}
interface FamilyStats {
  n: number
  spread_kpa: number
  bias_kpa: number
  rms_kpa: number
  pub_std_kpa?: number
  real_std_kpa?: number[]
  corr?: number[]
}
type Fam = 'nopatch' | 'patch' | 'dsig'
type SummaryKind = 'published' | 'mean' | 'std' | 'bias'
interface MgsimMeta {
  lake: string
  center_num: number
  published: BedEntry
  realizations: BedEntry[]
  bed_off_m: number
  bed_scale_m: number
  bed_vmin_m: number
  bed_vmax_m: number
  bed_palette: string
  vlim_kpa: number
  tracks: string
  tracks_stats: { n_picks: number; seasons: string[] }
  summary_panels: Partial<Record<Fam, Record<SummaryKind, string>>>
  summary_stats: Partial<Record<Fam, FamilyStats | null>> | null
  phase_space: string
  method: { generator: string; variogram: (number | string)[]; mg_resols_px: number[] }
  radar_source: string
  elmer: string
}

const lake = ref<SimDomainMeta | null>(null)
const meta = ref<MgsimMeta | null>(null)

// ── page state ──
const beat = ref(0)            // 0 landed (pre-drain) · 1 drained
const landed = ref(false)      // block has settled (pills appear)
const glassy = ref(false)      // "see the bed topography"
const dataOpen = ref(false)    // right column: radar panels
const explored = ref(false)    // "Other interpolations" opened the ring
const solutionOn = ref(false)  // the solution drape is up
const summaryOpen = ref(false) // right column: the summary
const bedIdx = ref(-1)         // −1 published · 0..n−1 realizations
const fromCh2 = ref(false)     // arrived through the chapter's door
const solFam = ref<Fam>('dsig')
const solDiff = ref(false)     // "change vs published bed"
const sumFam = ref<Fam>('dsig')
const sumKind = ref<SummaryKind>('published')
const FAMS: { id: Fam; label: string }[] = [
  { id: 'nopatch', label: 'no patch' },
  { id: 'patch', label: 'with patch' },
  { id: 'dsig', label: 'difference' },
]
const SUMMARY_KINDS: { id: SummaryKind; label: string }[] = [
  { id: 'published', label: 'published bed' },
  { id: 'mean', label: 'ensemble mean' },
  { id: 'std', label: 'spread' },
  { id: 'bias', label: 'mean − published' },
]
const FAM_TO_FIELD: Record<Fam, SimField> = { nopatch: 'nopatch', patch: 'patch', dsig: 'difference' }
const FIELD_TO_FAM: Record<SimField, Fam> = { nopatch: 'nopatch', patch: 'patch', difference: 'dsig' }

/** The R2 key for a page asset ('ch02/…' keys pass through). */
function url(key: string): string {
  return mediaUrl(key.includes('/') ? key : `addl/mgsim/${key}`)
}
function fmt(v: number | undefined, d = 1): string {
  return v == null || !Number.isFinite(v) ? '—' : v.toFixed(d)
}

const currentBed = computed<BedEntry | null>(() => {
  if (!meta.value) return null
  return bedIdx.value < 0 ? meta.value.published : (meta.value.realizations[bedIdx.value] ?? null)
})
const bedLabel = computed(() => currentBed.value?.label ?? '')
const bedShort = computed(() =>
  bedIdx.value < 0 ? 'published bed' : `realization ${String(bedIdx.value + 1).padStart(2, '0')}`,
)
const bedSub = computed(() => {
  const b = currentBed.value
  if (!b || !meta.value) return ''
  const n = meta.value.realizations.length
  const pos = bedIdx.value < 0 ? 'reference' : `${bedIdx.value + 1} of ${n}`
  return `${pos} · ${b.bed_min_m.toFixed(0)}…${b.bed_max_m.toFixed(0)} m`
})
const currentDiff = computed(() => currentBed.value?.diff_stats)
const diffUrl = computed(() => (currentBed.value ? url(currentBed.value.diff) : ''))
// The ring opens with "Other interpolations", and stays open — and a
// solution on the block is itself an invitation to flip beds.
const navVisible = computed(() => explored.value || bedIdx.value >= 0 || solutionOn.value)
const hasSummary = computed(() => !!meta.value?.summary_panels?.nopatch)
const vlimLabel = computed(() => (meta.value?.vlim_kpa ?? 400).toFixed(0))

// ── which result drapes the block ──
/** The drape files of one family for a bed: [with this bed, change vs published]. */
function famFiles(b: BedEntry, f: Fam): [string | undefined, string | undefined] {
  switch (f) {
    case 'nopatch': return [b.stress_nopatch, b.stress_nopatchdiff]
    case 'patch': return [b.stress_patch, b.stress_patchdiff]
    default: return [b.stress_dsig, b.stress_dsigdiff]
  }
}
function famStats(b: BedEntry, f: Fam): FieldStats | undefined {
  return f === 'nopatch' ? b.nopatch_stats : f === 'patch' ? b.patch_stats : b.dsig_stats
}
function hasFam(f: Fam): boolean {
  const b = currentBed.value
  return !!b && !!famFiles(b, f)[0]
}
const hasAnyResult = computed(() => hasFam('nopatch') || hasFam('patch') || hasFam('dsig'))
/** The family on screen: the one asked for, or "no patch" while this
 *  bed's patch run is still queued (its with-patch + difference drapes
 *  need both twins). */
const effFam = computed<Fam | null>(() =>
  hasFam(solFam.value) ? solFam.value : hasFam('nopatch') ? 'nopatch' : null,
)
const fallback = computed(() => effFam.value !== null && effFam.value !== solFam.value)
/** The drape on the block, or null while nothing has landed for this bed. */
const view = computed<{ fam: Fam; diff: boolean; file: string } | null>(() => {
  const b = currentBed.value
  const f = effFam.value
  if (!b || !f) return null
  const [abs, dif] = famFiles(b, f)
  const wantDiff = solDiff.value && bedIdx.value >= 0 && !!dif
  const file = wantDiff ? dif! : abs!
  return { fam: f, diff: wantDiff, file }
})
const altUrl = computed<string | undefined>(() => (view.value ? url(view.value.file) : undefined))
const legend = computed(() => {
  const b = currentBed.value
  const v = view.value
  if (!b || !v) return { kicker: '', title: '', stats: '' }
  const st = famStats(b, v.fam)
  const who = bedShort.value
  const rms = st ? `RMS vs published ${fmt(st.rms_pub_kpa, 0)} kPa · corr ${fmt(st.corr_pub, 2)}` : ''
  const name = v.fam === 'nopatch' ? 'σ<sub>1</sub> · no patch'
    : v.fam === 'patch' ? 'σ<sub>1</sub> · with patch'
      : 'Δσ<sub>1</sub> = with patch − no patch'
  const what = v.fam === 'nopatch' ? 'no patch' : v.fam === 'patch' ? 'with patch (R = 2.5 km free slip)' : 'difference'
  if (v.diff) {
    return {
      kicker: `Elmer/Ice · viscous · ${what} · this bed − published bed`,
      title: `${name} · change from the published bed · ${who}`,
      stats: rms,
    }
  }
  return {
    kicker: `Elmer/Ice · viscous · ${what}`,
    title: `${name} · ${who}`,
    stats: st
      ? (bedIdx.value < 0
        ? `p99.7 ${fmt(st.p997_kpa, 0)} kPa · std ${fmt(st.std_kpa, 0)} kPa`
        : `p99.7 ${fmt(st.p997_kpa, 0)} kPa · ${rms}`)
      : '',
  }
})

const summaryFamily = computed(() => meta.value?.summary_panels?.[sumFam.value] ?? null)
const summaryCaption = computed(() => {
  const m = meta.value
  const s = m?.summary_stats?.[sumFam.value]
  if (!s) return ''
  const name = sumFam.value === 'nopatch' ? 'σ₁ no patch' : sumFam.value === 'patch' ? 'σ₁ with patch' : 'Δσ₁ difference'
  switch (sumKind.value) {
    case 'published': return `${name} with the published bed · the reference`
    case 'mean': return `mean over ${s.n} beds · bias ${s.bias_kpa >= 0 ? '+' : ''}${fmt(s.bias_kpa, 0)} kPa`
    case 'std': return `per-pixel spread over ${s.n} beds · mean ${fmt(s.spread_kpa, 0)} kPa`
    default: return `ensemble mean − published · RMS ${fmt(s.rms_kpa, 0)} kPa`
  }
})
function stepSummary(dir: number): void {
  const i = SUMMARY_KINDS.findIndex((k) => k.id === sumKind.value)
  const n = SUMMARY_KINDS.length
  sumKind.value = SUMMARY_KINDS[(i + dir + n) % n].id
}

// ── the right column is one slot: data, summary, or the stress space ──
const phaseVisible = computed(
  () => beat.value === 1 && solutionOn.value && !glassy.value && !dataOpen.value &&
    !summaryOpen.value && !!currentBed.value?.phase_key,
)
const columnBusy = computed(() => dataOpen.value || summaryOpen.value || phaseVisible.value)

// ── the hint line under the dock ──
const hint = computed(() => {
  const m = meta.value
  if (!m) return ''
  const b = currentBed.value
  const v = view.value
  const nn = String(bedIdx.value + 1).padStart(2, '0')
  const vl = (m.vlim_kpa ?? 400).toFixed(0)
  if (solutionOn.value) {
    if (!v || !b) return 'this realization\'s Elmer/Ice runs are still queued on the VM · step ◀ ▶ to a bed with a result'
    if (fallback.value) return 'this bed\'s patch run has not landed yet — showing the no-patch field instead'
    const st = famStats(b, v.fam)
    if (v.diff) {
      return v.fam === 'dsig'
        ? `where this bed changed the difference (RMS ${fmt(st?.rms_pub_kpa, 0)} kPa) · amplitude and texture, not the ring`
        : `this bed's ${v.fam === 'nopatch' ? 'no-patch' : 'with-patch'} field minus the published bed's (RMS ${fmt(st?.rms_pub_kpa, 0)} kPa) · this is where the bed matters most`
    }
    switch (v.fam) {
      case 'dsig':
        return bedIdx.value < 0
          ? `difference = with patch − no patch, the published response at ±${vl} kPa (Ch.2 drapes it at ±1 MPa) · ◀ ▶ swaps the bed under the same drainage`
          : 'the same drainage on this bed · the ring of tension survives every bed — <b>change vs published bed</b> (legend) shows what the bed moved · the stress space on the right follows'
      case 'patch':
        return bedIdx.value < 0
          ? 'the surface stress with the free-slip patch under the drained lake, published bed'
          : `the with-patch field on realization ${nn} · the legend\'s chips switch fields; ◀ ▶ swaps the bed`
      default:
        return bedIdx.value < 0
          ? 'the surface stress before any patch, published bed · the background the drainage acts on'
          : `the no-patch field on realization ${nn} · this is where the bed matters most (RMS vs published ${fmt(st?.rms_pub_kpa, 0)} kPa)`
    }
  }
  if (glassy.value) {
    if (navVisible.value) return 'under the glass: ◀ ▶ flips the bed, the misfit panel follows · <b>Use this bed</b> puts it under the ice'
    if (dataOpen.value) return 'the radar picks, and how far the published bed sits from them · <b>Other interpolations</b> swaps in the MGSIM realizations'
    return 'under the ice: the published bed, hillshaded (blue below sea level → white highs) · <b>See the data</b> shows what conditioned the ensemble'
  }
  if (bedIdx.value >= 0) {
    return `the block now rests on realization ${nn} · <b>Viscous solution with this bed</b> runs the published drainage on it${beat.value === 0 ? ' (it drains the lake first)' : ''}`
  }
  return beat.value === 0
    ? 'the PNAS block for lake 1951 on its published bed · <b>Drain the lake</b> (above) for the published response, or look under the ice first'
    : 'the drained block on its published bed · <b>Viscous solution</b> drapes the published fields, or look under the ice'
})

// ─────────────────────── rAF lerp (Ch.1/Ch.2 pattern) ─────────────────
function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}
type Lerp = {
  rafId: number | null
  startT: number | null
  fromV: number
  toV: number
  current: number
  durationMs: number
}
function makeLerp(durationMs: number): Lerp {
  return { rafId: null, startT: null, fromV: 0, toV: 0, current: 0, durationMs }
}
function startLerp(L: Lerp, target: number): void {
  if (L.rafId !== null) window.cancelAnimationFrame(L.rafId)
  L.fromV = L.current
  L.toV = target
  L.startT = null
  const tick = (now: number) => {
    if (L.startT === null) L.startT = now
    const t = Math.min(1, (now - L.startT) / L.durationMs)
    L.current = L.fromV + (L.toV - L.fromV) * easeInOutCubic(t)
    emitSimDomain()
    if (t < 1) {
      L.rafId = window.requestAnimationFrame(tick)
    } else {
      L.rafId = null
      L.startT = null
    }
  }
  L.rafId = window.requestAnimationFrame(tick)
}
function cancelLerp(L: Lerp): void {
  if (L.rafId !== null) {
    window.cancelAnimationFrame(L.rafId)
    L.rafId = null
    L.startT = null
  }
}

const tileLerp = makeLerp(700)
const carveLerp = makeLerp(3800)
const s2Lerp = makeLerp(1600)
const drainLerp = makeLerp(1400)
const lakesLerp = makeLerp(900)
const stressLerp = makeLerp(1200)
const modelMixLerp = makeLerp(500)
const glassLerp = makeLerp(900)   // surfA: 1 → GLASS_A
const palLerp = makeLerp(900)     // bedPalMix: 0 → 1
const altLerp = makeLerp(700)     // altMix: 0 → 1
const ALL = [tileLerp, carveLerp, s2Lerp, drainLerp, lakesLerp, stressLerp, modelMixLerp,
  glassLerp, palLerp, altLerp]

let timers: number[] = []
function later(ms: number, fn: () => void): void {
  timers.push(window.setTimeout(fn, ms))
}
function clearAll(): void {
  for (const id of timers) window.clearTimeout(id)
  timers = []
  for (const L of ALL) cancelLerp(L)
}

function payload(): SimDomainPayload | null {
  const l = lake.value
  const m = meta.value
  if (!l || !m) return null
  const b = currentBed.value ?? m.published
  return {
    demUrl: mediaUrl(`ch02/sim/${l.dem}`),
    bedUrl: url(b.bed),
    bedOffM: m.bed_off_m,
    bedScaleM: m.bed_scale_m,
    stressUrl: mediaUrl(`ch02/sim/${l.stress}`),
    stressViscousUrl: mediaUrl(`ch02/sim/${l.stress_viscous}`),
    s2PreUrl: mediaUrl(`ch02/sim/${l.s2_pre}`),
    s2PostUrl: mediaUrl(`ch02/sim/${l.s2_post}`),
    // Per-bed in-polygon tables (viscous); beds whose patch run is
    // queued borrow the published catalog (same outlines).
    lakesUrl: url(b.lakes ?? m.published.lakes ?? `ch02/sim/${l.lakes}`),
    bbox: { lonW: l.bbox.lon_w, lonE: l.bbox.lon_e, latS: l.bbox.lat_s, latN: l.bbox.lat_n },
    centerLon: l.lon,
    centerLat: l.lat,
    halfKm: l.domain_half_km,
    corners: l.corners_lonlat,
    centerSurfM: l.center_surf_m,
    carveT: carveLerp.current,
    tileT: tileLerp.current,
    s2T: s2Lerp.current,
    drainT: drainLerp.current,
    lakesA: lakesLerp.current,
    stressT: stressLerp.current,
    modelMix: modelMixLerp.current,
    surfA: 1 - (1 - GLASS_A) * glassLerp.current,
    bedPalMix: palLerp.current,
    bedPaletteUrl: corsUrl(url(m.bed_palette)), // its own cache key (SectionCh2's note)
    bedVminM: m.bed_vmin_m,
    bedVmaxM: m.bed_vmax_m,
    stressAltUrl: altUrl.value,
    altMix: altLerp.current,
  }
}
function emitSimDomain(): void {
  const p = payload()
  if (p) emit('sim-domain', p)
}

// ── choreography ──
function zoomFocus(l: SimDomainMeta, durationMs: number): void {
  emit('chapter-focus', {
    lat: l.lat,
    lon: l.lon + CH2_FOCAL_LON_EAST,
    cameraLat: l.lat - 5.4,
    cameraLon: l.lon + CH2_FOCAL_LON_EAST,
    distance: CH2_ZOOM_DIST,
    fovDeg: CH2_ZOOM_FOV,
    durationMs,
    focalElevM: l.center_surf_m,
    focalExag: CH2_EXAG_ZOOM,
  })
}

/** Land the block.
 *  live    — Ch.2's own two-step, verbatim: the CW overview with the
 *            seven PNAS lakes, then the "Zoom in" dive with its timings.
 *  instant — a deep link: land at the zoomed state.
 *  handoff — through Ch.2's door: the block is ALREADY on screen
 *            (Explore swallowed the chapter's unmount nulls); re-emit
 *            the same framing and payload so nothing moves. */
function land(mode: 'live' | 'instant' | 'handoff'): void {
  const l = lake.value
  if (!l) return
  clearAll()
  emit('globe-clicks', 1)
  emit('lake-polygons', null)
  emit('sim-dates', { pre: l.date_pre, post: l.date_post })
  if (mode !== 'live') {
    emit('chapter-exag', CH2_EXAG_ZOOM)
    zoomFocus(l, 900)
    tileLerp.current = 1
    carveLerp.current = 1
    s2Lerp.current = 1
    if (beat.value === 1) {
      drainLerp.current = 1
      lakesLerp.current = 1
    }
    emitSimDomain()
    if (mode === 'handoff') landed.value = true
    else later(950, () => { landed.value = true })
    return
  }
  emit('chapter-exag', CH2_EXAG)
  emit('chapter-focus', {
    lat: CH2_FOCAL.lat,
    lon: CH2_FOCAL.lon,
    cameraLat: CW_CAM_LAT,
    cameraLon: CW_CAM_LON,
    distance: CW_CAM_DISTANCE_MEDIUM,
    fovDeg: CW_CAM_FOV_MEDIUM_DEG,
    durationMs: PAN_MS,
  })
  emit('lake-polygons', { dataUrl: PNAS_LAKES_URL, opacity: 1, featured: true })
  emitSimDomain() // warm build: the block's textures decode during the pan
  later(PAN_MS + 500, () => {
    emit('lake-polygons', null)
    zoomFocus(l, 5600)
    startLerp(tileLerp, 1)
    later(1200, () => startLerp(carveLerp, 1))
    later(2400, () => startLerp(s2Lerp, 1))
    later(2700, () => emit('chapter-exag', CH2_EXAG_ZOOM))
    later(5700, () => { landed.value = true })
  })
}

function drain(): void {
  if (beat.value !== 0) return
  beat.value = 1
  emit('face-reset')
  startLerp(drainLerp, 1)
  later(500, () => startLerp(lakesLerp, 1))
  emit('beat-change', 1, true)
}
function undrain(): void {
  if (beat.value !== 1) return
  beat.value = 0
  solutionOn.value = false
  startLerp(altLerp, 0)
  startLerp(drainLerp, 0)
  startLerp(lakesLerp, 0)
  startLerp(stressLerp, 0)
  emit('face-reset')
  emit('beat-change', 0, false)
}

function showDrape(): void {
  if (!view.value) return
  altLerp.current = 1 // the alt texture is the only drape on this page
  modelMixLerp.current = 1
  startLerp(stressLerp, 1)
  emitSimDomain()
}
function hideDrape(): void {
  startLerp(stressLerp, 0)
  later(1250, () => { altLerp.current = 0; emitSimDomain() })
}

function toggleGlass(): void {
  glassy.value = !glassy.value
  if (glassy.value) {
    // Looking under the ice: the drape off, bed to the hypsometric ramp.
    summaryOpen.value = false
    if (solutionOn.value) {
      solutionOn.value = false
      hideDrape()
    }
    startLerp(glassLerp, 1)
    startLerp(palLerp, 1)
  } else {
    dataOpen.value = false
    startLerp(glassLerp, 0)
    // Keep the ramp on realizations (the published bed goes back to
    // the Ch.2 bedrock look so the block reads as it did in Ch.2).
    startLerp(palLerp, bedIdx.value < 0 ? 0 : 1)
  }
}
function toggleData(): void {
  dataOpen.value = !dataOpen.value
  if (dataOpen.value) summaryOpen.value = false
}
function toggleSummary(): void {
  summaryOpen.value = !summaryOpen.value
  if (summaryOpen.value) {
    dataOpen.value = false
    if (!meta.value?.summary_panels?.[sumFam.value]) sumFam.value = 'nopatch'
  }
}
function exploreOthers(): void {
  explored.value = true
  setBed(0)
}
function useBed(): void {
  if (glassy.value) toggleGlass()
}
function setBed(i: number): void {
  const n = meta.value?.realizations.length ?? 0
  bedIdx.value = i < 0 ? -1 : ((i % n) + n) % n
  preloadAround(bedIdx.value)
  if (bedIdx.value < 0) solDiff.value = false
  if (solutionOn.value) {
    if (view.value) {
      altLerp.current = 1
      startLerp(stressLerp, 1)
    } else {
      // No Elmer result yet for this bed: the drape fades off but the
      // mode stays armed so the next bed with a result shows it.
      startLerp(stressLerp, 0)
    }
  }
  emitSimDomain()
}
function stepBed(dir: number): void {
  const n = meta.value?.realizations.length ?? 0
  // The ring is [published, r0, r1, …]: published sits at −1.
  let i = bedIdx.value + dir
  if (i < -1) i = n - 1
  else if (i >= n) i = -1
  setBed(i)
}
function toggleSolution(): void {
  if (solutionOn.value) {
    solutionOn.value = false
    hideDrape()
    return
  }
  solutionOn.value = true
  dataOpen.value = false
  emit('face-reset')
  if (beat.value === 0) {
    // The fields belong to the drained block: drain first, then drape.
    drain()
    later(900, showDrape)
  } else {
    showDrape()
  }
}
function setFam(f: Fam): void {
  solFam.value = f
  if (solutionOn.value) showDrape()
}
function setDiff(on: boolean): void {
  solDiff.value = on
  if (solutionOn.value) showDrape()
}
function exit(): void {
  emit('exit', fromCh2.value ? 'ch2' : 'menu')
}

watch(
  () => props.advanceTrigger,
  (v, old) => {
    if (v == null || v === old) return
    drain()
  },
)

// Everything Explore needs for the shared in-canvas pieces.
watchEffect(() => {
  const m = meta.value
  const b = currentBed.value
  const keys = m
    ? [m.published.phase_key ?? 'published',
       ...m.realizations.map((r) => r.phase_key).filter((k): k is string => !!k)]
    : []
  const bedName = bedIdx.value < 0 ? 'published bed' : `realization ${String(bedIdx.value + 1).padStart(2, '0')}`
  emit('ui-state', {
    solutionOn: solutionOn.value,
    phaseVisible: phaseVisible.value,
    phaseKey: b?.phase_key ?? 'published',
    ghostKeys: keys,
    phaseLabel: `viscous · ${bedName}`,
    cardLabel: b?.lakes
      ? `viscous model · ${bedName}`
      : `viscous model · published-bed tables (this bed's patch run is queued)`,
    columnBusy: columnBusy.value,
    drained: beat.value === 1,
    field: FAM_TO_FIELD[view.value?.fam ?? solFam.value],
  })
})

// Neighbouring beds + their panels decode ahead of the flip.
const warmed = new Set<string>()
function warm(key: string): void {
  if (warmed.has(key)) return
  warmed.add(key)
  const im = new Image()
  // MUST match three.js's CORS mode: a plain (non-CORS) preload poisons
  // the browser cache with a response lacking the ACAO header, and the
  // TextureLoader's anonymous request for the same URL is then refused
  // on the live site (dev's same-origin /r2/ proxy never shows it).
  im.crossOrigin = 'anonymous'
  im.src = url(key)
}
function warmJson(key: string): void {
  if (warmed.has(key)) return
  warmed.add(key)
  fetch(url(key)).catch(() => {})
}
function preloadAround(i: number): void {
  const m = meta.value
  if (!m) return
  const n = m.realizations.length
  for (const j of [i - 1, i, i + 1]) {
    const e = j < 0 ? m.published : m.realizations[((j % n) + n) % n]
    warm(e.bed)
    warm(e.diff)
    for (const k of [e.stress_nopatch, e.stress_nopatchdiff, e.stress_patch, e.stress_patchdiff,
      e.stress_dsig, e.stress_dsigdiff]) {
      if (k) warm(k)
    }
    if (e.lakes) warmJson(e.lakes)
  }
}

onMounted(async () => {
  try {
    const [rs, rm] = await Promise.all([
      fetch(mediaUrl('ch02/sim/sim_domains_v2.json')),
      fetch(mediaUrl('addl/mgsim/mgsim_meta.json')),
    ])
    if (rs.ok) {
      const j = (await rs.json()) as { lakes: SimDomainMeta[] }
      lake.value = j.lakes.find((l) => l.id === LAKE_ID) ?? null
    }
    if (rm.ok) meta.value = (await rm.json()) as MgsimMeta
  } catch {
    // The page stays blank without its metadata; nothing else to do.
  }
  if (!lake.value || !meta.value) return
  const q = route.query
  fromCh2.value = q.from === 'ch2'
  const deep = q.drained === '1' || q.bed !== undefined || q.glass === '1' || q.solution === '1'
  if (q.drained === '1') beat.value = 1
  if (typeof q.bed === 'string') {
    const i = parseInt(q.bed, 10)
    if (Number.isFinite(i)) bedIdx.value = i < 0 ? -1 : Math.min(i, meta.value.realizations.length - 1)
    if (bedIdx.value >= 0) explored.value = true
  }
  // ?fam= (this page's word) or ?field= (Ch.2's word, from the door).
  if (q.fam === 'nopatch' || q.fam === 'patch' || q.fam === 'dsig') solFam.value = q.fam
  if (q.field === 'nopatch' || q.field === 'patch' || q.field === 'difference') {
    solFam.value = FIELD_TO_FAM[q.field]
  }
  if (q.diff === '1') solDiff.value = true
  preloadAround(Math.max(0, bedIdx.value))
  if (fromCh2.value) {
    // Through the chapter's door: continue in place. A model face on
    // the drained block becomes this page's solution — the published
    // field crossfades from Ch.2's ±1 MPa drape to the page scale.
    const face = props.face
    land('handoff')
    if (beat.value === 1 && (face === 'viscous' || face === 'elastic')) {
      solutionOn.value = true
      modelMixLerp.current = face === 'elastic' ? 0 : 1
      stressLerp.current = 1
      altLerp.current = 0
      emitSimDomain()
      startLerp(altLerp, 1)
      modelMixLerp.current = 1
    }
    emit('face-reset')
  } else {
    land(deep ? 'instant' : 'live')
    if (deep) {
      if (q.glass === '1') {
        glassy.value = true
        glassLerp.current = 1
        palLerp.current = 1
      } else if (bedIdx.value >= 0) {
        palLerp.current = 1
      }
      if (q.data === '1') dataOpen.value = true
      if (q.summary === '1') summaryOpen.value = true
      if (q.solution === '1' && beat.value === 1 && !glassy.value && view.value) {
        solutionOn.value = true
        altLerp.current = 1
        modelMixLerp.current = 1
        stressLerp.current = 1
      }
      emitSimDomain()
    }
  }
  emit('beat-change', beat.value, beat.value === 1)
})

onBeforeUnmount(() => {
  clearAll()
  emit('sim-domain', null)
  emit('sim-dates', null)
  emit('chapter-focus', null)
  emit('chapter-exag', null)
  emit('globe-clicks', 1)
})
</script>

<style scoped>
.mg-root {
  position: absolute;
  inset: 0;
  pointer-events: none;
  font-family: 'Inter', system-ui, sans-serif;
  /* Above the Ch.2 pill grid (12) so the right column covers it. */
  z-index: 13;
}

/* ── bottom dock: hint over the pill row, centered between the BC
   toggle (bottom-left) and the right column ── */
.mg-dock {
  position: absolute;
  left: 250px;
  right: 250px;
  bottom: 3.2vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.55rem;
  pointer-events: none;
}
.mg-dock-narrow {
  right: max(36vw, 560px);
}

.mg-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  justify-content: center;
  pointer-events: auto;
}

.mg-hint {
  margin: 0;
  color: var(--gold-dim);
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  text-align: center;
  line-height: 1.4;
  max-width: 78ch;
}
.mg-hint :deep(b) {
  color: var(--gold-bright);
  font-weight: 500;
}

.mg-pill {
  border: 1px solid var(--gold);
  background: rgba(8, 6, 4, 0.78);
  color: var(--gold-bright);
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 500;
  letter-spacing: 0.06em;
  padding: 0.5rem 1rem;
  border-radius: 999px;
  cursor: pointer;
  pointer-events: auto;
  white-space: nowrap;
  backdrop-filter: blur(8px);
  box-shadow:
    0 6px 28px rgba(0, 0, 0, 0.55),
    0 0 22px rgba(245, 199, 94, 0.18);
  transition: color 0.2s, border-color 0.2s, background 0.2s, box-shadow 0.2s;
}
.mg-pill:hover {
  color: #fff8d8;
  background: rgba(56, 38, 12, 0.85);
}
.mg-on {
  color: #1c1305;
  background: var(--gold);
  box-shadow:
    0 6px 28px rgba(0, 0, 0, 0.55),
    0 0 30px rgba(245, 199, 94, 0.45);
}
.mg-on:hover {
  color: #1c1305;
  background: var(--gold-bright);
}
.mg-pill-primary {
  color: #1c1305;
  background: var(--gold);
  animation: mg-pulse 2.4s ease-in-out infinite;
}
.mg-pill-primary:hover {
  color: #1c1305;
  background: var(--gold-bright);
}
.mg-pill-dim {
  border-color: rgba(245, 199, 94, 0.45);
  color: var(--gold-dim);
  font-size: 0.74rem;
  padding: 0.45rem 0.8rem;
}
.mg-pill-sq {
  padding: 0.45rem 0.7rem;
}
.mg-pill-sm {
  font-size: 0.72rem;
  padding: 0.35rem 0.75rem;
}
.mg-pill-wait {
  border-style: dashed;
  color: var(--gold-dim);
}
.mg-wait {
  font-size: 0.66rem;
  opacity: 0.8;
  letter-spacing: 0.04em;
}
@keyframes mg-pulse {
  0%, 100% { box-shadow: 0 6px 28px rgba(0,0,0,0.55), 0 0 22px rgba(245,199,94,0.18); }
  50%      { box-shadow: 0 6px 28px rgba(0,0,0,0.55), 0 0 36px rgba(245,199,94,0.42); }
}

.mg-nav {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
.mg-bedname {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  min-width: 11rem;
  line-height: 1.1;
}
.mg-bedlabel {
  color: var(--gold-bright);
  font-size: 0.82rem;
  font-weight: 500;
  letter-spacing: 0.05em;
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.9);
}
.mg-bedsub {
  color: var(--gold-dim);
  font-size: 0.64rem;
  letter-spacing: 0.06em;
  font-variant-numeric: tabular-nums;
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.9);
}

/* ── the solution legend (mirrors BlisterStressLegend) ── */
.mg-legend {
  position: absolute;
  top: 7vh;
  /* Right of the flow arrow (which hovers off the block's far corner,
     top-left of the frame) and left of the top-center lake card. */
  left: 18vw;
  width: 340px;
  padding: 0.8rem 1rem 0.7rem;
  background: rgba(8, 6, 4, 0.72);
  border: 1px solid var(--gold-faint);
  border-radius: 10px;
  backdrop-filter: blur(6px);
  pointer-events: auto;
  transition: opacity 0.6s;
}
.mg-hidden {
  opacity: 0;
  pointer-events: none;
}
.mg-leg-kicker {
  font-size: 0.62rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--gold-dim);
}
.mg-leg-title {
  font-family: 'EB Garamond', serif;
  font-size: 1.05rem;
  color: var(--gold);
  margin: 0.15rem 0 0.5rem;
}
.mg-leg-bar {
  height: 10px;
  border-radius: 3px;
  background: linear-gradient(to right, #00007f, #0000ff, #ffffff, #ff0000, #7f0000);
}
.mg-leg-ticks {
  display: flex;
  justify-content: space-between;
  font-size: 0.66rem;
  color: #d8d4cc;
  margin-top: 0.25rem;
  font-variant-numeric: tabular-nums;
}
.mg-leg-stats {
  margin-top: 0.35rem;
  font-size: 0.64rem;
  letter-spacing: 0.03em;
  color: #b8b3aa;
  font-variant-numeric: tabular-nums;
  min-height: 0.9rem;
}
.mg-leg-toggle {
  display: flex;
  gap: 0.35rem;
  margin-top: 0.45rem;
  flex-wrap: wrap;
}
.mg-mini {
  border: 1px solid rgba(245, 199, 94, 0.45);
  background: transparent;
  color: var(--gold-dim);
  font-family: inherit;
  font-size: 0.66rem;
  letter-spacing: 0.05em;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  cursor: pointer;
  pointer-events: auto;
}
.mg-mini:disabled {
  opacity: 0.4;
  cursor: default;
}
.mg-mini.mg-on {
  color: #1c1305;
  background: var(--gold);
  border-color: var(--gold);
}

/* ── right column (data · summary; the stress space shares the slot) ── */
.mg-data {
  position: absolute;
  right: 1.2vw;
  top: max(106px, calc(6.2vh + 42px));
  bottom: calc(3.2vh + 6.6rem);
  width: min(34vw, 540px);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 0.6rem 0.7rem 0.55rem;
  background: rgba(8, 6, 4, 0.8);
  border: 1px solid var(--gold-faint);
  border-radius: 12px;
  backdrop-filter: blur(8px);
  pointer-events: auto;
  overflow: hidden;
}
.mg-data-summary {
  bottom: 2vh;
}
.mg-data-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.mg-data-kicker {
  font-size: 0.64rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--gold-dim);
}
.mg-x {
  background: transparent;
  border: none;
  color: var(--gold-dim);
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
  padding: 0 0.2rem;
}
.mg-x:hover {
  color: var(--gold-bright);
}
.mg-panel {
  width: 100%;
  flex: 1 1 0;
  min-height: 0;
  object-fit: contain;
  border-radius: 6px;
  background: #0a0908;
}
.mg-panel-big {
  flex: 1 1 0;
}
.mg-data-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.mg-data-stat {
  font-size: 0.68rem;
  color: #d8d4cc;
  font-variant-numeric: tabular-nums;
}
.mg-data-dim {
  color: #9a948a;
}
.mg-src {
  margin: 0;
  font-size: 0.6rem;
  line-height: 1.35;
  color: #7f7a72;
}

/* ── summary controls ── */
.mg-sum-chips {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
}
.mg-sum-steps {
  display: flex;
  gap: 0.25rem;
  border-bottom: 1px solid rgba(245, 199, 94, 0.18);
  padding-bottom: 0.3rem;
}
.mg-step {
  flex: 1 1 0;
  border: none;
  background: transparent;
  color: var(--gold-dim);
  font-family: inherit;
  font-size: 0.66rem;
  letter-spacing: 0.05em;
  padding: 0.25rem 0.2rem;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
}
.mg-step:hover {
  color: var(--gold-bright);
}
.mg-step.mg-on {
  color: #1c1305;
  background: var(--gold);
}
.mg-sum-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.mg-summary-text {
  margin: 0;
  font-size: 0.72rem;
  line-height: 1.45;
  color: #e8e4dc;
}
.mg-summary-text b {
  color: var(--gold-bright);
  font-weight: 500;
}

.mg-fade-enter-active,
.mg-fade-leave-active {
  transition: opacity 0.35s;
}
.mg-fade-enter-from,
.mg-fade-leave-to {
  opacity: 0;
}
</style>
