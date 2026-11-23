"""Single-attempt DeepSeek JSON transport. Prompts and credentials stay on the server."""
from contextvars import ContextVar
from . import cloud
import asyncio
import json
import logging

import httpx

from .config import get_settings
from .errors import AppError

received_usage = ContextVar("received_usage", default=None)
connection = "unverified"
balance_blocked = False
last_error = ""
verified_at = None


async def _request(system: str, user: str, max_tokens: int):
    global connection, balance_blocked, last_error, verified_at
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
    call=await asyncio.to_thread(cloud.reserve_call)
    try:
        await asyncio.to_thread(cloud.dispatch_call,call)
        async with httpx.AsyncClient(timeout=cfg.timeout) as client:
            response = await client.post("https://api.deepseek.com/chat/completions", json=body,
                    headers={"Authorization": "Bearer " + cfg.api_key})
        if response.status_code == 402:
            balance_blocked = True
            await asyncio.to_thread(cloud.record_usage,call,blocked=True)
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError:
            raise AppError("AI_FORMAT", 502, "invalid_envelope") from None
        raw_usage=data.get("usage") if isinstance(data,dict) else None
        if isinstance(raw_usage,dict): received_usage.set(raw_usage)
        if isinstance(raw_usage,dict): await asyncio.to_thread(cloud.record_usage,call,raw_usage.get("total_tokens"))
        result, usage = parse_completion(data)
    except AppError:
        connection = "failed"
        last_error = "AI_FORMAT"
        raise
    except httpx.HTTPStatusError as exc:
        connection = "failed"
        code = {401: "LLM_AUTH", 403: "LLM_AUTH", 402: "LLM_BALANCE", 429: "LLM_RATE_LIMIT"}.get(exc.response.status_code, "LLM_FAILED")
        last_error = code
        raise AppError(code, 502) from None
    except (httpx.ConnectError,httpx.ConnectTimeout,httpx.PoolTimeout):
        await asyncio.to_thread(cloud.cancel_unsent,call)
        connection = "failed"
        last_error = "NETWORK"
        raise AppError("NETWORK", 502) from None
    except httpx.TimeoutException:
        connection = "failed"
        last_error = "LLM_TIMEOUT"
        raise AppError("LLM_TIMEOUT", 504) from None
    except httpx.RequestError:
        connection = "failed"
        last_error = "NETWORK"
        raise AppError("NETWORK", 502) from None
    except (ValueError, TypeError, KeyError, IndexError):
        connection = "failed"
        raise AppError("AI_FORMAT", 502) from None
    import time
    connection = "verified"
    last_error = ""
    verified_at = time.time()
    return result, raw_usage if isinstance(raw_usage,dict) else usage


def parse_completion(data):
    try:
        choice = data["choices"][0]
        reason = choice["finish_reason"]
        content = choice["message"]["content"]
    except (TypeError, IndexError, KeyError):
        raise AppError("AI_FORMAT", 502, "unexpected_envelope") from None
    raw_usage = data.get("usage")
    usage = {k: raw_usage[k] for k in ("prompt_tokens", "completion_tokens", "total_tokens")
             if isinstance(raw_usage, dict) and type(raw_usage.get(k)) is int}
    logging.getLogger(__name__).info("completion finish=%s chars=%s blank=%s usage=%s",
        reason if reason in ("stop", "length", "content_filter") else "other",
        len(content) if isinstance(content, str) else None, isinstance(content,str) and not content.strip(), usage)
    if reason != "stop":
        raise AppError("AI_FORMAT", 502, "output_limit" if reason == "length" else "incomplete")
    if not isinstance(content, str):
        raise AppError("AI_FORMAT", 502, "missing_content")
    if not content.strip():
        raise AppError("AI_FORMAT", 502, "whitespace" if content else "empty")
    try:
        result = json.loads(content)
    except ValueError:
        raise AppError("AI_FORMAT", 502, "invalid_json") from None
    if not isinstance(result, dict):
        raise AppError("AI_FORMAT", 502, "expected_object")
    return result, usage


async def complete_json(system: str, user: str) -> dict:
    result, _ = await _request(system, user, 3072)
    return result


async def ping():
    result, usage = await _request('Return exactly one JSON object, for example {"ok":true}. The ok field must be a JSON boolean.', "Confirm connectivity with ok set to true.", max_tokens=128)
    if result.get("ok") is not True:
        global connection
        connection = "failed"
        raise AppError("AI_FORMAT", 502, "invalid_probe_flag")
    return {"ok": True, "model": get_settings().model, "usage": usage}
