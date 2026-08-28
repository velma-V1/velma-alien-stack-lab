# velma-alien-stack-lab

Experimental laboratory for discovering how much verified capability and neural computation can be moved out of a fixed local model into deterministic, composable external cognition.

The lab treats existing AI architecture as a source of primitives and controls, not as a ceiling. Candidate mechanisms are tested alone, in compounds, in different orders, under ablation, on held-out tasks, and against compute budgets. Discovery results cannot certify themselves or modify V31M4 production architecture.

## Experiment 001

`experiments/001-combinatorial-alien-stack/` holds Qwen3.5-9B Q8_0 fixed and exhaustively evaluates the six-primitive Boolean cube before using remaining time for transfer, order, batching, antagonism, perturbation, and reasoning-budget tests.

Dry-run the plan:

```bash
python3 -m alien_lab.experiment \
  --dry-run \
  --config experiments/001-combinatorial-alien-stack/config.json
```

See `experiments/001-combinatorial-alien-stack/README.md` before the model run.
