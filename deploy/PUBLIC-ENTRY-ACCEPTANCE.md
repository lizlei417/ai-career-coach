# Public entry acceptance — 2026-11-21

Live gateway: https://ai-career-coach-three-versions.onrender.com

| App | Entrance | Branch | Live code commit |
| --- | --- | --- | --- |
| Codex V1 | /v1/ | feature/v1-auth-deploy | 582af4360ce5f900871ec2c15c7154a69ccc7620 |
| Codex V2 | /v2/ | feature/v2-auth-deploy | 8cf5bf355032682ef9d122eace6f14d53bccee15 |
| Claude | /claude/ | feature/claude-auth-deploy | a334e2f1f15a4d875345a9b391e6c626dcb5981a |

The existing Render Free service deployed successfully. The Docker build pins V1/Claude commits; V2 is the build context. Auto-deploy remains disabled. Subsequent documentation-only commits do not change the live image. Existing archived main/DeepSeek refs were checked with git ls-remote and remain unchanged. No force push, new server, paid upgrade, existing-user deletion or schema reset was performed.

## Authentication and email

Public signup is enabled, email confirmation required and anonymous sign-in disabled. Passwords require 10 characters with upper/lowercase and digits. App-scoped redirect patterns cover /v1/**, /v2/** and /claude/** on the actual HTTPS domain. Brevo Free SMTP is configured server-side. One real external QQ mailbox registered through the production signup form. Brevo recorded Sent, Delivered and Opened. The user confirmed the email; an actual password login and Supabase email_confirmed_at verified completion. The account has no coach_member or coach_admin marker. It successfully logged into all three production workbenches.

CAPTCHA is deliberately disabled at the user's explicit instruction. Existing Supabase authentication rate limits remain active, including 30 signup/signin requests per 5 minutes per IP and 60 seconds minimum between emails to one user. This does not eliminate account-farming risk. A second newly registered real mailbox was not provided: cross-user live tests used the newly public account and one existing real Auth QA account, not two newly public accounts.

## Live checks

- All three base routes show public landing pages before private content, including when a session exists. Claude retains its original architectural artwork. Public pages have no test account panel.
- Get started enters authentication while signed out and enters the workspace directly with a valid session. Normal account menu is top-right and private-only. Logout returns to public landing with the private app unmounted.
- V1 unauthenticated internal workspace navigation redirects to its scoped login with a safe next parameter. Login preserves the intended path. Feature navigation and refresh were exercised. English, simplified and traditional Chinese were exercised across the public/auth/private pages.
- Browser login with the newly confirmed ordinary account passed in V1, V2 and Claude. V2 initially contained only its own new empty default project. Claude tabs switch without AI calls.
- Live API checks passed unauthenticated private/AI rejection; new ordinary-user access in all apps; same-ID application separation; foreign-owner denial; optimistic revision conflict protection.
- A synthetic three-page PDF uploaded to V2 and downloaded byte-for-byte. Foreign owner, version and project ID were denied. Anonymous request was denied. Public Storage URL returned no PDF. Only newly created acceptance fixtures were removed afterward.
- V2 quota for the new public account returned limit=5, remaining=5, siteRemaining=17, blocked=false. The live model-call ledger was unchanged during this public-entry acceptance. Existing atomic quota, 402 latch and emergency-stop unit tests passed. No new paid model request was sent.
- Unit tests: V1 six, V2 six, Claude three passing. Three frontend production builds passed. Built assets were scanned for secret key patterns with zero findings. Keys remain in private local files and platform secret settings.

The earlier hosted connection verification made three DeepSeek calls, 223 total tokens using deepseek-flash. This public-entry increment made zero paid calls and zero model tokens. Full paid resume/match/interview workflows were not repeated.

## Remaining verification

Password-reset email was requested successfully through the production V2 form. End-to-end user-selected password completion is pending the user's action. A second self-registered mailbox is needed to specifically claim two-new-public-user acceptance. No CAPTCHA is expected. Email delivery uses a free sender relay, not a purchased custom domain; broader mailbox deliverability has only been demonstrated for the supplied mailbox.
