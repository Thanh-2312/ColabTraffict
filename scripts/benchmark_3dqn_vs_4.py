#!/usr/bin/env python3
"""Paired-demand benchmark of GAMA 3DQN against the four existing policies.

The four existing Q/DQN checkpoints come from fair_benchmark_20261005_final.
All policies use the same demand files and seeds. Baseline evaluation may be
reused after verifying its GAMA source hashes; otherwise all five policies
are evaluated anew. A separate legacy controller preserves the old 0/1 action
meaning for the four existing policies.
"""

import argparse
import asyncio
import csv
import hashlib
import json
import math
import random
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "dqn_py"))
from gama_env import GamaTrafficEnv
from server_manager import GamaServerManager
from three_dqn_agent import ThreeDQNAgent
from scripts.baseline_policies import pressure_heuristic
from scripts.fair_benchmark import BenchmarkEnv, Learners, METHODS, run_episode, source_hashes

THREE = "3DQN"
ALL_METHODS = (*METHODS, THREE)
DEFAULT_BASELINE = ROOT / "comparison_results/fair_benchmark_20261005_final"
EXTRA_METRICS = (
    "queue_time_integral", "external_wait_integral", "cumulative_max_wait",
    "ground_requests", "ground_pending",
)
SAFETY_FIELDS = (
    "total_tit_sum", "severe_conflicts_count", "hard_braking_count",
    "pet_conflicts_count", "critical_pet_count", "bypass_vehicles_passed",
)


def pack_expression(fields):
    return '"" + ' + ' + "|" + '.join(fields)


async def read_fields(env, fields):
    raw = str(await env._exec_expression(pack_expression(fields)))
    values = raw.split("|")
    if len(values) != len(fields):
        raise RuntimeError(f"Expected {len(fields)} GAMA metrics, got {len(values)}: {raw}")
    result = dict(zip(fields, map(float, values)))
    if not all(math.isfinite(v) for v in result.values()):
        raise RuntimeError(f"Non-finite GAMA metrics: {result}")
    return result


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def network_hash(agent):
    digest = hashlib.sha256()
    for value in agent.online_net.state_dict().values():
        digest.update(value.detach().cpu().numpy().tobytes())
    return digest.hexdigest()


def all_source_hashes():
    sources = source_hashes()
    for relative in ("Traffic/models/intersection-dqn-python.gaml",
                     "dqn_py/three_dqn_agent.py", "scripts/benchmark_3dqn_vs_4.py"):
        sources[relative] = file_hash(ROOT / relative)
    return sources


def evaluation_signature(spec, baseline, agent, horizon):
    method = spec["method"]
    policy = network_hash(agent) if method == THREE else None
    if method in METHODS[2:]:
        policy = file_hash(baseline / ("best_q.pt" if method == "Q-Learning" else "best_dqn.pt"))
    data = dict(method=method, seed=spec["seed"], horizon=horizon,
                demand=file_hash(spec["demand"]), policy=policy,
                sources=all_source_hashes(), reward_scope=spec.get("reward_scope", "all"),
                reward_mode=agent.reward_mode if method == THREE else "queue_time")
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


