"""LLM client via OmniRoute (preferred) or direct DeepSeek API.

OmniRoute is the free gateway (OpenAI-compatible). Point
OMNIROUTE_ENDPOINT at your OmniRoute /v1 base URL and use model ``auto``
so free providers are selected. Direct api.deepseek.com is paid and will
return 402 when the balance is exhausted.
"""

from __future__ import annotations

import asyncio
import os
import random
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from src.observability.logging import get_logger
from src.security.secrets import get_secret

logger = get_logger(__name__)

_BALANCE_CIRCUIT_UNTIL = 0.0
_BALANCE_COOLDOWN_SEC = float(os.environ.get("DEEPSEEK_BALANCE_COOLDOWN_SEC", "900"))


class DeepSeekBalanceError(RuntimeError):
    """Raised when the upstream returns HTTP 402 (insufficient balance)."""


def balance_circuit_open() -> bool:
    return time.monotonic() < _BALANCE_CIRCUIT_UNTIL


def _trip_balance_circuit() -> None:
    global _BALANCE_CIRCUIT_UNTIL
    _BALANCE_CIRCUIT_UNTIL = time.monotonic() + _BALANCE_COOLDOWN_SEC
    logger.error(
        "llm.insufficient_balance",
        cooldown_sec=_BALANCE_COOLDOWN_SEC,
        hint="Upstream balance empty — use OmniRoute free providers or top up DeepSeek",
    )


def _resolve_endpoint() -> str:
    """Prefer OmniRoute; only fall back to paid DeepSeek if explicitly unset."""
    for key in ("OMNIROUTE_ENDPOINT", "LLM_BASE_URL"):
        val = (get_secret(key) or os.environ.get(key) or "").strip()
        if val:
            return val.rstrip("/")
    return "https://api.deepseek.com/v1"


def _resolve_api_key() -> str:
    for key in ("OMNIROUTE_API_KEY", "DEEPSEEK_API_KEY", "LLM_API_KEY"):
        val = (get_secret(key) or os.environ.get(key) or "").strip()
        if val:
            return val
    return "omniroute"


def _resolve_model() -> str:
    return (
        os.environ.get("LLM_MODEL")
        or get_secret("LLM_MODEL")
        or "auto"
    )


T = TypeVar("T", bound=BaseModel)

_DEFAULT_TIMEOUT = 45.0
_MAX_RETRIES = 2
_BASE_BACKOFF = 1.0


class DeepSeekClient:
    """OpenAI-compatible chat client (OmniRoute gateway or DeepSeek direct)."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        endpoint: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _MAX_RETRIES,
    ) -> None:
        self._api_key = api_key if api_key is not None else _resolve_api_key()
        self._endpoint = (endpoint or _resolve_endpoint()).rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._model = _resolve_model()
        logger.info(
            "llm.client.configured",
            endpoint=self._endpoint,
            model=self._model,
            paid_direct="api.deepseek.com" in self._endpoint,
        )

    async def complete(
        self,
        prompt: str,
        response_schema: type[T] | None = None,
        *,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str | T:
        if balance_circuit_open():
            raise DeepSeekBalanceError(
                "LLM balance circuit open — switch OMNIROUTE_ENDPOINT to a free gateway or wait"
            )

        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                raw = await self._call(prompt, temperature=temperature, max_tokens=max_tokens)
                if response_schema is None:
                    return raw
                return self._parse_schema(raw, response_schema)
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt >= self._max_retries:
                    break
                delay = _BASE_BACKOFF * (2**attempt) + random.uniform(0, 0.5)
                await asyncio.sleep(delay)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code if exc.response is not None else 0
                if status == 402:
                    _trip_balance_circuit()
                    break
                if status < 500 and status != 429:
                    break
                if attempt >= self._max_retries:
                    break
                delay = _BASE_BACKOFF * (2**attempt) + random.uniform(0, 0.5)
                logger.warning(
                    "llm.retry",
                    attempt=attempt + 1,
                    delay=round(delay, 2),
                    status=status,
                )
                await asyncio.sleep(delay)
            except ValidationError as exc:
                last_error = exc
                if attempt >= 1:
                    break
                logger.warning("llm.schema_retry", error=str(exc))
                await asyncio.sleep(0.5)

        assert last_error is not None
        logger.error("llm.failed", error=str(last_error), endpoint=self._endpoint)
        raise last_error

    async def _call(
        self,
        prompt: str,
        *,
        temperature: float,
        max_tokens: int,
    ) -> str:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        body = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        url = f"{self._endpoint}/chat/completions"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code >= 400:
                logger.error(
                    "llm.client_error",
                    status=resp.status_code,
                    body=resp.text[:500],
                    endpoint=self._endpoint,
                    model=self._model,
                )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def _parse_schema(self, raw: str, schema: type[T]) -> T:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        return schema.model_validate_json(text)
