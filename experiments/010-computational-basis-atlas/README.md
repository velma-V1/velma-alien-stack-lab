# Experiment 010 — Computational Basis Atlas

## Purpose

Experiment 010 discovers which external computational capabilities can make a small-model VELMA system materially more capable, how those capabilities interact, where neural reasoning is still required, and which discoveries are worth later promotion into `velma-V1/V31m4`.

This is an architecture-discovery experiment, not a pass/fail referendum on VELMA. A valid unresolved result is evidence about the next bottleneck. The top-level valid completion state is:

```text
DISCOVERY_COMPLETE
```

The full design is in:

```text
docs/superpowers/specs/2026-08-29-experiment-010-computational-basis-atlas-design.md
```

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

The built-in implementations are deterministic **reference engines used to test the architecture and evidence machinery**. They are not automatically the implementations that V31M4 should ship. Production promotion should prefer mature replaceable implementations behind V31M4 contracts when evidence supports them.

## World set

The default generator creates 192 sealed base worlds across 12 behavioral families with this required-computation distribution:

```text
64  primarily one capability
64  two capabilities
40  three capabilities
16  four-or-more capabilities
 8  intentionally outside the initial basis
```

The eight outside-basis worlds are discovery probes. They are not infrastructure failures and they do not terminate the experiment.

## Deterministic phases implemented in v1

### Phase A — exact attribution

64 balanced oracle-IR diagnostic worlds are executed against every subset of the eight basis capabilities:

```text
64 × 256 = 16,384 cells
```

This supports minimum-basis attribution and engine-necessity/overlap analysis without neural-model noise.

### Phase B — broad oracle ceiling

All 192 worlds receive the full basis and each of eight leave-one-out variants:

```text
192 × 9 = 1,728 cells
```

Combined deterministic atlas size:

```text
18,112 cells
```

All deterministic cells use zero neural model calls.

## Evidence levels — do not conflate them

010 deliberately distinguishes three evidence classes.

### 1. Measured experiment evidence

A real ledger cell executed by the atlas runner and independently scored by its deterministic verifier. Phase A/B results belong here.

### 2. Controlled mechanism audit

A synthetic intervention with a known injected fault used to prove that the **experiment machinery** can localize or account for a mechanism correctly. Examples include rescue-stage injection and capability-reuse accounting.

These audits are labeled explicitly, including:

```text
CONTROLLED_RESCUE_AUDIT
SYNTHETIC_MECHANISM_AUDIT
```

They must never be reported as proof of live-model capability.

### 3. Pending live evidence

Questions involving a real semantic compiler, model router, frontier model, perceptual model, or true deployment cost remain explicit pending evidence until that phase actually runs.

Pending evidence is not converted into zero and not silently inferred from deterministic tests.

## Rescue semantics

The approved rescue ladder is:

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

A rescue is diagnostic. It never overwrites the original cell score.

Bottleneck labels are:

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

A map whose required live phase has not run must say so explicitly rather than fabricate evidence.

## Question coverage

The reporting contract preserves the Q0–Q26 scientific tribunal, with Q14 interpreted as the cheapest discriminating experiment that maximally changes the next decision. It adds Q27–Q36 for V31M4 production/promotion consequences.

The experiment is also required to answer the approved 32 capability/system/production questions from the design document.

## Profiles

### `smoke`

Credential-free CI profile with a reduced Phase A/B ledger. It verifies contracts, sealing, replay, reporting, and regressions quickly.

### `atlas`

Full 18,112-cell deterministic Phase A/B profile. No model service is required.

### `local`

Adds local semantic/router/model phases when a provider-neutral live adapter is configured. Until configured, live evidence remains `MODEL_UNAVAILABLE` with `score=null`.

### `frontier`

Adds paired frontier calibration in equivalent generic tool environments. Provider credentials and model identifiers are runtime configuration rather than hard-coded scientific assumptions.

## Run

Smoke:

```bash
python3 -m alien_lab.computational_atlas \
  --config experiments/010-computational-basis-atlas/config.json \
  --output-dir results/010-computational-basis-atlas-smoke \
  --profile smoke
```

Full deterministic atlas:

```bash
python3 -m alien_lab.computational_atlas \
  --config experiments/010-computational-basis-atlas/config.json \
  --output-dir results/010-computational-basis-atlas \
  --profile atlas
```

Exit codes:

- `0` — all required work for the selected credential-free profile is accounted for and the report was generated;
- `2` — invalid configuration, harness failure, corrupted evidence, changed-ledger output-directory mismatch, or another invalid execution condition.

There is deliberately no capability-failure exit code. Valid unresolved tasks remain scored evidence and the run continues.

## Evidence durability

The runner uses:

- deterministic preregistered ledger construction;
- SHA-256 ledger identity;
- SHA-256 per-cell evidence envelopes;
- atomic writes;
- resumable terminal cells;
- changed-ledger output-directory refusal;
- deterministic replay fingerprint;
- explicit invalid versus valid-unresolved semantics;
- no capability-based early termination.

Outputs include:

```text
ledger.json
ledger-manifest.json
cells/*.json
summary.json
discovery-report.json
production-fitness.json
```

## Current scientific boundary

The deterministic atlas can establish whether the **external-computation architecture and attribution machinery** behave as designed under correct formal representation. It cannot by itself establish Opus/Fable-class breadth, natural-language formalization quality, live local-model routing quality, perceptual understanding, or real V31M4 target-host cost.

Those remain later measured phases. The experiment is designed so those results can be added without changing the identity or interpretation of the deterministic evidence already collected.
