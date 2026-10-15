// A visitor's labels from the "Label lakes yourself" door, as a CSV in
// EXACTLY the lakelabel GUI's format (sat_tile_stack/labeling.py, the six
// files in cinematic/source_data/essd/irr/irr_labels_labeler<k>_CW_<year>.csv):
//
//   lake_id,label,p_ND,p_HF,p_MD,p_LD,p_CD,notes,flagged
//   CW2018_1077,LD,0.0,0.0,0.0,1.0,0.0,,False
//
// probabilities as decimals summing to 1 (pandas' repr: 0.0 · 0.25 · 0.5 ·
// 0.75 · 1.0), `label` = the hard argmax with a tie to the LOWER class (the
// paper's rule, essdLabel.softArgmax), notes quoted only when they hold a
// comma or a quote, flagged True/False, CRLF line ends as in those files.
//
// Pure TypeScript, no Vite: the page (SUBMIT) AND the labels Worker
// (cloudflare/labels-worker, which builds the CSV) import the same file,
// so the format, the name rule and the R2 key are fixed in one place.

import { ESSD_CLASSES, softArgmax } from './essdLabel'

export const IRR_CSV_HEADER = 'lake_id,label,p_ND,p_HF,p_MD,p_LD,p_CD,notes,flagged'
export const IRR_NAME_MAX = 60
export const IRR_ROWS_MAX = 200
export const IRR_NOTES_MAX = 200
/** The Worker refuses a body larger than this (bytes). */
export const IRR_BODY_MAX = 64 * 1024

const P_KEYS = ESSD_CLASSES.map((c) => `p_${c.code}`) as readonly string[]

export interface IrrRow {
  lake_id: string
  p_ND: number
  p_HF: number
  p_MD: number
  p_LD: number
  p_CD: number
  notes?: string
  flagged?: boolean
}
export interface IrrSave {
  name: string
  rows: IrrRow[]
  /** The visitor's proof of owning their name's file (32 hex), sent with
   *  every SUBMIT after the first — the Worker overwrites that file only
   *  when sha256(token) is the file's `tokenHash`. */
  token?: string
}

/** pandas' float repr for the quarter values: 0.0, 0.25, 0.5, 0.75, 1.0. */
export function fmtProb(v: number): string {
  return Number.isInteger(v) ? v.toFixed(1) : String(v)
}

// Control characters (tabs, newlines included) become spaces — the GUI's
// notes box is one line. Otherwise kept as typed (the GUI does not trim:
// one labeler's note ends in a space, and the round trip keeps it).
const CTRL = /[\u0000-\u001f\u007f]/g

/** One line, capped; a leading = + - @ gets a ' so a spreadsheet never
 *  runs it as a formula (OWASP's CSV-injection guard). */
export function cleanNotes(s: string | undefined): string {
  let t = (s ?? '').replace(CTRL, ' ')
  if (/^[=+\-@]/.test(t)) t = `'${t}`
  return t.slice(0, IRR_NOTES_MAX) // idempotent: a second pass changes nothing
}

/** pandas' QUOTE_MINIMAL: quote only a field holding , " or a line break. */
function csvField(s: string): string {
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

export function irrRowProbs(r: IrrRow): number[] {
  return P_KEYS.map((k) => r[k as keyof IrrRow] as number)
}

export function buildIrrCsv(rows: readonly IrrRow[]): string {
  const lines = [IRR_CSV_HEADER]
  for (const r of rows) {
    const p = irrRowProbs(r)
    lines.push(
      [r.lake_id, softArgmax(p), ...p.map(fmtProb), csvField(cleanNotes(r.notes)), r.flagged ? 'True' : 'False'].join(','),
    )
  }
  return lines.join('\r\n') + '\r\n'
}

/** The slug of a name with no ASCII letter or digit left. Not a name: the
 *  Worker refuses it (400), so it never blocks every such visitor at once. */
export const IRR_NO_SLUG = 'anon'

/** A visitor's name as a file-name slug: ascii letters/digits and '-',
 *  at most 40 characters, case and diacritics folded ('Zoë' = 'zoe');
 *  IRR_NO_SLUG when nothing is left. Two names are the SAME labeler
 *  exactly when their slugs are equal. */
export function nameSlug(name: string): string {
  const s = name
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40)
    .replace(/-+$/g, '')
  return s || IRR_NO_SLUG
}

// ── the R2 key: ONE file per labeler ───────────────────────────────────
// labels/irr/<slug>_<16 hex>.csv. The slug makes a name usable once (the
// Worker lists the prefix `labels/irr/<slug>_` — a slug has no '_', so
// 'ann' never matches 'ann-lee_…'); the tag (64 random bits, the
// Worker's crypto.getRandomValues) keeps the file private: the bucket is
// the site's PUBLIC one and r2.dev never lists it, so only the key's
// holder can read it (the director's choice: the R2 route, no second bucket).
// When it was written lives in the object's customMetadata `saved`.
const IRR_PREFIX = 'labels/irr/'
const TAG = /^[0-9a-f]{16}$/

