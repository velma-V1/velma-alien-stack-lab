from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

from .computational_atlas_live_ledger import build_phase_c_ledger, build_phase_d_ledger
from .computational_atlas_live_runner import run_phase_c_cell, run_phase_d_cell
from .computational_atlas_live_types import LiveCell, RunIdentity
from .computational_atlas_providers import ModelProvider, OllamaProvider, seal_run_identity
from .computational_atlas_semantics import DIRECT_SYSTEM_PROMPT, SEMANTIC_SYSTEM_PROMPT
from .computational_atlas_surfaces import task_ir_json_schema
from .computational_atlas_types import stable_hash


EXPERIMENT = "010-computational-basis-atlas"
LIVE_PROFILE = "live-cd-v1"
_SUPPORTED_LIVE_PHASES = ("C", "D")


def supported_live_phases() -> tuple[str, ...]:
    """Return the current explicit live execution gate.

    G/H/I remain preregistered definitions only. E/F test/runtime infrastructure
    exists, but the current live evidence gate intentionally executes C/D only.
    """
    return _SUPPORTED_LIVE_PHASES


def _reorder(cells: Iterable[LiveCell]) -> list[LiveCell]:
    reordered: list[LiveCell] = []
    for order, cell in enumerate(cells):
        payload = cell.to_dict()
        payload["order"] = order
        reordered.append(LiveCell(**payload))
    return reordered


def build_cd_ledger(phases: tuple[str, ...] = ("C", "D")) -> list[LiveCell]:
    normalized = tuple(str(phase).upper() for phase in phases)
    if not normalized or any(phase not in _SUPPORTED_LIVE_PHASES for phase in normalized):
        raise ValueError(f"LIVE_PHASE_NOT_ENABLED:{normalized}")
    cells: list[LiveCell] = []
    for phase in normalized:
        cells.extend(build_phase_c_ledger() if phase == "C" else build_phase_d_ledger())
    return _reorder(cells)


def live_prompt_contract_hash() -> str:
    return stable_hash({
        "profile": LIVE_PROFILE,
        "direct_system_prompt": DIRECT_SYSTEM_PROMPT,
        "semantic_system_prompt": SEMANTIC_SYSTEM_PROMPT,
        "task_ir_schema": task_ir_json_schema(),
        "surface_contract": "experiment-010-live-surfaces-v1",
        "max_output_tokens": 2048,
        "enabled_phases": list(_SUPPORTED_LIVE_PHASES),
    })


def default_generation_contract(*, context_limit: int | None = None) -> dict[str, Any]:
    return {
        "max_output_tokens": 2048,
        "sampling": "provider_default_frozen_per_complete_run",
        "transport_retries": 2,
        "context_limit": context_limit,
        "task_specific_tuning": False,
    }


def make_run_identity(
    *,
    system_version: str,
    model_id: str,
    endpoint: str,
    provider_kind: str = "ollama",
    model_digest: str | None = None,
    provider_version: str | None = None,
    context_limit: int | None = None,
) -> RunIdentity:
    if not system_version.strip():
        raise ValueError("SYSTEM_VERSION_REQUIRED")
    if not model_id.strip():
        raise ValueError("MODEL_ID_REQUIRED")
    return RunIdentity(
        experiment=EXPERIMENT,
        profile=LIVE_PROFILE,
        system_version=system_version,
        provider_kind=provider_kind,
        model_id=model_id,
        endpoint=endpoint.rstrip("/"),
        generation_contract=default_generation_contract(context_limit=context_limit),
        prompt_contract_hash=live_prompt_contract_hash(),
        model_digest=model_digest,
        provider_version=provider_version,
    )


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _ledger_payload(cells: list[LiveCell]) -> list[dict[str, Any]]:
    return [cell.to_dict() for cell in cells]


def prepare_live_run(output_dir: Path, identity: RunIdentity, cells: list[LiveCell]) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger = _ledger_payload(cells)
    ledger_hash = stable_hash(ledger)
    identity_hash = seal_run_identity(identity)
    manifest = {
        "experiment": EXPERIMENT,
        "profile": identity.profile,
        "enabled_live_phases": sorted({cell.phase for cell in cells}),
        "expected_cells": len(cells),
        "ledger_hash": ledger_hash,
        "run_identity": identity.to_dict(),
        "run_identity_hash": identity_hash,
    }
    manifest_path = output_dir / "live-manifest.json"
    ledger_path = output_dir / "live-ledger.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("run_identity_hash") != identity_hash or existing.get("ledger_hash") != ledger_hash:
            raise ValueError("LIVE_RUN_IDENTITY_MISMATCH")
        if int(existing.get("expected_cells", -1)) != len(cells):
            raise ValueError("LIVE_RUN_IDENTITY_MISMATCH")
        if not ledger_path.exists():
            raise ValueError("LIVE_LEDGER_MISSING")
        existing_ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        if stable_hash(existing_ledger) != ledger_hash:
            raise ValueError("LIVE_LEDGER_HASH_MISMATCH")
        return existing
    if ledger_path.exists() or (output_dir / "cells").exists():
        raise ValueError("LIVE_RUN_IDENTITY_MISMATCH")
    _atomic_json(ledger_path, ledger)
    _atomic_json(manifest_path, manifest)
    return manifest


