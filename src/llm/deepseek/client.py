"""OmniRoute-backed DeepSeek 4.1 client.

This is the only file in the repository that makes an outbound call to DeepSeek.
Every other module goes through DeepSeekClient.complete().
"""

from __future__ import annotations

import asyncio
import os
import json
import random
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from src.observability.logging import get_logger
from src.security.secrets import get_secret

logger = get_logger(__name__)

# After a 402 Insufficient Balance, skip outbound LLM calls for a cool-down
# so we do not spam DeepSeek or stall the queue with guaranteed failures.
_BALANCE_CIRCUIT_UNTIL = 0.0
_BALANCE_COOLDOWN_SEC = float(os.environ.get("DEEPSEEK_BALANCE_COOLDOWN_SEC", "900"))


class DeepSeekBalanceError(RuntimeError):
    """Raised when the DeepSeek account has insufficient balance (HTTP 402)."""


def balance_circuit_open() -> bool:
    return time.monotonic() < _BALANCE_CIRCUIT_UNTIL


def _trip_balance_circuit() -> None:
    global _BALANCE_CIRCUIT_UNTIL
    _BALANCE_CIRCUIT_UNTIL = time.monotonic() + _BALANCE_COOLDOWN_SEC
    logger.error(
        "deepseek.insufficient_balance",
        cooldown_sec=_BALANCE_COOLDOWN_SEC,
        hint="Top up the DeepSeek account; semantic matching paused until cooldown ends",
    )


T = TypeVar("T", bound=BaseModel)

_DEFAULT_TIMEOUT = 20.0
_MAX_RETRIES = 2
_BASE_BACKOFF = 1.0


class DeepSeekClient:
    """Thin async client for DeepSeek 4.1 via OmniRoute or direct API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        endpoint: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _MAX_RETRIES,
    ) -> None:
        self._api_key = api_key or get_secret("DEEPSEEK_API_KEY")
        self._endpoint = (
            endpoint
            or get_secret("OMNIROUTE_ENDPOINT")
            or "https://api.deepseek.com/v1"
        )
        self._timeout = timeout
        self._max_retries = max_retries

    async def complete(
        self,
        prompt: str,
        response_schema: type[T] | None = None,
        *,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str | T:
        """Send *prompt* and return raw text or a validated Pydantic model.

        Retries on timeout / 5xx with exponential backoff + jitter (max 2).
        If response_schema is given, validates and retries once on failure
        before raising.
        """
        if balance_circuit_open():
            raise DeepSeekBalanceError(
                "DeepSeek balance circuit open — top up account or wait for cooldown"
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
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code if exc.response is not None else 0
                if status == 402:
                    _trip_balance_circuit()
                    break
                # Retry only transient failures: 429 and 5xx. Never retry 401/403/402.
                if status < 500 and status != 429:
                    break
                if attempt >= self._max_retries:
                    break
                delay = _BASE_BACKOFF * (2**attempt) + random.uniform(0, 0.5)
                logger.warning(
                    "deepseek.retry",
                    attempt=attempt + 1,
                    delay=round(delay, 2),
                    error=str(exc),
                )
                await asyncio.sleep(delay)
            except ValidationError as exc:
                last_error = exc
                if attempt >= 1:
                    break
                logger.warning("deepseek.schema_retry", error=str(exc))
                await asyncio.sleep(0.5)

        assert last_error is not None
        logger.error("deepseek.failed", error=str(last_error))
        raise last_error

    async def _call(
        self,
        prompt: str,
        *,
        temperature: float,
        max_tokens: int,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": os.environ.get("LLM_MODEL", "deepseek-chat"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        url = self._endpoint.rstrip("/") + "/chat/completions"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code >= 400:
                logger.error(
                    "deepseek.client_error",
                    status=resp.status_code,
                    body=resp.text[:500],
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
