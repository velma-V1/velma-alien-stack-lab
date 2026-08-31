# Kimi C/D Read-Only Red-Team Adjudication — 2026-08-29

STATUS := GPT_REPRODUCTION_COMPLETE_FOR_STATIC_FINDINGS
LIVE_C_D_EVIDENCE_ACCEPTED := false
READY_FOR_LIVE_C_D := false
CLAUDE := HOLD
G_H_I_RUNTIME_GATE := closed

## Provenance

Kimi website returned `STATUS := INCOMPLETE`, `READY_FOR_LIVE_C_D := NO`, confidence 85%, after reading the frozen C/D contract and the shared implementation. Kimi had read-only access and did not execute tests.

This record distinguishes:

```text
KIMI_CLAIM := external static-review finding
GPT_REPRODUCED := finding confirmed directly against shared branch code / frozen contract
GPT_REJECTED := recommendation conflicts with frozen methodology or is unsupported
MORE_DISCRIMINATION_REQUIRED := static inspection cannot settle the claim
```

Model agreement is not evidence. Claude+Kimi convergence raises review priority but does not replace RED/GREEN tests.

## GPT adjudication of Kimi blockers

### K1 — R5 unreadable bit renderer

VERDICT := GPT_REPRODUCED / BLOCKER

`_render_text_png` serializes UTF-8 bits into sparse horizontal marks rather than rendering glyphs. Frozen R5 requires R1/R2 information rendered into a real image/document artifact. This is contract restoration, not score optimization.

### K2 — D repair triggered by end-to-end failure

VERDICT := GPT_REPRODUCED / BLOCKER

Current repair condition is based on `outcome.get("score") != 1`, so a syntactically/schema-valid, semantically executable TaskIR that merely produces the wrong verified answer can receive a second model call. That is an oracle-selected second guess and violates the frozen mechanism.

CORRECTION_TO_KIMI_FIX_WORDING:

Repair should not be reduced mechanically to `ir is None` only. Frozen D permits repair when the first TaskIR is syntactically, schema, or semantically invalid. The correct repair predicate is deterministic TaskIR invalidity/non-executability, never verifier disagreement on an otherwise valid executable IR.

### K3 — asymmetric JSON reading

VERDICT := GPT_REPRODUCED / BLOCKER

Ollama schema-constrained responses pass through fenced-JSON stripping in the provider while unconstrained FREE_JSON can later receive raw `json.loads(response.text)`. Byte-identical fenced JSON can therefore be treated differently by arm for parser reasons rather than structured-output efficacy.

### K4 — repair transport failure becomes capability zero

VERDICT := GPT_REPRODUCED / BLOCKER

The final D failure classification reads `first.error_kind`; when the first call succeeds and the repair call fails transport, the current path can classify the cell as valid unresolved semantic instead of invalid infrastructure `score:null`.

### K5 — structured-output support not gated

VERDICT := GPT_REPRODUCED / BLOCKER

The adapter contract does not declare/check whether structured output is supported before entering constrained D arms. Frozen D explicitly requires lack of structured-output support to be invalid configuration, not a zero.

LIMIT:

An adapter capability declaration is necessary but does not by itself prove a remote/server version actually enforces the schema. Provider/version identity must remain sealed, and live preflight must reject configurations that cannot establish the required interface.

### K6 — hidden intent vocabulary

VERDICT := GPT_REPRODUCED / CONTRACT_RESTORATION BLOCKER

The validator enforces a private finite intent vocabulary while the schema exposes bare `string` and the semantic prompt does not enumerate legal values. This conflates hidden-protocol guessing with semantic formalization. The frozen legal vocabulary is interface syntax, not a task-specific answer.

### K7 — rescue ladder incomplete

VERDICT := GPT_REPRODUCED / BLOCKER

Current `rescue_phase_c_outcome` implements only oracle-TaskIR substitution and emits only SEMANTIC or MISSING_CAPABILITY. The frozen rescue order contains eight stages.

ADDITIONAL GPT FINDING:

The live C/D evidence harness does not automatically persist rescue evidence for every original valid unresolved local semantic C cell. Therefore the missing work is both (a) full ladder semantics and (b) automatic separate rescue evidence integration.

### K8 — semantic-formalization tax/reporting absent

VERDICT := GPT_REPRODUCED / BLOCKER

`run_live_cells` pools totals and lacks frozen arm-separated, representation-separated, and paired in-basis `ORACLE_IR_BASIS - LOCAL_SEMANTIC_COMPILER_BASIS` reporting.

ADDITIONAL GPT FINDING:

Phase D also does not currently expose all frozen scoring diagnostics (`syntax_valid`, `schema_valid`, `semantic_executable`, `end_to_end_verified`) as explicit evidence fields.

### K9 — R5 leakage guard is vacuous for image content

VERDICT := GPT_REPRODUCED / BLOCKER FOR R5 RESTORATION

The existing test serializes the surface wrapper. It does not establish that the exact source text rendered into R5 is free of forbidden labels. Once R5 becomes readable, the rendered source itself must be exhaustively leakage-checked across all 192 worlds × R5 and paired non-oracle surfaces.

### K10 — outside-basis localization differs by recognizer arm

VERDICT := GPT_REPRODUCED / BLOCKER

