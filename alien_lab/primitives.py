from __future__ import annotations

from collections import defaultdict

from .types import CompilerInput, Derivation, Workspace


def _visible_sources(view: CompilerInput, ws: Workspace):
    visible = set(ws.evidence_ids)
    return [s for s in view.sources if s.record_id in visible]


def _visible_edges(view: CompilerInput, ws: Workspace):
    visible = set(ws.edge_ids)
    return [e for e in view.edges if e.edge_id in visible]


def apply_state(view: CompilerInput, ws: Workspace) -> None:
    groups = defaultdict(list)
    for src in _visible_sources(view, ws):
        groups[src.key].append(src)
    for key, records in groups.items():
        best_rank = max((r.authority, r.revision) for r in records)
        top = [r for r in records if (r.authority, r.revision) == best_rank]
        values = {r.value for r in top}
        if len(values) == 1:
            value = next(iter(values))
            ws.current_state[key] = value
            ws.derivations.append(Derivation(
                "state", "current_state", {key: value},
                [r.record_id for r in top],
                "select unique value at maximum (authority, revision); never break an equal-rank disagreement",
            ))


def apply_path(view: CompilerInput, ws: Workspace) -> None:
    edges = _visible_edges(view, ws)
    path = [view.entry]
    current = view.entry
    used: list[str] = []
    for _ in range(max(1, len(edges) + 1)):
        active = [e for e in edges if e.source == current and e.active]
        if len(active) != 1:
            break
        edge = active[0]
        used.append(edge.edge_id)
        current = edge.target
        if current in path:
            break
        path.append(current)
    ws.active_path = path
    ws.derivations.append(Derivation(
        "path", "active_path", list(path), used,
        "follow only uniquely active outgoing dependency edges from the declared entry",
    ))


def apply_uncertainty(view: CompilerInput, ws: Workspace) -> None:
    groups = defaultdict(list)
    for src in _visible_sources(view, ws):
        groups[src.key].append(src)
    for key, records in groups.items():
        best_rank = max((r.authority, r.revision) for r in records)
        top = [r for r in records if (r.authority, r.revision) == best_rank]
        values = sorted({r.value for r in top})
        if len(values) > 1:
            item = {
                "key": key,
                "values": values,
                "authority": best_rank[0],
                "revision": best_rank[1],
                "sources": [r.record_id for r in top],
            }
            ws.contradictions.append(item)
            ws.derivations.append(Derivation(
                "uncertainty", "contradiction", item,
                [r.record_id for r in top],
                "preserve disagreement when equal highest-authority records at the same revision conflict",
            ))


def apply_relevance(view: CompilerInput, ws: Workspace) -> None:
    allowed_scopes = {view.target_scope}
    if ws.active_path:
        allowed_scopes.update(ws.active_path)
    keep_sources = []
    discarded = []
    for src in _visible_sources(view, ws):
        if src.scope in allowed_scopes:
            keep_sources.append(src.record_id)
        else:
            discarded.append(src.record_id)
    ws.evidence_ids = keep_sources
    ws.discarded_evidence.extend(x for x in discarded if x not in ws.discarded_evidence)
    # Keep graph edges that are in the target scope or touch an already-known active path.
    keep_edges = []
    for edge in _visible_edges(view, ws):
        if edge.scope == view.target_scope or edge.source in allowed_scopes or edge.target in allowed_scopes:
            keep_edges.append(edge.edge_id)
    ws.edge_ids = keep_edges
    ws.derivations.append(Derivation(
        "relevance", "evidence_filter",
        {"kept": list(keep_sources), "discarded": list(discarded), "allowed_scopes": sorted(allowed_scopes)},
        list(keep_sources) + list(discarded),
        "retain evidence in the task scope and, when already derived, scopes on the active path",
    ))


def apply_procedure(view: CompilerInput, ws: Workspace) -> None:
    ws.procedure = list(view.procedure_rules)
    ws.derivations.append(Derivation(
        "procedure", "procedure", list(ws.procedure),
        [],
        "compile declared answer-independent decision rules into a concise procedural block",
    ))


def apply_memory(view: CompilerInput, ws: Workspace) -> None:
    groups = defaultdict(list)
    for src in _visible_sources(view, ws):
        groups[src.key].append(src)
    for key, records in groups.items():
        by_authority = defaultdict(list)
        for rec in records:
            by_authority[rec.authority].append(rec)
        if not by_authority:
            continue
        authority = max(by_authority)
        revision_groups = defaultdict(list)
        for rec in by_authority[authority]:
            revision_groups[rec.revision].append(rec)
        resolved_history = []
        for revision in sorted(revision_groups):
            records_at_revision = revision_groups[revision]
            values = {r.value for r in records_at_revision}
            # A contradictory revision is uncertainty, not a historical state.
            if len(values) != 1:
                continue
            resolved_history.append((revision, next(iter(values)), records_at_revision))
        for old, new in zip(resolved_history, resolved_history[1:]):
            old_revision, old_value, old_records = old
            new_revision, new_value, new_records = new
            if old_value == new_value:
                continue
            input_ids = [r.record_id for r in old_records + new_records]
            delta = {
                "key": key,
                "from": old_value,
                "to": new_value,
                "from_revision": old_revision,
                "to_revision": new_revision,
                "authority": authority,
                "sources": input_ids,
            }
            ws.memory_deltas.append(delta)
            ws.derivations.append(Derivation(
                "memory", "state_transition", delta,
                input_ids,
                "within the highest available authority, preserve transitions only between uniquely resolved revisions; conflicting revisions are not history",
            ))


PASS_FUNCTIONS = {
    "state": apply_state,
    "path": apply_path,
    "uncertainty": apply_uncertainty,
    "relevance": apply_relevance,
    "procedure": apply_procedure,
    "memory": apply_memory,
}
