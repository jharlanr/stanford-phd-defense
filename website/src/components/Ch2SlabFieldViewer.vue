<template>
  <!-- The idealized slab's every field (the director asked for a 'more
       fields' door that takes the visitor to the Chapter 2 deeper dive,
       where any field of the simulation, the analytical solution and
       their difference can be viewed): the
       sweep's runs on the talk's four sliders, every field of the manifest
       × Simulation (depth-averaged) | Theory | Difference | Difference ×10,
       one big panel. Opens on the run + field the talk last showed
       (config/ch2Slab.ts slabState). Plain <img> loads (the WebGL beats use
       their own cors=1 cache entry). -->
  <div class="sv">
    <div v-if="!man" class="sv-wait">…</div>
    <template v-else>
      <div class="sv-controls">
        <div v-for="p in SLAB_PARAMS" :key="p.key" class="sv-sl">
          <span class="sv-sym">{{ p.sym }}</span>
          <input
            type="range"
            min="0"
            :max="stopsOf(p.key).length - 1"
            step="1"
            :value="idxOf(p.key)"
            :class="{ 'sv-binary': stopsOf(p.key).length === 2 }"
            :aria-label="p.sym"
            @input="onSlide(p.key, $event)"
          />
          <span class="sv-val">{{ p.fmt(run ? run[p.key] : 0) + (p.unit === '°' ? '°' : p.unit ? ' ' + p.unit : '') }}</span>
        </div>
      </div>

      <div class="sv-body">
        <div class="sv-pick">
          <div class="sv-head">
            <span />
            <span v-for="c in COLS" :key="c.id">{{ c.short }}</span>
          </div>
          <div v-for="f in man.fields_all" :key="f" class="sv-row">
            <span class="sv-row-label" v-html="SLAB_FIELD_HTML[f] ?? f" />
            <button
              v-for="c in COLS"
              :key="c.id"
              class="sv-cell"
              :class="{ 'sv-cell--on': f === field && c.id === col }"
              :aria-label="`${f} ${c.title}`"
              @click="pick(f, c.id)"
            >
              <img v-if="srcOf(f, c.id)" :src="srcOf(f, c.id)!" alt="" draggable="false" loading="lazy" decoding="async" />
            </button>
          </div>
        </div>

        <div class="sv-paper">
          <div class="sv-title">
            <span class="sv-title-col">{{ colDef.title }}</span>
            <img :src="slabEqUrl('fb_' + field)" :style="eqStyle('fb_' + field, 2.6)" alt="" />
          </div>
          <div class="sv-plot">
            <div class="sv-ylab">y [km]</div>
            <div class="sv-img">
              <img v-if="srcOf(field, col)" :src="srcOf(field, col)!" alt="" draggable="false" />
              <svg class="sv-over" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                <ellipse
                  v-if="run"
                  :cx="cxPct" :cy="cyPct" :rx="rxPct" :ry="ryPct"
                  class="sv-patch"
                  vector-effect="non-scaling-stroke"
                />
              </svg>
              <div class="sv-xt">
                <span v-for="t in ticks" :key="'x' + t">{{ t }}</span>
              </div>
              <div class="sv-yt">
                <span v-for="t in [...ticks].reverse()" :key="'y' + t">{{ t }}</span>
              </div>
            </div>
            <div class="sv-xlab">x [km]</div>
          </div>
          <div class="sv-cbar">
            <div class="sv-cbar-bar" />
            <div class="sv-cbar-ticks">
              <span>−{{ lim }}</span><span>0</span><span>{{ lim }} kPa</span>
            </div>
          </div>
          <div class="sv-max">max {{ maxText }}</div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, shallowRef } from 'vue'
import { CH2_SLAB_EQ } from '../config/ch2SlabEqs'
import {
  SLAB_FIELD_HTML,
  SLAB_PARAMS,
  findSlabRun,
  fmtKpa,
  loadSlabManifest,
  slabEqUrl,
  slabRasterUrl,
  slabState,
  type SlabManifest,
  type SlabParam,
} from '../config/ch2Slab'

