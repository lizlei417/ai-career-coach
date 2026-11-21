# V3 deployment preparation

Historical pre-deployment plan: after this audit, the user explicitly authorized deployment. V3 is now live as /v3/ on the existing service, preserving the old application routes. See [V3-LIVE-ACCEPTANCE.md](V3-LIVE-ACCEPTANCE.md) for the authoritative deployment record. The independent preview-service blueprint below remains an optional alternative and was not applied. No hosted schema migration, credential change or real-user data mutation was performed.

V3 is on `codex/v3-career-audit`. `render.yaml` names a separate `career-coach-v3-preview` service with automatic deployment off, so it does not target the existing production service. Before deploying, publish/review that branch and validate the actual Docker image in a staging service. Docker was unavailable locally; the four-app Python gateway and each app's HTML/assets/auth boundary were exercised locally, but the Render image build was not.

The Dockerfile retains the original V1 and Claude pins and additionally pins the archived V2 source at `b176cccb5121b783d7a163fafc9a7ae30218275c`. New code is copied to `/srv/apps/v3`, mounted at `/v3/`. The existing `/v1/`, `/v2/` and `/claude/` routes remain. The gateway root redirects to `/v3/` in the prospective V3 preview service. The existing production gateway was not changed.

New runtime Python dependencies: `reportlab>=4.4,<6` and `python-docx>=1.2,<2`, listed in both backend and deploy requirements. There are no new frontend runtime dependencies and no new required runtime environment variables. All existing DeepSeek/Supabase/database settings and ACCOUNT_DAILY_LIMIT=10 remain in place. Test-only QA variables and servers are not part of production.

No new schema migration is required on an already-migrated V2 database. An optional original source snapshot is stored in the existing project JSON. The existing owner/application RLS policies accommodate `codex_v3`; original documents are stored under that namespace. Existing V2 data remains accessible to V2 and is not automatically imported. All app versions share the same account/day model ledger. Do not change or reset that ledger for release.

Add the new origin and `/v3/auth/callback` and `/v3/auth/callback?mode=recovery` destinations to the Supabase redirect allowlist as appropriate. Recheck hosted signup, actual verification/reset emails, login/session refresh and private Storage using disposable accounts on staging. Local synthetic Auth/Storage tests are not evidence that the hosted SMTP or Storage configuration is correct.

If a fresh environment is used, follow the existing schema/private-bucket setup (001, 002 and 003). Do not run the old migrate.py expecting it to apply 003; it historically includes only 001 and 002. An already-migrated production database needs no V3 schema change. No production migration was run in this audit.

A scanned PDF remains previewable but requires pasted text; OCR is not implemented. External JD pages that require login, client-side rendering, or disallow retrieval may fail explicitly and should use pasted text. The URL reader is not a Jobsdb job-search API integration. Production testing of any specific recruitment site remains separate.
