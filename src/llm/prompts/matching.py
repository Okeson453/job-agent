"""Semantic match prompt builder."""

from __future__ import annotations

from src.candidate.schemas import CandidateFactRead
from src.jobs.models import Job


def build_prompt(job: Job, candidate_facts: list[CandidateFactRead]) -> str:
    """Build the semantic matching prompt.

    Instructs the model to return structured JSON matching MatchResult.
    """
    facts_block = "\n".join(
        f"- [{f.evidence_level}] {f.fact}: {f.value}" for f in candidate_facts[:15]
    )
    techs = ", ".join(job.technologies or []) or "not specified"

    return f"""You are evaluating whether a candidate is a plausible match for a job.
Return ONLY valid JSON with this exact shape:
{{
  "match": <integer 0-100>,
  "strong_matches": [<string>, ...],
  "gaps": [<string>, ...],
  "recommendation": "QUALIFIED" | "REVIEW" | "REJECT"
}}

Rules:
- match is an internal prioritization signal, not a claim the candidate is qualified.
- strong_matches lists requirements the candidate facts clearly support.
- gaps lists requirements with no supporting fact at an appropriate evidence level.
- Do not invent experience. Only use the provided candidate facts.
- Evidence levels matter: a "designed" fact supports design claims, not deployment claims.

JOB:
Title: {job.title}
Company: {job.company}
Location: {job.location or "not specified"}
Remote: {job.remote}
Seniority: {job.seniority or "not specified"}
Technologies: {techs}
Description (excerpt):
{job.description[:2000]}

CANDIDATE FACTS:
{facts_block or "(none retrieved)"}
"""
