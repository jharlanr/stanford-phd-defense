import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// The base path is the one thing a deploy usually has to change: a project
// site at https://<user>.github.io/<repo>/ needs base '/<repo>/'. Pass it
// at build time (VITE_BASE=/my-talk/ npm run build); the default '/' suits
// local development and custom-domain deploys.
export default defineConfig({
  base: process.env.VITE_BASE ?? '/',
  plugins: [vue()],
})
