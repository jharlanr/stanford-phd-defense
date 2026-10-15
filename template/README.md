# Beat-driven talk — a plain template

A small Vite + Vue 3 + TypeScript skeleton of a *beat-driven presentation website*: one
object on stage, an ordered list of named **beats** (one per press of NEXT), and the plumbing
that keeps the keyboard, the address bar and the browser history in step with where the
talk is. It is deliberately plain — light page, system font, one blue — so you can re-theme
it and replace the object without untangling a design.

## Run it

```sh
npm install
npm run dev        # http://localhost:5173
npm run build      # vue-tsc type-check + vite build → dist/
npm run preview    # serve dist/ locally
```

Deploying: push to `main` with Pages set to "GitHub Actions" and `.github/workflows/deploy.yml` builds and publishes it at `https://<user>.github.io/<repo>/` (the base path comes from the repo name). By hand: `VITE_BASE=/<repo>/ npm run build`.

Drive the talk with **→ / Space / PageDown** (next), **← / PageUp** (back), **Home** (first
beat) — a presenter remote sends PageDown / PageUp, so it just works — or with the ribbon's
buttons. The address bar always carries `?beat=N`; copy it and the link opens the talk there
(`?beat=last` lands on the final beat).

## What each file is for

| File | Role |
| --- | --- |
| `src/beats.ts` | **The registry.** The ordered list of beats, each `{ id, section, title? }`, and the helpers `beatIndex(id)`, `phase(index)`, `sectionOf(index)`, `sectionStart(section)`. The single place the talk's order lives. |
| `src/useBeats.ts` | **The engine.** A composable holding the current index and the open door; `next() / back() / goTo(i)`, the keyboard handler, `?beat=N` and `?door=ID` kept in sync by `history.replaceState`, the door origin stored in `history.state`, and a `reduced` flag from `prefers-reduced-motion`. |
| `src/App.vue` | The frame: installs the engine once, lays out ribbon / stage / footer, and decides *by beat name* which extras are on screen (title, door button, takeaway card). Holds the `DOORS` map of door pages. |
| `src/components/Ribbon.vue` | The strip along the top: section names (click = jump to the section's first beat), the current one highlighted, an `N / total` counter, BACK and NEXT buttons. |
| `src/components/Stage.vue` | **The object placeholder.** An SVG disc with three labelled arcs whose appearance is a pure function of the current beat's name, animated by CSS transitions. Replace it with yours. |
| `src/components/TakeawayCard.vue` | The outlined card shown over the dimmed object on the `takeaway` beat. |
| `src/components/Door.vue` | A button that opens a door page from a beat. |
| `src/views/DeeperDive.vue` | The example door page. BACK (button, keys or the browser) returns to the beat the door was opened from. |
| `src/style.css` | Design tokens (`--accent`, `--bg`, `--dur`, …) and base styles. Re-theme here. |
| `src/media.ts` | **The media resolver.** One function, `mediaUrl(name)`, that points at an object-storage bucket via `VITE_MEDIA_BASE_URL` (see `.env.example`) and falls back to `public/` until you have one; carries the immutable-names rule and the `ASSET_VERSION` cache-buster. |
| `tools/shot.mjs` | **The verification tool.** A headless screenshot of any beat at a projected size, optionally after N presses of NEXT; prints console errors. `npm run shot -- <url> <out.png> [presses]`. One-time: `npx playwright install chromium`. |
| `.github/workflows/deploy.yml` | **The deploy.** GitHub Pages on every push to `main`; the base path is derived from the repository name. Move `.github/` to your repo root if you keep the app in a sub-folder (and set the four paths it names). |
| `vite.config.ts` | Vite with the Vue plugin; `base` from `VITE_BASE`. |
| `tsconfig*.json` | Strict TypeScript, split into app and node (config) projects, as `vue-tsc -b` expects. |

## The one rule: ask by name, never by number

Components never test `beat === 4`. They ask `phase` (the current beat's *id*) and answer
"what do I look like on `ch1-highlight`?". Because of this you can insert, remove or reorder
beats in `beats.ts` and nothing else goes stale — only the number in the URL moves. The ids
form a TypeScript union, so a misspelt name is a compile error, and the `switch` in
`Stage.vue` is exhaustive: add a beat and the compiler asks you what the object does on it.

## How to add a beat

1. Add a line to `BEATS` in `src/beats.ts`, in talk order, with a new `id` and its `section`
   (a new section name makes a new ribbon entry automatically).
2. Run `npm run build` (or let the editor tell you): `Stage.vue`'s `switch` now fails to
   type-check until you add a `case` for the new id, describing the object's state on it.
3. If the beat needs an extra element (a card, a door, a caption), gate it in `App.vue` with
   `v-if="phase === 'your-id'"`.

That is the whole procedure. No component counts beats, so nothing else needs editing.

## How to swap the object

`Stage.vue` is the only file that knows what the object is. Keep its shape — read `phase`
from `useBeats()`, compute a small "view" record from it, render from that record — and
replace the SVG with whatever your science looks at: a WebGL globe, a mesh, a map, a specimen
photo, a plot. For something heavy (Three.js, a map library) mount it once in `onMounted`
and `watch(view, …)` to move it; the engine does not care how the object draws itself, only
that its state follows the beat name. Use `reduced` to skip or shorten animation when the
visitor has asked the operating system for less motion.

## Where to read the real thing

This skeleton mirrors the concepts of a full, built-out talk site. When you need more than the
skeleton shows, the counterparts there (paths under its `website/src/`) are:

| Here | There |
| --- | --- |
| `src/beats.ts` | `config/ch1Beats.ts`, `config/ch2Beats.ts`, `config/ch3Beats.ts` (one registry per chapter, with multi-beat segments), `config/introSteps.ts`; the section list in `config/sections.ts` |
| `src/useBeats.ts` — keys | `views/Explore.vue`, the `onPresenterKey` handler |
| `src/useBeats.ts` — `?beat=N` | `views/Explore.vue` (`jumpToBeat`, `navBack`, `navNext`) and `config/sitePath.ts` (`parseBeatParam`, `pathPrev` / `pathNext`) |
| `src/useBeats.ts` — doors | `config/sitePath.ts` (`DoorStop`, `readDoorTrail`) and the door-trail block in `views/Explore.vue` |
| URL handling (hand-rolled here) | `router/index.ts` — vue-router, routes derived from the section registry |
| `src/App.vue` | `views/Explore.vue` (the one view that frames every page) and `components/sections/SectionCh1.vue` … (one component per chapter, each its own beat engine) |
| `src/components/Ribbon.vue` | the `.top-nav` and `.beat-nav` blocks of `views/Explore.vue`; the per-beat sub-menu in `components/BeatLandmarks.vue` + `config/landmarks.ts` |
| `src/components/Stage.vue` | `components/Globe.vue` (the object), `components/TheoryPanel.vue`, `components/TwinGlobes.vue` |
| `src/components/TakeawayCard.vue` | `components/TakeawayPop.vue` + `config/takeaways.ts`; the landing card in `components/ChapterTitleCard.vue` |
| `src/components/Door.vue`, `src/views/DeeperDive.vue` | `components/DeeperDive.vue` + `config/deeperDive.ts`, and the door pages under `components/sections/` (e.g. `SectionMgsim.vue`) |