type Col = 'da' | 'theory' | 'diff' | 'diff_zoom'
const COLS: { id: Col; short: string; title: string }[] = [
  { id: 'da', short: 'Simulation', title: 'Simulation' },
  { id: 'theory', short: 'Theory', title: 'Theory' },
  { id: 'diff', short: 'Difference', title: 'Simulation − Theory' },
  { id: 'diff_zoom', short: '×10', title: 'Simulation − Theory · ×10' },
]

const man = shallowRef<SlabManifest | null>(null)
onMounted(async () => {
  const m = await loadSlabManifest()
  if (!m) return
  if (!m.runs[slabState.run]) slabState.run = m.hero
  man.value = m
})
const run = computed(() => man.value?.runs[slabState.run] ?? null)
const field = computed(() => slabState.field)
const col = shallowRef<Col>('da')
function pick(f: string, c: Col): void {
  slabState.field = f
  col.value = c
}
const colDef = computed(() => COLS.find((c) => c.id === col.value)!)

function srcOf(f: string, c: Col): string | null {
  const r = run.value
  if (!r) return null
  const path = c === 'diff_zoom' ? r.diff_zoom?.[f] : r[c][f]
  return path ? slabRasterUrl(path, false) : null
}
const lim = computed(() => {
  const v = run.value?.vlim_kpa[field.value] ?? 0
  const x = col.value === 'diff_zoom' ? v / 10 : v
  return String(Math.round(x * 100) / 100)
})
const maxText = computed(() => {
  const r = run.value
  if (!r) return ''
  const f = field.value
  const v = col.value === 'da' ? r.max_kpa.sim_da[f] : col.value === 'theory' ? r.max_kpa.theory[f] : r.max_kpa.diff_abs[f]
  return v === undefined ? '—' : fmtKpa(v)
})

// the axes + the patch, from the run's own domain
const ticks = computed(() => {
  const d = run.value?.domain_km ?? [-50, 50, -50, 50]
  const lo = Math.ceil(d[0] / 25) * 25
  const out: number[] = []
  for (let t = lo; t <= d[1] + 1e-6; t += 25) out.push(t)
  return out
})
const cxPct = computed(() => {
  const d = run.value!.domain_km
  return ((0 - d[0]) / (d[1] - d[0])) * 100
})
const cyPct = computed(() => {
  const d = run.value!.domain_km
  return ((d[3] - 0) / (d[3] - d[2])) * 100
})
const rxPct = computed(() => {
  const d = run.value!.domain_km
  return (run.value!.patch_km / (d[1] - d[0])) * 100
})
const ryPct = computed(() => {
  const d = run.value!.domain_km
  return (run.value!.patch_km / (d[3] - d[2])) * 100
})

function stopsOf(k: SlabParam): number[] {
  const p = man.value?.params
  if (!p) return [0]
  return k === 'H' ? p.H : k === 'alpha_deg' ? p.alpha_deg : k === 'gamma' ? p.gamma : p.R
}
function idxOf(k: SlabParam): number {
  const s = stopsOf(k)
  const v = run.value ? run.value[k] : 0
  let j = 0
  for (let i = 0; i < s.length; i++) if (Math.abs(s[i] - v) < Math.abs(s[j] - v)) j = i
  return j
}
function onSlide(k: SlabParam, e: Event): void {
  const m = man.value
  const r = run.value
  if (!m || !r) return
  const want = { H: r.H, alpha_deg: r.alpha_deg, gamma: r.gamma, R: r.R }
  want[k] = stopsOf(k)[parseInt((e.target as HTMLInputElement).value, 10)]
  const id = findSlabRun(m, want, k)
  if (id) slabState.run = id
  ;(e.target as HTMLInputElement).value = String(idxOf(k))
}
function eqStyle(name: string, k: number): Record<string, string> {
  const b = CH2_SLAB_EQ[name]
  return b ? { width: `${b.w * k}px`, height: `${b.h * k}px` } : { display: 'none' }
}
</script>

