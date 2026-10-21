"""Unit tests for application state machine transition table."""

from __future__ import annotations

from src.applications.planner.state_machine import (
    APPLIED,
    DISCOVERED,
    DISMISSED,
    DOCUMENT_FAILED,
    DOCUMENT_PREP,
    INTERVIEW,
    LOW_MATCH,
    MATCHED,
    MISSING_INFORMATION,
    NOTIFIED,
    OFFER,
    QUALIFIED,
    REJECTED_BY_FILTER,
    _VALID_TRANSITIONS,
    can_transition,
    is_terminal,
)


class TestTransitionTable:
    def test_happy_path_reachable(self) -> None:
        """DISCOVERED can reach NOTIFIED through the documented path."""
        path = [
            DISCOVERED,
            "NORMALIZED",
            "ELIGIBILITY_CHECK",
            MATCHED,
            QUALIFIED,
            DOCUMENT_PREP,
            NOTIFIED,
        ]
        for cur, nxt in zip(path, path[1:]):
            assert can_transition(cur, nxt), f"{cur} → {nxt} must be legal"

    def test_notified_to_manual_outcomes(self) -> None:
        assert can_transition(NOTIFIED, APPLIED)
        assert can_transition(NOTIFIED, DISMISSED)

    def test_applied_to_outcomes(self) -> None:
        assert can_transition(APPLIED, INTERVIEW)
        assert can_transition(APPLIED, OFFER)
        assert can_transition(APPLIED, "EMPLOYER_REJECTED")

    def test_interview_to_offer_or_reject(self) -> None:
        assert can_transition(INTERVIEW, OFFER)
        assert can_transition(INTERVIEW, "EMPLOYER_REJECTED")

    def test_document_failed_can_retry_or_notify(self) -> None:
        assert can_transition(DOCUMENT_FAILED, DOCUMENT_PREP)
        assert can_transition(DOCUMENT_FAILED, NOTIFIED)

    def test_failure_paths(self) -> None:
        assert can_transition(DISCOVERED, REJECTED_BY_FILTER)
        assert can_transition(MATCHED, LOW_MATCH)
        assert can_transition(QUALIFIED, MISSING_INFORMATION)
        assert can_transition(DOCUMENT_PREP, MISSING_INFORMATION)
        assert can_transition(DOCUMENT_PREP, DOCUMENT_FAILED)

    def test_terminal_states(self) -> None:
        for state in (
            OFFER,
            "EMPLOYER_REJECTED",
            DISMISSED,
            REJECTED_BY_FILTER,
            LOW_MATCH,
            MISSING_INFORMATION,
            "DUPLICATE",
        ):
            assert is_terminal(state), f"{state} must be terminal"

    def test_pipeline_never_auto_submits(self) -> None:
        """No state may transition into a submission state: they don't exist."""
        for gone in ("SUBMISSION", "SUBMITTED", "SUBMISSION_FAILED", "READY", "MANUAL_REVIEW"):
            assert gone not in _VALID_TRANSITIONS
            for targets in _VALID_TRANSITIONS.values():
                assert gone not in targets

    def test_notified_is_not_terminal(self) -> None:
        assert not is_terminal(NOTIFIED)

    def test_discovered_initial(self) -> None:
        # Every application starts at DISCOVERED.
        assert DISCOVERED in _VALID_TRANSITIONS
