// Ch.2 boundary-condition mode — the 3-D overlays.
// Built by Globe.vue at the CURRENT exaggeration once the
// block has landed; rebuilt on every (lake, model, focus, exag) change.
//
//   ALWAYS (BC mode on): the ghost MODEL DOMAIN — the four outer walls
//     of the 24.75 km Elmer domain (the site's solid block is the
//     central 14.75 km analysis tile; the boundary conditions live 5 km
//     further out on every side), translucent with fine edges.
//   FOCUS (a card clicked): only that boundary's overlay —
//     inflow/outflow  the Dirichlet profile u_x(z′) as arrows at five
//                     stations + the traced profile through their free
//                     ends + a translucent fill (values: ch2BcData.ts,
//                     USF_TAVz.F90 / the elastic LUA, run inputs);
//     lat0/lat1       free-slip glyphs: arrows IN the wall plane (u·ŷ=0);
//     bed             the r = 2.5 km patch (ring + disc) and, outside it,
//                     the Weertman drag glyphs τ_b ∥ −x (viscous) or the
//                     clamp dots u = 0 (elastic) with pressure arrows
//                     inside the blister; a ghost of the full-domain bed;
//     surface         the free surface outlined + its normals n.

import * as THREE from 'three'
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js'
import { BC_CONST, BC_GRID_IDX, BC_LAKES, BC_ZETA, type BcLake } from '../config/ch2BcData'
import {
  BC_ARROW_FRAC,
  GLOBE_R,
  domainAxes,
  domainLL,
  domainWorld,
  wallXY,
  type BcKey,
  type V3,
} from '../config/simBcGeo'

type WallKey = 'inflow' | 'outflow' | 'lat0' | 'lat1'
const WALLS: WallKey[] = ['inflow', 'outflow', 'lat0', 'lat1']

export interface BcBuildOpts {
  lakeId: string
  model: 'viscous' | 'elastic'
  focus: BcKey | null
  exag: number
  /** Bed elevation [m] of the site's analysis-tile DEM at (lon, lat),
   *  or null outside the tile (then the coarse full-domain grid). */
  tileBedAt?: (lon: number, lat: number) => number | null
}

export interface BcAnchor {
  /** on the face (mid-height for walls) */
  pos: THREE.Vector3
  /** on the face's top edge (shown when the face points away) */
  edge: THREE.Vector3
  /** outward normal */
  n: THREE.Vector3
}

// ── materials (shared, created once; opacity = base × fade) ──
interface BcMat { m: THREE.Material & { opacity: number }; base: number }
let MATS: Record<string, BcMat> | null = null
function mats(): Record<string, BcMat> {
  if (MATS) return MATS
  const basic = (color: number, base: number, extra: Partial<THREE.MeshBasicMaterialParameters> = {}): BcMat => ({
    m: new THREE.MeshBasicMaterial({
      color, transparent: true, opacity: base, depthWrite: false, ...extra,
    }),
    base,
  })
  const line = (color: number, base: number): BcMat => ({
    m: new THREE.LineBasicMaterial({ color, transparent: true, opacity: base, depthWrite: false }),
    base,
  })
  MATS = {
    shell: basic(0xbfd8ee, 0.07, { side: THREE.DoubleSide }),
    shellFocus: basic(0xf5c75e, 0.2, { side: THREE.DoubleSide }),
    edge: line(0xf5f0e6, 0.5),
    edgeFocus: line(0xf5c75e, 0.95),
    arrow: basic(0xe4f1ff, 0.95),
    trace: basic(0xf5c75e, 1),
    fill: basic(0xf5c75e, 0.16, { side: THREE.DoubleSide }),
    axis: line(0xf5f0e6, 0.55),
    drag: basic(0xe6b07a, 0.95),
    patchDisc: basic(0xf5c75e, 0.3, { side: THREE.DoubleSide }),
    patchRing: basic(0xf5c75e, 1),
    water: basic(0x5fb4ff, 0.42, { side: THREE.DoubleSide }),
    waterArrow: basic(0x8fd0ff, 1),
    pin: basic(0xd9cbb3, 0.9),
    ghostBed: basic(0x6b5238, 0.55, { side: THREE.DoubleSide }),
    ghostSurf: basic(0xdfe8f0, 0.1, { side: THREE.DoubleSide }),
    normal: basic(0xf5e3b0, 0.9),
  }
  return MATS
}

