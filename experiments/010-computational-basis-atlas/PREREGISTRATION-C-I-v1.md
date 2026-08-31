# Experiment 010 — Frozen C–I Preregistration v1

Date frozen: 2026-08-29
Experiment: `010-computational-basis-atlas`
Production destination for later justified promotions: `velma-V1/V31m4`

## Governing immutability rule

This document freezes the scientific contract for Experiment 010 Phases C–I before any live C–I model evidence is collected.

After this commit:

- evidence may change the system under test, but may not change this test in favor of the model, system, architecture, data, hypothesis, or researchers;
- task-generation rules, phase membership, seeds, arms, scoring, rescue order, comparison rules, budgets, and invalidation rules are immutable;
- a poor result remains poor evidence and is never replaced by an easier task, friendlier metric, different arm, or selective subset;
- fixes to infrastructure may rerun invalid cells only and may not change valid scored evidence;
- no valid score may be overwritten by rescue evidence;
- no phase may be dropped because it is unfavorable;
- the only permitted scientific extension is a strictly harder or broader versioned extension after objective ceiling saturation demonstrates that the frozen test has insufficient discriminatory power;
- a harder extension appends evidence and never replaces, rescales, erases, or reinterprets v1 evidence.

### Objective ceiling trigger

A phase is ceiling-saturated only when all of the following hold on its valid scored cells:

1. at least two materially different system arms each achieve >= 98% verified success;
2. at least 90% of scored cells are jointly correct for those saturated arms;
3. the absolute verified-success separation between the top two materially different arms is < 2 percentage points;
4. no preregistered harder representation/horizon/overload stratum in that phase remains below 95% for either saturated arm.

Meeting the trigger permits only an appended `HARDER_EXTENSION_vN`; it does not permit changing v1.

## Evidence partition rule

Every live phase preserves paired immutable task identity. Diagnostic results may guide changes to VELMA, but the benchmark itself never changes. Every rerun records a new `system_version` and retains prior evidence.

The test harness must never silently reuse an output directory for a different system version, model identity, provider configuration, prompt contract, or ledger identity.

## Global anti-advantage rules

- Non-oracle surfaces never reveal `required_capabilities`, engine letters, engine names, behavioral-family names, or a direct textual description of the required solver class.
- Model/router prompts never receive the expected result, sealed answer, oracle capability assignment, or downstream verifier result before committing their own output.
- Model confidence is diagnostic only.
- A model may not verify its own answer.
- Frontier and local baseline arms receive the exact tool environment preregistered for that arm; no arm receives a hidden tool advantage.
- Tool descriptions are frozen before live execution.
- Output/token/call budgets are frozen by configuration and counted in evidence.
- Refusal, malformed output, unsupported modality, and inability to select/operate an available tool are capability outcomes when the provider itself is healthy; transport/provider outages are invalid `score=null` infrastructure outcomes.
- Rescues are separate diagnostic cells and never replace original scores.

## Live model identity and budget

The local model is runtime-configured but its exact model identifier, digest when available, context limit, generation options, endpoint identity, and provider version are sealed into the run manifest before the first live cell.

Default local generation contract for v1:

- one model identity per complete run;
- temperature/default sampling is not tuned per task;
- no task-specific prompt changes after the first scored cell;
- `max_output_tokens = 2048` unless the provider exposes a smaller hard maximum, in which case the complete run is invalid until a compatible model/configuration is selected;
- semantic-repair arms may use exactly one additional repair call where explicitly preregistered;
- all model calls, prompt tokens where available, output tokens where available, wall time, and retries are recorded.

Provider transport retries are limited to 2 and do not permit changing prompts or sampling. A third transport failure makes the cell invalid infrastructure evidence.

## Surface contract

The live surfaces use the same underlying sealed problem semantics as their paired oracle TaskIR but do not expose solver-class labels.

