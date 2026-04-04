"""Pure Python/OpenAI runner for EX-6.8 cycle design experiments.

No CognOS dependency — reproduces the experiments using only the OpenAI API.
Data scientists, AI engineers, and NLP practitioners can run these experiments
with just an OpenAI API key.

Usage:
    # Set your API key
    export OPENAI_API_KEY=sk-...

    # Run a specific experiment
    python -m experiments.ex6_8_cycle_design.openai_runner --experiment 6.8.4

    # Run with custom topic
    python -m experiments.ex6_8_cycle_design.openai_runner --experiment 6.8.5 \
        --topic "Analyze the impact of AI regulation on global innovation"

    # Use a different model
    python -m experiments.ex6_8_cycle_design.openai_runner --experiment 6.8.10 \
        --model gpt-4o

    # Dry run (print prompts, don't call API)
    python -m experiments.ex6_8_cycle_design.openai_runner --experiment 6.8.4 --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cognos_measure.schemas import ExperimentResult, EvidenceLevel, Measurement, Status

from .protocols import (
    AgentRole,
    CycleProtocol,
    Phase,
    Round,
    Topology,
    get_protocol,
)


# ============================================================================
# OpenAI API wrapper
# ============================================================================

def _call_openai(
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-4.1",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Call OpenAI chat completions API. Returns response dict with content and usage."""
    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: openai package not installed. Run: pip install openai", file=sys.stderr)
        sys.exit(1)

    client = OpenAI()  # Uses OPENAI_API_KEY env var
    start_time = time.monotonic()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    elapsed = time.monotonic() - start_time

    content = response.choices[0].message.content or ""
    usage = response.usage
    return {
        "content": content,
        "model": response.model,
        "prompt_tokens": usage.prompt_tokens if usage else 0,
        "completion_tokens": usage.completion_tokens if usage else 0,
        "total_tokens": usage.total_tokens if usage else 0,
        "elapsed_seconds": round(elapsed, 2),
    }


def _call_openai_dry(system_prompt: str, user_prompt: str, **kwargs: Any) -> dict[str, Any]:
    """Dry-run stub — prints prompts, returns placeholder."""
    print(f"  [DRY RUN] System: {system_prompt[:100]}...")
    print(f"  [DRY RUN] User: {user_prompt[:150]}...")
    return {
        "content": "[DRY RUN — no API call made]",
        "model": kwargs.get("model", "gpt-4.1"),
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "elapsed_seconds": 0.0,
    }


# ============================================================================
# Experiment execution engine
# ============================================================================

