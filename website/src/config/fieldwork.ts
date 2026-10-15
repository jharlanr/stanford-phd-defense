// The 2023 Greenland fieldwork ride-along (the Introduction's opening and
// the Additional-Work door). One registry for everything the fly-along needs on both
// sides of the seam: the Globe's Sentinel-2 patch, the flat map's
// projection, the clips, and the default view the Introduction lands on.
//
// FRAME. Everything is in local-tangent-plane METRES around
// (LAT_C, LON_C): x east, y SOUTH (SVG convention), the same separable
// projection SectionExtras used (dx = R·dλ·cos φ₀, dy = R·dφ), so the
// GPX tracks line up with the gdalwarp-aeqd basemap to within a few
// metres over the 50 × 30 km crop. The Globe builds its patch with the
// SAME mapping, so the 3-D landing frame and the 2-D map are one image.

export const FW_LAT_C = 68.59
export const FW_LON_C = -48.88
export const FW_R_EARTH = 6378137
const DEG2RAD = Math.PI / 180

/** Sentinel-2 true-colour crop (2023-08-18, 10 m/px, 5000 × 3000). */
export const FW_BASEMAP_KEY = 'extras/extras_basemap_sentinel2_20230818.webp'
export const FW_HALF_X_M = 25000
export const FW_HALF_Y_M = 15000

/**
 * The WIDE context basemap (the fieldwork door's): the whole 2023-09-01
 * flying day at 20 m/px, 6800 × 5900 since the 10 km widening. The day track runs from Ilulissat
 * out to the lake cluster — x −91.4..13.3 km, y −74.0..12.3 km — so the
 * detail crop above holds only its last few kilometres.
 *
 * Same projection origin as the detail crop, so a point's metres mean the
 * same number in both; this one is just asymmetric, because the day went
 * west and south. Drawn BENEATH the detail image, which stays 10 m/px
 * over the flight area.
 *
 * 2023-08-06 is the one date in the season with all three covering tiles
 * acquired and near-cloudless (22WDB 1.0 %, 22WEA 0.1 %, 22WEB 0.5 %) —
 * S2 swaths usually image neighbouring tiles on different days, and a
 * multi-date mosaic would seam visibly across the transit.
 *
 * FULL MODE ONLY. The Introduction's fly-along keeps the detail crop and
 * its old limits: the director judged that landing near-perfect, so widening
 * the world under it is not worth the risk.
 */
export const FW_WIDE_KEY = 'extras/extras_basemap_wide_sentinel2_20230806_eqc136.webp'
// The director asked for 10 km of margin on every side beyond the tracks'
// box (was −97/−80/19/18), so that when panning around, the limits of the
// map sit a little further out than the limits of the GPX tracks.
// 136 × 118 km, 6800 × 5900 px at 20 m — the `_eqc136` keys.
export const FW_WIDE_X0 = -107000
export const FW_WIDE_Y0 = -90000
export const FW_WIDE_X1 = 29000
export const FW_WIDE_Y1 = 28000

export function fwLonToX(lon: number): number {
  return FW_R_EARTH * (lon - FW_LON_C) * DEG2RAD * Math.cos(FW_LAT_C * DEG2RAD)
}
export function fwLatToY(lat: number): number {
  return -FW_R_EARTH * (lat - FW_LAT_C) * DEG2RAD
}
export function fwXToLon(x: number): number {
  return FW_LON_C + x / (FW_R_EARTH * DEG2RAD * Math.cos(FW_LAT_C * DEG2RAD))
}
export function fwYToLat(y: number): number {
  return FW_LAT_C - y / (FW_R_EARTH * DEG2RAD)
}

/**
 * The door page's default view (full mode): centred on the three
 * 2023-09-01 tracks, 14.6 km tall, width following the viewport's aspect
 * (SectionExtras's framing). The Introduction lands on fwLandingView()
 * instead.
 */
export const FW_DEFAULT_VIEW = { cx: -2637, cy: -690, heightM: 14625 }

/** A viewBox in frame metres (x east, y south) — FieldworkExplorer's view. */
export interface FwViewBox { x: number; y: number; w: number; h: number }

/**
 * The three Introduction tracks' bounding box in frame metres, over EVERY
 * trkpt of their GPX (GH010200 x −3245..7346 y −2492..5543 · GH010212
 * x −6668..−4711 y −5211..−3317 · GH010194 x −7620..−4254 y −5923..−4644;
 * computed by a scratch script in the same projection as fwLonToX/fwLatToY).
 * Frozen so the Globe can dive to the landing before the GPX arrive;
 * FieldworkExplorer warns if the loaded tracks disagree.
 */
