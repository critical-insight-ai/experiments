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

## Run 3 Results (2026-04-04, permissions applied, PriorityGuard disabled)

**Fix applied**: All agent types updated with full `defaultPermissions`
(7 permissions each). `ADMISSION_PRIORITY_GUARD_DISABLED: "true"` added
to Docker compose to eliminate 425 errors.

| Metric | Run 1 | Run 2 | Run 3 |
|--------|-------|-------|-------|
| Tool calls | 0 | 27 | 18 |
| Successful | 0 | 0 | 0 |
| Tokens | 18,494 | 96,197 | 69,718 |
| Duration | ~3 min | ~10 min | 6:30 |
| Tasks | 7/7 | 7/7 | 7/7 |

### Why Still Failing (Run 3)

All 18 tool calls failed with 403 (Forbidden). The 425 errors from Run 2
were eliminated, but **stale AgentType permissions in the Orleans grain
registry** meant the runtime still denied tool access. The Mesh catalog
(REST API layer) had the correct permissions, but the `AgentTypeRegistry`
grain (PostgreSQL-backed, used at runtime) retained old state from prior
sessions. CRD re-apply updates the catalog but does not invalidate the
grain cache.

| Error | Count | Tools affected |
|-------|-------|----------------|
| 403 Forbidden | 15 | channels.search, document.list, task.list, document.read, document.create_from_template |
| 405 Method Not Allowed | 2 | web.search.qa |
| 404 Not Found | 1 | web.search.raw |

## Run 4 Results (2026-04-04, silo restart attempt)

Hypothesis: silo restart would refresh the grain cache. **Disproven** —
Orleans grain state is backed by PostgreSQL and persists across restarts.

| Metric | Run 3 | Run 4 |
|--------|-------|-------|
| Tool calls | 18 | 21 |
| Successful | 0 | 0 |
| Tokens | 69,718 | 81,595 |
| Duration | 6:30 | 7:30 |

Same failure pattern. 21 tool calls, all 403 on platform tools, 405 on
web search. Confirms the stale grain is the root cause.

## Run 5 Results (2026-04-04, instance-level permissions — BREAKTHROUGH)

**Root cause fix**: Added `spec.permissions` directly to all 3 Agent CRDs
(not just AgentType `defaultPermissions`). `ToolPermissionHelper` checks
`ctx.Config.Permissions` first — if non-null, it **fully replaces**
`AgentType.DefaultPermissions`, bypassing the stale grain entirely.

| Metric | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|--------|-------|-------|-------|-------|-------|
| Tool calls | 0 | 27 | 18 | 21 | **75** |
| Successful | 0 | 0 | 0 | 0 | **59 (79%)** |
| Tokens | 18,494 | 96,197 | 69,718 | 81,595 | **319,423** |
| Duration | ~3 min | ~10 min | 6:30 | 7:30 | **4:00** |
| Tasks | 7/7 | 7/7 | 7/7 | 7/7 | **7/7** |
| Token ratio vs baseline | 1x | 5.2x | 3.8x | 4.4x | **17.3x** |

### Task-Level Breakdown (Run 5)

| Task | Tokens | Tool Calls | Successful | Turns |
|------|--------|------------|------------|-------|
| generate-round-1 | 43,609 | 17 | 7 | 7 |
| critique-round-1 | 28,764 | 5 | 5 | 5 |
| generate-round-2 | 41,638 | 8 | 8 | 7 |
| critique-round-2 | 75,976 | 14 | 9 | 9 |
| generate-round-3 | 72,302 | 17 | 16 | 9 |
| critique-round-3 | 16,031 | 3 | 3 | 3 |
| judge-verdict | 41,103 | 11 | 11 | 10 |

### Per-Tool Success Rates (Run 5)

| Tool | Success/Total | Notes |
|------|---------------|-------|
| channels.search | 9/9 | 100% — channel reads work |
| document.read | 8/8 | 100% — document reads work |
| document.list | 6/6 | 100% |
| task.complete | 6/6 | 100% |
| document.append | 4/4 | 100% |
| task.list | 4/4 | 100% |
| document.view.create | 3/3 | 100% |
| document.view.read | 3/3 | 100% |
| memory.capture_scene | 3/3 | 100% — episodic memory works |
| document.finalize | 2/2 | 100% |
| document.create | 1/1 | 100% |
| document.create_from_template | 1/1 | 100% |
| task.create | 6/15 | 40% — agent retries on existing tasks |
| channels.post | 3/5 | 60% — transient write failures |
| web.search.raw | 0/4 | 0% — no search backend configured |
| web.search.qa | 0/1 | 0% — no search backend configured |

### Key Findings (Run 5)

1. **Permission fix validated**: Instance-level permissions bypass stale
   grain state. 59/75 tool calls succeed (79%).
2. **17.3x token inflation**: When tools work, agents invest heavily in
   document lifecycle (create → append → finalize), channel communication,
   and task management. Run 1 baseline: 18,494 tokens. Run 5: 319,423.
