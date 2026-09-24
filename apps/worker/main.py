"""Worker process entrypoint — starts all six asyncio loops."""

from __future__ import annotations

import asyncio
import signal
import sys

from src.observability.logging import configure_logging, get_logger
from src.observability.tracing import configure_tracing
from src.scheduler.queues import close_redis
from src.database.session import close_engine

from apps.worker.discovery_worker import run_discovery_loops
from apps.worker.matching_worker import run_matching_loop
from apps.worker.llm_worker import run_llm_loop
from apps.worker.application_worker import run_application_loop
from apps.worker.browser_worker import run_browser_loop
from apps.worker.notification_worker import run_notification_loop

logger = get_logger(__name__)


async def main() -> None:
    configure_logging(json_output=True)
    configure_tracing(service_name="job-agent-worker")
    logger.info("worker.starting")

    from src.candidate.profile.service import seed_from_json
    from src.database.session import get_session

    try:
        async with get_session() as db:
            await seed_from_json(db)
    except Exception as exc:
        logger.warning("worker.seed_failed", error=str(exc))

    tasks = [
        asyncio.create_task(run_discovery_loops(), name="discovery"),
        asyncio.create_task(run_matching_loop(), name="matching"),
        asyncio.create_task(run_llm_loop(), name="llm"),
        asyncio.create_task(run_application_loop(), name="application"),
        asyncio.create_task(run_browser_loop(), name="browser"),
        asyncio.create_task(run_notification_loop(), name="notification"),
    ]

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("worker.shutdown_signal")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    await stop_event.wait()

    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    await close_redis()
    await close_engine()
    logger.info("worker.stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
