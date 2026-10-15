// Ch.2 boundary-condition mode (from the director's brief): geometry
// shared by the Globe (the ghost model-domain shell + per-boundary
// overlays) and Explore (the head-on camera views, emitted as ordinary
// `chapterFocus` targets — no second controls system).
//
// World frame = the Globe's: unit sphere radius GLOBE_R, a point at
// elevation e [m] sits at GLOBE_R + e/SURF_MAX_M · exag along its
// radial (Globe.vue simElevPos). The model frame is the sims' (SI §4):
// x along flow (inflow wall x = −Lx/2, outflow +Lx/2), y across
// (lat0 = −Ly/2, lat1 = +Ly/2), origin at the patch centre. Lon/lat of
// a model point = bilinear on the FULL-domain corners baked by
// cinematic/scene_ch02/build_bc_cards.py (exact at the corners; < 10 m
// off inside a 25 km square at 70° N).

import { BC_CONST, type BcLake } from './ch2BcData'

export const GLOBE_R = 0.5 // Globe.vue GLOBE_RADIUS
export const SURF_MAX_M = 3500 // Globe.vue SURF_MAX_M
/** Exaggeration value that renders the ice at TRUE scale (1×). */
export const TRUE_EXAG = (SURF_MAX_M / 6.371e6) * GLOBE_R
/** Globe.vue TARGET_VIEW_SHIFT: in every chapter the camera's look-at
 *  point renders at (1 − s)/2 of the width, not the centre. */
export const VIEW_SHIFT = 0.3

export type V3 = [number, number, number]
export type BcKey = 'inflow' | 'outflow' | 'lat0' | 'lat1' | 'bed' | 'surface'
export const BC_KEYS: BcKey[] = ['surface', 'inflow', 'outflow', 'lat0', 'lat1', 'bed']

const D2R = Math.PI / 180
export const add = (a: V3, b: V3): V3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]]
export const sub = (a: V3, b: V3): V3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
export const mul = (a: V3, k: number): V3 => [a[0] * k, a[1] * k, a[2] * k]
export const dot = (a: V3, b: V3): number => a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
export const cross = (a: V3, b: V3): V3 => [
  a[1] * b[2] - a[2] * b[1],
  a[2] * b[0] - a[0] * b[2],
  a[0] * b[1] - a[1] * b[0],
]
export const norm = (a: V3): V3 => mul(a, 1 / (Math.hypot(a[0], a[1], a[2]) || 1))

export function unitLL(lon: number, lat: number): V3 {
  const la = lat * D2R
  const lo = lon * D2R
  return [Math.cos(la) * Math.cos(lo), Math.cos(la) * Math.sin(lo), Math.sin(la)]
}

export function worldLL(lon: number, lat: number, elevM: number, exag: number): V3 {
  return mul(unitLL(lon, lat), GLOBE_R + (elevM / SURF_MAX_M) * exag)
}

/** Model point (x, y) [m] → [lon, lat]. */
export function domainLL(lake: BcLake, x: number, y: number): [number, number] {
  const h = BC_CONST.Lx / 2
  const u = (x + h) / (2 * h)
  const v = (y + h) / (2 * h)
  const c = lake.corners
  const w = [(1 - u) * (1 - v), u * (1 - v), u * v, (1 - u) * v]
  let lon = 0
  let lat = 0
  for (let i = 0; i < 4; i++) {
    lon += w[i] * c[i][0]
    lat += w[i] * c[i][1]
  }
  return [lon, lat]
}

/** Model point at elevation → world. */
export function domainWorld(lake: BcLake, x: number, y: number, elevM: number, exag: number): V3 {
  const [lon, lat] = domainLL(lake, x, y)
  return worldLL(lon, lat, elevM, exag)
}

/** Local tangent frame at the domain centre: ex along flow, ey across,
 *  up radial (all unit, world). */
export function domainAxes(lake: BcLake): { ex: V3; ey: V3; up: V3 } {
  const h = BC_CONST.Lx / 2
  const up = unitLL(...domainLL(lake, 0, 0))
  const px = sub(unitLL(...domainLL(lake, h, 0)), unitLL(...domainLL(lake, -h, 0)))
  const ex = norm(sub(px, mul(up, dot(px, up))))
  const ey = norm(cross(up, ex))
  return { ex, ey, up }
}

const mean = (a: number[]): number => a.reduce((s, v) => s + v, 0) / a.length

