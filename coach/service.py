from coach.errors import CoachError
from coach.knowledge import KnowledgeBase
from coach.models import (Audit, Context, Extraction, Feedback, Guide, InterviewSummary,
                          Matching, Optimization, Question, Turn)
from coach.parsing import sources, validate_text
from coach.prompts import prompt
from coach.validation import (check_evidence, check_extraction, check_matching,
                              check_optimization, has_new_numbers, require)


class CareerCoach:
    def __init__(self, client, knowledge: KnowledgeBase, language: str = "简体中文"):
        self.client, self.knowledge, self.language = client, knowledge, language

    def call(self, name, schema, payload):
        return self.client.generate(schema, prompt(name), {"output_language": self.language, **payload})

    def prepare(self, resume: str, jd: str, fingerprint: str) -> Context:
        resume_sources = sources(validate_text(resume, "简历"), "R")
        jd_sources = sources(validate_text(jd, "JD"), "J")
        extraction = self.call("extract", Extraction, {
            "resume": [s.model_dump() for s in resume_sources],
            "jd": [s.model_dump() for s in jd_sources]})
        check_extraction(extraction, jd_sources)
        self.audit_whole(extraction, {"resume": [s.model_dump() for s in resume_sources],
                                      "jd": [s.model_dump() for s in jd_sources]})
        return Context(fingerprint=fingerprint, resume=resume_sources, jd=jd_sources,
                       requirements=extraction.requirements)

    def payload(self, context: Context, topic: str):
        guides = self.knowledge.retrieve(topic + " " + " ".join(q.quote for q in context.requirements))
        return {"resume": [s.model_dump() for s in context.resume],
                "jd": [s.model_dump() for s in context.jd],
                "requirements": [q.model_dump() for q in context.requirements],
                "guides": [g.model_dump() for g in guides]}, guides

    def check_guides(self, ids: list[str], guides: list[Guide]):
        require(set(ids) <= {g.id for g in guides})

    def audit(self, candidates: list[dict], original: dict) -> dict[str, bool]:
        if not candidates:
            return {}
        result = self.call("audit", Audit, {"original_sources": original, "candidate_items": candidates})
        expected = [c["id"] for c in candidates]
        actual = [a.id for a in result.items]
        require(len(actual) == len(set(actual)) and set(actual) == set(expected),
                "独立事实核查未完整返回结果，本次输出已拦截，请重试。")
        return {a.id: a.supported for a in result.items}

    def audit_whole(self, result, payload):
        verdicts = self.audit([{"id": "result", "content": result.model_dump()}], payload)
        require(verdicts["result"], "独立事实核查未通过，本次结果未展示，请重试或补充材料。")

    def optimize(self, context: Context):
        payload, guides = self.payload(context, "resume optimization 简历优化 原句 改写")
        result = self.call("optimize", Optimization, payload)
        check_optimization(result, context)
        self.check_guides(result.guide_ids, guides)
        candidates = [{"id": r.id, "type": "revision", "content": r.model_dump()} for r in result.revisions]
        candidates += [{"id": f"gap-{i}", "type": "gap", "content": g.model_dump()} for i, g in enumerate(result.gaps)]
        require(len({c['id'] for c in candidates}) == len(candidates))
        verdicts = self.audit(candidates, payload)
        for revision in result.revisions:
            if has_new_numbers(revision.optimized, [e.quote for e in revision.evidence]):
                verdicts[revision.id] = False
        safe = result.model_copy(update={
            "revisions": [r for r in result.revisions if verdicts[r.id]],
            "gaps": [g for i, g in enumerate(result.gaps) if verdicts[f"gap-{i}"]]})
        blocked = len(candidates) - len(safe.revisions) - len(safe.gaps)
        return safe, guides, blocked

    def match(self, context: Context):
        payload, guides = self.payload(context, "job matching 岗位匹配 证据 必备条件 优先条件")
        result = self.call("match", Matching, payload)
        check_matching(result, context)
        self.check_guides(result.guide_ids, guides)
        self.audit_whole(result, payload)
        return result, guides

    def question(self, context: Context, turns: list[Turn], follow_up: str | None = None, translate_follow_up: bool = False):
        if len(turns) >= 30:
            raise CoachError("本次练习已达 30 次回答上限，请结束并生成总结。")
        payload, guides = self.payload(context, "interview questions 面试 提问 STAR")
        payload["history"] = [t.model_dump() for t in turns]
        if follow_up:
            require(bool(turns))
            payload["requested_follow_up"] = follow_up
            payload["translate_follow_up"] = translate_follow_up
            payload["current_question"] = turns[-1].question.model_dump()
        result = self.call("question", Question, payload)
        require(result.requirement_id in {q.id for q in context.requirements} and bool(result.text.strip()))
        check_evidence(result.evidence, context.resume)
        self.check_guides(result.guide_ids, guides)
        if follow_up:
            require(result.requirement_id == turns[-1].question.requirement_id)
            require(translate_follow_up or result.text == follow_up)
        self.audit_whole(result, payload)
        return result, guides

    def feedback(self, context: Context, question: Question, answer: str):
        if not answer.strip():
            raise CoachError("请先输入你的真实回答。")
        if len(answer) > 8000:
            raise CoachError("单次回答最多 8,000 字符，请精简后提交。")
        payload, guides = self.payload(context, "interview feedback 面试反馈 STAR 方法 推理")
        payload.update(current_question=question.model_dump(), current_answer=answer)
        result = self.call("feedback", Feedback, payload)
        require(bool(result.action.strip()) and bool(result.strengths) and bool(result.missing_information))
        require(all(q.strip() and q in answer for q in result.answer_quotes))
        if result.follow_up is not None:
            require(bool(result.follow_up.strip()))
        self.check_guides(result.guide_ids, guides)
        self.audit_whole(result, payload)
        return result, guides

    def summarize(self, context: Context, turns: list[Turn]):
        require(bool(turns), "还没有完成的回答，请至少提交一次回答后生成总结。")
        payload, guides = self.payload(context, "interview summary 面试总结 练习计划")
        payload["completed_turns"] = [t.model_dump() for t in turns]
        result = self.call("summary", InterviewSummary, payload)
        require(bool(result.strengths) and bool(result.practice_priorities) and bool(result.next_steps))
        self.check_guides(result.guide_ids, guides)
        self.audit_whole(result, payload)
        return result, guides
