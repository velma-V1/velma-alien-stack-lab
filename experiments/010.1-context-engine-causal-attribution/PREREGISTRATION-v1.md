# Experiment 010.1 — Context Engine Causal Attribution — Preregistration v1

Date frozen: 2026-08-30
Experiment: `010.1-context-engine-causal-attribution`
Parent experiment: `010-computational-basis-atlas`
Production destination for later justified promotions: `velma-V1/V31m4`

## Governing rule

010.1 is a separate experiment. It does not modify or reinterpret Experiment 010. The 010.1 harness may be designed, implemented, and mechanically validated while Experiment 010 C/D is still running, but **no live 010.1 context-system/model evidence is accepted until a parent-completion unlock receipt binds the terminal Experiment 010 C/D evidence identity**.

After this preregistration, evidence may change the system under test but may not change 010.1 task generation, splits, scoring, answer-context budget, arm membership, composition-selection algorithm, or holdout membership in favor of any candidate.

## Scientific question

For the same local answer model, which context/retrieval mechanisms create verified capability on private/current document tasks; which gains come from parsing versus retrieval; which mechanisms are complementary, redundant, antagonistic, or cost-negative; which ordering/fusion arrangements compound best; and does the selected context architecture still add value when placed behind VELMA?

A system-assisted gain is a **system gain**, never a claim that the base model itself became more capable.

---

# Fixed model and answer contract

Primary local answer model target:

- model family target: `qwen3.5:9b-q8_0`
- context limit target: `25,600`
- exact runtime model id/digest/provider version are sealed before first live 010.1 cell
- answer-generation model identity must be identical across comparable arms
- maximum answer-generation calls per cell: `1`
- maximum answer output tokens: `512`
- no per-arm or per-task answer prompt tuning

Answer output schema:

```json
{
  "answer": "string or null",
  "citations": ["document-id"],
  "abstain": false
}
```

The same prompt instructs the model to answer only from supplied evidence and to abstain when the evidence is insufficient. `MODEL_ONLY` receives the same question with an empty evidence section. `ORACLE_CONTEXT` receives only sealed required evidence.

## Equal answer-context budget

All non-model-only evidence arms are capped at:

`ANSWER_CONTEXT_UTF8_BYTES := 16384`

Evidence truncation/selection is deterministic. Actual prompt tokens reported by the provider are recorded but do not alter the byte budget after execution begins.

No arm may win by supplying a larger answer context.

---

# Candidate systems and frozen upstream identities

The scientific unit is the method plus pinned implementation identity. Upstream benchmark claims are not 010.1 evidence.

1. `RAGFLOW_FULL`
   - mechanism hypothesis: document parsing/chunking + hybrid retrieval + reranking/context assembly
   - upstream: `infiniflow/ragflow`
   - pin: `v0.27.1`

2. `PAGEINDEX_TREE`
   - mechanism hypothesis: vectorless hierarchical document tree + reasoning-based retrieval
   - upstream: `VectifyAI/PageIndex`
   - pin: `9fee239b174fcc205fec28df105e519ac7171522`

3. `MICROSOFT_GRAPHRAG`
   - mechanism hypothesis: extracted entity/relationship/community graph context
   - upstream: `microsoft/graphrag`
   - pin: `v3.1.2`
   - production note: upstream currently describes the project as largely maintenance-mode; scientific value and production fitness are scored separately

4. `COLBERT_LATE_INTERACTION`
   - mechanism hypothesis: token-level late interaction rather than one-vector-per-chunk similarity
   - upstream: `stanford-futuredata/ColBERT`
   - pin: `cc4f3dc91c0b45d2d08c251d9d95178285c65f1c`
   - retrieval checkpoint identity must be sealed at live-run time

5. `HIPPORAG_PPR`
   - mechanism hypothesis: associative knowledge graph + Personalized PageRank multi-hop retrieval
   - upstream: `OSU-NLP-Group/HippoRAG`
   - pin: `2f52a86dd04e4633703bd2fb3bb6a37683ac3cfb`

6. `SERVIETTE_LIVE_RAG`
   - mechanism hypothesis: continuously updated/live-data RAG with multimodal ingestion and a decoupled retrieval service
   - upstream: `pathwaycom/serviette`
   - pin: `800c874621c22dcdb9c29cf20bcd5205551800eb`
   - this arm is **not** classified as an adaptive-query-decomposition method

## Conventional baselines

7. `BM25_RAG` — frozen lexical retrieval over normalized fixed chunks.
8. `DENSE_VECTOR_RAG` — frozen dense-vector retrieval over the same chunks and a sealed local embedding identity.
9. `HYBRID_RRF_RAG` — deterministic reciprocal-rank fusion of BM25 and dense rankings.

