# Adaptive External Memory Frontier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Experiment 007: an adaptive, increasingly difficult external-memory benchmark that grows learned memory across stateless model calls, compares no-memory/full-memory/retrieved-memory arms, and stops only on a confirmed frontier or a clean runtime boundary.

**Architecture:** Add one isolated experiment module that owns the symbolic rule curriculum, append-only memory store, packet renderer, live runner, frontier logic, and summary generation. Reuse the existing `StrictFinalAnswerClient`, `ExperimentConfig`, `parse_packet_response`, record hashing helpers, and Ollama client. Do not modify Experiment 006 or shared compiler behavior.

**Tech Stack:** Python stdlib, existing `alien_lab` experiment/scoring/Ollama utilities, `unittest`, JSON/JSONL evidence.

**Spec:** `docs/superpowers/specs/2026-08-28-adaptive-external-memory-frontier-design.md`

## Global Constraints

- Fixed model and inference controls within a run.
- Every model call is stateless; only the experiment-owned external memory persists.
- No answer keys, choice ordering, or task-specific final values may enter memory.
- Same challenge packet and model seed across `NONE`, `FULL`, and `RETRIEVED` arms.
- Primary frontier threshold is 7/8 correct.
- One below-threshold packet is insufficient; a fresh same-level confirmation must also fail.
- `UNSCORABLE` is never counted as wrong capability.
- Do not start a level unless wall-clock budget can cover all three matched arms plus safety margin.
- Do not silently truncate prompts; classify a conservative context cap before invocation.
- Existing Experiment 006 files remain unchanged.

---

### Task 1: Deterministic curriculum, memory store, and render isolation

**Files:**
- Create: `tests/test_adaptive_memory_frontier.py`
- Create: `alien_lab/adaptive_memory_frontier.py`

**Interfaces:**
- Produces `MemoryRule`, `MemoryStore`, `MemoryTask`, `build_level_packet`, `render_memory_packet`, `composition_depth`, and `deterministic_preflight`.

- [ ] **Step 1: Write failing tests** proving seed stability, monotonic difficulty, unique answers, prior-acquired-rule use, append-only memory fingerprints, and exact arm isolation.
- [ ] **Step 2: Run** `python3 -m unittest tests.test_adaptive_memory_frontier -v`; expected failure is missing `alien_lab.adaptive_memory_frontier`.
- [ ] **Step 3: Implement minimal deterministic curriculum and memory renderer** using affine rules `(a*x+b) mod 97`, 12 bootstrap rules, 12 rules acquired per completed level, eight tasks per packet, and composition depth `level + 2`.
- [ ] **Step 4: Re-run the targeted test**; expected PASS.
- [ ] **Step 5: Commit** test plus deterministic implementation.

### Task 2: Scoring preflight, matched arms, and confirmed frontier

**Files:**
- Modify: `tests/test_adaptive_memory_frontier.py`
- Modify: `alien_lab/adaptive_memory_frontier.py`

**Interfaces:**
- Produces `AdaptiveMemoryRunner.run()`, `_run_arm`, `_confirm_failure`, and `summary`.
- Consumes `StrictFinalAnswerClient`, `ExperimentConfig`, `parse_packet_response`, and `OllamaClient`.

- [ ] **Step 1: Add failing tests** for exact packet parsing, `UNSCORABLE` exclusion, same model seed across matched arms, 7/8 pass threshold, two-packet failure confirmation, full-memory context-cap continuation, and time-budget clean stop between levels.
- [ ] **Step 2: Run targeted tests** and verify they fail on missing runner behavior.
- [ ] **Step 3: Implement minimal runner** with two-call live scoring preflight (`FULL`, `RETRIEVED`), three matched arms per level, fresh confirmation packet only after a retrieved-memory miss, conservative 3-bytes/token pre-call context guard, and P95 level-start budget check.
- [ ] **Step 4: Re-run targeted tests**; expected PASS.
- [ ] **Step 5: Commit** runner behavior.

### Task 3: Evidence, summary, and unattended configs

**Files:**
- Modify: `tests/test_adaptive_memory_frontier.py`
- Modify: `alien_lab/adaptive_memory_frontier.py`
- Create: `experiments/007-adaptive-memory-frontier/README.md`
- Create: `experiments/007-adaptive-memory-frontier/mistral-small-abliterated-24b.json`
- Create: `experiments/007-adaptive-memory-frontier/mistral-small-clean-24b.json`

**Interfaces:**
- CLI: `python3 -m alien_lab.adaptive_memory_frontier --config <path> [--preflight-only] [--output-dir <path>]`
- Evidence: `environment.json`, `preflight.json`, `memory.jsonl`, `runs.jsonl`, `observations.jsonl`, `summary.json`, `report.md`.

- [ ] **Step 1: Add failing tests** for append-only output refusal, required summary fields, interpretation strings, memory snapshot fingerprints, and CLI preflight behavior.
- [ ] **Step 2: Run targeted tests** and verify failure.
- [ ] **Step 3: Implement evidence writers and CLI**, keeping historical raw evidence append-only and producing a human-readable report.
- [ ] **Step 4: Run** `python3 -m unittest discover -s tests -v`; expected full suite PASS.
- [ ] **Step 5: Run preflight-only locally** against the intended model before any long run.
- [ ] **Step 6: Commit** docs/config/evidence layer.

### Task 4: Verification gate before unattended live run

**Files:**
- No production changes unless verification identifies a defect.

- [ ] **Step 1: Run** `python3 -m unittest discover -s tests -v` and require all tests PASS.
- [ ] **Step 2: Run** `python3 -m alien_lab.adaptive_memory_frontier --config experiments/007-adaptive-memory-frontier/mistral-small-abliterated-24b.json --preflight-only`; require deterministic and live preflight PASS.
- [ ] **Step 3: Inspect generated preflight output** for model tag, context 25600, temperature 0, 64-token output budget, no thinking, and both memory render modes parseable.
- [ ] **Step 4: Only then start the unattended live experiment.**
