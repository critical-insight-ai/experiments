"""Tests for cognos_measure.temporal module."""

from cognos_measure.temporal import commit_velocity, integration_window_score


def test_commit_velocity_daily():
    commits = [
        {"date": "2025-01-01T10:00:00", "message": "fix: bug"},
        {"date": "2025-01-01T14:00:00", "message": "feat: new"},
        {"date": "2025-01-02T09:00:00", "message": "refactor: clean"},
        {"date": "2025-01-03T11:00:00", "message": "feat: add"},
        {"date": "2025-01-03T15:00:00", "message": "feat: more"},
    ]
    result = commit_velocity(commits, period="daily")
    assert result["period"] == "daily"
    assert result["mean"] > 0
    assert result["active_pct"] > 0


def test_commit_velocity_weekly():
    commits = [
        {"date": "2025-01-01T10:00:00", "message": "fix: bug"},
        {"date": "2025-01-08T10:00:00", "message": "feat: new"},
    ]
    result = commit_velocity(commits, period="weekly")
    assert result["period"] == "weekly"
    assert result["mean"] > 0


def test_integration_window_small():
    """Small workload with few CRD kinds fits in context window."""
    result = integration_window_score(
        sprint_duration_days=5,
        total_crd_kinds=20,
    )
    assert result["fits_in_context"] is True


def test_integration_window_large():
    """Very large workload may not fit."""
    result = integration_window_score(
        sprint_duration_days=5,
        total_crd_kinds=10_000,
    )
    assert result["fits_in_context"] is False
