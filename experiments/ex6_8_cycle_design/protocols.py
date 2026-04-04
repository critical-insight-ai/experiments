"""EX-6.8: Cycle Design Variations — protocol definitions.

Each experiment is a CycleProtocol that defines:
- Round structure (who speaks, in what order/topology)
- Agent role definitions (system prompts)
- Skill specifications (per-phase or per-specialist instructions)
- Measurement extraction patterns

These protocols are used by both:
1. run.py (CognOS CLI mode — applies YAML, runs workflow, parses outputs)
2. openai_runner.py (Pure Python/OpenAI mode — no CognOS dependency)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Topology(str, Enum):
    """How agents interact within a round."""
    SEQUENTIAL = "sequential"     # gen → crit (baseline)
    PARALLEL_FAN = "parallel_fan" # gen → [crit1, crit2, crit3] → gen (EX-6.8.5)


class Phase(str, Enum):
    """Phase label for phased-role experiments."""
    BREADTH = "breadth"
    DEPTH = "depth"
    POLISH = "polish"
    UNIFORM = "uniform"  # baseline — same prompt every round


@dataclass
class AgentRole:
    """An agent's identity and behavior specification."""
    name: str
    system_prompt: str
    skill_prompt: str  # the specific skill/procedure for this agent in this context
    model: str = "gpt-4.1"


@dataclass
class Round:
    """A single round in the cycle."""
    number: int
    phase: Phase = Phase.UNIFORM
    generator_prompt: str = ""
    critic_roles: list[AgentRole] = field(default_factory=list)
    topology: Topology = Topology.SEQUENTIAL
    has_summarizer: bool = False
    summarizer_prompt: str = ""


@dataclass
class CycleProtocol:
    """Complete experiment protocol definition."""
    experiment_id: str
    name: str
    hypothesis: str
    description: str
    rounds: list[Round]
    generator: AgentRole
    judge: AgentRole
    topic: str = (
        "Analyze the geopolitical implications of semiconductor supply chain "
        "concentration in East Asia. Consider economic, military, technological, "
        "and diplomatic dimensions. Produce specific, falsifiable predictions "
        "for 2026-2030."
    )
    seed: str = ""
    budget_per_round_usd: float = 6.0

    @property
    def total_rounds(self) -> int:
        return len(self.rounds)

    @property
    def varied_dimension(self) -> str:
        """What this experiment varies vs baseline."""
        return self.description.split(":")[0].strip() if ":" in self.description else self.description


# ============================================================================
# Shared agent definitions
# ============================================================================

GENERATOR_SYSTEM_PROMPT = (
    "You are an expert intelligence analyst. You produce comprehensive, "
    "evidence-based geopolitical analysis. You respond to critique by "
    "strengthening your arguments, adding new evidence, and expanding scope. "
    "You never become defensive — every objection is an opportunity to improve."
)

CRITIC_SYSTEM_PROMPT = (
    "You are a rigorous adversarial critic. You find weaknesses in analysis: "
    "weak evidence, logical fallacies, missing perspectives, unfalsifiable claims, "
    "and methodological gaps. You are thorough but fair — you acknowledge "
    "strong arguments while ruthlessly targeting weak ones."
)

JUDGE_SYSTEM_PROMPT = (
    "You are an impartial judge evaluating the quality of intelligence analysis "
    "across multiple rounds of adversarial refinement. You score on 6 dimensions: "
    "ACCURACY (0.25), COMPLETENESS (0.20), COHERENCE (0.20), DEPTH (0.15), "
    "FALSIFIABILITY (0.10), SOURCE_DIVERSITY (0.10). You track convergence, "
    "breadth, and mode collapse."
)

