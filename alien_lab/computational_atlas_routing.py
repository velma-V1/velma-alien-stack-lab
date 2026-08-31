from __future__ import annotations

import json
from typing import Any

from .computational_atlas_semantics import CAPABILITY_BY_INTENT
from .computational_atlas_surfaces import UnboundTaskIR


REAL_TOOL_CATALOG: tuple[dict[str, Any], ...] = (
    {"name": "route_path", "description": "Find exact paths and reachability in explicit link/state graphs.", "capability": "G"},
    {"name": "derive_rules", "description": "Evaluate explicit facts and implication rules to determine entailed conclusions.", "capability": "L"},
    {"name": "select_under_limits", "description": "Choose the highest-value feasible set subject to explicit limits and costs.", "capability": "C"},
    {"name": "plan_state_goal", "description": "Find an executable sequence of allowed state transitions from start to goal.", "capability": "P"},
    {"name": "execute_transform", "description": "Execute a deterministic sequence of program-like value transformations.", "capability": "X"},
    {"name": "calculate_numeric", "description": "Perform exact numerical aggregation and mathematical calculation.", "capability": "M"},
    {"name": "join_records", "description": "Join structured records by keys and compute requested aggregates.", "capability": "D"},
    {"name": "rank_evidence", "description": "Rank evidence records by query match and authority and return the requested top results.", "capability": "R"},
)

DECOY_TOOL_CATALOG: tuple[dict[str, Any], ...] = (
    {"name": "sequence_advisor", "description": "Suggest a plausible order for activities without computing exact graph reachability."},
    {"name": "policy_summarizer", "description": "Summarize rules in prose without proving entailment."},
    {"name": "budget_explainer", "description": "Explain budget tradeoffs without solving an optimization problem."},
    {"name": "goal_brainstormer", "description": "Brainstorm possible plans without exact state-space search."},
    {"name": "code_reviewer", "description": "Describe program steps without executing them."},
    {"name": "math_explainer", "description": "Explain mathematical concepts without exact calculation."},
    {"name": "table_summarizer", "description": "Summarize tables without key-based relational joins."},
    {"name": "search_suggester", "description": "Suggest evidence sources without ranking the supplied records."},
    {"name": "workflow_narrator", "description": "Narrate workflow dependencies in natural language."},
    {"name": "constraint_checker", "description": "Check one proposed choice against stated limits but does not search alternatives."},
    {"name": "rule_editor", "description": "Rewrite rules for readability without deriving conclusions."},
    {"name": "route_estimator", "description": "Estimate route quality without exact path computation."},
    {"name": "script_formatter", "description": "Format program text without execution."},
    {"name": "statistical_commentator", "description": "Comment on numbers without performing requested aggregation."},
    {"name": "record_cleaner", "description": "Normalize field names without joining records."},
    {"name": "document_locator", "description": "Locate potentially related text without ranking supplied evidence."},
    {"name": "timeline_writer", "description": "Write a timeline from supplied events without exact state planning."},
    {"name": "decision_explainer", "description": "Explain an already chosen decision without optimization."},
    {"name": "logic_translator", "description": "Translate rule wording without proving the query."},
    {"name": "simulation_narrator", "description": "Describe a hypothetical simulation without numerical execution."},
    {"name": "schema_inspector", "description": "Inspect record schemas without calculating joins."},
    {"name": "evidence_summarizer", "description": "Summarize evidence content without relevance/authority ranking."},
    {"name": "path_visualizer", "description": "Draw already known links without finding a path."},
    {"name": "task_classifier", "description": "Classify tasks into broad categories without solving them."},
)


def _public(tool: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in tool.items() if key != "capability"}


def real_tool_catalog_bytes(condition: str | None = None) -> bytes:
    return json.dumps([_public(tool) for tool in REAL_TOOL_CATALOG], sort_keys=True, separators=(",", ":")).encode("utf-8")


def catalog_for_condition(condition: str) -> tuple[dict[str, Any], ...]:
    if condition == "CATALOG_8":
        return tuple(_public(tool) for tool in REAL_TOOL_CATALOG)
    if condition == "CATALOG_16":
        return tuple(_public(tool) for tool in REAL_TOOL_CATALOG) + DECOY_TOOL_CATALOG[:8]
    if condition == "CATALOG_32":
        return tuple(_public(tool) for tool in REAL_TOOL_CATALOG) + DECOY_TOOL_CATALOG
    raise ValueError(f"unknown catalog condition: {condition}")


def oracle_route(ir: UnboundTaskIR) -> tuple[str, ...]:
    routed: list[str] = []
    for operation in ir.operations:
        capability = CAPABILITY_BY_INTENT.get(operation.intent)
        if capability is None:
            return ()
        routed.append(capability)
    return tuple(routed)


def rule_route(ir: UnboundTaskIR, catalog: tuple[dict[str, Any], ...]) -> tuple[str, ...]:
    available_names = {tool["name"] for tool in catalog}
    name_by_capability = {tool["capability"]: tool["name"] for tool in REAL_TOOL_CATALOG}
    selected: list[str] = []
    for capability in oracle_route(ir):
        name = name_by_capability[capability]
        if name not in available_names:
            return ()
        selected.append(name)
    return tuple(selected)