## Ceilings/baselines without a context engine

10. `MODEL_ONLY`
11. `ORACLE_CONTEXT`

---

# Corpus

Seed: `20261001`

Total tasks: `96`

Eight strata, exactly 12 tasks each:

1. `SINGLE_HOP_TEXT`
2. `TABLE_STRUCTURED`
3. `LONG_LAYOUT_PDF`
4. `SCANNED_MULTIMODAL`
5. `CROSS_DOC_MULTI_HOP`
6. `RELATIONAL_GLOBAL`
7. `CONTRADICTION_VERSION_NO_ANSWER`
8. `DYNAMIC_UPDATE_FRESHNESS`

Every task uses synthetic-private identifiers/facts intended not to be recoverable from pretrained model knowledge. Every answerable task has sealed required evidence ids/spans. No-answer tasks contain no supporting evidence. Distractors include near-duplicates, high lexical similarity, stale revisions, irrelevant facts, and source conflicts where appropriate.

## Immutable split

Within each stratum, tasks are deterministically assigned:

- first 6 generated tasks -> `DISCOVERY` (48 total)
- next 3 -> `CONFIRMATORY` (24 total)
- final 3 -> `VELMA_TRANSFER` (24 total)

`VELMA_TRANSFER` tasks are not executed in standalone or composition phases before Stage D.

## Raw and normalized planes

Each task has:

- `raw` corpus artifacts preserving document modality/layout;
- `normalized` canonical UTF-8 document text generated by the experiment oracle parser.

The raw plane measures full-stack ingestion + retrieval. The normalized plane removes parser/modality differences and isolates downstream retrieval/ranking behavior.

Sealed answers/relevance labels are never supplied to candidate systems.

---

# Failure/status taxonomy

Valid scored limitations:

- `VALID_SUCCESS`
- `VALID_UNRESOLVED_INGESTION`
- `VALID_UNRESOLVED_RETRIEVAL`
- `VALID_UNRESOLVED_CONTEXT_TRUNCATION`
- `VALID_UNRESOLVED_POST_RETRIEVAL_REASONING`
- `VALID_UNRESOLVED_ABSTENTION`
- `VALID_UNRESOLVED_FRESHNESS`
- `VALID_UNRESOLVED_UNSUPPORTED_MODALITY`

Infrastructure/configuration failures use `score:null`, e.g. provider/service unavailable, corrupted index, version mismatch, or failed run identity validation.

A valid scored failure is never overwritten by rescue/diagnostic evidence.

---

# Typed evidence contract

All context engines must be adapted to emit the same external schema:

```text
EvidenceBundle
  task_id
  system_id
  corpus_identity
  plane := raw | normalized
  items[]
    source_id
    text
    rank
    score?           # system-native, diagnostic only
    version?
    location?
    provenance{}
  trace{}
  query_metrics{}
```

Candidate built-in answer/chat output is not accepted as the primary answer. The shared Qwen answer stage consumes only the typed evidence bundle.

If a candidate cannot expose evidence separately from its own final answerer, the primary arm is non-comparable and fails configuration validation rather than receiving an unfair private answer-model advantage.

---

# Metrics

## Direct capability metrics

- independently verified final answer success
- context sufficiency after the common 16,384-byte budget
- required-evidence recall
- relevant-evidence precision
- first-relevant rank / reciprocal rank
- wrong-source selection
- wrong-version/stale-source selection
- no-answer correctness
- citation correctness
- silent-wrong rate
- correct abstention / unnecessary abstention
- dynamic-update correctness before and after revision

## Mechanism diagnostics

- raw-vs-normalized retrieval delta
- parse/ingestion loss
- retrieval loss
- context truncation loss
- post-retrieval reasoning loss conditional on context sufficiency
- unique relevant contribution by system
- evidence overlap/redundancy between systems

## Cost/production diagnostics

Record where measurable:

- index wall time
- query wall time
- answer wall time
- internal retrieval/index model calls
- internal tokens
- answer-model calls/tokens
- transport retries
- peak RSS / VRAM
- persisted index size
- startup/idle service burden
- dynamic update convergence time

Missing cost telemetry is `UNMEASURED`, never zero.

---

# Stage A — standalone full-system attribution

Tasks: `DISCOVERY + CONFIRMATORY = 72`

Arms per task: all 11 arms listed above.

Nominal Stage-A end-to-end cells:

`72 × 11 = 792`

Candidate systems operate on the **raw** corpus plane. Conventional baselines use the experiment's frozen normalized chunk representation so they remain a strong conventional retrieval reference rather than an OCR/parser test.

Primary score: independently verified final answer.

