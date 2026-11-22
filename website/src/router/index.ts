import { createRouter, createWebHistory } from 'vue-router'
import Explore from '../views/Explore.vue'
import { SECTIONS, LEGACY_REDIRECTS } from '../config/sections'

// Single-component SPA: Explore.vue handles every UI state. The router
// just maps URL paths to a (mode, section) pair via route.name, which
// Explore reads on mount and on every navigation.
//
// The per-section routes derive from the section registry
// (src/config/sections.ts) — add a section there, its route exists.
//
// History mode (clean URLs like /stanford-phd-defense/chapter1) requires
// a 404.html SPA-fallback shim on GitHub Pages — see public/404.html and
// the decoder snippet at the top of index.html.

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: Explore },
    { path: '/menu', name: 'menu', component: Explore },
    ...SECTIONS.map((s) => ({ path: s.path, name: s.id, component: Explore })),
    ...Object.entries(LEGACY_REDIRECTS).map(([from, to]) => ({
      path: from,
      redirect: to,
    })),
    // Additional Work sub-pages: the section route is the card menu;
    // each door is its own URL so it deep-links and back-navigates.
    { path: '/additional-work/mgsim', name: 'additional-work-mgsim', component: Explore },
    // APS DFD 2026 · Interact: the flash slide + the interactive poster
    // (SectionDfd.vue; the door is at the top of the Chapter 2 deeper dive)
    { path: '/additional-work/dfd', name: 'additional-work-dfd', component: Explore },
    { path: '/additional-work/terminal-bench', name: 'additional-work-terminal-bench', component: Explore },
    { path: '/additional-work/fracture', name: 'additional-work-fracture', component: Explore },
    { path: '/additional-work/fieldwork', name: 'additional-work-fieldwork', component: Explore },
    // The ESSD inter-rater 200, labeled by the visitor.
    { path: '/additional-work/label', name: 'additional-work-label', component: Explore },
    // "Revisiting lake drainage papers": Christoffersen et al. 2018's
    // cascade lakes, each with its season of imagery (SectionRevisit.vue).
    { path: '/additional-work/revisit', name: 'additional-work-revisit', component: Explore },
    // The toggle's second stop, "Deeper dive into the chapters": one
    // page per chapter. Chapter 1's log-log and
    // twins beats link to /additional-work/deeper/chapter1 — keep it.
    { path: '/additional-work/deeper', redirect: '/additional-work/deeper/chapter1' },
    {
      path: '/additional-work/deeper/:chapter(chapter1|chapter2|chapter3)',
      name: 'additional-work-deeper',
      component: Explore,
    },
    { path: '/additional-work/deeper/:rest(.*)', redirect: '/additional-work/deeper/chapter1' },
    // Catch-all → home. Future sub-routes (e.g. /extras/fieldwork-2023)
    // get added explicitly above this line.
    { path: '/:pathMatch(.*)*', name: 'not-found', redirect: '/' },
  ],
})
