from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .computational_atlas_types import stable_hash
from .context_engine_corpus import build_context_corpus
from .context_engine_fusion import enumerate_discovery_topologies, select_six_topologies
from .context_engine_run import validate_parent_unlock
from .context_engine_types import (
    ADVANCED_SYSTEMS,
    ANSWER_CONTEXT_UTF8_BYTES,
    CONVENTIONAL_RETRIEVAL_ARMS,
    ContextCell,
    ContextCorpus,
    RETRIEVAL_ARMS,
    STANDALONE_ARMS,
    make_cell_id,
)


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _reorder(cells: list[ContextCell]) -> list[ContextCell]:
    return [ContextCell(**{**cell.to_dict(), "order": order}) for order, cell in enumerate(cells)]


def build_stage_a_ledger(corpus: ContextCorpus) -> list[ContextCell]:
    cells: list[ContextCell] = []
    for task in corpus.tasks:
        if task.split == "VELMA_TRANSFER":
            continue
        for arm in STANDALONE_ARMS:
            if arm in CONVENTIONAL_RETRIEVAL_ARMS:
                plane = "normalized"
            elif arm == "MODEL_ONLY":
                plane = "none"
            elif arm == "ORACLE_CONTEXT":
                plane = "oracle"
            else:
                plane = "raw"
            cells.append(
                ContextCell(
                    cell_id=make_cell_id("A", task.task_id, arm, plane),
                    order=0,
                    stage="A",
                    task_id=task.task_id,
                    arm=arm,
                    plane=plane,
                )
            )
    return _reorder(cells)


def build_stage_b_ledger(corpus: ContextCorpus) -> list[ContextCell]:
    cells: list[ContextCell] = []
    for task in corpus.tasks:
        if task.split == "VELMA_TRANSFER":
            continue
        for arm in RETRIEVAL_ARMS:
            cells.append(
                ContextCell(
                    cell_id=make_cell_id("B", task.task_id, arm, "normalized"),
                    order=0,
                    stage="B",
                    task_id=task.task_id,
                    arm=arm,
                    plane="normalized",
                )
            )
    return _reorder(cells)


def build_stage_c1_ledger(corpus: ContextCorpus, *, topology_ids: tuple[str, ...]) -> list[ContextCell]:
    if len(topology_ids) != 6 or len(set(topology_ids)) != 6:
        raise ValueError("STAGE_C_REQUIRES_SIX_UNIQUE_TOPOLOGIES")
    cells: list[ContextCell] = []
    for task in corpus.tasks:
        if task.split != "CONFIRMATORY":
            continue
        for topology_id in topology_ids:
            cells.append(
                ContextCell(
                    cell_id=make_cell_id("C1", task.task_id, topology_id),
                    order=0,
                    stage="C1",
                    task_id=task.task_id,
                    arm="COMPOSITION",
                    plane="normalized",
                    topology_id=topology_id,
                )
            )
    return _reorder(cells)


def build_stage_d_ledger(corpus: ContextCorpus, *, standalone_id: str, composition_id: str) -> list[ContextCell]:
    if standalone_id not in RETRIEVAL_ARMS:
        raise ValueError("STAGE_D_STANDALONE_UNKNOWN")
    arms = (
        "QWEN_NO_CONTEXT",
        f"QWEN_CONTEXT:{standalone_id}",
        "VELMA_BASELINE",
        f"VELMA_CONTEXT:{standalone_id}",
        f"VELMA_COMPOSITION:{composition_id}",
    )
    cells: list[ContextCell] = []
    for task in corpus.tasks:
        if task.split != "VELMA_TRANSFER":
            continue
        for arm in arms:
            cells.append(
                ContextCell(
                    cell_id=make_cell_id("D", task.task_id, arm),
                    order=0,
                    stage="D",
                    task_id=task.task_id,
                    arm=arm,
                    plane="raw" if "NO_CONTEXT" not in arm else "none",
                    topology_id=composition_id if arm.startswith("VELMA_COMPOSITION:") else None,
                )
            )
    return _reorder(cells)


