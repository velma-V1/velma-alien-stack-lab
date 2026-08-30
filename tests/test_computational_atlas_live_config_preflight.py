from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class LiveConfigurationPreflightTests(unittest.TestCase):
    @staticmethod
    def _identity(*, context_limit=32768, provider_version="0.12.6", model_digest="digest-a"):
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
            model_digest=model_digest,
            provider_version=provider_version,
        )

    @staticmethod
    def _provider(actual_version="0.12.6", context_limit=32768, actual_digest="digest-a", capabilities=("completion", "vision")):
        class Provider:
            provider_kind = "ollama"
            model_id = "local-test"
            endpoint = "http://127.0.0.1:11434"
            supports_structured_output = True
            supports_images = "vision" in capabilities
            transport_retries_total = 0

            def __init__(self):
                self.context_limit = context_limit

            def server_version(self):
                return actual_version

            def model_digest(self):
                return actual_digest

            def model_capabilities(self):
                return tuple(capabilities)

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

    def test_live_ollama_requires_sealed_model_digest_when_server_exposes_it(self):
        with self.assertRaisesRegex(ValueError, "LIVE_MODEL_DIGEST_REQUIRED"):
            self._run(self._identity(model_digest=None), self._provider())

    def test_live_ollama_rejects_model_digest_mismatch(self):
        with self.assertRaisesRegex(ValueError, "MODEL_DIGEST_MISMATCH"):
            self._run(self._identity(model_digest="digest-a"), self._provider(actual_digest="digest-b"))

    def test_live_ollama_provider_context_must_equal_sealed_context(self):
        with self.assertRaisesRegex(ValueError, "PROVIDER_CONTEXT_LIMIT_MISMATCH"):
            self._run(self._identity(context_limit=32768), self._provider(context_limit=4096))

    def test_ollama_request_enforces_configured_num_ctx(self):
        from alien_lab.computational_atlas_live_types import ModelRequest
        from alien_lab.computational_atlas_providers import OllamaProvider

        captured = {}

        def transport(request, timeout):
            del timeout
            captured.update(json.loads(request.data.decode("utf-8")))
            return json.dumps({"message": {"content": "{}"}, "done_reason": "stop"}).encode("utf-8")

        provider = OllamaProvider(
            model_id="local-test",
            endpoint="http://127.0.0.1:11434",
            transport=transport,
        )
        provider.context_limit = 32768
        provider.complete(ModelRequest(request_id="ctx", prompt="return json"))
        self.assertEqual(captured["options"].get("num_ctx"), 32768)

    def test_r5_without_vision_is_valid_capability_failure_not_infrastructure(self):
        from alien_lab.computational_atlas_live_ledger import build_phase_c_ledger
        from alien_lab.computational_atlas_live_runner import run_phase_c_cell

        class NoVisionProvider:
            provider_kind = "test"
            model_id = "text-only"
            endpoint = "test://text-only"
            supports_structured_output = True
            supports_images = False
            transport_retries_total = 0

            def complete(self, request):  # pragma: no cover - modality must be rejected before inference
                raise AssertionError(f"unsupported image request reached provider: {request.request_id}")

        for arm in ("MODEL_DIRECT", "LOCAL_SEMANTIC_COMPILER_BASIS"):
            cell = next(
                cell for cell in build_phase_c_ledger()
                if cell.world_index == 0
                and cell.representation == "R5_PERCEPTUAL"
                and cell.arm == arm
            )
            outcome = run_phase_c_cell(cell, NoVisionProvider())
            self.assertEqual(outcome["score"], 0)
            self.assertEqual(outcome["status"], "VALID_UNRESOLVED_PERCEPTION")
            self.assertEqual(outcome["error_kind"], "UNSUPPORTED_MODALITY")
            self.assertTrue(outcome["unsupported_modality"])
            self.assertEqual(outcome["model_calls"], 0)


if __name__ == "__main__":
    unittest.main()
