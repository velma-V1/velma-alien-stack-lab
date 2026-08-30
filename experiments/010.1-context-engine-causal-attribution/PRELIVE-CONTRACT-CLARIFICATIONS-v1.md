# Experiment 010.1 — Pre-Live Contract Clarifications v1

Date frozen: 2026-08-30
LIVE_EVIDENCE_AT_FREEZE := NONE
Parent 010 C/D state at freeze: still running externally; no parent result is used below.

This document resolves implementation ambiguities in `PREREGISTRATION-v1.md` before any live 010.1 evidence exists. It does not change task generation, splits, arms, answer-context budget, candidate set, topology selector, or promotion rules.

## C1 — Shared haystack, not task-local retrieval

Context engines must retrieve against a shared corpus, never the four documents stored on the individual task object alone.

Pre-transfer index corpus:

- DISCOVERY + CONFIRMATORY documents only;
- 72 tasks × 4 unique documents = **288 documents**;
- VELMA_TRANSFER documents are not materialized, indexed, or exposed to Stages A/B/C.

After the Stage-C topology selector and best-standalone selector are sealed, Stage D expands/rebuilds the corpus to:

- all 96 tasks × 4 unique documents = **384 documents**.

Thus transfer query contents and transfer documents are both untouched by pre-transfer selection.

## C2 — Actual raw artifact modalities

The raw corpus materializer emits real artifact types:

- normal text -> `.txt`;
- table -> `.csv`;
- scanned/multimodal -> rendered `.png` without a separate answer/relevance sidecar;
- long-layout PDF -> deterministic rendered `.pdf`.

Normalized plane emits canonical UTF-8 `.txt` documents.

A non-scientific materialization manifest may expose source id, file path, modality, and version. It may not expose expected answer, relevance, required-source labels, split, stratum, or system/arm labels.

## C3 — Freshness uses paired diagnostic cells

The preregistered base cell remains the V1 query and keeps its original score.

For `DYNAMIC_UPDATE_FRESHNESS` tasks, each applicable base arm also receives a separate `FRESHNESS_V2` diagnostic cell after the deterministic V1→V2 source revision and documented adapter update/rebuild path.

- each V1 or V2 answer cell uses at most one common answer-model call;
- the V2 diagnostic never overwrites the V1 score;
- pair-level freshness success requires both V1 and V2 independently verified success;
- stale V1 evidence in the V2 diagnostic is reported directly;
- update/rebuild latency and internal cost are reported separately.

Freshness diagnostics are additional to the nominal Stage-A/C1/D base-cell counts and are never used to rescale those base counts.

## C4 — Stage-B freshness observations

Stage B likewise preserves its base normalized V1 retrieval observation and adds a separate V2 retrieval diagnostic for dynamic-update tasks. Composition selection uses only the frozen base DISCOVERY observations; V2 freshness diagnostics are reported separately and cannot choose the six composition slots.

## C5 — Candidate internal model calls are system cost

Some context mechanisms, especially tree/graph methods, may legitimately use internal LLM calls as part of retrieval/indexing. They are allowed only when part of the pinned candidate's documented method/configuration and are recorded as `internal_model_calls/tokens/cost` where measurable.

They do not replace the common final Qwen answer stage and are never credited as base-model capability.

## C6 — Source mapping

A candidate may retrieve chunks/nodes rather than whole documents. Its bridge must map every returned item to an original experiment `source_id`. Candidate-native chunk/node ids and scores belong in provenance. Unmapped evidence is configuration-invalid because citation/source/version scoring would otherwise be incomparable.

## C7 — External-system boundary

Third-party systems and VELMA run outside the lab process through sealed adapter commands/services. Their dependency trees are not imported into `alien_lab`.

Context adapter operations are:

- `identity`
- `index`
- `retrieve`
- `update`

VELMA answer adapter operations are:

- `identity`
- `answer`

Every request excludes sealed expected answers and relevance labels.

## C8 — Live readiness meaning

`MECHANICALLY_READY` means the frozen corpus, ledgers, scoring, materialization, protocol, stage orchestration, resume/integrity rules, and credential-free fixture execution are executable and GitHub-green.

It does **not** mean all third-party dependencies are installed on the user's machine. Live 010.1 additionally requires:

1. parent-010 unlock receipt;
2. pinned candidate services/bridges configured and identity-valid;
3. sealed answer model and dense embedding identity;
4. live preflight success before the first scored cell.

No missing third-party installation is converted into a capability zero; it is configuration/infrastructure `score:null` until the live environment satisfies the frozen arm contract.
