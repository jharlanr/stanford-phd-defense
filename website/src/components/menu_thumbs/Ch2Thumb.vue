<!-- Chapter 2 card: the PNAS simulation domain of the main-text lake
     (CW2019_2511, SectionCh2's DEFAULT_LAKE) as a small block — the real
     25 m surface DEM on top, ice walls down the sides — turning slowly
     while its face cycles: Sentinel-2 before the drainage → after →
     the elastic response → the viscous response. Thumb-sized copies of
     the chapter's tiles live at menu/ch02/ (cinematic/scene_menu/
     build_menu_thumbs.py). The director's brief: the simulation domain
     object, rotating between pre-drain imagery, post-drain imagery,
     elastic model, and viscous model. A later note (the domain still
     looked jagged at the edges, and the flow arrow was not useful):
     the flow arrow is gone; the rim is drawn from a heavily smoothed
     band of the height grid (the interior keeps its relief), on a finer
     grid, and each ice wall is one flat-shaded plane. -->
<template>
  <div class="pnas-stage">
    <canvas ref="canvas" class="pnas-canvas" />
    <div class="pnas-label">{{ label }}</div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as THREE from 'three'
import { mediaUrl } from '../../config/media'

defineProps<{ playing?: boolean; lit?: boolean }>()
const canvas = ref<HTMLCanvasElement | null>(null)
const label = ref('')

// sim_domains.json, CW2019_2511 — the tile frame and the rotated domain.
const BBOX = { lonW: -50.366609708120535, lonE: -49.797813092029685, latS: 70.87999351078459, latN: 71.06556449759158 }
const CORNERS: [number, number][] = [
  [-49.993073, 71.061996],
  [-50.355671, 71.001384],
  [-50.169664, 70.883562],
  [-49.808751, 70.943773],
]
const DEM_MAX_M = 3500
const V_EXAG = 3 // vertical exaggeration of the surface relief
const SLAB_KM = 1.6 // block thickness below the mean surface, km (drawn)
const N = 144 // grid cells across the domain
// Height smoothing: the interior gets a light pass (the
// lake basin and ridges are many cells wide and survive); a band
// RIM_BAND cells wide along each wall eases onto a heavy blur, so the
// rim — the block's silhouette at card size — is a clean curve, not the
// 256-px DEM's pixel noise times V_EXAG.
const LIGHT_PASSES = 3
const HEAVY_PASSES = 40
const RIM_BAND = 16

const FACES = [
  'Sentinel-2 · 18 Aug 2019',
  'Sentinel-2 · 23 Aug 2019',
  'elastic model',
  'viscous model',
]
const HOLD_MS = 2600
const FADE_MS = 1300
const TURN_MS = 40000 // one full turn of the block

let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let topMat: THREE.ShaderMaterial | null = null
let disposables: { dispose(): void }[] = []
let rafId = 0
let t0 = 0
let ro: ResizeObserver | null = null
let dead = false

function placeholderTex(r: number, g: number, b: number): THREE.DataTexture {
  const t = new THREE.DataTexture(new Uint8Array([r, g, b, 255]), 1, 1)
  t.needsUpdate = true
  return t
}

function loadTex(file: string, onto: { value: THREE.Texture }) {
  new THREE.TextureLoader().load(mediaUrl(`menu/ch02/${file}`), (t) => {
    if (dead) { t.dispose(); return }
    t.colorSpace = THREE.NoColorSpace // sampled as-is, written as-is
    t.anisotropy = renderer?.capabilities.getMaxAnisotropy() ?? 1
    onto.value.dispose()
    onto.value = t
    disposables.push(t)
  })
}

