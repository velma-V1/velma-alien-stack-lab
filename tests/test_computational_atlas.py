from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alien_lab.computational_atlas import (
    ALL_CAPABILITIES,
    build_ledger,
    default_config,
    diagnose_rescue,
    run_experiment,
)
from alien_lab.computational_atlas_engines import run_engine
from alien_lab.computational_atlas_models import (
    build_production_fitness_record,
    unavailable_model_evidence,
)
from alien_lab.computational_atlas_report import (
    build_accumulation_audit,
    build_discovery_report,
    run_rescue_probe,
)
from alien_lab.computational_atlas_worlds import build_worlds


class ComputationalAtlasWorldTests(unittest.TestCase):
    def test_default_world_set_is_192_unique_balanced_worlds(self) -> None:
        worlds = build_worlds(seed=20260829, count=192)
        self.assertEqual(len(worlds), 192)
        self.assertEqual(len({world.world_id for world in worlds}), 192)
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 0: 0}
        for world in worlds:
            if world.outside_basis:
                distribution[0] += 1
            else:
                n = len(world.required_capabilities)
                distribution[4 if n >= 4 else n] += 1
        self.assertEqual(distribution, {1: 64, 2: 64, 3: 40, 4: 16, 0: 8})
        self.assertEqual(len({world.family for world in worlds}), 12)

    def test_world_generation_is_replay_deterministic(self) -> None:
        first = [world.sealed_dict() for world in build_worlds(seed=77, count=192)]
        second = [world.sealed_dict() for world in build_worlds(seed=77, count=192)]
        self.assertEqual(first, second)

    def test_non_oracle_rendering_hides_answers_and_required_capabilities(self) -> None:
        world = build_worlds(seed=5, count=192)[81]
        public = world.render("R2_NATURAL")
        text = json.dumps(public, sort_keys=True)
        self.assertNotIn("expected_result", text)
        self.assertNotIn("required_capabilities", text)
        for capability in world.required_capabilities:
            self.assertNotIn(f'"{capability}"', text)


class ComputationalAtlasEngineTests(unittest.TestCase):
    def test_all_eight_reference_engines_compute_real_operations(self) -> None:
        cases = {
            "G": ({"edges": [["A", "B"], ["B", "C"], ["A", "D"], ["D", "C"]], "start": "A", "goal": "C"}, ["A", "B", "C"]),
            "L": ({"facts": {"rain": True}, "rules": [["rain", "wet"], ["wet", "slippery"]], "query": "slippery"}, True),
            "C": ({"items": [{"id": "a", "cost": 4, "value": 8}, {"id": "b", "cost": 3, "value": 5}, {"id": "c", "cost": 5, "value": 10}], "budget": 7}, ["a", "b"]),
            "P": ({"transitions": {"s0": ["s1", "s2"], "s1": ["goal"], "s2": ["dead"], "dead": [], "goal": []}, "start": "s0", "goal": "goal"}, ["s0", "s1", "goal"]),
            "X": ({"program": [{"op": "set", "name": "x", "value": 5}, {"op": "mul", "name": "x", "value": 4}, {"op": "add", "name": "x", "value": 3}], "return": "x"}, 23),
            "M": ({"operation": "weighted_mean", "values": [10, 20, 30], "weights": [1, 2, 1]}, 20.0),
            "D": ({"left": [{"id": 1}, {"id": 2}], "right": [{"id": 1, "amount": 7}, {"id": 2, "amount": 11}, {"id": 3, "amount": 100}], "left_key": "id", "right_key": "id", "sum_field": "amount"}, 18),
            "R": ({"query_terms": ["alpha", "beta"], "records": [{"id": "r1", "terms": ["alpha"], "authority": 2}, {"id": "r2", "terms": ["alpha", "beta"], "authority": 1}, {"id": "r3", "terms": ["beta"], "authority": 3}], "top_k": 2}, ["r2", "r3"]),
        }
        self.assertEqual(set(cases), set(ALL_CAPABILITIES))
        for capability, (payload, expected) in cases.items():
            with self.subTest(capability=capability):
                result = run_engine(capability, payload, {})
                self.assertTrue(result.ok, result.error)
                self.assertEqual(result.value, expected)

    def test_unknown_engine_is_explicitly_unsupported(self) -> None:
        result = run_engine("Z", {}, {})
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "UNSUPPORTED_CAPABILITY:Z")


