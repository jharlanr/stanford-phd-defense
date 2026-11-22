// The APS DFD flash slide as files for the room laptop: a one-page PDF at
// 1920×1080 (fonts embedded, renders the same anywhere), a PNG at 2×
// (3840×2160) for the PowerPoint fallback, and a PNG at 1× — rendered from
// the site itself (SectionDfd beat 0 with `?print=1`, which hides the
// ribbon and the pills), so the file and the page can never drift apart.
//   node tools/dfd-export.mjs <outdir> [base]
// Needs the dev server (or a preview) at <base>; one GPU-rendered headless
// Chromium (the new headless via channel 'chromium').
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'

const out = process.argv[2]
const base = process.argv[3] ?? 'http://localhost:5173/stanford-phd-defense'
if (!out) throw new Error('usage: node tools/dfd-export.mjs <outdir> [base]')
mkdirSync(out, { recursive: true })
const url = `${base}/additional-work/dfd?beat=0&print=1`

const b = await chromium.launch({ channel: 'chromium', headless: true })
for (const [scale, name] of [[2, 'dfd_flash_slide@2x.png'], [1, 'dfd_flash_slide.png']]) {
  const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: scale })
  const p = await ctx.newPage()
  await p.goto(url, { waitUntil: 'domcontentloaded' })
  await p.waitForTimeout(6000)
  // every image on the slide decoded?
  const broken = await p.evaluate(() => [...document.querySelectorAll('.sl img')].filter((i) => !i.complete || i.naturalWidth === 0).length)
  if (broken) console.warn('images not decoded:', broken)
  await p.screenshot({ path: `${out}/${name}` })
  console.log('wrote', name)
  if (scale === 1) {
    await p.emulateMedia({ media: 'screen' })
    await p.pdf({
      path: `${out}/dfd_flash_slide.pdf`,
      width: '1920px',
      height: '1080px',
      printBackground: true,
      margin: { top: '0', right: '0', bottom: '0', left: '0' },
      pageRanges: '1',
      preferCSSPageSize: false,
    })
    console.log('wrote dfd_flash_slide.pdf')
  }
  await ctx.close()
}
await b.close()
