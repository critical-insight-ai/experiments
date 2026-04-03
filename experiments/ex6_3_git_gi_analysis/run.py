"""EX-6.3: Git History GI Analysis — run the full experiment.

Classifies CognOS git commits as Generation or Integration,
computes windowed GI ratios, and analyzes the oscillation rhythm.

Usage:
    python -m experiments.ex6_3_git_gi_analysis.run --repo C:\\Source\\CriticalInsight\\Cognos
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cognos_measure.gi import (
    classify_commit_message,
    classify_commit_layer3,
    gi_ratio,
    gi_rhythm_score,
    windowed_gi,
    GIPhase,
)
from cognos_measure.io import iter_git_log
from cognos_measure.temporal import commit_velocity
from cognos_measure.schemas import ExperimentResult, EvidenceLevel, Status


# Known development phases for interpretation
PHASES = [
    ("P1: Hardening", "2025-12-03", "2025-12-31"),
    ("P2: Surface polish", "2026-01-01", "2026-01-31"),
    ("P3: Release prep", "2026-02-01", "2026-02-14"),
    ("P4: Workload sprints", "2026-02-15", "2026-04-01"),
]


def run(repo_path: Path, since: str = "", until: str = "") -> ExperimentResult:
    """Run the full EX-6.3 experiment."""
    result = ExperimentResult(
        experiment_id="EX-6.3",
        hypothesis="H-5: Cognitive flywheel is a GI circuit; rhythm is measurable in Git history",
        status=Status.RUNNING,
        evidence_level=EvidenceLevel.OBSERVATIONAL,
    )

    print("EX-6.3: Git History GI Analysis")
    print("=" * 50)

    # --- Step 1: Load commits ---
    print(f"\n1. Loading Git history from {repo_path} (with diff stats)...")
    commits = list(iter_git_log(repo_path, since=since, until=until, include_stats=True))
    commits.reverse()  # chronological order (oldest first)
    print(f"   Loaded {len(commits)} commits")

    if not commits:
        result.status = Status.FAILED
        result.interpretation = "No commits found in the specified range."
        return result

    # --- Step 2: Classify each commit (Layer 3 + Layer 4 ensemble) ---
    print("\n2. Classifying commits (Layer 3 diff-stat + Layer 4 keyword ensemble)...")
    classifications: list[tuple[str, GIPhase]] = []
    l4_classifications: list[GIPhase] = []  # keyword-only for comparison
    for c in commits:
        phase = classify_commit_layer3(
            c["message"],
            files_added=c.get("files_added", 0),
            files_modified=c.get("files_modified", 0),
            files_deleted=c.get("files_deleted", 0),
            files_renamed=c.get("files_renamed", 0),
            total_insertions=c.get("total_insertions", 0),
            total_deletions=c.get("total_deletions", 0),
            file_paths=c.get("file_paths"),
        )
        classifications.append((c["date"], phase))
        l4_classifications.append(classify_commit_message(c["message"]))

    phases_only = [p for _, p in classifications]
    overall = gi_ratio(phases_only)

    result.add("total_commits", len(commits))
    result.add("g_count", overall["g_count"])
    result.add("i_count", overall["i_count"])
    result.add("a_count", overall["a_count"])
    result.add("overall_gi_ratio", overall["ratio"])
    result.add("overall_balance", overall["balance"])

    print(f"   Generation: {overall['g_count']} ({overall['g_count']/len(commits)*100:.0f}%)")
    print(f"   Integration: {overall['i_count']} ({overall['i_count']/len(commits)*100:.0f}%)")
    print(f"   Ambiguous: {overall['a_count']} ({overall['a_count']/len(commits)*100:.0f}%)")
    print(f"   GI Ratio: {overall['ratio']:.2f} — {overall['interpretation']}")

    # Layer 4 (keyword-only) comparison
    l4_ratio = gi_ratio(l4_classifications)
    l4_ambig_pct = l4_ratio["a_count"] / len(commits) * 100 if commits else 0
    l3_ambig_pct = overall["a_count"] / len(commits) * 100 if commits else 0

    result.add("l4_ambiguity_pct", round(l4_ambig_pct, 1))
    result.add("l3_ambiguity_pct", round(l3_ambig_pct, 1))

    print(f"\n   Classifier comparison:")
    print(f"   Layer 4 (keyword-only) ambiguity: {l4_ratio['a_count']} ({l4_ambig_pct:.1f}%)")
    print(f"   Layer 3 (ensemble)     ambiguity: {overall['a_count']} ({l3_ambig_pct:.1f}%)")
    print(f"   Ambiguity reduction: {l4_ambig_pct - l3_ambig_pct:.1f} percentage points")

    # --- Step 3: Weekly windowed analysis ---
    print("\n3. Weekly GI rhythm (7-day windows)...")
    windows = windowed_gi(classifications, window_size=7)
    for w in windows[:5]:
        print(f"   {w['window_start'][:10]} to {w['window_end'][:10]}: "
              f"R={w['ratio']:.2f} ({w['interpretation']})")
    if len(windows) > 5:
        print(f"   ... ({len(windows)} total windows)")

    # --- Step 4: Rhythm analysis ---
    print("\n4. GI rhythm oscillation analysis...")
    rhythm = gi_rhythm_score(windows)
    result.add("rhythm_score", rhythm["rhythm_score"])
    result.add("alternation_count", rhythm["alternation_count"])
    result.add("dominant_phase", rhythm["dominant_phase"])

    print(f"   Alternations: {rhythm['alternation_count']}/{rhythm['max_alternations']}")
    print(f"   Rhythm score: {rhythm['rhythm_score']:.2f} — {rhythm['interpretation']}")
    print(f"   Dominant phase: {rhythm['dominant_phase']}")

    # --- Step 5: Phase-by-phase analysis ---
    print("\n5. Known development phases:")
    phase_results = []
    for phase_name, start, end in PHASES:
        phase_commits = [
            (d, p) for d, p in classifications
            if start <= d[:10] <= end
        ]
        if phase_commits:
            phase_gi = gi_ratio([p for _, p in phase_commits])
            phase_results.append({
                "phase": phase_name,
                "commits": len(phase_commits),
                "gi_ratio": phase_gi["ratio"],
                "balance": phase_gi["balance"],
                "interpretation": phase_gi["interpretation"],
            })
            print(f"   {phase_name}: {len(phase_commits)} commits, "
                  f"R={phase_gi['ratio']:.2f} ({phase_gi['interpretation']})")

    # --- Step 6: Velocity analysis ---
    print("\n6. Commit velocity:")
    velocity = commit_velocity(commits, period="daily")
    result.add("mean_daily_commits", velocity["mean"])
    result.add("active_days_pct", velocity["active_pct"])
    print(f"   Mean: {velocity['mean']:.1f} commits/day")
    print(f"   Active days: {velocity['active_pct']}%")
    print(f"   Range: {velocity['date_range']}")

    # --- Summarize ---
    result.status = Status.COMPLETED
    result.interpretation = (
        f"Analyzed {len(commits)} commits. Overall GI ratio: {overall['ratio']:.2f} "
        f"({overall['interpretation']}). Rhythm score: {rhythm['rhythm_score']:.2f} "
        f"({rhythm['interpretation']}). The flywheel exhibits "
        f"{'healthy GI oscillation' if rhythm['rhythm_score'] > 0.3 else 'potential phase lock'}."
    )
    result.caveats = [
        "Layer 3 ensemble (keyword + diff-stat + file-type) reduces but does not eliminate ambiguity",
        "Commits vary in size — a 1-file commit and a 50-file commit count equally",
        "Ambiguous commits excluded from ratio; may hide important signals",
    ]
    result.metadata = {
        "overall": overall,
        "rhythm": rhythm,
        "velocity": velocity,
        "phases": phase_results,
        "windows_sample": windows[:20],
    }

    print("\n" + "=" * 50)
    print(f"Result: {result.interpretation}")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="EX-6.3: Git History GI Analysis")
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(r"C:\Source\CriticalInsight\Cognos"),
        help="Path to CognOS Git repository",
    )
    parser.add_argument("--since", default="", help="Start date (e.g. 2025-12-01)")
    parser.add_argument("--until", default="", help="End date (e.g. 2026-04-01)")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "results" / "ex6_3_results.json",
        help="Output path for results JSON",
    )
    args = parser.parse_args()

    result = run(args.repo, since=args.since, until=args.until)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result.summary(), indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\nResults written to {args.output}")


if __name__ == "__main__":
    main()
