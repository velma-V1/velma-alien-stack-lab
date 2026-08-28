import unittest

from alien_lab.adaptive_memory_frontier import (
    ARM_FULL,
    ARM_NONE,
    ARM_RETRIEVED,
    TITAN_MIN_BRANCH_POINTS,
    TITAN_MIN_CROSS_REGISTER_JOINS,
    TITAN_MIN_MEMORY_REFERENCES,
    TITAN_MIN_PROGRAM_STEPS,
    bootstrap_store,
    build_level_packet,
    build_titan_challenge,
    promote_task_macros,
    render_titan_prompt,
    solve_titan_oracle,
)


class TitanFrontierProbeTests(unittest.TestCase):
    def earned_store(self):
        store = bootstrap_store(20260828)
        for level in range(1, 8):
            tasks, _ = build_level_packet(20260828, level, store, task_count=8)
            promote_task_macros(
                store,
                tasks,
                {task.task_id: True for task in tasks},
                learned_level=level,
            )
        return store

    def test_titan_is_stable_for_same_seed_and_changes_for_new_seed(self):
        store = self.earned_store()
        a, sealed_a = build_titan_challenge(20260828, store)
        b, sealed_b = build_titan_challenge(20260828, store)
        c, sealed_c = build_titan_challenge(20260829, store)

        self.assertEqual(a.to_dict(), b.to_dict())
        self.assertEqual(sealed_a, sealed_b)
        self.assertNotEqual(a.to_dict(), c.to_dict())
        self.assertNotEqual(sealed_a, sealed_c)

    def test_titan_is_frontier_class_shape_not_one_more_ordinary_level(self):
        store = self.earned_store()
        titan, _ = build_titan_challenge(20260828, store)

        self.assertEqual(len(titan.initial_registers), 8)
        self.assertGreaterEqual(len(titan.program), TITAN_MIN_PROGRAM_STEPS)
        self.assertGreaterEqual(len(set(titan.referenced_memory_ids)), TITAN_MIN_MEMORY_REFERENCES)
        self.assertGreaterEqual(titan.branch_points, TITAN_MIN_BRANCH_POINTS)
        self.assertGreaterEqual(titan.cross_register_joins, TITAN_MIN_CROSS_REGISTER_JOINS)
        self.assertGreaterEqual(titan.nested_dependency_joins, 3)
        self.assertEqual(len(set(titan.choices.values())), 4)

    def test_titan_uses_earned_macro_memory_when_available(self):
        store = self.earned_store()
        titan, _ = build_titan_challenge(20260828, store)
        referenced = [store.get(rule_id) for rule_id in titan.referenced_memory_ids]
        macro_count = sum(rule.evidence_id.startswith("memory-") for rule in referenced)
        self.assertGreaterEqual(macro_count, 6)

        learned_levels = {rule.learned_level for rule in referenced}
        self.assertIn(0, learned_levels)
        self.assertIn(max(rule.learned_level for rule in store.all_rules()), learned_levels)
        self.assertTrue(any(0 < level < max(learned_levels) for level in learned_levels))

    def test_titan_oracle_is_independent_and_matches_the_sealed_answer(self):
        store = self.earned_store()
        titan, sealed = build_titan_challenge(20260828, store)
        final_value = solve_titan_oracle(titan, store)
        answer = next(letter for letter, value in titan.choices.items() if value == final_value)

        self.assertEqual(final_value, sealed["final_value"])
        self.assertEqual(answer, sealed["answer"])
        self.assertTrue(sealed["deterministic_unique"])

    def test_titan_memory_arms_are_exactly_isolated(self):
        store = self.earned_store()
        titan, sealed = build_titan_challenge(20260828, store)

        none_prompt, none_ids = render_titan_prompt(titan, store, ARM_NONE)
        full_prompt, full_ids = render_titan_prompt(titan, store, ARM_FULL)
        retrieved_prompt, retrieved_ids = render_titan_prompt(titan, store, ARM_RETRIEVED)

        self.assertEqual(none_ids, ())
        self.assertEqual(set(full_ids), {rule.rule_id for rule in store.all_rules()})
        self.assertEqual(set(retrieved_ids), set(titan.referenced_memory_ids))
        self.assertNotIn("next=(", none_prompt)

        for prompt in (full_prompt, retrieved_prompt):
            memory_prefix = prompt.split("TITAN PROGRAM", 1)[0]
            self.assertNotIn(str(sealed["final_value"]), memory_prefix)
            self.assertNotIn(f'answer={sealed["answer"]}', memory_prefix)
            self.assertNotIn("expected=", memory_prefix)

    def test_titan_constants_encode_the_minimum_requested_difficulty(self):
        self.assertGreaterEqual(TITAN_MIN_PROGRAM_STEPS, 32)
        self.assertGreaterEqual(TITAN_MIN_MEMORY_REFERENCES, 12)
        self.assertGreaterEqual(TITAN_MIN_BRANCH_POINTS, 4)
        self.assertGreaterEqual(TITAN_MIN_CROSS_REGISTER_JOINS, 6)


if __name__ == "__main__":
    unittest.main()
