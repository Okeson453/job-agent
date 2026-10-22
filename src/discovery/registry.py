"""Source registry — the single place that decides which sources are active.

discovery_worker iterates this dict; it never imports individual adapters
directly. All sources are zero-credential public feeds or browser listings.

The four primary IT/tech sources are enabled by default. Legacy sources stay
available behind explicit env flags but are off unless opted in.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from src.observability.logging import get_logger

if TYPE_CHECKING:
    from src.discovery.base import JobSource

logger = get_logger(__name__)

_SOURCES: dict[str, JobSource] | None = None


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "1" if default else "0")
    return raw.lower() in ("1", "true", "yes", "on")


# (module, class, env flag, enabled by default)
_PRIMARY_SOURCES: tuple[tuple[str, str, str], ...] = (
    ("src.discovery.ioassociates.adapter", "IOAssociatesAdapter", "DISCOVERY_IOASSOCIATES_ENABLED"),
    ("src.discovery.expertwoka.adapter", "ExpertWokaAdapter", "DISCOVERY_EXPERTWOKA_ENABLED"),
    ("src.discovery.turing.adapter", "TuringAdapter", "DISCOVERY_TURING_ENABLED"),
    ("src.discovery.micro1.adapter", "Micro1Adapter", "DISCOVERY_MICRO1_ENABLED"),
)

# Legacy broad-board sources. Kept for opt-in use; off by default so polling
# is spent on the configured primary sources.
_LEGACY_SOURCES: tuple[tuple[str, str, str], ...] = (
    ("src.discovery.greenhouse.adapter", "GreenhouseAdapter", "DISCOVERY_GREENHOUSE_ENABLED"),
    ("src.discovery.lever.adapter", "LeverAdapter", "DISCOVERY_LEVER_ENABLED"),
    ("src.discovery.remoteok.adapter", "RemoteOKAdapter", "DISCOVERY_REMOTEOK_ENABLED"),
    ("src.discovery.himalayas.adapter", "HimalayasAdapter", "DISCOVERY_HIMALAYAS_ENABLED"),
    ("src.discovery.wellfound.adapter", "WellfoundAdapter", "DISCOVERY_WELLFOUND_ENABLED"),
    ("src.discovery.yc.adapter", "YCAdapter", "DISCOVERY_YC_ENABLED"),
    ("src.discovery.linkedin.adapter", "LinkedInAdapter", "DISCOVERY_LINKEDIN_ENABLED"),
    ("src.discovery.indeed.adapter", "IndeedAdapter", "DISCOVERY_INDEED_ENABLED"),
    ("src.discovery.otta.adapter", "OttaAdapter", "DISCOVERY_OTTA_ENABLED"),
    ("src.discovery.arc.adapter", "ArcAdapter", "DISCOVERY_ARC_ENABLED"),
    ("src.discovery.contra.adapter", "ContraAdapter", "DISCOVERY_CONTRA_ENABLED"),
    ("src.discovery.company_career.adapter", "CompanyCareerAdapter", "DISCOVERY_COMPANY_CAREER_ENABLED"),
)


def _load(module_name: str, class_name: str) -> JobSource | None:
    import importlib

    try:
        module = importlib.import_module(module_name)
        return getattr(module, class_name)()
    except Exception as exc:  # pragma: no cover - import failures are logged, not fatal
        logger.error("discovery.registry.import_failed", module=module_name, error=str(exc))
        return None


def get_sources() -> dict[str, JobSource]:
    """Return the active source registry, building it on first call."""
    global _SOURCES
    if _SOURCES is not None:
        return _SOURCES

    sources: dict[str, JobSource] = {}

    for module_name, class_name, env_flag in _PRIMARY_SOURCES:
        if not _env_flag(env_flag, default=True):
            continue
        adapter = _load(module_name, class_name)
        if adapter is not None:
            sources[adapter.source_name] = adapter

    for module_name, class_name, env_flag in _LEGACY_SOURCES:
        if not _env_flag(env_flag, default=False):
            continue
        adapter = _load(module_name, class_name)
        if adapter is not None:
            sources[adapter.source_name] = adapter

    _SOURCES = sources
    logger.info("discovery.registry.loaded", sources=list(sources.keys()))
    return sources


def reset_registry() -> None:
    """Clear the cached registry. Intended for tests only."""
    global _SOURCES
    _SOURCES = None
