# Experiment 010 C/D Pre-Live Adjudication — 2026-08-29

STATUS := PRE_LIVE
LIVE_C_D_EVIDENCE_ACCEPTED := false
G_H_I_RUNTIME_GATE := closed

## Provenance

An external Claude Code preflight review reported eight implementation defects and five unresolved A-E findings. Claude also reported a local commit `d5d0e46`, but that commit is not present on the shared GitHub branch at the time of this record.

Therefore:

```text
CLAUDE_REVIEW := external review evidence
CLAUDE_LOCAL_COMMIT := unavailable to shared repo
GPT_ACTION := independently reproduce every material finding before claiming it fixed
DO_NOT := reconstruct or represent d5d0e46 as if independently verified
```

The shared GitHub branch remains the source of code truth.

## Operating formula

```text
USER:
    objective authority / approval at genuine scientific-contract decisions

GPT:
    primary 010 engineer
    TDD implementation
    Q0-Q36 adjudication
    evidence analysis
    independent verification

KIMI_WEBSITE:
    frequent read-only adversarial reviewer
    attacks design, code, claims, construct validity, and interpretation
    cannot change repo or certify tests
    every material Kimi claim must be independently reproduced by GPT before action

CLAUDE:
    scarce independent adversarial reviewer
    not routine reviewer
    reserved for a major gate only when GPT+Kimi evidence leaves material uncertainty,
    or for the C-F architecture tribunal before G/H/I system mechanisms are designed

FROZEN_010:
    referee

MEASURED_DATA:
    scientific authority over architecture claims
```

### Reviewer escalation rule

```text
GPT builds/tests
    -> Kimi read-only attack
    -> GPT reproduces/refutes Kimi findings
    -> tests/data decide

IF material disagreement remains AND current evidence cannot discriminate:
    use Q14 := cheapest discriminating check

IF high-impact ambiguity still remains after discrimination:
    Claude narrow red-team may be authorized by user
```

Model agreement is never evidence.

## Q0-Q36 adjudication rule

For each proposed fix or architectural claim:

```text
CHECK:
    Q0  decisive question still unasked
    Q1  actual success requirement
    Q2  true failure class
    Q3  assumptions to attack
    Q4  causally proven mechanisms/effect size
    Q5  serious alternative solution classes
    Q6  architecture without current-path anchoring
    Q7  strongest discriminating next action
    Q8  model capability fundamentally missing
    Q9  independent computation that can supply it
    Q10 typed information exchange
    Q11 complementary capability per component
    Q12 strongest architecture consistent with evidence
    Q13 structural ceilings
    Q14 cheapest decision-changing discrimination
    Q15 proof capability was created, not rearranged
    Q16 falsifier for our interpretation
    Q17 proxy vs direct measurement
    Q18 evidence threshold for architecture change
    Q19 serious alternatives remaining
    Q20 best architecture if forced to choose now
    Q21 causal accounting for claimed gain
    Q22 largest verified contribution
    Q23 necessity from ablation/leave-one-out
    Q24 exact end-to-end point where capability appears/disappears
    Q25 genuine causal synergy
    Q26 strongest argument against preferred interpretation
    Q27-Q36 production seam, authority, economics, isolation, verification,
            replaceability, ROI, roadmap displacement, compounding, competitive consequence

ALWAYS CHECK:
    construct validity
    direct measure vs proxy
    causal isolation
    paired identity
    oracle leakage
    hidden protocol guessing
    benchmark-specific shortcut
    silent-wrong behavior
    independent verification
    falsifier / alternative explanation

IF evidence cannot distinguish alternatives:
    VERDICT := MORE_DISCRIMINATION_REQUIRED
```

System improvements may use evidence. The frozen test may not be changed to improve observed performance.

An implementation that fails to instantiate the already-frozen construct is not protected merely because it is difficult; restoring the intended construct is contract restoration, not score optimization.

## A-E findings and current adjudication

### A — R5 perceptual renderer

REPORTED_FINDING:
    current `_render_text_png` encodes UTF-8 bits as tiny horizontal marks rather than readable glyphs.

FROZEN_CONSTRUCT:
    R5 is a rendered document/table/diagram/screenshot subset containing the same underlying problem information.

CURRENT_CLASSIFICATION := CONTRACT_RESTORATION

RATIONALE:
    an unreadable barcode does not instantiate the preregistered perceptual construct.
    restoring human/model-readable deterministic glyph rendering is required before live R5 evidence.
    task facts, seeds, answers, scoring, membership, and difficulty semantics must remain unchanged.

ACCEPTANCE:
    deterministic real image
    visible glyph-based text
    paired semantic content unchanged
    no capability/engine/family/answer leakage inside image pixels or text channel
    image bytes reach image-capable provider arms

### B — private intent vocabulary

REPORTED_FINDING:
    validator accepts a fixed private intent vocabulary while the TaskIR schema exposes `intent` only as an unconstrained string and the semantic prompt does not enumerate the allowed values.

FROZEN_CONSTRUCT:
    Phase C/D measures conversion into the exact TaskIR contract and separates syntax/interface effects from semantic correctness.

