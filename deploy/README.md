# Public entry update

The current increment exposes the existing landing design before authentication. Get started opens Log in / Sign up. A confirmed Supabase email account can access its private workspace without an invite marker. Administrator guide management still requires server-controlled app_metadata.coach_admin=true. Owner/application RLS and private Storage remain unchanged.

Routes are relative to each app base. /login, /signup, /forgot-password, /auth/callback and /reset-password implement authentication; /workspace and its feature paths require a verified session. Supabase redirect allowlists must include each version base. Public registration requires confirmed email and a working custom SMTP provider. CAPTCHA was omitted at the user's explicit request. Supabase authentication rate limits remain enabled. AI_REQUESTS_ENABLED=false is a server-only emergency switch stopping all new model requests. The existing shared daily request ledger remains authoritative.

# Private cloud integration

This branch preserves the existing application and adds invite-only Supabase authentication and private persistence. The archived main and GitHub Pages deployment remain independently recoverable.

Apply deploy/001_private.sql and deploy/002_storage.sql to the same Supabase database, using a privileged server connection. Set DATABASE_URL to the Supabase transaction-pooler connection with sslmode=require. The backend uses short transactions, SET LOCAL role and owner/application RLS. Keep the private schema outside exposed API schemas.

Disable new user signups in Supabase Auth. Administrators create members with email and password and server-controlled app_metadata.coach_member=true. Regular users cannot edit app_metadata. Knowledge-base administrators additionally need coach_admin=true. An invite email redirect flow is not enabled by this implementation. Set a member's initial password securely through the administrator workflow.

Configure DEEPSEEK_API_KEY, SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, SUPABASE_SECRET_KEY and DATABASE_URL in the server environment or the untracked ~/.config/ai-career-coach/cloud.env file. Publishable keys and legacy anon keys are accepted for the browser. Secret keys remain server-only. Rotate the DeepSeek credential previously disclosed in chat.

Private PDFs use the career-resumes-private bucket and an owner/application/project path. Browsers fetch documents through the authenticated backend. Existing anonymous browser records are not imported automatically into a member account.

Every actual AI attempt reserves a database ledger entry before transmission. All applications share SITE_DAILY_LIMIT=20, while V2 additionally has V2_DAILY_LIMIT=5 per user. The calendar day is Asia/Hong_Kong. Failed transmitted requests consume an attempt. Tokens are recorded when supplied by the provider. A 402 response persistently blocks subsequent requests. After replenishment an administrator must explicitly clear career_private.billing. Quotas are request limits, not a guaranteed monetary ceiling. Deleting business data preserves accounting entries.

V2 uses optimistic revisions to detect concurrent edits. The delete action waits for pending writes, requires two confirmations and reports deleted projects/PDFs. Failed Storage deletion keeps catalog records for retry. Other applications and members retain their records.

Local development requires Python 3.11+ and Node 22+. Install the backend requirements and frontend dependencies, build the frontend, then start the original FastAPI entry point. Build with the root base path for standalone local use. V1/V2 use backend/app/main.py, Claude uses server.py. The combined deployment in the V2 branch builds with /v1/, /v2/ and /claude/ base paths and mounts independent application namespaces in one process.

Validation on 2026-11-21 used synthetic local Auth/Storage plus real disposable PostgreSQL RLS, not hosted Supabase. Existing three-feature AI route mocks passed. Codex JSON parser edge cases passed. Browser tests passed sign-in/out, account switching, password changes, V1/V2 restoration, V2 multi-project and original PDF byte equality after server restart, languages and deletion. Isolation tests passed owner/application separation, conflicts, concurrent quota enforcement, partial-delete retry and persistent 402 protection. Hosted Auth, Storage policies, Render image build and public HTTPS verification remain pending platform credentials.

Codex V1 and V2 each completed one real deepseek-flash probe, each using 60 input and 5 output tokens. No real business workflow was exercised. The earlier AI_FORMAT responses were not retained, so their exact upstream cause cannot be proven. The fix distinguishes empty/whitespace/truncated/wrong-type/envelope errors, uses an explicit boolean JSON probe and raises its output ceiling to 128. It preserves strict validation without automatic retries.
