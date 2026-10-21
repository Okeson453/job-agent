"""Truth / Evidence Engine (Section 6).

Fail-closed: empty claim lists are not automatically accepted for
application-facing content. Unverified facts cannot support ACCEPTED.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from src.candidate.facts.evidence import EvidenceLevel, can_support, parse_evidence_level
from src.candidate.schemas import CandidateFactRead
from src.llm.validation.claim_extractor import Claim


class ValidationOutcome(str, Enum):
    ACCEPTED = "accepted"
    NEEDS_REWRITE = "needs_rewrite"
    UNSUPPORTED = "unsupported"
    NO_CLAIMS = "no_claims"


@dataclass
class ClaimVerdict:
    claim: Claim
    outcome: ValidationOutcome
    matched_fact_id: str | None = None
    actual_level: str | None = None
    rewrite_to_level: str | None = None
    reason: str = ""


@dataclass
class ValidationResult:
    verdicts: list[ClaimVerdict] = field(default_factory=list)
    empty_claims: bool = False

    @property
    def all_accepted(self) -> bool:
        """Fail closed: empty claim list is NOT accepted for application content."""
        if self.empty_claims or not self.verdicts:
            return False
        return all(v.outcome == ValidationOutcome.ACCEPTED for v in self.verdicts)

    @property
    def needs_manual_review(self) -> bool:
        if self.empty_claims or not self.verdicts:
            return True
        return any(
            v.outcome
            in (
                ValidationOutcome.UNSUPPORTED,
                ValidationOutcome.NO_CLAIMS,
            )
            for v in self.verdicts
        )

    @property
    def needs_rewrite(self) -> bool:
        return any(v.outcome == ValidationOutcome.NEEDS_REWRITE for v in self.verdicts)


def _find_matching_fact(
    claim: Claim, facts: list[CandidateFactRead]
) -> CandidateFactRead | None:
    """Match a claim to a fact with strict preference order.

    1. Project entity match (required when claim has project_ref)
    2. Project + technology overlap
    3. Technology overlap of at least 2 terms OR 1 tech + keyword score >= 2
    4. Keyword overlap >= 3 (weak matches rejected)
    """
    if not facts:
        return None

    if claim.project_ref:
        project_hits: list[CandidateFactRead] = []
        pref = claim.project_ref.lower()
        for fact in facts:
            meta = fact.metadata or {}
            if meta.get("project", "").lower() == pref:
                project_hits.append(fact)
            elif pref in fact.fact.lower() or pref in fact.value.lower():
                project_hits.append(fact)
        if not project_hits:
            return None
        # Prefer tech overlap within the project hits.
        if claim.technologies:
            tech_lower = {t.lower() for t in claim.technologies}
            best = None
            best_overlap = 0
            for fact in project_hits:
                meta = fact.metadata or {}
                fact_techs = {t.lower() for t in (meta.get("technologies") or [])}
                blob = (fact.fact + " " + fact.value).lower()
                for t in tech_lower:
                    if t in blob:
                        fact_techs.add(t)
                overlap = len(tech_lower & fact_techs)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best = fact
            if best is not None:
                return best
        return project_hits[0]

    if claim.technologies:
        tech_lower = {t.lower() for t in claim.technologies}
        best: CandidateFactRead | None = None
        best_overlap = 0
        for fact in facts:
            meta = fact.metadata or {}
            fact_techs = {t.lower() for t in (meta.get("technologies") or [])}
            text_blob = (fact.fact + " " + fact.value).lower()
            for t in tech_lower:
                if t in text_blob:
                    fact_techs.add(t)
            overlap = len(tech_lower & fact_techs)
            if overlap > best_overlap:
                best_overlap = overlap
                best = fact
        # Require at least 2 overlapping technologies, or 1 + strong keywords.
        if best is not None and best_overlap >= 2:
            return best
        if best is not None and best_overlap == 1 and claim.keywords:
            blob = (best.fact + " " + best.value).lower()
            kw_score = sum(1 for kw in claim.keywords if kw in blob)
            if kw_score >= 2:
                return best

    if claim.keywords:
        best = None
        best_score = 0
        for fact in facts:
            blob = (fact.fact + " " + fact.value).lower()
            score = sum(1 for kw in claim.keywords if kw in blob)
            if score > best_score:
                best_score = score
                best = fact
        # Require stronger keyword overlap than before (>= 3).
        if best is not None and best_score >= 3:
            return best

    return None


def validate(
    claims: list[Claim],
    facts: list[CandidateFactRead],
    *,
    require_verified: bool = True,
) -> ValidationResult:
    """Validate each claim against the candidate knowledge base.

    Fail-closed:
    - Empty claims → not all_accepted, needs_manual_review
    - Unverified matching facts → not ACCEPTED when require_verified=True
    """
    if not claims:
        return ValidationResult(empty_claims=True, verdicts=[])

    result = ValidationResult()

    for claim in claims:
        matched = _find_matching_fact(claim, facts)

        if matched is None:
            result.verdicts.append(
                ClaimVerdict(
                    claim=claim,
                    outcome=ValidationOutcome.UNSUPPORTED,
                    reason="No matching candidate fact found",
                )
            )
            continue

        if require_verified and not matched.verified:
            result.verdicts.append(
                ClaimVerdict(
                    claim=claim,
                    outcome=ValidationOutcome.UNSUPPORTED,
                    matched_fact_id=str(matched.id),
                    actual_level=matched.evidence_level,
                    reason="Matching fact exists but is not verified; cannot support autonomous submission",
                )
            )
            continue

        actual = parse_evidence_level(matched.evidence_level)

        if claim.claimed_level is None:
            # Unmarked factual claims must still be grounded. Accept only when
            # the matched fact is strong enough (verified/implemented); otherwise
            # force rewrite at the actual evidence level.
            if actual.value in ("verified", "implemented"):
                result.verdicts.append(
                    ClaimVerdict(
                        claim=claim,
                        outcome=ValidationOutcome.ACCEPTED,
                        matched_fact_id=str(matched.id),
                        actual_level=actual.value,
                        reason="Unmarked claim grounded by strong verified/implemented fact",
                    )
                )
            else:
                result.verdicts.append(
                    ClaimVerdict(
                        claim=claim,
                        outcome=ValidationOutcome.NEEDS_REWRITE,
                        matched_fact_id=str(matched.id),
                        actual_level=actual.value,
                        rewrite_to_level=actual.value,
                        reason=(
                            "Unmarked factual claim matched a weaker fact "
                            f"('{actual.value}'); rewrite at that evidence level"
                        ),
                    )
                )
            continue

        claimed = parse_evidence_level(claim.claimed_level)

        if can_support(claimed, actual):
            result.verdicts.append(
                ClaimVerdict(
                    claim=claim,
                    outcome=ValidationOutcome.ACCEPTED,
                    matched_fact_id=str(matched.id),
                    actual_level=actual.value,
                    reason=f"Actual level '{actual.value}' supports claimed '{claimed.value}'",
                )
            )
        else:
            result.verdicts.append(
                ClaimVerdict(
                    claim=claim,
                    outcome=ValidationOutcome.NEEDS_REWRITE,
                    matched_fact_id=str(matched.id),
                    actual_level=actual.value,
                    rewrite_to_level=actual.value,
                    reason=(
                        f"Claimed '{claimed.value}' but fact only supports "
                        f"'{actual.value}'. Rewrite at actual level."
                    ),
                )
            )

    return result
