# Combinatorial Alien-Stack Experiment Design

## Purpose

This repository is an experimental laboratory for discovering architectures that can move the effective capability boundary of a fixed local model. Existing AI patterns are controls and primitives, not architectural authorities.

The first experiment asks:

> How much verified capability and neural compute can be gained or replaced by deterministic external cognition, which primitives cause those gains, and which compounds create effects that no primitive produces alone?

The experiment must support both immediate causal analysis and a durable evidence base for later self-improvement.

## Fixed experimental subject

- Model: `qwen3.5:9b-q8_0`
- Runtime: Ollama HTTP API
- Primary context: 25,600 tokens, intentionally below the measured 26,592 all-GPU boundary
- Temperature: 0
- Seed: fixed per run
- Model is never allowed to certify its own result
- Expected answers are evaluator-only data and are unavailable to compiler passes and model prompts

## Scientific doctrine

Every candidate mechanism must answer four ledgers:

1. **Capability** — did verified task performance improve?
2. **Compute** — what neural and deterministic compute did the improvement cost?
3. **Causality** — which primitive or interaction caused the change?
4. **Generalization** — did the effect survive held-out task families?

A mechanism earns admission only if it improves verified capability or materially reduces neural computation at equal capability after accounting for deterministic cost.

## Six model-facing cognition primitives

The initial Boolean cube contains six independently switchable deterministic primitives.

### A — STATE
Resolve authoritative current state from competing records using authority and revision. If the highest-ranked state cannot be resolved safely, do not invent a value.

### B — PATH
Derive the active execution/dependency path from typed graph edges.

### C — UNCERTAINTY
Surface unresolved equal-authority/equal-revision contradictions explicitly instead of allowing the model to silently choose one.

### D — RELEVANCE
Prune evidence unrelated to the active scope and task target using deterministic scope/graph relationships, not evaluator labels or expected answers.

### E — PROCEDURE
Compile known decision rules into a concise task-specific procedure. This is a local text-skill analogue: it externalizes procedural bookkeeping but does not choose the final answer.

### F — MEMORY
Compile relevant state transitions and superseded-history deltas so the model can distinguish current state from historical state and reason about migration/change direction.

## Always-on instrumentation, not experimental privileges

These are recorded for every arm but are not model-facing powers unless an experiment explicitly promotes them later:

- source provenance
- compiler-pass provenance
- hashes of source observations and compiled workspaces
- discarded evidence
- unresolved contradictions
- derived facts
- pass order
- deterministic CPU time
- model prompt/generation metrics
- raw model thinking and response

## Controls

### RAW
Original evidence in intentionally ordinary project form. No compiler derivation.

### STRUCTURED / empty-set control
The exact same evidence normalized into typed sections with zero cognition primitives enabled. This separates formatting/serialization effects from external cognition.

### Deterministic-only ceiling
The harness records whether deterministic compilation alone uniquely determines the answer. Such cases remain useful but are classified separately and cannot be claimed as neural capability augmentation.

## Phase 1 — exhaustive compound discovery

Run the complete power set of the six primitives:

- empty set
- all 6 singles
- all 15 pairs
- all 20 triples
- all 15 four-way compounds
- all 6 five-way compounds
- full six-way stack

Total: 64 structured arms, plus RAW.

The scheduler runs one or more discovery-task replicates depending on measured local throughput and the wall-clock budget.

This phase enables exact analysis over the Boolean cube rather than hand-picked ablations.

## Compound mathematics

For capability, tokens, time, and other scalar metrics, compute:

- primitive main effects
- leave-one-in and leave-one-out effects
- pair interactions
- higher-order Möbius interaction coefficients
- exact Shapley contributions for six primitives
- minimal sufficient subsets
- Pareto frontier: capability vs neural tokens vs wall time vs deterministic cost
- antagonistic primitives and compounds
- superadditive compounds
- full-stack ablations

A compound is considered emergent only when its measured effect exceeds what its constituents predict and the effect transfers to held-out tasks.

## Recursive compound registry

Positive compounds are assigned stable IDs, e.g. `C001`, with:

- constituent primitives
- canonical order
- discovery interaction strength
- transfer score
- compute profile
- task families helped/hurt
- failure classes changed
- provenance to all supporting runs

The registry is intentionally recursive: a confirmed compound may become an input primitive in a later experiment, allowing tests such as `A+B -> C001`, `C+C001 -> C002`, and `A+C001+C002 -> C003` without treating the original architecture as sacred.

## Phase 2 — held-out transfer

Select candidate compounds using a diversity-aware Pareto rule, not accuracy alone. Transfer candidates must include:

- RAW
- STRUCTURED
- full stack
- best minimal compound
- best capability compound
- best efficiency compound
- strongest positive-interaction compound
- one deliberately weak/antagonistic control when time permits

Run them on held-out tasks from different task families.

Discovery and transfer tasks must be frozen before results are inspected.

## Phase 3 — order effects

Subset membership does not prove order invariance. For the strongest interacting primitive pairs, test both orders on held-out order-sensitive tasks.

Examples:

- `PATH -> RELEVANCE` vs `RELEVANCE -> PATH`
- `STATE -> PROCEDURE` vs `PROCEDURE -> STATE`
- `UNCERTAINTY -> PROCEDURE` vs `PROCEDURE -> UNCERTAINTY`

Record order effects separately from subset effects.

## Phase 4 — neural-compute substitution

Compare selected challenge tasks under deliberately unequal reasoning budgets:

- RAW at a large budget
- STRUCTURED at a medium budget
- best confirmed compound at a small budget
- full stack at a small budget

The strongest immediate evidence for external cognition is:

`compound@small >= RAW@large` in verified capability while STRUCTURED@small remains weaker and deterministic preprocessing cost is negligible relative to saved neural compute.

## Task families

The task suite must contain multiple independently generated or frozen instances from at least these families:

1. authority + temporal supersession
2. active-path/dependency reasoning
3. unresolved-authority conflict
4. cross-source semantic repair
5. migration/change-direction reasoning
6. side-effect / safety-property reasoning

Tasks use randomized answer positions and opaque project/entity names where appropriate to reduce shortcut learning.

The compiler sees typed observations but never expected answers.

## Anti-cheating and leakage controls

- answers live in a separate sealed evaluator artifact
- compiler APIs accept answer-free task objects only
- answer file is opened only after model generation for scoring
- no compiler pass may inspect answer choices to derive state
- no relevance labels derived from expected answer
- task-source and workspace hashes are persisted
- deterministic-only solvability is measured
- all model output is preserved, including failures and truncations

## Time-budgeted scheduler

The experiment has a one-hour wall-clock ceiling. Runtime varies with model generation behavior, so the harness uses a target plus an absolute cap.

Default:

- target: 55 minutes
- absolute ceiling: 60 minutes

Required causal phases run first. Remaining time is used adaptively for additional discovery replicates, held-out transfer, order checks, compute-substitution sweeps, and adversarial controls.

The scheduler must not start optional work unless the rolling high-percentile duration estimate plus a safety margin fits inside the remaining wall-clock budget. Any run terminated by the absolute ceiling is recorded explicitly as `TIME_BUDGET_ABORT` and never counted as a normal model failure.

The extra runtime is for broader causal coverage and replication, not automatically for larger neural reasoning budgets.

## Permanent run record

Every generation writes an append-only JSONL record containing:

- experiment/run/task identifiers
- task family and seed
- model, quantization, context, generation budget, temperature, seed
- enabled primitives and exact pass order
- source hash and workspace hash
- derived facts and derivation provenance
- discarded facts
- contradictions
- compiler timing
- prompt tokens
- generated tokens
- prompt-eval time
- generation time
- wall time
- tokens/sec
- done reason / ceiling hit
- model thinking
- final response
- evaluator result
- deterministic-only classification

## Failure taxonomy

Preserve evidence for later attribution to at least:

- STATE_ERROR
- PATH_ERROR
- AUTHORITY_ERROR
- CONTRADICTION_ERROR
- RELEVANCE_ERROR
- MEMORY_ERROR
- PROCEDURE_ERROR
- DISTRACTOR_ERROR
- SEMANTIC_REASONING_ERROR
- TRUNCATION
- LOOPING
- OUTPUT_ERROR
- COMPILER_ERROR
- TIME_BUDGET_ABORT

Failure labels may be added after the run by an independent auditor. Raw evidence is immutable.

## Self-improvement readiness

The run format must support later optimization of:

- primitive inclusion/exclusion
- pass order
- compiler rules
- representation schema
- compression
- retrieval/relevance policy
- task-family routing
- reasoning budget
- compound promotion/demotion

Self-improvement may propose changes but may not certify them. Promotion requires held-out evaluation under a frozen evaluator.

## Kill criteria

Do not expand the architecture merely because a component sounds useful.

A primitive or compound should be removed or demoted when it:

- fails to improve verified capability on relevant task families,
- fails to reduce neural compute at equal capability,
- only wins through formatting effects,
- creates brittle discovery-only gains that fail transfer,
- increases deterministic cost more than the neural cost it replaces,
- or makes uncertainty/provenance behavior less reliable.

## Production boundary

Nothing in this experiment changes V31M4 production architecture automatically. The lab produces evidence. Promotion into V31M4 requires separate causal confirmation, transfer, and independent review.
