"""Integration-style test: overstated claim is caught by the evidence pipeline.

Does not require a live database — exercises claim_extractor + evidence_validator
with realistic candidate facts matching the seed data shape.
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


class TestEvidencePipeline:
    def test_overstated_deployment_claim_blocked(self) -> None:
        """Cover-letter style text claiming deployment of a DESIGNED project
        must not pass validation."""
        generated = (
            "I built and deployed TestingEngine as a production real-time trading "
            "platform. The system uses TypeScript, WebSockets, and PostgreSQL and "
            "has been running at scale for two years."
        )
        claims = extract_claims(generated)
        assert claims, "expected claims to be extracted"

        facts = [
            _fact(
                "Designed event-driven architecture for TestingEngine",
                "Architecture specifies a ten-layer execution state machine and "
                "PostgreSQL-backed prediction pipeline. Production deployment not claimed.",
                "designed",
                technologies=["TypeScript", "WebSockets", "PostgreSQL"],
            ),
            _fact(
                "Partial implementation of TestingEngine prediction pipeline",
                "Core prediction pipeline components implemented in TypeScript.",
                "partially_implemented",
                technologies=["TypeScript", "WebSockets"],
            ),
        ]

        result = validate(claims, facts)
        assert not result.all_accepted
        outcomes = {v.outcome for v in result.verdicts}
        assert (
            ValidationOutcome.NEEDS_REWRITE in outcomes
            or ValidationOutcome.UNSUPPORTED in outcomes
        )

    def test_honest_design_claim_accepted(self) -> None:
        generated = (
            "I designed the TestingEngine architecture, specifying an event-driven "
            "pipeline with TypeScript and PostgreSQL. The design covers a ten-layer "
            "execution state machine."
        )
        claims = extract_claims(generated)
        facts = [
            _fact(
                "Designed event-driven architecture for TestingEngine",
                "Architecture specifies a ten-layer execution state machine.",
                "designed",
            ),
        ]
        result = validate(claims, facts)
        assert any(v.outcome == ValidationOutcome.ACCEPTED for v in result.verdicts)

    def test_research_cannot_support_design_language(self) -> None:
        generated = (
            "I designed OrionSentinel as a continuous security monitoring platform "
            "for trading infrastructure."
        )
        claims = extract_claims(generated)
        facts = [
            _fact(
                "Security monitoring research for trading infrastructure",
                "OrionSentinel research documents continuous security monitoring patterns.",
                "research",
                project="OrionSentinel",
                technologies=[],
            ),
        ]
        result = validate(claims, facts)
        # Research-level fact should not support a "designed" claim.
        if claims:
            outcomes = {v.outcome for v in result.verdicts}
            assert (
                ValidationOutcome.NEEDS_REWRITE in outcomes
                or ValidationOutcome.UNSUPPORTED in outcomes
                or not result.all_accepted
            )
