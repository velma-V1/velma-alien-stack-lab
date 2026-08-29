# GPT CURRENT TASK — 010-C-D-PRELIVE-RESTORATION

OWNER := user
EXECUTOR := GPT
REVIEWER := Kimi website after implementation green
CLAUDE := HOLD
STATUS := ACTIVE

OBJECTIVE:
    make Phase C/D capable of producing valid frozen-contract evidence
    without changing the benchmark to improve performance

SOURCE_OF_TRUTH:
    experiments/010-computational-basis-atlas/PREREGISTRATION-C-I-v1.md
    experiments/010-computational-basis-atlas/PREFLIGHT-ADJUDICATION-2026-08-29.md
    .claude/skills/010-tribunal/tribunal.md

METHOD:
    USE Q0-Q36 for every claim/fix
    TDD := RED -> minimal GREEN -> regression
    shared GitHub branch := code truth
    Claude prior findings := hypotheses until independently reproduced

QUEUE_1_REPRODUCE:
    D repair gated on verification rather than IR validity
    asymmetric JSON parsing across D arms
    missing structured-output capability declaration
    repair transport failure scored as capability zero
    provider identity / fake evidence labeling weakness
    recognizer access to sealed/oracle metadata
    outside-basis localization inconsistency
    incomplete R5 leakage guard

QUEUE_2_RESTORE_FROZEN_INSTRUMENTS:
    A readable deterministic R5 artifact with identical semantic content
    B disclose frozen legal TaskIR intent vocabulary equally to semantic arms
    C add explicit interpretation guard: narrow structured-key baseline only
    D implement arm/representation reporting + paired semantic-formalization tax
    E implement frozen rescue diagnostics without overwriting original scores

DO_NOT:
    change seeds
    change task membership
    change scoring to improve observed results
    use live results to alter difficulty
    implement G/H/I runtime
    modify V31M4
    claim Claude's unshared local commit was reproduced

ANTI_OVERFIT:
    IF fix/system mechanism requires task IDs, seeds, generator families, expected answers,
       benchmark-specific constants, or known scored examples:
        reject as production mechanism

DONE_WHEN:
    every reproduced defect has RED/GREEN evidence
    C/D preregistered metrics are computable
    rescue evidence stays diagnostic
    no original score is overwritten
    R5 is readable and leakage-tested
    frozen C/D counts/seeds/arms unchanged
    G/H/I boundary remains closed
    relevant CI/regressions green
    GPT performs Q0-Q36 self-attack
    STATUS can become READY_FOR_KIMI

NEXT:
    Kimi reads KIMI_REVIEW_TASK.md and shared repo
    GPT reproduces/refutes Kimi findings
    only unresolved high-impact ambiguity can justify scarce Claude use
