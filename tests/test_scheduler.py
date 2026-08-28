import tempfile
import unittest
from pathlib import Path

from alien_lab.experiment import ExperimentConfig, ExperimentRunner, parse_packet_response
from alien_lab.ollama import ModelResult


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


class FakeClient:
    def __init__(self, clock, seconds_per_call=0.1):
        self.clock = clock
        self.seconds_per_call = seconds_per_call
        self.calls = []

    def model_metadata(self, model, timeout_seconds=5.0):
        return {"name": model, "digest": "fake-digest", "size": 123, "details": {"quantization_level": "Q8_0"}}

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        duration = self.seconds_per_call
        if kwargs["timeout_seconds"] < duration:
            self.clock.advance(kwargs["timeout_seconds"])
            return ModelResult(status="TIME_BUDGET_ABORT", done_reason="time_budget_abort", wall_ms=kwargs["timeout_seconds"] * 1000)
        self.clock.advance(duration)
        # Up to six discovery tasks; parser ignores extra positions for single-task runs.
        return ModelResult(
            status="OK",
            response="1:A 2:B 3:C 4:D 5:A 6:B",
            thinking="trace",
            done_reason="stop",
            prompt_tokens=100,
            eval_tokens=24,
            prompt_eval_ns=100_000_000,
            eval_ns=1_000_000_000,
            wall_ms=duration * 1000,
        )


