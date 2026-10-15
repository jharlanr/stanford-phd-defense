# Design log

This is the record of how a PhD-defense talk became a website, written
for the next person who wants to build one — and for the coding agent
they will point at this repository. It is organised the way the work
happened: first the working relationship that produced everything else,
then the handful of ideas that organise the site, then the build phase by
phase, each phase ending with what it taught us.

Every decision is labelled as a **choice**, with the alternative that was
seriously considered and the reason the choice won. You are meant to
disagree with some of them. The few things presented as rules are the
ones about the audience, and they are the ones we would not bend.

The cast: **the director** is the student who gave the talk; **the
studio** is the AI coding agent (at busy times, a lead session with
several parallel agents) that built the site. The build ran for about
five months of calendar time and roughly thirty-six working days, most of
them in the last seven weeks before the defense.

---

## 1. How the director and the studio worked

This is the most reusable thing in the repository. The site is one
scientist's; the way of working is not.

### Roles

The director decided what the audience should see and judged the result.
The studio decided how to build it, built it, verified it, merged it, and
reported back. The director never opened the code; the studio never
chose the content. Where the line blurred — a framing, a scale, a word
on screen — the studio proposed and the director decided.

### What a note looked like

Notes were **short and literal**, usually a numbered batch after the
director had watched the site or given a practice talk, with the design
reason attached when it mattered ("to save room", "for the back of the
room", "so people catch on from the lake number"). The studio built
exactly what was said. A liberty survived only where the note left room,
and only if the report said so.

**A screenshot with one line was the best note of the project.** A
cropped picture of the screen and "the M is crossing the frame" located
a layout bug faster than any description. Screenshots found a basemap
that was 62 km off, a lake cut off at an inset's edge, the exact camera
framing the director wanted (recovered by fitting six known points to the
pixel), and which tiles were meant in a grid. If you take one practice from
this document, take that one.

In the last week the director **queued notes with "not yet"**, then
released them as a batch. The studio confirmed each in one line and built
them in one chain, in the order given.

### What the studio did with a note

1. Built it literally, in a branch, with the build as the gate.
2. Verified it as the audience would see it: a headless browser at the
   projected size, pressing the real NEXT, sweeping window sizes when a
   layout claim was involved.
3. Merged its own pull request without waiting.
4. Reported with **how to view the result** — the URL and the beat
   (`/chapter1?beat=10`) — and closed with **the judgment calls for the
   director's eye**, one line each, so a liberty was visible rather than
   discovered.

Questions got **numbers first** (how a 30 GB transcode fits a free tier;
whether the size card is right; whether a pass bar is unanimous), then a
recommendation, then the decision was the director's. Physics questions
got a derivation and an adversarial check before anything went on screen.

### What went wrong when the studio took liberties

Each of these became a rule, and each cost at least a round:

- A transition redesigned twice when the director preferred it as it had
  been. Rule: **"better before" means that exact earlier version**,
  restored from the commit and compared frame for frame.
- A dive redesigned on a misdiagnosis (the studio thought a flash was
  choreography; it was a texture still loading) and judged worse. Rule:
  **a live-site complaint is usually loading**; reproduce with the asset
  held back before touching the design.
- A card given an extra eyebrow and a lit rectangle; a plate with labeler
  numbers under faces the director had asked to be bare; a readout kept
  small after the director had said to remove it. Rule: **"in the corner" means the
  lightest possible thing**, and "remove" means remove.
- Long captions under figures the director narrates. Rule: **one line or
  none**.
- Siblings of a named change parked as "the director's call", twice.
  Rule: **a named change applies to every instance of the same thing**;
  grep before reporting done.

### What made a note effective

It named the thing on screen; said why; pointed at something already on
the site ("do what you did for the other centre lake", "like the
Additional Work panel"); and gave a number when one existed (a clock
time, a scale range, a count of beats).

### Decisions the director kept

Content — which imagery, which clips, which photos, which lake for the
demo, who is named and how; scale and framing calls; anything that would
change the paper. The studio offered candidates with a table and a cost,
and waited.

### Pace and safety

In the final week the director said plainly when the studio was slow,
and the studio adapted: one throwaway verification walk per code change,
payload-only rebakes straight to upload, one browser at a time. Safety
ran both ways: the studio reported when a credential had been echoed
into a log, when a public repository turned out to hold keys, and when a
bucket read had been too broad; the director ran the one command the
studio's permissions refused.

---

## 2. The ideas that organise the site

**Objects, plural.** The site is not slides with pictures; it is a small
number of three-dimensional objects the audience watches change. The
whole talk handles four: the Greenland mesh on a globe (the director
called it "the greenland object"), a simulation block carved out of it,
an idealised slab of ice, and a pair of twin Greenlands with sliders.
Chapters grew out of these objects, not the other way round. When a beat
could not be expressed as something happening to an object, it was
usually a slide in disguise and was cut or moved to a deeper dive.

**Beats and one path.** Every chapter is an ordered list of named beats,
each a press of NEXT, each with a URL. There is one deterministic path
through the whole site, driven by the arrow keys or a presenter remote,
and BACK and NEXT sit in the same place on every page. Visitors can
wander through a menu; the talk is one route through it.

**Registries, not numbers.** Beats, sections, landmarks and the stations
of a chapter are declared once in ordered lists, and code asks "which
phase am I in" by name, never by index. Cutting the two elastic beats on
the last day was a two-line change and nothing else moved.

**The narrator rule.** No prose on screen. The presenter speaks; the
screen shows. Labels that are the figure stay (axes, legends, a lake's
number); sentences, captions, eyebrow titles and hover hints go. The
exceptions are the ones the director asked for by name.

**Doors and the deeper dive.** Anything that would clutter a beat —
equations, supplementary fields, the paper itself — has a home on a
per-chapter "deeper dive" page under Additional Work, reached by a door
button on the beat. BACK from a door returns to the beat it was opened
from.

**Takeaways written once.** Each chapter's one-sentence conclusion lives
in one config and is read by the chapter's last beat, the implications
page and the Conclusion, so they cannot drift apart.

**Flat pages float above a live globe.** The 3D scene is mounted once and
never hidden; pages that need a flat layout are opaque layers above it.
Every way of hiding the canvas cost seconds on the next landing.

**Media lives in a bucket with immutable names; the repo holds code.**
See `OPERATIONS.md`.

---

## 3. The build, phase by phase

### Phase 1 — A stack picked and thrown away

Day one scaffolded the conventional thing: rendered equation animations
(Manim), a Markdown slide shell to click through them (Slidev), a
pre-rendered spinning globe as the opening shot, and a plain fallback
deck. The same day fixed the narrative arc — one scientific question,
chapters placed in the order of the argument rather than of publication
— and a tiering of which chapters deserved cinematic treatment.

- **Choice:** click-through steps the presenter advances by hand.
  **Instead of:** a passive video. **Because** the talk is narrated live
  and the presenter sets the pace.
- **Choice:** chapters ordered by the argument. **Instead of:**
  publication order. **Because** the order of the papers is an accident
  of peer review.

What went wrong: pre-rendered clips could not preserve the globe's
orientation at the instant of a click, so it jumped between its spin and
its zoom. Within a day the opening moved to live WebGL; within two the
slide shell and the fallback deck were deleted — the director preferred
one format to two.

Lessons: build the riskiest beat first; decide tiering before building;
prefer live rendering to video wherever continuity across a click
matters.

### Phase 2 — The live globe

A Three.js scene replaced the clips: a spinning globe with satellite
tiles, a zoom that captures the current orientation so there is no jump,
a fade to black leaving Greenland's silhouette, Greenland rising as an
ice mound (the bed-and-surface dataset displaced along the sphere normal
at about 90× vertical exaggeration), and ice-velocity streamlines (a
47 GB velocity product subsampled to a 1.7 MB grid and traced into a few
hundred polylines, coloured by speed). The first headless screenshot
script appeared the same day, so the studio could see its own renders.

- **Choice:** a "flatten Greenland" click was scrapped. **Instead of:**
  morphing the sphere segment to a plane. **Because** over 24° of
  latitude a tangent plane visibly distorts the shape, and from any
  reasonable camera the curved segment already reads as flat.
- **Choice:** alpha blending with depth test off and an explicit render
  order for the streamlines. **Instead of:** additive blending, or a
  radius offset. **Because** additive over near-white snow clamps to
  white, and the basemap's polygon offset beats any geometric offset.

What went wrong: dimming the basemap looked unchanged because the
renderer applies linear maths and then encodes to sRGB; the elevation
field needed a blur because fjord detail became spikes at 90×.

Lessons: verify renders with a screenshot — the director should not be
the studio's eyes; never use additive blending for anything that must be
read on snow; the colour pipeline is part of the design.

### Phase 3 — From a deck to an explorable site

The explorable website became the target: a standalone Vite + Vue 3 +
TypeScript app with the globe as a component, asset URLs relative to a
base path for GitHub Pages. The landing became "click on Greenland to
begin"; the opening a single combined seven-second motion ending in a
vertical gold menu that collapses to a top bar once a section is chosen.
Orbit controls let a visitor drag the globe; the scripted camera resumes
after an idle delay. Hillshade moved into the fragment shader with a
world-fixed sun.

- **Choice:** the defense is one click-path through the public site.
  **Instead of:** a separate defense deck. **Because** one artifact, one
  deterministic sequence, and the audience leaves with the same URL.
- **Choice:** forward clicks animate, backward clicks snap to the end
  state. **Instead of:** reversed animations. **Because** back-navigation
  is a correction, not a performance.
- **Choice:** the menu, not a click counter, is the navigation
  primitive. **Because** visitors wander; the presenter's path is one
  route through the menu.

What went wrong: a view-offset call mutated the camera aspect and its
inverse did not restore it, so the globe rendered egg-shaped after
returning to the hub; orbit controls fired on a plain click and froze
the opening mid-flight; three silvery 3D dimension arrows were built and
hidden because they cluttered Greenland instead of measuring it.

Lessons: mount the long-lived 3D scene once and treat everything else as
an overlay; surface phases as named states the parent toggles, never
sequence numbers inside a component; record how a change was verified
alongside the change.

### Phase 4 — The first cinematic moment

A three-second sweep carries a cut longitude from the coast to the
central dome; everything east of the cut disappears, and a shader-drawn
cross-section at the cut paints bedrock, a blue ice column and gold
interface lines. Beside it a gold arrow spans bed to surface, dashed
lines connect its tips to an inset of six procedurally modelled
skyscrapers for scale, and a card shows Greenland's silhouette over the
contiguous United States at true relative area.

- **Choice:** animate the cut's position, a binary cut at every instant.
  **Instead of:** fading the east half. **Because** the director's mental
  model was a cutaway melting from one side, not a depth fade.
- **Choice:** per-fragment discard with derivative-based anti-aliasing.
  **Instead of:** per-vertex discard. **Because** vertex discard
  stretched texels along wall triangles.
- **Choice:** the scale card is flat HTML in equal-area projections.
  **Instead of:** outlines on the sphere, an imagery decal in the tangent
  plane, or equirectangular crops — all built and removed. **Because** a
  size comparison that is not equal-area is dishonest; at that latitude
  the equirectangular stretch is about 1.25×.

What went wrong: the slab first spanned so deep that bedrock looked as
thick as the ice; a pinstripe in the ice column was wall triangles that
were never discarded; a "ramp jumps to the end" measurement was the
screenshot tool's own latency.

Lessons: when a visual makes a quantitative claim, project equal-area and
keep pixels square; match the animation to the director's physical
metaphor before polishing it; instrument timing inside the page.

### Phase 5 — Going live, and media to a bucket

The menu became six cards whose thumbnails come alive on hover. Version
control was initialised, the website folded under one umbrella
repository, and the first Pages deploy went live on every push touching
the website folder, with a no-index tag until the defense. Then every
media file moved to an object-storage bucket behind one `mediaUrl()`
resolver, and the repository's public folder shrank to a robots file.
The site promptly went live with a black globe: WebGL textures need CORS
headers and the bucket sent none.

- **Choice:** keep the vertical menu and upgrade the buttons to live
  cards. **Instead of:** four alternative layouts mocked up in ASCII.
  **Because** the director found the existing menu fine and wanted the
  imagery to come alive, not a new layout.
- **Choice:** all media in object storage, only code in git — one rule.
  **Instead of:** small files local, big files remote. **Because** files
  do not divide naturally by size, and a clean boundary was affordable
  early.
- **Choice:** a zero-egress object store. **Instead of:** S3, a video
  CDN, a custom media domain. **Because** video egress is the dominant
  cost and no personal domain was wanted.

What went wrong: two type errors the dev server tolerated broke the first
CI build; a configuration command echoed a credential into the
transcript and the token was rotated; the CORS failure was caught by the
director — a HEAD request returning 200 had been taken as proof of a
render.

Lessons: HTTP 200 is not a render; anything consumed by WebGL, a canvas
or cross-origin video needs CORS from its origin; suppress the output of
commands that may echo credentials; one resolver for every asset URL,
including the ones hiding in CSS; mock up layouts before coding them and
expect the simpler one to win.

### Phase 6 — Chapter 1 begins; deep links; a side door for fieldwork

Two studio sessions worked in parallel for the first time, in separate
worktrees and ports. Chapter 1 gained a camera-focus prop (a section
requests a target; the globe glides there and restores on exit), a
latitude knife through the first lake's catchment with a cross-section
slab, and eased morphs. The site gained `?beat=` deep links and
history-mode routes with the standard Pages 404 shim. Three helicopter
clips from the field season — chosen by the director from a 65 GB archive
— were transcoded from 4K to 1080p (1.1 GB to 114 MB) and became a side
page: a satellite basemap reprojected to a local plane, clickable GPS
tracks, a synced video, and a field-of-view wedge turning with the
heading.

- **Choice:** fieldwork is a side door — its own card, absent from the
  top navigation and from every NEXT flow. **Instead of:** another
  chapter. **Because** footage is a parallel track, not a checkpoint in
  the argument.
- **Choice:** imagery from a pass two weeks before the flight, reprojected
  to a local tangent plane. **Instead of:** the flight day (a swath gap),
  or pre-distorting the image. **Because** it was the only clear pass
  with bright lakes, and at 68.6°N equirectangular stretches longitude
  about 2.7×.
- **Choice:** the camera stays put during the cross-section reveal.
  **Instead of:** swinging face-on. **Because** cut, slab and camera at
  once was too much; two simultaneous transformations is the right
  number.

What went wrong: an `asin()` in a shader returned NaN one epsilon past
±1, and NaN discarded every fragment on the island; the canvas capture
returned black where the buffer cleared between frames.

Lessons: compare the monotonic quantity instead of calling `asin`; give
parallel sessions their own worktree, branch and port; gate "copy
everything" against the destination's quota; keep a deep link for every
state the studio needs to screenshot.

### Phase 7 — Hardening the Greenland object

The reveal was rebuilt so the knife sweeps north from the island's tip
and the cross-section is the knife's visible face, driven by one uniform
in lockstep with the cut. Every overlay now drapes on the real surface
through one shared elevation-readback helper. A latent shader bug was
found that flattened the dome whenever a cut was active. An audit
removed about 830 lines and folded two coordinated props into one, and a
scene-dump call started writing its JSON beside every screenshot. The
surface itself was rebuilt: the elevation pipeline in float32 packed as
16-bit, and a 72 MB high-resolution basemap that shows the lakes
natively. Chapter 1 opened on a clickable lake — a real-size polygon, a
black contour, a pulsing ring — that plays its drainage movie.

- **Choice:** the moving slab is the knife face: one uniform, one
  motion. **Instead of:** a streamline-following ribbon. **Because** the
  ribbon was geometrically truer but popped in mid-animation; one
  coordinated motion reads as one object.
- **Choice:** two elevation textures at two smoothings (about 1.5 km for
  displacement, 750 m for hillshade). **Instead of:** one. **Because** the
  smooth one had no gradient for shading and the interior read as fog.
- **Choice:** a black contour and an alpha-blended ring for the lake
  beacon. **Instead of:** an additive cyan halo. **Because** additive
  adds light to white.

What went wrong: a "3D-printed" pixelated look survived a mesh
subdivision because the data was the problem — a column down the dome
held 231 unique values in 3,600 pixels, 8-bit data inside a 16-bit file.
The basemap fetch deadlocked at 4.4 GB with a thread per tile. The
studio's 1440×900 screenshots could not show banding the director saw on
a high-density display.

Lessons: when you add precision, count unique values in the output;
verify at the director's display resolution; one shared helper answers
"where is the surface here"; dump scene state beside every screenshot
and let the director tune a camera by hand and paste the numbers back.

### Phase 8 — The reframing, seven weeks out

After a long gap for the written thesis, the talk became three chapters
plus an Introduction, Conclusion, Acknowledgements, Additional Work and
References, with a section registry as the single source of truth for
identity. A local mirror of the bucket, served by the dev server with
byte ranges, took the basemap from thirty seconds to a tenth of one, and
the screenshot tools learned to wait on a texture-readiness gate. Two
standing rules landed: **director/studio** (the director prompts; the
studio implements as it sees fit and always ends by saying how to view
the result) and **copy, never touch originals** (a fetch script copies
source datasets into a git-ignored folder; pipelines read only copies).
Chapter 1 grew to its full arc in an evening: water draining from the
slab, simulated stress painted on the cross-section, a morph to the
idealised slab, a derivation on an SVG chalkboard, and the closing drape
of the chapter's quantity over the whole ice sheet.

- **Choice:** build exactly the one closing beat the director picked of
  four offered. **Instead of:** all four. **Because** three were
  explicitly not selected.
- **Choice:** a perceptually ordered palette for the coupling-length
  map. **Instead of:** the paper's rainbow. **Because** monotonic
  lightness reads on white ice.

What went wrong: Playwright's `waitForFunction` options were passed in
the wrong slot, so every "black basemap" screenshot was taken before a
75 MB texture finished loading; a drape rendered flat on deep links
because its exaggeration uniform was written only during transitions.

Lessons: seed every shader uniform from live state at compile; a
readiness gate must know loads have started, not only that none are
pending; end every update by saying how to view it; re-read the calendar
before recommending "leave it".

### Phase 9 — The narrator rule

Four rounds of numbered notes in one day. Every Chapter 1 animation
switched to the paper's linear-rheology ensemble, for which the analytic
result is exact, so the theory overlays sit on the simulation curves by
construction. Then the rule that shaped everything after it: every blurb,
eyebrow title, caption, hover hint and narrative button label was
removed. The chapter component became headless (it only emits); NEXT and
BACK are plain pills; figures take the full screen; equations live inside
the figures; the finale became two live 3D Greenlands side by side.

- **Choice:** the presenter narrates; no prose on screen. **Instead of:**
  captions and hints for self-guided visitors. **Because** in the room
  the words are spoken, and on screen they compete with the figure.
- **Choice:** the exact linear ensemble everywhere. **Instead of:** the
  nonlinear hero run whose tails mismatch the analytic curve. **Because**
  exactness makes the collapse tight and removes a caveat the audience
  cannot absorb in a talk.
- **Choice:** two real 3D globes for the finale. **Instead of:** a
  two-panel image (shipped first and flagged). **Because** the director
  wanted handled objects, not a figure.
- **Choice:** three morph choreographies shipped behind a URL parameter.
  **Instead of:** picking one. **Because** the director expected to
  iterate; a filmstrip of all three is cheaper than three rounds.

What went wrong: a "texture already loaded" guard was never reset on
dispose, so revisiting the slab painted it black; switching lakes reused
a popup instance; a repository audit the same day deleted the abandoned
animation folder, the early planning documents, every merged branch and
every unreferenced bucket object.

Lessons: no prose on screen; reset cached guards wherever a mesh is
disposed and key reused components on identity; never uppercase Greek
letters with a text transform; once parallel work ends, keep one
checkout and prune everything together.

### Phase 10 — One object, never a hole

Chapter 1's transition to the idealised model became the "seam": the
slab levels and unrolls onto the tangent plane, the water column fades,
the slab spins so flow matches the model's left-to-right, and the camera
dives on a solved fit so the theory panel's field image lands pixel-
aligned over it — a four-unknown Newton solve on focal point, field of
view and exaggeration, accurate to under half a pixel. Chapter 2 opened:
the simulated lakes on the island, then a drain and a carve down to the
25 m simulation tile with the published stress draped on it. The
director's verdict on the first carve — a hole in the island — produced
the rule of the Greenland object: a transition to a model domain cuts
away the rest of the topography in a smooth sweep while the domain is
immune, then zooms; never stitch, fade, or hole. Three carve styles
shipped behind a parameter; the knife was locked, and the domain became
a solid block a visitor can orbit.

- **Choice:** solve the dive's scale with field of view, not distance.
  **Because** the camera rides a fixed ray and can never get nearer than
  the ray's miss distance; a near-orthographic view suits a flat diagram.
- **Choice:** the knife sweep spans the lake's neighbourhood. **Instead
  of:** the whole island. **Because** an island-wide sweep crossed the
  visible frame in 200 ms of a 3.8 s motion.
- **Choice:** inside the footprint the coarse skin stays opaque and
  sinks under the tile while the tile fades in. **Instead of:** fading
  the skin (a black halo) or collapsing it (a second bright square).
- **Choice:** crop the basemap once for the tile. **Instead of:** a fresh
  full-size texture per tile. **Because** resizing a 16k-pixel texture on
  the main thread froze the renderer for seconds.

What went wrong: the drain never animated for a freshly clicked lake —
two watchers fired in one reactive flush and the second killed the
first's timers (fixed with an idempotence guard); software-GL headless
Chromium rendered at under a frame per second, so choreography films
moved to a real GPU.

Lessons: two reactive changes in one flush can double-fire a watcher;
verify long choreographies with video at a known frame rate; a mesh that
renders nothing is usually off-frame — check camera maths before
shaders.

### Phase 11 — The block becomes the paper

The Chapter 2 block grew the paper's observation–simulation comparison:
the tile lands on pre-drainage imagery, a "drain the lake" pill
crossfades to the post-drainage face, the drainage catalogue's outlines
fade in with their classes, model pills drape the stress response and
open a stress-space panel. The end of Chapter 1 glides into Chapter 2's
exact opening framing before the route flips. Then the quantitative
layer: sliders on the twin globes backed by a pre-baked 5×5 grid of
drapes, boundary-condition cards with wall arrow fields and baked
equation chips cross-checked against both the solver's input files and
the paper's supplement, and warm builds for every heavy scene after a
profiler showed shader compiles and a 1.7 s scene build landing on the
click.

- **Choice:** pre-drawn, visibility-switched outline meshes. **Instead
  of:** one mutable canvas texture. **Because** slightly more GPU memory
  buys zero runtime texture updates.
- **Choice:** fixed axes on the slider stage. **Instead of:** rescaling
  as parameters move. **Because** a rescaling axis hides the change the
  slider is making.
- **Choice:** hand off chapters by making the end of one match the start
  of the next. **Instead of:** a cut. **Because** the same-object rule
  applies across chapters too.
- **Choice:** validate every on-screen boundary condition against both
  the run files and the paper. **Because** they disagreed in places; the
  site must not quote either without the director's decision.

What went wrong: hours were lost to canvas updates that never reached the
screen because the headed browser window was occluded and the compositor
had stopped presenting; a 5 s single-frame texture upload on deep links
because a paused globe never rendered.

Lessons: never debug GPU state from an occluded window; hide every
depth-writing sibling when the camera goes inside the object; anything a
click reveals must already exist, compiled and uploaded; when the paper
and the run inputs disagree, record both and ask.

### Phase 12 — The bed ensemble and the cache poison

Additional Work got its first real door: a page that reuses the
simulation-block object to show ten alternative bed topographies under
one lake, each with its stress response, and a stress space with the
other beds as a faint cloud. The bed and walls rendered in every dev
screenshot and in none of the director's live views. The cause took two
rounds: a plain image preload had cached a non-CORS response, and the
WebGL loader was then refused the same URL — invisible in dev because
the dev proxy is same-origin. The fix was a preload in the consumer's
request mode, then a version stamp on every remote URL because the
director's browser still held the old entries.

- **Choice:** show the ensemble's response at its own ±400 kPa scale
  plus a "change versus the published bed" view. **Instead of:** the
  chapter's ±1 MPa scale. **Because** the per-bed differences were a few
  colour levels at ±1 MPa — invisible by construction.
- **Choice:** stamp a version query on every remote asset URL.
  **Instead of:** relying on filenames. **Because** one query string is a
  fresh cache key for everything at once.
- **Choice:** one linear flow on the page, one primary button at a time.
  **Instead of:** every control at once. **Because** the director's first
  impression was confusion.

Lessons: verify under the user's conditions — live origin, the user's
cache, the user's click path, not an empty-cache dev proxy; a preload
uses the same request mode as its consumer; same name plus new bytes
needs a new cache key, every time.

### Phase 13 — Flat pages above a live globe; the timeline; the white flash

Additional Work became a flat card grid above the still-rendering globe,
and the rule came with it: every way of hiding the canvas (`v-show`,
visibility, opacity) made the next simulation landing stall for tens of
seconds, so flat pages are opaque layers above it. The Introduction
gained a literature timeline — stylised title cards, a year axis,
citation arcs verified against CrossRef, author/year pills that pop large
for the back of the room. The fly-along was built: the globe strips its
paint, flattens, and dives to a satellite crop where helicopter tracks
appear and play their clips. Then the white flash: the director reported
a bright flash before the imagery landed; the studio diagnosed
choreography and built a swing, a halo and a dimming, which the director judged
much worse. The real cause was a mesh that is white until its texture
arrives. The design changes were reverted to the exact prior commit and
the mesh now stays invisible until textured.

- **Choice:** stylised cards rather than publisher first pages.
  **Because** reusing copyrighted page images needs the director's
  explicit agreement.
- **Choice:** citation arcs from each DOI's reference list. **Instead
  of:** the studio's reading of who answers whom. **Because** the arcs
  must mean one checkable thing.
- **Choice:** one coordinate frame shared by the globe patch and the flat
  map. **Instead of:** two frames crossfaded. **Because** the cut is
  invisible only if the two read as one image.
- **Choice:** hide a huge SVG layer by a visibility cut, never an opacity
  fade. **Because** any opacity below one on a 15-megapixel layer froze
  frames for seconds.
- **Choice:** GPU-rendered new headless Chromium for all verification,
  no headed windows. **Because** the old headless shell was software GL
  at under a frame per second, and headed windows jumped onto the
  director's desktop during work.
- **Choice:** verify buttons with a real mouse click and a hit-test.
  **Instead of:** scripted `element.click()`. **Because** a NEXT button
  passed every scripted check while being dead for a human; a layer had
  made it pointer-transparent.
- **Choice:** each parallel session works in its own git worktree.
  **Because** the index is per checkout, and one session's commit swept
  another's staged branch into a docs commit.

Lessons: never hide a live WebGL canvas under a flat page; a complaint
about the live site is a complaint about loading; a scripted click is not
a click; take citation metadata from the DOI record, not memory.

### Phase 14 — Chapter 3 and the fieldwork season

Chapter 3 became a beat engine in Chapter 1's grammar: five example lakes
on the globe with callout panels playing their imagery (leaders placed
by a layout solver per viewport), a 3D-to-flat move into a strip map
where every lake's polygon breathes with its daily water fraction, a
live labeling demo, the inter-rater matrices, and later a layer-by-layer
walkthrough of one lake through the paper's trained network. The
fieldwork door grew into the whole flying season: a basemap per date, 27
clips over four days, a local-time clock, station positions from the
published paper, and a row of candidate imagery passes for the director
to judge — never a mosaic. A basemap was 62 km off for a week: a
map-frame extent (y down) handed to a north-up warp. The symmetric
detail crop was immune and coast looks like coast; one screenshot of a
lake cut off at the inset's edge found it.

- **Choice:** solve the callout layout per viewport. **Instead of:** a
  hand layout from the director's sketch. **Because** the five lakes
  project 30 px apart, and any hand layout crossed a neighbour's leader.
- **Choice:** the imagery for a day is one satellite pass. **Because**
  the director could see composite seams; a resolution step is fine, an
  imagery seam is not.
- **Choice:** offer every candidate pass in the legend, dimmed where it
  misses the array. **Instead of:** pre-rejecting on a cloud score.
  **Because** the director judges imagery, and a cloud mask over snow
  misses bright cloud.
- **Choice:** nothing uploaded without the director's selection —
  inventory, table, recommendation, cost, then wait.

What went wrong: two framings of one beat with byte-identical camera
state — the lakes had been built before the elevation data decoded and
sat at sea level, a race that looked temporal; a tutorial card's outline
was 15 px off because the raster transform came from the search window
rather than the tile.

Lessons: overlays that sample the elevation data rebuild when it
arrives; never pass a map-frame extent to a warp without flipping y, and
verify basemaps by correlation in the site's projection; look at the
contact sheet of every built raster; reproduce a figure the director
already has and compare side by side; merge your own pull requests.

### Phase 15 — The comb-through

Three weeks out the director returned from the written thesis with a
plan: go through the site in order and correct as you go, in batches by
section. The Introduction went headless; a References page took every
entry from CrossRef or the data archive; one site-wide BACK/NEXT pair
derived from the registry; Chapter 3 got a beat registry so three
parallel agents could land in any order. Then a long day with up to
seven agents: real LaTeX equations through a TeX-to-SVG pipeline,
per-chapter deeper-dive pages, a sub-menu rail of landmarks, Chapter 2's
tiers and boundary-condition cards, Chapter 3's epoch axis. The Chapter 2
zoom was redesigned twice and rejected twice before being restored
exactly from the reference commit. Then the presenter remote (its keys
route into the same handlers the pills call), the labeler door with its
Worker, an immutable one-year cache header on every object, and a
pre-warm audit on a production build with the real headers: 64 real
NEXT presses, cold and warm.

- **Choice:** one ordered beat registry per chapter; components read
  names, never numbers. **Because** three agents changed one line each
  and merged in any order.
- **Choice:** real LaTeX for every equation, deterministic bakes.
  **Instead of:** a plotting library's math text. **Because** the
  director found that font poor, and a byte-identical re-bake means only
  new names are ever uploaded.
- **Choice:** the deeper dive is a per-chapter page under Additional
  Work. **Because** the talk shows no equations; everything that would
  clutter a beat needs a home.
- **Choice:** restore the original zoom exactly. **Instead of:** a third
  reinterpretation. **Because** two in a row had lost.
- **Choice:** the remote is a keyboard; route its keys into the existing
  navigation. **Instead of:** a presenter mode. **Because** one path, one
  implementation, rehearsable with the laptop's arrow keys.
- **Choice:** visitors' labels go to the bucket through a Worker under
  unguessable keys. **Instead of:** a download (the director did not want
  a save dialog) or a private repository through a token (built, then
  reverted as no simpler).
- **Choice:** under an opaque page the globe renders one frame per
  250 ms, not zero. **Because** a hidden canvas at 60 fps built a 4 s
  GPU backlog that froze the next step, and a full pause left a cold
  first frame.
- **Choice:** agents never stash; each dev server gets a private build
  cache. **Because** the stash is repo-wide and two agents swapped work
  through it; shared caches blanked each other.

What went wrong: an agent reported the build passing but had built
before its last edit, and the deploy failed on an unused variable; a test
script ran a bucket read with an empty key after a failed POST, which
streams the whole bucket.

Lessons: the build is the type check — run it after the last edit;
restore, don't reinterpret; never run a bucket read with an unvalidated
key; a hidden 60 fps canvas under an opaque layer is a GPU queue waiting
to bite.

### Phase 16 — The practice-talk rounds

After a practice talk the director sent ten notes, then a second batch,
then a third, each built by five or six agents and merged the same day.
The standing complaint — not enough contrast for the back of a 50-seat
room — became **the back-row rule**, and two sweeps over every page
changed sizes, strokes and alphas only. Chapter 2 was rebuilt to the
director's path: a second centre lake reached by a "hop" with no return
to the overview, tier buttons kept as headings, equations off the talk,
a pulsing emphasised axis, a teaser cycling ten beds. The Conclusion
became a NEXT path where each takeaway pops. Chapter 3 gained a real
implications page and a results sequence that plays training and rolls
back to the best epoch. Chapter 1's cards grew. Acknowledgements stepped
by group with headshots from official pages only.

- **Choice:** judge every page from the back row — strokes at least
  1.5–2 px, labels at least about 15 px at 1440×900, no low-alpha greys
  for anything that must be read.
- **Choice:** the hop is a 220 ms dip to black with the second block
  landed underneath. **Instead of:** a second block slot to animate
  between lakes. **Because** the globe holds one block, the director had
  said twice not to return to the overview, and a brief black is cheaper
  than doubling the machinery.
- **Choice:** the takeaway pops by scaling the whole block as a
  transform. **Instead of:** animating font size. **Because** font
  changes re-wrapped the text mid-pop.
- **Choice:** the colourbar moved up under the pills rather than left.
  **Because** there was no room left; the request could not be met
  literally and the report said so.

What went wrong: an agent stopped its dev server with a process-name
kill that matched every agent's wrapper and took down five servers; a
cleanup `rm -rf` of an agent's own mistyped directory got every later
command of that agent refused.

Lessons: design for the back row; transform, never font size; stop
servers by port; never `rm -rf` in an agent — leave a stray path and
report it.

### Phase 17 — The last week: the slab, the physics, one browser

Three days out, nine queued notes were released at once. The large item
was a theory segment for Chapter 2: an idealised slab with the 3D surface
stress painted on it, a depth-averaging beat (the paint is the cumulative
average through the twelve node layers), then a nadir view with
Simulation | Theory | Difference panels and sliders, the analytic
solution ported from a notebook with a self-test. Every chapter now ends
on a takeaway beat. A polygon lag that had "measured clean" in headless
was finally understood: the overlay projected with the previous frame's
camera, invisible at a steady 60 fps and up to 17 px on the director's
uneven 30. Two days out the director asked whether the elastic model's
absolute stress fields mean anything; they do not, and a read-only
referee agent checked the superposition the chapter would show instead,
ranked the caveats, and later refereed the written justification a
second time. Chapter 2 was rebuilt to flow in time with its stations as
live controls on every beat.

- **Choice:** never paint the elastic absolute fields; paint the
  superposed state and label its definition. **Because** the absolutes
  depend on an unstressed reference no ice sheet has.
- **Choice:** run an adversarial referee, twice, and ship its wording.
  **Because** the committee reads the equations, not the footnote.
- **Choice:** the station is the view state; every beat sets its station
  on arrival and a click sets another. **Instead of:** decorative
  headings on results beats. **Because** the director wanted the same
  view for any station on any lake.
- **Choice:** one Playwright browser at a time, serialised, closed
  afterwards. **Because** three parallel QA browsers froze a 16 GB laptop.
- **Choice:** fix the polygon lag by moving the overlay update after the
  camera update, right before render. **Because** that is where the
  current camera exists.

Lessons: when the director is not convinced, write the derivation out,
state the caveats plainly, have it refereed, and say what the words mean;
one browser at a time on a laptop; at a steady 60 fps a one-frame lag is
invisible — inject unevenness and test in the user's browser.

### Phase 18 — The last day, and the morning of

The director cut the elastic model from the talk; the registry made it a
two-line change, and the full sequence moved to the deeper dive. Every
deeper dive now opens with the paper itself, and Chapter 1's derivation
was rewritten with the connecting text taken from the paper and the
equation numbers checked against the published PDF (the old glosses were
off by up to four). The stress solutions land large on a card and shrink
into their zones on NEXT; a scale bar joined the flow arrow; a colourbar
was cleared of its panel titles on short windows after a sweep of ten
viewport sizes; the Additional Work cards were trimmed to titles and
authors. Two wording changes named once were applied to one instance and
had to be redone for their siblings — the last rule of the project. On
the morning of the defense a zone word crossing the plot frame was fixed
and verified at three sizes. The queue was empty afterwards.

- **Choice:** viscous-only on the talk. **Because** the director judged
  the elastic model too much to fit, and the viscous story carries the
  takeaway.
- **Choice:** derivation prose is the paper's own sentences. **Instead
  of:** studio-written connecting text. **Because** the director's rule
  is never to invent the text between equations.
- **Choice:** the first fieldwork clip auto-plays two seconds after
  landing, disarmed by any press. **Because** it is an explicit
  exception the director asked for; the rest stays click-driven.

Lessons: a named change applies everywhere — grep the old wording before
shipping; derivation text from the paper; captions one line or none;
sweep viewport sizes with DOM rectangles before claiming no overlap.

---

## 4. What we would do differently

- **Start the registries on day one.** Every renumbering before them cost
  an afternoon; after them, nothing.
- **Start the design log on day one too.** The early phases above were
  reconstructed from working diaries; a page of decisions per phase as
  you go is cheaper.
- **Set the immutable cache header before the first upload**, and name
  every object with a version from the start.
- **The 75 MB basemap is still downloaded on every cold load**, because
  it exceeds the browser's per-entry cache cap. Tiling or a lower-
  resolution placeholder that upgrades in place is the one performance
  lever left.
- **Code-split the bundle.** It is a single 1.8 MB chunk; it works, and
  it would be a better citizen in pieces.
- **Decide the licence before the first push.** We did it as the last
  step instead of the first; it is MIT.

---

## Glossary

- **The greenland object** — the island mesh on the globe, the rest of
  the globe blacked out; the thing the talk handles and cuts.
- **Beat / step** — one press of NEXT in a chapter (or the Introduction);
  deep-linkable as `?beat=N`.
- **Beat registry** — the ordered list of beat ids per chapter; code asks
  for a phase by name, never by index.
- **The path** — the single NEXT/BACK route through the whole site that
  the talk follows.
- **Ribbon** — the top bar of section names. **Rail / landmarks** — the
  slim capsule under it naming about five landmark beats per chapter.
- **Pill** — any rounded button: BACK/NEXT, tiers, doors, links.
- **Door** — a button or card that leaves the path for a visitor page;
  BACK from it returns to the beat it was used from.
- **Deeper dive** — the per-chapter page under Additional Work holding
  the paper, its figures, equations and field viewers.
- **Takeaway** — a chapter's one-sentence conclusion, written once; the
  last beat grows it into a gold-edged card.
- **The knife / the carve** — a planar cut whose edge sweeps while
  fragments beyond it are discarded; Chapter 2's transition from the
  island to the block.
- **The slab** — a shader-drawn cross-section standing in a cut (Chapter
  1); also the idealised periodic slab of the theory segment (Chapter 2).
- **The seam** — Chapter 1's morph from the real cross-section to the
  model, with a solved camera fit so the theory panel lands pixel-aligned.
- **The block** — Chapter 2's simulation domain as a solid prism a
  visitor can orbit, carrying imagery or stress drapes.
- **The hop** — the dip-to-black between two centre lakes with no return
  to the overview.
- **Station / tier** — Chapter 2's state buttons (pre/post imagery;
  pre/post/difference stress) that double as headings.
- **Stress space** — a scatter of neighbouring lakes' stresses; "the
  population page" shows all lakes.
- **Twins** — Chapter 1's two side-by-side Greenlands with slider-driven
  drapes.
- **Callouts** — Chapter 3's five lake panels with leader lines to their
  lakes on the globe. **Walkthrough** — its layer-by-layer pass of one
  lake through the trained network.
- **Drape** — a texture painted on terrain or block. **Bake** — a
  pipeline script that produces an asset from source copies. **Warm** —
  fetch, decode or compile something before the press that reveals it.
- **The texture gate** — the readiness condition every globe screenshot
  waits on. **The mirror** — the local copy of the bucket the dev server
  serves.
- **Film / contact sheet** — a recorded run cut into frames and tiled
  for judging smoothness.
- **The narrator rule** — no prose on screen. **The back-row rule** —
  legibility judged from the back of a projected 50-seat room.
- **Director / studio** — the student who directs with notes; the AI
  that implements and reports how to view the result.
- **For the director's eye** — the closing list in every report of
  judgment calls the director may reverse.
