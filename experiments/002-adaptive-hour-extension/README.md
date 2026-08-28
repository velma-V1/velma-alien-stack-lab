# Experiment 002 — Adaptive Hour Extension

This experiment fixes the under-utilization discovered after Experiment 001.
It **does not repeat** Experiment 001's 172-generation finite queue.

Instead it:

1. reads Experiment 001's frozen `summary.json`, `environment.json`, and `runs.jsonl`;
2. verifies model, quantization, and context compatibility;
3. subtracts Experiment 001 elapsed time from the cumulative 55-minute target and 60-minute ceiling;
4. spends the remaining time on new complete 64-subset Boolean-cube replications;
5. uses the original held-out transfer set first, then alternates fresh-seed discovery/transfer task packets;
6. uses short paired RAW/STRUCTURED/winner/full/fusion/recursive/positive/negative controls when another complete 65-generation cube will not fit safely.

Run from WSL at the repository root:

```bash
python3 -m alien_lab.extension \
  --config experiments/002-adaptive-hour-extension/config.json \
  --extend-from results/001-combinatorial-alien-stack
```

New evidence is written to `results/002-adaptive-hour-extension/`.
Experiment 001 remains untouched and is referenced by hash in `prior_evidence.json`.
