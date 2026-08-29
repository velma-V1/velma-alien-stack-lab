---
paths:
  - "experiments/010-computational-basis-atlas/**"
  - "alien_lab/computational_atlas*.py"
  - "tests/test_computational_atlas*.py"
  - "docs/superpowers/specs/*010*"
  - "docs/superpowers/plans/*010*"
---

# Experiment 010 path-scoped rules

WHEN touching_010_file:
    READ experiments/010-computational-basis-atlas/PREREGISTRATION-C-I-v1.md relevant section
    READ corresponding tests
    PRESERVE frozen scientific semantics

ASSERT:
    original_score != rescue_score
    model_self_verification == forbidden
    unavailable_or_infrastructure_failure => score:null
    valid_unresolved => scored evidence
    evidence_kind is explicit
    hidden oracle/capability labels do not reach non-oracle arms

CHANGE_POLICY:
    IF implementation_bug:
        prove defect
        fix minimum code
        rerun targeted + relevant regression tests

    IF proposed_change alters frozen task/seed/arm/scoring/budget/fairness:
        reject change
        report contract conflict

    IF test ceiling is demonstrably saturated:
        propose harder versioned extension
        preserve v1 unchanged

PHASE_GATE:
    C_D := current live evidence target
    E_F := frozen/built reference test infrastructure; do not reinterpret from C/D results
    G_H_I := definition-only until explicit advance after evidence review

DO_NOT:
    implement G/H/I runtime/system behavior
    add G/H/I execution tests that force implementation
    modify V31M4
    optimize benchmark after results
    weaken a hard case

REPORT := FACT + EVIDENCE + INFERENCE + UNCERTAINTY
