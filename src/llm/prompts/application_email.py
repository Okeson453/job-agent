"""Prompt for a job-specific application email body.

The email is never sent by the system; it is drafted for the operator to copy,
adjust, and send themselves.
"""

from __future__ import annotations

from src.documents.kb import CandidateKB
from src.documents.tailoring import CVPlan
from src.jobs.models import Job


def build_prompt(job: Job, kb: CandidateKB, plan: CVPlan, recipient: str) -> str:
    bullets = dict(kb.bullet_pool())
    selected = [
        bullets[bid] for bid in plan.experience_bullet_ids if bid in bullets
    ][:5]
    projects = [p for p in kb.projects if p.id in set(plan.project_ids)][:2]

    bullet_block = "\n".join(f"- {text}" for text in selected) or "(none)"
    project_block = "\n".join(
        f"- {p.name}: {p.description}" for p in projects if p.description
    ) or "(none)"

    return f"""Write a short application email body for the job below.

Constraints:
- 120-180 words. Plain text. No markdown, no placeholders like [Company].
- Address the hiring team at {job.company}. The recipient address is {recipient}.
- Say which role is being applied for in the first sentence.
- Reference one or two concrete pieces of work from the material provided.
- Mention that the tailored CV is attached.
- Mention availability: based in {kb.location or "Nigeria"}, timezone {kb.timezone or "Africa/Lagos"}, remote-capable.
- Do not invent employers, projects, metrics, dates, certifications, or technologies.
- Do not claim a seniority level that is not in the material.
- No "I am passionate", no exclamation marks, no flattery.
- Sign off with the candidate's name: {kb.name}.

JOB
Title: {job.title}
Company: {job.company}
Location: {job.location or "not stated"}
Description:
{(job.description or "")[:2200]}

CANDIDATE EXPERIENCE BULLETS
{bullet_block}

CANDIDATE PROJECTS
{project_block}

CANDIDATE SUMMARY
{plan.summary}

Return only the email body. Do not include a subject line or the recipient address.
"""
