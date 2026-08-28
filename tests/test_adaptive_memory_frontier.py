import tempfile
import unittest
from pathlib import Path

from alien_lab.adaptive_memory_frontier import (
    ARM_FULL,
    ARM_NONE,
    ARM_RETRIEVED,
    FRONTIER_PASS_THRESHOLD,
    AdaptiveMemoryRunner,
    MemoryStore,
    bootstrap_store,
    build_level_packet,
    composition_depth,
    deterministic_preflight,
    generate_rules,
    promote_task_macros,
    render_memory_packet,
)
from alien_lab.experiment import ExperimentConfig
from alien_lab.ollama import ModelResult


class ScriptedClient:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []
        self.base_url = "http://localhost:11434"

    def model_metadata(self, model, timeout_seconds=5.0):
        return {"name": model}

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        if not self.results:
            raise AssertionError("unexpected model call")
        return self.results.pop(0)


def ok(response, *, wall_ms=1000, prompt_tokens=100, eval_tokens=16):
    return ModelResult(
        status="OK",
        response=response,
        done_reason="stop",
        prompt_tokens=prompt_tokens,
        eval_tokens=eval_tokens,
        wall_ms=wall_ms,
        hit_ceiling=False,
    )


class AdaptiveMemoryDeterministicTests(unittest.TestCase):
    def test_curriculum_is_stable_for_same_seed_and_changes_for_new_seed(self):
        a = bootstrap_store(20260828)
        b = bootstrap_store(20260828)
        self.assertEqual(a.snapshot_fingerprint(), b.snapshot_fingerprint())
        pa, sa = build_level_packet(20260828, 3, a)
        pb, sb = build_level_packet(20260828, 3, b)
        self.assertEqual([x.to_dict() for x in pa], [x.to_dict() for x in pb])
        self.assertEqual(sa, sb)

        c = bootstrap_store(20260829)
        pc, sc = build_level_packet(20260829, 3, c)
        self.assertNotEqual(a.snapshot_fingerprint(), c.snapshot_fingerprint())
        self.assertNotEqual([x.to_dict() for x in pa], [x.to_dict() for x in pc])
        self.assertNotEqual(sa, sc)

    def test_memory_store_is_append_only_and_fingerprint_changes(self):
        store = MemoryStore()
        first = generate_rules(11, start_index=1, count=2, learned_level=0)
        store.append(first)
        fingerprint = store.snapshot_fingerprint()
        second = generate_rules(11, start_index=3, count=2, learned_level=1)
        store.append(second)
        self.assertEqual(len(store), 4)
        self.assertNotEqual(fingerprint, store.snapshot_fingerprint())
        with self.assertRaises(ValueError):
            store.append((first[0],))

    def test_successful_task_becomes_a_validated_macro_memory(self):
        store = bootstrap_store(20260828)
        tasks, _ = build_level_packet(20260828, 1, store, task_count=1)
        task = tasks[0]
        before = len(store)
        promoted = promote_task_macros(store, tasks, {task.task_id: True}, learned_level=1)
        self.assertEqual(len(promoted), 1)
        self.assertEqual(len(store), before + 1)
        macro = promoted[0]
        self.assertEqual(macro.learned_level, 1)
        self.assertEqual(macro.evidence_id, task.task_id)
        for start in (0, 1, 17, 96):
            direct = start
            for rule_id in task.rule_ids:
                direct = store.get(rule_id).apply(direct)
            self.assertEqual(macro.apply(start), direct)

    def test_failed_task_is_never_promoted_to_memory(self):
        store = bootstrap_store(20260828)
        tasks, _ = build_level_packet(20260828, 1, store, task_count=2)
        promoted = promote_task_macros(
            store,
            tasks,
            {tasks[0].task_id: True, tasks[1].task_id: False},
            learned_level=1,
        )
        self.assertEqual(len(promoted), 1)
        self.assertEqual(promoted[0].evidence_id, tasks[0].task_id)

    def test_difficulty_increases_monotonically_while_success_builds_memory(self):
        store = bootstrap_store(20260828)
        previous_count = 0
        previous_depth = 0
        for level in range(1, 8):
            self.assertGreater(len(store), previous_count)
            self.assertGreater(composition_depth(level), previous_depth)
            tasks, _ = build_level_packet(20260828, level, store)
            self.assertTrue(all(len(task.rule_ids) == composition_depth(level) for task in tasks))
            previous_count = len(store)
            previous_depth = composition_depth(level)
            promote_task_macros(
                store,
                tasks,
                {task.task_id: True for task in tasks},
                learned_level=level,
            )

    def test_tasks_have_unique_choices_and_use_only_prior_memory(self):
        store = bootstrap_store(20260828)
        first_tasks, _ = build_level_packet(20260828, 1, store)
        promote_task_macros(
            store,
            first_tasks,
            {task.task_id: True for task in first_tasks},
            learned_level=1,
        )
        tasks, sealed = build_level_packet(20260828, 2, store)
        for task in tasks:
            self.assertEqual(len(set(task.choices.values())), 4)
            self.assertIn(sealed[task.task_id]["answer"], "ABCD")
            learned_levels = [store.get(rule_id).learned_level for rule_id in task.rule_ids]
            self.assertTrue(all(level < 2 for level in learned_levels))
            self.assertIn(0, learned_levels)
            self.assertIn(1, learned_levels)

    def test_memory_arms_are_exactly_isolated(self):
        store = bootstrap_store(20260828)
        tasks, sealed = build_level_packet(20260828, 1, store)
        referenced = {rule_id for task in tasks for rule_id in task.rule_ids}

        none_prompt, none_ids = render_memory_packet(tasks, store, ARM_NONE)
        full_prompt, full_ids = render_memory_packet(tasks, store, ARM_FULL)
        retrieved_prompt, retrieved_ids = render_memory_packet(tasks, store, ARM_RETRIEVED)

        self.assertEqual(none_ids, ())
        self.assertEqual(set(full_ids), {rule.rule_id for rule in store.all_rules()})
        self.assertEqual(set(retrieved_ids), referenced)
        self.assertNotIn("next=(", none_prompt)
        self.assertEqual(full_prompt.count("next=("), len(store))
        self.assertEqual(retrieved_prompt.count("next=("), len(referenced))

        for evaluator in sealed.values():
            self.assertNotIn(f'expected={evaluator["answer"]}', full_prompt)
            self.assertNotIn(f'expected={evaluator["answer"]}', retrieved_prompt)

    def test_deterministic_preflight_catches_design_invariants(self):
        report = deterministic_preflight(20260828)
        self.assertTrue(report["passed"], report)
        self.assertGreaterEqual(len(report["checks"]), 10)


