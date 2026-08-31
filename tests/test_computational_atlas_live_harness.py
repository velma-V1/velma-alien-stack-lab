from __future__ import annotations

import tempfile
import unittest
import urllib.error
from pathlib import Path


class LiveEvidenceHarnessTests(unittest.TestCase):
    def _identity(self, *, system_version: str = "sys-a"):
        from alien_lab.computational_atlas_live_types import RunIdentity
        return RunIdentity(
            experiment="010-computational-basis-atlas",
            profile="live-cd-v1",
            system_version=system_version,
            provider_kind="fake",
            model_id="fake-010",
            endpoint="fake://experiment-010",
            generation_contract={"max_output_tokens": 2048, "transport_retries": 2},
            prompt_contract_hash="prompt-contract-test",
        )

    def test_cd_live_ledger_is_exact_and_cannot_advance_to_g_h_i(self):
        from alien_lab.computational_atlas_live_experiment import build_cd_ledger, supported_live_phases

        ledger = build_cd_ledger()
        self.assertEqual(len(ledger), 3840 + 576)
        self.assertEqual({cell.phase for cell in ledger}, {"C", "D"})
        self.assertEqual(supported_live_phases(), ("C", "D"))

    def test_output_directory_rejects_changed_system_identity(self):
        from alien_lab.computational_atlas_live_experiment import build_cd_ledger, prepare_live_run

        ledger = build_cd_ledger()[:1]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            prepare_live_run(output, self._identity(system_version="sys-a"), ledger)
            with self.assertRaisesRegex(ValueError, "LIVE_RUN_IDENTITY_MISMATCH"):
                prepare_live_run(output, self._identity(system_version="sys-b"), ledger)

    def test_valid_cell_evidence_is_hash_sealed_and_fake_evidence_stays_fake(self):
        from alien_lab.computational_atlas_live_experiment import run_live_cells
        from alien_lab.computational_atlas_live_ledger import build_phase_c_ledger
        from alien_lab.computational_atlas_providers import FakeProvider
        from alien_lab.computational_atlas_surfaces import oracle_unbound_ir
        from alien_lab.computational_atlas_worlds import build_worlds
        from alien_lab.computational_atlas_types import stable_hash

        world = build_worlds(seed=20260910, count=1)[0]
        cell = next(
            cell for cell in build_phase_c_ledger()
            if cell.world_index == 0
            and cell.representation == "R2_NATURAL"
            and cell.arm == "LOCAL_SEMANTIC_COMPILER_BASIS"
        )
        provider = FakeProvider(model_id="fake-010", scripted=[oracle_unbound_ir(world).to_dict()])
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_live_cells(
                cells=[cell],
                provider=provider,
                output_dir=Path(tmp),
                identity=self._identity(),
            )
            self.assertEqual(summary["terminal_cells"], 1)
            evidence_path = next((Path(tmp) / "cells").glob("*.json"))
            import json
            envelope = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(stable_hash(envelope["payload"]), envelope["sha256"])
            self.assertEqual(envelope["payload"]["outcome"]["evidence_kind"], "FAKE_MECHANICS_ONLY")
            self.assertNotEqual(envelope["payload"]["outcome"]["evidence_kind"], "LIVE_MODEL_EVIDENCE")

    def test_transport_retry_accounting_records_two_retries_before_invalid_transport(self):
        from alien_lab.computational_atlas_live_types import ModelRequest
        from alien_lab.computational_atlas_providers import OllamaProvider

        attempts = {"count": 0}

        def failing_transport(request, timeout):
            del request, timeout
            attempts["count"] += 1
            raise urllib.error.URLError("offline")

        provider = OllamaProvider(
            model_id="fake-local",
            endpoint="http://127.0.0.1:11434",
            transport=failing_transport,
        )
        response = provider.complete(ModelRequest(request_id="retry-test", prompt="{}"))
        self.assertFalse(response.ok)
        self.assertEqual(response.error_kind, "TRANSPORT")
        self.assertEqual(attempts["count"], 3)
        self.assertEqual(response.transport_retries, 2)


if __name__ == "__main__":
    unittest.main()
