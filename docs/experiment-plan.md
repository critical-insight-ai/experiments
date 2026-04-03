# Experiment Plan: Hypothesis → Experiment → Article Mapping

This document maps every testable hypothesis from the CriticalInsights article series
to concrete experiments, data sources, difficulty assessments, and article support.

## Priority Ranking

Experiments ranked by: (1) data readiness, (2) reproducibility, (3) article urgency.

| Priority | Experiment | Hypothesis | Difficulty | Status | Articles |
|----------|-----------|------------|-----------|--------|----------|
| 1 | EX-1 Compositional Coverage | H-2 | Easy | **COMPLETE** | A2, A5 |
| 2 | EX-6.3 Git GI Analysis | H-5, H-1.3 | Easy | **COMPLETE** | A2, A6 |
| 3 | EX-6.2 GI Balance vs Quality | H-1.2 | Medium | Designed | A4, A6 |
| 4 | EX-3.1 Evidence Ordering | H-3 | Medium | Designed | A3 |
| 5 | EX-6.7 Cooperative Antagonism | H-4 | Medium | Run 1 done | A7, A9 |
| 6 | EX-2 Hierarchical Retrieval | H-6 | Medium | Designed | A3 |
| 7 | EX-5 Workload Re-runs | H-3 | Medium | Planned | A7, A8 |
| 8 | EX-6.4 Cross-domain Falsification | H-2, H-8 | Hard | Designed | A5, A10 |
| 9 | EX-4 Agent-as-Architect | H-6, H-7 | Hard | Designed | A8 |
| 10 | EX-6.6 Optimal Integration Freq | H-1.4 | Hard | Designed | A6, A10 |

---

## Hypothesis Register (Summary)

| ID | Statement | Testable? | Key Mechanism |
|----|-----------|-----------|---------------|
| H-1 | GI duality is a structural property of intelligence | Yes | Phase classification |
| H-1.1 | GI is structure, not pattern | Partially | Layer analysis |
| H-1.2 | GI balance predicts output quality | Yes | Quality correlation |
| H-1.3 | G/I phases are measurable in code | Yes | Commit classification |
| H-1.4 | Optimal integration frequency exists | Yes | Frequency sweep |
| H-2 | Compositional completeness enables coverage | Yes | CRD vocabulary analysis |
| H-3 | Compounding returns emerge from sprint reuse | Yes | Kind inheritance tracking |
| H-4 | Cooperative antagonism improves output | Yes | Multi-agent comparison |
| H-5 | The cognitive flywheel exhibits GI dynamics | Yes | Git history analysis |
| H-6 | Agents achieve system intelligence via memory | Partially | Retrieval quality |
| H-7 | Processes converge to attractor states | Partially | Workflow analysis |
| H-8 | Theory triangulation strengthens claims | Yes | Multi-framework mapping |

---

## Detailed Experiment Designs

### EX-1: Compositional Coverage (COMPLETE)

**Hypothesis**: H-2 — CognOS's 164 CRD kinds form a compositionally complete vocabulary
that enables domain-agnostic workload construction.

**Data source**: CognOS workload YAML bundles (`deploy/docker/bundles/demos/`)

**Measurements**:
- Activation census: which kinds are used by which workloads
- Coverage ratio: what fraction of the 164 kinds are activated
- Frequency distribution: power-law vs uniform
- Pairwise Jaccard similarity: cross-domain vocabulary overlap
- Cumulative saturation curve: does adding workloads plateau?
- Compression metrics: specification sparsity and cognitive load

**Results (first run)**:
- 65/164 kinds (39.6%) activated across 8 workloads
- DIANA↔Resale Jaccard: 0.789 (cross-domain sharing)
- Blackjack↔TTS Jaccard: 1.000 (identical primitive vocabulary)
- Logarithmic saturation R²=0.868 (strong fit)
- Saturation curve: coverage = 21.2·ln(step) + 23.9
- 23 universal kinds, 12 common, 16 domain-specific, 14 rare

**Interpretation**: Strong evidence for compositional completeness. The vocabulary
saturates logarithmically — early workloads discover most kinds, later workloads
reuse existing vocabulary. The high cross-domain Jaccard (DIANA↔Resale: 0.789)
confirms domain-agnostic composition.

**Caveats**: N=1 builder; 60.4% of kinds unactivated; no formal completeness proof.

**Supports articles**: A2 (Compositional Completeness), A5 (Integration Window)

---

### EX-6.3: Git GI Analysis (COMPLETE)

**Hypothesis**: H-5/H-1.3 — The cognitive flywheel exhibits measurable GI dynamics
observable in Git commit patterns.

**Data source**: CognOS Git repository (2,614 commits, Aug 2025–Apr 2026)

**Measurements**:
- Commit classification: Generation/Integration/Ambiguous (Layer 4 keyword heuristic)
- Overall GI ratio and balance
- Weekly windowed GI dynamics
- GI rhythm score (oscillation analysis)
- Phase-by-phase analysis (P1-P4 development phases)
- Commit velocity correlation

