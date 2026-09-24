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
    "OMNIROUTE_ENDPOINT": "https://api.deepseek.com/v1",
    "ALLOWED_DOMAINS": "boards.greenhouse.io,jobs.lever.co,www.linkedin.com,www.indeed.com",
    "APPLICATION_MODE_DEFAULT": "APPROVAL",
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
        # Also try project root relative to this package.
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
    """Return the value of a named secret.

    Raises RuntimeError if a required secret is absent.
    Raises KeyError if an unknown optional name is requested and not present.
    """
    secrets = _load_all()
    if name in secrets:
        return secrets[name]
    # Allow late-bound optional keys that were not in the defaults table.
    value = os.environ.get(name)
    if value is not None:
        return value
    raise KeyError(f"Secret '{name}' is not configured.")


def reload_secrets() -> None:
    """Clear secret + dependent caches so subsequent reads re-load the environment."""
    _load_all.cache_clear()
    try:
        from src.security.allowlist import reset_allowlist_cache

        reset_allowlist_cache()
    except Exception:
        pass
    try:
        from src.security.encryption import reset_encryption_cache

        reset_encryption_cache()
    except Exception:
        pass
