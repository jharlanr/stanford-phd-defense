# Operations — how the site is served, stored and verified

This is the plumbing. It is deliberately boring and it is the part most
people ask about first. Everything here is a choice; the alternative is
noted where one was seriously considered.

## 1. The shape of the deployment

```
GitHub repo ──push to main──▶ GitHub Actions ──▶ GitHub Pages   (the app: HTML, JS, CSS, ~10 MB)
                                                      │
                                                      ▼  the browser fetches media directly
                                      object-storage bucket (Cloudflare R2, public read)   (~6 GB)
                                                      ▲
                                      Cloudflare Worker (one tiny API: visitors' label CSVs)
```

- **The repo holds only application code and small derived assets.**
  Textures, movies, equation SVGs, simulation fields and PDFs live in the
  bucket. The repo would otherwise be tens of gigabytes and every clone
  would pay for it.
- **GitHub Pages serves the app** as a *project site*, at
  `https://<user>.github.io/<repo>/`. The repo name is therefore part of
  every URL, which is why the build needs to know it (below).
- **The bucket is public-read, write-only from one machine.** The site
  never needs credentials. The one thing visitors can write (their own
  lake labels on the "label lakes yourself" page) goes through a Worker
  that holds the bucket binding, so no key ever ships in the bundle.

Alternative considered: a single host that serves both app and media
(Netlify, Vercel, a VPS). Pages + a bucket was chosen because both are
free or nearly free at this scale, the media never passes through git,
and the two can be redeployed independently.

## 2. GitHub Pages

The workflow is `.github/workflows/deploy.yml`. It runs on every push to
`main` that touches `website/` (pipeline-only and docs-only pushes do not
redeploy), builds `website/` with Node 20 and publishes `website/dist/`.

One-time setup in a fork:

