"""Per-company career page configs for static HTML list pages.

Prefer dedicated ATS adapters (Greenhouse/Lever) when available. These entries
are public careers indexes polled with httpx + selectolax only.
"""

from __future__ import annotations

from typing import Any

SITE_CONFIGS: dict[str, dict[str, Any]] = {
    "stripe.com": {
        "list_url": "https://stripe.com/jobs/search",
        "job_link_selector": "a[href*='/jobs/listing/']",
    },
    "vercel.com": {
        "list_url": "https://vercel.com/careers",
        "job_link_selector": "a[href*='/careers/']",
    },
    "cloudflare.com": {
        "list_url": "https://www.cloudflare.com/careers/jobs/",
        "job_link_selector": "a[href*='/careers/jobs/']",
    },
}