def _dispatch(cell: LiveCell, provider: ModelProvider | None) -> dict[str, Any]:
    if cell.phase == "C":
        return run_phase_c_cell(cell, provider)
    if cell.phase == "D":
        return run_phase_d_cell(cell, provider)
    raise ValueError(f"LIVE_PHASE_NOT_ENABLED:{cell.phase}")


def _load_envelope(path: Path, *, identity_hash: str, cell: LiveCell) -> dict[str, Any]:
    envelope = json.loads(path.read_text(encoding="utf-8"))
    if stable_hash(envelope.get("payload")) != envelope.get("sha256"):
        raise ValueError(f"LIVE_EVIDENCE_HASH_MISMATCH:{path.stem}")
    payload = envelope.get("payload") or {}
    if payload.get("run_identity_hash") != identity_hash:
        raise ValueError(f"LIVE_EVIDENCE_IDENTITY_MISMATCH:{path.stem}")
    if payload.get("cell") != cell.to_dict():
        raise ValueError(f"LIVE_EVIDENCE_CELL_MISMATCH:{path.stem}")
    return envelope


def run_live_cells(
    *,
    cells: list[LiveCell],
    provider: ModelProvider | None,
    output_dir: Path,
    identity: RunIdentity,
    rerun_invalid: bool = False,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    manifest = prepare_live_run(output_dir, identity, cells)
    evidence: list[dict[str, Any]] = []
    identity_hash = str(manifest["run_identity_hash"])
    for cell in cells:
        path = output_dir / "cells" / f"{cell.cell_id}.json"
        envelope: dict[str, Any] | None = None
        if path.exists():
            envelope = _load_envelope(path, identity_hash=identity_hash, cell=cell)
            prior_score = (envelope.get("payload") or {}).get("outcome", {}).get("score")
            if prior_score is None and rerun_invalid:
                envelope = None
        if envelope is None:
            retries_before = int(getattr(provider, "transport_retries_total", 0) or 0) if provider is not None else 0
            outcome = _dispatch(cell, provider)
            retries_after = int(getattr(provider, "transport_retries_total", retries_before) or 0) if provider is not None else retries_before
            outcome = dict(outcome)
            outcome["transport_retries"] = max(0, retries_after - retries_before)
            payload = {
                "run_identity_hash": identity_hash,
                "cell": cell.to_dict(),
                "outcome": outcome,
            }
            envelope = {"payload": payload, "sha256": stable_hash(payload)}
            _atomic_json(path, envelope)
        evidence.append(envelope)

    terminal = len(evidence)
    invalid = sum(1 for item in evidence if item["payload"]["outcome"].get("score") is None)
    verified = sum(1 for item in evidence if item["payload"]["outcome"].get("score") == 1)
    unresolved = terminal - invalid - verified
    model_calls = sum(int(item["payload"]["outcome"].get("model_calls", 0) or 0) for item in evidence)
    transport_retries = sum(int(item["payload"]["outcome"].get("transport_retries", 0) or 0) for item in evidence)
    evidence_kinds: dict[str, int] = {}
    for item in evidence:
        kind = str(item["payload"]["outcome"].get("evidence_kind") or "UNSPECIFIED")
        evidence_kinds[kind] = evidence_kinds.get(kind, 0) + 1
    summary = {
        "experiment": EXPERIMENT,
        "profile": identity.profile,
        "enabled_live_phases": manifest["enabled_live_phases"],
        "expected_cells": len(cells),
        "terminal_cells": terminal,
        "invalid_cells": invalid,
        "verified_successes": verified,
        "valid_unresolved": unresolved,
        "model_calls": model_calls,
        "transport_retries": transport_retries,
        "ledger_hash": manifest["ledger_hash"],
        "run_identity_hash": identity_hash,
        "evidence_kinds": evidence_kinds,
        "conclusion": "DISCOVERY_COMPLETE" if terminal == len(cells) and invalid == 0 else "PARTIAL_INVALID_EVIDENCE",
    }
    _atomic_json(output_dir / "live-summary.json", summary)
    return summary


def run_cd_experiment(
    *,
    provider: ModelProvider,
    output_dir: Path,
    identity: RunIdentity,
    phases: tuple[str, ...] = ("C", "D"),
    rerun_invalid: bool = False,
) -> dict[str, Any]:
    cells = build_cd_ledger(phases)
    return run_live_cells(cells=cells, provider=provider, output_dir=output_dir, identity=identity, rerun_invalid=rerun_invalid)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Experiment 010 live C/D runner. G/H/I are intentionally disabled before the evidence gate.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--system-version", required=True)
    parser.add_argument("--model-digest")
    parser.add_argument("--provider-version")
    parser.add_argument("--context-limit", type=int)
    parser.add_argument("--phases", choices=("C", "D", "CD"), default="CD")
    parser.add_argument("--rerun-invalid", action="store_true")
    args = parser.parse_args(argv)

    phases = ("C", "D") if args.phases == "CD" else (args.phases,)
    identity = make_run_identity(
        system_version=args.system_version,
        model_id=args.model_id,
        endpoint=args.endpoint,
        provider_kind="ollama",
        model_digest=args.model_digest,
        provider_version=args.provider_version,
        context_limit=args.context_limit,
    )
    provider = OllamaProvider(model_id=args.model_id, endpoint=args.endpoint)
    try:
        summary = run_cd_experiment(
            provider=provider,
            output_dir=Path(args.output_dir),
            identity=identity,
            phases=phases,
            rerun_invalid=bool(args.rerun_invalid),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"LIVE_HARNESS_ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["conclusion"] == "DISCOVERY_COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
