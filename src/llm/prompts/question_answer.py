"""Free-text application question prompt."""

from __future__ import annotations

from src.candidate.schemas import CandidateFactRead


def build_prompt(
    question: str,
    candidate_facts: list[CandidateFactRead],
    *,
    category: str = "custom",
) -> str:
    """Build a prompt for answering an application question.

    Evidence-level discipline is stated explicitly.
    """
    facts_block = "\n".join(
        f"- [{f.evidence_level}] {f.fact}: {f.value}" for f in candidate_facts[:12]
    )

    return f"""Answer the following job-application question for the candidate.
Constraints:
- Use only the provided candidate facts.
- Match language to evidence level: designed ≠ built/deployed.
- Be direct and specific. Short sentences.
- No enthusiasm filler. No invented results or timelines.
- If the facts cannot support a truthful answer, say so briefly.

Category: {category}
Question: {question}

CANDIDATE FACTS:
{facts_block or "(none)"}

Return only the answer text.
"""
