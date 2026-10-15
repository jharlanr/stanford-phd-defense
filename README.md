# Stanford PhD defense — the site, and how to build one like it

[**Open the site →**](https://jharlanr.github.io/stanford-phd-defense/)

This repository is the website Josh Rines used to defend a PhD thesis
(Stanford Geophysics, 2026) — a talk given not from slides but from a
single interactive page that walks a globe, an ice-sheet mesh and a set
of simulation blocks through the story one beat at a time — and the
record of how it was built, written so that other students can point
their own coding agents at it and build theirs.

It was built in a particular way: the student acted as the **director**
and an AI coding agent as the **studio**. The director gave short notes
and screenshots; the studio built, verified in a headless browser at the
projected size, and reported back with a link to the exact beat. That
relationship, and what we learned running it for five months, is the
most reusable thing here. Start with [DESIGN.md](DESIGN.md).

## Who this is for

- **You want to watch the talk.** Open the link above. NEXT and BACK are
  the arrow keys; every beat has a URL (`/chapter1?beat=10`).
- **You want to build a site like this for your own defense.** Read the
  four documents below in order, then start from [`template/`](template/)
  — a deliberately plain skeleton of the engine — with the
  [`emulate-repo`](.claude/skills/emulate-repo/SKILL.md) skill loaded
  into your coding agent. Do not start from `website/`; it is one
  finished production, with one scientist's objects, story and taste.
- **You maintain this site.** [OPERATIONS.md](OPERATIONS.md) is the
  runbook.

## Read in this order

1. [DESIGN.md](DESIGN.md) — the design log: how the director and the
   studio worked, then every phase of the build in order, each decision
   labelled as a choice with the alternative considered, each phase
   ending with its lessons.
2. [LESSONS.md](LESSONS.md) — the lessons alone, one line each, with the
   why. If you are a person rather than an agent and will read one
   document, read this one.
3. [OPERATIONS.md](OPERATIONS.md) — hosting (GitHub Pages), storage (a
   public-read bucket with immutable names), the labels Worker, local
   development, headless verification, the asset pipelines.
4. [template/README.md](template/README.md) — the plain starter and how
   each of its files maps onto the full site.

## Layout

```
website/     the Vite + Vue 3 + Three.js app that is the site
cinematic/   the Python pipelines that bake every texture, movie, equation and figure the site shows
cloudflare/  one small Worker: visitors' lake labels → the bucket
template/    the engine, stripped and re-themed plain: the place to start your own
.claude/skills/emulate-repo/   a skill for coding agents: how to use this repo to build another talk
DESIGN.md · LESSONS.md · OPERATIONS.md
```

The repo holds application code and small derived assets only. Media
(about 6 GB) lives in an object-storage bucket; see OPERATIONS.md.

## Building your own

```
git clone https://github.com/jharlanr/stanford-phd-defense ../stanford-phd-defense
# in your own, empty repository
cp -R ../stanford-phd-defense/template/. .            # the starter, at the root
cp -R ../stanford-phd-defense/.claude .               # the emulate-repo skill
npm install && npm run dev
```

Then tell your agent to run `/emulate-repo ../stanford-phd-defense`. It
will read the documents above from that clone, ask you for your one-sentence takeaway, your objects and your beat
script, and get an empty skeleton deployed to a URL before building
anything else. The engine (named beats, NEXT/BACK, deep links, doors,
takeaway cards, the media resolver, the deploy) transfers. The content —
the globe, the ice, the dark-and-gold — is one scientist's and is meant
to be replaced, not reused.

## Running this site locally

```
cd website && npm ci && npm run dev          # http://localhost:5173/stanford-phd-defense/
npm run build                                # the gate: vue-tsc, then vite
```

Media is fetched from the public bucket through a dev proxy; a local
mirror makes it fast (OPERATIONS.md §5). The site is deliberately
unlisted (`robots.txt` and a `noindex` tag); a fork inherits that until
it removes them.

## What the site shows, and whose work it is

The talk covers three chapters of the thesis — the stress field that
drains Greenland's supraglacial lakes (viscous theory and a scaling
collapse), three-dimensional simulations of lake drainage against a
rough bed, and a neural network that classifies lake drainage from
satellite imagery — plus the fieldwork, side projects and
acknowledgements around them. The papers behind each chapter are linked
from their title cards. Data on the site come from BedMachine, ITS_LIVE,
RACMO, Sentinel-2, Landsat, MODIS and ASTER, from the CReSIS radar
archive and from the published lake catalogues cited on the page;
headshots are used with the owners' public pages as their source.

## Licence

MIT, for everything in this repository (see [LICENSE](LICENSE)). The
scientific data the site displays stay under their own providers' terms,
cited on the page; the headshots belong to the people in them and are
used with their public pages as the source.