class ExperimentRunner:
    """Execute a CycleProtocol using the OpenAI API."""

    def __init__(
        self,
        protocol: CycleProtocol,
        model: str = "gpt-4.1",
        dry_run: bool = False,
        output_dir: Path | None = None,
    ):
        self.protocol = protocol
        self.model = model
        self.dry_run = dry_run
        self.output_dir = output_dir or Path(f"outputs/{protocol.experiment_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._call = _call_openai_dry if dry_run else _call_openai

        # Running state
        self.analysis_history: list[str] = []     # generator outputs per round
        self.critique_history: list[list[str]] = []   # critic outputs per round (list of list for panel)
        self.summary_history: list[str] = []      # summarizer outputs (if applicable)
        self.usage_log: list[dict[str, Any]] = [] # all API call metadata

    def run(self) -> ExperimentResult:
        """Execute the full experiment and return structured results."""
        p = self.protocol
        print(f"\n{'='*70}")
        print(f"  {p.experiment_id}: {p.name}")
        print(f"  Topic: {p.topic[:80]}...")
        print(f"  Rounds: {p.total_rounds} | Varied: {p.varied_dimension}")
        print(f"  Model: {self.model} | Dry run: {self.dry_run}")
        print(f"{'='*70}\n")

        start_time = time.monotonic()

        for rnd in p.rounds:
            self._run_round(rnd)

        # Run judge
        judge_output = self._run_judge()

        elapsed = time.monotonic() - start_time
        total_tokens = sum(u.get("total_tokens", 0) for u in self.usage_log)

        # Parse judge output for scores
        scores = self._parse_judge_scores(judge_output)

        # Build result
        result = ExperimentResult(
            experiment_id=p.experiment_id,
            hypothesis=p.hypothesis,
            status=Status.COMPLETED,
            evidence_level=EvidenceLevel.COMPARATIVE,
            interpretation=f"Cycle design: {p.name}. {p.total_rounds} rounds.",
        )
        result.add("total_tokens", total_tokens, unit="tokens")
        result.add("elapsed_seconds", round(elapsed, 1), unit="s")
        result.add("rounds", p.total_rounds)
        result.add("model", self.model)
        result.add("api_calls", len(self.usage_log))

        for key, val in scores.items():
            result.add(key, val)

        # Save artifacts
        self._save_artifacts(result, judge_output)

        return result

    def _run_round(self, rnd: Round) -> None:
        """Execute a single round: generate → critique(s) → [summarize]."""
        p = self.protocol
        print(f"\n--- Round {rnd.number} [{rnd.phase.value.upper()}] ---")

        # === GENERATE ===
        gen_context = self._build_generator_context(rnd)
        gen_prompt = (
            f"EXPERIMENT {p.experiment_id} — ROUND {rnd.number} OF {p.total_rounds}\n\n"
            f"TOPIC: {p.topic}\n\n"
            f"INSTRUCTIONS: {rnd.generator_prompt}\n\n"
            f"{gen_context}"
        )

        print(f"  Generator...")
        gen_response = self._call(
            system_prompt=p.generator.system_prompt,
            user_prompt=gen_prompt,
            model=self.model,
        )
        self.usage_log.append({"role": "generator", "round": rnd.number, **gen_response})
        gen_output = gen_response["content"]
        self.analysis_history.append(gen_output)
        print(f"    -> {gen_response['total_tokens']} tokens, {gen_response['elapsed_seconds']}s")

        # === CRITIQUE ===
        round_critiques: list[str] = []

        if rnd.topology == Topology.PARALLEL_FAN and not self.dry_run:
            # Parallel critic execution
            print(f"  Critics (parallel: {len(rnd.critic_roles)})...")
            with ThreadPoolExecutor(max_workers=len(rnd.critic_roles)) as executor:
                futures = {}
                for critic in rnd.critic_roles:
                    crit_prompt = self._build_critic_prompt(rnd, critic, gen_output)
                    future = executor.submit(
                        self._call,
                        system_prompt=critic.system_prompt,
                        user_prompt=crit_prompt,
                        model=self.model,
                    )
                    futures[future] = critic.name

                for future in as_completed(futures):
                    name = futures[future]
                    crit_response = future.result()
                    self.usage_log.append({"role": name, "round": rnd.number, **crit_response})
                    round_critiques.append(f"[{name.upper()}]\n{crit_response['content']}")
                    print(f"    {name}: {crit_response['total_tokens']} tokens")
        else:
            # Sequential critic execution (or parallel in dry-run mode)
            for critic in rnd.critic_roles:
                crit_prompt = self._build_critic_prompt(rnd, critic, gen_output)
                print(f"  Critic ({critic.name})...")
                crit_response = self._call(
                    system_prompt=critic.system_prompt,
                    user_prompt=crit_prompt,
                    model=self.model,
                )
                self.usage_log.append({"role": critic.name, "round": rnd.number, **crit_response})
                round_critiques.append(f"[{critic.name.upper()}]\n{crit_response['content']}")
                print(f"    -> {crit_response['total_tokens']} tokens, {crit_response['elapsed_seconds']}s")

        self.critique_history.append(round_critiques)

        # === SUMMARIZE (if applicable) ===
        if rnd.has_summarizer:
            print(f"  Summarizer...")
            summary_context = (
                f"ROUND {rnd.number} ANALYSIS:\n{gen_output}\n\n"
                f"ROUND {rnd.number} CRITIQUES:\n{''.join(round_critiques)}\n\n"
                f"INSTRUCTIONS: {rnd.summarizer_prompt}"
            )
            sum_response = self._call(
                system_prompt=(
                    "You are a Context Summarizer. Produce concise, lossless-intent "
                    "summaries. Compress to 500 words maximum. Preserve ALL distinct "
                    "claims and objections. Remove only redundancy."
                ),
                user_prompt=summary_context,
                model=self.model,
                max_tokens=1024,
            )
            self.usage_log.append({"role": "summarizer", "round": rnd.number, **sum_response})
            self.summary_history.append(sum_response["content"])
            print(f"    -> {sum_response['total_tokens']} tokens")

    def _build_generator_context(self, rnd: Round) -> str:
        """Build context for the generator based on experiment design."""
        if rnd.number == 1:
            return "This is Round 1. Produce your initial comprehensive analysis."

        p = self.protocol

        # EX-6.8.1: Compressed context — use summary instead of full history
        if p.experiment_id == "EX-6.8.1" and self.summary_history:
            return (
                f"CONTEXT (compressed summary from Round {rnd.number - 1}):\n"
                f"{self.summary_history[-1]}\n\n"
                "Work from this summary only."
            )

        # EX-6.8.10: Selective attention — only most recent critique
        if p.experiment_id == "EX-6.8.10" and self.critique_history:
            latest_critiques = self.critique_history[-1]
            return (
                "MOST RECENT CRITIQUE (read only this — NOT earlier rounds):\n"
                f"{''.join(latest_critiques)}\n\n"
                "Address these objections specifically."
            )

        # Default: full history
        context_parts = []
        for i, (analysis, critiques) in enumerate(
            zip(self.analysis_history, self.critique_history), 1
        ):
            context_parts.append(f"ROUND {i} ANALYSIS (excerpt):\n{analysis[:1000]}...\n")
            context_parts.append(f"ROUND {i} CRITIQUES:\n{''.join(critiques)}\n")
        return "\n".join(context_parts)

    def _build_critic_prompt(self, rnd: Round, critic: AgentRole, gen_output: str) -> str:
        """Build the prompt for a critic."""
        return (
            f"EXPERIMENT {self.protocol.experiment_id} — ROUND {rnd.number} CRITIQUE\n\n"
            f"ANALYSIS TO CRITIQUE:\n{gen_output}\n\n"
            f"YOUR SPECIFIC MANDATE:\n{critic.skill_prompt}"
        )

    def _run_judge(self) -> str:
        """Run the judge to score all rounds."""
        p = self.protocol
        print(f"\n--- JUDGE ---")

        # Build full transcript for the judge
        transcript_parts = []
        for i, (analysis, critiques) in enumerate(
            zip(self.analysis_history, self.critique_history), 1
        ):
            phase = p.rounds[i - 1].phase.value if i <= len(p.rounds) else "unknown"
            transcript_parts.append(f"=== ROUND {i} [{phase.upper()}] ===\n")
            transcript_parts.append(f"GENERATION:\n{analysis}\n\n")
            transcript_parts.append(f"CRITIQUES:\n{''.join(critiques)}\n")

        transcript = "\n".join(transcript_parts)

        judge_prompt = (
            f"EXPERIMENT {p.experiment_id}: {p.name}\n"
            f"Design: {p.description}\n"
            f"Hypothesis: {p.hypothesis}\n\n"
            f"FULL TRANSCRIPT ({p.total_rounds} rounds):\n{transcript}\n\n"
            f"SCORING INSTRUCTIONS:\n{p.judge.skill_prompt}\n\n"
            f"Score each round. Build the diminishing returns table. "
            f"Analyze convergence, breadth trajectory, and mode collapse. "
            f"Provide specific analysis of the experimental variable "
            f"({p.varied_dimension})."
        )

        judge_response = self._call(
            system_prompt=p.judge.system_prompt,
            user_prompt=judge_prompt,
            model=self.model,
            max_tokens=4096,
        )
        self.usage_log.append({"role": "judge", "round": 0, **judge_response})
        print(f"  -> {judge_response['total_tokens']} tokens, {judge_response['elapsed_seconds']}s")

        return judge_response["content"]

    def _parse_judge_scores(self, judge_output: str) -> dict[str, Any]:
        """Extract structured scores from judge output text."""
        scores: dict[str, Any] = {}

        # Extract overall scores per round from table
        # Pattern: | N | X.X | X.X | X.X | X.X | X.X | X.X | X.X |
        table_pattern = re.compile(
            r"\|\s*(\d+)\s*\|"  # round number
            r"\s*([\d.]+)\s*\|"  # accuracy
            r"\s*([\d.]+)\s*\|"  # completeness
            r"\s*([\d.]+)\s*\|"  # coherence
            r"\s*([\d.]+)\s*\|"  # depth
            r"\s*([\d.]+)\s*\|"  # falsifiability
            r"\s*([\d.]+)\s*\|"  # source diversity
            r"\s*([\d.]+)\s*\|"  # overall
        )

        quality_trajectory = []
        for m in table_pattern.finditer(judge_output):
            rnd_num = int(m.group(1))
            overall = float(m.group(8))
            quality_trajectory.append(overall)
            scores[f"round_{rnd_num}_overall"] = overall
            scores[f"round_{rnd_num}_accuracy"] = float(m.group(2))
            scores[f"round_{rnd_num}_completeness"] = float(m.group(3))
            scores[f"round_{rnd_num}_coherence"] = float(m.group(4))
            scores[f"round_{rnd_num}_depth"] = float(m.group(5))
            scores[f"round_{rnd_num}_falsifiability"] = float(m.group(6))
            scores[f"round_{rnd_num}_source_diversity"] = float(m.group(7))

        if quality_trajectory:
            scores["quality_trajectory"] = quality_trajectory
            scores["final_quality"] = quality_trajectory[-1]
            scores["initial_quality"] = quality_trajectory[0]
            scores["quality_delta"] = round(quality_trajectory[-1] - quality_trajectory[0], 2)

        return scores

    def _save_artifacts(self, result: ExperimentResult, judge_output: str) -> None:
        """Save all outputs to the output directory."""
        # Save judge verdict
        verdict_path = self.output_dir / "judge-verdict.md"
        verdict_path.write_text(judge_output, encoding="utf-8")
        result.artifacts["judge_verdict"] = str(verdict_path)

        # Save analysis rounds
        for i, analysis in enumerate(self.analysis_history, 1):
            path = self.output_dir / f"round-{i}-analysis.md"
            path.write_text(analysis, encoding="utf-8")
            result.artifacts[f"round_{i}_analysis"] = str(path)

        # Save critiques
        for i, critiques in enumerate(self.critique_history, 1):
            path = self.output_dir / f"round-{i}-critiques.md"
            path.write_text("\n\n---\n\n".join(critiques), encoding="utf-8")
            result.artifacts[f"round_{i}_critiques"] = str(path)

        # Save summaries (if any)
        for i, summary in enumerate(self.summary_history, 1):
            path = self.output_dir / f"round-{i}-summary.md"
            path.write_text(summary, encoding="utf-8")
            result.artifacts[f"round_{i}_summary"] = str(path)

        # Save usage log
        usage_path = self.output_dir / "usage-log.json"
        usage_path.write_text(
            json.dumps(self.usage_log, indent=2, default=str), encoding="utf-8"
        )
        result.artifacts["usage_log"] = str(usage_path)

        # Save result
        result_path = self.output_dir / "result.json"
        result_path.write_text(
            result.model_dump_json(indent=2), encoding="utf-8"
        )

        print(f"\nArtifacts saved to: {self.output_dir}")


# ============================================================================
# Comparison
# ============================================================================

def compare_experiments(results: list[ExperimentResult]) -> None:
    """Print comparison table across multiple experiment results."""
    if not results:
        return

    print(f"\n{'='*80}")
    print("  EXPERIMENT COMPARISON")
    print(f"{'='*80}")
    print(f"\n{'Experiment':<20} {'Rounds':>6} {'Final Q':>8} {'Delta Q':>8} {'Tokens':>10} {'Time (s)':>10}")
    print("-" * 70)

    for r in results:
        exp_id = r.experiment_id
        rounds = r.get("rounds")
        final_q = r.get("final_quality")
        delta_q = r.get("quality_delta")
        tokens = r.get("total_tokens")
        elapsed = r.get("elapsed_seconds")

        print(
            f"{exp_id:<20} "
            f"{rounds.value if rounds else '?':>6} "
            f"{final_q.value if final_q else '?':>8} "
            f"{delta_q.value if delta_q else '?':>8} "
            f"{tokens.value if tokens else '?':>10} "
            f"{elapsed.value if elapsed else '?':>10}"
        )

    print()


# ============================================================================
# CLI
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run EX-6.8 cycle design experiments using the OpenAI API directly.",
        epilog=(
            "Examples:\n"
            "  python -m experiments.ex6_8_cycle_design.openai_runner --experiment 6.8.4\n"
            "  python -m experiments.ex6_8_cycle_design.openai_runner --experiment 6.8.5 --dry-run\n"
            "  python -m experiments.ex6_8_cycle_design.openai_runner --all\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--experiment", type=str, default=None,
        help="Experiment ID (e.g. 6.8.4, 6.8.5, 6.8.10, 6.8.1). Use --all for all.",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Run all Phase 1 experiments",
    )
    parser.add_argument(
        "--topic", type=str, default=None,
        help="Override the experiment topic",
    )
    parser.add_argument(
        "--model", type=str, default="gpt-4.1",
        help="OpenAI model to use (default: gpt-4.1)",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Base output directory (default: outputs/<experiment-id>)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print prompts without calling the API",
    )

    args = parser.parse_args()

    if not args.experiment and not args.all:
        parser.error("Specify --experiment <id> or --all")

    # Determine which experiments to run
    if args.all:
        experiment_ids = ["6.8.4", "6.8.10", "6.8.5", "6.8.1"]
    else:
        experiment_ids = [args.experiment]

    results: list[ExperimentResult] = []
    for exp_id in experiment_ids:
        protocol = get_protocol(exp_id)
        if args.topic:
            protocol.topic = args.topic

        output_dir = Path(args.output_dir) if args.output_dir else None
        if output_dir and len(experiment_ids) > 1:
            output_dir = output_dir / protocol.experiment_id

        runner = ExperimentRunner(
            protocol=protocol,
            model=args.model,
            dry_run=args.dry_run,
            output_dir=output_dir,
        )
        result = runner.run()
        results.append(result)

    if len(results) > 1:
        compare_experiments(results)


if __name__ == "__main__":
    main()
