from __future__ import annotations

import hashlib
import json
import unittest


class FrozenLiveContractTests(unittest.TestCase):
    def test_live_surfaces_do_not_leak_solver_labels(self):
        from alien_lab.computational_atlas_surfaces import render_live_surface
        from alien_lab.computational_atlas_worlds import CAPABILITY_NAMES, FAMILIES, build_worlds

        world = build_worlds(seed=20260910, count=1)[0]
        forbidden = set(CAPABILITY_NAMES.values()) | set(FAMILIES) | {"required_capabilities", "expected_result"}
        for representation in ("R1_STRUCTURED", "R2_NATURAL", "R3_PARAPHRASED", "R4_IMPLICIT", "R5_PERCEPTUAL"):
            rendered = render_live_surface(world, representation)
            text = json.dumps(rendered, sort_keys=True)
            for token in forbidden:
                self.assertNotIn(token, text)

    def test_oracle_unbound_ir_removes_engine_assignment_without_losing_operations(self):
        from alien_lab.computational_atlas_surfaces import oracle_unbound_ir
        from alien_lab.computational_atlas_worlds import build_worlds

        world = build_worlds(seed=20260912, count=70)[69]
        unbound = oracle_unbound_ir(world)
        self.assertEqual(len(unbound.operations), len(world.task_ir.operations))
        self.assertNotIn("required_capabilities", unbound.to_dict())
        for original, neutral in zip(world.task_ir.operations, unbound.operations):
            self.assertEqual(original.payload, neutral.payload)
            self.assertNotIn(original.capability, json.dumps(neutral.to_dict(), sort_keys=True))

    def test_r5_is_real_stable_png(self):
        from alien_lab.computational_atlas_surfaces import render_live_surface
        from alien_lab.computational_atlas_worlds import build_worlds

        world = build_worlds(seed=20260910, count=2)[1]
        first = render_live_surface(world, "R5_PERCEPTUAL")
        second = render_live_surface(world, "R5_PERCEPTUAL")
        self.assertEqual(first, second)
        raw = first.image_bytes()
        self.assertTrue(raw.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(first.sha256, hashlib.sha256(raw).hexdigest())

    def test_provider_contract_supports_fake_ollama_and_anthropic_shapes(self):
        from alien_lab.computational_atlas_providers import AnthropicMessagesProvider, FakeProvider, OllamaProvider
        from alien_lab.computational_atlas_live_types import ModelRequest

        request = ModelRequest(
            request_id="req-1",
            prompt="return json",
            json_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
            images=(),
            max_output_tokens=2048,
        )
        fake = FakeProvider(model_id="fake-010", scripted=[{"ok": True}])
        response = fake.complete(request)
        self.assertTrue(response.ok)
        self.assertEqual(response.parsed_json, {"ok": True})
        self.assertEqual(response.evidence_kind, "FAKE_MECHANICS_ONLY")
        self.assertEqual(OllamaProvider.default_path(), "/api/chat")
        self.assertEqual(AnthropicMessagesProvider.default_path(), "/v1/messages")

    def test_frozen_phase_ledgers_have_exact_counts(self):
        from alien_lab.computational_atlas_live_ledger import (
            build_phase_c_ledger,
            build_phase_d_ledger,
            build_phase_e_ledger,
            build_phase_f_ledger,
            build_phase_g_ledger,
            build_phase_h_ledger,
            build_phase_i_ledger,
        )

        counts = {
            "C": len(build_phase_c_ledger()),
            "D": len(build_phase_d_ledger()),
            "E": len(build_phase_e_ledger()),
            "F": len(build_phase_f_ledger()),
            "G": len(build_phase_g_ledger()),
            "H": len(build_phase_h_ledger()),
            "I": len(build_phase_i_ledger()),
        }
        self.assertEqual(counts, {"C": 3840, "D": 576, "E": 864, "F": 1152, "G": 864, "H": 120, "I": 288})
        self.assertEqual(sum(counts.values()), 7704)

    def test_phase_membership_is_frozen_and_not_performance_selected(self):
        from alien_lab.computational_atlas_live_ledger import build_phase_d_ledger, build_phase_e_ledger, build_phase_i_ledger

        d_worlds = sorted({cell.world_index for cell in build_phase_d_ledger()})
        e_worlds = sorted({cell.world_index for cell in build_phase_e_ledger()})
        self.assertEqual(d_worlds, list(range(64, 160)))
        self.assertEqual(e_worlds, list(range(0, 96)))
        self.assertTrue(all(cell.seed == 20260916 for cell in build_phase_i_ledger()))

    def test_phase_d_repair_budget_is_hard_capped_at_two_calls(self):
        from alien_lab.computational_atlas_semantics import semantic_call_budget

        self.assertEqual(semantic_call_budget("FREE_JSON"), 1)
        self.assertEqual(semantic_call_budget("SCHEMA_CONSTRAINED"), 1)
        self.assertEqual(semantic_call_budget("SCHEMA_VALIDATE_REPAIR"), 2)

    def test_phase_e_catalog_sizes_are_frozen_and_real_tools_identical(self):
        from alien_lab.computational_atlas_routing import catalog_for_condition, real_tool_catalog_bytes

        self.assertEqual(len(catalog_for_condition("CATALOG_8")), 8)
        self.assertEqual(len(catalog_for_condition("CATALOG_16")), 16)
        self.assertEqual(len(catalog_for_condition("CATALOG_32")), 32)
        self.assertEqual(real_tool_catalog_bytes("CATALOG_8"), real_tool_catalog_bytes("CATALOG_16"))
        self.assertEqual(real_tool_catalog_bytes("CATALOG_8"), real_tool_catalog_bytes("CATALOG_32"))

    def test_phase_f_worlds_require_real_typed_dataflow(self):
        from alien_lab.computational_atlas_composition import build_composition_worlds

        worlds = build_composition_worlds(seed=20260913, count=96)
        distribution = {2: 0, 3: 0, 4: 0, 5: 0}
        for world in worlds:
            distribution[len(world.required_capabilities)] += 1
            self.assertTrue(world.bindings)
            self.assertTrue(any(binding.producer_operation != binding.consumer_operation for binding in world.bindings))
        self.assertEqual(distribution, {2: 24, 3: 24, 4: 24, 5: 24})

    def test_phase_g_lineage_shape_is_frozen(self):
        from alien_lab.computational_atlas_accumulation import build_lineages

        lineages = build_lineages(seed=20260914, count=48)
        expected = ["NOVEL", "REPEAT", "PARAMETER_VARIATION", "REPRESENTATION_SHIFT", "ENVIRONMENT_DRIFT", "COMPOSITION_TRANSFER"]
        self.assertEqual(len(lineages), 48)
        for lineage in lineages:
            self.assertEqual([event.stage for event in lineage.events], expected)

    def test_phase_h_horizons_are_frozen(self):
        from alien_lab.computational_atlas_horizon import build_horizon_jobs

        jobs = build_horizon_jobs(seed=20260915)
        counts = {8: 0, 16: 0, 32: 0, 64: 0}
        for job in jobs:
            counts[job.horizon] += 1
            self.assertEqual(len(job.milestones), job.horizon)
        self.assertEqual(counts, {8: 10, 16: 10, 32: 10, 64: 10})

    def test_phase_i_distribution_and_tool_equivalence_are_frozen(self):
        from alien_lab.computational_atlas_frontier import build_phase_i_tasks, generic_tool_schema_bytes, velma_tool_schema_bytes

        tasks = build_phase_i_tasks(seed=20260916)
        kinds = {"semantic": 0, "composition": 0, "horizon": 0}
        for task in tasks:
            kinds[task.kind] += 1
        self.assertEqual(kinds, {"semantic": 12, "composition": 24, "horizon": 12})
        self.assertEqual(generic_tool_schema_bytes(), velma_tool_schema_bytes())


if __name__ == "__main__":
    unittest.main()
