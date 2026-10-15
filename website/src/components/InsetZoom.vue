<template>
  <!-- SVG expander overlay covering the whole viewport. The two
       <line> elements — and the stack's own position — are updated
       IMPERATIVELY inside the rAF loop (no Vue reactivity) so they
       track the projected arrow tips with zero frame lag — Vue's async
       tick was producing visible jitter when the user OrbitControls-
       rotated the main scene. -->
  <svg
    ref="svgRef"
    class="inset-expander"
    :width="viewportW"
    :height="viewportH"
    :style="{ opacity: placed ? insetOpacity : 0 }"
  >
    <line
      ref="lineTopRef"
      stroke="rgba(244, 207, 106, 0.95)"
      stroke-width="2"
      stroke-dasharray="6 5"
    />
    <line
      ref="lineBottomRef"
      stroke="rgba(244, 207, 106, 0.95)"
      stroke-width="2"
      stroke-dasharray="6 5"
    />
  </svg>

  <div ref="rootRef" class="inset-zoom" :style="{ opacity: placed ? insetOpacity : 0 }">
    <div class="inset-frame">
      <canvas ref="canvasRef"></canvas>
    </div>
    <div class="inset-caption">
      <div class="inset-title">≈ 3,400 m</div>
      <div class="inset-sub">≈ 10 × Salesforce Tower</div>
    </div>
  </div>
</template>

<script setup lang="ts">
// Inset 3D zoom window paired with the bronze scale arrow on Greenland's
// cross-section. Renders a stack of 10 procedural Salesforce Towers (the
// director chose the Salesforce Tower in San Francisco as the comparison
// rather than One World Trade: at 326 m tall, the ice column is about ten
// Salesforce Towers; the thickness itself is BedMachine
// v6's maximum, 3,413 m at 71.5°N 36.5°W on the slide's cut longitude —
// the old "≈ 3,200 m · 6 × One World Trade Center" undershot it).
// Audience reads: "the height of Greenland's ice column = this pile of
// buildings". Has its own canvas / WebGLRenderer / Scene so its camera and
// lighting are independent of the main globe.
//
// Procedural Salesforce Tower (see makeTower): the tapering rounded-square
// obelisk with its vertical fins, the set-back glass top floors and the
// rounded perforated crown; 326 m to the crown's top. Real heights exact;
// the plan is exaggerated 4× so the towers read at the inset's canvas.

import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'

