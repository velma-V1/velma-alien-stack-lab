from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable

from .computational_atlas_live_ledger import build_phase_c_ledger, build_phase_d_ledger
from .computational_atlas_live_runner import rescue_phase_c_outcome, run_phase_c_cell, run_phase_d_cell
from .computational_atlas_live_types import LiveCell, RunIdentity
from .computational_atlas_providers import ModelProvider, OllamaProvider, seal_run_identity
from .computational_atlas_semantics import DIRECT_SYSTEM_PROMPT, SEMANTIC_SYSTEM_PROMPT
from .computational_atlas_surfaces import task_ir_json_schema
from .computational_atlas_types import stable_hash
from .computational_atlas_worlds import build_worlds


EXPERIMENT = "010-computational-basis-atlas"
LIVE_PROFILE = "live-cd-v1"
_SUPPORTED_LIVE_PHASES = ("C", "D")
_MIN_OLLAMA_STRUCTURED_OUTPUT_VERSION = (0, 5, 0)


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
        "surface_contract": "experiment-010-live-surfaces-v2-readable-r5-explicit-intents",
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


def _normalized_endpoint(value: str) -> str:
    return str(value).rstrip("/")


def _normalized_version(value: str) -> str:
    return str(value).strip().lstrip("vV")


def _version_tuple(value: str) -> tuple[int, int, int]:
    normalized = _normalized_version(value)
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", normalized)
    if match is None:
        raise ValueError(f"PROVIDER_VERSION_INVALID:{value}")
    return tuple(int(part) for part in match.groups())


def _validate_provider_identity(provider: ModelProvider | None, identity: RunIdentity) -> None:
    if provider is None:
        return
    provider_kind = str(getattr(provider, "provider_kind", ""))
    model_id = str(getattr(provider, "model_id", ""))
    endpoint = _normalized_endpoint(str(getattr(provider, "endpoint", "")))
    expected = (
        str(identity.provider_kind),
        str(identity.model_id),
        _normalized_endpoint(identity.endpoint),
    )
    observed = (provider_kind, model_id, endpoint)
    if observed != expected:
        raise ValueError(f"PROVIDER_IDENTITY_MISMATCH:expected={expected}:observed={observed}")

    if provider_kind == "fake":
        return

    context_limit = identity.generation_contract.get("context_limit")
    if not isinstance(context_limit, int) or isinstance(context_limit, bool) or context_limit <= 0:
        raise ValueError("LIVE_CONTEXT_LIMIT_REQUIRED")

    sealed_provider_version = str(identity.provider_version or "").strip()
    if not sealed_provider_version:
        raise ValueError("LIVE_PROVIDER_VERSION_REQUIRED")

    if provider_kind == "ollama":
        version_reader = getattr(provider, "server_version", None)
        if not callable(version_reader):
            raise ValueError("PROVIDER_VERSION_UNAVAILABLE")
        actual_provider_version = str(version_reader()).strip()
        if _normalized_version(actual_provider_version) != _normalized_version(sealed_provider_version):
            raise ValueError(
                f"PROVIDER_VERSION_MISMATCH:sealed={sealed_provider_version}:actual={actual_provider_version}"
            )
        if _version_tuple(actual_provider_version) < _MIN_OLLAMA_STRUCTURED_OUTPUT_VERSION:
            raise ValueError(
                "STRUCTURED_OUTPUT_VERSION_UNSUPPORTED:"
                f"actual={actual_provider_version}:minimum=0.5.0"
            )
        if not bool(getattr(provider, "supports_structured_output", False)):
            raise ValueError("STRUCTURED_OUTPUT_UNSUPPORTED")

        digest_reader = getattr(provider, "model_digest", None)
        if not callable(digest_reader):
            raise ValueError("MODEL_DIGEST_UNAVAILABLE")
        actual_model_digest = str(digest_reader()).strip()
        sealed_model_digest = str(identity.model_digest or "").strip()
        if actual_model_digest and not sealed_model_digest:
            raise ValueError("LIVE_MODEL_DIGEST_REQUIRED")
        if sealed_model_digest != actual_model_digest:
            raise ValueError(
                f"MODEL_DIGEST_MISMATCH:sealed={sealed_model_digest}:actual={actual_model_digest}"
            )

        provider_context_limit = getattr(provider, "context_limit", None)
        if provider_context_limit != context_limit:
            raise ValueError(
                f"PROVIDER_CONTEXT_LIMIT_MISMATCH:sealed={context_limit}:configured={provider_context_limit}"
            )

        capabilities_reader = getattr(provider, "model_capabilities", None)
        if not callable(capabilities_reader):
            raise ValueError("MODEL_CAPABILITIES_UNAVAILABLE")
        capabilities = tuple(str(item) for item in capabilities_reader())
        try:
            setattr(provider, "supports_images", "vision" in capabilities)
        except Exception:
            pass


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


