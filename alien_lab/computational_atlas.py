from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

from .computational_atlas_engines import CAPABILITIES, run_engine
from .computational_atlas_types import AtlasCell, stable_hash
from .computational_atlas_worlds import World, build_worlds


ALL_CAPABILITIES = CAPABILITIES
RESCUE_STAGES = (
    "SEMANTIC",
    "DECOMPOSITION",
    "ROUTING",
    "ENGINE",
    "COMPOSITION",
    "EXECUTION",
    "VERIFICATION",
)


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def default_config(*, profile: str = "atlas", seed: int = 20260829) -> dict[str, Any]:
    if profile not in {"smoke", "atlas", "local", "frontier"}:
        raise ValueError(f"unsupported profile: {profile}")
    return {
        "experiment": "010-computational-basis-atlas",
        "profile": profile,
        "seed": int(seed),
        "world_count": 192,
        "representation_levels": ["R0_ORACLE_IR", "R1_STRUCTURED", "R2_NATURAL", "R3_PARAPHRASED", "R4_IMPLICIT", "R5_PERCEPTUAL"],
        "capabilities": list(ALL_CAPABILITIES),
    }


def _subsets(capabilities: tuple[str, ...]) -> Iterable[tuple[str, ...]]:
    for mask in range(1 << len(capabilities)):
        yield tuple(capabilities[index] for index in range(len(capabilities)) if mask & (1 << index))


def _diagnostic_worlds(worlds: list[World]) -> list[World]:
    indexes = list(range(0, 24)) + list(range(64, 84)) + list(range(128, 140)) + list(range(168, 176))
    return [worlds[index] for index in indexes]


def build_ledger(config: dict[str, Any]) -> list[AtlasCell]:
    profile = str(config["profile"])
    seed = int(config["seed"])
    worlds = build_worlds(seed=seed, count=int(config.get("world_count", 192)))
    cells: list[AtlasCell] = []

    diagnostics = _diagnostic_worlds(worlds)
    if profile == "smoke":
        diagnostics = diagnostics[:8]
        subset_space = list(_subsets(ALL_CAPABILITIES[:4]))
    else:
        subset_space = list(_subsets(ALL_CAPABILITIES))

    order = 0
    for world in diagnostics:
        for subset in subset_space:
            arm = "NONE" if not subset else "+".join(subset)
            raw = ["A_ATTRIBUTION", world.world_id, list(subset), seed]
            cells.append(AtlasCell(
                cell_id=f"A-{stable_hash(raw)[:20]}",
                order=order,
                phase="A_ATTRIBUTION",
                world_id=world.world_id,
                capabilities=subset,
                arm=arm,
            ))
            order += 1

    phase_b_worlds = worlds[:12] if profile == "smoke" else worlds
    phase_b_arms: list[tuple[str, tuple[str, ...]]] = [("FULL", ALL_CAPABILITIES)]
    phase_b_arms.extend(
        (f"WITHOUT_{removed}", tuple(cap for cap in ALL_CAPABILITIES if cap != removed))
        for removed in ALL_CAPABILITIES
    )
    for world in phase_b_worlds:
        for arm, subset in phase_b_arms:
            raw = ["B_ORACLE_CEILING", world.world_id, arm, list(subset), seed]
            cells.append(AtlasCell(
                cell_id=f"B-{stable_hash(raw)[:20]}",
                order=order,
                phase="B_ORACLE_CEILING",
                world_id=world.world_id,
                capabilities=subset,
                arm=arm,
            ))
            order += 1
    return cells


def _execute_world(world: World, capabilities: tuple[str, ...]) -> dict[str, Any]:
    if world.outside_basis:
        return {
            "status": "VALID_UNRESOLVED_MISSING_CAPABILITY",
            "score": 0,
            "verified": False,
            "result": None,
            "error": "OUTSIDE_INITIAL_BASIS",
        }
    missing = [cap for cap in world.required_capabilities if cap not in capabilities]
    if missing:
        return {
            "status": "VALID_UNRESOLVED_ENGINE",
            "score": 0,
            "verified": False,
            "result": None,
            "error": f"MISSING_CAPABILITIES:{','.join(missing)}",
        }
    values = []
    certificates = []
    for operation in world.task_ir.operations:
        result = run_engine(operation.capability, operation.payload, {})
        if not result.ok:
            return {
                "status": "VALID_UNRESOLVED_ENGINE",
                "score": 0,
                "verified": False,
                "result": values,
                "error": result.error,
            }
        values.append(result.value)
        certificates.append(result.certificate)
    observed = tuple(values)
    verified = observed == world.expected_result
    return {
        "status": "VERIFIED_SUCCESS" if verified else "VALID_UNRESOLVED_VERIFICATION",
        "score": 1 if verified else 0,
        "verified": verified,
        "result": values,
        "certificates": certificates,
        "error": None if verified else "EXPECTED_RESULT_MISMATCH",
    }


def run_cell(cell: AtlasCell, world: World) -> dict[str, Any]:
    outcome = _execute_world(world, cell.capabilities)
    payload = {
        "cell": cell.to_dict(),
        "world_hash": stable_hash(world.sealed_dict()),
        "required_capabilities_hash": stable_hash(list(world.required_capabilities)),
        "status": outcome["status"],
        "score": outcome["score"],
        "verified": outcome["verified"],
        "result": outcome.get("result"),
        "certificates": outcome.get("certificates", []),
        "error": outcome.get("error"),
        "model_calls": 0,
    }
    return {"payload": payload, "sha256": stable_hash(payload)}


