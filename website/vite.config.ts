import { defineConfig, loadEnv, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'
import { existsSync, createReadStream, statSync } from 'node:fs'
import { join, normalize, extname } from 'node:path'

// Dev-only: serve /r2/<key> from a local bucket mirror (website/.r2-cache)
// when the file exists there, falling through to the network proxy
// otherwise. The hi-res basemap + DEM textures total ~110 MB — pulling
// them from R2 on every fresh headless-browser screenshot made visual
// verification take 30+ s per shot. Populate the mirror with:
//   rclone sync r2:<bucket> .r2-cache
const R2_CACHE_DIR = '.r2-cache'
const MIME: Record<string, string> = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.json': 'application/json',
  '.mp4': 'video/mp4',
  '.gpx': 'application/gpx+xml',
  '.svg': 'image/svg+xml',
}

function r2LocalCache(root: string): Plugin {
  return {
    name: 'r2-local-cache',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (!req.url?.startsWith('/r2/')) return next()
        const key = decodeURIComponent(req.url.slice('/r2/'.length).split('?')[0])
        const file = normalize(join(root, R2_CACHE_DIR, key))
        // Path-traversal guard + existence check; miss → network proxy.
        if (!file.startsWith(normalize(join(root, R2_CACHE_DIR))) || !existsSync(file)) {
          return next()
        }
        const size = statSync(file).size
        const type = MIME[extname(file).toLowerCase()] ?? 'application/octet-stream'
        // Minimal Range support so <video> seeking works in dev.
        const range = req.headers.range?.match(/bytes=(\d+)-(\d*)/)
        if (range) {
          const start = Number(range[1])
          const end = range[2] ? Number(range[2]) : size - 1
          res.writeHead(206, {
            'Content-Type': type,
            'Content-Range': `bytes ${start}-${end}/${size}`,
            'Accept-Ranges': 'bytes',
            'Content-Length': end - start + 1,
          })
          createReadStream(file, { start, end }).pipe(res)
        } else {
          res.writeHead(200, {
            'Content-Type': type,
            'Content-Length': size,
            'Accept-Ranges': 'bytes',
          })
          createReadStream(file).pipe(res)
        }
      })
    },
  }
}

// GitHub Pages serves a project site at https://<user>.github.io/<repo>/.
// `base` must match the repo name with leading + trailing slashes so all
// asset URLs resolve correctly. Override at build time:
//   VITE_BASE=/greenland-defense/ npm run build
// Default '/' works for local dev and for custom-domain deploys.

// Per-worktree dev port. Each parallel-agent worktree pins its own port
// via website/.env.local (VITE_PORT=5174 etc.) so dev servers and the
// screenshot tool URLs stay stable. strictPort fails loud instead of
// silently drifting if the port is taken.
//
// Dev-only R2 proxy: the R2 bucket's CORS allow-list does not include
// localhost, so direct cross-origin requests from the dev server fail
// silently (broken textures → black globe). The proxy below makes
// /r2/<file> on localhost forward to the R2 base URL server-side, so
// the browser sees same-origin and CORS never enters the picture.
// `mediaUrl()` rewrites r2.dev URLs to /r2/* in dev only; prod
// (GitHub Pages) is whitelisted on the bucket and uses the direct URL.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const r2Base = env.VITE_MEDIA_BASE_URL ?? ''
  const r2Origin = r2Base.match(/^https?:\/\/[^/]+/)?.[0]
  return {
    base: env.VITE_BASE ?? '/',
    plugins: [vue(), r2LocalCache(process.cwd())],
    server: {
      port: Number(env.VITE_PORT ?? 5173),
      strictPort: true,
      proxy: r2Origin
        ? {
            '/r2/': {
              target: r2Origin,
              changeOrigin: true,
              rewrite: (path) => path.replace(/^\/r2\//, '/'),
            },
          }
        : undefined,
    },
  }
})
