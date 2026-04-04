"""EX-6.8: Cycle Design Variations — CognOS CLI + parse runner.

Tests H-4.1: how cycle design characteristics affect convergence dynamics,
quality ceilings, and efficiency in multi-agent adversarial refinement.

Two modes:
1. CognOS CLI mode: applies YAML bundles, runs workflows, parses outputs
2. Parse-only mode: extracts metrics from previously downloaded outputs

For the OpenAI-only runner (no CognOS required), see openai_runner.py.

Usage:
    # Parse existing run outputs:
    python -m experiments.ex6_8_cycle_design.run \
        --parse-only \
        --output-dir C:\\Source\\CriticalInsight\\CognOS-Workloads-Outputs\\ex-6-8\\6.8.4-run1 \
        --experiment 6.8.4

    # Full automated run via CognOS CLI:
    python -m experiments.ex6_8_cycle_design.run \
        --experiment 6.8.4 \
        --server http://localhost:8080 \
        --tenant acme \
        --token <keycloak-token>

    # Run all Phase 1 experiments:
    python -m experiments.ex6_8_cycle_design.run \
        --all \
        --server http://localhost:8080 \
        --tenant acme \
        --token <keycloak-token>
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

from cognos_measure.schemas import ExperimentResult, EvidenceLevel, Status

from .protocols import ALL_PROTOCOLS, get_protocol


# Bundle file mapping: experiment ID -> YAML bundle path (relative to CognOS repo)
BUNDLE_MAP = {
    "6.8.1": "docs/demos/acme-briefing/ex-6-8-1-compressed-context-bundle.yaml",
    "6.8.4": "docs/demos/acme-briefing/ex-6-8-4-phased-roles-bundle.yaml",
    "6.8.5": "docs/demos/acme-briefing/ex-6-8-5-multi-critic-bundle.yaml",
    "6.8.10": "docs/demos/acme-briefing/ex-6-8-10-selective-attention-bundle.yaml",
}

# Workflow ID mapping
WORKFLOW_MAP = {
    "6.8.1": "workflow/acme/ex-6-8-1-compressed-context/1.0.0",
    "6.8.4": "workflow/acme/ex-6-8-4-phased-roles/1.0.0",
    "6.8.5": "workflow/acme/ex-6-8-5-multi-critic-panel/1.0.0",
    "6.8.10": "workflow/acme/ex-6-8-10-selective-attention/1.0.0",
}

# EX-6.7b Run 6 baseline (5-round sweet spot)
BASELINE_RUN6 = {
    "date": "2026-07-02",
    "quality_trajectory": [7.65, 8.12, 8.58, 8.94, 9.23, 9.25, 9.28],
    "breadth_trajectory": [63, 145, 230, 300, 350, 355, 358],
    "quality_at_round_5": 9.23,
    "breadth_at_round_5": 350,
    "total_tokens": 1_112_667,
    "duration_seconds": 511,
    "tasks_completed": 15,
    "rounds": 7,
}


def validate_bundle(bundle_path: Path) -> list[str]:
    """Check a YAML bundle for common defects. Returns list of warnings."""
    import yaml

    warnings: list[str] = []
    text = bundle_path.read_text(encoding="utf-8")
    docs = list(yaml.safe_load_all(text))

    has_workflow = False
    has_process = False

    for doc in docs:
        if not doc or not isinstance(doc, dict):
            continue

        kind = doc.get("kind", "")

        if kind == "Workflow":
            has_workflow = True
            tasks = doc.get("spec", {}).get("tasks", [])
            if not tasks:
                warnings.append("Workflow has no tasks")

            # Check for dependsOn references
            task_ids = {t.get("taskId") for t in tasks if isinstance(t, dict)}
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                deps = task.get("dependsOn", [])
                for dep in deps:
                    if dep not in task_ids:
                        warnings.append(
                            f"Task {task.get('taskId', '?')} depends on unknown task: {dep}"
                        )

        elif kind == "Process":
            has_process = True

        elif kind == "AgentType":
            tools = doc.get("spec", {}).get("defaultTools", [])
            for tool_entry in tools:
                if isinstance(tool_entry, dict):
                    tool_id = tool_entry.get("toolId", "")
                    if "." not in tool_id:
                        warnings.append(f"Suspicious tool ID (no dot): {tool_id}")
                elif isinstance(tool_entry, str):
                    warnings.append(f"Tool entry should be {{toolId: ...}}, got string: {tool_entry}")

        elif kind == "Agent":
            perms = doc.get("spec", {}).get("permissions", [])
            if not perms:
                warnings.append(
                    f"Agent {doc.get('metadata', {}).get('id', '?')} has no spec.permissions"
                )

    if not has_workflow:
        warnings.append("No Workflow CRD found in bundle")
    if not has_process:
        warnings.append("No Process CRD found in bundle")

    return warnings


def run_workflow(
    server: str,
    tenant: str,
    bundle_path: Path,
    token: str,
    output_base: Path,
    workflow_id: str,
) -> Path:
    """Apply CRDs and run a workflow via CognOS CLI. Returns output directory."""
    cli = "cognos"

    # Apply CRDs
    print(f"Applying bundle: {bundle_path.name}...")
    result = subprocess.run(
        [cli, "crds", "apply", "--file", str(bundle_path),
         "--server", server, "--tenant", tenant, "--token", token,
         "--output", "json", "--quiet"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        print(f"  CRD apply failed: {result.stderr}", file=sys.stderr)
        raise RuntimeError(f"CRD apply failed: {result.stderr}")
    print(f"  CRDs applied successfully.")

    # Start workflow
    print(f"Starting workflow: {workflow_id}...")
    start_result = subprocess.run(
        [cli, "workflows", "runs", "start-then-wait", workflow_id,
         "--server", server, "--tenant", tenant, "--token", token,
         "--output", "json", "--quiet", "--timeout", "1800"],
        capture_output=True, text=True, timeout=1900,
    )

    # Parse run ID from start output
    run_id = "unknown"
    try:
        start_data = json.loads(start_result.stdout)
        run_id = start_data.get("runId", start_data.get("id", "unknown"))
    except (json.JSONDecodeError, AttributeError):
        # Try to extract run ID from text output
        m = re.search(r"run[_-]?id[:\s]+([^\s]+)", start_result.stdout, re.IGNORECASE)
        if m:
            run_id = m.group(1)

    output_dir = output_base / f"{run_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    if start_result.returncode != 0:
        print(f"  Workflow may have failed: {start_result.stderr}", file=sys.stderr)
        # Save error info but continue to try downloading outputs
        (output_dir / "workflow-error.txt").write_text(
            f"stdout:\n{start_result.stdout}\n\nstderr:\n{start_result.stderr}",
            encoding="utf-8",
        )

    # Download outputs
    print(f"Downloading outputs to: {output_dir}...")
    dl_result = subprocess.run(
        [cli, "workflows", "runs", "outputs", workflow_id, run_id,
         "--server", server, "--tenant", tenant, "--token", token,
         "--output-dir", str(output_dir)],
        capture_output=True, text=True, timeout=120,
    )
    if dl_result.returncode != 0:
        print(f"  Output download warning: {dl_result.stderr}", file=sys.stderr)

    return output_dir


def parse_run_outputs(output_dir: Path) -> dict[str, Any]:
    """Parse run outputs from a completed experiment run directory.

    Expects: judge-verdict.md (and optionally run-summary.md) in directory.
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

    m = re.search(r"\*\*Run ID\*\*:\s*`([^`]+)`", text)
    if m:
        metrics["run_id"] = m.group(1)

    m = re.search(r"\*\*Duration\*\*:\s*(.+?)$", text, re.MULTILINE)
    if m:
        metrics["duration"] = m.group(1).strip()

    m = re.search(r"\*\*Total Tokens\*\*:\s*([\d,]+)", text)
    if m:
        metrics["total_tokens"] = int(m.group(1).replace(",", ""))

    m = re.search(r"\*\*Tasks\*\*:\s*(\d+)/(\d+)\s*completed,\s*(\d+)\s*failed", text)
    if m:
        metrics["tasks_completed"] = int(m.group(1))
        metrics["tasks_total"] = int(m.group(2))
        metrics["tasks_failed"] = int(m.group(3))

    # Quality trajectory
    quality_traj = re.findall(r"quality.*?:\s*\[([^\]]+)\]", text, re.IGNORECASE)
    if quality_traj:
        try:
            metrics["quality_trajectory"] = [float(x.strip()) for x in quality_traj[0].split(",")]
        except ValueError:
            pass

    # Breadth trajectory
    breadth_traj = re.findall(r"breadth.*?:\s*\[([^\]]+)\]", text, re.IGNORECASE)
    if breadth_traj:
        try:
            metrics["breadth_trajectory"] = [int(float(x.strip())) for x in breadth_traj[0].split(",")]
        except ValueError:
            pass

    return metrics


