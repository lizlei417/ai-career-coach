from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(Record):
    id: str
    text: str


class Requirement(Record):
    id: str
    source_id: str
    quote: str
    category: Literal["responsibility", "required", "preferred"]


class Extraction(Record):
    resume_is_valid: bool
    jd_is_valid: bool
    issues: list[str]
    requirements: list[Requirement] = Field(max_length=60)


class Context(Record):
    fingerprint: str
    resume: list[Source]
    jd: list[Source]
    requirements: list[Requirement]


class Evidence(Record):
    source_id: str
    quote: str


class Revision(Record):
    title: str = Field(default_factory=str)
    id: str
    requirement_ids: list[str]
    evidence: list[Evidence]
    optimized: str
    reason: str


class Gap(Record):
    requirement_id: str
    explanation: str
    suggestion: str


class Optimization(Record):
    revisions: list[Revision] = Field(max_length=15)
    gaps: list[Gap]
    guide_ids: list[str]


class Match(Record):
    requirement_id: str
    status: Literal["direct", "partial", "none"]
    evidence: list[Evidence]
    assessment: str
    gap_type: Literal["sufficient", "clarify_existing", "not_in_material"]
    suggestion: str
    priority: Literal["high", "medium", "low"]


class Matching(Record):
    matches: list[Match]
    guide_ids: list[str]


class Question(Record):
    text: str
    kind: Literal["behavioral", "technical", "situational"]
    requirement_id: str
    evidence: list[Evidence]
    guide_ids: list[str]


class Feedback(Record):
    strengths: list[str]
    missing_information: list[str]
    action: str
    answer_quotes: list[str]
    follow_up: str | None
    guide_ids: list[str]


class Turn(Record):
    question: Question
    answer: str
    feedback: Feedback
    attempt: int


class InterviewSummary(Record):
    strengths: list[str]
    practice_priorities: list[str]
    next_steps: list[str]
    guide_ids: list[str]


class AuditItem(Record):
    id: str
    supported: bool
    reason: str


class Audit(Record):
    items: list[AuditItem]


class Guide(Record):
    id: str
    filename: str
    text: str
