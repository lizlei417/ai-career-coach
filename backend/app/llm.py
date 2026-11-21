"""Single-attempt DeepSeek JSON transport. Prompts and credentials stay on the server."""
import json

import httpx

from .config import get_settings
from .errors import AppError

connection = "unverified"
balance_blocked = False


async def _request(system: str, user: str, max_tokens: int):
    global connection, balance_blocked
    cfg = get_settings()
    if not cfg.configured:
        raise AppError("LLM_NOT_CONFIGURED", 503)
    if balance_blocked:
        raise AppError("LLM_BALANCE", 402)
    if len(system) + len(user) > 64000:
        raise AppError("CONTEXT_LIMIT", 422)
    body = {"model": cfg.model, "messages": [{"role": "system", "content": system + "\nReturn JSON."},
            {"role": "user", "content": user}], "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"}, "max_tokens": max_tokens}
    try:
        async with httpx.AsyncClient(timeout=cfg.timeout) as client:
            response = await client.post("https://api.deepseek.com/chat/completions", json=body,
                    headers={"Authorization": "Bearer " + cfg.api_key})
        if response.status_code == 402:
            balance_blocked = True
        response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]
        if choice["finish_reason"] != "stop":
            raise ValueError
        result = json.loads(choice["message"]["content"])
        if not isinstance(result, dict):
            raise ValueError
    except httpx.HTTPStatusError as exc:
        connection = "failed"
        code = {401: "LLM_AUTH", 403: "LLM_AUTH", 402: "LLM_BALANCE", 429: "LLM_RATE_LIMIT"}.get(exc.response.status_code, "LLM_FAILED")
        raise AppError(code, 502) from None
    except httpx.TimeoutException:
        connection = "failed"
        raise AppError("LLM_TIMEOUT", 504) from None
    except httpx.RequestError:
        connection = "failed"
        raise AppError("NETWORK", 502) from None
    except (ValueError, TypeError, KeyError, IndexError):
        connection = "failed"
        raise AppError("AI_FORMAT", 502) from None
    connection = "verified"
    return result, {k: v for k, v in (data.get("usage") or {}).items() if k in ("prompt_tokens", "completion_tokens", "total_tokens") and isinstance(v, int)}


async def complete_json(system: str, user: str) -> dict:
    result, _ = await _request(system, user, 3072)
    return result


async def ping():
    result, usage = await _request("Reply in JSON.", 'Return {"ok":true}', max_tokens=32)
    if result.get("ok") is not True:
        global connection
        connection = "failed"
        raise AppError("AI_FORMAT", 502)
    return {"ok": True, "model": get_settings().model, "usage": usage}
