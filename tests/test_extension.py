import json
import tempfile
import unittest
from pathlib import Path

from alien_lab.extension import run_extension
from alien_lab.experiment import ExperimentConfig, ExperimentRunner
from alien_lab.ollama import ModelResult


class FakeClock:
    def __init__(self): self.t = 0.0
    def now(self): return self.t
    def advance(self, seconds): self.t += seconds


class FakeClient:
    def __init__(self, clock, seconds_per_call=0.01):
        self.clock = clock
        self.seconds_per_call = seconds_per_call
    def model_metadata(self, model, timeout_seconds=5.0):
        return {"name": model, "digest": "fake-digest", "details": {"quantization_level": "Q8_0"}}
    def generate(self, **kwargs):
        duration = self.seconds_per_call
        if kwargs["timeout_seconds"] < duration:
            self.clock.advance(kwargs["timeout_seconds"])
            return ModelResult(status="TIME_BUDGET_ABORT", done_reason="time_budget_abort", wall_ms=kwargs["timeout_seconds"] * 1000)
        self.clock.advance(duration)
        return ModelResult(
            status="OK", response="1:A 2:B 3:C 4:D 5:A 6:B", thinking="trace", done_reason="stop",
            prompt_tokens=100, eval_tokens=24, prompt_eval_ns=100_000_000, eval_ns=1_000_000_000,
            wall_ms=duration * 1000,
        )


class ExtensionTests(unittest.TestCase):
    def test_extension_uses_prior_evidence_and_spends_only_remaining_cumulative_budget(self):
        clock = FakeClock()
        client = FakeClient(clock)
        prior_cfg = ExperimentConfig(target_minutes=0.03, ceiling_minutes=0.04, safety_margin_seconds=0.01)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            prior_dir = root / "prior"
            prior = ExperimentRunner(prior_cfg, client=client, clock=clock.now, output_dir=prior_dir)
            prior.run()
            prior_elapsed = prior.summary["elapsed_seconds"]

            ext_cfg = ExperimentConfig(
                experiment_id="002-adaptive-hour-extension",
                target_minutes=0.05,
                ceiling_minutes=0.06,
                safety_margin_seconds=0.01,
            )
            ext = run_extension(
                ext_cfg,
                prior_results_dir=prior_dir,
                client=client,
                output_dir=root / "extension",
                clock=clock.now,
            )
            summary = json.loads((root / "extension" / "extension_summary.json").read_text())

        self.assertEqual(summary["prior_context"]["prior_elapsed_seconds"], prior_elapsed)
        self.assertTrue(summary["adaptive_cube_generations"] or summary["adaptive_tail_generations"])
        self.assertGreaterEqual(summary["cumulative_elapsed_seconds"], 2.5)
        self.assertLessEqual(summary["cumulative_elapsed_seconds"], ext_cfg.ceiling_minutes * 60.0)
        self.assertFalse(any(r.phase == "discovery" for r in ext.records))

    def test_extension_rejects_model_mismatch(self):
        clock = FakeClock()
        client = FakeClient(clock)
        prior_cfg = ExperimentConfig(target_minutes=0.02, ceiling_minutes=0.03, safety_margin_seconds=0.01)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            prior_dir = root / "prior"
            ExperimentRunner(prior_cfg, client=client, clock=clock.now, output_dir=prior_dir).run()
            bad = ExperimentConfig(model="different-model", target_minutes=0.05, ceiling_minutes=0.06)
            with self.assertRaisesRegex(RuntimeError, "does not match"):
                run_extension(bad, prior_results_dir=prior_dir, client=client, output_dir=root / "extension", clock=clock.now)


if __name__ == "__main__":
    unittest.main()
