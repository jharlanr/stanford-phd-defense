// Ch.2 sim-domain drainage catalog — shared between Globe
// (outline drawing + hover hit-testing), Explore (popout/phase state),
// and the phase-space / stats components.
//
// Data source: cinematic/scene_ch02/build_sim_domains.py →
// ch02/sim/simlakes_<id>.json + phase_space.json (the paper's
// georef.LAKE_CATEGORIES + in-polygon stress-array pickles).

export interface SimStatRow {
  max: number | null
  min: number | null
  mean: number | null
}

export interface SimModelStats {
  s1_post: SimStatRow
  s2_post: SimStatRow
  s1_diff: SimStatRow
  s2_diff: SimStatRow
}

export interface SimCatalogLake {
  cw: number
  /** Display id, e.g. "CW2019_2511". */
  id: string
  /** Dunmire catalog number (cw + 1523) — the number shown in figures. */
  num: number
  cls: 'cyan' | 'gray' | 'black' | 'dashcyan' | 'dashgray' | 'magenta'
  center: boolean
  /** True when this lake is a point in the Fig. 5 phase space. */
  phase: boolean
  rings_uv: [number, number][][]
  centroid_uv: [number, number]
  centroid_ll: [number, number]
  /** Per-model in-polygon tables. The MGSIM page's per-bed catalogs
   *  carry viscous only (elastic: null — no elastic runs in the ensemble). */
  stats: { n_points: number; elastic: SimModelStats | null; viscous: SimModelStats } | null
}

export interface SimLakesFile {
  center: string
  center_cw: number
  lakes: SimCatalogLake[]
}

export interface PhasePoint {
  center: number
  num: number
  group: 'cyan' | 'gray' | 'black' | 'magenta'
  x1: number | null
  y1: number | null
  x2: number | null
  y2: number | null
  /** phase_space_v2.json: the polygon-mean σ_t1 / σ_t2 of the
   *  VISCOUS pre-drainage state (no patch) — the one background both
   *  models share. The elastic points' x1/x2 there are the superposed
   *  post-drainage principals, σ(σ^V_pre + Δσ^E), not the elastic solve's. */
  x1_pre?: number | null
  x2_pre?: number | null
  /** MGSIM page extras: the catalog class, Fig.-5 membership, center flag. */
  cls?: string
  phase?: boolean
  is_center?: boolean
}

/** Ch.2: keys 'viscous' | 'elastic'. MGSIM page: 'published' | 'mgsimNN'
 *  (each = the published context lakes + that bed's domain lakes). */
export interface PhaseSpaceFile {
  models: Record<string, { points: PhasePoint[]; axis_kpa: number }>
  error_kpa: [number, number]
  center?: number
}

/** Fig. 1 legend, translated to the site's dark theme. Solid classes
 *  use the paper's hues; the dashed (uncertain) classes share their
 *  solid hue with a dashed stroke. */
export const SIM_LAKE_STYLE: Record<
  SimCatalogLake['cls'],
  { color: string; dash: number[]; label: string }
> = {
  cyan:     { color: '#31e5ff', dash: [],       label: 'englacial' },
  gray:     { color: '#c7cdd4', dash: [],       label: 'lateral' },
  black:    { color: '#20242b', dash: [],       label: 'no drainage' },
  dashcyan: { color: '#31e5ff', dash: [10, 8],  label: 'englacial · later' },
  dashgray: { color: '#c7cdd4', dash: [10, 8],  label: 'lateral · may be englacial' },
  magenta:  { color: '#ff5df2', dash: [],       label: 'same-day englacial' },
}

export const SIM_HOVER_GOLD = '#f5c75e'

/** The drained block shows ONE face at a time — pre/post
 *  Sentinel-2 imagery or a model's stress drape (the 2×2 pill grid). */
export type SimFace = 'pre' | 'post' | 'elastic' | 'viscous'

/** The director's distinction: which stress FIELD a model face drapes — the
 *  absolute no-patch σ_t1, the absolute with-patch σ_t1, or their
 *  difference (the paper's stress response Δσ_t1). Same words on the
 *  MGSIM page. */
