"""Assemble and write the tailored CV for one job."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from src.documents.kb import CandidateKB
from src.documents.render import (
    CVData,
    ProjectBlock,
    RoleBlock,
    render_docx,
    render_pdf,
)
from src.documents.tailoring import CVPlan, selected_bullets, selected_projects
from src.jobs.models import Job
from src.observability.logging import get_logger

logger = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = Path(
    os.environ.get("DOCUMENT_OUTPUT_DIR", str(_REPO_ROOT / "data" / "generated_documents"))
)

_SKILLS_PER_GROUP = 6


@dataclass(frozen=True)
class CVArtifact:
    filename_base: str
    pdf_path: Path
    docx_path: Path


def slug(value: str, limit: int = 40) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned[:limit].strip("-") or "untitled"


def filename_base(job: Job, name: str) -> str:
    """Deterministic, human-readable, filesystem-safe stem for this job."""
    parts = [
        slug(name, 36),
        "cv",
        slug(job.company or "company", 28),
        slug(job.title or "role", 44),
        slug(str(job.id), 8),
    ]
    return "-".join(part for part in parts if part)


def _dates(start: str | None, end: str | None, current: bool) -> str | None:
    if start and end:
        return f"{start} – {end}"
    if start:
        return f"{start} – Present" if current else start
    if current:
        return "Current"
    return end or None


def _skill_lines(plan: CVPlan, kb: CandidateKB) -> tuple[tuple[str, str], ...]:
    order = {name: index for index, name in enumerate(plan.skill_names)}
    seen: set[str] = set()
    lines: list[tuple[str, str]] = []
    for group, names in kb.skills.items():
        picked: list[str] = []
        group_names = [name for name in names if name in order]
        group_names.sort(key=lambda name: order.get(name, 999))
        for name in group_names:
            # "AWS Lambda (SAM)" and "AWS Lambda" are the same skill.
            key = name.split(" (")[0].strip().lower()
            if key in seen:
                continue
            seen.add(key)
            picked.append(name)
            if len(picked) >= _SKILLS_PER_GROUP:
                break
        if picked:
            lines.append((group, ", ".join(picked)))
        if len(lines) >= 6:
            break
    return tuple(lines)


def _contact_lines(kb: CandidateKB) -> tuple[str, ...]:
    lines: list[str] = []
    if kb.email:
        lines.append(kb.email)
    if kb.phone and os.environ.get("CV_INCLUDE_PHONE", "1").lower() not in {"0", "false"}:
        lines.append(kb.phone)
    if kb.location:
        lines.append(kb.location)
    for label, url in kb.links.items():
        lines.append(f"{label}: {url}")
    return tuple(lines)


def build_cv_data(job: Job, kb: CandidateKB, plan: CVPlan) -> CVData:
    roles: list[RoleBlock] = []
    for entry, bullets in selected_bullets(plan, kb):
        meta_parts = [
            part
            for part in (
                entry.location,
                _dates(entry.start, entry.end, entry.current),
            )
            if part
        ]
        roles.append(
            RoleBlock(
                title=entry.title,
                org=entry.employer,
                meta=" · ".join(meta_parts) or None,
                bullets=tuple(bullets),
            )
        )

    projects: list[ProjectBlock] = []
    for project in selected_projects(plan, kb):
        meta_parts = [
            part
            for part in (
                project.role,
                _dates(project.start, project.end, project.current),
                project.url,
            )
            if part
        ]
        projects.append(
            ProjectBlock(
                name=project.name,
                meta=" · ".join(meta_parts) or None,
                description=project.description,
                bullets=tuple(project.bullets[:2]),
            )
        )

    education = tuple(
        (
            f"{edu.degree}, {edu.institution}"
            + (f" ({edu.status.replace('-', ' ')})" if edu.status else "")
        )
        for edu in kb.education
    )

    certifications = tuple(
        " — ".join(part for part in (cert.name, cert.issuer, cert.date) if part)
        for cert in kb.certifications
    )

    return CVData(
        name=kb.name,
        headline=plan.headline,
        contact=_contact_lines(kb),
        summary=plan.summary,
        roles=tuple(roles),
        projects=tuple(projects),
        skills=_skill_lines(plan, kb),
        education=education,
        certifications=certifications,
    )


def generate_cv(
    job: Job,
    kb: CandidateKB,
    plan: CVPlan,
    *,
    output_dir: Path | None = None,
) -> CVArtifact:
    """Render the CV to PDF and DOCX under ``output_dir/<job id>/``."""
    base = filename_base(job, kb.name)
    target_dir = (output_dir or DEFAULT_OUTPUT_DIR) / str(job.id)
    target_dir.mkdir(parents=True, exist_ok=True)

    data = build_cv_data(job, kb, plan)
    pdf_path = target_dir / f"{base}.pdf"
    docx_path = target_dir / f"{base}.docx"

    render_pdf(data, pdf_path)
    render_docx(data, docx_path)

    logger.info(
        "cv.generated",
        job_id=str(job.id),
        pdf=str(pdf_path),
        docx=str(docx_path),
    )
    return CVArtifact(
        filename_base=base, pdf_path=pdf_path, docx_path=docx_path
    )
