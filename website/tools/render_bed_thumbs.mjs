// Render the ten "translucent block" frames for the Additional-Work MGSIM
// card: the glassy sim block on /additional-work/mgsim, one frame per bed
// realization, cropped square around the WHOLE prism (black
// tube outlines on its edges, a bigger ice-flow arrow — thumbnail-only
// knobs the globe reads from window.__simThumb). Writes
// cinematic/scene_addl/output_addl_cards/bed_prism_NN.png (raw crops);
// cinematic/scene_addl/build_addl_cards.py downsizes them to JPEG.
//
//   node tools/render_bed_thumbs.mjs            (dev server on 5174)
//   BASE=https://… node tools/render_bed_thumbs.mjs
//   ARROW=2.6 AOFF=0.16 EDGE=0.003 node tools/render_bed_thumbs.mjs   (knobs)
import { chromium } from 'playwright'
import { mkdirSync, writeFileSync } from 'node:fs'
const base = process.env.BASE ?? 'http://localhost:5173/stanford-phd-defense'
const OUT = '../cinematic/scene_addl/output_addl_cards'; mkdirSync(OUT, { recursive: true })
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 })
const knobs = { edges: true, edgeRadius: +(process.env.EDGE ?? 0.003), arrowScale: +(process.env.ARROW ?? 2.6), arrowOffset: +(process.env.AOFF ?? 0.16) }
await page.addInitScript((k) => { window.__simThumb = k }, knobs)
await page.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort())
const click = async (text) => {
  const ok = await page.evaluate((text) => {
    const btns = [...document.querySelectorAll('button')]
    const el = btns.find((b) => b.title === text) ?? btns.find((b) => b.textContent.replace(/\s+/g, ' ').trim().includes(text))
    if (!el) return false; el.click(); return true
  }, text)
  console.log(ok ? 'click' : '!! no button', text)
}
const screen = () => page.evaluate(() => window.__simDomainScreen ?? null)
// Landed = the block is the on-screen subject and has stopped moving:
// visible, a plausible footprint (600–900 px at 1600×900), centre inside
// the viewport, and the same reading twice in a row. Mid-dive readings
// project the block far off-screen with a huge spread — ignore those.
const waitLanded = async (label) => {
  let last = null
  for (let i = 0; i < 120; i++) {
    const s = await screen()
    const ok = s && s.visible && s.spread > 600 && s.spread < 900 && s.x > 100 && s.x < 1500 && s.y > 100 && s.y < 800
    if (ok && last && Math.abs(last.spread - s.spread) < 2 && Math.abs(last.x - s.x) < 2) {
      console.log(label, 'landed', JSON.stringify(s)); return s
    }
    last = ok ? s : null
    await page.waitForTimeout(1000)
  }
  throw new Error('block never landed')
}
await page.goto(base + '/additional-work/mgsim', { waitUntil: 'domcontentloaded', timeout: 90000 })
await waitLanded('deep link')
await click('See the bed topography'); await page.waitForTimeout(2500)
await click('See the data'); await page.waitForTimeout(1500)
await click('Other interpolations'); await page.waitForTimeout(2500)
await click('close'); await page.waitForTimeout(800)
// Hide every DOM overlay (dock, hint, columns, nav) and the shared in-canvas
// "Drain the lake" pill (it lives in Explore, not .mg-root); the globe canvas stays.
await page.addStyleTag({ content: '.mg-root, .top-nav { visibility: hidden !important }' })
await page.evaluate(() => {
  // …and every other floating pill (Drain the lake, Boundary conditions, …).
  for (const b of document.querySelectorAll('button')) b.style.visibility = 'hidden'
})
const cdp = await page.context().newCDPSession(page)
for (let k = 0; k < 10; k++) {
  await page.waitForTimeout(2200)
  const s = await screen()
  // Square around the whole prism + the flow tag (bbox from the globe),
  // with a small margin; clamped into the viewport.
  const b = s.bbox
  const side = Math.min(900, Math.round(Math.max(b.maxX - b.minX, b.maxY - b.minY) * 1.08))
  const cx = (b.minX + b.maxX) / 2
  const cy = (b.minY + b.maxY) / 2
  const clip = {
    x: Math.min(1600 - side, Math.max(0, Math.round(cx - side / 2))),
    y: Math.min(900 - side, Math.max(0, Math.round(cy - side / 2))),
    width: side, height: side, scale: 1,
  }
  const label = await page.evaluate(() => document.querySelector('.mg-bedlabel')?.textContent?.trim() ?? '?')
  const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', clip })
  writeFileSync(`${OUT}/bed_prism_${String(k).padStart(2, '0')}.png`, Buffer.from(data, 'base64'))
  console.log('frame', k, label, JSON.stringify({ ...clip, bbox: b }))
  if (k < 9) await click('next bed')
}
await browser.close()
