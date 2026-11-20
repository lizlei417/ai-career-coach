{{shared_rules}}

TASK: Job matching (M3 page 2). Show which resume evidence answers each job requirement and which requirements are not yet explained.

For EVERY requirement in <requirements>, decide:
- "direct": a resume line (or supplement) shows the student actually performed this task / used this skill at a comparable level.
- "partial": related evidence exists but it is weaker, narrower, different context, or key details are missing.
- "none": no evidence was found in the materials.
Only treat similar skills as equivalent when the actual tasks are comparable. Keep required and preferred requirements separate (they are already labelled).

For each item:
- "evidence_ids": R/S ids that support the judgement (empty for "none"). Use only ids that exist.
- "rationale": 1–2 sentences in {{output_language}} explaining the judgement, referring to what the evidence actually says.
- "next_step.type": "clarify" when the student seems to have the experience but has not written it clearly; "supplement" when the student should add a missing artefact/detail; "learn" when no related experience appears and a learning or practice direction is appropriate; "none" for direct evidence that needs no action.
- "next_step.text": a concrete, doable action in {{output_language}}.
- "priority": 1 (handle first), 2, or 3. Required items with weak evidence come first.

Also return "priority_order": the requirement ids to handle first (max 5, only items with partial or no evidence), and "overview": one neutral sentence in {{output_language}} describing coverage (e.g. how many required items have direct evidence). Never describe this as a probability or a chance of being hired. Remind that "no evidence found" does not mean the student lacks the ability.

JSON schema:
{"items": [{"requirement_id": string, "status": "direct"|"partial"|"none", "evidence_ids": [string], "rationale": string, "next_step": {"type": "clarify"|"supplement"|"learn"|"none", "text": string}, "priority": 1|2|3}],
 "priority_order": [string], "overview": string, "guidance_used": [string]}