- `R1_STRUCTURED`: typed records/tables with domain-neutral field labels and explicit values/relationships.
- `R2_NATURAL`: normal prose describing the actual problem facts and requested outcome without solver names.
- `R3_PARAPHRASED`: semantically identical prose with reordered facts, synonyms, distractors, and changed surface order.
- `R4_IMPLICIT`: necessary relationships/constraints are distributed across mixed records and must be inferred; solver names are absent.
- `R5_PERCEPTUAL`: the R1/R2 information is rendered into a real image/document artifact. A model without the required modality receives a valid unresolved perception score, not an infrastructure invalidation.

The pre-existing A/B oracle evidence is not rescored when these harder non-oracle renderers are introduced.

---

# Phase C — Semantic Compilation and Representation Tax

**Seed:** `20260910`

**Worlds:** all 192 generated worlds.

**Representations:** R1, R2, R3, R4, R5.

**Arms for every world/representation pair:**

1. `MODEL_DIRECT` — local model receives the surface and must return the final result directly. No external computational engine is available.
2. `DETERMINISTIC_RECOGNIZER_BASIS` — frozen non-neural recognizer attempts to produce unbound TaskIR, then the full basis executes and verifies it.
3. `LOCAL_SEMANTIC_COMPILER_BASIS` — local model produces unbound TaskIR, then deterministic validation, routing, basis execution, and independent verification run.
4. `ORACLE_IR_BASIS` — sealed oracle TaskIR is supplied downstream of semantics; this arm is the paired downstream ceiling and can never count as semantic success.

**Nominal base cells:** `192 × 5 × 4 = 3,840` before separate rescue evidence.

**Primary scoring:** final independently verified result. Outside-basis worlds remain valid unresolved missing-capability evidence.

**Secondary diagnostics:** syntax validity, TaskIR schema validity, operation/dependency completeness, entity/constraint/objective errors, unsupported modality, model calls, tokens, wall time.

**Semantic-formalization tax:** paired `ORACLE_IR_BASIS verified success - LOCAL_SEMANTIC_COMPILER_BASIS verified success` on the same in-basis cells. It is never computed by substituting rescued scores.

**Automatic rescue:** every original valid unresolved local semantic cell receives the frozen rescue ladder from the main 010 design.

---

# Phase D — Model-to-IR Interface

**Seed:** `20260911`

**Worlds:** fixed generated indices `64..159` inclusive (96 worlds; 64 two-capability + 32 three-capability worlds).

**Representations:** R3 and R4 only.

**Arms:**

1. `FREE_JSON` — one unconstrained model call instructed to return TaskIR JSON.
2. `SCHEMA_CONSTRAINED` — one model call using provider-supported JSON-schema/structured-output enforcement when available. Provider lack of structured-output support is an invalid configuration for this arm, not a zero capability score.
3. `SCHEMA_VALIDATE_REPAIR` — one schema-constrained call, deterministic validation, then exactly one counterexample-guided repair call only if the first result is syntactically/schema/semantically invalid.

**Nominal base cells:** `96 × 2 × 3 = 576`.

**Frozen repair budget:** maximum 2 model calls total for the repair arm; no third semantic call.

**Scoring:**

- `syntax_valid`;
- `schema_valid`;
- `semantic_executable`;
- `end_to_end_verified` (primary);
- calls/tokens/time.

The repair arm is allowed more inference because that is the mechanism under test; the extra cost is always reported and never normalized away.

---

# Phase E — Routing and Capability Overload

**Seed:** `20260912`

**Worlds:** fixed generated indices `0..95` inclusive (64 one-capability + 32 two-capability worlds).

**Input:** oracle-correct **unbound** TaskIR: problem semantics are present, but engine/capability labels and `required_capabilities` are removed. This isolates routing from semantic compilation.

**Router arms:**

1. `ORACLE_ROUTER`
2. `RULE_ROUTER`
3. `LOCAL_MODEL_ROUTER`

**Catalog conditions:**

- `CATALOG_8`: eight real capability interfaces;
- `CATALOG_16`: the same eight real interfaces + eight frozen overlapping/irrelevant decoys;
- `CATALOG_32`: the same eight real interfaces + twenty-four frozen overlapping/irrelevant decoys.

