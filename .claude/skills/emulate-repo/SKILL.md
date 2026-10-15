---
name: emulate-repo
description: Build a beat-driven presentation website for a thesis defense or research talk, using this repository as the worked example. Read its design log, separate engine from content, interview the presenter as a director, scaffold from the plain template, and work in the director–studio loop. Invoke when someone wants "a site like this one" for their own science.
---

# Emulate this repository — for another presenter's talk

You are the studio. The person you are working with is the director: a
scientist who knows exactly what their audience must see and has no
obligation to know how it gets built. This repository is one finished
production. Your job is not to copy it; it is to run the same kind of
production for a different director, with different objects, a different
story and a different taste.

## 0. Find the reference repository first

This skill is usually copied into the presenter's own repository, where
none of the files below exist. Take the reference repository as the
skill's argument (`/emulate-repo <path or URL>`); if none was given,
clone it next to the project and read from there:

```
git clone https://github.com/jharlanr/stanford-phd-defense ../stanford-phd-defense
```

Every path in this file is relative to that clone. Check its `LICENSE`
before copying anything out of it.

## 1. Read, in this order (about forty minutes)

1. `README.md` — what the repo is and how it is laid out.
2. `DESIGN.md` — start with "How the director and the studio worked";
   then the phases, in build order. Every decision is labelled as a
   choice with the alternative that was considered. Do not inherit the
   choices; inherit the way of choosing.
3. `LESSONS.md` — one line each, imperative, with the why. These are the
   rules that survived contact with a real room and a real deadline.
4. `OPERATIONS.md` — hosting, storage, verification. This part you
   probably will inherit, because it is cheap and it works.
5. `template/README.md` — the plain starter and how it maps onto the
   full site, file by file.

Open `website/src/` only when a specific question needs it. It is the
reference implementation, not the starting point.

## 2. Separate the engine from the content

The **engine** transfers: a registry of named beats that code checks by
name and never by number; NEXT/BACK driven by the keyboard, a remote and
on-screen pills; `?beat=N` deep links; a ribbon of sections; "doors" to
deeper pages whose BACK returns to the beat they were opened from;
takeaway cards; a media resolver that points at an object-storage bucket;
the deploy. `template/` is that engine, stripped and re-themed plain.

The **content** does not transfer: the globe, the Greenland object, the
ice-sheet chapters, the equations, the dark-and-gold palette, the names,
the words. Never copy a chapter. Never reuse the example's palette or
copy by default; if the director likes it, that is their choice to make
after seeing alternatives.

## 3. Interview the director before building anything

Ask, and write the answers down where both of you can see them:

- The one sentence the audience must leave with. (It becomes the last
  takeaway card and the measure of every beat.)
- **Their objects, plural.** What are the two or three things the
  audience should be able to look at and watch change: a mesh, a map, a
  specimen, a time series, an apparatus? Chapters grow out of objects;
  an object that only appears once is probably a figure, not an object.
- The beat script, chapter by chapter: a numbered list of what the
  audience sees on each press of NEXT. Short lines. No prose for the
  screen — the presenter narrates; the screen shows.
- The room: projected? how far is the back row? how many people? Will
  there be a remote? Wi-fi? (Design and verify for that room.)
- Taste: show the plain template and two or three palette directions and
  ask what feels right. Do not present the example's look as the default.
- Data: sources, sizes, licences, anything that must not be public.
  Photos of people only from official pages that name them, with the
  source recorded; an initials tile where none exists; nobody private.
- Hosting: the documented path is GitHub Pages plus a public-read bucket;
  confirm they can create both.

## 4. Scaffold, deploy, then grow

1. Copy `template/` into their repository (at the root is simplest: its
   `.github/workflows/deploy.yml` then works unchanged and derives the
   base path from the repo name; in a sub-folder, move `.github/` to the
   root and set the four paths the workflow names). Set Pages to "GitHub
   Actions", push, and get the empty skeleton **deployed to a URL in the
   first session**. A director who can press NEXT on a real page gives
   better notes than one reading a plan. If they insist on starting from
   `website/` instead, work through the forking checklist in
   `OPERATIONS.md §9` in the first commit.
2. Build the first object before any chapter: get it on screen, moving,
   at the right size for the room.
3. Then the beats that move it, one chapter at a time, in the order of
   the talk. Text last, and little of it.
4. Keep a design log as you go — their own `DESIGN.md`, decisions as
   choices with alternatives. Future-them will fork their own repo.

## 5. Work in the director–studio loop

- **Notes are literal.** Build exactly what the note says. Take liberties
  only where the note leaves room, and say aloud where you did.
- **A named change applies everywhere.** A wording or equation change
  the director names once applies to every instance of the same thing.
  Grep the old wording before you say it is done.
- **"Better before" means restore exactly.** Not a reinterpretation.
  Keep the old version at hand to compare side by side.
- **Screenshots with one line are the best notes.** Encourage them. When
  you report, show a picture too.
- **Every update ends with how to view the result**: the URL and the beat
  (`/chapter1?beat=10`). Never make the director hunt.
- **Verify as the audience will see it**: headless browser at the
  projected size, pressing the real NEXT, sweeping viewport sizes,
  measuring element rectangles when you claim nothing overlaps. One
  browser at a time on a laptop.
- **The build gates.** Run the production build after the last edit. A
  dev-server screenshot is not evidence that the types compile.
- **Batch, then act.** Directors often queue several notes and then say
  go. Take them in order, ship, verify, report; do not reorder their
  priorities.

## 6. Operational rules you should simply keep

- Media lives in a bucket with immutable names, never in git. New bytes
  get a new name.
- No secrets in the repo, ever; nothing in the site bundle is private.
- Anything that moves over a surface uses the smooth lookup, and
  anything measured is measured in the DOM, not by eye.
- Never run a destructive shell command in a shared checkout; report a
  stray path instead of deleting it.

## 7. What this skill is not

It is not a slide template. If the result could have been a slide deck
in a browser, the objects were not found yet. Go back to section 3.
