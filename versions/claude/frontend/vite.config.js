import { defineConfig } from "vite";
export default defineConfig({
  plugins: [{ name: 'offline-demo', transformIndexHtml(html) {
    return process.env.VITE_PAGES_DEMO === '1' ? html.replace('<head>', '<head><meta http-equiv="Content-Security-Policy" content="connect-src &apos;none&apos;; form-action &apos;none&apos;; object-src &apos;none&apos;">') : html
  } }],
  server: {
    proxy: { "/api": "http://127.0.0.1:8765", "/art": "http://127.0.0.1:8765" },
  },
});
