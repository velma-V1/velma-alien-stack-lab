import json
import tempfile
import unittest
from pathlib import Path

from alien_lab.taskgen import generate_taskset, write_sealed_taskset


class TaskGenerationTests(unittest.TestCase):
    def test_public_tasks_exclude_expected_answer_and_compiler_view_excludes_choices(self):
        public, sealed = generate_taskset(1337)
        self.assertGreaterEqual(len(public.discovery), 2)
        task = public.discovery[0]
        self.assertFalse(hasattr(task, "expected_answer"))
        view = task.compiler_view()
        self.assertFalse(hasattr(view, "choices"))
        self.assertFalse(hasattr(view, "question"))
        self.assertIn(task.task_id, sealed.answers)

    def test_generation_is_stable_for_same_seed(self):
        public_a, sealed_a = generate_taskset(99)
        public_b, sealed_b = generate_taskset(99)
        self.assertEqual(public_a.to_dict(), public_b.to_dict())
        self.assertEqual(sealed_a.to_dict(), sealed_b.to_dict())

    def test_answer_positions_are_not_constant(self):
        public, sealed = generate_taskset(2026)
        letters = {sealed.answers[t.task_id]["answer"] for t in public.all_tasks()}
        self.assertGreaterEqual(len(letters), 3)

    def test_sealed_answers_write_separately(self):
        public, sealed = generate_taskset(7)
        with tempfile.TemporaryDirectory() as td:
            public_path = Path(td) / "tasks.json"
            sealed_path = Path(td) / "sealed" / "answers.json"
            write_sealed_taskset(public, sealed, public_path, sealed_path)
            public_doc = json.loads(public_path.read_text())
            sealed_doc = json.loads(sealed_path.read_text())
            self.assertNotIn("answer", json.dumps(public_doc).lower())
            self.assertIn("answers", sealed_doc)
            self.assertTrue(sealed_path.exists())


if __name__ == "__main__":
    unittest.main()