JUDGE_SKILL = """Score each round on 6 dimensions (1-10 each):
- ACCURACY (weight 0.25): Factual correctness, evidence quality, calibration
- COMPLETENESS (weight 0.20): Breadth of coverage, stakeholder diversity
- COHERENCE (weight 0.20): Logical consistency, narrative flow, no contradictions
- DEPTH (weight 0.15): Analytical depth, causal reasoning, mechanism identification
- FALSIFIABILITY (weight 0.10): Testable predictions, confidence calibration
- SOURCE_DIVERSITY (weight 0.10): Primary vs secondary, geographic diversity

OVERALL = ACCURACY*0.25 + COMPLETENESS*0.20 + COHERENCE*0.20 + DEPTH*0.15 + FALSIFIABILITY*0.10 + SOURCE_DIVERSITY*0.10

Output a table:
| Round | ACCURACY | COMPLETENESS | COHERENCE | DEPTH | FALSIFIABILITY | SOURCE_DIVERSITY | OVERALL |
Plus: convergence analysis, breadth trajectory, mode collapse detection."""


BASELINE_GENERATOR = AgentRole(
    name="generator",
    system_prompt=GENERATOR_SYSTEM_PROMPT,
    skill_prompt=(
        "Research the topic broadly. Structure analysis into multiple domains "
        "(economic, military, technological, diplomatic, social). Include "
        "perspectives from multiple geographic regions. For each claim, cite "
        "evidence. For each prediction, include confidence % and falsification "
        "condition. In subsequent rounds, read all critic objections and "
        "address each one. Add at least 2 new arguments and 1 new source "
        "per round. Never drop existing themes."
    ),
)

BASELINE_CRITIC = AgentRole(
    name="critic",
    system_prompt=CRITIC_SYSTEM_PROMPT,
    skill_prompt=(
        "Critique the analysis on 5 dimensions:\n"
        "1. EVIDENTIARY: Is each claim backed by cited evidence?\n"
        "2. LOGICAL: Any fallacies, hidden assumptions, invalid causal chains?\n"
        "3. FALSIFICATION: Are predictions specific and testable?\n"
        "4. SCOPE: Missing regions, stakeholders, time horizons, domains?\n"
        "5. METHODOLOGICAL: Framework breadth, disciplinary balance?\n"
        "Output numbered objections: [CRITICAL-N], [MAJOR-N], [MINOR-N]."
    ),
)

BASELINE_JUDGE = AgentRole(
    name="judge",
    system_prompt=JUDGE_SYSTEM_PROMPT,
    skill_prompt=JUDGE_SKILL,
)


# ============================================================================
# Protocol: EX-6.8.4 — Phased Role Specialization
# ============================================================================