class ComputationalAtlasLedgerTests(unittest.TestCase):
    def test_phase_a_has_all_256_subsets_for_64_diagnostics(self) -> None:
        config = default_config(profile="atlas")
        ledger = build_ledger(config)
        phase_a = [cell for cell in ledger if cell.phase == "A_ATTRIBUTION"]
        self.assertEqual(len(phase_a), 64 * 256)
        by_world: dict[str, set[tuple[str, ...]]] = {}
        for cell in phase_a:
            by_world.setdefault(cell.world_id, set()).add(cell.capabilities)
        self.assertEqual(len(by_world), 64)
        self.assertTrue(all(len(subsets) == 256 for subsets in by_world.values()))

    def test_phase_b_is_full_plus_eight_leave_one_out_arms(self) -> None:
        config = default_config(profile="atlas")
        ledger = build_ledger(config)
        phase_b = [cell for cell in ledger if cell.phase == "B_ORACLE_CEILING"]
        self.assertEqual(len(phase_b), 192 * 9)

    def test_smoke_run_is_complete_sealed_zero_model_and_replayable(self) -> None:
        config = default_config(profile="smoke")
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first = run_experiment(config, Path(a))
            second = run_experiment(config, Path(b))
            self.assertEqual(first["conclusion"], "DISCOVERY_COMPLETE")
            self.assertEqual(first["invalid_cells"], 0)
            self.assertEqual(first["model_calls"], 0)
            self.assertEqual(first["terminal_cells"], first["expected_cells"])
            self.assertEqual(first["replay_fingerprint"], second["replay_fingerprint"])
            self.assertEqual(first["ledger_hash"], second["ledger_hash"])
            self.assertEqual(first["question_coverage"]["mandatory_32"], 32)
            self.assertEqual(first["question_coverage"]["tribunal_q0_q36"], 37)
            self.assertEqual(len(first["production_fitness_records"]), 8)

    def test_changed_ledger_cannot_reuse_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            run_experiment(default_config(profile="smoke", seed=1), output)
            with self.assertRaisesRegex(ValueError, "OUTPUT_DIRECTORY_LEDGER_MISMATCH"):
                run_experiment(default_config(profile="smoke", seed=2), output)


class ComputationalAtlasDiagnosisTests(unittest.TestCase):
    def test_rescue_ladder_localizes_each_recoverable_stage(self) -> None:
        stages = [
            "SEMANTIC",
            "DECOMPOSITION",
            "ROUTING",
            "ENGINE",
            "COMPOSITION",
            "EXECUTION",
            "VERIFICATION",
        ]
        for stage in stages:
            rescue_results = {name: False for name in stages}
            start = stages.index(stage)
            for name in stages[start:]:
                rescue_results[name] = True
            with self.subTest(stage=stage):
                self.assertEqual(diagnose_rescue(False, rescue_results), stage)
        self.assertEqual(diagnose_rescue(False, {name: False for name in stages}), "MISSING_CAPABILITY")
        self.assertEqual(diagnose_rescue(True, {}), "NONE")

    def test_controlled_rescue_probe_preserves_original_failure_and_localizes_stage(self) -> None:
        world = build_worlds(seed=9, count=192)[130]
        for stage in ("SEMANTIC", "DECOMPOSITION", "ROUTING", "ENGINE", "COMPOSITION", "EXECUTION", "VERIFICATION"):
            with self.subTest(stage=stage):
                probe = run_rescue_probe(world, injected_fault=stage)
                self.assertEqual(probe["original_score"], 0)
                self.assertEqual(probe["localized_bottleneck"], stage)
                self.assertTrue(probe["rescued"])
        outside = build_worlds(seed=9, count=192)[190]
        probe = run_rescue_probe(outside, injected_fault="MISSING_CAPABILITY")
        self.assertEqual(probe["original_score"], 0)
        self.assertFalse(probe["rescued"])
        self.assertEqual(probe["localized_bottleneck"], "MISSING_CAPABILITY")

    def test_multi_engine_world_requires_complete_composition(self) -> None:
        world = build_worlds(seed=13, count=192)[170]
        self.assertGreaterEqual(len(world.required_capabilities), 4)
        report = run_rescue_probe(world, injected_fault="COMPOSITION")
        self.assertEqual(report["localized_bottleneck"], "COMPOSITION")
        self.assertEqual(report["original_score"], 0)
        self.assertEqual(report["rescued_score"], 1)


