"""Indeed adapter (permitted public endpoints only)."""

from src.discovery.indeed.adapter import IndeedAdapter
from src.discovery.indeed.parser import parse

__all__ = ["IndeedAdapter", "parse"]