<style scoped>
.sv {
  --sv-thumb: 58px;
  width: 100%;
  color: #ececec;
  font-family: 'Inter', system-ui, sans-serif;
}
.sv-wait { min-height: 200px; }
.sv-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem 2.2rem;
  margin-bottom: 1.2rem;
}
.sv-sl {
  display: grid;
  grid-template-columns: 1.5rem 120px auto;
  align-items: center;
  gap: 0.7rem;
}
.sv-sym {
  font-family: 'EB Garamond', Georgia, serif;
  font-style: italic;
  font-size: 1.5rem;
  line-height: 1;
  color: var(--gold-bright);
  text-align: right;
}
.sv-val {
  font-size: 1.1rem;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.sv-sl input[type='range'] {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  margin: 0;
  border-radius: 3px;
  background: rgba(245, 199, 94, 0.42);
  cursor: pointer;
}
.sv-sl input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #f5c75e;
  border: 1px solid rgba(0, 0, 0, 0.55);
}
.sv-sl input[type='range']::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #f5c75e;
  border: 1px solid rgba(0, 0, 0, 0.55);
}
.sv-sl input[type='range'].sv-binary { width: 60px; }

.sv-body {
  display: flex;
  gap: 2rem;
  align-items: flex-start;
}
.sv-pick {
  flex: none;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.sv-head,
.sv-row {
  display: grid;
  grid-template-columns: 3.6rem repeat(4, var(--sv-thumb));
  gap: 4px;
  align-items: center;
}
.sv-head span {
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  color: var(--gold);
  text-align: center;
  white-space: nowrap;
}
.sv-row-label {
  font-family: 'EB Garamond', serif;
  font-size: 1.3rem;
  color: #f5f0e6;
  text-align: right;
  padding-right: 0.4rem;
}
.sv-row-label :deep(sub) { font-size: 0.68em; }
.sv-cell {
  width: var(--sv-thumb);
  height: var(--sv-thumb);
  padding: 0;
  border: 1.5px solid rgba(245, 199, 94, 0.25);
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  overflow: hidden;
}
.sv-cell img { width: 100%; height: 100%; object-fit: cover; display: block; }
.sv-cell:hover { border-color: rgba(245, 199, 94, 0.7); }
.sv-cell--on { border: 2.5px solid var(--gold); box-shadow: 0 0 12px rgba(245, 199, 94, 0.5); }

.sv-paper {
  flex: 1;
  min-width: 0;
  max-width: min(560px, 54vh);
  display: flex;
  flex-direction: column;
  align-items: center;
}
.sv-title {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin-bottom: 0.6rem;
}
.sv-title-col {
  font-family: 'EB Garamond', serif;
  font-size: 1.6rem;
  color: var(--gold-bright);
}
.sv-plot {
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: 1fr auto;
  width: 100%;
  column-gap: 2.6rem;
}
.sv-ylab {
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  align-self: center;
  font-size: 1rem;
}
.sv-img {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  margin-bottom: 1.8rem;
}
.sv-img > img {
  width: 100%;
  height: 100%;
  display: block;
  border: 1px solid rgba(245, 199, 94, 0.6);
}
.sv-over {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.sv-patch {
  fill: none;
  stroke: #0a0a0a;
  stroke-width: 2.4;
  stroke-dasharray: 6 4;
}
.sv-xt {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(100% + 0.3rem);
  display: flex;
  justify-content: space-between;
  font-size: 0.95rem;
  font-variant-numeric: tabular-nums;
}
.sv-yt {
  position: absolute;
  top: 0;
  bottom: 0;
  right: calc(100% + 0.4rem);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-end;
  font-size: 0.95rem;
  font-variant-numeric: tabular-nums;
}
.sv-xt span,
.sv-yt span { line-height: 1; }
.sv-xlab {
  grid-column: 2;
  text-align: center;
  font-size: 1rem;
}
.sv-cbar { width: 70%; margin-top: 1rem; }
.sv-cbar-bar {
  height: 14px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 3px;
  background: linear-gradient(to right, #00004c, #0000ff 25%, #ffffff 50%, #ff0000 75%, #800000);
}
.sv-cbar-ticks {
  display: flex;
  justify-content: space-between;
  margin-top: 0.25rem;
  font-size: 1rem;
  font-variant-numeric: tabular-nums;
}
.sv-max {
  margin-top: 0.5rem;
  font-size: 1.05rem;
}
@media (max-width: 1100px) {
  .sv-body { flex-direction: column; }
}
</style>
