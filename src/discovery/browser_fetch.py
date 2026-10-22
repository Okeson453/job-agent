"""Playwright/HTTP helpers for public job-listing pages.

Policy: navigate publicly reachable URLs only. If a page requires login,
CAPTCHA, or an anti-bot challenge, log and return empty — never solve or
bypass anything. Scraped markup is untrusted data; it is never executed and
never treated as instructions.
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.observability.logging import get_logger
from src.security.allowlist import is_allowed

logger = get_logger(__name__)

_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

_BLOCK_STATUS = frozenset({401, 403, 429, 503})

# Titles used by challenge/interstitial pages. Checked against <title> only,
# so third-party scripts (e.g. recaptcha badges) do not trip detection.
_BLOCK_TITLES = (
    "attention required",
    "just a moment",
    "access denied",
    "please verify you are a human",
    "checking your browser",
)

# Only match phrases that appear as visible challenge copy.
_BLOCK_TEXT = (
    "verify you are human",
    "checking your browser before accessing",
    "attention required! | cloudflare",
    "enable javascript and cookies to continue",
)

_CHALLENGE_SELECTORS = "#challenge-form, #cf-challenge-running, [name=cf_chl_opt]"


def _looks_blocked(title: str, body_text: str) -> bool:
    t = (title or "").lower()
    if any(marker in t for marker in _BLOCK_TITLES):
        return True
    snippet = (body_text or "")[:3000].lower()
    return any(marker in snippet for marker in _BLOCK_TEXT)


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
                user_agent=_UA,
                viewport={"width": 1280, "height": 800},
            )
            page = await context.new_page()
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            if resp is not None and resp.status in _BLOCK_STATUS:
                logger.warning(
                    "browser_fetch.blocked",
                    url=url,
                    status=resp.status,
                    reason="access restricted; no bypass attempted",
                )
                await browser.close()
                return None
            if await _is_challenged(page):
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


async def render_pages(
    urls: list[str],
    *,
    wait_selector: str | None = None,
    settle_ms: int = 1500,
    timeout_ms: int = 30000,
) -> list[str | None]:
    """Render several listing URLs in one browser session.

    Returns HTML aligned with ``urls``; blocked or failed pages map to None so
    a single bad page cannot abort the whole source.
    """
    results: list[str | None] = [None] * len(urls)
    allowed = [(i, u) for i, u in enumerate(urls) if is_allowed(u)]
    for i, url in enumerate(urls):
        if (i, url) not in allowed:
            logger.warning("browser_fetch.allowlist_blocked", url=url)

    if not allowed:
        return results

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("browser_fetch.playwright_missing")
        return results

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                user_agent=_UA,
                viewport={"width": 1400, "height": 1000},
            )
            page = await context.new_page()
            for index, url in allowed:
                try:
                    resp = await page.goto(
                        url, wait_until="domcontentloaded", timeout=timeout_ms
                    )
                    if resp is not None and resp.status in _BLOCK_STATUS:
                        logger.warning(
                            "browser_fetch.blocked", url=url, status=resp.status
                        )
                        continue
                    if wait_selector:
                        try:
                            await page.wait_for_selector(wait_selector, timeout=8000)
                        except Exception:
                            pass
                    await page.wait_for_timeout(settle_ms)
                    if await _is_challenged(page):
                        logger.warning("browser_fetch.challenge_detected", url=url)
                        continue
                    results[index] = await page.content()
                except Exception as exc:
                    logger.warning("browser_fetch.page_error", url=url, error=str(exc))
            await browser.close()
    except Exception as exc:
        logger.error("browser_fetch.error", url=";".join(urls)[:200], error=str(exc))
    return results


async def render_with_clicks(
    url: str,
    *,
    card_selector: str,
    click_selector: str | None = None,
    click_text: str | None = None,
    max_clicks: int = 3,
    wait_selector: str | None = None,
    settle_ms: int = 1200,
    timeout_ms: int = 30000,
) -> str | None:
    """Render a listing and click a "load more" control repeatedly.

    Stops when the control disappears, stops yielding new cards, or the click
    budget is exhausted. Never interacts with login/CAPTCHA elements.
    """
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
                user_agent=_UA,
                viewport={"width": 1400, "height": 1000},
            )
            page = await context.new_page()
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            if resp is not None and resp.status in _BLOCK_STATUS:
                logger.warning("browser_fetch.blocked", url=url, status=resp.status)
                await browser.close()
                return None
            if wait_selector:
                try:
                    await page.wait_for_selector(wait_selector, timeout=8000)
                except Exception:
                    pass
            await page.wait_for_timeout(settle_ms)
            if await _is_challenged(page):
                logger.warning("browser_fetch.challenge_detected", url=url)
                await browser.close()
                return None

            cards = await page.query_selector_all(card_selector)
            count = len(cards)
            for _ in range(max_clicks):
                button: Any = None
                if click_text:
                    candidate = page.get_by_role("button", name=click_text, exact=True)
                    try:
                        if await candidate.count() and await candidate.first.is_visible():
                            button = candidate.first
                    except Exception:
                        button = None
                if button is None and click_selector:
                    for element in await page.query_selector_all(click_selector):
                        if await element.is_visible() and await element.is_enabled():
                            button = element
                            break
                if button is None:
                    break
                try:
                    await button.click(timeout=5000)
                except Exception:
                    break
                try:
                    await page.wait_for_function(
                        "([sel, n]) => document.querySelectorAll(sel).length > n",
                        arg=[card_selector, count],
                        timeout=8000,
                    )
                except Exception:
                    # No growth: the list is exhausted for this pass.
                    cards = await page.query_selector_all(card_selector)
                    if len(cards) <= count:
                        break
                cards = await page.query_selector_all(card_selector)
                count = len(cards)
            html = await page.content()
            await browser.close()
            return html
    except Exception as exc:
        logger.error("browser_fetch.error", url=url, error=str(exc))
        return None


async def fetch_static_html(url: str, *, timeout_s: float = 20.0) -> str | None:
    """Fetch server-rendered HTML without a browser.

    Returns None on non-200 responses and on challenge interstitials so the
    caller can fall back or skip the source without parsing a block page.
    """
    if not is_allowed(url):
        logger.warning("browser_fetch.allowlist_blocked", url=url)
        return None
    try:
        import httpx
    except ImportError:
        logger.error("browser_fetch.httpx_missing")
        return None
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout_s,
            headers={"User-Agent": _UA, "Accept": "text/html,application/xhtml+xml"},
        ) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.info("browser_fetch.static_non200", url=url, status=resp.status_code)
                return None
            text = resp.text
            if _looks_blocked("", text[:4000]):
                logger.warning("browser_fetch.static_challenge", url=url)
                return None
            return text
    except Exception as exc:
        logger.warning("browser_fetch.static_error", url=url, error=str(exc))
        return None


async def _is_challenged(page: Any) -> bool:
    try:
        title = await page.title()
    except Exception:
        title = ""
    try:
        body = await page.inner_text("body")
    except Exception:
        body = ""
    if _looks_blocked(title, body):
        return True
    try:
        return await page.query_selector(_CHALLENGE_SELECTORS) is not None
    except Exception:
        return False


def extract_cards(html: str, card_selector: str) -> list[Any]:
    from src.discovery.html import HTMLParser

    tree = HTMLParser(html)
    return tree.css(card_selector)


async def polite_sleep(seconds: float) -> None:
    """Small delay between requests to one source."""
    if seconds > 0:
        await asyncio.sleep(seconds)
