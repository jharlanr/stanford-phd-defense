// The ESSD soft label, shared by Chapter 3's "a label made live"
// (EssdLabelDemo.vue) and the "Label lakes yourself" door
// (SectionLabelLakes.vue): the five classes in the paper's order, their
// site-wide colours, and lakelabel's slider rules.

export interface EssdClass {
  code: string
  name: string
  color: string
}

// ESSD class palette (site-wide), in the paper's order — the order is
// also the tie rule: a tie defers to the LOWER class ID (ESSD Sect. 2.4.2,
// "a tie between HF (1) and MD (2) defers to HF").
export const ESSD_CLASSES: readonly EssdClass[] = [
  { code: 'ND', name: 'No drainage', color: '#e8524a' },
  { code: 'HF', name: 'Hydrofracture', color: '#4caf50' },
  { code: 'MD', name: 'Moulin drainage', color: '#42a5f5' },
  { code: 'LD', name: 'Lateral drainage', color: '#ff9800' },
  { code: 'CD', name: 'Crevasse drainage', color: '#ab47bc' },
]

export function classColor(code: string | null | undefined): string {
  return ESSD_CLASSES.find((c) => c.code === code)?.color ?? '#fff'
}
export function className(code: string | null | undefined): string {
  return ESSD_CLASSES.find((c) => c.code === code)?.name ?? (code ?? '')
}

// The labels Worker (cloudflare/labels-worker — its README has the
// deploy): the "Label lakes yourself" door's SUBMIT posts a visitor's
// labels there and it writes them to R2 as that labeler's one lakelabel
// CSV under labels/irr/ (deployed from the director's own Cloudflare login).
// Empty = nothing to submit to: the door shows no name/SUBMIT row. There
// is never a download (the director's rule).
export const LABELS_ENDPOINT: string = 'https://defense-labels.labels-worker.workers.dev/'

// lakelabel's sliders (sat_tile_stack/index.html buildProbSliders /
// onProbChange): min 0, max 1, step 0.25 with five tick dots, and "Clamp:
// if total > 1, pull this slider back" — the slider being moved gives way,
// rounded to a quarter. Submit is enabled only when the five sum to 1.
// Here in percent: 0 · 25 · 50 · 75 · 100.
export const SOFT_STEP = 25
export const SOFT_TICKS = [0, 25, 50, 75, 100]

export type SoftRaw = Record<string, number>

export function emptySoft(): SoftRaw {
  return { ND: 0, HF: 0, MD: 0, LD: 0, CD: 0 }
}

/** Set one class's slider, snapped to a quarter and clamped so the five
 *  never sum past 100. Returns the value actually taken. */
export function clampSoft(raw: SoftRaw, code: string, value: number): number {
  let v = Math.round((Number.isFinite(value) ? value : 0) / SOFT_STEP) * SOFT_STEP
  const others = ESSD_CLASSES.reduce((a, c) => a + (c.code === code ? 0 : raw[c.code]), 0)
  if (others + v > 100) v = Math.max(0, Math.round((100 - others) / SOFT_STEP) * SOFT_STEP)
  return v
}

export function softTotal(raw: SoftRaw): number {
  return ESSD_CLASSES.reduce((a, c) => a + raw[c.code], 0)
}

/** The hard label: argmax, a tie to the lower class ID (the paper's rule). */
export function softArgmax(p: readonly number[]): string {
  let best = 0
  for (let i = 1; i < p.length; i++) if (p[i] > p[best]) best = i
  return ESSD_CLASSES[best].code
}
