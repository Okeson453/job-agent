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


def format_daily_stats(stats: dict[str, Any]) -> str:
    return (
        f"<b>Daily stats</b>\n"
        f"Jobs discovered: {stats.get('jobs_discovered', 0)}\n"
        f"Opportunities tracked: {stats.get('applications', 0)}\n"
        f"Notified: {stats.get('notified', 0)}\n"
        f"Applied by you: {stats.get('applied', 0)}\n"
        f"High match: {stats.get('high_match', 0)}"
    )
