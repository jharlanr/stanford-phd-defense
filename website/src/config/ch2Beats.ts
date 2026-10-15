// Chapter 2's beats — the ONE place their order and count live (the
// pattern of introSteps.ts and ch3Beats.ts). SectionCh2 drives them;
// `?beat=N` deep-links to beat N; anything that names a Chapter 2 beat
// (the sub-menu's landmarks, config/landmarks.ts) uses CH2_BEAT.<id>.
//
// THE PATH (the director's ordering: the story is cleaner when the talk
// first looks at the initial elastic response, then considers what the
// viscous response would look like at longer timescales):
//
//   0 lakes             the seven PNAS center lakes at Ch.1's opening
//                       vantage; NEXT first opens Lake 2394's popup (or
//                       the clicked lake's)
//   1 outline           the simulation domain DRAWN onto the greenland
//                       object like a marker stroke (the centre lake's
//                       green polygon still there) — the director's image:
//                       outline it with a marker before cutting it with a knife
//   2 pre               THE ORIGINAL ZOOM, untouched; the green
//                       polygon rides the dive and fades at the landing as
//                       the Sentinel-2 face + the lake numbers fade in;
//                       lands on PRE DRAINAGE · IMAGERY
//   3 post              POST DRAINAGE · IMAGERY
//  ── THE RESULTS, IN TIME (the director asked that the simulation results
//     step through in time order: pre-drainage imagery, post-drainage
//     imagery, pre-drainage viscous, post-drainage elastic
//     (pre-viscous + elastic perturbation), elastic perturbation,
//     post-drainage viscous, viscous perturbation — with the x-axis of the
//     elastic stress space plot changed to the approximation pre-patch
//     viscous plus elastic perturbation. The elastic solves' absolute fields
//     mean nothing (an elastic body loaded by gravity from an unstressed
//     state); only their difference Δσ^E does, so the post-drainage
//     elastic state is σ^V_pre + Δσ^E, tensors added, then principals) ──
//   4 pre-viscous-t1    PRE DRAINAGE · VISCOUS σ_t1 (the no-patch run, the
//                       shared background) · the stress space BLANK, no axis
//                       lit — nothing has happened yet
//   5 post-viscous-t1   POST DRAINAGE · VISCOUS σ_t1 (x emphasised)
//   6 diff-viscous-t1   DIFFERENCE · VISCOUS Δσ_t1 (y emphasised)
//     (4–6: only THIS center lake's symbols — the population comes later.)
//     [THE ELASTIC MODEL IS OFF THE TALK (the director limited Chapter 2
//     to the viscous model — the elastic model was too much to fit into
//     the talk; the sequence stays the same minus the POST DRAIN ELASTIC
//     and DIFFERENCE ELASTIC beats, and the full sequence with the elastic
//     results became a section of the deeper dive): the two beats that sat
//     between 4 and 5 —
//     post-elastic-t1, POST DRAINAGE · ELASTIC σ_t1 = σ_t1(σ^V_pre + Δσ^E)
//     (the `stress_s_post` drape), and diff-elastic-t1, DIFFERENCE ·
//     ELASTIC Δσ_t1 — are gone from CH2_BEAT_IDS and nothing else: their
//     PHASES and steps stay below (the stations and the sub-menu follow the
//     beat list), and the Chapter 2 deeper dive's first group
//     (/additional-work/deeper/chapter2#sequence, Ch2SequenceViewer.vue)
//     walks all five results stations for any lake, elastic beats
//     included, with the elastic | viscous population beside it
//     (Ch2PopulationSpaces.vue — the population page as it was).]
//     [σ_t2 is NOT on the walk (the director moved the σ_t2 material from
//     the chapter to the additional work) — the two DIFFERENCE · Δσ_t2
//     beats that followed each
//     model's Δσ_t1 are gone. Its home is the Chapter 2 deeper dive
//     (/additional-work/deeper/chapter2): the field viewer's σ_t2 row
//     with its Difference column, every lake and both models (#fields),
//     and the thesis's two stress spaces, which plot Δσ_t2 (#stress-
//     spaces). The block and stress-space components still take
//     `comp: 't2'`; no beat asks for it.]
//  ── THE SECOND CENTER LAKE (1951; 2394 when the visitor zoomed 1951
//     first) — a HOP from the first lake's block, no LAKES view (the
//     director's rule: never return to the LAKES view between the two
//     center-lake examples; just hop to the next one — the audience
//     catches on because the lake number differs and the mini map shows
//     it): the block dips to black and comes back up as
//     the second lake's, landed on PRE · IMAGERY — no pan, no stroke, no
//     dive (SectionCh2 `hop`) ──
//   7 pre/2             PRE DRAINAGE · IMAGERY of the second lake
//   8 post/2
//   9 diff-viscous-t1/2 DIFFERENCE · VISCOUS Δσ_t1 (y emphasised)
//  10 bed/2             the block glassy over the bed (the MGSIM ramp),
//                       Lake 1938 lit
//  11 teaser/2          the bed view on the LEFT, a twin block on the RIGHT
//                       painted viscous Δσ_t1; both cycle every 3 s
//                       through BedMachine + the ten MGSIM bed
//                       realisations, in step; the bed door shows ONLY here
//  ── THE POPULATION (the director preferred the two stress-state plots
//     right after center lake 1951, then the theory, then the
//     implications) ──
//  12 population        the σ_t1 stress space of ALL seven lakes — viscous
//                       only (elastic | viscous before; that
//                       pair is the deeper dive's #sequence now) + the DIVE
//                       DEEPER door to it — the teaser's block dissolves into
//                       it (Ch2Results' flat page)
//  ── THE THEORY: the 1D/2D reduced-order model against 3D Stokes (the
//     director wanted some of the 2D Elmer simulations shown against the
//     2D analytical theory, to show that the 1D reduced-order model is
//     relevant and captures much of the structure of the more complicated
//     system) — the idealized periodic slab of the PNAS SI's
//     validation (Elmer/Ice, Newtonian, linear Weertman, a free-slip patch
//     of radius R), Ch2Slab.vue over the globe (paused under it); data
//     config/ch2Slab.ts (R2 ch02/slab_v2/ — the deeper dive's viewer
//     keeps ch02/slab_v1/) ──
//  13 slab              the population page gives way to the IDEALIZED
//                       block (a short dip, THE HOP's 220 ms veil, under
//                       the page's 0.7 s fade), its surface painted
//                       with the simulation's SURFACE field (σ_t1 | τ_rr |
//                       τ_xx), the free-slip patch dashed; the sweep's four
//                       sliders (H · α · γ · R), BOUNDARY CONDITIONS (the
//                       periodic walls), DEPTH AVERAGE (= NEXT). BACK =
//                       the population page dissolves back in above it
//  14 slab-da           THE DEPTH AVERAGE: the walls collapse to a sheet
//                       (5.2 s) and the top's paint IS the in-progress
//                       depth average — the cumulative average from the
//                       surface down to d = t·H (no wipe line, at the
//                       director's request) — a 2 s pause,
//                       the camera to nadir, the sheet slides left, Theory
//                       rises in the middle, Simulation − Theory right.
//                       A TRANSIT beat: when the animation lands it moves
//                       on to slab-compare by itself (NEXT mid-way lands it
//                       at once)
//  15 slab-compare      the settled three panels, sliders + field toggle
//                       live; ADDITIONAL WORK · MORE FIELDS →
//                       /additional-work/deeper/chapter2#slab-fields.
//                       BACK reverses to the landed block (slab); NEXT =
//                       the three panels dissolve into the implications
//                       page (BACK from it settles the panels at once)
//  ── THE IMPLICATIONS ──
//  16 implications      the chapter on one page: the FIRST lake's viscous
//                       Δσ_t1 surface field (left) and the seven lakes'
//                       viscous stress space (right) — the director's
//                       layout: Lake 2394's surface stress on the left,
//                       the full summary stress-space plot on the right
//                       (elastic | viscous panels before)
//  17 takeaway          the same page dimmed, its takeaway line popped
//                       into a centred card (the director's rule for every
//                       chapter: on the final NEXT everything fades into
//                       the background and the chapter's main takeaway is
//                       highlighted; Explore's TakeawayPop) — NEXT from
//                       it = Chapter 3
//
// Each beat has a PHASE — its id without the `/2` (ch2Phase) — and the
// code that styles a beat asks for the phase (`ch2Phase(b) ===
// CH2_PHASE.pre`) or a helper below, never a beat number.
export const CH2_BEAT_IDS = [
  'lakes',
  'outline',
  'pre',
  'post',
  'pre-viscous-t1',
  'post-viscous-t1',
  'diff-viscous-t1',
  'pre/2',
  'post/2',
  'diff-viscous-t1/2',
  'bed/2',
  'teaser/2',
  'population',
  'slab',
  'slab-da',
  'slab-compare',
  'implications',
  'takeaway',
] as const
export type Ch2BeatId = (typeof CH2_BEAT_IDS)[number]

