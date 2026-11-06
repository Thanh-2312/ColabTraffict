#!/usr/bin/env python3
"""Train four-phase Q-learning, DQN or 3DQN with paired GAMA demand.

Each CPU worker runs an independent GAMA simulation. A single learner merges
transitions in seed order, updates the policy, and saves full resume state.
"""

import argparse
import asyncio
import csv
import hashlib
import os
import time
from pathlib import Path

import torch

from three_dqn_agent import ThreeDQNAgent, FlatDQNAgent
from tabular_agent import TabularQAgent
from gama_env import GamaTrafficEnv, featurize
from server_manager import GamaServerManager
from evaluate import evaluate_episode
from demand import generate_demand, demand_parameters

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_args():
    p = argparse.ArgumentParser(description="Train four-phase GAMA traffic agents")
    p.add_argument("--algorithm", choices=("qlearning", "dqn", "3dqn"), default="3dqn")
    p.add_argument("--output-dir", type=str, default=None)
    p.add_argument("--resume-dir", type=str, default=None,
                   help="Resume from training_state.pt with replay and optimizer intact")
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
    p.add_argument("--workers", type=int, default=1,
                   help="Independent GAMA simulation workers; one learner merges batches in seed order")
    p.add_argument("--gama-heap-mb", type=int, default=2048,
                   help="Maximum Java heap per GAMA worker; default 2048 MB")
    p.add_argument("--keep-server", action="store_true",
                   help="Khong dung server sau khi train xong")
    p.add_argument("--seed-base", type=int, default=1000,
                   help="Seed GAMA cua episode e = seed_base + e")
    p.add_argument("--validation-seed-base", type=int, default=10_000_000,
                   help="Reserved held-out seed range; validation uses base+1 and base+2")
    # DQN hyperparameters
    p.add_argument("--lr", type=float, default=None)
    p.add_argument("--gamma", type=float, default=None)
    p.add_argument("--reward-mode", choices=("reference", "queue_time", "total_wait"), default="reference")
    p.add_argument("--demand-mode", choices=("paired", "model"), default="paired",
                   help="Paired CSV requests keep arrivals identical across policies; model uses live GAMA spawning")
    p.add_argument("--max-delay-sq", type=float, default=None,
                   help="Optional fixed tsd_max; default follows the paper's running maximum")
    p.add_argument("--validate-every", type=int, default=50)
    p.add_argument("--checkpoint-every", type=int, default=50)
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
    if (args.episode_horizon <= 100 or args.total_steps <= 0 or
            args.validate_every <= 0 or args.checkpoint_every <= 0 or
            args.workers <= 0 or args.gama_heap_mb < 512):
        p.error("Horizon must exceed 100 cycles; total-steps and validate-every must be positive")
    if args.workers > 1 and not args.start_server:
        p.error("Multiple workers require --start-server for isolated GAMA processes")
    if args.workers > 1 and args.reward_mode == "reference" and not (args.max_delay_sq and args.max_delay_sq > 0):
        p.error("Parallel reference reward requires a fixed positive --max-delay-sq shared by all workers")
    if args.resume_dir and args.output_dir and Path(args.resume_dir).resolve() != Path(args.output_dir).resolve():
        p.error("--output-dir must equal --resume-dir when resuming")
    possible_episodes = min(args.total_steps, args.episodes) if args.episodes else args.total_steps
    training_end = args.seed_base + possible_episodes
    if any(args.seed_base < args.validation_seed_base + offset <= training_end
           for offset in (1, 2)):
        p.error("Validation seeds overlap the possible training seed range")
    if args.gamma is None:
        args.gamma = .97 if args.reward_mode in ("queue_time", "total_wait") else .99
    if args.lr is None:
        args.lr = 0.1 if args.algorithm == "qlearning" else 1e-4
    return args


def training_config(args):
    fields = ("algorithm", "episode_horizon", "validate_every", "checkpoint_every",
              "workers", "gama_heap_mb", "seed_base",
              "validation_seed_base", "lr", "gamma",
              "reward_mode", "demand_mode", "max_delay_sq", "buffer_size", "warmup", "batch_size",
              "tau", "eps_start", "eps_decay_steps", "eps_min", "model_path")
    config = {name: getattr(args, name) for name in fields}
    files = ("Traffic/includes/collision_avoidance.gaml",
             "Traffic/models/intersection-dqn-python.gaml",
             "dqn_py/gama_env.py", "dqn_py/evaluate.py",
             "dqn_py/server_manager.py", "dqn_py/demand.py",
             "dqn_py/three_dqn_agent.py",
             "dqn_py/tabular_agent.py", "dqn_py/train.py")
    config["code_sha256"] = {name: hashlib.sha256(
        (Path(BASE_DIR).parent / name).read_bytes()).hexdigest() for name in files}
    return config


