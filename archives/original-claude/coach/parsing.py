import hashlib
import re
from io import BytesIO
from pypdf import PdfReader
from coach.errors import CoachError
from coach.models import Source

MAX_TEXT = 24000


def clean(text: str) -> str:
    return text.replace("\x00", "").replace("\r\n", "\n").strip()


def validate_text(text: str, label: str) -> str:
    text = clean(text)
    if len(re.sub(r"\s", "", text)) < 30:
        raise CoachError(f"{label}内容不足，请提供至少 30 个非空白字符的真实经历或岗位要求。")
    if len(text) > MAX_TEXT:
        raise CoachError(f"{label}超过 {MAX_TEXT:,} 字符，请精简后重试；系统不会静默截断材料。")
    return text


def pdf_text(data: bytes) -> str:
    if len(data) > 10 * 1024 * 1024:
        raise CoachError("PDF 超过 10 MB，请压缩或粘贴简历正文。")
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise CoachError("PDF 已加密，请上传未加密版本或粘贴文字。")
        if len(reader.pages) > 20:
            raise CoachError("简历 PDF 最多支持 20 页，请精简材料。")
        text = clean("\n\n".join(page.extract_text() or "" for page in reader.pages))
    except CoachError:
        raise
    except Exception:
        raise CoachError("无法读取此 PDF。请检查文件是否损坏，或改用粘贴文字。") from None
    if len(re.sub(r"\s", "", text)) < 30:
        raise CoachError("PDF 未提取到足够文字，可能是扫描件。此版本不含 OCR，请粘贴识别后的正文。")
    return validate_text(text, "PDF 简历")


def sources(text: str, prefix: str) -> list[Source]:
    # Deterministic IDs and exact text; no semantic inference happens here.
    parts = [p.strip() for p in clean(text).splitlines() if p.strip()]
    chunks = [p[i:i + 1200] for p in parts for i in range(0, len(p), 1200)]
    if len(chunks) > 160:
        raise CoachError("材料分段过多，请整理为较完整的经历段落或岗位条目后重试。")
    return [Source(id=f"{prefix}{i:03}", text=p) for i, p in enumerate(chunks, 1)]


def fingerprint(resume: str, jd: str, config_signature: str = "") -> str:
    return hashlib.sha256((resume + "\0" + jd + "\0" + config_signature).encode()).hexdigest()
