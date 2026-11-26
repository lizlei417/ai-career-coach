import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str
    timeout: float
    max_tokens: int
    knowledge_dir: Path


def settings() -> Settings:
    # dotenv_values allows a saved .env edit to take effect on the next rerun.
    from dotenv import dotenv_values
    values = {**dotenv_values(ROOT / ".env"), **os.environ}
    try:
        timeout = float(values.get("OPENAI_TIMEOUT", "60"))
        tokens = int(values.get("OPENAI_MAX_OUTPUT_TOKENS", "8000"))
        if not 5 <= timeout <= 180 or not 1000 <= tokens <= 32000:
            raise ValueError
    except (ValueError, TypeError):
        from coach.errors import CoachError
        raise CoachError("配置无效：超时须为 5–180 秒，输出 token 上限须为 1000–32000。") from None
    directory = Path(values.get("KNOWLEDGE_DIR", "knowledge"))
    return Settings(str(values.get("OPENAI_API_KEY") or "").strip(),
                    str(values.get("OPENAI_MODEL") or "gpt-4o-mini").strip(),
                    timeout, tokens, directory if directory.is_absolute() else ROOT / directory)
