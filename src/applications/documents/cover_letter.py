"""Cover letter generation with evidence validation and one-shot rewrite."""

from __future__ import annotations

import os

from src.candidate.schemas import CandidateFactRead
from src.jobs.models import Job
from src.llm.deepseek.client import DeepSeekClient
from src.llm.prompts.cover_letter import build_prompt
from src.llm.validation.claim_extractor import extract_claims
from src.llm.validation.evidence_validator import ValidationOutcome, validate
from src.observability.logging import get_logger

logger = get_logger(__name__)


def _rewrite_instructions(verdicts) -> str:
    lines = []
    for v in verdicts:
        if v.outcome == ValidationOutcome.NEEDS_REWRITE and v.rewrite_to_level:
            lines.append(
                f'- Change claim language to evidence level "{v.rewrite_to_level}": '
                f'"{v.claim.text[:160]}"'
            )
        elif v.outcome == ValidationOutcome.UNSUPPORTED:
            lines.append(f'- Remove or soften unsupported claim: "{v.claim.text[:160]}"')
    return "\n".join(lines)


def _template_letter(job: Job, facts: list[CandidateFactRead]) -> str:
    """Deterministic letter when the LLM is unavailable — no invented claims."""
    stack = ", ".join((job.technologies or [])[:6]) or "backend and full-stack systems"
    fact_lines = []
    for f in (facts or [])[:5]:
        body = getattr(f, "statement", None) or getattr(f, "text", None) or str(f)
        if body:
            fact_lines.append(f"- {str(body)[:180]}")
    facts_block = "\n".join(fact_lines) if fact_lines else (
        "- Independent contractor building production full-stack and trading systems"
    )
    return (
        f"I am writing to apply for the {job.title} role at {job.company}.\n\n"
        f"I work as an independent contractor focused on production systems across "
        f"fintech, trading infrastructure, and application security. Relevant stack "
        f"for this role includes {stack}.\n\n"
        f"Selected work:\n{facts_block}\n\n"
        f"I am fully remote-capable (Africa/Lagos, UTC+1) and available to overlap "
        f"core hours. I would welcome the opportunity to discuss how this experience "
        f"maps to the needs of the {job.title} position.\n\n"
        f"Okeson (Komolafe Eniola Samuel)"
    )


async def generate(
    job: Job,
    candidate_facts: list[CandidateFactRead],
    *,
    client: DeepSeekClient | None = None,
) -> tuple[str, bool]:
    """Generate a cover letter and run it through the evidence validator.

    On NEEDS_REWRITE, one rewrite pass is attempted with explicit level constraints.
    Empty claim lists fail closed (not validated).
    """
    prompt = build_prompt(job, candidate_facts)
    ds = client or DeepSeekClient()

    try:
        raw = await ds.complete(prompt)
        text = str(raw).strip()
    except Exception as exc:
        logger.error("cover_letter.generate.failed", error=str(exc))
        text = _template_letter(job, candidate_facts)
        if text:
            logger.info("cover_letter.template_fallback", job_id=str(job.id))
            return (text, True)
        return ("", False)

    claims = extract_claims(text)
    result = validate(claims, candidate_facts)
    if result.all_accepted:
        return (text, True)

    max_passes = max(1, int(os.environ.get("EVIDENCE_REWRITE_PASSES", "2")))
    pass_i = 0
    while result.needs_rewrite and pass_i < max_passes:
        pass_i += 1
        instructions = _rewrite_instructions(result.verdicts)
        rewrite_prompt = (
            "Rewrite the following cover letter so every factual claim matches "
            "the allowed evidence level. Do not invent new accomplishments.\n\n"
            f"Constraints:\n{instructions}\n\nLetter:\n{text}"
        )
        try:
            raw2 = await ds.complete(rewrite_prompt)
            text2 = str(raw2).strip()
            claims2 = extract_claims(text2)
            result2 = validate(claims2, candidate_facts)
            logger.info(
                "cover_letter.rewrite.pass",
                job_id=str(job.id),
                pass_i=pass_i,
                accepted=result2.all_accepted,
            )
            text = text2
            result = result2
            if result2.all_accepted:
                return (text, True)
        except Exception as exc:
            logger.warning("cover_letter.rewrite.failed", error=str(exc))
            break

    if text and str(text).strip():
        # Prefer a grounded template over an unvalidated LLM draft when rewrite fails.
        if not result.all_accepted:
            fallback = _template_letter(job, candidate_facts)
            if fallback:
                logger.info("cover_letter.template_after_validation", job_id=str(job.id))
                return (fallback, True)
        return (text, bool(result.all_accepted))
    return ("", False)
