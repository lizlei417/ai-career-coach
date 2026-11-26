import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/v3/',
  plugins: [react(), { name: 'offline-demo', transformIndexHtml(html) {
    return process.env.VITE_PAGES_DEMO === '1' ? html.replace('<head>', '<head><meta http-equiv="Content-Security-Policy" content="connect-src &apos;none&apos;; form-action &apos;none&apos;; object-src &apos;none&apos;">') : html
  } }],
  server: {
    host: '127.0.0.1',
    port: 5174,
    proxy: Object.fromEntries(['/v3/api', '/v3/auth-config', '/v3/healthz'].map(path => [path, { target: 'http://127.0.0.1:8113', changeOrigin: false }])),
  },
})
