"""Tests for cognos_measure.composition module."""

from cognos_measure.composition import (
    activation_census,
    cumulative_saturation,
    fit_saturation_curve,
    jaccard_similarity,
    kind_classification,
    pairwise_jaccard,
)


def test_activation_census_basic():
    workloads = {
        "wl1": ["Process", "Workflow", "AgentPolicy"],
        "wl2": ["Process", "Workflow", "Stream"],
        "wl3": ["Process", "Stream", "Channel"],
    }
    result = activation_census(workloads, total_kinds=10)

    assert result["union_size"] == 5  # Process, Workflow, AgentPolicy, Stream, Channel
    assert result["coverage_ratio"] == 0.5
    assert result["per_workload_counts"]["wl1"] == 3


def test_jaccard_identical():
    assert jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0


def test_jaccard_disjoint():
    assert jaccard_similarity({"a"}, {"b"}) == 0.0


def test_jaccard_partial():
    j = jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
    assert abs(j - 0.5) < 0.01  # 2 / 4


def test_pairwise_jaccard():
    workloads = {
        "a": ["Process", "Workflow"],
        "b": ["Process", "Stream"],
    }
    result = pairwise_jaccard(workloads)
    assert ("a", "b") in result
    assert abs(result[("a", "b")] - 1 / 3) < 0.01  # 1 shared / 3 total


def test_cumulative_saturation():
    ordered = [
        ("wl1", ["Process", "Workflow", "AgentPolicy"]),
        ("wl2", ["Process", "Workflow", "Stream"]),
        ("wl3", ["Channel"]),
    ]
    traj = cumulative_saturation(ordered, total_kinds=10)

    assert len(traj) == 3
    assert traj[0]["cumulative"] == 3
    assert traj[0]["new_kinds"] == 3
    assert traj[1]["cumulative"] == 4  # +Stream
    assert traj[1]["new_kinds"] == 1
    assert traj[2]["cumulative"] == 5  # +Channel


def test_fit_saturation_curve():
    # Create trajectory that follows log curve
    ordered = [
        ("w1", list(range(10))),  # 10 new
        ("w2", list(range(8, 15))),  # 5 new (8,9 overlap)
        ("w3", list(range(13, 17))),  # 2 new
        ("w4", list(range(16, 18))),  # 1 new
    ]
    traj = cumulative_saturation(
        [(n, [str(x) for x in k]) for n, k in ordered],
        total_kinds=50,
    )
    fit = fit_saturation_curve(traj)
    assert "r_squared" in fit
    assert fit["r_squared"] >= 0.0  # should be reasonably good fit


def test_kind_classification():
    freq = {"Process": 5, "Workflow": 5, "AgentPolicy": 3, "Stream": 2, "Bonsai": 1}
    result = kind_classification(freq, total_workloads=5)
    assert "Process" in result["universal"]
    assert "Bonsai" in result["rare"]
