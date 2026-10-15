// Plain-node checks of the Worker's pure parts (no Cloudflare login needed):
//   cd cloudflare/labels-worker
//   npx esbuild test/csv.test.ts --bundle --platform=node --format=esm --outfile=.wrangler/csv.test.mjs
//   node .wrangler/csv.test.mjs
// The round trip rebuilds the six lakelabel CSVs of the ESSD inter-rater
// study (cinematic/source_data/essd/irr/) from their parsed rows and
// compares them byte for byte with the originals.

import { readFileSync, existsSync } from 'node:fs'
import { strict as assert } from 'node:assert'
import {
  IRR_CSV_HEADER,
  IRR_NO_SLUG,
  buildIrrCsv,
  cleanNotes,
  irrKeyIsSlug,
  irrSaveKey,
  irrShownName,
  irrSlugPrefix,
  nameSlug,
  validateIrrSave,
  type IrrRow,
} from '../../../website/src/config/irrCsv'
import worker, { limiter, originAllowed, planSubmit, sha256Hex, type LabelsBucket } from '../src/index'
import LAKE_IDS from '../src/irr_lake_ids.json'

const IDS = new Set(LAKE_IDS as string[])
let passed = 0
function ok(name: string, fn: () => void): void {
  fn()
  passed++
  console.log(`  ok  ${name}`)
}
async function okAsync(name: string, fn: () => Promise<void>): Promise<void> {
  await fn()
  passed++
  console.log(`  ok  ${name}`)
}

// A minimal RFC 4180 reader (quotes, doubled quotes, CRLF).
function parseCsv(text: string): string[][] {
  const out: string[][] = []
  let row: string[] = []
  let f = ''
  let q = false
  for (let i = 0; i < text.length; i++) {
    const c = text[i]
    if (q) {
      if (c === '"' && text[i + 1] === '"') { f += '"'; i++ }
      else if (c === '"') q = false
      else f += c
    } else if (c === '"') q = true
    else if (c === ',') { row.push(f); f = '' }
    else if (c === '\r') { /* CRLF */ }
    else if (c === '\n') { row.push(f); out.push(row); row = []; f = '' }
    else f += c
  }
  if (f || row.length) { row.push(f); out.push(row) }
  return out
}

// ── the round trip against the labelers' own files ──────────────────────
const IRR_DIR = new URL('../../../cinematic/source_data/essd/irr/', import.meta.url)
const files = [1, 2, 3].flatMap((k) => [2018, 2019].map((y) => `irr_labels_labeler${k}_CW_${y}.csv`))
if (!existsSync(new URL(files[0], IRR_DIR))) {
  console.log('  (source CSVs not on this machine — round trip skipped)')
} else {
  for (const fname of files) {
    ok(`round trip ${fname}`, () => {
      const text = readFileSync(new URL(fname, IRR_DIR), 'utf8')
      const [head, ...recs] = parseCsv(text)
      assert.equal(head.join(','), IRR_CSV_HEADER)
      const rows: IrrRow[] = recs.map((r) => ({
        lake_id: r[0],
        p_ND: +r[2], p_HF: +r[3], p_MD: +r[4], p_LD: +r[5], p_CD: +r[6],
        notes: r[7],
        flagged: r[8] === 'True',
      }))
      // the labels Worker accepts every one of the labelers' rows …
      const v = validateIrrSave({ name: 'round trip', rows }, IDS)
      assert.ok(v.ok, v.ok ? '' : v.error)
      // … gives the same hard label (argmax, tie → lower class) …
      const built = buildIrrCsv(v.ok ? v.save.rows : [])
      const back = parseCsv(built)
      recs.forEach((r, i) => assert.equal(back[i + 1][1], r[1], `${r[0]} label`))
      // … and the same bytes, up to pandas writing an all-integer column
      // as 0 / 1 instead of 0.0 / 1.0 in two of the six files.
      const norm = (s: string) => s.replace(/,(0|1)(?=,)/g, ',$1.0')
      assert.equal(built, norm(norm(text)))
    })
  }
}