/** All BC materials (Globe warm-renders them at tile build). */
export function bcMaterialList(): THREE.Material[] {
  return Object.values(mats()).map((x) => x.m)
}

interface BcWallParts { fill: THREE.Mesh; top: THREE.Line; bot: THREE.Line; focused: boolean }

/** Light the boundary under a hovered card (no rebuild): a wall's face
 *  + rims, the surface = every wall's top rim, the bed = every bottom
 *  rim. Pass null to clear. */
export function setBcHover(g: THREE.Group, key: BcKey | null): void {
  const M = mats()
  const parts = g.userData.parts as Record<string, BcWallParts> | undefined
  if (!parts) return
  for (const [k, p] of Object.entries(parts)) {
    const wallOn = p.focused || key === k
    p.fill.material = wallOn ? M.shellFocus.m : M.shell.m
    p.top.material = wallOn || key === 'surface' ? M.edgeFocus.m : M.edge.m
    p.bot.material = wallOn || key === 'bed' ? M.edgeFocus.m : M.edge.m
  }
}

/** Fade the whole overlay set (0..1). */
export function setBcFade(k: number): void {
  for (const x of Object.values(mats())) x.m.opacity = x.base * k
}

// ── geometry helpers ──
const v3 = (p: V3): THREE.Vector3 => new THREE.Vector3(p[0], p[1], p[2])

function arrowGeoms(from: THREE.Vector3, to: THREE.Vector3, r: number, out: THREE.BufferGeometry[]): void {
  const dir = to.clone().sub(from)
  const len = dir.length()
  if (len < 1e-12) return
  dir.normalize()
  const headLen = Math.min(len * 0.45, r * 6)
  const shaftLen = len - headLen
  const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir)
  if (shaftLen > 1e-12) {
    const s = new THREE.CylinderGeometry(r, r, shaftLen, 6, 1, true)
    s.applyQuaternion(q)
    s.translate(...from.clone().addScaledVector(dir, shaftLen / 2).toArray())
    out.push(s.toNonIndexed())
    s.dispose()
  }
  const h = new THREE.ConeGeometry(r * 2.6, headLen, 10)
  h.applyQuaternion(q)
  h.translate(...from.clone().addScaledVector(dir, shaftLen + headLen / 2).toArray())
  out.push(h.toNonIndexed())
  h.dispose()
}

/** Drop consecutive (near-)duplicates — a zero-length segment makes
 *  a centripetal Catmull-Rom loop wildly. */
function dedupe(pts: THREE.Vector3[]): THREE.Vector3[] {
  const out: THREE.Vector3[] = []
  for (const p of pts) {
    if (!out.length || out[out.length - 1].distanceTo(p) > 1e-9) out.push(p)
  }
  return out
}

/** Smooth tube through `pts` (profiles, the patch ring). */
function tubeGeom(pts: THREE.Vector3[], r: number, closed = false): THREE.BufferGeometry {
  let q = dedupe(pts)
  if (closed && q.length > 2 && q[0].distanceTo(q[q.length - 1]) < 1e-9) q = q.slice(0, -1)
  const curve = new THREE.CatmullRomCurve3(q, closed, 'centripetal')
  return new THREE.TubeGeometry(curve, Math.max(8, q.length * 4), r, 6, closed).toNonIndexed()
}

/** Straight-segment tube (sharp corners — the domain's outline). */
function polyTube(pts: THREE.Vector3[], r: number): THREE.BufferGeometry {
  const q = dedupe(pts)
  const path = new THREE.CurvePath<THREE.Vector3>()
  for (let i = 0; i < q.length - 1; i++) path.add(new THREE.LineCurve3(q[i], q[i + 1]))
  return new THREE.TubeGeometry(path, (q.length - 1) * 2, r, 6, false).toNonIndexed()
}

