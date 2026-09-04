#!/usr/bin/env python3
"""
==============================================================================
TRAFFIC SIGNAL CONTROL BENCHMARK: FIXED-TIME vs MAXPRESSURE vs Q-LEARNING
==============================================================================
So sánh 6 tiêu chí đánh giá hiệu năng giao thông trên 3 thuật toán điều khiển:
  1. Throughput (Tổng số xe qua ngã tư)          [Cao hơn là tốt hơn]
  2. Average Waiting Time (Thời gian chờ TB)     [Thấp hơn là tốt hơn]
  3. Average Queue Length (Chiều dài hàng đợi TB)[Thấp hơn là tốt hơn]
  4. Average Speed (Vận tốc trung bình)          [Cao hơn là tốt hơn]
  5. Average Travel Time (Thời gian hành trình)  [Thấp hơn là tốt hơn]
  6. Max Waiting Time (Thời gian chờ tối đa)     [Thấp hơn là tốt hơn]
==============================================================================
"""

import os
import sys
import subprocess
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Đường dẫn GAMA và các file mô hình
GAMA_HEADLESS = "/Applications/Gama.app/Contents/headless/gama-headless.sh"
BASE_DIR = "/Users/mac/Documents/GAMA"
FIXED_TIME_MODEL = os.path.join(BASE_DIR, "Traffic/models/intersection-fixed-time.gaml")
MAXPRESSURE_MODEL = os.path.join(BASE_DIR, "Traffic/models/intersection-maxpressure.gaml")
QLEARNING_MODEL = os.path.join(BASE_DIR, "Traffic/models/intersection-qlearning.gaml")
OUTPUT_DIR = os.path.join(BASE_DIR, "comparison_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_simulation(model_path, model_name):
    """Chạy mô phỏng GAMA headless và trích xuất dữ liệu 6 metrics."""
    print(f"\n🚀 Đang chạy mô phỏng: {model_name}...")
    cmd = [
        "bash", GAMA_HEADLESS,
        "-batch", "my_batch_experiment",
        model_path
    ]
    
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1
    )
    
    records = []
    pattern = re.compile(r"METRIC_CSV,(\d+),(\d+),([\d\.]+),(\d+),([\d\.]+),([\d\.]+),([\d\.]+)")
    
    for line in iter(process.stdout.readline, ''):
        match = pattern.search(line)
        if match:
            cycle = int(match.group(1))
            passed = int(match.group(2))
            avg_wait = float(match.group(3))
            queue = int(match.group(4))
            avg_speed = float(match.group(5))
            avg_travel = float(match.group(6))
            max_wait = float(match.group(7))
            
            records.append({
                "cycle": cycle,
                "time_sec": cycle * 0.1,
                "throughput": passed,
                "avg_waiting_time": avg_wait,
                "queue_length": queue,
                "avg_speed": avg_speed,
                "avg_travel_time": avg_travel,
                "max_waiting_time": max_wait
            })
            if cycle % 400 == 0:
                print(f"   ⏳ [{model_name}] Cycle {cycle:4d} ({cycle*0.1:4.0f}s) | Xe qua: {passed:3d} | Hàng đợi: {queue:2d} | Vận tốc: {avg_speed:4.1f} km/h")
                
    process.wait()
    df = pd.DataFrame(records)
    csv_path = os.path.join(OUTPUT_DIR, f"{model_name.lower().replace('-', '_')}_metrics.csv")
    df.to_csv(csv_path, index=False)
    print(f"✅ Hoàn thành {model_name}! Thu thập được {len(df)} mẫu dữ liệu. Đã lưu: {csv_path}")
    return df

