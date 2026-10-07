"""Regression test for a yellow phase extended by junction clearance."""

import unittest

from dqn_py.gama_env import GamaTrafficEnv


class GamaEnvScheduleTest(unittest.IsolatedAsyncioTestCase):
    async def test_step_reaches_an_actual_decision_after_extended_yellow(self):
        env = GamaTrafficEnv(verbose=False)
        states = iter([
            {"cycle": 100, "dqn_waiting_action": True},
            {"cycle": 381, "dqn_waiting_action": False, "next_decision_in_cycles": 1},
            {"cycle": 382, "dqn_waiting_action": True,
             "current_queue_length": 4, "average_waiting_time": 2.0},
        ])
        stepped = []
        actions = []

        async def read_state():
            return next(states)

        async def step_cycles(n):
            stepped.append(n)

        async def set_action(action):
            actions.append(action)

        async def next_decision():
            return 280

        env.read_state = read_state
        env.step_cycles = step_cycles
        env.set_action = set_action
        env.get_next_decision_in = next_decision

        state, reward, done, info = await env.step(1)
        self.assertEqual(actions, [1])
        self.assertEqual(stepped, [1, 280, 1])
        self.assertTrue(state["dqn_waiting_action"])
        self.assertEqual(reward, -4.0)
        self.assertFalse(done)
        self.assertEqual(info["next_decision_in_cycles"], 281)


if __name__ == "__main__":
    unittest.main()
