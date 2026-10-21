"""Evidence-level hierarchy and the can_support rule.

The LLM is never permitted to upgrade an evidence level. can_support() is the
single function that encodes that rule; evidence_validator.py is the only
caller that decides whether a generated claim is allowed to leave the system.

Hierarchy (strongest → weakest):
  VERIFIED > IMPLEMENTED > PARTIALLY_IMPLEMENTED > DESIGNED > RESEARCH > CONCEPT
"""

from __future__ import annotations

from enum import Enum


class EvidenceLevel(str, Enum):
    """Fixed hierarchy from strongest to weakest evidence.

    Order is significant: a higher (earlier) level can support a claim that
    only needs a lower level, but never the reverse.
    """

    VERIFIED = "verified"
    IMPLEMENTED = "implemented"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    DESIGNED = "designed"
    RESEARCH = "research"
    CONCEPT = "concept"

    @classmethod
    def ordered(cls) -> list[EvidenceLevel]:
        """Return levels from strongest to weakest."""
        return [
            cls.VERIFIED,
            cls.IMPLEMENTED,
            cls.PARTIALLY_IMPLEMENTED,
            cls.DESIGNED,
            cls.RESEARCH,
            cls.CONCEPT,
        ]

    def rank(self) -> int:
        """Numeric rank: lower number = stronger evidence."""
        return self.ordered().index(self)

    def is_at_least(self, other: EvidenceLevel) -> bool:
        """True if this level is as strong as or stronger than *other*."""
        return self.rank() <= other.rank()


# Verbs that assert a given evidence level when they appear in generated text.
CLAIM_VERBS: dict[EvidenceLevel, frozenset[str]] = {
    EvidenceLevel.IMPLEMENTED: frozenset(
        {
            "built",
            "deployed",
            "shipped",
            "operated",
            "launched",
            "released",
            "ran in production",
            "production system",
        }
    ),
    EvidenceLevel.DESIGNED: frozenset(
        {
            "designed",
            "architected",
            "specified",
            "drafted",
            "proposed",
            "modelled",
            "modeled",
        }
    ),
    EvidenceLevel.RESEARCH: frozenset(
        {
            "researched",
            "studied",
            "investigated",
            "explored",
            "analysed",
            "analyzed",
        }
    ),
}


def can_support(claimed: EvidenceLevel, actual: EvidenceLevel) -> bool:
    """Return True if *actual* evidence is strong enough to support a *claimed* level.

    A DESIGNED fact cannot satisfy an IMPLEMENTED claim.
    An IMPLEMENTED fact can satisfy a DESIGNED claim.
    Equal levels always support.
    """
    return actual.rank() <= claimed.rank()


def parse_evidence_level(value: str) -> EvidenceLevel:
    """Parse a string into EvidenceLevel; raises ValueError on unknown values."""
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    try:
        return EvidenceLevel(normalized)
    except ValueError as exc:
        valid = ", ".join(e.value for e in EvidenceLevel)
        raise ValueError(f"Unknown evidence level '{value}'. Valid: {valid}") from exc


def strongest(levels: list[EvidenceLevel]) -> EvidenceLevel | None:
    """Return the strongest level in *levels*, or None if empty."""
    if not levels:
        return None
    return min(levels, key=lambda lv: lv.rank())
