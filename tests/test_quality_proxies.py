"""Tests for sprint quality proxies and EX-6.2 segmentation helpers."""

import numpy as np

from cognos_measure.gi import sprint_quality_proxies
from experiments.ex6_2_gi_quality.run import auto_segment_weekly, bootstrap_spearman


def test_quality_proxies_empty():
    result = sprint_quality_proxies([], label="empty")
    assert result["n_commits"] == 0
    assert result["quality_score"] == 0.0


def test_quality_proxies_all_fixes():
    """All fix commits should yield low quality score."""
    commits = [
        {"date": "2026-01-01", "message": "fix: broken build"},
        {"date": "2026-01-02", "message": "fix: regression in parser"},
        {"date": "2026-01-03", "message": "hotfix: urgent bug"},
    ]
    result = sprint_quality_proxies(commits, label="all-fixes")
    assert result["fix_density"] == 1.0
    assert result["quality_score"] < 5.0  # should be low


def test_quality_proxies_balanced_healthy():
    """Mix of generation, tests, and docs should yield high quality."""
    commits = [
        {"date": "2026-01-01", "message": "add: new parser module"},
        {"date": "2026-01-02", "message": "test: parser unit tests"},
        {"date": "2026-01-03", "message": "refactor: clean up API"},
        {"date": "2026-01-04", "message": "doc: update README"},
        {"date": "2026-01-05", "message": "create: integration test suite"},
        {"date": "2026-01-06", "message": "test: verify edge cases"},
    ]
    result = sprint_quality_proxies(commits, label="balanced")
    assert result["quality_score"] > 5.0  # should be decent
    assert result["fix_density"] == 0.0


def test_quality_proxies_has_gi_ratio():
    """Quality proxies should include GI metrics."""
    commits = [
        {"date": "2026-01-01", "message": "add: feature X"},
        {"date": "2026-01-02", "message": "refactor: simplify Y"},
    ]
    result = sprint_quality_proxies(commits)
    assert "gi_ratio" in result
    assert "gi_balance" in result
    assert "balance_distance" in result
    assert "quality_components" in result


def test_quality_components_sum_to_score():
    """Verify the quality score is derived from components correctly."""
    commits = [
        {"date": "2026-01-01", "message": "add: new feature"},
        {"date": "2026-01-02", "message": "test: add tests"},
        {"date": "2026-01-03", "message": "doc: add docs"},
        {"date": "2026-01-04", "message": "refactor: clean up"},
    ]
    result = sprint_quality_proxies(commits)
    components = result["quality_components"]
    # balance_score is metadata only — NOT included in quality_score
    expected = round(
        (components["fix_score"] * 0.45 +
         components["test_score"] * 0.30 +
         components["maturity_score"] * 0.25) * 10,
        2,
    )
    assert abs(result["quality_score"] - expected) < 0.01
    # balance_score should still be present as metadata
    assert "balance_score" in components


# --- auto_segment_weekly tests ---


def test_auto_segment_weekly_groups_by_iso_week():
    """Commits from the same ISO week land in the same bin."""
    commits = [
        {"date": "2026-01-05", "message": f"commit {i}"}
        for i in range(6)  # Mon 2026-01-05 is ISO week 2
    ]
    bins = auto_segment_weekly(commits)
    assert len(bins) == 1
    assert bins[0][0] == "2026-W02"
    assert len(bins[0][1]) == 6


def test_auto_segment_weekly_filters_small_bins():
    """Weeks with < MIN_BIN_SIZE commits are filtered out."""
    commits = [
        {"date": "2026-01-05", "message": "a"},  # W02 — only 1 commit
        *[{"date": "2026-01-12", "message": f"c{i}"} for i in range(7)],  # W03 — 7
    ]
    bins = auto_segment_weekly(commits)
    labels = [b[0] for b in bins]
    assert "2026-W02" not in labels
    assert "2026-W03" in labels


def test_auto_segment_weekly_sorted():
    """Bins are returned in chronological week order."""
    commits = [
        *[{"date": "2026-02-09", "message": f"b{i}"} for i in range(5)],  # W07
        *[{"date": "2026-01-12", "message": f"a{i}"} for i in range(5)],  # W03
    ]
    bins = auto_segment_weekly(commits)
    labels = [b[0] for b in bins]
    assert labels == sorted(labels)


# --- bootstrap_spearman tests ---


def test_bootstrap_spearman_perfect_positive():
    """Perfect positive monotonic → rho = 1.0."""
    x = np.arange(10, dtype=float)
    y = np.arange(10, dtype=float)
    bs = bootstrap_spearman(x, y, n_resamples=500)
    assert bs["rho"] == 1.0
    assert bs["ci_lo"] > 0.5


def test_bootstrap_spearman_negative():
    """Perfect negative monotonic → rho = -1.0."""
    x = np.arange(10, dtype=float)
    y = np.arange(10, dtype=float)[::-1]
    bs = bootstrap_spearman(x, y, n_resamples=500)
    assert bs["rho"] == -1.0
    assert bs["ci_hi"] < -0.5


def test_bootstrap_spearman_has_all_keys():
    """Result dict has all expected keys."""
    x = np.random.default_rng(0).normal(size=20)
    y = np.random.default_rng(1).normal(size=20)
    bs = bootstrap_spearman(x, y, n_resamples=200)
    expected_keys = {"rho", "p_spearman", "p_permutation", "ci_lo", "ci_hi", "bootstrap_mean", "n"}
    assert expected_keys == set(bs.keys())
    assert bs["n"] == 20