def make_actor(agent_class, learner, args, seed):
    """Freeze a small CPU policy for one rollout; never copy the learner's replay."""
    actor = agent_class(lr=args.lr, gamma=args.gamma, buffer_size=1,
                        warmup=1, batch_size=1, tau=args.tau,
                        eps_start=args.eps_start, eps_decay_steps=args.eps_decay_steps,
                        eps_min=args.eps_min, seed=seed, reward_mode=args.reward_mode,
                        **({} if args.algorithm == "qlearning" else {"device": torch.device("cpu")}))
    actor.eps = learner.eps
    actor.decisions = learner.decisions
    if args.algorithm == "qlearning":
        actor.table = {key: values.copy() for key, values in learner.table.items()}
    else:
        actor.online_net.load_state_dict(learner.online_net.state_dict())
        actor.online_net.eval()
    return actor


async def collect_rollout(env, actor, args, seed, decision_limit, force_warmup,
                          parameters=None):
    """Collect one episode on an independent server without changing the learner."""
    start = time.monotonic()
    state = await env.reset(seed=seed, parameters=parameters)
    await env.step_cycles(state["next_decision_in_cycles"])
    state = await env.read_state()
    if not state["dqn_waiting_action"]:
        raise RuntimeError("GAMA did not reach the first DQN decision")
    transitions = []
    reward_sum = 0.0
    decisions = 0
    while state["cycle"] < args.episode_horizon and decisions < decision_limit:
        observation = featurize(state)
        action = actor.act(observation, action_mask=state["action_mask"],
                           force_random=force_warmup)
        next_state, reward, _, info = await env.step(
            action, horizon=args.episode_horizon, current_state=state)
        if info["bootstrap_valid"]:
            transitions.append((observation, action, reward, featurize(next_state),
                                info["elapsed_seconds"], next_state["action_mask"].copy()))
        actor.decay_epsilon()
        reward_sum += reward
        decisions += 1
        state = next_state
    return dict(state=state, transitions=transitions, reward=reward_sum,
                decisions=decisions, wall=time.monotonic() - start)

