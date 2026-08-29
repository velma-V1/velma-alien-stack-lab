# Experiment 009 — Solver Kill Test Design

## Purpose

Experiment 009 is a falsification test for one claim only:

> An independent deterministic solver that consumes only the public Experiment 008 task surface can recover enough capability on unseen solvable tasks to make a path to at least 80% verified success mathematically plausible.

009 is not a VELMA, Alien, OpenAdapt, prompting, memory, or model-selection experiment. It must not use an LLM on the solver path.

## Why this test exists

The intact 008 factorial showed only a two-task gain over MODEL_ONLY at best: MODEL_ONLY solved 23/128 cells (17.97%), while Alien, OpenAdapt, Alien+OpenAdapt, and the full VELMA+Alien+OpenAdapt stack solved 25/128 (19.53%). VELMA alone remained at 23/128 while using substantially more model calls.

The current 008 generator also exposes a formal dependency grammar on the public surface: each action label contains `action=`, `requires=`, and `condition=` fields; current locators and forbidden-policy markings are public. The solver-kill hypothesis is therefore that exact computation should replace stochastic rediscovery of those dependencies.

## Mathematical acceptance threshold

The current 008 ledger contains 2,976 cells. Under the executed scorer, 428 cells are structurally incapable of verified success because `silent_effect_fault` tasks and lifecycle `SILENT_EFFECT_FAULT` stages force authoritative failure even when the semantic plan is correct.

Therefore:

- solvable ceiling: 2,548 / 2,976 = 85.62%;
- required successes for 80% overall: 2,381;
- required success rate on solvable cells: 2,381 / 2,548 = 93.45%;
- maximum allowable solvable misses at full scale: 167.

009 uses a 64-cell unseen solvable kill set. A 64/64 result has a 95% Wilson lower bound of approximately 94.34%, which is above the 93.45% solvable rate required by the full-workload target.

## Scientific contract

### Solver inputs

The solver may receive only `TaskSpec.public_dict()` or a lossless serialization of that public object.

It must not read or derive behavior from:

- `TaskSpec.required_semantics`;
- `TaskSpec.oracle_final`;
- `TaskSpec.oracle_hash` except for evidence identity after execution;
- private generator state;
- prior exact solution traces;
- model output.

The harness may retain the sealed `TaskSpec` only to execute and score the plan independently after the solver returns locators.

### Solver output

The solver returns:

- an ordered tuple/list of current public locators;
- a deterministic derivation trace containing the parsed action id, predecessor, condition, locator, and exclusion reason for discarded distractors;
- an explicit failure code if the public problem is malformed, ambiguous, cyclic, or unsatisfiable.

### Allowed computation

Only deterministic parsing, validation, graph traversal, condition evaluation, and locator binding are allowed in 009.

No LLM, embeddings, retrieval, memory, learned reranker, stochastic search, or oracle lookup is allowed.

## Public-surface grammar

For the current 008 task generator, each public action exposes a label with this grammar:

`action=<ID> requires=<PREDECESSOR> condition=<CONDITION>`

Relevant values include:

- root predecessor: `START`;
- distractor predecessor: `NEVER`;
- condition: `any` or `flag=<0|1>`;
- public policy: `forbidden=true|false`;
- current executable binding: `locator=<current locator>`.

The solver must parse the grammar exactly. It must reject malformed or duplicate semantic definitions rather than infer missing meaning.

## Deterministic solver algorithm

1. Parse every public action label into a typed node.
2. Reject duplicate action ids or duplicate current locators.
3. Exclude nodes marked forbidden.
4. Exclude `requires=NEVER` distractors.
5. Exclude nodes whose condition does not match `public_flag`.
6. Require exactly one reachable root with `requires=START`.
7. Build a predecessor-to-successor mapping over eligible nodes.
8. Walk from `START`, requiring exactly one successor at every step.
9. Stop when no eligible successor remains.
10. Reject cycles, ambiguity, missing predecessor references, or disconnected eligible nodes.
11. Emit the walked nodes' current locators in order.

The solver is deliberately minimal. 009 is a kill test of formal computation, not a generalized planner implementation.

## Kill-set construction

009 generates 64 unseen solvable tasks from seeds not used by 008. The set is fixed and sealed by configuration before execution.

Stratification:

- 8 task families excluding `silent_effect_fault`;
- 7 solvable families total: `linear_dependency`, `conditional_branch`, `multi_record_join`, `loop_worklist`, `policy_guard`, `composition`, `drift_resolution`;
- stages emphasize `NOVEL`, `PARAMETER_VARIATION`, `DRIFT`, `COMPOSITION`, and `TRANSFER`;
- difficulty emphasizes 12, 16, 20, 24, 28, and 32;
- all tasks use unseen seeds and isolated lineages.

The generator must deterministically fill exactly 64 solvable cells while balancing families, stages, and difficulty bands as evenly as possible.

## Silent-fault controls

009 also runs 16 controls that use either the `silent_effect_fault` family or lifecycle `SILENT_EFFECT_FAULT` stage.

These controls do not count toward the 64-cell capability threshold. Their purpose is to prove that the solver/harness does not launder screen success into verified success.

Expected result for every control:

- the solver should still derive the correct public plan;
- execution may report screen success;
- authoritative verification must remain false;
- the test must classify the control as `EXPECTED_REFUTATION`, never `SOLVER_SUCCESS`.

## Acceptance and kill rules

### PASS

009 passes only if all conditions hold:

1. exactly 64 solvable kill cells execute;
2. 64/64 achieve authoritative verified success;
3. solver model-call count is exactly zero;
4. no task uses sealed oracle fields as solver input;
5. every emitted locator exists on the current public surface;
6. all 16 silent-fault controls are correctly refuted;
7. the full evidence ledger is complete, deterministic, and hash-sealed;
8. rerunning the same profile produces identical task ids, plans, derivations, and classifications.

### KILL

The architecture hypothesis is killed if any well-formed solvable task fails because the deterministic solver cannot derive the exact executable plan from the permitted public surface.

Infrastructure or harness corruption is not converted into a solver failure; it is reported separately as invalid evidence.

## Evidence format

Each cell stores:

- cell id/order;
- phase (`SOLVABLE_KILL` or `SILENT_CONTROL`);
- public task only;
- oracle hash for sealed identity only;
- solver derivation;
- solver locators;
- executed semantics returned by the independent 008 executor;
- screen success;
- authoritative success;
- verified success;
- classification;
- solver model calls, fixed at zero;
- SHA-256 envelope.

Summary fields include:

- expected/terminal/valid cells;
- solvable successes and failures;
- solvable success rate;
- Wilson 95% interval;
- silent controls correctly refuted;
- model calls;
- deterministic replay fingerprint;
- `solver_kill_test_passed`.

## Scope boundary

A PASS means only that deterministic formal computation has the required order-of-magnitude effect on the exact 008 public representation.

It does not prove general intelligence or semantic formalization ability. A PASS authorizes a subsequent representation-generalization experiment in which the literal dependency grammar is paraphrased or removed while the underlying planning problem remains equivalent.