export type SimField = 'nopatch' | 'patch' | 'difference'

// ── The sim-domain block payload (Ch.2 + the Additional-Work MGSIM page) ──
// One object, emitted per frame by the headless section that owns the
// block, consumed by Globe.vue. The optional trailing fields are the
// MGSIM page's additions — Ch.2 never sets them and the
// shader defaults keep the published look.
export interface SimDomainPayload {
  demUrl: string
  /** Bed-topography RG16 (frac = (bed − bedOffM)/bedScaleM). Swapping
   *  this on a live block reloads the bed + rebuilds the ice walls. */
  bedUrl: string
  bedOffM: number
  bedScaleM: number
  /** Published ELASTIC Δσ_t1 drape (difference). */
  stressUrl: string
  /** Published VISCOUS (t_sic) Δσ_t1 drape — same ±1 MPa scale. */
  stressViscousUrl: string
  /** Sentinel-2 truecolor faces: pre/post-drainage. */
  s2PreUrl: string
  s2PostUrl: string
  /** Drainage-catalog JSON (rings_uv + classes + stress tables). */
  lakesUrl: string
  bbox: { lonW: number; lonE: number; latS: number; latN: number }
  centerLon: number
  centerLat: number
  /** Half-size of the (rotated) model domain [km]. */
  halfKm: number
  /** Rotated-domain corner ring [[lon,lat] ×4] — the immune square. */
  corners: [number, number][]
  /** Surface elevation at the domain center [m] (button anchoring). */
  centerSurfM: number
  /** Knife-sweep progress. */
  carveT: number
  tileT: number
  /** Basemap-crop → Sentinel-2 face crossfade. */
  s2T: number
  /** Pre → post-drainage imagery crossfade. */
  drainT: number
  /** Catalog-outline overlay opacity. */
  lakesA: number
  /** Stress drape opacity (0 until a model is chosen). */
  stressT: number
  /** 0 = elastic texture, 1 = viscous (lerped on switch). */
  modelMix: number
  // ── MGSIM page ──
  /** Ice-surface + wall opacity: 1 = the solid block, ~0.25 = "see the
   *  bed topography" (the block goes glassy, the bed reads through). */
  surfA?: number
  /** 0 = the Ch.2 brown bedrock shading, 1 = the hypsometric ramp
   *  (bedPaletteUrl over [bedVminM, bedVmaxM]). */
  bedPalMix?: number
  bedPaletteUrl?: string
  bedVminM?: number
  bedVmaxM?: number
  /** A third stress texture mixed over the elastic/viscous pair by
   *  altMix — hot-swappable. Ch.2 uses it for the absolute no-patch /
   *  with-patch fields; the MGSIM page for every drape of a bed. */
  stressAltUrl?: string
  altMix?: number
  /** A FOURTH stress texture mixed over all of the above by altMixB
   *  (Ch.2): the second alt slot, so one absolute field can
   *  crossfade straight into another (the slots ping-pong) — never a dip
   *  through the imagery between two stress paints. The Globe announces
   *  each slot's texture once it is in ('sim-alt-ready' for the first,
   *  'sim-altb-ready' for this one; detail = the URL). */
  stressAltUrlB?: string
  altMixB?: number
  // ── Ch.2 block view (config/ch2State.ts) ──
  /** IMAGERY · DIFFERENCE: 0 = the S2 face, 1 = the post − pre
   *  reflectance-change ramp (a shader mode on the S2 pair). */
  imgDiffT?: number
  /** Ch.2 results walk (beats ≥ 3): hide the x/y/z triad — the stress
   *  space owns the right column there. The prism outline stays. */
  axesOff?: boolean
  /** Chapter 2: the ICE FLOW arrow is an HTML overlay near
   *  the centre-lakes inset (Ch2FlowArrow.vue) — the Globe's 3D arrow
   *  stays hidden. The MGSIM page leaves it unset (its 3D arrow stays). */
  flowOverlay?: boolean
  // ── Ch.2 path (config/ch2Beats.ts) ──
  /** The `outline` beat's MARKER STROKE: the domain's rectangle drawn on
   *  the greenland object's surface — progress round the four sides
   *  (0…1) and the line's opacity. Follows the live exaggeration. */
  markerT?: number
  markerA?: number
  /** The `teaser` beat's TWIN: the same block rendered a second time,
   *  to the right of the first (mirrored about the screen's centre),
   *  painted opaque with `stressUrl` (a ±400 kPa seismic drape). `t`
   *  slides it out from behind the first block (0 = gone, 1 = in place).
   *  `preload` lists every bed + drape the cycle will show — decoded and
   *  uploaded up front so a 3 s tick never stalls. `gap` (in block
   *  widths) seats the twin that far right of the first block's right-most
   *  corner instead of mirroring it about the screen centre. */
  twin?: { stressUrl: string; t: number; preload: string[]; gap?: number } | null
}

