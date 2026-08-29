from __future__ import annotations

import unittest


class AccumulationExecutionTests(unittest.TestCase):
    def test_verified_executable_capability_reuses_repeat_with_zero_second_model_call(self):
        from alien_lab.computational_atlas_live_ledger import build_phase_g_ledger
        from alien_lab.computational_atlas_live_runner import CapabilityRuntimeState, run_phase_g_cell
        from alien_lab.computational_atlas_providers import FakeProvider
        from alien_lab.computational_atlas_surfaces import oracle_unbound_ir
        from alien_lab.computational_atlas_worlds import build_worlds

        world = build_worlds(seed=20260914, count=1)[0]
        cells = [cell for cell in build_phase_g_ledger() if cell.lineage_index == 0 and cell.arm == "VERIFIED_EXECUTABLE_CAPABILITY"]
        novel = next(cell for cell in cells if cell.stage == "NOVEL")
        repeat = next(cell for cell in cells if cell.stage == "REPEAT")
        provider = FakeProvider(model_id="fake", scripted=[oracle_unbound_ir(world).to_dict()])
        state = CapabilityRuntimeState()
        first = run_phase_g_cell(novel, provider=provider, state=state)
        second = run_phase_g_cell(repeat, provider=provider, state=state)
        self.assertEqual(first["score"], 1)
        self.assertEqual(first["model_calls"], 1)
        self.assertEqual(second["score"], 1)
        self.assertEqual(second["model_calls"], 0)
        self.assertTrue(second["reused_executable_capability"])
        self.assertEqual(len(state.packages), 1)

    def test_unverified_work_never_creates_executable_package(self):
        from alien_lab.computational_atlas_live_ledger import build_phase_g_ledger
        from alien_lab.computational_atlas_live_runner import CapabilityRuntimeState, run_phase_g_cell
        from alien_lab.computational_atlas_providers import FakeProvider

        novel = next(cell for cell in build_phase_g_ledger() if cell.lineage_index == 0 and cell.arm == "VERIFIED_EXECUTABLE_CAPABILITY" and cell.stage == "NOVEL")
        state = CapabilityRuntimeState()
        outcome = run_phase_g_cell(novel, provider=FakeProvider(model_id="fake", scripted=[{"task_id": "", "operations": []}]), state=state)
        self.assertEqual(outcome["score"], 0)
        self.assertEqual(state.packages, {})

    def test_text_memory_never_bypasses_semantic_model_call(self):
        from alien_lab.computational_atlas_live_ledger import build_phase_g_ledger
        from alien_lab.computational_atlas_live_runner import CapabilityRuntimeState, run_phase_g_cell
        from alien_lab.computational_atlas_providers import FakeProvider
        from alien_lab.computational_atlas_surfaces import oracle_unbound_ir
        from alien_lab.computational_atlas_worlds import build_worlds

        world = build_worlds(seed=20260914, count=1)[0]
        cells = [cell for cell in build_phase_g_ledger() if cell.lineage_index == 0 and cell.arm == "TEXT_MEMORY"]
        novel = next(cell for cell in cells if cell.stage == "NOVEL")
        repeat = next(cell for cell in cells if cell.stage == "REPEAT")
        provider = FakeProvider(model_id="fake", scripted=[oracle_unbound_ir(world).to_dict(), oracle_unbound_ir(world).to_dict()])
        state = CapabilityRuntimeState()
        first = run_phase_g_cell(novel, provider=provider, state=state)
        second = run_phase_g_cell(repeat, provider=provider, state=state)
        self.assertEqual(first["score"], 1)
        self.assertEqual(second["score"], 1)
        self.assertEqual(first["model_calls"], 1)
        self.assertEqual(second["model_calls"], 1)
        self.assertFalse(second["reused_executable_capability"])


