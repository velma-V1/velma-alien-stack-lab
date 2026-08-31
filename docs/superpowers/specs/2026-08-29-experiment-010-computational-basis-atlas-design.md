# Experiment 010 — Computational Basis Atlas Design

Date: 2026-08-29
Branch: `experiment/010-computational-basis-atlas`
Production destination: `velma-V1/V31m4`

## Purpose

Experiment 010 is an architecture-discovery program for the next VELMA intelligence layer. It asks how much verified problem-solving capability can be moved from stochastic model reasoning into reusable external computation, how those capabilities compose, where the local model remains necessary, and which discoveries are worth promoting into V31M4.

010 has no top-level scientific kill order. Valid unresolved outcomes are evidence. Every valid unresolved cell must be localized to the narrowest known bottleneck and must contribute to a ranked next-direction map.

The laboratory remains isolated from V31M4 production state. Promotion into V31M4 is a later governed action; 010 only produces evidence and a production-fit mapping.

## Stable scientific tribunal

Every 010 report must answer Q0–Q26 from the architecture-discovery framework. Q14 is interpreted as:

> What is the cheapest discriminating experiment that maximally changes what we should do next?

It is not an order to stop VELMA.

010 additionally answers the production/promotion tribunal:

- Q27 Production seam — can the capability enter V31M4 through an existing port, gateway, plugin, kernel, verifier, or capability boundary?
- Q28 Authority preservation — does model output remain untrusted and does authoritative state remain runtime-owned?
- Q29 Local-machine economics — CPU, RAM, VRAM, storage, startup, latency, sustained load, concurrency, idle overhead.
- Q30 Failure isolation — what fraction of VELMA fails if the capability fails?
- Q31 Verification contract — input, result, evidence/certificate, independent verification, failure conditions.
- Q32 Replaceability — can the implementation change behind a stable capability contract?
- Q33 Engineering ROI — verified capability gain per implementation and maintenance burden.
- Q34 Roadmap displacement — which planned V31M4 components can be simplified, replaced, merged, or eliminated?
- Q35 Capability compounding — can verified work become reusable computation without retraining?
- Q36 Competitive consequence — small-model compensator or generally superior architecture?

## Mandatory 32 experiment questions

### A — computational topology
1. What is the oracle-IR ceiling?
2. What does each engine uniquely contribute?
3. Which engines are redundant?
4. Which engines substitute for one another?
5. Which combinations demonstrate genuine synergy?
6. What is the minimum sufficient computational basis?
7. What problem clusters remain outside that basis?
8. What new fundamental operators do residual clusters imply?

### B — semantic/model interface
9. What is the semantic-formalization tax?
10. How does that tax change across representation levels?
11. Which semantic errors dominate?
12. How often is decomposition itself wrong?
13. What is routing regret versus oracle routing?
14. Does capability overload make routing worse?
15. When is a model call actually necessary?
16. Can the system recognize uncertainty/unsupported tasks instead of forcing a bad formalization?

### C — system intelligence
17. Does typed multi-engine composition create capability unavailable to individual engines?
18. Where does composition break?
19. How does capability degrade with horizon length?
20. How much does independent verification improve trustworthy success?
21. Where is verification incomplete or impossible?
22. How many silent wrong results survive each architecture?
23. Does verified capability accumulation reduce neural reasoning over repeated work?
24. Does accumulated capability survive parameter variation, representation shift, transfer, and drift?

### D — competitive and production consequence
25. How does VELMA + local compare to local-model-only?
26. How does architecture value change as model strength rises?
27. What capability-family gaps remain versus frontier systems?
28. What is the success/model-call/cost/latency Pareto frontier?
29. Where does each useful capability belong in V31M4?
30. What does each capability cost and risk in the production runtime?
31. Which planned V31M4 components can be simplified, replaced, merged, or eliminated?
32. Given all evidence, what are the Pareto-optimal next directions?

## Initial computational-basis hypothesis

010 begins with eight capability classes but does not assume they are complete:

- `G` graph/state-transition reasoning
- `L` logic/SMT-style reasoning
- `C` constraints/optimization
- `P` planning/search
- `X` program/code execution
- `M` symbolic/numerical math and simulation
- `D` relational/analytical data operations
- `R` retrieval/evidence operations

Cross-cutting mechanisms are:

- `S` semantic compiler
- `T` router/composer
- `V` authoritative verifier
- `K` verified capability library

Perception is treated initially as input-to-TaskIR structure extraction and measured separately rather than declared a ninth solver.

## TaskIR v0

All engines consume or emit typed JSON-compatible TaskIR fragments. TaskIR v0 contains:

- `task_id`
- `entities`
- `facts`
- `goals`
- `constraints`
- `relations`
- `actions`
- `resources`
- `objectives`
- `observations`
- `verification`
- `provenance`
- `required_capabilities`

No engine receives a natural-language answer key. Oracle TaskIR is sealed by the harness and exposed only in oracle arms and rescue interventions.

## Behavioral worlds

The default full profile defines 192 sealed base worlds across 12 behavioral families:

1. dependency/workflow coordination
2. resource allocation
3. scheduling
4. policy/rule reasoning
5. state-space planning
6. quantitative/engineering analysis
7. record/data synthesis
8. software/code problems
9. evidence reconciliation/research
10. temporal/spatial reasoning
11. scientific/diagnostic reasoning
12. multi-domain operational problems

Required-computation distribution:

- 64 primarily one-capability worlds
- 64 two-capability worlds
- 40 three-capability worlds
- 16 four-or-more-capability worlds
- 8 intentionally outside the initial basis

The outside-basis worlds are discovery probes. Their unresolved status is valid evidence and must be clustered into candidate missing operators.

## Representation ladder

A matched underlying world can be rendered as:

- `R0_ORACLE_IR` — canonical TaskIR
- `R1_STRUCTURED` — tables/schema/records/config-like input
- `R2_NATURAL` — normal natural-language request
- `R3_PARAPHRASED` — reordered facts, synonyms, irrelevant details
- `R4_IMPLICIT` — relations/constraints distributed or implicit
- `R5_PERCEPTUAL` — rendered document/table/diagram/screenshot subset

Task identity remains sealed across representations so representation effects are paired.

## Automatic rescue ladder

Every valid unresolved non-oracle task is replayed through interventions until the narrowest recoverable bottleneck is found:

1. original system path
2. oracle TaskIR
3. oracle decomposition
4. oracle routing
5. oracle individual engine outputs
6. oracle typed cross-engine handoff
7. oracle execution outcome
8. verifier discrimination against expected result

Localization labels:

- `SEMANTIC`
- `DECOMPOSITION`
- `ROUTING`
- `ENGINE`
- `COMPOSITION`
- `EXECUTION`
- `VERIFICATION`
- `MISSING_CAPABILITY`
- `AMBIGUOUS_INPUT`

A rescue is diagnostic only; rescued cells never overwrite the original task score.

## Phases

### Phase A — exact computational-basis attribution

Use 64 balanced oracle-IR diagnostic worlds. Execute all 256 subsets of the eight basis capabilities. These cells must use no neural model. Measure unique effects, redundancy, substitution, pairwise/higher-order interactions, harmful additions, and minimum sufficient subsets.

Default cells: 16,384.

### Phase B — broad oracle ceiling and leave-one-out

All 192 worlds receive full basis plus eight leave-one-out arms. Outside-basis worlds remain valid unresolved evidence.

Default cells: 1,728.

### Phase C — semantic compilation

Matched representation arms compare:

- local model only
- deterministic recognition + basis
- local semantic compiler + basis
- oracle TaskIR + basis

The difference between model-produced TaskIR and oracle TaskIR is the semantic-formalization tax.

### Phase D — model-to-IR interface

On a difficult held-out semantic subset compare:

- free JSON
- schema/grammar-constrained TaskIR
- constrained TaskIR + deterministic validation + counterexample-guided repair

Syntax validity and semantic correctness are scored separately.

### Phase E — routing and overload

Compare oracle router, deterministic/rule router, and local-model router. Repeat with 8 true capability interfaces, then with irrelevant/overlapping decoys to measure tool-overload degradation.

### Phase F — typed composition

Use held-out 2–5 capability worlds. Compare model-only, best single capability, all capabilities without typed composition, typed TaskIR composition, and typed composition + verifier. Synergy requires end-to-end verified success unavailable to every constituent alone.

### Phase G — capability accumulation

Use 48 lineages through `NOVEL`, `REPEAT`, `PARAMETER_VARIATION`, `REPRESENTATION_SHIFT`, `ENVIRONMENT_DRIFT`, `COMPOSITION_TRANSFER`. Compare no retained capability, text/memory retrieval, and verified executable capability. Measure model calls, reuse, incorrect reuse, transfer, and repair.

### Phase H — long-horizon slice

Use long jobs with dense intermediate milestones. Record success against horizon length, first failure location, recovery, state drift, and verification coverage.

### Phase I — frontier calibration

Run a sealed difficult subset through equivalent tool environments:

- local model only
- VELMA architecture + local model
- frontier baseline A
- VELMA architecture + frontier A
- frontier baseline B
- VELMA architecture + frontier B

