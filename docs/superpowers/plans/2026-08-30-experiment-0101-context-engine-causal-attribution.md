# Experiment 010.1 Context Engine Causal Attribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a credential-free mechanically verifiable Experiment 010.1 harness that generates the frozen 96-task corpus, records typed context evidence, compares standalone context mechanisms, exhaustively analyzes cached compositions, enforces a parent-010 live unlock gate, and later supports external live context engines plus VELMA without modifying either Experiment 010 or V31M4.

**Architecture:** 010.1 is a separate experiment behind a typed `ContextEngineAdapter -> EvidenceBundle -> common answer model -> independent verifier` boundary. Heavy candidate systems run outside the lab process and communicate through a version-sealed JSONL subprocess protocol; GitHub CI uses deterministic fixture adapters only. The harness separates raw ingestion from normalized retrieval, caches evidence for offline composition analysis, and allows live execution only when a cryptographically bound parent-010 completion receipt is supplied.

**Tech Stack:** Python 3.11 standard library; Pillow 11.3.0 for deterministic image fixtures; existing `alien_lab.computational_atlas_types.stable_hash`; `unittest`; GitHub Actions.

**Spec:** `experiments/010.1-context-engine-causal-attribution/PREREGISTRATION-v1.md`

## Global Constraints

- Do not modify the active Experiment 010 branch, runner, tasks, seeds, scoring, manifests, output directories, or evidence.
- Do not import or mutate V31M4 source code; VELMA is reachable only through a future external typed adapter.
- No live 010.1 candidate/model evidence before a valid parent-010 unlock receipt reports exactly `terminal_cells = 4416` and `0101_live_unlocked = true`.
- `ANSWER_CONTEXT_UTF8_BYTES = 16384`; answer-model maximum output is 512 tokens; one answer-model call per end-to-end cell.
- Corpus seed is `20261001`; 96 tasks; 8 strata x 12; fixed 48 DISCOVERY / 24 CONFIRMATORY / 24 VELMA_TRANSFER split.
- Stage A = 792 end-to-end cells; Stage B = 648 retrieval-only observations; Stage C1 = 144 confirmatory end-to-end cells; Stage D = 120 untouched transfer cells.
- Valid capability limitations remain scored; only infrastructure/configuration failures receive `score:null`.
- Candidate built-in final answers are not primary evidence. Every candidate must expose a typed `EvidenceBundle` separately.
- All selection rules use DISCOVERY evidence only where preregistered; VELMA_TRANSFER outcomes are never visible before Stage D.
- Every run seals corpus, ledger, adapter, model/provider, prompt, composition-policy, and output identities before evidence is accepted.

---

### Task 1: Freeze control state and test the scientific contract

**Files:**
- Modify: `experiments/010.1-context-engine-causal-attribution/DRAFT-DESIGN.md`
- Create: `tests/test_context_engine_0101_contract.py`
- Create: `.github/workflows/0101-smoke.yml`

**Interfaces:**
- Consumes: preregistration constants and existing `stable_hash` utility.
- Produces: executable contract tests that later modules must satisfy.

- [ ] **Step 1: Mark the prior draft as superseded**

Replace only its status/gate preamble with:

```text
STATUS := SUPERSEDED_BY_PREREGISTRATION_V1
IMPLEMENTATION := ALLOWED_ON_ISOLATED_0101_BRANCH
LIVE_EXECUTION := FORBIDDEN_UNTIL_PARENT_010_C_D_TERMINAL_RECEIPT
SOURCE_OF_TRUTH := PREREGISTRATION-v1.md
```

Do not alter Experiment 010.

- [ ] **Step 2: Write failing contract tests**

`tests/test_context_engine_0101_contract.py` must import the wished-for API and assert:

