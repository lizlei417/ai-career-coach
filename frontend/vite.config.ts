import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react(), { name: 'offline-demo', transformIndexHtml(html) {
    return process.env.VITE_PAGES_DEMO === '1' ? html.replace('<head>', '<head><meta http-equiv="Content-Security-Policy" content="connect-src &apos;none&apos;; form-action &apos;none&apos;; object-src &apos;none&apos;">') : html
  } }],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } },
  },
})
