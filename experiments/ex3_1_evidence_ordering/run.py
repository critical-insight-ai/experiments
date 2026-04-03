"""EX-3.1: Evidence Ordering — Monte Carlo test for build order compounding.

Tests H-3: workload build order produces more CRD inheritance (compounding)
than random orderings, indicating deliberate or emergent optimization.

Usage:
    python -m experiments.ex3_1_evidence_ordering.run --cognos-root C:\\Source\\CriticalInsight\\Cognos
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from cognos_measure.composition import (
    cumulative_saturation,
    inheritance_per_step,
    monte_carlo_ordering,
)
from cognos_measure.io import extract_crd_kinds, find_yaml_files, load_all_yaml
from cognos_measure.schemas import ExperimentResult, EvidenceLevel, Status


# Reuse workload paths from EX-1
WORKLOAD_PATHS: dict[str, str] = {
    "agentic-horizons": "deploy/docker/bundles/demos/podcast/agentic-horizons-bundle.yaml",
    "diana": "deploy/docker/bundles/demos/diana/diana-intelligence-workload.yaml",
    "prescience": "deploy/docker/bundles/demos/prescience/prescience-forecasting-workload.yaml",
    "crucible": "deploy/docker/bundles/demos/crucible",
    "software-engineering": "deploy/docker/bundles/demos/software-engineering",
    "resale": "deploy/docker/bundles/demos/resale/resale-inventory-workload.yaml",
    "blackjack": "deploy/docker/bundles/demos/blackjack",
    "tts": "deploy/docker/bundles/demos/tts",
}

BUILD_ORDER = [
    "agentic-horizons",
    "diana",
    "prescience",
    "crucible",
    "software-engineering",
    "resale",
    "blackjack",
    "tts",
]


def load_workload_kinds(cognos_root: Path) -> dict[str, list[str]]:
    """Load CRD kinds per workload from YAML bundles."""
    workloads: dict[str, list[str]] = {}
    for name, rel_path in WORKLOAD_PATHS.items():
        full_path = cognos_root / rel_path
        if full_path.is_dir():
            yaml_files = find_yaml_files(full_path)
            all_docs = []
            for f in yaml_files:
                try:
                    docs = load_all_yaml(f)
                    all_docs.extend(d for d in docs if isinstance(d, dict))
                except Exception as e:
                    print(f"  Warning: failed to parse {f}: {e}", file=sys.stderr)
            workloads[name] = extract_crd_kinds(all_docs)
        elif full_path.is_file():
            try:
                docs = load_all_yaml(full_path)
                docs = [d for d in docs if isinstance(d, dict)]
                workloads[name] = extract_crd_kinds(docs)
            except Exception as e:
                print(f"  Warning: failed to parse {full_path}: {e}", file=sys.stderr)
                workloads[name] = []
        else:
            print(f"  Warning: path not found: {full_path}", file=sys.stderr)
            workloads[name] = []
    return workloads


def run(cognos_root: Path, n_simulations: int = 10_000) -> ExperimentResult:
    """Run the full EX-3.1 experiment."""
    result = ExperimentResult(
        experiment_id="EX-3.1",
        hypothesis="H-3: Build order produces more CRD inheritance than random",
        status=Status.RUNNING,
        evidence_level=EvidenceLevel.COMPARATIVE,
    )

    print("EX-3.1: Evidence Ordering — Monte Carlo Compounding Test")
    print("=" * 50)

    # --- Step 1: Load workloads ---
    print("\n1. Loading workload CRD kinds...")
    workloads = load_workload_kinds(cognos_root)
    for name, kinds in workloads.items():
        print(f"   {name}: {len(set(kinds))} unique kinds")

    # --- Step 2: Actual inheritance curve ---
    print("\n2. Actual build order inheritance:")
    actual_items = [(name, workloads[name]) for name in BUILD_ORDER if name in workloads]
    actual_inheritance = inheritance_per_step(actual_items)
    for step in actual_inheritance:
        print(
            f"   Step {step['step']}: {step['name']:<25s} "
            f"{step['inherited']:2d}/{step['total_kinds']:2d} inherited "
            f"({step['inheritance_pct']:.0f}%)"
        )

    actual_total = sum(s["inherited"] for s in actual_inheritance)
    result.add("actual_total_inherited", actual_total)
    print(f"\n   Total inherited across all steps: {actual_total}")

    # --- Step 3: Cumulative new-kind trajectory ---
    print("\n3. Cumulative saturation (new kinds per step):")
    trajectory = cumulative_saturation(actual_items)
    for t in trajectory:
        print(
            f"   +{t['workload']:<25s} +{t['new_kinds']:2d} new, "
            f"{t['cumulative']:2d} cumulative"
        )

    # --- Step 4: Monte Carlo simulation ---
    print(f"\n4. Monte Carlo simulation ({n_simulations:,} random orderings)...")
    mc = monte_carlo_ordering(
        workloads, BUILD_ORDER,
        n_simulations=n_simulations,
        seed=42,
    )

    result.add("random_mean_inherited", mc["random_mean_total"])
    result.add("random_std_inherited", mc["random_std_total"])
    result.add("random_median_inherited", mc["random_median_total"])
    result.add("actual_weighted_score", mc["actual_weighted_score"])
    result.add("random_mean_weighted", mc["random_mean_weighted"])
    result.add("random_std_weighted", mc["random_std_weighted"])
    result.add("p_value", mc["p_value"])
    result.add("effect_size_cohens_d", mc["effect_size"])
    result.add("n_simulations", n_simulations)

    print(f"   Actual total inherited: {actual_total}")
    print(f"   Random mean total:  {mc['random_mean_total']:.1f} (invariant — sanity check)")
    print(f"\n   Weighted score (front-loading metric):")
    print(f"   Actual weighted:  {mc['actual_weighted_score']:.1f}")
    print(f"   Random weighted:  {mc['random_mean_weighted']:.1f} (std={mc['random_std_weighted']:.1f})")
    print(f"   p-value: {mc['p_value']:.4f}")
    print(f"   Effect size (Cohen's d): {mc['effect_size']:.3f}")
    print(f"\n   {mc['interpretation']}")

    # --- Step 5: Per-step comparison ---
    print("\n5. Per-step: actual vs random mean inheritance %:")
    for i, step in enumerate(actual_inheritance):
        actual_pct = step["inheritance_pct"]
        random_mean_pct = mc["per_step_random_mean"][i]
        random_std_pct = mc["per_step_random_std"][i]
        diff = actual_pct - random_mean_pct
        marker = " ***" if abs(diff) > random_std_pct else ""
        print(
            f"   {step['name']:<25s} actual={actual_pct:5.1f}%  "
            f"random={random_mean_pct:5.1f}% (+/-{random_std_pct:.1f}%)  "
            f"diff={diff:+.1f}%{marker}"
        )

    # --- Step 6: Acceleration index ---
    print("\n6. Compounding acceleration:")
    late_steps = actual_inheritance[3:]  # steps 4+ where compounding should show
    if late_steps:
        late_actual_pct = np.mean([s["inheritance_pct"] for s in late_steps])
        late_random_mean = np.mean(mc["per_step_random_mean"][3:])
        acceleration = late_actual_pct / late_random_mean if late_random_mean > 0 else float("inf")
        result.add("late_stage_acceleration", round(float(acceleration), 3))
        print(f"   Late-stage (steps 4+) actual avg: {late_actual_pct:.1f}%")
        print(f"   Late-stage random avg: {late_random_mean:.1f}%")
        print(f"   Acceleration index: {acceleration:.2f}x")

    # --- Summarize ---
    result.status = Status.COMPLETED
    result.interpretation = (
        f"Monte Carlo test ({n_simulations:,} shuffles): {mc['interpretation']} "
        f"Actual build order inherits {actual_total} CRD kinds across {len(actual_inheritance)} steps."
    )
    result.caveats = [
        "Inheritance counts CRD kind names, not instances — a kind used 50x counts same as 1x",
        "N=1 build sequence (cannot randomize reality, only compare to random baseline)",
        "Small number of workloads (8) limits statistical resolution",
        "Blackjack and TTS are prototypes with minimal kinds, reducing late-stage signal",
    ]
    result.metadata = {
        "actual_inheritance": actual_inheritance,
        "monte_carlo": {
            "p_value": mc["p_value"],
            "effect_size": mc["effect_size"],
            "actual_total": actual_total,
            "random_mean": mc["random_mean_total"],
            "random_std": mc["random_std_total"],
            "per_step_comparison": [
                {
                    "name": step["name"],
                    "actual_pct": step["inheritance_pct"],
                    "random_mean_pct": mc["per_step_random_mean"][i],
                    "random_std_pct": mc["per_step_random_std"][i],
                }
                for i, step in enumerate(actual_inheritance)
            ],
        },
    }

    print("\n" + "=" * 50)
    print(f"Result: {result.interpretation}")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="EX-3.1: Evidence Ordering Monte Carlo")
    parser.add_argument(
        "--cognos-root",
        type=Path,
        default=Path(r"C:\Source\CriticalInsight\Cognos"),
        help="Path to CognOS repository root",
    )
    parser.add_argument(
        "--simulations",
        type=int,
        default=10_000,
        help="Number of Monte Carlo simulations",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "results" / "ex3_1_results.json",
        help="Output path for results JSON",
    )
    args = parser.parse_args()

    result = run(args.cognos_root, n_simulations=args.simulations)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result.summary(), indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\nResults written to {args.output}")


if __name__ == "__main__":
    main()
