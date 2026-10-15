// The labels Worker: the "Label lakes yourself" door's SUBMIT.
//
// A static GitHub Pages site cannot write to R2, and R2 keys must never
// ship in the bundle — so the page POSTs a visitor's labels here and this
// Worker, bound to the bucket, writes them as a CSV in the lakelabel GUI's
// exact format. ONE file per labeler, always their latest full set:
//
//   POST {name, rows:[{lake_id, p_ND, p_HF, p_MD, p_LD, p_CD, notes?, flagged?}], token?}
//   → 200 {key, rows, token}   a new name: key = labels/irr/<name-slug>_<16 hex>.csv,
//                              token = 32 random hex (its SHA-256 kept as the
//                              object's customMetadata tokenHash)
//   → 200 {key, rows}          the name's owner again (sha256(token) = tokenHash):
//                              the SAME key overwritten with every row sent
//   → 409                      the name is someone else's (the director asked that
//                              a name entered twice get the sentence 'labeler with
//                              that name already exists, use a different name')
//
// Names are compared by slug (website/src/config/irrCsv.ts nameSlug: case
// and diacritics folded). The CSV is built HERE from the same file, so the
// format is fixed by the Worker, not by whatever a client sends. The last
// part of the key is 64 random bits — the bucket is the site's public one,
// and r2.dev never lists it, so the name is the lock.
//
// Refusals: 403 a foreign Origin · 405 not POST · 415 not JSON · 413 a
// body over 64 KB · 400 anything invalid (name 1–60 characters with at
// least one a-z/0-9 — a name with none has no slug, see IRR_NO_SLUG; 1–200
// rows, ids from the inter-rater 200, quarters summing to 1) · 409 the
// name is taken · 429 more than one write per 10 s, or one name lookup
// per second, from one IP (per isolate — crude on purpose).

import {
  IRR_BODY_MAX,
  IRR_NO_SLUG,
  buildIrrCsv,
  irrKeyIsSlug,
  irrSaveKey,
  irrSlugPrefix,
  nameSlug,
  validateIrrSave,
} from '../../../website/src/config/irrCsv'
import LAKE_IDS from './irr_lake_ids.json'

// The slice of the R2 binding this Worker uses (no workers-types needed).
interface LabelsObject {
  key: string
  customMetadata?: Record<string, string>
}
export interface LabelsBucket {
  head(key: string): Promise<LabelsObject | null>
  list(options: {
    prefix: string
    cursor?: string
    include?: ('httpMetadata' | 'customMetadata')[]
  }): Promise<{ objects: LabelsObject[]; truncated: boolean; cursor?: string }>
  put(
    key: string,
    value: string,
    options?: { httpMetadata?: { contentType?: string }; customMetadata?: Record<string, string> },
  ): Promise<unknown>
}
export interface Env {
  LABELS: LabelsBucket
}

const IDS: ReadonlySet<string> = new Set(LAKE_IDS as string[])

// The site (GitHub Pages) and a local dev server — nothing else.
const ORIGINS = new Set(['https://jharlanr.github.io'])
const LOCAL = /^http:\/\/(localhost|127\.0\.0\.1)(:\d{1,5})?$/
export function originAllowed(origin: string | null): origin is string {
  return !!origin && (ORIGINS.has(origin) || LOCAL.test(origin))
}

/** Per-IP spacing, remembered by this isolate only. `wait` = whole
 *  seconds still to wait (0 = go); `note` records a use. */
export function limiter(ms: number) {
  const last = new Map<string, number>()
  return {
    wait(ip: string, now: number): number {
      const t = last.get(ip)
      return t !== undefined && now - t < ms ? Math.ceil((ms - (now - t)) / 1000) : 0
    },
    note(ip: string, now: number): void {
      if (last.size > 5000) for (const [k, v] of last) if (now - v >= ms) last.delete(k)
      last.set(ip, now)
    },
  }
}
// One name LOOKUP (an R2 list) per second per IP, and one WRITE per 10 s
// per IP. A 409 writes nothing and does not count as a write — a visitor
// told the name is taken can submit under a new one at once — and is
// answered even inside another write's 10 s.
const writes = limiter(10_000)
const lookups = limiter(1_000)

/** A labeler file already in the bucket for a slug. */
export interface Existing {
  key: string
  tokenHash: string | null
}
export type Plan = { kind: 'create' } | { kind: 'overwrite'; key: string; tokenHash: string } | { kind: 'taken' }

/** What a SUBMIT does, given the files already under its slug (normally
 *  none or one) and the hash of the token it carried (null: none). */
export function planSubmit(existing: readonly Existing[], tokenHash: string | null): Plan {
  if (!existing.length) return { kind: 'create' }
  const mine = tokenHash ? existing.find((e) => e.tokenHash === tokenHash) : undefined
  return mine && tokenHash ? { kind: 'overwrite', key: mine.key, tokenHash } : { kind: 'taken' }
}

