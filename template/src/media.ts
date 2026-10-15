// The media resolver.
//
// Everything heavy — textures, movies, PDFs — lives in an object-storage
// bucket, never in git, and the app refers to it through this one function.
// VITE_MEDIA_BASE_URL is read from .env (committed: it is a public URL) and
// overridden in CI by a repository variable (see .github/workflows/deploy.yml).
// Until you have a bucket, leave it unset and put files in public/.
//
// Two rules that came out of the reference site, both worth keeping:
//   1. Objects are immutable. Upload every file with a one-year cache header
//      and never overwrite one in place: new bytes get a new name.
//   2. ASSET_VERSION is the emergency cache-buster. Bumping it gives every
//      asset a fresh cache key at once; it is not a substitute for rule 1.
export const ASSET_VERSION = '1'

const REMOTE = (import.meta.env.VITE_MEDIA_BASE_URL as string | undefined) ?? ''

/** The URL to fetch `name` from (e.g. 'intro/basemap.webp'). */
export function mediaUrl(name: string): string {
  if (!REMOTE) return `${import.meta.env.BASE_URL}${name}`
  return `${REMOTE}${name}?v=${ASSET_VERSION}`
}
