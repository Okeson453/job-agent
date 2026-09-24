"""Shared Telegram send helper used by workers and the bot process."""

from src.telegram.notifier import send

__all__ = ["send"]
