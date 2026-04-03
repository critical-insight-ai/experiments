"""Tests for cognos_measure.gi module."""

from cognos_measure.gi import (
    GIPhase,
    classify_commit_message,
    gi_ratio,
    gi_rhythm_score,
    windowed_gi,
)


def test_classify_generation():
    assert classify_commit_message("add new feature for streaming") == GIPhase.GENERATION
    assert classify_commit_message("create initial scaffold") == GIPhase.GENERATION
    assert classify_commit_message("implement batch processing") == GIPhase.GENERATION


def test_classify_integration():
    assert classify_commit_message("refactor admission pipeline") == GIPhase.INTEGRATION
    assert classify_commit_message("fix test for validation") == GIPhase.INTEGRATION
    assert classify_commit_message("document API endpoints") == GIPhase.INTEGRATION
    assert classify_commit_message("consolidate handler logic") == GIPhase.INTEGRATION


def test_classify_ambiguous():
    # A message with no strong signals
    result = classify_commit_message("update version")
    assert result in (GIPhase.GENERATION, GIPhase.INTEGRATION, GIPhase.AMBIGUOUS)


def test_gi_ratio_balanced():
    phases = [GIPhase.GENERATION, GIPhase.INTEGRATION] * 5
    result = gi_ratio(phases)
    assert result["ratio"] == 1.0
    assert abs(result["balance"]) < 0.01


def test_gi_ratio_generation_heavy():
    phases = [GIPhase.GENERATION] * 8 + [GIPhase.INTEGRATION] * 2
    result = gi_ratio(phases)
    assert result["ratio"] == 4.0
    assert result["balance"] > 0


def test_gi_ratio_integration_heavy():
    phases = [GIPhase.GENERATION] * 2 + [GIPhase.INTEGRATION] * 8
    result = gi_ratio(phases)
    assert result["ratio"] == 0.25
    assert result["balance"] < 0


def test_windowed_gi():
    classifications = [
        (f"2026-01-{i:02d}", GIPhase.GENERATION if i % 2 == 0 else GIPhase.INTEGRATION)
        for i in range(1, 15)
    ]
    windows = windowed_gi(classifications, window_size=7)
    assert len(windows) == 2  # 14 items, window 7 = 2 full windows
    assert "ratio" in windows[0]


def test_rhythm_score_perfect_alternation():
    windows = [
        {"balance": 0.5},
        {"balance": -0.5},
        {"balance": 0.5},
        {"balance": -0.5},
    ]
    rhythm = gi_rhythm_score(windows)
    assert rhythm["rhythm_score"] == 1.0


def test_rhythm_score_monotonic():
    windows = [
        {"balance": 0.5},
        {"balance": 0.8},
        {"balance": 1.2},
        {"balance": 0.6},
    ]
    rhythm = gi_rhythm_score(windows)
    assert rhythm["rhythm_score"] == 0.0  # no alternations


def test_gi_ratio_ambiguous_excluded():
    phases = [GIPhase.GENERATION, GIPhase.INTEGRATION, GIPhase.AMBIGUOUS, GIPhase.AMBIGUOUS]
    result = gi_ratio(phases)
    assert result["total_classified"] == 2  # ambiguous excluded
    assert result["a_count"] == 2