async def amain(args):
    stamp = time.strftime("%Y%m%d_%H%M%S")
    outdir = args.resume_dir or args.output_dir or os.path.join(
        BASE_DIR, "run", f"{args.algorithm}_{stamp}")
    outdir = os.path.abspath(outdir)
    os.makedirs(outdir, exist_ok=True)
    print(f"[Train] Ket qua se luu tai: {outdir}")
    config = training_config(args)
    def episode_parameters(seed):
        if args.demand_mode == "model":
            return None
        path = Path(outdir) / "demand" / f"seed_{seed}_h{args.episode_horizon}.csv"
        generate_demand(path, seed, args.episode_horizon)
        return demand_parameters(path)

    # 1. Server
    managers = []
    envs = []
    try:
        if args.start_server:
            for index in range(args.workers):
                port = args.port + index
                manager = GamaServerManager(
                    port=port, workdir=os.path.join(outdir, "server_ws", str(port)),
                    log_file=os.path.join(outdir, f"server_{port}.log"),
                    heap_mb=args.gama_heap_mb)
                manager.start(reuse_running=False)
                managers.append(manager)
        # 2. Environment + Agent
        for index in range(args.workers):
            env = GamaTrafficEnv(host=args.host, port=args.port + index,
                                 model_path=args.model_path, reward_mode=args.reward_mode,
                                 max_delay_sq=args.max_delay_sq)
            await env.setup()
            envs.append(env)
        env = envs[0]
        agent_class = {"qlearning": TabularQAgent, "dqn": FlatDQNAgent,
                       "3dqn": ThreeDQNAgent}[args.algorithm]
        agent = agent_class(
            lr=args.lr, gamma=args.gamma, buffer_size=args.buffer_size,
            warmup=args.warmup, batch_size=args.batch_size, tau=args.tau,
            eps_start=args.eps_start, eps_decay_steps=args.eps_decay_steps,
            eps_min=args.eps_min, seed=args.seed_base, reward_mode=args.reward_mode)
        print(f"[Train] {args.algorithm} | Device: {agent.device} | DTSE: 3x8x20 | Actions: 4 phases")

        # 3. Vong lap huan luyen
        log_path = os.path.join(outdir, "training_log.csv")
        header = ["episode", "seed", "decisions", "episode_reward", "epsilon",
                  "avg_loss", "updates", "throughput", "vehicles_created",
                  "avg_waiting_time", "max_waiting_time", "avg_speed",
                  "avg_travel_time", "final_queue", "wall_seconds"]
        best_validation_queue = float("inf")
        class DiscardSamples:
            def writerow(self, row):
                pass
        ep = 0
        if args.resume_dir:
            snapshot = torch.load(os.path.join(outdir, "training_state.pt"),
                                  map_location=agent.device, weights_only=False)
            if snapshot["config"] != config:
                raise ValueError("Resume requires identical training settings and source code")
            agent.restore_training(snapshot["agent"])
            ep = snapshot["episode"]
            best_validation_queue = snapshot["best_validation_queue"]
            for worker, normalizer in zip(envs, snapshot["normalizers"]):
                worker._worst_delay_sq = normalizer
            with open(log_path, newline="") as f:
                old_rows = list(csv.reader(f))
            if old_rows[0] != header or len(old_rows) < ep + 1:
                raise ValueError("Training log does not match the checkpoint")
            with open(log_path, "w", newline="") as f:
                csv.writer(f).writerows(old_rows[:ep + 1])
            print(f"[Train] Resumed episode {ep}, decision {agent.decisions}")
        else:
            if os.path.exists(log_path):
                raise FileExistsError("Training output already exists; use --resume-dir")
            with open(log_path, "w", newline="") as f:
                csv.writer(f).writerow(header)

        def save_training_snapshot():
            snapshot = {"config": config, "episode": ep,
                        "best_validation_queue": best_validation_queue,
                        "normalizers": [worker._worst_delay_sq for worker in envs],
                        "agent": agent.training_state()}
            temporary = os.path.join(outdir, "training_state.pt.tmp")
            torch.save(snapshot, temporary)
            os.replace(temporary, os.path.join(outdir, "training_state.pt"))
        while agent.decisions < args.total_steps and (args.episodes == 0 or ep < args.episodes):
            if args.workers > 1:
                available_episodes = (args.episodes - ep) if args.episodes else args.workers
                batch_size = min(args.workers, available_episodes,
                                 args.validate_every - ep % args.validate_every,
                                 args.checkpoint_every - ep % args.checkpoint_every,
                                 args.total_steps - agent.decisions)
                remaining = args.total_steps - agent.decisions
                quotas = [remaining // batch_size + int(i < remaining % batch_size)
                          for i in range(batch_size)]
                actors = [make_actor(agent_class, agent, args, args.seed_base + ep + i + 1)
                          for i in range(batch_size)]
                # All actors see the same frozen learner; independent GAMA
                # processes collect in parallel. Learn in seed order below.
                tasks = [asyncio.create_task(collect_rollout(
                    envs[i], actors[i], args, args.seed_base + ep + i + 1,
                    quotas[i], args.algorithm != "qlearning" and
                    len(agent.buffer) < args.warmup,
                    episode_parameters(args.seed_base + ep + i + 1))) for i in range(batch_size)]
                try:
                    collected = await asyncio.gather(*tasks)
                except BaseException:
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    raise
                for item in collected:
                    ep += 1
                    seed = args.seed_base + ep
                    for observation, action, reward, next_observation, seconds, mask in item["transitions"]:
                        agent.store(observation, action, reward, next_observation, False,
                                    seconds=seconds, next_mask=mask)
                        if agent.can_update():
                            agent.update()
                    for _ in range(item["decisions"]):
                        agent.decay_epsilon()
                    state = item["state"]
                    row = [ep, seed, item["decisions"], round(item["reward"], 2),
                           round(agent.eps, 4), round(agent.avg_loss, 5), agent.update_count,
                           state["total_vehicles_passed"], state["total_vehicles_created"],
                           state["average_waiting_time"], state["max_waiting_time"],
                           state["average_speed"], state["average_travel_time"],
                           state["current_queue_length"], round(item["wall"], 1)]
                    with open(log_path, "a", newline="") as f:
                        csv.writer(f).writerow(row)
                    marker = ""
                    if ep % args.validate_every == 0 or agent.decisions >= args.total_steps or ep == args.episodes:
                        normalizer = env._worst_delay_sq
                        scores = []
                        try:
                            for validation_seed in (args.validation_seed_base + 1,
                                                    args.validation_seed_base + 2):
                                last, _, _, _ = await evaluate_episode(
                                    env, agent, validation_seed, args.episode_horizon,
                                    DiscardSamples(), 0, collect_samples=False,
                                    parameters=episode_parameters(validation_seed))
                                wait = last["queue_time_integral"]
                                if args.reward_mode == "total_wait":
                                    wait += last["external_wait_integral"]
                                scores.append(wait / (args.episode_horizon * .1))
                        finally:
                            env._worst_delay_sq = normalizer
                        score = sum(scores) / len(scores)
                        with open(os.path.join(outdir, "validation_log.csv"), "a", newline="") as f:
                            csv.writer(f).writerow([ep, agent.decisions, *scores, score])
                        if score < best_validation_queue:
                            best_validation_queue = score
                            agent.save(os.path.join(outdir, "best_weights.pt"))
                            marker = "  <- best validation queue"
                    if (ep % args.checkpoint_every == 0 or
                            agent.decisions >= args.total_steps or ep == args.episodes):
                        agent.save(os.path.join(outdir, "checkpoint.pt"))
                        save_training_snapshot()
                    print(f"[Ep {ep:5d} | step {agent.decisions}/{args.total_steps}] "
                          f"reward={item['reward']:8.1f} | decisions={item['decisions']:3d} | "
                          f"eps={agent.eps:.3f} | loss={agent.avg_loss:.4f} | "
                          f"passed={state['total_vehicles_passed']:3d} | "
                          f"queue={state['current_queue_length']:2d} | "
                          f"{item['wall']:5.1f}s{marker}")
                continue
            ep += 1
            t0 = time.time()
            seed = args.seed_base + ep
            state = await env.reset(seed=seed, parameters=episode_parameters(seed))
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
                                   force_random=args.algorithm != "qlearning" and
                                   len(agent.buffer) < args.warmup)
                next_state, reward, _, info = await env.step(
                    action, horizon=args.episode_horizon, current_state=state)
                if info["bootstrap_valid"]:
                    agent.store(state_vec, action, reward, featurize(next_state), False,
                                seconds=info["elapsed_seconds"], next_mask=next_state["action_mask"])
                    if agent.can_update():
                        agent.update()
                agent.decay_epsilon()
                if agent.decisions in (1_000_000, 5_000_000):
                    agent.save(os.path.join(outdir, f"{args.algorithm}_{agent.decisions}_steps.pt"))
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
                    for validation_seed in (args.validation_seed_base + 1,
                                            args.validation_seed_base + 2):
                        last, _, _, _ = await evaluate_episode(env, agent, validation_seed,
                            args.episode_horizon, DiscardSamples(), 0,
                            collect_samples=False,
                            parameters=episode_parameters(validation_seed))
                        wait = last["queue_time_integral"]
                        if args.reward_mode == "total_wait":
                            wait += last["external_wait_integral"]
                        scores.append(wait / (args.episode_horizon * .1))
                finally:
                    env._worst_delay_sq = normalizer
                score = sum(scores) / len(scores)
                with open(os.path.join(outdir, "validation_log.csv"), "a", newline="") as f:
                    csv.writer(f).writerow([ep, agent.decisions, *scores, score])
                if score < best_validation_queue:
                    best_validation_queue = score
                    agent.save(os.path.join(outdir, "best_weights.pt"))
                    marker = "  <- best validation queue"
            if (ep % args.checkpoint_every == 0 or
                    agent.decisions >= args.total_steps or ep == args.episodes):
                agent.save(os.path.join(outdir, "checkpoint.pt"))
                save_training_snapshot()

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
            await asyncio.gather(*(env.close() for env in envs), return_exceptions=True)
        finally:
            if not args.keep_server:
                for manager in managers:
                    manager.stop()


if __name__ == "__main__":
    asyncio.run(amain(parse_args()))
