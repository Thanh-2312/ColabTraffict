"""Regression test for a yellow phase extended by junction clearance."""

import unittest
import numpy as np

from dqn_py.gama_env import GamaTrafficEnv


class GamaEnvScheduleTest(unittest.IsolatedAsyncioTestCase):
    async def test_paper_reward_uses_running_max_total_squared_delay(self):
        env = GamaTrafficEnv(verbose=False, reward_mode="reference")
        self.assertIsNone(env.max_delay_sq)
        self.assertEqual(env.reward_from_state({"delay_sq": 5.0}), 0.0)
        self.assertAlmostEqual(env.reward_from_state({"delay_sq": 2.0}), 0.6)
        self.assertEqual(env.reward_from_state({"delay_sq": 8.0}), 0.0)
        self.assertAlmostEqual(env.reward_from_state({"delay_sq": 4.0}), 0.5)

    async def test_reward_normalizer_survives_episode_reset(self):
        env = GamaTrafficEnv(verbose=False)
        env._worst_delay_sq = 10.0

        async def load_experiment(parameters=None):
            env.exp_id = "test"

        async def read_state():
            return {"cycle": 0}

        env.load_experiment = load_experiment
        env.read_state = read_state
        await env.reset(seed=17)
        self.assertEqual(env.reward_from_state({"delay_sq": 5.0}), 0.5)

    async def test_step_reaches_an_actual_decision_after_extended_yellow(self):
        env = GamaTrafficEnv(verbose=False)
        env._worst_delay_sq = 10.0
        states = iter([
            {"cycle": 100, "dqn_waiting_action": True},
            {"cycle": 381, "dqn_waiting_action": False, "next_decision_in_cycles": 1},
            {"cycle": 382, "dqn_waiting_action": True,
             "current_queue_length": 4, "average_waiting_time": 2.0,
             "delay_sq": 5.0},
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
        self.assertEqual(reward, 0.5)
        self.assertFalse(done)
        self.assertEqual(info["next_decision_in_cycles"], 281)

    async def test_step_stops_at_horizon_during_clearance(self):
        env = GamaTrafficEnv(verbose=False)
        env._worst_delay_sq = 10.0
        final = {"cycle": 200, "dqn_waiting_action": False, "next_decision_in_cycles": 1,
                 "delay_sq": 5.0, "dtse": np.zeros((3,8,20))}
        states = iter([{"cycle": 100, "dqn_waiting_action": True},
                       {k:v for k,v in final.items() if k != "dtse"}, final])
        stepped = []
        async def read_state(**kwargs): return next(states)
        async def step_cycles(n): stepped.append(n)
        async def set_action(a): pass
        async def schedule(): return 150
        env.read_state, env.step_cycles = read_state, step_cycles
        env.set_action, env.get_next_decision_in = set_action, schedule
        state, reward, done, info = await env.step(2, horizon=200)
        self.assertEqual(stepped, [1, 99])
        self.assertEqual(state["cycle"], 200)
        self.assertTrue(done and info["truncated"])
        self.assertFalse(info["bootstrap_valid"])
        self.assertEqual(info["elapsed_seconds"], 10.)


if __name__ == "__main__":
    unittest.main()