For every context arm, retrieval evidence is persisted before answer generation so retrieval and answer errors remain separable.

---

# Stage B — normalized retrieval/mechanism decomposition

Tasks: same 72 Stage-A tasks.

Retrieval arms:

- `BM25_RAG`
- `DENSE_VECTOR_RAG`
- `HYBRID_RRF_RAG`
- `RAGFLOW_FULL`
- `PAGEINDEX_TREE`
- `MICROSOFT_GRAPHRAG`
- `COLBERT_LATE_INTERACTION`
- `HIPPORAG_PPR`
- `SERVIETTE_LIVE_RAG`

All operate on the **normalized** plane.

Nominal Stage-B retrieval-only observations:

`72 × 9 = 648`

No shared answer-model call is required for Stage B. Its purpose is parser/retrieval causal decomposition and cached composition analysis.

For a candidate system S:

`PARSER_OR_NATIVE_INGESTION_DELTA(S) := normalized_retrieval_metric(S) - raw_retrieval_metric(S)`

Positive values indicate a raw-ingestion/parser deficit; negative values indicate useful native structure retained by the system.

---

# Stage C — compounding, ordering, redundancy, antagonism

## C0 discovery simulation

Input: cached typed retrieval outputs from **DISCOVERY only** (48 tasks) for the six advanced candidate systems:

`RAGFLOW, PAGEINDEX, GRAPHRAG, COLBERT, HIPPORAG, SERVIETTE`

No new retrieval or answer-model calls are needed for C0.

The simulator enumerates:

- every non-empty advanced-system subset under reciprocal-rank fusion: `2^6 - 1 = 63` subsets;
- every non-empty subset under consensus-first fusion: `63` subsets;
- every ordered pair under filter-then-rank cascade: `6 × 5 = 30` ordered cascades;
- leave-one-out evidence for the six-system full ensemble.

All fusion policies are deterministic and use no sealed relevance label at inference time. Relevance labels are used only after a bundle is produced to score it.

## C1 deterministic six-slot selector

Exactly six unique composition slots are selected using DISCOVERY evidence only:

1. `BEST_RRF`
2. `BEST_CONSENSUS`
3. `BEST_CASCADE`
4. `CHEAP_PARETO`
5. `MAX_COMPLEMENTARITY_PAIR`
6. `FULL_ENSEMBLE_RRF`

Tie-break order is deterministic: higher context-sufficiency rate, then evidence recall, then precision, then reciprocal rank, then lower context bytes, then lower measured query latency, then lexical topology id.

`CHEAP_PARETO` is the lowest measured-cost unique topology within 1 percentage point of the best discovery context-sufficiency rate and within 2 percentage points of its evidence recall; if none qualify, the next-best non-dominated topology is used.

`MAX_COMPLEMENTARITY_PAIR` maximizes the number of discovery tasks where the fused pair becomes context-sufficient while neither constituent alone was sufficient.

If two named selector slots resolve to the same topology, the later slot takes the next-best topology within its category; if none exists, the globally next-best unique topology is used.

The selected topology identities are sealed before the first C1 cell.

## C1 confirmatory execution

Tasks: `CONFIRMATORY = 24`

Cells: `24 × 6 = 144`

Each selected composition's final evidence is passed to the common answer model and deterministic verifier.

### Synergy accounting

For a composition C with constituents S1..Sn on the same confirmatory task:

- per-task genuine synergy requires C success, every constituent failure, and required evidence uniquely contributed by at least two constituents to the final evidence bundle;
- aggregate `COMPOUND_GAIN := success_rate(C) - max constituent success rate` on paired confirmatory tasks;
- report discordant wins/losses and an exact paired sign/binomial statistic;
- co-running multiple retrievers without complementary evidence is never labeled synergy.

Classification outputs: `SYNERGISTIC`, `ADDITIVE`, `REDUNDANT`, `ANTAGONISTIC`, `COST_NEGATIVE`, or `INCONCLUSIVE`.

---

# Stage D — untouched VELMA transfer

Tasks: `VELMA_TRANSFER = 24`

The Stage-D task contents are not used by Stages A/B/C or by the composition selector.

A frozen selector chooses, using only Stage-A DISCOVERY/CONFIRMATORY and Stage-C CONFIRMATORY evidence:

- `BEST_STANDALONE_CONTEXT`
- `BEST_CONFIRMED_COMPOSITION`

Stage-D arms:

1. `QWEN_NO_CONTEXT`
2. `QWEN_BEST_STANDALONE_CONTEXT`
3. `VELMA_BASELINE`
4. `VELMA_BEST_STANDALONE_CONTEXT`
5. `VELMA_BEST_CONFIRMED_COMPOSITION`

