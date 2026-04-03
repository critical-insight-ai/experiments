"""Compression metrics — specification sparsity, activation ratio, cognitive load."""

from __future__ import annotations

from typing import Any


def specification_sparsity(
    platform_lines: int,
    workload_lines: int,
) -> dict[str, float]:
    """Compute specification sparsity ratio.

    This is the cognitive ratio: how much the developer writes relative to what exists.
    326:1 means the developer reasons about 3,611 lines, not 1.18M.
    """
    ratio = platform_lines / workload_lines if workload_lines > 0 else 0.0
    return {
        "platform_lines": platform_lines,
        "workload_lines": workload_lines,
        "sparsity_ratio": round(ratio, 1),
        "label": f"{ratio:.0f}:1",
    }


def code_activation_ratio(
    total_platform_lines: int,
    activated_lines: int,
) -> dict[str, float]:
    """Compute code activation ratio.

    This is the engineering ratio: how much platform code actually runs
    for a given workload.
    """
    ratio = total_platform_lines / activated_lines if activated_lines > 0 else 0.0
    pct = (activated_lines / total_platform_lines * 100) if total_platform_lines > 0 else 0.0
    return {
        "total_lines": total_platform_lines,
        "activated_lines": activated_lines,
        "activation_ratio": round(ratio, 1),
        "activation_pct": round(pct, 1),
        "label": f"{ratio:.1f}:1",
    }


def compression_stack(
    layers: list[dict[str, Any]],
) -> dict[str, Any]:
    """Analyze a multi-layer compression stack.

    Each layer dict should have: name, input_size, output_size, description.
    Computes per-layer and cumulative compression ratios.
    """
    analyzed = []
    cumulative_ratio = 1.0

    for layer in layers:
        inp = layer.get("input_size", 0)
        out = layer.get("output_size", 0)
        ratio = inp / out if out > 0 else 0.0
        cumulative_ratio *= ratio
        analyzed.append({
            **layer,
            "ratio": round(ratio, 1),
            "cumulative_ratio": round(cumulative_ratio, 1),
        })

    return {
        "layers": analyzed,
        "total_layers": len(layers),
        "cumulative_ratio": round(cumulative_ratio, 1),
    }


def cognitive_load_estimate(
    crd_count: int,
    avg_fields_per_crd: float = 8.0,
    millers_constant: int = 7,
    chunking_levels: int = 3,
) -> dict[str, Any]:
    """Estimate cognitive load of a workload specification.

    Uses Miller's chunking model: capacity = k^levels where k is chunk size.
    Returns whether the workload fits within cognitive capacity.
    """
    total_fields = int(crd_count * avg_fields_per_crd)
    capacity = millers_constant ** chunking_levels  # e.g. 7^3 = 343

    return {
        "crd_count": crd_count,
        "estimated_fields": total_fields,
        "millers_capacity": capacity,
        "chunking_levels": chunking_levels,
        "fits_in_memory": total_fields <= capacity,
        "utilization_pct": round(total_fields / capacity * 100, 1),
    }
