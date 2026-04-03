# EX-6.2: GI Balance vs Quality

## Hypothesis

**H-1.2**: Systems built with balanced GI ratios produce higher-quality
outputs than those with imbalanced ratios.

## Protocol

1. Segment CognOS Git history into known development phases and workload sprints
2. Compute per-segment GI ratio and quality proxy metrics
3. Correlate GI balance (|log2(G/I)|) with quality proxies
4. Test correlation via Spearman's rho

## Quality Proxies

Since we lack ground-truth quality scores, we use commit-derived proxies:
- **Fix density**: fraction of fix/bug commits (lower = better quality)
- **Test density**: fraction of test-related commits (higher = better)
- **Doc density**: fraction of documentation commits (higher = maturer)
- **GI balance distance**: |log2(G/I)| — distance from perfect balance

These combine into a composite quality score (0-10 scale).

## Expected Results

- Sprints closer to GI balance (ratio ~1.0) should have lower fix density
- P1 (Hardening) should show high quality through integration effort
- Workload sprints should show varied quality tracking their GI dynamics

## Data Source

CognOS Git repository: `C:\Source\CriticalInsight\Cognos`

## Usage

```bash
python -m experiments.ex6_2_gi_quality.run --repo C:\Source\CriticalInsight\Cognos
```
