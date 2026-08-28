# Combinatorial Alien-Stack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible, time-budgeted experiment harness that exhaustively tests six external-cognition primitives alone and in compounds, then adaptively spends remaining runtime on transfer, order effects, and neural-compute substitution.

**Architecture:** A standard-library Python package generates sealed synthetic software-maintenance tasks, compiles answer-free cognitive workspaces through composable deterministic passes, calls local Ollama, appends immutable JSONL run records, and analyzes the Boolean cube for main effects, interaction effects, Shapley contributions, Pareto-efficient stacks, transfer, and order effects. Expected answers remain isolated in a sealed evaluator file that compiler code never receives.

**Tech Stack:** Python 3.11+ standard library, Ollama HTTP API, `unittest`, Git.

**Spec:** `docs/superpowers/specs/2026-08-28-combinatorial-alien-stack-design.md`

## Global Constraints

- Fixed model subject: `qwen3.5:9b-q8_0`.
- Default context: 25,600 tokens.
- Default target runtime: 35 minutes; stop scheduling optional work at 40 minutes.
- Temperature 0 and deterministic run seeds.
- Compiler code never receives expected answers.
- RAW and STRUCTURED controls must remain distinguishable from derived cognition.
- All six primitive subsets must be representable; Phase 1 enumerates the complete 64-arm Boolean cube.
- Raw outputs and derivation provenance are append-only evidence.
- No experiment result automatically changes V31M4.

---

### Task 1: Core task/workspace types and sealed task generation

**Files:**
- Create: `alien_lab/types.py`
- Create: `alien_lab/taskgen.py`
- Create: `tests/test_taskgen.py`

**Interfaces:**
- Produces: `Task`, `SourceRecord`, `Edge`, `Workspace`, `generate_taskset(seed: int)`, `write_sealed_taskset(...)`.
- `Task` intentionally has no expected-answer field.

- [ ] Write tests proving generated task objects contain no expected answer, answer positions vary, IDs are stable for a fixed seed, and sealed answers are stored separately.
- [ ] Run `python -m unittest tests.test_taskgen -v` and verify RED because implementation is absent.
- [ ] Implement the minimal dataclasses and deterministic task generator.
- [ ] Run the same test command and verify GREEN.
- [ ] Commit.

### Task 2: Six composable cognition primitives

**Files:**
- Create: `alien_lab/primitives.py`
- Create: `alien_lab/compiler.py`
- Create: `tests/test_primitives.py`

**Interfaces:**
- Produces primitive names `state`, `path`, `uncertainty`, `relevance`, `procedure`, `memory`.
- Produces `compile_workspace(task: Task, primitives: tuple[str, ...], order: tuple[str, ...] | None = None) -> Workspace`.

- [ ] Write failing tests for each primitive and key order-sensitive pair.
- [ ] Verify RED.
- [ ] Implement one primitive at a time with derivation traces and no evaluator access.
- [ ] Verify GREEN after each primitive.
- [ ] Add tests proving `PATH -> RELEVANCE` can differ from `RELEVANCE -> PATH` without changing source evidence.
- [ ] Commit.

### Task 3: Serialization controls and anti-leakage invariants

**Files:**
- Create: `alien_lab/serialize.py`
- Create: `tests/test_serialize.py`

**Interfaces:**
- Produces `render_raw(task)`, `render_structured(task)`, `render_workspace(task, workspace)`.

- [ ] Write tests proving RAW contains original evidence, STRUCTURED contains the same evidence without derivations, compiled serialization exposes only enabled-pass derivations, and no renderer can access sealed answers.
- [ ] Verify RED.
- [ ] Implement serializers.
- [ ] Verify GREEN.
- [ ] Commit.

### Task 4: Ollama runner and immutable run records

**Files:**
- Create: `alien_lab/ollama.py`
- Create: `alien_lab/records.py`
- Create: `tests/test_records.py`

**Interfaces:**
- Produces `OllamaClient.generate(...)`, `RunRecord`, `append_jsonl(path, record)`.

- [ ] Write failing tests for API payload shape, metric extraction, ceiling detection, and append-only JSONL serialization using a local fake HTTP server.
- [ ] Verify RED.
- [ ] Implement with Python standard-library HTTP only.
- [ ] Verify GREEN.
- [ ] Commit.

### Task 5: Boolean-cube arm generation and causal math

**Files:**
- Create: `alien_lab/design.py`
- Create: `alien_lab/analysis.py`
- Create: `tests/test_analysis.py`

**Interfaces:**
- Produces `all_subsets()`, `mobius_interactions(values)`, `shapley_values(values)`, `pareto_frontier(rows)`, `minimal_sufficient(rows)`.

- [ ] Write tests proving exactly 64 unique subsets are generated for six primitives.
- [ ] Write analytical fixtures with known additive, synergistic, and antagonistic value functions.
- [ ] Verify RED.
- [ ] Implement exact subset/Möbius/Shapley calculations and Pareto/minimal-set helpers.
- [ ] Verify GREEN.
- [ ] Commit.

### Task 6: Time-budgeted adaptive experiment scheduler

**Files:**
- Create: `alien_lab/experiment.py`
- Create: `tests/test_scheduler.py`

**Interfaces:**
- Produces `ExperimentConfig`, `ExperimentRunner.run()`, CLI `python -m alien_lab.experiment`.

- [ ] Write tests with a fake model client proving required Boolean-cube work runs before optional phases, rolling timing determines optional scheduling, no new optional run begins after the hard stop, and an in-flight run is never discarded.
- [ ] Verify RED.
- [ ] Implement phases: calibration, exhaustive discovery, transfer, order checks, compute substitution.
- [ ] Verify GREEN.
- [ ] Commit.

### Task 7: Compound promotion registry and report generation

**Files:**
- Create: `alien_lab/report.py`
- Create: `tests/test_report.py`

**Interfaces:**
- Produces `build_compound_registry(...)` and Markdown/JSON summary artifacts.

- [ ] Write tests proving only transferred positive interactions are marked confirmed, compound IDs are stable, recursive constituent metadata is preserved, and weak/antagonistic compounds are not silently promoted.
- [ ] Verify RED.
- [ ] Implement registry/report generation.
- [ ] Verify GREEN.
- [ ] Commit.

### Task 8: First experiment configuration and operator instructions

**Files:**
- Create: `experiments/001-combinatorial-alien-stack/config.json`
- Create: `experiments/001-combinatorial-alien-stack/README.md`
- Create: `results/.gitkeep`
- Modify: `README.md`

**Interfaces:**
- Produces one-command local execution instructions and frozen defaults.

- [ ] Add configuration with model `qwen3.5:9b-q8_0`, context `25600`, target `35`, hard stop `40`, and the three reasoning budgets.
- [ ] Document exact WSL execution and result files.
- [ ] Run the full unit-test suite.
- [ ] Run `python -m alien_lab.experiment --dry-run` to verify the complete arm/phase plan without invoking Ollama.
- [ ] Commit.

### Task 9: Verification gate before execution

**Files:**
- No new files unless verification reveals defects.

- [ ] Run `python -m unittest discover -s tests -v` and require zero failures.
- [ ] Run `python -m alien_lab.experiment --dry-run --config experiments/001-combinatorial-alien-stack/config.json` and inspect counts, phase ordering, and answer isolation.
- [ ] Inspect `git diff main...HEAD` for accidental evaluator leakage or hard-coded answer-derived logic.
- [ ] Only after fresh verification, open the branch for user execution/review.
