# EX-6.3: Git History GI Analysis

**Hypothesis (H-5, H-1.3)**: The cognitive flywheel IS a GI circuit. Git commits can be classified as generation (new code, features) or integration (refactoring, docs, tests). The GI rhythm is measurable and its balance correlates with development quality.

**Evidence level**: Observational

## What this measures

1. **Per-commit GI classification**: Each commit classified as Generation, Integration, or Ambiguous using keyword heuristics (Layer 4 — temporal/phase classification)
2. **Weekly GI ratio**: Sliding-window GI balance over the full development history
3. **Phase identification**: G-dominant vs I-dominant periods mapped to known development phases
4. **GI rhythm score**: How well the project alternates between G and I phases (0-1 scale)
5. **Velocity correlation**: Does GI balance predict commit velocity?

## Running

```bash
# Analyze the CognOS repo
python -m experiments.ex6_3_git_gi_analysis.run --repo C:\\Source\\CriticalInsight\\Cognos

# Analyze with date range
python -m experiments.ex6_3_git_gi_analysis.run --repo C:\\Source\\CriticalInsight\\Cognos --since 2025-12-01 --until 2026-04-01
```

## Expected results

- P1-P2 (Hardening/Polish): Integration-heavy (specs, tests, i18n normalization)
- P3 (Release prep): Balanced (Docker infrastructure + hardening)
- P4 (Workload sprints): Generation-heavy (new domains, features), with integration bursts between sprints
- Overall: alternating GI rhythm — generation sprints punctuated by integration consolidation

## Supports

- **Article 5** (Integration Window): The temporal coherence claim IS a GI-rate claim
- **Article 10** (The Circuit): Cross-domain GI evidence from the project's own history
- **H-5**: Flywheel exhibits balanced GI rhythm
