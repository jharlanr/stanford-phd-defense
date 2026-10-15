<template>
  <!-- "Software Repositories" — a plain table, on brand, deliberately
       NOT the Additional-Work cards (the director's choice). Three
       columns: the repo (links to GitHub in a new tab), its own one-line
       description, and the work it belongs to as in-site pills (or the
       paper's DOI). A flat opaque layer ABOVE the globe, which keeps
       rendering beneath it — never a veil. -->
  <div class="rp">
    <div class="rp-inner">
      <header class="rp-head">
        <h2 class="rp-title">Software Repositories</h2>
        <p class="rp-sub">Code behind the dissertation.</p>
      </header>

      <table class="rp-table">
        <thead>
          <tr>
            <th class="rp-th rp-col-repo">Repository</th>
            <th class="rp-th rp-col-desc">Description</th>
            <th class="rp-th rp-col-work">Associated work</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in REPOS" :key="r.href" class="rp-row">
            <td class="rp-td rp-col-repo">
              <a class="rp-repo" :href="r.href" target="_blank" rel="noopener noreferrer">
                <span class="rp-owner">{{ r.owner }}/</span><span class="rp-name">{{ r.name }}</span>
                <span class="rp-arrow">↗</span>
              </a>
            </td>
            <td class="rp-td rp-col-desc">{{ r.description }}</td>
            <td class="rp-td rp-col-work">
              <div class="rp-work">
                <template v-for="w in r.work" :key="w.label">
                  <a
                    v-if="w.href"
                    class="rp-pill"
                    :href="w.href"
                    target="_blank"
                    rel="noopener noreferrer"
                  >{{ w.label }} ↗</a>
                  <button
                    v-else
                    class="rp-pill"
                    @click="go(w)"
                  >{{ w.label }} →</button>
                </template>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { REPOS, type RepoWorkLink } from '../../config/repos'
import type { SectionId } from '../../config/sections'

const emit = defineEmits<{
  section: [id: SectionId]
  open: [page: 'mgsim' | 'terminal-bench']
}>()

function go(w: RepoWorkLink): void {
  if (w.page) emit('open', w.page)
  else if (w.section) emit('section', w.section)
}
</script>

<style scoped>
.rp {
  position: fixed;
  inset: 0;
  z-index: 1;
  overflow-y: auto;
  background: radial-gradient(ellipse at 50% 0%, #0f1420 0%, #050505 60%);
  color: #f5f5f5;
  font-family: 'Inter', system-ui, sans-serif;
  padding: 9vh 3vw 4vh;
  box-sizing: border-box;
  pointer-events: auto;
}

.rp-inner {
  max-width: 1240px;
  margin: 0 auto;
}

.rp-head {
  text-align: center;
  margin-bottom: 2.2rem;
}

.rp-title {
  font-family: 'EB Garamond', serif;
  font-weight: 400;
  font-size: 2.4rem;
  color: var(--gold);
  margin: 0;
  letter-spacing: 0.02em;
}

.rp-sub {
  margin: 0.15rem 0 0;
  color: rgba(244, 207, 106, 0.88);
  font-size: 1rem;
  letter-spacing: 0.04em;
}

.rp-table {
  width: 100%;
  border-collapse: collapse;
  border-top: 1px solid rgba(232, 185, 74, 0.3);
  border-bottom: 1px solid rgba(232, 185, 74, 0.3);
}

.rp-th {
  font-weight: 600;
  font-size: 0.85rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--gold);
  text-align: left;
  padding: 0.9rem 1rem 0.7rem;
  border-bottom: 1px solid rgba(232, 185, 74, 0.3);
}

.rp-col-repo { width: 30%; }
.rp-col-desc { width: 44%; }
.rp-col-work { width: 26%; }

.rp-td {
  padding: 1.15rem 1rem;
  vertical-align: middle;
  font-size: 1.05rem;
  line-height: 1.45;
  color: rgba(245, 245, 245, 0.88);
  border-bottom: 1px solid rgba(232, 185, 74, 0.3);
}

.rp-row:last-child .rp-td {
  border-bottom: none;
}

.rp-row {
  transition: background 0.2s;
}

.rp-row:hover {
  background: rgba(232, 185, 74, 0.05);
}

.rp-repo {
  color: var(--gold);
  text-decoration: none;
  font-size: 1.1rem;
  letter-spacing: 0.01em;
  white-space: nowrap;
  transition: color 0.2s;
}

.rp-repo:hover {
  color: var(--gold-bright);
}

.rp-owner {
  color: var(--gold-dim);
}

.rp-name {
  font-weight: 500;
}

.rp-arrow {
  margin-left: 0.35rem;
  font-size: 0.85rem;
  opacity: 0.7;
}

.rp-work {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.rp-pill {
  display: inline-block;
  background: transparent;
  border: 1px solid rgba(232, 185, 74, 0.5);
  color: rgba(244, 207, 106, 0.9);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.86rem;
  font-weight: 500;
  letter-spacing: 0.05em;
  padding: 0.32rem 0.75rem;
  border-radius: 999px;
  cursor: pointer;
  text-decoration: none;
  white-space: nowrap;
  transition: color 0.2s, border-color 0.2s, background 0.2s;
}

.rp-pill:hover {
  color: var(--gold-bright);
  border-color: var(--gold);
  background: var(--gold-faint);
}
</style>
