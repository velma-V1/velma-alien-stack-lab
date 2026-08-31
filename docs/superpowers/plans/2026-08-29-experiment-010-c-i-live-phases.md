# Experiment 010 C–I Live Phases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement every frozen Experiment 010 Phase C–I execution path so the complete local experiment can run against an Ollama model and Phase I can run paired frontier arms through a configured Anthropic-compatible provider without changing the preregistered scientific contract.

**Architecture:** Preserve the completed A/B runner and add focused modules for hard non-oracle surfaces, provider-neutral model I/O, frozen C–I ledgers, real semantic/router execution, typed dataflow composition, verified capability accumulation, long-horizon state execution, and fair generic-agent/frontier calibration. Credential-free tests use deterministic fake providers solely to verify mechanics; fake-provider output is permanently labeled non-live evidence.

**Tech Stack:** Python 3.11 standard library; `urllib.request` for Ollama `/api/chat` and Anthropic `/v1/messages`; JSON-schema payloads where the configured provider supports them; unittest; existing SHA-256 evidence envelopes; GitHub Actions.

**Spec:** `experiments/010-computational-basis-atlas/PREREGISTRATION-C-I-v1.md`

## Global Constraints

- The frozen C–I preregistration at commit `9f04d7cc750e3099a383e2beaafff9c4d87893e2` is authoritative and must not be edited to accommodate results.
- C–I seeds, world indices, arms, counts, scoring, budgets, rescue order, and fairness rules are immutable.
- Only a new strictly harder versioned extension is permitted after the preregistered objective ceiling trigger is met.
- A/B evidence and ledgers are preserved and never rescored.
- Non-oracle surfaces must not expose engine letters, engine names, behavioral-family labels, `required_capabilities`, or expected results.
- A model cannot verify its own result.
- Fake-provider CI evidence is mechanics-only and can never be counted as live-model capability evidence.
- Healthy-provider refusal/malformed output/unsupported modality is a capability outcome; transport/provider outage after two retries is invalid `score=null` infrastructure evidence.
- Every run seals `system_version`, provider/model identity, generation contract, and ledger identity before the first live cell.
- Changed run identity may not reuse an existing output directory.
- V31M4 remains untouched; 010 only produces promotion evidence.

---

### Task 1: Hard non-oracle surfaces and unbound TaskIR

**Files:**
- Create: `alien_lab/computational_atlas_surfaces.py`
- Modify: `alien_lab/computational_atlas_types.py`
- Test: `tests/test_computational_atlas_live.py`

**Interfaces:**
- Produces `UnboundOperation`, `UnboundTaskIR`, `render_live_surface(world, representation)`, `oracle_unbound_ir(world)`, `task_ir_json_schema()`.
- Non-oracle renderers expose problem facts/relationships without solver labels.

- [ ] Write tests asserting R1–R5 surfaces contain none of `G/L/C/P/X/M/D/R`, capability names from `CAPABILITY_NAMES`, family names, `required_capabilities`, or expected results.
- [ ] Write tests asserting `oracle_unbound_ir` preserves every operation's semantics/payload/order while removing engine assignment.
- [ ] Write tests asserting deterministic surface replay for seed/world/representation and real R5 image bytes with a stable SHA-256 identity.
- [ ] Run `python -m unittest tests.test_computational_atlas_live -v` and confirm RED because the live surface module does not exist.
- [ ] Implement domain-neutral operation intents (`path_query`, `rule_entailment`, `budget_selection`, `state_goal_search`, `program_transform`, `numeric_aggregate`, `record_join_aggregate`, `evidence_rank`) and naturalized R1–R4 renderers.
- [ ] Implement a standard-library PNG renderer for R5 and return base64 image payload plus media type.
- [ ] Run focused tests and commit.

### Task 2: Provider adapters and sealed run identity

