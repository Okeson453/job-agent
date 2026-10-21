"""Unit tests for the evidence-level hierarchy and can_support rule.

The single most important test in the project: a DESIGNED-level fact must not
satisfy a claim asserted at IMPLEMENTED level.
"""

from __future__ import annotations

import pytest

from src.candidate.facts.evidence import (
    EvidenceLevel,
    can_support,
    parse_evidence_level,
)


class TestEvidenceLevelOrdering:
    def test_ordered_strongest_to_weakest(self) -> None:
        ordered = EvidenceLevel.ordered()
        assert ordered[0] == EvidenceLevel.VERIFIED
        assert ordered[-1] == EvidenceLevel.CONCEPT
        assert len(ordered) == 6

    def test_rank_monotonic(self) -> None:
        ranks = [level.rank() for level in EvidenceLevel.ordered()]
        assert ranks == sorted(ranks)
        assert ranks[0] == 0
        assert ranks[-1] == 5


class TestCanSupport:
    def test_equal_levels_support(self) -> None:
        for level in EvidenceLevel:
            assert can_support(level, level) is True

    def test_stronger_actual_supports_weaker_claim(self) -> None:
        # IMPLEMENTED fact can support a DESIGNED claim
        assert (
            can_support(EvidenceLevel.DESIGNED, EvidenceLevel.IMPLEMENTED) is True
        )
        # VERIFIED can support anything
        for claim in EvidenceLevel:
            assert can_support(claim, EvidenceLevel.VERIFIED) is True

    def test_designed_cannot_support_implemented_claim(self) -> None:
        """Governing principle: LLM must never upgrade DESIGNED → IMPLEMENTED."""
        assert (
            can_support(EvidenceLevel.IMPLEMENTED, EvidenceLevel.DESIGNED) is False
        )

    def test_designed_cannot_support_verified_claim(self) -> None:
        assert can_support(EvidenceLevel.VERIFIED, EvidenceLevel.DESIGNED) is False

    def test_partially_implemented_cannot_support_implemented(self) -> None:
        assert (
            can_support(
                EvidenceLevel.IMPLEMENTED, EvidenceLevel.PARTIALLY_IMPLEMENTED
            )
            is False
        )

    def test_research_cannot_support_designed(self) -> None:
        assert can_support(EvidenceLevel.DESIGNED, EvidenceLevel.RESEARCH) is False

    def test_concept_supports_only_concept(self) -> None:
        assert can_support(EvidenceLevel.CONCEPT, EvidenceLevel.CONCEPT) is True
        for claim in (
            EvidenceLevel.RESEARCH,
            EvidenceLevel.DESIGNED,
            EvidenceLevel.IMPLEMENTED,
        ):
            assert can_support(claim, EvidenceLevel.CONCEPT) is False

    def test_implemented_supports_designed_and_below(self) -> None:
        for claim in (
            EvidenceLevel.IMPLEMENTED,
            EvidenceLevel.PARTIALLY_IMPLEMENTED,
            EvidenceLevel.DESIGNED,
            EvidenceLevel.RESEARCH,
            EvidenceLevel.CONCEPT,
        ):
            assert can_support(claim, EvidenceLevel.IMPLEMENTED) is True
        assert can_support(EvidenceLevel.VERIFIED, EvidenceLevel.IMPLEMENTED) is False


class TestParseEvidenceLevel:
    def test_valid_values(self) -> None:
        assert parse_evidence_level("designed") == EvidenceLevel.DESIGNED
        assert parse_evidence_level("IMPLEMENTED") == EvidenceLevel.IMPLEMENTED
        assert parse_evidence_level("partially-implemented") == EvidenceLevel.PARTIALLY_IMPLEMENTED

    def test_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown evidence level"):
            parse_evidence_level("shipped")
