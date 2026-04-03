"""Compositional coverage metrics — CRD activation census, Jaccard similarity, saturation curves."""

from __future__ import annotations

import random
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


def inheritance_per_step(
    workloads_ordered: list[tuple[str, list[str]]],
) -> list[dict[str, Any]]:
    """Compute per-step inheritance metrics for an ordering of workloads.

    For each workload in order, measures how many of its CRD kinds
    were already introduced by earlier workloads (inherited) vs. newly introduced.

    Returns:
        List of dicts with: step, name, total_kinds, new_kinds, inherited, inheritance_pct
    """
    cumulative: set[str] = set()
    results: list[dict[str, Any]] = []

    for i, (name, kinds) in enumerate(workloads_ordered):
        kind_set = set(kinds)
        inherited = kind_set & cumulative
        new = kind_set - cumulative
        cumulative |= kind_set

        results.append({
            "step": i + 1,
            "name": name,
            "total_kinds": len(kind_set),
            "new_kinds": len(new),
            "inherited": len(inherited),
            "inheritance_pct": round(len(inherited) / len(kind_set) * 100, 1) if kind_set else 0.0,
        })

    return results


def monte_carlo_ordering(
    workloads: dict[str, list[str]],
    actual_order: list[str],
    n_simulations: int = 1000,
    seed: int | None = 42,
) -> dict[str, Any]:
    """Monte Carlo test: is the actual build order's compounding better than random?

    Shuffles the workload build order n_simulations times, computing inheritance
    at each step. Compares the actual ordering's inheritance pattern against the
    random distribution using two metrics:

    1. Total inherited (invariant to ordering — serves as sanity check)
    2. Weighted inheritance score: Σ (N-step+1)/N * inheritance_pct — rewards
       front-loading (earlier inheritance is weighted more heavily)

    Args:
        workloads: Mapping workload_name -> CRD kinds used.
        actual_order: The chronological build order (list of workload names).
        n_simulations: Number of random shuffles.
        seed: Random seed for reproducibility.

    Returns:
        Dict with actual vs random inheritance curves, p-value, effect size.
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    # Actual inheritance curve
    actual_items = [(name, workloads[name]) for name in actual_order if name in workloads]
    actual_inheritance = inheritance_per_step(actual_items)
    actual_total_inherited = sum(s["inherited"] for s in actual_inheritance)
    actual_curve = [s["inheritance_pct"] for s in actual_inheritance]

    n_steps = len(actual_inheritance)
    # Weighted score: front-load early inheritance
    weights = np.array([(n_steps - i) / n_steps for i in range(n_steps)])
    actual_weighted = float(np.sum(np.array(actual_curve) * weights))

    # Monte Carlo: shuffle and compute inheritance each time
    names = [name for name in actual_order if name in workloads]
    random_totals: list[int] = []
    random_curves: list[list[float]] = []
    random_weighted_scores: list[float] = []

    for _ in range(n_simulations):
        shuffled = names.copy()
        random.shuffle(shuffled)
        items = [(name, workloads[name]) for name in shuffled]
        inheritance = inheritance_per_step(items)
        random_totals.append(sum(s["inherited"] for s in inheritance))
        curve = [s["inheritance_pct"] for s in inheritance]
        random_curves.append(curve)
        random_weighted_scores.append(float(np.sum(np.array(curve) * weights)))

    # Statistics on weighted scores (the meaningful metric)
    weighted_arr = np.array(random_weighted_scores, dtype=float)
    weighted_mean = float(np.mean(weighted_arr))
    weighted_std = float(np.std(weighted_arr))

    # p-value: fraction of random orderings whose weighted score >= actual
    p_value = float(np.mean(weighted_arr >= actual_weighted))

    # Effect size: Cohen's d on weighted scores
    effect_size = (actual_weighted - weighted_mean) / weighted_std if weighted_std > 0 else 0.0

    # Total inherited stats (sanity check — should be invariant)
    random_arr = np.array(random_totals, dtype=float)
    random_mean = float(np.mean(random_arr))
    random_std = float(np.std(random_arr))

    # Per-step random distribution (mean and std at each step)
    random_matrix = np.array(random_curves, dtype=float)
    per_step_random_mean = [float(v) for v in np.mean(random_matrix, axis=0)]
    per_step_random_std = [float(v) for v in np.std(random_matrix, axis=0)]

    return {
        "actual_order": names,
        "actual_inheritance": actual_inheritance,
        "actual_total_inherited": actual_total_inherited,
        "actual_curve": actual_curve,
        "actual_weighted_score": round(actual_weighted, 2),
        "random_mean_total": round(random_mean, 2),
        "random_std_total": round(random_std, 2),
        "random_median_total": int(np.median(random_arr)),
        "random_mean_weighted": round(weighted_mean, 2),
        "random_std_weighted": round(weighted_std, 2),
        "p_value": round(p_value, 4),
        "effect_size": round(effect_size, 3),
        "n_simulations": n_simulations,
        "per_step_random_mean": [round(v, 1) for v in per_step_random_mean],
        "per_step_random_std": [round(v, 1) for v in per_step_random_std],
        "interpretation": _interpret_monte_carlo(p_value, effect_size, actual_weighted, weighted_mean),
    }


def _interpret_monte_carlo(
    p_value: float, effect_size: float, actual: float, random_mean: float
) -> str:
    direction = "more early" if actual > random_mean else "less early"
    sig = "statistically significant" if p_value < 0.05 else "not statistically significant"
    mag = (
        "large" if abs(effect_size) > 0.8
        else "medium" if abs(effect_size) > 0.5
        else "small" if abs(effect_size) > 0.2
        else "negligible"
    )
    return (
        f"Actual ordering front-loads {direction} inheritance (weighted score "
        f"{actual:.1f} vs random mean {random_mean:.1f}). "
        f"Effect size: {mag} (d={effect_size:.2f}). "
        f"p={p_value:.3f} ({sig})."
    )
