"""Official M3 protocol, adapted to existing V3 UI and historical project shapes.

The supplied system message is used verbatim. Adapters only validate evidence
and translate keys; they do not invent scores or additional coaching rules.
"""
from __future__ import annotations
import hashlib
import json
import re
import logging
from .config import M3_PROMPT_PATH
from .errors import AppError
from .materials import check_materials, segment
from .grounding import grounding_report, quote_in_text, norm
from .rag import index, build_query
from .llm import complete_json
from .coach import _fingerprint, _validate_bundle

MATERIALS_VERSION = "m3-jd-sentences-v1"
LANG = {"zh-CN": "zh-Hans", "zh-TW": "zh-Hant", "en": "en"}
RESULT_KEYS = {
    "resume_optimization": "edits: array of {original, jd_quote, rewrite, reason}; questions_to_student: string array",
    "job_matching": "requirements: array of {jd_quote, priority, evidence_quotes: string array, status, reason, next_step}",
    "mock_interview": "phase: question|follow_up|summary; question: string|null; feedback: {answer_quote,strength,next_try}|null; summary: string|null",
}
STAGES = {"no_experience", "current_student", "recent_graduate"}
GOALS = {"internship", "job"}


def system_prompt():
    try:
        text = M3_PROMPT_PATH.read_text(encoding="utf-8")
        return re.search(r"```text\n(.*?)\n```", text, re.S).group(1)
    except (OSError, AttributeError):
        raise AppError("PROMPT_UNAVAILABLE", 503) from None


def prompt_status():
    try:
        text = system_prompt()
        return [{"name": "M3_Prompt_v1", "custom": False, "loaded": True, "protocol_adapter": "m3-json-v1",
                 "sha256": hashlib.sha256(text.encode()).hexdigest()}]
    except AppError:
        return [{"name": "M3_Prompt_v1", "custom": False, "loaded": False}]


def profile(stage, goal):
    if stage not in STAGES or goal not in GOALS:
        raise AppError("PROFILE_REQUIRED", 422)
    return {"user_stage": stage, "job_goal": goal}


async def prepare_materials(resume_text, jd_text, job_title, lang, user_stage=None, job_goal=None, resume_format="text"):
    # Parsing and exact JD-line requirements need no model call. M3 is applied
    # on each actual coaching operation, preserving the existing 10-call rule.
    if lang not in LANG: raise AppError("LANGUAGE_REQUIRED", 422)
    p = profile(user_stage, job_goal)
    check_materials(resume_text, jd_text)
    resume, jd = segment(resume_text, "R"), segment(jd_text, "J")
    if len([x for x in resume if not x["heading"]]) < 2:
        raise AppError("RESUME_TOO_SHORT", 422)
    reqs = []
    scoped = any(x["heading"] and re.search(r"responsibilit|requirement|qualification|preferred|任职|任職|职责|職責|要求|条件|條件", x["text"], re.I) for x in jd)
    in_scope = not scoped
    for line in jd:
        if line["heading"]:
            if re.search(r"responsibilit|requirement|qualification|preferred|任职|任職|职责|職責|要求|条件|條件", line["text"], re.I):
                in_scope = True
            continue
        if not in_scope or len(norm(line["text"])) < 8:
            continue
        if line == jd[0] and job_title and job_title.casefold() in line["text"].casefold():
            continue
        cat = "preferred" if re.search(r"preferred|nice.to.have|加分|優先|优先", line["text"]+line.get("section", ""), re.I) else "required"
        # Split exact JD sentences even below the PDF segmenter's length cutoff.
        # This avoids a degree requirement overwriting a language requirement.
        parts = re.split(r"(?<=[。！？!?；;])\s*|(?<=\.)\s+(?=[A-Z])", line["text"])
        for part in parts:
            if len(norm(part)) < 8: continue
            reqs.append({"id": f"Q{len(reqs)+1}", "text": part, "source_ids": [line["id"]], "category": cat, "kind": "technical"})
    if not reqs:
        raise AppError("JD_NO_REQUIREMENTS", 422)
    return {"fingerprint": _fingerprint(resume_text, jd_text, job_title, p["user_stage"], p["job_goal"], MATERIALS_VERSION), "job_title": job_title[:120],
            "resume_lines": resume, "jd_lines": jd, "requirements": reqs, "lang": lang,
            "prompt_version": "M3_Prompt_v1", "pipeline_version": MATERIALS_VERSION, "resume_format": resume_format, **p}


def texts(b):
    return "\n".join(x["text"] for x in b["resume_lines"]), "\n".join(x["text"] for x in b["jd_lines"])