async def run_three_episode(env, agent, seed, horizon, demand_path, output,
                            train=False, epsilon=0.0, teacher_prob=0.0):
    state = await env.reset(seed=seed, parameters=[
        dict(name="demand_file_path", type="string", value=str(demand_path.resolve()))])
    actual_seed = float(await env._exec_expression("world.seed"))
    if actual_seed != seed:
        raise RuntimeError(f"GAMA seed {actual_seed} differs from requested {seed}")
    rng = random.Random(seed * 1009)
    t0 = time.monotonic()
    samples = []
    decisions = []
    transitions = []
    pending = None
    total_reward = 0.0
    next_progress = 1000
    before_policy = network_hash(agent)
    while state["cycle"] < horizon:
        if state["dqn_waiting_action"]:
            if pending is not None:
                previous, action = pending
                reward = env.transition_reward(previous, state)
                total_reward += reward
                if train:
                    transitions.append((previous["dtse"].copy(), action,
                                        state["delay_sq"] if agent.reward_mode == "reference" else reward,
                                        state["dtse"].copy(), False,
                                        (state["cycle"] - previous["cycle"]) * .1,
                                        state["action_mask"].copy()))
            if train and teacher_prob > 0.0 and rng.random() < teacher_prob:
                action = pressure_heuristic(state["dtse"], pending[1] if pending else 0, state["action_mask"])
            elif train and rng.random() < epsilon:
                action = int(rng.choice(np.flatnonzero(state["action_mask"])))
            else:
                action = agent.act(state["dtse"], greedy=True, action_mask=state["action_mask"])
            decisions.append(dict(cycle=state["cycle"], phase=state["global_phase"],
                                  action=action, occupied_cells=int(state["dtse"][0].sum())))
            pending = (state, action)
            await env.set_action(action)
            await env.step_cycles(1)
        else:
            until_sample = 50 - state["cycle"] % 50
            count = min(state["next_decision_in_cycles"], until_sample,
                        horizon - state["cycle"])
            if count <= 0:
                raise RuntimeError(f"Invalid simulation schedule at cycle {state['cycle']}")
            await env.step_cycles(count)
        state = await env.read_state()
        if state["cycle"] >= next_progress:
            print(f"Progress {THREE} seed={seed} train={train}: "
                  f"cycle {state['cycle']}/{horizon}, "
                  f"passed={state['total_vehicles_passed']}", flush=True)
            next_progress += 1000
        if state["cycle"] % 50 == 0:
            samples.append(dict(cycle=state["cycle"],
                                average_speed=state["average_speed"],
                                queue_length=state["current_queue_length"],
                                throughput=state["total_vehicles_passed"]))
    if pending is not None:
        if "dtse" not in state:
            state = await env.read_state(force_dtse=True)
        previous, action = pending
        reward = env.transition_reward(previous, state)
        total_reward += reward
        if train and state["dqn_waiting_action"]:
            transitions.append((previous["dtse"].copy(), action,
                                state["delay_sq"] if agent.reward_mode == "reference" else reward,
                                state["dtse"].copy(), False,
                                (state["cycle"] - previous["cycle"]) * .1,
                                state["action_mask"].copy()))
    if not train and network_hash(agent) != before_policy:
        raise RuntimeError("3DQN weights changed during evaluation")
    errors = [m for m in env._server_messages if isinstance(m, dict) and m.get("type") in
              ("SimulationError", "RuntimeError", "GamaServerError", "SimulationErrorDialog")]
    if errors:
        raise RuntimeError(f"GAMA reported errors: {errors[:2]}")
    extras = await read_fields(env, EXTRA_METRICS)
    safety = await read_fields(env, SAFETY_FIELDS)
    created = state["total_vehicles_created"]
    if extras["ground_requests"] != created + extras["ground_pending"]:
        raise RuntimeError("Ground demand accounting differs between policies")
    metrics = dict(method=THREE, seed=seed, horizon=horizon, training=train,
                   epsilon=epsilon, throughput=state["total_vehicles_passed"],
                   created=created, requested=extras["ground_requests"],
                   external_queue=extras["ground_pending"],
                   remaining=created-state["total_vehicles_passed"],
                   queue_mean=extras["queue_time_integral"]/(horizon*.1),
                   stopped_vehicle_seconds=extras["queue_time_integral"],
                   external_vehicle_seconds=extras["external_wait_integral"],
                   accrued_wait_per_request=(extras["queue_time_integral"]+
                                             extras["external_wait_integral"])/
                       max(1, extras["ground_requests"]),
                   active_wait_mean=state["average_waiting_time"],
                   max_wait=extras["cumulative_max_wait"],
                   completed_travel_mean=state["average_travel_time"],
                   speed_mean=float(np.mean([s["average_speed"] for s in samples])),
                   reward=total_reward, decisions=len(decisions),
                   reward_mode=agent.reward_mode,
                   truncated_transition=bool(pending is not None and not state["dqn_waiting_action"]),
                   seconds=round(time.monotonic()-t0, 2),
                   policy_sha256=before_policy, demand_sha256=file_hash(demand_path),
                   **safety)
    output.mkdir(parents=True, exist_ok=True)
    for name, rows in (("series", samples), ("decisions", decisions)):
        with (output / f"{name}.csv").open("w", newline="") as stream:
            if rows:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    return metrics, transitions