export const CH2_BEAT = Object.fromEntries(CH2_BEAT_IDS.map((id, i) => [id, i])) as Record<Ch2BeatId, number>
export const CH2_BEATS = CH2_BEAT_IDS.length

/** The phases in walk order. A phase's index orders it (`>=` comparisons
 *  read "at or after"): the block beats run `pre` … `teaser`, the results
 *  (one stress space beside the block) `post-elastic-t1` … `diff-viscous-t1`,
 *  then the population's flat page, the idealized slab (`slab` …
 *  `slab-compare`), and the implications' flat page. Ranges (`>=`, `<=`)
 *  are only safe WITHIN one run of neighbours — the two flat pages are not
 *  neighbours (ch2IsFlatPage names them). */
export const CH2_PHASE_IDS = [
  'lakes',
  'outline',
  'pre',
  'post',
  'pre-viscous-t1',
  'post-elastic-t1',
  'diff-elastic-t1',
  'post-viscous-t1',
  'diff-viscous-t1',
  'bed',
  'teaser',
  'population',
  'slab',
  'slab-da',
  'slab-compare',
  'implications',
] as const
export type Ch2PhaseId = (typeof CH2_PHASE_IDS)[number]
export const CH2_PHASE = Object.fromEntries(CH2_PHASE_IDS.map((id, i) => [id, i])) as Record<Ch2PhaseId, number>

