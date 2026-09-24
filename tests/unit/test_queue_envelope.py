"""Queue envelope helpers (no Redis required)."""

from src.scheduler.queues import _envelope


def test_envelope_wraps_payload():
    env = _envelope({"job_id": "abc"})
    assert env["id"]
    assert env["attempts"] == 0
    assert env["payload"]["job_id"] == "abc"
    assert "attempts" not in env["payload"]
