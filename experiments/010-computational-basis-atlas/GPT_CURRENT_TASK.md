# GPT CURRENT TASK — 010-C-D-LIVE-RUN-GATE

OWNER := user
EXECUTOR := GPT
KIMI := OPTIONAL_NOT_A_GATE
CLAUDE := HOLD
STATUS := READY_FOR_LOCAL_LIVE_C_D
READY_FOR_LIVE_C_D := YES
G_H_I_RUNTIME_GATE := CLOSED

OBJECTIVE:
    execute the frozen Phase C/D experiment against the real local Ollama model
    only after GitHub Actions has mechanically verified the pre-live harness.

SOURCE_OF_TRUTH:
    experiments/010-computational-basis-atlas/PREREGISTRATION-C-I-v1.md
    experiments/010-computational-basis-atlas/PREFLIGHT-ADJUDICATION-2026-08-29.md
    experiments/010-computational-basis-atlas/KIMI-C-D-REVIEW-ADJUDICATION-2026-08-29.md
    .claude/skills/010-tribunal/tribunal.md

METHOD:
    USE Q0-Q36 for interpretation and architecture claims
    shared GitHub branch := code truth
    executable tests/CI := mechanical pre-live authority
    live local Ollama evidence := runtime/model authority
    model-reviewer agreement := never a substitute for evidence

FROZEN_CONTRACT_PRESERVED:
    C_CELLS := 3840
    D_CELLS := 576
    C_SEED := 20260910
    D_SEED := 20260911
    C_ARMS := unchanged
    D_ARMS := unchanged
    REPRESENTATIONS := unchanged
    SCORING_MEMBERSHIP := unchanged
    G_H_I_RUNTIME := disabled

RESOLVED_BLOCKERS:
    1. D repair no longer triggers merely because final verification is wrong
    2. free/constrained JSON reading is arm-symmetric
    3. constrained D requires declared structured-output support
    4. repair-call transport failure is infrastructure score:null
    5. runtime provider kind/model/endpoint/version/digest/context are checked against sealed RunIdentity
    6. fake/fixture runs are explicitly non-live evidence
    7. deterministic recognizer no longer copies sealed oracle verification/task metadata
    8. outside-basis localization is consistent with MISSING_CAPABILITY contract
    9. R5 is deterministic readable glyph-based PNG, not a bit barcode
    10. leakage sweep checks rendered R5 source content as well as wrappers
    11. legal TaskIR intent vocabulary is disclosed as interface syntax identically to semantic-interface arms
    12. semantic-formalization tax plus arm/representation aggregation is implemented
    13. Phase D emits syntax/schema/semantic-executable/end-to-end diagnostics
    14. rescue preserves all frozen rung names while marking collapsed/not-applicable rungs honestly
    15. rescue evidence is persisted separately from original evidence
    16. sealed context_limit is enforced in Ollama requests via num_ctx
    17. selected Ollama model digest is verified from provider state before scoring
    18. Ollama model capabilities are checked before live scoring
    19. R5 unsupported image modality is valid unresolved PERCEPTION, score 0
    20. Ollama HTTP application-level image rejection is not retried/misclassified as transport outage
    21. perception rescue localizes PERCEPTION without overwriting original score
    22. Phase C does not fabricate separate ORACLE_EXECUTION / VERIFIER_DISCRIMINATION evidence when those interventions are not independently identifiable

SCIENTIFIC_DECISIONS:
    R5 := CONTRACT_RESTORATION
    INTENT_VOCABULARY := CONTRACT_RESTORATION
    DETERMINISTIC_RECOGNIZER := KEEP_FROZEN_ARM + LIMIT_CLAIMS
    REPORTING := MISSING_PREREGISTERED_INSTRUMENTATION_RESTORED
    RESCUE := FROZEN_RUNG_STRUCTURE_RESTORED_WITH_COLLAPSE_DISCLOSURE
    PERCEPTION := FROZEN_LOCALIZATION_LABEL_RESTORED

REJECTED_CHANGES:
    no performance-conditioned live pilot
    no new random/shuffled control arm in 010-v1
    no seed/task/arm/scoring changes
    no post-hoc phase dropping
    no benchmark-specific production shortcut

D_REPAIR_RULE:
    permit second call only when deterministic validation establishes
    syntactic/schema/semantic TaskIR invalidity or non-executability
    never because an otherwise valid executable TaskIR merely fails final verification

Q0_Q36_SELF_ATTACK_ADDITIONS:
    runtime context must equal sealed context budget
    runtime model digest/capabilities must be established before evidence
    unsupported R5 modality is PERCEPTION rather than generic semantic/infrastructure failure
    HTTP application errors must not masquerade as transport failures
    rescue must not claim causal localization where intervention layers collapse

TDD_EVIDENCE:
    RED_RUN_INITIAL := workflow #79, 108 tests, 10 failures + 2 errors
    RED_RUN_AFTER_IDENTITY_FIXES := workflow #81, 108 tests, 7 failures
    GREEN_CODE_HEAD := 4663fd54a77e023a74e346bce0c17a51e2fe1c14
    GREEN_RUN := workflow #83
    GREEN_TESTS := 108/108 OK

FINAL_GITHUB_MECHANICAL_GATE:
    VERIFIED_HEAD_BEFORE_STATUS_UPDATE := 2d59813c89f80f75c9226ce23e37e249fe2c6aba
    WORKFLOW := #88
    RESULT := SUCCESS
    REGRESSION_TESTS := PASS
    CREDENTIAL_FREE_SMOKE := PASS
    FULL_18112_DETERMINISTIC_ATLAS := PASS
    EVIDENCE_UPLOAD := PASS

DETERMINISTIC_VERIFICATION:
    smoke.expected_cells := 324
    smoke.invalid_cells := 0
    smoke.ledger_hash := 8d34d04edbc79627f1c958a4b0836e1f4d315ef462a9f738ffd613f2a80baf0c
    full.expected_cells := 18112
    full.terminal_cells := 18112
    full.invalid_cells := 0
    full.verified_successes := 6104
    full.valid_unresolved := 12008
    full.model_calls := 0
    full.ledger_hash := 8b549d60d652f6d435ac1d2bc2631b00c01c454ca2522830f4a47b9ad74b8878
    full.replay_fingerprint := cda5d1ec6bec048c4cce0625ff3553b264f7f668ce607db70378f98f5df750ff

INTERPRETATION_LIMITS:
    C/D does not prove real-world semantic generalization
    deterministic recognizer does not prove general non-neural semantic recognition
    C/D does not prove frontier superiority
    C/D does not prove V31M4 production superiority
    C/D does not prove true multi-engine causal synergy; Phase F is required
    collapsed rescue rungs cannot support separate localization claims

GITHUB_LIMIT:
    GitHub-hosted runners cannot reach the user's localhost Ollama service.
    Therefore GitHub Actions proves the harness/config/mechanical invariants,
    but the frozen live C/D evidence must execute on the local machine against the sealed Ollama model/runtime.

NEXT:
    run complete frozen C/D locally using one sealed SYSTEM_VERSION and MODEL identity
    do not change VELMA/system implementation between C and D baseline cells
    preserve manifest/ledger/evidence artifacts
    then perform GPT Q0-Q36 evidence adjudication
    Kimi/Claude are optional escalation reviewers only if evidence remains genuinely ambiguous

DO_NOT:
    add another mandatory model-review gate
    inspect model performance on a pilot and condition continuation on results
    modify frozen C/D after seeing live results
    open G/H/I runtime
