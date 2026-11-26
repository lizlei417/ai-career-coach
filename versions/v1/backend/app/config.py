"""Server-only model and application configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


KB_DIR = Path(os.getenv("KB_DIR", BASE_DIR / "data" / "kb"))
PROMPT_DIR = BASE_DIR / "prompts"
CUSTOM_PROMPT_DIR = PROMPT_DIR / "custom"
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", BASE_DIR.parent / "frontend" / "dist"))

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_TEXT_CHARS = 30000


@dataclass(frozen=True)
class LLMSettings:
    provider: str = "deepseek"
    api_key: str = field(default="", repr=False)
    model: str = "deepseek-flash"
    timeout: float = 60

    @property
    def configured(self):
        return bool(self.api_key)

    def public(self):
        from .llm import connection
        return {"provider": self.provider, "model": self.model, "base_url": "https://api.deepseek.com",
                "configured": self.configured, "connection": connection if self.configured else "offline",
                "timeout": self.timeout, "allow_runtime_config": False}


def get_settings():
    key = os.getenv("DEEPSEEK_API_KEY") or dotenv_values(Path.home() / ".config/ai-career-coach/deepseek.env").get("DEEPSEEK_API_KEY")
    return LLMSettings(api_key=(key or "").strip())
