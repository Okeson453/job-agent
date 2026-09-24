"""Wellfound adapter (permitted endpoints only)."""

from src.discovery.wellfound.adapter import WellfoundAdapter
from src.discovery.wellfound.parser import parse

__all__ = ["WellfoundAdapter", "parse"]