**Results (first run)**:
- Overall: G=455 (17%), I=1242 (48%), A=917 (35%)
- GI ratio: 0.37 (integration-heavy)
- Rhythm score: 0.10 (low oscillation, potential phase lock)
- All phases show integration dominance:
  - P1 Hardening: R=0.36
  - P2 Surface polish: R=0.39
  - P3 Release prep: R=0.19
  - P4 Workload sprints: R=0.30
- Velocity: 11.9 commits/day, 75% active days

**Interpretation**: The integration-heavy signal is expected for a mature platform
in hardening/polish phases. The 35% ambiguous rate signals the Layer 4 keyword
heuristic needs refinement. Key open question: does the GI ratio correlate with
output quality? (→ EX-6.2)

**Refinement needed**:
1. Layer 3 classification (operational intent from diff stats) to reduce ambiguity
2. File-type-aware classification (new YAML files = generative, refactored C# = integrative)
3. Sprint-segmented analysis (workload sprints should show generation spikes)

**Caveats**: Keyword heuristic is coarse; 35% ambiguous; single-author commit style bias.

**Supports articles**: A2 (Compositional Completeness), A6 (The Acceleration)

---

### EX-6.2: GI Balance vs Quality (NEXT PRIORITY)

**Hypothesis**: H-1.2 — Systems built with balanced GI ratios produce higher-quality
outputs than those with imbalanced ratios.

**Data source**: CognOS workload sprints with quality assessments

**Protocol**:
1. Segment Git history into workload sprints (known date ranges)
2. Compute per-sprint GI ratio from commit classification
3. Assess output quality per sprint (workload operational success, # bugs, coherence)
4. Correlate GI balance with quality metrics

**Measurements**:
- Per-sprint GI ratio (from EX-6.3 infrastructure)
- Sprint output quality score (manual assessment + automated metrics)
- Spearman correlation: |log₂(GI ratio)| vs quality
- Scatter plot with trend line

**Expected result**: Sprints closer to GI balance (ratio ~1.0) should correlate
with higher quality. P1 (hardening, I-heavy) should show high quality through
integration. P4 (workloads, mixed) should show quality variation.

**Difficulty**: Medium — requires quality assessment rubric and manual scoring.

**Supports articles**: A4 (Cost of Being Wrong Slowly), A6 (The Acceleration)

---

### EX-3.1: Evidence Ordering Effects

**Hypothesis**: H-3 — The order in which workloads were built affects compounding returns
(earlier workloads deposit primitives that later workloads inherit).

**Data source**: CognOS Git history + workload bundle analysis

**Protocol**:
1. Extract per-sprint CRD kinds (which kinds each workload introduced)
2. Compute kind inheritance: which kinds were reused vs. newly created
3. Monte Carlo: shuffle build order 1000×, compare inheritance curves
4. Compare actual ordering vs random baseline

**Measurements**:
- Inheritance ratio per sprint (inherited/total kinds)
- Cumulative inheritance curve (actual vs shuffled mean ± std)
- Acceleration index: ratio of actual compounding to random baseline

**Expected result**: Actual build order should show higher early inheritance
than random shuffles, confirming that sprint ordering was deliberate.

**Difficulty**: Medium — requires sprint segmentation and Monte Carlo simulation.

**Supports articles**: A3 (Shape of Knowing)

---

### EX-6.7: Cooperative Antagonism (Run 1 Complete)

**Hypothesis**: H-4 — Multi-agent cooperative antagonism (challenger + synthesizer)
produces higher quality output than single-agent approaches.

**Data source**: CognOS workload execution artifacts

**Run 1 results** (Apr 3, 2026):
- Topic: Semiconductor supply chain analysis
- Duration: 4m 30s, 18,494 tokens
- Quality: 6.7 → 8.2 (23% improvement)
- Breadth: doubled 63 → 126 concepts
- No mode collapse detected
- Limitation: no tool invocation

**Run 2 needed**: With tool integration (web search, memory) to test whether
tool access amplifies or dampens the cooperative antagonism effect.

**Difficulty**: Medium — infrastructure exists, needs workload re-run with tools.

**Supports articles**: A7, A9

---

### EX-2: Hierarchical Retrieval Quality

**Hypothesis**: H-6 — Agents with hierarchical memory (knowledge mesh) retrieve
more relevant context than flat retrieval.

**Protocol**:
1. Create knowledge corpus with known hierarchy
2. Query with flat retrieval vs. hierarchical retrieval
3. Measure precision, recall, and relevance at k
4. Compare retrieval paths (direct hit vs. hierarchical traversal)

**Difficulty**: Medium — requires knowledge mesh setup and evaluation rubric.

**Supports articles**: A3 (Shape of Knowing)

---

### EX-5: Workload Re-runs (Evidence Through Time)

**Hypothesis**: H-3 — Platform evolution over 15-22 weeks produces measurable
quality improvements in workload re-runs without workload YAML changes.

**Protocol**:
1. Re-run Agentic Horizons (built Feb 23-28) after ~4 months of platform evolution
2. Compare output quality, coherence, and execution metrics with original run
3. Quantify improvement attributable to platform vs. model upgrades

**Target timing**: July 2026 (22 weeks post-construction)

**Difficulty**: Medium — requires operational re-run infrastructure.

**Supports articles**: A7, A8

---

### EX-6.4: Cross-Domain Falsification

**Hypothesis**: H-2, H-8 — The compositional completeness claim must survive
application to non-CognOS systems. If another platform achieves similar coverage
with fewer primitives, our claim needs revision.

**Protocol**:
1. Map CRD vocabulary equivalents in 3+ competing systems (LangChain, CrewAI, AutoGen)
2. Analyze activation patterns in their example/demo applications
3. Compare coverage ratios and saturation curves
4. Identify concepts where CognOS has more/fewer primitives

**Difficulty**: Hard — requires deep understanding of competing frameworks.

**Supports articles**: A5 (Integration Window), A10 (Ouroboros)

---

### EX-4: Agent-as-Architect

**Hypothesis**: H-6, H-7 — AI agents with access to the full CRD vocabulary
can compose novel workloads, demonstrating system-level intelligence.

**Protocol**:
1. Give an agent the CRD vocabulary + workload examples
2. Ask it to compose a new domain workload (e.g., medical diagnosis)
3. Validate the composed workload executes correctly
4. Measure vocabulary coverage and compare to human-designed workloads

**Difficulty**: Hard — requires reliable agent execution and evaluation.

**Supports articles**: A8

---

### EX-6.6: Optimal Integration Frequency

**Hypothesis**: H-1.4 — There exists an optimal integration interval for
maximizing system coherence.

**Protocol**:
1. Train multiple agents with varying integration intervals
2. Measure output quality as a function of integration frequency
3. Fit a curve to find the quality-maximizing frequency
4. Test whether the optimal point is robust across domains

**Difficulty**: Hard — requires controlled experiments with multiple configurations.

**Supports articles**: A6 (The Acceleration), A10 (Ouroboros)

---

## Article Support Matrix

Which experiments provide evidence for which articles:

| Article | Title | Primary Experiments | Secondary |
|---------|-------|-------------------|-----------|
| A1 | First Principles (published) | — | — |
| A2 | Compositional Completeness | **EX-1** | EX-6.3 |
| A3 | Shape of Knowing | EX-3.1, EX-2 | EX-1 |
| A4 | Cost of Being Wrong Slowly | **EX-6.2** | EX-6.3 |
| A5 | Integration Window | EX-1, EX-6.4 | EX-3.1 |
| A6 | The Acceleration | EX-6.3, **EX-6.6** | EX-6.2 |
| A7 | [Contingency showcase] | EX-6.7, EX-5 | — |
| A8 | [Deep theory] | EX-4, EX-5 | — |
| A9 | [Convergence] | EX-6.7 | EX-6.4 |
| A10 | The Ouroboros Code | EX-6.4, EX-6.6 | All |

## Reproducibility Protocol

Every experiment follows this protocol for GitHub reproducibility:

1. **Environment**: `pyproject.toml` pins all dependencies with minimum versions
2. **Data**: Input paths are configurable (point to any CognOS repo clone)
3. **Execution**: `python -m experiments.<name>.run [args]` from repo root
4. **Output**: JSON results with full provenance (timestamp, git SHA, parameters)
5. **Tests**: Unit tests validate measurement functions with synthetic data
6. **Documentation**: Each experiment has a README with hypothesis, protocol, expected results

### Running all experiments:

```bash
# Clone the repos
git clone https://github.com/CriticalInsight/experiments.git
git clone https://github.com/CriticalInsight/CognOS.git  # or use existing

# Set up environment
cd experiments
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run experiments
python -m experiments.ex1_compositional_coverage.run --cognos-root ../CognOS
python -m experiments.ex6_3_git_gi_analysis.run --repo ../CognOS
```

## Measurement Library Quick Reference

The `cognos_measure` library provides reusable measurement functions:

| Module | Functions | Domain |
|--------|-----------|--------|
| `composition` | `activation_census`, `jaccard_similarity`, `pairwise_jaccard`, `cumulative_saturation`, `fit_saturation_curve`, `kind_classification` | Compositional completeness |
| `compression` | `specification_sparsity`, `code_activation_ratio`, `compression_stack`, `cognitive_load_estimate` | Cognitive compression |
| `gi` | `classify_commit_message`, `gi_ratio`, `windowed_gi`, `gi_rhythm_score` | Generation-Integration dynamics |
| `temporal` | `commit_velocity`, `sprint_analysis`, `integration_window_score` | Temporal coherence |
| `schemas` | `Measurement`, `ExperimentResult`, `EvidenceChain` | Data structures |
| `io` | `load_yaml`, `find_yaml_files`, `extract_crd_kinds`, `iter_git_log` | Data loading |
