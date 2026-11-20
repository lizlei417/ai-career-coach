"""Application errors with stable codes. The frontend maps codes to localized
messages, so raw technical details are never shown to the student."""
from __future__ import annotations


class AppError(Exception):
    def __init__(self, code: str, status: int = 400, detail: str = ""):
        super().__init__(code)
        self.code = code
        self.status = status
        # `detail` is a short, non-sensitive hint (never resume text or keys)
        self.detail = detail[:200]


# Codes used across the API
RESUME_EMPTY = "RESUME_EMPTY"
RESUME_TOO_SHORT = "RESUME_TOO_SHORT"
JD_EMPTY = "JD_EMPTY"
JD_TOO_SHORT = "JD_TOO_SHORT"
JD_NO_REQUIREMENTS = "JD_NO_REQUIREMENTS"
PDF_UNREADABLE = "PDF_UNREADABLE"
PDF_NO_TEXT = "PDF_NO_TEXT"
FILE_TOO_LARGE = "FILE_TOO_LARGE"
FILE_TYPE = "FILE_TYPE"
URL_INVALID = "URL_INVALID"
URL_FETCH_FAILED = "URL_FETCH_FAILED"
URL_NO_CONTENT = "URL_NO_CONTENT"
LLM_NOT_CONFIGURED = "LLM_NOT_CONFIGURED"
LLM_AUTH = "LLM_AUTH"
LLM_TIMEOUT = "LLM_TIMEOUT"
LLM_RATE_LIMIT = "LLM_RATE_LIMIT"
LLM_FAILED = "LLM_FAILED"
AI_FORMAT = "AI_FORMAT"
MATERIALS_STALE = "MATERIALS_STALE"
KB_FILE_TYPE = "KB_FILE_TYPE"
KB_EMPTY_FILE = "KB_EMPTY_FILE"
RUNTIME_CONFIG_DISABLED = "RUNTIME_CONFIG_DISABLED"
BAD_REQUEST = "BAD_REQUEST"
