from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alien_lab.context_engine_run import (
    RunIdentity,
    prepare_run,
    read_evidence_envelope,
    validate_parent_unlock,
    write_evidence_envelope,
)
from alien_lab.context_engine_types import ContextCell


class ContextEngine0101RunIntegrityTests(unittest.TestCase):
    def _identity(self, **overrides) -> RunIdentity:
        payload = {
            "experiment": "010.1-context-engine-causal-attribution",
            "profile": "fixture",
            "system_version": "fixture-v1",
            "corpus_hash": "c" * 64,
            "ledger_hash": "l" * 64,
            "answer_model_identity": {"model": "fake", "digest": "d1"},
            "embedding_identity": {"model": "fake-embed", "digest": "e1"},
            "adapter_identities": {"RAGFLOW_FULL": {"pin": "v0.27.1"}},
            "answer_prompt_hash": "p" * 64,
            "composition_policy_hash": "f" * 64,
            "answer_context_utf8_bytes": 16384,
            "live": False,
        }
        payload.update(overrides)
        return RunIdentity(**payload)

    def test_parent_unlock_rejects_incomplete_or_wrong_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "unlock.json"
            base = {
                "parent_experiment": "010-computational-basis-atlas",
                "parent_run_identity_hash": "a" * 64,
                "parent_live_summary_sha256": "b" * 64,
                "terminal_cells": 4416,
                "parent_terminal_state": "DISCOVERY_COMPLETE",
                "0101_live_unlocked": True,
            }
            path.write_text(json.dumps(base), encoding="utf-8")
            self.assertEqual(validate_parent_unlock(path)["terminal_cells"], 4416)
            for key, value in (
                ("parent_experiment", "wrong"),
                ("terminal_cells", 4415),
                ("0101_live_unlocked", False),
                ("parent_run_identity_hash", "short"),
                ("parent_live_summary_sha256", "short"),
            ):
                bad = dict(base)
                bad[key] = value
                path.write_text(json.dumps(bad), encoding="utf-8")
                with self.assertRaises(ValueError, msg=key):
                    validate_parent_unlock(path)

    def test_prepare_run_rejects_identity_change_in_existing_directory(self) -> None:
        cell = ContextCell(cell_id="cell-1", order=0, stage="A", task_id="t", arm="MODEL_ONLY", plane="raw")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            identity = self._identity()
            prepare_run(root, identity, [cell])
            for changed in (
                self._identity(answer_context_utf8_bytes=16000),
                self._identity(answer_model_identity={"model": "different", "digest": "d2"}),
                self._identity(adapter_identities={"RAGFLOW_FULL": {"pin": "wrong"}}),
                self._identity(corpus_hash="x" * 64),
            ):
                with self.assertRaises(ValueError):
                    prepare_run(root, changed, [cell])

    def test_evidence_hash_detects_tamper_and_exact_resume_is_valid(self) -> None:
        cell = ContextCell(cell_id="cell-1", order=0, stage="A", task_id="t", arm="MODEL_ONLY", plane="raw")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cell.json"
            identity = self._identity()
            payload = {"run_identity_hash": identity.identity_hash(), "cell": cell.to_dict(), "outcome": {"score": 1}}
            first = write_evidence_envelope(path, payload)
            replay = read_evidence_envelope(path, expected_identity_hash=identity.identity_hash(), expected_cell=cell)
            self.assertEqual(first, replay)
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw["payload"]["outcome"]["score"] = 0
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(ValueError):
                read_evidence_envelope(path, expected_identity_hash=identity.identity_hash(), expected_cell=cell)

    def test_fixture_identity_cannot_be_live(self) -> None:
        with self.assertRaises(ValueError):
            self._identity(profile="fixture", live=True)


if __name__ == "__main__":
    unittest.main()
