# Claude Code Constitution — Experiment 010

ACTIVE_PROGRAM := "Experiment 010 — Computational Basis Atlas"
PRODUCTION_DESTINATION := "velma-V1/V31m4"
LAB := "velma-V1/velma-alien-stack-lab"

## Mission

GOAL:
    discover which external computational capabilities move VERIFIED problem-solving
    out of neural inference
    determine where neural inference remains necessary
    produce causal evidence for later governed V31M4 promotion

DO_NOT_OPTIMIZE_FOR:
    prettier scores
    preferred architecture
    preferred model
    prior GPT/Claude claims
    benchmark survival

## Source of truth

READ_WHEN_REQUIRED, IN_ORDER:
    1. experiments/010-computational-basis-atlas/PREREGISTRATION-C-I-v1.md
    2. docs/superpowers/specs/2026-08-29-experiment-010-computational-basis-atlas-design.md
    3. experiments/010-computational-basis-atlas/README.md
    4. experiments/010-computational-basis-atlas/CURRENT_TASK.md

IF conflict:
    preregistration > design > README > CURRENT_TASK

CURRENT_TASK may select work.
CURRENT_TASK may NOT change scientific truth.

## Scientific invariants

TEST_IS_FROZEN := true

NEVER:
    change tasks/seeds/arms/scoring/budgets/rescue/fairness to benefit any result
    reinterpret bad evidence as success
    overwrite original score with rescue score
    let a model verify its own output
    treat model confidence as evidence
    silently repair evidence
    mutate V31M4
    promote experimental code automatically
    inspect results to redesign the same preregistered test in our favor

IF infrastructure_or_model_unavailable:
    score := null
    classify := invalid_or_non_evidence

IF valid_unresolved:
    preserve score/status
    localize bottleneck
    continue evidence accounting

IF ceiling_saturation_proven:
    preserve all prior evidence
    create NEW harder versioned extension
    NEVER weaken or replace prior test

## Current phase boundary

CURRENT_IMPLEMENTATION_BOUNDARY := "C-F test/runtime infrastructure only"
NEXT_EVIDENCE_PRIORITY := "C/D live local-model evidence"

G_H_I:
    preregistered definitions/ledgers MAY exist
    live/system implementation MUST NOT proceed until GPT+user explicitly advance after evidence review

## Context discipline

BEFORE_READING:
    read CURRENT_TASK.md
    search filenames/symbols
    select narrow dependency surface

DO_NOT:
    reread whole repository
    inspect experiments/001-009 unless CURRENT_TASK requires it
    read result-cell directories wholesale unless statistical analysis requires it
    rediscover architecture already documented

READ:
    target module
    corresponding tests
    exact preregistration section
    direct dependencies only

## Engineering procedure

PROCESS:
    SEARCH
    -> READ_MINIMUM
    -> TRACE_CONTRACT
    -> ASSUME_CURRENT_IMPLEMENTATION_MAY_BE_WRONG
    -> WRITE/VERIFY_FAILING_TEST when changing behavior
    -> MODIFY_MINIMUM_NECESSARY_CODE
    -> RUN_TARGETED_TESTS
    -> RUN_RELEVANT_REGRESSIONS
    -> VERIFY_SCIENTIFIC_CONTRACT

IF proposed_change makes test easier:
    REJECT

IF proposed_change changes preregistered semantics:
    STOP
    REPORT "SCIENTIFIC_CONTRACT_CHANGE_REQUIRED"

## Pseudocode communication

DEFAULT_COMMUNICATION := concise pseudocode + exact identifiers

USE_PROSE_ONLY_WHEN:
    ambiguity requires explanation
    scientific consequence cannot be represented precisely in pseudocode

## Reporting contract

RETURN:
    STATUS
    FILES_READ
    FILES_CHANGED
    DEFECTS_FOUND
    EVIDENCE
    TESTS_RUN
    TEST_RESULTS
    SCIENTIFIC_IMPACT
    PREREGISTRATION_IMPACT := NONE | CEILING_EXTENSION_REQUIRED | CONTRACT_CONFLICT
    UNRESOLVED
    COMMIT

DISTINGUISH_ALWAYS:
    FACT
    EVIDENCE
    INFERENCE
    UNCERTAINTY
