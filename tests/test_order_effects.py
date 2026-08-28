import unittest

from alien_lab.order_effects import (
    CANDIDATE_ORDER,
    CANONICAL_ORDER,
    ControlledSeedClient,
    build_order_stress_tasks,
    order_catalog,
    semantic_workspace_signature,
)
from alien_lab.compiler import compile_workspace
from alien_lab.design import PRIMITIVES


class SeedStub:
    def __init__(self):
        self.calls = []
        self.base_url = "http://stub"

    def model_metadata(self, model, timeout_seconds=5.0):
        return {"name": model}

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return kwargs


class OrderEffectsTests(unittest.TestCase):
    def test_catalog_is_unique_and_holds_full_stack_constant(self):
        orders = order_catalog()
        self.assertGreaterEqual(len(orders), 8)
        self.assertEqual(len(orders), len(set(orders)))
        for order in orders:
            self.assertEqual(set(order), set(PRIMITIVES))
            self.assertEqual(len(order), len(PRIMITIVES))
        self.assertIn(CANONICAL_ORDER, orders)
        self.assertIn(CANDIDATE_ORDER, orders)

    def test_controlled_seed_client_overrides_runner_seed(self):
        inner = SeedStub()
        client = ControlledSeedClient(inner)
        client.seed_override = 4242
        result = client.generate(seed=999, prompt="x")
        self.assertEqual(result["seed"], 4242)
        self.assertEqual(inner.calls[-1]["seed"], 4242)

    def test_stress_set_targets_four_real_order_dependencies(self):
        tasks, sealed = build_order_stress_tasks(20260828)
        self.assertEqual(len(tasks), 4)
        self.assertEqual(set(sealed), {task.task_id for task in tasks})
        self.assertEqual(
            {task.family for task in tasks},
            {
                "order_path_relevance",
                "order_relevance_state",
                "order_relevance_uncertainty",
                "order_relevance_memory",
            },
        )

    def test_candidate_and_reverse_change_semantic_workspace(self):
        tasks, _ = build_order_stress_tasks(20260828)
        full = tuple(PRIMITIVES)
        changed = 0
        for task in tasks:
            candidate = compile_workspace(task.compiler_view(), full, order=CANDIDATE_ORDER)
            reverse = compile_workspace(task.compiler_view(), full, order=tuple(reversed(CANDIDATE_ORDER)))
            if semantic_workspace_signature(candidate) != semantic_workspace_signature(reverse):
                changed += 1
        self.assertGreaterEqual(changed, 3)

    def test_path_before_relevance_preserves_live_path_evidence(self):
        tasks, _ = build_order_stress_tasks(20260828)
        task = next(t for t in tasks if t.family == "order_path_relevance")
        full = tuple(PRIMITIVES)
        good = compile_workspace(task.compiler_view(), full, order=CANDIDATE_ORDER)
        bad_order = ("relevance", "path", "state", "uncertainty", "memory", "procedure")
        bad = compile_workspace(task.compiler_view(), full, order=bad_order)
        self.assertIn("live-policy", good.evidence_ids)
        self.assertNotIn("live-policy", bad.evidence_ids)

    def test_relevance_before_state_blocks_out_of_scope_authority_poisoning(self):
        tasks, _ = build_order_stress_tasks(20260828)
        task = next(t for t in tasks if t.family == "order_relevance_state")
        full = tuple(PRIMITIVES)
        good = compile_workspace(task.compiler_view(), full, order=CANDIDATE_ORDER)
        bad_order = ("state", "path", "relevance", "uncertainty", "memory", "procedure")
        bad = compile_workspace(task.compiler_view(), full, order=bad_order)
        self.assertEqual(good.current_state.get("mode"), "safe")
        self.assertEqual(bad.current_state.get("mode"), "turbo")

    def test_relevance_before_uncertainty_avoids_irrelevant_conflict(self):
        tasks, _ = build_order_stress_tasks(20260828)
        task = next(t for t in tasks if t.family == "order_relevance_uncertainty")
        full = tuple(PRIMITIVES)
        good = compile_workspace(task.compiler_view(), full, order=CANDIDATE_ORDER)
        bad_order = ("uncertainty", "path", "relevance", "state", "memory", "procedure")
        bad = compile_workspace(task.compiler_view(), full, order=bad_order)
        self.assertFalse(good.contradictions)
        self.assertTrue(bad.contradictions)

    def test_relevance_before_memory_prevents_wrong_scope_history(self):
        tasks, _ = build_order_stress_tasks(20260828)
        task = next(t for t in tasks if t.family == "order_relevance_memory")
        full = tuple(PRIMITIVES)
        good = compile_workspace(task.compiler_view(), full, order=CANDIDATE_ORDER)
        bad_order = ("memory", "path", "relevance", "state", "uncertainty", "procedure")
        bad = compile_workspace(task.compiler_view(), full, order=bad_order)
        self.assertTrue(any(x["from"] == "legacy" and x["to"] == "current" for x in good.memory_deltas))
        self.assertTrue(any(x["from"] == "shadow_old" and x["to"] == "shadow_new" for x in bad.memory_deltas))


if __name__ == "__main__":
    unittest.main()
