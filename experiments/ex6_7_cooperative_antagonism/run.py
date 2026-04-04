"""EX-6.7: Cooperative Antagonism — multi-agent GI dynamics.

Tests H-4: structured adversarial agent interaction (generator/critic/judge)
produces higher-quality outputs with measurable improvement across rounds.

Usage:
    # Parse existing run outputs:
    python -m experiments.ex6_7_cooperative_antagonism.run \
        --parse-only \
        --output-dir C:\\Source\\CriticalInsight\\CognOS-Workloads-Outputs\\ex-6-7-cooperative-antagonism\\20260403-run1

    # Full automated run (requires CognOS cluster):
    python -m experiments.ex6_7_cooperative_antagonism.run \
        --server http://localhost:8080 \
        --tenant acme \
        --bundle C:\\Source\\CriticalInsight\\Cognos\\docs\\demos\\acme-briefing\\ex-6-7-cooperative-antagonism-bundle.yaml
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from cognos_measure.schemas import ExperimentResult, EvidenceLevel, Status


# Run 1 baseline for comparison
RUN1_BASELINE = {
    "date": "2026-04-03",
    "topic": "Semiconductor supply chain concentration in East Asia",
    "quality_trajectory": [6.7, 7.9, 8.2],
    "breadth_trajectory": [63, 96, 126],
    "tool_calls": 0,
    "mode_collapse": False,
    "rounds": 3,
    "tasks_completed": 7,
    "tasks_failed": 0,
}


def parse_run_outputs(output_dir: Path) -> dict[str, Any]:
    """Parse run outputs from a completed EX-6.7 run directory.

    Expects: judge-verdict.md and run-summary.md in the directory.
    """
    metrics: dict[str, Any] = {}

    # Parse run-summary.md
    summary_path = output_dir / "run-summary.md"
    if summary_path.exists():
        text = summary_path.read_text(encoding="utf-8")
        metrics.update(_parse_run_summary(text))

    # Parse judge-verdict.md
    verdict_path = output_dir / "judge-verdict.md"
    if verdict_path.exists():
        text = verdict_path.read_text(encoding="utf-8")
        metrics.update(_parse_judge_verdict(text))

    return metrics


def _parse_run_summary(text: str) -> dict[str, Any]:
    """Extract metrics from run-summary.md."""
    metrics: dict[str, Any] = {}

    # Run ID
    m = re.search(r"\*\*Run ID\*\*:\s*`([^`]+)`", text)
    if m:
        metrics["run_id"] = m.group(1)

    # Duration
    m = re.search(r"\*\*Duration\*\*:\s*(.+?)$", text, re.MULTILINE)
    if m:
        metrics["duration"] = m.group(1).strip()

    # Total Tokens
    m = re.search(r"\*\*Total Tokens\*\*:\s*([\d,]+)", text)
    if m:
        metrics["total_tokens"] = int(m.group(1).replace(",", ""))

    # Tasks completed/failed
    m = re.search(r"\*\*Tasks\*\*:\s*(\d+)/(\d+)\s*completed,\s*(\d+)\s*failed", text)
    if m:
        metrics["tasks_completed"] = int(m.group(1))
        metrics["tasks_total"] = int(m.group(2))
        metrics["tasks_failed"] = int(m.group(3))

    # Tool calls (search for "0 tool calls" or similar)
    m = re.search(r"(\d+)\s*tool\s*call", text, re.IGNORECASE)
    if m:
        metrics["tool_calls"] = int(m.group(1))

    # Quality trajectory from "Quality increased ... X -> Y -> Z"
    m = re.search(r"([\d.]+)\s*->\s*([\d.]+)\s*->\s*([\d.]+)\s*\(overall", text)
    if m:
        metrics["quality_trajectory"] = [float(m.group(1)), float(m.group(2)), float(m.group(3))]

    # Breadth trajectory
    m = re.search(r"Breadth Score grew.*?:\s*([\d]+)\s*->\s*([\d]+)\s*->\s*([\d]+)", text)
    if m:
        metrics["breadth_trajectory"] = [int(m.group(1)), int(m.group(2)), int(m.group(3))]

    # Mode collapse
    metrics["mode_collapse"] = "mode collapse: yes" in text.lower() or "collapse detected" in text.lower()
    if "no mode collapse" in text.lower() or "no collapse" in text.lower():
        metrics["mode_collapse"] = False

    return metrics


def _parse_judge_verdict(text: str) -> dict[str, Any]:
    """Extract per-dimension scores from judge-verdict.md."""
    metrics: dict[str, Any] = {}

    # Overall score
    m = re.search(r"\*\*OVERALL SCORE:\s*([\d.]+)\*\*", text)
    if m:
        metrics["overall_score"] = float(m.group(1))

    # Per-dimension scores from the quality table
    dimensions = {}
    for match in re.finditer(
        r"\*\*(\w[\w\s]*?)\*\*\s*\|\s*(\d+)\s*\|", text
    ):
        dim = match.group(1).strip().lower()
        score = int(match.group(2))
        dimensions[dim] = score

    if dimensions:
        metrics["dimension_scores"] = dimensions

    # Round-by-round table
    round_rows = re.findall(
        r"\|\s*(\d)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
        text,
    )
    if round_rows:
        rounds = []
        for row in round_rows:
            rounds.append({
                "round": int(row[0]),
                "accuracy": int(row[1]),
                "completeness": int(row[2]),
                "coherence": int(row[3]),
                "depth": int(row[4]),
                "falsifiability": int(row[5]),
                "source_diversity": int(row[6]),
                "breadth": int(row[7]),
            })
        metrics["round_details"] = rounds

    return metrics


def compare_runs(run1: dict[str, Any], run2: dict[str, Any]) -> None:
    """Print a comparison table between two runs."""
    print("\n" + "=" * 60)
    print("COMPARISON: Run 1 vs Run 2")
    print("=" * 60)

    def _get(d: dict, key: str, default: Any = "N/A") -> Any:
        return d.get(key, default)

    q1 = _get(run1, "quality_trajectory", [])
    q2 = _get(run2, "quality_trajectory", [])
    b1 = _get(run1, "breadth_trajectory", [])
    b2 = _get(run2, "breadth_trajectory", [])

    print(f"\n{'Metric':<30s} {'Run 1':>12s} {'Run 2':>12s} {'Delta':>10s}")
    print("-" * 64)

    # Quality final
    q1_final = q1[-1] if q1 else 0
    q2_final = q2[-1] if q2 else 0
    delta = q2_final - q1_final
    print(f"{'Quality (final)':<30s} {q1_final:>12.1f} {q2_final:>12.1f} {delta:>+10.1f}")

    # Quality R1
    if q1 and q2:
        print(f"{'Quality (R1)':<30s} {q1[0]:>12.1f} {q2[0]:>12.1f} {q2[0]-q1[0]:>+10.1f}")

    # Breadth final
    b1_final = b1[-1] if b1 else 0
    b2_final = b2[-1] if b2 else 0
    print(f"{'Breadth (final)':<30s} {b1_final:>12d} {b2_final:>12d} {b2_final-b1_final:>+10d}")

    # Tool calls
    t1 = _get(run1, "tool_calls", 0)
    t2 = _get(run2, "tool_calls", 0)
    print(f"{'Tool calls':<30s} {t1:>12d} {t2:>12d} {t2-t1:>+10d}")

    # Mode collapse
    mc1 = "Yes" if _get(run1, "mode_collapse", False) else "No"
    mc2 = "Yes" if _get(run2, "mode_collapse", False) else "No"
    print(f"{'Mode collapse':<30s} {mc1:>12s} {mc2:>12s}")

    # Convergence speed (rounds to reach quality ≥ 8.0)
    def _rounds_to_threshold(trajectory: list[float], threshold: float = 8.0) -> str:
        for i, v in enumerate(trajectory, 1):
            if v >= threshold:
                return str(i)
        return "N/A"

    r1 = _rounds_to_threshold(q1)
    r2 = _rounds_to_threshold(q2)
    print(f"{'Rounds to Q>=8.0':<30s} {r1:>12s} {r2:>12s}")


def validate_bundle(bundle_path: Path) -> list[str]:
    """Pre-flight checks on the CRD bundle before submission.

    Returns a list of warning/error messages. Empty list = all checks pass.
    """
    issues: list[str] = []
    try:
        with open(bundle_path, encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
    except Exception as exc:
        return [f"Cannot parse bundle YAML: {exc}"]

    # Collect all CRD kinds
    kinds = [d.get("kind", "?") for d in docs if d]

    # Check 1: AgentType uses defaultTools (not tools)
    for doc in docs:
        if not doc or doc.get("kind") != "AgentType":
            continue
        spec = doc.get("spec", {})
        agent_id = doc.get("metadata", {}).get("id", "?")
        if "tools" in spec and "defaultTools" not in spec:
            issues.append(
                f"AgentType '{agent_id}' uses 'tools:' instead of 'defaultTools:'. "
                f"Tools will not be registered. Use 'defaultTools:' with '- toolId: ...' entries."
            )
        dt = spec.get("defaultTools", [])
        if dt:
            for entry in dt:
                if isinstance(entry, str):
                    issues.append(
                        f"AgentType '{agent_id}' has bare string in defaultTools: '{entry}'. "
                        f"Use '- toolId: {entry}' format."
                    )
            # Check for generic web.search/web.browse (should be specific IDs)
            tool_ids = [
                (e.get("toolId") if isinstance(e, dict) else e) for e in dt
            ]
            for tid in tool_ids:
                if tid == "web.search":
                    issues.append(
                        f"AgentType '{agent_id}': 'web.search' is not a registered tool. "
                        f"Use 'web.search.qa' and/or 'web.search.raw'."
                    )
                if tid == "web.browse":
                    issues.append(
                        f"AgentType '{agent_id}': 'web.browse' is not a registered tool. "
                        f"Use 'web.browse.scroll' and/or 'web.browse.links'."
                    )

    # Check 2: SemanticMemoryProfile present (needed for memory.search)
    if "SemanticMemoryProfile" not in kinds:
        issues.append("No SemanticMemoryProfile in bundle — memory.search tools will fail.")

    # Check 3: At least one workflow
    if "Workflow" not in kinds:
        issues.append("No Workflow CRD in bundle.")

    return issues


def run_workflow(
    server: str,
    tenant: str,
    bundle_path: Path,
    token: str,
    output_base: Path,
) -> Path | None:
    """Execute EX-6.7 workflow via CognOS CLI and download outputs.

    Returns the output directory path, or None on failure.
    """
    print(f"\n1. Applying CRD bundle: {bundle_path}")
    apply_cmd = [
        "cognos", "crds", "apply",
        "--file", str(bundle_path),
        "--server", server,
        "--token", token,
        "--tenant", tenant,
    ]
    result = subprocess.run(apply_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"   ERROR: CRD apply failed: {result.stderr}")
        return None
    print("   CRDs applied successfully")

    print("\n2. Starting workflow...")
    workflow_id = f"workflow/{tenant}/ex-6-7-cooperative-antagonism/1.0.0"
    start_cmd = [
        "cognos", "workflows", "start", workflow_id,
        "--server", server,
        "--token", token,
        "--tenant", tenant,
        "--output", "json",
    ]
    result = subprocess.run(start_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"   ERROR: Workflow start failed: {result.stderr}")
        return None

    try:
        start_output = json.loads(result.stdout)
        run_id = start_output.get("runId", "")
    except (json.JSONDecodeError, KeyError):
        # Try to extract run ID from text output
        m = re.search(r"(run/workflow/[^\s]+)", result.stdout)
        run_id = m.group(1) if m else ""

    if not run_id:
        print(f"   ERROR: Could not extract run ID from: {result.stdout[:200]}")
        return None

    print(f"   Started: {run_id}")

    # Poll for completion
    print("\n3. Waiting for workflow completion...")
    max_wait = 600  # 10 minutes
    poll_interval = 15
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval

        status_cmd = [
            "cognos", "workflows", "runs", "get", run_id,
            "--server", server,
            "--token", token,
            "--tenant", tenant,
            "--output", "json",
        ]
        status_result = subprocess.run(status_cmd, capture_output=True, text=True)
        if status_result.returncode == 0:
            try:
                status_data = json.loads(status_result.stdout)
                state = status_data.get("state", "").lower()
                if state in ("completed", "succeeded"):
                    print(f"   Completed after {elapsed}s")
                    break
                elif state in ("failed", "cancelled"):
                    print(f"   Workflow {state} after {elapsed}s")
                    return None
                print(f"   [{elapsed}s] State: {state}")
            except json.JSONDecodeError:
                print(f"   [{elapsed}s] Polling...")
    else:
        print(f"   TIMEOUT after {max_wait}s")
        return None

    # Download outputs
    timestamp = time.strftime("%Y%m%d")
    output_dir = output_base / f"{timestamp}-run2"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n4. Downloading outputs to {output_dir}...")
    outputs_cmd = [
        "cognos", "workflows", "runs", "outputs", run_id,
        "--server", server,
        "--token", token,
        "--tenant", tenant,
        "--output-dir", str(output_dir),
    ]
    result = subprocess.run(outputs_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"   WARNING: Output download may have failed: {result.stderr}")
    else:
        print(f"   Outputs saved to {output_dir}")

    return output_dir


def run(
    parse_only: bool = False,
    output_dir: Path | None = None,
    server: str = "",
    tenant: str = "",
    bundle_path: Path | None = None,
    token: str = "",
) -> ExperimentResult:
    """Run or parse EX-6.7 experiment."""
    result = ExperimentResult(
        experiment_id="EX-6.7",
        hypothesis="H-4: Cooperative antagonism (G/I agent pairs) produces higher-quality outputs",
        status=Status.RUNNING,
        evidence_level=EvidenceLevel.OBSERVATIONAL,
    )

    print("EX-6.7: Cooperative Antagonism — Multi-Agent GI Dynamics")
    print("=" * 60)

    output_base = Path(
        r"C:\Source\CriticalInsight\CognOS-Workloads-Outputs\ex-6-7-cooperative-antagonism"
    )

    if not parse_only:
        if not all([server, tenant, bundle_path, token]):
            print("ERROR: --server, --tenant, --bundle, and --token required for live run")
            result.status = Status.FAILED
            result.interpretation = "Missing CLI arguments for live workflow execution"
            return result

        # Pre-flight validation
        print(f"\nPre-flight: validating bundle {bundle_path}...")
        issues = validate_bundle(bundle_path)
        if issues:
            for issue in issues:
                print(f"   WARNING: {issue}")
            print(f"   {len(issues)} issue(s) found — run may not produce tool calls")
        else:
            print("   All pre-flight checks passed")

        output_dir = run_workflow(server, tenant, bundle_path, token, output_base)
        if output_dir is None:
            result.status = Status.FAILED
            result.interpretation = "Workflow execution failed"
            return result

    if output_dir is None:
        print("ERROR: --output-dir required for --parse-only mode")
        result.status = Status.FAILED
        return result

    # Parse run outputs
    print(f"\nParsing outputs from: {output_dir}")
    run_metrics = parse_run_outputs(output_dir)

    if not run_metrics:
        print("WARNING: No metrics could be extracted from outputs")
        result.status = Status.FAILED
        result.interpretation = "Could not parse run outputs"
        return result

    # Display parsed metrics
    print(f"\n--- Parsed Metrics ---")
    q = run_metrics.get("quality_trajectory", [])
    b = run_metrics.get("breadth_trajectory", [])
    print(f"Quality trajectory: {' -> '.join(str(v) for v in q) if q else 'N/A'}")
    print(f"Breadth trajectory: {' -> '.join(str(v) for v in b) if b else 'N/A'}")
    print(f"Overall score: {run_metrics.get('overall_score', 'N/A')}")
    print(f"Tool calls: {run_metrics.get('tool_calls', 'N/A')}")
    print(f"Mode collapse: {run_metrics.get('mode_collapse', 'N/A')}")
    print(f"Tasks: {run_metrics.get('tasks_completed', '?')}/{run_metrics.get('tasks_total', '?')}")

    # Store scalar metrics in result (complex types as JSON strings)
    for key, value in run_metrics.items():
        if isinstance(value, (int, float, str)):
            result.add(key, value)
        elif isinstance(value, bool):
            result.add(key, str(value))
        elif isinstance(value, (list, dict)):
            result.add(key, json.dumps(value))

    # Compare with Run 1 baseline
    compare_runs(RUN1_BASELINE, run_metrics)

    # Summarize
    result.status = Status.COMPLETED
    final_q = q[-1] if q else 0
    tool_calls = run_metrics.get("tool_calls", 0)
    collapse = run_metrics.get("mode_collapse", False)

    result.interpretation = (
        f"Quality: {' -> '.join(str(v) for v in q)}. "
        f"Tool calls: {tool_calls}. Mode collapse: {'yes' if collapse else 'no'}. "
        f"vs Run 1 baseline: quality delta {final_q - RUN1_BASELINE['quality_trajectory'][-1]:+.1f}, "
        f"tool delta {tool_calls - RUN1_BASELINE['tool_calls']:+d}."
    )
    result.caveats = [
        "Single run — no statistical power for cross-run comparison",
        "Different model versions across runs may confound",
        "Quality scores are model-self-assessed (judge agent), not ground truth",
    ]
    result.metadata = {
        "run_metrics": run_metrics,
        "run1_baseline": RUN1_BASELINE,
    }

    print(f"\n{'='*60}")
    print(f"Result: {result.interpretation}")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="EX-6.7: Cooperative Antagonism")
    parser.add_argument("--parse-only", action="store_true", help="Parse existing outputs only")
    parser.add_argument("--output-dir", type=Path, help="Directory with run outputs to parse")
    parser.add_argument("--server", default="http://localhost:8080", help="CognOS server URL")
    parser.add_argument("--tenant", default="acme", help="Tenant ID")
    parser.add_argument("--bundle", type=Path, dest="bundle_path", help="Path to CRD bundle YAML")
    parser.add_argument("--token", default="", help="Auth token")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "results" / "ex6_7_results.json",
        help="Output path for results JSON",
    )
    args = parser.parse_args()

    exp_result = run(
        parse_only=args.parse_only,
        output_dir=args.output_dir,
        server=args.server,
        tenant=args.tenant,
        bundle_path=args.bundle_path,
        token=args.token,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(exp_result.summary(), indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
