// Snap multiple scenarios in parallel and tile them into one labeled
// PNG so the agent (and the director) can see the whole flow at a glance.
//
// Why: when the user says "this looks bad", iterating one screenshot
// at a time is slow. A grid lets you compare ch1-beat1 against the
// introduction reference (or against ch1-beat0..1 across the chapter)
// in a single image without flipping between files.
//
// Usage:
//   node tools/shot-grid.mjs                              # default Ch.1 vs introduction
//   node tools/shot-grid.mjs --scenarios=introduction,ch1-beat1 --base=http://localhost:5173
//   node tools/shot-grid.mjs --scenarios=ch1-beat0,ch1-beat1 --out=/tmp/ch1-flow.png
//   node tools/shot-grid.mjs --cols=3                     # force grid columns
//   node tools/shot-grid.mjs --chapter=ch1                # auto: every ch1-beatN
//
// Scenarios are the same names as screenshot.mjs's SCENARIOS map.
//
// SIDECAR STATE DUMP: alongside <out>.png the tool also writes
// <out>.json with `{ scenarios: { name: <__dumpScene() output> } }`.
// Each cell in the grid PNG also overlays a small "state digest"
// card so visual scan + state inspection live in the same artifact.

import { chromium } from 'playwright'
import { writeFile } from 'node:fs/promises'

const DEFAULT_BASE = 'http://localhost:5173'
const DEFAULT_OUT  = '/tmp/shot-grid.png'
const DEFAULT_SCENARIOS = ['introduction', 'ch1-beat1']

// Mirror screenshot.mjs SCENARIOS so this tool is self-contained.
// Keep these two in sync if scenarios are added — short and rarely
// changes, so duplication is the lesser evil vs. wiring up a shared
// module under tools/.
const SCENARIOS = {
  intro:        { path: '/',                  settleMs: 1500 },
  menu:         { path: '/menu',              settleMs: 2500 },
  introduction: { path: '/introduction',      settleMs: 5000 },
  // 2-beat layout (velocity / streamline middle dropped):
  //   0 entry+beacon · 1 cross-section reveal (WIDE framing).
  'ch1-beat0':  { path: '/chapter1?beat=0',   settleMs: 2800 },
  'ch1-beat1':  { path: '/chapter1?beat=1',   settleMs: 5000 },
  // 16-beat arc (see SectionCh1). Settles cover the entry lerps.
  'ch1-beat2':  { path: '/chapter1?beat=2',   settleMs: 6000 },
  'ch1-beat3':  { path: '/chapter1?beat=3',   settleMs: 5000 },
  'ch1-beat4':  { path: '/chapter1?beat=4',   settleMs: 6500 },
  'ch1-beat5':  { path: '/chapter1?beat=5',   settleMs: 7000 },
  'ch1-beat7':  { path: '/chapter1?beat=7',   settleMs: 4500 },
  'ch1-beat9':  { path: '/chapter1?beat=9',   settleMs: 4500 },
  'ch1-beat11': { path: '/chapter1?beat=11',  settleMs: 4500 },
  'ch1-beat12': { path: '/chapter1?beat=12',  settleMs: 4500 },
  'ch1-beat13': { path: '/chapter1?beat=13',  settleMs: 6000 },
  'ch1-beat14': { path: '/chapter1?beat=14',  settleMs: 4500 },
  'ch1-beat15': { path: '/chapter1?beat=15',  settleMs: 6000 },
  extras:       { path: '/extras',            settleMs: 1500 },
}

// --chapter=<id> expands to every <id>-beatN scenario in SCENARIOS,
// in order. Lets the most common multi-scenario invocation —
// "show me the whole chapter" — drop to a single flag.
function expandChapter(chapterId) {
  const prefix = `${chapterId}-beat`
  return Object.keys(SCENARIOS)
    .filter((k) => k.startsWith(prefix))
    .sort((a, b) => {
      const an = Number(a.slice(prefix.length))
      const bn = Number(b.slice(prefix.length))
      return an - bn
    })
}

const TILE_W = 1440
const TILE_H = 900

function parseArgs(argv) {
  const out = {}
  for (const a of argv) {
    if (a.startsWith('--')) {
      const [k, v = 'true'] = a.slice(2).split('=')
      out[k] = v
    }
  }
  return out
}

