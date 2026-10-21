from src.candidate.provenance import resolve_source_document, require_resolvable_source
import pytest


class TestProvenance:
    def test_resolves_project_architecture(self) -> None:
        path = resolve_source_document("projects/TestingEngine/architecture.md")
        assert path is not None
        assert path.exists()

    def test_resolves_skills_scaffold(self) -> None:
        path = resolve_source_document("skills.json")
        assert path is not None
        assert path.exists()

    def test_missing_raises(self) -> None:
        with pytest.raises(ValueError):
            require_resolvable_source("projects/DoesNotExist/missing.md")
