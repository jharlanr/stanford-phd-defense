// Take a screenshot of the site so the coding agent can see what the user
// is seeing. Two ways to invoke:
//
//   1. URL form (raw):
//        node tools/screenshot.mjs                         # live site root
//        node tools/screenshot.mjs http://localhost:5173   # local dev
//        node tools/screenshot.mjs <url> <out.png>
//
//   2. Scenario form (named, navigates UI deep-link):
//        node tools/screenshot.mjs --scenario=ch1-beat0
//        node tools/screenshot.mjs --scenario=introduction --base=http://localhost:5173
//        node tools/screenshot.mjs --scenario=ch1-beat2 --out=/tmp/foo.png
//
// Output is overwritten each run — single file, no buildup. Browser
// binaries cache in ~/Library/Caches/ms-playwright/, not in node_modules.
//
// Adding a new scenario: add an entry to SCENARIOS below. Each scenario
// supplies `query` (URL query string), an optional `settleMs` override,
// and an optional `wait` callback for state-specific assertions.
//
// SIDECAR STATE DUMP: alongside <out>.png we also write <out>.json,
// a structured snapshot of every overlay's opacity, every shader
// uniform, the in-flight lerps, the camera pose, etc. — see
// Globe.vue's window.__dumpScene(). This lets an out-of-band reader
// (the agent, a test, a log scraper) answer "what's on screen?" without
// interpreting pixels.

import { chromium } from 'playwright'

const DEFAULT_BASE = 'https://jharlanr.github.io/stanford-phd-defense/'
const DEFAULT_OUT  = '/tmp/defense-site.png'

// Scenarios use the per-section history-mode routes from
// src/router/index.ts. Section beats stay on the URL as query params
// (SectionCh1 reads ?beat=N to jump straight to a beat).
//   /                   — intro splash (Greenland clickable)
//   /menu               — chapter menu
//   /<section-id>       — that section directly
//   /<section-id>?beat=N — jump to beat N inside a section
const SCENARIOS = {
  intro:        { path: '/',                  settleMs: 1500 },
  menu:         { path: '/menu',              settleMs: 2500 },
  introduction: { path: '/introduction',      settleMs: 5000 },
  // 2-beat layout (velocity / streamline middle dropped; the chapter
  // now jumps straight from beacon to cross-section):
  //   0 — entry (medium CW framing) + NL beacon
  //   1 — WIDE framing + south-to-NL knife reveal (REVEAL_MS = 3500 ms;
  //       needs the full lerp + a settle margin to land the slab).
  // 13-beat arc (see SectionCh1). Settles cover entry lerps
  // + in-stage animations (beat 5 = the depth-average wipe ~6 s).
  //   0-3 globe/slab · 4-11 theory stages 0-7 · 12 twin globes
  'ch1-beat0':  { path: '/chapter1?beat=0',   settleMs: 2800 },
  'ch1-beat1':  { path: '/chapter1?beat=1',   settleMs: 5000 },
  'ch1-beat2':  { path: '/chapter1?beat=2',   settleMs: 6000 },
  'ch1-beat3':  { path: '/chapter1?beat=3',   settleMs: 5000 },
  'ch1-beat4':  { path: '/chapter1?beat=4',   settleMs: 6500 },
  'ch1-beat5':  { path: '/chapter1?beat=5',   settleMs: 9000 },
  'ch1-beat6':  { path: '/chapter1?beat=6',   settleMs: 4500 },
  'ch1-beat7':  { path: '/chapter1?beat=7',   settleMs: 4500 },
  'ch1-beat8':  { path: '/chapter1?beat=8',   settleMs: 4500 },
  'ch1-beat9':  { path: '/chapter1?beat=9',   settleMs: 6000 },
  'ch1-beat10': { path: '/chapter1?beat=10',  settleMs: 6000 },
  'ch1-beat11': { path: '/chapter1?beat=11',  settleMs: 5500 },
  // Beat 12 = twin ACL + max-stress 3D globes (own texture loads).
  'ch1-beat12': { path: '/chapter1?beat=12',  settleMs: 9000 },
  extras:       { path: '/extras',            settleMs: 1500 },
}

