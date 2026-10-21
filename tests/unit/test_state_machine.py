"""Unit tests for application state machine transition table."""

from __future__ import annotations

from src.applications.planner.state_machine import (
    APPLICATION_PREP,
    DISCOVERED,
    FACT_VALIDATION,
    MANUAL_REVIEW,
    MATCHED,
    QUALIFIED,
    READY,
    REJECTED_BY_FILTER,
    SUBMISSION,
    SUBMITTED,
    SUBMISSION_FAILED,
    _VALID_TRANSITIONS,
    is_terminal,
)


class TestTransitionTable:
    def test_happy_path_reachable(self) -> None:
        """DISCOVERED can reach SUBMITTED through the documented path."""
        path = [
            DISCOVERED,
            "NORMALIZED",
            "ELIGIBILITY_CHECK",
            MATCHED,
            QUALIFIED,
            APPLICATION_PREP,
            FACT_VALIDATION,
            READY,
            SUBMISSION,
            SUBMITTED,
        ]
        for i in range(len(path) - 1):
            allowed = _VALID_TRANSITIONS.get(path[i], set())
            assert path[i + 1] in allowed, f"{path[i]} → {path[i + 1]} not allowed"

    def test_failure_states_terminal(self) -> None:
        for state in (
            REJECTED_BY_FILTER,
            "LOW_MATCH",
            "MISSING_INFORMATION",
            "DUPLICATE",
            "OFFER",
            "EMPLOYER_REJECTED",
        ):
            assert is_terminal(state), f"{state} should be terminal"

    def test_submitted_can_progress_to_interview(self) -> None:
        from src.applications.planner.state_machine import INTERVIEW

        assert INTERVIEW in _VALID_TRANSITIONS[SUBMITTED]

    def test_manual_review_can_recover(self) -> None:
        allowed = _VALID_TRANSITIONS[MANUAL_REVIEW]
        assert READY in allowed or SUBMISSION in allowed

    def test_submission_failed_can_retry(self) -> None:
        allowed = _VALID_TRANSITIONS[SUBMISSION_FAILED]
        assert SUBMISSION in allowed or MANUAL_REVIEW in allowed

    def test_no_skip_from_discovered_to_submitted(self) -> None:
        assert SUBMITTED not in _VALID_TRANSITIONS[DISCOVERED]

    def test_fact_validation_branches(self) -> None:
        allowed = _VALID_TRANSITIONS[FACT_VALIDATION]
        assert READY in allowed
        assert MANUAL_REVIEW in allowed
