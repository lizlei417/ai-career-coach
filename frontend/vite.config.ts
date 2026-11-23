import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/v4/',
  plugins: [react(), { name: 'offline-demo', transformIndexHtml(html) {
    return process.env.VITE_PAGES_DEMO === '1' ? html.replace('<head>', '<head><meta http-equiv="Content-Security-Policy" content="connect-src &apos;none&apos;; form-action &apos;none&apos;; object-src &apos;none&apos;">') : html
  } }],
  server: {
    host: '127.0.0.1',
    port: 5175,
    proxy: Object.fromEntries(['/v4/api', '/v4/auth-config', '/v4/healthz'].map(path => [path, { target: 'http://127.0.0.1:8114', changeOrigin: false }])),
  },
})
