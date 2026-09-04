#!/usr/bin/env python3
import os
import pandas as pd
import matplotlib.pyplot as plt

OUTPUT_DIR = "/Users/mac/Documents/GAMA/comparison_results"

def load_data():
    df_ft = pd.read_csv(os.path.join(OUTPUT_DIR, "fixed_time_metrics.csv"))
    df_mp = pd.read_csv(os.path.join(OUTPUT_DIR, "maxpressure_metrics.csv"))
    df_ql = pd.read_csv(os.path.join(OUTPUT_DIR, "q_learning_metrics.csv"))
    df_dqn = pd.read_csv(os.path.join(OUTPUT_DIR, "dqn_metrics.csv"))
    return df_ft, df_mp, df_ql, df_dqn

def generate_report(df_ft, df_mp, df_ql, df_dqn):
    metrics_summary = [
        {"id": 1, "name": "Throughput (Tổng xe qua)", "unit": "xe", "higher_is_better": True,
         "vals": {"Fixed-Time": df_ft["throughput"].iloc[-1], "MaxPressure": df_mp["throughput"].iloc[-1], 
                  "Q-Learning": df_ql["throughput"].iloc[-1], "Deep Q-Learning": df_dqn["throughput"].iloc[-1]}},
        {"id": 2, "name": "Average Waiting Time", "unit": "s", "higher_is_better": False,
         "vals": {"Fixed-Time": df_ft["avg_waiting_time"].mean(), "MaxPressure": df_mp["avg_waiting_time"].mean(), 
                  "Q-Learning": df_ql["avg_waiting_time"].mean(), "Deep Q-Learning": df_dqn["avg_waiting_time"].mean()}},
        {"id": 3, "name": "Average Queue Length", "unit": "xe", "higher_is_better": False,
         "vals": {"Fixed-Time": df_ft["queue_length"].mean(), "MaxPressure": df_mp["queue_length"].mean(), 
                  "Q-Learning": df_ql["queue_length"].mean(), "Deep Q-Learning": df_dqn["queue_length"].mean()}},
        {"id": 4, "name": "Average Speed", "unit": "km/h", "higher_is_better": True,
         "vals": {"Fixed-Time": df_ft["avg_speed"].mean(), "MaxPressure": df_mp["avg_speed"].mean(), 
                  "Q-Learning": df_ql["avg_speed"].mean(), "Deep Q-Learning": df_dqn["avg_speed"].mean()}},
        {"id": 5, "name": "Average Travel Time", "unit": "s", "higher_is_better": False,
         "vals": {"Fixed-Time": df_ft["avg_travel_time"].iloc[-1], "MaxPressure": df_mp["avg_travel_time"].iloc[-1], 
                  "Q-Learning": df_ql["avg_travel_time"].iloc[-1], "Deep Q-Learning": df_dqn["avg_travel_time"].iloc[-1]}},
        {"id": 6, "name": "Max Waiting Time", "unit": "s", "higher_is_better": False,
         "vals": {"Fixed-Time": df_ft["max_waiting_time"].max(), "MaxPressure": df_mp["max_waiting_time"].max(), 
                  "Q-Learning": df_ql["max_waiting_time"].max(), "Deep Q-Learning": df_dqn["max_waiting_time"].max()}}
    ]
    
    print("\n" + "="*110)
    print(" BẢNG TỔNG HỢP SO SÁNH 6 TIÊU CHÍ HIỆU NĂNG: FIXED-TIME vs MAXPRESSURE vs Q-LEARNING vs DEEP Q-LEARNING")
    print("="*110)
    print(f"{'Tiêu chí đánh giá':<25} | {'Fixed-Time':<10} | {'MaxPressure':<11} | {'Q-Learning':<10} | {'Deep Q-Learning':<15} | {'Tốt nhất':<15}")
    print("-" * 110)
    
    for m in metrics_summary:
        vals = m["vals"]
        best_name = max(vals, key=vals.get) if m["higher_is_better"] else min(vals, key=vals.get)
        print(f"{m['name']:<25} | {vals['Fixed-Time']:8.2f} {m['unit']:<2} | {vals['MaxPressure']:9.2f} {m['unit']:<2} | {vals['Q-Learning']:8.2f} {m['unit']:<2} | {vals['Deep Q-Learning']:13.2f} {m['unit']:<2} | 🏆 {best_name:<15}")
    print("="*110)

def plot_charts(df_ft, df_mp, df_ql, df_dqn):
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, axes = plt.subplots(3, 2, figsize=(16, 14))
    fig.suptitle("So Sánh Hiệu Năng 4 Thuật Toán (Fixed-Time, MaxPressure, Q-Learning, DQN)", fontsize=16, fontweight='bold', y=0.98)
    
    colors = {"FT": "#e74c3c", "MP": "#2ecc71", "QL": "#3498db", "DQN": "#9b59b6"}
    metrics = [
        (0, 0, "throughput", "1. Throughput [↑ Tốt]", "Số xe", True),
        (0, 1, "avg_waiting_time", "2. Avg Waiting Time [↓ Tốt]", "Giây (s)", False),
        (1, 0, "queue_length", "3. Queue Length [↓ Tốt]", "Số xe", False),
        (1, 1, "avg_speed", "4. Average Speed [↑ Tốt]", "km/h", False),
        (2, 0, "avg_travel_time", "5. Average Travel Time [↓ Tốt]", "Giây (s)", False),
        (2, 1, "max_waiting_time", "6. Max Waiting Time [↓ Tốt]", "Giây (s)", False)
    ]
    
    for row, col, col_name, title, ylabel, is_accum in metrics:
        ax = axes[row, col]
        ax.plot(df_ft["time_sec"], df_ft[col_name], label="Fixed-Time", color=colors["FT"], lw=2)
        ax.plot(df_mp["time_sec"], df_mp[col_name], label="MaxPressure", color=colors["MP"], lw=2)
        ax.plot(df_ql["time_sec"], df_ql[col_name], label="Q-Learning", color=colors["QL"], lw=2)
        ax.plot(df_dqn["time_sec"], df_dqn[col_name], label="Deep Q-Learning", color=colors["DQN"], lw=2, linestyle='--')
        
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_xlabel("Thời gian mô phỏng (s)")
        ax.set_ylabel(ylabel)
        if row == 0 and col == 0:
            ax.legend()
        ax.grid(True, linestyle="--", alpha=0.6)
        
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    chart_path = os.path.join(OUTPUT_DIR, "traffic_comparison_4models_6metrics.png")
    plt.savefig(chart_path, dpi=300)
    print(f"📊 Đã tạo biểu đồ 4 mô hình: {chart_path}")

if __name__ == "__main__":
    df_ft, df_mp, df_ql, df_dqn = load_data()
    generate_report(df_ft, df_mp, df_ql, df_dqn)
    plot_charts(df_ft, df_mp, df_ql, df_dqn)
