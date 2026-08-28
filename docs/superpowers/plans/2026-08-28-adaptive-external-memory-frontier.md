# Adaptive External Memory Frontier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Experiment 007: an adaptive, increasingly difficult external-memory benchmark that learns reusable macro-memory only from verified successful work, compares no-memory/full-memory/retrieved-memory arms, and stops only on a confirmed frontier or a clean runtime boundary.

**Architecture:** Add one isolated experiment module owning the symbolic curriculum, append-only memory store, verified macro promotion, packet renderer, live runner, frontier logic, and evidence. Reuse `StrictFinalAnswerClient`, `ExperimentConfig`, `parse_packet_response`, record hashing, and Ollama. Experiment 006 and shared compiler behavior remain unchanged.

**Tech Stack:** Python stdlib, existing `alien_lab` scoring/Ollama utilities, `unittest`, JSON/JSONL.

**Spec:** `docs/superpowers/specs/2026-08-28-adaptive-external-memory-frontier-design.md`

## Global Constraints

- Fixed model/inference controls within a run.
- Every model call is stateless; only experiment-owned external memory persists.
- Bootstrap with 12 sealed rules; after that, only correctly solved retrieved-memory tasks may create macro-memory.
- Failed tasks never teach memory.
- No answer keys, choice ordering, or start-specific final values enter memory.
- Same challenge packet and model seed across `NONE`, `FULL`, and `RETRIEVED`.
- Primary frontier threshold is 7/8.
- One below-threshold packet is insufficient; fresh same-level confirmation must also fail.
- `UNSCORABLE` is never counted as wrong capability.
- Do not start a level unless wall-clock reserve covers all three matched arms plus safety margin.
- Do not silently truncate prompts; classify a conservative context cap before invocation.
- Existing Experiment 006 files remain unchanged.

---

### Task 1: Deterministic curriculum and verified learning

**Files:**
- Create: `tests/test_adaptive_memory_frontier.py`
- Create: `alien_lab/adaptive_memory_frontier.py`

**Interfaces:**
- Produces `MemoryRule`, `MemoryStore`, `MemoryTask`, `build_level_packet`, `render_memory_packet`, `composition_depth`, `promote_task_macros`, and `deterministic_preflight`.

- [ ] Write failing tests for seed stability, append-only memory, unique answers, prior-only memory use, exact arm isolation, successful macro equivalence, and failed-task non-promotion.
- [ ] Run `python3 -m unittest tests.test_adaptive_memory_frontier -v` and verify the red failure is the missing implementation.
- [ ] Implement affine bootstrap rules, recursive macro promotion from verified successes, eight-task packets, and `level + 2` composition depth.
- [ ] Re-run targeted tests and require PASS.

### Task 2: Scoring and confirmed adaptive frontier

**Files:**
- Modify: `tests/test_adaptive_memory_frontier.py`
- Modify: `alien_lab/adaptive_memory_frontier.py`

**Interfaces:**
- Produces `AdaptiveMemoryRunner.run()`, `_run_arm`, `confirmed_failure`, and summary fields.

- [ ] Add failing tests for strict parsing, same matched-arm seed, 7/8 threshold, two-packet confirmation, `UNSCORABLE` exclusion, and full-memory context-cap continuation.
- [ ] Implement two-call live preflight (`FULL`, `RETRIEVED`), three matched arms per level, same-level fresh confirmation, 3-bytes/token context guard, and P95 level-start reserve.
- [ ] Require successful retrieved packets to promote at least seven verified macros before advancing.
- [ ] Re-run targeted tests and require PASS.

### Task 3: Evidence and unattended configs

**Files:**
- Modify: `alien_lab/adaptive_memory_frontier.py`
- Create: `experiments/007-adaptive-memory-frontier/README.md`
- Create: `experiments/007-adaptive-memory-frontier/mistral-small-abliterated-24b.json`
- Create: `experiments/007-adaptive-memory-frontier/mistral-small-clean-24b.json`

**Interfaces:**
- CLI: `python3 -m alien_lab.adaptive_memory_frontier --config <path> [--preflight-only] [--output-dir <path>]`
- Evidence: `environment.json`, `preflight.json`, `memory.jsonl`, `runs.jsonl`, `observations.jsonl`, `summary.json`, `report.md`.

- [ ] Record every promoted macro with evidence task ID and memory fingerprint.
- [ ] Refuse output directories containing prior raw Experiment 007 evidence.
- [ ] Produce explicit frontier/context/time/max-level/integrity interpretations.
- [ ] Add abliterated and clean Mistral configs with identical controls except model tag.

### Task 4: Mandatory verification gate

- [ ] Run `python3 -m unittest tests.test_adaptive_memory_frontier -v`.
- [ ] Run `python3 -m unittest discover -s tests -v`.
- [ ] Run `python3 -m alien_lab.adaptive_memory_frontier --config experiments/007-adaptive-memory-frontier/mistral-small-abliterated-24b.json --preflight-only`.
- [ ] Start the unattended live experiment only if all three commands exit 0.