// ── the format, the name, the key ──────────────────────────────────────
ok('csv: header, quarters, CRLF, quoting, tie to the lower class', () => {
  const csv = buildIrrCsv([
    { lake_id: 'CW2018_1077', p_ND: 0, p_HF: 0, p_MD: 0, p_LD: 1, p_CD: 0 },
    { lake_id: 'CW2018_1083', p_ND: 0, p_HF: 0.5, p_MD: 0.5, p_LD: 0, p_CD: 0, notes: 'HF, or "MD"', flagged: true },
    { lake_id: 'CW2019_1525', p_ND: 0.25, p_HF: 0, p_MD: 0.25, p_LD: 0.25, p_CD: 0.25, notes: '=1+1' },
  ])
  assert.equal(
    csv,
    'lake_id,label,p_ND,p_HF,p_MD,p_LD,p_CD,notes,flagged\r\n' +
      'CW2018_1077,LD,0.0,0.0,0.0,1.0,0.0,,False\r\n' +
      'CW2018_1083,HF,0.0,0.5,0.5,0.0,0.0,"HF, or ""MD""",True\r\n' +
      "CW2019_1525,ND,0.25,0.0,0.25,0.25,0.25,'=1+1,False\r\n",
  )
})
ok('notes: one line, capped, idempotent', () => {
  assert.equal(cleanNotes(' a\nb\tc '), ' a b c ')
  const long = cleanNotes('-' + 'x'.repeat(400))
  assert.equal(long.length, 200)
  assert.equal(cleanNotes(long), long)
})
ok('name slug', () => {
  assert.equal(nameSlug('Jane Doe'), 'jane-doe')
  assert.equal(nameSlug('  Zoë  Ångström!! '), 'zoe-angstrom')
  assert.equal(nameSlug('JANE  doe'), nameSlug('jane-doe'))
  assert.equal(nameSlug('李明'), IRR_NO_SLUG)
  assert.equal(nameSlug('a'.repeat(60)).length, 40)
})
ok('key: labels/irr/<slug>_<16 hex>.csv, one per labeler', () => {
  assert.equal(irrSaveKey('Jane', '0123456789abcdef'), 'labels/irr/jane_0123456789abcdef.csv')
  assert.equal(irrSaveKey('  Zoë Ångström ', '0123456789abcdef'), 'labels/irr/zoe-angstrom_0123456789abcdef.csv')
  assert.throws(() => irrSaveKey('Jane', 'xyz'))
  assert.throws(() => irrSaveKey('Jane', '0123456789ABCDEF'))
  assert.equal(irrShownName('labels/irr/jane_0123456789abcdef.csv'), 'jane.csv')
  assert.equal(irrSlugPrefix('jane'), 'labels/irr/jane_')
})
ok('key: a slug finds only its own file', () => {
  const k = 'labels/irr/jane_0123456789abcdef.csv'
  assert.ok(irrKeyIsSlug(k, 'jane'))
  assert.ok(!irrKeyIsSlug('labels/irr/jane-doe_0123456789abcdef.csv', 'jane')) // a longer slug
  assert.ok(!irrKeyIsSlug(k, 'jan'))
  assert.ok(!irrKeyIsSlug('labels/irr/jane_0123456789abcdef.csv.bak', 'jane'))
  assert.ok(!irrKeyIsSlug('labels/irr/jane_0123456789abcde.csv', 'jane'))
  assert.ok(!irrKeyIsSlug('labels/irr/jane_xyz_0123456789abcdef.csv', 'jane'))
  // the earlier stamped scheme (20261001T091205Z_jane_…) is not a slug file
  assert.ok(!irrKeyIsSlug('labels/irr/20261001T091205Z_jane_0123456789abcdef.csv', 'jane'))
})
ok('plan: create · overwrite with the token · taken without it', () => {
  const a = { key: 'labels/irr/jane_0123456789abcdef.csv', tokenHash: 'aa' }
  assert.deepEqual(planSubmit([], null), { kind: 'create' })
  assert.deepEqual(planSubmit([], 'aa'), { kind: 'create' })
  assert.deepEqual(planSubmit([a], 'aa'), { kind: 'overwrite', key: a.key, tokenHash: 'aa' })
  assert.deepEqual(planSubmit([a], null), { kind: 'taken' })
  assert.deepEqual(planSubmit([a], 'bb'), { kind: 'taken' })
  // a file with no tokenHash (put by hand) is nobody's to overwrite
  assert.deepEqual(planSubmit([{ key: a.key, tokenHash: null }], null), { kind: 'taken' })
  // two files under one slug (a same-instant race): the token picks its own
  const b = { key: 'labels/irr/jane_fedcba9876543210.csv', tokenHash: 'bb' }
  assert.deepEqual(planSubmit([a, b], 'bb'), { kind: 'overwrite', key: b.key, tokenHash: 'bb' })
})

