"""Schema bootstrap for empty managed databases.

Railway provisions Postgres without running Alembic. Worker and API call
``ensure_schema()`` at process start so tables exist before seed/runtime.

Uses ``create_all`` as the primary path — reliable under an already-running
asyncio loop. Alembic upgrade is attempted best-effort with a timeout; it must
not block worker startup.
"""

from __future__ import annotations

import asyncio

from src.observability.logging import get_logger

logger = get_logger(__name__)

_SCHEMA_READY = False
_SCHEMA_LOCK = asyncio.Lock()
_ALEMBIC_TIMEOUT_SEC = 45.0


async def ensure_schema() -> None:
    """Ensure all ORM tables exist. Never block forever on Alembic."""
    global _SCHEMA_READY
    async with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return

        logger.info("schema.bootstrap.start")

        # Primary path: metadata.create_all (idempotent, works in-async).
        try:
            await _create_all()
            logger.info("schema.ready", via="create_all")
        except Exception as exc:
            logger.error("schema.create_all_failed", error=str(exc))
            raise

        # Best-effort Alembic so version table stays current — never block startup.
        try:
            await asyncio.wait_for(
                asyncio.to_thread(_alembic_upgrade_head),
                timeout=_ALEMBIC_TIMEOUT_SEC,
            )
            logger.info("schema.alembic_ok")
        except asyncio.TimeoutError:
            logger.warning(
                "schema.alembic_timeout",
                timeout_sec=_ALEMBIC_TIMEOUT_SEC,
                hint="tables already created via create_all; continuing",
            )
        except Exception as exc:
            logger.warning("schema.alembic_skipped", error=str(exc))

        _SCHEMA_READY = True
        logger.info("schema.bootstrap.done")


def _alembic_upgrade_head() -> None:
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    root = Path(__file__).resolve().parents[2]
    ini = root / "alembic.ini"
    if not ini.exists():
        raise FileNotFoundError(f"alembic.ini not found at {ini}")
    cfg = Config(str(ini))
    command.upgrade(cfg, "head")


async def _create_all() -> None:
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
