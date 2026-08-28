# Experiment 007 — Adaptive External Memory Frontier Design

**Status:** Approved by user request to build an increasingly difficult test to failure, with persistent learned external memory and explicit protection against mid-run scoring failure.

## Purpose

Measure how far a fixed, stateless local model can extend its usable capability when validated information learned earlier is persisted outside the weights and supplied on later fresh calls. Separate three different ceilings that would otherwise be conflated as a single "memory cap":

1. **No-memory capability** — fresh model call with no retained rules.
2. **Full-memory capability** — every learned record is dumped into the prompt; this exposes attention/context overload.
3. **Retrieved-memory capability** — the external store may grow arbitrarily, but only records required by the current packet are supplied; this exposes the model's remaining composition/reasoning frontier rather than prompt bloat.

The primary frontier is the retrieved-memory arm. Full-memory failure is a separate working-context/attention boundary. No-memory is the causal control.

## Fixed model rule

Weights, model tag, quantization, temperature, context limit, output budget, and hardware remain unchanged within one run. Every generation is stateless. No conversation transcript carries information between calls. The only permitted cross-level state is the explicit append-only external memory store produced by this experiment.

## Learned information

Memory contains validated symbolic transformation rules. A rule has a stable ID, coefficients, modulus, acquisition level, evidence identifier, and deterministic fingerprint. The transformation is:

`next = (a * current + b) mod 97`

Rules are generated from a sealed seed and acquired into the append-only memory store before they can be used by later challenge levels. Later challenge prompts reference rule IDs but do not restate the rule definitions except through the memory arm being tested.

This makes memory necessary rather than decorative: a stateless no-memory call does not possess the arbitrary generated rule definitions.

No memory record may contain the current challenge's answer letter, choice ordering, expected answer field, or current task-specific final value. Memory stores reusable rules, never answer keys.

## Difficulty ladder

The experiment is adaptive and preregistered rather than fixed to five levels.

- Maximum levels: 30.
- Bootstrap learned rules before level 1: 12.
- New learned rules appended after each completed level: 12.
- Tasks per packet: 8.
- Composition depth at level `L`: `L + 2` rule applications per task.
- Each task must use both older and recently acquired memory whenever the store is large enough, preventing the test from degenerating into recency-only recall.
- Every level uses a new deterministic task seed.
- Correct choice and three distractors must be unique.
- Choice ordering is independently shuffled from rule generation.

Difficulty therefore rises simultaneously in cumulative memory size, distractor count for the full-memory arm, retrieval age span, and required multi-step composition depth.

## Arms and matched controls

For every level, the exact same eight challenge instances and the exact same model seed are evaluated in three conditions:

- `NONE`: no memory records.
- `FULL`: all accumulated validated memory records.
- `RETRIEVED`: exactly the union of memory records referenced by the packet.

The task text, choices, model, generation budget, context limit, and seed are otherwise identical.

## Frontier definition

A level passes the primary retrieved-memory frontier when at least 7 of 8 tasks are correct (`accuracy >= 0.875`) with a fully parseable, non-ceiling response.

The first retrieved-memory level below threshold is not immediately called the frontier. A fresh confirmation packet is generated at the same difficulty with a new seed. The frontier is confirmed only if the confirmation packet is also below threshold. The last prior passing level is then the measured retrieved-memory frontier.

A single malformed/length-truncated generation is `UNSCORABLE`, not wrong, and invalidates that packet rather than being counted as capability failure.

If the wall-clock budget is reached before a confirmed capability failure, interpretation is `FRONTIER_NOT_REACHED_TIME_LIMIT`, not failure.

If all 30 levels pass, interpretation is `FRONTIER_NOT_REACHED_MAX_LEVEL`.

## Full-memory context boundary

Before each model call, prompt bytes are measured and conservatively estimated at 3 bytes/token. A prompt estimated to exceed the configured context limit is not sent to Ollama and is recorded as `CONTEXT_CAP_REACHED`; this avoids silent truncation. Returned provider prompt-token counts are recorded for every sent call.

A full-memory context cap does not stop the experiment. The retrieved-memory arm continues so storage scale is separated from working-context scale.

## Runtime integrity / no half-finished experiment

Before any frontier level starts, a deterministic preflight must prove:

- generation is stable for a fixed seed;
- difficulty metrics increase monotonically;
- every task has exactly one sealed answer;
- every referenced rule exists and was acquired before the challenge;
- `NONE` contains zero rule definitions;
- `FULL` contains every currently learned rule;
- `RETRIEVED` contains all and only referenced rules;
- memory text contains no current answer key or choice ordering;
- scorer parses exact packet output correctly;
- confirmation logic requires two failures rather than one.

A live scoring preflight then requires the configured model to return a complete exact-format packet under both `FULL` and `RETRIEVED` rendering. If either fails, no frontier evidence is started.

Before starting a new level, the runner estimates the P95 duration of completed model calls. It starts a level only if enough wall-clock remains for all three matched arms plus the configured safety margin. This guarantees clean stopping between levels instead of a half-completed comparison.

Raw run evidence is append-only and a result directory containing prior raw evidence is refused.

## Recorded evidence

For every arm and level record:

- model and configuration
- task seed and model seed
- memory arm
- learned rule count
- referenced/retrieved rule count
- oldest/newest learned level used
- composition depth
- prompt bytes and provider prompt tokens
- output tokens and wall time
- per-task predictions and sealed answers
- packet accuracy
- status / unscorable reason
- memory snapshot fingerprint

Summary reports:

- retrieved-memory last passing level
- first confirmed retrieved-memory failure level
- learned rule count at the frontier
- composition depth at the frontier
- full-memory first capability failure
- full-memory context-cap level if reached
- no-memory aggregate accuracy
- retrieved-memory aggregate accuracy
- retrieved-vs-none gain by level
- retrieved-vs-full gain by level
- whether failure was neural, context, time, or max-level bounded

## Interpretation constraints

This experiment measures external-memory-assisted capability on a generated symbolic curriculum. It does not prove universal long-term memory, general intelligence, or weight recovery. A retrieved-memory advantage over `NONE`, while all calls remain stateless, is causal evidence that external retained information extends the model's usable capability on this domain. A `FULL` failure preceding `RETRIEVED` failure is evidence that retrieval/compilation, not raw memory volume, is the critical scaling mechanism.
