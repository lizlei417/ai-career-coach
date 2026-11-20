{{shared_rules}}

TASK: Build the shared requirement list from a job description.

Read <jd_lines>. Extract the employer's requirements and classify each one:
- "responsibility": a duty of the role (what the hire will do)
- "required": a must-have qualification, skill or condition
- "preferred": a nice-to-have / bonus / "plus" item
Use JD wording cues (e.g. Requirements / Qualifications / 任职要求 / 必备 → required; Preferred / Nice to have / Bonus / 优先 / 加分 → preferred). If unclear, choose the most reasonable category.

For each requirement:
- "text": a concise restatement (max ~20 words) in {{output_language}}
- "source_ids": the J ids it comes from (must exist in <jd_lines>)
- "kind": "behavioral" if it is about teamwork, communication, leadership, ownership etc.; "technical" if it is about methods, tools, domain knowledge, analysis.
Merge duplicates. Ignore company marketing, benefits, salary, and application instructions. Keep at most 18 requirements.

Also set "jd_readable": false only if the text is clearly not a job description (e.g. a login page, an error page, unrelated content).

JSON schema:
{"job_title": string, "jd_readable": boolean, "requirements": [{"category": "responsibility"|"required"|"preferred", "text": string, "source_ids": [string], "kind": "behavioral"|"technical"}]}
