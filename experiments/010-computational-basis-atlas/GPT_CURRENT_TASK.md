# GPT CURRENT TASK — 010-C-D-PRELIVE-RESTORATION

OWNER := user
EXECUTOR := GPT
KIMI := PRE_FIX_REVIEW_COMPLETE
CLAUDE := HOLD
STATUS := RED_PHASE

OBJECTIVE:
    make Phase C/D capable of producing valid frozen-contract evidence
    without changing the benchmark to improve performance

SOURCE_OF_TRUTH:
    experiments/010-computational-basis-atlas/PREREGISTRATION-C-I-v1.md
    experiments/010-computational-basis-atlas/PREFLIGHT-ADJUDICATION-2026-08-29.md
    experiments/010-computational-basis-atlas/KIMI-C-D-REVIEW-ADJUDICATION-2026-08-29.md
    .claude/skills/010-tribunal/tribunal.md

METHOD:
    USE Q0-Q36 for every claim/fix
    TDD := RED -> minimal GREEN -> regression
    shared GitHub branch := code truth
    prior Claude/Kimi findings := review inputs, never substitute for executable evidence

REPRODUCED_BLOCKERS:
    1. D repair can trigger on end-to-end verifier failure
    2. free/constrained JSON reading is asymmetric
    3. constrained D arm lacks structured-output capability gate
    4. repair-call transport failure can become capability zero
    5. provider identity is not cross-checked against sealed RunIdentity
    6. fake/fixture run can receive completion-looking summary
    7. deterministic recognizer copies sealed oracle metadata
    8. outside-basis localization differs by arm/path
    9. R5 renderer is a bit pattern, not readable glyph document
    10. R5 leakage test does not validate rendered source content
    11. legal TaskIR intent vocabulary is hidden protocol
    12. semantic-formalization tax + arm/representation aggregation missing
    13. Phase D frozen syntax/schema/semantic-executable/end-to-end diagnostics incomplete
    14. rescue ladder is incomplete
    15. automatic rescue evidence is not integrated into live persistence

SCIENTIFIC_DECISIONS:
    R5 := CONTRACT_RESTORATION
    INTENT_VOCABULARY := CONTRACT_RESTORATION
    DETERMINISTIC_RECOGNIZER := KEEP_FROZEN_ARM + LIMIT_CLAIMS
    REPORTING := MISSING_PREREGISTERED_INSTRUMENTATION
    RESCUE := MISSING_PREREGISTERED_INSTRUMENTATION

REJECTED_CHANGES:
    no performance-conditioned 40-cell live pilot
    no new random/shuffled control arm in 010-v1
    no seed/task/arm/scoring changes
    no post-hoc phase dropping

D_REPAIR_RULE:
    permit second call only when deterministic validation establishes
    syntactic/schema/semantic TaskIR invalidity or non-executability
    never because an otherwise valid executable TaskIR merely fails final verification

QUEUE_RED:
    write focused regression tests for each reproduced blocker
    add test module to 010 CI
    observe clean RED attributable only to missing/faulty behavior

QUEUE_GREEN:
    fix minimal code per failing behavior
    keep frozen C/D ledger/seeds/arms unchanged
    implement readable deterministic R5 renderer
    expose same legal intent vocabulary to all semantic-interface arms
    implement explicit D diagnostics
    implement paired live reporting
    implement conservative full rescue ladder with explicit collapsed/not-applicable rungs
    persist rescue separately from original evidence
    harden provider identity + fixture labeling

QUEUE_VERIFY:
    targeted tests
    010 regression set
    deterministic smoke/full atlas
    leakage sweep all 192 × R1-R5 including R5 source text
    Q0-Q36 self-attack

DONE_WHEN:
    every reproduced defect has RED/GREEN evidence
    C/D preregistered metrics are computable
    rescue evidence is automatic, separate, and cannot overwrite original scores
    R5 is readable and leakage-tested
    frozen C/D counts/seeds/arms unchanged
    G/H/I boundary remains closed
    relevant CI/regressions green
    STATUS := READY_FOR_FINAL_KIMI_REVIEW

NEXT:
    Kimi website performs one narrow post-fix read-only review
    GPT reproduces/refutes only new material findings
    Claude remains unused unless a high-impact ambiguity survives executable discrimination