```python
from alien_lab.context_engine_types import ANSWER_CONTEXT_UTF8_BYTES, STANDALONE_ARMS
from alien_lab.context_engine_corpus import build_context_corpus
from alien_lab.context_engine_experiment import build_stage_a_ledger, build_stage_b_ledger, build_stage_c1_ledger, build_stage_d_ledger

assert ANSWER_CONTEXT_UTF8_BYTES == 16384
assert len(STANDALONE_ARMS) == 11
corpus = build_context_corpus(seed=20261001)
assert len(corpus.tasks) == 96
assert sum(t.split == "DISCOVERY" for t in corpus.tasks) == 48
assert sum(t.split == "CONFIRMATORY" for t in corpus.tasks) == 24
assert sum(t.split == "VELMA_TRANSFER" for t in corpus.tasks) == 24
assert len(build_stage_a_ledger(corpus)) == 792
assert len(build_stage_b_ledger(corpus)) == 648
assert len(build_stage_c1_ledger(corpus, topology_ids=("T1","T2","T3","T4","T5","T6"))) == 144
assert len(build_stage_d_ledger(corpus, standalone_id="RAGFLOW_FULL", composition_id="T1")) == 120
```

Also assert the six pinned advanced system ids and eight strata are exact.

- [ ] **Step 3: Add isolated CI workflow**

`.github/workflows/0101-smoke.yml` triggers only on `experiment/010.1-context-engine-causal-attribution` paths and runs Python compile, new 010.1 tests, prior 010 regression tests, and a credential-free deterministic smoke command. It must never install or start RAGFlow/PageIndex/GraphRAG/ColBERT/HippoRAG/Serviette.

- [ ] **Step 4: Run GitHub Actions and verify RED**

Expected: import failures such as `ModuleNotFoundError: alien_lab.context_engine_types` because production modules do not exist yet. Record workflow run id/head SHA as TDD evidence.

- [ ] **Step 5: Commit**

Commit tests/workflow/control-doc changes before production implementation.

---

### Task 2: Typed contracts, corpus generator, and non-leaking ledgers

**Files:**
- Create: `alien_lab/context_engine_types.py`
- Create: `alien_lab/context_engine_corpus.py`
- Create: `alien_lab/context_engine_experiment.py`
- Extend test: `tests/test_context_engine_0101_contract.py`

**Interfaces:**
- Produces:
  - `EvidenceItem(source_id: str, text: str, rank: int, score: float|None, version: str|None, location: str|None, provenance: dict)`
  - `EvidenceBundle(task_id: str, system_id: str, corpus_identity: str, plane: str, items: tuple[EvidenceItem,...], trace: dict, query_metrics: dict)`
  - `ContextTask(task_id, stratum, split, question, expected_answer, required_source_ids, raw_documents, normalized_documents, answerable, freshness_revision)`
  - `ContextCorpus(seed, tasks, corpus_hash)`
  - `ContextCell(cell_id, order, stage, task_id, arm, plane, topology_id=None)`
  - `build_context_corpus(seed=20261001) -> ContextCorpus`
  - ledger builders named in Task 1.

- [ ] **Step 1: Add failing tests for deterministic corpus identity**

Assert two builds with seed 20261001 have identical hashes/task ids, a different seed changes the hash, every stratum has 12 tasks, and generated exposed source ids/filenames do not contain split names, stratum names, `required`, `answer`, arm ids, or relevance labels.

- [ ] **Step 2: Add failing tests for raw/normalized pairing and hidden relevance**

Every task must contain both planes; required source ids must reference actual documents internally but the exposed document text/metadata cannot encode relevance labels.

- [ ] **Step 3: Implement minimal frozen dataclasses/constants**

Define exact arm/system/stratum/split tuples and deterministic `.to_dict()` methods. Use `stable_hash` for corpus/cell identity.

- [ ] **Step 4: Implement deterministic 96-task generator**

