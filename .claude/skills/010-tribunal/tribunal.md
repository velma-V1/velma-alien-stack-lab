# Experiment 010 Scientific Tribunal Reference

Use this file only for scientific/architectural review. Do not load it for routine edits.

## Q0-Q26 — stable scientific tribunal

Q0  := What decisive question are we still failing to ask?
Q1  := What does success actually require on the target workload?
Q2  := Are failures primarily reasoning, information, representation, planning, execution, verification, memory, or architecture?
Q3  := Which assumptions must be attacked before trusting the preferred design?
Q4  := Which mechanisms are already causally proven, and at what effect size?
Q5  := Which serious solution classes could plausibly close the required capability gap?
Q6  := What architecture would we design if the current architecture did not exist?
Q7  := What would the strongest AI research team do next to discriminate architectures?
Q8  := What does the base model fundamentally lack that orchestration cannot create?
Q9  := What independent computation can supply those missing capabilities?
Q10 := How do components exchange typed information so cooperation creates capability rather than prose handoffs?
Q11 := What complementary capability does each component add that the model alone does not reliably possess?
Q12 := What is the strongest theoretical architecture consistent with current evidence?
Q13 := What structural ceilings remain even under that architecture?
Q14 := What is the cheapest discriminating experiment that maximally changes the next decision?
Q15 := What evidence proves capability was created rather than merely calls/tokens/errors being rearranged?
Q16 := What evidence would show our interpretation is wrong?
Q17 := Which measurements are proxies and which measure the requested phenomenon directly?
Q18 := What result would justify an architecture change?
Q19 := What serious alternative architectures remain?
Q20 := If $1M depended on choosing one architecture now, which would we choose and why?
Q21 := What is the causal accounting for every claimed gain?
Q22 := Which component contributes the largest verified gain?
Q23 := What do leave-one-out / ablation results say about necessity?
Q24 := Can we trace a hard task end-to-end and identify the exact point capability appears or disappears?
Q25 := Is there a task requiring genuine synergy where the combination beats every constituent and causal handoff is demonstrated?
Q26 := What is the strongest argument against our preferred interpretation/architecture?

RULE_Q14:
    never means "kill VELMA"
    means discriminate next direction

## Q27-Q36 — V31M4 production/promotion tribunal

Q27 := Production seam — can the capability enter an existing V31M4 boundary without corrupting the frozen core?
Q28 := Authority preservation — do models/tools remain non-authoritative and production state runtime-owned?
Q29 := Local-machine economics — CPU/RAM/VRAM/storage/startup/latency/sustained-load/concurrency/idle overhead?
Q30 := Failure isolation — what fraction of VELMA fails when this capability fails?
Q31 := Verification contract — input/result/evidence/certificate/independent check/failure conditions?
Q32 := Replaceability — can implementation change behind a stable contract?
Q33 := Engineering ROI — verified capability gain per implementation and maintenance burden?
Q34 := Roadmap displacement — what planned V31M4 work becomes simpler, merged, replaced, or unnecessary?
Q35 := Capability compounding — can verified work become reusable computation without retraining?
Q36 := Competitive consequence — small-model prosthetic only, or architecture that also improves frontier models?

## Mandatory 32 Experiment 010 questions

### A — computational topology

1  := What is the oracle-IR ceiling?
2  := What does each engine uniquely contribute?
3  := Which engines are redundant?
4  := Which engines substitute for one another?
5  := Which combinations demonstrate genuine causal synergy?
6  := What is the minimum sufficient computational basis?
7  := What problem clusters remain outside that basis?
8  := What new fundamental operators do those residual clusters imply?

### B — semantic/model interface

9  := What is the semantic-formalization tax?
10 := How does that tax change across representation levels?
11 := Which semantic errors dominate?
12 := How often is decomposition itself wrong?
13 := What is routing regret versus oracle routing?
14 := Does capability/tool overload make routing worse?
15 := When is a neural model call actually necessary?
16 := Can the system recognize uncertainty/unsupported tasks instead of forcing a bad formalization?

### C — system intelligence

17 := Does typed multi-engine composition create capability unavailable to individual engines?
18 := Where does composition break?
19 := How does capability degrade with horizon length?
20 := How much does independent verification improve trustworthy success?
21 := Where is verification incomplete or impossible?
22 := How many silent wrong results survive each architecture?
23 := Does verified capability accumulation reduce neural reasoning on repeated work?
24 := Does accumulated capability survive parameter variation, representation shift, transfer, and drift?

### D — competitive and production consequence

25 := How does VELMA + local compare with local-model-only?
26 := How does architecture value change as model strength rises?
27 := What capability-family gaps remain versus frontier systems?
28 := What is the success/model-call/cost/latency Pareto frontier?
29 := Where does each useful capability belong in V31M4?
30 := What does each capability cost and risk in production?
31 := Which planned V31M4 components can be simplified, merged, replaced, or eliminated?
32 := Given all evidence, what are the Pareto-optimal next directions?

## Adversarial review procedure

FOR each_claim:
    locate exact evidence
    identify whether evidence is:
        MEASURED_EXPERIMENT
        CONTROLLED_MECHANISM_AUDIT
        PENDING_LIVE_EVIDENCE
        INVALID_NON_EVIDENCE

    CHECK leakage:
        answer leakage
        capability-label leakage
        solver-type leakage
        seed/task selection after results
        oracle information in non-oracle arm
        unequal tool access
        unequal budgets
        post-hoc scoring changes

    CHECK causal validity:
        paired world identity
        ablation/leave-one-out
        rescue does not overwrite original
        synergy requires typed causal handoff
        verifier independent of producer
        model-call reduction is not treated as capability

    CHECK test immutability:
        IF result is bad:
            test remains unchanged
        IF result saturates ceiling:
            only harder versioned extension permitted

    RETURN conservative interpretation

## Output discipline

FACT := directly observable repo/evidence property
EVIDENCE := measured result supporting/refuting claim
INFERENCE := conclusion drawn from evidence
UNCERTAINTY := unresolved alternative explanation / missing measurement

IF evidence cannot distinguish alternatives:
    VERDICT := MORE_DISCRIMINATION_REQUIRED
