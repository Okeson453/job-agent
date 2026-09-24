"""Source registry — the single place that decides which sources are active.

discovery_worker iterates this dict; it never imports individual adapters
directly. All sources are zero-credential public feeds or browser listings.
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


def get_sources() -> dict[str, JobSource]:
    """Return the active source registry, building it on first call."""
    global _SOURCES
    if _SOURCES is not None:
        return _SOURCES

    sources: dict[str, JobSource] = {}

    if _env_flag("DISCOVERY_GREENHOUSE_ENABLED", default=True):
        from src.discovery.greenhouse.adapter import GreenhouseAdapter

        sources["greenhouse"] = GreenhouseAdapter()

    if _env_flag("DISCOVERY_LEVER_ENABLED", default=True):
        from src.discovery.lever.adapter import LeverAdapter

        sources["lever"] = LeverAdapter()

    if _env_flag("DISCOVERY_REMOTEOK_ENABLED", default=True):
        from src.discovery.remoteok.adapter import RemoteOKAdapter

        sources["remoteok"] = RemoteOKAdapter()

    if _env_flag("DISCOVERY_HIMALAYAS_ENABLED", default=True):
        from src.discovery.himalayas.adapter import HimalayasAdapter

        sources["himalayas"] = HimalayasAdapter()

    if _env_flag("DISCOVERY_WELLFOUND_ENABLED", default=True):
        from src.discovery.wellfound.adapter import WellfoundAdapter

        sources["wellfound"] = WellfoundAdapter()

    if _env_flag("DISCOVERY_YC_ENABLED", default=True):
        from src.discovery.yc.adapter import YCAdapter

        sources["yc"] = YCAdapter()

    if _env_flag("DISCOVERY_LINKEDIN_ENABLED", default=True):
        from src.discovery.linkedin.adapter import LinkedInAdapter

        sources["linkedin"] = LinkedInAdapter()

    if _env_flag("DISCOVERY_INDEED_ENABLED", default=True):
        from src.discovery.indeed.adapter import IndeedAdapter

        sources["indeed"] = IndeedAdapter()

    if _env_flag("DISCOVERY_OTTA_ENABLED", default=True):
        from src.discovery.otta.adapter import OttaAdapter

        sources["otta"] = OttaAdapter()

    if _env_flag("DISCOVERY_ARC_ENABLED", default=True):
        from src.discovery.arc.adapter import ArcAdapter

        sources["arc"] = ArcAdapter()

    if _env_flag("DISCOVERY_CONTRA_ENABLED", default=True):
        from src.discovery.contra.adapter import ContraAdapter

        sources["contra"] = ContraAdapter()

    if _env_flag("DISCOVERY_COMPANY_CAREER_ENABLED", default=True):
        from src.discovery.company_career.adapter import CompanyCareerAdapter

        sources["company_career"] = CompanyCareerAdapter()

    _SOURCES = sources
    logger.info("discovery.registry.loaded", sources=list(sources.keys()))
    return sources


def reset_registry() -> None:
    """Clear the cached registry. Intended for tests only."""
    global _SOURCES
    _SOURCES = None