function mergedMesh(geoms: THREE.BufferGeometry[], mat: THREE.Material, order: number): THREE.Mesh | null {
  if (!geoms.length) return null
  for (const g of geoms) {
    // mergeGeometries needs identical attribute sets
    for (const name of Object.keys(g.attributes)) {
      if (name !== 'position') g.deleteAttribute(name)
    }
  }
  const merged = mergeGeometries(geoms, false)
  for (const g of geoms) g.dispose()
  if (!merged) return null
  const mesh = new THREE.Mesh(merged, mat)
  mesh.renderOrder = order
  mesh.frustumCulled = false
  return mesh
}

function lineFrom(pts: THREE.Vector3[], mat: THREE.Material, order: number): THREE.Line {
  const l = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), mat)
  l.renderOrder = order
  l.frustumCulled = false
  return l
}

/** Bilinear sample of the coarse full-domain grid at model (x, y). */
function gridAt(lake: BcLake, which: 'zs' | 'zb', x: number, y: number): number {
  const n = BC_GRID_IDX.length
  const g = lake.grid[which]
  const pos = (m: number): number => {
    // model coordinate → fractional grid index
    const node = (m + BC_CONST.Lx / 2) / 150
    let i = 0
    while (i < n - 2 && BC_GRID_IDX[i + 1] < node) i++
    const t = (node - BC_GRID_IDX[i]) / (BC_GRID_IDX[i + 1] - BC_GRID_IDX[i])
    return i + Math.max(0, Math.min(1, t))
  }
  const fx = pos(x)
  const fy = pos(y)
  const ix = Math.min(n - 2, Math.floor(fx))
  const iy = Math.min(n - 2, Math.floor(fy))
  const tx = fx - ix
  const ty = fy - iy
  const at = (r: number, c: number): number => g[r * n + c]
  return (
    at(iy, ix) * (1 - tx) * (1 - ty) + at(iy, ix + 1) * tx * (1 - ty) +
    at(iy + 1, ix) * (1 - tx) * ty + at(iy + 1, ix + 1) * tx * ty
  )
}

