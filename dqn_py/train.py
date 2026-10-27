#!/usr/bin/env python3
"""
==============================================================================
TRAIN 3DQN - Dueling Double DQN dieu khien den giao thong GAMA (Ho tro Da Worker)
==============================================================================
Kien truc tong the:
    train.py (PyTorch)  <--WebSocket/gama-client-->  N x gama-server (Workers)
                                                                 <--->  mo hinh
                                                                 intersection-dqn-python.gaml

Vong lap huan luyen da worker:
    N workers chay song song tren cac cong WebSocket tu [port] den [port + N - 1].
    Moi worker tu dong reset seed, lay state tu GAMA, goi agent.act(), ap dung action,
    day transition vao Replay Buffer chung va cap nhat mang Dueling Double DQN.

Ghi log:
    run/train_<timestamp>/training_log.csv   : 1 dong/episode
    run/train_<timestamp>/checkpoint.pt      : weights moi 10 episode
    run/train_<timestamp>/dqn_weights.pt     : weights cuoi cung (cho evaluate.py)

Vi du (1 Worker):
    python train.py --total-steps 1000000 --port 6868 --start-server

Vi du (20 Workers tren Colab Pro / Workstation):
    python train.py --total-steps 1000000 --workers 20 --port 6868 --start-server --batch-size 128
==============================================================================
"""

import argparse
import asyncio
import csv
import os
import subprocess
import sys
import time

from three_dqn_agent import ThreeDQNAgent
from gama_env import GamaTrafficEnv, featurize
from server_manager import (
    GamaServerManager, GamaServerError, find_gama_headless,
    ensure_xvfb_running, is_x11_server_running
)
from evaluate import evaluate_episode

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_args():
    p = argparse.ArgumentParser(description="Train GAMA DTSE Dueling Double DQN")
    p.add_argument("--episodes", type=int, default=0,
                   help="Optional episode limit (0 = follow total-steps)")
    p.add_argument("--total-steps", type=int, default=1_000_000,
                   help="Agent decisions; use 1000000 or 5000000 as in the paper")
    p.add_argument("--episode-horizon", type=int, default=8000,
                   help="So cycle GAMA moi episode (8000 cycle = 800s)")
    p.add_argument("--port", type=int, default=6868,
                   help="Cong WebSocket bat dau (worker i dung cong port + i)")
    p.add_argument("--workers", type=int, default=1,
                   help="So luong GAMA server / worker chay song song (vi du: 4, 16, 20)")
    p.add_argument("--updates-per-step", type=int, default=1,
                   help="So lan cap nhat gradient moi transition hop le (default 1, co the tang 2-4)")
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
    if args.episode_horizon <= 100 or args.total_steps <= 0 or args.validate_every <= 0 or args.workers <= 0:
        p.error("Horizon, total-steps, validate-every, and workers must be positive")
    if args.gamma is None:
        args.gamma = .97 if args.reward_mode == "queue_time" else .99
    return args