**Files:**
- Create: `alien_lab/computational_atlas_providers.py`
- Create: `alien_lab/computational_atlas_live_types.py`
- Modify: `tests/test_computational_atlas_live.py`

**Interfaces:**
- Produces `ModelProvider`, `ModelRequest`, `ModelResponse`, `FakeProvider`, `OllamaProvider`, `AnthropicMessagesProvider`, `RunIdentity`, `seal_run_identity(...)`.
- `OllamaProvider` calls configured `/api/chat` with `stream=false`, optional JSON schema in `format`, and optional images.
- `AnthropicMessagesProvider` calls configured `/v1/messages`, supports text/image user content and runtime-configured model IDs.

- [ ] Add RED tests for provider request serialization, two transport retries, refusal/malformed-vs-transport classification, token/time accounting, schema payloads, image payloads, and immutable run identity.
- [ ] Add a fake HTTP transport fixture so tests validate real request/response parsing without network access.
- [ ] Implement provider-neutral dataclasses and a deterministic `FakeProvider` marked `FAKE_MECHANICS_ONLY`.
- [ ] Implement Ollama adapter against `/api/chat` with structured-output support and extraction from `message.content`.
- [ ] Implement Anthropic Messages adapter with `x-api-key`, `anthropic-version`, text/image content blocks, and extraction of text blocks/usage/stop reason.
- [ ] Implement output-directory identity refusal when `system_version`, provider/model, generation contract, or ledger identity changes.
- [ ] Run focused tests and commit.

### Task 3: Frozen Phase C/D ledgers and semantic execution

**Files:**
- Create: `alien_lab/computational_atlas_semantics.py`
- Create: `alien_lab/computational_atlas_live_ledger.py`
- Modify: `alien_lab/computational_atlas.py`
- Modify: `tests/test_computational_atlas_live.py`

**Interfaces:**
- Produces `build_phase_c_ledger() -> list[LiveCell]` with exactly 3,840 base cells; `build_phase_d_ledger() -> list[LiveCell]` with exactly 576 base cells; `compile_surface(...)`; `score_compiled_ir(...)`; `run_semantic_cell(...)`.

- [ ] Add RED tests for exact C/D seed, world, representation, arm, and cell counts from the frozen preregistration.
- [ ] Add paired tests proving original unresolved semantic scores remain unchanged after rescue diagnostics.
- [ ] Add tests for `MODEL_DIRECT`, deterministic recognizer, local semantic compiler, and oracle-IR arms using fake providers whose outputs are predetermined by test input rather than sealed answers.
- [ ] Add D tests for free JSON, schema constrained, and schema+validate+exactly-one-repair; assert the repair arm can never exceed two semantic model calls.
- [ ] Implement prompts frozen as module constants and hash them into run identity.
- [ ] Implement JSON extraction, unbound-IR validation, deterministic routing/binding, basis execution, independent result verification, and semantic error taxonomy.
- [ ] Implement C rescue evidence as separate envelopes without modifying original cells.
- [ ] Run focused tests and commit.

### Task 4: Frozen Phase E routing and overload

**Files:**
- Create: `alien_lab/computational_atlas_routing.py`
- Modify: `alien_lab/computational_atlas_live_ledger.py`
- Modify: `tests/test_computational_atlas_live.py`

**Interfaces:**
- Produces frozen `REAL_TOOL_CATALOG`, `DECOY_TOOL_CATALOG`, `rule_route(unbound_ir, catalog)`, `model_route(...)`, `build_phase_e_ledger() -> list[LiveCell]` exactly 864 cells.

- [ ] Add RED tests for exact 96 worlds × 3 routers × 3 catalogs and fixed 8/16/32 catalog sizes.
- [ ] Assert real eight-tool descriptions are byte-identical across catalog conditions and later Phase I.
- [ ] Assert decoys are unavailable to the executor and selecting one yields `VALID_UNRESOLVED_ROUTING`.
- [ ] Assert router inputs omit oracle engine assignment and expected answers.
- [ ] Implement oracle, rule, and local-model router execution with exact-set/precision/recall/decoy/missing-required metrics and paired routing regret.
- [ ] Run focused tests and commit.

