#!/usr/bin/env python3
"""
==============================================================================
EVALUATE DQN - Danh gia chinh sach da hoc (epsilon = 0, greedy policy)
==============================================================================
Chay N episode voi weights da train, moi 10 cycle doc metrics 1 lan
(giong hang "METRIC_CSV" cua 3 model kia) va xuat CSV cung schema voi
compare_traffic_control.py:

    cycle, time_sec, throughput, avg_waiting_time, queue_length,
    avg_speed, avg_travel_time, max_waiting_time, episode

Ket qua: /Users/mac/Documents/GAMA/comparison_results/dqn_metrics.csv
-> co the ghep thang vao pipeline so sanh 4 thuat toan.

Vi du:
    venv/bin/python evaluate.py --weights run/train_YYYYMMDD_HHMMSS/dqn_weights.pt
==============================================================================
"""

import argparse
import asyncio
import csv
import os
import time

from dqn_agent import DQNAgent
from gama_env import GamaTrafficEnv, featurize
from server_manager import GamaServerManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMPARISON_DIR = os.path.join(os.path.dirname(BASE_DIR), "comparison_results")


def parse_args():
    p = argparse.ArgumentParser(description="Evaluate trained DQN traffic controller")
    p.add_argument("--weights", type=str, required=True,
                   help="File dqn_weights.pt / best_weights.pt tu train.py")
    p.add_argument("--episodes", type=int, default=1)
    p.add_argument("--episode-horizon", type=int, default=2000)
    p.add_argument("--seed-base", type=int, default=5000,
                   help="Seed danh gia (khac voi seed train de tranh overfit)")
    p.add_argument("--port", type=int, default=6868)
    p.add_argument("--host", type=str, default="localhost")
    p.add_argument("--start-server", action="store_true")
    p.add_argument("--keep-server", action="store_true")
    p.add_argument("--hidden", type=int, nargs="+", default=[32, 32],
                   help="Phai khop kich thuoc mang khi train")
    p.add_argument("--w-queue", type=float, default=1.0)
    p.add_argument("--w-wait", type=float, default=0.0)
    p.add_argument("--experiment", type=str, default="dqn_server_experiment",
                   help="Ten experiment trong file GAML")
    p.add_argument("--output", type=str,
                   default=os.path.join(COMPARISON_DIR, "dqn_metrics.csv"))
    return p.parse_args()


async def amain():
    args = parse_args()

    manager = None
    if args.start_server:
        manager = GamaServerManager(port=args.port)
        manager.start()
    try:
        env = GamaTrafficEnv(host=args.host, port=args.port,
                             experiment=args.experiment,
                             w_queue=args.w_queue, w_wait=args.w_wait)
        await env.setup()
        agent = DQNAgent(hidden_dims=tuple(args.hidden))
        agent.load(args.weights)
        agent.eps = 0.0
        print(f"[Eval] Da load weights: {args.weights} | policy = GREEDY (eps=0)")

        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        fieldnames = ["episode", "cycle", "time_sec", "throughput", "avg_waiting_time",
                      "queue_length", "avg_speed", "avg_travel_time", "max_waiting_time"]
        n_rows = 0
        with open(args.output, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for ep in range(1, args.episodes + 1):
                seed = args.seed_base + ep
                state = await env.reset(seed=seed)
                ep_reward = 0.0
                decisions = 0
                t0 = time.time()

                nb = state["next_decision_in_cycles"]
                while state["cycle"] < args.episode_horizon:
                    if state["dqn_waiting_action"]:
                        if decisions > 0:
                            # State hien tai = trang thai tai quyet dinh ke tiep
                            # -> reward cua buoc truoc (giong logic trong train)
                            ep_reward += -(args.w_queue * state["current_queue_length"]
                                           + args.w_wait * state["average_waiting_time"])
                        action = agent.act(featurize(state), greedy=True)
                        await env.set_action(action)
                        await env.step_cycles(1)             # handshake
                        nb = await env.get_next_decision_in()
                        decisions += 1
                    chunk = max(1, min(nb, 10))
                    await env.step_cycles(chunk)
                    nb -= chunk
                    state = await env.read_state()
                    writer.writerow({
                        "episode": ep, "cycle": state["cycle"],
                        "time_sec": round(state["cycle"] * 0.1, 1),
                        "throughput": state["total_vehicles_passed"],
                        "avg_waiting_time": state["average_waiting_time"],
                        "queue_length": state["current_queue_length"],
                        "avg_speed": state["average_speed"],
                        "avg_travel_time": state["average_travel_time"],
                        "max_waiting_time": state["max_waiting_time"],
                    })
                    n_rows += 1

                print(f"[Eval] Ep {ep} | seed={seed} | reward={ep_reward:.1f} "
                      f"| decisions={decisions} | passed={state['total_vehicles_passed']} "
                      f"| avg_wait={state['average_waiting_time']:.2f}s "
                      f"| max_wait={state['max_waiting_time']:.2f}s "
                      f"| avg_speed={state['average_speed']:.2f}km/h "
                      f"| avg_travel={state['average_travel_time']:.2f}s "
                      f"| {time.time()-t0:.1f}s")

        print(f"\n[Eval] Da ghi {n_rows} dong -> {args.output}")
        print("[Eval] Ghep voi 3 model khac: python3 compare_traffic_control.py "
              "(hoac doc README.md)")
        await env.close()
    finally:
        if manager is not None and not args.keep_server:
            manager.stop()


if __name__ == "__main__":
    asyncio.run(amain())