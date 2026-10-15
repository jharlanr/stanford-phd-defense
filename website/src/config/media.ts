// Media URL resolver.
//
// All media (basemaps, video, logos, easter eggs, masks) lives on
// Cloudflare R2 — the GitHub repo holds only application code.
// VITE_MEDIA_BASE_URL is set in website/.env (committed) so local dev
// works out of the box, and overridden in CI by the MEDIA_BASE_URL
// repo variable. Trailing slash on the base URL is required.
//
// If the variable is somehow unset (e.g. a fresh checkout where .env
// got blown away), we fall through to BASE_URL so the page still
// renders in dev — broken images, but no crash.

const REMOTE_BASE = import.meta.env.VITE_MEDIA_BASE_URL as string | undefined
const LOCAL_BASE = import.meta.env.BASE_URL

// In dev, route R2 URLs through Vite's `/r2/` proxy so browsers see
// same-origin requests (the bucket's CORS allow-list does not include
// localhost). Prod is whitelisted and uses the direct URL.
// Cache generation for every remote asset URL. R2 sends no
// `Vary: Origin` on non-CORS responses, so a browser that ever fetched
// an asset WITHOUT CORS (an earlier plain image preload) keeps serving
// that poisoned entry — no ACAO header — to three.js's CORS texture
// requests, and hard refresh does not flush it. Since the performance
// pass every bucket object also carries `Cache-Control: public,
// max-age=31536000, immutable`, so ANY cached entry — poisoned or just
// old bytes under the same name — now lives a year, not hours. Bumping
// this string gives every asset a fresh cache key. R2 ignores the query
// string.
export const ASSET_VERSION = '3'

export function mediaUrl(filename: string): string {
  if (REMOTE_BASE) {
    if (import.meta.env.DEV && /\.r2\.dev\//.test(REMOTE_BASE)) {
      return `/r2/${filename}`
    }
    return `${REMOTE_BASE}${filename}?v=${ASSET_VERSION}`
  }
  return `${LOCAL_BASE}${filename}`
}

// Warm a file a <video> (or a plain <img>) will play into the HTTP cache,
// in THAT element's own request mode — plain, no-cors — so the entry it
// leaves is the one the element reads (a CORS fetch's entry is refused to
// a plain consumer and vice versa; see ASSET_VERSION above). A <video>'s
// own loads rarely leave a usable entry: the media loader reads ranges and
// aborts once it has enough, so every visit streamed the movie again (the
// performance walk measured Chapter 3's five opening movies, 27 MB, on a
// WARM cache). One complete 200 response serves every later range request.
const warmedPlain = new Set<string>()
export function warmPlain(url: string): void {
  if (warmedPlain.has(url)) return
  warmedPlain.add(url)
  fetch(url, { mode: 'no-cors' }).catch(() => {})
}

// The marker that keeps a CORS consumer's cache entry apart from a plain
// one of the SAME file (a WebGL texture vs a CSS background / <img>): R2
// answers a no-Origin request without ACAO or Vary, so one cached plain
// entry is refused to every later CORS load of that URL — for a year. R2
// ignores the query. (First hit by the Chapter 2 bed palette; the pattern
// of essdNetworkPool's cors=1 and SectionMotivation's crop.)
export function corsUrl(url: string): string {
  return url + (url.includes('?') ? '&' : '?') + 'cors=1'
}