export const FW_INTRO_TRACKS_BOX = { x0: -7620, y0: -5923, x1: 7346, y1: 5543 }

/**
 * Where that box sits on screen when the Introduction lands, as fractions
 * of the viewport — the director's own framing, read off a screenshot of
 * the landing he wanted (a 2038 × ~950 window,
 * the box at x 963–1867 px, y 93–785 px, 60.4 px/km): the tracks fill
 * the right two-thirds, the bottom-left is open ice for the clip panel.
 * The box is fitted into the band top..bottom and right-aligned at
 * `right`; on a narrow (4:3) screen it may grow left to `minLeft`, past
 * which it shrinks instead.
 */
export const FW_LAND_BOX = { top: 0.098, bottom: 0.826, right: 0.916, minLeft: 0.25 }

/**
 * The Globe's horizontal view shift during the Introduction (Globe.vue
 * TARGET_VIEW_SHIFT, `camera.setViewOffset`): the camera's focal point
 * lands at (1 − shift) / 2 of the width, i.e. 35 %, not the centre.
 */
export const FW_VIEW_SHIFT = 0.3

/**
 * The Introduction's landing view for a vw × vh viewport: FW_INTRO_TRACKS_BOX
 * placed at FW_LAND_BOX, kept inside the 10 m crop (an ultra-wide screen
 * slides the tracks left rather than show past the crop's edge).
 */
export function fwLandingView(vw: number, vh: number): FwViewBox {
  const b = FW_INTRO_TRACKS_BOX
  const f = FW_LAND_BOX
  const bw = b.x1 - b.x0
  const bh = b.y1 - b.y0
  // px per metre: fill the band's height unless the box would then run
  // left of minLeft.
  const s = Math.min(((f.bottom - f.top) * vh) / bh, ((f.right - f.minLeft) * vw) / bw)
  const px0 = f.right * vw - bw * s
  const py0 = f.top * vh + ((f.bottom - f.top) * vh - bh * s) / 2
  const w = vw / s
  const h = vh / s
  const x = Math.max(-FW_HALF_X_M, Math.min(FW_HALF_X_M - w, b.x0 - px0 / s))
  const y = Math.max(-FW_HALF_Y_M, Math.min(FW_HALF_Y_M - h, b.y0 - py0 / s))
  return { x, y, w, h }
}

/** Pan/zoom limits for the flat map. `intro` uses the detail crop's
 *  bounds; `full` uses the wide basemap's. */
export const FW_MIN_HEIGHT_M = 2500
export const FW_MAX_HEIGHT_M = 2 * FW_HALF_Y_M

/** Pan bounds per mode, in the shared local-tangent frame. */
export function fwBounds(wide: boolean): { x0: number; y0: number; x1: number; y1: number } {
  return wide
    ? { x0: FW_WIDE_X0, y0: FW_WIDE_Y0, x1: FW_WIDE_X1, y1: FW_WIDE_Y1 }
    : { x0: -FW_HALF_X_M, y0: -FW_HALF_Y_M, x1: FW_HALF_X_M, y1: FW_HALF_Y_M }
}

export type FieldworkSide = 'right' | 'left' | 'forward' | 'back'

export interface FieldworkClip {
  id: string
  /** ISO date of the flight. */
  date: string
  /**
   * Which window the GoPro looked out of, as segments over the (served)
   * clip's own time: the wedge uses the last segment whose `from` ≤ t.
   * Undefined = no wedge. The director's own list of clips gives the
   * sides and the camera-clock times of each
   * switch; the seconds here are `mark − creation_time`, and for the six
   * clips whose marks fell before the clip's start the switch was read
   * off contact sheets instead (168 179 194 204 208 215). The director's
   * corrections: 194 starts on the RIGHT and its last minute is left
   * (R → L → R → L, the third flip read off frames at 92 s, where the
   * camera swings back through the cabin); 208's flip is ~14 s earlier
   * than the frame read, 11 s; the rest stand.
   */
  sides?: { from: number; side: FieldworkSide }[]
  /**
   * The served clip is a cut of the original: seconds into the original
   * (and its GPX) where the served clip starts. The marker rides
   * `videoTime + cropStart`.
   */
  cropStart?: number
}

const R = 'right' as const
const L = 'left' as const

/**
 * The 2023 clips, every one with a GPX track (no track → not used, the
 * director's rule). Three are also the Introduction's. The door shows
 * only the clips of FW_DAYS (`fwDoorClips()`): the director pared the
 * legend to 22 Aug · 1 Sep · both, so the 25/28 Aug entries stay
 * here — and on R2 — but off the map.
 */
