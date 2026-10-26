# Traffic-Light-ABM

Mô phỏng vi mô giao thông tại nút giao bốn nhánh bằng **GAMA Platform**, kèm năm bộ điều khiển đèn: Fixed-Time, MaxPressure, Q-Learning, Deep Q-Network (DQN) và Dueling Double DQN (3DQN). Mô hình gồm đường mặt đất, cầu vượt, hầm và các tuyến rẽ. Python và PyTorch được dùng để huấn luyện, đánh giá và chạy benchmark trên cùng lịch xe.

## Nội dung repository

| Đường dẫn | Nội dung |
| --- | --- |
| `Traffic/models/` | Mô hình GAML cho năm bộ điều khiển, benchmark và kiểm thử |
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

## Huấn luyện và đánh giá 3DQN trên GAMA

Để GAMA Server tự khởi động cùng lệnh, dùng `--start-server`:

```bash
dqn_py/venv/bin/python dqn_py/train.py --total-steps 5000000 --episode-horizon 8000 --start-server
dqn_py/venv/bin/python dqn_py/evaluate.py --weights dqn_py/run/train_YYYYMMDD_HHMMSS/dqn_weights.pt --episodes 5 --start-server
```

Kết quả huấn luyện được lưu trong `dqn_py/run/train_<timestamp>/`. `train.py` và `evaluate.py` dùng mô hình `Traffic/models/intersection-dqn-python.gaml` qua GAMA Server.

Từ bản sửa 19/10/2026, mọi controller dùng vàng 3 giây, đỏ toàn phần tối thiểu 2 giây và chờ xe đã vào nút thoát ra. 3DQN có action mask: không gia hạn quá 60 giây khi hướng khác có xe, và ưu tiên pha có nhu cầu chưa được phục vụ trong 120 giây. Ngưỡng 120 giây kích hoạt ưu tiên ở quyết định tiếp theo, không phải cam kết giới hạn thời gian chờ khi nút đang bị chặn. Mask được dùng cho cả khám phá, greedy và Double DQN target. GUI preview phục vụ cả bốn pha.

Trong mỗi ô DTSE, tốc độ là **trung bình của các xe**, không phụ thuộc thứ tự duyệt. Occupancy vẫn nhị phân theo nhóm chuyển động, nên chưa biểu diễn mật độ theo từng làn vật lý. Checkpoint 3DQN cũ `dtse-v1` không dùng trực tiếp với hợp đồng state/controller mới; cần huấn luyện lại. `best_weights.pt` được chọn trên hai seed validation 3001–3002 theo hàng đợi, không theo reward của episode train. Horizon là giới hạn thời gian: transition cuối bị cắt giữa action không được đưa vào replay; transition đầy đủ vẫn bootstrap, không coi giao thông là terminal khi đồng hồ hết giờ.

Controller này chọn trực tiếp một trong bốn pha xanh: 0 NS đi thẳng, 1 NS rẽ trái, 2 EW đi thẳng, 3 EW rẽ trái. Xe rẽ phải và quay đầu dùng nhánh riêng, không nhận tín hiệu đèn trong topology GAMA. Chọn lại pha hiện tại kéo dài xanh 10 giây; đổi pha đi qua vàng 3 giây và đỏ toàn phần **tối thiểu** 2 giây, kéo dài đến khi xe đang qua nút đã thoát, rồi mới mở xanh tối thiểu 10 giây. State DTSE có kích thước `3×8×20`: occupancy, tốc độ chia cho 50 km/h, và pha xanh; 8 hàng là bốn hướng E/N/W/S nhân hai nhóm đi thẳng/rẽ trái, mỗi ô cách vạch dừng 8 m trong vùng 160 m. Reward dùng tổng squared delay của bài tham khảo: `clip(1 - D_t/max(D_1..D_t), 0, 1)`, với `D_t = sum(1 - (v/50)^2)` trên **mọi xe có tín hiệu thuộc đường vào nút giao**, kể cả ngoài vùng DTSE; mốc `max` được cập nhật theo lịch sử và giữ xuyên các episode. Đầu vào vẫn là DTSE thích nghi cho hình học GAMA; action 4 pha, mạng CNN/dueling và các siêu tham số chính theo bài báo. Epsilon bắt đầu ở 1, giảm hàm mũ theo thang 2 triệu quyết định tới sàn 0.001; 100.000 transition warm-up đầu được lấy ngẫu nhiên từ các action hợp lệ trước khi cập nhật gradient. Bài báo Đà Nẵng ghi epsilon 0.001 là giá trị ban đầu, trong khi công thức và nghiên cứu nguồn được trích dẫn mô tả epsilon tối thiểu; ở đây chọn cách đặt 0.001 làm sàn để vẫn có giai đoạn khám phá. Mặc định replay 1 triệu transition, Adam `1e-4`, Huber, `γ=0.99`, soft target `τ=0.001`. Có thể giảm `--buffer-size`, `--warmup`, `--total-steps` để kiểm tra nhanh. Một lượt chạy `--total-steps 5000000` lưu cả checkpoint 1M và 5M; chạy riêng lệnh 1M rồi 5M sẽ bắt đầu lại từ đầu. Số step ở đây là quyết định của agent, không phải chu kỳ 0,1 giây của GAMA.

