"""Secret loading.

Every module that needs a credential calls get_secret(); nothing reads
os.environ for secrets directly. Missing required secrets raise immediately
rather than silently defaulting.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

_REQUIRED = frozenset(
    {
        "DATABASE_URL",
        "REDIS_URL",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "ENCRYPTION_KEY",
    }
)

_OPTIONAL_DEFAULTS: dict[str, str] = {
    "DEEPSEEK_API_KEY": "",
    "OMNIROUTE_ENDPOINT": "",  # e.g. http://omniroute:20128/v1 — free gateway
    "OMNIROUTE_API_KEY": "omniroute",
    "LLM_MODEL": "auto",
    "ALLOWED_DOMAINS": "boards-api.greenhouse.io,boards.greenhouse.io,api.lever.co,jobs.lever.co,www.linkedin.com,www.indeed.com,wellfound.com",
    "APPLICATION_MODE_DEFAULT": "AUTO",
    "BROWSER_WORKER_CONCURRENCY": "2",
    "MATCHING_WORKER_CONCURRENCY": "5",
    "LLM_WORKER_CONCURRENCY": "3",
    "MATCH_THRESHOLD": "40",
}


def _ensure_dotenv_loaded() -> None:
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
    else:
        root = Path(__file__).resolve().parents[2]
        candidate = root / ".env"
        if candidate.exists():
            load_dotenv(candidate, override=False)


@lru_cache(maxsize=1)
def _load_all() -> dict[str, str]:
    _ensure_dotenv_loaded()
    result: dict[str, str] = {}
    for key in _REQUIRED:
        value = os.environ.get(key)
        if value is None or value.strip() == "":
            raise RuntimeError(
                f"Required secret '{key}' is missing or empty. "
                "Set it in the environment or .env file."
            )
        result[key] = value
    for key, default in _OPTIONAL_DEFAULTS.items():
        result[key] = os.environ.get(key, default)
    return result


def get_secret(name: str) -> str:
    """Return the value of a named secret."""
    secrets = _load_all()
    if name in secrets:
        return secrets[name]
    value = os.environ.get(name)
    if value is not None:
        return value
    raise KeyError(f"Unknown secret: {name}")


def reload_secrets() -> None:
    """Clear cache so subsequent get_secret() re-reads the environment."""
    _load_all.cache_clear()