Generate synthetic-private organization/entity identifiers from seeded RNG. Build answerable/no-answer, stale-version, multi-hop, table, long-layout, scanned/image-manifest, relational, and dynamic-update task structures without relying on model knowledge. Keep raw artifact descriptors deterministic; binary rendering is deferred to adapter materialization.

- [ ] **Step 5: Implement ledgers and verify counts**

Stage A excludes VELMA_TRANSFER and has 72 x 11. Stage B has 72 x 9 normalized retrieval observations. Stage C1 accepts exactly six sealed topology ids and uses only CONFIRMATORY tasks. Stage D uses only VELMA_TRANSFER tasks and five frozen arms.

- [ ] **Step 6: Run tests and commit GREEN for Task 2**

All contract/corpus/ledger tests pass while Stage-C selector/adapters remain unimplemented.

---

### Task 3: Evidence scoring, context budgeting, answer verification, and failure localization

**Files:**
- Create: `alien_lab/context_engine_scoring.py`
- Create: `tests/test_context_engine_0101_scoring.py`

**Interfaces:**
- Consumes: `ContextTask`, `EvidenceBundle`.
- Produces:
  - `budget_evidence(bundle, max_utf8_bytes=16384) -> EvidenceBundle`
  - `score_retrieval(task, bundle) -> RetrievalScore`
  - `verify_answer(task, answer_payload, delivered_bundle) -> AnswerScore`
  - `localize_failure(task, retrieval_score, answer_score) -> str`
  - `paired_exact_sign_test(wins: int, losses: int) -> float`

- [ ] **Step 1: Write failing budget tests**

Test deterministic truncation never exceeds 16,384 UTF-8 bytes, preserves ranking order, and never splits a UTF-8 code point.

- [ ] **Step 2: Write failing retrieval metric tests**

Use hand-built task/bundles to assert exact required-evidence recall, relevant precision, first relevant rank/MRR, wrong version, stale selection, context sufficiency, and no-answer contamination.

- [ ] **Step 3: Write failing answer-verifier tests**

Assert exact/normalized synthetic answers, citation correctness, correct abstention, unnecessary abstention, silent-wrong detection, and post-retrieval reasoning failure when context was sufficient but the answer was wrong.

- [ ] **Step 4: Write failing failure-localization tests**

Map missing raw parse evidence -> INGESTION where normalized retrieval succeeds; insufficient normalized evidence -> RETRIEVAL; sufficient pre-budget but insufficient delivered -> CONTEXT_TRUNCATION; sufficient delivered but wrong answer -> POST_RETRIEVAL_REASONING; stale V1 after V2 -> FRESHNESS.

- [ ] **Step 5: Implement minimal scoring functions**

Use deterministic exact-source/source-version accounting and standard-library math. No LLM judge is allowed in primary scoring.

- [ ] **Step 6: Run tests and commit**

---

### Task 4: Conventional baselines and typed external adapter protocol

**Files:**
- Create: `alien_lab/context_engine_adapters.py`
- Create: `tests/test_context_engine_0101_adapters.py`

**Interfaces:**
- Produces:
  - `ContextEngineAdapter.identity() -> dict`
  - `ContextEngineAdapter.index(corpus_dir, corpus_identity, plane) -> dict`
  - `ContextEngineAdapter.retrieve(task, plane) -> EvidenceBundle`
  - `ContextEngineAdapter.update(task, revision) -> dict`
  - `BM25Adapter`
  - `DenseFixtureAdapter` for CI only
  - `HybridRRFAdapter`
  - `JsonlSubprocessAdapter(command, sealed_identity)` for live external systems
  - `FixtureContextAdapter` labeled `FAKE_MECHANICS_ONLY`.

JSONL request/response protocol:

```json
{"op":"identity"}
{"op":"index","corpus_dir":"...","corpus_identity":"...","plane":"raw"}
{"op":"retrieve","task_id":"...","question":"...","plane":"raw","max_candidates":32}
{"op":"update","task_id":"...","revision":"V2"}
```

