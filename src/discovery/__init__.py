"""Job source adapters and registry."""

from src.discovery.base import JobSource
from src.discovery.registry import get_sources, reset_registry

__all__ = ["JobSource", "get_sources", "reset_registry"]
