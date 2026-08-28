# Experiment 007 — Adaptive External Memory Frontier

Experiment 007 measures how far a fixed stateless model can extend usable capability when only validated information from prior successful work is retained externally.

Every stage uses fresh challenge instances and three matched arms:

- `NONE` — no retained rule definitions.
- `FULL` — every validated learned rule is placed in the prompt.
- `RETRIEVED` — only rules referenced by the current packet are retrieved from the growing store.

The model receives no conversation history. Cross-stage learning exists only in the append-only memory store.

## Verified learning

The store starts with 12 sealed bootstrap rules. A correctly solved retrieved-memory task is deterministically compressed into a reusable affine macro representing the exact composition it solved. That macro is promoted only when the task was scored correct. Failed tasks cannot create memory.

Later stages deliberately mix old bootstrap memories with newly learned macro memories. The model therefore has to reuse validated information learned from earlier successful stages.

## One-hour accelerated frontier

The unattended launcher uses this preregistered composition-depth ladder:

```text
3, 5, 8, 12, 17, 23, 30, 38, 47, 57, 68, 80
```

Each number is the count of dependent external-memory rule applications required per task. There are 8 tasks per packet. The schedule is fixed before inference and never changes in response to model results.

This is deliberately more aggressive than the linear development runner so an approximately one-hour run has a realistic chance of reaching failure instead of spending the whole window below the model's frontier.

## Frontier and safety rules

- `RETRIEVED` always runs first; it is the primary measurement.
- `NONE` and `FULL` are controls and cannot turn a completed retrieved result into a failure.
- Retrieved memory passes at 7/8 or better.
- One retrieved miss does not define the frontier. A fresh same-difficulty packet must also fail.
- Confirmation runs before controls after a primary miss so controls cannot consume the frontier-confirmation reserve.
- `UNSCORABLE` is never counted as wrong.
- Failed tasks never teach memory.
- Prompt size is guarded before invocation to prevent silent context truncation.
- A legitimate `FULL` context/attention boundary does not stop `RETRIEVED`.
- The runner reserves measured P95 call time before starting work and stops cleanly when the remaining window is insufficient.

## Mandatory gate

Use the clean Experiment 007 branch and do not start the long run unless every command below exits 0:

```bash
python3 -m unittest tests.test_adaptive_memory_frontier -v
python3 -m unittest tests.test_adaptive_memory_frontier_accelerated -v
python3 -m unittest discover -s tests -v
python3 -m alien_lab.adaptive_memory_frontier_accelerated \
  --config experiments/007-adaptive-memory-frontier/mistral-small-abliterated-24b.json \
  --preflight-only
```

## Abliterated Mistral run

```bash
python3 -m alien_lab.adaptive_memory_frontier_accelerated \
  --config experiments/007-adaptive-memory-frontier/mistral-small-abliterated-24b.json \
  2>&1 | tee experiment-007-abliterated.log
```

## Clean Mistral comparator

```bash
python3 -m alien_lab.adaptive_memory_frontier_accelerated \
  --config experiments/007-adaptive-memory-frontier/mistral-small-clean-24b.json \
  2>&1 | tee experiment-007-clean.log
```

Use a separate result directory/config experiment ID for every rerun. Raw evidence is append-only and the runner refuses to mix a new run with existing `runs.jsonl`, `observations.jsonl`, or `memory.jsonl`.

Primary outputs are `environment.json`, `preflight.json`, `memory.jsonl`, `runs.jsonl`, `observations.jsonl`, `summary.json`, and `report.md`.
