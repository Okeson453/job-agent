"""Send messages and files via the Telegram Bot API.

Two call styles:

* ``send_message`` / ``send_document`` raise ``TelegramError`` on failure, which
  lets queue workers nack and retry.
* ``send`` returns a bool, for interactive handlers where a failed reply should
  not crash the bot loop.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from src.observability.logging import get_logger
from src.security.secrets import get_secret

logger = get_logger(__name__)

_API_BASE = "https://api.telegram.org"
MAX_MESSAGE_CHARS = 3800  # Telegram hard limit is 4096; leave room for markup
MAX_CAPTION_CHARS = 1000  # Telegram hard limit is 1024


class TelegramError(RuntimeError):
    """Raised when the Bot API rejects a request."""


def split_message(text: str, limit: int = MAX_MESSAGE_CHARS) -> list[str]:
    """Split long text on line boundaries so no chunk exceeds the API limit."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for line in text.splitlines():
        line_len = len(line) + 1
        if line_len > limit:
            # A single pathological line: hard-split it.
            if current:
                chunks.append("\n".join(current))
                current, size = [], 0
            for start in range(0, len(line), limit):
                chunks.append(line[start : start + limit])
            continue
        if size + line_len > limit:
            chunks.append("\n".join(current))
            current, size = [], 0
        current.append(line)
        size += line_len
    if current:
        chunks.append("\n".join(current))
    return chunks


async def _post(
    method: str, *, data: dict[str, Any], files: dict[str, Any] | None = None
) -> None:
    token = get_secret("TELEGRAM_BOT_TOKEN")
    url = f"{_API_BASE}/bot{token}/{method}"
    timeout = httpx.Timeout(30.0, connect=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if files is None:
                resp = await client.post(url, json=data)
            else:
                resp = await client.post(url, data=data, files=files)
    except httpx.HTTPError as exc:
        logger.error("telegram.request.error", method=method, error=str(exc))
        raise TelegramError(str(exc)) from exc

    if resp.status_code != 200:
        logger.error(
            "telegram.request.failed",
            method=method,
            status=resp.status_code,
            body=resp.text[:300],
        )
        raise TelegramError(f"{method} failed: HTTP {resp.status_code}")
    logger.info("telegram.request.ok", method=method)


async def send_message(text: str, *, parse_mode: str | None = "HTML") -> None:
    """Send one message, splitting it if needed. Raises on failure."""
    chat_id = get_secret("TELEGRAM_CHAT_ID")
    for chunk in split_message(text):
        payload: dict[str, str] = {"chat_id": chat_id, "text": chunk}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        await _post("sendMessage", data=payload)


async def send_document(
    path: str | Path,
    *,
    caption: str | None = None,
    filename: str | None = None,
) -> None:
    """Upload a document to the operator chat. Raises on failure."""
    file_path = Path(path)
    if not file_path.exists():
        raise TelegramError(f"document missing: {file_path}")

    chat_id = get_secret("TELEGRAM_CHAT_ID")
    data: dict[str, str] = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption[:MAX_CAPTION_CHARS]
        data["parse_mode"] = "HTML"

    with file_path.open("rb") as handle:
        files = {
            "document": (
                filename or file_path.name,
                handle,
                "application/octet-stream",
            )
        }
        await _post("sendDocument", data=data, files=files)
    logger.info("telegram.document.sent", path=str(file_path))


async def send(text: str, *, parse_mode: str | None = "HTML") -> bool:
    """Best-effort send: returns False instead of raising."""
    try:
        await send_message(text, parse_mode=parse_mode)
        return True
    except TelegramError:
        return False
