# Experiment 006 — Capability Frontier

Experiment 004 showed that pass order can change Qwen capability on order-sensitive stress tasks. Experiment 005 then showed a ceiling: candidate and canonical both reached 100% even though their compiled workspaces were semantically different.

Experiment 006 tests the compensation hypothesis directly:

> As deterministic workspace defects become larger and more numerous, does Qwen stop being able to repair the canonical workspace before it stops being able to solve the candidate workspace?

## Orders under test

Only two neural arms are compared:

- canonical: `STATE -> PATH -> UNCERTAINTY -> RELEVANCE -> PROCEDURE -> MEMORY`
- candidate: `PATH -> RELEVANCE -> STATE -> UNCERTAINTY -> MEMORY -> PROCEDURE`

All six primitives remain enabled. The candidate is not promoted by construction.

## Difficulty frontier

Five pre-registered difficulty levels are tested. Each level contains six task families:

1. `frontier_path_state`
2. `frontier_scope_conflict`
3. `frontier_history`
4. `frontier_multi_key`
5. `frontier_path_scope`
6. `frontier_compound`

Difficulty rises monotonically by increasing active-path depth, inactive branches, cross-scope high-authority records, unrelated keys, revision history, and irrelevant evidence. The underlying decision rules do not change with level.

Within every level/replication pair, canonical and candidate receive identical task facts, answer positions, source order, model seed, model, context, and generation budget. Only pass order changes.

Four reshuffled replications are used per level:

- 5 levels
- 4 replications
- 2 orders
- 40 neural generations
- 240 scored task observations

The Experiment 003 strict scorer remains in force with `think=false` and exact packet-only final answers.

## Deterministic compiler audit

Before the neural frontier run, Experiment 006 scores the compiler itself.

For every task, sealed expected IR facts specify:

- exact active path;
- expected target current state;
- expected target uncertainty;
- required and forbidden visible evidence;
- expected target memory transitions when applicable.

All **720 permutations** of the six passes are compiled and scored without Qwen. This separates compiler correctness from model compensation and gives candidate/canonical deterministic ranks.

The full deterministic table is written to `deterministic_permutation_scan.json`.

## Interpretation

`candidate_frontier_supported=true` requires all of the following:

1. all 40 neural generations are complete and scorable;
2. candidate deterministic workspace accuracy exceeds canonical;
3. candidate aggregate neural accuracy exceeds canonical;
4. candidate wins more matched level/replication packets than it loses.

The report also records:

- first level where candidate beats canonical;
- first error level for each order;
- per-level accuracy;
- packet wins/losses;
- all-720 deterministic ranking.

If both neural arms remain perfect through Level 5, the correct result is **frontier not reached**, not equivalence of the compiler orders.

## Run

From WSL at the repository root:

```bash
python3 -m unittest discover -s tests -v
```

Only after the suite passes:

```bash
python3 -m alien_lab.capability_frontier \
  --config experiments/006-capability-frontier/config.json
```

Results are written to `results/006-capability-frontier/`.

Do not rerun into the same output directory. Raw evidence is append-protected.
