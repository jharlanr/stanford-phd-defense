# Website

The interactive site: a Vite + Vue 3 + Three.js single-page app. One
component, `src/views/Explore.vue`, drives every page over a live 3D
globe; the router (`src/router/index.ts`) maps URLs to sections, and the
section registry (`src/config/sections.ts`) defines the pages and their
order. A pair of BACK / NEXT pills walks a deterministic path through the
whole site; every page and beat is deep-linkable (`/chapter1?beat=3`).

## Local development

```bash
npm install
npm run dev
```

The dev server runs at `http://localhost:5173/stanford-phd-defense/`
(`VITE_BASE` is set in the `dev` script; a `VITE_PORT` in `.env.local`
picks another port). Hot-reloads on save.

## Media

Large media (basemaps, DEM textures, lake movies, simulation fields) is
not in the repo. `VITE_MEDIA_BASE_URL` in `.env` points at a public
bucket, and every asset resolves through `mediaUrl()`
(`src/config/media.ts`). In dev, `/r2/<key>` is served from a local mirror
in `.r2-cache/` when the file is there and proxied to the bucket otherwise
(see `vite.config.ts`). The pipelines that produce the media live in
[../cinematic/](../cinematic/); only their outputs are uploaded.

## Build and deploy

```bash
npm run build
```

Writes `dist/`. `VITE_BASE=/<repo-name>/ npm run build` sets the base path
for a GitHub Pages project site; `public/404.html` and the snippet at the
top of `index.html` give history-mode routes a fallback there. The
workflow in [../.github/workflows/deploy.yml](../.github/workflows/deploy.yml)
builds and publishes on every push that touches `website/`.

## Tools

`tools/` holds the Playwright scripts used to check the site headlessly:
`npm run shot` (one scenario), `npm run shot:grid` (several, tiled),
`npm run shot:watch` (re-snap on file change) and
`node tools/inspect.mjs --daemon` for fast repeated snaps. Each script's
header comment explains its flags.
