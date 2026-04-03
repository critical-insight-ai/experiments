# CriticalInsight Experiments

Reproducible experiments supporting the [CriticalInsights "Overspecified" article series](https://open.substack.com/pub/criticalinsights) and the book project on intelligence, integration, and the Generation-Integration duality.

## Quick Start

```bash
# Install the measurement library + dependencies
pip install -e ".[dev]"

# Run a specific experiment
python -m experiments.ex1_compositional_coverage.run
python -m experiments.ex6_3_git_gi_analysis.run --repo /path/to/cognos

# Run all experiments
python -m pytest tests/ -v
```

## Structure

```
experiments/               # Top-level package
├── cognos_measure/        # Core measurement library (pip-installable)
│   ├── gi.py              # Generation-Integration metrics (GI ratio, balance, rhythm)
│   ├── compression.py     # Compression ratio, specification sparsity, activation census
│   ├── composition.py     # Compositional coverage, Jaccard similarity, saturation curves
│   ├── temporal.py        # Temporal coherence, integration window, velocity analysis
│   ├── schemas.py         # Data schemas (Experiment, Result, EvidenceChain)
│   └── io.py              # YAML/JSON loaders, CRD parsers, Git log readers
├── experiments/
│   ├── ex1_compositional_coverage/   # H-2: CRD vocabulary coverage analysis
│   ├── ex6_3_git_gi_analysis/        # H-5, H-1.3: GI rhythm in Git history
│   ├── ex6_2_gi_balance_quality/     # H-1.2: GI balance predicts output quality
│   └── ...
├── data/                  # Seed data, expected results, reference datasets
├── results/               # Experiment outputs (git-tracked for reproducibility)
├── tests/                 # Unit tests for cognos_measure
├── pyproject.toml
└── README.md
```

## Experiment Index

| ID | Hypothesis | Article | Difficulty | Status |
|----|-----------|---------|------------|--------|
| EX-1 | H-2: Compositional completeness — finite vocabulary covers domain | 2 | Easy | ✅ Data ready |
| EX-6.3 | H-5, H-1.3: Flywheel GI rhythm measurable in Git history | 5, 10 | Easy | ✅ Data ready |
| EX-6.2 | H-1.2: GI balance (R≈1) predicts higher quality | 10 | Medium | Designed |
| EX-3.1 | H-2d: Evidence ordering affects agent conclusions | 5 | Medium | Designed |
| EX-6.7 | H-4: Cooperative antagonism converges without mode collapse | 7, 9 | Medium | Run 1 complete |
| EX-5.1 | H-3: Workload re-run shows compounding returns | 6, 7 | Medium | Planned |
| EX-6.6 | H-1.4: Optimal integration frequency exists | 5 | Hard | Designed |
| EX-6.4 | H-1.1: GI duality holds across ≥5/8 domains | 10 | Hard | Designed |

## The `cognos_measure` Library

A Python package for measuring aspects of intelligence in cognitive systems:

- **GI metrics**: Generation rate G(t), Integration rate I(t), GI ratio R(t), balance score, rhythm detection
- **Compression metrics**: Specification sparsity ratio, code activation ratio, cognitive load estimates
- **Composition metrics**: CRD activation census, Jaccard similarity, coverage saturation curves, power-law fits
- **Temporal metrics**: Integration window duration, velocity analysis, coherence scoring, commit cadence

All metrics produce structured results with provenance metadata for evidence chains.

## Reproducibility

Each experiment directory contains:
- `run.py` — executable entry point
- `data/` — seed data and input files
- `expected/` — expected results from CognOS runs
- `results/` — actual outputs (git-tracked)
- `README.md` — hypothesis, protocol, interpretation guide

## License

MIT
