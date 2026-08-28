# Experiment 007 — Adaptive External Memory Frontier Design

**Status:** Frozen experimental design for the one-hour frontier run.

## Purpose

Measure how far a fixed, stateless local model can extend usable capability when validated information learned from earlier successful work is persisted outside the weights and supplied on later fresh calls. Separate three ceilings:

1. `NONE` — no retained rules.
2. `FULL` — every learned record is dumped into context, exposing attention/context overload.
3. `RETRIEVED` — only records required by the current packet are supplied, exposing the remaining memory-retrieval/composition frontier.

`RETRIEVED` is the primary measurement. `FULL` and `NONE` are controls and cannot redefine a completed primary result.

## Fixed-model rule

Weights, model tag, quantization, temperature, context limit, output budget, and hardware stay fixed within a run. Every generation is stateless. No conversation transcript carries information between calls. The only cross-stage state is the append-only experiment memory store.

## Learned information

The store starts with 12 sealed bootstrap affine rules of the form:

`next = (a * current + b) mod 97`

A challenge composes previously learned rules. When a retrieved-memory task is scored correct, its exact rule composition is deterministically reduced to one mathematically equivalent affine macro and promoted with that solved task ID as evidence. Failed tasks never create memory. If a primary packet misses threshold but a fresh confirmation packet passes, only correctly solved confirmation tasks may teach memory.

No memory record may contain a challenge answer letter, choice ordering, expected-answer field, start-specific final value, or any failed-task conclusion.

## Accelerated difficulty ladder

The unattended one-hour profile has 12 fixed stages. Each packet contains eight independent tasks. Required dependent memory operations per task are preregistered as:

`3, 5, 8, 12, 17, 23, 30, 38, 47, 57, 68, 80`

The ladder is fixed before inference and never changes in response to model performance. It is intentionally steeper than the linear development runner so the available window has a realistic chance of finding failure.

At a passing stage, up to eight verified task compositions become new macro memories. Even at the minimum passing score of 7/8, the store grows fast enough to supply every later scheduled depth. Every task uses old bootstrap memory and the newest learned stage whenever both exist, while remaining referenced rules are sampled from the complete prior store.

Difficulty therefore rises in cumulative learned store size, full-context distractor volume, memory age span, recursive macro reuse, and multi-step composition depth.

## Matched-arm ordering

For a normal stage, the same packet and model seed are used in all arms. Scheduling is:

1. `RETRIEVED` first.
2. If retrieved misses threshold, run a fresh same-difficulty retrieved confirmation before controls.
3. Run `NONE` and `FULL` controls only while their own runtime reserve remains.

This ordering prevents a bulky secondary control from consuming the time needed to establish the primary frontier.

## Frontier rule

Retrieved memory passes at accuracy `>= 0.875` with a complete non-ceiling response. The first miss is not a frontier. A fresh same-difficulty packet with a fresh model/task seed must also miss. `UNSCORABLE` is never counted as wrong.

Terminal primary interpretations include:

- `RETRIEVED_MEMORY_FRONTIER_FOUND`
- `RETRIEVED_MEMORY_CONTEXT_CAP_FOUND`
- `FRONTIER_NOT_REACHED_TIME_LIMIT`
- `FRONTIER_UNCONFIRMED_TIME_LIMIT`
- `FRONTIER_NOT_REACHED_MAX_LEVEL`
- explicit `INVALID_*` integrity failures

A `FULL` or `NONE` control becoming unscorable/unusable is recorded as that control's boundary and does not convert a valid retrieved result into failure.

## Context integrity

Prompt bytes are measured before invocation and conservatively estimated at 3 bytes/token. A prompt estimated beyond the configured context limit is not sent and is recorded `CONTEXT_CAP_REACHED`; silent truncation is forbidden. A full-memory context cap does not stop retrieved-memory testing.

## Runtime integrity

Before frontier evidence starts, deterministic preflight proves fixed-seed stability, monotonic scheduled difficulty under successful learning, unique sealed answers, prior-only memory references, exact arm isolation, no answer leakage, mathematically correct macro promotion, failed-task non-promotion, strict packet parsing, and two-failure confirmation logic.

A live preflight then requires complete exact-format answers under both `FULL` and `RETRIEVED` on trivial one-step memory tasks. If either fails, no frontier evidence starts.

The failure-resilient scheduler uses completed-call P95 duration with a 1.5 multiplier, a 30-second-per-call floor, and the configured safety margin before starting work. A same-stage confirmation will not start unless reserve predicts confirmation plus both controls can finish. Raw evidence is append-only and prior `runs.jsonl`, `observations.jsonl`, or `memory.jsonl` blocks reuse of a result directory.

## Interpretation

This generated symbolic curriculum measures external-memory-assisted capability, not universal intelligence or weight recovery. A retrieved-memory advantage over no-memory under stateless calls is causal evidence that retained external information extends usable capability on this domain. Full-memory degradation before retrieved-memory degradation is evidence that selective retrieval/compilation, rather than raw memory volume, is the scaling mechanism.
