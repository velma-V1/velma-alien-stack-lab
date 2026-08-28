from __future__ import annotations

from statistics import mean
from typing import Any


def build_compound_registry(
    candidates: list[dict[str, Any]],
    transfer_observations: list[dict[str, Any]],
    *,
    min_transfer_observations: int = 2,
    min_transfer_accuracy: float = 0.75,
) -> dict[str, Any]:
    normalized = []
    for candidate in candidates:
        constituents = tuple(sorted(candidate["constituents"]))
        matches = [
            o for o in transfer_observations
            if tuple(sorted(o.get("primitives", []))) == constituents
            and o.get("verified_success") is not None
        ]
        accuracy = (
            sum(bool(o["verified_success"]) for o in matches) / len(matches)
            if matches else None
        )
        confirmed = (
            float(candidate.get("interaction", 0.0)) > 0
            and len(matches) >= min_transfer_observations
            and accuracy is not None
            and accuracy >= min_transfer_accuracy
        )
        normalized.append({
            "constituents": list(constituents),
            "canonical_order": list(candidate.get("canonical_order") or constituents),
            "discovery_interaction_strength": float(candidate.get("interaction", 0.0)),
            "transfer_score": accuracy,
            "transfer_observations": len(matches),
            "confirmed": confirmed,
            "task_families": sorted({o.get("task_family", "") for o in matches if o.get("task_family")}),
            "evidence_run_ids": sorted({o.get("run_id", "") for o in matches if o.get("run_id")}),
            "compute_profile": {
                "avg_generation_eval_tokens": mean([o.get("generation_eval_tokens", 0) for o in matches]) if matches else None,
                "avg_generation_wall_ms": mean([o.get("generation_wall_ms", 0) for o in matches]) if matches else None,
            },
            "constituent_metadata": candidate.get("constituent_metadata", {}),
        })

    # IDs are deterministic from canonical ordering of all candidate sets, so the
    # same confirmed compound keeps the same ID if input ordering changes.
    ordered = sorted(normalized, key=lambda x: (len(x["constituents"]), tuple(x["constituents"])))
    for i, item in enumerate(ordered, 1):
        item["compound_id"] = f"C{i:03d}"
    return {"compounds": ordered}


def render_markdown_report(
    *,
    summary: dict[str, Any],
    discovery_analysis: dict[str, Any],
    registry: dict[str, Any],
    followup_analysis: dict[str, Any] | None = None,
) -> str:
    confirmed = [x for x in registry.get("compounds", []) if x.get("confirmed")]
    lines = [
        "# Alien-Stack Experiment Report",
        "",
        "## Capability",
        f"- Best discovery accuracy: {discovery_analysis.get('best_accuracy')}",
        f"- Best subset: {discovery_analysis.get('best_subset')}",
        f"- Minimal sufficient subset: {discovery_analysis.get('minimal_subset')}",
        "",
        "## Compute",
        f"- Generations: {summary.get('generation_count')}",
        f"- Task observations: {summary.get('observation_count')}",
        f"- Time-budget aborts: {summary.get('time_budget_aborts')}",
        "",
        "## Causality",
        f"- Confirmed compounds: {len(confirmed)}",
        f"- Strongest positive pair: {discovery_analysis.get('strongest_positive_pair')}",
        f"- Strongest negative pair: {discovery_analysis.get('strongest_negative_pair')}",
        "",
        "## Generalization",
        "- Compound promotion requires held-out transfer evidence; discovery-only effects remain provisional.",
        "",
    ]
    followup = followup_analysis or {}
    if followup.get("transfer"):
        lines.extend(["## Held-out Transfer", ""])
        for item in followup["transfer"]:
            lines.append(
                f"- {item.get('subset_id', item.get('representation'))}: accuracy={item.get('accuracy')}"
            )
        lines.append("")
    if followup.get("fusion"):
        lines.extend(["## Fusion", ""])
        for item in followup["fusion"]:
            lines.append(
                f"- {item.get('phase')}: {item.get('subset_id')} depth={item.get('fusion_depth')} accuracy={item.get('accuracy')}"
            )
        lines.append("")
    if followup.get("budget_curve"):
        lines.extend(["## Budget Curve", ""])
        for item in followup["budget_curve"]:
            lines.append(
                f"- {item.get('representation')}@{item.get('reasoning_budget')}: accuracy={item.get('accuracy')}"
            )
        lines.append("")
    if confirmed:
        lines.extend(["## Confirmed Compound Registry", ""])
        for item in confirmed:
            lines.append(
                f"- **{item['compound_id']}**: {' + '.join(item['constituents'])}; "
                f"transfer={item['transfer_score']}; interaction={item['discovery_interaction_strength']}"
            )
    return "\n".join(lines).rstrip() + "\n"
