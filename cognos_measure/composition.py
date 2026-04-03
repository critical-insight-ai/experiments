"""Compositional coverage metrics — CRD activation census, Jaccard similarity, saturation curves."""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any

import numpy as np


def activation_census(
    workloads: dict[str, list[str]],
    total_kinds: int = 164,
) -> dict[str, Any]:
    """Compute CRD activation statistics across workloads.

    Args:
        workloads: Mapping of workload_name -> list of CRD kind strings used.
        total_kinds: Total available CRD kinds in the platform.

    Returns:
        Dict with per-workload counts, union coverage, frequency distribution.
    """
    per_workload = {name: sorted(set(kinds)) for name, kinds in workloads.items()}
    per_workload_counts = {name: len(kinds) for name, kinds in per_workload.items()}

    all_kinds: list[str] = []
    for kinds in workloads.values():
        all_kinds.extend(kinds)

    union = sorted(set(all_kinds))
    frequency = Counter(all_kinds)

    return {
        "per_workload": per_workload,
        "per_workload_counts": per_workload_counts,
        "union": union,
        "union_size": len(union),
        "total_kinds": total_kinds,
        "coverage_ratio": len(union) / total_kinds if total_kinds > 0 else 0.0,
        "frequency": dict(frequency.most_common()),
    }


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 1.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def pairwise_jaccard(workloads: dict[str, list[str]]) -> dict[tuple[str, str], float]:
    """Compute Jaccard similarity for all workload pairs."""
    names = sorted(workloads.keys())
    results: dict[tuple[str, str], float] = {}
    for a, b in combinations(names, 2):
        j = jaccard_similarity(set(workloads[a]), set(workloads[b]))
        results[(a, b)] = round(j, 4)
    return results


def cumulative_saturation(
    workloads_ordered: list[tuple[str, list[str]]],
    total_kinds: int = 164,
) -> list[dict[str, Any]]:
    """Compute cumulative coverage as workloads are added in order.

    Args:
        workloads_ordered: List of (name, kinds) tuples in chronological build order.
        total_kinds: Total available CRD kinds.

    Returns:
        List of dicts with cumulative stats at each step.
    """
    cumulative: set[str] = set()
    trajectory: list[dict[str, Any]] = []

    for i, (name, kinds) in enumerate(workloads_ordered):
        new_kinds = set(kinds) - cumulative
        cumulative |= set(kinds)
        trajectory.append({
            "step": i + 1,
            "workload": name,
            "workload_kinds": len(set(kinds)),
            "new_kinds": len(new_kinds),
            "new_kind_names": sorted(new_kinds),
            "cumulative": len(cumulative),
            "coverage_ratio": len(cumulative) / total_kinds,
        })

    return trajectory


def fit_saturation_curve(trajectory: list[dict[str, Any]]) -> dict[str, float]:
    """Fit a logarithmic model to the cumulative coverage trajectory.

    Model: coverage = a * ln(step) + b

    Returns:
        Dict with coefficients a, b and R-squared.
    """
    steps = np.array([t["step"] for t in trajectory], dtype=float)
    coverage = np.array([t["cumulative"] for t in trajectory], dtype=float)

    log_steps = np.log(steps)
    # Linear regression on log(steps) vs coverage
    coeffs = np.polyfit(log_steps, coverage, 1)
    a, b = float(coeffs[0]), float(coeffs[1])

    predicted = a * log_steps + b
    ss_res = float(np.sum((coverage - predicted) ** 2))
    ss_tot = float(np.sum((coverage - np.mean(coverage)) ** 2))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    return {"a": round(a, 4), "b": round(b, 4), "r_squared": round(r_squared, 4)}


def kind_classification(
    frequency: dict[str, int],
    universal_threshold: int | None = None,
    total_workloads: int | None = None,
) -> dict[str, list[str]]:
    """Classify kinds into tiers by frequency.

    Returns:
        Dict with keys 'universal', 'common', 'domain_specific', 'rare'.
    """
    if universal_threshold is None:
        if total_workloads is None:
            total_workloads = max(frequency.values()) if frequency else 1
        universal_threshold = total_workloads  # appears in ALL workloads

    universal = []
    common = []
    domain_specific = []
    rare = []

    for kind, count in frequency.items():
        if count >= universal_threshold:
            universal.append(kind)
        elif count >= universal_threshold * 0.5:
            common.append(kind)
        elif count >= 2:
            domain_specific.append(kind)
        else:
            rare.append(kind)

    return {
        "universal": sorted(universal),
        "common": sorted(common),
        "domain_specific": sorted(domain_specific),
        "rare": sorted(rare),
    }
