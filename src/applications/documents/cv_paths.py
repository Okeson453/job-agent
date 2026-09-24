"""Resolve CV profile names to files under cv/."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.candidate.models import CVProfile

PROFILE_FILES: dict[str, str] = {
    "Security": "security.pdf",
    "Trading": "trading.pdf",
    "Backend": "backend.pdf",
    "FullStack": "fullstack.pdf",
    "General Software Engineer": "general.pdf",
}

_CV_DIR = Path(__file__).resolve().parents[3] / "cv"


def cv_dir() -> Path:
    return _CV_DIR


def path_for_name(name: str | None) -> Path | None:
    if not name:
        return None
    filename = PROFILE_FILES.get(name)
    if filename is None:
        candidate = _CV_DIR / name
        if candidate.exists():
            return candidate
        candidate = _CV_DIR / f"{name.lower()}.pdf"
        if candidate.exists():
            return candidate
        return None
    path = _CV_DIR / filename
    return path if path.exists() else None


async def resolve_cv_path(db: AsyncSession, profile_name: str | None) -> str | None:
    if not profile_name:
        return None
    result = await db.execute(select(CVProfile).where(CVProfile.name == profile_name))
    row = result.scalar_one_or_none()
    if row and row.file_path:
        p = Path(row.file_path)
        if p.exists():
            return str(p)
        alt = _CV_DIR / Path(row.file_path).name
        if alt.exists():
            return str(alt)
    path = path_for_name(profile_name)
    return str(path) if path else None


async def seed_cv_profiles(db: AsyncSession) -> None:
    """Insert CV variants only when the PDF exists on disk."""
    result = await db.execute(select(CVProfile))
    existing = {row.name for row in result.scalars().all()}
    for name, filename in PROFILE_FILES.items():
        if name in existing:
            continue
        path = _CV_DIR / filename
        if not path.exists():
            continue
        db.add(
            CVProfile(
                name=name,
                file_path=str(path.resolve()),
                keywords=[name.lower()],
            )
        )
    await db.flush()