Every response carries `ok`, `adapter_identity`, and for retrieval an `EvidenceBundle` payload. The harness never sends `expected_answer` or `required_source_ids`.

- [ ] **Step 1: Write failing leakage/protocol tests**

Capture subprocess requests and assert no sealed answer/relevance/source-label fields are serialized. Assert adapter identity mismatch fails closed.

- [ ] **Step 2: Write failing BM25 tests**

A rare decisive term must rank its source above distractors; source-id ties are deterministic.

- [ ] **Step 3: Write failing hybrid RRF tests**

Assert k=60 and deterministic rank-only fusion; dense scores cannot override rank ordering directly.

- [ ] **Step 4: Implement protocol and baselines**

BM25 is pure Python. Dense live retrieval remains external/runtime sealed; CI fixture vectors are deterministic and explicitly non-live.

- [ ] **Step 5: Run tests and commit**

---

### Task 5: Offline composition search and six-slot preregistered selector

**Files:**
- Create: `alien_lab/context_engine_fusion.py`
- Create: `tests/test_context_engine_0101_fusion.py`

**Interfaces:**
- Produces:
  - `rrf_fuse(bundles, k=60) -> EvidenceBundle`
  - `consensus_fuse(bundles, k=60) -> EvidenceBundle`
  - `cascade_filter_then_rank(first, second, candidate_cap) -> EvidenceBundle`
  - `enumerate_discovery_topologies(system_ids) -> tuple[Topology,...]`
  - `select_six_topologies(discovery_scores, cost_metrics) -> tuple[Topology,...]`
  - `classify_compounding(confirmatory_results) -> CompoundingVerdict`.

- [ ] **Step 1: Write failing topology-count tests**

For six advanced systems assert exactly 63 RRF subsets, 63 consensus subsets, and 30 ordered cascades. Reverse cascades must be distinct.

- [ ] **Step 2: Write failing no-label fusion tests**

Fusion takes only rankings/evidence bundles. Tests inspect call signatures/data to ensure relevance labels/expected answers are absent.

- [ ] **Step 3: Write failing selector tests**

Synthetic discovery results must deterministically choose six **unique** slots in the exact preregistered order and never read confirmatory/transfer rows.

- [ ] **Step 4: Write failing synergy tests**

A combination is genuine synergy only if every constituent answer fails and at least two constituents uniquely contribute required evidence to the successful combined bundle. A simple ensemble accuracy gain without complementary contribution must not be labeled synergy.

- [ ] **Step 5: Implement deterministic fusion/selection/classification**

Use lexical topology ids as final tie-break. Implement exact paired sign/binomial statistic with `math.comb`.

- [ ] **Step 6: Run tests and commit**

---

### Task 6: Manifest sealing, hashed evidence, parent unlock, resume safety

**Files:**
- Create: `alien_lab/context_engine_run.py`
- Create: `tests/test_context_engine_0101_run_integrity.py`

**Interfaces:**
- Produces:
  - `RunIdentity`
  - `validate_parent_unlock(receipt_path) -> dict`
  - `prepare_run(output_dir, identity, ledger) -> manifest`
  - `write_evidence_envelope(path, payload) -> envelope`
  - `read_evidence_envelope(path, expected_identity_hash, expected_cell) -> envelope`.

- [ ] **Step 1: Write failing parent-gate tests**

Reject missing receipt, wrong parent experiment, terminal count other than 4416, false unlock flag, missing summary hash, and malformed identity hash. Accept a deterministic fixture receipt only in fixture mode; fixture mode must never produce a live verdict.

- [ ] **Step 2: Write failing run-identity tests**

Changing adapter pin/config, corpus hash, model id/digest, embedding identity, prompt hash, context budget, or ledger must reject reuse of an existing output directory.

- [ ] **Step 3: Write failing tamper/resume tests**

Tampering any saved payload must fail its envelope hash. Exact matching completed evidence is reused; invalid infrastructure evidence may be rerun only under an explicit `rerun_invalid` flag.