def _parse_judge_verdict(text: str) -> dict[str, Any]:
    """Extract structured scores from judge verdict markdown."""
    metrics: dict[str, Any] = {}

    # Parse markdown table with round scores
    # Pattern: | N | X.X | X.X | X.X | X.X | X.X | X.X | X.X |
    table_pattern = re.compile(
        r"\|\s*(\d+)\s*\|"
        r"\s*([\d.]+)\s*\|"
        r"\s*([\d.]+)\s*\|"
        r"\s*([\d.]+)\s*\|"
        r"\s*([\d.]+)\s*\|"
        r"\s*([\d.]+)\s*\|"
        r"\s*([\d.]+)\s*\|"
        r"\s*([\d.]+)\s*\|"
    )

    quality_trajectory = []
    dimension_scores: dict[str, list[float]] = {
        "accuracy": [], "completeness": [], "coherence": [],
        "depth": [], "falsifiability": [], "source_diversity": [],
    }

    for m in table_pattern.finditer(text):
        overall = float(m.group(8))
        quality_trajectory.append(overall)
        dimension_scores["accuracy"].append(float(m.group(2)))
        dimension_scores["completeness"].append(float(m.group(3)))
        dimension_scores["coherence"].append(float(m.group(4)))
        dimension_scores["depth"].append(float(m.group(5)))
        dimension_scores["falsifiability"].append(float(m.group(6)))
        dimension_scores["source_diversity"].append(float(m.group(7)))

    if quality_trajectory:
        metrics["quality_trajectory"] = quality_trajectory
        metrics["dimension_scores"] = dimension_scores
        metrics["final_quality"] = quality_trajectory[-1]
        metrics["initial_quality"] = quality_trajectory[0]
        metrics["quality_delta"] = round(quality_trajectory[-1] - quality_trajectory[0], 2)

    # Overall score
    m = re.search(r"overall.*?score.*?:\s*([\d.]+)", text, re.IGNORECASE)
    if m and "final_quality" not in metrics:
        metrics["final_quality"] = float(m.group(1))

    # Mode collapse
    if re.search(r"mode\s*collapse.*?(detected|yes|true)", text, re.IGNORECASE):
        metrics["mode_collapse"] = True
    elif re.search(r"mode\s*collapse.*?(not detected|no|false|none)", text, re.IGNORECASE):
        metrics["mode_collapse"] = False

    return metrics


