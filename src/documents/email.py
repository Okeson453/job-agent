"""Draft a job-specific application email.

Two rules decide everything here:

* Only a recruitment address that the employer published in the job posting is
  used. Nothing is guessed from a domain.
* The draft is never sent. It is shown to the operator, who sends it manually.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from src.documents.grounding import unsupported_terms
from src.documents.kb import CandidateKB
from src.documents.tailoring import CVPlan
from src.jobs.models import Job
from src.llm.deepseek.client import DeepSeekClient
from src.llm.prompts.application_email import build_prompt
from src.observability.logging import get_logger

logger = get_logger(__name__)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# Addresses that are never a route to a hiring team.
_BLOCKED_LOCAL = {
    "noreply", "no-reply", "donotreply", "do-not-reply", "postmaster",
    "support", "help", "helpdesk", "privacy", "legal", "abuse", "unsubscribe",
    "webmaster", "billing", "payments", "press", "security",
}

# Job boards and vendors whose addresses appear in scraped text.
_BLOCKED_DOMAINS = {
    "ioassociates.co.uk", "expertwoka.com", "turing.com", "micro1.ai",
    "example.com", "sentry.io", "wixpress.com", "godaddy.com",
    "cloudflare.com", "sentry-next.wixpress.com", "email.com",
}

_CONTEXT_WORDS = (
    "apply", "application", "apply now", "recruit", "hiring", "send",
    "cv", "resume", "résumé", "career", "vacanc", "contact",
)

_RECRUITMENT_LOCAL = re.compile(
    r"^(hr|jobs?|careers?|recruit(ing|ment)?|talent|hiring|apply|people)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EmailDraft:
    to: str
    subject: str
    body: str

    def as_text(self) -> str:
        return f"To: {self.to}\nSubject: {self.subject}\n\n{self.body}\n"


def _context_ok(text: str, start: int, end: int) -> bool:
    window = text[max(0, start - 160) : end + 160].lower()
    return any(word in window for word in _CONTEXT_WORDS)


def find_recruitment_email(job: Job) -> str | None:
    """Return a public recruitment address from the posting, if there is one."""
    text = job.description or ""
    if not text:
        return None

    for match in _EMAIL_RE.finditer(text):
        address = match.group(0).rstrip(".,;:)")
        local, _, domain = address.partition("@")
        local_key = local.lower()
        domain_key = domain.lower().lstrip(".")

        if domain_key in _BLOCKED_DOMAINS:
            continue
        if local_key in _BLOCKED_LOCAL:
            continue
        if any(domain_key.endswith("." + blocked) for blocked in _BLOCKED_DOMAINS):
            continue
        if domain_key.startswith("www."):
            domain_key = domain_key[4:]

        if _RECRUITMENT_LOCAL.search(local_key):
            return address
        if _context_ok(text, match.start(), match.end()):
            return address

    return None


def _fallback_body(job: Job, kb: CandidateKB, plan: CVPlan) -> str:
    pool = dict(kb.bullet_pool())
    highlights = [
        pool[bid] for bid in plan.experience_bullet_ids if bid in pool
    ][:2]
    lines = [
        "Dear Hiring Team,",
        "",
        f"I am applying for the {job.title} role at {job.company}.",
        "",
        plan.summary,
        "",
    ]
    if highlights:
        lines.append("Relevant to this role:")
        lines.extend(f"- {item}" for item in highlights)
        lines.append("")
    lines.append(
        f"I have attached my tailored CV. I am based in {kb.location or 'Nigeria'} "
        f"({kb.timezone or 'Africa/Lagos'}) and can work remotely or overlap with "
        "your core hours."
    )
    lines.extend(
        [
            "",
            "Best regards,",
            kb.name,
            kb.email,
        ]
    )
    if kb.phone:
        lines.append(kb.phone)
    return "\n".join(line for line in lines if line is not None).strip()


def _body_is_acceptable(body: str, job: Job, kb: CandidateKB) -> bool:
    if len(body) < 120:
        return False
    # Quoting the posting's own title/company must not trip the grounding check.
    probe = body.replace(job.title or "", " ").replace(job.company or "", " ")
    return not unsupported_terms(probe, kb)


async def draft_application_email(
    job: Job,
    kb: CandidateKB,
    plan: CVPlan,
    *,
    client: DeepSeekClient | None = None,
) -> EmailDraft | None:
    """Return a draft when the posting publishes a recruitment address."""
    recipient = find_recruitment_email(job)
    if recipient is None:
        logger.info("email.no_recruitment_address", job_id=str(job.id))
        return None

    subject = f"Application: {job.title} — {kb.name}"
    prompt = build_prompt(job, kb, plan, recipient)

    try:
        ds = client or DeepSeekClient()
        raw = await ds.complete(prompt, temperature=0.4, max_tokens=700)
        body = str(raw).strip()
        if _body_is_acceptable(body, job, kb):
            logger.info("email.drafted", job_id=str(job.id), recipient=recipient)
            return EmailDraft(to=recipient, subject=subject, body=body)
        logger.warning("email.rejected_by_grounding", job_id=str(job.id))
    except Exception as exc:
        logger.warning("email.draft_failed", job_id=str(job.id), error=str(exc)[:200])

    return EmailDraft(to=recipient, subject=subject, body=_fallback_body(job, kb, plan))


def write_email_file(draft: EmailDraft, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(draft.as_text(), encoding="utf-8")
    return path
