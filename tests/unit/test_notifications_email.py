"""Application email drafting and Telegram delivery behaviour."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "t")
os.environ.setdefault("TELEGRAM_CHAT_ID", "0")
os.environ.setdefault("ENCRYPTION_KEY", "QUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUE=")

from apps.worker.notification_worker import _format_email, _format_opportunity
from src.documents.email import draft_application_email, find_recruitment_email
from src.documents.kb import load_kb
from src.documents.tailoring import deterministic_plan
from src.jobs.models import Job
from src.telegram.notifier import (
    MAX_MESSAGE_CHARS,
    TelegramError,
    send_document,
    send_message,
    split_message,
)


def make_job(description: str, **overrides) -> Job:
    defaults = {
        "id": uuid.uuid4(),
        "source": "expertwoka",
        "external_id": str(uuid.uuid4()),
        "title": "Backend Engineer",
        "company": "Acme Payments",
        "description": description,
        "application_url": "https://example.org/jobs/1",
        "remote": True,
        "location": "Remote",
    }
    defaults.update(overrides)
    return Job(**defaults)


@pytest.fixture(scope="module")
def kb():
    return load_kb()


# --------------------------------------------------------------------------- #
# Recruitment address detection
# --------------------------------------------------------------------------- #


def test_finds_published_recruitment_email():
    job = make_job("Send your CV and cover letter to talent@acme-payments.com today.")
    assert find_recruitment_email(job) == "talent@acme-payments.com"


def test_rejects_generic_and_platform_addresses():
    assert find_recruitment_email(make_job("Questions? support@acme.com")) is None
    assert find_recruitment_email(make_job("Contact privacy@acme.com for details")) is None
    assert find_recruitment_email(make_job("Apply via jobs@expertwoka.com")) is None
    assert find_recruitment_email(make_job("Apply via jobs@ioassociates.co.uk")) is None


def test_rejects_address_without_application_context():
    job = make_job("Our office manager maria@acme.com joined in 2019.")
    assert find_recruitment_email(job) is None


def test_accepts_hr_address_without_context():
    assert find_recruitment_email(make_job("Write to hr@acme.com.")) == "hr@acme.com"


# --------------------------------------------------------------------------- #
# Drafting
# --------------------------------------------------------------------------- #


async def test_draft_uses_grounded_llm_body(kb):
    job = make_job("Email your CV to careers@acme.com. Node.js and PostgreSQL.")

    class GoodClient:
        async def complete(self, prompt, schema=None, **kwargs):
            return (
                "Dear Hiring Team,\n\n"
                "I am applying for the Backend Engineer role at Acme Payments. "
                "I build Node.js and PostgreSQL services and have delivered "
                "real-time systems with Redis-backed caching.\n\n"
                "My tailored CV is attached. I am based in Abuja, Nigeria "
                "(Africa/Lagos) and can overlap with your core hours.\n\n"
                "Best regards,\nKomolafe Eniola Samuel"
            )

    draft = await draft_application_email(job, kb, deterministic_plan(job, kb), client=GoodClient())
    assert draft is not None
    assert draft.to == "careers@acme.com"
    assert "Backend Engineer" in draft.subject
    assert "Node.js" in draft.body


async def test_draft_falls_back_when_body_is_fabricated(kb):
    job = make_job("Email your CV to careers@acme.com.")

    class Liar:
        async def complete(self, prompt, schema=None, **kwargs):
            return (
                "Dear Hiring Team, I am a Principal Salesforce architect with "
                "12 years at Google. My tailored CV is attached."
            )

    draft = await draft_application_email(job, kb, deterministic_plan(job, kb), client=Liar())
    assert draft is not None
    assert "Salesforce" not in draft.body
    assert "Google" not in draft.body
    assert kb.name in draft.body


async def test_draft_skipped_without_public_address(kb):
    job = make_job("Apply through our portal. No email listed.")
    draft = await draft_application_email(job, kb, deterministic_plan(job, kb))
    assert draft is None


# --------------------------------------------------------------------------- #
# Telegram formatting and sending
# --------------------------------------------------------------------------- #


def test_card_shows_email_and_attachment_names_not_paths(kb):
    job = make_job("Email your CV to careers@acme.com.")
    draft = {"to": "careers@acme.com", "subject": "Application: Backend Engineer", "body": "Hi"}
    text = _format_opportunity(
        job,
        None,
        "app-123",
        cv_pdf="/app/data/generated/cv/komolafe-cv-acme.pdf",
        cv_docx="/app/data/generated/cv/komolafe-cv-acme.docx",
        email_draft=draft,
    )
    assert "careers@acme.com" in text
    assert "komolafe-cv-acme.pdf" in text
    assert "/app/data/generated" not in text
    assert "/applied app-123" in text


def test_card_escapes_scraped_markup():
    job = make_job("Normal text", title="Engineer <script>alert(1)</script>")
    text = _format_opportunity(job, None, "app-1")
    assert "<script>" not in text
    assert "&lt;script&gt;" in text


def test_email_message_contains_subject_and_body():
    job = make_job("Email your CV to careers@acme.com.")
    text = _format_email(
        job,
        {"to": "careers@acme.com", "subject": "Application: Backend Engineer", "body": "Dear team,\n\nHello."},
    )
    assert "careers@acme.com" in text
    assert "Application: Backend Engineer" in text
    assert "Dear team" in text


def test_split_message_respects_limit():
    text = "\n".join(f"line {i} " + "x" * 80 for i in range(100))
    chunks = split_message(text)
    assert len(chunks) > 1
    assert all(len(chunk) <= MAX_MESSAGE_CHARS for chunk in chunks)
    joined = "\n".join(chunks)
    assert "line 0" in joined and "line 99" in joined


async def test_send_message_chunks_and_posts_each(monkeypatch):
    calls: list[dict] = []

    async def fake_post(method, *, data, files=None):
        calls.append({"method": method, "data": data})

    monkeypatch.setattr("src.telegram.notifier._post", fake_post)
    long_text = "\n".join("y" * 100 for _ in range(80))
    await send_message(long_text)
    assert len(calls) > 1
    assert all(call["method"] == "sendMessage" for call in calls)


async def test_send_document_uploads_file(monkeypatch, tmp_path: Path):
    path = tmp_path / "cv.pdf"
    path.write_bytes(b"%PDF-1.4 test")
    seen: dict = {}

    async def fake_post(method, *, data, files=None):
        seen["method"] = method
        seen["data"] = data
        seen["filename"] = files["document"][0]
        seen["bytes"] = files["document"][1].read()

    monkeypatch.setattr("src.telegram.notifier._post", fake_post)
    await send_document(path, caption="Tailored CV")
    assert seen["method"] == "sendDocument"
    assert seen["filename"] == "cv.pdf"
    assert seen["bytes"].startswith(b"%PDF")


async def test_send_document_rejects_missing_file(tmp_path: Path):
    with pytest.raises(TelegramError):
        await send_document(tmp_path / "nope.pdf")