CURRENT_CLASSIFICATION := CONTRACT_RESTORATION_PENDING_TEST

RATIONALE:
    forcing a model to guess undocumented protocol tokens measures hidden-vocabulary guessing in addition to semantic formalization.
    the allowed TaskIR intent vocabulary is part of the interface contract, not an answer key or capability assignment.
    exposing the same frozen vocabulary to every semantic-interface arm restores the intended interface while preserving the semantic task.

GUARD:
    vocabulary disclosure must be identical across relevant semantic arms.
    it may describe legal TaskIR values but may not reveal which value applies to a particular task.

### C — deterministic recognizer inversion

REPORTED_FINDING:
    recognizer infers intent from exact generator payload key sets, yielding near-tautological recognition on R1/R4 and no general recognition elsewhere.

CURRENT_CLASSIFICATION := INTERPRETATION_LIMITATION

ACTION:
    keep the frozen arm and its scores.
    do not cite it as evidence of general non-neural semantic recognition.
    report it as a narrow structured-key recognizer / deterministic lower-bound baseline.

CLAIM_GUARD:
    no production promotion or broad semantic-recognition claim may rely on this arm alone.

### D — semantic-formalization tax/report aggregation missing

REPORTED_FINDING:
    live summary pools arms and does not implement the preregistered paired semantic-formalization tax or required per-arm/per-representation aggregation.

CURRENT_CLASSIFICATION := MISSING_PREREGISTERED_INSTRUMENTATION

ACTION:
    implement reporting only; do not change cell scores.

REQUIRED:
    arm-separated verified success
    representation-separated verified success
    paired in-basis ORACLE_IR_BASIS minus LOCAL_SEMANTIC_COMPILER_BASIS semantic-formalization tax
    no rescued score substitution
    oracle ceiling never counted as semantic success

### E — rescue ladder incomplete

REPORTED_FINDING:
    current C rescue implements only oracle-TaskIR substitution and can localize only SEMANTIC or MISSING_CAPABILITY.

FROZEN_CONSTRUCT:
    original -> oracle TaskIR -> oracle decomposition -> oracle routing -> oracle engine outputs -> oracle typed handoff -> oracle execution -> verifier discrimination.

CURRENT_CLASSIFICATION := MISSING_PREREGISTERED_INSTRUMENTATION

ACTION:
    implement the frozen diagnostic ladder without changing original scores.

GUARD:
    stages that are structurally indistinguishable for a given cell must be reported explicitly rather than fabricated.
    rescue evidence is diagnostic only.

## Previously reported implementation defects — GPT reproduction queue

Claude's review additionally reported these concrete defects. They are not accepted as fixed until reproduced on the shared branch:

```text
1. D repair incorrectly triggered on verifier failure rather than TaskIR invalidity
2. free vs constrained JSON had asymmetric parser behavior
3. provider structured-output support could be silently absent
4. repair-call transport failure could become capability zero
5. provider identity could be caller-asserted and fixture evidence mislabeled live
6. deterministic recognizer copied sealed/oracle metadata
7. outside-basis localization differed by arm
8. existing R5 leakage guard did not inspect image content comprehensively
```

GPT must reproduce each with a failing test before changing production behavior.

## Kimi read-only review contract

After GPT reports the pre-live implementation green, Kimi receives only the shared branch plus a narrow review request.

Kimi must:

```text
ASSUME GPT may be wrong
ASSUME green tests may encode bad assumptions
USE Q0-Q36 + mandatory 32 questions
ATTACK construct validity, causal validity, leakage, fairness, proxies, unsupported claims
DO NOT redesign the test merely because a result may be unfavorable
DO NOT claim a code/test execution occurred if website access cannot execute it
RETURN blockers, weaknesses, unsupported claims, strongest counterargument,
       what C/D can prove, what C/D cannot prove, confidence
```

GPT then reproduces or refutes each material Kimi finding before live evidence.

## Anti-overfitting promotion rule

A system change is suspect if it cannot be described without benchmark internals.

```text
CAN_DESCRIBE_CHANGE_WITHOUT:
    010 task IDs
    seeds
    generator-family checks
    expected answers
    benchmark-specific constants
    known scored failure examples

IF false:
    reject production promotion until independently justified
```

## Rebuilt staged evidence loop

```text
A/B evidence
    -> GPT reproduce Claude implementation findings under TDD
    -> GPT restore/verify A/B/D/E instruments and C claim guard
    -> GPT full Q0-Q36 pre-live self-attack
    -> Kimi read-only Q0-Q36 red-team
    -> GPT reproduce/refute Kimi findings
    -> IF unresolved high-impact ambiguity remains: user may authorize narrow Claude gate
    -> freeze S0 + M0
    -> run C/D
    -> GPT Q0-Q36 evidence analysis
    -> Kimi independent result interpretation
    -> GPT reproduce/adjudicate disagreements using Q14 discrimination
    -> build only causally justified S1
    -> rerun same C/D when comparison is needed
    -> E
    -> tribunal
    -> F
    -> full C-F GPT+Kimi tribunal
    -> reserve Claude for unresolved major architecture gate if needed
    -> HARD STOP before G/H/I
```

No live G/H/I runtime is authorized by this record.
