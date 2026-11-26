{{shared_rules}}

TASK: Mock interview — give feedback on the student's ACTUAL answer (M3 page 3).

Evaluate only what is in <answer>. Do not credit things the student did not say; do not assume details from the resume unless the student said them.
- "on_topic": up to 4 items. "quote" MUST be copied verbatim from <answer> (a short phrase or sentence). "why": how it addresses the question, in {{output_language}}.
- "missing": up to 4 short points in {{output_language}} describing information the answer lacks. For behavioral questions check Situation / Task / Action / Result and the student's own role; for technical questions check method, reasoning, trade-offs, and how the result was verified.
- "action": exactly ONE improvement the student can try immediately on a re-answer, in {{output_language}}.
- "structure": for behavioral questions, report which STAR parts are clearly present (true/false). For technical questions set all to null and use "reasoning_note" (one sentence on the approach/reasoning).
- "follow_up": if something the student SAID is unclear (their method, their specific role, or the result), ask one follow-up question about it. The follow-up must only build on what was said in <answer>; never presume an unmentioned experience. If nothing needs follow-up, set needed=false.
- If the answer is empty, off-topic, or too short to evaluate, say so plainly in "missing" and keep "on_topic" empty.
- Never comment on personality or predict hiring outcomes.

JSON schema:
{"on_topic": [{"quote": string, "why": string}], "missing": [string], "action": string,
 "structure": {"situation": boolean|null, "task": boolean|null, "action": boolean|null, "result": boolean|null},
 "reasoning_note": string, "follow_up": {"needed": boolean, "question": string, "reason": string}}
