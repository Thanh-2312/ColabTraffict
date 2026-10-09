# Traffic-Light-ABM

Mô phỏng vi mô giao thông tại nút giao bốn nhánh bằng **GAMA Platform**, kèm bốn bộ điều khiển đèn: Fixed-Time, MaxPressure, Q-Learning và Deep Q-Network (DQN). Mô hình gồm đường mặt đất, cầu vượt, hầm và các tuyến rẽ. Python và PyTorch được dùng để huấn luyện, đánh giá DQN và chạy benchmark trên cùng lịch xe.

## Nội dung repository

| Đường dẫn | Nội dung |
| --- | --- |
| `Traffic/models/` | Mô hình GAML cho bốn bộ điều khiển, benchmark và kiểm thử |
| `Traffic/includes/` | Mạng đường, cảnh quan và chỉ số an toàn |
| `Traffic/data/` | Dữ liệu đếm xe dùng để hiệu chỉnh |
| `dqn_py/` | DQN, môi trường kết nối GAMA Server, huấn luyện và đánh giá |
| `scripts/` | Benchmark, so sánh, kiểm thử và demo DQN |

Slide seminar, tài liệu nghiên cứu, checkpoint, kết quả chạy và ảnh chụp màn hình là dữ liệu cục bộ, không có trong repository. Các script tạo kết quả trong `comparison_results/` hoặc `dqn_py/run/`.

## Cài đặt

- GAMA Platform 2025.6.4 trở lên, Java 17 trở lên.
- Python 3.11 cho script cài đặt mặc định. Có thể đặt `PYTHON_BIN` nếu dùng một bản Python tương thích khác.
- GAMA Headless mặc định ở `/Applications/Gama.app/Contents/headless/gama-headless.sh`. Nếu cài ở nơi khác, đặt biến môi trường `GAMA_HEADLESS` tới file `gama-headless.sh`.

```bash
git clone https://github.com/ngocbityta/Traffic-Light-ABM.git
cd Traffic-Light-ABM
bash dqn_py/setup_env.sh
```

Trong GAMA Studio, chọn **File → Import → General → Existing Projects into Workspace** và trỏ đến thư mục `Traffic`.

## Chạy mô hình trong GAMA Studio

Mở một trong các file sau, chọn experiment `my_experiment` rồi nhấn **Run**:

- `Traffic/models/intersection-fixed-time.gaml`
- `Traffic/models/intersection-maxpressure.gaml`
- `Traffic/models/intersection-qlearning.gaml`

Các experiment `my_batch_experiment` chạy mô phỏng không có giao diện. Trong GUI, màn hình `doan_3d` hiển thị cầu vượt, hầm và giao lộ; `intersection_view` hiển thị bản đồ 2D.

## Huấn luyện và đánh giá DQN

Để GAMA Server tự khởi động cùng lệnh, dùng `--start-server`:

```bash
dqn_py/venv/bin/python dqn_py/train.py --episodes 100 --episode-horizon 8000 --start-server
dqn_py/venv/bin/python dqn_py/evaluate.py --weights dqn_py/run/train_YYYYMMDD_HHMMSS/dqn_weights.pt --episodes 5 --start-server
```

Kết quả huấn luyện được lưu trong `dqn_py/run/train_<timestamp>/`. `train.py` và `evaluate.py` dùng mô hình `Traffic/models/intersection-dqn-python.gaml` qua GAMA Server.

### Demo DQN trong GAMA Studio

Demo GUI dùng checkpoint `best_dqn.pt` do `scripts/fair_benchmark.py` tạo ra. Checkpoint **không được lưu trong Git**; cần chạy benchmark trước hoặc truyền đường dẫn tới checkpoint tương thích (mạng 11 đầu vào, hai hành động):

```bash
python3 scripts/demo_dqn.py --weights /duong/dan/best_dqn.pt
```

Giữ terminal đang chạy, mở `Traffic/models/intersection-dqn-demo.gaml` trong GAMA Studio, chọn `my_experiment` rồi nhấn **Run**. Nhấn `Ctrl+C` ở terminal để dừng demo. Demo GUI phát xe trực tiếp; số liệu benchmark dùng lịch xe cố định nên không tái tạo bằng cách chạy GUI.

## Benchmark bốn bộ điều khiển

```bash
dqn_py/venv/bin/python scripts/fair_benchmark.py \
  --output comparison_results/fair_benchmark_RUN \
  --train-episodes 40 --validate-every 10 --runs 5 \
  --horizon 8000 --workers 4 --start-server --port 6876
```

Pipeline huấn luyện và so sánh Fixed-Time, MaxPressure, Q-Learning và DQN với cùng lịch yêu cầu xe. Kết quả gồm `report.md`, `comparison.png`, `summary.csv`, `per_run_metrics.csv`, checkpoint và log từng lượt. Có thể dùng `--workers 1` để giảm tài nguyên; dùng `--resume` với cùng cấu hình để tiếp tục lượt bị gián đoạn. `--smoke --horizon 1000` chạy kiểm tra nhanh trong một thư mục output mới.

`scripts/compare_4_models.py` chạy các model GAML riêng để kiểm tra bản demo; kết quả đó không thay thế benchmark chính sách đã huấn luyện ở trên.

## Kiểm thử

```bash
python3 scripts/run_doan_integration_suite.py
python3 scripts/run_test_suite.py
dqn_py/venv/bin/python -m unittest dqn_py.test_gama_env_schedule
```

Các kiểm thử tích hợp GAMA cần GAMA Headless và có thể mất thời gian. Kết quả và log được ghi vào `comparison_results/`.
