#!/usr/bin/env python3
"""Standalone verification that DESIGNED cannot support IMPLEMENTED claims.

Exit 0 only if the governing principle holds.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.candidate.facts.evidence import EvidenceLevel, can_support
from src.llm.validation.claim_extractor import extract_claims
from src.llm.validation.evidence_validator import ValidationOutcome, validate
from src.candidate.schemas import CandidateFactRead
import uuid
from datetime import datetime, timezone


def main() -> int:
    # Rule-level check.
    if can_support(EvidenceLevel.IMPLEMENTED, EvidenceLevel.DESIGNED):
        print("FAIL: DESIGNED must not support IMPLEMENTED")
        return 1
    if not can_support(EvidenceLevel.DESIGNED, EvidenceLevel.IMPLEMENTED):
        print("FAIL: IMPLEMENTED should support DESIGNED")
        return 1

    # Pipeline-level check.
    text = (
        "I built and deployed TestingEngine as a production trading platform "
        "using TypeScript and PostgreSQL."
    )
    claims = extract_claims(text)
    facts = [
        CandidateFactRead(
            id=uuid.uuid4(),
            category="architecture",
            fact="Designed TestingEngine architecture",
            value="Architecture document only. Production deployment not claimed.",
            evidence_level="designed",
            source_document="projects/TestingEngine/architecture.md",
            verified=True,
            metadata={"project": "TestingEngine", "technologies": ["TypeScript", "PostgreSQL"]},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    ]
    result = validate(claims, facts)
    if result.all_accepted:
        print("FAIL: overstated claim was accepted")
        return 1

    print("PASS: evidence rule holds at rule level and pipeline level")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
