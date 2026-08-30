from __future__ import annotations

import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path


class LiveScientificSelfAttackTests(unittest.TestCase):
    @staticmethod
    def _identity(*, context_limit: int = 8192):
        from alien_lab.computational_atlas_live_types import RunIdentity

        return RunIdentity(
            experiment="010-computational-basis-atlas",
            profile="live-cd-v1",
            system_version="scientific-self-attack",
            provider_kind="ollama",
            model_id="local-test",
            endpoint="http://127.0.0.1:11434",
            generation_contract={
                "max_output_tokens": 2048,
                "transport_retries": 2,
                "context_limit": context_limit,
                "task_specific_tuning": False,
            },
            prompt_contract_hash="scientific-self-attack",
            model_digest="digest-a",
            provider_version="0.12.6",
        )

    @staticmethod
    def _oracle_cell():
        from alien_lab.computational_atlas_live_ledger import build_phase_c_ledger

        return next(
            cell for cell in build_phase_c_ledger()
            if cell.world_index == 0
            and cell.representation == "R2_NATURAL"
            and cell.arm == "ORACLE_IR_BASIS"
        )

    @staticmethod
    def _r5_cell(arm: str):
        from alien_lab.computational_atlas_live_ledger import build_phase_c_ledger

        return next(
            cell for cell in build_phase_c_ledger()
            if cell.world_index == 0
            and cell.representation == "R5_PERCEPTUAL"
            and cell.arm == arm
        )

    def test_ollama_request_enforces_configured_context_limit(self):
        from alien_lab.computational_atlas_live_types import ModelRequest
        from alien_lab.computational_atlas_providers import OllamaProvider

        captured = {}

        def transport(request, timeout):
            del timeout
            captured.update(json.loads(request.data.decode("utf-8")))
            return json.dumps({
                "message": {"content": "{}"},
                "done_reason": "stop",
                "prompt_eval_count": 1,
                "eval_count": 1,
            }).encode("utf-8")

        provider = OllamaProvider(
            model_id="local-test",
            endpoint="http://127.0.0.1:11434",
            context_limit=8192,
            transport=transport,
        )
        response = provider.complete(ModelRequest(request_id="ctx", prompt="{}"))

        self.assertTrue(response.ok)
        self.assertEqual(captured["options"]["num_ctx"], 8192)

    def test_live_run_rejects_runtime_context_different_from_sealed_identity(self):
        from alien_lab.computational_atlas_live_experiment import run_live_cells

        class Provider:
            provider_kind = "ollama"
            model_id = "local-test"
            endpoint = "http://127.0.0.1:11434"
            supports_structured_output = True
            supports_images = True
            transport_retries_total = 0
            context_limit = 4096

            def server_version(self):
                return "0.12.6"

            def model_digest(self):
                return "digest-a"

            def model_capabilities(self):
                return ("completion", "vision")

            def complete(self, request):  # pragma: no cover
                raise AssertionError(f"unexpected model call: {request.request_id}")

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "PROVIDER_CONTEXT_LIMIT_MISMATCH"):
                run_live_cells(
                    cells=[self._oracle_cell()],
                    provider=Provider(),
                    output_dir=Path(tmp),
                    identity=self._identity(context_limit=8192),
                )

    def test_r5_unsupported_modality_is_valid_perception_failure_for_both_model_arms(self):
        from alien_lab.computational_atlas_live_runner import run_phase_c_cell
        from alien_lab.computational_atlas_live_types import ModelResponse

        class NoVisionProvider:
            supports_structured_output = True

            def complete(self, request):
                self.last_request = request
                return ModelResponse(
                    ok=False,
                    text="",
                    model_calls=1,
                    error_kind="UNSUPPORTED_MODALITY",
                    error="model does not support images",
                )

        for arm in ("MODEL_DIRECT", "LOCAL_SEMANTIC_COMPILER_BASIS"):
            with self.subTest(arm=arm):
                outcome = run_phase_c_cell(self._r5_cell(arm), NoVisionProvider())
                self.assertEqual(outcome["status"], "VALID_UNRESOLVED_PERCEPTION")
                self.assertEqual(outcome["score"], 0)

    def test_ollama_http_400_image_rejection_is_not_retried_as_transport_outage(self):
        from alien_lab.computational_atlas_live_types import LiveImage, ModelRequest
        from alien_lab.computational_atlas_providers import OllamaProvider

        attempts = {"count": 0}

        def transport(request, timeout):
            del timeout
            attempts["count"] += 1
            body = io.BytesIO(json.dumps({"error": "this model does not support images"}).encode("utf-8"))
            raise urllib.error.HTTPError(request.full_url, 400, "Bad Request", hdrs=None, fp=body)

        provider = OllamaProvider(
            model_id="local-test",
            endpoint="http://127.0.0.1:11434",
            context_limit=8192,
            transport=transport,
        )
        response = provider.complete(ModelRequest(
            request_id="vision",
            prompt="read image",
            images=(LiveImage(media_type="image/png", base64_data="AA==", sha256="x"),),
        ))

        self.assertFalse(response.ok)
        self.assertEqual(response.error_kind, "UNSUPPORTED_MODALITY")
        self.assertEqual(attempts["count"], 1)
        self.assertEqual(response.transport_retries, 0)

    def test_r5_rescue_localizes_perception_without_overwriting_original(self):
        from alien_lab.computational_atlas_live_runner import rescue_phase_c_outcome
        from alien_lab.computational_atlas_worlds import build_worlds

        original = {
            "status": "VALID_UNRESOLVED_PERCEPTION",
            "score": 0,
            "verified": False,
            "result": None,
        }
        rescue = rescue_phase_c_outcome(original, build_worlds(seed=20260910, count=1)[0])

        self.assertEqual(rescue["localized_bottleneck"], "PERCEPTION")
        self.assertEqual(rescue["original_score"], 0)
        self.assertEqual(original["score"], 0)

    def test_rescue_does_not_claim_collapsed_execution_and_verifier_rungs_are_distinguishable(self):
        from alien_lab.computational_atlas_live_runner import rescue_phase_c_outcome
        from alien_lab.computational_atlas_worlds import build_worlds

        original = {
            "status": "VALID_UNRESOLVED_SEMANTIC",
            "score": 0,
            "verified": False,
            "result": None,
        }
        rescue = rescue_phase_c_outcome(original, build_worlds(seed=20260910, count=1)[0])
        stages = {stage["stage"]: stage for stage in rescue["stages"]}

        self.assertFalse(stages["ORACLE_EXECUTION"]["distinguishable"])
        self.assertFalse(stages["VERIFIER_DISCRIMINATION"]["distinguishable"])


if __name__ == "__main__":
    unittest.main()
