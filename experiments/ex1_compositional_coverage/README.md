# EX-1: Compositional Coverage Measurement

**Hypothesis (H-2)**: CognOS's 164 CRD kinds form a compositionally complete vocabulary — a finite typed vocabulary with composition rules that covers an unbounded application space.

**Evidence level**: Observational (systematic measurement, no manipulation)

## What this measures

1. **Per-workload activation**: How many CRD kinds does each workload use?
2. **Union coverage**: What fraction of the 164 kinds have been activated across all workloads?
3. **Frequency distribution**: Power-law? Which kinds are universal vs. domain-specific?
4. **Saturation curve**: Does cumulative coverage follow a logarithmic trajectory (hallmark of compositional completeness)?
5. **Pairwise Jaccard similarity**: How much vocabulary overlap exists between workload pairs?

## Running

```bash
python -m experiments.ex1_compositional_coverage.run
```

## Expected results (from prior EX-1 runs)

- 65/164 kinds activated (39.6% coverage)
- 2 universal kinds (Process, Workflow) — present in all workloads
- Power-law distribution: few high-frequency kinds, long tail of domain-specific
- Logarithmic saturation: first 4 workloads captured 91% of activated kinds
- Highest Jaccard: DIANA ↔ Resale (0.789)

## Data source

Workload CRD kind inventories extracted from YAML bundles at `C:\Source\CriticalInsight\Cognos\`.