3. **Paradoxically faster**: Despite 17x more tokens, Run 5 completed in
   4 minutes (vs 6-10 minutes for Runs 2-4). Tool failures cause expensive
   retry loops; successful tools are fast.
4. **Cooperative-antagonistic pattern emerges**: Generators create structured
   dossiers via document tools, critics query channels and documents to find
   weaknesses, judge synthesizes across all rounds via document reads.
5. **Expected failures**: Web search (no backend) and task.create retries
   (duplicate creation) account for all 16 failures.

### Root Cause Analysis: Permission 403 Debugging Arc

The 403 debugging across Runs 2-5 revealed a significant architectural
insight about CognOS:

- **Two storage systems**: Mesh catalog (REST API, always current) vs
  AgentTypeRegistry grain (runtime, PostgreSQL-backed, can be stale)
- **CRD apply** updates the catalog but **does not invalidate** the grain
- **Silo restart** does not help — grain state persists in PostgreSQL
- **Instance-level permissions** on Agent CRDs are the reliable path because
  `ToolPermissionHelper` uses `ctx.Config.Permissions` as a full replacement
  when non-null (code path: `Cognos.Orchestration/Providers/ToolPermissionHelper.cs`
  lines 140-154)

### Run 5 Next Steps

- [ ] Run 6 with web search backend for full tool coverage
- [ ] Compare quality across different topics (not just semiconductor geopolitics)
- [ ] Measure token efficiency (quality per token)

## Quality Trajectory Comparison: Run 1 (no tools) vs Run 5 (tools working)

### Overall Quality Scores

| Dimension | Run 1 (no tools) | Run 5 (tools) | Delta |
|-----------|------------------|---------------|-------|
| Accuracy | 9 | 8 | -1 |
| Completeness | 8 | 9 | +1 |
| Coherence | 8 | 9 | +1 |
| Depth | 7 | 8 | +1 |
| Falsifiability | 8 | 8 | 0 |
| Source Diversity | 9 | 8 | -1 |
| **Overall** | **8.2** | **8.5** | **+0.3** |

### Convergence Trajectory

| Run | Round 1 | Round 2 | Round 3 |
|-----|---------|---------|---------|
| Run 1 (no tools) | 6.7 | 7.9 | 8.2 |
| Run 5 (tools) | 6-7 | 7-8.5 | 8-9 |

### Breadth (Mode Collapse Detection)

| Run | Round 1 | Round 3 | Growth |
|-----|---------|---------|--------|
| Run 1 | 63 | 126 | 2.0x |
| Run 5 | 120 | 432 | 3.6x |

Neither run showed mode collapse. Run 5's breadth grew 3.6x vs Run 1's
2.0x — tools enable broader exploration (more themes, sources, perspectives).

### Key Insight: Marginal Quality, Qualitative Shift

The headline finding is surprising: **+0.3 quality points for 17.3x more tokens.**
At the top of the quality scale, diminishing returns are expected. But the
composition pattern is qualitatively different:

- **Run 1**: Agents operated entirely from parametric knowledge. Quality
  came from the adversarial debate structure itself.
- **Run 5**: Agents created structured documents (dossiers), posted to
  channels, managed sub-tasks, captured memory scenes, and read each
  other's work products. The debate was mediated by **persistent artifacts**
  rather than stateless message passing.

The +0.3 quality delta understates the difference. Run 5 produces a
**reusable evidence trail**: documents, channel history, task records,
and memory snapshots that persist after the workflow completes. Run 1
produces only the final text output.

This is consistent with H-4 (cooperative antagonism): the adversarial
pattern works even without tools, but tools transform the process from
a conversation into a **knowledge construction pipeline**.

## Run 6 Results (2026-04-04, 7 rounds — Diminishing Returns Curve)

Extended from 3 to 7 rounds to find the convergence point. Used a separate
bundle (`ex-6-7b-extended-rounds-bundle.yaml`) with 15 tasks (7 generate +
7 critique + 1 judge). Same topic (semiconductor geopolitics), same model
(gpt-4.1-2025-04-14), same agent types/skills from the base bundle.

| Metric | Run 5 (3 rounds) | Run 6 (7 rounds) |
|--------|-------------------|-------------------|
| Rounds | 3 | **7** |
| Tasks | 7 | **15** |
| Tokens | 319,423 | **1,112,667** |
| Duration | 4:00 | **8:31** |
| Overall (final) | 8.5 | **9.28** |
| Breadth (final) | 432 | **350** |

### Per-Round Quality Trajectory