1. Settings → Pages → Source: **GitHub Actions**.
2. In the workflow, set `VITE_BASE` to `/<your-repo-name>/` (leading and
   trailing slash). The same value is in the `dev` script of
   `website/package.json` so local dev and production share one base path;
   `website/public/404.html` and `website/src/router/index.ts` mention it
   in comments (the 404 shim's real knob is `pathSegmentsToKeep = 1`).
   The forking checklist in §9 lists every file that carries the name.
3. Settings → Secrets and variables → Actions → **Variables** (not
   secrets): `MEDIA_BASE_URL` = your bucket's public URL with a trailing
   slash. `website/.env` holds the same URL for local dev and is committed
   on purpose: it is a public URL, not a secret.

Watching and verifying a deploy:

```
gh run watch                                   # the Pages run
curl -s https://<user>.github.io/<repo>/ | grep -oE 'index-[A-Za-z0-9_-]+\.js'
curl -s https://<user>.github.io/<repo>/assets/<that file> | grep -c '<a string only the new build has>'
```

The bundle hash differs from a local build (the runner builds it) but the
grep tells you the new code is live. Two things that bit us: a run can sit
in "pending" for minutes while the Pages queue clears, and a docs-only
commit starts no run at all, so there is nothing to watch.

## 3. The bucket

### Layout

One bucket, one prefix per part of the talk. Sizes are from the final
state of the original site, to give a sense of scale (about 11,000
objects, about 6 GB in all; the table is the dev mirror's view and omits
objects the site no longer references):

| prefix        | what                                                              | size   |
|---------------|-------------------------------------------------------------------|--------|
| `intro/`      | globe and Greenland textures (basemap, DEM, velocity, flow trails) | 30 MB  |
| `ch01/` `ch02/` `ch03/` | each chapter's movies, equation SVGs, simulation fields, network frames | 70 MB · 60 MB · 1.3 GB |
| `conclusion/` | the closing figure's data                                         | <1 MB  |
| `menu/`       | menu thumbnails and the fly-by loop                               | 3.5 MB |
| `addl/`       | additional-work cards, deeper-dive figures, bed ensemble, revisit movies | 130 MB |
| `acks/`       | headshots                                                         | (small; the original also held an encrypted private page, dropped here) |
| `papers/`     | the PDFs the title cards open                                     | 36 MB  |
| `shared/`     | palettes, fonts, shared masks                                     | 135 MB |
| `extras/`     | fieldwork footage and other large clips                           | 2.8 GB |
| `labels/`     | written by the Worker: visitors' CSVs                             | tiny   |

Versioned sub-prefixes (`ch01/eq2/`, `ch03/network_4c/`, `addl/mgsim/…`)
mark re-bakes; see the immutability rule.

### The immutability rule (the one rule that matters)

Every object is uploaded with

```
Cache-Control: public, max-age=31536000, immutable
```

so browsers and the CDN keep it for a year without asking. The price of
that is simple: **new bytes get a new name.** A re-baked equation, a
re-cropped headshot, a re-encoded movie goes up under a new file name or
a new versioned prefix (`_v2`, `eq2/`, `people_v3/`), and the config
that points at it changes in the same commit. Never overwrite an object
in place; the old bytes would be served for a year to anyone who had
seen them.

Two related traps, both learned the hard way:

- **One URL, two cache entries.** A browser caches a plain `<img>` /
  CSS load of a file separately from a CORS load of the same file (a
  WebGL texture). The bucket answers a no-Origin request without CORS
  headers and without `Vary: Origin`, so the plain entry, once cached,
  is refused to every later texture load — for a year. Any URL used both
  ways gets two cache keys (`corsUrl()` in `website/src/config/media.ts`
  appends `?cors=1`; the bucket ignores the query).
- **A global cache-buster for emergencies.** `ASSET_VERSION` in
  `media.ts` is appended to every media URL (`?v=3`). Bumping it gives
  every asset a fresh cache key at once. Use it when a cached entry is
  poisoned, not as a substitute for new names.

### Uploading

`rclone` with an S3-compatible remote. Create an API token in the bucket
dashboard scoped to *this bucket only*, then:

```
rclone config            # type: s3, provider: Cloudflare, endpoint <account-id>.r2.cloudflarestorage.com
rclone copyto cinematic/output/thing_v2.webp r2:<bucket>/ch01/thing_v2.webp \
  --header-upload "Cache-Control: public, max-age=31536000, immutable"
rclone copy  cinematic/output/eqs_v2/ r2:<bucket>/ch01/eq2/ --header-upload "Cache-Control: public, max-age=31536000, immutable"
rclone size  r2:<bucket>
```

Throughout this repo the remote is written `r2:` and the bucket
`<bucket>`; substitute yours. Write credentials live only in rclone's
config on the maintainer's machine. Nothing in the repo can write to the
bucket.

Make the bucket readable: enable the public development URL (or a custom
domain) in the dashboard, and add a CORS policy allowing `GET` from
`https://<user>.github.io` (the Pages origin). Localhost is deliberately
not on that list; see "local dev".

### Cost

Object storage is priced per gigabyte-month with no egress charge on
this provider: about 1.5 cents per GB-month, so the ~6 GB here costs
about 9 cents a month, and a room full of people streaming the movies
costs nothing extra. Request charges are negligible at this scale. Before
uploading anything over about a gigabyte, say what it will cost.

## 4. The labels Worker

`cloudflare/labels-worker/` is a single Cloudflare Worker: it accepts a
`POST` of one visitor's labels, validates them strictly, and writes one
CSV per labeler into `labels/irr/` in the bucket. Its README documents the
protocol (names, tokens, what it refuses, rate limits, how to read the
submissions, a local test harness that needs no login).

Deploying it is a one-time, interactive step on the maintainer's machine:

```
cd cloudflare/labels-worker && npx wrangler login && npx wrangler deploy
```

then paste the printed URL into `LABELS_ENDPOINT` in
`website/src/config/essdLabel.ts`. Fill in your own `bucket_name` in
`wrangler.toml` first. With `LABELS_ENDPOINT` empty the page simply shows
no submit row, so a fork without a Worker still works.

## 5. Local development

```
cd website && npm ci && npm run dev        # http://localhost:5173/<repo>/
```

- The dev script sets the same base path as production, so a URL that
  works locally works live.
- A second dev server (for a parallel worktree) pins its own port in
  `website/.env.local` (`VITE_PORT=5174`); `strictPort` fails loudly
  rather than drifting.
- **Media in dev goes through a proxy.** The bucket's CORS policy does
  not include localhost, so `mediaUrl()` rewrites media URLs to `/r2/…`
  in dev and Vite forwards them to the bucket server-side. A local mirror
  short-circuits that: `rclone sync r2:<bucket> website/.r2-cache` (git-
  ignored) and the dev server serves any file it finds there, with byte
  ranges so video seeking works. The mirror was the single biggest speed-
  up for visual verification (a 110 MB texture set no longer crossed the
  network for every screenshot).
- **The build is the gate:** `npm run build` runs `vue-tsc -b` then
  `vite build`. A dev-server screenshot proves nothing about types; an
  unused import fails the build on the runner. Run the build after the
  last edit, every time.

## 6. Verifying as the audience would see it

The site was projected for a room; most defects were layout collisions
that only showed at particular viewport sizes or after a particular
click path. The tools in `website/tools/` exist for that:

- `screenshot.mjs` — one shot of a URL or a named scenario (a deep link
  such as `/chapter1?beat=10`), overwritten each run.
- `shot-grid.mjs` — several scenarios tiled into one labelled PNG, so a
  whole chapter's beats can be judged at a glance; `shot-watch.mjs`
  re-runs it when source files change.
- `inspect.mjs` — a warm-browser daemon that snaps on request in a few
  seconds instead of paying a cold launch each time.
- `render_bed_thumbs.mjs` — an example of using the headless browser as
  a renderer for assets (the bed-ensemble thumbnails).
- `build_extras_basemap.py` — the fieldwork door's per-date basemaps; a
  Python bake that lives here because it is driven from the site's own
  projection constants.

Rules that came out of using them:

- **Headless only, one browser at a time.** Use the new headless
  Chromium (`channel: 'chromium'`) with GPU rendering; never open a
  window on the presenter's desktop; never fan out several browsers on a
  laptop (it froze a 16 GB machine).
- **Press the real buttons.** Deep links preload everything; the
  audience arrives by pressing NEXT. Scripts that drive the actual
  next/back controls caught timing bugs that deep-link screenshots never
  showed.
- **Measure, don't eyeball, when claiming "no overlap".** Read the DOM
  rectangles of the two elements and sweep viewport sizes (1280×720,
  1366×768, 1440×900, 1920×1080). A colourbar that cleared its title at
  1440×900 overlapped it at 1366×768.
- **Judge from the back row.** Text at or above about 15 px and strokes
  at or above 1.5–2 px at 1440×900; no dim greys for anything that must
  be read.

## 7. The asset pipelines — a record, not a runbook

`cinematic/` holds the Python that baked every asset the site shows: one
folder per part of the talk (`scene_01_intro/`, `scene_ch01/` … `scene_acks/`,
`scene_addl/`), each script with a docstring saying what it reads, what it
writes and how it was run. Read them as a record of how the assets were
made. They will not run outside the author's environment as they stand:

- **Sources.** Two fetch scripts (`cinematic/fetch_sources.sh` and
  `cinematic/scene_addl/fetch_sources.sh`, plus the bed ensemble's
  `mgsim/scripts/copy_source_*.sh`) copy the original datasets into the
  git-ignored `cinematic/source_data/` from the author's lab drive and
  cluster share. Their roots are environment variables with placeholder
  defaults — `LAB_DRIVE`, `CLUSTER_MOUNT`, `SOURCE_ROOT`, `THESIS_ZIPS`,
  `ZOTERO_STORAGE`, `DEFENSE_SOURCE_DATA`, `SWEEP_DIR`, `FRACTURE_SRC` —
  and the folder layouts beneath them are the lab's. Point them at your
  own data; the rule the scripts enforce is that nothing reads an original
  in place.
- **Outputs.** Bakes write to `cinematic/data/`, `cinematic/output/` or a
  scene's `output_*/` folder (all git-ignored), then the result is copied
  into the dev mirror and uploaded with rclone as in §3. Generated
  TypeScript (`website/src/config/*.gen.ts`) is committed, so the site
  builds without running any Python.
- **Dependencies.** `cinematic/requirements.txt` lists the union of what
  the scripts import, unpinned; each script's docstring says which subset
  it needs (Earth Engine, PyTorch and the geospatial stack are only needed
  by the scripts that say so). The Chapter 3 network bakes also need the
  paper's own model package and checkpoint, which are not in this tree.

A fork keeps `cinematic/` as reference material and writes its own bakes
for its own objects.

## 8. What is public

Everything in `website/` ships to every visitor's browser. Treat the
bundle as public: no keys, no private names, no draft text. The bucket is
public-read by design; the only private things in the original project
(a password-protected acknowledgements page, its photos and its bake
script) were encrypted at rest and are not part of this release.

## 9. Forking checklist

Everything that carries this site's identity, for anyone who starts from
`website/` rather than from `template/` (the skill advises against it; if
you do it anyway, change all of these in your first commit):

- `.github/workflows/deploy.yml` — `VITE_BASE` (your repo name), the
  `MEDIA_BASE_URL` variable.
- `website/package.json` — the `dev` script's base path.
- `website/.env` — your bucket's public URL.
- `website/src/config/person.ts` — the presenter's name and links.
- `website/src/config/essdLabel.ts` — `LABELS_ENDPOINT`: set it to `''`
  unless you deploy your own Worker (this site's Worker refuses foreign
  origins, so a fork that keeps it shows "not submitted · 403").
- `website/src/config/sections.ts` — `LEGACY_REDIRECTS` (this site's old
  URLs; delete).
- `website/public/404.html`, `website/src/router/index.ts`,
  `website/tools/screenshot.mjs`, `website/tools/render_bed_thumbs.mjs`,
  `website/README.md`, `README.md` — the repo name in comments and
  defaults.
- `website/public/robots.txt` and the `noindex` tag in
  `website/index.html` — this site is deliberately unlisted; a fork
  inherits that silently.
- `cloudflare/labels-worker/wrangler.toml` — your bucket name; the Worker's
  allowed origin in `src/index.ts`.
- The acknowledgements, title card, references, timeline, takeaways and
  every chapter: one scientist's content, to be replaced, not edited.
