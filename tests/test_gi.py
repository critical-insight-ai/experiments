"""Tests for cognos_measure.gi module."""

from cognos_measure.gi import (
    GIPhase,
    classify_commit_message,
    classify_commit_layer3,
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


# --- Layer 3 classifier tests ---


def test_layer3_pure_additions():
    """Commit that only adds new files should classify as GENERATION."""
    result = classify_commit_layer3(
        "add new module",
        files_added=5, files_modified=0, files_deleted=0, files_renamed=0,
        total_insertions=200, total_deletions=0,
    )
    assert result == GIPhase.GENERATION


def test_layer3_deletions_and_renames():
    """Commit that deletes and renames should classify as INTEGRATION."""
    result = classify_commit_layer3(
        "refactor: clean up old code",
        files_added=0, files_modified=1, files_deleted=3, files_renamed=2,
        total_insertions=10, total_deletions=150,
    )
    assert result == GIPhase.INTEGRATION


def test_layer3_modifications_mostly_deletions():
    """Commit with net deletion = integration (simplification)."""
    result = classify_commit_layer3(
        "update utils",
        files_added=0, files_modified=4, files_deleted=0, files_renamed=0,
        total_insertions=5, total_deletions=80,
    )
    assert result == GIPhase.INTEGRATION


def test_layer3_no_stats_falls_back_to_keyword():
    """Without diff stats, should degrade to Layer 4 keyword classification."""
    result = classify_commit_layer3("add new feature for streaming")
    assert result == GIPhase.GENERATION

    result2 = classify_commit_layer3("refactor admission pipeline")
    assert result2 == GIPhase.INTEGRATION


def test_layer3_mixed_signals_majority_wins():
    """When keyword says G but diff stats say I, majority should win."""
    # keyword: "add" -> G; structural: 0 added, 3 deleted -> I; content: few ins -> I
    result = classify_commit_layer3(
        "add: remove deprecated modules",
        files_added=0, files_modified=1, files_deleted=3, files_renamed=0,
        total_insertions=2, total_deletions=50,
    )
    assert result == GIPhase.INTEGRATION


def test_layer3_file_path_tiebreaker():
    """When signals disagree, file-type tiebreaker should resolve."""
    # keyword: ambiguous; structural: 1 add, 1 delete = tie; content: 50/50 = ambiguous
    # file paths: test file -> integration tiebreaker
    result = classify_commit_layer3(
        "update: improve test coverage",
        files_added=1, files_modified=0, files_deleted=1, files_renamed=0,
        total_insertions=50, total_deletions=50,
        file_paths=["tests/test_foo.py", "src/old_module.py"],
    )
    assert result == GIPhase.INTEGRATION


def test_layer3_single_file_commit():
    """Single new file should be GENERATION."""
    result = classify_commit_layer3(
        "create parser module",
        files_added=1, files_modified=0, files_deleted=0, files_renamed=0,
        total_insertions=100, total_deletions=0,
        file_paths=["src/parser.py"],
    )
    assert result == GIPhase.GENERATION
