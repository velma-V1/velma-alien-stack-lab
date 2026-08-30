# Experiment 010.1 — Context Engine Causal Attribution

STATUS := DRAFT_ISOLATED
EXECUTION := FORBIDDEN_UNTIL_010_C_D_COMPLETE
PARENT_EVIDENCE := Experiment 010 only after its current live C/D run completes
BASE_COMMIT := a6c15dbffedf4441849d33b76d9ae66b12e33ae0

## Isolation contract

010.1 is a separate scientific extension and MUST NOT modify, import into, reconfigure, rerun, or otherwise interfere with the active frozen Experiment 010 C/D baseline.

Until 010 C/D is complete:

- no 010.1 runtime implementation;
- no changes to Experiment 010 code, tasks, seeds, arms, scoring, manifests, output directories, or CI;
- no shared output/evidence directories;
- no 010.1 branch merge into the active 010 branch;
- no conclusions from partial 010 results may be used to tune 010.1 tasks in favor of any system.

This document is design-only and is not yet preregistration.

---

## Primary question

Does a context/retrieval system create verified capability for the same small local model, which mechanism causes the gain, and do different mechanisms compound constructively or interfere when composed in different topologies/orders?

The experiment measures SYSTEM capability. It must never attribute a system-assisted gain to increased base-model capability.

## Fixed model-side contract

All non-oracle arms use the same model identity, model digest, context limit, generation contract, answer prompt contract, and independent verifier. No arm may receive a larger answer-context token budget merely because its retrieval system naturally returns more text.

Initial target model for design purposes:

- model: qwen3.5:9b-q8_0
- context limit: 25,600

Exact runtime identity is sealed at preregistration/run time.

---

## Candidate context mechanisms

### R — RAGFlow
Mechanism under test: document understanding/parsing, chunk construction, hybrid retrieval, reranking, and context/citation assembly.

### T — PageIndex
Mechanism under test: vectorless hierarchical document structure plus reasoning/tree-search retrieval; no ordinary vector-similarity dependence in the primary arm.

### G — GraphRAG
Mechanism under test: extracted entities/relationships/community structure and graph-conditioned retrieval.

### L — ColBERT / RAGatouille
Mechanism under test: token-level late-interaction retrieval rather than one-vector-per-chunk similarity.

### A — Adaptive/decomposed retrieval (Pathway/Serviette method family)
Mechanism under test: query decomposition, adaptive context expansion, retrieval retries, and configurable hybrid/reranked retrieval rather than a single fixed top-k pass.

Repositories/versions must be pinned before preregistration. Package branding is secondary; the scientific unit is the frozen mechanism.

---

## Corpus design

Use hidden synthetic-but-realistic corpora whose decisive facts cannot be answered reliably from model pretraining alone.

Initial design: 72 tasks across six equal strata:

1. ordinary text/document retrieval;
2. tables/spreadsheets/structured records;
3. layout-sensitive PDF/footnote/reference problems;
4. scanned/image-document extraction;
5. cross-document multi-hop reasoning;
6. contradiction/version/no-answer traps.

Every stratum should include distractors, near-duplicates, irrelevant lexical matches, stale revisions, and source-quality conflicts where applicable.

All arms receive paired immutable task identity.

---

# 010.1A — Standalone mechanism attribution

Baseline arms:

1. MODEL_ONLY — question only, no external evidence retrieval.
2. BASIC_RAG — frozen simple parser, fixed chunking, frozen embedding retrieval, fixed top-k.
3. RAGFLOW_FULL.
4. PAGEINDEX_FULL.
5. GRAPHRAG_FULL.
6. COLBERT_FULL.
7. ADAPTIVE_RETRIEVAL_FULL.
8. ORACLE_CONTEXT — exact necessary evidence supplied within the same answer-context budget ceiling where feasible.

Initial nominal size: 72 tasks × 8 arms = 576 cells.

The purpose is not merely to crown a repo. It establishes the independent verified gain, failure profile, evidence quality, latency, and context cost of each materially different retrieval strategy.

### Primary metrics

- independently verified final answer;
- required-evidence recall;
- evidence precision / irrelevant-evidence contamination;
- wrong-source or wrong-version selection;
- contradiction handling;
- no-answer correctness;
- citation/source attribution correctness where supported;
- answer-context tokens delivered to model;
- retrieval/index latency separated from generation latency;
- model calls;
- retrieval/model compute and memory where measurable.

### Key causal quantities

TOTAL_SYSTEM_GAIN(system) := verified_success(system) - verified_success(MODEL_ONLY)

GAIN_OVER_BASIC_RAG(system) := verified_success(system) - verified_success(BASIC_RAG)

