// THE ENGINE — one composable that owns "where are we in the talk".
//
// It holds the current beat index and whether a door page is open, and it
// keeps three things in step with them: the keyboard (a presenter remote
// is a keyboard too), the URL (`?beat=N`, so a copied link opens the talk
// at that beat) and the browser history (so BACK from a door returns to
// the beat the door was opened from).
//
// The state lives at module level, so every component that calls
// useBeats() shares the same talk. App.vue calls `install()` once to hook
// up the window listeners.

import { computed, readonly, ref } from 'vue'
import { BEATS, clampIndex, phase } from './beats'

const index = ref(0)
const door = ref<string | null>(null)
const reduced = ref(false)

// ── URL ⇄ state ──────────────────────────────────────────────────────
// The URL is the deep link. `?beat=N` is the index; `?beat=last` lands on
// the final beat (handy for "back into the previous section"). `?door=ID`
// means a door page is open over that beat.

function readUrl(): void {
  const q = new URLSearchParams(location.search)
  const raw = q.get('beat')
  index.value = raw === 'last' ? BEATS.length - 1 : clampIndex(parseInt(raw ?? '0', 10))
  door.value = q.get('door')
}

/** Rewrite the current history entry so the address bar matches the state. */
function writeUrl(): void {
  const url = new URL(location.href)
  url.searchParams.set('beat', String(index.value))
  if (door.value) url.searchParams.set('door', door.value)
  else url.searchParams.delete('door')
  history.replaceState(history.state, '', url)
}

// ── Moving through the talk ──────────────────────────────────────────

function goTo(i: number): void {
  index.value = clampIndex(i)
  writeUrl()
}

function next(): void {
  if (door.value) return // a door page is not part of the beat sequence
  goTo(index.value + 1)
}

function back(): void {
  if (door.value) closeDoor() // BACK from a door = return to where it was opened
  else goTo(index.value - 1)
}

// ── Doors ────────────────────────────────────────────────────────────
// A door is a side room (a deeper dive, a method page) reached from one
// beat. Opening it PUSHES a history entry whose state records the origin
// beat. Closing it reads that origin back and lands there, whether the
// visitor pressed our BACK or arrived at the door page by a copied link
// (then there is no origin, and we fall back to the `?beat=` in the URL).

function openDoor(id: string): void {
  const url = new URL(location.href)
  url.searchParams.set('door', id)
  history.pushState({ from: index.value }, '', url)
  door.value = id
}

function closeDoor(): void {
  const from = (history.state as { from?: unknown } | null)?.from
  door.value = null
  goTo(typeof from === 'number' ? from : index.value)
}

// ── Keyboard ─────────────────────────────────────────────────────────
// ArrowRight / Space / PageDown = next; ArrowLeft / PageUp = back;
// Home = first beat. Presenter remotes send PageDown / PageUp. Held keys
// (auto-repeat), modifier chords and typing in a text field are left
// alone, and Space on a focused button stays a click.

function onKey(e: KeyboardEvent): void {
  if (e.defaultPrevented || e.repeat || e.metaKey || e.ctrlKey || e.altKey) return
  const t = e.target as HTMLElement | null
  const tag = t?.tagName ?? ''
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || t?.isContentEditable) return
  if (tag === 'BUTTON' && e.key === ' ') return
  switch (e.key) {
    case 'ArrowRight':
    case ' ':
    case 'PageDown':
      next()
      break
    case 'ArrowLeft':
    case 'PageUp':
      back()
      break
    case 'Home':
      door.value = null
      goTo(0)
      break
    default:
      return
  }
  e.preventDefault()
}

// ── Install (once, from App.vue) ─────────────────────────────────────

function install(): () => void {
  readUrl()
  writeUrl()
  const motion = matchMedia('(prefers-reduced-motion: reduce)')
  const onMotion = () => (reduced.value = motion.matches)
  onMotion()
  motion.addEventListener('change', onMotion)
  window.addEventListener('keydown', onKey)
  window.addEventListener('popstate', readUrl) // browser back/forward re-reads the URL
  return () => {
    motion.removeEventListener('change', onMotion)
    window.removeEventListener('keydown', onKey)
    window.removeEventListener('popstate', readUrl)
  }
}

export function useBeats() {
  return {
    index: readonly(index),
    /** The current beat's NAME — compare against this, never against a number. */
    phase: computed(() => phase(index.value)),
    door: readonly(door),
    /** True when the visitor asked the OS for less motion; skip the transitions. */
    reduced: readonly(reduced),
    total: BEATS.length,
    next,
    back,
    goTo,
    openDoor,
    closeDoor,
    install,
  }
}
