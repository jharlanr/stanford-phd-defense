// Introduction step 0: the ice sheet's dimensions as figure labels on the
// greenland object (the director's brief: a measuring line along the
// length and one across the width, loose references for roughly measuring
// the dimensions of the ice sheet, in a big font, plus the sea-level
// number near the south-east tip).
//
// The numbers, checked against BedMachine Greenland v6's mask (every
// land/ice cell, 1.2 km stride, EPSG:3413 → WGS84, R = 6371 km):
//   · length: Cape Farewell 59.747°N 43.895°W → Cape Morris Jesup
//     83.658°N 33.332°W, great circle 2,674 km (ice sheet alone: 2,670;
//     the latitude span alone is 2,659 km)            → GRIS_LENGTH_KM
//   · width: widest at 76.25–76.5°N, 70.19°W → 18.59°W, great circle
//     1,309 km (1,352 km along the parallel; ice sheet alone 1,276)
//                                                     → GRIS_WIDTH_KM
// The measuring lines are great-circle arcs of EXACTLY these lengths at
// the object's own horizontal scale (the globe's radius ↔ 6,371 km),
// parallel to those two chords and slid off the ice sheet so they float
// beside it. They are drawn as arcs of projected points, so the on-screen
// length is the arc, not a chord.

/** Sea-level-rise equivalent of the whole ice sheet, metres. ONE place. */
export const GRIS_SLR_M = 7.4
export const GRIS_LENGTH_KM = 2670
export const GRIS_WIDTH_KM = 1300

const R_EARTH_KM = 6371
const D2R = Math.PI / 180
const R2D = 180 / Math.PI

type LatLon = [number, number]

/** Great-circle initial bearing (radians, clockwise from north) a → b. */
function bearing([la1, lo1]: LatLon, [la2, lo2]: LatLon): number {
  const p1 = la1 * D2R
  const p2 = la2 * D2R
  const dl = (lo2 - lo1) * D2R
  return Math.atan2(
    Math.sin(dl) * Math.cos(p2),
    Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl),
  )
}

/** Point reached from `a` along bearing `brg` (rad) after angular distance `d` (rad; may be negative). */
function destination([la, lo]: LatLon, brg: number, d: number): LatLon {
  const p1 = la * D2R
  const l1 = lo * D2R
  const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(brg))
  const l2 = l1 + Math.atan2(
    Math.sin(brg) * Math.sin(d) * Math.cos(p1),
    Math.cos(d) - Math.sin(p1) * Math.sin(p2),
  )
  return [p2 * R2D, l2 * R2D]
}

/** Great-circle angular distance a → b (rad). */
function angDist([la1, lo1]: LatLon, [la2, lo2]: LatLon): number {
  const p1 = la1 * D2R
  const p2 = la2 * D2R
  const dl = (lo2 - lo1) * D2R
  return Math.acos(
    Math.min(1, Math.max(-1, Math.sin(p1) * Math.sin(p2) + Math.cos(p1) * Math.cos(p2) * Math.cos(dl))),
  )
}

export interface DimLineSpec {
  id: string
  /** The chord the line is parallel to (its two real end points). */
  a: LatLon
  b: LatLon
  /** Drawn length, km (at the object's horizontal scale). */
  lengthKm: number
  /** Slide sideways off the chord's midpoint, km; + = to the LEFT of a→b. */
  offsetKm: number
  /** Height above the sphere, world units (globe radius 0.5). */
  lift: number
  /** Samples along the arc. */
  samples?: number
}

export interface DimLine {
  id: string
  points: LatLon[]
  lift: number
}

/**
 * The measuring arc: through the chord's midpoint slid `offsetKm`
 * sideways, along the chord's bearing there, `lengthKm` long. Drawn at
 * radius 0.5 + lift, the angular span is shrunk by 0.5 / (0.5 + lift) so
 * the arc's world length is exactly lengthKm at the globe's scale.
 */
export function dimLine(spec: DimLineSpec, globeRadius = 0.5): DimLine {
  const n = spec.samples ?? 33
  const mid = destination(spec.a, bearing(spec.a, spec.b), angDist(spec.a, spec.b) / 2)
  const brgMid = bearing(mid, spec.b)
  const off = spec.offsetKm / R_EARTH_KM
  const c = destination(mid, brgMid - Math.PI / 2, off)
  // Bearing at the slid centre: aim at the chord's far end slid the same
  // way, so the line stays parallel to the chord across its length.
  const bSlid = destination(spec.b, bearing(spec.b, spec.a) + Math.PI / 2, off)
  const brg = bearing(c, bSlid)
  const span = (spec.lengthKm / R_EARTH_KM) * (globeRadius / (globeRadius + spec.lift))
  const points: LatLon[] = []
  for (let i = 0; i < n; i++) {
    const s = -span / 2 + (span * i) / (n - 1)
    points.push(destination(c, brg, s))
  }
  return { id: spec.id, points, lift: spec.lift }
}

/** Arc length of a sampled line at radius 0.5 + lift, in km at the globe's scale (the check). */
export function drawnLengthKm(line: DimLine, globeRadius = 0.5): number {
  let a = 0
  for (let i = 1; i < line.points.length; i++) a += angDist(line.points[i - 1], line.points[i])
  return a * R_EARTH_KM * ((globeRadius + line.lift) / globeRadius)
}

// The real end points (BedMachine v6, above).
export const GRIS_SOUTH: LatLon = [59.747, -43.895]
export const GRIS_NORTH: LatLon = [83.658, -33.332]
export const GRIS_WEST_76: LatLon = [76.375, -70.19]
export const GRIS_EAST_76: LatLon = [76.375, -18.59]