async def start_all_managers(managers, startup_timeout=300.0):
    """Khoi dong tat ca cac tien trinh gama-server dong thoi thay vi tuan tu."""
    target_display = os.environ.get("DISPLAY") or ":99"
    if sys.platform.startswith("linux") and not is_x11_server_running(target_display):
        ensure_xvfb_running(":99")
        target_display = ":99"
        os.environ["DISPLAY"] = ":99"

    pending = []
    for m in managers:
        if m.is_port_open():
            print(f"[GamaServer] Cong {m.port} da mo -> dung lai server hien co.")
            continue
        os.makedirs(m.workdir, exist_ok=True)
        m._log_fh = open(m.log_file, "w")
        configuration = os.path.join(m.workdir, "configuration")
        workspace = os.path.join(m.workdir, "workspace")
        os.makedirs(workspace, exist_ok=True)
        if not m.gama_headless or not os.path.isfile(m.gama_headless):
            m.gama_headless = find_gama_headless(m.gama_headless)
        if not m.gama_headless or not os.path.isfile(m.gama_headless):
            raise GamaServerError(f"Khong tim thay file gama-headless tai: '{m.gama_headless}'")
        if sys.platform == "win32":
            cmd = ["cmd.exe", "/c", m.gama_headless, "-socket", str(m.port),
                   "-configuration", configuration, "-data", workspace]
            exec_cwd = os.path.dirname(m.gama_headless)
        else:
            cmd = ["bash", m.gama_headless, "-socket", str(m.port),
                   "-configuration", configuration, "-data", workspace]
            exec_cwd = m.workdir
        env = os.environ.copy()
        if sys.platform.startswith("linux"):
            env["DISPLAY"] = target_display
            env["LIBGL_ALWAYS_SOFTWARE"] = "1"
            env["LIBGL_DRI3_DISABLE"] = "1"
            env["LIBGL_DRI2_DISABLE"] = "1"
            env["GALLIUM_DRIVER"] = "llvmpipe"
            env["MESA_LOADER_DRIVER_OVERRIDE"] = "llvmpipe"
            env["__GLX_VENDOR_LIBRARY_NAME"] = "mesa"
            env["LIBGL_ALWAYS_INDIRECT"] = "0"
            env["GDK_BACKEND"] = "x11"
            env["NO_AT_BRIDGE"] = "1"
            # Ngăn JVM AWT/SWT gọi hàm OpenGL bị crash trên Xvfb
            java_opts = env.get("_JAVA_OPTIONS", "")
            extra_opts = [
                "-Dsun.java2d.opengl=false",
                "-Dsun.java2d.xrender=false",
                "-Djava.awt.headless=false",
            ]
            for opt in extra_opts:
                if opt.split("=")[0] not in java_opts:
                    java_opts = (java_opts + " " + opt).strip()
            env["_JAVA_OPTIONS"] = java_opts
        m.process = subprocess.Popen(
            cmd, cwd=exec_cwd, stdout=m._log_fh, stderr=subprocess.STDOUT,
            start_new_session=True, env=env,
        )
        pending.append(m)
        if len(managers) > 1:
            await asyncio.sleep(0.3)

    if not pending:
        return True

    ports_str = f"{pending[0].port}-{pending[-1].port}" if len(pending) > 1 else str(pending[0].port)
    print(f"[GamaServer] Dang cho {len(pending)} servers khoi dong tren port {ports_str}...")
    t0 = time.time()
    unopened = set(pending)
    while unopened and time.time() - t0 < startup_timeout:
        for m in list(unopened):
            if m.process and m.process.poll() is not None:
                raise GamaServerError(
                    f"gama-server tren port {m.port} ket thuc som voi code {m.process.returncode}. Log:\n{m._tail_log()}"
                )
            if m.is_port_open():
                unopened.remove(m)
        if unopened:
            await asyncio.sleep(1.5)

    if unopened:
        failed_ports = [m.port for m in unopened]
        for m in pending:
            m.stop()
        raise GamaServerError(f"Timeout {startup_timeout}s cho cac servers mo cong: {failed_ports}")

    print(f"[GamaServer] Tat ca {len(pending)} GAMA servers da mo cong (sau {time.time() - t0:.1f}s). Cho 5s de on dinh WebSocket...")
    await asyncio.sleep(5.0)
    return True


class DiscardSamples:
    def writerow(self, row):
        pass


