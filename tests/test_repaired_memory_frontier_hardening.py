import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from alien_lab.final_memory_frontier import (
    ARM_NONE,
    TITAN_NONE,
    ModelSpec,
    SuiteConfig,
    build_level,
    generate_bootstrap,
)
from alien_lab.repaired_memory_frontier import Repaired007Runner


class ScriptClient:
    def __init__(self, mode="ok"):
        self.mode = mode
        self.calls = []

    def model_metadata(self, model, timeout_seconds=5.0):
        return {"name": model, "capabilities": ["completion"]}

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        prompt = kwargs["prompt"]
        if self.mode == "ceiling":
            return SimpleNamespace(
                status="OK", response="", hit_ceiling=True,
                prompt_tokens=1, eval_tokens=kwargs["num_predict"], wall_ms=1.0,
                done_reason="length",
            )
        if prompt.startswith("FORMAT-ONLY RECOVERY"):
            source = prompt.split("SOURCE RESPONSE:\n", 1)[1]
            if self.mode == "recoverable" and source.strip() == "A B C D A B":
                response = "1:A 2:B 3:C 4:D 5:A 6:B"
            else:
                response = "INVALID"
            return SimpleNamespace(
                status="OK", response=response, hit_ceiling=False,
                prompt_tokens=2, eval_tokens=8, wall_ms=1.0, done_reason="stop",
            )
        if self.mode == "recoverable":
            response = "A B C D A B"
        else:
            task_count = prompt.count("\nTASK ") + (1 if prompt.startswith("TASK ") else 0)
            response = " ".join(f"{i}:A" for i in range(1, task_count + 1)) if task_count else "A"
        return SimpleNamespace(
            status="OK", response=response, hit_ceiling=False,
            prompt_tokens=10, eval_tokens=5, wall_ms=1.0, done_reason="stop",
        )


class HardeningTests(unittest.TestCase):
    def _runner(self, client, *, output_budget=512, retry_count=1):
        spec = ModelSpec("m", "m", context_limit=100000, output_budget=output_budget)
        cfg = SuiteConfig("x", (spec,), max_level=1, retry_count=retry_count)
        return Repaired007Runner(cfg, lambda _: client, Path(tempfile.mkdtemp())), spec

    def test_format_recovery_sees_only_prior_response_not_task(self):
        client = ScriptClient("recoverable")
        runner, spec = self._runner(client)
        store = generate_bootstrap(20260828)
        tasks, sealed = build_level(20260828, 1, 0, store)
        with tempfile.TemporaryDirectory() as td:
            row = runner._run_arm(client, spec, Path(td), 1, 0, tasks, sealed, store, ARM_NONE)
        self.assertEqual(row["status"], "OK")
        self.assertTrue(row["format_recovery_used"])
        self.assertEqual(row["format_recovery_response"], "1:A 2:B 3:C 4:D 5:A 6:B")
        recovery_prompt = client.calls[1]["prompt"]
        self.assertTrue(recovery_prompt.startswith("FORMAT-ONLY RECOVERY"))
        self.assertIn("A B C D A B", recovery_prompt)
        self.assertNotIn("BASE RULEBOOK", recovery_prompt)
        self.assertNotIn("TASK 1", recovery_prompt)
        self.assertNotIn("CHOICES", recovery_prompt)

    def test_ambiguous_format_recovery_stays_unscorable(self):
        client = ScriptClient("ambiguous")
        runner, spec = self._runner(client)
        raw = "A:B:C:D:A:\nB:D:C:B:D:"
        recovered, meta = runner._format_only_recovery(client, spec, raw, 6, 7)
        self.assertIsNone(recovered)
        self.assertEqual(meta["status"], "FORMAT_RECOVERY_INVALID")

    def test_ladder_preserves_output_cap_status(self):
        client = ScriptClient("ceiling")
        runner, spec = self._runner(client)
        store = generate_bootstrap(20260828)
        tasks, sealed = build_level(20260828, 1, 0, store)
        with tempfile.TemporaryDirectory() as td:
            row = runner._run_arm(client, spec, Path(td), 1, 0, tasks, sealed, store, ARM_NONE)
        self.assertEqual(row["status"], "OUTPUT_CAP_REACHED")
        self.assertIsNone(row["accuracy"])

    def test_titan_preserves_output_cap_status(self):
        client = ScriptClient("ceiling")
        runner, spec = self._runner(client)
        store = generate_bootstrap(20260828)
        with tempfile.TemporaryDirectory() as td:
            titan = runner._run_titan(client, spec, Path(td), store)
        self.assertEqual(titan["attempts"][TITAN_NONE]["status"], "OUTPUT_CAP_REACHED")


if __name__ == "__main__":
    unittest.main()
