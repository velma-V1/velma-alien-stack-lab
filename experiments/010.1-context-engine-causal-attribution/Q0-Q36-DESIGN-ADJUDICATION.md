# Experiment 010.1 — Q0–Q36 Design Adjudication

STATUS := DESIGN_ADJUDICATED_PRELIVE
LIVE_EVIDENCE := NONE
PARENT_010 := MUST_REMAIN_UNTOUCHED

This file applies the Experiment 010 tribunal to the design of `010.1-context-engine-causal-attribution`. All claims about candidate systems are design inputs until measured by 010.1. No candidate receives credit from vendor benchmarks or repository popularity.

## Q0–Q26 scientific tribunal

**Q0 — decisive questions still unasked**

1. Does a context system improve the small model because it retrieves the required evidence, or because it changes the answer-generation process?
2. When exact evidence is present, how often does the same answer model still fail?
3. Do context mechanisms contribute complementary evidence, merely duplicate each other, or contaminate one another?
4. Does ordering matter when mechanisms are composed?
5. Can the system stop using stale evidence after a source update?
6. Does a full-stack win come from parsing/ingestion or from retrieval/ranking?

These questions require separate retrieval evidence, a common answer model, an oracle-context ceiling, raw-vs-normalized ingestion, cached composition analysis, and a dynamic-update stratum.

**Q1 — success on the target workload**

Success requires an independently verified final answer from private/current corpus evidence, correct source attribution, correct abstention when the corpus does not support an answer, low stale/wrong-version selection, and acceptable local-machine cost. Aggregate answer accuracy alone is insufficient.

**Q2 — failure classes**

010.1 separates: INGESTION/PARSING, RETRIEVAL, RANKING/FUSION, CONTEXT_TRUNCATION, POST_RETRIEVAL_REASONING, ABSTENTION/CALIBRATION, FRESHNESS, UNSUPPORTED_MODALITY, and INFRASTRUCTURE. `score:null` is reserved for infrastructure/configuration failure; valid system limitations remain scored.

**Q3 — assumptions to attack**

- A repo's built-in chat answer is not comparable to another repo's retrieval output.
- More retrieved text is not better evidence.
- Larger context budgets may manufacture a false win.
- An LLM-heavy retriever may buy capability with hidden model calls.
- Raw document parsing and retrieval quality are different mechanisms.
- Graph systems are not assumed complementary merely because their internals differ.
- Vendor prompt tuning is forbidden after scored execution begins.
- Repository maturity and method value are separate production questions.

**Q4 — mechanisms already causally proven**

None for VELMA by 010.1 at design time. RAGFlow, PageIndex, GraphRAG, ColBERT, HippoRAG, and Serviette are `PENDING_LIVE_EVIDENCE` regardless of upstream claims.

**Q5 — serious solution classes**

Lexical retrieval; dense vector retrieval; lexical+dense hybrid fusion; document-aware parse/hybrid RAG; vectorless hierarchical tree reasoning; graph/community retrieval; token-level late interaction; associative graph/PPR retrieval; continuously updated/live-data RAG; and composed specialist retrieval.

**Q6 — architecture from scratch**

A stable typed `ContextEngine` boundary returns an `EvidenceBundle`. Parsers, indexes, graph/tree retrievers, rerankers, and fusion policies are replaceable behind that boundary. The answer model consumes the same bounded evidence schema regardless of source. A separate independent verifier owns correctness.

**Q7 — strongest discriminating study**

Paired hidden synthetic-private corpora; identical questions and answer model; oracle context; raw and normalized ingestion planes; retrieval metrics before generation; exact source relevance labels hidden from systems; fixed context budget; cost accounting; cached exhaustive composition search on discovery tasks; confirmatory holdout; untouched VELMA-transfer tasks.

**Q8 — base-model structural lack**

A base model cannot reliably possess private, newly changed, or deliberately synthetic facts that are absent from its weights. Context access is therefore an information/system limitation before it is a reasoning limitation.

**Q9 — independent computation**

Parsing/OCR/layout extraction, lexical/dense/late-interaction indexes, graph construction/traversal, hierarchical tree search, PPR/associative retrieval, live incremental indexing, deterministic fusion, and source/version validation.

**Q10 — typed exchange**

Every context system emits `EvidenceBundle{task_id, system_id, items[], query_metrics, trace}`. Every evidence item includes source id, rank, score when available, text, version, location metadata, and provenance. No prose-only handoff is accepted as scientific evidence.

**Q11 — complementary contribution**

Candidate contributions are hypotheses only: RAGFlow=parse/hybrid/rerank; PageIndex=hierarchical structural reasoning; GraphRAG=entity/community graph context; ColBERT=token-level late interaction; HippoRAG=associative graph/PPR; Serviette=continuous/live-data indexing. 010.1 must measure whether these contributions actually appear.

**Q12 — strongest theoretical architecture consistent with no 010.1 evidence**

A specialist context layer with a conventional hybrid baseline and optional structural/graph/late-interaction specialists, composed only when paired evidence demonstrates complementarity. No "all systems on" architecture is presumed.

**Q13 — structural ceilings**

Context systems cannot fix answer-model reasoning errors after oracle evidence is supplied; cannot answer facts absent from the corpus; may fail unsupported modalities; may create stale-index windows; and can increase contamination/cost faster than recall.

**Q14 — cheapest maximally discriminating action**