Decoy names/descriptions are generated from the immutable catalog table committed with the implementation and may not be edited after the first live E cell.

**Nominal base cells:** `96 × 3 × 3 = 864`.

**Primary scoring:** verified downstream result after selected real capabilities execute.

**Routing diagnostics:** exact-set match, precision, recall, decoy-selection rate, missing-required rate, unnecessary-real-tool rate, routing regret versus oracle, calls/tokens/time.

Tool-overload degradation is paired within world/router across 8/16/32 catalogs.

---

# Phase F — Genuine Typed Composition

**Seed:** `20260913`

**Worlds:** 96 dedicated chained worlds. Required-capability counts are fixed at:

- 24 worlds requiring exactly 2 capabilities;
- 24 requiring exactly 3;
- 24 requiring exactly 4;
- 24 requiring exactly 5.

Every world contains at least one typed data dependency in which a downstream engine cannot produce the sealed correct result unless it consumes an upstream engine result. Co-requirement without dataflow is insufficient.

**Input to computational arms:** oracle-correct unbound TaskIR to isolate composition. `MODEL_DIRECT` receives the paired R2 natural surface.

**Arms:**

1. `MODEL_DIRECT`
2. `SINGLE_G`
3. `SINGLE_L`
4. `SINGLE_C`
5. `SINGLE_P`
6. `SINGLE_X`
7. `SINGLE_M`
8. `SINGLE_D`
9. `SINGLE_R`
10. `ALL_ENGINES_NO_TYPED_HANDOFF`
11. `TYPED_COMPOSITION`
12. `TYPED_COMPOSITION_VERIFIED`

**Nominal base cells:** `96 × 12 = 1,152`.

**Synergy claim rule:** positive measured synergy exists for a world only when `TYPED_COMPOSITION` or `TYPED_COMPOSITION_VERIFIED` succeeds and every single-engine arm fails on that same world. Aggregate synergy requires the paired combined arm to outperform the best single-engine envelope; co-occurrence is never sufficient.

**Composition diagnostics:** first broken handoff, producer/consumer types, missing/invalid binding, execution order, verifier effect, calls/tokens/time.

---

# Phase G — Verified Capability Accumulation

**Seed:** `20260914`

**Lineages:** 48 immutable lineages.

**Stages per lineage, in order:**

1. `NOVEL`
2. `REPEAT`
3. `PARAMETER_VARIATION`
4. `REPRESENTATION_SHIFT`
5. `ENVIRONMENT_DRIFT`
6. `COMPOSITION_TRANSFER`

**Arms:**

1. `NO_RETAINED_CAPABILITY` — every event uses the normal live semantic path; nothing reusable is retained between lineage events.
2. `TEXT_MEMORY` — verified prior semantic/procedural evidence may be retrieved into context, but execution is not allowed to bypass semantic/model reasoning solely because text memory exists.
3. `VERIFIED_EXECUTABLE_CAPABILITY` — only a previously independently verified capability package may attempt zero-model recognition/binding/execution. If its frozen applicability check rejects the event, the normal semantic path runs and the event remains fully scored.

**Nominal events:** `48 × 6 × 3 = 864`.

**No negative-control leakage:** a capability package is created only after independently verified success. Failed/unverified work cannot be compiled as reusable capability.

**Primary scoring:** final independently verified success.

**Accumulation diagnostics:** semantic/model calls, zero-model reuse, incorrect reuse, applicability rejection, repair, parameter transfer, representation transfer, drift survival, composition transfer, tokens/time.

A lower model-call count is never credited if verified success falls; success and dependence remain separate axes.

---

# Phase H — Long-Horizon Reliability

**Seed:** `20260915`

**Jobs:** 40 dedicated long-horizon jobs:

- 10 at horizon 8;
- 10 at horizon 16;
- 10 at horizon 32;
- 10 at horizon 64.

A horizon is the number of independently checkable state-changing milestones, not prompt length.

**Arms:**

1. `MODEL_DIRECT_LONG`
2. `VELMA_NO_AUTHORITATIVE_VERIFIER`
3. `VELMA_FULL`

