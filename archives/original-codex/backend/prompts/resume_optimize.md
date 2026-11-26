{{shared_rules}}

TASK: Resume optimisation (M3 page 1). Make the experiences the job values clearer, without turning job requirements into things the student did.

Steps:
1. Compare each requirement in <requirements> against <resume_facts> and <student_supplements>.
2. Distinguish two cases:
   a) "done but not written clearly": a resume line contains the experience but the wording, verb, order, or emphasis hides its relevance → produce a rewrite item.
   b) "no evidence in the materials": nothing supports the requirement → produce a "missing" item asking the student to supply material. Never write it for them.
3. Rewrites may ONLY adjust verbs, word order, and emphasis, and may merge in facts from cited supplements. Keep the original scope of responsibility. Do not add tools, results, numbers, team size, duration, or seniority not present in the cited evidence. If the original line is already clear and relevant, do not include it.
4. Write each rewrite in the SAME language as the original resume line (a resume is a document the student will submit). The "reason" is written in {{output_language}}.
5. Choose up to 8 resume lines with the highest relevance. Skip headings, contact details, and education lines unless they matter for a requirement.

Field rules:
- "source_id": the single R id being rewritten.
- "evidence_ids": every R/S id whose facts the rewrite uses (must include source_id).
- "requirement_ids": Q ids this rewrite helps address.
- "changes": subset of ["verb", "order", "focus", "clarity", "merge_supplement"].
- "reason": 1–2 sentences: what changed and why it matters for this job.
- "missing.kind": "unclear" when related experience exists but key details (method, role, result) are not stated; "absent" when no related experience appears at all.
- "missing.ask": a direct question asking the student for the specific fact needed.
- "guidance_used": G ids you actually relied on (empty if none).

JSON schema:
{"items": [{"source_id": string, "rewrite": string, "reason": string, "evidence_ids": [string], "requirement_ids": [string], "changes": [string]}],
 "missing": [{"requirement_id": string, "kind": "unclear"|"absent", "note": string, "ask": string, "related_ids": [string]}],
 "guidance_used": [string]}
