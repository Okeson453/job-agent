"""Per-company career page configs.

Only real public list URLs. Adapters must respect robots and rate limits.
Empty SITE_CONFIGS means the company_career source discovers nothing until
configured — preferred over fake example.com entries.
"""

from __future__ import annotations

from typing import Any

# Populate with real careers hosts you have permission to poll.
# Example shape (disabled by default — enable by adding entries):
#   "boards.greenhouse.io": {...}  # prefer the dedicated Greenhouse adapter
SITE_CONFIGS: dict[str, dict[str, Any]] = {}
