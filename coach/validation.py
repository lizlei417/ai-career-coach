import re
from coach.errors import CoachError
from coach.models import Context, Evidence, Extraction, Matching, Optimization, Source


def require(ok: bool, message: str = "模型结果的来源核对未通过，结果已拦截。请重新分析。"):
    if not ok:
        raise CoachError(message)


def check_evidence(evidence: list[Evidence], sources: list[Source]):
    lookup = {s.id: s.text for s in sources}
    for item in evidence:
        require(item.source_id in lookup and bool(item.quote.strip()) and item.quote in lookup[item.source_id])


def check_extraction(result: Extraction, jd: list[Source]):
    if not result.resume_is_valid or not result.jd_is_valid:
        raise CoachError("材料未通过 AI 完整性检查：" + "；".join(result.issues or ["请补充真实简历及完整岗位要求。 "]))
    require(bool(result.requirements), "未识别出可核对的岗位要求，请补充完整 JD。")
    ids = [q.id for q in result.requirements]
    require(len(ids) == len(set(ids)))
    check_evidence([Evidence(source_id=q.source_id, quote=q.quote) for q in result.requirements], jd)


def check_optimization(result: Optimization, context: Context):
    ids = [r.id for r in result.revisions]
    require(len(ids) == len(set(ids)))
    valid = {q.id for q in context.requirements}
    for r in result.revisions:
        require(bool(r.optimized.strip()) and bool(r.evidence) and bool(r.requirement_ids))
        require(set(r.requirement_ids) <= valid)
        check_evidence(r.evidence, context.resume)
    require(all(g.requirement_id in valid for g in result.gaps))


def check_matching(result: Matching, context: Context):
    expected = {q.id for q in context.requirements}
    actual = [m.requirement_id for m in result.matches]
    require(len(actual) == len(set(actual)) and set(actual) == expected,
            "模型没有逐项覆盖全部岗位要求，结果已拦截，请重新分析。")
    for m in result.matches:
        check_evidence(m.evidence, context.resume)
        require(bool(m.evidence) == (m.status != "none"))
        require((m.status == "direct") == (m.gap_type == "sufficient"))
        if m.status == "none":
            require(m.gap_type == "not_in_material")


def has_new_numbers(optimized: str, originals: list[str]) -> bool:
    def numbers(text):
        return {re.sub(r"\s", "", n) for n in re.findall(r"\d+(?:[.,]\d+)*(?:\s*[%％])?", text)}
    return not numbers(optimized) <= numbers(" ".join(originals))
