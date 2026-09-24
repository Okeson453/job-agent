"""Telegram bot long-polling entrypoint."""

from __future__ import annotations

import asyncio
import signal
import sys

import httpx

from apps.telegram.commands import HANDLERS
from src.observability.logging import configure_logging, get_logger
from src.security.secrets import get_secret
from src.telegram.notifier import send

logger = get_logger(__name__)

_API = "https://api.telegram.org"


async def _get_updates(offset: int, token: str) -> list[dict]:
    url = f"{_API}/bot{token}/getUpdates"
    timeout = httpx.Timeout(35.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(
            url, params={"offset": offset, "timeout": 25, "allowed_updates": '["message"]'}
        )
        if resp.status_code != 200:
            logger.error("telegram.get_updates.failed", status=resp.status_code)
            return []
        data = resp.json()
        return data.get("result") or []


async def _handle_message(text: str, chat_id: str) -> None:
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].split("@")[0].lower()  # strip @botname
    args = parts[1] if len(parts) > 1 else ""

    handler = HANDLERS.get(cmd)
    if handler is None:
        await send(f"Unknown command: {cmd}")
        return

    try:
        reply = await handler(args)
        await send(reply)
    except Exception as exc:
        logger.error("telegram.handler.error", cmd=cmd, error=str(exc))
        await send(f"Error handling {cmd}: {exc}")


async def run_bot() -> None:
    configure_logging(json_output=True)
    token = get_secret("TELEGRAM_BOT_TOKEN")
    expected_chat = get_secret("TELEGRAM_CHAT_ID")
    logger.info("telegram.bot.starting")

    offset = 0
    stop = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    while not stop.is_set():
        try:
            updates = await _get_updates(offset, token)
            for upd in updates:
                offset = max(offset, upd["update_id"] + 1)
                msg = upd.get("message") or {}
                text = msg.get("text") or ""
                chat = msg.get("chat") or {}
                chat_id = str(chat.get("id", ""))
                if not text.startswith("/"):
                    continue
                if expected_chat and chat_id != expected_chat:
                    logger.warning("telegram.unauthorized_chat", chat_id=chat_id)
                    continue
                await _handle_message(text, chat_id)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("telegram.poll.error", error=str(exc))
            await asyncio.sleep(3)

    logger.info("telegram.bot.stopped")


if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        sys.exit(0)
