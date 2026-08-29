import json
import tempfile
import unittest
from pathlib import Path

from alien_lab.architecture_discovery import (
    ModelSpec,
    choose_compatible_007_model,
    parse_audit,
    parse_plan,
    rank_models_from_007,
)


class LiveHardeningTests(unittest.TestCase):
    def test_single_json_code_fence_is_losslessly_accepted(self):
        fenced = '```json\n{"plan":["node-00","node-02","node-01"]}\n```'
        self.assertEqual(parse_plan(fenced), ["node-00", "node-02", "node-01"])
        self.assertEqual(parse_audit('```json\n{"decision":"APPROVE"}\n```'), ("APPROVE", None))

    def test_prose_around_json_is_not_silently_extracted(self):
        text = 'Here is the answer: {"plan":["node-00"]}'
        self.assertIsNone(parse_plan(text))

    def test_rank_then_choose_first_008_compatible_model(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "suite.json"
            p.write_text(json.dumps({"models": [
                {"experiment_valid": True, "paired_packet_count": 4,
                 "paired_retrieved_minus_none_mean": 0.30,
                 "analysis": {"RETRIEVED": {"last_passing_level": 20}},
                 "model": {"model": "best007", "label": "best007"}},
                {"experiment_valid": True, "paired_packet_count": 4,
                 "paired_retrieved_minus_none_mean": 0.20,
                 "analysis": {"RETRIEVED": {"last_passing_level": 18}},
                 "model": {"model": "second007", "label": "second007"}},
            ]}))
            ranked = rank_models_from_007(p)
            self.assertEqual([m.model for m in ranked], ["best007", "second007"])
            allowed = {m.model: m for m in ranked}
            selected, attempts = choose_compatible_007_model(
                ranked,
                allowed,
                lambda spec: {"passed": spec.model == "second007", "models": {spec.label: {"passed": spec.model == "second007"}}},
            )
            self.assertEqual(selected.model, "second007")
            self.assertEqual([a["model"] for a in attempts], ["best007", "second007"])
            self.assertFalse(attempts[0]["passed"])
            self.assertTrue(attempts[1]["passed"])


if __name__ == "__main__":
    unittest.main()
