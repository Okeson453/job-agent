"""Map detected form fields to candidate identity data (Section 13)."""

from __future__ import annotations

from dataclasses import dataclass

from src.candidate.schemas import CandidateProfile


@dataclass
class FormField:
    name: str
    field_type: str  # text, email, tel, file, textarea, select
    label: str = ""
    required: bool = False


# Standard field name / label patterns → candidate attribute.
_MAPPINGS: list[tuple[list[str], str]] = [
    (["first_name", "firstname", "fname", "given-name"], "first_name"),
    (["last_name", "lastname", "lname", "family-name", "surname"], "last_name"),
    (["full_name", "name", "applicant_name", "your_name"], "full_name"),
    (["email", "e-mail", "email_address", "applicant_email"], "email"),
    (["phone", "telephone", "mobile", "phone_number", "tel"], "phone"),
    (["location", "city", "address", "current_location"], "location"),
    (["resume", "cv", "resume_file", "upload_resume"], "resume"),
    (["cover_letter", "coverletter", "letter", "cover-letter"], "cover_letter"),
]


def map_fields(
    detected_fields: list[FormField],
    candidate: CandidateProfile,
    *,
    cover_letter: str | None = None,
    cv_path: str | None = None,
) -> tuple[dict[str, str], list[FormField]]:
    """Map detected form fields to candidate data.

    Returns (mapped_values, unmapped_fields).
    Unmapped fields should be routed to the question engine.
    """
    name_parts = (candidate.full_name or "").split(None, 1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    values: dict[str, str] = {
        "first_name": first_name,
        "last_name": last_name,
        "full_name": candidate.full_name or "",
        "email": candidate.email or "",
        "phone": candidate.phone or "",
        "location": candidate.location or "",
        "resume": cv_path or "",
        "cover_letter": cover_letter or "",
    }

    mapped: dict[str, str] = {}
    unmapped: list[FormField] = []

    for field in detected_fields:
        key = _resolve_key(field)
        if key and key in values and values[key]:
            mapped[field.name] = values[key]
        else:
            unmapped.append(field)

    return mapped, unmapped


def _resolve_key(field: FormField) -> str | None:
    blob = f"{field.name} {field.label}".lower().replace("-", "_").replace(" ", "_")
    for patterns, attr in _MAPPINGS:
        for p in patterns:
            if p in blob:
                return attr
    return None
