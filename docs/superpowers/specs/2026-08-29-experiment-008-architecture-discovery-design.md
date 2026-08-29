# Experiment 008 — Architecture Discovery

## Purpose

Experiment 008 asks whether three architectural factors improve a fixed local model individually and in combination, and where each factor belongs in the pipeline:

- **Alien Tech** — verified external cognition that can be retrieved on later tasks.
- **VELMA** — governed manager/auditor/repair structure around model proposals.
- **OpenAdapt** — verified compiled-skill execution that can remove model calls on stable repeated work and independently verify declared effects.

The experiment is designed to discover architecture rather than validate a preferred topology. The current V31M4 repository structure is not treated as the search boundary.

## Scientific arms

The primary comparison is a complete 2×2×2 factorial:

1. `MODEL_ONLY`
2. `ALIEN`
3. `VELMA`
4. `OPENADAPT`
5. `VELMA_ALIEN`
6. `ALIEN_OPENADAPT`
7. `VELMA_OPENADAPT`
8. `VELMA_ALIEN_OPENADAPT`

The user's six requested systems are all present; `MODEL_ONLY` and `ALIEN_OPENADAPT` are diagnostic controls required to identify main effects and all pairwise/three-way interactions.

## OpenAdapt scope

The controlled factorial uses a Flow-compatible compiled-skill abstraction inside the deterministic synthetic workstation so every arm can be matched on the same task and oracle. It models:

- compile only from permitted traces;
- deterministic skill replay;
- zero model calls on a healthy matched replay;
- exact → label → structural resolution;
- safe halt on unresolved drift;
- independent effect verification that catches screen-success/backend-failure.

A separate **mandatory real-product gate** runs the installed `openadapt-flow tutorial` and `openadapt-flow tutorial --break-it`. The overnight profile cannot start unless the real product demonstrates both a healthy verified zero-model-call run and the broken-backend false-success halt. This keeps the causal abstraction and actual product evidence distinct.

## Task world

The harness uses a deterministic synthetic workstation with a public surface and a sealed independent oracle. The model sees current locators, stable action semantics, dependency/condition labels, and policy markings; it never sees the required semantic sequence or oracle final state.

Eight task families are used:

- `linear_dependency`
- `conditional_branch`
- `multi_record_join`
- `loop_worklist`
- `policy_guard`
- `composition`
- `drift_resolution`
- `silent_effect_fault`

Difficulty increases required chain depth and distractor count. UI slot/location is randomized independently from required execution order so the model cannot solve tasks by sorting a leaked step number.

## Lifecycle

Matched lineages preserve the same underlying task across stages unless the stage explicitly represents variation:

1. `NOVEL`
2. `REPEAT`
3. `PARAMETER_VARIATION`
4. `DRIFT`
5. `SILENT_EFFECT_FAULT`
6. `COMPOSITION`
7. `REPAIR`
8. `TRANSFER`
9. `LONG_RUN_1`
10. `LONG_RUN_2`
11. `LONG_RUN_3`

`NOVEL` and `REPEAT` share initial state, semantics, and action rules. `DRIFT` changes locators while preserving semantics. Variation/transfer/composition deliberately generate changed task instances.

## Phase 1 — full factorial

Every arm receives matched `NOVEL → REPEAT` cells at four difficulty bands over two seeds and all eight task families.

Default overnight cells: **1,024**.

This phase measures:

- verified success;
- main factor effects;
- A×V, A×O, V×O interactions;
- A×V×O interaction;
- model calls/tokens;
- safe halts;
- silent wrong effects;
- whether repeated work actually changes model dependence.

Factorial analysis uses only complete paired eight-arm blocks. Invalid cells cannot silently alter denominators.

## Phase 2 — layer-location sweeps

All three components are enabled. One location variable changes at a time. Every placement receives the same matched task and its own isolated `NOVEL → REPEAT` state lineage.

Alien locations:

- `PRE_REASON`
- `POST_PLAN_REFINE`
- `REPAIR_ONLY`
- `PRE_REASON_REPAIR`
- `PRE_REASON_REPAIR_POSTVERIFY_LEARN`
- `PREVERIFY_LEARN_NEGATIVE_CONTROL`

OpenAdapt locations:

- `EARLY_LOOKUP_POSTVERIFY_COMPILE`
- `AFTER_PLAN_LOOKUP_POSTVERIFY_COMPILE`
- `RESOLVER_POSTVERIFY_COMPILE`
- `REPAIR_ONLY`
- `POSTVERIFY_COMPILE_ONLY`
- `PREVERIFY_COMPILE_NEGATIVE_CONTROL`

VELMA verification locations:

- `PRE_EXEC_AUDIT`
- `POST_EFFECT_AUDIT`
- `BOTH`

Default overnight cells: Alien **192**, OpenAdapt **192**, VELMA **96**.

Placement analysis uses only complete paired blocks containing every candidate location.

## Phase 3/4 — complete topology lifecycle

