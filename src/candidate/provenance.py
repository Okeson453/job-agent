"""Resolve and enforce source_document provenance for candidate facts."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def resolve_source_document(source_document: str) -> Path | None:
    """Return an existing path for *source_document*, or None if unresolved.

    Search order:
    1. Path as given relative to repo root
    2. candidate/evidence/<source_document>
    3. candidate/<source_document>
    4. candidate/projects/… and top-level projects/
    5. Legacy seed names (skills.json → candidate/skills/)
    """
    if not source_document or not source_document.strip():
        return None
    rel = source_document.strip().lstrip("/")
    candidates = [
        _ROOT / rel,
        _ROOT / "candidate" / "evidence" / rel,
        _ROOT / "candidate" / rel,
    ]
    if rel.startswith("projects/"):
        candidates.append(_ROOT / "candidate" / rel)
        candidates.append(_ROOT / rel)
        candidates.append(_ROOT / "projects" / Path(rel).name)

    for path in candidates:
        if path is not None and path.is_file():
            return path
        if path is not None and path.is_dir():
            return path

    seed = _ROOT / "candidate" / Path(rel).name
    if seed.is_file():
        return seed

    # Scaffold layout: skills.json → candidate/skills/ (directory of yaml)
    stem = Path(rel).stem
    for folder in ("skills", "answer_bank", "profile", "identity", "experience"):
        if stem in (folder, f"{folder}.json") or rel in (f"{folder}.json", folder):
            d = _ROOT / "candidate" / folder
            if d.is_dir():
                return d
    return None


def require_resolvable_source(source_document: str) -> Path:
    path = resolve_source_document(source_document)
    if path is None:
        raise ValueError(
            f"Provenance source_document not found: {source_document!r}. "
            "Facts must point at an existing file under projects/ or candidate/."
        )
    return path
