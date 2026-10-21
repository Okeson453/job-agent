"""Candidate facts and evidence-level enforcement."""

from src.candidate.facts.evidence import (
    CLAIM_VERBS,
    EvidenceLevel,
    can_support,
    parse_evidence_level,
    strongest,
)
from src.candidate.facts.service import (
    MissingProvenanceError,
    bulk_create_facts,
    create_fact,
    get_fact,
    list_facts,
    search_facts,
)

__all__ = [
    "CLAIM_VERBS",
    "EvidenceLevel",
    "MissingProvenanceError",
    "bulk_create_facts",
    "can_support",
    "create_fact",
    "get_fact",
    "list_facts",
    "parse_evidence_level",
    "search_facts",
    "strongest",
]
