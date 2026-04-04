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

### Run 1 Root Cause: Zero Tool Calls

The bundle had two defects that prevented all tool invocation:

1. **Wrong field name**: AgentType used `tools:` (flat string list) instead of
   `defaultTools:` (list of `{toolId}` objects). The platform ignores `tools:`.
2. **Wrong tool IDs**: `web.search` and `web.browse` are not registered tools.
   Correct IDs: `web.search.qa`, `web.search.raw`, `web.fetch`,
   `web.browse.scroll`, `web.browse.links`.
3. **Missing permissions**: `defaultPermissions.permissions` was absent
   (agents need `data:access` + `data:read` for web/document tools).

The LLM received task prompts referencing tools but the orchestration engine
had no tools to offer. The model simulated the adversarial pattern entirely
from internal reasoning — still achieving Q 8.2, but without actual web
research, document creation, or channel communication.

**Fix applied**: Bundle updated to use `defaultTools` with correct specific
tool IDs and `defaultPermissions` block. Skills' `toolIds` also corrected.

## Run 2 Results (2026-04-04, tools enabled, infrastructure missing)

**Bundle fix validated.** The corrected bundle enabled tool invocation:
agents attempted 27 tool calls across 7 tasks (vs 0 in Run 1).

| Metric | Run 1 | Run 2 | Delta |
|--------|-------|-------|-------|
| Tool calls | 0 | 27 | +27 |
| Tokens | 18,494 | 96,197 | 5.2x |
| Tasks completed | 7/7 | 7/7 | — |
| Quality trajectory | 6.7→7.9→8.2 | Not scored | Judge lacked permissions |
| Mode collapse | None | Not assessed | — |

### Task-Level Breakdown (Run 2)

| Task | Tokens | Tool Calls | Turns | Elapsed |
|------|--------|------------|-------|---------|
| generate-round-1 | 23,050 | 6 | 5 | 1:08 |
| critique-round-1 | 8,585 | 2 | 2 | 0:36 |
| generate-round-2 | 13,963 | 6 | 3 | 1:47 |
| critique-round-2 | 17,087 | 3 | 4 | 0:52 |
| generate-round-3 | 12,115 | 2 | 3 | 0:36 |
| critique-round-3 | 8,734 | 2 | 2 | 0:37 |
| judge-verdict | 12,663 | 6 | 3 | 1:40 |

### Why All 27 Tool Calls Failed

The agents tried the right tools but the Docker cluster infrastructure
wasn't ready:

| Error | Count | Cause |
|-------|-------|-------|
| 425 (Too Early) | 16 | Tools infrastructure not initialized |
| 403 (Forbidden) | 8 | Permission denied at service level |
| 405 (Method Not Allowed) | 2 | Web search MCP not configured |
| 404 (Not Found) | 1 | Search endpoint missing |

Tools attempted: `document.create_from_template`, `document.create`,
`document.read`, `document.list`, `channels.search`, `task.list`,
`web.search.qa`, `web.search.raw`

### 4th Bundle Defect Found

The `gi-judge` agent type lacks `structured-documents:read` permission.
The judge couldn't read the experiment dossier or channel history,
so it couldn't produce quality scores.

### Key Findings

1. **Bundle fix confirmed**: 27 tool calls (vs 0) proves the three Run 1
   defects were correctly diagnosed and fixed
2. **Graceful degradation**: All tasks completed despite 100% tool failure —
   agents fell back to parametric generation
3. **Token inflation**: Tool retry turns consume 5.2x more tokens
4. **Agent role fidelity**: Generator used `document.create`, `web.search`;
   Critic used `document.list`, `channels.search`; Judge used all three
   categories — agents follow their playbook instructions

### Run 3 Plan (with working infrastructure)

- [ ] Fix gi-judge permissions (`structured-documents:read`)
- [ ] Configure web search MCP endpoint in Docker
- [ ] Resolve 425 tool initialization errors (possibly needs warm-up)
- [ ] Re-run same topic for controlled comparison
- [ ] Success criteria: tool calls > 0 **and** tool calls successful > 0

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