class ComputationalAtlasLearningTests(unittest.TestCase):
    def test_executable_capability_audit_reduces_reasoning_calls_across_lineages(self) -> None:
        audit = build_accumulation_audit(seed=20260829, lineage_count=48)
        self.assertEqual(audit["lineages"], 48)
        self.assertEqual(audit["stages_per_lineage"], 6)
        self.assertEqual(audit["evidence_kind"], "SYNTHETIC_MECHANISM_AUDIT")
        no_retained = audit["arms"]["NO_RETAINED_CAPABILITY"]
        executable = audit["arms"]["VERIFIED_EXECUTABLE_CAPABILITY"]
        self.assertLess(executable["reasoning_calls"], no_retained["reasoning_calls"])
        self.assertEqual(executable["incorrect_reuse"], 0)
        self.assertGreater(executable["reuse_events"], 0)


class ComputationalAtlasReportTests(unittest.TestCase):
    def test_discovery_report_contains_all_required_maps(self) -> None:
        worlds = build_worlds(seed=22, count=192)
        report = build_discovery_report(worlds=worlds, phase_maps={"minimum_basis": {}, "leave_one_out": {}, "computational_coverage": {}})
        required_maps = {
            "computational_coverage",
            "minimum_basis",
            "unique_engine_value",
            "synergy_matrix",
            "substitution_redundancy",
            "semantic_degradation",
            "semantic_error_taxonomy",
            "decomposition_error_rate",
            "routing_regret",
            "tool_overload",
            "model_dependence_pareto",
            "verification_value",
            "silent_wrong_rate",
            "capability_learning",
            "transfer_drift",
            "horizon_curve",
            "frontier_gap",
            "missing_capability_clusters",
            "rescue_bottlenecks",
            "next_direction_pareto",
        }
        self.assertEqual(set(report["maps"]), required_maps)
        self.assertEqual(report["conclusion_semantics"], "DISCOVERY_NOT_PASS_FAIL")


class ComputationalAtlasProductionTests(unittest.TestCase):
    def test_unavailable_model_is_unscored_not_capability_zero(self) -> None:
        evidence = unavailable_model_evidence("local", "not configured")
        self.assertEqual(evidence["status"], "MODEL_UNAVAILABLE")
        self.assertIsNone(evidence["score"])

    def test_production_fitness_record_covers_v31m4_promotion_questions(self) -> None:
        record = build_production_fitness_record(
            capability="C",
            contribution=0.25,
            domains=["scheduling", "resource_allocation"],
        )
        required = {
            "capability",
            "measured_contribution",
            "affected_domains",
            "model_calls_displaced",
            "composition_compatibility",
            "determinism",
            "verification_contract",
            "resource_estimate",
            "isolation_requirement",
            "state_requirement",
            "failure_containment",
            "replaceability_contract",
            "v31m4_integration_seam",
            "roadmap_displacement",
            "engineering_estimate",
            "evidence_confidence",
            "promotion_status",
        }
        self.assertTrue(required.issubset(record))
        self.assertEqual(record["promotion_status"], "EXPERIMENTAL")


if __name__ == "__main__":
    unittest.main()
