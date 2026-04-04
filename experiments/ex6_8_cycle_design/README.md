# EX-6.8: Cycle Design Variations

Tests **H-4.1**: how cycle design characteristics affect convergence dynamics, quality ceilings, and efficiency in multi-agent adversarial refinement.

## Phase 1 Experiments

| ID | Name | Varied Dimension | Rounds | Key Change |
|----|------|-------------------|--------|------------|
| EX-6.8.4 | Phased Roles | Role specialization | 5 | Breadth→Depth→Polish phase prompts |
| EX-6.8.10 | Selective Attention | Context window | 5 | Generator reads only most recent critique |
| EX-6.8.5 | Multi-Critic Panel | Critique topology | 3 | 3 parallel specialized critics (ACC/COH/SCP) |
| EX-6.8.1 | Compressed Context | Context window | 5 | Summarizer compresses context between rounds |

**Baseline**: EX-6.7b Run 6 — 5-round uniform prompts, quality 9.23, breadth 350.

## Two Runners

### 1. CognOS CLI Runner (`run.py`)

Requires a running CognOS cluster. Applies YAML bundles, starts workflows, downloads and parses outputs.

```bash
# Parse existing outputs
python -m experiments.ex6_8_cycle_design.run \
    --experiment 6.8.4 --parse-only --output-dir ./outputs

# Full run
python -m experiments.ex6_8_cycle_design.run \
    --experiment 6.8.4 \
    --server http://localhost:8080 --tenant acme --token <token>

# All Phase 1
python -m experiments.ex6_8_cycle_design.run \
    --all --server http://localhost:8080 --tenant acme --token <token>
```

### 2. Pure Python/OpenAI Runner (`openai_runner.py`)

**No CognOS dependency.** Reproduces the experiments using only the OpenAI API. Designed for data scientists, AI engineers, and NLP practitioners to reproduce results independently.

```bash
# Set your API key
export OPENAI_API_KEY=sk-...

# Run a single experiment
python -m experiments.ex6_8_cycle_design.openai_runner --experiment 6.8.4

# Use a different model
python -m experiments.ex6_8_cycle_design.openai_runner --experiment 6.8.5 --model gpt-4o

# Dry run (print prompts, no API calls)
python -m experiments.ex6_8_cycle_design.openai_runner --experiment 6.8.4 --dry-run

# Run all Phase 1
python -m experiments.ex6_8_cycle_design.openai_runner --all
```

### Differences Between Runners

| Feature | CognOS CLI (`run.py`) | OpenAI (`openai_runner.py`) |
|---------|----------------------|----------------------------|
| Dependency | CognOS cluster + CLI | OpenAI API key only |
| Tool access | Agents use web search, document tools, memory | Agents use only LLM + system/user prompts |
| Multi-critic parallelism | True parallelism via DAG workflow | ThreadPoolExecutor parallelism |
| State management | CognOS workspace, channels, documents | Python in-memory lists |
| Cost tracking | CognOS process budgets | Token counting from API responses |
| Output format | Structured documents + channel messages | Markdown files + JSON |

The CognOS runner is the canonical reference (agents have access to web search, document creation, memory). The OpenAI runner is a faithful approximation that captures the essential experimental design (role definitions, topology, context constraints) without the full platform.

## Protocol Definitions (`protocols.py`)

Each experiment is defined as a `CycleProtocol` dataclass:

- **AgentRole**: system prompt + skill prompt + model
- **Round**: phase label, generator prompt, critic roles, topology, optional summarizer
- **CycleProtocol**: full experiment definition (rounds, agents, topic, budget)

Protocols are shared between both runners. Modify `protocols.py` to change experiment designs.

## Measurement

Both runners output:
- Per-round quality scores (6 dimensions + overall)
- Quality trajectory and convergence curve
- Breadth trajectory
- Token usage and cost
- Mode collapse detection
- Experiment-specific analysis (phase transitions, attention effects, panel specialization, compression fidelity)

## File Structure

```
experiments/ex6_8_cycle_design/
├── __init__.py
├── README.md              # This file
├── protocols.py           # Protocol definitions (shared)
├── run.py                 # CognOS CLI runner
├── openai_runner.py       # Pure Python/OpenAI runner
└── results/               # Output data (created by runners)
```

## Corresponding CognOS YAML Bundles

Located in `CognOS/docs/demos/acme-briefing/`:
- `ex-6-8-1-compressed-context-bundle.yaml`
- `ex-6-8-4-phased-roles-bundle.yaml`
- `ex-6-8-5-multi-critic-bundle.yaml`
- `ex-6-8-10-selective-attention-bundle.yaml`

These bundles define the same protocols as `protocols.py` but in CognOS CRD format with full tool access, workspace configuration, and DAG workflow definitions.