const props = defineProps<{
  // 0–1, drives opacity. Inset fades in over the same window as the
  // bronze arrow (last 12% of the cut sweep).
  progress: number
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const rootRef = ref<HTMLDivElement | null>(null)
// Imperative refs to the SVG line elements — we set x1/y1/x2/y2
// directly in animate() to avoid Vue's async reactive update loop
// adding a frame of latency (visible as line "jitter" when the user
// rotates the camera).
const svgRef = ref<SVGSVGElement | null>(null)
const lineTopRef = ref<SVGLineElement | null>(null)
const lineBottomRef = ref<SVGLineElement | null>(null)

const insetOpacity = computed(() =>
  Math.max(0, Math.min(1, (props.progress - 0.88) / 0.12))
)
// False until the stack has been parked beside the arrow once (it would
// otherwise flash at the viewport's top-left corner on its first frame).
const placed = ref(false)

// Where the stack stands (the director found the towers too far from the
// slice in the first layout): right beside the cut face, tracking
// the gold scale arrow the Globe projects every frame (__arrowScreenPos),
// so the ties to the arrow stay short at every viewport width — it used
// to be pinned to the viewport's bottom-right corner, ~700 px from the
// slice on a wide screen. The object's on-screen size scales with the
// viewport HEIGHT (fixed vertical fov), so the offsets are in vh:
//   · the stack's axis sits STACK_AXIS_VH × vh right of the arrow — past
//     the cut face's east end with a clear gap before the towers;
//   · its spire tip sits level with the arrow's top, so the upper tie runs
//     flat and short, the lower one down to the stack's foot.
// Clamped on screen: right margin 2.5vw (as before), below the site's
// pills, above the bottom-right [references] link.
const STACK_AXIS_VH = 0.13
const RIGHT_MARGIN_VW = 0.025
const TOP_MIN_VH = 0.12
const BOTTOM_MIN_VH = 0.065

// Reactive viewport dims for the SVG outer width/height (these change
// rarely — fine for Vue reactivity).
const viewportW = ref(window.innerWidth)
const viewportH = ref(window.innerHeight)

// Salesforce Tower (San Francisco): 326 m to the top of the crown. The
// glass body rises to ~290 m; the top floors step in slightly and the
// perforated-aluminium crown rounds off the last ~30 m. Plan: a rounded
// square ~56 m across at the street tapering to ~44 m; drawn 4× wider
// (the radii below) so the towers read at the inset's small canvas.
const TOWER_BODY_H = 288      // m — the glass body, street to the top floors
const TOWER_TOPFL_H = 10      // m — the set-back top floors under the crown
const TOWER_CROWN_H = 28      // m — the rounded crown → 326 m total
const TOWER_HEIGHT = TOWER_BODY_H + TOWER_TOPFL_H + TOWER_CROWN_H
const BODY_BASE_R = 112       // 4 × ~28 m
const BODY_TOP_R = 90         // 4 × ~22.5 m
const FIN_COUNT = 16          // the vertical fins around the body

const STACK_COUNT = 10
const STACK_HEIGHT = STACK_COUNT * TOWER_HEIGHT

let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let renderer: THREE.WebGLRenderer | null = null
let animationId = 0

/** The body's silhouette as a lathe profile (radius, height): a rounded
 *  square reads as a circle at this size, so a straight taper. */
function bodyProfile(): THREE.Vector2[] {
  const pts: THREE.Vector2[] = []
  for (let k = 0; k <= 8; k++) {
    const t = k / 8
    pts.push(new THREE.Vector2(BODY_BASE_R + (BODY_TOP_R - BODY_BASE_R) * t, TOWER_BODY_H * t))
  }
  return pts
}
/** The crown: a shoulder that rounds over to the centre (a quarter ellipse). */
function crownProfile(r0: number): THREE.Vector2[] {
  const pts: THREE.Vector2[] = [new THREE.Vector2(r0, 0)]
  for (let k = 0; k <= 16; k++) {
    const a = (k / 16) * (Math.PI / 2)
    pts.push(new THREE.Vector2(r0 * Math.cos(a), TOWER_CROWN_H * Math.sin(a)))
  }
  return pts
}

function makeTower(tierIndex: number): THREE.Group {
  // The Salesforce Tower cartoon, four parts:
  //   1. Body   — the tapering obelisk of pale blue-grey glass
  //   2. Fins   — FIN_COUNT vertical mullions, the tower's signature ribbing
  //   3. Top floors — a short set-back glass drum under the crown
  //   4. Crown  — the rounded perforated cap, lighter and a touch translucent
  const tower = new THREE.Group()
  // Subtle per-tier tint variation so individual buildings remain
  // distinguishable in the stack.
  const isEven = tierIndex % 2 === 0
  const glassColour = isEven ? 0xb9cde0 : 0x9ab3ca
  const finColour = isEven ? 0xf0f4f7 : 0xd6dde3
  const crownColour = isEven ? 0xf2f5f8 : 0xdde3e8

  // Low metalness: a metallic standard material has nothing to reflect
  // here (no environment map) and went near-black at the inset's size.
  const glass = new THREE.MeshStandardMaterial({
    color: glassColour,
    metalness: 0.15,
    roughness: 0.38,
    emissive: 0x2b3a4a,
    emissiveIntensity: 0.5,
  })
  const body = new THREE.Mesh(new THREE.LatheGeometry(bodyProfile(), 48), glass)
  tower.add(body)

  // 2. Fins: thin vertical boxes standing proud of the glass, following
  // the taper (each a slim tapered lathe would be heavier; a box leaning
  // inward by the taper angle reads the same).
  const finMat = new THREE.MeshStandardMaterial({ color: finColour, metalness: 0.2, roughness: 0.45, emissive: 0x3a4048, emissiveIntensity: 0.35 })
  const taper = Math.atan2(BODY_BASE_R - BODY_TOP_R, TOWER_BODY_H)
  const finLen = TOWER_BODY_H / Math.cos(taper)
  const rMid = (BODY_BASE_R + BODY_TOP_R) / 2
  for (let f = 0; f < FIN_COUNT; f++) {
    const a = (f / FIN_COUNT) * Math.PI * 2
    const fin = new THREE.Mesh(new THREE.BoxGeometry(4.5, finLen, 7), finMat)
    const pivot = new THREE.Group()
    fin.position.set(rMid + 2.5, TOWER_BODY_H / 2, 0)
    fin.rotation.z = taper
    pivot.add(fin)
    pivot.rotation.y = a
    tower.add(pivot)
  }

  // 3. Top floors — set back from the body's top edge.
  const topR = BODY_TOP_R * 0.9
  const topFloors = new THREE.Mesh(new THREE.CylinderGeometry(topR * 0.985, topR, TOWER_TOPFL_H, 48), glass)
  topFloors.position.y = TOWER_BODY_H + TOWER_TOPFL_H / 2
  tower.add(topFloors)

  // 4. Crown.
  const crown = new THREE.Mesh(
    new THREE.LatheGeometry(crownProfile(topR * 0.985), 48),
    new THREE.MeshStandardMaterial({
      color: crownColour,
      metalness: 0.1,
      roughness: 0.5,
      emissive: 0x4a5058,
      emissiveIntensity: 0.45,
      transparent: true,
      opacity: 0.94,
    }),
  )
  crown.position.y = TOWER_BODY_H + TOWER_TOPFL_H
  tower.add(crown)

  // a thin dark reveal at the foot so the pile reads as ten buildings
  const seam = new THREE.Mesh(
    new THREE.CylinderGeometry(BODY_BASE_R * 1.03, BODY_BASE_R * 1.03, 3, 48),
    new THREE.MeshStandardMaterial({ color: 0x2a2e36, metalness: 0.3, roughness: 0.7 }),
  )
  seam.position.y = 1.5
  tower.add(seam)
  return tower
}

function makeStack(): THREE.Group {
  const stack = new THREE.Group()
  stack.name = 'tower-stack'  // animate() uses this for slow rotation
  for (let i = 0; i < STACK_COUNT; i++) {
    const t = makeTower(i)
    t.position.y = i * TOWER_HEIGHT
    stack.add(t)
  }
  return stack
}

function init(): void {
  if (!canvasRef.value) return
  const canvas = canvasRef.value
  const w = canvas.clientWidth || 280
  const h = canvas.clientHeight || 460

  scene = new THREE.Scene()
  // Wider FOV + greater distance so all 10 towers fit comfortably in the
  // portrait-oriented inset canvas. With STACK_HEIGHT = 3,260 m and
  // canvas aspect ≈ 0.50, camDist of 1.4 × stack height + FOV 42° gives
  // the whole stack in view with a small margin.
  camera = new THREE.PerspectiveCamera(42, w / h, 1, 30000)
  const camDist = STACK_HEIGHT * 1.4
  // Slightly oblique angle (a hint of perspective on the 3D forms)
  // without being so oblique that the stack looks foreshortened.
  camera.position.set(camDist * 0.32, STACK_HEIGHT * 0.50, camDist * 0.95)
  camera.lookAt(0, STACK_HEIGHT * 0.50, 0)

  renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: true,
  })
  const targetPR = Math.min(3, Math.max(2, window.devicePixelRatio || 1))
  renderer.setPixelRatio(targetPR)
  renderer.setSize(w, h, false)
  renderer.setClearColor(0x000000, 0)

  // Lighting: warm sun (key, upper-left), cool fill (right), plus a
  // sky-vs-ground hemisphere light so the blue glass picks up a
  // believable sky-blue reflection on its lit faces and a darker
  // "ground" tint on its lower faces. Matches the way the real tower
  // photographs against an open sky.
  const sun = new THREE.DirectionalLight(0xfff4e0, 2.2)
  sun.position.set(-STACK_HEIGHT * 1.2, STACK_HEIGHT * 1.6, STACK_HEIGHT * 0.7)
  scene.add(sun)
  const fill = new THREE.DirectionalLight(0xc4dcf5, 0.9)
  fill.position.set(STACK_HEIGHT * 1.4, STACK_HEIGHT * 0.4, -STACK_HEIGHT * 0.3)
  scene.add(fill)
  scene.add(new THREE.HemisphereLight(0xb6d4ee, 0x2a2e36, 0.65))

  // The stack itself.
  const stack = makeStack()
  scene.add(stack)

  animate()
}