def make_phased_roles_protocol() -> CycleProtocol:
    """EX-6.8.4: Breadth (R1-2) → Depth (R3-4) → Polish (R5)."""

    breadth_gen_skill = (
        "BREADTH PHASE: Maximize scope and coverage. Structure into 5+ distinct "
        "domains. Include 4+ geographic regions. Add 3+ new perspectives per round. "
        "If you find yourself deepening one area, STOP and add breadth instead."
    )
    depth_gen_skill = (
        "DEPTH PHASE: Strengthen evidence quality. Replace qualitative with "
        "quantitative. Add primary sources. Strengthen causal chains. Add "
        "confidence calibration (%) to predictions. Do NOT drop breadth themes."
    )
    polish_gen_skill = (
        "POLISH PHASE: Focus on coherence and actionability. Resolve contradictions. "
        "Merge redundancies. Produce confidence-calibrated summary table. "
        "Remove excessive hedging. Do NOT delete claims — only tighten."
    )
    breadth_crit_skill = (
        "BREADTH CRITIQUE: Focus on GAPS. Missing regions? Missing stakeholders? "
        "Missing domains? Missing time horizons? Missing second-order effects? "
        "Note evidence issues as [DEPTH-PHASE] for later. "
        "Output: [CRITICAL-N] MISSING DOMAIN, [MAJOR-N] MISSING PERSPECTIVE."
    )
    depth_crit_skill = (
        "DEPTH CRITIQUE: Focus on EVIDENCE AND LOGIC. Weak sources? Correlation "
        "vs causation? Hidden assumptions? Unfalsifiable predictions? Bad "
        "calibration? Output: [CRITICAL-N] WEAK EVIDENCE, [MAJOR-N] LOGIC GAP."
    )
    polish_crit_skill = (
        "POLISH CRITIQUE: Focus on COHERENCE. Contradictions? Redundancies? "
        "Dangling threads? Summary accuracy? Provide FINAL ASSESSMENT: "
        "objections addressed vs unaddressed, improvement plateau round."
    )

    rounds = [
        Round(1, Phase.BREADTH, generator_prompt=breadth_gen_skill,
              critic_roles=[AgentRole("critic", CRITIC_SYSTEM_PROMPT, breadth_crit_skill)]),
        Round(2, Phase.BREADTH, generator_prompt=breadth_gen_skill,
              critic_roles=[AgentRole("critic", CRITIC_SYSTEM_PROMPT, breadth_crit_skill)]),
        Round(3, Phase.DEPTH, generator_prompt=depth_gen_skill,
              critic_roles=[AgentRole("critic", CRITIC_SYSTEM_PROMPT, depth_crit_skill)]),
        Round(4, Phase.DEPTH, generator_prompt=depth_gen_skill,
              critic_roles=[AgentRole("critic", CRITIC_SYSTEM_PROMPT, depth_crit_skill)]),
        Round(5, Phase.POLISH, generator_prompt=polish_gen_skill,
              critic_roles=[AgentRole("critic", CRITIC_SYSTEM_PROMPT, polish_crit_skill)]),
    ]

    return CycleProtocol(
        experiment_id="EX-6.8.4",
        name="Phased Role Specialization",
        hypothesis=(
            "Phase-specific prompts (breadth→depth→polish) produce a different "
            "convergence curve than uniform prompts, with faster early breadth "
            "and higher final depth scores."
        ),
        description="Role Specialization: generator and critic prompts change per phase",
        rounds=rounds,
        generator=AgentRole("generator", GENERATOR_SYSTEM_PROMPT, ""),
        judge=BASELINE_JUDGE,
        seed="EX-6.8.4-semiconductor-geopolitics-phased",
    )


# ============================================================================
# Protocol: EX-6.8.10 — Selective Attention
# ============================================================================

def make_selective_attention_protocol() -> CycleProtocol:
    """EX-6.8.10: Generator reads only the most recent critique."""

    constrained_gen_skill = (
        "ATTENTION CONSTRAINT: Read ONLY the critic's most recent critique. "
        "Do NOT reference earlier rounds or full document history. "
        "Address those objections. Add 2+ new arguments, 1+ new source."
    )

    rounds = [
        Round(1, Phase.UNIFORM, generator_prompt=BASELINE_GENERATOR.skill_prompt,
              critic_roles=[AgentRole("critic", CRITIC_SYSTEM_PROMPT, BASELINE_CRITIC.skill_prompt)]),
        Round(2, Phase.UNIFORM, generator_prompt=constrained_gen_skill,
              critic_roles=[AgentRole("critic", CRITIC_SYSTEM_PROMPT, BASELINE_CRITIC.skill_prompt)]),
        Round(3, Phase.UNIFORM, generator_prompt=constrained_gen_skill,
              critic_roles=[AgentRole("critic", CRITIC_SYSTEM_PROMPT, BASELINE_CRITIC.skill_prompt)]),
        Round(4, Phase.UNIFORM, generator_prompt=constrained_gen_skill,
              critic_roles=[AgentRole("critic", CRITIC_SYSTEM_PROMPT, BASELINE_CRITIC.skill_prompt)]),
        Round(5, Phase.UNIFORM, generator_prompt=constrained_gen_skill,
              critic_roles=[AgentRole("critic", CRITIC_SYSTEM_PROMPT, BASELINE_CRITIC.skill_prompt)]),
    ]

    return CycleProtocol(
        experiment_id="EX-6.8.10",
        name="Selective Attention",
        hypothesis=(
            "Constraining the generator to read only the most recent critique "
            "reduces 'critique anchoring' and increases breadth, at the cost "
            "of some convergence speed."
        ),
        description="Context Window: generator reads only most recent critique",
        rounds=rounds,
        generator=BASELINE_GENERATOR,
        judge=BASELINE_JUDGE,
        seed="EX-6.8.10-semiconductor-geopolitics-selective",
    )


