"""EX-6.2: GI Balance vs Quality — correlate GI dynamics with quality proxies.

Tests H-1.2: balanced GI ratios correlate with higher-quality outputs.

Usage:
    python -m experiments.ex6_2_gi_quality.run --repo C:\\Source\\CriticalInsight\\Cognos
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import stats as sp_stats

from cognos_measure.gi import (
    classify_commit_message,
    gi_ratio,
    sprint_quality_proxies,
    GIPhase,
)
from cognos_measure.io import iter_git_log
from cognos_measure.schemas import ExperimentResult, EvidenceLevel, Status


# Development phases + workload sprints for granular analysis
SEGMENTS = [
    # Major development phases
    ("P1: Hardening", "2025-12-03", "2025-12-31"),
    ("P2: Surface polish", "2026-01-01", "2026-01-31"),
    ("P3: Release prep", "2026-02-01", "2026-02-14"),
    # Workload sprints (more granular)
    ("WL: Agentic Horizons", "2026-02-23", "2026-02-28"),
    ("WL: DIANA", "2026-03-05", "2026-03-09"),
    ("WL: Prescience", "2026-03-09", "2026-03-14"),
    ("WL: Crucible", "2026-03-13", "2026-03-18"),
    ("WL: Software Engineering", "2026-03-20", "2026-04-01"),
]


def segment_commits(
    commits: list[dict[str, str]],
    segments: list[tuple[str, str, str]],
) -> dict[str, list[dict[str, str]]]:
    """Assign commits to named segments by date range."""
    result: dict[str, list[dict[str, str]]] = {}
    for label, start, end in segments:
        result[label] = [
            c for c in commits
            if start <= c["date"][:10] <= end
        ]
    return result


def run(repo_path: Path) -> ExperimentResult:
    """Run the full EX-6.2 experiment."""
    result = ExperimentResult(
        experiment_id="EX-6.2",
        hypothesis="H-1.2: GI balance correlates with output quality proxies",
        status=Status.RUNNING,
        evidence_level=EvidenceLevel.OBSERVATIONAL,
    )

    print("EX-6.2: GI Balance vs Quality Correlation")
    print("=" * 50)

    # --- Step 1: Load commits ---
    print(f"\n1. Loading Git history from {repo_path}...")
    commits = list(iter_git_log(repo_path))
    commits.reverse()  # chronological
    print(f"   Loaded {len(commits)} commits")

    # --- Step 2: Segment commits ---
    print("\n2. Segmenting into development phases and workload sprints...")
    segmented = segment_commits(commits, SEGMENTS)
    for label, seg_commits in segmented.items():
        print(f"   {label}: {len(seg_commits)} commits")

    # --- Step 3: Compute quality proxies per segment ---
    print("\n3. Computing quality proxies per segment...")
    segment_metrics: list[dict] = []
    for label, seg_commits in segmented.items():
        if len(seg_commits) < 3:
            print(f"   {label}: skipped (only {len(seg_commits)} commits)")
            continue

        metrics = sprint_quality_proxies(seg_commits, label=label)
        segment_metrics.append(metrics)

        print(
            f"   {label}: Q={metrics['quality_score']:.1f}/10, "
            f"GI={metrics['gi_ratio']:.2f}, "
            f"|bal|={metrics['balance_distance']:.2f}, "
            f"fix={metrics['fix_density']:.1%}, "
            f"test={metrics['test_density']:.1%}"
        )

    # --- Step 4: Correlation analysis ---
    print("\n4. Correlation analysis: |GI balance| vs quality score...")
    if len(segment_metrics) >= 4:
        balance_distances = np.array([m["balance_distance"] for m in segment_metrics])
        quality_scores = np.array([m["quality_score"] for m in segment_metrics])
        fix_densities = np.array([m["fix_density"] for m in segment_metrics])

        # Spearman correlation: balance_distance vs quality (expect negative — closer to balance = higher quality)
        rho_quality, p_quality = sp_stats.spearmanr(balance_distances, quality_scores)
        # Spearman correlation: balance_distance vs fix density (expect positive — imbalance = more fixes)
        rho_fix, p_fix = sp_stats.spearmanr(balance_distances, fix_densities)

        result.add("spearman_rho_balance_quality", round(float(rho_quality), 4))
        result.add("spearman_p_balance_quality", round(float(p_quality), 4))
        result.add("spearman_rho_balance_fixes", round(float(rho_fix), 4))
        result.add("spearman_p_balance_fixes", round(float(p_fix), 4))

        print(f"   |balance| vs quality: rho={rho_quality:.3f}, p={p_quality:.3f}")
        print(f"   |balance| vs fix_density: rho={rho_fix:.3f}, p={p_fix:.3f}")

        # Interpretation
        if p_quality < 0.05 and rho_quality < 0:
            balance_finding = "Significant negative correlation: closer to GI balance = higher quality"
        elif p_quality < 0.05 and rho_quality > 0:
            balance_finding = "Unexpected: GI imbalance correlates with HIGHER quality (integration-heavy phases may be healthy)"
        else:
            balance_finding = f"No significant correlation (p={p_quality:.3f})"

        print(f"\n   Finding: {balance_finding}")
    else:
        balance_finding = "Insufficient segments for correlation (need >= 4)"
        rho_quality = float("nan")
        p_quality = float("nan")
        print(f"   {balance_finding}")

    # --- Step 5: Phase comparison ---
    print("\n5. Phase comparison (development vs workload sprints):")
    dev_phases = [m for m in segment_metrics if m["label"].startswith("P")]
    wl_sprints = [m for m in segment_metrics if m["label"].startswith("WL")]

    if dev_phases and wl_sprints:
        dev_avg_quality = np.mean([m["quality_score"] for m in dev_phases])
        wl_avg_quality = np.mean([m["quality_score"] for m in wl_sprints])
        dev_avg_balance = np.mean([m["balance_distance"] for m in dev_phases])
        wl_avg_balance = np.mean([m["balance_distance"] for m in wl_sprints])

        result.add("dev_avg_quality", round(float(dev_avg_quality), 2))
        result.add("wl_avg_quality", round(float(wl_avg_quality), 2))
        result.add("dev_avg_balance_distance", round(float(dev_avg_balance), 3))
        result.add("wl_avg_balance_distance", round(float(wl_avg_balance), 3))

        print(f"   Development phases: avg quality={dev_avg_quality:.1f}, avg |balance|={dev_avg_balance:.2f}")
        print(f"   Workload sprints:   avg quality={wl_avg_quality:.1f}, avg |balance|={wl_avg_balance:.2f}")

    # --- Step 6: Ranked segments ---
    print("\n6. Segments ranked by quality score:")
    for m in sorted(segment_metrics, key=lambda x: -x["quality_score"]):
        print(
            f"   {m['quality_score']:5.1f}/10  {m['label']:<25s}  "
            f"GI={m['gi_ratio']:.2f}  |bal|={m['balance_distance']:.2f}  "
            f"fix={m['fix_density']:.1%}"
        )

    # --- Summarize ---
    result.status = Status.COMPLETED
    n_segments = len(segment_metrics)
    result.interpretation = (
        f"Analyzed {n_segments} development segments. {balance_finding}. "
        f"Quality proxy combines fix density (35%), test density (25%), "
        f"GI balance (25%), documentation (15%)."
    )
    result.caveats = [
        "Quality proxies are commit-derived, not ground-truth quality assessments",
        "Composite score weights are heuristic, not empirically calibrated",
        "Small N (segments) limits statistical power",
        "Sprint date ranges may overlap slightly",
    ]
    result.metadata = {
        "segments": segment_metrics,
        "correlation": {
            "rho_balance_quality": round(float(rho_quality), 4) if not np.isnan(rho_quality) else None,
            "p_balance_quality": round(float(p_quality), 4) if not np.isnan(p_quality) else None,
        },
    }

    print("\n" + "=" * 50)
    print(f"Result: {result.interpretation}")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="EX-6.2: GI Balance vs Quality")
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(r"C:\Source\CriticalInsight\Cognos"),
        help="Path to CognOS Git repository",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "results" / "ex6_2_results.json",
        help="Output path for results JSON",
    )
    args = parser.parse_args()

    result = run(args.repo)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result.summary(), indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\nResults written to {args.output}")


if __name__ == "__main__":
    main()
