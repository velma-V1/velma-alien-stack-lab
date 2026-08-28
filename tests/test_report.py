import unittest

from alien_lab.report import build_compound_registry, render_markdown_report


class ReportTests(unittest.TestCase):
    def test_only_positive_transferred_compounds_are_confirmed(self):
        candidates = [
            {"constituents": ["state", "path"], "interaction": 0.25, "canonical_order": ["state", "path"]},
            {"constituents": ["state", "memory"], "interaction": -0.10, "canonical_order": ["state", "memory"]},
            {"constituents": ["path", "relevance"], "interaction": 0.20, "canonical_order": ["path", "relevance"]},
        ]
        transfer = [
            {"primitives": ["state", "path"], "verified_success": True, "run_id": "r1", "task_family": "a", "generation_eval_tokens": 100, "generation_wall_ms": 1000},
            {"primitives": ["state", "path"], "verified_success": True, "run_id": "r2", "task_family": "b", "generation_eval_tokens": 110, "generation_wall_ms": 1100},
            {"primitives": ["path", "relevance"], "verified_success": False, "run_id": "r3", "task_family": "a", "generation_eval_tokens": 90, "generation_wall_ms": 900},
            {"primitives": ["path", "relevance"], "verified_success": False, "run_id": "r4", "task_family": "b", "generation_eval_tokens": 95, "generation_wall_ms": 950},
        ]
        registry = build_compound_registry(candidates, transfer, min_transfer_observations=2, min_transfer_accuracy=0.75)
        by_set = {tuple(x["constituents"]): x for x in registry["compounds"]}
        self.assertTrue(by_set[("path", "state")]["confirmed"])
        self.assertFalse(by_set[("memory", "state")]["confirmed"])
        self.assertFalse(by_set[("path", "relevance")]["confirmed"])

    def test_confirmed_ids_are_stable_independent_of_candidate_input_order(self):
        a = {"constituents": ["state", "path"], "interaction": 0.2, "canonical_order": ["state", "path"]}
        b = {"constituents": ["memory", "procedure"], "interaction": 0.3, "canonical_order": ["memory", "procedure"]}
        transfer = []
        for subset, prefix in [(["state", "path"], "a"), (["memory", "procedure"], "b")]:
            for i in range(2):
                transfer.append({"primitives": subset, "verified_success": True, "run_id": f"{prefix}{i}", "task_family": "x", "generation_eval_tokens": 10, "generation_wall_ms": 20})
        r1 = build_compound_registry([a, b], transfer, min_transfer_observations=2)
        r2 = build_compound_registry([b, a], transfer, min_transfer_observations=2)
        map1 = {tuple(x["constituents"]): x["compound_id"] for x in r1["compounds"]}
        map2 = {tuple(x["constituents"]): x["compound_id"] for x in r2["compounds"]}
        self.assertEqual(map1, map2)

    def test_recursive_constituent_metadata_is_preserved(self):
        candidates = [{
            "constituents": ["state", "C007"],
            "interaction": 0.4,
            "canonical_order": ["state", "C007"],
            "constituent_metadata": {"C007": {"origin": ["path", "relevance"]}},
        }]
        transfer = [
            {"primitives": ["state", "C007"], "verified_success": True, "run_id": "r1", "task_family": "x", "generation_eval_tokens": 10, "generation_wall_ms": 20},
            {"primitives": ["state", "C007"], "verified_success": True, "run_id": "r2", "task_family": "y", "generation_eval_tokens": 11, "generation_wall_ms": 21},
        ]
        reg = build_compound_registry(candidates, transfer, min_transfer_observations=2)
        self.assertEqual(reg["compounds"][0]["constituent_metadata"]["C007"]["origin"], ["path", "relevance"])

    def test_markdown_report_contains_core_ledgers(self):
        report = render_markdown_report(
            summary={"generation_count": 100, "observation_count": 400, "time_budget_aborts": 0},
            discovery_analysis={"best_accuracy": 1.0, "best_subset": ["state", "path"], "minimal_subset": ["state"]},
            registry={"compounds": []},
        )
        for heading in ["Capability", "Compute", "Causality", "Generalization"]:
            self.assertIn(heading, report)

    def test_markdown_report_surfaces_followup_fusion_and_budget_data(self):
        report = render_markdown_report(
            summary={"generation_count": 10, "observation_count": 20, "time_budget_aborts": 0},
            discovery_analysis={"best_accuracy": 1.0, "best_subset": ["state", "path"], "minimal_subset": ["state"]},
            registry={"compounds": []},
            followup_analysis={
                "fusion": [{"phase": "recursive_fusion", "subset_id": "state+path", "fusion_depth": 2, "accuracy": 1.0}],
                "budget_curve": [{"phase": "budget_curve", "reasoning_budget": 96, "representation": "COMPOUND", "accuracy": 1.0}],
                "transfer": [{"phase": "transfer", "subset_id": "state+path", "accuracy": 1.0}],
            },
        )
        self.assertIn("Fusion", report)
        self.assertIn("Budget Curve", report)
        self.assertIn("Held-out Transfer", report)


if __name__ == "__main__":
    unittest.main()