All jobs use the same frozen initial state and milestone oracle across arms. VELMA arms may use the frozen computational basis and typed composition; the model-direct arm may not call hidden VELMA computation.

**Nominal base cells:** `40 × 3 = 120`.

**Primary scoring:** complete-job verified success.

**Dense diagnostics:** percentage of milestones correct, first incorrect milestone, first detected fault, recovery success, state drift, silent-wrong milestones, verifier coverage, calls/tokens/time.

No final-only success may erase an earlier incorrect authoritative milestone.

---

# Phase I — Frontier Calibration

**Seed:** `20260916`

**Tasks:** fixed 48-task difficult calibration suite generated independently from Phase I seed with this immutable distribution:

- 12 semantic/representation tasks;
- 24 genuine typed-composition tasks;
- 12 long-horizon tasks.

No task is selected based on C–H observed results.

**System arms:**

1. `LOCAL_GENERIC_AGENT`
2. `VELMA_LOCAL`
3. `FRONTIER_A_GENERIC_AGENT`
4. `VELMA_FRONTIER_A`
5. `FRONTIER_B_GENERIC_AGENT`
6. `VELMA_FRONTIER_B`

`FRONTIER_A` and `FRONTIER_B` model identifiers are runtime-configured and sealed before the first Phase I cell. They are never selected after inspecting Phase I outcomes.

## Equivalent-tool rule

Generic-agent baselines receive the same eight real capability interfaces as callable tools, with the same tool descriptions, execution permissions, tool-call budget, and underlying reference/mature implementations used by the paired VELMA arm. They do not receive VELMA's TaskIR compiler, deterministic router/composer, capability library, or authoritative verifier orchestration unless those are themselves exposed equally to every generic baseline (default: they are not).

VELMA arms use the frozen 010 architecture around the same underlying model and tools.

**Nominal base cells:** `48 × 6 = 288`.

**Primary scoring:** independent end-to-end verified success.

**Competitive metrics:** paired verified-success difference, capability-family gap, silent-wrong rate, tool/model calls, input/output tokens, wall time, cost where provider pricing metadata is supplied, and long-horizon milestone accuracy.

The primary comparison is system-to-system. A frontier model is never artificially denied generic tool access to make VELMA look better.

---

# Frozen rescue order for C–I

For an original valid unresolved cell where the phase permits rescue diagnostics:

1. original path;
2. oracle TaskIR;
3. oracle decomposition;
4. oracle routing;
5. oracle individual engine outputs;
6. oracle typed cross-engine handoff;
7. oracle execution outcome;
8. verifier discrimination against sealed expected result.

Localization labels remain:

`SEMANTIC`, `DECOMPOSITION`, `ROUTING`, `ENGINE`, `COMPOSITION`, `EXECUTION`, `VERIFICATION`, `MISSING_CAPABILITY`, `AMBIGUOUS_INPUT`, plus `PERCEPTION` for R5 modality inability.

The first intervention that restores a verified downstream result localizes the narrowest recoverable bottleneck. Rescued evidence is separate and the original score remains unchanged.

# Frozen execution order

The live experiment may be implemented in stages, but the scientific contract above may not be altered because of results. Normal execution order is C, D, E, F, G, H, I. VELMA itself may be improved between runs or phases; each change must receive a new `system_version`, and the unchanged test is rerun when comparison is required.

# Required readiness before first live C cell

Before any live Phase C result is accepted, CI/tests must establish that:

- the C–I ledger builders reproduce the exact preregistered counts above;
- non-oracle surfaces contain no capability/engine labels;
- local-provider transport and structured-output paths are executable;
- Phase I generic-agent and VELMA tool catalogs are byte-for-byte equivalent for the eight real tools;
- every phase records immutable model/provider/system identity;
- result directories reject changed ledger/model/system identity;
- scoring/rescue rules cannot overwrite original valid evidence;
- C–I fixtures can execute credential-free with deterministic fake providers without being reported as live model evidence.

Only after those conditions are green is the live test considered ready.