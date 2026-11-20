# AI Career Coach · Codex

[Open the public demo](https://lizlei417.github.io/ai-career-coach-codex/)

This is the independent Codex edition, built from the original React / TypeScript frontend and FastAPI service. GitHub Pages publishes only the Vite static build. Navigation, editing, language switching and review controls run in the browser. Coaching outputs use a labelled fictional case. PDF extraction, URL import, model credentials and retrieval require the local service. Use fictional materials when exploring the demo.

## V2 development branch

The public Pages link above serves the archived V1. This branch adds named projects and a near-fullscreen native PDF reader. A new project starts with empty materials. The first project can import V1 text and analysis stored in the same browser origin; attach the original PDF again for legacy records that contain only a filename.

V2 keeps the original PDF bytes, inputs, review decisions, results and interview records together in IndexedDB in this browser profile. Use the same host and port after restarting, and wait for **Saved** before closing the tab. Clearing site data also removes these projects. The local Python service extracts text; opening a preview uses the browser PDF viewer. In the static demo, uploads support preview, while text input remains available separately.

## Run locally

Install Node.js 22, npm and Python 3.11+. From the repository root run:

```sh
PORT=8012 ./start.sh
```

Open http://127.0.0.1:8012.

For an offline preview of the Pages build, run `npm ci && VITE_PAGES_DEMO=1 npm run build && npx vite preview` inside `frontend`. Rebuild without the demo flag to restore local API integration.

## GitHub Pages publishing

Pages serves the committed `docs/` directory on `main`. To update the demo, run the following in `frontend/`:

```sh
npm ci
VITE_PAGES_DEMO=1 npm run build -- --base=/ai-career-coach-codex/
```

Replace the contents of `docs/` with the new build from `frontend/dist/`, keep `docs/.nojekyll`, and push the changes. GitHub runs its Pages build and deployment workflow automatically. An optional source-build workflow is included in `deployment/pages-workflow.yml` for use with Actions-based Pages publishing.