export function buildBcGroup(o: BcBuildOpts): THREE.Group | null {
  const lake = BC_LAKES[o.lakeId]
  if (!lake) return null
  const M = mats()
  const g = new THREE.Group()
  const ex = o.exag
  const W = (x: number, y: number, z: number): THREE.Vector3 => v3(domainWorld(lake, x, y, z, ex))
  const Lw = (BC_CONST.Lx / 6.371e6) * GLOBE_R // Lx in world units
  const mPerWorld = BC_CONST.Lx / Lw
  const ax = domainAxes(lake)
  const exV = v3(ax.ex)
  const eyV = v3(ax.ey)
  const upV = v3(ax.up)
  const worldPerM = 1 / mPerWorld
  // vertical world units per metre of ice at this exaggeration
  const vertPerM = ex / 3500

  // ── ghost model domain: four outer walls ──
  const anchors: Record<string, BcAnchor> = {}
  const parts: Record<string, BcWallParts> = {}
  for (const k of WALLS) {
    const wz = lake.walls[k]
    const n = wz.zs.length
    const top: THREE.Vector3[] = []
    const bot: THREE.Vector3[] = []
    const pos: number[] = []
    for (let i = 0; i < n; i++) {
      const [x, y] = wallXY(k, i, n)
      top.push(W(x, y, wz.zs[i]))
      bot.push(W(x, y, wz.zb[i]))
    }
    for (let i = 0; i < n - 1; i++) {
      const a = bot[i], b = bot[i + 1], c = top[i + 1], d = top[i]
      pos.push(a.x, a.y, a.z, b.x, b.y, b.z, c.x, c.y, c.z, a.x, a.y, a.z, c.x, c.y, c.z, d.x, d.y, d.z)
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3))
    const focused = o.focus === k
    const fill = new THREE.Mesh(geo, focused ? M.shellFocus.m : M.shell.m)
    fill.renderOrder = 6
    fill.frustumCulled = false
    g.add(fill)
    const em = focused ? M.edgeFocus.m : M.edge.m
    const topL = lineFrom(top, em, 7)
    const botL = lineFrom(bot, em, 7)
    g.add(topL, botL)
    g.add(lineFrom([top[0], bot[0]], M.edge.m, 7))
    parts[k] = { fill, top: topL, bot: botL, focused }
    // anchors: wall centre (mid-height) + its top edge
    const mid = Math.floor(n / 2)
    const nrm = k === 'inflow' ? exV.clone().negate() : k === 'outflow' ? exV.clone()
      : k === 'lat0' ? eyV.clone().negate() : eyV.clone()
    const [mx, my] = wallXY(k, mid, n)
    anchors[k] = {
      pos: W(mx, my, (wz.zs[mid] + wz.zb[mid]) / 2),
      edge: W(mx, my, wz.zs[mid]),
      n: nrm,
    }
  }
  const zsC = gridAt(lake, 'zs', 0, 0)
  const zbC = gridAt(lake, 'zb', 0, 0)
  anchors.surface = { pos: W(0, 0, zsC), edge: W(0, 0, zsC), n: upV.clone() }
  anchors.bed = { pos: W(0, 0, zbC), edge: W(0, 0, zbC), n: upV.clone().negate() }
  g.userData.anchors = anchors
  g.userData.parts = parts
  // screen-fit points for the card layout: the 8 domain corners
  g.userData.corners = WALLS.flatMap((k) => {
    const wz = lake.walls[k]
    const n = wz.zs.length
    return [0, n - 1].flatMap((i) => {
      const [x, y] = wallXY(k, i, n)
      return [W(x, y, wz.zs[i]), W(x, y, wz.zb[i])]
    })
  })
  // bed-card candidates: the four bottom corners (a wall's own anchor
  // sits mid-wall, so a corner never doubles a lateral card's dot)
  g.userData.bedCorners = (['lat0', 'lat1'] as const).flatMap((k) => {
    const wz = lake.walls[k]
    const n = wz.zs.length
    return [0, n - 1].map((i) => {
      const [x, y] = wallXY(k, i, n)
      return W(x, y, wz.zb[i])
    })
  })

  const f = o.focus
  if (f === 'inflow' || f === 'outflow') buildWallProfile(g, lake, f, o, W, exV, Lw, vertPerM)
  else if (f === 'lat0' || f === 'lat1') buildLateral(g, lake, f, W, exV, Lw, vertPerM)
  else if (f === 'bed') buildBed(g, lake, o, W, exV, upV, worldPerM)
  else if (f === 'surface') buildSurface(g, lake, W, upV, worldPerM)

  g.traverse((c) => { c.frustumCulled = false })
  return g
}

