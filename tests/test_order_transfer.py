import unittest

from alien_lab.compiler import compile_workspace
from alien_lab.design import PRIMITIVES
from alien_lab.order_effects import CANONICAL_ORDER, CANDIDATE_ORDER, semantic_workspace_signature
from alien_lab.order_transfer import (
    HELDOUT_REPLICATION_OFFSETS,
    build_heldout_transfer_tasks,
    transfer_order_catalog,
)


class HeldoutOrderTransferTests(unittest.TestCase):
    def test_catalog_has_four_full_stack_controls(self):
        orders = transfer_order_catalog()
        self.assertEqual(len(orders), 4)
        self.assertEqual(len(set(orders)), 4)
        self.assertIn(CANONICAL_ORDER, orders)
        self.assertIn(CANDIDATE_ORDER, orders)
        for order in orders:
            self.assertEqual(set(order), set(PRIMITIVES))
            self.assertEqual(len(order), len(PRIMITIVES))

    def test_heldout_tasks_use_new_families_not_experiment_004_families(self):
        tasks, sealed = build_heldout_transfer_tasks(20260928)
        experiment_004_families = {
            "order_path_relevance",
            "order_relevance_state",
            "order_relevance_uncertainty",
            "order_relevance_memory",
        }
        self.assertEqual(len(tasks), 6)
        self.assertEqual(set(sealed), {task.task_id for task in tasks})
        self.assertFalse({task.family for task in tasks} & experiment_004_families)
        self.assertEqual(len({task.family for task in tasks}), 6)

    def test_generation_is_stable_for_same_seed_and_reshuffles_for_new_seed(self):
        first, first_sealed = build_heldout_transfer_tasks(20260928)
        again, again_sealed = build_heldout_transfer_tasks(20260928)
        other, other_sealed = build_heldout_transfer_tasks(20260929)
        self.assertEqual([task.to_dict() for task in first], [task.to_dict() for task in again])
        self.assertEqual(first_sealed, again_sealed)
        self.assertNotEqual([task.to_dict() for task in first], [task.to_dict() for task in other])
        self.assertNotEqual(first_sealed, other_sealed)

    def test_new_transfer_set_contains_real_semantic_order_sensitivity(self):
        tasks, _ = build_heldout_transfer_tasks(20260928)
        full = tuple(PRIMITIVES)
        changed = 0
        for task in tasks:
            canonical = compile_workspace(task.compiler_view(), full, order=CANONICAL_ORDER)
            candidate = compile_workspace(task.compiler_view(), full, order=CANDIDATE_ORDER)
            if semantic_workspace_signature(canonical) != semantic_workspace_signature(candidate):
                changed += 1
        self.assertGreaterEqual(changed, 4)

    def test_six_replications_are_pre_registered(self):
        self.assertEqual(HELDOUT_REPLICATION_OFFSETS, (0, 1, 2, 3, 4, 5))


if __name__ == "__main__":
    unittest.main()
