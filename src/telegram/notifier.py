"""Send messages via the Telegram Bot API.

Used by notification_worker and any module that needs to alert the operator.
"""

from __future__ import annotations

import httpx

from src.observability.logging import get_logger
from src.security.secrets import get_secret

logger = get_logger(__name__)

_API_BASE = "https://api.telegram.org"


async def send(text: str, *, parse_mode: str | None = "HTML") -> bool:
    """Send a message to the configured TELEGRAM_CHAT_ID.

    Returns True on success, False on failure (logged, not raised — notifications
    must not crash the pipeline).
    """
    token = get_secret("TELEGRAM_BOT_TOKEN")
    chat_id = get_secret("TELEGRAM_CHAT_ID")

    url = f"{_API_BASE}/bot{token}/sendMessage"
    payload: dict[str, str | int] = {
        "chat_id": chat_id,
        "text": text,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    timeout = httpx.Timeout(15.0, connect=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.error(
                    "telegram.send.failed",
                    status=resp.status_code,
                    body=resp.text[:200],
                )
                return False
            logger.info("telegram.send.ok", chat_id=chat_id)
            return True
    except httpx.HTTPError as exc:
        logger.error("telegram.send.error", error=str(exc))
        return False
