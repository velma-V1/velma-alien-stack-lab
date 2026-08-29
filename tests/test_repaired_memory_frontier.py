import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from alien_lab.final_memory_frontier import ModelSpec, SuiteConfig
from alien_lab.repaired_memory_frontier import Repaired007Runner


class FakeClient:
    def __init__(self, base_url, *, models=None, ceiling=False):
        self.models = {
            "thinking-model": {"name": "thinking-model", "capabilities": ["completion", "thinking"]},
            "plain-model": {"name": "plain-model", "capabilities": ["completion"]},
        } if models is None else models
        self.ceiling = ceiling
        self.calls = []

    def model_metadata(self, model, timeout_seconds=5.0):
        if model not in self.models:
            raise RuntimeError(f"MODEL_UNAVAILABLE: {model}")
        return self.models[model]

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        task_count = kwargs["prompt"].count("\nTASK ")
        if kwargs["prompt"].startswith("TASK "):
            task_count += 1
        response = " ".join(f"{i}:A" for i in range(1, task_count + 1)) if task_count else "A"
        return SimpleNamespace(
            status="OK",
            response=response,
            hit_ceiling=self.ceiling,
            prompt_tokens=10,
            eval_tokens=5,
            wall_ms=1.0,
            done_reason="length" if self.ceiling else "stop",
        )


class Tests(unittest.TestCase):
    def test_thinking_capability_is_disabled_but_plain_model_omits_think(self):
        thinking = FakeClient("")
        plain = FakeClient("")
        cfg = SuiteConfig("x", (ModelSpec("thinking-model", "t"), ModelSpec("plain-model", "p")), max_level=1)
        with tempfile.TemporaryDirectory() as td:
            runner = Repaired007Runner(cfg, lambda _: thinking, Path(td))
            runner._safe_generate(thinking, cfg.models[0], "hello", 1)
            self.assertIs(thinking.calls[-1]["think"], False)

            runner2 = Repaired007Runner(cfg, lambda _: plain, Path(td))
            runner2._safe_generate(plain, cfg.models[1], "hello", 1)
            self.assertIsNone(plain.calls[-1]["think"])

    def test_missing_exact_model_fails_preflight_without_ladder(self):
        cfg = SuiteConfig("x", (ModelSpec("missing", "missing"),), max_level=1)
        client = FakeClient("", models={})
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            runner = Repaired007Runner(cfg, lambda _: client, out)
            summary = runner.run_model(cfg.models[0])
            self.assertFalse(summary["completed"])
            self.assertFalse(summary["experiment_valid"])
            self.assertEqual(summary["evidence_status"], "MODEL_UNAVAILABLE")
            self.assertEqual(summary["paired_packet_count"], 0)
            self.assertFalse((out / "missing" / "runs.jsonl").exists())

    def test_output_ceiling_fails_live_preflight_instead_of_running_288_packets(self):
        cfg = SuiteConfig("x", (ModelSpec("thinking-model", "t"),), max_level=48, retry_count=2)
        client = FakeClient("", ceiling=True)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            runner = Repaired007Runner(cfg, lambda _: client, out)
            summary = runner.run_model(cfg.models[0])
            self.assertFalse(summary["completed"])
            self.assertEqual(summary["evidence_status"], "LIVE_SCORING_PREFLIGHT_FAILED")
            self.assertEqual(summary["paired_packet_count"], 0)
            self.assertLessEqual(len(client.calls), 6)
            preflight = json.loads((out / "t" / "live_preflight.json").read_text())
            statuses = {a["status"] for a in preflight["arms"].values()}
            self.assertEqual(statuses, {"OUTPUT_CAP_REACHED"})

    def test_valid_model_cannot_finish_with_zero_evidence(self):
        cfg = SuiteConfig("x", (ModelSpec("plain-model", "p", context_limit=100000),), max_level=1, retry_count=1)
        client = FakeClient("")
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            runner = Repaired007Runner(cfg, lambda _: client, out)
            summary = runner.run_model(cfg.models[0])
            self.assertTrue(summary["execution_completed"])
            self.assertTrue(summary["experiment_valid"])
            self.assertTrue(summary["completed"])
            self.assertGreater(summary["paired_packet_count"], 0)
            self.assertGreater(summary["paired_coverage"], 0)

    def test_suite_validity_is_not_loop_completion(self):
        cfg = SuiteConfig("x", (ModelSpec("missing", "missing"),), max_level=1)
        client = FakeClient("", models={})
        with tempfile.TemporaryDirectory() as td:
            result = Repaired007Runner(cfg, lambda _: client, Path(td)).run_suite()
            self.assertFalse(result["suite_valid"])
            self.assertFalse(result["suite_completed"])
            self.assertEqual(result["valid_model_count"], 0)


if __name__ == "__main__":
    unittest.main()