Retrieve once, cache typed rankings/evidence, and evaluate composition offline before spending additional answer-model calls. Exhaustively simulate subsets/order/fusion on discovery outputs, then run only six preregistered selected composition slots on an untouched confirmatory set.

**Q15 — evidence that capability was created**

A system-assisted arm must improve independently verified final answers on paired tasks; retrieval must contain the required evidence within the same context budget; oracle context must establish the post-retrieval ceiling; and system gains must not be credited from call-count reductions alone.

**Q16 — falsifiers**

- Oracle context does not materially beat model-only: tasks do not isolate information access.
- Advanced systems do not beat conventional hybrid retrieval: added complexity is unsupported.
- A full-stack win disappears on normalized ingestion: parsing rather than retrieval caused it.
- Composition gain disappears on confirmatory tasks: discovery synergy was overfit.
- VELMA+winner fails to beat either VELMA baseline or Qwen+winner on transfer tasks: integration does not compound.

**Q17 — direct vs proxy measures**

Direct: independently verified final answer, exact required-evidence presence, correct source/version, freshness after update. Proxies: vendor scores, semantic similarity, model confidence, component count, raw retrieval score, token count, and latency.

**Q18 — architecture-change threshold**

A mechanism is a promotion candidate only if it produces paired verified gain, survives confirmatory/transfer evidence where applicable, does not materially increase silent-wrong behavior, and lies on the local capability/cost Pareto frontier.

**Q19 — serious alternatives**

Conventional hybrid retrieval may remain optimal. A single specialist may win. A small pair may dominate an ensemble. Parsing may be the only useful RAGFlow contribution. Graph systems may be redundant. No candidate may justify its burden.

**Q20 — $1M architecture choice before evidence**

Use a stable replaceable context port plus a strong conventional hybrid baseline, and keep all advanced systems external/optional until measured. This minimizes irreversible coupling while preserving every experimental option.

**Q21 — causal accounting**

Every gain is reported as: parser delta (raw vs normalized), retrieval sufficiency delta, answer delta conditional on sufficient context, compound delta versus best constituent, freshness delta, and incremental compute/latency/memory/disk/model-call cost.

**Q22 — largest component gain**

Unknown until measured. The report ranks components by paired verified gain and retrieval-sufficiency gain, not by aggregate marketing benchmark.

**Q23 — ablation/leave-one-out**

Every selected multi-system composition receives constituent comparison; the full ensemble receives leave-one-out analysis from cached discovery evidence. A component is not necessary if removing it preserves sufficiency and verified success.

**Q24 — end-to-end trace**

Each task preserves source corpus -> parser/index identity -> retrieved evidence ids/ranks -> context truncation -> common answer prompt -> structured answer/citations -> deterministic verifier. The first stage at which required evidence disappears is recorded.

**Q25 — genuine synergy**

A synergy task requires the combined arm to succeed while every constituent fails on that same task, and the final combined evidence must contain required evidence uniquely contributed by at least two constituents. Aggregate compound gain without complementary contribution is not called synergy.

**Q26 — strongest argument against the preferred interpretation**

Advanced retrieval systems may merely spend substantially more model/index compute to approximate an oracle evidence set on a synthetic benchmark; gains may fail to transfer to VELMA's real workloads or may be dominated by a simple hybrid baseline once equal context and cost accounting are enforced.

## Q27–Q36 V31M4 production tribunal

**Q27 Production seam** — only a typed external `ContextEngine`/`EvidenceBundle` port is promotable; no candidate may own V31M4 authority or state.

**Q28 Authority preservation** — retrieved content is untrusted evidence. Models/context engines cannot certify correctness or mutate authoritative state.

**Q29 Local-machine economics** — record index wall time, query wall time, internal model calls/tokens, peak RSS/VRAM where exposed, disk index size, startup cost, idle services, and update latency. Missing metrics are `UNMEASURED`, never zero.

**Q30 Failure isolation** — a context engine failure must degrade only context acquisition. It cannot take down the VELMA runtime; fallback behavior remains explicit.

**Q31 Verification contract** — input question + corpus identity -> evidence bundle -> answer -> deterministic answer/source/version certificate. Infrastructure and capability failures are distinct.

**Q32 Replaceability** — adapters are external and version-sealed. RAGFlow/PageIndex/GraphRAG/ColBERT/HippoRAG/Serviette may be swapped without changing the V31M4-facing evidence schema.

**Q33 Engineering ROI** — report verified gain per latency, model call, memory/disk burden, and integration/maintenance score. The highest raw accuracy need not win.

**Q34 Roadmap displacement** — only measured evidence may justify replacing planned parsing, retrieval, reranking, graph, memory, or context-assembly work.

**Q35 Capability compounding** — useful retrieved evidence may feed later verified capability accumulation, but 010.1 does not claim persistent executable capability from retrieval alone.

**Q36 Competitive consequence** — Stage D tests whether the selected context mechanism helps VELMA beyond Qwen+context and VELMA baseline. The same context port can later be calibrated with frontier models without changing the context-engine claim.

## Design verdict

`VERDICT := BUILD_ISOLATED_HARNESS_NOW`

`LIVE_0101 := FORBIDDEN_UNTIL_PARENT_010_C_D_TERMINAL_RECEIPT`

The build may proceed on the isolated 010.1 branch. No live 010.1 model/context-system evidence may be accepted before an unlock receipt binds the completed parent 010 C/D evidence identity.