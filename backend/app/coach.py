"""Shared materials, context assembly, and the three coaching pipelines.

Flow (M3 page 4):
  submit materials -> readability check -> shared bundle (resume facts,
  job requirements, source lines) -> per-feature context (student evidence and
  school guidance passed separately) -> model -> output verification -> UI.

The API is stateless: the client keeps the shared bundle and sends it back with
each feature request, so the three features always reuse one parse.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from . import errors
from .config import CUSTOM_PROMPT_DIR, PROMPT_DIR
from .errors import AppError
from .grounding import grounding_report, norm, quote_in_text
from .kb import kb
from .llm import complete_json
from .materials import check_materials, segment

LANG_NAME = {
    "zh-CN": "Simplified Chinese (简体中文)",
    "zh-TW": "Traditional Chinese as used in Hong Kong (繁體中文)",
    "en": "English",
}
PROB_RE = re.compile(r"(概率|機率|几率|幾率|probability|likelihood|chance of|\d+\s*%)", re.I)


# ------------------------------------------------------------------ prompts

def load_prompt(name: str, lang: str) -> str:
    custom = CUSTOM_PROMPT_DIR / f"{name}.md"
    path = custom if custom.exists() else PROMPT_DIR / f"{name}.md"
    shared_custom = CUSTOM_PROMPT_DIR / "_shared_rules.md"
    shared_path = shared_custom if shared_custom.exists() else PROMPT_DIR / "_shared_rules.md"
    shared = shared_path.read_text(encoding="utf-8")
    text = path.read_text(encoding="utf-8").replace("{{shared_rules}}", shared)
    return text.replace("{{output_language}}", LANG_NAME.get(lang, LANG_NAME["zh-CN"]))


def prompt_status() -> list[dict]:
    out = []
    for p in sorted(PROMPT_DIR.glob("[!_]*.md")):
        out.append({"name": p.stem, "custom": (CUSTOM_PROMPT_DIR / p.name).exists()})
    return out


# ------------------------------------------------------------------ blocks

def _lines_block(tag: str, lines: list[dict]) -> str:
    body = "\n".join(
        f"[{ln['id']}]{' (' + ln['section'] + ')' if ln.get('section') and not ln.get('heading') else ''} {ln['text']}"
        for ln in lines
    )
    return f"<{tag}>\n{body or '(none)'}\n</{tag}>"


def _req_block(reqs: list[dict]) -> str:
    body = "\n".join(f"[{r['id']}] ({r['category']}, {r.get('kind', 'technical')}) {r['text']}" for r in reqs)
    return f"<requirements>\n{body}\n</requirements>"


def _guidance_block(chunks: list[dict]) -> str:
    if not chunks:
        return "<school_guidance>\n(no school guidance connected — do not cite any)\n</school_guidance>"
    body = "\n\n".join(f"[{c['id']}] {c['source']}{' › ' + c['section'] if c['section'] else ''}\n{c['text']}" for c in chunks)
    return f"<school_guidance>\n{body}\n</school_guidance>"


def _fingerprint(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update((p or "").encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:16]


# ------------------------------------------------------------------ bundle

def _validate_bundle(m: dict) -> dict:
    try:
        resume = [ln for ln in m["resume_lines"] if isinstance(ln, dict) and ln.get("id") and ln.get("text")]
        jd = [ln for ln in m["jd_lines"] if isinstance(ln, dict) and ln.get("id") and ln.get("text")]
        reqs = [r for r in m["requirements"] if isinstance(r, dict) and r.get("id") and r.get("text")]
    except (KeyError, TypeError):
        raise AppError(errors.MATERIALS_STALE, 409)
    if not resume or not jd or not reqs:
        raise AppError(errors.MATERIALS_STALE, 409)
    supplements = []
    for i, s in enumerate(m.get("supplements") or []):
        text = (s.get("text") if isinstance(s, dict) else str(s)) or ""
        if text.strip():
            supplements.append({"id": s.get("id") or f"S{i + 1}", "text": text.strip()[:1200], "section": "supplement", "heading": False})
    return {
        "resume_lines": resume,
        "jd_lines": jd,
        "requirements": reqs,
        "supplements": supplements,
        "job_title": (m.get("job_title") or "")[:120],
    }


def _facts_index(b: dict) -> dict[str, dict]:
    idx = {ln["id"]: ln for ln in b["resume_lines"]}
    idx.update({s["id"]: s for s in b["supplements"]})
    return idx


async def prepare_materials(resume_text: str, jd_text: str, job_title: str, lang: str) -> dict:
    check_materials(resume_text, jd_text)
    resume_lines = segment(resume_text, "R")
    jd_lines = segment(jd_text, "J")
    if len([l for l in resume_lines if not l["heading"]]) < 2:
        raise AppError(errors.RESUME_TOO_SHORT, 422)

    system = load_prompt("extract_requirements", lang)
    user = "\n\n".join([
        f"<job_title_hint>{job_title or '(not provided)'}</job_title_hint>",
        _lines_block("jd_lines", jd_lines),
    ])
    out = await complete_json(system, user)
    if out.get("jd_readable") is False:
        raise AppError(errors.JD_NO_REQUIREMENTS, 422)

    jd_ids = {l["id"] for l in jd_lines}
    reqs: list[dict] = []
    seen = set()
    order = {"responsibility": 0, "required": 1, "preferred": 2}
    for r in out.get("requirements") or []:
        if not isinstance(r, dict):
            continue
        text = str(r.get("text") or "").strip()
        cat = r.get("category") if r.get("category") in order else "required"
        src = [s for s in (r.get("source_ids") or []) if s in jd_ids]
        if not text or not src:
            continue  # requirement must trace back to a JD line
        key = norm(text)
        if key in seen:
            continue
        seen.add(key)
        reqs.append({
            "category": cat,
            "text": text[:200],
            "source_ids": src[:4],
            "kind": "behavioral" if r.get("kind") == "behavioral" else "technical",
        })
    if not reqs:
        raise AppError(errors.JD_NO_REQUIREMENTS, 422)
    reqs.sort(key=lambda r: order[r["category"]])
    for i, r in enumerate(reqs[:18]):
        r["id"] = f"Q{i + 1}"
    reqs = reqs[:18]

    return {
        "fingerprint": _fingerprint(resume_text, jd_text, job_title),
        "job_title": (job_title or str(out.get("job_title") or "")).strip()[:120],
        "resume_lines": resume_lines,
        "jd_lines": jd_lines,
        "requirements": reqs,
        "lang": lang,
    }


def _retrieve(query: str, k: int = 4) -> list[dict]:
    return kb.search(query, k=k)


def _guidance_out(chunks: list[dict], used: list[Any]) -> dict:
    used_set = {u for u in (used or []) if isinstance(u, str)}
    return {
        "connected": kb.status()["connected"],
        "sources": [
            {"id": c["id"], "source": c["source"], "section": c["section"], "excerpt": c["text"][:280], "used": c["id"] in used_set}
            for c in chunks
        ],
    }


# ------------------------------------------------------------------ resume optimisation

async def resume_optimize(materials: dict, lang: str) -> dict:
    b = _validate_bundle(materials)
    facts = _facts_index(b)
    req_ids = {r["id"] for r in b["requirements"]}
    guidance = _retrieve(f"resume writing bullet action verbs {b['job_title']} " + " ".join(r["text"] for r in b["requirements"][:8]))

    system = load_prompt("resume_optimize", lang)
    user = "\n\n".join([
        f"<job_title>{b['job_title'] or '(not provided)'}</job_title>",
        _req_block(b["requirements"]),
        _lines_block("resume_facts", b["resume_lines"]),
        _lines_block("student_supplements", b["supplements"]),
        _guidance_block(guidance),
    ])
    out = await complete_json(system, user)
    if not isinstance(out.get("items"), list):
        raise AppError(errors.AI_FORMAT, 502)

    items, hidden = [], 0
    used_sources = set()
    for it in out.get("items") or []:
        if not isinstance(it, dict):
            continue
        sid = it.get("source_id")
        rewrite = str(it.get("rewrite") or "").strip()
        src = facts.get(sid)
        if not src or not sid.startswith("R") or src.get("heading") or not rewrite:
            hidden += 1  # cannot be traced to a resume line -> not shown
            continue
        if sid in used_sources or norm(rewrite) == norm(src["text"]):
            continue
        ev_ids = [e for e in (it.get("evidence_ids") or []) if e in facts]
        if sid not in ev_ids:
            ev_ids.insert(0, sid)
        evidence_text = " ".join(facts[e]["text"] for e in ev_ids)
        report = grounding_report(rewrite, evidence_text)
        flagged = bool(report["unsupported_numbers"] or report["unsupported_terms"])
        used_sources.add(sid)
        items.append({
            "id": f"O{len(items) + 1}",
            "source_id": sid,
            "original": src["text"],
            "section": src.get("section", ""),
            "rewrite": rewrite[:600],
            "reason": str(it.get("reason") or "")[:500],
            "evidence_ids": ev_ids[:5],
            "requirement_ids": [q for q in (it.get("requirement_ids") or []) if q in req_ids][:4],
            "changes": [c for c in (it.get("changes") or []) if isinstance(c, str)][:5],
            "verification": {"status": "needs_review" if flagged else "grounded", **report},
        })

    missing = []
    for m in out.get("missing") or []:
        if not isinstance(m, dict) or m.get("requirement_id") not in req_ids:
            continue
        missing.append({
            "requirement_id": m["requirement_id"],
            "kind": "unclear" if m.get("kind") == "unclear" else "absent",
            "note": str(m.get("note") or "")[:400],
            "ask": str(m.get("ask") or "")[:400],
            "related_ids": [r for r in (m.get("related_ids") or []) if r in facts][:4],
        })

    return {
        "items": items,
        "missing": missing,
        "hidden_count": hidden,
        "guidance": _guidance_out(guidance, out.get("guidance_used")),
        "lang": lang,
    }


# ------------------------------------------------------------------ job matching

async def job_match(materials: dict, lang: str) -> dict:
    b = _validate_bundle(materials)
    facts = _facts_index(b)
    reqs = {r["id"]: r for r in b["requirements"]}
    guidance = _retrieve(f"skill gap learning plan {b['job_title']} " + " ".join(r["text"] for r in b["requirements"]))

    system = load_prompt("job_match", lang)
    user = "\n\n".join([
        f"<job_title>{b['job_title'] or '(not provided)'}</job_title>",
        _req_block(b["requirements"]),
        _lines_block("resume_facts", b["resume_lines"]),
        _lines_block("student_supplements", b["supplements"]),
        _guidance_block(guidance),
    ])
    out = await complete_json(system, user)
    if not isinstance(out.get("items"), list):
        raise AppError(errors.AI_FORMAT, 502)

    items: dict[str, dict] = {}
    for it in out.get("items") or []:
        if not isinstance(it, dict) or it.get("requirement_id") not in reqs or it["requirement_id"] in items:
            continue
        status = it.get("status") if it.get("status") in ("direct", "partial", "none") else "none"
        ev = [e for e in (it.get("evidence_ids") or []) if e in facts and not facts[e].get("heading")]
        downgraded = False
        if status in ("direct", "partial") and not ev:
            status, downgraded = "none", True  # claimed evidence that does not exist
        if status == "none":
            ev = []
        ns = it.get("next_step") if isinstance(it.get("next_step"), dict) else {}
        ns_type = ns.get("type") if ns.get("type") in ("clarify", "supplement", "learn", "none") else "supplement"
        if status != "direct" and ns_type == "none":
            ns_type = "supplement"
        try:
            prio = int(it.get("priority") or 3)
        except (TypeError, ValueError):
            prio = 3
        items[it["requirement_id"]] = {
            "requirement_id": it["requirement_id"],
            "status": status,
            "evidence": [{"id": e, "text": facts[e]["text"]} for e in ev[:4]],
            "rationale": str(it.get("rationale") or "")[:600],
            "next_step": {"type": ns_type, "text": str(ns.get("text") or "")[:500]},
            "priority": min(max(prio, 1), 3),
            "verification": "downgraded" if downgraded else "ok",
        }
    for rid in reqs:
        if rid not in items:
            items[rid] = {
                "requirement_id": rid, "status": "unassessed", "evidence": [], "rationale": "",
                "next_step": {"type": "none", "text": ""}, "priority": 3, "verification": "missing",
            }

    priority = [p for p in (out.get("priority_order") or []) if p in items and items[p]["status"] in ("partial", "none")][:5]
    if not priority:
        weak = [i for i in items.values() if i["status"] in ("partial", "none")]
        weak.sort(key=lambda i: (reqs[i["requirement_id"]]["category"] != "required", i["priority"]))
        priority = [i["requirement_id"] for i in weak[:5]]

    overview = str(out.get("overview") or "")
    if PROB_RE.search(overview):
        overview = ""  # never surface anything that reads like a hiring probability

    return {
        "items": [items[r] for r in reqs],
        "priority_order": priority,
        "overview": overview[:400],
        "guidance": _guidance_out(guidance, out.get("guidance_used")),
        "lang": lang,
    }


# ------------------------------------------------------------------ mock interview

async def interview_question(materials: dict, lang: str, asked: list[dict], target_requirement: str | None) -> dict:
    b = _validate_bundle(materials)
    facts = _facts_index(b)
    reqs = {r["id"]: r for r in b["requirements"]}
    asked_txt = json.dumps([
        {"question": str(a.get("question", ""))[:300], "requirement_id": str(a.get("requirement_id", ""))[:32],
         "answer": str(a.get("answer", ""))[:600], "feedback": str(a.get("feedback", ""))[:240]}
        for a in (asked or [])[-8:]
    ], ensure_ascii=False)
    target = target_requirement if target_requirement in reqs else ""
    guidance = _retrieve(f"interview question {b['job_title']} " + (reqs[target]["text"] if target else ""), k=3)

    system = load_prompt("interview_question", lang)
    user = "\n\n".join([
        f"<job_title>{b['job_title'] or '(not provided)'}</job_title>",
        _req_block(b["requirements"]),
        _lines_block("resume_facts", b["resume_lines"]),
        _lines_block("student_supplements", b["supplements"]),
        f"<asked_questions>\n{asked_txt or '(none yet)'}\n</asked_questions>",
        f"<target_requirement>{target or '(choose one)'}</target_requirement>",
        _guidance_block(guidance),
    ])
    out = await complete_json(system, user)
    q = str(out.get("question") or "").strip()
    if not q:
        raise AppError(errors.AI_FORMAT, 502)
    rid = out.get("requirement_id") if out.get("requirement_id") in reqs else (target or next(iter(reqs)))
    qtype = out.get("type") if out.get("type") in ("behavioral", "technical") else reqs[rid].get("kind", "technical")
    return {
        "question": q[:600],
        "type": qtype,
        "requirement_id": rid,
        "resume_refs": [{"id": r, "text": facts[r]["text"]} for r in (out.get("resume_ids") or []) if r in facts][:3],
        "focus": str(out.get("focus") or "")[:80],
        "guidance": _guidance_out(guidance, []),
        "lang": lang,
    }


async def interview_feedback(materials: dict, lang: str, question: dict, answer: str, history: list[dict]) -> dict:
    b = _validate_bundle(materials)
    facts = _facts_index(b)
    reqs = {r["id"]: r for r in b["requirements"]}
    answer = (answer or "").strip()
    if len(norm(answer)) < 4:
        raise AppError(errors.BAD_REQUEST, 422, "answer too short")
    rid = question.get("requirement_id") if question.get("requirement_id") in reqs else ""
    qtype = question.get("type") if question.get("type") in ("behavioral", "technical") else "technical"
    refs = [facts[r["id"]] for r in (question.get("resume_refs") or []) if isinstance(r, dict) and r.get("id") in facts]
    guidance = _retrieve(("STAR behavioral answer " if qtype == "behavioral" else "technical interview reasoning ") + (reqs[rid]["text"] if rid else ""), k=3)
    prev = "\n".join(
        f"Q: {str(h.get('question', ''))[:300]}\nA: {str(h.get('answer', ''))[:800]}" for h in (history or [])[-3:]
    )

    system = load_prompt("interview_feedback", lang)
    user = "\n\n".join([
        f"<requirement>{('[' + rid + '] ' + reqs[rid]['text']) if rid else '(general)'}</requirement>",
        f"<question type=\"{qtype}\">{str(question.get('question', ''))[:600]}</question>",
        _lines_block("related_resume_lines", refs),
        f"<earlier_turns_on_this_question>\n{prev or '(none)'}\n</earlier_turns_on_this_question>",
        f"<answer>\n{answer[:4000]}\n</answer>",
        _guidance_block(guidance),
    ])
    out = await complete_json(system, user)
    if not isinstance(out.get("action"), str):
        raise AppError(errors.AI_FORMAT, 502)

    on_topic, dropped = [], 0
    for o in out.get("on_topic") or []:
        if isinstance(o, dict) and quote_in_text(str(o.get("quote", "")), answer):
            on_topic.append({"quote": str(o["quote"])[:300], "why": str(o.get("why") or "")[:300]})
        else:
            dropped += 1  # quote not found in the actual answer -> not shown
    st = out.get("structure") if isinstance(out.get("structure"), dict) else {}
    structure = None
    if qtype == "behavioral":
        structure = {k: bool(st.get(k)) if st.get(k) is not None else False for k in ("situation", "task", "action", "result")}
    fu = out.get("follow_up") if isinstance(out.get("follow_up"), dict) else {}
    follow = {"needed": bool(fu.get("needed")) and bool(str(fu.get("question") or "").strip()),
              "question": str(fu.get("question") or "")[:400], "reason": str(fu.get("reason") or "")[:300]}
    return {
        "on_topic": on_topic[:4],
        "missing": [str(x)[:300] for x in (out.get("missing") or []) if str(x).strip()][:4],
        "action": str(out.get("action") or "")[:400],
        "structure": structure,
        "reasoning_note": str(out.get("reasoning_note") or "")[:400] if qtype == "technical" else "",
        "follow_up": follow,
        "unverified_quotes_removed": dropped,
        "guidance": _guidance_out(guidance, []),
        "lang": lang,
    }


async def interview_summary(lang: str, turns: list[dict]) -> dict:
    if not turns:
        raise AppError(errors.BAD_REQUEST, 422, "no turns")
    session = []
    for i, t in enumerate(turns[:20], 1):
        fb = t.get("feedback") or {}
        session.append(json.dumps({
            "turn": i,
            "question": str(t.get("question", ""))[:400],
            "answer": str(t.get("answer", ""))[:1500],
            "missing": fb.get("missing", [])[:4],
            "action": fb.get("action", ""),
        }, ensure_ascii=False))
    system = load_prompt("interview_summary", lang)
    out = await complete_json(system, "<session>\n" + "\n".join(session) + "\n</session>")
    if not isinstance(out.get("priorities"), list):
        raise AppError(errors.AI_FORMAT, 502)
    n = len(turns)

    def clean(lst):
        res = []
        for x in lst or []:
            if isinstance(x, dict) and str(x.get("text", "")).strip():
                try:
                    turn = int(x.get("turn") or 0)
                except (TypeError, ValueError):
                    turn = 0
                res.append({"text": str(x["text"])[:400], "turn": turn if 1 <= turn <= n else None})
        return res

    return {
        "strengths": clean(out.get("strengths"))[:4],
        "priorities": clean(out.get("priorities"))[:3],
        "next_session": str(out.get("next_session") or "")[:300],
        "lang": lang,
    }