def diagnose_rescue(original_success: bool, rescue_results: dict[str, bool]) -> str:
    if original_success:
        return "NONE"
    for stage in RESCUE_STAGES:
        if rescue_results.get(stage) is True:
            return stage
    return "MISSING_CAPABILITY"


def _phase_maps(evidence: list[dict[str, Any]], worlds_by_id: dict[str, World]) -> dict[str, Any]:
    phase_b = [item["payload"] for item in evidence if item["payload"]["cell"]["phase"] == "B_ORACLE_CEILING"]
    full = [item for item in phase_b if item["cell"]["arm"] == "FULL"]
    coverage_by_family: dict[str, dict[str, int]] = {}
    for item in full:
        world = worlds_by_id[item["cell"]["world_id"]]
        bucket = coverage_by_family.setdefault(world.family, {"success": 0, "total": 0, "outside_basis": 0})
        bucket["total"] += 1
        bucket["success"] += int(item["score"] == 1)
        bucket["outside_basis"] += int(world.outside_basis)

    leave_one_out: dict[str, dict[str, int]] = {}
    for removed in ALL_CAPABILITIES:
        rows = [item for item in phase_b if item["cell"]["arm"] == f"WITHOUT_{removed}"]
        leave_one_out[removed] = {
            "success": sum(int(item["score"] == 1) for item in rows),
            "total": len(rows),
        }

    phase_a = [item["payload"] for item in evidence if item["payload"]["cell"]["phase"] == "A_ATTRIBUTION"]
    minimal_basis: dict[str, list[str]] = {}
    by_world: dict[str, list[dict[str, Any]]] = {}
    for item in phase_a:
        by_world.setdefault(item["cell"]["world_id"], []).append(item)
    for world_id, rows in by_world.items():
        winners = [row for row in rows if row["score"] == 1]
        if not winners:
            minimal_basis[world_id] = []
            continue
        winners.sort(key=lambda row: (len(row["cell"]["capabilities"]), row["cell"]["capabilities"]))
        minimal_basis[world_id] = list(winners[0]["cell"]["capabilities"])

    return {
        "computational_coverage": coverage_by_family,
        "leave_one_out": leave_one_out,
        "minimum_basis": minimal_basis,
    }


def run_experiment(config: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger = build_ledger(config)
    ledger_payload = [cell.to_dict() for cell in ledger]
    ledger_hash = stable_hash({"config": config, "ledger": ledger_payload})
    manifest_path = output_dir / "ledger-manifest.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("ledger_hash") != ledger_hash:
            raise ValueError("OUTPUT_DIRECTORY_LEDGER_MISMATCH")
    else:
        atomic_json(output_dir / "ledger.json", ledger_payload)
        atomic_json(manifest_path, {"ledger_hash": ledger_hash, "expected_cells": len(ledger), "config": config})

    worlds = build_worlds(seed=int(config["seed"]), count=int(config.get("world_count", 192)))
    worlds_by_id = {world.world_id: world for world in worlds}
    evidence: list[dict[str, Any]] = []
    for cell in ledger:
        path = output_dir / "cells" / f"{cell.cell_id}.json"
        if path.exists():
            envelope = json.loads(path.read_text(encoding="utf-8"))
            if stable_hash(envelope.get("payload")) != envelope.get("sha256"):
                raise ValueError(f"EVIDENCE_HASH_MISMATCH:{cell.cell_id}")
        else:
            envelope = run_cell(cell, worlds_by_id[cell.world_id])
            atomic_json(path, envelope)
        evidence.append(envelope)

    payload_hashes = [item["sha256"] for item in sorted(evidence, key=lambda item: item["payload"]["cell"]["order"])]
    invalid = [item for item in evidence if item["payload"]["score"] is None]
    verified = sum(int(item["payload"]["score"] == 1) for item in evidence)
    maps = _phase_maps(evidence, worlds_by_id)
    summary = {
        "experiment": config["experiment"],
        "profile": config["profile"],
        "conclusion": "DISCOVERY_COMPLETE" if not invalid and len(evidence) == len(ledger) else "PARTIAL_INVALID_EVIDENCE",
        "expected_cells": len(ledger),
        "terminal_cells": len(evidence),
        "invalid_cells": len(invalid),
        "verified_successes": verified,
        "valid_unresolved": len(evidence) - verified - len(invalid),
        "model_calls": sum(int(item["payload"].get("model_calls", 0)) for item in evidence),
        "ledger_hash": ledger_hash,
        "replay_fingerprint": stable_hash(payload_hashes),
        "maps": maps,
    }
    atomic_json(output_dir / "summary.json", summary)
    return summary


def load_config(path: Path, profile_override: str | None = None) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    profile = profile_override or raw.get("profile", "atlas")
    config = default_config(profile=str(profile), seed=int(raw.get("seed", 20260829)))
    if "world_count" in raw:
        config["world_count"] = int(raw["world_count"])
    return config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Experiment 010 Computational Basis Atlas")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--profile", choices=("smoke", "atlas", "local", "frontier"))
    args = parser.parse_args(argv)
    try:
        config = load_config(Path(args.config), args.profile)
        summary = run_experiment(config, Path(args.output_dir))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"CONFIG_OR_HARNESS_ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["conclusion"] == "DISCOVERY_COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
