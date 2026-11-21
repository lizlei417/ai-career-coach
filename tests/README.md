# V3 audit tests

All identities, CVs, projects and JD content are fictional. Default tests use synthetic Supabase Auth/Storage and a deterministic mock at the model HTTP transport, with the real app routes, real UTF8 PostgreSQL RLS/revisions/quota, actual PDF extraction and actual PDF/DOCX generation. The mock is never installed in the production entry point. Tests count attempts against the unchanged account limit of 10. They never reset a production quota.

Install backend and test requirements in an isolated Python environment, and provide Chrome or install Playwright Chromium (the browser scripts currently select `channel='chrome'`). Build the frontend for `/v3/` before running:

```sh
cd frontend
npm ci
npm run build -- --base=/v3/
cd ..
python -m pip install -r tests/requirements.txt
QA_DATABASE_URL=postgresql://USER@127.0.0.1:PORT/coachtest_v3_audit_NAME python tests/run_audit.py
```

Create that UTF8 database yourself on a local PostgreSQL instance. The runner applies existing 001 and 003 migrations only inside that guarded disposable database; 002 targets hosted Storage and is not used by the mock. Ports 28648 and 28649 must be free. Existing processes are never killed by the runner. Evidence is saved under `tests/evidence/`. Backend tests can also run independently: `cd backend && python -m unittest discover -s tests -v`.

`e2e_audit.py --baseline` was exercised using a separate build of the archived V2 source to reproduce disabled review/regenerate buttons. It must not be run against the production website. `e2e_races.py` verifies edits during material preparation and optimization, then 503/manual recovery. `api_integration.py` checks ownership, conflicts and the real 10-attempt ledger; it makes only mocked model calls.

`real_e2e.py` is deliberately excluded from the runner. For an explicitly authorized, small live-model check, start `qa_server.py app` with `QA_REAL_MODEL=1` and the same synthetic Auth/Storage and guarded database. Do not set a fake DEEPSEEK_API_KEY in real mode; let the application load the already-configured private credential. The successful full workflow makes three real calls (prepare, match, optimize); no automatic retries occur. The report records any earlier partial call as well. Never print or commit credentials. Real hosted Auth/SMTP is a separate acceptance test, not claimed by these fixtures.

Trace files contain synthetic Auth tokens and fictional material; do not publish traces from real accounts. No DeepSeek credential is ever available to browser code.
