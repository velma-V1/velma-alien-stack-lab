from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .computational_atlas_routing import REAL_TOOL_CATALOG
from .computational_atlas_types import stable_hash


@dataclass(frozen=True)
class FrontierTask:
    task_id: str
    kind: str
    seed: int
    index: int


def _tool_schema() -> list[dict[str, Any]]:
    schemas = []
    for tool in REAL_TOOL_CATALOG:
        schemas.append({
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": {"type": "object", "additionalProperties": True},
        })
    return schemas


def generic_tool_schema_bytes() -> bytes:
    return json.dumps(_tool_schema(), sort_keys=True, separators=(",", ":")).encode("utf-8")


def velma_tool_schema_bytes() -> bytes:
    return json.dumps(_tool_schema(), sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_phase_i_tasks(seed: int = 20260916) -> list[FrontierTask]:
    tasks: list[FrontierTask] = []
    distribution = (("semantic", 12), ("composition", 24), ("horizon", 12))
    index = 0
    for kind, count in distribution:
        for _ in range(count):
            tasks.append(FrontierTask(
                task_id=f"FI-{seed}-{kind}-{index:03d}-{stable_hash([seed, kind, index])[:8]}",
                kind=kind,
                seed=seed,
                index=index,
            ))
            index += 1
    return tasks
