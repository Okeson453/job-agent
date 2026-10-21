"""Cover letter generation prompt."""

from __future__ import annotations

from src.candidate.schemas import CandidateFactRead
from src.jobs.models import Job


def build_prompt(job: Job, candidate_facts: list[CandidateFactRead]) -> str:
    """Build a constrained cover-letter prompt.

    Output must be short, specific, and grounded only in the supplied facts.
    Evidence levels must not be upgraded.
    """
    facts_block = "\n".join(
        f"- [{f.evidence_level}] {f.fact}: {f.value}" for f in candidate_facts[:10]
    )

    return f"""Write a short cover letter (3-4 tight paragraphs) for the role below.
Constraints:
- Name the actual role and company.
- Reference one or two verified pieces of the candidate's work from the facts.
- Use language that matches the evidence level of each fact.
  DESIGNED facts → "designed" / "architected" / "specified".
  Never say "built", "deployed", or "shipped" unless the fact is IMPLEMENTED or VERIFIED.
- No enthusiasm filler. No "I am passionate about". No exclamation points.
- Plain, precise, technical where appropriate.
- Do not invent projects, results, numbers, or timelines.

JOB:
Title: {job.title}
Company: {job.company}
Description (excerpt):
{job.description[:1500]}

CANDIDATE FACTS (use only these):
{facts_block or "(none)"}

Return only the cover letter text, no preamble.
"""
