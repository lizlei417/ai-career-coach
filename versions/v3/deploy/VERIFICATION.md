# Verification — 2026-11-21

Original remote refs verified after pushing development branches
- Codex main 5494181
- Codex DeepSeek V1 4c6a2a2
- Codex DeepSeek V2 2272a26
- Claude main f971cea
- Claude DeepSeek fdd1554

New independently pushed branches
- feature/v1-auth-deploy, 6e83be8
- feature/v2-auth-deploy, see this document's containing commit
- feature/claude-auth-deploy, a615346

All three TypeScript/Vite production builds passed with application-specific base paths. V1/V2 each passed four unittest cases including feature routes and JSON parsing. Claude passed its original multi-action evidence-audit mock. A disposable UTF-8 PostgreSQL instance tested actual RLS and atomic ledger transactions. Supabase Auth and Storage were synthetic local HTTP fixtures.

The combined mounted gateway passed unauthorized/nonmember rejection, two-user and three-application separation, stale revision conflicts, PDF owner/application checks, 14 concurrent V2 requests yielding exactly five reservations, then 24 concurrent mixed V1/Claude requests yielding exactly fifteen more. Repeated quota reads did not consume calls. Simulated Storage deletion failure preserved catalog records for retry. Successful retry removed only the current V2 owner's projects/PDFs and retained all other records and accounting. A persistent billing block stopped subsequent reservations in all applications.

Chrome browser QA passed all three private workbench entry points, account switching, password change, V1/V2 refresh persistence, two V2 projects, three-page PDF upload, exact original PDF bytes after gateway restart, three V2 interface languages, two-confirmation deletion and preservation of the other account's data. The final repeat used Supabase-compatible bulk object removal. Full Claude multi-device restoration and hosted provider behavior still need cloud acceptance.

Real paid requests this task were limited to one V1 probe and one V2 probe, both deepseek-flash. Each reported 60 prompt tokens, 5 completion tokens, 65 total. No further real AI calls were made for authentication/deployment tests.

Combined gateway cold import measured 0.65 seconds and peak RSS 86 MiB on this Mac. Frontend production directories were approximately 988 KiB, 1000 KiB and 864 KiB. These measurements do not establish Render cold-start time, Linux runtime peak or Docker image size. No Docker engine was available locally. RAG uses existing lexical retrieval and no embedding model was added.

Render and Supabase dashboard access required sign-in. No cloud.env with Supabase credentials or DATABASE_URL was available. No hosted resources or public HTTPS URLs were created. render.yaml specifies a single free service and the Dockerfile pins V1 and Claude source commits. Hosted migrations, signup disabling, member provisioning, actual Storage/RLS checks and Render image/deployment verification remain pending.

To unblock cloud work, authenticate the Render and Supabase dashboards and provide the server environment configuration through the untracked ~/.config/ai-career-coach/cloud.env file. Do not paste secrets in chat. Rotate the DeepSeek key previously disclosed in chat. An administrator must disable public signup and create approved accounts with server-controlled app_metadata.coach_member=true. The supplied migrations create the private schema/role and private bucket.

Official references
- https://api-docs.deepseek.com/guides/json_mode/
- https://supabase.com/docs/guides/auth/passwords
- https://render.com/docs/free