// Reusable temp vectors for stack-tip projection (avoid GC churn).
const _stackTipBottom = new THREE.Vector3()
const _stackTipTop = new THREE.Vector3()

// The inset shows on the dims step only, but it stays mounted through the
// whole Introduction — and drew its own antialiased 2×-DPR WebGL frame
// every frame of every step, invisible, beside the Globe and the clips
// (found in a performance pass). While it is invisible it neither draws nor
// spins, so the canvas still holds exactly the frame it would draw when
// the fade-in starts. HIDE_GRACE_MS outlasts the 0.4 s CSS fade-out.
const HIDE_GRACE_MS = 700
let liveUntil = 0

function animate(): void {
  animationId = requestAnimationFrame(animate)
  const now = performance.now()
  if (!placed.value || insetOpacity.value > 0) liveUntil = now + HIDE_GRACE_MS
  const live = now < liveUntil
  if (live && renderer && scene && camera) {
    renderer.render(scene, camera)
  }

  // Slow rotation of the tower stack so the audience sees its 3D form
  // (the director asked for a very slow rotation of the stack).
  if (live && scene) {
    const stack = scene.getObjectByName('tower-stack')
    if (stack) stack.rotation.y += 0.003  // ≈ 0.18°/frame at 60fps
  }

  // Park the stack beside the arrow, then tie the arrow's tips to the
  // stack's (the stack's actual top and bottom, not the canvas frame).
  // The Globe's loop ran first this frame, so the arrow is current.
  const arrow = (window as any).__arrowScreenPos as
    | { topX: number; topY: number; bottomX: number; bottomY: number }
    | undefined
  const root = rootRef.value
  const canvas = canvasRef.value
  if (!arrow || !root || !canvas || !camera) return
  const vw = window.innerWidth
  const vh = window.innerHeight
  const cw = canvas.clientWidth
  const ch = canvas.clientHeight
  // The stack's tips in canvas px (the canvas is the root's first box).
  _stackTipBottom.set(0, 0, 0).project(camera)
  _stackTipTop.set(0, STACK_HEIGHT, 0).project(camera)
  const tipTopX = (_stackTipTop.x + 1) * 0.5 * cw
  const tipTopY = (1 - _stackTipTop.y) * 0.5 * ch
  const tipBotX = (_stackTipBottom.x + 1) * 0.5 * cw
  const tipBotY = (1 - _stackTipBottom.y) * 0.5 * ch
  let x = Math.max(arrow.topX, arrow.bottomX) + STACK_AXIS_VH * vh - tipTopX
  let y = arrow.topY - tipTopY
  x = Math.min(x, vw * (1 - RIGHT_MARGIN_VW) - root.offsetWidth)
  y = Math.max(TOP_MIN_VH * vh, Math.min(y, vh * (1 - BOTTOM_MIN_VH) - root.offsetHeight))
  root.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`
  if (!placed.value) placed.value = true
  const lt = lineTopRef.value
  const lb = lineBottomRef.value
  if (lt && lb) {
    lt.setAttribute('x1', arrow.topX.toFixed(1))
    lt.setAttribute('y1', arrow.topY.toFixed(1))
    lt.setAttribute('x2', (x + tipTopX).toFixed(1))
    lt.setAttribute('y2', (y + tipTopY).toFixed(1))
    lb.setAttribute('x1', arrow.bottomX.toFixed(1))
    lb.setAttribute('y1', arrow.bottomY.toFixed(1))
    lb.setAttribute('x2', (x + tipBotX).toFixed(1))
    lb.setAttribute('y2', (y + tipBotY).toFixed(1))
  }
}

function onResize(): void {
  viewportW.value = window.innerWidth
  viewportH.value = window.innerHeight
}

// The inset's own WebGL context + first frame cost ~200 ms of main
// thread on mount — felt as a hitch at the menu → Introduction click.
// It is not seen until the dims step's peel-back, so build
// it once the flight has landed (INIT_DELAY_MS) or on first need.
const INIT_DELAY_MS = 1800
let initTimer: number | null = null
onMounted(() => {
  initTimer = window.setTimeout(() => {
    initTimer = null
    if (!renderer) init()
  }, INIT_DELAY_MS)
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  if (initTimer !== null) window.clearTimeout(initTimer)
  if (animationId) cancelAnimationFrame(animationId)
  renderer?.dispose()
  renderer = null
  scene = null
  camera = null
  window.removeEventListener('resize', onResize)
})

// Re-init if the prop changes meaningfully (rare; mostly opacity changes
// don't need re-init).
watch(canvasRef, (c) => {
  if (c && !renderer && initTimer === null) init()
})
</script>

<style scoped>
.inset-expander {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
  z-index: 7;
  transition: opacity 0.4s;
}

.inset-zoom {
  position: absolute;
  /* Beside the cut face: animate() translates it next to the scale
     arrow every frame (STACK_AXIS_VH above). */
  left: 0;
  top: 0;
  will-change: transform;
  width: 180px;
  pointer-events: none;
  transition: opacity 0.4s;
  z-index: 8;
}

/* No bordered frame — just a soft radial glow that "gently
   distinguishes" the tower stack from the dark background, per the
   director's note that the inset doesn't have to be a box. closest-side: the glow
   dies out INSIDE the box, so no edge shows where the box now overlaps
   the ice beside the cut face. */
.inset-frame {
  width: 180px;
  height: 360px;
  background: radial-gradient(
    closest-side,
    rgba(20, 32, 56, 0.55) 0%,
    rgba(8, 14, 28, 0.30) 55%,
    rgba(0, 0, 0, 0) 95%
  );
  overflow: visible;
}

.inset-frame canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.inset-caption {
  text-align: center;
  /* Wider than the 180 px stack so the sub line wraps less at its
     projector size (the projector contrast pass). */
  margin: 0.6rem -50px 0;
  font-family: 'Inter', system-ui, sans-serif;
  text-shadow: 0 1px 12px rgba(0, 0, 0, 0.7);
}

.inset-title {
  font-family: 'EB Garamond', serif;
  font-size: 1.45rem;
  color: var(--gold-bright);
  letter-spacing: 0.02em;
}

.inset-sub {
  font-size: 1rem;
  font-weight: 500;
  color: var(--gold-bright);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-top: 0.15rem;
}
</style>
