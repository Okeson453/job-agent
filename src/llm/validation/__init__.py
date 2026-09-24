"""Truth / Evidence Engine: claim extraction and validation."""

from src.llm.validation.claim_extractor import Claim, extract_claims
from src.llm.validation.evidence_validator import (
    ClaimVerdict,
    ValidationOutcome,
    ValidationResult,
    validate,
)

__all__ = [
    "Claim",
    "ClaimVerdict",
    "ValidationOutcome",
    "ValidationResult",
    "extract_claims",
    "validate",
]
