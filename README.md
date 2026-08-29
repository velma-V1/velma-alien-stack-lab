# velma-alien-stack-lab

Experimental laboratory for discovering how much verified capability and neural computation can be moved out of a fixed local model into deterministic, composable external cognition.

The lab treats existing AI architecture as a source of primitives and controls, not as a ceiling. Candidate mechanisms are tested alone, in compounds, in different orders, under ablation, on held-out tasks, and against compute budgets. Discovery results cannot certify themselves or modify V31M4 production architecture.

## Current experimental findings

### Experiment 007 — adaptive external-memory frontier

The repaired real-Ollama run produced scientifically usable paired evidence for **6 of 8 installed models**. The two tested 24B models produced zero paired packets because repeated generations hit the run output ceiling; they are **unscorable, not capability losers**.

The six valid downstream candidates were:

- `qwen3.5:9b`
- `qwen3.5:9b-q8_0`
- `qwen3:8b`
- `gemma3:12b`
- `qwen3:14b`
- `qwen2.5-coder:14b`

The preregistered 008 selection path chose `qwen3.5:9b-q8_0` as the highest-ranked valid 007 candidate that also passed the independent 008 live capability gate.

See [`experiments/007-adaptive-memory-frontier/RESULTS-2026-08-29.md`](experiments/007-adaptive-memory-frontier/RESULTS-2026-08-29.md).

### Experiment 008 — architecture discovery

The full **2,976-cell** ledger executed. Final evidence status:

- **2,970 valid/scored cells**
- **6 `OUTPUT_CAP_REACHED` cells**
- **0 missing cells**
- **0 orphan evidence cells**
- **0 recovered corrupt evidence files**
- `execution_complete = true`
- `experiment_complete_valid = false`
- `conclusion_status = PARTIAL_INVALID_EVIDENCE`

The six invalid observations were caused by a stale **128-token output budget** in the executed 008 configuration. No post-hoc rerun or repair is being used to convert this into a globally valid result.

Two major preregistered subexperiments are intact because they contain **zero invalid cells**:

1. the complete 2×2×2 component factorial; and
2. the complete lifecycle experiment.

The lifecycle analysis left two tested complete topologies on the Pareto frontier:

- `Alien=POST_PLAN_REFINE | OpenAdapt=AFTER_PLAN_LOOKUP_POSTVERIFY_COMPILE | VELMA=PRE_EXEC_AUDIT`
- `Alien=PRE_REASON | OpenAdapt=EARLY_LOOKUP_POSTVERIFY_COMPILE | VELMA=BOTH`

The run also measured `model_dependence_ratio = 0.9919191919191919`, showing that the current architecture still relied on at least one model call in about **99.19% of valid cells**. This points future work toward substantially more verified deterministic reuse rather than simply adding more inference layers.

The exact capability frontier remains unresolved because 4 frontier observations were output-cap-invalid. Two placement negative-control observations were also unscorable, so a completely clean placement ranking is not claimed.

See [`experiments/008-architecture-discovery/RESULTS-2026-08-29.md`](experiments/008-architecture-discovery/RESULTS-2026-08-29.md).

## Experiment 001

`experiments/001-combinatorial-alien-stack/` holds Qwen3.5-9B Q8_0 fixed and exhaustively evaluates the six-primitive Boolean cube before using remaining time for transfer, order, batching, antagonism, perturbation, and reasoning-budget tests.

Dry-run the plan:

```bash
python3 -m alien_lab.experiment \
  --dry-run \
  --config experiments/001-combinatorial-alien-stack/config.json
```

See `experiments/001-combinatorial-alien-stack/README.md` before the model run.