function buildUrl(base, scenario, opts = {}) {
  const baseWithSlash = base.endsWith('/') ? base : base + '/'
  const path = scenario.path.startsWith('/') ? scenario.path.slice(1) : scenario.path
  let url = `${baseWithSlash}${path}`
  if (opts.hud) {
    // Append debug=cam so Globe.vue paints the camera-state HUD into
    // each tile. Preserves any existing query params.
    url += url.includes('?') ? '&debug=cam' : '?debug=cam'
  }
  return url
}

const args = parseArgs(process.argv.slice(2))
const base = args.base || DEFAULT_BASE
const out  = args.out  || DEFAULT_OUT
// --chapter=ch1 overrides --scenarios. Useful for the common
// "snap the whole chapter" case without listing each beat by hand.
const chapterExpanded = args.chapter ? expandChapter(args.chapter) : null
if (args.chapter && chapterExpanded.length === 0) {
  console.error(`--chapter=${args.chapter} matched no scenarios; known: ${Object.keys(SCENARIOS).join(', ')}`)
  process.exit(1)
}
const names = chapterExpanded
  ?? (args.scenarios || DEFAULT_SCENARIOS.join(',')).split(',').map(s => s.trim()).filter(Boolean)
// --hud (default on) appends ?debug=cam to every scenario URL so each
// tile shows the camera-state HUD. Pass --hud=false to disable.
const hud = args.hud !== 'false'

for (const n of names) {
  if (!SCENARIOS[n]) {
    console.error(`unknown scenario "${n}". known: ${Object.keys(SCENARIOS).join(', ')}`)
    process.exit(1)
  }
}

const cols = args.cols ? Number(args.cols) : Math.min(names.length, 2)
const rows = Math.ceil(names.length / cols)

console.log(`base:      ${base}`)
console.log(`out:       ${out}`)
console.log(`scenarios: ${names.join(', ')}`)
console.log(`grid:      ${cols} × ${rows} (${TILE_W * cols} × ${TILE_H * rows} px)`)

const browser = await chromium.launch({
  // Match screenshot.mjs — local-dev R2 textures need CORS bypass.
  args: ['--disable-web-security'],
})

async function snapOne(name) {
  const s = SCENARIOS[name]
  const ctx = await browser.newContext({ viewport: { width: TILE_W, height: TILE_H } })
  const page = await ctx.newPage()
  const consoleErrors = []
  page.on('console',   (m)   => {
    if (m.type() === 'error') consoleErrors.push(m.text())
    // Surface our own debug logs (anything starting with '[') to stdout
    // so chapter-lerp tracing is visible without launching a browser.
    else if (m.text().startsWith('[')) console.log(`    [${name}] ${m.text()}`)
  })
  page.on('pageerror', (err) => consoleErrors.push(`PAGE ERROR: ${err.message}`))
  const url = buildUrl(base, s, { hud })
  // 'domcontentloaded' (not 'networkidle' or 'load'): Three.js's
  // per-frame rAF, HMR websocket chatter, and occasional slow R2
  // texture loads all starve both alternatives. DOM-content fires the
  // moment the script tags begin executing; settleMs is what we
  // actually rely on for "Three.js has rendered the settled state".
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 })
  // Texture-readiness gate (see screenshot.mjs): wait for Globe.vue's
  // pending-texture count to reach zero so settleMs only covers lerps.
  await page
    .waitForFunction(
      () => window.__texturesStarted > 0 && window.__texturesPending === 0,
      undefined,  // Playwright arg slot — options come third
      { timeout: 240000, polling: 250 },
    )
    .catch(() => console.warn(`[${name}] texture gate timed out — snapping anyway`))
  await page.waitForTimeout(s.settleMs ?? 2000)

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
  const captured = await page.evaluate(async () => {
    await new Promise(requestAnimationFrame)
    const c = document.querySelector('canvas')
    const dataUrl = c ? c.toDataURL('image/png') : ''
    // Mirror of camHud, populated by Globe.vue when ?debug=cam is on.
    const hud = (window).__camHud || null
    // Full structured scene state — overlays, shader uniforms, lerps.
    // Captured in the same evaluate as the toDataURL call so the PNG
    // and the JSON describe the same frame.
    const state = typeof window.__dumpScene === 'function'
      ? window.__dumpScene()
      : null
    return { dataUrl, hud, state }
  })
  await ctx.close()
  if (!captured.dataUrl) {
    console.warn(`  ${name}: no canvas found`)
    return { name, dataUrl: '', hud: null, state: null, errors: consoleErrors }
  }
  console.log(`  ${name}: snapped${captured.hud ? ' +hud' : ''}${captured.state ? ' +state' : ''}${consoleErrors.length ? ` (${consoleErrors.length} err)` : ''}`)
  return { name, dataUrl: captured.dataUrl, hud: captured.hud, state: captured.state, errors: consoleErrors }
}

