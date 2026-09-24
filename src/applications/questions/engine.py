"""Answer application questions with answer-bank first, then DeepSeek + validation."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.applications.models import Application
from src.applications.questions.classifier import HARD_EXCLUDED, QuestionCategory, classify
from src.applications.schemas import AnsweredQuestion
from src.candidate.answers.answer_bank import lookup
from src.llm.deepseek.client import DeepSeekClient
from src.llm.prompts.question_answer import build_prompt
from src.llm.retrieval.retriever import retrieve
from src.llm.validation.claim_extractor import extract_claims
from src.llm.validation.evidence_validator import validate
from src.observability.logging import get_logger
from src.jobs.models import Job
from sqlalchemy import select

logger = get_logger(__name__)


async def answer(
    db: AsyncSession,
    question: str,
    application: Application,
    *,
    client: DeepSeekClient | None = None,
) -> AnsweredQuestion:
    """Answer *question* for *application*.

    1. Answer-bank lookup
    2. Hard-excluded categories → require pre-configured answer or flag missing
    3. DeepSeek generation + claim extraction + evidence validation
    """
    category = classify(question)

    known = await lookup(db, question)
    if known is not None:
        return AnsweredQuestion(
            question=question,
            answer=known,
            category=category.value,
            validated=True,
            source="known_answer",
        )

    if category in HARD_EXCLUDED:
        logger.warning(
            "question.hard_excluded_no_answer",
            category=category.value,
            question=question[:80],
        )
        return AnsweredQuestion(
            question=question,
            answer="",
            category=category.value,
            validated=False,
            source="manual",
        )

    # Load the job for retrieval context.
    result = await db.execute(select(Job).where(Job.id == application.job_id))
    job = result.scalar_one_or_none()
    if job is None:
        return AnsweredQuestion(
            question=question,
            answer="",
            category=category.value,
            validated=False,
            source="manual",
        )

    facts = await retrieve(db, job, question=question)
    prompt = build_prompt(question, facts, category=category.value)
    ds = client or DeepSeekClient()

    try:
        raw = await ds.complete(prompt)
        text = str(raw).strip()
    except Exception as exc:
        logger.error("question.generate.failed", error=str(exc))
        return AnsweredQuestion(
            question=question,
            answer="",
            category=category.value,
            validated=False,
            source="manual",
        )

    claims = extract_claims(text)
    verdict = validate(claims, facts)
    if verdict.all_accepted:
        return AnsweredQuestion(
            question=question,
            answer=text,
            category=category.value,
            validated=True,
            source="generated",
        )

    if verdict.needs_rewrite:
        constraints = []
        for v in verdict.verdicts:
            if v.rewrite_to_level:
                constraints.append(
                    f'Use evidence level "{v.rewrite_to_level}" for: {v.claim.text[:120]}'
                )
        rewrite_prompt = (
            "Rewrite the answer so factual claims match the allowed evidence levels. "
            "Do not invent new claims.\n"
            + "\n".join(constraints)
            + f"\n\nAnswer:\n{text}"
        )
        try:
            raw2 = await ds.complete(rewrite_prompt)
            text2 = str(raw2).strip()
            verdict2 = validate(extract_claims(text2), facts)
            if verdict2.all_accepted:
                return AnsweredQuestion(
                    question=question,
                    answer=text2,
                    category=category.value,
                    validated=True,
                    source="generated",
                )
            text = text2
            verdict = verdict2
        except Exception as exc:
            logger.warning("question.rewrite.failed", error=str(exc))

    logger.info(
        "question.validation_failed",
        application_id=str(application.id),
        outcomes=[v.outcome.value for v in verdict.verdicts],
    )
    return AnsweredQuestion(
        question=question,
        answer=text,
        category=category.value,
        validated=False,
        source="generated",
    )
