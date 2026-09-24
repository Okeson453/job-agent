"""Known-answer lookup for common application questions.

Exact hash match first, then token-overlap near match for close phrasings.
"""

from __future__ import annotations

import hashlib
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.candidate.models import CandidateAnswer

_STOP = {"the", "a", "an", "is", "your", "you", "of", "to", "for", "in", "on", "and", "or"}


def normalize_question(text: str) -> str:
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def question_hash(text: str) -> str:
    return hashlib.sha256(normalize_question(text).encode("utf-8")).hexdigest()


def _tokens(text: str) -> set[str]:
    return {w for w in normalize_question(text).split() if w not in _STOP and len(w) > 2}


def _overlap_ratio(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


async def lookup(db: AsyncSession, question: str) -> str | None:
    """Return a pre-approved answer: exact hash, then near token match ≥ 0.75."""
    qh = question_hash(question)
    result = await db.execute(
        select(CandidateAnswer).where(CandidateAnswer.question_hash == qh)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row.answer_text

    q_tokens = _tokens(question)
    if not q_tokens:
        return None

    result = await db.execute(select(CandidateAnswer).limit(200))
    best = None
    best_score = 0.0
    for candidate in result.scalars().all():
        c_tokens = _tokens(candidate.question_text)
        score = _overlap_ratio(q_tokens, c_tokens)
        if score > best_score:
            best_score = score
            best = candidate
    if best is not None and best_score >= 0.75:
        return best.answer_text
    return None


async def store_answer(
    db: AsyncSession,
    question_text: str,
    answer_text: str,
    category: str,
) -> CandidateAnswer:
    qh = question_hash(question_text)
    result = await db.execute(
        select(CandidateAnswer).where(CandidateAnswer.question_hash == qh)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        existing.answer_text = answer_text
        existing.category = category
        existing.question_text = question_text
        await db.flush()
        return existing
    row = CandidateAnswer(
        question_hash=qh,
        question_text=question_text,
        answer_text=answer_text,
        category=category,
    )
    db.add(row)
    await db.flush()
    return row
