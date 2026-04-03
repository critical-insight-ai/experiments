# EX-3.1: Evidence Ordering — Monte Carlo Compounding Test

## Hypothesis

**H-3**: The order in which CognOS workloads were built matters — earlier
workloads deposit reusable CRD primitives that later workloads inherit.
The actual build order produces more inheritance (compounding) than
random orderings.

## Protocol

1. Load per-workload CRD kinds from YAML bundles (reuses EX-1 infrastructure)
2. Compute inheritance curve for the actual chronological build order
3. Monte Carlo: shuffle build order 10,000 times, compute inheritance each time
4. Compare actual total inheritance vs random distribution
5. Report p-value, effect size (Cohen's d), and per-step comparison

## Expected Results

- Actual ordering should show higher inheritance than random mean
- Effect should be visible from workload 3+ (after primitives accumulate)
- p < 0.05 would indicate deliberate (or fortunate) ordering

## Data Source

CognOS workload YAML bundles (same as EX-1):
`deploy/docker/bundles/demos/`

## Usage

```bash
python -m experiments.ex3_1_evidence_ordering.run --cognos-root C:\Source\CriticalInsight\Cognos
```