### Task 5: Frozen Phase F typed dataflow composition

**Files:**
- Create: `alien_lab/computational_atlas_composition.py`
- Modify: `alien_lab/computational_atlas_live_ledger.py`
- Modify: `tests/test_computational_atlas_live.py`

**Interfaces:**
- Produces `CompositionWorld`, `Binding`, `build_composition_worlds(seed=20260913, count=96)`, `execute_composition(...)`, `build_phase_f_ledger() -> list[LiveCell]` exactly 1,152 cells.

- [ ] Add RED tests for the immutable 24/24/24/24 distribution of 2/3/4/5-capability worlds.
- [ ] Prove every world has at least one downstream input whose sealed correct value depends on a prior engine output.
- [ ] Add tests showing each single-engine arm and `ALL_ENGINES_NO_TYPED_HANDOFF` fail on a representative chained world while typed composition succeeds.
- [ ] Add a regression asserting co-requirement alone cannot set `measured_synergy=true`.
- [ ] Implement typed value references/selectors, dependency ordering, deterministic binding, execution trace, first-broken-handoff diagnostics, and independent verifier.
- [ ] Implement all 12 frozen F arms and paired synergy calculation.
- [ ] Run focused tests and commit.

### Task 6: Frozen Phase G verified capability accumulation

**Files:**
- Create: `alien_lab/computational_atlas_accumulation.py`
- Modify: `alien_lab/computational_atlas_live_ledger.py`
- Modify: `tests/test_computational_atlas_live.py`

**Interfaces:**
- Produces `CapabilityPackage`, `build_lineages(seed=20260914, count=48)`, `run_lineage_event(...)`, `build_phase_g_ledger() -> list[LiveCell]` exactly 864 events.

- [ ] Add RED tests for 48 lineages × six frozen stages × three frozen arms in strict order.
- [ ] Assert no executable package is created from unverified work.
- [ ] Assert `NO_RETAINED_CAPABILITY` never bypasses the semantic path; `TEXT_MEMORY` may add verified context but not bypass semantics; `VERIFIED_EXECUTABLE_CAPABILITY` may bypass the model only after its deterministic applicability check accepts.
- [ ] Add tests for correct reuse, applicability rejection, incorrect-reuse detection, parameter variation, representation shift, drift, and composition transfer.
- [ ] Implement a data-derived capability template generated from a verified surface/IR pair: immutable structural signature, parameter bindings learned from paired values, applicability predicate, executor plan, verifier contract, and provenance. Do not hard-code world IDs or generator indices into packages.
- [ ] Record success and model dependence as separate axes.
- [ ] Run focused tests and commit.

### Task 7: Frozen Phase H long-horizon state machine

**Files:**
- Create: `alien_lab/computational_atlas_horizon.py`
- Modify: `alien_lab/computational_atlas_live_ledger.py`
- Modify: `tests/test_computational_atlas_live.py`

**Interfaces:**
- Produces `HorizonJob`, `Milestone`, `build_horizon_jobs(seed=20260915)`, `run_horizon_job(...)`, `build_phase_h_ledger() -> list[LiveCell]` exactly 120 cells.

- [ ] Add RED tests for exactly ten jobs each at 8/16/32/64 independently verifiable state-changing milestones and exactly three arms.
- [ ] Assert final success cannot erase a previously incorrect authoritative milestone.
- [ ] Add tests for first-error location, state drift, verifier detection, recovery, silent-wrong milestones, and milestone coverage.
- [ ] Implement deterministic milestone state transitions built from frozen engine/composition operations and a sealed oracle trace.
- [ ] Implement `MODEL_DIRECT_LONG`, `VELMA_NO_AUTHORITATIVE_VERIFIER`, and `VELMA_FULL` with identical initial state and milestone oracle.
- [ ] Run focused tests and commit.