def generate_comparison_report(df_ft, df_mp, df_ql):
    """Tính toán bảng so sánh chi tiết 6 tiêu chí cho cả 3 thuật toán."""
    metrics_summary = [
        {
            "id": 1,
            "name": "Throughput (Tổng xe qua)",
            "unit": "xe",
            "higher_is_better": True,
            "ft_val": df_ft["throughput"].iloc[-1],
            "mp_val": df_mp["throughput"].iloc[-1],
            "ql_val": df_ql["throughput"].iloc[-1],
        },
        {
            "id": 2,
            "name": "Average Waiting Time",
            "unit": "s",
            "higher_is_better": False,
            "ft_val": df_ft["avg_waiting_time"].mean(),
            "mp_val": df_mp["avg_waiting_time"].mean(),
            "ql_val": df_ql["avg_waiting_time"].mean(),
        },
        {
            "id": 3,
            "name": "Average Queue Length",
            "unit": "xe",
            "higher_is_better": False,
            "ft_val": df_ft["queue_length"].mean(),
            "mp_val": df_mp["queue_length"].mean(),
            "ql_val": df_ql["queue_length"].mean(),
        },
        {
            "id": 4,
            "name": "Average Speed",
            "unit": "km/h",
            "higher_is_better": True,
            "ft_val": df_ft["avg_speed"].mean(),
            "mp_val": df_mp["avg_speed"].mean(),
            "ql_val": df_ql["avg_speed"].mean(),
        },
        {
            "id": 5,
            "name": "Average Travel Time",
            "unit": "s",
            "higher_is_better": False,
            "ft_val": df_ft["avg_travel_time"].iloc[-1],
            "mp_val": df_mp["avg_travel_time"].iloc[-1],
            "ql_val": df_ql["avg_travel_time"].iloc[-1],
        },
        {
            "id": 6,
            "name": "Max Waiting Time (Fairness)",
            "unit": "s",
            "higher_is_better": False,
            "ft_val": df_ft["max_waiting_time"].max(),
            "mp_val": df_mp["max_waiting_time"].max(),
            "ql_val": df_ql["max_waiting_time"].max(),
        }
    ]
    
    print("\n" + "="*95)
    print("        BẢNG TỔNG HỢP SO SÁNH 6 TIÊU CHÍ HIỆU NĂNG: FIXED-TIME vs MAXPRESSURE vs Q-LEARNING")
    print("="*95)
    print(f"{'Tiêu chí đánh giá':<28} | {'Fixed-Time':<12} | {'MaxPressure':<12} | {'Q-Learning':<12} | {'Thuật toán Tốt nhất':<18}")
    print("-"*95)
    
    for m in metrics_summary:
        ft = m["ft_val"]
        mp = m["mp_val"]
        ql = m["ql_val"]
        higher_better = m["higher_is_better"]
        
        vals = {"Fixed-Time": ft, "MaxPressure": mp, "Q-Learning": ql}
        if higher_better:
            best_name = max(vals, key=vals.get)
        else:
            best_name = min(vals, key=vals.get)
            
        winner = f"🏆 {best_name}"
        
        print(f"{m['name']:<28} | {ft:8.2f} {m['unit']:<3} | {mp:8.2f} {m['unit']:<3} | {ql:8.2f} {m['unit']:<3} | {winner:<18}")
        
    print("="*95)

