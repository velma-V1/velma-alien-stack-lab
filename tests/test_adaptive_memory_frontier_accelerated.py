import unittest

from alien_lab import adaptive_memory_frontier as core
from alien_lab.adaptive_memory_frontier import ARM_NONE, ARM_RETRIEVED
from alien_lab.adaptive_memory_frontier_accelerated import (
    DEPTH_SCHEDULE,
    AcceleratedSafeRunner,
    accelerated_depth,
)
from alien_lab.experiment import ExperimentConfig


class NullClient:
    base_url = "http://localhost:11434"


class AcceleratedFrontierTests(unittest.TestCase):
    def test_depth_schedule_is_strictly_increasing_and_reaches_eighty(self):
        self.assertEqual(DEPTH_SCHEDULE[0], 3)
        self.assertEqual(DEPTH_SCHEDULE[-1], 80)
        self.assertTrue(all(a < b for a, b in zip(DEPTH_SCHEDULE, DEPTH_SCHEDULE[1:])))
        self.assertEqual([accelerated_depth(i) for i in range(1, 13)], list(DEPTH_SCHEDULE))

    def test_schedule_fits_memory_even_at_minimum_passing_promotion_rate(self):
        # A passing eight-task packet can promote as few as seven macros. Before stage N, the store
        # therefore contains at least 12 + 7*(N-1) rules. Every scheduled depth must fit that floor.
        for stage, depth in enumerate(DEPTH_SCHEDULE, 1):
            minimum_rules = 12 + 7 * (stage - 1)
            self.assertLessEqual(depth, minimum_rules, (stage, depth, minimum_rules))

    def test_importing_profile_does_not_mutate_core_schedule(self):
        # Mutation happens only when the explicit accelerated runner is configured/launched.
        self.assertEqual(core.composition_depth(3), 5)
        self.assertEqual(accelerated_depth(3), 8)

    def test_summary_aggregation_tolerates_unmeasured_controls(self):
        config = ExperimentConfig(experiment_id="aggregate-test", model="test:model")
        runner = object.__new__(AcceleratedSafeRunner)
        runner.config = config
        runner.client = NullClient()
        runner.levels = [
            {
                "arms": {
                    ARM_RETRIEVED: {"status": "CONTEXT_CAP_REACHED", "accuracy": None}
                }
            }
        ]
        self.assertIsNone(runner._aggregate_accuracy(ARM_NONE))
        self.assertIsNone(runner._aggregate_accuracy(ARM_RETRIEVED))


if __name__ == "__main__":
    unittest.main()