async def run_job(spec, port, output, baseline, agent, horizon):
    label = spec["label"]
    marker = output / spec["folder"] / "metrics.json"
    signature = evaluation_signature(spec, baseline, agent, horizon)
    if not spec["train"] and marker.exists():
        saved = json.loads(marker.read_text())
        if (saved.get("method") == spec["method"] and
                saved.get("seed") == spec["seed"] and
                saved.get("horizon") == horizon and
                saved.get("demand_sha256") == file_hash(spec["demand"]) and
                saved.get("evaluation_sha256") == signature and
                all((marker.parent / name).exists() for name in ("series.csv", "decisions.csv"))):
            print(f"Reuse {spec['method']} seed={spec['seed']}", flush=True)
            return saved, []
    workdir = output / "server_ws" / str(port)
    logfile = output / "server_logs" / f"{label}.log"
    logfile.parent.mkdir(parents=True, exist_ok=True)
    manager = GamaServerManager(port=port, workdir=str(workdir), log_file=str(logfile))
    env = None
    try:
        await asyncio.to_thread(manager.start, reuse_running=False)
        if spec["method"] == THREE:
            env = GamaTrafficEnv(port=port, verbose=False,
                                 reward_scope=spec.get("reward_scope", "all"),
                                 reward_mode=agent.reward_mode,
                                 max_delay_sq=getattr(agent, "max_delay_sq", None))
            await env.setup()
            result = await run_three_episode(env, agent, spec["seed"], horizon,
                spec["demand"], output / spec["folder"],
                train=spec["train"], epsilon=spec["epsilon"],
                teacher_prob=spec.get("teacher_prob", 0.0))
        else:
            env = BenchmarkEnv(port, output=output)
            await env.setup()
            learner = Learners(42)
            if spec["method"] in METHODS[2:]:
                checkpoint = baseline / ("best_q.pt" if spec["method"] == "Q-Learning"
                                         else "best_dqn.pt")
                learner.load_policy(checkpoint, spec["method"])
            metrics = await run_episode(env, learner, spec["method"], spec["seed"],
                horizon, spec["demand"], output / spec["folder"])
            metrics.update(await read_fields(env, SAFETY_FIELDS))
            (output / spec["folder"] / "metrics.json").write_text(
                json.dumps(metrics, indent=2) + "\n")
            result = (metrics, [])
        result[0]["evaluation_sha256"] = signature
        marker.write_text(json.dumps(result[0], indent=2) + "\n")
        return result
    finally:
        try:
            if env is not None:
                await env.close()
        finally:
            await asyncio.to_thread(manager.stop)


async def run_group(specs, ports, output, baseline, agent, horizon):
    results = []
    for offset in range(0, len(specs), len(ports)):
        batch = specs[offset:offset+len(ports)]
        tasks = [asyncio.create_task(run_job(spec, port, output, baseline, agent, horizon))
                 for spec, port in zip(batch, ports)]
        try:
            current = await asyncio.gather(*tasks)
        except BaseException:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        results.extend(current)
    return results


def make_spec(method, seed, demand, folder, train=False, epsilon=0.0,
              reward_scope="all", teacher_prob=0.0):
    return dict(method=method, seed=seed, demand=demand,
                folder=folder, label=folder.replace("/", "_"),
                train=train, epsilon=epsilon, reward_scope=reward_scope,
                teacher_prob=teacher_prob)


def save_training_state(agent, training, path, worst_delay_sq):
    count = len(agent.buffer)
    replay = agent.buffer
    torch.save(dict(online=agent.online_net.state_dict(),
                    target=agent.target_net.state_dict(),
                    optimizer=agent.optimizer.state_dict(),
                    replay=dict(states=replay.states[:count].copy(),
                                next_states=replay.next_states[:count].copy(),
                                actions=replay.actions[:count].copy(),
                                rewards=replay.rewards[:count].copy(),
                                dones=replay.dones[:count].copy(),
                                discounts=replay.discounts[:count].copy(),
                                next_masks=replay.next_masks[:count].copy(),
                                pos=replay.pos, size=replay.size),
                    decisions=agent.decisions, eps=agent.eps,
                    updates=agent.update_count, losses=list(agent.last_losses),
                    numpy_rng=np.random.get_state(),
                    python_rng=random.getstate(),
                    torch_rng=torch.get_rng_state(),
                    episodes=len(training), worst_delay_sq=worst_delay_sq), path)


