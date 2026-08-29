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

CLAUDE:
    scarce independent adversarial reviewer
    reserved for major irreversible gates

FROZEN_010:
    referee

MEASURED_DATA:
    scientific authority over architecture claims
```

Claude is reserved for:

1. a narrow final red-team immediately before accepting the first live C/D evidence;
2. a major C-F architecture tribunal before live G/H/I mechanisms are designed.

## Q0-Q36 adjudication rule

For each proposed fix or architectural claim:

```text
CHECK:
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

## Staged evidence loop

```text
A/B evidence
    -> restore/verify C/D instruments
    -> final narrow Claude red-team
    -> freeze S0 + M0
    -> run C/D
    -> GPT Q0-Q36 evidence analysis
    -> build only causally justified S1
    -> rerun same C/D when comparison is needed
    -> E
    -> tribunal
    -> F
    -> full C-F tribunal
    -> HARD STOP before G/H/I
```

No live G/H/I runtime is authorized by this record.