async def amain(args):
    stamp = time.strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(BASE_DIR, "run", f"train_{stamp}")
    os.makedirs(outdir, exist_ok=True)
    print(f"[Train] Ket qua se luu tai: {outdir}")
    print(f"[Train] So luong Workers song song: {args.workers}")

    ports = [args.port + i for i in range(args.workers)]
    managers = []
    envs = []

    # 1. Khoi dong cac server
    if args.start_server:
        for port in ports:
            workdir = os.path.join(outdir, "server_ws", f"port_{port}")
            logfile = os.path.join(outdir, "server_logs", f"port_{port}.log")
            managers.append(GamaServerManager(port=port, workdir=workdir, log_file=logfile))
        await start_all_managers(managers)

    try:
        # 2. Khoi tao cac ket noi WebSocket Environment song song kem retry
        print(f"[Train] Dang ket noi WebSocket den {len(ports)} GAMA servers...")

        async def init_env(port):
            env = GamaTrafficEnv(host=args.host, port=port,
                                 model_path=args.model_path, reward_mode=args.reward_mode,
                                 max_delay_sq=args.max_delay_sq, verbose=(args.workers == 1))
            await env.setup(max_retries=15, retry_delay=3.0)
            return env

        envs = list(await asyncio.gather(*(init_env(port) for port in ports)))
        print(f"[Train] Da ket noi thanh cong tat ca {len(envs)} workers!")

        agent = ThreeDQNAgent(
            lr=args.lr, gamma=args.gamma, buffer_size=args.buffer_size,
            warmup=args.warmup, batch_size=args.batch_size, tau=args.tau,
            eps_start=args.eps_start, eps_decay_steps=args.eps_decay_steps,
            eps_min=args.eps_min, seed=args.seed_base, reward_mode=args.reward_mode)
        print(f"[Train] Device: {agent.device} | DTSE: 3x8x20 | Actions: 4 phases | Batch Size: {args.batch_size}")

        # 3. Khoi tao Log
        log_path = os.path.join(outdir, "training_log.csv")
        with open(log_path, "w", newline="") as f:
            csv.writer(f).writerow([
                "episode", "seed", "decisions", "episode_reward", "epsilon",
                "avg_loss", "updates", "throughput", "vehicles_created",
                "avg_waiting_time", "max_waiting_time", "avg_speed",
                "avg_travel_time", "final_queue", "wall_seconds",
            ])

        best_validation_queue = float("inf")
        ep_counter = 0
        csv_lock = asyncio.Lock()
        val_lock = asyncio.Lock()
        train_start_time = time.time()

        async def worker_loop(worker_id, env):
            nonlocal ep_counter, best_validation_queue
            while agent.decisions < args.total_steps and (args.episodes == 0 or ep_counter < args.episodes):
                async with csv_lock:
                    if agent.decisions >= args.total_steps or (args.episodes > 0 and ep_counter >= args.episodes):
                        break
                    ep_counter += 1
                    ep = ep_counter

                seed = args.seed_base + ep
                t0 = time.time()
                try:
                    # Tranh nghen CPU/IO khi tat ca workers dong loat gui lenh load GAML o episode dau tien
                    if worker_id > 0 and ep <= args.workers:
                        await asyncio.sleep(worker_id * 2.0)

                    state = await env.reset(seed=seed)
                    await env.step_cycles(state["next_decision_in_cycles"])
                    state = await env.read_state()
                    if not state["dqn_waiting_action"]:
                        continue

                    ep_reward = 0.0
                    decisions = 0
                    done = False
                    while not done and agent.decisions < args.total_steps:
                        state_vec = featurize(state)
                        action = agent.act(state_vec, action_mask=state["action_mask"],
                                           force_random=len(agent.buffer) < args.warmup)
                        next_state, reward, _, info = await env.step(action, horizon=args.episode_horizon)
                        if info["bootstrap_valid"]:
                            agent.store(state_vec, action, reward, featurize(next_state), False,
                                        seconds=info["elapsed_seconds"], next_mask=next_state["action_mask"])
                            if agent.can_update():
                                for _ in range(args.updates_per_step):
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

                    # Validation
                    marker = ""
                    if ep % args.validate_every == 0 or agent.decisions >= args.total_steps:
                        async with val_lock:
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

                    async with csv_lock:
                        with open(log_path, "a", newline="") as f:
                            csv.writer(f).writerow(row)
                        if ep % 10 == 0 or agent.decisions >= args.total_steps:
                            agent.save(os.path.join(outdir, "checkpoint.pt"))

                    prefix = f"[W{worker_id:02d}] " if args.workers > 1 else ""
                    pct = min(100.0, (agent.decisions / args.total_steps) * 100.0)
                    elapsed_total = time.time() - train_start_time
                    if agent.decisions > 0:
                        eta_sec = (elapsed_total / agent.decisions) * max(0, args.total_steps - agent.decisions)
                        if eta_sec >= 3600:
                            eta_str = f"{int(eta_sec // 3600)}h{int((eta_sec % 3600) // 60):02d}m"
                        elif eta_sec >= 60:
                            eta_str = f"{int(eta_sec // 60)}m{int(eta_sec % 60):02d}s"
                        else:
                            eta_str = f"{int(eta_sec)}s"
                    else:
                        eta_str = "--"

                    bar_len = 10
                    filled = int(bar_len * pct / 100.0)
                    bar = "=" * filled + "-" * (bar_len - filled)

                    print(f"{prefix}[Ep {ep:5d} | [{bar}] {pct:5.1f}% | {agent.decisions:,}/{args.total_steps:,} | ETA: {eta_str}] "
                          f"reward={ep_reward:7.1f} | eps={agent.eps:.3f} | loss={agent.avg_loss:.4f} | "
                          f"passed={state['total_vehicles_passed']:3d} | wait={state['average_waiting_time']:5.2f}s | "
                          f"queue={state['current_queue_length']:2d} | {wall:4.1f}s{marker}")

                except Exception as ex:
                    err_msg = str(ex) or type(ex).__name__
                    print(f"[W{worker_id:02d}] Gap loi o episode {ep}: {err_msg}. Dang khoi phuc ket noi WebSocket...")
                    try:
                        await env.close()
                    except Exception:
                        pass
                    await asyncio.sleep(2.0)
                    try:
                        await env.setup(max_retries=10, retry_delay=3.0)
                        print(f"[W{worker_id:02d}] Da ket noi lai WebSocket thanh cong tren port {env.port}.")
                    except Exception as re_err:
                        print(f"[W{worker_id:02d}] Khong the ket noi lai WebSocket port {env.port}: {re_err}")

        # 4. Chay cac worker tasks
        worker_tasks = [asyncio.create_task(worker_loop(i, env)) for i, env in enumerate(envs)]
        await asyncio.gather(*worker_tasks)

        # 5. Luu weights cuoi cung
        final_path = os.path.join(outdir, "dqn_weights.pt")
        agent.save(final_path)
        print("\n[Train] HOAN TAT HUAN LUYEN.")
        print(f"[Train] Weights cuoi cung : {final_path}")
        print(f"[Train] Weights tot nhat  : {os.path.join(outdir, 'best_weights.pt')}")
        print(f"[Train] Log huan luyen    : {log_path}")

    finally:
        for env in envs:
            try:
                await env.close()
            except Exception:
                pass
        if not args.keep_server:
            for m in managers:
                try:
                    m.stop()
                except Exception:
                    pass


if __name__ == "__main__":
    asyncio.run(amain(parse_args()))
