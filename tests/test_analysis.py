import unittest

from alien_lab.analysis import mobius_interactions, minimal_sufficient, pareto_frontier, shapley_values
from alien_lab.design import PRIMITIVES, all_subsets


class AnalysisTests(unittest.TestCase):
    def test_all_six_primitive_subsets_are_generated(self):
        subsets = all_subsets()
        self.assertEqual(len(subsets), 64)
        self.assertEqual(len(set(subsets)), 64)
        self.assertIn(frozenset(), subsets)
        self.assertIn(frozenset(PRIMITIVES), subsets)

    def test_mobius_recovers_additive_main_effects(self):
        weights = {name: i + 1 for i, name in enumerate(PRIMITIVES)}
        values = {s: sum(weights[x] for x in s) for s in all_subsets()}
        effects = mobius_interactions(values)
        for name, weight in weights.items():
            self.assertAlmostEqual(effects[frozenset({name})], weight)
        for subset, effect in effects.items():
            if len(subset) > 1:
                self.assertAlmostEqual(effect, 0.0)

    def test_mobius_recovers_pair_synergy(self):
        pair = frozenset({"state", "path"})
        values = {}
        for s in all_subsets():
            values[s] = len(s) + (5 if pair.issubset(s) else 0)
        effects = mobius_interactions(values)
        self.assertAlmostEqual(effects[pair], 5.0)

    def test_shapley_splits_pure_pair_synergy_equally(self):
        pair = {"state", "path"}
        values = {s: (10.0 if pair.issubset(s) else 0.0) for s in all_subsets()}
        phi = shapley_values(values)
        self.assertAlmostEqual(phi["state"], 5.0)
        self.assertAlmostEqual(phi["path"], 5.0)
        for name in set(PRIMITIVES) - pair:
            self.assertAlmostEqual(phi[name], 0.0)

    def test_pareto_frontier_removes_dominated_rows(self):
        rows = [
            {"id": "a", "accuracy": 1.0, "eval_tokens": 100, "wall_ms": 1000, "compiler_ms": 2},
            {"id": "b", "accuracy": 1.0, "eval_tokens": 120, "wall_ms": 1100, "compiler_ms": 3},
            {"id": "c", "accuracy": 0.8, "eval_tokens": 50, "wall_ms": 500, "compiler_ms": 1},
        ]
        ids = {r["id"] for r in pareto_frontier(rows)}
        self.assertEqual(ids, {"a", "c"})

    def test_minimal_sufficient_prefers_smallest_equal_capability_stack(self):
        rows = [
            {"id": "full", "accuracy": 1.0, "primitives": list(PRIMITIVES), "eval_tokens": 100},
            {"id": "pair", "accuracy": 1.0, "primitives": ["state", "path"], "eval_tokens": 110},
            {"id": "single", "accuracy": 0.75, "primitives": ["state"], "eval_tokens": 50},
        ]
        result = minimal_sufficient(rows)
        self.assertEqual([r["id"] for r in result], ["pair"])


if __name__ == "__main__":
    unittest.main()
