# Experiment 010 Computational Basis Atlas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, evidence-sealed Experiment 010 framework that measures an eight-capability computational basis, localizes unresolved tasks with counterfactual rescue, produces the mandatory discovery maps and V31M4 production-fit records, and exposes provider-neutral hooks for later local/frontier model phases.

**Architecture:** Split the experiment into typed TaskIR/world definitions, deterministic reference engines, an experiment runner with factorial/leave-one-out/rescue/lifecycle phases, and a reporter. CI runs the credential-free `smoke` profile plus all regression tests; `atlas`, `local`, and `frontier` remain explicit CLI profiles.

**Tech Stack:** Python 3.11 standard library, unittest, JSON/SHA-256 evidence envelopes, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-29-experiment-010-computational-basis-atlas-design.md`

## Global Constraints

- No top-level PASS/FAIL scientific conclusion; valid complete execution concludes `DISCOVERY_COMPLETE`.
- Labs never mutate V31M4 production state.
- Built-in engines are reference scientific adapters, not production promotion decisions.
- Deterministic phases require zero neural model calls.
- Every original unresolved task retains its own score; rescue interventions are diagnostic and cannot overwrite it.
- Invalid infrastructure/config/model-unavailable outcomes use `score=null`.
- Evidence and ledgers are SHA-256 sealed and changed-ledger output-directory reuse is refused.
- Model/provider integrations are provider-neutral and optional; CI requires no credentials or network inference.

---

### Task 1: Typed TaskIR, worlds, and eight reference engines

**Files:**
- Create: `alien_lab/computational_atlas_types.py`
- Create: `alien_lab/computational_atlas_worlds.py`
- Create: `alien_lab/computational_atlas_engines.py`
- Test: `tests/test_computational_atlas.py`

**Interfaces:**
- Produces `TaskIR`, `World`, `EngineResult`, `build_worlds(seed, count=192)`, `run_engine(capability, payload, inputs)`.
- World public renderings omit sealed expected answer and required-capability labels outside oracle arms.

- [ ] Write failing tests asserting 192 stable unique worlds, the 64/64/40/16/8 computation distribution, all 12 behavioral families, deterministic replay, and direct correctness of G/L/C/P/X/M/D/R engines.
- [ ] Run `python -m unittest tests.test_computational_atlas -v` and confirm failure because the 010 modules do not exist.
- [ ] Implement immutable dataclasses/JSON conversion, stable hashing, deterministic world generation, representation renderers, and eight small reference engines with explicit unsupported/error results.
- [ ] Run the focused test suite and require all Task 1 tests to pass.
- [ ] Commit the Task 1 implementation.

### Task 2: Phase A/B runner and exact attribution

**Files:**
- Create: `alien_lab/computational_atlas.py`
- Modify: `tests/test_computational_atlas.py`

**Interfaces:**
- Consumes `World`, `TaskIR`, and engine registry.
- Produces `build_ledger(config)`, `run_cell(cell)`, `run_experiment(config, output_dir)`, per-cell evidence envelopes, and summary metrics.

- [ ] Add failing tests for 256-subset enumeration, deterministic 64-world Phase A ledger, 192-world full/leave-one-out Phase B ledger, zero model calls, unique cell IDs, and output-directory ledger mismatch refusal.
- [ ] Run the tests and confirm the new runner assertions fail.
- [ ] Implement subset execution, typed handoffs, exact verifier, atomic JSON, SHA-256 envelopes, ledger manifest, resume semantics, and deterministic replay fingerprint.
- [ ] Implement unique contribution, redundancy/substitution, minimum-sufficient-subset, and interaction summaries from paired Phase A/B evidence.
- [ ] Run focused tests and require deterministic equality across clean runs.
- [ ] Commit Phase A/B.

### Task 3: Rescue localization, composition, and accumulation

**Files:**
- Modify: `alien_lab/computational_atlas.py`
- Create: `alien_lab/computational_atlas_report.py`
- Modify: `tests/test_computational_atlas.py`

**Interfaces:**
- Produces `localize_unresolved(...)`, composition evidence, lifecycle evidence, bottleneck taxonomy, model-dependence/reuse metrics, and generated discovery maps.

- [ ] Add failing tests in which controlled corruptions are rescued specifically at semantic, decomposition, routing, engine, composition, execution, and verification interventions, plus an outside-basis case that remains `MISSING_CAPABILITY`.
- [ ] Add failing tests proving a rescue never changes the original score and a typed multi-engine world can succeed only when all required handoffs are available.
- [ ] Implement the ordered rescue ladder and preserve every intervention as separate evidence.
- [ ] Implement 48 deterministic capability lineages across NOVEL/REPEAT/PARAMETER_VARIATION/REPRESENTATION_SHIFT/ENVIRONMENT_DRIFT/COMPOSITION_TRANSFER with reference no-retention/text-memory/executable-capability arms.
- [ ] Implement report maps for coverage, minimum basis, unique value, synergy, substitution, bottlenecks, silent-wrong/verification value, learning/transfer, and next-direction Pareto candidates.
- [ ] Run focused tests and commit.

### Task 4: Provider-neutral semantic/router hooks and production fitness

**Files:**
- Create: `alien_lab/computational_atlas_models.py`
- Modify: `alien_lab/computational_atlas_report.py`
- Modify: `tests/test_computational_atlas.py`

**Interfaces:**
- Produces strict `SemanticCompiler` and `Router` protocols, deterministic reference implementations, unavailable-model evidence, and `ProductionFitnessRecord` generation.

- [ ] Add failing tests proving model/provider absence is unscored unavailable evidence, not zero; hidden capability labels never reach non-oracle model/router inputs; and Production Fitness Records contain Q27–Q36-relevant fields.
- [ ] Implement provider-neutral request/result dataclasses and local/frontier configuration hooks without provider SDK imports.
- [ ] Implement deterministic semantic/routing fixtures used by CI to exercise R1–R4 degradation and routing-overload analysis without pretending they are live model evidence.
- [ ] Implement Production Fitness Records with V31M4 seam, verification, isolation, replaceability, resource-estimate, roadmap-displacement, and promotion-status fields.
- [ ] Run focused tests and commit.

### Task 5: CLI profiles, config, experiment docs, and CI

**Files:**
- Create: `experiments/010-computational-basis-atlas/config.json`
- Create: `experiments/010-computational-basis-atlas/README.md`
- Create: `.github/workflows/010-smoke.yml`
- Modify: `alien_lab/computational_atlas.py`
- Modify: `tests/test_computational_atlas.py`

**Interfaces:**
- CLI: `python -m alien_lab.computational_atlas --config ... --output-dir ... --profile smoke|atlas|local|frontier`.
- Exit 0 means execution/report generation completed with valid accounted evidence; exit 2 means invalid configuration/harness/infrastructure.

- [ ] Add failing CLI tests for `smoke`, changed-ledger refusal, complete accounted terminal cells, `DISCOVERY_COMPLETE`, and explicit unavailable live phases.
- [ ] Implement config loading/validation and profile-scoped ledger construction.
- [ ] Add README documenting scientific interpretation, no-kill semantics, rescue taxonomy, outputs, and V31M4 promotion boundary.
- [ ] Add GitHub Actions workflow: compileall; 010 tests; 009 and 008 regressions; run credential-free smoke CLI; print summary.
- [ ] Run all available tests through CI and require green evidence before claiming completion.
- [ ] Commit docs/config/workflow.

### Task 6: Final evidence review

**Files:**
- Create after verified execution: `experiments/010-computational-basis-atlas/RESULTS-2026-08-29.md`

- [ ] Verify exact branch HEAD, workflow run, test count, smoke ledger hash, replay fingerprint, invalid-cell count, and discovery conclusion.
- [ ] Confirm 009 branch remains unchanged and no V31M4 repository files were modified.
- [ ] Record what the smoke run demonstrates and explicitly what remains for full atlas/local/frontier execution.
- [ ] Create a draft PR targeting `experiment/009-solver-kill-test`; do not merge it.
