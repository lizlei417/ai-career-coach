"""CityUHK guidance retrieval over the versioned RAG_v1 corpus (no external services).

The corpus ships in data/rag_v1 and is loaded once at import, so a restart or a
fresh Render image never needs a manual upload. Every chunk's text is checked
against its recorded SHA-256; a chunk that fails is excluded and counted.

Retrieval is lexical BM25 within the chunks tagged for the current task. The
corpus is English while resumes and JDs are often Chinese, so the query side is
expanded with a small fixed glossary. Nothing here calls a model, so retrieval
never touches the account's model-call quota.

Chunks are reference data only. coach.py passes them in rag_chunks together
with their evidence_type; the M3 prompt limits what each type may support.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import threading
import time
from collections import Counter
from pathlib import Path

from .config import RAG_DIR

log = logging.getLogger("coach.rag")

FUNCTIONS = ("resume_optimization", "job_matching", "mock_interview")
CJK_RE = re.compile(r"[㐀-鿿]+")
WORD_RE = re.compile(r"[a-z0-9][a-z0-9+#.\-]*")
STOP = {"the", "and", "of", "to", "a", "in", "for", "is", "on", "with", "as", "be", "or", "an", "are", "by",
        "it", "that", "this", "link", "opens", "new", "window", "your", "you", "will", "can", "how", "what"}

# Task intent that is always part of the query, so retrieval stays on-topic even
# when the student's materials share no English vocabulary with the corpus.
INTENT = {
    "resume_optimization": "resume cv writing tips sample resumes",
    "job_matching": "career skills competencies industry occupations consultation",
    "mock_interview": "interview prepare job description practice star behavioral feedback",
}
# Chinese (simplified and traditional) phrases mapped to the corpus vocabulary.
GLOSSARY = {
    "简历": "resume cv", "履歷": "resume cv", "履历": "resume cv", "簡歷": "resume cv",
    "求职信": "application letter", "求職信": "application letter", "个人陈述": "personal statement",
    "個人陳述": "personal statement", "面试": "interview", "面試": "interview", "演示": "presentation",
    "汇报": "presentation", "匯報": "presentation", "行业": "industry", "行業": "industry",
    "技能": "skills competencies", "能力": "skills competencies", "职业": "career", "職業": "career",
    "薪酬": "salary", "薪資": "salary", "实习": "internship", "實習": "internship",
    "咨询": "consultation advising", "諮詢": "consultation advising", "行为": "behavioral",
    "行為": "behavioral", "同伴": "peers feedback", "反馈": "feedback", "回饋": "feedback",
    "职责": "job description", "職責": "job description", "岗位": "job", "職位": "job", "崗位": "job",
}
GOAL_TERMS = {"internship": "internship guidance", "job": "job search job application"}


def tokenize(text: str) -> list[str]:
    t = (text or "").lower()
    toks = [w.strip(".-") for w in WORD_RE.findall(t)]
    toks = [w for w in toks if w and w not in STOP and len(w) > 1]
    for run in CJK_RE.findall(t):
        toks.extend(run[i:i + 2] for i in range(len(run) - 1))
    return toks


def expand(text: str) -> str:
    extra = [v for k, v in GLOSSARY.items() if k in (text or "")]
    return (text or "") + " " + " ".join(extra)


class GuidanceIndex:
    def __init__(self, root: Path):
        self.root = root
        self._lock = threading.Lock()
        self.chunks: list[dict] = []
        self.sources: dict[str, dict] = {}
        self.rejected = 0
        self.error = ""
        self.version = ""
        self.loaded_at = 0.0
        self.retrieval_ready = False
        self.load()

    def load(self) -> None:
        chunks, rejected, error, version = [], 0, "", ""
        sources: dict[str, dict] = {}
        try:
            from bs4 import BeautifulSoup
            from urllib.parse import urlsplit
            raw = (self.root / "chunks.jsonl").read_bytes()
            version = hashlib.sha256(raw).hexdigest()[:12]
            manifests = json.loads((self.root / "sources.json").read_text(encoding="utf-8"))
            snapshots = {}
            for source in manifests:
                sid = source["id"]
                path = (self.root / source["raw"]).resolve()
                if sid in sources or not path.is_relative_to(self.root.resolve()):
                    raise ValueError("duplicate or invalid source")
                content = path.read_bytes()
                if (hashlib.sha256(content).hexdigest() != source["raw_sha256"]
                        or not (urlsplit(source["url"]).hostname or "").endswith(".cityu.edu.hk")):
                    raise ValueError("source integrity")
                sources[sid] = source
                snapshots[sid] = BeautifulSoup(content, "html.parser")
            seen = set()
            for line in raw.decode("utf-8").splitlines():
                if not line.strip():
                    continue
                c = json.loads(line)
                text = str(c.get("text") or "")
                source = sources.get(c.get("source_id"), {})
                anchor = urlsplit(c.get("source_url", "")).fragment
                soup = snapshots.get(c.get("source_id"))
                node = soup.find(id=anchor) if soup is not None and anchor else soup
                ok = (c.get("function") in FUNCTIONS and c.get("chunk_id") not in seen
                      and c.get("chunk_id") and text and source and node is not None
                      and c.get("evidence_type") in ("resource_listing_only", "library_context", "historical_workshop_report")
                      and hashlib.sha256(text.encode("utf-8")).hexdigest() == c.get("text_sha256")
                      and c.get("raw_sha256") == source.get("raw_sha256")
                      and c.get("source_url", "").split("#")[0] == source.get("url")
                      and text in " ".join(node.get_text(" ", strip=True).split()))
                if not ok:
                    rejected += 1
                    continue
                seen.add(c["chunk_id"])
                toks = Counter(tokenize(f"{c.get('section', '')} {text}"))
                chunks.append({**c, "_tokens": toks, "_len": sum(toks.values()) or 1})
            counts = Counter(c["source_id"] for c in chunks)
            if rejected or any(counts[sid] != source["chunk_count"] for sid, source in sources.items()):
                raise ValueError("chunk completeness")
            if set(c["function"] for c in chunks) != set(FUNCTIONS):
                raise ValueError("missing task")
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            error = type(exc).__name__
            chunks = []
        with self._lock:
            self.chunks, self.sources, self.rejected = chunks, sources, rejected
            self.error, self.version, self.loaded_at = error, version, time.time()
        self.retrieval_ready = bool(chunks) and not error and all(self.search(f, INTENT[f], 1) for f in FUNCTIONS)
        log.info("rag loaded version=%s chunks=%s rejected=%s error=%s", version, len(chunks), rejected, error or "-")

    def status(self) -> dict:
        per = Counter(c["function"] for c in self.chunks)
        files = [{"name": s.get("title", sid), "chunks": sum(1 for c in self.chunks if c["source_id"] == sid)}
                 for sid, s in self.sources.items()]
        return {
            "connected": self.retrieval_ready,
            "integrity": not self.error and bool(self.chunks),
            "indexed": bool(self.chunks),
            "version": "RAG_v1 " + self.version if self.version else "",
            "chunks": len(self.chunks),
            "rejected": self.rejected,
            "by_function": {f: per.get(f, 0) for f in FUNCTIONS},
            "files": files,
            "error": self.error,
        }

    def search(self, function: str, query: str, k: int = 3) -> list[dict]:
        started = time.perf_counter()
        with self._lock:
            pool = [c for c in self.chunks if c["function"] == function] if function in FUNCTIONS else list(self.chunks)
        q = Counter(tokenize(expand(query)))
        hits: list[tuple[float, dict]] = []
        if pool and q:
            n = len(pool)
            df = Counter(t for c in pool for t in set(c["_tokens"]))
            avg = sum(c["_len"] for c in pool) / n
            for c in pool:
                s = 0.0
                for term in q:
                    tf = c["_tokens"].get(term, 0)
                    if tf:
                        idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
                        s += idf * tf * 2.4 / (tf + 1.4 * (0.25 + 0.75 * c["_len"] / avg))
                if s > 0:
                    hits.append((s, c))
        hits.sort(key=lambda x: (-x[0], x[1]["chunk_id"]))
        out = [{
            "chunk_id": c["chunk_id"],
            "evidence_type": c["evidence_type"],
            "section": c.get("section", ""),
            "text": c["text"],
            "page_title": c.get("page_title", ""),
            "source_url": c.get("source_url", ""),
            "listed_resource_url": c.get("listed_resource_url", ""),
            "score": round(s, 3),
        } for s, c in hits[:k]]
        # Ids and scores only: queries contain resume/JD text and are never logged.
        log.info("rag search function=%s hits=%s ms=%.1f", function, [(h["chunk_id"], h["score"]) for h in out],
                 (time.perf_counter() - started) * 1000)
        return out


def build_query(task: str, job_goal: str, resume_text: str, jd_text: str, extra: str = "") -> str:
    # The JD and current question carry the topic; the resume is truncated so it
    # cannot drown the task intent.
    return " ".join([INTENT.get(task, ""), GOAL_TERMS.get(job_goal, ""), extra, jd_text[:4000], resume_text[:1500]])


index = GuidanceIndex(RAG_DIR)