Four causally motivated triple-stack topologies receive the same task lineages through the full lifecycle. State remains isolated by complete architecture configuration even when tasks are matched.

Default overnight cells: **704**.

The report preserves per-stage success, model calls, safe halts, and silent wrong effects. A Pareto set is reported instead of hiding trade-offs in a single composite score.

## Phase 5 — frontier

Three triple-stack topologies continue through difficulty 4, 8, 12, 16, 20, 24, 28, and 32. Each difficulty receives both `NOVEL` and `REPEAT`; state grows across the full frontier lineage. There is no capability early stop.

Default overnight cells: **768**.

The report stores complete NOVEL and REPEAT curves for each topology.

## Overnight workload

Default total: **2,976 preregistered core cells**.

The suite has no wall-clock timeout and no capability-based early termination. Individual model/API failures are terminalized as explicit non-scored evidence and the next cell continues.

## Model selection

008 does not guess a model before 007 finishes.

The final 007 summary is required. Eligible models must have valid experiment evidence and nonzero paired packet count. The primary model is selected by:

1. highest `paired_retrieved_minus_none_mean`;
2. tie-break by higher RETRIEVED last passing level;
3. tie-break by original suite order.

Before 008 starts, the selected model must pass an 008-specific live planner/auditor capability gate using the exact Ollama API and request shape.

## Real-model preflight

`--preflight-only` checks every installed candidate model before 007 is allowed to hand it to 008:

- exact model metadata/tag exists;
- thinking models receive `think=false`;
- non-thinking models omit `think`;
- the model returns strict planner JSON;
- the returned plan actually solves the easy sealed task;
- the model returns valid auditor JSON;
- internal Alien promotion/retrieval works;
- internal compiled-skill replay works with zero additional model calls.

A format-valid but objectively wrong plan fails preflight.

## Anti-zero contract

Numeric `0` means only a valid scored capability outcome that failed or safely halted. It never means missing evidence.

Non-scored statuses include:

- `MODEL_UNAVAILABLE`
- `COMPONENT_UNAVAILABLE`
- `OUTPUT_CAP_REACHED`
- `FORMAT_UNSCORABLE`
- `CONTEXT_CAP_REACHED`
- `INFRASTRUCTURE_UNSCORABLE`
- `ORACLE_INVALID`
- `HARNESS_INVALID`
- `CONFIG_INVALID`
- `SKIPPED_PREREGISTERED`
- `PRODUCT_VALIDATION_UNAVAILABLE`

All non-scored statuses require `score = null`. Evidence validation rejects accidental numeric scores on those statuses.

## Evidence and durability

Before live execution, the complete ledger is generated and sealed with SHA-256. Reusing an output directory with a different ledger raises `OUTPUT_DIRECTORY_LEDGER_MISMATCH` before work begins.

Every terminal cell is atomically written as an evidence envelope containing:

- full evidence payload;
- SHA-256 of the payload.

Evidence includes:

- cell order/state key;
- phase/model/topology;
- public task and sealed oracle hash;
- state-before/state-after snapshots and fingerprints;
- retrieved memory IDs;
- skill ID and resolution rungs;
- candidate/executed plan;
- semantic actions actually executed;
- screen result;
- authoritative system-of-record result;
- verification result;
- model-call/token/latency counts;
- retry events;
- terminal error/status.

Hash mismatch, truncated JSON, or malformed evidence is moved to `quarantine/` and the missing cell can be recomputed. Recovered corrupt artifacts remain visible in the final report but do not invalidate a fully recomputed evidence set.

## Resume semantics

State restoration is based on `state_key` and the highest completed predecessor `cell_order`, never filesystem filename order. This prevents stale memory/skill snapshots after a crash.

The same command and output directory resume completed cells. A changed ledger is refused.

## Completion semantics

The following are distinct:

- `execution_complete` — every preregistered cell has a terminal current evidence record.
- `experiment_complete_valid` — execution is complete, no current invalid/unscorable cells remain, no orphan evidence is mixed in, and paired factorial evidence exists.
- `conclusion_status` — `VALID`, `PARTIAL_INVALID_EVIDENCE`, or `INSUFFICIENT_VALID_EVIDENCE`.

Loop completion can never masquerade as scientific validity.

## Audit gate

Before publication, the implementation must pass:

- unit/adversarial suite;
- Python compile;
- synthetic end-to-end audit;
- deterministic 2,976-cell ledger audit;
- unique cell-ID audit;
- matched-task audit;
- 100-seed × 8-family × 5-difficulty generator/oracle property audit;
- real-Ollama preflight before the overnight run;
- real OpenAdapt product gate before the overnight run.

The synthetic audit must mechanically demonstrate:

- all eight factorial arms present;
- complete paired factorial blocks;
- OpenAdapt repeat can execute with zero model calls;
- Alien repeat retrieves learned cognition;
- VELMA invokes an independent auditor;
- OpenAdapt effect verification removes silent false-success claims;
- valid scored zeros remain zeros;
- invalid/missing work never becomes zero;
- every synthetic cell reconciles.
