"""Runtime configuration.

LLM settings come from environment variables (.env) and can be overridden at
runtime from the Settings panel. Overrides live in process memory only; the API
key is never logged or returned to the client.
"""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

KB_DIR = Path(os.getenv("KB_DIR", BASE_DIR / "data" / "kb"))
PROMPT_DIR = BASE_DIR / "prompts"
CUSTOM_PROMPT_DIR = PROMPT_DIR / "custom"
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", BASE_DIR.parent / "frontend" / "dist"))

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_TEXT_CHARS = 30000


@dataclass
class LLMSettings:
    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai").strip().lower())
    api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", "").strip())
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini").strip())
    base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", "").strip())
    timeout: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT", "90")))
    temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.2")))

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)

    def effective_base_url(self) -> str:
        if self.base_url:
            return self.base_url.rstrip("/")
        if self.provider == "anthropic":
            return "https://api.anthropic.com"
        return "https://api.openai.com/v1"

    def public(self) -> dict:
        key = self.api_key
        masked = ""
        if key:
            masked = ("•" * 6) + key[-4:] if len(key) > 8 else "•" * 6
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "configured": self.configured,
            "api_key_masked": masked,
            "allow_runtime_config": allow_runtime_config(),
        }


def allow_runtime_config() -> bool:
    return os.getenv("ALLOW_RUNTIME_CONFIG", "true").lower() in ("1", "true", "yes")


_lock = threading.Lock()
_settings = LLMSettings()


def get_settings() -> LLMSettings:
    with _lock:
        return LLMSettings(**_settings.__dict__)


def update_settings(**kwargs) -> LLMSettings:
    with _lock:
        for k, v in kwargs.items():
            if v is None:
                continue
            if k == "api_key" and v == "":
                continue  # empty means "keep current"
            if hasattr(_settings, k):
                setattr(_settings, k, v.strip() if isinstance(v, str) else v)
        return LLMSettings(**_settings.__dict__)


def clear_api_key() -> None:
    with _lock:
        _settings.api_key = ""
