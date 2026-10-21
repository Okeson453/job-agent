"""Job-description understanding prompt."""

from __future__ import annotations

from src.jobs.models import Job


def build_prompt(job: Job) -> str:
    """Build a prompt that extracts structured requirements from a JD."""
    return f"""Analyze this job posting and return ONLY valid JSON:
{{
  "required_skills": [<string>, ...],
  "preferred_skills": [<string>, ...],
  "seniority": <string or null>,
  "domain": <string or null>,
  "remote": <boolean>,
  "summary": <one-sentence summary>
}}

JOB:
Title: {job.title}
Company: {job.company}
Location: {job.location or "not specified"}
Description:
{job.description[:3000]}
"""
