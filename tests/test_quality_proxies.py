"""Tests for sprint quality proxies in cognos_measure.gi."""

from cognos_measure.gi import sprint_quality_proxies


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
