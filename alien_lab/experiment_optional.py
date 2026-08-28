from __future__ import annotations

from dataclasses import replace
from typing import Any

from .compiler import compile_workspace, fuse_workspace, recursive_fuse_workspace
from .design import PRIMITIVES, representative_orders, subset_id
from .serialize import render_packet
from .taskgen import generate_taskset


class ExperimentOptionalMixin:
    def _build_optional_jobs(self, public, analysis: dict[str, Any]) -> list[dict[str, Any]]:
        def fs(name: str) -> frozenset[str]:
            return frozenset(analysis[name])

        empty = frozenset()
        full = frozenset(PRIMITIVES)
        candidates = [
            fs("minimal_subset"),
            fs("best_subset"),
            fs("efficiency_subset"),
            fs("strongest_positive_pair"),
            full,
        ]
        unique: list[frozenset[str]] = []
        for s in candidates:
            if s not in unique:
                unique.append(s)

        jobs: list[dict[str, Any]] = []
        # Held-out single-task transfer is the anti-batching and generalization gate.
        conditions: list[tuple[str, frozenset[str]]] = [("RAW", empty), ("STRUCTURED", empty)]
        conditions.extend(("COMPOUND", s) for s in unique if s)
        for task in public.transfer:
            for rep, subset in conditions:
                order = tuple(p for p in PRIMITIVES if p in subset)
                jobs.append({"kind": "single", "kwargs": dict(
                    tasks=[task], phase="transfer", representation=rep, subset=subset, order=order,
                    budget=self.config.transfer_budget, tag=f"transfer:{task.task_id}:{subset_id(subset)}:{rep}",
                    taskset_seed=self.config.seed,
                )})

        winner = fs("minimal_subset") or fs("best_subset") or full
        for task in public.challenge:
            compute_conditions = [
                ("RAW", empty, self.config.large_budget, "raw-large"),
                ("STRUCTURED", empty, self.config.medium_budget, "structured-medium"),
                ("COMPOUND", winner, self.config.small_budget, "winner-small"),
                ("COMPOUND", full, self.config.small_budget, "full-small"),
            ]
            seen = set()
            for rep, subset, budget, label in compute_conditions:
                key = (rep, subset, budget)
                if key in seen:
                    continue
                seen.add(key)
                jobs.append({"kind": "single", "kwargs": dict(
                    tasks=[task], phase="compute_substitution", representation=rep, subset=subset,
                    order=tuple(p for p in PRIMITIVES if p in subset), budget=budget,
                    tag=f"compute:{task.task_id}:{label}", taskset_seed=self.config.seed,
                )})

        # Order effects: top three pair interactions, both permutations, two held-out tasks.
        top_pairs = [frozenset(item["subset"]) for item in analysis["pair_effects"][:3]]
        for pair in top_pairs:
            if len(pair) != 2:
                continue
            p = tuple(sorted(pair))
            for order in (p, tuple(reversed(p))):
                for task in public.transfer[:2]:
                    jobs.append({"kind": "single", "kwargs": dict(
                        tasks=[task], phase="order_effect", representation="COMPOUND", subset=pair,
                        order=order, budget=self.config.transfer_budget,
                        tag=f"order:{'+'.join(order)}:{task.task_id}", taskset_seed=self.config.seed,
                    )})

        # Higher-order order search. If the winner is too small to expose order
        # structure, use the full stack and sample representative permutations.
        order_subset = winner if len(winner) >= 3 else full
        for order in representative_orders(order_subset, max_orders=12):
            for task in public.transfer[:2]:
                jobs.append({"kind": "single", "kwargs": dict(
                    tasks=[task], phase="higher_order_order", representation="COMPOUND", subset=order_subset,
                    order=order, budget=self.config.transfer_budget,
                    tag=f"higher-order:{'+'.join(order)}:{task.task_id}", taskset_seed=self.config.seed,
                )})

        # First-order fusion: test whether a compound can become a new relation
        # rather than merely a flat union of its inputs.
        fusion_subsets = []
        for candidate in (winner, full):
            if candidate and candidate not in fusion_subsets:
                fusion_subsets.append(candidate)
        for subset in fusion_subsets:
            for task in public.transfer[:3]:
                jobs.append({"kind": "single", "kwargs": dict(
                    tasks=[task], phase="fusion_probe", representation="FUSED_COMPOUND", subset=subset,
                    order=tuple(p for p in PRIMITIVES if p in subset), budget=self.config.transfer_budget,
                    tag=f"fusion1:{subset_id(subset)}:{task.task_id}", taskset_seed=self.config.seed,
                    fusion_depth=1,
                )})

        # Compound-of-compound probe. Union the two strongest pair interactions;
        # if they do not span >=3 primitives, use the full stack. Compare flat,
        # first-order fusion, and recursive relational closure.
        positive_pairs = [frozenset(item["subset"]) for item in analysis["pair_effects"][:2]]
        recursive_subset = frozenset().union(*positive_pairs) if positive_pairs else full
        if len(recursive_subset) < 3:
            recursive_subset = full
        for task in public.challenge:
            for rep, depth, label in [
                ("COMPOUND", 0, "flat"),
                ("FUSED_COMPOUND", 1, "fusion1"),
                ("RECURSIVE_COMPOUND", 2, "fusion2"),
            ]:
                jobs.append({"kind": "single", "kwargs": dict(
                    tasks=[task], phase="recursive_fusion", representation=rep, subset=recursive_subset,
                    order=tuple(p for p in PRIMITIVES if p in recursive_subset), budget=self.config.transfer_budget,
                    tag=f"recursive:{label}:{task.task_id}", taskset_seed=self.config.seed,
                    fusion_depth=depth,
                )})

        # Explicit batching-distortion control for the winner: individual transfer
        # results already exist above; this packet provides the paired comparison.
        jobs.append({"kind": "packet", "kwargs": dict(
            tasks=list(public.transfer[:3]), phase="batching_control", representation="COMPOUND",
            subset=winner, order=tuple(p for p in PRIMITIVES if p in winner), budget=self.config.transfer_budget,
            tag="winner-heldout-batch", taskset_seed=self.config.seed,
        )})

        negative = fs("strongest_negative_pair")
        if negative:
            for task in public.transfer[:2]:
                jobs.append({"kind": "single", "kwargs": dict(
                    tasks=[task], phase="antagonism_control", representation="COMPOUND", subset=negative,
                    order=tuple(p for p in PRIMITIVES if p in negative), budget=self.config.transfer_budget,
                    tag=f"negative-pair:{task.task_id}", taskset_seed=self.config.seed,
                )})

        # Full capability-vs-neural-budget response curve on a challenge task.
        curve_task = public.challenge[0]
        curve_conditions = [("RAW", empty), ("STRUCTURED", empty), ("COMPOUND", winner), ("COMPOUND", full)]
        seen_curve = set()
        for budget in (64, 96, 128, 192, 256, 400):
            for rep, subset in curve_conditions:
                key = (budget, rep, subset)
                if key in seen_curve:
                    continue
                seen_curve.add(key)
                jobs.append({"kind": "single", "kwargs": dict(
                    tasks=[curve_task], phase="budget_curve", representation=rep, subset=subset,
                    order=tuple(p for p in PRIMITIVES if p in subset), budget=budget,
                    tag=f"budget-curve:{budget}:{rep}:{subset_id(subset)}", taskset_seed=self.config.seed,
                )})

        # Presentation perturbation: fresh seed reshuffles evidence and answer order
        # without changing the underlying causal truth.
        perturbed, perturbed_sealed = generate_taskset(self.config.seed + 1)
        # The correct actions are unchanged but answer letters are seed-dependent;
        # each perturbation job carries its own evaluator map.
        for rep, subset, label in [("RAW", empty, "raw"), ("STRUCTURED", empty, "structured"), ("COMPOUND", winner, "winner")]:
            jobs.append({"kind": "packet", "kwargs": dict(
                tasks=list(perturbed.discovery), phase="presentation_perturbation", representation=rep,
                subset=subset, order=tuple(p for p in PRIMITIVES if p in subset), budget=self.config.discovery_budget,
                tag=f"perturbation:{label}", taskset_seed=self.config.seed + 1,
                evaluator_override=perturbed_sealed.answers,
            )})
        # Two additional answer/evidence-order replications. They are last in
        # priority so they consume time only after richer causal probes.
        for offset in (2, 3):
            variant, variant_sealed = generate_taskset(self.config.seed + offset)
            for rep, subset, label in [
                ("RAW", empty, "raw"),
                ("STRUCTURED", empty, "structured"),
                ("COMPOUND", winner, "winner"),
                ("COMPOUND", full, "full"),
            ]:
                jobs.append({"kind": "packet", "kwargs": dict(
                    tasks=list(variant.discovery), phase="robustness_replication", representation=rep,
                    subset=subset, order=tuple(p for p in PRIMITIVES if p in subset),
                    budget=self.config.discovery_budget, tag=f"replication:{offset}:{label}",
                    taskset_seed=self.config.seed + offset, evaluator_override=variant_sealed.answers,
                )})

        return jobs