def compare_with_baseline(metrics: dict[str, Any], experiment_id: str) -> None:
    """Print comparison table against EX-6.7b Run 6 baseline."""
    base = BASELINE_RUN6

    print(f"\n{'='*70}")
    print(f"  {experiment_id} vs BASELINE (EX-6.7b Run 6)")
    print(f"{'='*70}")
    print(f"\n{'Metric':<30} {'Baseline':>15} {'Experiment':>15} {'Delta':>10}")
    print("-" * 70)

    def _row(name: str, base_val: Any, exp_val: Any) -> None:
        if base_val is not None and exp_val is not None:
            try:
                delta = f"{float(exp_val) - float(base_val):+.2f}"
            except (ValueError, TypeError):
                delta = "N/A"
        else:
            delta = "N/A"
        print(f"{name:<30} {str(base_val):>15} {str(exp_val):>15} {delta:>10}")

    _row("Final Quality", base.get("quality_at_round_5"), metrics.get("final_quality"))
    _row("Total Tokens", base.get("total_tokens"), metrics.get("total_tokens"))
    _row("Tasks Completed", base.get("tasks_completed"), metrics.get("tasks_completed"))
    _row("Mode Collapse", False, metrics.get("mode_collapse"))

    # Quality trajectory comparison
    exp_qt = metrics.get("quality_trajectory", [])
    base_qt = base.get("quality_trajectory", [])
    if exp_qt:
        print(f"\nQuality trajectory:")
        print(f"  Baseline:   {base_qt}")
        print(f"  Experiment: {exp_qt}")

    print()


