# Traffic-Light-ABM: Intelligent Traffic Signal Control

Hệ thống mô phỏng vi mô đa tác tử (Agent-Based Modeling) và điều khiển tín hiệu đèn giao thông thông minh trên nền tảng **GAMA Platform** kết hợp **PyTorch Deep Q-Network (DQN)**.

Dự án triển khai và đối sánh 4 thuật toán điều khiển đèn tín hiệu tại nút giao đô thị 4 nhánh:
1. **Fixed-Time**: Chu kỳ đèn cố định truyền thống.
2. **MaxPressure**: Thuật toán thích ứng dựa trên lý thuyết dòng xe & áp lực hàng đợi (Varaiya, 2013).
3. **Q-Learning**: Học tăng cường dạng bảng (Tabular Reinforcement Learning) nhúng trực tiếp trong GAML.
4. **Deep Q-Network (DQN)**: Học tăng cường sâu (Deep Reinforcement Learning) với PyTorch kết nối qua GAMA Server WebSocket.

---

## Cấu trúc thư mục

```
.
├── Traffic/                             # Mô hình mô phỏng GAMA
│   ├── .project                         # Cấu hình dự án GAMA / Eclipse
│   ├── includes/
│   │   └── collision_avoidance.gaml     # Thuật toán tránh va chạm vi mô
│   └── models/
│       ├── intersection-fixed-time.gaml # Mô hình Fixed-Time
│       ├── intersection-maxpressure.gaml# Mô hình MaxPressure
│       ├── intersection-qlearning.gaml  # Mô hình Q-Learning
│       ├── intersection-dqn-python.gaml # Mô hình DQN (kết nối GAMA Server)
│       └── test_traffic_controllers.gaml# Kiểm thử bộ điều khiển
│
├── dqn_py/                              # Mã nguồn Python DQN & GAMA Server Client
│   ├── dqn_agent.py                     # Cài đặt mạng neural DQN (PyTorch)
│   ├── gama_env.py                      # Môi trường Gym-like giao tiếp qua WebSocket
│   ├── server_manager.py                # Quản lý tiến trình GAMA Headless/Server
│   ├── train.py                         # Huấn luyện DQN Agent
│   ├── evaluate.py                      # Đánh giá mô hình đã huấn luyện
│   ├── smoke_test.py                    # Kiểm tra kết nối nhanh
│   ├── requirements.txt                 # Thư viện Python yêu cầu
│   ├── setup_env.sh                     # Script khởi tạo môi trường venv
│   └── run/
│       └── train_20260829_153936/       # Trọng số pre-trained (best_weights.pt)
│
├── scripts/                             # Scripts tự động hóa & Benchmark
│   ├── compare_4_models.py              # Chạy benchmark đối sánh cả 4 thuật toán
│   ├── compare_traffic_control.py       # Chạy đối sánh Fixed-Time, MaxPressure, Q-Learning
│   ├── plot_4_models.py                 # Vẽ đồ thị so sánh 6 tiêu chí hiệu năng
│   └── run_test_suite.py                # Bộ test suite kiểm thử hệ thống
│
├── comparison_results/                  # Kết quả đo lường & biểu đồ
│   ├── traffic_comparison_4models_6metrics.png # Biểu đồ đối sánh 4 mô hình
│   ├── fixed_time_metrics.csv           # Dữ liệu đo Fixed-Time
│   ├── maxpressure_metrics.csv          # Dữ liệu đo MaxPressure
│   ├── q_learning_metrics.csv           # Dữ liệu đo Q-Learning
│   └── dqn_metrics.csv                  # Dữ liệu đo DQN
│
└── reports/                             # Báo cáo khoa học & phân tích thực nghiệm
    ├── report_traffic_comparison.md     # Báo cáo Markdown chi tiết
    ├── report_traffic_comparison.pdf    # Bản PDF báo cáo 3 mô hình
    ├── benchmark_4models_report.tex     # Báo cáo LaTeX chi tiết 4 mô hình
    └── benchmark_4models_report.pdf     # Bản PDF báo cáo 4 mô hình
```

---

## Yêu cầu môi trường

- **GAMA Platform**: 2025.6.4 hoặc mới hơn (yêu cầu Java 17+)
- **Python**: 3.10+
- **PyTorch**: 2.0+ (hỗ trợ CPU hoặc Apple Silicon MPS / CUDA)

---

## Cài đặt

1. **Clone repository:**
   ```bash
   git clone https://github.com/ngocbityta/Traffic-Light-ABM.git
   cd Traffic-Light-ABM
   ```

2. **Cài đặt môi trường Python:**
   ```bash
   cd dqn_py
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cd ..
   ```

3. **Mở dự án trên GAMA Studio:**
   - Mở GAMA Platform.
   - Chọn `File` -> `Import` -> `General` -> `Existing Projects into Workspace`.
   - Chọn thư mục `Traffic` để nạp các mô hình GAML.

---

## Hướng dẫn sử dụng

### 1. Chạy mô phỏng trực tiếp trên GAMA
- Mở một trong các file trong `Traffic/models/`:
  - `intersection-fixed-time.gaml`
  - `intersection-maxpressure.gaml`
  - `intersection-qlearning.gaml`
- Nhấn chọn experiment `traffic_simulation` hoặc `batch_experiment` và bấm **Run**.

### 2. Huấn luyện và Đánh giá DQN (Python + GAMA Server)
- **Kiểm tra kết nối GAMA Server:**
  ```bash
  cd dqn_py
  python smoke_test.py
  ```
- **Huấn luyện mô hình:**
  ```bash
  python train.py --episodes 100 --steps 300
  ```
- **Đánh giá trọng số đã huấn luyện:**
  ```bash
  python evaluate.py --weights run/train_20260829_153936/best_weights.pt --episodes 5
  ```

### 3. Chạy Benchmark đối sánh 4 mô hình
Chạy tự động toàn bộ 4 mô hình qua GAMA Headless và xuất báo cáo đối sánh:
```bash
python scripts/compare_4_models.py --runs 5 --steps 1000
```
Kết quả CSV và đồ thị trực quan hóa sẽ được lưu vào thư mục `comparison_results/`.

---

## 6 Tiêu chuẩn Đánh giá (Evaluation Metrics)

1. **Throughput (Số xe thoát / hoàn thành hành trình)**: Đo lường thông lượng tổng thể.
2. **Average Waiting Time (Thời gian chờ trung bình)**: Đo lường độ trễ của phương tiện.
3. **Max Waiting Time (Thời gian chờ tối đa)**: Đo lường độ công bằng giữa các hướng lưu thông.
4. **Queue Length (Độ dài hàng đợi trung bình)**: Đánh giá nguy cơ ùn tắc lan truyền.
5. **Vehicle Speed (Vận tốc trung bình của phương tiện)**: Hiệu quả lưu thoát luồng xe.
6. **Phase Switches (Số lần chuyển pha đèn)**: Đánh giá độ ổn định và chi phí chuyển trạng thái an toàn (đèn vàng).
