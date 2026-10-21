"""Fail-closed validation and verified-fact gate."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from src.candidate.schemas import CandidateFactRead
from src.llm.validation.claim_extractor import Claim
from src.llm.validation.evidence_validator import ValidationOutcome, validate


def _fact(**kwargs) -> CandidateFactRead:
    base = dict(
        id=uuid.uuid4(),
        category="architecture",
        fact="Designed event-driven architecture",
        value="TestingEngine designed architecture",
        evidence_level="designed",
        source_document="projects/TestingEngine/architecture.md",
        verified=True,
        metadata={"project": "TestingEngine", "technologies": ["TypeScript"]},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    base.update(kwargs)
    return CandidateFactRead(**base)


class TestFailClosed:
    def test_empty_claims_not_accepted(self) -> None:
        result = validate([], [_fact()])
        assert result.all_accepted is False
        assert result.needs_manual_review is True
        assert result.empty_claims is True


class TestVerifiedGate:
    def test_unverified_fact_rejected(self) -> None:
        claim = Claim(
            text="I built the TestingEngine prediction pipeline",
            claimed_level="implemented",
            project_ref="TestingEngine",
            technologies=["TypeScript"],
            keywords=["prediction", "pipeline", "testingengine"],
        )
        fact = _fact(
            verified=False,
            evidence_level="partially_implemented",
            fact="Partial implementation of TestingEngine prediction pipeline",
            value="Core prediction pipeline components implemented in TypeScript",
            metadata={"project": "TestingEngine", "technologies": ["TypeScript", "WebSockets"]},
        )
        result = validate([claim], [fact], require_verified=True)
        assert result.all_accepted is False
        assert result.verdicts[0].outcome == ValidationOutcome.UNSUPPORTED

    def test_verified_designed_supports_designed_claim(self) -> None:
        claim = Claim(
            text="I designed the TestingEngine event-driven architecture",
            claimed_level="designed",
            project_ref="TestingEngine",
            technologies=["TypeScript"],
            keywords=["event", "driven", "architecture"],
        )
        result = validate([claim], [_fact()], require_verified=True)
        assert result.all_accepted is True


class TestStrictMatch:
    def test_single_tech_overlap_insufficient(self) -> None:
        claim = Claim(
            text="I implemented a GraphQL gateway",
            claimed_level="implemented",
            project_ref=None,
            technologies=["GraphQL"],
            keywords=["gateway"],
        )
        fact = _fact(
            fact="PostgreSQL proficiency",
            value="Designed PostgreSQL-backed data layers",
            evidence_level="implemented",
            metadata={"technologies": ["PostgreSQL"]},
        )
        result = validate([claim], [fact])
        assert result.verdicts[0].outcome == ValidationOutcome.UNSUPPORTED
