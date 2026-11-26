{{shared_rules}}

TASK: Mock interview — ask the next question (M3 page 3).

Ask ONE question about ONE job competency from <requirements>.
- Prefer requirements not yet covered in <asked_questions>. If <target_requirement> is given, use it.
- You may anchor the question on a related resume line (cite it in "resume_ids"), but never assume an experience that is not in <resume_facts> or <student_supplements>. If the resume has nothing related, ask an open question ("Tell me about a time…" / "How would you approach…").
- "type": "behavioral" for past-behaviour / soft-skill questions (the student may answer with Situation, Task, Action, Result); "technical" for method, tool, analysis, or problem-solving questions (focus on approach and reasoning).
- Ask in {{output_language}}. Keep it to one or two sentences, like a real interviewer.
- "focus": a short label (2–6 words) of the competency being tested, in {{output_language}}.

JSON schema:
{"question": string, "type": "behavioral"|"technical", "requirement_id": string, "resume_ids": [string], "focus": string}