export const FW_CLIPS: FieldworkClip[] = [
  // ── 22 Aug ──
  { id: 'GH010162', date: '2023-08-22', sides: [{ from: 0, side: R }, { from: 113, side: L }] }, // L from 09:42:21 local (the director's correction; 72 s was the camera-clock read)
  { id: 'GH010164', date: '2023-08-22', sides: [{ from: 0, side: R }] },
  { id: 'GH010166', date: '2023-08-22', sides: [{ from: 0, side: R }, { from: 88, side: L }, { from: 125, side: R }, { from: 203, side: L }, { from: 286, side: R }] },
  { id: 'GH010167', date: '2023-08-22', sides: [{ from: 0, side: R }, { from: 155, side: L }] },
  { id: 'GH010168', date: '2023-08-22', sides: [{ from: 0, side: L }], cropStart: 25 },
  { id: 'GH010173', date: '2023-08-22', sides: [{ from: 0, side: L }, { from: 14, side: R }, { from: 74, side: L }, { from: 134, side: R }] },
  { id: 'GH010177', date: '2023-08-22' },
  { id: 'GH010178', date: '2023-08-22', sides: [{ from: 0, side: L }, { from: 224, side: R }] },
  { id: 'GH010179', date: '2023-08-22', sides: [{ from: 0, side: R }], cropStart: 20 },
  { id: 'GH010181', date: '2023-08-22', sides: [{ from: 0, side: R }] },
  { id: 'GH010182', date: '2023-08-22', sides: [{ from: 0, side: R }] },
  { id: 'GH010185', date: '2023-08-22', sides: [{ from: 0, side: L }] },
  // ── 25 Aug ──
  { id: 'GH010190', date: '2023-08-25', sides: [{ from: 0, side: L }] },
  // ── 28 Aug ──
  { id: 'GH010191', date: '2023-08-28', sides: [{ from: 0, side: L }] },
  { id: 'GH010192', date: '2023-08-28', sides: [{ from: 0, side: R }] },
  // ── 1 Sep ──
  { id: 'GH010194', date: '2023-09-01', sides: [{ from: 0, side: R }, { from: 18, side: L }, { from: 62, side: R }, { from: 92, side: L }] },
  { id: 'GH010197', date: '2023-09-01', sides: [{ from: 0, side: R }] },
  { id: 'GH010200', date: '2023-09-01', sides: [{ from: 0, side: R }] },
  { id: 'GH010204', date: '2023-09-01', sides: [{ from: 0, side: L }] },
  { id: 'GH010205', date: '2023-09-01' },
  { id: 'GH010207', date: '2023-09-01', sides: [{ from: 0, side: R }] },
  { id: 'GH010208', date: '2023-09-01', sides: [{ from: 0, side: R }, { from: 11, side: L }] },
  { id: 'GH010212', date: '2023-09-01', sides: [{ from: 0, side: L }] },
  { id: 'GH010214', date: '2023-09-01', sides: [{ from: 0, side: R }] },
  { id: 'GH010215', date: '2023-09-01', sides: [{ from: 0, side: L }], cropStart: 0 },
  { id: 'GH010217', date: '2023-09-01', sides: [{ from: 0, side: R }] },
  { id: 'GH010218', date: '2023-09-01', sides: [{ from: 0, side: L }] },
]

/** The clips the door draws: those of the legend's days, in FW_CLIPS order. */
export function fwDoorClips(): FieldworkClip[] {
  return FW_CLIPS.filter((c) => FW_DAYS.some((d) => d.date === c.date))
}

/**
 * The Introduction's three 1 Sep clips, in the order its NEXT walks them
 * (the director's order: first the long track striking
 * northwest–southeast, then the squiggly track directly to its
 * northwest, and finally the north-westernmost track), told apart by
 * their GPX geometry:
 *   GH010200 — the long straight track, 13.3 km NW–SE (path/chord 1.00)
 *   GH010212 — the squiggly one NW of it (path/chord 1.27, an S-bend)
 *   GH010194 — the north-westernmost (reaches 68.643°N, 49.07°W)
 * config/introSteps.ts's clip1 · clip2 · clip3 are these, in this order.
 */
export const FW_INTRO_CLIP_IDS: readonly string[] = ['GH010200', 'GH010212', 'GH010194']

/**
 * Where an Introduction clip starts playing, as the panel's own clock
 * reads there (local Greenland time, HH:MM:SS) — the director wanted the
 * first clip of the Introduction to start part-way along its track, and
 * settled on 11:15:00; the second track starts at 16:05:30.
 *   GH010200 runs 11:13:17 → 11:17:15: 11:15:00 is 102 s in, 5.7 of its 13.3 km
 *   GH010212 runs 16:04:56 → 16:07:19: 16:05:30 is 34 s in, 1.5 of its 3.4 km
 * A clip not listed starts at its beginning; the fieldwork door's clips
 * always do (a click there opens a clip from its start). The scrubber still
 * reaches the whole clip.
 */
