#!/usr/bin/env python3
"""
==============================================================================
TRAIN DQN - Huan luyen Deep Q-Network dieu khien den giao thong GAMA
==============================================================================
Kien truc tong the:
    train.py (PyTorch)  <--WebSocket/gama-client-->  gama-server  <--->  mo hinh
                                                                     intersection-dqn-python.gaml

Vong lap 1 episode:
    reset(seed) -> lap lai [state -> action (eps-greedy) -> step handshake ->
    transition -> replay/update] -> den khi cycle >= horizon

Ghi log:
    run/train_<timestamp>/training_log.csv   : 1 dong/episode
    run/train_<timestamp>/checkpoint.pt      : weights moi 10 episode
    run/train_<timestamp>/dqn_weights.pt     : weights cuoi cung (cho evaluate.py)

Vi du:
    venv/bin/python train.py --episodes 150 --port 6868 --start-server
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


def parse_args():
    p = argparse.ArgumentParser(description="Train DQN traffic controller")
    p.add_argument("--episodes", type=int, default=150)
    p.add_argument("--episode-horizon", type=int, default=2000,
                   help="So cycle GAMA moi episode (2000 cycle = 200s, giong batch cac model khac)")
    p.add_argument("--port", type=int, default=6868)
    p.add_argument("--host", type=str, default="localhost")
    p.add_argument("--start-server", action="store_true",
                   help="Tu khoi dong gama-server (neu chua chay)")
    p.add_argument("--keep-server", action="store_true",
                   help="Khong dung server sau khi train xong")
    p.add_argument("--seed-base", type=int, default=1000,
                   help="Seed GAMA cua episode e = seed_base + e")
    # DQN hyperparameters
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--gamma", type=float, default=0.9)
    p.add_argument("--buffer-size", type=int, default=20000)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--target-sync", type=int, default=200)
    p.add_argument("--hidden", type=int, nargs="+", default=[32, 32])
    p.add_argument("--eps-start", type=float, default=0.5)
    p.add_argument("--eps-decay", type=float, default=0.995)
    p.add_argument("--eps-min", type=float, default=0.05)
    # Reward weights: (1,0) = giong Q-learning tabular (-queue)
    p.add_argument("--w-queue", type=float, default=1.0)
    p.add_argument("--w-wait", type=float, default=0.0)
    p.add_argument("--model-path", type=str, default=None,
                   help="Duong dan file .gaml (mac dinh intersection-dqn-python.gaml)")
    return p.parse_args()

async def amain():
    args = parse_args()
    stamp = time.strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(BASE_DIR, "run", f"train_{stamp}")
    os.makedirs(outdir, exist_ok=True)
    print(f"[Train] Ket qua se luu tai: {outdir}")

    # 1. Server
    manager = None
    if args.start_server:
        manager = GamaServerManager(port=args.port)
        manager.start()
    try:
        # 2. Environment + Agent
        env = GamaTrafficEnv(
            host=args.host, port=args.port,
            model_path=args.model_path,
            w_queue=args.w_queue, w_wait=args.w_wait,
        )
        await env.setup()
        agent = DQNAgent(
            hidden_dims=tuple(args.hidden), lr=args.lr, gamma=args.gamma,
            buffer_size=args.buffer_size, batch_size=args.batch_size,
            target_sync_every=args.target_sync,
            eps_start=args.eps_start, eps_decay=args.eps_decay,
            eps_min=args.eps_min, seed=args.seed_base,
        )
        print(f"[Train] Device: {agent.device} | State dim: 8 | Actions: 2 (EXTEND/SWITCH)")

        # 3. Vong lap huan luyen
        log_path = os.path.join(outdir, "training_log.csv")
        with open(log_path, "w", newline="") as f:
            csv.writer(f).writerow([
                "episode", "seed", "decisions", "episode_reward", "epsilon",
                "avg_loss", "updates", "throughput", "vehicles_created",
                "avg_waiting_time", "max_waiting_time", "avg_speed",
                "avg_travel_time", "final_queue", "wall_seconds",
            ])

        best_reward = -float("inf")
        for ep in range(1, args.episodes + 1):
            t0 = time.time()
            seed = args.seed_base + ep
            state = await env.reset(seed=seed)

            ep_reward = 0.0
            decisions = 0
            done = False
            while not done:
                state_vec = featurize(state)
                action = agent.act(state_vec)
                next_state, reward, _, _ = await env.step(action)
                agent.store(state_vec, action, reward, featurize(next_state),
                            1.0 if next_state["cycle"] >= args.episode_horizon else 0.0)
                if agent.can_update():
                    agent.update()
                agent.decay_epsilon()   # giam per decision, giong Q-learning tabular
                ep_reward += reward
                decisions += 1
                state = next_state
                done = state["cycle"] >= args.episode_horizon

            wall = time.time() - t0
            row = [
                ep, seed, decisions, round(ep_reward, 2), round(agent.eps, 4),
                round(agent.avg_loss, 5), agent.update_count,
                state["total_vehicles_passed"], state["total_vehicles_created"],
                state["average_waiting_time"], state["max_waiting_time"],
                state["average_speed"], state["average_travel_time"],
                state["current_queue_length"], round(wall, 1),
            ]
            with open(log_path, "a", newline="") as f:
                csv.writer(f).writerow(row)

            marker = ""
            if ep_reward > best_reward:
                best_reward = ep_reward
                agent.save(os.path.join(outdir, "best_weights.pt"))
                marker = "  <- best"
            if ep % 10 == 0 or ep == args.episodes:
                agent.save(os.path.join(outdir, "checkpoint.pt"))

            print(f"[Ep {ep:3d}/{args.episodes}] reward={ep_reward:8.1f} | "
                  f"decisions={decisions:3d} | eps={agent.eps:.3f} | "
                  f"loss={agent.avg_loss:.4f} | passed={state['total_vehicles_passed']:3d} | "
                  f"wait={state['average_waiting_time']:5.2f}s | "
                  f"queue={state['current_queue_length']:2d} | {wall:5.1f}s{marker}")

        # 4. Luu weights cuoi cung
        final_path = os.path.join(outdir, "dqn_weights.pt")
        agent.save(final_path)
        print("\n[Train] HOAN TAT.")
        print(f"[Train] Weights cuoi cung : {final_path}")
        print(f"[Train] Weights tot nhat  : {os.path.join(outdir, 'best_weights.pt')}")
        print(f"[Train] Log huan luyen    : {log_path}")
        await env.close()
    finally:
        if manager is not None and not args.keep_server:
            manager.stop()


if __name__ == "__main__":
    asyncio.run(amain())