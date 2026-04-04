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

# ---------------------------------------------------------------------------
# Tier 1: Production workloads (deploy/docker/bundles/demos/)
#   These are full, self-contained workloads built for specific domains.
# ---------------------------------------------------------------------------
PRODUCTION_WORKLOADS: dict[str, str] = {
    "agentic-horizons": "deploy/docker/bundles/demos/podcast/agentic-horizons-bundle.yaml",
    "diana": "deploy/docker/bundles/demos/diana/diana-intelligence-workload.yaml",
    "prescience": "deploy/docker/bundles/demos/prescience/prescience-forecasting-workload.yaml",
    "crucible": "deploy/docker/bundles/demos/crucible",
    "software-engineering": "deploy/docker/bundles/demos/software-engineering",
    "resale": "deploy/docker/bundles/demos/resale/resale-inventory-workload.yaml",
    "blackjack": "deploy/docker/bundles/demos/blackjack",
    "tts": "deploy/docker/bundles/demos/tts",
    "cognos-self-monitoring": "deploy/docker/bundles/demos/cognos-self-monitoring",
    "knowledge-federation": "deploy/docker/bundles/demos/knowledge-federation",
    "media-production": "deploy/docker/bundles/demos/media-production/media-production-pipeline.yaml",
    "ml-training": "deploy/docker/bundles/demos/ml-training/ml-training-pipeline.yaml",
    "security-ops": "deploy/docker/bundles/demos/security-ops",
}

# ---------------------------------------------------------------------------
# Tier 2: Scenario bundles (docs/demos/acme-briefing/)
#   These are capability demos — each explores a CRD combination pattern.
#   Experiment overlay bundles (ex-6-*) are excluded: they are additive
#   overlays on a base bundle, not standalone workloads.
# ---------------------------------------------------------------------------
SCENARIO_BUNDLES: dict[str, str] = {
    "acme-briefing": "docs/demos/acme-briefing/acme-briefing-bundle.yaml",
    "threat-intelligence": "docs/demos/acme-briefing/threat-intelligence-bundle.yaml",
    "supply-chain": "docs/demos/acme-briefing/supply-chain-analytics-bundle.yaml",
    "portfolio-analytics": "docs/demos/acme-briefing/portfolio-analytics-bundle.yaml",
    "web-research": "docs/demos/acme-briefing/web-research-bundle.yaml",
    "negotiation": "docs/demos/acme-briefing/negotiation-bundle.yaml",
    "game-theory": "docs/demos/acme-briefing/game-theory-bundle.yaml",
    "incident-warroom": "docs/demos/acme-briefing/incident-warroom-bundle.yaml",
    "order-review": "docs/demos/acme-briefing/order-review-bundle.yaml",
    "iterative-report": "docs/demos/acme-briefing/iterative-report-bundle.yaml",
    "knowledge-investigation": "docs/demos/acme-briefing/knowledge-investigation-bundle.yaml",
    "graph-document": "docs/demos/acme-briefing/graph-document-bundle.yaml",
    "spatial-memory": "docs/demos/acme-briefing/spatial-memory-bundle.yaml",
    "multi-memory": "docs/demos/acme-briefing/multi-memory-bundle.yaml",
    "model-hub": "docs/demos/acme-briefing/model-hub-bundle.yaml",
    "model-routing": "docs/demos/acme-briefing/model-routing-bundle.yaml",
    "ml-experiment": "docs/demos/acme-briefing/ml-experiment-bundle.yaml",
    "channel-review": "docs/demos/acme-briefing/channel-review-bundle.yaml",
    "compliance-audit": "docs/demos/acme-briefing/compliance-audit-bundle.yaml",
    "doc-automation": "docs/demos/acme-briefing/doc-automation-bundle.yaml",
    "event-subscription": "docs/demos/acme-briefing/event-subscription-bundle.yaml",
    "ex-6-7-cooperative-antagonism": "docs/demos/acme-briefing/ex-6-7-cooperative-antagonism-bundle.yaml",
}

# Chronological build order for saturation curve (production workloads only)
BUILD_ORDER = [
    "agentic-horizons",       # Feb 23-28
    "diana",                   # Mar 5-9
    "prescience",              # Mar 9-14
    "crucible",                # Mar 13-18
    "software-engineering",    # Mar 20-Apr 1
    "resale",                  # Design+prototype
    "blackjack",               # Prototype
    "tts",                     # Prototype
    "cognos-self-monitoring",  # Observability workload
    "knowledge-federation",    # Cross-tenant knowledge
    "media-production",        # Media pipeline
    "ml-training",             # ML pipeline
    "security-ops",            # SOC autonomous monitoring
]

