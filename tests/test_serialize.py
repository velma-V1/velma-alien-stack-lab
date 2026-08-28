import unittest

from alien_lab.compiler import compile_workspace
from alien_lab.serialize import render_raw, render_structured, render_workspace
from alien_lab.taskgen import generate_taskset


class SerializationTests(unittest.TestCase):
    def setUp(self):
        public, _ = generate_taskset(42)
        self.task = public.discovery[0]

    def test_raw_contains_original_evidence_and_question(self):
        text = render_raw(self.task)
        self.assertIn("RAW PROJECT EVIDENCE", text)
        self.assertIn(self.task.sources[0].raw, text)
        self.assertIn(self.task.question, text)

    def test_structured_contains_same_source_ids_without_derivations(self):
        text = render_structured(self.task)
        for src in self.task.sources:
            self.assertIn(src.record_id, text)
        self.assertNotIn("DERIVED", text)
        self.assertNotIn("CURRENT STATE", text)

    def test_workspace_only_exposes_enabled_derivations(self):
        ws = compile_workspace(self.task.compiler_view(), ("state", "path"))
        text = render_workspace(self.task, ws)
        self.assertIn("CURRENT STATE", text)
        self.assertIn("ACTIVE PATH", text)
        self.assertNotIn("MEMORY DELTAS", text)
        self.assertNotIn("PROCEDURE", text)

    def test_renderers_do_not_need_sealed_evaluator(self):
        # API itself proves evaluator separation: renderers accept Task/Workspace only.
        ws = compile_workspace(self.task.compiler_view(), ())
        for fn, args in [
            (render_raw, (self.task,)),
            (render_structured, (self.task,)),
            (render_workspace, (self.task, ws)),
        ]:
            self.assertIsInstance(fn(*args), str)


if __name__ == "__main__":
    unittest.main()

class PacketSerializationTests(unittest.TestCase):
    def test_packet_contains_each_task_once_and_one_compact_output_contract(self):
        from alien_lab.serialize import render_packet
        public, _ = generate_taskset(314)
        tasks = public.discovery[:3]
        text = render_packet(tasks, mode="structured")
        for i, task in enumerate(tasks, 1):
            self.assertIn(f"TASK {i}", text)
            self.assertIn(task.question, text)
        self.assertIn("1:<LETTER>", text)
        self.assertEqual(text.count("PACKET OUTPUT CONTRACT"), 1)
