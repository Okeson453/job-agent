"""Detect form fields, fill, upload CV, submit. Explicit timeouts on every step."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from src.applications.browser.field_mapper import FormField, map_fields
from src.applications.schemas import SubmissionResult
from src.candidate.schemas import CandidateProfile
from src.observability.logging import get_logger

logger = get_logger(__name__)

_NAV_TIMEOUT_MS = 30_000
_ACTION_TIMEOUT_MS = 15_000


async def submit(
    page: Page,
    application_url: str,
    candidate: CandidateProfile,
    *,
    cv_path: str | None = None,
    cover_letter: str | None = None,
    extra_answers: dict[str, str] | None = None,
    require_cv: bool = True,
    resolve_answer: Callable[[str], Awaitable[str | None]] | None = None,
) -> SubmissionResult:
    """Navigate to the application URL, fill detected fields, and submit.

    *extra_answers* maps field name/label → text for fields the mapper could
    not fill from the profile (answered via the Application Question Engine).

    *resolve_answer*, when provided, is called for required unmapped fields
    still missing an answer — this is the question-engine wiring path.

    On any failure captures screenshot + DOM before returning a failed result.
    """
    screenshot_path: str | None = None
    dom_path: str | None = None

    try:
        await page.goto(
            application_url,
            wait_until="domcontentloaded",
            timeout=_NAV_TIMEOUT_MS,
        )

        fields = await _detect_fields(page)
        mapped, unmapped = map_fields(
            fields, candidate, cover_letter=cover_letter, cv_path=cv_path
        )

        extras = {k.lower(): v for k, v in (extra_answers or {}).items() if v}

        for name, value in mapped.items():
            await _fill_field(page, name, value)

        # Fill unmapped fields from precomputed question-engine answers, then
        # resolve remaining required fields through resolve_answer (engine path).
        still_unmapped: list[str] = []
        for field in unmapped:
            key = (field.name or field.label or "").strip()
            if not key:
                continue
            label = (field.label or field.name or key).strip()
            answer = (
                extras.get(key.lower())
                or extras.get(label.lower())
                or extras.get((field.name or "").lower())
            )
            if not answer and resolve_answer is not None and field.required:
                try:
                    answer = await resolve_answer(label)
                    if answer:
                        extras[label.lower()] = answer
                        extras[key.lower()] = answer
                except Exception as exc:
                    logger.warning(
                        "form_filler.resolve_answer.failed",
                        field=label,
                        error=str(exc),
                    )
            if answer:
                await _fill_field(page, field.name or key, answer)
            elif field.required:
                still_unmapped.append(key)

        if still_unmapped:
            logger.warning(
                "form_filler.required_unmapped",
                fields=still_unmapped[:10],
            )
            return SubmissionResult(
                success=False,
                error=f"Required unmapped fields without answers: {still_unmapped[:5]}",
            )

        if require_cv and (not cv_path or not Path(cv_path).exists()):
            return SubmissionResult(
                success=False,
                error="CV required but path missing or file not found",
            )
        if cv_path and Path(cv_path).exists():
            await _upload_file(page, cv_path)

        submitted = await _click_submit(page)
        if not submitted:
            return SubmissionResult(
                success=False,
                error="No submit button found or click failed",
            )

        await asyncio.sleep(2)
        landing = page.url.lower()
        body = ""
        try:
            body = (await page.content()).lower()
        except Exception:
            body = ""
        error_signals = (
            "captcha",
            "please try again",
            "something went wrong",
            "error submitting",
            "unable to submit",
        )
        if any(sig in landing or sig in body for sig in error_signals):
            return SubmissionResult(
                success=False,
                error="Post-submit page looks like an error",
                confirmation_id=page.url,
            )
        thanks = ("thank", "received", "application submitted", "we got your", "successfully applied")
        confirmed = any(tok in body for tok in thanks) or any(
            tok in landing for tok in ("thank", "success", "confirmation", "applied")
        )
        if not confirmed:
            return SubmissionResult(
                success=False,
                error="Post-submit page did not confirm application",
                confirmation_id=page.url,
            )
        return SubmissionResult(
            success=True,
            confirmation_id=page.url,
        )

    except Exception as exc:
        try:
            from datetime import datetime, timezone
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            art = Path(__file__).resolve().parents[3] / "artifacts" / "browser"
            art.mkdir(parents=True, exist_ok=True)
            screenshot_path = str(art / f"screenshot_{ts}.png")
            await page.screenshot(path=screenshot_path, full_page=True)
            dom_content = await page.content()
            dom_path = str(art / f"dom_{ts}.html")
            Path(dom_path).write_text(dom_content, encoding="utf-8")
        except Exception:
            logger.warning("form_filler.capture_failed")
        logger.error("form_filler.failed", error=str(exc))
        return SubmissionResult(
            success=False,
            error=str(exc),
            screenshot_path=screenshot_path,
            dom_path=dom_path,
        )


async def _detect_fields(page: Page) -> list[FormField]:
    """Detect input/textarea/select fields on the current page."""
    fields: list[FormField] = []
    inputs = await page.query_selector_all("input, textarea, select")
    for el in inputs:
        name = await el.get_attribute("name") or await el.get_attribute("id") or ""
        if not name:
            continue
        tag = await el.evaluate("e => e.tagName.toLowerCase()")
        input_type = (await el.get_attribute("type") or "text").lower()
        if input_type in ("hidden", "submit", "button", "image"):
            continue
        label = ""
        try:
            label_id = await el.get_attribute("aria-label") or ""
            label = label_id
        except Exception:
            label = ""
        required = await el.get_attribute("required") is not None
        fields.append(
            FormField(
                name=name,
                field_type=input_type if tag == "input" else tag,
                label=label,
                required=required,
            )
        )
    return fields


async def _fill_field(page: Page, name: str, value: str) -> None:
    selectors = [
        f'[name="{name}"]',
        f"#{name}",
        f'[id="{name}"]',
    ]
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el is None:
                continue
            tag = await el.evaluate("e => e.tagName.toLowerCase()")
            input_type = (await el.get_attribute("type") or "").lower()
            if tag == "select":
                await el.select_option(label=value, timeout=_ACTION_TIMEOUT_MS)
            elif input_type in ("checkbox", "radio"):
                truthy = value.lower() in ("1", "true", "yes", "on", "checked")
                checked = await el.is_checked()
                if truthy and not checked:
                    await el.check(timeout=_ACTION_TIMEOUT_MS)
                elif not truthy and checked:
                    await el.uncheck(timeout=_ACTION_TIMEOUT_MS)
            else:
                await el.fill(value, timeout=_ACTION_TIMEOUT_MS)
            return
        except PlaywrightTimeout:
            continue
        except Exception:
            continue


async def _upload_file(page: Page, path: str) -> None:
    for sel in [
        'input[type="file"]',
        'input[name*="resume" i]',
        'input[name*="cv" i]',
        'input[name*="file" i]',
    ]:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.set_input_files(path, timeout=_ACTION_TIMEOUT_MS)
                return
        except Exception:
            continue


async def _click_submit(page: Page) -> bool:
    selectors = [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Submit")',
        'button:has-text("Apply")',
        'button:has-text("Send")',
    ]
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.click(timeout=_ACTION_TIMEOUT_MS)
                return True
        except Exception:
            continue
    return False