def _load_rescue_envelope(
    path: Path,
    *,
    identity_hash: str,
    cell: LiveCell,
    original_sha256: str,
) -> dict[str, Any]:
    envelope = json.loads(path.read_text(encoding="utf-8"))
    if stable_hash(envelope.get("payload")) != envelope.get("sha256"):
        raise ValueError(f"LIVE_RESCUE_HASH_MISMATCH:{path.stem}")
    payload = envelope.get("payload") or {}
    if payload.get("run_identity_hash") != identity_hash:
        raise ValueError(f"LIVE_RESCUE_IDENTITY_MISMATCH:{path.stem}")
    if payload.get("cell") != cell.to_dict():
        raise ValueError(f"LIVE_RESCUE_CELL_MISMATCH:{path.stem}")
    if payload.get("original_evidence_sha256") != original_sha256:
        raise ValueError(f"LIVE_RESCUE_ORIGINAL_MISMATCH:{path.stem}")
    return envelope


def _aggregate_group(items: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        cell = item["payload"]["cell"]
        key = str(cell.get(field) or "NONE")
        grouped.setdefault(key, []).append(item)
    result: dict[str, dict[str, Any]] = {}
    for key, group in grouped.items():
        valid = [entry for entry in group if entry["payload"]["outcome"].get("score") is not None]
        verified = sum(1 for entry in valid if entry["payload"]["outcome"].get("score") == 1)
        result[key] = {
            "terminal_cells": len(group),
            "valid_cells": len(valid),
            "invalid_cells": len(group) - len(valid),
            "verified_successes": verified,
            "valid_unresolved": len(valid) - verified,
            "verified_success_rate": (verified / len(valid)) if valid else None,
        }
    return result


def _semantic_formalization_tax(items: list[dict[str, Any]]) -> dict[str, Any]:
    paired: dict[tuple[int, str], dict[str, int | None]] = {}
    for item in items:
        cell = item["payload"]["cell"]
        if cell.get("phase") != "C":
            continue
        world_index = cell.get("world_index")
        representation = cell.get("representation")
        arm = cell.get("arm")
        if not isinstance(world_index, int) or world_index >= 184 or not isinstance(representation, str):
            continue
        if arm not in {"ORACLE_IR_BASIS", "LOCAL_SEMANTIC_COMPILER_BASIS"}:
            continue
        score = item["payload"]["outcome"].get("score")
        paired.setdefault((world_index, representation), {})[str(arm)] = score

    taxes: list[float] = []
    by_representation: dict[str, list[float]] = {}
    for (_, representation), values in paired.items():
        if "ORACLE_IR_BASIS" not in values or "LOCAL_SEMANTIC_COMPILER_BASIS" not in values:
            continue
        oracle_score = values["ORACLE_IR_BASIS"]
        local_score = values["LOCAL_SEMANTIC_COMPILER_BASIS"]
        if oracle_score is None or local_score is None:
            continue
        tax = float(oracle_score - local_score)
        taxes.append(tax)
        by_representation.setdefault(representation, []).append(tax)

    return {
        "paired_cells": len(taxes),
        "mean_tax": (sum(taxes) / len(taxes)) if taxes else None,
        "by_representation": {
            representation: {
                "paired_cells": len(values),
                "mean_tax": sum(values) / len(values),
            }
            for representation, values in sorted(by_representation.items())
        },
        "rescued_scores_substituted": False,
    }


def _needs_automatic_c_rescue(cell: LiveCell, outcome: dict[str, Any]) -> bool:
    return (
        cell.phase == "C"
        and cell.arm == "LOCAL_SEMANTIC_COMPILER_BASIS"
        and outcome.get("score") == 0
        and str(outcome.get("status") or "").startswith("VALID_")
    )


def run_live_cells(
    *,
    cells: list[LiveCell],
    provider: ModelProvider | None,
    output_dir: Path,
    identity: RunIdentity,
    rerun_invalid: bool = False,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    _validate_provider_identity(provider, identity)
    manifest = prepare_live_run(output_dir, identity, cells)
    evidence: list[dict[str, Any]] = []
    rescues: list[dict[str, Any]] = []
    identity_hash = str(manifest["run_identity_hash"])
    phase_c_worlds: list[Any] | None = None

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

        outcome = envelope["payload"]["outcome"]
        if _needs_automatic_c_rescue(cell, outcome):
            if phase_c_worlds is None:
                phase_c_worlds = build_worlds(seed=20260910, count=192)
            world = phase_c_worlds[int(cell.world_index)]
            rescue_path = output_dir / "rescues" / f"{cell.cell_id}.json"
            rescue_envelope: dict[str, Any]
            if rescue_path.exists():
                rescue_envelope = _load_rescue_envelope(
                    rescue_path,
                    identity_hash=identity_hash,
                    cell=cell,
                    original_sha256=str(envelope["sha256"]),
                )
            else:
                rescue = rescue_phase_c_outcome(outcome, world)
                rescue_payload = {
                    "run_identity_hash": identity_hash,
                    "cell": cell.to_dict(),
                    "original_evidence_sha256": envelope["sha256"],
                    "rescue": rescue,
                }
                rescue_envelope = {"payload": rescue_payload, "sha256": stable_hash(rescue_payload)}
                _atomic_json(rescue_path, rescue_envelope)
            rescues.append(rescue_envelope)

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

    fixture_run = identity.provider_kind == "fake" or evidence_kinds.get("FAKE_MECHANICS_ONLY", 0) > 0
    if fixture_run:
        conclusion = "NON_LIVE_FIXTURE_RUN"
    elif terminal == len(cells) and invalid == 0:
        conclusion = "DISCOVERY_COMPLETE"
    else:
        conclusion = "PARTIAL_INVALID_EVIDENCE"

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
        "live_model_evidence": bool(not fixture_run and evidence_kinds.get("LIVE_MODEL_EVIDENCE", 0) > 0),
        "rescue_cells": len(rescues),
        "by_arm": _aggregate_group(evidence, "arm"),
        "by_representation": _aggregate_group(evidence, "representation"),
        "semantic_formalization_tax": _semantic_formalization_tax(evidence),
        "conclusion": conclusion,
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
    parser.add_argument("--model-digest", help="Optional asserted model digest; actual Ollama digest must match.")
    parser.add_argument("--provider-version", help="Optional asserted Ollama server version; actual /api/version must match.")
    parser.add_argument("--context-limit", type=int, required=True)
    parser.add_argument("--phases", choices=("C", "D", "CD"), default="CD")
    parser.add_argument("--rerun-invalid", action="store_true")
    args = parser.parse_args(argv)

    phases = ("C", "D") if args.phases == "CD" else (args.phases,)
    provider = OllamaProvider(model_id=args.model_id, endpoint=args.endpoint, context_limit=args.context_limit)
    try:
        actual_provider_version = provider.server_version()
        actual_model_digest = provider.model_digest()
        provider.model_capabilities()
        identity = make_run_identity(
            system_version=args.system_version,
            model_id=args.model_id,
            endpoint=args.endpoint,
            provider_kind="ollama",
            model_digest=args.model_digest or actual_model_digest,
            provider_version=args.provider_version or actual_provider_version,
            context_limit=args.context_limit,
        )
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