### Task 8: Frozen Phase I equivalent-tool frontier calibration

**Files:**
- Create: `alien_lab/computational_atlas_frontier.py`
- Modify: `alien_lab/computational_atlas_live_ledger.py`
- Modify: `alien_lab/computational_atlas.py`
- Modify: `tests/test_computational_atlas_live.py`

**Interfaces:**
- Produces `build_phase_i_tasks(seed=20260916)`, `GenericToolAgent`, `VelmaArchitectureAgent`, `build_phase_i_ledger() -> list[LiveCell]` exactly 288 cells.

- [ ] Add RED tests for immutable 12 semantic + 24 composition + 12 horizon task distribution and six frozen arms.
- [ ] Assert Phase I task selection is seed/index based only and cannot accept C–H performance as input.
- [ ] Assert generic and VELMA paired arms receive byte-identical eight-real-tool schemas, underlying engine implementations, execution permissions, and tool-call budget.
- [ ] Implement generic-agent tool loop with provider tool calls mapped only to the frozen real tool catalog.
- [ ] Implement VELMA architecture arm using semantic compiler, deterministic validation, router/composer, same underlying tools, and authoritative verifier.
- [ ] Record provider/model identity before first I cell and refuse mid-run changes.
- [ ] Implement paired frontier-gap, silent-wrong, tool/model-call, token/time/cost, and milestone metrics.
- [ ] Run focused tests and commit.

### Task 9: CLI integration, complete readiness CI, and documentation

**Files:**
- Modify: `alien_lab/computational_atlas.py`
- Modify: `experiments/010-computational-basis-atlas/config.json`
- Modify: `experiments/010-computational-basis-atlas/README.md`
- Modify: `.github/workflows/010-smoke.yml`
- Modify: `tests/test_computational_atlas_live.py`

**Interfaces:**
- `--profile local` executes frozen C–H when a healthy local provider is configured.
- `--profile frontier` executes frozen I in addition to required local/frozen prerequisites when configured providers are available.
- `--profile prereg-smoke` executes all C–I ledgers/mechanics against fake providers and labels every such result `FAKE_MECHANICS_ONLY`.

- [ ] Add RED tests that `local`/`frontier` no longer return placeholder `MODEL_UNAVAILABLE` merely because the runner lacks implementation; absence of required runtime configuration returns explicit configuration/unavailable evidence without fabricating scores.
- [ ] Add tests asserting exact nominal C–I ledger counts: C 3,840; D 576; E 864; F 1,152; G 864; H 120; I 288.
- [ ] Add tests for complete frozen total base-cell count C–I = 7,704 before rescue evidence.
- [ ] Integrate phase execution, resume, evidence sealing, system/provider identity, and phase-specific summaries into CLI/reporting.
- [ ] Add CI preregistration-smoke that builds every C–I ledger, executes representative fake-provider cells from every arm, verifies no label leakage, checks tool equivalence, and runs all A/B/009/008 regressions.
- [ ] Update README with exact local and frontier environment/configuration instructions and immutable-test rule.
- [ ] Run fresh CI; do not claim full 010 live readiness until all readiness checks are green.
- [ ] Commit.

### Task 10: Final readiness evidence

**Files:**
- Create: `experiments/010-computational-basis-atlas/READINESS-C-I-2026-08-29.md`

- [ ] Record preregistration commit SHA, executable commit SHA, CI run ID, test command, exact ledger counts, provider-contract tests, leakage tests, fairness/tool-equivalence tests, and regression status.
- [ ] Explicitly distinguish `READY_FOR_LIVE_TESTING` from actual live C–I scientific results.
- [ ] Confirm no C–I live provider call was made before the frozen contract and readiness harness were complete.
- [ ] Keep PR #3 draft/unmerged until the human partner decides integration/branch handling.
