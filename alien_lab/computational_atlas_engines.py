from __future__ import annotations

from collections import deque
from itertools import combinations
from typing import Any

from .computational_atlas_types import EngineResult, stable_hash


CAPABILITIES = ("G", "L", "C", "P", "X", "M", "D", "R")


def _graph(payload: dict[str, Any]) -> EngineResult:
    edges = payload.get("edges")
    start = payload.get("start")
    goal = payload.get("goal")
    if not isinstance(edges, list) or not isinstance(start, str) or not isinstance(goal, str):
        return EngineResult(False, error="GRAPH_INPUT_INVALID")
    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        if not isinstance(edge, list) or len(edge) != 2:
            return EngineResult(False, error="GRAPH_EDGE_INVALID")
        left, right = str(edge[0]), str(edge[1])
        adjacency.setdefault(left, []).append(right)
    for values in adjacency.values():
        values.sort()
    queue = deque([(start, [start])])
    seen = {start}
    while queue:
        node, path = queue.popleft()
        if node == goal:
            return EngineResult(True, path, {"path_hash": stable_hash(path)})
        for nxt in adjacency.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, path + [nxt]))
    return EngineResult(False, error="GRAPH_NO_PATH")


def _logic(payload: dict[str, Any]) -> EngineResult:
    facts = payload.get("facts")
    rules = payload.get("rules")
    query = payload.get("query")
    if not isinstance(facts, dict) or not isinstance(rules, list) or not isinstance(query, str):
        return EngineResult(False, error="LOGIC_INPUT_INVALID")
    known = {str(key) for key, value in facts.items() if bool(value)}
    changed = True
    while changed:
        changed = False
        for rule in rules:
            if not isinstance(rule, list) or len(rule) != 2:
                return EngineResult(False, error="LOGIC_RULE_INVALID")
            antecedent, consequent = str(rule[0]), str(rule[1])
            if antecedent in known and consequent not in known:
                known.add(consequent)
                changed = True
    value = query in known
    return EngineResult(True, value, {"entailed": sorted(known)})


def _constraint(payload: dict[str, Any]) -> EngineResult:
    items = payload.get("items")
    budget = payload.get("budget")
    if not isinstance(items, list) or not isinstance(budget, (int, float)):
        return EngineResult(False, error="CONSTRAINT_INPUT_INVALID")
    normalized: list[tuple[str, float, float]] = []
    for raw in items:
        if not isinstance(raw, dict):
            return EngineResult(False, error="CONSTRAINT_ITEM_INVALID")
        try:
            normalized.append((str(raw["id"]), float(raw["cost"]), float(raw["value"])))
        except (KeyError, TypeError, ValueError):
            return EngineResult(False, error="CONSTRAINT_ITEM_INVALID")
    best_ids: tuple[str, ...] = ()
    best_value = float("-inf")
    best_cost = float("inf")
    for size in range(len(normalized) + 1):
        for subset in combinations(normalized, size):
            cost = sum(item[1] for item in subset)
            value = sum(item[2] for item in subset)
            ids = tuple(sorted(item[0] for item in subset))
            if cost > float(budget):
                continue
            candidate = (value, -cost, tuple(reversed(ids)))
            current = (best_value, -best_cost, tuple(reversed(best_ids)))
            if candidate > current:
                best_value, best_cost, best_ids = value, cost, ids
    return EngineResult(True, list(best_ids), {"objective": best_value, "cost": best_cost})


def _planning(payload: dict[str, Any]) -> EngineResult:
    transitions = payload.get("transitions")
    start = payload.get("start")
    goal = payload.get("goal")
    if not isinstance(transitions, dict) or not isinstance(start, str) or not isinstance(goal, str):
        return EngineResult(False, error="PLANNING_INPUT_INVALID")
    queue = deque([(start, [start])])
    seen = {start}
    while queue:
        state, path = queue.popleft()
        if state == goal:
            return EngineResult(True, path, {"steps": len(path) - 1})
        next_states = transitions.get(state, [])
        if not isinstance(next_states, list):
            return EngineResult(False, error="PLANNING_TRANSITIONS_INVALID")
        for nxt in sorted(str(item) for item in next_states):
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, path + [nxt]))
    return EngineResult(False, error="PLANNING_NO_PLAN")


