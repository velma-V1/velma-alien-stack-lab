from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alien_lab.architecture_discovery import build_task, execute_plan
from alien_lab.solver_kill_test import (
    build_kill_ledger,
    default_config,
    run_experiment,
    solve_public_task,
)


class PublicSurfaceSolverTests(unittest.TestCase):
    def test_solver_recovers_unseen_difficulty_32_composition_from_public_surface_only(self):
        task = build_task(20260991, "composition", 32, "NOVEL", "009-unseen-composition")
        result = solve_public_task(task.public_dict())
        self.assertTrue(result.ok, result.error)
        outcome = execute_plan(task, list(result.locators))
        self.assertTrue(outcome.verified_success)
        self.assertEqual(tuple(outcome.semantics), task.required_semantics)

    def test_solver_handles_all_solvable_families_and_stress_stages(self):
        families = (
            "linear_dependency",
            "conditional_branch",
            "multi_record_join",
            "loop_worklist",
            "policy_guard",
            "composition",
            "drift_resolution",
        )
        stages = ("NOVEL", "PARAMETER_VARIATION", "DRIFT", "COMPOSITION", "TRANSFER")
        for i, family in enumerate(families):
            stage = stages[i % len(stages)]
            with self.subTest(family=family, stage=stage):
                task = build_task(20260920 + i, family, 32, stage, f"009-{family}-{stage}")
                result = solve_public_task(task.public_dict())
                self.assertTrue(result.ok, result.error)
                outcome = execute_plan(task, list(result.locators))
                self.assertTrue(outcome.verified_success)

    def test_solver_rejects_ambiguous_root(self):
        public = {
            "task_id": "ambiguous",
            "family": "linear_dependency",
            "difficulty": 2,
            "stage": "NOVEL",
            "lineage": "test",
            "initial": [1, 2, 3],
            "public_flag": 0,
            "surface": [
                {"locator": "x", "label": "action=A00 requires=START condition=any", "slot": 0, "forbidden": False},
                {"locator": "y", "label": "action=A01 requires=START condition=any", "slot": 1, "forbidden": False},
            ],
        }
        result = solve_public_task(public)
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "AMBIGUOUS_SUCCESSOR:START")

    def test_solver_rejects_malformed_label_instead_of_guessing(self):
        public = {
            "task_id": "malformed",
            "family": "linear_dependency",
            "difficulty": 2,
            "stage": "NOVEL",
            "lineage": "test",
            "initial": [1, 2, 3],
            "public_flag": 0,
            "surface": [
                {"locator": "x", "label": "do A00 after START", "slot": 0, "forbidden": False},
            ],
        }
        result = solve_public_task(public)
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "MALFORMED_LABEL:x")

    def test_solver_rejects_duplicate_locator(self):
        public = {
            "task_id": "duplicate-locator",
            "family": "linear_dependency",
            "difficulty": 2,
            "stage": "NOVEL",
            "lineage": "test",
            "initial": [1, 2, 3],
            "public_flag": 0,
            "surface": [
                {"locator": "x", "label": "action=A00 requires=START condition=any", "slot": 0, "forbidden": False},
                {"locator": "x", "label": "action=A01 requires=A00 condition=any", "slot": 1, "forbidden": False},
            ],
        }
        result = solve_public_task(public)
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "DUPLICATE_LOCATOR:x")


class KillLedgerTests(unittest.TestCase):
    def test_default_ledger_contains_exactly_64_solvable_and_16_controls(self):
        ledger = build_kill_ledger(default_config())
        self.assertEqual(sum(c.phase == "SOLVABLE_KILL" for c in ledger), 64)
        self.assertEqual(sum(c.phase == "SILENT_CONTROL" for c in ledger), 16)
        self.assertEqual(len({c.cell_id for c in ledger}), 80)
        self.assertTrue(all(c.seed not in {20260829, 20260830} for c in ledger))

    def test_kill_ledger_is_deterministic(self):
        first = build_kill_ledger(default_config())
        second = build_kill_ledger(default_config())
        self.assertEqual(first, second)


class ExperimentHarnessTests(unittest.TestCase):
    def test_complete_default_experiment_hits_the_preregistered_kill_gate(self):
        with tempfile.TemporaryDirectory() as td:
            summary = run_experiment(default_config(), Path(td))
            self.assertEqual(summary["solvable_total"], 64)
            self.assertEqual(summary["solvable_successes"], 64)
            self.assertEqual(summary["solvable_failures"], 0)
            self.assertEqual(summary["silent_control_total"], 16)
            self.assertEqual(summary["silent_controls_correctly_refuted"], 16)
            self.assertEqual(summary["invalid_cells"], 0)
            self.assertEqual(summary["model_calls"], 0)
            self.assertGreater(summary["wilson95_lower"], 0.9345)
            self.assertTrue(summary["solver_kill_test_passed"])

            self.assertTrue((Path(td) / "ledger.json").exists())
            self.assertTrue((Path(td) / "ledger-manifest.json").exists())
            self.assertTrue((Path(td) / "summary.json").exists())
            self.assertEqual(len(list((Path(td) / "cells").glob("*.json"))), 80)

    def test_silent_control_is_refuted_not_counted_as_capability_success(self):
        config = default_config()
        config["solvable_count"] = 1
        config["silent_control_count"] = 2
        with tempfile.TemporaryDirectory() as td:
            summary = run_experiment(config, Path(td))
            self.assertEqual(summary["solvable_total"], 1)
            self.assertEqual(summary["silent_control_total"], 2)
            self.assertEqual(summary["silent_controls_correctly_refuted"], 2)
            self.assertEqual(summary["model_calls"], 0)

            rows = []
            for path in sorted((Path(td) / "cells").glob("*.json")):
                rows.append(json.loads(path.read_text(encoding="utf-8"))["evidence"])
            controls = [r for r in rows if r["phase"] == "SILENT_CONTROL"]
            self.assertEqual({r["classification"] for r in controls}, {"EXPECTED_REFUTATION"})
            self.assertTrue(all(r["screen_success"] is True for r in controls))
            self.assertTrue(all(r["authoritative_success"] is False for r in controls))
            self.assertTrue(all(r["verified_success"] is False for r in controls))

    def test_replay_fingerprint_is_identical_across_clean_output_directories(self):
        config = default_config()
        config["solvable_count"] = 8
        config["silent_control_count"] = 4
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first = run_experiment(config, Path(a))
            second = run_experiment(config, Path(b))
            self.assertEqual(first["replay_fingerprint"], second["replay_fingerprint"])


if __name__ == "__main__":
    unittest.main()
