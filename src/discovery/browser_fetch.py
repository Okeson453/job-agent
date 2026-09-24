"""Playwright helper for public job-listing pages.

Policy: navigate publicly reachable URLs only. If a page requires login,
CAPTCHA, or anti-bot challenge, log and return empty — never solve or bypass.
"""

from __future__ import annotations

from typing import Any

from src.observability.logging import get_logger
from src.security.allowlist import is_allowed

logger = get_logger(__name__)


async def fetch_listing_html(
    url: str,
    *,
    wait_selector: str | None = None,
    timeout_ms: int = 25000,
) -> str | None:
    """Return page HTML for a listing URL, or None if blocked/unavailable."""
    if not is_allowed(url):
        logger.warning("browser_fetch.allowlist_blocked", url=url)
        return None
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("browser_fetch.playwright_missing")
        return None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
            )
            page = await context.new_page()
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            if resp is not None and resp.status in (401, 403, 429, 503):
                logger.warning(
                    "browser_fetch.blocked",
                    url=url,
                    status=resp.status,
                    reason="access restricted; no bypass attempted",
                )
                await browser.close()
                return None
            body_text = (await page.content()).lower()
            if any(
                tok in body_text
                for tok in ("captcha", "cf-challenge", "verify you are human", "access denied")
            ):
                logger.warning(
                    "browser_fetch.challenge_detected",
                    url=url,
                    reason="bot challenge present; stopping",
                )
                await browser.close()
                return None
            if wait_selector:
                try:
                    await page.wait_for_selector(wait_selector, timeout=8000)
                except Exception:
                    pass
            html = await page.content()
            await browser.close()
            return html
    except Exception as exc:
        logger.error("browser_fetch.error", url=url, error=str(exc))
        return None


def extract_cards(html: str, card_selector: str) -> list[Any]:
    from selectolax.parser import HTMLParser

    tree = HTMLParser(html)
    return tree.css(card_selector)