function parseArgs(argv) {
  const out = { positional: [] }
  for (const a of argv) {
    if (a.startsWith('--')) {
      const [k, v = 'true'] = a.slice(2).split('=')
      out[k] = v
    } else {
      out.positional.push(a)
    }
  }
  return out
}

function buildUrl(base, scenario) {
  // History-mode routing: scenario.path is a clean URL like /chapter1.
  // Strip the leading '/' so it concatenates onto base's trailing '/'.
  const baseWithSlash = base.endsWith('/') ? base : base + '/'
  const path = scenario.path.startsWith('/') ? scenario.path.slice(1) : scenario.path
  return `${baseWithSlash}${path}`
}

const args = parseArgs(process.argv.slice(2))

let url
let out
let settleMs = 2000

if (args.scenario) {
  const s = SCENARIOS[args.scenario]
  if (!s) {
    console.error(`unknown scenario "${args.scenario}". known:`)
    for (const k of Object.keys(SCENARIOS)) console.error(`  - ${k}`)
    process.exit(1)
  }
  const base = args.base || DEFAULT_BASE
  url = buildUrl(base, s)
  out = args.out || DEFAULT_OUT
  settleMs = s.settleMs ?? settleMs
} else {
  url = args.positional[0] || DEFAULT_BASE
  out = args.positional[1] || DEFAULT_OUT
}

// CLI override always wins. Useful when a scenario's default isn't
// long enough for a specific lerp under inspection.
if (args.settleMs) {
  const n = Number(args.settleMs)
  if (Number.isFinite(n) && n >= 0) settleMs = n
}

console.log(`url:      ${url}`)
console.log(`out:      ${out}`)
console.log(`settleMs: ${settleMs}`)

// --disable-web-security so local-dev screenshots can load the R2
// textures via Three.js TextureLoader (which sets crossOrigin and
// triggers CORS). The R2 dev URL (pub-*.r2.dev) doesn't return
// Access-Control-Allow-Origin headers, so headless Chromium otherwise
// blocks bedmap / DEM / basemap PNGs and the canvas renders empty.
// Safe in this context — it's a one-shot screenshot tool, not a browser.
const browser = await chromium.launch({
  args: ['--disable-web-security'],
})
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
const page = await ctx.newPage()

const consoleErrors = []
page.on('console', (msg) => {
  if (msg.type() === 'error') consoleErrors.push(msg.text())
})
page.on('pageerror', (err) => consoleErrors.push(`PAGE ERROR: ${err.message}`))

import { writeFile } from 'node:fs/promises'

// 'domcontentloaded' (not 'networkidle' or 'load'): Three.js's
// per-frame rAF + Vite's HMR websocket + occasional slow R2 texture
// requests starve both. 'domcontentloaded' fires the moment the DOM
// is parsed and JS has begun running; settleMs covers Three.js warmup
// + camera lerps + texture loads, which is what we actually want.
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 })
// Texture-readiness gate: Globe.vue tracks every TextureLoader request
// in window.__texturesPending. Wait for the count to hit zero (all
// textures decoded + uploaded) BEFORE the settle, so settleMs only has
// to cover camera/opacity lerps — not the ~110 MB of basemap + DEM
// downloads, whose duration varies wildly between cold and warm runs.
// 240 s cap: the 75 MB hi-res basemap can take 25-90+ s to ingest
// in a busy headless process; a wedged loader still can't hang forever.
await page
  .waitForFunction(
    () => window.__texturesStarted > 0 && window.__texturesPending === 0,
    undefined,  // Playwright arg slot — options come third
    { timeout: 240000, polling: 250 },
  )
  .catch(() => console.warn('texture gate timed out — snapping anyway'))
// Give Vue / Three.js / scripted camera lerps a beat to settle before snapping.
await page.waitForTimeout(settleMs)

