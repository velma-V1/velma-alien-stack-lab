# Experiment 004 — Order Effects

Experiment 003 established a valid scorer and showed that deterministic external cognition can change Qwen's capability. Experiment 004 asks a narrower question:

> With all six primitives held constant, does execution order change the model-facing workspace and verified task capability?

## Controlled variables

Held fixed across order arms within each replication:

- model: `qwen3.5:9b-q8_0`
- quantization: Q8_0
- context: 25,600
- `think=false` through the Experiment 003 strict scorer
- reasoning/output budget: 64
- task facts
- answer positions
- source ordering
- neural sampling seed
- all six primitives enabled

Only pass order changes.

## Orders

The experiment tests nine causally motivated full-stack orders rather than all 720 permutations. It includes:

- the current canonical order;
- the proposed `PATH -> RELEVANCE -> STATE -> UNCERTAINTY -> MEMORY -> PROCEDURE` order;
- its reverse;
- targeted reversals around PATH/RELEVANCE, RELEVANCE/STATE, RELEVANCE/UNCERTAINTY, and RELEVANCE/MEMORY;
- a procedure-first control.

## Stress tasks

Four answer-independent stress families are repeated across four reshuffled task seeds:

1. `order_path_relevance` — PATH must expose live-path-scoped evidence before RELEVANCE filters.
2. `order_relevance_state` — RELEVANCE must remove out-of-scope high-authority poisoning before STATE resolves current state.
3. `order_relevance_uncertainty` — RELEVANCE must remove an irrelevant equal-rank conflict before UNCERTAINTY materializes it.
4. `order_relevance_memory` — RELEVANCE must remove out-of-scope history before MEMORY constructs transitions.

This yields 9 orders × 4 replications = 36 model generations and 144 scored task observations, plus the three-packet scoring preflight.

## Integrity rule

A capability conclusion is valid only if:

- scoring preflight passes;
- all 36 order generations return `OK`;
- every order has all 16 expected scored observations;
- no generation is `UNSCORABLE` or time-aborted.

The experiment also computes semantic workspace signatures with pass timing/order metadata removed. A model-answer difference is not treated as a causal order effect unless order actually changes model-facing workspace semantics.

## Run

From WSL at the repository root:

```bash
python3 -m unittest discover -s tests -v
```

Only after the suite passes:

```bash
python3 -m alien_lab.order_effects \
  --config experiments/004-order-effects/config.json
```

Results are written to `results/004-order-effects/`:

- `preflight.json`
- `environment.json`
- `runs.jsonl`
- `observations.jsonl`
- `workspace_matrix.json`
- `summary.json`
- `report.md`

Do not rerun into the same output directory. Raw evidence is append-protected.
