"""School guidance knowledge base (RAG).

Guidance files (.md / .txt / .pdf) are stored in KB_DIR, chunked, and indexed
with a lightweight BM25 retriever that handles both English words and CJK
character bigrams. Guidance is kept strictly separate from student facts: it is
passed to the model in its own block and returned to the UI as "guidance
sources", never as resume evidence.

When KB_DIR is empty, retrieval returns nothing and the UI shows that no
knowledge base is connected. No sources are fabricated.

To swap in a vector store later, implement `search()` with the same return
shape.
"""
from __future__ import annotations

import math
import re
import threading
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from . import errors
from .config import KB_DIR
from .errors import AppError
from .materials import normalize_text, pdf_to_text

ALLOWED = {".md", ".txt", ".pdf"}
CJK_RE = re.compile(r"[\u3400-\u9fff]+")
WORD_RE = re.compile(r"[a-z0-9][a-z0-9+#.\-]*")
STOP = {"the", "and", "of", "to", "a", "in", "for", "is", "on", "with", "as", "be", "or", "an", "are", "by", "it", "that", "this"}


def tokenize(text: str) -> list[str]:
    t = text.lower()
    toks = [w for w in WORD_RE.findall(t) if w not in STOP and len(w) > 1]
    for run in CJK_RE.findall(t):
        if len(run) == 1:
            toks.append(run)
        toks.extend(run[i : i + 2] for i in range(len(run) - 1))
    return toks


@dataclass
class Chunk:
    source: str
    index: int
    heading: str
    text: str
    tokens: Counter
    length: int


class KnowledgeBase:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._chunks: list[Chunk] = []
        self._df: Counter = Counter()
        self._avg = 1.0
        self.reload()

    # ---- indexing
    def _read(self, path: Path) -> str:
        if path.suffix.lower() == ".pdf":
            return pdf_to_text(path.read_bytes())["text"]
        return normalize_text(path.read_text(encoding="utf-8", errors="ignore"))

    def _chunk(self, source: str, text: str) -> list[Chunk]:
        out: list[Chunk] = []
        heading = ""
        buf: list[str] = []

        def flush():
            body = "\n".join(buf).strip()
            if len(body) >= 20:
                toks = Counter(tokenize(heading + " " + body))
                out.append(Chunk(source, len(out) + 1, heading, body, toks, sum(toks.values()) or 1))
            buf.clear()

        for line in text.split("\n"):
            if re.match(r"^\s*#{1,4}\s+", line):
                flush()
                heading = re.sub(r"^\s*#+\s*", "", line).strip()
                continue
            buf.append(line)
            if sum(len(x) for x in buf) > 700:
                flush()
        flush()
        return out

    def reload(self) -> None:
        chunks: list[Chunk] = []
        for p in sorted(self.root.iterdir()):
            if p.is_file() and p.suffix.lower() in ALLOWED and not p.name.startswith("."):
                try:
                    chunks.extend(self._chunk(p.name, self._read(p)))
                except Exception:
                    continue
        df: Counter = Counter()
        for c in chunks:
            df.update(set(c.tokens))
        with self._lock:
            self._chunks = chunks
            self._df = df
            self._avg = (sum(c.length for c in chunks) / len(chunks)) if chunks else 1.0

    # ---- management
    def status(self) -> dict:
        files = {}
        for c in self._chunks:
            files[c.source] = files.get(c.source, 0) + 1
        return {
            "connected": bool(self._chunks),
            "files": [{"name": k, "chunks": v} for k, v in files.items()],
            "chunks": len(self._chunks),
        }

    def add(self, filename: str, data: bytes) -> dict:
        name = Path(filename or "").name
        suffix = Path(name).suffix.lower()
        if suffix not in ALLOWED:
            raise AppError(errors.KB_FILE_TYPE, 415)
        safe = re.sub(r"[^\w.\-\u3400-\u9fff]+", "_", name)[:120]
        target = self.root / safe
        target.write_bytes(data)
        try:
            text = self._read(target)
        except AppError:
            target.unlink(missing_ok=True)
            raise
        if len(text.strip()) < 20:
            target.unlink(missing_ok=True)
            raise AppError(errors.KB_EMPTY_FILE, 422)
        self.reload()
        return self.status()

    def remove(self, name: str) -> dict:
        target = self.root / Path(name).name
        if target.exists() and target.is_file():
            target.unlink()
        self.reload()
        return self.status()

    # ---- retrieval
    def search(self, query: str, k: int = 4) -> list[dict]:
        with self._lock:
            chunks, df, avg = self._chunks, self._df, self._avg
        if not chunks:
            return []
        q = Counter(tokenize(query))
        if not q:
            return []
        N = len(chunks)
        k1, b = 1.4, 0.75
        scored = []
        for c in chunks:
            s = 0.0
            for term in q:
                tf = c.tokens.get(term, 0)
                if not tf:
                    continue
                idf = math.log(1 + (N - df[term] + 0.5) / (df[term] + 0.5))
                s += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * c.length / avg))
            if s > 0:
                scored.append((s, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "id": f"G{i + 1}",
                "source": c.source,
                "section": c.heading,
                "chunk": c.index,
                "text": c.text[:900],
                "score": round(s, 3),
            }
            for i, (s, c) in enumerate(scored[:k])
        ]


kb = KnowledgeBase(KB_DIR)