// ── Stress-space symbols (the paper's Fig. 5 / thesis stress spaces) ──
// Shared by the beat-2 PhaseSpacePanel and the results beats' diagrams.

/** Fig. 5's pinned marker per center-lake group (paper: s ^ v P X * D). */
export const PHASE_CENTER_MARKERS: Record<number, string> = {
  1910: 's', 1951: '^', 2394: 'v', 2411: 'P', 2416: 'X', 2511: '*', 2520: 'D',
}

/** Drainage-class colours on the dark theme (Fig. 5: cyan englacial,
 *  gray lateral, black-open none; magenta = same-day, MGSIM only). */
export const PHASE_GROUP_STYLE: Record<string, { color: string; open: boolean; label: string }> = {
  cyan: { color: '#31e5ff', open: false, label: 'englacial' },
  gray: { color: '#c7cdd4', open: false, label: 'lateral' },
  black: { color: '#e8e4da', open: true, label: 'none' },
  magenta: { color: '#ff5df2', open: false, label: 'same-day' },
}

/** Matplotlib-style marker paths: s ^ v P X * D o, half-size s. */
export function phaseMarkerPath(shape: string, x: number, y: number, s: number): string {
  switch (shape) {
    case 's':
      return `M ${x - s} ${y - s} h ${2 * s} v ${2 * s} h ${-2 * s} Z`
    case '^':
      return `M ${x} ${y - s} L ${x + s} ${y + s} L ${x - s} ${y + s} Z`
    case 'v':
      return `M ${x} ${y + s} L ${x + s} ${y - s} L ${x - s} ${y - s} Z`
    case 'P': {
      const a = s * 0.38
      return `M ${x - a} ${y - s} h ${2 * a} v ${s - a} h ${s - a} v ${2 * a} h ${-(s - a)} v ${s - a} h ${-2 * a} v ${-(s - a)} h ${-(s - a)} v ${-2 * a} h ${s - a} Z`
    }
    case 'X': {
      const a = s * 0.36
      return [
        `M ${x - s} ${y - s + a} L ${x - a} ${y} L ${x - s} ${y + s - a} L ${x - s + a} ${y + s}`,
        `L ${x} ${y + a} L ${x + s - a} ${y + s} L ${x + s} ${y + s - a} L ${x + a} ${y}`,
        `L ${x + s} ${y - s + a} L ${x + s - a} ${y - s} L ${x} ${y - a} L ${x - s + a} ${y - s} Z`,
      ].join(' ')
    }
    case '*': {
      const pts: string[] = []
      for (let i = 0; i < 10; i++) {
        const r = i % 2 === 0 ? s * 1.15 : s * 0.5
        const th = -Math.PI / 2 + (i * Math.PI) / 5
        pts.push(`${i === 0 ? 'M' : 'L'} ${x + r * Math.cos(th)} ${y + r * Math.sin(th)}`)
      }
      return pts.join(' ') + ' Z'
    }
    case 'D':
      return `M ${x} ${y - s} L ${x + s * 0.75} ${y} L ${x} ${y + s} L ${x - s * 0.75} ${y} Z`
    default:
      return `M ${x - s} ${y} a ${s} ${s} 0 1 0 ${2 * s} 0 a ${s} ${s} 0 1 0 ${-2 * s} 0`
  }
}
