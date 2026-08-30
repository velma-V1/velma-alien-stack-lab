from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


class LiveConfigurationPreflightTests(unittest.TestCase):
    @staticmethod
    def _identity(*, context_limit=32768, provider_version="0.12.6"):
        from alien_lab.computational_atlas_live_types import RunIdentity

        return RunIdentity(
            experiment="010-computational-basis-atlas",
            profile="live-cd-v1",
            system_version="config-preflight-test",
            provider_kind="ollama",
            model_id="local-test",
            endpoint="http://127.0.0.1:11434",
            generation_contract={
                "max_output_tokens": 2048,
                "transport_retries": 2,
                "context_limit": context_limit,
                "task_specific_tuning": False,
            },
            prompt_contract_hash="config-preflight-test",
            provider_version=provider_version,
        )

    @staticmethod
    def _provider(actual_version="0.12.6"):
        class Provider:
            provider_kind = "ollama"
            model_id = "local-test"
            endpoint = "http://127.0.0.1:11434"
            supports_structured_output = True
            transport_retries_total = 0

            def server_version(self):
                return actual_version

            def complete(self, request):  # pragma: no cover - oracle test cell must not call the model
                raise AssertionError(f"unexpected model call: {request.request_id}")

        return Provider()

    @staticmethod
    def _oracle_cell():
        from alien_lab.computational_atlas_live_ledger import build_phase_c_ledger

        return next(
            cell for cell in build_phase_c_ledger()
            if cell.world_index == 0
            and cell.representation == "R2_NATURAL"
            and cell.arm == "ORACLE_IR_BASIS"
        )

    def _run(self, identity, provider):
        from alien_lab.computational_atlas_live_experiment import run_live_cells

        with tempfile.TemporaryDirectory() as tmp:
            return run_live_cells(
                cells=[self._oracle_cell()],
                provider=provider,
                output_dir=Path(tmp),
                identity=identity,
            )

    def test_live_ollama_requires_sealed_context_limit(self):
        with self.assertRaisesRegex(ValueError, "LIVE_CONTEXT_LIMIT_REQUIRED"):
            self._run(self._identity(context_limit=None), self._provider())

    def test_live_ollama_requires_sealed_provider_version(self):
        with self.assertRaisesRegex(ValueError, "LIVE_PROVIDER_VERSION_REQUIRED"):
            self._run(self._identity(provider_version=None), self._provider())

    def test_live_ollama_rejects_sealed_version_that_differs_from_actual_server(self):
        with self.assertRaisesRegex(ValueError, "PROVIDER_VERSION_MISMATCH"):
            self._run(self._identity(provider_version="0.12.5"), self._provider(actual_version="0.12.6"))

    def test_live_ollama_rejects_server_too_old_for_json_schema_structured_output(self):
        with self.assertRaisesRegex(ValueError, "STRUCTURED_OUTPUT_VERSION_UNSUPPORTED"):
            self._run(self._identity(provider_version="0.4.9"), self._provider(actual_version="0.4.9"))


if __name__ == "__main__":
    unittest.main()
