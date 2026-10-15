import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'
import './style.css'

createApp(App).use(router).mount('#app')

// Font pre-warm. Google Fonts splits each family by unicode-range and a
// browser fetches a subset only when text first needs it. EB Garamond's
// latin-ext file (the `ℓ` of Chapter 1's patch length) was first needed
// on the log-log beat, mid-talk — its glyphs drew in the fallback face
// until the file arrived (seen on a performance walk). Ask for it once the
// family's @font-face rules are in; until then load() matches no face and
// resolves empty, so retry a few times.
function warmFontSubsets(tries = 0): void {
  if (!('fonts' in document)) return
  document.fonts
    .load('400 16px "EB Garamond"', 'ℓ')
    .then((faces) => {
      if (faces.length === 0 && tries < 8) window.setTimeout(() => warmFontSubsets(tries + 1), 1500)
    })
    .catch(() => {})
}
window.setTimeout(() => warmFontSubsets(), 1500)