/** Decode the RG16 DEM into metres on a (w × h) grid, row 0 = north. */
function loadDem(): Promise<{ w: number; h: number; m: Float32Array }> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      const c = document.createElement('canvas')
      c.width = img.naturalWidth
      c.height = img.naturalHeight
      const cx = c.getContext('2d', { willReadFrequently: true })!
      cx.drawImage(img, 0, 0)
      const d = cx.getImageData(0, 0, c.width, c.height).data
      const m = new Float32Array(c.width * c.height)
      for (let i = 0; i < m.length; i++) {
        m[i] = ((d[i * 4] * 256 + d[i * 4 + 1]) / 65535) * DEM_MAX_M
      }
      resolve({ w: c.width, h: c.height, m })
    }
    img.onerror = reject
    img.src = mediaUrl('menu/ch02/dem_256.png')
  })
}

/** `passes` of a 3 × 3 box over an n × n grid (edge cells average what exists). */
function boxBlur(src: number[], n: number, passes: number): number[] {
  let a = src.slice()
  let b = new Array<number>(a.length)
  for (let p = 0; p < passes; p++) {
    for (let j = 0; j < n; j++) {
      for (let i = 0; i < n; i++) {
        let acc = 0
        let cnt = 0
        for (let dj = -1; dj <= 1; dj++) {
          const jj = j + dj
          if (jj < 0 || jj >= n) continue
          for (let di = -1; di <= 1; di++) {
            const ii = i + di
            if (ii < 0 || ii >= n) continue
            acc += a[jj * n + ii]
            cnt++
          }
        }
        b[j * n + i] = acc / cnt
      }
    }
    ;[a, b] = [b, a]
  }
  return a
}