/** A beat's phase index (−1 for an out-of-range beat, e.g. "none yet").
 *  The `takeaway` beat IS the implications page (dimmed under its popped
 *  takeaway) — its phase is `implications`, so everything that styles
 *  the page treats both beats alike; ch2IsTakeaway tells them apart. */
export function ch2Phase(beat: number): number {
  const id = CH2_BEAT_IDS[beat]
  if (!id) return -1
  if (id === 'takeaway') return CH2_PHASE.implications
  return CH2_PHASE[id.replace(/\/2$/, '') as Ch2PhaseId]
}
/** The chapter's last beat: the implications page with its takeaway
 *  popped (TakeawayPop in Explore). */
export function ch2IsTakeaway(beat: number): boolean {
  return CH2_BEAT_IDS[beat] === 'takeaway'
}

/** First results PHASE (the single stress spaces beside the block). */
export const CH2_RESULTS_FIRST = CH2_PHASE['pre-viscous-t1']
/** True on the single-stress-space beats (4–6, 9) — and on the two
 *  elastic phases the talk no longer visits (the deeper dive's walk). */
export function ch2IsResultsPhase(ph: number): boolean {
  return ph >= CH2_RESULTS_FIRST && ph <= CH2_PHASE['diff-viscous-t1']
}
/** True on the imagery beats — the block with its PRE / POST / DIFFERENCE
 *  tiers, free to explore (the old landed + drained beats). */
export function ch2IsImageryPhase(ph: number): boolean {
  return ph === CH2_PHASE.pre || ph === CH2_PHASE.post
}
/** True on the idealized-slab beats (Ch2Slab.vue owns the screen). */
export function ch2IsSlabPhase(ph: number): boolean {
  return ph >= CH2_PHASE.slab && ph <= CH2_PHASE['slab-compare']
}

/** True while the simulation-domain block is the scene (pre … teaser). */
export function ch2IsBlockPhase(ph: number): boolean {
  return ph >= CH2_PHASE.pre && ph <= CH2_PHASE.teaser
}

/** The second pass's first beat (the hop lands here). */
export const CH2_SECOND_FIRST = CH2_BEAT['pre/2']

/** Which center lake a beat's FIGURES are about: 1 on the `/2` beats
 *  (the second lake), 0 elsewhere (the first lake — also the population
 *  page's lit lake and the implications figure). */
