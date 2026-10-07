"""Checks for paired demand and learning/evaluation separation."""
import tempfile
import unittest
from pathlib import Path

from scripts.fair_benchmark import EXTRA_FIELDS, Learners, generate_demand


class FairBenchmarkTest(unittest.TestCase):
    def test_demand_is_reproducible_and_keeps_requested_arrivals(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / f"{i}.csv" for i in range(3)]
            a = generate_demand(paths[0], 5001, 1000)
            b = generate_demand(paths[1], 5001, 1000)
            c = generate_demand(paths[2], 5002, 1000)
            self.assertEqual(a, b)
            self.assertNotEqual(a, c)
            rows = [list(map(int, line.split(","))) for line in paths[0].read_text().splitlines()]
            self.assertEqual(len(rows), 2 * 67 + 2 * 23 + 8 * 9)
            self.assertEqual({row[1] for row in rows}, set(range(12)))
            self.assertEqual([r[:2] for r in rows], sorted(r[:2] for r in rows))

    def test_both_learners_learn_from_shared_data_and_greedy_is_frozen(self):
        learners = Learners(123)
        left = dict.fromkeys(EXTRA_FIELDS, 0.0)
        left.update(global_phase=0, green_cycles=100, through_queue_ns=10)
        right = dict(left, through_queue_ns=0, through_queue_ew=10)
        for _ in range(80):
            for state, best in ((left, 0), (right, 1)):
                for action in (0, 1):
                    learners.learn(state, action, 0.0 if action == best else -3.0,
                                   state, True, 5.0)
        before = learners.policy_digest()
        for method in ("Q-Learning", "Deep Q-Learning"):
            self.assertEqual(learners.act(method, left), 0)
            self.assertEqual(learners.act(method, right), 1)
        self.assertEqual(before, learners.policy_digest())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "checkpoint.pt"
            learners.save(path)
            restored = Learners(456)
            restored.load_training(path)
            self.assertEqual(before, restored.policy_digest())
            self.assertEqual(restored.transitions, learners.transitions)
            self.assertEqual(restored.rng.getstate(), learners.rng.getstate())

    def test_pressure_does_not_hold_empty_through_for_waiting_left_turns(self):
        state = dict.fromkeys(EXTRA_FIELDS, 0.0)
        state.update(global_phase=4, green_cycles=300, left_queue_ew=4,
                     through_approach_ns=3)
        self.assertEqual(Learners(1).act("MaxPressure", state), 1)


if __name__ == "__main__":
    unittest.main()
