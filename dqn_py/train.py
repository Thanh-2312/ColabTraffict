#!/usr/bin/env python3
"""
==============================================================================
TRAIN 3DQN - Dueling Double DQN dieu khien den giao thong GAMA
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
    venv/bin/python train.py --total-steps 1000000 --port 6868 --start-server
==============================================================================
"""

import argparse
import asyncio
import csv
import os
import time

from three_dqn_agent import ThreeDQNAgent
from gama_env import GamaTrafficEnv, featurize
from server_manager import GamaServerManager
from evaluate import evaluate_episode

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_args():
    p = argparse.ArgumentParser(description="Train GAMA DTSE Dueling Double DQN")
    p.add_argument("--episodes", type=int, default=0,
                   help="Optional episode limit (0 = follow total-steps)")
    p.add_argument("--total-steps", type=int, default=1_000_000,
                   help="Agent decisions; use 1000000 or 5000000 as in the paper")
    p.add_argument("--episode-horizon", type=int, default=8000,
                   help="So cycle GAMA moi episode (8000 cycle = 800s, giong batch cac model khac)")
    p.add_argument("--port", type=int, default=6868)
    p.add_argument("--host", type=str, default="localhost")
    p.add_argument("--start-server", action="store_true",
                   help="Tu khoi dong gama-server (neu chua chay)")
    p.add_argument("--keep-server", action="store_true",
                   help="Khong dung server sau khi train xong")
    p.add_argument("--seed-base", type=int, default=1000,
                   help="Seed GAMA cua episode e = seed_base + e")
    # DQN hyperparameters
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--gamma", type=float, default=None)
    p.add_argument("--reward-mode", choices=("reference", "queue_time"), default="reference")
    p.add_argument("--max-delay-sq", type=float, default=None,
                   help="Optional fixed tsd_max; default follows the paper's running maximum")
    p.add_argument("--validate-every", type=int, default=10)
    p.add_argument("--buffer-size", type=int, default=1_000_000)
    p.add_argument("--warmup", type=int, default=100_000)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--tau", type=float, default=1e-3)
    p.add_argument("--eps-start", type=float, default=1.0)
    p.add_argument("--eps-decay-steps", type=float, default=2_000_000)
    p.add_argument("--eps-min", type=float, default=0.001)
    p.add_argument("--model-path", type=str, default=None,
                   help="Duong dan file .gaml (mac dinh intersection-dqn-python.gaml)")
    args = p.parse_args()
    if args.episode_horizon <= 100 or args.total_steps <= 0 or args.validate_every <= 0:
        p.error("Horizon must exceed 100 cycles; total-steps and validate-every must be positive")
    if args.gamma is None:
        args.gamma = .97 if args.reward_mode == "queue_time" else .99
    return args

async def amain(args):
    stamp = time.strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(BASE_DIR, "run", f"train_{stamp}")
    os.makedirs(outdir, exist_ok=True)
    print(f"[Train] Ket qua se luu tai: {outdir}")

    # 1. Server
    manager = GamaServerManager(port=args.port) if args.start_server else None
    env = None
    try:
        if manager is not None:
            manager.start()
        # 2. Environment + Agent
        env = GamaTrafficEnv(host=args.host, port=args.port,
                             model_path=args.model_path, reward_mode=args.reward_mode,
                             max_delay_sq=args.max_delay_sq)
        await env.setup()
        agent = ThreeDQNAgent(
            lr=args.lr, gamma=args.gamma, buffer_size=args.buffer_size,
            warmup=args.warmup, batch_size=args.batch_size, tau=args.tau,
            eps_start=args.eps_start, eps_decay_steps=args.eps_decay_steps,
            eps_min=args.eps_min, seed=args.seed_base, reward_mode=args.reward_mode)
        print(f"[Train] Device: {agent.device} | DTSE: 3x8x20 | Actions: 4 phases")

        # 3. Vong lap huan luyen
        log_path = os.path.join(outdir, "training_log.csv")
        with open(log_path, "w", newline="") as f:
            csv.writer(f).writerow([
                "episode", "seed", "decisions", "episode_reward", "epsilon",
                "avg_loss", "updates", "throughput", "vehicles_created",
                "avg_waiting_time", "max_waiting_time", "avg_speed",
                "avg_travel_time", "final_queue", "wall_seconds",
            ])

        best_validation_queue = float("inf")
        class DiscardSamples:
            def writerow(self, row):
                pass
        ep = 0
        while agent.decisions < args.total_steps and (args.episodes == 0 or ep < args.episodes):
            ep += 1
            t0 = time.time()
            seed = args.seed_base + ep
            state = await env.reset(seed=seed)
            # The controller first requests an action at cycle 100.  A call to
            # env.step() before then would store a transition for an action
            # that GAMA has not applied.
            await env.step_cycles(state["next_decision_in_cycles"])
            state = await env.read_state()
            if not state["dqn_waiting_action"]:
                raise RuntimeError("GAMA did not reach the first DQN decision")

            ep_reward = 0.0
            decisions = 0
            done = False
            while not done and agent.decisions < args.total_steps:
                state_vec = featurize(state)
                # The paper fills N_min with uniformly random legal transitions
                # before starting gradient updates, independently of epsilon.
                action = agent.act(state_vec, action_mask=state["action_mask"],
                                   force_random=len(agent.buffer) < args.warmup)
                next_state, reward, _, info = await env.step(action, horizon=args.episode_horizon)
                if info["bootstrap_valid"]:
                    agent.store(state_vec, action, reward, featurize(next_state), False,
                                seconds=info["elapsed_seconds"], next_mask=next_state["action_mask"])
                    if agent.can_update():
                        agent.update()
                agent.decay_epsilon()
                if agent.decisions in (1_000_000, 5_000_000):
                    agent.save(os.path.join(outdir, f"3dqn_{agent.decisions}_steps.pt"))
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
            if ep % args.validate_every == 0 or agent.decisions >= args.total_steps or ep == args.episodes:
                # Validation must not change the training reward normalizer.
                normalizer = env._worst_delay_sq
                scores = []
                try:
                    for validation_seed in (3001, 3002):
                        last, _, _, _ = await evaluate_episode(env, agent, validation_seed,
                            args.episode_horizon, DiscardSamples(), 0)
                        scores.append(last["queue_time_integral"] / (args.episode_horizon * .1))
                finally:
                    env._worst_delay_sq = normalizer
                score = sum(scores) / len(scores)
                with open(os.path.join(outdir, "validation_log.csv"), "a", newline="") as f:
                    csv.writer(f).writerow([ep, agent.decisions, *scores, score])
                if score < best_validation_queue:
                    best_validation_queue = score
                    agent.save(os.path.join(outdir, "best_weights.pt"))
                    marker = "  <- best validation queue"
            if ep % 10 == 0 or agent.decisions >= args.total_steps or ep == args.episodes:
                agent.save(os.path.join(outdir, "checkpoint.pt"))

            print(f"[Ep {ep:5d} | step {agent.decisions}/{args.total_steps}] reward={ep_reward:8.1f} | "
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
    finally:
        try:
            if env is not None:
                await env.close()
        finally:
            if manager is not None and not args.keep_server:
                manager.stop()


if __name__ == "__main__":
    asyncio.run(amain(parse_args()))
