// Screenshot a beat the way the audience will see it: a headless, GPU-rendered
// Chromium at a projected size, optionally pressing NEXT a few times first.
//
//   node tools/shot.mjs <url> <out.png> [presses] [width] [height]
//   node tools/shot.mjs 'http://localhost:5173/?beat=2' /tmp/b2.png
//   node tools/shot.mjs 'http://localhost:5173/' /tmp/b5.png 5 1280 720
//
// One-time: npx playwright install chromium. Never open a headed window on the
// presenter's desktop, and never run more than one browser at a time on a
// laptop. Console and page errors are printed, since a blank stage is usually
// one of those.
import { chromium } from 'playwright'

const [url, out = 'shot.png', presses = '0', w = '1440', h = '900'] = process.argv.slice(2)
if (!url) { console.error('usage: node tools/shot.mjs <url> <out.png> [presses] [width] [height]'); process.exit(2) }
const browser = await chromium.launch({ channel: 'chromium', headless: true })
const page = await browser.newPage({ viewport: { width: Number(w), height: Number(h) } })
const errors = []
page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`))
page.on('console', (m) => { if (m.type() === 'error') errors.push(`console: ${m.text()}`) })
await page.goto(url, { waitUntil: 'domcontentloaded' })
await page.waitForTimeout(800)
for (let i = 0; i < Number(presses); i++) { await page.keyboard.press('ArrowRight'); await page.waitForTimeout(500) }
await page.waitForTimeout(400)
await page.screenshot({ path: out })
await browser.close()
console.log(`${out}  ${page.url()}`)
console.log(errors.length ? errors.join('\n') : 'no console or page errors')
