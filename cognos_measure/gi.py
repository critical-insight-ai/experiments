"""Generation-Integration (GI) metrics.

Measures the fundamental rhythm of intelligence: the oscillation between
generation (creating distinctions, diverging) and integration (composing
distinctions into coherence).
"""

from __future__ import annotations

from collections import Counter
from enum import Enum
from typing import Any

import numpy as np


class GIPhase(str, Enum):
    """Classification of an event/commit as generation or integration."""
    GENERATION = "G"
    INTEGRATION = "I"
    AMBIGUOUS = "A"


# --- Layer 4 (Temporal/Phase) classification ---
# Classify by dominant phase of the workflow or sprint.

_GENERATION_KEYWORDS = {
    "add", "create", "new", "feature", "implement", "introduce", "initial",
    "prototype", "explore", "experiment", "spike", "draft", "design",
    "generate", "extend", "expand", "scaffold",
}

_INTEGRATION_KEYWORDS = {
    "refactor", "consolidate", "merge", "integrate", "unify", "simplify",
    "doc", "document", "test", "fix", "cleanup", "polish", "normalize",
    "rename", "move", "reorganize", "harmonize", "align", "spec",
    "review", "validate", "verify", "harden",
}


def classify_commit_message(message: str) -> GIPhase:
    """Classify a git commit message as Generation, Integration, or Ambiguous.

    Uses Layer 4 (temporal/phase) heuristic: keyword matching on commit message.
    This is the coarsest classification — good for aggregate GI rhythm analysis.
    """
    words = set(message.lower().split())
    # Also check if any keyword is a prefix of any word (e.g. "refactoring" matches "refactor")
    g_score = sum(1 for w in words for k in _GENERATION_KEYWORDS if w.startswith(k))
    i_score = sum(1 for w in words for k in _INTEGRATION_KEYWORDS if w.startswith(k))

    if g_score > i_score:
        return GIPhase.GENERATION
    elif i_score > g_score:
        return GIPhase.INTEGRATION
    return GIPhase.AMBIGUOUS


def classify_file_changes(files_changed: list[str]) -> GIPhase:
    """Classify a commit by the types of files changed.

    New files = generation. Tests/docs/refactors = integration.
    """
    g = 0
    i = 0
    for f in files_changed:
        fl = f.lower()
        if any(p in fl for p in ["test", "spec", ".md", "doc"]):
            i += 1
        elif any(p in fl for p in [".yaml", ".yml", ".json", "config"]):
            i += 1  # configuration = integration of existing
        else:
            g += 1  # new code = generation

    if g > i:
        return GIPhase.GENERATION
    elif i > g:
        return GIPhase.INTEGRATION
    return GIPhase.AMBIGUOUS


def classify_commit_layer3(
    message: str,
    *,
    files_added: int = 0,
    files_modified: int = 0,
    files_deleted: int = 0,
    files_renamed: int = 0,
    total_insertions: int = 0,
    total_deletions: int = 0,
    file_paths: list[str] | None = None,
) -> GIPhase:
    """Classify a commit using a 3-signal ensemble (Layer 3 + Layer 4).

    Combines:
      1. Layer 4 (keyword heuristic on message)
      2. Layer 3a (structural: file add/delete/rename ratios)
      3. Layer 3b (content flow: insertion vs deletion ratio)
      4. Tiebreaker: file-type heuristic via classify_file_changes()

    Falls back to keyword-only when diff stats are unavailable (all zeros).
    """
    # Signal 1: Layer 4 keyword classification
    keyword_phase = classify_commit_message(message)

    total_files = files_added + files_modified + files_deleted + files_renamed
    has_stats = total_files > 0 or total_insertions > 0 or total_deletions > 0

    if not has_stats:
        # No diff stats — degrade to keyword-only
        return keyword_phase

    # Signal 2: Layer 3a — structural change type ratio
    # New files = generation, deleted/renamed = integration (cleanup/restructure)
    structural_phase = GIPhase.AMBIGUOUS
    if total_files > 0:
        gen_signal = files_added
        int_signal = files_deleted + files_renamed
        if gen_signal > int_signal:
            structural_phase = GIPhase.GENERATION
        elif int_signal > gen_signal:
            structural_phase = GIPhase.INTEGRATION
        # If tied or all modified, stays AMBIGUOUS

    # Signal 3: Layer 3b — content flow (net insertions vs deletions)
    content_phase = GIPhase.AMBIGUOUS
    total_lines = total_insertions + total_deletions
    if total_lines > 0:
        ins_ratio = total_insertions / total_lines
        if ins_ratio > 0.70:
            content_phase = GIPhase.GENERATION  # mostly new content
        elif ins_ratio < 0.30:
            content_phase = GIPhase.INTEGRATION  # mostly removing/refining

    # Majority voting across 3 signals
    votes = [keyword_phase, structural_phase, content_phase]
    g_votes = sum(1 for v in votes if v == GIPhase.GENERATION)
    i_votes = sum(1 for v in votes if v == GIPhase.INTEGRATION)

    if g_votes >= 2:
        return GIPhase.GENERATION
    if i_votes >= 2:
        return GIPhase.INTEGRATION

    # No majority — if exactly one signal is non-AMBIGUOUS, use it
    non_ambiguous = [v for v in votes if v != GIPhase.AMBIGUOUS]
    if len(non_ambiguous) == 1:
        return non_ambiguous[0]

    # No majority — use file-type tiebreaker if file paths available
    if file_paths:
        file_phase = classify_file_changes(file_paths)
        if file_phase != GIPhase.AMBIGUOUS:
            return file_phase

    # If keyword gave a clear answer, prefer it over AMBIGUOUS
    if keyword_phase != GIPhase.AMBIGUOUS:
        return keyword_phase

    return GIPhase.AMBIGUOUS


