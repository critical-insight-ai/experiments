"""EX-1: Compositional Coverage — run the full experiment.

Usage:
    python -m experiments.ex1_compositional_coverage.run [--cognos-root PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cognos_measure.composition import (
    activation_census,
    cumulative_saturation,
    fit_saturation_curve,
    kind_classification,
    pairwise_jaccard,
)
from cognos_measure.compression import cognitive_load_estimate, specification_sparsity
from cognos_measure.io import find_yaml_files, load_all_yaml, extract_crd_kinds
from cognos_measure.schemas import ExperimentResult, EvidenceLevel, Status

# Workload bundle locations relative to CognOS repo root
WORKLOAD_PATHS: dict[str, str | list[str]] = {
    "agentic-horizons": "deploy/docker/bundles/demos/podcast/agentic-horizons-bundle.yaml",
    "diana": "deploy/docker/bundles/demos/diana/diana-intelligence-workload.yaml",
    "prescience": "deploy/docker/bundles/demos/prescience/prescience-forecasting-workload.yaml",
    "crucible": "deploy/docker/bundles/demos/crucible",  # directory with multiple files
    "software-engineering": "deploy/docker/bundles/demos/software-engineering",  # directory
    "resale": "deploy/docker/bundles/demos/resale/resale-inventory-workload.yaml",
    "blackjack": "deploy/docker/bundles/demos/blackjack",  # directory
    "tts": "deploy/docker/bundles/demos/tts",  # directory
}

# Chronological build order for saturation curve
BUILD_ORDER = [
    "agentic-horizons",  # Feb 23-28
    "diana",             # Mar 5-9
    "prescience",        # Mar 9-14
    "crucible",          # Mar 13-18
    "software-engineering",  # Mar 20-Apr 1
    "resale",            # Design+prototype
    "blackjack",         # Prototype
    "tts",               # Prototype
]

TOTAL_CRD_KINDS = 164
PLATFORM_LINES = 1_178_432


def load_workload_kinds(cognos_root: Path) -> dict[str, list[str]]:
    """Load CRD kinds for each workload from YAML bundles."""
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


def run(cognos_root: Path) -> ExperimentResult:
    """Run the full EX-1 experiment."""
    result = ExperimentResult(
        experiment_id="EX-1",
        hypothesis="H-2: CognOS's CRD kinds form a compositionally complete vocabulary",
        status=Status.RUNNING,
        evidence_level=EvidenceLevel.OBSERVATIONAL,
    )

    print("EX-1: Compositional Coverage Measurement")
    print("=" * 50)

    # --- Step 1: Load workloads ---
    print("\n1. Loading workload YAML bundles...")
    workloads = load_workload_kinds(cognos_root)
    for name, kinds in workloads.items():
        print(f"   {name}: {len(set(kinds))} unique kinds")

    # --- Step 2: Activation census ---
    print("\n2. Computing activation census...")
    census = activation_census(workloads, total_kinds=TOTAL_CRD_KINDS)
    result.add("union_size", census["union_size"])
    result.add("total_kinds", TOTAL_CRD_KINDS)
    result.add("coverage_ratio", round(census["coverage_ratio"], 4))
    print(f"   Union: {census['union_size']}/{TOTAL_CRD_KINDS} kinds ({census['coverage_ratio']:.1%})")

    # --- Step 3: Frequency distribution ---
    print("\n3. Kind frequency distribution (top 10):")
    for kind, count in list(census["frequency"].items())[:10]:
        print(f"   {kind}: {count} workloads")

    classification = kind_classification(census["frequency"], total_workloads=len(workloads))
    result.add("universal_kinds", len(classification["universal"]))
    result.add("common_kinds", len(classification["common"]))
    result.add("domain_specific_kinds", len(classification["domain_specific"]))
    result.add("rare_kinds", len(classification["rare"]))
    print(f"\n   Universal: {len(classification['universal'])}")
    print(f"   Common: {len(classification['common'])}")
    print(f"   Domain-specific: {len(classification['domain_specific'])}")
    print(f"   Rare (1 workload): {len(classification['rare'])}")

    # --- Step 4: Pairwise Jaccard ---
    print("\n4. Pairwise Jaccard similarity:")
    jaccard = pairwise_jaccard(workloads)
    for (a, b), j in sorted(jaccard.items(), key=lambda x: -x[1])[:5]:
        print(f"   {a} <-> {b}: {j:.3f}")

    # --- Step 5: Saturation curve ---
    print("\n5. Cumulative saturation curve:")
    ordered = [(name, workloads[name]) for name in BUILD_ORDER if name in workloads]
    trajectory = cumulative_saturation(ordered, total_kinds=TOTAL_CRD_KINDS)
    for t in trajectory:
        print(f"   +{t['workload']}: {t['cumulative']} kinds ({t['coverage_ratio']:.1%}), +{t['new_kinds']} new")

    fit = fit_saturation_curve(trajectory)
    result.add("saturation_a", fit["a"])
    result.add("saturation_b", fit["b"])
    result.add("saturation_r_squared", fit["r_squared"])
    print(f"\n   Log fit: coverage = {fit['a']:.1f} * ln(step) + {fit['b']:.1f}  (R² = {fit['r_squared']:.3f})")

    # --- Step 6: Compression metrics ---
    print("\n6. Compression metrics:")
    total_yaml_lines = sum(
        sum(1 for _ in open(cognos_root / p, encoding="utf-8"))
        if (cognos_root / p).is_file()
        else sum(
            sum(1 for _ in open(f, encoding="utf-8"))
            for f in find_yaml_files(cognos_root / p)
        )
        if (cognos_root / p).is_dir()
        else 0
        for p in WORKLOAD_PATHS.values()
    )
    sparsity = specification_sparsity(PLATFORM_LINES, total_yaml_lines)
    result.add("total_yaml_lines", total_yaml_lines)
    result.add("sparsity_ratio", sparsity["sparsity_ratio"])
    print(f"   Total workload YAML: {total_yaml_lines:,} lines")
    print(f"   Platform: {PLATFORM_LINES:,} lines")
    print(f"   Sparsity ratio: {sparsity['label']}")

    # Cognitive load per workload
    for name, kinds in workloads.items():
        cl = cognitive_load_estimate(len(set(kinds)))
        if not cl["fits_in_memory"]:
            print(f"   Warning: {name} ({len(set(kinds))} kinds) may exceed cognitive capacity")

    # --- Summarize ---
    result.status = Status.COMPLETED
    result.interpretation = (
        f"CRD vocabulary covers {census['coverage_ratio']:.1%} of available kinds across "
        f"{len(workloads)} workloads spanning {len(workloads)} domains. "
        f"Logarithmic saturation (R²={fit['r_squared']:.3f}) indicates compositional completeness: "
        f"early workloads discover most kinds, later workloads reuse existing vocabulary. "
        f"Specification sparsity ratio: {sparsity['label']}."
    )
    result.caveats = [
        "N=1 builder: all workloads designed by same person",
        f"{100 - census['coverage_ratio'] * 100:.0f}% of CRD kinds remain unactivated",
        "No formal proof of completeness; empirical coverage only",
    ]

    result.metadata = {
        "census": census,
        "classification": classification,
        "jaccard_top5": {f"{a}-{b}": j for (a, b), j in sorted(jaccard.items(), key=lambda x: -x[1])[:5]},
        "trajectory": trajectory,
        "saturation_fit": fit,
        "sparsity": sparsity,
    }

    print("\n" + "=" * 50)
    print(f"Result: {result.interpretation}")
    print(f"Caveats: {'; '.join(result.caveats)}")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="EX-1: Compositional Coverage")
    parser.add_argument(
        "--cognos-root",
        type=Path,
        default=Path(r"C:\Source\CriticalInsight\Cognos"),
        help="Path to CognOS repo root",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "results" / "ex1_results.json",
        help="Output path for results JSON",
    )
    args = parser.parse_args()

    result = run(args.cognos_root)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result.summary(), indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\nResults written to {args.output}")


if __name__ == "__main__":
    main()
