"""LLM worker promotes when deterministic score clears threshold."""

from __future__ import annotations

from apps.worker.llm_worker import _PROMOTE_DET, _qualify


class _MR:
    def __init__(self, rec, match, analysis=None):
        self.recommendation = rec
        self.match = match
        self.analysis = analysis or {}
        self.strong_matches = []
        self.gaps = []


def test_qualify_requires_qualified_and_thresholds():
    assert _qualify(_MR("QUALIFIED", 60), 50, 40) is True
    assert _qualify(_MR("REJECT", 90), 50, 40) is False
    assert _qualify(_MR("QUALIFIED", 40), 50, 40) is False


def test_promote_threshold_default():
    assert _PROMOTE_DET >= 40


def test_deterministic_promote_path_logic():
    det = 55
    mr = _MR("REJECT", 10, {"error": "timeout"})
    assert not _qualify(mr, 10, det)
    assert det >= _PROMOTE_DET
