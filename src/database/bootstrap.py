"""Schema bootstrap for empty managed databases.

Railway (and similar) provision Postgres without running Alembic. The worker
and API call ``ensure_schema()`` once at process start so tables such as
``seed_meta`` exist before seed/runtime queries.
"""

from __future__ import annotations

import asyncio

from src.observability.logging import get_logger

logger = get_logger(__name__)

_SCHEMA_READY = False
_SCHEMA_LOCK = asyncio.Lock()


async def ensure_schema() -> None:
    """Create missing tables (Alembic upgrade when possible, else create_all)."""
    global _SCHEMA_READY
    async with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return

        # Prefer Alembic so migration history stays consistent.
        try:
            await asyncio.to_thread(_alembic_upgrade_head)
            _SCHEMA_READY = True
            logger.info("schema.ready", via="alembic")
            return
        except Exception as exc:
            logger.warning("schema.alembic_failed", error=str(exc))

        try:
            await _create_all()
            _SCHEMA_READY = True
            logger.info("schema.ready", via="create_all")
        except Exception as exc:
            logger.error("schema.bootstrap_failed", error=str(exc))
            raise


def _alembic_upgrade_head() -> None:
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    root = Path(__file__).resolve().parents[2]
    ini = root / "alembic.ini"
    if not ini.exists():
        raise FileNotFoundError(f"alembic.ini not found at {ini}")
    cfg = Config(str(ini))
    # env.py reads DATABASE_URL from the environment.
    command.upgrade(cfg, "head")


async def _create_all() -> None:
    # Import every module that defines a mapped table so metadata is complete.
    import src.applications.automation_failures  # noqa: F401
    import src.applications.browser.sessions_store  # noqa: F401
    import src.applications.models  # noqa: F401
    import src.candidate.models  # noqa: F401
    import src.jobs.models  # noqa: F401
    import src.scheduler.outbox  # noqa: F401
    import src.telegram.notifications_store  # noqa: F401
    from src.database.base import Base
    from src.database.session import get_engine

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