def load_training_state(agent, path):
    data = torch.load(path, map_location="cpu", weights_only=False)
    agent.online_net.load_state_dict(data["online"])
    agent.target_net.load_state_dict(data["target"])
    agent.optimizer.load_state_dict(data["optimizer"])
    replay = agent.buffer
    state = data["replay"]
    count = state["size"]
    for name in ("states", "next_states", "actions", "rewards", "dones", "discounts", "next_masks"):
        getattr(replay, name)[:count] = state[name]
    replay.pos, replay.size = state["pos"], count
    agent.decisions, agent.eps = data["decisions"], data["eps"]
    agent.update_count = data["updates"]
    agent.last_losses.extend(data["losses"])
    np.random.set_state(data["numpy_rng"])
    random.setstate(data["python_rng"])
    torch.set_rng_state(data["torch_rng"])
    return data["episodes"], data["worst_delay_sq"]


def write_report(rows, output, horizon, train_episodes, warmup, reward_scope,
                 baseline_reuse=None, reward_mode="queue_time", baseline_episodes=40):
    import pandas as pd
    frame = pd.DataFrame(rows)
    metrics = [
        ("throughput", "Xe mặt đất hoàn thành", True),
        ("queue_mean", "Hàng đợi trung bình trong mạng", False),
        ("accrued_wait_per_request", "Chờ tích lũy / yêu cầu xe", False),
        ("external_queue", "Yêu cầu còn ngoài mạng", False),
        ("completed_travel_mean", "Thời gian hành trình xe hoàn tất", False),
        ("max_wait", "Chờ lớn nhất trong mạng", False),
        ("speed_mean", "Tốc độ trung bình", True),
        ("total_tit_sum", "Tổng TIT", False),
        ("severe_conflicts_count", "Xung đột TTC < 1 s", False),
        ("hard_braking_count", "Phanh gấp", False),
    ]
    frame.to_csv(output / "per_run_metrics.csv", index=False)
    summary = frame.groupby("method")[[m[0] for m in metrics]].agg(["mean", "std"])
    summary.to_csv(output / "summary.csv")
    lines = ["# So sánh 3DQN với bốn bộ điều khiển GAMA", "",
             f"Mỗi chính sách được đánh giá lại trên cùng {len(frame.seed.unique())} seed, "
             f"mỗi seed {horizon} chu kỳ GAMA, dùng cùng CSV nhu cầu xe.",
             f"3DQN huấn luyện {train_episodes} episode, warm-up {warmup} transition "
             "để đối chiếu theo ngân sách episode của DQN cũ. Đây là cấu hình "
             "benchmark, khác warm-up 100.000 transition trong bài báo. "
             f"Trong benchmark baseline {baseline_episodes} episode, Q-Learning và DQN luân phiên "
             "thu thập episode nhưng cùng học từ mọi transition của toàn bộ tập huấn luyện. "
             "Checkpoint 3DQN được chọn theo queue_mean trên seed validation "
             "3001–3002 sau mỗi 10 episode, giống quy tắc của baseline. " +
             ("Reward GAMA: âm của thời gian xe dừng tích lũy / 50; discount 0,97^(dt/5), "
              "giống Q-Learning và DQN. Đây là thay đổi so với reward bài báo."
              if reward_mode == "queue_time" else f"Reward tham khảo, phạm vi: {reward_scope}."),
             "Cả năm phương pháp chờ đỏ toàn phần tối thiểu 2 s và xe thoát nút. "
             "3DQN có action mask chống bỏ đói pha; DTSE gộp theo chuyển động dùng tốc độ trung bình. "
             "Đây là bản thích nghi GAMA, chưa phải tái lập nguyên bản bài báo.", "",
             "| Chỉ số (mean ± SD) | " + " | ".join(ALL_METHODS) + " |",
             "|---|" + "---:|" * len(ALL_METHODS)]
    for key, title, _ in metrics:
        cells = [f"{summary.loc[method, (key, 'mean')]:.2f} ± "
                 f"{summary.loc[method, (key, 'std')]:.2f}"
                 for method in ALL_METHODS]
        lines.append("| " + title + " | " + " | ".join(cells) + " |")
    lines += ["", "Nguồn checkpoint và phiên bản môi trường được ghi trong manifest. " +
              (f"Lượt đánh giá baseline được tái sử dụng từ {baseline_reuse}; "
               "hash mã GAMA baseline và nhu cầu xe đã được đối chiếu. "
               if baseline_reuse else "Mọi lượt đánh giá chạy trên mã GAMA hiện tại. ") +
              "Thứ hạng từ tập seed nhỏ không chứng minh ưu thế tổng quát.",
              "", "Xem `manifest.json`, `per_run_metrics.csv`, `summary.csv`, "
              "`train/` và `test/` để kiểm tra kết quả từng seed."]
    (output / "report.md").write_text("\n".join(lines) + "\n")


