"""Unit tests for claim extraction and evidence validation integration."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from src.candidate.schemas import CandidateFactRead
from src.llm.validation.claim_extractor import extract_claims
from src.llm.validation.evidence_validator import (
    ValidationOutcome,
    validate,
)


def _fact(
    *,
    fact: str,
    value: str,
    evidence_level: str,
    project: str | None = None,
    technologies: list[str] | None = None,
) -> CandidateFactRead:
    return CandidateFactRead(
        id=uuid.uuid4(),
        category="architecture",
        fact=fact,
        value=value,
        evidence_level=evidence_level,
        source_document="test.md",
        verified=True,
        metadata={"project": project, "technologies": technologies or []},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestClaimExtractor:
    def test_extracts_designed_claim(self) -> None:
        text = (
            "I designed an event-driven architecture for TestingEngine using TypeScript "
            "and PostgreSQL. The company culture looks strong."
        )
        claims = extract_claims(text)
        assert len(claims) >= 1
        assert any(c.project_ref and c.project_ref.lower() == "testingengine" for c in claims)

    def test_extracts_implemented_marker(self) -> None:
        text = "I built and deployed a production platform for real-time trading."
        claims = extract_claims(text)
        assert any(c.claimed_level == "implemented" for c in claims)

    def test_skips_company_sentences(self) -> None:
        text = "The company is a leader in fintech. Your team is excellent."
        claims = extract_claims(text)
        assert claims == []


class TestEvidenceValidatorIntegration:
    def test_designed_fact_rejects_implemented_claim(self) -> None:
        """Governing principle end-to-end through extractor + validator."""
        text = (
            "I built and deployed TestingEngine as a production real-time trading platform "
            "using TypeScript and PostgreSQL."
        )
        claims = extract_claims(text)
        assert claims, "expected at least one claim"

        facts = [
            _fact(
                fact="Designed event-driven architecture for TestingEngine",
                value="Architecture specifies state machine and prediction pipeline.",
                evidence_level="designed",
                project="TestingEngine",
                technologies=["TypeScript", "PostgreSQL"],
            )
        ]

        result = validate(claims, facts)
        # At least one claim should be rejected or need rewrite.
        outcomes = {v.outcome for v in result.verdicts}
        assert (
            ValidationOutcome.NEEDS_REWRITE in outcomes
            or ValidationOutcome.UNSUPPORTED in outcomes
        )
        assert not result.all_accepted

    def test_matching_level_accepted(self) -> None:
        text = "I designed the TestingEngine architecture using TypeScript."
        claims = extract_claims(text)
        facts = [
            _fact(
                fact="Designed TestingEngine architecture",
                value="Full architecture document for TestingEngine.",
                evidence_level="designed",
                project="TestingEngine",
                technologies=["TypeScript"],
            )
        ]
        result = validate(claims, facts)
        assert result.all_accepted or any(
            v.outcome == ValidationOutcome.ACCEPTED for v in result.verdicts
        )
