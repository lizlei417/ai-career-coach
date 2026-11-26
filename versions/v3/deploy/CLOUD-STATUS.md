# Cloud deployment status — 2026-11-21

The historical deployment observations below are retained for audit. The current public-entry deployment is described in PUBLIC-ENTRY-ACCEPTANCE.md; it supersedes the initial invite-only and unconfigured-model observations.

Live gateway https://ai-career-coach-three-versions.onrender.com

Independent entrances /v1/, /v2/, /claude/.
Render service srv-dc0k9cm7bikc73b2iqug, Singapore, Docker Free, 512 MB. No paid resources selected. Source branch feature/v2-auth-deploy, deployed code cc6715d, with pinned V1 6e83be8 and Claude a615346. Automatic deployment is disabled. First Docker build/deploy succeeded in 1m39s; configured environment redeploy succeeded in 36.8s. Render Events confirmed restart at 15:23 Hong Kong time.

Supabase project nyrxxbcpnllodrjhvaqt, ai-career-coach, Singapore Nano under the existing Free organization. Existing daily-journal project was not modified. Both migrations were executed successfully against the real transaction pooler. RLS enabled on projects, documents, calls and billing. Resume bucket public=false. Public signup was disabled and independently returned signup_disabled via Auth API. Anonymous sign-in remains disabled.

Two synthetic real Auth users were provisioned by admin API with coach_member=true, passwords privately saved with mode 0600 in ~/.config/ai-career-coach/qa-accounts.json. No invitations or emails were sent. Real group members are not yet provisioned because their addresses were not supplied. Cloud credentials are in the user-approved untracked cloud.env file, mode 0600.

Live HTTPS API tests passed signed-out 401, real token validation, per-user and per-application records, private PDF upload/download byte equality, foreign-user/project/app denial, successful V2 clear with deleted PDF returning 404, other user's PDF preservation, and post-restart document/draft restoration. Real database quota test reserved five synthetic nontransmitted calls, rejected the sixth, then removed those specific test reservations. No DeepSeek call was made. Public Storage path returned 400, with no PDF contents.

Actual Chrome UI checks passed all three sign-ins, welcome/workbench entry, V1 navigation, Claude tabs, V2 three languages and Saved status. V2 cloud quota displayed 5/5 and site remaining20. The two native confirmation dialogs were exercised and clear returned to the empty welcome state. Screenshots are local output/cloud-acceptance files; no credentials appear in them.

DeepSeek is deliberately still unconfigured in Render while awaiting a rotated credential supplied via the private local file. A replacement sent to chat also needs rotation. This cloud turn used zero paid model calls and zero model tokens. Previous local probes were 130 total tokens. Live AI analysis, feedback and interview acceptance therefore remain pending. No hosted AI success is claimed.

The service uses Free compute. Provider quotas, outbound transfer and API consumption remain subject to their service limits. No paid upgrades or payment methods were added. Historical main and DeepSeek refs were preserved.

## Live model verification

At 15:31 HKT all three live connection probes returned HTTP200, ok=true, model deepseek-flash. V1 and V2 each used 60 prompt +5 completion =65 tokens; Claude used88+5=93. Total three paid calls,223 tokens. User explicitly authorized configuring the replacement disclosed in chat; credential remains only in private local file and Render environment. Further rotation is recommended. No full paid business workflow was run.
