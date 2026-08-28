from __future__ import annotations

import time

from .primitives import PASS_FUNCTIONS
from .types import CompilerInput, Derivation, Workspace


def compile_workspace(
    view: CompilerInput,
    primitives: tuple[str, ...],
    order: tuple[str, ...] | None = None,
) -> Workspace:
    enabled = tuple(dict.fromkeys(primitives))
    unknown = set(enabled) - set(PASS_FUNCTIONS)
    if unknown:
        raise ValueError(f"unknown primitives: {sorted(unknown)}")
    execution_order = tuple(order) if order is not None else enabled
    if set(execution_order) != set(enabled) or len(execution_order) != len(enabled):
        raise ValueError("order must contain each enabled primitive exactly once")
    ws = Workspace(
        task_id=view.task_id,
        evidence_ids=[s.record_id for s in view.sources],
        edge_ids=[e.edge_id for e in view.edges],
    )
    for name in execution_order:
        started = time.perf_counter()
        PASS_FUNCTIONS[name](view, ws)
        ws.pass_timings_ms[name] = (time.perf_counter() - started) * 1000.0
        ws.pass_order.append(name)
    return ws


def fuse_workspace(view: CompilerInput, ws: Workspace) -> Workspace:
    """Create answer-independent cross-pass relations from already-derived state.

    Fusion is deliberately a meta-operation, not one of the six Boolean-cube
    primitives. It is tested only after the base causal effects are known.
    """
    started = time.perf_counter()
    relations = []
    path = list(ws.active_path)
    if path:
        for key, value in sorted(ws.current_state.items()):
            relations.append({
                "kind": "active_state",
                "path": path,
                "key": key,
                "value": value,
            })
        for item in ws.contradictions:
            relations.append({
                "kind": "active_uncertainty",
                "path": path,
                "key": item["key"],
                "values": list(item["values"]),
            })
        for item in ws.memory_deltas:
            relations.append({
                "kind": "active_transition",
                "path": path,
                "key": item["key"],
                "from": item["from"],
                "to": item["to"],
            })
    ws.fused_relations.extend(relations)
    input_ids = sorted({item for d in ws.derivations for item in d.input_ids})
    ws.derivations.append(
        Derivation(
            "fusion",
            "cross_pass_relations",
            relations,
            input_ids,
            "join already-derived active-path structure with current state, unresolved uncertainty, and historical transitions without inspecting questions or choices",
        )
    )
    ws.pass_timings_ms["fusion"] = (time.perf_counter() - started) * 1000.0
    ws.pass_order.append("fusion")
    return ws


def recursive_fuse_workspace(view: CompilerInput, ws: Workspace, depth: int = 2) -> Workspace:
    """Build higher-order relations from first-order fused relations.

    The closure is intentionally conservative: two relations may join only when
    they share the same task key and active path. This prevents arbitrary
    combinatorial mixing while allowing a compound output to become an input to
    a later compound operation.
    """
    import json
    from itertools import combinations

    if depth < 1:
        raise ValueError("depth must be >= 1")
    if "fusion" not in ws.pass_order:
        fuse_workspace(view, ws)
    for level in range(2, depth + 1):
        started = time.perf_counter()
        snapshot = list(ws.fused_relations)
        existing = {json.dumps(item, sort_keys=True) for item in snapshot}
        created = []
        for left, right in combinations(snapshot, 2):
            if left.get("key") is None or right.get("key") is None:
                continue
            if left.get("key") != right.get("key"):
                continue
            if left.get("path") != right.get("path"):
                continue
            if left.get("kind") == right.get("kind"):
                continue
            facts = {}
            for label, relation in (("left", left), ("right", right)):
                facts[label] = {
                    k: v for k, v in relation.items()
                    if k not in {"kind", "path", "key"}
                }
            relation = {
                "kind": "relational_join",
                "depth": level,
                "path": left.get("path"),
                "key": left.get("key"),
                "parents": sorted([str(left.get("kind")), str(right.get("kind"))]),
                "facts": facts,
            }
            marker = json.dumps(relation, sort_keys=True)
            if marker not in existing:
                existing.add(marker)
                created.append(relation)
        ws.fused_relations.extend(created)
        input_ids = sorted({item for d in ws.derivations for item in d.input_ids})
        pass_name = f"fusion_depth_{level}"
        ws.derivations.append(Derivation(
            pass_name,
            "recursive_relational_closure",
            created,
            input_ids,
            "join prior compound relations only when they share the same active path and task key; preserve parent relation identities",
        ))
        ws.pass_timings_ms[pass_name] = (time.perf_counter() - started) * 1000.0
        ws.pass_order.append(pass_name)
    return ws