def run(
    experiment_id: str,
    parse_only: bool = False,
    output_dir: str | None = None,
    server: str = "http://localhost:8080",
    tenant: str = "acme",
    bundle: str | None = None,
    token: str = "",
) -> ExperimentResult:
    """Main experiment entry point."""
    protocol = get_protocol(experiment_id)
    exp_key = experiment_id.replace("EX-", "").replace("ex-", "")

    result = ExperimentResult(
        experiment_id=protocol.experiment_id,
        hypothesis=protocol.hypothesis,
        evidence_level=EvidenceLevel.COMPARATIVE,
    )

    if parse_only:
        if not output_dir:
            print("ERROR: --output-dir required with --parse-only", file=sys.stderr)
            result.status = Status.FAILED
            return result

        output_path = Path(output_dir)
        if not output_path.exists():
            print(f"ERROR: output directory not found: {output_path}", file=sys.stderr)
            result.status = Status.FAILED
            return result

        print(f"Parsing outputs from: {output_path}")
        metrics = parse_run_outputs(output_path)

    else:
        # Full CognOS CLI run
        if not token:
            print("ERROR: --token required for live runs", file=sys.stderr)
            result.status = Status.FAILED
            return result

        bundle_path = Path(bundle) if bundle else None
        if bundle_path is None:
            rel = BUNDLE_MAP.get(exp_key)
            if rel is None:
                print(f"ERROR: no bundle known for {experiment_id}", file=sys.stderr)
                result.status = Status.FAILED
                return result
            # Try to find the CognOS repo
            cognos_root = Path(__file__).resolve().parent.parent.parent.parent / "Cognos"
            bundle_path = cognos_root / rel
            if not bundle_path.exists():
                bundle_path = Path(rel)  # Try as-is

        if not bundle_path.exists():
            print(f"ERROR: bundle not found: {bundle_path}", file=sys.stderr)
            result.status = Status.FAILED
            return result

        # Validate
        warnings = validate_bundle(bundle_path)
        for w in warnings:
            print(f"  WARNING: {w}")

        workflow_id = WORKFLOW_MAP.get(exp_key, "")
        if not workflow_id:
            print(f"ERROR: no workflow ID known for {experiment_id}", file=sys.stderr)
            result.status = Status.FAILED
            return result

        output_base = Path(
            output_dir
            or f"C:\\Source\\CriticalInsight\\CognOS-Workloads-Outputs\\ex-6-8\\{exp_key}"
        )

        run_output_dir = run_workflow(server, tenant, bundle_path, token, output_base, workflow_id)
        metrics = parse_run_outputs(run_output_dir)
        result.artifacts["output_dir"] = str(run_output_dir)

    # Populate result
    result.status = Status.COMPLETED
    for key, val in metrics.items():
        if isinstance(val, (int, float)):
            result.add(key, val)
        elif isinstance(val, list):
            result.metadata[key] = val
        elif isinstance(val, dict):
            result.metadata[key] = val
        else:
            result.metadata[key] = val

    # Compare with baseline
    compare_with_baseline(metrics, protocol.experiment_id)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run EX-6.8 cycle design experiments via CognOS CLI.",
        epilog=(
            "Examples:\n"
            "  python -m experiments.ex6_8_cycle_design.run --experiment 6.8.4 --parse-only --output-dir ./outputs\n"
            "  python -m experiments.ex6_8_cycle_design.run --experiment 6.8.5 --server http://localhost:8080 --tenant acme --token <token>\n"
            "  python -m experiments.ex6_8_cycle_design.run --all --server http://localhost:8080 --tenant acme --token <token>\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--experiment", type=str, help="Experiment ID (e.g. 6.8.4)")
    parser.add_argument("--all", action="store_true", help="Run all Phase 1 experiments")
    parser.add_argument("--parse-only", action="store_true", help="Parse existing outputs only")
    parser.add_argument("--output-dir", type=str, help="Output directory (for parse-only or override)")
    parser.add_argument("--server", type=str, default="http://localhost:8080")
    parser.add_argument("--tenant", type=str, default="acme")
    parser.add_argument("--bundle", type=str, help="Override bundle YAML path")
    parser.add_argument("--token", type=str, default="", help="Keycloak bearer token")
    parser.add_argument("--output", type=str, help="Save result JSON to this path")

    args = parser.parse_args()

    if not args.experiment and not args.all:
        parser.error("Specify --experiment <id> or --all")

    experiment_ids = list(ALL_PROTOCOLS.keys()) if args.all else [args.experiment]

    results: list[ExperimentResult] = []
    for exp_id in experiment_ids:
        print(f"\n{'#'*70}")
        print(f"  Running EX-{exp_id}")
        print(f"{'#'*70}")

        result = run(
            experiment_id=exp_id,
            parse_only=args.parse_only,
            output_dir=args.output_dir,
            server=args.server,
            tenant=args.tenant,
            bundle=args.bundle,
            token=args.token,
        )
        results.append(result)

        if args.output:
            out_path = Path(args.output)
            if args.all:
                out_path = out_path.parent / f"{out_path.stem}-{exp_id}{out_path.suffix}"
            out_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
            print(f"Result saved to: {out_path}")

    # Summary
    if len(results) > 1:
        print(f"\n{'='*70}")
        print("  PHASE 1 SUMMARY")
        print(f"{'='*70}")
        for r in results:
            fq = r.get("final_quality")
            print(f"  {r.experiment_id}: final_quality={fq.value if fq else '?'}, "
                  f"status={r.status.value}")


if __name__ == "__main__":
    main()
