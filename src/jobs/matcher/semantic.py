"""Semantic match analysis via DeepSeek."""

from __future__ import annotations

from src.candidate.schemas import CandidateFactRead
from src.jobs.models import Job
from src.jobs.schemas import MatchResult
from src.llm.deepseek.client import DeepSeekClient
from src.llm.prompts.matching import build_prompt
from src.observability.logging import get_logger

logger = get_logger(__name__)


async def analyze(
    job: Job,
    candidate_facts: list[CandidateFactRead],
    *,
    client: DeepSeekClient | None = None,
) -> MatchResult:
    """Run semantic analysis against the candidate facts.

    Builds the prompt, calls DeepSeek, validates the structured response.
    On repeated malformed responses, falls back to MANUAL_REVIEW recommendation.
    """
    prompt = build_prompt(job, candidate_facts)
    ds = client or DeepSeekClient()

    try:
        result = await ds.complete(prompt, response_schema=MatchResult)
        if isinstance(result, MatchResult):
            return result
        # Unexpected plain string — try one more parse.
        return MatchResult.model_validate_json(str(result))
    except Exception as exc:
        logger.error(
            "semantic.analyze.failed",
            job_id=str(job.id),
            error=str(exc),
        )
        return MatchResult(
            match=0,
            strong_matches=[],
            gaps=["semantic analysis failed"],
            recommendation="REVIEW",
            analysis={"error": str(exc)},
        )
