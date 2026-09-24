"""FastAPI app entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from fastapi import Depends

from apps.api.dependencies import require_api_key
from apps.api.middleware import RequestContextMiddleware
from apps.api.routes import applications, candidate, control, health, jobs, stats
from src.database.session import close_engine
from src.observability.logging import configure_logging, get_logger
from src.observability.tracing import configure_tracing
from src.scheduler.queues import close_redis

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(json_output=True)
    configure_tracing(service_name="job-agent-api")
    logger.info("api.starting")
    yield
    await close_redis()
    await close_engine()
    logger.info("api.stopped")


app = FastAPI(
    title="Job Agent API",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(RequestContextMiddleware)

# Health is public; everything else can require API_KEY when configured.
app.include_router(health.router)
_auth = [Depends(require_api_key)]
app.include_router(jobs.router, dependencies=_auth)
app.include_router(applications.router, dependencies=_auth)
app.include_router(candidate.router, dependencies=_auth)
app.include_router(stats.router, dependencies=_auth)
app.include_router(control.router, dependencies=_auth)
