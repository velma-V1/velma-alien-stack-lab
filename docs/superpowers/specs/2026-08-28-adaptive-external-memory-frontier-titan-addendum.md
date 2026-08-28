# Experiment 007 — Titan Frontier Probe Addendum

**Status:** User-directed extension to the approved Experiment 007 adaptive external-memory frontier.

## Purpose

Add one mandatory final challenge whose purpose is not to move the measured adaptive frontier, but to answer a separate calibration question:

> Can the tested model, with all validated external memory it earned during Experiment 007, correctly solve a deliberately frontier-class held-out problem designed to remain nontrivial for a strong 70–100B open-weight model?

Passing this probe does **not** prove the tested model is frontier-class. Failing it does **not** prove that it cannot be useful at frontier-class work. The result is a bounded empirical capability observation on one difficult held-out task.

## Separation from the adaptive frontier

The Titan probe is not `Level 31` and does not affect:

- `retrieved_last_passing_level`
- `retrieved_first_confirmed_failure_level`
- `memory_rules_at_frontier`
- the two-failure frontier confirmation rule

The ordinary adaptive ladder remains the causal external-memory experiment. Titan is a mandatory post-frontier calibration probe.

Titan must run even when:

- the retrieved-memory frontier was already confirmed at an earlier level;
- the adaptive ladder reached the maximum level;
- the runner stopped adding new adaptive levels because the reserved wall-clock budget was reached.

The runner must reserve enough time for Titan before starting another ordinary adaptive level. Infrastructure failure or an unscorable Titan generation is reported as `TITAN_INVALID`, never as a capability failure.

## Learned-memory requirement

Titan uses the final append-only memory snapshot actually earned by the model during the run. It may use only memory records that were deterministically validated before promotion.

Successful ordinary tasks may be promoted into reusable macro memories. A macro is the exact composition of the validated transformations used by the solved task and is represented as a new verified transformation with provenance back to that task. Failed or unscorable tasks are never promoted.

Titan must mix:

- old bootstrap memories;
- memories learned at intermediate levels;
- the newest validated memories available;
- validated macro memories produced from earlier successful tasks.

No Titan answer, choice ordering, task-specific final register value, or hidden branch result may enter memory.

## Titan challenge shape

Titan is one held-out task so the full inference budget is concentrated on a single difficult decision rather than amortized across an eight-task packet.

The challenge is a deterministic register program generated from a sealed seed. It contains:

- **8 registers** with independently generated initial values;
- **32 memory-backed transformation applications** minimum;
- at least **12 distinct referenced memory records**;
- at least **6 validated macro memories** when the earned store contains that many;
- **6 cross-register joins** where one register depends on two or more previously computed registers;
- **4 conditional branch points** whose selected path depends on intermediate computed state;
- **3 nested dependency joins** so later work depends on the result of earlier branches rather than independent arithmetic chains;
- **irrelevant but valid memory distractors** that are supplied only in the `FULL` arm, never in `RETRIEVED`;
- **four unique answer choices**, with distractors generated from realistic failure modes such as one wrong branch, one omitted macro, and one stale intermediate register.

Every operation is deterministic and has an independent oracle implementation. The sealed answer is calculated before model invocation and is never derived from model output.

## Difficulty target

The Titan construction is intentionally labelled **70–100B-class target difficulty**, not “proven 70–100B difficulty.” Parameter count is not a scientific difficulty unit, and no claim of calibration is allowed until the same sealed Titan generator is tested against actual 70–100B models.

The design target is that solving Titan requires simultaneous:

1. accurate retrieval/use of externally learned information;
2. long multi-step state tracking;
3. conditional control-flow reasoning;
4. composition of previously learned macro transformations;
5. resistance to plausible stale/intermediate distractors.

A 24B model solving it correctly is therefore a meaningful positive result, but not proof of frontier equivalence.

## Titan arms

Run three matched Titan conditions with the same task and model seed:

- `TITAN_NONE` — no learned memory definitions;
- `TITAN_FULL` — all earned validated memory, unless the full prompt hits the predeclared context guard;
- `TITAN_RETRIEVED` — only memories referenced by the Titan program.

`TITAN_RETRIEVED` is the primary result. `TITAN_NONE` measures whether retained information was necessary. `TITAN_FULL` measures whether unfiltered memory volume interferes with the solution.

If `TITAN_FULL` exceeds the conservative context guard, record `CONTEXT_CAP_REACHED` and continue with `TITAN_RETRIEVED`.

## Titan success and reporting

Titan success requires:

- a parseable exact-format final answer;
- no output ceiling;
- no context truncation;
- the selected answer exactly matching the sealed deterministic oracle.

Report at minimum:

- `titan_retrieved_correct`
- `titan_none_correct`
- `titan_full_correct`
- `titan_status`
- `titan_memory_rules_available`
- `titan_memory_rules_retrieved`
- `titan_macro_rules_retrieved`
- `titan_program_steps`
- `titan_branch_points`
- `titan_cross_register_joins`
- `titan_prompt_tokens`
- `titan_eval_tokens`
- `titan_wall_ms`
- `titan_memory_snapshot_fingerprint`

The human-readable report must state one of:

- `TITAN_SOLVED_WITH_RETRIEVED_MEMORY`
- `TITAN_NOT_SOLVED`
- `TITAN_INVALID`

No Titan result may be silently folded into the ordinary frontier score.

## Preflight additions

Before live Experiment 007 evidence starts, deterministic preflight must also prove:

- Titan generation is stable for a fixed seed and changes for a new seed;
- the independent Titan oracle reproduces the sealed answer;
- all Titan choices are unique;
- every referenced memory record exists in the supplied earned-memory snapshot;
- Titan uses old, intermediate, and newest available memory when those strata exist;
- failed/unscorable task memories cannot be referenced because they were never promoted;
- `TITAN_NONE`, `TITAN_FULL`, and `TITAN_RETRIEVED` obey the same memory-isolation rules as the ordinary experiment;
- Titan memory prefixes contain no answer key or hidden final state;
- the Titan prompt fits the retrieved-memory context guard before invocation;
- adaptive level scheduling reserves enough runtime for all mandatory Titan arms that can legally run.