def _program(payload: dict[str, Any]) -> EngineResult:
    program = payload.get("program")
    returned = payload.get("return")
    if not isinstance(program, list) or not isinstance(returned, str):
        return EngineResult(False, error="PROGRAM_INPUT_INVALID")
    env: dict[str, float | int] = {}
    for instruction in program:
        if not isinstance(instruction, dict):
            return EngineResult(False, error="PROGRAM_INSTRUCTION_INVALID")
        op = instruction.get("op")
        name = instruction.get("name")
        value = instruction.get("value")
        if not isinstance(name, str) or not isinstance(value, (int, float)):
            return EngineResult(False, error="PROGRAM_INSTRUCTION_INVALID")
        if op == "set":
            env[name] = value
        elif name not in env:
            return EngineResult(False, error=f"PROGRAM_UNBOUND:{name}")
        elif op == "add":
            env[name] = env[name] + value
        elif op == "sub":
            env[name] = env[name] - value
        elif op == "mul":
            env[name] = env[name] * value
        elif op == "div":
            if value == 0:
                return EngineResult(False, error="PROGRAM_DIV_ZERO")
            env[name] = env[name] / value
        else:
            return EngineResult(False, error=f"PROGRAM_OP_UNSUPPORTED:{op}")
    if returned not in env:
        return EngineResult(False, error=f"PROGRAM_RETURN_UNBOUND:{returned}")
    return EngineResult(True, env[returned], {"environment_hash": stable_hash(env)})


def _math(payload: dict[str, Any]) -> EngineResult:
    operation = payload.get("operation")
    values = payload.get("values")
    if not isinstance(values, list) or not all(isinstance(item, (int, float)) for item in values):
        return EngineResult(False, error="MATH_VALUES_INVALID")
    if operation == "weighted_mean":
        weights = payload.get("weights")
        if not isinstance(weights, list) or len(weights) != len(values) or not all(isinstance(item, (int, float)) for item in weights):
            return EngineResult(False, error="MATH_WEIGHTS_INVALID")
        denominator = float(sum(weights))
        if denominator == 0:
            return EngineResult(False, error="MATH_ZERO_WEIGHT")
        answer = sum(float(v) * float(w) for v, w in zip(values, weights)) / denominator
        return EngineResult(True, answer, {"operation": operation})
    if operation == "sum":
        return EngineResult(True, sum(values), {"operation": operation})
    return EngineResult(False, error=f"MATH_OPERATION_UNSUPPORTED:{operation}")


def _data(payload: dict[str, Any]) -> EngineResult:
    left = payload.get("left")
    right = payload.get("right")
    left_key = payload.get("left_key")
    right_key = payload.get("right_key")
    sum_field = payload.get("sum_field")
    if not isinstance(left, list) or not isinstance(right, list) or not all(isinstance(item, dict) for item in left + right):
        return EngineResult(False, error="DATA_ROWS_INVALID")
    if not all(isinstance(item, str) for item in (left_key, right_key, sum_field)):
        return EngineResult(False, error="DATA_KEYS_INVALID")
    right_index = {row.get(right_key): row for row in right}
    total: float | int = 0
    joined = 0
    for row in left:
        peer = right_index.get(row.get(left_key))
        if peer is None:
            continue
        value = peer.get(sum_field)
        if not isinstance(value, (int, float)):
            return EngineResult(False, error="DATA_SUM_VALUE_INVALID")
        total += value
        joined += 1
    return EngineResult(True, total, {"joined_rows": joined})


def _retrieval(payload: dict[str, Any]) -> EngineResult:
    query_terms = payload.get("query_terms")
    records = payload.get("records")
    top_k = payload.get("top_k")
    if not isinstance(query_terms, list) or not isinstance(records, list) or not isinstance(top_k, int) or top_k < 1:
        return EngineResult(False, error="RETRIEVAL_INPUT_INVALID")
    query = {str(term) for term in query_terms}
    ranked = []
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("terms"), list):
            return EngineResult(False, error="RETRIEVAL_RECORD_INVALID")
        overlap = len(query.intersection(str(term) for term in record["terms"]))
        authority = int(record.get("authority", 0))
        ranked.append((-overlap, -authority, str(record.get("id"))))
    ranked.sort()
    result = [item[2] for item in ranked[:top_k]]
    return EngineResult(True, result, {"query_terms": sorted(query)})


_ENGINES = {
    "G": _graph,
    "L": _logic,
    "C": _constraint,
    "P": _planning,
    "X": _program,
    "M": _math,
    "D": _data,
    "R": _retrieval,
}


def run_engine(capability: str, payload: dict[str, Any], inputs: dict[str, Any] | None = None) -> EngineResult:
    del inputs  # Reserved for typed cross-engine handoffs in later 010 phases.
    engine = _ENGINES.get(capability)
    if engine is None:
        return EngineResult(False, error=f"UNSUPPORTED_CAPABILITY:{capability}")
    try:
        return engine(payload)
    except Exception as exc:  # A reference engine failure is evidence, not a harness crash.
        return EngineResult(False, error=f"ENGINE_EXCEPTION:{type(exc).__name__}:{exc}")
