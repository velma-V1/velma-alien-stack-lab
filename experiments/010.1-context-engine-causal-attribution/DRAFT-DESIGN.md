# Experiment 010.1 — Superseded Draft

STATUS := SUPERSEDED_BY_PREREGISTRATION_V1
IMPLEMENTATION := ALLOWED_ON_ISOLATED_0101_BRANCH
LIVE_EXECUTION := FORBIDDEN_UNTIL_PARENT_010_C_D_TERMINAL_RECEIPT
SOURCE_OF_TRUTH := PREREGISTRATION-v1.md
BASE_COMMIT := a6c15dbffedf4441849d33b76d9ae66b12e33ae0

The earlier design draft has been superseded by:

1. `experiments/010.1-context-engine-causal-attribution/PREREGISTRATION-v1.md`
2. `experiments/010.1-context-engine-causal-attribution/Q0-Q36-DESIGN-ADJUDICATION.md`
3. `docs/superpowers/plans/2026-08-30-experiment-0101-context-engine-causal-attribution.md`

## Isolation contract

- Experiment 010 remains untouched.
- 010.1 implementation and credential-free mechanical CI may proceed only on `experiment/010.1-context-engine-causal-attribution`.
- No live 010.1 context-system/model/VELMA evidence is accepted until the preserved parent 010 C/D run reaches its frozen terminal count and a valid unlock receipt is supplied.
- No 010.1 merge into the active 010 branch is permitted during the parent run.
- Partial parent-010 results cannot alter 010.1 tasks, arms, splits, scoring, budgets, or composition-selection rules.

This file is retained only to prevent stale instructions from being treated as authoritative.