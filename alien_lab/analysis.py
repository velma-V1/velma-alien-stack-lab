from __future__ import annotations

import math
from itertools import combinations
from typing import Iterable

from .design import PRIMITIVES


def _subsets_of(s: frozenset[str]) -> Iterable[frozenset[str]]:
    items = tuple(sorted(s))
    for size in range(len(items) + 1):
        for combo in combinations(items, size):
            yield frozenset(combo)


def mobius_interactions(values: dict[frozenset[str], float]) -> dict[frozenset[str], float]:
    effects: dict[frozenset[str], float] = {}
    for subset in sorted(values, key=lambda s: (len(s), tuple(sorted(s)))):
        total = 0.0
        for inner in _subsets_of(subset):
            total += ((-1) ** (len(subset) - len(inner))) * float(values[inner])
        effects[subset] = total
    return effects


def shapley_values(
    values: dict[frozenset[str], float],
    primitives: tuple[str, ...] = PRIMITIVES,
) -> dict[str, float]:
    n = len(primitives)
    denom = math.factorial(n)
    result = {p: 0.0 for p in primitives}
    universe = frozenset(primitives)
    for p in primitives:
        others = tuple(sorted(universe - {p}))
        for size in range(len(others) + 1):
            coeff = math.factorial(size) * math.factorial(n - size - 1) / denom
            for combo in combinations(others, size):
                s = frozenset(combo)
                result[p] += coeff * (float(values[s | {p}]) - float(values[s]))
    return result


def _dominates(a: dict, b: dict) -> bool:
    at_least_as_good = (
        a["accuracy"] >= b["accuracy"]
        and a["eval_tokens"] <= b["eval_tokens"]
        and a["wall_ms"] <= b["wall_ms"]
        and a.get("compiler_ms", 0) <= b.get("compiler_ms", 0)
    )
    strictly_better = (
        a["accuracy"] > b["accuracy"]
        or a["eval_tokens"] < b["eval_tokens"]
        or a["wall_ms"] < b["wall_ms"]
        or a.get("compiler_ms", 0) < b.get("compiler_ms", 0)
    )
    return at_least_as_good and strictly_better


def pareto_frontier(rows: list[dict]) -> list[dict]:
    return [row for row in rows if not any(_dominates(other, row) for other in rows if other is not row)]


def minimal_sufficient(rows: list[dict], accuracy_tolerance: float = 0.0) -> list[dict]:
    if not rows:
        return []
    best = max(float(r["accuracy"]) for r in rows)
    capable = [r for r in rows if float(r["accuracy"]) >= best - accuracy_tolerance]
    min_size = min(len(r.get("primitives", [])) for r in capable)
    minimal = [r for r in capable if len(r.get("primitives", [])) == min_size]
    return sorted(minimal, key=lambda r: (r.get("eval_tokens", float("inf")), r.get("id", "")))