class SchedulerTests(unittest.TestCase):
    def test_packet_parser_maps_positions(self):
        parsed = parse_packet_response("1:B 2:D 3:A", ["t1", "t2", "t3"])
        self.assertEqual(parsed, {"t1": "B", "t2": "D", "t3": "A"})

    def test_dry_run_has_complete_boolean_cube_and_dense_observation_count(self):
        cfg = ExperimentConfig()
        runner = ExperimentRunner(cfg, client=None)
        plan = runner.dry_run()
        self.assertEqual(plan["discovery_structured_calls"], 64)
        self.assertEqual(plan["discovery_raw_calls"], 1)
        self.assertEqual(plan["discovery_tasks_per_call"], 6)
        self.assertEqual(plan["boolean_cube_task_observations"], 384)

    def test_required_cube_runs_before_any_optional_phase(self):
        clock = FakeClock()
        client = FakeClient(clock, seconds_per_call=0.1)
        cfg = ExperimentConfig(target_minutes=0.12, ceiling_minutes=0.14, safety_margin_seconds=0.2)
        with tempfile.TemporaryDirectory() as td:
            runner = ExperimentRunner(cfg, client=client, clock=clock.now, output_dir=Path(td))
            records = runner.run()
        discovery = [r for r in records if r.phase == "discovery"]
        self.assertEqual(len(discovery), 65)
        first_optional = next((i for i, r in enumerate(records) if r.phase != "discovery"), None)
        if first_optional is not None:
            self.assertGreaterEqual(first_optional, 65)

    def test_optional_work_does_not_start_when_estimate_plus_margin_will_not_fit(self):
        clock = FakeClock()
        client = FakeClient(clock, seconds_per_call=1.0)
        # 65 required calls consume 65s; only 2s remain and safety margin is 2s.
        cfg = ExperimentConfig(target_minutes=1.08, ceiling_minutes=67/60, safety_margin_seconds=2.0)
        with tempfile.TemporaryDirectory() as td:
            records = ExperimentRunner(cfg, client=client, clock=clock.now, output_dir=Path(td)).run()
        self.assertEqual(len([r for r in records if r.phase == "discovery"]), 65)
        self.assertFalse(any(r.phase != "discovery" for r in records))

    def test_absolute_deadline_abort_is_not_scored_as_model_failure(self):
        clock = FakeClock()
        client = FakeClient(clock, seconds_per_call=2.0)
        cfg = ExperimentConfig(target_minutes=0.015, ceiling_minutes=0.02, safety_margin_seconds=0.0)
        with tempfile.TemporaryDirectory() as td:
            runner = ExperimentRunner(cfg, client=client, clock=clock.now, output_dir=Path(td))
            records = runner.run()
        self.assertEqual(records[-1].status, "TIME_BUDGET_ABORT")
        self.assertIsNone(records[-1].verified_success)
        self.assertEqual(runner.summary["time_budget_aborts"], 1)
        self.assertEqual(runner.summary["scored_generations"], 0)

    def test_presentation_perturbation_uses_its_own_sealed_answer_positions(self):
        from alien_lab.taskgen import generate_taskset
        clock = FakeClock()
        client = FakeClient(clock, seconds_per_call=0.001)
        cfg = ExperimentConfig(target_minutes=0.5, ceiling_minutes=1.0, safety_margin_seconds=0.0)
        with tempfile.TemporaryDirectory() as td:
            runner = ExperimentRunner(cfg, client=client, clock=clock.now, output_dir=Path(td))
            runner.run()
            perturbed = [o for o in runner.observations if o["phase"] == "presentation_perturbation"]
        self.assertTrue(perturbed)
        _, sealed = generate_taskset(cfg.seed + 1)
        for obs in perturbed:
            self.assertEqual(obs["expected"], sealed.answers[obs["task_id"]]["answer"])

    def test_discovery_analysis_exports_full_causal_math(self):
        clock = FakeClock()
        client = FakeClient(clock, seconds_per_call=0.001)
        cfg = ExperimentConfig(target_minutes=0.0012, ceiling_minutes=0.0015, safety_margin_seconds=0.02)
        with tempfile.TemporaryDirectory() as td:
            runner = ExperimentRunner(cfg, client=client, clock=clock.now, output_dir=Path(td))
            runner.run()
            analysis = runner.summary["discovery_analysis"]
        self.assertIsNotNone(analysis)
        self.assertEqual(set(analysis["shapley_values"]), {"state", "path", "uncertainty", "relevance", "procedure", "memory"})
        self.assertEqual(len(analysis["mobius_interactions"]), 64)
        self.assertEqual(set(analysis["average_main_effects"]), set(analysis["shapley_values"]))
        self.assertEqual(set(analysis["leave_one_out_full"]), set(analysis["shapley_values"]))
        self.assertTrue(analysis["pareto_frontier"])
        self.assertTrue(analysis["minimal_sufficient_sets"])

    def test_finish_writes_machine_and_human_reports(self):
        clock = FakeClock()
        client = FakeClient(clock, seconds_per_call=0.001)
        cfg = ExperimentConfig(target_minutes=0.0012, ceiling_minutes=0.0015, safety_margin_seconds=0.02)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            runner = ExperimentRunner(cfg, client=client, clock=clock.now, output_dir=out)
            runner.run()
            self.assertTrue((out / "compound_registry.json").exists())
            self.assertTrue((out / "report.md").exists())
            self.assertIn("Capability", (out / "report.md").read_text())

    def test_environment_snapshot_records_model_digest(self):
        clock = FakeClock()
        client = FakeClient(clock, seconds_per_call=2.0)
        cfg = ExperimentConfig(target_minutes=0.015, ceiling_minutes=0.02, safety_margin_seconds=0.0)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            ExperimentRunner(cfg, client=client, clock=clock.now, output_dir=out).run()
            import json
            env = json.loads((out / "environment.json").read_text())
        self.assertEqual(env["model_metadata"]["digest"], "fake-digest")
        self.assertEqual(env["config"]["context_limit"], 25600)

    def test_run_records_preserve_exact_prompt_and_pass_cost_provenance(self):
        clock = FakeClock()
        client = FakeClient(clock, seconds_per_call=0.001)
        cfg = ExperimentConfig(target_minutes=0.0012, ceiling_minutes=0.0015, safety_margin_seconds=0.02)
        with tempfile.TemporaryDirectory() as td:
            runner = ExperimentRunner(cfg, client=client, clock=clock.now, output_dir=Path(td))
            records = runner.run()
        compound = next(r for r in records if r.phase == "discovery" and r.primitives)
        self.assertTrue(compound.metadata["prompt_hash"])
        self.assertIn("INDEPENDENT DECISION PACKET", compound.metadata["prompt_text"])
        self.assertTrue(compound.metadata["pass_timings_by_task"])
        self.assertGreater(compound.metadata["prompt_bytes"], 0)
        obs = next(o for o in runner.observations if o["run_id"] == compound.run_id)
        self.assertIn("pass_timings_ms", obs)
        self.assertIn("derived_fact_count", obs)

    def test_full_optional_catalog_includes_compound_order_fusion_and_budget_curve(self):
        plan = ExperimentRunner(ExperimentConfig(), client=None).dry_run()
        required = {
            "transfer", "compute_substitution", "order_effect", "higher_order_order",
            "fusion_probe", "recursive_fusion", "batching_control", "antagonism_control",
            "presentation_perturbation", "budget_curve", "robustness_replication"
        }
        self.assertTrue(required.issubset(set(plan["optional_phase_catalog"])))

    def test_recursive_fusion_phase_produces_second_order_compound_records(self):
        clock = FakeClock()
        client = FakeClient(clock, seconds_per_call=0.001)
        cfg = ExperimentConfig(target_minutes=0.5, ceiling_minutes=1.0, safety_margin_seconds=0.0)
        with tempfile.TemporaryDirectory() as td:
            runner = ExperimentRunner(cfg, client=client, clock=clock.now, output_dir=Path(td))
            records = runner.run()
        recursive = [r for r in records if r.phase == "recursive_fusion" and r.metadata.get("fusion_depth") == 2]
        self.assertTrue(recursive)
        self.assertTrue(any("fusion_depth_2" in r.pass_order for r in recursive))

    def test_discovery_analysis_separates_capability_and_compute_causality_per_task(self):
        clock = FakeClock()
        client = FakeClient(clock, seconds_per_call=0.001)
        cfg = ExperimentConfig(target_minutes=0.0012, ceiling_minutes=0.0015, safety_margin_seconds=0.02)
        with tempfile.TemporaryDirectory() as td:
            runner = ExperimentRunner(cfg, client=client, clock=clock.now, output_dir=Path(td))
            runner.run()
            analysis = runner.summary["discovery_analysis"]
        self.assertEqual(set(analysis["metric_causal_analysis"]), {"accuracy", "eval_tokens", "wall_ms", "compiler_ms"})
        self.assertEqual(len(analysis["per_task_causal_analysis"]), 6)
        for task_analysis in analysis["per_task_causal_analysis"].values():
            self.assertEqual(set(task_analysis["shapley_values"]), {"state", "path", "uncertainty", "relevance", "procedure", "memory"})

    def test_finish_writes_counterfactual_failure_and_followup_datasets(self):
        clock = FakeClock()
        client = FakeClient(clock, seconds_per_call=0.001)
        cfg = ExperimentConfig(target_minutes=0.5, ceiling_minutes=1.0, safety_margin_seconds=0.0)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            runner = ExperimentRunner(cfg, client=client, clock=clock.now, output_dir=out)
            runner.run()
            self.assertTrue((out / "counterfactuals.jsonl").exists())
            self.assertTrue((out / "failures.jsonl").exists())
            self.assertTrue((out / "causal_matrix.csv").exists())
            self.assertTrue((out / "followup_analysis.json").exists())
            follow = runner.summary["followup_analysis"]
            report_text = (out / "report.md").read_text()
        self.assertIn("Held-out Transfer", report_text)
        self.assertIn("Fusion", report_text)
        self.assertIn("Budget Curve", report_text)
        phases = {row["phase"] for row in follow["phase_aggregates"]}
        self.assertIn("transfer", phases)
        self.assertIn("budget_curve", phases)
        self.assertIn("recursive_fusion", phases)

    def test_existing_raw_results_cannot_be_silently_appended_to_a_new_run(self):
        clock = FakeClock()
        client = FakeClient(clock, seconds_per_call=0.001)
        cfg = ExperimentConfig()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            (out / "runs.jsonl").write_text("historical\n")
            runner = ExperimentRunner(cfg, client=client, clock=clock.now, output_dir=out)
            with self.assertRaisesRegex(RuntimeError, "already contains raw run evidence"):
                runner.run()
        self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
