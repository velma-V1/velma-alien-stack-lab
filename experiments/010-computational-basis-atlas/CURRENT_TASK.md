# CURRENT TASK — 010-C-D-PREFLIGHT-REVIEW

OWNER := GPT + user
EXECUTOR := Claude Code
MODE := adversarial review

OBJECTIVE:
    determine whether Experiment 010 Phase C/D is scientifically and operationally ready
    BEFORE any real local-model C/D evidence is collected

ASSUME:
    current implementation may be wrong
    GPT claims may be wrong
    green tests may encode a bad assumption

READ_FIRST:
    CLAUDE.md
    experiments/010-computational-basis-atlas/PREREGISTRATION-C-I-v1.md [global readiness + Phase C/D]
    alien_lab/computational_atlas_surfaces.py
    alien_lab/computational_atlas_semantics.py
    alien_lab/computational_atlas_providers.py
    alien_lab/computational_atlas_live_types.py
    alien_lab/computational_atlas_live_ledger.py [C/D builders only]
    alien_lab/computational_atlas_live_runner.py [C/D functions only]
    tests/test_computational_atlas_live.py [C/D contract/execution tests]
    tests/test_computational_atlas_claims.py [phase gate]

SEARCH_IF_NEEDED:
    direct imports/dependencies of the above only

DO_NOT_READ_BY_DEFAULT:
    experiments/001-009
    results/** cell directories
    G/H/I implementation ideas
    V31M4 repo

VERIFY:
    1. C worlds/representations/arms/seeds exactly match preregistration
    2. D worlds/representations/arms/seeds exactly match preregistration
    3. non-oracle surfaces contain no answer/capability/solver/family leakage
    4. R5 is a real stable artifact and provider actually receives image bytes
    5. MODEL_DIRECT does not receive oracle TaskIR
    6. LOCAL_SEMANTIC_COMPILER_BASIS receives only permitted surface information
    7. ORACLE_IR_BASIS is scored only as downstream ceiling, never semantic success
    8. deterministic recognizer has no hidden/oracle access
    9. free JSON vs constrained vs repair treatment is fair
    10. D repair permits max exactly one additional model call
    11. malformed semantic output is valid unresolved, not infrastructure failure
    12. provider/network unavailable => score:null
    13. rescue preserves original score
    14. model cannot verify itself
    15. scoring compares exact paired world result
    16. no post-hoc performance-based membership selection exists
    17. output/token/context settings cannot silently differ by arm except preregistered interface constraint
    18. no code path can auto-advance into G/H/I
    19. a complete C/D live run has an executable batch/CLI path; unit-callable functions alone are NOT sufficient
    20. run manifest seals system_version + provider_kind + model_id/digest when available + endpoint + generation contract + prompt contract + ledger identity BEFORE first live scored cell
    21. output directory reuse with changed ledger/model/provider/system/prompt identity is rejected
    22. fake-provider/controlled-fixture evidence can never be reported as LIVE_MODEL_EVIDENCE
    23. per-cell evidence is immutable/hash-checked/resumable without silently repairing valid evidence
    24. retry accounting matches preregistration and provider transport failure cannot become a capability zero

ADVERSARIAL_CHECKS:
    SEARCH oracle contamination
    SEARCH hidden labels
    SEARCH test data generated from answer
    SEARCH scoring shortcuts
    SEARCH deterministic parser that trivially reconstructs synthetic grammar
    SEARCH provider behavior inconsistent across arms
    SEARCH invalid evidence accidentally scored zero
    SEARCH output cap likely to invalidate strong models
    SEARCH run-identity/evidence persistence gaps
    SEARCH any condition that makes us look better than reality

IF defect_found:
    classify := HARNESS_BUG | SCIENTIFIC_FLAW | IMPLEMENTATION_BUG | EVIDENCE_RISK

    IF fix preserves frozen semantics AND does not make test easier:
        write failing regression test
        fix minimum code
        rerun targeted tests
        rerun relevant 010 regressions

    ELSE:
        DO_NOT_CHANGE
        report CONTRACT_CONFLICT

PHASE_BOUNDARY:
    G/H/I := STOP
    do not implement runtime/system behavior
    do not add execution tests requiring G/H/I implementation
    frozen G/H/I definitions/ledgers may be inspected only if needed to prove no auto-advance path

DONE_WHEN:
    C/D preregistration trace is complete
    complete live C/D execution path is auditable and identity-sealed
    no unresolved blocker remains for live C/D execution
    test evidence is reproducible
    G/H/I boundary is confirmed closed

RETURN:
    STATUS
    FILES_READ
    FILES_CHANGED
    DEFECTS_FOUND
    EVIDENCE
    TESTS_RUN
    TEST_RESULTS
    SCIENTIFIC_IMPACT
    PREREGISTRATION_IMPACT
    READY_FOR_LIVE_C_D := YES | NO
    G_H_I_BOUNDARY_CLOSED := YES | NO
    UNRESOLVED
    COMMIT