async def call(task, b, lang, *, action="start", history=None, answer="", extra=""):
    if lang not in LANG: raise AppError("LANGUAGE_REQUIRED", 422)
    p = profile(b.get("user_stage"), b.get("job_goal"))
    resume, jd = texts(b)
    chunks = index.search(task, build_query(task, p["job_goal"], resume, jd, extra), 3)
    payload = {"task": task, "ui_language": LANG.get(lang, ""), **p, "resume_format": b.get("resume_format", "text"),
               "resume_text": resume, "jd_text": jd, "rag_chunks": chunks,
               "interview_action": action, "history": history or [], "answer_text": answer}
    # Restate only the supplied protocol's machine schema, not new coaching
    # policy. JSON mode alone guarantees syntax, not the required envelope.
    contract = ("\n\nM3 JSON protocol reminder for task=" + task +
        ": exactly four top-level keys: status (ok or needs_input), message (string), "
        "result (object when ok; null when needs_input), citations (array of {claim, chunk_id}; "
        "use [] when no citations, never null or omitted). result fields: " + RESULT_KEYS[task] +
        ". For mock_interview finish, result.phase must be summary. Do not output the schema itself.")
    out = await complete_json(system_prompt() + contract, json.dumps(payload, ensure_ascii=False))
    if out.get("status") == "needs_input":
        # The message is still returned in detail; frontend provides a localized
        # recovery hint. No success result is saved for an incomplete analysis.
        raise AppError("M3_NEEDS_INPUT", 422)
    if out.get("status") != "ok" or not isinstance(out.get("result"), dict) or not isinstance(out.get("citations"), list):
        diagnostic = {"status_ok": out.get("status")=="ok", "result_type": type(out.get("result")).__name__,
                      "citations_type": type(out.get("citations")).__name__}
        logging.getLogger("coach.m3").warning("invalid envelope task=%s shape=%s", task, diagnostic)
        raise AppError("AI_FORMAT", 502, "m3_envelope:" + json.dumps(diagnostic, separators=(",", ":")))
    ids = {x["chunk_id"] for x in chunks}
    citations = [x for x in out["citations"] if isinstance(x, dict) and x.get("chunk_id") in ids and isinstance(x.get("claim"), str)]
    guidance = {"connected": index.status()["connected"], "sources": [
        {"id": c["chunk_id"], "source": c["page_title"], "section": c["section"], "excerpt": c["text"],
         "source_url": c["source_url"], "evidence_type": c["evidence_type"],
         "used": any(x["chunk_id"] == c["chunk_id"] for x in citations),
         "claims": [x["claim"] for x in citations if x["chunk_id"] == c["chunk_id"]]} for c in chunks]}
    return out["result"], guidance, {"status": "ok", "message": str(out.get("message") or ""), "citations": citations, "prompt_version": "M3_Prompt_v1"}


def bundle(materials, lang):
    if lang not in LANG: raise AppError("LANGUAGE_REQUIRED", 422)
    b = _validate_bundle(materials)
    b.update(profile(materials.get("user_stage"), materials.get("job_goal")))
    b["resume_format"] = materials.get("resume_format") if materials.get("resume_format") in ("pdf", "word", "text") else "text"
    return b


def strings(value):
    return [v[:800] for v in value if isinstance(v, str)] if isinstance(value, list) else []


async def resume_optimize(materials, lang):
    b = bundle(materials, lang)
    result, guidance, meta = await call("resume_optimization", b, lang)
    if not isinstance(result.get("edits"), list) or not isinstance(result.get("questions_to_student"), list):
        raise AppError("AI_FORMAT", 502, "m3_edits")
    items, seen, hidden = [], set(), 0
    _, jd = texts(b)
    for edit in result["edits"][:3]:
        if not isinstance(edit, dict) or not all(isinstance(edit.get(k), str) for k in ("original", "jd_quote", "rewrite", "reason")):
            raise AppError("AI_FORMAT", 502, "m3_edit")
        original, rewrite = edit["original"].strip(), edit["rewrite"].strip()
        candidates = [ln for ln in b["resume_lines"] if not ln["heading"] and original and original in ln["text"]]
        if len(candidates) != 1 or not rewrite or (edit["jd_quote"] and not quote_in_text(edit["jd_quote"], jd)):
            hidden += 1
            continue
        src = candidates[0]
        if src["id"] in seen or norm(original) == norm(rewrite):
            continue
        seen.add(src["id"])
        # A model quote may cover part of a line. Preserve all untouched text.
        whole = src["text"].replace(original, rewrite, 1)
        report = grounding_report(whole, src["text"])
        # Conservative checks cannot prove semantic truth. Flag loss of an
        # explicit support role or negation for human review before adoption.
        support = r"\b(helped|assisted|supported|participated|contributed)\b|参与|參與|协助|協助|辅助|輔助"
        negation = r"\b(not|never|without|no)\b|未曾|没有|沒有|并未|並未"
        for pattern, label in [(support, "responsibility_scope"), (negation, "negation_scope")]:
            if re.search(pattern, original, re.I) and not re.search(pattern, rewrite, re.I):
                report["unsupported_terms"].append(label)
        reqids = [r["id"] for r in b["requirements"] if edit["jd_quote"] and quote_in_text(edit["jd_quote"], r["text"])]
        items.append({"id": f"O{len(items)+1}", "source_id": src["id"], "original": src["text"], "section": src.get("section", ""),
                      "rewrite": whole, "reason": edit["reason"], "evidence_ids": [src["id"]], "requirement_ids": reqids,
                      "changes": [], "verification": {"status": "needs_review" if any(report.values()) else "grounded", **report}})
    return {"items": items, "missing": [], "questions_to_student": strings(result["questions_to_student"]),
            "hidden_count": hidden, "guidance": guidance, "lang": lang, "m3": meta}


