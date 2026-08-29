# Experiment 010 — Computational Basis Atlas

## Purpose

Experiment 010 discovers which external computational capabilities can make a small-model VELMA system materially more capable, how those capabilities interact, where neural reasoning is still required, and which discoveries are worth later promotion into `velma-V1/V31m4`.

This is an architecture-discovery program, not a pass/fail referendum on VELMA. Valid unresolved results are evidence about the next bottleneck. The test itself is adversarially frozen after preregistration; evidence may change the system under test, but never the test in our favor.

Top-level valid completion state:

```text
DISCOVERY_COMPLETE
```

## Source of truth

```text
experiments/010-computational-basis-atlas/PREREGISTRATION-C-I-v1.md
docs/superpowers/specs/2026-08-29-experiment-010-computational-basis-atlas-design.md
experiments/010-computational-basis-atlas/README.md
```

If they conflict, the frozen preregistration wins.

## Laboratory versus production

`velma-alien-stack-lab` is the research laboratory. `velma-V1/V31m4` is the production home for independently justified improvements.

010 never mutates V31M4 and never automatically promotes an experimental implementation. Every useful capability instead receives a Production Fitness Record describing measured contribution, V31M4 integration seam, verification, isolation, replaceability, resource questions, roadmap displacement, and evidence confidence.

## Initial computational-basis hypothesis

Eight capability classes are tested without assuming they are complete:

- `G` — graph/state-transition reasoning
- `L` — logic/rule reasoning
- `C` — constraint/optimization reasoning
- `P` — planning/search
- `X` — program/code execution
- `M` — symbolic/numerical math and simulation
- `D` — relational/analytical data operations
- `R` — retrieval/evidence operations

The built-in implementations are deterministic **reference engines used to test architecture and evidence machinery**. They are not automatically production implementations for V31M4.

## World set

The default generator creates 192 sealed base worlds across 12 behavioral families:

```text
64  primarily one capability
64  two capabilities
40  three capabilities
16  four-or-more capabilities
 8  intentionally outside the initial basis
```

The eight outside-basis worlds are discovery probes. They are valid unresolved evidence, not infrastructure failures.

## Frozen test rule

```text
IF result is bad:
    keep result
    improve system
    rerun same frozen test when comparison is required

IF objective ceiling saturation is proven:
    preserve all v1 evidence
    append HARDER_EXTENSION_vN
    never weaken/replace/rescale v1
```

Tasks, seeds, phase membership, arms, scoring, budgets, rescue order, fairness rules, and invalidation semantics are frozen by `PREREGISTRATION-C-I-v1.md`.

## Current implementation/evidence gate

```text
A/B := BUILT + EXECUTED + VERIFIED deterministic evidence
C/D := BUILT live test/runtime + identity-sealed evidence harness; next live evidence target
E/F := frozen + reference test/runtime infrastructure exists; not the current live gate
G/H/I := FROZEN DEFINITIONS/LEDGERS ONLY; live/system runtime intentionally absent
```

No code path in the current live harness can advance into G/H/I.

Before accepting the first real C/D model result, the adversarial Claude preflight in `CURRENT_TASK.md` must report `READY_FOR_LIVE_C_D := YES` and the normal independent GPT verification still applies.

## Deterministic Phases A/B

### Phase A — exact attribution

64 balanced oracle-IR diagnostic worlds execute against every subset of the eight basis capabilities:

```text
64 × 256 = 16,384 cells
```

### Phase B — broad oracle ceiling

All 192 worlds receive the full basis and each of eight leave-one-out variants:

```text
192 × 9 = 1,728 cells
```

Combined deterministic atlas:

```text
18,112 cells
```

All A/B deterministic cells use zero neural model calls.

## Frozen C–I sizes

The preregistered live definitions remain fixed even though implementation is gated:

```text
C = 3,840 cells
D =   576 cells
E =   864 cells
F = 1,152 cells
G =   864 cells
H =   120 cells
I =   288 cells
-------------
    7,704 cells
```

The existence of G/H/I ledger definitions does **not** authorize implementing or executing their system mechanisms before the explicit evidence gate.

## Evidence levels — do not conflate them

### 1. Measured experiment evidence

A real preregistered ledger cell executed and independently scored under a sealed run identity.

### 2. Controlled mechanism audit

A deterministic/fake-provider intervention used to prove that experiment machinery behaves correctly. It must retain an explicit non-live evidence kind such as:

```text
CONTROLLED_RESCUE_AUDIT
SYNTHETIC_MECHANISM_AUDIT
FAKE_MECHANICS_ONLY
```

Controlled audits are never live-model capability evidence.

