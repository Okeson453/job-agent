"""Playwright browser automation for form filling and submission."""

from src.applications.browser.field_mapper import FormField, map_fields

__all__ = [
    "FormField",
    "map_fields",
]

# Heavy Playwright imports are optional at package import time.
try:
    from src.applications.browser.form_filler import submit
    from src.applications.browser.session import close_browser, open_context

    __all__ += ["close_browser", "open_context", "submit"]
except ImportError:  # pragma: no cover
    pass
