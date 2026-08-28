from __future__ import annotations

from itertools import combinations, permutations

PRIMITIVES = ("state", "path", "uncertainty", "relevance", "procedure", "memory")


def all_subsets(primitives: tuple[str, ...] = PRIMITIVES) -> tuple[frozenset[str], ...]:
    out: list[frozenset[str]] = []
    for size in range(len(primitives) + 1):
        for combo in combinations(primitives, size):
            out.append(frozenset(combo))
    return tuple(out)


def subset_id(subset: frozenset[str]) -> str:
    if not subset:
        return "structured-empty"
    return "+".join(p for p in PRIMITIVES if p in subset)


def representative_orders(subset: frozenset[str], max_orders: int = 12) -> list[tuple[str, ...]]:
    canonical = tuple(p for p in PRIMITIVES if p in subset)
    if len(canonical) <= 1:
        return [canonical]
    if len(canonical) <= 4:
        return list(permutations(canonical))[:max_orders]
    candidates = [canonical, tuple(reversed(canonical))]
    for shift in range(1, len(canonical)):
        candidates.append(canonical[shift:] + canonical[:shift])
    for i in range(len(canonical) - 1):
        swapped = list(canonical)
        swapped[i], swapped[i + 1] = swapped[i + 1], swapped[i]
        candidates.append(tuple(swapped))
    unique = []
    for item in candidates:
        if item not in unique:
            unique.append(item)
        if len(unique) >= max_orders:
            break
    return unique