// Late-armed loads: a beat can create meshes AFTER the initial batch
// settles (e.g. Ch.1's deferred ACL drape), re-arming the pending
// counter during the settle. One more gate + short settle covers the
// texture + its fade-in.
const again = await page.evaluate(() => window.__texturesPending)
if (again > 0) {
  await page
    .waitForFunction(
      () => window.__texturesPending === 0,
      undefined,
      { timeout: 240000, polling: 250 },
    )
    .catch(() => console.warn('late texture gate timed out — snapping anyway'))
  await page.waitForTimeout(1500)
}

// Three.js's per-frame rAF makes Playwright's screenshot() stability
// check time out at close zoom. Pull the canvas pixels directly via
// toDataURL so we get a single frame regardless of what's animating.
// Webgl canvases need preserveDrawingBuffer=true OR a render call
// followed by an immediate readback in the same frame; toDataURL on
// the next rAF will be cleared. We invoke a render via
// requestAnimationFrame inside evaluate to ensure pixels are present.
//
// In the same evaluate we also call __dumpScene() (added by Globe.vue)
// so the PNG + state JSON describe the EXACT SAME frame — capturing
// them in separate evaluates risks a 16ms rAF tick between them where
// a lerp could move state.
const captured = await page.evaluate(async () => {
  await new Promise(requestAnimationFrame)
  const c = document.querySelector('canvas')
  const dataUrl = c ? c.toDataURL('image/png') : ''
  const state = typeof window.__dumpScene === 'function'
    ? window.__dumpScene()
    : null
  return { dataUrl, state }
})
if (captured.dataUrl) {
  const b64 = captured.dataUrl.replace(/^data:image\/png;base64,/, '')
  await writeFile(out, Buffer.from(b64, 'base64'))
} else {
  // Fallback for non-canvas pages (intro before WebGL initialises).
  await page.screenshot({ path: out, fullPage: false, timeout: 60000 })
}
// Sidecar state dump. Sibling JSON file at the same path with .json
// extension so screenshot tools that don't care about state can stay
// PNG-only, but anyone reasoning about "what's on screen" can read
// the JSON without re-loading the page.
const jsonOut = out.replace(/\.png$/i, '') + '.json'
if (captured.state) {
  await writeFile(jsonOut, JSON.stringify(captured.state, null, 2))
}

await browser.close()

console.log(`\nsaved ${out}`)
if (captured.state) {
  console.log(`saved ${jsonOut}`)
  // One-line state digest to stdout — the fields most useful for
  // "is the scene in the state I expected?".
  const s = captured.state
  const cut = s.cuts?.chapterCutLatDeg != null
    ? `cutLat=${s.cuts.chapterCutLatDeg}°`
    : s.cuts?.rollbackProgress != null && s.cuts.rollbackProgress > 0.01
      ? `rollback=${s.cuts.rollbackProgress}`
      : 'cut=off'
  const slab = s.overlays?.chapterSlab?.exists
    ? `slab(op=${s.overlays.chapterSlab.uOpacity}, lat=${s.overlays.chapterSlab.uCutLatDeg}°)`
    : 'slab=∅'
  const lakes = s.overlays?.lakePolyBase?.exists
    ? `lakes(op=${s.overlays.lakePolyBase.opacity}, n=${s.overlays.lakePolyBase.lakeCount})`
    : 'lakes=∅'
  const tube = s.overlays?.streamHiTube?.exists
    ? `tube(cur=${s.overlays.streamHiTube.opacityCurrent}→${s.overlays.streamHiTube.opacityTarget})`
    : 'tube=∅'
  console.log(`digest:   phase=${s.phase} exag=${s.exag?.currentExag} ${cut} | ${slab} | ${lakes} | ${tube}`)
} else {
  console.log('(no __dumpScene — pre-mount or older build)')
}
if (consoleErrors.length) {
  console.log(`\n${consoleErrors.length} console error(s):`)
  consoleErrors.forEach((e) => console.log(`  - ${e}`))
} else {
  console.log('no console errors')
}