The deterministic recognizer can return SEMANTIC before the shared outside-basis classification path, while the frozen C contract says outside-basis worlds remain valid unresolved missing-capability evidence. The base status must not depend on arm-specific parser ordering.

## Additional GPT blockers missed by Kimi

### G1 — provider identity is caller-asserted

Current live harness does not cross-check the runtime provider object's kind/model/endpoint against the sealed `RunIdentity`. A fixture provider can therefore be executed under a caller-supplied live-looking identity.

VERDICT := BLOCKER

### G2 — fixture run can receive completion-looking summary

Fake-provider cells retain `FAKE_MECHANICS_ONLY` per-cell evidence, but the current summary can still report `DISCOVERY_COMPLETE` without an explicit `live_model_evidence:false` / non-live fixture verdict.

VERDICT := BLOCKER

### G3 — deterministic recognizer copies sealed oracle metadata

`_deterministic_recognize` currently copies `world.task_ir.task_id` and `world.task_ir.verification`. These values are inert in the current execution path but violate the non-oracle access boundary and create latent oracle contamination risk.

VERDICT := BLOCKER

### G4 — automatic rescue is not integrated into live persistence

The frozen C contract requires automatic rescue for every original valid unresolved local semantic cell. The live harness currently persists base outcomes only.

VERDICT := BLOCKER

## Kimi nonblocking weaknesses — adjudication

### Synthetic payload-key regularity

VERDICT := REAL LIMITATION / NOT PRE-LIVE BLOCKER

The generator is intentionally synthetic and R1/R4 contain strongly structured records. This limits ecological/generalization claims. It does not invalidate paired representation measurements on the frozen generator. Reporting must not generalize C/D into proof of real-world semantic understanding.

### MODEL_DIRECT vs compiler output contract differs

VERDICT := BY DESIGN / CLAIM LIMITATION

These arms test different system paths. The primary semantic-formalization tax is not MODEL_DIRECT vs compiler; it is paired ORACLE_IR_BASIS vs LOCAL_SEMANTIC_COMPILER_BASIS. Direct-vs-compiler differences may be reported as system-path comparisons only.

### Random/shuffled-text control arm

VERDICT := REJECT_FOR_010_v1

Adding a new arm now changes frozen arm membership. It may be considered only in a future strictly harder/broader versioned extension after the frozen rules permit one; it cannot be inserted into v1 because it seems scientifically attractive after preregistration.

### Small live performance pilot before full C

VERDICT := REJECT AS DECISION GATE

The frozen test prohibits dropping/selecting phase membership based on observed performance. A 40-cell scored pilot used to decide whether the full 3,840-cell C run is worth continuing would violate immutability and create result-driven early termination.

Allowed preflight checks are credential-free/mechanical validity checks that do not inspect live model performance: provider capability/config validation, R5 readability, prompt/schema contract, fake-provider mechanics, identity sealing, score/rescue invariants, and CI.

### Context-window sufficiency

VERDICT := PRE-LIVE CONFIGURATION CHECK

The model/context identity is sealed before first live cell. A selected configuration must be capable of receiving the frozen surface and 2048-output-token contract. Failure to provide a compatible configured model is invalid configuration, not capability zero.

### Outside-basis generator validity

VERDICT := INTERPRETATION LIMITATION

The eight `U` probes are synthetic discovery probes, not proof of mathematically exhaustive impossibility under all conceivable compositions of the basis. Report them as outside the implemented initial-basis contract, not as universal impossibility theorems.

## Q0-Q36 adjudication of Kimi's Q14 recommendation

Kimi proposed a small live R2 pilot as the cheapest discriminating check. GPT rejects that as a performance-conditioned gate because the frozen contract already defines all C cells and forbids dropping an unfavorable phase.

Correct Q14 at this moment is:

```text
Q14 := cheapest check that can invalidate the measurement instrument before live evidence

ANSWER:
    RED/GREEN unit and harness tests for the reproduced blockers
    + deterministic R5 readability/leakage checks
    + provider/config identity checks
    + CI

NOT:
    inspect a subset of live model scores and decide whether the full frozen phase deserves to run
```

## What C/D may claim after blockers are fixed

C/D MAY establish, for the sealed model/system/generator:

- paired representation sensitivity;
- paired semantic-formalization tax on in-basis cells;
- downstream oracle-IR ceiling;
- structured-output interface effects on syntax/schema/semantic-executability/end-to-end verification;
- one-repair-call effect and its explicit model-call/token/time cost;
- rescue-localized bottleneck evidence to the extent each rung is actually distinguishable.

C/D MAY NOT establish by itself:

- real-world semantic generalization outside the frozen generator;
- general non-neural semantic recognition from the deterministic key recognizer;
- frontier-model competitive superiority;
- production V31M4 superiority;
- genuine multi-engine causal synergy (Phase F is required);
- capability accumulation or long-horizon reliability (G/H);
- that every observed formalization failure is "reasoning" rather than prompt/interface/model-specific sensitivity.

## Immediate engineering gate

READY_FOR_IMPLEMENTATION := YES
READY_FOR_LIVE_C_D := NO

Next work is RED -> GREEN on the shared branch. No Claude run is justified by this review: GPT and Kimi materially converge on the main blockers, and the remaining differences are resolvable by the frozen contract and executable tests.
