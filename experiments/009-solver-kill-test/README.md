# Experiment 009 — Deterministic Solver Kill Test

## Question

Can independent deterministic computation recover enough capability from the exact public Experiment 008 representation to make **>=80% verified success on the 008 workload mathematically plausible**?

009 is deliberately narrow. It does **not** test another VELMA/Alien/OpenAdapt arrangement and it does not use an LLM.

## Why 009 exists

The intact Experiment 008 factorial produced:

| Architecture | Verified success | Model calls |
| --- | ---: | ---: |
| MODEL_ONLY | 17.97% | 128 |
| ALIEN | 19.53% | 128 |
| VELMA | 17.97% | 361 |
| OPENADAPT | 19.53% | 116 |
| ALIEN + OPENADAPT | 19.53% | 116 |
| VELMA + ALIEN + OPENADAPT | 19.53% | 347 |

The best tested architecture recovered only 2 additional tasks out of 128. That effect size is far too small to explain a path to 80%.

The 008 public task surface already exposes a formal dependency grammar:

```text
action=A09 requires=START condition=any
action=A01 requires=A09 condition=any
...
```

009 tests whether replacing stochastic rediscovery of those dependencies with exact computation changes capability by the required order of magnitude.

## Mathematical gate

Under the current 008 scorer, 428 of 2,976 cells are structurally incapable of verified success because silent-effect tasks force authoritative failure.

Therefore:

```text
solvable cells                 = 2548
full workload target           = 2381 successes (>=80%)
required solvable-cell rate    = 2381 / 2548 = 93.45%
```

009 uses **64 unseen solvable tasks**. Passing all 64 gives a 95% Wilson lower bound of approximately **94.34%**, above the required 93.45% solvable-cell rate.

The acceptance rule is intentionally hard:

```text
64 / 64 solvable tasks must achieve authoritative verified success
16 / 16 silent-fault controls must be correctly refuted
0 model calls
0 invalid evidence cells
Wilson 95% lower bound > 0.9345
```

One well-formed solvable miss kills the 009 hypothesis under this preregistered gate.

## What the solver is allowed to see

The solver receives only:

```python
task.public_dict()
```

That contains current public locators, labels, slots, policy markings, the public condition flag, family/stage metadata, and public initial state.

The solver does **not** receive:

- `required_semantics`;
- `oracle_final`;
- previous exact solution traces;
- model output;
- Alien memory;
- VELMA auditor output;
- OpenAdapt skill memory.

The sealed `TaskSpec` exists only inside the independent harness after the solver returns, where the existing 008 executor performs authoritative scoring.

## Solver computation

The solver:

1. strictly parses `action=... requires=... condition=...`;
2. rejects malformed labels and duplicate identities/bindings;
3. removes forbidden actions and `requires=NEVER` distractors;
4. evaluates public flag conditions;
5. constructs the predecessor graph;
6. requires exactly one legal successor at every step;
7. rejects ambiguity, cycles, missing predecessors, and disconnected eligible nodes;
8. emits the current locators in solved order.

This is a deterministic graph computation. There is no stochastic search.

## Kill ledger

The default configuration contains:

- **64 `SOLVABLE_KILL` cells**;
- **16 `SILENT_CONTROL` cells**;
- unseen seeds `20260901` through `20260916`;
- solvable families:
  - `linear_dependency`
  - `conditional_branch`
  - `multi_record_join`
  - `loop_worklist`
  - `policy_guard`
  - `composition`
  - `drift_resolution`
- stress stages:
  - `NOVEL`
  - `PARAMETER_VARIATION`
  - `DRIFT`
  - `COMPOSITION`
  - `TRANSFER`
- difficulty bands `12, 16, 20, 24, 28, 32`.

Silent controls alternate between the `silent_effect_fault` family and the lifecycle `SILENT_EFFECT_FAULT` stage. They must derive the public plan successfully but remain authoritatively refuted.

## Run

Checkout the experiment branch:

```bash
git fetch origin
git checkout experiment/009-solver-kill-test
git pull origin experiment/009-solver-kill-test
```

Run the unit/adversarial contract first:

```bash
python3 -m unittest tests.test_solver_kill_test -v
```

Then run the preregistered kill test:

```bash
python3 -m alien_lab.solver_kill_test \
  --config experiments/009-solver-kill-test/config.json \
  --output-dir results/009-solver-kill-test
```

The command exits:

- `0` — `PASS_SOLVER_HYPOTHESIS`;
- `4` — valid scientific failure / hypothesis killed or not proven;
- `2` — invalid configuration or harness/infrastructure failure.

## Evidence

The output directory contains:

```text
ledger.json
ledger-manifest.json
cells/*.json
summary.json
```

Every cell is SHA-256 sealed and records:

- public task;
- sealed oracle hash for identity only;
- solver derivation;
- emitted current locators;
- executed semantics from the independent 008 executor;
- screen success;
- authoritative success;
- verified success;
- final classification;
- model-call count (`0`).

Reusing an output directory with a different ledger raises:

```text
OUTPUT_DIRECTORY_LEDGER_MISMATCH
```

## Interpretation

### If 009 fails

Discard the current deterministic-solver hypothesis before building a generalized neurosymbolic architecture. The public 008 structure did not support the magnitude of exact capability recovery required.

### If 009 passes

A pass demonstrates that replacing model-only dependency reasoning with exact computation can produce the required order-of-magnitude capability change **on the exact 008 representation**.

It does **not** prove general intelligence.

The next valid experiment must attack representation dependence: preserve the underlying planning problems while paraphrasing, hiding, or changing the literal `requires=` grammar so a semantic compiler must construct the formal representation before the solver can operate.
