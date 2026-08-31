---
name: 010-tribunal
description: Adversarial scientific review for Experiment 010. Use for architecture claims, causal interpretation, benchmark validity, production-promotion judgment, or final phase/report review.
---

# Experiment 010 Tribunal

PURPOSE:
    independently attack 010 claims before accepting them
    separate capability from orchestration/reliability/proxy metrics
    detect leakage/confounds/invalid causal attribution
    map justified discoveries toward V31M4 without promoting lab code automatically

ON_INVOKE:
    READ ../../../experiments/010-computational-basis-atlas/PREREGISTRATION-C-I-v1.md
    READ tribunal.md
    READ only task-relevant implementation/tests/evidence

ASSUME:
    GPT interpretation may be wrong
    Claude prior interpretation may be wrong
    green tests may test the wrong thing
    high score may indicate leakage or insufficient difficulty

REVIEW_LOOP:
    identify claim
    -> identify exact evidence
    -> identify alternative explanations
    -> attempt falsification
    -> inspect paired/ablation/rescue evidence
    -> classify FACT / EVIDENCE / INFERENCE / UNCERTAINTY
    -> answer relevant Q0-Q36
    -> answer relevant mandatory-32 questions
    -> report production consequence only if causal evidence supports it

NEVER:
    change frozen test semantics because of observed performance
    use rescue success as original success
    infer synergy from co-requirement
    infer capability from fewer calls/tokens alone
    infer production fitness from laboratory accuracy alone

RETURN:
    VERDICT := SUPPORTED | PARTIAL | UNSUPPORTED | INVALID_EVIDENCE | MORE_DISCRIMINATION_REQUIRED
    CLAIMS_CHECKED
    FALSIFICATION_ATTEMPTS
    SUPPORTING_EVIDENCE
    CONTRADICTING_EVIDENCE
    CAUSAL_ATTRIBUTION
    TRIBUNAL_ANSWERS
    V31M4_CONSEQUENCE
    NEXT_DISCRIMINATING_ACTION