Thiết kế state/action/reward và cấu hình mạng dựa trên [bài báo Đà Nẵng](https://doi.org/10.3390/make7030065) và [mã Ducrocq–Farhi](https://github.com/romainducrocq/DQN-ITSCwPD); [repo tham khảo thứ hai](https://github.com/ngctnnnn/DRL_Traffic-Signal-Control) dùng Double/Dueling DQN trên SUMO. Bốn pha và nhóm làn của nút giao GAMA là phép ánh xạ theo topology hiện có; kích thước DTSE vì thế khác cấu hình SUMO gốc.

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

### So sánh 3DQN với bốn bộ điều khiển cũ

Sau khi có checkpoint và CSV nhu cầu từ benchmark bốn bộ điều khiển, chạy:

```bash
dqn_py/venv/bin/python scripts/benchmark_3dqn_vs_4.py \
  --baseline comparison_results/fair_benchmark_RUN \
  --output comparison_results/benchmark_3dqn_vs_4_RUN \
  --train-episodes 40 --runs 5 --horizon 8000 --workers 4 --port 6890
```

Script huấn luyện 3DQN trên cùng 40 seed huấn luyện và đánh giá cả năm chính sách trên cùng năm seed kiểm tra, 8.000 chu kỳ/seed. Bốn chính sách cũ chạy qua `intersection-dqn-legacy.gaml` để giữ đúng action 0/1; 3DQN dùng mô hình bốn action. Warm-up mặc định của benchmark là 64 transition, replay 20.000 và bốn cập nhật mỗi transition. Epsilon thăm dò giảm theo hàm mũ sau mỗi transition; lượt kiểm tra dùng epsilon 0. Checkpoint được chọn theo hàng đợi trung bình trên hai seed validation sau mỗi 10 episode, cùng quy tắc với baseline. Đây là cấu hình so sánh theo ngân sách 40 tập, khác cấu hình 100.000 warm-up của huấn luyện 3DQN đầy đủ. Kết quả có `report.md`, `per_run_metrics.csv`, checkpoint, log từng lượt và `manifest.json`; dùng `--resume` với cùng cấu hình để tiếp tục lượt bị gián đoạn. Nếu các model GAMA baseline và dữ liệu nhu cầu không đổi, có thể thêm `--reuse-baselines /duong/dan/benchmark-cu` để dùng lại kết quả đánh giá bốn baseline sau khi đối chiếu hash.

Q-Learning và DQN trong benchmark là hai learner Python dùng chung transition của 40 episode; mỗi learner điều khiển 20 episode khi thu thập dữ liệu. Các model GAML `intersection-qlearning.gaml` và `intersection-dqn-python.gaml` là đường chạy demo/3DQN riêng, không phải checkpoint Q-Learning/DQN Python đã đánh giá trong benchmark. Lệnh `dqn_py/train.py` cũng dùng luồng xe do GAMA sinh theo seed; benchmark dùng CSV nhu cầu xe cố định.

Benchmark mới mặc định `--reward-mode queue_time`: reward âm của thời gian xe dừng tích lũy giữa hai quyết định chia 50, discount `0.97 ** (dt_seconds / 5)`, cùng mục tiêu với Q-Learning và DQN. Reward này tính cả thời gian vàng/đỏ và là lựa chọn thích nghi GAMA, **khác reward bài báo**. Dùng `--reward-mode reference --reward-scope all` để giữ công thức delay bình phương tốc độ của repo; `--reward-scope near` là ablation chỉ tính vùng DTSE 160 m. `train.py` độc lập vẫn mặc định `reference`; có thể truyền `--reward-mode queue_time`.

Phải chạy lại `fair_benchmark.py` trên phiên bản hiện tại trước khi so sánh. Script từ chối baseline huấn luyện bằng code/môi trường khác; cache kiểm tra hash policy/checkpoint, source Python/GAMA, demand và cấu hình reward. `--resume` còn đối chiếu agent seed và toàn bộ CSV train/validation/test. Q-learning GAML chạy online đã đổi sang reward tích lũy theo thời gian, discount theo khoảng quyết định, state có tuổi pha và bootstrap chỉ action đổi pha tại giới hạn xanh; đây vẫn là một demo online, không phải bảng Q của benchmark Python.

[Kiểm toán năm phương pháp](comparison_results/audit_5_methods_20261018/findings.md) và `benchmark_3dqn_clearance_20261018` là dữ liệu lịch sử trước bản sửa 19/10/2026, không đại diện cho code hiện tại. Chỉ số TTC hiện là sự kiện đuổi gần trên quỹ đạo cùng làn, tính độc lập với tên xe; phanh gấp được đếm khi bắt đầu một đợt phanh. PET tiếp tục đo xung đột cắt nhau. Các bộ đếm an toàn cũ theo tick không so trực tiếp với bộ đếm sự kiện mới.

## Kiểm thử

```bash
python3 scripts/run_doan_integration_suite.py
python3 scripts/run_test_suite.py
dqn_py/venv/bin/python -m unittest scripts.test_fair_benchmark scripts.test_learning_pipeline dqn_py.test_three_dqn_agent dqn_py.test_gama_env_schedule dqn_py.test_server_manager_cleanup
```

Các kiểm thử tích hợp GAMA cần GAMA Headless và có thể mất thời gian. Kết quả và log được ghi vào `comparison_results/`.

Kiểm tra protocol GAMA Server end-to-end (tùy chọn):

```bash
dqn_py/venv/bin/python dqn_py/test_doan_server.py --start-server --horizon 4000
```
