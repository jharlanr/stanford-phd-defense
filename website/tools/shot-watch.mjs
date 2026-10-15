// File-watcher loop around shot-grid. When any of the Ch.1-relevant
// source files change, re-run shot-grid and dump a fresh tiled PNG.
// Lets the agent iterate on framing/animation without manually
// re-snapping after every Edit.
//
// Usage:
//   node tools/shot-watch.mjs                                 # defaults
//   node tools/shot-watch.mjs --scenarios=introduction,ch1-beat2
//   node tools/shot-watch.mjs --out=/tmp/ch1-watch.png --debounceMs=600
//
// Pass-through args (--base, --scenarios, --cols, --out, --hud) are
// forwarded to shot-grid.mjs verbatim.

import { watch as fsWatch } from 'node:fs'
import { spawn } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SHOT_GRID = resolve(__dirname, 'shot-grid.mjs')
const WEBSITE_ROOT = resolve(__dirname, '..')

// Files the agent edits when iterating on Ch.1 visuals. Adding more
// here is cheap. Keep this list narrow — watching all of src/ is
// noisy because Vite HMR re-saves transformed files.
const WATCH_FILES = [
  'src/components/Globe.vue',
  'src/components/sections/SectionCh1.vue',
  'src/components/sections/SectionMotivation.vue',
].map(p => resolve(WEBSITE_ROOT, p))

function parseArgs(argv) {
  const out = []
  for (const a of argv) out.push(a) // pass-through verbatim
  return out
}

const passthrough = parseArgs(process.argv.slice(2))
const debounceMs = Number(
  passthrough.find(a => a.startsWith('--debounceMs='))?.split('=')[1] ?? 600,
)

let runId = 0
let pending = null
let inflight = false

function runShotGrid() {
  if (inflight) {
    // Another run is already going. Mark that we want a re-run when
    // it finishes so we don't lose intermediate edits.
    pending = true
    return
  }
  inflight = true
  const myId = ++runId
  const t0 = Date.now()
  console.log(`\n[watch ${myId}] running shot-grid…`)
  const child = spawn(
    process.execPath,
    [SHOT_GRID, ...passthrough.filter(a => !a.startsWith('--debounceMs'))],
    { cwd: WEBSITE_ROOT, stdio: 'inherit' },
  )
  child.on('exit', (code) => {
    const dt = ((Date.now() - t0) / 1000).toFixed(1)
    console.log(`[watch ${myId}] done in ${dt}s (exit ${code})`)
    inflight = false
    if (pending) {
      pending = false
      // Run again — debounce hit while previous shot was in-flight.
      setTimeout(runShotGrid, 50)
    }
  })
}

let debounceTimer = null
function schedule(file) {
  if (debounceTimer) clearTimeout(debounceTimer)
  console.log(`[watch] ${file} changed`)
  debounceTimer = setTimeout(() => {
    debounceTimer = null
    runShotGrid()
  }, debounceMs)
}

console.log('shot-watch — re-runs shot-grid on file change')
console.log(`debounce: ${debounceMs} ms`)
console.log('watching:')
for (const f of WATCH_FILES) {
  console.log(`  ${f}`)
  try {
    fsWatch(f, { persistent: true }, () => schedule(f))
  } catch (err) {
    console.error(`  (failed to watch: ${err.message})`)
  }
}

// Initial run so the agent sees the current state immediately without
// having to edit a file first.
runShotGrid()

// Keep the process alive forever — fs.watch handles do that on their
// own, but be explicit so SIGINT works cleanly.
process.on('SIGINT', () => {
  console.log('\nshot-watch: stopping')
  process.exit(0)
})
