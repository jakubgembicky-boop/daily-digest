"""
Shared Groq (OpenAI-compatible) client wrapper.

Used by cluster.py, process.py, and generate.py. Centralizes:
  - client construction (Groq base_url swap)
  - global throttle (>= GROQ_DELAY_SECONDS between calls — 30 RPM free limit)
  - retry with backoff
  - automatic fallback from the 70B model to the 8B model
  - optional JSON-object response mode + safe JSON parsing

Requires the GROQ_API_KEY environment variable.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from openai import OpenAI

import config

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

_client: OpenAI | None = None
_last_call_ts: float = 0.0


def get_client() -> OpenAI:
    """Lazily construct and cache the Groq client."""
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        _client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
    return _client


def _throttle() -> None:
    """Block until at least GROQ_DELAY_SECONDS have passed since the last call."""
    global _last_call_ts
    elapsed = time.time() - _last_call_ts
    wait = config.GROQ_DELAY_SECONDS - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_call_ts = time.time()


def chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    json_mode: bool = False,
) -> str:
    """
    Call Groq chat completions with throttle + retry + model fallback.
    Returns the assistant message content string. Raises on total failure.
    """
    client = get_client()
    models = [model or config.GROQ_PRIMARY_MODEL]
    if config.GROQ_FALLBACK_MODEL not in models:
        models.append(config.GROQ_FALLBACK_MODEL)

    last_err: Exception | None = None
    for m in models:
        for attempt in range(2):
            try:
                _throttle()
                kwargs: dict[str, Any] = {
                    "model":       m,
                    "messages":    messages,
                    "temperature": temperature,
                    "max_tokens":  max_tokens,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                resp = client.chat.completions.create(**kwargs)
                return resp.choices[0].message.content or ""
            except Exception as err:  # noqa: BLE001
                last_err = err
                print(f"    ! Groq {m} attempt {attempt + 1} failed: "
                      f"{type(err).__name__}: {err}")
                time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"Groq failed after all retries: {last_err}")


def _extract_json(raw: str) -> str:
    """Pull the first JSON object/array out of a possibly-noisy string."""
    raw = raw.strip()
    # strip ```json ... ``` fences if present
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", raw, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()
    if raw and raw[0] in "{[":
        return raw
    m = re.search(r"(\{.*\}|\[.*\])", raw, re.DOTALL)
    return m.group(1) if m else raw


def chat_json(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> Any:
    """chat() in JSON mode, parsed to a Python object. Raises on parse failure."""
    raw = chat(
        messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        json_mode=True,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(_extract_json(raw))
