# Experiment 007 — Adaptive External Memory Frontier Design

**Status:** Approved by user request to build an increasingly difficult test to failure, with persistent learned external memory and explicit protection against mid-run scoring failure.

## Purpose

Measure how far a fixed, stateless local model can extend usable capability when validated information learned from earlier successful work is persisted outside the weights and supplied on later fresh calls. Separate three ceilings:

1. `NONE` — no retained rules.
2. `FULL` — every learned record is dumped into context, exposing attention/context overload.
3. `RETRIEVED` — only records required by the current packet are supplied, exposing the remaining composition/reasoning frontier.

The retrieved-memory arm defines the primary frontier. Full-memory failure is a separate working-context boundary. No-memory is the causal control.

## Fixed-model rule

Weights, model tag, quantization, temperature, context limit, output budget, and hardware stay fixed within a run. Every generation is stateless. No conversation transcript carries information between calls. The only cross-level state is the append-only experiment memory store.

## Learned information

The store starts with 12 sealed bootstrap affine rules of the form `next = (a * current + b) mod 97`.

A challenge composes previously learned rules. When a task in the retrieved-memory arm is scored correct, its exact rule composition is deterministically reduced to one mathematically equivalent affine macro and promoted with that solved task ID as evidence. Failed tasks never create memory. If a primary packet misses threshold but a fresh confirmation packet passes, only correctly solved confirmation tasks may teach memory.

No memory record may contain a challenge answer letter, choice ordering, expected-answer field, start-specific final value, or any failed-task conclusion.

## Difficulty ladder

- Maximum level: 30.
- Tasks per packet: 8.
- Passing threshold: 7/8.
- Composition depth at level `L`: `L + 2`.
- Up to one macro is learned per correctly solved task.
- Each task uses both old bootstrap memory and the newest learned level whenever multiple learned levels exist.
- Remaining rules are sampled from the full prior store.
- Every level uses a new deterministic task seed and unique four-choice answer set.

Difficulty therefore rises in cumulative learned memory, full-context distractor volume, age span of retrieved knowledge, recursive macro reuse, and multi-step composition depth.

## Matched arms

At each level the exact same challenge packet and model seed are evaluated under `NONE`, `FULL`, and `RETRIEVED`. Model, budget, temperature, context, choices, and task text are otherwise fixed.

## Frontier rule

Retrieved memory passes at accuracy `>= 0.875` with a complete non-ceiling response. The first miss is not a frontier. A fresh same-level packet with a fresh seed must also miss. `UNSCORABLE` is never counted as wrong.

If wall-clock reserve prevents another complete matched level, return `FRONTIER_NOT_REACHED_TIME_LIMIT`. If all 30 levels pass, return `FRONTIER_NOT_REACHED_MAX_LEVEL`.

## Context integrity

Prompt bytes are measured before invocation and conservatively estimated at 3 bytes/token. A prompt estimated beyond the configured context limit is not sent and is recorded `CONTEXT_CAP_REACHED`; silent truncation is forbidden. A full-memory context cap does not stop retrieved-memory testing.

## Preflight integrity

Before frontier evidence starts, deterministic preflight proves fixed-seed stability, monotonic difficulty under successful learning, unique sealed answers, prior-only memory references, exact arm isolation, no answer leakage, mathematically correct macro promotion, failed-task non-promotion, strict packet parsing, and two-failure confirmation logic.

A live preflight then requires complete exact-format answers under both `FULL` and `RETRIEVED` on trivial one-step memory tasks. If either fails, no frontier evidence starts.

Before starting a new level, completed-call P95 duration plus reserve must indicate all three matched arms can fit. Raw evidence is append-only and prior `runs.jsonl`, `observations.jsonl`, or `memory.jsonl` blocks reuse of a result directory.

## Interpretation

This generated symbolic curriculum measures external-memory-assisted capability, not universal intelligence or weight recovery. A retrieved-memory advantage over no-memory under stateless calls is causal evidence that retained external information extends usable capability on this domain. Full-memory degradation before retrieved-memory degradation is evidence that retrieval/compilation, not raw memory volume, is the scaling mechanism.