// Serialize the snaps. Vite's dev server chokes on parallel ESM
// module-graph requests from 5 fresh page loads at once and starves
// page.goto past its timeout. Sequential is ~5 × 6 s = 30 s — fast
// enough, and reliable.
const t0 = Date.now()
const results = []
for (const n of names) {
  results.push(await snapOne(n))
}
console.log(`snapped ${names.length} scenarios in ${((Date.now() - t0) / 1000).toFixed(1)}s`)

// Compose. One full-bleed page with a CSS grid; each cell holds the
// tile + a small label badge. Then snapshot the page.
const composer = await browser.newContext({ viewport: { width: TILE_W * cols, height: TILE_H * rows } })
const composerPage = await composer.newPage()

function hudHtml(hud) {
  if (!hud) return ''
  const f = (n, d = 2) => Number(n).toFixed(d)
  return `<div class="cam-hud">
    <div><span>lat</span>${f(hud.latDeg)}°</div>
    <div><span>lon</span>${f(hud.lonDeg)}°</div>
    <div><span>dist</span>${f(hud.distWorld, 3)} <em>×R</em></div>
    <div><span>dist</span>${f(hud.distApi, 3)} <em>API</em></div>
    <div><span>fov</span>${f(hud.fov, 1)}°</div>
    <div><span>focal</span>(${f(hud.focalLatDeg)}°, ${f(hud.focalLonDeg)}°)</div>
  </div>`
}

function stateHtml(state) {
  if (!state) return ''
  // One row per "is this part of the scene doing something?" question.
  // Keep it terse — the JSON sidecar carries the full structure; this
  // card is the quick "what's on screen" digest for the eye.
  const lines = []
  lines.push(`<div><span>phase</span>${state.phase}</div>`)
  if (state.exag) lines.push(`<div><span>exag</span>${state.exag.currentExag}${state.exag.lerping ? ' ↗' : ''}</div>`)
  if (state.cuts) {
    if (state.cuts.chapterCutLatDeg != null) {
      lines.push(`<div><span>cut</span>↑${state.cuts.chapterCutLatDeg}°</div>`)
    } else if (state.cuts.rollbackProgress != null && state.cuts.rollbackProgress > 0.005) {
      lines.push(`<div><span>cut</span>roll ${state.cuts.rollbackProgress}</div>`)
    }
  }
  const ov = state.overlays || {}
  if (ov.chapterSlab?.exists) lines.push(`<div><span>slab</span>op=${ov.chapterSlab.uOpacity} lat=${ov.chapterSlab.uCutLatDeg}°</div>`)
  if (ov.lakePolyBase?.exists) lines.push(`<div><span>lakes</span>op=${ov.lakePolyBase.opacity} (n=${ov.lakePolyBase.lakeCount})</div>`)
  if (ov.lakePolyHighlight?.exists && ov.lakePolyHighlight.highlightId) {
    lines.push(`<div><span>NL</span>op=${ov.lakePolyHighlight.opacity}</div>`)
  }
  if (ov.streamHiTube?.exists) lines.push(`<div><span>tube</span>${ov.streamHiTube.opacityCurrent}→${ov.streamHiTube.opacityTarget}</div>`)
  if (ov.crossSectionSlab?.exists && ov.crossSectionSlab.uOpacity > 0.01) {
    lines.push(`<div><span>xsec</span>op=${ov.crossSectionSlab.uOpacity}</div>`)
  }
  if (ov.scaleArrow?.exists && (ov.scaleArrow.opacity ?? 0) > 0.01) {
    lines.push(`<div><span>arrow</span>op=${ov.scaleArrow.opacity}</div>`)
  }
  return `<div class="state-card">${lines.join('')}</div>`
}