export function ch2FigurePass(beat: number): 0 | 1 {
  return CH2_BEAT_IDS[beat]?.endsWith('/2') ? 1 : 0
}
/** Which center lake the BLOCK under a beat belongs to: the second lake
 *  from `pre/2` on (the flat pages after it keep the last block). */
export function ch2BlockPass(beat: number): 0 | 1 {
  return beat >= CH2_SECOND_FIRST ? 1 : 0
}

/** The second pass's lake: 1951 (the bed-topography case) unless the
 *  visitor zoomed 1951 first — then the chapter's default, 2394. */
export const CH2_SECOND_LAKE = 'CW2019_1951'
export function ch2SecondDefault(firstLake: string, fallback: string): string {
  return firstLake === CH2_SECOND_LAKE ? fallback : CH2_SECOND_LAKE
}

/** The bed beat's colour range [m] per lake: its bed's 1st–99th
 *  percentile rounded out to 50 m (ch02/sim/simbed_<id>_rg16.png), so the
 *  lows read blue — over the MGSIM page's −300…600 m the whole of 1951's
 *  bed (≈ 20–360 m) sat in one green. Others fall back to that range. */
export const CH2_BED_RANGE_M: Record<string, [number, number]> = {
  CW2019_1951: [0, 400],
  CW2019_2394: [-250, 500],
}
export function ch2BedRange(lakeId: string): [number, number] {
  return CH2_BED_RANGE_M[lakeId] ?? [-300, 600]
}
/** The neighbour the bed beat lights: Lake 1938, 6 km upstream of 1951
 *  over a deep bedrock trough, held compressive through the drainage (PNAS
 *  main text; thesis Ch. 2) — and 2309, 2394's neighbour over a bedrock
 *  high, when 2394 is the second lake. */
export const CH2_BED_NEIGHBOUR: Record<string, number> = { CW2019_1951: 1938, CW2019_2394: 2309 }

export type Ch2Model = 'elastic' | 'viscous'
export type Ch2Comp = 't1' | 't2'

/** `pre` = the viscous no-patch run (the shared pre-drainage state),
 *  `post` = after drainage (viscous: the with-patch run; elastic: the
 *  superposed σ^V_pre + Δσ^E), `diff` = the perturbation Δσ. */
export type Ch2Field = 'pre' | 'post' | 'diff'

/** The single-stress-space beats (4–6, 9; the elastic phases: the deeper
 *  dive's #sequence): which model paints the block,
 *  which principal the diagram plots (σ_t1 on every beat of the walk —
 *  see THE PATH), whether the block wears the POST-drainage
 *  field (σ_t1 of the with-patch run) or the DIFFERENCE (Δσ), and which
 *  axis of the stress space is emphasised (x = the post-drainage
 *  principal, y = its perturbation). Null on every other beat. */
export interface Ch2Step {
  model: Ch2Model
  comp: Ch2Comp
  field: Ch2Field
  emphasis: 'x' | 'y' | null
}
const CH2_STEPS: Partial<Record<Ch2PhaseId, Ch2Step>> = {
  'pre-viscous-t1': { model: 'viscous', comp: 't1', field: 'pre', emphasis: null }, // a blank plot, no axis lit (the director: no axis should glow on the PRE DRAINAGE VISCOUS beat)
  'post-elastic-t1': { model: 'elastic', comp: 't1', field: 'post', emphasis: 'x' },
  'diff-elastic-t1': { model: 'elastic', comp: 't1', field: 'diff', emphasis: 'y' },
  'post-viscous-t1': { model: 'viscous', comp: 't1', field: 'post', emphasis: 'x' },
  'diff-viscous-t1': { model: 'viscous', comp: 't1', field: 'diff', emphasis: 'y' },
}
export function ch2SingleStep(beat: number): Ch2Step | null {
  return CH2_STEPS[CH2_PHASE_IDS[ch2Phase(beat)]] ?? null
}
/** A phase's results step (null for the imagery and every other phase). */
export function ch2StepOf(id: Ch2PhaseId): Ch2Step | null {
  return CH2_STEPS[id] ?? null
}
/** True on the beats whose stations are live controls (the director
 *  wanted any station button clickable, giving the same views of the
 *  stress space, unified across all center lakes):
 *  the imagery and results phases, both passes, any lake on the block. */