// ── validation ─────────────────────────────────────────────────────────
const good: IrrRow = { lake_id: 'CW2018_1077', p_ND: 0, p_HF: 0, p_MD: 0, p_LD: 1, p_CD: 0 }
const bad = (body: unknown, why: RegExp) => {
  const v = validateIrrSave(body, IDS)
  assert.ok(!v.ok, `accepted: ${JSON.stringify(body).slice(0, 80)}`)
  assert.match(v.ok ? '' : v.error, why)
}
ok('validation accepts a good body and trims the name', () => {
  const v = validateIrrSave({ name: '  Jane  ', rows: [good] }, IDS)
  assert.ok(v.ok)
  assert.equal(v.ok && v.save.name, 'Jane')
  assert.equal(v.ok && v.save.token, undefined)
  const t = validateIrrSave({ name: 'Jane', rows: [good], token: '0123456789abcdef0123456789abcdef' }, IDS)
  assert.equal(t.ok && t.save.token, '0123456789abcdef0123456789abcdef')
})
ok('validation refuses bad bodies', () => {
  bad(null, /object/)
  bad([], /object/)
  bad({ name: 'J', rows: [good], extra: 1 }, /unknown field extra/)
  bad({ name: '', rows: [good] }, /name/)
  bad({ name: '   ', rows: [good] }, /name/)
  bad({ name: 'x'.repeat(61), rows: [good] }, /name/)
  bad({ name: 'a\u0007b', rows: [good] }, /control/)
  bad({ name: 7, rows: [good] }, /name/)
  bad({ name: 'J', rows: [] }, /rows/)
  bad({ name: 'J', rows: 'x' }, /rows/)
  bad({ name: 'J', rows: Array.from({ length: 201 }, () => good) }, /rows/)
  bad({ name: 'J', rows: [{ ...good, lake_id: 'CW2018_9999' }] }, /inter-rater 200/)
  bad({ name: 'J', rows: [good, good] }, /twice/)
  bad({ name: 'J', rows: [{ ...good, p_LD: 0.9, p_ND: 0.1 }] }, /0\.25/)
  bad({ name: 'J', rows: [{ ...good, p_LD: 0.75 }] }, /sum to 1/)
  bad({ name: 'J', rows: [{ ...good, p_LD: '1' }] }, /p_LD/)
  bad({ name: 'J', rows: [{ ...good, p_LD: NaN }] }, /p_LD/)
  bad({ name: 'J', rows: [{ ...good, p_LD: 1.25, p_ND: -0.25 }] }, /p_ND/)
  bad({ name: 'J', rows: [{ ...good, notes: 'x'.repeat(201) }] }, /notes/)
  bad({ name: 'J', rows: [{ ...good, flagged: 'True' }] }, /flagged/)
  bad({ name: 'J', rows: [{ ...good, label: 'ND' }] }, /unknown field label/)
  bad({ name: 'J', rows: [good], token: 'abc' }, /token/)
  bad({ name: 'J', rows: [good], token: '0123456789ABCDEF0123456789ABCDEF' }, /token/)
  bad({ name: 'J', rows: [good], token: 7 }, /token/)
})

