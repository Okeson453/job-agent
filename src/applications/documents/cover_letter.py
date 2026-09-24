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
                return (text2, True)
        except Exception as exc:
            logger.warning(
                "cover_letter.rewrite.failed",
                pass_i=pass_i,
                error=str(exc),
            )
            break

    logger.info(
        "cover_letter.validation_issues",
        job_id=str(job.id),
        outcomes=[v.outcome.value for v in result.verdicts],
        empty_claims=result.empty_claims,
    )
    return (text, False)
