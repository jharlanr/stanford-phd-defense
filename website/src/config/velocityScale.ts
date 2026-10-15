// The Introduction's surface-speed colour scale — the SAME stops the drape
// was baked with (cinematic/scene_01_intro/build_flow_trails.py reads
// velocityPalette.json too), so the colorbar can never disagree with the
// map. Log mapping: frac = log10(v / vmin) / log10(vmax / vmin).
import palette from './velocityPalette.json'

export const SPEED_MIN: number = palette.vmin
export const SPEED_MAX: number = palette.vmax
const STOPS = palette.stops as [number, string][]

/** Fraction of the colour bar (0 = vmin, 1 = vmax) for a speed in m/yr. */
export function speedToFrac(v: number): number {
  const f = Math.log10(v / SPEED_MIN) / Math.log10(SPEED_MAX / SPEED_MIN)
  return Math.min(1, Math.max(0, f))
}

/** CSS gradient stops for a bar running from vmin (0 %) to vmax (100 %). */
export function speedGradientStops(): string {
  return STOPS.map(([f, c]) => `${c} ${(f * 100).toFixed(2)}%`).join(', ')
}

/** Tick values: every decade inside the range, plus the saturating top. */
export function speedTicks(): number[] {
  const out: number[] = []
  for (let v = SPEED_MIN; v <= SPEED_MAX * 1.0001; v *= 10) out.push(v)
  if (out[out.length - 1] !== SPEED_MAX) out.push(SPEED_MAX)
  return out
}
