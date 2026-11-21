"""Material intake: PDF text extraction, job-posting URL import, and
segmentation of resume / JD text into addressable source lines.

Segmentation is deterministic so every downstream claim can be traced to an
exact source line id (R3, J7, S1 ...).
"""
from __future__ import annotations

import io
import re

from pypdf import PdfReader

from . import errors
from .config import MAX_TEXT_CHARS, MAX_UPLOAD_BYTES
from .errors import AppError

BULLET_RE = re.compile(r"^\s*(?:[•●○◦▪▫■□♦◆‣⁃∙·\-–—*]|\d{1,2}[.)、]|[a-zA-Z][.)]|[（(]\d{1,2}[)）])\s*")
SENT_END = tuple("。．.！!？?；;：:")
CJK_RE = re.compile(r"[\u3400-\u9fff]")


# ---------------------------------------------------------------- PDF

def pdf_to_text(data: bytes) -> dict:
    if len(data) > MAX_UPLOAD_BYTES:
        raise AppError(errors.FILE_TOO_LARGE, 413)
    if not data.startswith(b"%PDF"):
        raise AppError(errors.PDF_UNREADABLE, 422)
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                raise AppError(errors.PDF_UNREADABLE, 422, "encrypted")
        pages = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                pages.append("")
    except AppError:
        raise
    except Exception:
        raise AppError(errors.PDF_UNREADABLE, 422)
    text = "\n".join(pages)
    text = normalize_text(text)
    meaningful = re.sub(r"\s+", "", text)
    if len(meaningful) < 30:
        # pages exist but nothing extractable -> most likely a scanned image PDF
        raise AppError(errors.PDF_NO_TEXT, 422)
    if len(text) > MAX_TEXT_CHARS:
        raise AppError('CONTEXT_LIMIT', 422)
    return {"text": text[:MAX_TEXT_CHARS], "pages": len(pages), "truncated": len(text) > MAX_TEXT_CHARS}


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    # PDF fonts often map bullet glyphs to control or private-use code points
    text = re.sub(r"[\x7f\uf0b7\uf0a7\uf076\uf0d8\uf0fc\u25aa\u25cf]", "•", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ue000-\uf8ff]", "", text)
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------- URL import

from .job_import import fetch_job_posting


# ---------------------------------------------------------------- segmentation

def _is_heading(line: str) -> bool:
    s = line.strip()
    if not s or BULLET_RE.match(s):
        return False
    if len(s) <= 24 and not s.endswith(SENT_END[:6]):
        if s.isupper() or CJK_RE.search(s) or len(s.split()) <= 4:
            return True
    return False


def segment(text: str, prefix: str) -> list[dict]:
    """Split text into source lines. Wrapped PDF lines are re-joined; bullets
    and headings start new segments. Long paragraphs are split on sentence
    boundaries so each segment stays quotable."""
    raw_lines = [ln.strip() for ln in normalize_text(text).split("\n")]
    blocks: list[dict] = []
    section = ""
    for ln in raw_lines:
        if not ln:
            if blocks:
                blocks[-1]["closed"] = True
            continue
        if _is_heading(ln):
            section = ln.rstrip(":：")
            blocks.append({"text": ln, "section": section, "heading": True, "closed": True})
            continue
        is_bullet = bool(BULLET_RE.match(ln))
        clean = BULLET_RE.sub("", ln).strip() if is_bullet else ln
        prev = blocks[-1] if blocks else None
        prev_text = prev["text"] if prev else ""
        continues = (
            clean[:1].islower()
            or bool(re.search(r"(?:[,，、&/(\-–]|\b(?:and|or|with|of|to|the|for|in|on|a|an|by|using))$", prev_text, re.I))
            or (bool(CJK_RE.match(clean[:1] or "")) and bool(CJK_RE.search(prev_text[-1:])) and len(prev_text) > 20)
        )
        can_join = (
            prev is not None
            and not prev.get("heading")
            and not prev.get("closed")
            and not is_bullet
            and not prev_text.endswith(SENT_END)
            and not prev_text.endswith((")", "）"))
            and continues
        )
        if can_join:
            sep = "" if CJK_RE.search(prev["text"][-1:]) and CJK_RE.match(clean[:1]) else " "
            prev["text"] = prev["text"] + sep + clean
        else:
            blocks.append({"text": clean, "section": section, "heading": False, "closed": False})

    out: list[dict] = []
    n = 0
    for b in blocks:
        pieces = [b["text"]]
        if not b["heading"] and len(b["text"]) > 260:
            pieces = [p.strip() for p in re.split(r"(?<=[。！？!?；;])\s*|(?<=\.)\s+(?=[A-Z])", b["text"]) if p and p.strip()]
        for p in pieces:
            if len(re.sub(r"\s+", "", p)) < 2:
                continue
            n += 1
            out.append({"id": f"{prefix}{n}", "text": p, "section": b["section"], "heading": b["heading"]})
    return out


def check_materials(resume_text: str, jd_text: str) -> None:
    r = re.sub(r"\s+", "", resume_text or "")
    j = re.sub(r"\s+", "", jd_text or "")
    if not r:
        raise AppError(errors.RESUME_EMPTY, 422)
    if not j:
        raise AppError(errors.JD_EMPTY, 422)
    if len(r) < 60:
        raise AppError(errors.RESUME_TOO_SHORT, 422)
    if len(j) < 40:
        raise AppError(errors.JD_TOO_SHORT, 422)