/** Every file of exactly this slug (`jane` never finds `jane-doe_…`). */
export async function findExisting(bucket: LabelsBucket, slug: string): Promise<Existing[]> {
  const prefix = irrSlugPrefix(slug)
  const out: Existing[] = []
  let cursor: string | undefined
  for (let page = 0; page < 5; page++) {
    const res = await bucket.list({ prefix, cursor, include: ['customMetadata'] })
    for (const o of res.objects) {
      if (!irrKeyIsSlug(o.key, slug)) continue
      const meta = o.customMetadata ?? (await bucket.head(o.key))?.customMetadata
      out.push({ key: o.key, tokenHash: meta?.tokenHash ?? null })
    }
    if (!res.truncated || !res.cursor) break
    cursor = res.cursor
  }
  return out
}

export function randomHex(bytes: number): string {
  return [...crypto.getRandomValues(new Uint8Array(bytes))].map((b) => b.toString(16).padStart(2, '0')).join('')
}
export async function sha256Hex(s: string): Promise<string> {
  const d = new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s)))
  return [...d].map((b) => b.toString(16).padStart(2, '0')).join('')
}

function corsHeaders(origin: string): Record<string, string> {
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin',
  }
}

function reply(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', ...headers },
  })
}

/** The body, or null past `max` bytes (Content-Length may be absent). */
async function readCapped(req: Request, max: number): Promise<Uint8Array | null> {
  if (!req.body) return new Uint8Array(0)
  const reader = req.body.getReader()
  const parts: Uint8Array[] = []
  let n = 0
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    n += value.byteLength
    if (n > max) {
      await reader.cancel()
      return null
    }
    parts.push(value)
  }
  const out = new Uint8Array(n)
  let o = 0
  for (const p of parts) {
    out.set(p, o)
    o += p.byteLength
  }
  return out
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const origin = req.headers.get('Origin')
    if (!originAllowed(origin)) return reply(403, { error: 'origin not allowed' })
    const cors = corsHeaders(origin)
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors })
    if (req.method !== 'POST') return reply(405, { error: 'POST only' }, { ...cors, Allow: 'POST, OPTIONS' })

    if (!(req.headers.get('Content-Type') ?? '').toLowerCase().startsWith('application/json')) {
      return reply(415, { error: 'send application/json' }, cors)
    }
    if (Number(req.headers.get('Content-Length') ?? '0') > IRR_BODY_MAX) {
      return reply(413, { error: `body over ${IRR_BODY_MAX} bytes` }, cors)
    }
    const raw = await readCapped(req, IRR_BODY_MAX)
    if (!raw) return reply(413, { error: `body over ${IRR_BODY_MAX} bytes` }, cors)

    let body: unknown
    try {
      body = JSON.parse(new TextDecoder().decode(raw))
    } catch {
      return reply(400, { error: 'body is not JSON' }, cors)
    }
    const v = validateIrrSave(body, IDS)
    if (!v.ok) return reply(400, { error: v.error }, cors)
    const { name, rows, token } = v.save

    // A name with no a-z/0-9 has no slug of its own: refused, rather than
    // letting the first such visitor block every later one.
    const slug = nameSlug(name)
    if (slug === IRR_NO_SLUG) return reply(400, { error: 'name needs a letter or digit (a-z, 0-9)', field: 'name' }, cors)

    const ip = req.headers.get('CF-Connecting-IP') ?? 'unknown'
    const now = Date.now()
    const tooSoon = (wait: number) =>
      reply(429, { error: 'one submit per 10 s', retryAfter: wait }, { ...cors, 'Retry-After': String(wait) })
    const lookWait = lookups.wait(ip, now)
    if (lookWait) return tooSoon(lookWait)
    lookups.note(ip, now)

    let plan: Plan
    try {
      plan = planSubmit(await findExisting(env.LABELS, slug), token ? await sha256Hex(token) : null)
    } catch (e) {
      console.error('R2 list failed', slug, e)
      return reply(500, { error: 'storage failed' }, cors)
    }
    // The name's answer first (a taken name is taken whatever the clock
    // says); then the write spacing.
    if (plan.kind === 'taken') {
      return reply(409, { error: 'labeler with that name already exists, use a different name', field: 'name' }, cors)
    }
    const writeWait = writes.wait(ip, now)
    if (writeWait) return tooSoon(writeWait)
    writes.note(ip, now)
    let key: string
    let tokenHash: string
    let newToken: string | undefined
    if (plan.kind === 'overwrite') {
      key = plan.key
      tokenHash = plan.tokenHash
    } else {
      newToken = randomHex(16)
      tokenHash = await sha256Hex(newToken)
      key = irrSaveKey(name, randomHex(8))
    }
    try {
      await env.LABELS.put(key, buildIrrCsv(rows), {
        httpMetadata: { contentType: 'text/csv; charset=utf-8' },
        customMetadata: {
          // the full name (the key carries only its ascii slug)
          name: encodeURIComponent(name),
          rows: String(rows.length),
          saved: new Date(now).toISOString(),
          tokenHash,
        },
      })
    } catch (e) {
      console.error('R2 put failed', key, e)
      return reply(500, { error: 'storage failed' }, cors)
    }
    return reply(200, newToken ? { key, rows: rows.length, token: newToken } : { key, rows: rows.length }, cors)
  },
}
