"""EX-6.2: GI Balance vs Quality — correlate GI dynamics with quality proxies.

Tests H-1.2: balanced GI ratios correlate with higher-quality outputs.

Uses three complementary segmentation strategies to maximise statistical
power from a single repository's history:

  1. **Weekly bins** (primary) — ISO-week non-overlapping bins give N ~ 17-18
     data points and serve as the main Spearman test.
  2. **Bootstrap permutation** — 10 000-resample CI on rho for robustness.
  3. **Named phases** (secondary) — original 8 hand-curated segments for
     interpretive colour (dev vs workload, phase ranking).

Usage:
    python -m experiments.ex6_2_gi_quality.run --repo C:\\Source\\CriticalInsight\\Cognos
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy import stats as sp_stats

from cognos_measure.gi import (
    classify_commit_message,
    classify_commit_layer3,
    gi_ratio,
    sprint_quality_proxies,
    GIPhase,
)
from cognos_measure.io import iter_git_log
from cognos_measure.schemas import ExperimentResult, EvidenceLevel, Status


# Development phases + workload sprints for interpretive context
NAMED_SEGMENTS = [
    ("P1: Hardening", "2025-12-03", "2025-12-31"),
    ("P2: Surface polish", "2026-01-01", "2026-01-31"),
    ("P3: Release prep", "2026-02-01", "2026-02-14"),
    ("WL: Agentic Horizons", "2026-02-23", "2026-02-28"),
    ("WL: DIANA", "2026-03-05", "2026-03-09"),
    ("WL: Prescience", "2026-03-09", "2026-03-14"),
    ("WL: Crucible", "2026-03-13", "2026-03-18"),
    ("WL: Software Engineering", "2026-03-20", "2026-04-01"),
]

# Minimum commits per bin to compute meaningful quality metrics
MIN_BIN_SIZE = 5


def segment_commits(
    commits: list[dict],
    segments: list[tuple[str, str, str]],
) -> dict[str, list[dict]]:
    """Assign commits to named segments by date range."""
    result: dict[str, list[dict]] = {}
    for label, start, end in segments:
        result[label] = [
            c for c in commits
            if start <= c["date"][:10] <= end
        ]
    return result


def auto_segment_weekly(commits: list[dict]) -> list[tuple[str, list[dict]]]:
    """Group commits by ISO week, returning (label, commits) pairs.

    Only returns weeks with >= MIN_BIN_SIZE commits so that quality
    metrics are statistically meaningful.
    """
    by_week: dict[str, list[dict]] = defaultdict(list)
    for c in commits:
        dt = datetime.fromisoformat(c["date"][:10])
        iso_year, iso_week, _ = dt.isocalendar()
        key = f"{iso_year}-W{iso_week:02d}"
        by_week[key].append(c)

    # Sort by week label and filter out small bins
    return [
        (label, week_commits)
        for label, week_commits in sorted(by_week.items())
        if len(week_commits) >= MIN_BIN_SIZE
    ]


def bootstrap_spearman(
    x: np.ndarray,
    y: np.ndarray,
    n_resamples: int = 10_000,
    ci: float = 0.95,
    seed: int = 42,
) -> dict[str, float]:
    """Bootstrap confidence interval on Spearman rho.

    Returns dict with rho, p, ci_lo, ci_hi, resampled_mean.
    """
    rng = np.random.default_rng(seed)
    n = len(x)
    rho_obs, p_obs = sp_stats.spearmanr(x, y)

    rhos = np.empty(n_resamples, dtype=np.float64)
    for i in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        r, _ = sp_stats.spearmanr(x[idx], y[idx])
        rhos[i] = r

    alpha = (1 - ci) / 2
    ci_lo = float(np.nanpercentile(rhos, 100 * alpha))
    ci_hi = float(np.nanpercentile(rhos, 100 * (1 - alpha)))

    # Permutation p-value: fraction of resamples with |rho| >= |observed|
    perm_rhos = np.empty(n_resamples, dtype=np.float64)
    for i in range(n_resamples):
        y_perm = rng.permutation(y)
        r, _ = sp_stats.spearmanr(x, y_perm)
        perm_rhos[i] = r
    perm_p = float(np.mean(np.abs(perm_rhos) >= abs(rho_obs)))

    return {
        "rho": round(float(rho_obs), 4),
        "p_spearman": round(float(p_obs), 4),
        "p_permutation": round(perm_p, 4),
        "ci_lo": round(ci_lo, 4),
        "ci_hi": round(ci_hi, 4),
        "bootstrap_mean": round(float(np.nanmean(rhos)), 4),
        "n": int(n),
    }


def _spearman_if_enough(x: np.ndarray, y: np.ndarray, label: str) -> dict[str, float] | None:
    """Compute Spearman + bootstrap if enough data points."""
    if len(x) < 4:
        print(f"   {label}: N={len(x)} — insufficient (need >= 4)")
        return None
    bs = bootstrap_spearman(x, y)
    print(
        f"   {label} (N={bs['n']}): "
        f"rho={bs['rho']:+.3f}, "
        f"p(Spearman)={bs['p_spearman']:.3f}, "
        f"p(perm)={bs['p_permutation']:.3f}, "
        f"95% CI [{bs['ci_lo']:+.3f}, {bs['ci_hi']:+.3f}]"
    )
    return bs


def run(repo_path: Path) -> ExperimentResult:
    """Run the full EX-6.2 experiment."""
    result = ExperimentResult(
        experiment_id="EX-6.2",
        hypothesis="H-1.2: GI balance correlates with output quality proxies",
        status=Status.RUNNING,
        evidence_level=EvidenceLevel.OBSERVATIONAL,
    )

    print("EX-6.2: GI Balance vs Quality Correlation")
    print("=" * 60)

    # --- Step 1: Load commits ---
    print(f"\n1. Loading Git history from {repo_path} (with diff stats)...")
    commits = list(iter_git_log(repo_path, include_stats=True))
    commits.reverse()  # chronological
    print(f"   Loaded {len(commits)} commits")

    # ===================================================================
    # PRIMARY ANALYSIS: Weekly segmentation (maximise N)
    # ===================================================================
    print(f"\n2. Weekly segmentation (min {MIN_BIN_SIZE} commits/week)...")
    weekly_bins = auto_segment_weekly(commits)
    print(f"   {len(weekly_bins)} weeks with >= {MIN_BIN_SIZE} commits")

    weekly_metrics: list[dict] = []
    for label, week_commits in weekly_bins:
        metrics = sprint_quality_proxies(week_commits, label=label)
        weekly_metrics.append(metrics)

    # Print compact table
    print(f"\n   {'Week':<12s} {'N':>4s} {'Q':>6s} {'GI':>6s} {'|bal|':>6s} {'fix%':>6s}")
    print(f"   {'-'*42}")
    for m in weekly_metrics:
        print(
            f"   {m['label']:<12s} {m['n_commits']:>4d} "
            f"{m['quality_score']:>6.1f} {m['gi_ratio']:>6.2f} "
            f"{m['balance_distance']:>6.2f} {m['fix_density']:>6.1%}"
        )

    # Correlation on weekly bins
    print(f"\n3. Correlation analysis (weekly, N={len(weekly_metrics)})...")
    w_balance = np.array([m["balance_distance"] for m in weekly_metrics])
    w_quality = np.array([m["quality_score"] for m in weekly_metrics])
    w_fix = np.array([m["fix_density"] for m in weekly_metrics])

    bs_quality = _spearman_if_enough(w_balance, w_quality, "|balance| vs quality")
    bs_fix = _spearman_if_enough(w_balance, w_fix, "|balance| vs fix_density")

    if bs_quality:
        result.add("weekly_rho_balance_quality", bs_quality["rho"])
        result.add("weekly_p_spearman", bs_quality["p_spearman"])
        result.add("weekly_p_permutation", bs_quality["p_permutation"])
        result.add("weekly_ci_lo", bs_quality["ci_lo"])
        result.add("weekly_ci_hi", bs_quality["ci_hi"])
        result.add("weekly_n", bs_quality["n"])
    if bs_fix:
        result.add("weekly_rho_balance_fixes", bs_fix["rho"])
        result.add("weekly_p_fixes_perm", bs_fix["p_permutation"])

    # Interpret the primary result
    if bs_quality:
        rho_q = bs_quality["rho"]
        p_perm = bs_quality["p_permutation"]
        ci_lo = bs_quality["ci_lo"]
        ci_hi = bs_quality["ci_hi"]

        if p_perm < 0.05 and rho_q < 0:
            weekly_finding = (
                f"Significant: closer to GI balance = higher quality "
                f"(rho={rho_q:+.3f}, p_perm={p_perm:.3f}, CI [{ci_lo:+.3f},{ci_hi:+.3f}])"
            )
        elif p_perm < 0.05 and rho_q > 0:
            weekly_finding = (
                f"Significant but reversed: GI imbalance correlates with HIGHER quality "
                f"(rho={rho_q:+.3f}, p_perm={p_perm:.3f}, CI [{ci_lo:+.3f},{ci_hi:+.3f}])"
            )
        elif ci_lo > 0 or ci_hi < 0:
            weekly_finding = (
                f"CI excludes zero (directional signal): rho={rho_q:+.3f}, "
                f"CI [{ci_lo:+.3f},{ci_hi:+.3f}], p_perm={p_perm:.3f}"
            )
        else:
            weekly_finding = (
                f"No significant correlation: rho={rho_q:+.3f}, "
                f"p_perm={p_perm:.3f}, CI [{ci_lo:+.3f},{ci_hi:+.3f}]"
            )
        print(f"\n   Weekly finding: {weekly_finding}")
    else:
        weekly_finding = "Insufficient weekly bins"

    # ===================================================================
    # SECONDARY ANALYSIS: Named segments (interpretive context)
    # ===================================================================
    print(f"\n4. Named segments (interpretive context)...")
    named_segmented = segment_commits(commits, NAMED_SEGMENTS)
    named_metrics: list[dict] = []
    for label, seg_commits in named_segmented.items():
        if len(seg_commits) < 3:
            print(f"   {label}: skipped ({len(seg_commits)} commits)")
            continue
        metrics = sprint_quality_proxies(seg_commits, label=label)
        named_metrics.append(metrics)
        print(
            f"   {label}: Q={metrics['quality_score']:.1f}/10, "
            f"GI={metrics['gi_ratio']:.2f}, "
            f"|bal|={metrics['balance_distance']:.2f}, "
            f"fix={metrics['fix_density']:.1%}, "
            f"test={metrics['test_density']:.1%}"
        )

    # Named-segment correlation (for comparison with previous run)
    print(f"\n5. Named-segment correlation (N={len(named_metrics)}, for comparison)...")
    if len(named_metrics) >= 4:
        n_balance = np.array([m["balance_distance"] for m in named_metrics])
        n_quality = np.array([m["quality_score"] for m in named_metrics])
        bs_named = _spearman_if_enough(n_balance, n_quality, "|balance| vs quality (named)")
        if bs_named:
            result.add("named_rho_balance_quality", bs_named["rho"])
            result.add("named_p_permutation", bs_named["p_permutation"])
            result.add("named_n", bs_named["n"])

    # Phase comparison
    print(f"\n6. Phase comparison (development vs workload sprints):")
    dev_phases = [m for m in named_metrics if m["label"].startswith("P")]
    wl_sprints = [m for m in named_metrics if m["label"].startswith("WL")]

    if dev_phases and wl_sprints:
        dev_avg_quality = np.mean([m["quality_score"] for m in dev_phases])
        wl_avg_quality = np.mean([m["quality_score"] for m in wl_sprints])
        dev_avg_balance = np.mean([m["balance_distance"] for m in dev_phases])
        wl_avg_balance = np.mean([m["balance_distance"] for m in wl_sprints])

        result.add("dev_avg_quality", round(float(dev_avg_quality), 2))
        result.add("wl_avg_quality", round(float(wl_avg_quality), 2))
        result.add("dev_avg_balance_distance", round(float(dev_avg_balance), 3))
        result.add("wl_avg_balance_distance", round(float(wl_avg_balance), 3))

        print(f"   Development phases: avg Q={dev_avg_quality:.1f}, avg |balance|={dev_avg_balance:.2f}")
        print(f"   Workload sprints:   avg Q={wl_avg_quality:.1f}, avg |balance|={wl_avg_balance:.2f}")

    # Ranked segments
    print(f"\n7. Named segments ranked by quality score:")
    for m in sorted(named_metrics, key=lambda x: -x["quality_score"]):
        print(
            f"   {m['quality_score']:5.1f}/10  {m['label']:<25s}  "
            f"GI={m['gi_ratio']:.2f}  |bal|={m['balance_distance']:.2f}  "
            f"fix={m['fix_density']:.1%}"
        )

    # ===================================================================
    # SUMMARY
    # ===================================================================
    result.status = Status.COMPLETED
    n_weekly = len(weekly_metrics)
    n_named = len(named_metrics)
    result.interpretation = (
        f"Weekly segmentation (N={n_weekly}) — {weekly_finding}. "
        f"Named segments (N={n_named}) for interpretive context. "
        f"Quality proxy: fix density (45%), test density (30%), "
        f"documentation (25%). GI balance excluded to avoid circularity."
    )
    result.caveats = [
        "Quality proxies are commit-derived, not ground-truth quality assessments",
        "Composite score weights are heuristic, not empirically calibrated",
        "Weekly bins vary in commit count (heteroskedasticity risk)",
        "Bootstrap CI assumes exchangeability of weekly observations",
        "Named segment date ranges may overlap slightly",
        "Layer 3 ensemble classifier used (keyword + diff-stat + file-type)",
    ]
    result.metadata = {
        "weekly_metrics": weekly_metrics,
        "named_metrics": named_metrics,
        "weekly_correlation": bs_quality if bs_quality else None,
        "weekly_fix_correlation": bs_fix if bs_fix else None,
    }

    print(f"\n{'='*60}")
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
