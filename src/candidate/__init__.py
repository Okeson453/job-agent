"""Candidate knowledge base: facts, projects, skills, profile, answer bank."""

from src.candidate.facts.evidence import EvidenceLevel, can_support, parse_evidence_level
from src.candidate.schemas import CandidateProfile

__all__ = [
    "CandidateProfile",
    "EvidenceLevel",
    "can_support",
    "parse_evidence_level",
]