def validate_live_execution_gate(*, parent_unlock_path: Path | None) -> dict[str, Any]:
    if parent_unlock_path is None:
        raise ValueError("LIVE_0101_LOCKED_WAITING_FOR_PARENT_010")
    return validate_parent_unlock(Path(parent_unlock_path))


def _fixture_discovery_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, topology in enumerate(enumerate_discovery_topologies(ADVANCED_SYSTEMS)):
        rows.append(
            {
                "split": "DISCOVERY",
                "topology_id": topology.topology_id,
                "kind": topology.kind,
                "context_sufficiency_rate": 0.55 + ((index * 7) % 31) / 100.0,
                "required_recall": 0.58 + ((index * 5) % 29) / 100.0,
                "relevant_precision": 0.50 + ((index * 3) % 23) / 100.0,
                "reciprocal_rank": 0.45 + ((index * 11) % 37) / 100.0,
                "context_bytes": 6000 + ((index * 97) % 7000),
                "query_latency_ms": 5.0 + ((index * 13) % 200),
                "measured_cost": 1.0 + ((index * 17) % 19),
                "complementarity_wins": (index * 7) % 13,
            }
        )
    return rows


def run_fixture_experiment(output_dir: Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    corpus = build_context_corpus(seed=20261001)
    stage_a = build_stage_a_ledger(corpus)
    stage_b = build_stage_b_ledger(corpus)
    topologies = enumerate_discovery_topologies(ADVANCED_SYSTEMS)
    selected = select_six_topologies(_fixture_discovery_rows())
    selected_ids = tuple(item.topology_id for item in selected)
    stage_c = build_stage_c1_ledger(corpus, topology_ids=selected_ids)
    stage_d = build_stage_d_ledger(corpus, standalone_id="RAGFLOW_FULL", composition_id=selected_ids[0])

    manifest = {
        "experiment": "010.1-context-engine-causal-attribution",
        "profile": "fixture",
        "live": False,
        "evidence_kind": "FAKE_MECHANICS_ONLY",
        "corpus_hash": corpus.corpus_hash,
        "answer_context_utf8_bytes": ANSWER_CONTEXT_UTF8_BYTES,
        "selected_topology_ids": list(selected_ids),
        "ledger_hashes": {
            "A": stable_hash([cell.to_dict() for cell in stage_a]),
            "B": stable_hash([cell.to_dict() for cell in stage_b]),
            "C1": stable_hash([cell.to_dict() for cell in stage_c]),
            "D": stable_hash([cell.to_dict() for cell in stage_d]),
        },
    }
    fingerprint = stable_hash(manifest)
    summary = {
        "experiment": manifest["experiment"],
        "conclusion": "NON_LIVE_FIXTURE_RUN",
        "live_model_evidence": False,
        "evidence_kind": "FAKE_MECHANICS_ONLY",
        "corpus_hash": corpus.corpus_hash,
        "fixture_fingerprint": fingerprint,
        "stage_a_cells": len(stage_a),
        "stage_b_observations": len(stage_b),
        "stage_c1_cells": len(stage_c),
        "stage_d_cells": len(stage_d),
        "discovery_topology_count": len(topologies),
        "selected_topology_ids": list(selected_ids),
    }
    _atomic_json(output_dir / "fixture-manifest.json", manifest)
    _atomic_json(output_dir / "fixture-summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Experiment 010.1 context-engine causal-attribution harness")
    parser.add_argument("--profile", choices=("fixture", "live"), required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--config")
    parser.add_argument("--parent-unlock")
    args = parser.parse_args(argv)

    try:
        if args.profile == "fixture":
            summary = run_fixture_experiment(Path(args.output_dir))
            print(json.dumps(summary, indent=2, sort_keys=True))
            return 0
        validate_live_execution_gate(parent_unlock_path=Path(args.parent_unlock) if args.parent_unlock else None)
        if not args.config:
            raise ValueError("LIVE_CONFIG_REQUIRED")
        raise ValueError("LIVE_EXTERNAL_ADAPTER_EXECUTION_NOT_YET_ENABLED")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"CONTEXT_0101_HARNESS_ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
