"""Cover letter template fallback when LLM raises."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.applications.documents.cover_letter import _template_letter, generate


def test_template_letter_non_empty():
    job = SimpleNamespace(title="Backend Engineer", company="Acme", technologies=["python", "redis"])
    text = _template_letter(job, [])
    assert "Backend Engineer" in text
    assert "Acme" in text
    assert len(text) > 40


@pytest.mark.asyncio
async def test_generate_returns_template_on_exception():
    job = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        title="Platform Engineer",
        company="Widgets",
        technologies=["python"],
        description="remote python",
    )
    client = AsyncMock()
    client.complete = AsyncMock(side_effect=RuntimeError("402 Insufficient Balance"))
    text, ok = await generate(job, [], client=client)
    assert ok is True
    assert text
    assert "Platform Engineer" in text