const cellHtml = results.map((r) => `
  <div class="cell">
    ${r.dataUrl
      ? `<img src="${r.dataUrl}" />`
      : `<div class="missing">no canvas (${r.errors.length} err)</div>`}
    <div class="label">${r.name}</div>
    ${hudHtml(r.hud)}
    ${stateHtml(r.state)}
  </div>
`).join('')

await composerPage.setContent(`<!doctype html>
<html><head><style>
  html, body { margin: 0; padding: 0; background: #000; }
  .grid {
    display: grid;
    grid-template-columns: repeat(${cols}, ${TILE_W}px);
    grid-auto-rows: ${TILE_H}px;
    gap: 0;
  }
  .cell { position: relative; width: ${TILE_W}px; height: ${TILE_H}px; overflow: hidden; }
  .cell img { width: 100%; height: 100%; display: block; }
  .missing {
    width: 100%; height: 100%;
    display: flex; align-items: center; justify-content: center;
    color: #f99; font: 18px ui-monospace, monospace; background: #1a0808;
  }
  .label {
    position: absolute; top: 12px; left: 12px;
    font: 600 14px ui-monospace, monospace;
    color: #fff;
    background: rgba(0,0,0,0.65);
    padding: 6px 10px;
    border-radius: 4px;
    letter-spacing: 0.04em;
  }
  /* Mirror of Globe.vue .cam-hud — re-rendered here because
     canvas.toDataURL doesn't capture HTML overlays. */
  .cam-hud {
    position: absolute; top: 12px; right: 12px;
    padding: 10px 14px;
    background: rgba(0,0,0,0.78);
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 6px;
    color: #fff;
    font: 600 12px/1.4 ui-monospace, monospace;
    letter-spacing: 0.02em;
  }
  .cam-hud div { display: grid; grid-template-columns: 38px 1fr; gap: 0 8px; }
  .cam-hud span { color: #f5c75e; font-weight: 500; }
  .cam-hud em { font-style: normal; opacity: 0.55; font-size: 10px; margin-left: 2px; }
  /* State-digest card: bottom-left, mirrors the JSON sidecar's most
     important fields so an eye-scan of the grid answers the same
     questions the JSON would. */
  .state-card {
    position: absolute; bottom: 12px; left: 12px;
    padding: 10px 14px;
    background: rgba(0,0,0,0.78);
    border: 1px solid rgba(245,199,94,0.30);
    border-radius: 6px;
    color: #fff;
    font: 600 12px/1.4 ui-monospace, monospace;
    letter-spacing: 0.02em;
    max-width: 320px;
  }
  .state-card div { display: grid; grid-template-columns: 52px 1fr; gap: 0 8px; }
  .state-card span { color: #f5c75e; font-weight: 500; }
</style></head>
<body><div class="grid">${cellHtml}</div></body></html>`)

// Wait for all <img> loads to finish — data URLs decode async.
await composerPage.evaluate(async () => {
  const imgs = Array.from(document.images)
  await Promise.all(imgs.map(img => img.complete ? null : new Promise(r => img.onload = img.onerror = r)))
})

await composerPage.screenshot({ path: out, fullPage: true })
await browser.close()

// Sidecar JSON keyed by scenario name. Writers of one-off audits can
// diff or inspect just the bit they care about; a future regression
// suite can assert specific cells (e.g. "ch1-beat4 must have slab
// uOpacity > 0 and chapter-cut active at lat ~68.6°").
const jsonOut = out.replace(/\.png$/i, '') + '.json'
const stateDump = { generatedAt: new Date().toISOString(), base, scenarios: {} }
for (const r of results) {
  stateDump.scenarios[r.name] = r.state ?? null
}
await writeFile(jsonOut, JSON.stringify(stateDump, null, 2))

console.log(`\nsaved ${out}`)
console.log(`saved ${jsonOut}`)
const totalErr = results.reduce((a, r) => a + r.errors.length, 0)
if (totalErr) {
  console.log(`\n${totalErr} console error(s) across all scenarios:`)
  for (const r of results) {
    if (r.errors.length) {
      console.log(`  [${r.name}]`)
      r.errors.forEach(e => console.log(`    - ${e}`))
    }
  }
} else {
  console.log('no console errors')
}
