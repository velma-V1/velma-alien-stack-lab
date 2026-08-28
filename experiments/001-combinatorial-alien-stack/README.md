# Experiment 001 — Combinatorial Alien Stack

This run holds Qwen3.5-9B Q8_0 fixed and varies deterministic external-cognition primitives.

## Required discovery phase

The first phase always runs:

- one RAW six-task packet;
- every one of the 64 subsets of STATE, PATH, UNCERTAINTY, RELEVANCE, PROCEDURE, and MEMORY;
- six independent discovery tasks per subset.

That produces 384 Boolean-cube task observations plus six RAW observations from 65 model generations.

## Adaptive follow-up

If the rolling high-percentile generation time says work fits under the one-hour ceiling, the runner spends remaining time on:

1. held-out single-task transfer;
2. neural-compute substitution;
3. pass-order reversals;
4. batched-vs-single transfer control;
5. antagonistic compound control;
6. fresh-seed evidence/answer-order perturbation.

The absolute ceiling is 60 minutes. A time-budget abort is logged separately and is not scored as a model failure.

## Before the real run

From WSL in the repository:

```bash
curl -s http://localhost:11434/api/tags | head
```

If that returns Ollama JSON, run:

```bash
python3 -m alien_lab.experiment \
  --dry-run \
  --config experiments/001-combinatorial-alien-stack/config.json
```

Then execute:

```bash
python3 -m alien_lab.experiment \
  --config experiments/001-combinatorial-alien-stack/config.json
```

If WSL cannot reach Windows Ollama on `localhost`, do not run the experiment yet. Set `ollama_url` in `config.json` to a reachable Windows Ollama endpoint and rerun the connectivity check first.

## Output

The run writes to `results/001-combinatorial-alien-stack/` by default:

- `tasks.public.json` — public task packet;
- `sealed/answers.json` — evaluator artifact generated locally for this frozen run;
- `runs.jsonl` — immutable generation-level evidence;
- `observations.jsonl` — per-task counterfactual observations;
- `summary.json` — aggregate metrics and causal analysis;
- `compound_registry.json` — transferred compound status;
- `report.md` — human-readable four-ledger report.

Do not edit raw run evidence after generation. Corrections or auditor labels should be additive artifacts referencing run IDs.
