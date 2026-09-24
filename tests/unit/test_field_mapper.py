"""Unit tests for form field mapping."""

from __future__ import annotations

from src.applications.browser.field_mapper import FormField, map_fields
from src.candidate.schemas import CandidateProfile


def _profile() -> CandidateProfile:
    return CandidateProfile(
        full_name="Okeson Test",
        email="okeson@example.com",
        phone="+2340000000000",
        location="Nigeria",
    )


class TestFieldMapper:
    def test_maps_standard_fields(self) -> None:
        fields = [
            FormField(name="first_name", field_type="text", label="First Name"),
            FormField(name="last_name", field_type="text", label="Last Name"),
            FormField(name="email", field_type="email", label="Email"),
            FormField(name="phone", field_type="tel", label="Phone"),
        ]
        mapped, unmapped = map_fields(fields, _profile())
        assert mapped["first_name"] == "Okeson"
        assert mapped["last_name"] == "Test"
        assert mapped["email"] == "okeson@example.com"
        assert mapped["phone"] == "+2340000000000"
        assert unmapped == []

    def test_unmapped_custom_fields(self) -> None:
        fields = [
            FormField(name="email", field_type="email"),
            FormField(name="why_us", field_type="textarea", label="Why do you want to work here?"),
        ]
        mapped, unmapped = map_fields(fields, _profile())
        assert "email" in mapped
        assert len(unmapped) == 1
        assert unmapped[0].name == "why_us"

    def test_cover_letter_mapping(self) -> None:
        fields = [
            FormField(name="cover_letter", field_type="textarea"),
        ]
        mapped, _ = map_fields(
            fields, _profile(), cover_letter="I designed TestingEngine architecture."
        )
        assert "cover_letter" in mapped
        assert "TestingEngine" in mapped["cover_letter"]

    def test_empty_profile_leaves_gaps(self) -> None:
        empty = CandidateProfile()
        fields = [FormField(name="email", field_type="email")]
        mapped, unmapped = map_fields(fields, empty)
        # Empty email → unmapped
        assert len(unmapped) == 1 or mapped.get("email") == ""
