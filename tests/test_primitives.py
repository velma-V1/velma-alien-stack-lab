import unittest

from alien_lab.compiler import compile_workspace
from alien_lab.taskgen import generate_taskset


class PrimitiveTests(unittest.TestCase):
    def setUp(self):
        public, _ = generate_taskset(20260828)
        self.migration = public.discovery[0].compiler_view()
        self.conflict = public.discovery[1].compiler_view()

    def test_state_resolves_highest_authority_then_revision(self):
        ws = compile_workspace(self.migration, ("state",))
        self.assertEqual(ws.current_state["request_field"], "deadline_ms")
        self.assertEqual(ws.current_state["retry_limit"], "5")

    def test_state_does_not_invent_value_for_top_rank_tie(self):
        ws = compile_workspace(self.conflict, ("state",))
        self.assertNotIn("retry_mode", ws.current_state)

    def test_uncertainty_surfaces_equal_top_conflict(self):
        ws = compile_workspace(self.conflict, ("uncertainty",))
        retry = [x for x in ws.contradictions if x["key"] == "retry_mode"]
        self.assertEqual(len(retry), 1)
        self.assertEqual(set(retry[0]["values"]), {"bounded", "adaptive"})

    def test_path_traces_active_dependency(self):
        ws = compile_workspace(self.migration, ("path",))
        self.assertEqual(ws.active_path, ["gateway", "charge_handler"])

    def test_memory_records_supersession_direction(self):
        ws = compile_workspace(self.migration, ("memory",))
        transitions = [d for d in ws.memory_deltas if d["key"] == "request_field"]
        self.assertTrue(any(d["from"] == "timeout" and d["to"] == "deadline_ms" for d in transitions))

    def test_memory_never_turns_equal_revision_conflict_into_fake_history(self):
        ws = compile_workspace(self.conflict, ("memory",))
        retry = [d for d in ws.memory_deltas if d["key"] == "retry_mode"]
        self.assertEqual(retry, [])

    def test_procedure_compiles_rules_without_deciding_choice(self):
        ws = compile_workspace(self.migration, ("procedure",))
        self.assertGreaterEqual(len(ws.procedure), 3)
        self.assertFalse(any("choice" in x.lower() for x in ws.procedure))

    def test_relevance_prunes_unrelated_scope(self):
        ws = compile_workspace(self.migration, ("relevance",))
        self.assertIn("catalog-note", ws.discarded_evidence)
        self.assertNotIn("catalog-note", ws.evidence_ids)

    def test_path_before_relevance_preserves_active_component_scope_evidence(self):
        # The compiler's relevance pass can use a known active path; this test
        # protects order as a real experimental variable rather than metadata.
        ws_path_first = compile_workspace(self.migration, ("path", "relevance"), order=("path", "relevance"))
        ws_relevance_first = compile_workspace(self.migration, ("path", "relevance"), order=("relevance", "path"))
        self.assertNotEqual(ws_path_first.pass_order, ws_relevance_first.pass_order)
        self.assertIn("handler-note", ws_path_first.evidence_ids)
        self.assertNotIn("handler-note", ws_relevance_first.evidence_ids)

    def test_every_derivation_carries_pass_and_inputs(self):
        ws = compile_workspace(self.migration, ("state", "path", "memory", "procedure"))
        self.assertTrue(ws.derivations)
        for d in ws.derivations:
            self.assertTrue(d.pass_name)
            self.assertIsInstance(d.input_ids, list)
            self.assertTrue(d.rule)

    def test_workspace_records_per_pass_deterministic_cost(self):
        enabled = ("state", "path", "uncertainty", "relevance", "procedure", "memory")
        ws = compile_workspace(self.migration, enabled)
        self.assertEqual(set(ws.pass_timings_ms), set(enabled))
        for value in ws.pass_timings_ms.values():
            self.assertGreaterEqual(value, 0.0)


if __name__ == "__main__":
    unittest.main()

class FusionTests(unittest.TestCase):
    def test_fusion_creates_cross_pass_relation_not_present_in_either_primitive_alone(self):
        from alien_lab.compiler import fuse_workspace
        public, _ = generate_taskset(20260828)
        view = public.discovery[0].compiler_view()
        state_only = compile_workspace(view, ("state",))
        path_only = compile_workspace(view, ("path",))
        combined = compile_workspace(view, ("state", "path"))
        fuse_workspace(view, combined)
        self.assertEqual(state_only.fused_relations, [])
        self.assertEqual(path_only.fused_relations, [])
        active_state = [x for x in combined.fused_relations if x["kind"] == "active_state"]
        self.assertTrue(active_state)
        self.assertTrue(any(x["key"] == "request_field" and x["value"] == "deadline_ms" for x in active_state))
        self.assertIn("fusion", combined.pass_order)
        self.assertIn("fusion", combined.pass_timings_ms)

class RecursiveFusionTests(unittest.TestCase):
    def test_recursive_fusion_joins_first_order_compounds_on_shared_key_and_path(self):
        from alien_lab.compiler import recursive_fuse_workspace
        public, _ = generate_taskset(20260828)
        view = public.discovery[0].compiler_view()
        ws = compile_workspace(view, ("state", "path", "memory"))
        recursive_fuse_workspace(view, ws, depth=2)
        joins = [x for x in ws.fused_relations if x["kind"] == "relational_join"]
        self.assertTrue(joins)
        self.assertTrue(any(x["key"] == "request_field" for x in joins))
        self.assertIn("fusion_depth_2", ws.pass_order)
        self.assertIn("fusion_depth_2", ws.pass_timings_ms)
