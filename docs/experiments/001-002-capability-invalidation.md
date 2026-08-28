# Capability Invalidation — Experiments 001 and 002

## Status

The capability/effect conclusions from Experiments 001 and 002 are **invalid and must not be used to promote, demote, or rank alien-stack primitives or compounds**.

The raw evidence is retained. The runs remain useful for runtime, prompt-size, deterministic compiler-cost, derivation-count, provenance, and thinking-trace research.

## Observed failure

Local audit after the combined all-zero analysis found:

### Experiment 001

- 172 runs
- 172 status `OK`
- 172 generation-ceiling hits
- 172 blank final `response` values
- 172 nonblank `thinking` values

### Experiment 002

- 865 runs
- 865 status `OK`
- 865 generation-ceiling hits
- 865 blank final `response` values
- 865 nonblank `thinking` values

Thus all 1,037 generations exhausted `num_predict` before producing the final answer channel consumed by the evaluator.

## Root cause

The Ollama client used `think=True`. Qwen emitted reasoning into the separate `thinking` field. The experiment used short generation budgets, especially 128 tokens for discovery. Every audited run hit the generation ceiling with a blank `response`.

The evaluator correctly parsed only the final `response`, but the runner incorrectly converted missing predictions into `verified_success=False` instead of an unscorable state.

This produced artificial zero accuracy for RAW, STRUCTURED, every primitive, every compound, and the full stack.

## What remains valid

The following measurements are still observationally valid for the exact failed protocol:

- model/runtime identity snapshots;
- prompt-token counts;
- generation-token counts;
- generation and wall-clock timing;
- evidence/source/workspace hashes;
- deterministic compiler timings;
- compiler-pass provenance;
- derived-fact counts;
- discarded-evidence records;
- contradiction records;
- raw `thinking` traces;
- proof that the original output budget was insufficient for think-enabled packet scoring.

## What is invalid

Do not use the following from Experiments 001-002:

- accuracy;
- best/minimal subset rankings;
- Shapley capability values;
- Möbius capability interactions;
- pair synergy/antagonism conclusions;
- task-family capability conclusions;
- compound promotion/demotion;
- capability Pareto frontiers that depend on the invalid success labels.

## Repair rule

Experiment 003 introduces three hard gates:

1. primary capability validation runs with `think=False` so final answers are directly scorable;
2. blank, incomplete, malformed, or ceiling-hit final responses are `UNSCORABLE`, never `WRONG`;
3. a live RAW/STRUCTURED/FULL preflight must produce 6/6 parseable answers in all three packets before a causal cube can begin.

No full-hour capability experiment should run until Experiment 003 passes these gates.
