# AI Career Coach Agent instructions

- Unified repository: lizlei417/ai-career-coach. Read README.md, docs/UNIFICATION-AUDIT-20261126.md and versions/source-manifest.json first.
- Active implementation is V4 at root frontend/ and backend/. Use a new codex/ branch from the latest origin/main. codex/unified-repository-20261126 records the accepted integration; main is the canonical complete source after this release.
- versions/v1, versions/v2, versions/v3 and versions/claude are independent source snapshots. Claude remains Python/FastAPI with its own frontend/dependencies. Do not replace one implementation with another, convert stacks, or restructure root V4 without a specific request.
- archives/ are historical local source snapshots, not production inputs. Original branches are retained under archive/codex/* and archive/claude/* tags; never delete or rewrite them.
- Read the target version's README and requirements before editing. Change only the requested version. Shared gateway/Docker/config changes require checks on all five routes. Preserve /v1/, /v2/, /v3/, /v4/, /claude/ and the existing root redirect.
- Never change owner/application namespaces, Supabase project, private Storage paths, RLS, account ledger semantics or existing users as a side effect of source organization. No production migrations or data cleanup for this integration.
- Never commit .env, credentials, tokens, private user files, local DBs, browser traces or screenshots containing real data. Real keys stay in server configuration or untracked ~/.config/ai-career-coach. Test values must be visibly synthetic. Do not print secrets.
- Preserve uncommitted work: back up first, compare content and history, never reset or overwrite another worktree. No force push, branch deletion, archive overwrite or original repository deletion.
- Build target frontend with npm ci and npm run build -- --base=/VERSION/. Backend checks: from target backend run python -m unittest discover -s tests -v; Claude checks from versions/claude. Use synthetic data and isolated HOME/env so tests never access real cloud credentials.
- Shared local runtime: uvicorn local_gateway:app --app-dir deploy --host 127.0.0.1 --port 8114 after all five builds. Verify gateway health, each landing and unauthenticated API rejection. Build Docker when an engine is available; local tests do not prove Linux image behavior.
- Develop on a feature branch. On 2026-11-26 the user explicitly authorized this accepted integration to merge into main and deploy the existing Render service after all critical tests pass. This is not standing authorization for future releases. Future production changes require the then-current user request. Original Claude repository archival/deletion is not authorized in this task; report readiness only.
- Record source commits, functional differences, exact test results and any unverified claims. Commit dates or the newest SHA alone do not establish functional completeness.

- Only the ROOT Dockerfile is an active deployment entry point. Nested legacy Dockerfiles/render.yaml are preserved snapshots; do not execute them or apply their Blueprints. No active build/runtime path should clone the old Claude repository.

- Canonical repository after rename: https://github.com/lizlei417/ai-career-coach. Keep origin on this URL. The existing IS5542 Project, chat history and unified-career-coach directory stay in place.
- Read docs/REPOSITORY-RENAME-20261126.md for current repository identity and old-Claude deletion assessment. Use release/unified-20261126 (30e7ffb) or later unified sources for rollback/rebuild; do not rebuild the pre-unification clone-based Dockerfiles.
- The original Claude repository must NOT be deleted until the user explicitly gives final deletion confirmation. Current-source independence does not preserve its old GitHub Pages address or GitHub Actions history.