// ── inflow / outflow: the Dirichlet profile ──
function buildWallProfile(
  g: THREE.Group, lake: BcLake, wall: 'inflow' | 'outflow', o: BcBuildOpts,
  W: (x: number, y: number, z: number) => THREE.Vector3, exV: THREE.Vector3, Lw: number, vertPerM: number,
): void {
  const M = mats()
  const st = lake.prof[wall]
  const key = o.model === 'viscous' ? 'uv' : 'ue'
  const uMax = Math.max(...st.flatMap((s) => s[key]))
  const maxLen = BC_ARROW_FRAC * Lw
  const x = wall === 'inflow' ? -BC_CONST.Lx / 2 : BC_CONST.Lx / 2
  // one arrow weight for both x-walls (the outflow ice can be half as
  // thick): from the domain-mean station thickness, 8 gaps over H
  const all = [...lake.prof.inflow, ...lake.prof.outflow]
  const Hmean = all.reduce((a, s) => a + s.H, 0) / all.length
  const r = Math.max(1.2e-6, ((Hmean * vertPerM) / 8) * 0.075)
  const arrows: THREE.BufferGeometry[] = []
  const traces: THREE.BufferGeometry[] = []
  const fills: number[] = []
  const ARROW_ZETA = [0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1]
  for (const s of st) {
    const base = (z: number) => W(x, s.ly, s.zb + z * s.H)
    const off = (u: number) => exV.clone().multiplyScalar((u / uMax) * maxLen)
    // free end of each arrow: upstream tail (inflow) / downstream tip (outflow)
    const freeEnd = (p: THREE.Vector3, u: number) =>
      wall === 'inflow' ? p.clone().sub(off(u)) : p.clone().add(off(u))
    const uAt = (z: number): number => {
      // linear interpolation in BC_ZETA (25 levels)
      const n = BC_ZETA.length - 1
      const t = Math.max(0, Math.min(n, z * n))
      const i = Math.min(n - 1, Math.floor(t))
      const a = t - i
      return s[key][i] * (1 - a) + s[key][i + 1] * a
    }
    for (const z of ARROW_ZETA) {
      const p = base(z)
      const u = uAt(z)
      if (u / uMax < 0.02) {
        // u = 0 (elastic bed, u_b = 0): a dot, not an arrow
        const dot = new THREE.SphereGeometry(r * 2.2, 8, 6)
        dot.translate(p.x, p.y, p.z)
        arrows.push(dot.toNonIndexed())
        dot.dispose()
        continue
      }
      const e = freeEnd(p, u)
      if (wall === 'inflow') arrowGeoms(e, p, r, arrows)
      else arrowGeoms(p, e, r, arrows)
    }
    // the traced profile through the free ends (all 25 levels)
    const curve = BC_ZETA.map((z, i) => freeEnd(base(z), s[key][i]))
    traces.push(tubeGeom(curve, r * 0.9))
    // translucent fill between the wall axis and the profile
    for (let i = 0; i < BC_ZETA.length - 1; i++) {
      const a0 = base(BC_ZETA[i]), a1 = base(BC_ZETA[i + 1])
      const b0 = curve[i], b1 = curve[i + 1]
      fills.push(a0.x, a0.y, a0.z, b0.x, b0.y, b0.z, b1.x, b1.y, b1.z)
      fills.push(a0.x, a0.y, a0.z, b1.x, b1.y, b1.z, a1.x, a1.y, a1.z)
    }
    // the wall axis (u = 0 reference) at this station
    g.add(lineFrom([base(0), base(1)], M.axis.m, 8))
  }
  const fg = new THREE.BufferGeometry()
  fg.setAttribute('position', new THREE.Float32BufferAttribute(fills, 3))
  const fm = new THREE.Mesh(fg, M.fill.m)
  fm.renderOrder = 8
  g.add(fm)
  const am = mergedMesh(arrows, M.arrow.m, 9)
  const tm = mergedMesh(traces, M.trace.m, 10)
  if (am) g.add(am)
  if (tm) g.add(tm)
}

// ── lateral walls: free slip, no penetration ──
function buildLateral(
  g: THREE.Group, lake: BcLake, wall: 'lat0' | 'lat1',
  W: (x: number, y: number, z: number) => THREE.Vector3, exV: THREE.Vector3, Lw: number, vertPerM: number,
): void {
  const M = mats()
  const h = BC_CONST.Lx / 2
  const y = wall === 'lat0' ? -h : h
  const wz = lake.walls[wall]
  const n = wz.zs.length
  const cols = 6
  const arrows: THREE.BufferGeometry[] = []
  const Hm = wz.zs.reduce((a, v, i) => a + v - wz.zb[i], 0) / n
  const r = Math.max(1.2e-6, ((Hm * vertPerM) / 4) * 0.07)
  const len = (Lw / cols) * 0.55
  for (let c = 0; c < cols; c++) {
    const x = -h + ((c + 0.5) * 2 * h) / cols
    const i = Math.round(((x + h) / (2 * h)) * (n - 1))
    const zs = wz.zs[i]
    const zb = wz.zb[i]
    for (const z of [0.25, 0.5, 0.75]) {
      const p = W(x, y, zb + z * (zs - zb))
      const a = p.clone().addScaledVector(exV, -len / 2)
      const b = p.clone().addScaledVector(exV, len / 2)
      arrowGeoms(a, b, r, arrows)
    }
  }
  const am = mergedMesh(arrows, M.arrow.m, 9)
  if (am) g.add(am)
}