/** Mean surface / bed elevation over the four outer walls [m]. */
export function domainElev(lake: BcLake): { zs: number; zb: number } {
  const w = lake.walls
  return {
    zs: mean([...w.inflow.zs, ...w.outflow.zs, ...w.lat0.zs, ...w.lat1.zs]),
    zb: mean([...w.inflow.zb, ...w.outflow.zb, ...w.lat0.zb, ...w.lat1.zb]),
  }
}

/** Sample the outer walls as model points: for each wall, the (x, y)
 *  of each stored station (inflow/outflow along +y, lat0/lat1 along +x). */
export function wallXY(key: 'inflow' | 'outflow' | 'lat0' | 'lat1', i: number, nPts: number): [number, number] {
  const h = BC_CONST.Lx / 2
  const t = -h + (2 * h * i) / (nPts - 1)
  switch (key) {
    case 'inflow': return [-h, t]
    case 'outflow': return [h, t]
    case 'lat0': return [t, -h]
    default: return [t, h]
  }
}

// ── Arrow-field scale (Globe + framing must agree) ──
/** Longest wall-profile arrow, as a fraction of Lx. */
export const BC_ARROW_FRAC = 0.15

// ── Head-on views ─────────────────────────────────────────────────────

export interface BcFocusTarget {
  lat: number
  lon: number
  cameraLat: number
  cameraLon: number
  distance: number
  fovDeg: number
  durationMs: number
  focalElevM: number
  focalExag: number
  up: V3
}

export interface BcViewOpts {
  /** Camera direction FROM the domain TO the camera in the landed
   *  framing (world, unit) — the overview + bed/surface keep its
   *  azimuth so every move reads as a turn of the same object. */
  landedCamDir: V3
  /** Exaggeration the view lands at. */
  exag: number
  /** Viewport in CSS px. */
  W: number
  H: number
  fovDeg: number
  /** Screen rect [px] the subject must fit inside. */
  rect: { x: number; y: number; w: number; h: number }
  durationMs: number
  /** The elastic bed view sits lower, so the blister's (vertical)
   *  pressure arrows read. */
  model?: 'viscous' | 'elastic'
}

/** World points that must be in frame for a view. */
function subjectPoints(lake: BcLake, key: BcKey | 'overview', exag: number): V3[] {
  const h = BC_CONST.Lx / 2
  const w = lake.walls
  const pts: V3[] = []
  const wallPts = (k: 'inflow' | 'outflow' | 'lat0' | 'lat1', out?: V3, outLen = 0) => {
    const n = w[k].zs.length
    for (let i = 0; i < n; i += Math.max(1, Math.floor(n / 8))) {
      const [x, y] = wallXY(k, i, n)
      for (const z of [w[k].zs[i], w[k].zb[i]]) {
        const p = domainWorld(lake, x, y, z, exag)
        pts.push(p)
        if (out) pts.push(add(p, mul(out, outLen)))
      }
    }
    const [xe, ye] = wallXY(k, n - 1, n)
    pts.push(domainWorld(lake, xe, ye, w[k].zs[n - 1], exag))
    pts.push(domainWorld(lake, xe, ye, w[k].zb[n - 1], exag))
  }
  const ax = domainAxes(lake)
  const Lw = (BC_CONST.Lx / 6.371e6) * GLOBE_R // Lx in world units
  switch (key) {
    case 'inflow':
      wallPts('inflow', mul(ax.ex, -1), BC_ARROW_FRAC * Lw)
      break
    case 'outflow':
      wallPts('outflow', ax.ex, BC_ARROW_FRAC * Lw)
      break
    case 'lat0':
    case 'lat1':
      wallPts(key)
      break
    default:
      for (const k of ['inflow', 'outflow', 'lat0', 'lat1'] as const) wallPts(k)
  }
  void h
  return pts
}