class HorizonExecutionTests(unittest.TestCase):
    def test_velma_full_scores_every_milestone_and_has_authoritative_verifier_coverage(self):
        from alien_lab.computational_atlas_live_ledger import build_phase_h_ledger
        from alien_lab.computational_atlas_live_runner import run_phase_h_cell

        cell = next(cell for cell in build_phase_h_ledger() if cell.world_index == 0 and cell.arm == "VELMA_FULL")
        outcome = run_phase_h_cell(cell, provider=None)
        self.assertEqual(outcome["score"], 1)
        self.assertEqual(outcome["milestones_correct"], 8)
        self.assertEqual(outcome["milestones_total"], 8)
        self.assertEqual(outcome["verifier_coverage"], 1.0)
        self.assertEqual(outcome["model_calls"], 0)

    def test_model_direct_long_wrong_final_trace_is_not_rescued_by_final_only_answer(self):
        from alien_lab.computational_atlas_live_ledger import build_phase_h_ledger
        from alien_lab.computational_atlas_live_runner import run_phase_h_cell
        from alien_lab.computational_atlas_providers import FakeProvider

        cell = next(cell for cell in build_phase_h_ledger() if cell.world_index == 0 and cell.arm == "MODEL_DIRECT_LONG")
        outcome = run_phase_h_cell(cell, provider=FakeProvider(model_id="fake", scripted=[{"states": [0] * 8}]))
        self.assertEqual(outcome["score"], 0)
        self.assertLess(outcome["milestones_correct"], 8)
        self.assertIsNotNone(outcome["first_error"])


class FrontierCalibrationExecutionTests(unittest.TestCase):
    def test_generic_agent_can_use_frozen_real_tool_and_is_subject_to_frozen_budget(self):
        from alien_lab.computational_atlas_frontier import MAX_AGENT_TURNS, MAX_TOOL_CALLS, run_generic_tool_agent
        from alien_lab.computational_atlas_providers import FakeProvider

        provider = FakeProvider(model_id="fake", scripted=[
            {"action": "tool", "tool": "route_path", "arguments": {"edges": [["a", "b"], ["b", "c"]], "start": "a", "goal": "c"}},
            {"action": "final", "result": [["a", "b", "c"]]},
        ])
        result = run_generic_tool_agent(provider=provider, task={"request": "Find the route from a to c using links a-b and b-c."}, expected_result=(["a", "b", "c"],))
        self.assertEqual(result["score"], 1)
        self.assertEqual(result["tool_calls"], 1)
        self.assertEqual(result["model_calls"], 2)
        self.assertEqual(MAX_TOOL_CALLS, 8)
        self.assertEqual(MAX_AGENT_TURNS, 6)

    def test_phase_i_velma_and_generic_arms_share_identical_tool_schema(self):
        from alien_lab.computational_atlas_frontier import generic_tool_schema_bytes, velma_tool_schema_bytes
        self.assertEqual(generic_tool_schema_bytes(), velma_tool_schema_bytes())

    def test_phase_i_velma_semantic_task_runs_compiler_basis_and_independent_verifier(self):
        from alien_lab.computational_atlas_frontier import phase_i_semantic_world
        from alien_lab.computational_atlas_live_ledger import build_phase_i_ledger
        from alien_lab.computational_atlas_live_runner import run_phase_i_cell
        from alien_lab.computational_atlas_providers import FakeProvider
        from alien_lab.computational_atlas_surfaces import oracle_unbound_ir

        cell = next(cell for cell in build_phase_i_ledger() if cell.world_index == 0 and cell.arm == "VELMA_LOCAL")
        world = phase_i_semantic_world(0)
        provider = FakeProvider(model_id="fake", scripted=[oracle_unbound_ir(world).to_dict()])
        outcome = run_phase_i_cell(cell, provider=provider)
        self.assertEqual(outcome["score"], 1)
        self.assertTrue(outcome["verified"])
        self.assertEqual(outcome["model_calls"], 1)


if __name__ == "__main__":
    unittest.main()