async def job_match(materials, lang):
    b = bundle(materials, lang)
    result, guidance, meta = await call("job_matching", b, lang)
    if not isinstance(result.get("requirements"), list):
        raise AppError("AI_FORMAT", 502, "m3_requirements")
    resume, jd = texts(b)
    assessed = {}
    for r in result["requirements"]:
        if not isinstance(r, dict) or r.get("status") not in ("direct", "partial", "not_evidenced") or r.get("priority") not in ("required", "preferred", "unspecified"):
            raise AppError("AI_FORMAT", 502, "m3_requirement")
        if not all(isinstance(r.get(k), str) for k in ("jd_quote", "reason", "next_step")) or not isinstance(r.get("evidence_quotes"), list) or not all(isinstance(v, str) for v in r["evidence_quotes"]):
            raise AppError("AI_FORMAT", 502, "m3_requirement_fields")
        quote = r.get("jd_quote")
        if not isinstance(quote, str) or not quote_in_text(quote, jd):
            continue
        candidates = [q for q in b["requirements"] if quote_in_text(quote, q["text"]) or quote_in_text(q["text"], quote)]
        if not candidates:
            continue
        for q in candidates:
            ev = []
            for text in strings(r.get("evidence_quotes")):
                if not quote_in_text(text, resume):
                    continue
                line = next((x for x in b["resume_lines"] if quote_in_text(text, x["text"])), None)
                if line: ev.append({"id": line["id"], "text": text})
            status = {"not_evidenced": "none"}.get(r["status"], r["status"])
            downgraded = status != "none" and not ev
            if downgraded: status = "none"
            if status == "none": ev = []
            prior = assessed.get(q["id"])
            item = {"requirement_id": q["id"], "status": status, "evidence": ev,
                "rationale": str(r.get("reason") or "")[:800], "next_step": {"type": "clarify", "text": str(r.get("next_step") or "")[:800]},
                "priority_code": r["priority"], "priority": {"required":1,"preferred":2,"unspecified":3}[r["priority"]], "verification": "downgraded" if downgraded else "ok", "jd_quote": quote}
            # Multiple model requirements can legitimately map to one sentence.
            # Preserve each assessment and every quote instead of last-write-wins.
            detail = {"jd_quote": quote, "priority": r["priority"], "status": status,
                      "reason": item["rationale"], "next_step": item["next_step"]["text"]}
            item["assessments"] = [detail]
            if prior:
                details = prior["assessments"] + [detail]
                evidence = list({(e["id"], e["text"]):e for e in prior["evidence"]+ev}.values())
                item.update(assessments=details, evidence=evidence,
                    status="direct" if all(d["status"]=="direct" for d in details) else "partial" if evidence else "none",
                    rationale="\n".join(d["jd_quote"]+" — "+d["reason"] for d in details),
                    next_step={"type":"clarify","text":"\n".join(d["jd_quote"]+" — "+d["next_step"] for d in details)},
                    priority=min(prior["priority"], item["priority"]),
                    priority_code="required" if any(d["priority"]=="required" for d in details) else "preferred" if any(d["priority"]=="preferred" for d in details) else "unspecified",
                    verification="downgraded" if "downgraded" in (prior["verification"],item["verification"]) else "ok")
            assessed[q["id"]] = item
    items = [assessed.get(q["id"], {"requirement_id": q["id"], "status": "unassessed", "evidence": [], "rationale": "", "next_step": {"type": "none", "text": ""}, "priority_code": "unspecified", "priority": 3, "verification": "missing"}) for q in b["requirements"]]
    return {"items": items, "priority_order": [x["requirement_id"] for x in sorted(items, key=lambda x:x["priority"]) if x["status"] in ("partial", "none")][:5],
            "overview": "", "guidance": guidance, "lang": lang, "m3": meta}


