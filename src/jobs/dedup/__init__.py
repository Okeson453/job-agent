"""Job deduplication (Redis fast path + DB fallback)."""

from src.jobs.dedup.deduplicator import is_duplicate, remember

__all__ = ["is_duplicate", "remember"]