### 3. Pending live evidence

A preregistered question whose real model/system phase has not run. Pending evidence is not converted into zero and is not inferred from deterministic tests.

## Rescue semantics

Frozen order:

```text
original system path
  -> oracle TaskIR
  -> oracle decomposition
  -> oracle routing
  -> oracle engine outputs
  -> oracle typed handoff
  -> oracle execution
  -> verifier discrimination
```

A rescue is diagnostic and never overwrites the original score.

Bottleneck labels:

```text
SEMANTIC
DECOMPOSITION
ROUTING
ENGINE
COMPOSITION
EXECUTION
VERIFICATION
MISSING_CAPABILITY
AMBIGUOUS_INPUT
PERCEPTION
```

## Generated discovery outputs

The report contract reserves 20 maps:

1. computational coverage
2. minimum basis
3. unique engine value
4. synergy matrix
5. substitution/redundancy
6. semantic degradation
7. semantic-error taxonomy
8. decomposition-error rate
9. routing regret
10. tool overload
11. model-dependence Pareto frontier
12. verification value
13. silent-wrong rate
14. capability learning
15. transfer/drift
16. horizon curve
17. frontier gap
18. missing-capability clusters
19. rescue bottlenecks
20. next-direction Pareto set

A map whose required live phase has not run must explicitly remain pending.

## Question coverage

010 preserves the Q0–Q26 scientific tribunal with Q14 interpreted as the cheapest discriminating experiment that maximally changes the next decision. It adds Q27–Q36 for V31M4 production/promotion consequences and the approved 32 capability/system/production questions.

The on-demand Claude tribunal is located at:

```text
.claude/skills/010-tribunal/
```

## GPT ↔ Claude control structure

```text
CLAUDE.md
    permanent concise 010 constitution

.claude/rules/experiment-010.md
    path-scoped coding/evidence rules

.claude/skills/010-tribunal/
    on-demand Q0-Q36 + mandatory-32 adversarial review

experiments/010-computational-basis-atlas/CURRENT_TASK.md
    replaceable GPT -> Claude task packet
```

`CURRENT_TASK.md` may select work but may never override the preregistration.

## Deterministic runs

Smoke:

```bash
python3 -m alien_lab.computational_atlas \
  --config experiments/010-computational-basis-atlas/config.json \
  --output-dir results/010-computational-basis-atlas-smoke \
  --profile smoke
```

Full A/B atlas:

```bash
python3 -m alien_lab.computational_atlas \
  --config experiments/010-computational-basis-atlas/config.json \
  --output-dir results/010-computational-basis-atlas \
  --profile atlas
```

The older base-runner `local` / `frontier` profile names are **not** the accepted live C/D evidence path. They remain non-evidence placeholders in the A/B runner and must not be used to claim live results.

## Live C/D execution path

After adversarial preflight approval, the full live C/D run uses the dedicated identity-sealed harness:

```bash
python3 -m alien_lab.computational_atlas_live_experiment \
  --output-dir results/010-live-cd/<system-version>-<model> \
  --model-id <ollama-model-id> \
  --endpoint http://127.0.0.1:11434 \
  --system-version <immutable-system-version> \
  --model-digest <digest-if-known> \
  --context-limit <model-context-limit> \
  --phases CD
```

The harness freezes before the first scored cell:

```text
system_version
provider_kind
model_id
model_digest when supplied
provider_version when supplied
endpoint
generation contract
prompt contract hash
C/D ledger hash
```

It rejects output-directory reuse if run or ledger identity changes. Valid cell evidence is immutable/hash-checked. `--rerun-invalid` may recompute only prior `score=null` infrastructure cells; valid scored evidence is never silently replaced.

Current live phases accepted by this harness:

```text
C
D
```

G/H/I are intentionally not accepted CLI choices.

## Evidence durability

The deterministic and live runners use the applicable subset of:

- preregistered deterministic ledgers;
- SHA-256 ledger identity;
- sealed run identity;
- SHA-256 per-cell evidence envelopes;
- atomic writes;
- resumable terminal cells;
- changed-identity output-directory refusal;
- explicit invalid versus valid-unresolved semantics;
- no capability-based early termination;
- transport retry accounting.

## Current scientific boundary

A/B establish the computational substrate under correct formal representation. C/D are the next live target and will measure the semantic/formalization interface and constrained-repair effect.

E/F remain frozen reference infrastructure and must not be changed to accommodate C/D outcomes. G/H/I remain definition-only until the explicit evidence gate. Nothing in the current repository establishes Opus/Fable-class breadth, live capability accumulation, long-horizon advantage, or frontier-system superiority yet.