- [ ] **Step 4: Implement minimal integrity layer**

Atomic JSON writes and `stable_hash`; no external crypto dependency.

- [ ] **Step 5: Run tests and commit**

---

### Task 7: Deterministic fixture runner and scientific self-attack

**Files:**
- Extend: `alien_lab/context_engine_experiment.py`
- Create: `tests/test_context_engine_0101_self_attack.py`
- Create: `experiments/010.1-context-engine-causal-attribution/config.json`

**Interfaces:**
- Produces CLI:

```bash
python -m alien_lab.context_engine_experiment --profile fixture --output-dir <dir>
```

Live CLI exists but remains hard-gated:

```bash
python -m alien_lab.context_engine_experiment --profile live --config <json> --parent-unlock <json> --output-dir <dir>
```

- [ ] **Step 1: Write failing fixture-run tests**

Fixture run must deterministically generate 96 tasks, all frozen ledgers/topology counts, at least one synthetic success/failure/no-answer/freshness case, hashed evidence, and conclusion `NON_LIVE_FIXTURE_RUN`.

- [ ] **Step 2: Write failing self-attack tests**

Assert:
- transfer tasks cannot enter A/B/C;
- discovery selector cannot accept confirmatory/transfer observations;
- candidate adapter request cannot contain sealed labels;
- answer-context bytes never exceed 16384;
- candidate built-in answer cannot bypass common answerer;
- fixture adapters cannot produce `LIVE_MODEL_EVIDENCE`;
- live profile refuses without parent unlock;
- Stage C uses cached evidence rather than invoking context adapters;
- Stage D adapter is external and no `V31m4` package import exists.

- [ ] **Step 3: Implement fixture runner and CLI**

Fixture mode uses deterministic fake context/answer adapters only; it validates mechanics/scoring and never claims capability.

- [ ] **Step 4: Run all 010.1 and prior 010 tests locally if an executable environment is available; otherwise rely on GitHub Actions for executable proof**

- [ ] **Step 5: Commit and push exact head**

---

### Task 8: GitHub GREEN gate and final pre-live closure

**Files:**
- Create: `experiments/010.1-context-engine-causal-attribution/CURRENT_TASK.md`
- Update only if needed by test-discovered defect: 010.1 files on this isolated branch.

**Interfaces:**
- Produces: exact-head CI evidence and closed live gate.

- [ ] **Step 1: Run/fetch GitHub Actions on exact head**

Required successful steps:
- compile Python sources;
- all 010.1 contract/scoring/adapter/fusion/run-integrity/self-attack tests;
- relevant Experiment 010 regression tests;
- deterministic 010.1 fixture run;
- fixture evidence artifact upload.

- [ ] **Step 2: If CI fails, use systematic debugging and TDD**

For every newly discovered defect: add/reproduce failing test first, then minimal fix, then rerun. Do not weaken preregistration/tests to turn red into green.

- [ ] **Step 3: Record exact RED/GREEN evidence**

`CURRENT_TASK.md` records initial RED workflow run/head, final GREEN workflow run/head, test count, fixture hashes/counts, and upstream adapter pins.

- [ ] **Step 4: Close live gate**

Final state must be:

```text
IMPLEMENTATION := MECHANICALLY_READY
GITHUB_GATE := GREEN
LIVE_0101 := LOCKED_WAITING_FOR_PARENT_010_C_D_TERMINAL_RECEIPT
PARENT_010 := UNTOUCHED
V31M4 := UNTOUCHED
```

No live RAGFlow/PageIndex/GraphRAG/ColBERT/HippoRAG/Serviette/Qwen/VELMA 010.1 evidence is collected in this build phase.

- [ ] **Step 5: Final verification**

Run/fetch exact-head CI again if the control-document commit changes a workflow-triggering path. Do not claim completion until the exact current head is green.
