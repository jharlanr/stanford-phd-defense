// Fast iterative inspector. Keeps one Chromium browser warm and snaps
// arbitrary URLs on demand. Goal: ~3 s per snap instead of ~30 s with
// fresh `node tools/screenshot.mjs` (which pays Playwright launch +
// Vite-cold-cache + texture-load + settle costs every invocation).
//
// Two usage modes:
//
//   1. Daemon (recommended): start once, hit via HTTP from anywhere.
//        node tools/inspect.mjs --daemon
//      Then snap from any other terminal:
//        curl 'http://localhost:7171/snap?url=http://localhost:5173/&settle=3000&out=/tmp/now.png'
//      Returns the saved PNG path. Hot browser tab → ~2-3 s per snap.
//
//   2. Single-shot: legacy fallback if the daemon isn't running.
//        node tools/inspect.mjs http://localhost:5173/ --settle=3000 --out=/tmp/now.png
//      Same speed as screenshot.mjs — use the daemon for iteration.

import { chromium } from 'playwright'
import { writeFile } from 'node:fs/promises'
import http from 'node:http'
import { fileURLToPath } from 'node:url'

const DAEMON_PORT = 7171
const VIEWPORT = { width: 1440, height: 900 }

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

async function snapInPage(page, url, settleMs) {
  const consoleErrors = []
  const consoleLogs = []
  const onConsole = (m) => {
    const text = m.text()
    if (m.type() === 'error') consoleErrors.push(text)
    else if (text.startsWith('[')) consoleLogs.push(text)
  }
  const onPageError = (err) => consoleErrors.push(`PAGE ERROR: ${err.message}`)
  page.on('console', onConsole)
  page.on('pageerror', onPageError)
  try {
    // domcontentloaded (not 'load'): in a persistent SPA context, the
    // 'load' event only fires for the FIRST navigation. Subsequent
    // navigations are either pushState (no load event) or fire load
    // only on full-document swaps. domcontentloaded fires reliably on
    // every goto. settleMs covers post-DOM Three.js warmup.
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForTimeout(settleMs)
    const dataUrl = await page.evaluate(async () => {
      await new Promise(requestAnimationFrame)
      const c = document.querySelector('canvas')
      return c ? c.toDataURL('image/png') : ''
    })
    return { dataUrl, consoleErrors, consoleLogs }
  } finally {
    page.off('console', onConsole)
    page.off('pageerror', onPageError)
  }
}

async function runDaemon() {
  console.log('inspect daemon: launching Chromium…')
  // Stock-browser launch (no --disable-web-security). The dev server's
  // /r2/ proxy makes R2 textures same-origin, so we don't need CORS
  // bypass; and bypassing CORS was masking real bugs (textures that
  // loaded here but were refused on the live bucket).
  const browser = await chromium.launch()
  const context = await browser.newContext({ viewport: VIEWPORT })
  const page = await context.newPage()
  console.log(`inspect daemon: ready on http://localhost:${DAEMON_PORT}`)
  console.log('  GET /snap?url=...&settle=N&out=/path/out.png')
  console.log('  GET /quit')

  const server = http.createServer(async (req, res) => {
    const u = new URL(req.url, `http://localhost:${DAEMON_PORT}`)
    if (u.pathname === '/quit') {
      res.writeHead(200, { 'Content-Type': 'text/plain' })
      res.end('bye\n')
      setTimeout(async () => {
        await browser.close()
        process.exit(0)
      }, 50)
      return
    }
    if (u.pathname !== '/snap') {
      res.writeHead(404, { 'Content-Type': 'text/plain' })
      res.end('unknown\n')
      return
    }
    const url      = u.searchParams.get('url')    || 'http://localhost:5173/'
    const settleMs = Number(u.searchParams.get('settle') ?? 3000)
    const out      = u.searchParams.get('out')    || '/tmp/inspect.png'
    const t0 = Date.now()
    try {
      const result = await snapInPage(page, url, settleMs)
      if (!result.dataUrl) {
        res.writeHead(500, { 'Content-Type': 'text/plain' })
        res.end(`no canvas. errors=${result.consoleErrors.join(' | ')}\n`)
        return
      }
      const b64 = result.dataUrl.replace(/^data:image\/png;base64,/, '')
      await writeFile(out, Buffer.from(b64, 'base64'))
      const dt = ((Date.now() - t0) / 1000).toFixed(1)
      const body = JSON.stringify({
        out,
        seconds: Number(dt),
        url,
        settleMs,
        errors: result.consoleErrors,
        logs: result.consoleLogs,
      }, null, 2)
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(body + '\n')
      console.log(`  ${dt}s ${url} → ${out}${result.consoleErrors.length ? ` (${result.consoleErrors.length} err)` : ''}`)
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'text/plain' })
      res.end(`${err.message}\n`)
      console.log(`  ERR ${err.message}`)
    }
  })

  server.listen(DAEMON_PORT)
  process.on('SIGINT', async () => {
    console.log('\ninspect daemon: stopping')
    await browser.close()
    process.exit(0)
  })
}

async function runOnce(url, settleMs, outPath) {
  const browser = await chromium.launch({ args: ['--disable-web-security'] })
  const context = await browser.newContext({ viewport: VIEWPORT })
  const page = await context.newPage()
  const result = await snapInPage(page, url, settleMs)
  if (!result.dataUrl) {
    console.error(`no canvas. errors: ${result.consoleErrors.join(' | ')}`)
    await browser.close()
    process.exit(1)
  }
  const b64 = result.dataUrl.replace(/^data:image\/png;base64,/, '')
  await writeFile(outPath, Buffer.from(b64, 'base64'))
  console.log(`saved ${outPath}`)
  for (const l of result.consoleLogs)   console.log(`  log: ${l}`)
  for (const e of result.consoleErrors) console.log(`  err: ${e}`)
  await browser.close()
}

const isMain = import.meta.url === `file://${process.argv[1]}`
if (isMain) {
  const args = parseArgs(process.argv.slice(2))
  if (args.daemon) {
    await runDaemon()
  } else {
    const url = args.positional[0] || 'http://localhost:5173/'
    const settleMs = Number(args.settle ?? 3000)
    const out = args.out || '/tmp/inspect.png'
    await runOnce(url, settleMs, out)
  }
}