// ── bed: Weertman outside, the patch / blister inside ──
function buildBed(
  g: THREE.Group, lake: BcLake, o: BcBuildOpts,
  W: (x: number, y: number, z: number) => THREE.Vector3, exV: THREE.Vector3, upV: THREE.Vector3,
  worldPerM: number,
): void {
  const M = mats()
  const h = BC_CONST.Lx / 2
  const R = BC_CONST.R
  const bedAt = (x: number, y: number): number => {
    if (o.tileBedAt) {
      const [lon, lat] = domainLL(lake, x, y)
      const b = o.tileBedAt(lon, lat)
      if (b !== null) return b
    }
    return gridAt(lake, 'zb', x, y)
  }
  // ghost of the full-domain bed (coarse grid) — the site's solid tile
  // bed covers the centre; this fills the 5 km annulus out to the walls
  {
    const n = BC_GRID_IDX.length
    const pos: number[] = []
    const P = (iy: number, ix: number): THREE.Vector3 => {
      const x = BC_GRID_IDX[ix] * 150 - h
      const yy = BC_GRID_IDX[iy] * 150 - h
      return W(x, yy, lake.grid.zb[iy * n + ix] - 25)
    }
    for (let iy = 0; iy < n - 1; iy++) {
      for (let ix = 0; ix < n - 1; ix++) {
        const a = P(iy, ix), b = P(iy, ix + 1), c = P(iy + 1, ix + 1), d = P(iy + 1, ix)
        pos.push(a.x, a.y, a.z, b.x, b.y, b.z, c.x, c.y, c.z, a.x, a.y, a.z, c.x, c.y, c.z, d.x, d.y, d.z)
      }
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3))
    const mesh = new THREE.Mesh(geo, M.ghostBed.m)
    mesh.renderOrder = 5
    g.add(mesh)
  }
  const lift = 30 // m above the bed so it reads through the glassy ice
  const viscous = o.model === 'viscous'
  // patch / blister disc + ring
  {
    const N = 72
    const disc: number[] = []
    const ring: THREE.Vector3[] = []
    const c = W(0, 0, bedAt(0, 0) + lift)
    for (let i = 0; i <= N; i++) {
      const t = (i / N) * Math.PI * 2
      const x = R * Math.cos(t)
      const y = R * Math.sin(t)
      ring.push(W(x, y, bedAt(x, y) + lift * 1.3))
    }
    // rings of the disc (conform to the bed)
    const NR = 6
    const P = (k: number, i: number): THREE.Vector3 => {
      const rr = (R * k) / NR
      const t = (i / N) * Math.PI * 2
      const x = rr * Math.cos(t)
      const y = rr * Math.sin(t)
      return k === 0 ? c : W(x, y, bedAt(x, y) + lift)
    }
    for (let k = 0; k < NR; k++) {
      for (let i = 0; i < N; i++) {
        const a = P(k, i), b = P(k, i + 1), cc = P(k + 1, i + 1), d = P(k + 1, i)
        disc.push(a.x, a.y, a.z, b.x, b.y, b.z, cc.x, cc.y, cc.z, a.x, a.y, a.z, cc.x, cc.y, cc.z, d.x, d.y, d.z)
      }
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(disc, 3))
    const dm = new THREE.Mesh(geo, viscous ? M.patchDisc.m : M.water.m)
    dm.renderOrder = 9
    g.add(dm)
    const rt = mergedMesh([tubeGeom(ring, 160 * worldPerM, true)], M.patchRing.m, 10)
    if (rt) g.add(rt)
  }
  // glyph grid over the whole domain outside the patch
  const NG = 14
  const step = (2 * h) / NG
  const glyphs: THREE.BufferGeometry[] = []
  const r = 70 * worldPerM
  for (let iy = 0; iy < NG; iy++) {
    for (let ix = 0; ix < NG; ix++) {
      const x = -h + (ix + 0.5) * step
      const y = -h + (iy + 0.5) * step
      if (Math.hypot(x, y) <= R + step * 0.35) continue
      const p = W(x, y, bedAt(x, y) + lift)
      if (viscous) {
        // τ_b opposes the sliding velocity (u_b ∥ +x): arrow toward −x
        const a = p.clone().addScaledVector(exV, step * worldPerM * 0.3)
        const b = p.clone().addScaledVector(exV, -step * worldPerM * 0.3)
        arrowGeoms(a, b, r, glyphs)
      } else {
        // clamped: u = 0
        const s = new THREE.SphereGeometry(r * 2.6, 10, 8)
        s.translate(p.x, p.y, p.z)
        glyphs.push(s.toNonIndexed())
        s.dispose()
      }
    }
  }
  const gm = mergedMesh(glyphs, viscous ? M.drag.m : M.pin.m, 9)
  if (gm) g.add(gm)
  if (!viscous) {
    // blister pressure: σ·n_b = −P_w ρ g H n_b pushes UP on the ice base
    const press: THREE.BufferGeometry[] = []
    const pts: [number, number][] = [[0, 0]]
    for (const [rr, k] of [[1000, 6], [1900, 12]] as const) {
      for (let i = 0; i < k; i++) {
        const t = (i / k) * Math.PI * 2 + (k === 12 ? Math.PI / 12 : 0)
        pts.push([rr * Math.cos(t), rr * Math.sin(t)])
      }
    }
    const len = 1600 * worldPerM
    for (const [x, y] of pts) {
      const p = W(x, y, bedAt(x, y) + lift)
      arrowGeoms(p, p.clone().addScaledVector(upV, len), r * 1.25, press)
    }
    const pm = mergedMesh(press, M.waterArrow.m, 11)
    if (pm) g.add(pm)
  }
}

