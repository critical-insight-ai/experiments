# EX-6.7: Cooperative Antagonism — Multi-Agent GI Dynamics

## Hypothesis

**H-4**: Structuring agent interaction as cooperative antagonism
(generator vs critic vs judge) produces higher-quality outputs than
unconstrained multi-agent collaboration, with measurable quality
improvement across rounds and no mode collapse.

## Protocol

1. Apply the EX-6.7 CRD bundle (3 agent types, 7-task workflow)
2. Start a workflow run on a given topic
3. Collect per-round outputs: generator proposals, critic challenges, judge verdicts
4. Measure: quality trajectory, topic breadth, mode collapse, tool invocations
5. Compare Run 1 (no tools) vs Run 2 (with tools) vs future runs

## Run 1 Baseline (2026-04-03, no tool invocation)

- **Quality trajectory**: 6.7 → 7.9 → 8.2 (improving)
- **Topic breadth**: 63 → 96 → 126 unique concepts (no mode collapse)
- **Mode collapse**: None detected
- **Tool calls**: 0 (agents operated from prompts only)
- **Topic**: Semiconductor geopolitics

## Run 2 Plan (with tool invocation)

- Same topic (semiconductor geopolitics) for controlled comparison
- Verify tool providers are configured and agents have tool access
- Success criteria: quality ≥ 8.0 final, tool calls > 0, no mode collapse
- Key comparison: does tool access improve quality trajectory or breadth?

## Data Source

- CRD bundle: `Cognos/docs/demos/acme-briefing/ex-6-7-cooperative-antagonism-bundle.yaml`
- Run outputs: `C:\Source\CriticalInsight\CognOS-Workloads-Outputs\ex-6-7-cooperative-antagonism\`

## Usage

```bash
# Automated (requires CognOS cluster running on port 8080):
python -m experiments.ex6_7_cooperative_antagonism.run \
    --server http://localhost:8080 \
    --tenant acme \
    --bundle C:\Source\CriticalInsight\Cognos\docs\demos\acme-briefing\ex-6-7-cooperative-antagonism-bundle.yaml

# Parse existing run outputs:
python -m experiments.ex6_7_cooperative_antagonism.run \
    --parse-only \
    --output-dir C:\Source\CriticalInsight\CognOS-Workloads-Outputs\ex-6-7-cooperative-antagonism\20260403-run1
```
