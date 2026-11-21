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
    values = {**dotenv_values(Path.home() / ".config/ai-career-coach/deepseek.env"),
              **dotenv_values(ROOT / ".env"), **os.environ}
    try:
        timeout = float(values.get("DEEPSEEK_TIMEOUT", "60"))
        tokens = int(values.get("DEEPSEEK_MAX_OUTPUT_TOKENS", "3072"))
        if not 5 <= timeout <= 180 or not 1000 <= tokens <= 4096:
            raise ValueError
    except (ValueError, TypeError):
        from coach.errors import CoachError
        raise CoachError("配置无效：超时须为 5–180 秒，输出 token 上限须为 1000–4096。") from None
    directory = Path(values.get("KNOWLEDGE_DIR", "knowledge"))
    return Settings(str(values.get("DEEPSEEK_API_KEY") or "").strip(),
                    str(values.get("DEEPSEEK_MODEL") or "deepseek-flash").strip(),
                    timeout, tokens, directory if directory.is_absolute() else ROOT / directory)
