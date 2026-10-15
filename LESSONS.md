# Lessons

One line each, imperative, with the why. Every one of these was paid for.
They are grouped, not ranked; the first group is the one to read if you
read nothing else. `DESIGN.md` tells the stories behind them.

## Working with a director

- **Build exactly what the note says.** Take liberties only where the note
  leaves room, and say aloud where you did — a liberty the director did
  not ask for cost a round every time, and two cost a redesign.
- **A named change applies to every instance of the same thing.** Grep the
  old wording before you report done; parking the sibling as "the
  director's call" cost a second round twice.
- **"Better before" means that exact earlier version.** Restore it from
  the commit and compare frame for frame; two reinterpretations of a
  transition the director liked as it was were both rejected.
- **End every update with how to view it**: the URL and the beat. The
  director should never hunt for what changed.
- **Close every report with the judgment calls**, one line each, so a
  liberty is visible rather than discovered.
- **A screenshot with one line is the best note there is.** Ask for them;
  answer with them.
- **Questions get numbers first.** A size, a cost, a count, a derivation;
  then the recommendation; then the decision is the director's.
- **Content is the director's**: which imagery, which clips, which photos,
  which lake, who is named. Offer candidates with a table and a cost, then
  wait.
- **A repeated instruction is a hard rule**, and a question about a term
  means the term is wrong for the room.
- **When the director is not convinced by a physics claim**, write the
  derivation out, state the caveats plainly, have it refereed, and say
  what the words mean rather than the words.
- **Digest, then act.** When notes arrive in a queue with "not yet", confirm
  each in a line and build them as one batch in the order given.
- **Pace is part of the job in the last week.** One throwaway walk per
  change, payload-only rebakes straight to upload, one browser.

## Design and content

- **No prose on screen; the presenter narrates.** Labels that are the
  figure (axes, legends, data callouts) stay; sentences, captions, hints
  and eyebrow titles go.
- **Design for the back row of a projected room**: strokes at least 1.5–2
  px, labels at least about 15 px at 1440×900, no low-alpha greys for
  anything that must be read. A legibility sweep changes sizes, strokes
  and alphas only, never choreography.
- **One deterministic path.** BACK and NEXT in the same place on every
  page, labelled only "next", "back" or the next chapter's name; the
  presenter remote's keys route into the same handlers.
- **Click-driven by default.** Any autoplay is an explicit exception the
  director named.
- **Forward animates, backward snaps.** Back-navigation is a correction,
  not a performance.
- **Chapters grow out of objects.** Find the two or three things the
  audience will watch change before writing a single beat; an object that
  appears once is a figure.
- **One object, never a hole.** A transition from the whole to a model
  domain carves the same mesh in a smooth sweep; never stitch two things,
  fade to black, or leave a hole.
- **Two simultaneous transformations read; three are noise.** Hold the
  camera while the cut and the slab do the work.
- **Match the animation to the director's physical metaphor** before
  polishing it.
- **Equations are off the talk.** Everything that would clutter a beat
  gets a home in a per-chapter deeper dive, which opens with the paper.
- **Derivation text is the paper's own sentences**, with equation numbers
  checked against the published PDF; never invent the text between
  equations.
- **One line or none under a deeper-dive figure.**
- **Fixed axes on every instance of the same plot.** Show a tight view as
  an inset, never by rescaling the frame.
- **A takeaway is written once** in a config and read everywhere it
  appears, so implications and conclusions cannot drift apart.
- **When a visual makes a quantitative claim, project equal-area and keep
  pixels square.**
- **On bright snow, additive blends vanish.** Black contours and alpha
  blending for anything that must be read.
- **Grow text with a transform, never a font tween**, when it must not
  re-wrap.
- **"In the corner" means the lightest possible thing**: no plate, no
  extra lines.
- **Imagery for a day is one pass, never a mosaic.** A resolution step is
  fine; an imagery seam is not.
- **Reproduce a figure the director already has a picture of** and compare
  side by side before shipping; georeference from the data's own
  coordinates.
- **Headshots only from official pages that name the person**, with
  provenance recorded; an initials tile where none exists.
- **Non-public people stay out of any bundle.** A static site ships every
  byte it can render.

## Engineering

- **Registries, not numbers.** Beats, stations and landmarks derive from
  one ordered list; code asks for a phase by name, so cutting a beat is a
  line removed and nothing else moves.
- **Mount the long-lived 3D scene once.** Sections drive it through props
  and emits and own their own easing; everything else is an overlay.
- **Never hide a live WebGL canvas under a flat page.** Flat pages are
  opaque layers above it; a covered canvas renders at a few frames per
  second rather than zero (a cold first frame) or sixty (a GPU backlog).
- **Anything a click reveals must already exist**, compiled and uploaded,
  before the click; warm the next beat's assets in idle time.
- **An asynchronously textured mesh stays invisible until its texture is
  set.** A white plate where the imagery will land is a loading bug, not
  a design bug.
- **A reveal never waits on an asset without a deadline; a fetch is never
  trusted.** Check the status, decode, retry, fall back, warn.