def gi_ratio(classifications: list[GIPhase]) -> dict[str, Any]:
    """Compute GI ratio and balance from a sequence of classifications.

    Returns:
        Dict with g_count, i_count, a_count, ratio (G/I), balance score.
        Balance score: 0 = perfectly balanced, positive = generation-heavy,
        negative = integration-heavy.
    """
    counts = Counter(classifications)
    g = counts.get(GIPhase.GENERATION, 0)
    i = counts.get(GIPhase.INTEGRATION, 0)
    a = counts.get(GIPhase.AMBIGUOUS, 0)
    total = g + i  # exclude ambiguous from ratio

    ratio = g / i if i > 0 else float("inf") if g > 0 else 1.0
    # Balance: log2(G/I). 0 = balanced, +1 = 2x more G, -1 = 2x more I
    balance = float(np.log2(ratio)) if ratio > 0 and ratio != float("inf") else 0.0

    return {
        "g_count": g,
        "i_count": i,
        "a_count": a,
        "total_classified": total,
        "ratio": round(ratio, 3),
        "balance": round(balance, 3),
        "interpretation": _interpret_balance(balance),
    }


def _interpret_balance(balance: float) -> str:
    if abs(balance) < 0.3:
        return "Balanced GI rhythm (healthy)"
    elif balance > 1.0:
        return "Strongly generation-heavy (risk: divergence without convergence)"
    elif balance > 0.3:
        return "Generation-leaning (expanding phase)"
    elif balance < -1.0:
        return "Strongly integration-heavy (risk: premature convergence)"
    else:
        return "Integration-leaning (consolidation phase)"


def windowed_gi(
    classifications: list[tuple[str, GIPhase]],
    window_size: int = 7,
) -> list[dict[str, Any]]:
    """Compute GI ratio in sliding windows over time.

    Args:
        classifications: List of (date_str, phase) tuples, sorted chronologically.
        window_size: Number of items per window.

    Returns:
        List of per-window GI stats with start/end dates.
    """
    results = []
    for start in range(0, len(classifications) - window_size + 1, window_size):
        window = classifications[start : start + window_size]
        dates = [c[0] for c in window]
        phases = [c[1] for c in window]
        stats = gi_ratio(phases)
        stats["window_start"] = dates[0]
        stats["window_end"] = dates[-1]
        stats["window_size"] = len(window)
        results.append(stats)
    return results


