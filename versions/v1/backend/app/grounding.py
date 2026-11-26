"""Grounding checks applied to every model output before it reaches the UI.

The checks are conservative heuristics, not proof of correctness:
- numbers / quantities in a rewrite must appear in its cited evidence
- tool or technology names must appear in the cited evidence
- cited source ids must exist
- quotes from an interview answer must actually occur in that answer
"""
from __future__ import annotations

import re
import unicodedata

NUM_RE = re.compile(r"\d+(?:[.,]\d+)?\s*[%％kKwW万千百+]?")
CN_QTY_RE = re.compile(r"[一二两三四五六七八九十百千万]+\s*(?:名|个|人|位|年|月|项|次|倍|家|支|场|周|天|成)")
CN_NUM = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
LATIN_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#./\-]*[A-Za-z0-9+#]|[A-Za-z]")
CJK_RE = re.compile(r"[\u3400-\u9fff]")

TECH_TERMS = {
    "python", "java", "javascript", "typescript", "sql", "mysql", "postgresql", "mongodb", "excel", "vba",
    "tableau", "powerbi", "power", "figma", "sketch", "axure", "jira", "confluence", "notion", "spss", "stata",
    "matlab", "r", "react", "vue", "angular", "node", "django", "flask", "fastapi", "spring", "docker",
    "kubernetes", "aws", "azure", "gcp", "linux", "git", "github", "pandas", "numpy", "tensorflow", "pytorch",
    "scikit-learn", "sklearn", "spark", "hadoop", "hive", "kafka", "redis", "c", "c++", "c#", "go", "rust",
    "swift", "kotlin", "php", "html", "css", "photoshop", "illustrator", "premiere", "salesforce", "sap",
    "hubspot", "ga", "ga4", "seo", "sem", "llm", "gpt", "chatgpt", "langchain", "airflow", "dbt", "snowflake",
    "bigquery", "looker", "canva", "xd", "a/b", "scrum", "agile", "okr", "kpi", "crm", "erp", "api",
}
COMMON_WORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "by", "at", "as", "from", "via",
    "i", "we", "my", "our", "is", "are", "was", "were", "be", "been",
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").lower()
    return re.sub(r"[\s\u3000,，.。;；:：!！?？'\"“”‘’()（）\[\]【】\-–—_/·•]+", "", s)


def _numbers(text: str) -> set[str]:
    t = unicodedata.normalize("NFKC", text or "")
    vals = {re.sub(r"[\s,]", "", m.group(0)).rstrip("+").lower() for m in NUM_RE.finditer(t)}
    return {v for v in vals if v}


def _cn_quantities(text: str) -> set[str]:
    return {re.sub(r"\s", "", m.group(0)) for m in CN_QTY_RE.finditer(text or "")}


def unsupported_cn_quantities(rewrite: str, evidence: str) -> list[str]:
    ev = _cn_quantities(evidence)
    ev_digits = _numbers(evidence)
    out = []
    for q in _cn_quantities(rewrite):
        if q in ev:
            continue
        head = CN_NUM.get(q[0])
        if head is not None and len(q) == 2 and str(head) in ev_digits:
            continue
        out.append(q)
    return out


def unsupported_numbers(rewrite: str, evidence: str) -> list[str]:
    ev = _numbers(evidence)
    ev_plain = {re.sub(r"[^0-9.]", "", v) for v in ev}
    bad = []
    for v in _numbers(rewrite):
        core = re.sub(r"[^0-9.]", "", v)
        if v in ev or (core and core in ev_plain):
            continue
        bad.append(v)
    return bad


def _tool_like(tok: str, in_cjk_context: bool) -> bool:
    low = tok.lower()
    if low in COMMON_WORDS:
        return False
    if low in TECH_TERMS:
        return True
    if any(ch.isdigit() for ch in tok) or any(ch in "+#" for ch in tok):
        return True
    if len(tok) >= 2 and sum(ch.isupper() for ch in tok[1:]) >= 1:  # SQL, PowerBI, iOS
        return True
    # in Chinese text, any Latin word is very likely a tool / proper noun
    return in_cjk_context and len(tok) >= 2


def unsupported_terms(rewrite: str, evidence: str) -> list[str]:
    in_cjk = bool(CJK_RE.search(rewrite or ""))
    ev_low = unicodedata.normalize("NFKC", evidence or "").lower()
    bad = []
    for m in LATIN_TOKEN_RE.finditer(unicodedata.normalize("NFKC", rewrite or "")):
        tok = m.group(0).strip(".-/")
        if not tok or not _tool_like(tok, in_cjk):
            continue
        if tok.lower() not in ev_low and tok not in bad:
            bad.append(tok)
    return bad


def quote_in_text(quote: str, text: str) -> bool:
    q = norm(quote)
    if len(q) < 2:
        return False
    return q in norm(text)


def grounding_report(rewrite: str, evidence_text: str) -> dict:
    nums = unsupported_numbers(rewrite, evidence_text)
    terms = unsupported_terms(rewrite, evidence_text) + unsupported_cn_quantities(rewrite, evidence_text)
    return {"unsupported_numbers": nums, "unsupported_terms": terms}
