from __future__ import annotations

import json

from .types import Task, Workspace


def _choices(task: Task) -> str:
    return "\n".join(f"{k}: {v}" for k, v in task.choices.items())


def render_raw(task: Task) -> str:
    source_lines = [s.raw for s in task.sources]
    edge_lines = [e.raw for e in task.edges]
    return (
        "RAW PROJECT EVIDENCE\n"
        + "\n".join(source_lines + edge_lines)
        + "\n\nQUESTION\n"
        + task.question
        + "\n\nCHOICES\n"
        + _choices(task)
        + "\n\nReturn only A, B, C, or D."
    )


def render_structured(task: Task) -> str:
    lines = ["STRUCTURED PROJECT EVIDENCE", "SOURCES"]
    for s in task.sources:
        lines.append(
            f"id={s.record_id} scope={s.scope} kind={s.kind} authority={s.authority} "
            f"revision={s.revision} key={s.key} value={s.value}"
        )
    lines.append("EDGES")
    for e in task.edges:
        lines.append(
            f"id={e.edge_id} source={e.source} target={e.target} active={str(e.active).lower()} scope={e.scope}"
        )
    lines.extend(["QUESTION", task.question, "CHOICES", _choices(task), "Return only A, B, C, or D."])
    return "\n".join(lines)


def render_workspace(task: Task, ws: Workspace) -> str:
    lines = ["COMPILED COGNITIVE WORKSPACE"]
    if ws.current_state:
        lines.append("CURRENT STATE")
        for key, value in sorted(ws.current_state.items()):
            lines.append(f"{key}={value}")
    if ws.active_path:
        lines.extend(["ACTIVE PATH", " -> ".join(ws.active_path)])
    if ws.contradictions:
        lines.append("UNRESOLVED CONTRADICTIONS")
        for item in ws.contradictions:
            lines.append(json.dumps(item, sort_keys=True))
    if ws.procedure:
        lines.append("PROCEDURE")
        lines.extend(f"- {rule}" for rule in ws.procedure)
    if ws.memory_deltas:
        lines.append("MEMORY DELTAS")
        for item in ws.memory_deltas:
            lines.append(json.dumps(item, sort_keys=True))
    if ws.fused_relations:
        lines.append("FUSED RELATIONS")
        for item in ws.fused_relations:
            lines.append(json.dumps(item, sort_keys=True))

    visible_sources = {s.record_id: s for s in task.sources}
    visible_edges = {e.edge_id: e for e in task.edges}
    lines.append("VISIBLE EVIDENCE")
    for sid in ws.evidence_ids:
        src = visible_sources[sid]
        lines.append(
            f"source id={src.record_id} scope={src.scope} authority={src.authority} "
            f"revision={src.revision} key={src.key} value={src.value}"
        )
    for eid in ws.edge_ids:
        edge = visible_edges[eid]
        lines.append(
            f"edge id={edge.edge_id} source={edge.source} target={edge.target} active={str(edge.active).lower()} scope={edge.scope}"
        )

    lines.extend(["QUESTION", task.question, "CHOICES", _choices(task), "Return only A, B, C, or D."])
    return "\n".join(lines)


def render_packet(tasks, *, mode: str, workspaces=None) -> str:
    if mode not in {"raw", "structured", "workspace"}:
        raise ValueError("mode must be raw, structured, or workspace")
    if mode == "workspace" and (workspaces is None or len(workspaces) != len(tasks)):
        raise ValueError("workspace mode requires one workspace per task")
    parts = [
        "INDEPENDENT DECISION PACKET",
        "Solve every task independently. Facts from one task never apply to another task.",
    ]
    for i, task in enumerate(tasks, 1):
        if mode == "raw":
            body = render_raw(task)
        elif mode == "structured":
            body = render_structured(task)
        else:
            body = render_workspace(task, workspaces[i - 1])
        body = body.rsplit("Return only A, B, C, or D.", 1)[0].rstrip()
        parts.extend([f"TASK {i}", body])
    pattern = " ".join(f"{i}:<LETTER>" for i in range(1, len(tasks) + 1))
    parts.extend([
        "PACKET OUTPUT CONTRACT",
        f"Return exactly one letter per task in this format: {pattern}",
        "No explanation in the final response.",
    ])
    return "\n\n".join(parts)