export const FW_INTRO_CLIP_START: Readonly<Record<string, string>> = {
  GH010200: '11:15:00',
  GH010212: '16:05:30',
}

/** The side in force at `t` seconds into the served clip. */
export function fwSideAt(clip: FieldworkClip, t: number): FieldworkSide | null {
  if (!clip.sides?.length) return null
  let side: FieldworkSide = clip.sides[0].side
  for (const seg of clip.sides) if (t >= seg.from) side = seg.side
  return side
}

export interface FieldworkDay {
  date: string
  /** Legend label. */
  label: string
  /**
   * The day's colour, used for EVERYTHING of that day on the door — the
   * legend swatch, the helicopter route, the clip tracks, the marker and
   * wedge of a playing clip, the clip panel's frame (the director asked
   * for consistent colour choices: yellow for 22 Aug, purple for 1 Sep).
   */
  color: string
  /** The handheld GPS day track. */
  dayTrackKey?: string
  /** The Sentinel-2 pass the legend lands on when this day is picked
   *  (an FW_IMAGERY date); unset = the nearest pass that shows the
   *  array. The director's choice. */
  imagery?: string
}

/**
 * The 23 GNSS stations of the 2022–23 campaign, from Stevens et al. 2026
 * (Nat. Commun., 10.1038/s41467-026-73033-z): the paper's own a-priori
 * coordinates, `apcoords_lle_2023.mat` in goodnesglaciers/lakes_cluster
 * (Zenodo 19387821), with the paper's names — SQ11–16 at ~950 m, SQ21–27
 * at ~1150 m, SQ31–37 at ~1350 m, the moulin sites MLOW and MHIH, and
 * QIET. Checked against every handheld waypoint on the footage drive:
 * all 23 within 22–54 m (the helicopter's landing spot), elevations
 * within ±33 m; the field names G1xx/G2xx/G3xx are SQ1x/SQ2x/SQ3x.
 * Its own legend layer, not tied to a flying day.
 */
export const FW_STATIONS_KEY = 'extras/fieldwork_2023/gpx/stations_2023.gpx'

/**
 * The legend's days: the two long flying days, Ilulissat → the array and
 * back (the director kept only 22 Aug, 1 Sep and both days as the
 * options). 25 Aug (GH010190) and 28 Aug (GH010191/192) were short hops
 * near the coast; their clips and GPX stay on R2 but are not drawn.
 */
export const FW_DAYS: FieldworkDay[] = [
  { date: '2023-08-22', label: '22 Aug', color: '#f4cf6a', dayTrackKey: 'extras/fieldwork_2023/gpx/day_track_20230822.gpx' },
  { date: '2023-09-01', label: '1 Sep', color: '#d5a6ff', dayTrackKey: 'extras/fieldwork_2023/gpx/day_track_20230901.gpx' },
]

/**
 * Imagery on the door: ONE Sentinel-2 pass per option, never a composite
 * (the director could see the edges of a composite at a glance).
 * Each option is the wide 20 m image plus a 10 m inset over the array
 * from the SAME pass, feathered — a resolution step, not an imagery
 * seam. The three MGRS tiles of a pass are one acquisition cut into
 * files (seconds apart on the same orbit), so stitching them is
 * seamless; it is tiles from DIFFERENT passes that seam.
 *
 * Which passes (every pass 15 Jul – 30 Sep scored on its
 * SCL cloud mask over the flight corridor, then eyeballed at 200 m):
 * the orbits here repeat every 5 days and
 * two of the three that cross the area have a swath edge through it —
 * both flying days (22 Aug, 1 Sep) were imaged with the array in the
 * gap, and 18 Aug (the Introduction's crop) lacks the Ilulissat half.
 * Of the full-coverage passes only 6 Aug and 15 Sep are clean end to
 * end. The next best were built and rejected: 21 Aug (the day before
 * the first flight) is hazy over the whole array, 10 Sep has cloud
 * bands and their shadows across it, 23 Sep is under cloud on its east
 * half. Each day pins its pass (FW_DAYS.imagery).
 */
