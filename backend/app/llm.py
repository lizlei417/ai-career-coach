"""Thin LLM client supporting OpenAI-compatible Chat Completions and the
Anthropic Messages API. Returns parsed JSON objects; retries once with a repair
instruction if the model output is not valid JSON.

Nothing here logs prompts, resume text or API keys.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from . import errors
from .config import LLMSettings, get_settings
from .errors import AppError

log = logging.getLogger("coach.llm")


def _extract_json(text: str) -> Any:
    text = text.strip()
    # strip code fences
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise json.JSONDecodeError("no json object", text, 0)


def _raise_for_status(resp: httpx.Response) -> None:
    if resp.status_code < 400:
        return
    if resp.status_code in (401, 403):
        raise AppError(errors.LLM_AUTH, 502)
    if resp.status_code == 429:
        raise AppError(errors.LLM_RATE_LIMIT, 502)
    if resp.status_code == 404:
        raise AppError(errors.LLM_FAILED, 502, "model or endpoint not found")
    raise AppError(errors.LLM_FAILED, 502, f"provider status {resp.status_code}")


async def _call_openai(s: LLMSettings, system: str, user: str, json_mode: bool) -> str:
    url = s.effective_base_url() + "/chat/completions"
    body: dict[str, Any] = {
        "model": s.model,
        "temperature": s.temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {s.api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=s.timeout) as client:
        resp = await client.post(url, json=body, headers=headers)
        if resp.status_code == 400 and json_mode and "response_format" in resp.text:
            body.pop("response_format", None)
            resp = await client.post(url, json=body, headers=headers)
    _raise_for_status(resp)
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        raise AppError(errors.AI_FORMAT, 502)


async def _call_anthropic(s: LLMSettings, system: str, user: str) -> str:
    url = s.effective_base_url() + "/v1/messages"
    body = {
        "model": s.model,
        "max_tokens": 4096,
        "temperature": s.temperature,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    headers = {
        "x-api-key": s.api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    async with httpx.AsyncClient(timeout=s.timeout) as client:
        resp = await client.post(url, json=body, headers=headers)
    _raise_for_status(resp)
    data = resp.json()
    try:
        return "".join(part.get("text", "") for part in data["content"] if part.get("type") == "text")
    except (KeyError, TypeError):
        raise AppError(errors.AI_FORMAT, 502)


async def _raw(s: LLMSettings, system: str, user: str) -> str:
    try:
        if s.provider == "anthropic":
            return await _call_anthropic(s, system, user)
        return await _call_openai(s, system, user, json_mode=True)
    except httpx.TimeoutException:
        raise AppError(errors.LLM_TIMEOUT, 504)
    except httpx.HTTPError as e:
        log.warning("LLM transport error: %s", type(e).__name__)
        raise AppError(errors.LLM_FAILED, 502, type(e).__name__)


async def complete_json(system: str, user: str) -> dict:
    s = get_settings()
    if not s.configured:
        raise AppError(errors.LLM_NOT_CONFIGURED, 503)
    text = await _raw(s, system, user)
    try:
        obj = _extract_json(text)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, ValueError):
        pass
    # one repair attempt
    repair_user = (
        user
        + "\n\n---\nYour previous reply was not a valid JSON object. "
        "Reply again with ONLY one valid JSON object that follows the required schema. No prose, no code fences."
    )
    text = await _raw(s, system, repair_user)
    try:
        obj = _extract_json(text)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, ValueError):
        pass
    raise AppError(errors.AI_FORMAT, 502)


async def ping() -> dict:
    """Minimal connectivity test used by the Settings panel."""
    obj = await complete_json(
        "You are a health check. Reply with JSON only.",
        'Return exactly this JSON object: {"ok": true}',
    )
    return {"ok": bool(obj.get("ok", False))}