async def main(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    baseline = args.baseline.resolve()
    old_manifest = json.loads((baseline / "manifest.json").read_text())
    if not args.ignore_code_hash and old_manifest.get("code_sha256") != source_hashes():
        raise RuntimeError("Baseline checkpoints were trained with different code/environment. "
                           "Use --ignore-code-hash if you intentionally want to benchmark with modified models.")
    if old_manifest["horizon"] != args.horizon:
        raise RuntimeError("Baseline and 3DQN must use the same episode horizon")
    train_seeds = old_manifest["train_seeds"][:args.train_episodes]
    validation_seeds = old_manifest["validation_seeds"]
    test_seeds = old_manifest["test_seeds"][:args.runs]
    if len(train_seeds) != args.train_episodes or len(test_seeds) != args.runs:
        raise ValueError("Requested more seeds than the paired baseline dataset contains")
    agent = ThreeDQNAgent(buffer_size=args.buffer_size, warmup=args.warmup,
                          batch_size=args.batch_size, eps_decay_steps=args.eps_decay_steps,
                          seed=args.agent_seed, device=torch.device("cpu"),
                          reward_mode=args.reward_mode, gamma=.97 if args.reward_mode == "queue_time" else .99)
    agent.max_delay_sq = args.max_delay_sq

    if args.pretrained_weights and args.pretrained_weights.exists():
        print(f"Loading pretrained 3DQN weights from {args.pretrained_weights}", flush=True)
        agent.load(args.pretrained_weights)
        if args.eps_start is not None:
            agent.eps = args.eps_start
            agent.eps_start = args.eps_start
        else:
            agent.eps = 0.15
            agent.eps_start = 0.15

    if args.expert_transitions and args.expert_transitions.exists():
        print(f"Pre-populating replay buffer from {args.expert_transitions}", flush=True)
        exp_data = torch.load(args.expert_transitions, map_location="cpu", weights_only=False)
        for s, a, r, s_next, done, dt, mask in exp_data:
            agent.store(s, a, r, s_next, done, seconds=dt, next_mask=mask)
        print(f"Replay buffer seeded with {len(agent.buffer)} transitions", flush=True)

    reuse = args.reuse_baselines.resolve() if args.reuse_baselines else None
    if reuse:
        reused_manifest = json.loads((reuse / "manifest.json").read_text())
        if not args.ignore_code_hash:
            for name in source_hashes():
                if reused_manifest["source_sha256"].get(name) != file_hash(ROOT / name):
                    raise RuntimeError(f"Cannot reuse baseline results: {name} changed")
        if reused_manifest.get("baseline_checkpoints") != {
                name: file_hash(baseline / name) for name in ("best_q.pt", "best_dqn.pt")}:
            raise RuntimeError("Cannot reuse baseline results: checkpoints differ")
        if reused_manifest["horizon"] != args.horizon or reused_manifest["test_seeds"][:args.runs] != test_seeds:
            raise RuntimeError("Cannot reuse baseline results: horizon or test seeds differ")
    manifest = dict(horizon=args.horizon, train_episodes=args.train_episodes, agent_seed=args.agent_seed,
                    runs=args.runs, workers=args.workers, train_seeds=train_seeds,
                    validation_seeds=validation_seeds, validate_every=10,
                    test_seeds=test_seeds, warmup=args.warmup,
                    buffer_size=args.buffer_size, batch_size=args.batch_size,
                    updates_per_transition=args.updates_per_transition,
                    eps_decay_steps=args.eps_decay_steps,
                    exploration="exponential_per_transition",
                    reward_mode=args.reward_mode,
                    reward=(f"{args.reward_scope}_incoming_squared_speed_delay_running_max"
                            if args.reward_mode == "reference" else "negative_integrated_queue/50; gamma=.97**(seconds/5)"),
                    reward_scope=args.reward_scope,
                    reuse_baselines=str(reuse) if reuse else None,
                    reused_results_sha256=file_hash(reuse / "test_results.json") if reuse else None,
                    baseline_manifest=str(baseline / "manifest.json"),
                    baseline_checkpoints={name:file_hash(baseline / name)
                                          for name in ("best_q.pt", "best_dqn.pt")},
                    demand_sha256={str(seed): file_hash(baseline / "demand" / f"{seed}.csv")
                                   for seed in (*train_seeds, *validation_seeds, *test_seeds)},
                    source_sha256=all_source_hashes())
    manifest_path = output / "manifest.json"
    if args.resume:
        if not manifest_path.exists() or json.loads(manifest_path.read_text()) != manifest:
            raise RuntimeError("Resume requires the same benchmark configuration and code")
    else:
        if (output / "training_log.json").exists():
            raise RuntimeError("Output already contains training; use --resume")
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    ports = [args.port+i for i in range(args.workers)]
    training = (json.loads((output / "training_log.json").read_text())
                if args.resume else [])
    worst_delay_sq = 0.0
    best = (json.loads((output / "validation_best.json").read_text())
            if args.resume and (output / "validation_best.json").exists()
            else {"episode": 0, "queue_mean": float("inf")})
    if args.resume:
        recovered, worst_delay_sq = load_training_state(agent, output / "training_state.pt")
        if recovered != len(training):
            raise RuntimeError("Training checkpoint and log disagree")
    async def validate(episode):
        nonlocal best
        specs = [make_spec(THREE, seed, baseline / "demand" / f"{seed}.csv",
                           f"validation/ep{episode}_{seed}",
                           reward_scope=args.reward_scope)
                 for seed in validation_seeds]
        results = await run_group(specs, ports, output, baseline, agent, args.horizon)
        score = float(np.mean([metrics["queue_mean"] for metrics, _ in results]))
        if score < best["queue_mean"]:
            best = {"episode": episode, "queue_mean": score}
            agent.save(output / "best_3dqn.pt")
        (output / "validation_best.json").write_text(json.dumps(best, indent=2) + "\n")
        print(f"Validation episode {episode}: queue_mean={score:.3f}, "
              f"best={best['episode']} ({best['queue_mean']:.3f})", flush=True)
    if args.resume and training and len(training) % 10 == 0 and best["episode"] < len(training):
        await validate(len(training))
    while len(training) < len(train_seeds):
        offset = len(training)
        boundary = min(len(train_seeds), ((offset // 10) + 1) * 10)
        block = train_seeds[offset:min(offset + args.workers, boundary)]
        specs = []
        for seed in block:
            epsilon = agent.eps
            ep_idx = len(training)
            t_prob = max(0.0, args.teacher_prob * (1.0 - ep_idx / max(1, args.teacher_decay_episodes)))
            specs.append(make_spec(THREE, seed, baseline / "demand" / f"{seed}.csv",
                                   f"train/{seed}", train=True, epsilon=epsilon,
                                   reward_scope=args.reward_scope, teacher_prob=t_prob))
        results = await run_group(specs, ports, output, baseline, agent, args.horizon)
        for spec, (metrics, transitions) in zip(specs, results):
            reward_total = 0.0
            for state, action, value, next_state, done, seconds, next_mask in transitions:
                if args.reward_mode == "reference":
                    worst_delay_sq = max(worst_delay_sq, value)
                    norm = (args.max_delay_sq if args.max_delay_sq is not None
                            and args.max_delay_sq > 0 else worst_delay_sq)
                    reward = 0.0 if norm == 0 else max(0.0, min(1.0, 1.0 - value / norm))
                else:
                    reward = value
                reward_total += reward
                agent.store(state, action, reward, next_state, done, seconds=seconds, next_mask=next_mask)
                if agent.can_update():
                    for _ in range(args.updates_per_transition):
                        agent.update()
                agent.decay_epsilon()
            metrics.update(reward=reward_total, episode=len(training)+1,
                           replay_size=len(agent.buffer),
                           updates=agent.update_count, avg_loss=agent.avg_loss)
            (output / spec["folder"] / "metrics.json").write_text(
                json.dumps(metrics, indent=2) + "\n")
            training.append(metrics)
            print(f"Learned {len(training)}/{args.train_episodes}: "
                  f"replay={len(agent.buffer)}, updates={agent.update_count}, "
                  f"queue={metrics['queue_mean']:.2f}", flush=True)
        agent.save(output / "3dqn_checkpoint.pt")
        (output / "training_log.json").write_text(json.dumps(training, indent=2) + "\n")
        save_training_state(agent, training, output / "training_state.pt", worst_delay_sq)
        if len(training) == boundary:
            await validate(len(training))
    agent.save(output / "3dqn_weights.pt")
    if not (output / "best_3dqn.pt").exists():
        await validate(len(training))
    agent.load(output / "best_3dqn.pt")
    specs = [make_spec(method, seed, baseline / "demand" / f"{seed}.csv",
                       f"test/{method.replace(' ', '_')}_{seed}",
                       reward_scope=args.reward_scope)
             for seed in test_seeds for method in ((THREE,) if reuse else ALL_METHODS)]
    results = await run_group(specs, ports, output, baseline, agent, args.horizon)
    rows = [metrics for metrics, _ in results]
    if reuse:
        old_rows = json.loads((reuse / "test_results.json").read_text())
        for row in old_rows:
            if row["method"] not in METHODS or row["seed"] not in test_seeds:
                continue
            if row["horizon"] != args.horizon or row["demand_sha256"] != file_hash(
                    baseline / "demand" / f"{row['seed']}.csv"):
                raise RuntimeError("Cannot reuse baseline result: demand differs")
            folder = f"{row['method'].replace(' ', '_')}_{row['seed']}"
            shutil.copytree(reuse / "test" / folder, output / "test" / folder,
                            dirs_exist_ok=True)
            rows.append(row)
    for seed in test_seeds:
        paired = [r for r in rows if r["seed"] == seed]
        if len(paired) != len(ALL_METHODS) or len({r["demand_sha256"] for r in paired}) != 1:
            raise RuntimeError(f"Unpaired demand for seed {seed}")
        if len({r["requested"] for r in paired}) != 1:
            raise RuntimeError(f"Ground requests differ across methods for seed {seed}")
    (output / "test_results.json").write_text(json.dumps(rows, indent=2) + "\n")
    write_report(rows, output, args.horizon, args.train_episodes, args.warmup,
                 args.reward_scope, reuse, args.reward_mode, old_manifest["train_episodes"])
    print(f"Benchmark complete: {output / 'report.md'}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--reuse-baselines", type=Path)
    parser.add_argument("--reward-scope", choices=("all", "near"), default="all")
    parser.add_argument("--reward-mode", choices=("queue_time", "reference"), default="queue_time",
                        help="queue_time matches Q/DQN's time-integrated GAMA objective; reference retains the paper/source reward")
    parser.add_argument("--max-delay-sq", type=float, default=None,
                        help="Optional fixed tsd_max; default follows the paper's running maximum")
    parser.add_argument("--horizon", type=int, default=8000)
    parser.add_argument("--train-episodes", type=int, default=40)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--port", type=int, default=6880)
    parser.add_argument("--agent-seed", type=int, default=42)
    parser.add_argument("--warmup", type=int, default=64)
    parser.add_argument("--buffer-size", type=int, default=20000)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--updates-per-transition", type=int, default=4)
    parser.add_argument("--eps-decay-steps", type=float, default=1200)
    parser.add_argument("--pretrained-weights", type=Path, default=None,
                        help="Path to pre-trained 3DQN weights (.pt)")
    parser.add_argument("--expert-transitions", type=Path, default=None,
                        help="Path to pre-collected expert transitions (.pt)")
    parser.add_argument("--teacher-prob", type=float, default=0.0,
                        help="Initial probability of following expert teacher during training")
    parser.add_argument("--teacher-decay-episodes", type=int, default=20,
                        help="Number of episodes over which teacher probability decays to 0")
    parser.add_argument("--eps-start", type=float, default=None,
                        help="Initial exploration rate epsilon")
    parser.add_argument("--ignore-code-hash", action="store_true",
                        help="Bypass strict baseline source code hash checks")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if min(arguments.horizon, arguments.train_episodes, arguments.runs,
           arguments.workers, arguments.warmup, arguments.buffer_size,
           arguments.batch_size, arguments.updates_per_transition) <= 0:
        parser.error("All counts must be positive")
    asyncio.run(main(arguments))
