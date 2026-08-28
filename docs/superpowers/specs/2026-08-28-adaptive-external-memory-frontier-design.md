# Experiment 007 — Adaptive External Memory Frontier Design

**Status:** Approved by user request to build an increasingly difficult test to failure, with persistent learned external memory and explicit protection against mid-run scoring failure.

## Purpose

Measure how far a fixed, stateless local model can extend its usable capability when validated information learned from earlier successful work is persisted outside the weights and supplied on later fresh calls. Separate three ceilings that would otherwise be conflated as one "memory cap":

1. **No-memory capability** — fresh model call with no retained rules.
2. **Full-memory capability** — every learned record is dumped into the prompt, exposing attention/context overload.
3. **Retrieved-memory capability** — the external store may grow while only records required by the current packet are supplied, exposing the remaining composition/reasoning frontier instead of prompt bloat.

The primary frontier is the retrieved-memory arm. Full-memory failure is a separate working-context/attention boundary. No-memory is the causal control.

## Fixed-model rule

Weights, model tag, quantization, temperature, context limit, output budget, and hardware remain unchanged within one run. Every generation is stateless. No conversation transcript carries information between calls. The only permitted cross-level state is the explicit append-only memory store owned by this experiment.

## Learned information and promotion

The store starts with 12 sealed bootstrap transformation rules. A rule has a stable ID, coefficients, modulus, learned level, evidence identifier, and deterministic fingerprint. Every rule implements:

`next = (a * current + b) mod 97`

Challenge tasks compose previously learned rules. When the `RETRIEVED` arm solves a task correctly, the experiment deterministically composes that task's rule sequence into one reusable affine macro and promotes it to memory with the solved task ID as evidence. Incorrect tasks are never promoted. If a primary packet misses the pass threshold but a fresh confirmation packet passes, only correctly solved confirmation tasks may teach memory.

Therefore later levels literally reuse compressed operators learned from earlier verified success. No model self-report can create memory.

No memory record may contain a challenge answer letter, choice ordering, expected-answer field, start-specific final value, or any failed-task conclusion. Memory stores reusable transformations only.

## Difficulty ladder

The experiment is adaptive and preregistered rather than fixed to five levels.

- Maximum levels: 30.
- Bootstrap rules before level 1: 12.
- Tasks per packet: 8.
- Passing threshold: 7/8 correct.
- Up to one validated macro is learned from each correctly solved task.
- Composition depth at level `L`: `L + 2` rule applications per task.
- Every task uses both old bootstrap memory and the newest learned level whenever multiple learned levels exist.
- Remaining referenced rules are sampled from the complete prior memory store.
- Every level uses a new deterministic task seed.
- Correct choice and three distractors are unique.
- Choice ordering is shuffled independently from rule generation.

Difficulty rises in cumulative learned memory, full-memory distractor volume, age span of retrieved memory, recursive macro reuse, and required multi-step composition depth.

## Arms and matched controls

For every level, the exact same eight challenge instances and exact same model seed are evaluated in three conditions:

- `NONE`: zero memory rule definitions.
- `FULL`: all accumulated validated memory rules.
- `RETRIEVED`: all and only rules referenced by the current packet.

Task text, choices, model, generation budget, context limit, temperature, and seed are otherwise identical.

## Frontier definition

A level passes the primary retrieved-memory frontier at accuracy `>= 0.875` with a fully parseable, non-ceiling response.

The first retrieved-memory packet below threshold is not a frontier. A fresh packet is generated at the same difficulty with a new seed. The frontier is confirmed only when that packet also scores below threshold. The last prior passing level is then the measured retrieved-memory frontier.

A malformed or length-truncated generation is `UNSCORABLE`, never wrong. An unscorable primary or control packet invalidates the affected comparison rather than being converted into capability failure.

If wall-clock reserve prevents another complete matched level, interpretation is `FRONTIER_NOT_REACHED_TIME_LIMIT`. If all 30 levels pass, interpretation is `FRONTIER_NOT_REACHED_MAX_LEVEL`.

## Full-memory context boundary

Before each model call, prompt bytes are measured and conservatively estimated at 3 bytes/token. A prompt estimated to exceed the configured context limit is not sent and is recorded as `CONTEXT_CAP_REACHED`; silent truncation is forbidden. Provider-reported prompt tokens are recorded for every sent call.

A full-memory context cap does not stop the retrieved-memory experiment. It identifies a working-context boundary while the indexed/retrieved store can continue growing.

## Runtime integrity / no half-finished scientific claim

Before frontier evidence starts, deterministic preflight proves:

- fixed-seed bootstrap and packets are stable;
- difficulty metrics rise monotonically under successful learning;
- every task has one unique sealed answer;
- every referenced rule existed before the current level;
- `NONE` carries zero definitions;
- `FULL` carries the complete store;
- `RETRIEVED` carries all and only referenced rules;
- memory text carries no answer key;
- successful compositions produce mathematically equivalent macro rules;
- failed tasks cannot create memory;
- packet scoring parses exact output;
- confirmation requires two below-threshold packets.

A live scoring preflight then requires the configured model to produce complete exact-format answers under both `FULL` and `RETRIEVED` rendering on trivial one-step memory tasks. If either fails, no frontier evidence starts.

Before a new level starts, the runner uses completed-call P95 duration plus a reserve to decide whether all three matched arms can fit. The run stops between levels rather than intentionally beginning a comparison it predicts cannot finish.

Raw run evidence is append-only. A result directory already containing `runs.jsonl`, `observations.jsonl`, or `memory.jsonl` is refused.

## Evidence

Every arm/level records model configuration, level/task/model seeds, memory arm, complete-store size, supplied/referenced count, oldest/newest learned level referenced, composition depth, prompt bytes/tokens, output tokens, wall time, per-task sealed score, status, and memory fingerprint.

Every promoted macro records its evidence task ID, learned level, coefficients, and fingerprint in `memory.jsonl`.

Summary reports the retrieved last passing level, first confirmed retrieved failure, rules/depth at that boundary, full-memory accuracy/context boundaries, aggregate no-memory/full/retrieved accuracy, unstable one-off miss levels, maximum learned store size, and whether the run ended by neural frontier, context, time, max level, or integrity failure.

## Interpretation constraints

This is a generated symbolic curriculum. It tests whether validated external memory plus deterministic retrieval lets a stateless model perform increasingly difficult compositions that it cannot solve from the current task alone. It does not prove universal long-term memory, general intelligence, or weight recovery. If `RETRIEVED` materially beats `NONE` while all calls remain stateless, that is causal evidence for external retained information. If `FULL` degrades before `RETRIEVED`, that is evidence that retrieval/compilation—not merely storing more text—is the scaling mechanism.