"""Local lexical retrieval. Guides never become evidence of candidate history."""
import hashlib
import math
import re
from collections import Counter
from pathlib import Path
from coach.models import Guide
from coach.parsing import pdf_text


def tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z][a-z0-9+#.]{1,}|[\u4e00-\u9fff]+", text.lower())
    return [part for w in words for part in
            ([w[i:i+2] for i in range(len(w)-1)] if re.fullmatch(r"[\u4e00-\u9fff]+", w) else [w])]


class KnowledgeBase:
    def __init__(self, directory: Path):
        self.guides: list[Guide] = []
        self.warnings: list[str] = []
        if not directory.exists():
            return
        paths = sorted(p for p in directory.rglob("*") if p.suffix.lower() in {".pdf", ".txt", ".md"}
                       and p.name != "README.md" and not p.is_symlink())
        if len(paths) > 100:
            self.warnings.append("知识库最多加载 100 个文件，其余文件未载入。")
        for path in paths[:100]:
            try:
                if path.stat().st_size > 10 * 1024 * 1024:
                    raise ValueError
                data = path.read_bytes()
                text = pdf_text(data) if path.suffix.lower() == ".pdf" else data.decode("utf-8-sig")
                if len(text) > 100000:
                    raise ValueError
                name = str(path.relative_to(directory))
                for i, start in enumerate(range(0, len(text), 900)):
                    chunk = text[max(0, start-100):start+900].strip()
                    if chunk:
                        key = hashlib.sha256((name + str(i) + chunk).encode()).hexdigest()[:12]
                        self.guides.append(Guide(id=f"G-{key}", filename=name, text=chunk))
            except Exception:
                self.warnings.append(f"无法读取知识文件：{path.name}（请检查格式、编码或大小）。")

    def retrieve(self, query: str, limit: int = 4) -> list[Guide]:
        query_terms = set(tokens(query))
        if not self.guides or not query_terms:
            return []
        counts = [Counter(tokens(g.text)) for g in self.guides]
        df = Counter(t for c in counts for t in c)
        avg = sum(sum(c.values()) for c in counts) / len(counts) or 1
        scored = []
        for guide, count in zip(self.guides, counts):
            length = sum(count.values())
            score = sum(math.log(1+(len(counts)-df[t]+.5)/(df[t]+.5)) *
                        (count[t]*2.2)/(count[t]+1.2*(.25+.75*length/avg))
                        for t in query_terms if count[t])
            if score > 0:
                scored.append((score, guide))
        return [g for _, g in sorted(scored, key=lambda pair: pair[0], reverse=True)[:limit]]