function buildBlock(dem: { w: number; h: number; m: Float32Array }) {
  if (!scene) return
  const sample = (tu: number, tv: number): number => {
    // tv = 0 at the south edge; image row 0 is north.
    const fx = Math.min(dem.w - 1, Math.max(0, tu * (dem.w - 1)))
    const fy = Math.min(dem.h - 1, Math.max(0, (1 - tv) * (dem.h - 1)))
    const ix = Math.floor(fx)
    const iy = Math.floor(fy)
    const ax = fx - ix
    const ay = fy - iy
    const jx = Math.min(dem.w - 1, ix + 1)
    const jy = Math.min(dem.h - 1, iy + 1)
    const a = dem.m[iy * dem.w + ix]
    const b = dem.m[iy * dem.w + jx]
    const c = dem.m[jy * dem.w + ix]
    const d = dem.m[jy * dem.w + jx]
    return (a * (1 - ax) + b * ax) * (1 - ay) + (c * (1 - ax) + d * ax) * ay
  }

  // The domain square from its corners: c0 → c1 and c0 → c3 are edges.
  const [c0, c1, , c3] = CORNERS
  const e1 = [c1[0] - c0[0], c1[1] - c0[1]]
  const e2 = [c3[0] - c0[0], c3[1] - c0[1]]
  const lonC = CORNERS.reduce((s, p) => s + p[0], 0) / 4
  const latC = CORNERS.reduce((s, p) => s + p[1], 0) / 4
  const kmPerDegLat = 111.32
  const kmPerDegLon = 111.32 * Math.cos((latC * Math.PI) / 180)

  const pos: number[] = []
  const uv: number[] = []
  const heights: number[] = []
  for (let j = 0; j <= N; j++) {
    for (let i = 0; i <= N; i++) {
      const s = i / N
      const t = j / N
      const lon = c0[0] + s * e1[0] + t * e2[0]
      const lat = c0[1] + s * e1[1] + t * e2[1]
      const tu = (lon - BBOX.lonW) / (BBOX.lonE - BBOX.lonW)
      const tv = (lat - BBOX.latS) / (BBOX.latN - BBOX.latS)
      const hM = sample(tu, tv)
      heights.push(hM)
      pos.push((lon - lonC) * kmPerDegLon, 0, -(lat - latC) * kmPerDegLat)
      uv.push(tu, tv)
    }
  }
  // Light blur everywhere, heavy blur eased in along the rim band.
  const light = boxBlur(heights, N + 1, LIGHT_PASSES)
  const heavy = boxBlur(light, N + 1, HEAVY_PASSES)
  for (let j = 0; j <= N; j++) {
    for (let i = 0; i <= N; i++) {
      const k = j * (N + 1) + i
      const d = Math.min(i, j, N - i, N - j) / RIM_BAND
      const w = d >= 1 ? 0 : 1 - d * d * (3 - 2 * d) // 1 at the rim → 0 inside
      heights[k] = light[k] + (heavy[k] - light[k]) * w
    }
  }
  const hMean = heights.reduce((a, b) => a + b, 0) / heights.length
  for (let k = 0; k < heights.length; k++) {
    pos[k * 3 + 1] = ((heights[k] - hMean) / 1000) * V_EXAG
  }
  const idx: number[] = []
  for (let j = 0; j < N; j++) {
    for (let i = 0; i < N; i++) {
      const a = j * (N + 1) + i
      const b = a + 1
      const c = a + N + 1
      const d = c + 1
      idx.push(a, c, b, b, c, d)
    }
  }
  const top = new THREE.BufferGeometry()
  top.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3))
  top.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2))
  top.setIndex(idx)
  top.computeVertexNormals()
  // Winding may face down depending on the corner order — normals tell.
  const n0 = top.getAttribute('normal')
  if (n0.getY(Math.floor(n0.count / 2)) < 0) {
    for (let k = 0; k < idx.length; k += 3) {
      const tmp = idx[k + 1]
      idx[k + 1] = idx[k + 2]
      idx[k + 2] = tmp
    }
    top.setIndex(idx)
    top.computeVertexNormals()
  }

  const texPre = placeholderTex(214, 226, 238)
  const texPost = placeholderTex(214, 226, 238)
  const texE = placeholderTex(214, 226, 238)
  const texV = placeholderTex(214, 226, 238)
  const uPre = { value: texPre as THREE.Texture }
  const uPost = { value: texPost as THREE.Texture }
  const uE = { value: texE as THREE.Texture }
  const uV = { value: texV as THREE.Texture }
  topMat = new THREE.ShaderMaterial({
    uniforms: {
      tPre: uPre,
      tPost: uPost,
      tE: uE,
      tV: uV,
      uPhase: { value: 0 },
      uLight: { value: new THREE.Vector3(0.9, 1.6, 1.1).normalize() },
    },
    vertexShader: `
      varying vec2 vUv;
      varying vec3 vN;
      void main() {
        vUv = uv;
        vN = normalize(normalMatrix * normal);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: `
      uniform sampler2D tPre, tPost, tE, tV;
      uniform float uPhase;
      uniform vec3 uLight;
      varying vec2 vUv;
      varying vec3 vN;
      vec3 face(int i) {
        if (i == 0) return texture2D(tPre, vUv).rgb;
        vec3 post = texture2D(tPost, vUv).rgb;
        if (i == 1) return post;
        vec4 s = (i == 2) ? texture2D(tE, vUv) : texture2D(tV, vUv);
        return mix(post, s.rgb, s.a * 0.92);
      }
      void main() {
        int i = int(floor(uPhase));
        float f = smoothstep(0.0, 1.0, fract(uPhase));
        int j = i + 1;
        if (j > 3) j = 0;
        vec3 c = mix(face(i), face(j), f);
        vec3 l = normalize((viewMatrix * vec4(uLight, 0.0)).xyz);
        float d = 0.42 + 0.7 * max(dot(normalize(vN), l), 0.0);
        gl_FragColor = vec4(c * d, 1.0);
      }`,
  })
  const topMesh = new THREE.Mesh(top, topMat)
  scene.add(topMesh)
  disposables.push(top, topMat, texPre, texPost, texE, texV)

  // Ice walls: each edge of the surface grid dropped to the slab base.
  // One flat plane per side — a single outward normal and outward
  // winding — so a wall shades as one sheet of ice (per-vertex normals
  // on a both-ways-wound strip striped it).
  const wpos: number[] = []
  const wnrm: number[] = []
  const widx: number[] = []
  const yBot = -SLAB_KM
  const edges: number[][] = [[], [], [], []]
  for (let i = 0; i <= N; i++) {
    edges[0].push(i) // j = 0
    edges[1].push(N * (N + 1) + i) // j = N
    edges[2].push(i * (N + 1)) // i = 0
    edges[3].push(i * (N + 1) + N) // i = N
  }
  for (const e of edges) {
    const base = wpos.length / 3
    const kA = e[0]
    const kB = e[e.length - 1]
    const ex = pos[kB * 3] - pos[kA * 3]
    const ez = pos[kB * 3 + 2] - pos[kA * 3 + 2]
    // Horizontal normal to the side, turned to face away from the centre.
    let nx = ez
    let nz = -ex
    const mx = (pos[kA * 3] + pos[kB * 3]) / 2
    const mz = (pos[kA * 3 + 2] + pos[kB * 3 + 2]) / 2
    if (nx * mx + nz * mz < 0) { nx = -nx; nz = -nz }
    const nl = Math.hypot(nx, nz) || 1
    nx /= nl
    nz /= nl
    for (const k of e) {
      wpos.push(pos[k * 3], pos[k * 3 + 1], pos[k * 3 + 2])
      wpos.push(pos[k * 3], yBot, pos[k * 3 + 2])
      wnrm.push(nx, 0, nz, nx, 0, nz)
    }
    // (top q, bottom q, top q+1) faces n when (−y) × edge · n > 0.
    const outward = (-ez) * nx + ex * nz > 0
    for (let q = 0; q < e.length - 1; q++) {
      const a = base + q * 2
      const b = a + 1
      const c = a + 2
      const d = a + 3
      if (outward) widx.push(a, b, c, b, d, c)
      else widx.push(a, c, b, b, c, d)
    }
  }
  const walls = new THREE.BufferGeometry()
  walls.setAttribute('position', new THREE.Float32BufferAttribute(wpos, 3))
  walls.setAttribute('normal', new THREE.Float32BufferAttribute(wnrm, 3))
  walls.setIndex(widx)
  // A little self-light keeps the walls turned from the key reading as
  // ice rather than slate.
  const wallMat = new THREE.MeshLambertMaterial({
    color: new THREE.Color(0.62, 0.74, 0.88),
    emissive: new THREE.Color(0.1, 0.13, 0.18),
  })
  scene.add(new THREE.Mesh(walls, wallMat))
  disposables.push(walls, wallMat)

  // The block's edges, drawn: the four rim polylines (following the
  // surface), the four vertical corner edges and the base rectangle —
  // dark, thin, so the block reads as one cut solid (the "edges" knob the
  // bed-thumb renders use, in miniature).
  const edgePts: number[] = []
  const pushSeg = (a: number[], b: number[]) => edgePts.push(...a, ...b)
  for (const e of edges) {
    for (let q = 0; q < e.length - 1; q++) {
      const k0 = e[q]
      const k1 = e[q + 1]
      pushSeg([pos[k0 * 3], pos[k0 * 3 + 1] + 0.01, pos[k0 * 3 + 2]], [pos[k1 * 3], pos[k1 * 3 + 1] + 0.01, pos[k1 * 3 + 2]])
    }
  }
  const cornerIdx = [0, N, N * (N + 1), N * (N + 1) + N]
  const cornerXZ = cornerIdx.map((k) => [pos[k * 3], pos[k * 3 + 2]] as [number, number])
  cornerIdx.forEach((k, ci) => {
    pushSeg([pos[k * 3], pos[k * 3 + 1], pos[k * 3 + 2]], [pos[k * 3], yBot, pos[k * 3 + 2]])
    const [x0, z0] = cornerXZ[ci]
    const [x1, z1] = cornerXZ[[1, 3, 0, 2][ci]] // base ring: 0→1→3→2→0
    pushSeg([x0, yBot, z0], [x1, yBot, z1])
  })
  const edgeGeo = new THREE.BufferGeometry()
  edgeGeo.setAttribute('position', new THREE.Float32BufferAttribute(edgePts, 3))
  const edgeMat = new THREE.LineBasicMaterial({ color: 0x1a1d24, transparent: true, opacity: 0.85 })
  scene.add(new THREE.LineSegments(edgeGeo, edgeMat))
  disposables.push(edgeGeo, edgeMat)

  loadTex('s2pre_512.jpg', uPre)
  loadTex('s2post_512.jpg', uPost)
  loadTex('e_512.png', uE)
  loadTex('v_512.png', uV)
}

function setSize() {
  if (!renderer || !canvas.value || !camera) return
  const r = canvas.value.getBoundingClientRect()
  const w = Math.max(2, r.width)
  const h = Math.max(2, r.height)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.setSize(w, h, false)
  camera.aspect = w / h
  camera.updateProjectionMatrix()
}

function animate(now: number) {
  if (!renderer || !scene || !camera) return
  const t = now - t0
  // Face cycle: hold, fade, hold, fade … (four faces).
  const step = HOLD_MS + FADE_MS
  const k = Math.floor(t / step) % 4
  const within = t % step
  const f = within < HOLD_MS ? 0 : (within - HOLD_MS) / FADE_MS
  if (topMat) topMat.uniforms.uPhase.value = k + f
  const lbl = FACES[f < 0.5 ? k : (k + 1) % 4]
  if (label.value !== lbl) label.value = lbl
  // The camera walks around the block; the block stays put (its light
  // is fixed to the world, so the relief keeps its shading).
  const az = (2 * Math.PI * t) / TURN_MS
  const el = (31 * Math.PI) / 180
  const d = 34
  camera.position.set(d * Math.cos(el) * Math.sin(az), d * Math.sin(el), d * Math.cos(el) * Math.cos(az))
  camera.lookAt(0, -0.6, 0)
  renderer.render(scene, camera)
  rafId = requestAnimationFrame(animate)
}

onMounted(() => {
  if (!canvas.value) return
  renderer = new THREE.WebGLRenderer({ canvas: canvas.value, antialias: true, alpha: true })
  renderer.setClearColor(0x000000, 0)
  scene = new THREE.Scene()
  camera = new THREE.PerspectiveCamera(26, 16 / 5, 1, 400)
  scene.add(new THREE.AmbientLight(0xffffff, 0.55))
  const key = new THREE.DirectionalLight(0xfff4dc, 1.4)
  key.position.set(0.9, 1.6, 1.1)
  scene.add(key)
  const fill = new THREE.DirectionalLight(0x9fb8ff, 0.5)
  fill.position.set(-1.2, 0.6, -1)
  scene.add(fill)
  setSize()
  ro = new ResizeObserver(setSize)
  ro.observe(canvas.value)
  t0 = performance.now()
  rafId = requestAnimationFrame(animate)
  loadDem().then((dem) => { if (!dead) buildBlock(dem) }).catch(() => {})
})

onBeforeUnmount(() => {
  dead = true
  cancelAnimationFrame(rafId)
  ro?.disconnect()
  ro = null
  for (const d of disposables) d.dispose()
  disposables = []
  renderer?.dispose()
  renderer = null
  scene = null
  camera = null
  topMat = null
})
</script>

<style scoped>
.pnas-stage {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 50% 40%, #121722 0%, #07080c 70%);
  overflow: hidden;
}

.pnas-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}

.pnas-label {
  position: absolute;
  top: 0.4rem;
  right: 0.55rem;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 0.6rem;
  letter-spacing: 0.04em;
  color: #f4cf6a;
  background: rgba(0, 0, 0, 0.55);
  padding: 0.1rem 0.4rem;
  border-radius: 3px;
  pointer-events: none;
}
</style>
