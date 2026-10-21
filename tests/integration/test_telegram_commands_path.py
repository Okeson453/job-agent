"""Verify /applied + /dismiss and the API share the same service functions."""

from __future__ import annotations

from pathlib import Path

from src.applications.planner.state_machine import (
    APPLIED,
    DISMISSED,
    NOTIFIED,
    _VALID_TRANSITIONS,
)


class TestManualActionPathConsistency:
    def test_notified_can_go_to_applied(self) -> None:
        assert APPLIED in _VALID_TRANSITIONS[NOTIFIED]

    def test_notified_can_go_to_dismissed(self) -> None:
        assert DISMISSED in _VALID_TRANSITIONS[NOTIFIED]

    def test_applied_can_reach_interview(self) -> None:
        assert "INTERVIEW" in _VALID_TRANSITIONS[APPLIED]

    def test_no_submission_states_exist(self) -> None:
        # The auto-submission machinery is removed for good.
        for gone in ("SUBMISSION", "SUBMITTED", "SUBMISSION_FAILED", "READY", "MANUAL_REVIEW"):
            assert gone not in _VALID_TRANSITIONS

    def test_canonical_command_names_registered(self) -> None:
        from apps.telegram.commands import HANDLERS

        assert "/applied" in HANDLERS
        assert "/dismiss" in HANDLERS
        assert "/apply" not in HANDLERS

    def test_commands_and_api_share_service(self) -> None:
        root = Path(__file__).resolve().parents[2]
        cmds_src = (root / "apps/telegram/commands.py").read_text()
        api_src = (root / "apps/api/routes/applications.py").read_text()
        svc_src = (root / "src/applications/service.py").read_text()
        assert "mark_applied" in cmds_src
        assert "mark_applied_svc" in api_src or "mark_applied as mark_applied_svc" in api_src
        assert "DOCUMENT_QUEUE" not in svc_src
        assert "sm.advance" in svc_src
