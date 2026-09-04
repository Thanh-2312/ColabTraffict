#!/usr/bin/env python3
"""
Benchmark 4 thuật toán điều khiển đèn giao thông trên GAMA:

    Fixed-Time       -> GAMA headless batch (my_batch_experiment, 2000 cycles)
    MaxPressure      -> như trên
    Q-Learning       -> như trên
    Deep Q-Learning  -> gama-server (port 6868) + dqn_py/evaluate.py,
                        chính sách greedy (eps=0) với weights đã train

Quy trình:
    1. Chạy N lần độc lập cho mỗi thuật toán (--runs, mặc định 5).
    2. Tổng hợp bảng 6 tiêu chí dạng mean ± std, chọn thuật toán tốt nhất.
    3. Vẽ biểu đồ 6 panel từ series đại diện (run có throughput ở median).

Vì sao phải chạy N lần: batch headless của GAMA không tái lập bit-perfect dù
khai báo seed (seed ngẫu nhiên cho mỗi simulation + thứ tự nội bộ của JVM),
nên kết quả 1 lần chạy có nhiễu ±3-5% — so sánh hợp lệ cần nhiều lần chạy.

Kết quả (thư mục comparison_results/):
    - {fixed_time,maxpressure,q_learning,dqn}_metrics.csv : series đại diện
    - traffic_comparison_4models_6metrics.png             : biểu đồ 6 panel
    - bảng mean ± std in ra console

Cách chạy:
    python3 scripts/compare_4_models.py --runs 5      # benchmark đầy đủ
    python3 scripts/compare_4_models.py --plot-only   # tổng hợp + vẽ từ CSV cũ
"""

import argparse
import os
import re
import subprocess

import pandas as pd
import matplotlib.pyplot as plt

# --------------------------------------------------------------- Cấu hình ---
BASE_DIR = "/Users/mac/Documents/GAMA"
OUTPUT_DIR = os.path.join(BASE_DIR, "comparison_results")

GAMA_HEADLESS = "/Applications/Gama.app/Contents/headless/gama-headless.sh"
BATCH_EXPERIMENT = "my_batch_experiment"
HORIZON_CYCLES = 2000        # mỗi lần chạy: 2000 cycles = 200 giây mô phỏng
FIRST_SEED = 5001            # DQN: episode i dùng seed = FIRST_SEED + i - 1
                             # (3 model batch để GAMA tự chọn seed mỗi lần chạy)
N_RUNS_DEFAULT = 5

# Tên hiển thị -> (file GAML batch, tên file CSV kết quả)
BATCH_MODELS = {
    "Fixed-Time": ("intersection-fixed-time.gaml", "fixed_time"),
    "MaxPressure": ("intersection-maxpressure.gaml", "maxpressure"),
    "Q-Learning": ("intersection-qlearning.gaml", "q_learning"),
}
DQN_NAME = "Deep Q-Learning"
MODEL_NAMES = [*BATCH_MODELS, DQN_NAME]

DQN_DIR = os.path.join(BASE_DIR, "dqn_py")
DQN_PYTHON = os.path.join(DQN_DIR, "venv", "bin", "python")
DQN_EVAL = os.path.join(DQN_DIR, "evaluate.py")
DQN_WEIGHTS = os.path.join(DQN_DIR, "run", "train_20260829_153936", "best_weights.pt")
DQN_PORT = 6868              # gama-server chạy sẵn (kiểm tra: lsof -i :6868)

# Dòng "METRIC_CSV,cycle,passed,avg_wait,queue,speed,travel,max_wait" mà
# các model GAML in ra mỗi 10 cycles
METRIC_CSV_RE = re.compile(
    r"METRIC_CSV,(\d+),(\d+),([\d.]+),(\d+),([\d.]+),([\d.]+),([\d.]+)")

CHART_PATH = os.path.join(OUTPUT_DIR, "traffic_comparison_4models_6metrics.png")
COLORS = {"Fixed-Time": "#e74c3c", "MaxPressure": "#2ecc71",
          "Q-Learning": "#3498db", DQN_NAME: "#9b59b6"}


# --------------------------------------------------- Chạy 1 model batch GAMA
def run_batch(model_file, label):
    """Chạy 1 lần batch headless, trả về DataFrame metrics (199 dòng)."""
    print(f"🚀 [{label}] batch headless, {HORIZON_CYCLES} cycles...", flush=True)
    cmd = ["bash", GAMA_HEADLESS, "-batch", BATCH_EXPERIMENT, model_file]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, bufsize=1)

    records = []
    for line in iter(process.stdout.readline, ""):
        m = METRIC_CSV_RE.search(line)
        if not m:
            continue
        cycle = int(m.group(1))
        records.append({
            "cycle": cycle,
            "time_sec": cycle * 0.1,
            "throughput": int(m.group(2)),
            "avg_waiting_time": float(m.group(3)),
            "queue_length": int(m.group(4)),
            "avg_speed": float(m.group(5)),
            "avg_travel_time": float(m.group(6)),
            "max_waiting_time": float(m.group(7)),
        })
    process.stdout.close()
    process.wait(timeout=60)

    if not records:
        raise RuntimeError(f"[{label}] Không thu được dòng METRIC_CSV nào - "
                           f"kiểm tra model GAML hoặc tên experiment.")
    df = pd.DataFrame(records)
    print(f"✅ [{label}] {len(df)} mẫu (cycle {df['cycle'].min()}"
          f"-{df['cycle'].max()}), throughput={df['throughput'].iloc[-1]}",
          flush=True)
    return df