/** The chapterFocus target that frames `key` head-on. */
export function bcView(lake: BcLake, key: BcKey | 'overview', o: BcViewOpts): BcFocusTarget {
  const ax = domainAxes(lake)
  // Camera direction (from subject to camera): azimuth in the local
  // horizontal plane + elevation above it.
  const landedH = norm(sub(o.landedCamDir, mul(ax.up, dot(o.landedCamDir, ax.up))))
  const landedEl = Math.asin(Math.max(-1, Math.min(1, dot(o.landedCamDir, ax.up))))
  // Which flow-parallel wall faces the landed camera (the inflow/outflow
  // 3/4 views swing toward it, so the move is a short turn).
  const nearLat: V3 = dot(landedH, ax.ey) >= 0 ? ax.ey : mul(ax.ey, -1)
  let hDir: V3
  let el: number
  switch (key) {
    case 'inflow':
      // 3/4 view: the profile arrows are NORMAL to the wall, so a
      // square-on camera would see them end-on — swing 45° toward the
      // near lateral side so wall face and arrow lengths both read.
      hDir = norm(add(mul(ax.ex, -1), nearLat))
      el = 11 * D2R
      break
    case 'outflow':
      hDir = norm(add(ax.ex, nearLat))
      el = 11 * D2R
      break
    case 'lat0':
      hDir = mul(ax.ey, -1)
      el = 9 * D2R
      break
    case 'lat1':
      hDir = ax.ey
      el = 9 * D2R
      break
    case 'bed':
      // Down through the glassy ice onto the bed.
      hDir = landedH
      el = (o.model === 'elastic' ? 42 : 62) * D2R
      break
    case 'surface':
      hDir = landedH
      el = 48 * D2R
      break
    default:
      hDir = landedH
      el = landedEl
  }
  const camDir = norm(add(mul(hDir, Math.cos(el)), mul(ax.up, Math.sin(el))))
  const fwd = mul(camDir, -1)
  const upV = norm(sub(mul(ax.up, Math.cos(el)), mul(hDir, Math.sin(el))))
  const right = norm(cross(fwd, upV))

  // Fit (orthographic approximation — the views are telephoto).
  const pts = subjectPoints(lake, key, o.exag)
  let cx = 0
  let cy = 0
  let cz = 0
  for (const p of pts) {
    cx += p[0]
    cy += p[1]
    cz += p[2]
  }
  const c0: V3 = [cx / pts.length, cy / pts.length, cz / pts.length]
  let minR = Infinity
  let maxR = -Infinity
  let minU = Infinity
  let maxU = -Infinity
  for (const p of pts) {
    const d = sub(p, c0)
    const r = dot(d, right)
    const u = dot(d, upV)
    minR = Math.min(minR, r)
    maxR = Math.max(maxR, r)
    minU = Math.min(minU, u)
    maxU = Math.max(maxU, u)
  }
  const center = add(c0, add(mul(right, (minR + maxR) / 2), mul(upV, (minU + maxU) / 2)))
  const halfR = (maxR - minR) / 2
  const halfU = (maxU - minU) / 2
  const tanV = Math.tan((o.fovDeg * D2R) / 2)
  // px per world unit at distance D: (H/2) / (D tanV).
  const D = Math.max(
    (halfR * o.H) / (tanV * o.rect.w),
    (halfU * o.H) / (tanV * o.rect.h),
  )
  // Where the look-at point lands on screen (Globe view shift), and
  // where the subject's centre should land (the rect's centre): slide
  // the focal so the subject sits in the rect.
  const pxPerWorld = o.H / 2 / (D * tanV)
  const lookX = (o.W * (1 - VIEW_SHIFT)) / 2
  const lookY = o.H / 2
  const wantX = o.rect.x + o.rect.w / 2
  const wantY = o.rect.y + o.rect.h / 2
  const focal = sub(
    center,
    add(mul(right, (wantX - lookX) / pxPerWorld), mul(upV, -(wantY - lookY) / pxPerWorld)),
  )
  const cam = add(focal, mul(camDir, D))
  const fr = Math.hypot(focal[0], focal[1], focal[2])
  const cr = Math.hypot(cam[0], cam[1], cam[2])
  return {
    lat: Math.asin(focal[2] / fr) / D2R,
    lon: Math.atan2(focal[1], focal[0]) / D2R,
    focalElevM: ((fr - GLOBE_R) / o.exag) * SURF_MAX_M,
    focalExag: o.exag,
    cameraLat: Math.asin(cam[2] / cr) / D2R,
    cameraLon: Math.atan2(cam[1], cam[0]) / D2R,
    distance: cr,
    fovDeg: o.fovDeg,
    durationMs: o.durationMs,
    up: upV,
  }
}

/** Camera direction (unit, from focal to camera) of a chapterFocus
 *  target given in the Globe's convention. */
export function focusCamDir(f: {
  lat: number
  lon: number
  cameraLat?: number
  cameraLon?: number
  distance?: number
  focalElevM?: number
  focalExag?: number
}): V3 {
  const cam = mul(unitLL(f.cameraLon ?? f.lon, f.cameraLat ?? Math.max(20, f.lat - 25)), f.distance ?? 0.95)
  const focal = worldLL(f.lon, f.lat, f.focalElevM ?? 0, f.focalExag ?? 0)
  return norm(sub(cam, focal))
}
