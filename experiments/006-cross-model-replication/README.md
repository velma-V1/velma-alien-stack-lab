# Experiment 006 — Cross-model replication

This directory reuses the frozen Experiment 006 capability-frontier code without changing task generation, scoring, compiler behavior, pass orders, context, seeds, or generation budgets.

The scientific question is whether the candidate external-cognition order extends the usable capability frontier across model families and scales, not only for `qwen3.5:9b-q8_0`.

## Frozen controls

Every replica keeps:

- context limit: 25,600
- temperature: 0.0
- seed: 20260828
- output/reasoning budget: 64
- five frontier difficulty levels
- four replications per level
- canonical order: `STATE -> PATH -> UNCERTAINTY -> RELEVANCE -> PROCEDURE -> MEMORY`
- candidate order: `PATH -> RELEVANCE -> STATE -> UNCERTAINTY -> MEMORY -> PROCEDURE`
- Experiment 003 strict scoring with `think=false`
- identical deterministic 720-permutation compiler audit

Only the Ollama model tag changes. Wall-clock ceilings are enlarged for heavier models solely to avoid classifying slower inference as a capability failure.

## Run order

1. `gemma3:12b` — independent-family replication
2. `devstral-small-2:24b` — independent-family + larger-model replication
3. `qwen3:8b` — smaller Qwen frontier sensitivity
4. `qwen3:14b` — larger Qwen transfer
5. `qwen2.5-coder:14b` — specialized Qwen transfer
6. `qwen3.5:9b` — quantization/build sensitivity against the existing Q8 baseline
7. `huihui_ai/mistral-small-abliterated:24b` — modified-model robustness probe; interpret separately from clean family replication

The original `qwen3.5:9b-q8_0` Experiment 006 result remains the baseline and is not rerun or overwritten.

## Commands

Run the full unit suite after switching to this branch. Then invoke `alien_lab.capability_frontier` with exactly one model config at a time.

Each config has a unique `experiment_id`, so results are written to separate directories under `results/` and cannot overwrite the Qwen3.5 Q8 baseline or each other.