Nominal Stage-D cells:

`24 × 5 = 120`

VELMA is accessed only through an external typed adapter. 010.1 does not import or mutate V31M4 source code.

Stage D asks whether context capability transfers into VELMA and whether VELMA compounds with it rather than merely inheriting the context engine's standalone gain.

---

# Dynamic-update/freshness contract

For `DYNAMIC_UPDATE_FRESHNESS` tasks, each system is queried at state V1, then a corpus document is deterministically revised to V2 and the system's documented update path is invoked. The same question is queried again.

Measure:

- V1 correctness;
- V2 correctness;
- stale V1 evidence after update;
- convergence/update latency;
- whether a rebuild was required;
- update compute/model-call cost.

A system that requires a full rebuild is not invalid; rebuild cost is part of the mechanism/production result.

---

# Conventional baseline contract

`BM25_RAG`, `DENSE_VECTOR_RAG`, and `HYBRID_RRF_RAG` share:

- identical normalized document chunks;
- identical chunk boundaries;
- identical context-byte budget;
- no answer labels/relevance labels;
- no per-task tuning.

The dense embedding model/checkpoint/digest is runtime-configured but sealed before the first Stage-A cell and remains unchanged for the complete run.

Hybrid RRF uses frozen rank-only fusion with `k=60`.

---

# Composition fusion contract

## Reciprocal-rank fusion

For source ranking r from each constituent:

`RRF_SCORE(item) = sum(1 / (60 + rank_system(item)))`

Items are ordered by descending RRF score, then source id.

## Consensus-first fusion

Order items first by number of constituent systems retrieving the source, then by RRF score, then source id.

## Filter-then-rank cascade A -> B

A's top document set under the common pre-context candidate cap is the allowed set. B's cached ranking is filtered to that set and retains B ordering. If B contains no item from A's set, the bundle is empty. Reverse order is evaluated independently.

No relevance labels enter fusion.

---

# Run identity and evidence integrity

Before first live cell, seal:

- experiment/preregistration hash
- corpus seed and generated corpus hash
- task ledger hash
- split membership
- answer model id/digest/provider/version/context
- embedding model identity
- every candidate system pin/version/config hash
- external adapter identities
- context budget
- answer prompt hash
- composition policy hash
- output directory identity

Evidence is written per cell/observation under atomic hashed envelopes. Existing evidence can be reused only when run identity and cell identity match exactly.

---

# Parent-010 unlock gate

Live 010.1 execution requires an external JSON unlock receipt with:

- `parent_experiment = "010-computational-basis-atlas"`
- terminal parent C/D run identity hash
- SHA-256 of preserved parent live summary
- `terminal_cells = 4416`
- parent terminal conclusion/state
- explicit `0101_live_unlocked = true`

The receipt unlocks execution only. Parent 010 performance values do not alter 010.1 tasks, scoring, splits, arms, or selection rules.

Without a valid receipt, live candidate/model adapters must refuse to execute.

Credential-free deterministic fake-adapter CI is allowed before this gate and must be labeled non-live evidence.

---

# Anti-leakage / anti-overfit rules

- exposed documents/questions never contain expected answers outside the actual task facts;
- filenames/source ids do not encode relevance, arm, system, answer, stratum, or split;
- candidate adapters never receive required-evidence ids or sealed expected answers;
- the common answer model never receives retrieval scores/relevance labels unless they are normal system-native metadata explicitly included in the frozen evidence schema;
- composition selection cannot read CONFIRMATORY or VELMA_TRANSFER labels/outcomes;
- VELMA selection cannot read VELMA_TRANSFER labels/outcomes;
- no task may be removed after observing poor performance;
- valid scored evidence is immutable;
- infrastructure fixes may rerun only invalid `score:null` evidence with unchanged task/scoring contract.

---

# Production decision rule

Do not promote a repository because it wins aggregate accuracy.

For every candidate and confirmed composition report:

`VERIFIED_CAPABILITY_GAIN / (model_dependence + silent_wrong_risk + context_cost + compute + latency + memory + disk + integration_complexity + maintenance_burden)`

Promotion states remain:

`EXPERIMENTAL -> REPLICATED -> PROMOTION_CANDIDATE -> V31M4 integration branch`

Stage-D transfer is required before a context architecture can become a V31M4 promotion candidate.

## Frozen interpretation discipline

FACT := observable implementation/evidence property
EVIDENCE := measured experiment result
INFERENCE := conclusion supported by evidence
UNCERTAINTY := unresolved alternative explanation

If evidence cannot distinguish alternatives:

`VERDICT := MORE_DISCRIMINATION_REQUIRED`
