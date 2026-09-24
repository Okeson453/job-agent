"""Unit tests for application question classification."""

from __future__ import annotations

from src.applications.questions.classifier import HARD_EXCLUDED, QuestionCategory, classify


class TestClassifier:
    def test_work_authorization(self) -> None:
        assert classify("Are you authorized to work in the United States?") == (
            QuestionCategory.WORK_AUTHORIZATION
        )

    def test_compensation(self) -> None:
        assert classify("What are your salary expectations?") == (
            QuestionCategory.COMPENSATION
        )

    def test_availability(self) -> None:
        assert classify("What is your notice period / availability?") == (
            QuestionCategory.AVAILABILITY
        )

    def test_project(self) -> None:
        assert classify("Describe a challenging project you worked on.") == (
            QuestionCategory.PROJECT
        )

    def test_technical(self) -> None:
        assert classify("How would you design a high-throughput event pipeline?") == (
            QuestionCategory.TECHNICAL
        )

    def test_experience(self) -> None:
        assert classify("Tell us about your experience with TypeScript.") == (
            QuestionCategory.EXPERIENCE
        )

    def test_custom_fallback(self) -> None:
        assert classify("What is your favorite color?") == QuestionCategory.CUSTOM

    def test_hard_excluded_set(self) -> None:
        assert QuestionCategory.WORK_AUTHORIZATION in HARD_EXCLUDED
        assert QuestionCategory.COMPENSATION in HARD_EXCLUDED
        assert QuestionCategory.LEGAL in HARD_EXCLUDED
        assert QuestionCategory.TECHNICAL not in HARD_EXCLUDED
