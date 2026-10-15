// The two confusions Chapter 3 keeps coming back to (the director's point):
// humans struggle with the same distinctions the network does — HF vs MD
// and MD vs LD. On a matrix in the paper's class order (ND, HF, MD, LD, CD)
// each pair is a contiguous 2×2 block, and the two blocks share the MD–MD
// cell. Drawn on the labelers' matrices (EssdIrrMatrices, the IRR
// segment's second beat) and meant for the MODEL's matrices too.
//
// Use with <ConfusionBlockOutlines> (components/ConfusionBlockOutlines.vue)
// dropped INSIDE any CSS-grid matrix — see that file for the contract.

export type ConfusionPair = readonly [string, string]

/** HF–MD and MD–LD. */
export const CONFUSING_PAIRS: readonly ConfusionPair[] = [
  ['HF', 'MD'],
  ['MD', 'LD'],
]

/** Index range [lo, hi] (inclusive) of a pair's two classes in `order`;
 *  null if a class is missing. The block is the square lo..hi × lo..hi,
 *  so it is a 2×2 only when the two classes are adjacent in `order`. */
export function pairRange(order: readonly string[], pair: ConfusionPair): [number, number] | null {
  const a = order.indexOf(pair[0])
  const b = order.indexOf(pair[1])
  if (a < 0 || b < 0) return null
  return [Math.min(a, b), Math.max(a, b)]
}

/** CSS grid-row / grid-column for a pair's block, when cell (i, j) of
 *  the matrix sits in grid track i + offset + 1 (1-based lines; `offset`
 *  = header tracks before the first cell — 1 for a row/column of labels). */
export function blockArea(
  order: readonly string[],
  pair: ConfusionPair,
  offset = 1,
): { gridRow: string; gridColumn: string } | null {
  const r = pairRange(order, pair)
  if (!r) return null
  const lines = `${r[0] + offset + 1} / ${r[1] + offset + 2}`
  return { gridRow: lines, gridColumn: lines }
}

/** Is cell (i, j) inside any of the pairs' blocks? (for dimming the rest) */
export function inAnyBlock(
  order: readonly string[],
  pairs: readonly ConfusionPair[],
  i: number,
  j: number,
): boolean {
  for (const p of pairs) {
    const r = pairRange(order, p)
    if (r && i >= r[0] && i <= r[1] && j >= r[0] && j <= r[1]) return true
  }
  return false
}
