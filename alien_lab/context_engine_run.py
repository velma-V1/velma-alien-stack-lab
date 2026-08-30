from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .computational_atlas_types import stable_hash
from .context_engine_types import ContextCell, EXPERIMENT


_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(frozen=True)
class RunIdentity:
    experiment: str
    profile: str
    system_version: str
    corpus_hash: str
    ledger_hash: str
    answer_model_identity: dict[str, Any]
    embedding_identity: dict[str, Any]
    adapter_identities: dict[str, Any]
    answer_prompt_hash: str
    composition_policy_hash: str
    answer_context_utf8_bytes: int
    live: bool

    def __post_init__(self) -> None:
        if self.experiment != EXPERIMENT:
            raise ValueError("EXPERIMENT_IDENTITY_MISMATCH")
        if self.profile == "fixture" and self.live:
            raise ValueError("FIXTURE_CANNOT_BE_LIVE")
        if self.answer_context_utf8_bytes <= 0:
            raise ValueError("ANSWER_CONTEXT_BUDGET_INVALID")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def identity_hash(self) -> str:
        return stable_hash(self.to_dict())


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def validate_parent_unlock(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise ValueError("PARENT_UNLOCK_RECEIPT_REQUIRED")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("parent_experiment") != "010-computational-basis-atlas":
        raise ValueError("PARENT_EXPERIMENT_MISMATCH")
    if payload.get("terminal_cells") != 4416:
        raise ValueError("PARENT_TERMINAL_COUNT_MISMATCH")
    if payload.get("0101_live_unlocked") is not True:
        raise ValueError("PARENT_UNLOCK_FALSE")
    if not _HEX64.fullmatch(str(payload.get("parent_run_identity_hash") or "")):
        raise ValueError("PARENT_RUN_IDENTITY_HASH_INVALID")
    if not _HEX64.fullmatch(str(payload.get("parent_live_summary_sha256") or "")):
        raise ValueError("PARENT_SUMMARY_HASH_INVALID")
    if not str(payload.get("parent_terminal_state") or "").strip():
        raise ValueError("PARENT_TERMINAL_STATE_REQUIRED")
    return payload


def prepare_run(output_dir: Path, identity: RunIdentity, cells: Iterable[ContextCell]) -> dict[str, Any]:
    output_dir = Path(output_dir)
    cell_list = list(cells)
    ledger = [cell.to_dict() for cell in cell_list]
    actual_ledger_hash = stable_hash(ledger)
    identity_hash = identity.identity_hash()
    manifest = {
        "experiment": identity.experiment,
        "profile": identity.profile,
        "live": identity.live,
        "expected_cells": len(cell_list),
        "run_identity": identity.to_dict(),
        "run_identity_hash": identity_hash,
        "actual_ledger_hash": actual_ledger_hash,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "run-manifest.json"
    ledger_path = output_dir / "run-ledger.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("run_identity_hash") != identity_hash or existing.get("actual_ledger_hash") != actual_ledger_hash:
            raise ValueError("RUN_IDENTITY_MISMATCH")
        if not ledger_path.exists():
            raise ValueError("RUN_LEDGER_MISSING")
        existing_ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        if stable_hash(existing_ledger) != actual_ledger_hash:
            raise ValueError("RUN_LEDGER_TAMPERED")
        return existing
    if ledger_path.exists():
        raise ValueError("RUN_IDENTITY_MISMATCH")
    _atomic_json(ledger_path, ledger)
    _atomic_json(manifest_path, manifest)
    return manifest


def write_evidence_envelope(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    envelope = {"payload": payload, "sha256": stable_hash(payload)}
    _atomic_json(Path(path), envelope)
    return envelope


def read_evidence_envelope(path: Path, *, expected_identity_hash: str, expected_cell: ContextCell) -> dict[str, Any]:
    envelope = json.loads(Path(path).read_text(encoding="utf-8"))
    payload = envelope.get("payload") or {}
    if stable_hash(payload) != envelope.get("sha256"):
        raise ValueError("EVIDENCE_HASH_MISMATCH")
    if payload.get("run_identity_hash") != expected_identity_hash:
        raise ValueError("EVIDENCE_IDENTITY_MISMATCH")
    if payload.get("cell") != expected_cell.to_dict():
        raise ValueError("EVIDENCE_CELL_MISMATCH")
    return envelope