- **Seed every shader uniform from live state at compile.** A material
  compiled after the transition that would have set it keeps zero forever.
- **Avoid `asin`/`acos` in shaders**; compare the monotonic quantity. One
  epsilon past ±1 is NaN and NaN discards everything.
- **Hide every depth-writing sibling, even invisible ones**, when the
  camera goes inside an object.
- **One shared helper answers "where is the surface here".** Never pin an
  overlay at a radius chosen for the summit; rebuild DEM-sampling overlays
  when the DEM arrives.
- **Update anything projected to screen after the camera update, right
  before render.** A one-frame lag is invisible at a steady 60 fps and up
  to 17 px on an uneven 30.
- **Use a bilinear lookup for any overlay geometry that moves over a
  surface**; nearest-pixel makes vertices hop.
- **Two reactive changes in one flush can double-fire a watcher.** Guard
  idempotence; never add a second advance path.
- **Gate hidden components with `v-if`, not opacity**; pass a prop when a
  parent's class is meant to change what a child renders.
- **Hide a huge SVG layer with a visibility cut, never an opacity fade.**
- **Solve a zoom's scale with field of view** when the camera rides a
  fixed ray; dollying cannot get closer than the ray's miss distance.
- **Pre-bake what a slider will show** and preload the grid; a swap during
  a talk must be instant.
- **When you add precision, count unique values in the output.** The
  container format proves nothing.
- **Never flip y silently.** A map-frame extent handed to a north-up warp
  put a basemap 62 km off for a week; verify basemaps by correlation in
  the site's projection.
- **Look at the contact sheet of every built raster before uploading.**
- **Real LaTeX for every equation**, through a deterministic pipeline, so a
  re-bake is byte-identical and only new names are ever uploaded.

## Storage and the network

- **All media in object storage, only code in git.** One resolver for
  every asset URL, including the ones hiding in CSS.
- **Objects are immutable: new bytes get a new name.** Once the one-year
  cache header is on, overwriting in place serves old bytes for a year.
- **A preload uses the same request mode as its consumer.** A URL used
  both as a plain image and as a WebGL texture needs two cache keys; the
  origin answers no-Origin requests without CORS headers and without
  `Vary: Origin`, so the plain entry poisons every later texture load.
- **HTTP 200 is not a render.** For anything that affects pixels,
  screenshot it and look.
- **Any Playwright route handler disables the HTTP cache.** Measure loading
  on a production build behind the real headers with no routes.
- **Suppress the output of any command that may echo credentials**; rotate
  on exposure.
- **Never run a bucket read with an unvalidated key.** An empty key is the
  whole bucket.
- **Say what an upload will cost before uploading it.**

## Verification

- **Verify as the audience will see it**: the live origin, both browser
  engines, the user's cache and click path, at the projected size.
- **Headless only, GPU-rendered, one browser at a time.** A headed window
  jumps onto the presenter's desktop; three parallel browsers froze a
  16 GB laptop; software-GL headless renders at under one frame per
  second.
- **Press the real buttons.** Deep links preload everything; the audience
  arrives by NEXT. A scripted click is not a click: verify with a real
  mouse click and a hit-test.
- **Measure, don't guess.** DOM rectangles across viewport sizes before
  claiming no overlap; luma traces for flashes; rAF gaps alongside long
  tasks; a CPU profile before naming a cause.
- **Gate every globe screenshot on texture readiness**, and make the gate
  know that loads have started.
- **A settle time must exceed the rig's own warm-up**, or you measure the
  rig.
- **Instrument timing inside the page.** Tool latency masquerades as an
  animation bug.
- **Film long choreographies at a known frame rate**; per-frame grabs
  drift. Inject uneven frames to see a one-frame lag.
- **Never debug GPU state from an occluded window**; the compositor stops
  presenting and your screenshots are stale.
- **A live-site complaint is usually loading**, not choreography filmed
  with everything preloaded. Hold the asset back and film again before
  touching the design.
- **The build is the gate.** Run the production build after the last
  edit; the dev server tolerates what the type checker rejects.
- **Another agent's "verified" can be stale.** Re-shoot one thing per
  change yourself.

## Process and tooling

- **One worktree per parallel session or agent**, its own branch, port and
  build cache; never stash in a multi-worktree repository.
- **Commit by pathspec in a shared checkout**, and print the branch in the
  same command as the commit.
- **Stop servers by port, never by a shared process name.**
- **Never `rm -rf` in an agent.** Leave a stray path and report it.
- **Trial-merge before deleting a branch**; squash-merges make the merged
  flag lie.
- **Brief current beat numbers from the registries, never from memory.**
- **Review and land work from a misrouted session rather than redoing
  it.**
- **Pipelines read copies, never originals.** One fetch script fills a
  git-ignored source folder; extend it when a dataset is needed.
- **Build the riskiest beat first**; if it works the rest is incremental.
- **Mock up layouts before coding them**, and expect the simpler one to be
  chosen.
- **Record how each change was verified alongside the change.**
- **Keep a design log as you go.** This repo exists because one was kept.