export function ch2IsStationPhase(ph: number): boolean {
  return ch2IsImageryPhase(ph) || ch2IsResultsPhase(ph)
}

// ── The STATIONS over the block (SimViewControls; the director asked for
// a linear flow of header buttons in place of the earlier two rows,
// because the talk now flows in time) — ONE row, the first lake's walk
// in time order:
// its imagery beats and its results beats, each a station naming the
// stage over the layer. Derived from CH2_BEAT_IDS, so deleting a beat
// deletes its station.
export type Ch2StationStage = 'pre' | 'post' | 'difference'
export type Ch2StationLayer = 'imagery' | Ch2Model
export interface Ch2Station {
  /** The beat's phase id (e.g. 'post-elastic-t1'). */
  id: Ch2PhaseId
  stage: Ch2StationStage
  layer: Ch2StationLayer
  /** The station's symbol after the layer word: σ_t1 or Δσ_t1 (none on
   *  the imagery). */
  sym: 'post' | 'diff' | null
}
export const CH2_STATIONS: Ch2Station[] = CH2_BEAT_IDS.filter((id) => !id.endsWith('/2'))
  .map((id): Ch2Station | null => {
    if (id === 'pre' || id === 'post') return { id, stage: id, layer: 'imagery', sym: null }
    const st = CH2_STEPS[id as Ch2PhaseId]
    if (!st) return null
    return {
      id: id as Ch2PhaseId,
      stage: st.field === 'diff' ? 'difference' : st.field,
      layer: st.model,
      sym: st.field === 'diff' ? 'diff' : 'post',
    }
  })
  .filter((s): s is Ch2Station => s !== null)

/** The paint the BLOCK wears on a results beat — and on the flat pages
 *  after the teaser (they cover it), the last results paint. Null on the
 *  imagery, bed and teaser beats. */
export function ch2BlockPaint(beat: number): Ch2Step | null {
  return ch2SingleStep(beat)
}

/** Beats drawn as a full-screen flat page above the (still-rendering) globe:
 *  the population's stress spaces, and the implications (+ its takeaway) —
 *  the slab's beats sit between them on their own layer (Ch2Slab.vue). */
export function ch2IsFlatPage(beat: number): boolean {
  const ph = ch2Phase(beat)
  return ph === CH2_PHASE.population || ph === CH2_PHASE.implications
}

// ── The TEASER (`teaser/2`; the director asked for it to cycle through
// automatically, one frame every 3 seconds, over all the bed realisations
// and their stress responses) — Lake 1951's bed
// ensemble from the Additional-Work MGSIM page (cinematic/scene_addl/
// build_mgsim_assets.py → R2 addl/mgsim/): BedMachine (the published
// bed) then the ten MGSIM realisations, each with its viscous Δσ_t1
// (with patch − no patch), all on the MGSIM page's ONE seismic scale
// (±400 kPa — the viscous response is ~300 kPa at p99.7, a pale wash at
// the chapter's ±1000). The beds are RG16 in the block's own encoding
// (sim_domains.json bed_off_m / bed_scale_m for 1951).
export const CH2_TEASER_LAKE = 'CW2019_1951'
export const CH2_TEASER_PERIOD_MS = 3000
export const CH2_TEASER_VLIM_KPA = 400
export interface Ch2TeaserFrame {
  id: string
  /** The figure label (bed name / realisation counter). */
  label: string
  /** R2 keys (mediaUrl). */
  bed: string
  stress: string
}
export const CH2_TEASER_FRAMES: Ch2TeaserFrame[] = [
  {
    id: 'published',
    label: 'BedMachine',
    bed: 'ch02/sim/simbed_CW2019_1951_rg16.png',
    stress: 'addl/mgsim/simstress_dsig_published.png',
  },
  ...Array.from({ length: 10 }, (_, i) => ({
    id: `mgsim0${i}`,
    label: `MGSIM bed ${i + 1} / 10`,
    bed: `addl/mgsim/simbed_mgsim0${i}_rg16.png`,
    stress: `addl/mgsim/simstress_dsig_mgsim0${i}.png`,
  })),
]