# ============================================================================
# Protocol: EX-6.8.5 — Multi-Critic Panel
# ============================================================================

def make_multi_critic_protocol() -> CycleProtocol:
    """EX-6.8.5: 3 parallel specialized critics (accuracy, coherence, scope)."""

    accuracy_critic = AgentRole(
        name="critic-accuracy",
        system_prompt=(
            "You are a specialized ACCURACY CRITIC. Focus ONLY on factual accuracy "
            "and evidence quality. Leave coherence and scope to other panel members."
        ),
        skill_prompt=(
            "For each claim: Is there a cited source? Primary or secondary? "
            "Could evidence support a different conclusion? Conflicting sources ignored? "
            "For predictions: Falsifiable? Calibrated? Base rates considered? "
            "Output: [ACC-CRITICAL-N], [ACC-MAJOR-N], [ACC-MINOR-N]."
        ),
    )
    coherence_critic = AgentRole(
        name="critic-coherence",
        system_prompt=(
            "You are a specialized COHERENCE CRITIC. Focus ONLY on logical consistency, "
            "narrative flow, and structural integrity. Leave accuracy and scope to "
            "other panel members."
        ),
        skill_prompt=(
            "Find: logical fallacies, hidden assumptions, contradictions, non-sequiturs, "
            "structural weaknesses, narrative gaps. "
            "Output: [COH-CRITICAL-N], [COH-MAJOR-N], [COH-MINOR-N]."
        ),
    )
    scope_critic = AgentRole(
        name="critic-scope",
        system_prompt=(
            "You are a specialized SCOPE CRITIC. Focus ONLY on completeness, breadth, "
            "and missing perspectives. Leave accuracy and coherence to other panel members."
        ),
        skill_prompt=(
            "Find: missing regions, stakeholder groups, time horizons, adjacent domains, "
            "second-order effects, alternative scenarios, disciplinary tunnel vision. "
            "Output: [SCP-CRITICAL-N], [SCP-MAJOR-N], [SCP-MINOR-N]."
        ),
    )

    panel = [accuracy_critic, coherence_critic, scope_critic]

    rounds = [
        Round(1, Phase.UNIFORM, generator_prompt=BASELINE_GENERATOR.skill_prompt,
              critic_roles=panel, topology=Topology.PARALLEL_FAN),
        Round(2, Phase.UNIFORM,
              generator_prompt=(
                  "You received critiques from 3 specialists: accuracy [ACC-*], "
                  "coherence [COH-*], scope [SCP-*]. Address each category. "
                  "Add 2+ new arguments and 1+ new source."
              ),
              critic_roles=panel, topology=Topology.PARALLEL_FAN),
        Round(3, Phase.UNIFORM,
              generator_prompt=(
                  "FINAL ROUND. Address all remaining specialist objections. "
                  "Produce the strongest possible final version with "
                  "confidence-calibrated summary table."
              ),
              critic_roles=panel, topology=Topology.PARALLEL_FAN),
    ]

    return CycleProtocol(
        experiment_id="EX-6.8.5",
        name="Multi-Critic Panel",
        hypothesis=(
            "Three specialized critics (accuracy, coherence, scope) working in "
            "parallel find different flaws than a generalist, achieving higher "
            "quality-per-round at higher cost-per-round."
        ),
        description="Critique Topology: 3 parallel specialized critics",
        rounds=rounds,
        generator=BASELINE_GENERATOR,
        judge=BASELINE_JUDGE,
        seed="EX-6.8.5-semiconductor-geopolitics-panel",
        budget_per_round_usd=12.0,
    )


