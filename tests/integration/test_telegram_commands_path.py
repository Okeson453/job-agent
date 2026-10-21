"""Verify /apply and API approve share the same service function."""

from __future__ import annotations

from pathlib import Path

from src.applications.planner.state_machine import (
    MANUAL_REVIEW,
    READY,
    SUBMISSION,
    SUBMITTED,
    _VALID_TRANSITIONS,
)


class TestApprovePathConsistency:
    def test_ready_can_go_to_submission(self) -> None:
        assert SUBMISSION in _VALID_TRANSITIONS[READY]

    def test_manual_review_can_go_to_submission(self) -> None:
        assert SUBMISSION in _VALID_TRANSITIONS[MANUAL_REVIEW]

    def test_submitted_can_reach_interview(self) -> None:
        assert "INTERVIEW" in _VALID_TRANSITIONS[SUBMITTED]

    def test_canonical_command_names_registered(self) -> None:
        from apps.telegram.commands import HANDLERS

        assert "/apply" in HANDLERS
        assert "/applied" in HANDLERS
        assert "/mnt/agently" not in HANDLERS
        assert "/mnt/agentlied" not in HANDLERS

    def test_commands_and_api_share_service(self) -> None:
        root = Path(__file__).resolve().parents[2]
        cmds_src = (root / "apps/telegram/commands.py").read_text()
        api_src = (root / "apps/api/routes/applications.py").read_text()
        svc_src = (root / "src/applications/service.py").read_text()
        assert "approve_application" in cmds_src
        assert "approve_svc" in api_src or "approve_application as approve_svc" in api_src
        assert "BROWSER_QUEUE" in svc_src
        assert "sm.advance" in svc_src
        assert '"/apply"' in cmds_src or "'/apply'" in cmds_src
        assert '"/applied"' in cmds_src or "'/applied'" in cmds_src
