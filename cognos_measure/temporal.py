"""Temporal metrics — velocity analysis, integration window, coherence scoring."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any

import numpy as np


def commit_velocity(
    commits: list[dict[str, str]],
    period: str = "daily",
) -> dict[str, Any]:
    """Compute commit velocity over time.

    Args:
        commits: List of commit dicts with 'date' (ISO format) and 'hash'.
        period: 'daily' or 'weekly'.

    Returns:
        Dict with per-period counts, mean, std, active_days, etc.
    """
    dates = []
    for c in commits:
        dt = datetime.fromisoformat(c["date"].replace("Z", "+00:00"))
        dates.append(dt.date())

    date_counts = Counter(dates)

    if not date_counts:
        return {"mean": 0, "std": 0, "total_commits": 0, "active_days": 0}

    min_date = min(date_counts.keys())
    max_date = max(date_counts.keys())
    total_days = (max_date - min_date).days + 1

    if period == "weekly":
        # Group by ISO week
        week_counts: Counter[str] = Counter()
        for d, count in date_counts.items():
            week_key = f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"
            week_counts[week_key] += count
        values = list(week_counts.values())
        n_periods = len(week_counts)
    else:
        # Fill in zero-commit days
        values = []
        current = min_date
        while current <= max_date:
            values.append(date_counts.get(current, 0))
            current += timedelta(days=1)
        n_periods = total_days

    arr = np.array(values, dtype=float)
    active_days = sum(1 for v in values if v > 0)

    return {
        "period": period,
        "total_commits": sum(values),
        "n_periods": n_periods,
        "active_days": active_days,
        "active_pct": round(active_days / n_periods * 100, 1) if n_periods > 0 else 0,
        "mean": round(float(np.mean(arr)), 2),
        "median": round(float(np.median(arr)), 2),
        "std": round(float(np.std(arr)), 2),
        "max": int(np.max(arr)),
        "min": int(np.min(arr)),
        "date_range": f"{min_date} to {max_date}",
    }


def sprint_analysis(
    sprints: list[dict[str, Any]],
) -> dict[str, Any]:
    """Analyze workload sprint characteristics.

    Each sprint dict should have: name, start_date, end_date, commits, kinds_used.

    Returns:
        Dict with per-sprint metrics, compounding analysis, duration trend.
    """
    analyzed = []
    cumulative_kinds: set[str] = set()

    for s in sprints:
        start = datetime.fromisoformat(s["start_date"]) if isinstance(s["start_date"], str) else s["start_date"]
        end = datetime.fromisoformat(s["end_date"]) if isinstance(s["end_date"], str) else s["end_date"]
        duration = (end - start).days + 1
        kinds = set(s.get("kinds_used", []))
        new_kinds = kinds - cumulative_kinds
        inherited = kinds & cumulative_kinds
        cumulative_kinds |= kinds

        analyzed.append({
            "name": s["name"],
            "duration_days": duration,
            "commits": s.get("commits", 0),
            "commits_per_day": round(s.get("commits", 0) / duration, 1) if duration > 0 else 0,
            "kinds_used": len(kinds),
            "new_kinds": len(new_kinds),
            "inherited_kinds": len(inherited),
            "inheritance_pct": round(len(inherited) / len(kinds) * 100, 1) if kinds else 0,
        })

    durations = [a["duration_days"] for a in analyzed]
    duration_trend = "expanding" if len(durations) >= 3 and durations[-1] > durations[0] else "stable"

    return {
        "sprints": analyzed,
        "total_sprints": len(analyzed),
        "avg_duration": round(float(np.mean(durations)), 1) if durations else 0,
        "duration_trend": duration_trend,
        "total_cumulative_kinds": len(cumulative_kinds),
    }


def integration_window_score(
    sprint_duration_days: int,
    total_crd_kinds: int,
    avg_fields_per_kind: float = 8.0,
    context_window_tokens: int = 128_000,
    yaml_tokens_per_line: float = 3.5,
    yaml_lines_per_kind: float = 50.0,
) -> dict[str, Any]:
    """Score whether a workload fits within the integration window.

    The integration window hypothesis: systems built within a temporal window
    where all decisions are live in working memory are qualitatively more coherent.

    Proxy: does the full workload spec fit in one LLM context window?
    """
    estimated_yaml_lines = total_crd_kinds * yaml_lines_per_kind
    estimated_tokens = estimated_yaml_lines * yaml_tokens_per_line
    fits_context = estimated_tokens <= context_window_tokens
    utilization = estimated_tokens / context_window_tokens

    return {
        "sprint_duration_days": sprint_duration_days,
        "crd_kinds": total_crd_kinds,
        "estimated_yaml_lines": int(estimated_yaml_lines),
        "estimated_tokens": int(estimated_tokens),
        "context_window_tokens": context_window_tokens,
        "fits_in_context": fits_context,
        "context_utilization_pct": round(utilization * 100, 1),
        "interpretation": (
            "Within integration window"
            if fits_context and sprint_duration_days <= 14
            else "Borderline integration window"
            if fits_context
            else "Exceeds integration window"
        ),
    }
