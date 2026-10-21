"""Pure message formatters — no I/O."""

from __future__ import annotations

from typing import Any


def format_job_card(job: Any, match: Any | None = None) -> str:
    techs = ", ".join(getattr(job, "technologies", None) or []) or "n/a"
    score = getattr(match, "match_score", 0) if match else 0
    remote = "Yes" if getattr(job, "remote", False) else "No"
    return (
        f"<b>{job.title}</b>\n"
        f"Company: {job.company}\n"
        f"Remote: {remote}\n"
        f"Match: {score}%\n"
        f"Stack: {techs}\n"
        f"Source: {job.source}"
    )


def format_failure_alert(application_id: str, error: str | None) -> str:
    return (
        f"<b>Application failed</b>\n"
        f"ID: <code>{application_id}</code>\n"
        f"Reason: {error or 'unknown'}"
    )


def format_daily_stats(stats: dict[str, Any]) -> str:
    return (
        f"<b>Daily stats</b>\n"
        f"Jobs discovered: {stats.get('jobs_discovered', 0)}\n"
        f"Applications: {stats.get('applications', 0)}\n"
        f"Submitted: {stats.get('submitted', 0)}\n"
        f"Failed: {stats.get('failed', 0)}\n"
        f"High match: {stats.get('high_match', 0)}"
    )
