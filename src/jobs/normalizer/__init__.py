"""Source-specific raw dict → JobCreate normalization."""

from src.jobs.normalizer.normalizer import normalize, register_parser

__all__ = ["normalize", "register_parser"]
