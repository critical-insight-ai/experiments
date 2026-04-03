"""Tests for Monte Carlo ordering and inheritance functions."""

from cognos_measure.composition import (
    inheritance_per_step,
    monte_carlo_ordering,
)


def test_inheritance_per_step_first_has_zero():
    """First workload always has 0% inheritance (nothing to inherit from)."""
    workloads = [
        ("w1", ["A", "B", "C"]),
        ("w2", ["B", "C", "D"]),
        ("w3", ["A", "D", "E"]),
    ]
    result = inheritance_per_step(workloads)
    assert result[0]["inherited"] == 0
    assert result[0]["inheritance_pct"] == 0.0


def test_inheritance_per_step_accumulates():
    """Later workloads inherit from earlier ones."""
    workloads = [
        ("w1", ["A", "B", "C"]),
        ("w2", ["B", "C", "D"]),
        ("w3", ["A", "D", "E"]),
    ]
    result = inheritance_per_step(workloads)
    # w2 inherits B, C from w1
    assert result[1]["inherited"] == 2
    assert result[1]["new_kinds"] == 1  # D is new
    # w3 inherits A (from w1), D (from w2)
    assert result[2]["inherited"] == 2
    assert result[2]["new_kinds"] == 1  # E is new


def test_inheritance_identical_workloads():
    """Second identical workload inherits 100%."""
    workloads = [
        ("w1", ["A", "B", "C"]),
        ("w2", ["A", "B", "C"]),
    ]
    result = inheritance_per_step(workloads)
    assert result[1]["inheritance_pct"] == 100.0


def test_inheritance_disjoint_workloads():
    """Disjoint workloads have 0% inheritance."""
    workloads = [
        ("w1", ["A", "B"]),
        ("w2", ["C", "D"]),
    ]
    result = inheritance_per_step(workloads)
    assert result[1]["inherited"] == 0
    assert result[1]["inheritance_pct"] == 0.0


def test_monte_carlo_deterministic():
    """Same seed produces same results."""
    workloads = {
        "w1": ["A", "B", "C"],
        "w2": ["B", "C", "D"],
        "w3": ["C", "D", "E"],
        "w4": ["A", "E", "F"],
    }
    order = ["w1", "w2", "w3", "w4"]

    r1 = monte_carlo_ordering(workloads, order, n_simulations=100, seed=42)
    r2 = monte_carlo_ordering(workloads, order, n_simulations=100, seed=42)
    assert r1["p_value"] == r2["p_value"]
    assert r1["effect_size"] == r2["effect_size"]


def test_monte_carlo_returns_expected_fields():
    workloads = {
        "w1": ["A", "B", "C"],
        "w2": ["B", "C", "D"],
        "w3": ["C", "D", "E"],
    }
    order = ["w1", "w2", "w3"]

    result = monte_carlo_ordering(workloads, order, n_simulations=50, seed=1)
    assert "p_value" in result
    assert "effect_size" in result
    assert "actual_total_inherited" in result
    assert "random_mean_total" in result
    assert "per_step_random_mean" in result
    assert len(result["per_step_random_mean"]) == 3
    assert 0.0 <= result["p_value"] <= 1.0


def test_monte_carlo_identical_workloads():
    """If all workloads use the same kinds, ordering doesn't matter."""
    workloads = {
        "w1": ["A", "B"],
        "w2": ["A", "B"],
        "w3": ["A", "B"],
    }
    order = ["w1", "w2", "w3"]

    result = monte_carlo_ordering(workloads, order, n_simulations=100, seed=42)
    # Every ordering produces the same inheritance, so p-value = 1.0 (or close)
    # and effect size = 0
    assert result["effect_size"] == 0.0
    # All orderings produce the same total, so actual >= random always
    assert result["p_value"] == 1.0