Provider/model names are runtime configuration, never hard-coded scientific assumptions. This phase may be omitted from CI when credentials are unavailable; omission is explicit non-evidence, not zero.

## Evidence classifications

Top-level experiment completion is `DISCOVERY_COMPLETE`, never `PASS` or `FAIL`.

Scored/valid outcomes include:

- `VERIFIED_SUCCESS`
- `VALID_UNRESOLVED_SEMANTIC`
- `VALID_UNRESOLVED_DECOMPOSITION`
- `VALID_UNRESOLVED_ROUTING`
- `VALID_UNRESOLVED_ENGINE`
- `VALID_UNRESOLVED_COMPOSITION`
- `VALID_UNRESOLVED_EXECUTION`
- `VALID_UNRESOLVED_VERIFICATION`
- `VALID_UNRESOLVED_MISSING_CAPABILITY`
- `VALID_AMBIGUOUS_INPUT`
- `VERIFIED_SAFE_HALT`

Invalid/non-evidence outcomes include infrastructure/configuration/harness/model-unavailable/output-limit conditions and must have `score=null`.

## Anti-cheating rules

- Behavioral family names and required capability labels are hidden from non-oracle routing/model arms.
- No engine sees sealed answers or expected final state.
- Rescue interventions are recorded separately from original outcomes.
- Oracle IR may prove a downstream ceiling but cannot count as semantic success.
- Frontier systems receive equivalent generic tool access.
- Same-world comparisons are paired by immutable world identity.
- Held-out representation styles and world seeds are sealed before live execution.
- Model confidence is never evidence.
- A model cannot verify its own result.

## Metrics and generated maps

The reporter must automatically produce:

1. computational coverage map
2. minimum-basis map
3. unique engine-value map
4. synergy matrix
5. substitution/redundancy matrix
6. semantic degradation curve
7. semantic-error taxonomy
8. decomposition-error rate
9. routing-regret curve
10. tool-overload curve
11. model-dependence Pareto frontier
12. verification-value measurement
13. silent-wrong rate
14. capability-learning curve
15. transfer/drift curve
16. horizon curve
17. frontier-gap decomposition
18. missing-capability clusters
19. rescue/bottleneck distribution
20. next-direction Pareto set

## Production Fitness Record

Every experimentally useful capability receives a production mapping containing:

- capability identifier
- measured contribution and affected domains
- model calls displaced
- composition compatibility
- determinism/replay properties
- independent verification contract
- estimated CPU/RAM/VRAM/storage/latency/idle cost
- isolation requirement
- state requirement
- failure containment
- replaceability contract
- V31M4 integration seam
- candidate roadmap displacement
- engineering/maintenance estimate
- evidence confidence
- promotion status: `EXPERIMENTAL`, `REPLICATED`, or `PROMOTION_CANDIDATE`

010 never promotes code to V31M4 automatically.

## V31M4 compatibility invariants

Discoveries intended for promotion must preserve:

- production state remains owned by the authoritative V31M4 runtime
- models/tools/adapters never directly mutate domain state
- model output remains an untrusted proposal
- deterministic verification is independent whenever available
- labs remain isolated from production state
- external/provider details stay behind replaceable boundaries
- failures are typed and contained
- evidence is immutable and traceable

## Profiles

`smoke` — small deterministic subset for CI and harness verification.

`atlas` — full deterministic Phase A/B and synthetic composition/rescue coverage with no external model requirement.

`local` — adds live local semantic/router/model arms through configured Ollama-compatible endpoint.

`frontier` — adds paired configured frontier calibration; credentials/providers remain external configuration.

No unavailable live phase is silently converted to a capability failure.

## Durability and reproducibility

010 reuses the 008/009 evidence discipline:

- preregistered deterministic ledger
- SHA-256 ledger identity
- atomic per-cell evidence envelopes
- resume from terminal cells
- changed-ledger output-directory refusal
- explicit invalid/non-evidence statuses
- no capability-based early termination
- deterministic replay fingerprint for deterministic phases

## Implementation boundary for 010 v1

The first implementation must provide the complete experiment framework, TaskIR contract, deterministic world generator, capability registry/reference engines, full Phase A/B attribution, rescue localization, composition probes, capability-accumulation probes, automatic report maps, production fitness records, CLI profiles, tests, and CI.

Live local-model and frontier-model execution must be represented by strict provider-neutral interfaces and configuration, but CI is not allowed to require model/network credentials. Their absence is reported as explicit unavailable evidence rather than scientific failure.

The reference engines are scientific adapters used to test computational capability classes. A positive 010 result is not by itself permission to copy a reference engine into V31M4; production promotion should prefer mature implementations behind V31M4 contracts when appropriate.
