# KIMI REVIEW TASK — 010-C-D-READONLY-REDTEAM

STATUS := WAIT_FOR_GPT_READY
MODE := READ_ONLY
REVIEWER := Kimi website

DO_NOT_RUN_UNTIL:
    GPT_CURRENT_TASK.md reports READY_FOR_KIMI

OBJECTIVE:
    independently attack the final pre-live Phase C/D design, implementation, and claims
    before any real local-model C/D evidence is accepted

ASSUME:
    GPT may be wrong
    prior Claude findings may be wrong or incomplete
    green tests may encode bad assumptions
    implementation may faithfully implement a bad measurement

READ:
    CLAUDE.md
    experiments/010-computational-basis-atlas/PREREGISTRATION-C-I-v1.md [global + C/D]
    experiments/010-computational-basis-atlas/PREFLIGHT-ADJUDICATION-2026-08-29.md
    experiments/010-computational-basis-atlas/GPT_CURRENT_TASK.md
    .claude/skills/010-tribunal/tribunal.md
    final C/D implementation + corresponding tests only

USE:
    Q0-Q36
    mandatory 32 Experiment 010 questions

ATTACK:
    construct validity
    causal validity
    proxy-vs-direct measurement
    oracle contamination
    answer/capability/solver leakage
    hidden protocol guessing
    unfair arm treatment
    parser/provider artifacts
    invalid evidence scored as capability failure
    rescue overwriting original evidence
    benchmark-specific shortcuts
    ceiling/floor risks
    missing controls
    unsupported claims
    claims C/D cannot actually establish
    anything that could make results look better than reality

SPECIAL_CHECKS:
    R5 actually measures readable perception rather than artifact decoding
    TaskIR legal vocabulary is an interface contract, not task-specific answer leakage
    deterministic recognizer claims are limited to what it directly measures
    semantic-formalization tax is paired and excludes rescued/oracle semantic credit
    rescue stages do not fabricate distinguishability
    no path can execute G/H/I

DO_NOT:
    modify repo
    claim tests/commands were executed if website access cannot execute them
    redesign test merely because likely results are unfavorable
    propose post-hoc easier scoring
    accept GPT claims without repo evidence

RETURN:
    BLOCKERS
    NONBLOCKING_WEAKNESSES
    UNSUPPORTED_CLAIMS
    STRONGEST_ARGUMENT_AGAINST_THE_DESIGN
    WHAT_C_D_CAN_PROVE
    WHAT_C_D_CANNOT_PROVE
    Q0_Q36_FINDINGS
    MATERIAL_FINDINGS_FOR_GPT_TO_REPRODUCE
    READY_FOR_LIVE_C_D := YES | NO | UNCERTAIN
    CONFIDENCE
