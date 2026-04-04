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

## Results

### Latest Run (2026-04-03, Layer 3 ensemble classifier)

| Metric | L4 (keyword-only) | L3 (ensemble) | Delta |
|--------|-------------------|---------------|-------|
| Generation | 919 (35%) | 1909 (73%) | +990 |
| Integration | 781 (30%) | 690 (26%) | -91 |
| Ambiguous | 914 (35%) | 15 (0.6%) | -899 |
| GI ratio | 0.37 (I-heavy) | 2.77 (G-heavy) | flip |
| Rhythm score | — | 0.16 | weak |

### Interpretation: The GI Ratio Flip

The Layer 4 keyword classifier produced a misleading picture: with 35%
ambiguity, the remaining classified commits skewed integration-heavy
(0.37 ratio). The Layer 3 ensemble resolved nearly all ambiguity (0.6%
remaining) by examining *what commits actually changed*:

**Why ambiguous commits were mostly generation**: The 899 formerly-ambiguous
commits were overwhelmingly file additions with high insertion-to-deletion
ratios — the structural and content-flow signals both pointed to generation.
Their messages simply lacked generation keywords (e.g., commit messages like
"update config" or "add files" that don't contain "create" or "implement").

**What this means for the GI thesis**: CognOS is in a sustained generative
phase. The 73% G / 26% I ratio reflects a young platform aggressively
creating new capabilities. This is consistent with:
- 164 CRD kinds across 6 API groups (massive surface area)
- 6 workloads built in 3-11 days each (rapid feature generation)
- 12.6 commits/day sustained (high throughput)

**Why rhythm is weak (0.16)**: Phase lock into generation mode. The project
rarely alternates to sustained integration-dominant periods at the weekly
window level. Even "integration" phases (Hardening, Release prep) contain
substantial file additions. This is expected for a platform in rapid growth —
the article series predicts that healthy systems need integration phases, and
CognOS's strong generation bias may explain accretion of technical debt noted
in retrospectives.

**Implications for Article 10 ("The Circuit")**: The GI circuit thesis
predicts that sustained generation-dominance is a risk factor ("divergence
without convergence"). However, the EX-6.2 quality data (quality highest in
Hardening phase, which has the most integration) provides indirect evidence
that integration *does* correlate with quality — we just don't have enough
integration-dominant periods to prove it statistically.

**Key insight**: The ratio flip itself is article-worthy evidence. It
demonstrates that measurement method matters enormously — Layer 4 keywords
encoded an integration bias (refactor, test, fix are all common commit
prefixes) that masked the underlying generation reality. This echoes the
article series' own thesis: structural analysis reveals patterns that
surface-level signals miss.

## Supports

- **Article 5** (Integration Window): The temporal coherence claim IS a GI-rate claim
- **Article 10** (The Circuit): Cross-domain GI evidence from the project's own history
- **H-5**: Flywheel exhibits balanced GI rhythm
