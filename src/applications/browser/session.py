"""Playwright browser/context lifecycle with domain allowlist enforcement."""

from __future__ import annotations

from playwright.async_api import Browser, BrowserContext, async_playwright

from src.observability.logging import get_logger
from src.security.allowlist import is_allowed

logger = get_logger(__name__)

_playwright = None
_browser: Browser | None = None


async def _get_browser() -> Browser:
    global _playwright, _browser
    if _browser is not None and _browser.is_connected():
        return _browser
    started = await async_playwright().start()
    try:
        browser = await started.chromium.launch(headless=True)
    except Exception:
        await started.stop()
        raise
    _playwright = started
    _browser = browser
    return _browser


async def open_context(storage_state: str | dict | None = None) -> BrowserContext:
    """Launch a fresh, isolated Playwright context per application.

    Domain allowlist is enforced via route interception: any navigation
    to a host not on ALLOWED_DOMAINS is aborted.
    """
    browser = await _get_browser()
    kwargs = {
        "viewport": {"width": 1280, "height": 720},
        "accept_downloads": True,
    }
    if storage_state is not None:
        kwargs["storage_state"] = storage_state
    context = await browser.new_context(**kwargs)

    async def _route_handler(route: object) -> None:
        request = getattr(route, "request", None)
        url = getattr(request, "url", "") if request else ""
        if url and not is_allowed(url):
            logger.warning("browser.allowlist_block", url=url[:120])
            await route.abort()  # type: ignore[attr-defined]
        else:
            await route.continue_()  # type: ignore[attr-defined]

    await context.route("**/*", _route_handler)
    return context


async def close_browser() -> None:
    """Shut down the shared browser and playwright instance."""
    global _playwright, _browser
    if _browser is not None:
        await _browser.close()
        _browser = None
    if _playwright is not None:
        await _playwright.stop()
        _playwright = None