/** The R2 key of a labeler's file. */
export function irrSaveKey(name: string, tag: string): string {
  if (!TAG.test(tag)) throw new Error('tag must be 16 hex characters')
  return `${IRR_PREFIX}${nameSlug(name)}_${tag}.csv`
}
/** The prefix the Worker lists to find a name's file. */
export function irrSlugPrefix(slug: string): string {
  return `${IRR_PREFIX}${slug}_`
}
/** Is `key` the file of exactly this slug (not a longer slug, not junk)? */
export function irrKeyIsSlug(key: string, slug: string): boolean {
  const p = irrSlugPrefix(slug)
  return key.startsWith(p) && /^[0-9a-f]{16}\.csv$/.test(key.slice(p.length))
}
/** The file name a visitor's labels are kept under (the tag left off). */
export function irrShownName(key: string): string {
  return key.slice(key.lastIndexOf('/') + 1).replace(/_[0-9a-f]{16}\.csv$/, '.csv')
}

type Check = { ok: true; save: IrrSave } | { ok: false; error: string }

function isQuarter(v: number): boolean {
  return Math.abs(v * 4 - Math.round(v * 4)) < 1e-9
}

/** Strict validation of a SUBMIT body ({name, rows, token?}); returns the
 *  rows normalised (probabilities snapped to exact quarters, notes cleaned). */
export function validateIrrSave(body: unknown, lakeIds: ReadonlySet<string>): Check {
  const bad = (error: string): Check => ({ ok: false, error })
  if (!body || typeof body !== 'object' || Array.isArray(body)) return bad('body must be an object')
  const b = body as Record<string, unknown>
  for (const k of Object.keys(b)) if (k !== 'name' && k !== 'rows' && k !== 'token') return bad(`unknown field ${k}`)

  if (typeof b.name !== 'string') return bad('name must be a string')
  const name = b.name.trim()
  if (name.length < 1 || name.length > IRR_NAME_MAX) return bad(`name must be 1-${IRR_NAME_MAX} characters`)
  if (/[\u0000-\u001f\u007f]/.test(name)) return bad('name has control characters')

  if (b.token !== undefined && (typeof b.token !== 'string' || !/^[0-9a-f]{32}$/.test(b.token))) {
    return bad('token must be 32 hex characters')
  }

  if (!Array.isArray(b.rows)) return bad('rows must be an array')
  if (b.rows.length < 1 || b.rows.length > IRR_ROWS_MAX) return bad(`rows must number 1-${IRR_ROWS_MAX}`)

  const seen = new Set<string>()
  const rows: IrrRow[] = []
  for (let i = 0; i < b.rows.length; i++) {
    const r = b.rows[i] as Record<string, unknown>
    if (!r || typeof r !== 'object' || Array.isArray(r)) return bad(`row ${i}: not an object`)
    for (const k of Object.keys(r)) {
      if (k !== 'lake_id' && k !== 'notes' && k !== 'flagged' && !P_KEYS.includes(k)) return bad(`row ${i}: unknown field ${k}`)
    }
    if (typeof r.lake_id !== 'string' || !lakeIds.has(r.lake_id)) return bad(`row ${i}: lake_id not in the inter-rater 200`)
    if (seen.has(r.lake_id)) return bad(`row ${i}: ${r.lake_id} twice`)
    seen.add(r.lake_id)
    const p: number[] = []
    for (const k of P_KEYS) {
      const v = r[k]
      if (typeof v !== 'number' || !Number.isFinite(v) || v < 0 || v > 1 || !isQuarter(v)) {
        return bad(`row ${i}: ${k} must be 0, 0.25, 0.5, 0.75 or 1`)
      }
      p.push(Math.round(v * 4) / 4)
    }
    if (p.reduce((a, v) => a + v, 0) !== 1) return bad(`row ${i}: probabilities must sum to 1`)
    if (r.notes !== undefined && (typeof r.notes !== 'string' || r.notes.length > IRR_NOTES_MAX)) {
      return bad(`row ${i}: notes must be a string of at most ${IRR_NOTES_MAX} characters`)
    }
    if (r.flagged !== undefined && typeof r.flagged !== 'boolean') return bad(`row ${i}: flagged must be true or false`)
    rows.push({
      lake_id: r.lake_id,
      p_ND: p[0],
      p_HF: p[1],
      p_MD: p[2],
      p_LD: p[3],
      p_CD: p[4],
      notes: cleanNotes(r.notes as string | undefined),
      flagged: r.flagged === true,
    })
  }
  return { ok: true, save: b.token === undefined ? { name, rows } : { name, rows, token: b.token as string } }
}
