# Experiment 007 — Adaptive External Memory Frontier

Experiment 007 measures how far a fixed stateless model can extend its usable capability when only validated information from prior successful work is retained externally.

Every level uses fresh challenge instances and three matched arms:

- `NONE` — no retained rule definitions.
- `FULL` — every validated learned rule is placed in the prompt.
- `RETRIEVED` — only the rules referenced by the current packet are retrieved from the growing store.

The model receives no conversation history. Cross-level learning exists only in the append-only memory store.

## Verified learning

The store starts with 12 sealed bootstrap rules. A correctly solved retrieved-memory task is deterministically compressed into a reusable affine macro rule representing the exact composition it solved. That macro is promoted only when the task was scored correct. Failed tasks cannot create memory.

Later levels deliberately mix old bootstrap memories with the newest learned macro memories. The model therefore has to reuse validated information learned from earlier successful levels.

## Difficulty and frontier

- 8 tasks per packet.
- Level 1 requires 3 memory-rule applications per task.
- Every next level adds one required composition step.
- The store grows only through successful work.
- Full-memory prompt clutter grows with the store; retrieved-memory prompt size tracks currently needed memories.
- Retrieved-memory passes at 7/8 or better.
- One miss does not define the frontier. The same difficulty is regenerated with a fresh seed and must fail again.
- `UNSCORABLE` is never counted as wrong.
- Prompt size is guarded before invocation to prevent silent context truncation.
- The runner stops cleanly between levels if its wall-clock reserve is insufficient for a complete matched level.

## Mandatory gate

From the repository root:

```bash
python3 -m unittest tests.test_adaptive_memory_frontier -v
python3 -m unittest discover -s tests -v
python3 -m alien_lab.adaptive_memory_frontier \
  --config experiments/007-adaptive-memory-frontier/mistral-small-abliterated-24b.json \
  --preflight-only
```

Do not start the long run unless all three commands exit 0.

## Abliterated Mistral run

```bash
python3 -m alien_lab.adaptive_memory_frontier \
  --config experiments/007-adaptive-memory-frontier/mistral-small-abliterated-24b.json \
  2>&1 | tee experiment-007-abliterated.log
```

## Clean Mistral comparator

```bash
python3 -m alien_lab.adaptive_memory_frontier \
  --config experiments/007-adaptive-memory-frontier/mistral-small-clean-24b.json \
  2>&1 | tee experiment-007-clean.log
```

Use a separate result directory/config experiment ID for every rerun. Raw evidence is append-only and the runner refuses to mix a new run with existing `runs.jsonl`, `observations.jsonl`, or `memory.jsonl`.

Primary outputs are `environment.json`, `preflight.json`, `memory.jsonl`, `runs.jsonl`, `observations.jsonl`, `summary.json`, and `report.md`.