def gi_rhythm_score(windows: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze the GI oscillation rhythm across windows.

    A healthy cognitive system alternates between G-dominant and I-dominant phases.
    Monotonic G or I = pathological.

    Returns:
        Dict with alternation_count, rhythm_score (0-1), dominant_phase.
    """
    if len(windows) < 2:
        return {"alternation_count": 0, "rhythm_score": 0.0, "dominant_phase": "insufficient_data"}

    balances = [w["balance"] for w in windows]
    alternations = sum(
        1 for i in range(1, len(balances)) if balances[i] * balances[i - 1] < 0
    )
    max_alternations = len(balances) - 1
    rhythm_score = alternations / max_alternations if max_alternations > 0 else 0.0

    avg_balance = float(np.mean(balances))
    if avg_balance > 0.3:
        dominant = "generation"
    elif avg_balance < -0.3:
        dominant = "integration"
    else:
        dominant = "balanced"

    return {
        "alternation_count": alternations,
        "max_alternations": max_alternations,
        "rhythm_score": round(rhythm_score, 3),
        "avg_balance": round(avg_balance, 3),
        "dominant_phase": dominant,
        "interpretation": (
            "Strong GI oscillation" if rhythm_score > 0.6
            else "Moderate oscillation" if rhythm_score > 0.3
            else "Weak oscillation (may indicate phase lock)"
        ),
    }


# --- Sprint-level quality proxies ---

_FIX_KEYWORDS = {"fix", "bug", "patch", "hotfix", "workaround", "regression", "broken", "revert"}
_TEST_KEYWORDS = {"test", "spec", "verify", "validate", "assert", "coverage"}
_DOC_KEYWORDS = {"doc", "readme", "guide", "comment", "changelog", "note"}


def sprint_quality_proxies(
    commits: list[dict[str, Any]],
    label: str = "",
) -> dict[str, Any]:
    """Compute quality proxy metrics for a sprint's commits.

    Quality proxies (higher = better unless noted):
    - fix_density: fraction of commits that are fixes (lower = better)
    - test_density: fraction of test-related commits
    - doc_density: fraction of documentation commits
    - gi_balance_distance: |log2(G/I)| — distance from perfect balance (lower = better)

    Args:
        commits: List of commit dicts with 'message' and 'date'.
            May also include diff-stat fields (files_added, files_modified, etc.)
            for Layer 3 classification.
        label: Optional sprint/phase label.
    """
    n = len(commits)
    if n == 0:
        return {"label": label, "n_commits": 0, "quality_score": 0.0}

    fix_count = 0
    test_count = 0
    doc_count = 0
    classifications: list[GIPhase] = []

    for c in commits:
        msg_lower = c["message"].lower()
        words = set(msg_lower.split())

        if any(w.startswith(k) for w in words for k in _FIX_KEYWORDS):
            fix_count += 1
        if any(w.startswith(k) for w in words for k in _TEST_KEYWORDS):
            test_count += 1
        if any(w.startswith(k) for w in words for k in _DOC_KEYWORDS):
            doc_count += 1

        # Use Layer 3 ensemble if diff stats are present, otherwise Layer 4
        if "files_added" in c:
            classifications.append(classify_commit_layer3(
                c["message"],
                files_added=c.get("files_added", 0),
                files_modified=c.get("files_modified", 0),
                files_deleted=c.get("files_deleted", 0),
                files_renamed=c.get("files_renamed", 0),
                total_insertions=c.get("total_insertions", 0),
                total_deletions=c.get("total_deletions", 0),
                file_paths=c.get("file_paths"),
            ))
        else:
            classifications.append(classify_commit_message(c["message"]))

    gi = gi_ratio(classifications)
    balance_distance = abs(gi["balance"])

    # Composite quality score (0-10 scale):
    # Low fix density (+), high test density (+), low GI imbalance (+)
    fix_density = fix_count / n
    test_density = test_count / n
    doc_density = doc_count / n

    # Score components (each 0-1, weighted):
    fix_score = max(0, 1 - fix_density * 5)       # 0 fixes = 1.0, 20%+ fixes = 0
    test_score = min(1, test_density * 3)           # 33%+ tests = 1.0
    balance_score = max(0, 1 - balance_distance)    # kept as metadata, NOT in quality_score
    maturity_score = min(1, doc_density * 5)        # 20%+ docs = 1.0

    # NOTE: balance_score deliberately excluded from composite to avoid
    # circularity when correlating GI balance with quality (EX-6.2).
    quality_score = round(
        (fix_score * 0.45 + test_score * 0.30 + maturity_score * 0.25) * 10,
        2,
    )

    return {
        "label": label,
        "n_commits": n,
        "fix_count": fix_count,
        "fix_density": round(fix_density, 4),
        "test_count": test_count,
        "test_density": round(test_density, 4),
        "doc_count": doc_count,
        "doc_density": round(doc_density, 4),
        "gi_ratio": gi["ratio"],
        "gi_balance": gi["balance"],
        "balance_distance": round(balance_distance, 3),
        "quality_score": quality_score,
        "quality_components": {
            "fix_score": round(fix_score, 3),
            "test_score": round(test_score, 3),
            "balance_score": round(balance_score, 3),
            "maturity_score": round(maturity_score, 3),
        },
    }