// ── surface: stress-free ──
function buildSurface(
  g: THREE.Group, lake: BcLake,
  W: (x: number, y: number, z: number) => THREE.Vector3, upV: THREE.Vector3, worldPerM: number,
): void {
  const M = mats()
  const h = BC_CONST.Lx / 2
  // ghost of the full-domain surface (coarse grid), just below the
  // site's solid tile surface so the tile wins in the centre
  {
    const n = BC_GRID_IDX.length
    const pos: number[] = []
    const P = (iy: number, ix: number): THREE.Vector3 =>
      W(BC_GRID_IDX[ix] * 150 - h, BC_GRID_IDX[iy] * 150 - h, lake.grid.zs[iy * n + ix] - 20)
    for (let iy = 0; iy < n - 1; iy++) {
      for (let ix = 0; ix < n - 1; ix++) {
        const a = P(iy, ix), b = P(iy, ix + 1), c = P(iy + 1, ix + 1), d = P(iy + 1, ix)
        pos.push(a.x, a.y, a.z, b.x, b.y, b.z, c.x, c.y, c.z, a.x, a.y, a.z, c.x, c.y, c.z, d.x, d.y, d.z)
      }
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3))
    const mesh = new THREE.Mesh(geo, M.ghostSurf.m)
    mesh.renderOrder = 5
    g.add(mesh)
  }
  // the free surface outlined (top edges of the four walls, gold tube)
  const loop: THREE.Vector3[] = []
  for (const k of ['lat0', 'outflow', 'lat1', 'inflow'] as const) {
    const wz = lake.walls[k]
    const n = wz.zs.length
    const idx = [...Array(n).keys()]
    // walk the boundary counter-clockwise: lat0 (+x), outflow (+y),
    // lat1 (−x), inflow (−y)
    const order = k === 'lat1' || k === 'inflow' ? idx.reverse() : idx
    for (const i of order) {
      const [x, y] = wallXY(k, i, n)
      loop.push(W(x, y, wz.zs[i] + 15))
    }
  }
  loop.push(loop[0].clone())
  const tm = mergedMesh([polyTube(loop, 110 * worldPerM)], M.trace.m, 10)
  if (tm) g.add(tm)
  // normals n on a 5 × 5 grid
  const normals: THREE.BufferGeometry[] = []
  const NG = 5
  const len = 1400 * worldPerM
  for (let iy = 0; iy < NG; iy++) {
    for (let ix = 0; ix < NG; ix++) {
      const x = -h + ((ix + 0.5) * 2 * h) / NG
      const y = -h + ((iy + 0.5) * 2 * h) / NG
      const p = W(x, y, gridAt(lake, 'zs', x, y) + 25)
      arrowGeoms(p, p.clone().addScaledVector(upV, len), 55 * worldPerM, normals)
    }
  }
  const nm = mergedMesh(normals, M.normal.m, 11)
  if (nm) g.add(nm)
}
