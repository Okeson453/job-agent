"""Load the candidate knowledge base into a structured, render-ready form.

The KB is a directory of YAML/Markdown files that the candidate maintains by
hand. Many fields are intentionally still empty or marked TODO; this loader
never fills them in. Anything absent is omitted from generated documents
rather than guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from src.observability.logging import get_logger

logger = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_ROOT = _REPO_ROOT / "candidate"

_SKILL_GROUP_NAMES = {
    "ai_ml": "AI / ML",
    "programming_languages": "Languages",
    "frontend": "Frontend",
    "backend": "Backend",
    "databases": "Databases",
    "cloud": "Cloud",
    "devops": "DevOps",
    "distributed_systems": "Distributed Systems",
    "realtime": "Real-time Systems",
    "security": "Security",
    "testing": "Testing",
    "architecture": "Architecture",
    "networking": "Networking",
    "trading": "Trading Systems",
    "tools": "Tools",
    "frameworks": "Frameworks",
    "soft_skills": "Ways of Working",
}


@dataclass(frozen=True)
class ExperienceEntry:
    id: str
    title: str
    employer: str
    location: str | None
    start: str | None
    end: str | None
    current: bool
    bullets: tuple[str, ...]


@dataclass(frozen=True)
class ProjectEntry:
    id: str
    name: str
    role: str | None
    description: str
    technologies: tuple[str, ...]
    bullets: tuple[str, ...]
    url: str | None
    start: str | None
    end: str | None
    current: bool


@dataclass(frozen=True)
class EducationEntry:
    degree: str
    institution: str
    year: str | None
    status: str | None


@dataclass(frozen=True)
class CertificationEntry:
    name: str
    issuer: str | None
    date: str | None


@dataclass(frozen=True)
class CandidateKB:
    name: str
    email: str
    phone: str | None
    location: str | None
    timezone: str | None
    headline: str | None
    summary: str | None
    experience: tuple[ExperienceEntry, ...]
    projects: tuple[ProjectEntry, ...]
    education: tuple[EducationEntry, ...]
    certifications: tuple[CertificationEntry, ...]
    skills: dict[str, tuple[str, ...]] = field(default_factory=dict)
    achievements: tuple[str, ...] = ()
    links: dict[str, str] = field(default_factory=dict)

    def bullet_pool(self) -> list[tuple[str, str]]:
        """Every citable experience bullet as ``(id, text)``."""
        pool: list[tuple[str, str]] = []
        for entry in self.experience:
            for index, bullet in enumerate(entry.bullets):
                pool.append((f"{entry.id}#{index}", bullet))
        return pool

    def all_source_text(self) -> str:
        """Concatenated KB prose used for grounding checks."""
        parts: list[str] = []
        parts.extend(e.title for e in self.experience)
        parts.extend(e.employer for e in self.experience)
        for entry in self.experience:
            parts.extend(entry.bullets)
        for project in self.projects:
            parts.append(project.name)
            parts.append(project.description)
            parts.extend(project.technologies)
            parts.extend(project.bullets)
        for group in self.skills.values():
            parts.extend(group)
        for edu in self.education:
            parts.extend([edu.degree, edu.institution])
        parts.extend(self.achievements)
        if self.summary:
            parts.append(self.summary)
        return "\n".join(parts)


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except Exception as exc:  # pragma: no cover - malformed KB files are logged
        logger.warning("kb.yaml_invalid", path=str(path), error=str(exc))
        return {}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    return " ".join(str(value).split())


def _date_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        raw = value.get("value")
        return _text(raw) or None
    text = _text(value)
    return text or None


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "entry"


def _bullet_lines(path: Path) -> list[str]:
    """Extract markdown bullets, joining indented continuation lines."""
    if not path.exists():
        return []
    bullets: list[str] = []
    current: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            if current:
                bullets.append(" ".join(current.split()))
            current = stripped[2:].strip()
            continue
        if not stripped:
            if current:
                bullets.append(" ".join(current.split()))
            current = None
            continue
        # Wrapped bullet text is indented in these files.
        if current is not None and line[:1].isspace():
            current = f"{current} {stripped}"
    if current:
        bullets.append(" ".join(current.split()))
    return [
        bullet
        for bullet in bullets
        if bullet and bullet.upper() != "TODO" and not bullet.startswith("<!--")
    ]


def _first_sentence(text: str, limit: int = 280) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""
    match = re.match(r"(.+?[.!?])(\s|$)", cleaned)
    sentence = match.group(1) if match else cleaned
    if len(sentence) > limit:
        cut = sentence[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
        sentence = cut + "…"
    return sentence


def _load_identity(root: Path) -> dict[str, Any]:
    identity = root / "identity"
    legal = _load_yaml(identity / "legal_name.yaml")
    preferred = _load_yaml(identity / "preferred_name.yaml")
    contact = _load_yaml(identity / "contact.yaml")
    location = _load_yaml(identity / "location.yaml")
    timezone = _load_yaml(identity / "timezone.yaml")

    name = _text(legal.get("full_legal_name")) or _text(preferred.get("preferred_name"))
    city = _text(location.get("city"))
    country = _text(location.get("country"))
    place = ", ".join(part for part in (city, country) if part) or None

    return {
        "name": name or "Candidate",
        "email": _text(contact.get("email")),
        "phone": _text(contact.get("phone")) or None,
        "location": place,
        "timezone": _text(timezone.get("timezone")) or None,
    }


def _load_profile(root: Path) -> dict[str, Any]:
    overview = _load_yaml(root / "profile" / "candidate_overview.yaml")
    headline = _text(overview.get("current_title")) or None

    summary: str | None = None
    summary_path = root / "profile" / "professional_summary.md"
    if summary_path.exists():
        raw = summary_path.read_text(encoding="utf-8")
        raw = re.sub(r"<!--.*?-->", " ", raw, flags=re.DOTALL)
        body = [
            line.strip()
            for line in raw.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        candidate = " ".join(body).strip()
        if candidate.upper() != "TODO" and len(candidate) > 120:
            summary = candidate

    return {"headline": headline, "summary": summary}


def _experience_entries(root: Path) -> tuple[ExperienceEntry, ...]:
    entries: list[ExperienceEntry] = []
    seen: set[str] = set()
    exp_dir = root / "experience"
    if not exp_dir.exists():
        return ()

    # project_experience.yaml describes project roles, not employments; it has
    # no employer or bullets and would otherwise appear as empty jobs.
    skip = {"project_experience.yaml"}
    for path in sorted(exp_dir.glob("*.yaml")):
        if path.name in skip:
            continue
        data = _load_yaml(path)
        if not isinstance(data, dict):
            continue
        for _, rows in data.items():
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                employer = _text(row.get("employer") or row.get("client") or row.get("company"))
                title = _text(row.get("job_title") or row.get("role") or row.get("title"))
                if not employer and not title:
                    continue
                entry_id = _text(row.get("id")) or _slug(f"{employer}-{title}")
                dedupe_key = _slug(f"{employer}|{title}")
                if entry_id in seen or dedupe_key in seen:
                    # employment.yaml and independent_contracting.yaml both
                    # describe the same current engagement; keep the first.
                    continue
                seen.add(entry_id)
                seen.add(dedupe_key)
                bullets = tuple(
                    _text(item)
                    for item in (row.get("responsibilities") or [])
                    if _text(item)
                )
                entries.append(
                    ExperienceEntry(
                        id=entry_id,
                        title=title or "Engineer",
                        employer=employer or "Independent",
                        location=_text(row.get("location")) or None,
                        start=_date_value(row.get("start_date")),
                        end=_date_value(row.get("end_date")),
                        current=bool(row.get("current")),
                        bullets=bullets,
                    )
                )
    return tuple(entries)


def _project_technologies(project_dir: Path) -> tuple[str, ...]:
    data = _load_yaml(project_dir / "technologies.yaml")
    values: list[str] = []
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, str) and value.strip():
                values.append(_text(value))
    return tuple(dict.fromkeys(values))


def _project_entries(root: Path) -> tuple[ProjectEntry, ...]:
    projects_dir = root / "projects"
    if not projects_dir.exists():
        return ()
    entries: list[ProjectEntry] = []
    for project_dir in sorted(p for p in projects_dir.iterdir() if p.is_dir()):
        meta_path = project_dir / "project.yaml"
        if not meta_path.exists():
            continue
        meta = _load_yaml(meta_path)
        if not isinstance(meta, dict):
            continue
        name = _text(meta.get("name")) or project_dir.name
        description = _text(meta.get("description"))
        bullets = tuple(
            _bullet_lines(project_dir / "achievements.md")
            or _bullet_lines(project_dir / "responsibilities.md")
            or _bullet_lines(project_dir / "features.md")[:6]
        )
        links = _load_yaml(project_dir / "links.yaml")
        dates = meta.get("dates") if isinstance(meta.get("dates"), dict) else {}
        entries.append(
            ProjectEntry(
                id=project_dir.name,
                name=name,
                role=_text(meta.get("role")) or None,
                description=_first_sentence(description),
                technologies=_project_technologies(project_dir),
                bullets=bullets,
                url=_text(links.get("repo_url")) or None,
                start=_date_value(dates.get("start")) if dates else None,
                end=_date_value(dates.get("end")) if dates else None,
                current=bool(dates.get("current")) if dates else False,
            )
        )
    return tuple(entries)


def _education_entries(root: Path) -> tuple[EducationEntry, ...]:
    edu_dir = root / "education"
    degrees = _load_yaml(edu_dir / "degrees.yaml").get("degrees") or []
    if not isinstance(degrees, list):
        return ()
    entries: list[EducationEntry] = []
    for row in degrees:
        if not isinstance(row, dict):
            continue
        degree = _text(row.get("degree")) or _text(row.get("qualification"))
        institution = _text(row.get("institution"))
        if not degree and not institution:
            continue
        years = None
        start, end = _text(row.get("start_year")), _text(row.get("end_year"))
        if start and end:
            years = f"{start} – {end}"
        elif end:
            years = end
        elif start:
            years = f"{start} – Present"
        entries.append(
            EducationEntry(
                degree=degree or "Degree",
                institution=institution or "Institution",
                year=years,
                status=_text(row.get("status")) or None,
            )
        )
    return tuple(entries)


def _certification_entries(root: Path) -> tuple[CertificationEntry, ...]:
    data = _load_yaml(root / "certifications" / "certifications.yaml")
    rows = data.get("certifications") if isinstance(data, dict) else []
    if not isinstance(rows, list):
        return ()
    entries: list[CertificationEntry] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = _text(row.get("name"))
        if not name:
            continue
        entries.append(
            CertificationEntry(
                name=name,
                issuer=_text(row.get("issuer")) or None,
                date=_text(row.get("date_earned")) or None,
            )
        )
    return tuple(entries)


def _clean_skill_name(name: str) -> str:
    """Turn raw snake_case keys into readable skill names; leave others alone."""
    if not name:
        return ""
    if re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)+", name):
        return name.replace("_", " ").capitalize()
    if name and name[0].islower() and " " in name:
        return name[0].upper() + name[1:]
    return name


def _flatten_skill_group(raw_group: str, rows: Any) -> list[tuple[str, list[str]]]:
    """Return ``(label, names)`` pairs for a skill group, including sub-groups."""
    names: list[str] = []
    nested: list[tuple[str, list[str]]] = []

    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict):
                name = _clean_skill_name(_text(row.get("name")))
            elif isinstance(row, str):
                name = _clean_skill_name(_text(row))
            else:
                name = ""
            if name:
                names.append(name)
    elif isinstance(rows, dict):
        for sub_key, sub_rows in rows.items():
            nested.extend(_flatten_skill_group(str(sub_key), sub_rows))

    if not names:
        return nested

    label = _SKILL_GROUP_NAMES.get(raw_group, raw_group.replace("_", " ").title())
    return [(label, names), *nested]


def _skill_groups(root: Path) -> dict[str, tuple[str, ...]]:
    skills_dir = root / "skills"
    if not skills_dir.exists():
        return {}
    groups: dict[str, tuple[str, ...]] = {}
    for path in sorted(skills_dir.glob("*.yaml")):
        data = _load_yaml(path)
        if not isinstance(data, dict):
            continue
        for raw_group, rows in data.items():
            for label, names in _flatten_skill_group(str(raw_group), rows):
                existing = list(groups.get(label, ()))
                groups[label] = tuple(dict.fromkeys([*existing, *names]))
    return groups


def _achievement_items(root: Path) -> tuple[str, ...]:
    items: list[str] = []
    achievements_dir = root / "achievements"
    if not achievements_dir.exists():
        return ()
    for path in sorted(achievements_dir.glob("*.yaml")):
        data = _load_yaml(path)
        if not isinstance(data, dict):
            continue
        for rows in data.values():
            if not isinstance(rows, list):
                continue
            for row in rows:
                if isinstance(row, dict):
                    text = _text(row.get("claim") or row.get("result") or row.get("statement"))
                else:
                    text = _text(row)
                if text:
                    items.append(text)
    return tuple(dict.fromkeys(items))


def _portfolio_links(root: Path) -> dict[str, str]:
    links: dict[str, str] = {}
    github = _load_yaml(root / "portfolio" / "github.yaml")
    if _text(github.get("profile_url")):
        links["GitHub"] = _text(github.get("profile_url"))
    websites = _load_yaml(root / "portfolio" / "websites.yaml")
    for row in websites.get("sites") or []:
        if isinstance(row, dict) and _text(row.get("url")):
            links[_text(row.get("label")) or "Website"] = _text(row.get("url"))
    return links


@lru_cache(maxsize=4)
def load_kb(root: str | None = None) -> CandidateKB:
    """Load the KB from disk. Cached per root path."""
    base = Path(root) if root else _DEFAULT_ROOT
    identity = _load_identity(base)
    profile = _load_profile(base)
    kb = CandidateKB(
        name=identity["name"],
        email=identity["email"],
        phone=identity["phone"],
        location=identity["location"],
        timezone=identity["timezone"],
        headline=profile["headline"],
        summary=profile["summary"],
        experience=_experience_entries(base),
        projects=_project_entries(base),
        education=_education_entries(base),
        certifications=_certification_entries(base),
        skills=_skill_groups(base),
        achievements=_achievement_items(base),
        links=_portfolio_links(base),
    )
    logger.info(
        "kb.loaded",
        name=kb.name,
        experience=len(kb.experience),
        projects=len(kb.projects),
        skills=sum(len(v) for v in kb.skills.values()),
    )
    return kb
