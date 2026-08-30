# KIMI REVIEW TASK — 010-C-D-POSTFIX-READONLY-REDTEAM

STATUS := READY_TO_RUN
MODE := READ_ONLY
REVIEWER := Kimi website
GPT_ENGINEERING_STATUS := READY_FOR_FINAL_KIMI_REVIEW
CLAUDE := HOLD
G_H_I_RUNTIME_GATE := CLOSED

OBJECTIVE:
    perform one narrow post-fix adversarial review of Phase C/D
    before any real local-model C/D evidence is accepted

ASSUME:
    GPT may still be wrong
    tests may encode a bad assumption
    a restored implementation may still measure the wrong construct
    prior Claude/Kimi findings may be incomplete

DO_NOT_BROADLY_EXPLORE_REPO.

READ_FIRST:
    experiments/010-computational-basis-atlas/GPT_CURRENT_TASK.md
    experiments/010-computational-basis-atlas/KIMI-C-D-REVIEW-ADJUDICATION-2026-08-29.md
    experiments/010-computational-basis-atlas/PREREGISTRATION-C-I-v1.md [global readiness + C/D only]
    .claude/skills/010-tribunal/tribunal.md

READ_IMPLEMENTATION:
    alien_lab/computational_atlas_surfaces.py
    alien_lab/computational_atlas_semantics.py
    alien_lab/computational_atlas_providers.py
    alien_lab/computational_atlas_live_runner.py
    alien_lab/computational_atlas_live_experiment.py
    alien_lab/computational_atlas_live_ledger.py [C/D only]

READ_TESTS:
    tests/test_computational_atlas_live_cd_preflight.py
    tests/test_computational_atlas_live_config_preflight.py
    tests/test_computational_atlas_live_scientific_self_attack.py
    tests/test_computational_atlas_live_harness.py
    .github/workflows/010-smoke.yml

TRUST_BOUNDARY:
    You may inspect committed CI/test definitions and GPT's recorded CI evidence.
    You cannot independently claim tests or commands were executed from website read-only access.
    Treat execution claims as evidence to audit, not actions you personally performed.

USE:
    Q0-Q36 as an adversarial tribunal
    mandatory 32 Experiment 010 questions only where they materially affect C/D readiness

VERIFY_POST_FIX:
    1. R5 is a readable deterministic image/document artifact carrying the same semantic task information
    2. R5 source/image path does not leak capability, solver, family, intent assignment, or answers
    3. legal TaskIR intent vocabulary disclosure is interface syntax, identical across semantic arms, not task-specific answer leakage
    4. free JSON and constrained arms are not advantaged by asymmetric parsing
    5. D repair is allowed only for deterministic invalid/non-executable TaskIR, never merely wrong final verification
    6. repair transport failure is score:null infrastructure evidence
    7. structured-output support/config is validated before constrained evidence
    8. provider kind/model/endpoint/version/digest/context identity cannot silently differ from sealed RunIdentity
    9. sealed context_limit is actually enforced in Ollama request execution
    10. fake/fixture evidence cannot receive a live-evidence verdict
    11. unsupported R5 image modality is valid unresolved PERCEPTION, not a semantic zero or infrastructure outage
    12. HTTP application-level image rejection is not retried as transport failure
    13. semantic-formalization tax is paired on identical in-basis worlds and does not give semantic credit to oracle/rescue outcomes
    14. Phase D exposes syntax_valid, schema_valid, semantic_executable, end_to_end_verified separately
    15. rescue never overwrites original evidence
    16. rescue preserves frozen rung ordering but explicitly marks collapsed/not-applicable rungs instead of fabricating localization
    17. rescue evidence is automatically persisted separately for eligible valid-unresolved C cells
    18. deterministic recognizer has no sealed oracle metadata and claims remain narrow
    19. outside-basis status is not distorted by arm-specific parser ordering
    20. no path can execute G/H/I

ANTI_DELUSION_ATTACK:
    identify any remaining way C/D could look better than reality
    identify any remaining way C/D could look worse because the instrument is invalid
    identify proxy measurements being overstated as direct capability
    identify any benchmark-specific shortcut introduced by the fixes
    identify any claim that is broader than the frozen evidence can establish

DO_NOT_PROPOSE:
    performance-conditioned live pilot
    stopping/skipping C/D because a subset performs poorly
    new control arms in frozen 010-v1
    easier scoring
    altered seeds/tasks/arms/membership
    post-hoc representation dropping
    G/H/I implementation

IF you believe a new control or broader test is scientifically valuable:
    classify := FUTURE_VERSION_IDEA
    do not make it a condition for changing frozen 010-v1 unless the existing measurement is genuinely invalid

FOR_EACH_MATERIAL_FINDING:
    cite exact file/function/test evidence
    classify := BLOCKER | NONBLOCKING_LIMITATION | FUTURE_VERSION_IDEA | CLAIM_LIMITATION
    state the falsifier or cheapest credential-free discriminating check if static inspection cannot settle it

RETURN:
    STATUS := COMPLETE | INCOMPLETE
    FILES_READ
    POST_FIX_BLOCKERS := maximum 10, only evidence-invalidating issues
    NONBLOCKING_LIMITATIONS
    UNSUPPORTED_CLAIMS
    NEW_FINDINGS_NOT_IN_PRIOR_REVIEW
    STRONGEST_ARGUMENT_AGAINST_LIVE_C_D
    STRONGEST_ARGUMENT_AGAINST_YOUR_OWN_CONCLUSION
    WHAT_C_D_CAN_PROVE
    WHAT_C_D_CANNOT_PROVE
    Q0_Q36_MATERIAL_FINDINGS
    MATERIAL_FINDINGS_FOR_GPT_TO_REPRODUCE
    POST_FIX_BLOCKER := YES | NO | UNCERTAIN
    READY_FOR_LIVE_C_D := YES | NO | UNCERTAIN
    CONFIDENCE := 0-100%

IF static evidence cannot distinguish alternatives:
    VERDICT := MORE_DISCRIMINATION_REQUIRED

Do not modify the repository.
