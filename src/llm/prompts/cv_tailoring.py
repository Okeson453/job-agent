"""Prompt for job-specific CV tailoring.

The model selects from a fixed, numbered list of knowledge-base bullets and
returns the identifiers it wants. It never writes the bullets themselves, so
the rendered CV cannot contain invented experience.
"""

from __future__ import annotations

from src.documents.kb import CandidateKB
from src.jobs.models import Job


def build_prompt(job: Job, kb: CandidateKB) -> str:
    bullets = kb.bullet_pool()
    bullet_block = "\n".join(f"[{bid}] {text}" for bid, text in bullets)

    project_block = "\n".join(
        f"[{p.id}] {p.name} — {p.description or 'no description'}"
        f"{' (tech: ' + ', '.join(p.technologies[:10]) + ')' if p.technologies else ''}"
        for p in kb.projects
    )

    skill_block = "\n".join(
        f"{group}: {', '.join(names)}" for group, names in kb.skills.items()
    )

    technologies = ", ".join(str(t) for t in (job.technologies or [])[:20])

    return f"""You tailor an existing CV to one job. You may only SELECT from the material
below. You must not invent employers, projects, technologies, metrics, dates, or
certifications.

Return a single JSON object, no prose and no markdown fences, with these keys:
- "headline": short professional headline, at most 8 words. It must be supported
  by the candidate's actual titles. Do not add a seniority word (Senior, Staff,
  Principal, Lead) that is not present in the source material.
- "summary": 2-3 sentences, at most 70 words, written in first person without
  "I am passionate". Mention only technologies and work that appear below.
- "experience_bullet_ids": 8-14 ids copied exactly from EXPERIENCE BULLETS.
- "project_ids": 2-4 ids copied exactly from PROJECTS.
- "skill_names": up to 18 skill names copied exactly from SKILLS, ordered by
  relevance to this job.

Selection guidance: favour bullets and projects that overlap the job's stack and
responsibilities. Keep the strongest evidence; do not pad. If the job is
adjacent to the candidate's experience, select the closest transferable work
rather than forcing a match.

JOB
Title: {job.title}
Company: {job.company}
Seniority: {job.seniority or "not stated"}
Employment type: {job.employment_type or "not stated"}
Location: {job.location or "not stated"}
Remote: {"yes" if job.remote else "not stated"}
Technologies: {technologies or "not stated"}

Description:
{(job.description or "")[:3000]}

EXPERIENCE BULLETS
{bullet_block or "(none)"}

PROJECTS
{project_block or "(none)"}

SKILLS
{skill_block or "(none)"}
"""