# ============================================================================
# Protocol: EX-6.8.1 — Compressed Context
# ============================================================================

def make_compressed_context_protocol() -> CycleProtocol:
    """EX-6.8.1: Summarizer agent compresses context between rounds."""

    summarizer_prompt = (
        "Produce a 500-word maximum CUMULATIVE context summary:\n"
        "1. CURRENT STATE (100w): status, coverage\n"
        "2. DISTINCT CLAIMS (200w): numbered, marked [STRONG/MODERATE/WEAK]\n"
        "3. UNRESOLVED OBJECTIONS (100w): numbered, [CRITICAL/MAJOR/MINOR]\n"
        "4. METRICS SNAPSHOT (50w): themes, regions, sources, predictions\n"
        "5. PRIORITY FOR NEXT ROUND (50w): top 3 focus areas"
    )

    constrained_gen_skill = (
        "Read ONLY the [CONTEXT-SUMMARY] — a 500-word compressed brief. "
        "Do NOT read full document history. Address unresolved objections. "
        "Strengthen weak claims. Add 2+ new arguments, 1+ new source."
    )

    rounds = [
        Round(1, Phase.UNIFORM, generator_prompt=BASELINE_GENERATOR.skill_prompt,
              critic_roles=[AgentRole("critic", CRITIC_SYSTEM_PROMPT, BASELINE_CRITIC.skill_prompt)],
              has_summarizer=True, summarizer_prompt=summarizer_prompt),
        Round(2, Phase.UNIFORM, generator_prompt=constrained_gen_skill,
              critic_roles=[AgentRole("critic", CRITIC_SYSTEM_PROMPT, BASELINE_CRITIC.skill_prompt)],
              has_summarizer=True, summarizer_prompt=summarizer_prompt),
        Round(3, Phase.UNIFORM, generator_prompt=constrained_gen_skill,
              critic_roles=[AgentRole("critic", CRITIC_SYSTEM_PROMPT, BASELINE_CRITIC.skill_prompt)],
              has_summarizer=True, summarizer_prompt=summarizer_prompt),
        Round(4, Phase.UNIFORM, generator_prompt=constrained_gen_skill,
              critic_roles=[AgentRole("critic", CRITIC_SYSTEM_PROMPT, BASELINE_CRITIC.skill_prompt)],
              has_summarizer=True, summarizer_prompt=summarizer_prompt),
        Round(5, Phase.UNIFORM, generator_prompt=constrained_gen_skill,
              critic_roles=[AgentRole("critic", CRITIC_SYSTEM_PROMPT, BASELINE_CRITIC.skill_prompt)],
              has_summarizer=False),  # No summary after final round
    ]

    return CycleProtocol(
        experiment_id="EX-6.8.1",
        name="Compressed Context",
        hypothesis=(
            "Summarizer-compressed context prevents context bloat and mode "
            "collapse. Trade-off: summarizer may lose nuance. Net effect "
            "on quality ceiling and convergence speed is unknown."
        ),
        description="Context Window: summarizer compresses context between rounds",
        rounds=rounds,
        generator=BASELINE_GENERATOR,
        judge=BASELINE_JUDGE,
        seed="EX-6.8.1-semiconductor-geopolitics-compressed",
    )


# ============================================================================
# Registry
# ============================================================================

ALL_PROTOCOLS = {
    "6.8.1": make_compressed_context_protocol,
    "6.8.4": make_phased_roles_protocol,
    "6.8.5": make_multi_critic_protocol,
    "6.8.10": make_selective_attention_protocol,
}


def get_protocol(experiment_id: str) -> CycleProtocol:
    """Look up a protocol by experiment number (e.g. '6.8.4')."""
    key = experiment_id.replace("EX-", "").replace("ex-", "")
    factory = ALL_PROTOCOLS.get(key)
    if factory is None:
        raise ValueError(
            f"Unknown experiment: {experiment_id}. "
            f"Available: {', '.join(sorted(ALL_PROTOCOLS.keys()))}"
        )
    return factory()
