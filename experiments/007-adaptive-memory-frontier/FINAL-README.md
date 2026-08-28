# Experiment 007 — Final Model / External-Memory Frontier

This is the final broad diagnostic runner for the alien-stack external-memory work.

## What it measures

Every configured model completes the full 48-level ladder. A wrong answer, a failed level, a later recovery, a context cap in FULL memory, malformed output, or exhausted retries is recorded as data and does not terminate the remaining model suite.

Each level contains two independent six-task variants. Each variant is run in matched conditions:

- `NONE`: base rulebook only; no learned macro memory.
- `FULL`: base rulebook plus the complete validated learned-macro store.
- `RETRIEVED`: base rulebook plus only learned macros actually selected by deterministic compilation for that packet.

The underlying base facts are identical across arms. This avoids confounding "no memory" with missing problem information.

Correct RETRIEVED tasks may teach exact reusable macro transformations. Failed or unscorable tasks never teach. The memory store is append-only and all macro records carry deterministic provenance/fingerprints.

The runner records first miss, first below-threshold level, last passing level, sustained-collapse boundary, recovery levels after failure, paired RETRIEVED-vs-NONE gain and confidence interval, memory growth, prompt/token/latency cost, raw-vs-compiled steps, context caps, format/infrastructure failures, retries, and raw per-task evidence.

## Titan

After every model finishes all 48 levels, Titan always runs the same held-out deterministic program at three frozen-memory budgets:

1. `TITAN_NONE` — zero learned macro memory.
2. `TITAN_LIMITED` — 12 learned macros (or all if fewer than 12 were earned).
3. `TITAN_MAX` — the entire frozen learned-memory store, subject to the explicit context guard.

Titan contains 8 registers, 40 memory-backed transformations, 8 cross-register joins, 4 conditional branches, and 3 nested dependency joins (55 operations minimum). It is labeled a **70–100B-class target difficulty**, not a proven parameter-class equivalence benchmark.

## Resilience

- Three retries per model call.
- Context overflow is recorded, never silently truncated.
- Model-level catastrophe is recorded and the suite proceeds to the next model.
- Atomic checkpoint after every completed variant.
- Rerunning the same output directory resumes from the next unfinished variant.
- A completed model returns its existing final summary instead of duplicating evidence.
- No overall wall-clock ceiling terminates the scientific run.

## Pre-run verification

```bash
python3 -m unittest tests.test_final_memory_frontier -v
python3 -m alien_lab.final_memory_frontier --audit-only
```

Both must be green before live inference.

## Run the complete suite

```bash
python3 -m alien_lab.final_memory_frontier \
  --config experiments/007-adaptive-memory-frontier/final-suite.json \
  --output-dir results/007-final-model-memory-frontier
```

The runner executes configured models sequentially, one complete model at a time.

Model names are deliberately configuration-driven. If an Ollama tag differs on the target host, correct only that model's `model` field; do not change seeds, difficulty, task counts, arm definitions, or scoring logic after live evidence begins.