# ------------------------------------------------------- Đánh giá Deep Q-Net
def run_dqn(n_episodes):
    """Chạy evaluate.py qua gama-server, trả về list DataFrame mỗi episode."""
    print(f"🚀 [{DQN_NAME}] greedy (eps=0) qua gama-server :{DQN_PORT}, "
          f"{n_episodes} episodes (seed {FIRST_SEED}..{FIRST_SEED + n_episodes - 1})...",
          flush=True)
    cmd = [DQN_PYTHON, DQN_EVAL,
           "--weights", DQN_WEIGHTS,
           "--episodes", str(n_episodes),
           "--episode-horizon", str(HORIZON_CYCLES),
           "--seed-base", str(FIRST_SEED - 1),   # ep i -> seed = FIRST_SEED + i - 1
           "--port", str(DQN_PORT),
           "--host", "localhost"]
    process = subprocess.Popen(cmd, cwd=DQN_DIR, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in iter(process.stdout.readline, ""):
        print(f"   [DQN] {line.rstrip()}", flush=True)
    process.stdout.close()
    process.wait(timeout=60)

    if process.returncode != 0:
        raise RuntimeError(f"[{DQN_NAME}] evaluate.py thoát với mã "
                           f"{process.returncode} - gama-server đang chạy ở "
                           f"port {DQN_PORT} không?")

    csv_path = os.path.join(OUTPUT_DIR, "dqn_metrics.csv")
    df = pd.read_csv(csv_path)
    episodes = [g.reset_index(drop=True) for _, g in df.groupby("episode")]
    print(f"✅ [{DQN_NAME}] {len(episodes)} episode -> {csv_path}", flush=True)
    return episodes


# ------------------------------------------------------------- Tổng hợp ------
# (key cột, nhãn bảng, giá trị cao hơn là tốt hơn)
METRICS = [
    ("throughput", "1. Throughput (Tổng xe qua)", True),
    ("avg_waiting_time", "2. Average Waiting Time", False),
    ("queue_length", "3. Average Queue Length", False),
    ("avg_speed", "4. Average Speed", True),
    ("avg_travel_time", "5. Average Travel Time", False),
    ("max_waiting_time", "6. Max Waiting Time (Fairness)", False),
]


def per_run_values(df):
    """Giá trị 6 tiêu chí của MỘT lần chạy:
    throughput & travel time lấy giá trị cuối, max wait lấy max,
    wait/queue/speed lấy trung bình theo thời gian."""
    return {
        "throughput": df["throughput"].iloc[-1],
        "avg_waiting_time": df["avg_waiting_time"].mean(),
        "queue_length": df["queue_length"].mean(),
        "avg_speed": df["avg_speed"].mean(),
        "avg_travel_time": df["avg_travel_time"].iloc[-1],
        "max_waiting_time": df["max_waiting_time"].max(),
    }


def mean_std(values):
    m = sum(values) / len(values)
    sd = (sum((x - m) ** 2 for x in values) / len(values)) ** 0.5
    return m, sd


def report(reps, n_runs):
    """In bảng 6 tiêu chí dạng mean ± std trên n_runs lần chạy, chọn tốt nhất."""
    runs = {name: [per_run_values(df) for df in reps[name]] for name in MODEL_NAMES}

    print("\n" + "=" * 140)
    print(f"  BẢNG SO SÁNH 4 THUẬT TOÁN — MEAN ± STD TRÊN {n_runs} LẦN CHẠY ĐỘC LẬP "
          f"(mỗi lần {HORIZON_CYCLES} cycles)")
    print("=" * 140)
    header = f"{'Tiêu chí':<34} |" + "".join(f"{n:>17} |" for n in MODEL_NAMES) \
             + " Tốt nhất (mean)"
    print(header)
    print("-" * 140)

    wins = {name: 0 for name in MODEL_NAMES}
    for key, label, higher_better in METRICS:
        means = {name: mean_std([r[key] for r in runs[name]])[0] for name in MODEL_NAMES}
        best = max(means, key=means.get) if higher_better else min(means, key=means.get)
        wins[best] += 1

        cells = ""
        for name in MODEL_NAMES:
            m, sd = mean_std([r[key] for r in runs[name]])
            cells += f"{m:9.2f}±{sd:<5.2f} |"
        print(f"{label:<34} |{cells} 🏆 {best}")

    print("=" * 140)
    print("  Số tiêu chí thắng (theo mean): "
          + " | ".join(f"{n}: {w}" for n, w in wins.items()))
    print("  Lưu ý: throughput/speed cao hơn là tốt; các tiêu chí còn lại thấp hơn là tốt.")


# ------------------------------------------------------------- Biểu đồ ------
def representative(df_list):
    """Chọn series đại diện để vẽ: run có throughput cuối ở vị trí median."""
    if len(df_list) == 1:
        return df_list[0]
    finals = [d["throughput"].iloc[-1] for d in df_list]
    return df_list[finals.index(sorted(finals)[len(finals) // 2])]


def save_series(df, csv_stem):
    """Lưu series đại diện của 1 model ra CSV (dùng lại cho --plot-only)."""
    path = os.path.join(OUTPUT_DIR, f"{csv_stem}_metrics.csv")
    df.to_csv(path, index=False)


def plot(series_by_model):
    """Vẽ 6 panel (3x2), mỗi panel một tiêu chí so sánh 4 thuật toán."""
    plt.style.use("seaborn-v0_8-whitegrid"
                  if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, axes = plt.subplots(3, 2, figsize=(16, 14))
    fig.suptitle("So Sánh 4 Thuật Toán Điều Khiển Đèn Giao Thông "
                 "(Fixed-Time, MaxPressure, Q-Learning, Deep Q-Learning)\n"
                 f"2000 cycles (200s) mỗi lần chạy — GAMA Platform",
                 fontsize=15, fontweight="bold", y=0.99)

    panels = [
        ("throughput", "1. Throughput [↑ Tốt]", "Số xe"),
        ("avg_waiting_time", "2. Average Waiting Time [↓ Tốt]", "Giây (s)"),
        ("queue_length", "3. Average Queue Length [↓ Tốt]", "Số xe"),
        ("avg_speed", "4. Average Speed [↑ Tốt]", "km/h"),
        ("avg_travel_time", "5. Average Travel Time [↓ Tốt]", "Giây (s)"),
        ("max_waiting_time", "6. Max Waiting Time (Fairness) [↓ Tốt]", "Giây (s)"),
    ]
    for idx, (column, title, ylabel) in enumerate(panels):
        ax = axes[idx // 2][idx % 2]
        for name in MODEL_NAMES:
            df = series_by_model[name]
            is_dqn = name == DQN_NAME
            ax.plot(df["time_sec"], df[column], label=name, color=COLORS[name],
                    lw=2, linestyle="--" if is_dqn else "-")
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_xlabel("Thời gian mô phỏng (giây)")
        ax.set_ylabel(ylabel)
        if idx == 0:
            ax.legend(loc="upper left")
        ax.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    plt.savefig(CHART_PATH, dpi=300)
    plt.close(fig)
    print(f"\n📊 Biểu đồ so sánh 4 mô hình (300 DPI): {CHART_PATH}", flush=True)


# ------------------------------------------------------------------ main ----
def load_saved_series():
    """Mode --plot-only: đọc lại CSV đã lưu, mỗi model 1 series đại diện.
    CSV của DQN chứa nhiều episode -> chọn episode đại diện (median)."""
    series = {}
    for name in MODEL_NAMES:
        csv_stem = BATCH_MODELS.get(name, (None, "dqn"))[1]
        df = pd.read_csv(os.path.join(OUTPUT_DIR, f"{csv_stem}_metrics.csv"))
        if "episode" in df.columns and df["episode"].nunique() > 1:
            episodes = [g.reset_index(drop=True) for _, g in df.groupby("episode")]
            df = representative(episodes)
        series[name] = df.drop(columns=["episode"], errors="ignore")
    return series


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark 4 thuật toán điều khiển đèn giao thông trên GAMA")
    parser.add_argument("--runs", type=int, default=N_RUNS_DEFAULT,
                        help=f"Số lần chạy độc lập mỗi thuật toán "
                             f"(mặc định {N_RUNS_DEFAULT})")
    parser.add_argument("--plot-only", action="store_true",
                        help="Không chạy mô phỏng, chỉ tổng hợp + vẽ từ CSV đã lưu")
    args = parser.parse_args()
    n_runs = 1 if args.plot_only else args.runs

    print("=" * 140)
    print(" BENCHMARK 4 THUẬT TOÁN: FIXED-TIME | MAXPRESSURE | Q-LEARNING | "
          "DEEP Q-LEARNING")
    print(f" {n_runs} lần chạy độc lập mỗi thuật toán | "
          f"{HORIZON_CYCLES} cycles/lần | output: {OUTPUT_DIR}")
    print("=" * 140, flush=True)

    if args.plot_only:
        series = load_saved_series()
        reps = {name: [series[name]] for name in MODEL_NAMES}
    else:
        reps = {name: [] for name in MODEL_NAMES}
        for name, (model_file, csv_stem) in BATCH_MODELS.items():
            model_path = os.path.join(BASE_DIR, "Traffic/models", model_file)
            reps[name] = [run_batch(model_path, name) for _ in range(n_runs)]
            save_series(representative(reps[name]), csv_stem)
        reps[DQN_NAME] = run_dqn(n_runs)

    report(reps, n_runs)
    plot({name: representative(reps[name]) for name in MODEL_NAMES})
    print(f"\n🎉 Hoàn thành benchmark ({n_runs} lần chạy/thuật toán)!")


if __name__ == "__main__":
    main()


