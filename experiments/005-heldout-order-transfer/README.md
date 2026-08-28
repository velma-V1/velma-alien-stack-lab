# Experiment 005 — Held-out Order Transfer

Experiment 004 found that pass order changes both workspace semantics and verified capability on targeted order-sensitive tasks. Experiment 005 asks whether the candidate order transfers beyond those selection tasks.

## Candidate under test

`PATH -> RELEVANCE -> STATE -> UNCERTAINTY -> MEMORY -> PROCEDURE`

It is compared against:

- the original canonical order;
- the reverse candidate order;
- a relevance-first control.

All six primitives remain enabled in every arm.

## Controls held fixed within each replication

- model: `qwen3.5:9b-q8_0`
- quantization: Q8_0
- context: 25,600
- `think=false` through the Experiment 003 strict scorer
- output budget: 64
- task facts
- answer positions
- source ordering
- neural sampling seed

Only pass order changes.

## Held-out transfer stratum

Six new mixed-structure task families are repeated across six reshuffled seeds. None reuse the four Experiment 004 family names or task packets.

Three deliberately contain real scope/path/order interactions; three are broader controls where the candidate should not gain merely because the task was constructed around one dependency.

This stratum produces:

- 6 replications
- 4 orders
- 24 generations
- 144 scored task observations

## Legacy non-regression stratum

The repository's pre-existing six transfer tasks, which existed before Experiment 004 selected the candidate order, are run for two seeds under the same four orders.

This produces:

- 2 replications
- 4 orders
- 8 generations
- 48 scored task observations

## Promotion rule

The candidate is recommended for promotion only when all of the following are true:

1. all 32 generations are scorable and complete;
2. candidate held-out accuracy is higher than canonical held-out accuracy;
3. candidate beats canonical in at least 4 of 6 held-out replication packets;
4. candidate is non-inferior to canonical on the pre-existing transfer controls.

A semantic workspace difference alone is not enough.

## Run

From WSL at the repository root:

```bash
python3 -m unittest discover -s tests -v
```

Only after the suite passes:

```bash
python3 -m alien_lab.order_transfer \
  --config experiments/005-heldout-order-transfer/config.json
```

Results are written to `results/005-heldout-order-transfer/`:

- `preflight.json`
- `environment.json`
- `runs.jsonl`
- `observations.jsonl`
- `workspace_matrix.json`
- `summary.json`
- `report.md`

Do not rerun into the same output directory. Raw evidence is append-protected.