export interface FieldworkImagery {
  date: string
  label: string
  wideKey: string
  detailKey: string
  /** What the pass does NOT cover (a swath edge): 'array' = the 10 m
   *  inset is empty, 'west' = the Ilulissat half is. Shown dimmer in
   *  the legend; a day never lands on an 'array' gap. */
  gap?: 'array' | 'west'
}
function imagery(date: string, label: string, gap?: FieldworkImagery['gap'], insetRev = ''): FieldworkImagery {
  const d = date.replace(/-/g, '')
  return {
    date,
    label,
    // `_eqc` = built in the site's own projection with the
    // north-up extent (tools/build_extras_basemap.py). Everything before
    // (`_wide_…`, `_wide_…_full`) drew terrain 62 km south of where the
    // routes were — the director saw a lake half cut off. `_eqc136` = the
    // wides 10 km wider on every side. `insetRev` marks an inset
    // rebuilt since (`_r2` = the auto stretch for the bright September
    // passes) — a new key, because the old one is cached.
    wideKey: `extras/extras_basemap_wide_sentinel2_${d}_eqc136.webp`,
    detailKey: `extras/extras_basemap_sentinel2_${d}_eqc${insetRev}_feathered.webp`,
    ...(gap ? { gap } : {}),
  }
}
/**
 * Every pass the director can choose from (he wanted to decide himself
 * which days of imagery are good and bad): every pass with the
 * array imaged and under ~60 % cloud over it (an SCL survey in the
 * site's frame), plus the two flying days
 * themselves, whose passes miss the array. The director's cuts:
 * **15 Sep is the latest** (18/20/23/27/30 Sep dropped), and the two
 * clean full-coverage passes before 25 Jul added (2 Jul, 12 Jul — the
 * June–mid-July survey found nothing else under 25 % over the array
 * with the whole box imaged). Prune here as the director decides.
 */
export const FW_IMAGERY: FieldworkImagery[] = [
  imagery('2023-07-02', '2 Jul'),
  imagery('2023-07-12', '12 Jul'),
  imagery('2023-07-25', '25 Jul'),
  imagery('2023-08-06', '6 Aug'),
  imagery('2023-08-08', '8 Aug', 'west'),
  imagery('2023-08-11', '11 Aug'),
  imagery('2023-08-14', '14 Aug'),
  imagery('2023-08-18', '18 Aug', 'west'),
  imagery('2023-08-21', '21 Aug'),
  imagery('2023-08-22', '22 Aug', 'array'),
  imagery('2023-09-01', '1 Sep', 'array', '_r2'),
  imagery('2023-09-10', '10 Sep', undefined, '_r2'),
  imagery('2023-09-15', '15 Sep', undefined, '_r2'),
]
export function fwImageryFor(date: string): FieldworkImagery {
  const pinned = FW_DAYS.find((d) => d.date === date)?.imagery
  const hit = pinned && FW_IMAGERY.find((im) => im.date === pinned)
  if (hit) return hit
  const t = Date.parse(date)
  // The nearest pass that shows the array (the director's point: 15 Sep
  // imagery under 1 Sep footage makes no sense).
  return FW_IMAGERY.filter((im) => im.gap !== 'array').reduce((best, im) =>
    Math.abs(Date.parse(im.date) - t) < Math.abs(Date.parse(best.date) - t) ? im : best)
}

/** Greenland summer time (WGST) = UTC−2; the GPX is UTC. */
export const FW_UTC_OFFSET_H = -2

export function fwGpxKey(id: string): string {
  return `extras/fieldwork_2023/gpx/${id}_1_GPS5.gpx`
}

export function fwVideoKey(id: string): string {
  return `extras/fieldwork_2023/video/${id}_1080p.mp4`
}

/**
 * The landing camera for the fly-along: straight down, north up, over the
 * map point that the view shift puts at the camera's focal (35 % of the
 * width, mid-height) in fwLandingView(), at the altitude that makes the
 * telephoto frame the view's height — so the flat map that takes over is
 * the same picture at the same scale. Frame height on the surface =
 * 2·A·tan(fov/2).
 */
export const FW_LAND_FOV_DEG = 2.0
const EARTH_R_KM = 6371
export function fwLandingFocus(
  vw: number = window.innerWidth || 1440,
  vh: number = window.innerHeight || 900,
): { lat: number; lon: number; distance: number } {
  const v = fwLandingView(vw, vh)
  const lat = fwYToLat(v.y + v.h / 2)
  const lon = fwXToLon(v.x + ((1 - FW_VIEW_SHIFT) / 2) * v.w)
  const altM = v.h / (2 * Math.tan((FW_LAND_FOV_DEG * DEG2RAD) / 2))
  // Globe: sphere radius 0.5 world units = 6371 km; `distance` is from
  // the sphere CENTRE.
  const distance = 0.5 * (1 + altM / 1000 / EARTH_R_KM)
  return { lat, lon, distance }
}
