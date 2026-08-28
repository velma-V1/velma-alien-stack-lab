from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .analysis import minimal_sufficient as find_minimal_sufficient, mobius_interactions, pareto_frontier, shapley_values
from .design import PRIMITIVES, all_subsets, subset_id
from .report import build_compound_registry, render_markdown_report


class ExperimentAnalysisMixin:
    def _analyze_discovery(self) -> dict[str, Any]:
        groups: dict[frozenset[str], list[dict[str, Any]]] = {}
        for obs in self.observations:
            if obs["phase"] != "discovery" or obs["representation"] == "RAW" or obs["status"] != "OK":
                continue
            subset = frozenset(obs["primitives"])
            groups.setdefault(subset, []).append(obs)
        values: dict[frozenset[str], float] = {}
        rows = []
        for subset in all_subsets():
            items = groups.get(subset, [])
            accuracy = sum(1 for x in items if x["verified_success"]) / len(items) if items else 0.0
            values[subset] = accuracy
            run_ids = sorted({x["run_id"] for x in items})
            runs = [r for r in self.records if r.run_id in run_ids]
            avg_tokens = sum(r.eval_tokens for r in runs) / len(runs) if runs else float("inf")
            avg_wall = sum(r.wall_ms for r in runs) / len(runs) if runs else float("inf")
            avg_compiler = sum(r.compiler_ms for r in runs) / len(runs) if runs else float("inf")
            rows.append({
                "subset": subset,
                "subset_id": subset_id(subset),
                "accuracy": accuracy,
                "avg_eval_tokens": avg_tokens,
                "avg_wall_ms": avg_wall,
                "avg_compiler_ms": avg_compiler,
                "size": len(subset),
            })

        best_accuracy = max(r["accuracy"] for r in rows)
        capable = sorted(rows, key=lambda r: (-r["accuracy"], r["size"], r["avg_eval_tokens"], r["subset_id"]))
        best = capable[0]["subset"]
        minimal = min((r for r in rows if r["accuracy"] == best_accuracy), key=lambda r: (r["size"], r["avg_eval_tokens"], r["subset_id"]))["subset"]
        near_best = [r for r in rows if r["accuracy"] >= best_accuracy - (1 / max(1, len({o['task_id'] for o in self.observations if o['phase'] == 'discovery'})))]
        efficiency = min(near_best, key=lambda r: (r["avg_eval_tokens"], r["size"], -r["accuracy"], r["subset_id"]))["subset"]
        effects = mobius_interactions(values)
        shapley = shapley_values(values)
        average_main_effects = {}
        leave_one_out_full = {}
        leave_one_in_single = {}
        full_set = frozenset(PRIMITIVES)
        for primitive in PRIMITIVES:
            deltas = []
            for subset in all_subsets():
                if primitive in subset:
                    continue
                deltas.append(values[subset | {primitive}] - values[subset])
            average_main_effects[primitive] = sum(deltas) / len(deltas) if deltas else 0.0
            leave_one_out_full[primitive] = values[full_set] - values[full_set - {primitive}]
            leave_one_in_single[primitive] = values[frozenset({primitive})] - values[frozenset()]

        metric_value_maps = {
            "accuracy": values,
            "eval_tokens": {row["subset"]: float(row["avg_eval_tokens"]) for row in rows},
            "wall_ms": {row["subset"]: float(row["avg_wall_ms"]) for row in rows},
            "compiler_ms": {row["subset"]: float(row["avg_compiler_ms"]) for row in rows},
        }
        metric_causal_analysis = {}
        for metric_name, metric_values in metric_value_maps.items():
            metric_effects = mobius_interactions(metric_values)
            metric_causal_analysis[metric_name] = {
                "shapley_values": shapley_values(metric_values),
                "mobius_interactions": [
                    {"subset": sorted(subset), "effect": effect}
                    for subset, effect in sorted(metric_effects.items(), key=lambda x: (len(x[0]), tuple(sorted(x[0]))))
                ],
            }

        per_task_causal_analysis = {}
        discovery_task_ids = sorted({
            o["task_id"] for o in self.observations
            if o["phase"] == "discovery" and o["representation"] != "RAW" and o["status"] == "OK"
        })
        for task_id in discovery_task_ids:
            task_items = [
                o for o in self.observations
                if o["phase"] == "discovery" and o["representation"] != "RAW"
                and o["status"] == "OK" and o["task_id"] == task_id
            ]
            task_values = {frozenset(o["primitives"]): float(bool(o["verified_success"])) for o in task_items}
            if len(task_values) != len(all_subsets()):
                continue
            task_effects = mobius_interactions(task_values)
            per_task_causal_analysis[task_id] = {
                "task_family": task_items[0]["task_family"],
                "shapley_values": shapley_values(task_values),
                "mobius_interactions": [
                    {"subset": sorted(subset), "effect": effect}
                    for subset, effect in sorted(task_effects.items(), key=lambda x: (len(x[0]), tuple(sorted(x[0]))))
                ],
            }

        pareto_rows = pareto_frontier([
            {
                "id": row["subset_id"],
                "primitives": sorted(row["subset"]),
                "accuracy": row["accuracy"],
                "eval_tokens": row["avg_eval_tokens"],
                "wall_ms": row["avg_wall_ms"],
                "compiler_ms": row["avg_compiler_ms"],
            }
            for row in rows
        ])
        minimal_rows = find_minimal_sufficient([
            {
                "id": row["subset_id"],
                "primitives": sorted(row["subset"]),
                "accuracy": row["accuracy"],
                "eval_tokens": row["avg_eval_tokens"],
            }
            for row in rows
        ])
        pairs = [(s, e) for s, e in effects.items() if len(s) == 2]
        positive_pairs = sorted(pairs, key=lambda x: (-x[1], tuple(sorted(x[0]))))
        negative_pairs = sorted(pairs, key=lambda x: (x[1], tuple(sorted(x[0]))))
        strongest_positive = positive_pairs[0][0] if positive_pairs else frozenset()
        strongest_negative = negative_pairs[0][0] if negative_pairs else frozenset()
        return {
            "best_accuracy": best_accuracy,
            "best_subset": sorted(best),
            "minimal_subset": sorted(minimal),
            "efficiency_subset": sorted(efficiency),
            "full_subset": list(PRIMITIVES),
            "strongest_positive_pair": sorted(strongest_positive),
            "strongest_positive_pair_effect": effects.get(strongest_positive, 0.0),
            "strongest_negative_pair": sorted(strongest_negative),
            "strongest_negative_pair_effect": effects.get(strongest_negative, 0.0),
            "pair_effects": [
                {"subset": sorted(s), "effect": e}
                for s, e in sorted(pairs, key=lambda x: (-x[1], tuple(sorted(x[0]))))
            ],
            "mobius_interactions": [
                {"subset": sorted(subset), "effect": effect}
                for subset, effect in sorted(effects.items(), key=lambda x: (len(x[0]), tuple(sorted(x[0]))))
            ],
            "shapley_values": shapley,
            "metric_causal_analysis": metric_causal_analysis,
            "per_task_causal_analysis": per_task_causal_analysis,
            "average_main_effects": average_main_effects,
            "leave_one_out_full": leave_one_out_full,
            "leave_one_in_single": leave_one_in_single,
            "pareto_frontier": pareto_rows,
            "minimal_sufficient_sets": minimal_rows,
            "subset_rows": [
                {**{k: v for k, v in row.items() if k != "subset"}, "primitives": sorted(row["subset"])}
                for row in rows
            ],
        }

    def _build_followup_analysis(self) -> dict[str, Any]:
        groups: dict[tuple, list[dict[str, Any]]] = {}
        for obs in self.observations:
            if obs["phase"] == "discovery":
                continue
            key = (
                obs["phase"],
                obs["representation"],
                obs["subset_id"],
                obs["reasoning_budget"],
                obs.get("fusion_depth", 0),
                tuple(obs.get("pass_order", [])),
                obs.get("batch_size", 1),
            )
            groups.setdefault(key, []).append(obs)

        aggregates = []
        for key, items in groups.items():
            phase, representation, subset_id, budget, fusion_depth, pass_order, batch_size = key
            scored = [x for x in items if x.get("verified_success") is not None]
            aggregates.append({
                "phase": phase,
                "representation": representation,
                "subset_id": subset_id,
                "primitives": items[0].get("primitives", []),
                "reasoning_budget": budget,
                "fusion_depth": fusion_depth,
                "pass_order": list(pass_order),
                "batch_size": batch_size,
                "n": len(items),
                "scored_n": len(scored),
                "accuracy": (sum(bool(x["verified_success"]) for x in scored) / len(scored)) if scored else None,
                "avg_generation_eval_tokens": (sum(x.get("generation_eval_tokens", 0) for x in items) / len(items)) if items else None,
                "avg_amortized_eval_tokens": (sum(x.get("amortized_eval_tokens", 0) for x in items) / len(items)) if items else None,
                "avg_generation_wall_ms": (sum(x.get("generation_wall_ms", 0) for x in items) / len(items)) if items else None,
                "avg_compiler_ms": (sum(x.get("compiler_ms", 0) for x in items) / len(items)) if items else None,
                "ceiling_hits": sum(1 for x in items if x.get("hit_ceiling")),
            })
        aggregates.sort(key=lambda x: (x["phase"], x["reasoning_budget"], x["representation"], x["subset_id"], tuple(x["pass_order"])))

        def phase_rows(*names: str) -> list[dict[str, Any]]:
            wanted = set(names)
            return [x for x in aggregates if x["phase"] in wanted]

        return {
            "phase_aggregates": aggregates,
            "transfer": phase_rows("transfer"),
            "compute_substitution": phase_rows("compute_substitution"),
            "order_effects": phase_rows("order_effect", "higher_order_order"),
            "fusion": phase_rows("fusion_probe", "recursive_fusion"),
            "batching": phase_rows("batching_control"),
            "antagonism": phase_rows("antagonism_control"),
            "presentation_perturbation": phase_rows("presentation_perturbation"),
            "budget_curve": phase_rows("budget_curve"),
            "robustness_replication": phase_rows("robustness_replication"),
        }

    def _write_derived_datasets(self, discovery_analysis: dict[str, Any] | None, followup: dict[str, Any]) -> None:
        # Counterfactual trajectories: same task, multiple model-facing treatments.
        groups: dict[tuple, list[dict[str, Any]]] = {}
        for obs in self.observations:
            key = (obs.get("taskset_seed"), obs["task_id"], obs["phase"])
            groups.setdefault(key, []).append(obs)
        counter_lines = []
        for (taskset_seed, task_id, phase), items in sorted(groups.items(), key=lambda x: x[0]):
            if len(items) < 2:
                continue
            counter_lines.append(json.dumps({
                "taskset_seed": taskset_seed,
                "task_id": task_id,
                "task_family": items[0].get("task_family"),
                "phase": phase,
                "arms": [
                    {
                        "run_id": x["run_id"],
                        "representation": x["representation"],
                        "subset_id": x["subset_id"],
                        "primitives": x.get("primitives", []),
                        "pass_order": x.get("pass_order", []),
                        "fusion_depth": x.get("fusion_depth", 0),
                        "reasoning_budget": x["reasoning_budget"],
                        "verified_success": x.get("verified_success"),
                        "generation_eval_tokens": x.get("generation_eval_tokens"),
                        "generation_wall_ms": x.get("generation_wall_ms"),
                        "compiler_ms": x.get("compiler_ms"),
                        "prompt_hash": x.get("prompt_hash"),
                    }
                    for x in items
                ],
            }, sort_keys=True))
        (self.output_dir / "counterfactuals.jsonl").write_text(
            ("\n".join(counter_lines) + ("\n" if counter_lines else "")), encoding="utf-8"
        )

        failures = []
        for obs in self.observations:
            if obs.get("verified_success") is not False:
                continue
            failures.append({
                "run_id": obs["run_id"],
                "task_id": obs["task_id"],
                "task_family": obs.get("task_family"),
                "phase": obs["phase"],
                "representation": obs["representation"],
                "subset_id": obs["subset_id"],
                "primitives": obs.get("primitives", []),
                "pass_order": obs.get("pass_order", []),
                "fusion_depth": obs.get("fusion_depth", 0),
                "reasoning_budget": obs["reasoning_budget"],
                "prompt_hash": obs.get("prompt_hash"),
                "labels": [],
                "audit_status": "UNCLASSIFIED",
            })
        (self.output_dir / "failures.jsonl").write_text(
            "".join(json.dumps(item, sort_keys=True) + "\n" for item in failures), encoding="utf-8"
        )

        (self.output_dir / "followup_analysis.json").write_text(
            json.dumps(followup, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        matrix_path = self.output_dir / "causal_matrix.csv"
        rows = (discovery_analysis or {}).get("subset_rows", [])
        with matrix_path.open("w", newline="", encoding="utf-8") as f:
            fields = ["subset_id", "primitives", "size", "accuracy", "avg_eval_tokens", "avg_wall_ms", "avg_compiler_ms"]
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    "subset_id": row["subset_id"],
                    "primitives": "+".join(row.get("primitives", [])),
                    "size": row["size"],
                    "accuracy": row["accuracy"],
                    "avg_eval_tokens": row["avg_eval_tokens"],
                    "avg_wall_ms": row["avg_wall_ms"],
                    "avg_compiler_ms": row.get("avg_compiler_ms"),
                })

    def _finish(self, incomplete_reason: str | None = None, discovery_analysis: dict[str, Any] | None = None) -> list[RunRecord]:
        time_aborts = sum(1 for r in self.records if r.status == "TIME_BUDGET_ABORT")
        scored_generations = sum(1 for r in self.records if r.status == "OK")
        scored_observations = sum(1 for o in self.observations if o["verified_success"] is not None)
        followup_analysis = self._build_followup_analysis()
        self.summary = {
            "experiment_id": self.config.experiment_id,
            "elapsed_seconds": self.clock() - self._started,
            "generation_count": len(self.records),
            "observation_count": len(self.observations),
            "total_prompt_tokens": sum(r.prompt_tokens for r in self.records),
            "total_eval_tokens": sum(r.eval_tokens for r in self.records),
            "total_compiler_ms": sum(r.compiler_ms for r in self.records),
            "total_derived_facts": sum(len(r.derived_facts) for r in self.records),
            "observations_per_generation": (len(self.observations) / len(self.records)) if self.records else 0.0,
            "scored_generations": scored_generations,
            "scored_observations": scored_observations,
            "time_budget_aborts": time_aborts,
            "incomplete_reason": incomplete_reason,
            "discovery_analysis": discovery_analysis,
            "followup_analysis": followup_analysis,
        }

        registry = {"compounds": []}
        if discovery_analysis:
            candidates = [
                {
                    "constituents": item["subset"],
                    "interaction": item["effect"],
                    "canonical_order": [p for p in PRIMITIVES if p in set(item["subset"])],
                }
                for item in discovery_analysis.get("mobius_interactions", [])
                if len(item.get("subset", [])) >= 2
            ]
            transfer_observations = [o for o in self.observations if o.get("phase") == "transfer"]
            registry = build_compound_registry(candidates, transfer_observations)
        self.summary["confirmed_compounds"] = sum(1 for x in registry["compounds"] if x.get("confirmed"))
        self._write_derived_datasets(discovery_analysis, followup_analysis)

        (self.output_dir / "summary.json").write_text(json.dumps(self.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (self.output_dir / "compound_registry.json").write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report = render_markdown_report(
            summary=self.summary,
            discovery_analysis=discovery_analysis or {},
            registry=registry,
            followup_analysis=followup_analysis,
        )
        (self.output_dir / "report.md").write_text(report, encoding="utf-8")
        return self.records

