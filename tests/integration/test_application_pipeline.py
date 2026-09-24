"""Application pipeline gate: overstated application text fails validation.

Phase 5 checklist: the evidence gate must hold through cover-letter style text,
not only on isolated claim objects.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from src.candidate.schemas import CandidateFactRead
from src.llm.validation.claim_extractor import extract_claims
from src.llm.validation.evidence_validator import ValidationOutcome, validate


def _fact(
    fact: str,
    value: str,
    evidence_level: str,
    *,
    project: str | None = None,
    technologies: list[str] | None = None,
) -> CandidateFactRead:
    return CandidateFactRead(
        id=uuid.uuid4(),
        category="architecture",
        fact=fact,
        value=value,
        evidence_level=evidence_level,
        source_document="projects/TestingEngine/architecture.md",
        verified=True,
        metadata={
            "project": project or "TestingEngine",
            "technologies": technologies or ["TypeScript", "PostgreSQL"],
        },
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_cover_letter_style_overstated_claim_blocked() -> None:
    letter = (
        "I built and deployed the TestingEngine execution state machine to "
        "production and shipped it to live trading accounts."
    )
    facts = [
        _fact(
            "Designed a ten-layer execution state machine for TestingEngine",
            "Architecture specifies transitions; production deployment not claimed.",
            "designed",
        )
    ]
    claims = extract_claims(letter)
    assert claims, "claim extractor should find deployment language"
    result = validate(claims, facts)
    assert result.all_accepted is False
    outcomes = {v.outcome for v in result.verdicts}
    assert (
        ValidationOutcome.UNSUPPORTED in outcomes
        or ValidationOutcome.NEEDS_REWRITE in outcomes
    )


def test_designed_language_passes_with_designed_evidence() -> None:
    letter = (
        "I designed the TestingEngine execution state machine architecture "
        "and specified the transition rules."
    )
    facts = [
        _fact(
            "Designed a ten-layer execution state machine for TestingEngine",
            "Architecture specifies a ten-layer execution state machine.",
            "designed",
        )
    ]
    claims = extract_claims(letter)
    result = validate(claims, facts)
    assert not result.empty_claims or claims
    # Designed language against designed evidence must not be pure UNSUPPORTED.
    if result.verdicts:
        assert any(
            v.outcome in (ValidationOutcome.ACCEPTED, ValidationOutcome.NEEDS_REWRITE)
            for v in result.verdicts
        )