class AdaptiveMemoryRunnerTests(unittest.TestCase):
    def config(self):
        return ExperimentConfig(
            experiment_id="007-test",
            model="test:model",
            quantization="test",
            context_limit=25600,
            temperature=0.0,
            seed=20260828,
            target_minutes=5.0,
            ceiling_minutes=10.0,
            safety_margin_seconds=1.0,
            discovery_budget=64,
            transfer_budget=64,
            small_budget=64,
            medium_budget=64,
            large_budget=64,
            ollama_url="http://localhost:11434",
        )

    def test_threshold_is_seven_of_eight(self):
        self.assertEqual(FRONTIER_PASS_THRESHOLD, 7 / 8)

    def test_live_preflight_requires_full_and_retrieved_parseable_packets(self):
        client = ScriptedClient([ok("1:A 2:A"), ok("1:A 2:A")])
        with tempfile.TemporaryDirectory() as root:
            runner = AdaptiveMemoryRunner(self.config(), client=client, output_dir=Path(root))
            report = runner.live_preflight()
        self.assertTrue(report["passed"], report)
        self.assertEqual([row["arm"] for row in report["checks"]], [ARM_FULL, ARM_RETRIEVED])
        self.assertEqual(len(client.calls), 2)

    def test_same_model_seed_is_used_for_all_matched_arms(self):
        client = ScriptedClient([ok("1:A"), ok("1:A"), ok("1:A")])
        with tempfile.TemporaryDirectory() as root:
            runner = AdaptiveMemoryRunner(self.config(), client=client, output_dir=Path(root))
            runner._started = runner.clock()
            runner._deadline = runner._started + 600
            store = bootstrap_store(20260828)
            tasks, sealed = build_level_packet(20260828, 1, store, task_count=1)
            for arm in (ARM_NONE, ARM_FULL, ARM_RETRIEVED):
                runner._run_arm(1, tasks, sealed, store, arm, model_seed=4242, phase="frontier")
        self.assertEqual({call["seed"] for call in client.calls}, {4242})

    def test_one_retrieved_failure_is_not_a_confirmed_frontier(self):
        runner = AdaptiveMemoryRunner(self.config(), client=ScriptedClient([]), output_dir=Path("unused"))
        self.assertFalse(runner.confirmed_failure(primary_accuracy=0.75, confirmation_accuracy=1.0))
        self.assertTrue(runner.confirmed_failure(primary_accuracy=0.75, confirmation_accuracy=0.75))
        self.assertFalse(runner.confirmed_failure(primary_accuracy=1.0, confirmation_accuracy=0.75))

    def test_unscorable_is_never_counted_as_capability_failure(self):
        runner = AdaptiveMemoryRunner(self.config(), client=ScriptedClient([]), output_dir=Path("unused"))
        self.assertFalse(runner.confirmed_failure(primary_accuracy=None, confirmation_accuracy=0.0))
        self.assertFalse(runner.confirmed_failure(primary_accuracy=0.0, confirmation_accuracy=None))

    def test_full_context_cap_does_not_prevent_retrieved_arm(self):
        client = ScriptedClient([ok("1:A")])
        bounded = self.config().__class__(**{**self.config().__dict__, "context_limit": 400})
        with tempfile.TemporaryDirectory() as root:
            runner = AdaptiveMemoryRunner(bounded, client=client, output_dir=Path(root))
            runner._started = runner.clock()
            runner._deadline = runner._started + 600
            store = bootstrap_store(20260828)
            tasks, sealed = build_level_packet(20260828, 1, store, task_count=1)
            full = runner._run_arm(1, tasks, sealed, store, ARM_FULL, model_seed=1, phase="frontier")
            retrieved = runner._run_arm(1, tasks, sealed, store, ARM_RETRIEVED, model_seed=1, phase="frontier")
        self.assertEqual(full["status"], "CONTEXT_CAP_REACHED")
        self.assertIn(retrieved["status"], {"OK", "UNSCORABLE"})
        self.assertEqual(len(client.calls), 1)


if __name__ == "__main__":
    unittest.main()