// ── the Worker's gates ─────────────────────────────────────────────────
ok('origin allow-list', () => {
  assert.ok(originAllowed('https://jharlanr.github.io'))
  assert.ok(originAllowed('http://localhost:5232'))
  assert.ok(originAllowed('http://127.0.0.1:8787'))
  assert.ok(!originAllowed(null))
  assert.ok(!originAllowed('https://evil.example'))
  assert.ok(!originAllowed('https://jharlanr.github.io.evil.example'))
  assert.ok(!originAllowed('http://jharlanr.github.io'))
  assert.ok(!originAllowed('http://localhost.evil.example'))
})
ok('limiter: seconds left per IP', () => {
  const w = limiter(10_000)
  assert.equal(w.wait('1.2.3.4', 0), 0)
  w.note('1.2.3.4', 0)
  assert.equal(w.wait('1.2.3.4', 1), 10)
  assert.equal(w.wait('1.2.3.4', 9_001), 1)
  assert.equal(w.wait('5.6.7.8', 9_999), 0)
  assert.equal(w.wait('1.2.3.4', 10_000), 0)
})

// ── the whole Worker, on an in-memory bucket ───────────────────────────
interface Obj { value: string; customMetadata: Record<string, string> }
class MemBucket implements LabelsBucket {
  m = new Map<string, Obj>()
  async head(key: string) {
    const o = this.m.get(key)
    return o ? { key, customMetadata: o.customMetadata } : null
  }
  async list(opt: { prefix: string; include?: ('httpMetadata' | 'customMetadata')[] }) {
    const objects = [...this.m.keys()]
      .filter((k) => k.startsWith(opt.prefix))
      .sort()
      .map((key) => ({ key, customMetadata: opt.include?.includes('customMetadata') ? this.m.get(key)!.customMetadata : undefined }))
    return { objects, truncated: false }
  }
  async put(key: string, value: string, o?: { customMetadata?: Record<string, string> }) {
    this.m.set(key, { value, customMetadata: o?.customMetadata ?? {} })
  }
}
const env = { LABELS: new MemBucket() }
let ipN = 0
async function post(body: unknown, o: { ip?: string; origin?: string } = {}) {
  const r = await worker.fetch(
    new Request('https://w.example/', {
      method: 'POST',
      headers: {
        Origin: o.origin ?? 'https://jharlanr.github.io',
        'Content-Type': 'application/json',
        'CF-Connecting-IP': o.ip ?? `10.0.0.${++ipN}`,
      },
      body: JSON.stringify(body),
    }),
    env,
  )
  return { status: r.status, j: (await r.json()) as Record<string, unknown> }
}
const lakes = (n: number): IrrRow[] => (LAKE_IDS as string[]).slice(0, n).map((lake_id) => ({ ...good, lake_id }))
const SENTENCE = 'labeler with that name already exists, use a different name'
const first = { key: '', token: '' }

