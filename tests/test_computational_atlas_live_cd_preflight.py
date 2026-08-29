from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path


class CDPreflightRegressionTests(unittest.TestCase):
    @staticmethod
    def _d_cell(arm: str, representation: str = "R3_PARAPHRASED"):
        from alien_lab.computational_atlas_live_ledger import build_phase_d_ledger

        return next(
            cell
            for cell in build_phase_d_ledger()
            if cell.world_index == 64 and cell.representation == representation and cell.arm == arm
        )

    @staticmethod
    def _identity(*, provider_kind: str = "fake", model_id: str = "fake-010", endpoint: str = "fake://experiment-010"):
        from alien_lab.computational_atlas_live_types import RunIdentity

        return RunIdentity(
            experiment="010-computational-basis-atlas",
            profile="live-cd-v1",
            system_version="preflight-test",
            provider_kind=provider_kind,
            model_id=model_id,
            endpoint=endpoint,
            generation_contract={"max_output_tokens": 2048, "transport_retries": 2},
            prompt_contract_hash="preflight-test-contract",
        )

    def test_d_valid_executable_but_wrong_ir_does_not_receive_repair_call(self):
        from alien_lab.computational_atlas_live_runner import run_phase_d_cell
        from alien_lab.computational_atlas_providers import FakeProvider
        from alien_lab.computational_atlas_surfaces import oracle_unbound_ir
        from alien_lab.computational_atlas_worlds import build_worlds

        world = build_worlds(seed=20260911, count=65)[64]
        wrong = oracle_unbound_ir(world).to_dict()
        payload = wrong["operations"][0]["payload"]
        payload["edges"] = [[payload["start"], payload["goal"]]]
        provider = FakeProvider(
            model_id="fake-010",
            scripted=[wrong, oracle_unbound_ir(world).to_dict()],
        )

        outcome = run_phase_d_cell(self._d_cell("SCHEMA_VALIDATE_REPAIR"), provider)

        self.assertEqual(outcome["score"], 0)
        self.assertEqual(outcome["model_calls"], 1)
        self.assertFalse(outcome["repair_used"])

    def test_free_and_constrained_d_arms_read_identical_fenced_json_equally(self):
        from alien_lab.computational_atlas_live_runner import run_phase_d_cell
        from alien_lab.computational_atlas_providers import OllamaProvider
        from alien_lab.computational_atlas_surfaces import oracle_unbound_ir
        from alien_lab.computational_atlas_worlds import build_worlds

        world = build_worlds(seed=20260911, count=65)[64]
        fenced = "```json\n" + json.dumps(oracle_unbound_ir(world).to_dict(), sort_keys=True) + "\n```"

        def transport(request, timeout):
            del request, timeout
            return json.dumps({
                "message": {"content": fenced},
                "done_reason": "stop",
                "prompt_eval_count": 1,
                "eval_count": 1,
            }).encode("utf-8")

        free_provider = OllamaProvider(model_id="local-test", endpoint="http://127.0.0.1:11434", transport=transport)
        constrained_provider = OllamaProvider(model_id="local-test", endpoint="http://127.0.0.1:11434", transport=transport)

        free = run_phase_d_cell(self._d_cell("FREE_JSON"), free_provider)
        constrained = run_phase_d_cell(self._d_cell("SCHEMA_CONSTRAINED"), constrained_provider)

        self.assertEqual(free["score"], 1)
        self.assertEqual(constrained["score"], 1)

    def test_constrained_d_arm_rejects_provider_without_structured_output_support(self):
        from alien_lab.computational_atlas_live_runner import run_phase_d_cell
        from alien_lab.computational_atlas_live_types import ModelResponse
        from alien_lab.computational_atlas_surfaces import oracle_unbound_ir
        from alien_lab.computational_atlas_worlds import build_worlds

        world = build_worlds(seed=20260911, count=65)[64]
        ir = oracle_unbound_ir(world).to_dict()

        class NoStructuredProvider:
            model_id = "no-structured"
            endpoint = "test://no-structured"
            provider_kind = "test"
            supports_structured_output = False
            transport_retries_total = 0
            calls = 0

            def complete(self, request):
                del request
                self.calls += 1
                return ModelResponse(ok=True, text=json.dumps(ir), parsed_json=ir, model_calls=1)

        provider = NoStructuredProvider()
        outcome = run_phase_d_cell(self._d_cell("SCHEMA_CONSTRAINED"), provider)

        self.assertIsNone(outcome["score"])
        self.assertEqual(outcome.get("error"), "STRUCTURED_OUTPUT_UNSUPPORTED")
        self.assertEqual(provider.calls, 0)

    def test_repair_transport_failure_is_invalid_infrastructure(self):
        from alien_lab.computational_atlas_live_runner import run_phase_d_cell
        from alien_lab.computational_atlas_live_types import ModelResponse

        invalid = {"task_id": "", "operations": []}

        class RepairTransportProvider:
            model_id = "repair-transport"
            endpoint = "test://repair-transport"
            provider_kind = "test"
            supports_structured_output = True
            transport_retries_total = 0

            def __init__(self):
                self.calls = 0

            def complete(self, request):
                del request
                self.calls += 1
                if self.calls == 1:
                    return ModelResponse(ok=True, text=json.dumps(invalid), parsed_json=invalid, model_calls=1)
                return ModelResponse(ok=False, text="", model_calls=1, error_kind="TRANSPORT", error="offline")

        outcome = run_phase_d_cell(self._d_cell("SCHEMA_VALIDATE_REPAIR"), RepairTransportProvider())

        self.assertIsNone(outcome["score"])
        self.assertEqual(outcome["status"], "INVALID_INFRASTRUCTURE")

    def test_phase_d_emits_all_frozen_interface_diagnostics(self):
        from alien_lab.computational_atlas_live_runner import run_phase_d_cell
        from alien_lab.computational_atlas_providers import FakeProvider
        from alien_lab.computational_atlas_surfaces import oracle_unbound_ir
        from alien_lab.computational_atlas_worlds import build_worlds

        world = build_worlds(seed=20260911, count=65)[64]
        provider = FakeProvider(model_id="fake-010", scripted=[oracle_unbound_ir(world).to_dict()])
        outcome = run_phase_d_cell(self._d_cell("FREE_JSON"), provider)

        for field in ("syntax_valid", "schema_valid", "semantic_executable", "end_to_end_verified"):
            self.assertIn(field, outcome)
            self.assertTrue(outcome[field])

    def test_intent_vocabulary_is_disclosed_as_interface_contract(self):
        from alien_lab.computational_atlas_semantics import SEMANTIC_SYSTEM_PROMPT
        from alien_lab.computational_atlas_surfaces import INTENT_BY_CAPABILITY, task_ir_json_schema

        intent_spec = task_ir_json_schema()["properties"]["operations"]["items"]["properties"]["intent"]
        self.assertIn("enum", intent_spec)
        expected = set(INTENT_BY_CAPABILITY.values())
        self.assertEqual(set(intent_spec["enum"]), expected)
        for intent in expected:
            self.assertIn(intent, SEMANTIC_SYSTEM_PROMPT)

    def test_r5_contains_real_glyph_geometry_not_sparse_bit_rows(self):
        from PIL import Image
        from alien_lab.computational_atlas_surfaces import render_live_surface
        from alien_lab.computational_atlas_worlds import build_worlds

        world = build_worlds(seed=20260910, count=1)[0]
        raw = render_live_surface(world, "R5_PERCEPTUAL").image_bytes()
        image = Image.open(io.BytesIO(raw)).convert("L")
        pixels = image.load()
        width, height = image.size
        longest_vertical_ink_run = 0
        for x in range(width):
            run = 0
            for y in range(height):
                if pixels[x, y] < 128:
                    run += 1
                    longest_vertical_ink_run = max(longest_vertical_ink_run, run)
                else:
                    run = 0
        self.assertGreaterEqual(longest_vertical_ink_run, 5)

    def test_r5_render_source_is_leakage_checked_across_all_worlds(self):
        from alien_lab.computational_atlas_surfaces import _text_rows
        from alien_lab.computational_atlas_worlds import CAPABILITY_NAMES, FAMILIES, build_worlds

        forbidden = set(CAPABILITY_NAMES.values()) | set(FAMILIES) | {
            "required_capabilities",
            "expected_result",
        }
        for world in build_worlds(seed=20260910, count=192):
            rendered_source = "CASE " + world.world_id + "\n" + "\n".join(
                f"{index + 1}. {row}" for index, row in enumerate(_text_rows(world))
            )
            for token in forbidden:
                self.assertNotIn(token, rendered_source)

    def test_outside_basis_recognizer_status_is_missing_capability_not_parser_order(self):
        from alien_lab.computational_atlas_live_ledger import build_phase_c_ledger
        from alien_lab.computational_atlas_live_runner import run_phase_c_cell

        cell = next(
            cell
            for cell in build_phase_c_ledger()
            if cell.world_index == 184
            and cell.representation == "R2_NATURAL"
            and cell.arm == "DETERMINISTIC_RECOGNIZER_BASIS"
        )
        outcome = run_phase_c_cell(cell, provider=None)
        self.assertEqual(outcome["status"], "VALID_UNRESOLVED_MISSING_CAPABILITY")

    def test_deterministic_recognizer_does_not_copy_sealed_oracle_metadata(self):
        from alien_lab.computational_atlas_live_runner import _deterministic_recognize
        from alien_lab.computational_atlas_worlds import build_worlds

        world = build_worlds(seed=20260910, count=1)[0]
        recognized = _deterministic_recognize(world, "R1_STRUCTURED")
        self.assertIsNotNone(recognized)
        self.assertNotEqual(recognized.task_id, world.task_ir.task_id)
        self.assertEqual(recognized.verification, ())

    def test_runtime_provider_must_match_sealed_run_identity(self):
        from alien_lab.computational_atlas_live_experiment import run_live_cells
        from alien_lab.computational_atlas_live_ledger import build_phase_c_ledger
        from alien_lab.computational_atlas_providers import FakeProvider

        cell = next(cell for cell in build_phase_c_ledger() if cell.arm == "ORACLE_IR_BASIS")
        provider = FakeProvider(model_id="fake-010", scripted=[])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "PROVIDER_IDENTITY_MISMATCH"):
                run_live_cells(
                    cells=[cell],
                    provider=provider,
                    output_dir=Path(tmp),
                    identity=self._identity(provider_kind="ollama"),
                )

    def test_fixture_run_is_explicitly_non_live_even_when_all_cells_terminal(self):
        from alien_lab.computational_atlas_live_experiment import run_live_cells
        from alien_lab.computational_atlas_live_ledger import build_phase_c_ledger
        from alien_lab.computational_atlas_providers import FakeProvider
        from alien_lab.computational_atlas_surfaces import oracle_unbound_ir
        from alien_lab.computational_atlas_worlds import build_worlds

        world = build_worlds(seed=20260910, count=1)[0]
        cell = next(
            cell
            for cell in build_phase_c_ledger()
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
        self.assertIs(summary.get("live_model_evidence"), False)
        self.assertEqual(summary["conclusion"], "NON_LIVE_FIXTURE_RUN")

    def test_live_summary_reports_arm_representation_and_paired_semantic_tax(self):
        from alien_lab.computational_atlas_live_experiment import run_live_cells
        from alien_lab.computational_atlas_live_ledger import build_phase_c_ledger
        from alien_lab.computational_atlas_providers import FakeProvider
        from alien_lab.computational_atlas_surfaces import oracle_unbound_ir
        from alien_lab.computational_atlas_worlds import build_worlds

        world = build_worlds(seed=20260910, count=1)[0]
        local = next(
            cell for cell in build_phase_c_ledger()
            if cell.world_index == 0 and cell.representation == "R2_NATURAL" and cell.arm == "LOCAL_SEMANTIC_COMPILER_BASIS"
        )
        oracle = next(
            cell for cell in build_phase_c_ledger()
            if cell.world_index == 0 and cell.representation == "R2_NATURAL" and cell.arm == "ORACLE_IR_BASIS"
        )
        provider = FakeProvider(model_id="fake-010", scripted=[oracle_unbound_ir(world).to_dict()])
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_live_cells(
                cells=[local, oracle],
                provider=provider,
                output_dir=Path(tmp),
                identity=self._identity(),
            )

        self.assertIn("by_arm", summary)
        self.assertIn("LOCAL_SEMANTIC_COMPILER_BASIS", summary["by_arm"])
        self.assertIn("by_representation", summary)
        self.assertIn("R2_NATURAL", summary["by_representation"])
        self.assertIn("semantic_formalization_tax", summary)
        self.assertEqual(summary["semantic_formalization_tax"]["paired_cells"], 1)
        self.assertEqual(summary["semantic_formalization_tax"]["mean_tax"], 0.0)

    def test_rescue_ladder_exposes_all_frozen_stages_without_overwriting_original(self):
        from alien_lab.computational_atlas_live_runner import rescue_phase_c_outcome
        from alien_lab.computational_atlas_worlds import build_worlds

        world = build_worlds(seed=20260910, count=1)[0]
        original = {
            "status": "VALID_UNRESOLVED_SEMANTIC",
            "score": 0,
            "verified": False,
            "result": None,
        }
        rescue = rescue_phase_c_outcome(original, world)
        self.assertEqual(rescue["original_score"], 0)
        self.assertEqual(
            [stage["stage"] for stage in rescue["stages"]],
            [
                "ORIGINAL",
                "ORACLE_TASK_IR",
                "ORACLE_DECOMPOSITION",
                "ORACLE_ROUTING",
                "ORACLE_ENGINE_OUTPUTS",
                "ORACLE_TYPED_HANDOFF",
                "ORACLE_EXECUTION",
                "VERIFIER_DISCRIMINATION",
            ],
        )
        self.assertEqual(original["score"], 0)

    def test_unresolved_local_semantic_cell_persists_separate_automatic_rescue(self):
        from alien_lab.computational_atlas_live_experiment import run_live_cells
        from alien_lab.computational_atlas_live_ledger import build_phase_c_ledger
        from alien_lab.computational_atlas_providers import FakeProvider

        cell = next(
            cell for cell in build_phase_c_ledger()
            if cell.world_index == 0
            and cell.representation == "R2_NATURAL"
            and cell.arm == "LOCAL_SEMANTIC_COMPILER_BASIS"
        )
        provider = FakeProvider(model_id="fake-010", scripted=["not-json"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = run_live_cells(
                cells=[cell],
                provider=provider,
                output_dir=root,
                identity=self._identity(),
            )
            original_path = next((root / "cells").glob("*.json"))
            original = json.loads(original_path.read_text(encoding="utf-8"))
            rescues = list((root / "rescues").glob("*.json")) if (root / "rescues").exists() else []

        self.assertEqual(original["payload"]["outcome"]["score"], 0)
        self.assertEqual(summary.get("rescue_cells"), 1)
        self.assertEqual(len(rescues), 1)


if __name__ == "__main__":
    unittest.main()