def plot_charts(df_ft, df_mp, df_ql):
    """Vẽ biểu đồ so sánh trực quan 6 tiêu chí trên 3 thuật toán."""
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, axes = plt.subplots(3, 2, figsize=(16, 14))
    fig.suptitle("So Sánh Hiệu Năng: Fixed-Time vs MaxPressure vs Q-Learning (6 Tiêu Chí)", fontsize=17, fontweight='bold', y=0.98)
    
    colors = {"FT": "#e74c3c", "MP": "#2ecc71", "QL": "#3498db"}
    
    # 1. Throughput
    ax = axes[0, 0]
    ax.plot(df_ft["time_sec"], df_ft["throughput"], label="Fixed-Time", color=colors["FT"], lw=2.2)
    ax.plot(df_mp["time_sec"], df_mp["throughput"], label="MaxPressure", color=colors["MP"], lw=2.2)
    ax.plot(df_ql["time_sec"], df_ql["throughput"], label="Q-Learning", color=colors["QL"], lw=2.2, linestyle="--")
    ax.set_title("1. Throughput (Tổng số xe qua ngã tư) [↑ Cao hơn là tốt]", fontsize=12, fontweight='bold')
    ax.set_xlabel("Thời gian mô phỏng (giây)")
    ax.set_ylabel("Số xe")
    ax.legend(loc="upper left")
    ax.grid(True, linestyle="--", alpha=0.6)
    
    # 2. Average Waiting Time
    ax = axes[0, 1]
    ax.plot(df_ft["time_sec"], df_ft["avg_waiting_time"], label="Fixed-Time", color=colors["FT"], lw=2)
    ax.plot(df_mp["time_sec"], df_mp["avg_waiting_time"], label="MaxPressure", color=colors["MP"], lw=2)
    ax.plot(df_ql["time_sec"], df_ql["avg_waiting_time"], label="Q-Learning", color=colors["QL"], lw=2, linestyle="--")
    ax.set_title("2. Average Waiting Time (Thời gian chờ TB) [↓ Thấp hơn là tốt]", fontsize=12, fontweight='bold')
    ax.set_xlabel("Thời gian mô phỏng (giây)")
    ax.set_ylabel("Giây (s)")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.6)
    
    # 3. Queue Length
    ax = axes[1, 0]
    ax.plot(df_ft["time_sec"], df_ft["queue_length"], label="Fixed-Time", color=colors["FT"], alpha=0.8, lw=1.8)
    ax.plot(df_mp["time_sec"], df_mp["queue_length"], label="MaxPressure", color=colors["MP"], alpha=0.8, lw=1.8)
    ax.plot(df_ql["time_sec"], df_ql["queue_length"], label="Q-Learning", color=colors["QL"], alpha=0.8, lw=1.8, linestyle="--")
    ax.set_title("3. Queue Length (Chiều dài hàng đợi xếp hàng) [↓ Thấp hơn là tốt]", fontsize=12, fontweight='bold')
    ax.set_xlabel("Thời gian mô phỏng (giây)")
    ax.set_ylabel("Số xe kẹt")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.6)
    
    # 4. Average Speed
    ax = axes[1, 1]
    ax.plot(df_ft["time_sec"], df_ft["avg_speed"], label="Fixed-Time", color=colors["FT"], lw=2)
    ax.plot(df_mp["time_sec"], df_mp["avg_speed"], label="MaxPressure", color=colors["MP"], lw=2)
    ax.plot(df_ql["time_sec"], df_ql["avg_speed"], label="Q-Learning", color=colors["QL"], lw=2, linestyle="--")
    ax.set_title("4. Average Speed (Vận tốc trung bình toàn mạng) [↑ Cao hơn là tốt]", fontsize=12, fontweight='bold')
    ax.set_xlabel("Thời gian mô phỏng (giây)")
    ax.set_ylabel("km/h")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.6)
    
    # 5. Average Travel Time
    ax = axes[2, 0]
    ax.plot(df_ft["time_sec"], df_ft["avg_travel_time"], label="Fixed-Time", color=colors["FT"], lw=2)
    ax.plot(df_mp["time_sec"], df_mp["avg_travel_time"], label="MaxPressure", color=colors["MP"], lw=2)
    ax.plot(df_ql["time_sec"], df_ql["avg_travel_time"], label="Q-Learning", color=colors["QL"], lw=2, linestyle="--")
    ax.set_title("5. Average Travel Time (Thời gian hoàn thành chuyến đi) [↓ Thấp hơn là tốt]", fontsize=12, fontweight='bold')
    ax.set_xlabel("Thời gian mô phỏng (giây)")
    ax.set_ylabel("Giây (s)")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.6)
    
    # 6. Max Waiting Time
    ax = axes[2, 1]
    ax.plot(df_ft["time_sec"], df_ft["max_waiting_time"], label="Fixed-Time", color=colors["FT"], lw=2)
    ax.plot(df_mp["time_sec"], df_mp["max_waiting_time"], label="MaxPressure", color=colors["MP"], lw=2)
    ax.plot(df_ql["time_sec"], df_ql["max_waiting_time"], label="Q-Learning", color=colors["QL"], lw=2, linestyle="--")
    ax.set_title("6. Max Waiting Time (Thời gian chờ tối đa - Độ công bằng) [↓ Thấp hơn là tốt]", fontsize=12, fontweight='bold')
    ax.set_xlabel("Thời gian mô phỏng (giây)")
    ax.set_ylabel("Giây (s)")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.6)
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    chart_path = os.path.join(OUTPUT_DIR, "traffic_comparison_3models_6metrics.png")
    plt.savefig(chart_path, dpi=300)
    print(f"📊 Đã tạo biểu đồ so sánh 3 mô hình độ phân giải cao: {chart_path}")

def main():
    print("="*95)
    print(" BẮT ĐẦU CHẠY THỬ NGHIỆM ĐÁNH GIÁ SO SÁNH 3 MÔ HÌNH: FIXED-TIME vs MAXPRESSURE vs Q-LEARNING")
    print("="*95)
    
    df_fixed_time = run_simulation(FIXED_TIME_MODEL, "Fixed-Time")
    df_maxpressure = run_simulation(MAXPRESSURE_MODEL, "MaxPressure")
    df_qlearning = run_simulation(QLEARNING_MODEL, "Q-Learning")
    
    generate_comparison_report(df_fixed_time, df_maxpressure, df_qlearning)
    plot_charts(df_fixed_time, df_maxpressure, df_qlearning)
    print("\n🎉 Hoàn thành xuất sắc toàn bộ quy trình thử nghiệm và so sánh!")

if __name__ == "__main__":
    main()
