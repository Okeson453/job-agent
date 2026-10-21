"""LinkedIn adapter (permitted access only)."""

from src.discovery.linkedin.adapter import LinkedInAdapter
from src.discovery.linkedin.parser import parse

__all__ = ["LinkedInAdapter", "parse"]