await okAsync('worker: first SUBMIT → 200 {key, token}, one file, tokenHash kept', async () => {
  const { status, j } = await post({ name: 'Agent Test', rows: lakes(2) })
  assert.equal(status, 200)
  assert.match(String(j.key), /^labels\/irr\/agent-test_[0-9a-f]{16}\.csv$/)
  assert.match(String(j.token), /^[0-9a-f]{32}$/)
  assert.equal(j.rows, 2)
  const o = env.LABELS.m.get(String(j.key))!
  assert.equal(o.customMetadata.tokenHash, await sha256Hex(String(j.token)))
  assert.equal(o.customMetadata.name, 'Agent%20Test')
  assert.equal(o.customMetadata.rows, '2')
  assert.match(o.customMetadata.saved, /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/)
  assert.equal(o.value.split('\r\n').length, 4) // header + 2 rows + ''
  first.key = String(j.key)
  first.token = String(j.token)
})
await okAsync('worker: the same name again → 409 (case/diacritics folded), with a wrong token too', async () => {
  for (const name of ['Agent Test', 'agent  TEST', 'Agént-Test']) {
    const { status, j } = await post({ name, rows: lakes(1) })
    assert.equal(status, 409, name)
    assert.equal(j.error, SENTENCE)
    assert.equal(j.field, 'name')
  }
  const { status } = await post({ name: 'Agent Test', rows: lakes(1), token: 'f'.repeat(32) })
  assert.equal(status, 409)
  assert.equal(env.LABELS.m.size, 1)
})
await okAsync('worker: the owner\'s token → 200, the SAME key overwritten with every row', async () => {
  // another labeler's token does not open this name
  const other = (await post({ name: 'Agent Test 0', rows: lakes(1) })).j.token
  assert.equal((await post({ name: 'Agent Test', rows: lakes(3), token: other })).status, 409)
  const { status, j } = await post({ name: 'Agent Test', rows: lakes(3), token: first.token })
  assert.equal(status, 200)
  assert.equal(j.key, first.key)
  assert.equal(j.token, undefined)
  assert.equal(j.rows, 3)
  assert.equal([...env.LABELS.m.keys()].filter((k) => irrKeyIsSlug(k, 'agent-test')).length, 1)
  const o = env.LABELS.m.get(first.key)!
  assert.equal(o.value.split('\r\n').length, 5) // header + 3 rows + ''
  assert.equal(o.customMetadata.rows, '3')
  assert.equal(o.customMetadata.tokenHash, await sha256Hex(first.token))
})
await okAsync('worker: a different name (even one the first prefixes) → a new key', async () => {
  for (const name of ['Agent', 'Agent Test 2']) {
    const { status, j } = await post({ name, rows: lakes(1) })
    assert.equal(status, 200, name)
    assert.ok(irrKeyIsSlug(String(j.key), nameSlug(name)))
  }
})
await okAsync('worker: a name with no a-z/0-9 → 400 field name; a foreign origin → 403', async () => {
  for (const name of ['李明', '!!!', 'anon', 'ANON']) {
    const { status, j } = await post({ name, rows: lakes(1) })
    assert.equal(status, 400, name)
    assert.equal(j.field, 'name')
  }
  assert.equal((await post({ name: 'Evil', rows: lakes(1) }, { origin: 'https://evil.example' })).status, 403)
})
await okAsync('worker: 1 lookup/s, 1 write/10 s per IP; a 409 is not a write and is answered inside the 10 s', async () => {
  const sleep = (ms: number) => new Promise((res) => setTimeout(res, ms))
  const ip = '10.9.9.9'
  assert.equal((await post({ name: 'Rate One', rows: lakes(1) }, { ip })).status, 200)
  const r0 = await post({ name: 'Rate Two', rows: lakes(1) }, { ip })
  assert.equal(r0.status, 429)
  assert.equal(r0.j.retryAfter, 1) // the lookup spacing
  await sleep(1050)
  const r = await post({ name: 'Rate Two', rows: lakes(1) }, { ip })
  assert.equal(r.status, 429)
  assert.ok(Number(r.j.retryAfter) >= 8 && Number(r.j.retryAfter) <= 9, String(r.j.retryAfter)) // the write spacing
  await sleep(1050)
  assert.equal((await post({ name: 'Agent Test', rows: lakes(1) }, { ip })).status, 409) // still inside the 10 s
  // a refusal (409) does not start the 10 s; only the 1 s lookup spacing
  const ip2 = '10.9.9.10'
  assert.equal((await post({ name: 'Agent Test', rows: lakes(1) }, { ip: ip2 })).status, 409)
  const soon = await post({ name: 'Rate Three', rows: lakes(1) }, { ip: ip2 })
  assert.equal(soon.status, 429)
  assert.equal(soon.j.retryAfter, 1)
  await sleep(1050)
  assert.equal((await post({ name: 'Rate Three', rows: lakes(1) }, { ip: ip2 })).status, 200)
})

console.log(`${passed} checks passed`)
