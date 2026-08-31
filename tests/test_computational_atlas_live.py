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


class LiveExecutionTests(unittest.TestCase):
    def test_phase_c_oracle_and_semantic_compiler_reach_same_verified_result(self):
        from alien_lab.computational_atlas_live_ledger import build_phase_c_ledger
        from alien_lab.computational_atlas_live_runner import run_phase_c_cell
        from alien_lab.computational_atlas_providers import FakeProvider
        from alien_lab.computational_atlas_surfaces import oracle_unbound_ir
        from alien_lab.computational_atlas_worlds import build_worlds

        world = build_worlds(seed=20260910, count=1)[0]
        oracle_cell = next(cell for cell in build_phase_c_ledger() if cell.world_index == 0 and cell.representation == "R2_NATURAL" and cell.arm == "ORACLE_IR_BASIS")
        compiler_cell = next(cell for cell in build_phase_c_ledger() if cell.world_index == 0 and cell.representation == "R2_NATURAL" and cell.arm == "LOCAL_SEMANTIC_COMPILER_BASIS")
        oracle = run_phase_c_cell(oracle_cell, provider=None)
        fake = FakeProvider(model_id="fake", scripted=[oracle_unbound_ir(world).to_dict()])
        compiled = run_phase_c_cell(compiler_cell, provider=fake)
        self.assertEqual(oracle["score"], 1)
        self.assertEqual(compiled["score"], 1)
        self.assertEqual(compiled["result"], oracle["result"])
        self.assertEqual(compiled["model_calls"], 1)

    def test_phase_c_wrong_direct_answer_stays_zero_after_rescue(self):
        from alien_lab.computational_atlas_live_ledger import build_phase_c_ledger
        from alien_lab.computational_atlas_live_runner import rescue_phase_c_outcome, run_phase_c_cell
        from alien_lab.computational_atlas_providers import FakeProvider
        from alien_lab.computational_atlas_worlds import build_worlds

        cell = next(cell for cell in build_phase_c_ledger() if cell.world_index == 0 and cell.representation == "R2_NATURAL" and cell.arm == "MODEL_DIRECT")
        outcome = run_phase_c_cell(cell, provider=FakeProvider(model_id="fake", scripted=[{"result": ["wrong"]}]))
        world = build_worlds(seed=20260910, count=1)[0]
        rescue = rescue_phase_c_outcome(outcome, world)
        self.assertEqual(outcome["score"], 0)
        self.assertEqual(rescue["original_score"], 0)
        self.assertEqual(rescue["rescued_score"], 1)
        self.assertEqual(outcome["score"], 0)

    def test_phase_d_repair_uses_exactly_one_extra_call_and_can_recover(self):
        from alien_lab.computational_atlas_live_ledger import build_phase_d_ledger
        from alien_lab.computational_atlas_live_runner import run_phase_d_cell
        from alien_lab.computational_atlas_providers import FakeProvider
        from alien_lab.computational_atlas_surfaces import oracle_unbound_ir
        from alien_lab.computational_atlas_worlds import build_worlds

        world = build_worlds(seed=20260911, count=65)[64]
        cell = next(cell for cell in build_phase_d_ledger() if cell.world_index == 64 and cell.representation == "R3_PARAPHRASED" and cell.arm == "SCHEMA_VALIDATE_REPAIR")
        provider = FakeProvider(model_id="fake", scripted=[{"task_id": "", "operations": []}, oracle_unbound_ir(world).to_dict()])
        outcome = run_phase_d_cell(cell, provider=provider)
        self.assertEqual(outcome["score"], 1)
        self.assertEqual(outcome["model_calls"], 2)
        self.assertTrue(outcome["repair_used"])

    def test_phase_e_decoy_selection_is_routing_failure_but_oracle_route_succeeds(self):
        from alien_lab.computational_atlas_live_ledger import build_phase_e_ledger
        from alien_lab.computational_atlas_live_runner import run_phase_e_cell
        from alien_lab.computational_atlas_providers import FakeProvider

        oracle_cell = next(cell for cell in build_phase_e_ledger() if cell.world_index == 0 and cell.arm == "ORACLE_ROUTER" and cell.condition == "CATALOG_32")
        model_cell = next(cell for cell in build_phase_e_ledger() if cell.world_index == 0 and cell.arm == "LOCAL_MODEL_ROUTER" and cell.condition == "CATALOG_32")
        oracle = run_phase_e_cell(oracle_cell, provider=None)
        bad = run_phase_e_cell(model_cell, provider=FakeProvider(model_id="fake", scripted=[{"selected_tools": ["sequence_advisor"]}]))
        self.assertEqual(oracle["score"], 1)
        self.assertEqual(bad["score"], 0)
        self.assertEqual(bad["status"], "VALID_UNRESOLVED_ROUTING")
        self.assertGreater(bad["decoy_selection_rate"], 0)

    def test_phase_f_typed_handoff_creates_capability_unavailable_to_single_or_no_handoff(self):
        from alien_lab.computational_atlas_live_ledger import build_phase_f_ledger
        from alien_lab.computational_atlas_live_runner import run_phase_f_cell

        no_handoff_cell = next(cell for cell in build_phase_f_ledger() if cell.world_index == 0 and cell.arm == "ALL_ENGINES_NO_TYPED_HANDOFF")
        typed_cell = next(cell for cell in build_phase_f_ledger() if cell.world_index == 0 and cell.arm == "TYPED_COMPOSITION_VERIFIED")
        single_cell = next(cell for cell in build_phase_f_ledger() if cell.world_index == 0 and cell.arm == "SINGLE_G")
        no_handoff = run_phase_f_cell(no_handoff_cell, provider=None)
        typed = run_phase_f_cell(typed_cell, provider=None)
        single = run_phase_f_cell(single_cell, provider=None)
        self.assertEqual(no_handoff["score"], 0)
        self.assertEqual(single["score"], 0)
        self.assertEqual(typed["score"], 1)
        self.assertTrue(typed["measured_synergy_candidate"])


if __name__ == "__main__":
    unittest.main()
