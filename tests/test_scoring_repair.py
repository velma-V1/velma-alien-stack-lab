import tempfile
import unittest
from pathlib import Path

from alien_lab.experiment import ExperimentConfig
from alien_lab.ollama import ModelResult
from alien_lab.scoring_repair import ScoringRepairRunner, StrictFinalAnswerClient


VALID = "1:A 2:B 3:C 4:D 5:A 6:B"


class StubInner:
    def __init__(self, result):
        self.result = result
        self.calls = []
        self.base_url = "http://stub"

    def model_metadata(self, model, timeout_seconds=5.0):
        return {"name": model, "digest": "stub", "details": {"quantization_level": "Q8_0"}}

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class ScoringRepairTests(unittest.TestCase):
    def test_wrapper_forces_thinking_off(self):
        inner = StubInner(ModelResult(status="OK", response=VALID, done_reason="stop", eval_tokens=12))
        client = StrictFinalAnswerClient(inner)
        result = client.generate(
            model="qwen3.5:9b-q8_0",
            prompt="TASK 1\nX\nTASK 2\nX\nTASK 3\nX\nTASK 4\nX\nTASK 5\nX\nTASK 6\nX",
            num_ctx=25600,
            num_predict=64,
            temperature=0,
            seed=1,
            timeout_seconds=10,
            think=True,
        )
        self.assertEqual(result.status, "OK")
        self.assertFalse(inner.calls[0]["think"])

    def test_blank_thinking_only_completion_is_unscorable_not_wrong(self):
        inner = StubInner(ModelResult(
            status="OK", response="", thinking="reasoning", done_reason="length",
            eval_tokens=64, hit_ceiling=True,
        ))
        client = StrictFinalAnswerClient(inner)
        result = client.generate(
            model="q", prompt="TASK 1\nX", num_ctx=25600, num_predict=64,
            temperature=0, seed=1, timeout_seconds=10,
        )
        self.assertEqual(result.status, "UNSCORABLE")

    def test_incomplete_packet_is_unscorable(self):
        inner = StubInner(ModelResult(status="OK", response="1:A 2:B", done_reason="stop", eval_tokens=8))
        client = StrictFinalAnswerClient(inner)
        prompt = "\n".join(f"TASK {i}\nX" for i in range(1, 7))
        result = client.generate(
            model="q", prompt=prompt, num_ctx=25600, num_predict=64,
            temperature=0, seed=1, timeout_seconds=10,
        )
        self.assertEqual(result.status, "UNSCORABLE")

    def test_explanatory_text_is_unscorable_even_when_letters_can_be_found(self):
        inner = StubInner(ModelResult(
            status="OK",
            response=VALID + " because these are my answers",
            done_reason="stop",
            eval_tokens=20,
        ))
        client = StrictFinalAnswerClient(inner)
        prompt = "\n".join(f"TASK {i}\nX" for i in range(1, 7))
        result = client.generate(
            model="q", prompt=prompt, num_ctx=25600, num_predict=64,
            temperature=0, seed=1, timeout_seconds=10,
        )
        self.assertEqual(result.status, "UNSCORABLE")

    def test_complete_packet_is_scorable(self):
        inner = StubInner(ModelResult(status="OK", response=VALID, done_reason="stop", eval_tokens=12))
        client = StrictFinalAnswerClient(inner)
        prompt = "\n".join(f"TASK {i}\nX" for i in range(1, 7))
        result = client.generate(
            model="q", prompt=prompt, num_ctx=25600, num_predict=64,
            temperature=0, seed=1, timeout_seconds=10,
        )
        self.assertEqual(result.status, "OK")

    def test_validation_runner_never_schedules_optional_work(self):
        cfg = ExperimentConfig()
        runner = ScoringRepairRunner(cfg, client=None)
        self.assertFalse(runner._can_start_optional())

    def test_preflight_requires_three_complete_non_ceiling_packets(self):
        inner = StubInner(ModelResult(status="OK", response=VALID, done_reason="stop", eval_tokens=12))
        client = StrictFinalAnswerClient(inner)
        cfg = ExperimentConfig(discovery_budget=64)
        with tempfile.TemporaryDirectory() as td:
            runner = ScoringRepairRunner(cfg, client=client, output_dir=Path(td))
            report = runner.preflight()
        self.assertTrue(report["passed"])
        self.assertEqual(len(report["checks"]), 3)
        self.assertTrue(all(x["parseable_answers"] == 6 for x in report["checks"]))
        self.assertTrue(all(not call["think"] for call in inner.calls))

    def test_preflight_fails_before_cube_when_final_response_is_blank(self):
        inner = StubInner(ModelResult(
            status="OK", response="", thinking="reasoning", done_reason="length",
            eval_tokens=64, hit_ceiling=True,
        ))
        client = StrictFinalAnswerClient(inner)
        cfg = ExperimentConfig(discovery_budget=64)
        with tempfile.TemporaryDirectory() as td:
            runner = ScoringRepairRunner(cfg, client=client, output_dir=Path(td))
            report = runner.preflight()
        self.assertFalse(report["passed"])
        self.assertTrue(all(x["status"] == "UNSCORABLE" for x in report["checks"]))


if __name__ == "__main__":
    unittest.main()
