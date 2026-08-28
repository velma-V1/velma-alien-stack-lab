import unittest

from alien_lab.compiler import compile_workspace
from alien_lab.design import PRIMITIVES
from alien_lab.order_effects import CANONICAL_ORDER, CANDIDATE_ORDER
from alien_lab.capability_frontier import (
    FRONTIER_LEVELS,
    FRONTIER_REPLICATION_OFFSETS,
    build_frontier_tasks,
    deterministic_permutation_scan,
    score_workspace,
)


class CapabilityFrontierTests(unittest.TestCase):
    def test_frontier_levels_and_replications_are_preregistered(self):
        self.assertEqual(FRONTIER_LEVELS, (1, 2, 3, 4, 5))
        self.assertEqual(FRONTIER_REPLICATION_OFFSETS, (0, 1, 2, 3))

    def test_each_level_has_six_distinct_frontier_families(self):
        expected_families = {
            "frontier_path_state",
            "frontier_scope_conflict",
            "frontier_history",
            "frontier_multi_key",
            "frontier_path_scope",
            "frontier_compound",
        }
        for level in FRONTIER_LEVELS:
            tasks, sealed, expected = build_frontier_tasks(20260828, level)
            self.assertEqual(len(tasks), 6)
            self.assertEqual({task.family for task in tasks}, expected_families)
            self.assertEqual(set(sealed), {task.task_id for task in tasks})
            self.assertEqual(set(expected), {task.task_id for task in tasks})

    def test_difficulty_monotonically_increases_evidence_and_path_depth(self):
        previous_sources = 0
        previous_edges = 0
        for level in FRONTIER_LEVELS:
            tasks, _, _ = build_frontier_tasks(20260828, level)
            source_count = sum(len(task.sources) for task in tasks)
            edge_count = sum(len(task.edges) for task in tasks)
            self.assertGreater(source_count, previous_sources)
            self.assertGreater(edge_count, previous_edges)
            previous_sources = source_count
            previous_edges = edge_count

    def test_same_seed_is_stable_and_new_seed_reshuffles_packet(self):
        first, first_sealed, first_expected = build_frontier_tasks(20260828, 3)
        again, again_sealed, again_expected = build_frontier_tasks(20260828, 3)
        other, other_sealed, other_expected = build_frontier_tasks(20260829, 3)
        self.assertEqual([t.to_dict() for t in first], [t.to_dict() for t in again])
        self.assertEqual(first_sealed, again_sealed)
        self.assertEqual(first_expected, again_expected)
        self.assertNotEqual([t.to_dict() for t in first], [t.to_dict() for t in other])
        self.assertNotEqual(first_sealed, other_sealed)
        self.assertEqual(first_expected, other_expected)

    def test_candidate_compiler_is_more_correct_than_canonical_at_hardest_level(self):
        tasks, _, expected = build_frontier_tasks(20260828, 5)
        full = tuple(PRIMITIVES)
        candidate_total = 0
        canonical_total = 0
        for task in tasks:
            candidate = compile_workspace(task.compiler_view(), full, order=CANDIDATE_ORDER)
            canonical = compile_workspace(task.compiler_view(), full, order=CANONICAL_ORDER)
            candidate_total += int(score_workspace(candidate, expected[task.task_id])["overall"])
            canonical_total += int(score_workspace(canonical, expected[task.task_id])["overall"])
        self.assertGreater(candidate_total, canonical_total)

    def test_deterministic_scan_covers_all_720_full_stack_orders(self):
        tasks, _, expected = build_frontier_tasks(20260828, 5)
        report = deterministic_permutation_scan(tasks, expected)
        self.assertEqual(report["permutation_count"], 720)
        self.assertEqual(len(report["rows"]), 720)
        self.assertEqual(report["rows"][0]["task_count"], 6)

    def test_candidate_deterministic_score_beats_canonical_in_full_scan(self):
        tasks, _, expected = build_frontier_tasks(20260828, 5)
        report = deterministic_permutation_scan(tasks, expected)
        by_order = {tuple(row["order"]): row for row in report["rows"]}
        self.assertGreater(
            by_order[CANDIDATE_ORDER]["overall_accuracy"],
            by_order[CANONICAL_ORDER]["overall_accuracy"],
        )


if __name__ == "__main__":
    unittest.main()