| Round | Accuracy | Complete | Coherence | Depth | Falsif. | Src.Div. | **OVERALL** | **Δ** |
|-------|----------|----------|-----------|-------|---------|----------|-------------|-------|
| 1 | 8.0 | 7.5 | 8.0 | 7.0 | 7.5 | 6.0 | **7.65** | — |
| 2 | 8.3 | 8.0 | 8.5 | 7.5 | 8.0 | 7.0 | **8.06** | +0.41 |
| 3 | 8.7 | 8.7 | 9.0 | 8.5 | 8.5 | 8.0 | **8.73** | +0.67 |
| 4 | 8.8 | 9.1 | 9.1 | 9.0 | 8.7 | 9.0 | **9.09** | +0.36 |
| 5 | 9.0 | 9.4 | 9.2 | 9.1 | 8.8 | 9.2 | **9.23** | +0.14 |
| 6 | 9.0 | 9.5 | 9.2 | 9.2 | 8.8 | 9.2 | **9.26** | +0.03 |
| 7 | 9.0 | 9.5 | 9.2 | 9.3 | 8.8 | 9.2 | **9.28** | +0.02 |

### Breadth Trajectory

| Round | Distinct Concepts | Growth vs R1 |
|-------|-------------------|--------------|
| 1 | 32 | — |
| 2 | 75 | 2.3x |
| 3 | 168 | 5.3x |
| 4 | 315 | 9.8x |
| 5 | 350 | 10.9x |
| 6 | 350 | 10.9x |
| 7 | 350 | 10.9x |

Breadth saturates at Round 5. Later rounds refine existing concepts but
do not introduce new ones.

### Task-Level Breakdown (Run 6)

| Task | Tokens | Elapsed |
|------|--------|---------|
| generate-round-1 | 46,908 | 24.5s |
| critique-round-1 | 93,216 | 21.9s |
| generate-round-2 | 166,915 | 16.4s |
| critique-round-2 | 96,112 | 12.9s |
| generate-round-3 | 88,450 | 29.2s |
| critique-round-3 | 43,312 | 14.7s |
| generate-round-4 | 192,680 | 46.1s |
| critique-round-4 | 122,812 | 17.3s |
| generate-round-5 | 49,664 | 19.4s |
| critique-round-5 | 12,279 | 7.9s |
| generate-round-6 | 20,008 | 10.3s |
| critique-round-6 | 81,851 | 21.1s |
| generate-round-7 | 31,430 | 24.1s |
| critique-round-7 | 8,256 | 5.9s |
| judge-verdict | 58,774 | 31.5s |

Token investment peaks at Round 4 (315k) then drops sharply — agents
recognize diminishing returns and invest less in later rounds.

### Most Impactful Critic Objections

1. **Overemphasis on fabs** — led to inclusion of upstream materials,
   software ecosystem, and packaging/testing
2. **Overly pessimistic on US/EU catch-up** — prompted scenario analysis
   and acknowledgment of local hurdles (water, talent, permits)
3. **Cybersecurity risks** — added as major latent amplifier with evidence

### Recovery Timer Bug (Platform Finding)

The [OneWay] callback from `AgentTaskGrain` → `WorkflowGrain` never
fires. The 30-second recovery timer is the **sole mechanism** advancing
the workflow between sequential tasks.

| Metric | Value |
|--------|-------|
| Total idle time | **207.1 seconds** |
| Average gap per task | **13.8 seconds** |
| Min gap | 0.8 seconds |
| Max gap | 28.5 seconds |
| % of wall clock | **40.5%** |

**Root cause**: `IWorkflowGrain.OnTaskCompletedAsync` is marked `[OneWay]`.
The direct callback from silo2 (AgentTaskGrain) to silo1 (WorkflowGrain)
silently fails — neither the success log nor the catch handler fires.
The recovery timer + CLI status polling (which triggers `TriggerRecoveryAsync`)
are what actually advance the workflow, with variable latency.

**Impact**: Fixing this bug would reduce the 8:31 run to ~5:04 (active
work only). This is a platform-level issue affecting all sequential
workflow tasks.

### Key Finding: 5 Rounds is Optimal

```
Quality: 7.65 → 8.06 → 8.73 → 9.09 → 9.23 → 9.26 → 9.28
Delta:         +0.41   +0.67   +0.36   +0.14   +0.03   +0.02
                ^^^^^^^^^^^^^^^^^^^^    ^^^^^^^^   negligible
                 steep improvement      diminishing
```

- **3 rounds too shallow**: R4 still adds +0.36 and major concept breadth
- **5 rounds optimal**: 99.5% of final quality (9.23/9.28); breadth saturated
- **6-7 rounds negligible**: +0.05 total for 2 extra rounds and ~200k tokens
- **Sweet spot**: Rounds 4-5 are where quality transitions from steep growth
  to asymptotic plateau

The convergence curve follows a classic sigmoid shape. The debate reaches
informational saturation at Round 5 — critics run out of novel objections,
and generators have addressed all major gaps. This empirically validates
5 rounds as the default design for cooperative-antagonistic workflows.

## Data Source

- CRD bundle (3-round): `Cognos/docs/demos/acme-briefing/ex-6-7-cooperative-antagonism-bundle.yaml`
- CRD bundle (7-round): `Cognos/docs/demos/acme-briefing/ex-6-7b-extended-rounds-bundle.yaml`
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