def history_of(turns):
    history = []
    for turn in turns[-4:]:
        if turn.get("question"): history.append({"role": "assistant", "content": str(turn["question"])[:1000]})
        if turn.get("answer"): history.append({"role": "user", "content": str(turn["answer"])[:4000]})
    return history


def question_out(question, b, guidance, meta):
    if not isinstance(question, str) or not question.strip():
        raise AppError("AI_FORMAT", 502, "m3_question")
    req = b["requirements"][0]
    return {"question": question[:1200], "type": "behavioral" if re.search(r"tell me about a time|describe a time|曾经|曾經|经历|經歷|举例|舉例", question, re.I) else "technical", "requirement_id": req["id"], "resume_refs": [], "focus": "", "guidance": guidance, "m3": meta}


async def interview_question(materials, lang, asked, target_requirement):
    b = bundle(materials, lang)
    # Existing clients may request a next question directly. Include previous
    # answers as evidence, never evaluate an unanswered question.
    if len(asked) >= 4 or sum(not t.get("is_follow_up") for t in asked) >= 2:
        raise AppError("INTERVIEW_COMPLETE", 422)
    answered = [t for t in asked if t.get("answer")]
    if asked and not asked[-1].get("answer"):
        raise AppError("ANSWER_EMPTY", 422)
    result, guidance, meta = await call("mock_interview", b, lang, action="respond" if answered else "start",
        history=history_of(asked)[:-1] if answered else [], answer=str(asked[-1].get("answer", "")) if answered else "", extra=str(target_requirement or ""))
    if result.get("phase") not in ("question", "follow_up") or (not answered and result.get("feedback") is not None):
        raise AppError("AI_FORMAT", 502, "m3_question_phase")
    return question_out(result.get("question"), b, guidance, meta)


async def interview_feedback(materials, lang, question, answer, history, turns=None):
    b = bundle(materials, lang)
    if not str(question.get("question") or "").strip() or len(norm(answer)) < 4:
        raise AppError("ANSWER_EMPTY", 422)
    earlier = history_of(turns or [])
    earlier.append({"role": "assistant", "content": str(question["question"])[:1200]})
    result, guidance, meta = await call("mock_interview", b, lang, action="respond", history=earlier, answer=answer[:8000], extra=question["question"])
    if result.get("phase") not in ("question", "follow_up", "summary") or not isinstance(result.get("feedback"), dict):
        raise AppError("AI_FORMAT", 502, "m3_feedback")
    feedback = result["feedback"]
    if not all(isinstance(feedback.get(k), str) for k in ("answer_quote", "strength", "next_try")):
        raise AppError("AI_FORMAT", 502, "m3_feedback_fields")
    quote = str(feedback.get("answer_quote") or "")
    valid = quote_in_text(quote, answer)
    # The formal prompt allows one follow-up per main question. The UI tracks
    # explicit follow-up turns, so a follow-up cannot recursively spawn another.
    follow = result["phase"] == "follow_up" and not question.get("is_follow_up")
    next_q = result.get("question") if result["phase"] == "question" else None
    return {"on_topic": [{"quote": quote, "why": str(feedback.get("strength") or "")}] if valid and feedback.get("strength") else [],
            "missing": [], "action": str(feedback.get("next_try") or ""), "structure": None, "reasoning_note": "",
            "follow_up": {"needed": follow and bool(result.get("question")), "question": str(result.get("question") or "") if follow else "", "reason": ""},
            "next_question": question_out(next_q, b, guidance, meta) if next_q else None,
            "session_summary": str(result.get("summary") or "") if result["phase"] == "summary" else "",
            "unverified_quotes_removed": 0 if valid else 1, "guidance": guidance, "lang": lang, "m3": meta}


async def interview_summary(lang, turns, materials=None):
    if not turns: raise AppError("ANSWER_EMPTY", 422)
    b = bundle(materials or {}, lang)
    result, guidance, meta = await call("mock_interview", b, lang, action="finish", history=history_of(turns))
    if result.get("phase") != "summary" or not isinstance(result.get("summary"), str) or not result["summary"].strip():
        raise AppError("AI_FORMAT", 502, "m3_summary")
    return {"strengths": [], "priorities": [], "next_session": result["summary"], "guidance": guidance, "lang": lang, "m3": meta}