# Runtime truth from `cognos crds list` (April 4, 2026)
# 162 registrations across 7 API groups; 159 unique kind names
# (Document, GateProfile, ProviderBinding each in 2 groups — intentional)
TOTAL_CRD_KINDS = 159
PLATFORM_LINES = 1_178_432


def _load_bundle(cognos_root: Path, rel_path: str) -> list[str]:
    """Load CRD kinds from a single bundle path (file or directory)."""
    full_path = cognos_root / rel_path
    if full_path.is_dir():
        yaml_files = find_yaml_files(full_path)
        all_docs: list[dict] = []
        for f in yaml_files:
            try:
                docs = load_all_yaml(f)
                all_docs.extend(d for d in docs if isinstance(d, dict))
            except Exception as e:
                print(f"  Warning: failed to parse {f}: {e}", file=sys.stderr)
        return extract_crd_kinds(all_docs)
    elif full_path.is_file():
        try:
            docs = load_all_yaml(full_path)
            docs = [d for d in docs if isinstance(d, dict)]
            return extract_crd_kinds(docs)
        except Exception as e:
            print(f"  Warning: failed to parse {full_path}: {e}", file=sys.stderr)
            return []
    else:
        print(f"  Warning: path not found: {full_path}", file=sys.stderr)
        return []


def load_workload_kinds(
    cognos_root: Path,
    paths: dict[str, str],
) -> dict[str, list[str]]:
    """Load CRD kinds for each workload from YAML bundles."""
    return {name: _load_bundle(cognos_root, rel) for name, rel in paths.items()}


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

    # --- Step 1: Load workloads (both tiers) ---
    print("\n1. Loading workload YAML bundles...")
    print("  Tier 1: Production workloads (deploy/docker/bundles/demos/)")
    production = load_workload_kinds(cognos_root, PRODUCTION_WORKLOADS)
    for name, kinds in production.items():
        print(f"   {name}: {len(set(kinds))} unique kinds")

    print("  Tier 2: Scenario bundles (docs/demos/acme-briefing/)")
    scenarios = load_workload_kinds(cognos_root, SCENARIO_BUNDLES)
    for name, kinds in scenarios.items():
        print(f"   {name}: {len(set(kinds))} unique kinds")

    # Combined for union/overlap analysis
    workloads = {**production, **scenarios}
    result.add("production_count", len(production))
    result.add("scenario_count", len(scenarios))
    result.add("total_workload_count", len(workloads))

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

    # --- Step 5: Saturation curve (production workloads only — chronological) ---
    print("\n5. Cumulative saturation curve (production workloads):")
    ordered = [(name, production[name]) for name in BUILD_ORDER if name in production]
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
    all_paths = {**PRODUCTION_WORKLOADS, **SCENARIO_BUNDLES}
    total_yaml_lines = sum(
        sum(1 for _ in open(cognos_root / p, encoding="utf-8"))
        if (cognos_root / p).is_file()
        else sum(
            sum(1 for _ in open(f, encoding="utf-8"))
            for f in find_yaml_files(cognos_root / p)
        )
        if (cognos_root / p).is_dir()
        else 0
        for p in all_paths.values()
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
    # Also compute production-only coverage
    prod_census = activation_census(production, total_kinds=TOTAL_CRD_KINDS)
    result.add("production_union_size", prod_census["union_size"])
    result.add("production_coverage_ratio", round(prod_census["coverage_ratio"], 4))
    print(f"\n   Production-only coverage: {prod_census['union_size']}/{TOTAL_CRD_KINDS} "
          f"({prod_census['coverage_ratio']:.1%})")

    result.status = Status.COMPLETED
    result.interpretation = (
        f"CRD vocabulary covers {census['coverage_ratio']:.1%} of {TOTAL_CRD_KINDS} unique kinds "
        f"across {len(workloads)} workloads ({len(production)} production + {len(scenarios)} scenarios). "
        f"Production workloads alone activate {prod_census['coverage_ratio']:.1%}. "
        f"Logarithmic saturation (R\u00b2={fit['r_squared']:.3f}) indicates compositional completeness: "
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