REMAINING_CONTEXT_DEFICIT(system) := verified_success(ORACLE_CONTEXT) - verified_success(system)

MODEL_OR_POST_RETRIEVAL_DEFICIT := 1 - verified_success(ORACLE_CONTEXT)

No rescued/oracle score substitutes for an original system score.

---

# 010.1B — Mechanism decomposition

Where supported without changing the scientific meaning of the package, decompose gains into narrower interventions, for example:

- parsing/chunking;
- candidate retrieval;
- reranking;
- graph expansion;
- tree reasoning;
- query decomposition;
- adaptive context expansion;
- context fusion/assembly.

A mechanism receives credit only through paired intervention evidence. A repo-level win does not prove every subsystem contributes.

---

# 010.1C — Compounding, redundancy, antagonism, and order

Only after 010.1A establishes standalone behavior, test composition using the SAME frozen task corpus and scoring contract.

The goal is to discover whether mechanisms are complementary, redundant, antagonistic, or cost-negative.

## Composition topologies

### PARALLEL_SPECIALISTS

query -> multiple independent retrievers -> frozen evidence fusion -> same model

Candidate specialists: T + G + L, optionally R where parsing quality is a prerequisite rather than a competing retriever.

### CASCADE

upstream broad/structural retrieval -> downstream precision reranking/filtering -> model

Candidate examples:

- R parsing/chunks -> L late-interaction precision retrieval;
- T structural narrowing -> L reranking;
- G relational expansion -> L precision filtering.

### ADAPTIVE_ROUTER

A frozen routing policy selects one or more retrieval specialists based on query/task observables without access to expected answers.

Candidate specialists: T, G, L, R-derived retrieval.

### RETRIEVE_ALL_THEN_FUSE

All enabled systems retrieve independently; a frozen deterministic or separately tested fusion stage selects evidence within the same context budget.

This arm detects whether broad ensemble recall helps or simply increases contamination.

## Ordering tests

For any pair where order is semantically meaningful, test both directions using paired tasks:

A -> B
B -> A

Examples:

- structural/tree narrowing -> late-interaction rerank versus late-interaction retrieval -> structural filtering;
- graph expansion -> precision rerank versus lexical/vector retrieval -> graph expansion;
- adaptive decomposition before specialist retrieval versus specialist retrieval before adaptive retry/fusion.

Do not assume order symmetry.

## Composition classifications

For a combined system C with constituents S1..Sn:

COMPOUND_GAIN := verified_success(C) - max(verified_success(S1)..verified_success(Sn))

Classify with paired evidence:

- SYNERGISTIC: combined arm materially beats every constituent and the gain survives paired uncertainty/error analysis;
- ADDITIVE: positive but modest verified gain;
- REDUNDANT: no material verified gain;
- ANTAGONISTIC: verified performance decreases;
- COST_NEGATIVE: accuracy improves but capability-per-cost/latency/context/complexity is worse than the selected production threshold.

True synergy requires a causal handoff or complementary evidence contribution, not merely more components running.

---

## Fairness controls

- same base model and verifier across comparable arms;
- same maximum answer-context token budget;
- same underlying document corpus and task identity;
- same answer-generation prompt wherever the retrieval interface permits;
- index-time LLM work is recorded separately and never treated as free;
- retrieval-time model calls are counted separately from answer-generation calls;
- no system may see expected answers, sealed relevant-document IDs, or oracle evidence labels;
- no post-hoc task dropping;
- unsupported modalities or system failures are classified explicitly rather than silently removed;
- package-specific default settings must be frozen before scored execution, with no per-task tuning.

---

## Production decision objective

Do not promote a repository merely because it wins aggregate accuracy.

Select the smallest system or composition that maximizes:

VERIFIED_CAPABILITY_GAIN /
(model_dependence + silent-wrong risk + context cost + compute + latency + memory + integration complexity + maintenance burden)

Possible outcomes include:

- adopt one standalone retrieval engine behind a V31M4 retrieval/context port;
- adopt only a causally proven subsystem such as parser, reranker, tree index, graph expansion, late-interaction retrieval, or adaptive router;
- compose complementary mechanisms behind one typed V31M4 context interface;
- reject all candidates if gains do not justify system burden.

---

## Gate before implementation

010.1 implementation may begin only after:

1. the currently running Experiment 010 live C/D baseline reaches a terminal state and its evidence is preserved;
2. GPT/user explicitly reopen the 010.1 branch for design finalization;
3. candidate repositories/versions and hardware feasibility are re-verified;
4. this draft is converted into a frozen preregistration before the first scored 010.1 live cell.

Until then: DESIGN_ONLY / NO_EXECUTION.
