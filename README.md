# AI Career Coach · Claude

[Open the public demo](https://lizlei417.github.io/ai-career-coach-claude/)

This is the independent Claude edition, built from the original React / TypeScript frontend and FastAPI service. GitHub Pages publishes only the Vite static build. Navigation, editing, language switching and review controls run in the browser. Coaching outputs use a labelled fictional case. PDF extraction, URL import, model credentials and retrieval require the local service. Use fictional materials when exploring the demo.

## Run locally

Install Node.js 22, npm and Python 3.11+. From the repository root run:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./run.sh
```

Open http://127.0.0.1:8765.

For an offline preview of the Pages build, run `npm ci && VITE_PAGES_DEMO=1 npm run build && npx vite preview` inside `frontend`. Rebuild without the demo flag to restore local API integration.

## GitHub Pages publishing

Pages serves the committed `docs/` directory on `main`. To update the demo, run the following in `frontend/`:

```sh
npm ci
VITE_PAGES_DEMO=1 npm run build -- --base=/ai-career-coach-claude/
```

Replace the contents of `docs/` with the new build from `frontend/dist/`, keep `docs/.nojekyll`, and push the changes. GitHub runs its Pages build and deployment workflow automatically. An optional source-build workflow is included in `deployment/pages-workflow.yml` for use with Actions-based Pages publishing.
